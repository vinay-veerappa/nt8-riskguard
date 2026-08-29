# RISKGUARD_BROWSER_GATE_PLAN.md

**Status:** v0 — IDEA, nothing built. Talking doc.
**Created:** 2026-08-29. **Last updated:** 2026-08-29.
**Origin:** user saw https://milkmantrades.com/buy-lock.html — "I am sure we can convert our riskguard into a chrome extension as well to deal with my tradingview and tradovate systems."
**Decision already made:** when built, it lives in this repo at `browser/`. NOT a new repo, NOT a vendored submodule of the bridge.

---

## 0. What this is (one paragraph)

A Chrome MV3 extension that blocks **order entry** on TradingView web and Tradovate web when a lock is live. RiskGuard guards the NT8 broker connection: if an order is submitted from a browser, RiskGuard only sees it **after** the fill (react, flatten, lockout). The browser extension is the only cheap thing that can stop the click **before** submission on those surfaces. It is a pre-trade gate for surfaces the C# guard cannot reach. It does not replace RiskGuard; it closes a hole next to it.

**Framing that must survive every design review in this doc:** this is *friction*, not a vault. Cool-state you removing options from hot-state you. Any feature that pretends to be enforceable from inside the same browser is a lie; see §9.

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

## 3. Architecture (when built)

Mirror of the HARMONISED_TRADING_ARCHITECTURE 3-layer pattern, carried into the browser plane:

```
browser/
  daemon/                        # PRIMARY plane: TV Desktop via CDP (decided, §4a)
    gate_daemon.py               # Playwright connect_over_cdp(9222); inject + lock engine host
    inject/
      event_kill.js              # capture-phase blocker — injected on every new document
      dom_watch.js               # greying/toast/PnL scrape — the content-script role
    status/                      # localhost status page (badge/off-switch equivalent)
  extension/                     # MV3 plane for web surfaces — same rules schema as daemon
    manifest.json                # MV3, minimal permissions (see §7)
    src/core/                    # lock engine — vendor-neutral
      lock_engine.js             # state machine: no lock < soft lock < hard lock
      storage.js                 # chrome.storage.local, schema versioning
      event_kill.js              # capture-phase blocker (same code as daemon inject)
      alarms.js                  # expirations, schedule windows
      anchor_probe.js            # liveness monitoring (see §5.2)
    src/sites/tradingview/
      adapter.js                 # anchors, side detection, PnL scraper, submit intercept
      anchors.md                 # every data-name/class relied on + date last verified
    src/sites/tradovate/
      adapter.js                 # TBD — DOM discovery pass required (see §6)
      anchors.md
    src/ui/
      popup.html|js              # durations, rule list, status
      toast.css|js               # locked-state affordance
      badge.js                   # ON / STALE / OFF — STALE is the important one
  launcher/                      # TV Desktop wrapper: launches with CDP port, then arms daemon
  tests/
    fixtures/tradingview_ticket.html
    fixtures/tradovate_ticket.html
    *.test.js|py                 # Playwright asserts blocked/allowed per §8
```

**Design rules:**
- Core never imports from site adapters; adapters declare `{ id, matches, anchors: {...}, isBuyContext(), readPnl(), lock(target), unlock(target) }`.
- Never key on class hashes (they rotate). Anchor on stable attributes (`data-name`, `data-testid`, literal button text as last fallback), and record each anchor with the date it was last observed valid in `anchors.md`.
- Exits are never blocked, on any adapter, at any lock level. Entry blocked / management allowed / flatten allowed. This is ADR-020's spirit (16:00 liquidation must always remain possible).

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

⚠️ The copier does not help here: followers copy the leader (NT8, guarded). A browser-side order reaches only its own account. But if the locked browser belongs to a *copier leader*, blocking it protects every follower at once.

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
| `chrome.storage.local` | lock state lives in the daemon process instead |
| popup + badge | daemon serves a tiny local status page (localhost) or writes state the NT8 side displays |
| MutationObserver greying/toast | unchanged — it's all just injected JS |

