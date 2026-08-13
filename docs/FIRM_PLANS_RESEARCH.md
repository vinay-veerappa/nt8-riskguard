# Firm plans — researched 2026-08-13

**Purpose**: to populate `FirmMirror.FirmProfiles` with numbers that came from the firms' published
rules rather than from a guess. This is `CONFIG_DEFAULTS` **R3**: *a dollar limit is derived from the
account, never guessed.*

⚠️ **CONFIDENCE, STATED UP FRONT.** These figures come from third-party rule-aggregator sites, dated
2026, not from the firms' own documentation — Tradeify's own help centre returned HTTP 403 and Apex's
returned 403 too. Every number below was seen on at least one 2026-dated source, and where a second
source corroborated it that is noted. **Prop-firm rules change without notice**, several of these
firms changed plans during 2026 (Lucid added `LucidDaily` in July 2026 and made its DLL a paid add-on
in August 2026), and **the operator has not yet confirmed any of it.** Treat this as a research
starting point that needs one pass of human correction before it becomes risk configuration.

**Sources** are listed at the bottom.

---

## 1. The headline: both plans currently deployed are WRONG

`F-9` mapped five Sim accounts to two plans built from the four profiles recovered from a 2026-08-07
config backup (`CONFIG_DEFAULTS` R3a). Those recovered profiles carried **no account size**, and the
size I inferred for each was wrong. Now that the real tables exist, here is what they actually were:

| Recovered profile | What its numbers actually match | Deployed on this box as | Wrong how |
|---|---|---|---|
| `TakeProfitTrader` — `eod`, 1500 / buf 200, DailyLoss **off** | TPT **25K** (its max loss is $1,500) | `TakeProfitTrader-50K` | **Amount** should be **2000** for a 50K. And a **PRO** account trails **INTRADAY**, not `eod` |
| `Apex` — `eod`, 2000 / buf 200, DailyLoss `include_unrealized_peak` 1000 / buf 100 | Apex **50K EOD** *exactly* ($2,000 DD, $1,000 DLL) | `Apex-100K` | Should be **3000 / 1500** for a 100K EOD |
| `Tradeify` — `eod`, 2000 / buf 200, lock 100, DailyLoss 1250 / buf 100 | Tradeify **50K** — $2,000 DD and $1,250 DLL match Growth-50K and Lightning-50K exactly | not deployed | correctly sized, wrongly *labelled* (it was keyed only by firm) |
| `Lucid` — `eod`, 2500 / buf 200, DailyLoss 2500 / buf 200 | ⚠️ **matches no current Lucid plan at any size** (50K→2000, 100K→3000, 150K→4500) | not deployed | unknown provenance; do not reuse |

⚠️ **The `eod`-vs-`intraday` error is the dangerous one, and it is not a "tighter is safer" case.**
An EOD trail recalculates the threshold once at the close. An intraday trail follows the *peak
equity including open unrealized profit*, so during a session in which you are up, the firm's floor
rises **immediately** while an EOD model's floor stays stale and **lower**. Modelling an intraday
account as EOD therefore puts the guard's floor *below* the firm's: **the firm fails you before the
guard speaks.** That is R3's stated failure mode. `TAKEPROFITPRO524207503` is a **PRO** account, so
this is the mode it would have been protected under had it been mapped.

⚠️ The two amount errors both err **tighter** than the firm (1500 < 2000, 2000 < 3000), which is the
safe direction — the guard acts first — but they will flatten the mapped Sim accounts earlier than the
firm would, which is its own cost: `CONFIG_DEFAULTS` R5 is that a limit which fires on a normal day
trains you to switch the system off.

---

## 2. The structural finding: firm + size is NOT a plan

`F-9` keyed `FirmProfiles` by **firm + size** (`Apex-100K`) because one dollar amount cannot serve a
50K and a 100K. The research says that was necessary and **not sufficient**. Every one of the four
firms sells **multiple rule sets at the same account size**:

| Firm | Variants at one size | Worst case |
|---|---|---|
| **Apex** | EOD (has a DLL) vs Intraday (no DLL, trail **locks** at start + $100 on PA) | same size, one has a daily loss limit and one does not |
| **TPT** | Test (EOD) / **PRO (INTRADAY)** / PRO+ (EOD) | same size, opposite drawdown *type* |
| **Tradeify** | Growth / Select / Select Daily / Select Flex / Lightning | **100K max loss is 3500, 3000, 2500, 3000 or 4000** depending on family |
| **Lucid** | Pro / Flex / Daily / Direct | 100K DLL is 1800, none, 1800-if-purchased, or 2100 |

