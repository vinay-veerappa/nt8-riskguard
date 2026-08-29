# RISKGUARD_BROWSER_GATE_PLAN.md

**Status:** v1 — reviewed plan (external review pass 2026-08-29 folded in; V1 cut defined in §3). Still nothing built.
**Created:** 2026-08-29. **Last updated:** 2026-08-29.
**Origin:** user saw https://milkmantrades.com/buy-lock.html — "I am sure we can convert our riskguard into a chrome extension as well to deal with my tradingview and tradovate systems."
**Decision already made:** when built, it lives in this repo at `browser/`. NOT a new repo, NOT a vendored submodule of the bridge.

---

## 0. What this is (one paragraph, updated 2026-08-29 review pass)

A **Node daemon + launcher** that blocks **order entry** on **TradingView Desktop** (with the web extension and Tradovate adapters parked for later) when a lock is live. RiskGuard guards the NT8 broker connection: an order submitted from TradingView reaches the broker without ever touching NT8, so RiskGuard sees it only **after** the fill (react, flatten, lockout). A CDP overlay — injected into the same Electron/Chromium DOM the MCP already drives — can stop the click **before** submission. It is a pre-trade gate for a surface the C# guard cannot reach; it does not replace RiskGuard, it closes a hole next to it. Safety is defined by **exposure effect, not button side** (§5.4): while locked, generic directional submissions are blocked and explicit Close / Flatten / Cancel always work.

**Framing that must survive every design review in this doc:** this is *friction, not a vault* — "blocks verified DOM entry paths on the pinned TradingView build", never "universal order rejection" (§4a contract). Cool-state you removing options from hot-state you. Any feature that pretends to be enforceable from inside the same browser is a lie; see §9.

---
---

## 1. Why a button does anything (the behavioral case, distilled)

From the milkman page (credit: milkmantrades.com). Accounts rarely die in one trade; they die across a series of decisions that each looked reasonable on its own. The engine is:

> Loss → feeling you can't sit with → "this time I'll do it right" → reload → loss

Key insights worth keeping in the product brief:

1. **The reload thought is a prediction.** "This time I've learned my lesson" is testable and has a record. Write the prediction down with a date and a number before acting on it.
2. **The trade is doing a job, and the job is not profit.** Putting money back repairs a belief. Sitting still makes the loss final — that's exactly why sitting still is the expensive part.
3. **Four problems, one mechanism** — green morning = can't stop, red morning = can't accept, no setup = can't sit out, blown account = can't let it be final. All four are an inability to be done. **Flat is a position.** It's the one position that's hard to hold.
4. **Afternoon giveback is the reload loop compressed into one day** — $500 you can't accept turning into $5,000. Not a separate discipline problem.
5. **The urge arrives dressed as analysis** ("volume is picking up", "same setup as this morning", "just a small one"). Test: say the setup out loud in one sentence before clicking. Real setups survive being spoken; impulses fall apart halfway through.
6. **Urges break by themselves** — rise, peak, pass, usually inside 30 minutes. You don't win the argument, you outlast it.
7. **The dangerous thought is not the first slip** — it's "well, I've already broken the rule, might as well."
8. **Friction beats willpower.** Present-you removes future-you's options. Do not plan around future-you's judgment.

*One warning from the source, kept verbatim in spirit:* building the tool can quietly become a way to spend the day near the market. Tuning the lock instead of being away from the screen is the loop finding a new costume.

---

## 2. What exists (milkman v1/v2 inventory)

### v1 (397 lines, ~8 KB) — ship parity with this
- Manual lock only: pick duration from toolbar popup, Buy stops working.
- Durations 15 min → 3:00 PM Central close; plus "until I unlock it" requiring typing `UNLOCK`.
- **Tech:** MV3 content script injected at `document_start`, match `*://*.tradingview.com/*`, all frames. Listens on `window` with `capture: true` for `pointerdown/up, mousedown/up, click, dblclick` + Enter/Space on keydown/keyup — capture phase kills the event before any page handler sees it.
- **Anchor:** `data-name="side-control-buy"` (class hashes rotate between TV builds; class prefixes and label text are fallbacks only).
- Submit conditionally blocked: only while the ticket's Buy side is active. Sell tickets and order management pass through untouched.
- Visible feedback: MutationObserver on 400 ms debounce greys locked controls with dashed red outline; click throws toast "Buy is locked, you locked it for a reason." Badge `ON` while lock is live.
- **Storage:** `chrome.storage.local` = `{ locked, lockUntil }`. Permissions: **storage only**. No network calls anywhere.

### v2 (694 lines, 12 KB, self-declared WIP) — feature targets
- **Auto-lock on daily PnL.** Max loss AND max gain in dollars; either trips a hard lock for a chosen number of hours. Gain side matters as much as loss side (green-morning "can't stop" is the same failure as red-morning "can't accept").
- **Daily schedule** on the Central clock, can wrap past midnight. Set once, afternoon closed by default.
- **Frozen settings.** While a hard lock runs, limits and schedule are uneditable — hot-state you can't widen your own rails.
- PnL source: Daily PnL field in TradingView's account-manager header, scraped every 2 s from an open tab. Permissions: storage + alarms.
- Author's own health warning: it reads markup TradingView can change silently; **a lock that silently stops firing is worse than no lock** — check the badge says ON.

### The author's own escape-hatch list (honest, keep the same list in our docs)
chrome://extensions disable · another browser/profile/incognito · broker desktop or mobile app · changing the computer clock. "A few seconds of friction at the moment of the urge is often enough, because the urge is on a clock and you are only trying to outlast it."

Their field-tested ways to raise friction: buy-lock, one-tap re-buy.

---

## 3. Architecture (when built) — V1 CUT (review finding 11)

The full tree below shows the *destination*; the V1 build is the subset marked **[V1]**. The V1 scope statement — one testable proposition — is:

> **When the gate reports `ENFORCING`, the known TradingView Desktop entry paths cannot create exposure, and the explicit emergency exits (Close / Flatten / Cancel) remain available.**

V1 boundaries: TV Desktop only · one installed TV version · one integrated broker · one explicitly configured account · **Node daemon, no cross-language source import** (finding 8) · wrapper launcher · manual + schedule locks · generic directional submissions blocked · explicit Close/Flatten/Cancel preserved · persistent lock state · independent heartbeat witness · frame inventory + blocker canary · append-only lock journal · **no** PnL triggers, **no** behavioral coaching, **no** MV3 extension, **no** Tradovate adapter, **no** narration/journaling.

```
browser/
  daemon/                        # PRIMARY plane: TV Desktop via CDP (decided, §4a) — Node, ESM
    gate_daemon.js               # [V1] attach over CDP (127.0.0.1:9222); lock engine + injector host
    lock_state/                  # [V1] atomic lock-state file (write-temp+rename+fsync); single-owner; startup restore
    journal/                     # [V1] append-only lock-transition JSONL (triggered/restored/extended/
                                 #      expired/unlock-attempted/attachment-lost/health-changed)
    inject/
      event_kill.js              # [V1] capture-phase blocker — ONE copy, shared (see inject/ note below)
      dom_watch.js               # frame inventory, greying/toast, anchor probes, canary host
    witness.js                   # [V1] independent heartbeat: daemon → witness; witness lives OUTSIDE
                                 #      the daemon process (launcher-hosted) so a dead daemon's
                                 #      heartbeat gap is observable by something that survives (§5.2)
    manifest.json                # [V1] coverage manifest: every enabled trading surface → is its
                                 #      entry path intercepted? unknown-enabled-surface ⇒ INERT/STALE
    status/                      # localhost status page (launcher-hosted read-only witness view)
  launcher/
    launch_tv_debug wrapper      # [V1] launches TV with CDP port, starts daemon, then runs the
                                 #      readiness handshake (§4a); TV is NOT declared ready until
                                 #      the witness confirms ENFORCING
  compat/
    probe.js                     # [V1] read-only probe against the INSTALLED TV build: anchors,
                                 #      ticket structure, account header — gates any release
  tests/
    fixtures/…                   # static ticket DOM copies for unit tests (never sufficient alone, §8)
    acceptance.test.js           # [V1] the never-trap battery + acceptance matrix (§8.2)
  extension/                     # MV3 plane for web surfaces — PARKED (out of V1; revive only if a
    …                            #   web trading need appears)
  sites/tradovate/               # PARKED (§6 note retained for future discovery pass)
```

