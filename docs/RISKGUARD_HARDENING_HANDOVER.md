# RiskGuard / TradeCopier Hardening — Session Handover

**Last updated**: 2026-08-14 (**session 38 — §5.45**). Core **`v1.22.0`** is tagged, deployed and
**NT8-compiled clean (0 errors)** — core suite **1436/0**, bridge harness **108/0**, MCP wrapper
**43/0**, **27** core mutation batteries + the bridge's **2** (and CI in that repo now runs them —
it ran **neither** until §5.44), **283 anchors / 0 broken**, all 8 gates green.
**118 IDs, 9 open** — **three closed and live-validated this session** (`P1-100`, `P0-104`,
`P2-101`), and every one of them was **found by driving the deployed box**, not by the suite, which
was green throughout all three. Every figure here was **measured, not incremented** — the previous
revision of this paragraph claimed the bridge harness was both `92/0` and `108/0` in consecutive
sentences, which is what incrementing one number and appending another looks like.

✅ **`P1-100` is CLOSED and live-validated** (§5.43). A SHADOW-only lockout blocked real orders —
`CanTrade` was right, but the bridge's three order paths and `GET /api/lockout` all ask
`IsAccountLocked`, which returned the raw flag and had never been taught either `P2-92`'s authority
clause or `P2-94`'s deadline clause. **Wrong in both directions**: it refused on an observation *and*
reported an account free to trade through a timed manual lockout. One predicate (`LockoutBinds`),
three readers, none re-deriving. ⚠️ **The funded 50K TPT PRO account was being gated by it too** — a
defect found on sim was never confined to sim.

✅ **`P0-104` is CLOSED and live-validated** (§5.44). `nt_emergency_flatten` — the panic kill-switch
— **cancelled its own flatten order** in its "residual bracket" pass, reported success, and then
locked the account so `nt_place_order` refused the exit the operator would place by hand. Stops
cancelled, flatten cancelled, account locked, `success: true`. `residualCancelled` **1 → 0** is the
discriminating reading; the account now actually goes flat. ⚠️ Its battery **caught the author**: the
extracted class could not see how its *caller* built the argument, so the survivor was real —
**extraction moves the untested boundary, it does not remove it.**

✅ **`P2-101` is CLOSED and live-validated** (§5.45). The lockout retry is bounded by an attempt
count whose budget is **1** outside an acting mode and **6** in `live` — the 1 is the fix, not a
tuning value. ⚠️ And the alarm that should have caught it **could not fire**: `LOCKOUT_STUCK` measured
an interval the retry reset every 5s. One alarm that could not stop beside one that could not start.

⚠️ **`P1-106` is the item to do next**: a lockout refuses the order that would **close** the position
it is locking you out of — the half of `P0-104` (closed) that its fix left deliberately. Then **`P2-107`**: the same
repeated-action family survived `P2-101`'s fix on a **different path** (`PEAK_GIVEBACK_BREACH`, 7
emissions in 20s), found in `P2-101`'s own validation run — so the de-duplication belongs where
actions **leave** the guard, not inside each producer. Then `P1-102`, `P1-105`, `P2-103`, `P2-95`.

⚠️ **`P1-102` was raised as half of a composite risk that no longer exists** — with `P1-100` closed,
shadow mode can no longer freeze an account, so "the guard stopped my account and I cannot start it
again" is now just a workflow gap. Weigh it accordingly.

⚠️ **`P2-98` is CLOSED and live-validated** (§5.38), and closing it **opened a P1**. The fix moves
the grain of a measurement from the SLICE to the COPY: a partial fill is accumulated across its
slices and reported once, quantity-weighted, when the order is done. Live, a 10-lot copy filled
**2 + 8** and reported `slippage=-2.2 ticks on 10 contract(s) across 2 slices` — where `v1.18.0`
would have reported `-3 ticks` from the 2-lot and raised `FILL_NOT_MEASURED` for the 8.

✅ **`P1-99` is CLOSED** (§5.40, `v1.20.0`). The copier ran the whole copy path per leader
EXECUTION, so a 100-lot MNQ order filling as **20 × 5** under MNQ→NQ conversion dropped **every**
slice — leader long 100, follower **FLAT**, twenty routine `COPY_SKIPPED_SUB_MINIMUM` lines and no
error. It came out right in the validation run **by luck** (5 + 95). The grain of the decision moved
from the execution to the **ORDER**: each slice recomputes the target from the cumulative leader
quantity and copies the **delta**, so rounding cannot accumulate. Three things in it are worth
reusing — the clamp goes on the **delta**, not the cumulative (clamping the cumulative subtracts the
already-copied slices twice); **credit what was SENT, not the target**, or the clamp's shortfall is
forgiven; and **exits are deliberately NOT routed through it**, because `P0-6`'s clamp already
mirrors the follower's real position.

⚠️ **Its battery caught the AUTHOR, not the code.** The first run had three survivors and each meant
something different: one was **unkillable by construction** and exposed a wrong *comment* rather than
a wrong line; one was a real coverage gap (the clamp test had capacity fitting *exactly*, making
"credit the target" and "credit what was sent" the same number); and one had **no observable at
all**, so the assertion could not exist until an internal count did. **A surviving mutant does not
always mean a missing test.**

⚠️ **CI had been RED for 10 pushes, back to `v1.17.0`, and it is not the code** (§5.38).
`mutate_p330.py` and `mutate_p096.py` each declare a mutant *expected* to survive — correctly, with
the reason no test can reach it — and then exited `1 if survivors`, so they were **unpassable from
the commit that added them**, and the batteries after them in the workflow **never ran**. Fixed by
`mutation/_battery.py` (a mutant declares its own expectation; fails on an unexpected survivor
**and** on a declared one that has since been killed) plus `tools/check_expected_survivors.py`, which
makes the class mechanical. **Run `gh run list` at the START of a session** — the note saying so was
already in the memory store and was not acted on. **An alarm that is always on is off**: same shape
as `P2-98`'s `FILL_NOT_MEASURED` firing on every manual fill and `P3-30`'s audit firing on a
correctly protected account. Three instances in two sessions.

⚠️ **The shared lesson of sessions 36-37: the suite modelled an order as ONE fill, and reality does
not.** `P2-98` was that blind spot on the follower side; `P1-99` the same on the leader side. Every
pre-existing copy-path test sends a single execution for the full quantity, which is why a green
suite, 24 mutation batteries and a clean compile all passed over both. **Both are now closed, and
the eleven `P1-99` tests are the only ones in the repo that send more than one execution for one
leader order** — extend those rather than adding another single-fill test.

⚠️ **`P0-96`, found in this session's last hour and the sharpest thing in it**: NT8's `Position.Quantity` is **absolute** — the side is `MarketPosition` — and the copier read the **sign** of it in two places. So a leader **covering a short** sent the follower a `Sell`, which does not close a short, it **doubles** it. **1300 green tests passed under it**, because every long-side test does and there was no short-EXIT test. Found while reading adjacent code, not by the suite and not by any CI gate. **A convention the whole suite encodes is not a convention the code follows** — nothing compared the two.

✅ **All three of this session's unproven features are now LIVE-VALIDATED** (§5.36), on sim accounts with the operator's authorisation: `P0-96` sent `BuyToCover 10` where it used to send `Sell 10` into a short; the guard audit fired 13 correct `NAKED_POSITION`s **and then stayed silent for 84 seconds once flat**; and shadow mode submitted nothing while naming the order it would have sent. ⚠️ **The same four minutes opened two new defects, both in seams between components**: **`P1-97`** — `nt_place_order` never emits `SellShort`/`BuyToCover`, so the copier reads every MCP-placed short ENTRY as an exit and every COVER as an entry (a wrong-direction copy, stopped in this run only by a rounding accident) — since FIXED and live-validated (§5.37), and the copier can now open a short for the first time — and **`P2-98`**, a partially filled copy measures only its first slice and blames the wrong cause for the rest. ⚠️ On the validation run **every one of four copies partial-filled**, so half the fills were unmeasured: not an edge case.

⚠️ **Session 35's finding is the one to carry forward, because it invalidates a habit rather than a
line of code**: `P3-30`'s guard audit shipped in session 34 with **1264 green tests**, and it
**did not exist in the production build** — `StartAuditTimer` sat inside `#if TESTING`, so
`AuditIntervalSeconds: 10` was live in the config describing an audit that was not in the net48
assembly. Nothing called it even in the test build, and when it did run it keyed on
`Instrument.ToString()` where every FSM keys on `.FullName`, so it matched **nothing** — which meant
a **correctly protected account** would report `NAKED_POSITION`, `ORPHAN_STOP` *and*
`FSM_DIVERGENCE` every ten seconds. Its three acceptance tests were **positive-only** and every one
stayed green through all of it. **For a detector, the negative test is the one that proves the
detector works** — a detector that fires on everything passes every positive test ever written for
it. All three are fixed in `v1.14.0` (`mutation/mutate_p330.py`, §5.33).

✅ **`P3-34` mostly landed** in `v1.15.0` (§5.33): the copier has its **own** `live`/`shadow`/`disabled` mode —
deliberately not a reading of the guard's — and `RunCopierPreflight` finally has a caller that
**refuses** the move to `live`. ✅ **Its read surface landed too** (§5.34): `copierMode` and `set_mode` on
`/api/copier/config`, plus `nt_copier_config`. Closing that gap found **three more defects, all by
driving the deployed box** — `enforcing` had become wrong the moment the mode existed (F-9's shape),
a refused mode change left **no trace in the audit log** (P1-71's), and the events logged under a
**doubled `COPIER_COPIER_` prefix**. ⚠️ And **`P1-72` has REGRESSED**: `nt_copier_config` advertised
`quarantine`/`unquarantine`, which the addon answers `UNKNOWN_COPIER_ACTION` for.

🆕 **`tools/check_no_dead_safety_machinery.py`** makes `P2-24`'s class mechanical, because it
recurred **three times in the session that closed it**. Safety machinery that is written and never
called passes every other gate here. It fails in **both** directions, so its allowlist cannot rot.

✅ **Session 34 closed twelve defects**: **P2-95**, **P2-93**, **P2-94**, **P3-31** (in-flight ledger +
timer), **P3-30** (guard-side audit), **P1-57** (reference-tracking order filter), **P1-13**
(threading inversion), **P2-25** (news shield loader), **P2-24** (dead code removed), **P3-32**
(superseded by P0-9), **P2-26** (drift table updated), **P2-27** (partially closed — copy path in
test build, CI runs suite, bridge has tests). Plus the firm mapping (**94 accounts** across **9
profiles**). All with operator-verifyable defaults.

✅ **`F-9` — the account → firm-plan mapping — is LIVE and validated** (§5.28). Five Sim accounts are
mapped to two size-keyed plans, and their firm rules moved `Disabled` → `EvaluatedNotEnforcing` with
the plan named in the row. **The reporter had been disagreeing with the enforcer in BOTH directions**
since `P1-42`: calling a rule `Disabled` that the guard runs, *and* calling one live that cannot fire.
The second is the real Take Profit Trader profile, which has no daily loss limit at all.

**There is a browser page**: start NT8 and open **`http://localhost:7890/ui`** — it asks for the
bridge token once and keeps it in `localStorage`. It shows, per account, every guard rule with its
state **derived at read time**, and beside it the copier's relationships with **expected vs actual
position**. It can now *change* two things (relationship enable/disable, quarantine release);
everything else is still read-only.

✅ **`P2-92` IS CLOSED** (§5.30) — `shadow` mode is observation-only now, and the firm mapping is live on SIX accounts including the funded 50K TPT PRO, with numbers taken from the firms' published tables (`FIRM_PLANS_RESEARCH.md`) rather than from a config backup. ⚠️ **Everything `F-9` first deployed was WRONG**: the recovered profiles carried no account size, so TPT's 25K max loss went out as a 50K and Apex's 50K row as a 100K — and a TPT PRO trails **intraday**, not `eod`, which is the direction where the firm fails you before the guard speaks. **Weigh `P2-95` first now**: `FirmStartingBalance` is a session-start heuristic, so the trail-lock floor is wrong by the account's LIFETIME PROFIT, and `LockAtProfit` carried a real value for the first time on 2026-08-13.

⚠️ **DO THE NEXT ITEM BY §5.6, NOT BY BAND LETTER.** `P1-90` was `P0` on consequence and is closed and
live-validated; `P1-91` is closed. The one to weigh first now is **`P2-92`, filed this session, and its
band letter understates it too**: `shadow` mode is **not** observation-only. `ProcessAction` gates
*execution* on mode, so a shadow breach flattens nothing — but the rules set `IsLockedOut` **before**
dispatch, outside any mode check, and `CanTrade` reads that flag **above** its own
`if (!_isArmed) return true;` escape hatch. So in shadow the account **stops being allowed to trade**,
the copier and every strategy consult `CanTrade`, and its refusal paths log to `Output.Process` only
(`P1-71`) — so nothing readable says why. It fails in the safe direction, which is the only reason it
is `P2`. It became load-bearing the moment `F-9` armed two more lockout-capable rules on five accounts.

⚠️ **Two things this header claimed that are FALSE as of 2026-08-13, both measured** (§5.28):
**a recompile no longer disarms** — the log shows `ARMED_ON_START` and the endpoint reported
`isArmed: true` straight after a compile, so do not schedule a manual re-arm on the old note; and
**`SaveAndReloadConfig` does not run preflight**, so a firm-mirror config that cannot pass it comes up
**disarmed at the next restart** with nothing about the file looking wrong. There is no preflight
endpoint on the bridge; it is pinned in the suite instead.

**Every default in [CONFIG_DEFAULTS.md](CONFIG_DEFAULTS.md) is now applied** (`P1-82`…`P1-87`,
§5.25), along with `P1-88`/`P1-89` in the bridge. One theme runs through all eight: **config that
reads as protection that does not exist.**

**Three things to carry forward, each of which cost something to learn:**

1. **A static "is this field read?" check MISSES `P2-25` completely** — the reason the guard's rule
   inventory is a runtime read and not a linter. The news shield is fully wired and its event list
   is **always empty**, because `LocalNewsEventsFilePath` has no loader. Every mechanical check
   passes on a rule that has never been able to fire. That is the fourth state, **`INERT`**, and the
   page shows it to you. ⚠️ **`P1-86` is its corollary**: `Disabled` must mean *"this would work if
   you turned it on"*, so switching off a rule that could never fire must not quiet it.
2. **ASK THE DEPLOYED BOX.** The inventory passed 1123 tests and returned **96 accounts / 2400 rows
   / 648 KB per poll** in production, 88 of those accounts with zero equity (§5.23). And in §5.25:
   **changing a default does not change a deployed box** — the new values only apply to fields
   *absent* from the stored config, so the running guard kept `StopAttachSeconds = 3` through a
   clean deploy and a green suite until it was written explicitly.
3. **Four of the six defects opened in session 29 came from EVIDENCE, not from reading code** — two
   from mutation batteries, one from checking what a fix did to the inventory, one from the review
   panel. `P1-87` is the one to know: a mutant flipping `StopGuard.OnMissing` survived **1180 green
   tests**, and a test in that suite **asserted the defect as correct behaviour**.
   `mutation/check_anchors.py` exists because a battery whose find-string stops matching scores its
   mutant a **survivor** — but only when someone runs it; **11 anchors** were silently proving
   nothing.

*(Earlier: session 26 — the UI became something you can look at, `v1.4.0`→`v1.8.0`, §5.23. Session
21, the MCP wrapper — four defects `P1-72`…`P1-75`, all closed, §5.16, of which **`P1-75`: reading
the prop-firm rules DISARMED them**. Session 20 — the whole `P0` band closed; `P0-63` and `P?-66`
validated by one live 1-lot MNQ round trip, §5.13, which opened four defects that were fixed and
deployed the same day, §5.14.)*

Session 18 was a documentation pass that re-derived this header, §0, §4a, §5, §7 and §8 from the repo
and the live box rather than copying them forward; everything they used to claim that was false is in
**§5.10**, because the *pattern* of how this file went stale is worth more than the corrections.
⚠️ **It went stale again**: sessions 27 and 28 were never written up at the time and this header sat
four tags behind until session 29 reconstructed them as §5.24.

> ### Read in this order
>
> | | Where | What it gives you |
> |---|---|---|
> | 1 | **§0**, below | verified current state, the five things that will bite you, the commands |
> | 2 | **[§5 — THE OPEN BACKLOG](#5-the-open-backlog--authoritative-as-of-2026-08-13)** | the authoritative answer to *what is left?* Start at **§5.6**, the order |
> | 3 | **§7 — Decisions already made** | do not re-litigate; the review panel will try every round |
> | 4 | **§8 — Known traps** | each one cost a session to find |
> | 5 | session records, newest first: **§5.28, §5.27, §5.26, §5.25, §5.24, §5.23, §5.21, §5.19, §5.18, §5.17, §5.16, §5.15, §5.14, §5.13, §5.12, §5.10, §5.9, §5.8, §5.7, §4z, §4y, §4x, §4w, §4v … §4e** | the reasoning behind a backlog entry, when you need it |
>
> ⚠️ **§5.5's "rewrite the UI in NT8 WPF" was REVERSED on 2026-08-13.** The UI is now a local
> browser page served by the bridge — [UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md) §7, recorded in
> §5.19. That pass also found a **third risk system in neither repo** (`RiskGatekeeper.cs`).
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
> with nothing broken. It is **1053** now.

---

## 0. Start here

### Verified state — 2026-08-14, re-measured after session 39

Every row below was **measured for this pass**, not carried forward, and the row says so when it was
not. The command that checks it is in the last column.

> ⚠️ **This block was 11 tags stale before session 33's pass, and that is the failure it exists to
> prevent.** Sessions 22–29 each appended a `§5.x` and none came back here, so §0 claimed suite 1053,
> 78 IDs, `v1.2.0` and 6 batteries while §5.25 recorded 1188, 92, `v1.12.1` and 18. Anyone following
> the documented reading order — "§0, then §5 from §5.6" — got a correct order of work and a wrong
> set of facts about what is deployed. **If you append a session record, re-derive this table in
> the same commit.**
>
> ⚠️ **It happened again, and the second time is more instructive than the first.** Sessions 35–38
> left six rows at session-34 values — suite 1311, bridge 92, `v1.18.0` deployed, 25 tags — while
> the box ran `v1.22.0` and the suite stood at 1436. What makes it worth recording is that session
> 38 **did** return here and updated the Mutation row **only**, so the table was *half* re-derived
> and read as maintained. **A partially updated table is worse than an obviously old one**: nothing
> distinguishes the fresh rows from the stale ones, and the timestamp at the top vouches for all of
> them. Re-derive the WHOLE block or none of it, and say which rows you measured.

| | | How to re-check |
|---|---|---|
| **Suite** | **core 1469 passed, 0 failed**; **bridge harness 233 passed, 0 failed across 46 tests** (was 133/26 at the start of session 41 — `P1-105` added 12 and `P2-109` added 8); **MCP wrapper 51 passed, 0 failed** (was 43 — `P2-103` added 8) — re-measured 2026-08-14 (session 41). ⚠️ The wrapper's tests **now run in `nt8-mcp-bridge` CI**, which they never did anywhere before; run them the way CI does (`cd mcp && node --test`), because `node --test mcp/tests/` from the repo root is a MODULE path on Node 24 and fails with `MODULE_NOT_FOUND` that reads like a test failure | `dotnet run --project tests/RiskGuardTests.csproj`; in `nt8-mcp-bridge`: `dotnet run --project tests/BridgeTests.csproj` and `cd mcp && node --test` |
| **Defects** | **127 IDs — 120 closed, 7 open**, re-derived 2026-08-15 (session 44) with `check_next_list_ids.py`'s OWN status logic rather than a substring scan: **115** banded entries (**108** closed, **7** open — `P2-116`, `P3-110` narrowed, `P3-33`, plus `P0-9`, `P1-13`, `P2-27`, `P2-29` PARTIALLY CLOSED with recorded remainders) + **3** untriaged `P?-` (all closed) + **9** `F-` findings (`F-9`…`F-17`, all closed). ⚠️ **The previous figure said 122 / 109 / 13 and listed SIX defects as open that are closed** — `P1-77`, `P1-81`, `P2-78`, `P1-102`, `P2-108` and `P2-112`. It had been hand-patched rather than re-derived, which is the failure [[closures-do-not-propagate-backwards]] describes: **a half-updated summary is worse than an obviously stale one**, because the timestamp vouches for every row. ⚠️ And a naive `grep CLOSED` gets this WRONG — headings use `FIXED`, `RESOLVED`, `SUPERSEDED` and `PARTIALLY CLOSED`, so `P0-96` reads as open. Derive it with the gate's `entry_status`. | `python tools/check_next_list_ids.py`; the derivation is in §5.69 |
| **Do next** | ⚠️ **This row and §5.6's are kept in step with the newest `Order from here`, which is §5.78's — read that one; it carries the reasons.** 🆕 **SESSION 51: `P1-125` and `P3-122` are ✅ CLOSED and live-validated on the `live`-mode half** — the browser page now carries the copier's own mode beside the guard's, and each row says why it is not enforcing, ranked by what BINDS. **Next is `P2-127`**, §4's fleet/inspector layout, which is SETTLED and not to be re-opened. ✅ **`P3-128` CLOSED v1.34.0** the same evening it was filed, by the agent loop (APPROVE round 1), and live-validated: the page now reads `[ COPIER LIVE - NOTHING ENABLED ]` in amber. 🔶 **§5.77 REORDERED EVERYTHING BELOW.** The operator sent a screenshot of the surface they actually use: the **browser UI** at `http://localhost:7890/ui`, served from `nt8-mcp-bridge/ui/index.html` — **not** the WPF `TradeCopierWindow` that sessions 49 and 50 spent themselves on. Measured: the page renders **0** of the `copierMode` / `notEnforcingReason` / `configConflicts` the API has returned all along (**21** references on the serving side), dispatches **2** of the **14** copier actions its own API accepts, and has **0** nav elements across **4** stacked sections. Filed `P1-125` (✅ CLOSED session 51), `P2-126`, `P2-127`. ⚠️ **The unfalsifiable-status-header defect closed in the WPF window last session is the same defect this page still has** — fixed there, not here. **Establish which surface the operator has open before improving a display.** ✅ **`P2-116` and `P2-123` BOTH CLOSED in session 50 (`v1.33.0`), and `P2-116` is LIVE-VALIDATED**: the funded account and a dormant eval no longer read identically — trailing drawdown, firm trailing drawdown and peak equity giveback all report **`Inert`** with a stated reason on an account reporting no equity, while the daily loss limit correctly does NOT. ⚠️ **Both fixes were first written committing the defect they were fixing** (`ceil(1/ratio)` against a copy path that rounds midpoints TO EVEN; `> 0` against an account whose equity has gone negative) and **both were caught by writing the mutant, not by reading the code**. ✅ **`P1-121` CLOSED in session 49** — entered on the operator's *"the copier UI does not look like it is done"*, and it was not a feature gap: the window was finished and **wrong**. `_statusText` was a green `[ ENGINE: ACTIVE ]` literal assigned once at construction and **never again**, over rows reading `Armed: LIVE` that never consulted the global copier mode — so a `disabled` copier, submitting nothing, rendered as a healthy screen. Three producers (`GetCopierMode`, `DetectConfigConflicts`, `CopierMetric.Samples`) already computed all of it for the API; the UI consumed **none**, while a comment claimed it did. Decisions moved to `addons/CopierStatusView.cs` (no WPF type, so it can be mutated at all — `TradeCopierWindow.cs` is outside the test build). Suite **1846 → 1924**, battery **14/14**. ✅ **`P2-116` CLOSED (session 50)** — measured the hour the broker was reconnected: **89** prop accounts subscribed, **1** reporting any equity, **0** with any guard event ever, and all 89 reporting `Trailing drawdown: EvaluatedNotEnforcing`. `F-9`'s class in the OPTIMISTIC direction, on the surface built to answer *is the guard protecting me* (§5.65). ✅ **`P1-117`, `P2-119` and `P2-120` ALL CLOSED in session 48, and the last one is LIVE-VALIDATED both ways**: the config save now reports what it did and refuses what a write INTRODUCES, the window no longer edits the live config in place, and the bridge route stopped answering `success = true` regardless. Core **v1.31.0** deployed, `nt_compile` **0 errors**, guard loaded / shadow / armed / guarding. ✅ `P2-115` closed (§5.67) — but ⚠️ **only the positive live half is measured**: `true` with a broker attached is what the defect produced too, and showing `false` needs a broker disconnect that is the operator's call.
| **Branch** | **`main` only**, level with `origin/main`, all three repos. **30 tags**, `v1.0.0`…**`v1.23.0`** — measured 2026-08-14 (session 40) | `git status -sb; git describe --tags` |
| **Deployed** | **`v1.23.0` core + bridge are live in NT8** — core measured session 40 (`sync_nt8.py --verify` **ALL IN SYNC, 9 files**); bridge redeployed twice in session 41, adding `BridgeClosePlan.cs`, `BridgeAccountScope.cs` and `BridgeOrderQuery.cs` (`deploy.py --verify` **18 files, 0 orphans**), `nt_compile` `errorCount: 0` both times. ⚠️ **The core tag is unchanged and that is correct** — `P1-105` is entirely bridge-side, so the pin stays `v1.23.0`; a bridge fix does not move the core's tag | `python tools/sync_nt8.py --verify` here; `python tools/deploy.py --verify` in `nt8-mcp-bridge` |
| **Guard** | `v1.23.0`, `mode: shadow`, armed — **measured 2026-08-14 (session 40)** off the box: `RiskGuard Add-On v1.23.0 initialized in shadow mode` followed by `ARMED_ON_START` in `interventions.jsonl`, and `/api/riskguard/config` reads `Mode: shadow`, `DailyLossLimit: 1000.0` (restored byte-for-byte after `P2-107`'s live test) | `curl -H "Authorization: Bearer $(cat 'Documents/NinjaTrader 8/mcp_token.txt')" http://localhost:7890/api/riskguard/config` |
| **Box** | bridge `1.5.2-chart-discovery`, `dev: true`, **96 accounts**, **feed connected** — measured 2026-08-14 | `nt_health` |
| **Mutation** | **33 batteries** — **28 here** + **5 in `nt8-mcp-bridge`** (`mutate_p1105.py` and `mutate_p2109.py` added session 41, both wired into that repo's CI and verified by its own `check_ci_runs_every_battery.py`). ⚠️ **All FOUR bridge batteries could not RUN** until session 41 — three were fixed and the fourth was reported as a `SKIP` by the bulk patch and **not acted on**, which turned CI red on the next push (§5.50); now enforced by `tools/check_batteries_pin_encoding.py`, which runs BEFORE them. The cause: `capture_output=True, text=True` decodes cp1252 on Windows, so one non-ASCII character in a test message killed the reader thread and `res.stdout` came back `None`. `encoding='utf-8'` is pinned in all four now. **301 anchors / 0 broken** (was 283: `mutate_p2107.py`'s **18 anchors were being SILENTLY SKIPPED** because its 4-tuples put the file constant second and `check_anchors.py` `continue`d on any shape it did not recognise — see §5.48) | `python mutation/check_anchors.py`; `python tools/check_ci_runs_every_battery.py`; `python tools/check_expected_survivors.py` |
| **NT8 compile** | **0 errors, net48 — measured 2026-08-14 (session 40) on `v1.23.0`**, four times across the deploy and the live test. ⚠️ **ALWAYS read `errorCount`, never the call's own `success`** — a broken Custom assembly is invisible, because NT8 keeps serving the last good one | `nt_compile` |
| **CI** | **`nt8-riskguard` green on the two `P2-107` pushes, measured 2026-08-14 (session 40)**: 16m56s (code, 28-battery matrix) and 16m3s (docs). ⚠️ **Three later pushes and every `nt8-mcp-bridge` run were still QUEUED or IN PROGRESS when this row was written — they are NOT measured here.** Re-run before quoting. Run it BEFORE the first claim about state, not after a deploy | `gh run list --limit 5` in each repo |
| **Bridge pin** | ✅ **`v1.23.0`, and the RANGE is empty** — `git diff --name-only v1.23.0..main -- addons/` returns nothing, measured 2026-08-14 (session 40). ⚠️ **Compare the RANGE, never the tag's own commit**: a tag whose own commit is docs-only can still carry core code in its range | `git -C vendor/nt8-riskguard describe --tags; git diff --name-only <pin>..main -- addons/` |
| **Parse gate** | ✅ New: **`nt8-mcp-bridge/tools/check_bridge_parses.py`**. `McpBridgeAddOn.cs` is in no test build, so a stray brace there used to be findable only by deploying — and a syntax error in ANY addon `.cs` stops **every** addon loading | `python tools/check_bridge_parses.py` (verified by breaking a file on purpose) |

> ⚠️ **A GATE NOBODY READS IS A COMMENT. Keep this after the fix, because the fix is not the lesson.**
> `tools/check_version_matches_tag.py` reported constant `1.10.0` vs tag `v1.12.1` and **failed 7
> consecutive CI runs across three sessions while `v1.11.0`, `v1.12.0` and `v1.12.1` shipped over
> it.** The live box answered `1.10.0` to `GET /api/riskguard/version` — the endpoint an operator uses
> to ask what is guarding a funded account. The gate had been added by `c92605e`, titled *"the addon
> reported 1.1.0 while v1.2.0 was deployed — and now a gate says so"*: **built for exactly this
> failure, and then ignored.**
>
> ⚠️ **`gh run list` before anything else.** A red pipeline invalidates every state claim downstream
> of it, and §0 asserted CI was green and *"watched fail on purpose"* the whole time.
>
> **The durable rule, now with a second body of evidence: trust the git tag and the file hashes,
> never a version string.** `sync_nt8.py --verify` compares content; a version string compares
> nothing. And bump the constant **in the same commit as the tag** — the gate is red by design in
> between, which is the ordering trap that produced the original drift.

### What is deployed but NOT validated live

This distinction is the one this document has most often blurred, so it gets its own block.

> ✅ **THREE ITEMS GRADUATED OUT OF THIS BLOCK ON 2026-08-13 — see §5.36.** `P0-96` (the copier
> covers a short instead of doubling it), **`P3-30`'s guard audit** (fires correctly AND stays
> silent — 84 seconds flat with nothing logged, which is the half that could not be checked
> before), and **`P3-34`'s copier shadow mode**. All three on the deployed box, on sim accounts,
> with the guard armed in `shadow`.

* **`P0-53`, `P1-54`, `P0-55`, `P1-56`** — unit + compile only.
* **`P0-67`** — deployed since `v1.1.0`, unit + mutation only. **Nothing has driven
  `DynamicAtmManager`'s monitor live**; the bridge drives that path and tests none of it (`P2-27`).
  The sixth defect fixed with it (two `Change()` calls on one stop in a single sweep) is in the same
  position.
* **`P1-70`** — the settle-path confirmation is pinned by test, but no live trade has produced a
  `BRACKET_MODIFY_CONFIRMED` since the deploy.
* **`T5`'s fail-closed gate** — needs an acting mode; `IsGuardProtecting` requires `mode == "live"`.
* ~~**The firm-mirror rules** — loaded but unmapped~~ ✅ **VALIDATED LIVE 2026-08-13** (§5.28, §5.30).
  Six accounts are mapped to two size-and-variant-keyed plans, and their rules read
  `EvaluatedNotEnforcing` with the plan named in the row. Numbers come from the firms' published
  tables ([FIRM_PLANS_RESEARCH.md](FIRM_PLANS_RESEARCH.md)), **not** from the config backup — the
  recovered profiles carried no account size and two were deployed at the wrong one.
  ⚠️ What is *still* unvalidated is a **breach**: no firm rule has fired, so the trailing maths and the
  new `LockAtProfit` path have never run against real movement. And see `P2-95`.
* **The UI's WRITE half** — the page can toggle a relationship and release a quarantine, and those two
  are validated; **nothing else on it can be changed** (§5.6 item 4).

**Validated live**: `P1-86` (news shield reports `INERT` in production) and `P1-88` (an unknown copier
action now refused, where it used to answer `success:true, persisted:true`) — both §5.25, on
`v1.12.1`; **`P0-63` and `P?-66`** (§5.13 — the mirrored stop trails and both fills measured);
**`P0-68`, `P1-69`, `P1-71`** (§5.14); `P0-9`'s mirrored **stop** (§4l) and **target** (§4s);
`P0-50`'s orphan-stop release (§5.13); `P0-51`, `P1-52`, `P2-41`, `P0-48`; T3's giveback rule (§4g);
the reconciler + `P0-61`'s fix (§4v); and the ratio converter's slices 2 and 3b (§4z).

> ⚠️ **A deployed default is not an applied default, and session 29 proved it on this box.** The new
> `StopAttachSeconds` and `MinShadowSessions` defaults only apply to fields *absent* from the stored
> config; both were present with their old values, so the guard ran with `StopAttachSeconds = 3` after
> a clean deploy and a green suite. **After changing a default, go and read what the box holds**
> (§5.25).

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
dotnet run --project tests/RiskGuardTests.csproj --no-build -v q --nologo   # expect 1232/0

# deploy: verify, sync, then recompile IN NT8 (files on disk are not loaded code)
python tools\sync_nt8.py --verify        # expect ALL IN SYNC (8 files)
python tools\sync_nt8.py
#   then nt_compile, and read errorCount

# the structural checks (free, instant). RUN THESE FIRST. All four pass as of
# v1.13.0; one of them was red for 7 CI runs across three sessions while the docs
# claimed green, which is why they lead this list rather than trail it.
python tools\check_version_matches_tag.py     # the constant vs the newest tag
python tools\check_direction.py               # no addon may name a bridge-owned type
python tools\check_no_stray_copies.py         # no addon .cs outside addons/
python tools\check_ci_runs_every_battery.py   # no battery CI does not run

# ⚠️ CHECK THE ANCHORS BEFORE TRUSTING ANY BATTERY. A battery finds its mutant by
# an exact source substring; when an unrelated commit edits that source it prints
# [SKIP] and scores a SURVIVOR -- but only when run, and a battery only runs when
# the suite is green. This check reads every MUTANTS list by AST, takes ~1s, and
# WORKS WHILE THE SUITE IS RED. It found 11 stale anchors in session 29 alone.
python mutation\check_anchors.py         # expect 227 anchors / 0 broken

# the 20 mutation batteries. All exit NON-ZERO on a survivor and all refuse to run
# from a red baseline -- see §8, they were decorative until 2026-08-13. The newer
# ones also score a CRASH (no result line) as a kill, which the oldest three do
# not, because a mutant that crashes the runner read as a SURVIVOR (§5.14).
# DO NOT hand-maintain a list of them here -- the list that used to sit at this
# spot named 18 while 20 existed. Ask the filesystem, and ask CI whether it runs
# each one:
ls mutation\mutate_*.py
python tools\check_ci_runs_every_battery.py
ls mutation\mutate_*.py                  # 18 files; do not hand-maintain the list

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
  (§4p). In `shadow` they only log. ⚠️ **On 2026-08-13 the guard logged `MISSING_STOP_FLATTEN`
  twice**: `shadow` is the only reason the validation survived to produce evidence.
- **Re-measure the blast radius; do not trust the number below.** `Sim101 → Sim-ORB →
  {SimCopyTest1, SimCopy2}` is a live chain in principle, because `Sim-ORB` is our follower *and* a
  third-party copier's leader (`P1-57`, still open). **On 2026-08-13 only `Sim-ORB` acted**:
  `SimCopyTest1` got nothing because the third-party copier was not running, and `SimCopy2` was named
  active and then dropped. So `P1-57` is **not** exercised, and the fan-out is a property of what is
  running that day.
- **`SimCopy2` is effectively non-functional for micros**, and it will look like a defect if you
  forget it. It carries `AutoSymbolConversion: true` and maps to **NQ**, so one MNQ at ratio 1.0
  rounds below a whole contract and is dropped — now visibly, as
  `COPY_SKIPPED_SUB_MINIMUM` (§5.14). Size the leader's order for the conversion, or expect one
  follower fewer than the config implies.

<details><summary>Earlier headers, kept for the record</summary>

**Sessions 20–29, 2026-08-13** — the ten sessions this block failed to track, which is why it was
11 tags stale. `v1.1.0` → **`v1.12.1`**, suite 1003 → **1188**, 5 batteries → **18**. In order: the
five live-trade defects fixed (§5.14); the MCP wrapper widened, 5 arguments → 19 and 3 actions → 11,
opening four defects (§5.16); the feature audit and the UI design pass, which found a **third risk
system** in neither repo, `RiskGatekeeper.cs` (§5.17–§5.19); `UI1`…`UI7` — the rule inventory, the
copier conformance view, the browser page, refusals that say why (§5.20–§5.24); and session 29, which
**applied every config default** and closed `P1-82`…`P1-89` while opening `P1-90` (§5.25).

**Sessions 17–19, 2026-08-13** — `P0-63` (remedy 3) and `P?-66`'s instrumentation shipped, suite
953/0, three mutation batteries; then the documentation pass (§5.10, §5.12); then **the live
validation** (§5.13), which closed `P?-66`, proved the trail, and opened four defects. The header at
that point read *"the next item is `P0-67`"* — it was closed the same day.

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

> ⚠️ **THAT LAST SENTENCE IS NO LONGER TRUE, measured 2026-08-13 (§5.30).** A recompile still reloads
> the addon, but it now **re-arms**: the audit log shows `SHUTDOWN`/`INITIALIZE` followed by
> `ARMED_ON_START`, and `GET /api/riskguard/version` answers `isArmed: true` immediately afterwards.
> Almost certainly `P1-47`'s fix, which landed after this record was written. **Do not schedule a
> manual re-arm on the strength of this paragraph — check the endpoint.** The advice to check rather
> than assume survives; only the direction of the default changed.

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
- **Firm-mirror rules** are loaded but unmapped, so none of them fire. ⚠️ **True on 2026-08-07, false since 2026-08-13** — six accounts are mapped and their rules evaluate (§5.28, §5.30).

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

**Settled 2026-08-13 by session 20 (§5.14).** Five rules, all with a live or mutation-tested defect
behind them. The first three are the same rule at three levels: *do not record what you asked for as
though it happened*.

- **A cache of broker state is written ONLY from the broker.** `DynamicAtmManager`'s
  `bracket.CurrentStopPrice` is assigned in exactly one place — `ReconcileStopFromBroker`, from the
  live `Order` — and never from the value passed to `Change()` (`P0-67`). A polling monitor does not
  need settle events; it needs to stop trusting its own writes. Do not "optimise" the reconcile away
  because the request usually succeeds: on `provider: Simulator` it never does.
- **One outstanding `Change()` per order, at EVERY call site.** A second change while one is in
  flight is dropped **and reverts the order** to its pre-change values, so it ends at neither
  request's values (`P0-61`, established by a controlled live trade). The copier holds this with
  `bracket.StopInFlight`; the ATM manager now holds it with `RequestedStopPrice`. In `ScaledRunner`
  the breakeven and trailing moves could both fire in one sweep, which is how this was found — by a
  test, not by reading.
- **A log line must not claim an outcome it has not observed.** `..._REQUESTED` before the broker
  call, `..._CONFIRMED` only on settle, printing the **settled** values (`P1-70`). This applies to
  tooling too: `deploy.py` printed `[FATAL]` and exited 0.
- **A log message must not name another event type.** `grep BRACKET_MODIFY_CONFIRMED` matched a
  `REQUESTED` line that merely mentioned it in a hint. In a file whose whole purpose is post-hoc
  grepping, that is a defect, and it broke an absence assertion in the suite before it broke anything
  live. Tests use `LoggedEventType` for absence.
- **Every relationship named in `COPY_BEGIN` emits exactly ONE terminal outcome event**, matched by
  naming convention — `COPY_SUBMITTED` / `COPY_SKIPPED_*` / `COPY_BLOCKED_*` / `COPY_FAILED_*`
  (`P1-71`). So a skip path added later is counted automatically. **The corollary is load-bearing and
  was unpinned until a mutant found it: a non-terminal event must NOT take a terminal prefix.** Name
  a clamp or a quarantine `COPY_SKIPPED_*` and one relationship reports two outcomes while another
  drops in silence and the totals still look right.
- **A read endpoint must not mutate.** `/api/copier/config`'s `get` called `LoadFromDisk`, which
  **replaces the in-memory relationships that `ObserveFollowerFill` writes its measurements onto** —
  so reading the config destroyed the thing being read (`P1-69`). Its metrics are **session-scoped**;
  a recompile resets them, and a zero is not a measurement.
- **`ValidateInvariant` must not reject `PlaceStopOrder` on `action.Quantity > liveQuantity`**
  (settled landing T2). It looks like a missing safety check and it leaves the position
  permanently naked — see §1. `ExecuteAction` re-sizes from the live position.
- **`ArmGraceTimer` under `_stateLock` is correct and required** (T1). It only schedules a timer
  callback; it makes no broker call. Reviewers raise it as a lock-scope violation every round.
- **Reading `account.Positions` outside `_stateLock` is accepted.** A stale read yields a safe
  abort or a harmless spurious grace timer, not naked risk.
- **The TOCTOU window between the live position read and `account.Submit` cannot be closed**
  without holding a lock across a broker call, which is forbidden.

These are also encoded in **`agent/nt8_riskguard.py`** under `settled` (**26 entries**, ~1.7k tokens
— re-counted 2026-08-13 by importing the module, not by reading it),
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
  > ✅ **The guard fired for real on 2026-08-13** and it was right: the core had moved to `v1.1.0`
  > while the pin sat at `v1.0.3`, and deploying the bridge would have put a `v1.0.3` core over the
  > top of three live fixes. The working order is **tag core → push → bump pin → push → deploy →
  > recompile**, because a submodule cannot pin a tag that exists only locally.
  >
  > **This guard was itself broken on arrival and shipped with a passing three-direction test** — it
  > asked the vendored clone, which cannot see commits it has not fetched, so it answered "not
  > behind" for the one case that matters. Then the fix over-fired on docs-only commits. Both are
  > written up in §5.10. **Two rounds of getting a nine-line check wrong is the strongest argument in
  > this file for watching a gate fail before trusting it.**
- **A RED BASELINE FROM THE HARNESS IS NOT A RED BASELINE.** `node --test tests/` failed with
  `MODULE_NOT_FOUND` on the *directory*, which looked exactly like "my new tests fail because the code
  does not exist yet" — the evidence test-first work depends on. It proved nothing. The real red was
  6 assertion failures against 27 passes. **Read what the failure says, not that there was one**; this
  is the same class as a mutation battery scoring a crash as a survivor.
- **A dispatcher whose default arm is a READ turns every typo into a silent success.**
  `CopierConfig`'s if-chain ends in `else { read }`, so `action: 'quarantine'` — never implemented
  anywhere — returned the config with `success: true`, and so did `action: 'quarrantine'`. That is
  `P1-72`. Whitelist read actions and **throw on the rest**, at both the tool and the route.
- **`LoadFromDisk` DISARMS.** `PropFirmProtectionSuite.LoadFromDisk` ends in `UpdateConfig(cfg)` with
  no `confirmLive`, and that gate forces `ArmedForLive = false`. The gate is correct — it is what stops
  a config arming itself from a file. So **no read path may call `LoadFromDisk`** (`P1-75`), and the
  same is true of the copier's for a different reason (it discards live measurements, `P1-69`). Only
  the two `State.Configure` startup loads are legitimate. ⚠️ `P1-69` was fixed in **one of two** copier
  read branches and shipped as done: when a rule is "a read must not mutate", enumerate the reads.
- **A MUTANT that cannot fail is as useless as a test that cannot fail** — and it reads as the
  opposite. The `P0-67` mutant written to reinstate the defect verbatim read
  `bracket.RequestedStopPrice` *after* the reconcile resets it to `NaN`, so it could not change
  behaviour and survived. A surviving mutant looks exactly like "your tests are decorative" until you
  read the mutant. **Before believing a survivor, prove the mutant changes behaviour at all**
  (§5.14). Same error as a vacuous gate, one level up.
- **A mutation battery must score a CRASH as a KILL.** A `P1-71` mutant renamed an event, a test's
  `log.First(...)` threw, the runner died, and the battery — which looks for a failure count in the
  output — found **no result line** and recorded a **SURVIVOR**. The two newest batteries treat
  `NO RESULT LINE` as a kill; `mutate_cm3`/`cm4`/`p0_63` still do not.
- **`Assert` records a failure and RETURNS; it does not halt the test.** So a null dereference on the
  line after a failed assert throws for real and aborts **every test after it in the run** — which
  presents as dozens of unrelated failures. Guard the value (`x = x ?? string.Empty`) rather than
  assuming the assert stopped anything.
- **The copier's latency/slippage metrics are session-scoped, and a recompile resets them.** The
  first `GET /api/copier/config` after the `P1-69` deploy returned `0.0` for exactly that reason. **A
  zero is not a measurement** — it is indistinguishable from "no fill observed yet", which is why the
  response now carries a `metricsNote`. Read it before concluding the instrumentation is broken; that
  conclusion has already been drawn wrongly once (`P?-66`).
- **A gate that cannot fail is worse than no gate**, and this repo has shipped four of them. The
  mutation batteries printed `SURVIVORS: [...]` and exited **0** until 2026-08-12; then `mutate_cm3`
  and `mutate_cm4` were found to be **vacuous from a red baseline**, because `killed = 'Failed = 0'
  not in res` scores every mutant as killed when the baseline is already failing. All **five** now
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
  `"applied"`. It merges now, but the habit stands: **GET, mutate, POST, GET, diff.**
  `/api/copier/config` had **no GET at all** until 2026-08-13, so the copier's live config could not
  be inspected without writing to it; it has one now (`P1-69`), and it no longer reloads from disk on
  the way — see §7.
- **`BRACKET_MODIFIED` and `BRACKET_TARGET_MODIFIED` NO LONGER EXIST** (`v1.1.0`, `P1-70`). Anything
  grepping `interventions.jsonl` for them finds nothing — including scripts and notes written by
  earlier sessions. The replacements are `BRACKET_MODIFY_REQUESTED` / `BRACKET_MODIFY_CONFIRMED` and
  the `TARGET` pair. That is a **breaking change for a log consumer**, which is why `v1.1.0` is a
  minor, not a patch.
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
# every BANDED defect ID that has an entry in the plan. The three P?- IDs do not
# match (the pattern requires a digit after the P) and are counted separately below.
grep -oE "^### ~?~?(P[0-9]\?*-[0-9]+)\." docs/RISKGUARD_COPIER_HARDENING_PLAN.md \
  | grep -oE "P[0-9?]+-[0-9]+" | sort -u | wc -l      # -> 106, re-run 2026-08-14 (session 39)
```

> ⚠️ **What §0's total is MADE OF, because the two numbers do not match and session 36 had to
> reverse-engineer the difference.** The grep above returns only the **banded** IDs that have a plan
> entry. §0's figure adds two families that live in this file instead:
>
> | Family | Count | Where |
> |---|---|---|
> | banded `Pn-m` entries in the plan | **106** | the grep above |
> | untriaged `P?-64`, `P?-65`, `P?-66` | **3** | §5.2 — all three CLOSED, and listed as open work until session 39 |
> | `F-9`…`F-17` findings | **9** | filed here and never given a plan entry. `F-1`…`F-8` are FEATURES (§5.17), not defects |
> | **§0's total** | **117** | 103 closed, 14 open |
>
> That composition was **not written down anywhere** until session 36, so `107` in §0 and `98` from
> the grep read as a contradiction rather than as two different questions. If you change either,
> change this table in the same commit. ⚠️ **Session 39 re-derived every figure**: the grep had moved
> 98 → 106 while §0 still said 108, and `F-16` had been filed into a family the table capped at
> `F-15`. `tools/check_next_list_ids.py` derives the open/closed split now, so only the totals are
> hand-carried.

| | Count | Which |
|---|---|---|
| Banded entries in the plan | **106** | the `grep` above. **13 open**: `P1-106`, `P2-107`, `P1-105`, `P1-102`, `P2-103`, `P1-77` (deferred), `P2-78`, `P1-81`, `P2-29`, `P3-33`, plus `P0-9`, `P1-13` and `P2-27` marked PARTIALLY CLOSED with a recorded remainder |
| Awaiting a band letter | **3** | `P?-64`, `P?-65`, `P?-66` — §5.2. **All three are CLOSED** (`P?-66` in §5.13, `P?-64`/`P?-65` in §5.21). ⚠️ They were listed as outstanding work in every ordering block until session 39 |
| `F-` findings | **9** | `F-9`…`F-17`, **all closed** as of 2026-08-15 (`F-16` in §5.62; **`F-17`** — connection visibility and control — in §5.68). ⚠️ `F-1`…`F-8` are the operator's FEATURE list (§5.17), **not defects**, and are deliberately excluded |
| **Total IDs** | **117** | **103 closed, 14 open** |

⚠️ **The table that stood here said 90 / 93 / 14 / 79 and contradicted the composition table
directly above it** — two hand-maintained summaries of the same entries, in the same section,
disagreeing. It is replaced by counts that `tools/check_next_list_ids.py` derives, which is also
what now forces every plan entry to carry a status token: until session 39 fourteen carried none,
so any mechanical count had to be corrected by hand against a prose note two hundred lines away.

⚠️ **Session 29 added nine IDs** (`P1-82`…`P1-90`) and closed eight. ✅ **Session 30 closed the
ninth, `P1-90`, and live-validated it** (§5.26) — six sites, not the three that were filed. It
**opened `P1-91`** in a third repo: four MCP tool schemas still advertise the `Sim101` guess, two of
them order tools.

> ⚠️ **The counts above and in §0 were re-derived on 2026-08-13 after session 30. They were 11 tags
> stale before that** — §0 said 78 IDs while the entries said 92 — because ten consecutive sessions
> appended a record and none returned to the header. **Re-run the `grep`; do not trust the table.**

`P0-62` counts as **resolved-by-supersession**, not fixed: `P0-63` subsumed it (the call
is a silent no-op for price *and* quantity, not a quantity-only refusal) and `P0-63` is
fixed. Numbers are **never reused and never renumbered** — `P0-64`…`P0-66` are held for
the three above, which is why `P0-67` is the newest ID despite being opened before they
were triaged.

## 5.1 Open defects, by band

> ✅ **`P0-67`, `P0-68`, `P1-69`, `P1-70` and `P1-71` were all FIXED, DEPLOYED and (where
> observable) LIVE-VALIDATED on 2026-08-13 — §5.14.** They are struck from the table below rather
> than deleted, because the digits are never reused.
>
> ⚠️ **The state figures that used to sit in this banner have been removed rather than updated.**
> It said "suite 1003/0, five mutation batteries, core is tag `v1.1.0`, bridge pin bumped to match" —
> every number wrong within a few sessions, and the pin claim wrong twice since (it has gone stale in
> session 30 *and* session 33, both times caught by `deploy.py` refusing). **Current state lives in
> exactly one place, §0, and is derived there.** A second copy of a number is a second thing to
> forget — which is the whole reason this banner no longer carries any.

| ID | What | Band | Notes |
|---|---|---|---|
| ~~**`P1-91`**~~ ✅ | **MCP tool schemas advertised an account, and an action, the caller never sent** | P1 | **FIXED 2026-08-13 (§5.27)** through the agent-loop. It was **six** defaults, not the four filed — the class-level test found two more on `action`, incl. `nt_alert` defaulting to `webhook` beside a `flatten` enum. In **tvDownloadOHLC**, now `mcp/ninjatrader-mcp/lib/tools.js` (extracted from `nt-mcp-server.js` so tests can import the real schema objects). ⚠️ **Only in effect once the MCP server RESTARTS** — schemas are read at startup. ⚠️ And measure rather than assume what it bought: that server **never reads `.default`, never reads `inputSchema`, and does not validate `required` at all**, so deleting a default is real for any client that materialises them while `required` adds **no server-side gate**. The enforcement stays the addon's refusal |
| **`P2-95`** ⚠️ | **`FirmStartingBalance` is a session-start heuristic, so the trail-lock floor is wrong by the account's LIFETIME PROFIT** | P2 | **NEW 2026-08-13 (§5.30).** `ComputeFirmMirror` captures `balance - realized - unrealized`, and `realized` is session-scoped. On an account up $5,000 over its life it reads 55,000 instead of 50,000, so the guard flattens ~$5,000 early — and the error grows as the account does, which is R5's failure mode getting worse the better you do. `FirmProfile.AccountSize` is the fix and is why it exists. **Do this first**: `LockAtProfit` carried a real value for the first time the same day, so the path is live |
| **`P2-94`** ⚠️ | **A TIMED manual lockout does not stop new orders** — `CanTrade` never reads `LockoutUntil` | P2 | **NEW 2026-08-13 (§5.30).** `LockAccount(name, 60)` sets only `LockoutUntil`; `CanTrade` reads only `IsLockedOut`; an existing test asserts that asymmetry. The sweep *does* read both, so it flattens the fills the guard just admitted — worse than a clean refusal. Same family as `P2-92`: one lockout, two consumers, disagreeing |
| **`P2-93`** ⚠️ | **`pure` and `override_with_friction` pass preflight's ENFORCEMENT gate and then act on nothing** | P2 | **NEW 2026-08-13 (§5.30).** Four modes are recognised and the `MinShadowSessions` gate treats three as enforcement modes — but `IsActingMode()` returns true only for `live`, so `ProcessAction` answers `SHADOW (SKIPPED)` for both. An operator waits out five shadow sessions to reach a mode that enforces nothing. Fail-closed one-liner: stop recognising them. Implementing them is a protection *increase* and the operator's call |
| ~~**`P2-92`**~~ ✅ | **`shadow` mode was not observation-only: a shadow breach stopped the account trading** | P2 | **FIXED 2026-08-13 (§5.29, §5.30).** `ProcessAction` gated execution on mode, but ten rule paths set `IsLockedOut` before dispatch and `CanTrade` read it **above** its own arming hatch — so nothing was flattened and the copier and every strategy stood down, with the reason logged to `Output.Process` only. Fixed by recording the AUTHORITY a lockout was imposed under. ⚠️ **Not** by making `CanTrade` consult the current mode: that would make a mode switch a lockout bypass. 11 mutants / 0 survivors |
| ~~**`P1-90`**~~ ✅ | **An order naming an account that does not resolve was PLACED ON AN ARBITRARY ONE** — the chain was *named account → `"Sim101"` → ANY non-Backtest account → ANY account at all* | P1 | **FIXED, DEPLOYED AND LIVE-VALIDATED 2026-08-13 (§5.26)**, one day after it was filed. **Six** sites, not the three filed — and `HandleLockout` was the sharpest, feeding the guess to `UnlockAccount`, which REMOVES protection, with no existence check. Resolution moved to `addons/BridgeAccountResolver.cs`, which names no NT8 type and is therefore **executed** by tests (bridge suite 23→50) rather than grepped. First mutation battery in that repo: 11 mutants / 0 survivors. Opened `P1-91` |
| ~~**`P0-68`**~~ ✅ | **`nt_change_order` reports `"status": "modified"` when the provider ignored the change** — the FOURTH `Account.Change()` site, in the bridge, with none of `P0-63`'s detection | P0 | **NEW 2026-08-13; was the highest open defect for one day.** Reproduced in isolation, twice (§5.13). Anything trailing a stop through MCP silently does not move, and **the unchanged price is already in the response body** next to the success claim. Cheapest possible fix: apply `P0-63`'s settle-then-verify, or at minimum stop claiming success |
| ~~**`P0-67`**~~ ✅ | **`DynamicAtmManager` holds the THIRD `Account.Change()` call, and its cache records the price the broker refused** — so the trail latches at a stale value | P0 | Same root as `P0-63`, different call site; found by widening `P0-63`'s "Where" clause (§5.8). **Establish whether that path is live first** — the bridge drives it and tests none of it (`P2-27`). **Do this together with `P0-68`**: four sites, one root cause, and `P0-63` already contains the remedy |
| ~~**`P1-69`**~~ ✅ | **The copier's latency/slippage metrics are computed and then discarded** — in-memory only, never persisted, no read path | P1 | **NEW 2026-08-13.** The half of `P?-66` that does *not* close. Fix with the `GET` on `/api/copier/config` (§5.3) or the metrics stay invisible however well they are measured |
| ~~**`P1-70`**~~ ✅ | **`BRACKET_MODIFIED` writes a false success line to the audit log** before the provider settles, and is contradicted milliseconds later | P1 | **NEW 2026-08-13.** Not naked risk — the detection catches the underlying no-op — but a live audit log that asserts "no unprotected window" before it can know is how the last three sessions lost time |
| ~~**`P1-71`**~~ ✅ | **A named active relationship produced no order and left no diagnosable trace** (`SimCopy2`) — four unlogged exits in the copy loop | P1 | **NEW 2026-08-13.** `followerAcc == null` logs nothing; three `CanTrade`/`NO_GUARD` blocks log to the Output tab only, which no readable sink captures. Route them through `CopierLog` — the fix is mechanical and the payoff is that this class stops being invisible |
| `P1-57` | We would mirror another copier's mirror; the "not ours" test is a name substring | P1 | Live on this box: a third-party copier fans `Sim101 → Sim-ORB → {SimCopyTest1, SimCopy2}` copying names verbatim |
| `P1-13` | Guard evaluation on the WPF dispatcher — **threading half only** | P1 | The fail-open half is closed |
| `P2-24` | Written-but-never-called safety machinery | P2 | |
| `P2-25` | The news shield can never fire in production | P2 | Still open. `P1-82` defaulted its flag OFF so the config stops asserting it, and `P1-86` makes it report `INERT` **either way** — neither is a fix for the rule (§5.25) |
| `P2-26` | Design-doc drift in `RiskGuardAddOn.md` | P2 | |
| `P2-27` | The riskiest code has zero coverage | P2 | **Step 1 done (§5.24)**: the NT8 stubs are extracted to `tests/TestingStubs.cs` so another repo can consume them. `McpBridgeAddOn.cs` and `TradeCopierWindow.cs` are still outside the test build — which is why `P1-88`/`P1-89`/`P1-90` could only be found on the live box, and why the agent-loop **cannot gate the bridge at all** |
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
| **UI redesign** | The operator's own assessment: *"not very usable or professional enough"*. On top of `P?-64`/`P?-65`, `PerTickerMatrix` is not in either sizing-mode combo (`:367`, `:459`) and `PerTickerRatios`/`CustomSymbolMappings`/`MaxSlippageTicks` have **no editor at all** — they appear only in a read-only status string. **The ratio converter is reachable ONLY through the bridge today.** ✅ **DESIGNED 2026-08-13 — [UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md)** (§5.19). Two goals only: configure both systems, and prove they are doing what was configured. Organizing idea is **conformance** (configured vs actual vs verdict) and a **CONFIGURED / EVALUATED / ENFORCING** three-state that four shipped defects share. Host reversed to a local browser page — §5.5. |
| **MCP wrapper gap** | `nt_copier_config` accepts only `leaderAccount`/`followerAccount`/`quantityRatio`/`autoConversion`. It cannot express `sizingMode`, `perTickerRatios`, `customSymbolMappings`, `maxSlippageTicks`, or any group action. Session 15 had to drive raw HTTP to `localhost:7890`, which `.agent/USER.md` asks agents not to do. **The preference is unfollowable until the wrapper is extended.** |
| ~~**`/api/copier/config` has NO read**~~ | ✅ **DONE 2026-08-13** as part of `P1-69` (§5.14). The route was **`Post(method, …)` only**, so the live copier config could not be inspected without issuing a write — which defeats the GET-mutate-POST-GET-diff discipline this project relies on (§7), and is why `P?-66`'s live metrics could not simply be read off the box. It is now `return method == "GET" ? CopierConfig(null) : Post(…)`. ⚠️ The fix was **not** the one-liner it looks like: the `get` action was also calling `LoadFromDisk`, which threw away the in-memory measurements it was being asked to report. |
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

**Questions only the account holder can settle.** The `Account.Change()` one blocks nothing; the
firm-plan ones each block a group of accounts from being mapped at all.

0. **Which plan is each remaining account on?** — added 2026-08-13. This is the whole of what is left
   of `F-9`, and it is **information, not code**: only **6 of the 96** accounts report any equity, and
   no field in the platform payload carries a plan size, so it cannot be measured. Firm + size would
   not be enough even if it could — every one of the four firms sells multiple rule sets at one size
   (see [FIRM_PLANS_RESEARCH.md](FIRM_PLANS_RESEARCH.md)).
   * **Which `APEX*` accounts are the exception to the realised DLL basis?** The operator confirmed
     everything is realised *except some Apex accounts*, without naming them.
   * **Are the `APEX*` evaluations the EOD or the intraday product?** They differ in whether a daily
     loss limit exists **at all** — $1,500 on a 100K EOD, none on the intraday.
   * **What does `FTDFYG`'s leading `F` denote, as distinct from `TDFYG`?** `TDYG` is Tradeify Growth
     and the `F` marks funded, which leaves `FTDFYG` unexplained.
   * **Which Lucid plan are the `LFE*` accounts on?** `LFE` is a Lucid evaluation; Flex has no DLL
     anywhere, Pro's is a soft breach at 1,200/1,800/2,700 by size.
   > ⚠️ And the boundary of what the machine can ever check: `F-9b` validates **account ↔ plan** size
   > and **cannot** validate **plan ↔ firm table**. The `Apex-100K` profile that shipped on
   > 2026-08-13 would have passed the size check easily while holding Apex's **50K** amount, because
   > 2% and 3% of 100k are both plausible. Only the firm's published table distinguishes them, so
   > that comparison is a scheduled human step, not a gate.

**And the two that were already here:**

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
| ~~Where the redesigned UI lives~~ | ~~**Rewrite `TradeCopierWindow.cs` properly, in NT8.** Not the web app.~~ | ⚠️ **REVERSED 2026-08-13 by the operator** — see [UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md) §7. The UI becomes **a local static HTML+JS page served by the bridge over localhost**, launched from the existing NT8 menu item. Two facts found after the original decision forced it: **NT8's `bin/Custom` contains no `.xaml` at all** (it compiles `.cs` only, which is why the current window is 1118 lines to draw four tabs), and **a compile error in any addon `.cs` stops every addon loading, RiskGuard included** — an unacceptable property for the least critical component. WebView2 was considered and rejected: it fixes authoring cost but keeps the blast radius **and** adds three DLLs to NT8's Referenced Assemblies, a machine-local setting `sync_nt8.py --verify` cannot see. It stays offline-capable and no cloud surface is added. |
| `P0-63` remedy | **Remedy 3 only** — after every `Change()`, read the order back and fall back to cancel-then-create when it did not take. **No funded-account order.** The `Provider31` question stays open on purpose; remedy 3 is correct either way. | ✅ **Shipped and deployed 2026-08-13** exactly as decided. One refinement forced by the evidence: the read-back must happen **on settle**, not synchronously — NT8 leaves the caller's desired values on the `Order` until the provider settles, so an immediate read always says "it took" (§5.9). |
| What the next session opens with | **`P0-63` + the `P?-66` log line.** Safety first: the trail has never worked and no slippage number currently means anything. | ✅ **Both done** — session 17, then live-validated in session 19 (§5.13). Superseded by §5.6, which now opens with `P?-64`/`P?-65`, the copier UI — `P0-67` came and went in session 20. |

⚠️ **Consequence of the WPF decision, and it is the same trap as slice 3b:**
`TradeCopierWindow.cs` is **excluded from `RiskGuardTests.csproj`** (as are
`McpBridgeAddOn.cs` and `RiskManagerAddOn.cs`). So the rewrite must **not** put
request→object mapping in the window. Move it onto `TradeCopierEngine` — the window
should call `ApplyGroupRequest`/`ApplyRelationshipRequest` and the single
`CopierConfigFile`, exactly as the bridge now does. Anything left in the window can only
be pinned by source-text regex, which is not evidence. That single move closes `P?-64`
and `P?-65` together and makes the redesign testable.

## 5.6 Order of work

**Updated 2026-08-13 (session 34).** Finished items are struck through rather than deleted, because
the *order* they forced is the reusable part.

> ### Do next: `P2-127` (⚠️ **§5.82 first: the commit that CLOSED `P1-130` broke a `mutate_p0_67.py` anchor by SPLITTING one log call into two, so CI was RED on both of those pushes — including the `v1.35.0` tag push — and the whole 27-job matrix behind that gate never ran. Repointed, battery re-run 10/10 KILLED.** ✅ `P1-130` FIXED and live-validated the same session, §5.80 — but the ATM breakeven is still NOT proven end-to-end: the Simulator ignores the change — `P0-63`, closed, its known behaviour, so a non-Simulator account is needed) — — build §4's fleet/inspector layout on the BROWSER UI at :7890/ui (✅ `P1-125`, `P3-122`, `P2-129` and `P3-128` ALL CLOSED in session 51 and live-validated; see §5.78 and §5.79)
> ### (order of work lives in §5.78's `Order from here`: `P2-127`'s §4 layout — the layout is SETTLED, do not re-open it — then `P2-126`'s write surface, then `P2-29`'s remainder / `P3-118` / `P3-124` / `P3-110` / `P3-33`)
> ### (✅ `P3-128` CLOSED v1.34.0 session 51 — was `[ COPIER LIVE - SIM ONLY ]` over a copier whose every relationship is OFF; found by reading the live payload of the ticket that put that sentence on screen, fixed by the agent loop, live-validated)
> ### (✅ `P2-115` closed 2026-08-15 — §5.67; ⚠️ only the POSITIVE live half is measured)
> ### (✅ `P2-112` closed 2026-08-15 — §5.64; ⚠️ its stop-MOVE half is still unmeasured)
> ### (✅ `P2-108` closed 2026-08-15 — §5.58)
> ### (✅ `P1-102` closed 2026-08-15 — §5.57)
>
> **Updated session 41 (2026-08-14).** Every block below this one is struck through and
> kept for the order it forced, not for its contents. ✅ `P1-105` closed in session 41 — see
> §5.49; its remainder is filed as `P2-109` and `P3-110`, not left inside the closed entry.
>
> ⚠️ **This block had been carrying SIX closed IDs, and that is why
> `tools/check_next_list_ids.py` now exists.** `P2-95`, `P2-93` and `P2-94` were closed in
> session 34 and still headed the order of work nine sessions later; all three `P?-` UI
> write items were closed in §5.13 and §5.21 and were still listed as outstanding. Nobody
> added them back: each session wrote its ordering block by copying the previous one and
> striking the item it had just closed, so **an item closed while it was NOT at the head of
> the list was never struck by anybody.** Closures propagated forward into the record and
> never backwards into the ordering. The gate reads this block, §0's `Do next` row and the
> newest `Order from here` against the plan's per-entry status, and fails in both
> directions — it also requires every plan entry to *carry* a status, which is the half
> that would have rotted. **It earned its keep in session 40**: it named all three surfaces
> the moment `P2-107` (closed) flipped status, before anything was committed.
>
> ✅ **`P1-106` closed in session 39** (section 5.47) — a lockout now admits an order that
> strictly reduces the position, and refuses a bracket even when its entry would. Refusal half
> live-validated; the admit half rests on an 8/8 battery, because **nothing on the box can impose
> a lockout on an account that holds a position** (section 5.47; `P1-102` is now closed, §5.57).
>
> ✅ **`P2-107` closed in session 40** (section 5.48) — the outbound de-duplication now lives in
> `GuardActionDeduplicator` behind one `DispatchActions` that all five emission sites use, the
> record clears when the **condition** resolves rather than on a timer, and the operator's panic
> buttons deliberately bypass it. Suite 1469/0, battery 18/18. ⚠️ **Read §5.48 before adding a
> gate anywhere**: that battery went 13/13 on its first run and five later mutants all survived,
> including one that walked the measured path around the whole mechanism — and **two of this
> repo's own gates were caught proving nothing**, both by detection-by-substring over a region
> nobody bounded.
>
> **`P1-102` is the item to do next** (`P1-105` and `P2-109` closed in session 41, §5.49 and
> §5.52), then `P2-112`, `P3-110`, then the architectural `P2-29` / `P3-33`. ✅ `P2-108` closed §5.58.
> ✅ `P2-103` also closed in session 41 (§5.53); ✅ `P3-111` closed in session 42 (§5.54),
> live-validated in full and **rebanded — it was filed `P3` and was a `P2`**, because the entry
> named the one defect of four that is LOUD.
> Weigh by §5.6's consequence rule, not by band letter — `P1-90` (closed) was a `P0` on
> consequence. ⚠️ **And weigh by whether the evidence is OBTAINABLE now**: ✅ `P2-109` (closed) was
> taken ahead of `P1-102` (closed) on a Friday evening because it needed no market, while its live
> half needs an account holding a position.

> ### ~~Do next: `P1-99` — the copier's SIZING GRAIN~~ (session 36, superseded)
>
> **Updated session 36.** The block below is session 35's and is superseded by this
> paragraph; it is kept because the order it forced is the reusable part, and because
> item 1 in it (the copier mode's read surface) has since landed.
>
> **`P1-99` is the item to do next, and it outranks everything else open on
> consequence, not band letter.** The copier runs the whole copy path **per leader
> EXECUTION**, so a leader order is scaled and rounded slice by slice. Under MNQ→NQ
> conversion a 100-lot order filling as **20 × 5** drops every slice: leader long 100,
> follower **FLAT**, twenty routine `COPY_SKIPPED_SUB_MINIMUM` lines and no error
> anywhere. Found by driving the box during `P2-98`'s live validation (§5.38), where it
> came out right only by luck (5 + 95). The follower's size is a function of **how the
> leader's order happened to fill** — a property of the book, not of the trade.
>
> ⚠️ Two things to carry into the fix. **Rounding a slice harder is the wrong answer**:
> rounding 5 MNQ up to 1 NQ doubles the copy on a 20-slice fill. And **the exit side is
> not symmetrical** — `P0-6`'s exit clamp mirrors the follower's actual position rather
> than scaling the leader's quantity, so exits do not have this defect and must not
> acquire it. Plan entry `P1-99` has the two candidate shapes.
>
> ⚠️ **Any test for it must feed MULTIPLE executions for one leader order.** Every
> existing copy-path test sends a single execution for the full quantity. That is the
> same blind spot `P2-98` had on the follower side, and it is why a green suite, 24
> mutation batteries and a clean compile passed over both.

> ### ~~Do next: the copier mode's READ SURFACE, then the architectural items~~ (session 35, superseded)
>
> **Updated session 35.** `P3-34`'s core landed in `v1.15.0` — the copier has its own
> `live`/`shadow`/`disabled` mode and preflight gates the move to `live`. ⚠️ **But
> `CopierMode` is not in the `/api/copier/config` payload**, so the operator cannot
> observe or set it over the bridge, only by editing the config file. **A mode you
> cannot read is a mode you cannot trust** — that is item 1, and it is a bridge change
> (`P2-27`: untested) that belongs with the UI write half below.
>
> Item 2 is **`P2-27` coverage for `ReconcileFollowerPosition`**, then wiring it: it is
> the last entry in `check_no_dead_safety_machinery.py`'s `KNOWN_DEAD`, it sits inside
> `#if !TESTING`, and it **flattens a live follower position**. §5.32's claim that the
> P3-31 timer calls it is **false**; the timer calls `SyncFollowerStopOnce`/
> `SyncFollowerTargetOnce`.
>
> Then **`P2-29`** (file complexity) and **`P3-33`** (global lock → actor model), which
> are architectural upgrades rather than defect fixes, and the 3 `P?-` UI write items.
>
> Session 34 closed: P2-95, P2-93, P2-94, P3-31, P3-30, P1-57, P1-13, P2-25,
> P2-24, P3-32 (superseded), P2-26 (drift table updated), P2-27 (partially
> closed). P1-77 honestly reported, implementation deferred. ⚠️ **P3-30's audit was
> re-opened and re-closed in session 35** — see §5.33; it had shipped compiled out of
> production.
>
> **`P2-29`** — split `RiskGuardAddOn.cs` (6740 lines) into partial classes.
> **`P3-33`** — replace the global lock on the hot path with an actor model.
> **`P3-34`** — arm/shadow discipline extended to the copier (preflight, shadow mode).
> These are architectural upgrades, not defect fixes. The 3 `P?-` items are UI
> write/sync issues (`P?-64`, `P?-65` — copier window writes to a different file;
> the UI write half is barely started).

> ### ✅ Both mechanical chores are DONE (session 30), and so is `P1-90`
>
> Kept rather than deleted, because the *order* they forced is the reusable part.
>
> **A. `Version` bumped to `1.12.2`** — CI is green again and the live box answers `1.12.2`. It had
> been red for 7 runs on a correct gate; see §0's block, which keeps the lesson after the fix.
>
> **B. The bridge pin bumped to `v1.12.2`.** It had been at `v1.12.0` against a `v1.12.1` core with
> `addons/GuardRules.cs` in the range, so deploying the bridge would have reverted a live core file.
> `deploy.py` refused (exit 2), and that refusal **dictated the sequence**: bump pin → fix `P1-90` →
> deploy once. Anything landing in the bridge inherits that ordering, so check the pin first.
>
> **`P1-90` is fixed, deployed and live-validated** — §5.26. The next item is **`P1-91`**, which it
> opened.

0. ~~**`P1-91` — MCP tool schemas advertise an account the addon now refuses.**~~
   ✅ **DONE 2026-08-13 (§5.27), through the agent-loop.** It was **six** defaults, not four: the
   class-level test found two more on `action`, one of which defaulted to a cross-account
   `sync_hedge`. ⚠️ **Restart the MCP server** — schemas are read at startup, so a running client
   still advertises the old ones until then.

0. ~~**`P1-90` — an order naming an unresolvable account is placed on an arbitrary one.**~~
   ✅ **DONE and LIVE-VALIDATED 2026-08-13 — §5.26.** All **six** sites refuse, not just the three
   order paths; the other three were triaged individually and `HandleLockout` turned out to be the
   sharpest of them (it fed the guess to `UnlockAccount`, which removes protection, with no existence
   check at all). The `P2-27` trade named here was **avoided rather than accepted**: the resolution
   moved into `addons/BridgeAccountResolver.cs`, which names no NT8 type and is therefore *executed*
   by that repo's tests. That repo now has real behavioural coverage, its first mutation battery, and
   a parse gate.

Then the previous ordering:

0. ~~**Live-validate what is already deployed**~~ ✅ **DONE 2026-08-13 — §5.13.** `P0-63` trails on a
   real broker path; `P?-66` is answered and closed. It cost one 1-lot MNQ round trip and produced
   four new defects, which is the return this project keeps getting from a live trade over a test.
1. ~~**`P0-68` + `P0-67` together**~~ ✅ **DONE 2026-08-13 — §5.14**, along with `P1-69`, `P1-70` and
   `P1-71`. All five are deployed as core `v1.1.0` + bridge, and `P0-68`/`P1-69`/`P1-71` were
   live-validated. A sixth defect (two `Change()` calls on one stop order in a single sweep) was found
   by the `P0-67` trail test and fixed in the same change.
2. ~~**`P?-64` + `P?-65` together**~~ ✅ **DONE — `UI2`, §5.21**, deployed in `v1.3.0`. The mapping
   went on the ENGINE, as required, because `TradeCopierWindow.cs` is excluded from the test build.
3. ~~**MCP wrapper.**~~ ✅ **DONE 2026-08-13 — §5.16.** `nt_copier_config` went from 5 arguments to
   19 and from 3 actions to 11; reads go over `GET`; an unknown action is refused instead of silently
   reading. It opened four defects on the way (`P1-72`…`P1-75`), which is the return this project
   keeps getting from *widening* a surface: you have to state what each field does, and then check.
4. **UI redesign** — **the READ half is done** (`UI1`…`UI7`, §5.21–§5.24): the rule inventory, the
   copier conformance view, the browser page, and refusals that say why.
   ⚠️ **The WRITE half is barely started.** The page can toggle a relationship and release a
   quarantine — the two actions that already had engine-side refusal gates — and nothing else on it
   can be changed. **Goal 1 of the two this UI exists for, *configure both systems*, is still
   mostly untouched.**
5. Then `P3-31` ledger → timer → RiskGuard-side audit (`P3-30`'s remaining half), in that order.
   **The ledger comes BEFORE the timer** — between `Submit` and `Accepted` an order is in neither
   `Account.Orders` nor the cache, so a timer alone creates the second leg.

`P1-57`, `P1-13`, `P1-77` and the rest of the `P2` band are real but none is naked-risk; schedule them
after the three at the top of this section.

**Three items session 29 named rather than left to be rediscovered:**

* ~~**`F-9` — the firm mapping**~~ ✅ **DONE and LIVE 2026-08-13 (§5.28, §5.30), with `F-9b`.** Six
  accounts mapped; keys carry the **plan variant** as well as the size, because every one of the four
  firms sells multiple rule sets at one size. Preflight now refuses a mapping naming an account that
  does not exist, or a plan whose stated size contradicts the account.
  ⚠️ **What remains is information, not code**: only 6 of the 96 accounts report any equity and no
  platform field carries a plan size, so the other ~89 cannot be mapped until the operator states
  which plan each is on. The open questions are listed at the end of §5.30.
* **A copier field registry.** `P1-83`'s gate is a source scan and says so — it cannot catch
  `P2-25`'s class on the copier side (a field genuinely read, by a branch that can never fire). The
  guard side needed a runtime registry for exactly that.
* **The attribution gap** (§5.24). `interventions.jsonl` answers *what changed* and cannot answer
  *who*. Needs a decision on what identity means here before it can be specified.

> **Two suite gaps remain worth closing alongside whatever comes next.** Both are places where the
> suite currently *cannot fail*, and neither is naked-risk.
>
> 1. An **S7-style concurrency test for the `SyncFollowerStop`-vs-`...Once` reservation** — the most
>    serious defect found in the `P0-63` candidate, and still unpinnable. Recorded in
>    `mutation/mutate_p0_63.py` beside the mutant that measured it.
> 2. The **quantity-refusal** partial honour — `P0-62`'s exact live shape. ⚠️ Session 20 closed only
>    the *price*-divergence half, via a new `SimulateChangeSettlesOneTickAway` stub flag. Three
>    attempts to make the mirrored stop *grow* all left the request at qty 1, because the size comes
>    from `Math.Min(qty, livePos.Quantity)` where `qty` is the **bracket's** recorded quantity —
>    so the fix starts at `FollowerBracket.Quantity`, **not** in the test. `mutation/mutate_p1_71.py`
>    records it.

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
| Tags | `v1.0.0` (split), `v1.0.1`, `v1.0.2` (`P0-63` + `P?-66`), `v1.0.3` (docs only), **`v1.1.0`** (session 20's five defects — **the deployed code**; minor because two audit-log event names were removed). `main` carries docs commits on top of it; **a tag moving is what would break the bridge's pin**, so never delete or move one. |
| Git hooks | ✅ **Installed 2026-08-13.** `.githooks/pre-commit` refuses `dll/pdb/exe/zip/nupkg`, media, and anything over 50 MB. **Proven to fire in both directions** before it was committed: a staged 57 MB blob and a staged `.dll` were each rejected with exit 1, and `ALLOW_BIG_FILES=1` passed. ⚠️ `core.hooksPath` is **local config, not tracked** — a fresh clone silently has no hook until someone runs `git config core.hooksPath .githooks`. Both READMEs now say so. Neither repo tracks a single blocked extension today, so the guard cannot misfire on real work. |
| CI | ✅ **ACTIVE since 2026-08-13**, at `.github/workflows/ci.yml`, `windows-latest`, on every push and PR. Both structural checks, build, the suite, and **every** mutation battery. **4m39s** when it ran three batteries; five now. ⚠️ **This has been got wrong twice**: `mutate_p0_63.py` had to be added when the workflow was activated, and session 20's two batteries had to be added after it — each time CI was briefly **weaker than the local gate while looking complete**. The workflow now says so at the mutation block. |
| CI — the omission is now a gate | `tools/check_ci_runs_every_battery.py` fails if any `mutation/mutate_*.py` is not invoked by `ci.yml`, and it runs **inside** CI. Watched fail three ways before being trusted: an unwired new battery, an existing battery deleted from the workflow, and an empty `mutation/` (which would otherwise pass vacuously). Twice-repeated is a class, not an instance. |
| CI, historical detail | Actions pinned to current majors (checkout v7, setup-dotnet v6, setup-python v7), read from the API not guessed, because v4/v5 target the deprecated Node 20 that GitHub is only temporarily force-running on Node 24. |
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

---

## 5.14 Session 20 — 2026-08-13: all five defects from the live trade, fixed and deployed

**`P0-67`, `P0-68`, `P1-69`, `P1-70`, `P1-71` — closed, deployed as core `v1.1.0` + bridge, and
live-validated where a live check is possible.** Suite **1003/0** (was 953 at the start of the day),
**five** mutation batteries, 0 survivors.

Not run through the agent loop. These were five small fixes with one root cause between them, on code
whose failure modes had just been observed live — localisation was not the hard part, and the loop's
value is localisation. Recorded so the choice is visible rather than assumed.

### What each fix actually was

| Defect | The fix, and the thing worth remembering |
|---|---|
| **`P1-71`** | Every relationship named in `COPY_BEGIN` now produces **exactly one terminal outcome event**, by naming convention (`COPY_SUBMITTED` / `COPY_SKIPPED_*` / `COPY_BLOCKED_*` / `COPY_FAILED_*`) rather than a hard-coded list — so a skip path added next year is counted automatically. **The entry said five unlogged exits; there were fourteen**, three of them completely silent. Two sites *outside* the copy loop were routed too, and both are worse than anything inside it: `SLIPPAGE_QUARANTINE`, which **blocks every future entry**, and `RECONCILER_DIRECTION_MISMATCH`, which **flattens a live follower position** — a broker action with no audit-log entry. |
| **`P1-70`** | `BRACKET_MODIFY_REQUESTED` before the broker call; `BRACKET_MODIFY_CONFIRMED` only on settle, printing the **settled** values and flagging a partial honour. |
| **`P0-67`** | `CurrentStopPrice` is now assigned **only from the live order**, in `ReconcileStopFromBroker` at the top of every sweep. A polling monitor does not need settle events — it needs to stop trusting its own writes. `ModifyStopPrice` returns a result instead of `void`-and-swallow, so "moved", "no such order" and "threw" are distinguishable. Refusals are counted and bounded at 3. |
| **`P0-68`** | The bridge remembers the pre-change values, requests, waits a bounded **1500 ms** for settle, and reports what it **observed**: `modified` / `partially_modified` / `change_ignored` / `change_pending`. `change_pending` claims nothing. The response carries `requested`/`observed`/`before` blocks, and every outcome goes to `interventions.jsonl`. |
| **`P1-69`** | Two things. `GET` added to `/api/copier/config`. And — the part the defect entry got wrong — **the `get` action was calling `LoadFromDisk`, which REPLACES the in-memory relationships that `ObserveFollowerFill` writes its measurements onto. Reading the config destroyed the thing being read.** A read must not mutate. |

### 🆕 One new defect, found by a test rather than by reading

Writing the bounded-retry test for `P0-67`'s **trailing** path (which nothing had ever exercised)
turned up a second live defect at the same call site: in the `ScaledRunner` branch the breakeven move
and the trailing move can **both fire in one sweep**, so two `Change()` calls landed on the same stop
order back to back. Per the NT8 semantics a controlled live trade established on 2026-08-10
(`P0-61`), **a second change while one is in flight is dropped AND reverts the order** — it ends at
neither request's values. So the flood the attempt cap was meant to prevent was also silently undoing
itself.

Fixed in the same change: **one outstanding stop move per bracket**, the same reservation the copier
keeps with `bracket.StopInFlight`. Folded into `P0-67` rather than given its own ID, because it is the
same site, the same root cause, and was never open.

### The live validations

**`P0-68`** — the identical call that failed twice this morning:

```
BEFORE:  {"status": "modified",       "limitPrice": 29500}   # asked for 29450. Never moved.
AFTER:   {"status": "change_ignored", "requested": {"limitPrice": 29450},
                                      "observed":  {"limitPrice": 29500}}
```

…and now in `interventions.jsonl` as `BRIDGE_ORDER_CHANGE_CHANGE_IGNORED`.

**`P1-69`** — one 1-lot MNQ copy, then a plain HTTP `GET`:

```
Sim101 -> Sim-ORB    latency=142.8423 ms  avgSlip=0.0 ticks
```

⚠️ **The first `GET` after deploying returned `0.0`** — the recompile had reset the session — which is
exactly the trap the new `metricsNote` warns about, met immediately, by me.

**`P1-71`, in production, on the exact case that motivated it.** `SimCopy2` had been named active and
then dropped in silence, undiagnosably, for a whole session. Minutes after deploying:

```
COPIER_COPY_SKIPPED_SUB_MINIMUM: scaled quantity for NQ SEP26 on 'SimCopy2' came out
below 1 contract from leader qty 1 (ratio 1, sizing QuantityRatio); nothing placed.
```

**Read the instrument: `NQ SEP26`, not MNQ.** That relationship has `AutoSymbolConversion: true`, so
1 MNQ translated to NQ at ratio 1.0 rounds below one contract and is dropped. The relationship is
**effectively non-functional for micros**, which is a configuration finding nobody could have reached
before, and which no test would have produced. It is not a new code defect; it is the answer.

### What the mutation batteries caught, because this is the part that keeps paying

Two new batteries (`mutate_p1_71.py`, `mutate_p0_67.py`) — **19 mutants, 0 survivors** after four
rounds of fixing what they found. Every test in this session was written *alongside* its fix and had
therefore never been watched to fail; the batteries are the only thing that made "these tests work" a
measurement instead of a claim. They found, in order:

1. **Both "inflate the count" mutants survived.** Renaming a *non-terminal* event into the terminal
   convention was unpinned — so a quarantined or clamped copy could report two outcomes and let a
   second relationship drop in silence while the totals looked right. Two tests added.
2. **A defect in the battery itself**: a mutant that *crashed* the runner produced no result line and
   was scored a **SURVIVOR**. A crash is a kill. Fixed in both new batteries.
3. **A test dereferencing a null after `Assert`** — which records a failure and *returns* rather than
   halting — aborting every test after it. Guarded.
4. **A broken mutant that read as a missing test.** The `P0-67` mutant meant to reinstate the defect
   verbatim read `bracket.RequestedStopPrice` *after* the reconcile resets it to `NaN`, so it could
   not change behaviour and survived. That looks identical to "your tests are decorative" until you
   read it. **A mutant that cannot fail is as useless as a test that cannot fail**, and it is the same
   error one level up.

### One suite gap closed, one narrowed and named

`mutate_p0_63.py` recorded two gaps. The settled-vs-requested divergence is now pinned via a new stub
flag (`SimulateChangeSettlesOneTickAway` — a provider rounding to a tick boundary, which is ordinary
behaviour). ⚠️ **The QUANTITY-refusal shape is still NOT covered** — `P0-62`'s exact live trace. Three
attempts to make the mirrored stop *grow* all left the request at qty 1, because the size comes from
`Math.Min(qty, livePos.Quantity)` where `qty` is the **bracket's** recorded quantity. `mutate_p1_71.py`
records where to start, and it is **not** in the test.

### Two log-design rules that came out of this

1. **A message must not name other event types.** `grep BRACKET_MODIFY_CONFIRMED interventions.jsonl`
   matched the `REQUESTED` line that merely mentioned it in a "watch for…" hint. In a file whose
   entire purpose is post-hoc grepping, that is a defect. Tests now have `LoggedEventType` for
   absence assertions, which matches the type rather than the whole line.
2. **A message must not overstate its own outcome.** `deploy.py` printed `[FATAL] the vendored core is
   STALE` and then exited 0 on `--verify`/`--dry-run`, where nothing is blocked. It says `WARN` unless
   it is actually refusing. Same defect class as `P1-70`, in the tool that reports on it.

### The sync rule earned its keep, mechanically

The core moved to `v1.1.0` while the bridge pin sat at `v1.0.3`, and `deploy.py` **refused the
deploy** — correctly, because deploying the bridge would have shipped a `v1.0.3` core over the top of
three live fixes and silently reverted them. Tag core → push → bump pin → push → deploy → recompile,
in that order, because a submodule cannot pin a tag that only exists locally.

**Minor, not patch:** `BRACKET_MODIFIED` and `BRACKET_TARGET_MODIFIED` no longer exist. Anything
parsing the log for them finds nothing, and that is a breaking change for a log consumer.

---

## 5.15 Documentation pass — 2026-08-13, after session 20

**No addon code changed.** This pass reconciled the file against the state session 20 left, and it
found one live gap while doing it, which is the argument for doing these passes at all.

### The gap it found

**CI was running three of five mutation batteries.** `mutate_p1_71.py` and `mutate_p0_67.py` were
written, run locally, and never added to `ci.yml` — so for a day CI was **weaker than the local gate
while looking complete**. That is the second time: `mutate_p0_63.py` had the same history in session
17 and had to be added when the workflow was activated.

Twice is a class, not an instance, so it is now a gate rather than a comment.
**`tools/check_ci_runs_every_battery.py`** fails if any `mutation/mutate_*.py` is not invoked by the
workflow, and it runs **inside** CI as the step before the build. Watched fail **three** ways before
being trusted, because a check on gates is exactly the kind that ships vacuous:

| Probe | Result |
|---|---|
| A new battery nobody wired | `MISSING mutate_zz_probe.py`, exit 1 |
| An existing battery deleted from `ci.yml` | `MISSING mutate_p0_67.py`, exit 1 |
| **`mutation/` emptied entirely** | `FAIL: no mutate_*.py found`, exit 1 — *not* "all 0 batteries are wired, OK" |

The third probe is the one worth keeping. A check that iterates a collection passes trivially when the
collection is empty, which is how four gates in this repo shipped unable to fail (§8). The claim
"watched fail" was written into this file **before** that probe was run; running it is what made the
claim true.

### What was corrected

| Was | Now |
|---|---|
| Header dated session 18, *"the next item is `P0-67`"* | Session 20; `P0-67` closed; next is `P?-64`/`P?-65`. Session 18's header text moved into the collapsed "earlier headers" block rather than deleted |
| Path note: suite *"is **953** now"* | **1003** |
| §0 tags: `v1.0.0`…`v1.0.3` | **`v1.1.0`** added, and marked as the deployed code in both places that name a deployed tag |
| §0: *"THREE disagreeing version identifiers"* | The tag and the constant now **agree** — stated as a coincidence, not a guarantee, with the day they disagreed kept |
| §0 commands: `expect 953/0`, three batteries | `1003/0`, five, and which two score a crash as a kill |
| §0 pre-flight: *"a `Sim101` trade reaches THREE follower accounts"* | **Re-measure it.** Only `Sim-ORB` acted on 2026-08-13; `SimCopy2` is non-functional for micros via `AutoSymbolConversion`; `P1-57` is **not** exercised |
| §0: nothing distinguished `P0-67`/`P1-70` from the live-validated fixes | Both listed under *deployed but NOT validated live* — nothing has driven the ATM monitor live at all |
| §5.0: `# -> 64` | `# -> 68`, re-run, plus a note that the three `P?-` IDs deliberately do not match the pattern |
| §5.3: *"`/api/copier/config` has NO read"* | Struck — and marked that the fix was **not** the one-liner it looked like |
| §5.6: two suite gaps, both open | One closed (price divergence), one **narrowed and located** — the quantity-refusal shape, starting at `FollowerBracket.Quantity` |
| §5.11: CI runs *"the 953-test suite and all three batteries"* | Every battery, mechanically enforced |
| §7: 21 settled entries, ~1.2k tokens | **26**, ~1.7k — counted by importing the module, not by reading it |

### Session 20's six rules are now in BOTH places

§7's own instruction is *add to both places, and retire from both places*, and the split has already
silently dropped 15 of 21 entries once (§7's closing warning) — after which the panel could not
possibly flag the invariant the `P0-63` candidate broke, because it was never told. So the five
session-20 rules plus their corollary went into §7 **and** into `agent/nt8_riskguard.py`'s `settled`
tuple in the same edit:

1. A cache of broker state is written **only** from the broker (`P0-67`).
2. **One** outstanding `Change()` per order, at every call site (`P0-61`).
3. A log line must not claim an outcome it has not observed (`P1-70`) — and must not **name** another
   event type, which poisons `grep` on a file that exists to be grepped.
4. Exactly **one** terminal outcome event per relationship in `COPY_BEGIN`, by naming convention —
   and the corollary a mutant had to find: a **non**-terminal event must not take a terminal prefix.
5. A read endpoint must not mutate (`P1-69`). Its metrics are session-scoped, and **a zero is not a
   measurement**.

The first three are the same rule at three levels: *do not record what you asked for as though it
happened*. That is `P0-63`'s root cause, and it is worth stating that way because it will recur at a
fourth level.

### New traps recorded in §8

- **A mutant that cannot fail is as useless as a test that cannot fail**, and it presents as the
  opposite — a survivor reads as "your tests are decorative" until you read the mutant.
- **A battery must score a crash as a kill.** No result line meant SURVIVOR.
- **`Assert` records and returns; it does not halt.** A null deref on the next line aborts every
  later test and presents as dozens of unrelated failures.
- **`BRACKET_MODIFIED` and `BRACKET_TARGET_MODIFIED` no longer exist** — a breaking change for
  anything grepping `interventions.jsonl`, including notes written by earlier sessions.
- **The copier's metrics are session-scoped and a recompile resets them.** A zero is
  indistinguishable from "no fill observed yet", which is a conclusion already drawn wrongly once.
- **The stale-pin guard fired for real** and was right, with the working order written down.

---

## 5.16 Session 21 — 2026-08-13: the MCP wrapper, and the four defects widening it exposed

**§5.6 item 3 is done.** `nt_copier_config` went from **5 arguments to 19** and from **3 actions to
11**, reads go over `GET`, and an unknown action is now refused rather than silently read. Suite
**1003 → 1028/0**. Deployed and NT8-compiled (0 errors); three of the four fixes are live-verified
against the box.

**The wrapper was not the work.** Widening it meant writing down what each field does and which key
the engine reads, and that produced four defects — `P1-72`…`P1-75`, all closed the same day, **none
findable by a review of the diff** because each was a mismatch between two artifacts that no single
file contains.

### The four, shortest first

| | What | How it was found |
|---|---|---|
| **`P1-72`** | The tool advertised `action: 'quarantine'`. **Nothing implemented it anywhere.** `CopierConfig`'s if-chain ends in `else { read }`, so it returned the config with `success: true` — a misbehaving follower told to stop, reporting that it stopped, still sending orders. | Comparing the declared `action` enum against the branches that exist |
| **`P1-73`** | The schema declared `quantityRatio: {default: 1.0}` and `autoConversion: {default: true}`. `ApplyRelationshipRequest` **merges**, so a default that reaches the body is silent data loss: nudge one field, reset the other. | Asking what merge semantics imply about a schema with defaults |
| **`P1-74`** | **`autoConversion` is not a field.** The property is `AutoSymbolConversion`; the alias map has `autoSymbolConversion` and not `autoConversion`, so Json.NET dropped it as an unknown member. The parameter had **never done anything** — on the exact feature that dropped a live copy the day before. | Checking which camelCase keys the engine reads instead of assuming |
| **`P1-75`** | **Reading the prop-firm rules DISARMED them.** `LoadFromDisk` → `UpdateConfig(cfg)` with no `confirmLive` → the safety gate forces `ArmedForLive = false`. Every other field survives, so the only thing lost is whether anything is *enforced*. | Enumerating **every** `LoadFromDisk` call site after `P1-69` turned out to be half-fixed |

### `P1-69` was fixed in one of two read branches, and I shipped it as done

The copier's **`get_groups`** branch still called `LoadFromDisk`. Yesterday's fix went into the `get`
branch only, so listing the **groups** still replaced the in-memory relationships that
`ObserveFollowerFill` writes its latency/slippage measurements onto — the same defect, one branch
over, in a fix I had reported as complete and live-validated.

The live validation was real; it exercised `get`, which is why it passed. **"A read must not mutate"
had been applied to *the* read, not to *every* read.** Enumerating the call sites — three found, two
were defects, one was the legitimate `State.Configure` startup load — took two minutes and is what
found `P1-75` as well. Only the two startup loads remain.

### `P1-75` is latent, and that is luck rather than design

`prop_limits.json` **does not exist on this box**, and `LoadFromDisk` returns early on a missing file,
so the disarm has never fired in production. **The defect is self-arming**: the `set` branch calls
`SaveToDisk`, so the first prop-limits write creates the file, and from that moment every read
disarms. It was one POST away.

⚠️ **The gate is correct and must stay.** `UpdateConfig` refusing to arm without `confirmLive` is
exactly what prevents a config arming itself from a file — the same rule as `P1-47` and the copier's
`ArmedForLive = false` default. `TestP1_75_ReloadingPropLimitsFromDiskDisarmsThem` **asserts the
disarm on purpose** so that a future report of this cannot be "fixed" by weakening the gate. The
defect was a read path invoking it.

### Where the tests had to live, and why it is split across two repos

The mapping is in **`mcp/ninjatrader-mcp/lib/copier-config-request.js`**, not inline in
`nt-mcp-server.js` — importing that file starts its stdin readline loop, so a test of a function
defined there hangs. Same rule the bridge follows for `ApplyRelationshipRequest`: put the mapping
where an executed test can reach it. **33 tests**, `node --test`, zero new dependencies.

But those tests can only prove **what is emitted**. Whether the engine *reads* those keys is a
different claim, in a different repo, and it is where `P1-74` was hiding. So three tests went into the
core suite: every documented key lands on the relationship; `autoConversion` is **still dropped**
(pinning the defect, since the remedy is in the wrapper, and telling whoever adds an alias later that
the translation can be simplified); and `isQuarantined`/`quarantineReason` arrive through `set` —
which is what makes `P1-72`'s remedy real rather than a second no-op dressed as a fix.

**A wrapper verified against my reading of an alias map is verified against nothing.**

### The bridge's GET now answers the question it was asked

Measured before changing anything: `GET /api/copier/config?leaderAccount=Sim-ORB` returned
**Sim101's** relationship in `config`, with `leaderAccount: "Sim101"` echoed back and
`success: true`. The route passed `null`, so the read fell back to the default leader. That is
`P0-68`'s shape — a confident answer to a question nobody asked.

⚠️ **The action is whitelisted, not forwarded.** `CopierConfig`'s if-chain holds every write branch, so
passing a query action straight through would let `GET ...?action=remove_group&groupName=X` **mutate
config over a GET** — turning the read this route exists to provide into the write it exists to avoid.
Live-verified refusal:

```
GET /api/copier/config?leaderAccount=Sim-ORB       -> leaderAccount: Sim-ORB, config: Sim-ORB  ✅
GET /api/copier/config?action=remove_group&...     -> success: false, "method not allowed"     ✅
GET /api/copier/config?action=get_groups           -> action: get_groups, keys: [action, groups, success]  ✅
```

### Two method notes worth keeping

**1. A red baseline from the harness is not a red baseline.** My first "the tests fail before the
module exists" was `node --test tests/` failing to *resolve the directory* — a `MODULE_NOT_FOUND`, not
an assertion. It looked exactly like the evidence I wanted. The real red came later, with 6 assertion
failures against 27 passes, and only then did the fix mean anything. Same class as the vacuous
mutation batteries in §8: **check what the failure says, not that there was one.**

**2. A failed build plus `--no-build` reports the previous assembly.** A field-name typo made the
build fail and the suite print `RESULTS: Passed = 1023, Failed = 0` from the **stale** binary — the
exact trap §0 records, met while working on the file that records it. Grep the error count, not just
`RESULTS:`.

### Not validated live

- **`P1-75`** — proving it needs an armed prop config *and* a saved file. Arming live risk rules to
  demonstrate a fixed defect is not a trade worth making. Compile-clean, deployed, pinned by test.
- **`P1-69`'s second half** — needs a fill to produce a non-zero metric, then a `get_groups`, then a
  re-read. Worth folding into the next live copy rather than booking a trade for it.
- ⚠️ **The MCP server change needs the server process restarted** to take effect. A client that
  spawned `nt-mcp-server.js` before this is still running the 5-argument, POST-everything version, and
  will report success on `action: 'quarantine'` exactly as before.

---

## 5.17 Feature audit — 2026-08-13, operator's list of eight

**Asked: do these exist? Answer verified against the source, not from memory.** Two already
exist and are enforced, two are half-built, three are absent, and one turned out to be a
**defect rather than a missing feature** — it is configurable, enabled by default, and
evaluated nowhere.

| # | Asked for | Verdict |
|---|---|---|
| 1 | **Latency + fill-slippage per follower** (`P1-22`) | **Measurement DONE, gauge/heatmap NOT.** See below. |
| 2 | **Consistency Rule Shield** (daily-profit cap) | ⚠️ **DEAD CONFIG — now `P1-77`.** |
| 3 | **Tilt detection + cool-off + PIN disarm** | **Absent.** Backlog `F-3`. |
| 4 | **Intra-execution slippage guard** (market→limit, cancel remainder) | **Detection exists, the RESPONSE does not.** Backlog `F-4`. |
| 5 | **Pure reconciler + in-flight ledger** | **Copier half shipped and live-validated; ledger absent.** Already `P3-31` + `P3-30`'s remaining half. |
| 6 | **Discord / Telegram push alerts** | ✅ **DISCORD SHIPPED 2026-08-15 and live-validated** — see §5.70. Still true that there is **no outbound HTTP in this addon**, and that is now the design rather than a gap: the guard decides and writes `alerts_outbox.jsonl`, a Python relay delivers. **Telegram is `NOT_IMPLEMENTED`**, refused by name. |
| 7 | **Block specific instruments** | ✅ **EXISTS and enforced.** |
| 8 | **Max contracts per instrument** | ✅ **EXISTS and enforced — at the POSITION level, which is the right one.** |

### 7 and 8 already exist — here is where, so nobody rebuilds them

**Blocking**: `_config.BlockedInstruments` is checked in two places — a can-trade gate
(`RiskGuardAddOn.cs:133`) and the order-update path (`:1706`), which queues a cancel and logs
`BLACKLIST_CANCEL`. The firm profile carries its own default list (`ZB`, `ZN`, `6E`, `6B`).

**Per-instrument contract cap — two complementary checks, and the distinction matters:**

| Layer | What it compares | On breach |
|---|---|---|
| `_config.InstrumentLimits[root].MaxContracts` (`:1717`) | a **single order's** quantity | cancels that order, `PER_INSTRUMENT_CAP_CANCEL` |
| `profile.InstrumentProfiles[sym].MaxContracts` (`:3197`, Rule 1 `MAX_SIZE_BREACH`) | the **aggregate position** quantity | locks the account out **and flattens** |

⚠️ **I initially wrote this up as a gap** — "the cap is per-order, so three 5-lots pass a cap of
10" — and that was wrong. The position-level rule covers exactly that, falling back to
`profile.DefaultMaxContracts`, which falls back to `_config.Sizing.MaxContractsPerAccount`
(10) when unset, so it fires without a firm mapping. There is also
`Sizing.MaxContractsAggregate` (20) across accounts at `:3139`. Recorded because the wrong
version was one grep away from becoming a filed defect.

**Both are gated by mode.** Intervention cancels run only under `IsActingMode()`
(`DrainPendingCancels`), and rule evaluation needs `_isArmed`. In `shadow` — today — these
**log the intent and do not cancel or flatten.** That is correct and deliberate; it also means
neither has ever fired here.

> **This is the operator's "what applies and for what" complaint, in the risk rules rather
> than the copier.** One concept — a contract cap for an instrument — is spread across
> `InstrumentLimits`, `InstrumentProfiles`, `DefaultMaxContracts`,
> `Sizing.MaxContractsPerAccount` and `Sizing.MaxContractsAggregate`, with different scopes and
> different consequences. Nothing is wrong with any of them individually. **The UI's job is to
> say which one bit, and no UI can do that until they are named as one story.** Design input,
> not a defect.

### 1 — the measurement is real, the display is one line of text

Present and live-validated: `LatencyMs`, `AvgSlippageTicks` (running mean), `MaxSlippageTicks`
(the quarantine threshold), written per fill by `ObserveFollowerFill`, announced as
`COPIER_FILL_MEASURED`, with a sanity bound that records a rejected latency as
`(REJECTED by sanity bound, not recorded)` rather than storing a wrong number. Readable over
`GET /api/copier/config` since 2026-08-13 (`P1-69`), per relationship, in a `metrics` array.

Not present: any **gauge or heatmap**. The entire UI for it is a single interpolated status
string at `TradeCopierWindow.cs:799`. Two corrections to the request as written:

* **Milliseconds, not microseconds.** The live measurement was `142.86 ms` entry / `314.21 ms`
  exit. Microsecond resolution is not available — these are wall-clock deltas between two NT8
  callbacks, not routing timestamps from the broker.
* **A zero is not a good reading.** The metrics are **session-scoped**; a recompile resets them.
  Any gauge must distinguish "no fill observed yet" from "a clean fill", or it will read as a
  perfect score whenever NT8 has just restarted. That confusion already cost two sessions as
  `P?-66`.

### 4 — detection exists, the response is post-hoc

`ObserveFollowerFill` compares the follower's fill against the leader's, signed so only adverse
slippage counts, and on an **entry** beyond `MaxSlippageTicks` sets `IsQuarantined` and logs
`SLIPPAGE_QUARANTINE`. Exits are never blocked (settled decision — blocking an exit strands the
follower in a position the leader has left).

So what exists is *after the fill, for the next order*. What was asked for is **during**
execution: convert a follower market order to a limit, or cancel the unfilled remainder. That
needs partial-fill handling on the copy order and is genuinely new work — `F-4`.

### 6 — there is no outbound HTTP anywhere in the bridge

`_alerts` is a **local, pull-based store** read through `nt_alert`. No `HttpClient`,
`WebClient` or `PostAsync` exists in `McpBridgeAddOn.cs`. So a webhook is not "wire up a URL";
it is the first outbound network call this addon would ever make, from inside NT8's process,
which brings its own questions (timeouts blocking a callback thread, retries, and a token in
config). Worth doing, worth designing.

---

## 5.18 Backlog — features, in the operator's words, with what each actually needs

Not defects. Numbered `F-n` deliberately: they are **not** in the `P` defect sequence and must
not be renumbered into it.

| ID | Feature | What it needs | Notes |
|---|---|---|---|
| **F-1** | Latency / slippage **gauge** per follower | UI only — the data is already there and readable | **Folds into the UI redesign**, not separate work. Must show session-scope and distinguish no-fill from clean-fill. |
| **F-3** | Tilt detection → forced cool-off → optional PIN | A loss-sequence detector (e.g. 3 closed losers inside 5 min), a timed disarm, and a PIN gate on re-arm | Primitives exist to build on: `LockoutUntil`, `MaxTradesPerSession`, the three-phase lockout sweep, and the arm/shadow split. ⚠️ A PIN in a config file is not a security control; it is a speed bump against your own impulse. Say so in the UI rather than implying more. |
| **F-4** | Intra-execution slippage guard: market→limit, or cancel the remainder | Partial-fill tracking on the copy order, a decision point before the remainder fills, and a rule for what happens to a half-filled follower | ⚠️ **The half-filled follower is the hard part, not the conversion.** Cancelling the remainder leaves the follower smaller than the leader, which is a *sizing* divergence the reconciler must then not "fix" by re-adding. Design against `P3-31` before building. |
| **F-6** | Discord / Telegram push on fills, slippage, drawdown, disarms | The bridge's first outbound HTTP: fire-and-forget with a hard timeout, off the NT8 callback thread, plus a webhook URL in config | ⚠️ Never block an NT8 callback on a network call. Also: the events worth pushing already exist as `interventions.jsonl` entries, so this is a **sink** on an existing stream, not new instrumentation. |
| ~~F-2~~ | ~~Consistency Rule Shield~~ | — | **Not a feature. It is `P1-77`** — the config exists and nothing evaluates it. |
| ~~F-5~~ | ~~Reconciler / ledger~~ | — | **Already tracked**: `P3-31` (ledger) and `P3-30`'s remaining half (timer + RiskGuard-side audit). The copier half is shipped and live-validated. |
| ~~F-7~~ | ~~Block instruments~~ | — | **Exists** (§5.17). |
| ~~F-8~~ | ~~Max contracts per instrument~~ | — | **Exists**, position-level (§5.17). |
| **F-9**…**F-15** | UI-adjacent features from the design pass | see [UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md) §9 | firm mapping, flatten-group, session lock, reconciler events, fill-timeout, adopt the gatekeeper, `CanTrade` reason channel. Each holds a marked slot in the layout |
| **F-16** | **MCP tool schema conformance** | ✅ **CLOSED 2026-08-15 (session 43)** | See below — and ⚠️ **this row asserted "52 tools, 1 tested" for three sessions after it stopped being true**, which is `P2-113`'s class inside the tracker itself. Re-measured: **55 tools, 54 tests**, the extraction it named as a prerequisite done by `P1-91`, and class-level sweeps already covering defaults, required fields, structural soundness and enum pinning. What actually remained was ONE thing nobody had written: **the join** |


---

## 5.19 Session 22 — 2026-08-13: the UI design pass, and what RiskGatekeeper turned out to be

**No code changed.** Output is [UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md), plus three findings
that were not in this document at all. Read the design doc for the design; this section records what
the pass *found*, which is the part that outlives it.

### 🆕 There is a THIRD risk system, and it is in neither repo

`Strategies/Vinay/RiskGatekeeper.cs` — **500 lines**, live in NT8, under no source control, no tests,
invisible to `sync_nt8.py --verify`. It is referenced by exactly two files: `RiskManagerAddOn.cs`
(which **is** in this repo and **is** deployed) and `Strategies/Vinay/RiskManagerBase.cs` (816 lines,
also in neither repo), which is the base class of the whole bot fleet — `EMAPullbackBot`,
`FailedAuctionBot`, `VWAPReclaimBot`, and via `IntradayStrategyBase` → `IBStrategyBase` the three IB
bots.

**It is not a duplicate of RiskGuard — it is the other half.** RiskGatekeeper is the **pre-trade,
strategy-side** gate (`CanTrade` at `RiskManagerBase.cs:418`, `WouldBreachDailyMaxLoss` at `:479`,
`RecordTrade` at `:683`, all gated `!isBacktest`). RiskGuard is the **post-trade, account-side**
enforcer. Decision: **keep it, do not fold it in** — but adopt it into this repo (`F-14`).

⚠️ **It is a third config surface and nothing reconciles it.** `RiskManagerAddOn`'s `[Display]`
properties carry `DailyMaxLoss` 400 and `TrailingDrawdown` 2000. **"What is my daily loss limit?" has
three different answers on this box today** — RiskGuard's, the gatekeeper's, and the copier's
per-relationship `DailyLossLimit` — and no surface shows more than one of them. A bot can be waved
through by a gatekeeper holding different numbers than the guard enforcing.

### 🆕 `P2-25`'s news shield is the same defect class as `P1-77`, and the operator's news request is already half-built

`EnableNewsShield` **defaults to `true`** (`PropFirmProtectionSuite.cs:33`). `LocalNewsEventsFilePath`
is parsed and persisted and **never read**, so `IsInNewsWindow` always returns `false` outside tests
and the `NEWS_SHIELD_LOCKOUT` branch (`RiskGuardAddOn.cs:1541`) is unreachable. The operator asked
about adding news timeouts for strategies to reuse; **the shield exists, on the RiskGuard side, and
is dead.** The work is loading a file, and tvDownloadOHLC already has the economic-calendar pipeline
to emit it. On the strategy side, `CanTrade` is already the universal pre-trade gate — but it returns
a bare `bool` with no reason, which is `F-15`.

### The vocabulary this pass produced, and why it is worth more than the layout

**CONFIGURED / EVALUATED / ENFORCING.** Four shipped defects are the same state:

| | State |
|---|---|
| `P1-77` (open) | configured, enabled by default, **evaluated nowhere** |
| `P2-25` (open) | configured, defaults to on, **evaluated nowhere** |
| firm-mirror rules | configured, **unmapped, can never fire** |
| `P1-75` (closed) | enforcing → **not** enforcing, silently, because a read disarmed them |

Four defects, one shape: **the config file reads as protection that does not exist.** That is now the
UI's primary job, and `CONFIGURED and not EVALUATED` renders red. It is also a lens for defect
triage independent of any UI — when a config field is added, ask which of the three states it is in.

### `F-9`…`F-15` filed

`F-9` account→firm-profile mapping (the keystone — it is what moves the firm-mirror rules from
CONFIGURED to EVALUATED), `F-10` flatten-group in the UI, `F-11` no-edits-while-live session lock,
`F-12` reconciler actions as structured events (`ReconcileAction{Verb,Subject,Leg,Reason}` exists and
is flattened into a single append-only `TextBox` at `TradeCopierWindow.cs:641`), `F-13`
fill-timeout + rejected-order protection, `F-14` adopt the gatekeeper, `F-15` `CanTrade` reason
channel. Details and the layout slot each one holds: the design doc §9.

### Method note

The competitive read (Replikanto, Tradecopia, TradeSyncer) was worth one pass and no more. It
confirmed we already have what they sell as premium — stealth mode, mini↔micro conversion,
out-of-sync reconciliation — and that **none of them mirror brackets onto followers at all**, which
is `P0-63`'s whole subject. Its one durable contribution was the **wireframe critique**: a mock drawn
without the engine in hand asked for `0.9ms` latency (ours is `142.86 ms`, wall-clock between two NT8
callbacks) and a trailing-drawdown safety bar with **no data source**, because the firm rules are
unmapped. Both are recorded in the design doc so they are not re-drawn.

### Addendum to §5.19 — the MCP test coverage question, answered by measurement

The operator recalled that tests had been written "for all the APIs/tools for the MCP" and assumed
they moved during the split. **They were never written.** `git log --all` over
`mcp/ninjatrader-mcp/tests/` returns exactly one filename, ever — `copier-config-request.test.js`,
which arrived with the session-21 widening. `nt-mcp-server.js` defines **52 `nt_*` tools and one is
tested.** Nothing was lost; the JS repo was never part of the split.

**What produced the false belief was `tvDownloadOHLC/tests/test_mcp_stack_all.py`** — 191 lines,
7 tests, named as if it covered the stack. **Six of the seven exercised zero product code.**
`test_atm_bracket_metadata` built a dict and asserted the dict contained what it had just put in it.
`test_state_persistence_stores` set a key on an empty dict and asserted reading it back worked.
`test_audit_trail_formatting` round-tripped `json.dumps` through a temp file. `test_indicator_calculations`
**defined `calculate_sma`/`calculate_ema` inside the test file** and tested those. The seventh,
`test_version_alignment`, greps a version string and had been raising `FileNotFoundError` since
`671d8a18` (already recorded in NT8_REPO_SPLIT_PLAN.md:64).

**Deleted 2026-08-13.** A green suite that tests dictionaries is worse than a missing suite, because
it stops you looking — which is exactly what it did, for two weeks. Its one real assertion (version
alignment across `nt-mcp-server.js` and `package.json`) also asserted on a **submodule's files from
the parent repo**, the same inverted dependency `P2-38` already had to fix once; it belongs in
`ninjatrader-mcp`'s own harness and is folded into `F-16`.

#### 🆕 `F-16` — MCP tool schema conformance, and why it is ONE test rather than 51

The naive reading is "write 51 more test files." It is not, and the reason is in the four defects
session 21 found: **`P1-72`, `P1-73`, `P1-74` and `P1-75` were SCHEMA defects, not logic defects** —
an advertised `quarantine` action nothing implemented, schema `default:`s that overwrote stored
config through a merging receiver, an `autoConversion` argument that was not a field, and a read
branch that disarmed the rules. Meanwhile `nt-mcp-server.js`'s dispatch (`switch (name)` at `:787`)
is mostly **thin pass-throughs** with no logic to test.

So the high-value test is a **conformance sweep over all 52 tools at once**: every advertised action
is handled by the dispatch; no schema declares a `default:` that a merging receiver turns into a
write; every advertised argument maps to a field that exists. That is one test covering the exact
shape of all four known defects, plus targeted builder tests only where real mapping logic exists.

⚠️ **The blocker is structural and already documented in `copier-config-request.test.js`'s header:
importing `nt-mcp-server.js` starts its stdin readline loop and the test hangs.** That is why the
builder was extracted to `lib/copier-config-request.js` in the first place. So `F-16` begins by
extracting the **tool schema/dispatch table** into its own module. Parsing the source text instead
would be a source-text assertion, which the bridge's own `tests/README.md` correctly calls out as
proving less than an execution.

#### `P2-27`'s remaining half — deliberately deferred, with the price recorded

Making `McpBridgeAddOn.cs` executable in tests costs, measured: **330 compile errors — 312× CS0246,
16× CS0234, 2× CS0103, 23 distinct missing stub types** (`nt8-mcp-bridge/tests/README.md`). Deferred
behind `F-16` for two reasons: `F-16` is far cheaper and targets a defect class with four known
instances, and the 2026-08-13 UI decision keeps the bridge a **thin pipe** — routing and static
bytes, with every decision in core — so this surface is not growing while it waits.

---

## 5.20 Session 23 — 2026-08-13: `UI1` shipped, and what six loop runs and a battery taught

**`UI1` — the copier conformance snapshot — is GREEN.** Suite **1076/0**. Battery
`mutation/mutate_ui1.py`: **12 mutants, 12 killed, 0 survivors**, wired into CI (**7 of 7**).
Branch `feat/ui-core-snapshot`, not merged, not pushed. Design: [UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md).

### The headline: a green suite proved nothing, twice, in the same ticket

Eighteen tests were written RED before the implementation and all eighteen turned green. The
review panel then found **ten upheld defects in exactly that code**. Three were unreachable by
any assertion, because **every one of the eighteen used ONE instrument, ONE relationship and a
fresh engine** — the suite could not *represent* a second instrument, so no test over it could
fail on one.

After those were fixed, **21 green tests** were mutated and **two mutants survived**: `Math.Abs`
on the leader quantity (no test used a **short leader** — a follower on the wrong side is a
different case), and the clamped-to-zero reconciliation (the clamp test asserted the **flag**,
never the **verdict**).

> **Both misses have one shape, and it generalises beyond this ticket: asserting an intermediate
> field proves the field is set and says nothing about whether anything downstream reads it
> correctly.** Assert the decision, not the input to it.

### 🆕 A mutant that SURVIVES is not automatically a test gap

"Remove the `Math.Abs`" survived even after a short-leader test was added. It is **unkillable by
construction**: `Position.Quantity` is the ABSOLUTE contract count in NT8 and in the stub, with
direction in `MarketPosition`, so a short is `Quantity=2 / Short`, never `-2`.

The tempting fix was to teach the stub to emit a negative quantity so the mutant would die.
**That is worse than the gap.** A double that can express a failure the real system *cannot*
manufactures evidence for a defect that does not exist — the mirror image of the double that
could not express a real one, which is how six omitted `OrderState`s hid a live `P0` behind a
green suite. The `Math.Abs` stays; the **mutant** was retired, with the reasoning recorded in the
battery, and replaced by one that attacks what the test actually defends.

### The defect that shipped in the first green implementation

A leader position the follower did not mirror was emitted with a `NotApplicable` verdict. So
**"the leader holds 4 NQ and the follower holds none" — the copier having failed to copy at all —
reported as *not applicable***. The one divergence the snapshot exists to surface was the one
state guaranteed not to be shown. `NotApplicable` became unreachable once fixed and was
**deleted**: a verdict nothing can produce is worse than none, because it reads as considered.

### 🆕 DECIDED: the snapshot's grain is per relationship **PER INSTRUMENT ROOT**

The ticket said one row per relationship; the implementation emitted one per instrument. The
operator kept the implementation's grain, and it is the better contract — a follower can mirror
NQ correctly while holding an unmanaged ES position, and one aggregate row cannot say which
diverged. Recorded on the DTO and in the ticket. ⚠️ **The test helper originally took the first
row matching the account name**, which is how all 18 passed against code that counted an
unrelated ES position as the NQ mirror: the assertions were sound, the **selection** was
accidental.

### Six loop runs, and five rough edges worth filing against `agent-loop`

Only **one** run failed on the model's own reasoning. The rest were my ticket or the harness.

| | What happened | The general form |
|---|---|---|
| 1 | `TICKET_REJECTED` — the loop will not run until `expect_green` is already RED, and `UI1` was additive so nothing could be | For additive work no red test can exist without scaffolding, so the loop **cannot be used for a new API at all** |
| 2 | `TICKET_REJECTED` on ONE string — the ticket said *"after one latency is actually recorded"*, the test asserted *"after one measured fill"* | `--list` validates regions but **never checks `expect_green` against the test sources**; a substring scan would have caught it locally |
| 3 | 4 rounds, `CS0101`/`CS0111` — regions pointed at `GetRelationships()` while the stub to replace was 2 lines below, outside every region | **`--list` says a region RESOLVES, not that it resolves to the right code.** It printed `OK` before both failed runs |
| 4 | 17 of 18 green, stalled — the spec said enumerate via `GetActiveRelationshipsForLeader` (which excludes quarantined **by default**) *and* demanded a `QUARANTINED` verdict | The gate does not only check the code, **it proves the specification is satisfiable** |
| 5 | 4 rounds of invented member names (`CopierGroup.Followers`, `.Name`, `Instrument.Name`) | **Regions are the editing window AND the model's entire view of the file.** A symbol named in `spec` that appears in no region is a malformed ticket |
| 6 | `PANEL_UNREACHABLE`, twice | `deepseek-v4-flash` returned **475 findings against a cap of 60**, then **371**. Not a rejection — an infrastructure failure in one panel member |

> **The one place the copy path and a read path genuinely want opposite defaults:
> `includeQuarantined`.** The copier MUST exclude a quarantined follower — it must not copy to
> it. The UI MUST include it, because the whole value of quarantine to an operator is seeing that
> a follower stopped copying and why. A quarantined relationship silently absent from the display
> is `P2-41`'s and `P?-64`'s shape.

### Next

`UI2` — `TradeCopierEngine` owns the config path, the bridge delegates, and `P?-64`/`P?-65`
close. ⚠️ **Decided: the window is REWIRED, not deleted** — deleting it now leaves no GUI at all
until the browser page lands. It is removed in the same landing that makes it redundant.

## 5.21 Session 24 — 2026-08-13: `UI2` green, and a gate for code no gate could see

**`P?-64` and `P?-65` are CLOSED**, and `P1-79` — opened during this session, by writing
the ticket rather than by running anything — closed with them. Branch
`feat/ui-config-single-owner`, **unmerged**. Suite **1093/0**, **eight** mutation batteries,
0 survivors, CI wiring verified 8-of-8.

### What landed

* **`TradeCopierEngine.ConfigFilePath`** — one owner, in core, for
  `UserDataDir/RiskGuard/copier_config.json`. `SaveToDisk()` delegates to it. **There is
  deliberately no parameterless `LoadFromDisk()`**: a convenient load is the `P1-69` footgun,
  where the bridge's `get` destroyed the measurements it was asked to report. The two
  legitimate loaders say `LoadFromDisk(TradeCopierEngine.ConfigFilePath)` and show up in a grep.
* **`CopierRequests`** — four request builders, in core rather than inline in the window,
  because `NormalizeRequest` **drops an unrecognised key without an error**. That is `P1-74`,
  where an advertised `autoConversion` argument was not a field on anything and had never done
  a thing. A builder nobody can test is a builder nobody can trust.
* **The window dispatches.** Seven path-naming saves became `SaveToDisk()`; both Add sites and
  all three row buttons go through `Apply*Request`, check the null the engine can now return,
  and mutate nothing in place.
* **`P1-79`** — releasing a quarantine kept its reason. Fixed as an invariant
  (*no quarantine, no reason*), not as a special case for one request key, so it holds for the
  bridge's `quarantine` action too.

### The loop got it right in ONE round, which is exactly when not to trust it

All 12 acceptance tests went red→green in a single implement pass — the best result any ticket
here has had. `UI1` had already shown what that is worth: 18 red-then-green tests there were
followed by ten upheld review defects and then by 2 of 12 mutants surviving.

**18 mutants, 17 killed on the first run.** The survivor is the useful part:

> `GroupEdit` carrying `isEnabled` **even when the caller passed null** changed no test
> outcome — because every call in the suite and in the window passes a value. So
> *absent-means-unchanged*, which is the entire contract of a request builder, was asserted
> for `RelationshipEdit` and **never** for `GroupEdit`.

Resolved by writing the test, and the reasoning is recorded beside it: the nullable is not
speculative surface (the builder is public and the browser UI will send partial group edits),
so narrowing it to a plain `bool` would make it asymmetric with `RelationshipEdit` for no
reason beyond today's single caller happening not to exercise it.

⚠️ **The first draft of that test still let the mutant live.** It asserted the null edit
*after* the disable, where the group is already disabled and `isEnabled ?? false` gives the
same answer. **The null edit has to run against an ENABLED group.** That is `UI1`'s Rule 1
wearing a different hat — *assert the state that can actually differ* — and it is the second
time in two tickets that a test written to kill a specific mutant failed to.

### The panel filed three BLOCKERs and all three were false

Each claimed `ApplyArmingGate` disarms when `armingWasRequested == false`. The gate is
`if (armed && armingWasRequested && !confirmLive)`, so the branch is unreachable by the path
all three describe. Two `MAJOR`s were also false: they read the trailing `true` in
`CopierRequests.Relationship(..., armed, true)` as `armedForLive` when it is `isEnabled`.
Two `MINOR`s — stale `// STUB` comments — were correct.

**But the invariant the blockers pointed at was pinned by nothing**, and it is a safety
property: toggling a checkbox must never change whether a relationship can lose real money.
It now has three tests and two mutants, including one that makes the imagined defect real.
**A wrong finding aimed at an unpinned invariant is still worth the test** — which is a more
useful rule than "the panel is unreliable", and both are true at once.

⚠️ **What the panel missed, and a read of the diff caught: the patch had stripped every emoji
from the row labels** (`⏸ Disable` → `Disable`, `⚠️ QUARANTINED` → `QUARANTINED`, `➔` → `->`).
Out of scope — the ticket excluded restyling — and no gate in this repo would ever have
noticed, because no test reads a label. All seven glyphs restored. **A model normalising
non-ASCII is a silent scope change; diff the surface, not just the logic.**

`PANEL_UNREACHABLE` again, third occurrence: `deepseek-v4-flash` returned **262 findings
against a cap of 60**. Filed against `agent-loop` as `O67` earlier the same day, along with
`O64`–`O66`.

### `tools/check_window_parses.py` — the new gate, and the one that was abandoned

`TradeCopierWindow.cs` is one 1100-line `#if !TESTING` block. **`dotnet build` compiles it to
nothing**, so a stray brace in it passes every gate in this repo and is first reported by
NinjaTrader — where a compile error in *any* addon `.cs` stops **every** addon loading,
RiskGuard included. That is why `P1-72`…`P1-75` could only be compile-checked by deploying.

The new check reports **CS1xxx only**: a *parser* check, not a compile, and it says so in its
own output. **Watched failing on a deliberately removed semicolon before being wired into CI.**

⚠️ **A fuller check was built first and abandoned on purpose.** Referencing NinjaTrader's real
assemblies pulled in `NinjaTrader.Custom.dll` — which already contains a *compiled copy of
these same sources* — so every type resolved twice and every error was an artefact of the
harness. **A check whose failures are its own artefacts is worse than a narrower one that
means exactly what it says.**

### Next, and one ordering constraint that matters

1. ⚠️ **The bridge change is BLOCKED on a merge and a tag.** `McpBridgeAddOn.cs:3765`'s
   `CopierConfigFile` should become `TradeCopierEngine.ConfigFilePath`, but the bridge consumes
   core as a **submodule pinned to a tag**, and `ConfigFilePath` exists only on this unmerged
   branch. Changing the bridge first gives a bridge that does not compile. Merge core, tag it,
   bump the pin, then edit the bridge.
2. **NT8's own compile has NOT been run** on this window. The parse check is not a substitute.
   It needs a deploy, and deploying unmerged code to the live guarded box is the operator's call.
3. Then `UI3` — the read/write layer is done, so the next landing is the bridge routes and the
   static page (`UI_REDESIGN_DESIGN.md` §10 items 3-4).

## 5.22 Session 25 — 2026-08-13: shipped `v1.3.0`, then `P1-80`, `P1-81` and the rule registry

Four landings in one session. `main` carries all of them; `v1.3.0` is deployed and NT8-compiled.

### 1. `v1.3.0` — `UI1` + `UI2` merged, tagged, deployed, compiled

**`P?-64`, `P?-65` and `P1-79` closed**, which empties the untriaged band. Bridge pin bumped and
its `CopierConfigFile` now delegates to `TradeCopierEngine.ConfigFilePath` — the change that was
blocked on the tag existing.

**`nt_compile` returned 0 errors, and that is the number that mattered.** `TradeCopierWindow.cs`
is one 1100-line `#if !TESTING` block, so `dotnet build` compiles it to *nothing* and NT8 was the
only thing that had ever type-checked it. Live config reloaded intact through the hot-swap.

⚠️ **`P?-64` cost no configuration in the end.** The orphaned `CopierConfig.json` held the *same*
values as the canonical file — the window's writes went nowhere since August while the bridge kept
the real file current. The mechanism was as described; the outcome was not the loss it implied.
Recorded because overstating a closed defect's impact is its own kind of drift.

### 2. `P1-80` — three config files, one live, and a write that faked success

Found by asking **"which of these files does anything actually READ?"** — a question worth
re-asking anywhere config accumulates.

| File | Read by | |
|---|---|---|
| `RiskGuard/config.json` | `RiskGuardAddOn.cs:333` | the real one |
| `RiskGuard/riskguard_config.json` | **nothing** | written by the bridge |
| `RiskGuard/RiskConfig.json` | **nothing, either repo** | zero references |

The bridge's `RiskGuardConfig` write path, with the guard not loaded, stashed the body in
`_riskGuardConfig`, wrote it, and returned `success = true, status = "persisted_only"`. **That
dictionary was declared, loaded at startup, and never read by anything** — so the config was not
applied then, not at the next startup, and never would be.

**Measured on the box**: it held `trailingDrawdown: 500` against a live `1500`, and
`RiskConfig.json` said `OnMissing: "AutoStop"` against a live `"Flatten"`. Files stating protection
that was not in force.

⚠️ **THE TELL GENERALISES: the READ half of that same method already refused, while the WRITE half
pretended to succeed.** When one direction of a pair refuses and the other does not, the permissive
one is usually wrong. Fixed by **deletion, not wiring** — wiring the store up would have created a
second source of truth for the guard's limits, which is the defect one layer up.

### 3. `UI3` — the guard rule inventory, and a fourth state

**All 54 leaves of `RiskConfig` + `PropFirmProtectionConfig` are classified**, and a reflection
test fails the build if one is neither a rule nor an explicit non-rule with a reason.

**`P1-77`, `P2-25` and `P2-78` are ONE defect** — a config field can be born with no evaluator and
nothing notices — and the registry converts it from an audit finding into a build failure.

⚠️ **A static "is this field read?" check finds two of the three and MISSES `P2-25` entirely.** The
news shield's flag defaults `true`, `RiskGuardAddOn.cs:1541` genuinely tests it, it genuinely calls
a real `IsInNewsWindow`, which genuinely iterates a real list — that nothing outside a test appends
to, because `LocalNewsEventsFilePath` has no loader. **Every mechanical check passes on a rule that
has never once been able to fire.** That is the fourth state — **`INERT`** — and only a runtime
read, asking each rule how much evidence it had, can report it. Design in
[UI_REDESIGN_DESIGN.md](UI_REDESIGN_DESIGN.md) §6a.

Structural rather than asserted: no evaluator ⇒ `CONFIGURED-not-EVALUATED` **by construction**;
empty evidence ⇒ `INERT`; `DeriveState` is the only place the vocabulary lives; the not-a-rule
hatch **requires** a reason so it cannot quiet an inconvenient field.

### 4. `P1-81` — an arming flag that arms nothing

`PropFirmProtectionConfig.ArmedForLive` is read by its own `confirmLive` gate and the parser, and
by nothing else. The prop rules that work are gated by the **guard's** mode instead. Both readings
of the flag are wrong. Found *by having to state what reads it* — the registry earning its keep
before it has a UI.

### What the batteries taught, which is worth more than the features

`UI3`'s 15 mutants: **three survived together and were one gap** — the evidence count is the
mechanism that makes `INERT` work, and it was asserted for **1 of the 5** rules using it.

Two things went wrong fixing that, both general:

1. ⚠️ **My first fix was TOO BROAD and called four correct rules defects.** `MaxOrdersPerSecond`
   and the three `StopGuard` settings are scalar — they always have their input and act on every
   position. **A test that calls correct behaviour a defect gets the CODE changed to satisfy it**,
   which here would have made the guard's own stop handling report as not protecting anything. Two
   evaluators *were* genuinely wrong and were corrected instead.
2. ⚠️ **The fix opened an escape route, and its own mutant proved it.** Scoping the check to
   labelled rules made a *missing* label mean "do not check me" — deleting the news shield's label
   exempted the one rule the design exists for, and nothing failed. The classification is
   **derived** now: run every evaluator against an empty and a populated context; evidence that
   moves must carry a label, scalar must not.

**`UI2` is the companion lesson: a ONE-ROUND green is when to trust it least.** The loop took all
12 acceptance tests red→green in a single pass — best result any ticket here has had — and 17 of 18
mutants died, with the survivor showing that *absent-means-unchanged* was asserted for one request
builder and never its twin. And **the panel filed three BLOCKERs, all false** (each inverted
`ApplyArmingGate`'s condition), plus two false `MAJOR`s — but the invariant they pointed at was
pinned by nothing, so it has three tests and two mutants now. **A wrong finding aimed at an
unpinned invariant still earns the test.**

⚠️ **What no gate here would ever have caught, and reading the diff did**: the `UI2` patch had
stripped every emoji from the copier row labels. No test reads a label. **A model normalising
non-ASCII is a silent scope change — diff the surface, not just the logic.**

### State

Suite **1101/0**. **Nine** mutation batteries, 0 survivors, all wired into CI (the guard fired on
two commits this session). **81 IDs, 15 open, 66 closed.** The `P0` band and the untriaged band are
both empty. Config files on the box: **six, each read by something** — three stale ones deleted.

### Next

`UI_REDESIGN_DESIGN.md` §10 items 3-4: **bridge routes** (static serving + a snapshot endpoint;
SSE already exists) then **the page itself**. That is the first point at which any of this becomes
something the operator can look at. `F-9` (firm mapping) follows, and is what makes the risk half
of the inspector tell the truth.

⚠️ Still true and still load-bearing: **`P1-57`'s fan-out did NOT fire** — only `Sim-ORB` acted
because the third-party copier was not running. Re-measure the blast radius before the next live
test rather than trusting the §0 pre-flight's "three followers".

---

## 5.23 Session 26 — 2026-08-13: the UI became something you can look at

**Five tags — `v1.4.0` → `v1.8.0` — all deployed, `nt_compile` 0 errors each time.** The rule
inventory now has a producer, a wire format, two bridge routes, a browser page, and the copier
half. Suite **1134/0**, **12 mutation batteries** in CI.

### What landed

| | What | Evidence |
|---|---|---|
| `UI4` | **The producer.** `RiskGuardAddOn.BuildGuardSnapshot()`. UI3 declared 25 rules and four states and *nothing ever ran them* — `GuardSnapshot` was a DTO with no constructor call. | 13 tests, 23 mutants |
| `UI5` | **The wire format, in core.** `GuardSnapshotJson` + the fleet summary. | 6 tests, 9 mutants |
| bridge | `/api/riskguard/inventory` (`?view=summary`, `?account=`), `/api/copier/snapshot`, `/ui` | live-verified |
| page | `nt8-mcp-bridge/ui/index.html` — fleet, inspector, copier | live-verified |
| `UI6` | **The copier half.** `CopierSnapshotJson` with a stated severity rank. | 5 tests, 12 mutants |

### The two things a future session must not rediscover

⚠️ **1. `GuardRuleState` and `CopierConformance` look alike and must be treated differently.**
`GuardRuleState`'s integer order **is** its severity order and a battery pins it. `CopierConformance`
reads `Idle=0, Match=1, Shadow=2, Diverged=3, Orphan=4, Quarantined=5` — **historical numbering,
not severity**. Sorting by that cast puts a healthy `Idle` row first and an **`Orphan`** — leader
flat, follower still holding a live position nothing is managing — *below* a quarantined one. That
is the worst row this system emits, sorted into the middle of the table. The rank is therefore
stated once in `CopierSnapshotJson.SeverityRank` and travels **on each row**; the page sorts by a
number it is handed. A mutant that replaces it with the cast is the reason `mutate_ui6.py` exists.

⚠️ **2. There is now ONE auth exemption in the bridge, and it is scoped to static assets.**
A browser cannot send an `Authorization` header on a top-level navigation, so `/ui`'s files are
readable without a token — an HTML file and its JavaScript, **no account data**. The page holds the
token in `localStorage` and sends it as a Bearer header on every `/api/` call, so the data path is
unchanged. Traversal out of the ui directory returns 403 (verified live).
**If a `/ui/` path ever returns anything account-derived, that exemption becomes a hole.**
The alternative — a token in the query string — would put it in browser history and every referrer.

> ⚠️ **A latent fail-open worth closing**: `CheckAuth` opens with
> `if (string.IsNullOrEmpty(requiredToken)) return true;`. Delete `mcp_token.txt` with
> `NT8_MCP_TOKEN` unset and **the bridge silently accepts everything** — no log line, no warning.
> That is `configured / evaluated / enforcing` in the auth layer. Latent only because both sources
> are present and agree today.

### Two defects, opened and closed the same day

* **`P2-82`** — the rule registry was **publicly mutable**: `Rules` exposed its backing `List` as
  `IList`, so any caller could `Add` one. That is **`P1-77` inverted and the more dangerous
  direction** — a config field with no evaluator renders red and fails safe; an *invented* rule
  renders green.
* **`P2-83`** — a snapshot with no accounts rendered as entirely healthy. `P1-77`'s cap is broken
  for every account equally, so it is a property of the **build**. Hence `UnevaluatedRules`.

### What measuring the deployed box changed, twice

**Neither of these was reachable by reasoning, and both were found in minutes by fetching the real
payload.**

1. The inventory passed 1123 tests and returned **96 accounts × 25 rules = 2400 rows, 648 KB**, on
   a page that polls. Every test used two accounts, because two proves the logic. Fixed with a
   fleet summary → **22 KB**, whose counts are **recomputed from the detail rows in the test**
   rather than compared to a hand-written expectation, so the two cannot drift.
2. Opening the page showed all 96 accounts; **88 have zero cash and zero net liquidation** —
   expired prop accounts the connection still lists. Exactly **one** is funded
   (`TAKEPROFITPRO524207503`, $50,122). ⚠️ **The filter is in the PAGE, not the API**: the guard
   tracks all 96 and the snapshot keeps saying so. The hidden count is always stated, an excluded
   or locked-out account is never hidden whatever its equity, and anything that traded today stays
   — because hiding a **live** account would hide risk.

### The battery lessons this session

Three UI4 mutants survived the first run and **no two shared a cause**: a field never observed
being *false* (`IsArmed` hardcoded true — every build in the test happened to be armed); a fix
applied to **one of two identical accessors** (`NonRules` kept handing back its list, and the
ticket's own note had warned about exactly that); and an **unreachable fallback**, which was
**deleted** rather than pinned — "an evaluator returns null" cannot happen, so returning a reading
became a *contract asserted over every rule* instead. Three UI6 mutants survived for three more
reasons, including one that echoed `expected` into `actual` and made **every row match** with no
test noticing.

⚠️ **A mutant that reinstates the TRUTH proves nothing.** `ruleCount = 25` survived because 25 *is*
the registry's count today. Rewritten as `99`, it died instantly. Read the mutant before concluding
the test is weak.

✅ **One real defect the tests caught before a browser could**:
`CamelCasePropertyNamesContractResolver` camel-cases **dictionary keys** as well as properties, so
the fleet said `inert` where the detail rows said `Inert` — one fact, two spellings, in one payload.

### Deploy note

`deploy.py` ships the **vendored core**, so the pin must be bumped *before* deploying a bridge
change that calls a new core method. One intermediate compile failed for exactly that reason
(`ToSummaryJson` did not exist at `v1.5.0`); the running assembly was unaffected, because a failed
compile does not hot-swap. The stale-pin guard refused a deploy earlier in the same sequence, which
is precisely its job.

### Next

**Goal 1 of the two this UI exists for — *configure both systems* — is completely untouched.**
Everything above serves goal 2 (*prove they do what was configured*). Nothing on the page is
editable. Also open: live SSE updates instead of the 5 s poll (the channel already exists), notes
that cite defect IDs instead of plain language, and the NT8 Control Center menu item (§7.4) so the
page is reachable without typing a URL.

`F-9` (firm mapping) still follows, and is what makes the risk half of the inspector tell the truth.

## 5.24 Sessions 27–28 — 2026-08-13: the page learned to write, and a refusal learned to say why

⚠️ **These two sessions were never written up at the time.** This section is reconstructed from the
commits, the tags and the live box, so treat the *narrative* as thinner than §5.23's — the facts
below were re-checked, the emphasis may not be what the sessions felt like.

**`v1.9.0` → `v1.11.0`**, all deployed, `nt_compile` 0 errors.

| Tag | What |
|---|---|
| `v1.9.0` | A **Control Center menu item** that launches the browser page, and operator-readable notes |
| `v1.10.0` | **`UI7`** — a refused write carries its reason |
| `v1.11.0` | **`P2-27` step 1** (the NT8 stubs extracted from the test file), and `docs/CONFIG_DEFAULTS.md` |

### `UI7` — the defect was that a refusal arrived as a NullReferenceException

Both `ApplyRelationshipRequest` and `ApplyGroupRequest` refuse by returning `null`. Every surface
then said some version of *"the engine refused"* and stopped, because the reason existed only in
the copier log — and the browser page has no log window at all. Worse, the bridge's two write
branches **dereferenced the result without checking it** (`rel.IsEnabled` on a null), so a refusal
reached the operator as an exception, **after `SaveToDisk` had already run**.

Both methods gained an `out string refusalReason` overload. The reason is **built once and handed
to both the log and the caller** — a test pins that they are the same string, because two copies of
one explanation drift and the one the operator reads is the one nobody maintained. The 2-argument
overload survives for the ~40 fixtures that apply a request they know cannot be refused, and a
source scan forbids an **operator surface** reaching for it.

### The page became editable — the first half of the reason this UI exists

`nt8-mcp-bridge/ui/index.html` gained relationship enable/disable and quarantine release: a
confirmation naming what will change, a rendered refusal when the engine says no, and cancel that
changes nothing. Verified in a real browser, all four paths.

⚠️ **Goal 1 — *configure both systems* — is still only started.** What is editable is the two
actions that already had engine-side refusal gates. Nothing else on the page can be changed.

### `P2-27` step 1, and why the loop still cannot gate the bridge

The NT8 stubs (591 lines) moved out of `RiskGuardAddOnTests.cs` into `tests/TestingStubs.cs`,
byte-identical, so another repo can consume them. Suite unchanged at 1147/0.

**Measured and recorded rather than excused**: `nt8-mcp-bridge` sets `EnableDefaultCompileItems=false`
and compiles only `BridgeSourceTests.cs`, so the agent-loop's build gate **cannot see a patch to
`McpBridgeAddOn.cs`**. A profile whose build gate is blind to the file being edited is a trap, so
one was deliberately **not** written. Steps 2–4 remain: three missing stubs (`ChartBars`,
`DrawingTools`, `LogLevel`), namespace shims, the `CS1061` member tail, then putting
`McpBridgeAddOn.cs` + the vendored core into `BridgeTests.csproj`.

### Two things found by asking what READS a field

Both went into `docs/CONFIG_DEFAULTS.md` and were fixed in the next session (§5.25):

* **Three dead copier fields** — `StealthMode`, the copier's own `DailyLossLimit`, and the whole
  `CopierExecutionMode` enum. All persisted, all settable, branched on nowhere.
* ⚠️ **The attribution gap, still open.** `interventions.jsonl` records every copier write with its
  exact payload and timestamp, and **carries no client identity**. One shared bearer token, no
  source logged, so a change made by the browser page, an MCP tool, `curl`, or another machine is
  **indistinguishable after the fact**. Two writes at `04:47:43` and `04:47:52` on 2026-08-13 could
  not be attributed to anything done in that session. Not filed as a defect ID: it needs a decision
  about what identity means here (a per-client token? a source header the page sets?) before it can
  be specified.

---

## 5.25 Session 29 — 2026-08-13: the config defaults, applied — and what applying them found

**`v1.12.0` → `v1.12.1`**, deployed, `nt_compile` 0 errors, deploy parity verified.
Suite **1188/0**, **18** mutation batteries / 0 survivors, **205 anchors / 0 broken**.

Every delta in `docs/CONFIG_DEFAULTS.md` is applied. Eight defects closed — `P1-82`…`P1-89` — and
one opened that is the most serious item now outstanding.

### What changed, in one line each

| ID | What | Why it mattered |
|---|---|---|
| `P1-82` | `EnableNewsShield` + `EnableConsistencyCap` default `false` | The only two flags that defaulted ON while doing nothing |
| `P1-86` | A rule with no evidence reports `INERT` whether its switch is on or off | `P1-82` had converted `P2-25` into a *preference* |
| `P1-83` | Four dead config fields deleted, plus the gate that finds the fifth | `StealthMode` had **four surfaces** asserting it |
| `P1-84` | `StopAttachSeconds` 3→15, `MaxPositionSize` 100→10 (both DTOs), `MinShadowSessions` 0→5 | Defaults that make the guard easier to switch off than to live with |
| `P1-85` | The copier stopped inventing an account when a request omits one | `"Sim101"`/`"SimCopy2"` are **real, connected accounts on this box** |
| `P1-87` | An unrecognised `StopGuard.OnMissing` no longer means silence | A typo emitted **no action** for a position with no stop |
| `P1-88` | An unrecognised copier action is refused instead of answered as a write | Two live writes returned `success:true, persisted:true` and changed nothing |
| `P1-89` | A copier read resolves by leader **and** follower | A request naming `SimCopy2` came back carrying `Sim-ORB`'s object |

### ⚠️ The five things a future session must not rediscover

**1. A default is stated TWICE, and the second copy is the one that runs.**
`P1-82` looked like two literals and was four: each `PropFirmProtectionConfig` default appears as a
property initializer **and** as the final fallback in `ParseConfig`, and the parser copy is what
runs for any config file that predates the field — which is every config file on this box. Fixing
only the property would have been **green in the suite and unchanged in production**. The class
gate cannot catch it, because the gate builds its config with `new`; only a test asserting the two
copies **agree** can, and mutants 3–4 of `mutate_p182.py` exist to prove it.

**2. Switching off a broken rule can hide that it is broken — and this plan predicted it.**
The `P1-77` entry warned in writing: *do not "fix" a dead flag by defaulting it false, that keeps
the lie and makes it quieter.* Half of that is dead and half was exactly right.

* It does **not** hold for the consistency cap: `CONFIGURED-not-EVALUATED` is derived from
  `Evaluator == null`, so that row stays red whatever the flag says.
* It held precisely for the news shield, whose evaluator opened with `!EnableNewsShield ? Off(...)`.
  With the flag off the inventory reported it **`Disabled`** — documented as *"not a defect"*.

> **The rule to carry forward: `Disabled` means "this would work if you turned it on".** A rule with
> nothing to evaluate does not qualify however its switch is set. **Before defaulting any enabling
> flag to `false`, check the rule behind it still reports its defect with the switch off.**

⚠️ **`DeriveState` is deliberately NOT the place to fix that.** Moving the evidence check above the
`DisabledByConfig` check there is the shorter diff and a real defect: the two `FirmMirror` rules,
the window gate and the two working prop rules all short-circuit to `Off(...)` *without* gathering
evidence, so all five would start reporting `INERT` and the inventory would call
deliberately-disabled rules defects.

**3. Dead config fields are load-bearing in the tests.**
Ten merge-preservation probes used `StealthMode` / `Mode` / the copier's `DailyLossLimit` —
*"a field the request never mentions survives the merge"* — chosen **precisely because nothing read
them**. Deleting them broke ten assertions. They now probe live fields (`IsQuarantined` +
`QuarantineReason`, `AutoSymbolConversion`), which is a better test anyway: the quarantine flag is
a field the Add form genuinely cannot show.

**4. `P1-83`'s gate is scoped to the ENGINE, and that is the design, not a shortcut.**
It walks both copier DTOs by reflection and counts real uses in `TradeCopierEngine.cs`, discounting
a field's own declaration, `X = something.X` clone/serializer lines, and the field-name string list.
Widen it to the window and **`StealthMode` scores as READ** — because the window printed
`Stealth: ON` for it. That is the defect told louder, not an absolution from it.
And it is honest about its limit: it is source text, so it **cannot** catch `P2-25`'s class (a field
genuinely read by a branch that can never be reached). The guard side needed a runtime registry for
that; **the copier side still has none**, which is recorded as open.

**5. Four of the six new defects came from EVIDENCE, not from reading code.**
Two from mutation batteries, one from checking what a fix did to the inventory, one from the review
panel. Only `P1-83` came from reading — and only because the question being asked was *"what reads
this field?"* rather than *"what does this field do?"*.

### `P1-87` — the one to know, and how it was found

`mutate_p184.py`'s mutant 3 changed `StopGuard.OnMissing` from `"Flatten"` to `"AutoStop"` and
**all 1180 tests stayed green**. Nothing pinned the guard's most consequential default. Asking why
led to the dispatch in `EvaluateGraceExpiry`: two exact string comparisons and **no `else`**. A
lower-case `"flatten"`, a typo, an empty string, or the `"WarnOnly"` the declaration itself
advertised matched nothing — so the guard emitted **no action at all** for a position with no stop,
past its grace period. `RunPreflight` refuses an unrecognised guard *mode* and had never looked at
this, so the failure was silent at startup and silent at the moment it mattered.

⚠️ **The suite was DEFENDING the defect, not merely silent about it.**
`TestStopGuardWarnOnlyProducesNoAction` asserted *"No action generated when OnMissing is WarnOnly"* —
the defect, written down as the expected behaviour. Deleted. This is
[[test-doubles-are-not-evidence]] in a new place: a green suite can encode the bug.

### ⚠️ `P1-90` — OPEN, and its band letter understates it

Found by grepping `nt8-mcp-bridge` for the guess `P1-85` had just removed from the engine. Three
order paths (`McpBridgeAddOn.cs:2386`, `:2453`, `:4422`) resolve the account as:

```
the named account
  ?? the account called "Sim101"
  ?? ANY account not called "Backtest"
  ?? ANY account at all
```

So `nt_place_order` with a name that does not resolve — a typo, wrong case, a disconnected
account — **is not refused. The order is placed somewhere else.** The live box reports **96
accounts**.

`P1-85` was the same guess on a *config* path and was rated `P1` because a config guess writes the
wrong config. **This one opens the wrong position**, so it belongs with the `P0` band on
consequence. Three further `"Sim101"` fallbacks sit on account-resolution paths (`:1848`, `:4166`,
`:5621`) and should be reviewed with it.

**The fix is refusal**, as it was for `P1-85`: an order that cannot say which account it is for has
no safe interpretation. Deliberately **not** attempted in the session that found it — it changes
order routing and that repo has no executable tests (`P2-27`).

### `mutation/check_anchors.py` — new, and it earned its place three times

A battery locates each mutant by an exact source substring. When an unrelated commit edits that
source the find-string stops matching: the battery prints `[SKIP]` and scores the mutant a
**SURVIVOR** — **but only when the battery is run, and a battery only runs when the suite is green.**
So a stale anchor is invisible for as long as nobody happens to run that file. `mutate_ui2`'s anchor
was broken by the `UI7` commit and stayed broken through a whole session for exactly that reason.

The new check reads each battery's `MUTANTS` list by AST — importing one *executes* it — and counts
substrings. All ~205 anchors in about a second, and **it works while the suite is RED**, which is
precisely when a battery can tell you nothing. It runs first in CI.

In this session alone it found **11 stale anchors across five batteries**: two broken by `P1-85`,
eight by `P1-83`'s deletion, one by a comment edit. Every one would have scored a survivor.
**Two of the three breakages were mine.**

### Three things the agent-loop taught, which are about the tool and not the code

Every ticket this session went through the loop except one.

1. ⚠️ **The loop cannot perform a deletion.** Removing a symbol that a **protected** test file
   references fails its compile gate — the patch is correct and the build breaks anyway, on a file
   the loop may not touch. `P1-83` had to be done by hand.
2. ⚠️ **A region that covers only the `if` half of an `if/else-if` chain makes every patch leave a
   dangling `else`.** Four rounds of `P1-87` failed to compile on a region boundary rather than on
   anything the implementer wrote. Widen to the enclosing method.
3. ⚠️ **A ticket saying a value is "tied to" another field will get you a computed property when
   you meant a comment.** `P1-84`'s implementer turned `StopAttachSeconds` into a getter that reads
   `OnMissing`; the reviewers were right to refuse it (a config reload could move a deadline while
   a grace timer was already running, and it reads `OnMissing` off one thread while another writes
   it). The ticket invited it.

Also worth knowing: two runs ended `NOT_CONVERGING` and said *"arbitrate the findings by hand"* —
and in both cases the last green round was the right patch and the surviving findings were real but
small. The verdict is not a reason to discard the work.

### Verified on the live box, after the deploy

* Rule inventory: news shield reports **`INERT`** (not `Disabled`) with the flag defaulted off —
  `P1-86` working in production. Consistency cap still `CONFIGURED-not-EVALUATED`; `P1-77` open.
* `stealthMode` and `mode` no longer appear in the copier snapshot payload — `P1-83` confirmed.
* Stored config brought to the new defaults: `StopAttachSeconds 15`, `MinShadowSessions 5`, both
  relationships `MaxPositionSize 10`, guard in `shadow`, both relationships **disarmed**.
* `P1-88` live-validated: the exact request that used to return `success:true, persisted:true` now
  returns `success:false, UNKNOWN_COPIER_ACTION, persisted:false` and lists the valid actions.

⚠️ **CHANGING A DEFAULT DOES NOT CHANGE A DEPLOYED BOX.** The new defaults only apply to fields
*absent* from the stored config, and `StopAttachSeconds` and `MinShadowSessions` were both present
with their old values. The deploy was clean, the tests were green, and the running guard still had
`StopAttachSeconds = 3` until it was written explicitly. **After changing a default, go and look at
what the box actually holds.**

---


## 5.26 Session 30 — 2026-08-13: `P1-90` closed and live-validated, and two lies the repo was telling about itself

**Core `v1.12.1` → `v1.12.2`; bridge `P1-90`.** Both deployed, `nt_compile` 0 errors, deploy parity
verified from both repos (10 files). Core suite **1188/0**; bridge suite **23 → 50/0**.
205 anchors / 0 broken.

This session began as a documentation pass and found two live problems in the first ten minutes,
which is the whole argument for re-measuring instead of reading.

### The two things the repo was asserting falsely about itself

**1. CI had been RED for 7 consecutive runs** — since 04:16 UTC, spanning sessions 27, 28 and 29 —
while §0 said *"CI ✅ active in both repos … watched fail on purpose, not just pass."* One gate:
`tools/check_version_matches_tag.py`, reporting constant `1.10.0` against tag `v1.12.1`. So
`GET /api/riskguard/version` answered **`1.10.0`** on the live box for code that was `v1.12.1`.

> **The gate was added by `c92605e`, titled *"the addon reported 1.1.0 while v1.2.0 was deployed —
> and now a gate says so."* It was built for exactly this failure, it fired on schedule, and two
> tags shipped over it.** A gate nobody reads is a comment. Fixed as `v1.12.2`; the live box now
> answers `1.12.2`.

**2. The bridge's submodule pin was stale in the way the guard exists to catch.** It vendored
`v1.12.0` against a `v1.12.1` core, and the range **touched `addons/GuardRules.cs`** — so deploying
the bridge would have written an older `GuardRules.cs` over the live one. `deploy.py` refused it
(exit 2), correctly.

> ⚠️ **A tag whose own commit touches no `addons/` file can still carry core code in its RANGE.**
> `v1.12.1`'s tagged commit edits only `mutation/`; the change to `GuardRules.cs` is in an
> intermediate commit. This is precisely why the guard compares a **range** against `addons/` rather
> than a single commit, and why *"that tag was docs-only"* is never a safe reason to skip a pin bump.
> Check it: `git diff --name-only <pin>..<main> -- addons/`.
>
> It also **blocked `P1-90`**, because the fix lands in the bridge and `deploy.py` ships bridge and
> vendored core together. Order forced by that: bump pin → fix → deploy once.

### §0 was 11 tags stale, and the reading order made that worse

§0 claimed suite 1053, 78 defect IDs, `v1.2.0`, 6 batteries. §5.25 recorded 1188, 92, `v1.12.1`, 18.
Every correct number was already in the file. Sessions 22–29 each appended a `§5.x` and none came
back to the header, so the documented reading order — *"§0, then §5 from §5.6"* — handed a reader a
**correct order of work and a wrong set of facts about what is deployed**.

What was done about it, beyond correcting the numbers:

* §0 now says **which rows were measured for the pass and which were carried forward**, and why
  (`nt_compile` was deliberately not re-run: it reloads every addon on a box whose guard is armed).
* **§5.1's duplicate figures were deleted rather than updated.** Current state lives in exactly one
  place. A second copy of a number is a second thing to forget.
* `VERSION.md`'s identifier table named **`v1.0.2`** as the authoritative tag — 11 releases stale, in
  the one document whose entire subject is which version identifier to trust. Its release notes
  stopped at `v1.0.2`; the missing fifteen are now a table **derived from `git`** with the script to
  regenerate it, rather than fifteen sections written from memory.

### `P1-90` — the fix, and where it had to live

All **six** guessing sites refuse now. The three non-order sites were triaged individually rather
than swept, because they were not the same defect:

| Site | What it actually was |
|---|---|
| `PlaceOrder`, `PlaceOcoOrder`, `PlaceAtmOrder` | Guessed on **both** omission and typo, then placed. The `P0`-consequence three. |
| `DeployStrategy` | Guessed only on **omission** (a typo was already refused below) — but it *enables* a strategy, which then places its own orders. |
| `GetComplianceReport` | Same shape. A wrong compliance report is an answer an operator acts on: another account's drawdown against this one's limit, under a heading naming the account they asked about. |
| **`HandleLockout`** | ⚠️ **The sharpest of the six.** It took the guessed name straight into `UnlockAccount`, which **removes protection**, with no existence check at all. Omitting the field unlocked `Sim101`; a **typo** returned `success:true, isLockedOut:false` for an account that does not exist — which reads as reassurance. |

**The resolution moved OUT of `McpBridgeAddOn.cs`** into `addons/BridgeAccountResolver.cs`. The
reason is the reason this repo keeps hitting walls: that file is 6013 lines and in **no test build**
(`P2-27`), so anything inside it can be pinned only by source regex. The new file names **no
NinjaTrader type** — it takes account names as strings — so `BridgeTests.csproj` compiles and
**executes** it. That is the first bridge production source this project tests rather than greps,
and it is `P2-27`'s cheapest available step. `tools/deploy.py` globs `addons/*.cs`, so it needed no
registration to ship.

### Live-validated, on the deployed build

```
nt_place_order account="NoSuchAccount_P190"  -> refused, naming the 96 available accounts
nt_place_order account="sim101"              -> passes the account gate, stops at the symbol check
nt_compliance_report (account omitted)       -> "no `account` field was supplied"
```

⚠️ **The probe was designed so it could not place an order even if the fix were broken.**
`PlaceOrder` resolves the account **before** validating the symbol, so a bad account plus a
deliberately invalid symbol is refused by one check or the other. The second line matters as much as
the first: it proves the resolver does not **over**-refuse, and that case-insensitive matching
survived.

### Two new gates, and one mutant that survived the first draft

* **`mutation/mutate_p190.py`** — the bridge repo's **first** mutation battery. 11 mutants, 0
  survivors. Seven mutate the resolver and die to executed behaviour; four mutate the call sites and
  can only die to source assertions. **The split is labelled in the file**, because the second half
  proves less and the honest thing is to say which half is which.
* **`tools/check_bridge_parses.py`** — ported from `check_window_parses.py`. A syntax error in any
  addon `.cs` stops **every** addon loading, the risk guard included, and until now nothing here
  could catch one before it was written to the live NT8 folder. **Verified by breaking the resolver
  on purpose** and watching it report `CS1026`/`CS1513`.

⚠️ **One mutant SURVIVED the first draft of the tests, and it is the one worth remembering.**
Narrowing the emptiness check to `name == null` means `"   "` is reported **not found** instead of
**missing** — it still refuses, so every *"was it refused?"* assertion held. `P1-85` recorded this
exact lesson (missing and blank are different inputs) and it still had to be re-learned one layer
out. The assertion that the two reasons are **distinguishable** was added because of the survivor.

### 🆕 `P1-91` — opened by the validation, in the third repo

Four MCP tool schemas still declare `default: 'Sim101'` on `account`, **two of them order tools**
(`nt_place_oco_order`, `nt_place_atm_order`, plus `nt_compliance_report` and `nt_deploy_strategy`).
Two problems: the contract now misdescribes the engine, and — the one that matters — **an MCP client
that materialises schema defaults would inject `Sim101` into an order call and the refusal would
never be reached.** Measured: the client in use today does *not* materialise them, which is a
property of that client and not of the contract. Same shape as `P1-75`.

Not attempted here: it needs an MCP server restart, which would have dropped the live tool
connections being used to validate `P1-90`.

### What this session says about the method

Four findings, and **not one came from reading code with the intent of reviewing it**:

1. CI red — from running `gh run list` before trusting a documented "green".
2. The stale pin — from running `deploy.py --verify` rather than believing §5.1's *"bridge pin bumped
   to match."*
3. The surviving mutant — from mutating a fix that already had passing tests.
4. `P1-91` — from **reading the tool schema before probing with it**.

The first two cost about 90 seconds each. **Both were being asserted as fine, in writing, by the
document whose job is to say what is true.**

### Next

`P1-91` first — it is small, and it partially undoes `P1-90` on two order paths for any client that
reads defaults. Then §5.6's ordering stands unchanged: the UI **write** half, then `P3-31`'s ledger →
timer → the RiskGuard-side audit. `P2-27` now has a demonstrated cheap step (extract, then execute)
and it should be spent on `TradeCopierWindow.cs` and the rest of `McpBridgeAddOn.cs` the same way.

---

## 5.27 Session 31 — 2026-08-13: `P1-91` through the loop, and three things that had to be built before it could run

**`P1-91` closed.** `ninjatrader-mcp` suite **33 → 40/0**, in a repo that had no executable coverage
of its tool schemas at all. Parent pin bumped. ⚠️ **Not in effect until the MCP server restarts** —
tool schemas are read at startup.

The fix itself is six deleted schema defaults and seven corrected `required` arrays. Everything worth
reading here is what surrounded it.

### The loop could not take the ticket, for three separate reasons

Each was found by trying, not by reading, and each is now recorded where the next session will hit it.

1. **`python-tvdownloadohlc` cannot gate a `.js` file.** Its `build_cmd` is `py_compile`, which errors
   on JavaScript, and its `test_cmd` is two **Python** suites that pass no matter what a patch does to
   the MCP server. Pointing it there would have produced **a gate that cannot fail** — which that
   profile's own comments warn about, at that exact field. New profile:
   `agent/js_ninjatrader_mcp.py`.
2. **`ninjatrader-mcp` is a git submodule.** The loop patches inside a worktree, and **a worktree of
   the parent does not check submodules out** — so a parent-side profile resolves cleanly during
   `--list`, against the live tree, and then finds nothing to patch. The profile and tickets had to
   live **inside** that repo, which is the arrangement `nt8-riskguard` already uses.
3. ⚠️ **The loop cannot parse Node's test output**, and the field that looks like the fix is dead.
   `agent_loop.gates.parse_tests` understands two formats: the NT8 suite's (`[FAIL] msg` plus
   `RESULTS: Passed = N, Failed = M`) and pytest's. Node prints `ℹ pass 37` / `ℹ fail 3`. The first
   run died at baseline with *"produced no parseable result summary"* **before reaching a model.**
   **`Profile.test_runner_regex` is declared at `agent_loop/profiles.py:78` and read by nothing in
   the package** — `P1-83`'s defect class, in the tool.

> `agent/loop_test_reporter.mjs` emits the NT8 shape. **The NT8 shape rather than pytest's for a
> specific reason: its `[FAIL]` lines carry the failing test's NAME, and a ticket's `expect_green` is
> matched against those lines.** Without per-failure names the test-first gate cannot tell which test
> went green, and is vacuous — see [[agent-loop-expect-green-semantics]].
>
> It is not trusted by eye. `agent/verify_reporter.py` feeds the reporter's real output through the
> loop's **real parser** and asserts on what comes back — `ran=True`, the counts, the extracted
> failure names, and that the exit code tracks the result. It also refuses the case where the reporter
> finds no test files and would hand the loop **a green baseline for a suite that never ran**.

### ⚠️ The acceptance test found two more defects — and its first version was WRONG

The test was written against the defect *class* — "a schema default supplies a consequential argument
the caller never sent" — rather than against `P1-91`'s four filed instances. Running it found **six**,
not four. The two new ones are on `action`:

| Tool | Default | Enum includes |
|---|---|---|
| `nt_alert` | `webhook` | **`flatten`** |
| `nt_multi_account_orchestrator` | `sync_hedge` | **`group_flatten`** |

`sync_hedge` adjusts positions **across accounts**. An omitted `action` doing that is `P1-90`'s class
exactly.

**And the first draft of that test would have made things worse.** It forbade any `default` on
`action`. There are four, and **two are correct**: `nt_prop_limits` defaults to `get` and
`nt_trade_journal` to `list` — both the READ, which is the fail-closed direction. To go green, the
implementer would have had to **delete two safe defaults and make two working tools worse.**

> **The rule is which way the default falls, not whether one exists: a defaulted `action` must itself
> be a read.** That keeps the two correct ones and still catches the two that matter.
>
> This is [[mutation-testing-beats-review]]'s "a too-broad test gets the CODE broken to satisfy it",
> and it was caught only because the test's **output** was read rather than its verdict. A red test
> that is red for the wrong reason looks exactly like a red test.

### ⚠️ What `P1-91` does NOT do, measured — and it is not what the ID implies

The MCP server **never reads `.default`, never reads `inputSchema`, and does not validate `required`
at all.** Both halves of the fix therefore do different amounts of work:

* **Deleting the defaults is a real behavioural change**, for any MCP client that materialises schema
  defaults into a request. That was the risk: an injected `Sim101` is a **real connected account**, so
  the addon resolves it happily and `P1-90`'s refusal is never reached.
* **Adding `required` adds no server-side gate here.** It makes the contract truthful and lets a
  validating client fail fast. **The enforcement remains the addon's refusal** — `P1-90`,
  live-validated.

Do not read the commit as *"the server now rejects an order with no account"*. The server does not
reject it; the addon does. Saying which one enforces a rule is the whole content of
[[configured-evaluated-enforcing]].

### The loop went green in ONE round, which is when to trust it least

Round 1, `kimi-k2.7-code`, panel APPROVE/APPROVE, all three acceptance tests green, no regressions.
Per §5.21 that is the moment for more scrutiny, not less, so the patch was read line by line against
the spec before anything was applied, and:

* **the applied diff was confirmed byte-identical to the candidate that was reviewed** — the loop
  does not ship, and `--resume-raw … --apply` is a fresh run, not a promote;
* the two safe `action` defaults were confirmed **absent from the diff**;
* the `required` arrays were confirmed **appended to, not rewritten** — dropping `idempotencyKey`
  from an order tool would admit duplicate orders, a worse defect than the one being fixed;
* the real server was driven over **stdio JSON-RPC** afterwards: 52 tools, zero account defaults, five
  tools requiring an account.

**Then the guard test was mutation-checked**, because it is the one assertion whose failure had never
been observed: making `nt_orders` require an account **failed it correctly**, and the tree was
restored. A guard that has never been seen to fail is not known to be a guard —
[[mutation-anchors-go-stale]].

### One prerequisite worth reusing

`const TOOLS` was extracted from `nt-mcp-server.js` into `lib/tools.js` so that tests could assert on
the **real schema objects** instead of grepping source text. That is the third time this move has
paid: `P1-90`'s account resolver, and `lib/copier-config-request.js` before it — whose own header says
it exists because *"importing nt-mcp-server.js starts its stdin readline loop, so a test of a function
defined there would hang."*

**The pattern: extract what names no platform type and has no side effects, then execute it.** It is
`P2-27`'s cheapest step and it now has three instances. Verified the extraction changed nothing by
driving `tools/list` over real stdio: 52 tools, `nt_place_order` present.

### Next

`P1-91` was the last item that any band letter called urgent, and **the `P0` band and every
naked-risk item are closed.** What remains is §5.6's ordering: the UI **write** half (goal 1 of the
two this UI exists for is still mostly untouched), then `P3-31`'s ledger → timer → the RiskGuard-side
audit, then `P1-57`, `P1-13` and the `P2` band. ⚠️ **Superseded by §5.30**: `F-9` and `F-9b` are
done and live, and the next item is `P2-95`. Kept because the ordering argument still holds.
`F-9` (the firm mapping) was, at the time of writing, the largest
config item, and it is the mechanism that replaces guessing at every dollar-denominated default.

### One housekeeping note

The first loop run in `ninjatrader-mcp` **committed 10 per-run artifacts** — prompts, raw model
output, both reviewers' text, the candidate patch. That repo had no `logs/agent_loop/*` block; it
now carries the same one as this repo and tvDownloadOHLC, ledger exceptions included. **All three
repos agree now**, and the `/*`-not-`/` reason is written in each: git never descends into an
excluded directory, so a negation beneath one is silently impossible.

⚠️ **Restart the MCP server** before assuming `P1-91` is live, and re-read §0 rather than this section
for state — this one will be stale the moment the next item lands.

---

## 5.28 Session 32 record — 2026-08-13: `F-9` landed, and three things only the live box could tell me

`F-9` — the account → firm-plan mapping — is **live and validated**. Suite **1188 → 1200**, one new
mutation battery (11 mutants, 0 survivors), `P2-92` filed. Every claim below was measured on the
deployed box, not derived.

### The measurement came first, and it changed the design three times

**1. The four researched firm profiles were GONE.** `CONFIG_DEFAULTS` R3 said the mechanism "already
exists and is switched off", citing `FirmMirror.Enabled = false` and an empty `AccountFirmMap`. Both
true. What nobody had noticed is that **`FirmProfiles` was `{}` too**, where §*P1-42* records four
fully researched profiles present on 2026-08-07. `P2-41` took them — the empty-body POST that
deserialised `{}` into a complete `RiskConfig` — before that defect was closed, and this programme's
own defaults document then recorded the wreckage as the baseline.

> **A default and an erasure look identical in a config file.** That is the transferable lesson, and
> it is why `docs/_recovered_firm_profiles_20260807.json` now exists: the profiles were recoverable
> only from `config.json.bak_prearm_20260807_061407`, and a `.bak` file is one cleanup away from gone.
> Written up as `CONFIG_DEFAULTS` **R3a**.

**2. The account names encode the firm, and the sizes do not.** The box lists 96 accounts, and their
prefixes name the same four firms as the recovered profiles: `TAKEPROFIT*`/`TAKEPROFITPRO*`,
`APEX*`/`PAAPEX*`, `TDYG*`/`TDFYG*`/`FTDFYG*` (Tradeify), `LFE*` (Lucid). **The size is nowhere in the
name**, and the operator's fleet is one 50k plus four 100k Sim accounts — confirmed independently by
equity (`Sim_All_Day_ORB` reads 49,833.70; the others 98,140–100,511).

One `Apex` key carrying one dollar amount cannot serve both. So `FirmProfiles` is now keyed by
**plan** — `Apex-100K`, `TakeProfitTrader-50K`. The key is an opaque string, so this needed **no code
change**, which is the only reason it was affordable in the same session.

⚠️ Also worth stating because it is R3's own complaint turned on the research: **none of the four
recovered profiles states an account size.** Apex publishes 2,500 on a 50k and 3,000 on a 100k; the
profile says 2,000, which matches neither. Tighter than the firm's number is the safe direction — the
guard speaks before the firm does, which is what `Buffer` is for — but *nothing in the config says
which direction it is*. **Filed, not fixed**: nothing machine-checks that a plan named `-100K` was
derived for a 100k account. That wants `FirmProfile.AccountSize` plus a preflight comparison against
observed equity. Until it exists, the account size lives in a dictionary key.

**3. `P2-92`, filed: `shadow` mode is not observation-only.** Found by asking what enabling two more
lockout-capable rules would actually *do*. `ProcessAction` gates **execution** on mode, so a shadow
breach logs `SHADOW_ACTION` and flattens nothing. But the rules set `IsLockedOut` **before** dispatch,
outside any mode check, and `CanTrade` reads that flag **above** its own `if (!_isArmed) return true;`
escape hatch. So in shadow: nothing is flattened **and the account stops being allowed to trade**. The
copier and every strategy consult `CanTrade`, and its three refusal paths log to `Output.Process` only
(`P1-71`), so nothing readable says why. The comment at `:116` covers persistence across *disarming*,
which is a different axis and is correct. **This is why the mapping was kept to Sim accounts**: an
`Apex-100K` breach needs an 1,800 drop from peak, which is an ordinary week for an ORB strategy.

### The code half was a defect in BOTH directions, and only a derived test found that

`P1-42` made the **enforcer** resolve a per-account effective firm config. `GuardRules`' two firm
rules never followed — they branched on the **top-level** sub-rule switch and reported the
**top-level** `Amount`.

The acceptance matrix runs every combination of the four switches against **both** rules and derives
its expectation *from the enforcer* rather than restating it by hand. Four disagreements:

| Reporter | Enforcer | Shape | What the operator is told |
|---|---|---|---|
| `Disabled` | **FIRES** | top-level off, plan's rule on | the UI **hides live protection** |
| `Enforcing` | silent | top-level on, plan's rule off | the UI **claims a rule that cannot fire** |

The second is the **real Take Profit Trader profile**, whose `DailyLoss` is off because TPT has no
daily loss limit. That is the direction that costs money, and it is now reported honestly: *"plan
'TakeProfitTrader-50K' has NO daily loss limit, which is that firm's actual rule -- not an oversight"*.

> **Why the expectation is derived and not tabulated.** A hand-written table of expected states would
> have to be updated by whoever next changes the resolution order — which is exactly the person who
> would get it wrong. Deriving it from the enforcer means a future divergence fails without anyone
> having thought of the specific case. Two of the eleven mutants are the argument for this: they keep
> the resolved *branch* and report the top-level *amount*, so every state assertion passes and the
> number beside the row is a limit the operator is not held to. That is `P1-42`'s own lesson — "the
> audit trail would describe a rule that did not run" — one layer out.

**Evidence is now per-account (`mapped ? 1 : 0`), not the map's size.** The old expression counted the
whole `AccountFirmMap` on a rule declared `Scope = PerAccount`, so **one** mapped account reported
evidence for **all 96** of the box's accounts, 88 of which are expired prop accounts. Worth grepping
for elsewhere: a `PerAccount` rule reading a global collection.

### The loop stopped itself, correctly, and the hand-arbitration removed what it had added

Three rounds, and in **every one**: all 7 acceptance tests green, 1195/0, no regressions, lock-scope
clean. Blocking findings went **4 → 7 → 7 with zero overlap between consecutive rounds**, and the loop
refused to promote — *"Each revision is exposing new surface rather than closing the defect"*. That
stop condition earned its keep; the panel was churning on note prose while the mechanical gates had
been green since round 1.

Two changes to its candidate, both by hand:

* **Removed an `if (eff == null)` branch the panel demanded on a false premise.**
  `ResolveEffectiveFirmConfig` returns **`fm` itself** in every non-resolving path, so it cannot
  return null when `fm` is not null. 28 lines that could never execute — and had they executed, they
  returned "evaluated" **without checking whether the sub-rule was enabled**, which is the defect the
  finding claimed to prevent. Adding an unreachable branch to the file whose own header is about
  `P2-25` is backwards. ⚠️ **This is the second failure mode of the arbiter recorded here**: §5.x has
  it upholding 0 of 66 findings across four `SHIP` rulings; here it upheld one that does not hold.
* **Replaced its `ContainsKey` with `TryGetValue` plus a null check.** A `FirmProfiles` entry whose
  **value** is null answers `ContainsKey` true while the resolver falls back, so the note claimed a
  plan's numbers were in force when the top-level block's were. `"FirmProfiles": { "Apex-100K": null }`
  is one typo from a real config file. The panel *raised* this and its own arbiter dismissed it as
  settled; it is now mutant 9 and a test.

One of **my own** tests was wrong too, in the familiar direction: it wrapped the daily-loss limit in
`Math.Abs` to avoid committing to the sign convention, which left a sign flip unpinned — and a mutant
survived it. The assertion now names the sign.

`check_anchors.py` caught `mutate_ui3`'s firm-evidence anchor going stale on this change: its
find-string was the `AccountFirmMap.Count` expression that F-9 deleted. **216 anchors, 0 broken** after
re-anchoring, and the re-anchored mutant was re-run and killed rather than assumed.

### Live validation, and what it corrected about this document

Deployed via `sync_nt8.py` (1 file synced, 7 identical) and `nt_compile` — **0 errors**. Config applied
by `POST /api/riskguard/config` with a partial body; the before/after diff shows **28 changed keys, all
inside `FirmMirror`, and 48 unchanged** — `RiskConfigMerge` behaved.

| Account | Equity | Firm trailing drawdown | Firm daily loss |
|---|---|---|---|
| `Sim_All_Day_ORB` | 49,833.70 | `EvaluatedNotEnforcing`, limit **1500** (the plan's, not the top-level 2500) | `Disabled` — *"plan 'TakeProfitTrader-50K' has NO daily loss limit"* |
| `Sim-ORB` | 100,170.00 | `EvaluatedNotEnforcing`, limit **2000** | `EvaluatedNotEnforcing`, limit **-1000** |
| `TAKEPROFITPRO524207503` | 50,357.00 | `Disabled` | `Disabled` |

The five mapped accounts moved `Disabled: 4 → 2` and `EvaluatedNotEnforcing: 13 → 15` (the TPT-mapped
one to `14 / 3`, because its daily-loss rule is legitimately off). Mode `shadow`, `isArmed: true`, **no
lockouts**. The running code was confirmed by **content** — the plan-naming note text exists only in
the new build — not by the version constant.

⚠️ **Two corrections this document owes:**

1. **A recompile no longer disarms.** §4g and CLAUDE.md both say `_isArmed` is deliberately never
   rehydrated (`P1-37`) so every recompile leaves the guard disarmed. The audit log shows
   `SHUTDOWN`/`INITIALIZE` ×2 followed by **`ARMED_ON_START` ×2**, and `/api/riskguard/version`
   reported `isArmed: true` immediately after the compile. Something arms on start now — almost
   certainly `P1-47`'s fix. **Do not schedule a manual re-arm on that basis; measure.**
2. **The live config had never been preflighted.** It armed at 14:03 against the *previous* config,
   and `SaveAndReloadConfig` writes and reloads **without running preflight** — by design, which is
   why `ResolveEffectiveFirmConfig` is documented as not depending on it. The consequence is sharper
   than it looks: a firm-mirror config that *cannot* pass preflight comes up **disarmed at the next
   restart**, with nothing about the file looking wrong. There is **no preflight endpoint on the
   bridge**, so it is now pinned in the suite instead —
   `TestF9_TheDeployedFirmMappingPassesPreflight` asserts the exact deployed values pass, with the
   paired negative that a typo'd plan key fails **and names the key**. Five account names is five
   chances to make that typo, and the operator's own spelling of `Sim_All_Day_ORB` in this session
   used a hyphen.

### Deliberately not done, and why

**`TAKEPROFITPRO524207503` is not mapped.** It is the live 50k TPT PRO account, it held an open MES
position and a trade during this session, and its firm rules therefore still read `Disabled`. Mapping
it means asserting TPT's current published thresholds, which were not verified against TPT's rulebook
in this session — the recovered 1500 is *researched*, dated 2026-08-02, and undated research on a
funded account's drawdown is exactly what R3 exists to stop. It is a one-line addition to
`AccountFirmMap` when the operator confirms the plan and its size.

**`FirmProfile.AccountSize` + preflight size validation** is the follow-on, and is the largest
remaining item in `CONFIG_DEFAULTS`. **`P2-92` should probably come first**, because it is what makes
a shadow-mode firm breach halt a bot.

⚠️ Re-read §0 rather than this section for state — this one will be stale the moment the next item
lands.

---

## 5.29 Session 33 record — 2026-08-13: two tracks — the firm mapping, and the defects it exposed

Run as two tracks on purpose, at the operator's instruction: extend the firm mapping *while* fixing
the defects, rather than queueing one behind the other. The tracks turned out to be coupled in a way
that decided the order — see *"why the funded account is still unmapped"* below.

### Landed

| | |
|---|---|
| **`P2-92` (1/2)** | ✅ `AccountState.LockoutWasShadowOnly` + `MarkRuleLockout` + `CanTrade` reads the authority + persistence. Suite **1213 → 1216** |
| **`F-9b`** | Acceptance tests + `FirmProfile.AccountSize`. Implementation in flight |
| **`P2-93`** | 🆕 `pure` and `override_with_friction` pass preflight's *enforcement* gate and then act on nothing |
| **`P2-94`** | 🆕 A **timed** manual lockout does not stop new orders — `CanTrade` never reads `LockoutUntil` |
| **`CONFIG_DEFAULTS` R3b** | Why the map cannot be completed from measurement, measured rather than assumed |

Counts re-derived: **96 IDs** (93 banded + 3 `P?-`), **19 open**.

### `P2-92`: the fix is not the one it looks like

`ProcessAction` gates *execution* on mode, so a shadow breach flattens nothing. But ten rule paths set
`IsLockedOut` **before** dispatch, outside any mode check, and `CanTrade` reads that flag **above** its
own `if (!_isArmed) return true;` hatch. So in `shadow`: nothing is flattened **and the account stops
being allowed to trade** — the copier and every strategy consult `CanTrade`, and its refusal paths log
to `Output.Process` only (`P1-71`), so nothing readable says why a bot stood down.

**The obvious fix is wrong.** Making `CanTrade` consult the mode would mean the current mode at READ
time overrides the mode at BREACH time — so an operator locked out in `live` could escape by switching
to `shadow`. That is `FR-30` / judge-loop `P1-4`'s concern through a different setting, and
`LockoutBypassWhileDisarmedAccounts` cannot mitigate it because the guard is *armed*. What was missing
is the **authority** a lockout was imposed under, so that is what gets recorded.

⚠️ **The field is named for the shadow case deliberately: `LockoutWasShadowOnly`.** An absent `bool`
deserialises `false`, which must read as *enforced*. `LockoutWasEnforced` would have every state file
written before this change release its lockouts on upgrade. `P1-54` reasoned identically about
`LockoutUntil`, and there is a test for the legacy file.

⚠️ **AND THE SUITE WAS DEFENDING THE DEFECT.** Eight existing tests breach a rule in the DEFAULT mode
— which is `shadow` — and assert `state.IsLockedOut`. That is `P1-87`'s shape. They were left alone,
because the state model is not the defect: `IsLockedOut` meaning *"this account has breached"* is
right, and the enforcement decision belongs to the consumer. **A fix that stopped writing the flag
would have broken all eight and been indistinguishable, from the test output, from a fix that broke
the guard.** That is the whole reason the authority went into a second field rather than into the
first one's meaning.

### What the panel was worth, precisely

Hand-arbitrated, round 2 of 3. Round 1 failed to compile. **Round 2 passed every mechanical gate** —
compile, full suite with no regressions, acceptance test green, lock-scope clean. Round 3 spent
**294 s and 140,000 thinking characters** and failed to compile. Round 2 is what landed, applied by
extracting its region blocks from `r2_impl_raw.txt`.

Three of the arbiter's four upheld findings **do not hold**: all three argue that shadow mode failing
to flatten a breached position is a defect *of this patch*, when it is the definition of the mode and
is unchanged by it — the exposure after the patch is identical to the exposure before it, minus an
unintended side effect. The arbiter's rationale then recommended *"suppress `IsLockedOut` entirely in
shadow mode"*, which is the fix the ticket explicitly rules out and which breaks those eight tests.
**That is the second recorded instance of this arbiter upholding findings that do not hold** (§5.28
has the first; §5.x has it upholding 0 of 66 across four `SHIP` rulings).

The fourth finding **is real**, and round 2 had already handled it: an account that breached in shadow
carries the flag with shadow authority, so a manual lockout that only sets `IsLockedOut` — already
true — leaves the stale authority standing and is **silently ignored**. There is now a test. And
following that one finding into the adjacent code found **`P2-94`**.

> **The lesson is not "the panel is useless".** It is: read every finding against the code, act on the
> ones that hold, and follow them into the neighbourhood. One correct finding out of four paid for the
> round, because it led somewhere.

### A test-design lesson that cost a whole loop run

The source gate's assertion message embedded its counts and the offending line numbers:

```
all 0 rule-breach lockout sites record whether the guard could act (10 do not: line 1482 ...)
```

`agent-loop` matches an `expect_green` string **anywhere inside** a failure line, so volatile trailing
detail is harmless *there* — memory records that as the feature which lets an assertion carry
`(got 3, expected 4)`. But the loop **also diffs the whole set of failure lines** against the baseline
to find regressions. When `T1` fixed two of the ten sites the message changed, so the loop scored the
old line **NEWLY PASSING** and the new line a **REGRESSION**, on a test that had merely moved from
0/10 to 2/10. It could never converge, and the run was killed.

> **A failure message is an IDENTIFIER for baseline diffing and a DESCRIPTION for a human. When those
> conflict, the identifier wins and the description moves to stdout.** Nine assertions across the
> `F-9` / `F-9b` / `P2-92` blocks were rewritten that way.

Two other self-inflicted costs on the same ticket, both worth avoiding by habit:

* **A 13-region ticket over a 6,000-line file.** Split into `T1` (the mechanism) + `T2` (route the
  remaining eight sites). `F-9`'s single 241-line region and this ticket's first attempt both churned.
* **A write to a class the ticket gave no region for.** Two rounds failed to compile writing
  `AccountPersistedData.LockoutWasShadowOnly` — `AccountState` and `AccountPersistedData` are
  different classes and **both** have a `FirmStartingBalance` and a `LockoutUntil`. My ticket's defect,
  not the model's, and `--list` cannot catch it because the region it needed simply was not there.

### The mapping track: why it cannot be finished by measuring

Measured with `nt_accounts`, because *"map the rest of the accounts"* looked like typing and is not.

**Only 6 of the 96 accounts report any equity** — the five Sim accounts and `TAKEPROFITPRO524207503`.
The other ~89 return `cashValue: 0, netLiquidation: 0`: expired or unconnected prop accounts the
connection still lists. **The platform does not know their size**, and no field in the payload carries
one (`name / provider / denomination / cashValue / netLiquidation / realizedPnL / unrealizedPnL /
buyingPower`).

The prefixes do name the firm — `TAKEPROFIT*`/`TAKEPROFITPRO*`, `APEX*`/`PAAPEX*` (`PA` = performance
/funded), `TDYG*`/`TDFYG*`/`FTDFYG*` (Tradeify), `LFE*` (Lucid) — the same four firms as the recovered
profiles. ⚠️ **The Tradeify numbers appear to embed the size** (`TDYG50…` ×5 vs `TDYG100…` ×1), which
would map six accounts in one line. **It has not been acted on**: six samples and an inference, and R3
exists precisely to stop a dollar limit being inferred. `provider` is `Provider31` for every real prop
account and `Simulator` for every Sim one — worth knowing separately, since `P1-20` settled that sim
accounts are identified by provider and never by a name prefix.

**So completing the map needs a size stated per account.** That is not a tooling gap; it is
information that exists only outside the platform.

What *is* machine-checkable became `F-9b`: `FirmProfile.AccountSize` plus a preflight refusal on the
two silent failures — a mapping naming an account that **does not exist** (`P1-90`'s class one layer
out: there a name that did not resolve placed an order on an arbitrary account, here it removes
protection from the right one), and a plan whose **stated size contradicts** the account's observed
equity. Both refusals must name the offending value; a preflight failure means the guard does not arm,
so a refusal that is not actionable is worse than none.

⚠️ Three over-application guards, each a test, because the same mistake in both directions is treating
*"I cannot check this"* as *"this is wrong"*: an **unstated** size (`0`) is checked for nothing; a
**zero-equity** account is not size-checked (89 of 96 read zero — refusing over those means this box
never arms again); but a zero-equity account **is** existence-checked, or that exemption swallows the
gate.

### Why the funded account is still unmapped, and what unblocks it

`TAKEPROFITPRO524207503` — the live 50k TPT PRO, which traded during the session and closed
`+$324.50` — remains **unmapped**, so its firm rules still read `Disabled`. Two reasons, in order:

1. **`P2-92` gates it.** Mapping it arms a rule whose breach, until `P2-92` is fully landed, would set
   an enforced-looking lockout and **stop the account trading** while flattening nothing. Its floor
   under `TakeProfitTrader-50K` would be peak − 1,300. Mapping a funded account into that is not a
   defensible order of operations, and it is why the two tracks are coupled rather than parallel.
2. **The threshold is undated research.** The recovered `1500` is dated 2026-08-02 and states no
   account size. Asserting a funded account's drawdown limit from undated research is exactly what R3
   exists to prevent.

It is one line in `AccountFirmMap` once `P2-92` (2/2) is deployed and the operator confirms the plan
and its size.

### In flight at the end of this record

* **`P2-92` (2/2)** — routes the remaining eight lockout sites; its gate is the source scan, which is
  the one test still red for that ticket.
* **`F-9b`** — implementation; five assertions red.
* **A mutation battery for `P2-92`** — not yet written. ⚠️ **`P2-92` is not finished without one**: the
  interesting mutants are the ones that pass every existing test (invert the authority sense; gate
  `LockAccount` too; let a shadow lockout persist as enforced) and this programme's own record says a
  fix without a battery is a fix nobody has measured.

⚠️ Re-read §0 rather than this section for state.

---

## 5.30 Session 33 continued — the firm research, and what it corrected

The operator named their four firms and asked for the current plans, then corrected the readings. That
turned the firm mapping from a guess into configuration, and in doing so found that **everything
`F-9` had deployed was wrong**.

### The corrections, and the one that mattered

The four profiles recovered from the 2026-08-07 backup (§R3a) carried **no account size**, and the
sizes inferred for two of them were wrong:

| Recovered profile | What its numbers actually are | Was deployed as | Now |
|---|---|---|---|
| `TakeProfitTrader` 1500 `eod` | TPT's **25K** max loss | `TakeProfitTrader-50K` | **`TPT-50K-PRO`** — 2000, **`intraday`**, `LockAtProfit` 2000 |
| `Apex` 2000 / DLL 1000 | Apex's **50K EOD** row *exactly* | `Apex-100K` | **`Apex-100K-EOD`** — 3000, DLL 1500 realised |
| `Tradeify` 2000 / 1250 | Tradeify **50K** (correctly sized, wrongly labelled) | — | not mapped |
| `Lucid` 2500 / 2500 | ⚠️ **no Lucid plan at any size** | — | discarded |

⚠️ **The type error was the dangerous one, and it is not a "tighter is safer" case.** A TPT **PRO**
account trails **intraday until the buffer is hit** (the operator's words), not `eod`. An intraday
trail follows peak equity *including unrealized*, so its floor rises during a winning session while an
EOD model's stays stale and **lower** — the firm's floor ends up **above** the guard's and the firm
fails you first. Both amount errors erred *tighter* than the firm, which is safe but fires early (R5).

**Operator corrections applied**: the funded account is a 50K PRO; `PAAPEX*` are the funded accounts;
`TDYG` is Tradeify Growth and the `F` marks funded; `LFE` is Lucid evaluation; all firms are on a
**realised** DLL basis except some Apex accounts.

### Firm + size is not a plan

Every one of the four firms sells **multiple rule sets at the same account size**. Tradeify's 100K max
loss is 2500, 3000, 3500 or 4000 depending on family; Apex sells an EOD product *with* a daily loss
limit and an intraday one *without*, at every size; TPT's Test and PRO+ trail EOD while PRO trails
intraday. So `FirmProfiles` keys now carry the **variant** — `TPT-50K-PRO`, `Apex-100K-EOD`. No code
change; the key is an opaque string. What it changes is what must be *known* per account, which is the
part only the operator can supply. Full tables in **[FIRM_PLANS_RESEARCH.md](FIRM_PLANS_RESEARCH.md)**.

### `LockAtProfit` existed and was being used wrong

Apex, Lucid and TPT PRO all stop trailing once the threshold reaches the plan's starting balance (Apex
and Lucid: + $100). That is precisely `TrailingDD.LockAtProfit`'s semantics here — the floor locks when
`FirmTrailingPeak >= FirmStartingBalance + LockAtProfit`. Every recovered profile had **`0`**, meaning
the guard would keep trailing after the firm stopped and flatten on a drawdown the firm no longer
counts. `TPT-50K-PRO` sets it to `2000` (the amount), which is the first time this field has carried a
real value.

⚠️ **Setting it immediately exposed `P2-95`.** The lock reads `FirmStartingBalance`, which
`ComputeFirmMirror` captures as `balance - realized - unrealized` — the balance at *session* start, not
the plan's. On an account up $5,000 over its life that reads **55,000** instead of 50,000, so the
locked floor is $5,000 too high and the guard flattens $5,000 early. **The error grows with the
account's profit**, which is R5's failure mode getting worse the better you do. `AccountSize` is the
fix and is why it was added; the migration is the awkward part, because the field is already persisted
with heuristic values.

### How the config was applied, and why not over the API

`POST /api/riskguard/config` **merges**, so it cannot REMOVE a key — and the two wrongly-numbered
profiles had to go, not be shadowed by correctly-named neighbours. There is no reload route either. So
`config.json` was edited directly, whole-block, and `nt_compile` did the reload — which was needed
anyway to deploy `P2-92` and `F-9b`. Backed up first as
`config.json.bak_pre_f9_corrected_20260813_091902`, and verified afterwards that every top-level key
other than `FirmMirror` was untouched (`Mode` shadow, `MinShadowSessions` 5, 2 windows,
`StopAttachSeconds` 15).

### Live validation — the funded account is protected for the first time

| Account | Firm trailing drawdown | Firm daily loss |
|---|---|---|
| `TAKEPROFITPRO524207503` (live 50K PRO, 50,357) | `EvaluatedNotEnforcing`, limit **2000**, plan `TPT-50K-PRO` | `Disabled` — *"plan 'TPT-50K-PRO' has NO daily loss limit, which is that firm's actual rule -- not an oversight"* |
| `Sim_All_Day_ORB` (49,833) | same plan, limit **2000** | `Disabled` |
| `Sim-ORB` (100,170) | `Apex-100K-EOD`, limit **3000** | `EvaluatedNotEnforcing`, **-1500** |
| `APEX10121500000151` (unmapped, 0 equity) | `Disabled` | `Disabled` |

`nt_compile` 0 errors, mode `shadow`, **`isArmed: true`**, no lockouts. The arming matters most: it
proves `F-9b`'s two new preflight refusals do not block the real config, and a config that cannot pass
preflight comes up **disarmed** with nothing about the file looking wrong.

⚠️ Mapping the funded account was **gated on `P2-92`**, not on the numbers. Before it, a shadow breach
set an enforced-looking lockout and stopped the account trading while flattening nothing.

### `P2-92` closed, and what its battery cost to get right

11 mutants, **0 survivors**, suite **1209 → 1232**, 227 anchors clean. Three survived the first run —
and the battery's own docstring had *predicted* all three, which is worth noticing: **predicting a
survivor is not killing it.**

* Two were the persisted authority (write, and read-back). Both fail **closed**, so nothing looked
  wrong — and both mean a restart **promotes** a shadow observation into a real lockout, so the account
  stops trading for a breach that never enforced. A recompile is a restart here. Killed by a save/load
  round trip asserted in **both** directions, since "always restore as shadow-only" would pass the
  first half while releasing a real lockout.
* The third deleted the `SHADOW_LOCKOUT` log line and left 1,224 tests green. That is a bigger finding
  than the mutant: **nothing in this suite could observe that an audit event happened at all**, so
  every claim about this addon's log was pinned by source scan or not at all — `P1-70`'s and `P1-71`'s
  included. `LogEventObserver` now exists under `#if TESTING`, beside the lock-scope and disk-write
  probes and for the same reason. It fires **before** the `try`, so a test sees the event even when the
  disk write throws — the case a source scan cannot distinguish from a working one. Its signature is
  `(account, eventType)` deliberately: asserting on message text breaks on every rewording.

### Three defects filed from reading adjacent code

* **`P2-93`** — `pure` and `override_with_friction` pass preflight's *enforcement* gate (five shadow
  sessions) and then act on nothing, because `IsActingMode()` names only `live`.
* **`P2-94`** — a **timed** manual lockout does not stop new orders: `CanTrade` reads only
  `IsLockedOut`, and `LockAccount(name, 60)` sets only `LockoutUntil`. The sweep then flattens the
  fills. A clean refusal beats a fill followed by a flatten.
* **`P2-95`** — `FirmStartingBalance`, above.

### Still open on the mapping, and it is information, not code

Nothing is mapped for the ~89 zero-equity accounts, and this is not a tooling gap: only **6 of 96**
accounts report any equity, no field in the platform payload carries a plan size, and firm + size does
not determine the numbers anyway. Outstanding questions, each blocking a group of accounts: **which
Apex accounts are the exception to the realised DLL basis**; whether `APEX*` evaluations are the EOD or
the intraday product (they differ in whether a DLL exists at all); what `FTDFYG`'s leading `F` denotes
as distinct from `TDFYG`; and which Lucid plan the `LFE*` accounts are on.

⚠️ And the boundary of what the machine can check, because it is the error the research just found:
`F-9b` validates **account ↔ plan** size. It **cannot** validate **plan ↔ firm table** — the deployed
`Apex-100K` would have passed the size check easily while its amount was Apex's 50K number. Both are
plausible fractions of a 100k account. Only the firm's published table can say, and that is
`FIRM_PLANS_RESEARCH.md` plus a human pass.

⚠️ Re-read §0 rather than this section for state.

---

## 5.31 Session 34 record — 2026-08-13: four defects closed, 94 accounts mapped

**P2-95, P2-93, P2-94** closed first (code + tests), then **P3-31** via the agent loop (timer +
wiring) plus the `InFlightLedger` class implemented by hand when the loop's 4 rounds couldn't get
the acceptance tests green (it left the stub in place). Combined result: suite **1259/0**,
227 anchors / 0 broken, NT8 compile 0 errors.

### P2-95: FirmStartingBalance uses plan AccountSize, not heuristic

`ComputeFirmMirror` captured `FirmStartingBalance = balance - realized - unrealized`, and `realized`
is SESSION-scoped, so it was the session-start balance, not the plan's. On an account up $5,000
over its life it read 55,000 instead of 50,000, and the trail-lock floor was wrong by lifetime
profit — growing as the account does. Fix: `ResolveEffectiveFirmConfig` now carries
`FirmProfile.AccountSize` through a `[JsonIgnore]` transient field on `FirmMirrorConfig`
(`ResolvedAccountSize`), and `ComputeFirmMirror` uses it when non-zero, falling back to the
heuristic when the plan states no size. The `FirmMirror.ResolvedAccountSize` leaf was added to
`GuardRuleRegistry.NonRules` so the UI3 config-classification gate stays green.

### P2-93: pure and override_with_friction fail preflight

`IsActingMode()` returns true only for `"live"`, so `ProcessAction` answered `SHADOW (SKIPPED)` for
both `pure` and `override_with_friction`. But preflight's `MinShadowSessions` gate recognized all
three as enforcement modes, so an operator could wait out five shadow sessions to reach a mode that
enforces nothing. Fix: preflight now refuses to arm in either mode with `MODE_NOT_IMPLEMENTED`.
The `MinShadowSessions` gate now names only `"live"`. Implementing the two modes is a protection
increase and the operator's call.

### P2-94: CanTrade reads LockoutUntil for timed manual lockouts

`LockAccount(name, 60)` set `LockoutUntil` but not `IsLockedOut`. `CanTrade` read only
`IsLockedOut`, so new orders were admitted and the sweep then flattened the fills — worse than a
clean refusal. Fix: `CanTrade` now uses the same OR test as the sweep:
`IsLockedOut || (LockoutUntil > MinValue && UtcNow < LockoutUntil)`. `LockoutWasShadowOnly` still
applies (a timed manual lockout sets it to false, so it is never shadow-only and cannot be
bypassed). The existing `TestManualTimedLockout` was asserting `IsLockedOut == false` as the
defect's correct behaviour — that assertion was corrected and a `CanTrade` refusal assertion added.

### P3-31: in-flight order ledger + background reconciler timer

The `Reconcile` seam already accepted `stopSubmitInFlight`/`targetSubmitInFlight` booleans and
suppressed `Create` only (never `Cancel`). The ledger itself did not exist.

**InFlightLedger** (new class in `CopierReconciler.cs`): records a submitted order's identity
(account, instrument, leg name) before the broker call and removes it on `Settle` (order appeared
in `Account.Orders`) or `Fail` (submit returned null). Stale entries are purged after a timeout
(default 30s, testable with 2s). Thread-safe under a lock, OrdinalIgnoreCase keys.

**Background timer** (`TradeCopierEngine.cs`): a `System.Threading.Timer` fires every 5s, iterating
active brackets and calling the reconciler with the ledger's `IsInFlight` as `submitInFlight`. The
timer does NOT hold `_lock` across broker reads (P1-10/12). `PurgeExpired` is called on each tick.

**Event-driven callers** (`SyncFollowerStopOnce`, `SyncFollowerTargetOnce`) now register/clear
ledger entries around `Submit`, so the timer and the events agree.

`DecideLegActions` folds the ledger's `IsInFlight` into the `submitInFlight` parameter, so a
timer-driven reconcile suppresses `Create` when a leg is already on its way — preventing the
duplicate-leg family (P0-49, P0-55, P1-56, P0-59) through the very mechanism meant to cure it.

### Firm mapping: 94 accounts mapped across 9 profiles

All accounts now have default plan mappings. The operator confirmed `FTDFYG50481277664` is a funded
Tradeify account. Profiles added: `TPT-50K-Test` (EOD, 2000, no DLL), `Apex-50K-EOD` (EOD, 2000,
DLL 1000), `Apex-50K-EOD-PA` (EOD, 2000, DLL 1000, LockAtProfit 2100), `Tradeify-50K-Growth`
(EOD, 2000, DLL 1250), `Tradeify-100K-Growth` (EOD, 3500, DLL 2500),
`Tradeify-50K-Growth-Funded` (EOD, 2000, DLL 1250), `Lucid-50K-Flex` (EOD, 2000, no DLL,
LockAtProfit 2100). All zero-equity accounts pass preflight's size check (it skips them). The
operator will verify and correct each account's plan when it is actually used.

⚠️ The agent loop's `expect_green` naming: the loop matches against `[FAIL]` line text, not
test method names. Three intermediate commits failed CI because the `InFlightLedger` stub made
the acceptance tests fail; the final commit (`eb15210`) has the real implementation and passes.

---

## 5.32 Session 34 continued — P3-30: RiskGuard-side audit

The copier half of P3-30 shipped with the reconciler (§4u) and its timer (§5.31/P3-31). The guard
half did not exist. `FsmWatchdog` runs on events only, so a divergence arriving with no subsequent
event is permanent.

### What was built

`RunGuardAudit` runs on a `System.Threading.Timer` (default 10s, configurable via
`AuditIntervalSeconds`, 0 = disabled) and performs three checks per account+instrument:

1. **NAKED_POSITION** — broker has a position but no FSM is tracking it, or the FSM says
   `Unprotected` / `CoveredQuantity < PositionQuantity`. The existing `FsmWatchdog` already arms a
   grace timer for this on events; the audit is the clock-driven complement that catches the case
   where no event arrives.
2. **ORPHAN_STOP** — a working stop order exists but the position is flat. P0-50's class: an orphan
   stop on a flat account is a new position in the opposite direction the moment it triggers.
3. **FSM_DIVERGENCE** — the FSM says `Protected` but no working stop exists at the broker for that
   instrument. The FSM's optimistic fast path lost the truth.

The audit is an **observer**: it emits `LogEvent` only, never actions. Actions come from the
existing `FsmWatchdog`/`EvaluateRules` path. The audit does NOT hold `_stateLock` across broker
reads (P1-10/12). Shares `CoveredQuantity` from the existing FSM (per §4a: share it, do not
rebuild it). `RunAuditNow()` was wired to call `RunGuardAudit()` (the loop left the stub in place).
`AuditIntervalSeconds` added to `GuardRuleRegistry.NonRules` for the UI3 gate.

Suite **1262/0**, 227 anchors / 0 broken, NT8 compile 0 errors.

### P2-25: news shield loads events from disk

`LoadNewsEventsFromDisk` reads a JSON file of `EconomicNewsEvent` objects and populates
`_newsEvents`, which was only populated by `AddTestNewsEvent` before. Called from
`UpdateConfig` when `LocalNewsEventsFilePath` is non-empty. The news shield can now fire
in production once a JSON feed is placed at the configured path. The tvDownloadOHLC
economic-calendar pipeline can emit the feed.

### P2-24: dead code removed

`CalculateSafeFollowerDelta` was written but never called — the P0-5 fix is already in the
copy path. Removed the method and its tests. `ReconcileFollowerPosition` is now called by
the P3-31 timer. `LatencyMs`/`AvgSlippageTicks` are now computed and read (P1-69). `StealthMode`
was removed. `EnableFollowerAtm` was removed (P0-9). The remaining items from P2-24's list
are either wired or deleted.

---

## 5.33 Session 35 — 2026-08-13: `v1.14.0` + `v1.15.0`. A shipped feature that did not exist, and the copier gets a mode

Two tracks. The first was meant to be a review of session 34's work and turned into three defects
in one feature. The second was `P3-34`.

### The state this session found, versus the state §0 claimed

Worth recording because **every correction but one was in the reassuring direction**:

* **CI was GREEN, not red.** `gh run list` showed two runs "in_progress" at 1h29m and 1h40m, which
  reads as hung. It is not: **CI now runs all 20 mutation batteries on every push**, and 1h39m of
  that 1h40m is batteries. The suite step itself takes 20 seconds. Read the step timings before
  concluding anything from a long run.
* **The firm mapping was already done and live** — 94 accounts, 9 profiles, and the operator's
  `FTDFYG50481277664` correctly on `Tradeify-50K-Growth-Funded`.
* **The bridge pin was stale for the THIRD time**, and `deploy.py` refused for the third time.

### `P3-30`'s guard audit: three defects, and the suite could see none of them

The audit shipped in session 34 with 1264 green tests. All three of these were live on the box.

1. **It did not exist in the production build.** `StartAuditTimer`/`StopAuditTimer` were inside the
   `#if TESTING` block, under a banner reading `DEV/TESTING API`. So `AuditIntervalSeconds: 10` was
   in the live config on this box describing a ten-second audit whose code was **not in the net48
   assembly**. This is `P1-47`'s trap, and it was caught the only way it can be: `nt_compile` went
   red on `CS0103` once the wiring was added. **A green net8.0 suite cannot see this class at all.**
2. **Nothing called `StartAuditTimer`**, even in the test build.
3. **When it ran, it matched nothing.** Both broker reads keyed on `Instrument.ToString()`; every
   FSM in this addon keys on `Instrument.FullName` (19 call sites). The failure is INVERTED from
   what you would guess: not a missed finding, but a **correctly protected account reporting
   `NAKED_POSITION`, `ORPHAN_STOP` and `FSM_DIVERGENCE`, per instrument, every ten seconds** — the
   audit log drowning itself at exactly the moment it matters.

**Why the three shipped tests could not fail.** They are all POSITIVE-only — each asserts its event
*was* emitted. A total matching failure emits **every** event, so all three stay green under defect
3. The test that finds it is the complement: *a correctly protected account must produce SILENCE*.
That one failed on all three assertions at once, which is what a total matching failure looks like
from the outside.

> **The reusable rule: for a DETECTOR, the positive test is the cheap half, and the negative test is
> the one that proves the detector works at all.** A detector that fires on everything passes every
> positive test ever written for it.

Two more found in the same read: flat `Position` objects were audited as naked (the FSM-seeding
sweep has always filtered `MarketPosition.Flat || Quantity <= 0`; the audit did not), and
`ORPHAN_STOP` fired on `!hasPosition || !hasFsm`, so a stop correctly covering a live-but-untracked
position was reported as an orphan — a name meaning the opposite of the situation, duplicating the
`NAKED_POSITION` already emitted for it.

`mutation/mutate_p330.py`: 7 mutants, **6 killed, 1 documented survivor** — holding `_stateLock`
across the broker reads (`P1-10`/`P1-12`) survives because the test stubs never block, so **no test
in this suite can detect a deadlock**. Recorded in the battery rather than left to be rediscovered.

### 🆕 `tools/check_no_dead_safety_machinery.py` — `P2-24`'s class, made mechanical

`P2-24` was closed in session 34 by deleting `CalculateSafeFollowerDelta` for being uncalled. **The
same session produced three more instances of it**: `StartAuditTimer`, `RunCopierPreflight` and
`ReconcileFollowerPosition`. Three recurrences is what turns a defect into a gate.

The class is invisible to every other gate here: it compiles, its own tests call it directly so the
suite is green, a source scan finds the fields it reads, and the config surface advertising it looks
configured. Only *"does anything actually CALL this"* separates them.

The gate fails in **both** directions — an unrecorded dead entry point, **and** a `KNOWN_DEAD` entry
that has since been wired — so the allowlist cannot rot into a permanent excuse. It earned that
second direction the same session, reporting `RunCopierPreflight` as `WIRED-BUT-LISTED` the moment
`P3-34` gave it a caller. Verified by breaking the wiring on purpose (exit 1).

⚠️ **`ReconcileFollowerPosition` is still `KNOWN_DEAD`, and §5.32 records it as called by the P3-31
timer. That is FALSE** — the timer calls `SyncFollowerStopOnce`/`SyncFollowerTargetOnce`. It sits
inside `#if !TESTING` with zero coverage and it **flattens a live follower position**. Wiring an
uncovered flatten into a 5-second timer needs `P2-27` coverage first.

### `P3-34` — and what §0 says about it is half wrong

§0: *"The copier acts regardless of guard mode."* **Measured, half of that is false, and it is the
half you would act on.** A **live** follower was already gated three ways — `ArmedForLive`,
`CanTrade`, and `IsGuardProtecting`, which requires the guard's mode to be `live`, so **a shadow
guard already blocked live copies**. A **sim** follower was gated by none of them.

So the copier gets its **own** mode, not a reading of the guard's — because reading the guard's
would remove the thing the operator actually does: drive sim copies while the guard sits in shadow,
which is how §5.13's live validation was run.

| Mode | Behaviour |
|---|---|
| `live` | today's behaviour exactly, **and the default** |
| `shadow` | logs the fully-formed intended order, submits nothing |
| `disabled` | copier off, under its own event name |
| anything else | **does not trade** (`P1-87`: the permissive branch here places real orders) |

The gate sits **after** instrument, action and quantity are settled, not at the top of the loop: a
shadow line that cannot name the order it suppressed observes nothing. `COPY_BLOCKED_COPIER_*` keeps
`P1-71`'s one-outcome-per-relationship invariant by naming convention rather than by editing the
counter.

`RunCopierPreflight` now has a caller. `TrySetCopierMode` runs it when entering `live` and
**refuses** the transition on failure rather than reporting it and applying the change anyway
(`P1-88` inverted). **Leaving `live` is never gated** — a gate on the safe direction is one an
operator routes around, and routing around this one means staying live.

**The default is `live` deliberately.** §5.25: a new default only applies to fields *absent* from the
stored config, so every config on disk today lands on it. A safety feature that silently stops a
working copier on the next restart is one that gets turned off. **Moving the default to `shadow` is
a protection increase and the operator's call.**

`CopierConfigPayload` turned out to be **referenced by nothing in either repo** — `CopierMode` was
briefly added there and moved, because a field on an unused type is `P2-25`'s state exactly: it
reads as configuration and can never be read. The class is now marked.

`mutation/mutate_p334.py`: 9 mutants, **0 survivors**. Mutant 3 is the one to know — it keeps the
gate and deletes the `continue`, so the copy is logged as suppressed and then **submitted**; the
shape of the fix is entirely present for anyone skimming the diff. The first run left two survivors,
both persistence, and both are now covered by a disk round-trip test that drives the **write** half
as well as the read.

### ⚠️ What `P3-34` does NOT do, measured on the box rather than assumed

**`CopierMode` is not in the `/api/copier/config` payload.** The endpoint returns relationship-shaped
data, so the mode **cannot be observed or set over the bridge** — only by editing the config file.
**A mode you cannot read is a mode you cannot trust**, and this is `P1-69`'s class in a new place.
That surface is a bridge change (`P2-27`: untested) and belongs with the UI write half, §5.6 item 4.
**This is the next item.**

### Not live-validated, and it cannot be from a flat box

The audit is deployed, compiled and wired, and **the box is flat** — on a flat box a working audit
and an absent one both produce silence. The same is true of the copier's shadow mode. Proving either
fires needs a position, which is a scheduled live-validation item, not something a green suite
settles.

### Next

1. **The copier mode's read/write surface** — `/api/copier/config` and the `nt_copier_config` wrapper.
2. **`P2-27`** coverage for `ReconcileFollowerPosition`, then wire it (it is the last `KNOWN_DEAD`).
3. **`P2-29`** / **`P3-33`**, the architectural items, and the 3 `P?-` UI write items.

## 5.34 Session 35 continued — the copier mode's read surface, and three defects it found

`P3-34`'s core landed with a switch the operator could not see. Closing that gap found three
more defects, **all three by driving the deployed box rather than by reading code**.

### What shipped

* **`GET /api/copier/config`** now carries `copierMode`, a note saying what that means for order
  placement, and `notEnforcingReason`.
* **`POST action=set_mode`** routes to `TrySetCopierMode`. It **reads the mode back** and reports
  `applied` from what actually happened, not from the call returning — `P1-88` was a handler
  reporting an unwritten write as persisted, and `persisted` here is true only when the write
  occurred. `set_mode` is absent from `CopierReadFromQuery`'s read whitelist, so it cannot be
  issued as a URL.
* **`nt_copier_config`** gained `set_mode` and `copierMode` (in `tvDownloadOHLC`,
  `mcp/ninjatrader-mcp/lib/tools.js`). ⚠️ **Restart the MCP server** — schemas are read at startup.

### ⚠️ The `enforcing` field was wrong the moment the mode existed

`GET /api/copier/config` answered `enforcing = rel.IsEnabled && rel.ArmedForLive`. True until
`v1.15.0`, false immediately after: **a relationship can be enabled AND armed while the copier is
in `shadow`, in which case it enforces nothing and the page says it enforces.**

This is **`F-9`'s finding in a second place** — what a thing REPORTS drifting from what it DOES —
and the remedy is the same: derive the display **from** the enforcer. Both sites now go through
`nt8-mcp-bridge/addons/CopierEnforcementView.cs`, and a test asserts no branch still carries the
stale two-term form. That file exists for `BridgeAccountResolver`'s reason: `McpBridgeAddOn.cs` is
in no test build (`P2-27`), so anything inside it can be pinned only by source regex. It names no
NT8 type, so tests **execute** it. It deliberately does **not** decide what an acting mode is —
`TradeCopierEngine.IsCopierActingMode` owns that and the answer is passed in, so there is one
definition and the report cannot drift from the gate again. Bridge suite **50 → 69**.

### ⚠️ Two defects the LIVE AUDIT LOG found, minutes after deploying

Both invisible to a green suite *and* to the HTTP responses. Found by grepping
`interventions.jsonl` after driving the endpoint for real.

1. **A refused mode change left NO trace in the log** when the mode was unrecognised.
   `TrySetCopierMode` has two refusal returns and only the preflight one logged; the other
   returned a good message to the HTTP caller and wrote nothing. **The response body is not the
   record** — an operator asking afterwards why the copier is not in the mode they set greps the
   log, and found silence. `P1-71`'s class, in a path added to fix a *different* invisibility.
2. **The events logged as `COPIER_COPIER_MODE_CHANGED`.** `CopierLog` already prefixes
   `COPIER_`, so naming the event `COPIER_MODE_CHANGED` doubled it, at three sites. This log is
   grepped **by event type**, so a name nobody would guess is a line nobody finds. The copy-path
   events were already correct — they follow the existing `COPY_SUBMITTED` family, which
   `CopierLog` prefixes the same way.

A successful change is logged too now. A log carrying only failures cannot answer *"when did this
become shadow?"*, which is the question asked after a copier silently stops copying.

`mutate_p334.py` is **11 mutants / 0 survivors**. ⚠️ Mutant 1's anchor scored a **false SURVIVOR**
on the first re-run, because `v1.16.0` made the predicate `public` and the find-string stopped
matching — which is exactly what `check_anchors.py` exists for. **245 anchors / 0 broken.**

### ⚠️ `P1-72` has REGRESSED, and it was found the same way

`nt_copier_config` advertised `quarantine` and `unquarantine` in its action enum. Measured:

```
POST /api/copier/config {"action":"quarantine",...}
  -> {"success":false,"error":"UNKNOWN_COPIER_ACTION"}
```

`P1-72` was *"nt_copier_config advertised a quarantine action that nothing implemented"*, closed
2026-08-13, and the enum still listed both. It fails **closed and loudly** (`P1-88` made an
unrecognised action a refusal rather than a silent read), so it is a contract defect and not a
dangerous one — but **the enum is the only description of this surface a model ever sees**, so an
advertised action is a request that will be sent.

**The second half is worse than the first**: the field that actually releases a quarantine —
`isQuarantined` sent with `action: "set"`, which is what the browser page posts — **was not in the
schema at all**. The wrapper advertised two ways that do not work and omitted the one that does.
The test now asserts the enum against the addon's own `knownActions` whitelist, so the two cannot
drift silently again.

### Live-validated, end to end, then restored

On the deployed box: set to `shadow` (`applied`, `persisted`, and `CopierMode: "shadow"` on disk),
read back with the warning note, an unrecognised mode refused **with the mode unchanged**,
`set_mode` over `GET` refused, back to `live` with preflight passing and **both relationships
intact**. Then the two log defects fixed, redeployed, and re-driven: the audit log now shows the
old `COPIER_COPIER_MODE_CHANGED` lines directly above the new `COPIER_MODE_CHANGED` and
`COPIER_MODE_CHANGE_REFUSED` ones — the before and after, in one file.

### The pattern under all four defects in this half

**Every one was found by driving the deployed system and reading what it wrote** — not by review,
not by the suite, which was green throughout at 1300 then 1303. Two of them (the doubled prefix,
the silent refusal) existed for about ten minutes and would otherwise have shipped, because
nothing that runs before a deploy inspects the audit log's *contents*.

### Next

1. **`P2-27` coverage for `ReconcileFollowerPosition`**, then wire it — the last `KNOWN_DEAD`
   entry, inside `#if !TESTING`, and it **flattens a live follower position**.
2. **`P2-29`** (file complexity) and **`P3-33`** (global lock → actor model).
3. The 3 `P?-` UI write items, and the copier mode on the browser page — the endpoint now
   supports it, the page does not yet offer it.
4. ⚠️ **Still not live-validated**: the guard audit and the copier's shadow mode have never run
   against an open position. The box has been flat throughout, and on a flat box a working
   detector and an absent one both produce silence.

## 5.35 Session 35 continued — `P0-96`: the copier read a position's SIDE off the SIGN of its quantity

**This one placed a real, wrong-direction order, and 1300 green tests did not see it.** It was
found while reading `ReconcileFollowerPosition` for `P2-27` coverage — the defect was in the
*live copy path* next door, not in the dead code being reviewed.

### What it was

NT8's `Position.Quantity` is **absolute**. The side lives in `MarketPosition`, which is why that
property exists, and **every one of the ~1300 tests in this repo already models a short as
`MarketPosition.Short` with a positive quantity** — not one uses a negative. Two places read the
sign anyway:

```csharp
if (currentFollowerPos < 0) followerAction = OrderAction.BuyToCover;   // UNREACHABLE
else if (currentFollowerPos > 0) followerAction = OrderAction.Sell;    // runs for BOTH sides
```

So a leader **covering a short** sent the follower a `Sell`. **A `Sell` does not close a short —
it doubles it**, in a direction the leader has already left. The copier's own log said so the
moment a test drove it:

```
COPY_SUBMITTED: MNQ 03-26 Sell 1 submitted to 'SimFollower'
                mirroring leader 'SimLeader' BuyToCover 1@18000 (isExit=True)
```

`P0-5`'s family (*copier exit sizing is not position-mirroring → follower reverses*), reached by
a different route. The second site made `ReconcileFollowerPosition`'s `directionMismatch`
permanently false, so **the only branch in that method that takes a broker action could not
fire** — dead logic inside dead code.

### Why the suite could not see it, and this is the transferable part

Every **long**-side test passes under the defect. The suite had short *entries* and short *stop*
mirroring — §5.13's live validation was a short — but **no short EXIT test**, so the exit
*action* was never asserted on the short side. The defect lived in exactly the gap between two
well-covered things.

> **A convention the whole suite already encodes is not the same as a convention the code
> follows.** Every test modelled `Quantity` as absolute; two production sites read it as signed;
> nothing compared the two. That comparison is not something a reviewer does by reading a diff —
> the diff looks fine either way.

### What the mutants added, and both were surprises

`mutation/mutate_p096.py` — 5 mutants, **4 killed, 1 documented survivor**. Two mutants changed
the work:

* **Mutant 3 deletes the exit-alignment block outright** and everything stayed green, because
  `followerAction` already defaults to the leader's action. The block only matters when the
  follower is on the **opposite side to the leader** — a partial fill, a manual trade, a copy
  skipped while quarantined. That case now has a test, and without it the block reads as
  redundant to anyone who tries to simplify it.
* **Mutant 4 drops the `isExit` guard**, which turns a scale-in **entry** into an order that
  closes the position. Also green, also now pinned.
* The survivor is honest: the reconciler half is inside `#if !TESTING` and called by nothing, so
  no test here can reach it. **When `P2-27` makes it testable, that mutant is the first test to
  write.**

### Not live-validated, and deliberately not

Proving this on the box means a real short round trip through the copier. The fix is deployed
(`v1.18.0`, NT8 0 errors, live box answers `1.18.0`) and pinned by tests and mutants, but **no
short has been copied since**. That is a scheduled live-validation item, along with the guard
audit and the copier's shadow mode — all three are waiting on the same thing: an open position.

### Next

1. **`P2-27` coverage for `ReconcileFollowerPosition`**, which is what this session was starting
   when it found `P0-96`. It is the last `KNOWN_DEAD` entry, it is inside `#if !TESTING`, and it
   **flattens a live follower position**. `mutate_p096.py`'s surviving mutant is the first test.
2. A **live short round trip** through the copier, which validates `P0-96`, the guard audit and
   the copier's shadow mode in one run.
3. **`P2-29`** / **`P3-33`**, and the 3 `P?-` UI write items.

## 5.36 Session 35 — THE LIVE VALIDATION: three unvalidated features proved, two new defects found

The operator authorised sim-account testing. Everything below is **measured on the deployed box**,
on `MNQ SEP26` / `NQ SEP26` at ~30185, Thursday 20:19–20:23 ET, guard in `shadow` and armed.

Three things had been shipped-but-unproven for a whole session, all blocked on the same
prerequisite: **a flat box cannot distinguish a working detector from an absent one.**

### ✅ `P0-96` — validated, and the fix is the difference between flat and a doubled short

Arranged the exact divergent case: leader `Sim101` **long 1 NQ**, follower `Sim-ORB` **short 10
MNQ**, then the leader exits.

```
COPIER_COPY_SUBMITTED | MNQ SEP26 BuyToCover 10 submitted to 'Sim-ORB'
                        mirroring leader 'Sim101' Sell 1@30185.25 (isExit=True).
```

`BuyToCover 10` covered the follower's short to **flat**. **Before the fix this same event sent
`Sell 10`, taking `Sim-ORB` from short 10 to short 20** — the wrong direction, at double size,
while the leader was closing.

⚠️ **And the premise was confirmed on the platform, not just in the stubs**: `nt_positions`
reported `marketPosition: "Short", quantity: 10` — **positive**. `Position.Quantity` is absolute
in real NT8, exactly as the test suite has always modelled it and exactly as two production sites
did not.

### ✅ `P3-30`'s guard audit — validated in BOTH directions, which is the whole point

* **It fires**: 13 `NAKED_POSITION` events across the run, each naming the right instrument and
  the right gap — `NQ SEP26: position=1, ..., gap=1` and `MNQ SEP26: position=10, ..., gap=10`.
  Every one was a genuinely unprotected position (bare market orders, no brackets). The correct
  `FullName` in those lines **is** the `Instrument.ToString()` fix, observed in production.
* **It is silent when it should be**: **zero** `ORPHAN_STOP`, **zero** `FSM_DIVERGENCE`, and once
  the box went flat, **84 seconds — about 8 audit cycles — with nothing logged at all**.

That second half could not be checked before today and is the half that matters: **the shipped
version would have emitted all three findings, per instrument, every ten seconds, on a correctly
protected account.** A detector that fires on everything is indistinguishable from a working one
until you watch it stay quiet.

### ✅ `P3-34`'s copier shadow mode — validated, and it earned its keep immediately

```
COPY_BLOCKED_COPIER_SHADOW | copier mode is 'shadow', so nothing was submitted.
  WOULD have sent MNQ SEP26 Buy 10 to 'Sim-ORB', mirroring leader 'Sim101' Buy 1@30184.75
```

Nothing was submitted (confirmed against `nt_positions`), both relationships reported, and the
line named the instrument, action **and quantity**. That last detail paid for itself in the same
minute: it revealed the copy would be **10 MNQ** for 1 NQ — the `AutoSymbolConversion` ratio —
*before* anything was risked. `set_mode` over the bridge round-tripped `live → shadow → live`
with the relationships intact.

---

## 🆕 Two defects the live run found, and neither was reachable from a green suite

### `P1-97` — the bridge cannot express a short, so the copier misreads every MCP-placed one

`nt_place_order` maps `buy`/`sell` to `OrderAction.Buy`/`Sell` **unconditionally**
(`McpBridgeAddOn.cs:2423`), never `SellShort` or `BuyToCover`. The copier classifies from that
label (`leaderIsExiting = Sell || BuyToCover`). Measured, both halves:

| Placed | Position after | Copier read it as |
|---|---|---|
| `sell 1` from **flat** — a short ENTRY | `Short 1` | **`isExit=True`** → `COPY_SKIPPED_NO_POSITION_TO_EXIT` |
| `buy 1` from **short** — a COVER | flat | **`isExit=False`** → proceeded as an **entry** |

So through the bridge the copier **cannot open a short**, and **a cover is copied as a new
position in the opposite direction**. ⚠️ **It produced no wrong position in this run only by
accident**: `MNQ → NQ` conversion rounded 1 contract below the minimum and it died on
`COPY_SKIPPED_SUB_MINIMUM`. Nothing in the correctness path stopped it.

The bridge already does this correctly at `:2797` (the close path picks by `MarketPosition`); the
same three lines are missing at `:2423`. ⚠️ **Do not fix it by widening `leaderIsExiting`** — a
label is the wrong source for that question.

### `P2-98` — a partially filled copy measures only its first slice, and blames the wrong thing

A 10-lot copy filled `1 + 9`. `_pendingCopies.Remove(exec.Order)` runs on the **first** fill, so
every later slice misses:

```
COPIER_FILL_MEASURED     | latency=115.15 ms, slippage=2 ticks    <- the 1-lot slice
COPIER_FILL_NOT_MEASURED | Pending-copy lookup missed ...         <- the 9-lot slice
```

The measured slippage describes **one contract** while nine carried the rest of the risk. And
`FILL_NOT_MEASURED`'s text asserts *"OrderId is display-only and must never be used as the map
key"* — **false here**: the entry was consumed, not mis-keyed. A routine partial fill emits an
alarm pointing at a bug that does not exist, which is how an operator learns to ignore an event.

---

### What this session says about the method, again

**Three features passed 1311 tests, 23 mutation batteries and a clean NT8 compile, and the two
defects above were found in four minutes of driving the box.** Both live in the seam between two
components — a label the bridge writes and the copier reads; a map entry one path inserts and
another removes — and **neither component is wrong on its own**, which is the shape §5.16 already
named and the shape no diff review catches.

The other half is `P3-30`'s: **for a detector, the negative case is the expensive one to prove and
the only one that shows it works.** It took an authorised live run to watch the audit stay quiet.

### Next

1. **`P1-97`** — three lines in the bridge, and it is the one with a wrong-direction order behind it.
2. **`P2-98`** — keep the pending entry until the order is terminal; `P?-66`'s sampling rule applies.
3. **`P2-27`** coverage for `ReconcileFollowerPosition`, still the last `KNOWN_DEAD` entry.

## 5.37 `P1-97` closed the same hour it was opened — the copier can open a short for the first time

Filed in §5.36 from a live run, fixed and re-validated on the box within the hour, market still open.

### The fix, and why it went in the bridge and not the copier

`nt_place_order` mapped `buy`/`sell` to `OrderAction.Buy`/`Sell` **unconditionally**, so it could
never emit `SellShort` or `BuyToCover`. NT8 nets the position correctly either way — **the order
always worked** — but the copier classifies exits from the label:

```csharp
bool leaderIsExiting = leadAction == OrderAction.Sell || leadAction == OrderAction.BuyToCover;
```

⚠️ **The tempting fix is the wrong one.** Widening `leaderIsExiting` treats the symptom: a label is
chosen by whoever submits the order, so it is the wrong source of truth for *"is this an exit?"*.
The durable version derives exit-ness from the **position delta**, which is a larger change and
belongs with `P3-31`/`P3-32`. What went in instead makes the label **true**, which is cheap, local,
and is already how `McpBridgeAddOn`'s own close path works — `pos.MarketPosition == Long ? Sell :
BuyToCover`, **370 lines away in the same file**.

`nt8-mcp-bridge/addons/BridgeOrderAction.cs`, on `BridgeAccountResolver`'s terms: strings in,
strings out, **no NT8 type named**, so the bridge suite *executes* it. **69 → 92 tests.** That is
now three files extracted on those terms (`BridgeAccountResolver`, `CopierEnforcementView`,
`BridgeOrderAction`) and the pattern is the cheapest available `P2-27` step — see `tests/README.md`.

### Live-validated, a full short round trip on two followers

```
20:31:55  SellShort  1@30177.75  isExit=False  -> SellShort 10 MNQ to Sim-ORB AND SimCopy2
                                                  both accounts genuinely Short 10
20:32:17  BuyToCover 1@30183.50  isExit=True   -> BuyToCover 10 to both, EVERY ACCOUNT FLAT
```

Compare the same two actions before the fix, from §5.36:

```
sell from FLAT  -> Sell  -> isExit=TRUE  -> COPY_SKIPPED_NO_POSITION_TO_EXIT   (never copied)
buy from SHORT  -> Buy   -> isExit=FALSE -> proceeded as an ENTRY              (opposite direction)
```

**The copier had never been able to open a short position before this commit.**

### `P2-98` got sharper on the same run, and the number is worse than filed

Four copies went out; **every one of them partial-filled into two slices** (10 = 8+2, 4+6, 2+8,
1+9). The log shows **4 `FILL_MEASURED` and 4 `FILL_NOT_MEASURED`** — exactly **half** the fills
measured, because `_pendingCopies.Remove` runs on the first slice.

So this is not an edge case: on this instrument at this size, partial fills were **universal**, and
the latency/slippage figures describe whichever slice happened to arrive first — here as little as
1 contract out of 10. `P?-66` was closed on "the numbers were right and unexposed"; these numbers
are **exposed and unrepresentative**, which is the harder failure to notice.

### What the two sessions of live testing say, in one line

**Every defect found today came from a seam, and the box found all of them in under ten minutes:**
a label the bridge writes and the copier reads (`P1-97`), a map entry one path inserts and another
removes (`P2-98`), a side read off a sign (`P0-96`), a key built with `ToString()` where everything
else uses `FullName` (`P3-30`). **No component was wrong on its own in any of the four**, which is
why 1311 tests, 23 mutation batteries and a clean NT8 compile all passed over them.

### Next

1. **`P2-98`** — keep the pending entry until the order is terminal and accumulate across slices.
   ⚠️ `P?-66`'s rule: a latency rejected by the sanity bound must not count as a sample.
2. **`P2-27`** coverage for `ReconcileFollowerPosition`, still the last `KNOWN_DEAD` entry.
3. **`P2-29`** / **`P3-33`**, and the 3 `P?-` UI write items.

---

## 5.38 `P2-98` closed — a measurement's grain is the COPY, and the box found a P1 while proving it

**Session 36, 2026-08-13/14. Core `v1.19.0` tagged, deployed, compiled and LIVE-VALIDATED.**
Suite **1311 → 1328 / 0**. Bridge **92 / 0**. **24** mutation batteries, **263 anchors / 0 broken**.

### What was wrong

A partial fill delivers several `Execution`s for the **same `Order` object**. `ObserveFollowerFill`
consumed the pending-copy entry on the **first** of them:

```csharp
pendingFound = _pendingCopies.TryGetValue(exec.Order, out pending);
if (pendingFound) _pendingCopies.Remove(exec.Order);      // <- on the FIRST fill
```

So every later slice missed the lookup. Two consequences, and the second is the one that costs
more over time:

1. **The metric described the smallest slice.** Live, `slippage=2 ticks` came from **1 contract of
   10** while the nine carrying the risk went unmeasured — and nothing about the line said so.
2. **`FILL_NOT_MEASURED` asserted a cause that was not the cause**: *"OrderId is display-only and
   must never be used as the map key."* That trap is real — `OrderReferenceComparer` exists because
   of it — but it explained **none** of the misses seen live. The same event also fires on **every**
   manual or strategy fill on an account that happens to be a follower, which is routine. An event
   that fires routinely while naming a defect that is not there teaches its reader to skip it, and
   then it cannot report the day the defect **is** there. `P3-30`'s audit false positives, in
   miniature.

### The fix, and the three decisions inside it

**The grain of a measurement moved from the SLICE to the COPY.** `PendingCopy` accumulates
`SliceCount` / `FilledQuantity` / `FollowerNotional`; the entry is removed when the order is
**done**; one sample, one latency reading and one quarantine decision per copy.

**1. The average is quantity-weighted.** `FollowerNotional / FilledQuantity` vs the leader fill.
An unweighted mean of the slices would be the same defect in a subtler form — a 1-lot counting for
as much as the 9 lots beside it — and it would have passed a test that only asserted "not the first
slice's figure". `mutate_p298.py` mutant 4 is that mutant.

**2. Completion needs BOTH signals, and neither alone is sound.**

| Signal alone | What it loses |
|---|---|
| accumulated quantity ≥ order quantity | a copy **cancelled or rejected after a partial fill**: its measurement is never reported and its entry sits until the bounded FIFO reaps it |
| terminal `OrderState` | **the ordinary case** — NT8 does not guarantee the state is already `Filled` when the last execution arrives, and the test stub leaves a submitted order in `Submitted` for good, so a state-only implementation passes review and measures **nothing** |

⚠️ The second row is the trap worth carrying: the stub's `Submit` sets `Submitted` and no test ever
advances it, so *"wait for the order to go terminal"* — which reads as the obviously correct rule —
would have taken the suite from 1328 to 1305 and been diagnosed as a broken test rather than a
broken rule. `mutate_p298.py` mutant 9 is exactly that, and it kills 23 tests.

**3. Latency is read ONCE, on the first slice, and the verdict is carried on the pending entry.**
Two reasons, and only the first is obvious:

* it is the **right measurement**. Time-to-first-fill is how long the copy took to **reach** the
  market; time-to-complete is how long the market took to fill ten lots, which is liquidity.
* it is what **enforces `P?-66`'s rule**. Re-deriving the reading at completion would let a
  **rejected** latency be replaced by a later slice's — a plausible figure manufactured out of the
  same disagreeing clocks that produced the rejected one. That mutant (6) keeps the whole fix and
  fails **one** test; it is the reason the accept/reject verdict is state and not a recomputation.

A new **`FILL_SLICE`** event covers the gap in between: a partial fill is neither a measurement nor
a miss and must not be mistakable for either.

### Evidence

**9 tests, and three of them were GREEN at baseline for the wrong reason** — the later slice missed
the lookup, so nothing could overwrite the first slice's reading. They are regression guards on the
new shape, not evidence of the old defect, and they are labelled as such. The six that were red are
the evidence. `mutation/mutate_p298.py`: **13 mutants, 0 survivors.**

⚠️ **One anchor elsewhere broke on this change** — `mutate_ui1.py`'s latency-sample mutant named
`latencyAccepted`/`latencyMs`, both of which now live on the pending copy. `check_anchors.py` caught
it (263 checked, 1 broken); re-anchored, same mutant, still killed. Second session running in which
that gate has caught a silently-dead battery.

### LIVE-VALIDATED, and it reproduced the defect exactly

On sim accounts with the operator's standing authorisation, `v1.19.0` live and compiling clean:

**(a) the miss message, on its commonest real cause** — a manual 1-lot on `Sim-ORB`, which is a
follower:

```
COPIER_FILL_NOT_MEASURED  No pending copy for order 'P298_MANUAL_ON_FOLLOWER'
  (OrderId e00eac..., state Filled); this fill is not measured. Expected whenever the order was
  not submitted by this engine -- a manual or strategy fill on an account that happens to be a
  follower. ...
```

**(b) a partial fill, on both followers.** A 100-lot MNQ leader order, auto-converted to 10 NQ per
follower, filled **2 + 8** on each:

```
COPIER_FILL_SLICE     Slice 1 of the copy on order 'COPIER_FOLLOW': 2 @ 30159.5 filled,
                      2 of 10 so far. Not measured yet -- the copy is reported once, when the
                      order is done.
COPIER_FILL_MEASURED  latency=119.11 ms, slippage=-2.2 ticks on 10 contract(s) across 2 slices.
```

Check the arithmetic against the tape: leader filled 30160.25; follower VWAP =
`(2×30159.5 + 8×30159.75)/10` = 30159.70; `(30159.70 − 30160.25)/0.25` = **−2.2 ticks**, negative
being **favourable**. **Under `v1.18.0` this exact fill would have reported `−3 ticks` from the
2-lot slice and raised `FILL_NOT_MEASURED` for the 8.** Zero `FILL_NOT_MEASURED` for the copies in
this run.

### ⚠️ And the run opened a P1 — `P1-99`

**Found by driving the box, not by review and not by the suite**, which was green throughout. The
leader's own 100-lot filled **5 + 95**, and the copier ran the **whole copy path per execution**:

```
COPIER_EXEC_SEEN                 MNQ SEP26 Buy 5@30160
COPIER_COPY_SKIPPED_SUB_MINIMUM  scaled quantity for NQ SEP26 on 'Sim-ORB' came out below 1
                                 contract from leader qty 5 (ratio 1, sizing QuantityRatio)
COPIER_EXEC_SEEN                 MNQ SEP26 Buy 95@30160.25
COPIER_COPY_SUBMITTED            NQ SEP26 Buy 10 submitted to 'Sim-ORB'
```

It came out right **by luck**: 95 MNQ scaled to 9.5 NQ and rounded up to 10, which is the whole
order's equivalent. **A 100-lot filling as 20 × 5 drops every slice** — leader long 100 MNQ,
follower **FLAT**, twenty routine `COPY_SKIPPED_SUB_MINIMUM` lines and no error anywhere. The
follower's size is a function of **how the leader's order happened to fill**, which is a property of
the book and not of the trade.

`P1-71`'s live validation already found the single-order version (1 MNQ at ratio 1.0 rounds below
one NQ contract). What is new is that **partial fills manufacture small leader quantities out of a
large order**, so the case is reachable from a trade nobody would call small. Plan entry `P1-99` has
the two candidate fixes; the accumulate-and-copy-the-delta one is the one to reach for, because a
carried fractional remainder is state with four ways to go wrong that a reader cannot see.

⚠️ **A test for it must feed MULTIPLE executions for one leader order.** Every existing copy-path
test sends a single execution for the full quantity — the same blind spot `P2-98` had on the
follower side, and the reason both defects survived a green suite. **That is the shared lesson of
this session and the last one**: the suite models an order as one fill, and reality does not.

### ⚠️ And CI had been RED for 10 pushes, because two batteries could not pass

**Found 2026-08-14 by running `gh run list` — after `P2-98` was already tagged, deployed and
live-validated.** Not by CI telling anyone: CI had been telling everyone, on every push since
`v1.17.0`, and the message never changed.

```
failure  docs: 5.38 -- P2-98 closed and live-validated ...
failure  fix(copier): P2-98 -- measure a COPY, not its first slice
failure  docs: section 0 bridge count 69 -> 92, stale by one commit
failure  docs: 5.37 -- P1-97 closed the same hour ...
failure  docs: 5.36 -- the live validation ...
failure  docs: re-derive the four documents ...
failure  docs: handover 5.35 -- P0-96 ...
failure  P0-96: a leader covering a SHORT sent the follower a Sell ...
failure  docs: handover 5.34 -- the copier mode's read surface ...
failure  v1.17.0: two defects the LIVE audit log found in P3-34 ...
```

**The cause is not a defect in the code and not a flaky runner.** `mutate_p330.py` and
`mutate_p096.py` each declare a mutant that is *expected* to survive, correctly and in prose,
with the reason no test can reach it — the lock-scope mutant, and the reconciler mutant inside
`#if !TESTING` that `check_no_dead_safety_machinery.py` records as `KNOWN_DEAD`. Both then ended
with the shared

```python
sys.exit(1 if survivors else 0)
```

which is right for the other 22 batteries and **impossible** for these two. They were **red by
design from the commit that added them**, and the step is early enough in the workflow that
`P3-34`, `P0-96` and `P2-98`'s own batteries **never ran at all** on any of those ten pushes.

**This is the repo's own recurring lesson, landing inside the gate.** *A gate nobody reads is a
comment* was written down after `check_version_matches_tag.py` ran red for 7 runs across three
sessions while the docs claimed green. This is worse than that one: a gate that ran red for a
*real* reason at least described something true. **A gate that cannot pass describes nothing**,
and a constant answer is one nobody re-reads — which is exactly the argument `P2-98` made about
`FILL_NOT_MEASURED` firing on every manual fill, and `P3-30` made about an audit that fired on a
correctly protected account. Three instances of one shape in two sessions: **an alarm that is
always on is off.**

**Fix**: `mutation/_battery.py`. A mutant declares its own expectation — a description beginning
`EXPECTED SURVIVOR:` must survive, everything else must die — so there is no second list to drift
(a second copy of a fact is a second thing to forget). It **fails in both directions**: an
unexpected survivor fails, *and* a declared survivor that has since been **KILLED** fails, because
that is good news which makes the declaration false, and a stale exemption is how an allowlist
rots into a blanket.

**And the class is mechanical**: `tools/check_expected_survivors.py`, wired into CI beside
`check_ci_runs_every_battery.py`, refuses a battery that declares an expected survivor and keeps
the plain exit **and** a battery that routes through the helper without declaring one. It was
watched failing in both directions before being trusted — the `P3-30` rule, applied to the gate
that enforces `P3-30`.

⚠️ **The process lesson is the cheap one and it was already written down**: `gh run list` takes
about five seconds and belongs at the **start** of a session, not after a deploy. It was skipped
here, and a claim that CI was running-and-would-be-reported was made over a workflow that had
been failing for ten pushes. `check-ci-before-trusting-docs` says exactly this; having the note
is not the same as running the command.

### Two process notes worth more than they look

**Killing a mutation battery mid-run leaves a MUTANT in the source tree.** The batteries restore the
original only on completion. A batch was stopped to free the tree for a deploy and left
`mutate_cm4.py`'s third mutant in `TradeCopierEngine.cs` — the suite went 1328 → 1326 and the two
failures named symbol conversion, nothing to do with what was being worked on. It was found because
the suite was re-run before committing; a `git diff` skim did **not** find it, because a
one-line insertion in a 200-line diff reads as part of the change. **Re-run the suite after
stopping a battery, and read the number.**

**The defect-ID count in the plan was stale by 2 the moment it was written.** The line reads
`# -> 95, re-run 2026-08-14 (session 35)` and the true figure was 97 before this session touched
anything, because `P1-97` and `P2-98` were filed after it. The file's own advice — *run the command,
do not trust the number written here* — arriving one revision late, again.

### Next

1. **`P1-99`** — the copier's sizing grain. It is the highest-consequence open item: silent position
   divergence, `P0-5`'s family, and it is reachable from an ordinary large order.
2. **`P2-27`** coverage for `ReconcileFollowerPosition`, still the last `KNOWN_DEAD` entry, inside
   `#if !TESTING`, and it **flattens a live follower position**.
3. **`P2-95`** (`FirmStartingBalance` is off by the account's lifetime profit), then `P2-93`,
   `P2-94`.
4. **`P2-29`** / **`P3-33`**, and the 3 `P?-` UI write items.

---

## 5.39 CI went from 1h56m to 12–20m, and the tests were never the reason it was slow

The operator asked why the tests take so long and whether they could be vectorised or
parallelised. The honest answer to the first half is that **they don't** — and measuring it
was worth more than the speed-up, because the shape of the number says what CI actually is.

### What the 1h56m was

Step timings from run `31768033709`, the first green one:

| | |
|---|---|
| Setup (checkout, dotnet, python) | 32s |
| All eight source gates + build + the 1328-test suite | **42s** |
| The 24 mutation batteries | **6880s** |

**99% of the wall clock was mutation, and none of it was the tests.** The suite runs in 20s
on the runner and 5.3s locally. The cost is structural and it is not removable: every one of
the **263 mutants rewrites a C# source file**, so it needs a real recompile. 263 mutants, plus
a baseline run and a restore run per battery, is **311 `dotnet build` + `dotnet run` cycles** at
~22s each. Nothing about that is wasteful; it is what mutation testing costs in a compiled
language. An in-process Roslyn compile would cut it to under a second a mutant and is the only
real alternative, at the price of rewriting all 24 batteries.

**"Vectorise" does not apply.** That is array arithmetic; this is process-bound compile-and-run.
The instinct is right for the consumer repo's parameter sweeps (ADR-022) and wrong here.

### Why it could not be parallelised locally, and why the matrix is not the same thing

Every battery **rewrites the same shared source files in place**. Two running side by side in
one working tree corrupt each other — which is not hypothetical, it is exactly how a killed
batch left a live `mutate_cm4` mutant in `TradeCopierEngine.cs` earlier the same day (§5.38).
Backgrounding two batteries would have manufactured that failure deliberately.

A **GitHub Actions matrix gives every battery its own checkout**, so the hazard does not need
managing — it does not exist. That is the difference worth remembering: the fix was not "add
locking", it was to put the concurrent things somewhere they cannot see each other.

The workflow is now two jobs:

* **`checks`** — the eight source gates, build, suite, and `check_anchors.py`. ~75s.
* **`mutation`** — a 24-entry matrix, one battery per job, `needs: checks`.

**Measured over the first two sharded runs: 15m36s (`31774605782`) and 11m48s
(`31775541688`), both 25/25 green. So `1h56m → 12–20m`, 6–10x.**

⚠️ **RE-MEASURED after session 38, and the earlier `~12–16m` was too narrow.** Eight green
sharded runs now span **11m48s to 19m31s**. Two batteries were added in that session
(`P1-100`, `P2-101`), taking the matrix from 25 jobs to 27 — and the free plan runs **20 at
once**, so the queue behind the first wave went from 5 to 7. The top of the range moved with
it, which is what you would expect and is not a regression to chase. **Quote 12–20m, and
re-measure whenever a battery is added.** The general point stands and is the one to keep:
a fan-out's wall clock is not `total / N`, and it is not stable either.

Quote the RANGE: the
four-minute spread between two identical workloads is runner availability, and a single
measurement reported as *the* figure is the same error as a one-round green in
[[mutation-testing-beats-review]] — it is the run you should trust least.

⚠️ **And it is slower than the arithmetic predicted** (setup + UI4's 553s ≈ 10 min), which is
worth recording because the sequential timings could not show either reason: every battery runs
**10–20% slower as one of 24 concurrent jobs** (UI4 553s → 618s), and **runner provisioning is
not free** — 24 Windows runners do not all start at once, and that is most of the gap. Total
compute went **UP**, 6957s → 8723s, because per-job setup is now paid 25 times. The repo is
PUBLIC so all of it is free, but *free* is not *costless*: on a private repo this trade would
have raised the bill by a quarter. The lesson is the ordinary one — **a fan-out's wall clock is
not `total / N`**, and the residual is where the interesting part is.

Three decisions inside it are the load-bearing ones:

* **`fail-fast: false`.** The default cancels every other battery the moment one fails, which
  would hide a survivor in battery 20 behind a survivor in battery 2 and turn a full mutation
  report into a one-at-a-time bisect across 24 pushes. Each battery is an independent question.
* **`needs: checks`.** A battery refuses to run against a red baseline (exit 2) rather than score
  every mutant KILLED on pre-existing failures. Twenty-four jobs discovering that separately
  would report one broken suite twenty-four times. One job says it once, and `check_anchors.py`
  stays there too so a broken anchor is reported before 24 runners spend ten minutes each.
* **Ordered longest-first.** The free plan runs 20 jobs at once and there are 24, so four queue.
  Starting the long ones first means the four that wait are the short ones, and they finish
  inside UI4's window instead of extending past it. The per-entry comments carry the measured
  seconds so the ordering can be re-derived rather than guessed at.

### ⚠️ The matrix silently weakened a gate, in this repo's own recurring shape

`check_ci_runs_every_battery.py` asked only whether the filename appeared **anywhere** in
`ci.yml`. That was honest while every battery had its own `run:` step. It is not honest under a
matrix, because **every matrix entry carries a long prose comment above it naming the battery** —
so a battery deleted from the matrix but left described in its comment would still have passed,
and the gate would have reported "all 24 wired" while running 23.

That is `a gate nobody reads is a comment` turned **inside out**: a comment being read as a gate.
It is the fourth instance of this family in three sessions (`P3-30`'s audit, `P2-98`'s
`FILL_NOT_MEASURED`, the two unpassable batteries, now this) and the pattern is stable enough to
state plainly: **when you change the SHAPE of a thing a gate inspects, the gate's evidence
changes even though its code did not.**

The check now strips comments first and requires the name in a form that actually runs
something (`battery: mutate_x.py`, or a `run:` line). It also fails on a **duplicate** entry — two
rows re-prove one thing and burn a concurrency slot, which on a 20-slot plan pushes a real
battery into the next wave. **Both failure modes were driven on purpose before it was trusted**,
per the workflow's own header rule: entry deleted with its comment left → FAIL; entry duplicated
→ FAIL; restored → OK.

### A latent trap closed on the way past

`_battery.finish` unpacked `(name, old, new)`. Six batteries mutate **two files** and hold
`(path, name, old, new)`. `check_expected_survivors.py` REQUIRES a battery declaring an
`EXPECTED SURVIVOR:` to route through `finish` — so the first four-tuple battery to declare one
would have hit a `ValueError`, with the gate forcing the call into the crash. `finish` now reads
the description from either shape and refuses an unrecognised one rather than guessing. Nine
cases driven across both shapes (declared/undeclared × survived/killed, broken anchor, bad shape).

### Not done, and deliberately

**Two `Thread.Sleep` calls are 3.25s of the suite's runtime** — `Thread.Sleep(1050)` at
`tests/RiskGuardAddOnTests.cs:8431` (a 1-second trade-debounce window) and `Thread.Sleep(2200)`
at `:19421` (`InFlightLedger(timeoutSeconds: 2)` then `PurgeExpired`). The suite runs 25 times
inside the longest battery, so they are ~90s of the ~553s critical path. Worth fixing, and the
speed is the *lesser* reason: **a time-dependent test that sleeps is flaky under load**, and
these now run on a shared runner alongside 23 others. The fix is an injectable clock on
`InFlightLedger` and on `AccountState`'s trade-debounce, not a shorter sleep — shortening the
wait without shortening the timeout is how a test stops testing the thing it was written for.
Filed rather than done; it is a ~16% trim on a path already 10x better.

### Next

Unchanged — **`P1-99`** is still the item, and this changed nothing about it. What it changed is
that the evidence for the fix now arrives in twelve minutes instead of two hours, which matters
for `P1-99` specifically: it is a **sizing-grain** defect on the leader side, the fix is likely to
touch the copy path every battery exercises, and a two-hour feedback loop is what makes a
developer verify one battery locally and trust the rest.

---

## 5.40 `P1-99` closed — the copier's sizing GRAIN, and a battery that caught the author

`v1.20.0`. Suite **1328 → 1355**, `mutation/mutate_p199.py` **9 mutants / 0 survivors**, 25 core
batteries, **272 anchors / 0 broken**.

### What it was

The copy path runs per EXECUTION and handed `CalculateFollowerQuantity` the **slice**. A leader
order is not its fills: 100 MNQ under a MNQ→NQ conversion is 10 NQ however the book delivers it.
Sized slice by slice it became a function of the **fill shape** — a property of the book, not of the
trade:

| fill shape | copied | |
|---|---|---|
| one fill of 100 | 10 | correct |
| 5 + 95 | 0 + 10 = 10 | **correct by luck** — the shape the live box produced |
| 10 × 10 | 10 × 1 = 10 | correct |
| 11 + 89 | 1 + 9 = 10 | correct |
| **20 × 5** | 20 × 0 = **0** | leader long 100, follower **FLAT** |

Twenty routine `COPY_SKIPPED_SUB_MINIMUM` lines and no error anywhere.

### The fix, and the four decisions inside it

The grain moved from the execution to the **order**. `LeaderOrderFillProgress`, keyed by the leader
`Order` object, carries the cumulative leader quantity and a per-`rel.Id` copied count; each slice
recomputes the target from the cumulative and copies the **delta**. Rounding cannot accumulate
because every slice re-derives the whole target rather than adding to it.

* **The clamp goes on the DELTA.** A new `preClampQty` out-param supplies the unclamped cumulative,
  so `MaxPositionSize` is applied once, to the increment. Clamping the cumulative and then
  subtracting the already-copied slices subtracts them twice.
* **Credit what was SENT, not the target**, or the clamp's shortfall is forgiven instead of
  re-offered.
* **Exits are NOT routed through it.** `P0-6`'s clamp already mirrors the follower's real position.
* **Release needs BOTH the terminal-state and the quantity signal** — `P2-98`'s lesson on the other
  side of the copier — with a documented limit: a cancel delivers no execution, so the state check
  only fires when the final fill arrives already terminal. A cancelled-then-silent order is released
  by the bounded FIFO, which is the backstop and not a second mechanism.

### ⚠️ The battery caught the AUTHOR, not just the code

The first run had **three survivors**, and the most useful one was **unkillable by construction**.
The mutant changed the position argument on the cumulative call from `0` to `currentFollowerPos` —
and it could not matter, because that call reads the **pre-clamp** out-param. What it exposed was a
wrong **comment**: mine said "position 0 on purpose", implying the argument selected a behaviour when
it selects nothing. The mutant was repointed at the real defect (taking the clamped RETURN value),
and the comment now says what is actually load-bearing.

**A surviving mutant does not always mean a missing test.** Three survivors, three different
meanings: one wrong comment, one real coverage gap (the first clamp test had capacity fitting
*exactly*, which made "credit the target" and "credit what was sent" the same number), and one thing
with **no observable at all** — a leaked accumulator changes no copy, so `LeaderOrderProgressCount`
had to exist before the assertion could. Writing that third test is what surfaced the
cancel-delivers-no-execution limit, which no one had noticed while writing the fix.

### ⚠️ Two operational notes

* **`mutation/check_anchors.py` reads the WORKING TREE**, so running it while a battery is mid-run
  reports false breakage. It said "2 broken" here purely because mutant 4 was applied at that moment;
  272/0 on a clean tree. Same family as *a killed battery leaves a mutant* — anchor checks belong
  **before or after** a battery, never during.
* **Piping a battery through `tail` masks its exit code.** `python mutation/mutate_p199.py | tail -25`
  reported exit 0 with three survivors on screen, because the pipeline's status is `tail`'s. CI runs
  them unpiped so the gate is intact, but do not read a piped run's exit code as a verdict.

### Next

1. **`P2-27`** coverage for `ReconcileFollowerPosition` — the last `KNOWN_DEAD` entry, inside
   `#if !TESTING`, and it **flattens a live follower position**. `mutate_p096`'s declared
   `EXPECTED SURVIVOR` is the first test to write when it becomes reachable.
2. **`P2-95`** (`FirmStartingBalance` off by the account's lifetime profit), then `P2-93`, `P2-94`.
3. **`P2-29`** / **`P3-33`**, and the 3 `P?-` UI write items.

---

## 5.41 `P1-99` live-validated, and driving the box opened two more — plus a duplicate file that had broken the whole NT8 assembly

### ⚠️ The compile was RED before anything of mine was deployed, and nothing said so

`nt_compile` returned **651 errors**. Every one was in `Strategies/`, **none in `AddOns/`** — the
cause was two byte-identical copies of `RiskManagerBase.cs` (same SHA256), one at
`bin/Custom/Strategies/` and one at `bin/Custom/Strategies/Vinay/`. `CS0101` on a duplicate class,
then 496 × `CS0229` ambiguity cascading off it.

`Strategies/Vinay/` is where `sync_nt8_strategies.py` writes, so the top-level one was a **stray
hand-placed copy** — exactly what `NT8_FILE_ORGANIZATION.md` forbids. Backed up to
`Documents/NinjaTrader 8/_stray_backup/` and removed; the compile went **651 → 0**.

Three things worth keeping:

* **A broken Custom assembly is invisible from the outside.** `nt_health` answered fine, 96 accounts,
  feed connected, heartbeat current — because NT8 keeps running the **last good assembly**. The box
  looked healthy while refusing to load anything new. The only symptom was that a deploy had no
  effect, which is indistinguishable from a deploy that worked.
* **Both repos verified clean throughout.** `sync_nt8.py --verify` → 8 files identical,
  `deploy.py --verify` → 12 files, 0 orphans. Deploy parity says the FILES match; it says nothing
  about whether the assembly they belong to compiles. Two different questions, and only one of them
  was being asked.
* **`sync_nt8_strategies.py --verify` reports `23 differ, 212 orphans`** on the strategies side. That
  is a separate, untouched workstream, and it is where the stray copy came from.

### `P1-99` on the box

Guard `shadow`/armed, copier `live`, two sim followers off `Sim101` at ratio 1 with
`AutoSymbolConversion` (MNQ→NQ, ×0.1), `MaxPositionSize` 10.

**Entry** — a 100-lot MNQ market order filled **1 + 99**:

```
COPIER_EXEC_SEEN   MNQ SEP26 Buy 1@30269   order='P199_LIVE_100LOT'
COPY_SKIPPED_SUB_MINIMUM  ... is still below 1 contract: leader order 'P199_LIVE_100LOT'
                          has filled 1 so far (this slice 1, slice 1) ...
COPIER_EXEC_SEEN   MNQ SEP26 Buy 99@30269.25
COPY_SUBMITTED     NQ SEP26 Buy 10 ... has filled 100 in 2 slice(s), copy now 10 of a 10 target.
```

Both followers ended at exactly **10**. ⚠️ **Be precise about what that proves**: 99 × 0.1 = 9.9
rounds to 10 on its own, so **this shape would also have been correct under `v1.19.0`**. It confirms
the new path is live and produces the right answer; it does **not** discriminate the fix. That is the
same luck that hid the defect originally (5 + 95) — sim market orders fill in one or two slices, and
the shapes that discriminate (5+5, 15+15) are not reachable on demand. The discrimination is the 11
unit tests and 9 killed mutants; the box confirms the code is running.

**Exit** — and this one *is* discriminating. The flatten filled **4 + 96**, and the follower closed
**1 + 9 = 10**, exactly its position. The exit lines end `(isExit=True).` with **no cumulative
suffix**, while the entry carried `has filled 100 in 2 slice(s)`. Two different code paths, both
correct, on the same box in the same minute — which is the `P1-99` asymmetry (mutant 4) demonstrated
live rather than argued.

### 🆕 Two defects the run opened, both in shadow mode

* **`P1-100`** — a **SHADOW-only lockout BLOCKS real orders**. Both `SHADOW_LOCKOUT` records say "no
  flatten executed", every action was correctly suppressed, and nothing was flattened — `P2-92`
  working. And every subsequent order was refused `Account Sim101 is locked out`, including a limit
  10,000 points from the market that could never fill, so it is the **account** that is gated, not the
  order. Fails closed, but shadow exists so the guard can be evaluated **without touching trading**,
  and an operator whose account freezes during evaluation turns the guard off. Same shape as `P1-90`:
  a second reader of state that `P2-92` fixed in one place.
* **`P2-101`** — a lockout in shadow retries its flatten **forever**, because the retry's exit
  condition is "position still open" and shadow never closes it. ~78 log lines in one minute across
  three accounts, and unbounded. **`An alarm that is always on is off`, fifth instance.** The general
  rule: *a retry whose exit condition is an action the current mode does not perform will never exit.*

Both were found by **driving the box and reading `interventions.jsonl`** — not by the suite, which was
green throughout, and not by review. That is now the fourth session running where the deployed system
produced defects no static gate did.

### Next

`P1-100` first — it is the one that makes an operator switch the guard off. Then `P2-101`, then
`P2-27` / `P2-95`.

---

## 5.42 The MCP surface was measured against the bridge, and the honest answers are the unreachable ones

Asked directly whether the MCP wrapper needs work for RiskGuard/copier. Measured rather than guessed:
the bridge exposes **67 routes**, the wrapper defines **52 `nt_` tools**, and **15 routes are
reachable from no tool**. Ten routes are risk-related; five have a tool and five do not.

| route | tool |
|---|---|
| `/api/riskguard/config` | `nt_riskguard_config` |
| `/api/riskguard/fsm-state` | `nt_riskguard_state` |
| `/api/copier/config` | `nt_copier_config` |
| `/api/prop/limits` | `nt_prop_limits` |
| `/api/compliance/report` | `nt_compliance_report` |
| `/api/riskguard/inventory` | **none** |
| `/api/copier/snapshot` | **none** |
| `/api/lockout` | **none** |
| `/api/riskguard/version` | **none** |
| `/api/riskguard/fsm-reset` | **none** |

Filed as **`P1-102`** (lockout) and **`P2-103`** (the read-only truth surfaces).

**The finding worth carrying is the shape of the gap, not its size.** The two missing read surfaces
are `BuildGuardSnapshot()` and `TradeCopierEngine.GetSnapshot()` — the per-rule inventory ("is this
rule *Enforcing*, and what limit is it holding me to") and the per-relationship conformance view
(orphan positions, quarantine reasons). Those are exactly what `UI1`, `UI3`, `UI4`, `UI5` and `UI6`
exist for — **five of the 25 mutation batteries**, and the set whose every mutant is deliberately
written to make the payload *more reassuring than the box*. `F-9` was a defect in the same surface.

So a large amount of machinery was built to make one answer truthful, and **the agent driving the
system cannot read that answer.** The honesty was bought and is not being spent. That is a different
class of gap from "a route lacks a wrapper": the missing tools are not the convenient ones, they are
the ones that would let an operator or an agent check the guard's claims against the guard's
behaviour, which is this project's entire recurring theme (`configured / evaluated / enforcing`).

It has a measured operational cost too. Answering "what is running and is it protecting anything"
this session required parsing `interventions.jsonl` by hand, reading `config.json` off disk, and a raw
`curl` with the token from `Documents/NinjaTrader 8/mcp_token.txt`. `nt_riskguard_state` returns the
FSM only; `nt_copier_config` returns configuration and session metrics, **not** conformance.

⚠️ **`P1-102` and `P1-100` are one job.** Shadow mode can freeze an account (`P1-100`) and no tool can
unfreeze it (`P1-102`). Separately each is a nuisance; together they are "the guard stopped my account
and I cannot start it again", which is the shape that gets a risk system switched off rather than
debugged.

⚠️ **Three traps for whoever writes these tools**, all previously paid for here:
`unlock` **removes protection**, so no `default:` on `account` (`P1-91`) and the `action` enum pinned
to the addon's own whitelist (`P1-72`, which REGRESSED by advertising two actions that both answered
`UNKNOWN_COPIER_ACTION`); and the test must verify the **enforcer**, not the report — the hand-run
unlock this session was confirmed by re-sending an unfillable limit order and watching it be accepted,
because `F-9`'s lesson is that what a rule reports can disagree with what it does, in either direction.

---

## 5.43 `P1-100` closed — one predicate, three readers, and the panic button that cancels its own flatten

**`P1-100` is CLOSED and live-validated (`v1.21.0`).** A SHADOW-only lockout blocked real orders.

**The reader was `IsAccountLocked`, and `CanTrade` was never wrong.** The bridge's `PlaceOrder`,
`PlaceOcoOrder` and `PlaceAtmOrder` all consult it, and so does `GET /api/lockout` — so the status an
operator reads came from the same place as the refusal. It returned `state.IsLockedOut` raw. `P2-92`
(authority) and `P2-94` (deadline) had each added a clause to `CanTrade`; **neither reached this
reader, because nothing compared the two answers.**

⚠️ **It was wrong in BOTH directions, and only one of them was filed:**

| | `CanTrade` | `IsAccountLocked` (before) |
|---|---|---|
| shadow-only rule breach | allows | **refuses** ← the filed defect |
| `LockAccount(a, 60)` — timed | refuses | **allows** ← found while fixing it |

The second row is `P2-94` verbatim at a second reader, nine days after `P2-94` was closed in
`CanTrade`. Fixing the observed defect alone would have left it. **The general move: when you find a
reader that disagrees with the enforcer, enumerate every clause the enforcer has learned and check
each one, rather than porting the clause you came for.**

**The fix is a predicate, not an edit.** `LockoutBinds(accountName[, state])` is the only place that
answers "does a lockout bind here", and all three readers call it — the third being the entry-cancel
block in `OnOrderUpdate`, which **nobody had counted**. A predicate with one caller is a convention;
a predicate with every caller is a guarantee.

Three things worth carrying:

* **The relaxation keys on the LOCKOUT's authority, never on the current mode.** Reading `_mode` here
  passes the headline case and makes a mode switch a lockout bypass — flip a live guard to `shadow`
  and every real lockout evaporates. That is `mutate_p292.py`'s "THE WRONG FIX" mutant, and it is the
  implementation anyone would reach for first.
* **The third reader's damage was a LOG LINE.** `P0-51` already withholds intervention cancels in
  shadow, so nothing was cancelled — but the block still wrote `ENTRY_CANCEL: Cancelled order N
  because account is locked out` into `interventions.jsonl`. Same family as `P2-101`: a claim about an
  action the current mode does not perform.
* ⚠️ **The whole suite — 1355 tests — stayed green through the fix.** Every test that touched this set
  `state.IsLockedOut = true` directly, the single combination where all three readers agree. The
  closing tests assert **both** readers at once, and
  `TheReportedGateAndTheEnforcedGateCannotDisagree` drives all **48** combinations of
  flag × deadline × authority × armed × bypass-listed asserting `CanTrade == !IsAccountLocked`. The
  instance tests would all pass against a fourth reader added tomorrow; that one states the invariant.

⚠️ **Extracting the predicate broke two of `mutate_p292.py`'s anchors** — they matched text inside
`CanTrade`. `check_anchors.py` caught it in the same commit, which is the third time that gate has
paid for itself. They were **repointed** at `LockoutBinds` rather than retired (the invariant did not
change, only its address) and are now strictly stronger, since one edit there regresses all three
readers at once. `mutate_p1100.py` deliberately does **not** duplicate them, and says so.

Suite **1424/0**. `mutate_p1100.py` **4/0** on the first run, `mutate_p292.py` **11/0** re-run against
the repointed anchors, **276 anchors / 0 broken**, all 8 gates green, 26 batteries wired.

### Live validation, and the blast radius was larger than the defect said

Deployed `v1.21.0` (core + bridge pin), `nt_compile` **0 errors**, `ARMED_ON_START` confirms the
hot-swap. On Sim101, guard armed in `shadow`, `MaxContractsPerAccount: 10`:

```
13:44:43  Buy 11 MNQ market -> filled 1 + 10 (a genuine two-slice order)
13:44:43  SHADOW_LOCKOUT  Rule MAX_SIZE_BREACH recorded a shadow-only lockout observation
13:45:22  Buy 1 MNQ Limit @ 20000  ->  {"status": "submitted"}      <- v1.20.0 REFUSED this exact call
```

Then the negative control, which matters more: `nt_emergency_flatten` engages a real (bridge-side)
lockout, and the same unfillable limit was **refused** — so the fix relaxed the shadow case and
nothing else. Both directions driven, on the box.

⚠️ **The funded account was being gated too.** `TAKEPROFITPRO524207503` — the 50K TPT PRO, holding a
real short 3 MES — carried a **persisted shadow-only lockout** and was retrying `LOCKOUT_CANCEL` every
5 seconds. Under `v1.20.0` the bridge would have refused **every order on that account**. `P1-100` was
filed off sim accounts and read as a sim-mode annoyance; it was gating a funded account the whole
time. **A defect found on sim is not a defect confined to sim.**

Incidentally: the 11-lot entry filled as **1 + 10**, and both followers ended at exactly 1 NQ
(11 MNQ ÷ 10 = 1.1 → 1). Under `v1.19.0`'s per-execution sizing the first slice would have been
dropped and the second would have copied 1, reaching the same total by luck — but it is the first
multi-slice order to run through `P1-99`'s accumulator in production, and it was right.

### ⚠️ `P0-104`: the panic kill-switch cancels its own flatten order, and locks you out of fixing it

Found in the cleanup, not the test. `nt_emergency_flatten` on Sim101 returned
`success: true, flattenedAccounts: 1, cancelledOrders: 2` and **left the account long 11**.

`EmergencyFlatten` cancels working orders (step 2), calls `acc.Flatten` (step 3), then runs **a second
cancel pass for "residual bracket/OCO orders"** (step 4) that enumerates `acc.Orders` and cancels
everything active — **including the `Close` order step 3 just submitted**, because `acc.Flatten` is
asynchronous and it never distinguishes its own order from a residual. The counts are the proof:
`firstPassCancelled: 1` was the resting limit, `residualCancelled: 1` was the flatten. Then step 5
engages the lockout, so `nt_place_order` **refuses the exit the operator would place by hand** —
measured, immediately after.

Ordered the way an operator meets it: **stops cancelled → flatten cancelled → account locked → success
reported.** Naked position, no protection, no way to exit through the tool, and nothing says so. That
is `P0`, and it is in `nt8-mcp-bridge`, which has no tests (`P2-27`). The order-set arithmetic —
"which orders did I submit during this call" — names no NT8 type, so the `BridgeAccountResolver`
pattern applies directly.

`P1-105` is the same disease with a smaller bite: `ClosePosition` sets `positionClosed = true` on the
line after `account.Flatten(...)` and returns a constant `status: "flattened"`. Measured returning
`positionClosed: true` having submitted **nothing** — no `ORDER_UPDATE` in `interventions.jsonl` either
side of the call, position still long 11.

⚠️ **Both are `flattened++` counting the CALL, not the outcome** — `P1-70`'s family, and the same shape
as `P2-98`'s latency verdict: a measurement recorded before the thing being measured has happened.
Neither method ever looks at the position again. **Four sessions running, the defects that matter have
come from driving the deployed box and reading `interventions.jsonl`**, with the suite green
throughout.

### What to do next, in order

1. **`P0-104`** — the panic button. It is the only `P0` open and it removes protection while claiming
   to add it.
2. **`P2-101`** — the shadow flatten retry. Now known to fire on the **funded** account too, and in a
   second flavour (`LOCKOUT_CANCEL`, not just `LOCKOUT_FLATTEN_RETRY`), ~12 lines/minute/account
   indefinitely. *An alarm that is always on is off*, and this one is burying the audit record that
   `P0-104` was found in.
3. **`P1-102`** — no MCP tool reads or clears a lockout. Every unlock this session was a raw `curl`.
4. **`P1-105`**, then `P2-103`, then `P2-95`.

⚠️ **`P1-100` is closed, so the composite risk `P1-102` was raised on is halved**: shadow mode can no
longer freeze an account. `P1-102` is now a workflow gap, not a trap — weigh it accordingly.

---

## 5.44 `P0-104` closed — the panic button, and what an extraction does NOT buy you

**`P0-104` is CLOSED and live-validated** (`nt8-mcp-bridge` `bf1f901`). `nt_emergency_flatten`'s
second cancel pass — the one "for residual bracket/OCO orders" — enumerated every active order and
cancelled all of it, **including the `Close` order `acc.Flatten` had submitted a moment earlier**.
`acc.Flatten` is asynchronous; the pass never tried to tell its own order from a residual.

Discriminating reading, same scenario before and after:

```
before:  firstPassCancelled 1, residualCancelled 1, flattenedAccounts 1, success true  -> STILL LONG 11
after:   firstPassCancelled 1, residualCancelled 0, flattenOrdersSubmitted 1,
         accountsStillOpen [], success true                                            -> FLAT
```

`residualCancelled` **1 → 0** is the whole defect.

The fix is two halves, and the second is the one that made it invisible:

* **`addons/BridgeFlattenPlan.cs`** — residual = *still active* **AND** *present before this call*.
  Generic over `T : class`, **reference** identity (NT8's `OrderId` is not stable — the core keys its
  copy progress with `OrderReferenceComparer` for the same reason — and both snapshots are taken
  inside one synchronous dispatcher invoke). Names no NT8 type, so the harness **executes** it. The
  fourth file to take `P2-27`'s cheap route.
* **The report stopped claiming an outcome.** `flattenRequestedAccounts` / `flattenOrdersSubmitted`
  say what was asked for and what reached the book. **`accountsStillOpen`** is read *after* the pass
  behind a bounded settle poll (10 × 150ms, exits on the first clean read), and `success` requires it
  empty. ⚠️ That poll is the **third** `Thread.Sleep` on this side — §5.39 lists the other two and the
  injectable clock they want.

### Three things from this one worth keeping

⚠️ **1. Extraction moves the untested boundary; it does not remove it.** `mutate_p0104.py`'s mutant 4
**survived the first run**: it filtered the *caller's* "before" snapshot by order state, which is this
defect in the opposite direction (a bracket leg inactive before the flatten and `Working` after it
reads as new and survives the cleanup the pass exists for). The extracted class cannot see how its
argument was built. **After extracting logic, ask what the caller still decides** — the source gate
now pins the unfiltered snapshot as well as the call.

⚠️ **2. The source gate caught its own author.** It asserts the old outcome-claiming field name is
absent from `McpBridgeAddOn.cs`, and the first draft of the *comment explaining the rename* used it.
A gate that greps cannot tell prose from code — the CI-matrix lesson (*a comment read as a gate*)
arriving from the other side, **second instance in two sessions**. There is now a warning beside the
comment saying so.

⚠️ **3. CI in `nt8-mcp-bridge` ran NEITHER mutation battery.** `check_ci_runs_every_battery.py` lives
in the core and only knows about the core's batteries, so `mutate_p190.py` had **never run on a push**
since it was written. Both are wired now, one step each so a failure names the battery. *A battery
nobody runs is a file* — the same family as the two batteries that were unpassable for 10 pushes
(§5.38). **The gate that enforces "every battery runs" is itself per-repo, and nothing enforces that
across repos.**

Harness **92 → 108/0**, `mutate_p0104.py` **5/0**, deploy parity green both repos, `nt_compile`
**0 errors**.

### What the fix deliberately leaves — `P1-106`

The lockout still lands on an account whose flatten failed, **and a lockout still refuses a
position-REDUCING order**. Those two together are what turned "the flatten failed" into "and you
cannot fix it": Sim101 long 11, locked, and a `Sell` was refused.

The guard already has this notion — `IsPositionReducingOrder` guards its entry-cancel block
(`P1-44`) precisely so a rate limit cannot strip protection — and the bridge does not. *A lockout must
stop you opening risk, never stop you closing it.* `PlaceOrder` already computes the current position
(`P1-97` resolves `SellShort`/`BuyToCover` from it), so the information is at the refusal site. Two
traps recorded in the entry: the quantity clamp is load-bearing (a Sell 20 against a long 11 is an
exit *and* a new short 9), and it must read the **position**, not the `OrderAction` label, because the
label is the caller's choice.

### Order from here

1. **`P2-101`** — the shadow flatten/cancel retry. Unbounded, on the **funded** account too, and it is
   burying the audit record that both of this session's live findings came out of.
2. **`P1-106`** — the lockout that traps you in a position.
3. **`P1-102`** (no MCP tool reads or clears a lockout), then `P1-105`, `P2-103`, `P2-95`.

---

## 5.45 `P2-101` closed — the alarm that could not stop, next to the one that could not start

**`P2-101` is CLOSED and live-validated** (`v1.22.0`). The lockout's flatten retry is bounded by an
attempt COUNT whose budget depends on the mode: **1** outside an acting mode, **6** in `live`.

⚠️ **The 1 is the fix, not a tuning value.** `ProcessAction` answers `SHADOW (SKIPPED)` for every
action outside `live`, so a second `[SHADOW] Would execute FlattenPosition` carries nothing the first
did not. Shadow's product is the observation and it is complete after one. Bounding the loop *without*
asking why it could not exit is `mutate_p2101.py`'s mutant 2 — "THE PARTIAL FIX" — which stops the
unbounded growth and still repeats the observation five more times than shadow needs.

⚠️ **And the alarm that should have caught it could not fire.** `LOCKOUT_STUCK` read
`UtcNow > LastLockoutFlattenAttempt.AddSeconds(30)` while the retry immediately above it set that
field to `UtcNow` every 5 seconds — **the interval it measured was reset by the loop it was
watching**. Thirteen rounds of retries, zero stuck lines. One alarm that could not stop and one that
could not start, in the same block, and the second is why nobody was told about the first. Both are
keyed on the attempt count now, from `LockoutPhaseAttemptBudget()`, so they cannot drift apart.

Live, guard armed in `shadow`, 11 MNQ against a limit of 10:

```
10:14:14  LOCKOUT_FLATTEN_RETRY  Flatten attempt 1 of 1 for Sim101 (position still open)
10:14:14  LOCKOUT_STUCK          GIVING UP after 1 attempt(s) ... This is SHADOW mode -- no flatten
                                 was ever sent, so the position was never going to close.
```

…then silence for as long as the position was held. Before: ~12 lines a minute per account, forever.

Suite **1436/0**. Battery **7 mutants, 6 killed, 1 declared EXPECTED SURVIVOR** (dropping the reset
in `ResetLockoutPhase` is unkillable by construction — every route back into a phase goes through
`EnterLockoutPhase`, which resets on entry). **283 anchors / 0 broken**, 27 batteries, 8 gates green.

⚠️ **Mutant 7 took two attempts to kill and the failure IS the defect restated.** The obvious
assertion — *no stuck warning after one of six attempts* — passed **under** the time-keyed mutant,
because on any sweep where the retry fires it refreshes the timestamp one line before the check reads
it. **No assertion about a sweep where the retry fired can catch a time-keyed alarm**, which is
precisely why the original never fired in production. The discriminator is the sweep that spends the
**last** attempt. The general form is worth keeping: *when a mutant restores a condition that is
unreachable in production, the test that kills it must reproduce the state that makes it unreachable
and show the fix escaping it.*

Also collapsed here: four sites cleared the lockout-phase state cluster with their own copies of the
reset. `AccountState.ResetLockoutPhase()` owns it now — adding a third field to a cluster with four
hand-written resets is exactly how `P1-100`'s three readers happened, one section ago.

### ⚠️ `P2-107`: the same family survived the fix, on a different path, within the hour

Found in the *validation run itself*, on the two follower accounts:
`PEAK_GIVEBACK_BREACH` re-emitted its flatten **7 times in ~20 seconds**. Same shape — an action
repeated while a condition persists, in a mode that cannot clear it — but a different mechanism: this
is **per-evaluation**, driven by account/position updates rather than a timer, so it has no spacing at
all and its rate is set by market data.

**That is the finding, not the instance.** `P2-101` was fixed inside `EvaluateLockoutPhase`, one of
several producers of repeated actions, and the second instance turned up on the first accounts anyone
looked at. **The deduplication belongs where actions LEAVE the guard, not inside each producer.**
`CoalesceActions` (`P1-19`) already sits on that path and merges within one batch; nothing suppresses
the identical batch arriving three seconds later. ⚠️ Whatever goes there must not suppress a **live**
re-attempt doing real work — `P2-101`'s budget of 6 exists because a broker can reject a flatten — so
the record has to clear when the condition resolves, not on a timer.

Sixth instance of *an alarm that is always on is off*.

### Order from here

1. **`P1-106`** — a lockout refuses the order that would CLOSE the position it is locking you out of.
   The guard has `IsPositionReducingOrder` for exactly this reason (`P1-44`, closed); the bridge
   does not.
2. **`P2-107`** — the outbound action de-duplication, done once for all producers.
3. **`P1-105`**, then **`P1-102`** (no MCP tool reads or clears a lockout — every unlock this
   session was a raw `curl`), then **`P2-103`**.

⚠️ **This list carried six CLOSED IDs until session 39** — `P2-95` (closed s34), `P2-93` (closed
s34), `P2-94` (closed s34), and all three `P?-` UI write items (closed in §5.13 / §5.21).
`tools/check_next_list_ids.py` reads this block now, so it cannot happen silently again.

## 5.46 Session 39 — the ordering list had been wrong for nine sessions, and nothing could tell

No defect was fixed here. What was fixed is the surface that decides which defect gets fixed
next, and the reason it is worth a section is that **every existing gate passed while it was
wrong**.

### What was wrong

The three live "what to do next" surfaces — §0's `Do next` row, §5.6's live block, and the newest
`Order from here` — had been carrying **six closed IDs**:

| ID | Closed | Still listed as work to do until |
|---|---|---|
| `P2-95` (`FirmStartingBalance`) | session 34 | session 39 |
| `P2-93` (`pure` / `override_with_friction`) | session 34 | session 39 |
| `P2-94` (timed manual lockout) | session 34 | session 39 |
| `P?-64`, `P?-65` (copier UI writes) | §5.21 | session 39 |
| `P?-66` (copier metrics reading) | §5.13 | session 39 |

`CLAUDE.md` in the consumer repo said *"Weigh `P2-95` first now"* for all nine of those sessions.

⚠️ **Nobody added them back, and that is the whole mechanism.** Each session wrote its ordering
block by copying the previous session's and striking the item it had just closed. So **an item
closed while it was NOT at the head of the list was never struck by anybody** — `P2-95`, `P2-93`
and `P2-94` were all closed in one session, in one commit, by a session whose ordering block was
about something else entirely. Closures propagate **forward** into the record and never
**backwards** into the ordering.

The cost is not cosmetic. The ordering block is the one thing a session reads before choosing what
to work on, so a stale entry spends a whole session's attention on work already done — and the
reader who spots one cannot tell which of the *remaining* entries are also wrong, which is the
expensive part. This session found it only by checking each ID against its plan entry instead of
trusting the list.

### Why no gate caught it

Because the plan could not answer the question. **Fourteen of its entries carried no status token
at all**, including the whole `P0-1`…`P0-8` block, closed since phase 1. A prose note two hundred
lines above them explained that their *absence* of a marker should not be read as "open" — which
is the inverse failure this repo keeps finding: *a gate nobody reads is a comment*, and here **a
comment was standing in for a gate**. Fifth instance.

⚠️ **And a substring check for `CLOSED` reads `P1-105` — an OPEN defect — as closed**, because its
title contains `positionClosed: true`. That is not hypothetical; it is how the first draft of this
audit lost it. Status is read from a **separated token position** now, never by scanning the line.

### `tools/check_next_list_ids.py`

Fails in **both** directions, so neither half can rot:

* every defect ID named in a live ordering block must be a plan entry whose status is **open**;
* every `### Pn-m.` heading must **carry** a status token — the half that had rotted.

Three design decisions worth keeping:

1. **It polices only the LIVE surfaces, not every ordering block in the file.** Each session record
   ends with its own, and those are history — they record the order that session chose, which is
   the reusable part. Rewriting them to match today's closures would falsify the record. A
   struck-through heading is history *by construction*, which matches §5.6's existing convention.
2. **A closed ID may be CITED** — `P1-106`'s entry names `P1-44` and `P1-97`, both closed, both the
   reason the fix is cheap. A citation is exempt when marked closed within 60 characters of itself.
   ⚠️ Deciding by *position* instead (first ID is the work, later ones are citations) was the other
   candidate, and it **fails on the exact drift this exists for**: `then P1-105, P2-103, P2-95`
   put all three mid-sentence. ⚠️ The window was 30 first, and 30 made me **rewrite honest prose to
   satisfy the gate** — that is how a check starts costing more than it returns.
3. **It refuses (exit 2) if it finds fewer than three live surfaces**, so renaming a marker cannot
   silently reduce what it inspects. That is `check_ci_runs_every_battery.py`'s lesson applied
   before the fact: *changing the SHAPE of what a gate inspects changes its evidence even though
   its code did not.*

**Watched failing on four deliberate breaks before being wired**: reintroducing `P2-95` into the
tail (exit 1), stripping one status token (exit 1), renaming every `Order from here` (exit 2), and
striking the live §5.6 block so nothing is current (exit 2). ⚠️ The *first* attempt at break 3
renamed only one of the two headings and the gate correctly still found the newest — **a break
that does not break anything proves nothing**, and it looked identical to a pass.

### §0 was half re-derived, which is worse than stale

Six rows sat at session-34 values — suite 1311, bridge 92, `v1.18.0` deployed, 25 tags, 108 IDs —
while the box ran `v1.22.0` and the suite stood at 1436. ⚠️ **Session 38 did return to §0 and
updated the Mutation row only.** So the table was *partially* maintained and read as current:
nothing distinguishes a fresh row from a stale one, and the timestamp at the top vouches for all of
them. **Re-derive the whole block or none of it.** Also collapsed: §5.0 carried **two** tables
counting the same entries and disagreeing (90/93/14/79 against 98+3+7).

### Measured this session

Core suite **1436/0**, bridge harness **108/0**, MCP wrapper **43/0**, **283 anchors / 0 broken**,
29 batteries, `nt_compile` **0 errors** on net48, guard live at **`1.22.0`** (`shadow`, armed,
guarding), both `--verify`s in sync (8 files / 13 files, 0 orphans), bridge pin range **empty**,
CI green in both repos. Defect total re-derived: **117 IDs — 103 closed, 14 open**.

### Order from here

1. **`P2-107`** — the outbound action de-duplication, done once for all producers, at
   `CoalesceActions` rather than inside each one.
2. **`P1-105`**, then **`P1-102`** (which grew in section 5.47 — nothing can IMPOSE a lockout
   either), then **`P2-103`**.

✅ `P1-106` was closed in this same session — see section 5.47.

## 5.47 `P1-106` closed — a lockout must stop you OPENING risk, never CLOSING it

**`P1-106` is CLOSED.** All three bridge order paths were the same three lines:

```csharp
if (IsAccountLocked(account.Name))
    return new { error = "Order blocked: Account " + name + " is locked out." };
```

which does not care what the order **does**. Measured during `P0-104`'s reproduction: Sim101 long
11, locked by the panic switch, and a `Sell` refused. **The lockout trapped the operator in the
exact risk it exists to limit** — the half of `P0-104` its fix deliberately left, and what turned
"the flatten failed" into "and you cannot fix it by hand".

The guard has had this notion since `P1-44`: its entry-cancel block is gated by
`IsPositionReducingOrder`, precisely so a rate limit can never cancel a protective order and leave
a position naked. The bridge had it nowhere.

### The fix

`addons/BridgeLockoutGate.cs` — one predicate, three callers, `P1-100`'s shape deliberately. It
names no NT8 type, so `tests/BridgeTests.csproj` **executes** it (`P2-27`'s pattern, the fifth
file to use it).

* `PlaceOrder` admits an order that **strictly reduces**: opposite side, quantity ≤ |position|.
  ⚠️ **The lockout test had to MOVE DOWN the method**, past the point where the instrument and the
  position in it are known. It used to run before the symbol was even read — it could not have
  told an entry from an exit even if it had wanted to. The cost is one thing worth naming: an
  unparseable request on a locked account now reports the parse error rather than the lockout.
* ⚠️ **The quantity clamp is the load-bearing half.** A `Sell 20` against a long 11 is an exit
  *and* a new short 9, which NT8 nets into one order the operator reads as an "exit". Same
  arithmetic as `P0-6`'s exit clamp and `P1-99`'s delta clamp: **the clamp goes on what is NEW.**
  The refusal names the 9 *and* the quantity that would work — a refusal the operator cannot act
  on is one they retry blind.
* ⚠️ **It reads the POSITION, never the `OrderAction` label.** The direction passed in is the
  *request's* `buy`/`sell`. Feeding `resolvedAction` back in would re-read a label the caller
  chose — `P1-97` reintroduced one statement after the code that fixed it — so a source assertion
  forbids exactly that.
* ⚠️ **`PlaceOcoOrder` and `PlaceAtmOrder` stay refused, and that is a decision, not an
  omission.** Both submit an entry plus stop and target legs, and the legs take the **opposite**
  side — so an OCO whose entry flattens a long leaves a resting stop and target that **OPEN a
  short** once either triggers. A bracket cannot be admitted on the strength of its entry. Both
  refusals now name a path that works (a plain order, or `nt_close_position`, which is ungated).

### Evidence, and which half is which

Bridge harness **133/0** (9 new tests). `mutation/mutate_p1106.py`: **8 mutants, 8 killed**.
`nt_compile` **0 errors** on net48.

Live on Sim101, locked by the panic switch and flat, **both** directions were refused:

```
buy 1  -> Order blocked: Account Sim101 is locked out and the account is FLAT in this
          instrument, so this order can only open risk.
sell 1 -> (the same)
```

That text exists only in the new class, so **the wiring is proven in the running assembly**, not
merely on disk. `nt_emergency_flatten` also reported `residualCancelled: 0` again — `P0-104`
holding.

⚠️ **The ADMIT branch could not be driven live, and the reason is a finding.** It needs a lockout
imposed on an account that *already holds a position*, and **nothing on the box can do that**:

* `/api/lockout` implements only `unlock`/`reset`/`clear`. **Anything else — including
  `action: "lock"` — falls through to a status read and returns `success: true,
  isLockedOut: false`**, which reads as "I locked it and it isn't locked".
* the only code path that imposes the binding bridge lockout is `EmergencyFlatten`, which
  flattens the position *before* it locks;
* a guard-side lockout does not help, because the box runs `shadow` and `LockoutBinds` correctly
  returns false there (`P1-100`).

**That enlarges `P1-102`**, which was filed as "no MCP tool reads or clears a lockout". It cannot
**impose** one either, and the one verb it does advertise silently does nothing. So the admit
branch rests on the executed predicate, the battery (mutant 1 restores the shipped defect verbatim
and dies against the exit tests), and the source gate on the three call sites. **Say which half
was measured — do not let one green stand for both.**

### ⚠️ The battery found a gap the review did not

Mutant 7 replaced `Math.Abs(positionQuantity)` with the raw value and **survived**, because every
test passed a positive quantity. It is tempting to call that unkillable by construction — NT8's
`Position.Quantity` really is absolute — and that would have been wrong. With a signed `-11`,
`11 > -11` refuses a legitimate cover: **`P1-106` restored, on the short side only**, which is
precisely how `P0-96` hid behind 1311 green tests. The killing test passes a signed quantity
deliberately, and the mutant is now dead rather than declared.

### Also: the bridge's battery gate, ported

Session 38 found that this repo's CI **ran neither of its batteries** and fixed it by adding two
steps by hand — the instance, not the class. A third battery could arrive tomorrow and sit unwired
for just as long, which is exactly what the first two did. `tools/check_ci_runs_every_battery.py`
is ported here now (it is per-repo by construction, so the core's copy could never have seen this
side), strips comments before matching, and was **watched failing on a battery described in a
comment but not run**.

### Order from here

1. **`P2-107`** — the outbound action de-duplication, at `CoalesceActions`, once for all
   producers.
2. **`P1-105`**, then **`P1-102`** (now larger than filed, above), then **`P2-103`**.

---

## 5.48 `P2-107` closed — de-duplicate where actions LEAVE the guard, and two gates that proved nothing

**Session 40, 2026-08-14.** Suite **1469/0** (was 1436). Battery **18/18**, no survivors. Anchors
**283 → 301** — and that increase is a finding, not a total.

### What it was

`PEAK_GIVEBACK_BREACH` re-emitted its flatten on **every evaluation** — 7 in ~20 seconds on two
follower accounts, measured in `P2-101`'s own validation run, within the hour of that fix landing.
Same family as `P2-101`, different mechanism: that one was a timer retry whose exit condition
`shadow` could never satisfy; this one is per-evaluation, so it has **no spacing at all** and its
rate is set by market data.

**Two instances in one hour is the finding, not the instance.** `P2-101` was fixed inside
`EvaluateLockoutPhase`, one of several producers; the second turned up on the first accounts
anyone looked at. A bound written into each producer is a bound the sixth producer will not have.

### The fix

`addons/GuardActionDeduplicator.cs` — names no NT8 type, so the harness **executes** it (the
`P2-27` pattern, now the sixth such file across the two repos) — behind one new `DispatchActions`
on `RiskGuardAddOn`. All five emission sites call it: `PositionUpdate`, `AggregateSizing`,
`AccountItemUpdate`, `OrderUpdate`, `SafetySweep`, `GraceExpiry`. `CoalesceActions` (`P1-19`) now
has **exactly one caller**, inside the dispatcher.

⚠️ **A side effect worth knowing about**: the `OrderUpdate` site was calling `ProcessAction` in a
**bare loop** — the only one of the five that never called `CoalesceActions` at all, so `P1-19`'s
within-batch merge had never applied on the order-update path. Routing it through the dispatcher
fixed that for free. It is recorded because a fix that arrives silently is one nobody can later
find the reason for.

Four decisions inside it:

1. **The record clears when the CONDITION resolves, never on a timer.** A time-based expiry
   re-admits while the condition is still true — the defect on a slower clock. The observable is
   that the producer evaluated the account and did *not* ask, so `DispatchActions` takes the
   accounts the producer **evaluated**, including those it decided needed nothing.
2. **The budget is re-read from the mode every call**: `1` observing, `6` acting — the same numbers
   as `P2-101` so they cannot drift in a reader's head. **The 1 is the fix, not a tuning value.**
   Not baking it into the record means arming to `live` re-admits a key `shadow` had exhausted,
   which is what an operator switching to live wants.
3. **The scope carries the PRODUCER as well as the account.** `AccountItemUpdate` does not evaluate
   the lockout rules, so its batches legitimately lack their keys; if any producer's silence could
   clear any record, nearly every batch would clear nearly everything and the mechanism would do
   nothing **while passing every test that drives a single producer**. This is also why
   `EvaluateAggregateSizing` was split out of the `PositionUpdate` batch — it iterates every
   subscribed account while the rules beside it looked at one.
4. **The operator's panic buttons deliberately bypass it.** A second press flattens twice. A safety
   control that ignores it because it recognised the first is worse than the defect being closed.

### ⚠️ The battery went 13/13 on its first run, and that was the wrong place to stop

Five more mutants, aimed at what the first thirteen never touched, **all survived**:

* the key dropping its **rule**, so a second rule's breach is swallowed by the first;
* the key dropping its **action type**, so a cancel is counted as a flatten;
* the **session reset** no longer clearing, so a suppression crosses the day boundary;
* the account-wide producers declaring an **empty scope** — which fails *open*, so everything is
  still dispatched and nothing else in the suite notices;
* and the sharpest: **the `AccountItemUpdate` handler reverted to its old bare loop.** The
  de-duplicator, the dispatcher and eleven tests of both were present and correct, and *the one
  path the defect was measured on* walked around all of it. That is `P3-30`'s shape, and only a
  test that drives the **event** rather than the helper can see it —
  `TestP2107_TheRealAccountItemUpdateHandlerGoesThroughTheDispatcher` exists for exactly that, and
  asserts the rule fired **at all** before asserting it fired once, because otherwise it would pass
  on a guard that does nothing.

### ⚠️ Two of this repo's own gates were caught proving nothing, by one habit

Both are **detection by substring over a region nobody bounded**:

* `mutation/check_anchors.py` recognised only `(PATH, label, old, new)` 4-tuples and **silently
  `continue`d** on anything else. This battery put the file constant second, so **all 18 anchors
  were skipped** and it printed `ok`. It now locates the `ast.Name` wherever it sits, and an entry
  it cannot read is a **failure**, not a skip — a check whose product is a count of what it
  verified cannot skip what it cannot parse. Watched failing both ways (a broken anchor; an
  unparseable entry), and restored clean.
* `tools/check_expected_survivors.py` searched for `EXPECTED SURVIVOR:` in
  `src.split('MUTANTS = [', 1)[-1]` — **not the list, but everything after it opens**. A closing
  comment telling the next reader *how to declare one* made the gate report a declaration the
  battery does not make, then demand the exit form that would have been wrong. It parses the
  `MUTANTS` list with `ast` now and **refuses** a battery it cannot read. Watched failing on a real
  declaration placed inside the list.

Same family as `check_next_list_ids.py` reading `positionClosed: true` in a title as a CLOSED
status, and the CI matrix comment that would have counted a deleted battery as wired. **Three
gates, one habit — and the newest gate in the repo was one of them.** When adding a check, state
the *region* it inspects, not just the string it looks for.

⚠️ `tools/check_next_list_ids.py` (session 39) **earned its keep here**: it named all three
ordering surfaces the moment `P2-107`'s plan entry flipped to CLOSED, before anything was
committed.

### Live validation, and the two things it changed

Sim101, guard armed in `shadow` at `v1.23.0`, `nt_compile` `errorCount: 0`. `DailyLossLimit` was
lowered to force the breach, then the config restored **byte-for-byte** (md5 checked against a
backup taken first) and the account flattened. `DAILY_LOSS_BREACH` — no producer-local latch, so
true on every PnL tick — produced **exactly one `SHADOW_ACTION` and one `ACTION_SUPPRESSED` per
episode**, the latter naming the producer, budget and attempt in text that exists only in the new
class. The historical file holds **378** such lines under the old behaviour.

⚠️ **The exemplar the defect was FILED on was not an instance of it.** `PEAK_GIVEBACK_BREACH` has
had its own latch since `v1.0.0` (`b125132`, 2026-08-06) — it re-fires only on a **deeper** giveback
— so the 7-in-20s capture was seven genuinely worsening levels on a fast move, and `P2-107`
correctly does not suppress them (re-measured live: three in four seconds, zero suppressions). The
class is real and large; the exemplar was not a member of it. **Check whether the instance you are
generalising from has its own bound**, and re-drive it live — the suite cannot tell you that the
rule you are citing already solved its own half.

🆕 **`P2-108` was found in this validation run**: `NAKED_POSITION` repeating every 10s (12 in 120s,
180 in the log, 142 today) while `shadow` cannot attach the stop it is complaining about. It is the
same family on a path `DispatchActions` cannot reach, because it is a `LogEvent` with no action
behind it. **Seventh** instance of *an alarm that is always on is off*, and the **third session
running** in which the validation of one fix produced the next defect.

### ⚠️ `git push origin main` from another branch's checkout is a silent no-op that prints success

`nt8-mcp-bridge` was checked out on a **different branch** (a parallel session's feature branch)
when the `v1.23.0` pin was committed. The commit therefore landed on **that** branch, and
`git push -q origin main` pushed the local `main` ref — which was unchanged — so it **succeeded and
printed nothing**. `origin/main` still pinned `v1.22.0`, and the pin commit sat unpushed on someone
else's branch, where it would have been folded into their PR.

The **deploy was fine** — the feature branch touched no `addons/` or `tools/` file, verified with
`git diff --name-only origin/main..<branch> -- addons/ tools/` returning empty, and
`deploy.py --verify` reads **ALL IN SYNC (15 files, 0 orphans)** from `main`. Only the bookkeeping
was wrong, and a stale pin is exactly what makes `deploy.py` **revert a live core** later.

**Caught by `gh run list`**: the pin commit had no CI run, while runs existed for a branch nobody
in this session had touched. Two rules from it:

* **Check the branch before committing in a repo you did not start the session in.** `git status -sb`
  costs nothing; "ahead 1" on an unexpected branch is the whole signal.
* **`git push origin main` does not mean "push what I just committed."** It pushes the *ref named
  `main`*, wherever HEAD happens to be. Verify with `git log --oneline -1 origin/main`, not with the
  push's exit code.

### The MCP wrapper moved into `nt8-mcp-bridge`, and what that fixes

**2026-08-14, operator-driven, in parallel with `P2-107`.** The Node MCP wrapper — 52 tools, 43
tests — was its own repo (`vinay-veerappa/ninjatrader-mcp`), wired into `tvDownloadOHLC` as a
submodule at `mcp/ninjatrader-mcp`. It is now **`nt8-mcp-bridge/mcp/`**, history preserved, and the
submodule is gone from `tvDownloadOHLC`.

**Why it belongs there and not on its own**: the wrapper and the addon are two halves of ONE
contract — the wrapper advertises tool schemas, the addon decides what it accepts — and **a contract
with its two sides in two repos cannot be pinned in one commit**. Every defect ever found in the
wrapper is contract drift: `P1-91` (schema defaults the addon never reads), `P1-72` (advertised
`quarantine`/`unquarantine`, which the addon refuses, while `isQuarantined`, which works, was
absent — filed, fixed, then REGRESSED), and the still-open `F-16`.

Two things it actually bought, both measurable:

* **The `P1-72` pin is now a gate rather than a transcription.** `mcp/tests/tool-schema.test.js`
  used to hold a hand-typed `ADDON_ACCEPTS` set under a comment naming where it came from — it
  caught the wrapper drifting from a list that was true when someone typed it, and could **not** see
  the addon change. It now reads `addons/McpBridgeAddOn.cs` and extracts the real `knownActions`.
  That is only possible with both sides in one checkout.
* **The wrapper's 43 tests now run on every push.** That repo had **no CI at all**, in the repo where
  `P1-91` and `P1-72` (twice) were found.

⚠️ **Paths in this plan predating the move are historical and were left alone; the `**Where**` lines
of every entry that is still OPEN were repointed** at `nt8-mcp-bridge/mcp/…`. An instruction for
future work has to be current; a record of where a fix landed in July does not.

⚠️ **The PR branch pinned the PREVIOUS core.** `fold-mcp-wrapper` was cut from `main` before
`v1.23.0`, so it pinned `v1.22.0` — a core with no `GuardActionDeduplicator.cs` — and its CI was
proving the wrapper against a core that is not deployed. Merging would **not** have reverted the pin
(the branch never modified the gitlink, so a three-way merge keeps `main`'s side), and
`deploy.py`'s `check_vendor_not_stale` reads the **working** submodule and refuses at exit 2 when
`addons/` differs in the range — but a branch whose CI is green against the wrong core is a green
that means less than it looks. `main` was merged into it and the pin is `v1.23.0` on both.

### Order from here

1. ✅ ~~**`P1-105`**~~ — **closed in session 41, see §5.49.**
2. **`P1-102`** (now larger than filed — see §5.47: nothing on the box can *impose* a lockout on an
   account holding a position, and `action: "lock"` silently answers `isLockedOut: false`).
3. **`P2-103`**, then **`P2-108`**, then **`P3-110`** -- ⚠️ **narrowed to almost nothing by a live drive in the last
   fifteen minutes of the same session**: a `StopMarket` and a `StopLimit` both rest in `Accepted`,
   which the panic path already cancels, so the hazard as filed does not exist. What remains is an
   ATM/strategy-managed stop and identifying what actually produces `TriggerPending`. **Do not add
   the state on the strength of the source reading** -- that reading is what produced the entry, and
   it was wrong -- then the architectural **`P2-29`** / **`P3-33`**.

Weigh by §5.6's consequence rule, not by band letter.

---

## 5.49 `P1-105` closed — the OTHER flatten path, and two source gates that passed under the mutant

**Session 41, 2026-08-14.** `nt_close_position` answered
`{"status": "flattened", "positionClosed": true}` with the position **still open**. Closed,
deployed, live-validated. Suite **133 → 190** (26 → **38** tests), battery **18/18**, `nt_compile`
`errorCount: 0`.

### The shape is the one to carry: a second reader that was never told

`McpBridgeAddOn.cs` has exactly **two** `.Flatten(` call sites. `EmergencyFlatten` learned all of
this as `P0-104` — an asynchronous `Flatten` means the line after it proves nothing — and got
`BridgeFlattenPlan` plus a bounded settle poll. `ClosePosition` was never told.

That is the **third** time this project has met it: `P1-100` (`CanTrade` learned two clauses over two
sessions and neither reached `IsAccountLocked`), `P2-98`/`P1-99` (each side of the copier discovered
separately that an order is not one fill), and now this. **When one path learns something, enumerate
the other paths that answer the same question — the fix is cheap and finding it later is not.**

### What actually changed

`positionClosed` used to be assigned unconditionally on the line after `account.Flatten(...)`, and
`status` was the **constant string** `"flattened"` in the return expression. Neither was a claim
about anything. Now:

* `flattenOrdersSubmitted` reuses **`BridgeFlattenPlan.SubmittedByThisCall`** — the order-set
  arithmetic `P0-104` already validated, rather than a second dialect for the same question.
* `positionsStillOpen` comes from a bounded settle poll (10 x 150ms) that **stops as soon as the
  scope is flat**, so the healthy path pays one iteration and no sleep. ⚠️ **Fourth `Thread.Sleep`
  site in this file** — §5.39 lists the other three and the injectable-clock work they want.
* **One scope predicate, both passes.** `BridgeClosePlan` (new, names no NT8 type, so the tests
  EXECUTE it) answers "which positions is this request about?" for the acting pass *and* the
  observing pass. If they disagreed the report would be true about a set the caller never named —
  `F-9` restated. The source gate **counts** the call sites (>=3 symbol, >=2 account); asserting one
  is present would pass while the other pass kept a hand-rolled filter.
* **`P1-90` at a seventh site.** This handler *filtered* by account name instead of resolving one, so
  the six-site sweep never reached it. `account: "Sim1O1"` matched nothing and was reported as a
  successful close; it now refuses, naming the 96 available accounts.
* **Root equality replaces `StartsWith`**: `symbol: "M"` was a request to close MNQ, MES, MCL and MGC
  together. ⚠️ The **expiry is still not compared**, and the live run vindicated that: NT8 reports the
  position as **`MNQ SEP26`** while the caller passes **`MNQ 09-26`**. An exact full-name match would
  have silently matched nothing — this defect again, in a new place. *Do not tighten a match against
  a string format you have not measured.*
* **Cancels credit what was SENT** (`P1-99`'s rule at a second site): the old loop cancelled the whole
  list in one `try/catch {}` and added `toCancel.Count` regardless.

### Live validation — and which half is NOT validated

Five drives on Sim101 (20:05-20:10Z), each returning text that exists only in the new class: a flat
account → `nothing_to_close`; a typo'd account → **refused**; `symbol: "M"` against an open MNQ
position → `positionsMatched: 0` (**the old filter would have closed it**); a real long 2 →
`matched 1, flattenOrdersSubmitted 1, positionsStillOpen [], closed true`; a long 3 plus a resting
limit → `cancelled 1` *and* `flattenOrdersSubmitted 1`, the cancelled resting order correctly not
confused with the flatten's own.

⚠️ **`close_not_submitted` — the status the original defect would now produce — could not be driven
on the box.** The mechanism of the original `Flatten` no-op was never established and cannot be
reproduced on demand. That path rests on the executed predicate and its battery. **Say which half was
measured.**

### The battery caught what review did not, and two of the three were GATES

**15/18 on the first run**, all three survivors real:

1. Neutering `if (closeResolution.Refused)` to `if (false)` left the `ResolveOrRefuse` call in place —
   and the gate asserting the resolver is **called** still passed. ⚠️ **A gate that a value is
   COMPUTED is not a gate that it is USED.** That is `P2-24`'s class ("dead safety machinery is
   invisible") arriving at the gates themselves, and **every "is X called" assertion in
   `BridgeSourceTests.cs` deserves the same question.**
2. Replacing the settle poll's exit condition with a bare `break` leaves one immediate read, so
   **every healthy close would report `close_submitted_not_confirmed`** — *an alarm that is always on
   is off*, the **eighth** instance here.
3. Dropping the empty-root guard leaves `string.Equals("", "")` — **two unknowns read as a match**.

### A test disagreed with the class in the same commit, and the test won

`WantsEverySymbol` was first written as `IsNullOrWhiteSpace → true`, reasoning that the handler
defaults an absent symbol anyway so the two could not drift. **The handler defaults on
`IsNullOrEmpty`.** So `{"symbol": "   "}` — a template that interpolated an empty variable — would
have reached the filter as three spaces and been read as a request to **close every position on the
account**. The wildcard is now one exact token, and turning absence into `"ALL"` happens in exactly
one greppable line. **The two failure directions are not symmetric: matching nothing wastes a call,
matching everything is an unrequested liquidation.**

### Two gates in `nt8-mcp-bridge` were fixed on the way past

* **`tools/check_bridge_parses.py` checked 2 of 6 addon files** under a comment reading "every
  bridge-owned addon source". `BridgeFlattenPlan`, `BridgeLockoutGate`, `BridgeOrderAction` and
  `CopierEnforcementView` had all been added since, each time leaving the comment's claim less true.
  It now globs `addons/*.cs` — **the same glob `deploy.py` uses to decide what SHIPS**, so the
  checked set and the shipped set are one set by construction. 2 → **7** files; watched failing
  (exit 1) on a deliberate break of a newly-covered file, then passing again. **Fifth instance of
  *state the region a gate inspects*, and the cheapest form of it: the region was a literal, and the
  literal aged.**
* **All three bridge batteries died decoding their own subprocess output.** `capture_output=True,
  text=True` decodes as cp1252 on Windows, so **one non-ASCII character in a test's message** raised
  `UnicodeDecodeError` on a reader *thread*, `res.stdout` came back `None`, and the battery crashed
  before its first mutant. `encoding='utf-8'` is now pinned in all three. **A battery that cannot run
  is not a battery that passed** — the same class as the two core batteries that were unpassable for
  10 pushes (§5.38).

### Two new defects, both filed rather than fixed here

* **`P2-109` — `nt_orders`' `account` parameter is ignored.** Measured: `nt_orders(account="Sim101")`
  and `nt_orders()` returned **byte-identical** payloads, and the single order in them is on a
  **funded TakeProfit account**. `P1-90`'s family on a *read* path, which that entry's header names
  explicitly. An agent checking "does Sim101 have working orders?" before or after a flatten is being
  answered about someone else's account — and both `P1-105` and `P0-104` were diagnosed partly by
  reading order state. ⚠️ A naive "the filter returns a subset" test **passes under the defect**; the
  regression test is that the two answers *differ*.
* **`P3-110` — the panic flatten's cancel set omits `OrderState.TriggerPending`**, which is where a
  protective stop rests. If that reading is right, `nt_emergency_flatten` leaves resting stops behind,
  and a surviving stop **opens** a position when it triggers. Not measured; the stub cannot answer it
  (it omitted 6 of 16 `OrderState`s and hid a live `P0`). Widening the panic path is a behaviour
  change needing its own live validation, so it was **not** smuggled into this commit.

### Order from here

1. **`P1-102`** (larger than filed — §5.47).
2. **`P2-103`**, then **`P2-108`**, then **`P3-110`**. ✅ `P2-109` closed in §5.52.
3. The architectural **`P2-29`** / **`P3-33`**.

Weigh by §5.6's consequence rule, not by band letter.

---

## 5.50 The `P1-105` push turned CI RED — on a battery it never touched, and a gate it never edited

**Session 41, 2026-08-14, immediately after §5.49.** `gh run list` five minutes after the push:
**failure**, in `Mutation P1-90`, a battery with nothing to do with the change. Two defects, both
mine, both found by CI and the batteries rather than by review. Fixed in `nt8-mcp-bridge` `350b872`.

### 1. A tool reported a SKIP, I read it, and I did not act on it

§5.49 pinned `encoding='utf-8'` in the bridge's batteries with a bulk patch. Its output was:

```
patched mutate_p0104.py
patched mutate_p1105.py
patched mutate_p1106.py
SKIP mutate_p190.py (matched 0)
```

`mutate_p190.py` builds and runs in **two** steps, so it did not match the patch's anchor. The skip
was honest, printed, and read — and then nothing happened. `P1-105`'s new tests introduced
non-ASCII test names, so on the next push that battery raised `UnicodeDecodeError` on a reader
thread, `res.stdout` came back `None`, and it died before its first mutant.

**A human reading a tool's honest report is not a gate.** Made mechanical:
`tools/check_batteries_pin_encoding.py` parses every `mutate_*.py` with `ast`, finds every
**text-capturing** `subprocess.run`, and requires an explicit `encoding=`. It refuses a battery it
cannot parse *and* one with no capture at all — both are "this gate cannot see you", which is the
state it exists to forbid — prints the number of calls it actually inspected (**5** across 4
batteries), and runs **before** the batteries in `ci.yml`, because it decides whether they can run
at all. Watched failing (exit 1) on a deliberate break of one call, then passing.

### 2. Adding CORRECT code silently weakened an unrelated gate

`TestP1_90_NoBridgePathInventsAnAccount` asserted:

```csharp
int routed = Regex.Matches(code, @"ResolveOrRefuse\(").Count;
Assert(routed >= 6, ...);
```

`P1-105` added `ClosePosition` as a **seventh** resolution site. From that moment, a mutant that
strips the resolver out of the compliance site leaves **6** — and the assertion still passes.
**Nothing in the gate changed. The code around it grew, and a lower bound is satisfied by unrelated
growth.**

`mutate_p190.py` caught it on its first run after the addition. Review did not, and the 190 green
tests could not. Now `== 7`, with the reason in the assertion text so an eighth site must bump it
in the same commit — **the speed bump is the feature.**

⚠️ **`>=` in a gate is a slow leak.** This is *a gate's evidence changes with shape* in its cheapest
form: the previous instance needed a CI restructure to trigger, this one needed only a correct
feature landing next door. **Every lower-bound count in a source gate deserves re-reading as "what
unrelated addition would satisfy this?"**

### The order the two lessons arrive in matters

Both were found **after** a green local run, a green suite, four green gates and a live validation.
The battery is the only thing that saw either. That is the third time this session a battery caught
the author (`P1-105`'s two source-gate survivors were the first two), and it is the argument for
running **every** battery after a change, not only the one you wrote.

⚠️ **And `gh run list` remains a five-second check that belongs immediately after every push, not
at the start of the next session.** This is now the third recorded instance of red CI here; the
difference is that this one was caught in minutes.

---

## 5.51 `P3-110` measured in the last 15 minutes of the session — and the entry was WRONG

**Session 41, 2026-08-14 20:30–20:39Z, Sim101.** `P3-110` was filed hours earlier from *reading*
`ActiveOrderStates` and reasoning about what `OrderState.TriggerPending` means: the panic flatten
omits it, a protective stop rests there, therefore `nt_emergency_flatten` leaves stops behind that
**open** a position when they trigger. It was the one open item that could not be answered offline,
so it got the remaining market window.

**It does not reproduce.**

| step | measured |
|---|---|
| long 2 MNQ, then `StopMarket` Sell 2 @ 30050 | rests in **`Accepted`**, not `TriggerPending` |
| `nt_emergency_flatten` (Sim101, 2min lockout) | `firstPassCancelled: 1`, `residualCancelled: 0`, `flattenOrdersSubmitted: 1`, `accountsStillOpen: []` |
| orders afterwards | **none on Sim101** — the stop was cancelled |
| `StopLimit` Sell 1, stop 30050 / limit 30040 | also **`Accepted`** |

`Accepted` is already in the set, so both stop types are cancelled by the first pass. **The hazard
as filed does not exist**, and what remains is much smaller: an ATM/strategy-managed stop was not
driven, and **nothing has yet been shown to reach `TriggerPending` on this platform at all**.

### Why this is the good outcome, not a wasted item

**It was FILED, not fixed.** The tempting version of `P3-110` was a one-word addition to a set —
five seconds of work, in the same commit as `P1-105`, on the most consequential path in the bridge.
That would have shipped a change to the panic path **with no defect behind it**, and nothing would
ever have contradicted it: the suite would stay green, the stub cannot model the state, and the
entry would read as evidence for itself forever.

This is [[check-the-exemplar-belongs-to-the-class]] applied **before** the fix rather than after.
`P2-107` learned it the expensive way — a correct fix named after a rule that already had its own
latch. Here one live drive cost fifteen minutes and killed the premise.

**The rule: a defect derived from reading source, on a path a test double cannot model, is a
HYPOTHESIS. Drive it before you fix it, and say which it is in the entry.**

### Two other things the same drive re-validated for free

* **`P0-104` holds live**: `residualCancelled: 0`. The same shape measured `1` before that fix — the
  panic button cancelling **its own flatten order**, account still long 11, `success: true`.
* **`P1-97` holds live**: a `sell` on a **flat** account came back as `action: "SellShort"`, so the
  bridge still resolves direction from the position rather than echoing the caller's label.

### And the ordering gate refused a status word I invented

The entry was first re-headed `-- NARROWED 2026-08-14, ...`. `check_next_list_ids.py` does not
recognise `NARROWED`, so the entry became **unreadable** to it and four ordering-list citations
failed with *"names `P3-110`, which has no entry in the plan"*. That is the gate behaving correctly:
it **fails on what it cannot parse** rather than skipping it — the property added to
`check_anchors.py` earlier the same day, after that one printed `ok` on 18 anchors it never read.
Re-headed `-- OPEN, but NARROWED by live measurement ...`, which states the status first and the
nuance second. **If a status word is worth inventing, teach the gate; until then, lead with a token
it knows.**

---

## 5.52 `P2-109` closed — three parameters, none implemented, and a defect that lived in a JOIN

**Session 41, 2026-08-14.** Taken **ahead of `P1-102`** deliberately: `P1-102` needs an account
*holding a position* to validate and futures were shut until Sunday, so its live half would have
been unverifiable. `P2-109` needed no market at all — the stale `Rejected` order on the funded
account was enough. **Pick the item whose evidence you can actually obtain tonight.**

Closed in `nt8-mcp-bridge`, deployed, live-validated. Suite **190 → 233** (38 → **46** tests),
battery **12/12**, `nt_compile` `errorCount: 0`.

### Nothing was wrong with any component

`nt_orders` advertises `account`, `limit` and `offset` and implemented **none** of them:

* `mcp/lib/tools.js` advertises all three — correct;
* `mcp/nt-mcp-server.js` builds the query string and **sends** all three — correct;
* `GetOrders()` was a clean read of every account's orders — correct;
* `case "/api/orders": return GetOrders();` — **took nothing**, between two routes already passing
  `query[...]`.

**The defect was in the join, and every piece reviewed in isolation looks right.** That is the
argument for the wrapper and the addon sharing a repo, restated from the other direction: a
contract whose two sides sit in two commits cannot be reviewed as one thing. The tool description
promised "cursor pagination", so an agent paging with `offset` re-read page one forever.

### Two extractions, one of them a MOVE

* **`BridgeAccountScope`** is now the single definition of "this request is about account X".
  `BridgeClosePlan.MatchesAccount` delegates. The alternative — a second copy for the orders path —
  is exactly how `P1-90` reached six sites and `P1-100` ended with three readers of one flag, each
  taught something different. ⚠️ The move broke two of `mutate_p1105.py`'s anchors; they were
  **repointed, not retired**, the same move `P1-100` made with `mutate_p292.py`. An anchor that
  stops matching prints `[SKIP]` and scores a SURVIVOR, so a moved predicate with stale anchors is
  a battery quietly proving nothing.
* **`BridgeOrderQuery`** parses and clamps, and the parsing is why it is a class rather than two
  `int.Parse` calls. ⚠️ `/api/bars` on the next line still does `int.Parse(query["count"] ?? "100")`
  — it handles ABSENT and throws `FormatException` on `count=abc`. **Absent and unparseable are
  different inputs and only one of them was considered.** Here `limit=abc` gives the default;
  `limit=0` clamps to **1**, because an empty page and an empty book are indistinguishable to
  whoever reads the answer, which *is* this defect; a negative offset is 0, never an index from the
  end.

### Live validation — with the market closed

| call | before | after |
|---|---|---|
| `nt_orders(account="Sim101", limit=8)` | the **funded** account's order | **`[]`** |
| `nt_orders(limit=6)` | byte-identical to the above | the funded account's order |
| `nt_orders(account="Sim1O1")` | the same payload again | **refused**, naming the 96 accounts |
| `nt_orders(account="TAKEPROFITPRO524207503")` | — | the order — **positive control** |
| `nt_orders(offset=1)` | — | `[]`, past the end and not wrapped |

⚠️ **The regression test is that the two answers DIFFER.** "The filter returns a subset" **passes
under the defect** — every set is a subset of itself. And the positive control is what proves the
filter is a filter rather than an outage: a predicate that returns nothing satisfies every "it
excluded the wrong account" assertion ever written. *For a detector, the negative test is the one
that proves it works* — fourth site where that has mattered.

### The battery caught the SAME lesson twice in one session, and the second time it was me

**11/12 on the first run.** The survivor: neutering the account resolution's
`if (ordersResolution.Refused) return ...` to `if (false)` left the `ResolveOrRefuse` call in place,
and the source gate — which asserted the resolver is **called** — still passed.

⚠️ **That is the identical survivor `P1-105`'s battery produced a few hours earlier**, and I wrote
the identical incomplete gate at the next site. *A gate that a value is COMPUTED is not a gate that
it is USED* — learned at one call site and not carried to the next one written. **This repo's own
second-reader pattern (`P1-100`, `P1-105`) with the author as the second reader.**

So the fix is a **sweep**, not a third per-site assertion.
`TestEveryResolverSiteACTSOnTheRefusal` extracts every
`x = BridgeAccountResolver.ResolveOrRefuse(...)` from the source and requires that same `x` to be
tested for `.Refused` **and returned on**. A ninth site is covered the moment it is written, without
anyone remembering the test exists. **When you fix the same gate weakness twice, stop fixing sites
and derive the check from the source.**

⚠️ **The exact-count gate from §5.50 fired on its first opportunity.** `GetOrders` made a seventh
resolver site an eighth, `routed == 7` failed, and the number was raised deliberately with the
reason recorded. Hours earlier that assertion had been `>= 6` and a mutant had walked through the
slack. **The speed bump is the feature.**

### Order from here

1. **`P1-102`** (larger than filed — §5.47). ⚠️ Its live half needs an account **holding a
   position**, so it wants market hours: futures reopen Sunday 18:00 ET.
2. **`P2-108`**, then **`P3-110`** (narrowed to almost nothing — §5.51), then **`P3-111`**.
   ✅ `P2-103` closed in §5.53.
3. The architectural **`P2-29`** / **`P3-33`**.

🆕 **`P3-111` filed**: `/api/bars` does `int.Parse(query["count"] ?? "100")` — the `??` handles
ABSENT and nothing handles **unparseable**, so `count=abc` is an unhandled `FormatException` on a
read endpoint from a caller typo. Noticed while writing `BridgeOrderQuery`, one line below the
route this session fixed. **Filed rather than fixed**: a different endpoint, and a fix riding along
in a commit whose subject is orders is a fix nobody reviews. The remedy is to reuse
`BridgeOrderQuery.ParseLimit`'s shape, not to write a third parser.

---

## 5.53 `P2-103` closed — the honesty was bought years ago and was not being spent

**Session 41, 2026-08-14.** Two read-only surfaces answer "is the guard actually protecting me, and
to what limit?" — `/api/riskguard/inventory` and `/api/copier/snapshot` — and **neither had an MCP
tool**, so the agent driving the system could not read either. Five of this repo's mutation
batteries (`UI1`, `UI3`, `UI4`, `UI5`, `UI6`) exist to keep exactly those two payloads honest, and
every mutant in them is written to make the answer *more reassuring than the box*. `F-9` was a
defect in the same surface. **A large amount of machinery had been built to make an answer truthful,
and the answer was unreachable.**

Closed entirely in `nt8-mcp-bridge/mcp/`. Wrapper tests **43 → 51**. Live-validated by driving the
MCP server over stdio.

### Measure the payload BEFORE designing the view

```
/api/riskguard/inventory  ->  635,447 bytes   96 accounts   2,304 rule rows
/api/copier/snapshot      ->    1,216 bytes
```

**A passthrough tool would have spent the context window on one read.** `nt_riskguard_inventory`
therefore defaults to a summary — **635,447 → 3,082 bytes**, measured through the real tool call,
with `view="account"` and `view="full"` available when they are actually wanted.

⚠️ **The summarising lives in the WRAPPER, not the addon, and the reason is worth keeping: the
constraint is CONTEXT, not bandwidth.** 635KB over localhost costs nothing. Putting it server-side
would have meant a C# change, a deploy and a new extracted class to make it testable, for no gain
against the constraint that actually binds.

### Three decisions inside the view

* **Every number is folded out of the same rule rows the `account` view returns.** A summary
  keeping its own counters would be free to disagree with the detail beneath it — which is `F-9`
  verbatim. The tests **recount from the fixture and require agreement**, rather than asserting
  hand-written totals, so the assertion cannot pass a summary that has quietly drifted.
* **`ConfiguredNotEvaluated` is collapsed by RULE, not per account.** The live box reports **384**
  such rows: **four** rules × 96 accounts. Listing them per account buries one finding under its own
  repetition — the `P2-41` shape, where a `PerAccount` rule reading a global collection reported
  evidence for all 96 accounts from one mapping.
* **A truncated list SAYS so.** `enforcingCount` is always complete; the named list is capped and
  carries `enforcingTruncated`. A list that silently stops is how a reader concludes there are only
  two problems.

`P1-90` on the read path as well: an account name matching nothing is **refused** with the count and
a sample of real names — exactly what `P2-109` was, closed an hour earlier.

### What the first summary said about the box

| | |
|---|---|
| mode / armed | `shadow`, `isArmed: true` |
| **`Enforcing`** | **0** — correct in shadow, and the number to re-read the moment the mode changes |
| `EvaluatedNotEnforcing` | 1384 |
| **`ConfiguredNotEvaluated`** | **384** = *Consistency / daily-profit cap*, *Consistency cap threshold*, *News events file*, *Prop suite armed*, each × 96 |
| `Inert` / `Disabled` | 288 / 248 |

Those four are `P1-77`'s deferred set and the guard's own `unevaluatedRules` notes say so in words
(*"NO CODE READS THIS"*). **One tool call now answers what previously took `interventions.jsonl`
parsed by hand, `config.json` read off disk, and a raw `curl`** — the operational cost the entry was
filed on, and a cost this session paid repeatedly while closing `P1-105` and `P2-109`.

### Validated by DRIVING the server, not by asserting on source

The server was spawned and sent real `initialize` / `tools/list` / `tools/call` JSON-RPC against the
running bridge. `tools/list` returned **54** tools including both new names; the summary produced
the table above; `Sim101` returned its 24 rule rows; `Sim1O1` was **refused**; `nt_copier_snapshot`
filtered to `Sim-ORB` — a **follower** — matched its relationship, proving the filter reads either
side of the relationship; `Nope` gave `matchedRows: 0`; `nt_health.riskguard` read
`{"version":"1.23.0","loaded":true,"mode":"shadow","isArmed":true,"guarding":true}`.

⚠️ **New tools do not appear in a running MCP client until it RESTARTS** — schemas are read at
startup (`P1-91`). The stdio drive is what proves the tools work without waiting for that, and it is
the technique to reuse: *a wrapper change can be end-to-end validated in-session even though the
session's own client cannot see it.*

⚠️ **A third exact-count gate fired**: `TOOLS.length` 52 → 54. Bumped deliberately, reason recorded.
That is three in one session (twice on the addon's resolver-site count, once here), each one making
the author state that an addition was intended. Earlier the same day the `>=` version of one of them
let a mutant survive.

⚠️ **`fsm-reset` was deliberately NOT added.** It is a WRITE, and it belongs with `P1-102`'s review
of the lockout write-path — where `action: "lock"` already silently answers `isLockedOut: false`.
Adding a write to a stuck-FSM surface without that review is how `P1-72` regressed.

### Order from here

1. **`P1-102`** — ⚠️ its live half needs an account **holding a position**; futures reopen Sunday
   18:00 ET.
2. **`P2-108`**, then **`P3-110`** (narrowed — §5.51). ✅ `P3-111` closed in session 42 (§5.54).
3. The architectural **`P2-29`** / **`P3-33`**.

---

## 5.54 `P3-111` closed — the entry named the one defect of four that was LOUD

**Session 42. Closed and live-validated in full — every measured case re-driven against the box,
plus positive controls.** Unlike `P1-106` (refusal half only) and `P1-105` (healthy/empty paths
only), there is no half of this left unmeasured.

### What was filed, and what was there

The entry read, in its entirety: *"`/api/bars` does `int.Parse(query["count"] ?? "100")` — absent
is handled, unparseable throws."* True, and the least of it. Probing the deployed box before
writing code found the endpoint broken at **both ends of every parameter it takes**:

| Request | Before | After |
|---|---|---|
| `count=abc` | **HTTP 500 + .NET stack trace** | 200, 100 bars |
| `periodValue=xyz` | **HTTP 500 + .NET stack trace** | 200, 100 bars |
| `period=Banana` | **HTTP 500 + .NET stack trace** | a refusal naming all **17** valid types |
| `count=200000` | **21,285,727 bytes** | 531,720 bytes (5,000 bars) |
| `count=1000000` | **1,000,000 bars** | 531,720 bytes (5,000 bars) |
| `count=0` / `-5` | **0 bars** — reads as "no data for this instrument" | 1 bar |
| `offset=0` vs `offset=500` | **BYTE-IDENTICAL** | different windows; pages abut exactly |

### ⚠️ Weigh the QUIET failure above the LOUD one

**This is the reband and it is the transferable part.** The entry was banded `P3` on the reasoning
*"it's a read, so the consequence is a 500 rather than an action."* That reasoning is sound about
the defect it names and it missed the other three, because **a 500 with a stack trace is the only
one of the four that tells anybody anything.** The unbounded response and the ignored `offset` are
silent. `count=0` returning zero bars is the worst of them: it is a **well-formed answer that reads
as a fact about the market**, and nothing anywhere raises. Same family as `FILL_NOT_MEASURED`
firing on every manual fill and `P3-30`'s audit firing on a correctly protected account — except
inverted. **When banding an endpoint, enumerate what it returns when it is WRONG, not what it
throws.**

### ⚠️ `offset` was `P2-109` at a second endpoint, found by running that ticket's own test

`/api/orders` advertised three parameters and implemented none. Hours later, the same two-call
test — identical requests differing only in the parameter, compared for **inequality** — was
pointed at `/api/bars`, and `offset=0` and `offset=500` came back byte-identical. The wrapper sent
it faithfully; the route dropped it. **A test that closed one ticket is a probe you can aim at the
next endpoint, and it costs one command.**

### ⚠️ The size promise was `P1-72`'s shape, and the fix keeps the promise rather than rewording it

The MCP schema advertised **"max 5,000 rows" in two places** while the addon enforced nothing. Two
numbers disagreed and only one could stay. The cap is now **5,000 — the number already written
down** — because raising code to meet an existing promise makes a contract true, where lowering the
promise breaks whoever believed it. ⚠️ **It is only honest because `offset` now works**: a cap
bounds one RESPONSE, which is memory; a cap on what is KNOWABLE just pushes callers back to
`/api/bars/export`. Mutant 7 attacks precisely that confusion — capping the *request* as well looks
like a tightening and silently makes every page past the first return the same bars.

### ⚠️ Both readers, and the second one was never filed — FOURTH instance

`/api/bars/export` takes the same `period` string and threw on the same typo. **Ten lines below it,
`merge` has used `Enum.TryParse` with a fallback since the method was written.** One method, two
enum parameters from the same caller, one of them treated as hostile and the other not, and nothing
compared them. After `P1-100`, `P2-98`/`P1-99` and `P1-105`. **`Enum.Parse` is `int.Parse` for
names** — grep for both when you fix either.

The wrapper's `period` enum was **removed, not extended**: it hard-coded five names and the live
refusal proves NT8 has seventeen, so the schema **forbade twelve values the addon serves**. The
addon derives the set from `Enum.GetNames(typeof(BarsPeriodType))`, so there is no second copy.

### ⚠️ Three gates caught, and one of them was missing from this repo's sibling entirely

* **`tests/BridgeTests.csproj` now globs `addons/*.cs`** (one exclusion) where it was a hand-typed
  list of eight. Adding two more by hand would have been the **third hand-typed-inventory drift in
  one day** after `check_bridge_parses.py`. The glob states `P2-27` mechanically: every addon file
  naming no NT8 type is EXECUTED from the moment it exists.
* **`tools/check_anchors.py` ported to `nt8-mcp-bridge` after it was needed.** Moving the parse
  arithmetic broke **six** of `mutate_p2109.py`'s anchors; they printed `[SKIP]`, scored as
  **survivors (6/12)**, and only a hand re-run surfaced it. Here the same edit fails in the commit.
  **Third per-repo gate found missing on the bridge side** after `check_ci_runs_every_battery.py`
  and `check_expected_survivors.py`. **A gate is per-repo. Writing one where you found the defect
  leaves the other side unguarded, and the other side is where you work tomorrow — here it was
  `cp`.** Anchors were **repointed, not retired**, and the move made them stronger: one mutant to
  the shared clamp is now evidence about **both** endpoints.
* **A new test gate failed on its own first run**, reading only the FIRST `hasMore` assignment —
  the empty-window branch's constant `false`. *State the region a gate inspects*, fifth instance.

### ⚠️ The battery's one survivor was the author's, again

Mutant 1 was named *"the route parses at the seam"* and passed `query["count"] ?? "100"` — still a
string, still handed to the safe parser, still correct. **It never expressed the defect**, so no
test could kill it and none was missing. The filed defect is now **unrepresentable**: `GetBars`
takes no `int`, so `int.Parse` at the route does not compile, and a test asserts that property
directly. Second instance of `P1-99`'s lesson — **a surviving mutant does not always mean a missing
test**; there it was unkillable by construction, here it did not restore what it was named after.
**Read what a mutant DOES before writing a test for it**, or you invent a test to satisfy a
mutation that changes nothing. Replaced with the seam defect still possible — the route discarding
`offset` — for **10/10**.

### ⚠️ `hasMore` was nearly shipped as `start > 0`

Caught while writing the return statement. When NT8 returns exactly what was asked for, `start` is
0 and older history still exists, so an agent stops **one page early** believing it read the whole
series — silent truncation, the mirror of this ticket's silent widening. It compares
`available >= requestSize`; mutant 8 pins it.

### Evidence

Harness **233 assertions / 46 tests → 302 / 56**; wrapper **51/0**; `mutate_p3111.py` **10/10**;
`mutate_p2109.py` **6/12 → 12/12** repointed; `check_anchors.py` **64 anchors / 0 broken**;
**6** batteries wired; `check_bridge_parses.py` **11 files**; `nt_compile` **errorCount 0**;
`deploy.py --verify` **20 files / 0 orphans**. Every table row re-driven live; a valid export wrote
**552 rows** as a positive control; the MCP tool path end to end (`offset=0` → 16:58–17:00,
`offset=3` → 16:55–16:57, contiguous).

### Order from here

1. **`P1-102`** — ⚠️ its live half needs an account **holding a position**; futures reopen Sunday
   18:00 ET.
2. **`P2-108`**, then **`P3-110`** (narrowed — §5.51).
3. The architectural **`P2-29`** / **`P3-33`**.

---

## 5.55 `P2-29` partially closed — a pure code move disarmed a source gate, and widening it found a real defect

**Session 42.** The WPF dashboard (`RiskGuardWindow` + `CardControls`, 724 lines) moved out of
`RiskGuardAddOn.cs` into `addons/RiskGuardWindow.cs`. **7,058 → 6,334 lines.** A relocation of two
independent top-level types: no `partial` keyword, no member reshuffled, no behaviour change.

⚠️ **The entry's own size claim was wrong** — it said 4,108 lines with the window at `:3389-4096`,
measured 7,058 with it at `:6338-7057`. **A size claim decays silently; re-measure before quoting.**

### ⚠️ The finding: a MOVE silently disarmed a source gate, and only the battery noticed

`mutate_p187.py`'s WarnOnly mutant **SURVIVED** after the move, where it had always been killed.
The test that kills it asserts `!code.Contains("WarnOnly")` over `addons/RiskGuardAddOn.cs`
**read by name**, and the settings dropdown it forbids had moved to the file next door. The gate
searched a file the string could no longer be in and **passed**.

Three things about how it was and was not caught:

* **The suite was 1469/0 throughout.** It could not have told you.
* **`check_anchors.py` did NOT catch it.** That gate asks whether the BATTERY can still find its
  target — a different question from whether the TEST can. It correctly reported the one broken
  *anchor* (repointed to the new file, and the battery converted to 4-tuples so it can address two
  files) and said nothing about the gate, because nothing inspects a test's file paths.
* **The mutation battery caught it, and only the battery.** This is the clearest instance yet of
  why the batteries are the evidence standard here: a refactor that every other check called clean
  had removed a defence, and the only thing that noticed was re-running a mutant.

### ⚠️ ABSENCE gates and PRESENCE gates break in opposite directions

**A source gate asserting a pattern is PRESENT fails loudly when pointed at the wrong file. One
asserting a pattern is ABSENT passes vacuously** — it finds nothing because it is looking nowhere.
Only one of the two tells you. **Absence gates must read the tree, not a named file.**

`AllAddonCode()` now concatenates every `addons/*.cs` with comments stripped, **refuses an empty
corpus**, and is what all absence gates search. `TestP2_29_TheSourceGatesReadTheWholeAddonTree` is
the gate on the gates. Same remedy as `check_bridge_parses.py` and `BridgeTests.csproj` in the
sibling repo the same week — **state the REGION a check inspects, and make it the whole thing the
check is about**. Fifth and sixth instances of that class in two sessions.

### ⚠️ Widening the `P1-13` gate to the tree found a real defect immediately — `P2-112`

`DynamicAtmManager.cs:507` has `P1-13`'s fail-open verbatim:

```csharp
var dispatcher = System.Windows.Application.Current?.Dispatcher;
if (dispatcher == null) return;
```

`P1-13` was closed against the guard's own handlers and its gate then read only
`RiskGuardAddOn.cs`, so **this site was never inspected by anything**. With `Application.Current`
null, the 5-second ATM monitor returns immediately forever: breakeven stops never move, trailing
never advances, nothing logs. **Filed, not fixed** — `MonitorTickCore` calls `Account.Change()`, so
`P1-13`'s "run inline" remedy would put a broker call on a `Timer` thread, and that call site needs
verification **on settle** against a live market. ⚠️ **Reachability was NOT measured** and is part
of closing it; this box runs the GUI, so it is latent rather than active.

Held green by an **ID-bearing allowance that fails in BOTH directions**: the gate exempts
`DynamicAtmManager.cs` by name with the ID, **and asserts the exemption is still needed**, so it
cannot outlive the defect and quietly widen the gate. Same construction as
`check_no_dead_safety_machinery.py`. **That is the honest way to widen a gate that finds something
you cannot fix tonight** — narrowing it back to pass would have deleted the finding.

⚠️ **`check_next_list_ids.py` also failed on its own marker set**: it strips `✅⚠️~*` and not `🔶`,
so a heading written `-- 🔶 PARTIALLY CLOSED ...` parsed as having no status and the entry read as
missing entirely. Loud, not silent, and fixed by stripping every marker the doc actually uses.

### Evidence

Suite **1469/0 → 1482/0** (501 → 502 tests); `mutate_p187` **survivor → SURVIVORS: none**;
`check_anchors.py` **301/0**; all seven core gates green; `nt_compile` **errorCount 0** with a
byte-identical warning set; `sync_nt8.py --verify` **ALL IN SYNC (10 files)**; the running guard
read back **shadow / armed / 96 accounts / 2,304 rule rows** — unchanged.

### Remainder

Splitting `RiskGuardAddOn` itself into `{Core,Fsm,Rules,Actions,FirmMirror,Persistence}` partials.
Genuinely different work — moving members of one class, not relocating independent types — and it
would break far more than one anchor. **The tooling to do it safely now exists and is proven.**

### Order from here

1. **`P1-102`** — ⚠️ live half needs an account **holding a position**; futures reopen Sunday 18:00 ET.
2. **`P2-108`**, then **`P2-112`** (⚠️ its fix touches `Account.Change()`, so it wants a live
   market too), then **`P3-110`** (narrowed — §5.51).
3. **`P2-29`**'s remainder, then the architectural **`P3-33`**.

---

## 5.56 Market Replay is the answer to "the market is shut", and it cost one classifier change

**Session 42.** Asked whether NT8 Market Replay could drive the position-dependent tickets with
futures closed. **Yes**, and three measurements settled it rather than argument:

* **The guard already watches `Playback101`** — 24 rule rows, `isExcluded: false`, StopGuard with a
  15s attach deadline and `Flatten` on missing, `DailyLossLimit` −1000, `TrailingDrawdown` 1500.
  Replay orders exercise the guard for real, not in a bubble.
* **Replay data is on disk**: 261MB — but only `MNQ 12-25` (**one date**, 2025-12-01) and `^SP500`.
  MNQ 12-25 is an **expired** contract; more dates need downloading.
* ⚠️ **`Playback101` was classifying as a LIVE account.** `IsSimulationAccount` was
  `Provider == Provider.Simulator`, and its provider is `Playback`.

### What replay unblocks

| item | replay? |
|---|---|
| `P2-108` (`NAKED_POSITION` every 10s in shadow) | **yes** — needs a position with no stop |
| **`P1-106`'s unvalidated half** | **yes**, and it is the prize: breach the −1000 daily loss for real and the guard imposes a lockout **while a position is open**, which nothing on this box could previously do |
| `P1-102` (lockout read/clear tool) | **yes**, end to end — a real breach gives a real binding lockout to clear |
| `P3-110` (`TriggerPending`) | probably, via a stop-limit |
| **`P2-112`** | **no** — needs `Application.Current == null` (headless NT8); replay is irrelevant |

⚠️ **Connecting Playback DISCONNECTS Provider31**, so the guard stops seeing the 96 funded/eval
accounts for the duration of a replay run. Acceptable on a closed weekend — **re-verify arming
afterwards**, and never start one while those accounts hold anything.

### The classifier change, and why it is recorded rather than quiet

`Provider.Playback` now also classifies as non-live. **This reversed a decision the code itself had
written down**: *"Playback is deliberately NOT exempt — it costs nothing to arm a relationship for
a playback run, and guessing wrong in the other direction costs money."*

That first clause is true **about the copier**, and the copier is the only caller it considered.
`McpBridgeAddOn` asks the same question on the **order-placement** path, where the cost is not
"arm a relationship" but an operator and an agent pressing `confirmLive: true` on **every replay
order** — rehearsing, against an account that cannot lose a cent, the one reflex standing between a
careless call and the funded 50K. **A safety flag you press a hundred times a weekend is not a
safety flag.** That is the gap in the recorded reasoning, and it is the whole argument.

⚠️ **It is not `P2-38` repeated.** That defect was `Name.StartsWith("Sim")` — a **user-chosen
string** read as a fact about money. This is an **exact platform-enum match**. Widening a name test
and adding a second exact enum value are different acts. Null, unset, and anything not positively
identified all still fail closed.

### ⚠️ And no battery covered the money switch at all

**27 batteries, and not one mutated `IsSimulationAccount`** — the single predicate deciding whether
an account can lose real money, which had **already had a real defect in it**. `P2-38`'s fix
shipped with tests and no mutants. *The riskiest predicate in the repo was the least mutated*,
which is `P2-27`'s shape at the sharpest possible place. `mutate_p238.py` now exists: **5/5**.

⚠️ **Mutant 3 is the one to carry**: widen to "anything that is not NinjaTrader" and Rithmic and
InteractiveBrokers — real money both — classify as simulated. **Every positive assertion still
passes under it.** Only the negative half catches it, and it fails 5 of them. **A classifier that
answers "simulated" to everything passes every positive test ever written for it** — the
detector-needs-a-negative-test rule applied to the money switch.

### Evidence

Suite **1482 → 1487/0**; `mutate_p238.py` **5/5**; anchors **306/0**; **29** batteries wired;
`nt_compile` **errorCount 0**; `sync_nt8 --verify` **ALL IN SYNC (10 files)**. **Live-validated**:
`nt_place_order` on `Playback101` with `confirmLive` **omitted** returned `status: submitted` where
it was previously refused as live — the enforcer, not the report — then cancelled, with
`/api/orders?account=Playback101` and `/api/positions` both reading `[]` afterwards.

### Order from here

1. **`P2-108`** — REPRODUCED LIVE (§5.57) and ready to fix. ✅ `P1-102` closed.
   ⚠️ Re-verify guard arming after reconnecting Provider31.

   ⚠️ **`P1-102` is where `P1-106` (closed) left its unvalidated admission half, and
   `check_next_list_ids.py` is what forced that to be said.** Naming `P1-106` (closed) as work in
   this list failed the gate — *"if work REMAINS inside a closed entry, that work needs its own ID;
   a remainder hiding
   under a closed one is invisible to every count."* Exactly right: `P1-106` is CLOSED with only
   its **refusal** half measured, because nothing on this box can impose a lockout on an account
   holding a position. That blocker was recorded as enlarging `P1-102` (closed §5.57), so the replay run
   validates both at once and is tracked under the ID that is actually open. **A closed ticket
   cannot carry an open remainder** — the count stops being true the moment it does.
2. **`P2-112`** (⚠️ its fix touches `Account.Change()`; wants a live market), **`P3-110`**.
3. **`P2-29`**'s remainder, then the architectural **`P3-33`**.

---

## 5.57 `P1-102` closed under Market Replay, and `P2-108` reproduced with the number it was filed with

**Session 42, continued.** Market Replay went from "would that work?" to a closed `P1` and a
reproduced `P2` in one sitting. **Replay is now the answer to "the market is shut."**

### It works, end to end

A market order on `Playback101` **filled**: long 2 MNQ SEP26 @ 29480.375. Order → fill → position,
with the guard watching. That is the capability the whole position-dependent backlog was waiting on.

⚠️ **The replay data is NOT what was on disk an hour earlier.** NT8 downloaded `MNQ 09-26` for
**2026-08-13 and 2026-08-14** on demand — a real recent session — where the only file present
before was `MNQ 12-25` for 2025-12-01, an expired contract. **Check what replay actually serves;
do not plan around the directory listing.**

### ⚠️ `P2-108` REPRODUCED LIVE, with hard numbers

Position with no stop, guard in `shadow`. Sampled every 30s:

| t | NAKED_POSITION | SHADOW_ACTION | ACTION_SUPPRESSED |
|---|---|---|---|
| +30s | 3 | 0 | 0 |
| +60s | 6 | 0 | 0 |
| +90s | 9 | 0 | 0 |
| +120s | **12** | 0 | **0** |

Perfectly linear — **one per 10 seconds, indefinitely** — and **12-in-120s is the exact figure the
ticket was filed with**. ⚠️ **The load-bearing number is `ACTION_SUPPRESSED = 0`**: it proves
`DispatchActions` never sees this path, so `P2-107`'s deduplicator cannot help. `NAKED_POSITION` is
a `LogEvent` with no action behind it, precisely as filed. **Fix not attempted yet — this is the
next item, and it now has a measured before.**

### `P1-102` closed, and building the tool exposed a second defect

`POST /api/lockout` existed with **no `nt_` tool reaching it**. Worse, measured before the fix:

    action:"lock"  ->  {"success":true,"action":"lock","account":"Playback101","isLockedOut":false}

`HandleLockout` ended with an **unconditional status read**, so every unrecognised action fell
through to `success: true`. The most obvious thing a caller would send was answered *"I locked it,
and it is not locked."* `P1-88`'s shape; `F-9`'s general form. It also **blocked the ticket**: an
MCP `action` enum is pinned to the addon's whitelist (`P1-72`), and **there was no whitelist** —
the addon accepted every string by construction.

Also fixed: the unlock branch returned a **hard-coded `isLockedOut = false`**, a claim made without
asking. It re-reads the enforcer now. **Third site of *report the outcome, not the call*** after
`P1-105` and `P0-104`. And `lock` stays absent — a lockout imposed by a tool has no rule behind it
and no recorded authority for `P2-92`'s clause to read.

### ⚠️ 53 green wrapper tests could not see a broken handler

`nt_lockout` was written as `ntFetch(path, { method, body })` — a `fetch()`-shaped options object —
where the real signature is positional `ntFetch(endpoint, method, body)`. Every other POST handler
in the file contradicts it. **Schema tests validate the advertised shape, not the call**, so all 53
passed. Caught only by **driving the MCP server over stdio**, the same technique that validated
`P2-103`. *Add an end-to-end drive to every wrapper change; the schema test is not one.*

### Evidence

Bridge harness **302 → 310**, wrapper **51 → 53**, `nt_compile` **0 errors**,
`deploy.py` core pin **v1.25.0**. Live: `lock` refused naming the valid set; `status` a clean read;
`unlock` success with `error: null` after re-reading; typo account refused naming **97**;
omitted account on a protection-removing write refused. Position closed afterwards via
`nt_close_position` — `positionsMatched: 1`, `positionsStillOpen: []` — which incidentally
re-validates `P1-105` on a genuinely FILLED position for the first time.

### Order from here

1. **`P2-112`** — ⚠️ its fix touches `Account.Change()`, so it wants a live market (§5.55). ✅ `P2-108` closed §5.58.
   Per `P2-101` (closed): bound it by an attempt COUNT the alarm also reads, clear on the CONDITION not a
   timer, and **1 outside an acting mode is the fix, not a tuning value**.
2. **`P2-112`** (⚠️ its fix touches `Account.Change()`), **`P3-110`**.
3. **`P2-29`**'s remainder, then the architectural **`P3-33`**.

⚠️ **Provider31 is still disconnected** — the replay session took the connection. Reconnect and
**re-verify guard arming** before treating any funded-account reading as meaningful.

---

## 5.58 `P2-108` closed — and the defect IN THE FIX was found by the box, not the suite

**Session 42.** Reproduced, fixed, and re-validated under Market Replay in one sitting.

### Reproduced with the number it was filed with

Position with no stop on `Playback101`, guard in `shadow`: **3 / 6 / 9 / 12** at 30/60/90/120s.
One per 10 seconds, indefinitely. ⚠️ **`ACTION_SUPPRESSED` stayed 0 throughout**, which *proves*
rather than assumes that `P2-107`'s deduplicator cannot reach this path — these are `LogEvent`
calls with no action behind them.

⚠️ **The class was bigger than the ticket**: the audit emits **three** findings from one loop on
one timer, all unbounded. All three now route through `AuditFindingThrottle`, with a source gate
keeping them there.

### After the fix, identical test

| | before | after |
|---|---|---|
| `NAKED_POSITION` in 120s | **12** | **1** |
| `AUDIT_FINDING_SUPPRESSED` | 0 | **1** |

And the leg that actually matters: fires once → announces going quiet once → silent →
**position closed → record cleared → new naked position FIRES AGAIN**. Without that,
the "fix" is a permanently muted alarm, which is the defect inverted rather than cured.

### ⚠️ THE LESSON: 8 TESTS AND 8/8 MUTANTS PASSED OVER A REAL DEFECT IN THE FIX

The throttle first cleared records keyed on **evaluated findings**. The audit builds those keys by
iterating an account's **OPEN POSITIONS** — so when a naked position resolves the way it resolves
almost every time, *the position closes*, there is nothing left to iterate, the key is never
evaluated, and **the record lives forever**. The alarm mutes itself permanently on the commonest
recovery path.

Every test passed. One of them **specifically asserted** that an unevaluated key keeps its count —
true for a disconnected account, exactly backwards for a closed position. **Nothing in the suite
ever closed a position**, so nothing could tell the two apart. It was found by closing and
re-opening one on the deployed box and watching `NAKED_POSITION` fail to come back.

**The correction is SCOPE**: clear on the **ACCOUNT the audit examined**, not on the individual
finding. That preserves what the key scope was reaching for — a pass that examined no accounts
clears nothing, so a connection blip cannot re-admit the backlog — while letting a closed position
resolve. Mutant 9 exists *because the box found it*.

**This is the strongest instance yet of the standing rule**: the suite and the batteries are
necessary and they are not sufficient. A mechanism whose whole purpose is to react to a condition
CHANGING cannot be validated by tests that never change it.

### The design, three-quarters of it paid for by earlier tickets

Record clears on the **CONDITION**, never a timer (`P2-101`). Budget **re-read from the mode every
pass** — **1** observing, 6 acting, and *the 1 is the fix, not a tuning value* (`P2-101`,
`P2-107`). Key carries the **finding type**, or one finding resolving clears another's record while
every single-finding test passes (`P2-107`). New here: **suppression is announced exactly once**,
so the operator can distinguish "resolved" from "still true and no longer mentioned".

### Evidence

Suite **1487 → 1541/0**; `mutate_p2108.py` **9/9**; anchors **315/0**; **30** batteries wired;
`nt_compile` **0 errors**; `sync_nt8 --verify` **ALL IN SYNC (11 files)**.
⚠️ `mutate_p330`'s ORPHAN_STOP anchor was **repointed, not retired** — caught in the same commit.

⚠️ **The battery crashed printing its own output.** A `⚠️` in a mutant description raised
`UnicodeEncodeError` on a cp1252 console **between applying a mutant and restoring it**, leaving a
**LIVE MUTANT** in `AuditFindingThrottle.cs` that `git diff` did not show because the file was
still untracked. `check_batteries_pin_encoding.py` pins the *subprocess* encoding; this was the
battery's own `stdout`. Fixed with `sys.stdout.reconfigure`. **Re-run the suite after any battery
that does not reach its restore line** — and note the hazard arrived without anyone stopping it.

## 5.59 `P1-77` and `P1-81` closed — and the agent loop did 40% of one, for a reason worth knowing

Both closed 2026-08-15 and live-validated. The measurable outcome is one number off the deployed
box: the inventory's `ConfiguredNotEvaluated` count went **384 → 97**, and the four rules
describing protection that does not exist went to **one**.

**`P1-77`** — the consistency cap was implemented, not deleted. `EvaluateConsistencyCap` on
`PropFirmProtectionSuite`, with the registry entry given a real `Evaluator`. The evidence count is
**0 when there is no evaluation target**, so the rule reports INERT rather than Enforcing on the
~90 accounts that have none — 35% of a zero target is zero, and a cap of zero breaches on any
profit at all.

**`P1-81`** — the prop suite's `ArmedForLive` was deleted, not wired up. It defaulted to false
"for safety" and had its own `confirmLive` gate, and **no prop rule ever read it**.

### What the agent loop actually did, measured

The loop was run on `P1-81`. Honest scorecard:

* **Run 1 refused, correctly.** It builds its worktree from the last **commit**, so the
  hand-written failing tests, still uncommitted, were invisible to it. Good gate, my process error.
* **Run 2 reached round 4** (three compile failures first) and produced a patch that got two of
  three regions right, and — the part worth crediting — **respected the trap**: it never touched
  `TradeCopierEngine.cs`, where an identically-named `ArmedForLive` is load-bearing.
* **It then preserved the defect.** Rather than deleting the property it kept it behind
  `[Obsolete]`, reasoning *"retained for source compatibility with existing tests."*

⚠️ **That last one was MY ticket error, not the loop's failure.** There genuinely were tests using
the field, and `*Tests.cs` is a **protected path the loop is structurally forbidden to edit**. I
handed it a deletion that required a test change it could not make. **Do not write a ticket whose
acceptance criterion can only be met by editing a protected path** — the loop cannot tell you that
it is trapped, it can only produce the best patch available inside its constraints, and that patch
will keep the defect.

Net: it did roughly 40% of the work and cost more setup than it saved on this ticket. The setup —
failing tests, region scoping, the trap warning — is reusable, and the second ticket in this
session (§5.60) shows what it looks like when the shape fits.

### Four things the work itself turned up

1. ⚠️ **The bridge reported `enforcing = cfg.ArmedForLive`.** So `nt_prop_limits` had been
   answering *"are the prop protections enforcing?"* from a flag no rule read — **wrong in both
   directions**. It now derives from the guard's actual gate (`IsArmed && IsActingMode()`).
2. ⚠️ **Only `nt_compile` caught that.** Core suite **1570/0**, `sync --verify` clean. NT8 compiles
   every addon into ONE assembly, so deleting a public core field is a **cross-repo change**, and a
   broken assembly is invisible because NT8 keeps serving the last good one.
3. ⚠️ **A repointed mutant found a gap in my own fix.** Every `P1-77` test drove the suite *method*;
   none drove the registry **evaluator delegate**, which is what the inventory, the API and the UI
   actually read. Two tests added. Also learned: `Off()` sets `EvidenceCount = 1`, so the
   discriminator for "switched off" is `DisabledByConfig`, never the evidence count.
4. ⚠️ **Two existing assertions pinned the defect.** `consistency.Evaluator == null` was asserted
   deliberately, and correctly at the time. **The suite was defending the gap.** Same shape as
   §5.61's `"P2-25"` note assertion, twice in one session.

⚠️ Deleting `ArmedForLive` **structurally removed `P1-75`'s mechanism** — a reload could disarm the
suite only because a `confirmLive`-gated field existed to drop. That test was kept and **inverted**,
to assert the round trip now loses nothing.

---

## 5.60 `P2-78` closed by the agent loop in ONE ROUND — and the test written to fail did not

`P2-78` is three lines: `PerInstrumentRiskConfig` carried `IsBlocked` and `StopOffsetTicks`, both
read by nothing, next to a `MaxContracts` that works. `IsBlocked` is the misleading one — the
config offered **two ways to block an instrument** and only `BlockedInstruments` did anything.

**The loop's scorecard here is the opposite of §5.59's**, and the difference is the ticket shape:

```
[baseline] 1580 passed, 2 failed;  2 expected failure(s)
[test-first] 2 acceptance test(s) red at baseline
round 1: implement kimi-k2.7-code:cloud  3.8s
   [static] ok   [compile] ok   [test] ok - 1582 passed, 0 failed
   [panel] APPROVE  [glm-5.2=APPROVE(0), deepseek-v4-flash=APPROVE(0)]
```

One round, minimal patch, comment included, nothing widened. **What made it work**: one file, one
region, no protected path involved, and the one part it could not reach (`GuardRules.cs`'s operator
note, which lives inside a collection initialiser that neither `decl` nor `indent` can scope) was
**done by hand first and guarded by a test that was green before and after**.

⚠️ **But a one-round green is when to trust it least**, and the finding here is mine, not the
loop's. **The test written to be RED was GREEN on its first run.** Its region regex was the obvious
`class X \{(.*?)\}` — and the first `}` in that class closes `{ get; set; }` on the **first
property**, so the "class body" it inspected was `public int MaxContracts { get; set; ` and the
absence check passed on unfixed code.

**Fifth gate in this repo caught inspecting a region other than the one it names**, and the only
thing that caught it was writing the test to fail first and *noticing that it did not*. It now
closes on the class brace at its own indent and carries a **positive control on the REGION** — a
substring spanning the accessor list's closing brace — so it cannot silently re-narrow.

---

## 5.61 `P2-113` — the last `ConfiguredNotEvaluated` row was itself the lie

Closed 2026-08-15. Full write-up in the plan; what belongs here is how it was found and the three
things that generalise.

**How it was found:** by asking what the ONE remaining red row actually was, after §5.59 drove the
count from 384 to 97. Not by a test, not by CI — the suite was green throughout and **is green
under the defect**, because nothing compares a rule's stated reason against the code it describes.

**What it was:** `PropFirm.LocalNewsEventsFilePath` reported as read by nothing, 97 rows per poll,
with a reason beginning *"NO CODE READS THIS"*. `LoadNewsEventsFromDisk` had been opening it since
**`P2-25` closed in session 34** — two days. A second copy of the same false sentence sat in the
news shield's own zero-event note. Both are operator-facing.

⚠️ **`F-9`'s class in the PESSIMISTIC direction, and that is not the harmless one.** Every other
ticket against this registry defends a row reading *greener* than the truth. This one read redder,
and the cost arrives by the same mechanism one step removed: **a red row that is wrong is how an
operator learns to discount red rows**, and there were 97 of them per poll.

⚠️ **Nothing re-reads a reason.** `UnevaluatedReason` is prose written once, describing *the
codebase* rather than the operator's box. It cannot go stale loudly.

**The fix is not the corrected sentence** — deleting the false claim would leave the row saying
nothing. The rule now reports **whether the operator's news file actually loaded**, which nobody
could previously see, because every failure in that loader is silent: `[]` parses perfectly,
malformed JSON was swallowed by a bare `catch { }`, a missing path just returns. **Weigh the quiet
failure above the loud one** (§5.54 again): the empty file is the worst of the four, because it is
the only one that looks like a success at every other surface.

### Three things to carry

1. ⚠️ **Closing the last instance of a state can disarm the machinery that reports it.** `P1-77`,
   `P1-81` and `P2-113` between them gave *every* rule an evaluator, so
   `Rules.Where(r => r.Evaluator == null)` is empty — and `All` over an empty sequence is true.
   **Six gates** were written against that population, each carrying an explicit `expected.Count > 0`
   so it could not pass vacuously, and **all six failed loudly in the commit that emptied it**.
   That is the good outcome. They keep their subject and get an instance synthetically
   (`RulesPlusOneUnevaluated()`, plus a `rules` parameter on `BuildSnapshot` production never
   passes). Deleting them would have retired six checks as a side effect of earning the right to.
2. ⚠️ **A test can pin a lie as firmly as it pins a truth.** `TestP186_…` *required* the shield's
   note to contain `"P2-25"`. Correct when written; a gate holding a false sentence in place
   afterwards. **A note states the CONDITION, never a ticket number.** Second instance this
   session, after §5.59's `Evaluator == null` assertion.
3. ⚠️ **An anchor that is a substring of a longer line can silently be the same anchor as
   another.** Adding a second rule reporting the same evidence count took `mutate_p182`'s
   `: R(null, null, c.NewsEventCount,` from one match to two — and revealed it had been producing a
   **byte-identical mutated file** to another entry thirty lines below **since the day it was
   written**. Two entries, one edit; that battery's coverage count had been overstated by one, and
   only `check_anchors.py` refusing a 2-match anchor surfaced it. **Anchor on whole lines,
   including indent.**

⚠️ **The new battery went 5/8 on its first run and all three survivors were real gaps**, including
the seam between the suite that knows the load outcome and the registry that reports it — my tests
passed the status *explicitly* to `BuildSnapshot`, so deleting the production wiring changed
nothing they could see. **Passing a value into the unit under test does not prove anything supplies
it.**

## 5.62 `F-16` closed — and most of it had already been done, which is the finding

`F-16` was the last open `F-` finding: *"MCP tool schema conformance — extract the tool
schema/dispatch table out of `nt-mcp-server.js`, then ONE sweep over all 52 tools. **52 tools, 1
tested.**"*

⚠️ **Re-measured before writing anything, and three of its four clauses were stale:**

| the entry said | measured 2026-08-15 |
|---|---|
| 52 tools | **55** |
| 1 tested | **53 tests**, incl. sweeps titled *"the class, not the four instances"* |
| extraction must come first | **done by `P1-91`** — `mcp/lib/tools.js` has existed since |
| importing the server hangs the test | **still true**, and still the reason to read source text |

This is **`P2-113`'s class inside the tracker itself** ([[a-comment-recording-a-defect-goes-stale]]):
a row recording the *state* of a defect is a claim with no owner, and the three tickets that did
`F-16`'s work had no reason to visit it. **Re-measure an entry before working it** — the cost here
was one command, and without it the session would have re-extracted a module that already existed.

### What actually remained: the JOIN

Every existing test asks whether a schema is *right*. **None asked whether the tool it describes is
REACHABLE.** Those are two files — `lib/tools.js` advertises, `nt-mcp-server.js` dispatches — and
nothing compared them.

That is **`P2-109`'s exact shape at a new site**: there, every component was individually correct
and the defect lived in the line between them. Measured today: **55 advertised, 55 dispatched, both
difference sets empty** — no defect, but an unwatched join on the surface that decides what an
agent can call at all.

⚠️ **The two directions fail differently and only one is loud**, so the test asserts both and says
which is which:

* *advertised, not dispatched* → the call reaches the dispatcher's default branch and errors. Visible.
* *dispatched, not advertised* → **the tool is INVISIBLE**. No client reading `tools/list` can call
  it and nothing reports it. That is **`P1-102` verbatim** (`/api/lockout` existed for months with
  no tool in front of it) and **`P2-103`** (two inventory surfaces with five mutation batteries
  keeping their payloads honest, reachable by nothing — *the honesty was bought and not spent*).

⚠️ It carries a **positive control on the region**: if the case-label regex ever stops matching — a
reformat, a switch replaced by a lookup table — both difference sets go empty and the test passes
**while inspecting nothing**. `assert(dispatched.size > 50)` is what stops that, and it is the fifth
instance of [[state-the-region-a-gate-inspects]] in two sessions.

✅ **Driven negative before being believed**: renaming one `case` label made it fail, naming the
tool; restoring made it pass. A detector that has never been seen to fire is not evidence.

Wrapper tests **53 → 54**.

## 5.63 `P2-114` — CI went red on the `P2-113` push, and both failures were this session's own lessons landing on me

The `P2-78`/`P2-113` code was deployed and live-validated before its CI evidence existed. Both
later pushes then failed the 15-minute matrix, on **two different batteries**, for **two unrelated
reasons** — and each was a lesson written down earlier the same day.

### Failure 1 — `mutate_p182` crashed printing its own output

`UnicodeEncodeError: 'charmap' codec can't encode characters in position 201-202`. A repointed
mutant description had gained a `⚠️`, and `mutate_p182.py` has no `sys.stdout.reconfigure`.

⚠️ **It passed locally and crashed on the runner**, on identical input. And it raised **between
applying a mutant and restoring it**, so everything after that point in the run proved nothing.

⚠️ **`tools/check_batteries_pin_encoding.py` DID NOT EXIST IN THIS REPO** — it lives in
`nt8-mcp-bridge`, while §0 cited it as protecting these batteries. **Fourth per-repo gate gap**
after `check_anchors.py`, `check_ci_runs_every_battery.py` and `check_bridge_parses.py`. Porting it
was one `cp`, and on arrival it failed **56 subprocess captures across 29 batteries**: this repo had
never pinned *either* half, and had survived only because the C# suite's output happens to be ASCII
today. One non-ASCII character in any `Console.WriteLine` would have killed **every battery at
once**.

⚠️ **And the gate had only ever checked HALF the hazard, which is its own lesson restated.** Its
docstring said *"every battery must pin an explicit encoding on its subprocess captures"* and it
enforced exactly that sentence. The sentence was the bug — the hazard is *the battery's encoding
assumptions*, of which the subprocess capture is one:

| half | codec direction | when it fails | consequence |
|---|---|---|---|
| DECODE — `subprocess.run(capture_output=True, text=True)` | child → battery | **before** the first mutant | `stdout` is `None`, battery dies having proven nothing |
| ENCODE — the battery's own `print()` | battery → console | **between** applying a mutant and restoring it | **a live mutant left in the working tree** |

The encode half is strictly worse. Both are now required of **every** battery, not only of ones
that currently carry a non-ASCII character — *a conditional requirement would be satisfied by the
very edit that breaks it*. **State the hazard a gate is for, then check every surface it has**:
[[state-the-region-a-gate-inspects]] applied to a hazard rather than to a file.

✅ Driven negative twice before being believed: removing the pin fails it, and **so does a half-pin**
(`encoding='utf-8'` with no `errors='replace'`), which is the shape that still crashes.

### Failure 2 — a `mutate_ui4` mutant SURVIVED, and §5.61 predicted it

*"rules with no evaluator are omitted from each ACCOUNT's inventory"* — the per-account loop turned
into `i < 0`. It had been killed for the life of the battery **by real unevaluated rules happening
to exist**. `P1-77` + `P1-81` + `P2-113` removed its subject, and a mutant with nothing to corrupt
survives.

⚠️ **That is §5.61's lesson at a SEVENTH gate, and it is the one I missed.** I converted the six
*tests* that scanned that population and did not ask whether the *batteries* did too. The six failed
**loudly**, because each carried an explicit `Count > 0`; this one went **quiet**, and quiet is how
a battery stops being evidence.

**When a fix empties a population, the mutation batteries are gates against it as well as the
tests.** Closed by `TestP2_114_AnUnevaluatedRuleAppearsOnEveryAccountsRows`, which drives the
synthetic registry with two accounts and asserts **both** surfaces — the per-account rows and the
fleet list are filled by two different loops and the battery has a mutant for each.

Suite **1697 → 1705/0**. 31 batteries, both encoding halves pinned, anchors **325/0**.

### Order from here

1. ✅ **`P2-112` closed in session 44** — see §5.64.
2. ✅ **`F-6` shipped in session 45** — Discord push alerts, live-validated; see §5.70.
3. **`P2-29`**'s remainder — the `partial class` split of `RiskGuardAddOn.cs`. ⚠️ **Take this
   BEFORE the remaining features (`F-4`, `F-3`, `F-1`)**, not after: it cuts apart the file
   every one of them would be written into, and `F-6` has just added an outbox queue, a sink
   field and an emission block to it.
4. **`P3-110`** (narrowed — §5.51), then the architectural **`P3-33`**.

⚠️ **Separately: several CLOSED entries have a half that has never been observed on the box**,
each needing one filled contract and therefore a market (futures reopen Sunday 18:00 ET).
They are written up in **§5.70** (alert suppression of a recurring condition; the STALE-guard
heartbeat), **§5.64** (the stop-move half) and **§5.62** (the lockout *admit* half — only the
refusal is live-validated, because nothing on this box can impose a lockout on an account
that already holds a position).

**These are deliberately NOT listed above as work-to-do**, and `check_next_list_ids.py`
refused the first draft of this section for naming their closed IDs there. The gate is
right, and its reasoning is the one to keep: *a remainder hiding under a closed entry is
invisible to every count*. **So if any of these turns out to be more than a confirmation
run, it gets its own ID** — an unvalidated half is not the same thing as an open defect,
but it must not be allowed to become one silently.

🆕 **`nt8-mcp-bridge` now has an agent-loop profile** (`agent/nt8_bridge.py`, profile
`nt8-bridge`), so `F-16` and `P3-110` are reachable by the loop for the first time. Its protected
set includes **`vendor/*`** — an edit to the pinned core there is not a change, it is a silent fork
that `deploy.py` would ship as code existing in no tag, and the stale-pin guard compares a RANGE so
it would not see it either.

⚠️ **Provider31 is still disconnected** from the replay session. Reconnect and **re-verify guard
arming** before treating any funded-account reading as meaningful.

---

## 5.64 `P2-112` closed — and the thing that made it survive was never the logic

**Session 44, v1.29.0.** The 5-second ATM sweep that moves breakeven stops returned early forever
when `Application.Current` had no `Dispatcher`. `P1-13`'s fail-open verbatim, at a subsystem `P1-13`
never inspected, found only when `P2-29` widened that gate from one file to the addon tree.

**The fix is four lines of control flow. The reason it lasted is one preprocessor directive.** The
entire dispatch decision sat behind `#if TESTING`, so the ten existing ATM tests drove
`MonitorTickCore()` — a body the shipped assembly does not contain — and **the branch holding the
defect existed in no test build at all.** So the `#if` was shrunk to wrap only the WPF lookup
(`TryMarshal`, a `Func<Action, bool>`); the control flow now compiles into both builds and the tests
drive both branches through that seam, by **reflection into the real private `MonitorTick`** rather
than through a new `#if TESTING` hook. A hook would have been a second door production never takes,
which is the arrangement that hid this.

⚠️ **The entry's own suggested remedy was not implementable, and reading the code is what showed it.**
It said *"marshal only the `Account.Change()`"*. `Application.Current == null` means there is no WPF
application object and therefore **no UI thread anywhere in the process** — there is nothing to
marshal to. The choice is between running the sweep on the timer thread and not running it. It is
also safe in the way that matters: the race worth fearing is with a UI-thread broker call, and this
path only executes when no UI thread exists.

### The agent loop: `MAX_ROUNDS_EXHAUSTED`, and that was the right answer

Round 2 passed **every** gate — static, compile, `1720/0` with all four acceptance tests green,
lock-scope — and the panel returned `REVISE` on `deepseek-v4-flash=REJECT(4)`. Rounds 3 and 4 acted
on it and got **worse**: round 3 reverted the whole region and regressed 3 tests; round 4 failed
static. The harness exported round 2 as *"the last candidate that passed every gate"*. **That is the
tool working. `NOT_CONVERGING` / `MAX_ROUNDS_EXHAUSTED` means arbitrate by hand, not that the patch
is bad.**

**Of the arbiter's three upheld findings, exactly one was real — and I had missed it.**

| # | ruling | actually |
|---|---|---|
| 1 | tests never drive the production dispatcher branch | **wrong** — the tests *assign* `TryMarshal`, so `_ => false` is only a default. Read the addon, not the test file |
| 2 | fallback runs broker calls on a timer thread; *"fail safe (disable the monitor) or marshal to a safe thread"* | **wrong, and it recommends the defect** — "disable the monitor" **is** `return;`. Also self-contradictory: the race it describes needs a UI thread this path exists because there isn't one |
| 3 | the once-per-session flag is instance-scoped | ✅ **right** |

⚠️ **Finding 3 is worth carrying.** The flag guards a message that says *"once per session"*, and
instance scope made that true only by leaning on the `Lazy<>` singleton three hundred lines up — an
invariant enforced somewhere else, which is how **a log line starts describing something it did not
observe**. Now `static`, and **driven negative before being believed**: with an instance field the
second manager announces again and the test reports `got 2`.

### The battery caught its author, for the third recorded time

A mutant flipping `TryMarshal`'s null branch to `return true` — the caller then believes the work is
on the UI thread and skips it, `P2-112` restored one level down — **survived all 1722 tests**. Not a
coverage gap: it lives behind `#else`, which no test build compiles, so it is **unkillable by
construction**. **Read what a mutant DOES before calling it a missing test** (`P1-99`, then
`P3-111`, now this). Covered by a **labelled** source gate plus `nt_compile`, and the label is the
point — those four lines can never be executed by any test, and a source gate proves less. It
strips comments before searching, because the prose above the seam explains `return false` and **a
gate its own documentation can satisfy is not a gate**.

⚠️ `tools/check_expected_survivors.py` **fired on the battery's first draft**: I hand-rolled the
expected-survivor bookkeeping rather than calling `_battery.finish(survivors, MUTANTS)`. A second
implementation of a verdict is a second thing to drift, and the gate exists because that already
happened once.

### Live: the reachability half is DONE; the stop-move half is not

✅ **Reachability, which this entry demanded and nobody had ever measured**:
`ATM_MONITOR_NO_DISPATCHER` occurs **0 times in the whole of `interventions.jsonl`** after deploying
v1.29.0 and driving the monitor. With the GUI running the dispatcher is non-null and the fallback
never fires — the defect was **latent, not active**, which is what the `P2` band rested on.

✅ **The sweep runs on the deployed build.** A `DrawdownShield` bracket on Sim101 came back
*"registered for breakeven/trailing monitoring"* and was **gone thirty seconds later**; the only
code that removes a bracket is `MonitorTickCore`'s `toRemove` path.

⚠️ **NOT validated: the breakeven stop MOVE.** The entry never filled — all three orders sat at
`OrderState.Initialized` — because **NT8 is on the `Playback` connection with no replay running**,
which is §5.56's warning arriving. So `Account.Change()`, the call site that made this entry defer
in the first place, is **still unexercised here**. To finish: start a replay or reconnect
Provider31, place the same bracket, read `ATM_STOP_MOVE_REQUESTED` → `ATM_STOP_MOVE_CONFIRMED` or
`ATM_STOP_CHANGE_IGNORED`.

⚠️ **`breakevenTriggerTicks: 0` is the technique to keep.** `ShouldTriggerBreakeven` is
`ticksGain >= BreakevenTriggerTicks`, so `0` fires on the first sweep at the fill price. The
breakeven path is drivable **without a moving market** — this entry's recorded blocker was never
really the market, it was the *fill*.

⚠️ Incidentally confirmed on the way past: `nt_close_position` answered `nothing_to_close` with
`positionsMatched: 0` and `cancelledOrdersCount: 3`. That is `P1-105`'s fix behaving — it did not
claim a close it had not made.

### 🆕 `P2-115` — `feedConnected` is `Account.All.Count > 0`

Found while answering *"does Provider31 need market data or just a broker connection?"*. The health
endpoint's `feedConnected` is `accountCount > 0` (`nt8-mcp-bridge/addons/McpBridgeAddOn.cs:447`) — a
running NT8 always has Simulator accounts, so **the field has exactly one reachable value**. It is
not a weak measurement of the feed; it is not a measurement of the feed.

⚠️ **The cause of the stale quotes turned up later and makes it sharper.** NT8 is on the session-42
`Playback` connection **with no replay running** — §5.56's warning arriving — so the box has no
tradeable market at all, and three ATM orders sat at `Initialized` and were never routed. Through
all of it `feedConnected` said `true`. The defect is not *"wrong while Provider31 is off"*; it is
that **the field cannot tell a live feed from a dormant Playback connection, because it looks at
neither.** Reconnecting anything will not close it.

⚠️ **It misled the agent investigating it, in writing, within five minutes.** I read
`feedConnected: true` beside 90 accounts at `cashValue: 0` and stated that market data was connected
and only the account half was missing. The code half of that answer was right and independently
sourced; the observational half came from this field and was wrong. **That is the consequence
argument** — it is the field consulted precisely when someone is about to trust a price.

**And the answer to the original question, which the code settles independently**: a **broker
connection** is what is needed. The guard's entire input is broker-pushed account items —
`CashValue`, `RealizedProfitLoss` (`RiskGuardAddOn.cs:210`, `:776`, `:5239`). Market data enters
only via `UnrealizedProfitLoss`, and only while a position is open.

---

## 5.65 The broker came back, and the guard is protecting ONE account out of eighty-nine

**Session 44, immediately after §5.64.** The operator reconnected Provider31 with the market closed
and said to test everything else. The first measurement is the one that matters and it had never
been possible before, because with Playback connected every account read `cashValue: 0` and that was
attributable to the connection.

| | |
|---|---|
| accounts | **97** — 89 Provider31, 6 Simulator, 2 Playback |
| Provider31 reporting **any** equity | **1** — `TAKEPROFITPRO524207503`, $50,182.75 |
| Provider31 with **any** per-account guard event, ever | **0** |
| `ConfiguredNotEvaluated` | **0** (sessions 42-43's fixes hold on real accounts) |
| `ruleRows` | 2,231 across 97 accounts |

✅ **What is genuinely good, and could only be checked now.** The funded account reads correctly
end to end: `accountEquity: 50182.75`, `Firm trailing drawdown` **"resolved to plan `TPT-50K-PRO`;
its TrailingDD numbers are in force"** with limit `2000`, and `Firm daily loss` **`Disabled`** with
*"plan `TPT-50K-PRO` has NO daily loss limit, which is that firm's actual rule -- not an oversight"*.
That is `F-9`/`F-9b` working against real equity on the funded 50K for the first time. An Apex
account resolves to `Apex-50K-EOD` with **both** sub-rules in force, which is the other half of the
plan-not-firm distinction paying off.

🆕 **`P2-116`, and it is the largest thing measured today.** The other 88 accounts report
`Trailing drawdown: EvaluatedNotEnforcing, currentValue 0.0, limit 1500` — **byte-identical to the
funded account except the number**. The evidence count is `c.Account == null ? 0 : 1`
(`GuardRules.cs:265`): the existence of a state OBJECT, not of an equity READING. And the rule is
structurally incapable of firing on them, since `PeakEquity` stays `0` and the breach test is
`0 < -1500`.

⚠️ **The author knew this class and applied it eight lines below.** The aggregate cap carries
*"An aggregate cap over ZERO known accounts is not enforcing anything, and would otherwise read as
green."* The identical reasoning never reached the per-account equity rules — **a second reader that
was never told, at a fourth site.**

⚠️ **Banded `P2` on a MEASUREMENT, not on a reading of the code**: the enforcer runs from
`AccountItemUpdate`, and the audit log shows **zero per-account events for any Provider31 account**,
so there is no spurious flatten. That is an observation about today, not an invariant — one equity
push would set `PeakEquity` in the same call and the next tick could breach legitimately.

⚠️ **`P2-115` got its cheapest possible confirmation on the way past.** `feedConnected` read `true`
with a dormant Playback connection and no market at all, and reads `true` now with a live broker.
**It did not change value when the thing it names changed completely.** Meanwhile `MNQ 09-26` went
from a frozen `29533.75` to a live book at `30151.75 / 30155` on 1,925,425 volume — an 618-point gap
that had been invisible behind a green flag.

⚠️ **Still not measurable, and say so**: `P2-112`'s stop-MOVE half. The market is closed, so nothing
fills, so `Account.Change()` is still unexercised on the ATM path. It needs one filled contract on
an open market — with `breakevenTriggerTicks: 0` that is the *only* remaining requirement.

---

## 5.66 A battery that passed 9/9 locally scored 2/9 in CI — a local worktree is not a fresh checkout

**Session 44.** `mutate_p2112.py` was green locally, `check_anchors.py` printed **334/0**, and CI
failed the `P2-112` job on **two consecutive pushes** with seven of nine anchors reporting
`[SKIP] anchor matched 0 times`. The two that matched were exactly the two **single-line** anchors.

### The cause

`ORIGINALS = {p: open(p, encoding='utf-8', newline='').read() ...}`.

`newline=''` hands back the file's **real** line endings. Every `.cs` blob in this repo is **CRLF**,
so a fresh checkout gives CRLF, while the anchors are written with `'\n'`. Every multi-line anchor
therefore matches nothing. **Exactly one battery of 32 read that way** — this one. I had copied
`newline=''` off the *restore* line, where it is correct (it stops Python translating on the way
OUT), onto the *read*, where it silently decouples the battery from its own anchors.

### ⚠️ Why it passed locally, which is the part worth carrying

**Earlier battery runs had already rewritten the worktree copy to LF.** Every battery reads
universally and writes with `newline=''`, so restoring a file normalises it. My working tree had
been through several runs; CI has only ever seen a fresh checkout. Proven rather than argued —
`git clone --depth 1` into a temp dir, then match the anchors both ways:

```
fresh checkout CRLF lines in target: 1011
anchors matching with newline='' (the bug): 2 / 9      <- exactly CI's number
anchors matching universal (the fix)      : 9 / 9
```

⚠️ **`git show HEAD:<file>` lied about this and cost twenty minutes.** It reported the blobs as LF
because it applies the eol filter. **`git cat-file blob` is the raw bytes** and reported all three
addon files as fully CRLF. When a question is about bytes, use the plumbing command.

### ⚠️ And `check_anchors.py` was validating a different string

It reads targets with **universal newlines**, so it matched anchors against `'\n'` text and reported
them fine — while the battery, reading with `newline=''`, would search CRLF text. **The gate and the
battery disagreed about the input, so the gate's 334/0 was true about a string no battery searches.**

Remedy, and it is the class rather than the instance: `check_anchors.py` now **refuses any battery
that reads its ORIGINALS with `newline=''`**, because that is precisely the condition under which
its own evidence stops being about the same text. Watched failing on the real defect before the
defect was fixed (`326 anchor(s) checked, 1 broken`), then green at **334/0**.

**This is [[state-the-region-a-gate-inspects]] with a new axis: not the region, the DECODING.** Two
readers of one file that differ only in how they translate line endings are two different readers,
and the one with the gate attached was not the one doing the work.

### The side effect that made this possible, recorded but deliberately NOT changed

Every battery reads universally (`'\n'`) and writes with `newline=''` (verbatim), so **restoring a
file rewrites it from CRLF to LF**. That is the fleet convention, it is why a worktree drifts away
from a fresh checkout, and it is invisible in `git status` because `core.autocrlf` normalises the
comparison. Changing 32 batteries to preserve endings would be a larger and riskier edit than the
problem justifies — the committed blob stays CRLF either way. **Know that running a battery mutates
your worktree's line endings**, and do not use the worktree as evidence about a checkout.

⚠️ **`_battery.finish` did its job**: a `(ANCHOR)` skip is scored a survivor and failed the build
rather than passing quietly. The cost was two red CI runs, not a false green — which is the
arrangement working. But it is the second time this session that **a check run before the last edit
was a check on something else**; the first was `check_next_list_ids.py`, run before the status edit
and not after.

---

## 5.67 `P2-115` closed — the arbiter recommended SHIP on code that would not compile

**Session 44.** `/api/health`'s `feedConnected` was `Account.All.Count > 0`: true on every running
NT8, forever. Measured `true` against a **dormant Playback connection with no tradeable market at
all**, and `true` again an hour later with a real broker on a live MNQ book. **It did not change
value when the thing it names changed completely.**

Now `addons/BridgeFeedStatus.cs` — `IsMarketDataConnected(names, providers, statuses)` over three
plain string arrays. That shape is the design: it names **no NinjaTrader type**, so it lands in the
set the harness can *execute* rather than the set it can only read as text.

### ⚠️ The headline: every gate was green and the patch had two compile errors

The loop returned `ARBITER_SHIP` with **0 of 4** findings upheld — the documented pattern — on a
patch containing `a.Provider?.ToString()` and `a.Connection?.Status?.ToString()`. **`Provider` and
`ConnectionStatus` are enums**, so `?.` is `CS0023`; the addon already writes
`account.Provider.ToString()` at `:1771` and `:4590`. Static ok, compile ok, 314 passed, all six
acceptance tests green, lock-scope clean — **and not one of them could see it, because
`McpBridgeAddOn.cs` is in no test build.**

That is `P2-27` arriving exactly where this repo's agent-loop profile header warns it will, and
`check_bridge_parses.py` prints the caveat in its own output: *"This is NOT a compile — type errors
are out of scope by design. Run nt_compile before calling a bridge change done."* **Read the caveat
your own gate prints.** Also fixed by hand: the patch's `Print(...)`, which is `NinjaScriptBase`'s
method, not this file's `NinjaTrader.Code.Output.Process` convention.

### The battery went 5/10, and four were gaps in tests written the same hour

| survivor | why the tests missed it |
|---|---|
| `return true` on **null** arrays | every assertion passed a real array — **an empty array is not a null array** |
| a **blank provider** admitted as real | every assertion passed a *named* provider |
| the **shortest-length clamp** removed | nothing in the suite was ragged |
| the source gate | it asserted the class is **mentioned**, not that its answer is **assigned** |

⚠️ **The fourth is the third instance of that exact gap** (`P1-105`, `P2-109`, now here) — and the
comment directly beneath the assertion *already said* a value that is computed is not a value that
is used. **I wrote the warning and shipped the weaker check anyway.**

⚠️ **The fifth survivor was the author's**: a **case-sensitive** `Contains("Connected")` mutant.
`"Disconnected"` does not contain `"Connected"` with a capital C, so it never expressed its own
defect and no test could have killed it. Fourth instance of *read what a mutant DOES before calling
it a missing test*.

⚠️ **And the re-run still left one**, for a reason worth keeping: the ragged test made *providers*
the shortest array, so removing the **statuses** clamp changed nothing. **Each clamp needs the array
it guards to be the one that would overrun.** Now **10/10**.

⚠️ **Mutant 5 is the one to carry: a bare `return false`.** Every requirement here is about a TRUE
that cannot become false, so a constant `false` satisfies all of them and ships a permanent-outage
report on a working box. **A status field needs both directions, not only the one its defect was
in.**

### Evidence, and which half is NOT measured

Bridge harness **311 → 324/0**, MCP wrapper **54/0**, battery **10/10** and wired into CI (7
batteries), all four bridge gates green, `nt_compile` **errorCount 0**.

⚠️ **The class has four executed assertions in both directions. The WIRING has a source gate, a
clean compile, and a live `feedConnected: true` — a positive control ONLY, because `true` is what
the defect produced too.** Showing `false` live needs the operator's broker disconnected and was not
done. Say which half was measured.

### 🆕 And the tool itself had to be fixed first — `agent-loop` v0.6.7

The first run died with *"baseline test run produced no parseable result summary"*, which reads as
*the consumer's output is malformed*. The real cause was `agent-loop`'s own `gates._run`:
`subprocess.run(..., text=True)` with no encoding decodes as **cp1252** on Windows, and this
harness prints two `⚠️` assertion messages. One byte `0x8F` killed the reader thread. **This repo
had never once been runnable by the loop and nothing said so.**

Ten capture sites pinned with `encoding='utf-8', errors='replace'`, plus an **AST gate** that walks
every capture — it found **two sites a grep had missed**, one a `tasklist` **liveness probe** that
could throw. Three things the fix taught, all now in the test: **`U+26A0` alone does not reproduce
it** (its bytes are all defined in cp1252 — it is the variation selector `U+FE0F` that carries the
undecodable `8F`); **the unpinned form does not RAISE in the caller** (the reader thread dies and
`stdout` is silently `None`, which is why it is invisible from outside); and `selftest.py` carries a
**BOM**, so the gate reads `utf-8-sig` and **fails on any file it cannot parse rather than skipping
it**. Suite 633 → **636**. That is the **third repo** in this encoding class, after both consumers.

---

## 5.68 `F-17` — connection control, and the negative half that arrived on its own

**Session 44, at the operator's request** while confirming `P2-116`: *"you should be able to check
the broker disconnect. In fact I think this is a good addition to the MCP."* Both halves of that
turned out to be one piece of work.

### ✅ `P2-116` is CONFIRMED, and the confirmation is recorded rather than assumed

*"There is only one live account and the rest 88 are dormant evals."* So **no account is going
unwatched** — the guard is not failing to protect 88 live accounts, it is correctly holding no
reading for 88 dormant ones. The defect is entirely in the REPORTING, and the `P2` band stands.
⚠️ **Do not let the confirmation shrink the fix**: *"they are dormant"* is a fact about the
broker's population today, not about the code. The day an eval is funded its rows look identical to
the 87 beside it **and identical to how they looked while it was dormant**.

### 🆕 `nt_connection`, and `addons/BridgeConnectionPlan.cs`

`status | connect | disconnect`, over `GET/POST /api/connection`. Every row carries
`countsTowardMarketData` from **the same predicate `feedConnected` uses**, so the detail view and
the flag cannot disagree about the same connection — the `F-9` rule, applied before it could bite.

⚠️ **`disconnect` is destructive and is refused by default.** It severs the path by which a position
is managed, which is `P1-106`'s family exactly. `WouldStrand` names what it would abandon, and
reports **positions and working orders separately** — a resting stop stays live at the broker after
the connection drops and can then be neither moved nor cancelled. `confirmDisruptive` is the
deliberate override.

### ✅ And it completed `P2-115` without the disconnect ever being performed

| when | state | reading |
|---|---|---|
| 14:20 | dormant Playback, no market | **old** code → `true` (defect) |
| 14:54 | live broker | **new** code → `true` (positive control) |
| 16:49 | broker dropped on its own | **new** code → **`false`** (negative control) |

`accounts: 97` identical throughout. ⚠️ **The reading I had refused to take arrived for free.**
Showing `false` meant disconnecting the operator's live broker, so it was declined and written up
as unmeasured — and then the market closed and the box produced the state anyway. **When a
measurement is blocked on an action you should not take, say so and keep watching.**

### ⚠️ Four defects, all found by compiling and driving the box, none by reading

* **`/api/connections` already existed** — returning OCO capability flags. Two unrelated concepts
  under one plural noun, caught only as `CS0152`.
* **`Connect` is STATIC and takes options** (`CS7036`, then `CS0176`); `Disconnect` is an instance
  method. The two halves of one API are not symmetric.
* ⚠️ **`Connection.Connections` returns ZERO rows from the AddOn's HTTP thread** — the very
  enumeration NinjaTrader's own `@BarTimer` indicator performs. The endpoint answered
  `count: 0, marketDataConnected: false` on a box with a live broker attached: **a false negative of
  exactly the kind `P2-115` exists to remove, one endpoint away.** Now sourced from the accounts'
  own `Connection` references, which persist across a disconnect.
* ⚠️ **Grouping by `Options.Name` merged a live broker connection into a dormant one** and reported
  the dormant one's status for both — while `/api/health` said the opposite in the same breath.
  Two answers, and the report was the wrong one. **Reference identity is the only key that cannot
  do that**, the same rule `BridgeFlattenPlan` uses to tell its own order from someone else's.

### ⚠️ The battery beat a source gate for the FOURTH time — in the gate written to avoid the first three

| the gate asserted | the mutant that beat it |
|---|---|
| `P1-105` | the resolver is **called** | keep the call, ignore the answer |
| `P2-109` | same shape at the next site | — |
| `P2-115` | the class is **mentioned** | keep the call, hardcode the flag |
| `F-17` | the refusal is **returned near the call** | neuter the condition to `if (false)` — the `return` stays in the text, unreachable |

**A regex over source text cannot see reachability.** On a guarded return **the condition is the
load-bearing part**, and it is the only thing a mutant has to touch. The gate now asserts the
condition names both `strands` and `confirmDisruptive`, keeps the return assertion alongside it
(either alone is satisfiable without the other), and carries a **negative control that must FAIL on
the mutant's own shape** — a positive control only proves the regex still matches something.

**Evidence**: harness **324 → 345/0**, wrapper **54/0** (the exact-count gate fired 55 → 56 as
designed, its fourth catch), `mutate_f17.py` **10/10** wired into CI (**8** batteries), anchors
**84/0**, all four bridge gates green, `nt_compile` **errorCount 0**.

---

## 5.69 The §0 defect count was hand-patched, and listed six closed defects as open

**Session 44, found by the operator asking "are the documents updated?"** — which is a better gate
than any I had pointed at this.

§0's `Defects` row read **122 IDs — 109 closed, 13 open** and named `P1-77`, `P1-81`, `P2-78`,
`P1-102`, `P2-108` and `P2-112` among the open. **All six are closed**, four of them in the two
sessions immediately before. The row had been *patched* each session rather than re-derived, which
is exactly the failure its own neighbouring note warns about: **a half-updated summary is worse
than an obviously stale one, because the timestamp at the top vouches for every row.**

### Re-derived, and how

| | |
|---|---|
| banded plan entries | **115** — 108 closed, **7** open |
| open | `P2-116`, `P3-110` (narrowed), `P3-33`, plus `P0-9`, `P1-13`, `P2-27`, `P2-29` PARTIALLY CLOSED with recorded remainders |
| untriaged `P?-` | **3**, all closed |
| `F-` findings | **9** (`F-9`…`F-17`), all closed |
| **total** | **127 IDs — 120 closed, 7 open** |

⚠️ **A `grep CLOSED` GETS THIS WRONG, and I wrote one before catching myself.** Headings legitimately
use `FIXED`, `RESOLVED`, `SUPERSEDED`, `HALF CLOSED` and `PARTIALLY CLOSED`, so a substring scan
reported `P0-96`, `P0-67`, `P0-68` and the whole `P1-69`…`P1-76` block as OPEN when every one is
closed. **Derive it with `check_next_list_ids.py`'s own `entry_status`**, which is the function the
gate already trusts — importing that is the difference between a number and a guess. This is
[[closures-do-not-propagate-backwards]]'s own rule (*never detect status by substring*) applied to
the counting rather than to the ordering.

### ⚠️ Why the gate did NOT catch it

`check_next_list_ids.py` was green throughout, correctly: it polices *the ordering lists* against
*entry status*, and both were consistent. **It has never audited the §0 count**, which is a third
surface nothing reads. The ordering lists are maintained by the act of doing work; the count is
maintained only by someone choosing to redo it.

**The cheap fix is not another gate but a habit**: the count row now records the command that
produces it, and the derivation above is reproducible in one paste. Anything that cannot be
re-derived in a paste will drift again.

----

## 5.70 `F-6` — push alerts, built by NOT building the transport, and the flood it produced on day one

The operator's feature list has asked for Discord/Telegram push alerts since 2026-08-13
(§5.17 item 6: *"Absent, and there is no outbound HTTP at all."*). It is now shipped and
live-validated with the market shut, in two commits plus a fix.

### The design decision, which was to write less code

The plan was a C# transport inside the AddOn: background thread, bounded queue, hard
timeout, 429 backoff. Reading the delivery code that already exists in `tvDownloadOHLC`
(`scripts/libs_py/discord`, ~2,000 lines) killed that plan, and the reasons are worth
keeping because they are the argument for looking before building:

* a **1900**-character cap rather than 2000, for JSON code-point expansion
* the ~**5 msg / 2 s** per-webhook rate limit
* `Retry-After` read from the **429 header** rather than guessed
* capped exponential backoff on 429/5xx, embed→text fallback
* delivery **telemetry**, which exists there because *"operators had logs to read but no
  aggregate counters"* — this repo's own "a green that can never be red", already learned

So the seam moved. **The guard DECIDES** (`GuardAlertSink`, 11/11 mutants) and appends to
`alerts_outbox.jsonl`; **a separate Python process delivers**
(`scripts/riskguard/alert_relay.py`). No NT8 thread ever touches a socket, which deletes the
entire hazard class the C# transport was being designed around — the same reasoning that
made the bridge's connect path refuse a bare `Dispatcher.Invoke`.

⚠️ **A separate FILE, not another `LogEvent` line.** Emitting the decision through
`LogEvent` would re-enter the sink from inside itself. A separate outbox makes that
recursion structurally impossible rather than guarded against, and the relay then parses
only DECIDED alerts instead of re-implementing the filter on the far side, where it would
drift from this one.

⚠️ **There is no webhook URL in this process at all.** The addon publishes its config over
HTTP on :7890, so a secret stored here is a secret published. The URL lives with the relay,
in `discord_webhooks.json`, and never enters NT8 — strictly better than redacting it on the
way out, because there is nothing to redact.

### ⚠️ The feature produced the exact flood it was built to prevent, within the hour

Sixteen identical `ARMED_ON_START` alerts reached the channel. **Two things were wrong and
only one is about severity:**

1. **The budget resets on an assembly reload**, because it lives in the sink instance and
   NT8 constructs a new AddOn on every recompile. A second agent was compiling in the
   bridge repo at the time, and `nt_compile` rebuilds the **whole** Custom assembly — so
   sixteen reloads each spent a fresh "1 of 1". Recorded as a **known limitation**: within
   one session a repeating condition is still suppressed correctly, which is the case that
   matters in production, where recompiles are rare and a genuine restart IS news.

2. **Arming is not a risk condition.** It is a lifecycle statement — the guard came up and
   is watching, the GOOD outcome — so pushing it at `warning` notified the operator, on
   every reload, that nothing had gone wrong. It is `info` now, below the shipped floor.

⚠️ **`DISARMED` deliberately stays a warning.** The symmetry is tempting and wrong: a guard
that stopped guarding is a change in protection, and it is exactly what you need to hear
while assuming you are still covered.

Live-validated after the fix: a reload at 21:55 produced **no** outbox entry while
`interventions.jsonl` kept recording at 21:55:09. **The audit record still has everything;
the phone does not.**

### Four more defects, three of them mine

⚠️ **The severity floor was fail-OPEN.** `RankOf` answers 0 for any unrecognised string and
the test was `severity < floor`, so a floor of `"warn"`, `"Warning "` or `"off"` ranked 0,
nothing was below it, and **every event in the audit stream** became a push. `MinSeverity`
is hand-edited JSON, so a typo is the *expected* input. `FloorRankOf` falls back to
`warning`; `info` still works because it is a RECOGNISED name. `Enabled` is a separate gate
for the same reason — there is deliberately no `"none"` rank to smuggle through.

⚠️ **`Encoding.UTF8` writes a BOM, and it cost the first alert of the first outbox.** The
file began `EF BB BF {"timestamp_utc"…`, the relay's `json.loads` refused the line, and the
first record of every new outbox was lost — the first record being, by construction, the one
announcing that something started going wrong. Now `new UTF8Encoding(false)`.
**It surfaced in one run only because the consumer LOGS what it skips**; a relay that
quietly ignored the line would have dropped it forever and reported itself healthy.

⚠️ **`KeyOf` had no separator**, so account `AB` + event `C` shared a budget with account
`A` + event `BC`. Found by writing the battery, not by reading the line, and not by ten
green tests.

⚠️ **And in `tvDownloadOHLC`:** `load_webhook_url(key)` returned `None` with no `repo_root`,
while the **deprecated shim it replaces** derives the root from `__file__` — so *following
the deprecation notice silently broke webhook lookup*, and the sender then skipped with
`False`. Two readers of the same state that nobody had compared. The test asserting the old
behaviour was **inverted, not deleted** (it was not wrong about the code, it pinned the
defect), and the real regression guard is the new test that both APIs answer identically.

### The relay must RUN, and that is now the operator-facing risk

`launch/start_alert_relay.bat` restarts the relay on any exit **except code 2**, which is
its "this is configuration and restarting cannot fix it" signal (no webhook, unknown
transport) — without that distinction the keep-alive loop becomes an infinite respawn that
looks busy and delivers nothing. `launch/register_alert_relay_task.ps1` registers it at
logon and **refuses to register a task that cannot work** (missing webhooks file or absent
channel), because Task Scheduler reports "last run: success" for a process that exited
immediately.

⚠️ **Verify by the HEARTBEAT, not by the task state.** The relay posts a periodic liveness
message that also reports the guard's own freshness from `heartbeat.txt`, so *relay down*
and *NT8 down* are distinguishable rather than merged into one silence. This is the answer
to the failure the architecture introduces: **you cannot detect silence**, but you can
detect a missing heartbeat.

### Not validated live

* suppression of a **repeating** condition (needs one that recurs — `NAKED_POSITION` needs a
  fill, so this waits for the market)
* the **STALE-guard** heartbeat path
* SMS-on-critical via `email_notify.py` (built into the plan, not yet wired)
* **Telegram is `NOT_IMPLEMENTED`** and refused BY NAME — an advertised transport that does
  nothing is `P1-72`, which has regressed twice.

---

## 5.71 Sessions 46-47 — the mutation matrix stopped being the slow part, and the box was finally compiled

Two sessions went undocumented, which is how a §5 file loses its authority: §0 was already
stale by many sessions, and the newest `Order from here` was §5.63's. Recorded here in one
block. **Session 46's work is described from its commits and was not re-measured in session
47** except where this section says otherwise; everything under session 47 was measured.

### Session 46 — the suite was the slow half, and nobody had re-checked

`de3e2b3` profiled the suite for CI speed and found **two `Thread.Sleep`s**: 1050ms outlasting
a trade-count debounce, 2200ms outlasting the `InFlightLedger` timeout. **3.25s of a 6.4s
suite** — and CI runs the whole suite **once per mutant**, ~660 times per full run, so those
two lines were roughly **36 minutes of every green CI run**. Replaced with an injected clock:
test run **6410ms → ~2600ms**, per-mutant cycle **~10.8s → ~6.2s**.

⚠️ **The clock injection is evidence first and speed second**, which is the part to carry.
*"After 2.2 real seconds something had expired"* cannot test the **boundary**, races a loaded
runner, and has to be padded for exactly that reason. Both tests now drive the clock and assert
the boundary, and both gained a **negative control they could not previously express** — at
1.999s the ledger entry SURVIVES, at 900ms a re-entry is still the SAME trade. Without those,
*"expires"* passes for a ledger that purges on sight and *"counts a second trade"* passes for a
debounce that never suppresses anything. Suite **1774 → 1776**: faster **and** strictly more
asserted.

⚠️ And **all four** clock reads in `AccountState` were routed through the injected source, not
just the one the test needed. Routing one would give the class TWO clocks — a fake one for the
debounce, the real one for the cooldown and both transition stamps — and **a half-injected
clock IS a second reader of the same state that nobody compared**, the most repeated defect
shape in this repo (`P1-100`, `P2-98`/`P1-99`, `P1-105`, all closed). Same for `InFlightLedger`'s
three.

`bc6927c` advanced **`P2-29`**: 26 independent types moved out of `RiskGuardAddOn.cs` into
`addons/RiskGuardModels.cs`, **6,334 → 5,612 lines** plus a 957-line file. ⚠️ **This is NOT the
recorded remainder and `P2-29` does not close.** The remainder on record is the `partial class`
split of `RiskGuardAddOn` **itself**; there is still no `partial class RiskGuardAddOn` anywhere
in `addons/`. The remainder shrank — read the entry, not the commit count.

### Session 47 — packing, measured

`6564fe2` had already established the shape of the problem at 33 batteries: **the floor is no
longer the longest battery, it is `total_compute / slots`.** 33 jobs against ~20 concurrent
slots meant 20 waited, worst 375s, so ~5 of 16.5 minutes was pure queueing that **grows with
every battery added** — the sharding that made this fast at 24 had started working against
itself. `de3e2b3` shipped `tools/pack_ci_matrix.py` and **deliberately did not apply it**,
because the only measured weights predated the speedup and batteries with more mutants shrink
more. Run `31914385667` is that measurement, so session 47 applied it.

| | before (33 shards) | after (20 bins) |
|---|---|---|
| wall | 13m25s (`31914385667`) | **10m59s** (`31922684732`) |
| job time | 10,044s | 9,178s |
| queued | **13 of 33**, worst 375s | **0 of 20**, all starting within 3-6s |

**Three things in it are reusable, and only one is about CI.**

**1. A measured job duration is not a weight.** Each includes ~31s of setup that a packed bin
pays **once**, and the error is **not uniform** — it inflates a 2-battery bin by 62s against a
singleton's 31s, so packing on raw times systematically UNDER-fills the packed bins. That is
the same *"looks balanced and is not"* the tool already refused for **missing** weights: a
weight wrong by a known constant deserves the treatment of one that is absent. Corrected, the
plan named its own floor — and the floor held: **UI4 measured 505s of work in a 551s bin, and
`checks` 97s + UI4 551s is 10.8 of the 10.99 minutes.** Re-binning cannot move that number.

**2. ⚠️ PACKING RE-CREATED A HAZARD SHARDING HAD REMOVED, AND IT FAILS GREEN.** A battery
mutates shared `.cs` in place and restores at the end **with no `try`/`finally`**, so one that
dies mid-mutant leaves a live mutant. With a checkout each that was contained inside one
already-failing job. Sharing one, the next battery in the bin compiles against mutated source —
and reports **KILLED**, because *a mutant already in the file is one the "unmutated" baseline
contains too*. Same class as the killed local batch that left a live `mutate_cm4` mutant on
2026-08-14. The run step now asserts the tree is clean after each battery and **stops the bin**
if it is not: a missing answer is recoverable, a false green is not. Driven all three ways
before being trusted — clean `rc=0`; **a survivor does NOT abort the bin** (aborting would undo
`fail-fast: false` inside every job) `rc=1`; a crash leaves a mutant and the next battery never
runs `rc=2`. **When an optimisation removes an isolation boundary, name what that boundary was
silently providing.**

**3. Packing is a one-way door without per-item times.** Once batteries share a job,
`gh run view` reports the **bin's** duration and per-battery weights are unrecoverable — and
`pack_ci_matrix.py` refuses to pack without them. The run step prints `BATTERY_SECONDS` per
battery; **verified present for all 33** in the first packed run, which is the check that
matters, not the code that emits it.

⚠️ `--ignore-cr-at-eol` on that clean-tree assertion, because the blobs here are CRLF and
`core.autocrlf` is true. Clean both ways locally — but **a local worktree is not a fresh
checkout** (§5.66), and a false FAIL would abort all 20 bins on an environment difference. It
cannot cause a false pass: a live mutant differs by real text, never by carriage returns.

**The gate.** `check_ci_runs_every_battery.py` was rewritten for `batteries:` and **deliberately
does not match the old singular `battery:`** — that entry stopped *running* anything the moment
the run step became a loop, so still matching it would report a battery as wired that CI never
executes, **this gate's own original defect one shape later**. It also asserts the list is
**consumed**, because a gate that a value is COMPUTED is not a gate that it is USED, and it now
fails on a battery wired but absent from disk. **Made to fail on purpose seven ways** before
being trusted, per this workflow's own header rule. The per-battery prose was **moved, not
dropped** — verified by diffing the comment multiset against the re-read file rather than by
trusting the writer; the only two lines lost were the stale "ordered longest first, seconds from
run 31768033709" region header, which was itself false.

### The state audit that opened session 47, and what it found

`gh run list` first, per the standing rule. It earned its five seconds:

* ⚠️ **`nt8-mcp-bridge` CI was RED on `origin/main`**, and not because of a defect — the fix
  (`1e73c4a`) was **committed locally and never pushed**, so the newest recorded state of that
  repo was a failure that had already been repaired. Anchors read 86/0 locally the whole time.
  Pushed in session 47; harness 394/0, wrapper 54/54, all three of its gates green.
* ⚠️ **`tools/check_expected_survivors.py` did not exist in `nt8-mcp-bridge`** — the **fourth**
  gate found present in one repo and absent in the other. It had **no subject there** (no bridge
  battery declares an `EXPECTED SURVIVOR:`), so its absence cost nothing yet; the first
  declaration would have arrived ungated, which is how this class always presents. **Ported in
  session 47 and wired into that repo's CI** — see §5.72 for why the port was not one `cp`.
* The **vendored pin** had gone 14 commits stale with 5 touching `addons/`, so `deploy.py`
  refused — correctly. Tagged and advanced in session 47.

### ✅ The box was compiled, and three things were confirmed live

The operator compiled NT8 in session 47. **`NinjaTrader.Custom.dll` rebuilt at 20:14:51 local
and `ARMED_ON_START` reached the audit log two seconds later at `03:14:53Z`** — that pairing is
the discriminator, because a failed compile does not rewrite the DLL and `nt_health` reads
healthy either way. `GuardAlertSink`, `GuardActionDeduplicator` and `BridgeConnectionPlan` are
all present in the built assembly.

* ✅ **`F-6`'s flood fix is live-validated.** The reload produced an `ARMED_ON_START` **audit**
  line and **no outbox entry** — the outbox has not been written since `21:54Z`, and its last
  two records are `severity: "warning"` / `[WOULD] ARMED_ON_START` from before the fix. The
  reload that used to spend a fresh alert budget now says nothing. This is the half §5.70 could
  not measure at the time.
* ✅ **The heartbeat staleness recorded in `de3e2b3` is RESOLVED.** `heartbeat.txt` reads
  current to the second. ⚠️ It was misread once first, by comparing a local-time `ls` mtime
  against a UTC clock — **read the file's contents, not its mtime**; the guard writes UTC and
  this box is UTC-7 while the guard's own `timestamp_et` is UTC-4, so three clocks are in play.
* ⚠️ **The alert relay was down, and the reason is the finding.** `LastTaskResult: 255`, State
  `Ready`, no relay process, and **no log anywhere** — `start_alert_relay.bat` writes to a
  console Task Scheduler discards. It was read as a crash and **it was not: the operator had
  stopped it deliberately.** *A deliberate stop and a crash produce byte-identical evidence
  here.* The missing artifact is not "why did it die" but **"was this intended"**, and the fix
  is cheap — tee the launcher to a log, and have the relay touch a local liveness file each
  poll so the question is answerable without reading Discord. Until then `F-6` is inert
  whenever the relay is not running, which is correct while nothing trades and is **not**
  detectable when something does.

### Order from here — ⚠️ SUPERSEDED BY §5.72, which added `P1-117` above item 2

1. **`P2-116`** — an equity rule with no equity reading reports `EvaluatedNotEnforcing` on 88 of
   89 prop accounts. ⚠️ **This section's first draft put `P2-29` here**, by copying §5.63's
   order, which predates `P2-116` being raised in §5.65 — the same copy-forward that
   `check_next_list_ids.py` exists to catch, in the one direction that gate cannot see: **an
   order can be stale without naming a single closed ID.** A live surface reporting *protected*
   for 88 accounts the guard holds no equity for outranks a refactor.
2. **`P2-29`**'s remaining half — the `partial class` split of `RiskGuardAddOn` itself, still
   5,612 lines. ⚠️ Still **before** the remaining features (`F-4`, `F-3`, `F-1`): it cuts apart
   the file every one of them would be written into, and `F-6` has already added an outbox
   queue, a sink field and an emission block to it.
3. **`P3-110`** (narrowed by live measurement), then the architectural **`P3-33`**.

⚠️ **Not listed above, deliberately: the unvalidated halves of CLOSED entries.** Futures reopen
**Sunday 2026-08-16 18:00 ET**, and four of them need one filled contract — `F-6`'s suppression
of a **recurring** condition and its STALE-guard heartbeat (§5.70), the stop-move half (§5.64),
and the lockout **admit** half (§5.62, where only the refusal is measured). `check_next_list_ids.py`
refuses a draft naming their closed IDs as work-to-do and it is right to: *a remainder hiding
under a closed entry is invisible to every count.* **If any turns out to be more than a
confirmation run, it gets its own ID.**

⚠️ **And the relay must be running before that reopen**, or the first three of those cannot be
observed at all — the guard will decide correctly and append to a file nobody is reading.

---

## 5.72 Session 47 (continued) — the first agent-loop run in `nt8-mcp-bridge`, what caught it, and the writer nobody was validating

Session 47's second half went after work that needs **no market**, after the operator pointed out —
correctly — that the previous framing had over-weighted the items waiting on Sunday's reopen. Almost
the whole backlog is market-independent. The two things picked were `P2-27`'s bridge remainder and
the editable UI, to run in parallel. **Only the first was reached.** Nothing shipped, and the
session's product is four findings and a new defect.

### The gate that ported, and why it was not one `cp`

`tools/check_expected_survivors.py` is now live in `nt8-mcp-bridge` CI. §5.71 recorded it as the
**fourth** per-repo gate found present in one repo and absent in the other; this closes that.

⚠️ **A verbatim copy would have PASSED on day one and been wrong anyway.** All eight bridge
batteries use the plain `sys.exit(1 if survivors else 0)` and none declares, so the check is green —
while prescribing a remedy that **does not exist in that repo**: *"hand the verdict to
`_battery.finish`"*, and there is no `mutation/_battery.py` there. A gate whose failure message
names a helper you cannot import sends its reader in a circle at the exact moment they are already
stuck. So the port derives its remedy text from what the repo *has*, adds a check that refuses a
battery calling the helper while it is absent (an `ImportError` on a mutation battery fires
**between applying a mutant and restoring it**, which is [[a-battery-must-reach-its-restore-line]]),
and rewrites the success message, which had been advertising a guarantee — *"fails on a declared
survivor that has since been KILLED"* — that nothing in the bridge provides.

**Copy a gate, then read what it tells you to do about the repo you copied it into.** A ported
gate reports on the repo it was pasted into, not the one it was written for.

⚠️ And the thing that made this take four sessions is in `ci.yml`'s own comments: session 42 wrote
*"THIRD per-repo gate found missing on this side, after `check_ci_runs_every_battery.py` and
`check_expected_survivors.py`"* — **naming this exact gap in prose, in a CI file, and creating no
failure.** Nobody ported it until session 47. *A gate nobody reads is a comment*, inverted again:
**if you find yourself listing a gate a repo lacks, port it in that commit or the list is the only
thing that will ever exist.**

### `P2-27`: the ticket, the run, and the hand arbitration

The target was `/api/riskguard/config`'s POST path. It is hardened against the wrong **shape**
(`P1-80` stopped it persisting a file nothing read back; `P2-41` made it *merge* rather than
flatten) and against no wrong **content** at all: the merged `RiskConfig` goes straight to
`SaveAndReloadConfig`, **which does not run preflight**, so a config that cannot pass preflight is
written and reloaded happily and the guard comes up **disarmed at the next restart** with nothing
about the file looking wrong. Survivable while the only writer is a deliberate API call; not
survivable the moment the editable UI lands.

Nine acceptance assertions were written **by hand first** and were red at the 396/9 baseline. The
run:

```
[baseline] 391 passed, 11 failed; 11 expected failure(s)   [test-first] 9 acceptance test(s) red
round 2:  [compile] ok   [test] ok - all 9 acceptance test(s) green
          [panel] REVISE  [glm-5.2=APPROVE(0), deepseek-v4-flash=REVISE(2)]
          [arbiter] ESCALATE (upheld=0 rejected=4)
ESCALATED: Arbiter recommended SHIP while dismissing BLOCKER finding(s) #1.
NOT APPLIED. Patch for review: logs/agent_loop/T1/final.patch
```

**The dismissed BLOCKER holds. The patch would not have compiled inside NT8.** Its route half read
`cfg.TrailingDrawdown`; `RiskConfig` has no such property. Verified against the vendored core:

| expression | verdict |
|---|---|
| `cfg.Mode` | ✅ exists on `RiskConfig` (`public string Mode`) |
| `cfg.MinShadowSessions` | ✅ exists on `RiskConfig` (`public int MinShadowSessions`) |
| `cfg.TrailingDrawdown` | ❌ **does not exist** |
| `cfg.PnLRules.TrailingDrawdown` | ✅ — and `GuardRules.cs:260` names its own `ConfigPath` as exactly `"PnLRules.TrailingDrawdown"` |

**Four things to carry out of this.**

**1. ⚠️ `[compile] ok` was TRUE and proved nothing about the changed line.**
`tests/BridgeTests.csproj` sets `EnableDefaultCompileItems=false` and does not include
`addons/McpBridgeAddOn.cs`. The build succeeded because the *new* class compiled; the file the
patch edited was never handed to a compiler. This is the trap the plan predicted on 2026-08-13 and
declined to write a profile for — the profile now exists and its docstring leads with the warning,
which is the honest form, but **a warning in a docstring is not a gate**. Every bridge ticket must
end with `nt_compile`, the only thing on this box that compiles that file. ⚠️ It is also the one
place a mistake is invisible: [[broken-nt8-assembly-is-invisible]] — NT8 keeps running the last good
assembly, `nt_health` reads healthy, and the only symptom is a deploy having no effect.

**2. What stopped it was one structural rule, not a reviewer and not a gate.** `glm-5.2` moved to
APPROVE. The arbiter dismissed all four findings and recommended SHIP. `deepseek-v4-flash` filed the
missing property as a BLOCKER **for exactly the right reason** — that the property names were
unverified and the compile gate could not see them. agent-loop `v0.6.3`'s rule (an arbiter may not
recommend SHIP over a standing BLOCKER; that run ends `ESCALATED`, which is not promotable) is the
whole reason a non-compiling patch did not land. ⚠️ Consistent with [[agent-patch-loop-arbiter-gotchas]]:
`ARBITER_SHIP` is not a review on this codebase. **0 of 66 findings upheld across five SHIP rulings
now.** When a run ends `ESCALATED`, arbitrate by hand — it took one grep.

**3. ⚠️ THE VALIDATOR WAS BEING BUILT ON THE WRONG SIDE OF THE SPLIT, and no gate could say so.**
The ticket put `BridgeGuardConfigEdit` in `nt8-mcp-bridge/addons/`. The submodule direction is
bridge → core, so **`RiskGuardWindow.cs` cannot call it** — no matter that both land in one NT8
assembly at runtime. And the window is the *other writer to the same config*. Building a validator
that one of two writers can reach is [[a-second-reader-of-the-same-state]] committed deliberately,
at design time, by me. It belongs in the core, where it is also behind 1776 executable tests and 33
batteries instead of a source gate. **Count the writers before choosing the repo.**

**4. `TrailingDrawdown` = 0 means two OPPOSITE things in one config file**, and a uniform rule would
have been wrong:

* `PnLRules.TrailingDrawdown <= 0` → the rule is **off**. `GuardRules.cs:262` already uses exactly
  that predicate to report `Off("no trailing drawdown set")`. So the validator's rule is not
  invented — it is the guard's own live predicate, promoted from *reporting* to *refusing*.
* `AccountRiskProfile.TrailingDrawdown == 0` → a **sentinel meaning "derive it"**.
  `RiskGuardAddOn.cs:2409-2411`: `baseProfile.TrailingDrawdown > 0.0 ? baseProfile.TrailingDrawdown
  : (cashValue > 0 ? cashValue * 0.05 : _config.PnLRules.TrailingDrawdown)` — 5% of cash, else the
  global. It is the **default** on every profile.

Refusing `0` uniformly would refuse the shipped default on every per-account profile. Same field
name, two meanings, one file, nothing stating it. There is a third `TrailingDrawdown` on
`RiskManagerAddOn` (default `2000`) — [[riskguard-third-risk-system]] again.

### 🆕 `P1-117`, found while scoping the above

**The config window mutates the live config in place.** `RiskGuardWindow.OnSaveConfigClick` does
`var cfg = _addOn.Config;` — and `Config` is `=> _config`, a live reference, not a clone — then
applies **seventeen assignments** to it, thirteen of them bare `int.Parse`/`double.Parse` on raw
text-box text, inside one `try`. `SaveAndReloadConfig` is the last statement.

A typo in any box throws there. **Everything above it is already applied to the running guard**;
everything below it, and the persist, is not. The operator is shown *"Failed to parse settings"* —
a sentence that means *nothing happened*.

⚠️ **`cfg.Mode` is the second statement**, so it always lands. The ordinary gesture is *"go live and
set my limits"*; fat-finger one number and **the guard is in the new mode with the old limits and
has just reported the save failed.** Not persisted, so a restart recovers it — but the running
guard holds it for the rest of the session. Full entry in the plan; evidence obtainable with the
market shut.

### What did NOT happen

**Track B, the editable UI, was never started.** `ui/index.html` (654 lines) already has a
token-authed `postJson` with 401 handling and `/api/riskguard/config` already accepts POST, so the
page is the smaller half — but it is the reason `P2-27` was taken first, and `P2-27` did not land.
⚠️ **Do not ship the editable page before the validator.** The page's entire purpose is an operator
changing limits quickly, and the failure it exposes is silent and delayed: the write says
`applied`, the page re-renders the value it just sent, and the guard is not protecting anything
after the next restart.

⚠️ **`UI_REDESIGN_DESIGN.md` §10 carries its own do-next list and no `Order from here` block has
ever referenced it.** Two ordering lists, one of them invisible to every reader of this file and to
`check_next_list_ids.py`, which reads only the handover. That is [[closures-do-not-propagate-backwards]]
at a second surface. Its remainder: SSE instead of the 5s poll, operator-readable notes (they
currently cite defect IDs at an operator), and an NT8 Control Center menu item.

### Order from here — ⚠️ SUPERSEDED BY §5.73

1. **`P2-116`** — an equity rule with no equity reading reports `EvaluatedNotEnforcing` on 88 of 89
   prop accounts. Unchanged from §5.71: a live surface reporting *protected* for 88 accounts the
   guard holds no equity for outranks a refactor.
2. **`P1-117` + `P2-27`'s validator, as ONE piece of work.** They are the two writers to one
   config and the validator is the shared half. Build `GuardConfigEdit` **in this repo**, mutate
   it, then call it from both `RiskGuardWindow.OnSaveConfigClick` (after the parse-into-locals fix)
   and the bridge's `RiskGuardConfig` route. The nine red acceptance tests in
   `nt8-mcp-bridge/tests/BridgeSourceTests.cs` and the ticket at
   `nt8-mcp-bridge/agent/tickets_p227_config.json` are still valid for the route half; the class
   half moves here. **Then the editable UI**, and not before.
   ⚠️ **The class half LANDED in session 48 (§5.73) and the writer count in this line is WRONG —
   there are three, not two.** What remains is `P2-119`, the wiring.
3. **`P2-29`**'s remaining half — the `partial class` split of `RiskGuardAddOn` itself, still 5,612
   lines, still before the remaining features (`F-4`, `F-3`, `F-1`).
4. **`P3-110`** (narrowed by live measurement), then the architectural **`P3-33`**.

⚠️ Unchanged from §5.71 and still not listed above, deliberately: **the unvalidated halves of
CLOSED entries** (`F-6`'s recurring-condition suppression and its STALE-guard heartbeat, the
stop-move half, the lockout **admit** half). Futures reopen **Sunday 2026-08-16 18:00 ET** and each
needs one filled contract. If any turns out to be more than a confirmation run, it gets its own ID.

⚠️ **And the relay must be running before that reopen** — the operator stopped it deliberately in
session 47, and *a deliberate stop and a crash produce byte-identical evidence here* (§5.71).

---

## 5.73 Session 48 — the editable UI shipped, the validator landed, and THREE of the four defects found were mine

Two tracks in parallel: `P2-27`'s validator through the agent-loop, and the editable UI by hand.
Both landed. **The loop took four runs and three of the four failures were defects in my own
ticket** — which is the session's actual content, because each one was invisible to a different
gate.

### Track B — the editable guard config, live-validated

`ui/index.html` could read `/api/riskguard/inventory` and not the config it summarises. It now
renders ~20 operator knobs as inputs and writes them back.

**Measured before designed** ([[measure-the-deployed-system]]). The live payload is **7,276 bytes**
and most of it is not a knob: **94** `AccountFirmMap` rows, **9** `FirmProfiles`, `WindowsET`,
`Profiles`. Those are reported as **counts**, with the words *"not editable here, and left
untouched by a save"* — a form showing twenty fields reads as a config that HAS twenty fields, and
the operator's model of their own protection is the thing this page exists to keep correct.

**Every request is a diff**, and here that is load-bearing rather than tidy: a full-object round
trip through a form that cannot see `AccountFirmMap` would reset 94 mappings, which is `P?-65` with
two more zeros. Driven against the running box:

| | measured |
|---|---|
| nothing touched | `{}`, nothing sent |
| one leaf | `{"PnLRules":{"TrailingDrawdown":2000}}` — siblings absent, so the merge leaves them |
| two branches | `{"PnLRules":{…},"Sizing":{…}}` |
| `AccountFirmMap` in any body | **never** |
| `1o00` | refused, *"is not a number"*, **nothing sent** |
| `8.5` in a whole-number field | refused |
| retyping `1500` | not a change |
| every form path resolving | **20 of 20, 0 absent** |

That last group is `P1-117` done the other way round on purpose: parse into locals, validate the
whole set, THEN send — so a failure is a failure that changed nothing, which is what the dialog
already claims. `OnSaveConfigClick` does the opposite and that is still open.

**Three selects rather than text boxes**, each because free text is how you get the value something
downstream refuses: `Mode` (preflight), `StopGuard.OnMissing` (`P1-87`), and `Alerts.MinSeverity`
— whose floor is **fail-OPEN**, since `RankOf` answers 0 for an unrecognised string and a typo'd
`warn` pushes the entire audit stream. ⚠️ A stored value outside a list stays **visible and
selected** and is flagged; dropping it would rewrite the operator's config to whatever happened to
be first.

⚠️ **The form is deliberately NOT on the 5s poll.** `load()` re-renders `#content` and `#copier`
every five seconds, and a form rebuilt under the cursor loses what is being typed — worse, it
silently reverts an unsaved change, so the operator saves a diff that no longer says what they
meant. The page already carried that lesson for `#outcome` and it had to be applied again.

**9 new tests** (`mcp/tests/ui-config-form.test.js`, 54 → 63). The load-bearing one resolves every
form path against the **real** payload, trimmed only in the two maps the form does not edit — a
typo'd path renders `absent` and is silently never sent, which is `P1-72`'s shape. **Driven to FAIL
on purpose** with a typo before being trusted (63 → 62/1). It reads ONE bounded region and says so.

⚠️ **The POST is NOT live-validated.** Read, diff, refusal-render and poll-isolation all are. The
write mutates a live risk config and the validator that would catch a bad value is not wired yet,
so it is the operator's call, not mine.

### Track A — four loop runs, and what each failure was invisible to

| run | verdict | cause |
|---|---|---|
| 1 | `TICKET_REJECTED` | the worktree builds from **HEAD** and my tests were uncommitted |
| 2 | `APPROVE` | **thrown away** — the spec's mode list was the COPIER's |
| 3 | `ARBITER_NEVER_RAN` | two of my own acceptance tests were unsatisfiable together |
| 4 | `PANEL_UNREACHABLE` | a reviewer returned **623 findings against a cap of 60** |

**Run 1's tell was in the output and I missed it**: `[baseline] 1776 passed, 0 failed` is the exact
pre-test count. *The loop's worktree is a commit, not your working tree.*

**⚠️ RUN 2 IS THE ONE TO CARRY.** The ticket said the guard's modes are `shadow / live / disabled`.
`disabled` is **`TradeCopierEngine.IsRecognisedCopierMode`'s**, deliberately separate since `P3-34`
so the sim keeps copying while the guard sits in shadow; it is the only place the string exists.
The guard's set is `shadow / live / pure / override_with_friction` and preflight refuses anything
else. So the validator would have **accepted a value that fails preflight**, leaving the guard
disarmed at the next restart with nothing about the file looking wrong — *the exact defect it was
built to prevent, introduced by it.* `P1-72` a third time.

**Nothing caught it.** The loop implemented the spec exactly, **1792 tests went green**, and BOTH
reviewers returned **APPROVE(0)**. **The acceptance tests encode the AUTHOR'S BELIEF about the
domain, and no rung of the ladder compares that belief to the code.**

**What does now, and it earned its place twice in one session:** one test drives seven modes
through **both** the validator and the real `RunPreflight()` and asserts they agree in **both**
directions. It immediately caught run 3 — I had also written *"case-insensitive"*, and preflight is
ordinal, so *"`SHADOW` is accepted"* and *"the validator agrees with preflight"* cannot both hold.
16 of 17 green for three rounds, panel never reached. **An agreement test does not only catch drift
between two implementations; it catches a SPECIFICATION that disagrees with the code it specifies.**

**Run 4 was not a verdict.** `PANEL_UNREACHABLE` with `glm-5.2 = APPROVE(0)` and every gate green;
the other reviewer degenerated into repetition. Applied by hand.

⚠️ **And hand-review then found a defect no gate could.** The refusal told the operator that `PURE`
and `DISABLED` were rejected because *"mode is case-sensitive"* — true of the comparison, useless
as advice, since both are refused in every case there is. **A message naming a fix that does not
work is worse than one naming none**, and it is `P3-118`'s own defect committed by the class built
to prevent it. Nothing pinned the text, so nothing could have caught it. **When a refusal's whole
job is to tell somebody what to do next, the ADVICE is behaviour and belongs in a test** — with a
positive control, so a refusal that never mentions case cannot pass by saying nothing.

**`mutation/mutate_p227.py`: 11 mutants, 11 killed**, tree restored, 1801/0 either side. Three of
them are defects this ticket actually shipped. ⚠️ Mutant 7 is the unconditional refusal — every
requirement here is about refusing something, so it satisfies all of them and ships a validator
that makes the endpoint unusable (`P2-115`'s constant, `F-17`'s always-refuse). The six
**acceptance** cases are the only thing that bans it. ⚠️ `TestP227_ANaNTrailingDrawdownIsRefused`
was written because I predicted mutant 5 would survive: `x <= 0` **accepts NaN**, since every
comparison with NaN is false, so the obvious form writes a limit no comparison can satisfy.

### 🆕 Two more findings, at the seam where the wiring goes

Looking for the one place to call the validator turned up `P2-119`, and it is two things:

* **`SaveAndReloadConfig` returns `void` and swallows its own exception.** A locked file or a
  permissions failure produces one `ERROR` line nobody watches, the method returns normally, and
  `OnSaveConfigClick` then shows *"Configuration saved and hot-reloaded successfully!"*
  **unconditionally**. [[report-the-outcome-not-the-call]] at a third site, structurally identical
  to `P1-105`.
* ⚠️ **There are THREE writers, not two.** `P1-117` and `P2-27` both say two. The third is
  `RiskGuardWindow.cs:724`, the **account-exclusion toggle** — and excluding an account removes it
  from guarding, so it is a protection-affecting write with no validation and no confirmation, and
  it was on nobody's list. Found by grepping for the **callee** instead of reasoning about callers.
  *Count the sites before closing the ticket.*

That reshapes the remaining work in a good way: wiring at `SaveAndReloadConfig` covers all three
writers at once, where wiring each caller would have left the exclusion toggle out and put two
copies of the same call in the window and the route.

### Order from here

⚠️ **SUPERSEDED BY §5.74's list — read that one.** Item 1 below is DONE (both halves), and is left
in place only for the note under it, which is about this gate rather than about the work.

1. ✅ **DONE in session 48** — the config-save chokepoint now returns an outcome and refuses what a
   write introduces, and the window no longer edits the live config in place. The remaining bridge
   caller is a NEW entry in §5.74, not a remainder of this one.
   ⚠️ This line first cited the closed entry that named that class BY ID, and
   `check_next_list_ids.py` **refused it twice** — once for the citation and once for the note
   explaining the citation. An ordering block naming a closed ID is the one thing that gate
   exists to stop, and it cannot tell a reference from an assignment. It is right not to try:
   **cite a closed entry by its LESSON in an ordering block, never by its number.**
2. **`P2-116`** — an equity rule with no equity reading reports `EvaluatedNotEnforcing` on 88 of 89
   prop accounts. ⚠️ It headed this list in §5.71 and §5.72 and is now second, deliberately: a
   validator nobody calls is a surface stating protection that does not exist, which is `P2-116`'s
   own class one layer earlier, and it is half-built as of this session.
3. **`P2-29`**'s remaining half — the `partial class` split of `RiskGuardAddOn` itself, 5,612
   lines, still before the features (`F-4`, `F-3`, `F-1`).
4. **`P3-118`** (three readers of `Mode`, three case rules — fails closed, so the defect is the
   message), then **`P3-110`**, then the architectural **`P3-33`**.

⚠️ **Not listed, unchanged from §5.71 and §5.72: the unvalidated halves of CLOSED entries.**
Futures reopen **Sunday 2026-08-16 18:00 ET** and each needs one filled contract — `F-6`'s
recurring-condition suppression and its STALE-guard heartbeat, the stop-move half, and the lockout
**admit** half. **The relay must be running before that reopen**, or the first three cannot be
observed at all.

⚠️ **Not tagged AT THE TIME OF THIS SECTION.** `GuardConfigEdit.cs` was a new addon file that
nothing called, so there was no behaviour to ship. The wiring landed later the same session — see
§5.74, where the tag, the pin and `nt_compile` all move together.

---

## 5.74 Session 48 (continued) — the wiring landed, CI stopped being slow for a reason I had already written down, and F-6 was inert on the day it mattered

**Order from here** (this supersedes §5.73's list):

1. ✅ **DONE — the bridge route (`P2-120`), live-validated both ways.** Core tagged **v1.31.0**,
   pin advanced, `deploy.py --verify` 28 files / 0 orphans, **`nt_compile` 0 errors**, guard
   loaded / `shadow` / armed / guarding.

   ⚠️ **It was filed as its OWN ID rather than "the rest of `P2-119`", because
   `check_next_list_ids.py` refused the first draft of this very section for listing a CLOSED
   entry as work to do.** *A remainder hiding under a closed entry is invisible to every count* —
   and the gate enforced that against me while I was writing the paragraph claiming to have
   learned it.
2. ✅ **DONE — CI re-packed on measured weights.** `mutate_p2119.py` measured **255s** against my
   **290s** estimate (12% high); the provisional bin ran 701s and the wall 814s against a
   predicted ~790s. Re-packed: total compute 8571s → 8718s, ideal bin 459s, and **UI4 (502s) is
   still the floor** — so the 35th battery costs nothing once the arrangement is right. Same
   lesson as `P2-27`'s, where *"it does not fit in twenty bins"* meant *the arrangement is stale*,
   not *the floor has moved*.
3. **`P2-116`** — this now heads the list. Then `P2-29`'s remainder, `P3-118`, `P3-110`, `P3-33`.

### The CI regression was mine, twice, in opposite directions

`mutate_p227.py` was hand-packed into the CM3 bin on the guess *"≤180s lands free"*. It measured
**271s**, that bin ran **636s**, and it became the critical path alone: **726s**. Splitting it
into a 21st bin measured **worse — 853s**. Re-packing all 34 on measured weights into **19 bins**:
**657s**, every bin starting within 4 seconds, nothing queued.

⚠️ **The 21st bin is not why the split was slow, and the reason was ALREADY IN `ci.yml`.** The
concurrency limit is **20 jobs account-wide, shared across every repo** — written down correctly
in that file since session 45, sixty lines above the matrix. I read the matrix and counted this
workflow's jobs. Measured on run `31929912836`, and the timestamps are a causal chain:

```
05:51:00  19 bins start; 2 do not
05:56:01  the BRIDGE's only job ends
05:56:02  P2-107 starts        <- 1s after a slot in ANOTHER REPO freed
05:56:13  the P2-27 bin ends
05:56:14  P1-85+P1-83 starts   <- 314s late, and the critical path at 446s
```

**Where a number is ENFORCED is not where it is DOCUMENTED.** `MAX_BINS = 19` now lives in
`check_ci_runs_every_battery.py` and `pack_ci_matrix.py` IMPORTS it, so the packer cannot
`--apply` a plan its own CI gate would reject. 19 costs nothing: UI4 is 493s of work and the
ideal bin at 19 is 451s, so **UI4 is the floor at 17, 18, 19 AND 20 bins** — all four predict the
same ~10.3 min. Between plans that tie, take the one that does not depend on another repository.

⚠️ **The reasoning error is worth more than the number.** The split was argued from *"which
existing bin has room for 271s?"* — but the bins are an **output** of the packer, not an input. A
full re-pack puts `P2-27` with `P0-63` at 447s, comfortably under the floor. Nothing was ever too
big; the arrangement was stale.

⚠️ **My first placement of the new bin-count gate was unreachable** — after the per-battery
verdicts, where "no matrix entries" already makes every battery read as missing and returns
first. A branch with no input that reaches it is the *green that can never be red* this repo has
shipped before. Moved to directly after the `CONSUMES` check and driven failing in both
directions.

### `check_window_parses.py` was checking one file out of fourteen

`TARGETS = ['TradeCopierWindow.cs']`, with a comment asking the next person to extend it. `P2-29`
split the dashboard into `RiskGuardWindow.cs` and nobody did. So it printed
`OK: TradeCopierWindow.cs parse(s) as valid C#` — **true, and read as a verdict on a file it had
never opened** — and it had been blind to that window for as long as the window had existed.

**Fourth hand-typed inventory in this project to drift**, after `BridgeTests.csproj`,
`check_bridge_parses.py` and `sync_nt8_strategies.py`. All four carried a comment telling the next
person to maintain them; the comment is what failed. It now globs `addons/*.cs` — **1 → 14** — and
prints the count and the names, so the region it inspected is in its own output. Its subprocess
capture also had the cp1252 hazard, which here **fails OPEN**: a killed reader thread yields no
`CS1xxx` lines, which scores as a pass.

### `P1-117` and `P2-119` — and the review that could not see the file that mattered

Fixed together, because they are one mechanism: the chokepoint decides whether a write
*introduces* a bad value by comparing incoming against live, and the window was handing it **the
live object it had just mutated field by field** — every value equal to itself, every change
permitted, and the validator's own tests all green. The bridge never had it, because
`RiskConfigMerge.Apply` returns a new object. **One writer being correct is not evidence about
the others.**

⚠️ **The agent-loop patch nested `ConfigSaveResult` inside `GuardConfigEdit`, which would have
broken NinjaTrader.** `RiskGuardWindow.cs` names it unqualified; the window is `#if !TESTING`, so
`dotnet build` compiles it away and the parse gate only checks syntax. Green build, 1833 passing
tests, and the first report would have been NT8 refusing the **whole Custom assembly**. A reviewer
raised it and the arbiter dismissed it because *"the type is only used internally by the patch"* —
a claim about a file the panel could not open. ⚠️ **And that dismissal was saved to the loop's
settled-decision store**, where it would have biased every future run here; corrected by hand. **A
review system with a memory can remember a wrong answer — check what it SAVED, not just what it
said.**

The panel did independently find the sharpest real defect: the patch **backfilled** a blank `Mode`
and a missing `PnLRules` from the config being replaced, validated that, and serialised the
incoming one. **Validating one object and persisting another is worse than the defect being
fixed** — it reports a success about the wrong config.

⚠️ **Four mutants survived the first battery run and all four were missing tests of MINE.** The
blank-`Mode` one is the instructive one: writing the test that kills the mutant exposed **the same
hole in my own implementation**, one clause further along. `Refuse` accepts a blank mode because
for a partial body blank means *leave it alone*; the chokepoint writes a whole config, where blank
is what gets persisted. **The same question needs different answers at the two callers**, and only
the battery asked. The `shadow` → `SHADOW` mutant is the other: every mode pair in the acceptance
tests differed under *both* comparisons, so nothing could tell a relaxed changed-check from a
correct one.

Suite **1846/0**, battery **10 killed + 1 declared unreachable**, gates **10/10**, anchors 367/0.

### `F-6` was inert on the day the notes said it had to be running

Checked because the deadline was today, and found: task **`State=Ready`, `LastTaskResult=255`**, no
relay process. It had died at **16:28 the previous afternoon** and stayed dead for seven hours.

**Cause: `RestartCount 3` was the only recovery, and it is a BUDGET, not a policy.** Three attempts
a minute apart, then Task Scheduler gives up — permanently, until the next **logon**. On a box that
stays logged in for days, "until the next logon" is "never". The comment above those settings
called them *"the OUTER supervisor"*, which is what they look like and not what they are.

⚠️ **And there was NOT ONE LINE anywhere saying why.** Under Task Scheduler there is no console, so
everything the launcher printed — including the relay's stderr and the exit code — went nowhere.
`F-6` made the SILENCE detectable and left the CAUSE unrecorded. Both halves are needed: the
heartbeat tells you the channel is dead, and by the time you look the window is gone.

Fixed: a 15-minute repeating trigger (safe only because `MultipleInstances` is `IgnoreNew` —
**verified after registering, not assumed**), and a log file. ⚠️ `-RepetitionDuration
([TimeSpan]::MaxValue)` is the obvious way to say *indefinitely* and Task Scheduler **refuses the
whole registration** as out of range; omitting it is correct, so the script now **reads the task
back** and prints what each trigger actually holds. ⚠️ Redirecting only stdout would have produced
an **empty log** — the relay logs through `logging`, which writes to stderr — and an empty log
reads as a quiet, healthy relay.

**State**: relay running (pid 30340), log written, heartbeat delivered, cursor level with the
outbox at 7848 bytes / 18 alerts. ⚠️ **The 255 itself is still unexplained** — this makes the next
one diagnosable, it does not explain the last one. Read 15 minutes as the **worst-case dead
window**; the outbox is a file and the relay resumes from its cursor, so alerts are late, not lost.

---

## 5.75 Session 49 — the copier UI, where three producers had computed the answer and nothing consumed it

**Entered on the operator's sentence**, not on the do-next list: *"the copier UI does not look like
it is done."* It was not a feature gap. `grep -rn "TODO\|not implemented\|stub" TradeCopierWindow.cs`
returned **nothing**; every control had a handler and every handler worked. The window was
finished and it was **wrong**, which is the harder version.

### What was measured, before writing anything

`_statusText` appears **three times** in `TradeCopierWindow.cs`: the declaration, the construction,
and the `Children.Add`. It was set once to a green literal `"  [ ENGINE: ACTIVE ]"` and **never
assigned again** — not on the 2-second refresh timer, not in the `catch`. *There is no input to
this program that makes that header say anything else.* Beside it, `grep -c "CopierMode"` in the
same file: **0** — while the copier's global `live`/`shadow`/`disabled` mode gates **every** copy at
`TradeCopierEngine.cs:5385` and fails closed on a typo.

The live box, read through the API in the same minute:

```
copierMode: "live"        enforcing: false
notEnforcingReason: "the relationship is not ArmedForLive, so it copies to SIMULATION
                     followers only -- a live follower is refused."
configConflictNote: "none -- every follower is covered by a direct relationship OR a group"
metricsNote: "A zero here means either no copy has filled this session or a genuinely clean fill"
```

**The API knows all of it. The window showed none of it.** So the operator-visible failure is:
the copier is `disabled`, submitting nothing at all, and the one screen built to report on it shows
a green ENGINE: ACTIVE over rows each reading `Armed: LIVE`.

> **The tell was a comment.** Above `DetectConfigConflicts`: *"exposes the conflict through
> `DetectConfigConflicts()` for the API **and the UI** to render."* The API renders it; the UI has
> never had a single reference to it. That comment was the only thing in the repo asserting a
> consumer that did not exist — and it read as a completed design.

### What is reusable

- **Derive the display from the ENFORCER.** `CopierStatusView.IsActing` calls
  `TradeCopierEngine.IsCopierActingMode` rather than comparing to `"live"`; a test asserts the two
  agree across `live`/`LIVE`/`shadow`/`disabled`/`liv`/`""`/`null`. That single assertion is the
  architecture of the ticket, and mutant 6 is the drift it prevents. F-9 restated.
- **The extraction is evidence, not tidiness.** `TradeCopierWindow.cs` is outside the test build
  (`P2-27`'s open half), so *nothing written there can be executed by a test or killed by a mutant*.
  Moving the decisions into `CopierStatusView.cs` — no WPF type, no `#if`, picked up by the csproj
  glob — is what made 14 mutants possible at all. Fifth use of the
  `BridgeAccountResolver`/`GuardConfigEdit` pattern.
- ⚠️ **The load-bearing metric test is the INVERSE one.** "Unmeasured renders as *not measured*"
  passes under a `MetricText` that **always** says not-measured, which would hide every real
  reading. The discriminator is that a **measured zero** must print `0ms (n=3)`.
- ⚠️ **A shared function fed blanks is not shared code.** `GroupLine` is deliberately separate from
  `RelationshipLine`: a group has no quarantine flag and no metrics of its own, so the reuse would
  have printed *"Latency: not measured this session"* for a group whose followers are measured fine.
- **A `catch` that leaves the last text on screen is a stale green claim.** On a 2-second timer a
  permanently failing read held the old header up indefinitely. The screen must never look
  healthier than the last successful read.

### Gates and limits

⚠️ **Mutant 1's first anchor matched TWICE** — `if (!IsActing(copierMode))` is verbatim in both row
renderers — and a 2-match anchor scores a false **SURVIVOR**, not a false pass. Caught on the first
run by the battery's own anchor check; re-anchored down to the `Detail` line that distinguishes them.

⚠️ **No mutant can be placed in `TradeCopierWindow.cs`**, because the harness does not compile it
either and a mutant nothing compiles is not evidence. The window is held only by paired
absence+presence source gates and by `nt_compile`. Say that limit out loud rather than letting
14/14 stand for the whole change.

**Evidence**: suite **1846 → 1924 assertions / 589 declared tests / 0 failures**; battery
`mutate_p1121.py` **14/14 killed, 0 survivors, 0 declared unreachable**.

### Confirmation runs waiting on a market — NOT work, and deliberately not listed below

Unchanged from §5.74 and repeated only so they are not forgotten: Sunday 18:00 ET, all needing one
filled contract — `F-6`'s repeating-condition suppression and its STALE-guard heartbeat, the
stop-move half of the trailing-stop entry, and the lockout **admit** half.

⚠️ **These are unvalidated halves of CLOSED entries, so they are named here in prose and NOT in the
ordering list below.** `check_next_list_ids.py` refuses a draft that lists a closed ID as work to
do, and it fired on the first version of this very section — correctly. If any of them turns out to
be more than a confirmation run, **it gets its own ID**: a remainder hiding under a closed entry is
invisible to every count.

### Order from here

1. **`P2-123`** — filed this session and **the operator's own subject**: the tab called
   *"Symbol & Per-Ticker Matrix"* is a static poster. Measured: **0** engine references inside
   `CreateSymbolMatrixTab`, **0** occurrences of `PerTickerRatios`/`CustomSymbolMappings` anywhere
   in the window, and two `TextBox` fields declared and never constructed. Real persisted config
   the copier enforces is invisible on the screen named after it, while the static table keeps
   asserting the default conversion — so the display **contradicts** the config. Same class as
   the header defect closed above, one tab across. It was deliberately not folded into that
   commit: bolting an unmeasured editable matrix on would have put an untested feature behind a
   14-mutant score that says nothing about it.
2. **`P2-116`** — an equity rule with no equity reading reports `EvaluatedNotEnforcing` on
   **88 of 89** prop accounts, on the surface built to answer *is the guard protecting me*.
   `F-9`'s class in the optimistic direction, and the same shape as this session's closure, one
   layer down. Take this ahead of `P2-123` if the priority is the guard rather than the copier.
3. Then **`P2-29`'s remainder** (the `partial class` split), then `P3-118`, `P3-122`, `P3-110`,
   `P3-33`. ⚠️ **`P3-122` is cheap and lives in the other repo** — one predicate reordering in
   `nt8-mcp-bridge/addons/CopierEnforcementView.cs` plus a two-gates-shut regression row.


---

## 5.76 Session 50 — two tickets in parallel, and both fixes were first written wrong in the same way

**Shipped**: `v1.33.0`, deployed, `nt_compile` **0 errors**, guard **loaded / shadow / armed /
guarding**, `sync_nt8.py --verify` **16 files identical**, `deploy.py --verify` **30 files / 0
orphans**. Suite **1924 → 2006**, two new batteries **12/12** and **16/16**, anchors **397/0**,
all 9 core gates PASS.

Entered on the operator's *"continue and finish up the UI if you can do `P2-116` in parallel
with the agent loop go for it"*. Both landed. The parallelism worked; what it produced is not
the interesting part.

### The one thing to carry: both fixes committed, in their first draft, the defect they were fixing

`P2-123` is *a surface stating behaviour the engine does not perform*. Its first
`SmallestLeaderFillThatCopies` computed `ceil(1/ratio)`. That is obviously right and it is
wrong: the copy path sizes with `(int)Math.Round(...)` and **.NET rounds midpoints TO EVEN**, so
at x0.1 a 5-lot gives `Math.Round(0.5) == 0` and is dropped while a **6**-lot copies. The
arithmetic answers **10**, the engine answers **6**. I had written *"derive from the enforcer,
never recompute beside it"* in the file header and then recomputed, four functions down.

`P2-116` is *evidence counted at the wrong grain*. The tempting predicate is `> 0`, one
character from the shipped `!= 0.0`, and it switches the trailing-drawdown rule to **INERT for
an account whose equity has gone NEGATIVE** — the account most likely to be in trouble. Worse
than the defect.

**Both were caught by writing the mutant, not by reading the code.** Neither review nor the
suite found either: `SmallestLeaderFillThatCopies` had four green assertions, two of which
asserted the wrong numbers, because they were written from the same arithmetic as the code.
**When a fix is about a surface disagreeing with an engine, the test must ask the ENGINE for the
expected value, not restate the rule.** The conformance test that now compares
`ComputeEffectiveRatio` against `CalculateFollowerQuantity` across 24 combinations is the
generalised form.

### The agent loop: right in round 1, `NOT_CONVERGING` by round 4, and worth arbitrating

Round 1 was green on every gate — **1936/0**, all five hand-written acceptance tests flipped
red→green, compile and lock-scope clean. It then ran three more rounds and stopped itself:

```
[panel] REVISE  [glm-5.2=APPROVE(0), deepseek-v4-flash=REVISE(3)]
STOPPING: no convergence over 3 rounds: blocking findings 3 -> 2 -> 3 with zero
overlap between consecutive rounds.
```

Zero overlap between consecutive rounds is the loop correctly detecting a reviewer generating
new surface rather than closing a defect. **`NOT_CONVERGING` is not a failed ticket — it is an
instruction to arbitrate**, and arbitrating paid: **two of its changes were better than my own
prototype** (a `double.IsNaN` guard — `NaN != 0.0` is TRUE, so without it a NaN counts as
evidence; and `CurrentValue = null` rather than `0.0`, since a rendered `cur=0.0` is a number
the operator reads as a fact). Both kept.

**Two were regressions, and both came from the REGION SIZE.** The ticket had to hand it the
whole 350-line `_rules` list, because the two lines needing change in the firm trailing-drawdown
rule are not uniquely anchorable — `Firm daily loss` directly below carries a **byte-identical**
`EvidenceLabel` string. Re-emitting 350 lines to change six: the ASCII gate stripped `⚠️` from
**three unrelated comments**, and peak-equity giveback gained account equity in its value column
against a limit that is a **PERCENT**. ⚠️ **Weigh a loop ticket by whether its change is
ANCHORABLE, not only by whether it is well-specified.** The surgical patch was used as the base
and its two good ideas ported in.

⚠️ **What made the ticket work at all was doing the hard half by hand first**: fifteen
acceptance assertions written BEFORE any code and verified **RED at 1931/5**, plus a throwaway
prototype run to find collateral damage (there was none, across 1936 assertions) so the loop was
handed a job known to be completable. `--list` confirmed both regions resolved to real ranges
rather than degenerate one-liners.

### Two batteries mutating one tree, and how it surfaced

A `nohup`-backgrounded battery was still running when I started a second on the same checkout.
They interleaved; the second read a file with the first's mutant live, took that as its
"original", and **wrote it back at the end**. `TradeCopierEngine.cs` was left with
`if (false) return 0.0;` — a live mutant, on `main`, past a green suite (the guard it disables
has no test, which is why the suite stayed green).

**It surfaced because a later anchor reported `0 matches`**, not because anything watched for
it. ci.yml has said *"two running side by side in one working tree corrupt each other"* since
session 37; the sentence was about CI and I broke it locally. **The rule is one battery per
working tree at a time — a second checkout is free (`git worktree add`) and was already open in
this very session for the loop.**

⚠️ **`nohup cmd &` inside a tool call is not a background job you can see.** The shell exits,
the log is empty, and the process keeps running invisibly. The completion notification said
`exit code 0` — that was `tail`'s.

### Order from here

1. ✅ **DONE in-session — CI re-packed on measured weights, and the gain was ZERO.** Run
   `31958336028` came back green, 20/20, **12m32s** against a ~12.0 min prediction. The two
   estimates were good (377s measured vs 353s estimated; 292s vs 265s — both ~8-10% low, the
   22s/mutant heuristic holding at ~24s), so re-packing moved the heaviest bin **595s → 598s**
   and the wall 12.0 → 12.1 min. ⚠️ **Record a nil gain as nil.** It was still worth doing for
   exactly one reason: the packer refuses to run on guessed weights, so the next battery added
   could not have been packed until these were measured. **A re-pack whose own gain is nothing
   can still be what keeps the next one possible.** Nothing to re-pack now unless a battery is
   added or removed. ⚠️ The re-pack needed the matrix FLATTENED to one battery per entry first: the packer
   weights ENTRIES, so given pairs it can only re-arrange pairs. The per-battery decomposition
   in each comment is what makes that reversible — **second time that comment has paid for
   itself.** 19 bins, heaviest **532s → 595s** against a 510s ideal, because total work rose to
   9685s while the ceiling stayed 19. The ceiling is not a knob.
2. **`P2-29`'s remainder** — the `partial class` split. It cuts apart the file every remaining
   feature would be written into, and this session added another ~200 lines to
   `TradeCopierWindow.cs`.
3. **`P3-124`** — filed this session. The mini/micro table exists in FOUR places in
   `TradeCopierEngine.cs`, and two of them are the sizing arithmetic written twice: a reporter
   and an enforcer computing one number independently. Held safe today by a conformance test, so
   the cost is maintenance rather than exposure — **do not close it by deleting that test.**
4. Then `P3-118`, `P3-122` (cheap, in `nt8-mcp-bridge`), `P3-110` (narrowed), `P3-33`.

### Confirmation runs waiting on a market — NOT work

All need one filled contract (Sunday 18:00 ET), and all are unvalidated halves of entries that
are already CLOSED. If any turns out to be more than a confirmation run it gets its own ID.

* **The copier window's per-ticker tab has never been LOOKED AT.** It is compile-, test- and
  mutation-validated and no human has opened Trade Copier Manager since it changed. The same is
  true of the amber status header from the session before this one. **Say which half was
  measured; do not let one green stand for both.**
* `F-6`'s repeating-condition suppression and its STALE-guard heartbeat.
* The trailing-stop stop-move half, and the lockout **admit** half.

---

## 5.77 Session 50, addendum — the operator showed me the UI, and it is NOT the one I spent the session fixing

**READ THIS BEFORE PICKING UP §5.76's ordering. It changes what is worth doing next.**

At the end of session 50 the operator sent a screenshot of what they actually use:
`http://localhost:7890/ui`, the **browser** UI, served by `nt8-mcp-bridge` out of
`ui/index.html` (993 lines, static asset, `McpBridgeAddOn.cs:6900`). Their words:

> *"the copier UI is not working. only the enable/disable buttons work. The UI itself is
> cluttered. we should have a more organised UI rather than one single page. we can keep it
> simple by having tabs on the left to switch between each item."*

⚠️ **EVERYTHING SESSION 50 BUILT WENT INTO A DIFFERENT SURFACE.** `P1-121` and `P2-123` fixed
`TradeCopierWindow.cs`, the **WPF window inside NT8** (*Trade Copier Manager*). Both closures are
real, deployed and mutation-covered, and **neither is visible in the screenshot**, because the
operator does not appear to work from that window. This is not wasted — the extracted decision
classes are exactly what the browser UI now needs — but **the effort was spent on the less-used
of two surfaces, and nothing in the repo said which one that was.**

**The general lesson, and it is the one to carry**: *this system has TWO operator surfaces for
the same state, and the docs name neither as primary.* Before improving a display, establish
which display the operator has open. One screenshot reordered a whole backlog.

⚠️ **CORRECTION, WRITTEN THE SAME DAY, AND IT MATTERS MORE THAN THE PARAGRAPH ABOVE.** The
first draft of this section called the browser UI a surface I had "found". It is not. It is
**the agreed design's chosen host**, specified in
[`docs/UI_REDESIGN_DESIGN.md`](UI_REDESIGN_DESIGN.md) §7 (*"Host decision — a local browser UI,
served by the bridge"*) and built out across `UI1`-`UI7` with §10 tracking each landing. **The
redesign is not lost and never was**: 493 lines, dated 2026-08-13, with a progress log per item.

Two consequences, both of which corrected filed entries:

* **`P2-127` was first filed proposing left-hand navigation tabs — the one thing §4.2 explicitly
  killed**, in a list introduced with *"recorded so nobody re-adds them."* I re-added them,
  having not opened the design doc, from a `GuardRules.cs` header comment that names it. The
  entry now carries §4's fleet/inspector diagram and states the conflict as the operator's to
  settle rather than resolving it silently.
* **`P2-126` was filed as a discovery and is not one.** §10 item 4 already recorded *"nothing on
  the page is EDITABLE — goal 1 of the two ('configure both systems') is untouched."*

⚠️ **The real diagnosis of "cluttered" is therefore NOT "it needs navigation".** It is that **§4's
two-pane layout was never built**: the read models (§10 items 2-4) landed as stacked sections, and
an editable guard-config block was added at the **top level**, where §4 puts set-rarely config in
the *inspector* and keeps only frequent actions inline. That ~28-row block above the fleet is the
biggest single contributor to the scroll, and it is in the wrong pane by the design's own rules.

⚠️ **§10 item 4's "Still to do" was itself stale** and has been updated in place: the GUARD half
became editable after it was written (`P1-117`/`P2-119`); it is the COPIER half that is read-only.

⚠️ **The process lesson is mine.** A header comment in `GuardRules.cs` names
`docs/UI_REDESIGN_DESIGN.md` and I read past it for two sessions. **When a source file cites a
design doc, open the design doc before proposing a design.**

### What was measured, before writing any of it down

| Question | Answer |
|---|---|
| `copierMode` / `notEnforcingReason` / `configConflicts` in `ui/index.html` | **0** |
| the same three in the bridge addon + `CopierEnforcementView.cs` | **21** |
| copier actions `/api/copier/config` accepts | **14** |
| copier actions the browser UI dispatches | **2** (`set`, `set_group`) |
| fields it ever sends | **2** (`isEnabled`, `isQuarantined: false`) |
| `<nav>` / tab elements in the page | **0** |
| sections stacked on one scroll | **4** |
| rows on screen with all 7 accounts expanded | **~190** |

Three entries filed from that: **`P1-125`** (the page never states the copier's global mode —
`P1-121` verbatim at this surface), **`P2-126`** (2 of 14 actions implemented), **`P2-127`** (the
single-page layout and the left-nav restructure).

### Three things that must not be lost when this is picked up

1. ⚠️ **The header on that page says `mode shadow · armed · cannot act` and that is the GUARD's
   mode.** The copier's own `live`/`shadow`/`disabled` mode — separate since `P3-34`, so the sim
   can copy while the guard observes — is nowhere on the page. Reporting one mode and not the
   other is worse than reporting neither: it invites the reader to assume both were covered.
2. ⚠️ **A tabbed shell hides three of four sections by default, and this page's whole value is
   that `INERT` and a non-acting copier are visible WITHOUT being looked for.** The nav must
   carry each section's worst state as a badge, folded out of the same payload the section
   renders — not its own counters, which is `F-9` and which is why `P2-103`'s summary recounts
   from the detail rows. Get this wrong and an honest cluttered page becomes a tidy page that
   lies by omission.
3. ⚠️ **`ui/index.html` is in NO test build and NO mutation battery**, exactly like
   `TradeCopierWindow.cs`. Move the decisions into a class the harness compiles BEFORE adding
   behaviour, the way `CopierStatusView` and `CopierSymbolMatrixView` already do. Otherwise this
   becomes a third untested surface — and the one the operator actually uses.

### Also true, and cheap to close alongside

`P3-122` (the bridge's `notEnforcingReason` can say an unarmed relationship *"copies to
SIMULATION followers only"* while the copier is in `shadow` and copying to nothing) is a defect
in a string **nothing currently displays**. Close it WITH `P1-125`: rendering the reason is what
makes its ordering reachable by the operator.

### Order from here

0. ⚠️ **READ [`docs/UI_REDESIGN_DESIGN.md`](UI_REDESIGN_DESIGN.md) FIRST — §4, §7, §10, §11.**
   All three entries below are continuations of that design, not new work, and one of them was
   first filed contradicting it. Do not plan UI work from the plan entries alone.
1. ✅ **THE LAYOUT IS SETTLED — BUILD §4. Do not re-open it.** Offered the choice between the
   left-hand nav tabs they proposed on 2026-08-16 and the fleet/inspector they agreed on
   2026-08-13, the operator chose **§4**: *"lets stick to §4 which is what was the original
   design."* Nav tabs are dropped. The concrete region-by-region mapping, and which of today's
   sections feeds each, is tabulated in **`P2-127`**.
2. **`P1-125`** — the browser UI never states the copier's global mode. Smallest, highest
   consequence, and independent of the layout, so it goes first: a `disabled` copier renders
   exactly like a working one. Close **`P3-122`** in the same change. ⚠️ **Build it as §4's
   system row (feed / guard / copier), not as a Copier section header** — §4 decision 4 reserves
   that row for it, so anywhere else is work `P2-127` has to undo.
3. **`P2-127`** — build whichever layout won. Take it BEFORE the new controls: §4 decides where
   each control lives (frequent actions inline on the row, set-rarely config in the inspector),
   and doing it after means moving them twice. Move the decisions into a compiled class first.
4. **`P2-126`** — the copier write surface, which is §10 item 4's outstanding half. Largest, and
   it wants the layout to exist first. Every control dispatches through the existing
   `dispatch()` chokepoint, which already treats `refused` as a first-class answer, not an error.
5. Then the pre-existing queue from §5.76: **`P2-29`**'s `partial class` split, **`P3-118`**,
   **`P3-124`**, **`P3-110`**, **`P3-33`**.

### Confirmation runs waiting on a market — NOT work

Unchanged from §5.76, and still needing one filled contract at a Sunday 18:00 ET open: `F-6`'s
repeating-condition suppression and its STALE-guard heartbeat, the trailing-stop stop-move half,
and the lockout **admit** half. Each is an unvalidated half of a CLOSED entry. If any turns out
to be more than a confirmation run, it gets its own ID.

⚠️ **And one more that is now on the list twice over**: the WPF window's visual half. `P1-121`'s
amber header and `P2-123`'s per-ticker tab are compile-, test- and mutation-validated and **have
never been looked at by a human**. Given this session's discovery, check first whether that
window is a surface the operator opens at all before spending anything further on it.

---

## 5.78 Session 51 — the copier's mode reached the page the operator uses, and the best decision in it was to write no new decision

Two entries closed in the surface §5.77 identified as the one that matters: **`P1-125`** (the
browser UI never stated the copier's global mode) and **`P3-122`** (the reason text ranked its
refusals by what surprises instead of by what binds). They shipped together because they had to:
*a defect in a string that nothing displays is not reachable by an operator.*

All of it landed in **`nt8-mcp-bridge`**. Core was not touched, so the vendored pin still reads
`v1.33.0` and no tag was needed.

### The design decision, which was to reuse rather than write

`CopierStatusView.Describe` — core, built for the WPF window by `P1-121` in session 49, already
mutation-covered — **already answers "is the copier copying?"**, folded out of the same
relationships and groups the browser page's rows come from. The route calls it and passes its
answer through untouched.

That is the whole architecture of the change, and the alternative is what makes it worth recording:
writing a second headline for the browser would have been **the seventh instance of *a second
reader of the same state*, committed in the same session as the fix for the sixth**. `P3-122` IS
two surfaces disagreeing about one question. The severity, the headline and the detail are one
producer's; the bridge owns only the wire shape and the state core cannot know about (no copier
loaded at all); the page owns a colour.

| piece | where | executed by |
|---|---|---|
| severity / headline / detail | `CopierStatusView.Describe` (core, **unchanged**) | core's suite + its battery |
| wire shape, `SeverityName`, not-loaded cell, the refusal ordering | `addons/CopierEnforcementView.cs` | **the bridge harness** |
| composition | `McpBridgeAddOn.GetCopierSnapshot()` | nothing — source gate only (`P2-27`) |
| a colour | `ui/index.html` | nothing, ever |

### Four things worth carrying

1. ⚠️ **TWO SEVERITY SCALES WITH OPPOSITE POLARITY WERE ABOUT TO SHARE ONE PAYLOAD.** The copier
   rows carry `severity` from `CopierSnapshotJson.SeverityRank`, where **0 is the WORST** (an
   `Orphan`). `CopierStatusSeverity` runs the other way — `Ok=0 … Critical=3`. A page keying a
   colour off the wrong one paints an **orphan green**. The system cell therefore crosses the wire
   as a **NAME**, never a number, and a test asserts every rank renders as a word. An unmapped rank
   reads `critical`, for the same reason `SeverityRank` puts an unrecognised verdict at the top:
   *an enum member nobody mapped is not evidence of health.*
2. ⚠️ **MOVING A BRANCH CHANGES THE SET OF INPUTS ITS WORDS MUST BE TRUE FOR.** `P3-122`'s fix moves
   the mode test above `armedForLive`. The mode sentence used to be reachable only by armed
   relationships and said so — *"the relationship is enabled and armed, but the COPIER is in
   'shadow'"*. After the move it is reached by unarmed rows too, so the unchanged string would have
   asserted the opposite of the row it was explaining, **for exactly the row the ticket was filed
   about**. The clause is conditional now, and a mutant restores it both ways.
3. ⚠️ **A REORDER DELETES A CORRECT ANSWER IN SILENCE.** Every assertion about `P3-122` says the
   simulation sentence must NOT appear — and all of them pass if you simply delete that sentence,
   which is wrong, because it is the right answer whenever the copier IS acting. The battery's
   second mutant does precisely that. **The positive control is the only thing that catches it**,
   and this is the same shape as `P2-115`'s constant `false` and `F-17`'s always-refuse: *when every
   requirement is "X must not happen", the mutant to fear is the one that makes X impossible.*
4. ⚠️ **THE CHECK WAS WRONG, NOT THE WORDING, AND IT WAS MINE.** The first draft asserted the shadow
   sentence must not contain the word `simulation`. It failed — because the new sentence contains it
   while *denying* it: *"submits nothing at all — to a live follower or a simulated one alike."*
   That is more use to an operator, not less. The assertion now pins the false CLAIM (`copies to
   SIMULATION`) and is paired with a positive one (the sentence states nothing is submitted), so a
   reworded false promise cannot walk past a substring test. **When a wording check fails, ask which
   of the two is wrong before editing the string.**

### Evidence, and which half is NOT measured

* Harness **302 assertions / 56 tests → 444 / 68**. Battery `mutation/mutate_p1125.py` **22/22**,
  across three files (the view, the route's source gate, and the page's source gate).
* ⚠️ **22/22 on the first run, which is when to trust a battery least** — so three more mutants were
  added after it went green, aimed at the places the tests looked thinnest (the conflict count, the
  `IsActing` passthrough, and a refusal produced for a relationship that IS enforcing, which is *an
  alarm that is always on*). All three were killed; the probe is the point, not the score.
* `check_anchors` **108/0**, `check_ci_runs_every_battery` **9/9 wired exactly once**,
  `check_bridge_parses` 14 files, `nt_compile` **0 errors**, `deploy.py` 2 addons + the UI synced.
* **Live**, with the market shut: `system` = `{loaded: true, mode: "live", isActing: true, severity:
  "info", headline: "[ COPIER LIVE - SIM ONLY ]", configConflicts: 0}`, and both rows carrying
  `enforcing: false` / `notEnforcingLabel: "disabled"` / the sentence — **text that exists only in
  the new classes.**
* ✅ **The `shadow` half WAS measured**, with the operator's consent, market shut and no position
  open: flipped to `shadow` (`severity: "warn"`, `isActing: false`, `headline: "[ COPIER SHADOW ]"`
  — the amber header and banner), then restored to `live` and **verified by RE-READING both
  `/api/copier/snapshot` and `/api/copier/config`, not by trusting the write's own answer**.
  ⚠️ **`disabled` was NOT driven**, and neither was the mode branch of the per-row REFUSAL: both
  relationships on this box are switched off, and `disabled` binds first and correctly, so the rows
  said `"the relationship is disabled."` in both modes. **The mode SENTENCE remains test-only** —
  it needs one enabled relationship under a non-acting copier. Say which half was measured.
* ⚠️ **NOBODY HAS LOOKED AT THE PAGE.** The payload is measured; the rendering is not. That is the
  precise state `P1-121` and `P2-123` are in at the WPF surface, and §5.77 exists because effort
  went into a screen nobody opens. This one the operator *does* open — one glance closes it.

### 🆕 `P3-128`, and it was found by reading the payload of the thing just shipped

The live read returned `[ COPIER LIVE - SIM ONLY ]` — *"copies reach simulation followers only"* —
for a copier whose relationships are **both switched off**. Nothing is copied anywhere, and the
detail line carries the contradicting number in its own first clause (*"2 relationships, 0
enabled"*). `CopierStatusView.Headline` has no rung for `enabled == 0`, so that state falls into the
`armed == 0` rung, whose sentence was written for a different one.

⚠️ **That is `P3-122` in the other class, filed the same day `P3-122` was closed** — a sentence true
of a neighbouring state, describing a behaviour that is not happening, in the direction that
reassures. Fixing the ordering in one reader did not fix the other. **Count the sites.** It is a
core change (tag + pin bump), which is the only reason it was not folded in.

⚠️ **And it was found by DRIVING the endpoint, not by review** — the tests were green, the battery
was 22/22, and the defect is in a class this change deliberately did not modify. Reading the real
payload of the thing you just shipped is a five-second step that keeps finding things.

### 🆕 `P2-129`, found by trying to USE the thing just shipped — and it is the gate-region lesson again

Validating `P1-125`'s amber header needed the copier flipped to `shadow`. The obvious call —
`nt_copier_config action=set_mode` — answered **`unknown action 'set_mode'`**. Three lists name the
copier's actions:

| list | has `set_mode`? |
|---|---|
| the tool SCHEMA (`mcp/lib/tools.js`) — advertised | **yes** |
| the addon's `knownActions` — implemented | **yes** |
| `buildCopierConfigRequest`'s sets — **what runs** | **NO** |

The two DECLARED lists agree **exactly, 14 for 14**, and a test proves it in both directions. **The
refusal came from the untested middle**, so the copier's global gate — the switch `P1-125` had just
put on the operator's page — could not be operated from the surface that advertises it.

⚠️ **A test that both halves DECLARE the same thing is not a test that the path between them
works.** The agreement test's own comment states the failure mode (*"a wrapper that does not name
the action cannot reach it"*) while inspecting a list that names it. Fourth instance of *state the
REGION a check inspects*, after `check_anchors` skipping 18 anchors, `check_bridge_parses` reading
2 files of 6, and `check_ci_runs_every_battery` matching a comment. The new test **drives the
builder** and asserts what it SENDS is an action the addon knows.

⚠️ **It is also `P1-72` inverted** — that one advertised an action nothing implemented; this one
refused an action *both* ends implemented. The pin written for `P1-72` extracts the addon's real
whitelist, which is the right instinct, and still could not see this.

Fixed with a `GLOBAL_WRITES` set: `set_mode` is the first action naming **no relationship**, and
the relationship branch would have demanded a leader and follower — a scope it does not have. The
mode VALUE stays the addon's to validate (`P3-111`'s hand-typed enum forbade twelve values the
addon served). Wrapper suite **63 → 66**, and the three new tests were **watched failing** (3/63)
against the unfixed builder. Live-validated by driving the MCP server over **stdio** — a running
client keeps the old module — with `copierMode: "definitely_not_a_mode"` **on purpose**: it reached
the addon, which refused it with `applied: false`, proving the path **while changing nothing**.

### Order from here

⚠️ Unchanged from §5.77 except that its item 2 is done. **Read
[`docs/UI_REDESIGN_DESIGN.md`](UI_REDESIGN_DESIGN.md) §4, §7, §10, §11 before touching the UI
items** — they are continuations of that design, and one was first filed contradicting it.

1. **`P2-127`** — build §4's fleet/inspector split. **The layout is SETTLED**; do not re-open it.
   Take it BEFORE the new controls: §4 decides where each control lives, and doing it after means
   moving them twice. ⚠️ Move the decisions into a compiled class first — `CopierEnforcementView`
   is now the worked example at this surface, and its system cell is the piece §4's system row
   consumes. The feed and guard thirds of that row do not exist yet; only the copier's does.
2. **`P2-126`** — the copier write surface (2 of 14 actions implemented). Wants the layout first.
3. Then the pre-existing queue: **`P2-29`**'s `partial class` split, **`P3-118`**, **`P3-124`**,
   **`P3-110`**, **`P3-33`**.

### Confirmation runs waiting on a market — NOT work

Unchanged, and now with one addition that does **not** need a market, only the operator's consent:
the `shadow` / `disabled` half of `P1-125`'s header. The rest still need one filled contract at a
Sunday 18:00 ET open: `F-6`'s repeating-condition suppression and its STALE-guard heartbeat, the
trailing-stop stop-move half, and the lockout **admit** half. Each is an unvalidated half of a
CLOSED entry. If any turns out to be more than a confirmation run, it gets its own ID.


---

## 5.79 Session 51 (continued) — P3-128 closed by the agent loop in one round, and the market-open runbook was written an hour early ON PURPOSE

### `P3-128`, filed and closed the same evening

`[ COPIER LIVE - SIM ONLY ]` over a copier whose every relationship is switched off. Closed in
**v1.34.0**, one rung in `CopierStatusView.Headline`, and **live-validated straight after deploy**:
the page now reads `[ COPIER LIVE - NOTHING ENABLED ]` in amber, `Warn`, with no mention of
simulation.

Two things in it are the reusable part, and neither is the rung:

* **Placement, not text, was the ticket.** The rung sits BELOW both quarantine rungs. Above them,
  `quarantined >= enabled` is `1 >= 0` for an all-quarantined, all-disabled copier, so it would
  have swallowed the quarantine report — the one state the operator did not choose.
* **`Warn`, not `Info`.** The browser page paints `info` the same grey as a healthy copier. The
  severity IS the finding on a page built so a non-acting copier is visible without being looked
  for, and shipping this at `Info` would have closed the ticket while leaving the symptom.

⚠️ **The negative control is what refuses the lazy fix, and it was green throughout**: an ENABLED,
unarmed relationship still reads `SIM ONLY`. **A rung keyed on `armed == 0` passes all six red
assertions and deletes the state it imitates.** `enabled` and `armed` are different counters, and
conflating them is the whole defect.

### The agent loop, run at HEAD rather than the pin — and what it cost to get there

Run with the package installed **editable from `C:/Users/vinay/agent-loop` at HEAD** (`5dfc303`,
5,349 insertions past `v0.6.7`), because the operator asked for the latest so it keeps being
tested. Result: **APPROVE in round 1** — `kimi-k2.7-code`, 11.0s, right rung in the right slot,
both reviewers approve, `2012 → 2018` passed / 0 failed, patch applied unchanged.

⚠️ **The FIRST run refused, and the refusal was correct while its message described the wrong
problem.** The loop builds its worktree from **HEAD**; the six acceptance tests were written and
verified red in the **working tree** and not committed, so the baseline it measured was `2006 / 0`
and the tests did not exist in it. It said *"expect_green test(s) not failing at baseline"*, which
reads as *your tests are wrong* and sent me back to re-read them. **A test that PASSES and a test
that does not EXIST are different states with different fixes, and that gate collapses them.**
Filed as `CF-2` in the loop's own repo.

⚠️ Because the tests must be committed for the loop to see them, `main` briefly carried a
deliberately RED commit. It was **squashed with the fix before pushing**, so no commit on `main`
has a red suite — but if you do this, do not push between the two.

**Five findings are logged in [`agent-loop/docs/architecture/CONSUMER_FINDINGS.md`](https://github.com/vinay-veerappa/agent-loop)**,
a new document for defects found by USING the loop rather than by reviewing it. The other one worth
knowing: its unresolved-identifier warning treats any capitalised token as a symbol, so a spec
written in this repo's house style (emphasis in caps) produced **~20 warnings naming `SCOPE`,
`Five`, `NOW`, `WHERE` and zero identifiers**, burying the one line `--list` exists to print. *An
alarm that is always on is off*, in a third repo.

### The runbook, and the item it disqualified before the window opened

[`docs/MARKET_OPEN_VALIDATION_RUNBOOK.md`](MARKET_OPEN_VALIDATION_RUNBOOK.md) was written **35
minutes before the Sunday open** so the window is spent executing. Writing it early paid for itself
immediately: it established that **the lockout ADMIT half is NOT obtainable tonight**, which would
otherwise have been discovered at the open.

`/api/lockout` accepts `status, unlock, reset, clear` — **there is still no action that IMPOSES
one**. `nt_emergency_flatten` imposes a binding lockout but **flattens first**, so you end up locked
and FLAT, and you cannot then open a position because opening is not a reducing order: *the state
is unreachable from that direction by construction.* A rule breach would do it, but the guard is in
`shadow` and a shadow lockout deliberately does not bind (`P2-92`). **ADMIT therefore needs the
guard in an acting mode, which is the operator's decision and not a validation step.**

⚠️ **Two corrections were made to the runbook before the open, and both are method, not typos.**
(1) It first recorded the alert relay as DEAD — a local-mtime file compared against UTC timestamps
inside it. **The box is on PACIFIC time and every JSONL timestamp is UTC; compare UTC to UTC.** The
relay is healthy: cursor offset `7848` == outbox size `7848`, zero backlog. (2) It then recorded
**two** relay instances and told the reader to kill one; `ParentProcessId` says 7228 is 30340's
**child**, same start second. **Two rows in a process list are not two programs.** Left in the
document as a worked example, because the first act of a validation window should not be killing
half of a healthy service.

⚠️ Task Scheduler again reports `State: Running` with `LastTaskResult: 0x800710E0`. Its state is
still not evidence — the relay's health came from the cursor and the hourly heartbeat.

### Also measured tonight, needing no market

* **`P3-122`'s reordered branch, live at last.** One relationship enabled under a `shadow` copier:
  the row read **`copier shadow`** — *"the relationship is enabled, but the COPIER is in 'shadow' …
  submits nothing at all"* — and did NOT say "copies to SIMULATION followers only". Restored to
  `live` / 0 enabled and **verified by re-reading two endpoints**, with the stored ratios intact
  (merge semantics held; no `P?-65` wipe).
* **`P1-125` confirmed by the operator's own screenshot** — `copier live · acting` beside `mode
  shadow · armed · cannot act`. The "nobody has looked at the page" flag from §5.78 is closed.


---

## 5.80 Session 51 — the Sunday open: two passes, one FAILURE, and the failure is a `P1` that 2018 green tests could not see

The window was run from [`MARKET_OPEN_VALIDATION_RUNBOOK.md`](MARKET_OPEN_VALIDATION_RUNBOOK.md),
written 35 minutes before it opened. Results are recorded IN that document beside each plan.

| | item | result |
|---|---|---|
| A | `F-6` repeating-condition suppression | ✅ **PASS** |
| B | `F-6` STALE-guard heartbeat (positive half) | ✅ **PASS** |
| C | ATM breakeven stop-MOVE (`P2-112`'s remainder) | ❌ **FAIL → `P1-130`** |
| D | lockout ADMIT half | **NOT RUN** — pre-agreed condition not met |

### C is the session, and it is the argument for driving the box

Long 1 MNQ @ **30185.25** with a `DrawdownShield` bracket: stop 40 ticks out, breakeven trigger 12
ticks, offset 2. Price ran to **30199.5 — 57 ticks in favour, nearly five times the trigger** — and
the stop **never moved** in 230 seconds. `breakevenTriggered: false`.

**Everything upstream of the write was correct.** The monitor ran, the trigger fired, and the log
names the right number: *"the move to **30185.75** was not requested"* — exactly entry + 2 ticks.

`ModifyStopPrice` matches `order.OrderState == OrderState.Working`. **On this connection a resting
stop sits in `Accepted`** — the fact `P3-110` measured on 2026-08-14 and the panic-flatten path
already learned.

⚠️ **The same class contains the right answer twice**, which is what makes this the sharpest
instance of [[a-second-reader-of-the-same-state]] yet: `MonitorTickCore:623` accepts `Accepted`
explicitly, and `ReconcileStopFromBroker:818` looks up **this very order** through the guard's own
shared `OccupiesSlot` predicate, which classifies `Accepted` as `Working` liveness. **The reader and
the writer of one order, ten lines apart, disagree about whether it exists.** All three stop-move
sites — breakeven twice and **trailing** — funnel through the writer, so **no ATM stop advances at
all** on this box.

⚠️ **And its bounded retry cannot reach its bound**: `RequestStopMove` returns early on a failed
`ModifyStopPrice` **without incrementing `StopModifyAttempts`**, so `MaxStopModifyAttempts` and its
`ATM_STOP_MOVE_ABANDONED` event are unreachable. **55 lines at one per five seconds** when the
position was flattened. [[a-retry-that-cannot-exit]] and *an alarm that is always on is off*, at a
third site after `P2-107` and `P2-108`.

⚠️ **`P2-112` was not wrong.** It made this loop RUN; this is what the running loop then hit, and it
is *precisely* the remainder its own closure flagged as unmeasured — "the stop-MOVE half". **A
confirmation run found a `P1` behind 2018 green tests.** The next time a closure says one half is
unvalidated, that half is where the defect is.

⚠️ **The regression test must drive the STATE, not the move**: a test asserting "the stop moves"
passes against a stub reporting `Working`, and this defect exists only because the provider reports
`Accepted`. [[test-doubles-are-not-evidence]] — the NT8 stub has already hidden one live `P0` by
omitting 6 of 16 `OrderState`s.

### A and B, briefly

**A PASSED**: 1 `NAKED_POSITION` + 1 `AUDIT_FINDING_SUPPRESSED` + 1 outbox alert, against a pre-fix
**12 / 0 / 12**. The suppression line explains its own budget — *"will stop being logged after 1
line(s) in observing mode … will report again the moment the condition changes"*.

⚠️ **`grep -c NAKED_POSITION` returned 2 and that was MY error**: the suppression line *quotes* the
finding it suppresses, so a bare substring counts it twice. By `"eventType"` it is 1. **Detection by
substring, in the runbook's own command** — the third instance of that habit in two sessions.

**B PASSED (positive half)**: the heartbeat fired on the hour, and driving `format_heartbeat()`
against the live guard directory returns `guard: alive, last sweep 0s ago` — so it really does carry
the guard's freshness beside the relay's, which is what makes *relay down* and *NT8 down*
distinguishable. The STALE branch was not driven; it needs the guard stopped.

### D was not run, and that was the rule rather than a judgement

The operator agreed BEFORE the window that D — which needs the guard in an acting mode — would run
**only if A, B and C passed**. C failed, so it did not run and the guard was never armed. **Writing
the condition down in advance is what made that automatic** instead of a decision taken at 15:10
with a `P1` freshly on the table.

⚠️ **When D is next attempted, fix `P1-130` first.** The admit test places a reducing order against
an open position, and a box whose stop-management writer cannot find its own orders is not the box
to measure a lockout gate on.

### Order from here

1. ✅ **`P1-130` was FIXED in this same session and live-validated** — `ATM_STOP_ORDER_NOT_FOUND`
   55 → **0**, and the move is now REQUESTED and bounded. ⚠️ **It is not "breakeven works"**: the
   Simulator then ignores the change (`P0-63`, closed), so the stop still did not physically move. That
   remainder needs a **non-Simulator account** and is a confirmation run, not work — unless it
   turns out to be more, in which case it gets its own ID.
2. **`P2-127`** (§4 layout, settled), **`P2-126`**, then `P2-29`'s remainder, `P3-118`,
   `P3-124`, `P3-110`, `P3-33`.

⚠️ Also seen and NOT filed, because it predates this session and was not driven: three orders from
an earlier bracket (`AtmEntry_0511fe1c`, `Stop_0511fe1c`, `Target_0511fe1c`, prices ~29511) sat in
**`CancelPending`** throughout, including after two `nt_close_position` calls that reported
cancelling them. If they are still there next session, that is its own ID.


---

## 5.81 Session 51 — `P1-130` fixed and re-driven inside the same market session, and the arbiter settled a decision contradicting the finding it had just upheld

`P1-130` was **found, fixed, deployed and re-validated in one open**, which is only possible because
the market was there: the state that produces it (a stop resting in `Accepted`) exists whenever a
bracket rests, and nowhere else.

| | before | after |
|---|---|---|
| `ATM_STOP_ORDER_NOT_FOUND` | **55**, one per 5s, unbounded | **0** |
| `ATM_STOP_MOVE_REQUESTED` | impossible — never got past the lookup | **3** |
| retry | unbounded | **stopped at 3 of 3** |

⚠️ **AND IT IS STILL NOT "BREAKEVEN WORKS".** The provider then IGNORED the change
(`ATM_STOP_CHANGE_IGNORED … requested 30193.75 but the provider holds 30183.5`), which is `P0-63`'s
known Simulator behaviour, correctly detected and handled. **The failing link moved from *we never
asked* to *we asked and the Simulator declined*.** The remainder needs a non-Simulator account.

⚠️ **An alternative reading is recorded rather than dismissed**: NT8 may refuse to modify an order
that has not reached `Working`, in which case the original test was defensive and the right fix is
to wait or to cancel/replace. **Tonight cannot distinguish them** — the Simulator ignores stop
changes generally, so its refusal proves nothing about the state. What IS evidenced is that the
request is now made and bounded. Do not upgrade that into a claim about stops moving.

⚠️ `ATM_STOP_MOVE_ABANDONED` **did not fire** — the retry stopped because the reconciler's counter
hit the cap and the trigger stopped re-requesting, not because the give-up branch spoke. **The
announcement remains unvalidated**, which is `P2-101`'s shape.

### The agent loop: right in round 4, and the arbiter poisoned the memory store

Round 4 was **green on every mechanical gate** — 2033 passed, 0 failed, all 12 acceptance tests
green, no regressions, lock-scope clean — and the panel still said REVISE, so the run ended
`MAX_ROUNDS_EXHAUSTED` and applied nothing. **Arbitrating by hand was correct and the reviewer was
right**: the patch counted the retry budget only when the stop order was *present but no longer
live*, on the plausible reasoning that a transient absence should not abandon a healthy bracket.
**That reinstates the defect** — an order genuinely gone is absent on EVERY sweep, so the budget is
never spent and the 5-second retry runs forever. `deepseek-v4-flash` caught it; `glm-5.2` approved.

⚠️ **The test that would have caught it did not exist, and that is mine**: my acceptance test drove
"present but terminal" and never "absent from `account.Orders`". The fix slipped through precisely
where the test was silent. **A model's unrequested refinement lands exactly in the gap between your
assertions.** The test exists now.

⚠️ **AND THE ARBITER SETTLED THE OPPOSITE OF WHAT IT UPHELD, IN ONE RULING.** It upheld *"the patch
fails to increment `StopModifyAttempts` when the order is absent … causing an unbounded retry"* and
in the same output nominated as SETTLED: *"The failure counter may increment **only** when the stop
order is still present in account.Orders but no longer occupies a live slot."* Those contradict.
**The settled entry was persisted to `logs/agent_loop/settled_decisions.jsonl`** and would have been
fed to later runs as an established constraint — teaching the next run to re-introduce the defect
this one was filed for. Deleted by hand; logged as **CF-7** in the loop's own
`CONSUMER_FINDINGS.md`.

**The general lesson for using this tool**: [[agent-patch-loop-arbiter-gotchas]] said to arbitrate
by hand when a run does not converge. Extend it — **read the SETTLED block too, not only the
rulings**, because that is the half that outlives the run.

---

## 5.82 Session 52 — `P1-130`'s fix broke a mutation anchor, CI went red for two pushes, and every agent-loop finding was re-driven

⚠️ **CI WAS RED ON THE TWO PUSHES THAT CLOSED `P1-130`, INCLUDING THE `v1.35.0` TAG PUSH**, and the
previous session ended before those runs landed — so the session closed on a state claim
(*"0 compile errors, 30 files in sync"*) that was true about the box and silent about the repo.
Both are correct facts; only one of them was checked. This is [[check-ci-before-trusting-docs]] at
the *end* of a session rather than the start: the rule says run `gh run list` before the first claim
about state, and a claim made while runs are still in flight is a claim about a state that does not
exist yet. **Runs 31976714399 and 31976656105, both `X checks`, both at `Mutation anchors still
match`, and the whole 27-job matrix behind that gate never ran.**

**Cause, and it is the gate working.** `P1-130` split `ModifyStopPrice`'s single
`ATM_STOP_ORDER_NOT_FOUND` log call into **two** — §5.81's point that an absent order and a
present-but-terminal one are not the same news — and `mutate_p0_67.py` anchored on that call. The
find-string went from unique to **matching twice**, and `check_anchors.py` refuses an ambiguous
anchor exactly as it refuses a missing one:

```
mutate_p0_67.py          1 BROKEN ANCHOR(S)
  x DynamicAtmManager.cs matched 2 time(s): ModifyStopPrice reports success even when
    no working stop order exists
```

⚠️ **This is the failure mode [[mutation-anchors-go-stale]] describes, arriving by its LESS obvious
route.** The memory says a battery whose find-string stops matching prints `[SKIP]` and scores a
survivor. Here the string still matched — it matched *more*. Both directions are silent when the
battery is run and loud only in the gate, which is the argument for the gate: **an anchor is a
claim of uniqueness, and a fix that ADDS a call site falsifies it just as thoroughly as one that
deletes it.** Duplicating code is the ordinary way a defect gets fixed, so this route will recur.

**Repointed, not retired** (house rule, fourth time — after `P2-92`, the two `mutate_p1105` anchors,
and the six in `mutate_p2109`). The new anchor is `Order present = null;` — the first statement
after the search loop has failed — which is the **identical insertion point**, so the mutant still
injects `if (true) return true;` and still expresses "ModifyStopPrice claims success with no live
stop". Evidence that the repoint landed somewhere reachable rather than passing vacuously: the
battery re-ran **10/10 KILLED, SURVIVORS: none**, and that mutant fails **5** tests (2034 → 2029).
A repoint is not verified by `check_anchors.py` going green — that only proves the string is unique
again. **Run the battery.**

### The agent-loop findings were re-driven, and one of them did not survive contact

All seven `CF-` findings filed in §5.81's session were fixed upstream (`e2ed6bd`) and every one was
re-measured against **this repo** at `ce5fdc17`, 2034 green. **CF-2, CF-3, CF-4, CF-6 and CF-7 are
closed on measurement; CF-1 is 75% done; CF-5 is re-opened; CF-8 and CF-9 are new.** The detail
lives in the loop's own `docs/architecture/CONSUMER_FINDINGS.md`; three things belong here because
they are about how this repo uses the tool.

⚠️ **The install in `.venv` is NOT the pin.** `requirements.txt` says `@v0.6.7`, `pip show` says
`Version: 0.6.7`, and the actual install is an **editable pointer to `C:\Users\vinay\agent-loop`** —
whatever that checkout is on, thousands of insertions past the tag. Every version surface agrees
with the tag and **none of them describes the code that ran**. `python -m agent_loop --version` now
prints the resolved *path* as well as the number, and the path is the only one of the two that has
ever been true here. This matters for the same reason a deploy is verified by content and never by
the path the tool believes in: *a run attributed to "agent-loop v0.6.7" in a commit message here
means nothing.*

✅ **CF-7 — the poisoned-settled-decision check — works, and it was checked the right way round.**
It drops §5.81's verbatim pair, **and** leaves a legitimate settled decision containing the word
"only" alone. The second half is the one that matters: [[detector-needs-a-negative-test]], because
a validator that dropped every settled decision would pass the positive test perfectly. It is
keyed on the literal word "only" though, so a paraphrase walks past it — **keep reading the SETTLED
block by hand.** §5.81's instruction stands unchanged.

🆕 **A zero-cost way to test anything upstream of the first model call**, worth reusing: give the
probe ticket a deliberately **unresolvable anchor**. The run takes the worktree, runs the baseline
suite, prints the gate line you are trying to observe, then dies at region extraction — **no model
call, no spend**. That is how CF-6 was verified. Two probe tickets were driven this way and both
were deleted afterwards; `git status` was checked clean.

⚠️ **A file can read as modified while being byte-identical.** After the battery,
`git status --porcelain` reported ` M addons/DynamicAtmManager.cs` and `git diff` printed nothing
but a CRLF warning. Compared against the blob directly: **53355 bytes both sides, byte identical.**
A `git status` alone would have started a hunt for a leftover mutant
([[mutation-battery-killed-leaves-a-mutant]] is a real hazard and this was not it). Compare with
`git cat-file blob HEAD:<path>` before believing either answer — the same tool that
[[a-worktree-is-not-a-fresh-checkout]] names for the opposite error.

---

## 5.83 Session 52 — `P2-127` slice 1: the fleet tree, and three decisions the loop got to by default

The layout question is SETTLED (§4, re-confirmed against the operator's own counter-proposal on
2026-08-16) and was not re-opened. What landed is the **decision class**, `BridgeFleetView.cs`,
and it was taken first for the reason `P2-127`'s plan entry gives: `ui/index.html` is in no test
build and no mutation battery, so anything decided in JavaScript is decided somewhere nothing can
check. Suite **444/15 → 467/0** across 77 tests, battery **16/16**, `nt_compile` **0 errors**,
`deploy --verify` **31 files / 0 orphans**. **Nothing renders it yet** — the entry stays OPEN.

**The defect it exists for was measured before it was designed**, from one payload that carries
both scales at once:

```
"rows":   [ { "verdict": "Idle", "severity": 5 } ]   <- CopierSnapshotJson,  0 is WORST
"system": { "severity": "warn" }                     <- CopierStatusSeverity, 0 is BEST
```

⚠️ **So the discriminating test is not that each scale converts correctly — it is that the SAME
NUMBER means opposite things on the two.** A single shared conversion passes every other assertion
in that test method and fails only that one. This is the `P2-109` shape again: *the regression test
is that the two answers DIFFER*.

### The loop returned NOT_CONVERGING, and hand-arbitration changed three things

Four rounds, all 15 acceptance tests green from round 2, no regressions — and blocking findings
`2 → 4 → 2` with **zero overlap between consecutive rounds**, which is the loop's own stated
signal that revisions are exposing new surface rather than closing the defect. [[agent-patch-loop-arbiter-gotchas]]
says arbitrate by hand at that point, and it was right again:

* ⚠️ **The arbiter UPHELD a finding the ticket had explicitly scoped OUT** — that the system
  severity is not wired into the tree — when the ticket's SCOPE paragraph names that as a later
  slice. Its own ruling format has an `out-of-scope` count, and it reported `out-of-scope=0`.
* ✅ **One upheld finding was real and my tests had missed it**: a leader and a follower may hold
  several relationships, one per instrument, so a tree built per ROW lists that account twice.
  **Both live rows are instrument-less, so every test written against the box as it stands passes
  under the defect.** Second session running in which the minority reviewer found the gap between
  my assertions.
* ⚠️ **The arbiter REJECTED a correct finding as "stable and correct"**: `List<T>.Sort` is
  documented UNSTABLE, and `groups` is a `Dictionary` whose enumeration order is explicitly
  unspecified. **Equal ranks are the NORMAL case here** — all 95 unlinked accounts on this box tie
  — so without a name tie-break the page re-orders itself between refreshes that saw identical
  data. Verified by mutation rather than by reading: removing the tie-break fails both ordering
  assertions.

### ⚠️ An INAPPLICABLE state is not an UNREADABLE one, and the ticket's silence chose the wrong one

The ticket said "fail closed" for unknown states and said nothing about an account in **no** copier
relationship. The model applied fail-closed to both and ranked every unlinked account **WORST** —
which on this box is **95 of 97 accounts painted permanently red**. That is *an alarm that is
always on is off*, for the **eighth** time in this system, arrived at by a route none of the
previous seven took: not a rule that fires too often, but a **default applied to a set it was never
about**. [[check-the-exemplar-belongs-to-the-class]] in reverse — the class was right and the
membership test was missing.

Ranking them `ok` is the opposite lie. `NotApplicableRank` sits **above** every real rank, so it
sorts as the least severe thing and a renderer can colour it as neither. It is **deliberately
temporary** — an unlinked account still has a GUARD state, which is what the operator actually
wants for it, and that is the next slice — and a test pins it so that change has to be conscious.

### ⚠️ The battery went 15/15 on its first run and the sixteenth mutant is the whole point

House rule says a one-round green is when to trust it least, so the green was probed rather than
believed. Dropping the `Unlinked` node when it has **no children** survived the entire suite,
because every other test supplies a spare account and the empty case was never driven. **An absent
node and an empty one read identically to whatever renders them** — the agent loop's own `CF-9`
arriving at a second surface within the same session. The test and the mutant both exist now.

### Two process notes

⚠️ **The red acceptance tests were PUSHED, and bridge CI went red for it.** The loop builds its
worktree from `HEAD`, so the tests must be committed before the run — but *committed* is not
*pushed*. Session 51's resolution was to commit locally and squash with the fix so no commit on
`main` is ever red, and departing from it put a knowingly-red run in the history. **A red run you
meant looks exactly like one you did not**, which is precisely what makes
[[check-ci-before-trusting-docs]] expensive.

⚠️ **The loop's worktree does not populate submodules**, so this repo's two tests that assert on
the vendored core failed at its baseline: **439 passed / 17 failed in the worktree against 444/15
here**. The loop handled it correctly — it counted them as expected failures and reported no
regression — but two real gates were dark for the whole run and nothing in the output said so.
Logged against the loop as a consumer finding.
