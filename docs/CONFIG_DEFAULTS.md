# Config defaults — what they are, and why

**Status:** doctrine agreed 2026-08-13, and **every delta in this document is now applied** —
`P1-82` (R2), `P1-83` (§4), `P1-84` (R4/R5). Two further defects were opened *by* applying them
and are closed: `P1-86` (switching off a broken rule hid that it was broken) and `P1-87` (an
unrecognised stop action silently disabled the stop guard). See §7.
**Scope:** all three config surfaces — the copier (`copier_config.json`), the guard
(`RiskGuard/config.json`), and the prop-firm suite (`prop_limits.json`, which does not exist on
this box until something writes it).
**Related:** `RISKGUARD_COPIER_HARDENING_PLAN.md` (`P1-77`, `P2-25`, `P1-81`), `UI_REDESIGN_DESIGN.md`
§2.1 (the five-state vocabulary), `RISKGUARD_HARDENING_HANDOVER.md` §0.

---

## 1. What a default is for, here

This is not a preferences file. Every value below either prevents an account-ending mistake or
gets in the way of a legitimate trade, and most of them can do both depending on the number.

So the frame is a trader's, not an engineer's:

* **The account being protected is a prop evaluation account.** Losing it costs the eval fee and
  the reset, and the loss is *discrete* — one breach ends it, regardless of how the rest of the
  month went.
* **The worst outcome is not a losing trade.** It is a rule breach that fails the account
  instantly: the daily loss limit, or the trailing drawdown. Those are hard fails with no appeal.
* **The second worst outcome is the guard flattening a good trade for no reason.** That is not
  merely annoying. It is how the guard ends up switched off, and a guard that is off during the
  one session that mattered has provided exactly nothing. **A default that fires on a normal day
  is a default that disarms the system.**

Everything below follows from those three.

---

## 2. The five rules

### R1. Ship disarmed. Always.

`Mode = "shadow"`, and every `ArmedForLive` on every object defaults to `false`. A guard that
arrives armed, carrying dollar limits it guessed, will flatten a live position on day one. Already
true everywhere, and it is the one rule with no exceptions.

### R2. A default must never read as protection that does not exist.

**This is the rule the system currently breaks, and it breaks it in the two places that matter
most.** If the rule inventory reports a rule as `CONFIGURED-not-EVALUATED` or `INERT`, then its
enabling flag must default to `false`.

The reasoning is not stylistic. A flag that defaults `true` on a rule nothing reads produces a
config file that *reads as protection* — you open it, you see `"EnableNewsShield": true`, and you
size your position accordingly. Defaulting it `false` costs nothing (the rule does nothing either
way) and removes the false assurance entirely.

Measured on the live box, 2026-08-13, via `/api/riskguard/inventory`:

| Flag | Default | Inventory state | Defect |
|---|---|---|---|
| `PropFirm.EnableNewsShield` | **`true`** | `INERT` — 0 events loaded, `IsInNewsWindow` can only return false | `P2-25` |
| `PropFirm.EnableConsistencyCap` | **`true`** | `CONFIGURED-not-EVALUATED` — no code reads it | `P1-77` |

Those are the **only two flags in the entire system that default ON while doing nothing**, which
is what makes them the highest-value change in this document.

**Applied as `P1-82`, and it took four literals rather than two.** Each of these defaults is
stated *twice* — once as a property initializer and once as the parser's final fallback — and the
parser copy is what runs for any config file that predates the field, which is every config file
on this box. Fixing only the property would have been green in the suite and unchanged in
production.

⚠️ **R2 IS NOT SAFE ON ITS OWN, and the plan said so before we did it.** The `P1-77` entry in
`RISKGUARD_COPIER_HARDENING_PLAN.md` warns in writing: *do not "fix" a dead flag by defaulting it
to false, that keeps the lie and makes it quieter.* Half of that objection is dead and half was
exactly right.

* It does **not** hold for the consistency cap. `CONFIGURED-not-EVALUATED` is derived from
  `Evaluator == null`, so that row stays red whatever the flag says.
* It held precisely for the news shield, whose evaluator opened with
  `!EnableNewsShield ? Off(...)`. With the flag off the inventory reported it **`Disabled`** — a
  state this codebase documents as *"not a defect"*. Switching off a rule that could never have
  fired downgraded its defect to a preference, silently.