- **Architecture for the Desktop plane:** a small local daemon (Python, Playwright `connect_over_cdp("http://127.0.0.1:9222")`) attaches to the TV process, injects the gate script into every target (main + iframes), and owns the lock engine. The *same* lock engine core can then back both planes: daemon injects into TV Desktop; the MV3 extension (if ever built) reads the same rules schema. One brain, two arms.
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
                      ┌──────────────┴──────────────┐
              tradingview-mcp                  gate daemon
        (stdio MCP, on-demand,             (always-on, event-driven,
         agent-facing request/response)     trader-facing enforcement)
```

**Division of labor — anything one-shot and request/response belongs in the MCP; anything persistent and event-driven belongs in the daemon:**

| Concern | Home | Notes |
|---|---|---|
| Read chart state/studies/prices | MCP (exists) | |
| Push computed context onto chart | MCP (draw_shape exists; add session-overlay tool) | §14.2 use case 5 |
| Read hand-drawn drawings as data | MCP (pine drawing reads exist) | §14.3 use case 5 |
| Alert *setting* | MCP (exists) | |
| Alert *firing* as events | daemon (needs event watching) | |
| One-shot scrapes (option chains, trade panel dump) | MCP (new tools) | fits request/response |
| Lock engine, event-kill, DOM-watch, urge telemetry, fill journaling, stale alarm | **daemon** | the whole §5 model |
| Launcher | MCP `tv_launch`, extended to arm the daemon after launch | |

**Code reuse:** the daemon imports the MCP's `src/connection.js` (`CDP_HOST`/`CDP_PORT` resolution, evaluate helpers, `/json/list` enumeration). Do not re-solve the known traps: Electron resolves to `::1` first while `--remote-debugging-port` binds IPv4 only (connection.js:7-8), and the MSIX path in `health.js`. One anchors file shared by both.

**Known issues in the MCP that this plan inherits (fix before building on it):**
1. `tests/launch.test.js` is **red on this box today** — the test expects `launch()` to refuse with `TradingView not found`, but TV is installed, so the spawn path executes and the "should not spawn" assertion fires. Environment-dependent test, trivially fixable (point TV search at a stub dir in tests), but the suite must be green before the daemon leans on it. House rule: never build on a repo whose suite you haven't run.
2. Missing CDP plumbing for the daemon needs: `Page.addScriptToEvaluateOnNewDocument` (injection on every new document — absent from connection.js) and `Target.setAutoAttach`-style multi-target handling (the order ticket renders in iframes; connection.js currently targets one page).
3. **Governance rule, decided here:** the MCP has `ui_click` and can therefore click the Buy button — but the daemon's capture-phase event-kill deadens **MCP-dispatched clicks too** (a synthetic click is still a DOM event). The gate survives the agent. Complementary rule: the MCP gains **no order-placement tools, ever** — same deny-only posture as §14.5's governance line.

---

## 5. Lock model

### 5.1 Trigger types (v1 = rows 1–4, everything else parking lot)

| # | Trigger | Source | Semantics |
|---|---|---|---|
| 1 | Manual lock | user picks duration | no unlock button until it expires; or manual-unlock requiring typed `UNLOCK` |
| 2 | Daily schedule | clock, Central, wraps midnight | entry locked inside window; set once |
| 3 | Daily loss hit | PnL scrape (TV / Tradovate) | hard lock for N hours; count N clearly on the popup |
| 4 | Daily gain hit | same | hard lock — protects giveback AND prop-firm best-day consistency share |
| 5 | Loss-streak counter (parking lot) | adapter detects N consecutive losing round-trips | cooldown, not hard lock, for v1+ |
| 6 | Cooldown after flatten (parking lot) | fill events via adapter | no re-entry for X minutes after going flat |
| 7 | RiskGuard sync (v2) | bridge → localhost | lock when FSM enters SoftStop/HardStop/Lockout; release with recovery |

### 5.2 The two fixes milkman didn't build (our v1 differentiators)

1. **Anchor liveness probe.** Every 60 s the adapter asserts its anchors still resolve. Probe result → badge + populator of `last_verified` per site in `anchors.md`. A TV build that renames `side-control-buy` turns into a visible **STALE** badge within a minute, not a lock that never fires. (Their failure mode: "no reading means no trigger", silently.)
2. **Stale-source alarm.** PnL scraping needs an open tab. If a lock rule depends on PnL and no PnL reading for > 2 min while any position could exist → badge `STALE`, toast, (optional v1.5) a mechanical bell via the existing NT8 side. Behavior choice on record: **fail-closed** (PnL unknown ⇒ treat as locked for the remainder of the day window) is the aggressive default; make it a setting, state it on the popup.

### 5.3 Lock semantics, borrowed and hardened

- **Hard lock:** layers 3/4. During a hard lock: trigger list, limits, and schedule are **frozen** (v2 parity).
- **Unlock paths:** timer expiry (never before the stated time — "make unlocking slow by design, so the unlock lands tomorrow when you no longer want it"); typed-`UNLOCK` for the manual-until-can't variant; optionally unlock word decided at lock time (random string shown frozen on screen at the time of locking, not pickable at unlock time).
- **One-sentence check (behavioral):** on any manual-unlock attempt, the popup requires one sentence describing the setup before the input accepts typing. If you can't type the sentence, the urge is the author. (Maps to §1.5.)
- **Prediction note (optional v1.5, unique to our stack):** before a scheduled-end unlock, optionally demand/offer a note ("next session I expect …") posted to `.agent` outcomes ledger via `capture_outcome` — scoreable later, per §1.1.

### 5.4 Never-lock list

Sell side. Order modify. Cancel. Close/flatten. Chart interaction generally (only entry-side controls that create or add exposure are in scope). ATM/bracket escalation of an existing position. A lock that traps you in a losing position is a different defect class; exits always win.

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

- **Fixture pages:** static HTML copies of the TV order ticket and Tradovate ticket (trimmed, but carrying the real anchors + a stub account header). These live in `tests/fixtures/` and are the only DOM the tests assume.
- **Playwright (headless, loads unpacked):**
  1. lock manual 1 min → click Buy absent `side-control-buy`-equivalent → no submit/entry event; sell still works.
  2. schedule lock (fake clock) → same.
  3. PnL trip at loss and at gain → lock N hours; settings frozen while held.
  4. anchor mutation (fixture renames attribute) → badge STALE within 60 s + toast.
  5. PnL tab closed → STALE within 2 min (with fail-closed setting on).
- **CI:** extension test battery wired into the existing gate scripts pattern (`check_*.py` reached via the guard's CI; if we keep JS, `node --test` where Playwright can't run). *(Recorded because a gate on disk wired to nothing is the known trap — every new defense in this repo gets a `check_*.py` in the same commit as the defense.)*
- Anchors.md: file date must be touched on every deployment of TV in use; this doc's §2 anchors were valid as of the milkman page fetch (2026-08-29), **not** verified against today's TradingView build — first code task is probing each anchor live and dating it.

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

- **Bridge sync (the v2 payoff):** extension reads lock state from the McpBridge over localhost (auth TBD — token or local-only loopback). Lock state becomes one artifact shared by NT8 guard + browser gate. Same pin-on-tag discipline as bridge ↔ addon: the extension calls a *versioned* endpoint, not a scraper of the addon's UI; break on contract, fail to SAFE (locked or STALE), never to unlocked.
- **Prop-firm rule presets:** daily loss/pnl numbers should default to the user's actual challenge rules (drawdown mode, daily allowance). We already have encoded, firm-official rule data via the prop-firm directory/simulator tools — a preset dropdown ("Apex 50K: DDB trailing-realized-EOD $2,250 ⇒ gain/loss trip at X") beats free-floating dollar guesses. The intra-day-trailing rule (the most-miscalculated one in the industry) is exactly the case where a hand-typed browser limit lies to you.
- **Consistency link:** dailyGain lock interacts with prop-firm best-day consistency gates — one outsized day effectively raises the remaining target (see prop-firm engine notes). Locking a green morning is this rule's browser-side twin.
- **Outcomes ledger / trader narrative:** unlock-time prediction notes and close-of-day "flat is a position" summaries can flow into `.agent` outcomes (`capture_outcome`) without any network from the extension — export file → script, or manual paste. Keep the extension itself network-zero; the post-processing is ours.

---

## 11. Open questions (bring answers, then this doc graduates to a build plan)

1. Which surface do you actually trade from most — TradingView charts with an integrated broker, Tradovate's own web portal, or both? (Decides adapter order and which PnL scrape matters first.)
2. Live accounts or sim/aperture for v1? (Changes how scary fail-closed needs to be.)
3. Trigger set for v1: rows 1–4 above? Is loss-streak in or out?
4. Unlock discipline: timer-only, or timer + frozen + one-sentence check + (optional) prediction note — how much friction do you actually want at 11:40 in the morning?
5. RiskGuard sync: for v1 leave standalone with named stale-state visibility, and add bridge sync as v2? (The one-source-of-truth rule in §4 then strictly holds.)
6. Do we want the badge/office behavior mirrored into NT8 (RiskGuard shows "browser gate STALE/armed" in its own UI) once bridge sync exists?
7. **TV Desktop first?** §4a came from a user statement that Desktop (not web) is the daily surface. Confirm, and if so v1 scope = daemon + launcher only, extension dropped until a web browsing need appears.

---

## 12. Parking lot

- Multi-account awareness: per-rule account identity (if the same browser hosts two portals).
- "Urge log" in-extension (time-stamped entries, re-exported) — timed urge waves, per §1.6.
- Peak-equity giveback trigger (browser-side twin of `nt_prop_limits` givebackCapPct).
- News-window lock (blackout windows like PropFirmProtectionSuite's news shield, browser side).
- Keep controls in this repo's `browser/` consistent with VISUAL_SYSTEM palette only if we ever surface a chart-side overlay; the extension has no chart UI otherwise.

---

## 14. Control-plane use-case catalog (the CDP link buys more than a lock)

The gate daemon is the first subscriber of a general capability: a **persistent, bidirectional channel between this repo's computed context and the live TV Desktop DOM** (chart pushes: injected drawings/HUD; pulls: DOM scrapes; behavior: deny + nudge). The use cases below split by whether they ride the **daemon** (always-on, event-driven) or the **MCP** (on-demand, agent-invoked — see §4b). Feasibility tier: **A** = plumbing exists today, **B** = new build but known technique, **C** = speculative/fragile.

### 14.1 Behavioral plane (the user's stated use case, 2026-08-29)

*"Logging my behaviour while trading, and somehow shouting at me if I am not doing things right and asking me to back off."*

This is the same product idea as the gate, one level up: **the gate is the mute button; this is the conscience.** Both ride the same daemon and the same DOM-watch injection. Split into three escalating lines of defense — **measure → warn → act** — because shouting without a log is nagging, and nagging gets ignored within a week:

**Line 1 — Measure (telemetry, always-on).** The DOM already exhibits every behavior worth scoring; the daemon timestamps it:

| Signal (all DOM-observable) | Proxy for |
|---|---|
| Order ticket opened / closed | itch to act |
| Buy↔Sell toggle flips on one ticket | indecision — the urge dressed as analysis (§1.5) |
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

⚠️ **Honest failure modes of this plane, recorded now:** (1) the shout trains the user to watch the shout, and tuning thresholds becomes the new way of spending the day near the market — the milkman warning (§1) applies to the telemetry itself; (2) alert fatigue is the default outcome of a warn system that fires a lot — thresholds must default to *rare and loud*, not continuous commentary; (3) measurement changes behavior (good in intent, but means the baseline shifts once installed — compare against post-install baseline only).

### 14.2 Context plane — push (repo computes it, chart should show it)

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

### 14.3 Context plane — pull (chart is a source; the repo wants what your hands did)

| # | Use case | Daemon or MCP | Tier | Notes |
|---|---|---|---|---|
| 5 | **Drawing harvest**: user's hand-drawn S/R boxes, flip zones, intent annotations read via existing pine drawing reads → outcomes ledger / profiler KB. Your intuition becomes labeled training data | MCP (exists today — `data_get_pine_boxes/labels`) | **A** | the pull that was historically hardest: capturing your eye, not just your fills |
| 6 | **Fill-moment journaling**: TV-side fills observed in DOM → screenshot + extract + session-tag → write to journal/outcomes. Today TV trades are the ones evaporating from journals | daemon (event-driven; MCP can one-shot-dump the panel) | **B/C** | compliance posture: journaling is write-only, never trades |
| 7 | **Option chain scrape**: TV renders chains it exposes no API for → feed Greeks engine/level scorer as second source beside TOS RTD | MCP (new tool, one-shot) | **B** | direction reversed 2026-08-29: primary OI/GEX source is **Schwab API** (§14.2); TV chain scrape is only the fallback when Schwab/TOS are both down |
| 8 | **Alert-fired events**: TV alert firing is DOM/network-observable → local event → ledger entry / narrative trigger / notify. Alerts become a bus instead of a sound | daemon | **B** | setting alerts is already in the MCP |

### 14.3a Signal overlay — "an AI living through TradingView" (brainstorm, captured verbatim-intent, NOT committed)

*User framing, 2026-08-29: "things like a price narrator, or telling me hey, something is setting up to be a trade, or giving me indications like look for longs now / look for shorts now, or we are in premium/discount, or check for IB strategy… more like an AI living through TradingView."* Recorded as **requirements + looks-possible**, no build decisions made. This is the narrative engine (`TRADER_NARRATIVE_PLAN.md`, NARRATIVE_ENGINE_CURRENT_DESIGN.md) and the ICT/KZ machinery getting a *mouth* on the chart.

**How it would actually work — the honest pipeline (all Tier B, one shared spine):**

```
repo state engines (already exist, run headless)
  narrative engine · ICT features (kz_pivots, imbalance, ipda) · profiler stats
  quarters theory · options levels · GEX (Schwab) · bias signals
        │  (computed on cron / event — unchanged, no live CDP dependency)
        ▼
