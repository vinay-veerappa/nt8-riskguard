# NinjaTrader 8 File Organization

> **Path note (repo split, 2026-08-12).** This document was written while the addons lived in
> `tvDownloadOHLC`, at `scripts/ninjatrader/addons/` with the test project at
> `ninjatrader-addon/`. They now live in this repo as `addons/` and `tests/`, and the deploy
> tool is `tools/sync_nt8.py`. Operative commands and source-of-truth statements have been
> repathed. **Paths inside historical records -- "what landed", migration steps, closed
> defects -- are deliberately left as they were written**: that is what the record said at the
> time, and the hardening plan keys defects to `file:line` across that history. Rewriting them
> would falsify the trail. See [NT8_REPO_SPLIT_PLAN.md](NT8_REPO_SPLIT_PLAN.md)
>
> **Scope note.** This doc also covers `strategies/`, `indicators/` and `shared/`, which did
> **not** move here -- they remain in `tvDownloadOHLC`, together with the strategy/indicator
> half of the sync tool. In this repo only the AddOns half applies.


> **Date**: 2026-07-30, updated 2026-08-07
> **Status**: **Adopted (Option A).** The restructure to `scripts/ninjatrader/` has happened —
> that is where the code lives now. Everything below the "Current State" heading describes the
> *pre-migration* layout and is kept only as the record of why the move was made. For how things
> stand today, read this section.

---

## Source of truth and deployment (authoritative, updated 2026-08-13)

> ⚠️ **Repathed 2026-08-13.** This section still described `scripts/ninjatrader/addons/` and
> `sync_nt8_strategies.py --only addons` — **the pre-split layout in a different repository.** The
> path note at the top of this file claimed operative statements had been repathed; this one had not,
> and it is the most operative section in the document. `--only addons` over there now **exits 2**,
> so following it would have failed rather than done damage — but a deployment doc that names a
> nonexistent source of truth is exactly how the wrong copy of an addon gets treated as canonical.

**Two repos deploy into one NT8 folder, and neither can be deployed alone.**

```
nt8-riskguard/addons/*.cs        ← THE source of truth for the guard, copier, reconciler (7 files)
        │                             tools/sync_nt8.py
        │
        │   nt8-mcp-bridge/addons/McpBridgeAddOn.cs     ← THE source of truth for the bridge
        │           +  its vendor/nt8-riskguard submodule (a pinned copy of the 7 above)
        │                             tools/deploy.py
        ▼
%USERPROFILE%/Documents/NinjaTrader 8/bin/Custom/AddOns/   ← live, untracked, compiled by NT8
```

**Every AddOn compiles into ONE assembly** (`NinjaTrader.Custom.dll`) and calls the others' types
directly. So in NT8 a compile error is never local: the whole Custom assembly fails and **every**
addon stops loading, the risk guard included. **A half-deploy does not degrade the bridge — it
disarms the account.**

`tests/RiskGuardTests.csproj` compiles the same canonical `addons/` folder, minus
`McpBridgeAddOn.cs` (not in this repo) and `RiskManagerAddOn.cs` (compiling it alongside
`RiskGuardAddOn.cs` duplicates types in the *test* build only — **it is still deployed**, and
conflating a test-build exclusion with a deployment exclusion silently removes a live addon).

**Deploying:**

```bash
# the guard + copier (this repo)
python tools/sync_nt8.py --verify      # what has drifted?  expect ALL IN SYNC (7 files)
python tools/sync_nt8.py               # deploy

# the bridge -- deploys the bridge AND its vendored core, together or not at all
cd ../nt8-mcp-bridge
python tools/deploy.py --verify        # expect ALL IN SYNC (8 files, 2 orphans)
python tools/deploy.py

# then recompile in NT8 (F5, or the nt_compile MCP tool) and confirm errorCount == 0
```

> **Keep the bridge's submodule pin bumped whenever this repo moves**, and **push the tag first** —
> a submodule cannot resolve a tag that exists only locally. A stale pin does not merely fail to
> carry a fix across: because `deploy.py` owns the core too, it **overwrites a newer live core with
> an older one**. On 2026-08-12 the pin sat at `v1.0.1` while `v1.0.2` — carrying `P0-63` — was live.
> `deploy.py` now exits 2 rather than let that happen.

**Rules learned the hard way (P2-28, and the 2026-08-07 deployment):**

- **Never copy `.cs` into the NT8 tree by hand.** Use the script. Manual copies are how canonical
  and deployed drift apart in the first place.
