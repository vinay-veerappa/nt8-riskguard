# TICKET T1: P0-63: Account.Change() is accepted and silently ignored, so the mirrored stop has never trailed -- verify the read-back and fall back to cancel-then-create
## Defect
`Account.Change()` on a `provider: Simulator` account does NOTHING. The order transitions ChangeSubmitted -> Accepted and keeps its ORIGINAL price and quantity. No exception, no rejection, no log line. Not quantity-specific, not OCO-specific, not ATM-specific, not stop-specific.

Established 2026-08-10 by an isolated probe on `Sim_All_Day_ORB`, an account in no copier relationship so nothing else could have been reverting it:
  - standalone StopMarket, no OCO, qty 1 -> 2  ==> stayed qty 1
  - same order, price only, 29700 -> 29695     ==> stayed 29700
  - resting Limit 300 points from market, 29500 -> 29550 ==> stayed 29500
The third is decisive: a resting limit that far from the market has no trigger-proximity or margin rule to blame.

Retroactively confirmed on the copier's own path: stop `34410` was CREATED at 29753.5, logged `BRACKET_MODIFIED ... stop moved to 1@29754.5`, and ended at 29753.5. The modify did nothing and the log claimed it had.

Why this was believed to work: `/api/connections` reports `OrderChange` in `allFeatures` for `Sim101`, but that is the CONNECTION's capability (TPT, which supplies data) while the ACCOUNT's `provider` is `Simulator` -- NT8's internal sim engine handles the orders and ignores Change(). Advertised by the connection is not honoured by the provider.

WHAT IT COSTS. Every account this project has validated on is a Simulator account, so the mirrored stop has NEVER trailed once. A leader trailing its stop up to lock in profit leaves the follower carrying the ORIGINAL risk for the life of the trade, while `BRACKET_MODIFIED` logs success. Section 4o's entire 'modify in place, so there is no unprotected window' design is a no-op that reports otherwise. This is the highest open defect in the backlog.

STILL UNRESOLVED, DELIBERATELY: whether Change() works on a non-Simulator provider. The funded accounts are `Provider31` and were Disconnected. Answering it means placing a real order on a funded account, which the operator has declined. Remedy 3 is correct either way and does not need the answer.

THERE IS A THIRD CALL SITE the plan's 'Where' clause never named: `DynamicAtmManager.ModifyStopPrice` at addons/DynamicAtmManager.cs:622. It is OUT OF SCOPE for this ticket -- it has no settle hook and no bracket state to hang a pending request on, so it needs its own design. Do not touch it here.
## Required change
Remedy 3, which is the operator's decision (handover 5.5) and is not open for re-litigation: after a Change(), verify the order actually took the new values, and fall back to cancel-then-create when it did not.

1. RECORD WHAT WAS ASKED, separately from the Order object. Add per-leg fields to `FollowerBracket` holding the price and quantity a Change() requested (and a flag or a NaN sentinel for 'nothing asked'). You cannot recover this from the Order: the engine already wrote the desired values onto it, so the object cannot tell you what the broker holds. Set these under `_lock` at the same point `bracket.WorkingStop = toModify` is set, i.e. after Change() returns without throwing.