So the key must be **firm + plan + size**, e.g. `Apex-100K-EOD`, `TPT-50K-PRO`,
`Tradeify-100K-Lightning`, `Lucid-100K-Flex`. This costs no code — the key is an opaque string — but
it changes what has to be *known* about an account before it can be mapped, which is the thing only
the operator can supply.

---

## 3. Apex Trader Funding

Two drawdown products at every size. Profit target is 6% of the starting balance.

### EOD trailing (threshold recalculated at 4:59:59 PM ET, then enforced intraday next session)

| Size | Max drawdown | Profit target | Daily loss limit | Max contracts (eval / PA) |
|---|---|---|---|---|
| 25K | $1,000 | $1,500 | **$500** | 4 / 2 |
| 50K | $2,000 | $3,000 | **$1,000** | 6 / 4 |
| 100K | $3,000 | $6,000 | **$1,500** | 8 / 6 |
| 150K | $4,000 | $9,000 | **$2,000** | 12 / 10 |

### Intraday trailing (follows peak equity **including unrealized**, in real time)

| Size | Max drawdown | Profit target | Daily loss limit | Trail stops? |
|---|---|---|---|---|
| 25K | $1,000 | $1,500 | none | PA only: locks at start + $100 |
| 50K | $2,000 | $3,000 | none | PA only: locks at start + $100 |
| 100K | $3,000 | $6,000 | none | PA only: locks at start + $100 |
| 150K | $4,000 | $9,000 | none | PA only: locks at start + $100 |

**Maps onto `FirmProfile` as:**

* EOD: `TrailingDD { Type = "eod", IncludesUnrealized = false, Amount = <size row> }`,
  `DailyLoss { Enabled = true, Amount = <size row> }`
* Intraday: `TrailingDD { Type = "intraday", IncludesUnrealized = true, Amount = <size row> }`,
  `DailyLoss { Enabled = false }`
* The PA trail-lock is **exactly what `LockAtProfit` is for**. This codebase locks when
  `FirmTrailingPeak >= FirmStartingBalance + LockAtProfit`, and Apex locks when the *threshold*
  reaches start + $100, i.e. when `peak - Amount >= start + 100`. So
  **`LockAtProfit = Amount + 100`** — e.g. **3100** on a 100K. ⚠️ The recovered profile had
  `LockAtProfit = 0`, which means the guard would have kept trailing after the firm stopped: the guard
  would flatten on a drawdown the firm no longer counts.

⚠️ `PAAPEX*` accounts are Performance Accounts (funded); `APEX*` are evaluations. The trail-lock
applies to **PA only**, so those two prefixes need *different* profiles even at the same size.

---

## 4. Take Profit Trader

**No daily loss limit at any size or stage** — removed January 2025. The drawdown is the only control.

| Size | Max loss (all stages) | Test profit target | Test | **PRO** | PRO+ |
|---|---|---|---|---|---|
| 25K | $1,500 | $1,500 | EOD | **intraday** | EOD |
| 50K | **$2,000** | $3,000 | EOD | **intraday** | EOD |
| 75K | $2,500 | $4,500 | EOD | **intraday** | EOD |
| 100K | $3,500 | $6,000 | EOD | **intraday** | EOD |
| 150K | $4,500 | $9,000 | EOD | **intraday** | EOD |

**Maps onto `FirmProfile` as:** `DailyLoss { Enabled = false }` for every plan — which is what the
recovered profile had, and it is right, and `F-9`'s inventory already reports it honestly (*"plan
'TakeProfitTrader-50K' has NO daily loss limit, which is that firm's actual rule -- not an
oversight"*). `TrailingDD.Type` is `"intraday"` with `IncludesUnrealized = true` on **PRO**, and
`"eod"` on Test and PRO+.

⚠️ **This is the single biggest correction in this document.** The live account
`TAKEPROFITPRO524207503` is a **50K PRO**: max loss **$2,000**, **intraday** trailing, no DLL. The
deployed profile says $1,500 EOD. Sources describe the Test→PRO switch to intraday trailing as *"the
single biggest rule change between stages and the most common reason traders blow funded accounts in
the first week"*.