**Runtime decision (finding 8):** the daemon is **Node**, not Python. The earlier draft had a Python daemon importing the MCP's Node `connection.js` — that does not work and is withdrawn. The MCP stays the on-demand plane; the daemon is a separate Node process. Connection-level reuse is handled by **option 2 of the review**: a small local CDP adapter living in *this* repo, with **contract tests** asserting the adapter's behavior matches the MCP's (same port resolution, same IPv4 default, same target-pick semantics) — a pinned-behavior contract instead of a source import. If drift hurts enough, a genuinely shared package is the later answer; not a cross-repo private import.

**Single-copy rule for safety-critical injection:** `event_kill.js` exists **once** in this repo (`daemon/inject/`). The parked extension must not carry its own copy — if it's ever revived, it consumes the same file. Two copies of a submission blocker is a drift hazard on exactly the component that must never diverge.

**Design rules:**
- Core never imports from site adapters; adapters declare `{ id, matches, anchors: {...}, isDirectionalContext(), readPnl(), lock(target), unlock(target) }`.
- Never key on class hashes (they rotate). Anchor on stable attributes (`data-name`, `data-testid`, literal button text as last fallback), and record each anchor with the date it was last observed valid in `anchors.md`.
- **Exposure rule replaces the old "exits never blocked" one-liner** (finding 1): V1 = directional submissions blocked (Buy AND Sell), explicit Close/Flatten/Cancel always allowed. Full rule and rationale: §5.4. ADR-020's spirit survives — the 15:59 liquidation path is exactly what `Flatten` is.

---

## 4. Surfaces matrix (why this isn't RiskGuard-converted, it's RiskGuard-extended)

| Surface | Auto-tradable | Guard today | With gate |
|---|---|---|---|
| NT8 chart/dom | yes | RiskGuard FSM (pre-trade via bridge lockout when armed) | unchanged |
| **TradingView Desktop app** | yes (integrated brokers) | **none until fill** | **script injected via CDP daemon — see §4a** |
| TradingView web + broker panel | yes (Tradovate/APX integrated brokers) | **none until fill** → RiskGuard reacts post-fill via account state | **click blocked pre-submit** when lock live |
| Tradovate web | yes | **none until fill** | **click blocked pre-submit** |
| Broker mobile app | yes | none | **out of scope — documented gap** (trade from the desk; mobile is for monitoring) |
| TOS Desktop | yes | none (separate platform) | out of scope |

âš ï¸ The copier does not help here: followers copy the leader (NT8, guarded). A browser-side order reaches only its own account. But if the locked browser belongs to a *copier leader*, blocking it protects every follower at once.

**One-source-of-truth question for design:** if the extension computes its own daily PnL from a scrape and RiskGuard computes account state from the bridge, two numbers that can disagree (PnL basis: balance vs equity; open PnL included or not; EOD vs intraday anchor). Rule: either the extension is standalone with a *named, visible* number source, or v2 syncs lock state from RiskGuard via localhost (see §10) and its own PnL logic is deleted. No third state where two brains both fire.

### 4a. TradingView Desktop — the actual case that matters (decided 2026-08-29)

User trades from **TradingView Desktop**, not the browser. Turns out this is buildable, and *stronger* than the extension route:

- **TV Desktop is Electron/Chromium** — same rendering engine, same DOM, same `data-name="side-control-buy"` anchors as the web app. The order ticket, the account header, the PnL field: all real DOM. The milkman content-script *code* ports; his *packaging* does not.
- **Electron does not load Chrome extensions.** `--load-extension` is stripped/ignored in Electron apps, so the MV3 route is dead on arrival here. Do not chase it.
- **The door is CDP, and it is already open.** This box already launches TV Desktop with a debugger port via the `tradingview_tv_launch` tooling (`--remote-debugging-port=9222`, including the MSIX relaunch fallback). CDP replaces every extension capability we need:

| Extension capability | CDP equivalent |
|---|---|
| content script @ `document_start`, all frames | `Page.addScriptToEvaluateOnNewDocument` (re-injects on every navigation/reload automatically) |
| capture-phase event kill | the exact same injected script — capture phase is a DOM fact, not an extension feature |
| `chrome.storage.local` | **persistent lock-state file owned by the daemon** — atomic write (temp+rename+fsync), restored on restart; corrupt/unreadable state ⇒ `STALE/LOCKED`, never OFF (§5.3, review finding 3) |
| popup + badge | launcher-hosted witness view (read-only). The daemon **cannot** honestly render its own health — a dead daemon updates nothing (finding 2); the witness (§5.2) is what reports |
| MutationObserver greying/toast | unchanged — it's all just injected JS |

- **Architecture for the Desktop plane:** a small local **Node** daemon attaches to the TV process over CDP (127.0.0.1:9222), injects the gate script into every target (main + iframes), and owns the lock engine + the persistent lock-state file (§5.3). Runtime choice and reuse contract: §3 (finding 8 — no cross-language import).
- **This is stronger than the extension, not a compromise:**
  1. The daemon is local code we own, sitting next to RiskGuard and the bridge — bridge sync (§5.1 row 7, §10) becomes a plain localhost call, no chrome.runtime messaging.
  2. No permission sandbox theater — storage, alarms, network rules are our own.
  3. **The launcher becomes the constraint.** If TV Desktop only ever gets launched via the wrapper (which enables CDP), the gate is *automatically present* every session. The failure mode moves from "did the extension get toggled off?" (invisible) to "did I launch via the shortcut?" (visible, once, at session start). Cool-state you writes the wrapper; hot-state you would have to go find `tradingview.exe` directly — a step up in friction from a chrome://extensions toggle.
- **Trap already known on this box:** the CDP port blocked on some installs (MSIX/Store build) — the launcher already handles that with the local-copy relaunch; the daemon must *require* the port be live and **refuse to run silent** (`STALE`/red state) if TV is reachable but the daemon isn't attached. Symmetry with §5.2: the gate must be able to announce its own absence.
- **Escape hatches, honestly:** kill the daemon (`taskkill`), launch `tradingview.exe` directly without the port, use the broker's own app. Same tier as the extension list in §9 — but each is a deliberate, visible act rather than a silent toggle. The TV-only-opens-via-wrapper discipline is the real upgrade.

**Tradovate note:** if Tradovate is used via *web*, the extension/browser path (§3) applies. If a Tradovate desktop client exists in the workflow, same CDP question applies — open question for §11.

### 4b. `tradingview-mcp` — reuse, don't duplicate (verified 2026-08-29)

There is already a CDP client on this box: `C:\Users\vinay\tvDownloadOHLC\tradingview-mcp` — a local Node MCP server (84 tools) serving `chart_get_state`, OHLCV, pine drawing reads, `draw_shape`, UI control, alerts, replay, screenshots, and its own `tv_launch` (CDP port + MSIX fallback). It connects to **the same port 9222** into the same TV Desktop process. Topology therefore:

