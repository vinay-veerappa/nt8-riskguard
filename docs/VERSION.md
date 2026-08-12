# Version history

> ## ⚠️ There are THREE version identifiers for this addon, and only one is authoritative
>
> | Identifier | Value | Authoritative? |
> |---|---|---|
> | **Git tag on `main`** | **`v1.0.2`** | ✅ **Yes.** It is what `tools/sync_nt8.py` deploys and what `nt8-mcp-bridge` pins its submodule to. |
> | `RiskGuardAddOn.Version` const (`addons/RiskGuardAddOn.cs:35`) | `1.1.0` | ❌ No. Reported over `GET /api/riskguard/version`, and **hand-maintained, so it drifts.** |
> | The `v1.7.0-ui-audit` scheme this file used to lead with | — | ❌ No. A pre-hardening release-notes scheme, abandoned mid-2026-07 and unrelated to the tags. |
>
> **Trust the git tag and the file hashes.** `python tools/sync_nt8.py --verify` compares content;
> a version string compares nothing. This was recorded as a trap on 2026-08-13 after all three
> disagreed on a live box — the deployed, correct build reported itself as `1.1.0` while the repo
> was tagged `v1.0.2` and this file claimed `v1.7.0-ui-audit`.
>
> **To find what is actually deployed**: `git -C . describe --tags` for the repo, and
> `tools/sync_nt8.py --verify` for whether NT8 has it.

---

## Tagged releases (this repo, post-split)

These are the real versions. The repo was created by the 2026-08-12 split; everything before it is
under "Pre-split history" below.

### `v1.0.2` — 2026-08-12 · **deployed, live in NT8**

Two defects from the hardening backlog, both driven test-first through the agent loop.

- **`P0-63` FIXED (remedy 3)** — `Account.Change()` is a **silent no-op on `provider: Simulator`
  accounts**, so the mirrored follower stop had **never trailed**. `Change()` is a *request*: the
  caller's desired values sit on the `Order` until the provider settles, and an unhonoured change
  **reverts** on settle. Detection is therefore *"the settled order is still at its pre-change
  values"* — positive evidence, fails safe — and recovery re-drives the leg through
  `SyncFollowerStop` (the wrapper, which holds `P1-56`'s in-flight reservation) as
  cancel-then-create. Modify-in-place is preserved for providers that honour it.
- **`P?-66` INSTRUMENTED** — `ObserveFollowerFill` had **five ways to return without recording
  anything**, all leaving the same trace: none. So `LatencyMs: 0.0, AvgSlippageTicks: 0.0` was
  uninterpretable. Six distinct events now: `FILL_MEASURED`, `FILL_ORDER_MISSING`,
  `FILL_NOT_MEASURED`, `FILL_RELATIONSHIP_MISSING`, `LATENCY_REJECTED`,
  `SLIPPAGE_NOT_COMPARABLE`. **No behaviour changed** — same measurements, same sanity bound, same
  quarantine decision. **`P?-66` remains OPEN**: instrumentation is not an answer.
- Suite **926 → 953**. New mutation battery `mutation/mutate_p0_63.py` (7 mutants, 0 survivors), and
  `mutate_cm3`/`mutate_cm4` now **refuse to run from a red baseline** — they had been vacuous
  whenever the baseline was failing.

### `v1.0.1` — 2026-08-11 · docs only

The repo split recorded as executed. No code change.

### `v1.0.0` — 2026-08-11 · first tagged core after the split

`nt8-riskguard` extracted from `tvDownloadOHLC` with `git-filter-repo`, full history preserved:
guard + copier + reconciler + test suite + mutation batteries + deploy tool + agent-loop profile.
Suite **926/0** (929 minus three assertions that moved to `nt8-mcp-bridge` with
`McpBridgeAddOn.cs`). A migration, not a defect — nothing closed.

> **`McpBridgeAddOn.cs` is NOT in this repo.** It lives in
> [nt8-mcp-bridge](https://github.com/vinay-veerappa/nt8-mcp-bridge), which consumes this repo as a
> submodule pinned to a tag. Entries below that mention it are pre-split history.

---

## Pre-split history

> **A different, abandoned numbering scheme.** These `v1.x` numbers are **not** comparable to the
> tags above — `v1.7.0-ui-audit` came *before* `v1.0.0`. Kept because the entries record what
> shipped when, and several are cited from the hardening plan.

### `v1.7.0-ui-audit` (2026-07-25) — UI/UX audit and feature work

1. **Interactive UI (`TradeCopierWindow.cs`)**: inline `Unquarantine / Quarantine` toggles on
   relationships and group controls; non-blocking 1.5s hold-to-confirm panic controls for mass
   account liquidations; real-time execution-audit stream panel.
2. **Three copier safety rules (`TradeCopierEngine.cs`)**: delta-based hedging prevention; an
   event-driven position reconciler comparing follower vs leader direction; auto-close of follower
   positions when the leader reaches 0 qty.
3. **Planned, not built**: execution latency/slippage badges, red-folder news shield overlay.

> Much of this was later found to be **written but not wired** — see `P2-24` ("written-but-never-called
> safety machinery"), `P2-25` (the news shield can never fire in production) and `P1-22` (the
> latency/slippage fields were fake). **A changelog entry is not evidence a feature works.** The
> hardening plan exists because this release read as complete and was not.

### `v1.6.0-audit` (2026-07-25)

- Thread-safe emergency-flatten sequence (`AUDIT-NT8-001`)
- Atomic RiskGuard persistence model (`AUDIT-NT8-002`)
- Trade-copier threading and scaling precision (`AUDIT-NT8-003`)

### `v1.5.0` (2026-07-21)

- **`TradeCopierEngine.cs`**: local trade copier — multi-account leader→follower replication with
  ratio scaling.
- **`PropFirmProtectionSuite.cs`**: USD red-folder news shield, evaluation target lock.
- **`McpBridgeAddOn.cs`** (now in `nt8-mcp-bridge`): five MCP tools — `nt_inspect_strategy`,
  `nt_get_logs`, `nt_capture_chart`, `nt_open_chart`, `nt_subscribe_fills`.

### `v1.0.0` (initial release)

Base RiskGuard AddOn: protective-stop guard (FSM state machine), daily loss limits, trailing
drawdown limits.
