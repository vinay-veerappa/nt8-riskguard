using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
#if !TESTING
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core;
#else
using NinjaTrader.Cbi;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core;
using NinjaTrader.Code;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
#endif

namespace NinjaTrader.NinjaScript.AddOns
{
    public class RiskGuardAddOn : AddOnBase
    {
        public static RiskGuardAddOn Instance { get; private set; }
        // Reported by GET /api/riskguard/version, which is how an operator finds out what
        // is running on a live account. Bump it in the SAME commit as the release tag --
        // tools/check_version_matches_tag.py fails the build otherwise, because on
        // 2026-08-13 this said 1.1.0 while v1.2.0 was tagged, deployed and compiled.
        public const string Version = "1.29.0";
        public object StateLock => _stateLock;
        public RiskConfig Config => _config;

        public void SaveAndReloadConfig(RiskConfig newConfig)
        {
            lock (_stateLock)
            {
                try
                {
                    string json = JsonConvert.SerializeObject(newConfig, Formatting.Indented);
                    File.WriteAllText(_configFile, json);
                    LoadConfig(); // Reloads from the file, updating _config and _parsedWindows
                    LogEvent("SYSTEM", "CONFIG_SAVE", "Configuration successfully saved and reloaded from UI.");
                }
                catch (Exception ex)
                {
                    LogEvent("SYSTEM", "ERROR", $"Failed to save config: {ex.Message}");
                }
            }
        }

        public void ReloadConfig()
        {
            LoadConfig();
        }

        // - FSM observation API (for MCP bridge; read-only, -7 of RiskGuardAddOn.md) -
        public class FsmSnapshot
        {
            public string AccountName { get; set; }
            public string Instrument { get; set; }
            public string State { get; set; }
            public string PositionSide { get; set; }
            public int PositionQuantity { get; set; }
            public DateTime EntryTime { get; set; }
            public DateTime GraceDeadline { get; set; }
            public bool HasAutoStopOrder { get; set; }
            public string RecognizedStopName { get; set; }
        }

        public List<FsmSnapshot> GetFsmSnapshots()
        {
            var list = new List<FsmSnapshot>();
            lock (_stateLock)
            {
                foreach (var fsm in _guardFsms.Values)
                {
                    list.Add(new FsmSnapshot
                    {
                        AccountName = fsm.AccountName,
                        Instrument = fsm.Instrument,
                        State = fsm.State.ToString(),
                        PositionSide = fsm.PositionSide.ToString(),
                        PositionQuantity = fsm.PositionQuantity,
                        EntryTime = fsm.EntryTime,
                        GraceDeadline = fsm.GraceDeadline,
                        HasAutoStopOrder = fsm.AutoStopOrder != null,
                        RecognizedStopName = fsm.RecognizedStopOrder?.Name
                    });
                }
            }
            return list;
        }

        public bool ResetFsm(string accountName, string instrument)
        {
            lock (_stateLock)
            {
                return _guardFsms.Remove(FsmKey(accountName, instrument));
            }
        }

        /// <summary>
        /// P1-100. THE ONE PLACE that answers "does a lockout currently bind on this account", i.e.
        /// must an order be refused. Every reader of that fact calls this; none re-derives it.
        ///
        /// It exists because the fact HAD three readers and they disagreed. `P2-92` taught CanTrade
        /// to honour the authority a lockout was imposed under, and `P2-94` taught it to read
        /// LockoutUntil -- both edits landed here and nowhere else, so `IsAccountLocked`, which the
        /// bridge's order paths consult, still returned the raw flag and was wrong in BOTH
        /// directions: it refused real orders on a shadow-only observation (measured live
        /// 2026-08-14, `P1-100`), and it admitted orders during a TIMED manual lockout, which is
        /// `P2-94` verbatim surviving at a second reader. A predicate with one caller is a
        /// convention; a predicate with every caller is a guarantee.
        ///
        /// The three parts, and why each is load-bearing:
        ///
        ///   * `IsLockedOut || UtcNow &lt; LockoutUntil` -- an OR, per `P1-54`. LockAccount's timed
        ///     branch sets only the deadline; every rule breach sets only the flag. Reading either
        ///     one alone misses half the lockouts in this codebase.
        ///
        ///   * `!LockoutWasShadowOnly` -- `P2-92`. A rule breach observed in shadow mode records
        ///     what it WOULD have done. Shadow exists to evaluate the guard without touching
        ///     trading, so an observation must not gate an order. Note this is a property of the
        ///     LOCKOUT, not of the current mode: consulting `_mode` here would make a mode switch a
        ///     lockout bypass. Manual lockouts set it false explicitly and so always bind.
        ///
        ///   * the disarmed bypass -- FR-30 + judge-loop `P1-4`. Lockouts survive a disarm unless
        ///     the account is listed in LockoutBypassWhileDisarmedAccounts, so a panic toggle-off
        ///     cannot defeat a daily-loss lockout on a prop account.
        ///
        /// Precondition: caller holds _stateLock.
        /// </summary>
        private bool LockoutBinds(string accountName)
        {
            if (!_accountStates.TryGetValue(accountName, out var state)) return false;
            return LockoutBinds(accountName, state);
        }

        // Overload for callers that already hold the AccountState. Same predicate, no second copy.
        private bool LockoutBinds(string accountName, AccountState state)
        {
            if (state == null) return false;

            bool underLockout = state.IsLockedOut
                || (state.LockoutUntil > DateTime.MinValue && DateTime.UtcNow < state.LockoutUntil);
            if (!underLockout) return false;

            if (state.LockoutWasShadowOnly) return false;

            bool bypassAllowed = !_isArmed
                && _config != null
                && _config.LockoutBypassWhileDisarmedAccounts != null
                && _config.LockoutBypassWhileDisarmedAccounts.Contains(accountName);
            return !bypassAllowed;
        }

        public bool CanTrade(string accountName, string instrument, string strategyName = "DefaultStrategy")
        {
            lock (_stateLock)
            {
                if (LockoutBinds(accountName)) return false;

                if (!_isArmed) return true;
                if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accountName)) return true;
                if (!string.IsNullOrEmpty(instrument))
                {
                    string root = instrument.Split(' ')[0].ToUpper();
                    if (_config.BlockedInstruments != null && _config.BlockedInstruments.Contains(root)) return false;
                }
                return true;
            }
        }

        public class AccountStateSnapshot
        {
            public string AccountName { get; set; }
            public bool IsLockedOut { get; set; }
            public double RealizedPnL { get; set; }
            public double UnrealizedPnL { get; set; }
            public int TradesToday { get; set; }
            public int ConsecutiveLosses { get; set; }
            public string PositionString { get; set; }
            public bool IsExcluded { get; set; }
            public double AccountEquity { get; set; }
            public DateTime LockoutUntil { get; set; }
        }

        public List<AccountStateSnapshot> GetAccountSnapshots()
        {
            var list = new List<AccountStateSnapshot>();
            lock (_stateLock)
            {
                foreach (var state in _accountStates.Values)
                {
                    var account = Account.All.FirstOrDefault(a => a.Name == state.AccountName);
                    if (account == null)
                    {
                        continue; // Skip historical/blown accounts not currently loaded
                    }
                    double equity = account.Get(AccountItem.CashValue, Currency.UsDollar) + account.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar);
                    var snapshot = new AccountStateSnapshot
                    {
                        AccountName = state.AccountName,
                        IsLockedOut = state.IsLockedOut,
                        RealizedPnL = state.RealizedPnL,
                        UnrealizedPnL = state.UnrealizedPnL,
                        TradesToday = state.TradesToday,
                        ConsecutiveLosses = state.ConsecutiveLosses,
                        IsExcluded = _config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(state.AccountName),
                        AccountEquity = equity,
                        LockoutUntil = state.LockoutUntil
                    };
                    
                    var posList = new List<string>();
                    foreach (var pos in state.Positions.Values)
                    {
                        if (pos.MarketPosition != MarketPosition.Flat)
                        {
                            string posType = pos.MarketPosition == MarketPosition.Long ? "L" : "S";
                            posList.Add(string.Format("{0} {1} {2}", posType, pos.Quantity, pos.Instrument.Split(' ')[0]));
                        }
                    }
                    snapshot.PositionString = posList.Count > 0 ? string.Join(", ", posList) : "FLAT";
                    list.Add(snapshot);
                }
            }
            return list;
        }

        /// <summary>
        /// The rule inventory for every account the guard knows about (UI4).
        ///
        /// This method's ONLY job is to gather what the registry cannot reach -- the mode, the
        /// armed flag, the account states and the news-event count -- and hand them over. It must
        /// contain no rule logic and no state derivation of its own: everything that decides
        /// whether a rule is protecting you lives in `GuardRuleRegistry`, so there is one place
        /// for it to be wrong.
        /// </summary>
        public GuardSnapshot BuildGuardSnapshot()
        {
            string mode;
            bool isArmed;
            RiskConfig config;
            lock (_stateLock)
            {
                mode = _mode;
                isArmed = _isArmed;
                config = _config;
            }

            return GuardRuleRegistry.BuildSnapshot(
                config,
                PropFirmProtectionSuite.Instance.Config,
                mode,
                isArmed,
                GetAccountSnapshots(),
                PropFirmProtectionSuite.Instance.NewsEventCount,
                PropFirmProtectionSuite.Instance.NewsEventsLoadStatus);
        }
        private string _logDir;
        private string _logFile;
        private string _stateFile;
        private string _configFile;
        private string _heartbeatFile;
        private DateTime _lastHeartbeatTime = DateTime.MinValue;
        private bool _stateDirty = false;

        private Timer _safetyTimer;
        private readonly object _stateLock = new object();
        // FR-30: Guard starts each session DISARMED; no enforcement until explicitly armed via Preflight().
        // Previously defaulted to true, which violated FR-30 and bypassed the arming ritual.
        // Under TESTING, tests assume an armed guard by default (call SetArmedForTest(false) to test disarm).
#if TESTING
        private bool _isArmed = true;
#else
        private bool _isArmed = false;
#endif
        // FR-29: count of completed shadow sessions, persisted across restarts. Incremented on session reset.
        private int _shadowSessionsCompleted = 0;
        // Tracks the session date already counted, so we only increment once per ET session day.
        private DateTime _lastShadowSessionDate = DateTime.MinValue.Date;
        private string _mode = "shadow"; // fail-safe default; overridden by config in LoadConfig()

        // Per-position guard state machines (see -6 of RiskGuardAddOn.md).
        // Keyed by "accountName|instrumentFullName". All access under _stateLock.
        private readonly Dictionary<string, PositionGuardFsm> _guardFsms = new Dictionary<string, PositionGuardFsm>();
        private System.Threading.Timer _auditTimer;
        private int _auditIntervalSeconds = 10;

        // Pending-stop buffer: stops whose OrderUpdate arrived before PositionUpdate
        // (possible per NT8 event ordering). Keyed by "accountName|instrumentFullName".
        // Consumed when the FSM is created on the position-open event; protects against the
        // race where the stop leg is observed before the position leg.
        //
        // P1-14 made this a LIST with a timestamp. It was one Order per key, which failed three
        // ways at once:
        //   - a bracket with two stop legs, or a second stop arriving first, silently overwrote
        //     the first and the guard saw only the survivor;
        //   - entries were removed only on consumption or on flat, so a stop buffered for a
        //     position that never opened (entry rejected) lived forever and was consumed by a
        //     LATER, UNRELATED position on the same instrument;
        //   - nothing checked what the order actually was. The side is genuinely unknown at
        //     buffer time -- that part is inherent -- but the consumer only checked side, so a
        //     resting stop-market ENTRY order (a breakout entry: the most common non-protective
        //     stop there is) was adopted as the position's protective stop. A 10-lot sell-stop
        //     breakout entry buffered while flat, then a 1-lot long opened by hand, and the FSM
        //     reads Protected with CoveredQuantity 10 on a 1-lot position: grace cancelled, no
        //     auto-stop, and the account flips 9 lots short if that order ever triggers.
        private class BufferedStop
        {
            public Order Order;
            public DateTime BufferedAtUtc;
        }
        private readonly Dictionary<string, List<BufferedStop>> _pendingStops =
            new Dictionary<string, List<BufferedStop>>();

        // P1-35/P1-10: cancellations decided while holding _stateLock, to be sent to the broker
        // once it is released. The design doc's central concurrency invariant is that no
        // Account trading call happens under the lock; queueing is how a decision made inside
        // the lock reaches the broker outside it. Guarded by _stateLock.
        // Deferred cancel queue. Entries carry intent so the drain can distinguish
        // trader-order interventions (withheld in shadow mode) from RiskGuard's own
        // cleanup cancels (sent in every mode). See T6/P0-51.
        private enum PendingCancelIntent
        {
            Intervention,
            Cleanup
        }

        private readonly struct PendingCancelEntry
        {
            public readonly Account Account;
            public readonly Order Order;
            public readonly PendingCancelIntent Intent;

            public PendingCancelEntry(Account account, Order order, PendingCancelIntent intent)
            {
                Account = account;
                Order = order;
                Intent = intent;
            }
        }

        private readonly List<PendingCancelEntry> _pendingCancels =
            new List<PendingCancelEntry>();

        // Tracks which accounts have already logged a shadow lockout-sweep skip this lockout,
        // so the informative shadow log is emitted at most once per account per lockout.
        private readonly Dictionary<string, bool> _lockoutSweepShadowLogged =
            new Dictionary<string, bool>();
#if !TESTING
        private NTMenuItem _myMenuItem;
        private ControlCenter _controlCenter;
#endif
        private RiskConfig _config = new RiskConfig();

        // Cached Resources (Fix 12)
        private TimeZoneInfo _etZone = TimeZoneInfo.FindSystemTimeZoneById(
            Environment.OSVersion.Platform == PlatformID.Win32NT
                ? "Eastern Standard Time"
                : "America/New_York");
        private List<ParsedWindow> _parsedWindows = new List<ParsedWindow>();

        // Async Logging (Fix 11)
        private readonly System.Collections.Concurrent.ConcurrentQueue<string> _logQueue = new System.Collections.Concurrent.ConcurrentQueue<string>();

        // Per-account and aggregate state models
        private readonly Dictionary<string, AccountState> _accountStates = new Dictionary<string, AccountState>();
        private readonly List<string> _subscribedAccounts = new List<string>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "RiskGuardAddOn";
                Description = "Cross-Account Risk Guard and Discipline Backstop";
            }
            else if (State == State.Configure)
            {
                Instance = this;
                InitializeRiskGuard();
            }
            else if (State == State.Terminated)
            {
                CleanupRiskGuard();
            }
        }

        private void InitializeRiskGuard()
        {
            try
            {
                _logDir = Path.Combine(Globals.UserDataDir, "RiskGuard");
                if (!Directory.Exists(_logDir))
                {
                    Directory.CreateDirectory(_logDir);
                }

                _logFile = Path.Combine(_logDir, "interventions.jsonl");
                _stateFile = Path.Combine(_logDir, "state.json");
                _configFile = Path.Combine(_logDir, "config.json");
                _heartbeatFile = Path.Combine(_logDir, "heartbeat.txt");

                // Cache timezone (Fix 12)
                _etZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

                // Load or generate config
                LoadConfig();

                // Load any persisted lockout/session state
                LoadPersistedState();

                // Subscribe to existing accounts
                lock (_stateLock)
                {
                    foreach (Account account in Account.All)
                    {
                        SubscribeToAccount(account);
                    }
                }

                // Subscribe to connection events to catch new account connections dynamically
                Connection.ConnectionStatusUpdate += OnConnectionStatusUpdate;

                // Start 5-second safety sweep timer.
                // Phase 2: all per-account rules are event-driven (PositionUpdate/OrderUpdate).
                // The sweep only handles: heartbeat, log flush, session reset, aggregate
                // sizing, grace-expiry polling, firm-mirror, state persist, FSM watchdog.
                // None of these need 1-second resolution; 5s is sufficient.
                _safetyTimer = new Timer(OnSafetySweep, null, 5000, 5000);

                // P3-30's audit is the CLOCK-driven complement to FsmWatchdog, which runs on
                // events only -- so a divergence that arrives with no subsequent event is
                // permanent without it. It shipped with nothing calling StartAuditTimer, so
                // `AuditIntervalSeconds: 10` sat in the live config describing an audit that
                // never ran: a configured protection that did not exist.
                StartAuditTimer();

                LogEvent("SYSTEM", "INITIALIZE", $"RiskGuard Add-On v{Version} initialized in {_mode} mode. Event monitoring started.");
                // P1-47: the mode is resolved by now, so the arm default can follow it.
                ApplyInitialArmState();
                NinjaTrader.Code.Output.Process($"[RiskGuard v{Version}] RESOLVED MODE = {_mode} (armed={_isArmed})", PrintTo.OutputTab1);
            }
            catch (Exception ex)
            {
                LogEvent("SYSTEM", "ERROR", "Initialization failed: " + ex.ToString());
            }
        }

        private void CleanupRiskGuard()
        {
            try
            {
                // Stop safety timer
                _safetyTimer?.Dispose();
                StopAuditTimer();

                // Unsubscribe from connection events
                Connection.ConnectionStatusUpdate -= OnConnectionStatusUpdate;

                // Unsubscribe from all accounts
                lock (_stateLock)
                {
                    foreach (Account account in Account.All)
                    {
                        UnsubscribeFromAccount(account);
                    }
                }

                // Persist current session state before exit
                SavePersistedState();

                LogEvent("SYSTEM", "SHUTDOWN", "RiskGuard Add-On shut down successfully.");
            }
            catch (Exception ex)
            {
                LogEvent("SYSTEM", "ERROR", "Cleanup failed: " + ex.ToString());
            }
        }

        // P3-30. NOT a dev/test hook: this is the production audit timer. It sat inside
        // the `#if TESTING` block below, which is why `AuditIntervalSeconds: 10` could be
        // live in the deployed config while the code honouring it did not exist in the
        // net48 assembly at all. P1-47 is the same trap: a green net8.0 suite cannot see it,
        // only nt_compile can.
        private void StartAuditTimer()
        {
            StopAuditTimer();

            int seconds = _config != null ? _config.AuditIntervalSeconds : _auditIntervalSeconds;
            if (seconds <= 0)
                return;

            _auditTimer = new System.Threading.Timer(
                state =>
                {
                    try
                    {
                        RunGuardAudit();
                    }
                    catch (Exception ex)
                    {
                        LogEvent("RiskGuard", "AUDIT_TIMER_ERROR",
                            $"Audit timer callback failed: {ex}");
                    }
                },
                null,
                TimeSpan.FromSeconds(seconds),
                TimeSpan.FromSeconds(seconds));
        }

        private void StopAuditTimer()
        {
            var timer = _auditTimer;
            if (timer != null)
            {
                timer.Change(System.Threading.Timeout.Infinite, System.Threading.Timeout.Infinite);
                timer.Dispose();
                _auditTimer = null;
            }
        }

        // -
        // DEV/TESTING API
        // -
#if TESTING
        internal void SetConfigForTest(RiskConfig cfg)
        {
            _config = cfg;
        }

        internal void SetAccountStateForTest(string accountName, AccountState state)
        {
            _accountStates[accountName] = state;
        }

        internal AccountState GetAccountStateForTest(string accountName)
        {
            AccountState state;
            return _accountStates.TryGetValue(accountName, out state) ? state : null;
        }

        internal void SetSubscribedAccountForTest(string accountName)
        {
            _subscribedAccounts.Add(accountName);
        }

        // The copier reaches RiskGuard through the static Instance, which production
        // assigns in State.Configure. A test constructing `new RiskGuardAddOn()` never
        // reaches Configure, so Instance stays null and the copier sees no guard at
        // all -- which silently made the P0-8 lockout test unable to observe its own
        // subject. Tests must wire the instance explicitly.
        internal static void SetInstanceForTest(RiskGuardAddOn guard) { Instance = guard; }

        internal void SetArmedForTest(bool armed) { _isArmed = armed; }
        internal void ApplyInitialArmStateForTest() { ApplyInitialArmState(); }

// The two methods below are PRODUCTION code and must exist in the NT8 (net48) build too, so the
// TESTING guard is closed around them. Leaving them inside it compiled cleanly under net8.0 and
// failed only in NT8 with "ApplyInitialArmState does not exist" -- the test build proves nothing
// about the real one.
#endif

        // P1-47: the arm default follows the resolved mode.
        //
        // Arming controls whether the guard EVALUATES; the mode controls whether it ACTS
        // (ProcessAction returns "SHADOW (SKIPPED)" before touching the broker unless the mode is
        // "live"). Defaulting to disarmed therefore protected against the wrong thing: it could
        // not prevent enforcement, because shadow cannot enforce, but it did mean every recompile
        // silently stopped the guard observing anything -- four times in one session on
        // 2026-08-07, each needing the operator to notice and re-arm by hand.
        //
        // FR-30's intent -- no enforcement until a deliberate arming ritual -- is preserved:
        // acting modes still come up disarmed and still require preflight plus TOGGLE ARMED.
        // An unrecognised mode is treated as non-acting because ProcessAction requires exactly
        // "live", so observing is the safe reading of a config we do not understand.
        internal static bool DefaultArmedForMode(string mode)
        {
            return !(string.Equals(mode, "live", StringComparison.OrdinalIgnoreCase)
                  || string.Equals(mode, "pure", StringComparison.OrdinalIgnoreCase)
                  || string.Equals(mode, "override_with_friction", StringComparison.OrdinalIgnoreCase));
        }

        // Applied once at initialise, after LoadConfig has resolved the mode. NOT applied on a
        // config reload: that would override an operator who deliberately disarmed.
        private void ApplyInitialArmState()
        {
            _isArmed = DefaultArmedForMode(_mode);

            if (_isArmed)
            {
                LogEvent("SYSTEM", "ARMED_ON_START",
                    $"Guard armed on start in '{_mode}' mode. It observes and logs; it cannot act outside 'live'.");
            }
            else
            {
                // Loud on purpose. The real failure in P1-47 was not the default -- it was that
                // being unprotected looked identical to being protected.
                LogEvent("SYSTEM", "UNPROTECTED_ON_START",
                    $"GUARD IS NOT ARMED. Mode '{_mode}' is an acting mode, so arming requires a deliberate "
                    + "preflight and TOGGLE ARMED. Until then no rule evaluates and CanTrade allows everything.");
            }
        }

#if TESTING
        internal void SetModeForTest(string mode)  { _mode = mode; }
        internal void SetParsedWindowsForTest(List<ParsedWindow> windows) { _parsedWindows = windows; }
        internal bool GetIsArmed() => _isArmed;

        // - FSM test accessors (-6) -
        internal void TestFsmOnPosition(Account account, string instrument, MarketPosition pos, int qty)
        {
            lock (_stateLock) { UpdateFsmOnPosition(account, instrument, pos, qty); }
            // Mirror ExecutePositionUpdateDetails: the teardown queues orphan cancels and the
            // caller drains them after the lock. Without this a test driving the FSM directly
            // would leave the queue full and the orphan stop alive.
            DrainPendingCancels();
        }
        internal void TestFsmOnOrder(Account account, string instrument, Order order)
        {
            lock (_stateLock) { UpdateFsmOnOrder(account, instrument, order); }
        }
        internal PositionGuardFsm TestGetFsm(string accountName, string instrument)
        {
            lock (_stateLock)
            {
                return _guardFsms.TryGetValue(FsmKey(accountName, instrument), out var fsm) ? fsm : null;
            }
        }
        internal List<PositionGuardFsm> TestAllFsms()
        {
            lock (_stateLock) { return _guardFsms.Values.ToList(); }
        }
        internal void TestClearFsms()
        {
            lock (_stateLock) { _guardFsms.Clear(); _pendingStops.Clear(); }
        }

        // P3-30 stub: exists so the acceptance tests compile. The real audit is the
        // agent loop's job. This stub does nothing, so every assertion fails.
        internal void SetFsmForTest(string accountName, string instrument, PositionGuardFsm fsm)
        {
            lock (_stateLock) { _guardFsms[FsmKey(accountName, instrument)] = fsm; }
        }
        internal void RunAuditNow() { RunGuardAudit(); }

        // --- pending-stop buffer seams (P1-14) ---
        internal int TestPendingStopCount(string accountName, string instrument)
        {
            lock (_stateLock)
            {
                List<BufferedStop> b;
                return _pendingStops.TryGetValue(FsmKey(accountName, instrument), out b) ? b.Count : 0;
            }
        }

        /// <summary>
        /// Ages every buffered stop for a key. The TTL is measured in grace periods, which are
        /// configured in whole seconds, so a real-time test would have to sleep for them --
        /// and a sleeping test is one that gets shortened until it stops proving anything.
        /// </summary>
        internal void TestBackdatePendingStops(string accountName, string instrument, TimeSpan by)
        {
            lock (_stateLock)
            {
                List<BufferedStop> b;
                if (!_pendingStops.TryGetValue(FsmKey(accountName, instrument), out b)) return;
                foreach (var entry in b) entry.BufferedAtUtc -= by;
            }
        }

        // ExecuteAction and ValidateInvariant are the two halves of the auto-stop
        // path that T2 rewrote (reserve-before-submit, rollback, live-position
        // sizing). Both are private, so before these seams existed the only
        // coverage they could have was indirect. Exposed read-through only -- the
        // seams add no behaviour of their own, so a test that passes through them
        // is testing production code, not a test-only variant of it.
        internal void TestExecuteAction(GuardAction action)
        {
            ExecuteAction(action);
        }

        internal bool TestValidateInvariant(GuardAction action)
        {
            // Production reaches ValidateInvariant from ProcessAction, which already
            // holds _stateLock; match that so the _guardFsms read is not racy.
            lock (_stateLock) { return ValidateInvariant(action); }
        }

        // --- FR-29 shadow-session gate (P1-37) ---
        // Production wires _stateFile inside InitializeRiskGuard, which a test cannot
        // call without also starting timers and subscribing to accounts. Point the
        // persistence at a temp file instead, so a restart can be simulated honestly:
        // save, construct a second instance, load, and see what it believes.
        internal void SetStateFileForTest(string path) { _stateFile = path; }
        // S8 drives a genuine SaveAndReloadConfig round trip. Without a real path the write
        // throws inside its own catch, LoadConfig finds no file and manufactures a default
        // config -- and the test would "pass" while proving the opposite of what it claims.
        internal void SetConfigFileForTest(string path) { _configFile = path; }
        internal void SavePersistedStateForTest() { SavePersistedState(); }
        internal void LoadPersistedStateForTest() { LoadPersistedState(); }
        internal int GetShadowSessionsCompletedForTest() { return _shadowSessionsCompleted; }
        internal DateTime GetLastShadowSessionDateForTest() { return _lastShadowSessionDate; }
        internal void SetLastShadowSessionDateForTest(DateTime d) { _lastShadowSessionDate = d; }

        // --- lock-scope probe (P1-10, P1-35) ---
        // The design doc's central concurrency invariant is that no Account trading call
        // happens while _stateLock is held. Monitor.IsEntered answers that for the calling
        // thread, which is precisely the thread the broker stub runs on, so a test can
        // observe every violation instead of hoping a reviewer spots one nested three
        // calls deep inside a lock block.
        internal bool TestIsStateLockHeld() { return Monitor.IsEntered(_stateLock); }

        // --- disk-write probe (P1-12) ---
        // Same argument as the broker-call probe above, for the other class of call that must
        // never run under _stateLock. A stalled disk holding the lock stalls every NT8 event
        // handler behind it, including the ones that attach protective stops. Reading the code
        // does not settle it: _stateLock is RE-ENTRANT, so a write that looks outside the lock is
        // still inside it whenever its caller was itself called under the lock -- which is how
        // three of the four original sites got there.
        internal static Action<string> FileWriteObserver;

        // --- audit-event probe (P2-92) ---
        // Same argument as the two probes above, for the addon's OTHER product: the audit record.
        // A mutant that deleted the SHADOW_LOCKOUT log line survived 1,224 passing tests, because
        // nothing in the suite could observe that an event was emitted at all. `(account, eventType)`
        // is deliberately the whole signature -- a test asserting on the message TEXT would break on
        // every rewording, and the thing worth pinning is that the event HAPPENS and carries the
        // right type. See `P1-71`: a message must not NAME another event type, because this log is
        // grepped by type after the fact.
        internal static Action<string, string> LogEventObserver;