So R2 carries a companion rule, applied as `P1-86`: **`Disabled` means "this would work if you
turned it on"**. A rule with no evidence to evaluate does not qualify however its switch is set,
so it must report `INERT` either way. Do not apply R2 to a rule without checking that its
evaluator still reports the defect when the switch is off.

### R3. A dollar limit is derived from the account, never guessed.

Every dollar-denominated default in the system was chosen for one unstated account size:

* `PnLRules.DailyLossLimit = 1000`
* `PnLRules.TrailingDrawdown = 1500`
* `FirmMirror.TrailingDD.Amount = 2500`, `FirmMirror.DailyLoss.Amount = 1500`
* `PropFirm.EvaluationTargetProfit = 3000`

On a $50k evaluation those are roughly right. On a $150k account the $1,000 daily limit fires on
an ordinary red day — R1's failure mode, and you will turn it off. On a $25k evaluation the same
$1,000 sits *above* some firms' own limit and is therefore not a buffer at all; the firm fails you
before the guard speaks.

The mechanism that fixes this already exists and is switched off: `FirmMirror.Enabled = false`
with an empty `AccountFirmMap`. **Until an account is mapped to a firm, the honest default is not
a different number — it is no number, and a rule that says so.** The inventory can render that
now; it could not when these values were chosen.

This is `F-9`, and it is the single change that makes the risk half of the UI tell the truth.

#### R3a. The four researched profiles were destroyed, and this is the only surviving copy

Written 2026-08-13 while acting on R3. The sentence above says the mechanism "already exists and is
switched off". That was **half true**: `FirmMirror.Enabled` is `false` and `AccountFirmMap` is empty,
as stated — but `FirmProfiles` is empty **too**, and it did not use to be. The plan records four
fully researched profiles present in the live config on 2026-08-07 (§ *"P1-42"*). They are gone.

**`P2-41` took them.** A single `nt_riskguard_config` call with no arguments POSTed an empty body,
which deserialised `{}` into a complete `RiskConfig` and wrote it — and among the things it reset to
default was `FirmProfiles`, to `{}`. The defect is closed (`RiskConfigMerge`), but it ran on this box
before it was, and this document then recorded the wreckage as the baseline without noticing that a
collection had gone missing from it. **A default and an erasure look identical in a config file.**

The four profiles below were recovered from
`Documents/NinjaTrader 8/RiskGuard/config.json.bak_prearm_20260807_061407`. They are written here
because a doc is in git and a `.bak` file is one cleanup away from gone.

| Firm | TrailingDD | DailyLoss |
|---|---|---|
| `TakeProfitTrader` | `eod`, 1500 / buffer 200, excl. unrealized | **OFF** — TPT has no daily loss limit |
| `Tradeify` | `eod`, 2000 / buffer 200, lock-at-profit 100 | `include_unrealized_peak`, 1250 / buffer 100 |
| `Lucid` | `eod`, 2500 / buffer 200 | `include_unrealized_peak`, 2500 / buffer 200 |
| `Apex` | `eod`, 2000 / buffer 200 | `include_unrealized_peak`, 1000 / buffer 100 |

⚠️ **Two of the four have a sub-rule switched off or set differently from the top-level block.** That
is not an edge case, it is the norm — and it is what made the reporter's disagreement with the
enforcer (§F-9 below) a defect in *both* directions rather than one.

⚠️ **None of the four states an account size, which is R3's own complaint.** Apex's published
trailing threshold is $2,500 on a 50k and $3,000 on a 100k; this profile says $2,000, which matches
neither. Tighter than the firm's own number is the safe direction — the guard speaks before the firm
does, which is what `Buffer` is for — but *nobody can tell from the config which direction it is*.
So the keys change: `FirmProfiles` is now keyed by **plan**, not by firm — `Apex-100K`,
`TakeProfitTrader-50K`. The key is an opaque string, so this needs no code change, and one "Apex"
entry carrying one dollar amount **cannot** serve a 50k and a 100k account, which is the fleet this
box actually has.

#### R3b. The map cannot be completed from measurement, and here is exactly why

Measured 2026-08-13 via `nt_accounts`, because "map the rest of the accounts" turns out not to be a
typing exercise.

