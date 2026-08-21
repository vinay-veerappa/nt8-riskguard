// P1-149, the strategy-side half. A configured contract cap that nothing on the ENTRY path consults
// before a RiskManagerBase strategy places an order.
//
// MEASURED 2026-08-18 (recorded against the bridge half, addons/BridgeSizingGate.cs in
// nt8-mcp-bridge), with `Sizing.MaxContractsPerAccount: 10` live in the config:
//
//     Sim101   sell 1000 MES  -> FILLED. -$1,213 of slippage on the fill alone.
//     FUNDED   sell  501 MES   -> REJECTED, by the PROP FIRM, not by us:
//              "Your maximum order quantity has been met... Limit: 60 Current: 501"
//
// The bridge/order path was fixed there. THIS file is the same decision for the OTHER order origin:
// a RiskManagerBase strategy calling RiskGatekeeper as part of its entry gate. `MaxContractsPerAccount`
// was configured, evaluated by the guard's reactive rule, rendered in the UI -- and enforced nowhere
// on the strategy-side path that can spend it.
//
// ⚠️ THE GUARD'S OWN CAP IS REAL AND IT IS REACTIVE. `RiskGuardAddOn`'s `MAX_SIZE_BREACH` fires a
// flatten when `pos.Quantity > limit` -- a predicate over a position that ALREADY EXISTS, on the
// audit sweep. The fill, and its slippage, have already happened. This file is the half that can say
// no FIRST. It does not replace the reactive rule: a position can exceed the cap without any order of
// ours having done it (a copier fill, a manual trade, a partial), and only the reactive rule sees
// those.
//
// ⚠️ A CAP MUST NOT REFUSE THE ORDER THAT CLOSES THE POSITION. It is the load-bearing rule here: if
// you are somehow long 50 against a cap of 10, a `Sell 50` is the fix, not the offence. Refusing it
// would trap the operator inside exactly the exposure the cap exists to prevent --
// [[a-lockout-must-not-trap-you]], where a lockout refused the order that would CLOSE a position.
// Strictly-reducing orders are ALWAYS allowed, whatever the cap says and whatever the position size is.
//
// ⚠️ AND THE CHECK IS ON THE RESULTING POSITION, NOT THE ORDER QUANTITY. Long 8 against a cap of 10,
// `Buy 5` is an order of 5 -- under the cap -- that leaves 13, over it. Checking only the order
// quantity passes it, and then the reactive rule flattens the whole 13 later. The two halves have to
// agree on what they measure or they disagree about the same account.
//
// ⚠️ `Position.Quantity` IS ABSOLUTE ON NT8 -- the side is `MarketPosition`, and reading the SIGN is
// `P0-96`, where the copier answered a short-cover with a Sell and DOUBLED a follower's short behind
// 1311 green tests. Everything here takes the side as a string and the quantity as a magnitude, so
// there is no sign to misread.
//
// WHY ITS OWN FILE: `RiskGatekeeper.cs` names `NinjaTrader.Cbi` types, so no test build compiles it
// (mirrors McpBridgeAddOn.cs's exclusion, P2-27) and a decision written inside it could only be
// checked by reading the text. Everything here names no NT8 type, so `RiskGuardTests.csproj` compiles
// and EXECUTES it. [[test-doubles-are-not-evidence]]. RiskGatekeeper delegates to it.
using System;

namespace NinjaTrader.NinjaScript.AddOns
{
    public class ContractCapDecision
    {
        public bool Allowed;

        /// <summary>Why it was refused. Null when allowed -- there is no reason to give.</summary>
        public string Reason;

        /// <summary>
        /// The position this order would leave behind, as a magnitude. Reported so the caller can
        /// log what it judged rather than recomputing it, and so a test can assert the arithmetic
        /// separately from the verdict -- a gate that refuses for the wrong reason still refuses.
        /// </summary>
        public int ResultingQuantity;
    }

