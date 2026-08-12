# nt8-riskguard

A NinjaTrader 8 AddOn that enforces risk rules on funded futures accounts, and a trade
copier that mirrors a leader account's fills onto followers.

Extracted from `tvDownloadOHLC` on 2026-08-12 with full history (see
[docs/NT8_REPO_SPLIT_PLAN.md](docs/NT8_REPO_SPLIT_PLAN.md)). This repo is the **canonical
source**. Never edit the copies NinjaTrader compiles from.

## Layout

```
addons/     the AddOn sources NT8 compiles
tests/      RiskGuardTests.csproj -- a plain net8.0 console runner, plus NT8 API stubs
mutation/   mutation batteries; a surviving mutant means a test only looks like coverage
tools/      sync_nt8.py -- the only sanctioned way to deploy into NT8
agent/      agent-loop profile and the defect tickets it consumes
config/     a sample RiskGuard config
docs/       hardening plan (the defect index), session handover, design docs
```

## Build and test

```bash
dotnet build tests/RiskGuardTests.csproj -v q --nologo
dotnet run --project tests/RiskGuardTests.csproj --no-build     # 1028 passed / 0 failed
python mutation/mutate_cm3.py                                   # 14 mutants, all killed
python mutation/mutate_cm4.py                                   # 10 mutants, all killed
python mutation/mutate_p0_63.py                                 #  7 mutants, all killed
python mutation/mutate_p1_71.py                                 #  9 mutants, all killed
python mutation/mutate_p0_67.py                                 # 10 mutants, all killed
```

The suite is a plain `Main()` that calls every test method; there is no test framework.
`RiskGuardAddOnTests.cs` ends with a harness self-check asserting that every declared
test method was actually invoked, because a runner that silently skips tests is worse
than no runner.

`RiskManagerAddOn.cs` is excluded from the test build (superseded by `RiskGuardAddOn.cs`;
compiling both duplicates types). It still deploys.

Three structural checks. All three have been watched fail, so they can actually fail:

```bash
python tools/check_direction.py              # this repo must never name a bridge type
python tools/check_no_stray_copies.py        # exactly one copy of each addon source
python tools/check_ci_runs_every_battery.py  # no battery that CI does not run
```

The third exists because a battery was left out of CI twice, each time leaving CI weaker
than the local gate while looking complete. It also refuses an empty `mutation/`, since a
check that iterates a collection passes trivially when the collection is empty.

**CI runs all of the above on every push and pull request** — all five batteries, enforced —
on `windows-latest`, from
[.github/workflows/ci.yml](.github/workflows/ci.yml) -- active since 2026-08-13. Deploy
parity is deliberately *not* in CI: it compares against a NinjaTrader install that exists
only on the trading machine, so on a hosted runner it would pass vacuously, and a green
check that proves nothing is worse than an absent one.

### Install the pre-commit hook -- once per clone

```bash
git config core.hooksPath .githooks
```

`.githooks/pre-commit` refuses build output, binaries and anything over 50 MB.
`core.hooksPath` is **local config, not tracked**, so a fresh clone has no hook until
you run that line -- and nothing will tell you. Deliberate override:
`ALLOW_BIG_FILES=1 git commit ...`.

## Deploy

```bash
python tools/sync_nt8.py --verify    # what has drifted?
python tools/sync_nt8.py             # deploy
```

Then recompile inside NT8. **Never hand-copy `.cs` into
`Documents/NinjaTrader 8/bin/Custom/AddOns/`** -- the traps are recorded in
[docs/NT8_FILE_ORGANIZATION.md](docs/NT8_FILE_ORGANIZATION.md).

## Consumers

NT8 has no package manager: every AddOn compiles into one assembly
(`NinjaTrader.Custom.dll`) and calls the others' types directly. So a consumer needs a
**compile-time source dependency**, not a package reference.

[`nt8-mcp-bridge`](https://github.com/vinay-veerappa/nt8-mcp-bridge) consumes this repo as
a git submodule at `vendor/nt8-riskguard`, pinned to a tag, and deploys both trees
together. It reaches this code through two singleton facades --
`RiskGuardAddOn.Instance` and `TradeCopierEngine.Instance`, about 26 members in total.

**The dependency is one-way and must stay that way.** This repo must never name
`McpBridgeAddOn`; `tools/check_direction.py` fails if it does. If that inverts, the two
repos become mutually recursive and the split is dead.

## Reading order for the risk rules

1. [docs/RISKGUARD_COPIER_HARDENING_PLAN.md](docs/RISKGUARD_COPIER_HARDENING_PLAN.md) --
   the defect index, keyed to `file:line`. Defect IDs are never renumbered or reused.
2. [docs/RISKGUARD_HARDENING_HANDOVER.md](docs/RISKGUARD_HARDENING_HANDOVER.md) -- live
   state. **Read section 0, then section 5 (THE OPEN BACKLOG), starting at 5.6.** The file
   accretes and a later section supersedes an earlier one; section 4a is historical and is
   explicitly not a plan.
3. [docs/RiskGuardAddOn.md](docs/RiskGuardAddOn.md) -- design doc. Known to have drifted
   from the code (open defect `P2-26`).

## Status

This code manages real money on live funded accounts, and it is **not finished hardening**.
**75 defect IDs; 61 closed, 14 open.** Tag `v1.1.0` is the deployed code, live in NT8 in
`shadow` mode; suite 1028/0, five mutation batteries with 0 survivors.

**`P0-63` was validated live on 2026-08-13** by one 1-lot MNQ round trip on `Sim101 -> Sim-ORB`.
`Account.Change()` being a silent no-op meant the mirrored stop had **never trailed**; the log
now shows the provider ignoring the change, the fallback detecting it on settle, and the stop
replaced at the correct price with no unprotected window and no duplicate leg. `P?-66` closed
in the same trade: both fills measured (142.86 ms / 0 ticks entry, 314.21 ms / -4 ticks exit).

That trade opened four new defects, and **all four are now fixed, deployed and -- where a live
check is possible -- live-validated**, together with `P0-67` and a sixth defect the work
uncovered (two `Change()` calls landing on one stop order in a single sweep, which reverts it).
`nt_change_order` no longer claims `"modified"` without observing it; the copier's audit log can
no longer drop a copy in silence; and the latency/slippage metrics are readable over a GET. See
the handover's section 5.14.

Four more (`P1-72`…`P1-75`) were opened and closed on 2026-08-13 by widening the MCP wrapper's
argument surface -- a pass whose *subject* was tooling and whose *output* was defects, because
stating what each field does forces you to check. The one worth reading is **`P1-75`: reading the
prop-firm rules DISARMED them**, latent only because `prop_limits.json` does not exist on this box
and the first write creates it. See the handover's section 5.16.

The highest open defects are now **`P?-64`/`P?-65`**: the copier UI writes to a different file
than anything reads, so every UI change is lost on restart, and its two save sites destroy the
ratio matrix.

**Read the handover before trusting any of it** -- in particular sections 5.13 and 5.14.
