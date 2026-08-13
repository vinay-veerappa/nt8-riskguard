# RiskGuard + TradeCopier — UI Redesign Design

**Status:** Design, agreed with the operator 2026-08-13. Not yet implemented.
**Supersedes:** the handover's **§5.5 row "Where the redesigned UI lives"**, which decided *"Rewrite
`TradeCopierWindow.cs` properly, in NT8. Not the web app."* That decision is **reversed here**, on
evidence gathered after it was made (§7 below). The rest of §5.5 stands.
**Related:** handover §5.2 (`P?-64`/`P?-65`), §5.3 (UI redesign entry), §5.6 item 4, §5.17 (feature
audit), §5.18 (`F-n` backlog).

---

## 1. What this UI is for

The operator stated two goals, and they are the whole scope:

1. **Configure the system** — both RiskGuard and the copier.
2. **Verify that groups/relationships are doing exactly what they were configured to do.**

With three constraints:

* **No complicated graphs, no distracting information.**
* **No multiple clicks** to reach something needed routinely.
* Ideas that turn into new features go to the backlog; the layout **holds a marked slot** for them
  rather than building them now.

Goal 2 is not "show me numbers." It is **"prove the system is doing what I configured."** That is a
comparison, not a display, and it drives everything below.

---

## 2. The organizing idea — conformance, not monitoring

Every screen answers one question in one shape:

> **what I configured** vs **what is actually happening** vs **verdict**

This works here because both engines are deterministic against config. For a copier relationship the
expected follower position is a pure function of the leader's position, the sizing rule and the
symbol map — so agreement is **computable**, not eyeballed. A verdict word replaces a chart.

### 2.1 The three-state vocabulary

The most valuable thing this UI can carry. Every rule, on every account, is in exactly one state:

| State | Meaning |
|---|---|
| **CONFIGURED** | it is in the file |
| **EVALUATED** | code actually reads it |
| **ENFORCING** | it can act — armed, and in an acting mode |

**This is not theoretical. Four shipped defects are the same state, and a UI carrying this vocabulary
would have shown each of them on sight:**

| Defect | State | What the operator's config says |
|---|---|---|
| **`P1-77`** (open) | CONFIGURED, not EVALUATED | the consistency / daily-profit cap is enabled by default and **evaluated nowhere** |
| **`P2-25`** (open) | CONFIGURED, not EVALUATED | `EnableNewsShield` **defaults to `true`**; `LocalNewsEventsFilePath` is parsed, persisted and never read, so `IsInNewsWindow` always returns `false` and the `NEWS_SHIELD_LOCKOUT` branch (`RiskGuardAddOn.cs:1541`) is unreachable |
| **Firm-mirror rules** | CONFIGURED, not EVALUATED | loaded but **unmapped**, so none can fire (handover §0) |
| **`P1-75`** (closed) | ENFORCING → not ENFORCING, silently | **reading** the prop-firm rules **disarmed** them |
| **shadow mode** | EVALUATED, not ENFORCING | correct and deliberate — but must be unmistakable |
| **`P3-34`** (open) | the copier is ENFORCING **regardless of guard mode** | a single "armed" indicator would be a lie |

**Design rule: `CONFIGURED and not EVALUATED` renders red, everywhere, always.** It is the most
dangerous state this system can be in, because the config file reads as protection.

⚠️ **A FOURTH state was found on 2026-08-13 and it is worse, because every static check passes:
`INERT` — the rule executes and its evidence set is empty.** The news shield (`P2-25`) is
configured `true` by default, genuinely tested at `RiskGuardAddOn.cs:1541`, and genuinely calls a
real `IsInNewsWindow` — which iterates a list **nothing outside a test ever appends to**, because
`LocalNewsEventsFilePath` is parsed and then read by no loader. It always returns `false`. See
§6a: this is why the rule inventory belongs in the runtime snapshot and not in a linter.

---

