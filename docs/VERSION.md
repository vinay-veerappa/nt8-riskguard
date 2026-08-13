# Version history

> ## ⚠️ There are THREE version identifiers for this addon, and only one is authoritative
>
> **Re-measured 2026-08-13 after session 29.** Every value below was read off the repo and the live
> box, and the two disagree *right now* — see the warning under the table.
>
> | Identifier | Value | Authoritative? |
> |---|---|---|
> | **Git tag on `main`** | **`v1.12.1`** (18 tags, `v1.0.0`…`v1.12.1`) | ✅ **Yes.** It is what `tools/sync_nt8.py` deploys and what `nt8-mcp-bridge` pins its submodule to. |
> | `RiskGuardAddOn.Version` const (`addons/RiskGuardAddOn.cs:39`) | ⚠️ **`1.10.0`** — two minor versions behind | ❌ No. Reported over `GET /api/riskguard/version`, and **hand-maintained, so it drifts.** |
> | The `v1.7.0-ui-audit` scheme this file used to lead with | — | ❌ No. A pre-hardening release-notes scheme, abandoned mid-2026-07 and unrelated to the tags. Note the collision: there is now a real `v1.7.0` tag that has nothing to do with it. |
>
> ⚠️ **THE DRIFT IS LIVE, AND CI HAS BEEN SAYING SO FOR 7 RUNS.** The deployed code is `v1.12.1`
> (verified by content hash, `sync_nt8.py --verify` → ALL IN SYNC, 8 files) and the running addon
> answers **`1.10.0`**. `tools/check_version_matches_tag.py` — added by `c92605e` for exactly this
> failure — fails the build, and two tags shipped over it anyway. **Bump the constant in the same
> commit as the tag, as the gate asks.**
>
> **Trust the git tag and the file hashes.** `python tools/sync_nt8.py --verify` compares content;
> a version string compares nothing. First recorded as a trap on 2026-08-13 after all three
> identifiers disagreed on a live box; it has now happened twice, the second time with a gate already
> in place and red.
>
> **To find what is actually deployed**: `git describe --tags` for the repo, and
> `tools/sync_nt8.py --verify` for whether NT8 has it. **Never the version string.**

---

## Tagged releases (this repo, post-split)

These are the real versions. The repo was created by the 2026-08-12 split; everything before it is
under "Pre-split history" below.

### ⚠️ `v1.0.3` … `v1.12.1` — derived, not written up

**This file's prose notes stop at `v1.0.2` and fifteen tags shipped after it.** Rather than
back-fill fifteen sections from memory — which is how the identifier table above came to name a tag
that was 11 releases old — the table below is **derived from `git`**: date, subject, and whether the
release touched `addons/` at all. The narrative for each lives in the handover section named in the
last column, which is where it was actually written down.

```bash
# regenerate this table instead of maintaining it
for t in $(git tag --sort=v:refname); do
  echo "$t | $(git log -1 --format=%ad --date=short $t) | core=$(git diff --name-only $t^ $t -- addons/ | wc -l) | $(git log -1 --format=%s $t)"
done
```

| Tag | Date | Touched `addons/`? | What it carried | Written up in |
|---|---|---|---|---|
| **`v1.12.1`** | 2026-08-13 | in-range: **`GuardRules.cs`** | Re-pointed the `ui3` mutation anchor a `GuardRules` comment edit had broken — **a stale anchor scores a SURVIVOR, silently** | §5.25 |
| `v1.12.0` | 2026-08-13 | — | agent-loop ledger + learning feedback from the config-defaults session | §5.25 |
| `v1.11.0` | 2026-08-12 | — | `CONFIG_DEFAULTS.md` — the defaults defined from a trader's frame, plus a battery fix | §5.25 |
| `v1.10.0` | 2026-08-12 | 3 | `UI7` — a refused write carries its reason, instead of arriving as a `NullReferenceException` | §5.24 |
| `v1.9.0` | 2026-08-12 | 3 | A Control Center menu item, and operator-facing notes | §5.24 |
| `v1.8.0` | 2026-08-12 | 2 | `UI6` — the copier's wire format, and the severity order the enum does not give you | §5.23 |
| `v1.7.0` | 2026-08-12 | 2 | Account equity + trade count on the wire, so a surface can filter | §5.23 |
| `v1.6.0` | 2026-08-12 | 2 | `UI5` — the fleet summary, **because the real box has 96 accounts** | §5.23 |
| `v1.5.0` | 2026-08-12 | 1 | The rule inventory gets a wire format | §5.22 |
| `v1.4.0` | 2026-08-12 | 1 | The rule inventory gets a producer (`UI3`) | §5.22 |
| `v1.3.0` | 2026-08-12 | 1 | `UI1` + `UI2` — the UI redesign's host-agnostic core layer. **`P?-64`/`P?-65` closed here**, on the engine rather than the window | §5.21 |
| `v1.2.1` | 2026-08-12 | 1 | `P1-76`/`P1-77`/`P2-78` filed; the feature audit | §5.17 |
| `v1.2.0` | 2026-08-12 | 1 | `P1-76` — a follower belongs to a direct relationship **or** a group, not both | §5.16 |
| `v1.1.0` | 2026-08-12 | 1 | `P0-67` — the third `Change()` site stops believing its own write | §5.14 |
| `v1.0.3` | 2026-08-12 | — | Docs: the handover re-derived from the repo, 15 dropped review findings restored | §5.12 |

⚠️ **`v1.11.0`, `v1.12.0` and `v1.12.1` each touch no `addons/` file in their own tagged commit**, but
the **range** `v1.12.0..v1.12.1` does (`GuardRules.cs`). That distinction is the whole reason
`nt8-mcp-bridge`'s stale-pin guard compares a *range* against `addons/` rather than a single commit —
a pin that looks like it trails only docs can still revert live code.

### `v1.0.2` — 2026-08-12 · ~~deployed, live in NT8~~ superseded by `v1.12.1`

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