```
                     CDP port 9222 (localhost, IPv4)
                      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
              tradingview-mcp                  gate daemon
        (stdio MCP, on-demand,             (always-on, event-driven,
         agent-facing request/response)     trader-facing enforcement)
```

**Division of labor — anything one-shot and request/response belongs in the MCP; anything persistent and event-driven belongs in the daemon:**

| Concern | Home | Notes |
|---|---|---|
| Read chart state/studies/prices | MCP (exists) | |
| Push computed context onto chart | MCP (draw_shape exists; add session-overlay tool) | §13.2 use case 5 |
| Read hand-drawn drawings as data | MCP (pine drawing reads exist) | §13.3 use case 5 |
| Alert *setting* | MCP (exists) | |
| Alert *firing* as events | daemon (needs event watching) | |
| One-shot scrapes (option chains, trade panel dump) | MCP (new tools) | fits request/response |
| Lock engine, event-kill, DOM-watch, urge telemetry, fill journaling, stale alarm | **daemon** | the whole §5 model |
| Launcher | MCP `tv_launch`, extended to arm the daemon after launch | |

**Code reuse (rewritten per finding 8):** the daemon does **not** import the MCP's `src/connection.js` — different process, and a runtime dependency on another repo's private source is fragile. Instead: a small local CDP adapter in this repo, plus **contract tests** asserting adapter behavior matches the MCP's on the points that matter (port resolution + IPv4-vs-::1 default, `/json/list` target picking, evaluate semantics). The known traps (Electron resolves `::1` first; the debug port binds IPv4 only; MSIX path) are re-solved once here and pinned by those tests. Anchors stay shared (one `anchors.md`).

**Known issues in the MCP that this plan inherits (fix before building on it):**
1. ~~`tests/launch.test.js` is red on this box today~~ **RESOLVED 2026-08-29**: the fork now carries the upstream deps-seam fix and the full unit battery is 328/328 green (see the sync session). Kept here as the reminder of the rule: never build on a repo whose suite you haven't run.
2. Missing CDP plumbing for the daemon needs: `Page.addScriptToEvaluateOnNewDocument` (injection on every new document — absent from connection.js) and `Target.setAutoAttach`-style multi-target handling (the order ticket renders in iframes; connection.js currently targets one page).
3. **Governance rule, decided here:** the MCP has `ui_click` and can therefore click the Buy button — but the daemon's capture-phase event-kill deadens **MCP-dispatched clicks too** (a synthetic click is still a DOM event). The gate survives the agent. Complementary rule: the MCP gains **no order-placement tools, ever** — same deny-only posture as §13.5's governance line.

---

## 5. Lock model

### 5.1 Trigger types (V1 = rows 1–2 only; the rest carry their own gate conditions)

| # | Trigger | Source | V1? | Semantics |
|---|---|---|---|---|
| 1 | Manual lock | user picks duration | **V1** | no unlock button until it expires; or manual-unlock requiring typed `UNLOCK` |
| 2 | Daily schedule | clock, Central, wraps midnight | **V1** | entry locked inside window; set once |
| 3 | Daily loss hit | PnL scrape | **NOT V1** | hard lock for N hours. Blocked on the full PnL-semantics dependency list in §5.5 |
| 4 | Daily gain hit | PnL scrape | **NOT V1** | same; protects giveback AND prop-firm best-day consistency share |
| 5 | Loss-streak counter | N consecutive losing round-trips | NO | cooldown, not hard lock |
| 6 | Cooldown after flatten | fill events via adapter | NO | no re-entry for X minutes after going flat |
| 7 | RiskGuard sync | bridge → localhost | V1.5 | latched, reason-specific, revision-stamped — see §5.5b. **"Release with recovery" is explicitly rejected** — see that section |
| 8 | staleHealth | heartbeat witness (§4a) | **V1** | lock that engages when the gate cannot prove it is enforcing |

### 5.2 Gate health — the four states + the independent witness (review finding 2 & 6)

**Health vocabulary is borrowed from this repo's own `docs/UI_REDESIGN_DESIGN.md:41-71`, not invented:** `CONFIGURED` (written down, nothing computes it) → `EVALUATED` (being measured) → `ENFORCING` (actively blocking, evidence in hand) → `INERT` (present but proving nothing). The milkman `ON/STALE/OFF` badge maps onto these; the UI may show `ON`, but **internally the only states that exist are these four**, and `ON` may never be displayed unless the state is `ENFORCING`.

1. **Anchor liveness probe.** Every 60 s the adapter asserts its anchors still resolve. But an anchor resolving does **not** prove enforcement (finding 6): the listener can be absent from one iframe, removed by navigation, or attached too late. So the probe is a *stack*, and health is the minimum:
   - anchor recognized on the pinned build
   - correct account recognized (account-switch detection — see §5.5)
   - every relevant frame injected (frame inventory, from CDP target list, checked per navigation)
   - **event-blocker canary**: the injected script fires a synthetic event at a sacrificial control and verifies the interceptor deadened it — the *blocker itself* is tested, not just the anchor it parks on
   - lock engine loaded and lock state readable
   - source data fresh (for anything that scrapes)
2. **The witness problem — a dead daemon cannot report that it is dead (finding 2).** Everything in (1) runs inside the daemon; a crashed daemon updates nothing. So an **independent witness** owns the truth:
   - the launcher (and later the NT8 bridge) watches a daemon heartbeat: ≥ 1/5 s, containing daemon session id, PID, attached target ids, frame inventory, injection status, canary result, lock-state file hash
   - the launcher does **not** declare TradingView ready until the witness has seen a heartbeat with `ENFORCING` evidence; until then it shows the gate as `CONFIGURED/NOT-ENFORCING`
   - the heartbeat file is written by the daemon but *read* by the launcher/RiskGuard UI — the consumer is a different process, so daemon death is observable by something that survives it
   - heartbeat gap → NT8-side RiskGuard UI shows browser gate `STALE` (v1.5 once bridge sync exists; until then the launcher window/notification carries it)
3. **Stale-source alarm (retained for v1.5 with PnL).** If a rule depends on scraped PnL and no reading for > 2 min while a position could exist → `EVALUATED/STALE` state, toast, optional mechanical bell. **Fail-closed** default: PnL unknown ⇒ treat as locked for the remainder of the day window; setting, stated on the popup. (Rows 3/4 are out of V1; the fail-closed principle is stated now because it generalizes.)

### 5.3 Lock semantics, borrowed and hardened

- **Hard lock:** during any hard lock: trigger list, limits, and schedule are **frozen** (v2 parity).
- **Unlock paths:** timer expiry (never before the stated time — "make unlocking slow by design, so the unlock lands tomorrow when you no longer want it"); typed-`UNLOCK` for the manual-until-can't variant; optionally unlock word decided at lock time (random string shown frozen on screen at the time of locking, not pickable at unlock time).
- **One-sentence check (behavioral):** on any manual-unlock attempt, the popup requires one sentence describing the setup before the input accepts typing. If you can't type the sentence, the urge is the author. (Maps to §1.5.)
- **Prediction note (optional v1.5, unique to our stack):** before a scheduled-end unlock, optionally demand/offer a note ("next session I expect …") posted to `.agent` outcomes ledger via `capture_outcome` — scoreable later, per §1.1.
- **Persistence & restoration (finding 3, V1 must-have).** Lock state lives in the daemon process only at runtime; the **authoritative copy is an atomically-written local lock file** (write-temp + rename, fsynced). On daemon start: read, validate, restore. Rules:
  - A lock that was active at shutdown comes back active after restart — killing the daemon may never clear a lock (that would defeat "never before the stated time").
  - Corrupt or unreadable lock state ⇒ the gate comes up in `STALE/LOCKED` (locked, visibly unproven), **never** `OFF`.
  - **Single-instance ownership:** the lock file and heartbeat are owned by exactly one daemon; a second instance refuses to start rather than racing for ownership.
  - **Append-only lock-transition journal** alongside the state file: triggered, restored, extended, expired, unlock-attempted, attachment-lost, health-changed. This is the audit trail for "why was I locked at 11:40".
