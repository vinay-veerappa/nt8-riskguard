# Market-open validation runbook — Sunday 2026-08-16, 18:00 ET / 15:00 PDT / 22:00 UTC

**Written 14:25 PDT, 35 minutes before the open, so that the open is spent EXECUTING and not
planning.** The operator is not trading this session, so Sim101 is free for deliberate abuse.

> ⚠️ **THE BOX IS ON PACIFIC TIME.** `date` reads PDT; every timestamp inside NT8's JSONL files is
> **UTC**. Comparing a file's local mtime against a UTC timestamp inside it is how this session
> briefly concluded the alert relay was dead when it was healthy. **Compare UTC to UTC.**

---

## 0. State at the time of writing — measured, not assumed

| thing | reading | how |
|---|---|---|
| guard | `shadow`, armed, **cannot act** | page header / `/api/riskguard/config` |
| copier | `live`, acting, **0 of 2 relationships enabled** | `/api/copier/snapshot` → `system` |
| alert relay | **healthy** — cursor offset `7848` == outbox size `7848`, zero backlog; hourly heartbeat last at 13:45 PDT, next 14:45 | `alerts_relay_cursor.json` vs `alerts_outbox.jsonl` |
| relay processes | **ONE relay**: PID 30340 (venv launcher, parent `cmd.exe`) and PID 7228, which is **its CHILD** — same start second, `--channel test_channel`. Up since 2026-08-15 23:30 PDT | `Get-CimInstance Win32_Process`, compared by `ParentProcessId` |
| ⚠️ Task Scheduler | says `State: Running`, `LastTaskResult: 0x800710E0` ("operator refused the request") | `Get-ScheduledTaskInfo` |
| accounts | 97, of which 7 report equity; funded `TAKEPROFITPRO524207503` at $50,183 | page |

⚠️ **CORRECTED BEFORE THE OPEN, and worth keeping as the method.** The first draft of this table
read "TWO relay instances are running" and told you to kill one before section A. They are one
relay: 7228 is 30340's **child**, same start second. Two rows in a process list are not two
programs — **compare `ParentProcessId` before concluding a duplicate**, or the first act of the
validation window is killing half of a healthy service.

⚠️ Task Scheduler still reports a state that is not evidence: `Running` with a last result of
`0x800710E0`. The relay's health here was established from the **cursor offset matching the outbox
size** and the hourly heartbeat in the log — *verify by the heartbeat, never by the task state.*

---

## A. `F-6` — repeating-condition suppression ✅ OBTAINABLE

**What is unvalidated**: that `GuardActionDeduplicator` emits ONE alert plus one
`ACTION_SUPPRESSED` per episode, instead of one line per evaluation. The suite proves it; the box
never has, because it needs a condition that genuinely repeats.

**The cheapest repeating condition is `NAKED_POSITION`** — a position with no protective stop,
re-evaluated every 10s. It needs one filled contract and nothing else, and it is `P2-108`'s own
exemplar.

```bash
# 1. baseline the two files FIRST -- a count is only a count against a mark
TOK=d0b837223cab4653
BASE_I=$(wc -l < "/c/Users/vinay/Documents/NinjaTrader 8/RiskGuard/interventions.jsonl")
BASE_O=$(wc -l < "/c/Users/vinay/Documents/NinjaTrader 8/RiskGuard/alerts_outbox.jsonl")
echo "interventions=$BASE_I outbox=$BASE_O"

# 2. one contract on Sim101, NO stop attached
#    nt_place_order account=Sim101 symbol=MNQ SEP26 action=buy quantity=1 orderType=market

# 3. WAIT 120 SECONDS. Do not shorten this -- the defect was 12 lines in 120s,
#    so a 30s sample cannot tell a fix from a slow clock.

# 4. count what arrived after the mark
I="/c/Users/vinay/Documents/NinjaTrader 8/RiskGuard/interventions.jsonl"
tail -n +$((BASE_I+1)) "$I" | grep -c NAKED_POSITION
tail -n +$((BASE_I+1)) "$I" | grep -c AUDIT_FINDING_SUPPRESSED
tail -n +$((BASE_O+1)) "/c/Users/vinay/Documents/NinjaTrader 8/RiskGuard/alerts_outbox.jsonl" | wc -l
```

⚠️ **THE MARKER IS `AUDIT_FINDING_SUPPRESSED`, NOT `ACTION_SUPPRESSED`, and getting it wrong would
read a PASS as a FAIL.** The first draft of this runbook counted the latter. `NAKED_POSITION` is
bounded by **`AuditFindingThrottle`** (`P2-108`), not by `GuardActionDeduplicator` (`P2-107`):
audit findings are `LogEvent`s with no action behind them, on a path `DispatchActions` never sees —
which is exactly why `P2-108` had to exist after `P2-107` shipped. **`ACTION_SUPPRESSED = 0` is the
CORRECT reading here**, and is the load-bearing zero in `P2-108`'s own filing.

