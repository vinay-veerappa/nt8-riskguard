# RiskGuard Backlog Roadmap — post-P0-180

**Written 2026-08-21 (session 62).** A prioritised plan for the OPEN backlog after the
`P1-151`/`P0-180` StopGuard work shipped and was live-validated.

⚠️ **This is a snapshot, and a snapshot rots.** The authoritative open set is whatever the plan's
entries say TODAY. Re-derive before trusting any count here:
`grep -nE "^### (P|F|UI|T)[0-9?]" docs/RISKGUARD_COPIER_HARDENING_PLAN.md | grep -ivE "CLOSED|FIXED|RESOLVED|✅|superseded"`.
Every item below cites its plan ID; the plan is the reference for each defect's mechanism and
evidence. This file is only the *order* and the *why-that-order*.

**Live anchor at time of writing:** `v1.58.0`, `mode: shadow`, `isArmed: true`, `guarding: true`,
all 102 accounts flat. AutoStop (`OnMissing=AutoStop`, ~5 bps) live-validated on Sim101. The box is
safe to arm live at the operator's discretion — that decision is not in this roadmap.

---

## How this is ordered

Three axes, applied in this order:

1. **Does it bind on real money, and is the fix's consequence obtainable?** ([[weigh-work-by-obtainable-evidence]]) A band letter measures consequence *if the fix is right*; it says nothing about whether you can find out. Items that can be **live-validated** on Sim/funded rank above suite-only ones of equal band.
2. **Cost of being wrong × cost to fix.** Correctness bugs that silently *mislead* (a wrong timestamp, a status that can't be set) are cheap to fix and expensive to leave, so they go early.
3. **Repo blast radius.** Cross-repo items (bridge pin dance) and core-guard changes carry more ceremony than bridge-only or doc-only ones.

Two standing constraints from the deployed system:
- **Config edits are inert under `shadow`** — any config-shaped change can be staged safely and only matters at arming. [[configured-evaluated-enforcing]]
- **Every fix ships the same way:** failing test → fix → mutation battery over the fix site → all 14 gates → CI green → deploy → **re-validate on Sim where the path is live-observable.** `P0-180` is the cautionary tale: suite-green for the life of the feature, broken the first time it ran live.

---

## Housekeeping (do first, ~minutes)

- **`P1-102` → CLOSE.** "No MCP tool to read/clear a lockout" is stale: `nt_lockout` exists and calls `/api/lockout` (`nt8-mcp-bridge/mcp/nt-mcp-server.js:314`, schema `mcp/lib/tools.js:364`). Verified 2026-08-21. Mark the entry closed.
- **`P1-149` → REFRAME** (see the dedicated section below; the "enforced by nothing" half is closed).

---

## Wave 1 — correctness bugs that mislead (cheap, high trust-value, contained)

> **✅ Status 2026-08-21 (session 63): DEPLOYED to the live shadow box (`v1.59.0`, armed,
> guarding, 0 compile errors) and Sim-validated.** P2-178: `nt_extract_trades` emits true UTC
> (`04:03:05.645Z` for a 00:03 ET fill = +4h EDT, DST-correct). P2-150: ATM placement returns
> `status: pending_legs`. P2-154: bad breakeven pair (offset 20 ≥ trigger 12) refused **addon-side**
> with a structured error (live now, no MCP restart). P2-181: `pending_legs` confirmed live via the
> shared ATM bracket path; the standalone OCO endpoint's live-check is gated on an MCP-wrapper
> restart (stale `limitPrice`→`targetPrice` param drift in the running Node process — unrelated to
> the fix). A fourth, **`P2-181`**, was found while fixing `P2-150`: the bridge's `PlaceOcoOrder`
> carried the identical dead synchronous verdict ([[a-second-reader-of-the-same-state]] — count the
> sites), and was fixed the same session. See the plan entries for evidence.

These are wrong *answers*, not missing features. Each is small and each is currently lying to a consumer.

| ID | Problem | Approach | Repo | Effort | Live-validatable? |
|---|---|---|---|---|---|
| **P2-178** | `nt_extract_trades` stamps Eastern times with a `Z` suffix → every consumer reads them 4h wrong (measured: `09:57:51.985Z` vs the log's `13:57:52Z`). | Emit true UTC (convert before formatting), or drop the `Z` and label ET explicitly. A `Z` is a claim, not decoration. | bridge | S | yes — compare against `interventions.jsonl` |
| **P2-154** | `nt_place_atm_order` accepts a breakeven pair (`offset >= trigger`) the addon then refuses at `PlaceBracket` — operator learns at placement, not at the schema. | Mirror `DynamicAtmManager`'s refusal (already load-bearing, `P2-141`) in the wrapper's arg validation / schema. | bridge | S | yes — reject before submit |
| **P2-150** | `PlaceBracket` reads the exit legs' `OrderState` in the same breath as `Submit()`, so `partial_submit` can never be set (`DynamicAtmManager.cs:526-536`). | Read state after the platform assigns it (next event / poll), not synchronously post-Submit. | core | S | yes — provoke a partial |

**Why first:** all three are contained, each misleads a real consumer today, and each is cheaply live-checkable. Fixing them buys trust in the surfaces the operator reads.

---

## Wave 2 — enforcement completeness (the P1-149 residue and its neighbours)

### P1-149 — REFRAMED (research 2026-08-21, see the report in the plan entry)

The defect's central complaint is **half-closed**: `BridgeSizingGate` now enforces `MaxContractsPerAccount` pre-trade on all three bridge order paths (`McpBridgeAddOn.cs:2623/2712/5760`), and the copier clamps to the same cap (`TradeCopierEngine.cs:5318`). The number is **not** dead — it is enforced pre-trade on the paths the guard/bridge/copier own, and reactively (`MAX_SIZE_BREACH` flatten, `RiskGuardAddOn.cs:4693`) everywhere else.

**The NT8 platform fact (irreducible):** an AddOn has no pre-submit veto for an order it did not originate. `OrderUpdate` fires no earlier than `Submitted`/`Accepted`, and instant market fills surface once, already `Filled` (`RiskGuardAddOn.cs:4667-4670`). So **manual UI orders, external-platform orders, and non-`RiskManagerBase` strategies can only be caught reactively** — cancel-if-still-working (a race) or flatten-after-fill (slips). The prop firm's own 60-contract desk refusal is the only true pre-trade cap on those paths.

**Actionable sub-tasks:**
1. **Reframe the plan entry** to the above (it currently reads as wholly open; it is not). *(housekeeping-effort)*
2. **Wire the contract cap into `RiskGatekeeper.CanTrade`** (`Documents/NinjaTrader 8/bin/Custom/Strategies/Vinay/RiskGatekeeper.cs:98`) so `RiskManagerBase` strategies get a genuine pre-trade size refusal, not just loss/drawdown/count. This is the ONE closeable enforcement gap. ⚠️ `RiskGatekeeper` lives in **neither git repo** (deployed `Strategies\Vinay` only) — decide where it should be version-controlled before editing. Effort **M**; live-validatable via a `RiskManagerBase` strategy on Sim.
3. **Accept manual/external as a documented non-goal** — reactive `MAX_SIZE_BREACH` is the only lever, and it slips. Confirm that flatten is as tight as it can be, and record the residue so it is not re-filed. [[configured-evaluated-enforcing]]

### Neighbours

| ID | Problem | Approach | Repo | Effort | Live? |
|---|---|---|---|---|---|
| **P1-131** | The bridge hand-rolls its own order-liveness list, disagreeing with the core's shared classifier in BOTH directions — and that decides whether a disconnect would strand you. | One shared classifier; the bridge consumes it, deletes its own. Cross-repo → pin dance. | bridge+core | M | yes — measured live |
| **P2-147** | 12 funded-account executions were dropped by the copier because they carry no `Order`, so no direction could be read. | Derive direction from the execution/position delta when `Order` is null; test with the captured live shape. | core (copier) | M | yes — replay the capture |

---

## Wave 3 — lifecycle & CI hardening (protect the invariants)

> **⏳ Status 2026-08-21 (session 63): P2-158 and P2-155 FIX LANDED (code + tests + batteries +
> gates); committed with Wave 2 for one combined CI run; P3-177 partially done.**
> - **P2-158**: `tools/check_lock_discipline.py` in BOTH repos, wired into both CI gate jobs. Core:
>   57 `lock (_stateLock)` blocks inspected, 0 violations (the addon queues cancels via
>   `DrainPendingCancels`, so nothing calls a broker method inline). Bridge: 0 blocks (no `_stateLock`),
>   armed via a self-test that supplies a synthetic violation.
> - **P2-155**: a superseded (post-hot-swap) `DynamicAtmManager` now stops its sweep — the timer
>   callback refuses to run unless `this` is the current owner (`_activeManager`, set in the ctor;
>   identical to `Instance` in production) and self-disposes the orphaned timer. Test
>   `TestAtm_P2155_ASupersededManagerStopsSweeping` (drives the FULL callback, which every other ATM
>   test bypasses) + `mutate_p2155.py` (6/6). Suite 3507/0.
> - **P3-177**: fixed the stale honesty in the touched comments with MEASURED data (critical path is
>   **1335s**, run 32499010481, not the cited ~1119s; `P0-166+P1-151+P0-180` bin measured 789s vs 891s
>   estimated, ~13% high). The two NEW batteries (`p1149gate`, `p2155`) carry estimates until this
>   combined run prints their `BATTERY_SECONDS`; a full `pack_ci_matrix.py` re-pack + true-up is the
>   follow-up once that run is green. Not closed.
>
> None closed — each plan entry stays OPEN until CI green + (for P2-155) Sim re-validation on a
> recompile.

| ID | Problem | Approach | Repo | Effort |
|---|---|---|---|---|
| **P2-158** | The lock-discipline check exists only in the agent-loop profile, so a HAND-WRITTEN change gets no `_stateLock` review — exactly how `P1-157` slipped a `Cancel` under the lock. | Port the check into `tools/` as a CI gate (both repos, per [[a-gate-is-per-repo]]). | core+bridge | S |
| **P2-155** | `_monitoring`/`_monitorTimer` are per-INSTANCE, so a recompile leaves the ATM sweep on an orphaned manager. | Make the latch singleton-safe like `DynamicAtmManager.Instance`. Same family as the hot-swap-wipes-static-state hazard. | core | S-M |
| **P3-177** | `ci.yml` bin comments claim a 1119s critical path; it is 1358s, and local estimates read 21-23% high. | Re-measure `BATTERY_SECONDS` from a green run, re-pack with `tools/pack_ci_matrix.py`, fix the comments. Also replace the `P0-180` bin's `~200s ESTIMATED` with its measured time. | core | S |

**Why here:** `P2-158` closes a gate-coverage hole that guards the one invariant (`_stateLock` never held across a broker call) whose violation is a deadlock/‑strand — cheap insurance. `P2-155` is the recompile-safety family we already know bites. `P3-177` keeps the CI packing honest so future bins are sized right.

---

## Wave 4 — observability & operator surface

| ID | Problem | Approach | Repo | Effort |
|---|---|---|---|---|
| **P2-132** | In `shadow` the rule inventory cannot tell a rule that JUST FIRED from one that never has — measured on the funded account with `MAX_SIZE_BREACH` live. | Add a `lastFiredUtc` / recency to the inventory vocabulary. | core | M |
| **P2-126** | The copier browser UI implements 2 of the 14 actions its own API supports. | Build out the remaining actions against `knownActions` (`McpBridgeAddOn.cs:4253`). | bridge (ui) | M |
| **P2-108** | `NAKED_POSITION` re-logs every 10s because the audit calls `LogEvent` directly, not via `DispatchActions`. | Throttle, or route through the dedup path. Noise, not risk. | core | S |

---

## Wave 5 — architecture & robustness (as capacity allows; no acute risk)

| ID | Problem | Approach | Repo | Effort |
|---|---|---|---|---|
| **P3-118** | Three readers of `Mode` with three case rules; `Mode: "Live"` is refused as unrecognised by the reader that decides arming. | One canonical, case-insensitive Mode parser. ⚠️ Worth doing BEFORE anyone writes `Mode: "Live"` into config. | core | S-M |
| **P3-124** | The mini/micro symbol table is written FOUR times in `TradeCopierEngine.cs`, two of them the sizing arithmetic twice. | Extract to one source of truth; the duplication is a drift hazard ([[a-second-reader-of-the-same-state]]). | core (copier) | M |
| **P3-111** | `/api/bars` throws an unhandled `FormatException` on a caller's query typo (`int.Parse`). | `TryParse` → 400 with a named field. | bridge | S |
| **P3-110** | The panic flatten's cancel set omits `OrderState.TriggerPending` — NARROWED live; small remainder. | Add `TriggerPending` to `ActiveOrderStates`. | bridge | S |
| **P3-33** | Global `lock()` on the hot path. | The pragmatic subset (never hold `_stateLock` across I/O) is largely in place; the full actor-model port is LARGE. Defer unless contention is observed. | core | L |

---

## Sequencing summary

1. **Housekeeping** — close `P1-102`, reframe `P1-149`. (minutes)
2. **Wave 1** — `P2-178`, `P2-154`, `P2-150`. (contained correctness; each live-checkable)
3. **Wave 2** — `P1-149` sub-task 2 (RiskGatekeeper cap) + `P1-131` + `P2-147`. (enforcement)
4. **Wave 3** — `P2-158`, `P2-155`, `P3-177`. (hardening)
5. **Wave 4** — `P2-132`, `P2-126`, `P2-108`. (observability/UI)
6. **Wave 5** — `P3-118`, `P3-124`, `P3-111`, `P3-110`, `P3-33`. (architecture)

**Not in this roadmap** (operator decisions, not engineering tasks): arming the box `live`; and the cooldown-ladder config values (deployed `CooldownMinutes=5, MaxConsecutiveLosses=3` vs the discussed `base 2 / cap 4`). Both are inert under `shadow` and change only what happens once armed.
