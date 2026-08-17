// P1-133. ONE definition of what an ATM bracket's three legs are CALLED, and the only place this
// add-on is allowed to look one of them up.
//
// WHY THE NAME AND NOT `Order.OrderId`. NT8 assigns a GUID when an order is submitted and the
// BROKER REPLACES `Order.OrderId` with its own id once it accepts. The NT8 Simulator never re-ids
// anything. Measured on one box in one minute, 2026-08-16:
//
//     Sim101      "orderId": "2f515ed0f89e4ab08f549fa356614236"   <- still the GUID
//     Provider31  "orderId": "613562531447"                        <- the broker's id
//
// So a lookup keyed on the id captured at placement works on `Sim101` and fails on every real
// connection. `DynamicAtmManager` did exactly that in five places, and breakeven and trailing
// stops had therefore never once moved on a live or funded account -- measured on the funded 50K,
// where the stop was resting `Working` at the recorded price and only the identity was wrong.
//
// The NAME is a value THIS add-on sets at placement, and the broker does not touch it: the same
// live run returned `name: "Stop_15bc730b"` for the order whose id had been replaced. A value we
// own cannot vary by provider; a value the broker owns will.
//
// ⚠️ THE REST OF THIS ADDON ALREADY KNEW, IN WRITING, IN THREE PLACES -- `RiskGuardModels.cs`
// tracks recognised stops by object reference, `TradeCopierEngine.OrderReferenceComparer` says
// "`Order.OrderId` must not be used as a key", and `CopierReconciler` says it a third time.
// `DynamicAtmManager` was the sole holdout. A convention documented in three files is not a
// convention the fourth follows, and nothing compared them.
//
// ⚠️ AND THE COPIER'S COMMENT PREDICTED THIS DEFECT: "no test would catch it, because the test
// stub hands out a stable GUID per order." It was right for two years. The regression test is
// therefore in the STUB -- `ReIdAsARealBrokerWould` -- not only in the manager. A test that passes
// under both a stable and a re-issued id is evidence about neither.
//
// ⚠️ `ActiveBracket.EntryOrderId` / `StopOrderId` / `TargetOrderId` still exist and are still
// reported in the bridge's API payload. They are REPORTING FIELDS ONLY and must never be fed to a
// lookup again.
//
// ⚠️ NO TOLERANT `OrderId == key || Name == key` FALLBACK HERE, deliberately. The bridge's
// `McpBridgeAddOn.cs` lookup does match all three identities, correctly, because it serves an id a
// CALLER supplied and cannot know which kind it is. This class placed the order itself and knows
// the name it chose, so a fallback would only reintroduce the stale-id path under a longer
// condition.
//
// It names `Account` and `Order` and nothing else from NT8, both of which the test build stubs, so
// every line here is EXECUTED by tests rather than merely scanned (P2-27). `tools/sync_nt8.py`
// globs `addons/*.cs`, so it needs no registration to ship.
using System;
using NinjaTrader.Cbi;

namespace NinjaTrader.NinjaScript.AddOns
{
    public static class AtmOrderIdentity
    {
        public static string EntryName(string bracketId)
        {
            return "AtmEntry_" + bracketId;
        }

        public static string StopName(string bracketId)
        {
            return "Stop_" + bracketId;
        }

        public static string TargetName(string bracketId)
        {
            return "Target_" + bracketId;
        }

        /// <summary>
        /// The ONE comparison. Both finders below and the entry-liveness check in
        /// `DynamicAtmManager` all route through here, so there is a single answer to "is this our
        /// leg?" rather than four hand-inlined copies that can drift apart.
        ///
        /// ⚠️ A blank name matches NOTHING. The alternative -- treating blank as "any" -- would
        /// make a bracket with an unset id match the FIRST order on the account, which on a funded
        /// account is somebody else's working order and would be moved or reported as ours.
        /// Ordinal, because these strings are constructed by this file and are not human text.
        /// </summary>
        public static bool NameMatches(Order order, string name)
        {
            if (order == null || string.IsNullOrWhiteSpace(name)) return false;
            return string.Equals(order.Name, name, StringComparison.Ordinal);
        }

        /// <summary>
        /// The leg by that name whatever state it is in, or null. Used for the DIAGNOSTIC half of
        /// a failed stop move: P1-130 established that "absent entirely" and "present but no
        /// longer live" are not the same news and must not print the same line.
        /// </summary>
        public static Order FindByName(Account account, string name)
        {
            if (account == null || account.Orders == null) return null;
            foreach (Order order in account.Orders)
            {
                if (NameMatches(order, name)) return order;
            }
            return null;
        }

        /// <summary>
        /// The leg by that name that is still live, or null.
        ///
        /// Liveness is `RiskGuardAddOn.OccupiesSlot`, the guard's own shared predicate, and NOT a
        /// hand-written list of states. P1-130 was a hand-written list here (`Working` only) that
        /// disagreed with the reader ten lines below it, and P1-131 was the same mistake in the
        /// bridge. An unrecognised state must not silently become "not here".
        /// </summary>
        public static Order FindLiveByName(Account account, string name)
        {
            if (account == null || account.Orders == null) return null;
            foreach (Order order in account.Orders)
            {
                if (NameMatches(order, name) && RiskGuardAddOn.OccupiesSlot(order.OrderState))
                    return order;
            }
            return null;
        }
    }
}