signal bus ── localhost JSON events: { token, kind, severity, text, ttl, anchors }
        ▼
overlay daemon (the same daemon from §3, one more consumer)
  ─ resolves token → position over price (CDP price→pixel conversion, or chart-screenhook via injected script)
        ▼
   1 HUD band (discreet, one-line)      2 voice (price narrator)      3 Pine-driven marks (optional, via §14.2 Ch A)
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
1. **Indications, never instructions.** "Longs look armed" ≠ "go long." The plane delivers *awareness*; the decision, the click, and the risk stay human — this is also what keeps deny-only authority (§14.5) intact: a system that murmurs "premium" cannot be blamed for a trade; a system that says "click buy now" is an order system wearing a costume.
2. **Every signal names its engine and confidence.** "quarters: premium (static)" vs "narrative: 60% Asia continuation (p12)". Attribution is auditable; a random-feeling oracle gets muted within a week (§14.1 fatigue lesson).
3. **State changes only, by default.** The narrator speaks on *transitions* (entered discount, IB broken, sweep happened), not on a clock. Ticking narration is the alert-fatigue fate of §14.1 wearing a voice.
4. **The 14.1 ladder idea applies**: repeated ignored signals may *escalate to the behavioral plane* (log it as "advice taken / not taken" — that's outcome data), but may NEVER auto-execute anything.

*(Status: brainstorm only. Candidate pilot: #4 premium/discount via the spine + one HUD band — smallest scope, engines already exist, no TTS required. Decide after §14.1's telemetry is real.)*

### 14.3b Review modes — journaling without the paste (brainstorm, requirements captured, NOT committed)

*User framing, 2026-08-29: "monitor my journalling… instead of me pasting images, we can enter into a specific mode like EOD review, EOW review, next-week review, reviews of today's trades etc — where you read the data directly and then add it to the journalling."* Requirements + looks-possible.

**The requirement, restated:** today the journal entry is assembled by hand — you screenshot charts, paste, type what happened. Instead, entering a **review mode** should make an agent assemble the raw entry *itself* by reading the sources directly, so you only review, correct and add judgment. The system's job: **data assembly, not journaling** — the written reflection stays yours.

**Modes (requirement list):**

| Mode | When | Data reads (all exist or §14.3-adjacent) |
|---|---|---|
| **Trades-of-today** | any time intraday/on demand | §14.3 #6 fill events + §14.2 session levels (what was drawn/thought then) + §14.1 behavioral telemetry for the trade windows |
| **EOD review** | after close (15:00 CT session close, ADR-020 anyone?) | chart screenshots at key times (open/IB/noon/close — replay available for re-rendering specific moments), OHLCV summaries, profiler stats, classification (read, not drawn — §14.2 exclusion list), narrative close output, behavior day summary |
| **EOW review** | Friday / Saturday | week of EOD entries + weekly profiler + giveback/consistency stats + outcomes ledger week roll-up |
| **Next-week prep** | weekend | bias signals state, GEX/EM levels pre-computed (Schwab), wargaming scenario inputs for the coming week |

**How it works (the honest assembly):**
1. **Capture layer** — screenshots via existing MCP `capture_screenshot` (and `nt_trade_chart` on the NT8 side for fills); the *shot list* is the new bit: per mode, which chart, which symbol, which time anchors. Daemon can time-stamp-and-snap at the moments that matter during the day so EOD doesn't need replay reconstruction (that's §14.4's replay-bench synergy).
2. **Assembly layer** — an agent prompt per mode (docs-mode of agent-loop generalizes well here: it already reads a repo + graphs + writes structured markdown) with the mode's read-list; output is a **draft** into the journal target.
3. **Journal target (open, needs a decision):** not the CDP plane's job to pick — candidates already in the ecosystem: **Notion** (MCP exists this box), **NT8 `nt_trade_journal`** (CRUD + macro auto-tagging + TraderSync/TradesViz export already built), memory-store outcomes ledger. Likely: trades → trade_journal; day/week reflections → Notion draft page under review. **One decision needed from user (see below).**
4. **The monitor** (his word, "monitor my journalling"): a compliance check, §14.1 Line-1 style — "journaled today? streak N" — on the *absence* of an entry, not nagging about content. Amber only; content policing is explicitly out of scope (the journal is judgment, not homework).

**Feasibility:** Tier B overall; every capture primitive exists (screenshots, OHLCV, pine reads, exporters); the new build is the **shot-lists + mode prompts + wiring**, which is convention CRUD, not research. Highest-uncertainty item: EOD "shots at key times" if the chart wasn't on that symbol at that time (→ fallback: replay-mode re-render, Tier B, see §14.4 bench).

**Open decisions for this entry:** (a) journal target(s) — trade_journal vs Notion vs both; (b) do review modes run *inside* the agent session (opencode invoking MCP tools — cheapest, semi-manual: "run EOD review") or as scheduled daemon tasks producing drafts you read later; (c) weekly/next-week modes need weekend data policy (markets closed — replay vs static summaries).

### 14.3c Pointer protocol — live chart Q&A: test / validate / explain on annotation (brainstorm, requirements captured, NOT committed)

*User framing, 2026-08-29: "strategy testing/validating or explaining while I live on the charts and do annotations, or point to something that you can then take a look at?"*

**Core insight that makes this cheap: your drawings already ARE a query payload.** A hand-drawn box carries `{symbol, t1, p1, t2, p2, type, label-text}` — that's a complete structured question. The MCP reads them today (`data_get_pine_boxes/lines/labels`, Tier A). §14.3 #5 harvests them *passively*; this use case uses the same reads *deliberately* — **the same plumbing, two intents**: harvest = data for the ledger; pointer = a question to the agent. Disambiguation is a convention choice, not new tech: (a) an explicit "ask mode" gesture in the UI, (b) a label-text convention (`?` prefix, or a named study the annotations live under), or (c) implicit — user is in an agent session and says "look at the box I drew on NQ". Decide later; fine either way.

**Query → answer flows, each mapped to what already exists:**

| # | "Point at something" means | What the agent runs | Tier |
|---|---|---|---|
| 1 | **Explain this** (box circled around a move/zone) | OHLCV around the window + ICT detectors (ICT_SPEC_V1 runs headless) + what the engines see there (levels, bias state at the time) — an explanation *citing computed evidence* | **A/B** |
| 2 | **Is this level real/significant?** (trend line, horizontal) | distance-check against derived levels: PDH/PDL, KZ pivots, GEX walls (Schwab), quarters, session levels — "within 4 ticks of zero-gamma flip" beats "yeah looks important" | **A/B** |
| 3 | **Would the model have caught this?** (zone/pattern) | hindsight run of bias signals / profiler combos on that window; narrative engine asked "what did you say at 10:15?" | **B** |
| 4 | **Test this idea** (pattern + hypothesis text) | NT8 `nt_signal_backtest` / `nt_backtest` on the pattern rule; or TradingView strategy tester (MCP `data_get_strategy_results` + `data_get_trades` already exist) → agent explains metrics + weak spots | **A/B** |
| 5 | **Validate my trade** (circle the fill) | §14.3 #6 fill data + what conditions looked like pre-entry (bias, GEX, levels) | **B** |

**Answer routes (one of three, per context):** (a) **pinned inline note** — injected DOM element anchored at the annotation's chart position; shares the *price→pixel anchor* problem with §14.3a's spine (same infra, build once), (b) voice via the narrator mouth, (c) the agent session itself (chat answer, no on-chart artifact — cheapest, often enough).

**The catch to record before anyone falls in love:** the agent explaining what's on your chart is dangerously close to **post-hoc storytelling** — the confabulation risk. Binding discipline: an explanation must anchor to data reads (OHLCV, detector outputs, base rates from the profiler/quantile machinery) and tag any speculative part as narrative, not fact. The repo already owns this instinct in narrative-engine design (known issues section) — carried forward here. Latency expectation: this is async Q&A ("leave the question, read the answer"), not a conversation while bars tick — pointer questions queue; answers land when computed.

*(Status: brainstorm. Nothing to pilot until §14.3 #5's drawing read has been pointed at live annotations once — after that, flow #1 (explain) is the natural first query type.)*

### 14.4 Benches (proven or parked, not commitments)

- **Replay-mode review**: MCP replay tools exist (start/step/status/trade). A scripted "replay the day we just logged" (§3.5 of the §14.1 ledger) is Tier A adjacent — build the journal first, this comes free after.
- **Away-mode 16:00**: *strip the ticket, watchlist hot-buttons and news feed out of the DOM*, leaving price only — the chart closes itself. Daemon-side. Parked as trigger #8 in §5.1 territory or a §7 rule — **strongest behavioral payoff on this page; the strongest constraint is the removed one** — but deliberately after the gate exists, not before. The §1 warning applies whole: don't let "away-mode settings" become the new tuning habit.
- **Perf mode**: `Network.setBlockedURLs` + CSS to kill chat/social panels — TV Desktop RAM problem solved as a side effect. Tier B, trivially optional.
- **Symbol-switch stampede → auto-lock** — same mechanism as §14.1's escalation ladder, different threshold. Listed under 14.1, listed here because it likely ships as a generic "any n-behavior rule can escalate to lock" hook.

### 14.5 Governance line for the whole plane (decided here, applies to everything above)

1. **The CDP plane never places orders. Deny-only authority, total.** Gate kills clicks; Context draws and reads; Behavioral measures and warns. If a future use case seems to need order submission, it goes through the NT8 bridge (which already has its own hardening/audit trail) or a broker API — never through the chart's DOM click path from daemon or MCP. (`replay_trade` is exempt: replay P&L touches no account; and after hours, replay+§14.1 telemetry is exactly how the simulation lab should work.)
2. **Every DOM-sourced capability gets the house treatment from day one**: one probe script, a date-stamped anchors.md entry, one `check_*.py` gate in the same commit — or the feature doesn't ship. A stale anchor must always be *visible* (STALE state), never silent — the §5.2 lesson generalizes to every scrape in this section.
3. **The chart stays a chart.** The screen is where the trading happens; the plane's UX budget is small (status line at most). Any overlay that turns into a dashboard drifts into the §1 "loop found a new costume" failure and gets cut in review.

---

## 15. References

- Source/inspiration: https://milkmantrades.com/buy-lock.html (fetched 2026-08-29). V1/v2 feature lists above are from that page; this doc is ours and the implementation, when it exists, will be ours. **The milkman zips were never downloaded or executed — everything in this plan describing his build comes from the write-up, and any build here is written from scratch.**
- Repo context: `docs/NT_RISK_GUARD_SPEC.md`, `docs/TRADE_COPIER_PRD.md`, `docs/HARMONISED_TRADING_ARCHITECTURE.md` (tvDownloadOHLC), ADR-020 (RTH liquidation), ADR-018 (visual constraint, N/A here but listed for completeness).
- Known trap quoted in §8: gate wired to nothing is invisible (see P2 family tracking in hardening plan).