// P0-182, the decision half. `RiskManagerAddOn.OnExecutionUpdate` called
// `RiskGatekeeper.ResetDay(account, fill.Date)` on EVERY execution event whenever the
// stored state's TradingDate differed from the fill's date. There was no monotonic
// guard, so a STALE fill -- a broker replay, a re-subscription replay, a late print --
// dated the day BEFORE the stored state moved the state BACKWARD (9/1 -> 8/31), and the
// next current-dated event moved it forward again. On 2026-09-01 (firm boundary 22:00
// UTC + NT8 restart + account re-subscription) account LFE02559938020006 produced 44+
// alternating `new session 8/31/2026` / `new session 9/1/2026` resets in ONE SECOND,
// each with a SaveState file write, and wedged NT8's UI thread (the chart hang, 1% CPU,
// nt_charts timing out while file-backed bridge reads worked).
//
// THE RULE is four lines and pure: a session reset may move the trading date FORWARD,
// or land on the SAME date (a re-detect of today is a no-op, not an error); it must
// never move BACKWARD. A backward "reset" is not a new day -- it is stale data, and
// stale data must be IGNORED (dropped + reported), never applied. Returning a verdict
// the caller can act on means the state-mutating caller (RiskGatekeeper, which names
// NinjaTrader.Cbi types and is therefore not compiled into the test build) stays thin
// while this file carries all the decisions -- the ContractCapGate split (P1-149).
//
// WHY A VERDICT OBJECT, NOT A BOOL: a refusal for the right reason is what makes the
// fix auditable. The caller logs the verdict verbatim; a test asserts the reason
// separately from the outcome -- a gate that refuses for the wrong reason still refuses.
using System;

namespace NinjaTrader.NinjaScript.AddOns
{
    public class SessionResetDecision
    {
        public bool Apply;

        /// <summary>Why, as a fixed token: "new-day" | "same-day-noop" | "stale-date-refused". Null when Apply is true and this is a genuine new day.</summary>
        public string Reason;

        /// <summary>The date the state is on if this verdict is applied. Reported so a test can assert the arithmetic separately from the verdict.</summary>
        public DateTime EffectiveDate;

        /// <summary>The state's date if the verdict is REFUSED (the stored date). Null when Apply is true. Diagnostic for the refusal log line.</summary>
        public DateTime? StoredDate;

        /// <summary>The fill/event date that triggered the evaluation. Diagnostic.</summary>
        public DateTime EventDate;
    }

    public static class SessionResetGate
    {
        /// <summary>
        /// Whether a session reset may be applied. `storedDate` is the state's current
        /// TradingDate; `eventDate` is the date on the triggering execution/event.
        /// A reset is applied only when it moves the date strictly FORWARD, or is a
        /// same-day re-detect (no-op). A BACKWARD move is refused as stale data.
        /// </summary>
        public static SessionResetDecision Evaluate(DateTime storedDate, DateTime eventDate)
        {
            var d = new SessionResetDecision
            {
                StoredDate = storedDate,
                EventDate  = eventDate,
            };

            if (eventDate.Date > storedDate.Date)
            {
                d.Apply         = true;
                d.Reason        = "new-day";
                d.EffectiveDate = eventDate.Date;
                return d;
            }

            if (eventDate.Date == storedDate.Date)
            {
                // A same-day re-detect is a benign no-op: nothing changes, no reset, no save.
                d.Apply         = false;
                d.Reason        = "same-day-noop";
                d.EffectiveDate = storedDate.Date;
                return d;
            }

            // eventDate < storedDate: a stale/replayed event. Refuse; the caller drops it.
            d.Apply         = false;
            d.Reason        = "stale-date-refused";
            d.EffectiveDate = storedDate.Date;
            return d;
        }
    }
}