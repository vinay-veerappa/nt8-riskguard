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

### P1-77. The Consistency Rule Shield is configurable, enabled by default, and evaluated nowhere — ✅ CLOSED 2026-08-15 (session 43, §5.59: `EvaluateConsistencyCap`)

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

### P2-78. `PerInstrumentRiskConfig` carries two fields nothing reads — ✅ CLOSED 2026-08-15 (session 43, §5.60)

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

✅ **CLOSED 2026-08-15 (session 43).** Both fields deleted; `MaxContracts` is the only member of
the type and the only one anything reads. The registry note that warned about them went in the same
change — a note describing fields the config no longer has is the same defect one turn later.

---

### P2-114. Two mutation batteries stopped being evidence, in two different ways — ✅ CLOSED 2026-08-15 (session 43, §5.63)

*(found by `gh run list` after the `P2-113` push. The code it guards was already deployed and
live-validated; both failures were in the batteries, not the addon.)*

**Two unrelated causes, and each was a lesson written down earlier the same day.**

#### (a) A battery crashed printing its own output, leaving a LIVE MUTANT

`mutate_p182.py` raised `UnicodeEncodeError: 'charmap' codec can't encode characters in position
201-202` on the GitHub windows runner, **while passing locally on identical input**. A repointed
mutant description had gained a `⚠️`. It raised **between applying a mutant and restoring it**, so
everything after that point proved nothing.

⚠️ **`tools/check_batteries_pin_encoding.py` did not exist in this repo** — it lives in
`nt8-mcp-bridge`, while §0 cited it as protecting these batteries. **Fourth per-repo gate gap.**
Porting it was one `cp`, and on arrival it failed **56 subprocess captures across 29 batteries**:
this repo had never pinned *either* half, and survived only because the C# suite's output happens
to be ASCII today. One non-ASCII `Console.WriteLine` would have killed **every battery at once**.

⚠️ **The gate had only ever checked half the hazard.** Its docstring said *"every battery must pin
an explicit encoding on its subprocess captures"* and it enforced exactly that sentence. **The
sentence was the bug** — the hazard is the battery's *encoding assumptions*, of which the
subprocess capture is one surface:

| half | direction | when it fails | consequence |
|---|---|---|---|
| DECODE — `subprocess.run(capture_output=True, text=True)` | child → battery | **before** the first mutant | `stdout` is `None`; the battery dies having proven nothing |
| ENCODE — the battery's own `print()` | battery → console | **between** applying a mutant and restoring it | **a live mutant left in the working tree** |

Both are now required of **every** battery, not only of ones that currently carry a non-ASCII
character — *a conditional requirement would be satisfied by the very edit that breaks it*. A
half-pin (`encoding='utf-8'` with no `errors='replace'`) is rejected, because that shape still
crashes. ✅ Driven negative on both before being believed.

#### (b) A `mutate_ui4` mutant SURVIVED, because its subject had been fixed away

*"rules with no evaluator are omitted from each ACCOUNT's inventory"* — the per-account loop turned
into `i < 0`. It had been killed for the life of the battery **by real unevaluated rules happening
to exist**. `P1-77` + `P1-81` + `P2-113` gave every rule an evaluator, and a mutant with nothing to
corrupt survives.

⚠️ **That is §5.61's own lesson at a seventh gate, and the one instance of it I missed.** I
converted the six *tests* that scanned that population and never asked whether the *batteries* did
too. The six failed **loudly**, because each carried an explicit `expected.Count > 0`; this one went
**quiet**, and quiet is how a battery stops being evidence. **When a fix empties a population, the
mutation batteries are gates against it as well as the tests — re-run them, not just the suite.**

#### (c) A third route to the same live mutant, and it was mine

Two batteries were launched concurrently. They rewrite **the same source files**, so one's restore
overwrote the other's mid-flight state and left `snapshot.IsArmed = true` in `GuardRules.cs`. That
is [[mutation-battery-killed-leaves-a-mutant]] arriving without anyone stopping anything. **Run
batteries one at a time**, and the correct response to a battery that is mid-run is to *wait*, not
to kill it — killing it is what causes this.

**Where**: `tools/check_batteries_pin_encoding.py` (ported + extended), all 31 `mutation/mutate_*.py`,
`tests/RiskGuardAddOnTests.cs` (`TestP2_114_AnUnevaluatedRuleAppearsOnEveryAccountsRows`),
`.github/workflows/ci.yml`.

---

### P2-115. `nt_health`'s `feedConnected` is `Account.All.Count > 0` — a market-data flag that can never be false — ✅ CLOSED 2026-08-15 (session 44, §5.67)

**Where**: `nt8-mcp-bridge/addons/McpBridgeAddOn.cs:447`

```csharp
accountCount = Account.All != null ? Account.All.Count : 0;
connectedToFeed = accountCount > 0;
```

**The field has exactly ONE reachable value.** A running NT8 always reports at least the Simulator
accounts, so `feedConnected` is `true` on every call, forever, on every box. It is not a weak
measurement of the data feed; it is not a measurement of the data feed at all. It is a constant
wearing the name of the one thing an agent checks before trusting a price.

**Measured, 2026-08-15 14:20 UTC — a Friday, with the futures market OPEN:**

| what | reported |
|---|---|
| `nt_health` | `feedConnected: true` |
| `nt_quote MNQ 09-26` | last `29533.75`, time **`2026-08-07T01:45:06`**, volume `0` |
| `nt_quote NQ 09-26` | last `29532.25`, time **`2026-08-07T01:45:25`**, volume `0` |
| `nt_quote ES 09-26` | last `0`, time `0001-01-01`, volume `0` |

Eight days stale on two instruments and never subscribed on the third, while the health endpoint
reported the feed connected.

⚠️ **The CAUSE was found half an hour later and it makes this SHARPER, not weaker.** The connection
log reads `Connection status: Connected, Connection: Playback` — NT8 is on the session-42 replay
connection, **with no replay running**, which is exactly what §5.56 warned would displace Provider31.
So the box has **no tradeable market at all**: three ATM orders placed on Sim101 sat at
`OrderState.Initialized` and were never routed. And through all of that `feedConnected` said `true`.
The defect is not "the field is wrong while Provider31 is off" — it is that **the field cannot
distinguish a live feed from a dormant Playback connection, because it never looks at either.**

⚠️ **THIS DEFECT MISLED THE AGENT INVESTIGATING IT, IN WRITING, WITHIN FIVE MINUTES.** Asked whether
a Provider31 reconnection needed market data or only a broker connection, I read `feedConnected:
true` beside 90 accounts reporting `cashValue: 0` and stated that market data was connected and only
the account half was missing. The code half of that answer was right and independently sourced; the
observational half was wrong, and wrong *because* it was drawn from this field. That is the whole
consequence argument: this is the field consulted precisely when someone is about to trust a price.

**Band**: `P2`. It is a read, and a read cannot move a stop — but **weigh the quiet failure above
the loud one** (`P3-111`). A well-formed `true` is the worst possible answer here, because the
honest one is available for free and the caller has no other way to ask.

**Fix**: report what is actually known, and let it be false. `Connection.Connections` carries real
per-connection status, and the instrument subscriptions carry a last-tick time. At minimum
`feedConnected` must be capable of being `false`, and the field should be renamed or split if it
cannot be made to mean what it says — `accounts` is already reported separately one line above, so
today it is the same number twice with one of them mislabelled.

⚠️ **Second half, recorded here rather than filed separately because it is one reader's problem**:
`nt_quote` returns an eight-day-old price with **no staleness signal**. The evidence is in the
payload — `time` is right there and `volume: 0` — but nothing flags it, so a caller that reads
`last` and not `time` gets a number that looks exactly like a live one. Fixing `feedConnected`
without giving `nt_quote` a staleness flag leaves the trap one call further down.

⚠️ **Reachability is TOTAL and it is not conditional on Provider31.** With the broker reconnected
this field will still be `true` always; it will merely stop being noticeably wrong. **Do not close
this by reconnecting the feed.**

**Measured again with the BROKER CONNECTED, 2026-08-15 14:54 UTC** (operator reconnected Provider31;
market closed). `feedConnected` is still `true` — as it was with a dormant Playback connection and
no market at all. **The field did not change value when the thing it names changed completely**,
which is the cheapest possible demonstration that it measures nothing. Everything else did change:
`MNQ 09-26` went from a frozen `29533.75` to a live book at `30151.75 / 30155` on 1,925,425 volume.

#### ✅ What shipped

`addons/BridgeFeedStatus.cs` — `IsMarketDataConnected(names, providers, statuses)` over **three
plain string arrays**. The shape is the point: it names **no NinjaTrader type**, so it lands in the
set the harness can *execute* rather than the set it can only read as text. TRUE requires an entry
that is BOTH connected AND non-simulated; `Connected`, `Simulator` and `Playback` are **exact,
case-insensitive** matches; null, blank and unrecognised all fail closed; the arrays clamp to the
shortest length.

⚠️ **THE ARBITER RECOMMENDED SHIP ON A PATCH THAT WOULD NOT COMPILE.** It upheld **0 of 4** findings
— the documented pattern — and the patch contained `a.Provider?.ToString()` and
`a.Connection?.Status?.ToString()`. **`Provider` and `ConnectionStatus` are enums**, so `?.` on them
is `CS0023`; the addon already writes `account.Provider.ToString()` with no `?.` at `:1771` and
`:4590`. Every gate was green — static ok, compile ok, 314 passed, all 6 acceptance tests green,
lock-scope clean — and **none of them could see it, because `McpBridgeAddOn.cs` is in no test
build.** That is `P2-27` arriving exactly where this repo's agent-loop profile warns it will, and
`check_bridge_parses.py` says so in its own output: *"This is NOT a compile — run nt_compile before
calling a bridge change done."* Fixed by hand, along with the patch's `Print(...)`, which is
`NinjaScriptBase`'s method and not this file's convention (`NinjaTrader.Code.Output.Process`).

⚠️ **The battery went 5/10 and FOUR of the five were gaps in tests written the same hour**:
`return true` on **null** arrays (every assertion passed a real one — **an empty array is not a null
array**); a **blank provider** admitted as real; the **shortest-length clamp** removed with nothing
ragged in the suite; and a source gate asserting the class is **mentioned** rather than that its
answer is **assigned** — the third time that exact gap has been found here after `P1-105` and
`P2-109`, and the comment directly beneath it *already said* a value that is computed is not a value
that is used. The fifth was the author's: a **case-sensitive** `Contains("Connected")` mutant, which
`"Disconnected"` does not match, so it never expressed its own defect (fourth instance of *read what
a mutant DOES*). ⚠️ And the re-run left **one** survivor for the same reason — the ragged test made
*providers* the shortest array, so removing the **statuses** clamp changed nothing. **Each clamp
needs the array it guards to be the one that would overrun.** Now **10/10**.

⚠️ **Mutant 5 is the one to carry: a bare `return false`.** Every requirement in this ticket is
about a TRUE that cannot become false, so a constant `false` satisfies all of them and ships a
health endpoint reporting a permanent outage on a working box. **A status field needs both
directions, not just the one its defect was in.**

**Evidence**: bridge harness **311 → 324/0**, MCP wrapper **54/0**, `mutation/mutate_p2115.py`
**10/10** and wired into CI (7 batteries), all four bridge gates green, `nt_compile` **errorCount
0**, `deploy.py` clean.

✅ **BOTH HALVES ARE NOW MEASURED, and the negative one arrived while `F-17` was being built.**
The broker dropped on its own with the market closed, giving the discriminating reading this entry
had been unable to obtain:

| when | state of the box | reading |
|---|---|---|
| 14:20 | dormant Playback, no tradeable market | **old** code → `feedConnected: true` — the defect |
| 14:54 | live broker attached, MNQ 30151.75/30155 | **new** code → `true` — positive control |
| 16:49 | broker disconnected | **new** code → **`false`** — negative control |

`accounts: 97` was identical at all three readings, so the field moved with the connection and not
with the account count. Confirmed independently: the funded account's equity went to `0` and only
the six Simulator accounts still reported any. **The field now moves with the thing it names.**

⚠️ **The negative half was NOT obtained by planning for it.** It was refused deliberately — showing
`false` meant disconnecting the operator's live broker — and then the market closed and the box
produced the state for free. **When a measurement is blocked on an action you should not take, say
so and keep watching; the system may perform it for you.**

**Follow-up, deliberately not done here**: a `connections` detail list on the payload. It is a
contract change for every client of `/api/health` and belongs with a decision about the wrapper
schema. Also unresolved: `guarding` is character-for-character `isArmed` on
`/api/riskguard/version` — one fact under two names.

**Where**: `nt8-mcp-bridge/addons/BridgeFeedStatus.cs` (new), `addons/McpBridgeAddOn.cs`,
`tests/BridgeSourceTests.cs`, `mutation/mutate_p2115.py`, `.github/workflows/ci.yml`.

**The rest of the payload was swept before banding this, and it comes out well** — which is what
makes the one bad field worth fixing rather than distrusting the whole surface. `/api/riskguard/version`
computes `loaded`, `mode`, `isArmed` and `guarding` from the live instance (`McpBridgeAddOn.cs:483`),
and `P1-47` added the arm state there for exactly this reason. Two smaller notes, neither a defect:
`status = "ok"` is also a constant, but defensibly so — an unreachable endpoint returns no payload
at all, so the constant carries its meaning in being *received*. And `guarding` is character-for-character
the same expression as `isArmed`, so the health payload reports one fact under two names, the same
shape as `accounts` and `feedConnected` being the same number. Collapse or differentiate it when
this is fixed; do not file it separately.

---

### P2-113. The inventory reported the news events file as read by nothing, for two days after something started reading it — ✅ CLOSED 2026-08-15 (session 43, §5.61)

*(found 2026-08-15 while closing out `P1-77`/`P1-81`, by asking what the ONE remaining
`ConfiguredNotEvaluated` row on the live box actually was. Not by a test and not by CI — the suite
was green throughout, and it is green under the defect, because nothing compares a rule's stated
reason against the code it describes.)*

**What was measured**, off the deployed box, before any code was written:

```
nt_riskguard_inventory ->  "ConfiguredNotEvaluated": 97
                           [ { "rule": "News events file", "accounts": 97 } ]
```

97 rows per poll, one per account, reporting `PropFirm.LocalNewsEventsFilePath` as configured and
evaluated by nothing, with a stated reason beginning **"NO CODE READS THIS … the path is stored but
nothing ever opens it"**. `PropFirmProtectionSuite.LoadNewsEventsFromDisk` has opened it since
**`P2-25` closed in session 34** — called from `UpdateConfig`, which `McpBridgeAddOn.cs:245` calls
at startup. A second copy of the same sentence sat in the news shield's own zero-event note, which
is also operator-facing.

⚠️ **This is `F-9`'s class in the PESSIMISTIC direction, and that is not the harmless one.** Every
other ticket against this registry defends against a row reading *greener* than the truth. This one
read redder. The cost arrives by the same mechanism at one remove: a red row that is wrong is
exactly how an operator learns to discount red rows, and there were 97 of them on every poll.

⚠️ **Nothing re-reads a reason.** `UnevaluatedReason` is prose written once, at the moment a gap is
found, and it describes *the codebase* rather than the operator's box. It cannot go stale loudly. A
registry that records why a field is unevaluated inherits the obligation to notice when it becomes
evaluated, and this one had no mechanism for that at all.

**The fix is not the corrected sentence.** Deleting the false claim would have left the row
reporting nothing. What the rule reports now is the thing nobody could previously see: **whether
the operator's news file actually loaded**. Every failure in that loader is silent —

| what the operator has | what happened before | what the row says now |
|---|---|---|
| `[]` in the file | parses perfectly, loads zero events | *"loaded and is EMPTY, so the shield cannot fire"* |
| malformed JSON | swallowed by a bare `catch { }` | *"could not be read (JsonReaderException: …)"* |
| a path that does not exist | `File.Exists` false, method returns | *"the configured news events file does not exist: …"* |
| no path configured | — | *"no news events file configured"* → `Disabled`, not red |

**Weigh the quiet failure above the loud one** (§5.54, again): the empty file is the worst of the
four, because it is the only one that looks like a success at every other surface. The `catch`
stays — a bad news file must not stop the guard loading — and stops being silent.

**Three things worth reusing:**

1. **Closing the last instance of a state can disarm the machinery that reports it.** `P1-77`,
   `P1-81` and this ticket between them gave *every* registered rule an evaluator, so
   `Rules.Where(r => r.Evaluator == null)` is now empty — and `All` over an empty sequence is true.
   Six gates were written against that population, each carrying an explicit `expected.Count > 0`
   so it could not pass vacuously, and all six **failed loudly in the commit that emptied it**.
   That is the good outcome. They keep their subject and get an instance synthetically
   (`RulesPlusOneUnevaluated()`, plus a `rules` parameter on `BuildSnapshot` that production never
   passes). Deleting them would have retired six checks as a side effect of earning the right to.
2. **A test can pin a lie as firmly as it pins a truth.** `TestP186_…` *required* the shield's note
   to contain the string `"P2-25"`. That was correct when written and became a gate holding a false
   sentence in place. A note must state the **condition**, never a ticket number.
3. **An anchor that is a substring of a longer line can silently be the same anchor as another.**
   Adding a second rule reporting the same evidence count took `mutate_p182`'s
   `: R(null, null, c.NewsEventCount,` from one match to two — and revealed it had been producing a
   **byte-identical mutated file** to another entry thirty lines below since the day it was
   written. Two entries, one edit; that battery's count had overstated its coverage by one, and
   only `check_anchors.py` refusing a 2-match anchor surfaced it. Anchor on whole lines.

**Where**: `addons/GuardRules.cs` (the rule, the shield's note, the header),
`addons/PropFirmProtectionSuite.cs` (`NewsEventsLoadStatus` and the loader),
`addons/RiskGuardAddOn.cs` (the seam that carries it into the snapshot).
**Battery**: `mutation/mutate_p2113.py`.

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

### P1-81. The prop suite's `ArmedForLive` arms nothing — ✅ CLOSED 2026-08-15 (session 43, §5.59)

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

### P2-108. `NAKED_POSITION` repeats every 10 seconds on a path `P2-107` does not cover, because it is a LOG and not an action — ✅ CLOSED 2026-08-15 (session 42), reproduced AND fixed AND re-validated under Market Replay

**Reproduced with the number it was filed with**, a session later, on a different account. Position
with no stop on `Playback101`, guard in `shadow`, sampled every 30s:

| t | NAKED_POSITION | ACTION_SUPPRESSED |
|---|---|---|
| +30s | 3 | 0 |
| +60s | 6 | 0 |
| +90s | 9 | 0 |
| +120s | **12** | **0** |

⚠️ **`ACTION_SUPPRESSED = 0` is the load-bearing measurement.** It proves `P2-107`'s
`GuardActionDeduplicator` never sees this path rather than assuming it: these are `LogEvent` calls
with no action behind them, and `DispatchActions` cannot reach them.

⚠️ **THE CLASS IS BIGGER THAN THE TICKET.** The audit emits **three** findings from one loop on one
timer — `NAKED_POSITION`, `ORPHAN_STOP`, `FSM_DIVERGENCE` — all unbounded. Fixing only the measured
one would have left two identical defects one `foreach` apart. All three now route through
`AuditFindingThrottle`, and a source gate keeps them there.

**After the fix, the identical 120-second test:**

| | before | after |
|---|---|---|
| `NAKED_POSITION` | **12** | **1** |
| `AUDIT_FINDING_SUPPRESSED` | 0 | **1** |

⚠️ **AND THE RE-ARM IS THE HALF THAT MATTERS.** Fires once → announces going quiet once → silent →
**position closed → record cleared → new naked position fires again**. Without that last leg the
"fix" is just a permanently muted alarm, which is the defect inverted rather than cured.

### ⚠️ THE SUITE COULD NOT SEE THE DEFECT IN THE FIX. THE BOX COULD.

The throttle first cleared records keyed on **evaluated findings**. The audit builds those keys by
iterating an account's **open positions** — so when a naked position resolves the way it resolves
almost every time, *the position closes*, there is no position left to iterate, the key is never
evaluated, and **the record lives forever**. The alarm mutes itself permanently on the commonest
recovery path.

**Eight unit tests and 8/8 mutants passed under it** — including one that specifically asserted
"a key that was not evaluated keeps its count", which is correct for a disconnected account and
exactly backwards for a closed position. Nothing in the suite ever closed a position. It was found
by closing and re-opening one on the deployed box and watching `NAKED_POSITION` fail to return.

**The correction is scope**: clearing is keyed on the **ACCOUNT the audit examined**, not on the
individual finding. That keeps what the key scope was reaching for — a pass that examined no
accounts clears nothing, so a connection blip cannot re-admit the backlog — while making a closed
position resolve properly. Mutant 9 is that defect, and it exists because the box found it.

**Four things in the design, three of them `P2-101`/`P2-107` restated because those tickets paid
for them:** the record clears on the **CONDITION**, never on a timer; the budget is **re-read from
the mode every pass** (**1** observing, 6 acting — and *the 1 is the fix, not a tuning value*,
because in shadow the product IS the observation); the key carries the **finding type** so one
finding resolving cannot clear another's record; and **suppression is announced exactly once**, so
the operator can tell "resolved" from "still true and no longer mentioned".

**Evidence**: suite **1487 → 1541/0**; `mutate_p2108.py` **9/9**; anchors **315/0**; **30**
batteries wired; `nt_compile` **0 errors**; `sync_nt8 --verify` **ALL IN SYNC (11 files)**.
⚠️ `mutate_p330`'s ORPHAN_STOP anchor was **repointed, not retired** — `check_anchors.py` caught it
in the same commit that broke it.

⚠️ **The battery crashed printing its own output** (`⚠️` to a cp1252 console) **between applying a
mutant and restoring it, leaving a LIVE MUTANT in the tree** that `git diff` did not show because
the file was still untracked. `check_batteries_pin_encoding.py` pins the *subprocess* encoding;
this was the battery's own `stdout`. Fixed with `sys.stdout.reconfigure`. **Re-run the suite after
any battery that does not reach its restore line.**

---

<details>
<summary>The entry as originally filed, 2026-08-14</summary>

### P2-108 (as filed). `NAKED_POSITION` repeats every 10 seconds

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

</details>

---

### P1-102. There is no MCP tool to READ or CLEAR a lockout, so an account frozen by the guard cannot be recovered by the agent that is driving it — ✅ CLOSED 2026-08-15 (session 42), live-validated end to end under Market Replay

**`nt_lockout` exists**, and building it exposed a second defect in the handler it calls.

⚠️ **`HandleLockout` ANSWERED SUCCESS TO ANYTHING.** It ended with an unconditional status read,
so every unrecognised action fell through. Measured on the box before the fix:

    action:"lock"  ->  {"success":true,"action":"lock","account":"Playback101","isLockedOut":false}

The most obvious thing a caller would send, answered *"I locked it, and it is not locked"*, with
`success: true`. That is `P1-88`'s shape (an unrecognised action reported as a write) and `F-9`'s
general form (what a surface REPORTS disagreeing with what it DOES). It also **blocked this
ticket**: the MCP `action` enum is pinned to the addon's own whitelist (`P1-72`'s remedy, after
that enum drifted twice) and **there was no whitelist to pin to** — the addon accepted every
string by construction. Now an explicit `LockoutActions` array, and an unknown action is REFUSED
by name with the valid set.

⚠️ **The unlock branch returned a hard-coded `isLockedOut = false`** — a claim the unlock worked,
made without asking. It re-reads `IsAccountLocked` now and reports what it found. Third site of
*report the outcome, not the call*, after `P1-105` and `P0-104`.

⚠️ **`lock` is deliberately absent and must stay absent.** A lockout imposed by a tool has no rule
behind it and no recorded authority for `P2-92`'s clause to read.

⚠️ **THE WRAPPER HANDLER WAS BROKEN AND 53 GREEN SCHEMA TESTS COULD NOT SEE IT.** Written as
`ntFetch(path, { method, body })` — a `fetch()`-shaped options object — where the real signature is
positional `ntFetch(endpoint, method, body)`. **Schema tests validate the advertised shape, not the
call.** Caught only by driving the MCP server over stdio, the technique that validated `P2-103`.

**Live-validated** on the raw route AND through the MCP server: `lock` refused naming the valid
set; `status` a clean read; `unlock` success with `error: null` after re-reading the enforcer; a
typo account refused naming **97** accounts; an omitted account on a write that REMOVES protection
refused. Suite **302 → 310**, wrapper **51 → 53**, `nt_compile` **0 errors**.

---

<details>
<summary>The entry as originally filed, 2026-08-14</summary>

### P1-102 (as filed). There is no MCP tool to READ or CLEAR a lockout — ✅ CLOSED 2026-08-21 (session 62): `nt_lockout` is wired (`nt8-mcp-bridge/mcp/nt-mcp-server.js:314` → `/api/lockout`, schema `mcp/lib/tools.js:364`, status/unlock/reset/clear). Verified in use this session.

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

</details>

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

### P2-116. An equity rule with NO equity reading reports `EvaluatedNotEnforcing` — 88 of 89 prop accounts read exactly like the one that is actually protected — ✅ CLOSED v1.33.0 (session 50), LIVE-VALIDATED

**Where**: `addons/GuardRules.cs:265` (and the other `PerAccount` equity rules beside it)

```csharp
Evaluator = c => c.Config.PnLRules.TrailingDrawdown <= 0
    ? Off("no trailing drawdown set")
    : R(c.Account == null ? (double?)null : c.Account.AccountEquity,
        c.Config.PnLRules.TrailingDrawdown, c.Account == null ? 0 : 1)
                                            ^^^^^^^^^^^^^^^^^^^^^^^^
```

**The evidence count is the existence of an `AccountState` OBJECT, not of an equity READING.** Every
subscribed account has a state object, so every account scores evidence `1` and reports
`EvaluatedNotEnforcing` — the state that means *"this rule ran and you are within it."*

**Measured live, with Provider31 connected (market closed):**

| | |
|---|---|
| Provider31 accounts subscribed | **89** |
| …reporting any equity at all | **1** — `TAKEPROFITPRO524207503`, $50,182.75 |
| …with any per-account guard event, ever | **0** |
| `Trailing drawdown` state on all 89 | **`EvaluatedNotEnforcing`**, limit `1500` |

The funded account and a blank one are byte-identical on every equity row except the number:

```
TAKEPROFITPRO524207503  equity=50182.75   Trailing drawdown  EvaluatedNotEnforcing  cur=50182.75  limit=1500
TAKEPROFITPRO4945748    equity=0.0        Trailing drawdown  EvaluatedNotEnforcing  cur=0.0       limit=1500
```

⚠️ **The rule is structurally INCAPABLE of firing on those 88.** Trailing drawdown breaches when
`currentPnL < PeakEquity - TrailingDrawdown`. With no reading, `PeakEquity` stays `0` and the test is
`0 < -1500`, which is never true. Confirmed from the other end too: `EvaluatePnLRules` is driven by
`AccountItemUpdate`, and the audit log shows **zero per-account events for any Provider31 account** —
the enforcer has not run once.

**This is `F-9`'s class in the OPTIMISTIC direction, which is the dangerous one**, and it is on the
one surface built specifically to answer *"is the guard actually protecting me"* (`P2-103`). An
operator reading the inventory sees 89 accounts saying the same reassuring thing and **cannot tell
the one that is protected from the 88 that cannot be.**

⚠️ **The author already knew this class and applied it eight lines below.** The aggregate cap carries
`EvidenceLabel = "accounts visible to the aggregate cap"` and the comment *"An aggregate cap over
ZERO known accounts is not enforcing anything, and would otherwise read as green."* **The identical
reasoning was never carried to the per-account equity rules** — [[a-second-reader-of-the-same-state]]
at a fourth site.

✅ **THE OPERATOR HAS CONFIRMED THE POPULATION, 2026-08-15**: *"there is only one live account and
the rest 88 are dormant evals."* That settles the question the entry was filed with and it settles
the band. **No account is going unwatched** — the guard is not failing to protect 88 live accounts,
it is correctly holding no reading for 88 dormant ones. **The defect is entirely in the REPORTING**,
and it is still worth fixing for exactly the reason `F-9` was: the operator cannot tell, from the
surface built to answer it, which of the 89 identical-looking rows is the one that matters.

⚠️ **Do not let the confirmation shrink the fix.** *"They are dormant"* is true today and is a fact
about the broker's population, not about the code — the day an eval is funded, its rows look
identical to the 87 beside it and identical to what they looked like while it was dormant. The row
must say *why* it cannot evaluate, or the next reader re-derives this whole investigation.

**Band**: `P2`, now confirmed rather than assumed. The reason is the measurement above: because
`AccountItemUpdate` never fires for these accounts the enforcer never runs, so there is **no
spurious flatten** — the failure is confined to reporting. ⚠️ **Check that before down-banding it, though**: if a blank
account ever *did* receive one equity push, `PeakEquity` would jump from `0` to that value in the
same call, and the very next tick could satisfy `currentPnL < PeakEquity - 1500` legitimately. The
band rests on "the enforcer never runs", which is an observation about today, not an invariant.

**Fix**: an equity-derived rule with no equity reading has **no evidence**, so it should report
`Inert` with a note naming the condition — *"the broker reports no equity for this account, so this
rule cannot evaluate"*. `Inert` already exists for exactly this (`Blocked instruments` uses it with
`evidenceCount: 0`). Derive the display from the enforcer as `F-9` requires: the discriminator is
whether an equity reading was ever *received*, which is not the same as `equity != 0` — record
whether `AccountItemUpdate` has delivered `CashValue` for the account rather than inferring it from
the value, since a genuinely zero account and an unreported one are otherwise indistinguishable
(the `P2-41` shape: *a default and an erasure look identical*).

⚠️ **And the count is the headline, not the rule**: the operator has **89 prop accounts and the
guard holds a real equity reading for one**. Whatever the fix does to the row, that fact belongs on
the summary view, because it is the answer to the question the surface exists for.

---


---

✅ **CLOSED (session 50, v1.33.0) and live-validated on the box the defect was measured on.**
Evidence for an equity-backed rule is now an equity **READING**, not the existence of an
`AccountState` object, via one predicate `HasEquityReading` that **three** readers call:
`PnLRules.TrailingDrawdown`, `FirmMirror.TrailingDD.Amount` and
`PropFirm.EnablePeakEquityProtection`. The two accounts that were byte-identical now differ:

| | funded `…503` | dormant `…748` |
|---|---|---|
| Trailing drawdown | `EvaluatedNotEnforcing`, ev 1, cur 50182.75 | **`Inert`**, ev 0, cur `null` |
| Firm trailing drawdown | `EvaluatedNotEnforcing`, ev 1 | **`Inert`**, ev 0 |
| Peak equity giveback | `EvaluatedNotEnforcing`, ev 1 | **`Inert`**, ev 0 |
| Daily loss limit | `EvaluatedNotEnforcing` | `EvaluatedNotEnforcing` ← **scope pin holds** |

Five things in it are reusable:

⚠️ **`!= 0.0` and NOT `> 0`, and this is the fix, not a style choice.** An account whose
equity has gone NEGATIVE is reporting a reading, and it is the account most likely to be in
trouble; `> 0` switches the rule to INERT at the moment it matters most, which is a **worse**
defect than the one being fixed. One character, and a test pins it.

⚠️ **The scope was deliberately NOT widened to the realized-PnL rules**, and a green test
pins that too. `RealizedPnL` is tracked by the GUARD, where zero is a legitimate reading for a
flat account; `AccountEquity` is pushed by the BROKER, where 0.0 is what "never pushed" looks
like. Reporting a funded flat account as INERT on its daily loss limit is `F-9` in the
PESSIMISTIC direction, and an operator who learns to ignore INERT rows has lost the signal.

⚠️ **The note is PREFIXED, not replaced.** The firm row's existing text is the only place
that says whether the plan's numbers or the fallback block's are in force; trading one missing
fact for another is not a fix. Live: *"…cannot fire; resolved to plan 'TPT-50K-PRO'; its
TrailingDD numbers are in force"*.

⚠️ **`CurrentValue` is `null`, not `0.0`, when there is no reading** — a rendered
`cur=0.0` is a NUMBER and the operator reads it as a fact about the account, which is
`CopierMetric.Measured`'s distinction at a second surface.

⚠️ **The classification gate had to be TAUGHT about the new evidence kind, or it would
have fired on the fix.** `TestUi3_AnEmptyCollectionCanNeverReportEnforcing` derives
`labelled ⇔ evidence-varies`, probing only the CONFIG COLLECTIONS — so an honestly
labelled equity rule read as *"has a label but never varies"*. The probe pair now also moves
the account's equity while holding **presence** constant; probing null-vs-present instead would
drag in ten rules whose evidence genuinely IS the account's existence. **A gate can be correct
and still be aimed at the wrong variable.**

**Built with the agent-loop, and the loop's own verdict was wrong in both directions.** Its
round-1 patch was green on every gate (1936/0, all five acceptance tests) and it then ran to
`NOT_CONVERGING` as the panel churned **3 → 2 → 3** findings with **zero overlap between
consecutive rounds** — the loop correctly diagnosing a reviewer exposing new surface rather
than closing a defect. Arbitrated by hand: **two of its changes were better than my prototype**
(a `double.IsNaN` guard, and the `null` CurrentValue) and are kept; **two were regressions** —
the 350-line region re-emission stripped `⚠️` from three unrelated comments to satisfy
the ASCII gate, and it put account equity in the value column of peak-equity giveback, whose
Limit is a **PERCENT**. ⚠️ **A region the size of a whole collection initializer is the
cost of not being able to anchor two adjacent lines** — `Firm daily loss` carries a
byte-identical `EvidenceLabel` string to the rule above it, so neither is uniquely anchorable.

**Evidence**: acceptance tests written BY HAND FIRST and verified **RED at 1931/5**, green at
1941/0; battery `mutate_p2116.py` **12/12 killed, 0 survivors**; live inventory above.

### P1-117. The config window mutates the LIVE config in place, so a typo in any of thirteen boxes leaves the guard half-reconfigured while the dialog says the save failed — ✅ CLOSED 2026-08-16 (session 48), commit `c0e6556`

**Where**: `addons/RiskGuardWindow.cs`, `OnSaveConfigClick` (~`:377-424`)

```csharp
var cfg = _addOn.Config;                                              // RiskGuardAddOn.cs:41 -> `public RiskConfig Config => _config;`
cfg.Mode = _modeCombo.SelectedItem.ToString();                        // <- statement 2, ALWAYS lands
cfg.EnableWindowGate = _windowGateCheck.IsChecked ?? false;
cfg.Sizing.MaxContractsPerAccount = int.Parse(...);                   // <- 13 bare Parse calls follow
...
cfg.PnLRules.DailyLossLimit = double.Parse(...);
cfg.PnLRules.TrailingDrawdown = double.Parse(...);
...
_addOn.SaveAndReloadConfig(cfg);                                      // <- LAST statement; a throw skips it
```
```csharp
catch (Exception ex)
{
    MessageBox.Show($"Failed to parse settings: {ex.Message}", "Error", ...);
}
```

**`Config` is a live reference, not a clone** — an expression-bodied property returning the private
field. So the seventeen assignments above are not building a candidate config to validate and then
commit; **they are editing the object the guard is enforcing from, one statement at a time.**

An unparseable value in any of the thirteen text boxes throws at that line. Everything **above** it
has already been applied to the running guard. Everything **below** it, and the persist, has not.
The operator is then shown *"Failed to parse settings"* — a sentence that means *nothing happened*.

⚠️ **`Mode` is the second statement, which is what sets the band.** The ordinary operator gesture is
*"go live and set my limits"*: type the mode, type the numbers, hit save. Fat-finger one number and
**the guard is now in the new mode with the old limits, and has just told you the save failed.**
Every ordering of that gesture puts `Mode` before every limit, because the handler's order is
fixed, not the operator's.

Two things make it survivable today and neither is a property of the code: the change is **not
persisted** (`SaveAndReloadConfig` never runs), so a restart recovers it; and nothing has traded
through it. It is *in effect* on the running guard for the rest of the session.

**This is [[report-the-outcome-not-the-call]] at the config surface** — the dialog reports the
outcome of *reaching the catch*, not the outcome of the write, which is partial. And it is
`P2-41`'s shape from the other direction: that defect silently reset fields the caller never named;
this one silently applies fields the caller did name while claiming it applied none.

**Fix** — the shape matters more than the parsing:

1. **Parse into locals first, then assign.** Nothing touches `_addOn.Config` until every box has
   parsed and the whole set has validated. A failure then genuinely means *nothing happened*, which
   is what the dialog already claims.
2. **`TryParse`, not `Parse`**, so the message names the FIELD — `"Daily loss limit: 'l500' is not
   a number"` — instead of surfacing a `FormatException`'s text into a form with thirteen inputs.
   `Enum.Parse`/`int.Parse` hostility is the family `P3-111` closed at two endpoints, and this is
   the same thing at a WPF text box.
3. **Run the same value validator the HTTP route is getting** (see `P2-27` below). This window and
   `/api/riskguard/config` are **two writers to one config**, and only one of them was being given
   a validator.

⚠️ **THE VALIDATOR MUST THEREFORE LIVE IN THIS REPO, NOT IN `nt8-mcp-bridge`.** The submodule
direction is bridge → core, so a class in `nt8-mcp-bridge/addons/` is unreachable from
`RiskGuardWindow.cs` no matter that both end up in one NT8 assembly at runtime. Putting it in the
core also puts it behind **1776 executable tests and 33 batteries** instead of the bridge's
source-gate-plus-small-harness. The session-47 ticket had it on the bridge side and that was wrong
— recorded in handover §5.72.

⚠️ **Evidence is obtainable with the market shut.** This needs a text box and a typo, not a fill.

---

### P2-119. `SaveAndReloadConfig` returns `void` and swallows its own exception, so a config write that FAILED is reported to the operator as *"saved and hot-reloaded successfully"* — ✅ CLOSED in the core 2026-08-16 (session 48), commit `772ac9e`; ⚠️ the BRIDGE caller and `nt_compile` are still outstanding

**Where**: `addons/RiskGuardAddOn.cs:43`, and its three callers.

```csharp
public void SaveAndReloadConfig(RiskConfig newConfig)     // <- void
{
    lock (_stateLock)
    {
        try
        {
            string json = JsonConvert.SerializeObject(newConfig, Formatting.Indented);
            File.WriteAllText(_configFile, json);
            LoadConfig();
            LogEvent("SYSTEM", "CONFIG_SAVE", "Configuration successfully saved and reloaded from UI.");
        }
        catch (Exception ex)
        {
            LogEvent("SYSTEM", "ERROR", $"Failed to save config: {ex.Message}");   // <- and returns normally
        }
    }
}
```

```csharp
_addOn.SaveAndReloadConfig(cfg);                                          // RiskGuardWindow.cs:417
MessageBox.Show("Configuration saved and hot-reloaded successfully!", ...); // <- UNCONDITIONAL
```

**The catch swallows and the method returns normally, so the caller cannot tell.** A locked file,
a permissions failure, a full disk, or a serializer throw all produce the same thing: one `ERROR`
line in the audit log that nobody is watching, and a green dialog saying the opposite. The
`try/catch` sits *inside* `OnSaveConfigClick`'s own `try`, so even that cannot see it.

⚠️ **This is [[report-the-outcome-not-the-call]] at a third site**, and structurally identical to
`P1-105`: `positionClosed = true` recorded that control reached the line, not that anything closed.
Here the success message records that `SaveAndReloadConfig` *returned*, which it does either way.

⚠️ **AND THERE ARE THREE WRITERS, NOT TWO.** The count in `P1-117` and `P2-27` was wrong:

| caller | what it writes |
|---|---|
| `RiskGuardWindow.cs:417` | `OnSaveConfigClick` — the seventeen-assignment form save |
| `RiskGuardWindow.cs:724` | the account-exclusion toggle — **and excluding an account removes it from guarding** |
| `nt8-mcp-bridge`'s `RiskGuardConfig` route | the merged partial body |

The third one was found only by grepping for the callee rather than reasoning about the callers,
which is [[a-second-reader-of-the-same-state]] in its usual form: *count the sites before closing
the ticket.* The exclusion toggle is the interesting one — it is a protection-affecting write with
no validation and no confirmation, and it was not on anybody's list.

**Fix, and it closes three things at once.** `SaveAndReloadConfig` returns a result rather than
`void`, calls `GuardConfigEdit.Refuse` **before** it writes, and refuses rather than persisting;
the three callers report what it actually answered. That is the one choke point all three writers
share, so wiring the validator there is strictly better than wiring each caller — which is what
`P2-27` was originally scoped to do, and would have left the exclusion toggle unvalidated and the
route and the window with two copies of the same call.

⚠️ **`P2-27`'s `GuardConfigEdit` is CALLED BY NOTHING until this lands** — `P2-24`'s class,
recorded here rather than left silent. The class is built, mutated 11/11 and CI-wired; it is the
wiring that is outstanding, and this entry is it.

**Band**: `P2`. No position goes unprotected — the guard keeps running its previous config — but
the operator believes limits are in force that were never written, which is the
`configured / evaluated / enforcing` family on the surface that *sets* the config rather than the
one that reports it.

⚠️ **Evidence is obtainable with the market shut**: make `RiskGuard/config.json` read-only and
press Save.

#### CLOSING NOTES (session 48) — what the fix cost, and what it did not catch

Built by the agent loop and then corrected by hand. The loop reached a green patch at round 4
(build ok, 1833/0, all 20 acceptance tests green) and ran out of rounds on a REVISE.

⚠️ **The most dangerous defect in the reviewed patch was invisible to every gate the loop has.**
It nested `ConfigSaveResult` inside `GuardConfigEdit`. `RiskGuardWindow.cs` names the type
unqualified, and the window is `#if !TESTING` — compiled to nothing by `dotnet build`, and only
*syntax*-checked by `tools/check_window_parses.py`. So the C# build was green, 1833 tests passed,
and the first report would have been **NinjaTrader refusing the whole Custom assembly**, which
stops every addon loading, this guard included. A reviewer raised the nesting; the arbiter
dismissed it because *"the type is only used internally by the patch"* — an assertion about a
file the panel could not open. **The harness and NinjaTrader do not compile the same set of
files, and only `nt_compile` knows the difference.**

⚠️ **And the dismissal was written to the loop's settled-decision store**, where it would have
biased every future run in this repo. Corrected by hand in
`logs/agent_loop/settled_decisions.jsonl` (gitignored; original kept as
`.bak_before_correction`). A review system with a memory can remember a wrong answer — check
what it saved, not just what it said.

**What the panel DID find, independently and correctly** (findings #8/#9): the patch backfilled
a blank `Mode` and a missing `PnLRules` section from the config being *replaced*, validated
that, and then serialised the incoming one. **Validating one object and persisting another is
strictly worse than the defect being fixed** — it does not merely fail to report an outcome, it
reports a success about the wrong config. Every value validated at the chokepoint is now read
exactly as it will be written.

**The mutation battery (`mutation/mutate_p2119.py`, 11 mutants across THREE files) is where the
rest came from.** Four survived the first run and **all four were missing tests of mine**:

* **a blank `Mode`** — and writing the test that kills the mutant found *the same hole in the
  hand-written implementation*, one clause further along. `Refuse` accepts a blank mode because
  for a PARTIAL body blank means "leave it alone"; this chokepoint writes a WHOLE config, where
  blank is what gets persisted. The two callers need different answers to the same question.
* **`shadow` → `SHADOW`** — every mode pair in the acceptance tests differed under *both* an
  ordinal and a case-insensitive comparison, so nothing could tell a relaxed changed-check from
  a correct one. The discriminator did not exist until the battery demanded it.
* the first write on a box with no config; and a null config, serialised as the literal `null`.

One mutant is declared `EXPECTED SURVIVOR:` and is unkillable by construction — the reloaded
config is a JSON round trip of the caller's, so no input separates them.

⚠️ **`check_anchors.py` refused a placeholder 4-tuple of `None`s on its first opportunity**
("could not read it statically"), which is session 47's hardening working as designed.

**State**: suite **1846/0**, battery **10 killed + 1 expected**, gates **10/10**.
⚠️ **REMAINING**: the bridge's POST route still returns `success = true` regardless — it needs
the core tagged and its pin advanced — and **`nt_compile` has not run**, which given the nesting
defect is the gate that matters most here.

---

### P2-120. The bridge's `POST /api/riskguard/config` still answers `success = true` whatever the save did — the SECOND reader of an outcome the core now reports — ✅ CLOSED and LIVE-VALIDATED 2026-08-16 (session 48), `nt8-mcp-bridge` commit `63df711`

**Where**: `nt8-mcp-bridge/addons/McpBridgeAddOn.cs`, in `RiskGuardConfig(body)`:

```csharp
RiskGuardAddOn.Instance.SaveAndReloadConfig(cfg);
return new { success = true, status = "applied", config = ..., requested = req, ... };
```

**Why it is its own ID rather than a remainder of `P2-119`.** `P2-119` is CLOSED: the core now
returns a `ConfigSaveResult` and refuses what a write introduces. This is the other side of a
repo boundary — the bridge pins the core **by tag**, so it cannot even see the new return type
until the tag is cut and the pin advanced. Work that remains inside a closed entry is invisible
to every count, which is what `tools/check_next_list_ids.py` refused a draft of this handover for.

**What it costs today.** The route discards the result, so a refusal and a failed write are both
reported as `"applied"`. It is strictly better than before only in that the core now REFUSES
rather than writing a bad value — the caller is told the opposite of what happened, and
`config` (which echoes the live config) will quietly disagree with `success`. **An API that
reports the negation of its own outcome is worse than one that reports nothing**, because a
script acting on it proceeds.

**Fix**:
1. Tag the core and advance the submodule pin.
2. `var r = RiskGuardAddOn.Instance.SaveAndReloadConfig(cfg);` then `success = r.Saved`, with
   `refusal`/`error`/`warning` surfaced as their own fields. Keep echoing the resulting live
   config — that is `P2-41`'s fix and it stays.
3. Re-add the three ROUTE assertions to `nt8-mcp-bridge/tests/BridgeSourceTests.cs`. They were
   removed in session 48 because they pinned a class that moved to the core; the gap is recorded
   there in a 25-line note and this is the commit that closes it.
4. **`deploy.py` and `nt_compile`.** Not optional here: the reviewed core patch nested
   `ConfigSaveResult`, which builds green in both harnesses and fails NinjaTrader's compile,
   and `nt_compile` is the only gate that knows the difference.

⚠️ **Evidence is obtainable with the market shut** — make `RiskGuard/config.json` read-only and
POST a valid change; the reply must say `success = false`. The positive control matters as much:
a normal POST must still say `true`.

#### CLOSING NOTES — measured, both halves, with the market shut

Core pinned `v1.30.0` → **`v1.31.0`**, which is what makes `ConfigSaveResult` reachable here at
all. Then, against the running box:

```
POST {"PnLRules":{"TrailingDrawdown":0}}
  -> success false, status "refused", refusal names the field
     in text that exists only in GuardConfigEdit; live TD still 1500.0
POST {"PnLRules":{"TrailingDrawdown":1500}}      (positive control)
  -> success true, status "applied", warning null
config.json unchanged at 1500.0 after both
```

**The positive control is not optional** — a route that refused everything would satisfy the
first line on its own.

⚠️ **The route does NOT call the validator, and the plan above that said it would was wrong.**
The validator lives inside `SaveAndReloadConfig`, so all three writers get it whether they
remember to ask or not; a route-level call would have been a **fourth copy of a decision that now
has exactly one home**. What the route owns is the OUTCOME, and that is what the restored
assertions pin.

⚠️ **`nt_compile`: 0 errors** — the gate that actually mattered, since the core patch this builds
on nearly shipped a nested type that compiles green in *both* harnesses and fails NinjaTrader.
`nt_health` reports RiskGuard **1.31.0**, loaded, `shadow`, armed, guarding.

⚠️ **Five assertions replaced the nine that were removed, and the last is the load-bearing one**:
a NEGATIVE CONTROL forbidding the old unconditional `success = true, status = "applied"` literal.
Every other assertion is satisfied by a file that still contains the defect beside the fix. Driven
failing before being trusted (398/1). A first draft of another was a **tautology** — `no bare call
OR a captured call`, always true once the capture assertion passes — and was removed rather than
reworded.

---

### P1-121. The Trade Copier window shows a green `[ ENGINE: ACTIVE ]` that no input can turn red, over rows that read `Armed: LIVE` while the global copier mode is `disabled` — ✅ CLOSED 2026-08-16 (session 49)
**Where**: `addons/TradeCopierWindow.cs`, new `addons/CopierStatusView.cs`, `addons/TradeCopierEngine.cs`
**Found**: not by review and not by the suite — by the operator saying *"the copier UI does not look
like it is done"*, then reading the window against the API it is supposed to agree with.

**The defect, measured before any code was written.** `_statusText` was assigned once, in the
constructor, to the literal `"  [ ENGINE: ACTIVE ]"` in green — and never assigned again. Not on
the 2-second refresh timer, not on failure, not anywhere: `grep -n "_statusText"` returned exactly
three lines, the declaration, the construction and the `Children.Add`. **There is no input to this
program that makes that header say anything else.** Meanwhile the copier's own global mode —
`live` / `shadow` / `disabled`, which gates *every* copy at `TradeCopierEngine.cs:5385` and fails
closed on a typo — appeared in the window **zero** times, and each relationship row ended
`Armed: {(rel.ArmedForLive ? "LIVE" : "SIM")}` with no reference to it.

So the failure the operator meets is: **the copier is `disabled`, submitting nothing at all, and the
one screen built to report on it shows a green ENGINE: ACTIVE header above a list of rows each
saying `Armed: LIVE`.** Every individual widget is doing what it was written to do.

**Three producers already computed everything the window needed**, and it consumed none of them:

| Producer | What it knows | Rendered by the API | Rendered by the window |
|---|---|---|---|
| `GetCopierMode()` | the global live/shadow/disabled gate | ✅ `copierMode` + `copierModeNote` | ❌ |
| `DetectConfigConflicts()` | a follower covered by BOTH a direct relationship and a group, so copied **twice** | ✅ `configConflicts` | ❌ |
| `CopierMetric.Samples` | whether a metric was ever measured | ✅ `metricsNote` | ❌ |

> **The comment above `DetectConfigConflicts` said the conflict was exposed "for the API and the
> UI to render."** The API renders it. The UI never did. That comment was the only thing in the
> repo asserting a consumer that did not exist — [[a-comment-recording-a-defect-goes-stale]] in
> the one direction that is not about staleness: it was never true.

**Why it is `P1` and not `P3`.** It places no order and drops none. It removes the operator's
ability to *notice* that no order is being placed — and the product of a trade copier is entirely
"my follower accounts mirror my leader". Believing that while it is false is how follower accounts
silently diverge, and two of the 96 accounts on this box are funded. Weighed the way
[[weigh-the-quiet-failure-above-the-loud]] prescribes: this never throws, never logs and never
degrades. It just reads correct.

**Fixed by** the split `P2-27` has prescribed since it was filed and that
`BridgeAccountResolver`, `BridgeFlattenPlan`, `BridgeLockoutGate` and `GuardConfigEdit` have each
already proven: **every decision moved into `addons/CopierStatusView.cs`, which names no WPF type
and carries no `#if`**, so the `tests/RiskGuardTests.csproj` glob compiles it and it is executed
and mutated. The window keeps the brush mapping and nothing else. `TradeCopierWindow.cs` remains
outside the test build, so this is not tidiness — *it is the difference between having evidence
about this code and having none.*

Four things in it are worth reusing:

1. **The display is derived from the ENFORCER, never recomputed beside it.** `CopierStatusView.IsActing`
   calls `TradeCopierEngine.IsCopierActingMode` rather than comparing to `"live"` itself, and one
   test asserts they agree across `live`/`LIVE`/`shadow`/`disabled`/`liv`/`""`/`null`. This is F-9's
   finding restated — a rule's reported state had drifted from its enforced state in **both**
   directions — and the remedy is the same one. Mutant 6 reintroduces exactly that drift.
2. **A metric with no samples must not print a number.** `Latency: 0ms` is produced both by
   *nothing has filled this session* and by *a copy filled instantly*, and only the second is a
   claim about the market; `P1-22` shipped the first as if it were the second. New
   `GetRelationshipMetrics` pairs each value with its count at the grain the card renders
   (`GetSnapshot` already pairs them, but one row **per instrument**, which the window would have
   had to re-aggregate and would then be free to do differently from the engine). ⚠️ **The
   load-bearing test is the inverse** — a measured **zero** must still print as `0ms (n=3)`, or a
   `MetricText` that always says *not measured* passes the obvious test while hiding every real
   reading.
3. **A group is deliberately NOT routed through `RelationshipLine`.** A group carries no quarantine
   flag and no metrics of its own, so reusing that method means feeding it blanks — and it would
   then print *"Latency: not measured this session"* for a group whose followers are being measured
   perfectly well. **A shared function that has to be fed blanks is not shared code, it is a second
   dialect with one caller lying.**
4. **A throwing refresh now replaces the header.** The `catch` logged to `Console` and returned,
   leaving the last text on screen — on a 2-second timer, meaning a permanently failing read left
   a stale, possibly green, claim up indefinitely. The screen must never look healthier than the
   last successful read.

**Evidence**: suite **1846 → 1924 assertions / 589 declared tests**, 0 failures. Battery
`mutation/mutate_p1121.py`, **14 mutants**. ⚠️ **Mutant 1's first anchor matched TWICE** — the
`if (!IsActing(copierMode))` branch is verbatim in both `RelationshipLine` and `GroupLine` — and a
2-match anchor scores a false **SURVIVOR**, which is `[[mutation-anchors-go-stale]]` catching
itself on the first run rather than in six months.

⚠️ **What this battery cannot reach, and it is the honest limit of the ticket**: no mutant can be
placed in `TradeCopierWindow.cs`, because the harness does not compile it either — a mutant nothing
compiles is not evidence. The window is held only by the source gates in
`TestP1121_TheWindowDelegatesItsStatusTextToTheView` (paired absence + presence, per
[[a-code-move-disarms-a-source-gate]]) and by `nt_compile`.

---

### P2-123. The tab called *"Symbol & Per-Ticker Matrix"* contains no per-ticker matrix — it is a static poster that reads zero engine state, beside two dead fields — ✅ CLOSED v1.33.0 (session 50)
**Where**: `addons/TradeCopierWindow.cs:622` `CreateSymbolMatrixTab`, fields at `:186-187`

Measured, four commands, no reading required:

| Question | Answer |
|---|---|
| `TradeCopierEngine` references inside `CreateSymbolMatrixTab` | **0** |
| `PerTickerRatios` / `CustomSymbolMappings` anywhere in the window | **0** |
| Occurrences of `_ratioNqText` in the file | **1** — the declaration |
| Occurrences of `_ratioEsText` in the file | **1** — the declaration |

The tab is a hardcoded `rows[i, 0..3]` table of asset classes, mini/micro contract names and
scaling ratios, rendered as `TextBlock`s. It has no input, reads nothing, and writes nothing.
The two `TextBox` fields that would have made it editable were declared and never constructed —
**dead UI fields, which `check_no_dead_safety_machinery.py` does not cover because they are not
safety machinery** — and their names (`Nq`, `Es`) show the tab was scoped to two instruments
while the engine's `PerTickerRatios` is an arbitrary case-insensitive map.

**Why it is `P2` and not cosmetic.** `PerTickerRatios` and `CustomSymbolMappings` are real,
persisted, engine-enforced config, settable through `nt_copier_config`. An operator who sets
`{"NQ": 2, "ES": 1}` sees **no trace of it** on the screen named after it — and worse, the static
table continues asserting the default conversion, so the display actively **contradicts** the
config the copier is enforcing. That is `P1-121`'s class one tab across, and `F-9`'s in the
general form: *a surface that states behaviour it does not read.*

⚠️ The static text also presents mini↔micro conversion as clean — *"1 NQ to 10 MNQ ... across all
futures asset classes"* — with no mention of the rounding the MCP schema warns about in its own
`autoConversion` description: **with ratio 1.0 a 1-lot micro copy is DROPPED**, because 1 MNQ
translated to NQ rounds below one contract. The one place an operator goes to understand
conversion is the one place that omits how it loses a trade.

✅ **CLOSED (session 50, v1.33.0).** The tab now renders from the same `GetRelationships()`
the first tab shows, on the same 2-second timer, through `addons/CopierSymbolMatrixView.cs` —
no WPF type, no `#if`, so the harness executes it and mutants can reach it. The six dead
`TextBox` fields are **deleted, not wired**: their names scoped the tab to six instruments while
`PerTickerRatios` is an arbitrary case-insensitive map, so wiring them would have built an editor
that cannot express the config it edits. The static table survives, relabelled **REFERENCE**, with
the rounding caveat it had always omitted.

⚠️ **THE FIRST VERSION OF THIS FIX COMMITTED THE DEFECT IT WAS FIXING, and that is the
thing to carry.** `SmallestLeaderFillThatCopies` used `ceil(1/ratio)` — obviously right, and
wrong. The copy path sizes with `(int)Math.Round(...)`, and .NET rounds **midpoints TO EVEN**, so
at x0.1 a 5-lot gives `Math.Round(0.5) == 0` and is DROPPED while a **6**-lot copies. The
arithmetic said **10**; the engine says **6**. A tab telling the operator they need four more
contracts than they do is *a surface stating behaviour the engine does not perform*, which is this
entry's own title. It now **probes** with the engine's own rounding, `RoundToContracts` is
extracted so the copy path and the tab share ONE rule, and a mutant restoring the ceiling is in
the battery.

⚠️ **`ComputeEffectiveRatio` is itself a SECOND implementation of the sizing arithmetic.**
`CalculateFollowerQuantity` computes `absRatio * symbolMultiplier` itself, character for
character. They agree today and nothing structural makes them agree tomorrow — so *"the tab
derives from the enforcer"* is only true while those two do. A **conformance test** now compares
them across 24 root/quantity combinations rather than hoping, which is the same move as pinning
the NT8 stub enum against the real assembly.

Three smaller decisions worth reusing: a **zero ratio is not rendered as a number** where the
sizing mode ignores ratios (`RatioApplies` asks the MODE, never the value — `x0` would tell a
correctly configured fixed-lot operator their copier multiplies by zero); **automatic conversion
needs BOTH conditions**, the flag AND a non-matrix sizing mode, where the old poster claimed
conversion happened *"across all futures asset classes"* full stop; and **an empty config SAYS
so** and names the flat ratio in force, at severity `Info`, because *"nothing to show"* and
*"nothing is wrong"* must not look the same.

⚠️ **The tests were written AFTER the code and all passed on their first run** — the
weakest evidence position in this repo. The battery is the only thing that says they have teeth:
`mutate_p2123.py` **16/16 killed, 0 survivors**, including the mutant that restores the `ceil`
arithmetic. ⚠️ **Its first run left a live mutant in the tree** — not the battery's
fault: an orphaned `nohup` run was still going when a second was started, two batteries mutated
the same files concurrently, and one wrote the other's mutant back as "original". Caught because
a later anchor reported **0 matches**. ⚠️ **The VISUAL half is unvalidated**: nothing here
proves the tab looks right. Opening Trade Copier Manager is what would.

**Original fix note**: render the tab from `GetRelationships()` — the effective per-ticker ratio per
relationship, folded out of the same rows the first tab shows — and either wire the two fields or
delete them. Keep any static reference table clearly labelled as *reference*, separate from
configured state. Deliberately **not** folded into `P1-121`: that ticket's evidence is 14 mutants
over an extracted decision class, and bolting an unmeasured editable matrix onto the same commit
would have put a feature with no tests behind a mutation score that says nothing about it.

---

### P3-124. The mini/micro symbol table exists in FOUR places inside `TradeCopierEngine.cs`, and two of them are the sizing arithmetic written twice — OPEN, found 2026-08-16 (session 50) while giving the copier window a per-ticker tab

**Where**: `addons/TradeCopierEngine.cs` — the `TranslateSymbol` switch (`:1553-1565`), the
multiplier test inside `ComputeEffectiveRatio` (`:1500-1506`), the same multiplier test AGAIN
inside `CalculateFollowerQuantity` (`:1746-1757`), and the pairing test in the conflict detector
(`:4559-4571`).

Four copies of *"NQ/ES/YM/CL/GC/RTY are minis and MNQ/MES/MYM/MCL/MGC/M2K are their micros"*.
Adding a seventh asset class means finding all four, and nothing fails if you find three.

⚠️ **Two of the four are not a table, they are the SIZING ARITHMETIC.**
`ComputeEffectiveRatio` and `CalculateFollowerQuantity` both compute
`Math.Abs(ratio) * symbolMultiplier` from the same inputs, character for character.
`ComputeEffectiveRatio` is what the snapshot **reports** and now what the window **displays**;
`CalculateFollowerQuantity` is what the copier **sends**. **A reporter and an enforcer computing
one number twice is `F-9`'s shape**, and it is the reason `P2-123` shipped a conformance test
comparing them across 24 combinations instead of trusting the agreement.

**Why `P3` and not higher.** They agree today — measured, not assumed. The conformance test makes
a future divergence fail the build rather than reach a screen, so the remaining cost is
maintenance, not exposure. **Do not close it by deleting the test**: the test is what holds the
duplication safe, and merging the two functions is what would let it be retired.

**Fix**: give the mini/micro relation ONE definition — a root-pair table with `IsMini`,
`MicroOf`, `MiniOf` and `MultiplierFrom` — and have all four sites read it. Then fold
`CalculateFollowerQuantity`'s sizing onto `ComputeEffectiveRatio` so the number the operator is
shown is arithmetically the number that is sent, and retire the conformance test in the same
commit that makes it vacuous. ⚠️ This touches the live copy path, so it wants its own battery and
a sim round trip, which is why it was not folded into `P2-123`.

---

### P3-122. The bridge tells you an unarmed relationship *"copies to SIMULATION followers only"* while the copier is in `shadow` and copying to nothing at all — ✅ CLOSED 2026-08-16 (session 51), shipped with `P1-125`
**Where**: `nt8-mcp-bridge/addons/CopierEnforcementView.cs`, `NotEnforcingReason`

Found by comparing the two readers of the same question after building the third.
`CopierEnforcementView` (the API, `nt8-mcp-bridge`) and `CopierStatusView` (the window, this
repo) both correctly defer to `TradeCopierEngine.IsCopierActingMode` — neither keeps its own
copy of the predicate, which is `P1-100`'s lesson applied. **Their reason ORDERING differs**,
and one ordering produces a false sentence:

| enabled | armed | mode | bridge says | window says |
|---|---|---|---|---|
| ✔ | ✘ | `live` | *not ArmedForLive, so it copies to SIMULATION followers only* ✅ | `Armed: SIM` ✅ |
| ✔ | ✘ | `shadow` | *not ArmedForLive, so it copies to SIMULATION followers only* ❌ | `INERT - copier mode is 'shadow'` ✅ |

In `shadow` the copy path blocks at `TradeCopierEngine.cs:5385` **before any follower is
reached** — `COPY_BLOCKED_COPIER_SHADOW`, `continue` — so it copies to simulation followers
*too*. The bridge's sentence describes a behaviour that is not happening.

The ordering is **deliberate** and its comment says so: *"The mode is named LAST because it is
the newest reason and the one an operator will not think to check."* That reasoning is right
about which reason is most surprising and wrong about which is **binding** — when two gates are
both shut, the one to name is the one that shuts hardest, not the one that is easiest to forget.
**Rank refusal reasons by what BINDS, not by what surprises.**

**Fix**: test `copierModeIsActing` before `armedForLive` in `NotEnforcingReason`, and keep the
mode's explanatory sentence. The regression test is the row above: enabled + **not** armed +
`shadow` must not mention simulation followers.

⚠️ **Not measured live** — the mechanism is read from the copy path, not driven. Flipping the
deployed copier out of `live` is the operator's call, not a validation step, so this was filed
rather than confirmed. Banded `P3` for that reason and because `shadow` is the safe direction:
it misdescribes a state in which nothing is being sent.

**CLOSED (session 51), in `nt8-mcp-bridge/addons/CopierEnforcementView.cs`, and shipped with
`P1-125` because it had to be**: a defect in a string that nothing displays is not reachable by an
operator, so `P1-125`'s rendering of the reason is what makes this ordering matter at all.

The ordering is now **disabled > global mode > not armed**, and the two words that decide it are in
the code: rank by what **BINDS**, not by what **SURPRISES**. `isEnabled` stays first, deliberately
— it is the only term that is both binding *and* actionable on the relationship itself, and its
sentence claims no behaviour a shadow copier contradicts. That precedence is now the same one
`CopierStatusView.RelationshipLine` uses for the WPF window, so the two surfaces cannot disagree.

⚠️ **The reorder made the moved sentence LIE ABOUT ARMING, and that is the trap worth recording.**
The mode branch used to be reachable only by armed relationships and its text said so — *"the
relationship is enabled and armed, but the COPIER is in 'shadow'"*. Moving it above `armedForLive`
makes it reachable by unarmed rows too, so the unchanged string would have asserted the opposite of
the row it was explaining, **for exactly the row this ticket was filed about**. The clause is now
conditional. *Moving a branch changes the set of inputs its words have to be true for.*

⚠️ **And the other direction, which a reorder breaks in silence**: the simulation sentence is
**correct** whenever the copier IS acting, and every assertion about this defect passes if you
simply delete it. The battery's second mutant does exactly that. The positive control — unarmed +
`live` still says *"copies to SIMULATION followers only"* — is the only thing that catches it.

⚠️ **A substring test on the word `simulation` was WRONG, and it was mine.** The first draft asserted
the shadow sentence must not contain "simulation"; the new sentence contains it while *denying* it
(*"submits nothing at all — to a live follower or a simulated one alike"*), which is more useful to
the operator, not less. The assertion now pins the false CLAIM (`copies to SIMULATION`) and is
paired with a positive one (the sentence states that nothing is submitted). **When a check on
wording fails, ask whether the wording or the check is wrong.**

**Evidence**: 6 executed tests over the whole 48-combination space (2 × 2 × 2 × 6 modes), asserting
that `NotEnforcingReason` and `WhyNotEnforcing().Sentence` never disagree — one ordering, two
renderings. Battery `mutation/mutate_p1125.py` **22/22**.

⚠️ **THE REORDERED BRANCH ITSELF IS NOT LIVE-VALIDATED, and saying so is the point.** The copier was
driven into `shadow` and back for `P1-125`, and **the rows did not change**: both relationships on
this box are switched OFF, so `disabled` binds first — correctly, and by this ticket's own design —
and every row read `"the relationship is disabled."` in `live` and in `shadow` alike. The sentence
this ticket rewrote needs **one enabled relationship under a non-acting copier**, which no state on
the box currently produces. What is measured live is the ordering's FIRST rung; the rung that moved
is covered by the 48-combination test and by two mutants, and by nothing on the box.

---

### P3-118. Three readers of `Mode`, three different case rules — `Mode: "Live"` is refused as *unrecognised* by the one reader that decides arming — OPEN, found 2026-08-16 (session 48) by a test that made two other tests disagree

**Where**: `addons/RiskGuardAddOn.cs`, three places that each ask *what mode is this?*

| reader | comparison | answer for `"Live"` |
|---|---|---|
| `DefaultArmedForMode` (`:610`) | `OrdinalIgnoreCase` | matches `live` → an acting mode → comes up **disarmed** |
| `RunPreflight` check (c) (`:3857`) | `_mode != "shadow" && _mode != "live" && …` — **ordinal** | **no match → refuses to arm, "Unrecognised mode 'Live'"** |
| `IsActingMode` (`:4205`) | `_mode == "live"` — **ordinal** | no match → **not acting**, observation only |

Two more comparators exist on the same concept and both ignore case:
`TradeCopierEngine.IsRecognisedCopierMode` and the copier's own acting check.

**The behaviour is safe and the MESSAGE is the defect.** Every disagreement here fails closed — a
capitalised mode does not act, and preflight refuses to arm it — so nothing is left unprotected.
But the operator is told their mode is **unrecognised**, which is true of one `!=` and false of the
codebase: `Live` appears everywhere, `DefaultArmedForMode` recognised it a moment earlier, and the
copier would have accepted it. They will go looking for a typo they did not make.

⚠️ **Found by a test that made two OTHER tests contradict each other.** `P2-27`'s validator was
specified as case-insensitive, copied forward from a bridge draft without checking. Its acceptance
suite then demanded both *"`SHADOW` is accepted"* and *"the validator agrees with preflight on every
mode"* — and no implementation can satisfy both, because preflight refuses `SHADOW`. The agent-loop
sat at **16 of 17 green for three rounds** and ended `ARBITER_NEVER_RAN`. **The contradiction was
the finding**: an agreement test does not only catch drift, it catches a specification that
disagrees with the code it is specifying.

**Fix**: one predicate — `GuardConfigEdit.IsRecognisedGuardMode(string)` is the obvious home once
`P2-27` lands — with all three readers calling it, keyed on `OrdinalIgnoreCase` to match the two
readers that already do and the two copier comparators beside them. ⚠️ **That is a behaviour change
on the arming path** (`Mode: "Live"` would begin to arm where it now refuses), which is why it is
filed rather than folded into `P2-27`: a validator ticket must not quietly widen what preflight
accepts. Until it lands, `P2-27`'s validator is deliberately **ordinal**, so that it agrees with the
reader that decides arming, and its refusal names the case rather than claiming the mode is unknown.

**Band**: `P3`. Every reader fails closed, so no position goes unprotected; the cost is an
operator's time and a misleading sentence. ⚠️ Re-band if the one-predicate fix is taken, because at
that point the three readers stop agreeing by accident and start agreeing by construction, and a
mistake in the shared predicate reaches the arming decision.

⚠️ **Evidence is obtainable with the market shut** — it is a config string and a preflight call.

---

### P1-125. The browser UI never states the copier's GLOBAL MODE -- the one gate that decides whether any copy is submitted at all -- while the API has returned it all along; `P1-121` verbatim, at the surface the operator actually uses -- ✅ CLOSED 2026-08-16 (session 51) and live-validated

**Where**: `nt8-mcp-bridge/ui/index.html` (993 lines, served from `McpBridgeAddOn.cs:6900` as a
static asset at `http://localhost:7890/ui`)

Measured, two commands:

| Question | Answer |
|---|---|
| `copierMode` / `notEnforcingReason` / `configConflicts` in `ui/index.html` | **0** |
| the same three in `McpBridgeAddOn.cs` + `CopierEnforcementView.cs` | **21** |

⚠️ **THIS IS THE DEFECT `P1-121` CLOSED, AT A DIFFERENT SURFACE, AND IT IS THE MORE IMPORTANT
ONE.** Session 50 rebuilt the WPF `TradeCopierWindow` header so it derives from
`CopierStatusView` and goes amber on a `shadow` or `disabled` copier. The **browser UI** — which
is what the operator had open when they reported the problem — was never touched and still shows
nothing. A `disabled` copier, submitting nothing at all, renders exactly like the screenshot:
two rows, verdict `shadow`, a `Disable` button on each.

The page header reads `mode shadow · armed · cannot act`. **That is the GUARD's mode.** The
copier has its OWN mode (`live`/`shadow`/`disabled`), deliberately separate since `P3-34` so the
sim can keep copying while the guard sits in shadow — and it appears nowhere on the page. An
operator reading that header has been told about a mode, which is worse than being told nothing:
it invites the conclusion that the copier's state has been reported too.

⚠️ **The reason text is already built and already has a filed defect.** `CopierEnforcementView`
computes `notEnforcingReason`, and `P3-122` is open against its ORDERING — it can say an unarmed
relationship *"copies to SIMULATION followers only"* while the copier is in `shadow` and copying
to nothing. **A defect in a string nothing displays is not reachable by the operator**, so
`P3-122` and this entry should be closed together: rendering the reason is what makes its
ordering matter.

**Fix**: render the copier's global mode and `notEnforcingReason` severity-coloured, plus the
`configConflicts` count. ⚠️ **Put it in the SYSTEM ROW, not the Copier section header.**
[`UI_REDESIGN_DESIGN.md`](UI_REDESIGN_DESIGN.md) §4 decision 4 reserves a feed/guard/copier system
row for exactly this — *"where `P3-34`'s two-or-three-indicator problem lives"* — and the operator
confirmed §4 on 2026-08-16. Shipping it in a section header means `P2-127` moves it later. The
existing page header already shows the GUARD's mode; this is the third indicator beside it. The decision belongs in
`CopierEnforcementView` (already in the test build) and NOT in the HTML, for the same reason
`CopierStatusView` exists: `ui/index.html` is in no test build and no mutation battery can reach
it.

**CLOSED (session 51) and live-validated with the market shut.** Where each piece went, and the one
rule behind the split:

| piece | where | why there |
|---|---|---|
| severity / headline / detail | **`CopierStatusView.Describe`**, core, *unchanged* | the WPF window's producer, already mutation-covered. Reused, not re-derived |
| wire shape, `SeverityName`, the not-loaded cell | `nt8-mcp-bridge/addons/CopierEnforcementView.cs` | names no NT8 type, so the bridge harness **executes** it |
| composition | `McpBridgeAddOn.GetCopierSnapshot()` | in no test build — so it is plumbing and nothing else, pinned by a source gate |
| a colour | `ui/index.html` | in no test build and never will be, so it decides nothing |

**The load-bearing decision was to WRITE NO NEW DECISION.** `CopierStatusView.Describe` already
answers *"is the copier copying?"*, folded out of the same relationships and groups this payload's
rows come from. Writing a second answer for the browser — in the same session as `P3-122`, whose
entire content is two surfaces disagreeing about one question — would have been the seventh
instance of [[a-second-reader-of-the-same-state]] committed by the person closing the sixth.

Three things inside it are reusable:

* ⚠️ **The severity crosses the wire as a NAME, and that is not a style choice.** The rows in the
  **same payload** carry a numeric `severity` from `CopierSnapshotJson.SeverityRank` where **0 is
  the WORST**; `CopierStatusSeverity` runs the other way, `Ok=0 … Critical=3`. Two numbers with
  opposite polarity in one JSON document is a trap for whoever writes the next consumer, and the
  cost of getting it wrong is a page that paints an **ORPHAN green**. An unmapped rank reads
  `critical`, for the same reason `SeverityRank` puts an unrecognised verdict at the top.
* **The not-loaded cell is a state, not an absence.** `TradeCopierEngine.Instance` is null when the
  addon fails to load, and the header still has to say something — a blank indicator is read as
  *fine*. It reports `critical`, `isActing: false`, and says *"not the same as a copier with no
  relationships"*, which is a distinction the page already drew for the rows and not for the header.
* **The reason is rendered per ROW as a short label, with the sentence as the tooltip.** The full
  sentence is ~30 words and is *identical on every row* whenever the global mode is the cause; a
  table repeating one paragraph per row buries the row that differs, which is `P2-41`'s shape. The
  banner states it once. ⚠️ The label is **not a second decision** — `WhyNotEnforcing` returns both
  lengths from one ordering, and a test drives all 48 combinations asserting they never disagree.

**Evidence**: harness **302/56 → 444 assertions / 68 tests**, battery `mutation/mutate_p1125.py`
**22/22**, `nt_compile` **0 errors**, `deploy.py` 2 addons + the UI synced. Live, against the running
box: `system` = `{loaded: true, mode: "live", isActing: true, severity: "info", headline: "[ COPIER
LIVE - SIM ONLY ]", configConflicts: 0}` and both rows carrying `enforcing: false`,
`notEnforcingLabel: "disabled"` — text that exists only in the new classes.

✅ **The `shadow` half was measured too**, with the operator's consent: flipped to `shadow`
(`severity: "warn"`, `isActing: false`, `"[ COPIER SHADOW ]"`), then restored to `live` and
**verified by re-reading two endpoints rather than trusting the write's own answer**. ⚠️ **`disabled`
was not driven**, and neither was the mode branch of the per-row refusal — both relationships here
are switched off, so `disabled` binds first and correctly in either mode. That branch needs one
enabled relationship under a non-acting copier and stays test-only.

⚠️ **NOBODY HAS LOOKED AT THE PAGE.** The payload is measured; the rendering is not. That is exactly
the state `P1-121` and `P2-123` are in at the *other* surface, and §5.77 was written about spending
effort on a screen nobody opens. One glance closes it.

🆕 **`P3-128` was found BY the live read**, in the headline this ticket just put on screen. Filed
below.

---

### P2-126. The copier section of the browser UI implements TWO of the fourteen actions its own API supports, so the operator can toggle a relationship and nothing else -- OPEN, found 2026-08-16 (session 50), reported by the operator as "only the enable/disable buttons work"

**Where**: `nt8-mcp-bridge/ui/index.html` (the `dispatch` / `toggleRow` / `releaseRow` block,
~lines 573-611) against `McpBridgeAddOn.cs:4253` `knownActions`

Measured:

| | |
|---|---|
| actions `/api/copier/config` accepts | **14** — `get`, `get_groups`, `set`, `update`, `set_group`, `upsert_group`, `remove_group`, `delete_group`, `add_follower_to_group`, `remove_follower_from_group`, `remove`, `clear`, `delete`, `set_mode` |
| actions the UI ever dispatches | **2** — `set` and `set_group` |
| fields the UI ever sends on them | **2** — `isEnabled`, and `isQuarantined: false` |

So the operator cannot, from the page: **create** a relationship or a group, **delete** either,
add or remove a follower from a group, change **sizing mode, ratio, per-ticker ratios or symbol
mappings**, or set the **copier's global mode** — the last of which is `P3-34`'s whole point, a
feature built specifically so the mode would stop being editable only by hand in
`copier_config.json`.

⚠️ **`Release` is wired and the operator was still right.** `releaseRow` exists and posts
`isQuarantined: false`. It renders only when a row IS quarantined, and neither of the two live
rows is — so the observation *"only the enable/disable buttons work"* is exactly what the page
offers today. **Do not close this by pointing at code that cannot be reached**; that is
`configured / evaluated / enforcing` at the level of a button.

⚠️ **`quarantine` (the verb, not the release) does not exist in the addon at all** — measured, 0
occurrences of `"quarantine"`/`"unquarantine"` as actions in `McpBridgeAddOn.cs`. This is the
remains of `P1-72`'s twice-regressed advertisement. An operator can release a quarantine and
cannot impose one. Decide deliberately whether that asymmetry stays; it is defensible (the engine
imposes quarantine on measured slippage, not on opinion) but it is nowhere stated.

⚠️ **THIS IS NOT A NEW DISCOVERY AND MUST NOT BE PLANNED AS ONE.**
[`docs/UI_REDESIGN_DESIGN.md`](UI_REDESIGN_DESIGN.md) §10 item 4 already records it as
the outstanding half of the whole redesign: *"nothing on the page is EDITABLE — goal 1 of
the two ('configure both systems') is untouched."* This entry is that sentence measured.
⚠️ That line is now **partly stale**: the GUARD config became editable afterwards
(`P1-117`/`P2-119`, the `Review and save` block posting to `/api/riskguard/config`). It is
the **copier** half that is still read-only, which is why the operator hit it there.

**Fix**: needs the layout settled first, so take it WITH
`P2-127` rather than bolting controls onto the current scroll. §4 decides where each control goes: frequent actions
(arm/disarm, enable/disable, ratio) **inline on the row**, set-rarely config (symbol
mappings, per-ticker matrix, slippage thresholds) **in the inspector**. The read surface is already honest and rich;
what is missing is a write surface, and the write surface is what
`GuardConfigEdit`/`CopierRequests` exist to validate. **Every new control must dispatch through
the existing `dispatch()` chokepoint** — one place that builds a request and one that reads the
answer, including `refused`, which is the engine declining on purpose and is not an error.

---

### P2-127. The page never got section 4 of the agreed design -- the fleet/inspector split -- so everything landed as one scroll; and the obvious fix is the ONE thing that design explicitly killed -- ✅ FIXED 2026-08-18 (session 58), found 2026-08-16 (session 50), reported by the operator as "cluttered"

✅ **CLOSED 2026-08-18 (session 58) — all four slices of §4 shipped, deployed and live-validated.**
Recorded here rather than at EOF, under the ID it closes. ⚠️ **The status line above said `OPEN`
for six sessions after slice 1 landed and carried no record of slices 2–4 at all**, while the
newest "Order from here" in the handover still listed `P2-127` as *"slice 1 landed session 52; the
page does not consume it yet"* — [[closures-do-not-propagate-backwards]], again, on this entry.

| slice | what | commit |
|---|---|---|
| 1 | the fleet tree's decision class, `BridgeFleetView.cs` | `10e274c` (session 52) |
| 2 | **wiring it to the page** — split out as its own ID because it was built and served to nobody | `P2-138`, `8050ec4` |
| 3 | the inspector's three tabs, `BridgeInspectorTabs.cs`, built AND wired in one commit | `a983455` |
| 4 | the events pane and §4 decision 4's system row, `BridgeEventsView.cs` + `BridgeSystemRow.cs` | `6ab39d3` |

Measured at close: bridge harness **597 / 0** (`declared` 104), wrapper **66 / 0**, **13** mutation
batteries all wired, **174 anchors / 0 broken**, `nt_compile` **0 errors**, CI green.

**Live-validated**, which is the half slice 1's entry could not claim: the system row rendered the
guard as *"Shadow"* at rank 3 **beside** the copier at *"live, acting"* rank 1 — two different
answers to "is it on?", side by side, which is the whole point of `P3-34` and of never merging those
two cells.

⚠️ **The events pane earned its keep inside minutes and that is the finding, not the feature.**
Three defects surfaced immediately that had been sitting in a **44 MB** `interventions.jsonl`
nobody could read: `NAKED_POSITION` firing with `gap=0` (**`P2-145`**), two genuinely unprotected
positions on the FUNDED account (**`P1-146`** — since closed not-a-defect; the live-mode corollary is **`P1-151`**), and twelve dropped copier executions
(**`P2-147`**). None was caused by this work; all three were invisible before it. *A log nobody can
read is a log nobody reads.*

⚠️ **What is NOT closed, stated rather than left implied**: `ui/index.html` is still in **no test
build and no mutation battery**. Every decision in §4 lives in a compiled class for exactly that
reason — that is `P2-138`'s lesson applied — but the renderer itself is covered only by source
assertions over the file's text, and a source assertion cannot see whether the page runs. Three
separate times this session a text gate matched **a comment about its own subject** rather than the
subject. If the renderer grows logic, it needs a real harness and that gets its own ID.

🔶 **SLICE 1 LANDED (session 52): the FLEET tree's decision class**, `nt8-mcp-bridge/addons/BridgeFleetView.cs`, suite **444/15 → 467/0** across 77 tests, battery **16/16**, `nt_compile` **0 errors**, `deploy --verify` **31 files / 0 orphans**. The entry stays **OPEN** because nothing renders it yet -- the HTML, the inspector's three tabs and the events pane are still to come. Three things in it are worth carrying, and all three came from arbitrating the agent loop by hand after it returned `NOT_CONVERGING`: **one node per FOLLOWER, not per row** (a leader and a follower may hold several relationships, one per instrument, and both live rows are instrument-less -- so a per-row tree passes every test written against the box as it stands); **the order must be TOTAL** -- `List<T>.Sort` is documented UNSTABLE and `groups` is a `Dictionary` whose enumeration order is unspecified, and equal ranks are the NORMAL case here since all 95 unlinked accounts tie, so without a name tie-break the page re-orders itself between refreshes of identical data (⚠️ **the arbiter REJECTED this finding as "stable and correct"**); and ⚠️ **an INAPPLICABLE state is not an UNREADABLE one** -- the ticket was silent, so the model defaulted to fail-closed and ranked all 95 unlinked accounts WORST, which paints 95 permanent red rows. `NotApplicableRank` sits above every real rank, is explicitly temporary, and is pinned by a test so the next slice has to change it deliberately. ⚠️ **The battery went 15/15 on its first run and the sixteenth mutant is the lesson**: dropping the `Unlinked` node when it is EMPTY survived the whole suite, because every other test supplies a spare account -- *an absent node and an empty one read identically to whatever renders them.*

**Where**: `nt8-mcp-bridge/ui/index.html`

Measured:

| | |
|---|---|
| `<nav>` / `role="tab"` / `class="tab"` elements | **0** |
| top-level sections stacked on one scroll | **4** — Configuration, Copier, Accounts, "Configured, and evaluated by nothing" |
| editable config rows in the first section | **~28** |
| account rows visible by default | **7 of 97**, each expanding to **23** rule rows |
| rows on screen with every account expanded | **~190** |

⚠️ **READ [`docs/UI_REDESIGN_DESIGN.md`](UI_REDESIGN_DESIGN.md) §4 BEFORE TOUCHING THIS. THIS
ENTRY WAS FIRST FILED PROPOSING THE EXACT THING THAT DESIGN KILLED.**

§4 is titled *"Layout — one window, two panes, zero nav tabs"* and specifies:

```
┌────────────────────────────────┬──────────────────────────┐
│ FLEET (always visible)         │ INSPECTOR (selection)    │
│  ▾ Group A · leader NT_9451    │  [copier] [risk] [rare]  │
│    ├ follower_1  1.0x  ✔MATCH  │  full config for the     │
│    └ follower_2  1.0x  ⚠SHADOW │  selected entity         │
├────────────────────────────────┴──────────────────────────┤
│ EVENTS — filtered to selection                            │
└───────────────────────────────────────────────────────────┘
```

and §4.2 lists **"top-level navigation tabs"** among the things *"Killed by the operator's
constraints, **recorded so nobody re-adds them**."* The first draft of this entry re-added them,
which is precisely what that sentence exists to prevent.

**So the diagnosis is not "the page needs navigation". It is that §4 was never built.** What
landed was the read models (§10 items 2-4) rendered as stacked sections, plus an editable guard
config block that §4 never called for at the top level at all — §4 puts set-rarely config *in the
inspector* and keeps only frequent actions inline. The ~28-row `CONFIGURATION` block sitting above
the fleet is the single biggest contributor to the scroll, and it is in the wrong pane by the
design's own rules.

✅ **SETTLED BY THE OPERATOR, 2026-08-16: BUILD §4. The left-hand nav tabs are DROPPED.**
Asked to choose between the layout they had just proposed and the one they agreed on 2026-08-13,
they chose §4 — *"lets stick to §4 which is what was the original design."* **This question is
closed; do not re-open it, and do not re-derive it from the "cluttered" report.** The two options
were close enough to be confused, which is why the comparison is kept below rather than deleted:

| | left NAV TABS (the 2026-08-16 request) | FLEET pane (§4, agreed 2026-08-13) |
|---|---|---|
| what the left column lists | **sections** — Configuration, Copier, Accounts | **entities** — groups, followers, unlinked accounts |
| what selecting does | swaps which section is on screen | drives the inspector to that account's config |
| where a warning on an unselected item goes | **hidden behind a tab** | still visible in the tree, worst-first |

§4 satisfies the operator's stated goal — no single scroll, pick a thing on the left, see its
detail on the right — and does it per ACCOUNT, which is the question actually asked ("which limit
applies to this account"). Section tabs answer a question nobody asks.

### What building §4 concretely means here

| Region | Contents | Source today |
|---|---|---|
| **FLEET**, left, always visible | groups with followers nested; *"Unlinked accounts"* below; sorted **worst-first** | the existing `ACCOUNTS` section + `/api/copier/snapshot` rows, re-grouped |
| **INSPECTOR**, right, follows selection | the selected entity's full config. **The only tabs in the app live here**: `[copier] [risk] [rare]` | the existing `CONFIGURATION` block, **moved off the top level** |
| **EVENTS**, bottom | filtered to the selection | SSE already exists (§10 item 3) |
| **inline on each row** | the frequent actions only: arm/disarm, enable/disable, ratio | today's two toggles, extended by `P2-126` |

⚠️ **Moving the `CONFIGURATION` block is the de-cluttering.** It is ~28 rows at the top level and
§4 puts set-rarely config in the inspector. Nothing else on the page accounts for the scroll the
operator reported.

🔶 **SLICE 2 LANDED (session 55): the tree is WIRED and rendering** — `P2-138`, the wiring slice
this entry never filed. Re-verified against the deployed box **2026-08-17 (session 56)**:
`GET /api/copier/snapshot` on `localhost:7890` returns **10 969 bytes** with a `fleet` array the
page renders — one `group` node (`Sim101`, rank 5) holding two `disabled` followers, and an
`unlinked` node (rank 6, `NotApplicableRank`) holding the rest. `#config` now lives inside
`#inspector`, so the ~28 config rows are off the top level.

🔶 **SLICE 3 LANDED (session 56): the INSPECTOR'S THREE TABS** — `addons/BridgeInspectorTabs.cs` in
`nt8-mcp-bridge`, served by a new `GET /api/ui/inspector` route and rendered by the page. Bridge
harness **506 → 542 / 0** across 93 declared tests, battery `mutate_p2127tabs.py` **8 mutants**.
**Live-validated on the deployed box**, which is the part that matters:

| tab | badge | rank |
|---|---|---|
| copier | `Severity 5 (2)` | 5 |
| **risk** | **`Inert (559)`** | **1** |
| rare | `No conflicts (0)` | 5 |

…and in the page's DOM: three tabs in §4's order, the risk tab amber **without being clicked**,
`#config`/`#content` hidden behind their tabs, clicking swaps panes, and selecting `Sim-ORB` in the
fleet tree narrows the risk badge **`Inert (559)` → `Inert (3)`**.

⚠️ **`Inert (559)` IS THE WHOLE POINT AND IT VINDICATES THE MEASUREMENT ABOVE.** `unevaluatedRules`
— the field this page was built to surface — is **empty** on this box, so a strip folding it would
render three clean tabs over 559 rules that cannot fire.

⚠️ **THE PANEL'S ONE GOOD FINDING, AND THE FIRST IMPLEMENTATION SHIPPED THE DEFECT.** A rare tab with
zero config conflicts folded `BridgeFleetView.WorstOf(new int[0])`, which returns `UnknownRank` —
and `UnknownRank == WorstRank` — so it rendered as the **worst item on the always-visible strip while
its own badge read "No conflicts"**. A surface whose report contradicts its rank, in the direction
that teaches an operator to discount the strip. Fixed with a named `CleanRank` (5, above every real
severity and below `NotApplicableRank`). `WorstOf`'s pessimistic empty answer is right for a set that
could not be READ; zero conflicts is a set that WAS read and was empty.
[[an-inapplicable-state-is-not-unreadable]]. The loop ended `MAX_ROUNDS_EXHAUSTED` and **four of the
five upheld findings failed** — #1 claimed `Inert` ranked *better* than `EvaluatedNotEnforcing`,
having read the lower-is-worse scale backwards.

⚠️ **THE ROUTE IS GATED AT THE SOURCE FOR *SERVING* THE CLASS, BECAUSE `P2-138` WAS THE OPPOSITE.**
`McpBridgeAddOn.cs` is the one bridge source the test project cannot compile, so
`TestP2127_TheRouteServesTheTabsAndDecidesNothing` asserts it calls `Build`, `RuleRowsFromInventory`
and `RowsFromSnapshot` — and, as negative controls, that it assigns **no** rank, names **no** tab id
and **re-sorts nothing**. Anything that file decides is untestable by construction. **The wiring
landed in the same commit as the class**, deliberately.

⚠️ **THE BATTERY FOUND A REAL TEST GAP, NOT A CODE DEFECT:** 6/8 first run, both survivors being
states this class **cannot read** — an unrecognised state and an empty one — which no test exercised,
so mutants making them read as CLEAN survived a green suite. That is the fail-OPEN direction. Closed
by `TestP2127_AnUnreadableRuleStateRanksWorstNotBest`.

**What is still missing from §4 is the events pane and §4 decision 4's system row.**

⚠️ **THE TABS ARE THE REMAINING DE-CLUTTERING, and the payload for them is now MEASURED** — do not
design them from the shape of the code. Session 56, from the running bridge:

| source | measured |
|---|---|
| `GET /api/riskguard/inventory` | **549 271 bytes**, `mode: shadow`, `isArmed: true`, **97** accounts × **23** rules = **2 231** rule rows |
| rule `state` histogram | `EvaluatedNotEnforcing` **1 129** · `Inert` **559** · `Disabled` **543** |
| `unevaluatedRules` | **0** — so on a box with accounts loaded, **`Inert` is the worst state that exists**, and it is the one a tab would hide |
| `GET /api/copier/snapshot` `system` | `mode: live`, `isActing: true`, `severity: warn`, `[ COPIER LIVE - NOTHING ENABLED ]` |
| `GET /api/riskguard/config` | 7 276 bytes, 17 config keys |

⚠️ **So the tab strip's badge must fold `Inert`, not `ConfiguredNotEvaluated`.** The state this page
was built to make unmissable is empty on the live box while **559 rules are `Inert`** — a strip that
watches only `unevaluatedRules` would render three clean tabs over the exact condition the hazard
note below is about. Fold from the **2 231 detail rows**, never from a counter (`F-9`, `P2-103`).

⚠️ An unknown endpoint answers **HTTP 500 with a stack trace** naming the absolute source path,
rather than 404. Seen while measuring the above (`/api/riskguard/state` does not exist; the routes
are `riskguard/config`, `riskguard/inventory`, `riskguard/version`). Localhost and behind the Bearer
token, so it is small — **it gets its own ID when it is taken**, and it is not folded in here.

⚠️ **`P1-125` HAS A DESIGNATED HOME IN §4 AND IT IS NOT THE COPIER SECTION HEADER.** §4 decision 4:
*"Selecting nothing shows the system row (feed / guard / copier) — which is where `P3-34`'s
two-or-three-indicator problem lives."* The copier's global mode belongs in that system row,
beside the feed and the guard, because the operator's confusion is precisely that the page shows
**one** mode and they read it as covering both. `P1-125` can still ship before the layout — it is
independent — but put it where §4 will keep it, not somewhere the restructure has to move it from.

⚠️ **Whichever wins, the hiding hazard is the same and is the reason §4.2 killed tabs.** This
page's value is that `INERT`, `ConfiguredNotEvaluated` and a non-acting copier are visible without
being looked for — `GuardSnapshot.UnevaluatedRules` exists precisely so a box with no accounts
loaded cannot render a clean, empty, reassuring page. Anything that puts a section behind a click
must carry that section's worst state into the always-visible column, folded out of the same
payload the section renders and never from its own counters (`F-9`; `P2-103` recounts from the
detail rows for this reason).

⚠️ **`ui/index.html` is in NO test build and NO mutation battery**, exactly like
`TradeCopierWindow.cs`, and §11's second open question already asks whether `P2-27` should be
closed first for this reason. Move the decisions — which badge, which severity, what the tree
contains — into a class the harness compiles, the way `CopierStatusView` and
`CopierSymbolMatrixView` do for the WPF window. Otherwise this grows a third untested surface,
and it will be the one the operator actually uses.

---

### P3-128. With every relationship switched OFF, the copier headline reads `[ COPIER LIVE - SIM ONLY ]` and says copies *"reach simulation followers only"* — nothing is copied at all — ✅ CLOSED v1.34.0 (session 51) and live-validated

**Where**: `addons/CopierStatusView.cs` (**this repo**), `Headline`

Measured on the box, verbatim, seconds after `P1-125` shipped:

```json
"headline": "[ COPIER LIVE - SIM ONLY ]",
"detail":   "2 relationships, 0 enabled. Nothing is armed for live, so copies reach
             simulation followers only and a live follower is refused."
```

Both relationships are **disabled**. Nothing reaches a simulation follower, or any other kind.
The detail line even carries the contradicting number — *"0 enabled"* — in its own first clause.

`Headline`'s ladder is `unrecognised mode > not acting > total == 0 > all quarantined > some
quarantined > armed == 0 > armed`. There is **no rung for `enabled == 0`**, so a copier with
relationships that are all switched off falls into the `armed == 0` rung, whose sentence is written
for a *different* state: enabled relationships that are not armed for live.

⚠️ **This is `P3-122` in the other class, filed the same day `P3-122` was closed.** Same shape
exactly: a sentence that is true of a neighbouring state, describing a behaviour that is not
happening, in the direction that reassures — *"copies reach simulation followers"* invites the
reader to believe copying is occurring somewhere safe. **Two readers, one question, and fixing the
ordering in one of them did not fix the other.** Count the sites.

⚠️ **And the severity is `Info`, so the page renders it in grey.** A copier that copies nothing
while its rows are all off is at least the same `Warn` as a `shadow` copier: both are *configured
to do something they are not doing*, which is `CopierStatusSeverity.Warn`'s own definition.

**Fix**: a rung for `total > 0 && enabled == 0` above the `armed == 0` one — *"[ COPIER LIVE -
NOTHING ENABLED ]"*, `Warn`, detail naming the count. ⚠️ Note `quarantined >= enabled` on the rung
above is already `0 >= 0` for this state and only escapes because `quarantined > 0` is tested
first; a new rung must go **below** the quarantine rungs, or an all-quarantined copier stops
reporting quarantine.

**Band**: `P3`. Nothing is unprotected — the copier genuinely submits nothing — and the operator's
own rows say `disabled` beside it. The cost is a headline that contradicts its own detail line on
the surface they were just given.

⚠️ **Evidence is obtainable with the market shut** — it is the box's current state, so the
regression is confirmable by reading `/api/copier/snapshot` before and after. It is a **core**
change, so it needs a tag and a vendored-pin bump in `nt8-mcp-bridge`, which is the only reason it
was not folded into `P1-125`.

**CLOSED v1.34.0, the same evening it was filed, and live-validated on the state that produced it.**
One rung in `Headline`, `total > 0 && enabled == 0`, reading `[ COPIER LIVE - NOTHING ENABLED ]` at
`Warn`.

**Placement was the whole of the ticket.** It sits BELOW both quarantine rungs and above
`armed == 0`. Above them, `quarantined >= enabled` is `1 >= 0` for an all-quarantined,
all-disabled copier, so the new rung would have swallowed the quarantine report — and quarantine
ranks first deliberately, because it is the one state the operator did not choose.

⚠️ **`Warn`, not `Info`, and that is not a cosmetic call.** The browser page renders `info` in the
same grey as a healthy copier and `warn` in amber. Reporting this state as `Info` is how it sat
unnoticed on a page whose whole claim is that a non-acting copier is visible without being looked
for.

⚠️ **The negative control is the load-bearing test**, and it was green before and after: an
**ENABLED**, unarmed relationship still reads `SIM ONLY` and still says "simulation", because that
state really does copy to simulation followers only. **A rung keyed on `armed == 0` instead of
`enabled == 0` passes all six red assertions and deletes the state it is imitating** — `enabled`
and `armed` are different counters and conflating them is the entire defect.

**Evidence**: six acceptance tests written FIRST and watched failing at **2012 passed / 6 failed**,
with the failure output reproducing the live payload verbatim; **2018 / 0** after. Implemented by
**agent-loop at HEAD** (past `v0.6.7`) — APPROVE in round 1, both reviewers, 11.0s of model time,
patch applied unchanged. `nt_compile` **0 errors**, `deploy --verify` **30 files / 0 orphans**.
Live, immediately after deploy:

```
[ COPIER LIVE - NOTHING ENABLED ]   severity: warn
Every relationship is switched off, so nothing is copied. 2 relationships, 0 enabled.
```

⚠️ **The GROUP half is covered by the same rung and by its own test, but is NOT live-validated** —
this box has no copier groups configured, so the state cannot be produced here. `Describe` folds
group followers into the same `enabled` counter, which is why one rung serves both; a fix reading
only the relationship list fails that test.

---

### P2-129. Three lists name the copier's actions, the two that are DECLARED agree exactly, and the one that RUNS refused `set_mode` — so the copier's global gate was unreachable through the tool that advertises it — ✅ CLOSED 2026-08-16 (session 51) and live-validated

**Where**: `nt8-mcp-bridge/mcp/lib/copier-config-request.js`, `buildCopierConfigRequest`

**Found by trying to use it.** Session 51 needed to flip the copier to `shadow` to validate
`P1-125`'s amber header. The obvious call failed:

```
nt_copier_config action=set_mode copierMode=shadow
  -> unknown action 'set_mode'. Known actions: get, get_groups, set, update, remove,
     clear, delete, quarantine, unquarantine, set_group, ...
```

Measured, by extracting each list from its own source rather than reading them:

| list | contains `set_mode`? |
|---|---|
| the tool SCHEMA's `action.enum` (`mcp/lib/tools.js`) — what is advertised | **yes** |
| the addon's `knownActions` (`McpBridgeAddOn.cs`) — what is implemented | **yes** |
| `buildCopierConfigRequest`'s three `Set`s — **what actually runs** | **NO** |

The first two agree **exactly, 14 for 14**, and `tool-schema.test.js` proves it in both
directions. **The refusal came from the untested middle.** `quarantine`/`unquarantine` in that
message are correct — they are this wrapper's own aliases, translated to `set` + `isQuarantined`,
which is `P1-72`'s fix working.

⚠️ **THE LESSON IS THE GATE'S REGION, AND IT IS THIS PROJECT'S MOST REPEATED ONE.** The agreement
test is the right idea aimed at the wrong pair: it compares what each end **DECLARES** and cannot
see the translation between them. Its own doc comment even states the failure mode — *"a wrapper
that does not name the action cannot reach it"* — while checking a list that names it. **A test
that both halves declare the same thing is not a test that the path between them works.** Same
family as `check_anchors` skipping 18 anchors it could not parse, `check_bridge_parses` reading 2
files of 6, and `check_ci_runs_every_battery` matching a comment: *state the region a check
inspects.*

⚠️ **And it is `P1-72` inverted.** That defect advertised an action nothing implemented; this one
refused an action **both** ends implemented. The pin written for `P1-72` extracts the addon's real
whitelist — the right instinct — and still could not see this, because it never asked the builder.

**Fix**: a `GLOBAL_WRITES` set, because `set_mode` is the first action that names **no
relationship** — routing it through the relationship branch would demand a leader and a follower,
naming a scope this action does not have (it changes what *every* relationship does). The mode
VALUE is deliberately not validated in the wrapper: the addon owns which modes exist and fails
closed, and a second list here is how `P3-111`'s hand-typed `period` enum came to forbid twelve
values the addon serves.

**The regression test drives the BUILDER**, not the schema: every action extracted from the addon's
own source must be buildable, *and* what the builder SENDS must itself be an action the addon
knows. Plus the refusal message must list every action accepted — `set_mode` was missing from the
accepted set and from that message for exactly as long, and a refusal naming an incomplete menu
sends the caller to another tool.

**Evidence**: wrapper suite **63 → 66 tests**, and the three new ones were **watched failing**
against the unfixed builder (3 failed / 63 passed) before the fix made them green. ⚠️ **Live-
validated by driving the MCP server over stdio** — a running client keeps the old module, so
`tools/call` against a freshly spawned server is the only end-to-end proof. It was called with
`copierMode: "definitely_not_a_mode"` **on purpose**: the request reached the addon, which refused
it with `applied: false, copierMode: "live"`, proving reachability **while changing nothing**.

**Band**: `P2`. Nothing is unsafe — the wrapper failed closed, loudly, and the mode stayed
reachable by `curl`, the browser UI and the NT8 window. The cost is that the copier's global gate,
the one `P1-125` had just made visible, could not be operated from the agent surface that
advertises it.

---

### P1-130. The ATM breakeven and trailing stops NEVER move: the writer demands `OrderState.Working` while a resting stop sits in `Accepted` — the reader in the same class already knows better — ✅ FIXED 2026-08-16 (session 51) and live-validated, ⚠️ but the feature is still NOT proven end-to-end

🔶 **SESSION 52, ON A REAL BROKER: the bounded-retry half is now LIVE-VALIDATED and the remaining gap has a name.** Driven on the funded 50K (Provider31): exactly **three** `ATM_STOP_ORDER_NOT_FOUND` attempts and then **`ATM_STOP_MOVE_ABANDONED`, which had NEVER fired before** (0 occurrences in the whole log until 19:56:03). ⚠️ **But the stop still did not move, for a DIFFERENT reason — filed as `P1-133`: the lookup keys on the GUID NT8 assigns at submission, and a real broker REPLACES `Order.OrderId` with its own id.** So this entry's fix was correct and its validation was worthless in the same breath: `Sim101` is the only account where the identity test can pass, because the Simulator never re-ids an order. ⚠️ **Also measured: on the real connection the resting stop is `Working`, not `Accepted`** — the state this ticket was filed about is the *Simulator's* behaviour, so the defect this entry fixed would not have bitten here at all. **The fix and its validation shared one blind spot.**

**Where**: `addons/DynamicAtmManager.cs`, `ModifyStopPrice` (`:742`)

**MEASURED LIVE at the Sunday 2026-08-16 open on Sim101 / MNQ SEP26**, which is the whole reason
the runbook item existed:

| | |
|---|---|
| entry filled | **30185.25**, long 1 |
| stop placed | **30175.25** (40 ticks), `DrawdownShield`, BE trigger **12t**, offset **2t** |
| price reached | **30199.5** — **+57 ticks**, nearly 5× the trigger |
| stop after 230s | **30175.25 — UNMOVED** |
| `nt_atm_bracket_status` | `breakevenTriggered: false` |
| `ATM_STOP_ORDER_NOT_FOUND` | **55 lines, one every 5 seconds** |

**The loop RUNS, the trigger FIRES, the arithmetic is RIGHT, and the write fails.** The log names
the correct target price:

```
no WORKING stop order with id '802abaf811e9442c8d7c58c301884a4f' on 'Sim101',
so the move to 30185.75 was not requested. The position may be unprotected.
```

`30185.75` is exactly entry + 2 ticks. Every computation in the chain is correct. **And that order
id existed the whole time** — `/api/orders` showed it as `Stop_21ea2a85`, `StopMarket`,
`stopPrice: 30175.25`, state **`Accepted`**.

⚠️ **`ModifyStopPrice` matches `order.OrderState == OrderState.Working` and nothing else**, and on
this connection a resting stop **never occupies that state**. `P3-110` measured precisely this fact
on 2026-08-14 — *"a `StopMarket` rests in **`Accepted`** — not `TriggerPending`"* — and the panic
flatten learned it. This writer never did.

⚠️ **THE SAME CLASS ALREADY CONTAINS THE RIGHT ANSWER, TWICE.** This is
[[a-second-reader-of-the-same-state]] inside one file:

| site | test | finds the resting stop? |
|---|---|---|
| `MonitorTickCore` `:623` (is the entry still alive?) | `Working \|\| Submitted \|\| Accepted` | ✅ |
| `ReconcileStopFromBroker` `:818` (**the reader of this very order**) | `RiskGuardAddOn.OccupiesSlot(o.OrderState)` | ✅ |
| `ModifyStopPrice` `:742` (**the writer of this very order**) | `== OrderState.Working` | ❌ |

`OccupiesSlot` is the guard's own shared predicate and `Classify(Accepted)` returns
`OrderLiveness.Working`, so the codebase has one correct definition, uses it to READ the order, and
hand-rolls a narrower one to WRITE it. **The reader and the writer of a single order disagree about
whether it exists.**

**Scope: this is not only breakeven.** All three stop-move sites — breakeven (`:657`, `:689`) and
**trailing** (`:702`) — funnel through `RequestStopMove` → `ModifyStopPrice`. **No ATM stop
advances, ever, on this connection.**

⚠️ **AND THE BOUNDED RETRY CANNOT REACH ITS BOUND.** `RequestStopMove` checks
`bracket.StopModifyAttempts >= MaxStopModifyAttempts` and has an `ATM_STOP_MOVE_ABANDONED` event
for giving up — but on the not-found path it does `if (!ModifyStopPrice(...)) return false;`
**without incrementing the counter**, so the cap is unreachable and the retry runs every 5 seconds
for the life of the position. Measured: **55 lines and still counting when the position was
flattened.** That is [[a-retry-that-cannot-exit]] and *an alarm that is always on is off*, at a
third site after `P2-107` and `P2-108`.

⚠️ **The message is also wrong in the reassuring direction's opposite**: *"The position may be
unprotected"* is **false here** — the original 40-tick stop is resting and working perfectly. The
position is protected, it is merely not being ADVANCED. A risk surface that cries unprotected at a
protected position is the `P3-122`/`P3-128` family again, and it trains the operator to discount
the one line that will matter.

**Fix**: `ModifyStopPrice` uses `RiskGuardAddOn.OccupiesSlot(order.OrderState)` — the predicate its
own reader uses, ten lines away — and `RequestStopMove` increments `StopModifyAttempts` on **every**
failed request, not only on provider refusals, so the abandon cap is reachable. Correct the message
to say what is true: the stop was not MOVED and remains at its current price.

⚠️ **The regression test must be the STATE, not the move.** A test that asserts "the stop moves"
passes against a stub that reports `Working`; the defect only exists because the live provider
reports `Accepted`. Drive `ModifyStopPrice` across **every** state `OccupiesSlot` admits — this is
exactly [[test-doubles-are-not-evidence]], and the NT8 stub has already hidden one live `P0` by
omitting 6 of 16 `OrderState`s.

**Band**: `P1`. It fails in the safe direction — the initial stop stays exactly where it was placed,
so no position is naked — but **every risk-reduction feature of the ATM system is inert**, silently,
on the live path, while `nt_atm_bracket_status` reports `breakevenTriggered: false` to anyone who
looks and nothing at all to anyone who does not. An operator running `DrawdownShield` believes their
stop went to breakeven at +12 ticks. It did not, and it never will.

**FIXED AND RE-DRIVEN ON THE SAME BOX, 40 MINUTES LATER, WITH THE MARKET STILL OPEN.** A second
`DrawdownShield` bracket, breakeven trigger dropped to 2 ticks so the WRITE path is exercised
regardless of where price drifts (the trigger value was never what was under test):

| | before the fix | **after** |
|---|---|---|
| `ATM_STOP_ORDER_NOT_FOUND` | **55**, one per 5s, unbounded | **0** |
| `ATM_STOP_MOVE_REQUESTED` | **never possible** | **3** |
| retry | unbounded | **stopped at 3 of 3** |

`ATM_STOP_MOVE_REQUESTED: a1934749: breakeven trigger reached -- requested stop 30183.5 ->
30193.75` is a line the old code **could not emit**, because it never got past the lookup. The
writer now finds a stop resting in `Accepted` and asks the broker to move it.

⚠️ **AND THE FEATURE STILL DOES NOT WORK, FOR THE NEXT REASON DOWN — say this plainly.** The
provider then **ignored the change**:

```
ATM_STOP_CHANGE_IGNORED  a1934749: requested stop 30193.75 but the provider holds 30183.5
                         (attempt 1 of 3). Treating the BROKER's price as the truth.
```

That is `P0-63`'s known behaviour, already detected and handled — the reconciler takes the broker's
price as truth, exactly as designed. **So the breakeven stop still did not move on Sim101.** What
changed is which link fails: from *"we never asked"* to *"we asked and the Simulator declined"*.

⚠️ **AND AN ALTERNATIVE READING MUST BE RECORDED RATHER THAN DISMISSED.** It is possible NT8
refuses to modify an order that has not reached `Working`, in which case the original
`== OrderState.Working` test was defensive rather than wrong, and the right fix is to wait for
`Working` or to cancel/replace. Tonight cannot distinguish the two: the Simulator ignores stop
changes generally (`P0-63`), so a refusal proves nothing about the state. **The evidence for the
change is that the request is now MADE and bounded; the evidence that a stop physically MOVES needs
a non-Simulator account.** Do not record this as "breakeven works".

⚠️ **`ATM_STOP_MOVE_ABANDONED` did NOT fire.** The retry stopped after three attempts because the
reconciler's own counter reached the cap and the trigger stopped re-requesting — not because the
give-up branch announced itself. **The announcement is still unvalidated**, and a give-up that
never speaks is the shape `P2-101` was filed under. Worth one directed test.

⚠️ **`P2-112` is CLOSED and was not wrong** — it made this loop RUN, and this defect is what the
running loop then hit. It is the exact remainder its own closure flagged as unmeasured: *"the
stop-MOVE half"*. **A confirmation run found a P1 the suite could not.**

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

⚠️ **UPDATE 2026-08-16 (session 47) — the paragraph above is superseded, and the trap it predicted
FIRED on the first run.** A profile now exists (`nt8-mcp-bridge/agent/nt8_bridge.py`, added with
the `v1.28.0` pin), written the only way it can be honest: its module docstring leads with *"the
one thing to know about this repo: `addons/McpBridgeAddOn.cs` IS IN NO TEST BUILD… `[test] ok` here
proves much less than it does in the core repo,"* and it directs every ticket to move logic into an
executable `Bridge*.cs`. That is the `P2-27` pattern stated as a profile rule.

**It was then run, and the prediction cashed out exactly.** The `P2-27` config-validator ticket
produced a patch that reported `[compile] ok — build succeeded` and `[test] ok — all 9 acceptance
tests green`, and **it would not have compiled inside NT8**: the route half read
`cfg.TrailingDrawdown`, a property `RiskConfig` does not have. Both gates were *true* and both were
*structurally blind to the changed line*, because `BridgeTests.csproj` sets
`EnableDefaultCompileItems=false` and does not include the file that was edited.

**What stopped it was not the profile and not the gates.** One panel reviewer filed the missing
property as a BLOCKER; the arbiter dismissed it and recommended SHIP; agent-loop `v0.6.3`'s rule —
*an arbiter may not recommend SHIP while a BLOCKER stands dismissed* — ended the run `ESCALATED`,
which is not promotable, so nothing was applied. Hand-arbitrated and the blocker held. Full record
in handover §5.72.

**So the profile is usable and its green is still not evidence.** Read it as: the loop can be run
here, the ladder's *lower* rungs (static, lock-scope, the executable `Bridge*.cs` half) are real,
and the build/test rungs are a source gate wearing a compiler's name. Until `McpBridgeAddOn.cs` is
in a test build, **the only thing that compiles it is `nt_compile` against a running NT8** — which
is also the only place a mistake is invisible (a broken Custom assembly keeps running the last good
one). Every bridge ticket must end with an `nt_compile`.

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

### P2-38. The strategy-deploy guard has P1-20's name-prefix hole too — CLOSED 2026-08-07 (⚠️ the classifier was WIDENED to `Provider.Playback` on 2026-08-15 — see the note at the end of this entry, and `mutate_p238.py`, which did not exist until then)
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

**⚠️ WIDENED 2026-08-15 (session 42): `Provider.Playback` now also classifies as non-live.**

Market Replay is how the position-dependent tickets (`P1-102`, `P2-108`, and `P1-106`'s
unvalidated half) get driven with the market shut, and `Playback101` reports
`provider: "Playback"`, so it was classifying as **LIVE** — every replay order would have needed
`confirmLive: true`.

**This REVERSED a decision the code itself had recorded**, and the reversal is written into the
doc comment rather than applied quietly. The original note read *"Playback is deliberately NOT
exempt — it costs nothing to arm a relationship for a playback run, and guessing wrong in the
other direction costs money."* The first clause is true about the **copier**, which is the only
caller that sentence considered. It is not the only caller: `McpBridgeAddOn` asks this question on
the **order-placement** path, where the cost is not "arm a relationship" but an operator and an
agent pressing `confirmLive: true` on every replay order — **rehearsing, against an account that
cannot lose a cent, the exact reflex that is the last thing between a careless call and the funded
50K. A safety flag you press a hundred times a weekend is not a safety flag.**

⚠️ **This is NOT the defect this entry is about.** `P2-38` was `Name.StartsWith("Sim")` — a
**user-chosen string** read as a fact about money, which is why "SimpsonFund" got through. This is
an **exact match on a platform enum**: `Provider.Playback` is NinjaTrader's own statement that the
account replays recorded data and settles nothing. Widening a name test and adding a second exact
enum value are different acts. Everything else still fails closed: null, unset, and anything not
positively identified stays live.

⚠️ **AND NO BATTERY COVERED THIS PREDICATE AT ALL.** 27 batteries and not one mutated
`IsSimulationAccount` — the single switch deciding whether an account can lose real money, which
had already had a real defect in it. Its `P2-38` fix shipped with tests and **no mutants**. The
riskiest predicate in the repo was the least mutated (`P2-27`'s shape). `mutation/mutate_p238.py`
now exists: **5/5**. ⚠️ **Mutant 3 is the one to know** — widened to "anything that is not
NinjaTrader", so Rithmic and InteractiveBrokers classify as simulated. **Every positive assertion
still passes under it**; only the negative half catches it, and it fails 5 of them.
*A classifier that says "simulated" to everything passes every positive test ever written for it.*

**Live-validated**: `nt_place_order` on `Playback101` with `confirmLive` **omitted** was
`status: submitted` (it was refused as live before), then cancelled; `/api/orders?account=Playback101`
and `/api/positions` both read `[]` afterwards. Suite **1482 → 1487/0**, `nt_compile` **0 errors**.


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

**Step 1 of the remainder landed 2026-08-15 (session 45).** The 26 independent top-level
types that sat at the bottom of the file — `GuardActionType`, `GuardAction`, `AccountState`,
`PositionState`, `PositionGuardFsm`, `PersistedStateData` and the config DTOs — moved to
`addons/RiskGuardModels.cs` (942 lines). **`RiskGuardAddOn.cs` 6,502 → 5,612.** Same operation
as the window: independent types, so no `partial` keyword and no member reshuffled.

⚠️ **THE PREDICTED BLAST RADIUS WAS REAL AND THE GATE CAUGHT ALL OF IT.** `check_anchors.py`
reported **6 broken anchors** across three batteries the moment the move landed — the config
defaults (`StopAttachSeconds`, `OnMissing`, `MinShadowSessions`) and two persisted-DTO fields
had moved out from under `mutate_p184`, `mutate_p292` and `mutate_p2101`. All six were
**repointed, never retired**: the subject is unchanged and the defect each defends is the same.

⚠️ **AND AN ANCHOR THAT RESOLVES IS NOT A MUTANT THAT DIES.** `check_anchors.py` asks whether
the BATTERY can find its target, which is a different question from whether the TEST can kill
it — that distinction is what let `mutate_p187`'s WarnOnly mutant survive silently last time.
So all three batteries were **re-run**, not merely re-checked: `p184` no survivors, `p292` no
survivors, `p2101` every mutant dead except the one declared unreachable, surviving exactly as
declared.

⚠️ **Two of the three batteries were SINGLE-FILE** (3-tuples with one implicit path) and had
nowhere to say which file a mutant targets. They are 4-tuples now, the shape `mutate_p184.py`
already used, because the alternative is a battery that GUESSES which of two files holds an
anchor — and a gate that guesses is the thing this repo keeps catching.

Live: `nt_compile` **errorCount 0**, `sync_nt8.py --verify` **ALL IN SYNC (13 files)**, and the
running guard read back **shadow / armed / 97 accounts / 2,231 rule rows / 0 Enforcing**.

**Remainder (still NOT done)**: splitting `RiskGuardAddOn` itself into
`{Core,Fsm,Rules,Actions,FirmMirror,Persistence}` partials. That is a genuinely different change —
it moves members of one class rather than relocating independent types — and it would break far
more than one anchor. The tooling to do it safely now exists and is proven (`check_anchors.py` +
`AllAddonCode()` + the batteries). Optionally port `scripts/complexity_audit.py` as a CI metric.

---

### P2-112. `DynamicAtmManager.MonitorTick` fails open with no dispatcher — the ATM breakeven loop silently never runs — ✅ CLOSED 2026-08-15 (session 44, v1.29.0, §5.64)

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

#### ✅ What shipped, and the three things in it worth reusing

**The `#if` SHRANK; it did not move.** `TryMarshal` is a `Func<Action, bool>` whose contract is
*"true if I have taken ownership and will run this on the UI thread; false if there is no
dispatcher and YOU must run it."* Only the WPF lookup is behind the directive. The control flow —
marshal if you can, otherwise do the work here, and say so once — is compiled into **both** builds,
and the tests drive both branches through the seam. **This was not cosmetic: it is why the defect
lasted.** The whole dispatch decision had been behind `#if TESTING`, so the ten existing ATM tests
drove `MonitorTickCore()`, a body the shipped assembly does not contain, and the branch holding the
defect existed in **no test build at all**.

**The tests reach the real private `MonitorTick` by REFLECTION, deliberately.** A `#if TESTING`
entry point would have been a second door production never takes — which is precisely the
arrangement that hid this. `MonitorTickForTest()` already existed and is exactly that shape; it
stays for the P0-67 tests, but nothing new was built on it.

**There was nothing to marshal TO, and that settles the design.** `Application.Current == null`
means the process has no WPF application object and therefore no UI thread anywhere, so
*"marshal only the `Account.Change()`"* — this entry's own suggested remedy, written before the
code was read — is not implementable. The choice is between running the sweep on the timer thread
and not running it, and not running it is the defect. It is also safe in the way that matters: the
race worth fearing is with a **UI-thread** broker call, and on this path no UI thread exists to
make one.

✅ **REACHABILITY IS NOW MEASURED, and it was the half of this entry nobody had done.**
`ATM_MONITOR_NO_DISPATCHER` appears **0 times in the whole of `interventions.jsonl`** after
deploying v1.29.0 and driving the monitor. With the NT8 GUI running, `Application.Current` is
non-null, the dispatcher path is taken, and the fallback never fires — so the defect was **latent,
not active**, confirmed by observation rather than assumed. That is what the `P2` band rested on and
it had never been checked.

✅ **And the sweep demonstrably RUNS on the deployed build.** A `DrawdownShield` bracket placed on
Sim101 came back `"Bracket registered for breakeven/trailing monitoring"` and was **gone from
`nt_atm_bracket_status` thirty seconds later**, with nothing else having touched it. The only code
that removes a bracket is `MonitorTickCore`'s `toRemove` path, so the 5-second timer fired and the
sweep executed.

⚠️ **WHAT WAS *NOT* VALIDATED, stated plainly: the breakeven stop MOVE.** The entry never filled —
all three orders sat at `OrderState.Initialized` — because **NT8 is connected to `Playback` with no
replay running**, which is the session-42 replay connection §5.56 warned would displace Provider31.
So `Account.Change()`, the call site whose semantics made this entry defer in the first place, is
**still unexercised on this path**. **Say which half was measured; do not let one green stand for
both** (`P1-106`'s rule). To finish it: start a replay (or reconnect Provider31), place the same
`breakevenTriggerTicks: 0` bracket, and read `ATM_STOP_MOVE_REQUESTED` → `ATM_STOP_MOVE_CONFIRMED`
or `ATM_STOP_CHANGE_IGNORED`.

⚠️ **A 0-tick breakeven trigger is the technique worth keeping**: `ShouldTriggerBreakeven` is
`ticksGain >= BreakevenTriggerTicks`, so `0` fires on the first sweep at the fill price. That makes
the breakeven path drivable **without a moving market** — the blocker this entry recorded for a
month was never really the market, it was the *fill*.

⚠️ **THE REVIEW PANEL UPHELD THREE FINDINGS AND ONLY ONE WAS REAL — but that one was real, and I
had missed it.** The announcement flag was instance-scoped while the message it guards says *"once
per session"*, which today is true only by leaning on the `Lazy<>` singleton three hundred lines
up: an invariant enforced somewhere else, which is how a log line starts describing something it
did not observe. Now `static`, driven negative before being believed (with an instance field a
second manager announces again and the test reports `got 2`). The other two were wrong in an
instructive way — one claimed the tests never drive the production dispatcher branch, having read
the addon and **not the test file**; the other recommended *"fail safe (disable the monitor)"*,
which **is `return;`, the defect itself**, and rested on a race requiring a UI thread that this
path exists precisely because there isn't one. **The panel's value here was one finding in three,
and the loop's own rounds 3 and 4 acting on the other two made the patch worse** — round 3 reverted
the entire region and regressed 3 tests. `MAX_ROUNDS_EXHAUSTED` exported round 2, the last candidate
that passed every gate, which is the harness working: *arbitrate by hand; it does not mean the
patch is bad.*

⚠️ **AND THE BATTERY CAUGHT ITS AUTHOR AGAIN, for the third recorded time.** A mutant flipping
`TryMarshal`'s null branch to `return true` survived all 1722 tests — not a coverage gap, but
**unkillable by construction**: it lives behind `#else`, which no test build compiles. **Read what a
mutant DOES before calling it a missing test** (`P1-99`, then `P3-111`, now this). Covered instead
by a **labelled source gate**, plus `nt_compile` — and the label matters, because a source gate
proves less and the four lines it guards can never be executed by any test.
`TestP2_112_TheProductionMarshalReportsFailureWhenThereIsNoDispatcher` strips comments before
searching, because the prose above the seam explains `return false` and **a gate its own
documentation can satisfy is not a gate**.

⚠️ **`tools/check_expected_survivors.py` fired on this battery's first draft.** I hand-rolled the
expected-survivor bookkeeping instead of calling `_battery.finish(survivors, MUTANTS)`, which is the
one definition that reads expectations out of `MUTANTS` itself and fails in both directions. A
second implementation of a verdict is a second thing to drift.

**Evidence**: suite **1705 → 1722/0** (+5 tests); `mutation/mutate_p2112.py` **8/8 with 1 declared
survivor**; `check_anchors.py` **334/0**; all seven gates green; 32 batteries wired into CI;
`nt_compile` **errorCount 0**; `sync_nt8.py --verify` clean. The `P1-13` whole-tree gate is
**unexempted again** — its own second assertion, that the allowance was still needed, failed in the
same commit the defect did, which is the both-directions construction working exactly as designed.

**Where**: `addons/DynamicAtmManager.cs`, `tests/RiskGuardAddOnTests.cs` (4 new tests + the
un-exempted `TestP1_13_...`), `mutation/mutate_p2112.py`, `.github/workflows/ci.yml`.

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

---

### P1-131. The bridge hand-rolls its own order-liveness list, disagrees with the core's shared classifier in BOTH directions, and that count is what decides whether a disconnect would strand you — OPEN, found 2026-08-16 (session 52) by reading live state during market hours

**Where**: `nt8-mcp-bridge/addons/McpBridgeAddOn.cs` — `OccupiesSlotForBridge` (2 call sites) and
the inline filter in `GetOrders`.

**Measured live**, Sunday session, while the funded 50K account held a real position:

```
nt_connection      TPT   openPositions: 1   workingOrders: 7
nt_orders(funded)  4 orders, all state "Working"     <- genuinely live, correctly counted
nt_orders(Sim101)  3 orders, all state "CancelPending", filled 0, no position
```

**Three of the seven "working orders" are cancelling and cannot fill.** They had been in
`CancelPending` for roughly five hours.

**The core already decided this question and wrote down why.** `RiskGuardAddOn.Classify`:

```csharp
// A cancel is in flight. It still occupies its slot at the broker, so
// cancelling again is noise -- but it must NOT be counted as coverage,
// which is precisely what `!IsTerminal` used to do (P0-60).
case OrderState.CancelSubmitted:
case OrderState.CancelPending:
    return OrderLiveness.Departing;
```

and `OccupiesSlot` = `Working | Changing | Inert | Indeterminate`, which **excludes `Departing`**.
The bridge's list is written out by hand and includes `CancelPending`:

```csharp
private static bool OccupiesSlotForBridge(OrderState s)
{
    return s == OrderState.Working || s == OrderState.Accepted
        || s == OrderState.Submitted || s == OrderState.TriggerPending
        || s == OrderState.ChangePending || s == OrderState.CancelPending
        || s == OrderState.PartFilled;
}
```

⚠️ **It is wrong in BOTH directions**, which is `F-9` and `P1-100`'s shape exactly — and the
reason is the same in all three: **nothing ever compared the two answers.**

| | core `OccupiesSlot` | `OccupiesSlotForBridge` | |
|---|---|---|---|
| `CancelPending` | **no** | **yes** | counted today, measured, ×3 |
| `CancelSubmitted` | no | no | ⚠️ same handshake as the row above, opposite treatment |
| `Initialized` | **yes** | **no** | live order, invisible |
| `AcceptedByRisk` | **yes** | **no** | live order, invisible |
| `ChangeSubmitted` | **yes** | **no** | ⚠️ `ChangePending` IS in the list; its twin is not |
| `Suspended` | **yes** | **no** | present but dormant, invisible |
| `Unknown` | **yes** | **no** | ⚠️ the state you least want to disconnect under |

**Why this is a `P1` and not a display nit**: `workingOrders` is not only rendered — it is passed
straight to `BridgeConnectionPlan.WouldStrand(openPositions, workingOrders, ...)`, the predicate
that **refuses a disconnect** on the grounds that orders *"stay live at the broker and can be
neither moved nor cancelled from here"*. So the false-negative half means **a disconnect is
PERMITTED while a protective stop rests in a state the bridge does not recognise** — and the
false-positive half means the refusal you *do* get may be citing orders that are already leaving.
Today's refusal of a TPT disconnect would be justified entirely by three dead Sim101 orders.

⚠️ **And there is a THIRD definition of the same question in the same file.** `GetOrders` filters
with `order.OrderState == OrderState.Filled || order.OrderState == OrderState.Cancelled` — which
omits **`Rejected`**, the third terminal state, so a rejected order is served as an active order by
the endpoint whose description says "active/working". One question, three hand-rolled answers, one
repo. `P1-90` was this shape across six sites.

**Fix**: one predicate, extracted to its own file so the harness can EXECUTE it — the
`CopierEnforcementView` / `BridgeFlattenPlan` trade. It cannot take `OrderState` (an NT8 type), so
it takes the state NAME and the call sites pass `o.OrderState.ToString()`. Then all three sites
call it, and a source gate pins that no fourth list appears. ⚠️ **The states must be derived from
the core's own classifier rather than re-typed**, or this is the same defect with a newer list:
the point is not that the bridge's list is short, it is that it is a SECOND list.

⚠️ **The severity direction is not symmetric and the fix must not "simplify" it**: counting a
departing order costs a refused disconnect, and missing a live one costs a stranded stop. When in
doubt the predicate says YES — which is what the core's `Indeterminate` → `OccupiesSlot` already
encodes for `Unknown`.

**Not reproduced, and deliberately not claimed**: nothing here has been measured stranding a real
order. The false-positive half is measured; the false-negative half is derived from the two lists
and is the reason for the band. Say which half was measured.

---

### P2-132. In `shadow`, the rule inventory cannot distinguish a rule that JUST FIRED from one that has never fired — measured on the funded account while `MAX_SIZE_BREACH` was live — OPEN, found 2026-08-16 (session 52)

**Where**: `nt8-riskguard/addons/GuardRules.cs` (the `Max contracts per account` / `Max contracts
aggregate` evaluators) and the `state` vocabulary the inventory reports.

**Measured live**, Sunday session, on `TAKEPROFITPRO524207503` — the funded 50K TPT PRO:

```
nt_positions        MNQ SEP26  Long  11        <- cap is 10
interventions.jsonl 23:40:52Z  SHADOW_LOCKOUT  TAKEPROFITPRO524207503
                    "Rule MAX_SIZE_BREACH recorded a shadow-only lockout observation"
nt_riskguard_inventory --account TAKEPROFITPRO524207503:
    { "name": "Max contracts per account", "state": "EvaluatedNotEnforcing",
      "currentValue": null, "limit": 10, "evidenceCount": 1, "note": null }
```

**The enforcer fired at the exact second the 10-lot filled. The reporter shows `null`.**

Two separate halves, and the second is the larger one.

**(a) The sizing evaluators hardcode a null `currentValue`** while the enforcer reads the position
every sweep (`RiskGuardAddOn.cs`: `if (pos.Quantity > limit)`):

```csharp
Evaluator = c => c.Config.Sizing.MaxContractsPerAccount <= 0
    ? ...
    : R(null, c.Config.Sizing.MaxContractsPerAccount, c.Account == null ? 0 : 1)
```

⚠️ **This is inconsistent within one view**, which is what makes it misleading rather than merely
sparse: `Daily loss limit` reports `-101.25` against `-1000`, `Max trades per session` reports
`4` against `8`, `Max consecutive losses` reports `5` against `3`. Three rules tell you where you
stand and the sizing ones do not — and the sizing one was the one in breach. `F-9`'s remedy
applies unchanged: **derive the display FROM the enforcer**, which already computes `pos.Quantity`.

**(b) `EvaluatedNotEnforcing` is doing two jobs and the operator cannot separate them.** In
`shadow` NOTHING is `Enforcing` — correctly, since nothing acts. So a rule that has never come
close and a rule that **breached ninety seconds ago and recorded a lockout** render identically.
`evidenceCount` does not separate them either (both `1`).

⚠️ **The consequence is not cosmetic, and it is aimed at the next thing the operator will do.**
The account carries `isLockedOut: true` right now — a shadow-authority lockout that does not bind
(`P2-92`, working as designed). **The moment the guard is armed to `live`, that account stops
trading.** The per-account field is in the payload, so a careful reader can find it; the per-RULE
view, which is where you would look to ask *which* rule, says nothing. This is the same family as
[[configured-evaluated-enforcing]]: *what a rule REPORTS can disagree with what it DOES*, and here
it disagrees in the reassuring direction.

**Fix sketch**: (a) pass the enforcer's own `pos.Quantity` (the max across the account's non-flat
positions, and the aggregate across accounts for the `Aggregate` row) as `currentValue`; (b) add a
BREACHED signal folded out of the same comparison the enforcer makes — not a sixth state, since
`Enforcing` vs `EvaluatedNotEnforcing` is about *authority* and this is about *the value* — plus
the timestamp of the last firing, so "never fired" and "fired a minute ago" are different answers.
⚠️ **Recount it from the rule rows rather than adding a counter** (`P2-103`'s rule, and `F-9` was
a drifting counter).

⚠️ **A negative control is mandatory here** ([[detector-needs-a-negative-test]]): a BREACHED flag
that is true whenever a limit exists would pass every positive test. The 96 accounts holding
nothing must report it false in the same sweep that reports this one true.

**What is NOT claimed**: the guard behaved correctly throughout. It detected the breach, recorded
the lockout, and declined to flatten because it is in `shadow`. This entry is about the READ
surface only.

#### ⚠️ P1-131 CORRECTED, same session, before any code was written

The entry above was filed against the wrong reference predicate, and the correction is the most
useful thing in it. **`OccupiesSlot` is not the right answer to borrow**, because it is not the
same question. Its own doc comment:

```
/// "Is there already an order here, so I must not create a second one?"
/// True for anything the broker still holds. Answering this wrongly with NO is
/// what produces two protective legs behind one position.
```

It excludes `Departing` **deliberately**: once a cancel is in flight you *should* be free to place
the replacement leg. `WouldStrand` asks something else entirely — *"if I sever this connection
now, is there anything at the broker I will no longer be able to manage?"* — and for that question
**a cancel stuck in flight is the strongest possible YES**. The three Sim101 orders measured today
had been `CancelPending` for about five hours; an assessment built on `OccupiesSlot` would have
discarded exactly those.

**So the bridge including `CancelPending` is CORRECT, and the "false positive" half of the entry
above is withdrawn.** What remains is the false-negative half, which is the dangerous one and is
larger than first stated. The stranding question is **`!IsTerminal`** — everything the broker still
holds — and the bridge's list omits **six** non-terminal states:

| omitted state | | |
|---|---|---|
| `Initialized` | live | |
| `AcceptedByRisk` | live | |
| `ChangeSubmitted` | live | ⚠️ `ChangePending` IS in the list; its twin is not |
| `CancelSubmitted` | live | ⚠️ `CancelPending` IS in the list; its twin is not |
| `Suspended` | present but dormant | |
| `Unknown` | unreadable | ⚠️ the state you least want to disconnect under |

**Every omission is in the direction that PERMITS a disconnect.** And the two twin-state
asymmetries are the tell that the list was written by remembering states rather than by deriving
them — each handshake has two halves and one half of each was recalled.

**Revised fix**: the predicate is `!IsTerminal(state)` — `Filled`, `Cancelled`, `Rejected` are the
only NOs — which also fixes `GetOrders`, whose inline filter is the same question minus `Rejected`.
One definition, both sites, and an unrecognised state name answers **YES** (fail-safe: assess the
disconnect as if something is there).

⚠️ **THE GENERAL LESSON, and it is the reusable half.** "Reuse the shared predicate instead of
hand-rolling one" is right only when it is the same QUESTION. This core already knows that — it
carries three predicates over one enum (`OccupiesSlot`, `ProvidesCoverage`, `AcceptsModification`)
and the third's comment opens *"The third question, added 2026-08-10 after a live trade"*. **This
is the fourth**, and naming the bridge's copy `OccupiesSlotForBridge` is what disguised it: the
name claims it is the core's predicate with a suffix, so nobody asked which question it answers.
The defect is not that it duplicated a definition — it is that it duplicated a NAME across two
questions. **Name a predicate after its question, not after the file it came from.**

**Band unchanged at P1**, but for one reason instead of two: a disconnect permitted while a
protective order rests in a state the bridge cannot see.

---

### P1-133. The ATM manager looks its own stop up by an id the BROKER replaces, so breakeven and trailing can never work on any live account — the Simulator is the only place they have ever worked — ✅ CLOSED 2026-08-17 (session 52), found live on the funded 50K

**Where**: `nt8-riskguard/addons/DynamicAtmManager.cs` — `ActiveBracket.StopOrderId` and every lookup
keyed on it (`ModifyStopPrice`, `ReconcileStopFromBroker`).

**Measured live** on `TAKEPROFITPRO524207503` (Provider31, funded 50K), 1 MNQ, `DrawdownShield`,
2-tick trigger:

```
nt_place_atm_order ->  stopOrderId: "f953ea2b50bb43759747e0cb6beab2cc"     <- a GUID
nt_orders          ->  name "Stop_15bc730b", orderId: "613562531447"       <- the BROKER's id

19:55:48/53/58  ATM_STOP_ORDER_NOT_FOUND
   "no order with id 'f953ea2b50bb43759747e0cb6beab2cc' is on
    'TAKEPROFITPRO524207503' at all, so the move to 30216.5 was not requested"
```

**The order was sitting right there, `Working`, at the price the bracket recorded.** The arithmetic
was right too — `30216.5` is exactly entry `30216.25` + the 1-tick offset. The *identity* is wrong:
NT8 assigns a GUID at submission and **replaces `Order.OrderId` with the broker's id once the
broker accepts**. The manager stores the GUID at placement and searches by it forever after.

⚠️ **THIS IS WHY IT HAS ALWAYS PASSED ON `Sim101`.** The NT8 Simulator never re-ids an order, so
the GUID keeps matching — measured in the same session, Sim101 orders carry
`"orderId": "2f515ed0f89e4ab08f549fa356614236"`, still a GUID, while every order on the real
connection carries a numeric broker id. **The one account where the feature works is the one
account whose behaviour is not the product.** [[test-doubles-are-not-evidence]] with the double
being a whole live provider.

⚠️ **AND IT IS THE SECOND HALF OF `P1-130`, WHICH I CLOSED AS "the write fails".** That ticket
fixed the *state* test (`Working` vs `Accepted`) and was validated on Sim101 — the only place the
*identity* test could pass. **The fix and its validation shared the same blind spot.** `P1-130`'s
own entry says the feature "is still NOT proven end-to-end"; this is what was hiding in that gap.

**Fix**: do not key on `OrderId` at all. `Order` identity survives re-id — hold the `Order`
reference the placer already has, or match on `Order.Name` (`Stop_<bracketId>`), which this system
sets itself and the broker does not touch. ⚠️ **Whatever is chosen must be verified against a
non-Simulator account**, because that is precisely the axis on which every existing test agrees
and reality does not.

#### ⚠️ THE REST OF THIS ADDON ALREADY KNEW, IN WRITING, IN THREE PLACES — swept 2026-08-16

The class sweep was run before writing any code, and it did not find a widespread habit. It found
the opposite, which is worse: **every other module that keys an order got this right, on purpose,
with a comment explaining why, and `DynamicAtmManager` is the sole holdout.**

| Site | What it does | Its own words |
|---|---|---|
| `RiskGuardModels.cs:492` | FSM tracks `_recognizedStops` as `List<Order>` | *"NT8 Order.OrderId is NOT unique and can change over the order's lifetime … Track recognised stops by the Order object reference, not by id string."* |
| `TradeCopierEngine.cs:4477` | `OrderReferenceComparer : IEqualityComparer<Order>` keys `_pendingCopies` | *"**`Order.OrderId` must not be used as a key**… Keying on the id here would mis-attribute a fill… **and no test would catch it, because the test stub hands out a stable GUID per order.**"* |
| `CopierReconciler.cs:647` | reference identity again | *"Reference identity, not `Order.OrderId`."* |
| `McpBridgeAddOn.cs:2683` | the bridge's order lookup | tolerant three-way: `o.OrderId == key \|\| o.Name == key \|\| o.Id.ToString() == key` |

So the fix is **well-precedented rather than novel**: `OrderReferenceComparer` exists, is tested,
and states the rule. This is not a new convention to introduce, it is one module to bring into
line — which also means the ticket should be small and the review should be about the *sites*, not
the approach.

⚠️ **`DynamicAtmManager` has FOUR id-keyed lookups, not the one the summary above names**:
`:622` (`o.OrderId == bracket.EntryOrderId`), `:742` and `:758` (both inside `ModifyStopPrice`),
and `:861` (`o.OrderId == bracket.StopOrderId`, the reconcile path). Fixing only the one the live
run happened to exercise would leave breakeven working and the entry-detection and reconcile paths
still broken on exactly the same accounts. **Count the sites before closing the ticket**
([[a-second-reader-of-the-same-state]]).

⚠️ **And the existing warnings UNDERSTATE the mechanism.** All three say the id "can change over
the order's lifetime (historical→live transition)" — a rare edge. What was measured is not rare and
not that: **the broker replaces the id on ACCEPT, on every order, on every real connection.** The
comments are right about the rule and wrong about how often it bites, and being right about a rule
for an under-stated reason is how a fourth module comes to think it is exempt. The copier's comment
is the one that names the real trap — *"no test would catch it, because the test stub hands out a
stable GUID per order"* — which is [[test-doubles-are-not-evidence]] written down, unread, two
years before it cost us a safety feature.

**Regression test**: the stub must hand out an id that CHANGES on accept, at least for one order —
otherwise the suite continues to model the one broker whose behaviour is not the product. A test
that passes under both a stable and a re-issued id is not evidence about either.

---

#### ✅ CLOSED 2026-08-17 (session 52) — five sites, and the fifth is the one grep does not find

`addons/AtmOrderIdentity.cs` is now the ONE definition of what a bracket's legs are called and the
only place one is looked up. **Names, not reference identity** — the copier's `OrderReferenceComparer`
is the stronger tool and the wrong one here, because `ActiveBracket` is serialised into the bridge's
API payload and an `Order` reference cannot go in it. The three `…OrderId` fields stay, as REPORTING
fields, and now say so at the declaration.

⚠️ **FIVE sites, not the four the sweep counted.** The fifth is `RequestStopMove`, which *passes*
`bracket.StopOrderId` into `ModifyStopPrice` and compares nothing — so a grep for `OrderId ==` finds
four and misses the one that feeds them all. It cost four agent-loop rounds: the ticket granted the
callee whose signature changed and not its caller, and the model produced the identical 21
regressions four times because the line it needed was outside every editable region. **When a fix
changes a signature, the site list is the comparisons PLUS the callers.**

**Evidence.** Suite **2038 → 2056 / 0**. Battery `mutate_p1133.py` **14/14**. `nt_compile` 0 errors,
`sync_nt8.py --verify` 17/17. Anchors **423 / 0**.

⚠️ **The battery is aimed at the EVIDENCE as much as the fix, and that is where it paid.** Two of
the fourteen mutants attack the test stub rather than the addon, because a green suite is the
weakest possible evidence for this defect — 2038 tests were green while it was live, for exactly
one reason. **Four mutants survived the first run and all four were real gaps:**

1. **A blank name matched everything** — `FindLiveByName("")` resolving to the FIRST order on the
   account, which on the funded 50K is somebody else's working order that this class then MOVES.
   `P1-105`'s `WantsEverySymbol` at a second site. The two directions do not cost the same.
2. **The comparison could go case-insensitive.** Not reachable today (bracket ids are lowercase
   hex) but pinned, because widening a match here can only ADMIT something we did not place.
3. **`P1-130`'s absent-vs-terminal distinction was UNASSERTABLE** — see below.
4. **The re-id helper could be neutered while still being called**, and all three `P1-133` tests
   still passed. ⚠️ **That is what success looks like** — once the lookup is by name, the re-id is
   irrelevant — so the helper's protection is entirely INDIRECT: it is what makes those tests fail
   when the FIX is reverted. Nothing asserted it worked, so a silent no-op would have disarmed the
   regression guard without failing anything. Third instance of *read what a surviving mutant DOES*,
   and this time the answer was "a test is genuinely missing".

#### ⚠️ `P1-130` shipped a distinction nothing could observe, for a week

`P1-130` split `ATM_STOP_ORDER_NOT_FOUND` into two MESSAGES under one event type, because "absent
entirely" and "present but no longer live" are not the same news and only one means the position may
be unprotected. **The only test probe carried `(account, eventType)`**, and its comment says that is
"deliberately the whole signature" — correct for the case it was written for, and wrong for this
one. A mutant collapsing the two branches survived the entire suite with both messages still in the
source.

`LogEventMessageObserver` now fires from the same statement as the existing probe, so the two cannot
disagree about whether an event happened. The boundary is written at the declaration: use it only
where two branches share a type and the MESSAGE is the product, and assert on the distinguishing
phrase, not the sentence.

⚠️ **The assertion has to be that the two answers DIFFER.** "The message mentions the stop" passes
under the collapse — one message describes both situations perfectly well. `P2-109`'s lesson at a
third site, after "the filter returns a subset".

⚠️ **And the first run of that test captured two EMPTY strings**, because `LogFromComponent` is a
no-op when `Instance` is null and `AtmSetup` clears it. That is why no existing ATM test asserts on
a log line at all, and part of why this went unobserved. The positive control is what said so.

⚠️ **`mutate_p0_67.py`'s anchor broke for the SECOND time in one day** — this morning `P1-130` ADDED
a second match (ambiguous), tonight `P1-133` REMOVED the only one (matched 0). An anchor is a claim
of uniqueness and both directions break it; the mutant and its insertion point never moved, so it
was repointed rather than retired both times.

⚠️ **NOT LIVE-VALIDATED.** The fix needs one filled contract on a **non-Simulator** account, and
`Sim101` cannot produce evidence about it — that is the entire content of the defect. Until then
this entry is closed on a suite, a battery and a compile, which is exactly the standard that let
`P1-130` close with this hiding inside it. **Say which half was measured.**

### P2-134. `ATM_STOP_MOVE_ABANDONED` says "not asking again for this bracket" and then says it every 5 seconds — and blames a provider that refused nothing — ✅ CLOSED 2026-08-17 (session 53), found 2026-08-16 (session 52), same run

**Measured**, immediately after `P1-133`'s three not-found lines:

```
19:56:03  ATM_STOP_MOVE_ABANDONED  15bc730b: 3 consecutive stop moves were refused by the
                                   provider; not asking again for this bracket.
19:56:13  ATM_STOP_MOVE_ABANDONED  (same)
19:56:18  ATM_STOP_MOVE_ABANDONED  (same)
19:56:23  ATM_STOP_MOVE_ABANDONED  (same)
```

**Four in twenty seconds, from a line whose text promises it will not recur.** The attempt counter
is correctly capped — the three `NOT_FOUND` lines stop exactly at the budget, which is `P1-130`'s
bounded retry working — but the *announcement* of giving up is re-emitted on every sweep. **Ninth
instance of *an alarm that is always on is off***, and the sharpest one yet, because the operator
is told explicitly that this line will not repeat.

⚠️ **`F-6`'s `GuardAlertSink` does not cover it**, for the same reason `P2-108` was not covered:
this is a `LogEvent` with no action behind it, so `DispatchActions` never sees it. **That is now
twice.** The de-duplication belongs where the *log* is written, not only where actions are
dispatched — or every future give-up line arrives with this defect built in.

**Second half — the message names the wrong cause.** *"refused by the provider"* is false here:
the provider was never asked, because `P1-133` meant the order was never found. The counter is
shared by two different failures and the text asserts one of them. Same class as `P1-130`'s
*"the position may be unprotected"*, which was corrected for exactly this reason. **State what was
observed — N attempts failed — and name the last observed reason rather than assuming it.**

⚠️ **Do not fix this before `P1-133`.** Suppressing the repeat first would make the *only* visible
symptom of a dead breakeven feature quieter. — **HOLD EXPIRED 2026-08-17**, `P1-133` is ✅ CLOSED.

⚠️ **This entry spent a day reading as CLOSED and was not.** `P1-133`'s closure record was appended
to the end of the file, which put it *under this heading* — so the first thing below "OPEN, found
2026-08-16" was a `#### ✅ CLOSED` block describing a different defect. Corrected 2026-08-17.
**A closure record must be filed under the ID it closes, not at EOF**, and the ordering surfaces
are not the only place a status can be misread — see [[closures-do-not-propagate-backwards]].


#### ✅ CLOSED 2026-08-17 (session 53) — and the clear the ticket asked for would have been unreachable

The announcement is latched on `ActiveBracket.StopMoveAbandonAnnounced` and the message states the
**last observed** reason from `LastStopMoveFailureReason`, recorded at both sites that spend the
budget. Suite **2058 → 2071 / 0**, battery `mutate_p2134.py` **11/11**, all 11 gates green,
anchors **434 / 0**, `sync_nt8.py --verify` 17/17, `nt_compile` **0 errors**.

⚠️ **The spec's second clause was wrong and the test caught it, not review.** It said *"the latch
clears when the CONDITION resolves, never on a timer"* — `P2-107`'s rule, correct in general and
**false here**. The condition is `StopModifyAttempts >= Max` and it cannot resolve while the latch
is set: past the cap `RequestStopMove` returns before it asks, a confirm needs an outstanding
request, and the counter is reset only on a confirm. **Abandonment is permanent for a bracket** —
which is exactly what *"not asking again for this bracket"* says — so the episode boundary is the
**bracket**, and the clear would have been a line that can never run, reading as a release valve
that works. [[dead-safety-machinery-gate]] shipped in the act of preventing a repeat.

⚠️ **Test and fix agreed with each other and both were wrong about the system.** The first draft of
the recovery test "recovered" by assigning `bracket.StopModifyAttempts = 0` — not a recovery, a
poke — and the loop's patch answered it with a **setter on that property** that cleared the latch
on any assignment of zero. Green. `ActiveBracket` is serialised into the bridge payload, so a
deserialiser writing the default would have re-armed the announcement with nothing recovered.
**The POSITIVE CONTROL is what broke the agreement**: asserting that `ATM_STOP_MOVE_CONFIRMED`
had actually fired turned a passing test into a question, and the answer was that the scenario
does not exist. *Ask the engine what happened; do not assert the state you wanted.*

#### The battery went 6/11, and two survivors were not missing tests

**Three were real, and all three became tests.**

1. ⚠️ **The abandon branch must still RETURN FALSE.** `RequestStopMove`'s value is consumed —
   `if (RequestStopMove(...)) bracket.BreakevenTriggered = true;` — so a branch that returns true
   once it has announced makes the manager record a breakeven **that never happened**, and a
   `ScaledRunner` then trails from a price that was never set. `return false` → `return
   bracket.StopMoveAbandonAnnounced` passed **2063 green tests**. Quieting the announcement must
   not quieten the refusal.
2. The genuine refusal path (`ReconcileStopFromBroker`) must record its own reason, or the one
   failure where *"refused"* is TRUE is reported as whatever `ModifyStopPrice` last said.
3. A bracket restored with a count and no reason must say **"not recorded"** rather than print
   *"last observed reason: ."* — a well-formed sentence that reads as a fact about the failure.

**Two were badly-chosen mutants and were replaced, not chased.** One weakened a test's own positive
control (`abandoned >= 1` → `>= 0`): a mutant that makes an assertion *looser* cannot fail a suite
whose code is correct — **unkillable by construction**. The way to prove a positive control is
load-bearing is to break the CODE it guards, which the replacement `if (false)` mutant does. The
other gave two brackets the same `BracketId`, described as collapsing the scope test; it does not,
because `AddBracketForTest` keys by id, so the second bracket *replaces* the first, arrives with a
fresh latch and announces anyway. Third and fourth instance of **read what a surviving mutant DOES
before concluding a test is missing.**

⚠️ **Two mutants die as `NO RESULT LINE`, which is an opaque kill**, so it was re-driven by hand:
the `if (false)` mutant prints `[FAIL] P2-134: the bracket IS abandoned and does say so (positive
control -- got 0 ...)` first and by name. **A kill you cannot explain is not evidence.**

#### ⚠️ `check_anchors.py` was DEAD, and nothing said so

It crashed with `UnicodeEncodeError: 'charmap' codec can't encode characters in position 44-45`.
Windows stdout is cp1252; this repo's mutant descriptions are full of `⚠️`; and **a gate only
prints those strings when it has a finding**. So it could run green for months and die on the
first run where it mattered, with a traceback that reads as a defect in the script. While it could
not run it was checking **nothing**. Fixed, its first run reported **434 anchors / 1 BROKEN** —
`mutate_p1133`'s caller anchor, broken by this ticket's signature change and **repointed for the
third time at that one site in two days**.

⚠️ **`check_batteries_pin_encoding.py` already enforced this rule** — over `mutation/mutate_*.py`,
a region that excludes a file **in its own directory** and all of `tools/`. Twelve scripts sat
unpinned behind a green gate whose header describes exactly their hazard. Now
`tools/check_tools_pin_stdout.py`, wired into CI, which **caught a thirteenth that a text sweep
could not**: `check_batteries_pin_encoding.py` itself contains the string `reconfigure` as the
thing it searches for, so grepping for it reported the file compliant. **Parse; do not grep.**
Fifth instance of [[state-the-region-a-gate-inspects]].

#### ✅ LIVE-VALIDATED 2026-08-17 (session 54) — `Sim101`, MNQ SEP26, bracket `4b37828a`

```
23:40:03  ATM_STOP_MOVE_REQUESTED   4b37828a: breakeven trigger reached -- 30229.25 -> 30241.25
23:40:08  ATM_STOP_CHANGE_IGNORED   ... provider holds 30229.25 (attempt 1 of 3)
23:40:13  ATM_STOP_CHANGE_IGNORED   ... (attempt 2 of 3)
23:40:58  ATM_STOP_CHANGE_IGNORED   ... (attempt 3 of 3)
23:40:58  ATM_STOP_MOVE_ABANDONED   4b37828a: 3 stop moves failed, last observed reason: provider
                                    holds 30229.25 instead of requested 30241.25. Not asking again
                                    for this bracket. The stop is still at 30229.25 and will NOT
                                    trail. Intervene manually.
```

**Exactly one** `ATM_STOP_MOVE_ABANDONED` across the episode (counted over the whole buffer, not
eyeballed), against **four in twenty seconds** at baseline. Both halves hold: the line states what
was OBSERVED — *"3 stop moves failed"* — instead of asserting *"refused by the provider"*, and it
names the last observed reason, the price the stop is left at, and what to do.

⚠️ **It was validated by luck, and the luck is `P2-135`.** The announcement is emitted from
`RequestStopMove`, so it needs a CALLER after the budget is spent. This bracket had
`TrailMultiplier` 0.5, which keeps the trailing branch live; it was the trailing call in the very
same sweep as attempt 3 that reached the announcement. A second bracket that night, `75726b75`,
hit the identical failure on the identical path with the shipped default `TrailMultiplier` of 2 —
trailing dormant — and **the line was never said at all**. Same code, same provider, same failure:
see `P2-135` for the controlled pair.

#### Also live-validated in passing

* **`P1-130`'s differentiated message**, on one order in two states within five seconds:
  `CancelSubmitted` → *"It is on its way out; the stop was not moved."*;
  `Cancelled` → *"It is terminal, so THE POSITION MAY BE UNPROTECTED."*
* **`P1-133`'s name-based lookup** — every line above resolves `Stop_<bracketId>`, on a provider
  whose ids the manager no longer touches.
* **The bounded retry** stops exactly at the budget on both increment sites.

#### ⚠️ One measurement this does NOT explain

Bracket `b604e308`, the `ModifyStopPrice`-fails path (stop cancelled out from under the manager),
spent the budget cleanly — `ATM_STOP_ORDER_NOT_FOUND` at 23:35:38, :43, :48 — and then produced
**no announcement for 3.7 minutes**, with the position open, the price above the breakeven trigger,
and the sweep demonstrably alive (it was logging for another bracket minutes later). On that path
`BreakevenTriggered` is never set, so trailing never runs either, and breakeven should have called
`RequestStopMove` on the very next sweep and reached `:836`. `TestAtm_P2134_TheAbandonAnnouncement‐
FiresOncePerEpisode` drives exactly this shape and gets `abandoned == 1`. **The suite and the live
box disagree on this path** and the discrepancy is unexplained — do not close it by reasoning; drive
it again and instrument `StopModifyAttempts`, which `GetBracketStatus` does not expose (`P3-137a`).


### P2-135. `ATM_STOP_MOVE_ABANDONED` cannot be said on the path that spends its budget by refusal — ✅ FIXED 2026-08-17 (session 55), found session 54 while live-validating `P2-134`

**Measured on `Sim101`, bracket `75726b75`, MNQ SEP26, one contract:**

```
23:21:22  ATM_STOP_MOVE_REQUESTED   75726b75: breakeven trigger reached -- requested stop 30212 -> 30232.5
23:21:27  ATM_STOP_CHANGE_IGNORED   ... the provider holds 30212 (attempt 1 of 3)
23:21:52  ATM_STOP_MOVE_REQUESTED   (same)
23:21:57  ATM_STOP_CHANGE_IGNORED   ... (attempt 2 of 3)
23:22:22  ATM_STOP_MOVE_REQUESTED   (same)
23:22:27  ATM_STOP_CHANGE_IGNORED   ... (attempt 3 of 3)
          -- nothing further, ever --
```

The budget is spent to exactly `MaxStopModifyAttempts` and **`ATM_STOP_MOVE_ABANDONED` is never
emitted.** The operator is told "attempt 3 of 3" and then the surface goes quiet for the life of
the position, with the stop resting at its ORIGINAL price and no longer trailing. `P2-134` was
filed because that line was said too often; this is the same defect inverted, on the neighbouring
branch, and it is the worse direction.

**Why.** The announcement lives at the TOP of `RequestStopMove`, so it only speaks if something
CALLS that method after the budget is exhausted. The two sites that spend the budget differ in
whether anything ever does:

| site | returns | caller sets `BreakevenTriggered`? | re-requests next sweep? |
|---|---|---|---|
| `RequestStopMove` — `ModifyStopPrice` failed (`:871`) | `false` | no, the call returned false | **yes** → abandon reached |
| `ReconcileStopFromBroker` — provider holds another price (`:922`) | n/a, the request had SUCCEEDED | yes, set on the successful request | **no** → abandon unreachable |

The re-arm that would rescue the second row is `:932`:

```csharp
if (bracket.BreakevenTriggered && bracket.StopModifyAttempts < MaxStopModifyAttempts)
    bracket.BreakevenTriggered = false;
```

`attempts < Max` is false at exactly the attempt that exhausts the budget, so `BreakevenTriggered`
is left latched `true`, `:709`'s `!bracket.BreakevenTriggered` is false forever, and the breakeven
caller stops calling. The only remaining caller is the trailing branch at `:728`, which needs
`newStop > CurrentStopPrice` — with the default `TrailMultiplier` of 2 that means price must exceed
entry by a full stop-distance. **So the give-up line is reachable only on the branch where the trade
is winning, and silent in exactly the case where a frozen stop matters most.**

#### The controlled pair, measured the same night on the same account

Two brackets, the same code, the same provider, the same failure mode, and one variable:

| bracket | `TrailMultiplier` | trailing branch | `ATM_STOP_MOVE_ABANDONED` |
|---|---|---|---|
| `4b37828a` | **0.5** | live — `ATM_STOP_MOVE_IN_FLIGHT ... trailing stop advanced` every sweep | **fired, exactly once**, 23:40:58 |
| `75726b75` | **2** (the shipped default) | dormant — `newStop` never exceeded `CurrentStopPrice` | **never fired**, 3 attempts then silence |

On `4b37828a` the announcement came out in the *same sweep* as attempt 3: the reconcile incremented
the counter to the cap and left `BreakevenTriggered` latched `true`, which is precisely what enables
the trailing branch a few lines later — and that trailing call is what reached `:836`. **The latch
that disables the breakeven caller is the same latch that enables the trailing one**, so whether
anybody is left to say the line comes down entirely to a parameter that has nothing to do with
giving up.

⚠️ **This is why `P2-134` reads as validated.** It is — on the configuration that happened to be
under test. The default configuration is the silent one.

⚠️ **The suite cannot see this, and its own setup contains the workaround.**
`ATM_STOP_CHANGE_IGNORED` appears **zero** times in `tests/RiskGuardAddOnTests.cs`.
`TestAtm_P2134_TheGenuineRefusalKeepsItsName` does drive the refusal path to the cap — and then, at
`:8476`, does this:

```csharp
inst.MarketData.Last.Price = 20010.00;   // now ask for a move, and be refused
```

It moves the price by hand to force another `RequestStopMove`. That is a faithful test of the
message's CONTENT and it never asks whether anything calls it. **A test that supplies the missing
caller itself cannot discover that the caller is missing.** Another instance of
[[an-alarm-wired-to-a-dead-output]], and a second instance of the `P2-134` lesson that the test and
the fix can agree with each other and both be wrong about the system.

⚠️ **The harness cannot represent this path honestly.** The stub's `ModifyStopPrice` assigns
`live.StopPrice = newStopPrice` before `account.Change()`, so in the tests a change ALWAYS takes and
the reconcile always reads CONFIRMED. That is why the existing test must re-prime
`bracket.RequestedStopPrice` on every iteration — production sets it to `NaN` at `:935` and only a
successful request restores it. Any fix here needs a stub that can decline a `Change()`.

**Not to do:** do not "fix" this by relaxing `<` to `<=` in the re-arm. That reinstates the
5-second flood `P2-134` closed. The announcement wants emitting where the budget is SPENT, not
where the next request is refused.

#### A Simulator refusal, measured — `Sim101` does decline a `Change()`

[[the-simulator-re-ids-nothing]] records the Simulator echoing a requested price back. It does not
always: the three `ATM_STOP_CHANGE_IGNORED` lines above are `Sim101` declining a move outright.
The requested stop was **entry + 2 ticks with the trigger also at 2 ticks**, so the breakeven stop
landed at 30232.5 with the market at 30232.5-30233.5 — a sell-stop at or above the bid. The
Simulator refuses that and holds the old price; with a trigger of 8 ticks against an offset of 2 the
same move was accepted. **So "the Simulator honours everything" is false, and the distinguishing
variable is whether the resulting stop is valid against the current market, not the provider.**


### P2-141. `BreakevenOffsetTicks >= BreakevenTriggerTicks` is a configuration that CANNOT be honoured, and it is accepted in silence — ✅ FIXED 2026-08-18 (session 59), measured on the FUNDED account 2026-08-17 (session 56)

**FIXED.** `ValidateBreakevenPlacement(offsetTicks, triggerTicks)` — a pure static naming no
`NinjaTrader.Cbi` type, so it is reachable from the harness without a platform stub — returns a
refusal reason or `null`. `PlaceBracket` calls it beside the existing `stopPrice <= 0` refusal and
strictly BEFORE `string ocoId = Guid.NewGuid()`, so nothing is created, submitted or registered.
The refusal names both parameters and both values, and is logged as `ATM_BRACKET_REFUSED`.

The condition is `offset >= trigger`, not `>`. **Equal is also a refusal** — a stop exactly at the
market is not a valid resting stop — and that boundary has its own test and its own mutant, because
it is the off-by-one this defect turns on.

⚠️ **Two negative controls, and they are not optional.** The default 12/2 pair and an offset one
tick INSIDE the trigger must both still be ACCEPTED. A validator that refuses everything passes
every refusal test ever written for it ([[a-detector-needs-a-negative-test]]), and the
one-tick-inside case is the only thing that catches the guard being off by one in the other
direction, refusing a stop that is genuinely below the market.

**Driven through the agent-loop, which ended `NOT_CONVERGING` after 3 rounds** — tests green,
compile clean and no regressions every round, but one blocking finding per round with zero overlap
between consecutive rounds. Arbitrated by hand, which is what that verdict means. The panel's
blockers were style objections and one of them contradicted the ticket (it asked for the refusal to
precede the `switch` that computes `stopPrice`, which the ticket had placed deliberately after it).

⚠️ **The panel missed the only real defect, and it was in the line it had just written.**
`RiskGuardAddOn.LogFromComponent(string account, string eventType, string message)` takes an
ACCOUNT first, and the candidate passed `"DynamicAtmManager"` — filing the audit row against an
account that does not exist. Every other call site passes an account name or `""`. Found by reading
the signature rather than the diff, and it is now group 5 of the battery.

**Evidence**: suite 3163 → 3170 (7 tests, 5 written RED first), `mutation/mutate_p2141.py`
**7/8 killed + 1 declared EXPECTED SURVIVOR**. The declared one is the audit-row subject:
`LogFromComponent` is a no-op when `Instance` is null and the ATM tests clear it, so nothing logged
from here is observable from the harness — the same exemption the reconciler tests cite. Routed
through `_battery.finish` so a declaration that starts being KILLED is reported STALE rather than
passing quietly.

⚠️ **One survivor was a defect in the TEST, not the code.** The first version of the
names-both-values assertion asked only for the words "offset" and "trigger" anywhere in the string,
and a mutant that deleted `breakevenTriggerTicks` from the sentence that matters SURVIVED — because
a later sentence of prose still contained the word "trigger". Tightened to assert the two parameter
identifiers and the two parenthesised values. Same shape as
[[a-substring-assertion-catches-the-identifier]].

**The bridge half is NOT done**: `nt_place_atm_order`'s schema in `nt8-mcp-bridge` still accepts the
pair without comment. The addon refusing on its own is the load-bearing half — a schema that
validates is not a guard that refuses — but the caller still gets the refusal later than it could.

**A breakeven stop placed `offset` ticks past entry, triggered `trigger` ticks past entry, is above
the market whenever `offset >= trigger`.** For a long, a sell-stop at or above the bid is invalid,
so the provider holds the old price — every time, structurally, for the life of the position.

**Measured live on `TAKEPROFITPRO524207503` (Provider31), bracket `302e7759`**, placed with
`breakevenTriggerTicks: 1` and `breakevenOffsetTicks: 2` — values `nt_place_atm_order` accepted
without comment:

```
19:06:20  ATM_STOP_MOVE_REQUESTED   302e7759: breakeven trigger reached -- requested stop 30067 -> 30077.5
19:06:25  ATM_STOP_CHANGE_IGNORED   provider holds 30067 (attempt 1 of 3)
19:06:25  ATM_STOP_MOVE_REQUESTED   ... 30067 -> 30077.5          <- re-arm, same price
19:06:30  ATM_STOP_CHANGE_IGNORED   provider holds 30067 (attempt 2 of 3)
19:06:35  ATM_STOP_MOVE_REQUESTED   ... 30067 -> 30077.5
19:06:40  ATM_STOP_MOVE_ABANDONED   3 stop moves failed ... The stop is still at 30067
```

Entry 30077.25, so breakeven fired at 30077.25 and asked for **30077.5** — a quarter-point *above*
the price that triggered it. **Twenty seconds from fill to a permanently abandoned stop, on a healthy
winning position.** The trade later closed +$12 with its stop never having moved off the initial
10-point distance.

⚠️ **THE CONFIG SURFACE IS THE DEFECT, NOT THE PROVIDER.** `P2-136`'s addendum already established
that *"the distinguishing variable is whether the resulting stop is valid against the current market,
not the provider"*. What is new is that nothing anywhere refuses, clamps or warns about a combination
that **cannot succeed on any provider**: not `nt_place_atm_order`'s schema, not `PlaceBracket`, not
`AtmStrategyConfig`. The defaults (`trigger 12` / `offset 2`) are fine, which is why this has never
been hit — it needs an operator to tighten the trigger, which is a natural thing to want.

⚠️ **AND IT SPENDS `MaxStopModifyAttempts` ON SOMETHING UNACHIEVABLE.** The 3-attempt budget exists so
a *transient* refusal can recover. Here the condition is permanent, so the budget is guaranteed to be
consumed and `ATM_STOP_MOVE_ABANDONED` is guaranteed to fire — the alarm is correct and the operator
can do nothing with it, which over time is how a real alarm gets discounted.
[[a-recovery-budget-is-not-a-policy]].

**Where**: `addons/DynamicAtmManager.cs` `PlaceBracket` (validate before registering) and
`nt8-mcp-bridge` `nt_place_atm_order`'s schema. **Refuse at placement, naming both values** — a stop
that cannot be placed is not something to discover twenty seconds later from an abandonment line.
⚠️ Do NOT "fix" it by clamping silently: a caller who asked for a 1-tick trigger and got 12 has been
answered a different question, which is `P1-102`'s lesson about defaulting in the wrapper.

**Found by the operator watching the live run** — *"the stop did not go to BE and it just exited
now"* — which is the same detection surface that found `P2-138`. Both `P1-139`'s and `P2-135`'s live
halves were confirmed by the same bracket; see `P1-139`'s closure.


### P2-142. `ARMED_ON_START` re-arms the guard on every recompile, so a deliberate DISARM does not survive somebody else's deploy — ✅ FIXED 2026-08-18 (session 59), split out of `P2-136` 2026-08-17 (session 57)

**FIXED, on an explicit operator ruling: ALL configuration is persistent.** Asked whether a disarm
should persist (the guard may come up off when you expect it on) or keep re-arming (a disarm
silently evaporates), the answer was the general rule rather than the instance.

`PersistedStateData.OperatorDisarmedUtc` is a **nullable** `DateTime` recording *when* an operator
deliberately disarmed. `ToggleArmed` sets it on disarming and clears it on arming;
`LoadPersistedState` rehydrates it; `ApplyInitialArmState` honours it and returns before the
mode default is applied.

⚠️ **NULLABLE BECAUSE THREE STATES HAVE TO BE DISTINGUISHABLE AND A BOOL CARRIES TWO**: "an
operator disarmed at T", "nobody has disarmed", and — for a state file written before the field
existed — "unknown", which reads as null and behaves as the safe answer. A bool would have made a
fresh install and a deliberate disarm identical, which is the trap where a default and an erasure
look the same.

⚠️ **THE ASYMMETRY IS THE DESIGN, NOT AN OVERSIGHT, AND IT IS WHAT A FUTURE READER WILL TIDY AWAY.**
Only a DISARM is honoured from persisted state. A persisted ARM is still ignored — `_isArmed` is
still forced false on load and arming an acting mode still requires preflight plus a deliberate
toggle — because `FR-30/31` exists to stop a stale `true` re-arming a guard. The two directions
carry **opposite** risk: a wrongly-restored ARM makes a guard act on stale intent, a
wrongly-restored DISARM only declines to act. They must not share one symmetrical rule, and two
mutants (one per direction) exist solely to catch someone collapsing them into one line.

**A persisted disarm gets its own event**, `DISARM_PERSISTED`, naming the timestamp and the start
kind it survived — not `UNPROTECTED_ON_START`, which already means "this mode comes up disarmed by
default". The fact an operator needs on returning to the box is *a person turned it off and it is
still off*, and persistence without visibility is how a config comes to read as protection that
does not exist. [[configured-evaluated-enforcing]].

**A recompile is now told from a restart.** `StartKindFor(recordedPid, recordedStartUtc, currentPid,
currentStartUtc)` is pure and names no NinjaTrader type. Identity is the pid **plus the process
start time**, because pids are recycled; an unrecorded host reads as `a RESTART`, the answer that
claims less. This is what the entry asked for: 84 arm events was 84 sessions by this code's
reckoning and one by the operator's.

⚠️ **The first battery left two survivors and they were a real coverage gap, not battery noise.**
Every other test seeded `OperatorDisarmedUtc` directly, so the HONOURING half was covered and the
WRITING half was not: a mutant that never recorded the intent and one that never cleared it both
passed the whole suite. `TestArm_P2142_TheToggleRecordsAndClearsTheIntent` closes it. The
round-trip test is there for the same reason in the other dimension — the seam tests prove the
field is READ, not that it is WRITTEN, and a value held only in memory would be lost by exactly
the recompile this entry is about.

**Evidence**: suite 3170 → 3185, `mutation/mutate_p2142.py` 12 mutants, wired into CI.


Measured while diagnosing `P2-136`: **84 `ARMED_ON_START` events in one 3 MB tail** of
`interventions.jsonl`, alongside 84 `INITIALIZE` and 171 `CONNECTION_CHANGE` — every one a recompile
rather than a restart, several of them from another repo deploying unrelated NinjaScript.

In `shadow` this is noise. In `live` it means **the guard re-arms itself minutes after an operator
disarmed it**, with no interaction from that operator and no symptom other than a log line that
already appears 84 times.

⚠️ **AND IT SITS DIRECTLY AGAINST A RULE THAT IS DELIBERATE, WHICH IS WHY IT IS ITS OWN ID RATHER
THAN FOLDED INTO `P2-136`.** `LoadPersistedState` refuses to rehydrate `_isArmed`, in writing:

```
// FR-30/31: never rehydrate the armed flag from persisted state.
// Lockouts persist, but armed state must be set fresh each session via Preflight().
// Previously: _isArmed = data.IsArmed;  (could silently re-arm across restarts)
```

So the existing rule prevents a persisted `true` from re-arming, and `ApplyInitialArmState` then arms
from the CONFIG anyway. The two mechanisms answer the same question differently. **This is not a
one-line fix and must not be treated as one**: making a disarm persist means persisting a `false`
through exactly the path `FR-30/31` exists to keep closed, and the distinction it needs is
*"disarmed because nobody armed it yet"* versus *"disarmed because an operator said so"* — which the
state file does not currently carry. [[configured-evaluated-enforcing]].

Note also that a compile is not a restart, so "set fresh each session" is doing work the phrase does
not obviously cover: 84 arm events is 84 sessions by this code's reckoning and one session by the
operator's. Whatever the fix, it wants `ARMED_ON_START` to distinguish the two, or the log stays
unreadable on this axis regardless.


### P1-143. `P2-136`'s restore hands a refused stop a FRESH retry budget on every recompile, because the "consumed once" latch is per-INSTANCE and a compile makes several instances — ✅ FIXED 2026-08-18 (session 58), found the same session in the first live run of the fix that introduced it

`AtmBracketPersistence.Decide` clears `StopModifyAttempts = 0` and
`StopMoveAbandonAnnounced = false` when it restores a bracket
(`addons/AtmBracketPersistence.cs:267-268`). The comment justifying that sits two files over in
`DynamicAtmManager.cs:122` and says the reset is safe **because a record is consumed once**.

It is not. Measured on this box after a single `nt_compile`:

```
02:10:29  ATM_BRACKET_RESTORED 41162959  + INITIALIZE + ARMED_ON_START
02:10:44  ATM_BRACKET_RESTORED 41162959  + INITIALIZE + ARMED_ON_START
02:10:59  ATM_BRACKET_RESTORED 41162959  + INITIALIZE + ARMED_ON_START
02:11:14  ATM_BRACKET_RESTORED 41162959  + INITIALIZE + ARMED_ON_START
```

One compile produced **four `InitializeRiskGuard` runs**, each on a fresh static context — so
`_persistedRestorePending`, which is an instance field, was `true` four times and the file was
consumed four times. The latch makes the restore once-per-INSTANCE; nothing makes it
once-per-BRACKET.

Two consequences, and the first is the one that costs money:

* **The refusal budget is laundered.** `P2-135` bounds stop-move attempts precisely so a provider
  refusing a move cannot be asked forever. A compile burst hands a refused bracket 3–4 fresh
  budgets. The bound still exists; it is no longer the bound the code claims.
* **`if (restored > 0) EnsureMonitor();`** (`DynamicAtmManager.cs:715-716`) — `EnsureMonitor`'s
  `if (_monitoring) return` is also per-instance, so N managers each hold their own copy of one
  bracket, with their own `CurrentStopPrice` cache, all moving the same stop.
  [[a-second-reader-of-the-same-state]].

⚠️ **This is self-inflicted and it is a REGRESSION**: before `P2-136`, a post-compile manager had an
empty registry and did nothing at all. The reasoning that failed was *"a new assembly is a new
episode"*, which is true of a restart and false of a compile — the same distinction `P2-142` records
from the other side. A fix that only de-duplicates the log line fixes the symptom and leaves the
budget reset.

**Proposed direction** (not yet implemented): stop resetting the budget and the abandon latch on
restore — persist and carry them. The CONFIRMED branch in `DynamicAtmManager.cs:1332,1338` already
clears both on a genuine recovery, which is the event that should clear them. Then suppress the
repeat announcement so `ATM_BRACKET_RESTORED` says itself once per bracket.

✅ **FIXED 2026-08-18 (session 58).** The reset is gone. `StopModifyAttempts`,
`StopMoveAbandonAnnounced` and `LastStopMoveFailureReason` are plain serialised properties of
`ActiveBracket`, so carrying them across a compile was a DELETION, not new machinery. The event that
should clear them already did: `ReconcileStopFromBroker`'s CONFIRMED branch, where a move is OBSERVED
to have taken.

Suite **2182 → 2188 / 0**; battery `mutate_p2136survive.py` **26 → 30 mutants, 30/30 killed**.

⚠️ **TWO ARTEFACTS FROM THE SESSION THAT SHIPPED THE DEFECT WERE ENFORCING IT**, and this is the part
worth carrying:

* the test asserted `restored.StopModifyAttempts == 0` — written in the same session as the reset,
  from the same wrong premise, so it licensed the defect rather than catching it; and
* the battery carried a mutant scoring the CORRECT behaviour as the bug (*"the refusal budget
  survives … which is a new episode by any reading"*).

A test written from the same premise as the code tests the premise, not the code. Both are inverted,
and the new negative control — a CONFIRMED move must still clear the carried budget — is what stops
the fix becoming "nothing ever clears it".

⚠️ **NOT FIXED, and deliberately left with `P2-142`:** `if (restored > 0) EnsureMonitor()` is still
per-instance, so several managers may each hold a copy of one bracket. Whether old assemblies survive
a hot-swap has not been MEASURED by anybody here, and it belongs with the question of why one compile
yields 3-4 `INITIALIZE` events. Bundling a guess with a definite fix would have made both unverifiable.


### P2-144. `check_bridge_parses.py` was on disk and wired to NOTHING — and neither repo's meta-gate could ever have noticed, because both globbed `mutation/` only — ✅ FIXED 2026-08-18 (session 58)

Found while deriving a gate count for `CLAUDE.md` rather than by any gate.
`nt8-mcp-bridge/tools/check_bridge_parses.py` is referenced in the handover (§ parse gate) and in
this plan in six places as the gate covering **`McpBridgeAddOn.cs`** — the one bridge source
`BridgeTests.csproj` cannot compile, so a stray brace there is findable only by deploying. CI had
**never run it**. It had only ever run by hand, on the machine that wrote it.

The stakes are the ones the riskguard sibling states in its own workflow comment: a syntax error in
**any** addon `.cs` stops **every** addon loading, RiskGuard included — and
[[broken-nt8-assembly-is-invisible]] means the symptom is a deploy that appears to do nothing.

⚠️ **THE CLASS, WHICH IS WHY THIS IS NOT A ONE-LINE CI EDIT.** `check_ci_runs_every_battery.py`
exists in both repos precisely because a battery on disk and unwired proves nothing. Its own
docstring records fixing that for batteries and warns that fixing an instance is not fixing a class.
Both copies glob `mutation/mutate_*.py` — so **no gate script in either repo was ever required to be
wired anywhere**. The meta-gate had the identical defect it was written to prevent, one directory
over.

Fixed in both repos: each `check_ci_runs_every_battery.py` now also globs `check_*.py` under
`tools/` and `mutation/` and requires each to be executed exactly once, **matched on the
repo-relative path** so `python tools/x.py` and `python mutation/x.py` are not interchangeable
evidence for the same basename. `check_bridge_parses.py` wired into the bridge workflow in the same
commit.

Controls run both ways in both repos, since [[a-source-gate-must-assert-the-condition]]: with the
gate unwired each meta-gate exits **1** naming it; restored, each exits **0**. riskguard reads
`44 batteries / 11 gates`, bridge `13 batteries / 5 gates`.

Not covered, and stated rather than left implied: the bridge has no `pack_ci_matrix.py` and no bin
ceiling, so its gates are plain steps. Nothing yet requires a *new* gate to carry a negative
control.


### P2-145. `NAKED_POSITION` fires on fully-covered positions — 21 of 245 measured findings were wrong, and the `gap` half of this entry never existed — ✅ FIXED 2026-08-18 (session 59), `v1.44.0`

Surfaced within minutes of `P2-127`'s events pane going live, from 235 `NAKED_POSITION` events that
were previously buried in a 44 MB `interventions.jsonl`. Grouped by `fsmState` and `gap`:

| fsmState | gap | count |
|---|---|---|
| `ProtectedPending` | **0** | **10** |
| `Protected` | **1** | **2** |
| `Protected` | **2** | **2** |
| `FlattenPending` | 1, 2, 3, 10, 11, 100 | 163 |
| `Unprotected` | 1, 2, 3, 10, 11, 100 | 58 |

Two opposite failures, and they need separating before either is fixed:

* **Fires on a non-condition — 10 events with `gap=0`.** e.g.
  `MNQ SEP26: position=5, fsmState=ProtectedPending, covered=5, gap=0`. Every contract is covered
  and the event announces a naked position. A detector that fires when its own arithmetic says
  there is nothing to report is [[a-filter-that-matches-too-much]], and on this surface the cost is
  that the 58 real `Unprotected` events read like more of the same noise.
* **The state says `Protected` while the gap is 1 or 2 — 4 events.** That is the *serious*
  direction and it is not the same bug: coverage is genuinely short while the FSM believes it is
  not. [[configured-evaluated-enforcing]].

⚠️ **Do not "fix" this by suppressing `gap=0`.** That silences the loud half and leaves the quiet
half — the four `Protected`-with-a-gap events — exactly as invisible as they are now, and
[[weigh-the-quiet-failure-above-the-loud]] says which of the two is worth the session. The
`Protected` rows are the ones to drive first.

Also unestablished: whether `ProtectedPending`/`gap=0` is a *transient* read taken before coverage
settles, in which case the fix is a settle window rather than a predicate change. Nothing measured
yet distinguishes those.



---

## RESOLVED 2026-08-18 (session 59). One half was real, the other half did not exist.

**Re-derived from all 245 `NAKED_POSITION` findings rather than from the 235 the pane showed:**

| fsmState | gap | count | verdict |
|---|---|---|---|
| `ProtectedPending` | **0** | **17** | ‼️ FALSE ALARM — every contract covered |
| `Protected` | 1–2 | **4** | ✅ CORRECT, and deliberate — see below |
| `FlattenPending` | >0 | 163 | correct |
| `Unprotected` | >0 | 61 | correct |

**`gap == positionQty - covered` in 245 of 245 rows.** Nothing ever disagreed with its own `gap`
field, so the headline of this entry was wrong and the "BOTH directions" framing sent the next
reader looking for an arithmetic bug that was never there. What actually existed was **one** OR with
two arms:

```csharp
if (!isProtected || covered < positionQty)      // RiskGuardAddOn.cs, was ~3457
```

The left arm is true whenever the state is not *exactly* `Protected`. `ProtectedPending` means the
stop is Submitted/Initialized/Accepted — states `ProvidesCoverage` **already counts as cover** —
so a fully protected position took the branch and announced itself naked. All 17.

⚠️ **AND THE FOUR `Protected`-WITH-A-GAP ROWS ARE NOT A DEFECT.** This entry called them "the
*serious* direction" and they are the system working. `Protected` does not mean fully covered:
`P1-36` deliberately made losing one stop of several a *partial* rather than a nakedness, and the
terminal-stop path drops to `Unprotected` only when `CoveredQuantity <= 0`
(`RiskGuardAddOn.cs`, the `FSM_UNDERCOVERED` branch). A gap under `Protected` is a correctly
reported partial. The fix therefore does **not** touch them — it makes the message say
`partially uncovered` so no future reader repeats this entry's misreading.

So the standing instruction in this entry — *"drive the `Protected` rows first"* — pointed at the
half that was already right. [[weigh-the-quiet-failure-above-the-loud]] is sound advice that assumed
a quiet failure existed.

**THE FIX.** The predicate is extracted to `RiskGuardAddOn.AssessCoverage(hasFsm, state, covered,
positionQty)`, returning `CoverageFinding.{None, NakedPosition, CoverageDisagrees}` plus `Gap` and
`Partial`. `NAKED_POSITION` now requires `covered < positionQty`.

⚠️ **Narrowing it had to not eat a true positive.** `!isProtected` was the only reporter of *fully
covered while the state machine does not agree* — an FSM stuck `Unprotected` or `FlattenPending`
behind a complete stop. Deleting that arm would have removed a signal silently, which is the one
failure a green suite cannot show you, so it is **rehomed** as a distinct
`FSM_COVERAGE_DISAGREES` finding rather than dropped. `ProtectedPending` counts as agreement, which
is the single line the 17 turn on. [[a-filter-that-matches-too-much]].

**WHY IT SURVIVED, which is the part worth carrying.** Every `NAKED_POSITION` test in this repo
exercises the **throttle** (`AuditFindingThrottle`), not the condition. The predicate sat inline in
`RunGuardAudit`, which needs `Account.All`, so nothing could reach it from the test build — and a
predicate that fires on everything passes every positive test ever written for it.
[[a-detector-needs-a-negative-test]]. `P3-30`'s battery comment already recorded that its three
guard-audit tests were positive-only; this is the same gap, one predicate over.

**Evidence:** suite **3158 / 0** (the exhaustive gap check contributes 624 assertions). Battery
`mutation/mutate_p2145coverage.py`, **10 / 10 killed**, wired into the `P1-76+P3-30+P2-145` CI bin
next to the other guard-audit battery. The group-1 mutant that restores the old predicate verbatim
produces **239 failures**, which is the test-first evidence — these tests would have been red
before the fix. The battery also carries a mutant for the gap arithmetic that was measured correct
in 245/245 rows, because "measured correct" is a statement about the past.

⚠️ **NOT LIVE-VALIDATED.** `AssessCoverage` is proven by the suite and the battery against the
measured inputs; nothing has yet watched a real `ProtectedPending` position go un-alarmed on the
box. The next 17-shaped occurrence is the confirmation, and its absence is what to look for.

### P1-146. Two genuinely UNPROTECTED positions on the FUNDED account, and the guard reported both without acting because it is in `shadow` — ✅ CLOSED NOT-A-DEFECT 2026-08-18 (session 59): the operator's own bare manual entries, and the guard read them correctly

Not a detector defect — these are the true positives inside `P2-145`'s noise, on
`TAKEPROFITPRO524207503`, a funded 50K TPT PRO account:

```
2026-08-18T01:53:03Z  MNQ SEP26: position=3, fsmState=Unprotected, covered=0, gap=3
2026-08-18T02:26:14Z  MES SEP26: position=1, fsmState=Unprotected, covered=0, gap=1
```

`covered=0` on both: real money in the market with **no stop at all**, for as long as it took the
position to close. Neither position was placed by this session's work (that was MNQ on `Sim101`).

Both records carry `mode: shadow`, so `EvaluatedNotEnforcing` applied and the guard did nothing but
write a line. **That is the guard behaving exactly as configured** — which is the point worth
recording rather than the defect: the protection that would have covered these exists, is armed, is
guarding, and is switched to report-only. [[configured-evaluated-enforcing]].

Open questions, none answered yet: what opened them (no `ATM_BRACKET_*` event names either
instrument at those times, so they did not come through `DynamicAtmManager`); whether a bracket was
attempted and refused; and whether `P1-143`'s laundered budget could produce this shape. Do not
close this against `P2-145` — the detector being noisy and these being real are independent facts.

---

**ANSWERED 2026-08-18 (session 59), from `interventions.jsonl`. The guard was right; there is no
code defect here.** The operator places orders on this account two different ways, and the log
distinguishes them by `orderName`:

* **`Entry` / `Stop1` / `Target1` / `Exit` / `Close`** — Chart Trader with an NT8 **ATM strategy**
  attached. 90 MNQ entries between 08-07 and 08-17, and every one is covered **in the same second**:
  `19:24:41 Entry Buy 3 Filled` and `19:24:41 Stop1 Working @30185.0` + `Target1 Working`, with
  `Stop1` then trailing 30185 -> 30193.75 -> 30196.5 -> ... -> 30208.5. Includes a **10-lot** at
  19:40:52 which arrived with `Stop1 qty=10 @30196.5` attached — bracketed, not a runaway.
* **`orderName` EMPTY** — a bare order with no ATM strategy. **All four naked episodes are these.**

So the answer to "what opened them" is: a bare manual entry, and nothing brackets those. Full set on
the funded account (ET), wider than the two originally filed:

```
Sun 08-16 19:28:46  MNQ short 3, cov=0   <- see the flip note below
Mon 08-17 21:52:54  MNQ Sell 3 @30005.50 -> covered 21:53:23 @29979.50.  NO STOP EVER. naked 29s
Mon 08-17 23:30:30  MNQ Sell 1 @29860.00 -> covered 23:31:18 @29853.00.  naked ~48s
Tue 08-18 00:01:59  MNQ Sell 1 @29880.25 -> stop appeared 00:02:42.      naked 43s
```

`AUDIT_FINDING_SUPPRESSED` matters for reading these: *"is STILL TRUE and will stop being logged
after 1 line(s)"*. **A single `NAKED_POSITION` row does not mean a brief window** — four of the five
funded `covered=0` conditions carry a suppression, i.e. they persisted past the 10-second re-check.

**08-16 19:28 is a different shape and worth its own attention.** It was not an entry. The operator
was long 3 and clicked `Exit Sell 2` three times (19:27:08, 19:28:45, 19:28:48 x2), which sold
through flat and **flipped the account to short 3 with no bracket**, because `Stop1`/`Target1`
belonged to the long. An over-click on the exit button is a naked reversal.

**Ruled out as causes, each measured rather than reasoned:**

* **The copier.** `copier_config.json` holds two relationships, `Sim101->Sim-ORB` and
  `Sim101->SimCopy2`, both `IsEnabled: false`, and the funded account appears as neither leader nor
  follower. Confirmed by the operator: the copier is not enabled yet. The operator's MNQ strategy
  runs on **sim** accounts and never reached real money.
* **`DynamicAtmManager`.** Its brackets are named `AtmEntry_*`/`Stop_*`/`Target_*` and all five on
  this account attached their stop in the same second.
* **`P1-143`'s laundered budget.** `StopModifyAttempts` is not in this path at all; these positions
  never had a stop to modify.
* **A `Suspended` stop dropping out of `CoveredQuantity`.** Raised as a hypothesis because
  `Suspended` -> `OrderLiveness.Inert` -> not cover (`RiskGuardAddOn.cs:2724`) and the four live
  TakeProfit accounts produce it (25-118 stop updates each) while `Sim101` produces **zero** — the
  shape of [[the-simulator-re-ids-nothing]]. **Measured and refuted:** 179 of 179 `Suspended` stops
  return to `Working` (123) or `Accepted` (56), median **0.0s**, max **0.2s**. It is a sub-200ms
  transient inside a modification, not a dormant order, and the 10-second audit cadence almost never
  samples it. The fail-closed classification is correct and this is not a coverage defect.

⚠️ **WHAT THIS TURNS INTO, AND IT POINTS AT `live`.** `StopGuard.OnMissing: Flatten` with
`StopAttachSeconds: 15`. Against the measured behaviour above, arming `live` would have **flattened
the operator's own trades**: the 00:01:59 position 28 seconds *before* their stop arrived at
00:02:42, and the 21:52:54 three-lot out from under an active scalp. `RiskGuardModels.cs:912` already
names this hazard — `P1-84` raised the value from 3 to 15 because *"entering manually and reaching
for the mouse to place the stop gets you flattened on a day when nothing was wrong"* — and **15 is
still about 3x short of measured hand speed.** That comment also states the number is only right
*for* `Flatten`; `OnMissing: AutoStop` exists with offsets already configured (MNQ 40, MES 16) and is
the better pairing here, because an invented stop is recoverable and being taken out of a trade is
not. `P1-84` mitigated this with a guess; there is now a measurement. **This is a blocker on arming
`live` and it needs its own ID before anyone does.**

Note also `ACTION_SUPPRESSED`: *"already reported once and the condition has not resolved; the guard
is not acting."* In `live` the **second** naked position of the same kind receives no flatten at all.

**The lesson, since the premise was wrong rather than the code:** the entry asked "what opened
these", assuming a component did. The detector was accurate the whole time and the defect was in the
workflow it was watching. [[check-the-exemplar-belongs-to-the-class]] — and the two positions
originally filed were 5 of 9 funded rows, so the exemplar was also incomplete.


### P2-147. Twelve executions on the funded account were dropped by the copier because they carry no `Order`, so no direction could be read — OPEN, measured 2026-08-18 (session 58)

```
2026-08-18T02:00:54Z  TAKEPROFITPRO524207503
  execution 613562532259_1 has no Order, so its direction cannot be determined.
  execution 613562532273_1 has no Order, so its direction cannot be determined.
  execution 613562532319_1 has no Order, so its direction cannot be determined.
  ... 12 in total, all on the funded account
```

Three of them share one timestamp to the tick, which suggests one fill event fanned into several
executions rather than twelve separate trades — [[an-order-is-not-one-fill]].

The copier reads direction from `execution.Order`. When that is null it ignores the execution, which
is the safe branch and is why this is a P2 rather than a P0: dropping is better than guessing a
side. But an ignored execution on a LEADER account is a copy that silently did not happen, and
nothing downstream reports the leader and the follower having diverged.

⚠️ **`Order` being null is a BROKER-DEPENDENT fact and must not be reasoned about from `Sim101`.**
[[the-simulator-re-ids-nothing]] — the provider here is whatever `TAKEPROFITPRO524207503` connects
through, and any evidence gathered for this ID has to name it. The candidate direction is to read
the side from `Execution.MarketPosition` or the position delta rather than from `Order`, but that is
a guess until somebody measures which fields are actually populated on this provider when `Order` is
null.


### P2-148. A mutant that CRASHES the test harness scores as KILLED with nothing having detected it — ALL 44 batteries, in two spellings — ⚠️ OPEN: fixed in one battery 2026-08-18 (session 58), the other 43 are a mechanical sweep

Found while diagnosing a kill that read oddly, not by a gate.

Every battery's `run()` ends by regex-matching the harness's `Passed = N, Failed = M` line, which the
harness prints **last**. So an unhandled exception anywhere leaves no result line, `run()` returns
`'NO RESULT LINE'`, and the scoring reads:

```python
killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) or ... 
```

**A crash counts as a kill unconditionally.** That is correct when assertions failed first and the
crash was a consequence; it is a FALSE KILL when the mutant merely broke the harness and no test
detected anything. The two are indistinguishable to the scorer, and a false kill is invisible — it
prints `[KILLED]` and leaves the survivor list empty, which is the exact shape of
[[a-green-that-can-never-be-red]] that this repo keeps paying for.

⚠️ **THE COUNT WAS FIRST WRITTEN AS "41 of 44" AND THAT IS WRONG.** 41 batteries spell the defect
as `('NO RESULT LINE' in res)`. The other three — `mutate_cm3.py`, `mutate_cm4.py`,
`mutate_p0_63.py` — spell it `killed = 'Failed = 0' not in res`, which is **strictly more
permissive**: every non-green result string counts as a kill, including `TIMEOUT` and
`BUILD FAILED`, with no enumeration at all. Grepping for one spelling and reporting the count as
the population is the same mistake as a naive `grep CLOSED` on this file. **All 44 are affected.**

**Measured on the instance that exposed it.** The `alreadyLive = false` mutant in
`mutate_p2136survive.py` dies with a `NullReferenceException`. Re-driven by hand, it **is** genuinely
caught — two `P2-134` assertions fail on the way down — so the verdict was right, **by accident**.
The scoring could not have told the difference.

⚠️ **AND THEN THE FIXED SCORING IMMEDIATELY FOUND A REAL FALSE KILL, IN THIS BATTERY.** An earlier
draft of this entry said "no battery result is known to be wrong"; that was written before the
battery was re-run and **it is false**. Re-run with the stricter rule, `mutate_p2136survive.py` went
**30/30 → 29/30**, and the newly-exposed survivor is the first mutant in the file:

> ⚠️ THE IDENTITY CHECK GOES AWAY: any open position in the right symbol is adopted.

That is **`P2-136`'s entire safety argument** — a record is only picked up when the live order named
`Stop_<bracketId>` is still working — and it has been scored KILLED since the battery was written
while nothing detected it. The mechanism: with `if (liveStop == null)` mutated to `if (false)`,
control reaches `b.CurrentStopPrice = liveStop.StopPrice` and throws a `NullReferenceException`.

⚠️ **The test that should catch it EXISTS and is correct** — `TestAtm_P2136_AnOpenPositionWithNoNamedStopIsNotAdopted`
— but it never runs its assertion, because `Main` is a **flat list of unguarded calls** and one throw
kills the process. So the crash is not merely mis-scored; **every test registered after the throwing
one goes unrun**, and the number that reach an assertion at all is unknown. This is the same
structural fact as the `P2-134` precondition crash noted below, and it is the real defect underneath
`P2-148`.

⚠️ **A second, separate problem with that mutant, and it cuts the other way.** Its stated consequence
— *"this monitor starts moving a stop the operator placed, on a funded account"* — is **not** what the
mutated code does. It throws before adopting anything, and `ExecuteSafetySweep` wraps the call, so in
production this shape would be logged as a restore failure rather than adopting a stranger's
position. **The mutant does not model the defect it describes.** A faithful one returns a fabricated
non-null stop and lets the adoption actually happen. Until that mutant is written, the identity check
has no evidence behind it in either direction — [[check-the-exemplar-belongs-to-the-class]].

**So the correct summary is not "41 batteries have been mis-scoring".** It is: one false kill is
confirmed, in the battery that happened to be re-run; the other 40 batteries have the same blind spot
and **have not been re-run under the stricter rule**, so nothing is known about them yet. Re-running
them is how to find out, and it is the first thing to do here.

**The fix, applied to `mutate_p2136survive.py` only:** a crash counts as detection only if the run
printed at least one `[FAIL]` first.

```python
if not m and '[FAIL]' not in out:
    return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
```

⚠️ Ordering matters and is easy to get wrong: the new verdict string CONTAINS `'NO RESULT LINE'`, so
it must be excluded before that substring is read as a kill. A first draft that appended the note
without the exclusion scored identically to the defect — [[a-substring-assertion-catches-the-identifier]].

**Why the other 40 are not done in the same commit.** It is a mechanical edit to the verification
layer of the whole repo, made at the end of a session, on files a running battery mutates in place.
`mutation/_battery.py` already exists and exports `_description` and `finish` but **not** `run` —
each battery owns its own copy — so the class fix is either 40 near-identical edits or lifting `run`
into the shared module and migrating callers. ⚠️ **Do not add the helper without migrating**: a
correct `run` in `_battery.py` that 40 batteries do not call is dead safety machinery, and this repo
has a CI gate that exists because of exactly that.

⚠️ **And there is a second, smaller defect underneath this one, which is what made the kill
ambiguous.** `TestAtm_P2134_TheGenuineRefusalKeepsItsName` dereferences a null **after its own
precondition assertion has already failed**, so it crashes rather than failing cleanly — taking
every test registered after it down with it, unrun. A test that cannot survive its own failed
precondition converts one red assertion into an unknown number of unmeasured ones. That is worth its
own sweep of the suite's preconditions and gets its own ID when taken.


### P1-149. `Sizing.MaxContractsPerAccount` is configured, evaluated, displayed — and enforced by NOTHING before an order is placed. The only thing that refuses an oversized order is the PROP FIRM, at 60 — ⚠️ REFRAMED 2026-08-21 (session 62): the bridge/copier halves are CLOSED; the RiskGatekeeper sub-task and the documented non-goal remain — OPEN

> **Research 2026-08-21 (session 62).** The "enforced by nothing" half is now false. `BridgeSizingGate` enforces the cap pre-trade on all three bridge order paths (`McpBridgeAddOn.cs:2623/2712/5760`, reading the guard's `EffectiveMaxContracts` at `RiskGuardAddOn.cs:1639`), and the copier clamps to the same number (`TradeCopierEngine.cs:5318`, lower-binds). The cap is also enforced REACTIVELY in the guard via `MAX_SIZE_BREACH` (`RiskGuardAddOn.cs:4693-4706`). So the number is NOT dead.
>
> **The irreducible residue (NT8 platform fact).** An AddOn has no pre-submit veto for an order it did not originate — `OrderUpdate` fires no earlier than `Submitted`/`Accepted`, and instant fills surface once, already `Filled` (`RiskGuardAddOn.cs:4667-4670`). So **manual UI orders, external-platform orders, and non-`RiskManagerBase` strategies can only be caught reactively** (cancel-if-working = a race; flatten-after-fill = slips, which is what this defect measured). The prop firm's 60-contract desk refusal is the only TRUE pre-trade cap on those paths.
>
> **The one closeable gap:** `RiskGatekeeper.CanTrade` (the strategy-side pre-submit gate for `RiskManagerBase` strategies, `Documents/NinjaTrader 8/bin/Custom/Strategies/Vinay/RiskGatekeeper.cs:98`) enforces loss/drawdown/trade-count but NOT the contract cap. Wiring the cap in there would give `RiskManagerBase` strategies a genuine pre-trade size refusal. ⚠️ that file is in NEITHER git repo. See `RISKGUARD_BACKLOG_ROADMAP.md` Wave 2 for the sub-tasks. What remains OPEN is that sub-task and the documented non-goal; the original blanket framing is closed.

Found because the operator proposed the experiment — *"if you try to go for 1000 contracts it might refuse"* — after this session's author had asserted, wrongly, that the ATM order path has no pre-trade gate at all.

**Measured, on `Sim101`, with `Sizing.MaxContractsPerAccount: 10` live in the config:**

```
nt_place_atm_order  MES SEP26  sell 1000
  -> status "submitted", calculatedQuantity 1000, bracket daefb3c5
  -> FILLED: quantity 1000, avgPrice 7740.50725 against a 7743 last
  -> unrealizedPnL -1213.75 the instant it filled, from entry slippage alone
```

**100× the configured cap, accepted without comment.** No guard event, no warning, no refusal.

⚠️ **THE CAP IS REAL — IT IS JUST REACTIVE.** `RiskGuardAddOn.cs:3822` does enforce it:

```csharp
if (pos.Quantity > limit)
{
    MarkRuleLockout(stateModel, "MAX_SIZE_BREACH");
    actions.Add(new GuardAction { ActionType = GuardActionType.FlattenPosition, ... });
}
```

That is a predicate over a position **that already exists**. With `AuditIntervalSeconds: 10`, the live sequence is: order accepted → filled → up to ~10s → force-flatten, which slips again on the way out. At 1000 contracts on a 50K funded account the entry slippage alone (**-$1,213 measured, on a quiet overnight book**) is 2.4% of the account before the sweep has run once. The control exists and cannot arrive in time. [[configured-evaluated-enforcing]].

⚠️ **AND THE BRIDGE — THE PATH AN AGENT USES — CHECKS SIZING NOWHERE.** `grep MaxContracts addons/McpBridgeAddOn.cs` returns **nothing**. The readers of `MaxContractsPerAccount` are `GuardRules.cs` (evaluates it for the inventory display), `RiskGuardAddOn.cs` (builds it into a profile, then the reactive rule above), `RiskGuardWindow.cs` (lets you edit it), and `TradeCopierEngine.cs` (sizes copies with it). **Four readers, and the one that places the order is not among them.**

`PlaceAtmOrder` does have two pre-trade gates, which is what makes the gap easy to miss: a live-account `confirmLive` guard, and `BridgeLockoutGate.Evaluate`. A path with *some* refusals reads as a path with refusals.

⚠️ **BANDED `P0` FOR TWENTY MINUTES, ON AN ASSUMPTION THE OPERATOR THEN DISPROVED.** The `P0` rested
on *"a mistyped quantity is account-ending before anything can react"*, inferred from 1000 filling on
`Sim101`. The operator tried **501 on the LIVE funded account** and it was **REJECTED** — and the
refusal is not ours:

```
Order='613562532433/TAKEPROFITPRO524207503'  New state='Rejected'  Quantity=501  Error='Panic'
  "Your maximum order quantity has been met... Limit: 60  Current: 501.  Scope: M..."
```

**The prop firm caps this account at 60 contracts per order.** `Sim101` filled 1000 because a
Simulator has no such desk. So the exposure is **not unbounded — it is the band 11 to 60**, where the
broker allows and the configured cap of 10 says no and nothing enforces it. Six times the intended
size, not a hundred, and the reactive `MAX_SIZE_BREACH` flatten still arrives within
`AuditIntervalSeconds`. That is a `P1`.

⚠️ **The band letter was re-derived, not defended.** It is recorded here rather than quietly
corrected because the original reasoning was sound and the *input* was wrong: a Simulator fill was
read as evidence about a live desk. [[test-doubles-are-not-evidence]] — a Simulator does not enforce
the broker's risk desk any more than a stub enforces `OrderState`. ⚠️ **And `Scope: M...` is
TRUNCATED in the log**: whether 60 is a micros-scoped limit with a lower ceiling on full-size `ES` is
**unmeasured**. Do not assume it scales — 60 `ES` is $3,000/point and would restore the `P0`. Measure
it before relying on this band.

⚠️ **A THIRD SYSTEM SAW IT, AND IT IS NEITHER OF THE TWO ABOVE.** The `Sim101` probe tripped
`RiskGatekeeper`, the strategy-side pre-trade half: `*** ACCOUNT BLOWN *** Sim101 | Drawdown
$3,685.00 >= Limit $2,000.00`. It detected the damage the guard only observed and the bridge never
checked — on the one path it covers. [[riskguard-third-risk-system]]: *"what is my maximum size?"* now
has **four** answers — the bridge's (none), the guard config's (10), the prop firm's (60), and
`RiskGatekeeper`'s drawdown proxy.

**The fix is a pre-trade quantity check on every bridge order path**, refusing rather than reporting, keyed to the same config value the display already shows — and `nt_place_oco_order` / `nt_place_order` need auditing for the same hole in the same commit. ⚠️ Do not fix it only in `PlaceAtmOrder`: [[a-second-reader-of-the-same-state]] is this repo's most repeated shape, and there are at least three order entry points.

⚠️ **A CORRECTION THIS ENTRY EXISTS TO RECORD.** Session 58 first reported that a funded-account order placed during an active lockout proved *"the bridge's ATM path accepted the order with no pre-trade refusal"*. **That was wrong.** The gate is there, and it allowed the order for a correct reason: `LockoutBinds` (`RiskGuardAddOn.cs:224`) contains

```csharp
if (state.LockoutWasShadowOnly) return false;
```

and the 03:31 lockout was `SHADOW_LOCKOUT` (`CONSECUTIVE_LOSS_BREACH`). **A shadow lockout must not bind, or `shadow` would be enforcing.** In `live` that lockout binds and the order is refused pre-trade. So the lockout half was the system behaving correctly and the author reading a `shadow` observation as a defect — [[configured-evaluated-enforcing]] in the OPTIMISTIC direction, and the reason the sizing hole underneath went unnoticed for the length of a session.



### P2-154. `nt_place_atm_order` still accepts a breakeven pair the addon will refuse, so the operator learns at placement instead of at the schema — OPEN, split out of `P2-141` 2026-08-18 (session 59)

**⏳ FIX LANDED 2026-08-21 (session 63), pending deploy + Sim re-validation.** New
`mcp/lib/atm-breakeven.js` refuses an EXPLICIT `offset >= trigger` pair at the MCP tool boundary,
before the round-trip, naming both values; wired into `nt_place_atm_order` in
`mcp/nt-mcp-server.js`. The addon's `PlaceBracket` → `ValidateBreakevenPlacement` refusal is KEPT
(the authority; the bridge is one of several callers). Fires only on an explicit pair (never
assumes the addon's defaults), so it cannot forbid a pair the addon accepts — the P3-111
false-refusal class the copier wrapper's mode-check comment warns about. 7 JS tests (node --test
73/73), consistent with the house standard for JS wrapper modules (negative controls, no mutation
battery). **Stays OPEN until deployed and re-validated on Sim** (a bad pair is refused before
submit).

`P2-141` closed the load-bearing half: `DynamicAtmManager.PlaceBracket` now refuses
`BreakevenOffsetTicks >= BreakevenTriggerTicks` before anything is created, naming both values.

The wrapper half is untouched. `McpBridgeAddOn.cs` reads `breakevenTriggerTicks` and
`breakevenOffsetTicks` straight into `AtmStrategyConfig` with no relation between them checked, so
the pair is accepted by the tool, travels to the addon, and comes back as an error. That is a worse
answer than a schema refusal, not a broken one — the trade is still refused.

⚠️ **The addon must KEEP its refusal regardless.** A schema that validates is not a guard that
refuses: the bridge is one of several callers, and a check that lives only in the wrapper is absent
for every other path. This is additive.

⚠️ **Do not implement it as a schema `default:`.** A `default` on a field the receiver merges is a
WRITE, which is how a wrapper came to answer a different question than the caller asked. Refuse and
name both values; do not substitute one.

**Where**: `nt8-mcp-bridge`, `McpBridgeAddOn.cs` around the `breakevenTriggerTicks` read. Its own
repo, its own suite, its own contract tests.

### P2-155. `_monitoring` and `_monitorTimer` are per-INSTANCE, so a recompile can leave the ATM sweep running on an orphaned manager — OPEN, split out of `P2-142` 2026-08-18 (session 59)

Carried as an unnamed remainder under a now-closed entry, which is why it gets an ID: a remainder
hiding under a closed entry is invisible to every count.

`DynamicAtmManager.Instance` is a `Lazy<T>` static, but the sweep's latch is not:

```csharp
private void EnsureMonitor()
{
    if (_monitoring) return;
    _monitoring = true;
    _monitorTimer = new Timer(MonitorTick, null, 5000, 5000);
}
```

Both fields are instance state. A NinjaScript recompile builds a new assembly in the SAME process
and replaces the statics, so the new `Instance` sees `_monitoring == false` and starts a second
timer — while the previous manager's `Timer` is still referenced by the runtime and still firing
`MonitorTick`. Neither is disposed by the swap.

⚠️ **This is the same shape the recompile family keeps producing** — a latch whose scope is narrower
than the thing it is latching. `P1-143` was per-instance retry budget (a compile handed a refused
stop a fresh budget), and the closed arming entry was per-instance arm state. Ask what a compile
resets before trusting any latch.

**Not yet measured, and that ordering matters.** What is known is the scope of the fields, which is
read from the source. What is NOT known is whether NT8 actually keeps the old timer alive across a
compile, or collects it with the old assembly — and the two possibilities are a duplicated sweep
versus nothing at all. **Measure before fixing**: count `MonitorTick` executions across a
deliberate recompile with a bracket registered. A fix built on the untested half would be a guess
with a mutation battery wrapped around it.

**Where**: `addons/DynamicAtmManager.cs` `EnsureMonitor` / `_monitoring` / `_monitorTimer`. Note the
comment already at `:823` reasoning about instance-versus-process scope for the dispatcher — the
same question was asked there and answered the other way, so read it first.

### P1-156. Arming ON START never seeds FSMs, so after every recompile the guard is armed and covering nothing — ✅ FIXED 2026-08-18 (session 59), MEASURED LIVE on the funded account minutes after deploying v1.45.0

Found by checking coverage after a deploy, not by any test or gate. `nt_riskguard_state` returned
**zero FSMs** for `TAKEPROFITPRO524207503` while it held **MNQ SEP26 Short 6**, with `nt_health`
reporting the guard `loaded`, `shadow`, `isArmed: true`, `guarding: true`.

The event order after a recompile is the defect:

```
SUBSCRIBE          isArmed:false    SeedFsmsForExistingPositions runs HERE -- but the broker has
                                    not delivered positions yet, so it seeds nothing
CONNECTION_CHANGE  Connected        positions arrive; AuditPosition ->
                                    ExecutePositionUpdateDetails -> UpdateFsmOnPosition ...
INITIALIZE
ARMED_ON_START     isArmed:true     ... which returned early on `if (!_isArmed) return;`
```

Two guards conspire. `SubscribeToAccount` early-returns on `_subscribedAccounts.Contains`, so the
connection-change re-subscribe is a no-op and the seeding inside it never re-runs. And a **static**
position generates no further position update, so nothing seeds it afterwards — the gap lasts the
life of the trade.

⚠️ **THIS IS `P1-15` THROUGH A DIFFERENT DOOR, AND THAT IS WORTH MORE THAN THE FIX.** `P1-15` added
seeding to the RE-ARM path (`ToggleArmed`) for exactly this reason, with a test and a comment
saying that otherwise "the guard is armed and reports healthy while covering nothing".
`ApplyInitialArmState` — the OTHER path that sets `_isArmed = true` — never learned the same
clause. [[a-second-reader-of-the-same-state]]: count the sites before closing the ticket.

**Fixed** by seeding every subscribed account inside the armed branch of `ApplyInitialArmState`,
after `_isArmed` is set. Seeding is idempotent and makes no broker calls.

⚠️ **The tempting wrong fix gets its own mutant**: seeding on the DISARMED branch, or before
`_isArmed = true`, reads correctly and does nothing — the FSM paths return early while disarmed,
which is the very reason the gap exists.

⚠️ **A survivor exposed a hole in the FIRST test, not in the code.** With one account in the
fixture, a `break` after the first successful seed is undetectable. On the live box there are 97
accounts and the funded one is **not first**, so the account that matters is precisely the one a
first-only loop would miss. A two-account test closes it.

**Consequence today was observation, not protection**: the guard is in `shadow`, so nothing was
going to intervene. In `live` it would have reported healthy over an unguarded position.

**Evidence**: suite 3185 → 3191, `mutation/mutate_p1156.py` 4/4.

### P1-157. The auto-stop is never withdrawn when the operator attaches their own, so one position carries TWO stops — ✅ FIXED 2026-08-18 (session 59), the precondition for turning `OnMissing: AutoStop` on

Found while designing the `AutoStop` direction the operator asked for, not by a failure.

The operator forgets a stop, the guard places `RiskGuardAutoStop`, and then the operator attaches
their own bracket. The guard recognises the new stop and moves to `Protected` — and leaves its own
order working. **Both stay live.** On a fast move both can fill before the flat-teardown cancels the
survivor, which does not leave you flat, it leaves you **REVERSED** — the failure the guard exists
to prevent, arriving by the guard's own hand. Same shape as `P1-56` and `P1-140`.

Nothing detected it: `AssessCoverage` tests `covered < positionQty` for nakedness and treats
`covered >= positionQty` as fine, so OVER-coverage is invisible to the audit.

**Fixed** in `UpdateFsmOnOrder`: when a stop that is not the auto-stop is recognised and coverage
**excluding the auto-stop** reaches the whole position, the auto-stop is dropped from the
recognised set and its cancel is QUEUED, then logged as `AUTOSTOP_HANDOVER`.

⚠️ **THE CONDITION IS FULL COVERAGE BY SOMEONE ELSE, NOT THE APPEARANCE OF ANOTHER STOP**, and the
two directions are not symmetric: withdrawing eagerly strips the remainder of a partly-covered
position of its only cover — the guard cancelling the protection it just placed. A partial
operator stop therefore leaves the auto-stop alone, with its own test and its own mutant.

⚠️ **The cancel is QUEUED, never sent inline**: `_stateLock` is held there, and the teardown
comment a few lines above says a nested lock is re-entrant and only hides the violation.
`TestFsmOnOrder` gained a `DrainPendingCancels()` to mirror the live path, which already drains.

**Evidence**: suite 3191 → 3196, `mutation/mutate_p1157.py` **6/7 + 1 declared**.

⚠️ **The declared survivor is a GATE gap, not a test gap** — see `P2-158`. Lock scope is not
observable from a unit test: the stub `Account.Cancel` succeeds either way and the re-entrancy
hazard needs a concurrent caller. The real detector is a source gate, the agent-loop profile has
one (`lock_name="_stateLock"`), and it runs **only on loop-authored changes** — this fix was
hand-written, so nothing checked it.

### P2-158. The lock-discipline check exists in the agent-loop profile and NOT in CI, so it only guards code the loop wrote — OPEN, split out of `P1-157` 2026-08-18 (session 59)

`agent/nt8_riskguard.py:27` configures a `lock_name="_stateLock"` gate, and the loop reports
`[lock-scope] ok — no risk calls under _stateLock` on every round. That check does not exist in
`tools/`, so a HAND-WRITTEN change gets no lock-discipline review at all — which is exactly what
happened in `P1-157`, where a mutant putting `account.Cancel` under the lock survived.

⚠️ **This is the per-repo gate lesson turned inward**: not a gate missing from a sibling REPO, but
a gate missing from a sibling PATH into the same repo. Two ways code arrives, one of them checked.

**Where**: port the check to `tools/check_lock_scope.py` and wire it into the `checks` job. It must
brace-match rather than regex line-by-line, and it needs a NEGATIVE CONTROL — a gate that cannot
go red is worse than none, and four mutants have already beaten source checks in this project.
⚠️ Note `agent/nt8_riskguard.py:172` records a KNOWN false positive to preserve: `ArmGraceTimer`
under the lock is correct and required, because it only schedules a callback and makes no broker
call. Reviewers raise it every round; the ported gate must not.

### P1-159. A per-instrument cap is checked PER ORDER, so N orders of 1 build a position of N -- the cap does not mean what its name says — ✅ FIXED 2026-08-18 (session 60), `v1.48.0`

`InstrumentLimits["MNQ"].MaxContracts = 1` refuses a single 2-lot order and permits **two 1-lot
orders**, leaving a position of 2. MEASURED three times in one evening on
`TAKEPROFITPRO524207503`: a duplicate submission produced two 1-lot fills 99ms / 150ms / 26ms
apart, and on one of them the operator's hand-drawn stop covered 1 of 2 -- the FSM read `Protected`
while half the position was naked (`gap=1 (partially uncovered)`).

```csharp
if (e.Order.Quantity > perInstCap.MaxContracts)   // ONE order's quantity, not the position
```

⚠️ **THERE ARE TWO CAP MECHANISMS AND THEY READ DIFFERENT CONFIG.** The per-ORDER check reads
`InstrumentLimits` (config root). The per-POSITION check, `MAX_SIZE_BREACH` in the audit, reads
`profile.InstrumentProfiles` via `ResolveMaxContracts` -- and `Profiles` is **empty on the live
box**, so every instrument falls back to `Sizing.MaxContractsPerAccount`. Setting `InstrumentLimits`
therefore caps the ORDER and not the POSITION, which is the opposite of what the operator intends.

**Fix the class, not the config**: `ResolveMaxContracts` should consult `InstrumentLimits[root]`
before falling back to `DefaultMaxContracts`, so ONE config location drives BOTH enforcement points.
The alternative -- asking the operator to maintain the same numbers in two places -- is how they
come to disagree. [[a-second-reader-of-the-same-state]].

⚠️ Do NOT let the position check become the only one: refusing the oversized ORDER costs nothing,
while `MAX_SIZE_BREACH` FLATTENS, which is a fill and a commission to undo a mistake.


#### ✅ FIXED 2026-08-18 (session 60), `v1.48.0` — suite **3209/0**, battery **9/9**, 11 gates green

One dictionary, both enforcement points. `_config.InstrumentLimits` is merged into the resolved
profile inside `CreateDynamicProfile`, so `ResolveMaxContracts` keeps the signature `P1-149` gave
it and **both** of its callers are fixed by the same edit: the reactive `MAX_SIZE_BREACH` sweep and
`EffectiveMaxContracts`, the answer the MCP bridge gives a caller *before* it places an order. The
per-ORDER check in `ExecuteOrderUpdate` was left alone — it already reads the same dictionary, so
after this change the two sites cannot drift.

**The two caps combine by MINIMUM, not by precedence.** A cap is a maximum, and the minimum of two
maxima can never permit more than either surface intended, so the direction cannot fail unsafely.
Any precedence order silently discards one of the two configured numbers, and the operator who
tightens the losing one sees no change and concludes the guard is enforcing something it is not.
Both directions are asserted, and the battery mutates both — each one alone looks correct from a
test written against the other.

⚠️ **The merged dictionary is a fresh `OrdinalIgnoreCase` copy, and that is load-bearing twice
over.** The line it replaced was `baseProfile.InstrumentProfiles ?? new Dictionary<string,
InstrumentProfile>()`, which (a) **aliased the config object's own dictionary**, so merging in
place would have written derived caps into `_config.Profiles[i]` where the next save persists them
as though the operator had typed them — numerically identical on the first pass, and only visible
once they LOOSENED a cap and found the tighter derived value still there; and (b) supplied **no
comparer** on the fallback path, which would have made every instrument lookup case-sensitive so a
hand-edited `mnq` key capped nothing. `RiskGuardModels.cs` already warns about (b) in writing,
beside the `InstrumentLimits` declaration. Both are mutants, and (a) needed a test of its own that
resolves twice — a merge that mutates in place still returns the right answer once.

**Evidence.** 8 acceptance tests, 5 red at baseline; `mutate_p1159.py`, 9 mutants, **9 killed, 0
survivors**, wired into the `P2-107+P2-134+P2-108` bin (the lightest at 770s, against a 1119s
critical path, so CI should not get slower). Two of the eight tests were green from the start and
were kept deliberately: an **unlisted instrument keeps the account default** — the negative control
against a fix that applies the tightest configured cap to everything, which would otherwise pass
every positive assertion — and **the tighter wins when the PROFILE is the tighter one**, which the
obvious implementation (consult `InstrumentLimits` first and return) breaks with nothing else
noticing. [[detector-needs-a-negative-test]].

⚠️ **The loop went green in ONE round, which is when to trust it least.** The panel returned
`APPROVE_PARTIAL` on a quorum of one: `deepseek-v4-flash` degenerated again, returning **436
findings against a cap of 60**, was scored `UNPARSEABLE` and dropped. So the patch had exactly one
model reviewer and was read by hand before applying. The battery is the evidence, not the verdict.

#### What this does NOT close

* The per-ORDER check, `BLACKLIST_CANCEL` and `ORDER_FLOOD_LOCKOUT` all live in
  `ExecuteOrderUpdate` — which is `internal` and therefore perfectly reachable from a test — and
  **not one of the three has a single test**. Three enforcement rules with no coverage, in a method
  the suite can already call. **Filed as `P2-165`** rather than left as prose here -- a remainder
  hiding under a closed entry is invisible to every count. `P1-160` builds a fourth rule in the
  same method and has to construct that harness anyway, but it does not automatically cover the
  other three.
* ⚠️ **The rule inventory still describes the cap as `PerOrder` only.** Read live from the
  funded account minutes after deploying `v1.48.0`: the `InstrumentLimits` row reports
  `scope: PerOrder` and the note *"caps the size of an instrument; it does not block it"*. Both
  were true this morning and the scope half is now wrong -- the cap binds on the POSITION as well.
  `nt_riskguard_inventory` is the surface that answers "is the guard actually protecting me", so a
  stale scope there is the same class as the defect just closed: what a rule REPORTS disagreeing
  with what it DOES. Folded into the `P1-160` landing commit rather than given its own ID, because
  `GuardRules.cs` is a region of that ticket and editing it mid-run would collide with the patch.
  ⚠️ If `P1-160` lands without it, file it.
* `MAX_SIZE_BREACH` **flattens the whole position**, not the excess over the cap. That is the
  pre-existing rule and this entry deliberately did not change it, but it means the response to a
  1-contract overshoot on a 5-lot cap is a full exit. Worth an ID if it ever fires in anger.
### P1-160. A duplicate entry doubles position size with no rule against it, and the second fill is invisible to the operator — ✅ FIXED 2026-08-19 (session 60), `v1.49.0`

MEASURED **three times in six attempts** on the funded account, across two platforms:

| time | gap | result |
|---|---|---|
| 03:31:01 | 99ms | two Sell 1 -> position 2 |
| 03:33:27 | 26ms | two ATM entries -> two brackets, position 2 |
| 03:50:57 | 150ms | two Sell 1 -> position 2, stop covered 1 of 2 |

Tradovate's own order list shows two SEPARATE orders, so the duplication happens upstream of NT8 and
neither the bridge nor the guard causes it. The cause does not matter for the fix: **a second entry
for the same account, instrument and direction within a few hundred milliseconds is never
intentional**, and the guard is the only component positioned to refuse it.

⚠️ **THE HARM IS NOT THE SIZE, IT IS THE SILENT HALF-COVERAGE.** The operator sizes their stop for
the position they believe they have. On 03:50:57 the stop covered 1 of 2 and the FSM reported
`Protected` -- a naked half that looks protected on the chart and in the state. A fully naked
position at least announces itself.

**Where**: the order path beside the existing `MaxOrdersPerSecond` flood check, which is the same
shape but a different question -- that one counts orders per second across everything, this one asks
whether THIS entry repeats the previous one. Refuse the duplicate (cancel), do not flatten.

⚠️ Must not fire on legitimate scale-ins the operator intends, nor on a bracket's own legs, which
arrive 3-11ms after the entry fill and are the OPPOSITE side. Keyed on same-direction ENTRY orders.


#### ✅ FIXED 2026-08-19 (session 60), `v1.49.0` — suite **3263/0**, battery **23 killed / 1 declared**, 11 gates green

A second `OrderType.Market` entry for the same instrument root and side, within
`Overtrading.DuplicateEntryWindowMs` (default 1000ms), queues an intervention cancel and emits one
`DUPLICATE_ENTRY` naming both order ids, the instrument and the gap. It does **not** lock the
account out: the operator did not cause this, their platform did, and a rail that takes the session
away for a broker glitch is a rail that gets switched off.

#### ⚠️ THE TICKET WAS WRONG ABOUT THE EVENT PATH, AND THE LOG IS WHAT SAID SO

The rule shipped from the loop gated on `Submitted || Accepted`, copied from the rate governor next
door. Then the live log:

```
03:31:01.441  35921  Market Sell 1  Filled     <- the ENTIRE event stream for these four orders
03:31:01.540  35922  Market Sell 1  Filled
03:50:57.804  35950  Market Sell 1  Filled
03:50:57.954  35951  Market Sell 1  Filled
```

**Two of the three measured duplicates never produce a `Submitted` or an `Accepted` at all**,
because they were placed on the BROKER platform rather than through NT8 — which is how the operator
normally trades. The ATM entry in the same session logged its full lifecycle (`Initialized` twice,
`Submitted`, `Accepted`, `Working`, `Filled`), so this is not the log dropping states.

Thirteen acceptance tests were green over that gap, because every one of them synthesised the
NT8-native event order. [[test-doubles-are-not-evidence]] — the double here was not a stub, it was
**the event sequence I assumed**, and nothing but the log could settle it. The rule now has its own
gate including `Filled`; widening the governor's gate instead would have changed what it counts.
Cancelling a filled order is meaningless and `DrainPendingCancels` already declines to try, so on
that path the ANNOUNCEMENT is the entire product — which is exactly right, since the silent
half-coverage is the harm.

#### ⚠️ THE BATTERY FOUND TWO MORE, BOTH FALSE POSITIVES, WHICH IS THE DANGEROUS DIRECTION

Missing a duplicate leaves the operator where they were. Refusing something that is *not* a
duplicate takes away an order they meant. Both of these survived four loop rounds, two reviewers
and eighteen green tests:

* **A retry after a broker REJECTION was cancelled.** The entry is anchored at `Submitted`; the
  broker rejects it; the immediate retry lands inside the window against an order that no longer
  exists and is refused. No position and two refusals, from a rule meant to stop the operator
  holding twice what they intended. A `Rejected` or `Cancelled` anchor is now dropped.
* **The rule protected only the FIRST trade of the session.** Anchors are keyed by (instrument,
  side); once the key existed the record-new-anchor branch could never run again, so the anchor kept
  the timestamp of the first trade of the day and every later gap was measured from there. Trades
  two onward were unprotected and nothing said so. A non-duplicate entry now refreshes the anchor.
  Every test had opened exactly one trade, which is why the whole suite was blind to it.

**The pruning pass is gone.** Once the anchor refreshes it is redundant — the gap is checked at the
decision point, so an expired anchor cannot produce a false positive and the next real entry
overwrites it. Keeping machinery no behavioural test can distinguish is the shape
[[dead-safety-machinery-gate]] exists to catch.

#### What the rule deliberately will not do

⚠️ **`OrderType.Market` is a SAFETY clause, not an optimisation.** A long bracket's stop and target
are both sells, arrive 3-11ms apart (measured), and `IsPositionReducingOrder` returns false for both
while the position still reads Flat — the ordinary case at 3ms. Without the market restriction the
rule cancels the TARGET as a duplicate of the STOP and strips a live position of cover the operator
did place. A protective leg is never a market order, so the filter is drawn where it cannot reach
one. [[a-filter-that-matches-too-much]].

⚠️ **Copier orders are excluded.** If the LEADER suffers a duplicate the copier mirrors both legs;
cancelling the second puts the follower out of conformance, the reconciler corrects it, the guard
refuses it again. `CopierOrderNames.Follow` is now a shared constant read by both the copier's
`CreateOrder` and this exclusion, so a rename cannot disarm it in silence — there is a mutant for
that.

**One EXPECTED SURVIVOR is declared** and paired through `_battery.finish`: relaxing the enable from
`> 0` to `>= 0` is an *equivalent* mutant while `gapMs < dupWindowMs` guards the decision point. It
is kept because it stops being equivalent the day that check is removed, and the helper reports a
declared survivor that starts being KILLED as STALE. Its partner — deleting the gap check — IS
killed, by a frozen-clock test placing two events at the exact window boundary, which wall-clock
timing cannot reach on purpose.

#### The loop run

Four rounds, `NOT_CONVERGING`; round 3 exported as the last candidate to pass every gate and
arbitrated by hand. ⚠️ **Its patch also rewrote 11 unrelated comments** across three files — every
`⚠️` to `WARNING:`, a box-drawing rule to dashes, and two `//` lines to `///` — none of which any
gate or reviewer flagged. Filtered to the 5 intended hunks before applying. Filed upstream as
`CF-25`, with the obvious cause ruled out by measurement: the saved implement prompt carries all its
glyphs intact, so it is not the encoding path.

Of the arbiter's two upheld findings, one was right for a reason it did not give (the shared gate,
above) and one did not hold: for a platform duplicate the two orders are identical, so which one is
anchored has no observable consequence. Both are recorded at the site.

### P2-161. The loss cooldown fires only at the consecutive-loss LIMIT, so losses 1..N-1 cost nothing and it is redundant with the lockout it coincides with — ✅ CLOSED 2026-08-20 (session 61), v1.56.0 — suite 3455/0, battery 9/9 (shared with P2-162, P2-164)

**The cool-off now escalates.** `ApplyTradeJudgement` (the single once-per-trade judgement point in
`RiskGuardModels.cs`) arms `CooldownMinutes * 2^(n-1)` minutes for consecutive loss `n` while
`1 <= n < MaxConsecutiveLosses`; the cap itself is the hard `CONSECUTIVE_LOSS_BREACH` lockout, so no
cooldown is written there — two overlapping deadlines would only muddy which the audit shows. The
redundant setter in `ExecuteAccountItemUpdate` (fired only at the limit, off a possibly-unjudged
counter) is deleted; the cool-off has exactly one owner now.

⚠️ **The off-by-one and the win-reset are the two failures a coarse test cannot see, and both have
their own assertion.** `TestP2161_TheCooldownEscalatesWithTheStreak` checks the exact 2/4/8-minute
DURATIONS, not merely "a cooldown was set" — an exponent that charges loss `n` the loss `n-1` pause
fails it. `TestP2161_AWinResetsTheEscalationNotJustTheCounter` drives a win between losing streaks
and asserts the next pause returns to the BASE rather than continuing the ladder; the escalation and
the counter are the same field (`ConsecutiveLosses`) today, and that test is what would catch them
being split.

**The agreed 2/4/8/lockout table is config, not code.** The code default stays `CooldownMinutes 5`
because a missing setting must fail toward a LONGER pause; the operator-agreed base 2 with
`MaxConsecutiveLosses 4` is a `config.json` change to make at deploy. `CooldownMinutes` kept its name
rather than being renamed to `CooldownBaseMinutes`: the WPF window and `GuardRules.cs` both bind it,
and it still means "how long the cool-off is", now as the base rung.

⚠️ **`P2-164`'s loss definition is now the config key `Overtrading.LossFloorDollars`** (default 0.0 =
every negative counts, exactly today's semantics), classified as a `GuardNonRule` so
`TestUi3_...` forces it to stay accounted for. `TestP2164_TheLossFloorDecidesWhatCounts` proves a
sub-floor scratch is untouched at a $10 floor and — the negative control — that the default counts
the same $5 loss it did before. The `P2-164` measurement now flips a number, not a build.

**Original entry (the defect as filed):**

```csharp
if (state.ConsecutiveLosses >= _config.Overtrading.MaxConsecutiveLosses
    && _config.Overtrading.CooldownMinutes > 0)
    state.CooldownUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.CooldownMinutes);
```

With `MaxConsecutiveLosses: 3` that is: loss 1 nothing, loss 2 nothing, loss 3 a 5-minute cooldown --
*and* the 60-minute `CONSECUTIVE_LOSS_BREACH` lockout fires on the same tick, so the cooldown is
almost entirely subsumed by it. The ladder today is **nothing, nothing, 60 minutes**.

**The operator's stated requirement** (2026-08-18): *"any loss triggers me. consecutive losses more
so. so a tightening/increasing of the cooldown for every loss makes sense"*. Every loss gets a
cooldown; the duration escalates with the consecutive count; a win resets the ladder.

Agreed shape -- `MaxConsecutiveLosses: 4`, base 2, doubling:

| consecutive loss | pause |
|---|---|
| 1 | 2 min |
| 2 | 4 min |
| 3 | 8 min |
| 4 | hard lockout (60 min) |

⚠️ **A win must reset the ESCALATION, not merely the counter** -- they are the same field today but
need not stay so, and an off-by-one giving loss 3 the loss-2 pause is invisible to any test that
only checks "a cooldown was set".

⚠️ **What counts as a loss is NOT settled and is owned by `P2-164`.** Any negative realized
delta, however small? The three losses that locked the account out on 2026-08-18 were scratches of a
few dollars. Build the ladder with the definition behind a config key defaulting to today's semantics
(every negative counts), so `P2-164` resolves into a number rather than a rebuild.

### P2-162. The cooldown FLATTENS a filled position instead of refusing the entry, so a pause costs a fill, a commission and slippage — ✅ CLOSED 2026-08-20 (session 61), v1.56.0 — suite 3455/0, battery shared with P2-161

**Refuse first, flatten only as backstop.** `ExecuteOrderUpdate` now cancels an entry submitted
during a running cooldown, in the same block that refuses one under a lockout, exempting
position-reducing orders (`P1-44`) so it can never strip a live position of its exit. The
`COOLDOWN_BREACH` `FlattenPosition` in `EvaluateRules` STAYS as a backstop for a position that
already exists — a fill that beat the cancel, or one opened before the cooldown began — because
refusing future entries does nothing about a live one. The two are not alternatives.

⚠️ **The refusal is logged as `COOLDOWN_CANCEL`, a distinct rule id from `ENTRY_CANCEL`.** The audit
must name the cause, and the `P1-167` de-dup is keyed by `(rule, order)` — a shared id would let a
lockout refusal and a cooldown refusal on the same order suppress each other.
`TestP2162_AnEntryDuringCooldownIsRefusedNotFlattened` asserts the cancel, the `COOLDOWN_CANCEL`
label via the log observer, the reducing-order exemption, and — the negative control — that with no
cooldown running the same entry is untouched, so the refusal is keyed on the cooldown and not firing
unconditionally. No self-cure was needed as there was for `P1-172`'s streak refusal: `CooldownUntil`
is a deadline by construction and lapses on its own.

**Original entry (the defect as filed):**

`COOLDOWN_BREACH` emits `FlattenPosition` when a position is open during the cooldown window. So
entering during a cooldown gets you filled and then closed, rather than simply refused.

The lockout path next door already does it correctly: `ENTRY_CANCEL` cancels the entry order before
it fills, and is careful to exempt position-reducing orders (`P1-44`) so it can never strip a live
position of its protection. The cooldown should use the same mechanism.

⚠️ **Keep the flatten as a BACKSTOP, not the primary.** If a position somehow exists during a
cooldown -- a fill that beat the cancel, or a position opened before the cooldown began -- refusing
future entries does nothing about it. The two are not alternatives.

### P2-163. `AllowedInstruments` is read by one unit test and no production code, and its default PERMITS the minis — ✅ FIXED 2026-08-19 (session 61), v1.51.0 — suite 3332/0, battery 17/17, closed together with `P1-168`

```csharp
public List<string> AllowedInstruments { get; set; } =
    new List<string> { "NQ", "MNQ", "ES", "MES", "YM", "MYM", "CL", "MCL", "GC", "MGC", "RTY", "M2K" };
```

`PropFirmProtectionSuite.cs:26`. The only reader anywhere is
`TestPropFirmProfile_AllowedInstruments`. **Nothing in production consults it.** A reader of the
config would reasonably conclude instruments are governed by an allow-list; they are not, and the
default explicitly includes every full-size contract. [[dead-safety-machinery-gate]].

The live mechanism is `BlockedInstruments`, which is **default-ALLOW**: anything not enumerated is
permitted, including `SI`, `NG`, `HG`, `6E`, `ZB` and every future product.

⚠️ **Why this matters at the operator's settings**: with `DailyLossLimit: 250`, ONE full-size
contract at the guard's own catastrophe-stop distance is $200 -- 80% of the day in a single trade
(ES 16 ticks x $12.50; NQ 40 ticks x $5.00). The instrument restriction is not a preference, it is
what makes the daily limit coherent.

**Fix**: make the allow-list enforce, defaulting to the micros actually traded, with
`BlockedInstruments` retained as the day-by-day override (the operator asked to sometimes exclude
MNQ). Default-deny is the correct shape for a rule set that defines how one MUST trade.

**FIXED** in `v1.51.0`, **together with `P1-168`, because they are one change**: instrument permission
is ONE question -- "may this account trade this instrument" -- and it is now asked in exactly one
place, `ResolveInstrumentPermission`, by all three readers (the pre-trade `CanTrade`, the per-ORDER
refusal in `ExecuteOrderUpdate`, and a NEW per-POSITION sweep in `EvaluateRules`). Doing them
separately would have meant writing the position-side hook twice.
[[a-second-reader-of-the-same-state]].

* `AllowedInstruments` moved to `RiskConfig`, beside the list it pairs with, defaulting to
  `MNQ, MES, MYM, MCL, MGC, M2K`.
* `PropFirmProfile.AllowedInstruments` and `PropFirmProfile.BlockedInstruments` were **deleted, not
  deprecated** -- the precedent `P1-81` set for `ArmedForLive` in that same file. The second had
  **zero** readers, not even a test.
* The tautological test went with them: it built its own list and asserted `Contains("MNQ")` against
  that, so it could not fail for any value of the production default.
* The comparison is now case-insensitive. The old path used an ordinal `List.Contains` against an
  upper-cased root, so a lowercase entry a human typed **silently matched nothing** and the block did
  not exist. That was a live defect nobody had filed.

Suite **3332/0** with 16 new tests. Battery **17 mutants, 17 killed, 0 survivors**.

⚠️ **The two properties that matter most are the ones that stop this hurting more than the defect
did**, and both are asserted and mutated: an order that REDUCES a position is never refused (otherwise
an instrument becoming non-permitted traps the operator in it -- [[a-lockout-must-not-trap-you]]), and
an EMPTY allow-list permits everything rather than refusing every order
([[an-inapplicable-state-is-not-unreadable]] -- an upgrade that deserialized the list as empty must
not silently halt a funded account).

⚠️ **A non-permitted position is FLATTENED but does NOT lock the account out.** A size breach is a
discipline failure; a wrong instrument can be a mistyped symbol, and ending the session over one is
how a rail stops being tolerated.

⚠️ **THE TESTS WERE WRITTEN AFTER THE IMPLEMENTATION HERE**, because the defect was found mid-session
while closing `P0-166`. So "the tests pass" carries much less weight than usual for this entry and
**the battery is the primary evidence**. That is recorded in the battery header and in the CI bin
comment so the bin cannot be quietly dropped. One mutant in the first run *survived* and it was the
mutant's fault, not a coverage gap: it appended `if (false) { }` AFTER the `actions.Add(...)`, which
is a no-op. Rewritten to genuinely compute-and-discard, it dies. **A survivor is evidence only once
the mutant provably changes behaviour.**

⚠️ **What the completeness gate could not see.** `PropFirmProfile` is not a property of
`PropFirmProtectionConfig` and is not reachable from `RiskConfig`, so `TestUi3_EveryConfigLeafIsClassified`
-- which walks both roots -- **never inspected it**. That is how a safety-shaped field with a
permissive default survived for months while a gate reported every config leaf classified. Fifth-plus
instance of [[state-the-region-a-gate-inspects]]. `PropFirmProfile` now has one member (`Name`) and
still no referrer; an orphan-config-type gate is the unfiled follow-up.

### P2-165. Three enforcement rules live in a method the suite can already call, and not one of them has a test — ✅ CLOSED 2026-08-20 (session 61), filed 2026-08-18 (session 60)

Found while closing `P1-159`. `ExecuteOrderUpdate` is `internal`, takes a plain
`(object sender, OrderEventArgs e)`, drains its own pending cancels at the end, and both
`LogEventObserver` and `LogEventMessageObserver` are available to assert against it. It is
straightforwardly reachable from a test. Three rules inside it have **zero** coverage:

| rule | what it does | tests |
|---|---|---|
| `ORDER_FLOOD_LOCKOUT` | > N distinct orders in 1s → lockout + cancel | 0 |
| `BLACKLIST_CANCEL` | instrument root in `BlockedInstruments` → cancel | 0 |
| `PER_INSTRUMENT_CAP_CANCEL` | order quantity over `InstrumentLimits[root]` → cancel | 0 |

`grep` for each rule id across `tests/` returns nothing. This is not "hard to test and therefore
untested" — it is untested with the harness already sitting there.

⚠️ **`BLACKLIST_CANCEL` and `PER_INSTRUMENT_CAP_CANCEL` are the two rules carrying the operator's
2026-08-18 discipline contract** — every full-size future blocked, and `MNQ`/`MGC`/`MCL` capped at
one. `P1-159` gave the per-instrument cap a second enforcement point on the POSITION and mutation
coverage to go with it. The per-ORDER halves of both rules are still proved by nothing.

⚠️ Both rules are **cancel** paths, which is the asymmetric direction: `P1-44` exists because a
rate-limit cancel once stripped a live position of its protective stop. `BLACKLIST_CANCEL` has
**no `IsPositionReducingOrder` guard at all** — read it before assuming that is safe. If a
blacklisted instrument is somehow already open, the rule as written would cancel the stop covering
it. That is a hypothesis from reading, not a measurement; the test that settles it is the point of
this entry.

**Do this as characterisation first** — assert what the code does today, then decide what is wrong.
`P1-160` builds a fourth rule in the same method and has to construct this harness anyway; if it
lands without covering the neighbours, this stays open on its own.

✅ **THE HARNESS NOW EXISTS AND THIS ENTRY IS STILL OPEN.** `P1-160` landed the fourth rule in
this method and with it `P1160Setup` / `P1160Send`, which construct an `Account`, an
`AccountState` and an `OrderEventArgs`, drive the real `ExecuteOrderUpdate`, and capture the log
through `LogEventMessageObserver`. Reuse them — the remaining work is the assertions, not the
scaffolding. It did NOT cover the three neighbours; that was deliberate scope discipline, and it
is why this has its own ID rather than a sentence inside a closed entry.

⚠️ **AND `P1-160` MADE THE CASE STRONGER, NOT WEAKER.** Its own rule first shipped gated on
`Submitted || Accepted`, copied from the rate governor next door — and the live log then showed
that two of the three duplicates it was written for produce ONLY a `Filled` event, because they
were placed on the broker platform. Thirteen green tests did not notice, because every one of them
synthesised the NT8-native event order. **All three rules here share that gate.** Whether
`BLACKLIST_CANCEL` and `PER_INSTRUMENT_CAP_CANCEL` can see an order the operator placed from
Tradovate at all is now an open question with the evidence pointing the wrong way, and it is the
first thing to measure rather than the last.

#### ✅ CLOSED 2026-08-20 (session 61) — `v1.53.0`, suite **3404/0**, battery **14/14, no survivors**

Written as characterisation, as the entry instructed. **Sixteen tests; fourteen passed on the first
run.** The two that failed are the whole finding, and they were not the ones this entry predicted.

##### ⚠️ The entry's own table was stale before it was worked

It listed three rules with zero tests. By the time it came up, `BLACKLIST_CANCEL` had **four**,
added by `P1-168` — including `TestInst_P1168_AnExitOrderIsNeverRefused`, which is precisely the
guard this entry hypothesised was missing from it. Counted with `grep -c` before writing a line, not
after. [[closures-do-not-propagate-backwards]] — an entry describes the repo on the day it was
filed, and this one was two sessions old.

##### ⚠️ The hypothesis was right about the wrong rule

The entry warned that a cancel path with **no `IsPositionReducingOrder` guard** would strip a live
position of its exit, and pointed at the blacklist. The blacklist had been fixed. The
**per-instrument cap — which the entry did not suspect at all** — still had none, and it is the one
where the trap is *reachable* rather than hypothetical:

> `P1-160` measured the platform turning two 1-lot MNQ entries into a position of **2**, three times
> in six attempts, under the operator's configured MNQ cap of **1**. The flatten of that position is
> a **2-lot order against a cap of 1**.

So the guard cancelled the operator's own exit and left them holding the oversized position the rule
exists to prevent, with no way out but to fight it one lot at a time.
[[a-lockout-must-not-trap-you]] — third instance, and the same lesson each time: **the refusal half
is the easy half; the quantity clamp is the load-bearing one.**

##### The fix, and why the clamp is not optional

```csharp
bool capExitWithinPosition = capOpenQty > 0
    && IsPositionReducingOrder(e.Order, instState)
    && e.Order.Quantity <= capOpenQty;
```

⚠️ **`IsPositionReducingOrder` asks about DIRECTION ONLY.** A `Sell 5` against a `Long 1` satisfies
it. Exempting every reducing order — the obvious one-line fix, and the exact shape of the guard
`P1-168` put next door — would let a single order close 1 and open an oversized 4 the other way,
**making the cap opt-out by holding one lot.** The exemption is the size that flattens and no more.
The blacklist needs no such clamp because a refusal has no size to clamp; that asymmetry is why
copying the neighbouring guard verbatim would have shipped a worse rule than the defect.

`mutation/mutate_p2165.py` group 1 mutant 2 is that mutant, kept because it is the one that reads as
a simplification.

##### What the other fourteen tests bought

Nothing was wrong with the rate governor — and that is the point of pinning it. Both corrections
recorded in its own comments were, until now, **proved by nothing**:

| pinned | was protected by |
|---|---|
| `P1-52` — a bracket sharing an OCO id counts as ONE decision | a comment |
| `P2-46` — distinct keys, not state transitions (the live log's "29–32 orders/sec" were transitions) | a comment |
| `P1-44` — the tripping order is not cancelled when it is the stop covering a live position | a comment |
| `P1-45` — the lockout carries a deadline | one `P0-166` test, asserting only this |
| the 1s window actually **evicts** | nothing |
| `> maxPerSecond`, not `>=` | nothing |
| `LockoutRuleId` attribution (`P0-166` clears the counter of whichever rule locked) | nothing |

Each has both directions: `ABracketSharingAnOcoIdCountsAsOne` is paired with
`DistinctOcoGroupsStillCount`, and `TheTrippingProtectiveOrderIsNotCancelled` with
`TheTrippingEntryOrderIsCancelled`, because "group by OCO" is satisfied by ignoring bracketed orders
entirely and "never cancel a protective order" is satisfied by never cancelling anything.
[[a-detector-needs-a-negative-test]]

##### Two behaviours characterised rather than changed

1. **`MaxOrdersPerSecond = 0` does not disable the rule; it falls back to 5.** In the same config
   section, `DuplicateEntryWindowMs = 0` *is* the documented off switch. Two settings, two readings
   of zero. Pinned by `TestFlood_P2165_AZeroLimitFallsBackToTheDefault` rather than reconciled —
   changing it is an operator-facing decision, and the operator who sets it to zero to switch the
   rule off currently gets a rule at 5.
2. **The entry's open question about broker-placed orders is answered, and the answer is that the
   gate is right.** All three rules are gated on `Submitted || Accepted || Working`, so an order
   that reaches the addon only as `Filled` — which `P1-160` measured for orders placed on the broker
   platform — is invisible to them. **Cancelling a filled order is meaningless**, so this is not the
   defect the entry feared. The coverage lives elsewhere: `P1-159` put the same cap on the
   **position**, which is what catches the broker-placed case. `TestCap_P2165_AFilledOrderIsNotCancelled`
   pins that division of labour so a later widening of the gate has to argue with it.

### P2-164. DECISION — what counts as "a loss" for the escalating cooldown ladder, settled by measurement rather than preference — ✅ RESOLVED 2026-08-20 (session 61), filed 2026-08-18 (session 59)

**Not an implementation entry.** `P2-161` builds the ladder; this entry owns the one input it
cannot pick for itself. Filed at the operator's request: *"The three small losses locking me out
might be an issue. Log it as something to work out later since I have two differing view points on
that but I want to do what is right and not what I think."*

#### The two viewpoints, both defensible

1. **Any negative realized delta counts.** The operator's own account of themselves — *"any loss
   triggers me"* — and the discipline contract is PRESCRIPTIVE, not fitted to observed behaviour
   (their correction, same session). Under this reading a scratch is a loss because the tilt it
   produces is not proportional to its size.
2. **A loss must clear a magnitude floor.** On 2026-08-18 three scratches of a few dollars each
   drove `ConsecutiveLosses` to 3 and took a 60-minute lockout on the funded account. Under the
   `P2-161` ladder those same three trades cost 2 + 4 + 8 minutes before the lockout. ⚠️ **A rail
   that charges eight minutes for a one-tick scratch is a rail that gets switched off** — and a
   disarmed guard protects nothing, which is a strictly worse outcome than a slightly loose one.

#### ⚠️ Why this must NOT be settled by asking the operator again

Both viewpoints are the operator's, held simultaneously, and they have said explicitly they want
the right answer rather than the one they currently favour. Re-asking returns whichever one is
uppermost that day. **The question is empirical and there is data.**

#### The measurement that decides it

The ladder's entire justification is that a trade taken shortly after a loss is worse than a
baseline trade. That is a testable claim about this account, not a general one:

* **Source**: `interventions.jsonl` (realized P&L per closed trade, with timestamps) cross-checked
  against `nt_extract_trades` / the NT8 trade journal. Prefer whichever has *entry* timestamps —
  the interval that matters is loss-close → next-entry, not close → close.
* **Measure**: expectancy of the next trade, bucketed by (a) the size of the preceding loss and
  (b) the elapsed gap. If post-scratch expectancy tracks baseline while post-real-loss expectancy
  drops, the floor is measured and its value falls out of the buckets. If both drop equally,
  viewpoint 1 is correct on this account's own evidence and the scratches count.
* **Also measure the COST**: total minutes each definition would have paused, over the same
  history. A definition that pauses a third of the session is not enforceable regardless of what
  the expectancy says.
* ⚠️ **Report the sample size and refuse a conclusion below it.** A handful of post-loss trades
  cannot separate these hypotheses, and a fitted floor from six observations is a preference
  wearing a number. If the data cannot decide, say so and take viewpoint 1 — the stricter rail —
  because an unjustified pause costs minutes and an unjustified permission costs the account.
* ⚠️ **The experiments of 2026-08-18 are not evidence about how the operator trades.** They were
  deliberate probes of the guard. Exclude that session from any bucket.

#### Interim, so `P2-161` is not blocked

Ship the ladder with the loss definition behind a config key (a minimum-magnitude threshold,
default `0` = every negative counts, matching today's `ConsecutiveLosses` semantics). Then this
decision changes a number in `config.json` rather than a build, and the measurement above can run
against real sessions while the ladder is already live. **`All configuration is persistent`** —
the key must round-trip the recompile like everything else.

Related: `P2-161` (the ladder), `P2-162` (refuse the entry rather than flatten the fill).

### P0-166. A lockout whose trigger is session-scoped but whose cure is a 60-minute timeout re-locks forever, and says "tradeable again" every hour while doing it — ✅ FIXED 2026-08-19 (session 61), v1.50.0 — suite 3295/0, battery 19/19, instance and class

⚠️ **This is a harder blocker on arming `live` than `P1-151`.** Measured on the funded account
`TAKEPROFITPRO524207503`, which has been cycling once an hour since 07:15Z:

```
14:16:17 LOCKOUT_LAPSED    Lockout deadline 2026-08-19T14:16:12Z has passed; the account is tradeable again.
14:16:17 SHADOW_LOCKOUT    Rule DAILY_LOSS_BREACH recorded a shadow-only lockout observation; no flatten executed.
14:16:22 LOCKOUT_CONFIRMED Lockout confirmed: all orders cancelled, position flat.
```

Eight identical cycles, 07:15Z through 14:16Z, five seconds from "tradeable again" to locked. It
will not stop on its own. In `shadow` the cancels were withheld, so nothing was enforced -- the
80 `ENTRY_CANCEL` events of that session all say `account is locked out` and all were withheld.
**Arm `live` on a day this fires and the account is locked for the session, with a false all-clear
once an hour that invites an order and then cancels it.**

**The class.** A lockout pairs a *trigger condition* with a *cure*. The cure must be capable of
clearing the trigger. Six sites set a timeout cure; four of their triggers are session-scoped
counters that only `SESSION_RESET` clears, so the deadline lapses into the same true condition:

| site | rule | trigger | what clears the trigger | timeout valid |
|---|---|---|---|---|
| `RiskGuardAddOn.cs:1918` | `DAILY_LOSS_BREACH` | session realized PnL under `PnLRules.DailyLossLimit` | session reset | ❌ |
| `RiskGuardAddOn.cs:1958` | `TRAILING_DD_BREACH` | drawdown off `PeakEquity` | session reset | ❌ |
| `RiskGuardAddOn.cs:4409` | `MAX_TRADES_BREACH` | `TradesToday` at the cap | session reset | ❌ |
| `RiskGuardAddOn.cs:4428` | `CONSECUTIVE_LOSS_BREACH` | `ConsecutiveLosses` at the cap | a WIN, or session reset | ❌ while flat |
| `RiskGuardAddOn.cs:2132` | `ORDER_FLOOD_LOCKOUT` | N orders inside 1 second | one second of time | ✅ |
| `RiskGuardAddOn.cs:4894` | operator `LockAccount(name, minutes)` | the operator asked | the operator's own intent | ✅ |

**The mechanism already exists and is already documented.** `EvaluateLockoutPhase` skips the lapse
when `LockoutUntil == DateTime.MinValue`, and the comment at `RiskGuardAddOn.cs:4113` states the
intent outright: *"MinValue means no deadline, NOT expired. LockAccount(name, -1) uses exactly that
to express an EOD lockout."* The three hard rails should have been using it from the start.

**The fix is not uniform, and that is the point.** Do not lock all four to EOD:

* `DAILY_LOSS_BREACH`, `TRAILING_DD_BREACH`, `MAX_TRADES_BREACH` -- EOD is correct and is what the
  prop firm itself enforces. Breaching the daily limit ends the day; a cure that hands the account
  back after an hour would walk it through the firm's real rail.
* `CONSECUTIVE_LOSS_BREACH` -- a timeout is the INTENDED cure ("cool off, then resume"), so the
  defect here is the other half: nothing clears `ConsecutiveLosses` when the lockout lapses, so it
  re-locks on the next evaluation with the account still flat. Clear the counter on lapse. ⚠️ Do
  not make this one EOD -- three scratches ending the day is exactly the outcome `P2-164` is open
  to decide, and `P2-161` replaces the flat 60 with the escalating ladder. This entry must not
  pre-empt either.

⚠️ **`LockoutMinutes` stops applying to three rules, and a config key that quietly stops meaning
anything is its own defect** ([[configured-evaluated-enforcing]]). Whatever shape the fix takes, the
inventory row for these rules must report the cure it will actually apply, not the config value it
no longer reads.

⚠️ **`LOCKOUT_LAPSED` names no numbers**, which is why eight hours of this read as routine. Neither
does `SHADOW_LOCKOUT`: *"Rule DAILY_LOSS_BREACH recorded a shadow-only lockout observation"* omits
the PnL and the limit, so the log cannot answer whether the breach was real. It was -- realized was
`-347.75` against a `250.0` limit -- but that had to be reconstructed from `nt_accounts` and
`SessionStartRealizedPnL`. Make both lines state the value and the bound.

⚠️ **Five further rules set `MarkRuleLockout` with NO deadline at all** -- `NEWS_SHIELD_LOCKOUT`,
`EVALUATION_TARGET_REACHED`, `MAX_SIZE_BREACH`, `FIRM_DAILY_LOSS_BREACH`, `FIRM_TRAILING_DD_BREACH`.
They inherit whatever `LockoutUntil` already held, so their cure depends on which rule fired before
them. `P1-45` is the precedent for the flag-without-a-deadline shape. Characterise before changing:
for the firm rules and the evaluation target, EOD is likely right already.

**FIXED** in `v1.50.0`. `ApplySessionScopedCure` sets `LockoutUntil = DateTime.MinValue` for the three
hard rails; `CONSECUTIVE_LOSS_BREACH` keeps its timeout and now clears `ConsecutiveLosses` when that
timeout lapses, keyed on a new persisted `AccountState.LockoutRuleId` so the clear cannot become a
blanket amnesty. Every lockout line now carries its numbers. Suite **3295/0**, battery **19 mutants,
19 killed, 0 survivors**, 11 gates green.

**Three things this entry got wrong on the first attempt, all caught by machinery rather than review:**

1. ⚠️ **A "fix" that contradicted a deliberate decision.** `LockAccount(name, minutes > 0)` sets the
   deadline and NOT `IsLockedOut`, which reads exactly like the `P1-45` flag-without-a-deadline shape
   inverted -- so it was "fixed". Three existing tests failed, and they were right: `P2-94` pins the
   flag to *indefinite/EOD* lockouts specifically, the deadline is what refuses a timed one, and
   `CanTrade` consults both. Reverted, with the reasoning left in the source so the next reader does
   not re-make it. [[a-wrong-red-test-enforces-itself]] in the reverse direction -- here the existing
   test was the spec and the new change was the error.
2. ⚠️ **Two of the new tests passed vacuously**, and the mutation battery is the only reason that is
   known. A fresh `AccountState` **already** has `LockoutUntil == MinValue`, so asserting `MinValue`
   after a breach passes whether or not the cure ran -- the mutant that emptied the helper survived.
   Every such test now starts from a live deadline (`UtcNow.AddHours(3)`) so the cure has to clear it.
   [[a-green-that-can-never-be-red]].
3. ⚠️ **The trailing-drawdown test was measuring the wrong rail.** `PnLRules.DailyLossLimit` DEFAULTS
   to `1000.0`, so a test that drove realized PnL to `-1100` to trigger a 1500 trailing drawdown
   breached the DAILY rule first; that locked the account, and the trailing rule's own
   `if (!IsLockedOut)` never ran. The test named one rule and proved another, and the mutant that left
   the trailing rail on a timeout survived. [[check-the-exemplar-belongs-to-the-class]]. The test now
   raises the daily limit out of the way and asserts that `DAILY_LOSS_BREACH` did **not** fire.

**`ResetAccountForNewSession` was extracted from the sweep loop** and is `internal`, because the
session boundary is now the cure for three rails and it had **zero** tests -- it was reachable only
from inside a `while` loop. The battery found that mechanically: the mutant that stopped it clearing
`LockoutRuleId` survived because nothing could call it. The body is unchanged.

⚠️ **`PnLRules.LockoutMinutes` now governs nothing at all**, and `Overtrading.LockoutMinutes` governs
two rules rather than three. Both are declared in `GuardRules.cs` as `GuardNonRule` and both `Reason`
strings were rewritten to say so, because a config key that quietly stops meaning anything reads
exactly like a protection the operator has set. [[configured-evaluated-enforcing]].

⚠️ **The operator's counters were NOT reset as part of this.** `TradesToday 16` and
`ConsecutiveLosses 16` on the funded account are real state from the 2026-08-18/19 probe session, and
`ConsecutiveLosses 16` against a `MaxConsecutiveLosses` of 3 means the consecutive-loss rail is
breached the moment it is evaluated. It will clear at the session boundary through the path this entry
just made testable. Verify it did, rather than assuming.

### P1-167. Every rule in `ExecuteOrderUpdate` refuses the same order once per state transition, so one order draws N cancels and N log lines — ✅ CLOSED 2026-08-20 (session 61), v1.54.0 — the DUPLICATE_ENTRY half closed 2026-08-19 with `P0-171`; the other four rules closed here

Measured on the funded account the day `v1.49.0` went out. One duplicate order, three refusals:

```
06:19:07 DUPLICATE ENTRY CANCELLED: order 35996 on MNQ Buy duplicated anchor order 35993 (881ms within 1000ms window).
06:19:07 DUPLICATE ENTRY CANCELLED: order 35996 on MNQ Buy duplicated anchor order 35993 (884ms within 1000ms window).
06:19:07 DUPLICATE ENTRY CANCELLED: order 35996 on MNQ Buy duplicated anchor order 35993 (917ms within 1000ms window).
```

Three `PendingCancelEntry` values queued for one order, three log lines, and three *different* gap
values because each state transition recomputes the gap against the same anchor.

**It is not specific to the new rule** -- the per-instrument cap does it too, same session:

```
06:14:19 Cancelled order 35972 because quantity 3 exceeds MNQ cap (1).   (x3)
```

So this is `ExecuteOrderUpdate`'s shape, not `P1-160`'s: the method runs per order event, and no
rule inside it records that it has already refused a given order. `P1-160` only made it visible, by
widening its own gate to include `Filled` -- at `Submitted || Accepted` the count was 2 rather
than 3, which is equally wrong and simply looked less like it.

⚠️ **The consequence is not only noise.** `SHADOW_PENDING_CANCEL` reported 96 withheld cancels
that session against far fewer offending orders, so the one number an operator would use to judge
how often the guard intervened is inflated by a factor of the platform's state-transition count --
a quantity no rule controls and the broker chooses. [[measure-the-deployed-system]].

⚠️ In `live` the second and third cancels land on an order that is already `Cancelled` or `Filled`.
`Filled` is terminal and `DrainPendingCancels` drops it, so the likely outcome is a no-op -- but
"likely" is doing load-bearing work in that sentence and it has never been measured against
`Provider31`. [[the-simulator-re-ids-nothing]].

⚠️ Fix the class: one refusal per order per rule. The natural seam is a per-account set of
already-refused order references, cleared where `RecentEntryAnchors` is. Do **not** fix it by
narrowing the state gate back down -- that reintroduces the `Filled`-only blindness `P1-160`
measured, where 2 of 3 live cases arrived as `Filled` and nothing else.

#### ✅ CLOSED 2026-08-20 (session 61) — `v1.54.0`, suite **3434/0**, battery **10 killed + 1 declared EXPECTED SURVIVOR**

The class, not another instance. `AccountState.MarkRefusedOnce(ruleId, order)` returns true the
first time a rule refuses an order and false every time after; the caller queues its cancel and
writes its log line only on a true. Applied to **all four** rules in the method —
`PER_INSTRUMENT_CAP_CANCEL`, `BLACKLIST_CANCEL`, `ENTRY_CANCEL` and the rate governor's cancel.

⚠️ **This entry had been "partially fixed" twice, both times for the rule it had just been measured
on.** `P0-171` closed it for `DUPLICATE_ENTRY` and left the neighbours, which is why it stayed open
under its own ID. The entry said in as many words that this is `ExecuteOrderUpdate`'s shape rather
than one rule's. [[fix-the-class-not-the-instance]]

##### Keyed by (rule, object reference), and both halves of that key are load-bearing

**Per rule**, because two different rules may each legitimately refuse the same order once. A single
shared set would let the first rule's refusal silence the second's — the operator fixes the
instrument, resubmits, and hits an unexplained cap refusal that was never reported the first time.
Fail-open, and it reads as a simplification. `TestP1167_EachRuleStillRefusesTheSameOrderOnceEach`
and group 1 mutant 2. [[a-second-reader-of-the-same-state]]

**By object reference**, for the reason already written above `DuplicateEntryEvaluatedOrders`:
Provider31 issues `Order.Id` as a submission GUID and **replaces it on accept** while the Simulator
never does, so an id-keyed set is written under one key and read under another — it never matches on
this operator's own provider, and every test passes on `Sim101`. Both directions are tested: an
order whose id *changes* mid-flight draws one refusal, and two genuinely different orders *sharing*
an id draw two. [[the-simulator-re-ids-nothing]]

##### ⚠️ Not a second copy of `DuplicateEntryEvaluatedOrders`

That set records that an order was **evaluated** — it must not be judged twice even when the verdict
was "not a duplicate", because a second evaluation against a moved anchor can reach the opposite
verdict. This one records that an order was **refused**, per rule. Merging them would make one
rule's refusal silence another's, which is the mutant above.

##### The null-state branch fails OPEN, deliberately

`instState` can be null in the blacklist and cap blocks (no known position, so no state to remember
in). The refusal then goes out **un-deduplicated** rather than being dropped. On a path that cancels
orders in a blocked or over-cap instrument, a silently dropped refusal is the direction that costs
money — and `instState == null ||` reads like defensive noise until you ask which way it fails.
`TestP1167_AnUntrackedAccountIsStillRefused` exists because that branch was unreachable from every
other test, so the fail-closed mutant would have survived. [[a-filter-that-matches-too-much]]

##### What this fixes for the operator

`SHADOW_PENDING_CANCEL` reported **96 withheld cancels** in one session against far fewer offending
orders. That number is the one an operator would use to judge how often the guard intervened, and it
was inflated by the platform's state-transition count — a quantity no rule controls and the broker
chooses. [[measure-the-deployed-system]]

⚠️ **The sets are cleared at the session reset**, with the anchors and for the same reason: an order
reference from last session can never come back, so keeping them is a leak on a process that runs
for weeks. The whole dictionary is dropped, not just the sets a rule happens to have created.

##### ⚠️ QUANTIFIED LIVE ON THE DAY IT WAS FIXED, and NOT yet live-validated

The ledger for 2026-08-20, split at the 15:43Z deploy of `v1.54.0`:

```
BEFORE: 228 refusal log lines for 74 distinct orders = 3.08 lines per order
        distribution: {1: 1, 2: 22, 3: 44, 4: 2, 8: 2, 9: 3}
AFTER : no refusals at all
```

**3.08 lines per order**, with 44 orders drawing exactly three — the entry's "one duplicate order,
three refusals" reproduced at scale, hours before the fix shipped. Two orders drew **eight** and
three drew **nine**.

⚠️ **THE "AFTER" WINDOW PROVES NOTHING AND MUST NOT BE READ AS SUCCESS.** There were no qualifying
orders after the deploy, so the absence of refusals is the absence of *input*, not evidence of
de-duplication. Silence is not success. The fix is live-DEPLOYED and live-UNVALIDATED; the next
over-cap or blocked order settles it, and the number to check is lines-per-order, not the count.

#### ✅ MEASURED AND RESOLVED 2026-08-20 (session 61) — take viewpoint 1, behind a config key. `tools/measure_post_loss_expectancy.py`

Run against every `EXECUTION_UPDATE` in `interventions.jsonl` and its archive — 467,581 ledger
lines, 6,269 usable executions, FIFO-reconstructed into round trips per (account, root). The tool
is committed so this is re-runnable rather than a one-off assertion.

##### The answer: the data cannot separate the hypotheses, so viewpoint 1 stands

That was the pre-agreed outcome for exactly this case, and the entry was right to specify it in
advance. But the measurement is more informative than "not enough data":

**On the funded account (n=31, the only discretionary sample):**

| preceding | next E[$] | n | vs baseline |
|---|---|---|---|
| scratch, ≤ $10 | −2.00 | 10 | **+15.90** |
| $10–25 | +18.12 | 2 | +36.02 |
| $25–50 | −43.33 | 3 | −25.44 |
| > $50 | +1.75 | 5 | +19.65 |
| **CONTROL: after a WIN** | **−50.19** | 9 | **−32.30** |

⚠️ **The premise the ladder rests on is not supported here — it is inverted.** Post-scratch
expectancy is *better* than baseline, and the worst trade on this account is **the one after a
win**. Taken at face value these numbers argue for a cooldown after WINS. They are not taken at
face value, because every bucket is n = 2–11 against a declared floor of 30.

**On the largest sample (`Sim101`, n=125):** post-loss −21.57 vs baseline, post-win **−21.32** vs
baseline. Within **25 cents of each other**. Whatever that measures, it is not tilt — it is
outlier skew: 73% of those trades lose and expectancy is still +$10.71, so two or three trades
carry the mean and every "vs baseline" figure is a statement about them.

##### ⚠️ And the large sample is the wrong sample, which is the finding worth keeping

`Sim101`, `SimCopy2`, `SimCopyTest1`, `Sim-ORB`, `Sim_All_Day_ORB`, `Playback101` — 274 of the 432
reconstructed round trips — are sim accounts carrying **copier-validation orders placed during
these hardening sessions** plus ORB-strategy traffic. Calibrating a discipline rail about the
operator's psychology against the agent's own test orders would be measuring the wrong thing
*precisely*, which is worse than measuring nothing. **Do not raise n by pooling them in.** The
sample is small because the operator has taken 31 round trips through this guard.

##### The cost side, which DOES give a usable answer

| a loss is… | losses | paused | lockouts |
|---|---|---|---|
| any negative | 21 | **198 min** (~28 min/day over 7 days) | 2 |
| \|loss\| > $10 | 10 | 36 min | 0 |
| \|loss\| > $25 | 8 | 32 min | 0 |
| \|loss\| > $50 | 5 | 18 min | 0 |

So the strict definition costs about half an hour a day and is **not** the "pauses a third of the
session" scenario that would make it unenforceable. The stricter rail is affordable.

⚠️ **The percentage column is a floor, not a ceiling.** Its denominator is the sum of each day's
first-entry-to-last-exit span, which came to 8,397 minutes over 7 days — 20 hours a day, because a
day containing one early and one late trade counts the gap between them. The first version divided
by wall clock across 11.6 days and reported 1.2%; both are too generous. **Read the minutes, not
the percent.**

##### ⚠️ The operator's objection is answered by the LADDER, not by the floor

This is the part that dissolves the dilemma. Their concern was three scratches costing a
**60-minute lockout** on 2026-08-18 — and the measurement reproduces it: "any negative" fires **2
lockouts** in 7 days. But under `P2-161`'s ladder those same three scratches cost **2 + 4 + 8 = 14
minutes**, not 60. The thing they objected to was the lockout, and the ladder already removes it.

**They do not have to accept a looser definition of "a loss" to avoid the outcome they disliked.**
Which means the two viewpoints were never actually in conflict — they were both responses to a
60-minute penalty that `P2-161` deletes.

##### What `P2-161` should therefore build

* **Definition: any negative realized delta counts.** Stricter rail, chosen because the data
  declined to justify a floor, and cheap enough to enforce.
* ⚠️ **Behind a config key** (`Overtrading.LossFloorDollars`, default `0.0`) so the answer lands as
  a number and not a rebuild — the entry's own instruction, and it stays right: the honest state of
  this measurement is "n = 31, revisit at n = 100", and revisiting must not mean recompiling.
* **Re-run this tool at n ≈ 100 discretionary round trips.** At the current rate that is roughly a
  month. If post-real-loss expectancy then separates from post-scratch, the floor is measured and
  its value falls out of the buckets — that is what the config key is for.

### P1-168. Every per-order rule shares a state gate that cannot see an instantly-filled market order, and `BLACKLIST_CANCEL` is the one with no position-level backstop — ✅ FIXED 2026-08-19 (session 61), v1.51.0 — suite 3332/0, battery 17/17, closed with `P2-163`

⚠️ **This is the operator's own discipline contract not binding.** "Every full-size future blocked"
is carried by `BlockedInstruments`, and `BlockedInstruments` has exactly two readers:

| reader | reached by | reaches a broker-placed market order? |
|---|---|---|
| `CanTrade()` (`RiskGuardAddOn.cs:251`) | NT8 strategies and the bridge, pre-trade | ❌ never consulted -- the order did not originate in NT8 |
| `BLACKLIST_CANCEL` (`ExecuteOrderUpdate`) | order events, gated `Submitted \|\| Accepted \|\| Working` | ❌ the state is `Filled` |

There is no third. **No rule anywhere checks whether an open POSITION is in a blocked instrument.**

**The measurement.** Of the 99 orders the guard saw on `TAKEPROFITPRO524207503` on 2026-08-19,
**17 arrived only as `Filled`** -- never `Submitted`, never `Accepted`, never `Working`:

```
35919 ['Filled']          35925 ['Suspended', 'Accepted', 'Working', 'Cancelled']
35920 ['Filled']          35926 ['Suspended', 'Accepted', 'Working', 'Cancelled']
35921 ['Filled']   ...    (resting orders DO show their lifecycle, so the log is not dropping states)
```

A market order that fills immediately is reported once, already terminal. Every rule gated on the
live states is blind to all 17.

**The class, and which instances are already covered.** This is the same shape `P1-159` closed for
the contract cap -- one enforcement point on the ORDER, none on the POSITION -- and it was closed
for that rule only:

| rule | order gate sees `Filled`-only | position-level backstop |
|---|---|---|
| `ENTRY_CANCEL` (lockout) | ❌ | ✅ the lockout flatten sweep |
| `PER_INSTRUMENT_CAP_CANCEL` | ❌ | ✅ `MAX_SIZE_BREACH`, via `P1-159` |
| `DUPLICATE_ENTRY` | ✅ (its gate includes `Filled`) | n/a -- refusal is the whole rule |
| `BLACKLIST_CANCEL` | ❌ | ❌ **nothing** |

So three of the four survive the blindness, two because a position rule catches what the order rule
missed and one because its gate was widened. `BLACKLIST_CANCEL` has neither. ⚠️ Do not "fix" this by
adding `Filled` to its gate: **cancelling a filled order is meaningless**. The correct response to a
filled order in a blocked instrument is to FLATTEN the position, which is a different action, in a
different method, and needs the arbiter's risk-reducing invariant to permit it.

⚠️ **This also explains `P2-162` rather than merely relating to it.** That entry asks why the cooldown
flattens the fill instead of refusing the entry; the answer is that for these 17 orders it *cannot*
refuse -- there is no cancellable state to refuse in. Refusing the entry is the right default and
flattening must stay as the backstop, exactly as that entry says, but the backstop is load-bearing
for a measurable fraction of real orders rather than a belt-and-braces afterthought.

⚠️ **Fold this together with `P2-163`.** That entry makes `AllowedInstruments` enforce as default-deny;
this one says instrument permission has to bind on the POSITION. They are one change -- "is this
instrument permitted for this account", asked at both enforcement points -- and doing them separately
means writing the position-side hook twice. [[a-second-reader-of-the-same-state]] is the failure mode
if they are split.

⚠️ `PropFirmProtectionSuite.cs:27` carries its OWN `BlockedInstruments` defaulting to
`ZB, ZN, 6E, 6B`. Whether anything reads it, and whether it agrees with the config's list, is
unmeasured -- and "what is blocked on this account?" having two answers is
[[configured-evaluated-enforcing]] in its most literal form. Establish that before adding a third
reader.

**MEASURED, then FIXED** in `v1.51.0`. That suite-side list had **zero** readers -- not one, not even
a test -- so "what is blocked on this account?" did not have two answers; it had one live list and two
dead ones. Both dead fields were deleted. The fix and its evidence are recorded under `P2-163`, which
this entry was closed together with, because instrument permission is one question and now has exactly
one answering method.

⚠️ **The blindness itself is NOT fixed and was not the fix.** `ENTRY_CANCEL`,
`PER_INSTRUMENT_CAP_CANCEL` and `BLACKLIST_CANCEL` still gate on `Submitted || Accepted || Working`
and still cannot see the 17-of-99 orders that arrive already `Filled`. What changed is that
instrument permission no longer *depends* on that gate, because it now also binds on the POSITION --
the same remedy `P1-159` applied to the contract cap. Adding `Filled` to a cancel path would be
meaningless: **you cannot cancel a filled order.** `P1-167` covers the remaining per-order rules, and
the open question there is not the count of log lines but whether each rule has a backstop at all.

### P0-169. Two invisible bytes made SIX mutation bins report `A MUTANT IS LIVE` for runs in which every mutant died — ✅ FIXED 2026-08-19 (session 61), v1.51.0 — gate added, both directions verified

`addons/RiskGuardModels.cs` was committed containing **two `\r\r\n` sequences** -- a bare CR before a
CRLF. Nothing visible changed. It compiled. The suite was **3295/0**. `git diff` looked normal. Every
line still ended in CRLF.

But Python opened in TEXT mode translates `\r\r\n` into TWO newlines, and every mutation battery
snapshots its targets exactly that way:

```python
ORIGINALS = {p: open(p, encoding='utf-8').read() ...}          # \r\r\n -> \n\n
open(path, 'w', encoding='utf-8', newline='').write(text)      # writes 2 EXTRA lines
```

So every battery that touched that file restored it **1028 lines long where HEAD has 1026**. CI's
post-battery check compares the tree to HEAD, found a difference, and reported
`<battery> did not restore the tree -- A MUTANT IS LIVE`. **Six bins failed identically**
(`mutate_p1160`, `mutate_p2119`, `mutate_p2101`, `mutate_p292`, and the two others in that set), each
printing `1 file changed, 1028 insertions(+), 1026 deletions(-)`, and in every one of them **every
mutant had already died and the battery had printed `OK`**.

⚠️ **`--ignore-cr-at-eol` was ALREADY on that check and could not help.** A bare CR is not a CR *at
end of line*; it is content. Three successive theories -- that I had flipped the file's line endings,
that `core.autocrlf` was normalising one side, that a BOM had changed -- were all wrong, and each was
disproved by measuring rather than by reasoning. What identified it was the arithmetic: `1028 - 1026`
is exactly `2`, and the file contained exactly 2 bad sequences.

⚠️ **A false `A MUTANT IS LIVE` is the most expensive alarm this repo can raise**, because the honest
response to it is to distrust the whole run -- which is the opposite of what a green battery earned.
[[weigh-the-quiet-failure-above-the-loud]] inverted: this failure was loud, and being loud about the
wrong thing cost more than silence would have.

**How it got there, and the idiom is still in use.** A patch script detects the target's line ending
and re-applies it:

```python
nl = '\r\n' if '\r\n' in s else '\n'
s = s.replace(old, new.replace('\n', nl))
```

If the script's OWN source was saved with CRLF -- which is what happens when it is written by a tool
on Windows -- then a multi-line string literal inside it already contains `\r\n`, and
`.replace('\n', nl)` rewrites each of those to `\r\r\n`. **The defect is invisible in the script and
invisible in its output.** The correct idiom normalises first:

```python
new.replace('\r\n', '\n').replace('\n', nl)
```

`tests/RiskGuardAddOnTests.cs` carried **60** of them from the same cause and was pure luck: no
battery targets the test file, so nothing had gone red yet.

**FIXED** by `tools/check_no_bare_cr.py`, the 12th gate, wired into CI. It walks `git ls-files`,
skips genuine binaries, and fails listing byte offsets. ⚠️ Verified in BOTH directions before being
trusted -- injecting one `\r\r\n` into `GuardRules.cs` makes it exit 1 naming the file and offset 98,
and removing it returns exit 0. It also refuses to pass vacuously: an empty `git ls-files` raises
rather than reporting a clean tree. 160 text files inspected, 0 offenders.

⚠️ **The batteries were NOT changed, and that is a deliberate choice with a cost.** The real defect is
that a battery snapshots in text mode and restores in binary-ish mode, so it can write back different
BYTES than it read. Fixing that properly means byte-exact snapshots in all 53 batteries, whose
scaffold has **11 different shapes** for the `ORIGINALS` line and where only 21 even define
`def restore()`. That is a real remaining hazard: any future bare CR from any other source will
produce the same false alarm, and the gate is what stands between. **If it recurs, fix the harness,
not the file.**

### P1-170. After a recompile the daily-loss rail reads a loss of ZERO on an account that is down $347, and the value it needs is already persisted beside it — ✅ FIXED 2026-08-19 (session 62), v1.52.2 — suite 3367/0, battery 5/5 + 1 declared, and the gate written for it found `P1-173` on its first run

Read live off `TAKEPROFITPRO524207503` minutes after `v1.51.0` deployed, from
`nt_riskguard_inventory`:

```json
{ "name": "Daily loss limit", "configPath": "PnLRules.DailyLossLimit",
  "state": "EvaluatedNotEnforcing", "currentValue": 0, "limit": -250 }
```

`currentValue: 0`. The account's realized PnL at that moment was **-347.75** against a **250** limit,
i.e. the rail was **breached by $96** and reporting a flat day.

**Mechanism.** `EvaluatePnLRules` computes `currentPnL = stateModel.RealizedPnL + UnrealizedPnL`, and
`RealizedPnL` is **not in `AccountPersistedData`**. `LastRealizedPnL` and `SessionStartRealizedPnL`
both are. So on every restart, recompile or hot-swap the working value resets to `0.0` while the two
numbers that DERIVE it survive:

```
LastRealizedPnL (-347.75) - SessionStartRealizedPnL (-1.50) = -346.25
```

The restore path had everything it needed and reconstructed nothing.

⚠️ **It self-heals on the next `AccountItemUpdate`** -- the first PnL tick recomputes
`rawRealized - SessionStartRealizedPnL`, the breach fires, and the account locks. So the exposure is
bounded: *from the moment the assembly reloads until the next fill*. That window is exactly when an
operator is most likely to place a trade, because a recompile is something THEY just did.
[[a-successful-compile-wipes-static-state]] -- same cause as the ATM bracket registry emptying,
different victim.

⚠️ **This is `configured / evaluated / enforcing` at its most literal**: the rule is enabled, is being
evaluated, has the right limit, and is reading a number that says there is nothing to enforce. The
inventory row -- the surface that answers *"is the guard actually protecting me"* -- shows
`EvaluatedNotEnforcing`, which is TRUE and completely misleading.
[[configured-evaluated-enforcing]].

⚠️ **`TRAILING_DD_BREACH` shares the input** and its `PeakEquity` IS persisted, so it is the asymmetric
case: peak survives, current does not. Check what that combination reports before assuming it is
merely blind rather than wrong in the dangerous direction.

⚠️⚠️ **MEASURED WORSE, same day: it does not merely under-report, it FABRICATES A LOSS.** After the
`v1.51.0` recompile left `RealizedPnL` at `0.0`, the next `AccountItemUpdate` computed
`newRealizedPnL - RealizedPnL` = `-346.25 - 0` and handed that to `RecordRealizedDelta` as **one
losing trade**. Observed on the funded account across the 16:44 reconnect:

| field | before | after | note |
|---|---|---|---|
| `ConsecutiveLosses` | 16 | **17** | a loss that never happened |
| `TradesToday` | 16 | 16 | unchanged, which is what exposes it |

A trade counter and a loss counter that disagree is the symptom; the phantom delta is the cause. **The
divergence is the only reason this was visible at all.**

⚠️ **This corrupts the exact counter `P2-161`'s escalating ladder will be built on**, and `P2-164` is
open on what should even count as a loss. Calibrating a ladder against a counter that gains a phantom
entry on every recompile would bake the artefact into the rail. **Fix this before `P2-161`, not after.**
[[a-fix-can-commit-its-own-defect]] is the risk if the ladder is built first.

**Fix**: reconstruct `RealizedPnL` in the restore path from the two persisted fields, and add the
field to `AccountPersistedData` so a future reader is not required to know the identity. ⚠️ A test must
drive the RESTORE, not just the arithmetic -- `P0-166` found that the session-reset path had zero tests
because it was reachable only from inside the sweep loop, and this path is reached the same way.

⚠️ **Two other rails were reading BREACHING values in the same snapshot and reporting
`EvaluatedNotEnforcing` purely because the mode is `shadow`**: `Max trades per session` at
`currentValue 16` against a limit of `8`, and `Max consecutive losses` at `16` against `3`. Those are
correct readings of real state left by the probe session, not defects -- but they mean **arming `live`
before the 22:00Z session reset would lock the account out immediately on two rails**, and the daily
rail would join them on the first fill. That is an operational note for whoever arms it, not a code
change.


**CLOSED 2026-08-19 (session 62), `v1.52.2`.** Suite **3367 / 0**, `mutate_p1170.py` **5 killed + 1
declared equivalent**, 13 gates green, 633 anchors / 0 broken.

**One line, in the restore path:**

```csharp
state.RealizedPnL = kvp.Value.LastRealizedPnL - kvp.Value.SessionStartRealizedPnL;
```

⚠️ **DERIVED, NOT PERSISTED, AND THE PLAN'S OWN "FIX" LINE ASKED FOR BOTH.** Adding `RealizedPnL` to
`AccountPersistedData` as well would create a SECOND source for one number, free to disagree with the
identity that defines it after any future edit that updates one and not the other — with no way to
tell which is right. The identity holds at every site that writes any of the three: `AccountItemUpdate`
sets `Last = raw` and `Realized = raw - SessionStart` in the same breath, and both session-reset paths
set all three so it is zero. One source.

⚠️ **IT READS `kvp.Value`, NOT `state`, AND THAT IS LOAD-BEARING.** The two fields it needs are
assigned from `kvp.Value` immediately above, so `state.X` would read identically today — and would
break the day those two assignments move below it. Reading the persisted record makes the line
order-independent. The mutant that swaps it is EQUIVALENT and is declared as such, kept to record the
choice rather than to score it; `_battery.finish` reports it STALE if it ever starts being killed.

**The tests reproduced the live numbers before the fix went in**, which is the part worth keeping:

```
[FAIL] the daily loss survives a recompile (got 0.00)
[FAIL] and the rail actually BREACHES ... $346.25 against a $250 limit
[FAIL] a recompile followed by an unchanged PnL tick invents no losing trade (got 17)
[FAIL] ConsecutiveLosses <= TradesToday ... violated at 17 against 16
```

`got 17` is the funded account's own number, regenerated from 16 by a restore plus one *unchanged*
PnL tick. That pins `P1-172`'s phantom loss as **caused by** this defect rather than merely
correlated with it.

⚠️ **TWO NEGATIVE CONTROLS, BECAUSE THE FIX IS A SUBTRACTION AND EVERY MEASURED NUMBER IS NEGATIVE.**
A flat session restores at zero rather than at its own $5,000 offset, and a WINNING session restores
as `+750` not `-750`. Inverting the operands still produces something loss-shaped, so it fails only on
a green day — which is the day nobody is looking at the daily-loss rail. Both mutants die only because
those two tests exist.

⚠️ **A TEST OF THIS FIX CAUGHT ITSELF ABOUT TO PASS VACUOUSLY.** The "does the rail actually breach"
assertion failed after the fix, and the cause was not the fix: `LoadPersistedState` deliberately
clears `_isArmed` (FR-30/31 — a restart must never silently re-arm), and `EvaluatePnLRules` returns an
empty list while disarmed. The assertion was about to be checked against a guard evaluating **no rules
at all**. Armed explicitly, with the reason in the test. Worth carrying separately: **after every
recompile the guard is disarmed until preflight re-arms it.**

**THE CLASS FIX: `tools/check_account_state_persisted.py`, the 13th gate.** Nothing about any
individual line here was wrong — the defect was an OMISSION, and an omission has no source location
for a reviewer to look at, which is the one kind of defect a gate is strictly better at catching than
a person. Every `AccountState` field must now be persisted, or declared runtime-only / derived /
persisted-elsewhere / reset-by-design, each with a reason. Watched failing in BOTH directions before
being wired: an unclassified new field, and a declaration naming a field that no longer exists.

⚠️ **IT IS A RATCHET, NOT AN AUDIT, AND SAYS SO.** Three fields sit in an explicitly UNREVIEWED
baseline. Writing justifications for all 37 would have made the file read as a review that never
happened; the guarantee is narrower and real — nothing NEW can be added without someone deciding.
It is also a NAME match, so a field that is persisted, written and never restored would still pass it.
That gap is stated in the file rather than papered over.

**On its first run the gate found [[P1-173]]**: `CooldownUntil` is written on a consecutive-loss
breach, read at `RiskGuardAddOn.cs:4545` raising `COOLDOWN_BREACH` → `FlattenPosition`, cleared on
session reset — and absent from `AccountPersistedData` entirely. A recompile clears an active loss
cooldown. That is this defect's class with a worse property: the action that defeats it is one the
operator already performs, six times on this box today.

**THE `TRAILING_DD_BREACH` REMAINDER, CHECKED RATHER THAN CARRIED FORWARD.** The ordering entry
asked whether the asymmetry — `PeakEquity` persisted, current value not — made that rail wrong in
the dangerous direction rather than merely blind. It did, conditionally, and the mechanism is a
**ratchet**:

```csharp
if (currentPnL > stateModel.PeakEquity)
    stateModel.PeakEquity = currentPnL;          // persisted, and only ever climbs
if (!firmTrailingInEffect && currentPnL < stateModel.PeakEquity - profile.TrailingDrawdown)
```

With `RealizedPnL` reset to `0.0`, `currentPnL` reads 0 for one evaluation. On a session whose
peak was NEGATIVE — a day that never traded green — `0 > PeakEquity` is true, so the phantom zero
is written into the peak *and persisted there*. The rail then measures every later drawdown from a
high the account never reached, and fires EARLY and permanently, on a value no log explains.

⚠️ **It did not fire on the measured account, and the reason is luck, not design**: that account's
persisted `PeakEquity` was **121.5**, so `0 > 121.5` was false and the ratchet was not fed. Any
session whose peak sat below zero at the moment of a recompile would have taken the other branch.

Fixed by this ticket rather than separately: the phantom zero was the only input that could feed
the ratchet, and the restore now reconstructs the real value before any rule sees it. **No new ID**
— the remainder is answered, not deferred, which is what the ordering gate demands before an entry
may be struck.

⚠️ **NOT live-validated.** The measurement that produced the ticket is reproduced deterministically in
the suite from the funded account's own figures. The reading to take after the next recompile is the
`Daily loss limit` row's `currentValue` in `nt_riskguard_inventory` on an account with a non-zero
session P&L.

### P0-171. A broker reconnect replays the day's fills, and the duplicate-entry rule times them by when the GUARD SAW them — 45 false refusals in one second — ⚠️ FIXED WRONG in v1.52.0, FALSIFIED LIVE, then ✅ FIXED 2026-08-20 (session 62) in v1.52.3 — suite 3370/0, battery 19/19, and the first fix is now a mutant. Read the correction below before the original closure record: the original is kept because the way it was wrong is the point

⚠️ **BLOCKS ARMING `live`.** Measured on `TAKEPROFITPRO524207503` within half an hour of `v1.51.0`
deploying, with no trading taking place at all:

```
16:44:39  CONNECTION_CHANGE  Connection status: Disconnecting, Connection: TPT
16:44:40  CONNECTION_CHANGE  Connection status: Disconnected,  Connection: TPT
16:44:42  CONNECTION_CHANGE  Connection status: Connecting,    Connection: TPT
16:44:44  CONNECTION_CHANGE  Connection status: Connected,     Connection: TPT
```

On reconnect NT8 **replays the session's order history**. 118 distinct orders arrived in that one
second, every one already in state `Filled`, and all 59 executions landed inside **two** seconds
(38 at `16:44:43`, 21 at `16:44:44`). Nothing was placed; nothing was traded.

The duplicate-entry rule then produced **45 `DUPLICATE_ENTRY` refusals**:

```
16:44:44 DUPLICATE ENTRY CANCELLED: order 36129 on MES Sell duplicated anchor order 36040 (152ms within 1000ms window).
16:44:44 DUPLICATE ENTRY CANCELLED: order 36135 on MNQ Buy  duplicated anchor order 36047 (140ms within 1000ms window).
16:44:44 DUPLICATE ENTRY CANCELLED: order 36139 on MES Sell duplicated anchor order 36040 (172ms within 1000ms window).
...
```

Every gap is 135-190ms, and every anchor is one of just four much older orders. **The rule measures
the interval between when the GUARD FIRST SAW two orders, not the interval between when they were
PLACED.** On a replay that interval is an artefact of the replay's own speed, and it is always inside
any sane window.

⚠️ **In `live` this queues 45 cancels off one reconnect.** The replayed orders are `Filled`, so
`DrainPendingCancels` drops them and the likely outcome is 45 no-ops -- but "likely" is load-bearing
and unmeasured against `Provider31`, and **any replayed order that is still `Working` would receive a
real cancel for an order the operator placed hours earlier**. [[the-simulator-re-ids-nothing]].

⚠️ **It is not confined to this rule.** In the same second `PER_INSTRUMENT_CAP_CANCEL` fired **32**
times on `TAKEPROFIT469067500` with 32 withheld cancels and 5 `SHADOW_LOCKOUT`s, all from the same
replay. Every rule inside `ExecuteOrderUpdate` treats a replayed order as a new one, so this is
`ExecuteOrderUpdate`'s shape and not one rule's -- the same finding as `P1-167`, reached from a
different direction, and it argues for fixing them together.

**FREQUENCY, measured rather than assumed.** There were **36** `CONNECTION_CHANGE` events on
2026-08-19 and **19** of them reported `Connected`, but exactly **ONE** was a genuine
`Disconnected -> Connected` cycle (down `16:44:40`, up `16:44:44`). Only that one produced a storm.
The other 18 were re-subscribes with no preceding disconnect -- including the two recompiles at
`15:18` and `16:20`, which logged `Connected` and replayed nothing.

So this is **rare and severe, not constant noise**: 45 of the day's 54 `DUPLICATE_ENTRY` events --
**83%** -- came from that single reconnect, and the other 9 were the genuine duplicates from the probe
session. ⚠️ Do not let the rarity reprioritise it downward: one disconnect is 45 queued cancels in
`live`, and a disconnect is not something the operator controls or can see coming.

⚠️ **The trigger is the DISCONNECT, not the `Connected` event.** A fix that keys on "we just saw
Connected" would fire on all 19 and suppress the rule during 18 occasions that never needed it.

**Fix direction.** The rule needs an age, not an arrival order:

* Prefer the order's OWN timestamp (`Order.Time`) over `stateModel.UtcNow()` when computing the gap,
  so a replayed fill from 03:31 is 13 hours old and cannot be a duplicate of anything.
  ⚠️ MEASURE what `Order.Time` actually holds on `Provider31` before relying on it -- it may be the
  fill time, the submit time, or unset. Evidence must name its provider.
* AND suppress rule evaluation during a replay window, keyed off `CONNECTION_CHANGE`, because the
  timestamp fix cannot help a rule whose input genuinely is "how many orders in one second"
  (`ORDER_FLOOD_LOCKOUT` would still see 118).
* ⚠️ Do NOT fix it by narrowing the state gate back to `Submitted || Accepted`: `P1-160` measured 2 of
  3 real duplicates arriving only as `Filled`, and 17 of 99 orders that day were `Filled`-only.

⚠️ **A `try/finally`-style suppression is not enough on its own**: whatever gates the replay must FAIL
LOUD if it is ever left on, or the duplicate rule silently stops protecting anything. Pair it with the
`DISARM_PERSISTED` pattern -- a line that says so on every evaluation while suppressed.



⚠️⚠️ **THE FIRST FIX WAS WRONG, AND A LIVE TEST IS THE ONLY THING THAT FOUND IT. Read this before
the closure record below, which describes a fix that suppressed nothing.**

`v1.52.0` armed the suppression on `Connected`. On 2026-08-20T00:34 the reconnect was reproduced
deliberately, through the MCP's new connect/disconnect, against the deployed `v1.52.2` — and it
produced **17 false refusals**, with the fix in place. The reason, in the log both times:

| event | 16:44 natural | 00:34 induced |
|---|---|---|
| `Connecting` | 42.444 | 43.519 |
| **replay burst** | **44.275 → 44.471** (45 refusals) | **44.619 → 44.686** (17 refusals) |
| `Connected` | 44.711 | 44.773 |

**THE REPLAY ARRIVES BETWEEN `Connecting` AND `Connected`.** `Connected` lands 240ms and 87ms
*after* the burst has finished, so a suppression armed there covers nothing at all. 53 order events
arrived in 67ms on the induced run; every refusal preceded `Connected`.

⚠️ **THE EVIDENCE WAS ALREADY IN THIS TICKET.** It quotes all four `CONNECTION_CHANGE` timestamps
and the refusal timestamps. `16:44:44.275 < 16:44:44.711` settles it in one subtraction. It was
argued about instead — the reasoning being that arming earlier would let a 1000ms window lapse
before the replay, which is true of `Disconnected` and irrelevant to `Connecting`.

⚠️⚠️ **AND THE TEST SUITE WAS DEFENDING THE DEFECT.** `TestP0171_ADisconnectDoesNotArmTheSuppression`
asserted that `Disconnected`/`Connecting` must NOT arm the suppression — the exact opposite of the
truth — and it PASSED. Worse, the battery's `group 1: armed on ANY connection status` mutant, which
is the **correct behaviour**, was scored KILLED against it. A green suite and a green battery, both
enforcing the bug. [[a-wrong-red-test-enforces-itself]], and the most expensive instance of it so
far: 15/15 mutants and 3352 passing tests were consistent with a fix that did nothing.

**THE CORRECTED FIX.** A new `OvertradingConfig.ReconnectReplayGraceMs`, default **5000ms**, armed
and RE-ARMED on every connection transition. The arm that covers the burst is the latest one before
it — `Connecting`.

⚠️ **NOT derived from `DuplicateEntryWindowMs`, and deriving it from that is what failed.** They are
unrelated quantities: one is how close two entries must be to count as duplicates, the other is how
long a platform takes to re-send a session. Measured `Connecting` → end-of-replay: **2027ms**
(natural) and **1167ms** (induced).

⚠️ **THE DEFAULT IS NOT "JUST ABOVE THE WORST SAMPLE", AND THE ARITHMETIC SAYS WHY:**

| grace | natural (2027ms gap) | induced (1167ms gap) |
|---|---|---|
| 1000ms — *what v1.52.0 used* | MISSES by 1027ms | MISSES by 167ms |
| 2000ms | **MISSES by 27ms** | covers |
| **5000ms** | covers, +2973ms margin | covers, +3833ms margin |

A 2000ms grace passes the induced regression test and fails the natural one by 27 milliseconds. With
only the induced sample it would have looked correct. Both reconnects are now regression tests at
their measured offsets, and a mutant pinned at 2000ms exists so the tighter of the two is proved to
bind.

**LIVE-VALIDATED: SIX RECONNECTS, TWO CONNECTIONS, ONE NATURAL AND FIVE INDUCED** through the MCP
connect/disconnect. Measured, not argued:

| sample | connection | `Connecting` -> burst end | `Connected` after burst | refusals |
|---|---|---|---|---|
| 16:44 natural | TPT | **2027ms** | +240ms | **45** (pre-fix) |
| 00:34 induced | TPT | 1167ms | +87ms | **17** (`v1.52.2` -- fix present and useless) |
| 00:48 induced | TPT | 1172ms | +71ms | **0** (`v1.52.3`) |
| 00:57 induced | LUCID | 1132ms | +57ms | **0** |
| 01:05 induced | TPT | 1134ms | +130ms | **0** |
| 01:06 induced | LUCID | 1014ms | +51ms | **0** |

⚠️ **`Connected` TRAILED THE BURST IN 6 OF 6 SAMPLES, BY 51-240ms. IT HAS NEVER ONCE PRECEDED IT.**
That is what makes arming on `Connected` structurally incapable of working, and it is now measured
rather than inferred. Worst `Connecting` -> burst-end is the natural event at **2027ms**, against a
5000ms grace: **2.5x margin**, and the natural event remains the binding case.

The 00:48 run is the direct before/after -- the SAME induced reconnect that produced 17 refusals on
`v1.52.2` produced 0 on `v1.52.3`, with all 53 order events still arriving. The rule still SEES the
replay; it stops refusing it. Suppressed, not blinded.

The 00:57 run carried real order history on a second connection: four same-side 1-lot MNQ market
entries replayed inside 11ms -- precisely the collision this rule exists to catch. Zero refusals;
pre-fix that shape yields three guaranteed false cancels.

⚠️⚠️ **THE SIMULATOR DOES NOT REPLAY, SO THIS DEFECT CLASS IS INVISIBLE TO SIM TESTING.** `Sim101`
was given four 1-lot MNQ market round trips (80 order events, GUID execution ids rather than
Provider31's numeric ones), then BOTH connections were cycled. `Sim101` contributed **zero** events
to either replay while the Provider31 accounts on the same connection replayed 53 and 10. A
Simulator account has no broker session to re-send.

The consequence is the reason to record it: **`P0-171` could not have been reproduced on `Sim101`**
however it was exercised, which is why 3352 passing tests and a 15/15 battery were all consistent
with a fix that suppressed nothing. Any future claim of "validated on Sim101" about replay
behaviour is empty. [[test-doubles-are-not-evidence]].

⚠️ **SCOPE OF THE 5000ms DEFAULT: every replay sample is `Provider31`.** LUCID and TPT are both
Provider31, so the six samples establish that the ordering is connection-INDEPENDENT within one
provider -- not that it holds across providers. The Simulator cannot supply that evidence because
it does not replay at all, and no other broker is instantiated on this box. Say "measured on
Provider31" and mean it. [[the-simulator-re-ids-nothing]].

⚠️ An early LUCID cycle replayed NOTHING because those accounts had not traded yet. Kept, because it
is the control that pins the mechanism: **the replay is driven by the ACCOUNT'S ORDER HISTORY, not
by the connection event.** No history, no burst, no false refusals -- which is also why a quiet
account cannot reproduce this defect however often it reconnects, and why the first LUCID run had to
be repeated after trading it.

⚠️ **A CONFOUND I CREATED AND ALMOST PUBLISHED.** The first `Sim101` attempt disconnected
`TPT/Simulator` and reconnected `TPT/Provider31`, so `Sim101` was never on the connection being
cycled; the replay contained Provider31 accounts only. The conclusion drawn from the retry is the
same one that attempt appeared to support, and it would have been unearned. Whichever connection was
cycled most recently reports as `Provider31`-only afterwards while the other picks up `Simulator+`,
so **connection/provider attribution must be re-read after every cycle, never carried across one.**

**Incidental, measured, and not a defect here:** account attribution MOVED between connection
objects across the reconnect — TPT went `8 accounts / Simulator+Provider31` to `3 / Provider31`,
LUCID `2` to `7`. The arming loop iterates `Account.All` and stamps every account state, so it is
insensitive to this. Anything that keys on connection identity would not be.

**CLOSED 2026-08-19 (session 62), `v1.52.0`.** Suite **3352 / 0**, battery `mutate_p0171.py`
**15 / 15**, no survivors; 623 anchors / 0 broken; 12 gates green.

**The fix is two runtime-only fields on `AccountState`, and NEITHER covers the other's case.**

```csharp
public DateTime ReplaySuppressionUntilUtc { get; set; } = DateTime.MinValue;
public HashSet<string> DuplicateEntryEvaluatedOrderIds { get; set; } = new HashSet<string>();
```

Neither is in `AccountPersistedData`, deliberately. `OnConnectionStatusUpdate` stamps the first with
`replayState.UtcNow().AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs)` on `Connected`
only; the rule guard became `if (isEntry && !replaySuppressed && !alreadyEvaluated)`, and the id is
recorded after the anchor block — reached whether the order was refused or became the anchor, and
NOT reached when the rule was suppressed.

⚠️ **A suppressed order does not ANCHOR, and that is the half that is easy to half-do.** Suppressing
only the refusal moves the false positive off the replay and onto the next genuine entry, by which
time the operator is actually trading. Mutant `group 4` is the one that proves it: it lets the FIRST
replayed order anchor and suppresses the rest, so the burst itself looks cured and no refusal is
logged during the replay.

⚠️ **The bound is the entire safety argument.** A suppression that never lapses is strictly WORSE
than the defect — the duplicate rule then protects nothing from the first reconnect of the session
onward and says nothing about it, while every test that asserts something is *not* refused passes.
Group 2 mutates it four ways: wrong unit, ten windows, hard-coded to the default, and
`DateTime.MaxValue`. All four die.

**Three tests exist only because a mutant demanded them**, and all three were green the moment the
fix landed — which is exactly why they needed the mutant rather than the other way round:

| test | mutant it kills |
|---|---|
| the boundary is at-or-before, to the millisecond | `<=` weakened to `<` |
| only `Connected` arms it, not `Disconnected`/`Connecting` | armed on any status |
| the length follows the CONFIGURED window, not a constant | hard-coded `1000`, which is the default |

The second matters more than it looks. The measured sequence is four events over five seconds —
`Disconnecting` 16:44:39, `Disconnected` :40, `Connecting` :42, `Connected` :44 — so arming on the
wrong one starts a 1000ms window **four seconds before the replay** and it has lapsed by the time it
is needed. The guard would carry a suppression, log nothing unusual, and refuse all 45 orders
anyway: a silent failure that looks identical to the fix simply not working.

**`OnConnectionStatusUpdate` is now `internal`**, for the same reason `ExecuteOrderUpdate` is. The
suppression has to be armed by the path a real reconnect takes; a test driving a stand-in proves
only that a field can be assigned. [[an-alarm-wired-to-a-dead-output]].

⚠️ **NOT live-validated.** Reproducing this needs a broker disconnect on the funded account, which
is not something to arrange deliberately. What is behind it is the measurement that produced the
ticket (45 refusals, 118 orders, 59 executions, four connection events with timestamps) reproduced
deterministically in the suite from those numbers, plus the battery. The next genuine reconnect is
the test; `DUPLICATE_ENTRY` count for that minute is the reading to take.

⚠️ **THE TICKET ALSO SAID TO KEY THE EVALUATED-ORDER SET ON `Order.Id`, AND THAT IS THE WRONG
KEY ON THIS OPERATOR'S PROVIDER.** The rule being edited says so 25 lines below the change --
*"Key by object reference, not `Order.Id`: NT8's OrderId is neither unique nor stable"* -- and it
was read past. Provider31 issues `Order.Id` as a submission GUID and **replaces it on accept**;
`Sim101` never does. Keyed on the id the set is written under the submission id and read under the
accepted one, so it never matches: `P1-167` would have stayed OPEN on the funded account while every
test passed, because the test provider re-ids nothing. [[the-simulator-re-ids-nothing]] -- never key
on a value the broker owns. The other direction fails OPEN: ids are not unique either, so two
genuinely different orders sharing one would see the second silently skipped.

Now a `HashSet<Order>` with an explicit `OrderReferenceComparer`. Explicit because
`EqualityComparer<Order>.Default` is whatever NinjaTrader's assembly decides `Equals` means -- a
decision made outside this codebase and free to move under a platform update.

⚠️ **AND NOTHING CLEARED THE SET ON SESSION RESET.** Runtime-only means nothing on DISK grows; this
guard runs for weeks between restarts, so it would have accumulated every order object of every
session for the life of the process, pinning each against collection. Cleared now, with the
suppression stamp beside it.

⚠️ **BOTH DEFECTS WERE FOUND BY CI, VIA THE NEIGHBOURING BATTERY, NOT BY THE ONE WRITTEN FOR THIS
FIX.** `mutate_p0171.py` was 15/15 green while both were live. What went red was `mutate_p1160.py`,
with two survivors -- and they had **opposite causes that looked identical in the output**:

| survivor | cause | resolution |
|---|---|---|
| the state gate is removed entirely | **a missing test** | an order whose FIRST observation is already `Rejected` is unreachable by the evaluated set, so nothing skipped it and it anchored. Test added; mutant killed again. |
| the same Order object on a later transition | **genuinely equivalent** | the evaluated set now skips the second event before `ReferenceEquals` is reached. Declared as an EXPECTED SURVIVOR with the condition that ends the equivalence. |

**The general shape, and it will recur: a fix that adds a second mechanism makes the first
mechanism's mutants survive, and "equivalent now" is indistinguishable from "test missing" in the
battery output.** Reasoning about it got one of the two right; only writing the test for each
showed which was which. ⚠️ Do NOT delete a guard because its mutant started surviving -- that
inverts the finding. The battery grew 15 -> 18 with group 7 covering the key and the bound.

⚠️ **THE TICKET'S STATED REASON FOR NEEDING BOTH MECHANISMS IS WRONG, AND THE FIX IS UNAFFECTED.**
Constraint D said a recompile empties the evaluated-order set exactly when NT8 replays the session,
so the reconnect stamp was needed to cover the post-recompile case. Measured on this box the same
day, from `interventions.jsonl`: **six addon restarts** -- 03:29, 04:55, 05:42, 05:43, 15:18, 16:20
-- produced **zero** duplicate events, while the day's only two clusters were 06:19 (9, the
per-transition over-count) and 16:44 (45, the reconnect). **An assembly reload does not make NT8
re-send the session; a reconnect does.** Nor could the stamp cover it if it did: subscribing to
`Connection.ConnectionStatusUpdate` does not replay past events, so a reload that re-subscribes
never sees a `Connected` event and arms nothing.

The two mechanisms are still both needed -- they answer two different defects, `P0-171` and
`P1-167` -- but not because either backs the other up. The corrected reasoning is in the source
comment beside the fields; the wrong one is recorded here rather than deleted because it was load-
bearing in the ticket the loop was given, and a spec premise that survives into a comment is how
[[a-comment-recording-a-defect-goes-stale]] starts.

**Provenance.** Ticket written by hand; `agent-loop --mode test --path-isolated` generated six
correct scenarios and unusable scaffolding (`CF-30`); patch mode ended `ARBITER_NEVER_RAN` after six
rounds because it could not see `_config.Overtrading.DuplicateEntryWindowMs` and invented 90 lines
of reflection to look for it (`CF-31`). The two-mechanism structure and the field placement in the
loop's patch were correct and were kept; the reflection was deleted and replaced with one property
path.

### P1-175. The suite has load-sensitive tests, and a flake during a mutant scores that mutant KILLED — ✅ FIXED 2026-08-20 (session 61) for its CAUSE, five machine-global temp filenames; the scoring rule it exploited is split out as `P1-179`

**Measured, not inferred.** Six copies of the suite run concurrently in **six separate git
worktrees**, all builds completed first so no build storm overlapped them:

```
wt0 3433/1   wt1 3425/3   wt2 3434/0   wt3 3426/2   wt4 3433/1   wt5 3428/2
```

Non-deterministic, never the same set twice. **Run alone, every one of those worktrees is
3434/0.** So this is not an environment difference and not a worktree artefact — the worktree was
eliminated as a variable deliberately, because `[[a-worktree-is-not-a-fresh-checkout]]` made it the
obvious suspect and it was the wrong one.

The names that recur: `CM2: the camelCase aliases and the flat legacy file still load`, `CM2: a
saved relationship reloads with its sizing mode and ratio table intact`, `CM2: a relationship
loaded from disk sizes a fill from its table`, and `HARNESS: every declared test method is invoked
by the runner`. The `CM2` cluster is copier-config round-trip through
`Globals.UserDataDir/RiskGuard/copier_config.json`.

⚠️ **`Globals.UserDataDir` is NOT the live NinjaTrader directory and this is not a live hazard.**
The stub roots it at `AppDomain.CurrentDomain.BaseDirectory/MockUserData`, i.e. inside each
worktree's own build output. Checked, because "the test suite writes the guard's real config" would
have been a far more serious finding than the one that is actually here.

#### ⚠️ Why this is P1 and not a test-hygiene nit

**A battery reads `Failed > 0` as a DETECTION.** Every one of them does — it is the scoring rule.
So a flake occurring during a mutant run marks that mutant **KILLED** when nothing killed it, and
the battery reports a better score than the suite earned. That failure is **silent**: it produces a
green run, no survivor, and no line anywhere saying a test flaked. The mutation batteries are this
repo's whole evidence standard, and this puts a non-deterministic inflation term on all of them.

The other direction is merely wasteful: a flake at the baseline aborts the battery with `baseline
is RED`, which is loud and costs one re-run.

⚠️ **GitHub CI cannot see this**, which is why it has never shown up. CI runs one bin per hosted
runner with nothing else on the box, so the suite is never under contention there. The local runner
is what exposed it, and the exposure is the reason to keep the local runner even though CI is green.

#### What to do

1. **Find the shared or timing-sensitive state.** The `CM2` cluster is the lead: a config
   write-then-read that loses a race under IO load, or a fixed filename within `MockUserData`
   colliding between the tests themselves rather than between processes.
2. ⚠️ **Then give the batteries a defence that does not depend on having found it.** The scoring
   rule `Failed > 0 == KILLED` cannot distinguish a detection from a flake, and a fix to three
   named tests does not change that. Re-running a mutant that appears killed, once, and requiring
   the same verdict twice would — at the cost of doubling only the killed cases.
3. `tools/ci_local.py` already retries a red baseline once and defaults `--jobs` well below the
   core count. Both are mitigations, not the fix, and both are commented as such.

#### ✅ CAUSE FOUND AND FIXED 2026-08-20 (session 61) — `v1.55.0`. ⚠️ The SCORING RULE it exploited is untouched and is now `P1-179`.

**The cause was five fixed filenames under `%TEMP%`**, and nothing subtler:

```
test_cm2_<name>.json      test_cm3_group.json       test_copier_group_config.json
test_p1_76_overlap.json   test_p1_75_prop_limits.json
```

`Path.GetTempPath()` is **machine-global**, so each of those is ONE file shared by every suite
process on the box. Two processes reach `File.WriteAllText` then `LoadFromDisk` on the same path and
one reads the other's fixture. The `CM2` cluster in the original measurement was exactly this.

⚠️ **Both obvious suspects were wrong, and eliminating them was the work.** The failure looked
like `[[a-worktree-is-not-a-fresh-checkout]]` — LF here, CRLF in a checkout — so a worktree run was
done ALONE first: **3434/0**, which killed that hypothesis. The second suspect was the suite writing
the live NinjaTrader config; `Globals.UserDataDir` is stubbed to
`AppDomain.CurrentDomain.BaseDirectory/MockUserData`, i.e. inside each worktree's own build output,
so that was wrong too and it was worth checking because it would have been far more serious.
Six concurrent runs in six **separate** worktrees with all builds finished first still failed, which
left machine-global state as the only candidate.

##### The fix, and the measurement either side of it

One helper, `TempFileForTest(name)`, tagged with the **process id plus a per-run GUID computed
once** — so a name is stable *within* a run, which callers rely on, and unique *across* concurrent
runs. All five sites now route through it.

| | 6 concurrent runs, separate worktrees |
|---|---|
| before | **0 / 1 / 1 / 2 / 2 / 3** failures of 3434, never the same set |
| after | **3434/0 twelve times over**, across two rounds |

`tools/check_tests_use_unique_temp_paths.py` is the 14th gate and stops a sixth site appearing. It
carries a **negative control** — it asserts it still flags the shape it forbids — and refuses to
pass if it finds zero `GetTempPath` sites, since a moved helper would otherwise make it report OK
forever. [[a-source-gate-must-assert-the-condition]], [[state-the-region-a-gate-inspects]]

⚠️ **THE GATE CANNOT REPRODUCE THE DEFECT IT PREVENTS, AND IS A SOURCE CHECK FOR THAT REASON.** CI
runs one bin per hosted runner with nothing else on the box, so the suite is never under contention
there and this failure is *unreachable* in CI. That is also why it survived this long: it was
invisible to every green run in the project's history until the suite was run in parallel locally.

##### ⚠️ What is NOT fixed, and why it gets its own ID

The reason this was filed P1 was never the flaky test — it was that **a battery scores `Failed > 0`
as a DETECTION**, so any spurious failure during a mutant run marks that mutant KILLED for free.
Removing this cause removes the only *known* trigger. It does not make the scoring rule able to tell
a detection from an accident, and the next source of non-determinism will be scored the same way.

That residual is **`P1-179`**, filed rather than left inside this closed entry, because work hiding
under a closed ID is invisible to every count.

### P1-179. A mutation battery cannot distinguish a detection from an accident: `Failed > 0` is scored KILLED, whatever caused it — ✅ CLOSED 2026-08-20 (session 61), LOCAL-ONLY by design

**The kill decision now lives in `mutation/_battery.py`** (`is_kill` + `score`), and all 60 batteries
were converted to `killed = _battery.score(res, run)` — a single mechanical change, each keeping its
own `run()`. `score` re-runs an apparent kill and requires it to reproduce; a one-time red is scored
a SURVIVOR, because a real detection is deterministic and an accident is not. A survivor is never
re-run (verified: it is already the loud, investigated outcome).

⚠️ **It runs ONLY under `RG_DOUBLE_KILL`, which `tools/ci_local.py` sets, and NOT in GitHub CI —
this is the measured decision, not a shortcut.** The measurement the entry demanded: ~500 mutants
across 60 batteries, ~95% killed, so re-running every kill adds ~1.5–1.7× CI compute and pushes the
killed-heavy bins (30/24/23 mutants) past the 1119s critical path. And the accident it guards (the
`P1-175` temp-file collision) needs two batteries CONTENDING on one machine, which happens ONLY in
the local parallel runner — GitHub CI runs one bin per hosted runner with nothing else on the box
and structurally cannot reproduce it. So the double-kill is armed exactly where accidents can occur,
at zero cost to the slot-limited public CI, whose scoring is byte-for-byte unchanged (the env var is
unset there). Operator decision, 2026-08-20.

⚠️ **The measurement also found what the filed entry's one paragraph did not: the batteries had
drifted into ~10 `run()` variants across several scoring generations** (only 18 of 60 carried the
crash-aware `is_kill`). The move therefore UNIFIED the kill decision as well — an improvement
(a crash is not a detection, everywhere now), validated by a full local CI run in which every
converted battery still scored all-killed / its declared survivors.

**Original entry (the defect as filed):**

Every one of the 60 batteries scores a mutant like this:

```python
killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) or (failed_count > 0)
```

`failed_count > 0` is the whole test. **Any** reason the suite went red reads as "the mutant was
detected" — a real detection, a flaky test, a machine hiccup, an unrelated regression, a collision
with something else on the box. The rule cannot see the difference and never could.

⚠️ **THE FAILURE IS SILENT AND IT INFLATES.** A mis-scored kill produces a green battery, no
survivor, and no line anywhere saying the verdict was accidental. It is the opposite of the failure
mode this repo is built to catch: `check_anchors.py` exists because a broken anchor scores a
SURVIVOR, which is loud. This scores a KILL, which is not.

`P1-175` closed the only known trigger — five machine-global temp filenames — and its before/after
is clean. That is a reason to believe the score today, not a reason the rule is sound.

#### The fix, and why the cheap version is the right one

**Re-run a mutant that appears KILLED, once, and require the same verdict twice.** A real detection
is deterministic and will re-kill; an accident usually will not.

* It costs runtime **only on the killed path**, which is the overwhelming majority — so it roughly
  doubles a battery's cost. ⚠️ That is a real price and the reason to measure it before adopting it
  everywhere: full CI compute is 17,144s today.
* ⚠️ **It must NOT be applied to survivors.** A survivor is already the loud, investigated outcome,
  and re-running it would only add cost to the case that already gets human attention.
* The scoring rule is copied into all 60 batteries rather than shared, so this is either a
  mechanical edit across 60 files or a move of `run()`/scoring into `mutation/_battery.py` first.
  **The move is the better shape** and `_battery.py` already exists for exactly this kind of
  shared decision — but it is a 60-file change and must not be bundled with a defect fix.

⚠️ **Do not "fix" this by making the battery parse WHICH test failed and compare it to an expected
set.** That was considered and rejected: it turns every battery into a second, silent copy of the
suite's own pass/fail bookkeeping, and a mutant that legitimately breaks a different test than
expected would then score as an accident — the fail-open direction, on the mechanism that decides
whether this project's safety evidence is real.

### P2-176. CI ran only on GitHub while 24 local cores sat idle, and a self-hosted runner is the wrong answer on a PUBLIC repo — ✅ CLOSED 2026-08-20 (session 61), `tools/ci_local.py`

**The measurement that motivated it**: one rebuild-and-run of the ~3400-test suite takes **8.07s on
this box against ~19.6s on a hosted runner — 2.4x**. Total CI compute for a full run is **17,144s
across 20 jobs**, so the hardware difference is worth having.

⚠️ **A SELF-HOSTED GITHUB RUNNER WAS CONSIDERED AND REJECTED, AND THE REASON IS THE POINT.** Both
repos are **PUBLIC** and `ci.yml` triggers on `pull_request`. A self-hosted runner would let any
fork's pull request execute arbitrary code **on the machine running NinjaTrader against a funded
50K account**, which is the single worst place on this network to offer that. GitHub's own
documentation advises against precisely this pairing. The operator was offered going private as the
alternative and chose the local script instead. `gh api .../actions/runners` returns
`total_count: 0` and should stay there.

#### What it does

`python tools/ci_local.py` runs all 13 gates plus `check_anchors.py` (6 seconds; CI's `checks` job
takes 110), then build + suite, then **all 60 batteries across parallel git worktrees** pulled from
a shared queue longest-first — self-balancing, so it needs no weights and sidesteps
`pack_ci_matrix.py`'s refusal to guess them.

⚠️ **Each worker gets its OWN worktree, and that is the load-bearing part.** A battery owns its
source tree for the length of its run; two in one tree interleave and one writes the other's mutant
back as its "original". That has happened twice here. Per-worktree isolation makes it structurally
impossible, and a worker killed mid-mutant leaves the damage in a directory the script deletes.

⚠️ **It also makes gates safe to run BESIDE the batteries**, which is otherwise forbidden — a gate
reading source with a mutant applied reports a FALSE RED, and a false red is the one you act on.

**First full run: 17.2 min against GitHub's 24m08s**, with 50 of 60 batteries green and the other
10 traced to `P1-175`.

⚠️ **THIS DOES NOT REPLACE GITHUB ACTIONS AND MUST NOT.** A local pass proves the tree you ran it
on; only CI proves the commit you **pushed** was checked, and nothing local runs on a commit you
forgot to run it on. The script prints that line at the end of every green run.

### P3-177. `ci.yml`'s bin comments claim a 1119s critical path; it is 1358s, and every local estimate in the file has read 21-23% high — OPEN, measured 2026-08-20 (session 61)

The workflow's packing comments were written against a critical path of **1119s**. Measured on run
`32385089590` it is **1358s** (`P2-136+P2-101+P2-142+P1-157`), so the numbers the packing decisions
were justified against have drifted low by more than 20%.

Three independent measurements now agree on the direction of the *other* error too: local estimates
of battery weight came in **21%, 22% and 23% high** against CI for `P2-165`, `P1-167` and `P1-172`.
That is consistent enough to correct for, and it is why `pack_ci_matrix.py` refuses a guessed
weight rather than accepting one.

⚠️ **Do not repack from the numbers in the comments.** Mine `BATTERY_SECONDS` from a green run
first. And note the ceiling is a CONSTRAINT, not a target: 19 bins + `checks` = 20 jobs = the whole
account-wide concurrency limit, shared with the sibling repo.

### P2-178. `nt_extract_trades` returns EASTERN timestamps with a `Z` suffix, so every consumer reads them as UTC — OPEN, found 2026-08-20 (session 61)

**⏳ FIX LANDED 2026-08-21 (session 63), pending deploy + Sim re-validation.** New
`addons/BridgeTradeTime.cs` converts the Eastern wall-clock to true UTC (DST-correct via
`TimeZoneInfo`, NOT a fixed 4h subtraction), and BOTH call sites now route through it —
`ExtractTrades` and `nt_capture_chart`'s `fillTime` (the second was the same false-`Z` on
`targetExec.Time`, [[fix-the-class-not-the-instance]]). 6 executed tests + a source gate;
`mutation/mutate_p2178.py` 8/8, incl. the "+4h constant" mutant the entry warns against, killed
by the winter-DST case. **Stays OPEN until deployed and re-validated on Sim** (compare
`nt_extract_trades` against `interventions.jsonl`).

Found while measuring `P2-164`, by a discrepancy that had no other explanation. The tool reported
executions on the funded account at `2026-08-20T09:57:51.985Z`; `interventions.jsonl` had the same
orders at `13:57:52Z`. Four hours apart, which is ET→UTC on this date.

**`Z` means UTC. It is not a decoration.** A consumer that trusts it — and every consumer should —
places the operator's morning session in the middle of the night, and any analysis that joins this
tool's output to the ledger, to bar data, or to session windows silently mis-buckets everything by
four hours. It cost one wrong statement to the operator in the session that found it, corrected
only because the ledger disagreed.

⚠️ **The failure is quiet and self-consistent**, which is the bad kind: every timestamp is wrong by
the same offset, so nothing inside the output looks odd. It is visible only by joining to another
source, and `[[measure-the-deployed-system]]` is what made the join happen at all.

Fix in `nt8-mcp-bridge`: emit real UTC, or drop the `Z` and name the zone. ⚠️ Do not "fix" it by
subtracting four hours — the offset is a DST-dependent property of the date, not a constant.

### P1-174. A recompile while holding a WINNING position re-baselines the peak-giveback rail to the current price, and the code already marks that state dirty for a save that never stores it — ✅ FIXED 2026-08-20 (session 62), v1.52.6 — suite 3382/0, battery 6/6, and the battery caught an UNTESTED safeguard I had written and commented at length
**CLOSED 2026-08-20 (session 62), `v1.52.6`.** Suite **3382 / 0**, `mutate_p1174.py` **6 / 6** no
survivors, 13 gates green, 644 anchors / 0 broken. This empties
`tools/check_account_state_persisted.py`'s UNREVIEWED baseline: every `AccountState` field is now
either persisted or classified with a reason.

⚠️⚠️ **JSON HAS NO NaN LITERAL, AND THAT IS THE HALF THAT WOULD HAVE SHIPPED.**
`PeakGivebackLastTriggerUnrealized` uses `NaN` for "has not triggered". Every state file on every
box predates this field, so it deserializes as **`0.0`** -- and `0.0` is a LEGITIMATE trigger level,
a giveback that fired exactly at breakeven. Restored raw, the guard comes up believing the giveback
has ALREADY fired on every account it tracks, which suppresses the next real one. First load after
the upgrade, silently, on all of them. The restore normalises `0.0 -> NaN`, because absent is the
only thing a missing field can mean.

Nothing in the ticket mentioned this. It surfaced from writing the restore.

⚠️ **AND THE BATTERY CAUGHT THAT SAFEGUARD BEING UNTESTED.** The normalisation was written AND
given a fifteen-line comment justifying it -- and covered by nothing, because every other P1-174
test set the sentinel to a non-zero level so the `== 0.0` branch never executed. The mutant that
strips the normalisation SURVIVED the first run. That is the argument for mutation testing in one
example: **review cannot distinguish a well-commented defence from a tested one.** The missing test
now exists and the mutant dies.

⚠️ **A GREEN SUITE FROM A STALE BINARY, on the way.** Adding that test, `dotnet build` reported 38
errors while `dotnet run --no-build` printed `Failed = 0` from the PREVIOUS assembly -- a heredoc
had turned `
` into a real newline inside a C# string literal. Reading only the RESULTS line would
have called a syntactically broken file green. Same shape as a broken NT8 assembly reading healthy:
the artefact under test is not the artefact you just changed. It is why CI builds and tests in two
independently-failing steps.

**The fix itself** is three fields on `AccountPersistedData`, both copy sites, and the restore. The
stale-peak bound claimed when this was filed HOLDS and is now asserted: the rule's flat branch
discards all three on any evaluation while the account reads flat, so a peak belonging to a position
that closed while the guard was down cannot make the giveback fire early on the next one. ⚠️ That
branch lives in `EvaluatePnLRules`, not `EvaluateRules` -- calling the wrong one made a correct fix
look broken for one cycle, and a test driving the wrong entry point is indistinguishable from a
failing fix.

⚠️ **EVERY ANCHOR IN THIS PATCH ENDS AT A LINE BOUNDARY**, because
`public DateTime CooldownUntil { get; set; }` matches BOTH the DTO and `AccountState`'s copy -- the
latter reads `... = DateTime.MinValue;` and the shorter string is a PREFIX of it. The same shape
displaced `P1-54`'s comment an hour earlier and reached a green suite. Anchor on the whole line,
trailing comment included.



The third instance of `P1-170`'s class, and the last three fields
`tools/check_account_state_persisted.py` had in its UNREVIEWED baseline. They are now the only
entries left there.

**The three fields**, all on `AccountState`, none in `AccountPersistedData`:

| field | meaning |
|---|---|
| `PeakOpenGain` | the high-water mark of `UnrealizedPnL` for the CURRENT open position |
| `PeakGivebackTriggered` | the latch, re-armed whenever a new peak is set |
| `PeakGivebackLastTriggerUnrealized` | `NaN` sentinel for the level the latch last fired at |

**The mechanism**, from the rule itself:

```csharp
if (!accountIsFlat)
{
    if (stateModel.UnrealizedPnL > stateModel.PeakOpenGain)
    {
        // New peak = new episode. Re-arm the giveback latch.
        stateModel.PeakOpenGain = stateModel.UnrealizedPnL;
        stateModel.PeakGivebackTriggered = false;
        stateModel.PeakGivebackLastTriggerUnrealized = double.NaN;
        _stateDirty = true;
    }
}
```

A recompile sets `PeakOpenGain` to `0.0`. The very next evaluation finds `UnrealizedPnL > 0` and
**re-baselines the peak to the CURRENT unrealized**, losing the true high. The giveback is then
measured from a lower high, so the rail fires later than it should or not at all — for as long as
that position stays open.

⚠️⚠️ **THE CODE ALREADY BELIEVES THESE SHOULD BE DURABLE.** Both branches set `_stateDirty = true`,
which is the flag that schedules a state write — for three fields the writer does not carry. That is
a WRITE TO NOWHERE, and it is stronger evidence than any argument about whether persisting is
"worth it": the author of this rule marked the state as needing to be saved, and the save silently
did not include it. Same family as [[an-alarm-wired-to-a-dead-output]].

**Why P1 and not P0.** The rail is weakened rather than disabled — the peak still climbs from the
re-baselined level, so a giveback that develops *after* the recompile is still caught. The exposure
is one open position, and it ends when that position closes. It also fails in the LENIENT direction
(a winner is held longer), which costs money but cannot trap the operator.

**Fix**: add all three to `AccountPersistedData` and to both copy sites, and restore them — the same
three-line shape as `P1-173`. ⚠️ The test must drive the RESTORE, not the arithmetic; this path is
reachable only through `LoadPersistedState`, which is what made `P0-166`, `P1-170` and `P1-173` all
need the same reminder.

⚠️ **ONE EDGE THAT NEEDS A TEST, AND IT IS THE ONLY WAY THIS FIX CAN HURT.** The persisted peak
belongs to a specific position. If the guard is DOWN across a flat window — position closed, new one
opened, all while the assembly is reloading — the restored peak is from the previous episode, and a
stale high makes the giveback fire EARLIER than it should. The `accountIsFlat` branch zeroes all
three on any evaluation while flat, so the window is exactly "down for the whole flat period", which
is narrow but real. It fails toward over-protection rather than under-protection, so it is the
acceptable direction; **assert it rather than assume it.**

⚠️ `PeakEquity` — the account-level peak used by `TRAILING_DD_BREACH` — **is** persisted, and is a
different field. Do not conflate them: this entry is about the per-position unrealized peak only.
The asymmetry (account peak durable, position peak not) is what made this easy to miss.

### P1-173. A recompile clears an active loss cooldown, and recompiling is something the operator does — ✅ FIXED 2026-08-20 (session 62), v1.52.4 — suite 3373/0, battery 5/5, and adding the field disarmed an unrelated battery (see below)
**CLOSED 2026-08-20 (session 62), `v1.52.4`.** Suite **3373 / 0**, `mutate_p1173.py` **5 / 5** no
survivors, 13 gates green, 638 anchors / 0 broken.

Three lines: the field on `AccountPersistedData`, the save projection, the restore. Restored and
NOT re-armed -- a deadline already in the past stays there, so an account that has served its
cooldown is not flattened for it after a restart. Two of the five mutants exist for that direction
alone, because it is the one that hurts the operator and the tests for the two directions look
nearly identical.

⚠️ **ADDING A FIELD TO THE DTO DISARMED AN UNRELATED BATTERY, AND IT WOULD HAVE SCORED A
SURVIVOR.** `mutate_p292.py` anchored on `LockoutWasShadowOnly { get; set; }` followed by the class
brace, using "last member before the closing brace" as the thing that told it apart from
`AccountState`'s identically-named field. `CooldownUntil` displaced it and the anchor matched ZERO
times. Re-anchored on the field plus a bare newline, which is unique because `AccountState`'s copy
reads `= false;` -- and which depends on nothing's POSITION.

This is [[mutation-anchors-go-stale]] with a trigger not seen before here: not a code MOVE, just an
APPEND. Any anchor whose uniqueness comes from adjacency rather than content is one field away from
silently passing. Worth grepping the other batteries for `}` in an anchor.


Found by `tools/check_account_state_persisted.py` on its first run, which is the entire argument for
that gate: this was not spotted by reading the cooldown code, it fell out of asking *which
`AccountState` fields are not persisted* and looking at the answers.

**The three sites.**

| | |
|---|---|
| written | `RiskGuardAddOn.cs:1894` on a consecutive-loss breach, and `RiskGuardModels.cs:303` in `ApplyTradeJudgement` |
| read | `RiskGuardAddOn.cs:4545`, inside `EvaluateRules` |
| cleared | `RiskGuardAddOn.cs:4962`, the session reset |
| persisted | **nowhere** — `AccountPersistedData` has no `Cooldown` member at all |

The read is an enforcement point, not a display:

```csharp
if (DateTime.UtcNow < stateModel.CooldownUntil)
{
    bool hasOpen = stateModel.Positions.Values.Any(p => p.MarketPosition != MarketPosition.Flat);
    if (hasOpen)
        actions.Add(new GuardAction { ... RuleId = "COOLDOWN_BREACH",
                                      ActionType = GuardActionType.FlattenPosition });
}
```

So a restart, a recompile or a hot-swap sets `CooldownUntil` back to `DateTime.MinValue`, every
comparison against it is false, and `COOLDOWN_BREACH` cannot fire for the rest of the cooldown that
was supposed to be running.

⚠️ **THE DEFEAT IS AN ACTION THE OPERATOR ALREADY TAKES.** This is the same class as `P1-170` —
[[a-successful-compile-wipes-static-state]] — but with a worse property: the cooldown exists to
interrupt revenge trading after a run of losses, and the state that enforces it is cleared by
NinjaScript's recompile button. Six recompiles happened on this box on 2026-08-19 alone, none of them
for this reason. Nothing about that is deliberate and nothing logs it, which is why it needs an ID
rather than a note.

**Scope, stated precisely so the fix is not over-sold.** The cooldown as currently written does not
refuse entries — it flattens an open position — and `P2-162` is already open on exactly that (a pause
that costs a fill, a commission and slippage instead of preventing the entry). So what a recompile
currently destroys is *the flatten*, not an entry block. If `P2-162` is fixed first and the cooldown
becomes an entry refusal, this defect silently becomes more serious, because the thing being cleared
would then be the whole rail rather than its recovery action. **Fix this before `P2-162`, or fix them
together.**

**Fix.** Add `CooldownUntil` to `AccountPersistedData` and to both copy sites, and restore it. It is
an absolute UTC deadline, so unlike `P1-170` there is nothing to reconstruct and nothing to derive —
it is simply a field that was never added. ⚠️ A test must drive the RESTORE, not the arithmetic: the
same requirement `P0-166` and `P1-170` both hit, because this path is reachable only through
`LoadPersistedState`.

⚠️ **Do NOT also persist the P2-101 lockout-phase cluster while you are in there.** Those are
classified `RESET_BY_DESIGN` in the gate for a reason that survives a restart being *correct*: a new
process should re-attempt a flatten rather than believe a dead one already did it. The cooldown is
different because its deadline is a fact about time, not a record of an attempt.

**Three other fields remain in the gate's `UNREVIEWED_BASELINE`** — `PeakOpenGain`,
`PeakGivebackTriggered`, `PeakGivebackLastTriggerUnrealized`. They are the peak-giveback rule's
working state and they may be the same defect again; they are listed as unreviewed rather than
classified because I did not measure them, and writing a justification I had not verified would have
made the gate read as a review that never happened.

### P1-172. `ConsecutiveLosses` reads **17** on an account that took **16** trades — a realized delta arriving while the guard sees no position counts as a losing trade, and the counter it inflates refuses every entry — ✅ CLOSED 2026-08-20 (session 61), filed 2026-08-19 (session 62)

Read live off `TAKEPROFITPRO524207503` from `RiskGuard/state.json` at `2026-08-19T19:01:02Z`:

```json
"TradesToday": 16,
"ConsecutiveLosses": 17,
"LastRealizedPnL": -347.75,
"SessionStartRealizedPnL": -1.5
```

**17 consecutive losses out of 16 trades is arithmetically impossible.** A consecutive-loss streak
cannot exceed the number of trades in the session, and it resets to 0 on any win, so it cannot exceed
the number of trades *since the last win* either. At least one increment did not come from a trade,
and the two counters cannot both be right.

**Mechanism.** `AccountState.RecordRealizedDelta` (`RiskGuardModels.cs`) has three cases, and the
third is the one that fires:

```csharp
if (!HasOpenPosition())
{
    ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
    ApplyTradeJudgement(config);          // ConsecutiveLosses++ on any delta < -0.01
    OpenTradeRealizedDelta = 0.0;
    ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
}
```

Any negative realized delta arriving while every tracked position reads `Flat` is judged **on its
own** as a losing trade. `TradesToday` is not touched — that increments only inside the position-update
path, gated on a genuine new trade lifecycle (`P1-16`). So the two counters are incremented by two
different events and only one of them is debounced to a trade.

`P1-16`'s comment says this in as many words and treats it as the acceptable residue:

> 3. No trade is tracked at all (the guard never saw the position, or this is a standalone
>    adjustment) -> judge the delta on its own, preserving the pre-existing behaviour. Silently
>    ignoring untracked realized losses would make the lockout less sensitive than before, which is
>    not an acceptable trade for this fix.

That reasoning is sound for the case it names — a position the guard genuinely never saw. It is wrong
for the case that actually produces these numbers, because **the guard did see the position; it is
being told about the same fill twice.**

**Why today.** `P0-171` measured the mechanism: one `Disconnected -> Connected` cycle at 16:44 replayed
118 orders and **all 59 executions inside two seconds**, with the account flat. Every replayed negative
execution takes case 3 and increments the streak. The reconnect that produced 45 phantom
`DUPLICATE_ENTRY` refusals also produced an unknown number of phantom losses, and the second effect is
worse than the first because nothing logs it — a refusal writes to `interventions.jsonl`, an increment
writes nowhere.

`P1-170` is the same input reaching the same counter by the other route: `RealizedPnL` is not persisted,
so a recompile resets the working value while `LastRealizedPnL` survives, and the next tick's delta is
computed against a zero.

**Why P1 and not P0.** The refusal path exempts reducing orders, so a phantom streak cannot trap the
operator in a position:

```csharp
if (LockoutBinds(accountName, stateModel)
    || stateModel.ConsecutiveLosses >= _config.Overtrading.MaxConsecutiveLosses)
{
    ...
    if (!IsPositionReducingOrder(e.Order, stateModel))
```

It fails in the safe direction. It is P1 rather than P2 because of what that `||` means, below.

⚠️ **THE SECOND READER IS NOT GATED ON A LOCKOUT.** The condition above refuses entries whenever the
raw counter is at or over the cap — `LockoutBinds(...)` **or** `ConsecutiveLosses >= Max`. No lockout
need be active, no cooldown need be running, and no deadline is consulted. With `MaxConsecutiveLosses`
at its default of 3 and the counter at 17, **every entry on this account is refused right now**, and
in `live` that is the operator unable to open a trade at all.

The counter has exactly three cures: a winning trade, a session reset, and a `CONSECUTIVE_LOSS_BREACH`
lockout *lapsing* (`P0-166`'s fix, `RiskGuardAddOn.cs:4136`). The first is **unreachable while entries
are refused** — the cure requires the action the rule is blocking. The third does not apply here: the
account is locked by `DAILY_LOSS_BREACH`, which `P0-166` deliberately made EOD-scoped, so
`LockoutUntil` is `MinValue` and no lapse ever runs. That leaves the 22:00Z session reset as the only
cure, for a counter whose value is partly fabricated.

This is `P0-166`'s shape one reader over — a trigger paired with a cure that cannot clear it — and
[[a-second-reader-of-the-same-state]]'s: `EvaluateLockoutPhase` learned to zero the counter on lapse
and this reader never did.

**Do not fix it by making case 3 ignore untracked deltas.** That is the trade `P1-16` explicitly
refused, and it would blind the streak to a real loss on a position the guard never saw. The two
candidate fixes are (a) suppress realized-delta judgement during the same reconnect replay window
`P0-171` establishes, which is guard-owned state that already has to exist, and (b) make the entry
refusal read the same cure the lockout reader does, so a streak at the cap with nothing locked is not a
permanent refusal. **(b) is the load-bearing half** — it is what turns a wrong count into a temporary
wrong count instead of a session-long trading ban.

⚠️ **`TradesToday` vs `ConsecutiveLosses` is a free invariant and nothing asserts it.** No test in the
suite compares the two counters, which is why a value that cannot occur sat in persisted state
unremarked. `ConsecutiveLosses <= TradesToday` holds for every genuine sequence and is checkable at
every settlement.

#### ✅ CLOSED 2026-08-20 (session 61) — `v1.54.0`, suite **3434/0**, battery **14/14, no survivors**

Both halves fixed, and the second one is the half that mattered.

##### (a) The replay is no longer judged as a sequence of losing trades

`RecordRealizedDelta`'s case 3 now returns without judging while
`ReplaySuppressionUntilUtc` is live — the same guard-owned stamp `P0-171` already arms on every
connection transition, so this needed no new state and no new lifecycle.

⚠️ **Only the JUDGEMENT is suppressed. The money is still recorded.** The realized P&L being
replayed is real, and `DAILY_LOSS_BREACH` reads it — suppressing the amount as well as the verdict
would disarm the daily-loss rail for the length of every reconnect window. `mutate_p1172.py` group
1 mutant 4 is that mistake.

⚠️ **And the banked total is still cleared**, so a replayed amount cannot sit in
`OpenTradeRealizedDelta` and land later as part of a genuine trade's judgement — which would turn a
win into a loss and increment the very counter this fixes. That mutant (group 1, mutant 3) is the
subtle one: it suppresses correctly and then leaks.

This does **not** make the trade `P1-16` refused. `P1-16` declined to blind case 3 to untracked
losses; this suppresses only inside the bounded window in which the guard *knows* it is being
re-told. `TestP1172_ARealLossOutsideTheWindowStillCounts` is the control, and group 1 mutant 2
inverts the window to prove it is load-bearing in both directions.

##### (b) The refusal now owns a cure — and this is what made it a P1

The reader refused on `ConsecutiveLosses >= Max` with **nothing on that side of the `||` that could
ever expire**. All three cures were unreachable at once, which is why the account sat refusing every
entry:

| cure | why it could not run |
|---|---|
| a winning trade | needs the action this rule is blocking — **the cure requires the thing it forbids** |
| the session reset | 22:00Z, hours away |
| a `CONSECUTIVE_LOSS_BREACH` lockout lapsing | `EvaluateRules` claims its lockout only `if (!IsLockedOut)`, and `DAILY_LOSS_BREACH` already held an **EOD** lockout whose `LockoutUntil` is `MinValue` and by design never lapses |

The fix makes **the reader that refuses responsible for the cure**: when the streak alone binds, it
arms the streak's own deadline and attributes it to `CONSECUTIVE_LOSS_BREACH`, so `P0-166`'s
existing cure can lapse it and zero the counter. That cure was already written; it was simply
unreachable from here.

⚠️ **This loosens nothing, and that was the constraint.** The refusal still fires on the same event
and every event until the deadline lapses. It only *adds* a deadline where none existed.

##### ⚠️ `!IsLockedOut` is not redundant with `!LockoutBinds`, and the difference is a live rail

A lockout that does **not bind** still exists and still owns `LockoutRuleId` — a shadow-only lockout
(`P1-100`) and a disarmed-bypass account are both `IsLockedOut` with `LockoutBinds` false. Arming
there would **re-attribute another rule's lockout**, and `P0-166`'s cure clears the counter of
whichever rule the attribution *names* — so the clobber would forgive the loss streak because the
daily-loss lockout expired. Worse, it would convert an EOD lockout into a 60-minute one, handing
back an account the prop firm's own rail has stopped for the session.

Two tests hold that line (`AnExistingLockoutIsNotReattributed`, `AShadowOnlyLockoutIsNotReattributedEither`)
and group 3 mutant 1 drops the guard, because it reads as redundant.

⚠️ **The re-arm bound too.** Without `LockoutUntil <= UtcNow`, every refused entry re-arms the
deadline, so the cure never lapses while the operator keeps trying and each attempt to trade extends
the ban refusing it. [[a-retry-that-cannot-exit]], one reader over.

##### The invariant is now reported — the increment used to write nowhere

`ConsecutiveLosses <= TradesToday` is free, holds for every genuine sequence, and **nothing compared
them**, which is exactly why an arithmetically impossible value sat in persisted state unremarked. A
refusal writes to `interventions.jsonl`; an increment wrote nowhere.

⚠️ **Reported, not clamped.** Clamping reads like the helpful fix and hides the next mechanism that
inflates this counter — which is precisely what cost a session to find the first one. Group 4 mutant
3 clamps, and the negative control (`AGenuineStreakIsNotReportedAsAViolation`) stops the alarm firing
on every ordinary losing trade, because an alarm that always fires is the same as no alarm.

##### One thing found while fixing it, not in the entry

The raw-counter clause had **no `> 0` guard**, so an unset `MaxConsecutiveLosses` made `0 >= 0` true
and refused every entry on the account. Same shape as the zero-reading asymmetry `P2-165`
characterised in the neighbouring config section.

### P1-153. A test that THROWS kills the runner before `RESULTS:` prints, so every mutation battery scored a crash as a detection — ✅ FIXED 2026-08-18 (session 59), instance and class

Found by `P2-148`, which was written for exactly this and found it on its first CI run. Not by
reading anything.

`Main` invoked all 677 tests as bare statements:

```csharp
TestMaxPositionSizeEnforcement();
TestDailyLossLimitLockout();
```

with no per-test `try`/`catch`. The first test to throw took the process down, so `RESULTS:
Passed = x, Failed = y` was never printed at all. **A run that dies prints no failure**, and the
suite therefore read `3158 / 0` in exactly the case where something was badly wrong.

Two gates were defeated by that, in opposite directions:

1. **Every battery in `mutation/` scores `NO RESULT LINE` as KILLED.** So a mutant that made
   production code *throw* counted as detected while nothing had asserted anything. `P2-148`
   started requiring a `[FAIL]` before believing a crash, and **7 mutants across 5 CI bins
   immediately flipped KILLED → SURVIVED** — every one a null-handling mutant:

   | battery | mutant |
   |---|---|
   | `mutate_ui6.py` | the latency metric flattened to its value (`P1-22`) |
   | `mutate_ui6.py` | the slippage metric flattened the same way |
   | `mutate_ui6.py` | a missing copier serialises without an error (`P2-83`) |
   | `mutate_p2119.py` | a null config accepted and written as literal `null` |
   | `mutate_p1121.py` | `GetRelationshipMetrics` throws on a null relationship |
   | `mutate_ui2.py` | a `JArray` arrives as one nonsense account name |
   | `mutate_p2123.py` | `ComputeEffectiveRatio` drops its null guard |

2. **The agent-loop's `expect_green` gate matches this runner's `[FAIL]` lines**, so a test that
   throws instead of failing silently *removes itself from the gate* — the thing standing between
   this repo and a suite that asserts whatever the implementation happens to do.

⚠️ **The hazard was already written down, twice, in the file it applies to** — `:1325` and
`:11807`, both saying "a test that throws instead of failing produces no `[FAIL]` line and
silently removes itself from the gate." It was stated and never closed. The same family has bitten
this repo before: `TestHarness_AllDeclaredTestsAreInvoked`'s own docstring records a stray
`Environment.Exit` that aborted a run at test 92 of 117, undetected for as long as the suite was
green.

**The fix is the class, not the 7 instances.** A `Run(Action)` wrapper reports an escaping
exception as `[FAIL] <name> THREW <Type>: <message>` and *continues*, so one bad test cannot
conceal the 676 behind it. Writing 7 individual null tests would have left the next crash-mutant
mis-scored. Two source-gate tests take a `[CallerFilePath]` parameter and get the named overload,
because a bare lambda's `Method.Name` renders as `<Main>b__0` on precisely the tests whose failure
line has to name them.

`Run` deliberately does **not** add to `_invokedTests`: that set is fed by `Assert`'s
`CallerMemberName` so a test which is *called but asserts nothing* still gets caught, and marking
invocation in `Run` would make that structural check pass vacuously
([[a-green-that-can-never-be-red]]).

**The negative control is the load-bearing half** — a wrapper that swallows exceptions and one
that reports them are indistinguishable from a green suite
([[a-detector-needs-a-negative-test]]). `TestHarness_AThrowingTestIsAFailureAndTheRunContinues`
throws on purpose and asserts the count, the continuation, and the emitted text.

⚠️ **It captures stdout, and that is not tidiness.** Every battery decides "did anything object?"
by searching stdout for `[FAIL]`. A control that printed a real `[FAIL]` would make every
undetected crash look detected again — re-arming this exact hole from inside its own proof. The
counters are saved and restored for the same reason.

Suite `3158 / 0` → `3163 / 0` (5 new assertions, same 677 tests).

### P2-152. A mutant whose anchor now matches only a COMMENT edits prose, can never be killed, and `check_anchors.py` reports it healthy — ✅ FIXED 2026-08-18 (session 59), instance and class

Found by re-running `mutate_p330.py` after `P2-145` landed, not by reading anything.

`P2-145` replaced the audit's inline predicate with `AssessCoverage`. `mutate_p330.py` carried a
mutant anchored on that predicate verbatim:

```python
'if (!isProtected || covered < positionQty)',
'if (!isProtected || covered > positionQty)'),
```

The predicate is gone from the code — but the `P2-145` comment block **quotes it**, deliberately,
because quoting what you replaced is how a defect's history stays readable here. So the find-string
still matched **exactly once**, `check_anchors.py` reported the battery healthy, and the mutant
edited a comment: no effect, suite green, scored **SURVIVED**.

⚠️ **This is [[mutation-anchors-go-stale]] in its least visible form.** The recorded version is an
anchor that stops matching and prints `[SKIP]`. This one *still matches*. It matches the wrong
thing, and the gate built to catch stale anchors is the gate that certified it.

**MEASURED BLAST RADIUS: 1 of 508 anchors**, and it was the one this session created. Thirteen
others *span* a comment — code followed by commentary inside one multi-line anchor — which is
legitimate and must keep passing. That distinction is what makes the fix non-trivial: the weak
question ("does this text appear outside comments anywhere?") fails all 13.

**THE FIX, both halves:**

* **Instance.** The mutant is **removed**, not re-pointed. `mutate_p2145coverage.py` groups 1-2
  already mutate that comparison where it now lives, in more spellings than this one had (the state
  test, the `<=` off-by-one, and the tempting wrong fix). Two batteries rewriting one line is a
  collision risk for no extra evidence — and every battery rewrites shared source in place.
* **Class.** `check_anchors.py` gains `strip_cs_comments`, which blanks `//` and `/* */` to spaces
  **preserving offsets**, so a match position found in the original indexes the same span in the
  stripped text. The gate then asks of *that one match*: is its span entirely comment? Exactly one
  match is now necessary and **not sufficient**.

**Control, run both ways** — because a check that cannot go red is not a check
([[a-green-that-can-never-be-red]]):

```
with a probe mutant anchored on the comment:   509 anchors checked, 1 broken
probe removed:                                 508 anchors checked, 0 broken
```

⚠️ **`P2-145` and `P2-148` between them are why this surfaced at all.** The stricter scoring from
`P2-148` is what stopped the crash-and-survivor cases hiding each other, and re-running the battery
is what exposed it. Nothing here was found by reading code — the same pattern as the rest of this
session.

**Also closed in passing:** `mutate_p330.py`'s mutants 3 and 4 (the flat-position filter) are now
declared `EXPECTED SURVIVOR:`. `AssessCoverage` answers `positionQty <= 0` with
`CoverageFinding.None` before anything else, so removing the caller's filter has no observable
effect — the mutants became **equivalent**. The coverage moved rather than vanishing:
`mutate_p2145coverage.py` group 5 mutates that answer directly. ⚠️ Neither the caller's filter nor
the totality check should be removed to make them killable again — that would be making the code
worse to keep a battery green. `_battery.finish` fails if a declared survivor is ever KILLED, which
is the correct coupling: it means the totality check went away.

### P1-151. `StopGuard.OnMissing: Flatten` at `StopAttachSeconds: 15` would flatten the operator's own manual trades — `P1-84` set that number by guess, and there is now a measurement — ✅ RESOLVED 2026-08-20 (session 61), v1.57.0 — suite 3470/0, battery 9/9

**Settled by the operator, not by fitting the measurement.** The 43-second hand-speed was the input;
the operator's ruling was that it is behaviour NOT to be accommodated: *"15 seconds to attach a stop
loss is too large. … the 43 seconds is a trade behaviour that should not be encouraged. What I want
is an AutoStop roughly 5 basis points worth on any instrument. Worst case I will move it if I want it
larger."* So the answer is a SHORTER window with a non-destructive penalty, not a longer one.

**Implemented:**
- `StopGuard.OnMissing` default `Flatten` → **`AutoStop`**. An attached stop is recoverable; being
  flattened is not, and the operator moves the stop if they want it wider.
- New `StopGuard.StopDistanceBps` (default **5.0**). The AutoStop distance is ~5 bps of the entry
  price on ANY instrument — computed in `ComputeAutoStopOffsetTicks` (a pure static, so the pricing
  is unit-tested and mutation-covered) as bps of `AveragePrice` → ticks, floored at 1 tick. The old
  fixed-tick `Offsets` map (NQ 40 / ES 16 …) is retired to an OPTIONAL per-instrument override,
  empty by default — a fixed tick count is ~5 bps at only one price and drifts with the market.
- `StopAttachSeconds` default 15 → **5**. With AutoStop the P1-84 reasoning for a long deadline
  inverts: the action is non-destructive, so a short window protects sooner at no cost.
- ⚠️ **The shorter default opened a hole and preflight now closes it (c3):** a config that sets
  `OnMissing: Flatten` but inherits the short 5s default would flatten a manual entry — the original
  P1-84 danger. `RunPreflight` refuses `Flatten` with `StopAttachSeconds < 15` and names it
  (`STOP_GUARD_FLATTEN_DEADLINE`); AutoStop carries no such floor. [[a-green-that-can-never-be-red]]

⚠️ **This resolves the CODE. Arming `live` remains a separate, operator-gated step**, and the funded
`config.json` still needs the ladder values (`P2-161`: base 2, cap 4) set alongside this before live.
[[manual-entry-then-stop-43-seconds]]

**Original entry (the defect as filed):**

Split out of `P1-146` on closure: the detector there was correct and the workflow was the defect, but
what the workflow implies for `live` is real work and needs an ID of its own.

**Measured on `TAKEPROFITPRO524207503`** (funded 50K TPT PRO), from `interventions.jsonl`. The
operator enters manually with a bare order — no ATM strategy attached, `orderName` empty — and
attaches the stop afterwards by hand, or not at all on a fast scalp:

```
00:01:59  MNQ Sell 1 @29880.25   position short 1, FSM -> Unprotected
00:02:08  NAKED_POSITION covered=0 gap=1
00:02:14  grace expires -> MISSING_STOP_FLATTEN   <-- in `live`, this flattens
00:02:42  the operator's own stop arrives: Working StopMarket @29885.25 -> Protected (covered 1/1)
```

**28 seconds too early.** And the 21:52:54 case is worse: `Sell 3 @30005.50`, no stop ever attached,
covered by hand at 21:53:23 for roughly **+$156 in 29 seconds** — `live` would have flattened a
three-lot out from under an active scalp at 21:53:09.

`RiskGuardModels.cs:912` already names this exact hazard. `P1-84` raised the value from 3 to 15
because *"three seconds from fill to a working stop ... entering manually and reaching for the mouse
to place the stop gets you flattened on a day when nothing was wrong. A default that fires on a
normal day is a default that disarms the guard."* The reasoning was right; the number was a guess.
**Measured hand speed on this operator is 43 seconds**, so 15 is about 3x short and the P1-84 comment
describes a defect that is still live at the new value.

⚠️ **This is a blocker on arming `live`.** In `shadow` it costs nothing, which is exactly why it has
survived: the failure is invisible until the posture changes. [[configured-evaluated-enforcing]].

**Direction, and the same comment argues for it.** `RiskGuardModels.cs:920` states the 15 is only
right *for* `Flatten`, and that `AutoStop` would want a much SHORTER deadline "because an invented
stop is recoverable and being taken out of the trade is not". `OnMissing: AutoStop` is implemented
(`RiskGuardAddOn.cs:3258`), has offsets configured (`MNQ 40`, `MES 16`, `NQ 40`, `ES 16`,
`default 30`) and `MaxAutoStopAttempts: 2`. For an operator who brackets via NT8 ATM most of the time
and free-hands the rest, `AutoStop` protects the free-handed entries without ever removing them from
a trade. Prefer it over lengthening the `Flatten` deadline.

Two constraints on any fix:

* **Do not compute the deadline from `OnMissing`.** `RiskGuardModels.cs:921-927` refuses this
  deliberately: a getter that recomputes would let a config reload move a deadline while a grace
  timer was already running, and would read `OnMissing` off one thread while another wrote it. Change
  the defaults together, in one edit, as plain values.
* **`ACTION_SUPPRESSED` makes the protection one-shot.** Measured at 00:02:14: *"already reported
  once and the condition has not resolved; the guard is not acting."* So in `live` the **second**
  naked position of the same kind receives no action at all. Whichever action is chosen, decide
  deliberately whether it is once-per-condition or once-per-position — the current behaviour is the
  former and it is not obviously intended. [[a-recovery-budget-is-not-a-policy]].

⚠️ **`AutoStop` has never run in `live` on this box.** Everything above is `shadow` evidence about
what *would* have happened. The auto-stop placement path (`PlaceStopOrder` / `MISSING_STOP_ATTACH`)
is exercised only by the suite, so re-banding this to a fix means live-validating a path that has
placed a real order zero times — on an account where a wrong stop price is real money.


### P2-150. `PlaceBracket` reads its exit legs' `OrderState` in the same breath as `Submit()`, so `partial_submit` is a status that can never be set — OPEN, measured 2026-08-18 (session 59)

**⏳ FIX LANDED 2026-08-21 (session 63), pending deploy + Sim re-validation.** `DynamicAtmManager`
now reports `status: "pending_legs"` with the leg ids and drops the dead synchronous read (the bug
was the TIMING; not widened). The misleading stub-only `partial_submit` test — which only passed
because the stub rejects legs SYNCHRONOUSLY inside `Submit()`, a thing no real broker does
([[test-doubles-are-not-evidence]]) — was rewritten into an honest one; 14 status assertions
updated. Suite 3477/0, `mutation/mutate_p2150.py` 4/4 (the flagship re-introduces the synchronous
verdict; only the P2-150 test catches it). ⚠️ **A SIBLING was found and fixed the same session:
`P2-181`** — the bridge's `PlaceOcoOrder` carried the identical dead read
([[a-second-reader-of-the-same-state]] — count the sites). **Stays OPEN until deployed and
re-validated on Sim.**

`DynamicAtmManager.cs:526-536`, immediately after `account.Submit(validOrders)`:

```csharp
foreach (var o in new[] { stopOrder, targetOrder })
{
    if (o != null && (o.OrderState == OrderState.Rejected || o.OrderState == OrderState.Cancelled))
        rejectedOrders.Add(o.Name + " state=" + o.OrderState);
}
if (rejectedOrders.Count > 0) { result.Status = "partial_submit"; ... }
```

`Submit` is asynchronous. **Measured from `interventions.jsonl`, eight bridge-placed brackets on
2026-08-10**, the state sequence for a stop leg is:

```
00:11:31.2870  Initialized
00:11:31.3085  Submitted     (+21ms)
00:11:31.4203  Accepted     (+132ms)
```

The verdict arrives 20-200ms later, on `OnOrderUpdate`. At the instant this loop runs the leg is
`Initialized`, so the predicate is false for every order that will *later* be rejected. The only
order it can catch is one already terminal *before* submission, which nothing produces.
`partial_submit` is therefore unreachable, and a caller that trusts `status: "submitted"` learns
nothing about whether its protective legs were accepted — [[a-green-that-can-never-be-red]]:
for any status value, ask what input makes it fire, and if you cannot name one, it is not a status.

The caller here is frequently **an agent** via `nt_place_atm_order`, which makes a truthful status
load-bearing rather than cosmetic.

**Why P2 and not higher:** the downstream net is real. `NAKED_POSITION` + the grace timer +
`MISSING_STOP_ATTACH` do notice an uncovered position within `StopGuard.StopAttachSeconds`, so a
rejected stop is caught by the guard even though the bracket call misreported. This is a truthful-
reporting defect, not an unprotected-position defect.

**Direction:** the outcome cannot be known synchronously, so do not try. Either report
`status: "pending_legs"` with the leg ids and let the caller poll `nt_atm_bracket_status`, or have
`RegisterBracket` arm a short deferred check that emits an `ATM_LEG_REJECTED` event on the real
transition. Do **not** simply widen the state list — the bug is the *timing*, and a wider list read
at the same instant is still read too early. [[report-the-outcome-not-the-call]].

⚠️ **TWO THEORIES THIS ENTRY RECORDS AS DISPROVEN**, both by the same eight-bracket measurement,
so that neither is re-derived from a source read:

1. *"The ATR strategies never round to tick size, unlike the three other price-writing paths
   (`RiskGuardAddOn.cs:5099`, `TradeCopierEngine.cs:3942`, `CopierReconciler.cs:447`), so
   `MNQ`/`NQ`/`RTY`/`M2K`/`CL` — whose `DefaultStrategy` is `AtrAdaptive`, reached whenever
   `strategyName` is omitted (`McpBridgeAddOn.cs:5706`) — submit off-tick stops that the broker
   rejects."* The prices genuinely are off-tick and it genuinely reaches the broker:
   `29876.04464285714`, `29872.866071428572`, `29897.41964285714`. **NT8 rounds them itself on
   submit** — `29876.04464… -> 29876.0`, `29872.866… -> 29872.75`, `29897.4196… -> 29897.5`, nearest
   tick, and **all eight reached `Accepted` with zero rejections**; one filled as an ordinary
   stop-out. Not a safety defect.
2. *"A null `stopOrder` from `CreateOrder` still submits the entry (`469-486`) and reports
   `Status = "submitted"` with `StopOrderId = null`, no event, no retry."* The code does read that
   way and the fail-open direction is wrong. But an off-tick price was the only plausible way to
   make `CreateOrder` return null, and (1) shows it does not. **No evidence this branch is
   reachable**, so it is hardening, not a measured defect — and per
   [[check-the-exemplar-belongs-to-the-class]] it should not be filed as one until something
   demonstrates a null.

What survives from (1) worth its own small ID later: the unrounded `stopPrice` is stored in
`ActiveBracket.CurrentStopPrice` while the broker holds the rounded value, so the two disagree by
up to half a tick permanently. `Stop_5c903ad3` shows the symptom — a `ChangeSubmitted` at
01:45:38.746 that resolved to the **same** `29897.5` it already had. A no-op modification, and
[[nt8-order-change-semantics]] says a modification in flight is not free.


### P2-181. The bridge's `PlaceOcoOrder` carries the SAME dead synchronous verdict as `P2-150` — OPEN, found and fixed 2026-08-21 (session 63)

Found while fixing `P2-150`. `McpBridgeAddOn.cs`'s `PlaceOcoOrder` read `stopOrder`/`targetOrder`
`OrderState` in the same breath as `account.Submit(...)` and set `status: "partial_submit"` from
it — the identical defect to `P2-150`, in a second place, one repo over.
[[a-second-reader-of-the-same-state]]: count the sites before closing the ticket. `Submit` is
async, the legs are `Initialized`/`Submitted` at that instant, so the read could never catch a
rejection and `partial_submit` was a status no live input could set —
[[a-green-that-can-never-be-red]].

**⏳ FIX LANDED 2026-08-21 (session 63), pending deploy + Sim re-validation.** The synchronous
read is removed (not widened — the bug is the TIMING) and the OCO path reports `pending_legs` with
the leg ids and an honest per-leg `state` SNAPSHOT (not a verdict). SOURCE GATE only —
`McpBridgeAddOn.cs` is in no test build (`P2-27`), so `TestP2181_...` asserts the region no longer
contains `partial_submit`/`rejectedOrders` and reports `pending_legs`; `mutation/mutate_p2181.py`
3/3 proves the gate FAILS on the regression (the word or the read reappearing) rather than passing
vacuously. **Stays OPEN until deployed and re-validated on Sim** (an OCO placement reports
`pending_legs`).

### P1-140. The partial-profit order joins the stop and target's OWN OCO group, and both of those are for the FULL quantity — every outcome NT8 can pick is a defect — ⚠️ OPEN: slice 1 landed 2026-08-17 (session 56), so the hazard is gone and the feature is STATED unavailable, but native partials are the remaining slice and get their own ID

`PlaceBracket` submits the stop and the target with **`calculatedQty`** — the whole position — and
both carry the same `ocoId` (`:401`-`:402`). `MonitorTickCore`'s partial-profit block then submits a
**third** order into that same group (`:726`):

```csharp
var partialOrder = account.CreateOrder(position.Instrument, exitAction, OrderType.Limit,
    TimeInForce.Day, partialQty, partialTarget, 0, bracket.OcoId, "Partial_" + bracket.BracketId, null);
account.Submit(new[] { partialOrder });
bracket.PartialProfitTaken = true;        // <-- whatever the broker does with it
```

**There are exactly three things NT8 can do with that, and all three are defects:**

| NT8's behaviour | result |
|---|---|
| the new order **joins** the live OCO group — ⚠️ **not a guess: this repo live-validated it and then built on it.** `TestBracket_P0_9_ALateTargetJoinsTheLiveStopsOcoGroup` says *"an id can be joined while its group still has a live member"*, citing the live test in handover 4p | the partial fills → **OCO cancels the stop AND the target** → the remaining half of the position is **completely unprotected**, with no operator-visible symptom |
| the group does **not** cancel | the partial fills half, and the stop is still sized for the **full** quantity → it fires and **FLIPS the position** the other way. This is `P1-56`'s exact shape, already found in the copier: *"qty 1 AND qty 2 behind 2 lots, which FLIPS the follower when both fire"* |
| the OCO id is **refused** on a new order | the partial silently never happens, and `PartialProfitTaken = true` on the line after `Submit` means **it is never retried** — a risk-reduction feature that is dead and reports success |

⚠️ **`PartialProfitTaken = true` records reaching the line, not the outcome.** Set immediately after
`Submit`, outside any check on what the submission did. [[report-the-outcome-not-the-call]] — the same
shape as the panic kill-switch that cancelled its own flatten and reported success.

⚠️ **`partialTarget` is computed from a cache nothing ever reconciles.** `CurrentTargetPrice` is
written **once**, at construction (`:440`), and read only at `:717`-`:718`. `ReconcileStopFromBroker`
fixed exactly this for the stop — *"a polling monitor does not need settle events; it needs to stop
believing its own writes"* — and **the target leg never got that fix**. If the broker adjusted or
refused the target at placement (`P0-63`'s behaviour, and `P2-136`'s addendum measured a *stop*
refused for being invalid against the market), the partial's limit price is derived from fiction —
and unlike the stop cache, this one is used to **submit a live order**.

⚠️ **WHY NOTHING HAS EVER SEEN IT: `partialQty = (int)Math.Floor(bracket.Quantity * 0.50)` is ZERO
for a 1-lot position**, and `if (partialQty > 0)` skips the whole block. Every ATM test in the suite
and every live bracket measured so far has been **1 lot**, so the entire path is unreached. It needs
**2+ contracts** — and `DrawdownShield`, the only type with a partial block, is the **default**
`AtmStrategyConfig.Type`. [[an-order-is-not-one-fill]] is the neighbouring lesson: every copy-path
test sent one execution for the full quantity and hid a defect on each side.

⚠️ **THE COPIER PROVES THE MECHANISM BY RELYING ON IT, IN THE OPPOSITE DIRECTION.**
`TestBracket_TargetIsMirroredAsAnOcoPairWithTheStop` asserts the follower's stop and target share
**one** id, and states why: *"Without it the stop survives the target's fill and opens a fresh
position when it triggers."* That is the whole argument. A group of two is a bracket; adding a
**third** member sized differently from the other two turns the same mechanism into the thing that
removes the protection.

**Do NOT fix this by sizing the stop down after the partial** — that is a second write to a leg whose
first write may still be in flight, which `P0-61` establishes reverts the order and loses both. And
there is no version of "partial fills, protection stays full-size" that is safe either: a full-size
stop against a half position **flips** it. **Protection cannot be resized safely at trigger time, so
it must be PARTITIONED at placement** — which is what NT8's own ATM strategies do, one OCO group per
target.

**Proposed decomposition, because the safe fix and the real fix are different sizes:**

| | |
|---|---|
| **`P1-140`, this entry** | remove the hazard. The partial must not join the protective group, and since the remaining protection cannot then be corrected, the partial is **not submitted at all** — `ATM_PARTIAL_PROFIT_UNAVAILABLE` is said once per bracket, naming the quantity it would have taken and why it did not. The feature becomes **stated as unavailable** instead of silently producing a naked or flipped position. `PartialProfitTaken` must record the outcome, not the line |
| **follow-on, its own ID when taken** | partials done natively: at placement, split into one OCO group per target so nothing needs resizing. ⚠️ That means **two stops**, and `AtmOrderIdentity.StopName(bracketId)` returns **one** name that `P1-133`'s five call sites and its whole battery are keyed to — which is why it is not this ticket |

**Where**: `addons/DynamicAtmManager.cs` `:401`-`:402` (the full-quantity legs), `:714`-`:731` (the
partial block), `:440` + `:717`-`:718` (the unreconciled target cache).

#### P1-140 closure — 2026-08-17 (session 56)

Slice 1 landed (the hazard removed; the native implementation is still a follow-on ID, unfiled until
taken). Driven by the agent loop (`agent/tickets_p1140.json`), verdict **`APPROVE_PARTIAL`** in
**2 rounds**. Suite **2134 → 2139 / 0**, battery `mutate_p1140.py` **10 mutants**.

**The number that matters: `found 3` → `found 2`.** A two-lot bracket past its partial trigger no
longer puts a third order into the stop and target's OCO group. ⚠️ **That block had never executed,
anywhere, ever** — `(int)Math.Floor(1 * 0.50)` is `0` and `if (partialQty > 0)` skips it, so every
test in the suite and every live bracket measured on this box walked past it, on `DrawdownShield`,
which is the **default** type.

⚠️ **`APPROVE_PARTIAL` MEANS ONE REVIEWER, AND THAT IS WHEN TO REVIEW BY HAND.**
`deepseek-v4-flash` returned **1449 findings against a cap of 60**, was scored `UNPARSEABLE` and
dropped; `glm-5.2` approved with **0 findings**. That degeneration is now measured at **373 → 853 →
1449** across sessions. A patch with one zero-finding review has effectively had none.

**Two things that review found, both real:**

| | |
|---|---|
| four `⚠️` markers **stripped** from comments the ticket explicitly protected, including `P1-133`'s *REPORTING FIELDS ONLY* and the *`LogFromComponent`, NOT `Code.Output.Process`* note | restored; this is the third session in a row the loop has altered these glyphs, each time by a different substitution (`WARNING:`, `(!)`, deletion) |
| ⚠️ **the block's gate was swapped from `!PartialProfitTaken` to `!PartialProfitUnavailableAnnounced`** | correct **today** only because nothing assigns `PartialProfitTaken` any more. The follow-on ID assigns it again, and then a gate asking only *"have we announced?"* re-evaluates a partial that has **already been taken** and reports it unavailable. Both clauses now, pinned by `TestAtm_P1140_TheTakenFlagStaysFalseWhileNoPartialIsTaken` |

⚠️ **`PartialProfitTaken` IS NOW INERT, AND THAT IS `P3-137`'S SHAPE.** Its only writer was the line
after `account.Submit(...)` — which recorded *reaching the line*, not the outcome
([[report-the-outcome-not-the-call]]) — and that line is gone. The field is still serialised into the
bridge payload by `GetBracketStatus` as `partialProfitTaken` and **can no longer be true**. It is
**kept rather than deleted** because a writer is coming with the follow-on ID, and pinned by a test so
that stays a recorded decision instead of something nobody notices.
[[a-green-that-can-never-be-red]].

⚠️ **THE BATTERY FOUND A WEAK ASSERTION OF MINE, WHICH IS THE MORE USEFUL LESSON.** The test checked
that the message contains `"1"` — and a mutant printing the FULL quantity twice (`"2 of 2"` instead of
`"1 of 2"`) **SURVIVED**, because the OCO group named in the same sentence is `OCO-P140`, which
contains a `1`. **A substring assertion over a message that also carries identifiers is satisfied by
the identifiers.** Now asserts the phrase `"1 of 2"`. 9/10 → 10/10.

⚠️ **`CurrentTargetPrice` STILL HAS NO RECONCILER and it needs its own ID.** Written once at
construction (`:440`), read at `:717`-`:718`, and `P0-67`'s fix for the stop cache was never applied
to the target leg. Its consequence **dropped** with this fix — it used to determine the limit price of
a **submitted order**, and now only decides when a log line fires — which is why it is not folded in
here.

⚠️ **NOT LIVE-VALIDATED, and it needs 2+ CONTRACTS**, which is the whole reason nothing found it: one
lot cannot reach the block. The confirmation run is a two-lot `DrawdownShield` bracket carried past
`PartialProfitPct` of its target.


### P1-139. One refused trailing move asks the broker to put the stop BACK at breakeven — the re-arm `P0-67` added to un-latch the trail is what loosens it, and there is no monotonic guard anywhere — ✅ FIXED 2026-08-17 (session 56), found by reading `P2-136`'s neighbourhood

**`RequestStopMove` will ask the broker to move a stop the wrong way and call it a success.** There
is no comparison against the price the broker holds at any of the three call sites nor inside the
one function they all route through — and its own log line prints the loosening as though it were
an advance: `ATM_STOP_MOVE_REQUESTED ... requested stop 20010 -> 20000.5`.

**Reproduced deterministically** (`TestAtm_P1139_ARefusedTrailMoveNeverAsksTheStopBackDown`,
red at baseline, `Order is at 20000.5`):

| step | |
|---|---|
| 1 | Long MNQ, entry 20000.00, `ScaledRunner`. Breakeven fired long ago; the trail has advanced the stop to **20010.00**, confirmed by the broker each time, so `StopModifyAttempts == 0` |
| 2 | A trail move to 20013.00 is **refused** — the provider holds 20010.00 |
| 3 | `ReconcileStopFromBroker` counts it and re-arms: `if (BreakevenTriggered && attempts < Max) BreakevenTriggered = false;` |
| 4 | ⚠️ **The SAME sweep** then reaches the breakeven branch. `!BreakevenTriggered` is now true, and `ShouldTriggerBreakeven` compares price to **ENTRY** and knows nothing about the stop — so it is true and stays true for the life of a winning trade |
| 5 | `beStop = CalculateBreakevenStopPrice(entry, …)` = **20000.50**, computed from entry, and `RequestStopMove` asks for it |
| 6 | **9.5 points of locked profit handed back, on a live position, five seconds after a single refusal** |

**The flag has two meanings and that is the whole defect.** `BreakevenTriggered` is *"breakeven has
been reached"* to the breakeven branch, *"the trail may run"* to the trailing branch, and `P0-67`
made it *"retry the outstanding move"* to the reconciler. Clearing it to retry a **breakeven** move
is correct and is what `P0-67` was for; clearing it to retry a **trail** move recomputes the target
from the wrong origin. [[a-second-reader-of-the-same-state]], and
[[a-fix-can-commit-its-own-defect]] — the re-arm is `P0-67`'s own fix.

⚠️ **The direction guard alone is NOT sufficient, and getting only half of this is worse than
either half.** If the wrong-way request is merely refused, `BreakevenTriggered` stays false, and the
trailing block is gated on exactly that flag — so the trail never runs again and the position rides
to its original stop. **That is `P0-67`'s defect restored by its own repair.** Both halves are
required and each is pinned by a test that the other half fails
(`TestAtm_P1139_TheTrailStillAdvancesAfterARefusedTrailMove`).

⚠️ **`CurrentStopPrice` is `0` on a bracket that has never reconciled, and a bare comparison kills
every SHORT.** "Better" is higher for a long and *lower* for a short, so a short's first move —
19999.50 against a baseline of 0 — reads as wrong-way and is refused forever. An unset baseline is
*"no baseline"*, not *"the best possible stop"*. [[an-inapplicable-state-is-not-unreadable]], which
painted 95 of 97 accounts worst for the same reason. `TestAtm_P1139_AFreshShortBracketCanStillMoveItsStop`
is the negative control.

⚠️ **Our own refusal is not a provider refusal.** It must not spend `MaxStopModifyAttempts` — three
of them would abandon a perfectly healthy bracket — must not leave `RequestedStopPrice` set, which
would block the next real move for the life of the position, and must be **said**, because "the stop
did not move" is otherwise indistinguishable from the latched trail this whole file exists to
prevent.

**Why no test caught it:** every one of the eleven existing ATM sweep tests starts with the stop
**below** the breakeven price, where `beStop` is a genuine improvement and the guard is invisible.
The defect needs a stop that has already trailed *past* breakeven, which no test reached.

**Where**: `addons/DynamicAtmManager.cs` — `RequestStopMove`, `ReconcileStopFromBroker`, and one new
field on `ActiveBracket`.

#### P1-139 closure — 2026-08-17 (session 56)

Driven by the agent loop (`agent/tickets_p1139.json`), which ended **`NOT_CONVERGING`** — blocking
findings **3 → 7 → 5 with zero overlap between consecutive rounds**, and the loop's own stop message
said to arbitrate by hand. Its patch passed every gate it ran (`2113 / 0`, all 5 acceptance tests
green), so the patch was promoted and the findings settled by hand. Suite **2108 → 2132 / 0**.

**Three parts landed, and part three is the one that is easy to omit:**

| | |
|---|---|
| the invariant | `RequestStopMove` refuses any target that is not strictly better than the price the broker holds, before it reaches `ModifyStopPrice`. Direction from `bracket.IsLong`; equal refused too (`P0-61`); non-positive refused; a non-positive **baseline** means *no baseline*, not *the best possible stop* |
| the re-arm | `ActiveBracket.OutstandingStopMoveKind` — the reconciler clears `BreakevenTriggered` only when the move that was refused **was** the breakeven move. Passed explicitly from all three call sites, never inferred from the `reason` string |
| `alreadyAtBreakeven` | a stop already at or beyond the breakeven price **has** reached breakeven: record it without issuing a request. Without this the guard leaves the flag false and the trailing block is gated on it — ✅ CLOSED `P0-67`'s defect restored by its own repair |

⚠️ **THE FIX CONTAINS A REDUNDANCY AND IT IS RECORDED RATHER THAN REMOVED.** Part three alone
repairs the original defect, because it re-establishes `BreakevenTriggered` inside the **same** sweep
that wrongly cleared it. Part two makes that repair unnecessary instead of load-bearing;
`TestAtm_P1139_OnlyARefusedBREAKEVENMoveClearsTheFlag` is what stops it being deleted later as dead
weight. Found by the battery, not by reading.

⚠️ **THE ARBITER UPHELD FIVE FINDINGS AND ALL FIVE FAILED.** #13 and #14 are closed by machinery
already present (the reconciler's new `finally`; the pre-existing in-flight guard, which *is* that
concern and predates the patch). #15 demanded that a refused **trail** move re-arm
`BreakevenTriggered` — the exact inverse of this ticket. #16 said the non-positive refusal omits the
held price; the string contains it. #18 was **accepted, then measured false**: it needs something in
the reconciler's `try` to throw, and every call in it is `LogFromComponent`, whose whole body is
`try { inst.LogEvent(...); } catch { }`. Its one-line hardening was kept as defence and the
corresponding mutant declared an EXPECTED SURVIVOR.
[[agent-patch-loop-arbiter-gotchas]] — 0 upheld findings held, again.

⚠️ **THE BATTERY FOUND THE GUARD UNKILLABLE, AND THAT IS THE LESSON WORTH CARRYING.** `mutate_p1139.py`
replaced the entire wrong-way guard with `if (false)` and the suite stayed **green at 2113/0**.
Correct design is the reason: `alreadyAtBreakeven` means neither breakeven site ever hands
`RequestStopMove` a wrong-way price, and the trailing site has its own `stopMoved` check — so a
backstop at a choke point is, by construction, unreachable from the code around it. **The source gate
did not help either**: `IsLong` still matches inside a dead `if (false)` block, because a regex
cannot see reachability ([[a-source-gate-must-assert-the-condition]]). Closed by two `#if TESTING`
accessors (`RequestStopMoveForTest`, `DriveStopReconcileForTest`) that drive the invariant and
the re-arm rule directly. **5 of 14 mutants survived the first run; 13 of 14 killed after.**

⚠️ **AND THE RE-ARM RULE WAS UNOBSERVABLE THROUGH THE SWEEP** for the same structural reason:
`alreadyAtBreakeven` repairs a wrongly-cleared flag before `MonitorTickForTest` returns, so no
end-of-sweep assertion can see the difference. The single moment the recorded kind *is* observable is
immediately after the sweep that issued the request, which is what kills a mislabelled call site.

⚠️ **TWO OF THE FIVE RED TESTS WERE MY OWN WRONG SPECIFICATIONS AND COST THREE LOOP ROUNDS.** One
asserted the order was untouched at a price where the trail legitimately advances it — forbidding a
correct move. The other demanded `ATM_STOP_MOVE_WRONG_WAY` on the normal path, where the guard must
*not* fire. And the source gate's ordering assertion was vacuous first time out: `IndexOf` returns
`-1`, and `-1 < 1022` passes on exactly the baseline it exists to reject.
[[a-wrong-red-test-enforces-itself]], third and fourth instances.

⚠️ **A SETTLED DECISION WAS REVERSED BY MEASUREMENT.** The round-2 arbiter upheld *"a broker-confirmed
stop at 0.00 is a valid baseline"*, and the patch honoured it by defaulting `CurrentStopPrice` to
`double.NaN`. That field is serialised by `GetBracketStatus` as `currentStop` and returned verbatim by
`/api/order/atm/status`; the bridge passes no `JsonSerializerSettings`, so Newtonsoft's default
`FloatFormatHandling.String` ships it as the quoted string `"NaN"` and the value silently stops being
a number. The file had already decided the opposite ten lines from the guard —
`&& bracket.CurrentStopPrice > 0` — and the other reading refuses every short's first move forever.

🔶 **PARTLY LIVE-VALIDATED ON THE FUNDED ACCOUNT, 2026-08-17 (session 56)** — `TAKEPROFITPRO524207503`,
Provider31, bracket `302e7759`, 2 lots MNQ SEP26 from 30077.25. The refusal arrived without being
engineered (see ✅ `P2-141`, which is what caused it), and it settles **part two**:

| | |
|---|---|
| ✅ **the re-arm retries the move that was LOST** | three refused breakeven requests, and every one asked for **the same 30077.5** — never a price computed from somewhere else |
| ✅ **no wrong-way request, at all** | every request improved on the 30067 the broker held; `ATM_STOP_MOVE_WRONG_WAY` never fired |
| ✅ **`P0-67`'s legitimate re-arm survives the fix** | which is what `TestAtm_P1139_ARefusedBreakevenMoveStillRetriesTheSamePrice` pins, now seen on a real provider |
| ✅ **`P2-135` + `P2-134`, LIVE** | `ATM_STOP_MOVE_ABANDONED` said **once**, after the budget, naming the reason it OBSERVED on the failure that exhausted it |
| ✅ **`P3-137a`, LIVE** | `stopModifyAttempts: 3`, `stopMoveAbandonAnnounced: true`, `lastStopMoveFailureReason` — *"has this given up, and why?"* answered from the running system |
| ✅ **`P1-133` re-confirmed** | placement returned `stopOrderId: cde35048…`; the broker reported that order as `613562532221`. The lookup worked only because it keys on the NAME `Stop_302e7759` |

⚠️ **WHAT IS STILL NOT VALIDATED, AND IT IS THE ORIGINAL DEFECT'S OWN PRECONDITION.** The loosening
needs a stop that has **trailed PAST breakeven** and then a refused **TRAIL** move. On this run the
stop never moved at all, so the wrong-way branch was never reachable — the evidence above is about a
refused **breakeven** move, where the re-requested price is *correct by construction*. The remaining
confirmation needs a valid breakeven (`offset < trigger`, per ✅ `P2-141`), at least one accepted trail
advance, and then a refusal. That sequence cannot be scheduled: it depends on the market putting the
trailed stop close enough to the bid to be declined. **Do not record this entry as live-validated
until that specific order of events is in a log.** [[the-simulator-re-ids-nothing]] — and note the
evidence above names its provider, which is the point.


### P2-136. A NinjaScript recompile silently drops every tracked ATM bracket — ✅ FIXED 2026-08-17: SAID (session 55) and SURVIVED (session 57)

A **successful** compile hot-swaps `bin/Custom` into a new assembly. `DynamicAtmManager`'s registry
lives behind `private static readonly Lazy<DynamicAtmManager> _instance` (`:160`) — which reads as
"survives anything" and does not survive this. The new assembly gets a fresh `Lazy`, so
`_activeBrackets` starts **empty**, while the position and both broker-side legs are untouched.

**Measured**, on a box with **377 minutes of NT8 uptime and no restart**:

* `mcp_compile_result.json` stamped `2026-08-17T03:17:56Z`, whose own note reads *"NinjaScript
  hot-swaps right after this; if the connection dropped, GET /api/compile/result"*.
* **18** `CONNECTION_CHANGE Connecting -> Connected -> INITIALIZE -> ARMED_ON_START` bursts in 2.5
  hours — every one a recompile, none a restart.
* Bracket `1a48f3cf`, registered at 23:16 with an OPEN 1-lot MNQ position, was absent from the
  registry by 23:17:3x. The position was still long 1. Nothing was logged.

**Consequence:** breakeven and trailing stop, permanently, with **no operator-visible symptom** —
the stop and target still rest at the broker, so every surface an operator would check reports the
trade as protected. It is protected at its original price and will never move again. This also
explains the pre-existing orphan `0511fe1c`, left in `CancelPending` since 18:03.

⚠️ **A concurrent session does this to you.** The 23:17:56 compile came from another process
deploying unrelated `range_probability` NinjaScript in the `tvDownloadOHLC` repo. **Deploying an
indicator that has nothing to do with the guard discards the guard's ATM state.**

⚠️ **I filed the wrong cause first.** The initial reading was a transient `Account.All` miss during
a connection cycle hitting the unlogged `toRemove` at `:638` — plausible, wrong, and it would have
produced a fix for a defect that is not there. The compile timestamp matched to the second.
[[check-the-exemplar-belongs-to-the-class]].

**Two things are wanted, and they are separable:**

1. **Say it.** Neither removal branch (`:638`, `:652`) logs anything, so a bracket leaving management
   is indistinguishable from one that was never added. That is cheap and is the whole difference
   between silent and diagnosable.
2. **Survive it**, or state plainly that it cannot. `ActiveBracket` is already serialised into the
   bridge payload, so the shape for rehydration exists.

⚠️ `ARMED_ON_START` re-fires on every one of these. In `shadow` that is noise; in `live` it means a
deliberate disarm does not survive somebody else's compile. **Given its own ID as `P2-142`** rather
than folded: it is a different mechanism (the guard's arming gate, not the ATM registry) and it
contradicts `FR-30/31`, which deliberately refuses to rehydrate `_isArmed` so a restart cannot
silently re-arm. Whether a deliberate DISARM should persist is a policy question against that rule,
not a bug in this one.

#### P2-136 "survive it" closure — 2026-08-17 (session 57)

`addons/AtmBracketPersistence.cs` (new) + wiring in `DynamicAtmManager` and `RiskGuardAddOn`. Core
suite **2139 → 2182 / 0** across 18 new tests, `mutate_p2136survive.py` **26 mutants / 0 survivors**,
495 anchors / 0 broken, 9 local gates green. `v1.41.0`.

| | |
|---|---|
| **persist** | the registry is written to `UserDataDir/RiskGuard/atm_brackets.json` on register, on remove, and **on every sweep that saw a bracket** — the fields worth surviving are the ones the sweep MOVES (`CurrentStopPrice`, `BreakevenTriggered`), and a file written only at placement restores a bracket as if breakeven had never been reached, which then asks the broker to move the stop back DOWN. That is `P1-139` arriving by a new route. |
| **identity** | ⚠️ **NOT "is there a position".** A record says "account X, symbol MNQ", and a two-day-old file plus an unrelated MANUAL MNQ trade on that account satisfies that description exactly — restoring on it would attach this monitor to a position it did not create and start **moving the operator's own stop** on a funded account. A record is picked up only when the live order named `Stop_<bracketId>` is still working: bracket-unique, chosen by this addon, and per `P1-133` the one identity a broker does not replace. |
| **the price** | read off the live order that was just found, never from the file. `P0-67` one layer up: a price written before a compile is this monitor's last WISH, and trusting it reinstates exactly the cache-vs-broker fiction that made the trail LATCH. `RequestedStopPrice`/`OutstandingStopMoveKind` reset; the refusal budget resets too, because a new assembly is a new episode. |
| **direction** | a LONG record over a SHORT position is refused as `Mismatched`. The named stop may well be there — this is a hand-reversed position, not an identity failure — but every breakeven and trail price downstream is signed by `IsLong`. |
| **defer vs drop** | ⚠️ **"not restorable now" ≠ "never restorable", and this entry's own first diagnosis is why that distinction is here.** That reading blamed a transient `Account.All` miss during a connection cycle: wrong cause for THAT measurement, but the transient is real — an `ARMED_ON_START` burst IS a connection cycle and this code runs during one. An absent or not-yet-synced account DEFERS and stays on disk; a flat position is answered and DROPPED. The deferral is bounded at **3** and its give-up is announced, naming the consequence. |
| **consumed once** | `RestoreInto` refuses a bracket id already live. Without it a file re-read on every 5-second sweep would launder `MaxStopModifyAttempts = 3` into an unbounded order flood, and would replace the object the sweep is advancing. |
| **loud vs silent, both ways** | a MISSING file says nothing (the ordinary state of a box that has never placed a managed bracket); a file that exists and cannot be PARSED is announced, because something was being managed and is not any more. Both directions are pinned, so neither can drift into the other. |

⚠️ **THE WIRING WAS THE PART THAT NEARLY SHIPPED DEAD, AND ONLY THE BATTERY SAW IT.** Nothing in this
assembly referenced `DynamicAtmManager` at all before this ticket — it is reached solely through the
bridge's `/api/order/atm` — and `EnsureMonitor` is called from `PlaceBracket` **only**, so after a
recompile with no new order there is no ATM timer at all. The first version called the restore from
`InitializeRiskGuard`, and `mutate_p2136survive.py` put `if (false)` in front of that one call:

* the suite stayed **2176 / 0**,
* `check_anchors` stayed green,
* and `check_no_dead_safety_machinery.py` still read **WIRED** — because the ATM sweep also calls the
  method, and that gate asks "is this called by ANYTHING", not "by a driver that RUNS".

Nothing could kill it: NT8's startup path is not driveable from the test build, and a C# source
assertion finds the call text sitting inside the dead branch. **So the code moved rather than the test
being weakened**: the guaranteed driver is now `ExecuteSafetySweep`, which is `internal`, already
driven by the suite, and on a timer started unconditionally at init. The init call remains for
immediacy only, which is why the battery has no mutant against it alone — with the sweep in place,
killing it does not kill the restore. [[a-backstop-at-a-choke-point-is-unkillable]],
[[fix-the-class-not-the-instance]].

⚠️ **AND `check_no_dead_safety_machinery.py` WAS WRONG FOR EVERY ENTRY POINT, NOT JUST THIS ONE.** It
now deletes statically-dead branches (`if (false)`, `while (0)`, `#if false`) before searching, and
**self-tests in both directions on every invocation**. The first version of that stripper immediately
mis-fired: it matched an `if (false)` inside a **doc comment** in `DynamicAtmManager.cs` and its
single-statement walk then deleted forward to the next `;`, taking two REAL `ReconcileStopFromBroker`
call sites with it — so the gate reported a live, wired, load-bearing method as **DEAD**. Comments and
string literals are masked first, and the self-test pins that regression by name. A comment ABOUT a
mutant is not a mutant. `mutate_p2136survive.py` runs the gate as part of its own scoring, with a
control mutant that injects an unwired `Reconcile*` entry point — if that control ever SURVIVES, the
gate is not in the loop and every gate-dependent result in the battery is worthless.

⚠️ **STILL NOT LIVE-VALIDATED, AND THIS ONE IS CHEAP TO GET.** The reproduction is a managed
`DrawdownShield` bracket open across a recompile — `nt_compile` with an ATM position on. Grep for
`ATM_BRACKET_RESTORED` and expect the stop price in the line to be the BROKER's, not the file's.


### P3-137. `ActiveBracket.IsComplete` is never set true — two filters and one API field are inert — ✅ FIXED 2026-08-17 (session 55)

`grep -rn "IsComplete" addons/*.cs` returns five lines and **not one of them assigns `true`**:

```
:128   public bool IsComplete { get; set; }              declared
:436               IsComplete = false                    the only write, at construction
:484   _activeBrackets.Values.Where(b => !b.IsComplete)  GetActiveBrackets() -- passes everything
:508               isComplete = b.IsComplete             bridge payload -- always false
:628   _activeBrackets.Values.Where(b => !b.IsComplete)  the sweep's working set -- passes everything
```

Nothing in `nt8-mcp-bridge/addons` writes it either. Both filters read as "skip finished brackets"
and are no-ops; the bridge advertises `isComplete` to every consumer as a constant. Removal from
management is done entirely by `RemoveBracket` / `toRemove`, which is why nobody has noticed.

[[a-green-that-can-never-be-red]] inverted — ask what input makes this TRUE, and if you cannot name
one, delete the field and both filters rather than leaving a mechanism that looks load-bearing. If
it is meant to become real, it belongs to `P2-136`'s "say it" half, where a bracket that has left
management is exactly what wants recording.

#### P3-137a. `GetBracketStatus` exposes the wrong fields — the retry state is invisible

`GetBracketStatus` (`:495`-`:510`) returns thirteen fields and **none of them is
`StopModifyAttempts`, `StopMoveAbandonAnnounced`, or `LastStopMoveFailureReason`.** It does return
`isComplete`, which is the one that can never change. So the single question an operator has about
a bracket that has stopped trailing — *has this given up, and why?* — cannot be asked of the running
system at all; the only evidence is a log line that, per `P2-135`, may never have been emitted.

Found while trying to settle `P2-134`'s unexplained `b604e308` measurement from outside, which could
not be done for exactly this reason. Swap `isComplete` for the three retry fields, or add them.
Note the abandon message's own fallback comment (`:842`-`:845`) already reasons about "a bracket
restored from the bridge's payload" carrying the count — **the payload does not carry the count.**


### P2-138. The fleet tree was built, tested, mutation-covered, deployed — and served to nobody — OPEN→FIXED 2026-08-17 (session 55)

`BridgeFleetView.Build` had **no caller outside its own test file**. Measured:

```
$ grep -rn "BridgeFleetView\.\|FleetNode" --include=*.cs --include=*.js --include=*.html .
    38 hits, ALL of them in tests/BridgeSourceTests.cs
```

199 lines of view logic, 137 lines of acceptance tests, a 253-line mutation battery, wired into
CI, green — and **no endpoint returned the tree, and the commit that added the class did not touch
`ui/index.html`**. `P2-127`'s ticket was scoped to *"build the fleet tree ... in a class the
harness executes"*, deliberately and correctly; the **wiring slice was never filed.** The file says
so itself, in the doc comment on `NotApplicableRank`: *"⚠️ TEMPORARY, AND THE NEXT SLICE OF P2-127
REPLACES IT."*

⚠️ **The only surface this was detectable on was the operator saying they still could not see it.**
Every gate this repo has was green: build, 481 tests, 11 mutation batteries, `check_anchors`,
`deploy --verify`, CI. This is [[dead-safety-machinery-gate]] in the bridge repo — written, tested,
deployed, wired to nothing — and the gate that catches it in `nt8-riskguard` has no counterpart
here, which is [[a-gate-is-per-repo]] for the fourth time.

**Two smaller findings inside the same slice:**

* `FleetNode.Badge` was **declared and assigned nowhere**, so every node's badge was null. Same
  never-set-field shape as `P3-137`'s `ActiveBracket.IsComplete`, in the fleet view itself. §4's
  rows read `follower_1 1.0x ✔MATCH`, so a tree of bare names is not that pane. Fixed by folding
  the badge out of `FleetCopierRow.NotEnforcingLabel`, which the row already carried — not a fourth
  vocabulary.
* **§4's layout had never been built at all.** `docs/UI_REDESIGN_DESIGN.md` §10 item 4 says so in
  terms, and the operator called the shipped stacked-sections page *"cluttered"* on 2026-08-16.
  What they were reacting to is the **absence** of §4, not §4 — which is why the tree needed a
  *pane* to live in and not a fifth stacked section.

#### What landed

| half | where | how |
|---|---|---|
| mapping | `BridgeFleetView.RowsFromSnapshot` | agent-loop, `agent/tickets_p2138.json` |
| badge | `BridgeFleetView.Build` | agent-loop, same ticket |
| route | `McpBridgeAddOn.GetCopierSnapshot` → `payload["fleet"]` | agent-loop, same ticket |
| page | `ui/index.html` — §4's two panes | **by hand** |

The page half is hand-written because the loop's profile for this repo is
`file_suffixes=(".cs",)` and **cannot edit `index.html`**. That is not an oversight in the profile:
it is the same fact that makes the page gate weak, and it is why `RowsFromSnapshot` lives in
`BridgeFleetView.cs` rather than inline in the route. `McpBridgeAddOn.cs` is the one bridge source
`BridgeTests.csproj` cannot compile, so a mistyped field name mapped *there* deserialises to
`null`/`0` and the tree renders a **healthy-looking lie with every test still green**.

#### The evidence is a payload, not a shape I wrote down

`tests/fixtures/copier_snapshot_live_20260817.json` is captured from the deployed box — 2
relationships, 97 accounts, 25 fields per row — and the mapping test maps *it*. A field rename in
core now breaks a test instead of blanking a column. [[measure-the-deployed-system]].

#### ⚠️ One acceptance assertion was WRONG, and was corrected rather than satisfied

It demanded the page read the node's `rank`. That is the **opposite** of the design: core sorts the
tree — that is what `BridgeFleetView`'s 199 lines and its mutation battery are *for*, because two
incoming severity scales disagree about which end is bad — so a page that touched the rank would be
the second copy of an ordering this whole file exists to keep single. It now asserts the renderer
sorts **nothing**, over a stated 1611-char region.

Had it gone to the loop unfixed, **the loop would have implemented a defect to turn a gate green.**
That is the risk that comes with writing the tests first, and it is worth stating plainly: a red
test is a specification, and a wrong one is a wrong specification with a mechanism for enforcing
itself. [[a-fix-can-commit-its-own-defect]].

#### Still open after this

* The **inspector** is still the old stacked sections, now filtered by the fleet selection. §4 puts
  set-rarely config there behind tabs; that is not built.
* **Inline row actions** — arm/disarm, enable/disable, ratio — are §4 decision 3 and remain `P2-126`
  (the page dispatches 2 of the 14 actions `/api/copier/config` accepts).
* The **events pane** (§4's bottom strip) exists nowhere.
* `NotApplicableRank` is still the stand-in its comment describes: an unlinked account has a GUARD
  state, and folding that in is what removes it.

#### Live-verified 2026-08-17, after deploy + `nt_compile` (0 errors)

The suite proves none of this: `FleetNode`'s members are public **fields**, and nothing in the
harness asserts what the camel-case resolver does with them. Read from the running box instead.

```
/api/copier/snapshot -> keys [takenUtc, rows, system, fleet]
node keys            : kind, name, role, rank, badge, children
Sim101             kind=group     rank=5  children=2
   - Sim-ORB       role=follower  rank=5  badge=disabled
   - SimCopy2      role=follower  rank=5  badge=disabled
Unlinked accounts  kind=unlinked  rank=6  children=94
```

And the **rendered page**, which b32d151 had to record as *"Nobody has LOOKED at the rendered
page"*:

| checked | result |
|---|---|
| layout | `main.shell` `display:flex`, fleet pane 300px, inspector 909px |
| tree | 98 `.fnode` rows, 2 top-level nodes |
| select `Sim-ORB` | `Copier (1 of 2, for Sim-ORB)`, `Accounts (1 of 97)`, 1 row highlighted |
| select an unlinked account | `Copier (0 of 2, for APEX…)` + the system banner, `Accounts (1 of 97)` |
| deselect | `Copier (2)`, `Accounts (7 of 97)`, 0 highlighted |

⚠️ The unlinked case is the one worth keeping: that APEX account has no equity and no trades, so
the hide-empty filter would have hidden it — **selecting a row and getting an empty table is
indistinguishable from a broken page**, which is why the selection overrides that filter.

#### ⚠️ Measured cost, recorded rather than fixed

The fleet adds **10 477 bytes to a payload that was 1 793** — a 6× increase, ~123 KB/min at the 5s
poll. Almost all of it is 94 leaf nodes carrying `role: null`, `badge: null` and `children: []`.
That is affordable today and is **not** the 648 KB the inventory once returned, but it is the same
shape, and the remedy is the same one: omit nulls and empty children. Left alone deliberately —
recorded so the next person measuring does not think it went unnoticed.

#### P2-135 closure — 2026-08-17 (session 55)

Fixed by moving the announcement to the sites that **spend** the budget, called after the reason is
recorded, latched once per episode. Only the logging moved: the bounded retry still refuses and
`MaxStopModifyAttempts` is untouched. Driven by the agent loop
(`agent/tickets_p2135.json`). Suite 2072 → **2076 / 0**, tagged `v1.37.0`, deployed, `nt_compile` 0
errors.

⚠️ **The loop found a second defect — in `P2-134`'s own reasoning — and it is right.** P2-134
argued for **no latch clear at all**: the confirm branch is unreachable while the latch is set,
*"past MaxStopModifyAttempts RequestStopMove returns before it asks, a confirm needs an outstanding
request"*, so a clear would be a line that can never run. **The step it missed:** the
`CHANGE_IGNORED` branch does not clear `RequestedStopPrice`, so the request stays **outstanding**
after the budget is spent, and a provider that honours it late is confirmed on a later sweep with
no new `RequestStopMove` call at all. The branch is reachable, abandonment is **not** permanent for
a bracket, and without the clear a bracket that recovered and failed again would never announce the
second failure — on a position the operator believes is trailing. Both stale comments are corrected
in place rather than left contradicting the code.

⚠️ **One of my own acceptance assertions was UNSATISFIABLE, and is why four rounds could not
converge.** It required the substring `refus`. `P2-134` deliberately **deleted** that word, because
the message is shared with the path where nothing was ever submitted, and
`TestAtm_P2134_...NeitherMessageClaims...` pins its **absence**. Two tests pinning opposite things:
no implementation satisfies both. **Second wrong red test in one session** (the other is `P2-138`'s
`.rank` assertion). A red test is a specification, and a wrong one is a wrong specification *with a
mechanism for enforcing itself* — the loop will implement a defect to turn a gate green. Read a red
test against the assertions that already exist before handing it to the loop.

⚠️ **Not live-validated.** The fix is deployed and compiled, but reproducing it needs a position
whose stop the provider declines to move, three times. It is reproduced deterministically in the
suite from the live measurement (`Sim101`, bracket `75726b75`), which is the evidence that exists.


#### P2-136 + P3-137 + P3-137a closure — 2026-08-17 (session 55)

All three fixed in one slice, driven by the agent loop (`agent/tickets_p2136.json`), finished by
hand where the loop could not reach. Suite 2079 → **2096 / 0**.

| | what landed |
|---|---|
| `P2-136` "say it" | `ATM_BRACKET_RELEASED` at both removal branches, naming the bracket and **which** condition — the two branches say different things. ✅ **LIVE-VALIDATED on the FUNDED account 2026-08-17 (session 56)**, `TAKEPROFITPRO524207503` / Provider31, bracket `a58ad4da`: its stop filled and 5s later the sweep said *"MNQ position is flat and no entry order is still working, so the trade is finished and the bracket is released. Nothing further is managed for it."* — the **finished-trade** sentence, not the orphan one, which is the distinction two of `mutate_p2135.py`'s mutants attack. Previously `Sim101` only |
| `P2-136` "survive it" | ✅ **DONE in session 57** — `AtmBracketPersistence.cs`, 18 tests, 26 mutants / 0 survivors, `v1.41.0`. See the closure block under the entry itself. Not yet live-validated |
| `P3-137` | `IsComplete` deleted — the property, its one construction-time write, both `Where(b => !b.IsComplete)` filters, and the `isComplete` API field |
| `P3-137a` | `GetBracketStatus` gains `stopModifyAttempts`, `stopMoveAbandonAnnounced`, `lastStopMoveFailureReason` |

⚠️ **THE LOOP WIRED THE ANNOUNCEMENT TO THE WRONG SINK, AND IT COMPILED, AND THE FIX WAS PRESENT.**
It used `NinjaTrader.Code.Output.Process` — the NT8 output tab, which **no operator surface and no
audit query reads** — rather than `RiskGuardAddOn.LogFromComponent`, which every other `ATM_*`
event uses. The line existed, was correct, named the right bracket, and reached nobody: the defect
it was added to fix, reintroduced by the fix. The acceptance test caught it only because it
observes `LogEventMessageObserver`. **A gate that checks a fix is PRESENT cannot see which sink it
writes to** — name the reader before writing the string.
[[an-alarm-wired-to-a-dead-output]].

⚠️ **`isComplete` HAD a consumer, and the grep that said otherwise was scoped too narrowly.**
`grep IsComplete` over both repos' `addons/` and the MCP wrapper returned five hits, all in
`DynamicAtmManager.cs` — and `tests/` was not searched. `TestAtm_ActiveBracketStatus` read
`status.isComplete` through **`dynamic`**, so removing the field did not fail a test: it threw
`RuntimeBinderException` and **killed the runner**, which is why the loop reported *"no parseable
result summary"* twice and never reached an arbiter. The assertion it was making —
`isComplete == false` on a new bracket — was itself a green that could never be red. Replaced with
one that can fail.

#### The mutation battery, and what it found — `mutation/mutate_p2135.py`, 12 mutants

⚠️ **FIRST RUN: 5 of 13 killed. The green suite was hiding four real gaps and three bad mutants.**
This is the clearest case yet for [[mutation-testing-beats-review]] in this repo: every test above
passed, and the battery showed the tests could not tell.

The four **real** gaps, all now closed with tests:

1. the **orphan branch had no test at all** — only the flat-position branch was driven
2. nothing asserted the two branches say **different** things
3. nothing asserted the line waits for the budget — announcing on failure **1 of 3** still yields
   one announcement, so a counting assertion cannot see it
4. nothing asserted the **latch clear** works, so a bracket that recovered and failed again could
   silently never announce the second episode

And one gap that needed the test to be **constructed differently**, not merely added: "announce
one line EARLIER, before the reason is recorded" survived because every attempt records an
*identical* reason, so the message is byte-identical either way. It is detectable only when
consecutive failures **differ** — the test now makes the broker hold a different price on the
attempt that exhausts the budget. ⚠️ And that test was **off by one on its first write**, because
an attempt had already been spent earlier in the same test; it is now keyed to the bracket's own
counter rather than the loop index.

⚠️ **THREE OF MY OWN MUTANTS WERE UNKILLABLE BY CONSTRUCTION AND ARE REMOVED.** Two mutated TESTS:
one re-added a line whose absence is a test's whole point (with the fix in place, it passes either
way), the other replaced a passing precondition with `Assert(true, ...)` — and **deleting a passing
assertion can never fail a suite**. A mutant whose kill condition cannot occur is a permanent
survivor wearing the costume of a finding. Whether an assertion RUNS is proved by *source* mutants.
One genuine **`EXPECTED SURVIVOR`** is declared and paired through `_battery.finish`: the
`ModifyStopPrice` call site is redundant with the top-of-method check on that path, kept because it
announces one 5-second sweep earlier.

⚠️ **THE BATTERY LEFT A LIVE MUTANT IN THE TREE ON ITS FIRST RUN.** It shipped without
`sys.stdout.reconfigure(...)`, crashed on `⚠️` in a mutant description **between applying a mutant
and restoring it**, and left the P2-135 defect itself in `DynamicAtmManager.cs` — the announce call
gone from the reconciler branch, three call sites down to two. **A commit at that moment would have
shipped the bug back in the same commit as the battery proving it fixed.** Second measured instance
(the first was `mutate_p182.py` in CI, 2026-08-15). `tools/check_batteries_pin_encoding.py` names
this exact failure and I ran it *after* the battery rather than before. It now has the pin **and** a
`try/finally`, because the pin closes the one failure that has happened twice and the `finally`
closes the class. [[a-battery-must-reach-its-restore-line]].

#### CI

`mutate_p2135.py` is appended to the `UI6+P2-112` bin rather than given its own, and **that bin
becomes the critical path** (~524s → ~1024s, roughly 3 minutes onto CI). The ceiling is **19** bins
— 20 concurrent jobs account-wide, shared with `nt8-mcp-bridge` — and the existing bins already
span 524s..842s, so ~500s cannot be absorbed anywhere for free. A re-pack is the right answer and
is deliberately **not** done here: `tools/pack_ci_matrix.py` refuses to pack on guessed weights and
this battery has never run in CI, so its weight does not exist yet. Re-pack after the first green
run; the command is recorded in `ci.yml` beside the bin.

#### Still open

* **`P2-136` "survive it".** A recompile still discards every tracked bracket; it is now *said*,
  not survived. `ActiveBracket` is serialised into the bridge payload, so the shape for rehydration
  exists — and `P3-137a` just put the retry state into that payload, which the abandon message's
  own fallback comment already assumed was there.
* `ARMED_ON_START` still re-fires on every recompile. Noise in `shadow`; in `live` it means a
  deliberate disarm does not survive somebody else's compile. Still needs an ID.
* `P2-135`/`P2-136` are **not live-validated**. Reproducing either needs a provider that declines a
  stop move three times, or a bracket dropped with a position open. Both are reproduced
  deterministically in the suite from the live measurements (`75726b75`, `1a48f3cf`).

### P0-180. `StopGuard.OnMissing: AutoStop` never places a stop in live execution — the guard rejects its own first stop as its own pending state — ✅ FIXED + LIVE-VALIDATED 2026-08-20 (session 62), v1.58.0 — suite 3475/0, battery 3/3

**Found by the Sim test, not the suite.** The `P1-151` AutoStop policy shipped in `v1.57.0`
suite-green, but the FIRST time it ever ran armed-live — a scoped Sim101-only window, MES 1-lot,
2026-08-20 — the grace timer expired and the guard **rejected its own stop**:

> `ARBITER_REJECTED: Arbiter rejected action PlaceStopOrder — would increase risk or target is invalid.`

The position then sat `NAKED_POSITION` (`covered=0, gap=1`) for the life of the trade, re-logged
every 10s by the audit sweep. `OnMissing=Flatten` was unaffected — the arbiter admits a
`FlattenPosition` unconditionally — which is why the pre-existing default always worked and this
stayed latent.

**Mechanism (a state-machine self-defeat).** `EvaluateGraceExpiry` set `fsm.State = ProtectedPending`
in its `isUnprotected` branch — *before* the `PlaceStopOrder` it emitted reached the arbiter — and
`ValidateInvariant` rejects a `PlaceStopOrder` whose FSM is `Protected || ProtectedPending`. The
reserve and the arbiter's duplicate-check shared one state value with two incompatible meanings, so
the guard rejected the first stop it ever tried to place. The premature reserve was also
**redundant**: `GraceEmitted` (set after both branches, checked at the top of the method) already
suppresses re-emission, and the *real* reserve-before-submit is in `ExecuteAction` (~line 6206) —
under lock, right before `Submit`, rolled back on failure (that is `P0-3`'s design; see
`TestT2_SubmitFailureRollsBackFsmAndClearsGraceEmitted`).

**Why the suite missed it.** `EvaluateGraceExpiry`, `ValidateInvariant`, and `ExecuteAction` were
each driven in isolation with FSM states set up independently; nothing carried the SAME action from
emission through the arbiter to the executor. Same family as `an-order-is-not-one-fill` and
`test-doubles-are-not-evidence`. The Sim test exists precisely to catch this class.

**Fix.** Delete the premature `fsm.State = GuardFsmState.ProtectedPending` in `EvaluateGraceExpiry`.
`GraceEmitted` remains the anti-duplicate latch; the FSM stays `Unprotected` after emission so the
arbiter admits the action, and the executor reserves `ProtectedPending` after the arbiter passes.
No arbiter change: its `ProtectedPending` rejection is now correct — it means a stop is genuinely
pending. `TestFsm_GraceExpiryPlacesAutoStopOnce` updated to assert the FSM stays `Unprotected` with
`GraceEmitted` set (the latch), not `ProtectedPending`.

**Evidence.** `TestP0180_GraceExpiryAutoStopSurvivesItsOwnArbiter` drives grace-expiry → the emitted
action → `ProcessAction(forceLive:true)` and asserts the arbiter admits it, a stop is **created**
(not the position flattened, via `BrokerCallObserver`), and the executor reserves `ProtectedPending`
and tracks the order. Red before the fix (`REJECTED (INVARIANT VIOLATION)`, broker calls `[]`), green
after (`EXECUTED`, `[CreateOrder,Submit]`). `mutate_p0180.py` (3/3): re-adds the premature reserve,
widens the arbiter to reject `Unprotected`, and corrupts the executor's reserve state — P0-180 kills
each.

✅ **Live-validated 2026-08-20 (session 62).** After deploying `v1.58.0`, the same scoped Sim101-only
test was re-run: a naked MES 1-lot placed a `RiskGuardAutoStop` (Sell StopMarket, Accepted) at
**7665.25** against a **7669.0** entry — **15 ticks = ~4.9 bps** below, exactly the 5 bps rule — with
no `NAKED_POSITION`. Flatten cancelled the stop; box restored to `shadow`. `v1.57.0` carried the
defect but no funded account was ever exposed: the deployed config was `Flatten` and `shadow` acts on
nothing. The box is now safe to arm live with `OnMissing=AutoStop` when the operator chooses.