- **Always scope the sync.** Historical: an unscoped `sync_nt8_strategies.py` also pushed strategies
  and indicators, and during the RiskGuard shadow deployment that would have installed 21 unrelated
  indicator files into a live NT8 mid-session. **`tools/sync_nt8.py` owns only `addons/` and cannot
  do this** — the hazard is gone by construction rather than by discipline, which is the better fix.
- **Never put backups inside `bin/Custom/`.** NT8 compiles that tree *recursively*, so a folder of
  `.cs` backups produces duplicate-type errors. Backups belong in
  `Documents/NinjaTrader 8/_riskguard_backups/`.
- **Normalise line endings before believing a diff.** The repo is LF, the NT8 tree tends to CRLF.
  A raw `diff` reports every line of every file as changed. The sync script's hash now normalises;
  by hand, use `diff --strip-trailing-cr`.
- **A hard link from repo to NT8 was considered and rejected.** It would make every keystroke
  change what the live trading system compiles next. The explicit deploy step is deliberate.
- **A copy that tracks what is DEPLOYED rather than what is CANONICAL is a trap regardless of how it
  is linked.** `mcp/ninjatrader-mcp/nt8-addon/McpBridgeAddOn.cs` (in tvDownloadOHLC) was a *hardlink*
  to the deployed NT8 file, so every sync dirtied that submodule with nobody editing it, and the copy
  drifted 15 hunks behind. The hardlink is broken now and that sync path exits 2, but the same shape
  recurs as a stale submodule pin. **Two things may write to `AddOns/`: `sync_nt8.py` and
  `deploy.py`. Nothing else, ever.**
- **Two files in the live `AddOns/` belong to neither repo** — `RiskGuardAddOnTests.cs` and
  `TestingStubs.cs`, reported as orphans by both deploy tools. They compile clean today, but NT8
  compiles `bin/Custom/` recursively, so they are two files away from a duplicate-type error.

---

## Current State *(pre-migration, historical)*

```
scripts/strategies/nt8/           ← all NT8 code lives here
├── addons/                        ← AddOn .cs files (synced to AddOns/)
├── base/                          ← base classes (RiskManagerBase, IntradayStrategyBase)
├── ib_breakout/                   ← IB strategies (3 bots + IBStrategyBase)
├── ema_pullback/                  ← EMA pullback strategy
├── failed_auction/                ← Failed auction strategy
├── vwap_reclaim/                  ← VWAP reclaim strategy
└── indicators/                    ← NEW (just created)
    └── redtail/                   ← 14 RedTail indicator .cs files
```

**Problems:**
1. Indicators and strategies are under `strategies/nt8/` — misleading path name
2. `sync_nt8_strategies.py` doesn't sync indicators (no `Indicators/` mapping)
3. As we build more indicators (IB Confluence, etc.), the flat structure will get messy
4. `ninjatrader-addon/` has duplicate strategy files — confusing source-of-truth

---

## Proposed Structure

```
scripts/ninjatrader/               ← TOP-LEVEL: all NT8 NinjaScript code
├── strategies/                    ← Strategy .cs files
│   ├── base/                      ← Base classes (RiskManagerBase, IntradayStrategyBase)
│   ├── ib_breakout/               ← IB strategies (3 bots + IBStrategyBase)
│   ├── ema_pullback/              ← EMA pullback strategy
│   ├── failed_auction/            ← Failed auction strategy
│   └── vwap_reclaim/              ← VWAP reclaim strategy
├── indicators/                    ← Indicator .cs files
│   ├── vinay/                     ← Our custom indicators
│   │   └── IBConfluenceIndicator.cs  ← (to be built)
│   ├── redtail/                   ← RedTail indicators (third-party, open-source)
│   │   ├── RedTailMarketStructure.cs
│   │   ├── RedTailAutoVWAP.cs
│   │   ├── RedTailKeyLevels.cs
│   │   └── ... (14 files)
│   └── third_party/               ← Other third-party indicators (future)
│       ├── FairValueGapICT.cs     ← (if we fork/modify)
│       └── ...
├── addons/                        ← AddOn .cs files
│   ├── McpBridgeAddOn.cs
│   ├── RiskGuardAddOn.cs
│   └── ...
└── shared/                        ← Shared code (referenced by both strategies + indicators)
    └── IBConfluenceEngine.cs      ← (to be extracted from IBStrategyBase)
```

### NT8 destination mapping (sync script)

```
scripts/ninjatrader/strategies/**/*.cs  →  Documents/NinjaTrader 8/bin/Custom/Strategies/Vinay/
scripts/ninjatrader/indicators/**/*.cs  →  Documents/NinjaTrader 8/bin/Custom/Indicators/
scripts/ninjatrader/addons/*.cs         →  Documents/NinjaTrader 8/bin/Custom/AddOns/
scripts/ninjatrader/shared/*.cs         →  Documents/NinjaTrader 8/bin/Custom/Strategies/Vinay/  (shared classes compile with strategies)
```

