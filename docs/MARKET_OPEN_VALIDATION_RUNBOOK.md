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
tail -n +$((BASE_I+1)) "/c/Users/vinay/Documents/NinjaTrader 8/RiskGuard/interventions.jsonl" \
  | grep -c NAKED_POSITION
tail -n +$((BASE_I+1)) "/c/Users/vinay/Documents/NinjaTrader 8/RiskGuard/interventions.jsonl" \
  | grep -c ACTION_SUPPRESSED
tail -n +$((BASE_O+1)) "/c/Users/vinay/Documents/NinjaTrader 8/RiskGuard/alerts_outbox.jsonl" | wc -l
```

**PASS**: `NAKED_POSITION` appears **once** (or once per re-evaluation of a genuinely *worsening*
condition), `ACTION_SUPPRESSED` names the producer and the budget, and the outbox gains **one**
line, not twelve.
**FAIL**: ~12 `NAKED_POSITION` in 120s — the pre-`P2-107` behaviour.

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

* **14:45 PDT** (before the open) — read `logs/alert_relay.log` in `tvDownloadOHLC` and confirm a
  new `Discord update sent` line, then confirm the message names the guard's last-seen time.
* **Then kill NT8's bridge?** No — do **not** manufacture staleness tonight. The negative half
  (heartbeat reports the guard as STALE) needs the guard stopped, which is a bigger intervention
  than this window allows. **Record the positive half only, and say so.**

---

## C. Trailing stop / ATM breakeven — `P2-112`'s stop-MOVE half ✅ OBTAINABLE

`DynamicAtmManager.MonitorTick` was failing open with no dispatcher: the breakeven loop never ran.
Fixed and suite-proven; the stop actually MOVING has never been watched.

1. Place an ATM bracket on Sim101 (`nt_place_atm_order`), one contract, with a breakeven rule.
2. Note the stop's price via `nt_orders account=Sim101`.
3. Wait for price to travel the breakeven trigger distance.
4. Re-read `nt_orders`. **PASS**: the stop's price has MOVED to (or past) entry.

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

1. **D**, only if the operator has said yes (it is the one with a real decision attached).
2. **A** — the flood test. Needs 120 uninterrupted seconds and no compiling.
3. **C** — the ATM stop move, which needs price to actually travel.
4. **B** — free, just read the log at :45.

**Record each as PASS/FAIL with the measured numbers, and for anything not driven, say which half
was measured.** A confirmation run that is skipped is not a pass.