## 3. The three signals

Per row, all text, no charts:

| Signal | Example | Answers |
|---|---|---|
| **Presence** | `LONG 2 MNQ · +$45.00` | is a trade on right now |
| **Agreement** | `expected 2 ✔` / `expected 2, actual 1 ✖` | did it copy per config |
| **Liveness** | `4s ago` | is the engine processing, or silently stalled |

**Liveness is not optional.** Without it, a stalled copier and an idle copier are visually identical.

### 3.1 Rules for the live P&L

* **Current only.** No cumulative, no history, no sparkline. P&L is *context for the verdict*, not a
  thing to watch. It answers "a trade is on," nothing more.
* **Flat is a valid MATCH.** Leader flat + follower flat = `✔ IDLE`, not a blank row.
* **The one row that must scream: leader flat, follower not.** An orphan position on a funded
  account. `CopierReconciler.cs` (608 lines) handles it and has **zero UI** today — that is `F-12`.
* **Session-scoped metrics render `—`, never `0.00`.** Latency and slippage reset on recompile.
  That confusion cost two sessions as `P?-66`. Measured reality is **142.86 ms** entry /
  **314.21 ms** exit — wall-clock between two NT8 callbacks. Milliseconds, not microseconds.

Data is available in-process (`Account.Get(AccountItem.UnrealizedProfitLoss)`,
`Position.MarketPosition`/`Quantity`); over HTTP it needs one snapshot endpoint.

---

## 4. Layout — one window, two panes, zero nav tabs

```
┌────────────────────────────────┬──────────────────────────┐
│ FLEET (always visible)         │ INSPECTOR (selection)    │
│                                │                          │
│ ▾ Group A · leader NT_9451     │  [copier] [risk] [rare]  │
│    ├ follower_1  1.0x  ✔MATCH  │                          │
│    ├ follower_2  1.0x  ⚠SHADOW │  full config for the     │
│    └ follower_3  0.5x  ✖DIVERG │  selected entity,        │
│ ▾ Unlinked accounts            │  round-tripped whole     │
│    └ Sim101      —     ✔ARMED  │                          │
├────────────────────────────────┴──────────────────────────┤
│ EVENTS — filtered to selection                            │
└───────────────────────────────────────────────────────────┘
```

Four decisions inside that:

1. **One tree of accounts, grouped by copy group; accounts in no group under "Unlinked."**
   RiskGuard and the copier stop being two systems — they become **two sections of the inspector for
   the same account**. This is what answers "which limit applies here" without building a rule engine.
2. **Groups are the only grouping.** `P1-76` made a follower belong to a direct relationship **or** a
   group, never both. A 1:1 pair is a group of one. The current two tabs ("Direct 1:1 Pairs",
   "Copier Groups (1:N)") invite the exact conflict the engine now rejects.
3. **Frequent actions are inline on the row, never in the inspector** — arm/disarm, enable/disable,
   ratio. That is the no-multiple-clicks rule. The inspector holds set-rarely config: symbol
   mappings, per-ticker matrix, slippage thresholds, firm profile.
4. **The only tabs in the entire app are inside the inspector.** Selecting nothing shows the system
   row (feed / guard / copier) — which is where `P3-34`'s two-or-three-indicator problem lives.

### 4.1 Group row

Reads as one line: `Group A · leader LONG 1 NQ +$210 · 6 followers · 6 MATCH`

### 4.2 What is deliberately NOT here

Killed by the operator's constraints, recorded so nobody re-adds them: performance graphs, equity
curves, journaling and post-trade analytics, prop-firm purchase/payout trackers, drag-to-reorder,
sparklines, "safety %" progress bars, and top-level navigation tabs.

---

## 5. Architecture — the same under any host

**The pattern under every defect in this area is identical: a surface builds its own partial copy of
a domain object and writes it.** Six remembered subsets found so far — `P?-65` (two, at
`TradeCopierWindow.cs:997` and `:1055`), slice 3b's two in the bridge, and `P1-72`…`P1-75`. The
redesign must make that structurally impossible, not fix the seventh instance.