**Only 6 of the 96 accounts report any equity at all**: the five Sim accounts and
`TAKEPROFITPRO524207503`. The other ~89 return `cashValue: 0, netLiquidation: 0` — expired or
unconnected prop accounts the connection still lists. **So the platform does not know their size**,
and equity cannot supply it. There is no field that can: the payload is
`name / provider / denomination / cashValue / netLiquidation / realizedPnL / unrealizedPnL / buyingPower`.

What the names *do* carry:

| Prefix | Firm | Size in the name? |
|---|---|---|
| `TAKEPROFIT*`, `TAKEPROFITPRO*` | Take Profit Trader | no |
| `APEX*`, `PAAPEX*` (`PA` = performance/funded) | Apex | no — `101215` is an account id, not a size |
| `TDYG*`, `TDFYG*`, `FTDFYG*` | Tradeify | ⚠️ **apparently yes** |
| `LFE*` | Lucid | no |

⚠️ **The Tradeify pattern is an OBSERVATION, not a rule, and must not be used to write risk config
until someone confirms it.** Five accounts read `TDYG50...` and one reads `TDYG100...`, which looks
exactly like the plan size in thousands — but that is six samples and an inference, and the whole
point of R3 is that a dollar limit is not inferred. `provider` is `Provider31` for every real prop
account and `Simulator` for every Sim one, which is worth knowing separately: `P1-20` already
settled that sim accounts are identified by provider and never by a name prefix.

**So completing the map needs the operator to state a size per account.** That is not a gap in the
tooling; it is information that exists only outside the platform.

#### R3c. The firms' actual published numbers — and both deployed plans are wrong

See **[FIRM_PLANS_RESEARCH.md](FIRM_PLANS_RESEARCH.md)**, researched 2026-08-13 for Apex, Take Profit
Trader, Tradeify and Lucid, at the operator's request and pending their correction.

Three things it establishes that change R3a's conclusions:

1. ⚠️ **Both plans `F-9` deployed carry the wrong numbers.** The recovered `TakeProfitTrader` profile
   (1500) is the **25K** max loss, deployed as a 50K (should be **2000**); the recovered `Apex` profile
   (2000 DD / 1000 DLL) is Apex's **50K EOD** row *exactly*, deployed as a 100K (should be **3000 /
   1500**). The recovered `Lucid` profile (2500/2500) matches **no Lucid plan at any size**.
2. ⚠️ **One of those errors is in the dangerous direction.** A TPT **PRO** account trails
   **intraday**, not `eod`. An intraday trail follows peak equity *including unrealized*, so its floor
   rises during a winning session while an EOD model's stays stale and lower — the firm's floor ends up
   **above** the guard's and the firm fails you first. The amount errors both err tighter, which is
   safe but fires early (R5).
3. ⚠️ **Firm + size is not a plan.** Every one of the four firms sells multiple rule sets at the same
   size — Tradeify's 100K max loss is 2500, 3000, 3500 or 4000 depending on family; a TPT PRO trails
   intraday where Test and PRO+ trail EOD; Apex sells an EOD variant *with* a DLL and an intraday
   variant *without* one. So the key must be **firm + plan + size**, which costs no code and changes
   what has to be known about an account before it can be mapped.

It also names what this guard **cannot** express — consistency rules (`P1-77`, still open, and the rule
most likely to void a payout), Lucid's `LucidScale` DLL of 60%-of-highest-EOD-profit, and soft-vs-hard
DLL breaches — because a profile that silently omits a firm rule is `CONFIGURED`-not-`EVALUATED`
wearing a firm's name.

**What IS machine-checkable, and is `F-9b`:** `FirmProfile.AccountSize` (added 2026-08-13) plus a
preflight refusal on two silent failures — a mapping naming an account that does not exist, and a
plan whose stated size contradicts the account's observed equity. The first is `P1-90`'s class one
layer out: there a name that did not resolve placed an order on the wrong account, here it removes
protection from the right one, and the operator's own spelling of `Sim_All_Day_ORB` in the session
that mapped it used a **hyphen**. Both refusals name the offending value, because a refusal that
does not is not actionable.

⚠️ Two things that check must NOT do, each pinned by a test: an **unstated** size (`0`) is checked
for nothing — the check is opt-in per plan, or adding a plan locks you out of arming until you have
researched a number you may not have; and a **zero-equity** account is not size-checked, because 89
of 96 read zero and refusing over those would mean this box never arms again. But a zero-equity
account is still *existence*-checked, or that exemption swallows the whole gate.

