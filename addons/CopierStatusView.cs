// CopierStatusView.cs
//
// What the Trade Copier window SAYS about the copier, derived from what the copier DOES.
//
// Why this file exists (P1-121):
// Three producers already compute everything an operator needs to answer "is the copier
// actually copying?" --
//   - TradeCopierEngine.GetCopierMode()        the global live/shadow/disabled gate
//   - TradeCopierEngine.DetectConfigConflicts() followers covered twice
//   - CopierMetric.Samples                     whether a metric was ever measured
// -- and the window rendered NONE of them. It displayed a hardcoded green
// "[ ENGINE: ACTIVE ]" that was assigned once at construction and never again, so no input
// could turn it red: the copier could be `disabled`, copying nothing, while the one screen
// built to report on it showed green and listed every relationship as enabled.
//
// The comment above DetectConfigConflicts said the conflict was exposed "for the API and the
// UI to render". The API renders it. The UI never did. That comment was the only thing
// asserting a consumer that did not exist.
//
// THE RULE THIS FILE ENCODES, which is F-9's finding restated:
// the display is DERIVED FROM THE ENFORCER, never recomputed alongside it. `IsActing` calls
// TradeCopierEngine.IsCopierActingMode rather than comparing to "live" itself. If the set of
// acting modes ever changes, this file changes with it because it never had its own opinion.
// F-9 was a rule whose reported state had drifted from its enforced state in BOTH directions,
// and the remedy there was the same one.
//
// Why it names no WPF type:
// TradeCopierWindow.cs is excluded from the test build (P2-27's open half), so anything
// written there cannot be executed by a test or killed by a mutant. This file is plain C#
// with no `#if`, so the tests/RiskGuardTests.csproj glob picks it up automatically and every
// decision below is executed and mutated. The window keeps only the brush mapping.
// That is the same split that BridgeAccountResolver, BridgeFlattenPlan, BridgeLockoutGate and
// GuardConfigEdit already use.
//

