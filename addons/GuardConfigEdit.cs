// GuardConfigEdit.cs
//
// Shared validator for edits to the guard configuration.
//
// Why this file exists:
// Two writers reach the live RiskConfig and neither validates what a value means:
//   - The /api/riskguard/config POST endpoint merges a partial JSON body onto the live config.
//   - RiskGuardWindow.OnSaveConfigClick parses form values straight onto the live config.
// SaveAndReloadConfig does not run preflight, so a bad value is written to RiskGuard/config.json,
// reloaded at the next restart, and the guard comes up disarmed with nothing in the file looking wrong.
// This validator is called before any write so that an unacceptable value is refused with a
// sentence naming the field, instead of being persisted.
//
// Scope warning - TrailingDrawdown = 0 means two different things in this codebase:
//   - On the global PnLRules it means the rule is OFF. That is what this validator refuses.
//   - On an AccountRiskProfile it is a deliberate sentinel meaning "derive from account cash value"
//     (see RiskGuardAddOn.cs around line 2409). Do not feed a per-account value into this validator.
// There is also a TrailingDrawdown default on RiskManagerAddOn (2000) that is unrelated.
//

using System;

namespace NinjaTrader.NinjaScript.AddOns
{
    public static class GuardConfigEdit
    {
        public static string Refuse(string mode, double trailingDrawdown, int minShadowSessions)
        {
            string modeProblem = RefuseMode(mode);
            if (modeProblem != null)
            {
                return modeProblem;
            }

            // `!(x > 0)` rather than `x <= 0` deliberately: it refuses NaN too, and NaN is what a
            // caller gets from a text box that parsed to nothing. `NaN <= 0` is FALSE, so the
            // obvious form accepts it and writes a limit no comparison can ever satisfy.
            if (!(trailingDrawdown > 0.0))
            {
                return "Trailing drawdown must be greater than zero. Zero is not a tight limit, "
                     + "it is no limit -- the guard reports the rule as off.";
            }

            if (minShadowSessions < 0)
            {
                return "Minimum shadow sessions cannot be negative. Use 0 to require none.";
            }

            return null;
        }

        /// <summary>
        /// The mode clause, and every branch of it exists to say something DIFFERENT about what
        /// the operator should do next.
        ///
        /// ⚠️ ONLY A CASE VARIANT OF A VALID MODE MAY MENTION CASE. The first version of this
        /// method told the operator that `PURE` and `DISABLED` were refused because "mode is
        /// case-sensitive" -- true of the comparison and useless as advice, because `pure` and
        /// `disabled` are refused in any case at all. A message that names a fix which does not
        /// work is worse than one that names none: it is `P3-118`'s defect, which is that
        /// preflight calls `Live` unrecognised and sends the reader hunting for a typo. No test
        /// pinned the text, the panel did not raise it, and it arrived through the one gate this
        /// class exists to be -- so it is pinned now.
        /// </summary>
        private static string RefuseMode(string mode)
        {
            // A missing mode in a partial update means "do not change it". The endpoint takes
            // partial bodies by design (P2-41's merge), so refusing an omitted field would make
            // every partial write fail.
            if (string.IsNullOrWhiteSpace(mode))
            {
                return null;
            }

            // ORDINAL, because RunPreflight is: `if (_mode != "shadow" && _mode != "live" && ...)`.
            // A validator that accepted `Shadow` would write a config the guard then refuses to
            // arm on, which is the entire defect this class exists to prevent. See P3-118 for why
            // the three readers of Mode disagree about case in the first place.
            if (mode == "shadow" || mode == "live")
            {
                return null;
            }

            if (string.Equals(mode, "shadow", StringComparison.OrdinalIgnoreCase)
                || string.Equals(mode, "live", StringComparison.OrdinalIgnoreCase))
            {
                return "Mode '" + mode + "' differs only in CASE from a valid mode, and the guard "
                     + "compares it exactly. Use '" + mode.ToLowerInvariant() + "'.";
            }

            if (string.Equals(mode, "pure", StringComparison.OrdinalIgnoreCase)
                || string.Equals(mode, "override_with_friction", StringComparison.OrdinalIgnoreCase))
            {
                return "Mode '" + mode + "' is recognised but NOT IMPLEMENTED -- only 'live' acts, "
                     + "so it would observe while reporting an acting mode. Use 'shadow' or 'live'.";
            }

            if (string.Equals(mode, "disabled", StringComparison.OrdinalIgnoreCase))
            {
                return "Mode 'disabled' belongs to the trade COPIER, not the guard. To stop the "
                     + "guard acting use 'shadow', which observes and records. Valid: 'shadow', 'live'.";
            }

            return "Mode '" + mode + "' is not a guard mode. Valid: 'shadow', 'live'.";
        }
    }
}