### R4. Two names for one concept carry one number.

The copier's `MaxPositionSize` defaults to **100**. The guard's `Sizing.MaxContractsPerAccount`
defaults to **10**. They cap the same thing. The lower always binds, so **the copier's cap has
never stopped anything** — it is decoration that reads like a limit.

Two limits on one quantity is worse than one, because you will read whichever you happen to open
and size against it.

### R5. A default that fires on a normal day trains you to disarm.

`StopGuard.StopAttachSeconds = 3`. Three seconds from fill to a working stop, or the guard acts —
and `StopGuard.OnMissing = "Flatten"`, so it acts by flattening you.

If you enter manually and then place your stop, three seconds is not enough time to reach the
mouse. The guard will flatten good entries, repeatedly, on days when nothing is wrong. **This is
the most likely single reason this system gets switched off**, and it is a one-line change.

---

## 3. The defaults, with the trader's reason

Values marked **→** were changed; everything else is a decision to keep what is there. Every
change named below is applied and pinned by a mutation battery.

### 3.0 Copier — GLOBAL (`P3-34`, core `v1.15.0`)

One switch, above every relationship. It is the copier's own, deliberately **not** a reading of
the guard's mode: the operator drives sim copies while the guard sits in `shadow`, which is how
§5.13's live validation was run, and following the guard's mode would take that away.

| Field | Default | Why |
|---|---|---|
| `CopierMode` | **`live`** | ⚠️ **Deliberately not `shadow`, and this is the one default in this file chosen to preserve existing behaviour rather than to increase safety.** §5.25's rule is that a new default applies only to fields *absent* from the stored config — so every `copier_config.json` on disk today lands on this value. A safety feature that silently stops a working copier at the next restart is one that gets switched off. **Moving it to `shadow` is a protection increase and the operator's call.** |

Recognised values, and nothing else acts:

| Value | Behaviour |
|---|---|
| `live` | today's behaviour: an enabled, armed relationship places real orders |
| `shadow` | logs the fully-formed order it *would* have sent (`COPY_BLOCKED_COPIER_SHADOW`, with instrument, action and quantity) and submits nothing |
| `disabled` | copier off, under its own event name so the two intentions stay distinguishable in a log that is grepped by event type |
| anything else | **does not trade.** `P1-87`'s rule: the permissive branch here places real orders, so a typo must not be the difference between observing and trading |

Entering `live` runs `RunCopierPreflight` and is **refused** if a follower does not resolve.
Leaving `live` is never gated — a gate on the safe direction is one an operator routes around.
Readable and settable over `GET`/`POST /api/copier/config` (`copierMode`, `action=set_mode`) and
`nt_copier_config`.

### 3.1 Copier — per relationship and per group

| Field | Default | Why |
|---|---|---|
| `ArmedForLive` | `false` | R1. Non-negotiable. |
| `IsEnabled` | `true` | A relationship you just created, you want on. Harmless while disarmed. |
| `QuantityRatio` | `1.0` | A mirror is the least surprising thing a copier can do. |
| `SizingMode` | `QuantityRatio` | Same reason. Notional-based sizing is a deliberate choice, not a default. |
| `AutoSymbolConversion` | `true` | Leader on NQ, follower on MNQ is the common prop setup. |
| `MaxPositionSize` | ~~`100`~~ **`10`** | R4 — agree with the guard's per-account cap. 100 MNQ is ~$4.5M notional; it is not a cap, it is the absence of one. |
| `MaxSlippageTicks` | `0.0` (off) | **Deliberately off, and this is not an oversight.** A wrong threshold quarantines a *healthy* relationship mid-session, and a quarantine that blocks an entry is survivable while one that delays your read on an exit is not. When you do set it: normal copy slippage on MNQ/MES is 0–2 ticks, so **8** catches genuinely bad routing without firing on noise. |
| ~~`StealthMode`~~ | **DELETED** (`P1-83`) | See §4. Read by no logic — and the NT8 window *displays* "Stealth: ON". |
| ~~`DailyLossLimit`~~ | **DELETED** (`P1-83`) | See §4. Read by nothing at all. |
| ~~`Mode`~~ (`CopierExecutionMode`) | **DELETED** (`P1-83`) | See §4. The enum is declared, persisted, settable, and branched on nowhere. |
| `LeaderAccountName` | ~~`"Sim101"`~~ **`""`, and no fallback** (`P1-85`) | A request that omits the account is currently routed to a *guessed* account. That is how you copy to the wrong one. Refuse instead. |
| `FollowerAccountName` | ~~`"SimCopy2"`~~ **`""`, and no fallback** (`P1-85`) | Same. |

