# RiskGuard + TradeCopier Hardening Plan

> **Path note (repo split, 2026-08-12).** This document was written while the addons lived in
> `tvDownloadOHLC`, at `scripts/ninjatrader/addons/` with the test project at
> `ninjatrader-addon/`. They now live in this repo as `addons/` and `tests/`, and the deploy
> tool is `tools/sync_nt8.py`. Operative commands and source-of-truth statements have been
> repathed. **Paths inside historical records -- "what landed", migration steps, closed
> defects -- are deliberately left as they were written**: that is what the record said at the
> time, and the hardening plan keys defects to `file:line` across that history. Rewriting them
> would falsify the trail. See [NT8_REPO_SPLIT_PLAN.md](NT8_REPO_SPLIT_PLAN.md).

**Status** (2026-08-13, tag `v1.0.2` deployed, suite **953 passed / 0 failed**):
**57 of 71 closed.** Live in NT8, `shadow`, armed and guarding; NT8 compiles clean (0 errors, net48).

**`P0-63` AND `P?-66` WERE VALIDATED LIVE on 2026-08-13** by a single 1-lot MNQ round trip on
`Sim101 -> Sim-ORB` — the mirrored stop trailed for the first time on a real broker path, and both
fills measured (`142.86 ms / 0 ticks` entry, `314.21 ms / -4 ticks` exit). `P?-66` is **closed**;
handover §5.13 has the event-by-event record.

That one trade also opened **four new defects** (`P0-68`, `P1-69`, `P1-70`, `P1-71`), which is the
return this project keeps getting from a live trade over a test. ✅ **All four, plus `P0-67`, were FIXED and DEPLOYED the same day as core `v1.1.0` + bridge** —
handover §5.14. `P0-68`, `P1-69` and `P1-71` are live-validated; `P1-71` was validated *on the exact
case that motivated it*, and the answer turned out to be a symbol-conversion/sizing interaction
(1 MNQ translated to NQ at ratio 1.0 rounds below one contract). A sixth defect was found by the
`P0-67` trail test and fixed in the same change: two `Change()` calls landing on one stop order in a
single sweep, which per `P0-61` reverts the order.

✅ **`P?-64`/`P?-65` are CLOSED** (handover §5.21, branch `feat/ui-config-single-owner`, unmerged):
the copier UI wrote to a file nothing read, and its save sites destroyed the ratio matrix. The
config path now has one owner in core and the window dispatches requests. Highest open is now
**`P1-77`** — the prop-firm Consistency Rule Shield is enabled by default and evaluated nowhere.

**For "what is left?" read the handover's
[§5, THE OPEN BACKLOG](RISKGUARD_HARDENING_HANDOVER.md#5-the-open-backlog--authoritative-as-of-2026-08-13),
starting at §5.6.** This plan is the reference for *each defect's mechanism and evidence*; the
handover is the reference for *state and order of work*. Keeping both authoritative for both is what
made them disagree.

**Created**: 2026-08-06

## Defect inventory — regenerated from the entries, 2026-08-13

> **This table used to carry a ⚠️ STALE banner instead of being fixed.** It said "58 defects" where
> the handover said 62, listed `P0-51`/`P1-52` as OPEN and then FIXED four lines below, and predated
> `P0-63`/`P0-67`. It is now **derived from the per-defect entries in §1–§5**, which were always the
> accurate part. A warning label is not a fix; see the handover §5.12.

**Numbered once, never renumbered, never reused.** ⚠️ **This paragraph used to assert "83 defect
IDs" while the derivation returned 95** — the same failure the banner above describes, one revision
later. So it no longer asserts a total at all; run the command:

```bash
# how many defect entries this file carries. Run it; do not trust a number written here.
grep -oE "^### ~?~?(P[0-9]\?*-[0-9]+)\." docs/RISKGUARD_COPIER_HARDENING_PLAN.md \
  | grep -oE "P[0-9?]+-[0-9]+" | sort -u | wc -l      # -> 98, re-run 2026-08-14 (session 36)
# ⚠️ It said 95 when it was re-run in session 35 and the true figure was 97 by the time
# anyone read it: P1-97 and P2-98 were filed AFTER the line was written, in the same session.
# That is this file's own lesson arriving one revision later, again -- the command is the
# answer, the number beside it is a comment with a shelf life.
```

**The TOTAL is not maintained here**, because a second copy of a number is a second thing to
forget. It lives in the handover's **§5.0**, which derives it, and it is larger than the figure
above for two reasons: the three untriaged `P?-64`/`P?-65`/`P?-66` have no mechanism write-up here
(handover §5.2), and the non-`P` workstream IDs — `F-9`, `F-9b`, `UI1`…`UI7`, `T1`…`T5` — were
never plan entries.

⚠️ Three IDs appear in the handover's prose and are **not** entries here: `P0-64` and `P0-66` (the
reserved digits, referred to by their eventual band) and `P1-4`. Reserved digits are why `P0-67` is
newer than `P0-63` despite being opened first.

| Band | IDs | Count | Open | Status |
|---|---|---|---|---|
| **P0** — naked-risk / wrong-size | `P0-1`…`P0-9`, `P0-48`…`P0-51`, `P0-53`, `P0-55`, `P0-59`…`P0-63`, `P0-67`, `P0-68` | 22 | **0** | ✅ **The whole P0 band is closed.** `P0-67` and `P0-68` were the third and fourth `Account.Change()` sites and were fixed together on 2026-08-13 (§5.14); `P0-68` is live-validated. `P0-62` is **superseded** by `P0-63`. `P0-9` has both legs closed and live-validated. |
| **P1** — real bugs, not yet live-risk | `P1-10`…`P1-23`, `P1-35`…`P1-37`, `P1-39`, `P1-40`, `P1-42`…`P1-45`, `P1-47`, `P1-52`, `P1-54`, `P1-56`, `P1-57`, `P1-69`…`P1-77`, `P1-79`…`P1-90` | 49 | **5** | ✅ `P1-69`…`P1-71` closed 2026-08-13 (§5.14); `P1-72`…`P1-75` closed the same day (§5.16) — all four found by widening the MCP wrapper, none by a review. `P1-75` is **latent, not historical**: it never fired only because `prop_limits.json` does not exist on this box, and the first prop-limits write creates it. Still open: **`P1-57`** (we would mirror another copier's mirror), **`P1-13`'s threading half**, and `P1-77` (the consistency cap is dead config). ✅ **`P1-79` CLOSED** in handover §5.21 — a released quarantine kept its REASON, because `NormalizeRequest` strips nulls so no request can clear a string field; fixed as an invariant on `ApplyRelationshipRequest`. |
| **P2** — structural | `P2-24`…`P2-29`, `P2-38`, `P2-41`, `P2-46`, `P2-58`, `P2-78`, `P2-82`, `P2-83`, `P2-92`…`P2-95` | 17 | **10** | ✅ **`P2-92` CLOSED 2026-08-13** — shadow mode is observation-only now; 11 mutants / 0 survivors. ⚠️ **`P2-95` NEW**: `FirmStartingBalance` is a session-start heuristic, so the trail-lock floor is wrong by the account's lifetime profit — and `LockAtProfit` was set for the first time the same day. ⚠️ **`P2-94` NEW**: a TIMED manual lockout does not stop new orders. ⚠️ **`P2-93` NEW 2026-08-13**: `pure` and `override_with_friction` are recognised modes that pass preflight's *enforcement* gate (`MinShadowSessions`) and then act on nothing, because `IsActingMode()` names only `live` -- an operator had to WAIT OUT five shadow sessions to reach a mode that enforces nothing. ⚠️ **`P2-92` NEW 2026-08-13**: `shadow` mode is not observation-only — a shadow breach sets `IsLockedOut`, and `CanTrade` reads that flag *above* its own mode/arming escape hatch, so the account stops trading while nothing is flattened. Filed while scoping `F-9`, which arms two more lockout-capable rules. Closed: `P2-28`, `P2-38`, `P2-41`, `P2-46`, `P2-58`, and ✅ **`P2-82` + `P2-83`, both closed by `UI4` on the day they were opened** — the registry was publicly mutable (a caller could invent a rule, which is `P1-77` inverted and fails *un*safe), and a snapshot with no accounts rendered as healthy. Neither was found by review; both came out of writing the producer's tests. Open: `P2-24`, `P2-25`, `P2-26`, `P2-29`, and `P2-27` — **half done**. `OnExecution` is covered and CI is active; `McpBridgeAddOn.cs`/`TradeCopierWindow.cs` are still excluded from the test build, which is why `P1-72`…`P1-75` could only be compile-checked by NT8 itself. |
| **P3** — enhancements | `P3-30`…`P3-34` | 5 | **5** | All open. **`P3-30`'s copier half shipped and is live-validated**; the timer and the RiskGuard-side audit remain. `P3-31`'s seam in `Reconcile` exists, the ledger does not — and **the ledger is required before the timer**. `P3-32` may be **superseded by `P0-9`**; read it before scheduling it. |
| **Untriaged band** | `P?-64`, `P?-65`, `P?-66` | 3 | **0** | Handover §5.2. ✅ **The whole untriaged band is CLOSED.** `P?-66` closed by the live validation — the measurement was never broken; its *reporting* was, and that became `P1-69`. **`P?-64` and `P?-65` closed in handover §5.21** (`UI2`): the config path has one owner in core and the window dispatches requests instead of building domain objects. **Merged and shipped as `v1.3.0`**, deployed to the box with `nt_compile` reporting 0 errors. |
| | | **97** | **18** | **77 closed or superseded** |

> ⚠️ **These counts and the handover's §0 counts are derived independently and have drifted before.**
> `docs/RISKGUARD_HARDENING_HANDOVER.md` §0 is the authoritative one (CLAUDE.md says so); re-derive
> rather than trusting either header. `F-n` feature IDs are deliberately not in this table and must
> not be renumbered into the `P` sequence.

> **Two closures were found by a live operator trade rather than by any test**, and that ratio is the
> plan's real lesson: `P0-49`/`P0-50` (session 8), `P0-51`/`P1-52` (2026-08-09), `P0-59`/`P0-60`
> (2026-08-10), `P0-61` and `P0-62` (2026-08-10). **`P1-57` and `P2-58` were found by watching a
> third-party copier work on the same box** — neither was findable by a test, because both are about
> what *another program's* orders look like to us.

> **ID collision, resolved 2026-08-07 — read this if you are following a git commit or an old
> doc.** `P1-30` and `P1-31` were appended during the P0 work and collided with the pre-existing
> `P3-30` (reconciler) and `P3-31` (expected-position ledger) — four distinct defects sharing two
> numbers. The two newcomers were renumbered; `P3-30`/`P3-31` are unchanged.
>
> | Old | New | Defect |
> |---|---|---|
> | `P1-30` | **`P1-35`** | FSM teardown cancels the orphan auto-stop under `_stateLock` |
> | `P1-31` | **`P1-36`** | Coverage tracks a single stop; two partial stops read as under-covered |
>
> Commits from the P0 phase (`d94d5521` … `f6405c7f`) still say `P1-30`/`P1-31`. Map them here.
> **When adding a defect, take the next free number — do not extend a band in place.**
**Scope**: `addons/{RiskGuardAddOn,TradeCopierEngine,TradeCopierWindow,PropFirmProtectionSuite,DynamicAtmManager}.cs`
**Comparison baseline**: `github.com/mkalhitti-cloud/universal-or-strategy` (V12 Photon Kernel — SIMA fleet dispatch, REAPER defense, Symmetry Guard)
**Related**: [RiskGuardAddOn.md](RiskGuardAddOn.md) (design doc — **contains drift; that is `P2-26`, still open**, and the drift is catalogued in its own header), [NT8_FILE_ORGANIZATION.md](NT8_FILE_ORGANIZATION.md)

---

## 0. Why this review, and what the baseline gives us

Our addons and the V12 strategy solve overlapping problems — multi-account replication and
automated protection of unprotected positions — but from opposite directions:

| Concern | Our addons | V12 (`universal-or-strategy`) |
|---|---|---|
| Replication trigger | `Account.ExecutionUpdate` on the leader, fan-out to followers | Strategy-internal dispatch (`ExecuteSmartDispatchEntry`) before the master order is even submitted |
| Follower risk anchor | none — followers get scaled market orders | `AnchorSnapshot` pinned to the **master's actual weighted fill**, plus `SlippageCushionPoints` |
| Follower brackets | none (`EnableFollowerAtm` is dead config) | "Path B" fixed brackets submitted with the entry |
| Naked-position defense | per-position FSM + one-shot grace timer | FSM **plus** an independent REAPER audit loop that re-derives truth from the broker every cycle |
| Concurrency | one global `lock (_stateLock)`, work marshaled to the WPF dispatcher | zero `lock()`; actor/`Enqueue` model, background audit thread marshals only order calls |
| Submit safety | submit, then record state | reserve/record state **under lock before** submit, roll back on null/reject |
| Desync repair | `ReconcileFollowerPosition` exists but is never called | `REAPER.Repair` + `REAPER.NakedStop` with in-flight dedupe dictionaries and grace windows |

The single most important structural idea to borrow is **REAPER's separation of concerns**:
the FSM is an optimistic fast path, and a *separate, independent auditor* re-derives ground
truth from the broker and repairs whatever the fast path missed. Our FSM has no such
backstop — `FsmWatchdog()` (RiskGuardAddOn.cs:1763) only writes a log line. Every P0 below
is a case where the fast path can lose the position and nothing recovers it.

The second idea worth borrowing is the **reserve-before-submit / rollback-on-failure**
discipline (V12's `A1-1/A2-1` pattern), which we currently invert.

Conversely, we have things V12 lacks and should keep: shadow mode with a preflight gate
(`RunPreflight`, `MinShadowSessions`), friction-gated lockout override, JSONL intervention
log + heartbeat file, and `SeedFsmsForExistingPositions` — a genuinely good state
re-derivation routine that is currently called from only one place.

---

## 1. P0 — Naked-risk and wrong-size defects (fix before any live use)

> ✅ **THE WHOLE `P0-1`…`P0-8` BLOCK IS CLOSED.** It was fixed as tickets `T1`–`T5` in phase 1,
> and the record of each is in the **handover**, not here.
>
> ⚠️ **These eight headings carried no status marker until 2026-08-14 (session 39), and this note
> is what stood in for one.** That was a prose assertion two hundred lines above the entries it
> describes, so every mechanical reading of this file — including `grep`s in the handover that
> derive the counts — returned eight *apparently open* naked-risk defects and needed a human to
> know about this paragraph. A note explaining why a check is wrong is not a substitute for the
> check being right: *a gate nobody reads is a comment*, and this was the inverse again — a
> comment standing in for a gate.
>
> The bodies are still exactly as written, because the plan keys defects to `file:line` across the
> whole history and rewriting those would falsify the trail. Only the status token was appended,
> which asserts nothing this note did not already assert. `tools/check_next_list_ids.py` now
> requires every entry to carry one, so this cannot recur silently.

### P0-1. FSM returning to `Unprotected` never re-arms the grace timer → permanent naked position — CLOSED 2026-08-07 (phase 1, ticket T1)
**Where**: `RiskGuardAddOn.cs:1667-1677` (`UpdateFsmOnOrder`, terminal-stop branch), `1763-1776` (`FsmWatchdog`)
**What happens**: When the recognised protective stop goes terminal (cancelled by the user,
rejected by the broker, or filled on a partial) while the position is still open, the FSM is
set back to `Unprotected` — but no new `GraceTimer` is armed. Grace expiry moved off the sweep
onto per-FSM one-shot timers (`UpdateFsmOnPosition:1591-1606`), and the timer was disposed when
the FSM first left `Unprotected` (`1700-1704`). `EvaluateGraceExpiry` is called from exactly one
place, `OnGraceExpired` (`1633`), so nothing will ever fire again for that position.
`FsmWatchdog` notices and logs `FSM_WATCHDOG` every 5 s, forever, without acting.
**Impact**: Cancel your stop manually (or have a broker reject one) and the position runs
unprotected for the rest of the session with the guard reporting the condition in the log only.
**Fix**:
1. Extract timer arming into `ArmGraceTimer(PositionGuardFsm fsm, Account acct, string instrument)`
   and call it from *every* transition into `Unprotected`, not just FSM creation.
2. Promote `FsmWatchdog` from log-only to remediation: if a FSM has been `Unprotected` past
   `GraceDeadline + StopGuard.WatchdogEscalateSeconds`, re-derive state via the existing
   `SeedFsmsForExistingPositions` logic (refactor it into
   `ReDeriveFsmFromBroker(account, instrument)`), then call `OnGraceExpired`.
3. Borrow REAPER's `_repairInFlight` / `_nakedPositionFirstSeen` pattern: a
   `ConcurrentDictionary<string, DateTime>` keyed by FSM key so escalation fires once per
   naked episode and not once per sweep.
**Test**: position open + stop reaches `Working` → cancel the stop → assert a new grace timer is
armed and `MISSING_STOP_ATTACH` (or `_FLATTEN`) is emitted exactly once.

### P0-2. Auto-stop state is recorded *after* submission and unconditionally — CLOSED 2026-08-07 (phase 1, ticket T1)
**Where**: `RiskGuardAddOn.cs:2595-2611`
**What happens**:
```csharp
if (stopOrder != null) {
    account.Submit(new[] { stopOrder });
    lock (_stateLock) { ... fsm.State = GuardFsmState.ProtectedPending; }
}
```
Three defects in six lines:
- The `OrderUpdate` for the new stop can arrive **before** the lock is taken, so a stop that
  already reached `Working` (state `Protected`) is regressed to `ProtectedPending`; worse, a stop
  that was **rejected** (state correctly reset to `Unprotected`) is overwritten to
  `ProtectedPending` — and per P0-1 no timer is armed, so the position is naked permanently.
- `stopOrder == null` is a silent no-op: no log, no retry, no flatten fallback.
- The submit itself is not wrapped in try/catch here (the outer `ProcessAction` catches, but the
  FSM is then left in whatever state the pre-submit code left it).
**Fix**: adopt V12's ordering — set `fsm.AutoStopOrder`/`State = ProtectedPending` **under lock
before** `Submit`, then roll back to `Unprotected` + re-arm grace if `CreateOrder` returns null or
`Submit` throws. Never write FSM state from the post-submit path; let `UpdateFsmOnOrder` own it
from there. Add an explicit `AUTO_STOP_SUBMIT_FAILED` event and escalate to
`MISSING_STOP_FLATTEN` after `StopGuard.MaxAutoStopAttempts` (new config, default 2).

### P0-3. Auto-stop quantity is a stale snapshot — can flip the position — CLOSED 2026-08-07 (phase 1, ticket T2)
**Where**: `RiskGuardAddOn.cs:2508-2597` (uses `action.Quantity`), `ValidateInvariant:2436-2440`
**What happens**: `ExecuteAction` re-reads the live `position` (line 2511) but then sizes the stop
from `action.Quantity`, captured when the action was emitted. `ValidateInvariant` for
`PlaceStopOrder` only checks `InstrumentObj != null && Quantity > 0` — it does not verify that a
position still exists, its side, or its size.
**Impact**: position scaled down between emission and execution → the auto-stop is **larger than
the position**, and when it triggers it opens a **new position in the opposite direction**. Scaled
up → the stop under-covers and part of the position is silently naked.
**Fix**: size from `position.Quantity` at submit time; assert side matches `orderAction`; reject
the action if the position is flat or the side flipped. Tighten `ValidateInvariant` to look up the
live position and confirm the action is genuinely risk-reducing (this is what the "ActionArbiter"
claims to do — see §6 doc drift).

### P0-4. Scale-in keeps `Protected` without checking stop coverage — CLOSED 2026-08-07 (phase 1, ticket T2)
**Where**: `RiskGuardAddOn.cs:1555-1563`
**What happens**: A same-side quantity update updates `PositionQuantity` in place and explicitly
preserves `Protected`/`ProtectedPending`. Nothing compares `RecognizedStopOrder.Quantity` to
`PositionQuantity`, so 1 → 5 contracts with a 1-lot stop still reports fully protected.
**Fix**: add `GuardFsmState.PartiallyProtected` (or a `CoveredQuantity` field, which is less
invasive). On a same-side increase, if covered < position, re-arm the grace timer for the
uncovered delta and emit `MISSING_STOP_ATTACH` sized to the delta. REAPER does the equivalent by
checking stop *quantity* coverage, not mere existence.

### P0-5. Copier exit sizing is not position-mirroring → follower reverses — CLOSED 2026-08-07 (phase 1, ticket T3)
**Where**: `TradeCopierEngine.cs:401` (`return isExit ? leaderQty : rel.FixedLotSize`),
`427` (`if (isExit) return rawCopyQty;`), consumed at `OnExecution:685-737`
**What happens**: exits are sized from the leader's execution quantity and returned
**unclamped**, never compared to the follower's actual position. In `FixedLot` mode the exit uses
the **leader's raw quantity** and ignores `FixedLotSize` entirely.
**Concrete failure**: `FixedLotSize = 1`. Leader buys 5, follower buys 1. Leader sells 5 →
follower submits `Sell 5` while holding 1 → **follower ends up short 4 contracts** on a market
order, with no stop (P0-9) and no reconciliation (P2-24).
The same happens after any clamp by `MaxPositionSize`, any failed entry copy, or any
micro/mini rounding difference.
**Fix**: route every copy decision through the already-written but **never called**
`CalculateSafeFollowerDelta` (`TradeCopierEngine.cs:165`) — it clamps a reducing delta to
`Math.Abs(currentFollowerQty)` and blocks opposite-side market opens, which is exactly the guard
needed. Target-position mirroring (compute the follower's *desired* position from the leader's
*resulting* position, then submit the delta) is strictly safer than replaying execution
quantities; adopt it.

### P0-6. Micro→Mini conversion floors to 1 contract → 10× notional — CLOSED 2026-08-07 (phase 1, ticket T3)
**Where**: `TradeCopierEngine.cs:426` — `Math.Max(1, Math.Round(leaderQty * absRatio * symbolMultiplier))`
**What happens**: with `symbolMultiplier = 0.1` (MNQ→NQ), a leader trading 5 MNQ yields
`Math.Max(1, round(0.5))` = **1 NQ = 10 MNQ equivalent**, i.e. 2× intended notional; a leader
trading 1 MNQ yields 1 NQ = **10× intended notional**. Any `QuantityRatio < 1` hits the same floor.
**Fix**: floor to 0 and skip the copy (log `SUB_MINIMUM_SKIPPED`) instead of `Math.Max(1, …)`.
Optionally carry a per-(relationship, instrument) fractional residue accumulator so repeated
sub-1 copies eventually emit one contract. Add a hard notional-parity assertion in tests:
`followerQty × followerPointValue ≈ leaderQty × leaderPointValue × ratio`.

### P0-7. Peak-giveback rule compares incompatible quantities → fires on every profitable flat account — CLOSED 2026-08-07 (phase 1, ticket T4)
**Where**: `RiskGuardAddOn.cs:1154`, predicate at `PropFirmProtectionSuite.cs:104-111`
**What happens**: `EvaluatePeakEquityGiveback(peakOpenGain, currentUnrealized)` is called as
`EvaluatePeakEquityGiveback(stateModel.PeakEquity, stateModel.UnrealizedPnL, …)`.
`PeakEquity` is the peak of **Realized + Unrealized** (`1038-1040`), the second argument is
**Unrealized only**. An account that banked +$2,000 and is now flat gives
`giveback = 2000 - 0 = 2000`, `givebackPct = 1.0 ≥ 0.30` → `PEAK_GIVEBACK_BREACH` →
`FlattenPosition` emitted on **every** `AccountItemUpdate`.
**Impact**: harmless while flat (nothing to flatten), then it instantly flattens the next
position taken after any profitable session. Note this branch deliberately does *not* set
`IsLockedOut`, so it never latches and never stops.
**Fix**: define one basis and use it consistently. Recommended: track `PeakOpenGain` (peak of
unrealized only, reset on flat) and compare against current unrealized; or track
`PeakTotalPnL` and compare against current total. Add a `position != flat` precondition and a
latch so the rule fires once per episode.

### P0-8. The copier is the only order path that bypasses the RiskGuard lockout — CLOSED 2026-08-07 (phase 1, ticket T5)
**Where**: `TradeCopierEngine.OnExecution:645-737` vs `McpBridgeAddOn.cs:2252`, `2315`, `3966`
**What happens**: every order path in `McpBridgeAddOn` checks
`RiskGuardAddOn.Instance.IsAccountLocked(...)` before submitting. The copier does not. A follower
that RiskGuard has locked out for a daily-loss breach will still receive fresh copied entries;
RiskGuard's lockout sweep then fights the copier — cancel/flatten every 5 s against new entries
arriving on every leader fill.
**Fix**: gate the per-relationship loop on the public API that already exists for this —
`RiskGuardAddOn.Instance.CanTrade(followerName, instrument, "TradeCopier")` (`RiskGuardAddOn.cs:108`)
— and auto-quarantine the relationship (P2-24) when the follower is locked. Also skip copying
*from* a locked leader.

### P0-9. Followers are left naked — no bracket replication — naked exposure CLOSED 2026-08-07 (stops); targets/ATM still open — PARTIALLY CLOSED 2026-08-10 (three recorded non-goals below)
**Where**: `TradeCopierEngine.OnExecution:721-738` (always `OrderType.Market`, no protective legs);
`EnableFollowerAtm` / `FollowerAtmStrategyName` are carried between DTOs (`:91`, `:36-37`) and
**never read**
**What happens**: followers receive bare market orders. Their only protection is RiskGuard's
`StopAttachSeconds` grace → `RiskGuardAutoStop` at a fixed tick offset from *average price*
(`RiskGuardAddOn.cs:2545`), which bears no relation to the leader's actual stop. If RiskGuard is
disarmed, in shadow mode, or the follower is in `ExcludedAccounts`, there is no stop at all.
**Fix** (in preference order):
1. Replicate the leader's protective legs: on leader stop/target `OrderUpdate`, mirror them to
   followers scaled by the same quantity function, anchored to the **follower's own fill** (V12
   Symmetry Guard pattern) rather than the leader's price.
2. Failing that, implement `EnableFollowerAtm` by submitting a fixed bracket at copy time
   (V12 "Path B") using a stop distance derived from the leader's stop, with
   `SlippageCushionPoints`-style padding so follower dollar risk ≤ the configured cap.
3. Minimum bar: refuse to copy to a follower unless RiskGuard is armed, live, and subscribed to
   that account — fail closed, log `COPY_BLOCKED_NO_GUARD`.

**Fixed by (option 1, stops only) — 2026-08-07.** Followers are no longer naked. The copier now
subscribes to `OrderUpdate` (via `P1-21`'s subscription seam), recognises the leader's protective
stop, and mirrors it to every follower:

```
followerStop = followerEntry -/+ |leaderPositionAvgPrice - leaderStopPrice|
```

**The stop carries the leader's risk DISTANCE, anchored to the follower's own fill — not the
leader's stop price.** Copying the price is wrong by exactly the slippage `P1-22` now measures,
and wrong by an entire price scale across a micro/mini conversion. A follower that filled 2 points
worse than the leader gets the same 10 points of risk, not 12.

Lifecycle, each pinned by a falsifiable test:

| Behaviour | Test |
|---|---|
| Distance anchored to the follower's fill | `TestBracket_StopMirrorsLeaderDistanceFromFollowerFill` |
| Leader stop seen *before* the copy fills is held and applied on the fill | `TestBracket_StopBeforeFollowerFillIsAppliedOnFill` |
| Leader trailing its stop replaces, never duplicates | `TestBracket_MovingLeaderStopReplacesRatherThanDuplicates` |
| Follower flat → mirrored stop cancelled | `TestBracket_FollowerGoingFlatCancelsTheMirroredStop` |
| Price-incomparable instruments are not mirrored | `TestBracket_IncomparableInstrumentsAreNotMirrored` |

Notes that are not obvious:

- **The classification is RiskGuard's, not a second copy.** `IsStopType`, `IsProtectiveSide` and
  `IsPendingOrWorking` were promoted from `private` to `internal` and are reused. Two definitions
  of "the order protecting this position" would drift, and the copier's would be the one that
  silently stopped recognising a stop.
- **Cancel-then-replace, not modify.** A stale stop left working beside a new one over-covers: when
  both fire the follower is flipped to the opposite side.
- **Every broker call is outside `_lock`** (`P1-10`/`P1-35`). `SyncFollowerStop` computes under the
  lock, releases, then calls `Cancel`/`CreateOrder`/`Submit`.
- **An orphan stop is not a leftover, it is a new position.** Releasing on flat is why
  `UpdateFollowerBracketOnFill` re-reads `account.Positions` rather than accumulating from
  executions — the fill may be our copy, the mirrored stop firing, or a manual trade, and only the
  broker knows the net.
- **The mirrored stop is also visible to RiskGuard**, which will seed the follower's FSM as
  `Protected` instead of firing `MISSING_STOP_FLATTEN` at the grace deadline.

> ### 2026-08-10 research: mirroring the target IS possible. Two API facts that decide the design.
>
> An earlier note here claimed `Order.Oco` is create-time only and a working order cannot be
> joined to a group. **That was wrong** — `Order.Oco` has a public setter. What is true, and what
> actually constrains the design, was established by reflecting on `NinjaTrader.Core.dll` and by
> two live runs:
>
> 1. ~~**An OCO id cannot be REUSED.**~~ **CORRECTED 2026-08-10 by controlled live test — handover
>    §4p.** The rule is about the GROUP'S LIFE, not the id's history: **an id can be JOINED while its
>    group still has a live member, and is rejected only once every leg has gone terminal.** Proved
>    by submitting one identical order twice under the same id — `Working` while the bracket was
>    alive, `Rejected` after the group was retired. So re-creating ONE leg beside a still-working
>    sibling may keep the same id, and per-generation ids are needed only for the fully-dead-group
>    case. The original wording was inferred from a single `Rejected` `COPIER_TARGET`, which carried
>    a *distinct* id and so cannot have been rejected for reuse at all.
> 2. **There is no `OcoChanged` field.** `Order` has `LimitPriceChanged`, `StopPriceChanged` and
>    `QuantityChanged`, which is what `Account.Change()` carries, so an already-working order
>    cannot be moved between groups. Modifying price/qty in place is fine and preserves the group —
>    **confirmed live 2026-08-10** (§4p): a trailed stop kept its `orderId` AND its `oco` on the
>    leader and on both Replikanto followers, with the sibling target untouched.
> 3. **Consequence: the trail path never re-creates a leg, so it never needs a fresh id.** With (1)
>    corrected, the only case requiring a new id is a group that has already gone fully terminal. The
>    per-generation redesign this entry originally demanded shrinks to one conditional: keep the id
>    while any sibling is live, mint a fresh one only when the group is dead.
>
> Also useful: `Account.CancelOrdersByOcoID(orders, ocoId)` is a real group-cancel primitive, and
> `Connection.Features` answers capability at runtime. On this box the TPT connection serving both
> Sim and the funded accounts advertises `Order`, `OrderChange` and `NativeGtdOrders` but **not**
> `NativeOcoOrders` — so OCO here is NT8-simulated, not broker-native. Probe it with
> `GET /api/connections`.
>
> ~~**Status: parked on branch `wip/p09-oco-target`, NOT deployed.**~~ **CLOSED and deployed
> 2026-08-10 (`86c6376f`).** See "Item (1) shipped" below. The parked branch is superseded — it was
> rebased onto the `SyncFollowerStopOnce`/holder split and gained five things it did not have.

#### Item (1) shipped — 2026-08-10, `86c6376f`. Suite 653/0 → 686/0, `nt_compile` 0 errors, deployed

The follower receives the leader's target as well as its stop, anchored to its own fill by the
same signed distance, with both legs in one OCO group. **The asymmetry between the legs is the
design and must not be tidied away**: the stop is risk and may re-mint the OCO id and tear the
target down to rebuild the pair; the target is upside and never cancels or re-creates the stop.

Five things the parked branch did not have, four of which are live-risk:

| | What | Why it matters |
|---|---|---|
| 1 | **The dead-group id conditional** | Re-using the id on the cancel-then-create path has the broker reject the new **stop**. A naked follower produced by the target feature, on the leg it is not about |
| 2 | **`P1-56`'s reservation on the target leg** | The parked target sync had none and carried the duplicate-leg defect verbatim. Its own flags, not the stop's — sharing would let an in-flight target sync make the risk leg wait |
| 3 | **A bounded target budget** (`MaxBracketTargetAttempts`) | The parked target could be re-submitted forever against a rejecting broker. Kept separate from `StopAttempts` so target churn cannot spend the stop's budget |
| 4 | **The OCO-retirement guard** | When the target fills NT8 cancels the stop; the copier read that as a *lost* stop and re-submitted it against a position that had just closed. `P0-50`'s orphan, by a route that did not exist until targets were mirrored. **A leg whose sibling FILLED was retired, not lost** |
| 5 | **Tick rounding on both legs** | The anchor is an average fill price and averages land between ticks. This is the likely cause of the `COPIER_TARGET` Rejected at **29905.625** on a 0.25-tick instrument — §4p's "suspected, not concluded", now fixed either way |

**A multi-target leader is not mirrored at all.** A scale-out bracket has several targets and the
follower has one mirrored leg, so there is no honest answer: last-seen makes the follower's exit an
artefact of NT8's event ordering, and nearest exits the follower's *whole* position at the leader's
*first* partial. It withdraws the target, logs `BRACKET_TARGET_AMBIGUOUS`, and keeps the stop — the
follower still exits on the copied leader fills, which is the behaviour that shipped before targets
existed. Deliberately **not** applied to stops: several working stops is a reconciliation problem
(`P1-36`, `P3-30`) and dropping the risk leg over it is the wrong trade.

Nine tests, hand-written first, every guard verified falsifiable by mutation rather than by
argument. What each mutation produced: retirement guard off → the orphan stop is submitted (2 vs 1);
id re-used → the retired group's id is carried onto the new stop; reservation off → 2 live targets;
re-drive removed → a 1-lot target behind 2 lots; rounding off → both legs at `.125` on a 0.25 tick.

> ⚠️ **Deployed but NOT live-validated**, like `P0-53`/`P1-54`/`P0-55`/`P1-56`. Two things now differ
> on the *stop* path and neither has been seen on a real fill: the stop carries an **OCO id** where
> it used to carry `""`, and its price is **rounded to tick**. The id is what lets a later target
> join rather than forcing the protective stop to be re-created — but a single-member OCO group is
> inferred to be harmless, not proven. Watch the first live `COPIER_STOP` for a rejection.

**Explicitly NOT done — do not read this as P0-9 fully closed:**

1. ~~**Profit targets and OCO pairing.**~~ **CLOSED 2026-08-10, `86c6376f`** — see above. What is
   still not done inside it: a **multi-target (scale-out) leader is refused rather than mirrored**,
   and partial-fill **re-pairing** across a scaled leader position is untested.
2. ~~Option 2 (`EnableFollowerAtm` / `FollowerAtmStrategyName`) is still unread config~~ —
   **RESOLVED by deletion.** Both fields were carried between DTOs and read by nothing: not
   parsed in `LoadFromDisk`, not exposed by the bridge API, not shown in the UI. They could not
   be set by any means, while implying followers were getting an ATM bracket. Removed, per
   `P1-23`'s rule that config must not lie.
   > **A copier-side DEFAULT bracket was deliberately not built in their place.** RiskGuard's
   > `StopAttachSeconds` → auto-stop already owns "position with no stop". Two independent stop
   > sources on one position over-cover, and when both fire the follower is flipped — the same
   > hazard the cancel-then-replace rule above exists to prevent, but across two components that
   > cannot see each other. If the leader never sets a stop, RiskGuard is the answer, not a
   > second mechanism.
3. **`StopLimit` leaders become `StopMarket` followers.** The limit offset is not carried.
   > **Assessed and accepted, not overlooked.** The trigger price is mirrored correctly; only the
   > post-trigger order type differs. A `StopMarket` is *more* likely to fill than a `StopLimit`,
   > so the divergence is toward the follower being protected, never toward a wrong or unfilled
   > exit. It is a fidelity gap, not a safety one.
   > **Investigating it is what found the signed-offset defect below**, which was a safety one.
4. **A leader that CANCELS its stop but stays in the position leaves the follower's stop working.**
   Deliberate — fail-safe — but it is a divergence from the leader, and it is not tested.

> Tracked as follow-on work rather than a new defect number, since `P0-9` remains open for (1),
> (3) and (4). The naked-follower exposure that made it P0 is closed.

#### The signed-offset defect — shipped in `76137575`, fixed same session

The first implementation computed `Math.Abs(leaderAnchor - stopPrice)` and always subtracted it
for a long. **A leader trailing its stop into profit puts the stop ABOVE its entry on a long**, and
the absolute distance mirrored that as a stop the same distance BELOW the follower's entry —
converting the leader's locked-in gain into open risk of equal size, on every follower, silently
and on the most ordinary trade management there is.

The offset is now signed and one expression covers both sides:

```
followerStop = followerEntry + (leaderStopPrice - leaderPositionAvgPrice)
```

**The original trail test could never have caught it**: it moved the stop 17990 → 17995 → 17998,
all below entry. Two tests now cover the inversion on both sides
(`TestBracket_StopTrailedIntoProfitStaysAboveFollowerEntry`,
`TestBracket_ShortStopTrailedIntoProfitStaysBelowFollowerEntry`), and the revert case reproduces
the exact shipped defect.

> **How it was found is the transferable part.** Not by a test, a gate, or review — by the
> operator asking whether item (3), the `StopLimit` conversion, could trigger wrong orders.
> Answering that honestly meant re-deriving what price the follower's stop actually lands on,
> which is when the `Math.Abs` became visible. **A test suite confirms the cases you thought of.**

### P0-49. The mirrored stop is never placed, because the anchor is read before the position exists — CLOSED 2026-08-07
*(found by an operator ATM trade on the live box, 2026-08-07 — not by any test)*
**Where**: `TradeCopierEngine.UpdateFollowerBracketOnFill`, called only from the follower's
`ExecutionUpdate`
**What happens**: the bracket's anchor (`FollowerEntryPrice`/`Side`/`Quantity`) was derived by
re-reading `followerAcc.Positions` at execution time. **NT8 raises `ExecutionUpdate` BEFORE
`PositionUpdate`**, so on an entry fill there is no position row yet: the method took its flat
branch, called `ReleaseFollowerBracket`, and returned. The anchor was never set.

Nothing rebuilt it. An ATM stop sits at `Accepted` and raises no further `OrderUpdate`, so
`OnLeaderOrderUpdate` never fired again either. **The follower was naked for the entire trade** —
precisely the exposure `P0-9` exists to close, surviving in the trigger rather than the arithmetic.

Observed live, Sim101 → Sim-ORB, MNQ SEP26:

```
15:43:21.237  Created FSM Sim-ORB|MNQ SEP26 -> Unprotected
15:43:24.241  [SHADOW] Would execute FlattenPosition triggered by MISSING_STOP_FLATTEN
15:45:22.572  COPIER_STOP finally submitted -- as the position was CLOSING
```

**Fixed**: the copier subscribes to `Account.PositionUpdate` for follower accounts, which is the
authoritative anchor source. On the execution path a flat read is ambiguous, and the anchor
disambiguates it — a bracket that has never held a position (`FollowerEntryPrice` is `NaN`) has
nothing to exit *from*, so flat means "the position event is still in flight"; once an anchor
exists, flat means flat and the bracket is released as before.

> **The first version of this fix simply stopped releasing on the execution path, and
> `TestBracket_FollowerGoingFlatCancelsTheMirroredStop` caught it immediately.** Releasing on flat
> is load-bearing; the defect was never that it released, only that it could not tell the two
> kinds of flat apart.

**The arithmetic was correct throughout.** The live stop landed at 29774.25 = follower entry
29789.25 + (29774.5 − 29789.5). `P0-9`'s signed offset is now **confirmed on real fills**.

### P0-50. Orphan mirrored stops submitted against a follower that is already flat — CLOSED 2026-08-07
*(found in the same live trade)*
**Where**: `TradeCopierEngine.SyncFollowerStop`
**What happens**: the method trusted the bracket's snapshot of the follower all the way to
`Submit`. When the follower had gone flat in the meantime, it submitted a protective stop anyway —
three of them on the live box (`34225`, `34226`, `34227` at 15:45:22 / :30 / :31), each cancelling
the last, all against a flat account, each consuming one of `MaxBracketStopAttempts`.

**An orphan stop on a flat account is not a leftover. It opens a position in the opposite
direction the moment it triggers.** The design doc already says this under `P0-9`; the code did
not enforce it on this path.

**Fixed**: `SyncFollowerStop` re-reads the live position immediately before touching the broker
and aborts on flat (`BRACKET_ABORTED_FLAT`) or on a side mismatch (`BRACKET_ABORTED_SIDE`),
cancelling any stale stop on the way out. Quantity is taken from the live position too, so a
follower that scaled out in between cannot receive a stop larger than the position it covers.
This is the same discipline T2 already applies to `RiskGuardAutoStop`, and for the same reason.

---

### P0-51. Shadow mode does not restrain the lockout — the sweep flattens for real — CLOSED 2026-08-09
*(found by a live operator ATM trade on 2026-08-09, the same way `P0-49`/`P0-50` were)*
**Where**: `RiskGuardAddOn.cs:1848-1889` (the lockout watchdog collects `cancelBatches` and
`flattenBatches`) and `:1899-1940` (it executes them: `batch.Key.Cancel(...)` at `:1901`,
`account.Flatten(...)` at `:1913`)

**What happens**: there are **two parallel paths out of a lockout, and only one is mode-gated.**

1. `EvaluateLockoutPhase` (`:2718-2735`) emits a `FlattenPosition` `GuardAction`, which goes
   through `ProcessAction`'s shadow gate at `:3277-3285` and correctly returns `SHADOW (SKIPPED)`,
   logging `[SHADOW] Would execute action FlattenPosition triggered by LOCKOUT_FLATTEN`.
2. The lockout watchdog sweep at `:1848` builds its own batches **with no `_mode` check anywhere
   in the block**, and after the lock releases calls `Cancel` and `Flatten` straight at the broker.

Path 2 does the work. The guard announces it is only observing, and flattens the account anyway.

**Observed live, 2026-08-09 21:15:25 ET.** A false flood lockout (`P1-52`) hit `Sim101`,
`SimCopyTest1` and `SimCopy2`. All three logged `[SHADOW] Would execute action FlattenPosition`,
and all three were then really flattened: market orders `34256`/`34257`/`34258`, action `Sell`,
qty 2, **name `"Close"`** — the name NT8's `Account.Flatten()` gives its close order — filled at
29848.75 within 15 ms of each other.

> **Manual operator action is ruled out.** A human "flatten everything" would also have closed
> `Sim-ORB`, which was long 2 on the same instrument at the same moment. `Sim-ORB` was the one
> account that had **not** tripped the lockout, and it was the one account left untouched. The
> flatten tracked lockout state exactly.

**Why this is P0 and not a tidiness issue.** Phase A's entire premise is that shadow is a safe
place to observe a guard that is not yet trusted — `:443` prints *"it observes and logs; it cannot
act outside 'live'"* on every startup. That statement is false for every lockout rule: order
flood, consecutive losses, daily loss. Any subscribed account, including a funded one, can be
cancelled and flattened by an addon the operator believes is inert.

**Fix**: the sweep must not reach the broker outside an acting mode. Do **not** simply wrap `:1899-1940`
in `if (_mode == "live")` and stop there — that leaves the divergence in place for the next path
that grows its own broker call. Route the sweep's cancel/flatten through the same arbiter +
mode gate every other action uses, so there is exactly one place where "may I touch the broker"
is answered. Until then, treat shadow as an **acting** mode for lockouts.

**A test would not have caught this by construction.** The suite exercises `ProcessAction`'s gate,
which is correct. Nothing asserts the *negative* — that in shadow mode, no broker call is issued
by any path. `S4`'s `BrokerCallObserver` is the machinery to assert it with; §0's lesson 2 ("a
machine check is only as good as the paths driven through it") applies verbatim, for the third time.

**Fixed 2026-08-09.** One predicate, `IsActingMode(bool forceLive = false)`, now answers "may I
touch the broker". `ProcessAction` calls it in place of its inline expression (behaviour unchanged)
and the lockout sweep calls it too.

The half that mattered was the **deferred cancel queue**, and two candidates got it wrong before
one got it right — both passing every gate:

| Attempt | What it did | Why it was wrong |
|---|---|---|
| 1 | Gated `DrainPendingCancels()` at the sweep's call site | The drain has **four** call sites; `ExecuteOrderUpdate` drains it too, so shadow still cancelled the trader's orders. Also left the queue growing all session, to fire as a stale burst on a mode switch |
| 2 | Drained unconditionally in every mode (the arbiter's own remedy) | Reintroduces the defect: four of the five enqueue sites are interventions against the trader's orders |
| 3 ✅ | Moved the decision **inside** `DrainPendingCancels` and gave the queue an intent | Covers all four call sites by construction |

`_pendingCancels` now carries `PendingCancelIntent`:

- **`Intervention`** — the trader's orders (lockout entry-cancel, blacklist, per-instrument cap).
  Withheld in a non-acting mode **and discarded**, never retained. Counts log as
  `SHADOW_PENDING_CANCEL`.
- **`Cleanup`** — RiskGuard's own orphaned auto-stop, from `UpdateFsmOnPosition`. Sent in **every**
  mode. Skipping it strands an orphan stop on a flat account, which opens a new position when it
  triggers — that is `P0-50`, and the review panel was right to catch it.

Pinned by six acceptance tests written before the fix. `P1-10`/`P1-35` and `P1-11` are preserved;
live-mode behaviour is unchanged. NT8 `nt_compile`: **0 errors** under net48.

---

### P1-56. Concurrent bracket syncs create duplicate protective legs — CLOSED 2026-08-10
**Where**: `TradeCopierEngine.SyncFollowerStop` (and the parked `SyncFollowerTarget`)
**What happens**: `bracket.WorkingStop` is set to `null` under `_lock` **before** the broker call
and only reassigned **after** `Submit`. A second sync entering that window sees `null`, concludes
there is no working stop, and creates another one.

**Observed live 2026-08-10 01:02** on a clean 2-lot ATM: `Sim-ORB` finished with `COPIER_STOP`
qty **1** and `COPIER_STOP` qty **2** against a 2-lot position — three contracts of stop, both
orders carrying the same creation timestamp. Over-cover: when both fire the follower is flipped
to the opposite side, which is the exact hazard the cancel-then-replace rule was written to avoid.

The window is **pre-existing** and not caused by the target work. A partial fill plus the P0-55
re-anchor gives two sync triggers a few milliseconds apart; the target work doubled the number of
sync invocations and turned a rare interleaving into a reproducible one.

**Fix**: reserve before submit, with rollback on failure — the pattern `T2` already established
for RiskGuard's auto-stop (`P0-2`/`P0-3`). Publish a placeholder into `WorkingStop` (or an
in-flight flag) under the lock *before* releasing it, so a concurrent caller sees the reservation
rather than a gap, and clear it if `CreateOrder`/`Submit` fails.

> **The unit suite cannot see this** — 653 passed with the defect live. The tests drive the sync
> paths sequentially; the defect only exists when two triggers interleave. Any fix needs a
> concurrent test, and the `S`-series is sequential too (see the handover's warning about `P1-13`).

**Fixed 2026-08-10.** The body became `SyncFollowerStopOnce`; `SyncFollowerStop` kept its signature
and became the reservation **holder**. It publishes `StopInFlight` under `_lock` before any broker
call, runs a bounded re-drive loop (`MaxBracketResyncPasses`), and clears the flag exactly once in a
`finally` that runs **after** the loop — so there is no instant between passes at which a third sync
sees no reservation. A sync arriving mid-flight sets `StopResyncOwed` and returns without touching
the broker or `StopAttempts`; the holder then re-drives so the newer size/price is applied. Both
`bracket.WorkingStop = null` clears are gone, here and in `OnFollowerOrderUpdate`: an honest
`WorkingStop` is what makes an entering sync **modify** the existing order via the `Change()` trail
path rather than create a second one, and it lets `ReleaseFollowerBracket` still cancel a leg an
abort abandoned.

Pinned by two hand-written concurrent tests — `…InterleavedSyncsLeaveExactlyOneProtectiveStop`
(red at baseline: two live stops, qty 2+1 behind 2 lots) and a **three-sync** variant, because the
arbiter recorded "there is no gap between passes" as settled on argument alone. Plus
`…AFailedSubmitDoesNotWedgeLaterSyncs`, which guards the failure mode the fix introduces if written
carelessly: a reservation leaked on a throwing path is permanent and worse than the defect. Suite
**653 passed / 0 failed**; `nt_compile` 0 errors; synced and hot-swapped.

> ⚠️ **Two candidates from the agent loop would have shipped live defects, and both passed every
> gate.** Recorded because the pattern is the point, not the incident.
>
> 1. Round 1's reviewers correctly found a window, then all three — **arbiter included** — endorsed
>    "leave `StopInFlight` set when a re-sync is owed and let the re-drive's own `finally` clear it".
>    The re-drive's first act is to test `StopInFlight` and back off, so it returns without ever
>    reaching a `finally`: **the reservation leaks forever** and that follower can never be given
>    another stop.
> 2. The apply run produced and applied a **third, unreviewed** candidate (`--resume-raw` reseeds
>    round 1; a `REVISE` then triggers a fresh round 2). It set `countAttempt = (pass == 0)`, so
>    re-drive passes reached the broker **without counting an attempt** — turning
>    `MaxBracketStopAttempts = 3` into effectively 9 submissions, the order-flood mode `P1-40`,
>    `P2-46` and the flood cluster have already cost us — and it restored `WorkingStop = null` on the
>    `catch` and abort paths, losing track of a possibly-live stop and reintroducing **this very
>    defect**. Caught by §9 step 3, reverted, and the reviewed candidate spliced in via the loop's own
>    region machinery and verified byte-identical to the gated `final.patch`.

---

### P1-57. We would mirror another copier's mirror — the "not ours" test is a name substring — ✅ CLOSED 2026-08-13 (session 34: reference-tracking order filter)
**Where**: `TradeCopierEngine.OnLeaderOrderUpdate` — `if (!string.IsNullOrEmpty(order.Name) && order.Name.Contains("COPIER")) return;`
(and the same substring test in `ReevaluateLeaderStops`'s candidate filter)

**What happens**: the only thing stopping the copier mirroring a mirrored stop is that *our own*
legs are named `COPIER_STOP`. A third-party copier's legs are not. **Replikanto copies its leader's
order names verbatim** — its mirrored legs on a follower are called `Stop1` and `Target1`, exactly
like a native NT8 ATM bracket. So if an account is both another copier's follower and one of our
leaders, we read its mirrored stop as a genuine leader stop and mirror it onward.

**This path exists on the box today.** `Sim-ORB` is our follower (`Sim101 -> Sim-ORB`) *and*
Replikanto's leader, so the live chain is `Sim101 -> Sim-ORB -> {SimCopyTest1, SimCopy2}`. Observed
2026-08-10 01:56:56: a 1-lot bracket on `Sim-ORB` produced identical `Stop1`/`Target1` legs on both
of Replikanto's followers within ~12 ms and ~29 ms, each under its own fresh OCO id.

Two consequences, and the second is the dangerous one:
1. A mirrored distance gets re-mirrored down a chain, so the far end's risk is anchored to an entry
   two hops away.
2. **Any live validation now fans out further than intended.** A `Sim101` test trade reaches three
   follower accounts, not one — which matters for `P1-56`'s live validation specifically.

**Fix**: stop identifying our own orders by name substring. Track the orders we submit by object
reference (the same discipline `P0-9`'s settled decision already requires for pending copies and
recognised stops, precisely because names and ids are unreliable), and refuse to anchor to an order
we did not observe the leader place itself. A name test cannot distinguish "a bracket the trader
placed" from "a bracket another program placed on the trader's behalf", and it never will.

> **Do not fix this by adding more name patterns.** Matching `Stop1`/`Target1` would blacklist the
> most common *legitimate* NT8 ATM names and stop mirroring real brackets — the failure mode is
> inverted and worse.

---

### P2-58. The "is this a manual bracket" diagnostic in the handover is wrong — CLOSED 2026-08-10
**Where**: `RISKGUARD_HARDENING_HANDOVER.md` §4o, "Operational gotchas found the hard way"

**What happened**: that note told the next person that overlapping leader brackets are told apart by
the leader's order *names* — `Stop1`/`Target1` for a manual/ATM bracket versus `Stop_<bracketId>`
for ours. Since another copier reproduces its leader's names verbatim (`P1-57`), a follower carrying
`Stop1`/`Target1` may be a *mirror*, not a manual bracket. The documented tell was not a tell.

This was P2 because it cost debugging time rather than money — but it is the kind of confidently
wrong note that sends someone down the wrong path for an hour, which is exactly what `P2-26` exists
to catch elsewhere.

**Fixed 2026-08-10** (`a727d2da`). §4o now carries the correction inline rather than relying on the
reader reaching §4p two sections later, and names a replacement tell: **order count against position
size, and the `oco` field**. Both are properties of the orders themselves rather than of what
someone chose to call them.

> The general lesson is `P2-26`'s: a correction recorded only where it was *discovered* leaves the
> wrong claim standing where it is *read*. Fix it at the point of use.

---

### P0-59. An order being MODIFIED reads as dead, so the copier duplicates the leg — CLOSED 2026-08-10
*(found by the first live validation of the mirrored target — handover §4s)*

**Where**: `RiskGuardAddOn.IsPendingOrWorking` (`:2208`), consumed by
`TradeCopierEngine.OnFollowerOrderUpdate`, `SyncFollowerStopOnce` and `SyncFollowerTargetOnce`

**What happens**: NT8 moves an order through **`ChangeSubmitted` / `ChangePending`** while
`Account.Change()` is in flight. `IsPendingOrWorking` lists only
`Submitted | Accepted | Initialized | Working | PartFilled`, so a leg that is merely being modified
is classified as **not alive**. Two consumers then act on that:

1. **`OnFollowerOrderUpdate` treats `!IsPendingOrWorking` as "went terminal"** — but the predicate's
   complement is not `IsTerminal` (`Cancelled | Rejected | Filled`). `ChangeSubmitted` falls in the
   gap between them, so a leg mid-modification is logged `BRACKET_STOP_LOST` / `BRACKET_TARGET_LOST`
   and **re-submitted**.
2. **`SyncFollower*Once` computes `stillLive = IsPendingOrWorking(existing.OrderState)`.** False
   means `toCancel` is never set, so the create path runs **without cancelling the order it is
   replacing**. Two live legs behind one position.

**Observed live 2026-08-10 13:55:56** on `Sim-ORB` (MNQ SEP26, long 1): `COPIER_TARGET` 34367
entered `ChangeSubmitted`, and the copier created `COPIER_TARGET` 34371 — `BRACKET_TARGET_MIRRORED`
at .3437, before 34367's change even reached the broker at .3537. Both finished **`Working` at
29859.75 in the same OCO group**, and the third-party copier faithfully mirrored the pair onward, so
three accounts each carried two targets against one lot.

**This is not specific to targets, and it is not caused by the target work.** The identical hole is
on the **stop** path and predates it: our own trail calls `Account.Change()` (`BRACKET_MODIFIED`),
which puts the mirrored stop through `ChangeSubmitted` on **every trail step**. Two protective stops
behind one position is `P1-56`'s live symptom reached by a different route — and one the `P1-56`
reservation cannot prevent, because no concurrency is required: a single sync misreading one state
is enough.

**Why no test caught it, and why none could**: the test stub's `OrderState` enum
(`RiskGuardAddOnTests.cs:23`) does not declare `ChangeSubmitted` or `ChangePending` at all. The
state does not exist in the test build, so the suite was green at 686/0 with this live. Same shape
as `P0-49` — *"the test stub raises whatever the test raises"* (§6) — one level lower down, in the
enum rather than the event order.

**The codebase already disagrees with itself**: `McpBridgeAddOn.cs:3419`'s `activeStates` correctly
includes `ChangePending`. Two definitions of "this order is alive", and the copier uses the wrong one.

**Fix**:
1. Add `ChangeSubmitted` and `ChangePending` to `IsPendingOrWorking`. Declare them in the stub enum
   first, and drive a leg through them in a test — the fix is worthless if nothing can express it.
2. **Stop inferring "terminal" from `!IsPendingOrWorking` in `OnFollowerOrderUpdate`.** Test
   `IsTerminal` explicitly. The two predicates are not complements and must not be treated as such;
   any future state NT8 adds lands in the same gap otherwise.
3. Audit every other `!IsPendingOrWorking` / `IsPendingOrWorking` call site for the same inference.

**Fixed 2026-08-10 (`b5c58ae0`), together with `P0-60` — they are one defect seen from two sides.**
See `P0-60` for the model. Verified by mutation: restoring the old belief reproduces the live
incident exactly (2 `COPIER_TARGET`s), and shows the trail path duplicating the **stop** too.

---

### P0-60. Two addons, two opposite, non-total definitions of "this order is alive" — CLOSED 2026-08-10
*(the root cause behind `P0-59`; found by stepping back from it rather than by patching it)*

**Where**: `RiskGuardAddOn.IsPendingOrWorking` / `IsTerminal` and all 21 call sites across both addons

**What happened**: NT8 has **sixteen** `OrderState`s. `IsPendingOrWorking` classified five,
`IsTerminal` three. **The two predicates were not each other's complement**, so eight states were
unclassified — and each addon silently inferred the opposite thing about them:

| Addon | Predicate used | Consequence |
|---|---|---|
| RiskGuard | `!IsTerminal` | a stop in `CancelSubmitted`/`CancelPending` **counted as coverage**, so a position read as protected during exactly the window its protection was being withdrawn, and no replacement was armed |
| the copier | `IsPendingOrWorking` | a leg in `ChangeSubmitted`/`ChangePending`/`TriggerPending` **counted as gone**, so it created a duplicate — `P0-59` |

Both are naked-risk/over-cover hazards. Both were live. One root cause.

**Why one boolean could never have fixed it.** Callers ask two different questions whose fail-safe
answers point in opposite directions:

- *"Is something already here, so I must not create a second?"* — answering **no** wrongly
  **over-covers** (two stops flip the position when both fire).
- *"Does this actually protect the position?"* — answering **yes** wrongly leaves it **naked**.

Adding the missing states to one list would have fixed the instance and left the structure that
generates it. That is the patch this entry exists to have avoided.

**Fixed**: one total classification with two derived predicates.

```
OrderLiveness { Working, Departing, Inert, Terminal, Indeterminate }
  OccupiesSlot(s)     -> Working | Inert | Indeterminate   "something is here; do not duplicate it"
  ProvidesCoverage(s) -> Working                            "this will actually act"
  IsTerminal(s)       -> Terminal                           honest; now zero production callers
```

`Indeterminate` **occupies a slot and provides no coverage** — conservative in both directions
simultaneously, which is precisely what a single boolean cannot be. Any state NT8 adds lands there
rather than in a silent default.

**`IsPendingOrWorking` was deleted, not wrapped.** That turned every ambiguous call site into a
compile error and forced each one to declare which question it was asking — the same technique §4k
records as having found three defects by making something a compile error.

> **The test double was the reason none of this was visible.** The stub's enum carried **ten of
> sixteen** states, so six could not be named by any test, and the suite was green at 686/0 with a
> P0 live on the box. All sixteen are now declared — obtained by reflecting
> `NinjaTrader.Core.dll`, not from memory — and `TestOrderLiveness_ClassifiesEveryNT8OrderState`
> fails if the stub drifts from NT8 or if any state reaches the default arm. The test file's own
> private copy of the liveness list is gone too: a second definition of "alive" living in the
> grader is this same defect one level up.

Suite 686/0 → **705/0**, `nt_compile` 0 errors under net48, deployed.

---

### P0-61. A second `Change()` against a leg already mid-change is dropped, and REVERTS the order — CLOSED 2026-08-10
*(found by a live trade, one hour after `P3-30` shipped. Not by any gate, and not by 782 tests.)*

**Where**: `CopierBracketReconciler.Reconcile`'s Modify branch, and the `AcceptsModification`
predicate that did not exist.

**What happens**: `P0-60` established two questions with opposite fail-safe answers. This is a
**third** question that neither answers — *"can I issue a change against this order right now?"* —
and the defect has exactly the same shape: a caller asking something no predicate covered, and
inferring it from the nearest one. A leg in `ChangeSubmitted`/`ChangePending` **occupies a slot**
(yes) and **provides coverage** (yes) but must not be changed again.

Issue a second `Account.Change()` and NT8 does not merely ignore it — **it drops the change AND
reverts the order to its pre-change values**, so the leg ends up neither where the first change
wanted it nor where the second did. The live trace, on a follower going 1 → 2 lots:

```
34412 ChangeSubmitted  qty 1 @ 29822.25    first change in flight
34412 ChangePending    qty 2 @ 29822.5     our second change
34412 Working          qty 1 @ 29822.25    reverted -- BOTH changes lost
```

The follower held 2 lots behind a 1-lot stop and a 1-lot target. RiskGuard saw it
(`FSM_UNDERCOVERED: covered 1 < pos 2`) and logged `MISSING_STOP_FLATTEN` on all four accounts —
in shadow, so nothing happened; **armed live it would have flattened the lot.** The compensating
control worked and the copier still under-covered.

**Fixed**: `OrderLiveness.Changing`, a third derived predicate, and a fourth reconcile verb.

```
OrderLiveness { Working, Changing, Departing, Inert, Terminal, Indeterminate }
  OccupiesSlot(s)        -> + Changing    still true: reading it as gone is P0-59
  ProvidesCoverage(s)    -> + Changing    still true: it IS protecting the position
  AcceptsModification(s) -> Working only  the new question
```

`Reconcile` emits `ReconcileVerb.Defer` instead of `Modify`, and **deliberately does not fall back
to cancel-then-replace** — pulling a protective leg whose change is about to land opens a naked
window in order to fix a price.

> ⚠️ **Declining to act is only safe if something later acts.** The first cut set the existing
> `*ResyncOwed` flag, which `SyncFollowerStop`'s own pass loop consumes *immediately* — re-driving
> while the leg is still mid-change, deferring three times, and giving up at the pass bound. The
> two signals cannot share storage: *"a concurrent sync had a newer instruction"* is not *"the
> broker is busy, come back when it is not"*. So there is a dedicated per-leg
> `StopChangeDeferred`/`TargetChangeDeferred`, and `OnFollowerOrderUpdate` re-drives when the leg
> settles — **before** its `OccupiesSlot` early return, because a leg settling out of
> `ChangeSubmitted` still occupies its slot and would otherwise be dropped.

**Live-validated 2026-08-10** on `Sim101 -> Sim-ORB`: `BRACKET_DEFERRED` →
`BRACKET_DEFERRED_REDRIVE` → `stop moved to 2@29742.5` and `target moved to 2@29805`. The previous
build never got either leg past qty 1.

Verified by mutation, 7 for 7, including three that silently dropped the re-drive and left the
suite green until the end-to-end test existed. Suite 762/0 → **787/0**.

---

### ~~P0-63. `Account.Change()` is a SILENT NO-OP on `provider: Simulator` accounts — so the mirrored stop has never trailed~~ — **FIXED 2026-08-13** (remedy 3)
*(found 2026-08-10 by an isolated probe designed to check `P0-62`'s premise. It disproved it, and found something larger.)*

**Where**: every `followerAcc.Change(...)` call in `TradeCopierEngine` (both leg syncs), and
`McpBridgeAddOn.ChangeOrder`. One API, one behaviour.

**What happens**: nothing. The order transitions `ChangeSubmitted` → `Accepted` and **keeps its
original price and quantity.** Not quantity-specific, not OCO-specific, not ATM-specific, not
stop-specific. Established on `Sim_All_Day_ORB`, an account in no copier relationship, so nothing
else could be reverting it:

| Probe | Asked | Result |
|---|---|---|
| standalone `StopMarket`, no OCO | qty 1 → 2 | **qty 1** |
| same order, price only | 29700 → 29695 | **29700** |
| resting `Limit`, 300 pts from market | 29500 → 29550 | **29500** |

The third is the decisive one: a resting limit far from the market has no trigger-proximity or
margin rule to blame.

**Retroactive confirmation on the copier's own path**: in the first live test of §4v, stop `34410`
was *created* at 29753.5, logged `BRACKET_MODIFIED ... stop moved to 1@29754.5`, and ended at
**29753.5**. The modify did nothing there either.

**Why we believed otherwise.** `/api/connections` reports `OrderChange` in `allFeatures` for
`Sim101` — but that is the **connection's** capability (`TPT`, which supplies data), while the
account's **`provider` is `Simulator`**, i.e. NT8's internal sim engine handles the orders and
ignores `Change()`. §4o's "Verified available: the connection advertises the OrderChange feature"
read the wrong layer. **Advertised by the connection ≠ honoured by the provider.**

**What this invalidates:**

- **The entire "modify in place, so no unprotected window" trail path** (`§4o`, shipped
  `995f6402`). Every leader trail step leaves the follower's stop at its **original** price. A
  leader trailing a stop up to lock in profit leaves the follower carrying the original risk.
- **`P0-62` was wrong** and is superseded by this entry — see below.
- **§4p's "a trailed leg kept both its orderId and its oco"** is consistent with the change simply
  never happening, so it is not evidence that `Change()` preserves OCO membership.
- The loop profile's invariant asserting modify-in-place has been corrected (`agent/nt8_riskguard.py`),
  or the review panel would defend a no-op.

> ⚠️ **UNRESOLVED, and it decides the remedy: does `Change()` work on a non-`Simulator` provider?**
> Every account validated on so far is `provider: Simulator`. The funded accounts are
> `Provider31` and were `Disconnected` during this work. If `Change()` is honoured there, the trail
> works in production and only our *testing* is misleading; if not, the trail is broken everywhere.
> **Do not assume either way.** Establishing it means placing a real order on a funded account,
> which is the user's call, not the agent's.

**Remedy options, all of which subsume `P0-62`:**

1. **Assume `Change()` never works: cancel-then-create every adjustment.** Correct on any provider,
   at the cost of a naked window on the risk leg per trail step — the exact failure §4o shipped
   modify-in-place to avoid. Going back to it knowingly is a real regression in a different axis.
2. **Delta leg for growth, cancel-then-create for repricing.** Needs `Reconcile` to accept N legs
   summing to the position size (`P1-36`'s coverage sum), which is the class-level fix.
3. **Detect it at runtime**: after a `Change()`, verify the order actually took the new values, and
   fall back to cancel-then-create when it did not. Works on both provider types without deciding
   the question, and turns a silent no-op into an observable one. **Cheapest honest option, and it
   composes with 1 and 2.**

> ✅ **FIXED 2026-08-13 via remedy 3, the operator's choice.** The requested price/quantity AND the
> pre-change values are recorded on the bracket with the `Order` they belong to; `OnFollowerOrderUpdate`
> verifies on the settle event; a leg still sitting at its pre-change values is positive evidence the
> change was ignored, and is replaced by cancel-then-create through `SyncFollowerStop` (the wrapper,
> so `P1-56`'s in-flight reservation still holds). An account observed ignoring a change is never
> asked again. Modify-in-place is preserved where the provider honours it, so `§4o`'s naked-window
> fix is intact. **The `Provider31` question stays open on purpose and remedy 3 does not need it.**
>
> Detection is deliberately "still at the PRE-CHANGE values" rather than "not at the requested ones":
> a false positive costs a real naked window plus a permanently marked account, so it must not fire on
> a rounding difference or a partial honour — and this way the check degrades to today's behaviour if
> NT8 ever stops reverting, instead of cancel-then-creating on every trail step.
>
> Suite **926 → 953**, four new acceptance tests (stop, target, quantity-only, six-step trail) plus a
> two-step honoured-change guard. New battery `mutation/mutate_p0_63.py`: 7 killed, no survivors.
>
> **Two gaps recorded in that battery, both in the SUITE rather than the fix**: the
> wrapper-vs-`Once` distinction is invisible to a suite with no concurrent settle-path test (and that
> was the most serious defect in the candidate — no reviewer found it), and the quantity half of the
> detection guards a PARTIAL honour, which the stub cannot express.

> ⚠️ **This entry's "Where" clause was short by one call site.** See `P0-67` immediately below.

---

### P0-67. `DynamicAtmManager` has the THIRD `Account.Change()` call, and its cache records the price the broker refused — ✅ FIXED 2026-08-13 (v1.1.0)
*(found 2026-08-13 by grepping for `.Change(` across `addons/` instead of trusting `P0-63`'s "Where" clause, which named the two copier leg syncs and `McpBridgeAddOn.ChangeOrder` and missed this one entirely.)*

**Where**: `addons/DynamicAtmManager.cs:622`, inside `ModifyStopPrice`, reached from both
`AtmStrategyType` branches of the bracket monitor (`:547`, `:577`, `:591`).

`P0-63` applies here unchanged — same API, same provider, same silent no-op. But the consequences
are **worse than in the copier**, for three reasons that are specific to this file:

**1. The cache is updated whether or not the broker agreed.** Every call site is the same shape:

```csharp
ModifyStopPrice(account, bracket.StopOrderId, newStop);
bracket.CurrentStopPrice = newStop;      // <-- unconditional
```

`ModifyStopPrice` returns `void` and swallows its own exceptions, so the caller cannot tell. After
one refused change, `bracket.CurrentStopPrice` is a value no order anywhere holds.

**2. So the trail's own gate is computed against a fiction, and latches.** The trail only acts when
`stopMoved`, and `stopMoved` compares the new price to `bracket.CurrentStopPrice` (`:588`). Having
just written the refused price into that field, the manager believes it has already trailed. It will
not try again until price moves past a stop that does not exist. Net effect on a `Simulator`
provider: **the ATM stop sits at its original price for the whole trade while the cached state
claims it is trailing.** The copier at least re-drives from the leader on every update; this does
not.

**3. Breakeven is one-shot and never verified.** `bracket.BreakevenTriggered = true` is set
immediately after the same unchecked call (`:549`, `:579`). A refused breakeven move is therefore
**permanent** — the flag guarantees it is never attempted again.

Two further defects in the same 18-line method, found while reading it:

- **It keys on `order.OrderId == orderId`** (`:619`). `RiskGuardAddOn.cs:4481` carries the warning
  that NT8's `OrderId` is neither unique nor stable across the historical→live transition, and the
  settled decision in `agent/nt8_riskguard.py` says protective legs are tracked **by object
  reference, never by id**. This is the only place left that keys a protective stop by id.
- **It requires the literal state `OrderState.Working`** (`:619`), so a stop at `Accepted` or
  `TriggerPending` is skipped in silence. `TriggerPending` is *a stop waiting on its trigger — the
  most protective state a stop can be in* (`Classify`'s own comment), and `AcceptsModification`
  exists to answer precisely this question. It is not used here.

**Remedy**: the same read-back as `P0-63`, but it cannot be lifted across as-is — this file has no
settle hook and no per-leg pending-request state to hang one on, which is why it was deliberately
left out of `P0-63`'s ticket rather than bolted on. At minimum, and in this order: make
`ModifyStopPrice` return whether it found and changed an order; stop updating `CurrentStopPrice` and
`BreakevenTriggered` on a call that did not demonstrably take; switch the lookup to
`AcceptsModification` and to reference identity.

> **Not yet established: whether this path is live.** `DynamicAtmManager` is driven by
> `nt8-mcp-bridge`, whose harness does not execute any of it (`P2-27`). Decide that before ranking
> this against the rest of the P0 band — if nothing calls it, it is dormant rather than dangerous.

---

### P0-68. `nt_change_order` reports `"status": "modified"` when the provider ignored the change — ✅ FIXED + LIVE-VALIDATED 2026-08-13

*(found 2026-08-13 during the live validation of `P0-63`, by trying to trail a leader stop through
MCP and watching it not move. Handover §5.13.)*

**Where**: `McpBridgeAddOn.ChangeOrder` — the **fourth** `Account.Change()` call site, and the only
one with no verification of any kind. `P0-63`'s "Where" clause named it; `P0-67` widened the search
and found the third; this is the fourth and it was hiding behind a success response.

**What happens**: the bridge calls `Change()`, then reads the order back **synchronously** and
returns it. NT8 leaves the caller's desired values on the `Order` until the provider settles, so the
read is meaningless — and on `provider: Simulator` the change is then silently discarded. The
response says `"status": "modified"` and the order never moves.

**Reproduced twice, the second time in isolation** with no position, no copier and no ATM strategy
involved:

```
nt_place_order  Sim101 MNQ 09-26 buy 1 Limit @29500      -> Working
nt_change_order <that orderId> limitPrice=29450
  -> {"status": "modified", "limitPrice": 29500, "stopPrice": 0}
nt_orders       Sim101                                    -> still Working @29500
```

⚠️ **The refutation is already inside the response.** `limitPrice: 29500` is the *unchanged* value and
it sits directly beside `"status": "modified"`. Nothing compares the two.

**Why this is P0 and not a reporting nit**: anything that trails a stop through MCP — an agent, a
scheduled task, a strategy driven over the bridge — believes it has moved risk and has not. That is
the same live exposure as `P0-63`, minus the detection. It is also **why the `P0-63` live test needed
a cancel-and-replace on the leader**: the obvious way to trail the leader silently did nothing.

**Remedy**: reuse `P0-63`'s. Verify **on settle**, not synchronously; on a detected no-op either fall
back to cancel-then-create or return an honest failure. At an absolute minimum, stop claiming
success: compare the settled values against the request and say which fields did not take.

**Note the deeper fact this makes unavoidable**: there are **four** `Account.Change()` call sites and
they have four different levels of rigour. The class fix is one verified helper that every site calls
— see [[fix-the-class-not-the-instance]] reasoning in §7 — not a fourth bespoke check.

### P1-69. The copier's latency and slippage metrics are computed, then discarded — ✅ FIXED + LIVE-VALIDATED 2026-08-13

*(found 2026-08-13 by the live validation. This is the half of `P?-66` that did NOT close.)*

**Where**: `TradeCopierEngine.ObserveFollowerFill` writes `rel.LatencyMs` (`:3071`) and
`rel.AvgSlippageTicks` (`:3110`) onto the canonical in-memory `CopierRelationship` — correctly, and
onto the right object, which was itself a fixed defect. Nothing then persists or exposes them.

**Evidence**: after a 1-lot round trip that logged `FILL_MEASURED` **twice** with real figures
(`142.86 ms / 0 ticks` on the entry, `314.21 ms / -4 ticks` on the exit),
`UserDataDir/RiskGuard/copier_config.json` still read `LatencyMs=0.0 AvgSlippageTicks=0.0` — with its
**mtime unchanged from the previous day**.

**Three defects compound into "the metrics do not work"**, which is what `P?-66` originally recorded:

| Layer | State |
|---|---|
| Measured? | ✅ yes, on the live path |
| Persisted to `copier_config.json`? | ❌ no writer |
| Readable over HTTP? | ❌ `/api/copier/config` is `Post`-only (§5.3) |
| Readable in the UI? | ❌ the UI reads a **different file** (`P?-64`) |

**Remedy**: fold into the MCP-wrapper work (§5.6 item 4) — add the `GET`, and persist the metrics
through the same `CopierConfigFile` path the ratio converter's slice 3b established. ⚠️ Do **not**
write them on every fill: that is a disk write on the hot path. Snapshot them with the existing save,
or expose them read-only over the endpoint and leave the file alone.

**The general lesson, which is worth more than the fix**: a number that is computed correctly and
cannot be read is indistinguishable from a number that was never computed — and for two sessions it
was diagnosed as the latter.

### P1-70. `BRACKET_MODIFIED` writes a false success line into the live audit log — ✅ FIXED 2026-08-13 (v1.1.0)

*(found 2026-08-13 by the live validation, in the log of the trade that proved `P0-63` works.)*

**Where**: the optimistic log in the stop/target modify path of `TradeCopierEngine`, emitted straight
after `Change()` returns and **before the provider settles**.

**What the audit log actually contained**, two lines, same millisecond, same account:

```
COPIER_BRACKET_MODIFIED            MNQ SEP26 stop moved to 1@29830.75 in place
                                   (leader offset -10, follower entry 29840.75);
                                   no cancel/replace, so no unprotected window.
COPIER_BRACKET_STOP_CHANGE_IGNORED MNQ SEP26: provider ignored Change() for stop
                                   (still 1@29820.75, requested 1@29830.75);
                                   falling back to cancel-then-create.
```

The first line asserts three things it cannot yet know: that the stop moved, that it moved *in place*,
and that there was therefore no unprotected window.

**Not naked risk** — the detection immediately behind it is what makes the system correct. But this is
the **same defect that was already fixed once** inside this very feature: `:3113-3119` records
`FILL_MEASURED` being changed to print the figure *this* fill produced rather than the stored value,
because "printing the stored value here would put a number in the log that nothing computed for this
fill, in the line that claims the fill was measured: `P1-22`'s own defect, reproduced inside `P1-22`'s
instrumentation."

**Remedy**: log the *intent* before, and the *outcome* after settle — or emit nothing until settle.
`BRACKET_MODIFY_REQUESTED` then `BRACKET_MODIFIED` on confirmation would make the log a record of
what happened instead of what was hoped.

### P1-71. A named active relationship produced no order and left no diagnosable trace — ✅ FIXED + LIVE-VALIDATED 2026-08-13

*(found 2026-08-13 by reading the live validation's log for what was **missing** rather than what was
present.)*

**What was observed**: on both the entry and the exit, the copier logged

```
COPIER_COPY_BEGIN  2 active relationship(s), isExit=False: Sim-ORB, SimCopy2
```

`Sim-ORB` then produced a full, correct chain of events. **`SimCopy2` produced nothing at all** — no
order, no skip, no reason, on either leg of the round trip.

**The obvious explanations are ruled out.** `SimCopy2` exists (`provider: Simulator`, cash
98,140.50); `IsQuarantined: false`; `LockoutUntil` unset; `TradesToday` 1 against a
`MaxTradesPerSession` of 8; `BlockedInstruments` and `InstrumentLimits` both empty. `ArmedForLive:
false` does **not** exclude it — that gate only blocks **non-Sim** followers (`:3413`).

**Why the cause is unknown, which is the actual defect**: every exit from the copy loop between
`COPY_BEGIN` and order submission is invisible in the only readable sink.

| Exit | Line | Logs where |
|---|---|---|
| `followerAcc == null` | `:3408` | **nowhere at all** |
| leader locked (`CanTrade`) | `:3440` | `Output.Process` only |
| follower locked (`CanTrade`) | `:3446` | `Output.Process` only |
| `COPY_BLOCKED_NO_GUARD` | `:3452`, `:3460` | `Output.Process` only |

`NinjaTrader.Code.Output.Process` reaches the NT8 Output tab and **nothing else** — not
`interventions.jsonl`, not the bridge's event stream. That is verbatim the failure
`RiskGuardAddOn.cs:4435-4440` says was fixed for the copier: *"on 2026-08-09 a leader exit failed to
mirror to its follower and there was no record of why, because every candidate path either logged to
a sink nobody can read or returned silently. Anything worth reading later belongs here."* Five paths
were missed. **`nt_get_logs --tab Output` does not help**: it returns the guard's structured stream,
not raw `Output.Process` output.

**Remedy**: route all five through `CopierLog`, each with its own event type. Mechanical, cheap, and
it converts this whole class from "undiagnosable" to "one grep". Then re-run the live test and read
the answer.

⚠️ **Do this BEFORE the next live validation** (§5.6 item 2). The next silence should cost one log
line to explain, not a session.

### ~~P0-62. `Account.Change()` applies the price but silently refuses a quantity INCREASE~~ — SUPERSEDED by `P0-63`
*(opened and superseded the same day. Kept, not deleted: IDs are never reused, and the reasoning error is worth keeping.)*

> ❌ **This entry's premise was WRONG.** It claimed the price applied while the quantity was
> refused, inferred from `2@29742.5` being logged and the order reading `1 @ 29742.5`. I treated
> `29743.5` as the order's prior value; it never was one — it was only ever another *desired* value
> that also failed to apply. The order was **created** at 29742.5 and never changed at all.
> `P0-63` has the isolated evidence.
>
> **The reasoning error, which I made twice in one session** (see also the retracted ATM
> lockout-bypass claim in handover §4v): **I read a final state and assumed a prior one.**
> Both times the fix was the same — establish the before-value independently, or probe the
> mechanism directly on an isolated account instead of inferring it from a busy one.

The original text follows for the record.

**Where**: every `followerAcc.Change(...)` call — both leg syncs — and therefore
`Reconcile`'s decision to emit `Modify` at all when the quantity must grow.

**The evidence is inside a single `Change()` call**, which is why this is not a guess. The engine
issued one change carrying **both** a new price and a new quantity, and logged it:

```
COPIER_BRACKET_MODIFIED   stop moved to 2@29742.5 in place
  order before:  1 @ 29743.5
  order after:   1 @ 29742.5     <-- price APPLIED, quantity increase REVERTED
```

**Consequence**: a follower that scales in can never have its protective leg grown by
modification. It stays permanently under-sized behind a larger position. The attempt budget
(`MaxBracketStopAttempts = 3`) then stops the retries — so it fails **quiet** rather than
flooding, which is the right failure but still leaves the follower under-covered with only
RiskGuard's `MISSING_STOP_FLATTEN` noticing.

**Not yet fixed, because the remedy is a real trade-off and should be chosen deliberately:**

1. **Cancel-then-create** when the desired quantity *exceeds* the working leg's — correct size, at
   the cost of a brief naked window on the risk leg, and it re-mints the OCO group.
2. **Submit an additional leg for the delta** — no naked window, but it deliberately creates the
   multi-leg state the whole duplicate-detection rule is built to eliminate, so `Reconcile`'s
   "cancel extras" would have to learn that N legs summing to the position size is legitimate.
   `P1-36` already built the multi-stop coverage sum this would need.

Option 1 is the smaller change and matches the existing fallback path. Option 2 is what `P1-36`'s
machinery points at. **Do not just widen the retry budget** — the budget is not what is failing.

> ⚠️ **Caveat on the reproduction, stated so nobody over-reads it.** The scale-in was a bare market
> order *outside* the leader's ATM bracket, so the LEADER was also 1-lot-covered behind 2 lots.
> That part is an artifact of how the test was driven. What is **not** an artifact: the copier
> computed qty 2 from the follower's own position, logged qty 2, issued qty 2, and the broker kept
> qty 1.

---

### P0-53. In an acting mode the lockout cancels the protective stop before flattening — CLOSED 2026-08-09
*(found while fixing `P0-51`, by making an existing test state its mode honestly)*
**Where**: `RiskGuardAddOn.cs:3461-3474` — `ExecuteAction`'s `CancelAllOrders` branch
**What happens**: `P1-11` filtered the **sweep's** cancel batches so a protective stop is never
cancelled before the flatten is confirmed. But the lockout's `PendingCancel` phase *also* emits a
`CancelAllOrders` `GuardAction`, and that branch cancels **every** working order — no
`IsPositionReducingOrder` filter, no scoping. In an acting mode the protective stop is therefore
cancelled *before* the flatten is attempted, and a flatten that then fails leaves the position
naked with nothing covering it.

This is the same hazard `P1-11` was opened for, surviving in the action pipeline rather than the
sweep. `P1-11` fixed one of the two routes and the second was never looked at.

**Why it was invisible**: `TestP1_11_LockoutSweepDoesNotCancelTheProtectiveStopBeforeFlattening`
never set a mode, and `_mode` defaults to `"shadow"`, so `ProcessAction` skipped the
`CancelAllOrders` action and only the (correctly filtered) sweep path ran. The test passed for a
reason that had nothing to do with what it claimed to prove. **Two defects — this and `P0-51` —
were both hidden by the same missing `SetModeForTest` call.**

**Fix**: apply the same intent split the sweep uses. `CancelAllOrders` must not cancel
position-reducing orders while the position is still open; reuse `IsPositionReducingOrder` rather
than writing a second definition. Either filter inside `ExecuteAction`, or have the lockout emit a
narrower action — but the guarantee must hold on both routes, not one.

**Fixed 2026-08-09.** The `CancelAllOrders` branch now reuses `IsPositionReducingOrder` and skips
any order that is reducing a still-open position, logging the retention as `LOCKOUT_STOP_RETAINED`.
Because "reducing" is only true while a position is actually open, a flat account still has every
order cancelled and the lockout still reaches `Confirmed`. The retained stop is cleared by the
sweep's existing deferred batch once the flatten is confirmed and the instrument is flat — that
machinery is `P1-11`'s and did not need rebuilding.

Pinned by `TestP1_11_LockoutSweepDoesNotCancelTheProtectiveStopBeforeFlattening`, which now covers
**both** routes. Its `SetModeForTest("live")` is load-bearing: in shadow the test proves nothing.

---

### P0-55. A follower can be left with NO mirrored stop after a partial-fill entry — CLOSED 2026-08-10
*(found by the live replay of the 2026-08-09 incident)*
**Where**: the copier's bracket path (`TradeCopierEngine.SyncFollowerStop` and its `OrderUpdate`
trigger); interacts with `RiskGuardAddOn`'s `FSM_PENDING_STOP_REJECTED`
**What happens, observed live 2026-08-10 00:11:31 ET**: a 2-lot ATM entry on `Sim101` filled in two
parts (1 then 1). The ATM's protective stop for **2** contracts arrived while the position was still
**Long 1**, and RiskGuard discarded it:

```
Sim101  FSM_PENDING_STOP_REJECTED  discarded 1 buffered stop(s) that are not protective
                                   cover for a Long 1 position.
Sim101  FSM_TRANSITION             Created FSM Sim101|MNQ SEP26 -> Unprotected
```

**`Sim-ORB` then received the copied entry but NO `COPIER_STOP` at all** and sat `Unprotected` for
the life of the trade, with RiskGuard emitting `MISSING_STOP_FLATTEN` (withheld, shadow). This is
the naked-follower condition `P0-9` exists to prevent, reached by a route `P0-9` does not cover.

**Mechanism, established 2026-08-10 — and it was NOT the FSM rejection.** The copier classifies
the leader's stop with the static helpers, not RiskGuard's FSM, so the rejection was a coincidence
of the same race rather than its cause. The real sequence, from the replay log:

| Time | Event |
|---|---|
| `.4203` | leader stop `34262` reaches **`Accepted`** |
| `.4683` | leader **`POSITION_UPDATE` Long 1** — the position exists only now |

`OnLeaderOrderUpdate` anchors the distance on `leaderAccount.Positions`, found nothing at `.4203`,
and returned. **An accepted ATM stop raises no further `OrderUpdate`**, and the leader's own
`PositionUpdate` was discarded outright by `OnAccountPositionUpdate` because the account is not a
follower. So the offset was never computed and nothing could ever recompute it.

**This is the leader-side twin of `P0-49`**, whose docstring already describes the identical race on
the *follower's* anchor — including the detail that an accepted ATM stop is event-silent afterwards.
Only the follower half was fixed.

Note the contrast with the 2026-08-09 incident, where `Sim-ORB` **did** receive a `COPIER_STOP`
1 ms after its fill. The difference is the partial fill.

**Fixed 2026-08-10.** The leader's `PositionUpdate` now re-drives the mirror for every working
protective stop on that instrument (`ReevaluateLeaderStops`). An account can be both leader and
follower, so the leader re-anchor and the follower anchor are two independent `if`s, not a branch.
The recoverable abandon is no longer silent: `BRACKET_NO_LEADER_POSITION` records the deferral and
`BRACKET_REANCHOR` records the recovery.

Pinned by `TestBracket_P0_55_LeaderStopAcceptedBeforeLeaderPositionIsStillMirrored`.

---

### P1-54. A lockout never lapses; `LockoutMinutes` has no effect — CLOSED 2026-08-10
**Where**: `RiskGuardAddOn.cs` — the lockout test at `:1734`, the flag clear at `:1847`,
`EvaluateLockoutPhase` at `:2783`, and `CapturePersistedState`
**What happens**: the lockout test is `IsLockedOut || DateTime.UtcNow < LockoutUntil` — an **OR** —
and **nothing clears `IsLockedOut` when `LockoutUntil` lapses**. The only clears are the daily
session reset (`:1847`) and the manual `UnlockAccount`. Worse, **`LockoutUntil` is not persisted at
all**: `state.json` carries a top-level `LockedOutAccounts` name list, so after any restart the flag
is restored with `LockoutUntil = DateTime.MinValue`.

So `Overtrading.LockoutMinutes` (default 60) is decorative. An account locked out at 21:15 is still
locked out hours later, until the 18:00 ET session boundary.

**Observed**: `Sim101`, `SimCopy2` and `SimCopyTest1` were all still locked out at 00:11 ET the
next day, ~3 hours after the false flood lockout, blocking a fresh test order with
*"Order blocked: Account Sim101 is locked out."* All three had to be cleared with
`POST /api/lockout {"action":"unlock"}`.

> **This is `P1-45`'s fix being ineffective, not `P1-45` reopened** (IDs are never reused). `P1-45`
> added `LockoutUntil` beside the flag, which is necessary but not sufficient: with an OR test and
> no expiry-clear, the deadline can only ever *extend* a lockout, never end one.

**Fixed 2026-08-10.** `EvaluateLockoutPhase` now ends a lockout whose deadline has passed
(`LOCKOUT_LAPSED`), and `LockoutUntil` persists per account in `AccountPersistedData`.

> **`MinValue` means "no deadline", not "expired".** `LockAccount(name, -1)` uses exactly that to
> express an EOD hold, so a naive `UtcNow >= LockoutUntil` check would silently unlock every
> deliberate hold-until-session-reset. The lapse is gated on `LockoutUntil > DateTime.MinValue`.
> Older state files deserialize the new field as `MinValue`, which reads as the previous behaviour,
> so an upgrade cannot shorten a lockout that was meant to hold.

Pinned by `TestP1_54_LockoutLapsesWhenItsDeadlinePasses` (which also asserts a *future* deadline
still holds — the lapse must not become a blanket unlock) and
`TestP1_54_LockoutDeadlineSurvivesARestart`.

---

### P1-52. The order-flood governor counts a normal ATM bracket as a flood — CLOSED 2026-08-09
**Where**: `RiskGuardAddOn.cs:1596-1631`; threshold `Overtrading.MaxOrdersPerSecond` (default 5,
`:5132`)
**What happens**: the governor counts distinct order IDs in a 1-second window with no notion of a
bracket. **One ordinary 2-contract ATM entry is 6 orders** — 2 entry fills, 2 stops, 2 targets —
against a limit of 5. So any 2-lot bracketed entry trips a lockout.

**Observed live, 2026-08-09 21:15:22 ET**: `ORDER FLOOD DETECTED: 6 distinct orders in 1s (limit 5)`
on `Sim101`, and — because the bracket was mirrored by a third-party copier (Replikanto) to
`SimCopyTest1` and `SimCopy2` — on all three accounts in the same second. Copier fan-out
multiplies the blast radius of a false positive across every mirrored account simultaneously.

This is the third defect on this governor (`P1-44`, `P1-45`, `P2-46` preceded it), and the second
about it firing when it should not. `P2-46` fixed *double-counting one order's state transitions*;
this is different — six genuinely distinct orders that are one trade.

**Fix options**, in preference order:
1. Count **entry** orders only, or count bracket groups (NT8 exposes the OCO id linking the
   protective legs), so the metric tracks trading rate rather than order-object churn.
2. Failing that, raise the default and scale it with position size — but this only moves the
   threshold, it does not make the metric mean the right thing.

> **Do not "fix" this by raising `MaxOrdersPerSecond` alone.** The governor exists to catch a
> runaway loop submitting orders; a bracket is not that, and a limit high enough to clear a 5-lot
> ATM is high enough to miss a real flood.

**Fixed 2026-08-09 (option 1).** The one-second window is keyed by **OCO group** where an order has
one, falling back to `Order.Id` where it does not. A bracket's legs collapse to one key per OCO
group instead of one per leg, so the live case counts 4 instead of 6. The threshold is untouched
at 5.

> **It keys rather than excludes, and the difference matters.** An earlier candidate treated any
> OCO-tagged order as a protective leg and dropped it from the count entirely. That makes OCO a
> blind spot: a runaway loop emitting OCO entry pairs — an ordinary breakout pattern — would never
> trip the governor. Keying keeps every distinct group counted. The review panel did not catch
> this; it was found by reading the diff.

`P2-46` (one order counted once across `Submitted`/`Accepted`), `P1-45` (`LockoutUntil` paired with
the flag) and `P1-44` (never cancel a protective order to enforce a rate limit) all still hold.

---

### P1-72. `nt_copier_config` advertised a `quarantine` action that nothing implemented — ✅ FIXED 2026-08-13, ⚠️ **REGRESSED and RE-FIXED the same day (§5.34)**. The enum still listed `quarantine` AND `unquarantine`; both are answered `UNKNOWN_COPIER_ACTION` — measured against the live box. It fails closed and loudly (P1-88), so it is a contract defect, not a dangerous one — but the enum is the only description of this surface a model ever sees. **The worse half**: `isQuarantined` (sent with `action: set`, which is what the browser page posts) was **not in the schema at all**, so the wrapper advertised two ways that do not work and omitted the one that does. A test now pins the enum against the addon's own `knownActions` whitelist, so the two cannot drift silently again

*(found 2026-08-13 while widening the MCP wrapper's argument surface — §5.6 item 3 — by comparing the
tool's declared `action` enum against the branches that exist.)*

**What it was**: the tool schema offered `action: ['get', 'set', 'quarantine']`. There is **no
`quarantine` branch anywhere** — not in `McpBridgeAddOn.CopierConfig`, not on `TradeCopierEngine`.
`CopierConfig`'s if-chain ends in `else { read }`, so `action: 'quarantine'` fell through to the read
branch and returned the config with **`success: true`**.

**Why it matters**: quarantine is what an operator reaches for when a follower is filling badly —
`MaxSlippageTicks` does it automatically, and a human does it manually. So the failure mode is: a
relationship known to be misbehaving is told to stop, reports that it stopped, and **keeps sending
orders to a real account**. That is `P0-68`'s shape (claiming an outcome that never happened) on a
safety control rather than on a stop order.

**The mechanism is the general defect, and it is worth more than the instance**: a dispatcher whose
default arm is a *read* converts every typo and every unimplemented action into a silent success.
`action: 'quarrantine'` behaved identically.

**Fix**: two halves.
1. The wrapper resolves `quarantine`/`unquarantine` to `set` + `isQuarantined`, which the engine does
   honour — pinned by `TestP1_74_QuarantineIsSettableThroughTheRequestPath`, because a remedy that
   assumed the field arrived would have been a second no-op dressed as a fix.
2. **An unknown action now throws** rather than degrading to a read, in
   `mcp/ninjatrader-mcp/lib/copier-config-request.js`. The bridge applies the same rule to GET: a
   write action over GET is refused with `method not allowed`, whitelisted rather than blacklisted,
   so `?action=remove_group` cannot mutate config over a read verb.

**Where**: `nt8-mcp-bridge/mcp/nt-mcp-server.js` (schema), `mcp/lib/copier-config-request.js` (mapping),
`McpBridgeAddOn.cs` `CopierReadFromQuery`. Live-verified: `?action=remove_group` → `success: false`.

---

### P1-73. The wrapper's schema defaults could silently reset stored config — ✅ FIXED 2026-08-13

*(found 2026-08-13 in the same pass, by asking what `ApplyRelationshipRequest`'s merge semantics imply
about a schema that declares defaults.)*

**What it was**: the tool declared `quantityRatio: { default: 1.0 }` and
`autoConversion: { default: true }`. `ApplyRelationshipRequest` **merges**: an absent key preserves
the stored value, a present key overwrites it (that is slice 3b's whole point, `CM3`). So a default
that reaches the request body is not a convenience — it is **silent data loss**. A caller nudging
`maxSlippageTicks` would reset a `quantityRatio` of 3 to 1, and re-enable a conversion the operator
had turned off.

**This is the destructive save pattern slice 3b deleted from the bridge, re-entering through a tool
schema.** `P?-65` is the same pattern in the WPF window. Three surfaces, one rule.

**Fix**: **no `default:` on any value field**, and the builder sends only keys the caller supplied.
`false` and `0` are values and are sent; only absence means absence. Verified over stdio against the
real server: `properties still carrying a default: none`.

**Also fixed here — the wrapper refuses to guess an account.** The engine falls back to
`leaderAccount` `"Sim101"` and `followerAccount` `"SimCopy2"`, both **real accounts on this box**, so
an underspecified write edited a live relationship silently. A relationship write now requires both
names explicitly, and arming requires `confirmLive` at the boundary instead of being quietly
downgraded to `armedForLive: false` in a response that contradicts its own request.

**Where**: `nt8-mcp-bridge/mcp/nt-mcp-server.js` `TOOLS`, `mcp/lib/copier-config-request.js`.
33 tests in `tests/copier-config-request.test.js`.

---

### P1-74. `autoConversion` is not a field, and had never done anything — ✅ FIXED 2026-08-13

*(found 2026-08-13 by checking, rather than assuming, which camelCase keys the engine reads — the
wrapper's correctness depended on it.)*

**What it was**: the engine's property is **`AutoSymbolConversion`**. `ConfigAliasMap` contains
`autoSymbolConversion` (lower-cased first letter of the canonical name) and **not `autoConversion`**,
so `NormalizeConfigObject` copied the unknown key through verbatim and `JsonConvert.PopulateObject`
discarded it as an unknown member. The MCP tool has advertised `autoConversion` since it was written.

**Why it matters more than a spelling slip**: that parameter names the exact feature that dropped a
live copy the day before. `SimCopy2` has `AutoSymbolConversion: true` and maps to NQ, so one MNQ at
ratio 1.0 rounds below a whole contract and is dropped (`P1-71`'s live answer). **The one control an
operator would reach for to fix that was inert, and reported success.** Same "config must not lie"
class as `P1-23` and the deleted `EnableFollowerAtm`.

**Fix**: the wrapper keeps `autoConversion` as its documented argument name and **translates** it to
`autoSymbolConversion` on the wire; an explicit `autoSymbolConversion` wins. Translating rather than
renaming keeps existing callers working.

**Pinned in both repos, deliberately.**
`TestP1_74_AutoConversionIsNotAFieldAndIsSilentlyDropped` asserts the engine **still drops**
`autoConversion` — it pins the defect, not a fix, because the remedy lives in another repo, and it
tells whoever adds an alias later that the translation can then be simplified.
`TestP1_74_EveryDocumentedCamelCaseArgumentReachesTheRelationship` pins all thirteen keys the wrapper
can now send. **A wrapper verified only against my reading of an alias map is verified against
nothing** — the JS tests can prove what is emitted, never what is read.

**Where**: `TradeCopierEngine.cs:703` `BuildConfigAliasMap`, `lib/copier-config-request.js`
`translateAutoConversion`.

---

### P1-75. Reading the prop-firm rules DISARMED them — ✅ FIXED 2026-08-13 (latent, never fired in production)

*(found 2026-08-13 by enumerating **every** `LoadFromDisk` call site after `P1-69` turned out to have
been fixed in only one of the bridge's two copier read branches. Fix the class, not the instance.)*

**What it was**: `McpBridgeAddOn.PropLimits`'s read branch called
`PropFirmProtectionSuite.LoadFromDisk`, which ends in `UpdateConfig(cfg)` **with no `confirmLive`** —
and `UpdateConfig`'s safety gate forces `ArmedForLive = false` without it. So a **read** of the
prop-firm configuration turned enforcement **off**.

**Every other field survives the reload.** `EvaluationTargetProfit`, both news-shield buffers, the
giveback cap — all intact. The only thing lost is whether any of them is *enforced*. That is why it
could sit in a read path unnoticed: the response looks right.

⚠️ **It has never fired on this box, and that is luck, not design.** `prop_limits.json` does not exist
here, and `LoadFromDisk` returns early on a missing file. **The defect is self-arming**: the `set`
branch calls `SaveToDisk`, so the first prop-limits write creates the file, and from that moment every
read disarms. It was one POST away from live.

**The gate is correct and stays.** Refusing to arm from a file is exactly what it is for — otherwise
a config could arm itself at startup, which is the failure `P1-47` and the copier's
`ArmedForLive = false` default both exist to prevent. The defect is a **read path invoking it**.
`TestP1_75_ReloadingPropLimitsFromDiskDisarmsThem` asserts the disarm on purpose, so that nobody
"fixes" a future report of this by weakening the gate.

**Fix**: the read branch returns `PropFirmProtectionSuite.Instance.Config` directly. In-memory *is*
the live config — loaded at `State.Configure`, written by every save path. A hand-edit to
`prop_limits.json` is picked up at the next NT8 start, deliberately not by a reader.

**`P1-69`'s second half went with it**: the copier's `get_groups` branch still called `LoadFromDisk`,
so listing the **groups** still discarded the relationship latency/slippage measurements that
`ObserveFollowerFill` writes. Only the two `State.Configure` startup loads remain in the bridge.

**Where**: `McpBridgeAddOn.cs` `PropLimits` (read branch), `CopierConfig` (`get_groups` branch),
`PropFirmProtectionSuite.cs:128` `LoadFromDisk` → `:68` `UpdateConfig`.

**Not live-validated, and it cannot be cheaply**: proving it needs an armed prop config plus a saved
file, and arming live risk rules to demonstrate a fixed defect is not a trade worth making. Compile
clean, deployed, pinned by an executed test.

---

### P1-76. Which config applies to a follower was emergent, not defined — ✅ FIXED 2026-08-13

*(found 2026-08-13 from the operator's observation that it was "not clear what configuration
applies and for what". It was not clear in the code either, which is the actual defect.)*

**What it was**: `GetActiveRelationshipsForLeader` added direct relationships, then expanded
matching groups into synthesized relationships, then deduplicated by follower with
`.GroupBy(...).Select(g => g.First())`. So a follower covered by **both** a direct relationship
and a group got the **direct** one — purely because directs were `AddRange`d into the list
first and `.First()` takes the earliest.

**Nothing named that rule and no test pinned it.** The existing dedup test asserted
`activeRels.Count == 1` and the follower's **name** — the safety property — and never which side
won. Reordering those two blocks is an innocuous-looking refactor that would have flipped every
group's `QuantityRatio`, `SizingMode`, `AutoSymbolConversion` and `MaxPositionSize` over every
direct relationship, **silently, with the whole suite green**, on live sizing.

The second consequence is the one the operator hit: **a follower in both places has its group
settings silently ignored**, so a group can be edited, saved, and have no effect.

**Operator decision, 2026-08-13: REFUSE THE OVERLAP.** A follower belongs to a direct
relationship OR a group, never both, so that there is exactly one place to look for what applies
to it.

**The asymmetry in the fix is deliberate and load-bearing:**

| Path | Behaviour |
|---|---|
| `ApplyRelationshipRequest`, `ApplyGroupRequest`, `AddFollowerToGroup` | **REFUSE.** Return null/false and log `CONFIG_OVERLAP_REFUSED`. A group request is **all-or-nothing** — creating it minus the clashing follower would silently drop an account the operator named (`P1-23`'s class). |
| `LoadFromDisk` | **TOLERATES and REPORTS.** Logs `CONFIG_OVERLAP_DETECTED` per overlap and exposes it via `DetectConfigConflicts()`. A load that refused would drop config the operator can see in the file, which is `P?-64`'s and `P2-41`'s shape and **worse** than the overlap. |

**Membership, not effect**: a **disabled** group still reserves its followers, because enabling a
group is one click and that click must not be what creates the overlap.

**Where an overlap already exists** (only reachable by hand-editing `copier_config.json`) the
**direct relationship wins**, and that is now stated in code rather than emerging from list
order. Surfaced over the API as `configConflicts` + `configConflictNote` so the UI can render
"this group setting is being ignored for this follower" instead of showing it as if it applied.

**One behaviour change worth knowing**: a **disabled** direct relationship now suppresses the
group entry, so that follower copies **nothing**. Previously the `IsEnabled` filter dropped the
direct entry and the group's entry survived, so the follower **copied at the group's ratio** —
a follower the operator had switched off, trading again through group membership.

**The mutation battery found the fix's own test to be decorative.** 3 of 14 mutants survived the
first run, including the one that restores the pre-`P1-76` emergent tie-break: direct-wins is
**over-determined**, since dedupe's `.First()` produces it too, so asserting the outcome held
either way. The case where the two mechanisms diverge is the **disabled** direct relationship
above — that is the test that was missing, and it is now the one that kills those mutants. A
second test pins deduplication on the only case it can still fire (one follower in two groups).

⚠️ `P1-76`'s insertion also broke an anchor in `mutate_cm3.py`, which reported `(ANCHOR)` and
scored it a **SURVIVOR** — that default is why an unrelated edit silently disarming another
battery's mutant was caught rather than shipped. Anchor narrowed.

**Where**: `TradeCopierEngine.cs` — `DetectConfigConflicts`, `GroupReserving`,
`DirectRelationshipExists`, the guards in `ApplyRelationshipRequest` / `ApplyGroupRequest` /
`AddFollowerToGroup`, the explicit tie-break in `GetActiveRelationshipsForLeader`, and the
report at the end of `LoadFromDisk`. Bridge: `configConflicts` on the copier config GET.
Tag **`v1.2.0`**. Suite 1053/0; `mutation/mutate_p1_76.py`, 14 mutants, 0 survivors.

**Not live-validated**: `groups` is empty on this box, so no overlap exists to demonstrate
against — which is also why the rule could be introduced with zero migration risk.

---

### P1-77. The Consistency Rule Shield is configurable, enabled by default, and evaluated nowhere — HONESTLY REPORTED, IMPLEMENTATION DEFERRED 2026-08-13

*(found 2026-08-13 by auditing the operator's feature list against the source rather than
against the config schema — §5.17.)*

✅ **RE-CONFIRMED MECHANICALLY, same day.** A survey counting every use of every config leaf across
`addons/` found `EnableConsistencyCap` and `MaxDailyProfitPctOfTarget` at exactly two sites each:
**the declaration and the JSON parser** (`PropFirmProtectionSuite.cs:46-47` and `:178-179`). There
is no evaluator, so unlike `P2-25` this rule is not INERT — it is the plainer
`CONFIGURED and not EVALUATED`, and [UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md) §6a makes that
state **structural**: a rule registered without an evaluator delegate cannot report anything else.

**What it is**: `PropFirmProtectionConfig` declares

```csharp
public bool EnableConsistencyCap { get; set; } = true;
public double MaxDailyProfitPctOfTarget { get; set; } = 0.35;
```

Both are parsed from `prop_limits.json` (`PropFirmProtectionSuite.cs:178-179`). **Those four
lines are the only places either name appears in the entire addon tree.** There is no
`EvaluateConsistencyCap`; the suite implements `EvaluateProfitTargetLock` and
`EvaluatePeakEquityGiveback` and nothing else.

**Why it matters more than an unimplemented feature.** It is not absent — it is **present,
enabled by default, and inert**. An operator reading the config, or an agent reading it over
the API, is told the consistency rule is switched on with a 35% cap. Prop-firm consistency
rules are an *account-failure* condition: exceeding the cap on one day can void an evaluation
no matter how good the rest of the account looks. So the failure mode is believing you are
covered against the one rule that silently disqualifies you.

**Same class as `P1-23`** (`EnableFollowerAtm`, which implied followers got a bracket and was
deleted rather than implemented), **`P2-24`** (written-but-never-called safety machinery) and
**`P1-74`** (an advertised argument that was not a field). Config must not lie.

**Two honest remedies, and the choice is the operator's:**

1. **Implement it.** Needs the evaluation target (`EvaluationTargetProfit`, present), the day's
   realized PnL (already tracked per account), and a decision on the action — lock out, or
   refuse new entries only. ⚠️ The action must **not** be *flatten*: hitting a profit cap is not
   a risk event, and flattening a winner to enforce a consistency rule realises the very P&L the
   rule is about.
2. **Delete both fields**, as `EnableFollowerAtm` was deleted. A field nobody reads is not a
   feature, and leaving it visible is the defect.

**Do not** "fix" this by defaulting `EnableConsistencyCap` to `false`. That keeps the lie and
makes it quieter.

> **Amended 2026-08-13 — the warning above was half right, and the half that was wrong is worth
> knowing.** `P1-82` defaulted both this and the news shield to `false`, and it does **not** make
> this one quieter: `CONFIGURED-not-EVALUATED` is derived from `Evaluator == null`, so the
> inventory reports this rule red whatever its flag says. The defect is untouched and still open.
> What the flag change removes is `prop_limits.json` *asserting* a 35% cap that has never capped
> anything.
>
> ⚠️ The warning was exactly right about the **news shield**, whose evaluator short-circuited on
> its own flag and so began reporting `Disabled` — "not a defect". That is `P1-86`, closed the
> same day, and the rule it left behind is the one to carry forward: **`Disabled` means "this
> would work if you turned it on"**. Before defaulting any enabling flag to `false`, check that
> the rule behind it still reports its defect with the switch off.
>
> The two honest remedies below are unchanged. Turning the flag off is not one of them; it is
> what you do *while* one of them is still outstanding.

**Where**: `addons/PropFirmProtectionSuite.cs:46-47` (declared), `:178-179` (parsed), evaluated
nowhere.

---

### P2-78. `PerInstrumentRiskConfig` carries two fields nothing reads — OPEN

*(found in the same audit, §5.17.)*

`PerInstrumentRiskConfig` (`RiskGuardAddOn.cs:5435`) has three fields. Only `MaxContracts` is
read (`:1717`). **`IsBlocked` has zero references anywhere in the tree**, and `StopOffsetTicks`
appears only at its own declaration.

`IsBlocked` is the more misleading of the two: a per-instrument `IsBlocked: true` looks exactly
like the way to block one instrument, and blocking is really done through the separate
`_config.BlockedInstruments` list. So the config offers two ways to block an instrument and only
one of them works.

Same class as `P1-77` above and `P1-23`. Cheapest correct fix is deletion; if `IsBlocked` is
wanted, it belongs in the `:1706` check next to `BlockedInstruments`.

**Where**: `addons/RiskGuardAddOn.cs:5435-5440`.

---

### P1-79. A quarantine can be released but its REASON cannot be cleared — ✅ CLOSED 2026-08-13 (§5.21, UI2)

*(found 2026-08-13 while writing the `UI2` ticket, not by a test and not by a live run. It is
in the `P1` band rather than `P2` because the surviving text is displayed to the operator as a
current fact about a live relationship.)*

`NormalizeRequest` (`TradeCopierEngine.cs:1706`) deliberately **strips null-valued properties**
before the merge:

> *"An explicit null means 'not specified', not 'wipe it'. Json.NET's default `NullValueHandling`
> would set the property to null, so `{"perTickerRatios": null}` — which is what a JS client sends
> for an untouched field — would null out the ratio matrix and hand a `NullReferenceException` to
> whatever sizes the next fill."*

That reasoning is correct and must stay. Its consequence is that **no request can clear a string
field**, and `QuarantineReason` is a string field.

So `{"isQuarantined": false}` releases the quarantine and leaves `QuarantineReason` holding
`"Margin / Order Rejection"`. `TradeCopierWindow.cs:812` renders that reason in red, prefixed
`⚠️ QUARANTINED:` — but it renders it inside `if (rel.IsQuarantined)`, so **the window happens
not to show it today**. That accident is the whole defect: the stale text is live in the object,
in `copier_config.json`, and over `/api/copier/config`, and the only thing hiding it is one
conditional in a file scheduled for replacement. The browser UI has no reason to guess that the
reason field is only meaningful when a second field is true.

This is `P1-23`'s and `P1-77`'s class — state that reads as a fact and is not one — reached from
the merge path rather than from a dead config field.

**Fix**: a domain invariant on `ApplyRelationshipRequest`, not a special case for one key. **A
reason without a quarantine is stale data**, so when the merge leaves `IsQuarantined == false`,
`QuarantineReason` is null. Stating it as an invariant means it also holds for the bridge's
`quarantine` action and for anything added later; stating it as "if the request said
`isQuarantined: false` then also clear the reason" would hold for exactly one caller.

⚠️ **Do NOT fix it by making `NormalizeRequest` honour nulls.** That reinstates the ratio-matrix
defect the strip exists to prevent, which is a live-money sizing failure, in exchange for a
cosmetic one.

**Where**: `addons/TradeCopierEngine.cs` — `ApplyRelationshipRequest` (:1796) is where the
invariant goes; `NormalizeRequest` (:1706) is why the obvious fix does not work; the stale text
surfaces at `TradeCopierWindow.cs:812`.

**Status**: being fixed as spec section E of the `UI2` ticket
(`agent/tickets_ui_config.json`), and pinned by `TestUi2_ARowEditNeverMutatesTheStoredObjectFirst`,
which asserts `released.QuarantineReason == null`.

---

### P1-80. A risk-config write that reported success and applied nothing, ever — CLOSED 2026-08-13

*(found by surveying the config files on the live box after `P?-64` closed, not by a test. The
question that found it was "which files here does anything actually read?" — worth asking again
elsewhere.)*

**Three config-shaped files sat in `UserDataDir/RiskGuard/`. One was live.**

| File | Read by | State |
|---|---|---|
| `config.json` | `RiskGuardAddOn.cs:333` | ✅ the real one |
| `riskguard_config.json` | **nothing** | written by the bridge, never consumed |
| `RiskConfig.json` | **nothing, in either repo** | zero references; `StopGuard.OnMissing: "AutoStop"` while the guard ran `"Flatten"` |

`McpBridgeAddOn`'s `RiskGuardConfig` write path did this when the guard was not loaded:

```csharp
_riskGuardConfig[key] = req;
File.WriteAllText(RiskGuardConfigFile, JsonConvert.SerializeObject(_riskGuardConfig));
return new { success = true, status = "persisted_only", ... };
```

`_riskGuardConfig` was **declared, loaded from disk at startup, and written to. It was never
read by anything.** So the configuration was not applied then, was not applied at the next
startup, and would never be applied. The note said *"NOT applied to a live engine"* — true about
that moment, and it reads as *"it will be picked up later"*. It would not.

**Measured on the live box**: `riskguard_config.json` held `trailingDrawdown: 500,
maxPositionCap: 5`, written 2026-07-30, while the live config ran `1500` and `10`. **A file
stating a drawdown limit three times tighter than the one actually enforced.** Anyone — an
operator, an agent, the browser UI — reading it would have concluded the account was far more
protected than it was.

This is `CONFIGURED and not EVALUATED`, the same state as `P1-77` (a prop rule enabled by default
and evaluated nowhere) and `P2-78`, reached through a *write* path rather than a dead field.

⚠️ **The tell was an asymmetry, and it is worth recognising elsewhere: the READ half of the same
method already refused** (`{ error = "RiskGuardAddOn not loaded" }`) **while the WRITE half
pretended to succeed.** When one direction of a pair refuses and the other does not, the
permissive one is usually wrong.

**Fix**: deletion, not wiring — `[[fix-the-class-not-the-instance]]`. The dictionary, the path
constant and the startup load are gone, and the write now REFUSES exactly as the read does. Risk
configuration with no engine to apply it to is an error, not a draft. Wiring the store up instead
would have created a *second* source of truth for the guard's limits, which is the defect one
layer up.

Both dead files were deleted from the box. Nothing read them, and the operator confirmed config
is disposable in the current phase.

**Where**: `nt8-mcp-bridge/addons/McpBridgeAddOn.cs` — the fallback branch in `RiskGuardConfig`,
`_riskGuardConfig` (:146), `RiskGuardConfigFile` (:4936) and the `LoadJsonStore` at :250.
**Pinned by**: `TestP1_80_NoWritePathPersistsRiskConfigNothingReads` in
`nt8-mcp-bridge/tests/BridgeSourceTests.cs` — source-text, because that file is still outside an
executable harness (`P2-27`), with a positive clause so deleting the method cannot pass it.

---

### P1-81. The prop suite's `ArmedForLive` arms nothing — OPEN

*(found 2026-08-13 while classifying every config leaf for the `UI3` rule registry. It was found
by the act of having to state, for one field, what reads it — which is the whole argument for the
registry.)*

`PropFirmProtectionConfig.ArmedForLive` (`PropFirmProtectionSuite.cs:32`) defaults to `false` with
the comment *"MUST default to false for safety"*, and is guarded by a `confirmLive` gate at `:73`
that disarms it unless arming was explicitly confirmed. Both of those are correct and careful.

**Nothing else reads it.** Its only other appearance is the JSON parser at `:168`. In particular
`RiskGuardAddOn` never consults it: the three prop rules that do work — the news shield (`:1541`,
and see `P2-25`), the profit-target lock (`:1559`) and the peak-equity giveback (`:1576`) — are
reached through the guard's own mode and armed state and **do not check whether the prop suite
itself is armed**.

So the flag has two readings and both are wrong:

* read as *"the prop rules are off until I arm them"* — they are not; they act on the guard's
  arming, not this one;
* read as *"arming this turns the prop rules on"* — it does not do that either.

⚠️ **This is not the same defect as `P1-77`.** The consistency cap is a rule that does not exist.
This is a *control* that does not control — closer to `P3-34` (the copier acts regardless of guard
mode) inverted: a second arming flag whose state is irrelevant to what actually fires.

**Severity**: `P1` rather than `P0` because the prop rules are gated by *something* real (the
guard's own mode), so there is no unguarded path — the defect is that the operator's mental model
of what arms what is wrong, and this flag is what makes it wrong.

**Fix, once decided**: either make the prop rules consult it — which is what it looks like it does
— or delete it and let the guard's arming be the single answer to "can this act?". ⚠️ **Do not
"fix" it by having the UI display it**, which would propagate the false model to a second surface.
The decision is *how many arming flags this system should have*, and the answer is probably one;
see `P3-34`, which asks the same question about the copier.

**Where**: `addons/PropFirmProtectionSuite.cs:32` (declaration), `:73` (its own gate), `:168`
(parser). No other reference exists in either repo.
**Reported by**: the `UI3` registry, which carries it as a rule with no evaluator and states the
reason — so it renders red rather than being invisible.

---

### P2-82. The rule registry was publicly mutable — CLOSED (`UI4`, 2026-08-13)

*(found while writing `UI4`'s acceptance tests, not by review.)*

`GuardRuleRegistry.Rules` and `.NonRules` returned their backing `List<T>` typed as `IList<T>`, so
`GuardRuleRegistry.Rules.Add(...)` compiled and worked from anywhere in the assembly.

The registry's entire value is that it is the **single** statement of what this codebase does and
does not enforce. A caller that can add an entry can make the inventory report protection that no
code implements — **`P1-77` inverted**: instead of a config field with no evaluator rendering red,
an invented rule renders green. It is the more dangerous direction of the two, because `P1-77` at
least fails safe.

**Fixed** by returning `AsReadOnly()` from both accessors, pinned by a test that asserts `Add`
throws on **each**, and by two mutants — one per accessor.

⚠️ **The second mutant is the point.** The fix was applied to both accessors, but the first test
exercised only `Rules`, and the `NonRules` mutant **survived**. The defect lived in two identical
members and a test aimed at the one a mutant happened to name would have left half of it open.
That is the general shape of "a fix applied to one of N identical sites", and the only thing that
caught it was mutating both.

**Where**: `addons/GuardRules.cs` — the two accessors immediately after `_nonRules`.
**Shipped in**: `v1.3.0` (as the defect); closed on `feat/ui-snapshot-builder`.

---

### P2-83. A snapshot with no accounts rendered as healthy — CLOSED (`UI4`, 2026-08-13)

*(design defect in `UI3`'s DTO, found by writing the producer for it. It never reached an operator
because nothing rendered the DTO.)*

`GuardSnapshot` carried its rule inventory **only underneath an account**. On a box with no
accounts loaded — during startup, after a connection loss, or on a machine where the guard has
seen no account activity yet — the inventory would have been empty, and an empty page reads as
*nothing is wrong*.

But `P1-77`'s consistency cap is broken for **every account equally**: a rule with no evaluator is
a property of the **build**, not of an account. Reporting it zero times because there is no
account to hang it on is the same lie `INERT` exists to prevent, told one level up — *"nothing to
show"* and *"nothing is wrong"* rendered identically.

**Fixed** by `GuardSnapshot.UnevaluatedRules`, built once per snapshot and independently of any
account, and by treating a **null** account list as an empty one so that nothing about the account
set can make `BuildSnapshot` throw — an exception there blanks the inventory, which is the same
failure by another route.

**Where**: `addons/GuardRules.cs`, `GuardSnapshot` and `GuardRuleRegistry.BuildSnapshot`.
**Shipped in**: `v1.3.0` (as the defect, unrendered); closed on `feat/ui-snapshot-builder`.

---

### P1-82. Two switches defaulted ON while doing nothing — CLOSED 2026-08-13

*(the R2 change from `CONFIG_DEFAULTS.md`, and the only one of this batch found by reading rather
than by evidence.)*

`PropFirm.EnableNewsShield` (`INERT`, `P2-25`) and `PropFirm.EnableConsistencyCap`
(`CONFIGURED-not-EVALUATED`, `P1-77`) were the **only two flags in the system that defaulted
`true` while the rules behind them could not fire**. `prop_limits.json` therefore read as
protection that did not exist — you open it, you see `"EnableNewsShield": true`, and you size a
position accordingly.

**Fixed** by defaulting both to `false`. This does **not** fix either rule; both stay open and the
inventory still reports them red. What changes is that the config stops asserting them.

⚠️ **It was four literals, not two.** Each default is stated once as a property initializer and
once as the final fallback in `ParseConfig`, and the parser copy is what runs for any config file
that predates the field — which is every config file on this box. Fixing only the property would
have been green in the suite and unchanged in production. Mutants 3 and 4 of `mutate_p182.py`
exist to prove that, and the class gate cannot catch them because it builds its config with `new`.

⚠️ **Three UI3 tests broke, and that was the interesting part.** They demonstrated `INERT` using a
*default* config — their evidence that the state exists at all depended on the news shield
defaulting on. They now turn the switch on explicitly, which is what they always meant: `INERT` is
the state an operator lands in when they enable the shield and it still cannot fire.

**Where**: `addons/PropFirmProtectionSuite.cs:33`, `:46`, and the two `ParseConfig` fallbacks.
**Gate**: `mutation/mutate_p182.py` — 8 mutants, including two controls that default the two
genuinely-enforcing switches OFF, so R2 cannot be satisfied by removing real protection.

---

### P1-86. Switching off a broken rule hid that it was broken — CLOSED 2026-08-13

*(opened by `P1-82`, and predicted in writing by this document's own `P1-77` entry.)*

The `P1-77` entry says: *do not "fix" a dead flag by defaulting it to false, that keeps the lie and
makes it quieter.* Half of that objection is dead and half was exactly right.

* It does **not** hold for the consistency cap. `CONFIGURED-not-EVALUATED` is derived from
  `Evaluator == null`, so that row stays red whatever the flag says.
* It held precisely for the news shield. Its evaluator opened with
  `!c.PropConfig.EnableNewsShield ? Off(...)`, and `Off(...)` sets `DisabledByConfig`, which
  `DeriveState` turns into **`Disabled`** — a state this codebase documents as *"switched off by
  the operator. Not a defect; shown so it is not mistaken for one."* So `P1-82` converted `P2-25`
  from a defect into a preference, on a default box, silently.

**Fixed** by making the evaluator ask whether it *can* fire before it asks whether it is switched
on: zero events loaded reports `INERT` with its `P2-25` note regardless of the flag, and `Off(...)`
is reached only when there is at least one event — the only situation in which "switched off" is
something the operator could reverse.

**The general rule, now stated on the evaluator**: `Disabled` means *"this would work if you turned
it on"*. A rule with nothing to evaluate does not qualify, however its switch is set.

⚠️ **`DeriveState` is deliberately NOT changed.** Moving the evidence check above the
`DisabledByConfig` check there is the shorter diff and a real defect: the two `FirmMirror` rules,
the window gate and the two working prop rules all short-circuit to `Off(...)` *without* gathering
evidence when switched off, so all five would start reporting `INERT` and the inventory would call
deliberately-disabled rules defects.

**Where**: `addons/GuardRules.cs`, the `PropFirm.EnableNewsShield` rule.
**Gate**: 4 mutants in `mutation/mutate_p182.py`, plus a class test that walks every rule keyed by
a bool and fails any that is `INERT` when on and `Disabled` when off.

---

### P1-83. Four config fields stored, settable, and read by nothing — CLOSED 2026-08-13

*(found while writing `CONFIG_DEFAULTS.md`, by asking what READS each field rather than what sets
it. `P1-77`'s shape, four more times.)*

`CopierRelationship`/`CopierGroup.StealthMode`, the copier's own `DailyLossLimit`, the entire
`CopierExecutionMode` enum, and `PropFirm.EnableAutoDayFiller`. All persisted, all settable,
branched on nowhere.

**`StealthMode` was the worst of them and not by a little.** `P1-77` and `P1-81` are silent; this
one had **four surfaces asserting it**: both window status lines printing `Stealth: ON`, a "Stealth
Tagging" checkbox on both Add forms, "Stealth Order Tagging" in the window title, and a `stealth`
flag on the browser page in `nt8-mcp-bridge` — for a feature with no implementation anywhere.

**Fixed** by deleting all four, plus the gate that finds the fifth: a class test that walks both
copier DTOs by reflection and counts real uses in **the engine**, discounting a field's own
declaration, `X = something.X` clone/serializer lines, and the field-name string list. Run against
the pre-fix tree it named exactly these three with no false positives.

⚠️ **Scoping the gate to the engine is the design, not a shortcut.** Widen it to the window and
`StealthMode` scores as READ — which is the defect told louder, not an absolution from it. And it
is honest about its limit: it is source text, so it cannot catch `P2-25`'s class (a field genuinely
read by a branch that can never be reached). The guard side needed a runtime registry for that;
the copier side still has none, which is recorded as open.

⚠️ **The dead fields were load-bearing in the tests.** Ten merge-preservation probes used them —
*"a field the request never mentions survives the merge"* — chosen precisely *because* nothing read
them. They now probe live fields.

⚠️ **The agent-loop cannot make this kind of change**, and the reason is structural: deleting a
symbol that a *protected* test file references fails its compile gate, so the patch is correct and
the build breaks anyway on a file the loop may not touch. Every other change in this batch went
through the loop.

**Where**: `addons/TradeCopierEngine.cs`, `TradeCopierWindow.cs`, `GuardRules.cs`,
`PropFirmProtectionSuite.cs`, and `nt8-mcp-bridge`'s `ui/index.html`.
**Gate**: `mutation/mutate_p183.py` — 6 mutants; mutant 4 reintroduces a field WITH a fake read,
which is the cheapest way to satisfy any "is it referenced?" check.

---

### P1-84. Three defaults that made the guard easier to switch off than to live with — CLOSED 2026-08-13

*(R4 and R5 from `CONFIG_DEFAULTS.md`.)*

* `StopGuard.StopAttachSeconds = 3` with `OnMissing = "Flatten"`: three seconds from fill to a
  working stop, or you are flattened. Enter manually, reach for the mouse, get flattened on a day
  when nothing was wrong. **→ 15.**
* `MaxPositionSize = 100` on both copier DTOs against the guard's `MaxContractsPerAccount = 10`.
  Same quantity, and the lower always binds, so the copier's cap **had never stopped anything**.
  **→ 10.**
* `MinShadowSessions = 0`, while `RunPreflight`'s FR-29 gate reads `MinShadowSessions > 0 && ...`
  — so zero does not relax the precondition, it **switches it off**. **→ 5.**

The tests matter more than the numbers: an *inequality* between two files rather than a pinned
cap, a deadline floor *conditional* on `OnMissing`, and a value asserted together with the source
line that makes it a defect.

⚠️ The loop's implementer turned the deadline into a property computed from `OnMissing`, and the
reviewers were right to refuse it: a recomputing getter lets a config reload move a deadline while
a grace timer is already running, and reads `OnMissing` off one thread while another writes it.
The ticket invited that by saying the number was "tied to" `OnMissing` when it meant a comment.

**Where**: `addons/RiskGuardAddOn.cs` (`StopGuardConfig`, `MinShadowSessions`),
`addons/TradeCopierEngine.cs` (both DTOs).
**Gate**: `mutation/mutate_p184.py` — 8 mutants; mutant 6 raises the copier cap to ONE above the
guard's, which is what proves the assertion is an inequality and not a pinned 10.

---

### P1-85. The copier invented an account when a request omitted one — CLOSED 2026-08-13

*(found while writing `CONFIG_DEFAULTS.md` §3.1.)*

`TradeCopierEngine` guessed an identity in **four** places on the write path and twice more on the
load path: leader → `"Sim101"`, follower → `"SimCopy2"`, group name → `"DefaultGroup"`, and a new
group's leader → `"Sim101"`.

⚠️ **Those two account names are real, connected accounts on this box.** A truncated or malformed
write did not fail — it succeeded, against accounts nobody selected. `"DefaultGroup"` was worse
than a stray create: groups are looked up BY name, so an unnamed write silently **edited** whatever
was stored there.

**Fixed** across three slices. A request that cannot say what it applies to is refused with a
reason, logged through `CopierLog`. On the load path an entry whose key cannot supply the missing
name is skipped and **reported through the guard log** rather than `Console.WriteLine` — a
malformed entry silently dropped at startup is `P?-64`'s shape, and refusing to guess must not buy
that back. The DTO defaults became `""`: empty reads as unset, where `"Sim101"` read as configured.

⚠️ **Two of ten mutants survived the first battery run**, and both were findings:

* Swapping `IsNullOrWhiteSpace` for a null check on the relationship accounts left the suite green.
  The behaviour was already right; there was no *evidence* of it, because every test OMITS the
  account and **omitted and blank are different inputs reaching the same field**. The ticket had
  even said "it already refuses blanks", which was true and not the point.
* The blank-leader rule was stated **twice** — once on the raw request before the merge, once on
  the merged object — so narrowing either one left the suite green. A rule stated twice cannot be
  tested, because neither statement is load-bearing; it is why a genuine review finding had no way
  to fail. Reduced to one unconditional post-merge check: **no group with a blank leader is ever
  stored, by any route.**

**Where**: `addons/TradeCopierEngine.cs` — both Apply methods, both `TryParse` methods, both DTOs.
**Gate**: `mutation/mutate_p185.py` — 10 mutants.

---

### P1-87. An unrecognised stop action silently disabled the stop guard — CLOSED 2026-08-13

*(found because a mutant SURVIVED, not by review.)*

`EvaluateGraceExpiry` dispatched on `StopGuard.OnMissing` with two exact string comparisons and no
`else`. A lower-case `"flatten"`, a typo, an empty string, or the `"WarnOnly"` that the declaration
itself advertised matched nothing, so the method emitted **no action at all** — a position with no
stop, past its grace period, and the guard simply returned. `RunPreflight` refuses an unrecognised
guard *mode* and had never looked at this, so the failure was silent at startup and silent at the
moment it mattered.

⚠️ **The suite was defending the defect, not merely silent about it.**
`TestStopGuardWarnOnlyProducesNoAction` asserted *"No action generated when OnMissing is
WarnOnly"* — the defect, written down as expected behaviour. Deleted.

**How it was found**: `mutate_p184.py`'s mutant 3 changed `OnMissing` from `"Flatten"` to
`"AutoStop"` and **all 1180 tests stayed green**. Nothing pinned the guard's most consequential
default, and asking why led here.

**Fixed**: the unrecognised case and `Flatten` are one branch producing one action under one RuleId
(the log is grepped by RuleId); `RunPreflight` refuses an unrecognised value and names it; and
`WarnOnly` is gone from the declaration comment and from the settings dropdown that offered it.

⚠️ Two loop rounds failed to compile on a **region boundary** rather than on anything the
implementer wrote — R1 covered only the `if` half of the if/else-if chain, so every patch left a
dangling `else`.

**Where**: `addons/RiskGuardAddOn.cs` — `EvaluateGraceExpiry`, `RunPreflight`, `StopGuardConfig`,
and the settings window's `_onMissingCombo`.
**Gate**: `mutation/mutate_p187.py` — 6 mutants; mutant 2 keeps the `else` and makes it do nothing,
so the shape of the fix survives and the behaviour does not.

---

### P1-88. An unrecognised copier action was answered as a successful write — CLOSED 2026-08-13

*(found on the live box while applying `P1-84`'s new `MaxPositionSize` default. Two writes came
back `success:true, persisted:true, loaded:true` and the value did not move.)*

`McpBridgeAddOn.CopierConfig` tests each recognised action in turn and ends in an `else` that is
the **read** path — and that path returns `success = true`, `loaded = true` and
`persisted = File.Exists(CopierConfigFile)`. So **any** unrecognised action was answered as a
persisted write. The request had used `"set_relationship"`; the action is `"set"`.

`P1-80`'s shape on the copier, and worse: the caller sent a payload it believes was applied.

**Fixed** with a whitelist checked once before any branch, refusing by name and listing the valid
actions. A whitelist rather than accepting the extra name, because the failure is not that one
name was wrong — it is that **any** wrong name was answered as a write. Three surfaces reach this
one handler (the MCP wrapper, the browser page, `curl`) and only one of them has a schema.

**Live-validated**: the same request now returns `success:false`, `UNKNOWN_COPIER_ACTION`,
`persisted:false`.

**Where**: `nt8-mcp-bridge`, `addons/McpBridgeAddOn.cs`, `CopierConfig`.

---

### P1-89. A copier read resolved a relationship by leader alone — CLOSED 2026-08-13

*(found in the same request, because the response carried the wrong relationship.)*

The read branch used `FirstOrDefault(r => r.LeaderAccountName.Equals(leader))`, ignoring the
follower even when the caller named one. With two followers under `Sim101`, a request naming
`SimCopy2` came back carrying `Sim-ORB`'s object — and looked like a successful read.

Both accounts identify a relationship everywhere else in this system: the config key, the refusal
paths, the conformance rows. **Fixed** to match on both, while a request that names *no* follower
still gets the leader's first — that is the historical behaviour and is right for "show me this
leader". What was wrong was ignoring a follower the caller *did* name.

**Where**: `nt8-mcp-bridge`, `addons/McpBridgeAddOn.cs`, the copier read branch.
**Gate**: `tests/BridgeSourceTests.cs` — a source scan, because this repo has no executable tests
(`P2-27`).

---

### P1-90. An unresolvable account name routes an order to an arbitrary account — CLOSED 2026-08-13, LIVE-VALIDATED

*(found while closing `P1-88`, by grepping the bridge for the guess `P1-85` had just removed from
the engine. Was the most serious item open in either repo for one day.)*

> ✅ **FIXED, DEPLOYED AND VALIDATED ON THE LIVE BOX** — session 30, handover §5.26. All **six**
> sites refuse. The measured proof, on the deployed build:
>
> ```
> nt_place_order account="NoSuchAccount_P190"
>   -> "No account named 'NoSuchAccount_P190' (matched case-insensitively) among the 96
>       available. Refusing to place an order rather than choosing a different account."
> nt_place_order account="sim101"       (lower case, valid)
>   -> reaches the symbol check -> "instrument not found" -- so it refuses the unresolvable
>      without over-refusing the resolvable, and case-insensitive matching is preserved
> nt_compliance_report  (account omitted)
>   -> "This request must name an account: no `account` field was supplied."
> ```
>
> **The resolution moved OUT of `McpBridgeAddOn.cs`** into `addons/BridgeAccountResolver.cs`, which
> names no NinjaTrader type — so `BridgeTests.csproj` compiles and **executes** it. That is the
> first bridge production source this project tests rather than greps, and it is `P2-27`'s cheapest
> available step. Suite 23 → **50**.
>
> Gates, both made to fail on purpose before being trusted: **`mutation/mutate_p190.py`** — the
> bridge repo's **first** mutation battery, 11 mutants / 0 survivors (7 kill on executed behaviour,
> 4 on source assertions, and the split is labelled) — and **`tools/check_bridge_parses.py`**,
> ported from `check_window_parses.py`, which catches a syntax error in bridge code *before* it
> reaches the live NT8 folder.
>
> ⚠️ **One mutant SURVIVED the first draft of the tests**: narrowing the emptiness test to a null
> check, so `"   "` was reported *not found* rather than *missing*. It still refused, so every
> "was it refused?" assertion held. The assertion that the two reasons are distinguishable was added
> because of it — `P1-85`'s lesson (missing and blank are different inputs) arriving a second time.
>
> ⚠️ **`P1-91` was opened by this fix**: four MCP tool schemas still advertise
> `default: 'Sim101'`, two of them **order** tools. See that entry — the engine refuses, and the
> wrapper still tells callers the guess exists.

Three order paths in `McpBridgeAddOn.cs` (`:2386`, `:2453`, `:4422`) resolve the account as:

```
the named account
  ?? the account called "Sim101"
  ?? ANY account not called "Backtest"
  ?? ANY account at all
```

So `nt_place_order` with an account name that does not resolve — a typo, wrong case, a
disconnected account — **is not refused. The order is placed somewhere else.** The live box
reports 96 accounts.

⚠️ **Severity is above `P1` despite the number.** `P1-85` was the same guess on the copier's
config path and was rated `P1` because a config guess writes the wrong config. This one opens the
wrong position. It belongs with the `P0` band on consequence; it is filed here because it was
found here and has not been triaged.

Three further `"Sim101"` fallbacks sit on account-resolution paths (`:1848`, `:4166`, `:5621`) and
should be reviewed with it.

**The fix is refusal**, as it was for `P1-85`: an order that cannot say which account it is for
has no safe interpretation. Deliberately **not** attempted at the end of the session that found
it — it changes order routing, and this repo has no executable tests to catch a mistake (`P2-27`).

**Where**: `nt8-mcp-bridge`, `addons/McpBridgeAddOn.cs` — and the fix, in
`addons/BridgeAccountResolver.cs`.

---

### P1-91. MCP tool schemas supplied an account, and an action, the caller never sent — CLOSED 2026-08-13

*(opened 2026-08-13 by `P1-90`'s live validation, in the third repo. Found by reading the tool
schema before probing with it, which is the only reason it was noticed at all.)*

`tvDownloadOHLC/mcp/ninjatrader-mcp/nt-mcp-server.js` declares `default: 'Sim101'` on the `account`
property of four tools — **two of them order tools**:

| Line | Tool |
|---|---|
| `:89` | **`nt_place_oco_order`** |
| `:124` | **`nt_place_atm_order`** |
| `:588` | `nt_compliance_report` |
| `:672` | `nt_deploy_strategy` |

**Two distinct problems, and the second is the one that matters.**

1. The schema now **misdescribes the deployed behaviour**. It tells a caller — human or agent —
   that omitting `account` targets `Sim101`. Since `P1-90` the bridge refuses. An agent reading the
   contract will write a request the box rejects.
2. ⚠️ **Latent, and it would restore `P1-90` at the wrapper layer.** MCP clients are permitted to
   materialise schema defaults into the request. Any client that does would inject
   `account: "Sim101"` into an **order** call, and the bridge — correctly receiving a named,
   resolvable account — would place the order on `Sim101`. The refusal would never be reached.

> **Measured, so this is not filed on suspicion:** with `nt_compliance_report` and no `account`, the
> bridge received **no account field** and refused. So *this* client does not materialise defaults.
> That is a property of the client in use today, not of the contract — which is exactly the shape of
> `P1-75` (a schema `default:` that became a write because the receiver merged it) and `P1-73`.

**The fix is to delete the four defaults** and mark `account` required, so the contract says what
the engine does. Deliberately not attempted in the session that found it: it is a third repo, the
MCP server must be restarted to reload tool schemas, and a restart drops the live tool connections
that were being used to validate `P1-90`.

> ✅ **FIXED 2026-08-13 (session 31), through the agent-loop, and it grew on contact.**
> Six defaults deleted and seven `required` arrays corrected, in
> `mcp/ninjatrader-mcp/lib/tools.js`. Suite 33 → **40/0** in a repo that had no
> executable coverage of its schemas at all.
>
> ⚠️ **It was NOT four defaults. It was six.** The acceptance test was written against the defect
> *class* rather than the four filed instances, and running it found two more — on `action`:
>
> | Tool | Default | Enum includes |
> |---|---|---|
> | `nt_alert` | `webhook` | **`flatten`** |
> | `nt_multi_account_orchestrator` | `sync_hedge` | **`group_flatten`** |
>
> `sync_hedge` adjusts positions **across accounts**. An omitted `action` doing that is `P1-90`'s
> class exactly: something consequential happening that the caller never named.
>
> ⚠️ **And the first version of that test was WRONG, in the dangerous direction.** It forbade any
> `action` default, which would have made the implementer delete two **correct** ones —
> `nt_prop_limits` (`get`) and `nt_trade_journal` (`list`) — to go green. Both default to the READ,
> which is fail-closed. The rule is *which way the default falls*, not whether one exists: a
> defaulted `action` must itself be a read. **That is "a too-broad test gets the CODE broken to
> satisfy it", caught before it could happen only because the test was run and its output read
> rather than its verdict.**
>
> ### ⚠️ What this fix does NOT do — measured, and it is not what the ID implies
>
> The MCP server **never reads `.default`, never reads `inputSchema`, and does not validate
> `required` at all.** So:
>
> * Deleting the defaults **is** a real behavioural change, for any client that materialises schema
>   defaults. That was the whole risk: an injected `Sim101` is a real connected account, so the addon
>   resolves it happily and `P1-90`'s refusal is never reached.
> * Adding `required` adds **no server-side gate here**. It makes the contract truthful and lets a
>   validating client fail fast. **The enforcement remains the addon's refusal** (`P1-90`,
>   live-validated).
>
> Do not read this as "the server now rejects an order with no account". The server does not reject
> it; the addon does.
>
> ⚠️ **NOT IN EFFECT UNTIL THE MCP SERVER IS RESTARTED.** Tool schemas are read at startup.
>
> **Three obstacles had to be cleared before the loop could take this at all**, and each is recorded
> where the next session will hit it:
> 1. `python-tvdownloadohlc` **cannot gate a `.js` file** — `py_compile` errors on it and its
>    `test_cmd` is two Python suites that pass whatever the patch does. A gate that cannot fail.
>    New profile: `agent/js_ninjatrader_mcp.py`, **inside** that repo.
> 2. `ninjatrader-mcp` is a **submodule**, and a worktree of the parent does not check submodules
>    out — so a parent-side profile resolves during `--list` and then finds nothing to patch.
> 3. ⚠️ **The loop cannot parse Node's test output**, and `Profile.test_runner_regex` — which looks
>    like the configuration point for exactly that — is **dead: declared at
>    `agent_loop/profiles.py:78` and read by nothing in the package.** That is `P1-83`'s class in the
>    tool itself. Worked around with `agent/loop_test_reporter.mjs`, emitting the NT8 shape because
>    its `[FAIL]` lines carry test NAMES and `expect_green` is matched against them — without those,
>    the test-first gate is vacuous. `agent/verify_reporter.py` proves it by feeding the reporter's
>    real output through the loop's real parser.

**Where**: `nt8-mcp-bridge/mcp/lib/tools.js` (the schemas were at
`nt-mcp-server.js:89`, `:124`, `:588`, `:672` before the extraction).

### P2-92. `shadow` mode is not observation-only: a shadow breach stops the account trading — ✅ CLOSED 2026-08-13 (§5.30: a lockout records the AUTHORITY it was imposed under)

*(filed 2026-08-13 while scoping `F-9`, by asking what enabling two more lockout-capable rules on a
live box would actually do)*

**Where**: `RiskGuardAddOn.cs:112` (`CanTrade`) against `:4622` / `:4647`
(`EvaluateFirmMirror`), and the same shape at `:1482`, `:1522`, `:1581`, `:1599` for the PnL rules.

**The mechanism.** `ProcessAction` gates *execution* on mode — `IsActingMode` is false in `shadow`, so
the flatten is logged as `SHADOW_ACTION` and never sent. That is the whole promise of shadow mode.
But the rules set `stateModel.IsLockedOut = true` **before** the action is dispatched, outside any
mode check, and `_stateDirty` persists it. And `CanTrade` reads that flag **first**:

```csharp
if (_accountStates.TryGetValue(accountName, out var state) && state.IsLockedOut)
{
    bool bypassAllowed = !_isArmed && _config.LockoutBypassWhileDisarmedAccounts...
    if (!bypassAllowed) return false;
}
if (!_isArmed) return true;          // <- the mode/arming escape hatch is BELOW the lockout
```

So in `shadow`: nothing is flattened, and the account **stops being allowed to trade**. The copier
consults `CanTrade(followerName, ...)` (plan §1, `:3440`/`:3446`) and every strategy consults it
through `RiskManagerBase`. A shadow-mode breach therefore halts a bot silently — the three refusal
paths log to `Output.Process` only, which is `P1-71`'s finding, so *nothing readable says why*.

**Why the existing comment does not cover it.** The comment at `:116` explains lockout persistence
across **disarming** (`FR-30`, judge-loop `P1-4`) — a panic toggle-off must not defeat a daily-loss
lockout. That decision is right and is not in question. `shadow` is a different axis, and it was
never considered: `LockoutBypassWhileDisarmedAccounts` cannot help, because the guard is *armed*.

**Why it is P2 and not P1.** It fails in the safe direction — it stops trading rather than permitting
it — and it is recoverable through the existing unlock path. But "shadow" naming a mode that can halt
your bots is a false description of the one mode the whole `MinShadowSessions` gate exists to make
safe, and it will be discovered as "the copier mysteriously stopped".

⚠️ **This is load-bearing for `F-9`.** `F-9` maps accounts to firm plans, which arms two more
lockout-capable rules. On the five Sim accounts mapped, an `Apex-100K` breach needs a $1,800 drop from
peak — an ordinary week for an ORB strategy. Mapping was deliberately kept to Sim accounts for
exactly this reason.

**Fix, not yet applied**: decide whether a non-acting mode may set `IsLockedOut` at all. The honest
options are (a) record the would-be lockout on a separate shadow field that `CanTrade` ignores, or
(b) let `CanTrade` consult the mode the way `ProcessAction` does. (b) is one line and (a) is more
truthful; (a) also gives the shadow session the count it is supposed to be collecting.

### P2-95. `FirmStartingBalance` is a session-start heuristic, and the error GROWS with the account — ✅ CLOSED 2026-08-13 (session 34: FirmProfile.AccountSize is the floor)

*(filed 2026-08-13, straight out of [FIRM_PLANS_RESEARCH.md](FIRM_PLANS_RESEARCH.md): the research gave
the config the real starting balance, and revealed that the guard measures its own)*

**Where**: `RiskGuardAddOn.cs:4664` in `ComputeFirmMirror`.

```csharp
if (st.FirmStartingBalance == 0.0)
{
    st.FirmStartingBalance = balance - realized - unrealized;
    result.TraceLogs.Add($"Initial starting balance captured heuristically: {st.FirmStartingBalance}");
}
```

`realized` is **session-scoped**, so that expression is *the balance at the start of this session*, not
the plan's starting balance. The comment says "heuristically" and is honest about it. What was not
appreciated is how the two diverge:

| Account state | Real plan start | `FirmStartingBalance` becomes | Locked floor is wrong by |
|---|---|---|---|
| fresh 50K | 50,000 | 50,000 | 0 |
| 50K, up $324 this session | 50,000 | 50,032.50 | $32 |
| 50K, up $5,000 over its life | 50,000 | **55,000** | **$5,000** |

**Two paths read it, and both are load-bearing for the plans just deployed:**

* `TrailingDD.Type == "static"` → `guardFloor = (FirmStartingBalance - Amount) + Buffer`.
* **The trail lock** → once `FirmTrailingPeak >= FirmStartingBalance + LockAtProfit`, the floor becomes
  `FirmStartingBalance`. This is the mechanism Apex, Lucid **and TPT PRO** all use, and `LockAtProfit`
  was set for the first time on 2026-08-13 (`TPT-50K-PRO`, `LockAtProfit = 2000`).

So on a TPT PRO account up $5,000 lifetime, the guard would lock its floor at **55,000** while the
firm's is **50,000**, and flatten roughly $5,000 early. That is `CONFIG_DEFAULTS` **R5**'s failure
mode — a limit that fires on a good day is the most likely single reason this system gets switched
off — and unlike R5's `StopAttachSeconds` it gets *worse* the better the account does.

⚠️ **It is currently invisible.** `FirmStartingBalance` is captured once and persisted, so on this box
it holds whatever the balance was at the first evaluation after `F-9` landed. Nothing displays it and
nothing validates it.

**Fix**: seed it from the mapped plan's `FirmProfile.AccountSize` when that is `> 0`, falling back to
the heuristic when it is not — which is exactly why `AccountSize` was added (`F-9b`, `CONFIG_DEFAULTS`
R3). ⚠️ Note the migration: the field is already persisted with heuristic values, so the fix needs to
*correct* existing state rather than only affect fresh accounts, and a test per case
(fresh / persisted-heuristic / persisted-correct / unmapped). Also surface it in the inventory: a
trailing floor whose anchor nobody can see is the same class of problem as a limit nobody reads.

### P2-94. A TIMED manual lockout does not stop new orders — `CanTrade` never reads `LockoutUntil` — ✅ CLOSED 2026-08-13 (session 34)

*(filed 2026-08-13 while fixing `P2-92`, from a review-panel finding that pointed at the adjacent
code)*

**Where**: `RiskGuardAddOn.cs:112` (`CanTrade`) against `:3648` (`LockAccount`) and `:1777` (the
sweep).

`LockAccount(accountName, minutes)` has two branches:

```csharp
if (minutes == -1) { state.IsLockedOut = true; state.LockoutUntil = DateTime.MinValue; }   // EOD
else if (minutes > 0) { state.LockoutUntil = DateTime.UtcNow.AddMinutes(minutes); }        // timed
```

The timed branch **never sets `IsLockedOut`** — and an existing test asserts exactly that
(*"IsLockedOut is false for timed lockout"*, `:10229`). `CanTrade` reads **only** `IsLockedOut`. So a
timed manual lockout does not refuse a single order.

It is not entirely inert: the sweep tests `IsLockedOut || DateTime.UtcNow < LockoutUntil` — an OR, at
`:1777` — so it will flatten and cancel. The net behaviour is therefore the **worst available**
combination: the operator asks for a 60-minute lockout, the guard accepts new orders, and the sweep
flattens each resulting position. A clean refusal is strictly better than a fill followed by a
flatten, and the operator has no way to tell from the config or the UI which of the two they asked
for.

Same family as `P2-92`: **one lockout, two consumers, and they disagree about what it means.**
`P2-92` records the *authority* under which a lockout was imposed; this one is about the two
*representations* of a lockout — a flag and a deadline — where each consumer reads a different subset.

**Fix**: make `CanTrade` honour the deadline the way the sweep already does, i.e. test
`IsLockedOut || DateTime.UtcNow < LockoutUntil`. ⚠️ Do it with `P2-92`'s authority flag in mind, and
check `:3021`'s lapse logic first — the comment there records that the flag deliberately *outlives*
its own deadline, so the two conditions are not interchangeable and the interaction needs a test per
combination, not one.

### P2-93. `pure` and `override_with_friction` pass the enforcement gate and then enforce nothing — ✅ CLOSED 2026-08-13 (session 34: both now fail preflight)

*(filed 2026-08-13 while scoping `P2-92`, by reading what `IsActingMode` actually returns)*

**Where**: `RiskGuardAddOn.cs:3670` (`IsActingMode`) against `:3423` (preflight's mode check) and
`:3431` (the `MinShadowSessions` gate).

Four modes are recognised:

```csharp
if (_mode != "shadow" && _mode != "live" && _mode != "pure" && _mode != "override_with_friction")
    result.Fail("MODE", $"Unrecognised mode '{_mode}'");
```

and three of them are treated as **enforcement** modes by the soft gate immediately below, which
refuses to arm until `MinShadowSessions` shadow sessions have completed:

```csharp
if ((_mode == "live" || _mode == "pure" || _mode == "override_with_friction")
    && _config.MinShadowSessions > 0 && _shadowSessionsCompleted < _config.MinShadowSessions)
```

But the predicate that decides whether anything **acts** names only one:

```csharp
internal bool IsActingMode(bool forceLive = false) { return _mode == "live" || forceLive; }
```

So an operator who sets `pure`, waits out five shadow sessions to satisfy a gate that exists *only*
for enforcement modes, and arms, gets `ProcessAction` returning **`SHADOW (SKIPPED)`** for every
action. The friction gate for `override_with_friction` (`Override.WaitSeconds >= 30`) is validated
in the same block, for a mode that overrides nothing.

This is the canonical class in this programme — **a config that reads as protection that does not
exist** — and it is worse than `P1-77`, because the operator had to *pass a gate* to get here.

**Not fixed deliberately.** Making the two modes act is a protection **increase**, and turning two
dormant modes live on a box that trades funded accounts is the operator's call, not a side effect of
a defect fix. `P2-92` uses `IsActingMode()` precisely so the two consequences of "acting" stay
governed by one predicate rather than two definitions — which is what makes this findable at all.

**The honest options**: (a) implement the two modes, with tests that distinguish them from `live`;
(b) delete them from the recognised list, so setting one is refused at preflight instead of accepted
and ignored. **(b) is the fail-closed choice** and is one line.

---

### P0-96. The copier read a position's SIDE off the SIGN of its quantity — ✅ FIXED 2026-08-13 (v1.18.0)

**Where**: `TradeCopierEngine.OnExecution` (the exit-direction alignment) and
`ReconcileFollowerPosition` (the direction-mismatch check).

**What happens**: NT8's `Position.Quantity` is **absolute** — the side lives in
`MarketPosition`, which is why that property exists, and every one of the ~1300 tests in this
repo already models a short as `MarketPosition.Short` with a **positive** quantity. Two places
read the sign anyway:

```csharp
if (currentFollowerPos < 0) followerAction = OrderAction.BuyToCover;   // UNREACHABLE
else if (currentFollowerPos > 0) followerAction = OrderAction.Sell;    // runs for BOTH sides
```

So a leader **covering a short** sent the follower a `Sell`. A `Sell` does not close a short —
it **doubles** it, in a direction the leader has already left. The copier's own log said so as
soon as a test drove it:

```
COPY_SUBMITTED: MNQ 03-26 Sell 1 submitted to 'SimFollower'
                mirroring leader 'SimLeader' BuyToCover 1@18000 (isExit=True)
```

`P0-5`'s family (*copier exit sizing is not position-mirroring → follower reverses*), reached by
a different route. The second site made `ReconcileFollowerPosition`'s `directionMismatch`
permanently false, so the only branch in that method that takes a broker action **could not
fire**.

**Why 1300 green tests missed it**: every long-side test passes under the defect, and there was
no short-**exit** test. The suite had short *entries* and short *stop* mirroring; the exit
action was never asserted.

**Fix**: both sites read `MarketPosition`. The sizing is untouched — `CalculateFollowerQuantity`
takes the quantity through `Math.Abs`, so it was always sign-agnostic.

**Pinned by** `mutation/mutate_p096.py` — 5 mutants, 4 killed. Two of them are the lesson:
mutant 3 **deletes the alignment block entirely** and only a test with the follower on the
*opposite* side to the leader notices, because `followerAction` already defaults to the leader's
action; and mutant 4 drops the `isExit` guard, turning a scale-in **entry** into an order that
closes the position. Both survived the first draft and both now have tests. The fifth is a
**documented survivor**: the reconciler half is inside `#if !TESTING` and called by nothing, so
no test here can reach it — when `P2-27` makes it testable, that is the first test to write.

---

### P1-97. `nt_place_order` never emits `SellShort`/`BuyToCover`, so the copier misreads every MCP-placed short — ✅ FIXED and LIVE-VALIDATED 2026-08-13, found and closed the same hour

**Where**: `nt8-mcp-bridge/addons/McpBridgeAddOn.cs:2423` versus
`TradeCopierEngine.OnExecution:4876`.

```csharp
// the bridge, for EVERY order, regardless of the account's current position:
var orderAction = actionStr.Equals("buy", ...) ? OrderAction.Buy : OrderAction.Sell;

// the copier, which classifies from that label:
bool leaderIsExiting = leadAction == OrderAction.Sell || leadAction == OrderAction.BuyToCover;
```

**Measured on the live box**, both halves, on `Sim101`:

| What was placed | NT8 position after | Copier read it as | Log |
|---|---|---|---|
| `sell 1 MNQ` from **flat** — a short ENTRY | `Short 1` | **`isExit=True`** | `COPY_SKIPPED_NO_POSITION_TO_EXIT` |
| `buy 1 MNQ` from **short** — a COVER | flat | **`isExit=False`** | proceeded as an ENTRY into `CalculateFollowerQuantity` |

So through the bridge the copier **cannot open a short at all**, and a **cover is copied as a
new entry in the opposite direction**. The second is the dangerous one: the follower is sent a
`Buy` while the leader is closing a short.

⚠️ **It did not produce a wrong position in this run only by accident.** `AutoSymbolConversion`
maps `MNQ → NQ`, and 1 MNQ scaled to NQ rounds below one contract, so it died on
`COPY_SKIPPED_SUB_MINIMUM`. With an NQ leader, or any ratio ≥ 1 after conversion, the follower
takes the position. Nothing in the correctness path stopped it.

**Note the bridge already knows how to do this** — `McpBridgeAddOn.cs:2797`, the close path,
picks `pos.MarketPosition == Long ? Sell : BuyToCover`. The same three lines are missing at 2423.

**FIXED** in `nt8-mcp-bridge/addons/BridgeOrderAction.cs` — its own file on `BridgeAccountResolver`'s
terms (strings in, strings out, no NT8 type named), so the bridge suite **executes** it rather than
grepping it. 69 → 92 tests.

✅ **Live-validated after deploying**, a full short round trip on two followers:

```
SellShort  1@30177.75  isExit=False -> SellShort 10 MNQ to Sim-ORB AND SimCopy2, both Short 10
BuyToCover 1@30183.50  isExit=True  -> BuyToCover 10 to both, every account FLAT
```

**The copier had never been able to open a short before this fix.**

**Fix**: choose the action from the account's current position at submit time, as the close path
does. ⚠️ **Do NOT "fix" it by widening the copier's `leaderIsExiting` test** — a label is the
wrong source for that question; the durable version derives exit-ness from the position DELTA.
That is the larger change and it belongs with `P3-32`/`P3-31`, not with this one.

---

### P2-98. A partially filled copy measures only its FIRST slice, and blames the wrong thing for the rest — CLOSED 2026-08-13

**Where**: `TradeCopierEngine.ObserveFollowerFill` (~`:4472`).

```csharp
pendingFound = _pendingCopies.TryGetValue(exec.Order, out pending);
if (pendingFound) _pendingCopies.Remove(exec.Order);      // <- on the FIRST fill
```

A partial fill delivers several executions for the **same `Order` object**, so every slice after
the first misses the lookup. Measured live: a 10-lot copy filled `1 + 9`.

```
COPIER_FILL_MEASURED     | latency=115.15 ms, slippage=2 ticks     <- the 1-lot slice
COPIER_FILL_NOT_MEASURED | Pending-copy lookup missed ...          <- the 9-lot slice
```

Two consequences, and the second is the worse one:

1. **The metric describes the smallest slice.** Here the measured slippage came from 1 contract
   and the 9 carrying the rest of the risk were unmeasured. `P?-66` was closed on the finding
   that the numbers were right and unexposed; this is the numbers being *incomplete* and looking
   whole.
2. **`FILL_NOT_MEASURED` asserts a diagnosis that is FALSE here**: *"OrderId is display-only and
   must never be used as the map key."* The lookup did not miss because of key misuse — it
   missed because the entry was already consumed. A routine partial fill therefore emits an
   alarm that sends the reader after a bug that is not there, which is how an operator learns to
   ignore the event. Same family as the audit false positives in `P3-30`.

**Fix**: keep the pending entry until the order is terminal, and accumulate across slices.
⚠️ `P?-66`'s rule applies to the accumulation: a latency rejected by the sanity bound must **not**
count as a sample, or the average silently becomes a lie again.

> **Fixed 2026-08-13.** The grain of a measurement moved from the SLICE to the COPY.
> `PendingCopy` now carries `SliceCount`, `FilledQuantity` and `FollowerNotional`; the entry is
> removed when the order is **done**, not when it first fills; and the reported slippage is
> `FollowerNotional / FilledQuantity` vs the leader fill — **quantity-weighted**, because an
> unweighted mean of the slices is this same defect in a subtler form, a 1-lot counting for as
> much as the 9 lots beside it. One sample per copy, one quarantine decision per copy.
>
> **Completion needs BOTH signals and neither alone is sound.** Quantity alone loses a copy
> cancelled or rejected after a partial fill — the measurement would never be reported and the
> entry would sit until the bounded FIFO reaped it. Order state alone loses the ordinary case,
> because NT8 does not guarantee `OrderState` is already `Filled` when the last execution
> arrives (and the test stub leaves a submitted order in `Submitted` for good, which is why a
> state-only implementation passes review and measures nothing).
>
> **Latency is read ONCE, on the first slice**, and the verdict is carried on the pending entry.
> That is what enforces `P?-66`'s rule: re-deriving it at completion would let a *rejected*
> reading be replaced by a later slice's — a plausible figure manufactured out of the same
> disagreeing clocks that produced the rejected one. It is also the right measurement:
> time-to-first-fill is how long the copy took to **reach** the market, where time-to-complete is
> how long the market took to fill ten lots, which is liquidity.
>
> **A third thing had to change, and it is not arithmetic.** `FILL_NOT_MEASURED` asserted
> *"OrderId is display-only and must never be used as the map key"*. That trap is real —
> `OrderReferenceComparer` exists because of it — but it was the cause of **none** of the misses
> seen live, and the event also fires on every manual or strategy fill on an account that
> happens to be a follower. It now states what is known and lists the causes it genuinely
> cannot tell apart, likeliest first. A new `FILL_SLICE` event covers the gap in between: a
> partial fill is neither a measurement nor a miss, and must not be mistakable for either.
>
> Nine tests, and three of them (`Latency...NotTheLasts`, `ALatencyRejected...NotRescued`,
> `ATerminalOrderState...`) were **GREEN at baseline for the wrong reason** — the later slice
> missed the lookup, so nothing could overwrite the first slice's reading. They are regression
> guards on the new shape, not evidence of the old defect; the six that were red are that.
> `mutation/mutate_p298.py`: **13 mutants, 0 survivors.**
>
> ⚠️ One anchor elsewhere broke on this change (`mutate_ui1.py`'s latency-sample mutant, which
> named `latencyAccepted`/`latencyMs` — both now live on the pending copy). `check_anchors.py`
> caught it. Re-anchored, same mutant, still killed.

---

### P1-99. The copier sizes each leader EXECUTION independently, so a leader order that fills in small slices can copy NOTHING — CLOSED 2026-08-14 (v1.20.0)

**Where**: `TradeCopierEngine.OnExecution` — the whole copy path runs **per execution**, and
`ScaleQuantity` rounds each one on its own. `COPY_SKIPPED_SUB_MINIMUM` is raised when the result
lands below one contract.

**Found by driving the deployed box** while live-validating `P2-98`, not by review and not by the
suite. A 100-lot MNQ market order on the leader filled **5 + 95**, and the copier treated the two
slices as two independent copies:

```
COPIER_EXEC_SEEN              MNQ SEP26 Buy 5@30160    order='P298_LEADER_100LOT'
COPIER_COPY_SKIPPED_SUB_MINIMUM  scaled quantity for NQ SEP26 on 'Sim-ORB' came out below 1
                                 contract from leader qty 5 (ratio 1, sizing QuantityRatio)
COPIER_EXEC_SEEN              MNQ SEP26 Buy 95@30160.25 order='P298_LEADER_100LOT'
COPIER_COPY_SUBMITTED         NQ SEP26 Buy 10 submitted to 'Sim-ORB'
```

Here it came out right by luck — 95 MNQ scaled to 9.5 NQ and rounded **up** to 10, which happens to
be the whole 100-lot's equivalent. Change the fill shape and it does not:

* a 100-lot filling as **20 × 5** drops **every** slice. The leader is long 100 MNQ (10 NQ
  equivalent) and the follower is **FLAT**, with twenty `COPY_SKIPPED_SUB_MINIMUM` lines and no
  error anywhere;
* a 100-lot filling as **10 × 10** copies 10 × 1 NQ = 10 NQ, which is right;
* a 100-lot filling as **11 + 89** copies 1 + 9 = 10 NQ, also right.

So the follower's size is a function of **how the leader's order happened to fill**, which is a
property of the book, not of the trade. `P1-71`'s live validation already found the single-order
version of this (1 MNQ at ratio 1.0 rounds below one NQ contract and is dropped); what is new is
that **partial fills manufacture small leader quantities out of a large order**, so the case is
reachable from a trade nobody would call small.

**Why it is P1 and not P2**: the failure is silent position divergence — `P0-5`'s family. The
copier's whole contract is that the follower mirrors the leader, and here it does not, with the
audit log recording each drop as a routine skip.

**Fix — the shape, not the arithmetic.** Rounding a slice harder is the wrong answer: rounding 5 MNQ
UP to 1 NQ doubles the copy on a 20-slice fill. What is wrong is the **grain**: the copier decides
size per execution where the leader's intent is per ORDER. Two candidates, and the second is the one
this repo's own history argues for:

1. Accumulate the leader's fills per order and copy the DELTA of the correctly-scaled cumulative
   target — i.e. after 5 filled, target = round(0.5) = 0, copy nothing; after 100, target = 10, copy
   10. Self-correcting, and each slice's rounding error cannot accumulate.
2. Carry a per-relationship fractional REMAINDER across slices. Simpler to write, but it is state
   that has to be reset on flat, on quarantine, on a symbol change and on a restart — four ways to
   get a wrong size that a reader cannot see.

⚠️ **Whichever is chosen, the exit side is NOT symmetrical** and must be reasoned about separately:
`P0-6`'s exit clamp already mirrors the follower's actual position rather than scaling the leader's
quantity, so exits do not have this defect and must not acquire it. Same asymmetry as `P2-98`'s
quarantine decision and `P1-23`'s fail-closed sizing.

⚠️ **A test for this must feed MULTIPLE executions for one leader order.** Every existing copy-path
test sends a single execution for the full quantity, which is the same blind spot `P2-98` had on the
follower side — and the reason both defects survived a suite that was green.

**FIXED in `v1.20.0`.** Candidate 1 was taken: the grain of the decision moved from the EXECUTION to
the leader ORDER. `LeaderOrderFillProgress`, keyed by the leader `Order` **object** (never `OrderId`
— `OrderReferenceComparer`, same reason as `_pendingCopies`), carries the cumulative leader quantity
and a per-`rel.Id` count of what has already been copied. Each slice recomputes the target from the
cumulative and copies the **delta**. Rounding cannot accumulate, because every slice re-derives the
whole target rather than adding to it: 20 × 5 copies 0,1,1,0,0,1… summing to exactly **10**.

Four things in it are worth reusing:

* **The clamp goes on the DELTA, not the cumulative.** The cumulative is read from a new
  `preClampQty` out-param, so `MaxPositionSize` is applied once, to the increment, against the
  capacity actually left. Clamping the cumulative first and then subtracting what earlier slices
  copied subtracts them **twice** — with `MaxPositionSize` 10 a 50+50 fill copies 5 and then
  nothing, and every event reads as success.
* **Credit what was SENT, not the target.** A copy cut short by the clamp leaves its shortfall
  outstanding, so a later slice re-offers it when room appears. Crediting the target forgives the
  clamped contracts silently.
* **Exits are NOT routed through it**, and a mutant pins that. `P0-6`'s exit clamp already mirrors
  the follower's ACTUAL position, so exits were never fill-shape dependent; adding the accumulator
  would defer closing a position the leader has left — `P0-5`'s failure arriving through this fix.
* **Releasing the accumulator needs the terminal-STATE signal as well as the quantity one**, which
  is `P2-98`'s lesson on the other side of the copier. ⚠️ With a documented limit: a cancel delivers
  **no execution**, so the state check only fires when the final fill arrives with the order already
  terminal. An order cancelled and then silent is released by the bounded FIFO — that is the
  backstop, not a second mechanism.

**Evidence**: suite 1328 → **1355**, eleven new tests, and they are the only copy-path tests in the
repo that send more than one execution for one leader order. `mutation/mutate_p199.py`, **9 mutants /
0 survivors** — but the FIRST run had **three** survivors and each said something different:

1. one was **unkillable by construction** and caught a wrong comment rather than a wrong line: the
   cumulative is read from the pre-clamp out-param, so the position argument on that call cannot
   affect it. The mutant was repointed at the real defect (taking the clamped RETURN value);
2. one was a real **coverage gap** — the first clamp test had capacity fitting *exactly*, which made
   "credit the target" and "credit what was sent" the same number;
3. one had **no observable at all**, because a leaked accumulator changes no copy. An internal
   `LeaderOrderProgressCount` makes the release assertable, and writing that test is what surfaced
   the cancel-delivers-no-execution limit above.

---

### P1-100. A SHADOW-only lockout BLOCKS real orders, so shadow mode halts the account it is only supposed to observe — ✅ CLOSED 2026-08-14 (session 38), v1.21.0

**Where**: whatever `nt_place_order` / the bridge consults for "is this account locked out". `P2-92`
made `CanTrade` read the **authority** a lockout was imposed under, so a shadow observation could not
gate trading. This path does not, or does not read the same record.

**Found by driving the deployed box** while live-validating `P1-99`, on sim accounts. Guard in
`shadow`, armed. A 100-lot MNQ entry tripped two rules, and both recorded shadow-only observations:

```
13:00:47  Sim101  SHADOW_LOCKOUT  Rule MAX_SIZE_BREACH recorded a shadow-only lockout
                                  observation; no flatten executed.
13:01:21  Sim101  SHADOW_LOCKOUT  Rule DAILY_LOSS_BREACH recorded a shadow-only lockout
                                  observation; no flatten executed.
```

Every consequent action was correctly suppressed — `[SHADOW] Would execute action FlattenPosition`,
`LOCKOUT_SWEEP_SHADOW: Would execute lockout sweep` — and **nothing was flattened**, which is
`P2-92` working. But every subsequent order was refused:

```
nt_place_order Sim101 MNQ Sell 100 Market  ->  "Order blocked: Account Sim101 is locked out."
nt_place_order Sim101 MNQ Buy 1 Limit@20000 ->  "Order blocked: Account Sim101 is locked out."
```

The second is the proof: a limit 10,000 points below the market can never fill, so this is not a risk
check on the order's content — the **account** is gated. The only lockouts on the box that day are the
two shadow observations above.

**Why it matters even though it fails CLOSED.** It is not a safety hole; it is more restrictive than
configured. The consequence is worse than it looks anyway: `shadow` exists so an operator can evaluate
the guard **without it touching trading**, and an operator whose account freezes during evaluation
turns the guard OFF. A mode whose whole purpose is "observe only" that halts the account is a mode
nobody will run, which costs the guard the evaluation period it exists for.

⚠️ **Same shape as `P1-90`**: the fix went into the sites that were filed, and a further site reads
the same state by another route. Find every reader of the lockout record before fixing one.

**Fix**: one reader, or one predicate. `P2-92` stored the authority precisely so this question has a
single answer; a second call site that re-derives it is the defect. A test must assert a shadow
lockout leaves `nt_place_order` WORKING — a positive-only test that a live lockout blocks passes under
this defect.

**FIXED in `v1.21.0`** (`RiskGuardAddOn.cs`). The reader was `IsAccountLocked`, which the bridge's
`PlaceOrder`, `PlaceOcoOrder` and `PlaceAtmOrder` all consult (plus `GET /api/lockout`, so the status
an operator reads came from the same place). It returned `state.IsLockedOut` raw. `CanTrade` was
never wrong.

**It was wrong in BOTH directions, and only one of them was filed.** `P2-92` (authority) and `P2-94`
(deadline) had each taught `CanTrade` a clause; neither reached this reader. So:

| | `CanTrade` | `IsAccountLocked` (before) |
|---|---|---|
| shadow-only rule breach | allows | **refuses** ← the filed defect |
| TIMED manual lockout (`LockAccount(a, 60)`) | refuses | **allows** ← found while fixing it |

The second row is `P2-94` verbatim, surviving at a second reader nine days after `P2-94` was closed —
the operator asks for a 60-minute lockout, the bridge keeps placing orders, and the sweep flattens
each resulting fill. Filing the defect that was *observed* would have fixed one row.

Three things worth reusing:

* **The fix is a predicate, not an edit.** `LockoutBinds(accountName[, state])` is now the only place
  that answers "does a lockout bind here", and all three readers call it — `CanTrade`,
  `IsAccountLocked`, and the entry-cancel block in `OnOrderUpdate`, which was a **third** reader
  nobody had counted. A predicate with one caller is a convention; a predicate with every caller is
  a guarantee.
* **The relaxation is keyed on the LOCKOUT's authority, never on the current mode.** Reading `_mode`
  here passes the headline case and makes a mode switch a lockout bypass — flip a live guard to
  `shadow` and every real lockout evaporates. That is `mutate_p292.py`'s "THE WRONG FIX" mutant, and
  it is the obvious implementation.
* **The third reader's damage was a LOG LINE, not an order.** `DrainPendingCancels` already withholds
  intervention cancels in shadow (`P0-51`), so nothing was cancelled — but the block still wrote
  `ENTRY_CANCEL: Cancelled order N because account is locked out` into `interventions.jsonl`, the
  file that has to stay readable after an incident. Same family as `P2-101`: a claim about an action
  the current mode does not perform.

⚠️ **The whole suite — 1355 tests — stayed green through the fix.** Every test that touched this set
`state.IsLockedOut = true` directly, which is the single combination where all three readers agree.
The tests that close it assert **both** readers at once, and one of them
(`TheReportedGateAndTheEnforcedGateCannotDisagree`) drives all **48** combinations of flag × deadline
× authority × armed × bypass-listed and asserts `CanTrade == !IsAccountLocked` — the instance tests
would all still pass against a fourth reader added tomorrow; that one states the invariant.

⚠️ **Extracting the predicate broke two of `mutate_p292.py`'s anchors**, which had matched text inside
`CanTrade`. `check_anchors.py` caught it in the same commit. They were **repointed** at `LockoutBinds`
rather than retired — the invariant did not change, only its address — and they are now strictly
stronger, since one edit there regresses all three readers. `mutate_p1100.py` deliberately does **not**
duplicate them.

Suite **1424/0** (+69). Battery `mutation/mutate_p1100.py`, **4 mutants / 0 survivors**, wired into CI
as the 26th. `mutate_p292.py` re-run: **11/0** against the repointed anchors.

---

### P2-101. A lockout in shadow mode retries its flatten FOREVER, because in shadow the flatten never happens — ✅ CLOSED 2026-08-14 (session 38), v1.22.0

**Where**: `LOCKOUT_FLATTEN_RETRY` / the lockout sweep's retry loop.

The retry is conditioned on "position still open". In `shadow` the flatten is not executed, so the
position stays open, so the condition never clears:

```
13:01:24  LOCKOUT_FLATTEN_RETRY  Flatten attempt for Sim101 (position still open)
13:01:29  LOCKOUT_FLATTEN_RETRY  Flatten attempt for Sim101 (position still open)
13:01:34  ...   every 5 seconds, on THREE accounts, indefinitely
```

It ran from 13:01:24 until the operator flattened by hand at 13:02:24 — ~13 rounds × 3 accounts × 2
events ≈ **78 log lines that describe nothing changing**, and it would have continued indefinitely.
`interventions.jsonl` is the audit record, and this is the one file that has to stay readable after an
incident.

⚠️ **`An alarm that is always on is off`, again** — the fifth instance of this family (`P3-30`'s audit
firing on a protected account, `P2-98`'s `FILL_NOT_MEASURED` on every manual fill, the two unpassable
batteries, now this). The pattern is stable enough to state as a rule: **a retry whose exit condition
is an action the current mode does not perform will never exit.**

**Fix**: shadow must not enter the retry loop at all — it has already logged what it would do, once.
The retry belongs to the enforcing path. ⚠️ Do NOT fix it by capping the retries: a capped loop still
logs 78 lines on a live account where the flatten is genuinely failing, which is the case the retry
exists for and where the operator needs it.

---

**FIXED and live-validated in `v1.22.0`.** Two halves, and the second was not in the filed defect.

**The retry is bounded by an ATTEMPT COUNT, and the budget depends on the mode**:
`LockoutPhaseAttemptBudget()` returns **1** outside an acting mode and **6** in `live`.

⚠️ The 1 is not a tuning choice. `ProcessAction` answers `SHADOW (SKIPPED)` for every action outside
`live`, so a second identical `[SHADOW] Would execute FlattenPosition` carries nothing the first did
not — **shadow's product is the observation, and the observation is complete after one.** The 6 is
the ~30 seconds the old stuck warning was written for (retries are 5s apart), and it exists because a
broker can reject a real flatten. Bounding the loop without asking *why it could not exit* is
`mutate_p2101.py`'s mutant 2, "THE PARTIAL FIX": it stops the unbounded growth and still repeats the
observation five more times than shadow needs.

⚠️ **The second half is sharper, and it is the reason nobody was told.** `LOCKOUT_STUCK` — the one
alarm that says *the guard is not getting this position closed* — read:

```csharp
UtcNow > stateModel.LastLockoutFlattenAttempt.AddSeconds(30)
```

while the retry immediately above it set `LastLockoutFlattenAttempt = UtcNow` **every 5 seconds**. The
interval it measured was reset by the loop it was watching, so it could never reach 30. The live run
that found `P2-101` produced 13 rounds of retries and **zero** stuck lines. **One alarm that could not
stop and one that could not start, in the same block.** Both are keyed on the attempt count now, from
one method, so they cannot drift; `LockoutStuckLogged` makes the give-up exactly one line, and it
names shadow explicitly so an operator is not sent hunting a broken account.

Also collapsed: four sites cleared this state cluster with their own copies of the reset.
`AccountState.ResetLockoutPhase()` owns it — adding a third field to a cluster with four hand-written
resets is exactly how `P1-100`'s three readers happened.

**Live-validated** (guard armed in `shadow`, 11 MNQ against a limit of 10):

```
10:14:14  SHADOW_LOCKOUT         Rule MAX_SIZE_BREACH ... no flatten executed.
10:14:14  LOCKOUT_PHASE          Phase: PendingFlatten
10:14:14  LOCKOUT_FLATTEN_RETRY  Flatten attempt 1 of 1 for Sim101 (position still open)
10:14:14  LOCKOUT_STUCK          GIVING UP after 1 attempt(s) ... This is SHADOW mode -- no flatten
                                 was ever sent, so the position was never going to close.
```

…and then silence, for as long as the position was held. Before: ~12 lines per minute per account,
indefinitely.

Suite **1424 → 1436/0**. `mutation/mutate_p2101.py`: 7 mutants, **6 killed, 1 DECLARED EXPECTED
SURVIVOR** (dropping the reset in `ResetLockoutPhase` is unkillable by construction — every route
back into a phase goes through `EnterLockoutPhase`, which resets on entry).

⚠️ **Mutant 7 took two attempts to kill, and the failure is the defect restated.** The obvious
assertion — "no stuck warning after one of six attempts" — passed **under** the time-keyed mutant,
because on any sweep where the retry fires it refreshes the timestamp one line before the check reads
it. *No assertion about a sweep where the retry fired can catch a time-keyed alarm*, which is exactly
why the original never fired in production. The discriminator is the sweep that **spends the last
attempt**: count-keyed it fires, time-keyed it cannot.

---

### P2-107. `PEAK_GIVEBACK_BREACH` re-emits its flatten on every evaluation, so the same family survives `P2-101`'s fix on a different path — CLOSED 2026-08-14 (session 40)

**Where**: the rule evaluators, not the lockout phase machine — so `P2-101`'s attempt budget does not
reach it.

Measured on the box **immediately after `P2-101` was validated**, on the two follower accounts:

```
10:14:22  Sim-ORB   [SHADOW] Would execute action FlattenPosition triggered by PEAK_GIVEBACK_BREACH
10:14:25  Sim-ORB   ... 10:14:32, 10:14:33, 10:14:41, 10:14:42   -- 7 in ~20 seconds
```

Same shape as `P2-101` — an action re-emitted while a condition persists, in a mode that cannot clear
it — but a **different mechanism**: this is per-evaluation, driven by account/position updates rather
than a timer, so it has no spacing at all and its rate is set by market data.

**Why it is `P2` and not a duplicate**: `P2-101` was fixed inside `EvaluateLockoutPhase`, which is one
of several places that emit repeated actions. This is the second instance found in the same hour, on
the first accounts anyone looked at, which is the signal that **the deduplication belongs where the
actions LEAVE the guard, not inside each producer.** `CoalesceActions` (`P1-19`) already sits on that
path and merges actions *within one batch*; nothing suppresses the identical batch arriving three
seconds later.

**Fix**: prefer one mechanism over N. A per-(account, rule, action) "already emitted, not yet
resolved" record on the outbound path would cover `P2-101`'s class, this one, and whatever the third
turns out to be. ⚠️ It must not suppress a **live** re-attempt that is doing real work — `P2-101`'s
budget of 6 exists because a broker can reject a flatten — so the record has to be cleared by the
condition resolving, not by a timer.

Related: `P2-101` (same family, bounded), `P3-30` (an audit firing on a correctly protected account),
`P2-98`'s `FILL_NOT_MEASURED`. **Sixth instance of *an alarm that is always on is off*.**

**Fixed by** `addons/GuardActionDeduplicator.cs` (names no NT8 type, so the harness executes it —
the `P2-27` pattern) behind one new `DispatchActions` method that **all five emission sites now
use**. Actions are coalesced within the batch (`P1-19`, unchanged), then de-duplicated across
batches, then processed. Suite **1469/0**; battery **18/18**, no survivors.

Four things in it are worth reusing, and the last two are the ones that cost time:

1. **The record clears when the CONDITION resolves, never on a timer.** A time-based expiry
   re-admits the action while the condition is still true, which is the defect again on a slower
   clock. The observable that means *resolved* is that the producer evaluated the account and did
   **not** ask for the action — so `DispatchActions` takes the accounts the producer **evaluated**,
   including the ones it decided needed nothing, and absence from that batch is the resolution.
   ⚠️ An account left out of the declared scope keeps its record forever; one wrongly included has
   its record cleared by a producer that never looked at it. Both directions are silent.
2. **The budget is re-read from the mode on every call** — `1` outside an acting mode, `6` inside
   one, the same numbers as `P2-101` so the two cannot drift in a reader's head. **The 1 is the
   fix, not a tuning value.** Because it is not baked into the record, arming to `live` re-admits a
   key `shadow` had already exhausted, which is exactly what an operator switching to live wants.
3. ⚠️ **The scope must carry the PRODUCER as well as the account.** `AccountItemUpdate` does not
   evaluate the lockout rules, so its batches legitimately lack their keys — if any producer's
   silence could clear any record, nearly every batch would clear nearly everything and the
   mechanism would do nothing **while passing every test that drives a single producer**. This is
   also why `EvaluateAggregateSizing` was split out of the `PositionUpdate` batch: it iterates
   every subscribed account while the rules beside it looked at one, so the two have different
   scopes. The price is that an aggregate flatten and a per-account flatten for one account are no
   longer merged; two flattens are idempotent at the broker, a de-duplicator that clears itself is
   not.
4. ⚠️ **The operator's panic buttons deliberately do NOT come through here.**
   `TriggerManualFlatten`/`TriggerManualFlattenAll` call `ProcessAction(forceLive: true)` directly,
   so a second press flattens twice. A safety control that ignores the second press because it
   recognised the first is a worse defect than the one this closes. Pinned by a mutant.

⚠️ **The suite was 1436 green before this change and 1436 green after it**, because every existing
test drives one event and a de-duplicator only speaks on the second. Same shape as `P1-100`'s 1355
and `P0-96`'s 1311.

⚠️ **And the battery went 13/13 on its first run, which is when to trust it least.** Five more
mutants, aimed at the parts the first thirteen never touched, **all survived**. The sharpest
reverted the `AccountItemUpdate` handler to its old bare loop — *the one path the defect was
measured on walking around the entire mechanism* while eleven tests of that mechanism passed. That
is `P3-30`'s shape, and only a test that drives the **event** rather than the helper can see it.
The other four: the key dropping its rule, the key dropping its action type, the session reset no
longer clearing, and the account-wide producers declaring an empty scope (which fails **open**, so
everything is still dispatched and nothing else notices).

⚠️ **Two of this repo's own gates were caught proving nothing by this work, both by the same
habit — detection by substring over a region nobody bounded:**

* `mutation/check_anchors.py` recognised only `(PATH, label, old, new)` 4-tuples and **silently
  `continue`d** on any other shape. This battery's tuples put the file constant second, so **all 18
  anchors were skipped** and the battery printed `ok`. It now finds the `ast.Name` wherever it sits
  and treats an unreadable entry as a **failure**, not a skip. Anchor count **283 → 301**.
* `tools/check_expected_survivors.py` searched for `EXPECTED SURVIVOR:` in
  `src.split('MUTANTS = [', 1)[-1]` — which is not the list, it is *everything after the list
  opens*. A closing comment telling the next reader how to declare one made the gate report a
  declaration this battery does not make, and then demand the wrong exit form. It parses the
  `MUTANTS` list with `ast` now, and **refuses** a battery it cannot read rather than reporting
  `all mutants must die` about one it never inspected.

  Same family as `check_next_list_ids.py` reading `positionClosed: true` in a title as a CLOSED
  status, and as the matrix comment that would have counted a deleted battery as wired. **Three
  gates, one habit.**

**Live-validated 2026-08-14 on Sim101**, guard armed in `shadow` at `v1.23.0`, `nt_compile`
`errorCount: 0`. `DailyLossLimit` was temporarily lowered to force the breach, then the config was
restored **byte-for-byte** (md5 verified against a backup taken first) and the account flattened.

`DAILY_LOSS_BREACH` — a rule with **no** producer-local latch, so it evaluates true on every PnL
tick — produced, per episode, **exactly one `SHADOW_ACTION` and exactly one `ACTION_SUPPRESSED`**:

```
14:36:59.162  SHADOW_ACTION      [SHADOW] Would execute action FlattenPosition triggered by DAILY_LOSS_BREACH
14:36:59.162  ACTION_SUPPRESSED  Holding back FlattenPosition from DAILY_LOSS_BREACH on Sim101: already
                                 reported once and the condition has not resolved; the guard is not acting,
                                 so repeating it adds nothing. Attempt 1 of budget 1, producer
                                 AccountItemUpdate. This is the last line about it until the condition resolves.
```

Both at the same millisecond, because NT8 delivers several `AccountItem` changes in one burst and
each is a separate dispatch into the same scope. The producer, budget and attempt in that line
exist only in the new class, so the wiring is proven **in the running assembly** and not just on
disk. The historical file holds **378** `DAILY_LOSS_BREACH` shadow lines under the old behaviour.

### ⚠️ The exemplar this defect was FILED on was not an instance of it

`PEAK_GIVEBACK_BREACH` has had a **producer-local latch since `v1.0.0`** (commit `b125132`,
2026-08-06): it fires on the first breach of an episode and re-fires only when the position gives
back **further than the prior trigger point** (`worsenedSinceTrigger`). That was live when the
7-in-~20s burst was captured, so those seven lines were **seven genuinely deeper givebacks on a
fast move**, not one condition reported seven times — and `P2-107` correctly does **not** suppress
them. Measured again live: three emissions in four seconds, **zero** suppressions, because each was
a new episode by the rule's own definition.

**So the filing generalised from an exemplar that did not belong to the class, and reached the
right conclusion anyway.** The class is real and large — every rule *without* a latch
(`DAILY_LOSS_BREACH` 378, `MAX_TRADES_BREACH` 251, `EDGE_WINDOW_BREACH` 123, `MAX_SIZE_BREACH`,
`AGGREGATE_SIZE_BREACH`, `CONSECUTIVE_LOSS_BREACH`) was streaming one line per evaluation, and each
of those is now one per episode. But the specific reading *"`PEAK_GIVEBACK` re-emits the same
demand"* was wrong, and it would have become folklore if the fix had been validated only against
the suite. **Check whether the exemplar has its own bound before generalising from it** — and
re-drive the exact instance live, because the suite cannot tell you that the rule you are citing
already solved its own half.

---

### P2-108. `NAKED_POSITION` repeats every 10 seconds on a path `P2-107` does not cover, because it is a LOG and not an action — OPEN, found live 2026-08-14

**Where**: the guard audit (`P3-30`'s detector), which calls `LogEvent` directly rather than
raising a `GuardAction`. `DispatchActions` therefore never sees it.

Measured on Sim101 during `P2-107`'s own live validation, holding one unstopped 2-lot in `shadow`:

```
14:42:05  NAKED_POSITION  MNQ SEP26: position=2, fsmState=FlattenPending, covered=0, gap=2
14:42:15  ... 14:42:25, 14:42:35, 14:42:45, 14:42:55   -- 12 identical lines in 120 seconds
```

**180 in the log, 142 of them today.** The condition is real — the position genuinely has no stop —
but the guard is in `shadow`, so it cannot attach one, so the audit interval is the only thing
setting the rate. That is *a retry whose exit condition is an action the current mode does not
perform* (`P2-101`) restated for an alarm, and the **seventh** instance of *an alarm that is always
on is off*.

**Why it is a separate ID and not a `P2-107` remainder**: `P2-107` de-duplicates **actions**, at the
point where they leave the guard. This is a log line with no action behind it, so no amount of work
in `DispatchActions` reaches it. The fix has to sit at `LogEvent` for the alarm event types, or the
audit has to carry its own "already reported, not yet resolved" record — and **whichever is chosen,
it must not be a third mechanism**: that is the mistake `P2-107` exists to stop repeating.

⚠️ Note the shape of the discovery: it was found by **driving the deployed box**, in the validation
run of the fix for its own predecessor — exactly as `P2-107` was found in `P2-101`'s. Third time in
three sessions that the validation run produced the next defect.

---

### P1-102. There is no MCP tool to READ or CLEAR a lockout, so an account frozen by the guard cannot be recovered by the agent that is driving it — OPEN, found 2026-08-14

**Where**: `nt8-mcp-bridge/mcp/lib/tools.js`. The bridge has
`POST /api/lockout` with `action` of `status` | `unlock` | `reset` | `clear`, hardened by `P1-90`'s
account resolver. **No `nt_` tool calls it.**

**Found while cleaning up after `P1-99`'s live validation.** Three sim accounts were locked out by the
guard; clearing them needed a raw `curl` with the bridge token read off disk
(`Documents/NinjaTrader 8/mcp_token.txt`), because no tool exposes the route.

**Why it is P1 and not a nice-to-have**: `P1-100` means a **shadow-only lockout can freeze an
account**. So the mode an operator is told to evaluate the guard in can halt trading, and the toolset
they are driving it with has **no way to undo that**. Those two defects compose into "the guard
stopped my account and I cannot start it again", which is the shape that gets a risk system deleted
rather than debugged.

⚠️ **`unlock` REMOVES PROTECTION** — it is the one write here that must not get a permissive schema.
`P1-90` records that `HandleLockout` used to feed a guessed account name straight into
`UnlockAccount` with no existence check, so omitting the field unlocked `Sim101` and a typo returned
`success:true, isLockedOut:false` for an account that does not exist. The resolver fixed the addon;
a new tool must not re-open it from the other side — no `default:` on `account` (`P1-91`), and the
`action` enum pinned to the addon's own whitelist (`P1-72`'s remedy).

⚠️ **Verify the ENFORCER, not the report.** `{"success":true,"isLockedOut":false}` is a claim. When
this was done by hand the unlock was confirmed by re-sending an unfillable limit order and watching it
be accepted, because `F-9`'s lesson is that what a rule REPORTS can disagree with what it DOES in
either direction. The tool's test must assert the same way.

---

### P0-104. `nt_emergency_flatten` CANCELS ITS OWN FLATTEN ORDER, reports success, and locks the account so the operator cannot exit by hand — ✅ CLOSED 2026-08-14 (session 38)

**Where**: `McpBridgeAddOn.cs`, `EmergencyFlatten`, steps 3-5. In the `nt8-mcp-bridge` repo, which
`P2-27` records as untested.

**This is the panic kill-switch.** It runs five steps per account: terminate strategies, cancel all
working orders, `acc.Flatten(...)`, **a second cancel pass for "residual bracket/OCO orders"**, then
engage a lockout. `acc.Flatten` is asynchronous — it *submits* a `Close` market order. Step 4 then
enumerates `acc.Orders` for anything in `Working`/`Submitted`/`Accepted`/`ChangePending`/`PartFilled`
and cancels **every one of them**, which includes the `Close` order step 3 submitted a moment
earlier. It cannot tell its own flatten from a residual bracket, because it does not try.

**Measured on Sim101 2026-08-14 13:45:36Z**, while live-validating `P1-100`. Account long 11 MNQ, one
resting limit:

```
13:45:36  35541  Limit Buy 1   McpBridge  CancelPending -> CancelSubmitted -> Cancelled   <- step 2, correct
13:45:36  35542  Market Sell 11  Close     Initialized -> Submitted -> CancelPending
13:45:36  35542                            -> CancelSubmitted -> Working -> Cancelled     <- step 4 kills the flatten
```

The response:

```json
{"success": true, "cancelledOrders": 2, "firstPassCancelled": 1, "residualCancelled": 1,
 "flattenedAccounts": 1, "lockoutMinutes": 2, "errors": []}
```

`firstPassCancelled: 1` is the resting limit; **`residualCancelled: 1` is its own `Close` order**. The
counts are the proof — there were exactly two orders on the account and the second one was the
flatten. The position was **still long 11** afterwards.

**Why P0.** Sequence the consequences the way an operator hits them in a crisis:

1. their protective stops are cancelled (step 2, and it is right to do so before flattening);
2. the flatten is cancelled (step 4), so the position is **naked** — no stop, no exit;
3. the account is locked out (step 5), so `nt_place_order` **refuses** the exit they would place by
   hand. Measured immediately after, on the same account:
   `{"error": "Order blocked: Account Sim101 is locked out."}`;
4. the tool returns **`success: true`, `flattenedAccounts: 1`**, so nothing tells them any of this.

The panic button removes the protection, leaves the position, and takes away the ability to fix it —
and says it worked. On a funded account that is the whole account.

⚠️ **`flattened++` counts the CALL, not the outcome** — `P1-70`'s family, and the same shape as
`P2-98`'s latency verdict: a measurement taken before the thing being measured has happened. There is
no completion signal anywhere in this method; it never looks at the position again.

**Fix**: the residual pass must exclude the orders this call submitted (`acc.Flatten` returns nothing,
so capture `acc.Orders` before step 3 and cancel only the set difference — or filter by `Name ==
"Close"`, which is weaker and would break on a bracket legitimately named that). Then re-read the
position and report what is **actually** flat. And the lockout in step 5 must not be applied to an
account this call failed to flatten: locking an account with an open unprotected position is strictly
worse than not locking it.

⚠️ The tests for this live in `nt8-mcp-bridge`, which has none (`P2-27`). The `BridgeAccountResolver`
pattern applies: extract the order-set arithmetic into a class that **names no NT8 type** and execute
it. "Which orders did I submit during this call" is pure set logic and does not need a broker.

**FIXED and live-validated 2026-08-14** (`nt8-mcp-bridge`, commit `bf1f901`). Two halves:

* **`addons/BridgeFlattenPlan.cs`** — the set arithmetic. Residual = *still active* **AND** *already
  present before the call began*; anything else this call created. It is generic over `T : class`
  with **reference** identity (NT8's `OrderId` is not stable — it is why the core keys its copy
  progress with `OrderReferenceComparer` — and both snapshots are taken inside one synchronous
  dispatcher invoke). Names no NT8 type, so `tests/BridgeTests.csproj` **executes** it. Fourth file
  to use `P2-27`'s cheap pattern.
* **The report stopped claiming an outcome.** `flattenRequestedAccounts` and
  `flattenOrdersSubmitted` say what was asked for and what reached the book; **`accountsStillOpen`**
  is read *after* the pass, behind a bounded settle poll (10 × 150ms, exits on the first clean read,
  so the healthy path pays one iteration), and `success` now **requires it to be empty**. A panic
  flatten that left a position open is not a success whatever it cancelled on the way.

⚠️ **The "before" snapshot is deliberately UNFILTERED by order state.** A bracket leg sitting
inactive before the flatten and reaching `Working` after it is a genuine residual — filtering
"before" by state would classify it as new and let it survive, which is this defect in the opposite
direction. That is `mutate_p0104.py`'s mutant 4, and it **survived the first run**.

⚠️ **What that survivor taught, and it is the reusable part**: extraction made the *logic* executable,
but **how the caller BUILDS its argument stayed in the ungrepped file**. The source gate now pins the
unfiltered snapshot as well as the call. **Extraction moves the untested boundary; it does not remove
it** — so after extracting, ask what the caller still decides.

⚠️ The source gate also **caught its own author**: it asserts the old outcome-claiming field name is
absent from `McpBridgeAddOn.cs`, and the first draft of the *explanatory comment* named it. A gate
that greps cannot tell prose from code — the CI-matrix lesson (`a comment read as a gate`) arriving
from the other side, second instance in two sessions.

**Live-validated** on the identical scenario (position + one resting order, then panic):

```
before (v1.20.0):  firstPassCancelled 1, residualCancelled 1, flattenedAccounts 1,
                   success true   -> position STILL LONG 11
after:             firstPassCancelled 1, residualCancelled 0, flattenOrdersSubmitted 1,
                   accountsStillOpen [], success true   -> account FLAT
```

`residualCancelled` going **1 → 0** is the discriminating reading.

Harness **92 → 108/0**. `mutation/mutate_p0104.py`, **5 mutants / 0 survivors**. ⚠️ And wiring it up
found that **CI in `nt8-mcp-bridge` ran NEITHER battery** — the core's
`check_ci_runs_every_battery.py` only knows about the core's, so `mutate_p190.py` had never run on a
push since it was written. Both are wired now. *A battery nobody runs is a file.*

**What this fix does NOT do**: see `P1-106`. The lockout still lands on an account whose flatten
failed, and a lockout still refuses a position-**reducing** order. Those two together are what turned
this from "the flatten failed" into "and you cannot fix it".

---

### P1-106. A lockout refuses the order that would CLOSE the position it is locking you out of — ✅ CLOSED 2026-08-14 (session 39), refusal half live-validated

**Where**: `McpBridgeAddOn.cs` — the `IsAccountLocked` gate in `PlaceOrder`, `PlaceOcoOrder` and
`PlaceAtmOrder`. Filed while closing `P0-104`; it is the half of that incident the fix does not
address.

Every one of those paths is:

```csharp
if (IsAccountLocked(account.Name))
    return new { error = $"Order blocked: Account {account.Name} is locked out." };
```

It does not care what the order *does*. So an operator holding an open position on a locked account
cannot place the exit — the lockout traps them in the risk it exists to limit. Measured directly
during `P0-104`'s reproduction: Sim101 long 11, locked by the panic switch, and a Sell was refused.

**The guard already has this notion and the bridge does not.** `RiskGuardAddOn`'s entry-cancel block
is guarded by `IsPositionReducingOrder` (`P1-44`), precisely so a rate limit can never cancel a
protective order and leave a position naked. The same reasoning applies one level up: *a lockout must
stop you opening risk, never stop you closing it.*

The bridge's `PlaceOrder` already computes the current position — `P1-97` made it resolve
`SellShort`/`BuyToCover` from exactly that — so the information is in hand at the refusal site.

**Fix**: admit an order that strictly reduces the position (opposite side, quantity ≤ `|position|`)
even under a lockout, and log it as such. Two things to get right:

* the quantity clamp is load-bearing — a Sell of 20 against a long 11 is an exit *and* a new short 9;
* it must read the position, not the `OrderAction` label, because the label is chosen by the caller
  (`P1-97`, and `nt8-position-quantity-is-absolute`'s second half).

A test asserting only that a locked account refuses an entry passes under this defect.

**✅ CLOSED 2026-08-14 (session 39).** The decision moved into `nt8-mcp-bridge/addons/
BridgeLockoutGate.cs` — one predicate, three callers, `P1-100`'s shape deliberately — and the
bare `if (IsAccountLocked(...)) return blocked;` is gone from all three order paths.

* `PlaceOrder` admits an order that **strictly reduces**: opposite side, quantity ≤ |position|.
  The lockout test **moved down the method**, past the point where the instrument and the
  account's position in it are known — it used to run before the symbol was even read, which is
  why it could not tell an entry from an exit.
* **The quantity clamp is the load-bearing half.** A `Sell 20` against a long 11 is an exit *and*
  a new short 9, netted by NT8 into one order the operator reads as an "exit". The refusal names
  the 9 and the quantity that would work.
* **It reads the position, never the `OrderAction` label.** The direction passed in is the
  *request's* `buy`/`sell`; feeding `resolvedAction` back would re-read a label the caller chose,
  one statement after `P1-97` fixed exactly that. A source assertion pins it.
* ⚠️ **`PlaceOcoOrder` and `PlaceAtmOrder` stay refused, and that is a decision rather than an
  omission.** Both submit an entry plus stop and target legs, and the legs take the *opposite*
  side — so an OCO whose entry flattens a long leaves a resting stop and target that **OPEN a
  short** once either triggers. A bracket cannot be admitted on the strength of its entry. Both
  refusals now name a path that does work (a plain order, or `nt_close_position`, which is
  ungated).

**Evidence.** Bridge harness **133/0** (9 new tests). Battery `mutation/mutate_p1106.py`:
**8 mutants, 8 killed**. `nt_compile` **0 errors** on net48. Live on Sim101, locked by the panic
switch and flat: both a `buy 1` and a `sell 1` were refused with *"is locked out and the account
is FLAT in this instrument, so this order can only open risk"* — text that exists only in the new
class, so the wiring is proven in the running assembly, not just on disk.

⚠️ **The ADMIT branch could not be driven live, and the reason is a finding — see `P1-102`.**
Proving it needs a lockout imposed on an account that already holds a position, and **the
deployed system offers no way to do that**: `/api/lockout` implements only `unlock`/`reset`/
`clear` (anything else, including `lock`, silently falls through to a status read and returns
`success: true, isLockedOut: false`), and the only code path that imposes the binding bridge
lockout is `EmergencyFlatten`, which flattens the position *before* it locks. A guard-side
lockout does not help either: the box runs `shadow`, where `LockoutBinds` correctly returns false
(`P1-100`). So the admit branch rests on the executed predicate, its 8/8 battery — mutant 1
restores the shipped defect verbatim and dies against the exit tests — and the source gate on the
three call sites. **Say which half was measured; do not let one green stand for both.**

⚠️ **The mutation battery found a real gap the review did not**: mutant 7 replaced
`Math.Abs(positionQuantity)` with the raw value and **survived**, because every test passed a
positive quantity. With a signed `-11`, `11 > -11` refuses a legitimate cover — `P1-106` restored
on the short side only, which is precisely how `P0-96` hid behind 1311 green tests. The killing
test passes a signed quantity deliberately.

---

### P1-105. `nt_close_position` reports `positionClosed: true` after submitting nothing — CLOSED 2026-08-14 (session 41), live-validated

**Where**: `McpBridgeAddOn.cs`, `ClosePosition`, step 2.

```csharp
account.Flatten(new[] { pos.Instrument });
positionClosed = true;              // <- the CALL succeeded; the position has not closed
```

`positionClosed` is assigned unconditionally on the line after the call and returned as the tool's
answer. It reports that the method reached that line.

**Measured on Sim101 2026-08-14 13:46:33Z**, cleaning up after `P1-100`'s validation. Account long 11
MNQ, no lockout (just cleared), guard in shadow so nothing could intervene:

```
request   {"account": "Sim101", "symbol": "MNQ 09-26"}
response  {"status": "flattened", "positionClosed": true, "cancelledOrdersCount": 0}
```

`interventions.jsonl` records the HTTP call at `13:46:33` and then **no `ORDER_UPDATE` for Sim101 at
all** — the audit log covers the window either side, and the account logs every order transition, so
nothing was submitted. The position was still long 11. A plain `nt_place_order` Sell 11 closed it
immediately, and the copier mirrored the exit to both followers, so the account and the path were both
working.

**The mechanism was never established and the fix does not guess at one.** What was established from
the source is that the report could not distinguish "flattened" from "called Flatten and nothing
happened", which is why the failure was invisible. `status: "flattened"` was a constant string in the
return expression — never a claim about anything.

#### The shape: a second reader that was never told

`McpBridgeAddOn.cs` has exactly **two** `.Flatten(` call sites. `EmergencyFlatten` learned all of
this as `P0-104` and got `BridgeFlattenPlan` plus a bounded settle poll. `ClosePosition` was never
told — the same way `IsAccountLocked` was never told what `CanTrade` had learned (`P1-100`), and the
same way the copier's follower side and leader side each had to discover separately that an order is
not one fill. **When one path learns something, ask which other path answers the same question.**

#### The fix (`addons/BridgeClosePlan.cs`, new — names no NT8 type, so tests EXECUTE it)

* **The report is derived from two observations, not from reaching a line.** `flattenOrdersSubmitted`
  reuses `BridgeFlattenPlan.SubmittedByThisCall` — order-set arithmetic `P0-104` already validated —
  and `positionsStillOpen` comes from a bounded settle poll that stops as soon as the scope is flat,
  so the healthy path pays one iteration and no sleep. ⚠️ **Fourth `Thread.Sleep` site in this file**
  (handover §5.39); worst case ~1.35s and only on the path that failed.
* **`positionsMatched == 0` is NOT a close.** It is what a typo'd symbol produces, and it was
  previously indistinguishable from success.
* **One scope predicate for both passes.** The acting pass and the observing pass call the same
  `BridgeClosePlan` functions. If they disagreed, the report would be true about a set the caller
  never named — `F-9` restated. The source gate **counts** the call sites (≥3 symbol, ≥2 account)
  rather than checking one is present.
* **`P1-90` at a seventh site.** This handler *filtered* by account name instead of resolving one, so
  the six-site sweep never reached it: `account: "Sim1O1"` matched nothing and was reported as a
  successful close. It now refuses.
* **Root equality replaces `StartsWith`.** `symbol: "M"` was a request to close MNQ, MES, MCL and MGC
  together. ⚠️ The **expiry is still not compared** — deliberately, and the live run vindicates it:
  NT8 reports the position as `MNQ SEP26` while the caller passes `MNQ 09-26`, so an exact full-name
  match would have silently matched nothing. Recorded as a known limit rather than guessed at.
* **Cancels credit what was SENT** (`P1-99`'s rule at a second site). The old loop cancelled the whole
  list inside one `try/catch {}` and then added `toCancel.Count` regardless, so a throw on the first
  order reported every order in the list as cancelled.

#### Live validation (Sim101, 2026-08-14 ~20:05–20:10Z) — say which half

Five drives, all returning text that exists only in the new class:

| drive | result |
|---|---|
| flat account, `MNQ 09-26` | `nothing_to_close`, `positionClosed: false` (old: `"flattened"`) |
| `account: "Sim1O1"` | **refused**, naming the 96 available accounts |
| long 2 MNQ, `symbol: "M"` | `positionsMatched: 0` — **the old prefix filter would have closed it** |
| long 2 MNQ, `MNQ 09-26` | `matched 1, flattenOrdersSubmitted 1, positionsStillOpen [], closed true` |
| long 3 MNQ + resting limit, `MNQ` | `cancelled 1, flattenOrdersSubmitted 1, still open [], closed true` |

⚠️ **Only the healthy and empty paths are live-validated.** `close_not_submitted` — the status the
original defect would now produce — **could not be driven on the box**, because the mechanism of the
original `Flatten` no-op was never established and cannot be reproduced on demand. That path rests on
the executed predicate and its battery. One green does not stand for both.

#### What the battery caught that review did not

**18/18 killed, after 15/18 on the first run.** All three survivors were real, and **two were SOURCE
gates that passed under the mutant**:

* Neutering `if (closeResolution.Refused)` to `if (false)` left the `ResolveOrRefuse` call in place,
  and the gate asserting the resolver is *called* still passed. ⚠️ **A gate that a value is COMPUTED
  is not a gate that it is USED** — `P2-24`'s class ("dead safety machinery is invisible") reaching
  the gates themselves. Every "is X called" assertion in that file deserves the same question.
* Replacing the settle poll's exit condition with a bare `break` left a single immediate read, so
  **every healthy close would report `close_submitted_not_confirmed`** — *an alarm that is always on
  is off*, now the **eighth** instance in this project.
* Dropping the empty-root guard leaves `string.Equals("", "")`, so **two unknowns read as a match**.

⚠️ **And a test disagreed with the class in the same commit, and the test won.** `WantsEverySymbol`
was written as `IsNullOrWhiteSpace → true` on the reasoning that the handler defaults an absent
symbol anyway. The handler defaults on `IsNullOrEmpty`, so `{"symbol": "   "}` — a template that
interpolated an empty variable — would have reached the filter as three spaces and been read as a
request to **close every position on the account**. The wildcard is now one exact token.

Related: `P0-104` (the same unobserved-outcome report, with worse consequences), `P1-100` (the second
reader), `F-9` (derive what you display from what actually happened), `P1-70`.

---

### P2-109. `nt_orders`' `account` parameter is ignored — a read answers about an account you did not name — CLOSED 2026-08-14 (session 41), live-validated

**Where**: the bridge's orders route / `mcp/lib/tools.js`. Found while confirming `P1-105`'s cleanup.

Measured on the live box 2026-08-14 20:10Z, two calls one after the other:

```
nt_orders(account="Sim101", limit=8)  -> [ { account: "TAKEPROFITPRO524207503", symbol: "MYM SEP26", ... } ]
nt_orders(limit=6)                    -> [ { account: "TAKEPROFITPRO524207503", symbol: "MYM SEP26", ... } ]
```

**Byte-identical.** The filter is not narrowing anything, and the one order returned is on a
**funded TakeProfit account** — not the account the caller named. Sim101 genuinely had no working
orders at that moment, so the honest answer was `[]`.

This is `P1-90`'s family on a **read** path, which that entry's own header calls out: *"for a write
that means acting on the wrong account; for a read it means answering confidently about someone
else's."* It is also `P1-72`'s shape — a parameter that is advertised and does nothing — and the
remedy there was to pin the surface to the addon's own behaviour rather than re-reviewing it.

⚠️ **Consequence beyond the wrong answer**: an agent asking "does Sim101 have working orders?" before
flattening, or after, gets an answer about a funded account. Both `P1-105` and `P0-104` were
diagnosed partly by reading order state.

#### It was not one ignored parameter — it was all THREE, and the failure is in a JOIN

`nt_orders` advertises `account`, `limit` and `offset`, and implemented **none** of them. Every
layer was individually correct:

* `mcp/lib/tools.js` advertises all three;
* `mcp/nt-mcp-server.js` builds the query string and **sends** all three;
* `GetOrders()` was a clean, correct read of every account's orders;
* and the line joining them was `case "/api/orders": return GetOrders();` — **taking nothing**,
  sitting between two routes that were already passing `query[...]`.

**Nothing you could review in isolation was wrong.** The contract between the halves was simply
never connected — which is the argument for the two halves living in one repo, restated: a
contract with its two sides in two commits cannot be reviewed as one thing. The description even
promised "cursor pagination", so an agent paging with `offset` re-read page one forever.

#### The fix

* `case "/api/orders": return GetOrders(query["account"], query["limit"], query["offset"]);`
* **`BridgeAccountScope`** (new) is now the ONE definition of "this request is about account X".
  `BridgeClosePlan.MatchesAccount` delegates to it — the alternative was a second copy, which is
  how `P1-90` reached six sites and `P1-100` ended with three readers of one flag. ⚠️ The move
  broke two of `mutate_p1105.py`'s anchors; they were **repointed, not retired**.
* **`BridgeOrderQuery`** (new) parses and clamps. `limit=abc` gives the default rather than
  throwing — the `/api/bars` route on the next line still does `int.Parse(query["count"] ?? "100")`
  and throws `FormatException` on a caller typo, because absent and unparseable were treated as one
  input. `limit=0` clamps to 1 (an empty page and an empty book are indistinguishable to the
  reader, which *is* this defect); a negative offset is 0, never an index from the end.
* **`P1-90` on the read path**: a supplied name that does not resolve is now refused. Answering
  "no orders" about an account that does not exist reads as reassurance, and on a read path
  reassurance is the entire damage.
* ⚠️ The response stays a **bare array** deliberately. The wrapper returns `res.data` straight
  through and 43 wrapper tests plus every consumer expect a list; an envelope would be a silent
  breaking change to every reader in order to carry metadata nobody consumes yet. Counts go to the
  log; the envelope belongs with the wrapper change that would use it.

#### Live validation 2026-08-14 20:55Z — the market was CLOSED and it did not need to be open

The stale `Rejected` order on the funded account was sufficient, which is why this item was taken
ahead of `P1-102` on a Friday evening:

| call | before | after |
|---|---|---|
| `nt_orders(account="Sim101", limit=8)` | the **funded** account's order | **`[]`** |
| `nt_orders(limit=6)` | the same payload, byte-identical | the funded account's order |
| `nt_orders(account="Sim1O1")` | the same payload again | **refused**, naming the 96 accounts |
| `nt_orders(account="TAKEPROFITPRO524207503")` | — | the order (**positive control**) |
| `nt_orders(offset=1)` | — | `[]` — past the end, not wrapped |

⚠️ **The regression test is that the two answers DIFFER.** A "the filter returns a subset"
assertion **passes under the defect**, because every set is a subset of itself. And the positive
control is what proves the filter is a filter rather than an outage — *for a detector, the negative
test is the one that proves it works*, and a filter that returns nothing passes every "it excluded
the wrong account" test ever written.

#### What the battery caught, and it was the same lesson twice in one session

**11/12 on the first run.** The survivor: deleting the account resolution's `if (...Refused) return`
left the `ResolveOrRefuse` call in place, and the source gate — which asserted the resolver is
**called** — still passed.

⚠️ **That is the identical survivor `P1-105`'s battery produced hours earlier**, and I wrote the
identical incomplete gate at the next site. *A gate that a value is COMPUTED is not a gate that it
is USED*, learned at one call site and not carried to the next one written — this repo's own
second-reader pattern with the author as the second reader.

Fixed as a **sweep** rather than a third per-site assertion: `TestEveryResolverSiteACTSOnTheRefusal`
extracts every `x = BridgeAccountResolver.ResolveOrRefuse(...)` from the source and requires that
same `x` to be tested for `.Refused` **and returned on**. A ninth site is covered the moment it is
written, without anyone remembering the test exists.

⚠️ **And the exact-count gate from `§5.50` fired on its very first opportunity**: adding `GetOrders`
made a **seventh** resolver site an **eighth**, the `== 7` assertion failed, and the number was
raised deliberately. That is the speed bump working as designed, hours after `>= 6` was found
leaking.

Related: `P1-90` (the same guess, on write paths), `P1-72` (a parameter advertised and not
implemented), `P1-91` (the schema half of the same contract).

---

### P3-111. `/api/bars` throws an unhandled `FormatException` on a caller's query typo — ✅ CLOSED 2026-08-14 (session 42), live-validated in full. ⚠️ **REBAND: filed `P3`, it was a `P2`** — the entry below describes ONE of FOUR defects on the endpoint, and the one it names is the least serious

**What was filed is quoted verbatim below and was correct as far as it went.** Probing the
deployed box before writing any code (`measure-the-deployed-system`) found the endpoint broken at
**both ends of every parameter it takes**. Measured 2026-08-14:

| Request | Before | After |
|---|---|---|
| `count=abc` | **HTTP 500 + .NET stack trace** | 200, 100 bars |
| `periodValue=xyz` | **HTTP 500 + .NET stack trace** | 200, 100 bars |
| `period=Banana` | **HTTP 500 + .NET stack trace** | 200, a refusal **naming all 17 valid period types** |
| `count=5000` | 531,658 bytes | 531,720 bytes |
| `count=200000` | **21,285,727 bytes** | 531,720 bytes (5,000 bars) |
| `count=1000000` | **1,000,000 bars** | 531,720 bytes (5,000 bars) |
| `count=0` / `count=-5` | **0 bars** — reads as "this instrument has no data" | 1 bar |
| `offset=0` vs `offset=500` | **BYTE-IDENTICAL** | different windows; pages abut exactly |

⚠️ **THE PARSE CRASH WAS THE LEAST OF THEM, AND THE FILED ENTRY IS WHY THE BAND WAS WRONG.** A 500
carrying a stack trace is ugly and **loud** — the caller knows something failed. The unbounded
response and the ignored `offset` are **silent**, and `count=0` returning zero bars is worse than
either, because it is a well-formed answer that reads as *a fact about the market*. **Weigh the
quiet failure above the noisy one**; banding on "it's only a read, so it's a 500" missed three
defects that never raise anything.

⚠️ **`offset` WAS `P2-109` AT A SECOND ENDPOINT**, found by running that ticket's own test — two
calls differing only in the parameter, compared for **inequality** — against the next endpoint.
`/api/orders` advertised three parameters and implemented none; `/api/bars` advertised `offset`,
the wrapper faithfully sent it, and the route dropped it. Same shape, same repo, hours apart.

⚠️ **AND THE SIZE PROMISE WAS `P1-72`'s SHAPE**: the MCP tool schema advertised **"max 5,000 rows"
in two places** while the receiver enforced nothing. The cap is now **5,000 — the number the schema
already said** — because raising the code to meet an existing written promise beats rewording the
promise to match the code. **It is only honest because `offset` now works**: a bound on one
RESPONSE is a bound on memory, but a bound on what is KNOWABLE would just push callers back to
`/api/bars/export`. Mutant 7 attacks exactly that confusion — it caps the *request* too, which
looks like a tightening and silently makes every page past the first return the same bars.

⚠️ **BOTH READERS WERE FIXED, AND THE SECOND ONE WAS NEVER FILED.** `/api/bars/export` takes the
same `period` string and threw on the same typo — and **ten lines below it, `merge` has always used
`Enum.TryParse` with a fallback**. One method, two enum parameters from the same caller, and only
one of them was ever treated as hostile. Fourth instance of *a second reader that was never told*
after `P1-100`, `P2-98`/`P1-99` and `P1-105`. `Enum.Parse` is `int.Parse` for names.

⚠️ **THE WRAPPER'S `period` ENUM WAS REMOVED, NOT EXTENDED.** It hard-coded five names; the live
refusal proves NT8 has **seventeen** (`Tick, Volume, Range, Second, Minute, Day, Week, Month, Year,
HeikenAshi, Kagi, Renko, PointAndFigure, LineBreak, Volumetric, Delta, PriceOnVolume`). The schema
**forbade twelve values the addon serves happily** — a hand-typed enum disagreeing with the
receiver's real whitelist, which is `P1-72` verbatim. The addon now derives the set from
`Enum.GetNames(typeof(BarsPeriodType))` and its refusal lists it, so a second copy buys nothing.

**Three gates were caught by this ticket, all in the same session:**

* **`tests/BridgeTests.csproj` now GLOBS `addons/*.cs`** with one exclusion, where it had been a
  hand-typed list of eight. That is the drift surface `check_bridge_parses.py` stopped being hours
  earlier (2 of 6 files under a comment claiming all of them); adding two more by hand would have
  been the **third instance in one day**. The glob states `P2-27`'s rule mechanically: every addon
  source naming no NT8 type is EXECUTED, automatically, from the moment it exists.

* **`tools/check_anchors.py` was PORTED from `nt8-riskguard` after it was needed.** Moving the
  parse arithmetic into `BridgeQueryValue` broke **six** of `mutate_p2109.py`'s anchors and nothing
  noticed — they printed `[SKIP]`, scored as **survivors, 6/12**, and the only reason it surfaced
  is that the battery was re-run by hand. In this repo the identical edit fails in the commit.
  **Third per-repo gate found missing on the bridge side**, after `check_ci_runs_every_battery.py`
  and `check_expected_survivors.py`. The anchors were **repointed, not retired**, and the move made
  them stronger: one mutant to the shared clamp is now evidence about **both** endpoints.

* **A new test gate failed on its own first run** by reading only the FIRST `hasMore` assignment,
  which is the empty-window branch's constant `false`. *State the region a gate inspects* — fifth
  instance, and the cheapest one to date.

⚠️ **THE BATTERY'S ONE SURVIVOR WAS THE AUTHOR'S, AGAIN.** Mutant 1 was named "the route parses at
the seam" and passed `query["count"] ?? "100"` — still a **string**, still handed to the safe
parser, still correct. It never expressed the defect, so no test could kill it and **none was
missing**. The filed defect is now **unrepresentable**: `GetBars` takes no `int`, so `int.Parse` at
the route does not compile, and the test asserts that property directly. Second instance of
`P1-99`'s lesson — **a surviving mutant does not always mean a missing test**; there it was
unkillable by construction, here it was a mutant that did not restore what it was named after.
Replaced with the seam defect that IS still possible (the route discarding `offset`): **10/10**.

⚠️ **`hasMore` was very nearly shipped as `start > 0`**, caught while writing the return statement.
When NT8 returns exactly what was asked for, `start` is 0 and older history still exists — so an
agent would stop **one page early** believing it had read the whole series. Silent truncation, the
mirror of this ticket's silent widening. It compares `available >= requestSize` instead, and
mutant 8 pins it.

**Evidence**: harness **233 assertions / 46 tests → 302 / 56**; wrapper **51/0**; battery
`mutate_p3111.py` **10/10**; `mutate_p2109.py` **6/12 → 12/12** after repointing; anchors **64/0**;
**6** batteries wired; `check_bridge_parses.py` 11 files; `nt_compile` **errorCount 0**;
`deploy.py --verify` **20 files / 0 orphans**. Every row of the table above was re-driven against
the deployed box, plus positive controls (a valid export wrote **552 rows**) and the MCP tool path
end to end (`offset=0` → 16:58–17:00, `offset=3` → 16:55–16:57, contiguous).

**Files**: `addons/BridgeQueryValue.cs` (new), `addons/BridgeBarsQuery.cs` (new),
`addons/BridgeOrderQuery.cs` (delegates), `addons/McpBridgeAddOn.cs` (route, `GetBars`,
`ExportBars`), `mcp/lib/tools.js`, `mcp/nt-mcp-server.js`, `tests/BridgeSourceTests.cs`,
`tests/BridgeTests.csproj`, `tools/check_anchors.py` (ported), `mutation/mutate_p3111.py` (new),
`mutation/mutate_p2109.py` (repointed), `.github/workflows/ci.yml`.

---

<details>
<summary>The entry as originally filed, 2026-08-14 — kept because the reband is the lesson</summary>

### P3-111 (as filed). `/api/bars` throws an unhandled `FormatException` on a caller's query typo

**Where**: `McpBridgeAddOn.cs`, the route table, one line below `/api/orders`:

```csharp
case "/api/bars":
    return GetBars(query["symbol"], query["period"] ?? "Minute",
        int.Parse(query["periodValue"] ?? "1"), int.Parse(query["count"] ?? "100"));
```

The `?? "1"` handles the parameter being **absent**. Nothing handles it being **present and
unparseable**: `count=abc` reaches `int.Parse` and throws. **Absent and unparseable are different
inputs, and only one of them was considered.**

Noticed while writing `BridgeOrderQuery` for `P2-109`, which now does the same job for
`/api/orders` with `int.TryParse` and clamping. Filed rather than fixed in that commit: it is a
different endpoint, and a fix riding along in a commit whose subject is orders is a fix nobody
reviews. **The remedy is to reuse `BridgeOrderQuery.ParseLimit`'s shape, not to write a third
parser** — a query parameter is attacker-shaped by construction, being a string from outside.

⚠️ Not measured. `nt_bars` is a read, so the consequence is a 500 rather than an action, which is
why this is a `P3` — but it is reachable by a typo, and an exception page is not an answer.

Related: `P2-109` (the same query string, the same class), `P1-91` (schema defaults on the same
surface).

</details>

---

### P3-110. The panic flatten's cancel set omits `OrderState.TriggerPending` — OPEN, but NARROWED by live measurement 2026-08-14: the hazard AS FILED does not reproduce, and only a small remainder stands

**Where**: `McpBridgeAddOn.cs`, `ActiveOrderStates` (hoisted from `EmergencyFlatten`'s local
`activeStates` by `P1-105`).

The set is `Working, Submitted, Accepted, ChangePending, PartFilled`. NT8 also has
`TriggerPending` — where a stop or stop-limit order rests until its trigger price is touched, which
is the ordinary state of a protective stop.

**If that is right, `nt_emergency_flatten` leaves resting stops behind**, and a stop that survives a
flatten is an order that **OPENS a position** in the opposite direction when it triggers — precisely
the hazard `P1-106` refuses OCO and ATM orders for.

⚠️ **Filed rather than fixed, because the stub cannot answer it** — it omits 6 of 16 `OrderState`s
and has hidden a live `P0` behind a green suite. Widening what the panic path cancels is a behaviour
change on the most consequential path in the bridge, so it needed a real resting stop on a live feed.

#### MEASURED 2026-08-14 20:30–20:39Z on Sim101 — and the hypothesis is WRONG

Driven in the last fifteen minutes of the Friday session, which is why it was worth doing then: this
is the one open item that **could not** be answered offline.

| step | measured |
|---|---|
| long 2 MNQ, then `StopMarket` Sell 2 @ 30050 | order rests in **`Accepted`** — *not* `TriggerPending` |
| `nt_emergency_flatten` on Sim101 | `firstPassCancelled: 1`, `residualCancelled: 0`, `flattenOrdersSubmitted: 1`, `accountsStillOpen: []` |
| orders afterwards | **none on Sim101** — the protective stop was cancelled |
| separately, `StopLimit` Sell 1 @ stop 30050 / limit 30040 | also rests in **`Accepted`** |

**`Accepted` is already in `ActiveOrderStates`**, so both stop types are cancelled by the first pass
and the hazard as filed does not exist. **A stop does not sit in `TriggerPending` on this feed.**

**What remains open, and it is much smaller:** `TriggerPending` is still absent from the set, and two
paths were *not* driven — an **ATM / strategy-managed** stop, and whatever order shape actually
produces `TriggerPending` on this platform, which is still unidentified. Until someone names an order
that reaches that state, there is no evidence a real order is ever missed. **Do not "fix" this by
adding the state on the strength of the source reading alone** — that was the reasoning that produced
this entry, and it was wrong.

⚠️ **This is [[check-the-exemplar-belongs-to-the-class]] applied BEFORE the fix instead of after.**
The entry was written from reading `ActiveOrderStates` and reasoning about what `TriggerPending`
means. One live drive contradicted it. The filing discipline is what paid: had this been "smuggled
into an adjacent commit" as a one-word addition to a set, it would have shipped a change to the panic
path with no defect behind it, and nothing would ever have contradicted it.

#### Two other things this drive re-validated for free

* **`P0-104` holds live**: `residualCancelled: 0`. Before that fix the same shape measured
  `residualCancelled: 1` — the panic button cancelling **its own flatten order** — with the account
  still long 11 and `success: true`.
* **`P1-97` holds live**: a `sell` submitted on a **flat** account came back as `action: "SellShort"`,
  so the bridge is still resolving the direction from the position rather than echoing the caller's
  label.

---

---

### P2-103. The three read-only surfaces that answer "is the guard actually protecting me?" have NO MCP tool, and they are exactly the ones five mutation batteries exist to make honest — CLOSED 2026-08-14 (session 41), live-validated

**Where**: `nt8-mcp-bridge/mcp/lib/tools.js`. Measured 2026-08-14 by diffing the bridge's 67 routes
against the 52 `nt_` tools: **15 routes are unreachable**, and these are the ones that matter:

| route | returns | MCP tool |
|---|---|---|
| `/api/riskguard/inventory` | `BuildGuardSnapshot()` — the per-rule inventory: is this rule `Enforcing`, and what limit is it holding you to | **none** |
| `/api/copier/snapshot` | `TradeCopierEngine.GetSnapshot()` — per-relationship conformance, orphan positions, quarantine reasons | **none** |
| `/api/riskguard/version` | the version an operator reads to know what is deployed | **none** |
| `/api/riskguard/fsm-reset` | clears a stuck FSM entry | **none** |

**Why this is worth a defect ID rather than a feature request.** `UI1`, `UI3`, `UI4`, `UI5` and `UI6`
— **five of the 25 mutation batteries**, and the ones whose every mutant is deliberately written to
make the payload *more reassuring than the box* — exist to keep precisely these two snapshots honest.
`F-9` was a defect in the same surface. That is a large amount of machinery built to make an answer
truthful, and **the agent driving the system cannot read the answer.** The honesty was bought and is
not being spent.

It also has a direct operational cost, measured this session: establishing "what is actually running
and is it protecting anything" needed `interventions.jsonl` parsed by hand, `config.json` read off
disk, and a raw `curl`. `nt_riskguard_state` returns the FSM only; `nt_copier_config` returns
configuration and session metrics, **not** conformance.

#### Fixed 2026-08-14 (session 41), entirely in `nt8-mcp-bridge/mcp/`

`nt_riskguard_inventory` and `nt_copier_snapshot` added; `/api/riskguard/version` folded into
`nt_health`, which is where anyone looks for "what is deployed". All three are **read-only**, so
the `P1-91` schema risk does not arise — there is no field whose default a receiver could merge
into stored config. `fsm-reset` is a WRITE and was deliberately left out; it belongs with
`P1-102`'s review.

⚠️ **The payload was measured BEFORE the view was designed**, per `measure-the-deployed-system`:

```
/api/riskguard/inventory  ->  635,447 bytes   96 accounts   2,304 rule rows
/api/copier/snapshot      ->    1,216 bytes
```

**A passthrough tool would have spent the context window on one read.** So `nt_riskguard_inventory`
defaults to a summary: **635,447 bytes → 3,082 bytes**, measured through the real tool call. The
constraint is CONTEXT, not bandwidth — 635KB over localhost costs nothing — which is why the
summarising lives in the wrapper, after the fetch, rather than in the addon.

Three decisions inside it are the reusable part:

* **Every number is folded out of the same rule rows the `account` view returns.** A summary
  keeping its own counters would be free to disagree with the detail beneath it, which is `F-9`
  verbatim: the guard REPORTING one thing while DOING another. The tests recount from the fixture
  and require agreement rather than asserting hand-written totals.
* **`ConfiguredNotEvaluated` is collapsed by RULE, not listed per account.** The live box has
  **384** such rows — which are **four** distinct rules × 96 accounts. Listing them per account
  buries one finding under its own repetition; that is the `P2-41` shape, where a `PerAccount` rule
  reading a global collection reported evidence for all 96 accounts from one mapping.
* **A truncated list says it was truncated.** `enforcingCount` is always complete; the named list
  is capped and carries `enforcingTruncated`. A list that silently stops is how a reader concludes
  there are only two problems.

`P1-90` on the read path too: an account name that matches nothing is **refused** with the count and
a sample of real names, never answered about all 96 — which is exactly what `P2-109` was.

#### What it immediately revealed about the live box

The first summary is a better answer than the endpoint it came from:

| | |
|---|---|
| mode / armed | `shadow`, `isArmed: true` |
| `Enforcing` | **0** — correct and expected in shadow; alarming only in `live` |
| `EvaluatedNotEnforcing` | 1384 |
| **`ConfiguredNotEvaluated`** | **384** = 4 rules × 96 accounts: *Consistency / daily-profit cap*, *Consistency cap threshold*, *News events file*, *Prop suite armed* |
| `Inert` / `Disabled` | 288 / 248 |

Those four are `P1-77`'s deferred set, and the guard's own `unevaluatedRules` notes say so in
words (*"NO CODE READS THIS"*). **The tool now surfaces in one call what previously required
parsing `interventions.jsonl` by hand, reading `config.json` off disk, and a raw `curl`** — which
is the operational cost this entry was filed on.

#### Live validation 2026-08-14 21:06Z — the MCP server driven over stdio

Not asserted from source: the server was spawned and sent real `tools/list` and `tools/call`
JSON-RPC, against the running bridge. `tools/list` advertised **54** tools including both new
names; the summary returned the table above; `account: "Sim101"` returned its 24 rule rows;
`account: "Sim1O1"` was **refused** naming 96 accounts with a sample; `nt_copier_snapshot`
filtered to `Sim-ORB` — a **follower** — matched its relationship, proving the filter reads either
side; `account: "Nope"` returned `matchedRows: 0`; and `nt_health.riskguard` read
`{"version":"1.23.0","loaded":true,"mode":"shadow","isArmed":true,"guarding":true}`.

⚠️ **The tools only appear in THIS session's MCP client after it restarts** — schemas are read at
startup (`P1-91`'s note). The stdio drive above is what proves they work without waiting for that.

⚠️ **A third exact-count gate fired**, `TOOLS.length` 52 → 54, and was bumped deliberately with the
reason recorded. Wrapper tests **43 → 51**.

⚠️ **`P1-72`'s trap was avoided by construction**: neither tool widens an existing `action` enum,
so there is no enum to drift from the addon's whitelist.

---

## 2. P1 — Concurrency and invariant violations

### P1-10. The safety sweep holds `_stateLock` across broker calls — CLOSED 2026-08-07
**Where**: `RiskGuardAddOn.cs:1336-1446` — the `lock (_stateLock)` block contains
`account.Cancel` (1413), `account.Flatten` (1423), `account.Submit` (1429) and
`ProcessAction(...)` (1439), which itself calls `ExecuteAction` → `Flatten`/`Cancel`/`Submit`.
**Why it matters**: [RiskGuardAddOn.md](RiskGuardAddOn.md) §5 and §6.7 both state the invariant
"deadlocks are avoided by yielding the lock before calling NinjaTrader's `Flatten` or `Cancel`".
The event paths honour it correctly (`ExecutePositionUpdateDetails:905-913` collects actions under
lock and processes them after release). The sweep does not. Because the sweep runs on the WPF
dispatcher via `InvokeAsync` (`1320`), any NT8 internal path that blocks on a background thread
which in turn needs `_stateLock` deadlocks the UI thread — and with it the guard.
**Fix**: restructure the sweep to the same collect-then-execute shape as the event handlers.
Nothing inside `lock` may call into `Account`.

> **How the lock-scope invariant is enforced now (2026-08-07).** The stub account reports every
> `Cancel`/`Flatten`/`CreateOrder`/`Submit` to `Account.BrokerCallObserver`, and the addon exposes
> `TestIsStateLockHeld()` (`Monitor.IsEntered`). `TestP1_10_...` and `TestP1_35_...` therefore assert
> the invariant directly instead of relying on someone spotting a broker call three frames deep
> inside a lock block. Any new violation anywhere on those paths fails the suite.
>
> `DrainPendingCancels()` **throws in the TESTING build if called with `_stateLock` held.** The
> tempting wrong fix here is a nested `lock (_stateLock)` around the cancel — it is re-entrant, so
> it changes nothing and merely hides the violation. The guard makes that mistake loud.

### P1-11. Lockout sweep cancels protective stops and reducing orders — CLOSED 2026-08-07
**Where**: `RiskGuardAddOn.cs:1410-1414`
```csharp
var toCancel = account.Orders.Where(o => o.OrderState != OrderState.Filled
                                      && o.OrderState != OrderState.Cancelled).ToList();
account.Cancel(toCancel);
```
This cancels **everything non-terminal** — including the protective stop covering the position it
is about to flatten, and including position-reducing orders that §6.10 of the design doc
explicitly promises to preserve (`IsPositionReducingOrder` is honoured in `OnOrderUpdate` but not
here). If the subsequent `Flatten` fails (the code catches and falls back to a market order,
which can also fail), the account is left with a position and **no stop**.
**Fix**: order of operations — (a) cancel only *entry / risk-increasing* working orders, (b)
flatten, (c) cancel the remainder after confirming flat. Reuse `RiskGuardOrderUtils.IsPositionReducingOrder`
and `IsProtectiveSide`. Add an attempt counter with escalation to a loud alert after N cycles
instead of silent infinite retry (REAPER's `_reaperFlattenInFlight` + grace pattern).

### P1-12. Blocking file I/O under the global lock — CLOSED 2026-08-07
**Where**: heartbeat `File.WriteAllText` (`1342`), log `File.AppendAllLines` (`1351`),
`SavePersistedState()` (`1395`) — all inside `lock (_stateLock)`; plus
`SavePersistedState()` called **synchronously on every position change** at `865`.
**Why it matters**: `_stateLock` is the same lock every NT8 event handler needs. A slow disk
stalls order-event processing. The `_stateDirty` batching mechanism already exists and is used by
the sweep — line 865 bypasses it.
**Fix**: replace line 865 with `_stateDirty = true`. Move all file writes outside the lock;
consider a dedicated writer thread draining `_logQueue`.

**Fixed 2026-08-07 (session 8).** `SavePersistedState` was split into `CapturePersistedState`
(builds the payload under the lock, no I/O) and `WritePersistedState` (serialise + write, lock
released) — the old method took the lock *itself*, so no caller could opt out. The sweep captures
its heartbeat stamp, log batch and state payload under the lock and writes all three in a
`finally` at the bottom, **after** the broker work: nothing about a heartbeat file is worth
delaying a flatten for, and a `finally` means log lines already drained out of the queue are not
lost if a rule throws. The position-change site sets `_stateDirty`. `ToggleArmed` and
`UnlockAccount` capture inside, write outside — neither was a latency problem alone, but both had
to move before the invariant could be enforced for anyone, because `_stateLock` is re-entrant.

Machine-checked by `FileWriteObserver` + `TestIsStateLockHeld()`, the same probe `P1-10` got. A
second test pins the batching itself, because a "fix" that merely deleted the write would pass the
lock-scope check while silently dropping persistence.

> **Scoped out deliberately**: `SaveAndReloadConfig`/`LoadConfig` still do their I/O under the
> lock. The write-then-read-back has to stay atomic with the `_config` swap, so moving it is a
> separate change with its own failure mode, and it is a rare user-initiated path rather than an
> event path.

### P1-13. Guard evaluation runs on the WPF dispatcher — HALF CLOSED 2026-08-07
**Where**: `OnSafetySweep:1317-1323`, `UpdateFsmOnPosition:1599-1604`, `SeedFsms…:501-507`
**Why it matters**: safety-critical latency is coupled to UI responsiveness. V12 does the
inverse — REAPER audits on a background thread and marshals *only* the order-submitting calls to
the strategy thread via `TriggerCustomEvent`.
**Fix**: evaluate on the timer's own thread; marshal only `Account.Flatten/Cancel/Submit` to the
dispatcher. This also removes the "no dispatcher → silently return" failure mode at `1318`,
where the entire sweep is skipped if `Application.Current` is null.

**The fail-open half is CLOSED (2026-08-07, session 8), and it was the worse half.** Five handlers
plus the entire sweep opened with `if (dispatcher == null) return;`, so with `Application.Current`
null — early startup, or a headless NT8 — the guard received every position, order, execution and
account-item event and **discarded all of them**: no FSM, no grace timer, no rule evaluation, no
heartbeat, no session reset, no lockout enforcement, no watchdog, no log line, and
`/api/riskguard/version` still reporting armed and guarding. All six now route through one
`RunGuardWork` seam that runs the work **inline** when there is no dispatcher.
`OnGraceTimerCallback` already had exactly that fallback and was the only one of the six that did.

Asserted against source text, because the branch lives under `#if !TESTING` and cannot be executed
by the suite at all — the `P1-47` shape. Comments are stripped first so the seam can quote the
defective pattern in its own documentation.

**STILL OPEN — the threading inversion.** Evaluating on the caller's thread and marshalling only
broker calls is the latency fix. The evidence says it is safe (the copier has been submitting real
follower orders straight off NT8's account-event thread, with no marshalling, in production). But
it turns six handlers the dispatcher was implicitly serialising into genuinely concurrent ones, and
**the S-series does not cover that**: `S4` is lock-scope, `S7` is copier fan-out, and
`S5`/`S6`/`S8`/`S9` are sequential scenario tests. A genuine concurrent-guard-event stress test is
a prerequisite, not an optional extra.

### P1-14. `_pendingStops` is single-slot, unbounded in lifetime, and side-blind — CLOSED 2026-08-07
**Where**: `UpdateFsmOnOrder:1651-1658`, consumed at `UpdateFsmOnPosition:1577-1587`
- `_pendingStops[key] = order` keeps **one** order per (account, instrument) — a bracket with
  multiple stop legs, or a second stop arriving first, overwrites the first.
- Entries are only removed on consumption or on flat. A buffered stop for a position that never
  materialises (entry rejected) leaks and can be consumed by a *later, unrelated* position on the
  same instrument.
- The comment admits the side is unknown at buffer time, so a **stop-market entry order** (a
  breakout entry, exactly what V12's OR mode submits) is buffered as a candidate protective stop.
**Fix**: `Dictionary<string, List<Order>>` with a TTL (e.g. `StopAttachSeconds × 2`), swept in the
watchdog; classify by side on consumption only, and require `order.Quantity <= positionQuantity`.

**Fixed 2026-08-07 (session 8)**, exactly as prescribed. `List<BufferedStop>` with a UTC stamp;
re-buffering the same `Order` object refreshes the stamp rather than duplicating (NT8 raises
`OrderUpdate` repeatedly for one order). Expired in the watchdog after **two** grace periods, not
one — one grace period is the longest a legitimate stop can lag its position event and still be the
thing protecting it, so expiring at one would break the race the buffer exists for. The test
asserts both edges. Terminal orders are dropped at any age.

The side-blind half is the one with teeth: a 10-lot sell-stop **breakout entry** buffered while
flat, followed by a 1-lot long opened by hand, produced `State = Protected` with
`CoveredQuantity = 10` on a 1-lot position — grace cancelled, auto-stop suppressed, and the account
left **9 lots short** if that order ever triggered. A sell-stop entry passes the side test by pure
coincidence. Consumption now also requires `Quantity <= positionQuantity`.

> Not changed: the live (non-buffered) recognition path still accepts an oversized stop as full
> coverage. That is the trader's own working order against a live position rather than an unrelated
> resting one.

### P1-15. Re-arming does not seed FSMs for open positions — CLOSED 2026-08-07
**Where**: `ToggleArmed:2231-2249`; `SeedFsmsForExistingPositions` is only called from
`SubscribeToAccount`
**What happens**: `UpdateFsmOnPosition`/`UpdateFsmOnOrder` return early when `!_isArmed`
(`1547`, `1645`). Disarm → open a position → re-arm, and there is no FSM, no grace timer, and no
protection until the position changes side.
**Fix**: call `SeedFsmsForExistingPositions` for every subscribed account inside `ToggleArmed`
when transitioning to armed. Same on `SaveAndReloadConfig`/`ReloadConfig` if
`ExcludedAccounts` shrank.

### P1-35. FSM teardown cancels the orphan auto-stop while the caller holds `_stateLock` — CLOSED 2026-08-07
*(found during T1 implementation, 2026-08-06 — a P1-10 site this review originally missed)*
**Where**: `RiskGuardAddOn.cs:1620` inside `UpdateFsmOnPosition`'s nonflat→flat branch:
`try { account.Cancel(new[] { fsm.AutoStopOrder }); }`
**What happens**: `UpdateFsmOnPosition` is only ever called with `_stateLock` held — from
`ExecutePositionUpdateDetails:880` and from `TestFsmOnPosition`. So the orphan-auto-stop
cancellation is a broker call under the global lock, exactly the invariant §5/§6.7 of the design
doc claims is never violated. P1-10 catalogued the sweep as the only offender; this is a second,
independent site on the hot event path.
**Fix**: fold into P1-10's collect-then-execute restructuring — queue the orphan order on a
pending-cancel list and drain it in `ExecutePositionUpdateDetails` after the lock is released,
alongside the existing `ProcessAction` loop. Do not add a separate drain mechanism.

### P1-36. Coverage tracking follows a single stop order, so two partial stops read as under-covered — CLOSED 2026-08-07
*(found during T1 review, 2026-08-06)*
**Where**: `PositionGuardFsm.RecognizedStopOrder` / the new `CoveredQuantity` (T1)
**What happens**: the FSM tracks exactly one protective stop. A trader covering a 6-lot position
with two working 3-lot stops leaves `CoveredQuantity = 3`, so the under-coverage rule introduced by
T1 fires and attaches a 3-lot auto-stop — total protective quantity 9 on a 6-lot position, which
flips the position when the stops trigger. T1 deliberately scopes this out (it clamps the emitted
action to the uncovered delta computed from one stop), so the defect is narrowed but not closed.
**Fix**: aggregate coverage across all non-terminal protective-side stop orders for the
`(account, instrument)` pair rather than tracking a single `Order` reference — i.e. replace
`RecognizedStopOrder` with a small list, and compute `CoveredQuantity` as the sum. This is the
same computation the P3-30 reconciler needs, so build it once and share it.

**Fixed 2026-08-07 (session 8).** `CoveredQuantity` and `RecognizedStopOrder` are now **derived**
from a list on the FSM and are **read-only**. That is deliberate: the old pair had to be assigned
together at nine separate sites and nothing stopped them drifting apart. Making them read-only
turned "find every writer" into a compile error — which is how the second half below was found.
`AddRecognizedStop` is idempotent by object reference; reads prune terminal orders first; losing
one leg of two drops that leg and re-arms grace for the delta only; seeding no longer `break`s on
the first stop it finds.

> **The defect lived in a second place, and closing only the first would have changed nothing.**
> `ExecuteAction` re-sized the auto-stop from the **live position**, ignoring existing cover. T2
> established that sizing must come from the live position rather than the emission snapshot and
> that is still right — but "the live position" is the wrong figure when the trader already has
> stops working. `EvaluateGraceExpiry` sized its *action* to the uncovered delta and
> `ExecuteAction` re-sized it back up to the full position, undoing it. Now
> `liveQuantity - alreadyCovered`. When that delta is `<= 0` the action aborts **and clears
> `GraceEmitted`** — dropping an action without clearing it is the T1/T2 trap that leaves a
> position permanently naked.

**The settled decision was retired in both places** (handover **§7** — renumbered from §5 on
2026-08-13 — and the loop profile, now `agent/nt8_riskguard.py`), per the rule there: left standing
it would instruct the review panel to approve reintroducing this.

### P1-37. The `MinShadowSessions` arming gate counts addon restarts, not sessions — CLOSED 2026-08-07
*(found during the Phase A shadow deployment, 2026-08-07 — observed live, then confirmed in code)*
**Where**: `RiskGuardAddOn.cs:1510` (the increment) against `RiskGuardAddOn.cs:211` (the date
marker) and `RiskGuardAddOn.cs:609` (the rehydrate).
**What happens**: the counter `_shadowSessionsCompleted` **is** persisted and rehydrated across
restarts, but the date marker that debounces it, `_lastShadowSessionDate`, is **not** — it is a
plain field initialised to `DateTime.MinValue.Date` on every construction, and there is no
`LastShadowSessionDate` key in `PersistedStateData`. So the guard `_lastShadowSessionDate !=
currentSessionDate` is true after *every* addon reload, and the counter increments again on the
same calendar day.

This is not theoretical. During the Phase A deployment the addon reloaded repeatedly (ordinary
NinjaScript recompile churn from `nt_compile` and `nt_script_execute`), and
`ShadowSessionsCompleted` went **0 → 3 in about four minutes**, on a single day, with no market
data connected and not one position taken. `MinShadowSessions=3` was satisfied outright. The
FR-29 soft gate at `RiskGuardAddOn.cs:2454-2460` — the check that is supposed to stand between
shadow mode and live arming — will now pass on this machine.

Severity is P1 rather than P0 because it cannot itself place or miss an order; it removes a
safety interlock. Note the asymmetry with FR-30/31 directly above it at line 604: that code is
careful never to rehydrate `_isArmed`, precisely so a restart cannot silently re-arm. The same
reasoning was not applied to the gate that authorises arming.

**Fix**: persist `_lastShadowSessionDate` in `PersistedStateData` alongside
`ShadowSessionsCompleted` and rehydrate it in the same block, so the pair moves together. A
restart then re-reads today's date and does not re-count. Consider also requiring a session to
have *seen activity* before it counts at all — a shadow day with no connected feed teaches
nothing, and counting it is the same error in a milder form.
**Test**: two constructions on the same simulated date increment the counter exactly once;
constructions on two different dates increment it twice.
**Fixed by**: persisting `LastShadowSessionDate` in `PersistedStateData` and rehydrating it in
the same block as the counter, so the pair travels together. Verified in production — the live
counter held steady across a recompile that would previously have bumped it.

**Operational step — ✅ DONE 2026-08-07 (session 7).** The live `state.json` had read
`ShadowSessionsCompleted = 5`, inflated by restarts before the fix landed. It no longer climbed,
but the historical value was wrong and `MinShadowSessions=3` read as satisfied. Now `0`, with
`LastShadowSessionDate` at `DateTime.MinValue`; backup `state.json.bak_20260807_095249`. All 93
`AccountsData` entries and the empty `LockedOutAccounts` list verified unchanged after the write.

```powershell
# NT8 must be CLOSED - shutdown flushes in-memory state and would overwrite the edit
$p = Join-Path $env:USERPROFILE 'Documents/NinjaTrader 8/RiskGuard/state.json'
$j = Get-Content $p -Raw | ConvertFrom-Json
$j.ShadowSessionsCompleted = 0
$j.LastShadowSessionDate = '0001-01-01T00:00:00'
$j | ConvertTo-Json -Depth 20 | Out-File $p -Encoding utf8
```

Do not edit it while NT8 is running: the addon rewrites the file on flush, and a torn write
loses persisted lockouts.

> **`LastShadowSessionDate` must be `'0001-01-01T00:00:00'`, never `null`.** It is a non-nullable
> `DateTime` (`:4525`). Json.NET throws converting `null` to it, `LoadPersistedState` catches that
> and logs `Failed to load persisted state`, and **the whole persisted state is discarded** —
> every account's PnL baseline and the locked-out list included. The command above is correct; a
> `null` variant that had crept into the handover was caught by checking the field's C# type
> before running it.
>
> **"NT8 closed" means "the AddOn is not loaded".** The reliable check is that the bridge does not
> answer on `localhost:7890` — the listener starts at `State.Configure`. NT8 can sit at its login
> dialog with the process running and no AddOn loaded; that is when this reset was performed.

**Verify after the next successful login**: `GET /api/riskguard/state` (or the dashboard) should
report `ShadowSessionsCompleted` climbing to exactly **1** after one genuine shadow session, not
jumping on recompiles.

### P1-39. Every config load appends the default windows, so `WindowsET` grows without bound and a default can never be deleted — CLOSED 2026-08-07
*(found on 2026-08-07 while excluding an account ahead of Phase A validation — observed live,
then confirmed in code)*
**Where**: `RiskGuardAddOn.cs:4251` (the initializer) against `RiskGuardAddOn.cs:599`
(`LoadConfig`) and `McpBridgeAddOn.cs:5126` (`req.ToObject<RiskConfig>()`).
**What happens**: `WindowsET` is a `List<WindowConfig>` property pre-populated by a collection
initializer with `NY_AM_Macro` and `NY_PM_Macro`. Json.NET's default
`ObjectCreationHandling.Auto` **reuses** an already-populated collection and *appends* to it
rather than replacing it. So every deserialization adds the two defaults on top of whatever the
file holds — and `WindowConfig.Days` has the same shape, so each window's day list grows by five
entries at the same time.

Observed live. A single POST to `/api/riskguard/config` took the config from 6 windows to 10,
because that path deserializes **twice**: once in `ToObject<RiskConfig>()` (6 → 8) and again in
the `LoadConfig()` inside `SaveAndReloadConfig` (8 → 10). `Days` went 5 → 10 → 15 → 20 on the
affected windows. A plain addon restart costs one round, not two — and the deployment record in
the handover notes 24 restarts in four minutes of ordinary recompile churn.

Two consequences, and the second is the safety-relevant one:
- **Unbounded growth.** The file is rewritten each time, so the corruption is persisted and
  compounds. The `Days` lists were already doubled before this session touched anything.
- **A default window can never be removed.** Delete `NY_AM_Macro` from `config.json` and it is
  back on the next load. `EnableWindowGate` is `true` on this machine, and the gate
  (`:2560`) flattens positions opened *outside* the permitted set — so the failure direction is
  that the permitted set silently **widens** and the operator cannot narrow it. That is the same
  class as P1-20 and P1-37: a safety gate that quietly stops gating.

Duplicate entries are otherwise behaviour-neutral, because `Days` is parsed into a
`HashSet<DayOfWeek>` (`:619`) and the window test is a union.

**Fix**: annotate each `List` property with
`[JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]`.

> **The settings-level fix this entry originally recommended is wrong — do not apply it.**
> Setting `ObjectCreationHandling.Replace` in `JsonSerializerSettings` also replaces the
> *dictionaries*, and `InstrumentLimits`, `AccountFirmMap` and `FirmProfiles` are constructed
> with `StringComparer.OrdinalIgnoreCase` (`:4242`, `:4278`, `:4279`). Json.NET would discard
> those instances and hand back fresh `Dictionary` objects using the **default** comparer,
> silently turning case-insensitive instrument and firm lookups case-sensitive — a quiet
> correctness regression traded for a cosmetic one. Those three are empty-initialized, so
> appending to them is already correct and they need no fix. A test now pins this
> (`InstrumentLimits must stay case-insensitive after deserialization`).
**Test**: deserialize a config whose `WindowsET` holds exactly the two default windows and assert
the result has two, not four; round-trip it twice and assert the count is stable. Assert a config
that omits `NY_AM_Macro` still omits it after a load.
**Not introduced by this branch** — the initializer dates to `a19c2adc`, well before the
hardening work.

**Fixed by**: `ObjectCreationHandling.Replace` on `Profiles`, `ExcludedAccounts`,
`LockoutBypassWhileDisarmedAccounts`, `BlockedInstruments`, `WindowsET` and `WindowConfig.Days`.
The bridge's `ToObject<RiskConfig>()` is fixed by the same attributes; no bridge change was
needed. Test-first: red at baseline (421 passed / **6 failed**, reproducing 2 → 4 on a single
load and 8 after round-trips), green after (**427 / 0**), red again when the two attributes are
reverted. **Verified in production**: the live config now reports 6 windows from a 6-window file,
where the same file previously loaded as 8.

The on-disk `config.json` was repaired by hand before the fix landed (deduplicated to 6 windows;
backups at `config.json.bak_prerepair`, `config.json.bak_prearm_20260807_061407`).

> **Still true, and a *separate* hazard: `POST /api/riskguard/config` does not merge.**
> `req.ToObject<RiskConfig>()` (`McpBridgeAddOn.cs:5126`) deserializes the body into a whole
> `RiskConfig`, so any field the body omits comes back as its **default** and is then written to
> disk by `SaveAndReloadConfig`. Always GET the full document, mutate one key, and POST the whole
> thing back — then diff every key. Tracked separately as `P2-41`.

---

## 3. P1 — Rule semantics

### P1-16. `ConsecutiveLosses` over-counts on partial exits — CLOSED 2026-08-07
**Where**: `RiskGuardAddOn.cs:1008-1014` — every negative delta in `RealizedProfitLoss`
increments the counter.
One trade closed in three partials at a loss = **3 consecutive losses**. §6.9 of the design doc
introduced flat-transition debouncing for `TradesToday` but not for this counter, so the two
disagree about what a "trade" is.
**Fix**: attribute realized-PnL deltas to the trade lifecycle already tracked by
`PositionState.LastFlatTransition`; evaluate win/loss once per flat transition.
**Fixed by**: banking deltas in `AccountState.OpenTradeRealizedDelta` while a position is open
and judging the total once in `SettleClosedTrade` at the flat transition (and on flips).

> **The obvious version of this fix drops losses.** It assumes the closing execution's realized
> PnL always arrives before the position-flat update. That ordering is *not* established — the
> live log happens to show it, but nothing guarantees it, and if PnL lags then settlement runs on
> a zero total and the real loss lands on the next trade. So late fills **revise** the
> settlement: the streak as it stood before the trade was judged is retained until the *next
> entry*, and re-judging from that snapshot is exact for any number of late fills, correctly
> flipping a settled win to a loss or back. Tested in both directions.
>
> A realized delta with **no tracked trade** (the guard never saw the position, or a standalone
> adjustment) is still judged on its own. Four pre-existing tests cover this; despite their names
> they never open a position, so they assert exactly this and not an ordering. Ignoring untracked
> realized losses would make the lockout less sensitive than before the fix.

**Test**: one trade exited in three partials is one consecutive loss, not three; three separate
losing trades are still three; a trade that nets positive resets the streak despite a losing
partial; a late fill that flips the net result revises the streak in either direction.

### P1-17. Evaluation profit target is fed session-scoped PnL — CLOSED 2026-08-07
**Where**: `RiskGuardAddOn.cs:1139` passes `stateModel.RealizedPnL`, which is
`raw - SessionStartRealizedPnL` (`1006`) and reset daily (`1376`).
`EvaluationTargetProfit` ($3,000 default) is a **cumulative** prop-firm evaluation target.
**Fix**: track `CumulativeRealizedPnL` in `PersistedStateData` (survives restarts) and feed that;
keep the session value for the daily-loss rule.
**Fixed by**: `AccountState.CumulativeRealizedPnL` (banked completed sessions) plus
`TotalRealizedPnL` (banked + current session), fed to `EvaluateProfitTargetLock`, persisted in
`AccountPersistedData` and rehydrated on load.

> Accumulated **once per session reset**, not per realized-PnL delta. A delta-based running total
> is permanently corrupted by a single spurious tick — the broker rebasing its own realized
> counter before our session reset runs would do it — and unlike the session value, a cumulative
> total is never rebased, so the corruption would never wash out.

**Test**: $1,500 banked plus $1,600 today reaches a $3,000 target while today alone does not; a
single $3,200 session still fires; prior losses offset rather than being ignored; and the total
survives a save/load round-trip, because a cumulative target that resets on recompile is not
cumulative.

### P1-18. Two overlapping trailing-drawdown implementations — CLOSED 2026-08-07
`EvaluatePnLRules` enforces `profile.TrailingDrawdown` against a **session-reset** `PeakEquity`
(`1101-1118`, reset to 0 at `1370`), while `EvaluateFirmMirror` (`2688`) implements the firm's
real trailing-DD model with `FirmTrailingDDConfig`. For Apex-style accounts the high-water mark
does **not** reset daily, so the first rule is either redundant or wrong depending on config.
**Fix**: make `FirmMirror` authoritative when a firm trailing rule is actually in effect for the
account; skip the profile-level rule only then.

> **The original wording of this fix — "skip whenever `FirmMirror.Enabled`" — is retired because
> it removes protection.** On the live config `FirmMirror.Enabled` is `true` while its
> `TrailingDD.Enabled` is `false` and no account is mapped, so it would have skipped the profile
> rule while the firm rule evaluated nothing, leaving *no* trailing-drawdown cover at all.
> Precedence keys on the account's **effective** firm config (P1-42's `ResolveEffectiveFirmConfig`),
> so it follows a mapped per-firm profile while leaving unmapped accounts on the same config
> covered. A test pins the enabled-but-inert shape.

**Fixed by**: `firmTrailingInEffect` in `EvaluatePnLRules`. The peak is still tracked while
suppressed, so the value stays meaningful if the firm rule is later disabled.
**Test**: red at baseline (451 / 2), green after (453 / 0), red again when the guard is reverted.

### P1-19. Actions are neither deduplicated nor instrument-scoped — CLOSED 2026-08-07
- A single `EvaluatePnLRules` pass can append `DAILY_LOSS_BREACH`, `TRAILING_DD_BREACH`,
  `NEWS_SHIELD_LOCKOUT`, `EVALUATION_TARGET_REACHED` and `PEAK_GIVEBACK_BREACH` — five
  `FlattenPosition` actions, each of which independently walks all positions and calls
  `account.Flatten` (`2450-2483`).
- `ExecuteAction`'s `FlattenPosition` **ignores `action.Instrument`** and flattens every
  instrument on the account, including instruments that only have working orders (`2460-2469`).
  A missing stop on MES therefore flattens MNQ too.
**Fix**: coalesce actions by `(AccountName, ActionType, Instrument)` before processing; honour
`action.Instrument` when set and only fall back to account-wide for lockout/panic rules.
**Fixed by**: a `scoped` filter in `ExecuteAction`'s `FlattenPosition`, and `CoalesceActions`
applied at all four processing loops. An account-wide flatten supersedes scoped ones for the same
account, since the wide call closes those instruments anyway.

> **Dedup must not erase the audit trail.** `EvaluatePnLRules` logs no breach event of its own —
> the `GuardAction` *is* the record — so merging five actions would have silently discarded the
> fact that four other rules fired. The survivor keeps its own `RuleId` (callers and tests match
> on it) and carries the rest in `MergedRuleIds`, which the action's audit line now names.

**Test**: red at baseline (455 / 4, the scope failure reading `got [MNQ,MES]`), green after
(459 / 0), red again when scoping and coalescing are reverted. The stub now records which
instruments each `Flatten` call was asked to close, because the defect is in what `ExecuteAction`
*requests*.

### P1-40. The peak-giveback rule has no floor on the peak, so one tick of noise trips a flatten — CLOSED 2026-08-07
*(found 2026-08-07 by the first live armed shadow session — observed, then confirmed in code)*
**Where**: `PropFirmProtectionSuite.cs:110-113`, reached from `RiskGuardAddOn.cs:1325`.
**What happens**: the rule is purely *proportional*. The only floor on the peak is
`peakOpenGain <= 0`:

```csharp
if (... || peakOpenGain <= 0 || currentUnrealized >= peakOpenGain) return false;
double givebackPct = (peakOpenGain - currentUnrealized) / peakOpenGain;
return givebackPct >= cfg.MaxPeakGivebackPct;   // 0.30 live
```

One MNQ tick is 0.25 pt = **$0.50**. If a position ticks one tick into profit, `PeakOpenGain`
becomes `0.50`; the next tick back to breakeven gives `0.50 / 0.50 = 100% >= 30%` and the rule
fires. A *fraction* of a tick is enough — the breach threshold at a $0.50 peak is any value below
$0.35. So **essentially every position breaches within seconds of entry**, and the rule re-fires
each time the position worsens past the prior trigger (`RiskGuardAddOn.cs:1328-1335`).

Observed live on `SimCopyTest1`, 2026-08-07, armed + shadow, 1 MNQ:
entry 13:24:06.036 @ 29721.75 → **`PEAK_GIVEBACK_BREACH` at 13:24:08.78, 2.4 s later, with the
position at −$1.00 and never meaningfully profitable**. It fired **six times** in the 36 s the
position was open (13:24:08.78, :10.79, :18.90, :22.95, :39.08, :40.08). Total excursion of the
whole trade was a few dollars; it closed +$8.50.

**In `live` mode this flattens nearly every trade seconds after entry**, and because the action is
`FlattenPosition` it would realise the loss each time. This is a hard blocker for leaving shadow —
it is not a tuning issue, the rule is unusable at any percentage while the peak can be one tick.

Note the unit tests do not catch it: they exercise the rule with meaningful peaks (a $500-scale
peak against a 0.30 cap), where proportional-only logic behaves sensibly. The defect lives
entirely in the small-peak regime, which is *every real position for its first seconds*.

Note also that `PropFirmProtectionSuite`'s own `ArmedForLive: false` / `enforcing: false` does
**not** gate this: `RiskGuardAddOn` calls `EvaluatePeakEquityGiveback` as a pure predicate and
acts under its own arming. The suite's switch reads like an off-switch and is not one.

**Fix**: gate the rule on an absolute floor before the proportional test — a configurable
`MinPeakGainDollars` (and/or a floor expressed in ticks of the instrument), below which the peak
is not considered established. Consider also requiring the peak to have been held for a minimum
interval, so a single print cannot establish it. Whatever the floor, the rule must not be able to
arm off sub-tick noise.
**Test**: peak `$0.50`, current `$0.00`, cap `0.30` → **no** breach. Peak `$500`, current `$300`,
cap `0.30` → breach (the existing behaviour must survive). Peak below the floor never breaches
regardless of how far the position falls; the existing daily-loss and stop rules cover that case.
**Fixed by**: `PropFirmProtectionConfig.MinPeakGainDollars` (default **50.0**, parsed from disk by
`ParseConfig`, set to `0` for the old purely-proportional behaviour), checked immediately before
the proportional test in `EvaluatePeakEquityGiveback`. Test-first:
`TestP1_40_NoiseSizedPeakDoesNotTripGiveback` was observed red at baseline (417 passed / **3
failed**, on exactly the three noise-peak assertions), green after the fix (**420 / 0**), and red
again when the single guard line is reverted. Deployed and compiled in NT8 with 0 errors; the live
`/api/prop/limits` response now reports `MinPeakGainDollars`, which is how you can tell the new
code is loaded.

> **The `50.0` default is the one judgement call here** and it is the number to argue with, not
> the mechanism. It says "below $50 of open profit there is no peak worth protecting". For a
> $50k account against a $1,500 trailing drawdown that is noise; for a much smaller account it
> may not be. It is per-config, so tune it rather than removing the floor.

### P1-42. Per-firm profiles are never read — `FirmMirror` silently protects nothing on a mapped account — CLOSED 2026-08-07
*(found 2026-08-07 while deciding what an armed shadow session would actually exercise)*
**Where**: `RiskGuardAddOn.cs:3594` (the call site) and `:3656` (`ComputeFirmMirror`), against
`FirmMirrorConfig.AccountFirmMap` / `FirmProfiles` (`:4294`, `:4295`).
**What happens**: `EvaluateFirmMirror` calls
`ComputeFirmMirror(balance, realized, unrealized, _config.FirmMirror, st, nowUtc)` — it passes the
**top-level** `FirmMirrorConfig` straight through, and `ComputeFirmMirror` reads only
`fm.TrailingDD` and `fm.DailyLoss`. **Neither `AccountFirmMap` nor `FirmProfiles` is consulted by
any evaluation path.** The only reference to `AccountFirmMap` in the whole addon is
`RunPreflight`'s validation at `:2668`, which checks that every mapped firm exists in
`FirmProfiles`.

That validation is what makes this dangerous rather than merely incomplete. Preflight *validates*
the mapping and refuses to arm if a firm name is unknown (P2-8), so the mapping presents as
load-bearing configuration that the system has checked — while no code reads it. A validated
mapping that is never used is worse than no mapping at all, because it buys false confidence.

Observed on this machine, 2026-08-07: `FirmMirror.Enabled: true`, but top-level
`TrailingDD.Enabled: false` and `DailyLoss.Enabled: false`, `AccountFirmMap: {}`, and four fully
researched profiles in `FirmProfiles` (TakeProfitTrader, Tradeify, Lucid, Apex — the TPT one
carrying the real $1,500 EOD trailing drawdown). Net effect: **no firm rule evaluates for any
account, including the funded TakeProfit Trader account, and mapping that account would not
change it.** The researched numbers are dead config.

**Fixed by**: `ResolveEffectiveFirmConfig` — maps account → firm → profile and substitutes that
profile's `TrailingDD`/`DailyLoss`, keeping the daily boundary (a property of the clock, not the
firm). Falls back to the top-level pair when the account is unmapped, the firm is absent, or the
profile omits a sub-rule. **The audit-log payloads read the effective config too**: left on the
top-level values they would have described a rule that did not run, which is the shape of failure
that made this defect invisible in the first place.
**Test**: red at baseline (430 passed / 3 failed) against the exact live config shape, green after
(433/0), red again when the resolver call is reverted.

Original fix note follows.

**Fix**: resolve an effective profile per account before computing. Look up
`AccountFirmMap[st.AccountName]`, then `FirmProfiles[firmName]`, and feed that profile's
`TrailingDD`/`DailyLoss` into `ComputeFirmMirror`, falling back to the top-level pair when the
account is unmapped or the firm is missing. `ComputeFirmMirror` already takes a
`FirmMirrorConfig`, so the smallest correct change is to build an effective one at `:3594` rather
than to thread new parameters through it. Both dictionaries are `OrdinalIgnoreCase`, so the
lookups are already case-tolerant — do not "fix" that (see P1-39).
**Test**: an account mapped to `TakeProfitTrader` breaches at the *profile's* trailing amount and
not the top-level one; an unmapped account still uses the top-level pair; a mapped account whose
firm is absent from `FirmProfiles` falls back rather than throwing (preflight blocks arming in
that case, but the evaluator must not depend on preflight having run); and with the top-level pair
disabled but a mapped profile enabled, the rule **does** fire — which is the exact case that
silently does nothing today.
**Sequencing**: closing this switches on real firm enforcement for any mapped account. Land it,
map the account, then run a full shadow session and read the `FIRM_*` events **before** going
anywhere near an acting mode — the numbers involved are the ones that fail a funded evaluation.

### P1-43. `ExecuteOrderUpdate` makes broker calls under `_stateLock` — a third instance of the closed P1-10/P1-35 invariant — CLOSED 2026-08-07
*(found 2026-08-07 while investigating the order-flood stress-test output)*
**Where**: `RiskGuardAddOn.cs:1400` opens `lock (_stateLock)`; `:1422` and `:1436` call
`account.Cancel(...)` inside it.
**What happens**: the documented central invariant — never hold `_stateLock` across a broker call
— is violated on the order-update path, which is the hottest path in the addon. P1-10 and P1-35
closed the same violation in the safety sweep and FSM teardown, and the lock-scope check was made
machine-enforced (`Account.BrokerCallObserver` + `TestIsStateLockHeld()`). **It did not catch this
one because the check only exercises the sweep and teardown paths**, not `ExecuteOrderUpdate`.
A machine check is only as good as the paths driven through it.
**Fix**: queue the cancels and drain after the lock is released, exactly as P1-35 did
(`_pendingCancels` / `DrainPendingCancels`). Do **not** wrap in a nested `lock` — it is re-entrant
and changes nothing.
**Test**: drive `ExecuteOrderUpdate` with the observer armed and assert zero broker calls occur
while `TestIsStateLockHeld()` is true. Then extend the check to *every* entry point that can reach
a broker call, so the next instance is caught by construction.

### P1-44. The order-flood cancel can kill a protective stop and leave a naked position — CLOSED 2026-08-07
*(found 2026-08-07, same investigation)*
**Where**: `RiskGuardAddOn.cs:1420-1423`.
**What happens**: on flood detection the triggering order is cancelled unconditionally:

```csharp
if (e.Order.OrderState != OrderState.Filled && e.Order.OrderState != OrderState.Cancelled)
    account.Cancel(new[] { e.Order });
```

There is **no `IsPositionReducingOrder` guard** — while the lockout-enforcement block immediately
below it at `:1432` has exactly that guard. So if the order that trips the rate limit happens to
be a stop-loss or other reducing order (very likely: an ATM submits entry, stop and target
together, and a copier fans the same burst across followers), RiskGuard cancels the protection
**and** locks the account out, leaving an open position with no stop. This is the P1-11 failure
mode in a path P1-11 did not touch.
**Fix**: reuse `IsPositionReducingOrder` before cancelling, as `:1432` does. Never cancel
protective orders to enforce a rate limit — rate-limit the *entries*.
**Test**: a burst in which the threshold-tripping order is a protective stop must leave that stop
working; only risk-increasing orders may be cancelled.

### P1-45. An order-flood lockout never expires, and it is persisted — CLOSED 2026-08-07
*(found 2026-08-07, same investigation)*
**Where**: `RiskGuardAddOn.cs:1419` sets `stateModel.IsLockedOut = true` and **never sets
`LockoutUntil`**.
**What happens**: the lockout test at `:1485` is
`(lockState.IsLockedOut || DateTime.UtcNow < lockState.LockoutUntil)` — an **OR**. Every other
lockout in the addon pairs the flag with a deadline (PnL `:1231`, `:1271`; overtrading `:2539`,
`:2558`), so it lapses. The flood path sets the flag alone, so it lapses **never** — and
`LockedOutAccounts` is persisted, so it survives a restart. A one-second burst can therefore
stop an account trading indefinitely with no timer and no obvious recourse.
**Fix**: set `LockoutUntil` from a configurable flood-lockout duration, consistent with the other
rules. Decide deliberately whether a flood should also require manual acknowledgement — but "no
deadline at all" should not be the accident it currently is.
**Test**: a flood lockout lapses after its configured duration; it is not resurrected by a restart
once lapsed.

### P2-46. The flood detector double-counts, so the real threshold is about half the nominal one — CLOSED 2026-08-07
*(found 2026-08-07, same investigation)*
**Where**: `RiskGuardAddOn.cs:1413-1417`.
**What happens**: the counter adds a timestamp for `OrderState.Submitted` **and** for
`OrderState.Accepted`, which are two states of the **same order**, with no dedupe by order id. A
single order commonly contributes two ticks, so the nominal "more than 5 orders/sec" fires at
roughly **3 real orders per second** — well within normal ATM bracket submission. The live log's
"29–32 orders/sec" readings are therefore not order counts but state-transition counts. The
threshold is also **hardcoded** (`> 5`) with no config knob, unlike every other limit in the addon.
**Fix**: count distinct order ids within the window, and expose the threshold and window in
`RiskConfig` alongside the other overtrading limits.
**Test**: ten distinct orders in a second trips a threshold of 5; one order passing through
Submitted→Accepted→Working counts once, not three times.

### P1-47. The guard defaults to disarmed, so every recompile silently removes all protection — CLOSED 2026-08-07
*(raised by the operator 2026-08-07 after four consecutive silent disarms in one session)*
**Where**: `RiskGuardAddOn.cs:206` (`private bool _isArmed = false;` in the non-TESTING build) and
`:655-656`, which deliberately does not rehydrate `IsArmed` from persisted state.
**What happens**: `nt_compile`, an NT8 restart, or any NinjaScript recompile reloads every AddOn
and the guard comes back **disarmed**. Nothing announces this beyond one `INITIALIZE` line, and
every evaluation path then returns early (`:1837`, `:2034`, `:1205`, `:2159`, `:2392`, `:2450`)
while `CanTrade` returns *allow* (`:124`). The dashboard is the only place the state is visible.
Observed four times in a single session on 2026-08-07; each time the operator had to notice and
re-arm by hand. A risk guard whose default state is "not guarding" fails open.

**The conflation.** `_isArmed` controls whether the guard *evaluates*; `_mode` controls whether it
*acts* (`:2895`, `isLive = _mode == "live"`). Armed + `shadow` observes and logs and cannot touch
the broker. The dangerous state is `live`, not `armed` — but the default protects against the
wrong one, and the cost is paid as unobserved gaps.

**Fix (recommended)**: make the default conditional on the resolved mode — come up **armed** when
the mode is non-acting (`shadow`), and **disarmed** in any acting mode, where arming should stay a
deliberate act after preflight. That keeps the original intent (freshly-loaded code must not act
on a funded account unattended) while closing the observability gap.

Whatever is chosen, **the disarmed state must be loud**: surface it in `/api/riskguard/version`
and `nt_health`, and log a distinct warning event on initialise rather than burying it in the
`INITIALIZE` line. The present failure is not just the default — it is that being unprotected
looks identical to being protected.

**Do not simply rehydrate `IsArmed` from disk.** That was removed on purpose (`:655`) so a restart
could not silently *re-arm* into an acting mode; restoring it would reintroduce that.
**Test**: constructing in `shadow` yields armed; constructing in `live`/`pure`/
`override_with_friction` yields disarmed; a persisted `IsArmed=true` never re-arms an acting mode
across a restart.
**Fixed by**: `DefaultArmedForMode` + `ApplyInitialArmState`, applied once at initialise after
`LoadConfig` resolves the mode (deliberately **not** on a config reload, which would override an
operator who disarmed on purpose). An unrecognised mode is treated as non-acting, because
`ProcessAction` requires exactly `"live"`. Coming up disarmed now logs `UNPROTECTED_ON_START`
naming the consequence, and `/api/riskguard/version` reports `mode`, `isArmed` and `guarding` so
the state is visible without opening the dashboard.

**Verified in production**: the next recompile came up `ARMED_ON_START` in shadow with the
endpoint reporting `isArmed: true` — the first reload of the day that did not silently disarm.

> **This one only failed in NT8.** Both methods were first written inside the `#if TESTING`
> region, which compiled cleanly under net8.0 and failed in net48 with "ApplyInitialArmState does
> not exist". The suite was green throughout. The `TESTING` guard now closes around them with a
> comment saying why — and this is the standing reason `nt_compile` is not optional after a
> change near the test hooks.

### P0-48. Every AddOn reload leaks a copier execution handler — CLOSED 2026-08-07, verified live
*(found 2026-08-07 while validating `P1-21`'s deployment, by reflecting on the live event list —
not by any test, review or log line)*
**Where**: `McpBridgeAddOn.cs`, `State.Configure` attached `OnAccountExecutionUpdate` to every
account and `State.Terminated` only called `StopServer()`. Nothing ever detached it.
**What happens**: NT8 hot-swaps a **new assembly** on every recompile and reloads every AddOn, but
the old instances are kept alive by the very event subscription that should have been removed. The
`-=` before `+=` in the old subscribe loop cannot help: it is evaluated against the *new* instance's
delegate, which never equals the orphan's.

Each orphan carries its own assembly's `TradeCopierEngine.Instance` — a distinct singleton with its
own `_relationships` (loaded from disk at its own `Configure`) and its own `_copiedExecutionIds`.
The per-instance dedupe therefore does **not** suppress them: one leader fill is copied once per
orphan.

**Measured on the live box, 2026-08-07 15:5x UTC**, `Sim101.ExecutionUpdate` invocation list:

| Owner | Handlers |
|---|---|
| `McpBridgeAddOn` (orphaned instances) | **57** |
| `ChartBars` / `ExecutionGrid` (NT8's own) | 6 |
| `MaxAlgoAutoTraderV3` | 1 |
| `TradeCopierEngine`, `RiskGuardAddOn`, `RiskManagerAddOn` | 1 each |
| | **67 total** |

`RiskGuardAddOn` at exactly 1 is the control: it already unsubscribes in `State.Terminated`
(`:331-338`), which is why it has not accumulated. The copier had no such path.

**Exposure at the time of discovery**: both relationships enabled, `Sim101 → Sim-ORB` with
`ArmedForLive: true`. A single Sim101 fill would have been copied by all 58 live engines, bounded
only by each one's independent `MaxPositionSize` re-read of the follower position.

> **Stated precisely**: the 57 live handlers and their distinct target instances are *measured*.
> The resulting duplicate copies are *inferred from the mechanism* — no fill occurred during the
> inspection, so the end-to-end effect has not been observed. The inference does not depend on
> anything unverified: the handlers are attached, and each forwards into a separate engine.

**Why this is P0 and not a housekeeping item**: it places unbounded unintended orders. It is
listed after `P1-47` because IDs are assigned in discovery order and never renumbered.

**Fixed by**: `P1-21`'s teardown half — `TradeCopierEngine.UnsubscribeAllAccounts()`, called from
`State.Terminated`, detaches exactly the accounts this engine instance attached. That stops
*recurrence* from the next reload onward.

**Not fixed by it**: the 57 orphans already attached. They belong to assemblies that are no longer
referenced by any live code, so no in-process call can enumerate or detach them by name — only an
**NT8 restart** clears them.

**✅ Both halves verified live, 2026-08-07.** NT8 was restarted and re-censused:

| | Before | After restart | After a further recompile |
|---|---|---|---|
| `McpBridgeAddOn` (orphans) | **57** | 0 | 0 |
| `TradeCopierEngine` | 1 | 1 | **1** |
| `RiskGuardAddOn` / `RiskManagerAddOn` | 1 / 1 | 1 / 1 | 1 / 1 |
| total | 67 | 8 | 10 |

The third column is the proof. A recompile reloads every AddOn and is precisely the event that used
to add an orphan; `TradeCopierEngine` holding at exactly 1 across it is the leak fixed, observed
rather than argued. (Totals rose 8→10 only from NT8's own `ChartBars`/`ExecutionGrid` re-registering.)

> **Note the post-fix shape**: `McpBridgeAddOn` is now **0**, not 1 — `P1-21` moved ownership of the
> subscription to `TradeCopierEngine`. An earlier draft of the runbook said to expect
> `McpBridgeAddOn == 1`; that is wrong. Expect `TradeCopierEngine == 1` and `McpBridgeAddOn == 0`.

**Open follow-ups**:
- Add the handler census to the deployment runbook (§4e) — it is cheap, and nothing else detects
  this class of bug.
- `RiskManagerAddOn.cs:150/289` has the same shape (subscribe at `Configure`, unsubscribe at
  `Terminated`) and currently reads 1, so it appears correct; confirm rather than assume.
- Consider whether `TradeCopierWindow.cs:1090` and `DynamicAtmManager.cs:507` hold any comparable
  subscription.

### P1-20. Weak simulated-account detection gates the live safety switch — CLOSED 2026-08-07
**Where**: `TradeCopierEngine.cs:650` — `followerAcc.Name.StartsWith("Sim", …)`
An account named e.g. `SimplyApex-01` is treated as simulated and **bypasses the
`ArmedForLive` gate** (`653-657`).
**Fix as landed**: `TradeCopierEngine.IsSimulationAccount(account)` tests
`account.Provider == Provider.Simulator` and fails closed — a null account or an
unidentifiable provider reads as live. Playback is deliberately *not* exempt. The defect cut
both ways and the tests pin both: a live `SimpsonFund` is now refused, and a genuine Simulator
account whose name lacks the `Sim` prefix is now served.

**Same defect, different file, still open**: `McpBridgeAddOn.cs:1710, 2243, 2307` gate strategy
deployment with `Name.StartsWith("Sim") || Provider…` — the name prefix is OR'd in, so it has
the same hole. Tracked as **P2-38**.

### P1-21. Copier never re-subscribes to accounts that connect later — CLOSED 2026-08-07
**Where**: `McpBridgeAddOn.cs:252-258` — `Account.All` is enumerated once at `State.Configure`.
RiskGuard handles this correctly via `Connection.ConnectionStatusUpdate`
(`RiskGuardAddOn.cs:296`, `OnConnectionStatusUpdate:770`).
**Fix**: mirror RiskGuard's pattern for `ExecutionUpdate` subscription, and unsubscribe on
disconnect to avoid duplicate handlers.
**Fixed by**: `TradeCopierEngine.RefreshAccountSubscriptions()` / `UnsubscribeAllAccounts()`, wired
from `McpBridgeAddOn`'s `State.Configure`, `Connection.ConnectionStatusUpdate` and
`State.Terminated`. A leader whose broker connects after startup is now subscribed on the next
connection change instead of being silently dead while enabled in the config and visible in the UI.

> **The bookkeeping deliberately lives on `TradeCopierEngine`, not in `McpBridgeAddOn`.**
> `RiskGuardTests.csproj` excludes `McpBridgeAddOn.cs` from the test build (its WPF dependencies
> break it), so a subscription implemented there is unreachable by any test — which is how this
> survived. Only the `Connection` event wiring, four lines, stays outside the test build.
>
> **The teardown half turned out to matter more than the re-subscribe half.** Adding
> `UnsubscribeAllAccounts` was defensive housekeeping when written; inspecting the live event list
> to confirm it worked found **57 orphaned handlers** from earlier reloads. That is **P0-48**.

**Tests** (`RiskGuardAddOnTests.cs`, all three proven falsifiable by a revert harness,
`scripts/agent_loop/verify_backfill_reverts.py` — **which no longer exists**; it went with the
archived predecessor loop. The equivalent today is a `mutation/` battery):
`TestCopierSubs_LateConnectingLeaderIsCopied` (0 copies when the pass is one-shot),
`TestCopierSubs_RepeatedRefreshAttachesOneHandler` (5 handlers when the `-=` is dropped),
`TestCopierSubs_TeardownDetachesHandlers` (1 handler survives when the detach is dropped).

> The idempotence test asserts on the **handler count**, via a new `ExecutionUpdateHandlerCount`
> on the Account stub, rather than on the number of copy orders. `OnExecution`'s `ExecutionId`
> dedupe would have absorbed a doubled handler within a single engine instance, so an
> order-counting assertion would have passed while proving nothing — the vacuous-test trap that
> the first draft of `S1`–`S4` fell into.

### P1-22. No slippage/latency control on copies — CLOSED 2026-08-07 (measurement + ceiling)
Everything is `OrderType.Market` with no reference to the leader's fill price, no maximum
acceptable slippage, and no latency measurement — while `LatencyMs` and `AvgSlippageTicks` are
displayed in the UI (`TradeCopierWindow.cs:799`) as if they were real.
**Fix**: record `exec.Time` → follower fill time to populate `LatencyMs`; compute realised
slippage in ticks vs the leader fill; add `MaxSlippageTicks` per relationship that quarantines
the relationship when exceeded; consider limit-with-offset instead of pure market for entries.

**Fixed by**: `RecordPendingCopy` at submit and `ObserveFollowerFill` on the follower's fill.
`LatencyMs` is the last observed leader-fill→follower-fill gap; `AvgSlippageTicks` is a running
mean. `MaxSlippageTicks` (default `0` = off) quarantines on breach.

The measurement hooks in at the **follower's** execution, immediately before recursion guard 1
drops it — that event is the copier's only possible observation of what its own order cost.

Four things that are not obvious, each pinned by a test:

1. **Slippage is signed by the follower's side.** Positive always means *worse for the follower*:
   a buy filled above the leader, or a sell filled below. Unsigned, a threshold quarantines
   relationships for filling **better** than the leader.
2. **Quarantine is entry-only, and quarantined relationships still copy exits.**
   `GetActiveRelationshipsForLeader` gained `includeQuarantined`, passed `true` for exits.
   `IsQuarantined` otherwise blocks *every* copy including the one that closes the follower out,
   stranding it in a position the leader has already left — the `P0-5` failure by another route.
   Same asymmetry as `P0-6`'s exit clamp and `P1-23`'s fail-closed sizing modes.
3. **Slippage is only computed between price-comparable instruments** — equal roots, or either
   direction of the built-in mini/micro matrix. A `CustomSymbolMappings` entry may legitimately
   map ES→NQ, whose prices are unrelated; with the guard removed that test records **−52,000
   ticks** and quarantines a healthy relationship on its first copy. Latency is still recorded,
   since it does not depend on price.
4. **Pending copies are keyed by `Order` *reference*, never `OrderId`.** `RiskGuardAddOn.cs:4481`
   already records that NT8's `OrderId` is not unique and can change across the historical→live
   transition. An id-keyed map passes every test in the suite because the stub assigns one stable
   GUID per order; `TestCopierSlip_FillIsMatchedWhenOrderIdChanges` makes the stub behave like
   NT8 instead. `OrderReferenceComparer` uses `RuntimeHelpers.GetHashCode` so the map is immune to
   any future `Order.Equals` override. **This was caught by reading the existing warning comment,
   not by a failing test — the suite was green with the defect in place.**

**Deliberately not done: limit-with-offset entries.** The plan lists it as "consider". It changes
copies from guaranteed-fill to maybe-fill, and a partial or unfilled entry leaves the follower's
size diverged from the leader's with no reconciliation — which is `P0-9`/`P3-30` territory. It
belongs with the bracket-replication work, not here.

**Also noted while in this code, not fixed**: `LoadFromDisk` does not parse `SizingMode`, `Mode`,
`StealthMode`, `PerTickerRatios` or `CustomSymbolMappings` for relationships, so those take their
defaults on every load and can only be set through the API or UI. `P1-23` assumed `PerTickerRatios`
was live config. Not yet numbered — verify before opening a defect.

### P1-23. Symbol translation and sizing modes are partly cosmetic — CLOSED 2026-08-07
- `TranslateSymbol` (`:360-395`) uses global `rawSymbol.Replace(symbol, target)` rather than a
  prefix substitution — fragile against any symbol appearing inside the expiry portion.
- `CopierSizingMode.NetLiquidationRatio`, `AvailableCashPercent` and `PerTickerMatrix` are
  declared (`:19`) but **not implemented** in `CalculateFollowerQuantity`; they silently degrade
  to `QuantityRatio`.
**Fix**: replace `Replace` with root-symbol substitution on the parsed root; either implement the
three sizing modes or remove them from the enum and the UI so the config cannot lie.
**Fixed by**: `TranslateSymbol` now substitutes the parsed root and matches case-insensitively;
`NetLiquidationRatio` and `AvailableCashPercent` fail closed on entries with an explicit log
instead of degrading to `QuantityRatio`. `PerTickerMatrix` needs no change — the per-ticker ratio
override is already applied in the ratio branch regardless of mode.

> **The case bug was the sharper half.** The root was upper-cased before lookup but `Replace` ran
> against the raw string, so a lower-case instrument name matched nothing, returned untranslated,
> and the copy went to the **leader's own contract** on a follower configured for the converted
> one — silently, with no error.
>
> **Unimplemented sizing modes fail closed on entries only.** Blocking an exit would strand the
> follower in a position the leader has already left, which is the P0-5 failure and worse than an
> unscaled one. Same asymmetry as the P0-6 exit clamp.

**Test**: `ES 12-26` ↔ `MES 03-26` both ways; a lower-case name still translates; a root that
merely *contains* a mapped symbol (`XES`) is not rewritten; an unimplemented sizing mode returns 0
for an entry and non-zero for an exit; `QuantityRatio` is unchanged.

---

## 4. P2 — Dead safety code, unreachable features, and stated-vs-actual gaps

### P2-24. Written-but-never-called safety machinery — ✅ CLOSED 2026-08-13, and the class is now a GATE (`tools/check_no_dead_safety_machinery.py`) because it recurred three times in the session that closed it
| Symbol | Location | Status |
|---|---|---|
| `CalculateSafeFollowerDelta` | TradeCopierEngine.cs:165 | never called — the fix for P0-5 already exists |
| `ReconcileFollowerPosition` | TradeCopierEngine.cs:194 | never called — the REAPER-equivalent desync repair |
| `IsQuarantined` | :326, :342 | read as a filter, **never set** by the engine on error |
| `DailyLossLimit` | :40, :501 | parsed, persisted, surfaced in the UI, **never enforced** |
| `EnableFollowerAtm` / `FollowerAtmStrategyName` | :36-37, :91 | copied between DTOs, never read |
| `LatencyMs` / `AvgSlippageTicks` | :43-44 | displayed in the UI, never computed |
| `StealthMode` | :38 | persisted, never read |

**Fix**: wire each one or delete it. Priority order: `CalculateSafeFollowerDelta` (P0-5),
`ReconcileFollowerPosition` (schedule it on a periodic reconciler — see P3-30), automatic
quarantine on submit exception / risk breach, then `DailyLossLimit` enforcement per relationship.
Config that is displayed but not enforced is worse than absent config — it invites a live
account to be armed on the belief that a limit is active.

### P2-25. The news shield can never fire in production — ✅ CLOSED 2026-08-13 (session 34: `LoadNewsEventsFromDisk`)
**Where**: `PropFirmProtectionSuite.cs:56` (`_newsEvents`), populated **only** by
`AddTestNewsEvent` (`:60`). `LocalNewsEventsFilePath` (`:36`) is parsed and persisted but never
read. `IsInNewsWindow` (`:84`) therefore always returns `false` outside tests, so the
`NEWS_SHIELD_LOCKOUT` branch (`RiskGuardAddOn.cs:1547`, reached from the test at `:1541`) is
unreachable. *(Line numbers re-measured 2026-08-13; the previous entry said `:51`, `:55` and
`:1124`.)*

⚠️ **RE-CONFIRMED INDEPENDENTLY 2026-08-13, and it is the reason the UI design gained a fourth
state.** A survey of every config leaf against every read in `addons/` scored this rule as READ:
`EnableNewsShield` defaults to `true`, `:1541` genuinely tests it, and it genuinely calls a real
method that genuinely iterates a real list. **Every static check passes on a rule that has never
been able to fire.** `CONFIGURED / EVALUATED / ENFORCING` cannot express that, so
[UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md) §6a adds **INERT** — *the rule executes and its
evidence set is empty* — and requires every rule in the guard snapshot to report the SIZE of the
evidence it evaluated against. This one would read `0 events loaded`. It is the state a linter
cannot see and a runtime snapshot can.
Also unimplemented: `EnableConsistencyCap` / `MaxDailyProfitPctOfTarget` / `EnableAutoDayFiller`
(parsed, never evaluated).
**Fix**: load events from `LocalNewsEventsFilePath` on config load and refresh periodically.
**tvDownloadOHLC** already has an economic-calendar pipeline
(`docs/architecture/ECONOMIC_CALENDAR_ARCHITECTURE.md` there — it did not move here in the split),
so the correct move is to emit a JSON feed from it into the path the suite reads, not to build a
second source. Note that this makes the fix **cross-repo**, which it was not when written.

### P2-26. Design-doc drift ([RiskGuardAddOn.md](RiskGuardAddOn.md)) — ✅ CLOSED 2026-08-13 (session 34: drift table updated)
| Doc claim | Code reality |
|---|---|
| §5, §6.5, §6.8: "1-second sweep" / "1-second `DispatcherTimer`" | `new Timer(OnSafetySweep, null, 5000, 5000)` — 5 s, `System.Threading.Timer` (`:303`) |
| §3 data-flow diagram: sweep → `EvaluateRules` | sweep no longer calls `EvaluateRules` (`:1448-1453`) |
| §6.5: sweep keeps aggregate sizing, firm-mirror, grace-expiry polling | all three moved to event handlers (`:889`, `:1048`) / per-FSM timers; sweep keeps only heartbeat, log flush, session reset, persist, lockout watchdog, FSM watchdog |
| §5, §6.7: "lock released before `Flatten`/`Cancel`" | ~~violated by the sweep (P1-10)~~ — **true again since 2026-08-07**; P1-10/P1-35 closed and the invariant is now machine-checked by `TestP1_10_...`/`TestP1_35_...` |
| §6.7: `EvaluateGraceExpiry` "called from a per-FSM Timer or the sweep" (code comment `:1708-1710`) | sweep never calls it — the "defensive" path does not exist |
| §9.1: "Automatic relationship quarantine on execution error or risk limit breach" | not implemented (P2-24) |
| §9.3: news / target / giveback "auto-lockout, auto-flatten" | news unreachable (P2-25); giveback mis-wired (P0-7); target semantics wrong (P1-17) |
| §2, §4, §8: "87 unit tests" / "84 comprehensive test methods" / "60 original + 24 FSM" in the same document | reconcile against an actual test run |
**Fix**: the doc is the artifact most likely to cause a wrong decision under pressure. Update it
in the same commit as each code change, and add a doc-drift check to the test harness (assert the
sweep interval constant matches the documented value).

**The drift got wider on 2026-08-07, not narrower.** Phases B and C changed real behaviour that
`RiskGuardAddOn.md` still does not describe: the pending-cancel queue and `DrainPendingCancels`
(P1-35), the sweep's three-phase lockout ordering (P1-11), provider-based simulation detection
(P1-20), FSM re-seeding on arm (P1-15), and `LastShadowSessionDate` in the persisted state
(P1-37). Anyone reading the design doc to understand the current lockout or copier gate will be
wrong about all five. Closing P2-26 means a rewrite against the code as it now stands, not a patch
of the table above.

### P2-27. The riskiest code has zero test coverage — PARTIALLY CLOSED 2026-08-13
**✅ The copy path (`OnExecution`) is now in the test build** — the harness repair (session 18) brought it in
deliberately, and it has three copy-path tests that reproduce P0-5, P0-6 and P0-8 as executable failures.
**✅ CI runs the suite** — GitHub Actions runs `dotnet run --project tests/RiskGuardTests.csproj` with
non-zero exit on failure (all 20 mutation batteries are invoked by CI, verified by
`check_ci_runs_every_battery.py`).
**✅ The bridge has its own test suite** — `nt8-mcp-bridge/tests/BridgeTests.csproj` has 50 tests,
a parse gate (`check_bridge_parses.py`), and `BridgeAccountResolver.cs` is executed by tests (P1-90).
**Still open**: `TradeCopierWindow.cs` is excluded from the test build (WPF dependencies). The UI's
write half (relationship toggle, quarantine release) is tested via engine-level tests, not window-level.
`McpBridgeAddOn.cs`'s HTTP endpoint handling is not behaviourally tested (only parse-checked).
`TradeCopierEngine.OnExecution` (`:613-745`) and `ReconcileFollowerPosition` (`:193-228`) are
inside `#if !TESTING`, so the entire copy path is excluded from `RiskGuardTests.csproj`. The same
applies to all real order submission in `RiskGuardAddOn.ExecuteAction`. The 4,237-line
`RiskGuardAddOnTests.cs` is a hand-rolled `Main`-plus-`Assert` console app with no CI job.
**Fix** — borrow V12's `PureLogic` split:
1. Extract the decision math into an NT8-free static class (`CopierSizingLogic`,
   `StopGuardDecisionLogic`) taking primitives/DTOs, with **no `#if`** — target position, delta,
   notional parity, stop price/side/quantity, coverage checks.
2. Keep `OnExecution`/`ExecuteAction` as thin submission shells over those functions.
3. Extend the stub `Account` (`TestingStubs.cs`) with a recording `Submit`/`Cancel`/`Flatten` so
   the submission shells become testable too.
4. Add a GitHub Actions job (`dotnet run --project tests/RiskGuardTests.csproj`)
   with a non-zero exit on failure — the harness currently has to be run by hand.

**A consequence that was not written down until 2026-08-13, and that costs something every
session: the agent-loop cannot be used on `nt8-mcp-bridge` at all.** The loop's ladder is held
up by two gates — a build and a test run — and in that repo both are blind to the file being
edited. `tests/BridgeTests.csproj` sets `EnableDefaultCompileItems=false` and compiles exactly
one file, `BridgeSourceTests.cs`; `addons/McpBridgeAddOn.cs` is not in it. So a loop run there
would compile a harness that excludes the patch, run source-text assertions, and report green
on code that does not compile. That is worse than not running it — it is a gate that proves
nothing, and this repo has now caught nine of those.

There is also no profile there (`agent/nt8_riskguard.py` is core-only). **One was deliberately
NOT written on 2026-08-13**: a profile whose build gate cannot see the patch is a trap, because
the next person to find it will trust its green. Same rule as everywhere else here — a thing
that reads as protection it does not provide is the defect, not the absence.

The unblock is step 1 of `tests/README.md`'s ordered remedy, and it lives **in this repo**: move
the NT8 stub block out of `tests/RiskGuardAddOnTests.cs` into `tests/TestingStubs.cs`. Mechanical,
same compilation unit, and fully gated here by 1147 executable tests and 13 batteries. 16 of the
19 types the bridge cannot resolve are already stubbed in that block; they just cannot be reached
from another repo without dragging in its `Main()`.

### P2-28. Three divergent copies of the addon sources + committed build output — ✅ **closed 2026-08-07**
- `scripts/ninjatrader/addons/` — canonical (referenced by `tests/RiskGuardTests.csproj`)
- ~~`scripts/strategies/nt8/addons_DONOTUSE/`~~ — **deleted**. Nine tracked files, zero code
  references (only this plan mentioned it); recoverable from history if ever needed.
- `mcp/ninjatrader-mcp/nt8-addon/` — **out of scope for this repo.** That path is a *git
  submodule* (gitlink `160000`), so its copies belong to the `ninjatrader-mcp` repo and must be
  fixed there. Deleting them from here would only dirty the submodule pointer.
- ~~`ninjatrader-addon/bin/`, `obj/`, committed `RiskGuardTests.exe`~~ — already resolved: all
  three are gitignored (`.gitignore:91-93`) and untracked. The plan text was stale.

**Fix as landed** — not the hard-link idea. `scripts/utils/sync_nt8_strategies.py` already
existed and does the job; it just had to be made trustworthy and safe:

- **It was blind to line endings.** It compared raw byte md5s, so with the repo on LF and the
  NT8 tree on CRLF it reported *every* file as drifted. That is where the runbook's false
  "the deployed sources have diverged" claim came from. `file_hash` now normalises CRLF and
  strips a BOM before hashing. A drift check that cries wolf on every file gets ignored, which
  is worse than no check.
- **It was all-or-nothing.** A full sync would have pushed 21 unrelated indicator files into a
  live NT8 mid-shadow-session. New `--only {strategies,indicators,addons}` scopes a deliberate
  deployment; orphan detection is skipped for scoped-out areas so it cannot report every
  deployed file as an orphan.

A hard link from the repo into `bin/Custom/AddOns/` was **considered and rejected**: it would
make every editor keystroke change what the live trading system compiles next, and destroy the
ability to run a shadow session against a known build while working on the next change. The
explicit deploy step is the feature.

Use `--verify --only addons` to check drift and `--only addons` to deploy. Never copy by hand
(this session did, and it is what left canonical two files ahead of deployed).

### P2-38. The strategy-deploy guard has P1-20's name-prefix hole too — CLOSED 2026-08-07
*(found while fixing P1-20, 2026-08-07)*
**Where**: `McpBridgeAddOn.cs:1710`, `:2243`, `:2307` —
`account.Name.StartsWith("Sim") || account.Provider.ToString().Contains("imulat")`.
**What happens**: the provider test is correct, but the name test is OR'd in front of it, so a
funded account called `SimpsonFund` is still classified as simulated and can be deployed to
without `confirmLive=true`. Same root cause as P1-20, different file and different blast radius
— this one gates *strategy deployment*, not copying.
**Fix**: drop the name clause at all three sites and reuse
`TradeCopierEngine.IsSimulationAccount`, or lift that helper somewhere both addons can share.
**Test**: an account named `SimpsonFund` on a live provider is refused without `confirmLive`.
P2 rather than P1 because it requires an explicit deploy call to reach, not an automatic path.

**Fixed 2026-08-07 (session 8) — and there were FOUR sites, not three.** The fourth
(`McpBridgeAddOn.cs:3992`, an order-placement path) used the name prefix **alone**, with no
provider test at all to fall back on. All four now call `TradeCopierEngine.IsSimulationAccount`.
Checked partly against source text: `McpBridgeAddOn.cs` is excluded from the test build by
construction, so its gates cannot be executed by the suite. The behavioural half — that the shared
classifier gets `SimpsonFund` right — is executed properly.

### P2-41. `POST /api/riskguard/config` overwrites the whole config with defaults — CLOSED 2026-08-07, verified live
*(split out of P1-39 on 2026-08-07 — the append half is closed, this half is not)*
**Where**: `McpBridgeAddOn.cs:5126` — `req.ToObject<RiskConfig>()`, then
`SaveAndReloadConfig(cfg)`.
**What happens**: the body is deserialized into a complete `RiskConfig`, so **every field the
caller omits silently becomes its default** — and `SaveAndReloadConfig` then writes that to
`RiskGuard/config.json` and reloads it. A caller posting `{"ExcludedAccounts": ["X"]}` intending
to add one exclusion would also reset `Mode` to `shadow`, `MinShadowSessions` to 0,
`EnableWindowGate` to false, and every `StopGuard`/`PnLRules`/`FirmMirror` value to its default,
destroying the live risk configuration. Nothing in the response indicates this happened — it
returns `status: "applied"` and echoes the *request*, not the resulting config.
**Workaround until fixed**: GET the full document, mutate the one key, POST the whole thing back,
then GET again and diff every key. That discipline is what surfaced P1-39.
**Fix**: merge the incoming `JObject` onto the live config (`JObject.Merge` with
`MergeArrayHandling.Replace`) before deserializing, or require an explicit
`?full=true` for whole-document replacement and reject partial bodies otherwise. Echo the
resulting live config rather than the request.
**Test**: POST `{"ExcludedAccounts":["X"]}` against a config with `MinShadowSessions=3` and
`Mode="shadow"`; assert both survive and only `ExcludedAccounts` changed.
P2 rather than P1 because reaching it requires an explicit API call, not an automatic path.

**Fixed 2026-08-07 (session 8).** The incoming `JObject` is merged onto the live config
(`RiskConfigMerge`), with arrays **replaced** rather than concatenated — union semantics would make
`ExcludedAccounts` append-only with no way to remove an entry through the API, and concatenation is
the exact mechanism behind `P1-39`. The response now echoes the **resulting** live config as
`config` and the request as `requested`; the old reply looked identical whether the merge happened
or not.

The merge lives in `RiskGuardAddOn.cs`, not the bridge, because the bridge is excluded from the
test build — it is pure JSON manipulation with nothing NinjaTrader about it, and putting it there
is what makes it testable at all.

> **Verified live, by accident, immediately after deploying.** `nt_riskguard_config` with no
> arguments POSTs an **empty body**. Under the old code that single call would have flattened the
> live risk configuration to defaults: `Mode` shadow, `MinShadowSessions` 0, `EnableWindowGate`
> false, all six `WindowsET` gone, all four `FirmProfiles` gone. The post-fix response returned
> `"requested": {}` alongside the complete, unchanged live config. **The MCP tool most likely to be
> reached for as a read was itself a destructive write.**

### P2-29. Single-file size / complexity — PARTIALLY CLOSED 2026-08-15 (session 42): the WPF dashboard is out and verified; the `partial class` split of `RiskGuardAddOn` itself is the recorded remainder

⚠️ **The sizes in the original entry were wrong and nothing had measured them since.** It said
`RiskGuardAddOn.cs` was 4,108 lines with the window at `:3389-4096`. Measured 2026-08-15:
**7,058 lines**, window at `:6338-7057`. A size claim decays silently; re-measure before quoting.

**What landed.** `RiskGuardWindow` + `CardControls` moved verbatim to `addons/RiskGuardWindow.cs`
(724 lines). `RiskGuardAddOn.cs` **7,058 → 6,334**. This is a **move, not a rewrite**: both are
their own top-level types, so no `partial` keyword was needed and no member could be reshuffled.
Suite **1469/0 before and after**; `nt_compile` **errorCount 0** with a byte-identical warning set;
`sync_nt8.py --verify` **ALL IN SYNC (10 files)**; the running guard read back **shadow / armed /
96 accounts / 2,304 rule rows**, unchanged.

⚠️ **THE FINDING, AND IT IS THE REASON THIS TICKET IS WORTH MORE THAN TIDINESS: A PURE CODE MOVE
SILENTLY DISARMED A SOURCE GATE.** `mutate_p187.py`'s WarnOnly mutant **SURVIVED** after the move,
where it had always been killed. The test that kills it asserts `!code.Contains("WarnOnly")` over
`addons/RiskGuardAddOn.cs` **read by name** — and the settings dropdown it forbids had moved to the
file next door. The gate searched a file the string could no longer be in and **passed**.

* **`check_anchors.py` did NOT catch it.** That gate verifies the BATTERY can still find its
  target — a different question from whether the TEST can. It correctly reported the one broken
  anchor and said nothing about the gate, because nothing inspects a test's file paths.
* **The mutation battery caught it, and only the battery.** The suite was 1469/0 throughout.
* ⚠️ **AND THE TWO DIRECTIONS ARE NOT SYMMETRIC.** A source gate asserting a pattern is **PRESENT**
  fails loudly when pointed at the wrong file. One asserting a pattern is **ABSENT** *passes
  vacuously* — it finds nothing because it is looking nowhere. **Absence gates must read the tree.**

**Remedy**: `AllAddonCode()` concatenates every `addons/*.cs` with comments stripped, refuses an
empty corpus, and is what all absence gates now search. `TestP2_29_TheSourceGatesReadTheWholeAddonTree`
is the gate on the gates. Same remedy as `check_bridge_parses.py` and `BridgeTests.csproj` in the
sibling repo, both of which stopped being hand-typed file lists the same week — **state the REGION
a check inspects, and make it the whole thing the check is about**.

⚠️ **WIDENING THE P1-13 GATE TO THE TREE FOUND A REAL DEFECT IMMEDIATELY** — filed as **`P2-112`**
below. Nothing needed registering for the new file: `sync_nt8.py` and `tests/RiskGuardTests.csproj`
both already glob `addons/*.cs`.

**Remainder (deliberately NOT done here)**: splitting `RiskGuardAddOn` itself into
`{Core,Fsm,Rules,Actions,FirmMirror,Persistence}` partials. That is a genuinely different change —
it moves members of one class rather than relocating independent types — and it would break far
more than one anchor. The tooling to do it safely now exists and is proven (`check_anchors.py` +
`AllAddonCode()` + the batteries). Optionally port `scripts/complexity_audit.py` as a CI metric.

---

### P2-112. `DynamicAtmManager.MonitorTick` fails open with no dispatcher — the ATM breakeven loop silently never runs — OPEN, found 2026-08-15 by widening `P1-13`'s gate to the addon tree

**Where**: `addons/DynamicAtmManager.cs:507`

```csharp
var dispatcher = System.Windows.Application.Current?.Dispatcher;
if (dispatcher == null) return;
dispatcher.InvokeAsync(() => MonitorTickCore());
```

**This is `P1-13` verbatim, at a subsystem that ticket never looked at.** `P1-13` was closed
against the guard's own event handlers, and its gate then read only `RiskGuardAddOn.cs` — so this
site was never inspected by anything. With `Application.Current` null (early startup before the WPF
app object exists, or a headless NT8), the 5-second monitor returns immediately, **forever**:
breakeven stops never move, trailing never advances, and nothing anywhere logs a word. A protection
feature that is silently absent while every surface reports healthy.

⚠️ **NOT FIXED IN THE COMMIT THAT FOUND IT, deliberately.** `P1-13`'s remedy was *run the work
inline* (`RunGuardWork(label, work) => work()`), justified because `_stateLock` already protects
the guard's state and broker calls marshal at the `ProcessAction` boundary. **That justification
does not transfer here**: `MonitorTickCore` calls `Account.Change()` directly, so running inline
puts a broker call on a `Timer` thread — and `Account.Change()` is the call site whose semantics
the handover records as needing verification **on settle** (a second change in flight reverts the
order; on Simulator it is discarded while NT8 echoes your price back). That is a change to make
against a live market, not behind a green suite on a Friday night.

⚠️ **Reachability is the mitigating factor and it was NOT measured.** This box runs the NT8 GUI, so
`Application.Current` is normally non-null; the defect is latent rather than active. **Nothing here
establishes how often it is null**, and that measurement is part of closing this.

**Band**: `P2` on consequence — one subsystem's protection silently absent, where `P1-13` was all of
them — with low measured reachability. **Weigh by §5.6, not by the letter.**

**Held green by an ID-bearing allowance**, not by narrowing the gate back: `TestP1_13_...` now
searches the whole tree, exempts `DynamicAtmManager.cs` by name with this ID, **and asserts the
exemption is still NEEDED** — so it cannot outlive the defect and quietly widen the gate. Same
both-directions construction as `tools/check_no_dead_safety_machinery.py`.

**Fix**: give the ATM monitor the same treatment the guard got, with the broker call marshalled
rather than the whole tick — i.e. run `MonitorTickCore` inline and marshal only the
`Account.Change()`, or fall back to inline with a one-shot warning. Then delete the allowance in
the same commit and re-drive an ATM breakeven move live.

---

## 5. P3 — Architecture upgrades worth porting from V12

### P3-30. An independent reconciler (the REAPER port) — ✅ CLOSED 2026-08-13. ⚠️ The guard-side audit shipped COMPILED OUT of production (`#if TESTING`), unwired, and keyed on `Instrument.ToString()` where every FSM keys on `.FullName`; all three fixed in v1.14.0 with `mutation/mutate_p330.py`

> 🔶 **PARTIALLY SHIPPED 2026-08-10 — the copier's bracket half is done and deployed. Still open:
> the background timer, and the RiskGuard-side audit.** See handover §4u.
>
> What landed (`scripts/ninjatrader/addons/CopierReconciler.cs`, new):
> - `ComputeDesiredBracket` — **pure**. Every leg price, side, and size derives from broker reads
>   and the signed offsets, with no accumulated state. The arithmetic defects are now property
>   tests on one function instead of scattered guards.
> - `Reconcile(desired, owned, stopInFlight, targetInFlight)` — **pure diff**, and it cancels
>   *extra* owned legs. That single rule is what makes a duplicate leg self-healing.
> - Both leg syncs in `TradeCopierEngine` now decide through it (`DecideLegActions`), rather than
>   from `bracket.WorkingStop` / `bracket.WorkingTarget`.
>
> **The structural finding that made this worth doing.** Neither sync had *ever* enumerated
> `followerAcc.Orders` — each read one cached `Order` reference per leg. So a leg that existed at
> the broker but was not the one being held was **invisible, and therefore permanent**. That is
> what "two working COPIER_TARGETs against one lot" was on 2026-08-10 (`P0-59`): not a leg placed
> wrongly, a leg nothing was *capable* of noticing afterwards. No amount of care on the fast path
> could have fixed that, which is the argument for the reconciler in one sentence.
>
> **A leg has THREE states of desire, not two.** `HasStop: bool` is the obvious design and it is
> wrong: "no stop desired" would mean both *"the position is gone, cancel everything"* and *"the
> leader cancelled its own stop, so we do not know where ours goes"*. Collapsing them reverts
> `P0-9` item (4) and takes the stop off an open position — a naked follower shipped as a
> refactor. Hence `LegIntent { Required, Unspecified, Forbidden }`, where `Unspecified` still
> de-duplicates but never creates and never cancels the last survivor.
>
> **Do not confuse `bracket.StopInFlight` with `Reconcile`'s in-flight parameter.** The first is
> mutual exclusion between two *syncs*; the second is "submitted, not yet in `Account.Orders`".
> Feeding the first into the second was the first wiring, and it placed **no stop at all** —
> `SyncFollowerStop` sets the reservation before calling in, so the reconcile suppressed the very
> Create the sync existed to make. The event-driven callers pass `false`.
>
> **Verified by mutation, not by argument**: 10 mutations of the pure core and 8 of the wiring,
> each reinstating a belief that was live at some point or an obvious-looking simplification.
> 17 of 18 were caught by a named test. The one survivor is recorded in handover §4u, along with
> two guards found to be *unreachable* by the same method and honestly re-labelled instead of
> being left to read as safety.

Today both addons trust their own in-memory model. V12's REAPER assumes the model is wrong and
re-derives truth from the broker every cycle. Build one auditor serving both addons:

```
RiskGuardReconciler (background thread, 1-2 s)
  for each subscribed account:
    broker truth  := account.Positions + account.Orders
    expected      := AccountState + _guardFsms  (+ copier target positions)
    detect:
      - naked position          (position != flat, no non-terminal covering stop >= qty)
      - partially covered       (stop qty < position qty)
      - orphan stop             (working stop, no position)
      - FSM/broker divergence   (FSM says Protected, broker has no stop)
      - copier desync           (follower position != f(leader position))
    remediate (marshaled to the order thread, deduped by in-flight dictionary,
               each with its own grace window):
      - attach stop | flatten | cancel orphan | re-derive FSM | quarantine relationship
```
Reuse what exists: `SeedFsmsForExistingPositions` is already a correct re-derivation routine, and
`ReconcileFollowerPosition` is already a correct follower repair — both just need to be called
from here. Borrow REAPER's `_repairInFlight` / `_nakedPositionFirstSeen` grace pattern so a
normal bracket-confirmation window is not mistaken for a naked position.

### P3-31. Expected-position ledger with reserve/rollback — ✅ CLOSED 2026-08-13 (session 34: `InFlightLedger` + the 5s reconciler timer)

> 🔶 **The reconciler's SEAM for this exists and is tested; the ledger itself does not.**
> `Reconcile` takes `stopSubmitInFlight` / `targetSubmitInFlight` and suppresses `Create` — and
> **only** `Create`, never a `Cancel`, so a reservation can delay placing a leg but never delay
> removing one (an orphan leg surviving on a flat account would be `P0-50` resurrected through
> the ledger). Both directions are pinned by test.
>
> On the event path the callers pass `false`, because the existing per-leg reservation already
> serialises syncs and the submitted leg is recorded in `bracket.WorkingStop` — which is folded
> into the candidate list — before a second pass can run. **A timer-driven caller is what needs
> the real ledger, and that is the half still to build.** `P3-31` is not a follow-up to `P3-30`,
> it is the other half of it: a timer without the ledger reproduces the duplicate-leg family,
> because between `Submit` and `Accepted` the order is in neither `Account.Orders` nor the cache.

V12 registers the master's expected position **before** submitting and rolls the reservation back
if the submit returns null. Adopting this fixes P0-2 structurally and gives the reconciler a
precise "expected vs actual" to compare, instead of inferring intent from order names.

### P3-32. Follower risk anchored to the follower's own fill — SUPERSEDED by P0-9, CLOSED 2026-08-13
**Verified**: `FollowerBracket.FollowerEntryPrice` is the follower's own average fill (`bracket.FollowerEntryPrice = pos.AveragePrice` at `TradeCopierEngine.cs:4558`). The stop and target offsets are SIGNED and applied to the follower's entry, not the leader's (`ComputeDesiredBracket` in `CopierReconciler.cs` uses `followerEntryPrice + stopOffset`). This is precisely "follower risk anchored to the follower's own fill". P0-9 is fully implemented and live-validated (§5.13). P3-32 is superseded and closed.

### P3-33. Replace the global lock on the hot path — OPEN
V12 enforces zero `lock()` via an `Enqueue(ctx => …)` actor model, so no event handler can ever
block another. A full port is large; the pragmatic subset is: keep `_stateLock` for state
mutation only, never hold it across I/O or broker calls (P1-10/12), and move the action queue to
a `ConcurrentQueue<GuardAction>` drained by a single executor.

### P3-34. Arm/shadow discipline extended to the copier — ✅ CLOSED 2026-08-13. The copier has its own `live`/`shadow`/`disabled` mode (core `v1.15.0`), `RunCopierPreflight` gates the move to `live`, and the read surface landed with it: `copierMode` + `set_mode` on `/api/copier/config`, and `set_mode`/`copierMode` on `nt_copier_config`. Live-validated end to end. 11 mutants / 0 survivors
RiskGuard's `RunPreflight` + `MinShadowSessions` gate is the best-designed safety feature in
either addon. The copier only has a per-relationship `ArmedForLive` bool with a name-based sim
check (P1-20). Give the copier the same treatment: a global arm switch, a shadow mode that logs
intended follower orders without submitting, and a preflight that verifies every follower is
connected, subscribed, not locked, and has a resolvable instrument.

---

## 6. Execution order

> **Superseded for P0, which is complete.** The original phases 1–2 were the P0 work and landed
> as tickets T1–T5 (see [RISKGUARD_HARDENING_HANDOVER.md](RISKGUARD_HARDENING_HANDOVER.md) §1).
> The table below is the **remaining** work, re-ordered for what P0 changed and for test-first
> development. The live roadmap with current status is handover **§5.6** (§4a is
> historical as of 2026-08-13); this is the reference version with exit gates.

### 6.0 Development model: test-first, suite as a first-class artifact

**Every defect gets its failing test before it gets its fix.** This is enforced mechanically, not
by convention:

- A ticket declares `expect_green` — the tests it exists to make pass.
- The loop **refuses the ticket** unless those tests are already *failing* at baseline. A name
  that is not red is either a typo (making the gate unfalsifiable) or a test that passes without
  the fix (so it does not test the defect).
- The test gate then **fails the candidate** while any named test is still red. "No regression" is
  not evidence that a defect is closed.
- Reviewers receive the acceptance tests read-only and must judge **completeness** (which spec
  behaviours and failure paths nothing covers) and **accuracy** (would this test fail if the
  defect returned?). Gaps are MAJOR findings.

The suite is never edited to make a patch pass: `*Tests.cs` is in the loop's protected paths, so
the implementer cannot reach it by construction. Tests are authored *outside* the implementation
loop, by a different party than the one being graded — which is the strongest form of this
discipline available here, not a limitation of it.

Two lessons paid for during P0 apply directly:
- **A test that cannot observe its own subject is worse than no test**, because it reads as proof.
  The P0-8 test built a locked RiskGuard but never wired the static the copier reads; it could
  never have passed however correct the fix.
- **A green suite is not a tested suite.** `ff72e574` found a test whose body had been replaced by
  a bad merge, silently skipping 21% of the run, while the suite reported green.

### 6.1 Remaining phases

| Phase | Content | Tests to write FIRST | Gate to exit |
|---|---|---|---|
| **A. Deploy P0** | no new code | — | A full session in `shadow`; `interventions.jsonl` shows no `PEAK_GIVEBACK_BREACH` on a profitable flat account and no wrong `COPY_BLOCKED_NO_GUARD` |
| **B. Foundation** ✅ | `expect_green` ✅, backfill T1–T3 tests ✅, P2-28 ✅ | submit-failure rolls back and clears `GraceEmitted`; auto-stop sized from live qty; scaled-down position still gets a stop; stop cancelled mid-position re-arms; profitable-flat emits no giveback; flip does not carry `PeakOpenGain` | Every P0 behaviour has a test that fails when reverted |
| **C. Gate integrity** DONE | **P1-20** done, then **P1-37** done | live-named account is NOT treated as simulated; unguarded live follower is refused; two restarts on one date count as one shadow session | T5's fail-closed gate no longer keys off a name prefix; `MinShadowSessions` cannot be satisfied by restarting |
| **D. Concurrency** | P1-35 + P1-10 (one ticket), P1-11, P1-12, P1-13, P1-14, P1-15, P1-36 | no `Account.*` reachable under `lock (_stateLock)`; sweep does not cancel protective stops; coverage aggregates across two partial stops | Lock-scope gate clean; sweep off the dispatcher |
| **E. Rule semantics** | P1-16, P1-17, P1-18, P1-19 | 3-partial loss counts as 1; eval target fed cumulative PnL; one trailing-DD implementation; instrument-scoped flatten leaves other instruments alone | Each rule has a test pinning its boundary |
| **F. Copier fidelity** | P0-9 (real bracket replication), P1-21, P1-22, P1-23, P3-32 | follower brackets present on every copy; re-subscribe on late connect; symbol translation table-driven | Brackets on every copy; latency/slippage from real fills |
| **G. P2 structural** | P2-24, P2-25, P2-26, P2-27 (CI half), P2-29 | drift assertion: design doc claims match code | CI runs the suite on push; doc matches code |
| **H. P3** | **P3-30 first** (reconciler/REAPER), P3-31, P3-33, P3-34 | manual stop cancel, manual naked position, follower desync each repaired within one grace window | Sim stress scenarios pass unattended |

**P3-30 is P3 by effort, not by value** — an independent auditor that re-derives truth from the
broker is the single highest-value addition in this document. Consider promoting it once D lands.

### Validation protocol (every phase)
1. Failing tests written and committed **before** the implementation ticket runs.
2. `shadow` mode on Sim accounts for the whole phase; diff intended vs actual actions in
   `interventions.jsonl`.
3. Adversarial Sim scenarios, run against the live bridge (extend
   `tmp/comprehensive_stress_test.ps1`): cancel a stop under an open position; reject a stop
   (invalid price); scale in past stop coverage; flatten the leader while a follower copy is
   in flight; lock a follower mid-session; disconnect a follower mid-copy; disarm and re-arm with
   positions open; kill NT8 with positions open and restart.
4. Only then flip `ArmedForLive` on a single live micro account with minimum size.

### Non-goals for this plan
- No port of V12's Photon SPSC ring / MMIO mirror. Our latency budget (HTTP bridge, 5 s sweep)
  is orders of magnitude above where zero-allocation ring buffers matter; adopting them would add
  risk, not remove it.
- No adoption of V12's entry logic (OR/RMA/MOMO/TREND/FFMA) — different problem domain.
- No move to `Account.All` iteration inside a strategy (V12's SIMA model). Our addon-based
  design is the right choice for copying trades placed by hand or by other strategies.

---

## 7. Quick-reference defect index — ⚠️ FROZEN P0-era snapshot, do NOT read as current

> **Frozen 2026-08-13. Kept as a record, not as an index.** It is a third hand-maintained copy of
> information the per-defect entries already hold, and it went stale the same way the inventory table
> did (handover §5.12):
>
> - **It omits eleven defects** — `P0-49`, `P0-50`, `P0-53`, `P0-55`, `P0-59`…`P0-63`, `P0-67`,
>   `P1-54`, `P1-56`, `P1-57`, `P2-58`. Scanning it would tell you `P0-63` does not exist.
> - **The `CLOSED` markers are incomplete**: `P0-1`…`P0-9`, `P1-36` and others are closed and are not
>   marked here.
> - **Every `file:line` predates the repo split** and most predate several thousand lines of change.
>   `RiskGuardAddOn.cs` is no longer 4,108 lines. Treat every number as an archaeological hint and
>   `grep` for the symbol instead.
>
> **For the current list:** the band table at the top of this file for counts, the §1–§5 entries for
> mechanisms, and the handover's §5 for what is open. Do not add rows here — a fourth copy is the
> problem, not the fix.

| ID | Severity | File:line *(pre-split, unreliable)* | One-line |
|---|---|---|---|
| P0-1 | naked risk | RiskGuardAddOn.cs:1667, 1763 | `Protected→Unprotected` never re-arms grace; watchdog is log-only |
| P0-2 | naked risk | RiskGuardAddOn.cs:2595 | FSM state written after submit, overwrites reject; null submit silent |
| P0-3 | wrong size | RiskGuardAddOn.cs:2508, 2436 | auto-stop uses stale qty; over-cover flips position |
| P0-4 | naked risk | RiskGuardAddOn.cs:1555 | scale-in stays `Protected` without coverage check |
| P0-5 | wrong side | TradeCopierEngine.cs:401, 427 | exit qty unclamped → follower reverses; `CalculateSafeFollowerDelta` unused |
| P0-6 | wrong size | TradeCopierEngine.cs:426 | `Math.Max(1, …)` on micro→mini = up to 10× notional |
| P0-7 | false trigger | RiskGuardAddOn.cs:1154 | peak-giveback compares total-PnL peak vs unrealized only |
| P0-8 | gate bypass | TradeCopierEngine.cs:645 | copier ignores RiskGuard lockout |
| P0-9 | naked risk | TradeCopierEngine.cs:721 | followers get bare market orders; `EnableFollowerAtm` dead |
| P0-51 CLOSED | gate bypass | RiskGuardAddOn.cs:1848-1889, 1899-1940 | lockout sweep calls `Cancel`/`Flatten` with no `_mode` check; shadow logs "would execute" and flattens anyway |
| P1-52 CLOSED | false lockout | RiskGuardAddOn.cs:1596-1631, 5132 | flood governor counts a 2-lot ATM bracket (6 orders) as a flood against a limit of 5 |
| P1-10 CLOSED | deadlock | RiskGuardAddOn.cs:1336-1446 | broker calls under `_stateLock`, violating documented invariant |
| P1-11 CLOSED | naked window | RiskGuardAddOn.cs:1410 | lockout sweep cancels protective + reducing orders |
| P1-12 | latency | RiskGuardAddOn.cs:865, 1342 | blocking file I/O under the global lock |
| P1-13 | latency | RiskGuardAddOn.cs:1317 | guard evaluation on the WPF dispatcher; skipped if null |
| P1-14 | correctness | RiskGuardAddOn.cs:1651 | `_pendingStops` single-slot, no TTL, side-blind |
| P1-15 CLOSED | coverage gap | RiskGuardAddOn.cs:2231 | re-arm does not seed FSMs for open positions |
| P1-35 CLOSED | deadlock | RiskGuardAddOn.cs:1620 | FSM teardown cancels orphan auto-stop under `_stateLock` |
| P1-36 | over-cover | RiskGuardAddOn.cs:3167 | coverage tracks one stop; two partial stops read as under-covered |
| P1-37 CLOSED | gate bypass | RiskGuardAddOn.cs:1510, 211, 609 | `MinShadowSessions` counted addon restarts; 0→3 in 4 min during Phase A |
| P1-39 CLOSED | gate widens | RiskGuardAddOn.cs:4251, 599; McpBridgeAddOn.cs:5126 | Json.NET appends to initialized lists; `WindowsET` grows every load and a default window cannot be deleted |
| P1-47 CLOSED | fails open | RiskGuardAddOn.cs:206, 655 | guard defaults to disarmed, so every recompile silently removes all protection |
| P1-43 CLOSED | invariant | RiskGuardAddOn.cs:1400, 1422, 1436 | broker `Cancel` under `_stateLock` on the order-update path; the machine check never drove this path |
| P1-44 CLOSED | naked position | RiskGuardAddOn.cs:1420 | flood cancel has no `IsPositionReducingOrder` guard and can cancel a protective stop |
| P1-45 CLOSED | permanent lockout | RiskGuardAddOn.cs:1419, 1485 | flood lockout sets no `LockoutUntil`, so it never lapses, and it is persisted |
| P2-46 CLOSED | miscount | RiskGuardAddOn.cs:1413 | Submitted and Accepted both counted for one order; threshold hardcoded at 5 |
| P1-42 CLOSED | silent no-op | RiskGuardAddOn.cs:3594, 3656 | `AccountFirmMap`/`FirmProfiles` are never read; firm-mirror protects nothing on a mapped account, and preflight validates the unused mapping |
| P1-40 CLOSED | false flatten | PropFirmProtectionSuite.cs:110; RiskGuardAddOn.cs:1325 | giveback rule was proportional-only; a one-tick peak made any retrace a 100% breach — fired 6× in 36 s live |
| P1-16 CLOSED | false lockout | RiskGuardAddOn.cs:1008 | consecutive losses counted per partial exit |
| P1-17 CLOSED | never fires | RiskGuardAddOn.cs:1139 | eval target fed session PnL, not cumulative |
| P1-18 CLOSED | conflict | RiskGuardAddOn.cs:1101 vs 2688 | two trailing-DD implementations, undefined precedence |
| P1-19 CLOSED | over-broad | RiskGuardAddOn.cs:1085-1162, 2450 | duplicate actions; flatten ignores instrument scope |
| P1-20 CLOSED | gate bypass | TradeCopierEngine.cs:650 | sim detection by name prefix |
| P2-38 | gate bypass | McpBridgeAddOn.cs:1710, 2243, 2307 | same name-prefix hole in the strategy-deploy guard |
| P2-41 | silent overwrite | McpBridgeAddOn.cs:5126 | config POST does not merge; omitted fields reset to defaults and are written to disk |
| P1-21 | silent no-op | McpBridgeAddOn.cs:252 | copier never re-subscribes on connect |
| P1-22 | no control | TradeCopierEngine.cs:721 | market-only copies; latency/slippage fields fake |
| P1-23 CLOSED | silent fallback | TradeCopierEngine.cs:360, 397 | `Replace`-based symbol translation; 3 sizing modes unimplemented |
| P2-24 | dead safety | TradeCopierEngine.cs:165, 194, 326 | reconciler, delta clamp, quarantine, daily-loss all unwired |
| P2-25 | never fires | PropFirmProtectionSuite.cs:51 | news events only injectable from tests |
| P2-26 | doc drift | RiskGuardAddOn.md | 8 concrete claims contradicted by code |
| P2-27 | test gap | TradeCopierEngine.cs:613 | whole copy path inside `#if !TESTING`; no CI |
| P2-28 ✅ | hygiene | `addons_DONOTUSE` deleted; sync script fixed | CRLF-blind drift check; mcp copy is a submodule |
| P2-29 | maintainability | RiskGuardAddOn.cs (4,108 lines) | single file incl. 700-line WPF window |

---

## 8. Stress and adversarial test programme

The order-flood events in the live log were a deliberate operator stress test, and reading their
output found four defects in an afternoon (`P1-43`, `P1-44`, `P1-45`, `P2-46`) that months of
review and a green suite had not. That is the argument for making stress tests a standing part of
the suite rather than an ad-hoc exercise.

**The lesson from `P1-43` in particular**: the lock-scope invariant *is* machine-checked, and the
check still missed a violation, because it only ever drove two code paths. A check is only as good
as the paths driven through it. Stress tests exist to drive the paths nobody thought to drive.

### Already present
- `TestCopierGroup_GroupStressAndConcurrency` — parallel group mutation, asserts zero thread
  exceptions.
- `TestP1_10_...`, `TestP1_35_...` — lock-scope checks, but only over the sweep and FSM teardown.

### To build

| # | Stress test | Must prove | Defect it would have caught |
|---|---|---|---|
| S1 ✅ | **Order burst** — N distinct orders/sec against the rate governor | fires on *distinct order ids* at the configured threshold; one order passing Submitted→Accepted→Working counts once | `P2-46` |
| S2 ✅ | **Burst whose tripping order is a protective stop** | the stop stays working; only risk-increasing orders are cancelled | `P1-44` |
| S3 ✅ | **Flood lockout lifetime** | the lockout lapses after its configured duration and is not resurrected by a restart | `P1-45` |
| S4 ✅ | **Lock-scope sweep over every entry point** — drive `ExecuteOrderUpdate`, `ExecuteAccountItemUpdate`, position updates, grace expiry, watchdog and the sweep with the broker observer armed | **zero** broker calls while `TestIsStateLockHeld()` is true, on every path, not a hand-picked two | `P1-43` |
| S5 ✅ | **Partial-fill storm** — one trade exited in many small fills, both event orderings | exactly one consecutive-loss judgement; late fills revise rather than accumulate | `P1-16` |
| S6 ✅ | **Rapid flip loop** — long↔short repeatedly | FSM coverage never outlives its position; no stale `CoveredQuantity`; grace re-arms each leg | `P1-36`, T1 |
| S7 ✅ | **Copier fan-out under burst** — one leader, many followers, rapid entries and exits | no duplicate copies, no follower left inverted, sizing correct under concurrency | `P0-5`, `P0-6`, `P1-22` |
| S8 ✅ | **Config reload while armed and in position** | live reload does not drop FSMs, coverage or lockouts, and does not corrupt the config | `P1-39` |
| S9 ✅ | **Restart mid-trade** — kill and reload with a position open | seeded FSM matches the broker; no double-count of trades or losses; lockouts survive | `P1-15`, `P1-16` limit |

> **S1–S4 landed 2026-08-07** as `TestStress_S1toS4_OrderFloodGovernor`, and immediately caught
> all four defects (461 passed / 4 failed at baseline, 465 / 0 after). S4 currently drives
> `ExecuteOrderUpdate` only; extending it to *every* entry point is still open, and is the part
> that would stop a fourth instance of the lock-scope violation appearing somewhere else.
>
> **The first draft of these tests was vacuous and it nearly went unnoticed.** Passing `null` as
> `sender` made `ExecuteOrderUpdate` throw on `(Account)sender` inside its own `try/catch`, so
> every call was swallowed: three assertions "passed" against code that never ran, including the
> lock-scope one. Only the two assertions that expected a *positive* effect failed and gave it
> away. A stress test that drives no code is worse than no stress test, because it reports safety.
> Always confirm a stress test fails for the reason you intended before trusting a pass.

### Rules for these tests
- They are **acceptance tests for the defects above** — write each one red against current code,
  and keep it in the suite afterwards. Do not commit a stress test that has never failed.
- Drive them through the real entry points (`ExecuteOrderUpdate`, `ExecuteAccountItemUpdate`,
  `UpdatePosition`), not by calling internals directly, or they will not catch wiring defects.
- Concurrency tests must assert on an observed invariant, not merely on "no exception thrown" —
  the existing group-stress test only asserts the latter, which is why it has never caught
  anything.