> ### The one rule
> **The UI renders and dispatches. It never constructs a domain object, and it never names a file path.**

| Side | Mechanism | Why |
|---|---|---|
| **Read** | engines expose immutable snapshot DTOs (`CopierSnapshot`, `GuardSnapshot`) built **in core** | testable in `RiskGuardTests.csproj`; the UI binds and cannot invent state |
| **Write** | UI emits a `JObject` → `ApplyRelationshipRequest` (`TradeCopierEngine.cs:1251`) / `ApplyGroupRequest` (`:1182`) / a new `ApplyGuardConfigRequest` | **WPF, MCP and HTTP then share one write path.** The hardening plan already states this as "three surfaces, one rule" (`RISKGUARD_COPIER_HARDENING_PLAN.md:1395`); nothing enforces it yet |
| **Paths** | `CopierConfigFile` moves from `private static` in `McpBridgeAddOn.cs:3765` (**the bridge repo**) to a public constant on `TradeCopierEngine` in core; the bridge delegates | closes `P?-64`. Note this is a **cross-repo** move: core cannot reference the bridge |

⚠️ **The UI must NOT call `LoadFromDisk`.** The obvious reading of `P?-64` is "the window never
loads, so make it load." That recreates `P1-69`: the bridge's `get` action called `LoadFromDisk` and
**threw away the in-memory latency/slippage measurements it was being asked to report**. The engine
is a singleton already loaded at startup (`McpBridgeAddOn.cs:245`). The UI renders **in-memory engine
state** and only ever *writes*.

**This layer is host-agnostic.** It is identical whether the UI is WPF or a browser, it is all core
C#, and it is all inside the test project. It is the first landing and it can start immediately.

---

## 6. Read-model contents

What the snapshot must carry, derived from §2 and §3:

**Per relationship / follower**
`leaderAccount`, `followerAccount`, `groupName|null`, `sizingMode`, effective ratio,
`isEnabled`, `armedForLive`, `isQuarantined` + `quarantineReason`, `stealthMode`,
expected position (side, qty), **actual** position (side, qty), open P&L, latency + slippage with a
`measured: bool` (never a bare `0`), last-event timestamp, **verdict**.

**Per account (RiskGuard side)**
every rule that applies, each with `{ name, source, scope, state, currentValue, limit }` where
`source` ∈ config / firm profile / default fallback, `scope` ∈ per-order / per-position /
per-account / aggregate, and `state` is the §2.1 three-state. This is what makes §5.17's complaint
answerable: one concept — a contract cap — is spread across `InstrumentLimits`,
`InstrumentProfiles`, `DefaultMaxContracts`, `Sizing.MaxContractsPerAccount` and
`Sizing.MaxContractsAggregate`, and **no UI can say which one bit until they are named as one story.**

**Per account (gatekeeper side)** — see §8.

**System**
feed connected, guard mode + armed + guarding, copier armed, bridge version, config file mtime.

---

## 6a. The rule inventory — and the fourth state the survey found

**Added 2026-08-13, after surveying every config field against the code that reads it.** §6 asks
the guard side of the snapshot to carry, per account, every rule with
`{ name, source, scope, state, currentValue, limit }`. Building that survey first changed the
design, so the reasoning is recorded here rather than discovered again.

### A grep for "is this field read?" is NOT an evaluation check

Every leaf field of `RiskConfig` and its nested types was counted against every use in `addons/`.
It found exactly the two fields `P2-78` already records (`PerInstrumentRiskConfig.IsBlocked` and
`.StopOffsetTicks`, zero references each) and **nothing else** — which looks reassuring and is not,
because **the two worst rules in the system both score as READ**:

