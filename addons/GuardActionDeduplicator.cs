// P2-107. De-duplicate guard actions where they LEAVE the guard, once, instead of inside each
// producer.
//
// WHAT THIS IS FOR, IN ONE SENTENCE: so that a condition which persists produces ONE action and
// one log line, rather than one of each per market-data tick, forever.
//
// ⚠️ WHY IT IS HERE AND NOT IN THE PRODUCER. P2-101 fixed exactly this shape inside
// EvaluateLockoutPhase: a lockout in `shadow` retried its flatten forever, because the retry's
// exit condition was "position still open" and shadow never closes it. Within the hour, and on
// the first two accounts anyone looked at, the SAME shape turned up on a different path --
// PEAK_GIVEBACK_BREACH re-emitting its flatten 7 times in ~20 seconds, per-evaluation, so with no
// spacing at all and a rate set by market data:
//
//     10:14:22  Sim-ORB  [SHADOW] Would execute action FlattenPosition triggered by PEAK_GIVEBACK_BREACH
//     10:14:25 ... 10:14:32, 10:14:33, 10:14:41, 10:14:42
//
// Two instances in one hour is the signal that the producer is the wrong place. There are five
// emission sites and any number of rules; a bound written into each one is a bound that the sixth
// site will not have. This sits on the single outbound path instead, so it covers the rules that
// exist and the rules nobody has written yet.
//
// This is the SIXTH instance of "an alarm that is always on is off" in this codebase -- see also
// P3-30's audit firing on a correctly protected account, P2-98's FILL_NOT_MEASURED firing on
// every manual fill, and P1-100's ENTRY_CANCEL asserting a cancel that shadow never performed.
//
// ── THE TWO RULES THAT SHAPE THE DESIGN ────────────────────────────────────────────────────────
//
// 1. THE RECORD IS CLEARED BY THE CONDITION RESOLVING, NEVER BY A TIMER. A time-based expiry
//    re-admits the action while the condition is still true, which is the defect again on a
//    slower clock. The observable that means "resolved" is that the producer evaluated the
//    account and did NOT ask for the action -- so Filter takes the whole batch for one scope and
//    treats ABSENCE from it as the resolution. That is why the caller must pass the accounts it
//    evaluated even when they produced nothing: a scope that is never filtered is never cleared.
//
//    ⚠️ This is also why the scope carries the PRODUCER. The AccountItemUpdate path does not
//    evaluate the lockout rules, so its batch legitimately lacks their keys; if one producer's
//    silence could clear another's record, every batch would clear almost everything and the
//    de-duplication would do nothing at all -- while still passing a test that only ever drives
//    one producer.
//
// 2. IT MUST NOT SUPPRESS A `live` RE-ATTEMPT THAT IS DOING REAL WORK. P2-101's budget of 6
//    exists because a broker can reject a flatten and the guard has to try again. So the budget
//    is read from the mode on every call: 1 outside an acting mode, 6 inside one.
//
//    ⚠️ THE 1 IS THE FIX, NOT A TUNING VALUE. In `shadow` the product is the observation, and the
//    observation is complete after one line. There is no argument for 2. (Same reasoning, same
//    number, as P2-101's out-of-live budget -- deliberately, so the two cannot drift apart in a
//    reader's head.)
//
//    Because the budget is re-read per call and not baked into the record, arming the guard to
//    `live` re-admits a key that `shadow` had already exhausted -- 1 attempt spent against a
//    budget of 6. That is the wanted behaviour and it needs no extra mechanism: the operator
//    switched to live in order for the action to happen.
//
// ⚠️ WHAT DELIBERATELY DOES NOT COME THROUGH HERE: the operator's panic buttons. TriggerManualFlatten
// and TriggerManualFlattenAll call ProcessAction(forceLive: true) directly, so pressing the button
// twice flattens twice. An operator repeating themselves is not a duplicate, and a safety control
// that ignores the second press because it recognised the first is a worse defect than the one
// this file closes. Asserted in source by the P2-107 tests.
//
// This class names no NinjaTrader type, so the harness EXECUTES it rather than grepping it -- the
// P2-27 pattern, as used by BridgeAccountResolver, BridgeFlattenPlan and BridgeLockoutGate.
using System;
using System.Collections.Generic;

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>One key's verdict from <see cref="GuardActionDeduplicator.Filter"/>.</summary>
    public sealed class ActionDedupDecision
    {
        /// <summary>The de-duplication key this verdict is about.</summary>
        public string Key = string.Empty;

        /// <summary>True when the action should be dispatched.</summary>
        public bool Admit;

        /// <summary>1-based attempt number within the current unresolved episode.</summary>
        public int Attempt;

        /// <summary>The budget the attempt was measured against, for the log line.</summary>
        public int Budget;

        /// <summary>
        /// True on the FIRST suppressed attempt of an episode and never again, so a persisting
        /// condition produces exactly one "I am holding this back" line. A silent suppression is
        /// the inverse of the defect being fixed: the operator would see neither the action nor
        /// any statement that it was withheld.
        /// </summary>
        public bool AnnounceSuppression;

        /// <summary>Human-readable reason, empty when admitted.</summary>
        public string Reason = string.Empty;
    }

    /// <summary>
    /// Per-(scope, key) "already emitted, not yet resolved" record for the guard's outbound
    /// action path. See the file header for why it lives here rather than in each rule.
    /// </summary>
    public sealed class GuardActionDeduplicator
    {
        /// <summary>Re-attempts allowed while the guard is acting. A broker can reject a flatten.</summary>
        public const int ActingBudget = 6;

        /// <summary>
        /// Attempts allowed when the guard is only observing. ONE. The observation is complete
        /// after one line; see the file header.
        /// </summary>
        public const int ObservingBudget = 1;

        private sealed class Record
        {
            public int Attempts;
            public bool Announced;
        }

        // scope -> key -> record.
        private readonly Dictionary<string, Dictionary<string, Record>> _byScope =
            new Dictionary<string, Dictionary<string, Record>>(StringComparer.Ordinal);

        /// <summary>Attempts permitted for the given mode.</summary>
        public static int BudgetFor(bool isActingMode)
        {
            return isActingMode ? ActingBudget : ObservingBudget;
        }

        /// <summary>
        /// The de-duplication key. Deliberately NOT the whole GuardAction: two flattens for the
        /// same account and instrument raised by the same rule are the same demand however many
        /// times the market ticks.
        /// </summary>
        public static string KeyFor(string accountName, string ruleId, string actionType, string instrument)
        {
            return (accountName ?? "") + "|" + (ruleId ?? "") + "|"
                 + (actionType ?? "") + "|" + (instrument ?? "");
        }

        /// <summary>
        /// Separates the producer from the account inside a scope string. U+0001 cannot occur in
        /// an NT8 account name or in any producer name, so no name can be built that collides
        /// with another scope by containing the separator.
        /// </summary>
        private const string ScopeSeparator = "\u0001";

        /// <summary>The scope within which absence means "the condition resolved".</summary>
        public static string ScopeFor(string producer, string accountName)
        {
            return (producer ?? "") + ScopeSeparator + (accountName ?? "");
        }

        /// <summary>
        /// Rule on one producer's batch for one scope. Keys present are counted against the
        /// budget; keys this scope was holding that are ABSENT are cleared, because the producer
        /// evaluated and no longer wants them.
        ///
        /// A key repeated inside one batch counts ONCE -- CoalesceActions should already have
        /// merged it, and counting duplicates would let a single batch spend the whole budget.
        /// </summary>
        /// <param name="scope">From <see cref="ScopeFor"/>. Must name one producer and one account.</param>
        /// <param name="keys">Every key this batch is asking to dispatch, in dispatch order.</param>
        /// <param name="isActingMode">Whether the guard will really execute the action.</param>
        public List<ActionDedupDecision> Filter(string scope, IList<string> keys, bool isActingMode)
        {
            var decisions = new List<ActionDedupDecision>();
            int budget = BudgetFor(isActingMode);
            scope = scope ?? "";

            Dictionary<string, Record> records;
            if (!_byScope.TryGetValue(scope, out records))
            {
                records = new Dictionary<string, Record>(StringComparer.Ordinal);
                _byScope[scope] = records;
            }

            var seen = new HashSet<string>(StringComparer.Ordinal);

            if (keys != null)
            {
                foreach (var raw in keys)
                {
                    string key = raw ?? "";
                    var decision = new ActionDedupDecision { Key = key, Budget = budget };

                    Record record;
                    if (!records.TryGetValue(key, out record))
                    {
                        record = new Record();
                        records[key] = record;
                    }

                    if (!seen.Add(key))
                    {
                        // Second occurrence within one batch. Do not spend a second attempt on
                        // it, and do not dispatch it twice either.
                        decision.Admit = false;
                        decision.Attempt = record.Attempts;
                        decision.Reason = "duplicate within one batch";
                        decisions.Add(decision);
                        continue;
                    }

                    if (record.Attempts >= budget)
                    {
                        decision.Admit = false;
                        decision.Attempt = record.Attempts;
                        decision.AnnounceSuppression = !record.Announced;
                        record.Announced = true;
                        decision.Reason = isActingMode
                            ? "already attempted " + record.Attempts + " time(s) of " + budget
                              + " and the condition has not resolved"
                            : "already reported once and the condition has not resolved;"
                              + " the guard is not acting, so repeating it adds nothing";
                        decisions.Add(decision);
                        continue;
                    }

                    record.Attempts++;
                    decision.Admit = true;
                    decision.Attempt = record.Attempts;
                    decisions.Add(decision);
                }
            }

            // Anything this scope was holding and the producer no longer asks for has resolved.
            // This is the ONLY way a record clears; see rule 1 in the file header.
            if (records.Count > 0)
            {
                var stale = new List<string>();
                foreach (var kvp in records)
                {
                    if (!seen.Contains(kvp.Key)) stale.Add(kvp.Key);
                }
                foreach (var key in stale) records.Remove(key);
            }

            return decisions;
        }

        /// <summary>
        /// Drop every record for one account across all producers. For the daily session reset,
        /// where the guard's whole view of the account starts again.
        /// </summary>
        public void ClearAccount(string accountName)
        {
            string suffix = ScopeSeparator + (accountName ?? "");
            var doomed = new List<string>();
            foreach (var scope in _byScope.Keys)
            {
                if (scope.EndsWith(suffix, StringComparison.Ordinal)) doomed.Add(scope);
            }
            foreach (var scope in doomed) _byScope.Remove(scope);
        }

        /// <summary>Drop everything. Used by the harness and by a disarm.</summary>
        public void ClearAll()
        {
            _byScope.Clear();
        }

        /// <summary>How many unresolved records are held, across every scope. For tests and diagnostics.</summary>
        public int TrackedCount
        {
            get
            {
                int total = 0;
                foreach (var kvp in _byScope) total += kvp.Value.Count;
                return total;
            }
        }
    }
}