### 3.2 Guard — `RiskConfig`

| Field | Default | Why |
|---|---|---|
| `Mode` | `"shadow"` | R1. |
| `MinShadowSessions` | ~~`0`~~ **`5`** | A soft gate on arming, currently disabled. You should not be able to point this at live money until it has watched you trade several sessions without wanting to intervene wrongly. Five sessions is a week. |
| `Sizing.MaxContractsPerAccount` | `10` | Generous for a micro-futures prop account without being absurd. |
| `Sizing.MaxContractsAggregate` | `20` | Two accounts at full size. Binds before the per-account cap on a 3-way mirror, which is the correct order. |
| `Overtrading.MaxTradesPerSession` | `8` | Overtrading is the most common way an evaluation dies — not one big loss, but eleven small ones. Erring low is correct here. |
| `Overtrading.MaxConsecutiveLosses` | `3` → 60 min lockout | Standard tilt protection. Three in a row is a bad read, not bad luck. |
| `Overtrading.CooldownMinutes` | `5` | Enough to break the re-entry reflex. |
| `Overtrading.MaxOrdersPerSecond` | `5` | A runaway-loop guard, not a trading rule. |
| `StopGuard.OnMissing` | `"Flatten"` | **The most important default in the file, and it is right.** The alternative (`AutoStop`) invents a stop at a guessed offset, which can be worse than being flat. Flat is always a known quantity. |
| `StopGuard.StopAttachSeconds` | ~~`3`~~ **`15`** | R5. Long enough to place a stop by hand; short enough that an unstopped position does not survive a spike. |
| `StopGuard.MaxAutoStopAttempts` | `2` | Two failures means the route is broken, not busy. |
| `StopGuard.Offsets` | NQ/MNQ 40t (10 pts), ES/MES 16t (4 pts), default 30t | These are **emergency backstops, not strategy stops** — the distance at which "no stop at all" becomes worse than a bad stop. 10 points on NQ against 4 on ES is roughly volatility-proportionate. |
| `PnLRules.DailyLossLimit` | `1000.0` | R3 — must come from the firm. See §4. |
| `PnLRules.TrailingDrawdown` | `1500.0` | R3. |
| `EnableWindowGate` | `false` | A gate that refuses to let you trade outside fixed hours is extremely intrusive and wrong for a discretionary trader. Off is right. |
| `FirmMirror.Enabled` | `false` + empty `AccountFirmMap` | Not a default to tune — this is `F-9`, the missing mechanism behind R3. |
| `LockoutBypassWhileDisarmedAccounts` | empty | Empty means lockouts persist for **all** accounts even when disarmed. Correct for prop accounts: a lockout you can escape by disarming is not a lockout. |

### 3.3 Prop-firm suite — `PropFirmProtectionConfig`

| Field | Default | Why |
|---|---|---|
| `ArmedForLive` | `false` | R1 — though `P1-81` means nothing reads it, so it is currently decoration. |
| `EnableNewsShield` | ~~`true`~~ **`false`** | **R2.** `INERT` (`P2-25`). |
| `NewsBufferMinutesBefore/After` | `2` / `2` **→ 5 / 15** when the shield works | Two minutes is too short to be useful. NFP and CPI move price for five to fifteen minutes after the release, and the dangerous part is the *reversal*, not the spike. |
| `EnableProfitTargetLock` | `true` | Evaluated and real. Locking after the target is hit is exactly right for an evaluation — the account has already done its job. |
| `EvaluationTargetProfit` | `3000.0` | R3 — correct for a $50k Apex evaluation, wrong elsewhere. Must come from the firm profile. |
| `EnablePeakEquityProtection` | `true` | Evaluated and real, and genuinely good: it stops a winner round-tripping. |
| `MaxPeakGivebackPct` | `0.30` | Give back at most 30% of an open peak. Tight enough to protect the trade, loose enough to survive normal noise. |
| `MinPeakGainDollars` | `50.0` | `P1-40`. Without a floor, a one-tick peak makes any retrace a 100% giveback and flattens you seconds after entry. |
| `EnableConsistencyCap` | ~~`true`~~ **`false`** | **R2.** `CONFIGURED-not-EVALUATED` (`P1-77`). |
| `MaxDailyProfitPctOfTarget` | `0.35` | A real firm rule (most sit between 30% and 50%), and a sane number — *if it were implemented*. |
| ~~`EnableAutoDayFiller`~~ | **DELETED** (`P1-83`) | Was read by nothing. |