    public static class ContractCapGate
    {
        /// <summary>
        /// Whether an order may be placed, given the cap the GUARD resolved for this account. The cap
        /// is passed in rather than read here: the guard config owns that number, and a second copy of
        /// it computed elsewhere is the defect this project keeps finding --
        /// [[a-second-reader-of-the-same-state]].
        /// </summary>
        /// <param name="maxContracts">
        /// The resolved cap. ZERO OR LESS MEANS NO CAP AND ALLOWS EVERYTHING, matching how the guard
        /// reports `MaxContractsPerAccount &lt;= 0` as "no per-account contract cap". The two must
        /// agree: a cap the inventory reports as OFF while this file enforces it would be worse than
        /// either behaviour on its own.
        /// </param>
        /// <param name="orderSide">"buy" or "sell" -- which way the ORDER trades.</param>
        /// <param name="positionSide">"Long", "Short" or "Flat" -- NT8's `MarketPosition`.</param>
        /// <param name="positionQuantity">ABSOLUTE size of the current position.</param>
        public static ContractCapDecision Evaluate(
            int maxContracts,
            int orderQuantity,
            string orderSide,
            string positionSide,
            int positionQuantity,
            string accountName,
            string instrumentName)
        {
            string acct = string.IsNullOrEmpty(accountName) ? "(unnamed account)" : accountName;
            string sym = string.IsNullOrEmpty(instrumentName) ? "(unnamed instrument)" : instrumentName;

            // A non-positive quantity is not this gate's business -- the order paths reject it on
            // their own terms -- but it must not be silently treated as "reducing" and waved past.
            if (orderQuantity <= 0)
                return new ContractCapDecision { Allowed = true, ResultingQuantity = positionQuantity };

            if (maxContracts <= 0)
                return new ContractCapDecision { Allowed = true, ResultingQuantity = positionQuantity };

            int held = positionQuantity < 0 ? -positionQuantity : positionQuantity;
            bool flat = held == 0
                || string.IsNullOrEmpty(positionSide)
                || positionSide.Equals("Flat", StringComparison.OrdinalIgnoreCase);

            bool longNow = !flat && positionSide.Equals("Long", StringComparison.OrdinalIgnoreCase);
            bool buying = !string.IsNullOrEmpty(orderSide)
                && orderSide.Equals("buy", StringComparison.OrdinalIgnoreCase);

            bool opposes = !flat && (longNow != buying);

            // THE ANTI-TRAP RULE, and it comes before every other test on purpose. A strictly
            // reducing order lowers exposure no matter how large it is, so the cap has nothing to
            // say about it. Placed first so that no later condition can accidentally refuse an exit.
            if (opposes && orderQuantity <= held)
            {
                return new ContractCapDecision
                {
                    Allowed = true,
                    ResultingQuantity = held - orderQuantity
                };
            }

            int resulting = opposes ? orderQuantity - held : held + orderQuantity;

            if (resulting <= maxContracts)
                return new ContractCapDecision { Allowed = true, ResultingQuantity = resulting };

            string position = flat
                ? "flat"
                : (longNow ? "long " : "short ") + held;

            // The refusal names the cap, what was asked, what it would leave, and -- when one
            // exists -- the largest order that WOULD be accepted. A refusal that does not say what
            // to do instead is a refusal the caller has to guess its way out of.
            int allowance = opposes ? held + maxContracts : maxContracts - held;
            string remedy = allowance > 0
                ? " The largest " + (buying ? "buy" : "sell") + " that would be accepted is "
                  + allowance + "."
                : " No order in this direction is accepted while the position is this size; reduce"
                  + " it first, which is never refused.";

            return new ContractCapDecision
            {
                Allowed = false,
                ResultingQuantity = resulting,
                Reason = "Order refused: " + orderQuantity + " contract(s) of " + sym + " on '" + acct
                    + "' would leave a position of " + resulting + ", over the configured cap of "
                    + maxContracts + " (MaxContractsPerAccount). Currently " + position + "."
                    + remedy
            };
        }
    }
}
