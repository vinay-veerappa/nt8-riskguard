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
//   P2-78  PerInstrumentRiskConfig.IsBlocked / .StopOffsetTicks: zero references anywhere.
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
    }

    public class GuardAccountRules
    {
        public string AccountName { get; set; }
        public bool IsExcluded { get; set; }
        public bool IsLockedOut { get; set; }
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

        private static GuardRuleReading Off(string note)
        {
            return new GuardRuleReading { DisabledByConfig = true, EvidenceCount = 1, Note = note };
        }

        private static readonly List<GuardRuleDefinition> _rules = new List<GuardRuleDefinition>
        {
            // ── P&L, per account ──────────────────────────────────────────────────────
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
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => c.Config.PnLRules.TrailingDrawdown <= 0
                    ? Off("no trailing drawdown set")
                    : R(c.Account == null ? (double?)null : c.Account.AccountEquity,
                        c.Config.PnLRules.TrailingDrawdown, c.Account == null ? 0 : 1)
            },

            // ── sizing ────────────────────────────────────────────────────────────────
            new GuardRuleDefinition {
                Name = "Max contracts per account", ConfigPath = "Sizing.MaxContractsPerAccount",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => c.Config.Sizing.MaxContractsPerAccount <= 0
                    ? Off("no per-account contract cap")
                    : R(null, c.Config.Sizing.MaxContractsPerAccount, c.Account == null ? 0 : 1)
            },
            new GuardRuleDefinition {
                Name = "Max contracts aggregate", ConfigPath = "Sizing.MaxContractsAggregate",
                EvidenceLabel = "accounts visible to the aggregate cap",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Aggregate,
                // Evidence is the number of accounts it can see. An aggregate cap over ZERO
                // known accounts is not enforcing anything, and would otherwise read as green.
                Evaluator = c => c.Config.Sizing.MaxContractsAggregate <= 0
                    ? Off("no aggregate contract cap")
                    : R(null, c.Config.Sizing.MaxContractsAggregate,
                        c.AllAccounts == null ? 0 : c.AllAccounts.Count)
            },

            // ── overtrading ───────────────────────────────────────────────────────────
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

            // ── stop guard ────────────────────────────────────────────────────────────
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
                // reading -- it means "cannot fire", and this always fires.
                Evaluator = c => R(null, null, 1,
                    "tick offsets used when the guard places a stop itself; "
                    + (c.Config.StopGuard.Offsets == null ? 0 : c.Config.StopGuard.Offsets.Count)
                    + " configured, the rest fall back to the default")
            },

            // ── instruments ───────────────────────────────────────────────────────────
            new GuardRuleDefinition {
                Name = "Blocked instruments", ConfigPath = "BlockedInstruments",
                EvidenceLabel = "instruments on the block list",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerOrder,
                // An EMPTY block list blocks nothing. INERT is the honest reading, not green.
                Evaluator = c => R(null, null,
                    c.Config.BlockedInstruments == null ? 0 : c.Config.BlockedInstruments.Count)
            },
            new GuardRuleDefinition {
                Name = "Per-instrument contract caps", ConfigPath = "InstrumentLimits",
                EvidenceLabel = "instruments with a configured cap",
                Source = GuardRuleSource.InstrumentLimit, Scope = GuardRuleScope.PerOrder,
                // ⚠️ Only MaxContracts is read. IsBlocked and StopOffsetTicks on the SAME object
                // have zero references anywhere -- P2-78 -- so a per-instrument `IsBlocked: true`
                // looks exactly like the way to block one instrument and does nothing.
                Evaluator = c => R(null, null,
                    c.Config.InstrumentLimits == null ? 0 : c.Config.InstrumentLimits.Count,
                    "only MaxContracts is enforced; IsBlocked and StopOffsetTicks on the same "
                    + "object are read by nothing (P2-78) -- use BlockedInstruments to block")
            },

            // ── trading windows ───────────────────────────────────────────────────────
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
                        ? "⚠️ the gate is ON with NO windows configured -- check what this permits"
                        : c.Config.WindowsET.Count + " window(s) permitted")
            },
            new GuardRuleDefinition {
                Name = "Permitted trading windows (ET)", ConfigPath = "WindowsET",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                Evaluator = c => !c.Config.EnableWindowGate
                    ? Off("only consulted when EnableWindowGate is true")
                    : R(null, null, 1, (c.Config.WindowsET == null || c.Config.WindowsET.Count == 0)
                        ? "⚠️ no windows configured while the gate is ON"
                        : c.Config.WindowsET.Count + " window(s)")
            },

            // ── firm mirror ───────────────────────────────────────────────────────────
            // ⚠️ Evidence is the ACCOUNT->FIRM MAP SIZE, not 1. The firm rules being "loaded but
            // unmapped, so none can fire" is a state this system has already been in (handover
            // §0), and an unmapped firm rule must read INERT rather than green.
            new GuardRuleDefinition {
                Name = "Firm trailing drawdown", ConfigPath = "FirmMirror.TrailingDD.Amount",
                EvidenceLabel = "accounts mapped to a firm",
                Source = GuardRuleSource.FirmProfile, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => !c.Config.FirmMirror.Enabled || !c.Config.FirmMirror.TrailingDD.Enabled
                    ? Off("firm trailing drawdown not enabled")
                    : R(c.Account == null ? (double?)null : c.Account.AccountEquity,
                        c.Config.FirmMirror.TrailingDD.Amount,
                        c.Config.FirmMirror.AccountFirmMap == null ? 0 : c.Config.FirmMirror.AccountFirmMap.Count,
                        "unmapped accounts fall back to the top-level TrailingDD block")
            },
            new GuardRuleDefinition {
                Name = "Firm daily loss", ConfigPath = "FirmMirror.DailyLoss.Amount",
                EvidenceLabel = "accounts mapped to a firm",
                Source = GuardRuleSource.FirmProfile, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => !c.Config.FirmMirror.Enabled || !c.Config.FirmMirror.DailyLoss.Enabled
                    ? Off("firm daily loss not enabled")
                    : R(c.Account == null ? (double?)null : c.Account.RealizedPnL,
                        -Math.Abs(c.Config.FirmMirror.DailyLoss.Amount),
                        c.Config.FirmMirror.AccountFirmMap == null ? 0 : c.Config.FirmMirror.AccountFirmMap.Count)
            },

            // ── prop-firm suite: the ones that DO work ────────────────────────────────
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
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                Evaluator = c => c.PropConfig == null || !c.PropConfig.EnablePeakEquityProtection
                    ? Off("peak equity protection disabled")
                    : R(null, c.PropConfig.MaxPeakGivebackPct, c.Account == null ? 0 : 1,
                        "ignores peaks below $" + c.PropConfig.MinPeakGainDollars + " (P1-40)")
            },

            // ── prop-firm suite: THE NEWS SHIELD. P2-25, and the reason for INERT. ─────
            new GuardRuleDefinition {
                Name = "News shield", ConfigPath = "PropFirm.EnableNewsShield",
                EvidenceLabel = "news events loaded",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                // Fully wired and structurally unable to fire. RiskGuardAddOn.cs:1541 tests the
                // flag, calls IsInNewsWindow, which iterates _newsEvents -- a list nothing
                // outside a test appends to, because LocalNewsEventsFilePath has no loader.
                // Evidence is the EVENT COUNT, so this reports INERT until one is loaded.
                Evaluator = c => c.PropConfig == null || !c.PropConfig.EnableNewsShield
                    ? Off("news shield disabled")
                    : R(null, null, c.NewsEventCount,
                        c.NewsEventCount == 0
                            ? "P2-25: no news events are loaded, so this can never fire. "
                              + "LocalNewsEventsFilePath is parsed and read by no loader."
                            : null)
            },

            // ── prop-firm suite: the ones with NO evaluator. Each is a finding. ────────
            new GuardRuleDefinition {
                Name = "Consistency / daily-profit cap", ConfigPath = "PropFirm.EnableConsistencyCap",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                UnevaluatedReason = "P1-77. EnableConsistencyCap defaults to TRUE and appears at "
                    + "exactly two sites -- its declaration and the JSON parser. No evaluator "
                    + "exists anywhere, so this has never capped anything. It covers an "
                    + "account-FAILURE condition on a funded evaluation."
            },
            new GuardRuleDefinition {
                Name = "Consistency cap threshold", ConfigPath = "PropFirm.MaxDailyProfitPctOfTarget",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                UnevaluatedReason = "P1-77. The threshold for a cap that is evaluated nowhere."
            },
            new GuardRuleDefinition {
                Name = "News events file", ConfigPath = "PropFirm.LocalNewsEventsFilePath",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                UnevaluatedReason = "P2-25, and this is the CAUSE of the news shield being INERT: "
                    + "the path is parsed out of the config and read by NO loader, so the event "
                    + "list is always empty. Fixing this one field is what makes the shield real."
            },
            new GuardRuleDefinition {
                Name = "Auto day filler", ConfigPath = "PropFirm.EnableAutoDayFiller",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.Session,
                UnevaluatedReason = "Parsed and evaluated nowhere. Unlike the consistency cap "
                    + "this one defaults to FALSE, so it is a dead option rather than a lie."
            },
            new GuardRuleDefinition {
                Name = "Prop suite armed", ConfigPath = "PropFirm.ArmedForLive",
                Source = GuardRuleSource.Config, Scope = GuardRuleScope.PerAccount,
                UnevaluatedReason = "Found 2026-08-13 while building this registry. It is read by "
                    + "its own safety gate (PropFirmProtectionSuite.cs:73) and by the parser, and "
                    + "by NOTHING ELSE -- no prop rule consults it before acting. The prop rules "
                    + "are gated by the GUARD's mode instead, so this flag protects nothing and "
                    + "an operator reading it would draw the wrong conclusion either way."
            },
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
            new GuardNonRule { ConfigPath = "PnLRules.LockoutMinutes", Reason = "the consequence of a P&L breach, not a threshold" },
            new GuardNonRule { ConfigPath = "Overtrading.LockoutMinutes", Reason = "the consequence of an overtrading breach" },
            new GuardNonRule { ConfigPath = "Overtrading.CooldownMinutes", Reason = "the consequence of a loss streak" },
            new GuardNonRule { ConfigPath = "Sizing.ExpectedCopies", Reason = "a divisor used when sizing across copied accounts; not a cap" },
            new GuardNonRule { ConfigPath = "Override.ConfirmPhrase", Reason = "friction for escaping a lockout (FR-35/36)" },
            new GuardNonRule { ConfigPath = "Override.WaitSeconds", Reason = "friction for escaping a lockout; clamped to >= 30 at validation" },
            new GuardNonRule { ConfigPath = "FirmMirror.Enabled", Reason = "the master switch for the two firm rules above; reported through their Disabled state" },
            new GuardNonRule { ConfigPath = "FirmMirror.AccountFirmMap", Reason = "which firm an account belongs to; it is the EVIDENCE COUNT for both firm rules" },
            new GuardNonRule { ConfigPath = "FirmMirror.FirmProfiles", Reason = "the per-firm value tables the two firm rules resolve against" },
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
            int newsEventCount)
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

            foreach (var account in accounts)
            {
                var accountRules = new GuardAccountRules();
                accountRules.AccountName = account.AccountName;
                accountRules.IsExcluded = account.IsExcluded;
                accountRules.IsLockedOut = account.IsLockedOut;
                accountRules.Rules = new List<GuardRuleRow>();
                snapshot.Accounts.Add(accountRules);
            }

            foreach (var def in Rules)
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
        private static readonly JsonSerializerSettings _settings = new JsonSerializerSettings
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
            }, _settings);
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
                    _settings);
            }

            return JsonConvert.SerializeObject(snapshot, _settings);
        }
    }

}