| Rule | Grep says | Truth |
|---|---|---|
| `EnableConsistencyCap` / `MaxDailyProfitPctOfTarget` (`P1-77`) | read | **declaration + the JSON parser, and nothing else.** No evaluator exists. Defaults to `true` |
| `EnableNewsShield` (`P2-25`) | read | read at `RiskGuardAddOn.cs:1541`, inside a real enforcement path, calling a real method. **And it can never fire** |

The news shield is the one that matters, because it defeats the obvious audit:

* `EnableNewsShield` defaults to `true`.
* `RiskGuardAddOn.cs:1541` genuinely tests it and genuinely calls `IsInNewsWindow`.
* `IsInNewsWindow` genuinely iterates `_newsEvents` and genuinely returns `true` for a high-impact
  event inside the buffer.
* **`_newsEvents` is only ever appended to by `AddTestNewsEvent`.** `LocalNewsEventsFilePath` is
  declared and parsed out of the config file — and read by nothing. No loader exists.

So in production the list is **always empty**, `IsInNewsWindow` **always returns `false`**, and the
`NEWS_SHIELD_LOCKOUT` branch is unreachable. Every static check passes. The rule is fully wired and
structurally incapable of acting.

### The fourth state: INERT

`CONFIGURED / EVALUATED / ENFORCING` cannot express that. The news shield is CONFIGURED, its code
is EVALUATED, and were the guard armed it would be ENFORCING — three greens on a rule that has
never once been able to fire.

> **INERT — the rule executes and its evidence set is empty, so its verdict is a foregone
> conclusion.**

**INERT is the state a static audit cannot see and a runtime snapshot can.** That is the whole
argument for putting the inventory in the snapshot rather than in a linter:

**every rule reports the size of the evidence it evaluated against.** News shield: `0 events
loaded`. A rule whose evidence count is zero renders red beside `CONFIGURED and not EVALUATED`,
because to an operator they mean the same thing — *this is not protecting you* — and only the
cause differs.

### What this makes the deliverable

A **registry**, not a hand-written list. Each rule is declared once with its config path, source,
scope, and **a delegate that evaluates it**:

* a rule with **no evaluator delegate** is `CONFIGURED, not EVALUATED` **by construction** — it
  cannot be mis-reported, because there is nothing to mis-report;
* a rule whose evaluator returns an empty evidence set is `INERT`;
* a rule in `shadow`, or on a disarmed account, is `EVALUATED, not ENFORCING`;
* and **a test asserts that every leaf field of `RiskConfig` and `PropFirmProtectionConfig` appears
  in the registry**, which closes the hole that produced `P1-77`, `P2-25` and `P2-78`: a field added
  to a config class and wired to nothing.

That last test is the point of the whole exercise. The three defects above are one defect — *a
config field can be born with no evaluator and nothing notices* — and the registry converts it from
something found by audit into something that cannot compile.

⚠️ **Do NOT report a rule's state from a hand-maintained table.** That is what every doc in this
repo that carried a defect count did, and all three drifted (§5.0). The state must be derived from
the registry at read time.

---

## 7. Host decision — a local browser UI, served by the bridge

**Decided 2026-08-13. Reverses §5.5.**

### 7.1 The two facts that forced it

1. **There is not one `.xaml` file anywhere in NT8's `bin/Custom`.** NT8 compiles `.cs` only. WPF here
   means hand-built code-behind *forever* — no designer, no declarative templates, no compile-checked
   bindings. That is why the current window is **1118 lines to draw four tabs**.
2. **A compile error in any addon `.cs` fails the entire Custom assembly and stops every addon
   loading — RiskGuard included.** Every line of UI code in NT8 is a line that can prevent the risk
   guard from loading. That is an unacceptable property for the least critical component in the system.

Meanwhile the bridge already has the whole data path: `HttpListener` (`McpBridgeAddOn.cs:301`), a
route switch (`:416`), auth (`:94`), and **an SSE stream** (`HandleSseStream`, `:4901`,
`text/event-stream`) — a live push channel, already built and running.

