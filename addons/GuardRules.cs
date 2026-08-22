// The guard-side rule inventory. UI redesign, UI3 -- see docs/UI_REDESIGN_DESIGN.md §6 and §6a.
//
// WHAT THIS IS FOR, IN ONE SENTENCE: so that "is this limit actually protecting me?" has a
// mechanically derived answer instead of a hand-maintained one.
//
// Three shipped defects are ONE defect -- a config field can be born with no evaluator and
// nothing notices:
//
//   P1-77  EnableConsistencyCap / MaxDailyProfitPctOfTarget: declaration + JSON parser, and
//          nothing else. No evaluator exists. Defaults to TRUE.
//   P2-25  the news shield: EnableNewsShield defaults true, RiskGuardAddOn.cs:1541 genuinely
//          tests it, it genuinely calls IsInNewsWindow, which genuinely iterates _newsEvents --
//          a list nothing outside a test ever appends to, because LocalNewsEventsFilePath is
//          parsed and read by NO loader. Always empty, always false, branch unreachable.
//          ✅ CLOSED: LoadNewsEventsFromDisk exists and runs. ⚠️ AND THE DESCRIPTION ABOVE WENT
//          ON BEING SERVED TO THE OPERATOR FOR TWO DAYS AFTER IT STOPPED BEING TRUE -- P2-113.
//          A registry that records WHY a field is unevaluated inherits the obligation to notice
//          when it becomes evaluated; nothing re-reads a reason once it is written.
//   P2-78  PerInstrumentRiskConfig.IsBlocked / .StopOffsetTicks: zero references anywhere.
//          ✅ CLOSED: both deleted.
//
// ⚠️ P2-25 IS WHY THIS IS A REGISTRY AND NOT A LINTER. A static "is this field read?" check
// scores the news shield as READ -- every mechanical check passes on a rule that has never once
// been able to fire. The state a linter cannot see is INERT: the rule executes and its evidence
// set is empty, so its verdict is a foregone conclusion. Only something running at read time,
// asking each rule how much evidence it evaluated against, can report that.
//
// THE STRUCTURAL PART, which is the point of the whole file: a rule declared without an
// Evaluator delegate reports CONFIGURED-and-not-EVALUATED **by construction**. It cannot be
// mis-reported, because there is nothing to mis-report. And every leaf of RiskConfig and
// PropFirmProtectionConfig must be either a registered rule or an explicit NotARule with a
// stated reason -- asserted by a test over reflection, so a field added to a config class and
// wired to nothing FAILS THE BUILD instead of waiting for an audit.
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
using Newtonsoft.Json.Serialization;

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>
    /// What an operator actually needs to know about one rule, worst first.
    ///
    /// The ordering is load-bearing and a test pins it: a UI sorting by this enum must surface
    /// the dangerous states above the healthy ones, and "the config file reads as protection
    /// that does not exist" is the most dangerous thing this system can report.
    /// </summary>
    public enum GuardRuleState
    {
        /// <summary>In the file, and NO code evaluates it. Renders red, always. P1-77's state.</summary>
        ConfiguredNotEvaluated = 0,

        /// <summary>
        /// Code evaluates it and its evidence set is EMPTY, so the verdict is a foregone
        /// conclusion. P2-25's state, and the one every static check misses.
        /// </summary>
        Inert = 1,

        /// <summary>Evaluated, but cannot act -- shadow mode, disarmed, or an excluded account.</summary>
        EvaluatedNotEnforcing = 2,

        /// <summary>Evaluated and able to act.</summary>
        Enforcing = 3,

        /// <summary>Switched off by the operator. Not a defect; shown so it is not mistaken for one.</summary>
        Disabled = 4
    }

    /// <summary>Where the number in force actually came from. §6: one cap is spread over five keys.</summary>
    public enum GuardRuleSource { Config = 0, InstrumentLimit = 1, AccountProfile = 2, FirmProfile = 3, DefaultFallback = 4 }

    /// <summary>What the rule is measured against, which decides what a breach can do.</summary>
    public enum GuardRuleScope { PerOrder = 0, PerPosition = 1, PerAccount = 2, Aggregate = 3, Session = 4 }

    /// <summary>
    /// One rule's reading for one account. `Limit` and `CurrentValue` are nullable because a
    /// non-numeric rule (StopGuard.OnMissing) has neither, and reporting 0 for "not applicable"
    /// is the exact confusion UI1 removed from the copier metrics.
    /// </summary>
    public class GuardRuleReading
    {
        public double? CurrentValue { get; set; }
        public double? Limit { get; set; }

        /// <summary>
        /// How many pieces of evidence the evaluator actually had. ZERO MEANS INERT.
        ///
        /// This is the field that catches P2-25, and it is why the inventory is a runtime read
        /// rather than a check: the news shield's evaluator runs, returns a clean `false`, and
        /// has 0 news events to have returned anything else from.
        /// </summary>
        public int EvidenceCount { get; set; }

        /// <summary>Set when the rule is off by operator choice, which is not a defect.</summary>
        public bool DisabledByConfig { get; set; }

        /// <summary>
        /// P2-132(b). Whether the rule's current value is PAST its limit, folded out of the SAME
        /// comparison the enforcer makes. This is NOT a sixth state: `Enforcing` vs
        /// `EvaluatedNotEnforcing` is about AUTHORITY (can it act), and this is about the VALUE
        /// (is it in breach). A rule can be EvaluatedNotEnforcing AND breached -- that is exactly
        /// the funded account's MAX_SIZE_BREACH, in shadow, and it is the row the operator most
        /// needs to see flagged.
        /// </summary>
        public bool Breached { get; set; }

        /// <summary>P2-132(b). When the rule last fired, or null if it never has.</summary>
        public DateTime? LastFiredUtc { get; set; }

        /// <summary>Free text the UI shows verbatim. Say what is missing, not that something is missing.</summary>
        public string Note { get; set; }
    }

    /// <summary>What an evaluator is handed. Everything it needs, and no engine it could mutate.</summary>
    public class GuardRuleContext
    {
        public string AccountName { get; set; }
        public RiskConfig Config { get; set; }
        public PropFirmProtectionConfig PropConfig { get; set; }
        public RiskGuardAddOn.AccountStateSnapshot Account { get; set; }

        /// <summary>Every account's snapshot, for Aggregate-scoped rules.</summary>
        public List<RiskGuardAddOn.AccountStateSnapshot> AllAccounts { get; set; }

        /// <summary>How many news events are loaded. P2-25's evidence count, passed in rather than read.</summary>
        public int NewsEventCount { get; set; }

        /// <summary>
        /// P2-113. What the last load of LocalNewsEventsFilePath actually did. The count above
        /// says WHETHER there is evidence; this says WHY there is not, which is the difference
        /// between a row an operator can act on and one they can only look at.
        /// </summary>
        public string NewsEventsLoadStatus { get; set; }
    }

    /// <summary>
    /// One rule, declared once.
    ///
    /// ⚠️ `Evaluator == null` is not an oversight, it is an ASSERTION: nothing in this codebase
    /// evaluates this field. That is what makes CONFIGURED-and-not-EVALUATED structural rather
    /// than something a human has to notice. Do not add a do-nothing delegate to "fill it in" --
    /// that converts an honest red row into a lie, which is the defect, not the fix.
    /// </summary>
    public class GuardRuleDefinition
    {
        public string Name { get; set; }
        public string ConfigPath { get; set; }
        public GuardRuleSource Source { get; set; }
        public GuardRuleScope Scope { get; set; }
        public Func<GuardRuleContext, GuardRuleReading> Evaluator { get; set; }

        /// <summary>Why there is no evaluator. REQUIRED when Evaluator is null; a test enforces it.</summary>
        public string UnevaluatedReason { get; set; }

        /// <summary>
        /// What this rule's EvidenceCount counts, in words the operator reads -- "news events
        /// loaded", "accounts mapped to a firm". §6a asks every rule to report the size of the
        /// evidence it evaluated against, and a bare integer does not say what it is a count OF.
        ///
        /// NULL means the rule is SCALAR: its input is a number in the config that is always
        /// present, so its evidence is legitimately constant and it never goes INERT. That
        /// distinction is not cosmetic -- a test asserts that every rule WITH a label reports
        /// INERT when its collection is empty, and three mutants survived precisely because
        /// nothing separated the two kinds.
        /// </summary>
        public string EvidenceLabel { get; set; }
    }

    /// <summary>One rule's state for one account, as the UI renders it.</summary>
    public class GuardRuleRow
    {
        public string Name { get; set; }
        public string ConfigPath { get; set; }
        public GuardRuleSource Source { get; set; }
        public GuardRuleScope Scope { get; set; }
        public GuardRuleState State { get; set; }
        public double? CurrentValue { get; set; }
        public double? Limit { get; set; }
        public int EvidenceCount { get; set; }
        public string Note { get; set; }

        /// <summary>P2-132(b). Whether the value is past the limit, folded out of the enforcer's own comparison.</summary>
        public bool Breached { get; set; }

        /// <summary>
        /// P2-132(b). When the rule last fired, or null if it never has. Carried so "never fired"
        /// and "fired a minute ago" are different answers in the inventory, which is the whole of
        /// the recency half of this defect.
        /// </summary>
        public DateTime? LastFiredUtc { get; set; }
    }

    public class GuardAccountRules
    {
        public string AccountName { get; set; }
        public bool IsExcluded { get; set; }
        public bool IsLockedOut { get; set; }

        /// <summary>
        /// Equity and trade count, carried as FACTS so a surface can decide what to show.
        ///
        /// ⚠️ The snapshot deliberately does NOT decide which accounts are "active". The live box
        /// lists 96 accounts and 88 of them have zero cash and zero net liquidation -- expired
        /// prop accounts the connection still reports -- so a page that renders all of them is
        /// 92% noise. But the guard TRACKS all 96, and an API that quietly returned 8 would be
        /// lying about its own scope.
        ///
        /// So the numbers travel and the judgement stays at the surface, where it can be stated
        /// and reversed. An account momentarily reporting zero equity because its connection has
        /// not synced must never be hidden without saying so -- that would hide RISK, which is
        /// the one direction this whole design refuses to fail in.
        /// </summary>
        public double AccountEquity { get; set; }
        public int TradesToday { get; set; }

        /// <summary>
        /// F-15. The reason CanTrade would refuse this account, or null if it would allow.
        /// The UI shows this in the inspector's "why am I blocked" field so the operator
        /// does not have to guess which gate refused them. Populated by BuildGuardSnapshot.
        /// </summary>
        public string BlockedReason { get; set; }

        public List<GuardRuleRow> Rules { get; set; }
    }

    public class GuardSnapshot
    {
        public DateTime TakenUtc { get; set; }
        public string Mode { get; set; }
        public bool IsArmed { get; set; }
        public List<GuardAccountRules> Accounts { get; set; }

        /// <summary>
        /// The rules nothing evaluates, reported ONCE and independently of any account.
        ///
        /// ⚠️ This exists because of a hazard one level up from INERT: `P1-77`'s consistency cap is
        /// broken for every account equally, and if the inventory only ever appears UNDER an
        /// account, then a box with no accounts loaded renders a clean, empty, entirely reassuring
        /// page. "Nothing to show" and "nothing is wrong" must not look the same -- that is the
        /// same defect as INERT, told at the level of the snapshot instead of the rule.
        /// </summary>
        public List<GuardRuleRow> UnevaluatedRules { get; set; }
    }

    /// <summary>
    /// A config field that is deliberately NOT a rule, with the reason stated.
    ///
    /// The escape hatch exists because the completeness test would otherwise force fake rules
    /// for `Mode`, `ExcludedAccounts` and friends -- and a gate that makes people invent entries
    /// to satisfy it decays into no gate. The reason is mandatory precisely so the hatch cannot
    /// be used to make an inconvenient field go quiet.
    /// </summary>
    public class GuardNonRule
    {
        public string ConfigPath { get; set; }
        public string Reason { get; set; }
    }

    public static class GuardRuleRegistry
    {
        // ── helpers ───────────────────────────────────────────────────────────────────
        // `evidence` is NOT a synonym for 1. It is how many data points the evaluator had, and
        // a zero makes the rule INERT. For a list-shaped rule -- BlockedInstruments,
        // InstrumentLimits, the news shield -- an EMPTY collection genuinely means the rule can
        // never fire, and saying so is the entire point of this file.
        private static GuardRuleReading R(double? current, double? limit, int evidence, string note = null)
        {
            return new GuardRuleReading { CurrentValue = current, Limit = limit, EvidenceCount = evidence, Note = note };
        }

        // P2-132(b). The full reading, with the breach flag and last-fired timestamp. The breach
        // flag is folded out of the SAME comparison the enforcer makes, so the inventory cannot
        // disagree with the enforcer about whether a rule is in breach.
        private static GuardRuleReading RB(double? current, double? limit, int evidence,
            bool breached, DateTime? lastFiredUtc, string note = null)
        {
            return new GuardRuleReading
            {
                CurrentValue = current,
                Limit = limit,
                EvidenceCount = evidence,
                Breached = breached,
                LastFiredUtc = lastFiredUtc,
                Note = note
            };
        }

        private static GuardRuleReading Off(string note)
        {
            return new GuardRuleReading { DisabledByConfig = true, EvidenceCount = 1, Note = note };
        }

        // P2-116. Evidence for an equity-backed rule is an equity READING, not the existence of
        // an AccountState OBJECT. Every subscribed account has an object, so counting it scored
        // 89 Provider31 accounts at evidence 1 while exactly ONE of them reported any equity --
        // and the 88 rendered byte-identical to the funded account on every row but the number.
        //
        // AccountEquity is a non-nullable double that stays 0.0 until the broker pushes a value,
        // so 0.0 is what "no reading has arrived" looks like from here.
        //
        // Trailing drawdown breaches when currentPnL < PeakEquity - TrailingDrawdown. With no
        // reading PeakEquity stays 0 and the test is `0 < -1500`, never true -- so the rule is
        // structurally incapable of firing, which is exactly what INERT means. It self-heals the
        // moment a number arrives.
        //
        // ⚠️ `!= 0.0` AND NOT `> 0`. An account whose equity has gone NEGATIVE is reporting a
        // reading, and it is the account most likely to be in trouble. Treating that as no
        // evidence would switch this rule to INERT at the moment it matters most, which is a
        // worse defect than the one being fixed. A test pins it.
        private const string NoEquityReading =
            "this account reports no equity, so its peak equity stays 0 and the rule cannot fire";

        private static bool HasEquityReading(RiskGuardAddOn.AccountStateSnapshot account)
        {
            return account != null && !double.IsNaN(account.AccountEquity) && account.AccountEquity != 0.0;
        }

        // P2-132(b). The last-fired timestamp for a rule, from the account's copied map. Null when
        // the account is absent or the rule has never fired. The map is keyed by the enforcer's
        // RuleId, which is the same string the inventory's ConfigPath maps to -- see the mapping
        // table below.
        private static DateTime? LastFiredOf(RiskGuardAddOn.AccountStateSnapshot account, string ruleId)
        {
            if (account == null || account.RuleLastFired == null) return null;
            DateTime t;
            return account.RuleLastFired.TryGetValue(ruleId, out t) ? (DateTime?)t : null;
        }

        // P2-132(b). The number the aggregate cap is actually compared against -- the SAME
        // `normalizedAggregate` EvaluateAggregateSizing computes, so the inventory cannot disagree
        // with the enforcer about the aggregate value OR whether it is in breach. When the copier
        // mirrors ONE trade across N accounts (ExpectedCopies > 1), the aggregate risk is the
        // largest single-account position, NOT the gross sum -- reporting the sum here would flag a
        // breach the enforcer never acts on. When copies <= 1 this is exactly the cross-account sum.
        // Each account's contribution is its TotalPositionQuantity (absolute, summed across
        // instruments in the snapshot), the same per-account number the enforcer sums.
        private static double AggregateNormalizedQuantity(IList<RiskGuardAddOn.AccountStateSnapshot> accounts, int expectedCopies)
        {
            if (accounts == null) return 0;
            double total = 0;
            double maxSingle = 0;
            foreach (var a in accounts)
            {
                if (a == null) continue;
                total += a.TotalPositionQuantity;
                if (a.TotalPositionQuantity > maxSingle) maxSingle = a.TotalPositionQuantity;
            }
            int copies = expectedCopies > 0 ? expectedCopies : 1;
            return copies > 1 ? maxSingle : total;
        }

        private static readonly List<GuardRuleDefinition> _rules = new List<GuardRuleDefinition>
        {
            // -- P&L, per account -------------------------------------------------------
            new GuardRuleDefinition {
                Name = "Daily loss limit", ConfigPath = "PnLRules.DailyLossLimit",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => c.Config.PnLRules.DailyLossLimit <= 0
                    ? Off("no daily loss limit set")
                    : R(c.Account == null ? (double?)null : c.Account.RealizedPnL,
                        -Math.Abs(c.Config.PnLRules.DailyLossLimit), c.Account == null ? 0 : 1)
            },
            new GuardRuleDefinition {
                Name = "Trailing drawdown", ConfigPath = "PnLRules.TrailingDrawdown",
                EvidenceLabel = "accounts reporting an equity reading",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => c.Config.PnLRules.TrailingDrawdown <= 0
                    ? Off("no trailing drawdown set")
                    // CurrentValue is NULL rather than 0.0 when there is no reading: a displayed
                    // `cur=0.0` is a number the operator reads as this account is flat, which is
                    // the same confusion the copier metrics removed.
                    : R(HasEquityReading(c.Account) ? (double?)c.Account.AccountEquity : null,
                        c.Config.PnLRules.TrailingDrawdown, HasEquityReading(c.Account) ? 1 : 0,
                        HasEquityReading(c.Account) ? null : NoEquityReading)
            },

            // -- sizing -----------------------------------------------------------------
            new GuardRuleDefinition {
                Name = "Max contracts per account", ConfigPath = "Sizing.MaxContractsPerAccount",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => c.Config.Sizing.MaxContractsPerAccount <= 0
                    ? Off("no per-account contract cap")
                    // Breach is NOT re-derived here from the flat config cap: the enforcer compares
                    // each position to its RESOLVED per-instrument limit (ResolveMaxContracts), which
                    // a per-symbol profile can set below the account default. GetAccountSnapshots
                    // computes the breach the enforcer's own way and hands it over, so the two cannot
                    // disagree ("derive the display from the enforcer", F-9).
                    : RB(c.Account == null ? (double?)null : c.Account.MaxPositionQuantity,
                        c.Config.Sizing.MaxContractsPerAccount, c.Account == null ? 0 : 1,
                        c.Account != null && c.Account.MaxPositionQuantityBreached,
                        LastFiredOf(c.Account, "MAX_SIZE_BREACH"))
            },
            new GuardRuleDefinition {
                Name = "Max contracts aggregate", ConfigPath = "Sizing.MaxContractsAggregate",
                EvidenceLabel = "accounts visible to the aggregate cap",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Aggregate,
                // Evidence is the number of accounts it can see. An aggregate cap over ZERO
                // known accounts is not enforcing anything, and would otherwise read as green.
                // P2-132(b): currentValue is `normalizedAggregate` -- the exact number the enforcer
                // compares to the limit -- so the breach flag is the enforcer's own `> limit`
                // comparison and cannot disagree with it. Computed once, used for both value and flag.
                Evaluator = c =>
                {
                    if (c.Config.Sizing.MaxContractsAggregate <= 0) return Off("no aggregate contract cap");
                    double normalized = AggregateNormalizedQuantity(c.AllAccounts, c.Config.Sizing.ExpectedCopies);
                    return RB(normalized, c.Config.Sizing.MaxContractsAggregate,
                        c.AllAccounts == null ? 0 : c.AllAccounts.Count,
                        normalized > c.Config.Sizing.MaxContractsAggregate,
                        LastFiredOf(c.Account, "AGGREGATE_SIZE_BREACH"));
                }
            },

            // -- overtrading ------------------------------------------------------------
            new GuardRuleDefinition {
                Name = "Max trades per session", ConfigPath = "Overtrading.MaxTradesPerSession",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                Evaluator = c => c.Config.Overtrading.MaxTradesPerSession <= 0
                    ? Off("no per-session trade cap")
                    : R(c.Account == null ? (double?)null : c.Account.TradesToday,
                        c.Config.Overtrading.MaxTradesPerSession, c.Account == null ? 0 : 1)
            },
            new GuardRuleDefinition {
                Name = "Max consecutive losses", ConfigPath = "Overtrading.MaxConsecutiveLosses",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                Evaluator = c => c.Config.Overtrading.MaxConsecutiveLosses <= 0
                    ? Off("no consecutive-loss cap")
                    : R(c.Account == null ? (double?)null : c.Account.ConsecutiveLosses,
                        c.Config.Overtrading.MaxConsecutiveLosses, c.Account == null ? 0 : 1)
            },
            new GuardRuleDefinition {
                Name = "Max orders per second", ConfigPath = "Overtrading.MaxOrdersPerSecond",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerOrder,
                Evaluator = c => R(null, c.Config.Overtrading.MaxOrdersPerSecond > 0
                    ? c.Config.Overtrading.MaxOrdersPerSecond : 5, 1,
                    c.Config.Overtrading.MaxOrdersPerSecond > 0 ? null : "falling back to the built-in 5/s")
            },
            new GuardRuleDefinition {
                Name = "Duplicate entry window", ConfigPath = "Overtrading.DuplicateEntryWindowMs",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerOrder,
                Evaluator = c => c.Config.Overtrading.DuplicateEntryWindowMs <= 0
                    ? Off("duplicate entry window is 0")
                    : R(null, c.Config.Overtrading.DuplicateEntryWindowMs, 1)
            },

            // -- stop guard -------------------------------------------------------------
            new GuardRuleDefinition {
                Name = "Action on missing stop", ConfigPath = "StopGuard.OnMissing",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerPosition,
                Evaluator = c => R(null, null, 1, "on missing stop: " + (c.Config.StopGuard.OnMissing ?? "Flatten"))
            },
            new GuardRuleDefinition {
                Name = "Stop attach deadline", ConfigPath = "StopGuard.StopAttachSeconds",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerPosition,
                Evaluator = c => R(null, c.Config.StopGuard.StopAttachSeconds, 1)
            },
            new GuardRuleDefinition {
                Name = "Auto-stop attempts before escalation", ConfigPath = "StopGuard.MaxAutoStopAttempts",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerPosition,
                Evaluator = c => R(null, c.Config.StopGuard.MaxAutoStopAttempts, 1)
            },
            new GuardRuleDefinition {
                Name = "Auto-stop offsets", ConfigPath = "StopGuard.Offsets",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerPosition,
                // Empty map = every instrument falls back to the default. Worth SEEING.
                // Evidence is 1, not the map size: an instrument with no entry falls back to a
                // built-in default, so the guard still places the stop. INERT would be the wrong
                // reading -- it means "not protecting", and this always fires.
                Evaluator = c => R(null, null, 1,
                    "OPTIONAL tick overrides used when the guard places a stop itself; "
                    + (c.Config.StopGuard.Offsets == null ? 0 : c.Config.StopGuard.Offsets.Count)
                    + " configured, the rest use the basis-point rule below")
            },
            new GuardRuleDefinition {
                Name = "Auto-stop distance (bps)", ConfigPath = "StopGuard.StopDistanceBps",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerPosition,
                // The distance the guard places its own stop at, in basis points of the entry
                // price, for any instrument without an explicit Offsets override. Always fires
                // when AutoStop attaches a stop, so evidence is 1, not INERT.
                Evaluator = c => R(null, c.Config.StopGuard.StopDistanceBps, 1,
                    "AutoStop distance: ~" + c.Config.StopGuard.StopDistanceBps
                    + " bps of entry price on any instrument")
            },

            // -- instruments ------------------------------------------------------------
            // P2-163 / P1-168: these two are ONE question, and the pair is DEFAULT-DENY. The allow
            // list is checked second and the block list wins, so the block list stays the day-by-day
            // override. Both bind on the ORDER and on the POSITION -- the position half is what makes
            // them bind at all for a market order that fills instantly, which 17 of 99 orders on the
            // funded account did on 2026-08-19.
            new GuardRuleDefinition {
                Name = "Permitted instruments", ConfigPath = "AllowedInstruments",
                EvidenceLabel = "instruments on the permitted list",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerPosition,
                // An EMPTY allow list permits EVERYTHING -- the documented escape hatch -- so empty
                // is INERT here for the same reason an empty block list is, and for the opposite
                // mechanical reason. Saying so is the point: the two lists read alike and behave
                // oppositely when empty.
                Evaluator = c => R(null, null,
                    c.Config.AllowedInstruments == null ? 0 : c.Config.AllowedInstruments.Count,
                    "default-deny: an instrument absent from this list is refused on the order AND "
                    + "flattened as a position. An EMPTY list disables the rule and permits everything")
            },
            new GuardRuleDefinition {
                Name = "Blocked instruments", ConfigPath = "BlockedInstruments",
                EvidenceLabel = "instruments on the block list",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerPosition,
                // An EMPTY block list blocks nothing. INERT is the honest reading, not green.
                Evaluator = c => R(null, null,
                    c.Config.BlockedInstruments == null ? 0 : c.Config.BlockedInstruments.Count,
                    "checked BEFORE the permitted list and wins over it -- the day-by-day override. "
                    + "Enforced on the order AND the position since P1-168")
            },
            new GuardRuleDefinition {
                Name = "Per-instrument contract caps", ConfigPath = "InstrumentLimits",
                EvidenceLabel = "instruments with a configured cap",
                Source = GuardRuleSource.InstrumentLimit, Scope = GuardRuleScope.PerPosition,
                // P2-78: this type used to carry two more fields that nothing read, and the note
                // below warned about them. They are GONE, so the warning goes with them -- a note
                // describing fields the config no longer has is the same defect one turn later.
                // The note now states the positive fact, which stays true however the type changes:
                // there is exactly ONE way to block an instrument.
                //
                // ⚠️ `P1-159` MOVED THE SCOPE, AND THE SCOPE IS THE PART A READER ACTS ON. This
                // row said `PerOrder` for the life of the rule and it was true: the cap was checked
                // against `e.Order.Quantity` and nothing else, so N orders of 1 built a position of
                // N unopposed. It now ALSO binds on the position, through the resolved profile. The
                // stale half was read live off the funded account minutes after `v1.48.0` deployed --
                // this inventory is the surface that answers "is the guard actually protecting me",
                // so a scope here that lags the enforcement is the same defect class `P1-159` closed:
                // what a rule REPORTS disagreeing with what it DOES.
                Evaluator = c => R(null, null,
                    c.Config.InstrumentLimits == null ? 0 : c.Config.InstrumentLimits.Count,
                    "caps the size of an instrument on BOTH the order and the position; it does not "
                    + "block it -- use BlockedInstruments to block")
            },

            // -- trading windows --------------------------------------------------------
            new GuardRuleDefinition {
                Name = "Trading window gate", ConfigPath = "EnableWindowGate",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                // Evidence is 1 once the gate is on, because the GATE is the enforcement and it
                // acts whatever the list says. An empty list with the gate on is a real
                // misconfiguration, but INERT is the wrong word for it -- that reads as "not
                // protecting" when it may in fact permit nothing at all. Say so instead.
                Evaluator = c => !c.Config.EnableWindowGate
                    ? Off("window gate off; trading is not restricted to the windows below")
                    : R(null, null, 1, (c.Config.WindowsET == null || c.Config.WindowsET.Count == 0)
                        ? "WARNING: the gate is ON with NO windows configured -- check what this permits"
                        : c.Config.WindowsET.Count + " window(s) permitted")
            },
            new GuardRuleDefinition {
                Name = "Permitted trading windows (ET)", ConfigPath = "WindowsET",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                Evaluator = c => !c.Config.EnableWindowGate
                    ? Off("only consulted when EnableWindowGate is true")
                    : R(null, null, 1, (c.Config.WindowsET == null || c.Config.WindowsET.Count == 0)
                        ? "WARNING: no windows configured while the gate is ON"
                        : c.Config.WindowsET.Count + " window(s)")
            },

            // -- firm mirror ------------------------------------------------------------
            // Both rules resolve the account's firm PLAN before reading anything, because the
            // ENFORCER does: EvaluateFirmMirror calls ResolveEffectiveFirmConfig and flattens on
            // the resolved plan's numbers (P1-42). These evaluators used to read the TOP-LEVEL
            // block, and F-9's acceptance matrix caught them disagreeing with the enforcer in BOTH
            // directions on the shapes the four researched profiles actually use:
            //   reporter=Disabled  enforcer=FIRES   top-level off, the plan's rule on
            //   reporter=Enforcing enforcer=silent  top-level on, the plan's rule off
            // The second is the real Take Profit Trader profile, whose DailyLoss is OFF because TPT
            // has no daily loss limit -- so the inventory claimed a live rule that could not fire.
            //
            // WARNING: Evidence is 1 when THIS account has a non-empty entry in AccountFirmMap, 0
            // otherwise. NOT the map's SIZE -- these are PerAccount rules, and on the live box one
            // mapped account would have turned all 96 accounts' firm rules green. The firm rules
            // being "loaded but unmapped, so none can fire" is a state this system has already been
            // in (handover section 0), and an unmapped firm rule must read INERT rather than green
            // even though the top-level block would fire for it: a rule evaluating the guessed
            // top-level number is not firm protection (CONFIG_DEFAULTS R3).
            //
            // "Did it resolve" is asked the way the resolver asks it -- TryGetValue plus a null
            // check -- and not with ContainsKey. A dictionary holding a NULL profile answers
            // ContainsKey true while ResolveEffectiveFirmConfig falls back, which would have the
            // note claim a plan's numbers are in force when the top-level block's are.
            new GuardRuleDefinition {
                Name = "Firm trailing drawdown", ConfigPath = "FirmMirror.TrailingDD.Amount",
                EvidenceLabel = "accounts mapped to a firm and reporting an equity reading",
                Source = GuardRuleSource.FirmProfile, Scope = GuardRuleScope.PerAccount,
                Evaluator = c =>
                {
                    var fm = c.Config.FirmMirror;
                    if (fm == null || !fm.Enabled)
                        return Off("firm mirror is off, so no firm trailing drawdown is evaluated for any account");
                    string firmKey = null;
                    bool mapped = !string.IsNullOrEmpty(c.AccountName)
                        && fm.AccountFirmMap != null
                        && fm.AccountFirmMap.TryGetValue(c.AccountName, out firmKey)
                        && !string.IsNullOrEmpty(firmKey);
                    FirmProfile plan = null;
                    bool resolved = mapped && fm.FirmProfiles != null
                        && fm.FirmProfiles.TryGetValue(firmKey, out plan) && plan != null;
                    var eff = RiskGuardAddOn.ResolveEffectiveFirmConfig(fm, c.AccountName);
                    var sub = eff.TrailingDD;
                    if (sub == null || !sub.Enabled)
                        return Off(resolved
                            ? "plan '" + firmKey + "' does not set a trailing drawdown"
                            : "firm trailing drawdown not enabled");
                    string note = resolved
                        ? "resolved to plan '" + firmKey + "'; its TrailingDD numbers are in force"
                        : mapped
                            ? "mapped to firm '" + firmKey + "', which is ABSENT from FirmProfiles; preflight refuses to arm on that, and the top-level TrailingDD block is what is in force"
                            : "not mapped to a firm plan; the top-level TrailingDD block is what is in force, and it was chosen for no stated account size";
                    // P2-116. A SECOND READER of the same state: this already gated evidence
                    // on the account being MAPPED to a firm, which a dormant eval certainly can
                    // be. Mapped and unread is still unread. The existing note is PREFIXED, not
                    // replaced -- it is the only place that says whether the numbers in force
                    // came from the resolved plan or the fallback block.
                    if (mapped && !HasEquityReading(c.Account))
                        note = NoEquityReading + "; " + note;
                    return R(HasEquityReading(c.Account) ? (double?)c.Account.AccountEquity : null,
                        sub.Amount, mapped && HasEquityReading(c.Account) ? 1 : 0, note);
                }
            },
            new GuardRuleDefinition {
                Name = "Firm daily loss", ConfigPath = "FirmMirror.DailyLoss.Amount",
                EvidenceLabel = "accounts mapped to a firm",
                Source = GuardRuleSource.FirmProfile, Scope = GuardRuleScope.PerAccount,
                Evaluator = c =>
                {
                    var fm = c.Config.FirmMirror;
                    if (fm == null || !fm.Enabled)
                        return Off("firm mirror is off, so no firm daily loss is evaluated for any account");
                    string firmKey = null;
                    bool mapped = !string.IsNullOrEmpty(c.AccountName)
                        && fm.AccountFirmMap != null
                        && fm.AccountFirmMap.TryGetValue(c.AccountName, out firmKey)
                        && !string.IsNullOrEmpty(firmKey);
                    FirmProfile plan = null;
                    bool resolved = mapped && fm.FirmProfiles != null
                        && fm.FirmProfiles.TryGetValue(firmKey, out plan) && plan != null;
                    var eff = RiskGuardAddOn.ResolveEffectiveFirmConfig(fm, c.AccountName);
                    var sub = eff.DailyLoss;
                    if (sub == null || !sub.Enabled)
                        return Off(resolved
                            ? "plan '" + firmKey + "' has NO daily loss limit, which is that firm's actual rule -- not an oversight"
                            : "firm daily loss not enabled");
                    string note = resolved
                        ? "resolved to plan '" + firmKey + "'; its DailyLoss numbers are in force"
                        : mapped
                            ? "mapped to firm '" + firmKey + "', which is ABSENT from FirmProfiles; preflight refuses to arm on that, and the top-level DailyLoss block is what is in force"
                            : "not mapped to a firm plan; the top-level DailyLoss block is what is in force, and it was chosen for no stated account size";
                    return R(c.Account == null ? (double?)null : c.Account.RealizedPnL,
                        -Math.Abs(sub.Amount), mapped ? 1 : 0, note);
                }
            },

            // -- prop-firm suite: the ones that DO work ---------------------------------
            new GuardRuleDefinition {
                Name = "Profit target lock", ConfigPath = "PropFirm.EnableProfitTargetLock",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => c.PropConfig == null || !c.PropConfig.EnableProfitTargetLock
                    ? Off("profit target lock disabled")
                    : R(c.Account == null ? (double?)null : c.Account.RealizedPnL,
                        c.PropConfig.EvaluationTargetProfit, c.Account == null ? 0 : 1)
            },
            new GuardRuleDefinition {
                Name = "Peak equity giveback", ConfigPath = "PropFirm.EnablePeakEquityProtection",
                EvidenceLabel = "accounts reporting an equity reading",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                // P2-116, THIRD SITE. It reports no CurrentValue, so it looks unlike the two
                // above -- but the enforcer behind it tracks peak equity, and with no reading the
                // peak stays 0 and the giveback can never trigger. What a row DISPLAYS is not
                // what decides whether it can fire.
                //
                // ⚠️ CurrentValue stays NULL deliberately. The Limit here is a PERCENT; putting
                // the account equity in the value column would render dollars against a percent
                // and read as wildly over the limit.
                Evaluator = c => c.PropConfig == null || !c.PropConfig.EnablePeakEquityProtection
                    ? Off("peak equity protection disabled")
                    : R(null, c.PropConfig.MaxPeakGivebackPct, HasEquityReading(c.Account) ? 1 : 0,
                        (HasEquityReading(c.Account) ? "" : NoEquityReading + "; ")
                        + "ignores peaks below $" + c.PropConfig.MinPeakGainDollars + " (P1-40)")
            },

            // -- prop-firm suite: THE NEWS SHIELD. P2-25, and the reason for INERT. ----
            new GuardRuleDefinition {
                Name = "News shield", ConfigPath = "PropFirm.EnableNewsShield",
                EvidenceLabel = "news events loaded",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                // Wired end to end since P2-25: RiskGuardAddOn.cs tests the flag and calls
                // IsInNewsWindow, which iterates _newsEvents, which LoadNewsEventsFromDisk fills
                // from LocalNewsEventsFilePath. Evidence is the EVENT COUNT, so this reports
                // INERT while that list is empty -- which is a real state and not a defect.
                //
                // ⚠️ P2-113: the zero-event note below used to assert that nothing ever opens the
                // file. Something does. What the operator needs at zero events is not a verdict
                // on the codebase but the reason THEIR list is empty, so the note now defers to
                // the load status and to the row above, which reports it.
                //
                // General rule: Disabled means "this would work if you turned it on". A rule
                // with nothing to evaluate does not qualify, however its switch is set, so the
                // zero-event reading must come from the evidence branch and report INERT.
                Evaluator = c => c.PropConfig == null
                    ? Off("news shield disabled")
                    : c.NewsEventCount == 0
                        ? R(null, null, 0,
                            "NO NEWS EVENTS ARE LOADED, so this cannot fire. "
                            + (c.NewsEventsLoadStatus ?? "the load outcome was not reported to "
                                + "this snapshot")
                            + " -- see the 'News events file' row")
                        : !c.PropConfig.EnableNewsShield
                            ? Off("news shield disabled")
                            : R(null, null, c.NewsEventCount, null)
            },

            // -- prop-firm suite: the ones with NO evaluator. Each is a finding. --------
            // P1-77: these two were the top of the "NO evaluator" block for the life of the
            // addon -- configured, enabled by default, and evaluated NOWHERE. They now have a
            // real evaluator (PropFirmProtectionSuite.EvaluateConsistencyCap) and move up here.
            // ⚠️ The evidence count is 0 when there is no evaluation target, which is what makes
            // the rule report INERT rather than Enforcing on the ~90 accounts that have none --
            // 35% of a zero target is zero, and a cap of zero breaches on any profit at all.
            new GuardRuleDefinition {
                Name = "Consistency / daily-profit cap", ConfigPath = "PropFirm.EnableConsistencyCap",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                Evaluator = c => c.PropConfig == null || !c.PropConfig.EnableConsistencyCap
                    ? Off("consistency cap disabled")
                    : R(c.Account == null ? (double?)null : c.Account.RealizedPnL,
                        c.PropConfig.EvaluationTargetProfit > 0
                            ? c.PropConfig.EvaluationTargetProfit * c.PropConfig.MaxDailyProfitPctOfTarget
                            : (double?)null,
                        (c.Account != null && c.PropConfig.EvaluationTargetProfit > 0) ? 1 : 0,
                        c.PropConfig.EvaluationTargetProfit > 0
                            ? "refuses new ENTRIES only -- flattening a winner would realise the "
                              + "very P&L the cap is about (P1-77)"
                            : "no EvaluationTargetProfit set, so the cap cannot be computed and "
                              + "does not fire (P1-77)")
            },
            new GuardRuleDefinition {
                Name = "Consistency cap threshold", ConfigPath = "PropFirm.MaxDailyProfitPctOfTarget",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                Evaluator = c => c.PropConfig == null || !c.PropConfig.EnableConsistencyCap
                    ? Off("consistency cap disabled")
                    : R(c.PropConfig.MaxDailyProfitPctOfTarget, null,
                        c.PropConfig.EvaluationTargetProfit > 0 ? 1 : 0,
                        "share of EvaluationTargetProfit allowed in one session")
            },
            new GuardRuleDefinition {
                Name = "News events file", ConfigPath = "PropFirm.LocalNewsEventsFilePath",
                // ⚠️ Deliberately NO EvidenceLabel. A label declares "this rule's evidence count
                // moves with a collection in RiskConfig", and a test drives every labelled rule
                // by emptying those collections. This rule's evidence comes from the prop suite's
                // loaded event list, which that test cannot move -- so a label here would make it
                // report a state the test never actually produced. The shield below carries the
                // label for the same count, once, which is where it belongs.
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                // P2-113. This entry carried an UnevaluatedReason reading "NO CODE READS THIS ...
                // the path is stored but nothing ever opens it". That was true when written and
                // has been FALSE since P2-25 closed: LoadNewsEventsFromDisk opens it, from
                // UpdateConfig, which the bridge calls at startup. So the last remaining
                // CONFIGURED-and-not-EVALUATED row on the live box -- 97 accounts, every poll --
                // was itself the lie this registry exists to prevent. F-9's class exactly: the
                // reporter disagreeing with the enforcer, this time in the pessimistic direction,
                // which is not the harmless one. A red row that is wrong teaches an operator to
                // discount red rows.
                //
                // What it reports now is the thing nobody could see: WHETHER THE FILE ACTUALLY
                // LOADED. Every failure in that loader is silent -- a missing path, an unparseable
                // file and a file containing `[]` all end with an empty list -- so this row is the
                // only surface on which "I configured a news file" and "my news file loaded" can
                // be told apart.
                Evaluator = c => c.PropConfig == null
                        || string.IsNullOrEmpty(c.PropConfig.LocalNewsEventsFilePath)
                    ? Off("no news events file configured")
                    : R(null, null, c.NewsEventCount,
                        c.NewsEventsLoadStatus ?? "the load outcome was not reported to this snapshot")
            },
            // P1-81: the "Prop suite armed" entry was HERE and is gone with the field it
            // advertised. It reported `PropFirm.ArmedForLive` as a ConfiguredNotEvaluated rule
            // against all 96 accounts on every inventory poll -- correctly, because the switch
            // did nothing. The remedy was to delete the switch rather than wire it up: this
            // system should have ONE arming answer and the guard's own mode is it. A second flag
            // the prop rules must ALSO satisfy creates a state where the operator has armed the
            // guard, believes the prop rules are live, and a separate switch silently holds them
            // off -- P3-34's defect inverted.
        };

        private static readonly List<GuardNonRule> _nonRules = new List<GuardNonRule>
        {
            // Not limits. Each one is machinery, an identity, or the CONSEQUENCE of a breach --
            // and a consequence is not a rule, because it has nothing to be compared against.
            new GuardNonRule { ConfigPath = "Mode", Reason = "the guard's enforcement mode; it decides whether rules can ACT and is reported on the snapshot itself, not as a rule" },
            new GuardNonRule { ConfigPath = "Profiles", Reason = "per-account overrides; each profile supplies VALUES for the rules above rather than being a rule" },
            new GuardNonRule { ConfigPath = "ExcludedAccounts", Reason = "scoping, not a limit -- an excluded account reports EvaluatedNotEnforcing on every rule" },
            new GuardNonRule { ConfigPath = "LockoutBypassWhileDisarmedAccounts", Reason = "scoping for lockout persistence while disarmed" },
            new GuardNonRule { ConfigPath = "MinShadowSessions", Reason = "an arming PRECONDITION (FR-29), not a trading limit" },
            // P0-171 second attempt. Not a limit: it is how long after a connection transition
            // the duplicate-entry rule stays SUPPRESSED, because NT8 replays the session in that
            // window. Listed here rather than as a rule because raising it does not tighten
            // anything -- it widens a blind spot, and the reason it is not derived from
            // DuplicateEntryWindowMs is that doing so is the bug this replaced: measured on two
            // reconnects, the replay lands 1167ms and 2027ms after Connecting, so a 1000ms
            // suppression covers neither.
            new GuardNonRule { ConfigPath = "Overtrading.ReconnectReplayGraceMs", Reason = "how long the duplicate-entry rule is suppressed after a connection transition, because NT8 replays the session then; widening it widens a blind spot rather than tightening a limit" },
            // P0-166: this key now governs NOTHING. Both rules that read it -- DAILY_LOSS_BREACH
            // and TRAILING_DD_BREACH -- trigger on session-scoped counters that only SESSION_RESET
            // clears, so both lock to the session boundary instead. Saying so here is the point: a
            // key that quietly stops meaning anything reads exactly like a protection that is set.
            new GuardNonRule { ConfigPath = "PnLRules.LockoutMinutes", Reason = "DEAD since P0-166 -- both P&L rails now lock to the session boundary, which is the only thing that can clear their trigger" },
            // P0-166: still live, but for FEWER rules than it reads like. MAX_TRADES_BREACH moved to
            // the session boundary with the P&L rails; CONSECUTIVE_LOSS_BREACH and
            // ORDER_FLOOD_LOCKOUT still use it, because a cool-off and a rate burst are genuinely
            // cured by waiting.
            new GuardNonRule { ConfigPath = "Overtrading.LockoutMinutes", Reason = "the cool-off for CONSECUTIVE_LOSS_BREACH and ORDER_FLOOD_LOCKOUT only -- since P0-166 MAX_TRADES_BREACH locks to the session boundary instead" },
            new GuardNonRule { ConfigPath = "Overtrading.CooldownMinutes", Reason = "the consequence of a loss streak -- since P2-161 the BASE of the escalating cool-off (base * 2^(n-1))" },
            new GuardNonRule { ConfigPath = "Overtrading.LossFloorDollars", Reason = "P2-164: the magnitude a net loss must clear to count toward the streak/cooldown; an input to CONSECUTIVE_LOSS_BREACH, not a limit of its own. Default 0 = every negative counts" },
            new GuardNonRule { ConfigPath = "Sizing.ExpectedCopies", Reason = "a divisor used when sizing across copied accounts; not a cap" },
            new GuardNonRule { ConfigPath = "Override.ConfirmPhrase", Reason = "friction for escaping a lockout (FR-35/36)" },
            new GuardNonRule { ConfigPath = "Override.WaitSeconds", Reason = "friction for escaping a lockout; clamped to >= 30 at validation" },
            new GuardNonRule { ConfigPath = "FirmMirror.Enabled", Reason = "the master switch for the two firm rules above; reported through their Disabled state" },
            new GuardNonRule { ConfigPath = "FirmMirror.AccountFirmMap", Reason = "which firm an account belongs to; it is the EVIDENCE COUNT for both firm rules" },
            new GuardNonRule { ConfigPath = "FirmMirror.FirmProfiles", Reason = "the per-firm value tables the two firm rules resolve against" },
            new GuardNonRule { ConfigPath = "FirmMirror.ResolvedAccountSize", Reason = "P2-95: transient carrier populated by ResolveEffectiveFirmConfig from FirmProfile.AccountSize; not serialized, not user-configured" },
            new GuardNonRule { ConfigPath = "AuditIntervalSeconds", Reason = "P3-30: the period of the guard-side audit timer; not a rule, it is the clock the audit runs on" },
            new GuardNonRule { ConfigPath = "Alerts.Enabled", Reason = "F-6: whether decided alerts are written to the outbox for the relay to deliver. It gates NOTIFICATION only -- it can never stop a rule evaluating, locking out or flattening, and a reader must not mistake it for one" },
            new GuardNonRule { ConfigPath = "Alerts.MinSeverity", Reason = "F-6: the severity floor for the push outbox. Not a trading limit; an unrecognised value falls back to 'warning' rather than to the lowest rank, because rank 0 would push the entire audit stream" },
            new GuardNonRule { ConfigPath = "FirmMirror.DailyResetHourUtc", Reason = "the session boundary the firm rules reset on" },
            new GuardNonRule { ConfigPath = "FirmMirror.DailyResetMinuteUtc", Reason = "the session boundary the firm rules reset on" },
            new GuardNonRule { ConfigPath = "FirmMirror.TrailingDD.Enabled", Reason = "reported through the firm trailing-drawdown rule's Disabled state" },
            new GuardNonRule { ConfigPath = "FirmMirror.TrailingDD.Type", Reason = "intraday vs EOD; shapes the firm trailing rule's calculation" },
            new GuardNonRule { ConfigPath = "FirmMirror.TrailingDD.IncludesUnrealized", Reason = "shapes the firm trailing rule's calculation" },
            new GuardNonRule { ConfigPath = "FirmMirror.TrailingDD.Buffer", Reason = "safety margin inside the firm trailing rule" },
            new GuardNonRule { ConfigPath = "FirmMirror.TrailingDD.LockAtProfit", Reason = "the profit at which a firm trailing drawdown stops trailing" },
            new GuardNonRule { ConfigPath = "FirmMirror.DailyLoss.Enabled", Reason = "reported through the firm daily-loss rule's Disabled state" },
            new GuardNonRule { ConfigPath = "FirmMirror.DailyLoss.Basis", Reason = "realized vs total; shapes the firm daily-loss calculation" },
            new GuardNonRule { ConfigPath = "FirmMirror.DailyLoss.Buffer", Reason = "safety margin inside the firm daily-loss rule" },
            new GuardNonRule { ConfigPath = "PropFirm.EvaluationTargetProfit", Reason = "the target the profit-target lock compares against" },
            new GuardNonRule { ConfigPath = "PropFirm.MaxPeakGivebackPct", Reason = "the threshold the peak-equity rule compares against" },
            new GuardNonRule { ConfigPath = "PropFirm.MinPeakGainDollars", Reason = "P1-40's absolute floor inside the peak-equity rule" },
            new GuardNonRule { ConfigPath = "PropFirm.NewsBufferMinutesBefore", Reason = "the window the news shield uses; inert for the same reason it is" },
            new GuardNonRule { ConfigPath = "PropFirm.NewsBufferMinutesAfter", Reason = "the window the news shield uses; inert for the same reason it is" },
        };

        public static IList<GuardRuleDefinition> Rules { get { return _rules.AsReadOnly(); } }

        /// <summary>
        /// P2-113. The requirement that a rule declared WITHOUT an evaluator states why, as a
        /// predicate rather than as a loop inside one test.
        ///
        /// It is extracted because the population it used to scan is now EMPTY -- every rule has
        /// an evaluator -- and `All` over an empty sequence is true, so the gate that enforced
        /// this became unfalsifiable at the moment the last instance was fixed. A predicate can
        /// be driven with a synthetic rule in both directions and keeps proving something at zero
        /// instances, which is when it matters: the next rule declared without an evaluator is
        /// exactly the case nobody is watching for.
        /// </summary>
        public static bool RuleExplainsItself(GuardRuleDefinition def)
        {
            if (def == null) return false;
            if (def.Evaluator != null) return true;
            return !string.IsNullOrWhiteSpace(def.UnevaluatedReason);
        }

        public static IList<GuardNonRule> NonRules { get { return _nonRules.AsReadOnly(); } }

        /// <summary>
        /// Turns one definition plus one reading into a state. The whole vocabulary lives here
        /// and nowhere else, so it cannot drift between rules.
        ///
        /// ⚠️ ORDER IS THE DESIGN. No evaluator outranks everything, because a rule nothing reads
        /// cannot act however armed the guard is -- reporting such a rule as "Enforcing" because
        /// the mode says `armed` is exactly the lie P1-77 tells today. INERT outranks the
        /// enforcing checks for the same reason.
        /// </summary>
        public static GuardRuleState DeriveState(
            GuardRuleDefinition def, GuardRuleReading reading, bool guardCanAct, bool accountExcluded)
        {
            if (def == null || def.Evaluator == null) return GuardRuleState.ConfiguredNotEvaluated;
            if (reading == null) return GuardRuleState.ConfiguredNotEvaluated;
            if (reading.DisabledByConfig) return GuardRuleState.Disabled;
            if (reading.EvidenceCount <= 0) return GuardRuleState.Inert;
            if (!guardCanAct || accountExcluded) return GuardRuleState.EvaluatedNotEnforcing;
            return GuardRuleState.Enforcing;
        }

        /// <summary>
        /// Whether the guard can ACT, from the two things that decide it.
        ///
        /// ⚠️ This duplicates `RiskGuardAddOn.IsActingMode()` plus its arming check, and a
        /// duplicated rule is exactly the shape of `P?-64`. It is duplicated deliberately, so the
        /// registry stays host-agnostic -- and a test compares this against the real guard across
        /// every valid mode, so the copy cannot drift in silence. If that test is ever deleted,
        /// delete this method with it and take `guardCanAct` as a parameter instead.
        /// </summary>
        public static bool CanAct(string mode, bool isArmed)
        {
            return mode == "live" && isArmed;
        }

        /// <summary>
        /// The whole inventory, for every account, as one value.
        ///
        /// Host-agnostic on purpose: it takes config and state rather than reaching for an engine,
        /// so the suite can build the exact situations that matter (shadow, disarmed, excluded, no
        /// accounts, no news events) without an NT8 in the room.
        /// </summary>
        public static GuardSnapshot BuildSnapshot(
            RiskConfig config,
            PropFirmProtectionConfig propConfig,
            string mode,
            bool isArmed,
            IList<RiskGuardAddOn.AccountStateSnapshot> accounts,
            int newsEventCount,
            // P2-113. Optional so the ~40 existing test call sites keep compiling; null means
            // "the caller did not say", which the rule reports as exactly that rather than as
            // a healthy reading. It is NOT a default that stands in for a good outcome.
            string newsEventsLoadStatus = null,
            // P2-113. The registry to inventory, defaulting to the real one. Production never
            // passes it. It exists because P2-113 emptied the set of rules with no evaluator --
            // which is the goal -- and SIX tests of the unevaluated-rule machinery were written
            // to scan that set, so all six became unfalsifiable in the same commit that earned
            // it. The machinery still has to work for the next rule declared without an
            // evaluator, and the only way to keep proving that at zero real instances is to hand
            // it a synthetic one. A seam for a test is cheaper than six gates that cannot fail.
            IList<GuardRuleDefinition> rules = null)
        {
            var snapshot = new GuardSnapshot();
            snapshot.TakenUtc = DateTime.UtcNow;
            snapshot.Mode = mode;
            snapshot.IsArmed = isArmed;
            snapshot.Accounts = new List<GuardAccountRules>();
            snapshot.UnevaluatedRules = new List<GuardRuleRow>();

            bool canAct = CanAct(mode, isArmed);

            // A null account list is the SAME situation as an empty one, and it must not throw.
            // The reason is the reason UnevaluatedRules exists: an exception escaping here blanks
            // the inventory, and a blank page reads as calm. `GetAccountSnapshots()` never returns
            // null today, so this is the one caller-shaped hazard rather than a live one -- it is
            // guarded because the cost is a line and the failure is silent.
            if (accounts == null) accounts = new List<RiskGuardAddOn.AccountStateSnapshot>();

            // P2-113: the real registry unless a caller names another. See the parameter's note.
            if (rules == null) rules = Rules;

            foreach (var account in accounts)
            {
                var accountRules = new GuardAccountRules();
                accountRules.AccountName = account.AccountName;
                accountRules.IsExcluded = account.IsExcluded;
                accountRules.IsLockedOut = account.IsLockedOut;
                accountRules.AccountEquity = account.AccountEquity;
                accountRules.TradesToday = account.TradesToday;
                // F-15: the blocked-reason channel from CanTrade.
                accountRules.BlockedReason = account.BlockedReason;
                accountRules.Rules = new List<GuardRuleRow>();
                snapshot.Accounts.Add(accountRules);
            }

            foreach (var def in rules)
            {
                if (def == null)
                    continue;

                if (def.Evaluator == null)
                {
                    var unevaluatedRow = new GuardRuleRow();
                    unevaluatedRow.Name = def.Name;
                    unevaluatedRow.ConfigPath = def.ConfigPath;
                    unevaluatedRow.Source = def.Source;
                    unevaluatedRow.Scope = def.Scope;
                    unevaluatedRow.State = GuardRuleState.ConfiguredNotEvaluated;
                    unevaluatedRow.CurrentValue = null;
                    unevaluatedRow.Limit = null;
                    unevaluatedRow.EvidenceCount = 0;
                    unevaluatedRow.Note = def.UnevaluatedReason;
                    snapshot.UnevaluatedRules.Add(unevaluatedRow);

                    for (int i = 0; i < accounts.Count; i++)
                    {
                        var accountRules = snapshot.Accounts[i];
                        var row = new GuardRuleRow();
                        row.Name = def.Name;
                        row.ConfigPath = def.ConfigPath;
                        row.Source = def.Source;
                        row.Scope = def.Scope;
                        row.State = GuardRuleState.ConfiguredNotEvaluated;
                        row.CurrentValue = null;
                        row.Limit = null;
                        row.EvidenceCount = 0;
                        row.Note = def.UnevaluatedReason;
                        accountRules.Rules.Add(row);
                    }
                }
                else
                {
                    for (int i = 0; i < accounts.Count; i++)
                    {
                        var account = accounts[i];
                        var accountRules = snapshot.Accounts[i];
                        GuardRuleReading reading = null;
                        string failureNote = null;

                        try
                        {
                            var context = new GuardRuleContext();
                            context.AccountName = account.AccountName;
                            context.Config = config;
                            context.PropConfig = propConfig;
                            context.Account = account;
                            context.AllAccounts = new List<RiskGuardAddOn.AccountStateSnapshot>(accounts);
                            context.NewsEventCount = newsEventCount;
                            context.NewsEventsLoadStatus = newsEventsLoadStatus;
                            reading = def.Evaluator(context);
                        }
                        catch (Exception ex)
                        {
                            failureNote = ex.GetType().Name + ": " + ex.Message;
                        }

                        var row = new GuardRuleRow();
                        row.Name = def.Name;
                        row.ConfigPath = def.ConfigPath;
                        row.Source = def.Source;
                        row.Scope = def.Scope;

                        if (reading != null)
                        {
                            row.CurrentValue = reading.CurrentValue;
                            row.Limit = reading.Limit;
                            row.EvidenceCount = reading.EvidenceCount;
                            row.Note = reading.Note;
                            row.Breached = reading.Breached;
                            row.LastFiredUtc = reading.LastFiredUtc;
                        }
                        else
                        {
                            row.CurrentValue = null;
                            row.Limit = null;
                            row.EvidenceCount = 0;
                            // A RED ROW MUST SAY WHY, and here it always can: `failureNote` is
                            // set whenever the evaluator threw, and an evaluator MAY NOT return
                            // null -- that is a contract a test enforces over every rule, rather
                            // than a fallback here. A third `??` branch was written first and a
                            // mutant deleting it survived, because nothing could reach it.
                            row.Note = failureNote ?? def.UnevaluatedReason;
                        }

                        row.State = DeriveState(def, reading, canAct, account.IsExcluded);
                        accountRules.Rules.Add(row);
                    }
                }
            }

            return snapshot;
        }
    }

    /// <summary>
    /// How a GuardSnapshot becomes JSON for the browser UI.
    ///
    /// ⚠️ THIS LIVES IN CORE ON PURPOSE. The obvious home is the bridge route, one line of
    /// `JsonConvert.SerializeObject`. But `McpBridgeAddOn.cs` is excluded from the test build
    /// (`P2-27`), so anything put there is unverifiable by construction -- and the serialization
    /// is not a detail. Three of its properties are load-bearing, and each has already been the
    /// shape of a defect in this codebase:
    ///
    ///   * ENUMS AS NAMES. `"state": 1` forces the page to hardcode the enum's integer order --
    ///     an order UI3's battery pins for a completely different reason (worst-sorts-first), so
    ///     the two would be silently coupled and a reordering would relabel every row.
    ///   * NULLS PRESERVED. `NullValueHandling.Ignore` drops `"limit": null`, and a page reading
    ///     `row.limit ?? 0` then renders a limit of ZERO for a rule that has none. That is UI1's
    ///     copier-metrics defect exactly: a bare 0 that means "not applicable".
    ///   * EMPTY LISTS PRESENT. `unevaluatedRules` missing and `unevaluatedRules: []` mean
    ///     opposite things, and the whole point of `P2-83` is that they must not look the same.
    /// </summary>
    public static class GuardSnapshotJson
    {
        /// <summary>
        /// The ONE settings object for everything this UI is served. `CopierSnapshotJson` uses it
        /// too, deliberately: two payloads rendered by one page must not disagree about whether an
        /// enum is a name or a number, or whether a null survives. Two settings objects would be
        /// two owners of one fact.
        /// </summary>
        internal static readonly JsonSerializerSettings UiJsonSettings = new JsonSerializerSettings
        {
            // camelCase because the only consumer is JavaScript, and the page's field names are
            // then the same characters as these ones.
            //
            // ⚠️ ProcessDictionaryKeys = FALSE, and this is not a style choice. The fleet summary
            // is keyed BY STATE NAME (`{"Inert": 3}`), and those keys are the same strings the
            // detail view carries as enum VALUES. `CamelCasePropertyNamesContractResolver` -- the
            // obvious thing to write here -- camel-cases dictionary keys as well, so the fleet
            // would say `inert` while the rows said `Inert`, and the page would need to know
            // which of the two it was looking at. Caught by the test that recomputes the fleet
            // counts from the detail rows; it would otherwise have been found in the browser.
            ContractResolver = new DefaultContractResolver
            {
                NamingStrategy = new CamelCaseNamingStrategy { ProcessDictionaryKeys = false }
            },

            // ⚠️ NOT `Ignore`. Dropping `"limit": null` is what turns "this rule has no numeric
            // limit" into a page rendering `0`, because `row.limit ?? 0` cannot tell an absent
            // key from an absent value.
            NullValueHandling = NullValueHandling.Include,

            // Names, not integers. See the class remarks.
            Converters = { new StringEnumConverter() },

            // A human hitting this endpoint in a browser is the first debugging tool anyone will
            // reach for; on localhost the bytes do not matter.
            Formatting = Formatting.Indented
        };

        /// <summary>
        /// The fleet view: every account, with a COUNT per state instead of its rules.
        ///
        /// ⚠️ THIS EXISTS BECAUSE OF A MEASUREMENT, NOT A HUNCH. The first live read of the real
        /// box returned **96 accounts x 25 rules = 2400 rows and 648 KB**, and the page polls. A
        /// 2400-row wall is not an inventory an operator can read, and re-fetching it every few
        /// seconds to render a summary is worse than pointless.
        ///
        /// The counts are DERIVED from the same rows the detail view shows, so the fleet and the
        /// inspector cannot disagree -- which is the failure this whole design exists to prevent,
        /// one level up: a summary maintained separately from what it summarises is exactly the
        /// hand-maintained table §6a forbids.
        /// </summary>
        public static string ToSummaryJson(GuardSnapshot snapshot)
        {
            if (snapshot == null) return ToJson(null);

            var accounts = new List<object>();
            foreach (var acct in snapshot.Accounts ?? new List<GuardAccountRules>())
            {
                var counts = new Dictionary<string, int>();
                GuardRuleState? worst = null;
                foreach (var row in acct.Rules ?? new List<GuardRuleRow>())
                {
                    string key = row.State.ToString();
                    counts[key] = counts.ContainsKey(key) ? counts[key] + 1 : 1;

                    // "Worst" is the LOWEST enum value, because the enum is ordered worst-first
                    // and a test pins that. Deriving it here rather than listing the states in
                    // priority order means a state added later cannot be silently left out of
                    // the ranking.
                    if (worst == null || (int)row.State < (int)worst.Value) worst = row.State;
                }

                accounts.Add(new
                {
                    accountName = acct.AccountName,
                    isExcluded = acct.IsExcluded,
                    isLockedOut = acct.IsLockedOut,
                    accountEquity = acct.AccountEquity,
                    tradesToday = acct.TradesToday,
                    blockedReason = acct.BlockedReason,
                    ruleCount = acct.Rules == null ? 0 : acct.Rules.Count,
                    worst = worst == null ? null : worst.Value.ToString(),
                    counts = counts
                });
            }

            return JsonConvert.SerializeObject(new
            {
                takenUtc = snapshot.TakenUtc,
                mode = snapshot.Mode,
                isArmed = snapshot.IsArmed,
                accounts = accounts,
                // Still carried in the summary. They are the rules nothing evaluates, they are the
                // reason P2-83 exists, and an operator who only ever opens the fleet view must
                // still see them.
                unevaluatedRules = snapshot.UnevaluatedRules
            }, UiJsonSettings);
        }

        public static string ToJson(GuardSnapshot snapshot)
        {
            // The route can only be handed null when the guard is not loaded. Serving the four
            // characters `null` leaves the page with nothing to render and nothing to say, so the
            // operator gets a blank screen -- which is `P2-83` reached by a third route. Say it.
            if (snapshot == null)
            {
                return JsonConvert.SerializeObject(
                    new { error = "the RiskGuard add-on is not loaded, so no rule inventory exists to report" },
                    UiJsonSettings);
            }

            return JsonConvert.SerializeObject(snapshot, UiJsonSettings);
        }
    }


    /// <summary>
    /// How a CopierSnapshot becomes JSON for the browser UI.
    ///
    /// Shares GuardSnapshotJson's settings for the same reasons (enum NAMES, nulls PRESERVED,
    /// empty lists PRESENT) and adds the one thing the copier needs that the guard does not:
    /// a SEVERITY RANK.
    ///
    /// ⚠️ `CopierConformance`'s own integer order is NOT severity order. It reads
    /// `Idle=0, Match=1, Shadow=2, Diverged=3, Orphan=4, Quarantined=5`, so a surface that sorted
    /// by the enum value would put a healthy Idle row FIRST and an ORPHAN -- the leader is flat
    /// and the follower is still holding a live position nobody is managing -- BELOW a quarantined
    /// one. That is the single most dangerous row this system can produce, sorted into the middle.
    ///
    /// So the rank is stated here, once, and travels on the row. The page sorts by a number it is
    /// given rather than re-deriving an order, which is the same reason the guard's four states
    /// are derived in one place: an ordering duplicated into JavaScript is an ordering that drifts.
    /// </summary>
    public static class CopierSnapshotJson
    {
        /// <summary>
        /// 0 is WORST. Every enum member must appear; a test asserts completeness AND that this
        /// disagrees with casting the enum, so sorting by the cast is a visible defect rather
        /// than an equivalent shortcut.
        /// </summary>
        public static int SeverityRank(CopierConformance verdict)
        {
            switch (verdict)
            {
                // The leader is FLAT and the follower is not. Somebody is holding a live position
                // that nothing is managing and nothing will close. Worst row this system emits.
                case CopierConformance.Orphan:      return 0;

                // Both non-flat and they disagree on side or size.
                case CopierConformance.Diverged:    return 1;

                // Not copying at all. A known state rather than a surprise, but it means the
                // follower is drifting from the leader for as long as it lasts.
                case CopierConformance.Quarantined: return 2;

                // Configured and will not act. Not a fault -- but it is the state most often
                // mistaken for working, so it ranks above the two that ARE working.
                case CopierConformance.Shadow:      return 3;

                case CopierConformance.Match:       return 4;
                case CopierConformance.Idle:        return 5;
            }

            // A value added to the enum and not to this switch. Rank it WORST rather than best:
            // an unrecognised verdict is not evidence of health, and putting it at the top is how
            // it gets noticed. The completeness test fails first, which is the real defence.
            return 0;
        }

        public static string ToJson(CopierSnapshot snapshot)
        {
            if (snapshot == null)
            {
                return JsonConvert.SerializeObject(
                    new { error = "the trade copier is not loaded, so no relationships can be reported" },
                    GuardSnapshotJson.UiJsonSettings);
            }

            // The rank travels ON each row so the page sorts by a number it was given. An
            // ordering duplicated into JavaScript is an ordering that drifts from this one.
            var rows = new List<object>();
            foreach (var r in snapshot.Rows ?? new List<CopierSnapshotRow>())
            {
                rows.Add(new
                {
                    relationshipId = r.RelationshipId,
                    leaderAccountName = r.LeaderAccountName,
                    followerAccountName = r.FollowerAccountName,
                    groupName = r.GroupName,
                    instrumentFullName = r.InstrumentFullName,
                    sizingMode = r.SizingMode,
                    effectiveRatio = r.EffectiveRatio,
                    isEnabled = r.IsEnabled,
                    armedForLive = r.ArmedForLive,
                    isQuarantined = r.IsQuarantined,
                    quarantineReason = r.QuarantineReason,
                    maxPositionSize = r.MaxPositionSize,
                    autoSymbolConversion = r.AutoSymbolConversion,
                    maxSlippageTicks = r.MaxSlippageTicks,
                    perTickerRatioLines = r.PerTickerRatioLines,
                    symbolMappingLines = r.SymbolMappingLines,
                    leaderSide = r.LeaderSide,
                    leaderQuantity = r.LeaderQuantity,
                    expectedSide = r.ExpectedSide,
                    expectedQuantity = r.ExpectedQuantity,
                    expectedIsClamped = r.ExpectedIsClamped,
                    actualSide = r.ActualSide,
                    actualQuantity = r.ActualQuantity,
                    // `Measured` is a computed getter on CopierMetric and serializes with the
                    // value. That pair is the whole of P1-22: these metrics are session-scoped, so
                    // a bare 0 cannot tell "no copy has filled yet" from "a copy filled and was
                    // perfect", and that confusion was once misdiagnosed as a broken measurement.
                    latency = r.Latency,
                    slippage = r.Slippage,
                    verdict = r.Verdict,
                    severity = SeverityRank(r.Verdict)
                });
            }

            return JsonConvert.SerializeObject(new
            {
                takenUtc = snapshot.TakenUtc,
                rows = rows
            }, GuardSnapshotJson.UiJsonSettings);
        }
    }

}
