# TICKET T1: P0-63: Account.Change() is accepted and silently ignored, so the mirrored stop has never trailed -- verify the read-back and fall back to cancel-then-create

## Defect this patch must close
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

## Mechanical gates (facts - you may not contradict these)
static: 6 block(s) well-formed; compile: build succeeded; test: no regressions; 939 passed, 5 failed, 3 expected failure(s) now green; all 3 acceptance test(s) green; lock-scope: no risk calls under _stateLock

## Already-settled decisions
A finding that restates one of these is REJECTED by definition.

- CoveredQuantity is the SUM over every live protective stop on the position, and both it and RecognizedStopOrder are DERIVED from PositionGuardFsm's stop list -- neither is assignable (P1-36, closed 2026-08-07).
- NT8 raises ExecutionUpdate BEFORE PositionUpdate. Code that reads account.Positions from an execution handler reads a position that does not exist yet on an entry fill (P0-49, closed 2026-08-07).
- The copier FAILS CLOSED ON ENTRIES, NEVER ON EXITS.
- Pending copies and recognised stops are keyed by Order OBJECT REFERENCE, never by Order.OrderId. NT8's OrderId is neither unique nor stable.
- The mirrored bracket stop carries the leader's SIGNED offset applied to the FOLLOWER's own fill. Never Math.Abs, never the leader's stop PRICE.
- Simulation accounts are identified by account.Provider == Provider.Simulator, never by a name prefix (P1-20, closed).

## Findings to rule on

#1 [BLOCKER] (from deepseek-v4-flash:cloud)
OnFollowerOrderUpdate verification block: The verification runs on ANY order that satisfies `AcceptsModification`, but the `StopChangeRequested`/`TargetChangeRequested` flags are only set when a Change() was issued. The problem: when a Change() is issued and the provider HONOURS it, the settle event arrives with the order carrying the NEW values, and the check passes (mismatch=false), clearing the flag. But when the provider IGNORES the change, the settle event arrives with the order carrying the OLD values — and the check correctly detects mismatch. However, the critical failure: the `_accountsIgnoringChange` set is keyed by `followerAcc.Name`, but the check `verifyIsStopLeg = ReferenceEquals(verifyBracket.WorkingStop, order)` uses the bracket's `WorkingStop` reference. After a successful Change() that is honoured, `bracket.WorkingStop = toModify` is set — but the Order object reference may be REPLACED by NT8 on the settle event (the Order object that arrives in OnFollowerOrderUpdate may be a different instance than the one passed to Change()). If NT8 delivers a different Order instance for the same logical order, `ReferenceEquals` fails, `verifyBracket` is set to null, and the verification is silently skipped — the no-op is never detected, and the stop stays at the original price forever. This is the exact defect the ticket claims to fix, and it remains unfixed for any provider that replaces the Order object reference on settle. The code must key verification by OrderId or by matching the order's instrument/price/quantity against the bracket's recorded request, not by ReferenceEquals on the Order object.

#2 [BLOCKER] (from deepseek-v4-flash:cloud)
SyncFollowerStopOnce bypass path: When `providerIgnoresChange` is true and `toModify != null`, the code sets `toCancel = toModify; wantsCreate = true; toModify = null;` and then proceeds to the cancel-then-create path. But the `StopAttempts` budget was already incremented at the top of the method (`bracket.StopAttempts++`). The cancel-then-create path then calls `followerAcc.Cancel` and `followerAcc.Submit`. If the broker rejects the new stop (a separate failure mode), the catch block logs `BRACKET_SUBMIT_FAILED` and the budget is consumed. But the critical issue: the bypass path does NOT clear `bracket.StopChangeRequested` before the cancel — it sets `bracket.StopChangeRequested = false` in the `if (toModify != null && providerIgnoresChange)` block, which is correct. However, the cancel-then-create path that follows does NOT reset `StopAttempts` (deliberately, per the comment), so a provider that ignores Change() AND rejects the replacement stop will exhaust the budget after `MaxBracketStopAttempts` attempts, leaving the follower naked with no further retries. The ticket says "check what the counters do on this new path before you assume they are fine" — the patch does not address this. The bypass path should reset `StopAttempts` when a no-op is detected and the account is marked, because the budget was designed for a different failure mode (rejected submissions), not for a provider that silently ignores Change().