### 7.2 The comparison

| | Hand-built WPF | WebView2 in NT8 | **Browser + bridge** |
|---|---|---|---|
| Cheap to author | ❌ | ✅ | ✅ |
| UI logic testable | ❌ excluded from `RiskGuardTests.csproj` | ✅ | ✅ |
| **Can stop RiskGuard loading** | ⚠️ yes | ⚠️ **yes — smaller shell, same assembly** | ✅ **no** |
| **New machine-level dependency** | none | ⚠️ **3 DLLs in NT8's Referenced Assemblies** | none |
| Needs the bridge deployed | no | yes (HTTP) or no (postMessage interop) | ⚠️ yes |
| Live updates | `DispatcherTimer` poll | SSE | SSE (already exists) |
| Offline / no cloud | ✅ | ✅ | ✅ localhost only |

### 7.3 Why WebView2 was rejected

WebView2 solves the authoring cost but **not the blast radius**, and it makes the dependency problem
worse rather than better. It needs `Microsoft.Web.WebView2.Core.dll`, `.Wpf.dll` and the native
`WebView2Loader.dll` added to **NT8's Referenced Assemblies** — a manual, machine-local setting that
`sync_nt8.py --verify` cannot see and no test can catch. If an NT8 upgrade or reinstall drops those
references, the Custom assembly fails to compile and **every addon stops loading, RiskGuard
included**. The runtime itself is fine (it ships with Windows 11); it is the *build-time reference*
that is fragile.

By contrast the **bridge dependency already exists and is already mandatory**: deploying either addon
repo alone fails the whole Custom assembly, so both are deployed together regardless. "The UI needs
the bridge" adds essentially no new operational risk — it is a dependency already managed and already
verified by `sync_nt8.py --verify`.

### 7.4 Shape

* **A single static HTML + JS file, no build step, no framework.** Matches "as simple as it can be"
  and keeps offline capability absolute.
* Served by the bridge from a new static route. `WriteResponse` (`:5733`) currently hardcodes
  `application/json` — it needs a content-type parameter.
* Live updates over the existing SSE channel; config reads/writes over the existing JSON routes.
* **Entry point preserved**: keep an NT8 Control Center menu item (`TradeCopierWindow.cs:20-90` is
  the existing injection) that launches the default browser at `localhost`. ~20 lines, near-zero
  assembly risk.

### 7.5 Accepted costs — recorded honestly

1. **Reverses §5.5.** Recorded here and in the handover so the next session does not follow the stale
   decision.
2. **The config UI becomes bridge-dependent.** Today `TradeCopierWindow` works without the bridge.
3. **⚠️ It lands in the untested component.** `McpBridgeAddOn.cs` is excluded from the test build —
   that is `P2-27`, half done. New serving code there is code no test can reach today. **Mitigation:
   keep the bridge's share to routing and static bytes; every decision lives in core.**
4. **A token in a browser.** Localhost-only, but it is a new place the token exists.

---

## 8. RiskGatekeeper — investigated, and it stays

The handover's open question ("what to do with the 500-line risk engine in neither repo") is
**answered**.

`RiskGatekeeper` is referenced by exactly two files — `AddOns/RiskManagerAddOn.cs` and
`Strategies/Vinay/RiskManagerBase.cs` — and `RiskManagerBase` is the base class of the bot fleet:

```
RiskManagerBase : Strategy                     ← calls RiskGatekeeper
├── EMAPullbackBot, FailedAuctionBot, VWAPReclaimBot
└── IntradayStrategyBase
    └── IBStrategyBase
        └── IBBreakoutBot, IBFadeBot, IBRetestBot
```