**The pre-fix numbers are on record, so this is a comparison and not an impression.** Measured
2026-08-15 under Market Replay — one position, no stop, guard in `shadow`:

| sample | NAKED_POSITION | ACTION_SUPPRESSED |
|---|---|---|
| t+30s | 3 | 0 |
| t+60s | 6 | 0 |
| t+90s | 9 | 0 |
| t+120s | **12** | 0 |

Perfectly linear, one per 10s, indefinitely; 180 sat in the log when it was filed.

**PASS**: `NAKED_POSITION` is **bounded** for the episode, and exactly **one**
`AUDIT_FINDING_SUPPRESSED` announces the suppression — announced once, because trading a screaming
alarm for a silent one is not a fix.
**FAIL**: the linear 3 / 6 / 9 / 12 above.

⚠️ **`NAKED_POSITION` IS a `warning`** — it is in `GuardAlertSink.WarningEvents` — so it clears the
`Alerts.MinSeverity = warning` floor and **must** reach the outbox. An empty outbox here IS a
failure, unlike the `info` case noted below.

⚠️ **This test does not actually need the open.** `P2-108` was measured under **Market Replay**,
which produces a position just as well. If the open is late or the feed is unhealthy, run it on
Replay rather than skipping it.

⚠️ **The budget lives in the sink INSTANCE and NT8 rebuilds the whole Custom assembly on every
`nt_compile`.** Do not compile between step 2 and step 4, or each reload spends a fresh "1 of 1"
and the flood reappears for a reason that is not the defect. **Finish all compiling before 15:00.**

⚠️ **Check the severity floor before believing an empty outbox.** `Alerts.MinSeverity` is
`warning`; an `info` event is correctly absent from the outbox and present in
`interventions.jsonl`. An empty outbox is only a failure if the intervention line says `warning`
or above.

**Clean up**: flatten Sim101.

---

## B. `F-6` — the STALE-guard heartbeat ✅ OBTAINABLE, and free

The relay's heartbeat carries the guard's own freshness, so *relay down* and *NT8 down* are
distinguishable. It fires hourly at :45.

✅ **RESULT — PASSED at 14:45:13 PDT, before the open.** Recorded here because a runbook that
only holds plans is half a document.

* The heartbeat fired **14:45:13**, exactly one hour after `13:45:11`. The relay is alive.
* ⚠️ **The log line alone does not prove the claim** — `Discord update sent (0 embed(s), no file)`
  says a message went out, not what was in it. Driving `format_heartbeat()` against the live guard
  directory returns:

  ```
  **RiskGuard relay heartbeat**
  relay: alive, 0 alert(s) delivered since start
  guard: alive, last sweep 0s ago
  ```

  So the message really does carry the **guard's** freshness beside the relay's, which is the
  whole point: *relay up + guard stale* and *relay down* are different reports.
* `heartbeat.txt` is being stamped by the guard continuously (age **0s** against a 180s STALE
  threshold), so the guard's sweep loop is running in `shadow` as it should.
* ⚠️ **The STALE half is NOT driven** — it needs the guard stopped, which is a bigger intervention
  than this window allows. **Positive half only, and the branch is confirmed to exist and to be
  reachable** (`GUARD_STALE_AFTER_SECONDS = 180`). Say which half was measured.
* **Then kill NT8's bridge?** No — do **not** manufacture staleness tonight. The negative half
  (heartbeat reports the guard as STALE) needs the guard stopped, which is a bigger intervention
  than this window allows. **Record the positive half only, and say so.**

---

## C. Trailing stop / ATM breakeven — `P2-112`'s stop-MOVE half ✅ OBTAINABLE

`DynamicAtmManager.MonitorTick` was failing open with no dispatcher: the breakeven loop never ran.
Fixed and suite-proven; the stop actually MOVING has never been watched.

**The vehicle is the `DrawdownShield` ATM strategy** — checked before the open, it is the one of
the eight that carries `breakevenTriggerTicks` / `breakevenOffsetTicks`, so no template has to be
built by hand:

```
nt_place_atm_order
  account=Sim101  symbol="MNQ 09-26"  action=buy  quantity=1
  strategyName=DrawdownShield
  stopTicks=40  targetTicks=80
  breakevenTriggerTicks=12  breakevenOffsetTicks=2
  idempotencyKey=<fresh uuid>
```

1. Place it. Record the fill price and the **stop's price** from `nt_orders account=Sim101`.
2. Wait for price to travel **12 ticks** in favour (MNQ tick = 0.25, so 3.00 points).
3. Re-read `nt_orders`. **PASS**: the stop has MOVED to entry + 2 ticks. **FAIL**: it is still at
   entry − 40.