2. VERIFY WHEN THE LEG SETTLES, NOT INLINE. `OnFollowerOrderUpdate` is the hook. A leg that has left ChangeSubmitted/ChangePending satisfies `RiskGuardAddOn.AcceptsModification`, and there is already a block there for exactly that transition (P0-61's `ReDriveDeferredLeg`). Verification has to happen in that block, BEFORE the `OccupiesSlot` early return -- a Working order occupies a slot, so the existing return would drop the event and the check would never run.

   A SYNCHRONOUS READ-BACK IMMEDIATELY AFTER Change() IS WRONG AND WILL FAIL THE ACCEPTANCE TESTS. Live, the order still carries the desired values at that point; the revert arrives with the settle event. This is the whole reason the stub applies the revert in `SettleChange` and not in `Change`.

3. ON MISMATCH: log it -- this is the 'turns a silent no-op into an observable one' half, and it is half the value of the ticket -- and re-drive the leg through cancel-then-create. Both halves of the fallback must happen: cancelling without creating is a naked follower, which is the failure the existing fallback in `SyncFollowerStopOnce`'s catch block already guards against. Reuse that path rather than writing a second one.

4. STOP ASKING A PROVIDER THAT HAS ALREADY REFUSED. Once a no-op has been observed on an account, later adjustments on that account must go straight to cancel-then-create without another doomed Change(). Keep this at ACCOUNT level (a `HashSet<string>` on the engine, guarded by `_lock`), not per bracket: the provider is a property of the account, and re-learning it per instrument wastes a round trip per instrument during which the stop is stale. This is what `TestBracket_P0_63_AFurtherTrailDoesNotWaitOnAnotherIgnoredChange` pins, and it discriminates: a fix that re-asks every time leaves the broker holding step ONE's price and fails.

5. DO NOT REGRESS MODIFY-IN-PLACE where the provider honours it. 'Always cancel-then-create' is remedy 1, it was considered, and it was NOT chosen: it reopens the naked window on the risk leg on every trail step, which is the defect section 4o shipped modify-in-place to close. `TestBracket_P0_63_AnHonouredChangeStillModifiesInPlace` is green at baseline and must stay green -- it asserts exactly one COPIER_STOP order is ever created.

6. BOTH LEGS. The stop and the target each have their own Change() site (`SyncFollowerStopOnce`, `SyncFollowerTargetOnce`) and each needs its own recorded request and its own verification. Keep them asymmetric in the way this file already is: the stop is risk and always wins, the target is upside and must never delay or disturb the stop. Do not let a target verification make the stop leg wait.

7. The existing `StopAttempts`/`TargetAttempts` budgets exist to stop a persistently-refusing broker turning re-submission into an order flood. A no-op that is detected and replaced must not be able to loop against those budgets forever -- check what the counters do on this new path before you assume they are fine.
## Additional context you must respect
The stop sync's Change() is at addons/TradeCopierEngine.cs:1993 inside `SyncFollowerStopOnce`; the target's is at :2312 inside `SyncFollowerTargetOnce`. Both sit in a try/catch whose catch already implements the cancel-then-create fallback for the case where Change() THROWS -- that is `SimulateChangeFailure` in the stub, and it is a different case from this one. This ticket adds the case where Change() does not throw and does not work.

`RiskGuardAddOn.AcceptsModification(OrderState)` (addons/RiskGuardAddOn.cs:2370) already documents a RELATED but distinct NT8 behaviour: a SECOND Change() while one is in flight is dropped AND reverts the order. That is P0-61 and it is already fixed. P0-63 is the FIRST change being ignored. Do not conflate them, and do not weaken P0-61's deferral -- `TestBracket_P0_61_ADeferredChangeIsReappliedWhenTheLegSettles` must stay green.

The OCO rule, which the cancel-then-create path depends on: an id can be JOINED while its group still has a live member, and is REJECTED once every leg has gone terminal. `ResolveOcoIdForRecreatedLeg` already implements this. A re-created leg that reuses a retired group id is rejected by the broker, which is a naked follower.
## Regions to rewrite
### REGION id="EngineFields"  file=addons/TradeCopierEngine.cs  lines 135-135
Purpose: declare the account-level 'this provider ignores Change()' set here, beside the _lock that must guard it. kind=line: a field declaration has no brace body, so the default decl expansion would run to the end of the class. Emit this line back unchanged plus the new declaration.
```csharp
        private readonly object _lock = new object();
```
### REGION id="FollowerBracket"  file=addons/TradeCopierEngine.cs  lines 1408-1471
Purpose: add the per-leg 'what the last Change() asked for' fields here, beside StopChangeDeferred/TargetChangeDeferred which are the P0-61 analogue
```csharp
        private class FollowerBracket
        {
            public string RelationshipId;
            public string FollowerAccountName;
            public string InstrumentFullName;
            public MarketPosition FollowerSide = MarketPosition.Flat;
            public int FollowerQuantity;
            public double FollowerEntryPrice = double.NaN;   // the anchor; NaN until the follower fills
            // SIGNED offset from the leader's average entry to its stop, in points.
            // Negative = stop below entry, positive = above. NaN until the leader's stop appears.
            // It must stay signed: a leader trailing its stop INTO PROFIT puts the stop above
            // entry on a long, and an absolute distance would mirror that as a loss of the same
            // size on the follower -- turning the leader's locked-in gain into open risk.
            public double StopOffset = double.NaN;
            public Order WorkingStop;                        // the follower's live protective order

            // In-flight reservation for the bracket stop sync. Set under _lock before the first
            // broker call and cleared exactly once in a finally, so a second sync arriving while
            // one is between _lock and Submit sees the reservation and backs off.
            public bool StopInFlight;

            // Set under _lock by a sync that backed off because StopInFlight was true. The sync
            // holding the reservation re-drives the sync after its broker work resolves, so the
            // newer size/price is not dropped.
            public bool StopResyncOwed;

            // Bounded re-submission. Raised by review of the first implementation: if Submit
            // threw, or the broker rejected the stop moments later, WorkingStop ended up null
            // with a perfectly valid offset and NOTHING re-triggered submission -- the follower
            // stayed naked for the life of the position. Re-submission fixes that, and the
            // counter is what stops a persistently-rejecting instrument turning it into an
            // order flood (the failure mode P2-46 and the flood cluster already cost us once).
            public int StopAttempts;

            // P0-9 item (1). SIGNED offset from the leader's average entry to its PROFIT TARGET,
            // same convention and same reason as StopOffset. NaN until the leader's target
            // appears -- a leader with no target simply leaves this NaN and the follower gets a
            // stop only, which is exactly the behaviour that shipped before this existed.
            public double TargetOffset = double.NaN;
            public Order WorkingTarget;

            // The target leg carries its own reservation, budget and owed-flag rather than
            // sharing the stop's. Sharing would let an in-flight target sync make the RISK leg
            // wait, which is the wrong way round: upside must never delay protection.
            public bool TargetInFlight;
            public bool TargetResyncOwed;
            public int TargetAttempts;

            // The OCO id both legs currently belong to. Assigned when the first leg is created
            // and joined by the second, so the follower's target and stop cancel each other the
            // way the leader's do. Re-minted only where the group may have gone terminal --
            // see ResolveOcoIdForRecreatedLeg.
            //
            // The stop carries an id even when the bracket has no target. A group of one is
            // harmless, and it is what lets a later target JOIN rather than forcing the
            // protective stop to be cancelled and re-created into a new group.
            public string OcoId;

            // P0-61. A sync computed a new price/size for this leg while a change against it was
            // already in flight, so it declined to act. Cleared and re-driven when the leg
            // settles (ReDriveDeferredLeg). NOT the same as *ResyncOwed -- see that method.
            public bool StopChangeDeferred;
            public bool TargetChangeDeferred;
        }
```
### REGION id="SyncFollowerStopOnce"  file=addons/TradeCopierEngine.cs  lines 1860-2104
Purpose: the risk leg's Change() at :1993, its success log (which currently claims 'no cancel/replace, so no unprotected window' about a no-op), and the cancel-then-create fallback to reuse
```csharp
        private void SyncFollowerStopOnce(Account followerAcc, Instrument instrument, FollowerBracket bracket)
        {
            if (followerAcc == null || instrument == null || bracket == null) return;

            DesiredBracket desired;
            var actions = DecideLegActions(
                followerAcc, instrument, bracket, CopierBracketReconciler.OwnedStopName,
                false, out desired);
            if (desired == null || actions.Count == 0) return;

            // ---- the position is gone, or is not the one this bracket was built for ----
            //
            // Every owned leg is Forbidden here, and the reconcile has already said so. The
            // bracket is stood down as well: it must not go on believing it protects something.
            if (!desired.HasPosition)
            {
                lock (_lock) { bracket.FollowerQuantity = 0; bracket.FollowerSide = MarketPosition.Flat; }
                foreach (var a in actions)
                {
                    if (a.Verb != ReconcileVerb.Cancel) continue;
                    try { followerAcc.Cancel(new[] { a.Subject }); } catch { }
                }
                NinjaTrader.Code.Output.Process(
                    $"[CopierEngine] BRACKET_ABORTED_FLAT: {followerAcc.Name} {instrument.FullName}: {desired.Reason}; no stop placed.",
                    PrintTo.OutputTab1);
                return;
            }

            // ---- duplicates go first, whatever happens to the keeper ----
            //
            // This is the action the old sync could not produce at all, and the reason this
            // path was rewritten. Cancelling a duplicate is not a submission, so it does not
            // spend the attempt budget: refusing to clean up because a leg has been rejected
            // three times would leave two stops behind one position (P1-56 -- qty 1 AND qty 2
            // behind 2 lots, which FLIPS the follower when both fire).
            var keeperActions = new List<ReconcileAction>();
            foreach (var a in actions)
            {
                bool isDuplicateSweep = a.Verb == ReconcileVerb.Cancel
                    && a.Reason != null && a.Reason.StartsWith("duplicate");
                if (!isDuplicateSweep) { keeperActions.Add(a); continue; }
                try
                {
                    followerAcc.Cancel(new[] { a.Subject });
                    CopierLog(followerAcc.Name, "BRACKET_DUPLICATE_CANCELLED",
                        $"{instrument.FullName}: {a.Reason}. The event-driven sync could not see this leg "
                        + "at all -- it read one cached Order reference and never enumerated the account.");
                }
                catch (Exception dex)
                {
                    CopierLog(followerAcc.Name, "BRACKET_DUPLICATE_CANCEL_FAILED",
                        $"{instrument.FullName}: {dex.Message}. TWO protective stops may still be working; "
                        + "the follower will be FLIPPED if both fire.");
                }
            }
            if (keeperActions.Count == 0) return;

            // P0-61. A change against this leg is already in flight, so the broker must not be
            // touched this pass -- NT8 drops the second change AND reverts the order. But the
            // newer instruction must not be LOST either, or the leg keeps the old price and size
            // for the life of the position, which is the same under-covered follower by a quieter
            // route. `ReDriveDeferredLeg` re-applies it when the leg settles.
            //
            // Its own flag, NOT `StopResyncOwed`: that one is consumed by SyncFollowerStop's pass
            // loop the instant it is set, which re-drives while the leg is still mid-change and
            // burns the pass budget deferring. See ReDriveDeferredLeg.
            foreach (var a in keeperActions)
            {
                if (a.Verb != ReconcileVerb.Defer) continue;
                lock (_lock) { bracket.StopChangeDeferred = true; }
                CopierLog(followerAcc.Name, "BRACKET_DEFERRED",
                    $"{instrument.FullName}: {a.Reason}");
                return;
            }

            Order toModify = null;
            Order toCancel = null;
            bool wantsCreate = false;
            foreach (var a in keeperActions)
            {
                if (a.Verb == ReconcileVerb.Modify) toModify = a.Subject;
                else if (a.Verb == ReconcileVerb.Cancel) toCancel = a.Subject;
                else if (a.Verb == ReconcileVerb.Create) wantsCreate = true;
            }

            double stopPrice = desired.Stop.Price;
            int qty = desired.Stop.Quantity;
            OrderAction action = desired.Stop.Action;

            lock (_lock)
            {
                if (bracket.StopAttempts >= MaxBracketStopAttempts)
                {
                    // Bounded: keep retrying a broker that will not accept the order and the
                    // copier becomes the order flood it was hardened against.
                    return;
                }
                bracket.StopAttempts++;
            }

            var livePos = followerAcc.Positions.FirstOrDefault(p =>
                p.Instrument != null &&
                p.Instrument.FullName.Equals(instrument.FullName, StringComparison.OrdinalIgnoreCase));
            if (livePos == null) return;

            try
            {
                // Outside the lock: Cancel/Change/CreateOrder/Submit are broker calls, and holding
                // _lock across them is the P1-10/P1-35 violation.

                // Re-clamped to the live position one last time. `desired.Quantity` was already
                // clamped when it was computed, but the position can move between the decision
                // and here, and a stop larger than the position FLIPS it on trigger.
                int liveQty = Math.Min(qty, livePos.Quantity);

                // A leader trailing its stop is the ordinary case, and cancel-then-create left the
                // follower unprotected on EVERY trail step, between the cancel and the new order's
                // acceptance. Modify the working order instead: one order, no window.
                //
                // The original P0-9 note said "cancel-then-replace, not modify", to stop a stale
                // stop working beside a new one -- that over-covers and flips the follower when
                // both fire. Change() cannot produce that state: there is only ever one order.
                // Verified available: the connection serving every account here advertises the
                // OrderChange feature (/api/connections). Any failure falls through to the
                // cancel-then-create path below, so an unsupporting connection degrades rather
                // than breaks.
                //
                if (toModify != null)
                {
                    try
                    {
                        toModify.StopPrice = stopPrice;
                        toModify.Quantity = liveQty;
                        followerAcc.Change(new[] { toModify });

                        lock (_lock) { bracket.WorkingStop = toModify; }

                        CopierLog(followerAcc.Name, "BRACKET_MODIFIED",
                            $"{instrument.FullName} stop moved to {liveQty}@{stopPrice} in place "
                            + $"(leader offset {bracket.StopOffset:+0.##;-0.##}, follower entry {bracket.FollowerEntryPrice}); "
                            + "no cancel/replace, so no unprotected window.");
                        return;
                    }
                    catch (Exception cex)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_MODIFY_FAILED",
                            $"{instrument.FullName}: {cex.Message}. Falling back to cancel-then-create.");
                        // The leg the broker refused to change becomes the leg to replace. Both
                        // halves must be set: cancelling without creating is a naked follower,
                        // and it is the failure this fallback exists to avoid.
                        toCancel = toModify;
                        wantsCreate = true;
                    }
                }

                if (toCancel != null) followerAcc.Cancel(new[] { toCancel });

                // A cancel with no create is the reservation case: a submit for this leg is
                // already in flight, so the replacement is that one, not a second one.
                if (!wantsCreate) return;

                // The OCO id for the order about to be created.
                //
                // Re-creating a leg is the ONE case that can need a fresh id: the cancel above may
                // have retired the whole group, and NT8 rejects an id once every leg has gone
                // terminal (handover 4p). A rejected stop is a naked follower, so this path does
                // not gamble -- it mints a fresh id and takes the target down with it, because a
                // working order cannot be moved between groups (there is no OcoChanged field) and
                // a target left in the retired group is paired with nothing. The target sync that
                // follows every stop sync rebuilds it in the new group.
                //
                // Whether cancelling one leg really retires the group is NOT established. This is
                // written to be correct either way; the cost when it does not is one rebuilt
                // target, on a path only reached when Change() has already failed.
                string oco;
                Order staleTarget = null;
                lock (_lock)
                {
                    if (toCancel != null)
                    {
                        staleTarget = bracket.WorkingTarget;
                        bracket.WorkingTarget = null;
                        bracket.OcoId = Guid.NewGuid().ToString();
                    }
                    else
                    {
                        // First creation. If the target got there first its group is live, so
                        // join it -- that is licensed by the live test in handover 4p.
                        string live = LiveLegOcoId(bracket, null);
                        if (!string.IsNullOrEmpty(live)) bracket.OcoId = live;
                        else if (string.IsNullOrEmpty(bracket.OcoId)) bracket.OcoId = Guid.NewGuid().ToString();
                    }
                    oco = bracket.OcoId;
                }

                if (staleTarget != null && RiskGuardAddOn.OccupiesSlot(staleTarget.OrderState))
                {
                    try { followerAcc.Cancel(new[] { staleTarget }); }
                    catch (Exception tex)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_TARGET_CANCEL_FAILED",
                            $"{instrument.FullName}: {tex.Message}. The stale target may still be working "
                            + "in the retired OCO group; the stop below is unaffected.");
                    }
                }

                Order stop = followerAcc.CreateOrder(
                    instrument, action, OrderType.StopMarket, TimeInForce.Day,
                    liveQty, 0, stopPrice, oco, "COPIER_STOP", null);

                if (stop == null)
                {
                    NinjaTrader.Code.Output.Process(
                        $"[CopierEngine] BRACKET_SUBMIT_FAILED on {followerAcc.Name} {instrument.FullName}: CreateOrder returned null. The follower is UNPROTECTED.",
                        PrintTo.OutputTab1);
                    return;
                }
                followerAcc.Submit(new[] { stop });

                // Deliberately does NOT reset StopAttempts. The failure this bound exists for is a
                // broker that ACCEPTS the submit and rejects the order a moment later, so
                // "Submit did not throw" is not evidence of protection and resetting here makes
                // the bound unreachable. The budget is refreshed only by a genuinely new
                // instruction from the leader, or by the bracket being released when the follower
                // goes flat. (Caught by this test failing at 21 submissions.)
                lock (_lock) { bracket.WorkingStop = stop; }

                NinjaTrader.Code.Output.Process(
                    $"[CopierEngine] BRACKET_MIRRORED: {followerAcc.Name} {instrument.FullName} stop {liveQty}@{stopPrice} (leader offset {bracket.StopOffset:+0.##;-0.##}, follower entry {bracket.FollowerEntryPrice}).",
                    PrintTo.OutputTab1);
            }
            catch (Exception ex)
            {
                int attempts;
                lock (_lock) { attempts = bracket.StopAttempts; }
                bool exhausted = attempts >= MaxBracketStopAttempts;
                NinjaTrader.Code.Output.Process(
                    $"[CopierEngine] BRACKET_SUBMIT_FAILED on {followerAcc.Name} {instrument.FullName} "
                    + $"(attempt {attempts}/{MaxBracketStopAttempts}): {ex.Message}. The follower is UNPROTECTED"
                    + (exhausted
                        ? " and the copier has GIVEN UP on this position -- RiskGuard's auto-stop is the only remaining cover, and only if it is armed and live."
                        : "; it will retry on the next leader stop update or follower fill."),
                    PrintTo.OutputTab1);
            }
        }
```
### REGION id="SyncFollowerTargetOnce"  file=addons/TradeCopierEngine.cs  lines 2211-2379
Purpose: the target leg's Change() at :2312, same treatment, but it must never delay or disturb the stop leg
```csharp
        private void SyncFollowerTargetOnce(Account followerAcc, Instrument instrument, FollowerBracket bracket)
        {
            if (followerAcc == null || instrument == null || bracket == null) return;

            DesiredBracket desired;
            var actions = DecideLegActions(
                followerAcc, instrument, bracket, CopierBracketReconciler.OwnedTargetName,
                false, out desired);
            if (desired == null || actions.Count == 0) return;

            // P0-50 on the target leg. An orphan LIMIT against a flat account opens a position
            // when it fills exactly as an orphan stop does when it triggers.
            //
            // Note what this deliberately does NOT do: it leaves FollowerQuantity and FollowerSide
            // alone. Zeroing them here would let a target sync switch the stop sync off.
            if (!desired.HasPosition)
            {
                foreach (var a in actions)
                {
                    if (a.Verb != ReconcileVerb.Cancel) continue;
                    try { followerAcc.Cancel(new[] { a.Subject }); } catch { }
                }
                lock (_lock) { bracket.WorkingTarget = null; }
                CopierLog(followerAcc.Name, "BRACKET_TARGET_ABORTED",
                    $"{instrument.FullName}: {desired.Reason}; no target placed.");
                return;
            }

            // Duplicates first, and outside the attempt budget -- see the stop leg for why.
            // Two working COPIER_TARGETs behind one lot is the defect that opened P0-59, and it
            // was permanent precisely because nothing enumerated the account's orders.
            var keeperActions = new List<ReconcileAction>();
            foreach (var a in actions)
            {
                bool isDuplicateSweep = a.Verb == ReconcileVerb.Cancel
                    && a.Reason != null && a.Reason.StartsWith("duplicate");
                if (!isDuplicateSweep) { keeperActions.Add(a); continue; }
                try
                {
                    followerAcc.Cancel(new[] { a.Subject });
                    CopierLog(followerAcc.Name, "BRACKET_DUPLICATE_CANCELLED",
                        $"{instrument.FullName}: {a.Reason}.");
                }
                catch (Exception dex)
                {
                    CopierLog(followerAcc.Name, "BRACKET_DUPLICATE_CANCEL_FAILED",
                        $"{instrument.FullName}: {dex.Message}. Two targets may still be working.");
                }
            }
            if (keeperActions.Count == 0) return;

            // As the stop leg: a change already in flight means wait, not push. Its own owed
            // flag, not the stop's -- an in-flight target must never make the RISK leg queue.
            foreach (var a in keeperActions)
            {
                if (a.Verb != ReconcileVerb.Defer) continue;
                lock (_lock) { bracket.TargetChangeDeferred = true; }
                CopierLog(followerAcc.Name, "BRACKET_TARGET_DEFERRED",
                    $"{instrument.FullName}: {a.Reason}");
                return;
            }

            Order toModify = null;
            Order toCancel = null;
            bool wantsCreate = false;
            foreach (var a in keeperActions)
            {
                if (a.Verb == ReconcileVerb.Modify) toModify = a.Subject;
                else if (a.Verb == ReconcileVerb.Cancel) toCancel = a.Subject;
                else if (a.Verb == ReconcileVerb.Create) wantsCreate = true;
            }

            double targetPrice = desired.Target.Price;
            int qty = desired.Target.Quantity;
            OrderAction action = desired.Target.Action;

            lock (_lock)
            {
                if (bracket.TargetAttempts >= MaxBracketTargetAttempts) return;
                bracket.TargetAttempts++;
            }

            var livePos = followerAcc.Positions.FirstOrDefault(p =>
                p.Instrument != null &&
                p.Instrument.FullName.Equals(instrument.FullName, StringComparison.OrdinalIgnoreCase));
            if (livePos == null) return;

            try
            {
                // Broker calls outside `_lock` (P1-10/P1-35), as the stop sync does.
                int liveQty = Math.Min(qty, livePos.Quantity);

                // Modify in place where possible: it preserves OCO group membership -- confirmed
                // live on 2026-08-10, a trailed leg kept both its orderId and its oco -- so the
                // pair survives without any id being re-minted.
                if (toModify != null)
                {
                    try
                    {
                        toModify.LimitPrice = targetPrice;
                        toModify.Quantity = liveQty;
                        followerAcc.Change(new[] { toModify });

                        lock (_lock) { bracket.WorkingTarget = toModify; }

                        CopierLog(followerAcc.Name, "BRACKET_TARGET_MODIFIED",
                            $"{instrument.FullName} target moved to {liveQty}@{targetPrice} in place "
                            + $"(leader offset {bracket.TargetOffset:+0.##;-0.##}, follower entry {bracket.FollowerEntryPrice}).");
                        return;
                    }
                    catch (Exception cex)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_TARGET_MODIFY_FAILED",
                            $"{instrument.FullName}: {cex.Message}. Falling back to cancel-then-create.");
                        toCancel = toModify;
                        wantsCreate = true;
                    }
                }

                if (toCancel != null) followerAcc.Cancel(new[] { toCancel });

                // A cancel with no create means a target submit is already in flight.
                if (!wantsCreate) return;

                string oco;
                lock (_lock)
                {
                    // Join the stop's group if it is live -- an id can be joined while its group
                    // still has a live member (handover 4p). Only mint a fresh one when there is
                    // no live sibling, which is the case NT8 actually rejects.
                    //
                    // Unlike the stop's re-create path this never cancels the sibling to force a
                    // rebuild. If the cancel above did retire the group, the stop's own
                    // OrderUpdate re-submits it and the pair reforms a beat later; cancelling a
                    // working protective stop to tidy up an OCO group is not a trade worth making.
                    string live = LiveLegOcoId(bracket, toCancel);
                    bracket.OcoId = !string.IsNullOrEmpty(live) ? live : Guid.NewGuid().ToString();
                    oco = bracket.OcoId;
                }

                Order target = followerAcc.CreateOrder(
                    instrument, action, OrderType.Limit, TimeInForce.Day,
                    liveQty, targetPrice, 0, oco, "COPIER_TARGET", null);

                if (target == null)
                {
                    CopierLog(followerAcc.Name, "BRACKET_TARGET_FAILED",
                        $"{instrument.FullName}: CreateOrder returned null. The follower keeps its stop "
                        + "and still exits when the leader's target fill is copied; only fill quality is lost.");
                    return;
                }

                followerAcc.Submit(new[] { target });
                lock (_lock) { bracket.WorkingTarget = target; }

                CopierLog(followerAcc.Name, "BRACKET_TARGET_MIRRORED",
                    $"{instrument.FullName} target {liveQty}@{targetPrice} "
                    + $"(leader offset {bracket.TargetOffset:+0.##;-0.##}, follower entry {bracket.FollowerEntryPrice}, oco {oco}).");
            }
            catch (Exception ex)
            {
                int attempts;
                lock (_lock) { attempts = bracket.TargetAttempts; }
                CopierLog(followerAcc.Name, "BRACKET_TARGET_FAILED",
                    $"{instrument.FullName} (attempt {attempts}/{MaxBracketTargetAttempts}): {ex.Message}. "
                    + "The stop is unaffected and the follower still exits on the copied leader target fill"
                    + (attempts >= MaxBracketTargetAttempts ? "; the copier has given up on mirroring this target." : "."));
            }
        }
```
### REGION id="OnFollowerOrderUpdate"  file=addons/TradeCopierEngine.cs  lines 1325-1379
Purpose: where the settle event arrives and the read-back belongs -- inside the AcceptsModification block, BEFORE the OccupiesSlot early return
```csharp
        private void OnFollowerOrderUpdate(Account followerAcc, Order order)
        {
            if (followerAcc == null || order == null || order.Instrument == null) return;

            // P0-61's completion hook, and it must come BEFORE the OccupiesSlot return below.
            //
            // A leg that has just settled out of ChangeSubmitted/ChangePending still occupies a
            // slot, so the early return would drop this event -- and the instruction we deferred
            // while the change was in flight would be lost, leaving the leg at its old price and
            // size for the life of the position. That is the defect P0-61 fixes, one layer down:
            // declining to act is only safe if something later acts.
            if (RiskGuardAddOn.AcceptsModification(order.OrderState)
                && ReDriveDeferredLeg(followerAcc, order))
                return;

            if (RiskGuardAddOn.OccupiesSlot(order.OrderState)) return;   // still there; nothing lost
            if (order.OrderState == OrderState.Filled) return;                 // it did its job

            string key = BracketKey(followerAcc.Name, order.Instrument.FullName);
            FollowerBracket bracket;
            bool isStopLeg;
            Order sibling;
            lock (_lock)
            {
                if (!_followerBrackets.TryGetValue(key, out bracket)) return;
                isStopLeg = ReferenceEquals(bracket.WorkingStop, order);
                bool isTargetLeg = ReferenceEquals(bracket.WorkingTarget, order);
                if (!isStopLeg && !isTargetLeg) return;                        // not one of ours
                sibling = isStopLeg ? bracket.WorkingTarget : bracket.WorkingStop;
                // Do NOT clear WorkingStop/WorkingTarget here. An honest reference keeps the
                // ReferenceEquals guard meaningful during an in-flight sync, and it lets a second
                // sync modify the existing order instead of creating a duplicate. The re-drive
                // will replace it once the broker work resolves.
            }

            // A leg whose OCO sibling has FILLED was not lost -- it was retired, which is what
            // "one cancels the other" means. Re-submitting here would place a protective order
            // against a position that has just been closed, because NT8 raises ExecutionUpdate
            // before PositionUpdate (P0-49's ordering) and the follower therefore still reads as
            // open. That is P0-50's orphan, arriving by a route that did not exist until targets
            // were mirrored. The follower's position update releases the bracket a beat later.
            if (sibling != null && sibling.OrderState == OrderState.Filled)
            {
                CopierLog(followerAcc.Name, "BRACKET_LEG_RETIRED_BY_OCO",
                    $"{order.Instrument.FullName} mirrored {(isStopLeg ? "stop" : "target")} went "
                    + $"{order.OrderState} because its OCO sibling filled; not re-submitting.");
                return;
            }

            NinjaTrader.Code.Output.Process(
                $"[CopierEngine] {(isStopLeg ? "BRACKET_STOP_LOST" : "BRACKET_TARGET_LOST")}: {followerAcc.Name} {order.Instrument.FullName} mirrored {(isStopLeg ? "stop" : "target")} went {order.OrderState}; re-submitting.",
                PrintTo.OutputTab1);

            SyncFollowerBracket(followerAcc, order.Instrument, bracket);
        }
```
Return one block per region id above, in the same order. No other output.