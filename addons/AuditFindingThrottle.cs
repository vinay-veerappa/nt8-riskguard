// P2-108. The FSM audit's findings are LogEvents with no action behind them, so nothing bounded
// them. Measured on the deployed box under Market Replay, 2026-08-15 -- one position with no stop,
// guard in `shadow`, sampled every 30 seconds:
//
//     t+30s   NAKED_POSITION=3    ACTION_SUPPRESSED=0
//     t+60s   NAKED_POSITION=6    ACTION_SUPPRESSED=0
//     t+90s   NAKED_POSITION=9    ACTION_SUPPRESSED=0
//     t+120s  NAKED_POSITION=12   ACTION_SUPPRESSED=0
//
// Perfectly linear: one per 10 seconds, indefinitely, for as long as the position is open. 180 of
// them sat in the log when the ticket was filed.
//
// ⚠️ `ACTION_SUPPRESSED = 0` IS THE LOAD-BEARING NUMBER. `P2-107` built `GuardActionDeduplicator`
// and routed all five emission sites through `DispatchActions` -- and it cannot help here, because
// these findings are not actions. They are `LogEvent` calls on a timer, on a path the dispatcher
// never sees. The zero proves it rather than assuming it.
//
// ⚠️ AND THE CLASS IS BIGGER THAN THE TICKET. `P2-108` names NAKED_POSITION. The audit emits
// THREE findings from the same loop on the same timer -- NAKED_POSITION, ORPHAN_STOP and
// FSM_DIVERGENCE -- and all three are unbounded. Fixing only the one that was measured would leave
// two identical defects one `foreach` apart, which is how `P1-90` reached eight sites.
//
// SEVENTH INSTANCE OF *an alarm that is always on is off*. A line every ten seconds is not a
// warning, it is weather: it buries every other line in the file, and the operator learns to scroll
// past the exact text that means "you are holding an unprotected position".
//
// FOUR THINGS IN HERE ARE LOAD-BEARING, and three of them are `P2-101`/`P2-107` restated because
// those tickets paid for them:
//
//   1. THE RECORD CLEARS WHEN THE CONDITION RESOLVES, NEVER ON A TIMER. A time-based expiry
//      re-admits while the finding is still true -- the same defect on a slower clock. So the
//      caller passes every key it EVALUATED, including the healthy ones, and a key that was
//      evaluated and did not fire is cleared. Attach a stop, and the next naked position on that
//      instrument reports again immediately.
//
//   2. THE BUDGET IS RE-READ FROM THE MODE ON EVERY PASS: 1 observing, 6 acting. ⚠️ **The 1 is
//      the fix, not a tuning value** -- in `shadow` the product IS the observation and it is
//      complete after one line. Re-reading rather than caching means arming to `live` re-admits a
//      key `shadow` had exhausted, which is the behaviour you want the moment the guard can act.
//
//   3. THE KEY CARRIES THE FINDING TYPE as well as account and instrument. Without it,
//      NAKED_POSITION resolving would clear ORPHAN_STOP's record for the same instrument and the
//      throttle would do nothing -- **while every single-finding test passed**. That is `P2-107`'s
//      producer-scope lesson verbatim.
//
//   4. SUPPRESSION IS ANNOUNCED EXACTLY ONCE. Trading a screaming alarm for a silent one is not a
//      fix, it is the same defect inverted: the operator would have no way to tell "resolved" from
//      "still true, still unfixed, no longer mentioned". `FirstSuppression` returns true on the
//      single pass where the budget runs out, so the caller emits one AUDIT_FINDING_SUPPRESSED
//      line naming the finding, the budget and the mode -- and nothing after.
//
// WHY IT NAMES NO NT8 TYPE: it takes strings and ints, so `tests/RiskGuardTests.csproj` compiles
// and EXECUTES it (`P2-27`). The audit that calls it is full of `Account`, `Position` and `Order`,
// none of which appear here.
using System;
using System.Collections.Generic;
using System.Linq;

namespace NinjaTrader.NinjaScript.AddOns
{
    public sealed class AuditFindingThrottle
    {
        /// <summary>
        /// Lines allowed per finding while the guard is NOT in an acting mode.
        ///
        /// ⚠️ ONE, and this is the fix rather than a tuning value. In `shadow` the guard's entire
        /// product is the observation, and the observation is complete after a single line. The
        /// same reasoning and the same number as <c>P2-101</c>'s flatten-retry budget and
        /// <c>P2-107</c>'s action budget; if this ever grows, the argument has to be re-made from
        /// scratch, because "a bit more logging is harmless" is what produced the defect.
        /// </summary>
        public const int ObservingBudget = 1;

        /// <summary>
        /// Lines allowed per finding while the guard IS acting. Higher than
        /// <see cref="ObservingBudget"/> because in `live` a finding that persists across several
        /// passes means remediation is failing, and that IS worth repeating -- but bounded, so it
        /// cannot become weather.
        /// </summary>
        public const int ActingBudget = 6;

