// CopierSymbolMatrixView.cs
//
// What the copier window's "Symbol & Per-Ticker Matrix" tab says, derived from the copier's
// own configuration rather than printed beside it.
//
// Why this file exists (P2-123):
// The tab of that name contained no per-ticker matrix. It was a hardcoded six-row poster of
// asset classes and mini/micro contract names, rendered as TextBlocks. Measured, four
// commands, no reading required:
//
//   TradeCopierEngine references inside CreateSymbolMatrixTab ......... 0
//   PerTickerRatios / CustomSymbolMappings anywhere in the window ..... 0
//   Occurrences of _ratioNqText in the file ........................... 1  (the declaration)
//   Occurrences of _ratioEsText in the file ........................... 1  (the declaration)
//
// PerTickerRatios and CustomSymbolMappings are real, persisted, engine-enforced config,
// settable through nt_copier_config. An operator who sets {"NQ": 2, "ES": 1} saw no trace of
// it on the screen named after it -- and worse, the static table went on asserting the default
// conversion, so the display CONTRADICTED the config the copier was enforcing.
//
// THE RULE THIS FILE ENCODES is the one CopierStatusView encodes one tab across, and it is
// F-9's: the display is DERIVED FROM THE ENFORCER, never recomputed alongside it. Every number
// below comes from TradeCopierEngine.ComputeEffectiveRatio and every routing decision from
// TradeCopierEngine.TranslateSymbol -- the same two functions the copy path itself calls. This
// file has no opinion about ratios or symbols and must never grow one.
//
// ⚠️ WHY THE ROWS ARE NOT A LIST OF ASSET CLASSES. The mini/micro table already exists in FOUR
// places in TradeCopierEngine.cs (the TranslateSymbol switch, the multiplier test inside
// ComputeEffectiveRatio, the pairing test in the conflict detector, and one more in the sizing
// path). Enumerating asset classes here would have made a FIFTH copy, in the one file whose
// job is to report what the other four do. The rows are instead the roots the operator has
// actually CONFIGURED, asked of the engine one at a time. Filed separately as P3-124.
//
// Why it names no WPF type:
// TradeCopierWindow.cs is excluded from the test build (P2-27's open half), so anything
// written there cannot be executed by a test or killed by a mutant. This file is plain C# with
// no `#if`, so tests/RiskGuardTests.csproj picks it up by glob and every decision below is
// executed and mutated. The window keeps only the brush mapping.