- **Clock policy.** Active countdowns use a **monotonic clock** (never wall-clock). Wall-clock is only for schedules, and schedule evaluation detects clock jumps, sleep/resume, DST and timezone changes — a clock jump forward may trigger a schedule lock evaluation, never shorten or cancel an active lock.
- **One-sentence check (behavioral):** on any manual-unlock attempt, the popup requires one sentence describing the setup before the input accepts typing. If you can't type the sentence, the urge is the author. (Maps to §1.5.)
- **Prediction note (optional v1.5):** before a scheduled-end unlock, optionally demand/offer a note ("next session I expect …") posted to `.agent` outcomes ledger via `capture_outcome` — scoreable later, per §1.1.

### 5.4 Exposure rule (replaces "Buy locked, Sell allowed" — review finding 1 & 5)

The milkman model (block side-control-buy) is **semantically wrong for futures**, and the draft repeated the error. Buy/Sell are *button sides*, not risk postures:

- "Sell is open during a Buy lock" permits opening/adding shorts.
- Blocking Buy can block *closing* a short.
- Worst case: long 3, submit Sell 4 through the generic ticket = reversal — one click that closes the long AND opens a short, fully inside a "Sell allowed" policy.

The rule that survives review:

> **While locked, allow an action only when it can be proven to cancel risk or reduce absolute exposure without crossing through flat.**

And the V1 implementation is deliberately narrower still:

> **V1 blocks all generic directional submissions (Buy and Sell alike) and preserves only explicit `Close`, `Flatten`, and `Cancel` controls.** No reduction-by-opposite-side, no size-aware allowances, no exceptions. If position/quantity/account meaning is *uncertain*, default is block (directional) + allow (explicit emergency controls).

Consequences, stated plainly:
- "Order management allowed" from the earlier draft is too broad and is **withdrawn**: removing a protective stop, widening a stop, increasing a working entry's quantity, and cancel-replace that flips through flat are all exposure-increasing or exposure-destabilizing. V1 policy: working-order *cancellation* always allowed; *modifications* block-or-warn per an explicitly chosen policy, default Block. Tightening-protection allowances are a V1.5 classification problem (§13 parking lot inherits it).
- The never-trap guarantee is preserved: explicit Close / Flatten / Cancel must pass from **every** supported locked state, and that is its own test battery (§8).
- The acceptance matrix in §8.2 is the contract; any code change that affects action classification re-runs it.

### 5.5 PnL-trigger prerequisites (why rows 3/4 are not V1 — review finding 7)

The one-brain rule (§4) already says scraped PnL and RiskGuard's account state must not both fire. Before an automatic PnL lock exists at all, every one of these is resolved, in writing:

- exact account identity (one explicitly configured account in V1; no identity ⇒ no trigger)
- realized vs unrealized basis (defined per firm rule: daily-loss basis is prior-day balance vs equity — the prop-firm engine already encodes this distinction)
- fees and commissions included or excluded, matching the firm's own accounting
- reset boundary and timezone (5pm CT? session close?)
- multi-tab conflict handling (two tabs reading different accounts)
- account-switch detection mid-session (chart switched to another account ⇒ trigger source invalidates and health drops out of ENFORCING until re-verified)
- locale/currency parsing of the rendered PnL string
- behavior when two valid sources disagree (fail-closed)
- and the honest failure mode already recorded in §5.2: a lock that silently stops firing is worse than one that fires wrongly

### 5.5b Bridge sync — latched, reason-specific, revision-stamped (review finding 9)

"Release with recovery" (the old row-7 wording) is **rejected**: a transient bridge hiccup recovering must never clear a manual, scheduled, PnL, or RiskGuard lock. Effective state is a **union of independent latches**, each with its own owner, expiry, and clear-path:

```text
effectiveLock = manual OR schedule OR pnlTrip OR riskGuard OR staleHealth
```

- Clearing one reason never clears the others. Unlock = all reasons individually cleared.
- Bridge (RiskGuard) updates carry a **monotonically increasing revision number**; a stale/older revision arriving late can never unlock a newer latched state (the same generation-guard idea the MCP connection manager uses).
- A lost bridge connection is itself a latch source (`staleHealth`), not a release.
- V1.5, after the daemon exists and the V1 cut is boring.

---

## 6. Tradovate adapter notes (open)

- Tradovate (incl. APX-branded portals) web frontend: DOM differs from TV, no `data-name` convention known. Discovery pass required: open order ticket, record stable attributes (probably `data-testid` or aria roles on the BUY/SELL toggle, and the daily PnL in the account bar). Fill `src/sites/tradovate/anchors.md` as part of the first build task, not later.
- Read daily PnL + account state from the DOM bar used by the active prop-firm portal; if the clean approach is its own REST/MMT call, that violates zero-network — do scout, but default is DOM-only.
- Same `_SIDE_CONTROL_` anchor probing policy (renamed generic): fail to STALE badge, never silently.

---

## 7. Permissions & data flow

- **Manifest V3.** Host permissions: energy-justified minimal — `*://*.tradingview.com/*`, Tradovate domains (exact list at build). Content scripts at `document_start`, `all_frames` (order tickets render in iframes on some portals).
- Permissions: `storage`, `alarms`. **No tabs, no scripting, no webRequest, no host wildcard, no network calls.** Daily PnL comes from a content script reading an already-open rendered page.
- Storage schema (versioned on day one, migration path in `storage.js`):

```jsonc
{
  "schemaVersion": 1,
  "locks": [{ "id": "manual-17:05:02", "level": "hard", "until": "epoch", "canUnlockEarly": false }],
  "rules": { "dailyLoss": 0, "dailyGain": 0, "lockHoursOnTrip": 0, "schedule": { "start": "12:00", "end": "15:00", "tz": "America/Chicago" } },
  "frozen": true,            // true while any hard lock is live
  "health": { "tv.anchor.lastOk": "...", "tv.pnl.lastRead": "..." }
}
```

Meltdown mode: `chrome://extensions` remains reachable; the popup shows the *failure we're risking* (their §"what it can't do", quoted in our docs) rather than pretending.

---

## 8. Testing plan (no shipped behavior without a test — repo convention)

### 8.1 Unit / fixture battery (necessary, never sufficient alone — review finding 10)

- **Fixture pages:** static HTML copies of the TV order ticket (trimmed, carrying the real anchors + a stub account header). These live in 	ests/fixtures/.
- **Playwright (headless):**
  1. manual lock 1 min → generic Buy blocked AND generic Sell blocked (acceptance: both directional paths dead, per §5.4).
  2. schedule lock (fake/monotonic clock) → same.
  3. **never-trap battery**: from every supported locked state, explicit Close / Flatten / Cancel still pass.
  4. anchor mutation (fixture renames attribute) → health leaves ENFORCING within 60 s, witness + launcher reflect it.
  5. **daemon killed mid-lock** → witness reports heartbeat gap; restart restores the active lock from the lock-state file; corrupt lock file ⇒ STALE/LOCKED, never OFF (finding 3).
  6. **blocker canary**: synthetic event at a sacrificial control is deadened on every frame; a frame missing injection ⇒ not ENFORCING (finding 6).
  7. second daemon instance refuses to start (single-owner lock file).
  8. monotonic-clock countdowns; wall-clock schedule detects clock jumps/sleep/DST and does not shorten an active lock.