        private readonly Dictionary<string, int> _emitted =
            new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        private readonly HashSet<string> _announcedSuppression =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        /// <summary>The budget for the current mode. Re-read every pass, never cached.</summary>
        public static int BudgetFor(bool isActingMode)
        {
            return isActingMode ? ActingBudget : ObservingBudget;
        }

        /// <summary>
        /// The throttle key. Carries the FINDING TYPE, not just the subject — see note 3 in the
        /// header: without it one finding resolving silently clears another's record.
        /// </summary>
        public static string KeyFor(string findingType, string account, string instrument)
        {
            return (findingType ?? "?") + "|" + (account ?? "?") + "|" + (instrument ?? "?");
        }

        /// <summary>
        /// The account a key belongs to. The clearing rule is keyed on the ACCOUNT the audit
        /// examined, not on the individual finding — see the header note on why.
        /// </summary>
        public static string AccountOf(string key)
        {
            if (string.IsNullOrEmpty(key)) return string.Empty;
            var parts = key.Split('|');
            return parts.Length >= 2 ? parts[1] : string.Empty;
        }

        /// <summary>
        /// Decide what this audit pass may log.
        ///
        /// <paramref name="examinedAccounts"/> is every account the audit successfully enumerated
        /// this pass — positions AND orders. <paramref name="firedKeys"/> is what is currently a
        /// finding. Any tracked key belonging to an examined account that did NOT fire has
        /// resolved, and its record is dropped.
        ///
        /// ⚠️ THE SCOPE IS THE ACCOUNT, NOT THE KEY, AND THAT IS THE WHOLE CORRECTION. This was
        /// first written taking `evaluatedKeys` — keys the audit had looked at — which sounds
        /// stricter and is wrong, because the audit builds those keys by iterating the account's
        /// OPEN POSITIONS. When a naked position is resolved the way it is resolved 99 times out
        /// of 100 — the position CLOSES — there is no position left to iterate, the key is never
        /// evaluated, and the record lives forever. **The alarm mutes itself permanently on the
        /// most common recovery path.**
        ///
        /// ⚠️ AND EVERY TEST PASSED. Eight unit tests and 8/8 mutants, including one specifically
        /// asserting that an unevaluated key keeps its count — true for a disconnected account,
        /// and exactly backwards for a closed position. It was caught by driving the deployed box:
        /// close the position, re-open it, and NAKED_POSITION never came back. *The suite could
        /// not distinguish the two cases because nothing in it closed a position.*
        ///
        /// The account scope keeps the protection the key scope was reaching for: a pass that
        /// examined NO accounts clears NOTHING, so a connection blip cannot re-admit the backlog.
        /// </summary>
        public IList<string> Admit(IEnumerable<string> examinedAccounts, IEnumerable<string> firedKeys,
                                   int budget)
        {
            var examined = new HashSet<string>(examinedAccounts ?? Enumerable.Empty<string>(),
                                               StringComparer.OrdinalIgnoreCase);
            var fired = new List<string>(firedKeys ?? Enumerable.Empty<string>());
            var firedSet = new HashSet<string>(fired, StringComparer.OrdinalIgnoreCase);

            // (1) THE CONDITION RESOLVED -> the record goes. A tracked key whose ACCOUNT was
            // examined and which did not fire means the audit looked at that account and found
            // nothing wrong there: a stop was attached, or the position closed. Keys on accounts
            // the audit could not examine keep their counts, so a disconnected provider cannot
            // re-admit the whole backlog on reconnect.
            foreach (var key in _emitted.Keys
                         .Where(k => examined.Contains(AccountOf(k)) && !firedSet.Contains(k))
                         .ToList())
            {
                _emitted.Remove(key);
                _announcedSuppression.Remove(key);
            }

            var admitted = new List<string>();
            foreach (var key in fired)
            {
                int count;
                _emitted.TryGetValue(key, out count);
                if (count < budget)
                {
                    _emitted[key] = count + 1;
                    admitted.Add(key);
                }
                else
                {
                    _emitted[key] = count + 1;
                }
            }
            return admitted;
        }

        /// <summary>
        /// True exactly once per key, on the pass where it first exceeds its budget. The caller
        /// emits one line saying the finding is still true and has gone quiet — note 4 in the
        /// header. Returns false forever after, until the condition resolves and clears the record.
        /// </summary>
        public bool FirstSuppression(string key, int budget)
        {
            int count;
            if (!_emitted.TryGetValue(key, out count)) return false;
            if (count <= budget) return false;
            return _announcedSuppression.Add(key);
        }

        /// <summary>How many times a key has fired, admitted or not. For the suppression line.</summary>
        public int TimesFired(string key)
        {
            int count;
            _emitted.TryGetValue(key, out count);
            return count;
        }

        /// <summary>Live record count. Used by tests to prove records are cleared, not leaked.</summary>
        public int TrackedCount { get { return _emitted.Count; } }
    }
}