Flow: `RiskManagerAddOn` watches accounts and feeds equity + fills → `RiskGatekeeper` holds shared
state → `RiskManagerBase.OnBarUpdate` asks `CanTrade(acct)` (`:418`) and
`WouldBreachDailyMaxLoss(potentialLoss)` (`:479`) **before entering**, and reports `RecordTrade(...)`
(`:683`) after. All gated `!isBacktest`, with local copies kept for backtesting.

**It is not a duplicate of RiskGuard — it is the other half:**

| | RiskGatekeeper | RiskGuard |
|---|---|---|
| When | **pre-trade** — refuses entry | **post-trade** — flattens and locks |
| Whose side | the **strategy's** | the **account's** |
| Consumer | the bots, via a shared base class | everything, whether it consents or not |

This is the "don't reinvent risk for every bot" scaffolding it was built to be. **Decision: keep it,
do not fold it into RiskGuard.** Two consequences:

* **Adopt it into this repo** (`F-14`). 500 lines of live risk logic in no repo, no tests, invisible
  to `sync_nt8.py --verify`. `RiskManagerBase.cs` (816 lines) likewise.
* **It is a third config surface.** `RiskManagerAddOn`'s `[Display]` properties (`DailyMaxLoss` 400,
  `TrailingDrawdown` 2000, `MaxTradesPerDay` 6, `MaxConsecutiveLosers` 2) are reconciled against
  RiskGuard's limits by **nothing**. A bot can be waved through by a gatekeeper holding different
  numbers than the guard enforcing. **The inspector must show both, per account, side by side.**
  That is the concrete payoff of one window.

### 8.1 News timeouts — the hook already exists, twice

The operator's recollection was that these components exist so NT8 strategies can reuse risk logic
rather than reinventing it. Correct, and it applies directly:

* **On the RiskGuard side the news shield is already written and already dead** — `P2-25`. Fixing it
  is "load `LocalNewsEventsFilePath` and refresh," and **tvDownloadOHLC already has the
  economic-calendar pipeline** to emit that feed (`docs/architecture/ECONOMIC_CALENDAR_ARCHITECTURE.md`
  there). Cross-repo, but not new invention.
* **On the strategy side `CanTrade` is the universal pre-trade gate** every bot already consults. A
  news blackout is just another reason it says no.

⚠️ `CanTrade` returns a bare `bool` with no reason. **Adding a reason channel (`F-15`) pays three
ways**: bots log why they stood down, the UI shows "blocked: news 14:28–14:32", and every future gate
(tilt cool-off, session lock) plugs into the same slot. Design the inspector's "why am I blocked"
field around it now, even if the channel lands later.

---

## 9. Backlog additions, and the slot each one gets

New `F-n` entries from this design pass. **`F-n` is deliberately not the `P` defect sequence and must
not be renumbered into it.**

| ID | Feature | Slot held in the layout |
|---|---|---|
| **F-1** *(existing)* | latency / slippage per follower | a **column** on the fleet row — text, `—` when unmeasured, session-scope marker. **No gauge** |
| **F-9** | **account → firm-profile mapping** | inspector › risk. **Keystone**: firm-mirror rules are loaded but unmapped, so this is what moves them from CONFIGURED to EVALUATED |
| **F-10** | Flatten Group / panic | group-header button. Exists over MCP, no UI |
| **F-11** | no-edits-while-live session lock | inspector chrome. More honest than `F-3`'s PIN — a PIN in a config file is a speed bump against your own impulse, and the UI should say so |
| **F-12** | reconciler actions as structured events | the events pane. `ReconcileAction { Verb, Subject, Leg, Reason }` exists and is flattened into a single append-only `TextBox` (`TradeCopierWindow.cs:641`) today |
| **F-13** | fill-timeout + rejected-order protection | fleet row status. Replikanto parity; cheaper than `F-4` |
| **F-14** | adopt `RiskGatekeeper.cs` + `RiskManagerBase.cs` into this repo | none — hygiene, but blocks honest display of gatekeeper limits |
| **F-15** | `CanTrade` reason channel | inspector › "why am I blocked" field |
| F-3 / F-4 / F-6 | tilt, intra-execution guard, push alerts | no slot; unchanged from §5.18 |