#3 [MAJOR] (from deepseek-v4-flash:cloud)
OnFollowerOrderUpdate verification: The verification block calls `SyncFollowerStopOnce`/`SyncFollowerTargetOnce` directly from within the `AcceptsModification` block. But `SyncFollowerStopOnce` calls `DecideLegActions` which may return a `Defer` action (if a change is still in flight on the OTHER leg, or if the leg itself is mid-change). The verification block already cleared `StopChangeDeferred`/`TargetChangeDeferred` on mismatch, but the re-drive via `SyncFollowerStopOnce` may hit the `Defer` path and set the deferred flag again, then return. The order is now settled (it left ChangeSubmitted), so the deferred flag will be re-driven on the NEXT OrderUpdate — but there may be no next OrderUpdate for this order (it's already settled and working). The deferred flag is only cleared in `ReDriveDeferredLeg`, which is called from `OnFollowerOrderUpdate` on the next event for that order. If no further events arrive for this order, the stop stays at the old price forever. The patch must ensure that after a mismatch is detected and the account is marked, the re-drive cannot be deferred again — it must force the cancel-then-create path immediately.

#4 [MAJOR] (from deepseek-v4-flash:cloud)
SyncFollowerStopOnce and SyncFollowerTargetOnce: The `_accountsIgnoringChange` check is done AFTER `bracket.StopAttempts++` is incremented. On the FIRST no-op detection (in OnFollowerOrderUpdate), the account is added to `_accountsIgnoringChange`, and then `SyncFollowerStopOnce` is called. That call increments `StopAttempts` again (now 2 for the same logical trail). The cancel-then-create path then runs. If the broker accepts the new stop, fine. But if the broker rejects it, the budget is consumed faster than before. More critically: the `StopAttempts` budget is never reset when a no-op is detected and the account is marked. The ticket says "A no-op that is detected and replaced must not be able to loop against those budgets forever" — the patch does not reset the budget on the bypass path, so a provider that ignores Change() AND rejects the replacement will exhaust the budget and leave the follower naked permanently.

#5 [MAJOR] (from deepseek-v4-flash:cloud)
OnFollowerOrderUpdate verification: The verification block runs for BOTH the stop and target legs, but it does NOT check whether the order is actually the one that was Changed. It checks `ReferenceEquals(verifyBracket.WorkingStop, order)` — but `WorkingStop` is set to `toModify` AFTER `Change()` returns. If a NEW stop is created (via cancel-then-create) and then a Change() is issued on it, `WorkingStop` points to the new order. But if the OLD order (the one that was cancelled) settles with an OrderUpdate that satisfies `AcceptsModification` (e.g., it goes from CancelPending to Cancelled), the verification block will run for the OLD order, find `ReferenceEquals(verifyBracket.WorkingStop, order)` false (because WorkingStop now points to the new order), set `verifyBracket = null`, and skip verification. That's correct. But the reverse: if the NEW order (created via cancel-then-create) settles with an OrderUpdate that satisfies `AcceptsModification` (e.g., Working -> Accepted), and `StopChangeRequested` is false (because it was cleared on the create path), the verification block runs, finds `StopChangeRequested` false, and does nothing. That's correct. The problem is the ORDER of events: the verification block runs BEFORE `ReDriveDeferredLeg`. If a Change() was issued, the settle event arrives, verification runs, and if the provider honoured it, `StopChangeRequested` is cleared. But if the provider ignored it, mismatch is detected, the account is marked, and `SyncFollowerStopOnce` is called. That call issues a cancel-then-create. The NEW order's settle event will then arrive, and the verification block will run again — but `StopChangeRequested` is false (cleared on the create path), so no verification happens. That's correct. However, the OLD order (the one that was cancelled) may ALSO settle with an OrderUpdate that satisfies `AcceptsModification` (e.g., Cancelled). The verification block runs for the OLD order, finds `ReferenceEquals(verifyBracket.WorkingStop, order)` false (WorkingStop now points to the new order), sets `verifyBracket = null`, and skips. That's correct. But there's a race: if the OLD order's settle event arrives AFTER the new order's settle event, and the OLD order's OrderState is `Cancelled` (which does NOT satisfy `AcceptsModification`), the verification block is skipped entirely. That's fine. The real race: if the OLD order's settle event arrives while `StopChangeRequested` is still true (because the new order hasn't been created yet), the verification block will run for the OLD order, find `ReferenceEquals(verifyBracket.WorkingStop, order)` true (because WorkingStop still points to the OLD order until the new one is created), and check the OLD order's price/quantity against the requested values. If the OLD order was cancelled (not changed), its price/quantity are the OLD values, which will MISMATCH the requested values, causing a false no-op detection and marking the account as ignoring Change() even though the provider never ignored anything — the order was cancelled, not changed. This is a false positive that would permanently disable modify-in-place for a healthy account.

