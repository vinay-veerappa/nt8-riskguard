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

            string trailingProblem = RefuseTrailingDrawdown(trailingDrawdown);
            if (trailingProblem != null)
            {
                return trailingProblem;
            }

            return RefuseMinShadowSessions(minShadowSessions);
        }

        /// <summary>
        /// ⚠️ EXTRACTED SO THAT RefuseChange DOES NOT HAVE TO LIE TO Refuse. The first
        /// implementation validated one field at a time by calling
        /// `Refuse("shadow", newTrailingDrawdown, 1)` -- passing invented values for the fields
        /// it was not asking about, so that Refuse's other clauses would stay quiet.
        ///
        /// That is correct only for as long as Refuse's clauses stay INDEPENDENT. The moment one
        /// of them relates two fields (a live mode requiring a nonzero drawdown, say), the
        /// placeholders become assertions about a config that does not exist, and the wrong
        /// answer arrives silently with every test still green. Per-field questions get
        /// per-field methods; Refuse composes them in the same order it always did, so there is
        /// still exactly ONE definition of each rule.
        /// </summary>
        private static string RefuseTrailingDrawdown(double trailingDrawdown)
        {
            // `!(x > 0)` rather than `x <= 0` deliberately: it refuses NaN too, and NaN is what a
            // caller gets from a text box that parsed to nothing, or from a config whose
            // PnLRules section is missing entirely. `NaN <= 0` is FALSE, so the obvious form
            // accepts it and writes a limit no comparison can ever satisfy.
            if (!(trailingDrawdown > 0.0))
            {
                return "Trailing drawdown must be greater than zero. Zero is not a tight limit, "
                     + "it is no limit -- the guard reports the rule as off.";
            }
            return null;
        }

        private static string RefuseMinShadowSessions(int minShadowSessions)
        {
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

        /// <summary>
        /// Refuse only what THIS WRITE INTRODUCES. A value that is already unacceptable and is
        /// being left alone is permitted through, because one of the writers behind this
        /// chokepoint is the account-exclusion toggle -- the control that puts an account BACK
        /// under the guard. Refusing there would remove the remedy for the very condition being
        /// refused over, which is `P1-106` at a second site.
        ///
        /// ⚠️ THE OLD VALUES MUST COME FROM A DIFFERENT OBJECT THAN THE NEW ONES. If a caller
        /// mutates the live config in place and passes it as `newConfig`, every field here
        /// equals itself, nothing is ever "changed", and this method permits everything while
        /// its own tests pass. That was `P1-117`, and it is why the window now edits a copy.
        /// </summary>
        public static string RefuseChange(
            string oldMode, string newMode,
            double oldTrailingDrawdown, double newTrailingDrawdown,
            int oldMinShadowSessions, int newMinShadowSessions)
        {
            // Ordinal, matching RunPreflight. See RefuseMode.
            if (!string.Equals(oldMode, newMode, StringComparison.Ordinal))
            {
                // ⚠️ A BLANK MODE MEANS SOMETHING DIFFERENT HERE THAN IT DOES IN Refuse, and
                // that asymmetry is the point. Refuse validates a PARTIAL body, where an omitted
                // field means "do not change it" -- so blank is accepted there, and
                // TestP227_AnOmittedModeIsAccepted pins it. RefuseChange guards a write of the
                // WHOLE config: nothing is omitted, and a blank mode is the value that gets
                // serialised. Deferring to RefuseMode here would accept it and persist a config
                // the guard cannot arm on.
                //
                // Found by the mutation battery. Mutant 6 restored the blank-fill and survived
                // 1838 green tests; writing the test that kills it showed the same hole in the
                // hand-written implementation, one clause further along.
                if (string.IsNullOrWhiteSpace(newMode))
                {
                    return "Mode is blank, and this write replaces the whole configuration -- "
                         + "blank is what would be saved. Use 'shadow' or 'live'.";
                }

                string refusal = RefuseMode(newMode);
                if (refusal != null) return refusal;
            }

            // ⚠️ .Equals, NOT `!=`. `NaN != NaN` is TRUE in C#, so `!=` reports an UNCHANGED NaN
            // as a change and refuses a save the operator needs in order to repair it -- the
            // trap this whole method exists to avoid, reintroduced by the obvious operator.
            if (!newTrailingDrawdown.Equals(oldTrailingDrawdown))
            {
                string refusal = RefuseTrailingDrawdown(newTrailingDrawdown);
                if (refusal != null) return refusal;
            }

            if (oldMinShadowSessions != newMinShadowSessions)
            {
                string refusal = RefuseMinShadowSessions(newMinShadowSessions);
                if (refusal != null) return refusal;
            }

            return null;
        }
    }

    /// <summary>
    /// What a config save actually did. `SaveAndReloadConfig` returned void and swallowed its
    /// own exception, so all three writers announced a success nobody had observed (`P2-119`).
    ///
    /// ⚠️ TOP-LEVEL, NOT NESTED INSIDE GuardConfigEdit, and that is not a style preference.
    /// The agent-loop patch that introduced this type nested it, the C# build stayed green, and
    /// `RiskGuardWindow.cs` -- which names `ConfigSaveResult` unqualified -- WOULD NOT HAVE
    /// COMPILED IN NINJATRADER. The window is `#if !TESTING`, so `dotnet build` compiles it to
    /// nothing and the parse gate only checks syntax; the first report would have been NT8
    /// refusing the whole Custom assembly, which stops EVERY addon loading, this guard
    /// included. The review panel considered the nesting and dismissed it on the grounds that
    /// "the type is only used internally by the patch" -- a claim about a file it could not see.
    /// </summary>
    public class ConfigSaveResult
    {
        /// <summary>True only if the file was written AND reloaded without throwing.</summary>
        public bool Saved { get; set; }
        /// <summary>Non-null: refused BEFORE writing. Nothing was persisted.</summary>
        public string Refusal { get; set; }
        /// <summary>Non-null: the write or the reload threw. Nothing reliable was persisted.</summary>
        public string Error { get; set; }
        /// <summary>Saved, but the resulting config still holds a pre-existing bad value.</summary>
        public string Warning { get; set; }
    }
}