**Config with no editor today**, all of which the inspector must cover: `Mode` (Executions/Orders),
`PerTickerRatios`, `CustomSymbolMappings`, `MaxSlippageTicks`, `DailyLossLimit`, `IsEnabled`,
quarantine state, and **3 of the 5 `CopierSizingMode` values** — the window offers only
`QuantityRatio` and `FixedLot`, so `PerTickerMatrix` is in **neither** combo and the ratio converter
is reachable **only through the bridge**.

---

## 10. Order of work

1. **The core layer — host-agnostic, starts now.** Snapshot DTOs + apply-requests on
   `TradeCopierEngine` and `RiskGuardAddOn`; one path constant in core with the bridge delegating;
   **`P?-64` + `P?-65` closed**. All inside `RiskGuardTests.csproj`. This is handover §5.6 item 2 and
   is directly agent-loop-able.
2. **The read model** — §6's snapshot contents, including the per-rule state. Tested in core.
   **DONE in two landings.** `UI3` declared the rules and the four states (§6a); `UI4` built the
   **producer**, which was the half that could quietly give the honesty back. Registry immutable
   (`P2-82`), evaluator failures contained and named, and `UnevaluatedRules` reported independently
   of any account (`P2-83`) so a box with no accounts cannot render as healthy. 21 mutants, 0
   survivors.
3. **Bridge routes** — static serving + a snapshot endpoint; SSE already exists.
   **DONE.** `/api/riskguard/inventory` with `?view=summary` and `?account=NAME`, plus `/ui`.
   ⚠️ **One auth exemption was introduced and it is stated in the code**: a browser cannot send
   an `Authorization` header on a top-level navigation, so the **static assets only** are exempt —
   an HTML file and its JavaScript, no account data. The page holds the token in `localStorage`
   and sends it as a Bearer header on every `/api/` call, so the data path is unchanged. The
   alternative — a token in the query string — would put it in browser history and every referrer.
4. **The UI itself** — one static file, fleet + inspector + events.
   **DONE for the guard half** (`ui/index.html` in `nt8-mcp-bridge`). Fleet of accounts sorted
   worst-first, click to expand one account's rules, and the rules nothing evaluates reported once
   at the top — including when there are no accounts at all (`P2-83`).
   ⚠️ **The fleet view exists because of a measurement.** The first live read of the real box
   returned **96 accounts × 25 rules = 2400 rows and 648 KB**, on a page that polls. The summary
   brought the poll to **22 KB**. Reasoning about this would not have produced it; asking the
   deployed system did.
   **Still to do here**: the copier half (relationships, verdicts, latency/slippage with
   `measured:`), and the NT8 Control Center menu item that launches the browser (§7.4).
5. **`F-9`** firm mapping, which is what makes the risk half of the inspector tell the truth.
6. Then §5.6 item 5 onward, unchanged: `P3-31` ledger → timer → RiskGuard-side audit.

⚠️ **Do 1 before anything renders.** Every past defect in this area came from a surface that could
build its own object; until that is impossible, a prettier surface is a faster way to lose config.

---

## 11. Open questions

* **Where does the static file live?** The bridge repo serves it, but the engine it describes is in
  core. Splitting them across repos repeats the `CopierConfigFile` problem in a new place.
* **Does `P2-27` get closed first?** Putting new code in the untested component is a known cost
  (§7.5). Closing the bridge's test gap before, rather than after, is defensible.
* **Does the fleet tree show accounts with no RiskGuard profile and no copier role at all?** 96
  accounts exist on this box; most are noise.
* **`RiskManagerAddOn`'s `[Display]` limits vs RiskGuard's** — the inspector will show they disagree.
  Showing it is this design's job; **reconciling them is not**, and needs its own decision.