Note: NT8 compiles all `.cs` in `Custom/Strategies/Vinay/` together. Shared classes like `IBConfluenceEngine` need to be in a folder NT8 can find — the simplest approach is to sync them to `Strategies/Vinay/` alongside the strategies (NT8 doesn't enforce folder = namespace). Alternatively, put them in `Custom/Indicators/` if they're indicator-only.

---

## Migration Plan

### Step 1: Create the new folder structure
```powershell
mkdir scripts/ninjatrader/strategies/base
mkdir scripts/ninjatrader/strategies/ib_breakout
mkdir scripts/ninjatrader/strategies/ema_pullback
mkdir scripts/ninjatrader/strategies/failed_auction
mkdir scripts/ninjatrader/strategies/vwap_reclaim
mkdir scripts/ninjatrader/indicators/vinay
mkdir scripts/ninjatrader/indicators/redtail
mkdir scripts/ninjatrader/indicators/third_party
mkdir scripts/ninjatrader/addons
mkdir scripts/ninjatrader/shared
```

### Step 2: Move existing files
- `scripts/strategies/nt8/base/*.cs` → `scripts/ninjatrader/strategies/base/`
- `scripts/strategies/nt8/ib_breakout/*.cs` → `scripts/ninjatrader/strategies/ib_breakout/`
- `scripts/strategies/nt8/ema_pullback/*.cs` → `scripts/ninjatrader/strategies/ema_pullback/`
- `scripts/strategies/nt8/failed_auction/*.cs` → `scripts/ninjatrader/strategies/failed_auction/`
- `scripts/strategies/nt8/vwap_reclaim/*.cs` → `scripts/ninjatrader/strategies/vwap_reclaim/`
- `scripts/strategies/nt8/addons/*.cs` → `scripts/ninjatrader/addons/`
- `scripts/strategies/nt8/indicators/redtail/*.cs` → `scripts/ninjatrader/indicators/redtail/`

### Step 3: Update sync script
Update `sync_nt8_strategies.py` to:
- Read from `scripts/ninjatrader/` instead of `scripts/strategies/nt8/`
- Sync `indicators/` subfolders to `Custom/Indicators/` (flatten — NT8 expects all indicators in one folder)
- Sync `shared/` to `Custom/Strategies/Vinay/` (so strategies can reference shared classes)

### Step 4: Remove old `scripts/strategies/nt8/` folder
After verifying the sync works from the new location.

### Step 5: Update all references
- `CLAUDE.md` — update any paths referencing `scripts/strategies/nt8/`
- `.github/copilot-instructions.md` — update sync command
- `sync_nt8_strategies.py` — update source paths
- Memory files — update any path references

---

## Why this structure

| Principle | How it's addressed |
|---|---|
| **Clear separation** | `strategies/` vs `indicators/` vs `addons/` vs `shared/` — no ambiguity |
| **Third-party isolation** | `indicators/redtail/` and `indicators/third_party/` keep external code separate from ours |
| **Our indicators have a home** | `indicators/vinay/` is where `IBConfluenceIndicator` and future custom indicators live |
| **Shared code** | `shared/` for classes used by both strategies and indicators (e.g., `IBConfluenceEngine`) |
| **Sync-friendly** | Each top-level folder maps 1:1 to an NT8 `Custom/` subfolder |
| **Scalable** | New strategies/indicators just drop into the right folder — no structural changes needed |
| **Git-friendly** | Moving files preserves history with `git mv` |

---

## Alternative: Keep `scripts/strategies/nt8/` but add `indicators/`

If you prefer not to move existing strategy files, we can keep the current root and just formalize the indicators subfolder:

```
scripts/strategies/nt8/
├── addons/
├── base/
├── ib_breakout/
├── ema_pullback/
├── failed_auction/
├── vwap_reclaim/
├── indicators/
│   ├── vinay/                     ← our custom indicators
│   ├── redtail/                   ← RedTail (already here)
│   └── third_party/               ← other third-party
└── shared/                        ← shared classes
```

This is less work (no file moves) but the path `scripts/strategies/nt8/indicators/` is slightly misleading since indicators aren't strategies.

---

## Decision needed

1. **Option A**: Full restructure to `scripts/ninjatrader/` (cleaner, more work)
2. **Option B**: Keep `scripts/strategies/nt8/` and add `indicators/vinay/` + `shared/` (less work, slightly misleading path)

Either way, the sync script needs updating to handle indicators → `Custom/Indicators/`.