using System;
using System.Collections.Generic;

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>Where the number or the routing in force actually came from.</summary>
    public enum CopierSymbolOrigin
    {
        /// <summary>The relationship's flat QuantityRatio, with no per-ticker entry.</summary>
        RelationshipDefault = 0,

        /// <summary>An entry the operator wrote into PerTickerRatios.</summary>
        PerTickerOverride = 1,

        /// <summary>An entry the operator wrote into CustomSymbolMappings.</summary>
        CustomMapping = 2,

        /// <summary>The built-in bidirectional mini/micro table.</summary>
        AutomaticMiniMicro = 3,

        /// <summary>No conversion applies; the follower trades the leader's own instrument.</summary>
        SameInstrument = 4
    }

    /// <summary>One configured instrument root, for one relationship.</summary>
    public class CopierSymbolRow
    {
        public string LeaderRoot { get; set; }
        public string FollowerRoot { get; set; }
        public CopierSymbolOrigin RoutingOrigin { get; set; }
        public CopierSymbolOrigin RatioOrigin { get; set; }

        /// <summary>
        /// ⚠️ FALSE means the sizing mode makes a ratio meaningless, NOT that the ratio is zero.
        /// Rendering `EffectiveRatio` when this is false states a number the copier does not
        /// use -- the same confusion CopierMetric.Measured removed from the latency fields.
        /// </summary>
        public bool RatioApplies { get; set; }

        public double EffectiveRatio { get; set; }

        /// <summary>Null when there is nothing to warn about. Never empty-string.</summary>
        public string Warning { get; set; }

        public string RatioText { get; set; }
        public string RoutingText { get; set; }
    }

    /// <summary>One relationship's configured per-ticker state, as the tab renders it.</summary>
    public class CopierSymbolMatrix
    {
        public string RelationshipId { get; set; }
        public string Label { get; set; }
        public string SizingModeText { get; set; }

        /// <summary>Whether the built-in mini/micro table is live FOR THIS RELATIONSHIP.</summary>
        public bool AutoConversionActive { get; set; }
        public string AutoConversionText { get; set; }

        /// <summary>Says so in words when nothing is configured. Never left to an empty list.</summary>
        public string Headline { get; set; }
        public CopierStatusSeverity Severity { get; set; }

        public List<CopierSymbolRow> Rows { get; set; }
    }

    public static class CopierSymbolMatrixView
    {
        public const string NothingConfigured =
            "no per-ticker ratios and no custom symbol mappings are configured";

        public const string NoRelationships =
            "no copier relationships are configured, so there is nothing to convert";

        /// <summary>
        /// Whether a ratio is a meaningful number for this sizing mode.
        ///
        /// ⚠️ Asked of the SIZING MODE, never of the value. ComputeEffectiveRatio answers 0.0
        /// for FixedLot, NetLiquidationRatio and AvailableCashPercent because those size off
        /// something other than a ratio -- so testing `ratio > 0` would call a correctly
        /// configured fixed-lot relationship "ratio 0", which reads as "copies nothing".
        /// </summary>
        public static bool RatioApplies(CopierSizingMode mode, bool fixedLotMode)
        {
            if (fixedLotMode) return false;
            return mode == CopierSizingMode.QuantityRatio || mode == CopierSizingMode.PerTickerMatrix;
        }

        /// <summary>
        /// Whether the built-in mini/micro table is live for this relationship.
        ///
        /// ⚠️ BOTH conditions, and the second is the one a reader forgets: PerTickerMatrix mode
        /// disables automatic conversion outright, to force same-instrument sizing. The static
        /// tab claimed conversion happened "across all futures asset classes" with no mention
        /// of either condition, which is false for every matrix-mode relationship on the box.
        /// </summary>
        public static bool AutoConversionActive(CopierRelationship rel)
        {
            if (rel == null) return false;
            return rel.AutoSymbolConversion && rel.SizingMode != CopierSizingMode.PerTickerMatrix;
        }

        /// <summary>How far this probes before giving up on a ratio being usable at all.</summary>
        public const int MaxProbedLeaderFill = 1000;

        /// <summary>
        /// The smallest leader fill that survives the conversion, or 0 when none within reach
        /// does.
        ///
        /// This is the caveat the static tab omitted, and it is the one that loses a trade: at
        /// ratio 1.0 a 1-lot MNQ leader fill converts to 0.1 of an NQ and the copy is SKIPPED,
        /// not rounded up. The tab that exists to explain conversion was the one place that
        /// never mentioned how conversion silently drops an order.
        ///
        /// ⚠️ COMPUTED BY ASKING THE ENGINE, NOT BY ARITHMETIC, and the first version of this
        /// function got it wrong in exactly the way this whole ticket is about. `ceil(1/ratio)`
        /// looks obviously right and disagrees with the copy path: .NET rounds midpoints TO
        /// EVEN, so at ratio 0.1 a 5-lot gives Math.Round(0.5) == 0 and is dropped while a
        /// 6-lot copies -- the honest answer is 6, and the arithmetic said 10. Telling an
        /// operator they need four more contracts than they do is a surface stating behaviour
        /// the engine does not perform, which is the defect, not the fix.
        /// </summary>
        public static int SmallestLeaderFillThatCopies(double effectiveRatio)
        {
            if (effectiveRatio <= 0.0 || double.IsNaN(effectiveRatio) || double.IsInfinity(effectiveRatio))
                return 0;

            for (int n = 1; n <= MaxProbedLeaderFill; n++)
            {
                if (TradeCopierEngine.RoundToContracts(n * effectiveRatio) >= 1) return n;
            }
            return 0;
        }

        public static string RatioTextFor(bool ratioApplies, CopierSizingMode mode, double effectiveRatio)
        {
            if (!ratioApplies)
                return "not sized by ratio (" + SizingModeText(mode) + ")";
            if (effectiveRatio <= 0.0)
                return "no ratio in force";
            return "x" + effectiveRatio.ToString("0.####");
        }

        public static string SizingModeText(CopierSizingMode mode)
        {
            switch (mode)
            {
                case CopierSizingMode.FixedLot: return "fixed lot";
                case CopierSizingMode.NetLiquidationRatio: return "net liquidation ratio";
                case CopierSizingMode.AvailableCashPercent: return "available cash percent";
                case CopierSizingMode.PerTickerMatrix: return "per-ticker matrix";
                default: return "quantity ratio";
            }
        }

        /// <summary>
        /// Every instrument root this relationship has been CONFIGURED for, deduplicated and
        /// case-folded the same way the engine's own dictionaries are.
        ///
        /// ⚠️ Both dictionaries, not just PerTickerRatios. A custom mapping with no ratio entry
        /// is a routing change the copier honours in every sizing mode, and omitting it would
        /// hide the setting most likely to send a copy somewhere the operator did not expect.
        /// </summary>
        public static List<string> ConfiguredRoots(CopierRelationship rel)
        {
            var roots = new List<string>();
            if (rel == null) return roots;

            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (rel.PerTickerRatios != null)
            {
                foreach (var key in rel.PerTickerRatios.Keys)
                {
                    if (string.IsNullOrEmpty(key) || !seen.Add(key)) continue;
                    roots.Add(key.ToUpper());
                }
            }
            if (rel.CustomSymbolMappings != null)
            {
                foreach (var key in rel.CustomSymbolMappings.Keys)
                {
                    if (string.IsNullOrEmpty(key) || !seen.Add(key)) continue;
                    roots.Add(key.ToUpper());
                }
            }
            roots.Sort(StringComparer.OrdinalIgnoreCase);
            return roots;
        }

        /// <summary>
        /// One row. `followerRoot` is what the ENGINE said this root translates to -- it is
        /// passed in rather than derived, because TranslateSymbol is the copy path's own
        /// routing decision and this file must not acquire a second one.
        /// </summary>
        public static CopierSymbolRow Row(
            CopierRelationship rel, string leaderRoot, string followerRoot, double effectiveRatio)
        {
            var row = new CopierSymbolRow
            {
                LeaderRoot = leaderRoot,
                FollowerRoot = followerRoot,
                EffectiveRatio = effectiveRatio
            };

            bool hasCustom = rel != null && rel.CustomSymbolMappings != null
                && rel.CustomSymbolMappings.ContainsKey(leaderRoot ?? "");
            bool hasPerTicker = rel != null && rel.PerTickerRatios != null
                && rel.PerTickerRatios.ContainsKey(leaderRoot ?? "");

            bool routesElsewhere = !string.IsNullOrEmpty(followerRoot)
                && !string.Equals(followerRoot, leaderRoot, StringComparison.OrdinalIgnoreCase);

            if (hasCustom)
                row.RoutingOrigin = CopierSymbolOrigin.CustomMapping;
            else if (routesElsewhere)
                row.RoutingOrigin = CopierSymbolOrigin.AutomaticMiniMicro;
            else
                row.RoutingOrigin = CopierSymbolOrigin.SameInstrument;

            row.RatioOrigin = hasPerTicker
                ? CopierSymbolOrigin.PerTickerOverride
                : CopierSymbolOrigin.RelationshipDefault;

            row.RatioApplies = rel != null && RatioApplies(rel.SizingMode, rel.FixedLotMode);
            row.RatioText = RatioTextFor(
                row.RatioApplies,
                rel == null ? CopierSizingMode.QuantityRatio : rel.SizingMode,
                effectiveRatio);

            switch (row.RoutingOrigin)
            {
                case CopierSymbolOrigin.CustomMapping:
                    row.RoutingText = leaderRoot + " -> " + followerRoot + " (custom mapping)";
                    break;
                case CopierSymbolOrigin.AutomaticMiniMicro:
                    row.RoutingText = leaderRoot + " -> " + followerRoot + " (automatic mini/micro)";
                    break;
                default:
                    row.RoutingText = leaderRoot + " -> " + leaderRoot + " (same instrument)";
                    break;
            }

            // ⚠️ The warning is only meaningful where a ratio is actually applied. A fixed-lot
            // relationship copies a lot count and cannot round a leader fill away, so claiming
            // it drops 1-lots would be a false alarm on a correct configuration.
            if (row.RatioApplies)
            {
                if (effectiveRatio <= 0.0)
                {
                    row.Warning = rel != null && rel.SizingMode == CopierSizingMode.PerTickerMatrix
                        ? "matrix mode has no fallback ratio, so this root COPIES NOTHING until "
                          + "a per-ticker ratio is set for it"
                        : "no ratio in force for this root, so nothing is copied";
                }
                else
                {
                    int smallest = SmallestLeaderFillThatCopies(effectiveRatio);
                    if (smallest > 1)
                    {
                        row.Warning = "a leader fill below " + smallest.ToString()
                            + " contract(s) is DROPPED: at x" + effectiveRatio.ToString("0.####")
                            + " the copier rounds it below one contract";
                    }
                    else if (smallest == 0)
                    {
                        row.Warning = "the ratio is too small to copy any leader fill";
                    }
                }
            }

            return row;
        }

        /// <summary>
        /// The whole tab, for every relationship.
        ///
        /// `routeOf` is the engine's TranslateSymbol, injected rather than called, so this file
        /// names no engine instance and the tests drive the real routing without an NT8.
        /// </summary>
        public static List<CopierSymbolMatrix> Describe(
            IEnumerable<CopierRelationship> relationships, Func<CopierRelationship, string, string> routeOf)
        {
            var result = new List<CopierSymbolMatrix>();
            if (relationships == null) return result;

            foreach (var rel in relationships)
            {
                if (rel == null) continue;
                result.Add(DescribeOne(rel, routeOf));
            }
            return result;
        }

        public static CopierSymbolMatrix DescribeOne(
            CopierRelationship rel, Func<CopierRelationship, string, string> routeOf)
        {
            var matrix = new CopierSymbolMatrix
            {
                RelationshipId = rel == null ? null : rel.Id,
                Label = rel == null
                    ? "(none)"
                    : rel.LeaderAccountName + " -> " + rel.FollowerAccountName,
                SizingModeText = SizingModeText(rel == null ? CopierSizingMode.QuantityRatio : rel.SizingMode),
                AutoConversionActive = AutoConversionActive(rel),
                Rows = new List<CopierSymbolRow>()
            };

            matrix.AutoConversionText = matrix.AutoConversionActive
                ? "automatic mini/micro conversion is ON for this relationship"
                : rel != null && rel.SizingMode == CopierSizingMode.PerTickerMatrix
                    ? "automatic mini/micro conversion is OFF: matrix mode forces same-instrument sizing"
                    : "automatic mini/micro conversion is OFF for this relationship";

            var roots = ConfiguredRoots(rel);
            foreach (var root in roots)
            {
                string follower = routeOf == null ? root : routeOf(rel, root);
                double ratio = TradeCopierEngine.ComputeEffectiveRatio(rel, root);
                matrix.Rows.Add(Row(rel, root, follower, ratio));
            }

            matrix.Severity = CopierStatusSeverity.Ok;
            if (matrix.Rows.Count == 0)
            {
                // ⚠️ "Nothing to show" and "nothing is wrong" must not look the same. An empty
                // panel under a tab named for per-ticker ratios reads as "there are none to
                // worry about"; this says which flat ratio every instrument therefore uses.
                double flat = rel == null ? 0.0 : Math.Abs(rel.QuantityRatio);
                bool applies = rel != null && RatioApplies(rel.SizingMode, rel.FixedLotMode);
                matrix.Headline = NothingConfigured + ", so every instrument uses "
                    + (applies
                        ? "the relationship ratio of x" + flat.ToString("0.####")
                        : "the " + matrix.SizingModeText + " sizing above");
                matrix.Severity = CopierStatusSeverity.Info;
                return matrix;
            }

            int warned = 0;
            foreach (var row in matrix.Rows)
                if (!string.IsNullOrEmpty(row.Warning)) warned++;

            matrix.Headline = matrix.Rows.Count.ToString() + " configured root(s)";
            if (warned > 0)
            {
                matrix.Headline += ", " + warned.ToString() + " of which lose fills to rounding";
                matrix.Severity = CopierStatusSeverity.Warn;
            }

            return matrix;
        }
    }
}