#6 [MINOR] (from deepseek-v4-flash:cloud)
SyncFollowerStopOnce: The `providerIgnoresChange` check is done inside the `try` block, but the `StopAttempts` increment happens BEFORE the try. If `providerIgnoresChange` is true and the cancel-then-create path throws (e.g., Cancel throws), the catch block logs `BRACKET_SUBMIT_FAILED` and the budget is consumed. But the account is already marked as ignoring Change(), so the next trail will again go straight to cancel-then-create, incrementing the budget again. The budget will exhaust after `MaxBracketStopAttempts` trails, leaving the follower naked. The patch should reset `StopAttempts` when the account is first marked as ignoring Change(), because the budget was designed for a different failure mode.

#7 [MINOR] (from deepseek-v4-flash:cloud)
OnFollowerOrderUpdate: The verification block calls `SyncFollowerStopOnce`/`SyncFollowerTargetOnce` directly, which can re-enter `OnFollowerOrderUpdate` indirectly (via the OrderUpdate event for the new order). This is a re-entrancy concern: the verification block is inside the `AcceptsModification` block, and `SyncFollowerStopOnce` may issue a Cancel and Submit, which will generate new OrderUpdate events. Those events will be processed by the same `OnFollowerOrderUpdate` handler, potentially while the current invocation is still on the stack. NT8's event dispatch is typically single-threaded, so this is likely safe, but the patch should document this assumption.

#8 [MINOR] (from deepseek-v4-flash:cloud)
Test adequacy: The patch description mentions three acceptance tests, but the actual test code is not shown in the patch. The tests must verify: (1) a no-op Change() is detected and the account is marked; (2) a subsequent trail on the same account goes straight to cancel-then-create; (3) an honoured Change() still modifies in place. The patch does not show how the stub simulates the provider ignoring Change() — the stub must apply the revert in `SettleChange` and NOT in `Change`, per the ticket. The tests must also verify the budget behaviour on the bypass path, which the patch does not address.

#9 [BLOCKER] (from glm-5.2:cloud)
OnFollowerOrderUpdate: The mismatch re-drive calls `SyncFollowerStopOnce`/`SyncFollowerTargetOnce` synchronously from within the order-update callback, but the verification block already holds `_lock` when it sets `_accountsIgnoringChange.Add(followerAcc.Name)` and clears the deferred/requested flags. The re-drive then enters `SyncFollowerStopOnce`, which immediately tries `lock (_lock)` at `if (bracket.StopAttempts >= MaxBracketStopAttempts)`. This is a non-reentrant `lock(_lock)` self-deadlock on every detected no-op. The line `if (verifyIsStopLeg) SyncFollowerStopOnce(followerAcc, order.Instrument, verifyBracket);` is reached while the outer `lock (_lock)` block in the verification has already exited, BUT the `_accountsIgnoringChange.Add` and flag clears happen inside a `lock (_lock)` that is released before the `if (mismatch)` block — so the deadlock is NOT there. However, the re-driven `SyncFollowerStopOnce` will call `followerAcc.Cancel` and `followerAcc.Submit` synchronously inside `OnFollowerOrderUpdate`, which is an NT8 event handler. Calling broker submit/cancel from within an order update callback can cause re-entrancy issues with NT8's order processing engine, potentially causing the submitted order's update to fire before this handler returns, creating a re-entrant callback chain.