⚠️ **`breakevenTriggerTicks` is 12 by default and the open is volatile — 3 MNQ points is seconds.**
Do not walk away between steps 1 and 3, and record the timestamps: "the stop moved" and "the stop
moved *when it should have*" are different claims and only the second one tests the loop.

⚠️ **Symbol format**: pass `MNQ 09-26`; NT8 reports the position back as `MNQ SEP26`. Both are the
same contract — `P1-105` deliberately does NOT compare expiries for this reason, and a mismatch
here is not a defect.

⚠️ **`Account.Change()` semantics**: a second change in flight reverts the order, and the
Simulator echoes your price back. **Verify the move by re-reading the order after it settles**,
never from the change call's own answer.

---

## D. Lockout ADMIT half (`P1-106`) — ⚠️ **BLOCKED, and this is the reason to have written this early**

`BridgeLockoutGate` admits an order that strictly REDUCES a position while a lockout is in force.
Only the REFUSAL half is live-validated. To validate ADMIT you need an account that is
**locked out AND holding a position**, and **there is no path to that state tonight**:

* `/api/lockout` accepts `status, unlock, reset, clear` — **measured in the source today**. There
  is still no action that IMPOSES a lockout.
* `nt_emergency_flatten` does impose one, but it **flattens first**, so you end up locked and
  FLAT — and then you cannot open a position, because opening one is not a reducing order. **The
  state is unreachable from that direction by construction.**
* A rule breach would impose one while the position is open — but the guard is in `shadow`, and a
  shadow lockout deliberately does **not** bind (`P2-92`), so nothing would be refused and there
  would be nothing to admit.

**Therefore ADMIT needs the guard in an ACTING mode**, which puts all 97 accounts — including the
funded TPT PRO — under a guard that will really flatten and really lock. **That is the operator's
call, not a validation step**, and it is the same line `P3-122` was filed under.

**If the operator says yes**, the narrowest form is: guard → `live`, breach the daily loss limit on
**Sim101 only**, confirm the lockout binds, then attempt (a) an increasing order → REFUSED, (b) a
reducing order → ADMITTED, then `unlock` and return the guard to `shadow`. Budget 15 minutes and
do it FIRST, because everything else in this list is safe.

**If not**, this stays an unvalidated half and gets recorded as such. It does not become a new ID —
it is a confirmation run, not work.

---

## E. Already done tonight, before the open — no market needed

* ✅ **`P1-125`** — the copier's mode on the page: confirmed by the operator's screenshot
  (`copier live · acting` beside `mode shadow · armed · cannot act`).
* ✅ **`P3-122`'s reordered branch** — driven live at 14:05 PDT by enabling one relationship under
  a `shadow` copier: the row read **`copier shadow`**, *"the relationship is enabled, but the
  COPIER is in 'shadow' … submits nothing at all"* — and did **not** say "copies to SIMULATION
  followers only". Restored to `live` / 0 enabled, verified by re-reading two endpoints.
* ✅ **`P2-129`** — `set_mode` over the MCP wrapper, driven over stdio.
* ⏳ **`P3-128`** — fixed and committed; needs a core tag + bridge pin bump + deploy before the
  page shows `[ COPIER LIVE - NOTHING ENABLED ]`. **Do this before 15:00** (see the compile
  warning in section A).

---

## Order at 15:00

✅ **DECIDED BY THE OPERATOR 14:32 PDT, before the open: A/B/C first, and D only if they pass.**
The reasoning is theirs and it is the right way round — D is the only item that changes the box's
risk posture, and spending it on a session whose safe items have not yet been shown to work would
be paying the cost before knowing the tooling is sound.

1. **A** — the flood test. Needs 120 uninterrupted seconds and **no compiling**.
2. **C** — the ATM stop move, which needs price to actually travel.
3. **B** — free, just read the log at :45.
4. **D** — **conditional on A, B and C passing.** Guard → `live`, breach the daily loss limit on
   **Sim101 only**, confirm the lockout binds, then (a) an increasing order → expect REFUSED,
   (b) a reducing order → expect ADMITTED. Then `unlock` and **return the guard to `shadow`,
   verified by re-reading `/api/riskguard/config`** — not by the write's own answer.
   ⚠️ If any of A/B/C fails, **D does not run**: the failure is the session's finding and arming a
   guard on a box whose alerting or stop-management has just been shown wrong is the wrong order.
   ⚠️ While `live`, all 97 accounts are under an acting guard, including the funded TPT PRO. That
   is tolerable only because nothing is being traded on it. **Return to `shadow` before anything
   else, even if D fails halfway.**

**Record each as PASS/FAIL with the measured numbers, and for anything not driven, say which half
was measured.** A confirmation run that is skipped is not a pass.