using System;
using System.Collections.Generic;

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>
    /// How loudly a status line should read. The window maps this to a brush; this file
    /// deliberately knows nothing about colour.
    ///
    /// Ordered by rank so that the worst of several inputs wins -- see Worse(). A headline
    /// that averaged its inputs would let one healthy relationship soften a quarantined one.
    /// </summary>
    public enum CopierStatusSeverity
    {
        Ok = 0,        // acting, and something is actually armed to act on
        Info = 1,      // working as configured, but not placing live orders
        Warn = 2,      // configured to do something it is not doing
        Critical = 3   // the operator's mental model is likely to be wrong
    }

    /// <summary>
    /// One rendered status line: what to show, how loud, and WHY.
    ///
    /// Detail is not decoration. "COPIER DISABLED" alone invites the next question; the whole
    /// point of this ticket is that the window stops making the operator go and ask the API.
    /// </summary>
    public class CopierHeadline
    {
        public string Text { get; set; }
        public CopierStatusSeverity Severity { get; set; }
        public string Detail { get; set; }
    }

    public static class CopierStatusView
    {
        /// <summary>
        /// The text shown when a metric has never been measured.
        ///
        /// This exists as a constant because it is the load-bearing half of the metric
        /// display: `Latency: 0ms` and `Latency: not measured` are the same underlying zero,
        /// and only one of them is a claim about the market. The plan has said since P1-22
        /// that a zero in these fields is not a pass.
        /// </summary>
        public const string NotMeasured = "not measured this session";

        /// <summary>
        /// Whether this mode places orders -- ASKED OF THE ENGINE, never decided here.
        /// See the header: this indirection is the ticket.
        /// </summary>
        public static bool IsActing(string copierMode)
        {
            return TradeCopierEngine.IsCopierActingMode(copierMode);
        }

        public static CopierStatusSeverity Worse(CopierStatusSeverity a, CopierStatusSeverity b)
        {
            return (int)a >= (int)b ? a : b;
        }

        /// <summary>
        /// Render one metric, refusing to print a number that was never measured.
        ///
        /// `metric` null is treated as unmeasured rather than throwing: this runs on a 2-second
        /// UI timer, and a status panel that crashes tells the operator less than one that says
        /// it does not know.
        /// </summary>
        public static string MetricText(string label, CopierMetric metric, string unit, int decimals)
        {
            if (metric == null || !metric.Measured)
                return label + ": " + NotMeasured;

            string number = metric.Value.ToString("F" + decimals.ToString());
            return label + ": " + number + unit + " (n=" + metric.Samples.ToString() + ")";
        }

        /// <summary>
        /// The per-relationship status line.
        ///
        /// The defect this fixes is narrow and worth stating: the old line ended
        /// `Armed: LIVE`, which reads as "this relationship places orders". It does not, unless
        /// the GLOBAL mode is also acting. So a shadow copier displayed a screen full of rows
        /// each claiming to be live. Any row that cannot act now says so, and names the reason,
        /// in this precedence:
        ///   quarantined  > disabled by the operator > global mode > not armed > active
        /// Quarantine ranks first because it is the one state the operator did not choose.
        /// </summary>
        public static CopierHeadline RelationshipLine(
            string copierMode,
            CopierSizingMode sizingMode,
            double ratio,
            int maxPositionSize,
            bool isEnabled,
            bool armedForLive,
            bool isQuarantined,
            string quarantineReason,
            CopierMetric latency,
            CopierMetric slippage)
        {
            string basics =
                "Sizing: " + sizingMode.ToString()
                + " | Ratio: " + ratio.ToString("F1") + "x"
                + " | MaxPos: " + maxPositionSize.ToString()
                + " | " + MetricText("Latency", latency, "ms", 0)
                + " | " + MetricText("Slippage", slippage, "t", 1);

            if (isQuarantined)
            {
                return new CopierHeadline
                {
                    Text = basics + " | QUARANTINED - not copying",
                    Severity = CopierStatusSeverity.Critical,
                    Detail = string.IsNullOrWhiteSpace(quarantineReason)
                        ? "Quarantined with no reason recorded."
                        : "Quarantined: " + quarantineReason
                };
            }

            if (!isEnabled)
            {
                return new CopierHeadline
                {
                    Text = basics + " | DISABLED - not copying",
                    Severity = CopierStatusSeverity.Warn,
                    Detail = "This relationship is switched off, so nothing is copied for it."
                };
            }

            if (!IsActing(copierMode))
            {
                return new CopierHeadline
                {
                    Text = basics + " | INERT - copier mode is '" + copierMode + "'",
                    Severity = CopierStatusSeverity.Warn,
                    Detail = "This relationship is enabled"
                        + (armedForLive ? " and armed for live" : "")
                        + ", but the global copier mode is '" + copierMode
                        + "', so no order is submitted for it."
                };
            }

            if (!armedForLive)
            {
                return new CopierHeadline
                {
                    Text = basics + " | Armed: SIM",
                    Severity = CopierStatusSeverity.Info,
                    Detail = "Copies to simulation followers only; a live follower is refused."
                };
            }

            return new CopierHeadline
            {
                Text = basics + " | Armed: LIVE",
                Severity = CopierStatusSeverity.Ok,
                Detail = "Enabled and armed: real orders are placed on the follower."
            };
        }

        /// <summary>
        /// The per-GROUP status line. Same defect as RelationshipLine and the same fix, but a
        /// group is deliberately not routed through that method: a group carries no quarantine
        /// flag and no metrics of its own (those live on the per-follower relationships it
        /// expands to), so reusing it would print "Latency: not measured this session" for a
        /// group whose followers are being measured perfectly well. A shared function that has
        /// to be fed blanks is not shared code, it is a second dialect with one caller lying.
        /// </summary>
        public static CopierHeadline GroupLine(
            string copierMode,
            string followersSummary,
            int followerCount,
            CopierSizingMode sizingMode,
            double ratio,
            bool isEnabled,
            bool armedForLive)
        {
            string basics =
                "Followers (" + followerCount.ToString() + "): [" + (followersSummary ?? "") + "]"
                + " | Sizing: " + sizingMode.ToString()
                + " | Ratio: " + ratio.ToString("F1") + "x";

            if (followerCount == 0)
            {
                return new CopierHeadline
                {
                    Text = basics + " | EMPTY - nothing to copy to",
                    Severity = CopierStatusSeverity.Warn,
                    Detail = "This group has no followers, so it copies nothing regardless of mode."
                };
            }

            if (!isEnabled)
            {
                return new CopierHeadline
                {
                    Text = basics + " | DISABLED - not copying",
                    Severity = CopierStatusSeverity.Warn,
                    Detail = "This group is switched off, so nothing is copied for it."
                };
            }

            if (!IsActing(copierMode))
            {
                return new CopierHeadline
                {
                    Text = basics + " | INERT - copier mode is '" + copierMode + "'",
                    Severity = CopierStatusSeverity.Warn,
                    Detail = "This group is enabled"
                        + (armedForLive ? " and armed for live" : "")
                        + ", but the global copier mode is '" + copierMode
                        + "', so no order is submitted for any of its followers."
                };
            }

            if (!armedForLive)
            {
                return new CopierHeadline
                {
                    Text = basics + " | Armed: SIM",
                    Severity = CopierStatusSeverity.Info,
                    Detail = "Copies to simulation followers only; a live follower is refused."
                };
            }

            return new CopierHeadline
            {
                Text = basics + " | Armed: LIVE",
                Severity = CopierStatusSeverity.Ok,
                Detail = "Enabled and armed: real orders are placed on every follower in this group."
            };
        }

        /// <summary>
        /// The window's header line -- the one that was a green constant.
        ///
        /// Every count is folded out of the SAME collections the window is about to render,
        /// rather than being tracked alongside them. A summary with its own counters is free to
        /// drift from the list underneath it, which is what F-9 was; the tests recount from the
        /// fixture instead of asserting hardcoded totals for the same reason.
        /// </summary>
        public static CopierHeadline Describe(
            string copierMode,
            IEnumerable<CopierRelationship> relationships,
            IEnumerable<CopierGroup> groups,
            int conflictCount)
        {
            int total = 0, enabled = 0, armed = 0, quarantined = 0;

            if (relationships != null)
            {
                foreach (var r in relationships)
                {
                    if (r == null) continue;
                    total++;
                    if (r.IsQuarantined) quarantined++;
                    if (r.IsEnabled) enabled++;
                    if (r.IsEnabled && r.ArmedForLive && !r.IsQuarantined) armed++;
                }
            }

            if (groups != null)
            {
                foreach (var g in groups)
                {
                    if (g == null) continue;
                    int followers = g.FollowerAccounts == null ? 0 : g.FollowerAccounts.Count;
                    total += followers;
                    if (g.IsEnabled) enabled += followers;
                    if (g.IsEnabled && g.ArmedForLive) armed += followers;
                }
            }

            var headline = Headline(copierMode, total, enabled, armed, quarantined);

            // A conflict never LOWERS the severity, and it is appended rather than replacing
            // the mode text: an operator needs both facts at once. A follower covered by both
            // a direct relationship and a group is copied twice, which is a sizing defect that
            // no single row can show, because each row is individually correct.
            if (conflictCount > 0)
            {
                headline.Severity = Worse(headline.Severity, CopierStatusSeverity.Warn);
                headline.Text = headline.Text + "  [ " + conflictCount.ToString() + " CONFIG CONFLICT"
                    + (conflictCount == 1 ? "" : "S") + " ]";
                headline.Detail = headline.Detail
                    + " " + conflictCount.ToString() + " follower"
                    + (conflictCount == 1 ? " is" : "s are")
                    + " covered by BOTH a direct relationship and a group, so that follower is"
                    + " copied twice.";
            }

            return headline;
        }

        /// <summary>
        /// Mode-first, because the global gate overrides every relationship beneath it.
        ///
        /// An unrecognised mode is CRITICAL rather than being treated as off, and that
        /// asymmetry is deliberate: the engine fails closed on it (P1-87), so nothing is being
        /// copied, but the operator set a value that the copier does not understand and no
        /// other surface will tell them.
        /// </summary>
        private static CopierHeadline Headline(
            string copierMode, int total, int enabled, int armed, int quarantined)
        {
            string counts = total.ToString() + " relationship" + (total == 1 ? "" : "s")
                + ", " + enabled.ToString() + " enabled"
                + (quarantined > 0 ? ", " + quarantined.ToString() + " QUARANTINED" : "");

            if (!TradeCopierEngine.IsRecognisedCopierMode(copierMode))
            {
                return new CopierHeadline
                {
                    Text = "[ COPIER MODE UNRECOGNISED ]",
                    Severity = CopierStatusSeverity.Critical,
                    Detail = "'" + (copierMode ?? "(null)") + "' is not one of live/shadow/disabled."
                        + " The copier fails closed and submits nothing. " + counts + "."
                };
            }

            if (!IsActing(copierMode))
            {
                bool disabled = string.Equals(copierMode, "disabled", StringComparison.OrdinalIgnoreCase);
                return new CopierHeadline
                {
                    Text = disabled ? "[ COPIER DISABLED ]" : "[ COPIER SHADOW ]",
                    Severity = CopierStatusSeverity.Warn,
                    Detail = (disabled
                            ? "The copier is off: no order is submitted for any relationship."
                            : "Shadow: the copier logs the order it would have sent and submits nothing.")
                        + " " + counts + "."
                };
            }

            if (total == 0)
            {
                return new CopierHeadline
                {
                    Text = "[ COPIER LIVE - NOTHING CONFIGURED ]",
                    Severity = CopierStatusSeverity.Warn,
                    Detail = "The copier is live but no relationship or group is configured,"
                        + " so nothing is copied."
                };
            }

            if (quarantined > 0 && quarantined >= enabled)
            {
                return new CopierHeadline
                {
                    Text = "[ COPIER LIVE - ALL QUARANTINED ]",
                    Severity = CopierStatusSeverity.Critical,
                    Detail = "Every enabled relationship is quarantined, so nothing is copied. "
                        + counts + "."
                };
            }

            if (quarantined > 0)
            {
                return new CopierHeadline
                {
                    Text = "[ COPIER LIVE - " + quarantined.ToString() + " QUARANTINED ]",
                    Severity = CopierStatusSeverity.Warn,
                    Detail = counts + ". A quarantined relationship copies nothing until released."
                };
            }

            if (armed == 0)
            {
                return new CopierHeadline
                {
                    Text = "[ COPIER LIVE - SIM ONLY ]",
                    Severity = CopierStatusSeverity.Info,
                    Detail = counts + ". Nothing is armed for live, so copies reach simulation"
                        + " followers only and a live follower is refused."
                };
            }

            return new CopierHeadline
            {
                Text = "[ COPIER LIVE - " + armed.ToString() + " ARMED ]",
                Severity = CopierStatusSeverity.Ok,
                Detail = counts + ", " + armed.ToString() + " armed for live."
            };
        }
    }
}
