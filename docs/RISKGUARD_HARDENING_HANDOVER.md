# RiskGuard / TradeCopier Hardening — Session Handover

**Last updated**: 2026-08-13 (session 18 — **a documentation pass; no code changed**. This header,
§0, §4a, §5, §7 and §8 were re-derived from the repo and from the live box rather than copied
forward. Everything they used to claim that was false is listed in **§5.10**, because the *pattern*
of how this file went stale is more useful than the corrections. **`P0-63` and `P?-66` are fixed,
deployed and compiling clean.** The next item is **`P0-67`** — §5.6.)

> ### Read in this order
>
> | | Where | What it gives you |
> |---|---|---|
> | 1 | **§0**, below | verified current state, the five things that will bite you, the commands |
> | 2 | **[§5 — THE OPEN BACKLOG](#5-the-open-backlog--authoritative-as-of-2026-08-13)** | the authoritative answer to *what is left?* Start at **§5.6**, the order |
> | 3 | **§7 — Decisions already made** | do not re-litigate; the review panel will try every round |
> | 4 | **§8 — Known traps** | each one cost a session to find |
> | 5 | session records, newest first: **§5.10, §5.9, §5.8, §5.7, §4z, §4y, §4x, §4w, §4v … §4e** | the reasoning behind a backlog entry, when you need it |
>
> ⚠️ **This file accretes, and a later section supersedes an earlier one.** Where two disagree, the
> higher-numbered §5.x wins. **§4a is now HISTORICAL** — its "START HERE" pointed at `P0-62`, which
> `P0-63` superseded and which is fixed; its counts and repo-hygiene notes were three sessions out
> of date. The reasoning in it still stands and is why the reconciler exists, so it is kept, marked,
> and no longer navigational.

> **Path note (repo split, 2026-08-12).** Most of this document was written while the addons lived
> in `tvDownloadOHLC` at `scripts/ninjatrader/addons/`, with the test project at `ninjatrader-addon/`.
> They now live here as `addons/` and `tests/`, and the deploy tool is `tools/sync_nt8.py`. Operative
> commands and source-of-truth statements have been repathed. **Paths inside historical records —
> "what landed", migration steps, closed defects — are deliberately left as they were written**: that
> is what the record said at the time, and the hardening plan keys defects to `file:line` across that
> history. Rewriting them would falsify the trail. See [NT8_REPO_SPLIT_PLAN.md](NT8_REPO_SPLIT_PLAN.md).
>
> The split's one behavioural consequence: `TestP2_38`'s three assertions against
> `McpBridgeAddOn.cs`'s source text moved to `nt8-mcp-bridge`, which is why the suite went 929 → 926
> with nothing broken. It is **953** now.

---

## 0. Start here

### Verified state — 2026-08-13, re-measured for this pass

Every row was checked, not carried forward. The command that checks it is in the last column.

| | | How to re-check |
|---|---|---|
| **Suite** | **953 passed, 0 failed** | `dotnet build tests/RiskGuardTests.csproj -v q --nologo; dotnet run --project tests/RiskGuardTests.csproj --no-build` |
| **Defects** | **71 IDs — 52 closed, 19 open.** Derivation in §5.0, so you can check it instead of trusting it. **4 opened and 1 closed by the 2026-08-13 live trade** (§5.13) | — |
| **Live-validated** | **`P0-63` trails and `P?-66` measures** — proven 2026-08-13 on `Sim101 → Sim-ORB`, not just in the suite | §5.13 |
| **Branch** | **`main` only** — `harden/p0-63` was merged and deleted. Pushed, 0 unpushed. Tags `v1.0.0` `v1.0.1` `v1.0.2` (code) `v1.0.3` (docs) | `git status -sb; git branch; git tag` |
| **Deployed** | **`v1.0.2` code is live in NT8.** 7 core files identical; 8 counting the bridge's; **0 orphans** | `python tools/sync_nt8.py --verify` |
| **NT8 compile** | 0 errors, net48. Every warning is pre-existing and in someone else's indicator | `nt_compile`, and read `errorCount` |
| **Guard** | `loaded: true`, `mode: shadow`, `isArmed: true`, `guarding: true` — re-verified after the 2026-08-13 recompile | `GET /api/riskguard/version` with **`Authorization: Bearer <token>`** (not `X-Auth-Token`, which returns `Unauthorized`) |
| **Box** | bridge `1.5.2-chart-discovery`, `dev: true`, 96 accounts, **feed connected** | `nt_health` |
| **Mutation** | 3 batteries, **31 killed, 0 survivors** | `mutation/mutate_cm3.py`, `mutate_cm4.py`, `mutate_p0_63.py` |
| **CI** | ✅ **Active in both repos** since 2026-08-13, `windows-latest`, every push and PR. Runs all of the above except deploy parity, in 4m39s. **Watched fail on purpose**, not just pass | `gh run list -R vinay-veerappa/nt8-riskguard -L 3` |

> ⚠️ **There are THREE disagreeing version identifiers on this box, and none of them is wrong by
> accident.** Git says **`v1.0.2`** (the real one — it is what `sync_nt8.py` deploys). `docs/VERSION.md`
> said **`v1.7.0-ui-audit`** until this pass, from an unrelated pre-hardening scheme. The addon's own
> constant reports **`1.1.0`** over `/api/riskguard/version`. **Trust the git tag and the file
> hashes; never a version string.** `VERSION.md` now says so at the top.

### What is deployed but NOT validated live

This distinction is the one this document has most often blurred, so it gets its own block.

* **`P0-53`, `P1-54`, `P0-55`, `P1-56`** — unit + compile only.
* **`T5`'s fail-closed gate** — needs an acting mode; `IsGuardProtecting` requires `mode == "live"`.
* **The firm-mirror rules** — loaded but unmapped, so none can fire.

**Validated live**: **`P0-63` and `P?-66` (§5.13, 2026-08-13 — the mirrored stop trails and both
fills measured)**, `P0-9`'s mirrored **stop** (§4l) and **target** (§4s), `P0-50`'s orphan-stop
release (§5.13), `P0-51`, `P1-52`, `P2-41`, `P0-48`, T3's giveback rule (§4g), the reconciler +
`P0-61`'s fix (§4v), and the ratio converter's slices 2 and 3b (§4z).

> **The remaining `provider: Simulator` caveat is now a narrow one, not a blanket one.** `P0-63`'s
> detection and its cancel-then-create fallback are proven on a live broker path — a *simulated* one,
> which is precisely where `Account.Change()` is silently ignored, so it is the **hostile** case, not
> the easy one. What stays unknown is only whether a funded `Provider31` account honours `Change()`
> at all (§5.4 item 1), and remedy 3 is correct under either answer.

> ⚠️ **The copier acts regardless of guard mode.** `shadow` restrains RiskGuard, not the copier.
> That is `P3-34`, and it is still open.

### Five things to know before you touch anything

**1. The plan's older `**Fix**:` notes are hypotheses, not instructions.** Several "settled"
recommendations were retired because following them would have made things *worse*:

- `P1-39` said prefer a serializer-level `ObjectCreationHandling.Replace`. That discards the
  `StringComparer.OrdinalIgnoreCase` dictionaries and silently makes instrument and firm lookups
  case-sensitive. Fixed per-property instead; a test pins the comparer.
- `P1-18` said skip the profile trailing-DD rule whenever `FirmMirror.Enabled`. On the live config
  `FirmMirror.Enabled` is `true` while its `TrailingDD` is `false` and nothing is mapped, so that
  would have left **no trailing-drawdown cover at all**.
- `P1-16`'s obvious fix (judge the trade at the flat transition) silently **drops losses** whenever
  realized PnL lags the position update — an ordering nothing guarantees.

Verify the mechanism against the code before acting on any entry, including ones marked settled.
Settled entries have since been retired for `P1-36`, `P1-13`, and `P0-9`'s "cancel-then-replace, not
modify" — always in this file *and* in the loop profile's `settled` tuple, which is
**`agent/nt8_riskguard.py:106`**. Retire from both places or the review panel keeps arguing for the
closed defect.

> The path above was `scripts/agent_loop/profiles.py` in every revision of this file until
> 2026-08-13. **That file has not existed here since the repo split**, so for two sessions the
> instruction "retire from both places" pointed at nothing — which is the exact failure it exists to
> prevent. Checked: the tuple is at `agent/nt8_riskguard.py:106`.

**2. A machine check is only as good as the paths driven through it.** The lock-scope invariant
was already machine-enforced (`Account.BrokerCallObserver` + `TestIsStateLockHeld()`) and still
missed `P1-43` — four `account.Cancel` calls under `_stateLock` on the order-update path — because
the check only ever drove the sweep and FSM teardown. `S4` now drives every entry point.

**3. Only NT8 proves the build.** `P1-47` compiled clean under net8.0 with the suite green and
failed in net48, because the methods sat inside `#if TESTING`. **Always `nt_compile` after
touching code near the test hooks**, and read `RESULTS:` from a *fresh* build — a `dotnet run
--no-build` after a failed build silently reports the previous assembly's result.

**4. A test double is not evidence, and this one hid a live P0 for months.** The NT8 stub could not
express `P0-63` at all: `Change()` applied the caller's values, so a silent no-op was
*unrepresentable* and 926 green tests said nothing about it. The stub now models the provider
holding its own copy and reverting on settle (§5.8). Before trusting a green suite about broker
behaviour, ask what the stub is physically able to get wrong.

**5. `P0-9` is fully implemented; what is left is live validation, not code.** Followers get a
mirrored **stop and target**, OCO-paired, both anchored to their own fill. Items (3) `StopLimit` and
(4) leader-cancels-stop are pinned by test.

### What the guard actually does right now

Armed, `shadow`. It evaluates every rule and logs would-be actions; `ProcessAction` returns
`SHADOW (SKIPPED)` before any broker call, so it cannot touch an account. Arming and acting are
**separate switches** — `_isArmed` enables evaluation, `_mode == "live"` enables action. Since
`P1-47` the guard comes up armed in shadow by itself and disarmed in acting modes;
`/api/riskguard/version` reports `mode`, `isArmed` and `guarding`, and coming up disarmed logs
`UNPROTECTED_ON_START`. Arming manually is still UI-only (`TOGGLE ARMED`); `nt_script_execute` does
not work on this box.

**Firm mirror is live but unmapped.** `P1-42` made `AccountFirmMap`/`FirmProfiles` actually load,
but no account is mapped and the top-level sub-rules are disabled, so no firm rule fires. Mapping
`TAKEPROFITPRO524207503` → `TakeProfitTrader` turns on real enforcement with real numbers — do it
deliberately, and run a shadow session on it first.

**No operational items remain.** Both that were once tracked here are done: the
`ShadowSessionsCompleted` reset (2026-08-07 — and the obvious command for it is destructive, see §8)
and `POST /api/riskguard/config` merging instead of flattening (`P2-41`, verified live).

### Commands

```powershell
# the suite -- ALWAYS build first; --no-build after a failed build silently
# reports the PREVIOUS assembly's result
dotnet build tests/RiskGuardTests.csproj -v q --nologo
dotnet run --project tests/RiskGuardTests.csproj --no-build -v q --nologo   # expect 953/0

# deploy: verify, sync, then recompile IN NT8 (files on disk are not loaded code)
python tools\sync_nt8.py --verify        # expect ALL IN SYNC (7 files)
python tools\sync_nt8.py
#   then nt_compile, and read errorCount

# the structural checks (free, instant)
python tools\check_direction.py          # no addon may name a bridge-owned type
python tools\check_no_stray_copies.py    # no addon .cs outside addons/

# the mutation batteries. All exit NON-ZERO on a survivor, and all three refuse
# to run from a red baseline -- see §8, they were decorative until 2026-08-13.
python mutation\mutate_cm3.py            # 14 killed   (copier matrix)
python mutation\mutate_cm4.py            # 10 killed   (copier round-trip)
python mutation\mutate_p0_63.py          #  7 killed   (ignored Change())

# free: do all ticket regions still resolve? READ THE LINE RANGES -- a degenerate
# one-line region also prints OK, and only `kind: line` regions should be one line.
$PY = "C:\Users\vinay\tvDownloadOHLC\.venv\Scripts\python.exe"   # agent-loop lives there
& $PY -m agent_loop --profile nt8-riskguard --profile-module agent.nt8_riskguard `
    --tickets agent\tickets_p0_63.json --list
```

> ⚠️ **If the BRIDGE changed too, deploy it from `nt8-mcp-bridge` with `python tools/deploy.py`**,
> which deploys the bridge **and its vendored core**. Deploying either repo alone fails the whole
> NT8 Custom assembly, which stops **every** addon loading — the risk guard included. And keep the
> bridge's submodule pin bumped when this repo moves: a stale pin makes `deploy.py` **overwrite a
> newer live core with an older one**. That is now blocked mechanically (exit 2) — §8.

> ⚠️ **This repo has no `.venv`.** `agent-loop` is installed in *tvDownloadOHLC's* venv, and it
> must be invoked with **this repo as the working directory** so that `--profile-module
> agent.nt8_riskguard` resolves. There is no `scripts.agent_loop` module and no `selftest` entry
> point here; both were paths into the archived predecessor loop.

> ⚠️ **This repo carries `agent_loop.config.json` setting `think: false` for the implementer.** With
> thinking on, the role spent its entire 96000-token budget on reasoning — 408,089 chars, **empty
> content**, `done_reason=length` — as soon as the ticket grew a hardened spec (§5.9). Do not turn it
> back on without raising `max_tokens` in the same edit.

**The arbiter recommends; it never ships.** A run that ends `ARBITER_SHIP` has *not* applied
anything — and `--resume-raw … --apply` is **not** a promote-what-I-read command, it is a fresh run
seeded with that raw (§4q). To promote an exact candidate, splice it with the loop's `regions.apply`
and diff the result against the `final.patch` you reviewed. Across four SHIP rulings in session 13
the arbiter upheld **0 of 66** panel findings, and on one plan the panel was right about a signed
exit quantity that would have **increased a follower position sitting opposite the leader**.

> ✅ **Work is test-first from here.** A ticket declares `expect_green`; the loop refuses it unless
> those tests are already failing at baseline, and fails any candidate that leaves one red.
> Reviewers judge the tests' completeness and accuracy too. This closes the hole T5 went through —
> it reached `ARBITER_SHIP` with its own acceptance test still red. See the plan's §6.0.

### Before booking any live validation

- **`MAX_TRADES_BREACH` fires on entry on `Sim101`/`Sim-ORB`** (`MaxTradesPerSession` 8, both past
  it), and **`EDGE_WINDOW_BREACH`** fires on an ordinary overnight entry. Armed live, either one
  flattens the trade about a second after it fills — destroying the test rather than the defect
  (§4p). In `shadow` they only log.
- **A `Sim101` trade reaches THREE follower accounts.** `Sim101 → Sim-ORB → {SimCopyTest1,
  SimCopy2}` is a live chain, because `Sim-ORB` is our follower *and* a third-party copier's
  leader. That is `P1-57`, still open.

<details><summary>Earlier headers, kept for the record</summary>

**Session 16, 2026-08-12** — the repo split executed; this file moved to
[nt8-riskguard](https://github.com/vinay-veerappa/nt8-riskguard), tagged `v1.0.0`, suite 926/0 (929
minus three assertions that moved to the bridge). A migration, not a defect.

**Session 15, 2026-08-12** — the copier ratio converter complete and deployed (slices 1, 2, 3a, 3b),
suite 929/0, validated on the sim accounts. A feature, not a defect.

**Session 12–14** — `P0-61` fixed; ratio converter slices 1 and 3a. The deployed build was
`f174ba68` on the old `harden/riskguard-p0-51` branch, in the pre-split repo.

</details>

### 0.0 ⚠️ Commit SHAs cited in the older sections below no longer resolve

Two separate rewrites orphaned them. First, getting session 7's push through required purging
`data/` (a 126 MB `NQ1_1m.parquet` exceeded GitHub's 100 MB limit and had been silently rejecting
every push for 202 commits) and then 88 MB of `.m4a`. Both changed every commit SHA in the range.
Second, **the 2026-08-12 repo split rewrote history again** with `git-filter-repo`, so SHAs from
*before* the split — including `f174ba68`, `b5c58ae0`, `86c6376f`, `c9459121`, `995f6402` and
`06c6a484` — do not exist in this repo at all. The *work* is all present; only the identifiers are
dead.

**Run `git cat-file -t <sha>` before trusting any SHA quoted below.** SHAs from `v1.0.0` onward
(`978ed3a` and later) are live here.

**The merge-ordering lesson stands**: that push happened *before* shadow validation, which is the
opposite of what this document recommended. It was a deliberate call to get 282 unpushed commits off
one machine, not a signal that anything was validated.

---

## 1. What landed

The original P0 tickets, all merged into `main` long ago. **Their SHAs are orphaned (§0.0)** and
the table that listed them was removed 2026-08-10; what each one *did* is below, and that is the
part that still matters.

| Ticket | Content |
|---|---|
| T1 — `P0-1` + `P0-4` | stop-guard FSM coverage model |
| T2 — `P0-2` + `P0-3` | reserve-before-submit auto-stop, sized from the live position |
| T3 — `P0-7` | unrealized-only peak for the giveback rule |
| T4 — `P0-5` + `P0-6` | exits clamped to the follower's position; no sub-1 flooring (+ an exit must not round down to zero and strand the follower) |
| T5 — `P0-8` + `P0-9` | copier respects the lockout; fails closed when unguarded |
| — | test-harness repair (the suite could not previously catch defects) |

### T2 (P0-2 + P0-3)
The auto-stop now **reserves before it submits**: `AutoStopOrder`, `RecognizedStopOrder`,
`CoveredQuantity` and `State = ProtectedPending` are written under `_stateLock` *before*
`account.Submit`, and the lock is released before `CreateOrder`/`Submit`. Both failure modes roll
back — clearing the stop fields, `CoveredQuantity` and **`GraceEmitted`** (or T1's latch would
suppress every future grace action and leave the position naked), re-arming grace, and rethrowing
so `ProcessAction` records `EXECUTION_ERROR`. The post-submit FSM write is gone; `UpdateFsmOnOrder`
owns all further state. The stop is sized from a live re-read immediately before `CreateOrder`,
aborting if the position went flat or changed side. `StopGuardConfig.MaxAutoStopAttempts`
(default 2, `<= 0` treated as 2) bounds retries, after which the instrument is flattened.

**The one thing not to undo**: `ValidateInvariant` deliberately does *not* reject
`PlaceStopOrder` when `action.Quantity > liveQuantity`. It reads like a missing safety check, and
it was in the candidate — the arbiter caught it. Because the action is dropped *before*
`ExecuteAction` runs, nothing clears `GraceEmitted`, so `EvaluateGraceExpiry` (`if
(fsm.GraceEmitted) return`) and `FsmWatchdog` (`&& !fsm.GraceEmitted`) are both suppressed
permanently and the position never gets another stop. `ExecuteAction` re-sizes from the live
position, so the check bought nothing. This is now recorded in the loop's `settled` profile.

### T1 (P0-1 + P0-4)
`PositionGuardFsm` gained `CoveredQuantity`, `GracePending`, `GraceEmitted`, `GraceGeneration`.
A new `ArmGraceTimer(fsm, account, instrument, delayMs)` (must be called under `_stateLock`)
replaces both inline timer sites. Every transition into `Unprotected` while the position is open
now re-arms grace. `EvaluateGraceExpiry` is coverage-aware and sizes its action to the
**uncovered delta** (`pos.Quantity - CoveredQuantity`) — emitting the full quantity on top of a
live partial stop would over-cover and flip the position. `FsmWatchdog` remediates by arming a
250 ms timer (it runs under `_stateLock`, so it must not touch the broker); dedupe is
`!GracePending && !GraceEmitted`.

### Test harness repair — read this before trusting any test result
Four structural defects, all found while trying to use the suite as a gate:

1. **`TestExecuteOrderUpdateProcessesActionsOutsideLock` had been destroyed by a bad merge.** Its
   body was the *tail of `Main()`* — ten test invocations, a summary print, and
   `Environment.Exit(1)`. It asserted nothing, and its stray exit aborted the process at call 92
   of 117 whenever any earlier test failed, **silently skipping the last 25 tests (21%)** —
   every copier-group, hedging, order-verification and ATM test.
2. **`EvaluateFirmMirror` declared a `nowEt` parameter and ignored it**, reading `DateTime.UtcNow`.
   Past the firm daily-reset boundary (`DailyResetHourUtc`, default 22:00 UTC) the session rolls
   over and rebases P&L, so two firm-mirror tests failed **every day after 18:00 ET** — which then
   triggered the early exit in (1). Parameter is now honoured; the production call site passes UTC
   (it previously passed ET, silently discarded); both tests pinned to a fixed clock.
3. **One test was never invoked**, and 13 were reachable only from inside another test.
4. **Nothing detected any of this while the suite was green.** Added
   `TestHarness_AllDeclaredTestsAreInvoked` — `Assert()` records its caller via
   `[CallerMemberName]`, and the guard reflects over every declared `Test*` method, failing with
   exact names if the runner stops reaching one. Negative-tested by deleting an invocation.

**Coverage**: `TradeCopierEngine.OnExecution` — the trade-copy path, the riskiest code in the
addon — was compiled out of the test build by `#if !TESTING` and had **zero** coverage. The only
real blocker was a missing `Instrument.GetInstrument` stub. It is now in the test build, with
three copy-path tests that reproduce P0-5, P0-6 and P0-8 as **executable failures**:

| Test | Expected | Was | Proves |
|---|---|---|---|
| `TestCopyPath_ExitDoesNotFlipFollowerShort` | ≤ 1 | **5** | P0-5: follower left short 4 |
| `TestCopyPath_MicroToMiniDoesNotInflateNotional` | 0 | **1** | P0-6: 1 MNQ → 1 NQ, 10× notional |
| `TestCopyPath_LockedFollowerReceivesNoCopy` | 0 orders | **1** | P0-8: copier ignores lockout |

**All three now pass.** The P0-8 one also needed a harness repair before it could ever have
passed: it built a locked RiskGuard but never assigned `RiskGuardAddOn.Instance` (production only
does that in `State.Configure`), so `OnExecution` saw no guard, took the unguarded branch, and
allowed the copy because the follower is named `SimFollower`. The assertion could not observe its
own subject. `SetInstanceForTest` now wires it, and `SetupCopyPath` clears it so the static cannot
leak between tests; the assertion itself is unchanged.

**Suite state at the time**: was 221 visible tests / 2 failures / 25 skipped, then 356 passed / 0
failed once the harness was repaired. **It is 686/0 today.** Any failure is a regression.

---

## 2. Two P0-era findings worth keeping

*(T1–T5 are all long since committed, merged and deployed. The per-ticket status table that used to
sit here was stale and its SHAs are orphaned — see §0.0. Current state is the banner at the top.)*

### Two things found by review, not by the panel
- **T4's exit rounding.** Removing the `Math.Max(1, ...)` floor was right for
  entries — that floor *was* P0-6 — but applying it to exits created the mirror defect: an exit
  that rounds to 0 strands the follower in a position the leader has already left. Not an edge
  case: every partial exit rounds down independently, so a leader who entered 10 MNQ (follower:
  1 NQ) and exits in any increment below 10 produces 0 every time, and even a 5+5 exit strands it
  because `Math.Round(0.5)` is 0 under banker's rounding. Exits now take at least one contract
  when the follower holds one, clamped to the real position size.
- **T3's session reset.** Spec item 1 asks for the new peak fields to be cleared
  where `PeakEquity` is, but neither of those two sites was in the ticket's region set, so the
  loop could not have done it. Added by hand.

### Known-acceptable residue in T2 (do not re-open without new evidence)
- ~~A dead clause survives in `ExecuteAction`~~ — removed. Recorded because the
  *proposed fix* mattered: glm-5.2 wanted the comparison made against the earlier
  `position.Quantity` from the pricing read, which would abort the auto-stop whenever the
  position scaled **up** between reads, leaving it naked. The dead clause was harmless; that
  fix would not have been.
- **`AutoStopAttempts` is consumed by transient failures** — it increments before `CreateOrder` and
  rollback does not decrement it, so two broker hiccups escalate to flattening a live position.
  This is spec-conformant and fail-closed (the alternative is retrying forever while naked).
  Reviewers split on this: glm read it correctly, deepseek claimed the counter is *always* reset
  and is simply wrong — the setter only zeroes it when the previous state was `Protected`, and the
  submit-failure path is `ProtectedPending → Unprotected`.

---

## 3. The loop, and what its history taught us

**The loop is `agent-loop`, an installed package — `python -m agent_loop`, run from this repo with
`--profile-module agent.nt8_riskguard`.** Commands in §0.

> ⚠️ **Repathed 2026-08-13.** This section used to say "use `python -m scripts.agent_loop`" and link
> to `AGENT_PATCH_LOOP.md` for full documentation. **Neither exists here.** `scripts.agent_loop` was
> the in-repo predecessor, now archived at
> `tvDownloadOHLC/scripts/agent_loop/_archive_predecessor/` and **not to be run**; its post-mortem
> doc is `tvDownloadOHLC/docs/architecture/AGENT_PATCH_LOOP.md`, marked ARCHIVED. The current
> package's docs live in the [agent-loop repo](https://github.com/vinay-veerappa/agent-loop) —
> `docs/architecture/AGENT_LOOP_V2_PLAN.md` and `IMPLEMENTATION_DECISIONS.md`. The three
> `AGENT_PATCH_LOOP.md` links elsewhere in this file (§3, §4j, §4q) are dead for the same reason;
> the material they cited is reproduced where it is cited.
>
> Also gone with the predecessor: `ollama_patch_loop.py`, whose gates were defective in three ways
> (an empty reviewer response scored as a dissent, so no candidate could pass; the lock-scope gate
> closed its scope before the Allman brace and was inert for 28 of 32 sites; `summary.json` was
> overwritten per invocation and was never a ledger). **A green run from it was never evidence** —
> recorded because the same three shapes keep reappearing in new gates: see the mutation batteries
> that exited 0 while printing `SURVIVORS` (§8).

> **§4, §4b, §4c and §4d were retired on 2026-08-10.** They were per-round post-mortems of that
> dead tool. The lessons below are what survived; nothing else referenced them. Section letters are
> deliberately **not** renumbered — they are stable identifiers cited from the plan, from
> `CLAUDE.md` and from older transcripts, so a gap is cheaper than a shifted reference.

**Five lessons, all paid for, none specific to the old tool:**

1. **Unanimous APPROVE from adversarial reviewers is unreachable, and the finding count going *up*
   after a minimal fix is the signature.** Three rounds against one 168-line method produced 11 then
   13 findings with **zero overlap**; a two-line fix in the next round drew 33. That is why there is
   an arbiter.
2. **Reviewers contradict each other on load-bearing facts.** On `AutoStopAttempts`, glm read the
   state machine correctly and deepseek asserted the exact opposite. Verify against the code.
3. **A reviewer's *proposed fix* can be worse than the defect it names**, and this has now happened
   repeatedly — see §4q, where all three of panel, panel and arbiter endorsed a fix that would have
   leaked a reservation forever.
4. **A 0-upheld arbiter ruling is not reassurance.** Read the patch (§4q).
5. **Confirm the candidate you promote is the one that was reviewed.** The old loop once printed a
   `promote:` hint naming a file it had never seen; the new loop's `--resume-raw … --apply` is a
   *fresh run*, not a promotion. Different mechanism, same failure, twice.

**Gates only prove no regression.** The suite had no coverage for the P0-2/P0-3 paths, which is why
those defects existed at all. Passing gates is necessary, never sufficient.

---

## 4a. HISTORICAL — the reasoning that produced the reconciler

> ## ⚠️ NOT THE BACKLOG. Do not plan from this section.
>
> **Superseded by [§5](#5-the-open-backlog--authoritative-as-of-2026-08-13), 2026-08-13.** Everything
> navigational in here was stale, some of it by three sessions:
>
> | It said | Actually |
> |---|---|
> | "62 defects, 49 closed, 13 open" | **67 IDs, 51 closed, 16 open** (§5.0) |
> | "START HERE: `P0-62` first — a live, open, naked-risk-adjacent defect" | `P0-62` is **SUPERSEDED** by `P0-63`, which is **fixed and deployed** |
> | "ratio converter slices 2 and 3 pending, slice 1 undeployed" | all four slices **complete, deployed, sim-validated** (§4z) |
> | "`harden/riskguard-p0-51` is unmerged and unpushed; the deployed build is `b5c58ae0`" | that branch does not exist in this repo; `main` @ `978ed3a` = `v1.0.2` is **deployed and pushed** |
> | Repo-hygiene items keyed to `docs/ROADMAP.md`, `scripts/trader/…` | those paths are in **tvDownloadOHLC**, not here — see §5.11 |
>
> **What is kept, and why:** the structural finding below is the single most useful paragraph in this
> document. It is why `CopierReconciler.cs` exists, and its argument — that 48 defects were closed by
> teaching the fast path one more case, while the item addressing the *class* went unstarted — still
> applies to the half of `P3-30` that remains. Read it as an argument, not as a plan.

### The reconciler is the primary path — the argument (2026-08-10)

> 🔶 **`P3-30`'s copier half SHIPPED 2026-08-10 (§4u).** `CopierReconciler.cs` is new, and both leg
> syncs decide through `ComputeDesiredBracket` + `Reconcile` instead of from one cached `Order`
> reference. A duplicate leg is now self-healing. Suite 762/0, net48 clean, deployed.
>
> **The pieces that remain** — ordering now lives in §5.6; only the *dependency* below is durable:
> 1. ~~**`P0-62`** — `Change()` applies the price but silently refuses a quantity INCREASE.~~
>    **SUPERSEDED by `P0-63`** (the call is a silent no-op on `provider: Simulator` for price *and*
>    quantity), which is **fixed and deployed**. The advice attached to it — *do not just widen the
>    retry budget* — was right, and is why remedy 3 verifies the read-back instead: §5.9.
> 2. **`P3-31`'s ledger** — required *before* the timer, not after. Between `Submit` and `Accepted`
>    the order is in neither `Account.Orders` nor the cache, so a timer without the ledger creates
>    the second leg. The seam in `Reconcile` is built and tested; the ledger is not.
> 3. **The background timer** — events call the reconciler; nothing calls it on a clock. A
>    divergence arriving with no subsequent event is still permanent.
> 4. **The RiskGuard-side audit** — naked position, orphan stop, FSM/broker divergence. `P3-30`
>    covers both addons; only the copier's bracket is done.
>
> ⚠️ **Do not confuse `bracket.StopInFlight` with `Reconcile`'s in-flight parameter** when you build
> the timer. Feeding the first into the second placed no stop at all. §4u has the mechanism.
>
> ⚠️ **Two guards in this code are unreachable and labelled as such** (§4u). One mutation SURVIVED
> and is kept deliberately. Read §4u before "simplifying" either.

The rest of this section is the reasoning that led here, and it still stands.

`P0-59`/`P0-60` are closed (§4t), and closing them properly rather than patching the symptom is
what this section is now about.

**The structural finding.** Almost every defect in this project is one shape: *the addon's model of
broker state diverged from the broker, and nothing re-derived it.* The plan said so on page one —
"the FSM is an optimistic fast path… **every P0 below is a case where the fast path can lose the
position and nothing recovers it**" — and then 48 defects were closed by making the fast path handle
one more case. `P3-30`, the item that addresses the class, has never been started, and
`ReconcileFollowerPosition` has sat written-and-never-called the whole time.

**So the next work is `P3-30` + `P3-31` together, built as the PRIMARY mechanism rather than as an
auditor bolted alongside the FSM:**

1. `ComputeDesiredBracket(leader, follower, relationship) → DesiredBracket` — **pure**, computed
   from broker reads with no accumulated state. Every arithmetic defect (`P0-6`, `P0-7`, the signed
   offset, the exit rounding, off-tick prices) becomes a property test here.
2. `Reconcile(desired, owned, inFlight) → Actions` — **pure diff**, and it cancels *extra* owned
   legs. That single rule makes duplicate legs self-healing instead of permanent.
3. Events **and a timer** both just call it. Idempotent, so ordering stops mattering — which
   dissolves `P0-49`, `P0-55`, `P1-56`, `P0-59` as a class rather than one at a time.

> ⚠️ **A reconciler without the in-flight ledger reproduces the duplicate-leg family**: between
> `Submit` and `Accepted` the order is not yet in observed state, so a naive second pass creates a
> second one. `P3-31` is not a follow-up to `P3-30`, it is half of it.

Doing this makes several things we currently maintain by hand unnecessary: `P1-56`'s reservation,
the OCO dead-group conditional, the multi-target refusal, and the `StopInFlight`/`StopResyncOwed`/
`TargetInFlight`/`TargetResyncOwed` flags.

Then `P1-57` — §4s showed its defence held only because the third-party copier happened to embed
our name in its own; a native `Stop1` would have gone straight through.

> **Booking a live session**: `MAX_TRADES_BREACH` now fires on entry on `Sim101`/`Sim-ORB`
> (`MaxTradesPerSession` 8, both past it), as well as `EDGE_WINDOW_BREACH` outside the edge window.
> Armed live either one flattens the trade and cancels its mirrored legs. And a `Sim101` trade
> reaches **three** follower accounts (`P1-57`).

### ~~Ready to code, in value order~~ — superseded by §5.6

The value-ordered table that stood here is replaced by **§5.6**, which is maintained. Three notes
from it are worth carrying, because they are engineering constraints rather than priorities:

- **`P3-30`'s remaining half needs `P1-36`'s multi-stop coverage sum** — the guard-side audit asks
  exactly the question `CoveredQuantity` already answers. Share it; do not rebuild it.
- **`P1-13` is two pieces of work, not one.** A concurrent-guard-event stress test has to exist
  before the threading inversion lands — see the S-series warning immediately below.
- **`P3-32` looks SUPERSEDED by `P0-9`** — the signed-offset mirror is precisely "follower risk
  anchored to the follower's own fill". Read it before scheduling it as new work; it may just need
  closing. Flagged 2026-08-07, **still not verified**.

### ⚠️ The S-series is not concurrency coverage

`S1`–`S9` are all in the suite as of session 8, and it is tempting to read "the stress backlog is
done" as covering `P1-13`. **It does not.** `S4` is lock-scope, `S7` is copier fan-out, and
`S5`/`S6`/`S8`/`S9` are **sequential scenario tests**. `P1-13`'s inversion turns six handlers the
dispatcher was implicitly serialising into genuinely concurrent ones, and nothing tests that.

Session 8 deferred `P1-13` explicitly on the grounds that the stress backlog was its prerequisite.
Once that backlog was written it was clear the reasoning was wrong: the tests are sequential and
the risk is concurrent. **Doing the risky half before its coverage exists is how `P1-40` shipped.**

### ~~Repo hygiene — still open~~ — every item was stale or belongs to another repo

Re-checked 2026-08-13; current hygiene lives in **§5.11**. For the record, this block was wrong in
four ways, and the shape of the error is the point: **after the split, half of it described
tvDownloadOHLC.**

- ~~"`harden/riskguard-p0-51` is unmerged and unpushed; `main` is untouched; the deployed build is
  `b5c58ae0`."~~ **That branch does not exist in this repo** — it was the pre-split branch name in
  tvDownloadOHLC, which is still sitting on it. Here, `main` @ `978ed3a` = `v1.0.2` is deployed and
  pushed, and `b5c58ae0` was orphaned by the filter-repo rewrite (§0.0).
- ~~"`.githooks/pre-commit` is not automatic."~~ It was never migrated at the split, so for a day
  there was no `.githooks/` here at all. ✅ **Ported and installed 2026-08-13** in both addon repos —
  see §5.11. The original complaint was right about the *shape*: `core.hooksPath` is local config, so
  it is still not automatic in a fresh clone, and both READMEs now say so.
- ~~The Gemini API key needing rotation, and 0.28 GB of parquet in published history.~~ Both are
  **tvDownloadOHLC's**, keyed to paths (`scripts/trader/chart_agent/test_vision.py`,
  `docs/ROADMAP.md`) that do not exist here. Still real over there; tracked in §5.11 so they are not
  simply dropped.
- ✅ **`wip/p09-oco-target` was DELETED 2026-08-10** — its work was rebased and shipped, and the
  branch as it stood lacked five fixes (§4r). Rebasing it would have re-introduced them. This one was
  accurate, and is now history rather than hygiene.

---

## 4e. Deployment runbook

> **Ran once on 2026-08-07 — see §4f for what actually happened, including two claims below
> that turned out to be wrong.** Steps are kept in their corrected form; re-read §4f before
> re-running.

**Do not copy code first.** Set the mode before the new addon runs.

1. **Check the live config is not in an acting mode.** `~/Documents/NinjaTrader 8/RiskGuard/config.json`
   is the file the addon reads (`Path.Combine(Globals.UserDataDir, "RiskGuard", "config.json")`).
   It was `"Mode": "override_with_friction"`, an *acting* mode (`RiskGuardAddOn.cs:2455`).
   Deploying new code without changing this puts freshly-written flatten logic straight in front
   of a funded account. Set `"Mode": "shadow"` **and confirm the running addon actually reloaded
   it** — the config has no file watcher, so it is only re-read on construction or an explicit
   reload. Verify via `GET /api/riskguard/config`, not by reading the file back.
   - ~~There is a second `config.json` at `bin/Custom/AddOns/config.json`~~ — **resolved**: it
     was dead, nothing reads it, and it has been renamed `config.json.UNUSED_not_read_by_addon`.
2. **Diff deployed vs canonical — with line endings normalised.** Deployed files are CRLF and
   the repo's are LF, so a plain `diff` reports *every* line as different and looks like massive
   drift. Use `diff --strip-trailing-cr`. On 2026-08-07 there was **no** pre-existing drift.

Then:

3. Rotate `interventions.jsonl` so shadow output is readable. Safe while running —
   `File.AppendAllLines` never holds the file open.
4. **Sync with the script, never by hand.** `sync_nt8_strategies.py --verify --only addons` to see
   the drift, then the same command without `--verify`. Then `nt_compile` and read `errorCount`.
   The test build is net8.0 with stubs, NT8 is net48, and **only NT8 proves the real build**.
   **Put backups outside `bin/Custom/`** — NT8 compiles that tree recursively and a backup folder
   of `.cs` files causes duplicate-type errors.
5. **Check the box is quiet first** — `nt_compile` hot-swaps the running addon. `nt_positions` and
   `nt_orders` should show no open positions and no *working* orders (terminal leftovers are fine).
6. Run a full session in shadow **on a real-time feed**. Kinetick End Of Day gives no Level 1, so
   the simulator cannot fill and no guard path will execute — a session on that feed proves
   nothing. Then read `interventions.jsonl` and ask specifically: did `PEAK_GIVEBACK_BREACH` fire
   on a profitable flat account (T3), and did any `COPY_BLOCKED_NO_GUARD` line name an account
   that should have been allowed (T5)?
7. Only then consider restoring an acting mode. *(The `P1-37` / `ShadowSessionsCompleted` step that
   used to sit here is done — see §0 item 4.)*

**Roll back** by restoring the previous `.cs` files and recompiling; nothing here migrates state.
Config is separate from code, so a mode change alone is instant and reversible.

---

## 4f. Deployment record — 2026-08-07, shadow

Executed against a running NT8 (92 accounts, no open positions, no working orders).

| Step | Result |
|---|---|
| Live config → `shadow` | Done. Backup `RiskGuard/config.json.bak_20260806_224830`. Verified **in memory**, not just on disk, via `GET /api/riskguard/config`. |
| Stray `bin/Custom/AddOns/config.json` (`"Mode": "live"`) | Confirmed **dead** — nothing reads it; the addon uses `Globals.UserDataDir/RiskGuard/config.json`. Renamed `config.json.UNUSED_not_read_by_addon`. |
| Rotate `interventions.jsonl` | Done → `interventions.jsonl.20260806_224904` (110 MB). Safe: written with `File.AppendAllLines`, never held open. |
| Merge to `main` | **Deliberately deferred** until shadow validation. Fast-forward confirmed available (`main` is strictly behind, 0 divergent commits). |
| Deploy sources | 4 files, not 5 — `TestingStubs.cs` is unchanged by the branch. Backup at `Documents/NinjaTrader 8/_riskguard_backups/_backup_20260806_224954`. |
| `nt_compile` | **0 errors.** All warnings pre-existing and in unrelated files (`McpBridgeAddOn`, indicators); none in the three addons. |
| Verify | `RiskGuard Add-On v1.1.0 initialized in shadow mode`, `mode: shadow`, `isArmed: false` on every event. |

**Two traps in §4e above were wrong, and both wasted time. Corrected here:**

- **"The deployed sources differ from canonical" was a false alarm.** The deployed files are
  CRLF, the repo's are LF, so a plain `diff` reports every line as changed. Normalised with
  `diff --strip-trailing-cr`, the deployed files were **byte-identical** to canonical at the
  merge-base — there was no pre-existing drift at all. Always normalise line endings before
  concluding anything from a diff against `bin/Custom/AddOns/`.
- **Never put a backup directory inside `bin/Custom/`.** NT8 compiles that tree recursively, so
  a folder of `.cs` backups produces duplicate-type errors. Caught before compiling; backups now
  live in `Documents/NinjaTrader 8/_riskguard_backups/`.

**What shadow could not prove.** The data connection is **Kinetick – End Of Day (Free)**: daily
bars arrive (today's forming bar included) but every real-time quote is `0`, and the NT8
simulator needs Level 1 to fill. A test market order on `Sim101` sat at `Submitted` and was
ultimately **Rejected** without filling. RiskGuard did observe it — `ORDER_UPDATE` events for
`Submitted` → `CancelPending` → `Rejected` — so event monitoring is live on the new build, but
**no position was ever opened, so not one guard path executed.** The §4e acceptance criteria
(`PEAK_GIVEBACK_BREACH` on a profitable flat account; a wrong `COPY_BLOCKED_NO_GUARD`) remain
**unverified**. They need a session on a real-time feed. Do not read "deployed and green" as
"validated".

**Restart churn is expected, and it is not a fault.** The addon cycled `SHUTDOWN`/`INITIALIZE`
roughly every 10 s for about four minutes (24 lifecycle events) and then went quiet. It was
`nt_compile` and `nt_script_execute` recompiling NinjaScript — each recompile reloads every
AddOn. It settled by itself and the heartbeat has been steady since. Pre-deploy the addon
initialised 3 times in 3 days, so if you see this cadence *without* having compiled, that is a
real problem.

That churn is what exposed **P1-37** — see the plan. `nt_script_execute` is also unreliable here
(one `NT8 timeout`, one `ECONNRESET`); don't count on it for runtime probing. The bridge's
`GET /api/riskguard/config` is the dependable way to read live in-memory state, using the token
at `Documents/NinjaTrader 8/mcp_token.txt`.

**How to tell the new code is actually loaded**, given `Version` is still `1.1.0` and so proves
nothing: look for `MaxAutoStopAttempts` in the live config response. That field arrived with T2
and does not exist at the merge-base.

---

## 4g. Validation record — 2026-08-07, armed + shadow, real-time feed

The first session in which **any guard path has ever executed**. Feed: TPT (real-time; Kinetick
EOD was disconnected at 12:56 UTC). Mode `shadow`, `isArmed: true` from 13:21:30 UTC after
`PREFLIGHT: passed`. `TAKEPROFITPRO524207503` (the only funded account, $50k) was added to
`ExcludedAccounts` first and confirmed live in memory before arming.

**Setup.** Test account `SimCopyTest1` — Simulator provider, and deliberately not a leader or
follower in either copier relationship (both are `Sim101 → {Sim-ORB, SimCopy2}`), so the copy path
could not confound the result. One MNQ, no attached stop.

| Time (UTC) | Event |
|---|---|
| 13:24:06.036 | entry filled @ 29721.75, Long 1 |
| 13:24:06.396 | `FSM_TRANSITION` — FSM created → `Unprotected`, grace deadline 13:24:09 |
| 13:24:08.78 | `SHADOW_ACTION` FlattenPosition ← **`PEAK_GIVEBACK_BREACH`** (position at −$1.00) |
| 13:24:09.41 | `SHADOW_ACTION` FlattenPosition ← `MISSING_STOP_FLATTEN` (grace expired, no stop) |
| 13:24:10.79 … :40.08 | `PEAK_GIVEBACK_BREACH` ×5 more |
| 13:24:42.22 | exit filled @ 29726.00 |
| 13:24:42.428 | `FSM_TRANSITION` — FSM torn down → `Flat`; realized **+$8.50** |

**What passed.**
- **T3 acceptance criterion — MET.** The account finished **flat and profitable** (+$8.50) and
  emitted **zero** `PEAK_GIVEBACK_BREACH` after `13:24:42.428`. Pre-fix, a peak that included
  realized PnL against a zero unrealized read as a 100% giveback and fired on exactly this state.
- **FSM lifecycle works live**: creation on fill, grace deadline set from
  `StopAttachSeconds`, clean teardown to `Flat` on exit, `nt_riskguard_state` reporting it
  throughout.
- **`MISSING_STOP_FLATTEN` fired correctly**, once, at the grace deadline, on a genuinely
  unprotected position — T1/T2's path behaving as designed.
- **Shadow containment holds.** All seven actions logged `[SHADOW] Would execute …` and the
  position stayed open until *I* closed it. `:2895` (`isLive = _mode == "live"`) is doing its job.

**What failed — `P1-40`, now CLOSED the same session.** `PEAK_GIVEBACK_BREACH` fired **six times
in 36 seconds** on a position whose entire excursion was a few dollars, the first time 2.4 s after
entry with the position *down* $1.00. The rule was proportional-only with no floor on the peak, so
a one-tick peak ($0.50 on MNQ) made any retrace a ≥100% giveback. In an acting mode it would have
flattened nearly every trade seconds after entry and realised the loss doing it. Fixed test-first
with `MinPeakGainDollars` (default 50) and redeployed; see the plan's P1-40.

**T5 was not testable and could not have been.** `IsGuardProtecting` (`:875`) requires
`mode == "live"`, so in shadow it is false for every account. Both copier followers are Simulator
accounts anyway, which skips the `COPY_BLOCKED_NO_GUARD` gate entirely. That criterion needs an
acting mode.

**Net**: half validated. T3 is proven on a live feed and the one blocker the session found is
closed. T5 still requires an acting mode and has never been exercised.

**State left behind.** `TAKEPROFITPRO524207503` has been removed from `ExcludedAccounts` and is
covered again. Live config: mode `shadow`, **6** `WindowsET` entries matching disk exactly now
that P1-39 is closed. The addon was **re-armed at 13:55:55 UTC** after both fixes landed
(`PREFLIGHT: passed` → `isArmed: true`) and is collecting shadow data against live trading. Note
that any recompile reloads the addon and disarms it again — `_isArmed` is deliberately never
rehydrated (P1-37), so check the log before assuming the guard is watching.

**What that session will and will not cover.** Stop-guard and PnL/giveback paths: covered. **Firm
mirror: not covered at all** — `P1-42`, found while scoping this session. `ComputeFirmMirror`
reads only the top-level `TrailingDD`/`DailyLoss`, both `Enabled: false` here, and never consults
`AccountFirmMap`/`FirmProfiles`. The four researched firm profiles, including the real TPT $1,500
EOD trailing drawdown, are dead config. Mapping the account would not change it. Do not read a
clean firm-mirror log as evidence of firm-mirror protection.

**Worth watching in the log**: `StopGuard.OnMissing = "Flatten"` with `StopAttachSeconds = 3`.
ATM entries attach their stop in ~0.35 s and are fine; a manual entry that takes longer than 3 s
to get a stop will log a would-be flatten. Learn whether 3 s matches real trading habits before
that ever becomes an acting rule.

---

## 4h. Session 6 record — 2026-08-07

Twelve defects closed in one session, on a live feed with the guard armed in shadow throughout.
Suite 427 → **481**, closed 24 → **30 of 47** (five of the new ones were *opened* this session).

| Closed | What it was |
|---|---|
| `P1-40` | Giveback rule was proportional-only; a one-tick peak made any retrace a ≥100% breach. Fired **6× in 36 s** live, first at 2.4 s after entry with the position *down* $1.00 |
| `P1-39` | Json.NET appended the default `WindowsET` on every load; a default window could never be deleted, so the window gate silently widened |
| `P1-16` | One trade exited in three partials counted as three consecutive losses |
| `P1-17` | Cumulative $3,000 evaluation target was fed session-scoped PnL, so it only fired if cleared in a single day |
| `P1-18` | Two trailing-drawdown implementations with undefined precedence |
| `P1-19` | A flatten scoped to MES closed MNQ too; one evaluation pass issued five account-wide flattens |
| `P1-42` | `AccountFirmMap`/`FirmProfiles` were read by no evaluation path — the funded account had no firm protection, and mapping it would not have changed that |
| `P1-43` | Four `account.Cancel` calls under `_stateLock` on the order-update path |
| `P1-44` | Flood cancel had no reducing-order guard and could cancel a protective stop |
| `P1-45` | Flood lockout set no `LockoutUntil`, so it never lapsed, and it was persisted |
| `P2-46` | Flood detector counted `Submitted` and `Accepted` as two orders — the nominal 5/sec limit fired near 3/sec |
| `P1-47` | Guard defaulted to disarmed, so every recompile silently removed all protection |
| `P1-23` | Symbol translation was case-sensitive and used a global `Replace`; two sizing modes silently degraded to 1:1 |

### How they were found — worth repeating

**The operator's order-flood stress test produced four of them in an afternoon** (`P1-43`–`P2-46`)
by reading `interventions.jsonl` back. A green suite and months of review had not. That is why
`S1`–`S9` now exist as a standing programme (plan §8) rather than an ad-hoc exercise.

**Reading the live log answered a real trading complaint.** The operator reported being locked out
after a single losing trade. The archive showed `CONSECUTIVE_LOSS_BREACH` flattens on **funded**
accounts (`TAKEPROFIT273495429` 66, `TAKEPROFIT619225465` 27, `TAKEPROFIT648470602` 18). Cause:
scale out at profit, runner comes back to the stop → the last realized delta is negative → the
whole trade recorded as a **loss despite netting a profit**. Three such trades hit
`MaxConsecutiveLosses`. `P1-16` fixes it — the trade is now judged on its net.
*(The runner itself was ordinary price action, not the guard. Only one `MISSING_STOP_FLATTEN` ever
touched a funded account.)*

### Two mistakes made and caught, recorded so they are not repeated

**The first draft of S1–S4 was vacuous.** Passing `null` as `sender` made `ExecuteOrderUpdate`
throw on `(Account)sender` inside its own `try/catch`, so every call was swallowed and **three
assertions passed against code that never ran** — including the lock-scope one. Only the
assertions expecting a *positive* effect failed and gave it away. Once fixed, the same test found
8 violations. **A stress test that drives nothing reports safety.**

**A `dotnet run --no-build` after a failed build reports the previous assembly.** This produced a
false green twice. Read `RESULTS:` only from a build that compiled.

### State left on the box

Deployed and compiling clean. `shadow`, **armed** (self-armed since `P1-47`).
`TAKEPROFITPRO524207503` is covered — it was excluded during T3 validation and restored
afterwards. `config.json` is clean at 6 windows and the live config now matches it exactly.
All accounts flat.


---

## 4i. Session 7 record — 2026-08-07: P1-21, and the defect it uncovered

**`P1-21` closed. Suite 481 → 486. NT8 compiles clean, guard self-armed through the reload.**

The ticket itself was small. What it found was not.

### The structural obstacle, and what was done about it

`P1-21` lives in `McpBridgeAddOn.cs`, which **`RiskGuardTests.csproj` excludes from the test
build**. So does `P2-38`. Under the test-first rule that is a dead end: no acceptance test can
reach the code.

The subscription bookkeeping was therefore moved to `TradeCopierEngine`, which *is* in the test
build — `RefreshAccountSubscriptions()`, `UnsubscribeAllAccounts()`, `SubscribedAccountCount`.
`McpBridgeAddOn` keeps only the four-line `Connection.ConnectionStatusUpdate` wiring. **When a
defect sits in an untestable file, moving the logic to a testable one is usually cheaper than
arguing about coverage** — and here it was also the better design, since the copier should own its
own subscriptions.

`verify_backfill_reverts.py` now reverts across multiple files (it was hardcoded to
`RiskGuardAddOn.cs`). All **9/9** cases falsifiable, including the three new ones — each observed
failing for the intended reason: 0 copies, 5 handlers, 1 surviving handler.

### P0-48 — 57 orphaned handlers, found by looking rather than by testing

The teardown half was written as defensive housekeeping. Checking whether it actually worked meant
reading the live event list through `POST /api/dev/reflect`, which returned **67 handlers on
`Sim101.ExecutionUpdate`** — **57 of them orphaned `McpBridgeAddOn` instances**, one per historical
AddOn reload, each with its own assembly's `TradeCopierEngine` singleton and its own dedupe set.

`RiskGuardAddOn` sat at exactly 1, because it already unsubscribes at `State.Terminated`. That
control is what makes the reading conclusive rather than suggestive.

Full detail, measured table, and the honest limit of the claim (handlers measured, duplicate copies
inferred) are in the plan under `P0-48`. **It requires an NT8 restart**; see the banner at the top.

### P1-22 — measurement, and a defect caught by reading rather than testing

`LatencyMs` and `AvgSlippageTicks` were rendered in the copier UI and written by **nothing**, so it
reported a clean `0ms / 0.0t` however badly a copy filled. Both are now populated from the
follower's own fill, plus a `MaxSlippageTicks` ceiling. Full detail in the plan under `P1-22`.

The part worth remembering: **the pending-copy map was first keyed on `Order.OrderId`, and every
test passed.** `RiskGuardAddOn.cs:4481` already warns that NT8's `OrderId` is neither unique nor
stable across the historical→live transition — the addon tracks recognised stops by object
reference for exactly that reason. The suite could not see it because the test stub assigns one
stable GUID per order, so the stub was *more forgiving than production*. Found by grepping the
production call sites for the API before trusting it, not by a red test. It is now keyed by object
reference (`OrderReferenceComparer`, using `RuntimeHelpers.GetHashCode`), and
`TestCopierSlip_FillIsMatchedWhenOrderIdChanges` makes the stub behave like NT8.

Two design decisions that go against the plan's own `**Fix**:` note, both deliberate:

- **Quarantine is entry-only; a quarantined relationship still copies exits.** The note says
  simply "quarantines the relationship when exceeded". Implemented literally, `IsQuarantined`
  blocks *every* copy — including the one that closes the follower out — stranding it in a
  position the leader has already left. That is `P0-5` reached by another route. Fourth time an
  older `**Fix**:` note would have made things worse if followed as written.
- **Limit-with-offset entries are not implemented.** The note lists it as "consider". It turns a
  guaranteed fill into a maybe-fill, and an unfilled entry diverges the follower's size from the
  leader's with nothing to reconcile it — `P0-9`/`P3-30` territory, not this ticket.

`verify_backfill_reverts.py` is at **14/14**. The price-comparability revert is the one to look
at: with the guard removed the ES↔MNQ case records **−52,000 ticks** and quarantines a healthy
relationship on its first copy.

### Three things worth carrying forward

1. **A green suite and a clean compile said nothing about this.** The defect is in *runtime object
   graph state accumulated across reloads* — a category no unit test in this repo can observe. The
   only thing that found it was inspecting the live process.
2. **`POST /api/dev/reflect` is the tool for that, and it works.** `{"result": N}` chains handles
   between ops; integer args need `{"type":"System.Int32","value":N}` or they arrive as Int64 and
   the invoke fails. A handler census is a two-minute read-only query — **add it to the deployment
   runbook**, since nothing else detects this class of bug.
3. **"It compiles and the tests pass" was true and irrelevant.** The same reload churn §4f
   describes as benign — "it settled by itself" — was silently accruing these handlers the whole
   time. That churn was written off twice in this document before anyone counted.

---

## 4j. Session 7, second half — P0-9, S7, and the loop's review mode

Eight commits. `P1-21` → `P1-22` → `P0-48` verified → `P0-9` → review mode. The through-line worth
carrying: **three separate defects this session were found by asking a question, not by a gate.**

| Commit | What |
|---|---|
| `4b724fbe` | `P1-21` closed; opened `P0-48` (57 leaked handlers) |
| `6e6d9905` | `P1-22` closed — latency/slippage measured, `MaxSlippageTicks` ceiling |
| `d399c976` | Shadow-counter reset, and corrected a destructive command in this file |
| `922b2c44` | `P0-48` closed and **verified live** |
| `76137575` | `P0-9`'s naked-follower half + stress test `S7` |
| `290ce6d1` | Signed-offset fix — a trailed stop was being inverted |
| `1d9566fe` | Loop `review` mode + the two defects it found |

### P0-9 — what shipped, and what did not

Followers are no longer naked. The copier subscribes to `OrderUpdate`, recognises the leader's
protective stop, and mirrors it **by signed offset anchored to the follower's own fill**:

```
followerStop = followerEntry + (leaderStopPrice - leaderPositionAvgPrice)
```

Copying the leader's stop *price* would be wrong by exactly the slippage `P1-22` measures, and
wrong by a whole price scale across a micro/mini conversion.

**Still open under `P0-9`** — read the plan before assuming it is done: profit targets and OCO,
`StopLimit` limit offsets (assessed as safe: `StopMarket` is *more* likely to fill, so the
divergence runs toward the follower being protected), and a leader that cancels its stop while
staying in position. `EnableFollowerAtm`/`FollowerAtmStrategyName` were **deleted**, not
implemented — they were unreachable config that could not be set by any means while implying
followers got a bracket.

> **A copier-side default bracket was deliberately not built.** RiskGuard's auto-stop already owns
> "position with no stop". Two independent stop sources on one position over-cover and flip it when
> both fire — the same hazard the cancel-then-replace rule prevents *within* the copier, but across
> two components that cannot see each other.

### The three defects that gates did not find

**1. The signed-offset inversion (`290ce6d1`).** `Math.Abs` discarded the sign, so a leader
trailing its stop into profit — stop above entry on a long, the most ordinary trade management
there is — mirrored onto the *losing* side of the follower's entry, converting a locked-in gain
into open risk of equal size. It survived a green 515-test suite, a clean net48 compile and a
20/20 falsifiability check. **The trail test moved the stop 17990 → 17995 → 17998, all below
entry, so it could never have caught it.** Found because the operator asked whether the
`StopLimit` conversion could trigger wrong orders; answering honestly meant re-deriving what price
the follower's stop lands on.

**2 and 3. Naked-on-failure (`1d9566fe`), found by review mode.** A stop whose `Submit` threw, or
which the broker rejected moments later, left `WorkingStop` null with a valid offset and **nothing
re-triggered submission** — naked for the life of the position. And the `OrderUpdate` reporting
that rejection **was being received and discarded**, because the handler returned early for any
account with no relationships, which every follower is.

### Loop `review` mode — built, and it earned its keep immediately

`--mode review --review-base <ref>` puts a committed diff in front of the panel and arbiter. No
implementer, no regions, no worktree, no apply path. Full design and properties lived in `AGENT_PATCH_LOOP.md` §11-12, which **is not in this repo** —
it documented the archived predecessor loop and stayed in tvDownloadOHLC
(`docs/architecture/AGENT_PATCH_LOOP.md`, marked ARCHIVED). For the current package see the
[agent-loop repo](https://github.com/vinay-veerappa/agent-loop).

It exists because **`patch` mode's guarantee does not hold for hand-written work.** Gate 0 makes
`*Tests.cs` unreachable to the implementer precisely so the grader is independent. When one author
writes the change *and* its tests, the tests encode the cases that author already thought of, and
the suite goes green for the same reason the bug got written.

First run, on the `P0-9` diff: **24 findings, 3 upheld, 8 rejected, 13 out of scope.** Two upheld
were real (above). **The third was wrong and the arbiter upheld it anyway** — it claimed a 10-point
ES stop becomes "10 follower-points" on MES, but every pair in the matrix trades at the same price
with the same tick size and only the dollar multiplier differs, which quantity scaling handles.
**Read the rulings** — the arbiter is not a rubber stamp, but it is not sufficient either (§3.4).

> **Fixing an upheld finding introduced the defect a REJECTED finding described.** Re-submission
> creates exactly the reject→resubmit flood finding #13 warned of and the arbiter dismissed *on
> the grounds that no such loop existed* — true before the fix, false after it.
> `MaxBracketStopAttempts` bounds it. The first bound was itself wrong: it reset the counter on
> `Submit` success, but the failure mode is rejection *after* a successful submit, so the bound was
> unreachable. The test caught it at 21 submissions.

### Two operational facts recorded elsewhere but easy to lose

- **`ShadowSessionsCompleted` was reset** (5 → 0) and has since counted **1** genuine session and
  **held at 1 across a recompile** — `P1-37`'s debounce proven from a clean baseline. The live
  arming gate is trustworthy on this box for the first time. Backup:
  `RiskGuard/state.json.bak_20260807_095249`.
- **`P0-48` is closed and verified**: 67 handlers → 8 after restart, and `TradeCopierEngine` held
  at exactly **1** across a further recompile — the event that used to add an orphan every time.

### Method notes worth repeating

- **"NT8 closed" means "the AddOn is not loaded"**, which is not the same as "the process is gone".
  The reliable check is the bridge not answering on `localhost:7890`.
- **Deploy unverified addon code mid-session, never at startup.** A failed `nt_compile` hot-swap
  leaves the running assembly in place and is recoverable; broken sources in `bin/Custom/AddOns/`
  only bite at the next startup, where they stop **every** AddOn loading, RiskGuard included.
- **The test stub can be more forgiving than NT8, and the suite cannot tell you.** `P1-22`'s
  pending-copy map was keyed on `Order.OrderId` and every test passed; NT8's `OrderId` is neither
  unique nor stable. Check how the existing addon uses an API, and why, before relying on it.

---

## 4k. Session 8 record — 2026-08-07: the P1 band closes

Seven commits. `P0-9` items 3/4 → `P1-12` → `P1-14` → `P1-36` → `P1-13` (half) → `S5`–`S9` →
`P2-38`/`P2-41`. Suite 524 → **616**, all green, NT8 `nt_compile` 0 errors, all 9 files in sync.

| Commit | What |
|---|---|
| `c2f54e9b` | `P0-9` items (3) `StopLimit` and (4) leader-cancels-stop, pinned by test |
| `12e0ca12` | `P1-12` — the disk comes off `_stateLock` |
| `35052e86` | `P1-14` — the pending-stop buffer: one order, forever, unchecked |
| `c6c4e02b` | `P1-36` — coverage is the sum of the stops, not one of them |
| `830cfa55` | `P1-13` fail-open half — the guard stopped guarding when the UI was absent |
| `0e21ad3c` | `S5`, `S6`, `S8`, `S9` — the stress backlog closes |
| `6077de0a` | `P2-41` config merge, `P2-38` sim/live gates |

### The through-line: three defects were found by making something a compile error, or by a test

**1. `P1-36` lived in a second place.** Making `CoveredQuantity`/`RecognizedStopOrder` read-only
turned "find every writer" into a compile error, which surfaced nine sites — and the ninth was
`ExecuteAction` re-sizing the auto-stop from the **whole live position**, ignoring existing cover.
`EvaluateGraceExpiry` had always sized its *action* to the uncovered delta; `ExecuteAction` sized
it straight back up. Closing only the FSM half would have left the 9-lots-behind-6 outcome exactly
as it was. **A fix verified only where the defect was reported is a fix that may not have landed.**

**2. `P1-13`'s machine check found a site I had already missed** on my own pass through the file.

**3. `S6`'s first draft was unfalsifiable and looked fine.** It cancelled each stop before flipping
— tidy, realistic-looking, and completely inert: a terminal order cannot contribute coverage to
anything, so the revert probe found nothing and the test reported safety. It now leaves the
previous leg's stop **working** as the flip lands, which is the real shape. This is the second time
a stress test in this programme has been vacuous on the first attempt (see §8 of the plan). **Every
stress test here must be shown red against the defect it names before it is worth anything.**

### `P2-41` was verified live, by accident, one minute after deploying

`nt_riskguard_config` with no arguments POSTs an **empty body**. Under the old code that single
call — the one you would reach for to *read* the config — would have deserialized `{}` into a
complete `RiskConfig` and written it: `Mode` → shadow, `MinShadowSessions` → 0, `EnableWindowGate`
→ false, all six `WindowsET` gone, all four `FirmProfiles` gone, `StopGuard.OnMissing` → `Flatten`.
It would have replied `"applied"` and echoed the request.

The post-fix call returned `"requested": {}` next to the complete, unchanged live config. **The
tool most likely to be reached for as a read was itself a destructive write, and the workaround
recorded in §0 item 4 — GET, mutate, POST, GET, diff — was the only thing standing between this
box and a wiped risk configuration.**

### Two things deliberately NOT done, with reasons

**`P0-9` item (1): profit targets and OCO.** This is the last piece of `P0-9` and it wants an
operator decision rather than a unilateral one. The case against building it: a mirrored target is
*upside*, not risk — the follower already exits when the leader's target fill is copied, so the gap
is fill quality, not exposure. Building it doubles the copier's order-placement surface on a
component whose **first** half has never been observed on a live fill. The case for: it is option 1
of the plan's own preferred fix, and the latency gap is real in a fast market. If it is built, it
must use a real broker-side OCO id — a mirrored target without OCO leaves the stop working after
the target fills, which flips the follower into a fresh position. **Recommendation: validate the
mirrored stop on a live feed first, then decide.**

**`P1-13`'s threading inversion.** The evidence says it is safe — the copier has been submitting
real follower orders straight off NT8's account-event thread, with no marshalling, in production.
But it converts six handlers the dispatcher was implicitly serialising into genuinely concurrent
ones, and **the S-series does not cover that**: `S4` is lock-scope, `S7` is copier fan-out, and
`S5`/`S6`/`S8`/`S9` are sequential scenario tests. I said mid-session that the stress backlog would
be the prerequisite; having written it, it is not. A genuine concurrent-guard-event stress test is.
Doing the risky half before its coverage exists is how `P1-40` shipped.

### Method notes

- **`McpBridgeAddOn.cs` is excluded from the test build**, so the `P2-38`/`P2-41` changes were
  unverifiable until `nt_compile`. That is the `P1-47` shape and it is structural, not incidental.
  The mitigation used here: put the *logic* somewhere compiled (`RiskConfigMerge` lives in
  `RiskGuardAddOn.cs`) and check the bridge's own wiring against **source text**. A source
  assertion proves less than an execution; it proves the exact thing that regressed.
- **A machine check on source text needs its comments stripped**, or it forbids documenting the bug
  it prevents — and then the comment gets deleted instead of the check getting fixed.
- **The TTL in `P1-14` is two grace periods, not one.** One grace period is the longest a
  legitimate stop can lag its position event and still be the thing protecting it. The test asserts
  both edges, because an over-eager TTL breaks the race the buffer exists for.

---

## 4l. Session 8, second half — the live ATM trade that found two P0s

The operator placed an ATM order on `Sim101` with `Sim-ORB` following, and reported that the
follower "did not follow". It had followed — the entry copy was correct. What had not happened
was the protective stop, and chasing that produced **`P0-49` and `P0-50`**, both P0, neither
reachable by any test in the suite.

| | |
|---|---|
| 15:43:21.232 | `COPIER_FOLLOW` Buy 1 MNQ SEP26 filled 29789.25 on Sim-ORB — **the copy worked** |
| 15:43:21.237 | `Created FSM Sim-ORB\|MNQ SEP26 -> Unprotected` |
| 15:43:24.241 | `[SHADOW] Would execute FlattenPosition triggered by MISSING_STOP_FLATTEN` |
| 15:45:22.572 | `COPIER_STOP` submitted — **~2 minutes late, as the position was closing** |
| 15:45:30, :31 | two more `COPIER_STOP` orders, against a **flat** account |

**The follower was naked for the entire trade**, then collected three orphan stops.

### The NT8 fact underneath it

**`ExecutionUpdate` is raised BEFORE `PositionUpdate`.** The bracket anchored itself by re-reading
`followerAcc.Positions` from the execution handler, so on every entry fill it read a position that
did not exist yet, released the bracket, and returned. Nothing rebuilt it, because an ATM stop
sits at `Accepted` and raises no further `OrderUpdate` — so the leader path never fired again
either. One event-ordering assumption, and the whole of `P0-9` silently did nothing.

This is the same class as the `P1-22` lesson in §4j: **the test stub is more forgiving than NT8,
and the suite cannot tell you.** The stub raises whatever the test raises, in whatever order the
test chooses, and every bracket test drove position-then-execution because that is the order a
person writes it in.

### The second trade — validated, 15:55:56

`P0-49`/`P0-50` were deployed and a second ATM trade run immediately:

| | |
|---|---|
| 15:55:56.9857 | Sim-ORB `COPIER_FOLLOW` **Filled** |
| 15:55:56.9988 | Sim-ORB execution, price **29822.25** |
| 15:55:56.9998 | Sim-ORB `COPIER_STOP` **@ 29807.25 — one millisecond later** |
| 15:55:57.0058 | `Created FSM Sim-ORB\|MNQ SEP26 -> ProtectedPending` |

Leader entry 29821.75, leader `Stop1` 29806.75, offset **-15.00**; follower 29822.25 - 15 =
**29807.25**. Exact. And the follower's FSM is created **`ProtectedPending`** rather than
`Unprotected`, so no `MISSING_STOP_FLATTEN` fires at all — compare the first trade, where the FSM
was born naked and the guard would have flattened it three seconds later.

**`P0-9`'s mirrored stop is now validated end to end on real fills: arithmetic, timing, and
resulting FSM state.** That was the longest-standing open item in this document, carried since
session 7.

Worth noting for the next reader: the stop went out at `.9998`, *before* the follower's
`PositionUpdate` event at `1.0058`. NT8's `Account.Positions` collection had already been updated
even though the event had not yet been raised, so the execution path found the anchor and placed
the stop. The `PositionUpdate` subscription added by `P0-49` is the **safety net** for the case
where the collection is not yet updated — which is exactly what happened on the first trade. Both
paths are needed; neither alone is sufficient.

### What is still NOT validated live

- **Profit targets are not mirrored** — the operator noticed within one trade. Sim101 carried
  `Target1` (Limit Sell 29851.5); Sim-ORB got only `COPIER_STOP`. Deliberate, and the last open
  item of `P0-9`. See §4a.
- **`T5`'s fail-closed gate** still needs an acting mode; `IsGuardProtecting` requires
  `mode == "live"`.
- **Firm-mirror rules** are loaded but unmapped, so none of them fire.

### A note on what "it didn't follow" meant

The reported symptom pointed at the wrong relationship. The `SUB_MINIMUM_SKIPPED` line in the
output was **SimCopy2**, not Sim-ORB, and it was **correct behaviour**: SimCopy2 has
`AutoSymbolConversion` on, so MNQ→NQ is micro→mini, 1 MNQ scales to 0.1 NQ, and the copier refuses
rather than rounding up to a 10× notional. That is `P0-6` working as designed. Reading the whole
log rather than the one alarming line is what separated the two.

---

## 4m. Session 9 — 2026-08-09: the guard flattened three accounts while claiming to be in shadow

Another live operator ATM trade, another two defects, and this time one of them undermines the
premise the whole deployment rests on. **No code was changed this session** — the incident was
diagnosed from the live event stream and the source; `P0-51` and `P1-52` are open.

### The four seconds

| Time (ET) | What |
|---|---|
| `21:15:21.9` | Operator enters 2 MNQ SEP26 on `Sim101` with an ATM bracket. Replikanto mirrors the full bracket to `SimCopyTest1` and `SimCopy2`; our copier mirrors entry + `COPIER_STOP` to `Sim-ORB` |
| `21:15:22.0` | `ORDER FLOOD DETECTED: 6 distinct orders in 1s (limit 5)` on **all three** bracket-carrying accounts |
| `21:15:25.0` | `LOCKOUT_PHASE PendingFlatten` + `[SHADOW] Would execute action FlattenPosition triggered by LOCKOUT_FLATTEN` on each |
| `21:15:25.15` | Market `Sell` 2 named **`"Close"`** on each of `Sim101` (`34256`), `SimCopyTest1` (`34257`), `SimCopy2` (`34258`) — all fill at 29848.75 |
| `21:15:25.4` | All three flat, `LOCKOUT_CONFIRMED`. **`Sim-ORB` still long 2** |

### `P0-51` — how the shadow gate was bypassed

Two paths leave a lockout and only one is gated:

- `EvaluateLockoutPhase` (`:2718`) → `GuardAction` → `ProcessAction`'s mode check (`:3277-3285`)
  → `SHADOW (SKIPPED)`. **Correct.**
- The lockout watchdog sweep (`:1848-1889`) builds `cancelBatches` / `flattenBatches` with no
  `_mode` check, then executes them at `:1899-1940` — `Cancel` at `:1901`, `Flatten` at `:1913`.
  **Ungated.**

`Account.Flatten()` cancels the instrument's working orders and submits a market close named
`"Close"`, which is exactly what appeared. The `[SHADOW]` line and the real flatten are the same
lockout, taking two different routes.

> **Attribution was checked, not assumed.** A manual "flatten everything" would also have closed
> `Sim-ORB`, which was long 2 on the same instrument at the same instant. `Sim-ORB` was the only
> account that had not tripped the lockout and the only one left untouched — the flatten tracked
> lockout state, not the operator.

**This is the third instance of §0 lesson 2.** The suite tests `ProcessAction`'s gate, and that
gate is correct. Nothing asserts the negative — *no broker call is issued by any path while in
shadow*. `S4`'s `BrokerCallObserver` already exists to assert exactly that and was never pointed
at this question.

### ⚠️ FOUR tests asserted shadow-mode broker actions. Expect more

`_mode` defaults to `"shadow"` (`RiskGuardAddOn.cs:212`, deliberately, as the fail-safe). A test
that never calls `SetModeForTest` therefore runs in shadow — and four of them asserted that the
guard **cancels or flattens** in that state:

| Test | Asserted |
|---|---|
| `TestP1_10_SweepMakesNoBrokerCallsUnderTheStateLock` | the sweep flattens |
| `TestP1_11_LockoutSweepDoesNotCancelTheProtectiveStopBeforeFlattening` | the sweep flattens and cancels |
| `TestOrderCancelledWhenLockedOnOrderUpdate` | a working order is cancelled |
| `TestOrderCancelledWhenConsecLossesAtMaxNotLocked` | a submitted order is cancelled |

All four were green, and all four were green **because of the defect**. Each has been given an
explicit `SetModeForTest("live")`, which is what they always meant — every one of them is about
*acting* behaviour. Baseline is unchanged by the correction (622/8), because the code acts in
every mode today.

**Two consequences worth carrying forward.** First, this is why `P0-51` survived: the suite did
not merely fail to catch it, it *asserted* it, so any fix looked like a regression — the loop
burned two full runs on exactly that (§4m's loop notes). Second, **`P0-53` was found only because
one of these tests was made honest.** If you touch a test that drives the sweep or an intervention
path, check whether it states a mode before you trust what it proves.

### `P1-52` — why the lockout fired at all

A 2-contract ATM entry is 6 orders (2 entries, 2 stops, 2 targets) against `MaxOrdersPerSecond = 5`.
**Every 2-lot bracketed trade trips it**, and third-party copier fan-out means it trips on every
mirrored account in the same second. Third defect on this governor after `P1-44`, `P1-45`, `P2-46`.

### The leftover, and the one thing still unexplained

`Sim-ORB` was left long 2 @ 29849.75 with `COPIER_STOP` working at 29835 — **protected, but
diverged from a leader that had been flat for hours**. It was flattened by the operator's
instruction at 2026-08-09 ~21:2x ET via `nt_close_position`; that call cancels orders itself, so
**it did not independently exercise `P0-50`'s orphan-stop release** and must not be recorded as a
re-validation of it.

**Open question — do not assume the answer.** Why the copier never mirrored `Sim101`'s exit to
`Sim-ORB` is *not established*. The exit path (`TradeCopierEngine.cs:1621-1748`) looks like it
should have fired: quarantine permits exits, `Sim-ORB` is a Sim follower so `COPY_BLOCKED_NO_GUARD`
does not apply, and `currentFollowerPos` was 2. It could not be settled from the logs because
**the copier's `[CopierEngine]` lines go to the NT8 Output tab and land in no readable sink** —
they are absent from the bridge's event stream, from `log/`, and from `trace/`. Giving those
lines a file sink is a prerequisite for diagnosing anything in the copier and should come before
the next copier change.

---

## 4n. 2026-08-10 — the incident replayed live, with instrumentation

Ran the 2026-08-09 incident again on purpose: same 2-lot MNQ ATM entry on `Sim101`, same Replikanto
fan-out, same `shadow` mode. **`P0-51` and `P1-52` are now validated on a live feed.**

### What the replay proved

| Fix | Evidence |
|---|---|
| **`P1-52`** | **No `ORDER_FLOOD_LOCKOUT` on any account.** The identical bracket that locked out three accounts on 2026-08-09 produced none |
| **`P0-51`** (sweep) | `LOCKOUT_SWEEP_SHADOW`: *"[SHADOW] Would execute lockout sweep for account SimCopyTest1: flatten [MNQ SEP26], cancel 2 order(s)."* — **and nothing was flattened.** `SimCopyTest1`/`SimCopy2` were still locked out from the incident and kept both position and orders |
| **`P0-51`** (queue) | `SHADOW_PENDING_CANCEL`: *"[SHADOW] Withheld 1 intervention cancel(s) in shadow mode."* The `ENTRY_CANCEL` lines still say "Cancelled order X because account is locked out" — **but the orders stayed `Working`.** That log line describes the decision, not the outcome; the outcome is the withheld line |
| **Exit mirroring** | Works. `COPIER_COPY_BEGIN: 2 active relationship(s), isExit=True: Sim-ORB, SimCopy2` → `COPIER_FOLLOW Sell 2` on `Sim-ORB`, filled |

**The 2026-08-09 exit-mirror failure is still unexplained**, but it is no longer *unexplainable*:
the normal exit path demonstrably works, and every abandon point now names itself. If it recurs the
log will say which one it was.

### The instrumentation

`RiskGuardAddOn.LogFromComponent` lets a sibling component write into the guard's structured log, so
copier lines now reach `interventions.jsonl` and the bridge event stream instead of dying in the NT8
Output tab. `TradeCopierEngine.CopierLog` is the dual sink. **Every early return in `OnExecution`
was silent** — seven of them — and each now emits a reason: `COPIER_EXEC_SEEN`, `EXEC_IGNORED`,
`EXEC_IS_FOLLOWER`, `EXEC_SELF_ORIGINATED`, `EXEC_DUPLICATE`, `NO_ACTIVE_RELATIONSHIPS`,
`COPY_BEGIN`.

**The bracket path is no longer dark.** `BRACKET_NO_LEADER_POSITION` and `BRACKET_REANCHOR` were
added while closing `P0-55`, and they are what turned "the follower is naked and nobody knows why"
into a two-line trace. `SyncFollowerStop`'s own internals remain uninstrumented — worth doing before
the next copier change.

### Two defects the replay opened

- **`P0-55`** ✅ **CLOSED same day.** `Sim-ORB` got no `COPIER_STOP` at all and ran the whole trade
  `Unprotected`. The cause was **not** the FSM rejection it appeared to be: the leader's stop
  reached `Accepted` at `.4203` and the leader's position only existed at `.4683`, so
  `OnLeaderOrderUpdate` had nothing to anchor to — and an accepted ATM stop is event-silent
  afterwards, while the leader's own `PositionUpdate` was discarded because the account is not a
  follower. **The leader-side twin of `P0-49`**, whose docstring describes the identical race on the
  follower's anchor. Fixed by re-driving the mirror from the leader's `PositionUpdate`.
- **`P1-54`** ✅ **CLOSED same day.** `Sim101`, `SimCopy2` and `SimCopyTest1` were *still locked out
  ~3 hours later* and blocked the replay. `IsLockedOut` was sticky, `LockoutUntil` was not
  persisted, and the test is an OR, so `LockoutMinutes` never ended a lockout. Fixed by lapsing on a
  passed deadline and persisting it — with `MinValue` still meaning "no deadline", since
  `LockAccount(name, -1)` uses it for an EOD hold.

### Two operational gotchas worth keeping

- **`nt_place_atm_order` caches by `idempotencyKey`.** Reusing a key replays the previous response —
  including a stale error. A blocked order that "stays blocked" after you fix the cause may just be
  the cache. Use a fresh key.
- **`UnlockAccount` also resets that account's metrics** (peak equity, trades today, consecutive
  losses, PnL basis). Fine on a Sim rig, not something to do casually on a funded account.

---

## 4o. 2026-08-10 — OCO research, and the trail fix it licensed

The operator rejected "we cannot propagate the OCO" as an answer. They were right to: **the
earlier claim in this document was wrong.** What follows is the corrected picture, the working
implementation, and the two things blocking it.

### The API facts, established by reflection and two live runs

Reflected on NT8's `NinjaTrader.Core.dll` (in the NinjaTrader 8 `bin` folder):

| Fact | Consequence |
|---|---|
| `Order.Oco` has a **public setter** | The old "create-time only, cannot be joined" claim is false |
| There is **no `OcoChanged`** field (only `LimitPriceChanged`, `StopPriceChanged`, `QuantityChanged`) | `Account.Change()` moves price/qty but **cannot** move a working order between groups |
| ~~**An OCO id cannot be REUSED** — NT8 rejects a new order carrying a used id~~ **CORRECTED 2026-08-10, see §4p** | The rule is about the GROUP'S LIFE, not the id's history: an id can be **joined** while its group still has a live member, and is only rejected once every leg has gone terminal. Re-creating one leg beside a live sibling may keep the same id |
| `Account.CancelOrdersByOcoID(orders, ocoId)` exists | A real group-cancel primitive; the copier currently hand-rolls this |
| `Connection.Features` returns `Feature[]` at runtime | Capability is answerable, not guessable |

**The id-reuse rule was found by the operator hitting the error, not by us.** It is the single
fact that most shapes the design, and nothing in the suite would have surfaced it. **It was also
stated too strongly, and §4p corrects it with a controlled test.**

### What this connection actually supports

Added a read-only probe, `GET /api/connections` (`McpBridgeAddOn.GetConnectionFeatures`). On this
box **one connection, `TPT`, serves both Sim101 and the funded TakeProfit accounts**, and it
advertises:

```
Bars1Minute, BarsDaily, BarsTick, BarsTickIntraday, Hotlists, MarketData, MarketDepth,
NativeGtdOrders, News, Order, OrderChange, ProvidesMarketDataSnapshot,
Quotes1Minute, QuotesDaily, QuotesTick
```

`NativeGtdOrders` is present, **`NativeOcoOrders` is not** — and since the `Native*Orders` family
is demonstrably in use, that absence is meaningful. **OCO here is NT8-simulated, not
broker-native.** It works (every ATM bracket on this box relies on it), but if NT8 dies between
one leg filling and the sibling being pulled, the survivor is live at the broker. That is the
exposure the operator's own manual brackets already carry — not a new one.

`OrderChange` being present is what licensed the trail fix below.

### Shipped: the trail no longer opens a naked window

`SyncFollowerStop` now **modifies** the working stop via `Account.Change()` instead of
cancel-then-create. Cancel-then-create left the follower unprotected on *every* trail step.

> This **revises a settled `P0-9` note** ("cancel-then-replace, not modify"). The note existed to
> stop a stale stop working beside a new one; `Change()` cannot produce that state because there
> is only ever one order. Verified, not assumed — `OrderChange` is advertised — and any failure
> falls through to the old path, logged `BRACKET_MODIFY_FAILED`.

Also: the test double's `Change()` was not calling `ObserveBrokerCall`, so it was **exempt from
the `P1-10` lock-scope check** — the same blind spot that hid `P1-43`'s four cancels. Now observed.

### ~~Parked: the mirrored target~~ — SHIPPED 2026-08-10, see §4r

> **Superseded.** The mirrored target was rebased off `wip/p09-oco-target` and shipped as
> `86c6376f`. **That branch is superseded and should be DELETED, not rebased** — it lacked five
> fixes, four of them live-risk (§4r). The live observations below still stand.

What the parked branch demonstrated live on `Sim101 -> Sim-ORB`:

- the leader's **limit** leg is recognised and mirrored, anchored to the **follower's own fill**;
- both legs carry one shared OCO id;
- both legs **modify in place** (`BRACKET_MODIFIED` / `BRACKET_TARGET_MODIFIED`);
- the `P0-55` re-anchor covers **both** legs (`re-evaluating 2 working protective leg(s)`).

Both of the things that stopped it shipping are resolved:

1. ~~**`P1-56`**~~ — closed 2026-08-10 (§4q).
2. ~~**The OCO-id-reuse rule.**~~ Corrected by controlled live test (§4p): an id can be joined while
   its group still has a live member, so the per-generation redesign shrank to one conditional on
   the cancel-then-create path. Shipped that way in §4r.

> **A mistake worth not repeating**: the first cut of the `P0-55` re-anchor filtered on
> `IsStopType`, so it silently left the *target* unanchored. The live trace said
> *"re-evaluating 1 working protective stop(s)"* on a two-legged bracket. A stop-shaped test
> cannot see an off-by-one-leg; the instrumentation caught it in one line.

### Replikanto is NOT being blocked by us

Asked and answered with evidence: during the clean run there were **zero events of any kind** on
`SimCopyTest1`/`SimCopy2`, and neither is locked out. If we had killed its orders you would see
`ORDER_UPDATE` -> `Cancelled`; no order ever existed. Since `P0-51`, RiskGuard in `shadow`
**withholds** interventions rather than executing them, so it cancels nothing.

Separately and correctly: **our own copier does skip `SimCopy2`** — it has `AutoSymbolConversion`
on, so 1 MNQ scales to 0.1 NQ and `P0-6` refuses rather than rounding to a 10x notional. Expected,
and unrelated.

### Operational gotchas found the hard way

- **`nt_place_atm_order` caches by `idempotencyKey`.** Reusing a key replays the previous
  response, *including a stale error*. An order that "stays blocked" after you fix the cause may
  just be the cache. Use a fresh key.
- **`UnlockAccount` also resets that account's metrics** — peak equity, trades today, consecutive
  losses, PnL basis. Fine on a Sim rig; think twice on a funded account.
- **`nt_close_position` cancels the orders itself**, so using it to clean up does **not**
  independently exercise the copier's orphan-stop release. Do not record it as validating `P0-50`.
- **Two overlapping leader brackets look exactly like a copier bug.** A manual bracket placed
  during a test produced multiple mirrored legs and a qty-4 order. The tell *was* the leader's order
  *names* (`Stop1`/`Target1` vs `Stop_<bracketId>`) — ⚠️ **but that diagnostic is BROKEN**: a
  third-party copier on this box copies leader names verbatim, so its mirrors are indistinguishable
  by name from a native bracket (§4p). Check order *count against position size* and the `oco`
  field instead.

---

## 4p. 2026-08-10 — the OCO id rule, pinned by a controlled live test

§4o's headline OCO fact was **too strong**, and it was the fact "that most shapes the design". It
is now pinned properly, by changing exactly one variable.

### The experiment

A 2-lot bracketed entry on `Sim_All_Day_ORB` (MNQ SEP26, 01:44 ET) via `/api/order/atm`: entry
filled 2 @ 29906.75, and `Stop_5c903ad3` (StopMarket 2 @ 29897.5) plus `Target_5c903ad3`
(Limit 2 @ 29921.75) went working, **both carrying one shared id `4980107b-…`**. Then the same
order — same id, account, side, quantity and price (Sell Limit 1 @ 30200, far from market so it
could not fill) — was submitted twice:

| # | State of the group `4980107b-…` | Result |
|---|---|---|
| 1 | stop + target still **working** | **`Working`** — accepted, it JOINED the group |
| 2 | group retired by `nt_close_position` (3 orders cancelled) | **`Rejected`** |

Nothing else differed between the two submissions. So:

> **An OCO id can be JOINED while its group still has a live member. It cannot be RESURRECTED once
> every leg has gone terminal.**

### Why this mattered, and what was built on it

The parked implementation was believed dead because it "mints one id per bracket and reuses it,
which NT8 rejects on any re-create". That is only true when the re-create happens after the whole
group has died. **Re-creating ONE leg while its sibling is still working may keep the same id**, so
per-generation ids are needed only for the fully-terminal case — and the `Order.Oco` public setter
agrees: group membership is assignable at create time, for a group that still exists.

**This is the fact the shipped implementation rests on** (§4r): a leg created beside a live sibling
*joins* its group, and only the cancel-then-create path — where our own cancel may have retired the
group — mints a fresh id.

### Two other things this trade exposed

- ⚠️ **`EDGE_WINDOW_BREACH` fires on an ordinary overnight entry.** The moment the position opened,
  the guard logged `[SHADOW] Would execute action FlattenPosition triggered by EDGE_WINDOW_BREACH`.
  Shadow only logged it (`P0-51` working), but **armed live this trade would have been flattened
  within a second of filling.** Any live validation booked outside the permitted edge window will be
  destroyed by the guard rather than by the defect under test. Schedule live work accordingly.
- **An ATM leg's price cannot be trailed from outside.** `nt_change_order` on `Stop_5c903ad3`
  returned `"modified"` and the order's timestamp moved, but the stop price did **not** change
  (29897.5 held) — our `DynamicAtmManager` owns that leg and re-asserted it. The copier's own
  `COPIER_STOP` is not ATM-managed, so `P0-9`'s `Change()` trail is unaffected; but do not use an
  ATM-managed order to test it.

### Suspected — one of the two is now addressed

The two `Rejected` `COPIER_TARGET` leftovers from the 01:01/01:03 parked-target run carried
**distinct** ids, so id reuse cannot be why they were rejected. Their tells point elsewhere: one is
qty **4** against a 2-lot position, and the other sits at **29905.625**, which is not a multiple of
MNQ's 0.25 tick.

> ✅ **The off-tick one is now moot** (§4r): both mirrored legs are snapped to the instrument's tick
> before submission. The cause is that the anchor is the follower's *average* fill price, and an
> average across partial fills lands between ticks. It was never *proven* to be the rejection
> reason — the ATM path's own off-tick prices (29897.419…, 29921.633…) were silently **rounded by
> NT8 at `Submitted`**, so off-tick is not always fatal — but there is now no path that sends one.
>
> ⚠️ **The qty-4-against-a-2-lot-position one is still unexplained**, and it is the more worrying
> of the two.

### Replikanto did nothing — until it was fixed, and then it told us a lot

The first attempt produced **no order, no position and no event** on either follower while
`Sim_All_Day_ORB` traded, with our copier correctly standing aside
(`COPIER_NO_ACTIVE_RELATIONSHIPS`). The operator then fixed its configuration; its real leader is
**`Sim-ORB`**, not `Sim_All_Day_ORB`. A 1-lot native ATM bracket on `Sim-ORB` at 01:56:56 then fanned
out cleanly:

| Account | Legs | OCO id |
|---|---|---|
| `Sim-ORB` (leader) | `Stop1` 1 @ 29913.75, `Target1` 1 @ 29958.75 | `75a1929ea45146109fd279b9185ddd4a` |
| `SimCopyTest1` | identical | `cb776ec9359a403cba1bc78238c0de8b` |
| `SimCopy2` | identical | `b32917cd0e9b48828e5626aee06181fc` |

Fan-out latency was ~12 ms and ~29 ms after the leader's legs.

**What this settles for `P0-9`'s mirrored target:**

1. **A mature copier mints a FRESH OCO id per follower account** — it does not propagate the
   leader's id. Three accounts, three unrelated ids. This corroborates the shape the parked
   `wip/p09-oco-target` branch already has (both follower legs sharing one locally-generated id) and
   rules out any design that tries to carry the leader's id across accounts.
2. **It mirrors the FULL bracket, stop and target.** That is precisely the capability we deliberately
   do not have yet, so "a follower with only a stop" is us being behind the field, not being careful.
3. Replikanto's ids are undashed 32-hex (`75a1929e…`); ours are dashed GUIDs. NT8 accepts either, so
   the id is an opaque string.

**⚠️ Two hazards this exposed in OUR code and docs:**

- **§4o's diagnostic rule is broken.** It says the tell for a manual bracket is the leader's order
  *names* (`Stop1`/`Target1` vs `Stop_<bracketId>`). Replikanto copies the leader's names
  **verbatim**, so its mirrors on a follower are indistinguishable by name from a native bracket.
- **We would mirror a mirror.** `OnLeaderOrderUpdate` only refuses orders whose `Name` contains
  `COPIER`. Replikanto's mirrored legs are named `Stop1`/`Target1`, so if an account were ever both a
  Replikanto follower and one of our leaders, we would treat its mirrored stop as a genuine leader
  stop and mirror it onward. **This is live today in one direction:** `Sim-ORB` is our follower
  (`Sim101 -> Sim-ORB`) *and* Replikanto's leader, giving
  `Sim101 -> Sim-ORB -> {SimCopyTest1, SimCopy2}`. A `Sim101` test trade now fans out to three
  follower accounts, which any P1-56 live validation must account for.

**Deliberately NOT concluded: whether Replikanto mirrors stop PRICE or DISTANCE.** All three accounts
filled at exactly 29928.75 in Sim, so both hypotheses predict identical legs and the run cannot
separate them. Ours mirrors distance from the follower's own fill because real fills differ.

### ANSWERED: Replikanto modifies the follower's leg IN PLACE, keeping the OCO group

The operator dragged the leader's `Stop1` in the NT8 UI, 29913.75 -> 29902. All three stops moved,
and everything that would betray a re-create stayed identical:

| Account | `orderId` | `oco` |
|---|---|---|
| `Sim-ORB` (leader) | `655154f7…` unchanged | `75a1929e…` unchanged |
| `SimCopyTest1` | `5491d1b8…` unchanged | `cb776ec9…` unchanged |
| `SimCopy2` | `e877f5f5…` unchanged | `b32917cd…` unchanged |

`Target1` was untouched on all three, and every stop carries the same modification timestamp
(`02:00:11.5915186`), so propagation was effectively instantaneous.

**Three conclusions, and they largely dissolve the blocker §4o put on the mirrored target:**

1. **Modify-in-place is what a mature copier does on a trail.** That retroactively vindicates the
   `Change()` trail fix in `995f6402` over the original `P0-9` "cancel-then-replace, not modify"
   note — and it is the ordinary case, not an edge case.
2. **A price modification PRESERVES OCO group membership, confirmed live.** Previously this was only
   inferred from reflection (`LimitPriceChanged`/`StopPriceChanged`/`QuantityChanged` exist,
   `OcoChanged` does not). Now observed.
3. **The trail path never re-creates a leg, so it never needs a fresh id.** Combined with the
   join-while-live result above, the ONLY case that needs a new id is one where the whole group has
   already gone terminal. `P1-56`'s remaining OCO work is therefore a narrow conditional, not the
   per-generation redesign §4o called for: keep the id when a sibling is still live, mint a fresh one
   only when the group is dead. The parked branch's "one id per bracket" is much closer to correct
   than it was credited for; its real gap is only the dead-group path (which is what its
   `BRACKET_MODIFY_FAILED` cancel-then-create fallback can hit).

### `nt_change_order` cannot trail an ATM-managed leg — confirmed twice

Attempted on our `DynamicAtmManager` bracket (`Stop_5c903ad3`, 29897.5 -> 29900) and on a native NT8
ATM bracket (`Stop1` on `Sim-ORB`, 29913.75 -> 29918.75). **Both returned `"modified"` and moved the
order's timestamp, and in both cases the stop price did not change** — the ATM owns the leg and
re-asserts it. The `"modified"` status is therefore not evidence of anything. The copier's own
`COPIER_STOP` is not ATM-managed, so `P0-9`'s `Change()` trail is unaffected; but never use an
ATM-managed order to test it.

---

## 4q. Session 10 record — 2026-08-10: `P1-56` closed, and the loop tried twice to ship a defect

**Closed**: `P1-56`. **Opened**: `P1-57`, `P2-58`. **Corrected**: the OCO id-reuse rule (§4p).
Suite 637/0 → **653/0**. Deployed build `995f6402` → **`c9459121`**, hot-swapped 06:19, 0 errors.
Seven commits on `harden/riskguard-p0-51`; nothing merged, nothing pushed.

### `P1-56` — what shipped

Body extracted to `SyncFollowerStopOnce`; `SyncFollowerStop` keeps its signature and becomes the
reservation **holder**: publish `StopInFlight` under `_lock` before any broker call, run a bounded
re-drive loop (`MaxBracketResyncPasses = 2`), release exactly once in a `finally` that runs **after**
the loop. A sync arriving mid-flight sets `StopResyncOwed`, returns without touching the broker or
`StopAttempts`, and the holder re-drives so the newer size/price is applied. Both
`bracket.WorkingStop = null` clears removed.

**The order of the two halves is the whole design.** The reservation stops a second sync creating a
duplicate; the *honest* `WorkingStop` is what makes that second sync **modify** the existing order
via the `Change()` trail path instead. Neither half works alone, and the reviewers who argued about
the reservation window never engaged with the second half — which is why they over-stated their
finding in one direction and under-stated it in the other.

### The loop produced three candidates. Two would have shipped live defects. All three passed every gate.

This is the session's most transferable finding, and it is about the **process**, not this defect.

1. **Round 1** put the reservation in place correctly but cleared it in the `finally` *before* the
   recursive re-drive re-took it. Both reviewers spotted the window; the arbiter upheld it. Then all
   three endorsed the same fix: *"do not clear `StopInFlight` when a re-sync is owed; let the
   re-drive's own `finally` clear it."* **That fix leaks the reservation forever** — the re-drive's
   first act is to test `StopInFlight` and back off, so it returns without ever reaching a `finally`,
   and that follower can never be given another protective stop. Redirected with an
   `--orchestrator-note` to hold one reservation across a bounded **loop** instead, which closes the
   window with no leak and no recursion.
2. **The apply run silently produced and applied a third, unreviewed candidate.** `--resume-raw`
   reseeds round 1 *and re-reviews it*; a `REVISE` there triggers a fresh round 2, and `--apply`
   ships **that**. It set `countAttempt = (pass == 0)`, so re-drive passes reached the broker
   **without counting an attempt** — turning `MaxBracketStopAttempts = 3` into effectively **9
   submissions**, the order-flood mode `P1-40`/`P2-46`/the flood cluster already cost us — and it
   restored `WorkingStop = null` on the `catch` and abort paths, losing track of a possibly-live stop
   and **reintroducing the very defect being fixed**. Caught by §9 step 3 (*confirm the candidate is
   the one that was reviewed*), reverted with `git checkout --`, and the reviewed candidate spliced in
   via the loop's own `regions.apply`, then verified **byte-identical** to the gated `final.patch`.

> ⚠️ **`--resume-raw … --apply` is not a promote-what-I-read command.** It is a fresh run seeded with
> that raw. If the panel says `REVISE`, you get a new implementation and *that* is what lands. To
> promote an exact candidate, splice it yourself with `regions.apply` and diff the result against the
> `final.patch` you reviewed. (This was mirrored into `AGENT_PATCH_LOOP.md` §9, which is not in this
> repo — see §3.)

**The arbiter rubber-stamped the winning round**: 22 findings, 0 upheld. A 0-upheld ruling is not
reassurance — on the round before it, the same arbiter upheld a finding and recommended a fix that
would have been a live defect. Read the patch.

### Test-first, and one test written specifically to distrust the arbiter

Three concurrent tests, all hand-written before the fix, because `*Tests.cs` is a protected path the
implementer cannot reach:

- `TestBracket_P1_56_InterleavedSyncsLeaveExactlyOneProtectiveStop` — **red at baseline**, reproducing
  the live shape exactly (two live stops, qty 2+1 behind 2 lots).
- `TestBracket_P1_56_AThirdSyncStillLeavesExactlyOneProtectiveStop` — written because the arbiter
  recorded *"there is no gap between passes"* as a **settled fact on argument alone**, and a settled
  fact nothing tests is how `P1-40` shipped.
- `TestBracket_P1_56_AFailedSubmitDoesNotWedgeLaterSyncs` — **passes at baseline**, and exists to fail
  if the reservation is ever leaked on a throwing path. A reservation leaked on failure is permanent
  and strictly worse than the duplicate-leg defect.

**The deterministic-interleaving technique is reusable and `P1-13` needs it.** `Account.BrokerCallObserver`
fires *inside* `CreateOrder` — the exact window — so the first sync can be parked there while another
thread drives the second. No sleeps, no racing, no flakiness. Every wait is bounded so that a fix
which makes one sync *block* on another reports a failure instead of hanging the suite. This is the
first genuinely concurrent test in the suite; the `S`-series is still sequential.

### Also this session

- **`P1-56` is NOT validated live** — unit + compile only, like `P0-53`/`P1-54`/`P0-55`.
- Two read-only `oco` fields added (`/api/orders`, `ORDER_UPDATE`) — they are what made §4p possible.
- The stale *"NT8's Change path is not available through this seam"* comment corrected; it had sat 60
  lines above the `Change()` call that contradicted it since `995f6402`.
- `MaxBracketResyncPasses` replaced the literals `3` and `2`, which encoded one bound twice and were
  one edit from disagreeing. The arbiter dismissed this as *"hypothetical future maintainers"*.

---

## 4r. Session 11 record — 2026-08-10: the mirrored target ships, and what the parked branch was missing

**Closed**: `P0-9` item (1). Suite 653/0 → **686/0**. Deployed build `c9459121` → **`86c6376f`**,
hot-swapped 13:12, `nt_compile` 0 errors under net48. One commit on `harden/riskguard-p0-51`;
nothing merged, nothing pushed. **`wip/p09-oco-target` is superseded — delete it.**

### The asymmetry between the legs is the design

The stop is **risk**; the target is **upside**. Every place they differ, they differ for that
reason, and tidying them into symmetry would break something:

- The stop's re-create path may **re-mint the OCO id and cancel the target** to rebuild the pair.
  The target's re-create path **joins** whatever live group the stop is in and never touches it.
  Cancelling a working protective stop to tidy up a group is not a trade worth making.
- Each leg has **its own** in-flight reservation, owed-flag and attempt budget. Sharing the stop's
  would let an in-flight *target* sync make the risk leg wait its turn, and would let target churn
  spend the budget that keeps the follower protected.
- The target's flat/side-abort path deliberately does **not** clear `FollowerQuantity`/
  `FollowerSide` as the stop's does — that would let a target sync switch the stop sync off.
- `SyncFollowerBracket` drives **stop first, always**, and every call site goes through it. A site
  that syncs one leg leaves the pair half-rebuilt, and that is a mistake that reads as correct.

### What the parked branch did not have — four of the five are live-risk

`wip/p09-oco-target` "worked" live and was credited as nearly done. Rebasing it onto the holder
split was the small part. These were the rest:

1. **The dead-group id conditional.** It minted one id per bracket and re-used it forever. On the
   cancel-then-create path the broker rejects a re-used id whose group has gone terminal — and that
   path belongs to the **stop**. The feature would have produced a naked follower on the leg it is
   not even about. *(Whether cancelling one leg retires the group is still unverified; the fix is
   written to be correct either way, which is why it does not need the answer.)*
2. **No reservation on the target sync.** It predated `P1-56` and carried that defect verbatim.
3. **No attempt bound on the target.** A rejecting broker would have been answered forever — the
   flood mode the `P1-43`…`P2-46` cluster already cost us.
4. **No OCO-retirement guard.** *This one is created by the pairing itself.* When the target fills,
   NT8 cancels the stop; `OnFollowerOrderUpdate` read that as a **lost** stop and re-submitted it —
   and because NT8 raises ExecutionUpdate before PositionUpdate (`P0-49`'s ordering) the follower
   still read as open, so `P0-50`'s live re-read let it through. An orphan stop on an account that
   has just closed. **A leg whose sibling FILLED was retired, not lost.**
5. **No tick rounding.** Both legs are computed from the follower's *average* fill price, and an
   average across partials lands between ticks. §4p listed the `COPIER_TARGET` Rejected at
   **29905.625** on a 0.25-tick instrument as "suspected, not concluded" — this is almost certainly
   it, and it is now moot on both legs.

### A multi-target leader is refused, not guessed at

A scale-out bracket has several targets; the follower has one mirrored leg. Last-seen makes the
follower's exit an artefact of NT8's event ordering; nearest exits the follower's **whole** position
at the leader's **first** partial. So it withdraws the target, logs `BRACKET_TARGET_AMBIGUOUS`, and
keeps the stop — falling back to the known-good pre-target behaviour. `Target1`/`Target2` is
ordinary ATM usage on this box, not an exotic case.

Deliberately **not** applied to stops: several working stops is a reconciliation problem
(`P1-36`, `P3-30`), and dropping the risk leg over it is the wrong trade in the wrong direction.

### Every guard was verified by mutation, not by argument

Nine tests, hand-written before the code (`*Tests.cs` is a protected path). Six were red at
baseline. The two that were not — the retirement guard and the tick rounding — **cannot** be red at
baseline, because neither situation can arise until targets exist. That is the exact shape of the
"settled fact nothing tests" that shipped `P1-40`, so each guard was instead mutated and the test
observed to fail:

| Mutation | What the suite reported |
|---|---|
| Retirement guard disabled | the orphan stop **is** submitted — 2 `COPIER_STOP` where 1 was expected |
| Id re-used on re-create | the retired group's id carried onto the new stop |
| Target reservation disabled | **2 live targets** against one position |
| Re-drive removed (back off, never re-apply) | a **1-lot** target behind a 2-lot position — under-cover |
| Multi-target refusal disabled | a target mirrored from a scale-out leader |
| Tick rounding disabled | both legs at `.125` on a 0.25 tick |

The stub gained `SimulateChangeFailure` (nothing could reach the cancel-then-create fallback before)
and `FillOrderAndRetireOcoGroup`. The stub models **fill-retires-the-group**, which is what OCO
means; it deliberately does **not** model cancel-retiring-the-group, because that is a guess and
encoding a guess in the double would have made the copier agree with it.

### Still open on this item

- **Not live-validated.** See §4a for exactly what to watch on the first Sim trade.
- **Partial-fill re-pairing across a scaled leader position is untested.**
- The two stop-path changes (OCO id, tick rounding) have not been seen on a real fill.

---

## 4s. 2026-08-10 — the mirrored target's first live trade: 3 of 4 signals pass, and a P0 falls out

**Setup.** `Sim101` ATM bracket, MNQ SEP26, long 1 @ 29788.25, `AtrAdaptive` (which overrode the
requested tick distances): leader stop 29745.75, leader target 29859.75, both in oco `4ac44f1c…`.
RiskGuard `shadow`, armed, guarding. Deployed build `86c6376f`.

### What passed

| | Signal | Result |
|---|---|---|
| 1 | **The mirrored stop is not rejected** now that it carries an OCO id | ✅ `COPIER_STOP` went `Initialized → Submitted → Accepted` under oco `a2e765fd…`. **A single-member OCO group is accepted by NT8** — that was inferred, not proven, and it was the one way this change could be worse than what it replaced |
| 2 | **Both legs, one shared group, right prices, on tick** | ✅ `COPIER_STOP` 1@29745.75 and `COPIER_TARGET` 1@29859.75, both oco `a2e765fd…`. The target JOINED the stop's live group rather than forcing a re-create. Both on a 0.25 boundary |
| 2b | **Distance-mirrored, not price-copied** | ✅ `BRACKET_TARGET_MIRRORED: target 1@29859.75 (leader offset +71.5, follower entry 29788.25)`. Leader and follower both filled 29788.25, so the *orders* alone cannot distinguish the two designs — the log line can, and does |
| — | Ordering and latency | ✅ Stop created 14 ms after the follower's own fill, target 16 ms after the stop. Stop first, as `SyncFollowerBracket` requires |
| — | FSM | ✅ `Created FSM Sim-ORB|MNQ SEP26 -> ProtectedPending` |

### Signal 3 failed, and found `P0-59`

To fill the target on demand its limit was moved to a marketable price. It never got there. The
copier saw the leg enter `ChangeSubmitted`, concluded it was gone, and **created a second
`COPIER_TARGET`** — `BRACKET_TARGET_MIRRORED` at 13:55:56.3437, *before* the modify reached the
broker at .3537. Both ended `Working` at 29859.75 in the same OCO group; the third-party copier
mirrored the pair onward, so three accounts each held two targets against one lot.

Root cause, and the reason it is a **P0 on the stop path**, in the plan's `P0-59`:
`IsPendingOrWorking` omits `ChangeSubmitted`/`ChangePending`, and `OnFollowerOrderUpdate` infers
"terminal" from `!IsPendingOrWorking` — **the two predicates are not complements**. Our own trail
calls `Change()`, so this is reachable on every trail step, on the risk leg, without any
concurrency. `P1-56`'s reservation cannot help: one sync misreading one state is enough.

**The stub enum does not declare those states**, so the suite could not have expressed this at
686/0. That is `P0-49`'s lesson one level lower down — in the enum rather than the event order.

> **The external modify is not what makes this real.** It is what made it *visible in one shot*.
> The production trigger is `Account.Change()`, which the copier calls itself.

### Two other things this trade exposed

- ⚠️ **`MAX_TRADES_BREACH` fired on entry**, on both `Sim101` and `Sim-ORB`, followed by
  `LOCKOUT_PHASE: PendingCancel` and a `LOCKOUT_SWEEP_SHADOW` every 5 s: *"would flatten
  [MNQ SEP26], cancel 2 order(s)"*. `MaxTradesPerSession` is 8 and these accounts are past it.
  **Armed live, this trade would have been flattened on entry and its mirrored legs cancelled** —
  add it to `EDGE_WINDOW_BREACH` on the list of things that will destroy a live validation.
  Shadow contained all of it, which is `P0-51` working.
- **`P1-57` came within one naming convention of firing.** `COPIER_EXEC_SELF_ORIGINATED` shows the
  third-party copier's copy was dropped only because it embedded *our* name
  (`COPIER_FOLLOW-34362-…`) and so matched the `COPIER` substring. Had it named the leg `Stop1`, as
  it does when copying a native bracket, we would have mirrored it onward. The defence held by
  luck, not by design.

### Cleanup

All four accounts flat, no working orders. `nt_close_position` on the leader did **not** propagate
an exit to the followers — each had to be closed explicitly (closing `Sim-ORB` did cascade through
the third-party copier to its two followers). Three `Rejected` leftovers from earlier sessions
remain and are unrelated.

---

## 4t. 2026-08-10 — stepping back: one root cause under both the copier's and RiskGuard's order bugs

`P0-59` looked like "add `ChangeSubmitted` to a list". Reflecting NT8's enum instead of trusting
ours turned it into something much larger.

### The finding

**NT8 has sixteen `OrderState`s.** `IsPendingOrWorking` classified five, `IsTerminal` three. The two
were **not each other's complement**, so eight states were unclassified — and the two addons
independently inferred *opposite* things about them:

| | asked | so an order in… | …was treated as | hazard |
|---|---|---|---|---|
| RiskGuard | `!IsTerminal` | `CancelSubmitted`, `CancelPending` | **coverage** | a position reads as protected while its stop is being pulled |
| copier | `IsPendingOrWorking` | `ChangeSubmitted`, `ChangePending`, `TriggerPending` | **gone** | a duplicate protective leg is created |

Both live. Both naked-risk or over-cover. One root cause, pointing in two directions at once.

### Why the obvious fix was the wrong one

Adding the missing states to `IsPendingOrWorking` would have made the symptom disappear and left
the structure that generates it — the next state NT8 adds lands in the same gap. The reason a single
boolean cannot be right is that **callers ask two questions whose fail-safe answers are opposite**:

- *"is something already here, so do not create a second?"* — answering **no** wrongly over-covers
- *"does this actually protect the position?"* — answering **yes** wrongly leaves it naked

So: one total classification, two derived predicates, and `Indeterminate` **occupies a slot and
provides no coverage** — conservative both ways at once.

**`IsPendingOrWorking` was deleted rather than wrapped**, turning all 21 call sites into compile
errors so each had to declare which question it asked. Nine were coverage questions, four were
cancel-worthiness questions, and they had been sharing one predicate.

### The test double was why none of it was visible

The stub enum carried **ten of sixteen** states. Six could not be named by any test, so the suite
was green at 686/0 with a P0 live. All sixteen are now declared — **reflected out of
`NinjaTrader.Core.dll`, not recalled** — and a conformance test fails if the stub drifts or any
state reaches the default arm. The test file's private copy of the liveness list is deleted too: a
second definition of "alive" living in the grader is this defect one level up.

> This is `P0-49`'s lesson again — *"the test stub raises whatever the test raises"* — one level
> lower down, in the enum rather than the event order. **A green suite is evidence about our
> fiction, not about NT8, unless something forces the two to agree.** That forcing function now
> exists for `OrderState` and for nothing else.

### Verified by mutation, both directions

| Mutation | What the suite reported |
|---|---|
| `ChangeSubmitted` → Terminal (the copier's old belief) | **2 `COPIER_TARGET`s**, exactly as seen live — and **2 `COPIER_STOP`s** on the trail path |
| `CancelSubmitted` → Working (RiskGuard's old belief) | `CoveredQuantity` **6** and state `ProtectedPending` on a position whose stops are *both* being cancelled |

The second is the one worth remembering: a fully naked position, reported as protected, with
nothing arming a replacement.

### What this says about the approach, not the defect

Almost every defect in this project is the same shape: **the model diverged from the broker and
nothing re-derived it.** The plan identified that on page one and then 48 defects were closed by
teaching the fast path one more case. That series does not terminate — the event space belongs to
NT8, and now to a third-party copier as well. The reconciler is not an enhancement to schedule when
convenient; it is the thing that closes the class. See §4a.

---

## 4u. 2026-08-10 — the reconciler lands as the primary path (`P3-30` copier half, `P3-31` seam)

§4t argued that the 48-defect series does not terminate and the reconciler is what closes the
class. This is that work, for the copier's bracket. **New file
`scripts/ninjatrader/addons/CopierReconciler.cs`; both leg syncs now decide through it.**
Suite **762 passed, 0 failed** (from 705). NT8 compiles clean, net48, 0 errors, deployed.

### The structural fact, which is sharper than "the model diverged"

Neither `SyncFollowerStopOnce` nor `SyncFollowerTargetOnce` had **ever** enumerated
`followerAcc.Orders`. Each decided from ONE cached `Order` reference —
`bracket.WorkingStop` / `bracket.WorkingTarget`. So a leg that existed at the broker but was not
the one being held was **invisible, and therefore permanent.**

That is what "two working COPIER_TARGETs against one lot" was on 2026-08-10 (`P0-59`): not a leg
placed wrongly, **a leg nothing was capable of noticing afterwards.** No amount of additional care
on the fast path could have repaired it, because the fast path could not see it. `Reconcile`
enumerating the account and cancelling *extra* owned legs is the whole difference.

### Three states of desire, not two — and why the obvious design is a naked follower

`HasStop: bool` was the first design. It is wrong: "no stop desired" then means both *"the position
is gone, cancel everything"* and *"the leader cancelled its own stop, so we do not know where ours
goes"*. Those need **opposite** handling. Collapsing them reverts `P0-9` item (4) and takes the stop
off an open position — a naked follower delivered as a refactor.

So `LegIntent { Required, Unspecified, Forbidden }`, and `Unspecified` still de-duplicates but never
creates and never cancels the last survivor. `TestDesired_UnknownOffsetIsUnspecifiedNotForbidden`
and `TestReconcile_UnspecifiedLegKeepsOneAndCreatesNone` are the two that hold it down.

### ⚠️ `bracket.StopInFlight` is NOT `Reconcile`'s in-flight parameter

The bracket flags are mutual exclusion between two **syncs**. `Reconcile`'s parameter means
"submitted, and not yet in `Account.Orders`". Feeding the first into the second was the first
wiring and it placed **no stop at all** — `SyncFollowerStop` sets the reservation *before* calling
in, so the reconcile suppressed the very `Create` the sync existed to make. The event-driven
callers pass `false`; a timer is what needs the real ledger.

### Verified by mutation, both layers

18 mutations, each reinstating a belief that was live at some point in this project or an
obvious-looking simplification. **17 caught by a named test.**

| Layer | Mutations | Caught |
|---|---|---|
| the two pure functions | 10 | 10 |
| the wiring into `TradeCopierEngine` | 8 | 7 |

Two results worth more than the tally:

1. **A test caught a real defect in `Reconcile` while it was being written.** The price/quantity
   comparison ran *before* the shape check, so a leg carrying our name with `OrderType.Limit` at
   the stop's price compared equal and was accepted **as the stop** — while a limit below the
   market is not a stop, it fills at once. Shape before price; the order of those two checks is
   the difference between a protective stop and an instant exit.
2. **The mutation harness lied on its first run.** All 10 reported `DID NOT COMPILE`, because the
   build-failure check matched `"error"` — which also matches the `0 Error(s)` summary line. A
   harness that reports every mutation as caught for the wrong reason is worse than none. It now
   matches `": error CS"`. *Check what your gate actually keys on before believing its verdict.*

### Two guards found to be UNREACHABLE, and honestly re-labelled

Mutation testing found two places where I had written something that reads as safety and cannot
change behaviour. Both are recorded rather than quietly kept:

- `AddIfMissing`'s reference-identity check (now `AddCandidate`, a plain append). `Reconcile`'s
  keeper loop already compares by reference, so a doubled entry never produced a cancel.
- `ContainsReference` in the slot collection. **Kept**, but the comment now says plainly that the
  behavioural protection is the keeper loop's `ReferenceEquals` and that this line only makes
  `slotCount` truthful for the operator-facing log. It is not defence.

> The general point: *"I added a guard" is not evidence the guard does anything.* Mutating it away
> and watching the suite stay green is. Both of these would otherwise have been read by the next
> session as load-bearing.

### The one mutation that SURVIVED, stated rather than papered over

`int liveQty = Math.Min(qty, livePos.Quantity)` at the broker call — replacing it with `qty` leaves
the suite green. It is a **second** clamp; `ComputeDesiredBracket` already clamped to the live
position. It is only reachable if the position changes between the reconciler's read and the broker
call, which is a concurrency window the suite cannot drive — the same gap §4a records for `P1-13`,
where the S-series is sequential and the risk is concurrent. **Kept as defence-in-depth, and
explicitly NOT proven.** Do not remove it on the grounds that no test covers it.

### What is NOT done

- **The background timer.** Events call the reconciler; nothing calls it on a clock. Until that
  exists, a divergence that arrives with no subsequent event is still permanent — the reconcile is
  idempotent and ready for it, but unscheduled.
- **`P3-31`'s ledger.** The seam is tested; the ledger does not exist. The timer needs it first.
- **The RiskGuard-side audit** (naked position, orphan stop, FSM/broker divergence). `P3-30`'s
  plan entry covers both addons; only the copier's bracket is done.
- **Live validation.** Everything here is unit + compile + mutation. No live trade has been through
  it. The first live `COPIER_STOP` and `COPIER_TARGET` are the ones to watch, and note that the
  decision path underneath *both* legs changed.

---

## 4v. 2026-08-10 — the reconciler's first live trade: it works, and it found two more defects

§4u shipped with "no live trade has been through this yet". This is that trade, on
`Sim101 -> Sim-ORB` with the guard in `shadow`. **The reconciler did what it was built to do, and
the same hour produced `P0-61` (fixed, live-validated) and `P0-62` (open).**

### ✅ What passed

**The mirror, through the new decision path.** Leader entry 29777.5, ATM stop 29752.75, target
29821.5 → offsets **−24.75 / +44.00**. Follower filled 29778.25 and got stop **29753.50** and
target **29822.25** — both exact, both on tick, **both in one OCO group**.

**The headline: a stray leg the engine held no reference to was cancelled.** A `COPIER_STOP` was
planted directly on `Sim-ORB` at 29745 with no OCO id, so the engine had never heard of it — the
exact state of the original `P0-59` incident. Two working stops then stood behind one lot. On the
next sync:

```
34416 Cancelled                              <- the stray
COPIER_BRACKET_MODIFIED  stop moved to 1@29754.5 in place; no unprotected window
```

The engine's own leg was **modified in place** and the stray was cancelled. The previous build
could not have done this at any price: it read one cached `Order` reference and never enumerated
`followerAcc.Orders`, so the stray was invisible and permanent.

**Exact-match ownership held, live.** The third-party copier mirrored our legs onto `SimCopyTest1`
and `SimCopy2` as `COPIER_STOP-34410-0104CFF5`. Those are not ours, and nothing touched them —
`P1-57`'s hazard from the dangerous direction, and the conservative naming is what covers it.

### ❌ `P0-61` — found by the trade, not by 762 tests

Scaling the leader in exposed it: a second `Change()` against a leg already in
`ChangeSubmitted`/`ChangePending` is **dropped by NT8, and reverts the order to its pre-change
values**. Both follower legs stayed at qty 1 behind 2 lots. Full write-up and the fix are in the
plan's `P0-61`; the short version is that this is `P0-60`'s lesson one step along — a **third**
question (`AcceptsModification`) that the two existing predicates both answer wrongly, because a
mid-change leg occupies a slot *and* provides coverage *and* cannot be changed.

**Re-tested live after the fix**: `BRACKET_DEFERRED` → `BRACKET_DEFERRED_REDRIVE` →
`stop moved to 2@29742.5`, `target moved to 2@29805`. Both legs reached the correct size and price,
which the previous build never managed.

> The transferable half: **declining to act is only safe if something later acts.** The first cut
> reused `*ResyncOwed`, which the sync's own pass loop consumes immediately — re-driving while the
> leg was still mid-change and giving up at the pass bound. It needed its own flag and a settle
> hook placed *before* `OnFollowerOrderUpdate`'s `OccupiesSlot` early return.

### ❌ `P0-62` — still open, and the evidence is inside one `Change()` call

`Account.Change()` **applies the price and silently refuses a quantity increase.** One call carried
both; the order went `1 @ 29743.5` → `1 @ 29742.5`. So a scaled-in follower can never have its
protective leg grown by modification. The attempt budget then stops the retries — it fails quiet
rather than flooding, which is the right failure, but the follower stays under-covered.

Two candidate remedies, both with real costs, written up in the plan. **Do not just widen the
retry budget; the budget is not what is failing.**

### RiskGuard was the only thing that noticed — and shadow is why nothing happened

`FSM_UNDERCOVERED: covered 1 < pos 2`, then `MISSING_STOP_FLATTEN` on all four accounts. **Armed
live, RiskGuard would have flattened the lot.** Worth holding both halves of that: the compensating
control worked exactly as designed, *and* the copier under-covered a live position. Neither fact
cancels the other.

### Operational notes from this session

- ❌ **RETRACTED — there is no ATM lockout bypass. An earlier revision of this section claimed one;
  it was wrong.** The observation was that `nt_place_atm_order` succeeded on `Sim101` while
  `nt_place_order` was blocked on `Sim-ORB`, and I inferred the ATM path skipped the gate. It does
  not: `PlaceAtmOrder`, `PlaceOrder` and `PlaceOcoOrder` all call `IsAccountLocked`
  (`McpBridgeAddOn.cs:3382`), which consults `RiskGuardAddOn.Instance.IsAccountLocked` first.
  **Disproved by direct test 2026-08-10**: `Sim_All_Day_ORB` was locked via
  `nt_emergency_flatten` and *both* endpoints then returned `Order blocked: ... is locked out.`
  > **The real explanation, and the lesson.** `Sim101` was **not** locked at 15:27:46 when the ATM
  > order went in — that entry pushed the trade count past `MaxTradesPerSession` and tripped the
  > lockout about five seconds later (`LOCKOUT_CANCEL` at 15:27:51). I read the status eight
  > minutes afterwards, saw `isLockedOut: true`, and treated it as the state *before* the order.
  > **A lockout state read after the fact is not evidence of the state at submit time**, and on
  > these accounts an ordinary entry is itself enough to cause the transition. Read the gate
  > before the action, or test the gate directly.
- **Both `Sim101` and `Sim-ORB` were locked out on arrival** (`MAX_TRADES_BREACH`, as §4a warns),
  with the shadow sweep logging `[SHADOW] Would execute action CancelAllOrders` every 5 s. I
  **unlocked both** via `POST /api/lockout {"action":"unlock"}` to run the test, which **resets
  those accounts' metrics**. `ShadowSessionsCompleted` is untouched. They are left unlocked.
- **State left clean**: all accounts flat, zero working orders, guard still `shadow`/armed.
- `/api/riskguard/state` does not exist; the FSM route is `/api/riskguard/fsm-state`, and
  `nt_riskguard_state` returned an empty list even with four positions open.

### ⚠️ A test-writing trap that cost an hour, and the product question under it

**Raising two separate leader stop ORDER OBJECTS leaves the first one `Working`, and the copier
re-anchors from whichever it reads last.** A test written that way passes or fails on collection
iteration order — `TestBracket_P0_61_ADeferredChangeIsReappliedWhenTheLegSettles` passed once, then
failed three runs in a row on identical source, which is what sent me looking for a bad mutation
restore that did not exist. Trail the **same** order object instead
(`leaderStop.StopPrice = ...; leader.TriggerOrderUpdate(leaderStop);`) — which is also what NT8
really does, since a trailed leg keeps its id and oco (§4p). `TestBracket_TrailingModifies...` uses
two objects and happens to pass; do not copy that shape.

**The product question it exposes**: with two working leader stops, the copier picks an arbitrary
one to anchor on. `P0-9` refuses a multi-*target* leader outright
(`TestBracket_P0_9_AMultiTargetLeaderIsNotMirroredAtAll`) but there is **no equivalent refusal or
coverage-sum for multi-STOP leaders**, even though `P1-36` built the multi-stop coverage sum that
would answer it. Not filed as a defect — a real leader's ATM trails one leg in place — but worth
resolving when `P1-36`'s sum is shared with the reconciler.

---

## 7. Decisions already made — do not re-litigate

> **Renumbered from §5 to §7 on 2026-08-13.** Two different sections were both called "§5" —
> this one and [§5 THE OPEN BACKLOG](#5-the-open-backlog--authoritative-as-of-2026-08-13) — so a
> cross-reference to "§5" was ambiguous for three sessions. Older text and transcripts saying
> "§5" about a *settled decision* mean this section.

> **`P0-9` item (1)'s five invariants (closed 2026-08-10).** Mirrored verbatim into the loop profile's
> `settled` tuple (`agent/nt8_riskguard.py:106`). Retire from **both** places or the panel keeps arguing.
>
> 1. **The two legs are deliberately asymmetric.** Do not propose unifying the syncs, sharing
>    `StopInFlight`/`StopAttempts` with the target, or making the target symmetric. Sharing lets an
>    in-flight *target* sync delay the risk leg, and lets target churn spend the stop's budget.
> 2. **The OCO id rule is about the group's life, not the id's history.** A fresh id is minted only
>    on the cancel-then-create path. Not per-generation on every sync; and not never — re-using an
>    id whose group may be retired has the broker reject the new **stop**.
> 3. **A leg terminal while its sibling FILLED was retired, not lost.** `P0-50`'s live re-read does
>    not catch this, because ExecutionUpdate precedes PositionUpdate.
> 4. **A multi-target leader is not mirrored at all.** Not nearest, not last-seen. Not applied to
>    stops.
> 5. **Leg prices are rounded to tick before the already-correct comparison**, not after — after
>    would never match and would re-drive the leg forever.

> **`P1-56`'s two invariants (closed 2026-08-10).** Mirrored verbatim into the loop profile's `settled`
> tuple (`agent/nt8_riskguard.py:106`).
>
> 1. **`SyncFollowerStop` is the reservation holder; `SyncFollowerStopOnce` does the work and never
>    touches the flags.** `StopInFlight` is published under `_lock` before any broker call and cleared
>    exactly once in a `finally` that runs *after* the bounded re-drive loop. Do not clear it between
>    passes (reopens the window); do not leave it set for the re-drive to clear (**leaks forever** —
>    the re-drive backs off before reaching any `finally`); do not make the re-drive recursive again;
>    and **do not let re-drive passes skip the `StopAttempts` increment** — they make real broker
>    submissions, so not counting them multiplies the bound.
> 2. **`bracket.WorkingStop` is never cleared before a broker call, nor in `OnFollowerOrderUpdate`** —
>    not even on the `catch` or abort paths. An honest `WorkingStop` is what makes a concurrent sync
>    *modify* the existing stop rather than create a second one. If the `Cancel` threw, the old stop
>    may still be live, and forgetting it recreates the duplicate-leg defect.

- **The copier fails closed on ENTRIES, never on EXITS** (settled across `P0-5`, `P0-6`, `P1-23`,
  `P1-22`). A quarantined relationship still copies exits; unimplemented sizing modes block
  entries only; an exit is never rounded or clamped to zero while the follower holds a position.
  Blocking an exit strands the follower in a position the leader has already left — worse than the
  thing being guarded against. Reviewers propose "just quarantine it" every time.
- **Orders are keyed by object reference, never by `Order.OrderId`** (`P1-22`). NT8's `OrderId` is
  neither unique nor stable across the historical→live transition (`RiskGuardAddOn.cs:4481`). The
  test stub assigns one stable GUID per order, so an id-keyed map passes the entire suite.
- **The mirrored bracket stop carries the leader's SIGNED offset**, applied to the follower's own
  fill (`P0-9`). Never `Math.Abs` — a leader trailing into profit puts the stop above entry on a
  long, and an absolute distance mirrors it onto the losing side. Never the leader's stop *price* —
  that is wrong by the slippage `P1-22` measures, and by a whole scale across a micro/mini
  conversion.
- **Bracket re-submission is bounded, and the counter does not reset on a successful `Submit`**
  (`P0-9`). The failure mode is a broker that accepts the submit and rejects the order moments
  later, so "Submit did not throw" is not evidence of protection.
- **Slippage and mirrored distances are computed only between price-comparable instruments**
  (`P1-22`, `P0-9`). A `CustomSymbolMappings` entry may legitimately point ES at NQ.
- **The copier places no default bracket of its own** (`P0-9`). RiskGuard's auto-stop owns
  "position with no stop"; two independent stop sources over-cover and flip the position when both
  fire. `EnableFollowerAtm` was deleted, not implemented.
- **Coverage is the SUM over every live protective stop** (**P1-36**, closed 2026-08-07).
  `CoveredQuantity` and `RecognizedStopOrder` are both **derived** from `PositionGuardFsm`'s stop
  list and neither is assignable — the old pair had to be written together at nine sites and
  nothing stopped them drifting. The auto-stop is sized to `liveQuantity - alreadyCovered`, not to
  the whole position. Do **not** propose restoring a single `RecognizedStopOrder` slot or the
  "replace only with an equal-or-larger stop" rule.
  > This bullet previously read *"multi-stop coverage aggregation is out of scope; `CoveredQuantity`
  > deliberately follows a single stop order"*. Same retirement as the P1-35 entry below: left
  > unedited it would instruct reviewers to approve reintroducing a closed defect.
- **Orphan cancels are queued, not inline** (**P1-35**, closed 2026-08-07). `UpdateFsmOnPosition`
  adds to `_pendingCancels` under the lock; `DrainPendingCancels()` sends them after it is
  released. Do **not** move the `Cancel` back inline, and do **not** call the drain from inside
  the lock — the lock is re-entrant, so that reads as correct and changes nothing. The TESTING
  build throws on it.
  > This bullet previously read *"orphan-cancel under `_stateLock` stays"*. Left unedited it
  > would now be instructing reviewers to approve reintroducing the defect. Settled decisions
  > have to be retired when they are settled the other way.
- **`SeedFsmsForExistingPositions` does not need its own lock** — its call sites
  (`SubscribeToAccount`, and `ToggleArmed` since P1-15) all already hold `_stateLock`, and it
  makes no broker call. Reviewers flag this as a false positive.
- **Simulated accounts are identified by `Provider`, never by name** (**P1-20**, closed). Do not
  reintroduce a `Name.StartsWith("Sim")` test or OR one in. Playback is deliberately not exempt.
- **The lockout sweep's three-phase order is deliberate** (**P1-11**, closed): cancel
  risk-increasing orders, flatten, then cancel reducing orders only for instruments confirmed
  flat. Cancelling everything up front and then failing to flatten is the naked-position bug.
- **`_lastShadowSessionDate` travels with `_shadowSessionsCompleted`** (**P1-37**, closed). They
  are one fact; splitting them let a restart re-count a session.
- **No new `GuardFsmState` enum values** — existing tests assert on them.
- **`ValidateInvariant` must not reject `PlaceStopOrder` on `action.Quantity > liveQuantity`**
  (settled landing T2). It looks like a missing safety check and it leaves the position
  permanently naked — see §1. `ExecuteAction` re-sizes from the live position.
- **`ArmGraceTimer` under `_stateLock` is correct and required** (T1). It only schedules a timer
  callback; it makes no broker call. Reviewers raise it as a lock-scope violation every round.
- **Reading `account.Positions` outside `_stateLock` is accepted.** A stale read yields a safe
  abort or a harmless spurious grace timer, not naked risk.
- **The TOCTOU window between the live position read and `account.Submit` cannot be closed**
  without holding a lock across a broker call, which is forbidden.

These are also encoded in **`agent/nt8_riskguard.py`** under `settled` (**21 entries**, ~1.2k tokens),
which injects them into every review round. **Add to both places, and retire from both places.**
A settled decision that has since been settled the other way does not merely go stale — it
actively instructs the panel to approve reintroducing a closed defect. The P1-35 entry above
was exactly that until 2026-08-07.

> ⚠️ **This claim was FALSE from the repo split until 2026-08-13, and it cost a real defect.** The
> tuple carried **6** entries while this section asserted that `P0-9`'s five invariants and
> `P1-56`'s two were "mirrored verbatim" into it. They were not there at all.
>
> That is not bookkeeping. `P1-56`'s invariant 1 — *`SyncFollowerStop` is the reservation holder;
> `SyncFollowerStopOnce` never touches the flags* — is **exactly** the rule the `P0-63` candidate
> broke, by re-driving through `...Once` and bypassing the in-flight reservation. It was the most
> serious defect in that candidate, **no reviewer flagged it**, and it was caught by reading (§5.9).
> The panel could not have flagged it: it was never told. The tuple is now reconciled against this
> section, and the invariant is stated in the imperative form that would have caught it — *any new
> caller that must respect the reservation calls the WRAPPER, never `...Once`*.
>
> **The lesson generalises past this file.** "Mirrored into the reviewer prompt" is a claim about a
> second artifact, and nothing checks it. When a doc says two things agree, verify they still do
> before relying on either — the split silently dropped 15 of 21 and no gate noticed.

---

## 8. Known traps

> **Renumbered from §6 to §8 on 2026-08-13**, with §7 above, so the two "§5"s no longer collide.
> Note that §7 and §8 sit *physically before* §4w–§4z and §5; section letters and numbers are stable
> identifiers cited from the plan and from older transcripts, so they are deliberately not reordered
> on disk. Use the reading order in the header.

- **A `.github/workflows/` push refused for the `workflow` scope is a *credential* problem, not a
  code one — and it has two exits, not one.** `gh auth refresh -s workflow` is the obvious one and it
  needs a browser. The other: **an SSH push is not an OAuth App push, so the restriction does not
  apply to it at all.** These repos were created over HTTPS with a `gh` token (`credential.helper` is
  `gh auth git-credential`, so the token's scopes govern every HTTPS push), and CI stayed parked for a
  day on the assumption that the scope was the only door. ⚠️ **Do not "prepare" the move by committing
  the workflow file locally while the push is blocked** — the rejection is per-push, not per-file, so
  one unpushable commit wedges *every* later push on that branch.
- **NT8 raises `ExecutionUpdate` BEFORE `PositionUpdate`.** Any code that reads `account.Positions`
  from an execution handler is reading a position that does not exist yet on an entry fill. This
  cost `P0-49`: the copier's bracket anchored itself that way and therefore never anchored at all,
  leaving followers naked for the life of every ATM trade. **The test stub raises whatever the
  test raises, in whatever order the test chose** — and every bracket test drove
  position-then-execution, because that is the order a person writes it in. Subscribe to
  `PositionUpdate` for anything that needs the net position.
- **Two unrelated background processes commit to *tvDownloadOHLC*.** Stage explicit paths, never
  `git commit -a` and never `git add <dir>` — a `git add docs/architecture/` swept in an
  unrelated agent's file during this work. Less acute here since the split (this repo has no other
  writers), but the loop *does* write `logs/agent_loop/` on every run: `.gitignore` excludes the
  per-run artifacts and keeps only `ledger.jsonl` and `learning_feedback.jsonl`. **2,838 lines of
  run artifacts were committed once before that rule existed**, and adding the rule did not untrack
  them — `.gitignore` only governs paths git is not already tracking, so it took `git rm --cached`.
- **A deploy tool that owns two trees can silently REVERT the other one.**
  `nt8-mcp-bridge/tools/deploy.py` deploys the bridge **and its vendored core**, so a submodule pin
  behind `nt8-riskguard` overwrites a newer live core with an older one. On 2026-08-12 the pin sat at
  `v1.0.1` while `v1.0.2` — carrying `P0-63`, without which the mirrored stop had never trailed — was
  live. **Nothing would have warned.** Now blocked: `deploy.py` exits 2 when the pinned commit is
  behind the sibling core's `main` **in `addons/`**. `--verify`/`--dry-run` are never blocked, a
  missing sibling checkout only warns, and being behind only in docs proceeds. **Keep the pin bumped
  whenever this repo's `addons/` moves**, and tag first — a submodule cannot resolve a tag that
  exists only locally.
  > **This guard was itself broken on arrival and shipped with a passing three-direction test** — it
  > asked the vendored clone, which cannot see commits it has not fetched, so it answered "not
  > behind" for the one case that matters. Then the fix over-fired on docs-only commits. Both are
  > written up in §5.10. **Two rounds of getting a nine-line check wrong is the strongest argument in
  > this file for watching a gate fail before trusting it.**
- **A gate that cannot fail is worse than no gate**, and this repo has shipped four of them. The
  mutation batteries printed `SURVIVORS: [...]` and exited **0** until 2026-08-12; then `mutate_cm3`
  and `mutate_cm4` were found to be **vacuous from a red baseline**, because `killed = 'Failed = 0'
  not in res` scores every mutant as killed when the baseline is already failing. All three now
  refuse to run unless the baseline is green (`mutate_p0_63.py` pins the failure *count*, since it
  was written against a deliberately red baseline). The predecessor loop had the same shape three
  times over (§3). **Watch a gate fail once before trusting it.**
  > And verify the verification: `python mutation/mutate_cm3.py | tail` reports **`tail`'s** exit
  > status, not the script's, so the fix looked like `exit=0` when it was really `exit=2`. Redirect
  > to a file and check `$?` on the script itself.
- **The test runner still exits non-zero on any failure**, which is correct, but it means a red
  suite masks nothing now that the mid-run exit is gone — read `RESULTS:` at the very end.
- **Never diff the NT8 tree without normalising line endings.** The repo is LF, the NT8 tree is
  CRLF. A plain `diff` reported 8216 changed lines on a 4108-line file that was byte-identical,
  and that false alarm was written into this handover as fact. Use `diff --strip-trailing-cr`;
  the sync script's hash now normalises.
- **Never put backups inside `bin/Custom/`.** NT8 compiles that tree *recursively*, so a folder
  of `.cs` backups produces duplicate-type errors. Use
  `Documents/NinjaTrader 8/_riskguard_backups/`.
- **Never sync to NT8 unscoped** — historical, and the shape still matters. In tvDownloadOHLC,
  `sync_nt8_strategies.py` without `--only addons` also pushed strategies and indicators; during the
  shadow deployment that would have installed 21 unrelated indicator files into a live NT8
  mid-session. **This repo's `tools/sync_nt8.py` owns only `addons/` and cannot do that**, and
  `--only addons` over there now exits 2 because there are no addon sources there any more. Use
  `tools/sync_nt8.py` here, `tools/deploy.py` in the bridge, and nothing else.
- **`nt_compile` and `nt_script_execute` both reload every AddOn.** Expect a few minutes of
  `SHUTDOWN`/`INITIALIZE` churn after compiling; it settles on its own. That churn is what
  exposed P1-37. `nt_script_execute` is also unreliable (`NT8 timeout`, `ECONNRESET`) — prefer
  `GET /api/riskguard/config` for live state.
- **`interventions.jsonl` grows without bound** — it reached 110 MB and was rotated on
  2026-08-07. Rotate it before a shadow session so the output is readable.
- **Resetting `ShadowSessionsCompleted` by hand: do NOT write `null`.** `LastShadowSessionDate` is a
  **non-nullable `DateTime`**. Json.NET throws converting `null` to it, `LoadPersistedState` catches
  that and logs `Failed to load persisted state`, and **the entire persisted state is discarded** —
  every account's PnL baseline and the locked-out list with it. Write `"0001-01-01T00:00:00"`. Both
  fields must move together (`P1-37`) or a restart re-counts the same session. An earlier revision of
  this handover carried the `null` version; it was caught by checking the C# field type, not by
  testing. Back the file up first, and verify the `AccountsData` entries survived.
  > **"NT8 closed" means "the AddOn is not loaded".** The reliable check is the bridge not answering
  > on `localhost:7890` — the listener starts at `State.Configure`. NT8 can sit at its login dialog
  > with the process running and no AddOn loaded.
- **`nt_riskguard_config` with no arguments POSTs an EMPTY BODY.** Before `P2-41` that one call
  flattened the entire live risk configuration to defaults while echoing your request back as
  `"applied"`. It merges now, but the habit stands: **GET, mutate, POST, GET, diff.** And
  `/api/copier/config` has **no GET at all** (§5.3), so the copier's live config cannot be inspected
  without writing to it.
- **Backticks in a `-m` commit message are executed by bash.** One message lost three fragments this
  way: a backticked span was run as command substitution, and a glob inside it expanded to `/` and
  tried to execute `/LICENSE.txt`. Use a single-quoted heredoc or `git commit -F file`. Heredocs have
  their own failure mode — a terminator that does not match means the command silently does nothing.
- 844 lines of WPF UI in `RiskGuardAddOn.cs` remain outside the test build (acceptable), as does
  `ReconcileFollowerPosition` (needs `Application.Current.Dispatcher`). If P2-24 wires that method
  up, it needs a dispatcher seam to stay testable.

---

## 4w. Session 13 record — 2026-08-11: the copier ratio converter, slice 1 of 3

**This is a FEATURE, not a defect fix.** No `P`-number: the hardening plan's IDs are
never reused, and nothing here closes one. Asked for by the user: *"a ratio
convertor for the copy trader where I can trade for e.g. one MES in one account,
but take 3 in a different account and 5 in another."*

### State

Two commits on `harden/riskguard-p0-51`, **unpushed**, on top of `86c6376f`:

* `36bd59f6` — CM1 acceptance tests, RED at baseline: 789 passed, **17 failed**
* `37cb5193` — the implementation: **806 passed, 0 failed**, build clean under net48
  + net8.0-with-stubs

**Not deployed. Not compiled in NT8. Not live-validated.** Unit + `dotnet build`
only. Before deploying, follow the NT8 sync rules in CLAUDE.md
(`sync_nt8_strategies.py --verify --only addons`, then `--only addons`, then
`nt_compile`) — do not hand-copy.

### What slice 1 changed

`CopierSizingMode.PerTickerMatrix` was declared at `TradeCopierEngine.cs:24` and
implemented **nowhere** — it fell through to the `QuantityRatio` branch. Four
defects followed, each now covered by a test that was red beforehand:

1. **The mini/micro multiplier was applied ON TOP of the table ratio.**
   `PerTickerRatios["MES"] = 3.0` with `AutoSymbolConversion = true` computed
   `round(1 * 3.0 * 0.1) = 0` — MES is in the micro list — and the sub-one-contract
   guard then silently skipped the entry. **The operator asked for 3 contracts and
   got none.**
2. **`TranslateSymbol` applied the same table independently**, routing an MES
   leader fill to **ES** on the follower while sizing it in MES contracts. The
   instrument decision and the quantity decision were made in two places from two
   different keys. That is the root defect, and it is the same shape as `P0-60`:
   two callers inferring different things from one fact.
3. **An unmapped instrument fell through to the flat `QuantityRatio`** — a silent
   unscaled copy. Observed: 1 contract from a configured ratio of 7.0.
4. **The lookup called `Math.Abs(tickerRatio)`**, so a configured **-3.0 would have
   become 3 live contracts.**

Now, inside matrix mode only: the branch is evaluated **first**; the ratio is the
literal contract count with no symbol multiplier; `NaN`, both infinities, zero,
negative, and anything rounding to zero are each treated as **no rule**; no rule
**fails closed on ENTRIES and never on exits**; and the leader's instrument is
preserved, with a cross-instrument `CustomSymbolMappings` entry **refused** rather
than approximated. Every other sizing mode is untouched.

### Settled here — do not re-litigate

* **The ratio is a contract COUNT in the follower's instrument, not a notional
  scaling.** `1 MNQ -> 3 MES` means three MES. The user chose this explicitly.
* **One rule is `(leader root -> follower root, ratio)`** — the instrument and the
  count are one decision, because deciding them separately is defect 2 above.
* **An unmapped instrument fails closed on entries, mirroring the existing
  `NetLiquidationRatio` guard.** The user chose this over falling back to auto
  conversion.
* **A no-rule EXIT mirrors `leaderQty` and lets the existing clamp cap it at the
  live position.** A reviewer raised twice that a partial leader exit can therefore
  flatten the follower completely. Accepted and documented in the code: on that path
  there is no ratio BY DEFINITION, and flat is safer than stranded.
* **`PerTickerRatios` needed no DTO work.** It already existed, was already
  deep-copied per follower by `CopierGroup.ToRelationships()`, and was already read
  by the sizing branch. A four-part plan that proposed re-creating all of that was
  discarded once the file was actually read.

### Still open — slices 2 and 3

* **Slice 2, cross-instrument** (`1 MNQ -> 3 MES`, `1 ES -> 2 MES`). Needs a rule
  type carrying the follower root, and must **replace** slice 1's deliberate
  refusal. Note `P1-22`'s rule survives: a cross-instrument mapping records **no
  slippage**, because the two price scales are incomparable.
* **Slice 3, reachability.** `PerTickerRatios` and `CustomSymbolMappings` are
  parsed by **nothing** and exposed by **nothing** — not by `LoadFromDisk`, not by
  the `McpBridgeAddOn` copier-config endpoint. So the table can still only be set
  from code or a test. This is the same "config that cannot be set" family as the
  fields `P1-23`/`P0-9` deleted. **Until slice 3 lands, the feature is not usable
  from the UI or the bridge.**

### Two constraints that will bite the next session

* **`McpBridgeAddOn.cs` and `RiskGuardAddOnTests.cs` cannot be edited by the agent
  loop at all.** Both contain C-style block comments, and `regions.py` refuses such
  files rather than risk its brace matcher. That makes slice 3's bridge half a
  hand-edit, and it is why slice 1's tests were hand-written.
* **`class Program` in the test harness is not `partial`, and `Assert` is private to
  it.** `TestHarness_AllDeclaredTestsAreInvoked` reflects only over
  `typeof(Program)`, so a test in a NEW file compiles and **runs nothing**. New
  tests must go into `RiskGuardAddOnTests.cs` and be registered in `Main`. The
  CM1 tests are at the end of that file, registered just before the self-check.

### The loop found thirteen of its own defects doing this

Slice 1 was produced by the agent loop (qwen3.5 implementer, glm-5.2 + minimax-m3
panel, deepseek-v4-pro arbiter) over three rounds — the gate ladder caught a
regression in round 1 that round 2 fixed. Getting there required fixing **O37-O50**
in the agent-loop package, now pinned at **v0.6.2**. The full account is
[agent-loop HANDOVER §13](file:///c:/Users/vinay/agent-loop/docs/architecture/HANDOVER.md).

**The one to carry into any future loop run on this addon:** the arbiter upheld
**0 of 66 findings** across four SHIP rulings, and on one plan the panel was right
about a signed exit quantity that would have **increased a follower position sitting
opposite the leader** — `P1-56`'s class, in a plan the arbiter shipped. Three of the
five human corrections to the CM1 ticket came from findings the arbiter had
dismissed. **Do not treat `ARBITER_SHIP` on this profile as a review.** Read the
patch against the file.

---

## 4x. Session 14 record — 2026-08-11: the copier ratio converter, slice 3a

> **THIS IS THE ADDON HANDOVER.** If you are working on the **agent-loop
> package** instead, read `C:\Users\vinay\agent-loop\docs\architecture\HANDOVER.md`
> §17. The two are not interchangeable: ten loop defects were closed the same
> day and none of them is recorded here.

**Still a FEATURE, not a defect fix.** No `P`-number. Slice 1 shipped in session
13; this is slice 3a.

### State

`harden/riskguard-p0-51`, **unpushed**, on top of session 13's `3b6478e8`:

| commit | what |
|---|---|
| `90933671` | CM2 acceptance tests, RED at baseline: 815 passed, **10 failed** |
| `62d1dc1b` | guard: one unreadable field must not discard the whole config (green at baseline) |
| `305fa4b9` | guard: a malformed number must not become a zero limit (green at baseline) |
| `1a210d7c` | **the implementation: 831 passed, 0 failed** |

**Not deployed. Not compiled in NT8. Not live-validated.** `dotnet build` +
suite only. Before deploying follow CLAUDE.md's NT8 rules —
`sync_nt8_strategies.py --verify --only addons`, then `--only addons`, then
`nt_compile` — and do not hand-copy.

### What slice 3a changed, and why it was bigger than session 13 thought

§4w recorded the problem as "`PerTickerRatios` is parsed by nothing". The real
shape is worse. `SaveToDisk` serialises each relationship and group **whole**,
with `JsonConvert.SerializeObject`, so every property reaches the file.
`LoadFromDisk` hand-parsed a remembered subset at **three** construction sites —
structured relationships, groups, and the flat legacy dictionary — and none read
`SizingMode`, `Mode`, `PerTickerRatios`, `CustomSymbolMappings` or
`StealthMode`. Only the relationship site read `MaxSlippageTicks`.

So the fields were **on disk, visible in the file, and looking set**, and loading
returned them to their defaults with no error. That is `P2-41`'s shape, not
"config that cannot be set". And `SizingMode` was among them, so slice 1's
`PerTickerMatrix` could not be selected by any means except editing C# and
recompiling.

All three sites now go through one alias map + reflective populate, with
`EnsureOrdinalIgnoreCase` re-applied to both dictionaries afterwards.

### Settled here — do not re-litigate

* **A malformed ENUM falls back to the default; a malformed NUMBER fails
  closed.** Tolerating an unrecognised enum name is not tolerating every
  deserialisation error. A blanket `Error` handler leaves a type-mismatched field
  at the CLR default — `MaxPositionSize` 0 instead of 100, `QuantityRatio` 0.0
  instead of 1.0 — and a zero cap sizes every fill at nothing, so the leader
  trades and the follower does not. **A review panel caught exactly this in a
  candidate that had already passed every mechanical gate**, and it is now
  pinned by a green-at-baseline test.
* **The camelCase aliases stay.** `leaderAccount` is a different NAME from
  `LeaderAccountName`, not a different case of it; Json.NET will not map it.
* **`ObjectCreationHandling.Replace` is still forbidden** (`P1-39`). It discards
  the property initialisers' `StringComparer.OrdinalIgnoreCase`.

### ⚠️ Applied by hand over a NOT_CONVERGING verdict — the reasoning

The loop produced a fully green candidate on rounds 2, 3 AND 4 and shipped none
of them. It stopped on thrash: blocking findings `0 -> 7 -> 10`, zero overlap.

**The leading 0 was false.** It is the loop's own O61 — a reviewer that
degenerated to 1,219 findings and was truncated before its closing marker parsed
as *zero* findings. The convergence history the detector ruled on was corrupted
by a defect fixed after the run.

**And the arbiter's five upheld findings do not survive checking.** Four are one
claim repeated: *"nested dictionaries inside `PerTickerRatios` lose their
comparer"*. `PerTickerRatios` is `Dictionary<string,double>` and
`CustomSymbolMappings` is `Dictionary<string,string>` — there are no nested
dictionaries, the candidate already calls `EnsureOrdinalIgnoreCase` on both, and
the acceptance test that reloads and matches `'mes'` against a stored `'MES'` is
green. The fifth was real but narrower than filed, and is now pinned by a test.

The loop's own stop message says what to do: *"arbitrate the findings by hand"*.
That is what happened, and this section is the record of it.

### Still open

* **Slice 3b — the bridge.** `McpBridgeAddOn.cs`'s `CopierConfig(body)` builds a
  `CopierGroup` from a hand-written field list: a **fourth** site with the same
  remembered subset, and the last thing between slice 1 and being settable from
  the UI. It is no longer a hand-edit — the loop's O53 fix means that file can be
  edited now.

  > **Session 15 correction — this understates it, and "add the six fields" is
  > the WRONG fix.** Three things found by reading the call path:
  >
  > 1. `UpsertGroup` (`TradeCopierEngine.cs:256`) and `UpsertRelationship`
  >    (`:139`) **remove the existing object and add the new one wholesale**.
  >    The bridge always constructs a *fresh* object, so every field the caller
  >    omits reverts to its CLR/initialiser default and is then written to disk
  >    by the `SaveToDisk` on the next line. A `set_group` carrying only
  >    `{groupName, quantityRatio}` therefore **destroys** the stored
  >    `PerTickerRatios`, `SizingMode`, `CustomSymbolMappings`, `StealthMode`
  >    and `MaxSlippageTicks`. That is data loss, not a missing feature — and
  >    completing the field list does not fix it, because the *next* omitted
  >    field is destroyed just the same. The fix is **merge semantics**: apply
  >    only the fields actually present in the request.
  > 2. Slice 3a's alias map, `NormalizeConfigObject`, `RemoveUnknownEnums` and
  >    `EnsureOrdinalIgnoreCase` are **local functions nested inside
  >    `LoadFromDisk`** (`:766`–`:905`). Nothing else can reach them. That is
  >    why the bridge hand-writes a field list: the machinery that would have
  >    made it unnecessary is trapped one scope down. Lifting them to statics
  >    removes the fourth remembered subset *structurally* rather than patching
  >    it — [[fix-the-class-not-the-instance]].
  > 3. `McpBridgeAddOn.cs` is `<Compile Remove>`d from `RiskGuardTests.csproj`
  >    (WPF deps). Anything left in that file can only be pinned by source-text
  >    regex, which is not evidence. The request→object mapping must move into
  >    `TradeCopierEngine` to be *executed* by the harness.
  >
  > So slice 3b is: lift the machinery (green at baseline), then add a merge
  > apply, then reduce the bridge to a call. Two regions, per the note below.
* **Slice 2 — cross-instrument** (`1 MNQ -> 3 MES`), which must REPLACE slice 1's
  deliberate refusal. `P1-22`'s rule survives: a cross-instrument mapping records
  no slippage.
* **Write slice 3b as TWO smaller regions.** CM2 was one 113-line region and took
  six attempts; the panel found new surface every round on a candidate that was
  already green.

### Everything in §4w's "two constraints that will bite" is now stale

* `McpBridgeAddOn.cs` and `RiskGuardAddOnTests.cs` **can** be edited by the loop
  (agent-loop O53). The block-comment refusal is gone.
* The `Program`-is-not-partial constraint **stands**: new tests still go into
  `RiskGuardAddOnTests.cs` and must be registered in `Main`, or they compile and
  run nothing. The CM2 tests are at the end of that file.

---

## 4y. Session 15 record — 2026-08-11: the copier ratio converter, slice 3b

**Slice 3b is done.** Still a FEATURE, no `P`-number. Read §4x's "Session 15
correction" block first — it says why "add the six missing fields" was the wrong
fix and this is not what §4x originally scoped.

### State

`harden/riskguard-p0-51`, **unpushed**, on top of session 14's `1a210d7c`:

| commit | what | suite |
|---|---|---|
| `373d34b4` | refactor: lift slice 3a's normalisation out of `LoadFromDisk` | 831 / 0 (unchanged) |
| `622f760c` | CM3 acceptance tests + verbatim move of the bridge mapping | 851 / **21 FAILED** |
| `33c0bfea` | the implementation: merge instead of rebuild | **889 / 0** |

**Not deployed. Not compiled in NT8. Not live-validated.** `dotnet build` +
suite only, exactly as slice 3a was left. Deploy per CLAUDE.md —
`sync_nt8_strategies.py --verify --only addons`, then `--only addons`, then
`nt_compile`. Do not hand-copy.

> ⚠️ **`McpBridgeAddOn.cs` is `<Compile Remove>`d from `RiskGuardTests.csproj`,
> so the two edits in that file have NEVER been through a compiler.** They are
> three lines each and were read back, but `nt_compile` is the first real check.
> Everything else in this slice is covered by the suite.

### What changed

The defect was not a short field list. `UpsertGroup`/`UpsertRelationship` remove
the existing object and add the new one wholesale, the bridge always built a
*fresh* object, and the next line is `SaveToDisk` — so a `set_group` carrying
`{groupName, quantityRatio}` wrote initialiser defaults over the stored config:

| field | stored | after a partial update, before this slice |
|---|---|---|
| `SizingMode` | `PerTickerMatrix` | `QuantityRatio` |
| `PerTickerRatios` | 2 entries | 0 |
| `CustomSymbolMappings` | 1 entry | 0 |
| `MaxSlippageTicks` | 2.5 | 0 |
| `MaxPositionSize` | 42 | 100 |
| `StealthMode` | false | true |
| `LeaderAccountName` | `Cm3Leader` | `Sim101` |
| `FollowerAccounts` | `[Cm3Follower]` | `[]` |

`ApplyGroupRequest`/`ApplyRelationshipRequest` now live on `TradeCopierEngine`,
start from what is stored, and apply only the keys **present** in the request.
The remembered subset is deleted, not extended — a fifth copy would have left
the next omitted field just as destroyed.

### Settled here — do not re-litigate

* **An explicit `null` means "not specified", not "wipe it".** Json.NET's
  default `NullValueHandling` *sets* the property to null, so a UI serialising
  untouched fields as null would null the ratio matrix and hand a
  `NullReferenceException` to whatever sizes the next fill.
* **A malformed NUMBER fails closed AND atomically.** Session 14 settled the
  first half. The merge runs against a defensive clone, so a request whose valid
  field precedes a bad one applies *neither* — without the clone the group is
  left in a state the caller never asked for and no longer knows about.
* **A malformed ENUM falls back without sinking the rest of the request.** One
  stale dropdown value must not refuse every edit sent alongside it.
* **Arming still requires `confirmLive`; a request that never mentions
  `armedForLive` leaves the stored value alone.** It has to — otherwise nudging
  a ratio on a live group silently stops it copying, which is `P0-9`'s shape
  from a new direction. An explicit `armedForLive:false` disarms without
  confirmation; refusing to disarm is not a safe default. Because the gate is
  decided in `ApplyArmingGate`, `Upsert*` is called with `confirmLive:true` so
  it does not re-apply its own gate and undo the preserved value. **This is the
  one decision in the slice that is a judgement call rather than a defect fix.**
* **Two inert lines were deleted rather than kept** — re-asserting `GroupName`
  and the relationship's account names after populate, where the lookup
  fallbacks are byte-identical to the initialiser defaults. The
  `EnsureOrdinalIgnoreCase` calls *look* equally inert (PopulateObject reuses the
  initialiser's dictionary instance) but catch a **stored** null, which
  `Upsert*` accepts, so they stay and are now covered on both sides.

### Mutation testing found what the tests missed — again

`mutation/mutate_cm3.py`, 11 mutants, **all killed**.
Three survived the first draft of the CM3 tests and are the reason four more
tests exist:

* **the defensive clone could be removed** — the malformed-request test used a
  request whose *only* field was malformed, so nothing could half-apply. Fixed
  by putting a valid field in front of the bad one.
* **unknown-enum stripping could be removed** — nothing sent a bad enum through
  the *request* path at all (only the load path).
* **the relationship's comparer guard could be removed** — the suite tested
  only the group half of a guard that exists twice.

Re-run it after any edit to `ApplyGroupRequest`/`ApplyRelationshipRequest`.
[[mutation-testing-beats-review]] holds for a third time on this addon.

### Known, deliberately not fixed

`set_group`/`set` do **not** `LoadFromDisk` first, so the merge starts from
in-memory state. `State.Configure` loads at startup and `SaveToDisk` runs on
every write, so memory is authoritative — but a config file edited **externally
while NT8 is running** will be overwritten by the next write, not merged with.
Pre-existing, and reloading before every write has its own failure mode
(discarding in-memory-only state), so it is left alone and recorded here.

### Still open

* **Slice 2 — cross-instrument** (`1 MNQ -> 3 MES`), which must REPLACE slice
  1's deliberate refusal. `P1-22`'s rule survives: a cross-instrument mapping
  records no slippage. This is now the last slice of the ratio converter.
* **Deploy and live-validate slices 3a and 3b together.** Neither has run in
  NT8. The bridge edits in particular have not been compiled.

---

## 4z. Session 15 record — 2026-08-12: slice 2, and the first LIVE validation

**The copier ratio converter is COMPLETE** — slices 1, 2, 3a, 3b. Still a
FEATURE, no `P`-number. **And for the first time it has been deployed,
compiled in NT8, and validated on the sim accounts.** Read §4y first.

### State

`harden/riskguard-p0-51`, **unpushed**:

| commit | what | suite |
|---|---|---|
| `894e27f7` | CM4 acceptance tests, RED | 907 / **6 FAILED** |
| `c8436062` | **slice 2**: cross-instrument matrix rules | 913 / 0 |
| (this) | **CM5 fix**: a named collection replaces the stored one | **929 / 0** |

**DEPLOYED.** `sync_nt8_strategies.py --only addons` then `nt_compile`:
**0 errors** (the CS0108 `Log` warning is pre-existing). The deployed build is
no longer session 12's `f174ba68`.

### What slice 2 changed

One rule is `(leader root -> follower root, ratio)`, **both halves keyed by the
LEADER root**:

```
CustomSymbolMappings["MNQ"] = "MES"   <- where it goes
PerTickerRatios["MNQ"]      = 3.0     <- how many
```

There is **no cross-instrument branch**. That is the design, not a tidy-up: a
separate branch is how the instrument and the quantity came to be decided from
two different keys in slice 1's defect 2. Three sites changed together, because
changing one alone is worse than changing neither — `TranslateSymbol` (stop
returning untranslated), the sizing branch (drop the refusal), and
`ResolveFollowerInstrument`.

**`ResolveFollowerInstrument` was a real defect, found by writing the test.** It
tested `AutoSymbolConversion` *before* consulting the mapping, while
`TranslateSymbol` — the actual copy path — honours an explicit mapping
regardless. With the flag off and a cross mapping set, the copy went to MES
while the bracket was computed against MNQ, and `ArePricesComparable(MNQ, MNQ)`
is true, so a leader stop distance in MNQ points would have been mirrored onto
an MES position as a **fabricated risk level** — exactly what `P1-22`'s guard
exists to prevent, reached by making one decision in two places.

### ⚠️ CM5 — slice 3b shipped a defect that only the sim run found

Merge semantics made every collection **append-only**. `PopulateObject` reuses
the existing dictionary *instance* (that is what preserves the comparer, and why
`P1-39` forbids `ObjectCreationHandling.Replace`) and merges keys **into** it.
Reproduced live through the bridge:

```
PerTickerRatios = {"MNQ": 3.0}
set perTickerRatios = {}        -> still {"MNQ": 3.0}
```

An operator could not remove a ticker rule, fix a typo'd mapping, or drop a
follower without deleting the whole relationship. **A ratio table you can only
add to is not a usable config surface** — the same "config that cannot be set"
family slice 3 existed to close, reintroduced by its own fix.

Rule now: **absent or null = unchanged; present = this IS the value, including
empty.** Resending the table without a ticker is how that ticker is removed.

### The live run — 2026-08-12 03:17 UTC, RiskGuard in `shadow`

Config set **entirely through the bridge** (`/api/copier/config`), which is
slice 3a+3b working: before them, every one of these fields was silently
dropped.

| step | result |
|---|---|
| set matrix + mapping via bridge | `SizingMode=4`, `{"MNQ":3.0}`, `{"MNQ":"MES"}` ✅ |
| partial update (`quantityRatio` only) | ratio applied, **everything else preserved** ✅ |
| `armedForLive:true` without `confirmLive` | refused ✅ |
| `armedForLive:true` with `confirmLive` | armed ✅ |
| unrelated edit afterwards | **did not disarm** ✅ |
| **buy 1 MNQ on Sim101** | Sim-ORB **1 MNQ**, SimCopy2 **3 MES** ✅ |
| sell 1 MNQ (exit) | SimCopy2 sold **3 MES**, all flat ✅ |
| `perTickerRatios:{}` after the CM5 fix | **cleared**, mappings untouched ✅ |

Leader fill `03:17:29.7587786` → follower order submitted `03:17:29.7952809`,
≈37 ms. Config was restored to its exact pre-test state afterwards.

### ⚠️ OPEN — P1-22's metrics did NOT produce a reading, and I could not prove why

`LatencyMs = 0` and `AvgSlippageTicks = 0` on **both** relationships after two
round trips, and no `SLIPPAGE_ON_EXIT` fired on the cross-instrument exit even
with `MaxSlippageTicks = 0.1` against a nominal ~87,778-tick price gap.

`ObserveFollowerFill` **is** reached (the `COPIER_EXEC_IS_FOLLOWER` log fires).
Two candidate causes, and the live evidence does not separate them:

* **(a)** `_pendingCopies.TryGetValue(exec.Order, ...)` misses, because it is
  keyed on the **Order reference** we cached — so no metrics run at all. This is
  the `P0-59`/`P3-30` shape *again*: one cached `Order` reference rather than
  enumerating what the broker holds.
* **(b)** It matches, but latency is rejected by the `>= 0 && < 600000` sanity
  bound because `exec.Time`'s `DateTimeKind` differs — which the code comment at
  the latency block explicitly warns about.

Under (b) `P1-22` is fine and slippage was correctly suppressed as incomparable.
Under (a) nothing measured anything and **`P1-22` is unverified on the live
path**. So: **slice 2 and slice 3b are live-validated; `P1-22` is NOT.** Do not
record it as validated on the strength of a zero. Next step is to log inside
`ObserveFollowerFill` on both the hit and the miss.

### ⚠️ There is NO UI for any of this, and the UI that exists is actively harmful

Asked at the end of session 15. `TradeCopierWindow.cs` (1,118 lines) is the WPF
window, and four separate problems sit in it. **None was introduced by slices
1–3b; all are pre-existing and all are still live.**

1. **`PerTickerMatrix` is not selectable.** Both sizing-mode combos
   (`:367`, `:459`) offer exactly `QuantityRatio` and `FixedLot`.
   `NetLiquidationRatio` and `AvailableCashPercent` are missing too.
2. **`PerTickerRatios`, `CustomSymbolMappings` and `MaxSlippageTicks` have no
   editor at all.** They appear only inside a read-only status string (`:799`,
   `:916`), and that string prints `SizingMode` and `AvgSlippageTicks` but never
   the table itself.
3. **The UI's save sites are a FIFTH and SIXTH remembered subset**
   (`:997`–`:1013` and `:1055`–`:1073`): build a fresh
   `CopierRelationship`/`CopierGroup` from a hand-written field list →
   `UpsertRelationship` (remove-and-replace) → `SaveToDisk`. **This is exactly
   the destructive pattern slice 3b deleted from the bridge.** Clicking
   Add/Update in the window would wipe `PerTickerRatios`,
   `CustomSymbolMappings`, `MaxSlippageTicks`, `Mode`, `DailyLossLimit` and
   `IsQuarantined` — including a matrix the bridge had just set.
4. **The UI persists to a DIFFERENT FILE than everything else reads.**

   | | path |
   |---|---|
   | UI (7 call sites) | `UserDataDir/CopierConfig.json` |
   | bridge + `State.Configure` startup load | `UserDataDir/RiskGuard/copier_config.json` |

   Both exist on this box with different timestamps and contents. And
   `TradeCopierWindow` **never calls `LoadFromDisk` at all** — it only saves. So
   the window edits shared in-memory singleton state, writes it somewhere
   nothing loads, and **every UI change is silently lost on the next NT8
   restart**, while the bridge's file wins.

Fixing 3 and 4 is the same move slice 3b already made: the window should call
`ApplyRelationshipRequest`/`ApplyGroupRequest` and the single `CopierConfigFile`
path, not hand-roll its own. Note `TradeCopierWindow.cs` is compiled into NT8
but, like `McpBridgeAddOn.cs`, is **not** in `RiskGuardTests.csproj` — so the
mapping must move onto the engine to be testable, exactly as in slice 3b.

**Until that is done, the ratio converter is reachable ONLY through the bridge**
(`/api/copier/config`), which is how it was validated. That is a real
limitation, not a documentation gap.

### Still open

* **The UI, above** — items 3 and 4 are defects, not missing features, and
  item 4 loses operator config on every restart. These deserve `P`-numbers.
* The `P1-22` question above — **do this before trusting any slippage number**.
* `P0-62`, still open (§4a).
* `main` untouched.

---

# 5. THE OPEN BACKLOG — authoritative as of 2026-08-13

> **This is the answer to "what is left?".** It supersedes §4a and the plan's inventory
> table, both of which had drifted out of agreement with themselves and with the entries
> they summarised. Everything below is re-derived from the per-defect entries, not copied
> forward — most recently on **2026-08-13**.
>
> **Nothing here is a new defect discovered by a new review.** It is the residue of
> sessions 1–17 plus what the live runs exposed.
>
> **Start at [§5.6](#56-order-of-work) for the order of work.**

## 5.0 The count, and how to check it

Three documents have carried three different totals (58, 62, 67) because each was
maintained by hand. So here is the derivation instead of the number — if you doubt it,
re-run the command rather than trusting the table.

```bash
# every defect ID that has an entry in the plan
grep -oE "^### ~?~?(P[0-9]\?*-[0-9]+)\." docs/RISKGUARD_COPIER_HARDENING_PLAN.md \
  | grep -oE "P[0-9?]+-[0-9]+" | sort -u | wc -l      # -> 64
```

| | Count | Which |
|---|---|---|
| Numbered entries in the plan | **68** | `P0-1`…`P0-9`, `P0-48`…`P0-51`, `P0-53`, `P0-55`, `P0-59`…`P0-63`, `P0-67`, **`P0-68`**, `P1-10`…`P1-23`, `P1-35`…`P1-37`, `P1-39`, `P1-40`, `P1-42`…`P1-45`, `P1-47`, `P1-52`, `P1-54`, `P1-56`, `P1-57`, **`P1-69`**, **`P1-70`**, **`P1-71`**, `P2-24`…`P2-29`, `P2-38`, `P2-41`, `P2-46`, `P2-58`, `P3-30`…`P3-34` |
| Awaiting a band letter | **3** | `P?-64`, `P?-65`, `P?-66` — §5.2. The *digits* are final and reserved; only the band is untriaged |
| **Total IDs** | **71** | 4 opened by the live validation, §5.13 |
| **Open** | **19** | the 17 in §5.1 + `P?-64`, `P?-65`. **`P?-66` closed 2026-08-13** |
| **Closed or superseded** | **52** | 68 − 17, plus `P?-66` |

`P0-62` counts as **resolved-by-supersession**, not fixed: `P0-63` subsumed it (the call
is a silent no-op for price *and* quantity, not a quantity-only refusal) and `P0-63` is
fixed. Numbers are **never reused and never renumbered** — `P0-64`…`P0-66` are held for
the three above, which is why `P0-67` is the newest ID despite being opened before they
were triaged.

## 5.1 Open defects, by band

| ID | What | Band | Notes |
|---|---|---|---|
| **`P0-68`** | **`nt_change_order` reports `"status": "modified"` when the provider ignored the change** — the FOURTH `Account.Change()` site, in the bridge, with none of `P0-63`'s detection | P0 | **NEW 2026-08-13, and now the highest open defect.** Reproduced in isolation, twice (§5.13). Anything trailing a stop through MCP silently does not move, and **the unchanged price is already in the response body** next to the success claim. Cheapest possible fix: apply `P0-63`'s settle-then-verify, or at minimum stop claiming success |
| **`P0-67`** | **`DynamicAtmManager` holds the THIRD `Account.Change()` call, and its cache records the price the broker refused** — so the trail latches at a stale value | P0 | Same root as `P0-63`, different call site; found by widening `P0-63`'s "Where" clause (§5.8). **Establish whether that path is live first** — the bridge drives it and tests none of it (`P2-27`). **Do this together with `P0-68`**: four sites, one root cause, and `P0-63` already contains the remedy |
| **`P1-69`** | **The copier's latency/slippage metrics are computed and then discarded** — in-memory only, never persisted, no read path | P1 | **NEW 2026-08-13.** The half of `P?-66` that does *not* close. Fix with the `GET` on `/api/copier/config` (§5.3) or the metrics stay invisible however well they are measured |
| **`P1-70`** | **`BRACKET_MODIFIED` writes a false success line to the audit log** before the provider settles, and is contradicted milliseconds later | P1 | **NEW 2026-08-13.** Not naked risk — the detection catches the underlying no-op — but a live audit log that asserts "no unprotected window" before it can know is how the last three sessions lost time |
| **`P1-71`** | **A named active relationship produced no order and left no diagnosable trace** (`SimCopy2`) — four unlogged exits in the copy loop | P1 | **NEW 2026-08-13.** `followerAcc == null` logs nothing; three `CanTrade`/`NO_GUARD` blocks log to the Output tab only, which no readable sink captures. Route them through `CopierLog` — the fix is mechanical and the payoff is that this class stops being invisible |
| `P1-57` | We would mirror another copier's mirror; the "not ours" test is a name substring | P1 | Live on this box: a third-party copier fans `Sim101 → Sim-ORB → {SimCopyTest1, SimCopy2}` copying names verbatim |
| `P1-13` | Guard evaluation on the WPF dispatcher — **threading half only** | P1 | The fail-open half is closed |
| `P2-24` | Written-but-never-called safety machinery | P2 | |
| `P2-25` | The news shield can never fire in production | P2 | |
| `P2-26` | Design-doc drift in `RiskGuardAddOn.md` | P2 | |
| `P2-27` | The riskiest code has zero coverage | P2 | **Half done.** `OnExecution` is covered now; `McpBridgeAddOn.cs` and `TradeCopierWindow.cs` are still excluded from `RiskGuardTests.csproj` |
| `P2-29` | Single-file size / complexity | P2 | |
| `P3-30` | Independent reconciler | P3 | **Copier half shipped + live-validated.** The **RiskGuard-side audit** and the **background timer** remain |
| `P3-31` | Expected-position ledger with reserve/rollback | P3 | The seam in `Reconcile` exists; the ledger does not. **Required BEFORE the timer** |
| `P3-32` | Follower risk anchored to the follower's own fill | P3 | **May be superseded by `P0-9`** — read before scheduling |
| `P3-33` | Replace the global lock on the hot path | P3 | |
| `P3-34` | Arm/shadow discipline extended to the copier | P3 | **The copier acts regardless of guard mode**; `shadow` restrains RiskGuard only |

**Closed since this section was created:** `P0-63` — fixed 2026-08-13 via remedy 3, **deployed in
`v1.0.2` and compiling clean**. The mirrored stop trails for the first time. It has never been
exercised against a real broker (§5.4), which remedy 3 was chosen to be correct in spite of.

## 5.2 Opened by the live runs — band letter still unassigned

**The digits are final and reserved; only the band is untriaged.** `P0-67` took the next free number
after these three were parked, so do not "fill the gap" — numbers are never reused. Triage the band
when one is scheduled.

| ID | What | Why it matters |
|---|---|---|
| **`P?-64`** | **The copier UI writes to a DIFFERENT FILE than everything else reads.** UI → `UserDataDir/CopierConfig.json` (7 call sites); bridge + `State.Configure` startup load → `UserDataDir/RiskGuard/copier_config.json`. `TradeCopierWindow` **never calls `LoadFromDisk`**. | **Every UI change is silently lost on the next NT8 restart.** Both files exist on this box with different contents. This is operator config vanishing without an error — `P2-41`'s shape. |
| **`P?-65`** | **`TradeCopierWindow`'s two save sites are a 5th and 6th remembered subset** (`:997`, `:1055`): fresh object → `UpsertRelationship` → `SaveToDisk`. | Exactly the destructive pattern slice 3b deleted from the bridge. Clicking Add/Update **wipes** `PerTickerRatios`, `CustomSymbolMappings`, `MaxSlippageTicks`, `Mode`, `DailyLossLimit`, `IsQuarantined`. |
| ~~**`P?-66`**~~ | ~~`P1-22`'s slippage/latency metrics produced NO reading on the live path~~ | ✅ **ANSWERED AND CLOSED 2026-08-13 by the live validation** (§5.13). The measurement was never broken: one 1-lot round trip produced `FILL_MEASURED` twice — `latency=142.86 ms, slippage=0 ticks` on the entry (a **true** zero, both legs filled at 29840.75) and `latency=314.21 ms, slippage=-4 ticks` on the exit, negative being *favourable*, which also confirmed the sign convention on live data. Neither suspect was the cause: no `FILL_NOT_MEASURED`, no `LATENCY_REJECTED`. **What was actually broken is the reporting**, and that is now `P1-69`: the figures are written to an in-memory relationship that nothing persists and no endpoint exposes, so every consumer reads 0. |

## 5.3 NEW — enhancements, not defects

| Item | What |
|---|---|
| **UI redesign** | The operator's own assessment: *"not very usable or professional enough"*. On top of `P?-64`/`P?-65`, `PerTickerMatrix` is not in either sizing-mode combo (`:367`, `:459`) and `PerTickerRatios`/`CustomSymbolMappings`/`MaxSlippageTicks` have **no editor at all** — they appear only in a read-only status string. **The ratio converter is reachable ONLY through the bridge today.** |
| **MCP wrapper gap** | `nt_copier_config` accepts only `leaderAccount`/`followerAccount`/`quantityRatio`/`autoConversion`. It cannot express `sizingMode`, `perTickerRatios`, `customSymbolMappings`, `maxSlippageTicks`, or any group action. Session 15 had to drive raw HTTP to `localhost:7890`, which `.agent/USER.md` asks agents not to do. **The preference is unfollowable until the wrapper is extended.** |
| **`/api/copier/config` has NO read** | Found 2026-08-13 while verifying live state for this pass. The route is **`Post(method, …)` only** (`McpBridgeAddOn.cs:524`), whereas `/api/riskguard/config` handles `GET` explicitly (`:536`). **So there is no way to inspect the live copier config without issuing a write.** That directly defeats the GET-mutate-POST-GET-diff discipline this project relies on (§7), and it is why `P?-66`'s live metrics could not simply be read off the box during this pass. Fix with the wrapper gap above: `return method == "GET" ? CopierConfig(null) : Post(…)`. |
| ~~**Repo split**~~ | ✅ **EXECUTED 2026-08-12** — §5.7. Two repos, both public: [nt8-riskguard](https://github.com/vinay-veerappa/nt8-riskguard) and [nt8-mcp-bridge](https://github.com/vinay-veerappa/nt8-mcp-bridge), the latter consuming the former as a submodule pinned to a tag. Record: [NT8_REPO_SPLIT_PLAN.md](NT8_REPO_SPLIT_PLAN.md). |
| ~~**Doc consolidation**~~ | ✅ **DONE 2026-08-13** — §5.12. The plan's inventory table is regenerated from the entries, the count is now *derived* rather than maintained (§5.0), and the sections that contradicted each other (§4a, the two §5s) are marked or renumbered. |

## 5.3a ✅ RESOLVED — the `sync_nt8_strategies.py` hardlink trap

**Both halves of this trap are closed. Re-verified 2026-08-13**; kept because the *shape* recurs and
because the resolution is what the current deploy rules are built on.

What it was: `mcp/ninjatrader-mcp/nt8-addon/McpBridgeAddOn.cs` was a **hardlink to the deployed NT8
file** (same inode, link count 2). Every `sync_nt8_strategies.py --only addons` run therefore dirtied
the `ninjatrader-mcp` repo with nobody editing it, and the change then looked like a hand-edit there.
The mirrored copy was found **15 hunks behind** the deployed file, only 2 of which were that
session's work.

| Half | Now |
|---|---|
| The hardlink | **Broken.** The two paths have different inodes and link count 1 each; the deployed file is written by `nt8-mcp-bridge/tools/deploy.py`, which copies. |
| `--only addons` | **Exits 2** in tvDownloadOHLC — there are no addon sources there any more, so the path that caused this cannot be driven. |
| The missing `.gitmodules` | **Added 2026-08-12**, reconstructed from each checkout's own `origin`. `git submodule status` lists all five gitlinks instead of erroring, and a fresh clone can initialise them. |

**The durable rule, which now has teeth:** a copy of an addon that tracks what is *deployed* rather
than what is *canonical* is a trap regardless of how it is linked, because deploy tools write to it.
That is the same failure as a stale submodule pin overwriting a newer live core, and it is why
`deploy.py` refuses on a stale pin (§8) rather than trusting anyone to remember.

## 5.4 ⚠️ Still open on the operator, not on engineering

**Two questions remain that only the account holder can settle. Neither blocks work.**

1. **Is `Account.Change()` honoured on the funded accounts?** Every account validated on so far is
   `provider: Simulator`. The funded accounts are `Provider31` and were `Disconnected`. If `Change()`
   is honoured there, the trail works in production and only our *testing* ever misled us; if not, it
   was broken everywhere. Establishing it means **placing a real order on a funded account**.
   > **Deliberately still open**, and `P0-63` shipped anyway: remedy 3 — verify the settled order took
   > the new values, fall back to cancel-then-create when it did not — **is correct under either
   > answer**. That is exactly why it was the chosen remedy (§5.5). The question is now a
   > *nice-to-know*, not a blocker.
2. ~~**A live copy has to run for `P?-66` to answer anything.**~~ ✅ **DONE 2026-08-13 — §5.13.** The
   operator authorised it and it ran exactly as scripted here: `FILL_MEASURED` with real numbers, and
   `BRACKET_STOP_CHANGE_IGNORED` followed by a replacement at the right price. **The prediction
   written in this item was correct in every particular**, which is the strongest evidence in the file
   that the instrumentation was designed against the right question.
   > Two footnotes for whoever books the next one. **`shadow` is what made it survivable** — the guard
   > logged `MISSING_STOP_FLATTEN` twice and, armed, would have flattened the position and destroyed
   > the test rather than the defect. And **the "three follower accounts" warning did not
   > materialise**: only `Sim-ORB` acted, `SimCopyTest1` got nothing because the third-party copier
   > was not running, and `SimCopy2` was named as active and then silently dropped — which is now
   > `P1-71`. Do not assume today's blast radius next time; re-measure it.

## 5.5 DECIDED by the operator, 2026-08-12 — do not re-litigate

| Question | Decision | Status |
|---|---|---|
| Where the redesigned UI lives | **Rewrite `TradeCopierWindow.cs` properly, in NT8.** Not the web app. The window stays offline-capable and no new surface is added. | Not started |
| `P0-63` remedy | **Remedy 3 only** — after every `Change()`, read the order back and fall back to cancel-then-create when it did not take. **No funded-account order.** The `Provider31` question stays open on purpose; remedy 3 is correct either way. | ✅ **Shipped and deployed 2026-08-13** exactly as decided. One refinement forced by the evidence: the read-back must happen **on settle**, not synchronously — NT8 leaves the caller's desired values on the `Order` until the provider settles, so an immediate read always says "it took" (§5.9). |
| What the next session opens with | **`P0-63` + the `P?-66` log line.** Safety first: the trail has never worked and no slippage number currently means anything. | ✅ **Both done** — session 17. Superseded by §5.6, which now opens with `P0-67`. |

⚠️ **Consequence of the WPF decision, and it is the same trap as slice 3b:**
`TradeCopierWindow.cs` is **excluded from `RiskGuardTests.csproj`** (as are
`McpBridgeAddOn.cs` and `RiskManagerAddOn.cs`). So the rewrite must **not** put
request→object mapping in the window. Move it onto `TradeCopierEngine` — the window
should call `ApplyGroupRequest`/`ApplyRelationshipRequest` and the single
`CopierConfigFile`, exactly as the bridge now does. Anything left in the window can only
be pinned by source-text regex, which is not evidence. That single move closes `P?-64`
and `P?-65` together and makes the redesign testable.

## 5.6 Order of work

**Updated 2026-08-13.** Items 1 and 2 of the previous ordering (`P0-63`, `P?-66`) are done and
deployed; everything else shifts up unchanged.

0. ~~**Live-validate what is already deployed**~~ ✅ **DONE 2026-08-13 — §5.13.** `P0-63` trails on a
   real broker path; `P?-66` is answered and closed. It cost one 1-lot MNQ round trip and produced
   four new defects, which is the return this project keeps getting from a live trade over a test.
1. **`P0-68` + `P0-67` together** ← **the next code work.** They are the **third and fourth**
   `Account.Change()` call sites and they share `P0-63`'s root cause, so fix them as one change and
   reuse the settle-then-verify that is already written and now live-proven. `P0-68` first: it is
   reproducible in ten seconds with no position, and until it is fixed **no agent or strategy can
   trail a stop through MCP** — the call reports success and does nothing. For `P0-67`, establish
   whether the `DynamicAtmManager` path is live at all; if it is dead code, say so and close it.
2. **`P1-71`** — route the copy loop's four silent exits through `CopierLog`. Mechanical, and it is
   what turns "SimCopy2 got nothing and we cannot say why" into a one-line answer. Do it **before**
   the next live test, so the next silence is diagnosable.
3. **`P?-64` + `P?-65` together.** Same fix, same shape as slice 3b: point the window at
   `ApplyRelationshipRequest`/`ApplyGroupRequest` and the single `CopierConfigFile`. Doing 64
   without 65 leaves a UI that persists correctly and destroys the payload on the way.
4. **MCP wrapper + the `GET` on `/api/copier/config`** (§5.3), which is what makes 5 testable the way
   this repo prefers. **Fold `P1-69` into this**: the read path and the persistence are the same
   problem, and a measured slippage figure nobody can read is worth exactly zero.
5. **UI redesign**, on top of a UI that no longer loses or destroys config.
6. Then `P3-31` ledger → timer → RiskGuard-side audit (`P3-30`'s remaining half), in that order.
   **The ledger comes BEFORE the timer** — between `Submit` and `Accepted` an order is in neither
   `Account.Orders` nor the cache, so a timer alone creates the second leg.

`P1-57`, `P1-13`, and the `P2` band are real but none is naked-risk; schedule them after the above.

> **Two suite gaps are worth closing alongside whatever comes next**, both recorded in
> `mutation/mutate_p0_63.py` beside the mutants that measured them: an S7-style concurrency test for
> the `SyncFollowerStop`-vs-`...Once` reservation (the most serious defect found in the `P0-63`
> candidate, and unpinnable today), and a `SimulateChangeAppliesQuantityOnly` stub flag for the
> partial-honour case. Neither is naked-risk; both are places where the suite currently cannot fail.

## 5.7 Session 16 record — 2026-08-12: the repo split executed, and what it exposed

**The split went first**, per the **split plan's** §8 choice between the two defensible orders (not
this file's §8, which is Known traps — the collision is why §7/§8 were renumbered). The reason to
prefer it: every commit made after the split lands in the new repos already, so the `P0-63`
work does not have to be migrated afterwards. Nothing about `P0-63` changed; §5.5 and §5.6
stand exactly as written, and **the next session still opens with `P0-63` remedy 3 + the
`P?-66` log line**.

Where things are now:

| | |
|---|---|
| This repo | [nt8-riskguard](https://github.com/vinay-veerappa/nt8-riskguard), public, **162 commits**, tagged `v1.0.0` |
| The bridge | [nt8-mcp-bridge](https://github.com/vinay-veerappa/nt8-mcp-bridge), public, 34 commits, vendors this repo at `vendor/nt8-riskguard` pinned to `v1.0.0` |
| `tvDownloadOHLC` | keeps no addon source, no csproj, no tickets, no addons sync path. Its `CLAUDE.md` holds a pointer |
| Suite | **926 passed / 0 failed** (was 929 — see below), `mutate_cm3` 14 killed, `mutate_cm4` 10 killed, no survivors |
| Deploy parity | all 8 deployed addon sources verified identical to the live NT8 tree after the move |

### Five things worth carrying forward

**1. `git subtree split` would have thrown away history it was chosen to preserve.** The
addon lineage spans three paths — `ninjatrader-addon/` → `scripts/strategies/nt8/addons/`
(`671d8a18`) → `scripts/ninjatrader/addons/` (`a19c2adc`) — and subtree follows neither
renames nor anything outside its single `-P` path. Used `git-filter-repo` with a
`--commit-callback` instead.

**2. Collapsing those three paths silently deleted two files, and reported success.**
`a19c2adc` *copied* the addons to the new path without deleting the old ones; the stale
duplicates were tidied up later by unrelated commits (`671d8a18`, `b8f410f4`). Mapped onto
one target, those cleanups delete the **live** file. It cost `RiskManagerAddOn.cs` and
`TradeCopierWindow.cs` — precisely the two files no later commit happened to rewrite, so
nothing resurrected them. **Only a blob-level diff of every migrated path against the source
catches this.** If either addon repo is ever re-extracted, run that diff.

**3. The suite depended on the bridge, which is the one direction the split forbids.**
`TestP2_38` regex-asserted on `McpBridgeAddOn.cs`'s source text. Its three source assertions
moved to `nt8-mcp-bridge/tests/BridgeSourceTests.cs`; the behavioural half — that the shared
classifier gets `SimpsonFund` right — stayed here. **That is the whole of the 929 → 926
change.** `tools/check_direction.py` now fails the build if a core source names a
bridge-owned type (comments excepted; four of them explain why code sits on this side).

**4. Both mutation batteries were a lying gate.** They printed `SURVIVORS: [...]` and exited
**0** regardless, so any CI step running them was a green light that proved nothing — the
same shape the batteries exist to catch. They now exit 1 when anything survives, an
unappliable ANCHOR included. Verified in both directions.

**5. `P2-27`'s bridge half is now measured, not just open.** §5 of the split plan feared the
split would bless the bridge's untestability. It is instead quantified: compiling
`McpBridgeAddOn.cs` against the vendored core gives **330 errors / 23 distinct missing
types**. Two useful results — **WPF is not the blocker** (`net8.0-windows` + `UseWPF` supplies
every WPF type it touches, so the WPF/HTTP separation the plan proposed is unnecessary), and
**16 of 19 missing types are already stubbed** inside this repo's 663 KB
`tests/RiskGuardAddOnTests.cs`, unreachable from there only because that file owns a
`Main()`. So the first step is a move, not new code: **extract the NT8 stub block out of
`RiskGuardAddOnTests.cs` into `tests/TestingStubs.cs`**, then re-verify 926 + both batteries,
tag, and re-pin the submodule. Duplicating the stubs on the bridge side instead would create
two definitions that drift, which is exactly what `P2-38` was. Ordered remedy:
`nt8-mcp-bridge/tests/README.md`.

### Two loose ends, neither naked-risk

* ~~**CI is parked.**~~ ✅ **Both activated 2026-08-13** — §5.11. The diagnosis here was right
  (the OAuth token lacks `workflow`) but the prescribed fix was not the one used: an **SSH
  push is not an OAuth App push**, so the restriction never applied to it.
* **Two stale files sit in the live NT8 `AddOns/` folder**: `RiskGuardAddOnTests.cs` and
  `TestingStubs.cs`. The old flat layout deployed the test suite into the trading assembly
  because the sync tool globbed `*.cs` from a directory that held both. The new tools
  correctly do not. Deleting them from the NT8 folder is a one-line manual step, deliberately
  left to the operator rather than done by a script reaching into a live install.

---

## 5.8 Session 17 — 2026-08-13: `P0-63` and `P?-66`, and four things found on the way in

Opened on §5.6's item 1 and item 2, as §5.5 directed. Both were driven through the agent loop
with the acceptance tests written **by hand first** and red at baseline, per §6.0.

### The loop could not start in this repo, and had not been able to since the split

`agent/__init__.py` still carried `from .python_tvdownloadohlc import PYTHON_TVDOWNLOADOHLC`,
inherited from tvDownloadOHLC's `scripts/agent_loop_config/__init__.py`. That profile stayed
behind with the Python code it describes, so importing the package raised
`ModuleNotFoundError` and **every** `--profile-module agent.nt8_riskguard` invocation died at
import.

Session 16's verification covered the suite, both mutation batteries, deploy parity and a
fresh clone of each repo — and none of that touches the loop. `--list` is free, takes two
seconds, and catches it; it belongs in CI. **The general lesson: a split's verification has to
include starting every tool that was moved, not just the ones that produce the artifact you
were looking at.**

Also repathed §0's `Commands` block, which still named `scripts\utils\sync_nt8_strategies.py
--only addons` and `-m scripts.agent_loop.selftest`. Neither exists here — the first is
tvDownloadOHLC's tool, whose addon half now exits 2, and the second was an entry point into
the archived predecessor loop.

### The test double could not express `P0-63` at all

This is why 926 tests passed while the mirrored stop had never trailed once, and it is worth
stating precisely because the shape recurs.

`Account.Change()` is a **request**. The caller writes the desired values onto the `Order`
object, and `Change()` asks the provider to honour them; the provider then either applies them
or leaves the order at the values **it** holds. The stub kept no provider-side copy of those
fields, so the caller's own writes were the only thing a test could ever read back — every
`Change()` "worked" by construction, and no test could have failed.

The stub now holds the provider's copy, captured at `Submit` and at an honoured `Change`, with
`ProviderStopPrice(order)` exposing it. **That is the only honest thing to assert on.**
`order.StopPrice` is just what we asked for; a test that reads it back is testing our own
assignment statement. Both `P0-63` acceptance tests assert against the provider's value, and
the second one is what discriminates the three candidate implementations from each other.

One deliberate design choice in the double: the revert is applied by a new `SettleChange(order)`
and **not** inside `Change()`. Live, the order is still carrying the desired values on the line
after `Change()` returns — the revert arrives with the settle event. A stub that reverted
synchronously would let a synchronous read-back pass the suite and still fail live, which is
the worst available outcome. **A double has to make the wrong fix fail, not just let the right
one pass.** Same lesson as the six `OrderState`s this stub used to omit.

### `P0-63`'s "Where" clause was short by one call site — now `P0-67`

Found by grepping `.Change(` across `addons/` instead of trusting the plan's prose, which named
the two copier leg syncs and `McpBridgeAddOn.ChangeOrder`. The third is
`DynamicAtmManager.ModifyStopPrice` (`addons/DynamicAtmManager.cs:622`), and its consequences
are **worse** than the copier's, for reasons specific to that file:

* every call site writes the refused price into `bracket.CurrentStopPrice` **unconditionally**,
  so the cache holds a value no order anywhere has;
* the trail's own gate compares against that field, so the manager believes it has already
  trailed and **latches** — the ATM stop sits at its original price for the whole trade while
  the cached state claims otherwise;
* `BreakevenTriggered = true` is set after the same unchecked call, making a refused breakeven
  move **permanent**.

Plus two more in the same 18-line method: it keys on `order.OrderId`, the one place left that
identifies a protective leg by id, and it requires the literal state `OrderState.Working`, so a
stop at `TriggerPending` — *the most protective state a stop can be in* — is skipped in
silence while `AcceptsModification` exists to answer exactly that question.

**Deliberately out of scope for `P0-63`'s ticket**, because it has no settle hook and no
per-leg pending-request state to hang a read-back on; bolting the copier's fix on would have
been the wrong shape. Full entry and ordered remedy in the plan. **First establish whether the
path is live at all** — `DynamicAtmManager` is driven by `nt8-mcp-bridge`, whose harness
executes none of it (`P2-27`), so it may be dormant rather than dangerous.

### `P?-64` is no longer an inference — it is measured, with timestamps

§5.2 recorded that the UI and the bridge use different files and that "both files exist on this
box with different contents". They now have numbers:

| | Path | Written by | mtime | Both relationships |
|---|---|---|---|---|
| **Live** | `<UserDataDir>/RiskGuard/copier_config.json` | `McpBridgeAddOn.cs:3600`, and the startup load at `:245` | **2026-08-11 20:27** | `IsEnabled: true` |
| **Orphan** | `<UserDataDir>/CopierConfig.json` | `TradeCopierWindow.cs`, 7 call sites | **2026-08-04 20:15** | `IsEnabled: false` |

The bridge's path is the one `LoadFromDisk` is called with at startup, so it is authoritative.
**Every change made in the NT8 window since 2026-08-04 has been written to a file nothing
reads, and discarded at the next restart** — and the two files disagree about whether the
copier is enabled at all. This does not change §5.6's ordering, but it does mean item 3 is
config loss that has already happened, not a hazard that might.

### One `P?-66` hypothesis ruled out before spending a ticket on it

§5.2 offered two candidate causes. The first — that `rel` fails to resolve because a
group-derived relationship is a fresh object from `ToRelationships()` — **is not the live
cause**: the live config has `Groups: {}` and two direct entries under `Relationships`, so
`_relationships` does contain the pair. That leaves the pending-map miss and the latency sanity
bound, which is what the instrumentation is there to separate. Recorded so the next reader does
not re-derive it.

### The regression guard earned its keep on round 1, and the reason is worth keeping

Round 1's candidate made **both** `P0-63` acceptance tests pass and broke
`TestBracket_P0_63_AnHonouredChangeStillModifiesInPlace`. That guard is green at baseline and
exists solely to stop the fix becoming *remedy 1* — always cancel-then-create — which passes
every test about trailing while silently reopening the naked window on the risk leg that §4o
closed. **Two acceptance tests plus no guard would have shipped the wrong remedy under the
right ticket number.**

Then the more interesting part: the candidate was not actually remedy 1. Its shape was right —
it recorded the requested price on the bracket, verified on the settle event, and kept an
account-level set of providers known to ignore `Change()`. It failed because **that set is
session-scoped and nothing cleared it, so it leaked between tests.** One earlier test provokes
a no-op, the follower account is marked, and every later test in the file inherits that
verdict. The guard was reading the previous test's state.

Session-scoped is the *correct* production behaviour and must not be weakened to make the guard
pass. The fix is that `ResetBracketsForTest` has to clear it, which meant **adding that method
to the ticket's editable regions** — round 2 could not have fixed it otherwise, because the
method was outside the region set, so it would have been forced to either thrash or weaken the
bypass. Recognising that and restarting with the region added cost one round; letting it run
would have cost several and might have landed the weakening.

**The general rule: any new session-scoped state in the engine has to join the existing
`*ForTest` reset, or it becomes a landmine under every later test.** The same is true of a
`--list` region set: if the ticket's spec implies touching a method, that method has to be in
`regions`, or the loop is being asked for something it cannot deliver.

### Both mutation batteries were vacuous whenever the baseline was red — now they refuse to run

`mutate_cm3.py` and `mutate_cm4.py` score a mutant with
`killed = 'Failed = 0' not in res`. That is correct **only from a green baseline**. With any
pre-existing failure, every mutant scores `KILLED` whether or not the suite detected it, and the
battery reports a clean sweep having tested nothing.

This is reachable in ordinary use, not a corner case: **test-first work leaves acceptance tests
red by design**, and running a battery in that window is exactly when you would most want
reassurance. Found here with the 8 `P0-63`/`P?-66` assertions red — both batteries would have
reported 14 and 10 killed, and both would have been lying.

Both now check the baseline first and **exit 2** with an explanation if it is not green. Verified
in both directions, and note that verifying it needs care: `python mutation/mutate_cm3.py | tail`
reports *tail's* exit status, so the first check of the fix read `exit=0` and looked like the gate
had not worked. Redirect to a file and read `$?` directly.

This is the third time a gate in this repo has turned out to prove nothing — after the batteries
exiting 0 on survivors (2026-08-12) and `test_version_alignment` raising `FileNotFoundError`
instead of asserting. **When a check passes, establish that it can fail before believing it.**

---

## 5.9 What shipped in session 17, and what it cost

**Both items §5.6 named are done.** `P0-63` is fixed via remedy 3 and `P?-66` is instrumented.
Suite **926 → 953 / 0 failed**. Three mutation batteries, **31 mutants killed, no survivors**. Both
structural checks green. **Neither is deployed** — `tools/sync_nt8.py --verify` reports
`TradeCopierEngine.cs` as the only drift, which is exactly this work.

### The loop produced the code; it did not decide what shipped

Neither ticket ended in a promotable verdict, and both were arbitrated by hand — which the loop
itself asked for.

`P0-63` ran to **`NOT_CONVERGING`**: *blocking findings 4 → 5 → 7 with zero overlap between
consecutive rounds*, and its own diagnosis was that each revision was exposing new surface rather
than closing the defect. That was correct, and the numbers show it: across four rounds the patch
grew **755 → 899 lines while the acceptance tests stayed identically green**, accreting three
budget refreshes and ten clear-points for the request record. Defensive state, added to answer
review, pinned by nothing.

`P?-66` ran to **`MAX_ROUNDS_EXHAUSTED`** — rounds 2 and 3 both reached 950/0 with every
acceptance test green; round 4 broke the build, so round 3 was exported.

**Read the panel composition before reading the verdicts.** Every blocking verdict on `P0-63`'s
later rounds came from `deepseek-v4-flash`, which the package catalogue lists as
`suited=('compactor',)` — **not a reviewer**. `glm-5.2`, the only catalogued reviewer, returned
**APPROVE with zero findings on three consecutive rounds**. On one earlier round deepseek emitted
**170 findings against a cap of 60**, which the loop correctly refused as "repetition, not review".
A second panel member from a different family is the policy; a second member the catalogue does not
recommend for the job is a configuration accident worth fixing.

### Mutation testing decided what was load-bearing, and it beat four rounds of review

`mutation/mutate_p0_63.py` was written to answer one question: which of those 424 changed lines can
the suite actually tell the absence of?

* **All three budget refreshes were decorative.** Deleting each changed no test outcome. They were
  added to chase a finding that is false — `OnLeaderOrderUpdate` already zeroes the budget whenever
  the leader's offset changes, which is every trail step. All three deleted; the new six-step trail
  test pins the behaviour they were meant to protect.
* **It found a real hole four review rounds missed.** Forcing the detection to fire *always* left
  every test green. A spurious detection is self-limiting for the current step — the re-drive is a
  reconcile and finds the leg already correct — but it **marks the account for the session**,
  silently downgrading every later trail step to cancel-then-create. One honoured step could not see
  that. The guard now drives two, and the mutant dies.

**The lesson, stated plainly: on this codebase a mutation battery is worth more than a review
round, and it is cheaper.** Four rounds of panel review produced 4→5→7 non-overlapping findings and
one real defect; one battery produced seven kills, three deletions and a coverage hole nobody saw.

### The claim the panel escalated on was false, and the repo already contained the refutation

An earlier `P0-63` run ended `ESCALATED` on the finding that **NT8 leaves the desired values on the
`Order` object**, so no read-back could ever detect a no-op — i.e. that the stub encodes a false
model and the fix is theatre. The arbiter's whole rationale rested on it.

The live trace in `AcceptsModification`'s docstring, the basis of `P0-61`, says otherwise: an order
settling to `Working` read back its **original** quantity and price. `P0-63`'s probe table says it
three more times, and stop `34410` was created at 29753.5, logged `stop moved to 1@29754.5`, and
ended at 29753.5. The trace is now quoted in the stub itself and in the ticket context, so the next
panel sees the evidence rather than reasoning about NT8 internals.

**Do not take a reviewer's model of an external system over a recorded trace of it.**

### Two known gaps, in the SUITE rather than in the fix

Both are recorded in `mutation/mutate_p0_63.py` beside the mutants that measured them, and both are
deliberate rather than overlooked:

1. **The wrapper-vs-`Once` distinction is unpinnable here.** That the re-drive must go through
   `SyncFollowerStop` — whose only job is to take `P1-56`'s in-flight reservation — was the most
   serious defect in the candidate, and **no reviewer found it**; it was caught by reading. Nothing
   in the suite drives two syncs concurrently through the settle path, so the mutant survives.
   Closing it means an S7-style test that parks one sync inside `CreateOrder` and drives a settle
   from another thread.
2. **The quantity half of the detection guards a PARTIAL honour** — the provider applying the
   quantity but not the price — which the stub cannot express because it is all-or-nothing. Remedy:
   a `SimulateChangeAppliesQuantityOnly` flag. Consequence if wrong is bounded: one unnecessary
   cancel-then-create.

### Three infrastructure notes, because four "failures" were not about the code

* **Ollama auto-updated itself 0.32.7 → 0.32.9 mid-session**, shutting the server down and opening a
  GUI installer. Two runs died `IMPLEMENTER_UNREACHABLE` (`WinError 10061`) either side of it.
* **`ollama serve` started from inside a tool call dies with that call.** Start it detached.
* **`think=true` on the implementer exhausted its whole budget on reasoning** — 408,089 chars,
  **empty content**, `done_reason=length` — once the ticket grew a hardened spec and a long
  orchestrator note. This repo now carries `agent_loop.config.json` setting `think: false` for that
  role. It is the same failure that once justified raising the role 48000 → 96000, at 3.3× the
  scale, and the package's own advice is to turn thinking off before raising the ceiling again
  because reasoning expands to fill whatever it is given. Every round since has returned a complete
  patch.

### Next

> **Superseded by §5.6.** Item 1 below — deploy — was done later the same day (§5.10). The rest is
> unchanged: **live validation, then `P0-67`.**

1. ✅ **Deploy.** Done 2026-08-13: `sync_nt8.py` 7/7 identical, `nt_compile` **0 errors**, ledger
   `ARMED_ON_START` at 12:58:05Z, copier `loaded: true, enforcing: true`. Tagged `v1.0.2`.
   **Live validation is still outstanding** — `P0-63` has never been exercised against a real broker,
   and `P?-66`'s instrumentation only answers its question once a live copy runs through it, so
   **`P?-66` is still unanswered, just no longer invisible.**
2. **`P0-67`** — the third `Change()` site, in `DynamicAtmManager`, where the cache records the price
   the broker refused and the trail therefore latches. Establish whether that path is live first.
3. Then §5.6's remaining items: `P?-64` + `P?-65` together, the MCP wrapper, the UI redesign,
   then `P3-31`.

---

## 5.10 Session 18 record — 2026-08-13: deploy, the sync rule made mechanical, and this doc pass

**No addon code changed.** Three things happened: `v1.0.2` went live, the "keep the bridge and the
core in sync" rule stopped depending on memory, and this document was re-derived from the repo.

### What was deployed, and the regression trap that surfaced doing it

`sync_nt8.py` reported 7/7 identical, `nt_compile` returned **0 errors**, and the guard came back
`ARMED_ON_START` in `shadow` with the copier `loaded: true, enforcing: true`. `main` was
fast-forwarded, tagged **`v1.0.2`** and pushed.

Then the standing instruction — *"always keep the mcp and the addons in sync"* — turned out to be
protecting against something sharper than untidiness. `nt8-mcp-bridge`'s vendored core was pinned at
**`v1.0.1`**, 10 commits behind and **without the `P0-63` fix**, and `deploy.py` deploys the core as
well as the bridge. Running it would have **overwritten the live core with the pre-fix version and
silently reverted a P0** on a live trading system.

The order matters and is not obvious: **the tag must be pushed before the submodule can pin to it.**

| # | Step | Result |
|---|---|---|
| 1 | core: `main` ← `harden/p0-63`, ff-only | `978ed3a` |
| 2 | tag `v1.0.2`, push `main` **and** the tag | `[new tag] v1.0.2` |
| 3 | bridge: fetch tags, check the submodule out at `v1.0.2` | pin now carries `_accountsIgnoringChange` (0 → 6 occurrences) |
| 4 | bridge harness against the new core | **9 / 0** |
| 5 | commit + push the pin bump | `74b76cf` |
| 6 | `deploy.py --verify` | **ALL IN SYNC** (8 files, 2 orphans) |

**Fix the class, not the instance:** `deploy.py` now **refuses to deploy a vendored core that is
behind the sibling checkout** (exit 2, remedy printed). Local check, no network — it asks git whether
the pinned commit is a *strict ancestor* of `nt8-riskguard`'s `main`, because strictly-behind is the
only unsafe case. No sibling checkout only warns; refusing on "I could not tell" would make the tool
unusable on a machine that has just the bridge.

> ⚠️ **That guard was broken on arrival, and its own "verified in three directions" is why it took a
> day to notice.** It ran `merge-base --is-ancestor` inside the **vendored clone** — a submodule
> checkout that only fetches when told to, so it does not know commits the core has made since the
> last bump. `--is-ancestor` against an unresolvable revision **exits non-zero**, and the code read
> any non-zero as "not an ancestor", i.e. *not behind*. **The guard therefore inverted in exactly the
> case it exists for.** The original three-direction test passed only because the vendor happened to
> have fetched the newer tag during it. **A guard verified under a condition you have not isolated is
> not verified** — this is §5.12's lesson 2 again, one day later, in code I had just written.
>
> Found by watching it pass when it should have failed: the core took a docs-only commit and
> `--dry-run` still said "not behind". Now it asks the **sibling**, which authored both commits, and
> distinguishes three outcomes rather than two — returncode 1 is a definitive "not an ancestor", and
> anything else is "could not evaluate" and prints a loud WARN instead of passing quietly.
>
> **And then it over-fired.** "Behind main" was the wrong question: this tool deploys `addons/*.cs`
> and nothing else, so a pin trailing only docs is harmless, and refusing on it would make every
> documentation commit in this repo require a tag-and-bump before the bridge could deploy. A guard
> that fires when nothing is wrong is one people learn to bypass — the same argument `file_hash()`
> already carries about line endings. It now asks
> `rev-list --count <pinned>..<main> -- addons/`. Verified four ways: in sync → exit 0; behind
> docs-only → proceeds, saying so; **11 behind with 3 touching `addons/` → exit 2, refuses**; same
> stale pin with `--verify` → exit 1, not blocked, and it names `TradeCopierEngine.cs` as the drifted
> file, which is precisely the `P0-63` revert. See §8.

### ✅ The two stale files in the live `AddOns/` folder — REMOVED 2026-08-13

`RiskGuardAddOnTests.cs` and `TestingStubs.cs` sat in the deployed folder, reported as orphans by
both deploy tools. They compiled to nothing (every line is inside `#if TESTING`, which NT8 never
defines), but NT8 compiles `bin/Custom/` **recursively**, so they were two files away from a
duplicate-type error that would stop *every* addon loading — the guard included.

**They did not "belong to neither tree", which is what this section said for a day.** Both have a
canonical home in `tests/`, and the deployed copy of `RiskGuardAddOnTests.cs` was **700 lines behind
it** (`diff --strip-trailing-cr`: 752 changed lines; raw `diff` says 25,642 because the deployed copy
is CRLF). So it was a stale fork of the test suite living inside the compiled tree — §5.3a's trap
exactly, one folder over: *a copy that tracks what was deployed rather than what is canonical.*

Moved, not deleted, to `Documents/NinjaTrader 8/_riskguard_backups/orphan_testfiles_<ts>/` — which is
a **sibling of `bin/`, deliberately**. Backing them up anywhere under `bin/Custom/` would have left
them compiled.

Verified after: `nt_compile` → **0 errors**; `sync_nt8.py --verify` → 7 identical, orphans now just
the bridge's own `McpBridgeAddOn.cs`; `GET /api/riskguard/version` → `loaded/shadow/armed/guarding`;
and the full config response byte-identical to the snapshot taken before the change. A recompile is
the moment the guard could silently fail to load, so it is checked, not assumed.

One artifact is deliberately left: `AddOns/config.json.UNUSED_not_read_by_addon`. It is not a `.cs`,
so it cannot reach the compiler, and its filename is the documentation.

---

## 5.11 Repo hygiene — current, and which repo each item belongs to

Re-checked 2026-08-13, and **actioned the same day** — everything below that could be closed without
an operator or a credential now is. The block this replaces (in §4a) had drifted so far that **half of
it described a different repository**, so ownership is now explicit.

> **No row here names a HEAD SHA.** The previous version did, and it was stale one commit later — the
> same failure this whole pass was cleaning up. Each row gives the property that stays true plus the
> command to re-measure it.

### This repo (`nt8-riskguard`)

| Item | State |
|---|---|
| Branches | ✅ **`main` only.** `harden/p0-63` was verified an ancestor of `main` and **deleted 2026-08-13**. Pushed, 0 unpushed. **`harden/riskguard-p0-51` does not exist here** — it was the pre-split branch name, and tvDownloadOHLC is still on it. |
| Tags | `v1.0.0` (split), `v1.0.1`, `v1.0.2` (`P0-63` + `P?-66` — **the deployed code**), `v1.0.3` (docs only). `main` carries docs commits on top of `v1.0.2`; **a tag moving is what would break the bridge's pin**, so never delete or move one. |
| Git hooks | ✅ **Installed 2026-08-13.** `.githooks/pre-commit` refuses `dll/pdb/exe/zip/nupkg`, media, and anything over 50 MB. **Proven to fire in both directions** before it was committed: a staged 57 MB blob and a staged `.dll` were each rejected with exit 1, and `ALLOW_BIG_FILES=1` passed. ⚠️ `core.hooksPath` is **local config, not tracked** — a fresh clone silently has no hook until someone runs `git config core.hooksPath .githooks`. Both READMEs now say so. Neither repo tracks a single blocked extension today, so the guard cannot misfire on real work. |
| CI | ✅ **ACTIVE since 2026-08-13**, at `.github/workflows/ci.yml`, `windows-latest`, on every push and PR. 11 steps: both structural checks, build, the 953-test suite, and **all three** mutation batteries — `mutate_p0_63.py` had to be **added**, because it arrived after the workflow was written and parked, so CI would have run two of three while looking complete. **4m39s** for the lot. Actions pinned to current majors (checkout v7, setup-dotnet v6, setup-python v7), read from the API not guessed, because v4/v5 target the deprecated Node 20 that GitHub is only temporarily force-running on Node 24. |
| CI — proven in **both** directions | Green on a known-good `main` proves the wiring runs, not that it can fail. So a throwaway branch carrying a deliberate `typeof(McpBridgeAddOn)` reference in `CopierReconciler.cs` was pushed: **run concluded `failure`, failing step `Direction check`** — then branch deleted, remote and local, and `check_direction.py` re-run clean. Six gates in these repos have been caught proving nothing (§8); a CI that has only ever been green is the seventh candidate. |
| ⚠️ How the scope block was actually cleared | **It was real**: a probe branch carrying a workflow file was refused verbatim — `refusing to allow an OAuth App to create or update workflow '.github/workflows/ci.yml' without 'workflow' scope`. HTTPS pushes here go through `gh auth git-credential`, so the `gh` token's scopes (`gist, read:org, repo`) govern them. **The fix was not `gh auth refresh`** — the operator added an SSH key, and **an SSH push is not an OAuth App push, so the restriction does not apply at all.** Both addon repos now use `git@github.com:` remotes. Keep that in mind before concluding a workflow file cannot be pushed. |
| Deployed tree | ✅ **No orphans.** The two stale test files were moved out of `bin/Custom/AddOns/` on 2026-08-13 and the guard re-verified after the recompile — §5.10. |
| Loop artifacts | `logs/agent_loop/*` is ignored except `ledger.jsonl` and `learning_feedback.jsonl`. See §8 for why that took two commits. |

### `nt8-mcp-bridge`

| Item | State |
|---|---|
| Submodule | `vendor/nt8-riskguard` pinned at **`v1.0.3`**. **Enforced** — `deploy.py` exits 2 on a pin that is behind in `addons/`, and *only* in `addons/`, so a docs commit on the core does not demand a tag bump (§8, §5.10). |
| Git hooks | ✅ Same hook, same proof, installed 2026-08-13. Its header names the real hazard here: `git add -A` from the root can reach into `vendor/`. |
| Tests | Harness 9/0, but `P2-27` still records that `McpBridgeAddOn.cs` has no real coverage; `tests/README.md` measures the gap. **CI being green here does not narrow that** — it runs the harness, and the harness asserts against source text. |
| CI | ✅ **ACTIVE since 2026-08-13**, same route. Two real steps: the harness, and one that **hides `vendor/nt8-riskguard` and requires `deploy.py --dry-run` to exit exactly 2** — so "it refuses to half-deploy" is a check rather than a comment claiming there is one. That step was replicated locally before activation, because this session's change to `check_vendor_not_stale` runs on the same path and could have turned the refusal into a crash. |

### tvDownloadOHLC — **not this repo's problem, recorded so it is not lost**

These were listed as this project's hygiene for months and are keyed to paths that do not exist here:

- **The Gemini API key** scrubbed from history (`scripts/trader/chart_agent/test_vision.py`) still
  needs **rotating**. It never reached GitHub; that is not the same as being safe. **The operator has
  taken this one** (2026-08-13) — it is not waiting on an engineer.
- ~~**~0.28 GB of older parquet remains in published history.**~~ ✅ **Done by the operator, and this
  entry was wrong for a day.** Measured 2026-08-13: `git rev-list --objects --remotes | grep -ci
  '\.parquet$'` → **0**, and the same over `--all` → **0**. Largest published blob is now 39.2 MB
  (`duckdb-mvp.wasm`). ⚠️ The GitHub API still reports `size: 423 MB` and the local `.git` is still
  1.5 GB — both count objects the rewrite made *unreachable*, pending GC. **A big size number is not
  evidence the purge failed;** ask git what is reachable. Detail in tvDownloadOHLC's `docs/ROADMAP.md`.
  > **Why this was wrong:** I wrote it from a memory note rather than from a measurement, in the
  > middle of a pass whose entire subject was doc claims nobody had re-checked. The rule the rest of
  > §5.11 follows — *state the property and the command to re-measure it* — exists because of exactly
  > this, and I broke it in the act of writing it down.
- ✅ That repo's unpushed commits were **pushed 2026-08-13**. Two unrelated background processes still
  commit to it, so re-check rather than assume (§8).

---

## 5.12 What this documentation pass found, and the pattern under it

**This section is the useful part of session 18.** Every correction is listed in the section it
belongs to; what follows is *why* a 3,100-line handover went stale in ways its own rules were
supposed to prevent.

### The corrections

| Where | Claimed | Actually |
|---|---|---|
| Header | suite 806, §0 said 787, path note said 926 — **three counts in one file** | **953 / 0** |
| Header | `Branch: harden/riskguard-p0-51 — not merged, not pushed. main is untouched.` | that branch **does not exist here**; `main` = `v1.0.2`, deployed and pushed |
| Header, §0 | "the deployed build is `f174ba68`" / `b5c58ae0` | both **orphaned by the split's history rewrite**; deployed build is `978ed3a` |
| Header, §0 | "all **10** addon files in sync" | **7** in this repo, 8 counting the bridge's, plus 2 orphans |
| §0, §7 | retire settled decisions from "this file *and* `scripts/agent_loop/profiles.py`" | that path **has not existed since the split**; it is `agent/nt8_riskguard.py:106` |
| §7 | `P0-9`'s five and `P1-56`'s two invariants "mirrored verbatim" into `settled` | **they were not there at all** — 6 entries, none of them these. Now 21 |
| §3 | "use `python -m scripts.agent_loop`", three links to `AGENT_PATCH_LOOP.md` | package is `agent_loop`; that doc is **not in this repo** |
| §4a | "62 defects, 49 closed"; plan said "58"; **START HERE: `P0-62`** | **67 / 51 / 16**, and `P0-62` is superseded by `P0-63`, which is fixed and deployed |
| §4a | ratio converter slices 2 and 3 pending, slice 1 undeployed | all four slices **complete, deployed, sim-validated** |
| §4a | four repo-hygiene items | **all four stale**; two belonged to tvDownloadOHLC |
| §5.3a | the hardlink trap and the missing `.gitmodules` | **both resolved** |
| §5.5, §5.6 | "the next session opens with `P0-63` + `P?-66`" | **both done and deployed**; next is `P0-67` |
| §5, §7 | two different sections both numbered **§5**; traps was §6 but sat before §5 | renumbered **§7** and **§8** |
| `VERSION.md` | "Current Release: `v1.7.0-ui-audit`" | git says **`v1.0.2`**; the addon constant says `1.1.0` |

### The pattern, which is worth more than the list

**1. A count maintained by hand in three places will disagree in three places.** 58 / 62 / 67 were
all written by someone summarising the same entries. §5.0 now records the `grep` that *derives* the
count instead, so the next reader can check it in one command rather than trusting a table. Prefer a
derivation to a number.

**2. "Mirrored into X" is a claim about a second artifact, and nothing checked it.** The settled-list
divergence is the most expensive finding here: `P1-56`'s reservation invariant was missing from the
reviewer prompt, and that is precisely the rule the `P0-63` candidate broke — the panel never flagged
it because **the panel was never told**. A doc that asserts two artifacts agree needs a check, or it
is decoration. Same family as the mutation batteries that exited 0 while printing survivors (§8).

**3. A repo split invalidates documentation silently.** Paths kept resolving in the *reader's* head
while pointing at nothing on disk: `profiles.py`, `AGENT_PATCH_LOOP.md`, `.githooks/`,
`docs/ROADMAP.md`, `scripts/trader/…`. The split's verification ran the tests — which passed — and
never started the moved tooling, which is also how the agent loop stayed broken here for two sessions
(§5.8). **Migrating code is not migrating a project.** After a move, run the tools and follow the
links, not just the suite.

**4. Stale navigation is worse than stale history.** The history in §1–§4v is fine: it is dated,
scoped, and honest about what it knew. The damage was concentrated in the parts that told you *what to
do next* — a header, a "START HERE", a "next four pieces". Those need an owner and a date; a
post-mortem does not. Hence the split in this file between a short current layer (header, §0, §5) and
an append-only historical layer, and hence §4a is now explicitly *not* a plan.

**5. Two of these were flagged by the documents themselves and left.** The plan's inventory table
carried a ⚠️ STALE banner, and §5.3 listed "Doc consolidation" as an item. A known-stale document
that stays in place is read by whoever does not notice the banner. **Fix it or delete it; a warning
label is not a fix.**

**6. Lesson 2 recurred inside this very session, in code written the day before.** The stale-pin
guard shipped on 2026-08-12 with "verified in all three directions" written next to it — and it was
inverted, because the check ran in a repo that could not see the commits it was asked about, and the
three-direction test happened to run under the one condition that hid it. Then the fix over-fired on
docs-only commits, which would have trained everyone to bypass it. **Two rounds of getting a nine-line
check wrong.** The pattern is not carelessness, it is that *"I verified it"* is a claim of the same
kind as *"it is mirrored into X"*: it names an outcome without naming the conditions. Record the
conditions, and make the gate fail in front of you at least once. §5.10 has the detail.

---

## 5.13 Session 19 — 2026-08-13: THE LIVE VALIDATION. `P0-63` trails, `P?-66` measures, and four new defects

**One 1-lot MNQ round trip on `Sim101 -> Sim-ORB`, RiskGuard in `shadow`.** The cheapest item on the
board, and it settled two open questions and opened four. Everything below is quoted from
`interventions.jsonl`; timestamps are ET on 2026-08-13.

### ✅ `P0-63` IS VALIDATED LIVE. The mirrored stop trails.

First time the fix has been exercised outside the suite. The sequence, in order:

| Time | Account | Event | What it proves |
|---|---|---|---|
| 11:52:51 | Sim-ORB | `ORDER_UPDATE` `ChangePending` **@29830.75** | NT8 shows the *caller's desired* price the instant `Change()` is called |
| 11:52:51 | Sim-ORB | `COPIER_BRACKET_MODIFIED` "stop moved to 1@29830.75 **in place** ... no cancel/replace, so no unprotected window" | the optimistic success line — **and it is wrong.** See `P1-70` |
| 11:52:51 | Sim-ORB | `ORDER_UPDATE` `ChangeSubmitted` **@29820.75** | the provider settles it back. **This is `P0-63`, live** |
| 11:52:51 | Sim-ORB | **`COPIER_BRACKET_STOP_CHANGE_IGNORED`** "provider ignored Change() for stop (still 1@29820.75, requested 1@29830.75); falling back to cancel-then-create" | **remedy 3's detection fires for the first time on a real broker path** |
| 11:53:55 | Sim-ORB | **`COPIER_BRACKET_MODIFY_BYPASSED`** "provider ignored a previous Change() on Sim-ORB; falling back to cancel-then-create" | the account-level memory works: the next sync **spends no doomed `Change()` at all** |
| 11:53:55 | Sim-ORB | `CancelSubmitted` (old) -> `Submitted @29830.75` (new) -> `Cancelled` (old) -> `Accepted @29830.75` | cancel-then-create, and the **new leg goes in before the old is confirmed gone** |
| 11:53:55 | Sim-ORB | `FSM_TRANSITION` "stop COPIER_STOP Submitted -> **ProtectedPending (covered 1/1)**" | independent corroboration from the guard's FSM that **coverage never reached 0** |

Final state: exactly **one** working follower stop at `29830.75`, matching the leader — new `orderId`
and a **new OCO id** (`741e7930...`, was `b36843d8...`), which is the signature of a replacement
rather than a modification. **No duplicate leg, no naked window, right price.**

> ⚠️ **Read the first two rows together, because they are the trap §5.9 predicted.** NT8 leaves the
> caller's desired values on the `Order` until the provider settles. A synchronous read-back would
> have said *"it took"* — the log even contains that claim. Detection **on settle** is what made this
> work, and it is the one refinement the evidence forced onto the operator's remedy-3 decision.

### ✅ `P?-66` IS ANSWERED — the measurement works. The *reporting* never existed.

Both fills measured, both figures real:

```
COPIER_FILL_MEASURED  entry: latency=142.86 ms, slippage=0 ticks
COPIER_FILL_MEASURED  exit:  latency=314.21 ms, slippage=-4 ticks
```

**The entry's `0` is a TRUE zero** — leader and follower both filled at 29840.75 — and it sits beside
a non-zero latency, which is exactly the distinction the instrumentation was built to make and the
reason §5.2 says *do not read a zero as a pass*. The exit then produced a non-zero: `-4` ticks,
**negative meaning FAVOURABLE**, because the follower sold at 29848.75 against the leader's 29847.75.
That confirms the sign convention at `TradeCopierEngine.cs:3099-3102` on live data — *positive is
always worse for the follower* — which no test could have established.

So `P?-66` splits, and only half of it closes:

| Half | Verdict |
|---|---|
| Is the metric computed on the live path? | ✅ **Yes.** Closed. |
| Can anyone READ it? | ❌ **No.** New defect `P1-69`. |

### 🆕 Four new defects, three found by looking at what the trade did NOT do

**Numbers 68-71; the digits are reserved and never reused.** The bands are this session's triage.

| ID | Band | What | Evidence |
|---|---|---|---|
| **`P0-68`** | **P0** | **`nt_change_order` reports `"status": "modified"` when the provider ignored the change.** A **fourth** `Account.Change()` call site — in the bridge — carrying `P0-63`'s defect with **none of its detection.** Anything trailing a stop through MCP silently does not move. | Observed twice. First on the leader's stop mid-test. Then **reproduced in isolation** with no position, no copier, no ATM: a resting buy limit at 29500 was asked to move to 29450; the response said `"status": "modified"` and the order stayed `Working @29500`. ⚠️ **The response body carries `limitPrice: 29500` right next to `"status": "modified"` — the refutation is already in the payload and nothing reads it.** |
| **`P1-69`** | P1 | **The copier's latency/slippage metrics are measured and then discarded.** `rel.LatencyMs` / `AvgSlippageTicks` are written to the in-memory relationship only; nothing persists them and there is no read path. | After two measured fills, `RiskGuard/copier_config.json` still reads `LatencyMs=0.0 AvgSlippageTicks=0.0`, with its **mtime unchanged from the previous day**. Compounded by two known defects: there is **no `GET` on `/api/copier/config`** (§5.3), and the UI reads a *different file* (`P?-64`). **Every consumer sees 0.** This is almost certainly what the original `P?-66` observation actually was. |
| **`P1-70`** | P1 | **`BRACKET_MODIFIED` writes a false success line into the live audit log**, claiming "stop moved ... in place ... no cancel/replace, so no unprotected window" *before* the provider settles — then `BRACKET_STOP_CHANGE_IGNORED` contradicts it in the same millisecond. | Both lines are quoted in the table above. Same shape as the defect already fixed at `:3113-3119`, where `FILL_MEASURED` printed a stored value nothing had computed for that fill. **A log that states an outcome it has not yet observed is the thing this project keeps paying for.** |
| **`P1-71`** | P1 | **A named active relationship produced no order and left no diagnosable trace.** `COPIER_COPY_BEGIN` logged *"2 active relationship(s): Sim-ORB, **SimCopy2**"* on both the entry and the exit. **Nothing followed for SimCopy2 — no order, no skip, no reason.** | `SimCopy2` exists (`provider: Simulator`, cash 98,140.50), is not quarantined, has no lockout, and stands at 1 trade of a `MaxTradesPerSession` of 8, so the obvious explanations are ruled out. **The cause is unreadable because every exit in that loop is invisible**: `followerAcc == null` (`:3408`) logs *nothing at all*, and the three `CanTrade` / `COPY_BLOCKED_NO_GUARD` blocks (`:3440`, `:3446`, `:3452`) go to `NinjaTrader.Code.Output.Process` **only** — not `CopierLog`, so not `interventions.jsonl`. That is precisely the sin the comment at `RiskGuardAddOn.cs:4435-4440` says was fixed for the copier. `nt_get_logs --tab Output` does not surface them either: it returns the guard's structured stream, not raw `Output.Process` lines. |

### Two things that worked, stated plainly

- **`shadow` is what made the test survivable, exactly as the pre-flight said.** The guard logged
  `[SHADOW] Would execute action FlattenPosition triggered by MISSING_STOP_FLATTEN` twice: once for
  the deliberately naked entry, once during the cancel-replace gap created on the leader. **Armed,
  either would have flattened the position and destroyed the test rather than the defect** (§4p).
- **`P0-50`'s orphan-stop release works.** The leader's exit copied, and the follower's mirrored stop
  went `terminal (CancelSubmitted) -> Unprotected` -> `Cancelled` with the position. No orphan.

### `P1-57`'s chain did NOT fire, so do not treat it as exercised

`SimCopyTest1` received nothing. The `Sim101 -> Sim-ORB -> {SimCopyTest1, SimCopy2}` fan-out the
pre-flight warns about is **live in configuration only** — the third-party copier was not running.
`P1-57` stays open and stays unexercised; a future test must not assume today's blast radius.

### Method note: the pre-flight paid for itself three times

Reading the config and the code *before* trading predicted two behaviours that then happened, and
disproved one suspicion for free:

1. **Ruled out** `MaxSlippageTicks: 0.0` as a `P?-66` cause without spending a trade — `:3124` shows
   it gates only the *quarantine* threshold, not the measurement.
2. **Predicted the fan-out** from `GetActiveRelationshipsForLeader`, which filters on `IsEnabled`
   **only**: `ArmedForLive` is checked later and blocks **non-Sim** followers alone (`:3413`). So
   `SimCopy2` being `ArmedForLive: false` did *not* exclude it — which is why its silence is a defect
   and not a setting.
3. **Found `StealthMode` is dead config** — declared twice, copied, persisted in the remembered
   subset, and **read by nothing**. A `P2-24` instance, recorded here rather than given its own ID.

### Operational facts worth keeping

- **The bridge's auth header is `Authorization: Bearer <token>`.** `X-Auth-Token` returns
  `{"error":"Unauthorized: Invalid or missing Bearer token"}`. §4g named the token file but not the
  header.
- **`MaxAutoStopAttempts` is nested under `StopGuard`**, not top level, in the config response. §4g
  uses its presence as the proof that post-T2 code is loaded; look in the right place.
- **This box runs `PDT` (UTC-7) while the logs are stamped ET.** File mtimes therefore look 3 hours
  behind the log timestamps. That is a timezone, not a stalled component — it briefly read as a dead
  heartbeat during pre-flight.