#10 [BLOCKER] (from glm-5.2:cloud)
OnFollowerOrderUpdate: The verification block reads `order.StopPrice` and `order.LimitPrice` to compare against the requested values, but the ticket explicitly states "the engine already wrote the desired values onto it, so the object cannot tell you what the broker holds." The patch's own FollowerBracket comment says "NT8 writes the desired values onto the Order immediately even when the provider silently ignores them." If NT8 writes the desired `StopPrice` onto the `Order` object immediately when `toModify.StopPrice = stopPrice` is set (before `Change()` is even called), then `order.StopPrice` will ALWAYS equal `StopChangeRequestedPrice` at settle time, because both were set from the same `stopPrice` variable. The verification `order.StopPrice != requestedPrice` will NEVER detect a mismatch. The stub test passes because the stub's `SettleChange` reverts the order object's price, but on a real NT8 Simulator account, the Order object's `StopPrice` field was already mutated to the desired value by `toModify.StopPrice = stopPrice` and the Simulator engine does not revert it — it just ignores the Change() call. The order object still carries the desired price. The verification is comparing the desired price against itself.

#11 [MAJOR] (from glm-5.2:cloud)
SyncFollowerStopOnce: The bypass path sets `toModify = null` but does not clear `bracket.WorkingStop` reference. When the bypass fires, `toCancel = toModify` (the old working stop) and `wantsCreate = true`. The cancel-then-create path then executes: `followerAcc.Cancel(new[] { toCancel })` cancels the old stop, then mints a new OCO id, potentially cancels the stale target, creates and submits a new stop. But `bracket.StopAttempts` was already incremented at the top of this method. The cancel-then-create fallback on the bypass path does NOT increment it again (it's the same method call), so the budget is consumed once per bypass — which is correct. However, the bypass path does NOT reset `StopChangeRequested` before the cancel — it sets `bracket.StopChangeRequested = false` under lock, which is correct. But if the cancel-then-create on the bypass path throws or fails, `StopChangeRequested` is already false, so no verification will fire on the new order's settle. The new order is a fresh create, not a change, so this is correct behavior.

#12 [MAJOR] (from glm-5.2:cloud)
OnFollowerOrderUpdate: When a mismatch is detected and the leg is re-driven via `SyncFollowerStopOnce`, that re-drive will call `followerAcc.Change()` again if the account is NOT yet in `_accountsIgnoringChange` — but it WAS just added. So the re-drive will bypass Change() and go to cancel-then-create. This is correct. However, the re-drive's `SyncFollowerStopOnce` increments `StopAttempts` again. The original `SyncFollowerStopOnce` call that issued the Change() already incremented `StopAttempts`. Now the re-drive increments it again. If the leader trails rapidly and each trail is a no-op, each trail costs 2 attempts (one for the Change path, one for the fallback cancel-then-create). With `MaxBracketStopAttempts` (default unknown but referenced as 21 in tests), the budget is consumed at 2x rate, potentially exhausting it after ~10 trail steps instead of 21, leaving the follower unprotected.

#13 [MAJOR] (from glm-5.2:cloud)
OnFollowerOrderUpdate: The verification block calls `SyncFollowerStopOnce` or `SyncFollowerTargetOnce` directly, but these methods call `DecideLegActions` which reads `followerAcc.Positions`. Per P0-49 (settled decision), NT8 raises ExecutionUpdate before PositionUpdate, so on an entry fill the position does not exist yet. If the order update that triggers verification is an entry fill (not a change settle), `livePos` will be null and the re-drive returns without placing a stop. This is not a new bug (the existing re-submit path has the same issue), but the verification path now reaches `SyncFollowerStopOnce` on more events, widening the exposure.

#14 [MINOR] (from glm-5.2:cloud)
OnFollowerOrderUpdate: The verification block acquires `_lock` twice in succession — once to look up the bracket and identify the leg, then again inside the `if (verifyBracket != null)` block to read/clear the requested fields. The first lock block sets `verifyBracket` and `verifyIsStopLeg`, then releases the lock. Between the two locks, another thread could modify `verifyBracket.WorkingStop` or `WorkingTarget`, making `verifyIsStopLeg` stale. The second lock block then reads `verifyBracket.StopChangeRequested` which may no longer correspond to the order that triggered the event. This is a TOCTOU race: the order update identifies the leg as a stop, the lock releases, a sync replaces `WorkingStop` with a new order, the second lock acquires, and the verification checks `StopChangeRequested` against the wrong order's state.

#15 [MINOR] (from glm-5.2:cloud)
SyncFollowerTargetOnce: The bypass path for the target leg does not cancel the stale target's OCO sibling (the stop) when minting a new OCO id, unlike the stop leg's re-create path which does cancel `staleTarget`. The target's cancel-then-create path uses `LiveLegOcoId(bracket, toCancel)` to join the stop's existing group. If the stop is still live in the old group and the target was just cancelled (retiring the group if the target was the last member), the new target joins the stop's group. This is correct. But if the account ignores Change() and the stop was ALSO just re-created into a new group, the target's `LiveLegOcoId` may find the stop's new group or may find nothing if the stop's re-create hasn't settled yet, minting a second group. This is a transient inconsistency but self-heals on the next sync.

#16 [MINOR] (from glm-5.2:cloud)
FollowerBracket: `StopChangeRequestedQuantity` and `TargetChangeRequestedQuantity` are `int` fields with no `NaN` sentinel. The ticket says "a flag or a NaN sentinel for 'nothing asked'". The `StopChangeRequested` bool serves as the flag, so this is fine. But `StopChangeRequestedQuantity` defaults to 0, and if a Change() legitimately requests quantity 0 (which should never happen for a stop), the verification `order.Quantity != requestedQty` would compare against 0. This is not a real-world issue since stops never have quantity 0, but it is a latent fragility.

## The patch under review (unified diff)
```diff
diff --git a/addons/TradeCopierEngine.cs b/addons/TradeCopierEngine.cs
index cd1b10b..eb3a475 100644
--- a/addons/TradeCopierEngine.cs
+++ b/addons/TradeCopierEngine.cs
@@ -133,6 +133,7 @@ namespace NinjaTrader.NinjaScript.AddOns
         private readonly Queue<string> _executionIdQueue = new Queue<string>();
         private const int MaxExecutionCacheSize = 5000;
         private readonly object _lock = new object();
+        private readonly HashSet<string> _accountsIgnoringChange = new HashSet<string>();
 
         public void AddRelationship(CopierRelationship rel) => UpsertRelationship(rel);
 
@@ -1326,16 +1327,89 @@ namespace NinjaTrader.NinjaScript.AddOns
         {
             if (followerAcc == null || order == null || order.Instrument == null) return;
 
-            // P0-61's completion hook, and it must come BEFORE the OccupiesSlot return below.
+            // P0-63 verification must come BEFORE the OccupiesSlot return below. A leg that has
+            // just settled out of ChangeSubmitted/ChangePending still occupies a slot, so the
+            // early return would drop the event -- and we would never notice that the provider
+            // silently ignored the Change() and left the order at its original price/size.
             //
-            // A leg that has just settled out of ChangeSubmitted/ChangePending still occupies a
-            // slot, so the early return would drop this event -- and the instruction we deferred
-            // while the change was in flight would be lost, leaving the leg at its old price and
-            // size for the life of the position. That is the defect P0-61 fixes, one layer down:
-            // declining to act is only safe if something later acts.
-            if (RiskGuardAddOn.AcceptsModification(order.OrderState)
-                && ReDriveDeferredLeg(followerAcc, order))
-                return;
+            // P0-61's completion hook is also in this block; verification runs first because a
+            // detected no-op forces the account onto the cancel-then-create path, which also
+            // satisfies any deferred change queued while the ignored change was in flight.
+            if (RiskGuardAddOn.AcceptsModification(order.OrderState))
+            {
+                string verifyKey = BracketKey(followerAcc.Name, order.Instrument.FullName);
+                FollowerBracket verifyBracket = null;
+                bool verifyIsStopLeg = false;
+                lock (_lock)
+                {
+                    if (_followerBrackets.TryGetValue(verifyKey, out verifyBracket))
+                    {
+                        verifyIsStopLeg = ReferenceEquals(verifyBracket.WorkingStop, order);
+                        bool isTargetLeg = ReferenceEquals(verifyBracket.WorkingTarget, order);
+                        if (!verifyIsStopLeg && !isTargetLeg) verifyBracket = null;
+                    }
+                }
+
+                if (verifyBracket != null)
+                {
+                    bool mismatch = false;
+                    int requestedQty = 0;
+                    double requestedPrice = double.NaN;
+                    lock (_lock)
+                    {
+                        if (verifyIsStopLeg && verifyBracket.StopChangeRequested)
+                        {
+                            requestedQty = verifyBracket.StopChangeRequestedQuantity;
+                            requestedPrice = verifyBracket.StopChangeRequestedPrice;
+                            if (double.IsNaN(requestedPrice)
+                                || order.StopPrice != requestedPrice
+                                || order.Quantity != requestedQty)
+                            {
+                                mismatch = true;
+                                verifyBracket.StopChangeRequested = false;
+                                verifyBracket.StopChangeDeferred = false;
+                                _accountsIgnoringChange.Add(followerAcc.Name);
+                            }
+                            else
+                            {
+                                verifyBracket.StopChangeRequested = false;
+                            }
+                        }
+                        else if (!verifyIsStopLeg && verifyBracket.TargetChangeRequested)
+                        {
+                            requestedQty = verifyBracket.TargetChangeRequestedQuantity;
+                            requestedPrice = verifyBracket.TargetChangeRequestedPrice;
+                            if (double.IsNaN(requestedPrice)
+                                || order.LimitPrice != requestedPrice
+                                || order.Quantity != requestedQty)
+                            {
+                                mismatch = true;
+                                verifyBracket.TargetChangeRequested = false;
+                                verifyBracket.TargetChangeDeferred = false;
+                                _accountsIgnoringChange.Add(followerAcc.Name);
+                            }
+                            else
+                            {
+                                verifyBracket.TargetChangeRequested = false;
+                            }
+                        }
+                    }
+
+                    if (mismatch)
+                    {
+                        CopierLog(followerAcc.Name, "BRACKET_CHANGE_IGNORED",
+                            $"{order.Instrument.FullName} mirrored {(verifyIsStopLeg ? "stop" : "target")} did not take the requested values "
+                            + $"(requested {requestedQty}@{requestedPrice}, broker {order.Quantity}@{(verifyIsStopLeg ? order.StopPrice : order.LimitPrice)}). "
+                            + "Falling back to cancel-then-create for this account.");
+
+                        if (verifyIsStopLeg) SyncFollowerStopOnce(followerAcc, order.Instrument, verifyBracket);
+                        else SyncFollowerTargetOnce(followerAcc, order.Instrument, verifyBracket);
+                        return;
+                    }
+                }
+
+                if (ReDriveDeferredLeg(followerAcc, order)) return;
+            }
 
             if (RiskGuardAddOn.OccupiesSlot(order.OrderState)) return;   // still there; nothing lost
             if (order.OrderState == OrderState.Filled) return;                 // it did its job
@@ -1468,6 +1542,18 @@ namespace NinjaTrader.NinjaScript.AddOns
             // settles (ReDriveDeferredLeg). NOT the same as *ResyncOwed -- see that method.
             public bool StopChangeDeferred;
             public bool TargetChangeDeferred;
+
+            // P0-63. What the last Change() asked for, recorded separately from the Order because
+            // NT8 writes the desired values onto the Order immediately even when the provider
+            // silently ignores them. The read-back in OnFollowerOrderUpdate compares these to the
+            // settled order; a mismatch means the provider did not honour the change.
+            public bool StopChangeRequested;
+            public double StopChangeRequestedPrice = double.NaN;
+            public int StopChangeRequestedQuantity;
+
+            public bool TargetChangeRequested;
+            public double TargetChangeRequestedPrice = double.NaN;
+            public int TargetChangeRequestedQuantity;
         }
 
         // How many EXTRA passes the reservation holder will re-drive the sync for, after a
@@ -1972,6 +2058,22 @@ namespace NinjaTrader.NinjaScript.AddOns
                 // and here, and a stop larger than the position FLIPS it on trigger.
                 int liveQty = Math.Min(qty, livePos.Quantity);
 
+                // P0-63. Once this account has demonstrably ignored a Change(), never ask it to
+                // Change() again -- go straight to cancel-then-create. The provider is a property
+                // of the account, not the instrument, so the verdict is account-level.
+                bool providerIgnoresChange;
+                lock (_lock) { providerIgnoresChange = _accountsIgnoringChange.Contains(followerAcc.Name); }
+
+                if (toModify != null && providerIgnoresChange)
+                {
+                    CopierLog(followerAcc.Name, "BRACKET_MODIFY_BYPASSED",
+                        $"{instrument.FullName}: this account has already ignored a Change() once; going straight to cancel-then-create.");
+                    lock (_lock) { bracket.StopChangeRequested = false; }
+                    toCancel = toModify;
+                    wantsCreate = true;
+                    toModify = null;
+                }
+
                 // A leader trailing its stop is the ordinary case, and cancel-then-create left the
                 // follower unprotected on EVERY trail step, between the cancel and the new order's
                 // acceptance. Modify the working order instead: one order, no window.
@@ -1992,7 +2094,13 @@ namespace NinjaTrader.NinjaScript.AddOns
                         toModify.Quantity = liveQty;
                         followerAcc.Change(new[] { toModify });
 
-                        lock (_lock) { bracket.WorkingStop = toModify; }
+                        lock (_lock)
+                        {
+                            bracket.WorkingStop = toModify;
+                            bracket.StopChangeRequested = true;
+                            bracket.StopChangeRequestedPrice = stopPrice;
+                            bracket.StopChangeRequestedQuantity = liveQty;
+                        }
 
                         CopierLog(followerAcc.Name, "BRACKET_MODIFIED",
                             $"{instrument.FullName} stop moved to {liveQty}@{stopPrice} in place "
@@ -2007,6 +2115,7 @@ namespace NinjaTrader.NinjaScript.AddOns
                         // The leg the broker refused to change becomes the leg to replace. Both
                         // halves must be set: cancelling without creating is a naked follower,
                         // and it is the failure this fallback exists to avoid.
+                        lock (_lock) { bracket.StopChangeRequested = false; }
                         toCancel = toModify;
                         wantsCreate = true;
                     }
@@ -2082,7 +2191,11 @@ namespace NinjaTrader.NinjaScript.AddOns
                 // the bound unreachable. The budget is refreshed only by a genuinely new
                 // instruction from the leader, or by the bracket being released when the follower
                 // goes flat. (Caught by this test failing at 21 submissions.)
-                lock (_lock) { bracket.WorkingStop = stop; }
+                lock (_lock)
+                {
+                    bracket.WorkingStop = stop;
+                    bracket.StopChangeRequested = false;
+                }
 
                 NinjaTrader.Code.Output.Process(
                     $"[CopierEngine] BRACKET_MIRRORED: {followerAcc.Name} {instrument.FullName} stop {liveQty}@{stopPrice} (leader offset {bracket.StopOffset:+0.##;-0.##}, follower entry {bracket.FollowerEntryPrice}).",
@@ -2300,6 +2413,22 @@ namespace NinjaTrader.NinjaScript.AddOns
                 // Broker calls outside `_lock` (P1-10/P1-35), as the stop sync does.
                 int liveQty = Math.Min(qty, livePos.Quantity);
 
+                // P0-63. Once this account has demonstrably ignored a Change(), never ask it to
+                // Change() again -- go straight to cancel-then-create. The target leg keeps its
+                // own flag so it never blocks or disturbs the stop leg.
+                bool providerIgnoresChange;
+                lock (_lock) { providerIgnoresChange = _accountsIgnoringChange.Contains(followerAcc.Name); }
+
+                if (toModify != null && providerIgnoresChange)
+                {
+                    CopierLog(followerAcc.Name, "BRACKET_TARGET_MODIFY_BYPASSED",
+                        $"{instrument.FullName}: this account has already ignored a Change() once; going straight to cancel-then-create.");
+                    lock (_lock) { bracket.TargetChangeRequested = false; }
+                    toCancel = toModify;
+                    wantsCreate = true;
+                    toModify = null;
+                }
+
                 // Modify in place where possible: it preserves OCO group membership -- confirmed
                 // live on 2026-08-10, a trailed leg kept both its orderId and its oco -- so the
                 // pair survives without any id being re-minted.
@@ -2311,7 +2440,13 @@ namespace NinjaTrader.NinjaScript.AddOns
                         toModify.Quantity = liveQty;
                         followerAcc.Change(new[] { toModify });
 
-                        lock (_lock) { bracket.WorkingTarget = toModify; }
+                        lock (_lock)
+                        {
+                            bracket.WorkingTarget = toModify;
+                            bracket.TargetChangeRequested = true;
+                            bracket.TargetChangeRequestedPrice = targetPrice;
+                            bracket.TargetChangeRequestedQuantity = liveQty;
+                        }
 
                         CopierLog(followerAcc.Name, "BRACKET_TARGET_MODIFIED",
                             $"{instrument.FullName} target moved to {liveQty}@{targetPrice} in place "
@@ -2322,6 +2457,7 @@ namespace NinjaTrader.NinjaScript.AddOns
                     {
                         CopierLog(followerAcc.Name, "BRACKET_TARGET_MODIFY_FAILED",
                             $"{instrument.FullName}: {cex.Message}. Falling back to cancel-then-create.");
+                        lock (_lock) { bracket.TargetChangeRequested = false; }
                         toCancel = toModify;
                         wantsCreate = true;
                     }
@@ -2361,7 +2497,11 @@ namespace NinjaTrader.NinjaScript.AddOns
                 }
 
                 followerAcc.Submit(new[] { target });
-                lock (_lock) { bracket.WorkingTarget = target; }
+                lock (_lock)
+                {
+                    bracket.WorkingTarget = target;
+                    bracket.TargetChangeRequested = false;
+                }
 
                 CopierLog(followerAcc.Name, "BRACKET_TARGET_MIRRORED",
                     $"{instrument.FullName} target {liveQty}@{targetPrice} "
@@ -2490,7 +2630,11 @@ namespace NinjaTrader.NinjaScript.AddOns
         /// </summary>
         internal void ResetBracketsForTest()
         {
-            lock (_lock) { _followerBrackets.Clear(); }
+            lock (_lock)
+            {
+                _followerBrackets.Clear();
+                _accountsIgnoringChange.Clear();
+            }
         }
 
         internal double GetMirroredStopPriceForTest(string followerAccount, string instrumentFullName)

```

Rule on all 16 findings by number, then recommend.