---

## 4. Fields that are not defaults — they are dead

Found 2026-08-13 while writing this document, by asking what actually reads each field rather than
what each field is set to. All three are on the copier, all three are persisted to
`copier_config.json`, and all three are settable from the NT8 window.

**`StealthMode` (defaults `true`).** Read by no logic anywhere. It is, however, *displayed* — the
copier window renders `Stealth: ON` in both the relationship and the group status lines. This is
the worst form of this defect in the repo so far: `P1-77` and `P1-81` are silent, but this one has
a UI actively asserting that a protection is on. **Delete the field and the two display fragments.**

**`DailyLossLimit` (defaults `1000.0`).** Read by nothing, displayed by nothing. It appears only in
the two clone paths and the field-name list. It sits in the config file next to the guard's *real*
`PnLRules.DailyLossLimit`, which is exactly the R4 confusion — two identically named limits, one of
which does nothing. **Delete.**

**`Mode` / `CopierExecutionMode` (defaults `Executions`).** The enum is declared, carried on both
DTOs, serialized (`"Mode": 0`), and settable — and no code branches on it. It is the most
consequential-sounding of the three: "copy on execution" versus "copy on order" is a genuine
copier design decision, and the config implies the choice is yours. It is not. **Delete the enum
and the field**, or implement it — but it must not stay as it is.

All three are `P1-77`'s exact shape. The pattern that finds them is the one this repo already
trusts: **ask what reads a field, not what sets it.**

### 4a. Applied as `P1-83`, with a gate so the fourth one cannot get in

All four are deleted — the three above plus `PropFirm.EnableAutoDayFiller`. `StealthMode` turned
out to have **four** surfaces asserting it, not two: both window status lines, a "Stealth Tagging"
checkbox on both Add forms, "Stealth Order Tagging" in the window title, and a `stealth` flag on
the browser page in `nt8-mcp-bridge`. All gone.

What makes this more than four deletions is the gate, and it is mechanical. It walks both copier
DTOs by reflection and counts real uses in **the engine**, discounting the three things that make
a dead field look alive: its own declaration, `X = something.X` clone and serializer lines, and
the field-name string list. Run against the pre-fix tree it named exactly these three, with no
false positives.

⚠️ **Scoping it to the engine is the design, not a shortcut.** Widen the scan to include the
window and `StealthMode` scores as READ — because the window printed `Stealth: ON` for it. That is
the defect told louder, not an absolution from it. The engine is where copying decisions are made,
so a field the engine never consults cannot change behaviour whatever a surface renders.

And it is honest about its limit: it is a source-text check, so it **cannot** catch `P2-25`'s
class — a field genuinely read, by a branch that can never be reached. The guard side needed a
runtime registry for that, and the copier side would too. What this catches is the cheaper and far
more common defect: the field nothing reads at all.

**Two things worth knowing before deleting a dead field here.**

1. **The dead fields were load-bearing in the tests.** Ten merge-preservation probes used them —
   *"a field the request never mentions survives the merge"* — chosen precisely *because* nothing
   read them. They now probe live fields, which is a better test: `IsQuarantined` is a field the
   Add form genuinely cannot show.
2. **The agent-loop cannot do this kind of change.** Deleting a symbol that a *protected* test
   file references fails the loop's compile gate: the patch is correct and the build breaks
   anyway, on a file the loop is not allowed to touch. Every other change in this document went
   through the loop; this one had to be done by hand.

---

## 5. What "at defaults" means operationally

Verified on the live box 2026-08-13 after this document was written:

* Both copier relationships (`Sim101 → Sim-ORB`, `Sim101 → SimCopy2`) reset to the code defaults —
  enabled, **disarmed**, ratio 1.0, `MaxPositionSize` 100, auto symbol conversion on, no per-ticker
  ratios, no custom symbol maps, `MaxSlippageTicks` 0, not quarantined.