- **CI:** battery wired to the guard's check_*.py gate pattern (a gate on disk wired to nothing is the known trap — every new defense gets its check_*.py in the same commit). The tradingview-mcp fork suite (328/328) is also a dependency and must stay green.

### 8.2 Acceptance matrix (the contract — re-run whenever action classification changes)

| Position | Requested action | Locked result |
|---|---|---|
| Flat | Buy | Block |
| Flat | Sell | Block |
| Long 3 | Buy 1 | Block |
| Long 3 | Sell 1 via generic ticket | Block in V1 (reduction-by-opposite-side is V1.5, only if proven reducing) |
| Long 3 | Explicit close / flatten | Allow |
| Long 3 | Sell 4 (reversal) | Block |
| Short 3 | Sell 1 | Block |
| Short 3 | Buy 1 via generic ticket | Block in V1; V1.5 only if proven reducing |
| Short 3 | Explicit close / flatten | Allow |
| Any | Cancel working order | Allow |
| Any | Increase working entry quantity | Block |
| Any | Remove / widen protective stop | Block (default policy; warn-only if explicitly chosen) |
| Unknown account / position | Directional submission | Block |
| Unknown account / position | Explicit flatten / cancel | Allow |

### 8.3 Release evidence (finding 10 — fixtures alone cannot detect a TV update)

1. **Read-only compatibility probe** against the *installed* TradingView build (version recorded): every anchor resolves, ticket + account-header structure matches `anchors.md`, coverage manifest accounts for every enabled trading surface. Failure ⇒ release blocked, gate stays EVALUATED. New `compat/probe.js` — read-only, never a live-trading tool.
2. **Simulation-account acceptance run**: full acceptance matrix (§8.2) executed against a **simulation account** end-to-end, then a fresh look at the lock journal for anything that tripped silently.
3. Only after both: the gate may claim ENFORCING on a live account. This mirrors the house rule recorded 2026-08-29 in the nt8 work: fixture batteries prove logic; acceptance runs prove the world still matches the fixtures.

### 8.4 Anchors.md upkeep

- File date touched on every TV deployment the gate runs against. This doc's §2 anchors were valid as of the milkman page fetch (2026-08-29), **not** verified against today's TradingView build — the compat probe's first job is dating them.
---

## 9. Security posture & escape hatches (kept honest, copied from source + mapped)

Bypass means (given, not claimed as solved): extension toggle, other browser/profile/incognito, broker mobile/desktop app, system clock change.

Honest tiers (their list, with our mapping):

1. **Reduce buying power at broker** — out of our hands; note as the real vault.
2. **Broker-side auto-liquidation at daily loss limit** — closest we have: RiskGuard already *does* this on NT8-routed accounts (FSM + emergency_flatten). This extension is the browser plane of the same idea.
3. **2FA to someone you trust** — recommended outside the tool.
4. **Delete saved payment/funding links** — user-side checklist, one-time, in the install README.
5. **Unlocking slow by design** — we build this (§5.3).

"One external constraint is worth about five self-administered ones" — keep the ratio honest: this extension is one of the self-administered ones, and the NT8 RiskGuard is the external constraint we already own.

---

## 10. Cross-project integration notes (for v2 thinking)

- **Bridge sync (the v2 payoff, superseded by §5.5b):** lock state read from the McpBridge over localhost (auth: token or loopback-only). Lock state becomes one artifact shared by NT8 guard + browser gate — but as **latched, reason-specific, revision-stamped** state (§5.5b), never a single boolean any transient recovery can clear. Same pin-on-tag discipline as bridge ↔ addon: a *versioned* endpoint, not a scraper; break on contract, fail to SAFE (latched-locked), never to unlocked.
- **Prop-firm rule presets:** daily loss/pnl numbers should default to the user's actual challenge rules (drawdown mode, daily allowance). We already have encoded, firm-official rule data via the prop-firm directory/simulator tools — a preset dropdown ("Apex 50K: DDB trailing-realized-EOD $2,250 â‡’ gain/loss trip at X") beats free-floating dollar guesses. The intra-day-trailing rule (the most-miscalculated one in the industry) is exactly the case where a hand-typed browser limit lies to you.
- **Consistency link:** dailyGain lock interacts with prop-firm best-day consistency gates — one outsized day effectively raises the remaining target (see prop-firm engine notes). Locking a green morning is this rule's browser-side twin.
- **Outcomes ledger / trader narrative:** unlock-time prediction notes and close-of-day "flat is a position" summaries can flow into `.agent` outcomes (`capture_outcome`) without any network from the extension — export file → script, or manual paste. Keep the extension itself network-zero; the post-processing is ours.

---

## 11. Open questions — STATUS after the review pass

**Answered / decided (2026-08-29 review pass):**
1. Surface: **TV Desktop only** for V1 (§4a). Tradovate stays §6-notes.
2. Accounts: V1 = **simulation only** until the §8.3 acceptance run passes on a sim account.
3. Trigger set: V1 = manual + schedule only (§5.1); PnL gated behind §5.5; loss-streak/cooldown parked.
4. Unlock discipline for V1: timer expiry + frozen settings during hard lock. One-sentence check / prediction notes = V1.5, decide when the gate is boring (§13.1 has the hooks).
5. RiskGuard sync: V1.5 with latched reason-union + revision stamps (§5.5b). V1 standalone with witness health.
6. NT8 mirror of gate health: V1.5, rides the bridge sync; RiskGuard UI gets a browser-gate health row only after ENFORCING is trustworthy.
7. ~~TV Desktop first?~~ **Decided — yes** (§4a); extension parked.

**Open for the build kickoff:**
- Which integrated broker inside TV Desktop is the one account (decides the ticket-adapter anchors).
- Daemon auto-restart policy at V1 (restart manually via launcher vs watchdog) — default: launcher restarts it, witness verifies.
- Modification policy default (Block vs Warn) — the review recommends Block for V1; confirm.

---

---

## 12. Parking lot

