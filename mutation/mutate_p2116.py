"""Mutation battery for P2-116 (an equity rule with NO equity reading).

The defect: evidence for the equity-backed rules counted the existence of an `AccountState`
OBJECT, which every subscribed account has. So 89 Provider31 accounts all reported
`EvaluatedNotEnforcing` -- the state that means "this rule ran and you are within it" -- while
exactly ONE of them reported any equity at all. The funded account and 88 dormant evals were
byte-identical on every row but the number, on the one surface built to answer "is the guard
actually protecting me".

⚠️ THIS ONE IS DIFFERENT FROM THE OTHER BATTERIES HERE: the acceptance tests were written BY
HAND FIRST and were RED at a measured 1931/5 baseline. So unlike a suite written against an
implementation, these assertions are already known to be capable of failing. This battery
therefore aims almost entirely at the WRONG FIXES rather than at the absence of a fix -- the
directions where the ticket is easy to get backwards:

  * 1-3 attack the reading predicate itself. Mutant 1 is the tempting one-character version,
    `> 0`, which switches the rule to INERT for an account whose equity has gone NEGATIVE --
    the account most likely to be in trouble. That is a WORSE defect than the one being fixed.
  * 4-6 restore the original object-counting evidence at each of the three sites. A fix applied
    at one reader and not the others is this codebase's single most repeated defect (P1-100,
    P2-98/P1-99, P1-105), so each site gets its own mutant rather than trusting one.
  * 7-9 attack the REPORTING half. A row that goes INERT without saying why makes the next
    reader re-derive the whole investigation (P2-113), and a `cur=0.0` is a number the operator
    reads as a fact about the account.
  * 10 widens the fix to the realized-PnL rules, which is the same defect in the PESSIMISTIC
    direction: a flat, funded, actively watched account reported as INERT on its daily loss
    limit teaches the operator to ignore INERT rows.
  * 11 removes the EvidenceLabel, which is what the UI renders as the noun in the red row.
  * 12 attacks DeriveState itself, the shared predicate all four states hang off.

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

# No `import _battery` here on purpose -- see the exit at the foot of the file.

# P2-114: a non-ASCII character in a mutant DESCRIPTION raises UnicodeEncodeError inside
# print() on a cp1252 console -- BETWEEN applying a mutant and restoring it, which leaves a
# live mutant in the source tree.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')

# (file, description, find, replace)
MUTANTS = [
    # ---- 1. THE TEMPTING WRONG FIX ----
    (RULES,
     "HasEquityReading uses `> 0` instead of `!= 0`, so an account whose equity has gone "
     "NEGATIVE reports INERT -- the rule switches off at the moment it matters most",
     '            return account != null && !double.IsNaN(account.AccountEquity) && account.AccountEquity != 0.0;',
     '            return account != null && !double.IsNaN(account.AccountEquity) && account.AccountEquity > 0.0;'),

    # ---- 2. THE DEFECT VERBATIM ----
    (RULES,
     "HasEquityReading answers the OLD question -- does an AccountState object exist -- which "
     "is the defect this ticket exists to fix, restored inside the predicate meant to fix it",
     '            return account != null && !double.IsNaN(account.AccountEquity) && account.AccountEquity != 0.0;',
     '            return account != null;'),

    # ---- 3. the NaN guard ----
    # NaN != 0.0 is TRUE, so without this guard a NaN scores as evidence and every comparison
    # the enforcer then makes against it is false: Enforcing, and incapable of firing.
    (RULES,
     "the NaN guard is dropped; NaN != 0.0 is TRUE, so a NaN equity counts as a reading and "
     "the rule reports Enforcing while being unable to fire",
     '            return account != null && !double.IsNaN(account.AccountEquity) && account.AccountEquity != 0.0;',
     '            return account != null && account.AccountEquity != 0.0;'),

    # ---- 4. site one: trailing drawdown ----
    (RULES,
     "the trailing-drawdown rule counts the account object again, which is the measured defect "
     "on all 89 accounts",
     '                        c.Config.PnLRules.TrailingDrawdown, HasEquityReading(c.Account) ? 1 : 0,',
     '                        c.Config.PnLRules.TrailingDrawdown, c.Account == null ? 0 : 1,'),

    # ---- 5. site two: the firm trailing drawdown ----
    (RULES,
     "the FIRM trailing drawdown goes back to counting the mapping alone, so a dormant eval "
     "that IS mapped to a firm reads as protected -- the second reader, unfixed",
     '                        sub.Amount, mapped && HasEquityReading(c.Account) ? 1 : 0, note);',
     '                        sub.Amount, mapped ? 1 : 0, note);'),

    # ---- 6. site three: peak equity giveback ----
    (RULES,
     "peak equity giveback goes back to counting the account object -- the third reader, and "
     "the one that looks unlike the others because it displays no value at all",
     '                    : R(null, c.PropConfig.MaxPeakGivebackPct, HasEquityReading(c.Account) ? 1 : 0,',
     '                    : R(null, c.PropConfig.MaxPeakGivebackPct, c.Account == null ? 0 : 1,'),

    # ---- 7. the note disappears ----
    (RULES,
     "the inert trailing-drawdown row stops saying WHY it is inert, so the operator gets a red "
     "row with no noun in it and re-derives the whole investigation (P2-113)",
     '                        HasEquityReading(c.Account) ? null : NoEquityReading)',
     '                        null)'),

    # ---- 8. the firm note is REPLACED rather than prefixed ----
    # The existing note is the only place that says whether the plan's numbers or the fallback
    # block's are in force. Trading one missing fact for another is not a fix.
    (RULES,
     "the firm note is replaced instead of prefixed, losing the only text that says whether the "
     "plan or the fallback block supplies the numbers in force",
     '                        note = NoEquityReading + "; " + note;',
     '                        note = NoEquityReading;'),

    # ---- 9. cur=0.0 comes back ----
    (RULES,
     "an unread account reports CurrentValue 0.0 instead of null, so the row renders a NUMBER "
     "the operator reads as a fact about the account",
     '                    : R(HasEquityReading(c.Account) ? (double?)c.Account.AccountEquity : null,\n                        c.Config.PnLRules.TrailingDrawdown, HasEquityReading(c.Account) ? 1 : 0,',
     '                    : R(c.Account == null ? (double?)null : c.Account.AccountEquity,\n                        c.Config.PnLRules.TrailingDrawdown, HasEquityReading(c.Account) ? 1 : 0,'),

    # ---- 10. THE OPPOSITE ERROR: widening the fix ----
    # A flat, funded, actively watched account reported INERT on its daily loss limit is F-9 in
    # the pessimistic direction, and an operator who learns to ignore INERT rows has lost the
    # signal the registry exists to give them.
    (RULES,
     "the fix is widened to the daily loss limit, whose evidence is REALIZED PnL -- a flat "
     "funded account now reports INERT on the rule that is actually watching it",
     '                        -Math.Abs(c.Config.PnLRules.DailyLossLimit), c.Account == null ? 0 : 1)',
     '                        -Math.Abs(c.Config.PnLRules.DailyLossLimit), HasEquityReading(c.Account) ? 1 : 0)'),

    # ---- 11. the label, which is the noun in the row ----
    (RULES,
     "the trailing-drawdown EvidenceLabel is removed, so a rule that CAN go inert no longer "
     "says what its evidence is -- and the sweep that classifies labelled rules exempts it",
     '                Name = "Trailing drawdown", ConfigPath = "PnLRules.TrailingDrawdown",\n                EvidenceLabel = "accounts reporting an equity reading",',
     '                Name = "Trailing drawdown", ConfigPath = "PnLRules.TrailingDrawdown",'),

    # ---- 12. the shared predicate every state hangs off ----
    (RULES,
     "DeriveState stops mapping zero evidence to INERT, which silently undoes this ticket and "
     "P2-25 together at the one place all four states are decided",
     '            if (reading.EvidenceCount <= 0) return GuardRuleState.Inert;',
     '            if (reading.EvidenceCount < 0) return GuardRuleState.Inert;'),
]


def run():
    b = subprocess.run(['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if 'Build succeeded' not in b.stdout:
        return 'BUILD FAILED'
    r = subprocess.run(['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    for line in r.stdout.splitlines():
        if line.startswith('RESULTS:'):
            return line.strip()
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if '[FAIL]' not in ((r.stdout or '') + (r.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return 'NO RESULT LINE'


originals = {p: open(p, encoding='utf-8').read() for p in (RULES,)}

print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print(f'\nREFUSING TO RUN: baseline is RED ({m.group(2)} failing). Every mutant would '
          'score KILLED on pre-existing failures and this battery would prove nothing.')
    sys.exit(2)

survivors = []
try:
    for i, (path, name, old, new) in enumerate(MUTANTS, 1):
        print(f'\n=== mutant {i}/{len(MUTANTS)}: {name} ===')
        src = originals[path]
        if src.count(old) != 1:
            print(f'  [SKIP] {name}: anchor matched {src.count(old)} times in '
                  f'{os.path.basename(path)}')
            survivors.append(name + ' (ANCHOR)')
            continue
        open(path, 'w', encoding='utf-8', newline='').write(src.replace(old, new))
        res = run()
        killed = _battery.score(res, run)
        print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
        if not killed:
            survivors.append(name)
        open(path, 'w', encoding='utf-8', newline='').write(src)
finally:
    # try/finally: a battery killed mid-run otherwise leaves a LIVE MUTANT in the tree --
    # measured once already, when a stopped mutate_cm4 batch left one in TradeCopierEngine.cs
    # and a `git diff` skim did not find it.
    for p, text in originals.items():
        open(p, 'w', encoding='utf-8', newline='').write(text)

print('\nrestored originals;', run())

if survivors:
    print('\nSURVIVORS:')
    for s in survivors:
        print('  -', s)
else:
    print('\nSURVIVORS: none')

# Plain exit, NOT _battery.finish: this battery declares no EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions.
sys.exit(1 if survivors else 0)