* No groups. No config conflicts (`DetectConfigConflicts` returns empty).
* Guard `Mode = shadow`. Inventory reports 5 rules `CONFIGURED-not-EVALUATED`, 3 `INERT`,
  13 `EvaluatedNotEnforcing`, 4 `Disabled` — and **zero `Enforcing`**, which is what shadow mode
  should look like.
* `prop_limits.json` does not exist. That is the correct state: the first write creates it, and
  `P1-75` is a reminder that reading it used to disarm the rules it described.

---

## 6. An open gap this exercise exposed

While reconstructing how the two relationships came to be disabled, the audit record answered
**what changed** and could not answer **who changed it**.

`interventions.jsonl` records every copier write with its exact payload and timestamp — that part
works, and it is how the timeline was reconstructed at all. What no record carries is a client
identity. There is one shared bearer token, and the bridge does not log a source. So a config
change made by the browser page, by an MCP tool, by `curl`, or by another machine on the network is
**indistinguishable after the fact**.

Two writes at `04:47:43` and `04:47:52` on 2026-08-13, one per relationship, could not be
attributed to any action taken in that session. They may well have been mine. The point is that the
system cannot say, and for a system whose entire purpose is that configuration must not lie, "the
protection was switched off and nobody can tell you by whom" is a gap worth closing before this
guards a funded account.

Not filed as a defect ID yet — it needs a decision about what identity even means here (a
per-client token? a source header the page sets?) before it can be specified.

---

## 7. What applying this document found

Every delta above is applied. Five defects were opened along the way, and **four of the five were
found by applying the fix rather than by writing it** — which is the point worth keeping.

**`P1-82` (R2) — closed.** Four literals, not two: each default is stated once as a property
initializer and once as the parser's final fallback, and the parser copy is what runs for every
config file that predates the field. Fixing only the property would have been green in the suite
and unchanged in production.

**`P1-86` — closed, and opened by `P1-82` itself.** Defaulting the news shield off made the
inventory report it `Disabled` instead of `INERT`. See §2/R2: the hardening plan predicted this in
writing and was half right. The evaluator now asks whether it *can* fire before it asks whether it
is switched on.

**`P1-83` (§4) — closed.** Four dead fields deleted, and the gate that finds the fifth built. See
§4a.

**`P1-84` (R4/R5) — closed.** Three numbers. The tests are worth more than the numbers: an
inequality between two files rather than a pinned cap, a deadline floor conditional on the
consequence, and a value checked together with the source line that makes it a defect.

**`P1-87` — closed, and found by a mutant SURVIVING.** Changing `StopGuard.OnMissing` from
`"Flatten"` to `"AutoStop"` broke nothing across 1180 green tests. Nothing pinned the guard's most
consequential default — and asking why led to the dispatch, which compares against two exact
string literals with no `else`. A lower-case `"flatten"`, a typo, an empty string, or the
`"WarnOnly"` the declaration itself advertised matched nothing, so the guard emitted **no action
at all**: a position with no stop, past its grace period, and it simply returned. `RunPreflight`
refuses an unrecognised guard *mode* and had never looked at this.

### The one thing to take from this

**Four of the five came from evidence, not from reading code.** Two came from mutation batteries
(`P1-87`, and the blank-versus-missing hole in `P1-85`), one from applying a fix and checking what
it did to the inventory (`P1-86`), one from the review panel (`P1-85`'s edit path). Only `P1-83`
came from reading — and only because the question being asked was *"what reads this field?"*
rather than *"what does this field do?"*.

`mutation/check_anchors.py` was written during this work and immediately found two stale anchors,
then nine more after the `P1-83` deletion. A battery whose find-string stops matching prints
`[SKIP]` and scores that mutant a **survivor**, but only when the battery is run — and a battery
only runs when the suite is green. Eleven mutants across five batteries were silently proving
nothing. It runs first in CI now, costs a second, and works while the suite is red, which is
exactly when a battery cannot tell you anything.

### Still open, and named rather than left to be discovered

* **`F-9`** — the firm mapping behind R3. Every dollar default is still a guess for one unstated
  account size, and that is the largest remaining item in this document.
* **§6's attribution gap** — the audit record answers *what changed* and cannot answer *who*.
* **A copier field registry.** §4a's gate is a source scan and says so. The guard side has a
  runtime registry that catches `INERT`; the copier side does not, so a copier field that is read
  by a branch which can never fire would still get through.