- Multi-account awareness (per-rule account identity) — presupposes §5.5 account identity work.
- Copier-leader awareness (blocking the leader protects followers) — revisit with bridge sync (§5.5b).
- Peak-equity giveback trigger (browser-side twin of `nt_prop_limits` givebackCapPct).
- News-window lock (blackout windows like PropFirmProtectionSuite's news shield, browser side).
- "Urge log" (time-stamped urge entries, re-exportable) — timed urge waves, per §1.6.
- Working-order modification classification: tighten-protection allowed, widen/increase blocked (the V1.5 slice of finding 5).
- Exposure-aware partial reductions via signed position + proposed qty (acceptance-matrix rows hard-blocked in V1).
- Pending-order exposure included in decisions.
- Auto-restart + state restoration + reattachment + canary after a daemon crash (V1.5).
- Calm retry feedback (one warning, then a quiet blocked-attempt counter, not repeated beeps).
- Support bundle: versions, recent heartbeat gaps, frame inventory, canary results, lock transitions.
- Trusted-person delayed unlock; OS-level wrapper enforcement.
- MV3 extension; Tradovate adapter; protocol-level request interception; multi-account; narration/journaling/review modes (see §13 brainstorms).
- VISUAL_SYSTEM palette conformity (ADR-018) IF a chart-side overlay ever ships.

---

## 13. Control-plane use-case catalog (the CDP link buys more than a lock)

The gate daemon is the first subscriber of a general capability: a **persistent, bidirectional channel between this repo's computed context and the live TV Desktop DOM** (chart pushes: injected drawings/HUD; pulls: DOM scrapes; behavior: deny + nudge). The use cases below split by whether they ride the **daemon** (always-on, event-driven) or the **MCP** (on-demand, agent-invoked — see §4b). Feasibility tier: **A** = plumbing exists today, **B** = new build but known technique, **C** = speculative/fragile.

### 13.1 Behavioral plane (the user's stated use case, 2026-08-29)

*"Logging my behaviour while trading, and somehow shouting at me if I am not doing things right and asking me to back off."*

This is the same product idea as the gate, one level up: **the gate is the mute button; this is the conscience.** Both ride the same daemon and the same DOM-watch injection. Split into three escalating lines of defense — **measure → warn → act** — because shouting without a log is nagging, and nagging gets ignored within a week:

**Line 1 — Measure (telemetry, always-on).** The DOM already exhibits every behavior worth scoring; the daemon timestamps it:

| Signal (all DOM-observable) | Proxy for |
|---|---|
| Order ticket opened / closed | itch to act |
| Buyâ†”Sell toggle flips on one ticket | indecision — the urge dressed as analysis (§1.5) |
| Stop-loss edited / removed / widened on a live ticket | moving the goalposts — the classic tell |
| Symbol switches per hour | chart-hopping / hunting for a setup that isn't there |
| Timeframe switches per 15 min | same, temporal flavor |
| Size changes before/at entry | sizing up off-plan |
| Clicks on Buy that get deadened by the gate, + any attempts to close the daemon | the direct record — this is the number the reload loop never had (§1.1) |
| Ticket opened then abandoned (no submit) | aborted impulses — the WINS to celebrate, not just the failures |
| Time sitting flat with market open | "flat is a position" — the metric the milkman essay says is hardest to hold (§1.3) |

Storage: local append-only JSONL (`.agent`-adjacent, same posture as outcomes ledger — local only, network-zero). Same schema discipline as `outcomes` in the memory store so `capture_outcome`/`recap_outcomes` can ingest a day's behavioral stats. **Tier A.**

**Line 2 — Warn (the shout).** Threshold rules over the telemetry, evaluated in-process, expressed on screen without any LLM in the hot path (deterministic, fast, never down):

- **Visual:** injected HUD band (top of chart, red/amber/green) — "STOP EDITS: 6 stop moves in 20 min." Amber for rising, red for tripped.
- **Audible:** OS beep / sound file per threshold trip — no network, no TTS dependency.
- **Language** (borrowed from the milkman essay, because it's already earned): "You are in the loop. Name it and write down the time." Not clever, not chatty. The shout is short *by design* — a paragraph at 11:40am is an invitation to argue.
- Escalation ladder: amber flash → beep → red band → (only after N unheeded reds in one session) **auto-escalate to a lock** (§5 trigger rows). Warn→lock handoff is the design's teeth: the coach can call the bouncer.

Examples of thresholds (all config, all frozen while a hard lock runs — §5.3): N stop-edits on one ticket in M min; N symbol switches per hour; N consecutive losing round-trips (§5.1 row 5, now implemented from telemetry instead of needing fill scraping); ticket-opened-and-aborted count exceeding session norm. **Tier B.**

**Line 3 — Reflect (the log, not live).** EOD: daemon aggregates → `capture_outcome` (+ tag `behavior`) → feeds `propose_skill`/narrative review. This is where the weekly "twenty entries show you your trigger pattern" promise (§1.6) actually gets kept — by data, not by memory. No live LLM involvement; it rides the existing self-learning layer. **Tier B.**

âš ï¸ **Honest failure modes of this plane, recorded now:** (1) the shout trains the user to watch the shout, and tuning thresholds becomes the new way of spending the day near the market — the milkman warning (§1) applies to the telemetry itself; (2) alert fatigue is the default outcome of a warn system that fires a lot — thresholds must default to *rare and loud*, not continuous commentary; (3) measurement changes behavior (good in intent, but means the baseline shifts once installed — compare against post-install baseline only).

### 13.2 Context plane — push (repo computes it, chart should show it)

**User philosophy, recorded 2026-08-29 and binding on this section:** anything expressible as Pine he will write as Pine and maintain as Pine. The CDP plane's job is **not to draw** — it is **to feed Pine the data Pine cannot fetch itself**, and only then to draw where drawing is the only carrier. "Pine gets fed, not fetched."

**Channels (the actual design space):**

| Ch | Channel | Mechanism | Tier | Notes |
|---|---|---|---|---|
| A | **Inputs-bridge** (primary) | MCP `indicator_set_inputs` (exists today) writes values into a custom Pine indicator's inputs (EM±, levels list as numeric/string inputs); Pine does all rendering, stays in layout, survives reloads | **A** | refresh = daemon/MCP sets inputs on a cadence; bounded by ~dozens of inputs per indicator — right shape for EM, flip, a few walls |
| B | **Synthetic-symbol feed** (the request.security unlock) | TradingView **custom symbols from CSV** (Premium-tier feature — verify plan) : repo writes a synthetic ticker's bars ("GEXQ_ES_250829" etc.) → Pine reads it with plain `request.security`, batching what would be hundreds of internal calls into a handful of synthetic ones | **B** | this is the honest answer to the 40-call limit: move the data into a symbol, don't multiply requests. Needs a one-time confirmation of the feature tier + file-drop automation (CDP can drive the import dialog) |
| C | **Drawing-bridge** (fallback) | daemon/MCP `draw_shape` / CDP injection draws levels the channels above can't carry | **B** | demoted per user preference — reserved for things no Pine input can hold (e.g., time-extended zones), or when Pine side is absent |
| D | **DOM overlay panel** (sidecar HUD) | injected positioned panel *next to* the chart (not on it) for data that is not chart-native at all: OI/GEX strike map, wargaming If-Then cards | **B/C** | user lets Pine draw chart things; a strike-map table is a panel, not a chart drawing — this is its home |

**Candidate use cases by channel (data is ours — Schwab API per OPTIONS_INVENTORY.md: auth, Greeks engine, level scorer; TOS RTD as the real-time feed):**

| # | Use case | Channel | Tier | Notes |
|---|---|---|---|---|
| 1 | **Expected moves auto-populated** into his Pine (EM± from Schwab/TOS) | A | **A** | "populate the Expected moves… into the indicators automatically" — verbatim ask; inputs carry upper/lower, Pine renders |
| 2 | **GEX levels** (flip / zero-gamma / largest walls / OPEX pins) into a Pine input block | A | **B** | same shape as #1; computed repo-side from Schwab chains today, TOS RTD for realtime |
| 3 | **OI/GEX strike map HUD** (net gamma by strike, call/put walls) as a sidecar table beside the chart | D | **B** | too rich for inputs, wrong shape for Pine — a panel it is; "OI map" is his verbatim ask |
| 4 | **request.security 40-limit relief** for *internal* series too: fold multi-timeframe/multi-symbol composites in the repo, deliver as one synthetic symbol | B | **B/C** | general escape from TV's per-indicator request budget; only needed if he actually bumps the ceiling — confirm before building |
| 5 | Session levels (DailyNY, KZ pivots, IPDA ranges, quarters, FVGs) — **live via Pine inputs or synthetic symbols only if he asks**; otherwise he keeps drawing them in Pine with his own scripts from the repo's numbers | A (inputs) | **A** | re-framed from "we draw it for you" to "we hand the data to your Pine" |

*(Deliberately not here: the EOD daily classification (R1/R2/DWP/DNP). It's an outcome/diagnostic, not something the live chart needs — decided 2026-08-29. Also demoted: proactive daemon drawing of session overlays (old Ch C row 1) — Pine-first per user, C draws only as fallback.)*

### 13.3 Context plane — pull (chart is a source; the repo wants what your hands did)

| # | Use case | Daemon or MCP | Tier | Notes |
|---|---|---|---|---|
| 5 | **Drawing harvest**: user's hand-drawn S/R boxes, flip zones, intent annotations read via existing pine drawing reads → outcomes ledger / profiler KB. Your intuition becomes labeled training data | MCP (exists today — `data_get_pine_boxes/labels`) | **A** | the pull that was historically hardest: capturing your eye, not just your fills |
| 6 | **Fill-moment journaling**: TV-side fills observed in DOM → screenshot + extract + session-tag → write to journal/outcomes. Today TV trades are the ones evaporating from journals | daemon (event-driven; MCP can one-shot-dump the panel) | **B/C** | compliance posture: journaling is write-only, never trades |
| 7 | **Option chain scrape**: TV renders chains it exposes no API for → feed Greeks engine/level scorer as second source beside TOS RTD | MCP (new tool, one-shot) | **B** | direction reversed 2026-08-29: primary OI/GEX source is **Schwab API** (§13.2); TV chain scrape is only the fallback when Schwab/TOS are both down |
| 8 | **Alert-fired events**: TV alert firing is DOM/network-observable → local event → ledger entry / narrative trigger / notify. Alerts become a bus instead of a sound | daemon | **B** | setting alerts is already in the MCP |

### 13.3a Signal overlay — "an AI living through TradingView" (brainstorm, captured verbatim-intent, NOT committed)

*User framing, 2026-08-29: "things like a price narrator, or telling me hey, something is setting up to be a trade, or giving me indications like look for longs now / look for shorts now, or we are in premium/discount, or check for IB strategy… more like an AI living through TradingView."* Recorded as **requirements + looks-possible**, no build decisions made. This is the narrative engine (`TRADER_NARRATIVE_PLAN.md`, NARRATIVE_ENGINE_CURRENT_DESIGN.md) and the ICT/KZ machinery getting a *mouth* on the chart.

**How it would actually work — the honest pipeline (all Tier B, one shared spine):**

```
repo state engines (already exist, run headless)
  narrative engine · ICT features (kz_pivots, imbalance, ipda) · profiler stats
  quarters theory · options levels · GEX (Schwab) · bias signals
        â”‚  (computed on cron / event — unchanged, no live CDP dependency)
        â–¼
signal bus â”€â”€ localhost JSON events: { token, kind, severity, text, ttl, anchors }
        â–¼
overlay daemon (the same daemon from §3, one more consumer)
  â”€ resolves token → position over price (CDP price→pixel conversion, or chart-screenhook via injected script)
        â–¼
   1 HUD band (discreet, one-line)      2 voice (price narrator)      3 Pine-driven marks (optional, via §13.2 Ch A)
```

**The candidate signals (requirement list, "looks possible" assessment each):**

| # | Signal (user words) | Source engine (exists today?) | Feasibility | The catch |
|---|---|---|---|---|
| 1 | **Price narrator** — quiet commentary of what price is doing | narrative engine intraday mode | **B** — everything needed exists headless; this is presentation only | the only *new* tech is cheap TTS; the hard part is **writing standards**: narrator says "rejection at PDH, respecting it" once, not every bar. Rate-limit to session-events, not ticks |
| 2 | **"Something is setting up"** — pre-trade awareness | ICT features pipeline (imbalance, KZ pivots, SMT in phase 2) + bias signals | **B** | this is a *probability* not an event — must state confidence, never certainty; see honesty rule below |
| 3 | **"Look for longs/shorts now"** — directional window nudge | `generate_bias_signals` (--eval-time machinery exists) | **B** | delivery timing matters more than content — right at window-open, not 20 min late; and **never** phrased as "enter now", always "conditions for longs are armed" |
| 4 | **Premium/discount calls** (quarters theory / IPDA ranges) | QUARTERS_THEORY doji/extremes + IPDA from ICT features | **B** | pure state-derivation, cheapest of the set; natural first candidate to pilot the spine |
| 5 | **"Check IB strategy"** — session-structure reminders | profiler combos (get_profiler_combinations — ALN/IB probabilities exist) | **B** | best shaped as a **prompt to check**, not a claim — "IB low held + Asia trending: recalls score X%" — machine hands the thought, human decides |
| 6 | Wargaming card surfacing at the right minute | pack_wargaming skill content | **C** | static cards are done; the *timing* engine (when which card applies) is un-built product logic |

**Shared spine requirement (this is the one thing to build; everything above rides it):** a `signal bus` daemon process that (a) subscribes to repo engines' outputs as local files/socket/queue — engines stay headless and unchanged, (b) normalizes to one event schema `{token, kind, severity, text, ttl}`, (c) presents through the three mouths (band / voice / Pine-inputs).token = which chart element it anchors to; ttl = events expire so stale guidance dies silently instead of lying around (the §5.2 lesson, again, for words).

**Honesty rules for this plane (binding, non-negotiable):**
1. **Indications, never instructions.** "Longs look armed" â‰  "go long." The plane delivers *awareness*; the decision, the click, and the risk stay human — this is also what keeps deny-only authority (§13.5) intact: a system that murmurs "premium" cannot be blamed for a trade; a system that says "click buy now" is an order system wearing a costume.
2. **Every signal names its engine and confidence.** "quarters: premium (static)" vs "narrative: 60% Asia continuation (p12)". Attribution is auditable; a random-feeling oracle gets muted within a week (§13.1 fatigue lesson).
3. **State changes only, by default.** The narrator speaks on *transitions* (entered discount, IB broken, sweep happened), not on a clock. Ticking narration is the alert-fatigue fate of §13.1 wearing a voice.
4. **The 14.1 ladder idea applies**: repeated ignored signals may *escalate to the behavioral plane* (log it as "advice taken / not taken" — that's outcome data), but may NEVER auto-execute anything.

*(Status: brainstorm only. Candidate pilot: #4 premium/discount via the spine + one HUD band — smallest scope, engines already exist, no TTS required. Decide after §13.1's telemetry is real.)*

### 13.3b Review modes — journaling without the paste (brainstorm, requirements captured, NOT committed)

*User framing, 2026-08-29: "monitor my journalling… instead of me pasting images, we can enter into a specific mode like EOD review, EOW review, next-week review, reviews of today's trades etc — where you read the data directly and then add it to the journalling."* Requirements + looks-possible.

**The requirement, restated:** today the journal entry is assembled by hand — you screenshot charts, paste, type what happened. Instead, entering a **review mode** should make an agent assemble the raw entry *itself* by reading the sources directly, so you only review, correct and add judgment. The system's job: **data assembly, not journaling** — the written reflection stays yours.

**Modes (requirement list):**

| Mode | When | Data reads (all exist or §13.3-adjacent) |
|---|---|---|
| **Trades-of-today** | any time intraday/on demand | §13.3 #6 fill events + §13.2 session levels (what was drawn/thought then) + §13.1 behavioral telemetry for the trade windows |
| **EOD review** | after close (15:00 CT session close, ADR-020 anyone?) | chart screenshots at key times (open/IB/noon/close — replay available for re-rendering specific moments), OHLCV summaries, profiler stats, classification (read, not drawn — §13.2 exclusion list), narrative close output, behavior day summary |
| **EOW review** | Friday / Saturday | week of EOD entries + weekly profiler + giveback/consistency stats + outcomes ledger week roll-up |
| **Next-week prep** | weekend | bias signals state, GEX/EM levels pre-computed (Schwab), wargaming scenario inputs for the coming week |

**How it works (the honest assembly):**
1. **Capture layer** — screenshots via existing MCP `capture_screenshot` (and `nt_trade_chart` on the NT8 side for fills); the *shot list* is the new bit: per mode, which chart, which symbol, which time anchors. Daemon can time-stamp-and-snap at the moments that matter during the day so EOD doesn't need replay reconstruction (that's §13.4's replay-bench synergy).
2. **Assembly layer** — an agent prompt per mode (docs-mode of agent-loop generalizes well here: it already reads a repo + graphs + writes structured markdown) with the mode's read-list; output is a **draft** into the journal target.
3. **Journal target (open, needs a decision):** not the CDP plane's job to pick — candidates already in the ecosystem: **Notion** (MCP exists this box), **NT8 `nt_trade_journal`** (CRUD + macro auto-tagging + TraderSync/TradesViz export already built), memory-store outcomes ledger. Likely: trades → trade_journal; day/week reflections → Notion draft page under review. **One decision needed from user (see below).**
4. **The monitor** (his word, "monitor my journalling"): a compliance check, §13.1 Line-1 style — "journaled today? streak N" — on the *absence* of an entry, not nagging about content. Amber only; content policing is explicitly out of scope (the journal is judgment, not homework).

**Feasibility:** Tier B overall; every capture primitive exists (screenshots, OHLCV, pine reads, exporters); the new build is the **shot-lists + mode prompts + wiring**, which is convention CRUD, not research. Highest-uncertainty item: EOD "shots at key times" if the chart wasn't on that symbol at that time (→ fallback: replay-mode re-render, Tier B, see §13.4 bench).

**Open decisions for this entry:** (a) journal target(s) — trade_journal vs Notion vs both; (b) do review modes run *inside* the agent session (opencode invoking MCP tools — cheapest, semi-manual: "run EOD review") or as scheduled daemon tasks producing drafts you read later; (c) weekly/next-week modes need weekend data policy (markets closed — replay vs static summaries).

### 13.3c Pointer protocol — live chart Q&A: test / validate / explain on annotation (brainstorm, requirements captured, NOT committed)

*User framing, 2026-08-29: "strategy testing/validating or explaining while I live on the charts and do annotations, or point to something that you can then take a look at?"*

**Core insight that makes this cheap: your drawings already ARE a query payload.** A hand-drawn box carries `{symbol, t1, p1, t2, p2, type, label-text}` — that's a complete structured question. The MCP reads them today (`data_get_pine_boxes/lines/labels`, Tier A). §13.3 #5 harvests them *passively*; this use case uses the same reads *deliberately* — **the same plumbing, two intents**: harvest = data for the ledger; pointer = a question to the agent. Disambiguation is a convention choice, not new tech: (a) an explicit "ask mode" gesture in the UI, (b) a label-text convention (`?` prefix, or a named study the annotations live under), or (c) implicit — user is in an agent session and says "look at the box I drew on NQ". Decide later; fine either way.

**Query → answer flows, each mapped to what already exists:**

| # | "Point at something" means | What the agent runs | Tier |
|---|---|---|---|
| 1 | **Explain this** (box circled around a move/zone) | OHLCV around the window + ICT detectors (ICT_SPEC_V1 runs headless) + what the engines see there (levels, bias state at the time) — an explanation *citing computed evidence* | **A/B** |
| 2 | **Is this level real/significant?** (trend line, horizontal) | distance-check against derived levels: PDH/PDL, KZ pivots, GEX walls (Schwab), quarters, session levels — "within 4 ticks of zero-gamma flip" beats "yeah looks important" | **A/B** |
| 3 | **Would the model have caught this?** (zone/pattern) | hindsight run of bias signals / profiler combos on that window; narrative engine asked "what did you say at 10:15?" | **B** |
| 4 | **Test this idea** (pattern + hypothesis text) | NT8 `nt_signal_backtest` / `nt_backtest` on the pattern rule; or TradingView strategy tester (MCP `data_get_strategy_results` + `data_get_trades` already exist) → agent explains metrics + weak spots | **A/B** |
| 5 | **Validate my trade** (circle the fill) | §13.3 #6 fill data + what conditions looked like pre-entry (bias, GEX, levels) | **B** |

**Answer routes (one of three, per context):** (a) **pinned inline note** — injected DOM element anchored at the annotation's chart position; shares the *price→pixel anchor* problem with §13.3a's spine (same infra, build once), (b) voice via the narrator mouth, (c) the agent session itself (chat answer, no on-chart artifact — cheapest, often enough).

**The catch to record before anyone falls in love:** the agent explaining what's on your chart is dangerously close to **post-hoc storytelling** — the confabulation risk. Binding discipline: an explanation must anchor to data reads (OHLCV, detector outputs, base rates from the profiler/quantile machinery) and tag any speculative part as narrative, not fact. The repo already owns this instinct in narrative-engine design (known issues section) — carried forward here. Latency expectation: this is async Q&A ("leave the question, read the answer"), not a conversation while bars tick — pointer questions queue; answers land when computed.

*(Status: brainstorm. Nothing to pilot until §13.3 #5's drawing read has been pointed at live annotations once — after that, flow #1 (explain) is the natural first query type.)*

### 13.4 Benches (proven or parked, not commitments)

- **Replay-mode review**: MCP replay tools exist (start/step/status/trade). A scripted "replay the day we just logged" (§13.1 Line-1 ledger ledger) is Tier A adjacent — build the journal first, this comes free after.
- **Away-mode 16:00**: *strip the ticket, watchlist hot-buttons and news feed out of the DOM*, leaving price only — the chart closes itself. Daemon-side. Parked as trigger #8 in §5.1 territory or a §7 rule — **strongest behavioral payoff on this page; the strongest constraint is the removed one** — but deliberately after the gate exists, not before. The §1 warning applies whole: don't let "away-mode settings" become the new tuning habit.
- **Perf mode**: `Network.setBlockedURLs` + CSS to kill chat/social panels — TV Desktop RAM problem solved as a side effect. Tier B, trivially optional.
- **Symbol-switch stampede → auto-lock** — same mechanism as §13.1's escalation ladder, different threshold. Listed under 14.1, listed here because it likely ships as a generic "any n-behavior rule can escalate to lock" hook.

### 13.5 Governance line for the whole plane (decided here, applies to everything above)

1. **The CDP plane never places orders. Deny-only authority, total.** Gate kills clicks; Context draws and reads; Behavioral measures and warns. If a future use case seems to need order submission, it goes through the NT8 bridge (which already has its own hardening/audit trail) or a broker API — never through the chart's DOM click path from daemon or MCP. (`replay_trade` is exempt: replay P&L touches no account; and after hours, replay+§13.1 telemetry is exactly how the simulation lab should work.)
2. **Every DOM-sourced capability gets the house treatment from day one**: one probe script, a date-stamped anchors.md entry, one `check_*.py` gate in the same commit — or the feature doesn't ship. A stale anchor must always be *visible* (STALE state), never silent — the §5.2 lesson generalizes to every scrape in this section.
3. **The chart stays a chart.** The screen is where the trading happens; the plane's UX budget is small (status line at most). Any overlay that turns into a dashboard drifts into the §1 "loop found a new costume" failure and gets cut in review.

---

## 14. References

- Source/inspiration: https://milkmantrades.com/buy-lock.html (fetched 2026-08-29). V1/v2 feature lists above are from that page; this doc is ours and the implementation, when it exists, will be ours. **The milkman zips were never downloaded or executed — everything in this plan describing his build comes from the write-up, and any build here is written from scratch.**
- Repo context: `docs/NT_RISK_GUARD_SPEC.md`, `docs/TRADE_COPIER_PRD.md`, `docs/HARMONISED_TRADING_ARCHITECTURE.md` (tvDownloadOHLC), ADR-020 (RTH liquidation), ADR-018 (visual constraint, N/A here but listed for completeness).
- Known trap quoted in §8: gate wired to nothing is invisible (see P2 family tracking in hardening plan).