#endif

        public void ResetStateForDev()
        {
            lock (_stateLock)
            {
                _accountStates.Clear();
                _guardFsms.Clear();
                _pendingStops.Clear();
                try { LoadConfig(); } catch {}
                // We'll also clear the persisted file so it doesn't reload old state
                if (File.Exists(_stateFile))
                {
                    try { File.Delete(_stateFile); } catch {}
                }
                LogEvent("SYSTEM", "DEV_RESET", "State was reset via Developer API.");
            }
        }

        private void SubscribeToAccount(Account account)
        {
            if (account == null) return;
            if (_subscribedAccounts.Contains(account.Name)) return;

            account.PositionUpdate += OnPositionUpdate;
            account.OrderUpdate += OnOrderUpdate;
            account.ExecutionUpdate += OnExecutionUpdate;
            account.AccountItemUpdate += OnAccountItemUpdate;

            _subscribedAccounts.Add(account.Name);

            if (!_accountStates.TryGetValue(account.Name, out var state))
            {
                state = new AccountState(account.Name);
                state.SessionStartRealizedPnL = account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
                state.LastRealizedPnL = state.SessionStartRealizedPnL;
                _accountStates[account.Name] = state;
            }
            else
            {
                if (state.SessionStartRealizedPnL == 0.0)
                {
                    state.SessionStartRealizedPnL = account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
                    state.LastRealizedPnL = state.SessionStartRealizedPnL;
                }
            }

            LogEvent("SYSTEM", "SUBSCRIBE", $"Subscribed to account events for: {account.Name}");

            // P1-6 (judge loop): instantiate FSMs for positions that already exist at subscribe time
            // (e.g. add-on startup, account reconnect, or NT8 restart mid-trade). Without this,
            // an existing position has no stop-guard until it first goes flat and re-enters.
            SeedFsmsForExistingPositions(account);
        }

        // Creates a PositionGuardFsm for every non-flat position currently on `account`.
        // If a working protective stop already exists in account.Orders (e.g. placed from
        // TradingView/Tradovate before the guard started), the FSM is seeded as Protected
        // instead of Unprotected so the grace timer does NOT fire a duplicate auto-stop.
        private void SeedFsmsForExistingPositions(Account account)
        {
            if (account == null) return;
            if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(account.Name)) return;

            try
            {
                foreach (Position pos in account.Positions)
                {
                    if (pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0) continue;
                    string instrument = pos.Instrument != null ? pos.Instrument.FullName : null;
                    if (string.IsNullOrEmpty(instrument)) continue;

                    string key = FsmKey(account.Name, instrument);
                    if (_guardFsms.ContainsKey(key)) continue; // already tracked

                    var fsm = new PositionGuardFsm(account.Name, instrument)
                    {
                        PositionSide = pos.MarketPosition,
                        PositionQuantity = pos.Quantity,
                        EntryTime = DateTime.UtcNow,
                        State = GuardFsmState.Unprotected
                    };

                    // Scan existing working orders for protective stops on the opposite side.
                    // If found, seed the FSM as Protected (or ProtectedPending) so the grace
                    // timer does not place a duplicate auto-stop on an already-covered position.
                    //
                    // P1-36: every matching stop counts, not just the first one found. This loop
                    // used to `break` on the first hit, so seeding a 6-lot position covered by two
                    // 3-lot stops -- exactly what a re-arm or a restart mid-trade walks into --
                    // recorded 3 of 6 and immediately attached a third stop for the phantom delta.
                    bool anyPending = false;
                    foreach (Order o in account.Orders)
                    {
                        if (o == null || o.Instrument == null) continue;
                        if (!string.Equals(o.Instrument.FullName, instrument, StringComparison.OrdinalIgnoreCase)) continue;
                        if (!IsStopType(o) || !IsProtectiveSide(o, pos.MarketPosition)) continue;
                        // P0-60: coverage, so ProvidesCoverage -- a stop already being cancelled
                        // is not cover, and seeding the FSM with one reports a naked position as
                        // protected.
                        if (!ProvidesCoverage(o.OrderState)) continue;
                        fsm.AddRecognizedStop(o);
                        if (o.OrderState != OrderState.Working) anyPending = true;
                    }
                    if (fsm.CoveredQuantity > 0)
                    {
                        // Pending drags the whole position down to ProtectedPending: a stop that
                        // is not yet Working is not yet cover.
                        fsm.State = anyPending ? GuardFsmState.ProtectedPending : GuardFsmState.Protected;
                    }

                    // Arm a one-shot grace timer only if still Unprotected (no existing stop found).
                    if (fsm.State == GuardFsmState.Unprotected && _config.StopGuard.StopAttachSeconds > 0)
                    {
                        ArmGraceTimer(fsm, account, instrument, _config.StopGuard.StopAttachSeconds * 1000);
                    }
                    else if (fsm.State != GuardFsmState.Unprotected && fsm.CoveredQuantity < fsm.PositionQuantity)
                    {
                        // Existing stop is under-sized; arm the grace timer for the uncovered delta.
                        fsm.GraceEmitted = false;
                        if (!fsm.GracePending)
                        {
                            ArmGraceTimer(fsm, account, instrument, _config.StopGuard.StopAttachSeconds * 1000);
                        }
                    }

                    _guardFsms[key] = fsm;
                    LogEvent(account.Name, "FSM_SEED",
                        $"Seeded FSM for existing position {key} -> {fsm.State} (qty {fsm.PositionQuantity})");
                }
            }
            catch (Exception ex)
            {
                LogEvent(account.Name, "ERROR", "SeedFsmsForExistingPositions failed: " + ex.Message);
            }
        }

        private void UnsubscribeFromAccount(Account account)
        {
            if (account == null) return;
            if (!_subscribedAccounts.Contains(account.Name)) return;

            account.PositionUpdate -= OnPositionUpdate;
            account.OrderUpdate -= OnOrderUpdate;
            account.ExecutionUpdate -= OnExecutionUpdate;
            account.AccountItemUpdate -= OnAccountItemUpdate;

            _subscribedAccounts.Remove(account.Name);
            LogEvent("SYSTEM", "UNSUBSCRIBE", $"Unsubscribed from account events for: {account.Name}");
        }

        // -
        // CONFIG & STATE PERSISTENCE
        // -

        private void LoadConfig()
        {
            try
            {
                if (File.Exists(_configFile))
                {
                    string json = File.ReadAllText(_configFile);
                    _config = JsonConvert.DeserializeObject<RiskConfig>(json) ?? new RiskConfig();
                    _mode = _config.Mode;
                }
                else
                {
                    _config = new RiskConfig();
                    string json = JsonConvert.SerializeObject(_config, Formatting.Indented);
                    File.WriteAllText(_configFile, json);
                }

                // Cache parsed windows (Fix 12)
                _parsedWindows.Clear();
                if (_config.WindowsET != null)
                {
                    foreach (var win in _config.WindowsET)
                    {
                        var pw = new ParsedWindow
                        {
                            Start = TimeSpan.Parse(win.Start),
                            End = TimeSpan.Parse(win.End),
                            Days = new HashSet<DayOfWeek>()
                        };
                        foreach (var d in win.Days)
                        {
                            if (Enum.TryParse(d, out DayOfWeek dow))
                            {
                                pw.Days.Add(dow);
                            }
                        }
                        _parsedWindows.Add(pw);
                    }
                }
            }
            catch (Exception ex)
            {
                LogEvent("SYSTEM", "ERROR", $"Failed to load config: {ex.Message}");
            }
        }

        /// <summary>Called by the MCP bridge to hot-reload state.json into the live instance.</summary>
        public void ReloadPersistedState() => LoadPersistedState();

        private void LoadPersistedState()
        {
            lock (_stateLock)
            {
                try
                {
                    if (File.Exists(_stateFile))
                    {
                        string json = File.ReadAllText(_stateFile);
                        var data = JsonConvert.DeserializeObject<PersistedStateData>(json);
                        if (data != null)
                        {
                            // FR-30/31: never rehydrate the armed flag from persisted state.
                            // Lockouts persist, but armed state must be set fresh each session via Preflight().
                            // Previously: _isArmed = data.IsArmed;  (could silently re-arm across restarts)
                            _isArmed = false;
                            // FR-29: shadow-session counter IS rehydrated (it accumulates across sessions).
                            // P1-37: rehydrate the date marker in the same breath. These two are one
                            // fact -- "N sessions counted, the most recent being D" -- and restoring
                            // the count without the date made every restart look like a new day, so
                            // the counter climbed on restarts rather than on sessions. Note the
                            // contrast with _isArmed three lines up: that is deliberately NOT
                            // restored so a restart cannot silently re-arm. The same care simply was
                            // never applied to the gate that authorises arming.
                            _shadowSessionsCompleted = data.ShadowSessionsCompleted;
                            _lastShadowSessionDate = data.LastShadowSessionDate;
                            if (data.LockedOutAccounts != null)
                            {
                                foreach (var accName in data.LockedOutAccounts)
                                {
                                    if (!_accountStates.TryGetValue(accName, out var state))
                                    {
                                        state = new AccountState(accName);
                                        _accountStates[accName] = state;
                                    }
                                    state.IsLockedOut = true; // P2-92: persisted lockout came from a real session; authority is restored from AccountsData.
                                }
                            }
                            if (data.AccountsData != null)
                            {
                                foreach (var kvp in data.AccountsData)
                                {
                                    if (!_accountStates.TryGetValue(kvp.Key, out var state))
                                    {
                                        state = new AccountState(kvp.Key);
                                        _accountStates[kvp.Key] = state;
                                    }
                                    // P1-54: restore the deadline. Older state files predate this
                                    // field and deserialize it as MinValue, which reads as "no
                                    // deadline" -- the previous behaviour -- so an upgrade cannot
                                    // shorten a lockout that was meant to hold.
                                    state.LockoutUntil = kvp.Value.LockoutUntil;
                                    state.LockoutWasShadowOnly = kvp.Value.LockoutWasShadowOnly;
                                    state.LastSessionDate = kvp.Value.LastSessionDate;
                                    state.TradesToday = kvp.Value.TradesToday;
                                    state.ConsecutiveLosses = kvp.Value.ConsecutiveLosses;
                                    state.PeakEquity = kvp.Value.PeakEquity;
                                    state.LastRealizedPnL = kvp.Value.LastRealizedPnL;
                                    state.SessionStartRealizedPnL = kvp.Value.SessionStartRealizedPnL;
                                    state.CumulativeRealizedPnL = kvp.Value.CumulativeRealizedPnL;
                                    state.FirmTrailingPeak = kvp.Value.FirmTrailingPeak;
                                    state.FirmFloorLocked = kvp.Value.FirmFloorLocked;
                                    state.FirmDailyDate = kvp.Value.FirmDailyDate;
                                    state.FirmDailyStartRealized = kvp.Value.FirmDailyStartRealized;
                                    state.FirmStartingBalance = kvp.Value.FirmStartingBalance;
                                }
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    LogEvent("SYSTEM", "ERROR", $"Failed to load persisted state: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Every disk write this addon makes goes through here (P1-12). Two reasons it is a
        /// funnel rather than a convention: the observer seam gives the suite one place to catch
        /// a write that happened under `_stateLock`, and the swallow-and-continue policy for I/O
        /// failures is stated once instead of in four `catch {}` blocks that had drifted apart.
        /// Callers must have released `_stateLock` first -- see <see cref="CapturePersistedState"/>
        /// for the capture-then-write split that makes that possible.
        /// </summary>
        private void WriteFileOutsideLock(string label, Action write)
        {
#if TESTING
            var obs = FileWriteObserver;
            if (obs != null) obs(label);
#endif
            try { write(); } catch { }
        }

        /// <summary>
        /// Builds the persisted-state payload under `_stateLock` and returns it WITHOUT touching
        /// the disk. The JSON encode and the write are the caller's job, after the lock is
        /// released. Splitting it this way is the whole of P1-12's state half: the old method
        /// took the lock and then wrote inside it, so every one of its callers -- including the
        /// one on the position-update hot path -- serialised order processing behind a disk write.
        /// </summary>
        private PersistedStateData CapturePersistedState()
        {
            lock (_stateLock)
            {
                try
                {
                    var lockedOut = _accountStates.Values.Where(s => s.IsLockedOut).Select(s => s.AccountName).ToList();
                    var accountsData = new Dictionary<string, AccountPersistedData>();
                    foreach (var state in _accountStates.Values)
                    {
                        accountsData[state.AccountName] = new AccountPersistedData
                        {
                            LastSessionDate = state.LastSessionDate,
                            TradesToday = state.TradesToday,
                            ConsecutiveLosses = state.ConsecutiveLosses,
                            PeakEquity = state.PeakEquity,
                            LastRealizedPnL = state.LastRealizedPnL,
                            SessionStartRealizedPnL = state.SessionStartRealizedPnL,
                            FirmTrailingPeak = state.FirmTrailingPeak,
                            CumulativeRealizedPnL = state.CumulativeRealizedPnL,
                            FirmFloorLocked = state.FirmFloorLocked,
                            FirmDailyDate = state.FirmDailyDate,
                            FirmDailyStartRealized = state.FirmDailyStartRealized,
                            FirmStartingBalance = state.FirmStartingBalance,
                            LockoutUntil = state.LockoutUntil,   // P1-54
                            LockoutWasShadowOnly = state.LockoutWasShadowOnly
                        };
                    }
                    return new PersistedStateData
                    {
                        IsArmed = _isArmed,
                        ShadowSessionsCompleted = _shadowSessionsCompleted,
                        LastShadowSessionDate = _lastShadowSessionDate,
                        LockedOutAccounts = lockedOut,
                        AccountsData = accountsData,
                        Timestamp = DateTime.UtcNow
                    };
                }
                catch (Exception ex)
                {
                    LogEvent("SYSTEM", "ERROR", $"Failed to capture persisted state: {ex.Message}");
                    return null;
                }
            }
        }

        /// <summary>Serialises and writes a captured payload. Must run with `_stateLock` released.</summary>
        private void WritePersistedState(PersistedStateData data)
        {
            if (data == null) return;
            WriteFileOutsideLock("state", () =>
                File.WriteAllText(_stateFile, JsonConvert.SerializeObject(data, Formatting.Indented)));
        }

        /// <summary>
        /// Capture + write, for the handful of callers that are genuinely outside the lock and
        /// genuinely need the state on disk before they return -- shutdown, arming, manual
        /// unlock. Anything on an event path should set `_stateDirty` and let the sweep batch it.
        /// </summary>
        private void SavePersistedState()
        {
            WritePersistedState(CapturePersistedState());
        }

        // -
#if !TESTING
        // WINDOW INTERCEPTION (UI INJECTION)
        // -

        protected override void OnWindowCreated(Window window)
        {
            ControlCenter cc = window as ControlCenter;
            if (cc == null) return;
            _controlCenter = cc;

            cc.Dispatcher.InvokeAsync(() =>
            {
                try
                {
                    NTMenuItem existingMenuItem = cc.FindFirst("ControlCenterMenuItemNew") as NTMenuItem;
                    if (existingMenuItem == null)
                    {
                        LogEvent("SYSTEM", "UI_ERROR", "ControlCenterMenuItemNew not found. Menu injection skipped.");
                        return;
                    }

                    _myMenuItem = new NTMenuItem
                    {
                        Header = "Risk Guard Dashboard",
                        Style = Application.Current.TryFindResource("MainMenuItem") as Style
                    };

                    _myMenuItem.Click += OnMenuItemClick;
                    existingMenuItem.Items.Add(_myMenuItem);

                    LogEvent("SYSTEM", "UI_INJECT", "Risk Guard Dashboard added to Control Center 'New' menu.");
                }
                catch (Exception ex)
                {
                    LogEvent("SYSTEM", "UI_ERROR", "Failed to inject menu item: " + ex.Message);
                }
            });
        }

        protected override void OnWindowDestroyed(Window window)
        {
            ControlCenter cc = window as ControlCenter;
            if (cc == null) return;
            _controlCenter = cc;

            if (_myMenuItem != null)
            {
                NTMenuItem existingMenuItem = cc.FindFirst("ControlCenterMenuItemNew") as NTMenuItem;
                existingMenuItem?.Items.Remove(_myMenuItem);
                _myMenuItem = null;
            }
        }

        private void OnMenuItemClick(object sender, RoutedEventArgs e)
        {
            try
            {
                var win = new RiskGuardWindow(this);
                if (_controlCenter != null)
                {
                    win.Owner = _controlCenter;
                }
                win.Show();
            }
            catch (Exception ex)
            {
                LogEvent("SYSTEM", "UI_ERROR", "Failed to open dashboard window: " + ex.Message);
            }
        }
#endif

        // -
        // EVENT HANDLERS
        // -

        private void OnConnectionStatusUpdate(object sender, ConnectionStatusEventArgs e)
        {
            LogEvent("SYSTEM", "CONNECTION_CHANGE", $"Connection status: {e.Status}, Connection: {e.Connection?.Options?.Name}");
            
            // Re-check, subscribe, and audit open positions for any account returning online
            lock (_stateLock)
            {
                foreach (Account account in Account.All)
                {
                    SubscribeToAccount(account);
                    if (e.Status.ToString() == "Connected")
                    {
                        foreach (Position pos in account.Positions)
                        {
                            if (pos.MarketPosition != MarketPosition.Flat && pos.Instrument != null)
                            {
                                AuditPosition(account, pos);
                            }
                        }
                    }
                }
            }
        }

        private void AuditPosition(Account account, Position pos)
        {
            if (account == null || pos == null || pos.Instrument == null) return;
            ExecutePositionUpdateDetails(account, pos);
        }




        /// <summary>
        /// "Is this account gated?" -- the question the MCP bridge asks before placing an order
        /// (PlaceOrder, PlaceOcoOrder, PlaceAtmOrder) and answers on GET /api/lockout.
        ///
        /// P1-100: this returned the raw `IsLockedOut` flag, which is NOT the predicate the guard
        /// enforces. Wrong in both directions, both measured or derivable from live logs:
        ///   * a SHADOW-only observation refused every real order on a sim account under evaluation;
        ///   * a TIMED manual lockout (deadline set, flag not) reported the account free to trade.
        /// It now shares LockoutBinds with CanTrade, so the reported gate and the enforced gate are
        /// the same predicate rather than two that agree by inspection. F-9's lesson, applied to a
        /// reader instead of a rule display: derive the report FROM the enforcer.
        /// </summary>
        public bool IsAccountLocked(string accountName)
        {
            lock (_stateLock)
            {
                return LockoutBinds(accountName);
            }
        }

        public bool IsGuardProtecting(string accountName)
        {
            lock (_stateLock)
            {
                if (!_isArmed)
                    return false;

                if (!string.Equals(GetMode(), "live", StringComparison.OrdinalIgnoreCase))
                    return false;

                if (_subscribedAccounts == null || !_subscribedAccounts.Contains(accountName))
                    return false;

                if (_config == null)
                    return false;

                if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accountName))
                    return false;

                StopGuardConfig stopGuard = _config.StopGuard;
                if (stopGuard == null)
                    return false;

                bool? enabled = GetStopGuardEnabled(stopGuard);
                if (enabled.HasValue && !enabled.Value)
                    return false;

                if (stopGuard.StopAttachSeconds < 0)
                    return false;

                return true;
            }
        }

        private static bool? GetStopGuardEnabled(StopGuardConfig stopGuard)
        {
            if (stopGuard == null)
                return null;

            System.Type type = typeof(StopGuardConfig);
            string[] candidateNames = { "Enabled", "IsEnabled", "Active", "IsActive" };

            foreach (string name in candidateNames)
            {
                System.Reflection.PropertyInfo prop = type.GetProperty(name, System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                if (prop != null && prop.PropertyType == typeof(bool))
                {
                    object value = prop.GetValue(stopGuard);
                    if (value is bool b)
                        return b;
                }

                System.Reflection.FieldInfo field = type.GetField(name, System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                if (field != null && field.FieldType == typeof(bool))
                {
                    object value = field.GetValue(stopGuard);
                    if (value is bool b)
                        return b;
                }
            }

            return null;
        }

        // P1-13 (fail-open half). Every guard event handler used to read
        //
        //     var dispatcher = Application.Current?.Dispatcher;
        //     if (dispatcher == null) return;
        //
        // so whenever `Application.Current` was null -- early startup before the WPF app object
        // exists, or a headless NT8 -- the guard received every position, order, execution and
        // account-item event and SILENTLY DISCARDED ALL OF THEM. No FSM, no grace timer, no rule
        // evaluation, no log line, and `/api/riskguard/version` still reporting armed and
        // guarding. A total protection outage that announces itself as healthy.
        //
        // Running the work inline instead is what OnGraceTimerCallback already did, and it is the
        // only defensible answer: the guard's job does not depend on a UI being up. The threading
        // inversion proper -- evaluate on the caller's thread, marshal only broker calls -- is the
        // other half of P1-13 and waits on the S5/S6/S8/S9 concurrency coverage, because it turns
        // a set of handlers the dispatcher had implicitly serialised into genuinely concurrent
        // ones.
        private int _noDispatcherWarned;

        // P1-13: the guard now evaluates on the caller's thread, not the WPF dispatcher.
        // The concurrent stress test (TestP113_ConcurrentGuardEventsDoNotCorruptState) proved
        // that _stateLock already protects the dictionaries under concurrent access. The copier
        // has been submitting orders off the event thread in production. The only thing that
        // needs the dispatcher is broker calls (Flatten/Cancel/Submit), and those are inside
        // ProcessAction -- which is called from within the guard work, so the marshalling
        // happens at the broker-call boundary, not the event-handler boundary.
        private void RunGuardWork(string label, Action work)
        {
            work();
        }

        private void OnPositionUpdate(object sender, PositionEventArgs e)
        {
            RunGuardWork("PositionUpdate", () => ExecutePositionUpdate(sender, e));
        }

        internal void ExecutePositionUpdate(object sender, PositionEventArgs e)
        {
            if (sender is Account acc && e?.Position != null)
            {
                ExecutePositionUpdateDetails(acc, e.Position);
            }
        }

        internal void ExecutePositionUpdateDetails(Account account, Position pos)
        {
            List<GuardAction> actions = null;
            List<GuardAction> aggregateActions = null;   // P2-107: its own scope, see below.
            List<string> aggregateScope = null;
            try
            {
                string accountName = account.Name;
                string instrument = pos.Instrument.FullName;
                MarketPosition marketPosition = pos.MarketPosition;
                int quantity = pos.Quantity;
                double averagePrice = pos.AveragePrice;
                double unrealizedPnL = 0.0;
                try { unrealizedPnL = pos.GetUnrealizedProfitLoss(PerformanceUnit.Currency); } catch { }

                lock (_stateLock)
                {
                    if (!_accountStates.TryGetValue(accountName, out var state))
                    {
                        state = new AccountState(accountName);
                        state.SessionStartRealizedPnL = account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
                        state.LastRealizedPnL = state.SessionStartRealizedPnL;
                        _accountStates[accountName] = state;
                    }

                    bool changed = state.UpdatePosition(account, pos.Instrument, marketPosition, quantity, averagePrice, unrealizedPnL, _config);

                    if (changed)
                    {
                        // P1-12: was a synchronous SavePersistedState() here -- a disk write under
                        // _stateLock on the hot path, once per position change, bypassing the very
                        // batching mechanism the sweep already uses. Mark it and let the sweep
                        // flush it. The batching window costs at most one sweep interval of
                        // staleness on restart, against stalling every order event behind the disk.
                        _stateDirty = true;
                    }

                    LogEvent(accountName, "POSITION_UPDATE", new JObject
                    {
                        { "instrument", instrument },
                        { "marketPosition", marketPosition.ToString() },
                        { "quantity", quantity },
                        { "averagePrice", averagePrice },
                        { "unrealizedPnL", unrealizedPnL }
                    });

                    // - Per-position guard FSM (-6) -
                    // On flat->nonflat: create/reset FSM, arm grace timer, consume any pending stop.
                    // On nonflat->flat: transition to Flat, cancel grace, cancel orphan auto-stop.
                    UpdateFsmOnPosition(account, instrument, marketPosition, quantity);

                    // -- Event-driven rule evaluation (Phase 2: no longer on the sweep) --
                    // EvaluateRules fires here on every position change. The sweep no
                    // longer calls EvaluateRules; all per-account rules are event-driven.
                    actions = EvaluateRules(account, state);

                    // -- Aggregate sizing (event-driven via PositionUpdate) --
                    // Scan all accounts' positions instantly on any position change.
                    //
                    // P2-107: kept in its OWN list rather than folded into `actions`. It iterates
                    // every subscribed account while the rules above looked at one, so the two
                    // have different evaluated scopes and merging them would make one producer's
                    // silence clear the other's records -- which is the de-duplication doing
                    // nothing while still passing any test that drives a single account.
                    //
                    // The cost of the split is that an aggregate flatten and a per-account
                    // flatten for the same account are no longer coalesced into one call. Two
                    // flattens against one account are idempotent at the broker; a de-duplicator
                    // that clears itself is not.
                    aggregateActions = EvaluateAggregateSizing();
                    aggregateScope = AggregateEvaluatedAccounts();

                    // -- Lockout phase enforcement (event-driven via PositionUpdate) --
                    // When a position goes flat, check if the lockout can advance to Confirmed.
                    // When a position appears while locked, emit the phased flatten/cancel actions.
                    var lockoutActions = EvaluateLockoutPhase(account, state);
                    if (lockoutActions != null && lockoutActions.Count > 0)
                    {
                        if (actions == null) actions = new List<GuardAction>();
                        actions.AddRange(lockoutActions);
                    }
                }

                // Lock released. Send anything the FSM teardown queued (P1-35) before running
                // the actions, so an orphaned stop dies before any new order is placed.
                DrainPendingCancels();

                // P1-19 coalescing and P2-107 de-duplication both live in DispatchActions now.
                // The scope is this ONE account: EvaluateRules and EvaluateLockoutPhase looked at
                // no other.
                if (actions != null)
                    DispatchActions(actions, "PositionUpdate", new List<string> { account.Name });

                // Aggregate sizing looked at every subscribed account, so its silence about an
                // account is evidence about that account -- which is exactly what the separate
                // scope buys.
                if (aggregateActions != null || aggregateScope != null)
                    DispatchActions(aggregateActions, "AggregateSizing", aggregateScope);
            }
            catch (Exception ex)
            {
                LogEvent("SYSTEM", "ERROR", $"Error handling OnPositionUpdate: {ex.Message}");
            }
        }

        private void OnExecutionUpdate(object sender, ExecutionEventArgs e)
        {
            RunGuardWork("ExecutionUpdate", () => ExecuteExecutionUpdate(sender, e));
        }

        internal void ExecuteExecutionUpdate(object sender, ExecutionEventArgs e)
        {
            lock (_stateLock)
            {
                try
                {
                    Account account = (Account)sender;
                    string accountName = account.Name;
                    string instrument = e.Execution.Instrument.FullName;
                    string orderId = e.Execution.Order != null ? e.Execution.Order.Id.ToString() : "N/A";
                    int quantity = e.Execution.Quantity;
                    double price = e.Execution.Price;
                    string action = e.Execution.Order?.OrderAction.ToString() ?? "N/A";

                    if (!_accountStates.TryGetValue(accountName, out var state))
                    {
                        state = new AccountState(accountName);
                        _accountStates[accountName] = state;
                    }

                    state.RecordExecution(instrument, action, quantity, price);

                    LogEvent(accountName, "EXECUTION_UPDATE", new JObject
                    {
                        { "instrument", instrument },
                        { "orderId", orderId },
                        { "action", action },
                        { "quantity", quantity },
                        { "price", price }
                    });
                }
                catch (Exception ex)
                {
                    LogEvent("SYSTEM", "ERROR", $"Error handling OnExecutionUpdate: {ex.Message}");
                }
            }
        }

        // -- AccountItemUpdate: fires when RealizedPnL, UnrealizedPnL, CashValue, NetLiquidation change --
        // This replaces the sweep's PnL polling with instant event-driven PnL rules.
        private void OnAccountItemUpdate(object sender, AccountItemEventArgs e)
        {
            RunGuardWork("AccountItemUpdate", () => ExecuteAccountItemUpdate(sender, e));
        }

        internal void ExecuteAccountItemUpdate(object sender, AccountItemEventArgs e)
        {
            List<GuardAction> actions = null;
            try
            {
                Account account = (Account)sender;
                string accountName = account.Name;

                if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accountName)) return;

                lock (_stateLock)
                {
                    if (!_accountStates.TryGetValue(accountName, out var state))
                        return;

                    // Only react to PnL-related items
                    if (e.AccountItem == AccountItem.RealizedProfitLoss)
                    {
                        double rawRealized = e.Value;
                        double newRealizedPnL = rawRealized - state.SessionStartRealizedPnL;

                        if (Math.Abs(newRealizedPnL - state.RealizedPnL) > 0.001)
                        {
                            double tradePnL = newRealizedPnL - state.RealizedPnL;
                            state.RecordRealizedDelta(tradePnL, _config);

                            state.LastRealizedPnL = rawRealized;
                            state.RealizedPnL = newRealizedPnL;

                            // Apply cooldown if consecutive loss limit breached
                            if (state.ConsecutiveLosses >= _config.Overtrading.MaxConsecutiveLosses && _config.Overtrading.CooldownMinutes > 0)
                            {
                                state.CooldownUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.CooldownMinutes);
                            }
                            _stateDirty = true;
                        }

                        // Evaluate PnL-based rules instantly
                        actions = EvaluatePnLRules(account, state);
                    }
                    else if (e.AccountItem == AccountItem.UnrealizedProfitLoss ||
                             e.AccountItem == AccountItem.NetLiquidation ||
                             e.AccountItem == AccountItem.CashValue)
                    {
                        // Update unrealized PnL and evaluate trailing DD / firm mirror
                        state.UnrealizedPnL = account.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar);

                        // Update peak equity for trailing DD
                        double currentPnL = state.RealizedPnL + state.UnrealizedPnL;
                        if (currentPnL > state.PeakEquity)
                            state.PeakEquity = currentPnL;

                        actions = EvaluatePnLRules(account, state);

                        // Firm mirror on PnL change
                        if (_config.FirmMirror != null && _config.FirmMirror.Enabled)
                        {
                            DateTime nowEt = TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, _etZone);
                            // FirmMirror's daily boundary is expressed in UTC
                            // (FirmMirror.DailyResetHourUtc), so pass UTC. This previously passed
                            // nowEt, which the method silently ignored in favour of DateTime.UtcNow.
                            var firmActions = EvaluateFirmMirror(account, state, DateTime.UtcNow);
                            if (firmActions != null && firmActions.Count > 0)
                            {
                                if (actions == null) actions = new List<GuardAction>();
                                actions.AddRange(firmActions);
                            }
                        }
                    }
                }

                // P2-107. This is the path the defect was MEASURED on: PEAK_GIVEBACK_BREACH,
                // raised by EvaluatePnLRules, re-emitted 7 times in ~20 seconds because a PnL
                // change re-evaluates and the giveback condition was still true. Scope is the one
                // account whose PnL moved.
                if (actions != null)
                    DispatchActions(actions, "AccountItemUpdate", new List<string> { accountName });
            }
            catch (Exception ex)
            {
                LogEvent("SYSTEM", "ERROR", "Error handling OnAccountItemUpdate: " + ex.Message);
            }
        }

        // Evaluate PnL-based rules (DailyLoss, TrailingDrawdown) - called from AccountItemUpdate.
        internal List<GuardAction> EvaluatePnLRules(Account account, AccountState stateModel)
        {
            var actions = new List<GuardAction>();
            if (!_isArmed) return actions;
            if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(stateModel.AccountName)) return actions;

            var profile = GetResolvedProfile(account);
            if (profile == null) return actions;

            double currentPnL = stateModel.RealizedPnL + stateModel.UnrealizedPnL;

            // Daily Loss
            if (currentPnL < -profile.DailyLossLimit)
            {
                actions.Add(new GuardAction
                {
                    AccountName = stateModel.AccountName,
                    ActionType = GuardActionType.FlattenPosition,
                    RuleId = "DAILY_LOSS_BREACH"
                });
                if (!stateModel.IsLockedOut)
                {
                    MarkRuleLockout(stateModel, "DAILY_LOSS_BREACH");
                    if (_config.PnLRules.LockoutMinutes > 0)
                        stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.PnLRules.LockoutMinutes);
                    _stateDirty = true;
                }
            }

            // Trailing Drawdown
            //
            // P1-18: FirmMirror implements the firm's real trailing model, whose high-water mark
            // typically does NOT reset daily, while the rule below runs against a session-reset
            // PeakEquity. Where the firm rule is actually in effect for this account it owns the
            // decision and this one would double-fire on the same event.
            //
            // Keying on FirmMirror.Enabled alone would be a protection *removal*: on a config
            // where FirmMirror is enabled but its TrailingDD sub-rule is off and the account is
            // unmapped -- the shape observed live on 2026-08-07 -- that would skip the rule below
            // while the firm rule evaluates nothing, leaving the account with no trailing-drawdown
            // cover at all. So resolve what is actually in effect for THIS account.
            bool firmTrailingInEffect = false;
            if (_config.FirmMirror != null && _config.FirmMirror.Enabled)
            {
                var fmEff = ResolveEffectiveFirmConfig(_config.FirmMirror, stateModel.AccountName);
                firmTrailingInEffect = fmEff != null && fmEff.TrailingDD != null && fmEff.TrailingDD.Enabled;
            }

            // Keep tracking the peak either way, so the value stays meaningful if the firm rule
            // is later disabled and this rule resumes ownership.
            if (currentPnL > stateModel.PeakEquity)
                stateModel.PeakEquity = currentPnL;
            if (!firmTrailingInEffect && currentPnL < stateModel.PeakEquity - profile.TrailingDrawdown)
            {
                actions.Add(new GuardAction
                {
                    AccountName = stateModel.AccountName,
                    ActionType = GuardActionType.FlattenPosition,
                    RuleId = "TRAILING_DD_BREACH"
                });
                if (!stateModel.IsLockedOut)
                {
                    MarkRuleLockout(stateModel, "TRAILING_DD_BREACH");
                    if (_config.PnLRules.LockoutMinutes > 0)
                        stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.PnLRules.LockoutMinutes);
                    _stateDirty = true;
                }
            }

            // Prop Firm Protection Suite Integrations (News Shield, Target Profit Lock, Peak Giveback)
            var propSuite = PropFirmProtectionSuite.Instance;
            if (propSuite != null && propSuite.Config != null)
            {
                // Peak Open Gain tracks the running peak of unrealized PnL for
                // the current open position. It resets when the account is flat
                // and only rises while a position is open.
                bool accountIsFlat = true;
                foreach (var pos in stateModel.Positions.Values)
                {
                    if (pos.MarketPosition != MarketPosition.Flat)
                    {
                        accountIsFlat = false;
                        break;
                    }
                }

                if (!accountIsFlat)
                {
                    if (stateModel.UnrealizedPnL > stateModel.PeakOpenGain)
                    {
                        // New peak = new episode. Re-arm the giveback latch.
                        stateModel.PeakOpenGain = stateModel.UnrealizedPnL;
                        stateModel.PeakGivebackTriggered = false;
                        stateModel.PeakGivebackLastTriggerUnrealized = double.NaN;
                        _stateDirty = true;
                    }
                }
                else
                {
                    bool needsReset = stateModel.PeakOpenGain != 0.0
                        || stateModel.PeakGivebackTriggered
                        || !double.IsNaN(stateModel.PeakGivebackLastTriggerUnrealized);
                    if (needsReset)
                    {
                        stateModel.PeakOpenGain = 0.0;
                        stateModel.PeakGivebackTriggered = false;
                        stateModel.PeakGivebackLastTriggerUnrealized = double.NaN;
                        _stateDirty = true;
                    }
                }

                if (propSuite.Config.EnableNewsShield && propSuite.IsInNewsWindow(DateTime.UtcNow, propSuite.Config.NewsBufferMinutesBefore, propSuite.Config.NewsBufferMinutesAfter))
                {
                    actions.Add(new GuardAction
                    {
                        AccountName = stateModel.AccountName,
                        ActionType = GuardActionType.FlattenPosition,
                        RuleId = "NEWS_SHIELD_LOCKOUT"
                    });
                    if (!stateModel.IsLockedOut)
                    {
                        MarkRuleLockout(stateModel, "NEWS_SHIELD_LOCKOUT");
                    }
                }

                // P1-17: EvaluationTargetProfit is a cumulative, multi-day evaluation target.
                // Feeding it the session-scoped RealizedPnL meant it only fired if the whole
                // target was cleared in a single day. TotalRealizedPnL = banked + this session.
                if (propSuite.EvaluateProfitTargetLock(stateModel.TotalRealizedPnL, propSuite.Config))
                {
                    actions.Add(new GuardAction
                    {
                        AccountName = stateModel.AccountName,
                        ActionType = GuardActionType.FlattenPosition,
                        RuleId = "EVALUATION_TARGET_REACHED"
                    });
                    if (!stateModel.IsLockedOut)
                    {
                        MarkRuleLockout(stateModel, "EVALUATION_TARGET_REACHED");
                    }
                }

                if (!accountIsFlat && stateModel.PeakOpenGain > 0)
                {
                    if (propSuite.EvaluatePeakEquityGiveback(stateModel.PeakOpenGain, stateModel.UnrealizedPnL, propSuite.Config))
                    {
                        bool alreadyTriggered = stateModel.PeakGivebackTriggered;
                        bool worsenedSinceTrigger = alreadyTriggered
                            && stateModel.UnrealizedPnL < stateModel.PeakGivebackLastTriggerUnrealized;

                        // Fire on the first breach of the episode, and re-fire if the
                        // position gives back further than the prior trigger point.
                        // This prevents a silently-failed flatten from leaving the
                        // position unprotected as the loss continues to deepen.
                        if (!alreadyTriggered || worsenedSinceTrigger)
                        {
                            actions.Add(new GuardAction
                            {
                                AccountName = stateModel.AccountName,
                                ActionType = GuardActionType.FlattenPosition,
                                RuleId = "PEAK_GIVEBACK_BREACH"
                            });
                            stateModel.PeakGivebackTriggered = true;
                            stateModel.PeakGivebackLastTriggerUnrealized = stateModel.UnrealizedPnL;
                            _stateDirty = true;
                        }
                    }
                }
            }

            return actions;
        }

        private void OnOrderUpdate(object sender, OrderEventArgs e)
        {
            RunGuardWork("OrderUpdate", () => ExecuteOrderUpdate(sender, e));
        }

        internal void ExecuteOrderUpdate(object sender, OrderEventArgs e)
        {
            List<GuardAction> lockoutActions = null;
            string orderUpdateAccountName = null;   // P2-107 scope; see the dispatch at the end.
            lock (_stateLock)
            {
                try
                {
                    Account account = (Account)sender;
                    string accountName = account.Name;
                    if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accountName))
                    {
                        // Skip entry cancellation for excluded accounts
                    }
                    else if (_accountStates.TryGetValue(accountName, out var stateModel))
                    {
                        // Order Rate Governor: detect rogue strategy order loops.
                        //
                        // P1-52: count TRADING RATE, not order-object churn. Key the one-second
                        // window by OCO group when an order has one, so a bracketed position
                        // decision (e.g. entry + stop + target sharing an OCO id) counts as a
                        // single burst instead of three order objects. Fall back to Order.Id
                        // for ungrouped orders so standalone entries are still counted
                        // individually. This keeps a runaway loop visible: each distinct OCO
                        // group or standalone order adds to the count.
                        //
                        // P2-46: count DISTINCT KEYS, not state transitions. This previously
                        // added a tick for Submitted and another for Accepted -- two states of
                        // the same order -- so a nominal "more than 5 per second" actually fired
                        // at about three real orders per second, inside normal ATM bracket
                        // submission. The live log's "29-32 orders/sec" were transition counts.
                        if (e.Order.OrderState == OrderState.Submitted || e.Order.OrderState == OrderState.Accepted)
                        {
                            DateTime floodNow = DateTime.UtcNow;
                            DateTime floodCutoff = floodNow.AddSeconds(-1);
                            var staleOrderIds = stateModel.RecentOrderIds
                                .Where(kv => kv.Value < floodCutoff).Select(kv => kv.Key).ToList();
                            foreach (var staleId in staleOrderIds) stateModel.RecentOrderIds.Remove(staleId);

                            string floodKey = !string.IsNullOrEmpty(e.Order.Oco)
                                ? e.Order.Oco
                                : (e.Order.Id != null ? e.Order.Id.ToString() : Guid.NewGuid().ToString());

                            if (!stateModel.RecentOrderIds.ContainsKey(floodKey))
                                stateModel.RecentOrderIds[floodKey] = floodNow;

                            int maxPerSecond = (_config.Overtrading != null && _config.Overtrading.MaxOrdersPerSecond > 0)
                                ? _config.Overtrading.MaxOrdersPerSecond : 5;

                            if (stateModel.RecentOrderIds.Count > maxPerSecond)
                            {
                                MarkRuleLockout(stateModel, "ORDER_FLOOD_LOCKOUT");

                                // P1-45: pair the flag with a deadline. The lockout test is
                                // `IsLockedOut || UtcNow < LockoutUntil` -- an OR -- and every
                                // other rule sets a deadline, so setting the flag alone made a
                                // one-second burst lock the account out permanently, persisted
                                // across restarts.
                                if (_config.Overtrading.LockoutMinutes > 0)
                                {
                                    stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.LockoutMinutes);
                                }

                                // P1-44: never cancel a protective order to enforce a rate limit.
                                // Without this guard, a burst whose tripping order happened to be
                                // the stop-loss cancelled the protection AND locked the account
                                // out, leaving an open position naked. The lockout-enforcement
                                // block below has always had this guard; this path did not.
                                if (!IsPositionReducingOrder(e.Order, stateModel))
                                {
                                    // P1-43: queued, not sent -- this block runs under _stateLock.
                                    _pendingCancels.Add(new PendingCancelEntry(account, e.Order, PendingCancelIntent.Intervention));
                                }

                                LogEvent(accountName, "ORDER_FLOOD_LOCKOUT", $"ORDER FLOOD DETECTED: {stateModel.RecentOrderIds.Count} distinct orders in 1s (limit {maxPerSecond}) triggered lockout.");
                            }
                        }

                        // P1-100: the THIRD reader of "is this account locked out", and it read the
                        // raw flag like the other two did. DrainPendingCancels withholds
                        // intervention cancels in shadow, so nothing was actually cancelled -- but
                        // this block still emitted `ENTRY_CANCEL: Cancelled order N because account
                        // is locked out` into interventions.jsonl, which is the audit record, for an
                        // order that was never touched. A log line that asserts an action the mode
                        // does not perform is the same family as P2-101's retry.
                        if (LockoutBinds(accountName, stateModel)
                            || stateModel.ConsecutiveLosses >= _config.Overtrading.MaxConsecutiveLosses)
                        {
                            if (e.Order.OrderState == OrderState.Submitted || e.Order.OrderState == OrderState.Accepted || e.Order.OrderState == OrderState.Working)
                            {
                                if (!IsPositionReducingOrder(e.Order, stateModel))
                                {
                                    if (e.Order.OrderType == OrderType.Limit || e.Order.OrderType == OrderType.StopMarket || e.Order.OrderType == OrderType.StopLimit || e.Order.OrderType == OrderType.Market)
                                    {
                                        // P1-43: queued, not sent -- this whole block runs under _stateLock.
                                        _pendingCancels.Add(new PendingCancelEntry(account, e.Order, PendingCancelIntent.Intervention));
                                        LogEvent(accountName, "ENTRY_CANCEL", $"Cancelled order {e.Order.Id} because account is locked out.");
                                    }
                                }
                            }
                        }
                    }

                    string rawInst = e.Order.Instrument != null ? e.Order.Instrument.FullName : "";
                    string instRoot = rawInst.Split(' ')[0].ToUpper();
                    if (_config.BlockedInstruments != null && _config.BlockedInstruments.Contains(instRoot))
                    {
                        if (e.Order.OrderState == OrderState.Submitted || e.Order.OrderState == OrderState.Accepted || e.Order.OrderState == OrderState.Working)
                        {
                            // P1-43: queued, not sent -- this whole block runs under _stateLock.
                            _pendingCancels.Add(new PendingCancelEntry(account, e.Order, PendingCancelIntent.Intervention));
                            LogEvent(accountName, "BLACKLIST_CANCEL", $"Cancelled order {e.Order.Id} because instrument {instRoot} is blacklisted.");
                        }
                    }
                    if (_config.InstrumentLimits != null && _config.InstrumentLimits.TryGetValue(instRoot, out var perInstCap))
                    {
                        if (e.Order.Quantity > perInstCap.MaxContracts)
                        {
                            if (e.Order.OrderState == OrderState.Submitted || e.Order.OrderState == OrderState.Accepted || e.Order.OrderState == OrderState.Working)
                            {
                                // P1-43: queued, not sent -- this whole block runs under _stateLock.
                                _pendingCancels.Add(new PendingCancelEntry(account, e.Order, PendingCancelIntent.Intervention));
                                LogEvent(accountName, "PER_INSTRUMENT_CAP_CANCEL", $"Cancelled order {e.Order.Id} because quantity {e.Order.Quantity} exceeds {instRoot} cap ({perInstCap.MaxContracts}).");
                            }
                        }
                    }
                    string instrument = e.Order.Instrument.FullName;
                    string orderId = e.Order.Id.ToString();
                    string orderState = e.Order.OrderState.ToString();
                    string orderType = e.Order.OrderType.ToString();
                    double limitPrice = e.Order.LimitPrice;
                    double stopPrice = e.Order.StopPrice;
                    int quantity = e.Order.Quantity;

                    // - Per-position guard FSM (-6) -
                    // Classify this order against the active FSM for (account, instrument).
                    // If no FSM exists yet but this is a protective-side stop, buffer it
                    // in _pendingStops so it is consumed when the position-open event arrives.
                    UpdateFsmOnOrder(account, instrument, e.Order);

                    // -- Lockout phase: advance on order state changes --
                    // When an order goes Cancelled/Filled, check if the lockout can
                    // advance to the next phase (PendingFlatten or Confirmed).
                    // Collect actions here; process OUTSIDE the lock to avoid
                    // re-entrancy corruption when ProcessAction triggers events.
                    //
                    // P2-107: this producer evaluated the account whether or not it turned out to
                    // be locked out, and "not locked out any more" IS the resolution signal. So
                    // the scope is recorded either way; only the evaluation is conditional. Set
                    // it inside the `if` instead and a lockout that ends would leave its records
                    // in place forever, and the next real one would be suppressed unseen.
                    if (_accountStates.TryGetValue(accountName, out var lockState))
                    {
                        orderUpdateAccountName = accountName;
                        if (lockState.IsLockedOut || DateTime.UtcNow < lockState.LockoutUntil)
                        {
                            lockoutActions = EvaluateLockoutPhase(account, lockState);
                        }
                    }

                    LogEvent(accountName, "ORDER_UPDATE", new JObject
                    {
                        { "instrument", instrument },
                        { "orderId", orderId },
                        { "orderState", orderState },
                        { "orderType", orderType },
                        { "orderAction", e.Order.OrderAction.ToString() },
                        { "orderName", e.Order.Name ?? "" },
                        { "quantity", quantity },
                        { "limitPrice", limitPrice },
                        { "stopPrice", stopPrice },
                        // The OCO group id, and the reason this log is the only place it can be
                        // read as a TIMELINE: /api/orders is a snapshot that also skips Filled and
                        // Cancelled orders, so it cannot show the moment one leg fills and its
                        // sibling is pulled -- which is exactly how OCO behaviour is identified.
                        // Empty string means the order carries no OCO group.
                        { "oco", e.Order.Oco ?? "" }
                    });
                }
                catch (Exception ex)
                {
                    LogEvent("SYSTEM", "ERROR", $"Error handling OnOrderUpdate: {ex.Message}");
                }
            }

            // P1-43: send the cancels queued above now that the lock is released. Four Cancel
            // calls sat inside the lock on this path -- the same invariant P1-10 and P1-35 closed
            // elsewhere. The machine check missed them because it only drove the sweep and FSM
            // teardown, never the order-update path.
            DrainPendingCancels();

            // Process lockout actions OUTSIDE the lock to prevent re-entrancy.
            //
            // ⚠️ P2-107 found this site calling ProcessAction in a BARE loop -- the only one of
            // the five that never called CoalesceActions, so P1-19's within-batch merge had never
            // applied on the order-update path at all. Routing it through the dispatcher fixes
            // that as a side effect; it is recorded here because a fix that arrives silently is
            // one nobody can later find the reason for.
            if (orderUpdateAccountName != null)
                DispatchActions(lockoutActions, "OrderUpdate", new List<string> { orderUpdateAccountName });
        }

        internal bool IsPositionReducingOrder(Order order, AccountState stateModel)
        {
            return RiskGuardOrderUtils.IsPositionReducingOrder(order, stateModel);
        }

        internal void OnSafetySweep(object state)
        {
            // The sweep was the worst of the six: with no dispatcher the ENTIRE safety sweep --
            // heartbeat, session reset, state flush, lockout enforcement and the FSM watchdog --
            // was skipped on every tick, forever, silently.
            try
            {
                RunGuardWork("SafetySweep", ExecuteSafetySweep);
            }
            catch (Exception ex)
            {
                LogEvent("SYSTEM", "ERROR", $"Error in OnSafetySweep dispatch: {ex.Message}");
            }
        }

        internal void ExecuteSafetySweep()
        {
            // Decisions taken under the lock, executed after it is released (P1-10).
            var cancelBatches = new List<KeyValuePair<Account, List<Order>>>();
            var deferredCancelBatches = new List<KeyValuePair<Account, List<Order>>>();
            var flattenBatches = new List<KeyValuePair<Account, List<Instrument>>>();
            var sweepActions = new List<GuardAction>();

            // P1-12: the sweep's three disk writes are DECIDED here and performed at the bottom,
            // after the lock has been released and after the broker work. Nothing about a
            // heartbeat file or a log flush is worth delaying a flatten for.
            string heartbeatStamp = null;
            List<string> logsToWrite = null;
            PersistedStateData stateToWrite = null;

            try
            {
                lock (_stateLock)
                {
                    // 1. Heartbeat (liveness) - decide only.
                    if (DateTime.UtcNow - _lastHeartbeatTime >= TimeSpan.FromSeconds(5))
                    {
                        _lastHeartbeatTime = DateTime.UtcNow;
                        heartbeatStamp = DateTime.UtcNow.ToString("o");
                    }

                    // 2. Log flush: the queue is drained under the lock (it is shared state); the
                    // append is not. A ConcurrentQueue drain is microseconds, a file append on a
                    // stalled disk is not bounded at all.
                    logsToWrite = new List<string>();
                    while (_logQueue.TryDequeue(out string logLine))
                        logsToWrite.Add(logLine);

                    // 3. Session reset (check date change - the one remaining time-based rule)
                    DateTime nowEt = TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, _etZone);
                    DateTime currentSessionDate = nowEt.TimeOfDay >= new TimeSpan(18, 0, 0) ? nowEt.Date.AddDays(1) : nowEt.Date;

                    foreach (var accName in _subscribedAccounts)
                    {
                        if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accName)) continue;
                        if (!_accountStates.TryGetValue(accName, out var stateModel)) continue;
                        if (stateModel.LastSessionDate == currentSessionDate) continue;

                        var account = Account.All.FirstOrDefault(a => a.Name == accName);
                        if (account == null) continue;

                        stateModel.LastSessionDate = currentSessionDate;
                        stateModel.TradesToday = 0;
                        stateModel.ConsecutiveLosses = 0;
                        stateModel.PeakEquity = 0.0;
                        stateModel.PeakOpenGain = 0.0;
                        stateModel.PeakGivebackTriggered = false;
                        stateModel.PeakGivebackLastTriggerUnrealized = double.NaN;
                        stateModel.IsLockedOut = false;
                        stateModel.ResetLockoutPhase();   // P2-101
                        // P2-107. A new session is a new set of conditions. Absence-based
                        // clearing would get there on its own, but only after each producer next
                        // evaluates -- and a suppression carried across a session boundary is a
                        // rule that fires on the new day and says nothing.
                        _actionDedup.ClearAccount(accName);
                        stateModel.SessionStartRealizedPnL = account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
                        stateModel.LastRealizedPnL = stateModel.SessionStartRealizedPnL;
                        // P1-17: bank the session that just ended before zeroing it, so the
                        // cumulative evaluation total survives the daily reset.
                        stateModel.CumulativeRealizedPnL += stateModel.RealizedPnL;
                        stateModel.RealizedPnL = 0.0;
                        LogEvent(accName, "SESSION_RESET", $"Session reset for {currentSessionDate:yyyy-MM-dd}");
                        _stateDirty = true;
                    }

                    // FR-29: increment the shadow-session counter once per day when running in shadow mode.
                    // This is the soft gate that RunPreflight() checks before allowing live-mode arming.
                    if (_mode == "shadow" && _lastShadowSessionDate != currentSessionDate)
                    {
                        _lastShadowSessionDate = currentSessionDate;
                        _shadowSessionsCompleted++;
                        _stateDirty = true;
                        LogEvent("SYSTEM", "SHADOW_SESSION",
                            $"Shadow session #{_shadowSessionsCompleted} counted for {currentSessionDate:yyyy-MM-dd} (MinShadowSessions={_config.MinShadowSessions})");
                    }

                    // T6/P0-51: clear the per-account shadow-sweep log flag when the account is
                    // no longer locked out, so the next lockout logs the skip again.
                    foreach (var accName in _subscribedAccounts)
                    {
                        if (_accountStates.TryGetValue(accName, out var stateModel) && !stateModel.IsLockedOut)
                            _lockoutSweepShadowLogged.Remove(accName);
                    }

                    // 4. State persist (batch flush) - capture now, write below. The flag is
                    // cleared here, not after the write: anything that dirties the state while
                    // the write is in flight must set it again and be picked up next sweep, not
                    // be cleared away by a flush that predates it.
                    if (_stateDirty)
                    {
                        stateToWrite = CapturePersistedState();
                        _stateDirty = false;
                    }

                    // 5. Lockout Watchdog - DECIDE ONLY (P1-10).
                    // This block used to call Cancel, Flatten, CreateOrder, Submit and
                    // ProcessAction with _stateLock held, which is the exact invariant the
                    // design doc claims is never violated. The event handlers already use
                    // collect-then-execute; the sweep now does too. Nothing below may touch
                    // Account until the lock is released.
                    foreach (var accName in _subscribedAccounts)
                    {
                        if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accName)) continue;
                        if (!_accountStates.TryGetValue(accName, out var stateModel)) continue;
                        if (!stateModel.IsLockedOut) continue;

                        var account = Account.All.FirstOrDefault(a => a.Name == accName);
                        if (account == null) continue;

                        // P1-11: split by intent. Risk-INCREASING orders go now; orders that
                        // reduce the position - above all the protective stop covering it -
                        // are held back until the flatten is confirmed. Cancelling the stop on
                        // the way in and then failing to flatten is how this path used to
                        // manufacture the naked position it exists to prevent.
                        var riskIncreasing = new List<Order>();
                        var reducing = new List<Order>();
                        foreach (Order o in account.Orders)
                        {
                            if (!OccupiesSlot(o.OrderState)) continue;
                            if (RiskGuardOrderUtils.IsPositionReducingOrder(o, stateModel))
                                reducing.Add(o);
                            else
                                riskIncreasing.Add(o);
                        }
                        if (riskIncreasing.Count > 0)
                            cancelBatches.Add(new KeyValuePair<Account, List<Order>>(account, riskIncreasing));
                        if (reducing.Count > 0)
                            deferredCancelBatches.Add(new KeyValuePair<Account, List<Order>>(account, reducing));

                        var toFlatten = new List<Instrument>();
                        foreach (Position pos in account.Positions)
                        {
                            if (pos.Instrument != null && pos.MarketPosition != MarketPosition.Flat)
                                toFlatten.Add(pos.Instrument);
                        }
                        if (toFlatten.Count > 0)
                            flattenBatches.Add(new KeyValuePair<Account, List<Instrument>>(account, toFlatten));

                        var lockoutActions = EvaluateLockoutPhase(account, stateModel);
                        if (lockoutActions != null && lockoutActions.Count > 0)
                            sweepActions.AddRange(lockoutActions);
                    }

                    // 6. FSM watchdog (log-only diagnostic for stuck FSMs; arms timers, no broker calls)
                    FsmWatchdog();
                }

                // ---- lock released: everything below may talk to the broker ----

                DrainPendingCancels();

                bool acting = IsActingMode();

                if (acting)
                {
                    foreach (var batch in cancelBatches)
                    {
                        try { batch.Key.Cancel(batch.Value); }
                        catch (Exception cex)
                        { LogEvent(batch.Key.Name, "LOCKOUT_CANCEL_FAIL", cex.Message); }
                    }

                    foreach (var batch in flattenBatches)
                    {
                        var account = batch.Key;
                        foreach (var instrument in batch.Value)
                        {
                            try
                            {
                                account.Flatten(new[] { instrument });
                            }
                            catch (Exception fex)
                            {
                                LogEvent(account.Name, "LOCKOUT_FLATTEN_FAIL",
                                    $"{instrument.FullName}: {fex.Message}; falling back to a market close.");

                                // Re-read the position rather than trusting the quantity captured
                                // under the lock - the flatten may have partially succeeded.
                                var pos = account.Positions.FirstOrDefault(
                                    p => p.Instrument != null && p.Instrument.FullName == instrument.FullName);
                                if (pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0)
                                    continue;

                                var closeAction = pos.MarketPosition == MarketPosition.Long
                                    ? OrderAction.Sell : OrderAction.BuyToCover;
                                try
                                {
                                    var closeOrder = account.CreateOrder(
                                        instrument, closeAction, OrderType.Market, TimeInForce.Day,
                                        pos.Quantity, 0, 0, string.Empty, "RiskGuardWatchdogFlatten", null);
                                    if (closeOrder != null) account.Submit(new[] { closeOrder });
                                }
                                catch (Exception sex)
                                { LogEvent(account.Name, "LOCKOUT_CLOSE_FAIL", $"{instrument.FullName}: {sex.Message}"); }
                            }
                        }
                    }

                    // P1-11 phase (c): only now, with the flatten attempted, may the reducing
                    // orders go - and only for instruments that are actually flat. If the flatten
                    // failed, the position is still open and its stop is the only thing standing
                    // between the account and an uncapped loss. Leave it working; the next sweep
                    // will try again.
                    foreach (var batch in deferredCancelBatches)
                    {
                        var account = batch.Key;
                        var stillCovered = new List<string>();
                        var safeToCancel = new List<Order>();

                        foreach (var order in batch.Value)
                        {
                            if (!OccupiesSlot(order.OrderState)) continue;
                            if (order.Instrument == null) continue;

                            var pos = account.Positions.FirstOrDefault(
                                p => p.Instrument != null && p.Instrument.FullName == order.Instrument.FullName);
                            bool flat = pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0;

                            if (flat) safeToCancel.Add(order);
                            else stillCovered.Add(order.Instrument.FullName);
                        }

                        if (safeToCancel.Count > 0)
                        {
                            try { account.Cancel(safeToCancel); }
                            catch (Exception cex)
                            { LogEvent(account.Name, "LOCKOUT_CANCEL_FAIL", cex.Message); }
                        }

                        if (stillCovered.Count > 0)
                        {
                            LogEvent(account.Name, "LOCKOUT_STOP_RETAINED",
                                $"Position still open after flatten for {string.Join(",", stillCovered.Distinct())}; "
                                + "keeping its protective order working rather than leaving the position naked.");
                        }
                    }
                }
                else
                {
                    // T6/P0-51: shadow mode observes and logs, but does not touch the broker.
                    // Summarize what the sweep would have done, once per account per lockout.
                    var shadowInstruments = new Dictionary<string, List<string>>();
                    var shadowCancelCounts = new Dictionary<string, int>();

                    foreach (var batch in flattenBatches)
                    {
                        string name = batch.Key.Name;
                        if (!shadowInstruments.ContainsKey(name))
                            shadowInstruments[name] = new List<string>();
                        foreach (var instrument in batch.Value)
                            if (instrument != null) shadowInstruments[name].Add(instrument.FullName);
                    }

                    foreach (var batch in cancelBatches)
                    {
                        string name = batch.Key.Name;
                        if (!shadowInstruments.ContainsKey(name))
                            shadowInstruments[name] = new List<string>();
                        shadowCancelCounts[name] = shadowCancelCounts.TryGetValue(name, out int c)
                            ? c + batch.Value.Count
                            : batch.Value.Count;
                    }

                    foreach (var batch in deferredCancelBatches)
                    {
                        string name = batch.Key.Name;
                        if (!shadowInstruments.ContainsKey(name))
                            shadowInstruments[name] = new List<string>();
                        shadowCancelCounts[name] = shadowCancelCounts.TryGetValue(name, out int c)
                            ? c + batch.Value.Count
                            : batch.Value.Count;
                    }

                    lock (_stateLock)
                    {
                        foreach (var kvp in shadowInstruments)
                        {
                            string accName = kvp.Key;
                            if (_lockoutSweepShadowLogged.ContainsKey(accName)) continue;

                            int cancelCount = shadowCancelCounts.TryGetValue(accName, out int cc) ? cc : 0;
                            string instruments = kvp.Value.Count > 0
                                ? string.Join(", ", kvp.Value.Distinct().ToArray())
                                : "none";

                            LogEvent(accName, "LOCKOUT_SWEEP_SHADOW",
                                $"[SHADOW] Would execute lockout sweep for account {accName}: flatten [{instruments}], cancel {cancelCount} order(s).");

                            _lockoutSweepShadowLogged[accName] = true;
                        }
                    }
                }

                // P1-19 + P2-107. The sweep iterates every subscribed account, so its silence
                // about one of them is a statement about that account, not an omission.
                DispatchActions(sweepActions, "SafetySweep", AggregateEvaluatedAccounts());

                // All rule evaluation is now event-driven:
                // - PositionUpdate -> EvaluateRules + EvaluateLockoutPhase + UpdateFsmOnPosition
                // - OrderUpdate -> UpdateFsmOnOrder + EvaluateLockoutPhase
                // - ExecutionUpdate -> RecordExecution
                // - AccountItemUpdate -> EvaluatePnLRules + EvaluateFirmMirror
                // - Per-FSM one-shot Timer -> OnGraceExpired
            }
            catch (Exception ex)
            {
                LogEvent("SYSTEM", "ERROR", $"Error in ExecuteSafetySweep: {ex.Message}");
            }
            finally
            {
                // P1-12: last, outside the lock, and in a finally -- a rule that threw must not
                // cost us the log lines already drained out of the queue, which exist nowhere else.
                if (heartbeatStamp != null)
                    WriteFileOutsideLock("heartbeat", () => File.WriteAllText(_heartbeatFile, heartbeatStamp));

                if (logsToWrite != null && logsToWrite.Count > 0)
                    WriteFileOutsideLock("log", () => File.AppendAllLines(_logFile, logsToWrite, Encoding.UTF8));

                WritePersistedState(stateToWrite);
            }
        }

        // -
        // RULE ENGINE FRAMEWORK
        // -

        private AccountRiskProfile GetResolvedProfile(Account account)
        {
            if (account == null) return null;
            
            if (_config.Profiles != null)
            {
                foreach (var profile in _config.Profiles)
                {
                    if (!string.IsNullOrEmpty(profile.AccountNamePattern) && 
                        Regex.IsMatch(account.Name, profile.AccountNamePattern, RegexOptions.IgnoreCase))
                    {
                        return CreateDynamicProfile(account, profile);
                    }
                }
            }

            var fallback = new AccountRiskProfile
            {
                ProfileName = "GlobalFallback",
                DailyLossLimit = _config.PnLRules.DailyLossLimit,
                TrailingDrawdown = _config.PnLRules.TrailingDrawdown,
                MaxTradesPerSession = _config.Overtrading.MaxTradesPerSession,
                DefaultMaxContracts = _config.Sizing.MaxContractsPerAccount
            };
            return CreateDynamicProfile(account, fallback);
        }

        private AccountRiskProfile CreateDynamicProfile(Account account, AccountRiskProfile baseProfile)
        {
            var p = new AccountRiskProfile
            {
                ProfileName = baseProfile.ProfileName,
                AccountNamePattern = baseProfile.AccountNamePattern,
                InstrumentProfiles = baseProfile.InstrumentProfiles ?? new Dictionary<string, InstrumentProfile>(),
                MaxTradesPerSession = baseProfile.MaxTradesPerSession > 0 ? baseProfile.MaxTradesPerSession : _config.Overtrading.MaxTradesPerSession,
                DefaultMaxContracts = baseProfile.DefaultMaxContracts > 0 ? baseProfile.DefaultMaxContracts : _config.Sizing.MaxContractsPerAccount
            };

            double cashValue = account.Get(AccountItem.CashValue, Currency.UsDollar);

            p.DailyLossLimit = baseProfile.DailyLossLimit > 0.0 
                ? baseProfile.DailyLossLimit 
                : (cashValue > 0 ? cashValue * 0.025 : _config.PnLRules.DailyLossLimit);

            p.TrailingDrawdown = baseProfile.TrailingDrawdown > 0.0
                ? baseProfile.TrailingDrawdown
                : (cashValue > 0 ? cashValue * 0.05 : _config.PnLRules.TrailingDrawdown);
                
            return p;
        }

        // -
        // PER-POSITION GUARD FSM HELPERS (-6 of RiskGuardAddOn.md)
        // All methods assume _stateLock is held by the caller.
        // -
        private static string FsmKey(string accountName, string instrument) =>
            accountName + "|" + instrument;

        // internal, not private: TradeCopierEngine's bracket replication (P0-9) must classify a
        // leader's protective legs by exactly the same rule the guard uses. Two definitions of
        // "this order is the thing protecting the position" would drift, and the copier's copy
        // would be the one that silently stopped recognising a stop.
        internal static bool IsProtectiveSide(Order o, MarketPosition positionSide)
        {
            if (positionSide == MarketPosition.Long)
                return o.OrderAction == OrderAction.Sell || o.OrderAction == OrderAction.SellShort;
            if (positionSide == MarketPosition.Short)
                return o.OrderAction == OrderAction.Buy || o.OrderAction == OrderAction.BuyToCover;
            return false;
        }

        internal static bool IsStopType(Order o) =>
            o.OrderType == OrderType.StopMarket || o.OrderType == OrderType.StopLimit;

        // ------------------------------------------------------------------
        // ORDER LIVENESS (P0-59, P0-60)
        //
        // This replaces `IsPendingOrWorking` and `IsTerminal`, which were two
        // NON-TOTAL predicates that were not each other's complement. NT8 has
        // SIXTEEN OrderStates; between them those two classified eight, and the
        // two addons then picked OPPOSITE approximations for the other eight:
        //
        //   RiskGuard asked `!IsTerminal`  -> a stop in CancelSubmitted counted
        //                                     as coverage, so a position read as
        //                                     protected while its stop was being
        //                                     cancelled.            (P0-60)
        //   the copier asked `IsPendingOrWorking` -> a stop in ChangeSubmitted
        //                                     counted as GONE, so it created a
        //                                     duplicate leg.        (P0-59)
        //
        // Both hazards, opposite directions, one root cause. Observed live
        // 2026-08-10: two working COPIER_TARGETs against one lot.
        //
        // The reason one boolean could never fix this is that callers ask TWO
        // different questions, whose fail-safe answers point opposite ways:
        //
        //   "is something already here, so do not create a second?"
        //        -> answering NO wrongly OVER-COVERS (two stops flip the position)
        //   "does this actually protect the position?"
        //        -> answering YES wrongly leaves it NAKED
        //
        // So there is one total classification and two derived predicates, and
        // an unclassifiable state answers BOTH questions conservatively: it
        // occupies a slot (do not duplicate it) and it does not count as cover.
        // ------------------------------------------------------------------

        internal enum OrderLiveness
        {
            /// <summary>Exists at the broker and will act on the market.</summary>
            Working,
            /// <summary>
            /// Exists, will act, and a modification of it is ALREADY IN FLIGHT.
            /// Protective in every sense -- but a second Change() against it is
            /// silently dropped by NT8, and the order REVERTS to its pre-change
            /// values. See <see cref="AcceptsModification"/> for the live trace.
            /// </summary>
            Changing,
            /// <summary>Exists, but a cancel is already in flight. Do not rely on it; do not cancel it again.</summary>
            Departing,
            /// <summary>Exists but will not act while it stays this way.</summary>
            Inert,
            /// <summary>Gone. The slot is free.</summary>
            Terminal,
            /// <summary>NT8 said Unknown, or a state this build does not classify.</summary>
            Indeterminate
        }

        /// <summary>
        /// Total over NT8's OrderState. Every member of the real enum is named here
        /// explicitly -- see TestOrderLiveness_ClassifiesEveryNT8OrderState, which fails
        /// if a state is added and left unclassified rather than letting it fall into a
        /// silent default.
        /// </summary>
        internal static OrderLiveness Classify(OrderState s)
        {
            switch (s)
            {
                // Exists and will act. TriggerPending is a stop waiting on its trigger:
                // the most protective state a stop can be in.
                case OrderState.Initialized:
                case OrderState.Submitted:
                case OrderState.Accepted:
                case OrderState.AcceptedByRisk:
                case OrderState.Working:
                case OrderState.PartFilled:
                case OrderState.TriggerPending:
                    return OrderLiveness.Working;

                // The states an order passes through during Account.Change(). It is
                // emphatically NOT gone, and reading it as gone is what duplicated a live
                // leg (P0-59) -- so this still occupies a slot AND provides coverage.
                // Separated from Working only because a THIRD question has a different
                // answer here: see AcceptsModification.
                case OrderState.ChangeSubmitted:
                case OrderState.ChangePending:
                    return OrderLiveness.Changing;

                // A cancel is in flight. It still occupies its slot at the broker, so
                // cancelling again is noise -- but it must NOT be counted as coverage,
                // which is precisely what `!IsTerminal` used to do (P0-60).
                case OrderState.CancelSubmitted:
                case OrderState.CancelPending:
                    return OrderLiveness.Departing;

                // Present but dormant. Not cover, and not a free slot either.
                case OrderState.Suspended:
                    return OrderLiveness.Inert;

                case OrderState.Filled:
                case OrderState.Cancelled:
                case OrderState.Rejected:
                    return OrderLiveness.Terminal;

                case OrderState.Unknown:
                    return OrderLiveness.Indeterminate;

                default:
                    // A state NT8 added that this build has never heard of. Conservative
                    // in both directions by construction: OccupiesSlot true, ProvidesCoverage
                    // false. The conformance test is what stops this being reached silently.
                    return OrderLiveness.Indeterminate;
            }
        }

        /// <summary>
        /// "Is there already an order here, so I must not create a second one?"
        /// True for anything the broker still holds. Answering this wrongly with NO is
        /// what produces two protective legs behind one position.
        /// </summary>
        internal static bool OccupiesSlot(OrderState s)
        {
            var c = Classify(s);
            return c == OrderLiveness.Working || c == OrderLiveness.Changing
                || c == OrderLiveness.Inert || c == OrderLiveness.Indeterminate;
        }

        /// <summary>
        /// "Does this order actually protect the position?"
        /// Only a Working order does. A cancelling, suspended or unknown order must never
        /// be counted as cover -- answering this wrongly with YES is what leaves a
        /// position naked while something believes it is protected.
        /// </summary>
        internal static bool ProvidesCoverage(OrderState s)
        {
            var c = Classify(s);
            return c == OrderLiveness.Working || c == OrderLiveness.Changing;
        }

        /// <summary>
        /// "Can I issue an Account.Change() against this order right now?"
        ///
        /// **The third question, added 2026-08-10 after a live trade on `Sim101 -> Sim-ORB`.**
        /// P0-60 established two questions with opposite fail-safe answers; this is a third
        /// that neither answers, and the shape of the defect is identical -- a caller asking
        /// something no predicate covered, and inferring it from the closest one.
        ///
        /// A leg mid-change occupies a slot (yes) and provides coverage (yes) but must NOT be
        /// changed again: **NT8 silently drops the second Change() and the order REVERTS to
        /// its pre-change values.** The live trace, on a follower scaling 1 -> 2 lots:
        ///
        ///     34412 ChangeSubmitted  qty 1 @ 29822.25   (first change in flight)
        ///     34412 ChangePending    qty 2 @ 29822.5    (our second change)
        ///     34412 Working          qty 1 @ 29822.25   (reverted -- BOTH changes lost)
        ///
        /// The follower was left holding 2 lots behind a 1-lot stop and a 1-lot target.
        /// RiskGuard saw it (`FSM_UNDERCOVERED: covered 1 &lt; pos 2`) and, in shadow, logged
        /// `MISSING_STOP_FLATTEN` on all four accounts -- armed live it would have flattened
        /// the lot. So the compensating control worked and the copier still under-covered.
        ///
        /// A caller that finds this false must NOT fall back to cancel-then-replace: cancelling
        /// a protective leg whose change is about to land is strictly worse than waiting a beat.
        /// Defer and re-drive once the order settles.
        /// </summary>
        internal static bool AcceptsModification(OrderState s)
        {
            return Classify(s) == OrderLiveness.Working;
        }

        /// <summary>
        /// "Is this order gone, so its slot is free?" Terminal ONLY -- a cancelling order
        /// is not terminal, it is Departing, and the difference is load-bearing. Callers
        /// asking about coverage want <see cref="ProvidesCoverage"/>; callers asking
        /// whether to place or cancel something want <see cref="OccupiesSlot"/>. Reach for
        /// this one only when you genuinely mean "the broker is finished with it".
        /// </summary>
        internal static bool IsTerminal(OrderState s)
        {
            return Classify(s) == OrderLiveness.Terminal;
        }

        // Called from ExecutePositionUpdate. Handles flat<->nonflat transitions.
        private void UpdateFsmOnPosition(Account account, string instrument, MarketPosition newPos, int qty)
        {
            if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(account.Name)) return;
            if (!_isArmed) return;

            string key = FsmKey(account.Name, instrument);
            bool isNonFlat = newPos != MarketPosition.Flat && qty > 0;

            if (isNonFlat)
            {
                lock (_stateLock)
                {
                    // Check if an FSM already exists for this (account, instrument).
                    if (_guardFsms.TryGetValue(key, out var existingFsm) && existingFsm.PositionSide == newPos)
                    {
                        // Same-side qty-only update (partial fill, scale-out/in):
                        // update qty in place, preserving Protected/ProtectedPending state
                        // and the recognized stop order. Do NOT recreate the FSM.
                        existingFsm.PositionQuantity = qty;

                        // Under-coverage detection: if we are protected but the stop
                        // does not cover the full position, arm the grace timer.
                        if ((existingFsm.State == GuardFsmState.Protected ||
                             existingFsm.State == GuardFsmState.ProtectedPending) &&
                            existingFsm.CoveredQuantity < existingFsm.PositionQuantity)
                        {
                            LogEvent(account.Name, "FSM_UNDERCOVERED",
                                $"{key}: covered {existingFsm.CoveredQuantity} < pos {existingFsm.PositionQuantity}");
                            existingFsm.GraceEmitted = false;
                            if (!existingFsm.GracePending)
                            {
                                ArmGraceTimer(existingFsm, account, instrument,
                                    _config.StopGuard.StopAttachSeconds * 1000);
                            }
                        }

                        LogEvent(account.Name, "FSM_UPDATE",
                            $"{key}: qty updated to {qty} (state stays {existingFsm.State})");
                        return;
                    }

                    // flat->nonflat or flip: dispose the outgoing FSM's timer before overwriting.
                    if (_guardFsms.TryGetValue(key, out var oldFsm))
                    {
                        oldFsm.GraceTimer?.Dispose();
                    }

                    // (re)create FSM, arm grace, consume pending stop
                    var fsm = new PositionGuardFsm(account.Name, instrument)
                    {
                        PositionSide = newPos,
                        PositionQuantity = qty,
                        EntryTime = DateTime.UtcNow,
                        State = GuardFsmState.Unprotected
                    };

                    // Consume a buffered stop that arrived before the position event (P1-14).
                    if (_pendingStops.TryGetValue(key, out var pending) && pending != null)
                    {
                        // Now -- and only now -- the position side is known, so the buffered
                        // candidates can finally be judged. Two conditions, both load-bearing:
                        //
                        //   IsProtectiveSide  the order reduces THIS position rather than opening
                        //                     another one.
                        //   Quantity <= qty   a resting breakout ENTRY passes the side test by
                        //                     coincidence (a sell-stop entry does reduce a long)
                        //                     while being sized for a trade that has nothing to do
                        //                     with this position. Adopting it reports coverage the
                        //                     position does not have and, if it triggers, flips the
                        //                     account by the difference. A genuine protective stop
                        //                     is never larger than what it protects.
                        // P1-36: adopt every valid candidate, largest first, while the running
                        // total still fits the position. A bracket whose two stop legs both
                        // arrive before the position event is the ordinary case this has to get
                        // right; taking one of them reports the position half naked.
                        var candidates = pending
                            .Where(b => b.Order != null
                                     && IsStopType(b.Order)
                                     && ProvidesCoverage(b.Order.OrderState)
                                     && IsProtectiveSide(b.Order, newPos)
                                     && b.Order.Quantity <= qty)
                            .OrderByDescending(b => b.Order.Quantity)
                            .ToList();

                        int adoptedCount = 0;
                        bool anyPendingLeg = false;
                        foreach (var candidate in candidates)
                        {
                            if (fsm.CoveredQuantity + candidate.Order.Quantity > qty) continue;
                            fsm.AddRecognizedStop(candidate.Order);
                            adoptedCount++;
                            if (candidate.Order.OrderState != OrderState.Working) anyPendingLeg = true;
                        }

                        if (adoptedCount > 0)
                        {
                            fsm.State = anyPendingLeg
                                ? GuardFsmState.ProtectedPending
                                : GuardFsmState.Protected;
                        }

                        int rejected = pending.Count - adoptedCount;
                        if (rejected > 0)
                        {
                            LogEvent(account.Name, "FSM_PENDING_STOP_REJECTED",
                                $"{key}: discarded {rejected} buffered stop(s) that are not protective "
                                + $"cover for a {newPos} {qty} position.");
                        }
                        _pendingStops.Remove(key);
                    }

                    // Arm a one-shot grace timer that fires at the exact grace deadline.
                    // This replaces the sweep polling of GraceDeadline with an instant trigger.
                    if (fsm.State == GuardFsmState.Unprotected && _config.StopGuard.StopAttachSeconds > 0)
                    {
                        ArmGraceTimer(fsm, account, instrument, _config.StopGuard.StopAttachSeconds * 1000);
                    }

                    _guardFsms[key] = fsm;
                    LogEvent(account.Name, "FSM_TRANSITION",
                        $"Created FSM {key} -> {fsm.State} (grace deadline {fsm.GraceDeadline:HH:mm:ss})");
                }
            }
            else
            {
                // nonflat->flat: tear down, cancel grace timer, cancel orphan auto-stop.
                // P1-35 (was P1-30): this runs with _stateLock held - every caller of
                // UpdateFsmOnPosition already holds it. So the orphan cancel is QUEUED here and
                // sent by DrainPendingCancels() once the caller releases the lock. Do NOT
                // "fix" a future variant of this by wrapping the Cancel in a nested
                // lock(_stateLock) and calling it outside: the nested lock is re-entrant, the
                // outer lock is still held, and it only hides the violation.
                if (_guardFsms.TryGetValue(key, out var fsm))
                {
                    fsm.GraceTimer?.Dispose();
                    if (fsm.AutoStopOrder != null && OccupiesSlot(fsm.AutoStopOrder.OrderState))
                    {
                        _pendingCancels.Add(new PendingCancelEntry(account, fsm.AutoStopOrder, PendingCancelIntent.Cleanup));
                    }
                    _guardFsms.Remove(key);
                    LogEvent(account.Name, "FSM_TRANSITION", $"Tore down FSM {key} -> Flat");
                }
                _pendingStops.Remove(key);
            }
        }

        /// <summary>
        /// Sends cancellations that were decided under `_stateLock`.
        ///
        /// **MUST be called with `_stateLock` NOT held.** Calling it from inside the lock would
        /// defeat the entire point: the lock is re-entrant, so the queue would drain and the
        /// broker call would happen under the lock exactly as before, while *looking* correct.
        /// The TESTING build throws on that mistake rather than letting it pass review — this
        /// is precisely the "nested lock buys nothing" trap recorded in the hardening plan.
        /// </summary>
        private void DrainPendingCancels()
        {
#if TESTING
            if (Monitor.IsEntered(_stateLock))
                throw new InvalidOperationException(
                    "DrainPendingCancels() was called while _stateLock is held. The lock is "
                    + "re-entrant, so this would send the cancel under the lock and reintroduce "
                    + "P1-35. Move the call after the lock block.");
#endif
            List<PendingCancelEntry> toDrain;
            lock (_stateLock)
            {
                if (_pendingCancels.Count == 0) return;
                toDrain = new List<PendingCancelEntry>(_pendingCancels);
                _pendingCancels.Clear();
            }

            var cleanup = new List<PendingCancelEntry>();
            var intervention = new List<PendingCancelEntry>();
            foreach (var entry in toDrain)
            {
                if (entry.Account == null || entry.Order == null) continue;
                if (!OccupiesSlot(entry.Order.OrderState)) continue;   // gone, or already going
                if (entry.Intent == PendingCancelIntent.Cleanup)
                    cleanup.Add(entry);
                else
                    intervention.Add(entry);
            }

            // Cleanup cancels remove RiskGuard's own footprint and are sent in every mode.
            foreach (var entry in cleanup)
            {
                try { entry.Account.Cancel(new[] { entry.Order }); }
                catch (Exception cex) { LogEvent(entry.Account.Name, "FSM_AUTOSTOP_CANCEL_FAIL", cex.Message); }
            }

            // Intervention cancels act on the trader's orders and are gated by mode.
            if (IsActingMode())
            {
                foreach (var entry in intervention)
                {
                    try { entry.Account.Cancel(new[] { entry.Order }); }
                    catch (Exception cex) { LogEvent(entry.Account.Name, "INTERVENTION_CANCEL_FAIL", cex.Message); }
                }
            }
            else
            {
                var withheld = new Dictionary<string, int>();
                foreach (var entry in intervention)
                {
                    string name = entry.Account.Name;
                    withheld[name] = withheld.TryGetValue(name, out int c) ? c + 1 : 1;
                }

                foreach (var kvp in withheld)
                {
                    LogEvent(kvp.Key, "SHADOW_PENDING_CANCEL",
                        $"[SHADOW] Withheld {kvp.Value} intervention cancel(s) in shadow mode.");
                }
            }
        }

        // Arms a one-shot grace timer. MUST be called with _stateLock already held.
        private void ArmGraceTimer(PositionGuardFsm fsm, Account account, string instrument, int delayMs)
        {
            fsm.GraceTimer?.Dispose();
            fsm.GraceDeadline = DateTime.UtcNow.AddMilliseconds(delayMs);
            fsm.GracePending = true;
            long generation = ++fsm.GraceGeneration;
            var capturedAccount = account;
            var capturedInstrument = instrument;
            fsm.GraceTimer = new Timer(_ =>
            {
                OnGraceTimerCallback(capturedAccount, capturedInstrument, generation);
            }, null, delayMs, Timeout.Infinite);
        }

        // Timer callback that validates the generation before invoking OnGraceExpired.
        private void OnGraceTimerCallback(Account account, string instrument, long generation)
        {
            string key = FsmKey(account.Name, instrument);
            lock (_stateLock)
            {
                if (_guardFsms.TryGetValue(key, out var fsm) && fsm.GraceGeneration == generation)
                {
                    // Valid generation; proceed to evaluate grace expiry.
                    // OnGraceExpired will call EvaluateGraceExpiry which takes _stateLock again,
                    // but that's safe because the lock is reentrant.
                }
                else
                {
                    return; // Stale callback, ignore.
                }
            }
            // Already had the inline fallback the other five lacked; now it shares the seam.
            RunGuardWork("GraceExpiry", () => OnGraceExpired(account, instrument));
        }

        // One-shot grace expiry callback - called by the per-FSM Timer or the sweep.
        internal void OnGraceExpired(Account account, string instrument)
        {
            var actions = EvaluateGraceExpiry(account, instrument);
            if (actions != null)
                DispatchActions(actions, "GraceExpiry", new List<string> { account.Name });   // P1-19 + P2-107
        }

        // Called from ExecuteOrderUpdate. Classifies the order against the active FSM.
        private void UpdateFsmOnOrder(Account account, string instrument, Order order)
        {
            if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(account.Name)) return;
            if (!_isArmed) return;
            if (order?.Instrument == null) return;

            string key = FsmKey(account.Name, instrument);

            lock (_stateLock)
            {
                // If no FSM yet, buffer protective-side stops pending the position event.
                if (!_guardFsms.ContainsKey(key))
                {
                    if (IsStopType(order) && ProvidesCoverage(order.OrderState))
                    {
                        // We don't know the position side yet; buffer and classify on consumption.
                        // P1-14: append rather than overwrite, and stamp it so the watchdog can
                        // expire it. Re-buffering the same Order object (NT8 raises OrderUpdate
                        // repeatedly for one order) refreshes the stamp instead of duplicating.
                        List<BufferedStop> buffered;
                        if (!_pendingStops.TryGetValue(key, out buffered))
                        {
                            buffered = new List<BufferedStop>();
                            _pendingStops[key] = buffered;
                        }

                        var existing = buffered.FirstOrDefault(b => ReferenceEquals(b.Order, order));
                        if (existing != null)
                            existing.BufferedAtUtc = DateTime.UtcNow;
                        else
                            buffered.Add(new BufferedStop { Order = order, BufferedAtUtc = DateTime.UtcNow });
                    }
                    return;
                }

                var fsm = _guardFsms[key];
                var prev = fsm.State;

                // Recognise a protective stop for the current position side.
                if (IsProtectiveSide(order, fsm.PositionSide) && IsStopType(order))
                {
                    // P0-60: not IsTerminal. A stop entering CancelSubmitted has stopped being
                    // cover before it is terminal, and waiting for terminal leaves a window in
                    // which the FSM reports protection that is already being withdrawn.
                    if (!ProvidesCoverage(order.OrderState))
                    {
                        // P1-36: losing ONE stop of several is not the same as being naked. Drop
                        // it from the cover and re-derive; the position drops to Unprotected only
                        // when nothing is left holding it. Under the single-stop model this branch
                        // zeroed coverage outright, so a 6-lot position covered by two 3-lot stops
                        // read as fully naked the moment either leg was cancelled -- and the
                        // auto-stop that followed was sized for the whole 6.
                        if (fsm.IsRecognizedStop(order))
                        {
                            fsm.RemoveRecognizedStop(order);
                            if (object.ReferenceEquals(order, fsm.AutoStopOrder)) fsm.AutoStopOrder = null;

                            if (fsm.PositionQuantity > 0)
                            {
                                fsm.GraceEmitted = false;
                                if (fsm.CoveredQuantity <= 0)
                                {
                                    fsm.State = GuardFsmState.Unprotected;
                                    LogEvent(account.Name, "FSM_TRANSITION",
                                        $"{key}: stop {order.Name} terminal ({order.OrderState}) -> Unprotected");
                                }
                                else
                                {
                                    LogEvent(account.Name, "FSM_UNDERCOVERED",
                                        $"{key}: stop {order.Name} terminal ({order.OrderState}); "
                                        + $"{fsm.CoveredQuantity} of {fsm.PositionQuantity} still covered by "
                                        + $"{fsm.RecognizedStops.Count} remaining stop(s)");
                                }

                                if (fsm.CoveredQuantity < fsm.PositionQuantity && !fsm.GracePending)
                                {
                                    ArmGraceTimer(fsm, account, instrument,
                                        _config.StopGuard.StopAttachSeconds * 1000);
                                }
                            }
                        }
                        else if (object.ReferenceEquals(order, fsm.AutoStopOrder))
                        {
                            // The auto-stop went terminal but it's not part of the cover;
                            // just clear the auto-stop reference.
                            fsm.AutoStopOrder = null;
                        }
                    }
                    else // Non-terminal order update
                    {
                        // P1-36: every protective-side stop adds to the cover. The old code kept
                        // one slot and so needed a rule for which order won -- "replace only with
                        // an equal-or-larger stop" -- which meant a genuine second leg was
                        // discarded with an FSM_IGNORE line and the position read under-covered
                        // while being fully protected. Adding is idempotent by object reference,
                        // and a quantity change on an order already tracked is picked up
                        // automatically because the sum reads Quantity off the live object.
                        bool isNew = !fsm.IsRecognizedStop(order);
                        fsm.AddRecognizedStop(order);
                        fsm.GraceEmitted = false;

                        if (order.OrderState == OrderState.Working)
                        {
                            if (order.Name == "RiskGuardAutoStop") fsm.AutoStopOrder = order;
                            // ProtectedPending only survives while some leg is still not Working.
                            fsm.State = fsm.RecognizedStops.Any(o => o.OrderState != OrderState.Working)
                                ? GuardFsmState.ProtectedPending
                                : GuardFsmState.Protected;
                            if (isNew)
                                LogEvent(account.Name, "FSM_TRANSITION",
                                    $"{key}: stop {order.Name} Working -> {fsm.State} "
                                    + $"(covered {fsm.CoveredQuantity}/{fsm.PositionQuantity})");
                        }
                        else // Submitted/Accepted/Initialized/PartFilled
                        {
                            fsm.State = GuardFsmState.ProtectedPending;
                            if (isNew)
                                LogEvent(account.Name, "FSM_TRANSITION",
                                    $"{key}: stop {order.Name} {order.OrderState} -> ProtectedPending "
                                    + $"(covered {fsm.CoveredQuantity}/{fsm.PositionQuantity})");
                        }

                        // If full coverage achieved, cancel any pending grace timer.
                        if (fsm.CoveredQuantity >= fsm.PositionQuantity)
                        {
                            fsm.GraceTimer?.Dispose();
                            fsm.GraceTimer = null;
                            fsm.GracePending = false;
                        }
                        else
                        {
                            // Under-covered: ensure a grace timer is armed for the delta.
                            if (!fsm.GracePending)
                            {
                                ArmGraceTimer(fsm, account, instrument,
                                    _config.StopGuard.StopAttachSeconds * 1000);
                            }
                        }
                    }
                }

                if (prev != fsm.State)
                {
                    fsm.LastTransitionTime = DateTime.UtcNow;
                    // Do NOT dispose the grace timer here; full-coverage disposal is handled
                    // in the recognition branches, and partial coverage must keep the timer alive.
                }
            }
        }

        // One-shot grace expiry. Called from a per-FSM Timer (or, defensively, from
        // the watchdog in the sweep if the timer was lost). Emits the StopGuard
        // action exactly once because the FSM transitions out of Unprotected.
        internal List<GuardAction> EvaluateGraceExpiry(Account account, string instrument)
        {
            var actions = new List<GuardAction>();
            lock (_stateLock)
            {
                if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(account.Name)) return actions;
                if (!_isArmed) return actions;

                string key = FsmKey(account.Name, instrument);
                if (!_guardFsms.TryGetValue(key, out var fsm)) return actions;

                // The timer that woke us has fired; clear the pending flag.
                fsm.GracePending = false;

                // Anti-duplicate latch: if a grace action was already emitted and
                // its outcome is still pending, do not emit another.
                if (fsm.GraceEmitted) return actions;

                // Position must still be open and the deadline must have passed.
                if (DateTime.UtcNow < fsm.GraceDeadline) return actions;

                var pos = account.Positions.FirstOrDefault(p => p.Instrument.FullName == instrument);
                if (pos == null || pos.MarketPosition == MarketPosition.Flat) return actions;

                // Proceed when unprotected OR under-covered (stop quantity < position).
                bool isUnprotected = fsm.State == GuardFsmState.Unprotected;
                bool isUnderCovered = fsm.CoveredQuantity < pos.Quantity;
                if (!isUnprotected && !isUnderCovered) return actions;

                // Size the action to the uncovered delta only.
                int uncovered = pos.Quantity - Math.Max(0, fsm.CoveredQuantity);
                if (uncovered <= 0) return actions;

                if (_config.StopGuard.OnMissing == "AutoStop")
                {
                    actions.Add(new GuardAction
                    {
                        AccountName = account.Name,
                        ActionType = GuardActionType.PlaceStopOrder,
                        Instrument = instrument,
                        InstrumentObj = pos.Instrument,
                        Quantity = uncovered,
                        RuleId = "MISSING_STOP_ATTACH"
                    });
                    // For the Unprotected case, transition to a pending state so a
                    // duplicate call does not re-emit. For the under-covered case
                    // the FSM is already Protected/ProtectedPending; do not downgrade.
                    if (isUnprotected)
                    {
                        fsm.State = GuardFsmState.ProtectedPending;
                    }
                }
                else
                {
                    // P1-87. This was `else if (OnMissing == "Flatten")`, so ANY other value --
                    // a lower-case "flatten", a typo, an empty string, or the "WarnOnly" the
                    // declaration itself used to advertise -- matched nothing and this method
                    // returned NO ACTION: a position with no stop, past its grace period, and
                    // the guard simply walked away. Nothing validated the value either.
                    //
                    // Flatten is the fallback because it is the documented default and the one
                    // that is always a known quantity; the alternative invents a stop at a
                    // guessed offset. Falling back silently would be its own lie, so
                    // RunPreflight now REFUSES an unrecognised value and names it.
                    //
                    // Deliberately one branch rather than two: splitting "Flatten" from
                    // "unrecognised" would put one outcome under two RuleIds, and the log is
                    // grepped by RuleId.
                    //
                    // Found because a mutant flipping OnMissing to "AutoStop" survived 1180
                    // green tests -- nothing pinned this at all.
                    actions.Add(new GuardAction
                    {
                        AccountName = account.Name,
                        ActionType = GuardActionType.FlattenPosition,
                        Instrument = instrument,
                        InstrumentObj = pos.Instrument,
                        Quantity = uncovered,
                        RuleId = "MISSING_STOP_FLATTEN"
                    });
                    if (isUnprotected)
                    {
                        fsm.State = GuardFsmState.FlattenPending;
                    }
                }

                // Mark that a grace action has been emitted for this episode.
                fsm.GraceEmitted = true;
            }
            return actions;
        }

        // Watchdog: log any FSM stuck in Unprotected past grace+buffer. Log only.
        private void FsmWatchdog()
        {
            ExpireStalePendingStops();

            foreach (var kv in _guardFsms)
            {
                var fsm = kv.Value;
                bool isNaked = fsm.State == GuardFsmState.Unprotected ||
                               fsm.CoveredQuantity < fsm.PositionQuantity;
                if (isNaked &&
                    DateTime.UtcNow > fsm.GraceDeadline.AddSeconds(2) &&
                    !fsm.GracePending &&
                    !fsm.GraceEmitted)
                {
                    // Keep the existing log line for the Unprotected case unchanged.
                    if (fsm.State == GuardFsmState.Unprotected)
                    {
                        LogEvent(fsm.AccountName, "FSM_WATCHDOG",
                            $"{fsm.Instrument}: Unprotected past grace deadline by " +
                            $"{(DateTime.UtcNow - fsm.GraceDeadline).TotalSeconds:F1}s");
                    }

                    Account account = Account.All.FirstOrDefault(a => a.Name == fsm.AccountName);
                    if (account != null)
                    {
                        // Arm a short grace timer; the sweep releases _stateLock
                        // before the callback needs it.
                        ArmGraceTimer(fsm, account, fsm.Instrument, 250);
                    }
                }
            }
        }

        private struct FsmAuditSnapshot
        {
            public string AccountName;
            public string Instrument;
            public GuardFsmState State;
            public long CoveredQuantity;
            public long PositionQuantity;
        }

        // P2-108. Survives across audit passes by design -- a per-pass instance would have no
        // memory and the throttle would do nothing while every test of it passed.
        private readonly AuditFindingThrottle _auditThrottle = new AuditFindingThrottle();

        private void RunGuardAudit()
        {
            var fsmSnapshot = new Dictionary<string, FsmAuditSnapshot>();
            lock (_stateLock)
            {
                foreach (var kv in _guardFsms)
                {
                    var fsm = kv.Value;
                    fsmSnapshot[kv.Key] = new FsmAuditSnapshot
                    {
                        AccountName = fsm.AccountName,
                        Instrument = fsm.Instrument,
                        State = fsm.State,
                        CoveredQuantity = fsm.CoveredQuantity,
                        PositionQuantity = fsm.PositionQuantity
                    };
                }
            }

            // P2-108. Findings are collected across the whole pass and emitted at the end, through
            // AuditFindingThrottle. Collected rather than logged inline because the throttle needs
            // BOTH sets to work: which ACCOUNTS were examined, and what fired. A finding on an
            // examined account that did not fire has resolved, and that is what clears its record
            // -- with no timer involved.
            var examinedAccounts = new List<string>();
            var firedKeys = new List<string>();
            var findingText = new Dictionary<string, string>();
            var findingAccount = new Dictionary<string, string>();
            var findingType = new Dictionary<string, string>();

            try
            {
                foreach (Account account in Account.All)
                {
                    string accountName = account.Name;

                    var positionsByInstrument = new Dictionary<string, Position>();
                    foreach (Position pos in account.Positions)
                    {
                        // A flat Position object is not a position. The FSM-seeding sweep
                        // filters these for the same reason; without it a flat account
                        // reports NAKED_POSITION on every tick of the audit timer.
                        if (pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0)
                            continue;
                        // FullName, not ToString(): every FSM key in this addon is built from
                        // Instrument.FullName, so ToString() here matched nothing and the audit
                        // reported all three findings against a correctly protected account.
                        string instrument = pos.Instrument == null ? string.Empty : pos.Instrument.FullName;
                        if (string.IsNullOrEmpty(instrument))
                            continue;
                        positionsByInstrument[instrument] = pos;
                    }

                    var workingStopsByInstrument = new Dictionary<string, int>();
                    foreach (Order order in account.Orders)
                    {
                        if (order == null || order.Instrument == null)
                            continue;

                        bool isWorking = order.OrderState == OrderState.Working || order.OrderState == OrderState.Accepted;
                        if (!isWorking)
                            continue;

                        bool isStop = order.OrderType == OrderType.StopMarket || order.OrderType == OrderType.StopLimit;
                        if (!isStop)
                            continue;

                        string instrument = order.Instrument.FullName;
                        if (string.IsNullOrEmpty(instrument))
                            continue;

                        if (workingStopsByInstrument.ContainsKey(instrument))
                            workingStopsByInstrument[instrument]++;
                        else
                            workingStopsByInstrument[instrument] = 1;
                    }

                    // ⚠️ RECORDED HERE, after this account's positions AND orders have been
                    // enumerated without throwing. This is what lets a CLOSED position clear its
                    // own record: there is no position left to iterate, so nothing key-scoped
                    // would ever be marked resolved. Recording the account instead is the fix,
                    // and it was found by driving the box, not by the suite.
                    examinedAccounts.Add(accountName);

                    foreach (var posKv in positionsByInstrument)
                    {
                        string instrument = posKv.Key;
                        Position pos = posKv.Value;
                        string fsmKey = accountName + "|" + instrument;
                        bool hasFsm = fsmSnapshot.TryGetValue(fsmKey, out FsmAuditSnapshot fsm);
                        bool isProtected = hasFsm && fsm.State == GuardFsmState.Protected;
                        long covered = hasFsm ? fsm.CoveredQuantity : 0;
                        long positionQty = pos.Quantity;
                        if (!isProtected || covered < positionQty)
                        {
                            long gap = Math.Max(0, positionQty - covered);
                            string stateName = hasFsm ? fsm.State.ToString() : "MISSING";
                            // P2-108: the finding is RECORDED here and logged (or withheld) at
                            // the end of the pass. Logging inline is what made this one line every
                            // 10 seconds, forever, on a path DispatchActions never sees.
                            string nakedKey = AuditFindingThrottle.KeyFor("NAKED_POSITION", accountName, instrument);
                            firedKeys.Add(nakedKey);
                            findingText[nakedKey] = $"{instrument}: position={positionQty}, fsmState={stateName}, covered={covered}, gap={gap}";
                            findingAccount[nakedKey] = accountName;
                            findingType[nakedKey] = "NAKED_POSITION";
                        }
                    }

                    foreach (var stopKv in workingStopsByInstrument)
                    {
                        string instrument = stopKv.Key;
                        bool hasPosition = positionsByInstrument.TryGetValue(instrument, out Position pos) && pos.Quantity != 0;
                        string fsmKey = accountName + "|" + instrument;
                        bool hasFsm = fsmSnapshot.ContainsKey(fsmKey);
                        // P0-50's class is a stop left working on a FLAT account -- that is a new
                        // position in the opposite direction the moment it triggers. A stop sitting
                        // over a LIVE position is not an orphan whatever the FSM knows about it;
                        // the untracked-position case is already reported as NAKED_POSITION above,
                        // so keying this on !hasFsm double-reported it under a name that is wrong.
                        string orphanKey = AuditFindingThrottle.KeyFor("ORPHAN_STOP", accountName, instrument);
                        if (!hasPosition)
                        {
                            firedKeys.Add(orphanKey);
                            findingText[orphanKey] = $"{instrument}: workingStopCount={stopKv.Value}, hasPosition={hasPosition}, hasFsm={hasFsm}";
                            findingAccount[orphanKey] = accountName;
                            findingType[orphanKey] = "ORPHAN_STOP";
                        }
                    }

                    foreach (FsmAuditSnapshot fsm in fsmSnapshot.Values)
                    {
                        if (fsm.AccountName != accountName)
                            continue;
                        if (fsm.State != GuardFsmState.Protected)
                            continue;
                        string divKey = AuditFindingThrottle.KeyFor("FSM_DIVERGENCE", accountName, fsm.Instrument);
                        if (!workingStopsByInstrument.ContainsKey(fsm.Instrument))
                        {
                            firedKeys.Add(divKey);
                            findingText[divKey] = $"{fsm.Instrument}: FSM claims Protected but no working stop order";
                            findingAccount[divKey] = accountName;
                            findingType[divKey] = "FSM_DIVERGENCE";
                        }
                    }
                }

                // P2-108. One decision point for all three findings.
                //
                // ⚠️ The budget is re-read from the MODE every pass and never cached: 1 while
                // observing, 6 while acting. In `shadow` the guard's product IS the observation
                // and it is complete after one line -- the 1 is the fix, not a tuning value.
                int auditBudget = AuditFindingThrottle.BudgetFor(IsActingMode());
                var admitted = _auditThrottle.Admit(examinedAccounts, firedKeys, auditBudget);
                var admittedSet = new HashSet<string>(admitted, StringComparer.OrdinalIgnoreCase);

                foreach (string key in admitted)
                {
                    LogEvent(findingAccount[key], findingType[key], findingText[key]);
                }

                // ⚠️ SUPPRESSION IS ANNOUNCED, EXACTLY ONCE. Silently withholding a true finding
                // trades a screaming alarm for a silent one, which is the same defect inverted:
                // the operator could not tell "resolved" from "still true and no longer mentioned".
                foreach (string key in firedKeys)
                {
                    if (admittedSet.Contains(key)) continue;
                    if (!_auditThrottle.FirstSuppression(key, auditBudget)) continue;
                    LogEvent(findingAccount[key], "AUDIT_FINDING_SUPPRESSED",
                        $"{findingType[key]} for {findingText[key]} is STILL TRUE and will stop " +
                        $"being logged after {auditBudget} line(s) in {(IsActingMode() ? "live" : "observing")} " +
                        "mode. It will report again the moment the condition resolves and recurs.");
                }
            }
            catch (Exception ex)
            {
                LogEvent("RiskGuard", "AUDIT_TIMER_ERROR",
                    $"RunGuardAudit failed: {ex}");
            }
        }

        /// <summary>
        /// P1-14: drops buffered stops that no position ever arrived to claim. Called from the
        /// watchdog, so it runs with `_stateLock` held and makes no broker calls.
        ///
        /// Without this the buffer only ever shrank on consumption or on a flat transition, so a
        /// stop buffered against an entry that was rejected simply stayed -- and the next
        /// position opened on that instrument, hours or days later, adopted it as its protective
        /// cover. The FSM would read Protected against an order that is stale, cancelled outside
        /// our view, or sized for a completely different trade.
        ///
        /// The window is two grace periods. One is the longest a legitimate stop can lag its
        /// position event and still be the thing that protects it; two leaves margin for a slow
        /// broker without letting the entry outlive the trade it belongs to. A terminal order is
        /// dropped immediately whatever its age -- it protects nothing.
        /// </summary>
        private void ExpireStalePendingStops()
        {
            if (_pendingStops.Count == 0) return;

            int graceSeconds = _config?.StopGuard != null ? _config.StopGuard.StopAttachSeconds : 0;
            var ttl = TimeSpan.FromSeconds(Math.Max(graceSeconds, 1) * 2);
            var now = DateTime.UtcNow;
            List<string> emptied = null;

            foreach (var kv in _pendingStops)
            {
                int before = kv.Value.Count;
                kv.Value.RemoveAll(b =>
                    b.Order == null || !ProvidesCoverage(b.Order.OrderState) || now - b.BufferedAtUtc > ttl);

                if (kv.Value.Count != before)
                {
                    LogEvent(kv.Key.Split('|')[0], "FSM_PENDING_STOP_EXPIRED",
                        $"{kv.Key}: expired {before - kv.Value.Count} buffered stop(s) that no position "
                        + $"claimed within {ttl.TotalSeconds:F0}s.");
                }

                if (kv.Value.Count == 0)
                    (emptied ?? (emptied = new List<string>())).Add(kv.Key);
            }

            if (emptied != null)
                foreach (var key in emptied) _pendingStops.Remove(key);
        }

        // -- Lockout phase enforcement (event-driven) --
        // Called from ExecutePositionUpdate and ExecuteOrderUpdate. Returns
        // actions for the phased lockout: PendingCancel -> PendingFlatten -> Confirmed.
        // Only Confirmed stops emitting actions. This replaces the sweep-based
        // lockout loop with event-driven state transitions.
        internal List<GuardAction> EvaluateLockoutPhase(Account account, AccountState stateModel)
        {
            var actions = new List<GuardAction>();

            // P1-54: end a lockout whose deadline has passed. The lockout test elsewhere is
            // `IsLockedOut || UtcNow < LockoutUntil` -- an OR -- so the flag outlives its own
            // deadline unless something clears it, and nothing did. Only the daily session reset
            // and a manual UnlockAccount ever cleared it, which made Overtrading.LockoutMinutes
            // decorative: three accounts sat locked out for three hours on 2026-08-10 after a
            // 60-minute lockout and had to be released by hand.
            //
            // MinValue means "no deadline", NOT "expired". LockAccount(name, -1) uses exactly that
            // to express an EOD lockout, so lapsing on MinValue would silently unlock every
            // deliberate hold-until-session-reset.
            if (stateModel.IsLockedOut
                && stateModel.LockoutUntil > DateTime.MinValue
                && DateTime.UtcNow >= stateModel.LockoutUntil)
            {
                stateModel.IsLockedOut = false;
                stateModel.ResetLockoutPhase();   // P2-101
                _stateDirty = true;
                LogEvent(stateModel.AccountName, "LOCKOUT_LAPSED",
                    $"Lockout deadline {stateModel.LockoutUntil:o} has passed; the account is tradeable again.");
                return actions;
            }

            if (!stateModel.IsLockedOut && DateTime.UtcNow >= stateModel.LockoutUntil)
            {
                // Not locked out -> reset phase if it was left dirty
                if (stateModel.CurrentLockoutPhase != AccountState.LockoutPhase.None)
                {
                    stateModel.ResetLockoutPhase();   // P2-101
                }
                return actions;
            }

            // P2-101. See EnterLockoutPhase / LockoutPhaseAttemptBudget below the method.

            // Check actual account state (not stale memory)
            bool hasWorkingOrders = false;
            bool hasOpenPosition = false;
            foreach (Order o in account.Orders)
            {
                if (o.OrderState == OrderState.Working || o.OrderState == OrderState.Submitted ||
                    o.OrderState == OrderState.Accepted || o.OrderState == OrderState.Initialized)
                {
                    hasWorkingOrders = true;
                    break;
                }
            }
            foreach (Position p in account.Positions)
            {
                if (p.MarketPosition != MarketPosition.Flat)
                {
                    hasOpenPosition = true;
                    break;
                }
            }

            // Confirmed: all clean
            if (!hasWorkingOrders && !hasOpenPosition)
            {
                if (stateModel.CurrentLockoutPhase != AccountState.LockoutPhase.Confirmed)
                {
                    stateModel.CurrentLockoutPhase = AccountState.LockoutPhase.Confirmed;
                    LogEvent(stateModel.AccountName, "LOCKOUT_CONFIRMED",
                        "Lockout confirmed: all orders cancelled, position flat.");
                }
                return actions;
            }

            // Phase: PendingCancel -> cancel all working orders
            if (stateModel.CurrentLockoutPhase == AccountState.LockoutPhase.None ||
                stateModel.CurrentLockoutPhase == AccountState.LockoutPhase.PendingCancel)
            {
                if (hasWorkingOrders)
                {
                    if (stateModel.CurrentLockoutPhase == AccountState.LockoutPhase.None)
                    {
                        EnterLockoutPhase(stateModel, AccountState.LockoutPhase.PendingCancel,
                            "Phase: PendingCancel - cancelling all working orders");
                    }
                    if (DateTime.UtcNow > stateModel.LastLockoutFlattenAttempt.AddSeconds(3)
                        && stateModel.LockoutPhaseAttempts < LockoutPhaseAttemptBudget())
                    {
                        actions.Add(new GuardAction
                        {
                            AccountName = stateModel.AccountName,
                            ActionType = GuardActionType.CancelAllOrders,
                            RuleId = "LOCKOUT_CANCEL"
                        });
                        stateModel.LastLockoutFlattenAttempt = DateTime.UtcNow;
                        stateModel.LockoutPhaseAttempts++;
                    }
                }
                else
                {
                    EnterLockoutPhase(stateModel, AccountState.LockoutPhase.PendingFlatten,
                        "Phase: PendingFlatten - orders cancelled, now flattening position");
                    stateModel.LastLockoutFlattenAttempt = DateTime.MinValue; // Allow immediate flatten action emit
                }
            }

            // Phase: PendingFlatten -> flatten the position
            if (stateModel.CurrentLockoutPhase == AccountState.LockoutPhase.PendingFlatten)
            {
                if (hasOpenPosition)
                {
                    if (DateTime.UtcNow > stateModel.LastLockoutFlattenAttempt.AddSeconds(5)
                        && stateModel.LockoutPhaseAttempts < LockoutPhaseAttemptBudget())
                    {
                        actions.Add(new GuardAction
                        {
                            AccountName = stateModel.AccountName,
                            ActionType = GuardActionType.FlattenPosition,
                            RuleId = "LOCKOUT_FLATTEN"
                        });
                        stateModel.LastLockoutFlattenAttempt = DateTime.UtcNow;
                        stateModel.LockoutPhaseAttempts++;
                        LogEvent(stateModel.AccountName, "LOCKOUT_FLATTEN_RETRY",
                            $"Flatten attempt {stateModel.LockoutPhaseAttempts} of "
                            + $"{LockoutPhaseAttemptBudget()} for {stateModel.AccountName} "
                            + "(position still open)");
                    }
                }
                else
                {
                    if (!hasWorkingOrders)
                    {
                        stateModel.CurrentLockoutPhase = AccountState.LockoutPhase.Confirmed;
                        LogEvent(stateModel.AccountName, "LOCKOUT_CONFIRMED",
                            "Lockout confirmed: all orders cancelled, position flat.");
                    }
                }
            }

            // P2-101. Give up ONCE and say so, rather than retrying forever and saying it forever.
            //
            // ⚠️ The warning this replaces could NEVER FIRE. It read
            // `UtcNow > LastLockoutFlattenAttempt.AddSeconds(30)`, and the retry above sets
            // `LastLockoutFlattenAttempt = UtcNow` every 5 seconds -- so the interval it measured
            // was reset by the very loop it was watching, and could not reach 30. The live run
            // that found P2-101 produced 13 rounds of retries and zero LOCKOUT_STUCK lines. The
            // ONE alarm that would have told an operator the guard was not getting the position
            // closed was unreachable, in the same block as an alarm that never stopped.
            //
            // It is keyed on the attempt COUNT now -- the same thing that bounds the retry -- so
            // the two cannot drift apart, and `LockoutStuckLogged` makes it exactly one line.
            bool exhausted = stateModel.LockoutPhaseAttempts >= LockoutPhaseAttemptBudget();
            if (exhausted && (hasOpenPosition || hasWorkingOrders) && !stateModel.LockoutStuckLogged)
            {
                stateModel.LockoutStuckLogged = true;
                LogEvent(stateModel.AccountName, "LOCKOUT_STUCK",
                    $"GIVING UP after {stateModel.LockoutPhaseAttempts} attempt(s) in phase "
                    + $"{stateModel.CurrentLockoutPhase}. Position open: {hasOpenPosition}, "
                    + $"working orders: {hasWorkingOrders}. "
                    + (IsActingMode()
                        ? "Manual intervention required."
                        : "This is SHADOW mode -- no flatten was ever sent, so the position was "
                          + "never going to close. Nothing is wrong with the account.")
                    + $" Account: {stateModel.AccountName}");
            }

            return actions;
        }

        // P2-101. How many intervention attempts one lockout phase may emit before it gives up.
        //
        // ⚠️ ONE in a non-acting mode, and that is the whole defect, not a tuning choice.
        // `ProcessAction` answers "SHADOW (SKIPPED)" for every action outside `live`, so the
        // position cannot close, so "is the position still open" -- the retry's exit condition --
        // is permanently true. A second identical `[SHADOW] Would execute FlattenPosition` line
        // carries no information the first did not: shadow's product is the OBSERVATION, and the
        // observation is complete after one. Measured before this: ~12 lines/minute/account,
        // indefinitely, across three sim accounts and the funded one.
        //
        // SIX in live -- the retries are 5s apart, so that is the ~30 seconds the old (unreachable)
        // stuck warning was written for. Both numbers now come from here, so the retry and the
        // give-up warning cannot disagree.
        private int LockoutPhaseAttemptBudget()
        {
            return IsActingMode() ? 6 : 1;
        }

        // Entering a phase resets its attempt budget and its give-up flag. Precondition: caller
        // holds _stateLock.
        private void EnterLockoutPhase(AccountState stateModel, AccountState.LockoutPhase phase, string message)
        {
            stateModel.CurrentLockoutPhase = phase;
            stateModel.LockoutPhaseAttempts = 0;
            stateModel.LockoutStuckLogged = false;
            LogEvent(stateModel.AccountName, "LOCKOUT_PHASE", message);
        }

        // -- Aggregate sizing (event-driven via PositionUpdate) --
        // Scans all accounts' positions instantly on any position change.
        internal List<GuardAction> EvaluateAggregateSizing()
        {
            var actions = new List<GuardAction>();
            if (!_isArmed) return actions;

            int totalAggregateContracts = 0;
            int maxSingleAccountContracts = 0;
            foreach (var accName in _subscribedAccounts)
            {
                if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accName)) continue;
                if (!_accountStates.TryGetValue(accName, out var st)) continue;
                int accContracts = 0;
                foreach (var pos in st.Positions.Values)
                {
                    if (pos.MarketPosition != MarketPosition.Flat) accContracts += pos.Quantity;
                }
                totalAggregateContracts += accContracts;
                if (accContracts > maxSingleAccountContracts) maxSingleAccountContracts = accContracts;
            }

            int copies = _config.Sizing.ExpectedCopies > 0 ? _config.Sizing.ExpectedCopies : 1;
            int normalizedAggregate = copies > 1 ? maxSingleAccountContracts : totalAggregateContracts;

            if (normalizedAggregate > _config.Sizing.MaxContractsAggregate)
            {
                LogEvent("SYSTEM", "AGGREGATE_SIZE_BREACH", new JObject
                {
                    { "totalContracts", totalAggregateContracts },
                    { "maxSingleAccount", maxSingleAccountContracts },
                    { "expectedCopies", copies },
                    { "normalizedAggregate", normalizedAggregate },
                    { "limit", _config.Sizing.MaxContractsAggregate }
                });

                foreach (var accName in _subscribedAccounts)
                {
                    if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accName)) continue;
                    if (!_accountStates.TryGetValue(accName, out var st)) continue;
                    bool hasPosition = st.Positions.Values.Any(p => p.MarketPosition != MarketPosition.Flat);
                    if (hasPosition)
                    {
                        // Throttle aggregate flatten using LastLockoutFlattenAttempt
                        if (DateTime.UtcNow > st.LastLockoutFlattenAttempt.AddSeconds(5))
                        {
                            actions.Add(new GuardAction
                            {
                                AccountName = accName,
                                ActionType = GuardActionType.FlattenPosition,
                                RuleId = "AGGREGATE_SIZE_BREACH"
                            });
                            st.LastLockoutFlattenAttempt = DateTime.UtcNow;
                        }
                    }
                }
            }

            return actions;
        }

        internal List<GuardAction> EvaluateRules(Account account, AccountState stateModel)
        {
            if (!_isArmed || (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(stateModel.AccountName)))
            {
                return new List<GuardAction>();
            }
            var actions = new List<GuardAction>();

            var profile = GetResolvedProfile(account);
            if (profile == null) return actions;

            // Rule 1: Max Size
            foreach (var posPair in stateModel.Positions)
            {
                var pos = posPair.Value;
                if (pos.MarketPosition != MarketPosition.Flat)
                {
                    int limit = profile.DefaultMaxContracts;
                    string baseSymbol = pos.InstrumentObj?.MasterInstrument?.Name ?? pos.Instrument.Split(' ')[0];
                    
                    if (profile.InstrumentProfiles.TryGetValue(baseSymbol, out var instrProfile))
                    {
                        limit = instrProfile.MaxContracts;
                    }
                    else if (profile.InstrumentProfiles.TryGetValue(pos.Instrument, out var exactProfile))
                    {
                        limit = exactProfile.MaxContracts;
                    }

                    if (pos.Quantity > limit)
                    {
                        MarkRuleLockout(stateModel, "MAX_SIZE_BREACH");
                        actions.Add(new GuardAction
                        {
                            AccountName = stateModel.AccountName,
                            ActionType = GuardActionType.FlattenPosition,
                            Instrument = pos.Instrument,
                            InstrumentObj = pos.InstrumentObj,
                            Quantity = pos.Quantity,
                            RuleId = "MAX_SIZE_BREACH"
                        });
                        stateModel.LastLockoutFlattenAttempt = DateTime.UtcNow;
                    }
                }
            }

            // Fix 8: Overtrading Rules
            if (stateModel.TradesToday > profile.MaxTradesPerSession)
            {
                actions.Add(new GuardAction
                {
                    AccountName = stateModel.AccountName,
                    ActionType = GuardActionType.FlattenPosition,
                    RuleId = "MAX_TRADES_BREACH"
                });
                if (!stateModel.IsLockedOut)
                {
                    MarkRuleLockout(stateModel, "MAX_TRADES_BREACH");
                    if (_config.Overtrading.LockoutMinutes > 0)
                    {
                        stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.LockoutMinutes);
                    }
                    _stateDirty = true;
                }
            }

            if (stateModel.ConsecutiveLosses >= _config.Overtrading.MaxConsecutiveLosses)
            {
                actions.Add(new GuardAction
                {
                    AccountName = stateModel.AccountName,
                    ActionType = GuardActionType.FlattenPosition,
                    RuleId = "CONSECUTIVE_LOSS_BREACH"
                });
                if (!stateModel.IsLockedOut)
                {
                    MarkRuleLockout(stateModel, "CONSECUTIVE_LOSS_BREACH");
                    if (_config.Overtrading.LockoutMinutes > 0)
                    {
                        stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.LockoutMinutes);
                    }
                    _stateDirty = true;
                }
            }

            if (DateTime.UtcNow < stateModel.CooldownUntil)
            {
                bool hasOpen = stateModel.Positions.Values.Any(p => p.MarketPosition != MarketPosition.Flat);
                if (hasOpen)
                {
                    actions.Add(new GuardAction
                    {
                        AccountName = stateModel.AccountName,
                        ActionType = GuardActionType.FlattenPosition,
                        RuleId = "COOLDOWN_BREACH"
                    });
                }
            }

            // PnL rules (Daily Loss, Trailing Drawdown) have been migrated to
            // EvaluatePnLRules (called from AccountItemUpdate). They are no longer
            // evaluated here to avoid duplicate-fire when both PositionUpdate and
            // AccountItemUpdate fire for the same logical state change.
            // PeakEquity is still tracked here as a fallback in case AccountItemUpdate
            // hasn't fired yet (e.g. position just opened and PnL hasn't changed).
            double currentPnL = stateModel.RealizedPnL + stateModel.UnrealizedPnL;
            if (currentPnL > stateModel.PeakEquity)
            {
                stateModel.PeakEquity = currentPnL;
            }

            // Rule 4: Edge Window Gate (if enabled)
            if (_config.EnableWindowGate)
            {
                foreach (var posPair in stateModel.Positions)
                {
                    var pos = posPair.Value;
                    if (pos.MarketPosition != MarketPosition.Flat && pos.LastNonFlatTransition != DateTime.MinValue)
                    {
                        DateTime timeEt = TimeZoneInfo.ConvertTimeFromUtc(pos.LastNonFlatTransition, _etZone);
                        if (!IsInsidePermittedWindows(timeEt))
                        {
                            actions.Add(new GuardAction
                            {
                                AccountName = stateModel.AccountName,
                                ActionType = GuardActionType.FlattenPosition,
                                Instrument = pos.Instrument,
                                InstrumentObj = pos.InstrumentObj,
                                RuleId = "EDGE_WINDOW_BREACH"
                            });
                        }
                    }
                }
            }

            // Rule 5: Stop-Loss Guard has been migrated to the per-position FSM
            // (see -6 of RiskGuardAddOn.md). The FSM owns the grace timer and
            // emits MISSING_STOP_* via EvaluateGraceExpiry(); EvaluateRules no
            // longer snapshots account.Orders for this rule, which was the
            // source of the duplicate-SL race on OCO brackets.

            return actions;
        }

        private bool IsInsidePermittedWindows(DateTime timeEt)
        {
            if (_parsedWindows.Count == 0) return true;

            DayOfWeek dayOfWeek = timeEt.DayOfWeek;
            TimeSpan currentTime = timeEt.TimeOfDay;

            foreach (var win in _parsedWindows)
            {
                if (win.Days.Contains(dayOfWeek))
                {
                    if (currentTime >= win.Start && currentTime <= win.End)
                    {
                        return true;
                    }
                }
            }
            return false;
        }

        // -
        // ACTION ARBITER & EXECUTOR
        // -

        public string GetMode()
        {
            return _mode;
        }

        public bool IsArmed
        {
            get { return _isArmed; }
        }

        // FR-31: Arming ritual preflight. Returns true only when all checks pass:
        //   (a) config loaded and valid, (b) at least one non-excluded account connected,
        //   (c) guard mode is a recognised enforcement mode or shadow.
        // Any failure blocks arming and reports which check failed (logged).
        public PreflightResult RunPreflight()
        {
            var result = new PreflightResult();
            // (a) config loaded?
            if (_config == null)
            {
                result.Fail("CONFIG", "RiskConfig not loaded");
                return result;
            }
            // (b) at least one connected, non-excluded account?
            int connected = 0;
            foreach (Account a in Account.All)
            {
                if (a == null) continue;
                if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(a.Name)) continue;
                connected++;
            }
            if (connected == 0)
                result.Fail("ACCOUNTS", "No connected non-excluded accounts found");
            // (c) mode recognised?
            if (_mode != "shadow" && _mode != "live" && _mode != "pure" && _mode != "override_with_friction")
                result.Fail("MODE", $"Unrecognised mode '{_mode}'");
            // (c2) stop-guard OnMissing action recognised? Applies in every mode.
            string onMissing = _config.StopGuard?.OnMissing;
            if (onMissing != "AutoStop" && onMissing != "Flatten")
                result.Fail("STOP_GUARD_ON_MISSING", $"Unrecognised StopGuard.OnMissing value '{onMissing}'");
            // (d) FR-29 soft gate: live enforcement modes require MinShadowSessions completed shadow sessions.
            // P2-93: only "live" is an acting mode (IsActingMode returns true only for "live"), so
            // pure and override_with_friction pass this gate and then ProcessAction answers
            // SHADOW (SKIPPED) for both -- an operator waits out five shadow sessions to reach a
            // mode that enforces nothing. Fail-closed: stop recognising them here. Implementing
            // them is a protection increase and the operator's call; until then preflight must
            // not claim the gate was satisfied.
            if (_mode == "live"
                && _config.MinShadowSessions > 0
                && _shadowSessionsCompleted < _config.MinShadowSessions)
            {
                result.Fail("SHADOW_SESSIONS",
                    $"Only {_shadowSessionsCompleted} shadow session(s) completed; MinShadowSessions={_config.MinShadowSessions} required before live arming.");
            }
            // (e) FR-36: override friction minimums enforced.
            if (_mode == "override_with_friction" && _config.Override != null && _config.Override.WaitSeconds < 30)
                result.Fail("OVERRIDE_FRICTION", "Override.WaitSeconds below FR-36 enforced minimum of 30s.");
            // P2-93: pure and override_with_friction are recognised modes but IsActingMode()
            // returns true only for "live", so ProcessAction answers SHADOW (SKIPPED) for both.
            // An operator who passes the MinShadowSessions gate and arms in either mode gets
            // observation-only enforcement with an acting-mode label. Fail-closed: refuse to
            // arm until the mode is implemented. Use "live" or "shadow" until then.
            if (_mode == "pure" || _mode == "override_with_friction")
                result.Fail("MODE_NOT_IMPLEMENTED",
                    $"Mode '{_mode}' is recognised but not implemented -- IsActingMode() returns true only for 'live', " +
                    "so ProcessAction would answer SHADOW (SKIPPED) for every breach. Use 'live' or 'shadow' until this mode is wired.");
            // (f) FirmMirror validation (P2-8, F-9b): if enabled, every mapped account must exist on the platform,
            // its firm must exist in FirmProfiles, and each referenced firm profile must have non-zero amounts when its sub-rule is enabled.
            if (_config.FirmMirror != null && _config.FirmMirror.Enabled)
            {
                var fm = _config.FirmMirror;

                // F-9b: every mapped account name must resolve in Account.All (OrdinalIgnoreCase), regardless of equity.
                if (result.Passed && fm.AccountFirmMap != null)
                {
                    int platformAccountCount = 0;
                    var accountNameSet = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                    foreach (Account a in Account.All)
                    {
                        if (a != null)
                        {
                            platformAccountCount++;
                            if (!string.IsNullOrEmpty(a.Name))
                                accountNameSet.Add(a.Name);
                        }
                    }

                    foreach (var kvp in fm.AccountFirmMap)
                    {
                        if (string.IsNullOrEmpty(kvp.Value))
                            continue;

                        if (!accountNameSet.Contains(kvp.Key))
                        {
                            result.Fail("FIRM_MIRROR", $"Account '{kvp.Key}' mapped to firm '{kvp.Value}' was not found among the {platformAccountCount} account(s) reported by the platform. Correct the account name or connect the account.");
                            break;
                        }
                    }
                }

                // F-9b (2/2): mapped account equity must match the plan's AccountSize within 40% magnitude.
                if (result.Passed && fm.AccountFirmMap != null && fm.FirmProfiles != null)
                {
                    var accountByName = new Dictionary<string, Account>(StringComparer.OrdinalIgnoreCase);
                    foreach (Account a in Account.All)
                    {
                        if (a != null && !string.IsNullOrEmpty(a.Name))
                            accountByName[a.Name] = a;
                    }

                    foreach (var kvp in fm.AccountFirmMap)
                    {
                        if (string.IsNullOrEmpty(kvp.Value))
                            continue;

                        if (!fm.FirmProfiles.TryGetValue(kvp.Value, out var profile) || profile == null)
                            continue;

                        double accountSize = (double)profile.AccountSize;
                        if (accountSize <= 0)
                            continue;

                        if (!accountByName.TryGetValue(kvp.Key, out var account))
                            continue;

                        double cashValue = account.Get(AccountItem.CashValue, Currency.UsDollar);
                        double unrealized = account.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar);
                        double equity = cashValue + unrealized;

                        // 89 of the 96 accounts on this box report zero equity -- expired or
                        // unconnected prop accounts the connection still lists -- so an unreadable
                        // equity must be SKIPPED, not failed: refusing over those would mean the
                        // guard never arms here again. The existence check above still applies to
                        // them, which is what stops this exemption swallowing the whole gate.
                        //
                        // ⚠️ WRITTEN AS `!(equity > 0)`, NOT `equity <= 0`, AND THAT IS THE POINT.
                        // Every comparison against NaN is false, so `NaN <= 0` does not skip and
                        // `NaN > 0.40` does not fail -- a NaN equity would slide through BOTH
                        // guards and the check would silently PASS. Fail-open in a validator is the
                        // one direction that matters, and `account.Get` can return NaN before a
                        // provider has synced. Inverting the comparison handles NaN in the same
                        // operator rather than needing a second branch. Raised by the review panel;
                        // it upheld two findings on this patch and this was the one that held.
                        if (!(equity > 0.0))
                            continue;

                        double relativeDifference = Math.Abs(equity - accountSize) / accountSize;
                        if (relativeDifference > 0.40)
                        {
                            result.Fail("FIRM_MIRROR", $"Plan '{kvp.Value}' AccountSize {accountSize} does not match account '{kvp.Key}' observed equity {equity}; relative difference exceeds 40%.");
                            break;
                        }
                    }
                }

                // P2-8: every mapped firm must exist in FirmProfiles.
                if (result.Passed && fm.AccountFirmMap != null)
                {
                    foreach (var kvp in fm.AccountFirmMap)
                    {
                        if (!string.IsNullOrEmpty(kvp.Value) && (fm.FirmProfiles == null || !fm.FirmProfiles.ContainsKey(kvp.Value)))
                        {
                            result.Fail("FIRM_MIRROR", $"Account '{kvp.Key}' mapped to unknown firm '{kvp.Value}'. Add it to FirmProfiles or clear the mapping.");
                            break;
                        }
                    }
                }

                // P2-8: enabled firm sub-rules must have positive amounts.
                if (result.Passed && fm.FirmProfiles != null)
                {
                    foreach (var fp in fm.FirmProfiles)
                    {
                        if (fp.Value.TrailingDD != null && fp.Value.TrailingDD.Enabled && fp.Value.TrailingDD.Amount <= 0)
                        {
                            result.Fail("FIRM_MIRROR", $"Firm '{fp.Key}' has TrailingDD enabled but Amount <= 0. Populate real firm limits before arming.");
                            break;
                        }
                        if (fp.Value.DailyLoss != null && fp.Value.DailyLoss.Enabled && fp.Value.DailyLoss.Amount <= 0)
                        {
                            result.Fail("FIRM_MIRROR", $"Firm '{fp.Key}' has DailyLoss enabled but Amount <= 0. Populate real firm limits before arming.");
                            break;
                        }
                    }
                }
            }
            if (result.Passed)
                LogEvent("SYSTEM", "PREFLIGHT", "Preflight passed; arming permitted.");
            else
                LogEvent("SYSTEM", "PREFLIGHT_FAIL", $"Preflight failed: {result.FailureCode} - {result.FailureMessage}");
            return result;
        }

        public class PreflightResult
        {
            public bool Passed = true;
            public string FailureCode = "";
            public string FailureMessage = "";
            public void Fail(string code, string msg) { Passed = false; FailureCode = code; FailureMessage = msg; }
        }

        // FR-30/31: arming now requires a successful preflight. ToggleArmed() will refuse to
        // transition from disarmed -> armed unless RunPreflight() passes. Disarming is always allowed.
        public void ToggleArmed()
        {
            // P1-12: captured inside the lock, written outside it. Arming is rare enough that the
            // disk write was never a latency problem in itself -- but _stateLock is re-entrant, so
            // leaving it here meant `SavePersistedState` could not enforce "never under the lock"
            // for anybody.
            PersistedStateData toWrite = null;
            lock (_stateLock)
            {
                if (!_isArmed)
                {
                    // disarmed -> armed: gate on preflight
                    var pf = RunPreflight();
                    if (!pf.Passed)
                    {
                        LogEvent("SYSTEM", "ARM_BLOCKED", $"Arming refused: preflight failed ({pf.FailureCode}).");
                        return;
                    }
                }
                _isArmed = !_isArmed;
                LogEvent("SYSTEM", "TOGGLE_ARMED", $"System Armed State changed to: {_isArmed}");

                // P1-15: UpdateFsmOnPosition/UpdateFsmOnOrder both return early while disarmed,
                // so any position opened during that window is invisible to the guard. Re-deriving
                // state on the way in is the only way arming means anything for those positions;
                // otherwise the guard reports armed and healthy while covering nothing until the
                // position next changes side. Seeding is idempotent (it skips keys already
                // tracked) and makes no broker calls, so it is safe under _stateLock.
                if (_isArmed)
                {
                    foreach (var accName in _subscribedAccounts)
                    {
                        var account = Account.All.FirstOrDefault(a => a.Name == accName);
                        if (account != null) SeedFsmsForExistingPositions(account);
                    }
                }

                toWrite = CapturePersistedState();
            }

            WritePersistedState(toWrite);
        }

        public string TriggerManualFlatten(string accountName)
        {
            var action = new GuardAction
            {
                AccountName = accountName,
                ActionType = GuardActionType.FlattenPosition,
                RuleId = "MANUAL_PANIC"
            };
            return ProcessAction(action, forceLive: true);
        }

        public string TriggerManualFlattenAll()
        {
            var results = new List<string>();
            foreach (var account in Account.All)
            {
                var action = new GuardAction
                {
                    AccountName = account.Name,
                    ActionType = GuardActionType.FlattenPosition,
                    RuleId = "MANUAL_PANIC_ALL"
                };
                results.Add($"{account.Name}: {ProcessAction(action, forceLive: true)}");
            }
            return string.Join("; ", results);
        }

        // FR-35/36: friction-gated lockout override. In "override_with_friction" mode, escaping a
        // lockout requires the exact confirm phrase AND a forced wait (enforced min 30s).
        // Returns true if the override succeeded and the account was unlocked.
        // In "pure" mode this always returns false (no in-session override allowed).
        // In "shadow" mode the friction is still enforced for practice, but no real lockout existed.
        public bool OverrideLockout(string accountName, string confirmPhrase, out string reason)
        {
            reason = "";
            if (_mode == "pure")
            {
                reason = "Override not permitted in 'pure' enforcement mode; lockouts clear only at session reset.";
                LogEvent(accountName, "OVERRIDE_REJECTED", reason);
                return false;
            }
            if (_mode != "override_with_friction" && _mode != "shadow")
            {
                reason = $"Override not implemented for mode '{_mode}'.";
                return false;
            }
            // FR-36: clamp wait to enforced minimum.
            int waitSec = _config.Override?.WaitSeconds ?? 120;
            if (waitSec < 30) waitSec = 30;
            string expected = _config.Override?.ConfirmPhrase ?? "I understand locked means locked";
            if (!string.Equals(confirmPhrase, expected, StringComparison.Ordinal))
            {
                reason = "Confirm phrase does not match. Override refused.";
                LogEvent(accountName, "OVERRIDE_REJECTED", "Incorrect confirm phrase.");
                return false;
            }
            // The forced wait is enforced by the caller (UI/CLI) — this method performs the unlock
            // only after the wait has elapsed. We log the intent and the wait duration.
            LogEvent(accountName, "OVERRIDE_ACCEPTED",
                $"Confirm phrase accepted; applying override after {waitSec}s friction wait. Account will be unlocked.");
            UnlockAccount(accountName);
            reason = $"Override applied after {waitSec}s wait.";
            return true;
        }

        public void UnlockAccount(string accountName)
        {
            PersistedStateData toWrite = null;   // P1-12: captured under the lock, written after it
            lock (_stateLock)
            {
                if (_accountStates.TryGetValue(accountName, out var state))
                {
                    var account = Account.All.FirstOrDefault(a => a.Name == accountName);
                    double currentRealized = account != null ? account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar) : 0.0;

                    state.IsLockedOut = false;
                    state.LockoutUntil = DateTime.MinValue;
                    state.PeakEquity = 0.0;
                    state.PeakOpenGain = 0.0;
                    state.PeakGivebackTriggered = false;
                    state.PeakGivebackLastTriggerUnrealized = double.NaN;
                    state.TradesToday = 0;
                    state.ConsecutiveLosses = 0;
                    state.CooldownUntil = DateTime.MinValue;
                    state.SessionStartRealizedPnL = currentRealized;
                    state.LastRealizedPnL = currentRealized;
                    state.RealizedPnL = 0.0;
                    state.UnrealizedPnL = 0.0;
                    state.ResetLockoutPhase();   // P2-101

                    // Sync positions to avoid stale memory
                    state.Positions.Clear();
                    if (account != null)
                    {
                        foreach (Position p in account.Positions)
                        {
                            if (p.MarketPosition != MarketPosition.Flat)
                            {
                                double unrealized = 0.0;
                                try { unrealized = p.GetUnrealizedProfitLoss(PerformanceUnit.Currency); } catch { }
                                state.UpdatePosition(account, p.Instrument, p.MarketPosition, p.Quantity, p.AveragePrice, unrealized, _config);
                            }
                        }
                    }

                    LogEvent(accountName, "UNLOCK", "Account manually unlocked from dashboard. Metrics reset and synchronized.");
                    toWrite = CapturePersistedState();
                }
            }

            WritePersistedState(toWrite);
        }

        public void LockAccount(string accountName, int minutes)
        {
            lock (_stateLock)
            {
                if (_accountStates.TryGetValue(accountName, out var state))
                {
                    if (minutes == -1)
                    {
                        state.IsLockedOut = true; // P2-92: manual lockout is an operator instruction, not a rule breach; it must bite in every mode.
                        state.LockoutWasShadowOnly = false;
                        state.LockoutUntil = DateTime.MinValue;
                    }
                    else if (minutes > 0)
                    {
                        state.LockoutUntil = DateTime.UtcNow.AddMinutes(minutes);
                        state.InitialLockoutFlattened = false; // force flatten sweep
                    }
                    _stateDirty = true;
                    LogEvent(accountName, "MANUAL_LOCKOUT", "Account locked from dashboard for " + (minutes == -1 ? "EOD" : minutes + " minutes"));
                }
            }
        }

        internal bool IsActingMode(bool forceLive = false)
        {
            lock (_stateLock)
            {
                return _mode == "live" || forceLive;
            }
        }

        private void MarkRuleLockout(AccountState st, string ruleId)
        {
            st.IsLockedOut = true;
            st.LockoutWasShadowOnly = !IsActingMode();
            _stateDirty = true;
            if (st.LockoutWasShadowOnly)
            {
                LogEvent(st.AccountName, "SHADOW_LOCKOUT", $"Rule {ruleId} recorded a shadow-only lockout observation; no flatten executed.");
            }
        }

        internal string ProcessAction(GuardAction action, bool forceLive = false)
        {
            bool isLive = false;
            lock (_stateLock)
            {
                // 1. ActionArbiter - Check Invariant (Risk-Reducing Only)
                if (!ValidateInvariant(action))
                {
                    LogEvent(action.AccountName, "ARBITER_REJECTED", $"Arbiter rejected action {action.ActionType} - would increase risk or target is invalid.");
                    return "REJECTED (INVARIANT VIOLATION)";
                }

                // 2. Mode Check (Shadow Mode Gate)
                isLive = IsActingMode(forceLive);
                if (!isLive)
                {
                    string alsoShadow = (action.MergedRuleIds != null && action.MergedRuleIds.Count > 0)
                        ? $" (also: {string.Join(", ", action.MergedRuleIds)})" : "";
                    LogEvent(action.AccountName, "SHADOW_ACTION", $"[SHADOW] Would execute action {action.ActionType} triggered by {action.RuleId}{alsoShadow}");
                    return "SHADOW (SKIPPED)";
                }
            }

            // 3. Executor - Run the action (released lock to prevent deadlock with event dispatch thread)
            try
            {
                ExecuteAction(action);
                LogEvent(action.AccountName, "INTERVENTION", $"Executed action {action.ActionType} triggered by {action.RuleId}");
                return "EXECUTED";
            }
            catch (Exception ex)
            {
                LogEvent(action.AccountName, "EXECUTION_ERROR", $"Failed to execute {action.ActionType}: {ex.Message}");
                return $"ERROR: {ex.Message}";
            }
        }

        // Precondition: caller must hold _stateLock.
        private bool ValidateInvariant(GuardAction action)
        {
            var account = Account.All.FirstOrDefault(a => a.Name == action.AccountName);
            if (account == null) return false;

            if (action.ActionType == GuardActionType.FlattenPosition)
            {
                return true; 
            }

            if (action.ActionType == GuardActionType.CancelAllOrders)
            {
                return true;
            }

            if (action.ActionType == GuardActionType.CancelOrder)
            {
                return !string.IsNullOrEmpty(action.OrderId);
            }

            if (action.ActionType == GuardActionType.PlaceStopOrder)
            {
                // A stop order is risk-reducing only when it closes an existing,
                // same-side live position. The actual stop quantity is sized from
                // the live position in ExecuteAction, so the arbiter only verifies
                // that a coverable position exists and the action side matches it.
                // Do not mutate state or call trading methods.
                if (action.InstrumentObj == null || action.Quantity <= 0)
                    return false;

                var position = account.Positions.FirstOrDefault(p => p.Instrument != null && p.Instrument.FullName == action.Instrument);
                if (position == null || position.MarketPosition == MarketPosition.Flat)
                    return false;

                string key = FsmKey(action.AccountName, action.Instrument);
                if (!_guardFsms.TryGetValue(key, out var fsm))
                    return false;
                if (fsm.PositionSide != position.MarketPosition)
                    return false;
                if (fsm.State == GuardFsmState.Protected || fsm.State == GuardFsmState.ProtectedPending)
                    return false;

                int liveQuantity = (int)position.Quantity;
                if (liveQuantity <= 0)
                    return false;

                return true;
            }

            return false;
        }

        // P1-19: one EvaluatePnLRules pass can append five FlattenPosition actions -- daily loss,
        // trailing DD, news shield, evaluation target and peak giveback -- each of which
        // independently walks the account and calls Flatten. Coalesce by
        // (AccountName, ActionType, Instrument) before processing.
        internal static List<GuardAction> CoalesceActions(List<GuardAction> actions)
        {
            if (actions == null || actions.Count <= 1) return actions;

            // An account-wide flatten supersedes every scoped flatten for the same account: the
            // wide call closes those instruments anyway, so keeping both re-issues a broker call
            // against an account that is already flat.
            var accountWideFlatten = new HashSet<string>();
            foreach (var a in actions)
            {
                if (a != null && a.ActionType == GuardActionType.FlattenPosition
                    && string.IsNullOrEmpty(a.Instrument))
                {
                    accountWideFlatten.Add(a.AccountName ?? "");
                }
            }

            var survivors = new Dictionary<string, GuardAction>();
            var ordered = new List<GuardAction>();
            foreach (var a in actions)
            {
                if (a == null) continue;

                if (a.ActionType == GuardActionType.FlattenPosition
                    && !string.IsNullOrEmpty(a.Instrument)
                    && accountWideFlatten.Contains(a.AccountName ?? ""))
                {
                    continue;
                }

                string key = (a.AccountName ?? "") + "|" + a.ActionType + "|" + (a.Instrument ?? "");
                GuardAction survivor;
                if (survivors.TryGetValue(key, out survivor))
                {
                    // Merging must not erase WHY the other rules fired. The surviving action
                    // keeps its own RuleId (callers and tests match on it) and carries the rest
                    // so the audit line can name every rule that demanded this action.
                    if (survivor.MergedRuleIds == null) survivor.MergedRuleIds = new List<string>();
                    if (!string.IsNullOrEmpty(a.RuleId) && a.RuleId != survivor.RuleId
                        && !survivor.MergedRuleIds.Contains(a.RuleId))
                    {
                        survivor.MergedRuleIds.Add(a.RuleId);
                    }
                    continue;
                }

                survivors[key] = a;
                ordered.Add(a);
            }
            return ordered;
        }

        // P2-107. The accounts the account-wide producers (EvaluateAggregateSizing, the safety
        // sweep) iterate. It mirrors their filter exactly on purpose: a scope that does not match
        // what the producer actually looked at is the one way this mechanism goes silently wrong,
        // in either direction -- too narrow and a record never clears, too wide and it clears on
        // an evaluation that never happened.
        //
        // Takes _stateLock itself rather than declaring a precondition: one caller is inside the
        // lock (ExecutePositionUpdateDetails) and one is outside it (ExecuteSafetySweep, which
        // dispatches after releasing it per P1-10). _stateLock is reentrant, so this is correct
        // from both.
        internal List<string> AggregateEvaluatedAccounts()
        {
            var names = new List<string>();
            lock (_stateLock)
            {
                foreach (var accName in _subscribedAccounts)
                {
                    if (_config.ExcludedAccounts != null && _config.ExcludedAccounts.Contains(accName)) continue;
                    if (!_accountStates.ContainsKey(accName)) continue;
                    names.Add(accName);
                }
            }
            return names;
        }

        // P2-107. The de-duplication record for the outbound action path. See
        // GuardActionDeduplicator.cs for why it is here and not inside each rule; in short,
        // P2-101 fixed this shape inside EvaluateLockoutPhase and the same shape turned up on a
        // different path within the hour.
        private readonly GuardActionDeduplicator _actionDedup = new GuardActionDeduplicator();

        // P2-107. THE outbound path. Every rule-produced action goes through here: coalesced
        // within the batch (P1-19), then de-duplicated across batches, then processed.
        //
        // ⚠️ `accountsEvaluated` is not decoration and it is not derivable from `actions`. It is
        // the set of accounts this producer just looked at, INCLUDING the ones it decided needed
        // nothing -- because that decision is the only signal that a condition resolved. An
        // account left out of it keeps its record forever and will never re-announce; an account
        // wrongly included has its record cleared by a producer that did not evaluate it, which
        // restores the repetition. Pass exactly what the producer iterated.
        //
        // ⚠️ Do NOT route the operator's panic buttons through here. TriggerManualFlatten and
        // TriggerManualFlattenAll call ProcessAction(forceLive: true) directly, deliberately: a
        // second press is a second instruction, not a duplicate.
        internal void DispatchActions(List<GuardAction> actions, string producer, IList<string> accountsEvaluated)
        {
            var coalesced = CoalesceActions(actions);
            if (coalesced == null) coalesced = new List<GuardAction>();

            if (accountsEvaluated == null || accountsEvaluated.Count == 0)
            {
                // A producer that names no scope gets no de-duplication rather than no dispatch.
                // Dropping a flatten is a far worse failure than repeating one, so this path
                // fails OPEN -- and says so, because a silent bypass of the whole mechanism would
                // look exactly like it working.
                foreach (var a in coalesced)
                {
                    if (a == null) continue;
                    LogEvent(a.AccountName, "ACTION_UNSCOPED",
                        $"Producer {producer} dispatched {a.ActionType} ({a.RuleId}) without naming the"
                        + " accounts it evaluated, so P2-107 de-duplication was skipped for it.");
                    ProcessAction(a);
                }
                return;
            }

            bool acting = IsActingMode();

            var evaluated = new List<string>();
            var evaluatedSet = new HashSet<string>(StringComparer.Ordinal);
            foreach (var name in accountsEvaluated)
            {
                string n = name ?? "";
                if (evaluatedSet.Add(n)) evaluated.Add(n);
            }

            var byAccount = new Dictionary<string, List<GuardAction>>(StringComparer.Ordinal);
            var unscoped = new List<GuardAction>();
            foreach (var a in coalesced)
            {
                if (a == null) continue;
                string name = a.AccountName ?? "";
                if (!evaluatedSet.Contains(name)) { unscoped.Add(a); continue; }
                List<GuardAction> list;
                if (!byAccount.TryGetValue(name, out list))
                {
                    list = new List<GuardAction>();
                    byAccount[name] = list;
                }
                list.Add(a);
            }

            // Iterate the EVALUATED accounts, not the ones that produced actions. An account that
            // produced nothing is the whole point: that is how its record clears.
            foreach (var name in evaluated)
            {
                List<GuardAction> list;
                if (!byAccount.TryGetValue(name, out list)) list = new List<GuardAction>();

                var keys = new List<string>();
                foreach (var a in list)
                {
                    keys.Add(GuardActionDeduplicator.KeyFor(
                        a.AccountName, a.RuleId, a.ActionType.ToString(), a.Instrument));
                }

                var decisions = _actionDedup.Filter(
                    GuardActionDeduplicator.ScopeFor(producer, name), keys, acting);

                for (int i = 0; i < list.Count && i < decisions.Count; i++)
                {
                    var d = decisions[i];
                    if (d.Admit)
                    {
                        ProcessAction(list[i]);
                        continue;
                    }

                    // Exactly one line per episode. Suppressing in silence would be the inverse
                    // of the defect: the operator sees neither the action nor its absence.
                    if (d.AnnounceSuppression)
                    {
                        LogEvent(name, "ACTION_SUPPRESSED",
                            $"Holding back {list[i].ActionType} from {list[i].RuleId} on {name}"
                            + (string.IsNullOrEmpty(list[i].Instrument) ? "" : " (" + list[i].Instrument + ")")
                            + $": {d.Reason}. Attempt {d.Attempt} of budget {d.Budget}, producer {producer}."
                            + " This is the last line about it until the condition resolves.");
                    }
                }
            }

            foreach (var a in unscoped)
            {
                LogEvent(a.AccountName, "ACTION_UNSCOPED",
                    $"Producer {producer} raised {a.ActionType} ({a.RuleId}) for {a.AccountName}, which is"
                    + " not among the accounts it declared it evaluated, so P2-107 de-duplication was"
                    + " skipped for it. Dispatching anyway.");
                ProcessAction(a);
            }
        }

        private void ExecuteAction(GuardAction action)
        {
            var account = Account.All.FirstOrDefault(a => a.Name == action.AccountName);
            if (account == null) throw new Exception("Account not found");

            if (action.ActionType == GuardActionType.FlattenPosition)
            {
                // P1-19: honour action.Instrument. Without this a stop-guard flatten scoped to
                // MES closed every instrument on the account, so a missing stop on one contract
                // liquidated an unrelated, correctly-protected position. Account-level rules
                // (daily loss, trailing DD, lockout) leave Instrument unset and stay account-wide.
                bool scoped = !string.IsNullOrEmpty(action.Instrument);

                var instrumentsToFlatten = new List<Instrument>();
                foreach (Position p in account.Positions)
                {
                    if (p.MarketPosition != MarketPosition.Flat && p.Instrument != null)
                    {
                        if (scoped && !string.Equals(p.Instrument.FullName, action.Instrument, StringComparison.OrdinalIgnoreCase))
                            continue;
                        instrumentsToFlatten.Add(p.Instrument);
                    }
                }
                foreach (Order o in account.Orders)
                {
                    if ((o.OrderState == OrderState.Working || o.OrderState == OrderState.Submitted || o.OrderState == OrderState.Accepted) && o.Instrument != null)
                    {
                        if (scoped && !string.Equals(o.Instrument.FullName, action.Instrument, StringComparison.OrdinalIgnoreCase))
                            continue;
                        if (!instrumentsToFlatten.Contains(o.Instrument))
                        {
                            instrumentsToFlatten.Add(o.Instrument);
                        }
                    }
                }

                if (instrumentsToFlatten.Count > 0)
                {
                    try
                    {
                        account.Flatten(instrumentsToFlatten.ToArray());
                    }
                    catch (Exception fex)
                    {
                        LogEvent(action.AccountName, "FLATTEN_ERROR",
                            $"Flatten failed for {string.Join(",", instrumentsToFlatten.Select(i => i.FullName))}: {fex.Message}");
                        throw;
                    }
                }
            }
            else if (action.ActionType == GuardActionType.CancelAllOrders)
            {
                // P0-53: a lockout cancels the trader's working orders, but the protective stop
                // covering an OPEN position is not one of them. Cancelling it here and then
                // failing to flatten is how this path manufactures the naked position the lockout
                // exists to prevent.
                //
                // This is P1-11's hazard on P1-11's blind side. P1-11 split the SWEEP's cancel
                // batches by intent and stopped there; the lockout's PendingCancel phase also
                // emits this action, and this branch cancelled everything. The sweep's own
                // deferred batch is what eventually clears the retained stop, once the flatten is
                // confirmed and the instrument is actually flat.
                //
                // The classification is IsPositionReducingOrder's and is reused, not restated: a
                // second definition of "protective leg" would drift, and this file already has
                // one authority for the question.
                AccountState cancelState;
                lock (_stateLock) { _accountStates.TryGetValue(action.AccountName, out cancelState); }

                var orders = new List<Order>();
                var retained = new List<string>();
                foreach (Order o in account.Orders)
                {
                    if (o.OrderState == OrderState.Working || o.OrderState == OrderState.Submitted || o.OrderState == OrderState.Accepted)
                    {
                        // Reducing is only true while a position is actually open, so a flat
                        // account still has every order cancelled -- which is what lets the
                        // lockout reach Confirmed.
                        if (IsPositionReducingOrder(o, cancelState))
                        {
                            retained.Add(o.Instrument != null ? o.Instrument.FullName : o.Name);
                            continue;
                        }
                        orders.Add(o);
                    }
                }
                if (orders.Count > 0)
                {
                    account.Cancel(orders);
                }
                if (retained.Count > 0)
                {
                    LogEvent(action.AccountName, "LOCKOUT_STOP_RETAINED",
                        $"Position still open for {string.Join(",", retained.Distinct())}; "
                        + "keeping its protective order working rather than leaving the position naked.");
                }
            }
            else if (action.ActionType == GuardActionType.CancelOrder)
            {
                var order = account.Orders.FirstOrDefault(o => o.Id.ToString() == action.OrderId);
                if (order != null)
                {
                    account.Cancel(new[] { order });
                }
            }
            else if (action.ActionType == GuardActionType.PlaceStopOrder)
            {
                var instrument = action.InstrumentObj;
                if (instrument == null)
                {
                    LogEvent(account.Name, "AUTO_STOP_ABORT_NO_INSTRUMENT", "PlaceStopOrder missing InstrumentObj; aborting.");
                    return;
                }

                string key = FsmKey(account.Name, action.Instrument);

                bool IsFsmProtectedOrPending()
                {
                    lock (_stateLock)
                    {
                        return _guardFsms.TryGetValue(key, out PositionGuardFsm localFsm)
                            && (localFsm.State == GuardFsmState.Protected || localFsm.State == GuardFsmState.ProtectedPending);
                    }
                }

                void ReArmGraceIfUnprotected()
                {
                    lock (_stateLock)
                    {
                        if (_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm) && localFsm.State == GuardFsmState.Unprotected)
                        {
                            localFsm.GraceEmitted = false;
                            int delayMs = _config.StopGuard.StopAttachSeconds * 1000;
                            // ArmGraceTimer only schedules a timer callback; it does not invoke account trading methods.
                            ArmGraceTimer(localFsm, account, action.Instrument, delayMs);
                        }
                    }
                }

                void RollbackFsm(string reason)
                {
                    bool wasProtected = false;
                    lock (_stateLock)
                    {
                        if (_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm))
                        {
                            if (localFsm.State == GuardFsmState.Protected)
                            {
                                wasProtected = true;
                                localFsm.GraceEmitted = false;
                            }
                            else
                            {
                                localFsm.AutoStopOrder = null;
                                localFsm.ClearRecognizedStops();
                                localFsm.GraceEmitted = false;
                                if (localFsm.State != GuardFsmState.Flat)
                                    localFsm.State = GuardFsmState.Unprotected;

                                int delayMs = _config.StopGuard.StopAttachSeconds * 1000;
                                // ArmGraceTimer only schedules a timer callback; it does not invoke account trading methods.
                                ArmGraceTimer(localFsm, account, action.Instrument, delayMs);
                            }
                        }
                    }
                    if (wasProtected)
                        LogEvent(account.Name, "AUTO_STOP_ROLLBACK_PROTECTED", $"Protected FSM left intact for {action.Instrument}: {reason}");
                    else
                        LogEvent(account.Name, "AUTO_STOP_ROLLBACK", $"FSM rolled back for {action.Instrument}: {reason}");
                }

                void ClearTrackingAndSetUnprotected()
                {
                    lock (_stateLock)
                    {
                        if (_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm))
                        {
                            localFsm.AutoStopOrder = null;
                            localFsm.ClearRecognizedStops();
                            localFsm.GraceEmitted = false;
                            if (localFsm.State != GuardFsmState.Flat)
                                localFsm.State = GuardFsmState.Unprotected;
                        }
                    }
                }

                void AfterFlattenCleanup(string context)
                {
                    var posNow = account.Positions.FirstOrDefault(p => p.Instrument != null && p.Instrument.FullName == action.Instrument);
                    bool positionExists = posNow != null && posNow.MarketPosition != MarketPosition.Flat;

                    lock (_stateLock)
                    {
                        if (!_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm))
                        {
                            if (positionExists)
                            {
                                localFsm = new PositionGuardFsm(account.Name, action.Instrument);
                                localFsm.PositionSide = posNow.MarketPosition;
                                localFsm.PositionQuantity = (int)posNow.Quantity;
                                localFsm.EntryTime = DateTime.UtcNow;
                                localFsm.LastTransitionTime = DateTime.UtcNow;
                                localFsm.State = GuardFsmState.Unprotected;
                                localFsm.GraceEmitted = false;
                                localFsm.AutoStopAttempts = 0;
                                _guardFsms[key] = localFsm;
                            }
                        }

                        if (localFsm != null)
                        {
                            localFsm.AutoStopOrder = null;
                            localFsm.ClearRecognizedStops();
                            localFsm.GraceEmitted = false;
                            localFsm.AutoStopAttempts = 0;
                            if (localFsm.State != GuardFsmState.Flat)
                                localFsm.State = GuardFsmState.Unprotected;

                            if (positionExists && localFsm.State == GuardFsmState.Unprotected)
                            {
                                int delayMs = _config.StopGuard.StopAttachSeconds * 1000;
                                // ArmGraceTimer only schedules a timer callback; it does not invoke account trading methods.
                                ArmGraceTimer(localFsm, account, action.Instrument, delayMs);
                            }
                        }
                    }

                    LogEvent(account.Name, "AUTO_STOP_FLATTEN_CLEANUP", $"Post-flatten cleanup completed for {action.Instrument} ({context}).");
                }

                void FlattenAndClear(string reason)
                {
                    LogEvent(account.Name, "STOP_SIDE_FLATTEN", reason);
                    try
                    {
                        account.Flatten(new[] { instrument });
                    }
                    catch (Exception fex)
                    {
                        RollbackFsm($"Flatten failed: {fex.Message}");
                        LogEvent(account.Name, "FLATTEN_ERROR", $"Flatten failed for {instrument.FullName}: {fex.Message}");
                        throw;
                    }
                    AfterFlattenCleanup("stop-side-flatten");
                }

                var position = account.Positions.FirstOrDefault(p => p.Instrument != null && p.Instrument.FullName == action.Instrument);
                if (position == null || position.MarketPosition == MarketPosition.Flat)
                {
                    ReArmGraceIfUnprotected();
                    LogEvent(account.Name, "AUTO_STOP_ABORT_NO_POSITION", $"No live position for {action.Instrument}; aborting auto-stop.");
                    return;
                }

                MarketPosition initialSide = position.MarketPosition;

                bool sideMismatch = false;
                lock (_stateLock)
                {
                    if (!_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm) || localFsm.PositionSide != initialSide)
                        sideMismatch = true;
                }
                if (sideMismatch)
                {
                    ReArmGraceIfUnprotected();
                    LogEvent(account.Name, "AUTO_STOP_ABORT_SIDE_MISMATCH",
                        $"Live position side {initialSide} does not match FSM side for {action.Instrument}; aborting auto-stop.");
                    return;
                }

                int maxAttempts = _config.StopGuard.MaxAutoStopAttempts;
                if (maxAttempts <= 0) maxAttempts = 2;

                bool shouldEscalate = false;
                lock (_stateLock)
                {
                    if (_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm))
                    {
                        if (localFsm.AutoStopAttempts + 1 > maxAttempts)
                            shouldEscalate = true;
                    }
                    else
                    {
                        LogEvent(account.Name, "AUTO_STOP_ABORT_FSM_LOST", $"FSM missing for {action.Instrument} during escalation check; aborting.");
                        return;
                    }
                }

                if (shouldEscalate)
                {
                    bool stillEscalate = false;
                    lock (_stateLock)
                    {
                        if (_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm))
                            stillEscalate = localFsm.State == GuardFsmState.Unprotected;
                    }

                    if (!stillEscalate)
                    {
                        LogEvent(account.Name, "AUTO_STOP_ESCALATE_SKIPPED", $"Escalation skipped for {instrument.FullName}; FSM is not unprotected.");
                        return;
                    }

                    ClearTrackingAndSetUnprotected();
                    LogEvent(account.Name, "AUTO_STOP_ESCALATE",
                        $"Auto-stop escalation for {instrument.FullName}: attempts exceeded ceiling {maxAttempts}; flattening position.");

                    try
                    {
                        account.Flatten(new[] { instrument });
                    }
                    catch (Exception fex)
                    {
                        RollbackFsm($"Escalation flatten failed: {fex.Message}");
                        LogEvent(account.Name, "AUTO_STOP_ESCALATE_FAILED", $"Escalation flatten failed for {instrument.FullName}: {fex.Message}");
                        throw;
                    }

                    AfterFlattenCleanup("escalation");
                    return;
                }

                // Re-read the live position before computing the stop price and side.
                position = account.Positions.FirstOrDefault(p => p.Instrument != null && p.Instrument.FullName == action.Instrument);
                if (position == null || position.MarketPosition == MarketPosition.Flat || position.MarketPosition != initialSide)
                {
                    ReArmGraceIfUnprotected();
                    LogEvent(account.Name, "AUTO_STOP_ABORT_NO_POSITION", $"Position changed before stop pricing for {action.Instrument}; aborting auto-stop.");
                    return;
                }

                string symbolName = instrument.MasterInstrument.Name;
                int offsetTicks = 30; // default
                if (_config.StopGuard.Offsets.TryGetValue(symbolName, out int ticks))
                {
                    offsetTicks = ticks;
                }
                else if (_config.StopGuard.Offsets.TryGetValue("default", out int defTicks))
                {
                    offsetTicks = defTicks;
                }

                double tickSize = instrument.MasterInstrument.TickSize;
                double stopPrice = 0.0;
                OrderAction orderAction = OrderAction.Buy;

                // Fix B: Read real last price from market data
                double currentPrice = 0.0;
                if (instrument.MarketData != null && instrument.MarketData.Last != null)
                {
                    currentPrice = instrument.MarketData.Last.Price;
                }

                if (currentPrice <= 0.0)
                {
                    if (IsFsmProtectedOrPending())
                    {
                        LogEvent(account.Name, "AUTO_STOP_ESCALATE_SKIPPED", $"Stop-side flatten skipped for {instrument.FullName}; FSM already protected/pending.");
                        return;
                    }
                    FlattenAndClear($"Market price unavailable for {instrument.FullName}. Flattening.");
                    return;
                }

                if (position.MarketPosition == MarketPosition.Long)
                {
                    stopPrice = position.AveragePrice - (offsetTicks * tickSize);
                    orderAction = OrderAction.Sell;
                    
                    if (stopPrice >= currentPrice)
                    {
                        if (IsFsmProtectedOrPending())
                        {
                            LogEvent(account.Name, "AUTO_STOP_ESCALATE_SKIPPED", $"Stop-side flatten skipped for {instrument.FullName}; FSM already protected/pending.");
                            return;
                        }
                        FlattenAndClear($"Long stop {stopPrice} >= current price {currentPrice}. Flattening.");
                        return;
                    }
                }
                else if (position.MarketPosition == MarketPosition.Short)
                {
                    stopPrice = position.AveragePrice + (offsetTicks * tickSize);
                    orderAction = OrderAction.Buy;

                    if (stopPrice <= currentPrice)
                    {
                        if (IsFsmProtectedOrPending())
                        {
                            LogEvent(account.Name, "AUTO_STOP_ESCALATE_SKIPPED", $"Stop-side flatten skipped for {instrument.FullName}; FSM already protected/pending.");
                            return;
                        }
                        FlattenAndClear($"Short stop {stopPrice} <= current price {currentPrice}. Flattening.");
                        return;
                    }
                }
                else
                {
                    RollbackFsm("Unexpected position side");
                    LogEvent(account.Name, "AUTO_STOP_ABORT_UNEXPECTED_SIDE", $"Unexpected position side {position.MarketPosition} for {action.Instrument}; aborting auto-stop.");
                    return;
                }

                stopPrice = instrument.MasterInstrument.RoundToTickSize(stopPrice);

                // Re-read the live position immediately before sizing the stop.
                var positionForQuantity = account.Positions.FirstOrDefault(p => p.Instrument != null && p.Instrument.FullName == action.Instrument);
                if (positionForQuantity == null || positionForQuantity.MarketPosition == MarketPosition.Flat)
                {
                    ReArmGraceIfUnprotected();
                    LogEvent(account.Name, "AUTO_STOP_ABORT_NO_POSITION", $"Position became flat before stop sizing for {action.Instrument}; aborting auto-stop.");
                    return;
                }
                if (positionForQuantity.MarketPosition != position.MarketPosition)
                {
                    ReArmGraceIfUnprotected();
                    LogEvent(account.Name, "AUTO_STOP_ABORT_SIDE_MISMATCH",
                        $"Position side changed from {position.MarketPosition} to {positionForQuantity.MarketPosition} for {action.Instrument}; aborting auto-stop.");
                    return;
                }

                int liveQuantity = (int)positionForQuantity.Quantity;
                if (liveQuantity <= 0)
                {
                    ReArmGraceIfUnprotected();
                    LogEvent(account.Name, "AUTO_STOP_ABORT_NO_QUANTITY", $"Live position quantity {liveQuantity} for {action.Instrument}; aborting auto-stop.");
                    return;
                }

                // P1-36: size to the UNCOVERED DELTA, re-read live, not to the whole position.
                //
                // T2 established that the quantity must come from the live position rather than
                // the emission snapshot, and that is still true -- but "the live position" is the
                // wrong figure whenever the trader already has stops of his own working. Sizing
                // the auto-stop at 6 on a 6-lot position that is already half covered by a 3-lot
                // stop puts NINE lots of protection behind six, and flips the account three lots
                // short when they trigger. EvaluateGraceExpiry has always sized its ACTION to the
                // delta; ExecuteAction then re-sized it back up to the full position and undid it.
                int alreadyCovered;
                lock (_stateLock)
                {
                    alreadyCovered = _guardFsms.TryGetValue(key, out PositionGuardFsm coverFsm)
                        ? Math.Max(0, coverFsm.CoveredQuantity) : 0;
                }

                int stopQuantity = liveQuantity - alreadyCovered;
                if (stopQuantity <= 0)
                {
                    // Cover appeared between emission and execution -- the trader attached his own
                    // stop while the action was in flight. Placing anything now would over-cover.
                    //
                    // GraceEmitted is cleared deliberately. Dropping an action without clearing it
                    // is the T1/T2 trap: EvaluateGraceExpiry and FsmWatchdog are both gated on
                    // !GraceEmitted, so leaving it set would suppress every future attempt and
                    // leave the position permanently naked the moment that cover went away.
                    ReArmGraceIfUnprotected();
                    lock (_stateLock)
                    {
                        if (_guardFsms.TryGetValue(key, out PositionGuardFsm coveredFsm))
                            coveredFsm.GraceEmitted = false;
                    }
                    LogEvent(account.Name, "AUTO_STOP_ABORT_ALREADY_COVERED",
                        $"{action.Instrument} is covered {alreadyCovered}/{liveQuantity} by existing stops; "
                        + "no auto-stop needed. Grace re-armed in case that cover is withdrawn.");
                    return;
                }

                // Diagnostic logging
                var orderDump = new StringBuilder();
                orderDump.AppendLine($"RiskGuard triggering auto-stop for {stopQuantity} {symbolName}. Current Orders:");
                foreach (Order o in account.Orders)
                {
                    if (o.Instrument?.FullName == action.Instrument)
                    {
                        orderDump.AppendLine($" - {o.OrderAction} {o.Quantity} {o.OrderType} | State: {o.OrderState} | Name: {o.Name}");
                    }
                }
                LogEvent(account.Name, "AUTO_STOP_DIAGNOSTIC", orderDump.ToString().TrimEnd());

                // Increment the attempt counter and confirm the FSM still exists
                // immediately before CreateOrder.
                PositionGuardFsm fsmForAttempt = null;
                lock (_stateLock)
                {
                    if (_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm))
                    {
                        localFsm.AutoStopAttempts++;
                        fsmForAttempt = localFsm;
                    }
                }

                if (fsmForAttempt == null)
                {
                    LogEvent(account.Name, "AUTO_STOP_ABORT_FSM_LOST", $"FSM lost for {action.Instrument} before CreateOrder; flattening position.");
                    try
                    {
                        account.Flatten(new[] { instrument });
                    }
                    catch (Exception fex)
                    {
                        LogEvent(account.Name, "FLATTEN_ERROR", $"Flatten failed for {instrument.FullName}: {fex.Message}");
                        throw;
                    }
                    AfterFlattenCleanup("fsm-lost");
                    return;
                }

                Order stopOrder = account.CreateOrder(
                    instrument,
                    orderAction,
                    OrderType.StopMarket,
                    TimeInForce.Day,
                    stopQuantity,
                    0,
                    stopPrice,
                    string.Empty,
                    "RiskGuardAutoStop",
                    null
                );

                if (stopOrder == null)
                {
                    RollbackFsm("CreateOrder returned null");
                    LogEvent(account.Name, "AUTO_STOP_SUBMIT_FAILED", $"CreateOrder returned null for {instrument.FullName}.");
                    throw new Exception($"CreateOrder returned null for auto-stop on {instrument.FullName}");
                }

                // Reserve-before-submit: record the pending protection, then release
                // the lock before any account call.
                bool reserved = false;
                lock (_stateLock)
                {
                    if (_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm))
                    {
                        localFsm.AutoStopOrder = stopOrder;
                        // P1-36: ADD, do not replace. The auto-stop is sized to the UNCOVERED
                        // DELTA, so on a partially covered position replacing would discard the
                        // trader's own stop from the tally, leave the FSM under-covered again,
                        // and emit a second auto-stop for a delta that is already protected.
                        // That escalation on a 6-lot position with two 3-lot stops is P1-36.
                        localFsm.AddRecognizedStop(stopOrder);
                        localFsm.State = GuardFsmState.ProtectedPending;
                        reserved = true;
                    }
                }

                if (!reserved)
                {
                    // FSM disappeared after CreateOrder. Cancel the untracked stop
                    // and flatten as a fail-closed fallback.
                    try
                    {
                        account.Cancel(new[] { stopOrder });
                    }
                    catch (Exception cex)
                    {
                        LogEvent(account.Name, "AUTO_STOP_CANCEL_FAILED", $"Cancel of untracked stop failed for {instrument.FullName}: {cex.Message}");
                    }

                    LogEvent(account.Name, "AUTO_STOP_SUBMIT_FAILED", $"FSM lost before submit for {instrument.FullName}; flattening position.");
                    try
                    {
                        account.Flatten(new[] { instrument });
                    }
                    catch (Exception fex)
                    {
                        LogEvent(account.Name, "FLATTEN_ERROR", $"Flatten failed for {instrument.FullName}: {fex.Message}");
                        throw;
                    }
                    AfterFlattenCleanup("reserve-failed");
                    throw new Exception($"FSM lost before submit for auto-stop on {instrument.FullName}");
                }

                try
                {
                    account.Submit(new[] { stopOrder });
                }
                catch (Exception ex)
                {
                    bool alreadyProtected = false;
                    lock (_stateLock)
                    {
                        if (_guardFsms.TryGetValue(key, out PositionGuardFsm localFsm))
                        {
                            alreadyProtected = localFsm.State == GuardFsmState.Protected;
                            if (alreadyProtected)
                                localFsm.GraceEmitted = false;
                        }
                    }

                    if (alreadyProtected)
                    {
                        LogEvent(account.Name, "AUTO_STOP_SUBMIT_RACE",
                            $"Stop already Working for {instrument.FullName} despite Submit exception; leaving FSM Protected.");
                        return;
                    }

                    try
                    {
                        account.Cancel(new[] { stopOrder });
                    }
                    catch (Exception cex)
                    {
                        LogEvent(account.Name, "AUTO_STOP_CANCEL_FAILED", $"Cancel of failed-submit stop failed for {instrument.FullName}: {cex.Message}");
                    }

                    RollbackFsm($"Submit failed: {ex.Message}");
                    LogEvent(account.Name, "AUTO_STOP_SUBMIT_FAILED", $"Submit failed for {instrument.FullName}: {ex.Message}");
                    throw;
                }

                // No post-submit FSM write: UpdateFsmOnOrder owns all further state.
            }
        }

        // -
        // HELPER METHODS FOR UI & LOGGING
        // -

        public string GetAccountStatusString(string accountName)
        {
            lock (_stateLock)
            {
                if (!_accountStates.TryGetValue(accountName, out var state))
                {
                    return $"Account {accountName} not monitored.";
                }

                var sb = new StringBuilder();
                sb.AppendLine($"Account: {accountName}");
                sb.AppendLine($"Mode: {_mode} (Armed: {_isArmed})");
                sb.AppendLine($"Locked Out: {state.IsLockedOut}");
                sb.AppendLine($"Realized PnL: {state.RealizedPnL:C}");
                
                double openPnL = state.UnrealizedPnL;
                sb.AppendLine($"Open PnL: {openPnL:C}");
                sb.AppendLine($"Net PnL: {(state.RealizedPnL + openPnL):C}");
                sb.AppendLine($"Peak Equity (PnL): {state.PeakEquity:C}");
                
                sb.AppendLine("Positions:");
                foreach (var pos in state.Positions.Values)
                {
                    if (pos.MarketPosition != MarketPosition.Flat)
                    {
                        string posType = pos.MarketPosition == MarketPosition.Long ? "LONG" : "SHORT";
                        sb.AppendLine($"  - {pos.Instrument}: {posType} {pos.Quantity} @ {pos.AveragePrice}");
                        if (pos.LastNonFlatTransition != DateTime.MinValue)
                        {
                            double elapsed = (DateTime.UtcNow - pos.LastNonFlatTransition).TotalSeconds;
                            sb.AppendLine($"    Open for: {elapsed:F1}s");
                        }
                    }
                }
                
                return sb.ToString();
            }
        }

        private void LogEvent(string account, string eventType, string message)
        {
            LogEvent(account, eventType, new JObject { { "message", message } });
        }

        /// <summary>
        /// Lets a sibling component in this assembly write into the guard's structured log.
        ///
        /// The TradeCopier used to log only via NinjaTrader.Code.Output.Process, which reaches the
        /// NT8 Output tab and NOTHING else -- not `interventions.jsonl`, not the bridge's event
        /// stream, not `log/` or `trace/`. That made the copier undiagnosable after the fact: on
        /// 2026-08-09 a leader exit failed to mirror to its follower and there was no record of
        /// why, because every candidate path either logged to a sink nobody can read or returned
        /// silently. Anything worth reading later belongs here.
        ///
        /// Static and null-tolerant on purpose: the copier must not care whether the guard exists,
        /// and it is constructed independently in tests.
        /// </summary>
        internal static void LogFromComponent(string account, string eventType, string message)
        {
            var inst = Instance;
            if (inst == null) return;
            try { inst.LogEvent(account, eventType, message); } catch { }
        }

        private void LogEvent(string account, string eventType, JObject data)
        {
#if TESTING
            // P2-92. Added because a mutant that DELETED a log line survived the whole suite: the
            // audit record is a first-class product of this addon -- `P1-70` is about a log claiming
            // an outcome it has not observed, and `P1-71` is about a relationship that produced no
            // order and left no diagnosable trace -- and none of it was assertable, because nothing
            // could observe a LogEvent call. Every claim in that class was pinned by source scan or
            // not at all.
            //
            // Fires BEFORE the try, so a test sees the event even if the disk write throws, which is
            // the case a source scan cannot distinguish from a working one.
            var observer = LogEventObserver;
            if (observer != null) observer(account, eventType);
#endif
            try
            {
                JObject logEntry = new JObject
                {
                    { "timestamp_utc", DateTime.UtcNow.ToString("o") },
                    { "timestamp_et", TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, _etZone).ToString("o") },
                    { "account", account },
                    { "eventType", eventType },
                    { "mode", _mode },
                    { "isArmed", _isArmed },
                    { "data", data }
                };

                string logLine = logEntry.ToString(Formatting.None);
                _logQueue.Enqueue(logLine);
            }
            catch
            {
                NinjaTrader.Code.Output.Process($"Failed to serialize log: {eventType} for {account}", PrintTo.OutputTab1);
            }
        }

        // - Firm-mirror logic and unit test diagnostics (FR-24/25/26) -
        /// <summary>
        /// Evaluates the firm-mirror trailing-drawdown and daily-loss rules.
        /// </summary>
        /// <param name="nowUtc">
        /// UTC timestamp to evaluate against. This parameter was previously named nowEt and was
        /// IGNORED - the method read DateTime.UtcNow internally, so the firm daily-reset boundary
        /// (FirmMirror.DailyResetHourUtc, default 22:00 UTC) could roll over mid-test and zero the
        /// P&amp;L basis. That made TestFirmMirrorDailyLossBreachEmitsAction fail every day after
        /// 22:00 UTC, and because a corrupted test called Environment.Exit on failure, it silently
        /// skipped the last 25 tests in the suite. Callers must now pass the clock explicitly.
        /// </param>
        // P1-42: resolve the firm profile that actually applies to this account. Before this
        // existed, EvaluateFirmMirror handed ComputeFirmMirror the top-level FirmMirrorConfig
        // and nothing ever read AccountFirmMap or FirmProfiles -- the researched per-firm numbers
        // were dead config, and RunPreflight's validation of the mapping made it look otherwise.
        //
        // Falls back to the top-level TrailingDD/DailyLoss when the account is unmapped, when the
        // mapped firm is absent from FirmProfiles, or when the profile omits a sub-rule. The
        // dangling-firm case must not throw or silently disable: preflight refuses to arm on an
        // unknown firm name, but config can be reloaded while already armed, so the evaluator
        // cannot assume preflight has run. Both dictionaries are OrdinalIgnoreCase and the
        // lookups rely on that.
        internal static FirmMirrorConfig ResolveEffectiveFirmConfig(FirmMirrorConfig fm, string accountName)
        {
            if (fm == null || string.IsNullOrEmpty(accountName)) return fm;
            if (fm.AccountFirmMap == null || fm.FirmProfiles == null) return fm;

            string firmName;
            if (!fm.AccountFirmMap.TryGetValue(accountName, out firmName) || string.IsNullOrEmpty(firmName))
                return fm;

            FirmProfile profile;
            if (!fm.FirmProfiles.TryGetValue(firmName, out profile) || profile == null)
                return fm;

            return new FirmMirrorConfig
            {
                Enabled = fm.Enabled,
                TrailingDD = profile.TrailingDD ?? fm.TrailingDD,
                DailyLoss = profile.DailyLoss ?? fm.DailyLoss,
                // The daily boundary is a property of the clock, not of the firm.
                DailyResetHourUtc = fm.DailyResetHourUtc,
                DailyResetMinuteUtc = fm.DailyResetMinuteUtc,
                AccountFirmMap = fm.AccountFirmMap,
                FirmProfiles = fm.FirmProfiles,
                // P2-95: carry the plan's stated AccountSize so ComputeFirmMirror can use it
                // as the starting balance instead of the session-scoped heuristic.
                ResolvedAccountSize = profile.AccountSize
            };
        }

        internal List<GuardAction> EvaluateFirmMirror(Account account, AccountState st, DateTime nowUtc)
        {
            double balance = account.Get(AccountItem.CashValue, Currency.UsDollar);
            double realized = account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
            double unrealized = account.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar);

            // Everything below -- the computation AND the audit-log payloads -- must read the
            // effective config. Logging the top-level amounts while breaching on a profile's
            // would make the audit trail describe a rule that did not run.
            var fmEffective = ResolveEffectiveFirmConfig(_config.FirmMirror, st.AccountName);

            var res = ComputeFirmMirror(balance, realized, unrealized, fmEffective, st, nowUtc);
            
            if (res.StateChanged)
            {
                _stateDirty = true;
                foreach (var log in res.TraceLogs)
                {
                    LogEvent(st.AccountName, "FIRM_STATE_UPDATE", log);
                }
            }

            var actions = new List<GuardAction>();
            if (res.TrailingDDBreached)
            {
                LogEvent(st.AccountName, "FIRM_TRAILING_DD_BREACH", new JObject
                {
                    { "currentFirmEquity", balance + unrealized },
                    { "guardFloor", res.GuardFloor },
                    { "effectiveFloor", res.EffectiveFloor },
                    { "trailingPeak", res.TrailingPeak },
                    { "floorLocked", res.FloorLocked },
                    { "amount", fmEffective.TrailingDD.Amount },
                    { "buffer", fmEffective.TrailingDD.Buffer }
                });

                actions.Add(new GuardAction
                {
                    AccountName = st.AccountName,
                    ActionType = GuardActionType.FlattenPosition,
                    RuleId = "FIRM_TRAILING_DD_BREACH"
                });
                if (!st.IsLockedOut) MarkRuleLockout(st, "FIRM_TRAILING_DD_BREACH");
            }

            if (res.DailyLossBreached)
            {
                double dayRealized = realized - st.FirmDailyStartRealized;
                double dayPnL = fmEffective.DailyLoss.Basis == "include_unrealized_peak"
                    ? dayRealized + unrealized
                    : dayRealized;

                LogEvent(st.AccountName, "FIRM_DAILY_LOSS_BREACH", new JObject
                {
                    { "dayPnL", dayPnL },
                    { "guardLimit", res.GuardDailyLimit },
                    { "basis", fmEffective.DailyLoss.Basis },
                    { "amount", fmEffective.DailyLoss.Amount },
                    { "buffer", fmEffective.DailyLoss.Buffer }
                });

                actions.Add(new GuardAction
                {
                    AccountName = st.AccountName,
                    ActionType = GuardActionType.FlattenPosition,
                    RuleId = "FIRM_DAILY_LOSS_BREACH"
                });
                if (!st.IsLockedOut) MarkRuleLockout(st, "FIRM_DAILY_LOSS_BREACH");
            }

            return actions;
        }

        public static FirmMirrorResult ComputeFirmMirror(
            double balance, 
            double realized, 
            double unrealized, 
            FirmMirrorConfig fm, 
            AccountState st, 
            DateTime nowUtc)
        {
            var result = new FirmMirrorResult();
            bool stateChanged = false;

            if (st.FirmStartingBalance == 0.0)
            {
                // P2-95: prefer the plan's stated AccountSize over the heuristic.
                // The heuristic (balance - realized - unrealized) captures the SESSION-start
                // balance because `realized` is session-scoped. On an account up $5,000 over
                // its life it reads 55,000 instead of 50,000, so the trail-lock floor is wrong
                // by lifetime profit — and the error GROWS as the account does. When the plan
                // states an AccountSize, that is the plan's starting balance by definition.
                if (fm.ResolvedAccountSize > 0.0)
                {
                    st.FirmStartingBalance = fm.ResolvedAccountSize;
                    result.TraceLogs.Add($"Initial starting balance set from plan AccountSize: {st.FirmStartingBalance}");
                }
                else
                {
                    st.FirmStartingBalance = balance - realized - unrealized;
                    result.TraceLogs.Add($"Initial starting balance captured heuristically: {st.FirmStartingBalance}");
                }
                stateChanged = true;
            }

            var boundary = new TimeSpan(fm.DailyResetHourUtc, fm.DailyResetMinuteUtc, 0);
            DateTime firmDailyDate = nowUtc.TimeOfDay >= boundary ? nowUtc.Date.AddDays(1) : nowUtc.Date;
            if (st.FirmDailyDate != firmDailyDate)
            {
                st.FirmDailyDate = firmDailyDate;
                st.FirmDailyStartRealized = realized;
                result.TraceLogs.Add($"Firm daily boundary rollover for {firmDailyDate:yyyy-MM-dd} (UTC {fm.DailyResetHourUtc:00}:{fm.DailyResetMinuteUtc:00})");
                stateChanged = true;
            }

            if (fm.TrailingDD.Enabled)
            {
                double firmEquity = fm.TrailingDD.IncludesUnrealized
                    ? balance + unrealized
                    : balance;

                if (fm.TrailingDD.Type == "eod")
                {
                    firmEquity = balance;
                }

                if (!st.FirmFloorLocked)
                {
                    if (firmEquity > st.FirmTrailingPeak)
                    {
                        st.FirmTrailingPeak = firmEquity;
                        result.TraceLogs.Add($"Firm trailing peak advanced to: {st.FirmTrailingPeak}");
                        stateChanged = true;
                    }

                    if (fm.TrailingDD.LockAtProfit > 0.0 && st.FirmStartingBalance > 0.0)
                    {
                        if (st.FirmTrailingPeak >= st.FirmStartingBalance + fm.TrailingDD.LockAtProfit)
                        {
                            st.FirmFloorLocked = true;
                            result.TraceLogs.Add($"Trailing floor locked at starting balance. Peak={st.FirmTrailingPeak}, start={st.FirmStartingBalance}");
                            stateChanged = true;
                        }
                    }
                }

                double effectiveFloor = st.FirmFloorLocked
                    ? st.FirmStartingBalance
                    : st.FirmTrailingPeak - fm.TrailingDD.Amount;

                double guardFloor = effectiveFloor + fm.TrailingDD.Buffer;

                if (fm.TrailingDD.Type == "static" && st.FirmStartingBalance > 0.0)
                {
                    guardFloor = (st.FirmStartingBalance - fm.TrailingDD.Amount) + fm.TrailingDD.Buffer;
                }

                result.EffectiveFloor = effectiveFloor;
                result.GuardFloor = guardFloor;
                result.TrailingPeak = st.FirmTrailingPeak;
                result.FloorLocked = st.FirmFloorLocked;

                // DIFF 4: breach test uses the same basis as peak tracking (no mismatch)
                if (firmEquity <= guardFloor)
                {
                    result.TrailingDDBreached = true;
                }
            }

            if (fm.DailyLoss.Enabled)
            {
                double dayRealized = realized - st.FirmDailyStartRealized;
                double dayPnL = fm.DailyLoss.Basis == "include_unrealized_peak"
                    ? dayRealized + unrealized
                    : dayRealized;

                double guardLimit = -(fm.DailyLoss.Amount - fm.DailyLoss.Buffer);
                result.GuardDailyLimit = guardLimit;

                if (dayPnL <= guardLimit)
                {
                    result.DailyLossBreached = true;
                }
            }

            result.StateChanged = stateChanged;
            return result;
        }

        public FirmDiagnosticsResult RunFirmDiagnostics()
        {
            var res = new FirmDiagnosticsResult();
            res.Logs.Add("Starting Firm Mirror Unit Diagnostics...");

            try
            {
                var st = new AccountState("SimMock");
                st.FirmStartingBalance = 100000.0;
                st.FirmTrailingPeak = 100000.0;
                st.FirmFloorLocked = false;
                st.FirmDailyDate = new DateTime(2026, 7, 15);
                st.FirmDailyStartRealized = 0.0;

                var fm = new FirmMirrorConfig
                {
                    Enabled = true,
                    DailyResetHourUtc = 22,
                    DailyResetMinuteUtc = 0,
                    TrailingDD = new FirmTrailingDDConfig
                    {
                        Enabled = true,
                        Type = "intraday",
                        IncludesUnrealized = true,
                        Amount = 2500.0,
                        Buffer = 300.0,
                        LockAtProfit = 3000.0
                    },
                    DailyLoss = new FirmDailyLossConfig
                    {
                        Enabled = true,
                        Basis = "realized",
                        Amount = 1500.0,
                        Buffer = 200.0
                    }
                };

                // Test 1: Trailing DD buffer breach
                res.Logs.Add("[Test 1: Trailing DD] Advancing equity to 102,000...");
                var r1 = ComputeFirmMirror(102000.0, 2000.0, 0.0, fm, st, new DateTime(2026, 7, 15, 12, 0, 0, DateTimeKind.Utc));
                res.Logs.AddRange(r1.TraceLogs);
                if (st.FirmTrailingPeak != 102000.0) throw new Exception("Peak did not trail up to 102,000.");
                if (r1.GuardFloor != 99800.0) throw new Exception(string.Format("Expected guard floor to be 99,800, got {0}", r1.GuardFloor));

                res.Logs.Add("Dropping equity to 99,900...");
                var r2 = ComputeFirmMirror(99900.0, -100.0, 0.0, fm, st, new DateTime(2026, 7, 15, 13, 0, 0, DateTimeKind.Utc));
                if (r2.TrailingDDBreached) throw new Exception("Trailing DD breached prematurely at 99,900.");

                res.Logs.Add("Dropping equity to 99,750...");
                var r3 = ComputeFirmMirror(99750.0, -250.0, 0.0, fm, st, new DateTime(2026, 7, 15, 14, 0, 0, DateTimeKind.Utc));
                if (!r3.TrailingDDBreached) throw new Exception("Guard floor failed to trip at 99,750 (buffer-adjusted floor = 99,800).");
                res.Logs.Add("Test 1 Passed: Trailing DD buffer breach triggered correctly.");

                // Test 2: Floor Lock
                st.FirmStartingBalance = 100000.0;
                st.FirmTrailingPeak = 100000.0;
                st.FirmFloorLocked = false;

                res.Logs.Add("[Test 2: Floor Lock] Advancing equity to 103,500...");
                var r4 = ComputeFirmMirror(103500.0, 3500.0, 0.0, fm, st, new DateTime(2026, 7, 15, 15, 0, 0, DateTimeKind.Utc));
                res.Logs.AddRange(r4.TraceLogs);
                if (!st.FirmFloorLocked) throw new Exception("Floor did not lock after peak crossed LockAtProfit.");

                res.Logs.Add("Dropping equity to 100,250...");
                var r5 = ComputeFirmMirror(100250.0, 250.0, 0.0, fm, st, new DateTime(2026, 7, 15, 16, 0, 0, DateTimeKind.Utc));
                if (!r5.TrailingDDBreached) throw new Exception("Floor lock trailing DD failed to trip at 100,250.");
                res.Logs.Add("Test 2 Passed: Floor lock and breach verified.");

                // Test 3: Daily loss UTC boundary rollover & limit breach
                st.FirmDailyDate = DateTime.MinValue;
                st.FirmDailyStartRealized = 0.0;
                res.Logs.Add("[Test 3: Daily Loss] Initializing daily loss trace at 20:00 UTC...");
                var r6 = ComputeFirmMirror(100000.0, 0.0, 0.0, fm, st, new DateTime(2026, 7, 15, 20, 0, 0, DateTimeKind.Utc));
                res.Logs.AddRange(r6.TraceLogs);

                res.Logs.Add("Rollover daily reset boundary (23:00 UTC)...");
                var r7 = ComputeFirmMirror(102000.0, 2000.0, 0.0, fm, st, new DateTime(2026, 7, 15, 23, 0, 0, DateTimeKind.Utc));
                res.Logs.AddRange(r7.TraceLogs);
                if (st.FirmDailyStartRealized != 2000.0) throw new Exception("Failed to reset daily realized baseline.");

                res.Logs.Add("Post-rollover loss of 1,200...");
                var r8 = ComputeFirmMirror(100800.0, 800.0, 0.0, fm, st, new DateTime(2026, 7, 16, 0, 0, 0, DateTimeKind.Utc));
                if (r8.DailyLossBreached) throw new Exception("Daily loss breached prematurely at -1,200 loss.");

                res.Logs.Add("Post-rollover loss of 1,350...");
                var r9 = ComputeFirmMirror(100650.0, 650.0, 0.0, fm, st, new DateTime(2026, 7, 16, 1, 0, 0, DateTimeKind.Utc));
                if (!r9.DailyLossBreached) throw new Exception("Daily loss failed to breach at -1,350 (limit=-1,300).");
                res.Logs.Add("Test 3 Passed: Daily reset and daily loss limit verified.");

                res.Success = true;
                res.Logs.Add("All diagnostics passed!");
            }
            catch (Exception ex)
            {
                res.Success = false;
                res.Logs.Add("ERROR: " + ex.Message);
            }

            return res;
        }
    }

    public enum GuardActionType
    {
        FlattenPosition,
        CancelAllOrders,
        CancelOrder,
        PlaceStopOrder
    }

    public class GuardAction
    {
        public string AccountName { get; set; }
        public GuardActionType ActionType { get; set; }
        public string Instrument { get; set; }
        public Instrument InstrumentObj { get; set; }
        public string OrderId { get; set; }
        public int Quantity { get; set; }
        public string RuleId { get; set; }
        // P1-19: other rules that demanded this same action and were coalesced into it.
        // Kept so merging does not erase why the action was taken.
        public List<string> MergedRuleIds { get; set; }
    }

    public class AccountState
    {
        public string AccountName { get; }
        public Dictionary<string, PositionState> Positions { get; } = new Dictionary<string, PositionState>();
        public double RealizedPnL { get; set; } = 0.0;
        // P1-17: realized PnL banked in *completed* sessions. RealizedPnL above is
        // session-scoped and zeroed at every reset, which is right for the daily-loss rule and
        // wrong for EvaluationTargetProfit -- a cumulative, multi-day prop evaluation target.
        // The total to evaluate a cumulative target against is TotalRealizedPnL below.
        // Accumulated once per session reset rather than per realized-PnL delta: a delta-based
        // total would be permanently corrupted by a single spurious tick (e.g. the broker
        // rebasing its own counter before our session reset runs), whereas a session total is
        // rebased every day and cannot drift.
        public double CumulativeRealizedPnL { get; set; } = 0.0;
        public double TotalRealizedPnL { get { return CumulativeRealizedPnL + RealizedPnL; } }
        // P1-16: realized PnL banked for the trade currently being closed, summed across its
        // partial exits and judged once at the flat transition. Deliberately not persisted --
        // a restart mid-trade settles it as a scratch rather than inventing a result.
        public double OpenTradeRealizedDelta { get; set; } = 0.0;
        // True from a flat transition until the next entry: the window in which a late fill
        // for the closed trade may still arrive and must revise its settlement.
        public bool ClosedTradeAwaitingLateFills { get; set; } = false;
        // The streak as it stood before the current trade was judged, so re-judging on a late
        // fill is a correction rather than a second increment.
        public int ConsecutiveLossesBeforeSettlement { get; set; } = 0;
        public double UnrealizedPnL { get; set; } = 0.0;
        public double PeakEquity { get; set; } = 0.0;
        public double PeakOpenGain { get; set; } = 0.0;
        public bool PeakGivebackTriggered { get; set; } = false;
        public double PeakGivebackLastTriggerUnrealized { get; set; } = double.NaN;
        public bool IsLockedOut { get; set; } = false;
        public DateTime LockoutUntil { get; set; } = DateTime.MinValue;
        public bool InitialLockoutFlattened { get; set; } = false;
        public DateTime LastLockoutFlattenAttempt { get; set; } = DateTime.MinValue;

        // P2-101. How many intervention attempts the CURRENT lockout phase has emitted, and
        // whether its give-up warning has been written. Both reset when a phase is entered.
        //
        // The retry's exit condition was "the position is still open", which in shadow mode is an
        // action the guard does not perform -- so it never exited. Measured 2026-08-14: ~12 lines
        // per minute per account, indefinitely, on three sim accounts AND the funded one, burying
        // interventions.jsonl. The general rule, and it is worth grepping for elsewhere: A RETRY
        // WHOSE EXIT CONDITION IS AN ACTION THE CURRENT MODE DOES NOT PERFORM WILL NEVER EXIT.
        public int LockoutPhaseAttempts { get; set; } = 0;
        public bool LockoutStuckLogged { get; set; } = false;

        /// <summary>
        /// P2-101. Everything the lockout PHASE machine owns, cleared together.
        ///
        /// Four call sites end a lockout -- the daily session reset, the deadline lapse, the
        /// not-locked-out sweep branch, and UnlockAccount -- and each had its own copy of the
        /// two-line reset. Adding a third field to the cluster meant editing all four, which is
        /// how P1-100's three readers happened. One method, four callers.
        /// </summary>
        public void ResetLockoutPhase()
        {
            CurrentLockoutPhase = LockoutPhase.None;
            InitialLockoutFlattened = false;
            LockoutPhaseAttempts = 0;
            LockoutStuckLogged = false;
        }
        // P2-46: order id -> first time seen inside the rate window. Keyed by id so one order
        // passing Submitted -> Accepted -> Working counts once, not three times.
        public Dictionary<string, DateTime> RecentOrderIds { get; set; } = new Dictionary<string, DateTime>();

        // Lockout phase: PendingCancel -> PendingFlatten -> Confirmed.
        // Only Confirmed stops emitting actions. This prevents the infinite
        // flatten loop where account.Flatten() fails silently but the sweep
        // keeps re-firing every second.
        public enum LockoutPhase { None, PendingCancel, PendingFlatten, Confirmed }
        public LockoutPhase CurrentLockoutPhase { get; set; } = LockoutPhase.None;
        
        // Session and Overtrading
        public DateTime LastSessionDate { get; set; } = DateTime.MinValue;
        public int TradesToday { get; set; } = 0;
        public int ConsecutiveLosses { get; set; } = 0;
        public DateTime CooldownUntil { get; set; } = DateTime.MinValue;
        public double LastRealizedPnL { get; set; } = 0.0; // To track delta for consec losses
        public double SessionStartRealizedPnL { get; set; } = 0.0; // Baseline for session PnL

        // - Firm-mirror tracking (independent of discretionary PeakEquity) -
        public double FirmTrailingPeak { get; set; } = double.MinValue;
        public bool FirmFloorLocked { get; set; } = false;
        public DateTime FirmDailyDate { get; set; } = DateTime.MinValue;
        public double FirmDailyStartRealized { get; set; } = 0.0;
        public double FirmStartingBalance { get; set; } = 0.0;
        public bool LockoutWasShadowOnly { get; set; } = false;

        public AccountState(string name)
        {
            AccountName = name;
        }

        // P1-16: realized PnL arrives per execution, so a single trade exited in three partials
        // delivers three negative deltas. Counting each one as a "consecutive loss" made a
        // MaxConsecutiveLosses=3 lockout reachable from one losing trade, and put this counter
        // at odds with TradesToday, which is already debounced to the trade lifecycle.
        // Deltas are banked and judged once per trade. Three cases, because the relative order
        // of the realized-PnL event and the position-flat event is NOT guaranteed:
        //
        //  1. A trade is open  -> bank it; SettleClosedTrade judges the total at the flat
        //     transition. This is the fix: partial exits no longer count separately.
        //  2. The trade just closed and a late fill arrives -> revise the settlement in place
        //     rather than let the delta land on the next trade. This is why the running total
        //     and the pre-settlement streak are kept until the *next entry*, not cleared at
        //     settlement: re-judging from the snapshot is exact for any number of late fills,
        //     including one that flips the trade's net result from win to loss.
        //  3. No trade is tracked at all (the guard never saw the position, or this is a
        //     standalone adjustment) -> judge the delta on its own, preserving the pre-existing
        //     behaviour. Silently ignoring untracked realized losses would make the lockout
        //     less sensitive than before, which is not an acceptable trade for this fix.
        public void RecordRealizedDelta(double tradePnL, RiskConfig config)
        {
            OpenTradeRealizedDelta += tradePnL;

            if (ClosedTradeAwaitingLateFills)
            {
                ApplyTradeJudgement(config);
                return;
            }

            if (!HasOpenPosition())
            {
                ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
                ApplyTradeJudgement(config);
                OpenTradeRealizedDelta = 0.0;
                ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
            }
        }

        private bool HasOpenPosition()
        {
            foreach (var p in Positions.Values)
            {
                if (p.MarketPosition != MarketPosition.Flat) return true;
            }
            return false;
        }

        // Re-judges the current trade total from the streak as it stood before this trade was
        // settled, so calling it repeatedly as late fills arrive is idempotent rather than
        // cumulative. A scratch trade leaves the streak untouched in either direction.
        private void ApplyTradeJudgement(RiskConfig config)
        {
            ConsecutiveLosses = ConsecutiveLossesBeforeSettlement;

            if (OpenTradeRealizedDelta < -0.01)
                ConsecutiveLosses++;
            else if (OpenTradeRealizedDelta > 0.01)
                ConsecutiveLosses = 0;

            if (config != null && config.Overtrading != null
                && config.Overtrading.MaxConsecutiveLosses > 0
                && ConsecutiveLosses >= config.Overtrading.MaxConsecutiveLosses
                && config.Overtrading.CooldownMinutes > 0)
            {
                CooldownUntil = DateTime.UtcNow.AddMinutes(config.Overtrading.CooldownMinutes);
            }
        }

        // Judges the trade that just closed. Called on flat transitions and on flips (a flip is
        // a close plus an entry in one update).
        private void SettleClosedTrade(RiskConfig config)
        {
            ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
            ApplyTradeJudgement(config);
            ClosedTradeAwaitingLateFills = true;
        }

        public bool UpdatePosition(Account account, Instrument instrument, MarketPosition position, int quantity, double avgPrice, double unrealizedPnL, RiskConfig config)
        {
            if (quantity == 0)
            {
                position = MarketPosition.Flat;
            }

            string instrumentName = instrument.FullName;
            if (!Positions.TryGetValue(instrumentName, out var pState))
            {
                pState = new PositionState(instrument);
                Positions[instrumentName] = pState;
            }

            bool stateChanged = false;

            bool wasNonFlat = pState.MarketPosition != MarketPosition.Flat;
            bool isNonFlat = position != MarketPosition.Flat;
            bool isFlip = wasNonFlat && isNonFlat && position != pState.MarketPosition;

            // Treat a flip as a close of the old trade followed by a new entry.
            if ((position == MarketPosition.Flat && wasNonFlat) || isFlip)
            {
                pState.LastFlatTransition = DateTime.UtcNow;
                stateChanged = true;

                // P1-16: the trade is over -- judge it once, on its net realized result.
                SettleClosedTrade(config);

                if (isFlip)
                {
                    // NinjaTrader collapsed a close + reverse into one update.
                    // Log it so shadow data reveals how often flips occur.
                    NinjaTrader.Code.Output.Process(
                        $"[RiskGuard] FLIP detected on {AccountName}/{instrumentName}: " +
                        $"{pState.MarketPosition} -> {position}. Counted as close+entry.",
                        PrintTo.OutputTab1);
                }
            }

            // --- OPEN side: a new entry begins (flat->nonflat, or the new leg of a flip) ---
            if ((isNonFlat && !wasNonFlat) || isFlip)
            {
                pState.LastNonFlatTransition = DateTime.UtcNow;

                // A flip closes the old position and opens a new opposite leg in one
                // update. Reset the per-open-position peak-giveback tracking so the
                // new leg is not judged against the prior direction's peak.
                if (isFlip)
                {
                    PeakOpenGain = 0.0;
                    PeakGivebackTriggered = false;
                    PeakGivebackLastTriggerUnrealized = double.NaN;
                }

                // Debounce multi-contract / split-order trade count increment:
                // Only increment TradesToday if this is a genuine new trade lifecycle
                // (either a flip, or position was flat for > 1000ms, or initial entry).
                bool isGenuineNewTrade = isFlip || pState.LastFlatTransition == DateTime.MinValue ||
                                         (DateTime.UtcNow - pState.LastFlatTransition).TotalMilliseconds > 1000;

                if (isGenuineNewTrade)
                {
                    TradesToday++; // Increment trade count
                }

                // P1-16: a new trade starts with a clean slate. Until this point the previous
                // trade's total and pre-settlement streak are deliberately retained so a late
                // fill can revise its judgement.
                ClosedTradeAwaitingLateFills = false;
                OpenTradeRealizedDelta = 0.0;
                ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
                stateChanged = true;
            }
            else if (position == MarketPosition.Flat && wasNonFlat)
            {
                pState.LastNonFlatTransition = DateTime.MinValue;
            }

            pState.MarketPosition = position;
            pState.Quantity = quantity;
            pState.AveragePrice = avgPrice;
            pState.UnrealizedPnL = unrealizedPnL;

            // When the account returns to flat, reset the per-open-position
            // peak-giveback tracking so it cannot carry into the next trade.
            if (position == MarketPosition.Flat && wasNonFlat)
            {
                bool accountNowFlat = true;
                foreach (var pos in Positions.Values)
                {
                    if (pos.MarketPosition != MarketPosition.Flat)
                    {
                        accountNowFlat = false;
                        break;
                    }
                }

                if (accountNowFlat)
                {
                    PeakOpenGain = 0.0;
                    PeakGivebackTriggered = false;
                    PeakGivebackLastTriggerUnrealized = double.NaN;
                }
            }

            return stateChanged;
        }

        public void RecordExecution(string instrument, string action, int quantity, double price)
        {
            // Simple calculation of PnL can be done if execution updates are matched,
            // but in practice NinjaTrader handles account balance updates directly.
        }
    }

    public class FirmMirrorResult
    {
        public bool TrailingDDBreached { get; set; }
        public bool DailyLossBreached { get; set; }
        public double TrailingPeak { get; set; }
        public bool FloorLocked { get; set; }
        public double EffectiveFloor { get; set; }
        public double GuardFloor { get; set; }
        public double GuardDailyLimit { get; set; }
        public bool StateChanged { get; set; }
        public List<string> TraceLogs { get; set; } = new List<string>();
    }

    public class FirmDiagnosticsResult
    {
        public bool Success { get; set; }
        public List<string> Logs { get; set; } = new List<string>();
    }

    public class PositionState
    {
        public string Instrument { get; }
        public Instrument InstrumentObj { get; }
        public MarketPosition MarketPosition { get; set; } = MarketPosition.Flat;
        public int Quantity { get; set; }
        public double AveragePrice { get; set; }
        public double UnrealizedPnL { get; set; }
        public DateTime LastNonFlatTransition { get; set; } = DateTime.MinValue;
        public DateTime LastFlatTransition { get; set; } = DateTime.MinValue;

        public PositionState(Instrument instrument)
        {
            InstrumentObj = instrument;
            Instrument = instrument.FullName;
        }
    }

    internal static class RiskGuardOrderUtils
    {
        public static bool IsPositionReducingOrder(Order order, AccountState stateModel)
        {
            if (order == null || order.Instrument == null || stateModel == null) return false;
            string instrName = order.Instrument.FullName;
            if (!stateModel.Positions.TryGetValue(instrName, out var pState)) return false;

            if (pState.MarketPosition == MarketPosition.Long)
            {
                return order.OrderAction == OrderAction.Sell || order.OrderAction == OrderAction.SellShort;
            }
            else if (pState.MarketPosition == MarketPosition.Short)
            {
                return order.OrderAction == OrderAction.Buy || order.OrderAction == OrderAction.BuyToCover;
            }

            return false;
        }
    }

    // -
    // PER-POSITION GUARD STATE MACHINE (-6 of RiskGuardAddOn.md)
    // -
    // Tracks the protective-stop lifecycle for one (account, instrument) pair.
    // Eliminates the duplicate-SL race on OCO brackets by remembering that the
    // stop leg's Submitted event was already observed, so a later sweep or
    // re-entrant position update finds the FSM in ProtectedPending/Protected.
    public enum GuardFsmState
    {
        Unprotected,       // position open, no covering stop observed yet
        ProtectedPending,  // stop leg Submitted/Initialized/Accepted, not yet Working
        Protected,         // working stop covering the position
        FlattenPending,    // grace expired with OnMissing=Flatten, action emitted once
        Flat               // position closed; FSM entry awaiting cleanup
    }

    public class PositionGuardFsm
    {
        public string AccountName { get; }
        public string Instrument { get; }
        private GuardFsmState _state = GuardFsmState.Unprotected;
        public GuardFsmState State
        {
            get { return _state; }
            set
            {
                GuardFsmState previous = _state;
                _state = value;
                // Reset the per-episode auto-stop attempt counter when the FSM
                // reaches Protected (successful protection), reaches Flat (position
                // closed), transitions from Flat back to Unprotected (new episode),
                // or transitions from Protected back to Unprotected (protection
                // removed). We deliberately do NOT reset on Unprotected ->
                // ProtectedPending so that failed submit attempts continue to count
                // toward escalation.
                if (value == GuardFsmState.Protected && previous != value)
                    AutoStopAttempts = 0;
                else if (value == GuardFsmState.Flat && previous != value)
                    AutoStopAttempts = 0;
                else if (previous == GuardFsmState.Flat && value == GuardFsmState.Unprotected)
                    AutoStopAttempts = 0;
                else if (previous == GuardFsmState.Protected && value == GuardFsmState.Unprotected)
                    AutoStopAttempts = 0;
            }
        }
        public MarketPosition PositionSide { get; set; } = MarketPosition.Flat;
        public int PositionQuantity { get; set; }
        // P1-36. Coverage used to follow ONE Order. A trader covering a 6-lot position with two
        // working 3-lot stops therefore read as CoveredQuantity 3, the under-coverage rule fired,
        // and the guard attached a 3-lot auto-stop on top -- 9 lots of protection on a 6-lot
        // position, which flips it 3 lots the wrong way when the stops trigger. The guard
        // manufactured the reversal it exists to prevent.
        //
        // Coverage is now the SUM over every non-terminal protective stop working against this
        // position, and both `CoveredQuantity` and `RecognizedStopOrder` are DERIVED from that
        // list. They are read-only on purpose: the old pair had to be assigned together at nine
        // separate sites, and nothing stopped them drifting apart.
        //
        // NOTE: NT8 Order.OrderId is NOT unique and can change over the order's
        // lifetime (historical->live transition). Track recognised stops by the
        // Order object reference, not by id string. See RiskGuardAddOn.md -6.6.
        private readonly List<Order> _recognizedStops = new List<Order>();

        /// <summary>
        /// Drops stops that have gone terminal. Called on every read, so a cancelled or filled
        /// stop stops counting toward coverage the instant it is observed -- there is no window
        /// in which the FSM believes a dead order is protecting the position.
        /// </summary>
        private void PruneRecognizedStops()
        {
            _recognizedStops.RemoveAll(o => o == null || !RiskGuardAddOn.ProvidesCoverage(o.OrderState));
        }

        /// <summary>
        /// Adds a stop to the position's cover. Idempotent by object reference: NT8 raises
        /// OrderUpdate repeatedly for the same order, and counting one order twice would report
        /// cover that does not exist -- the same class of error as P1-36 itself, inverted.
        /// </summary>
        public void AddRecognizedStop(Order stop)
        {
            if (stop == null || !RiskGuardAddOn.ProvidesCoverage(stop.OrderState)) return;
            PruneRecognizedStops();
            if (_recognizedStops.Any(o => ReferenceEquals(o, stop))) return;
            _recognizedStops.Add(stop);
        }

        /// <summary>Removes one stop from the cover. Returns true if it was actually tracked.</summary>
        public bool RemoveRecognizedStop(Order stop)
        {
            if (stop == null) return false;
            int removed = _recognizedStops.RemoveAll(o => ReferenceEquals(o, stop));
            PruneRecognizedStops();
            return removed > 0;
        }

        /// <summary>True if this exact order is one of the stops currently covering the position.</summary>
        public bool IsRecognizedStop(Order stop)
        {
            if (stop == null) return false;
            return _recognizedStops.Any(o => ReferenceEquals(o, stop));
        }

        public void ClearRecognizedStops()
        {
            _recognizedStops.Clear();
        }

        /// <summary>Every live stop covering this position. Snapshot; safe to enumerate.</summary>
        public List<Order> RecognizedStops
        {
            get { PruneRecognizedStops(); return new List<Order>(_recognizedStops); }
        }

        /// <summary>
        /// The largest live stop covering the position, or null. Retained because the diagnostics
        /// surface and the qty-only-update path both want "the" stop, and because a single-stop
        /// position -- overwhelmingly the common case -- still has an unambiguous answer.
        /// It is NOT the coverage figure: use <see cref="CoveredQuantity"/> for that.
        /// </summary>
        public Order RecognizedStopOrder
        {
            get
            {
                PruneRecognizedStops();
                Order best = null;
                foreach (var o in _recognizedStops)
                    if (best == null || o.Quantity > best.Quantity) best = o;
                return best;
            }
        }

        public Order AutoStopOrder { get; set; }
        public string EntryOcoId { get; set; }   // best-effort join key; may be empty for external brackets
        public DateTime EntryTime { get; set; } = DateTime.MinValue;
        public DateTime GraceDeadline { get; set; } = DateTime.MinValue;
        public DateTime LastTransitionTime { get; set; } = DateTime.UtcNow;
        // One-shot grace timer: fires exactly at EntryTime + StopGuard.StopAttachSeconds.
        // Cancelled when the FSM reaches Protected or Flat. This replaces the sweep
        // polling of GraceDeadline with an instant event-driven trigger.
        public Timer GraceTimer { get; set; }

        /// <summary>
        /// Total quantity covered by every live protective stop on this position (P1-36).
        /// Derived, never assigned -- there is no way to record coverage that no order backs.
        /// </summary>
        public int CoveredQuantity
        {
            get
            {
                PruneRecognizedStops();
                int total = 0;
                foreach (var o in _recognizedStops) total += o.Quantity;
                return total;
            }
        }
        // True while a one-shot grace timer is armed.
        public bool GracePending { get; set; }
        // True once a grace action has been emitted and its outcome is still pending.
        public bool GraceEmitted { get; set; }
        // Monotonically increasing generation counter to invalidate stale timer callbacks.
        public long GraceGeneration { get; set; }
        // Number of auto-stop submit attempts in the current unprotected episode.
        // Escalation to flatten happens when this exceeds MaxAutoStopAttempts.
        public int AutoStopAttempts { get; set; }

        public PositionGuardFsm(string accountName, string instrument)
        {
            AccountName = accountName;
            Instrument = instrument;
        }
    }

    /// <summary>
    /// P2-41. `POST /api/riskguard/config` did `req.ToObject&lt;RiskConfig&gt;()` and handed the
    /// result straight to `SaveAndReloadConfig`. Deserialising a partial body into a complete
    /// `RiskConfig` gives every OMITTED field its default -- and that default was then written to
    /// `RiskGuard/config.json` and reloaded live. A caller posting `{"ExcludedAccounts":["X"]}` to
    /// add one exclusion also reset `Mode` to shadow, `MinShadowSessions` to 0, `EnableWindowGate`
    /// to false, and every StopGuard/PnLRules/FirmMirror value to its default -- destroying the
    /// live risk configuration. The response then said `"applied"` and echoed the REQUEST, so
    /// nothing about the reply revealed it.
    ///
    /// This lives here, not in `McpBridgeAddOn.cs`, because that file is excluded from the test
    /// build (WPF dependencies). The merge is pure JSON manipulation with nothing NinjaTrader
    /// about it, so keeping it here is what makes it testable at all.
    /// </summary>
    public static class RiskConfigMerge
    {
        /// <summary>
        /// Returns <paramref name="live"/> with only the keys present in <paramref name="patch"/>
        /// replaced. Nested objects merge recursively; arrays are REPLACED, not concatenated.
        ///
        /// Arrays replace deliberately. Union semantics would make `ExcludedAccounts` an
        /// append-only list with no way to remove an entry through the API, and concatenation is
        /// the exact mechanism behind P1-39 -- a list that grew on every write until a default
        /// could never be deleted. Replace is also what a caller means by sending an array.
        /// </summary>
        public static JObject Merge(JObject live, JObject patch)
        {
            if (live == null) return patch == null ? new JObject() : (JObject)patch.DeepClone();
            var merged = (JObject)live.DeepClone();
            if (patch == null) return merged;

            merged.Merge(patch, new JsonMergeSettings
            {
                MergeArrayHandling = MergeArrayHandling.Replace,
                // A caller who explicitly sends null means "clear this", which is a different
                // instruction from omitting the key. Omitted keys never appear in `patch` at all,
                // so they are untouched either way.
                MergeNullValueHandling = MergeNullValueHandling.Merge
            });
            return merged;
        }

        /// <summary>
        /// Convenience for the bridge: merge a partial body onto the live config and hand back a
        /// typed config plus the merged document to echo. Echoing the RESULT rather than the
        /// request is half the fix -- the old reply looked identical whether the merge happened
        /// or not.
        /// </summary>
        public static RiskConfig Apply(RiskConfig liveConfig, JObject patch, out JObject mergedJson)
        {
            var live = liveConfig == null ? new JObject() : JObject.FromObject(liveConfig);
            mergedJson = Merge(live, patch);
            return mergedJson.ToObject<RiskConfig>();
        }
    }

    public class PersistedStateData
    {
        public bool IsArmed { get; set; }
        public string Mode { get; set; }
        public List<string> LockedOutAccounts { get; set; } = new List<string>();
        // FR-29: count of completed shadow sessions. Persisted across restarts.
        public int ShadowSessionsCompleted { get; set; }
        // P1-37: the session date the counter was last incremented for. This MUST travel
        // with the counter. Persisting one without the other is what let a restart re-count
        // the same day -- the counter came back, the "already counted today" marker did not,
        // and MinShadowSessions could be satisfied by recompiling three times.
        public DateTime LastShadowSessionDate { get; set; } = DateTime.MinValue;
        
        // Dictionary for per-account persisted data
        public Dictionary<string, AccountPersistedData> AccountsData { get; set; } = new Dictionary<string, AccountPersistedData>();
        
        public DateTime Timestamp { get; set; }
    }

    public class AccountPersistedData
    {
        public DateTime LastSessionDate { get; set; }
        public int TradesToday { get; set; }
        public int ConsecutiveLosses { get; set; }
        public double PeakEquity { get; set; }
        public double LastRealizedPnL { get; set; }
        public double SessionStartRealizedPnL { get; set; }
        // P1-17: must persist -- a cumulative evaluation target that resets on recompile is
        // not cumulative.
        public double CumulativeRealizedPnL { get; set; }
        public double FirmTrailingPeak { get; set; }
        public bool FirmFloorLocked { get; set; }
        public DateTime FirmDailyDate { get; set; }
        public double FirmDailyStartRealized { get; set; }
        public double FirmStartingBalance { get; set; }
        // P1-54: the lockout DEADLINE must persist, not just the fact of the lockout. The
        // top-level LockedOutAccounts name list restored IsLockedOut = true with LockoutUntil
        // left at MinValue, so any restart -- and a recompile is a restart here -- silently
        // converted a 60-minute lockout into one that lasts until the session reset.
        public DateTime LockoutUntil { get; set; }
        public bool LockoutWasShadowOnly { get; set; }
    }

    // -
    // CONFIGURATION MODELS
    // -

    public class InstrumentProfile
    {
        public int MaxContracts { get; set; } = 5;
    }

    public class AccountRiskProfile
    {
        public string ProfileName { get; set; } = "Default";
        public string AccountNamePattern { get; set; } = ".*";

        public double DailyLossLimit { get; set; } = 0.0;
        public double TrailingDrawdown { get; set; } = 0.0;
        public int MaxTradesPerSession { get; set; } = 0;
        public int DefaultMaxContracts { get; set; } = 0;

        public Dictionary<string, InstrumentProfile> InstrumentProfiles { get; set; } = new Dictionary<string, InstrumentProfile>(StringComparer.OrdinalIgnoreCase);
    }

    public class PerInstrumentRiskConfig
    {
        // Only MaxContracts is enforced. Per-instrument blocking is intentionally
        // not a property here; blocking has exactly one mechanism: BlockedInstruments.
        // See P2-78.
        public int MaxContracts { get; set; } = 10;
    }

    // P1-39: every List property below carries ObjectCreationHandling.Replace. Json.NET's
    // default (Auto) REUSES a collection that a property initializer already populated and
    // *appends* the deserialized items to it, so each load re-added the initializer's contents.
    // Only WindowsET/Days had non-empty initializers and therefore actually corrupted, but any
    // default added to the others later would silently become the same bug.
    //
    // This is deliberately per-property and NOT set on the serializer. The dictionaries here
    // (InstrumentLimits, and FirmMirrorConfig's AccountFirmMap/FirmProfiles) are constructed
    // with StringComparer.OrdinalIgnoreCase; Replace would discard that instance and hand back
    // a fresh Dictionary using the default comparer, quietly making instrument and firm lookups
    // case-sensitive. They are empty-initialized, so appending to them is already correct.
    public class RiskConfig
    {
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<AccountRiskProfile> Profiles { get; set; } = new List<AccountRiskProfile>();
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<string> ExcludedAccounts { get; set; } = new List<string>();
        // Accounts listed here MAY bypass a persisted lockout when the guard is disarmed.
        // Accounts NOT listed here keep their lockout enforced even when disarmed (safe default for prop-firm accounts).
        // Default empty = lockouts persist for ALL accounts regardless of armed state.
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<string> LockoutBypassWhileDisarmedAccounts { get; set; } = new List<string>();
        public string Mode { get; set; } = "shadow";
        public bool EnableWindowGate { get; set; } = false;
        // FR-29: minimum completed shadow sessions before live-mode arming is permitted (soft gate).
        // Set to 0 to disable. The counter is persisted in PersistedStateData and incremented on session reset.
        // P1-84. Was 0, and RunPreflight's FR-29 gate reads
        // `MinShadowSessions > 0 && _shadowSessionsCompleted < MinShadowSessions` -- so zero
        // does not relax the precondition, it SWITCHES IT OFF, and live arming was gated on
        // nothing at all. Five is roughly a week of sessions watched without the guard wanting
        // to intervene wrongly, before it can be pointed at live money.
        public int MinShadowSessions { get; set; } = 5;
        public int AuditIntervalSeconds { get; set; } = 10;
        public Dictionary<string, PerInstrumentRiskConfig> InstrumentLimits { get; set; } = new Dictionary<string, PerInstrumentRiskConfig>(StringComparer.OrdinalIgnoreCase);
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<string> BlockedInstruments { get; set; } = new List<string>();
        public SizingConfig Sizing { get; set; } = new SizingConfig();
        public OvertradingConfig Overtrading { get; set; } = new OvertradingConfig();
        public StopGuardConfig StopGuard { get; set; } = new StopGuardConfig();
        public PnLRulesConfig PnLRules { get; set; } = new PnLRulesConfig();
        public FirmMirrorConfig FirmMirror { get; set; } = new FirmMirrorConfig();
        // FR-35/36: override friction for override_with_friction enforcement mode.
        public OverrideConfig Override { get; set; } = new OverrideConfig();
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<WindowConfig> WindowsET { get; set; } = new List<WindowConfig>
        {
            new WindowConfig { Name = "NY_AM_Macro", Start = "09:50", End = "11:10" },
            new WindowConfig { Name = "NY_PM_Macro", Start = "13:50", End = "15:10" }
        };
    }

    // FR-35/36: friction-gated lockout override. When Mode == "override_with_friction",
    // escaping a lockout requires typing the exact confirm phrase AND waiting wait_seconds
    // (enforced minimum 30s). This prevents one-click panic bypasses.
    public class OverrideConfig
    {
        public string ConfirmPhrase { get; set; } = "I understand locked means locked";
        // FR-36 enforced minimum: clamped to >= 30 at validation time.
        public int WaitSeconds { get; set; } = 120;
    }

    public class FirmMirrorConfig
    {
        public bool Enabled { get; set; } = false;
        public FirmTrailingDDConfig TrailingDD { get; set; } = new FirmTrailingDDConfig();
        public FirmDailyLossConfig DailyLoss { get; set; } = new FirmDailyLossConfig();
        public int DailyResetHourUtc { get; set; } = 22;
        public int DailyResetMinuteUtc { get; set; } = 0;
        // P2-95: populated by ResolveEffectiveFirmConfig from the matched FirmProfile.
        // Not serialized in config — it is a transient carrier so ComputeFirmMirror can
        // use the plan's stated AccountSize as the starting balance instead of the
        // heuristic (balance - realized - unrealized), which is session-scoped and wrong
        // by the account's lifetime profit. JsonIgnore because it is never user-configured.
        [JsonIgnore]
        public double ResolvedAccountSize { get; set; } = 0.0;
        // Per-firm profiles: map account name -> firm name. The matching FirmProfile in FirmProfiles
        // supplies the firm-specific drawdown/daily-loss rules. Falls back to TrailingDD/DailyLoss above
        // when an account is not mapped or the firm name is not found.
        public Dictionary<string, string> AccountFirmMap { get; set; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string, FirmProfile> FirmProfiles { get; set; } = new Dictionary<string, FirmProfile>(StringComparer.OrdinalIgnoreCase);
    }

    // Per-firm rules researched 2026-08-02. All four firms use EOD trailing drawdown for evaluations;
    // daily loss limits vary (TPT has none). Reset boundary is CME Globex rollover (~22:00 UTC).
    public class FirmProfile
    {
        public string Name { get; set; } = "";

        /// <summary>
        /// The account size these dollar amounts were derived for, or 0 for "not stated".
        ///
        /// CONFIG_DEFAULTS R3: a dollar limit is derived from the account, never guessed. None of
        /// the four researched profiles stated a size, which is why `Apex` carried 2000 while Apex
        /// publishes 2500 on a 50k and 3000 on a 100k -- tighter than the firm's own number, which
        /// is the safe direction, but nothing in the file said which direction it was. Keys are
        /// now plan names (`Apex-100K`), and this is the machine-readable half of that: preflight
        /// compares it against the account's observed equity, so a 100k account mapped to a 50k
        /// plan is refused instead of silently protected at the wrong threshold.
        ///
        /// 0 means unstated and is NOT an error -- the check is opt-in per plan, because an
        /// operator adding a plan should not be blocked from arming until they have researched a
        /// number they may not have. A plan that states nothing is checked for nothing.
        /// </summary>
        public double AccountSize { get; set; } = 0.0;

        public FirmTrailingDDConfig TrailingDD { get; set; } = new FirmTrailingDDConfig();
        public FirmDailyLossConfig DailyLoss { get; set; } = new FirmDailyLossConfig();
    }

    public class FirmTrailingDDConfig
    {
        public bool Enabled { get; set; } = false;
        public string Type { get; set; } = "intraday";
        public bool IncludesUnrealized { get; set; } = true;
        public double Amount { get; set; } = 2500.0;
        public double Buffer { get; set; } = 300.0;
        public double LockAtProfit { get; set; } = 0.0;
    }

    public class FirmDailyLossConfig
    {
        public bool Enabled { get; set; } = false;
        public string Basis { get; set; } = "realized";
        public double Amount { get; set; } = 1500.0;
        public double Buffer { get; set; } = 200.0;
    }

    public class SizingConfig
    {
        public int MaxContractsPerAccount { get; set; } = 10;
        public int MaxContractsAggregate { get; set; } = 20;
        public int ExpectedCopies { get; set; } = 1; // intended N-way mirror across accounts
    }

    public class OvertradingConfig
    {
        public int MaxTradesPerSession { get; set; } = 8;
        public int CooldownMinutes { get; set; } = 5;
        public int MaxConsecutiveLosses { get; set; } = 3;
        // P2-46: was hardcoded at 5 in the order-rate governor, unlike every other limit here.
        public int MaxOrdersPerSecond { get; set; } = 5;
        public int LockoutMinutes { get; set; } = 60;
    }

    public class StopGuardConfig
    {
        public string OnMissing { get; set; } = "Flatten"; // "AutoStop", "Flatten"

        // P1-84 / R5. Was 3, which is the single most likely reason this system gets switched
        // off: three seconds from fill to a working stop, and OnMissing above is "Flatten", so
        // entering manually and reaching for the mouse to place the stop gets you flattened on
        // a day when nothing was wrong. A default that fires on a normal day is a default that
        // disarms the guard, and a guard that is off during the one session that mattered has
        // provided exactly nothing.
        //
        // WARNING: THE NUMBER IS ONLY RIGHT FOR "Flatten", and that pairing is deliberate. If OnMissing
        // were "AutoStop" a much shorter deadline would be correct, because an invented stop is
        // recoverable and being taken out of the trade is not. It stays a plain default rather
        // than a value computed from OnMissing: a getter that recomputes would let a config
        // reload move a deadline while a grace timer was already running, and would read
        // OnMissing off one thread while another wrote it. The relationship is real; expressing
        // it as a mechanism costs more than it is worth. The test that guards this is
        // conditional on OnMissing for exactly the same reason.
        public int StopAttachSeconds { get; set; } = 15;

        public int MaxAutoStopAttempts { get; set; } = 2;
        public Dictionary<string, int> Offsets { get; set; } = new Dictionary<string, int>
        {
            { "NQ", 40 },
            { "MNQ", 40 },
            { "ES", 16 },
            { "MES", 16 },
            { "default", 30 }
        };
    }

    public class PnLRulesConfig
    {
        public double DailyLossLimit { get; set; } = 1000.0;
        public double TrailingDrawdown { get; set; } = 1500.0;
        public int LockoutMinutes { get; set; } = 60;
    }

    public class WindowConfig
    {
        public string Name { get; set; }
        public string Start { get; set; }
        public string End { get; set; }
        // P1-39: non-empty initializer + Json.NET's default Auto handling meant every load
        // appended another Mon-Fri to whatever the file declared. Live Days lists had reached
        // 20-25 entries. Harmless to the gate itself (Days parses into a HashSet) but it is
        // what made the corruption visible and unbounded.
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<string> Days { get; set; } = new List<string> { "Monday", "Tuesday", "Wednesday", "Thursday", "Friday" };
    }

    public class ParsedWindow
    {
        public TimeSpan Start { get; set; }
        public TimeSpan End { get; set; }
        public HashSet<DayOfWeek> Days { get; set; }
    }

}