---

## 5. Tradeify

Five plan families × four sizes. **All funded accounts use EOD trailing.** Consistency rules exist on
most families and this guard **cannot express them** (see §7).

| Plan | 25K | 50K | 100K | 150K |
|---|---|---|---|---|
| **Growth** (eval + funded) | 1000 / DLL 600 | 2000 / DLL **1250** | 3500 / DLL 2500 | 5000 / DLL 3750 |
| **Select** (eval) | 1000 / no DLL | 2000 / no DLL | 3000 / no DLL | 4500 / no DLL |
| **Select Daily** | 1000 / DLL 500 | 2000 / DLL 1000 | 2500 / DLL 1250 | 3500 / DLL 1750 |
| **Select Flex** | 1000 / no DLL | 2000 / no DLL | 3000 / no DLL | 4500 / no DLL |
| **Lightning** (instant funding) | 1000 / no DLL | 2000 / DLL 1250 | **4000** / DLL 2500 | 5250 / DLL 3000 |

*(format: max loss / daily loss limit. Growth consistency 35%, Select 40%, Lightning 20/25/30% by
payout cycle. Select Daily's DLL is a **soft** breach.)*

⚠️ **Note the 100K column: 2500, 3000, 3500 or 4000 depending on family.** A `Tradeify-100K` key
would be meaningless.

**On the account-name pattern.** Session 33 observed that Tradeify account numbers appear to embed the
size — `TDYG50…` ×5 and `TDYG100…` ×1 on this box — and deliberately did not act on it. The research
supports the *reading* (Tradeify sizes are 25/50/100/150, and `TDYG`/`TDFYG`/`FTDFYG` plausibly encode
family: Growth / Funded-Growth / something-Funded). ⚠️ **It still must not be used to write risk
config**: it identifies the SIZE at best, and §2 shows the size alone does not determine the numbers.
It is worth confirming as a labelling convenience, not as a source of limits.

---

## 6. Lucid Trading

All plans **EOD trailing** except **LucidDaily funded, which is always intraday** regardless of what
was chosen at evaluation.

| Plan | 25K | 50K | 100K | 150K | Notes |
|---|---|---|---|---|---|
| **LucidPro** | 1000 / no DLL | 2000 / DLL 1200 | 3000 / DLL 1800 | 4500 / DLL 2700 | DLL is a **soft** breach; 40% consistency |
| **LucidFlex** | 1000 / none | 2000 / none | 3000 / none | 4500 / none | **no DLL anywhere**, eval or funded |
| **LucidDaily** | 1000 / 600* | 2000 / 1200* | 3000 / 1800* | 4500 / 2700* | *DLL only if purchased; **funded drawdown always intraday** |
| **LucidDirect** | 1000 / none | 2000 / DLL 1200 | 3000 / DLL 2100 | 4500 / DLL 3000 | funded from day one; 20% consistency |

*(format: max loss / daily loss limit.)*

**Two mechanisms this guard partly has and partly does not:**

* **Initial Trail Balance = start + max loss + $100** (Pro and Direct only). That is the point at
  which the trail stops mattering in the same way, and it is `LockAtProfit`'s semantics again:
  **`LockAtProfit = Amount + 100`**.
* ⚠️ **LucidScale DLL**: once the balance closes above the Initial Trail Balance, the *fixed* DLL is
  replaced by **60% of the highest end-of-day profit**, ratcheting up and never down. **This guard
  cannot express a DLL that is a percentage of a high-water mark** — `FirmDailyLossConfig` has a flat
  `Amount`. A Lucid Pro/Direct account past its Initial Trail Balance is therefore protected against
  the wrong number, and the mismatch grows as the account grows. Named in §7 rather than papered over.

⚠️ The recovered `Lucid` profile (2500 / 2500) matches **no** Lucid plan at any size. Its provenance
is unknown and it should not be reused.

---

## 7. What the guard cannot currently express

Written down because a profile that silently omits a firm rule is `CONFIGURED`-not-`EVALUATED` wearing
a firm's name.

| Firm rule | Guard support | Consequence |
|---|---|---|
| **Consistency / max-day-as-%-of-profit** (all four firms) | `PropFirm.EnableConsistencyCap` exists and **nothing reads it** (`P1-77`, still open) | the rule most likely to void a payout is unprotected, and the inventory already says so in red |
| **LucidScale DLL** = 60% of highest EOD profit, ratcheting | none — `DailyLoss.Amount` is a flat dollar figure | a grown Lucid account is measured against a stale limit |
| **Apex / Lucid trail-lock** at start + max loss + $100 | ✅ `TrailingDD.LockAtProfit`, if set to `Amount + 100` | recovered profiles had `0`, so the guard kept trailing after the firm stopped |
| **Soft vs hard DLL breach** (Lucid, Tradeify Select Daily) | none — a breach is a breach | the guard flattens and locks out where the firm would only stop the session. ⚠️ Interacts with `P2-92`: a soft-breach DLL modelled as hard is precisely a rule that halts a bot for a condition the firm tolerates |
| **Max contracts per plan** (Apex: 4–12 by size and eval/PA) | ✅ `Sizing.MaxContractsPerAccount`, but it is **global**, not per account | one number for a fleet holding 25K and 150K accounts |
| **Payout / minimum-trading-day gates** | none, and out of scope — not a risk limit |

---

## 8. What is needed from the operator before any of this is deployed

The research supplies the numbers **per plan**. It cannot supply which plan each account is on, and
§2 shows that is exactly what determines the numbers.

1. **Which plan is `TAKEPROFITPRO524207503`?** Assumed 50K PRO from its name and its $50,357 balance →
   $2,000, intraday, no DLL. Confirm before mapping it, because it holds real money.
2. **Are the `APEX*` accounts EOD or Intraday, and are `PAAPEX*` the funded ones?** They differ in
   whether a DLL exists at all.
3. **Which Tradeify family do `TDYG*` / `TDFYG*` / `FTDFYG*` correspond to**, and does the number
   after the prefix really encode the size?
4. **Which Lucid plan are the `LFE*` accounts?** `LFE` reads like *Lucid Funded Evaluation*, and the
   plan decides whether there is a DLL at all.
5. **Confirm the `DailyLoss.Basis` for each firm.** This codebase offers `"realized"` and
   `"include_unrealized_peak"`. The recovered Apex and Tradeify profiles used
   `include_unrealized_peak`; the firms' documentation as read here does not state the basis
   explicitly, and it is the difference between a DLL that fires on an open position and one that does
   not.

Until each is answered, the honest configuration is the one `F-9` already reports: **unmapped, with
the firm rules reading `Disabled` rather than protecting against a guessed number.**

---

## Sources

All retrieved 2026-08-13.

- [Apex Trader Funding Review (Rules, Payouts, New Accounts 2026) — Damn Prop Firms](https://damnpropfirms.com/futures-prop-firms/apex-trader-funding/)
- [Apex Trader Funding Rules 2026 — QuantCrawler](https://quantcrawler.com/learn/apex-trader-funding-rules)
- [Apex Trader Funding Review 2026: Rules, Payouts & Cost — Velotrade](https://velotrade.com/blog/apex-trader-funding-review)
- [Take Profit Trader Rules 2026: Test, PRO, PRO+ — Tradecovex](https://tradecovex.com/guides/take-profit-trader-rules-2026)
- [What Is the TakeProfit Trader Daily Loss Limit? — QuantVPS](https://www.quantvps.com/blog/takeprofit-trader-daily-loss-limit)
- [TakeProfitTrader Accounts: Test, PRO, PRO+ Explained 2026 — Prop Trading Vibes](https://proptradingvibes.com/blog/takeprofittrader-accounts-overview)
- [Tradeify Rules 2026: Growth, Select & Lightning Accounts — TradeTanto](https://tradetanto.com/learn/tradeify-rules-explained-what-every-trader-should-know)
- [Tradeify Rules 2026: Drawdown, DLL & Consistency — Prop Trading Vibes](https://proptradingvibes.com/blog/tradeify-trading-rules-overview)
- [Lightning Funded Accounts — Tradeify Help Center](https://help.tradeify.co/en/articles/10495938-lightning-funded-accounts) *(403 to automated fetch)*
- [Lucid Trading Rules & Payouts (2026) — Damn Prop Firms](https://damnpropfirms.com/prop-firms/lucid-trading-rules-payouts/)
- [Lucid Trading Rules 2026 | LucidPro Drawdown and Evaluation Guide — QuantCrawler](https://quantcrawler.com/learn/lucid-trading-rules)
