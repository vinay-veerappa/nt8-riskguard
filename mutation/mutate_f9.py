"""Mutation battery for F-9 (the firm-rule REPORTER must resolve the account's firm plan).

P1-42 made the ENFORCER resolve a per-account effective firm config and flatten on
that plan's numbers. `GuardRules`' two firm rules never followed: they branched on
the TOP-LEVEL sub-rule switch and reported the TOP-LEVEL Amount. The acceptance
matrix caught them disagreeing with the enforcer in BOTH directions, on the shapes
the four researched profiles actually use:

    reporter=Disabled  enforcer=FIRES   top-level off, the plan's rule on
    reporter=Enforcing enforcer=silent  top-level on, the plan's rule off

The second is the real Take Profit Trader profile, whose DailyLoss is OFF because
TPT has no daily loss limit -- so the inventory reported a live daily-loss rule
that could not fire. That is the direction that costs money.

WHAT EACH GROUP IS DEFENDING:

  * MUTANTS 1 and 2 restore the defect itself, once per rule: branch on the
    top-level sub-rule instead of the resolved one.

  * MUTANTS 3 and 4 are the interesting ones, and they are P1-42's own lesson
    ("logging the top-level amounts while breaching on a profile's would make the
    audit trail describe a rule that did not run"). They keep the resolved BRANCH
    and report the top-level AMOUNT. Every state assertion still passes -- the row
    is Enforcing, which is correct -- and the number beside it is a limit the
    operator is not being held to. Only the limit test sees it.

  * MUTANT 5 puts the evidence count back to `AccountFirmMap.Count`. These are
    PerAccount rules; on the live box, ONE mapped account would have turned all
    96 accounts' firm rules green, 88 of them expired prop accounts.

  * MUTANT 6 makes the evidence unconditional, so an unmapped account renders as
    firm-protected while the number in force is the guessed top-level one.

  * MUTANT 7 keys the evidence on `resolved` rather than `mapped`. This looks
    STRICTER and is wrong: a dangling mapping then reports 0 evidence, the count
    stops varying with the collection, and the derived EvidenceLabel check fails.
    It is here because "be more conservative" is the plausible wrong edit.

  * MUTANT 8 drops the master switch. `ComputeFirmMirror` does not check
    `FirmMirror.Enabled` -- its CALLERS do -- so a reporter that skips it claims a
    rule the guard never reaches.

  * MUTANT 9 asks "did it resolve?" with `ContainsKey` instead of `TryGetValue`
    plus a null check. A `FirmProfiles` entry whose VALUE is null answers
    ContainsKey true while the resolver falls back, so the note claims a plan's
    numbers are in force when the top-level block's are. This is the one hole the
    loop's candidate actually had, it was found by hand rather than by the panel,
    and `"FirmProfiles": { "Apex-100K": null }` is a typo away from a real config.

  * MUTANT 10 flips the daily-loss sign. The reading has been negative by
    convention since the rule was written, beside a RealizedPnL that is also
    negative. The first draft of that assertion used Math.Abs to avoid committing
    to the convention and this mutant SURVIVED it; the assertion was tightened.

  * MUTANT 11 drops the plan key from the note. The row is correct and the
    operator cannot check it against the firm's rulebook, which is the only reason
    the mapping is worth having.

WHAT IS NOT MUTATED, and it is a real gap. Nothing pins that the amounts on a plan
named `-100K` were derived for a 100k account: `FirmProfile` has no `AccountSize`
and nothing compares one to observed equity. Filed in CONFIG_DEFAULTS R3a. Until it
exists, the account size lives in a dictionary key.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red
baseline.
"""
import os
import re
import subprocess
import sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')

MUTANTS = [
    ("the TRAILING rule branches on the TOP-LEVEL sub-rule again instead of the resolved\n"
     "     plan's -- the defect, restored. Reports Disabled while the guard flattens on the\n"
     "     plan's numbers",
     '                    var sub = eff.TrailingDD;',
     '                    var sub = fm.TrailingDD;'),

    ("the DAILY-LOSS rule branches on the TOP-LEVEL sub-rule again. This is the TPT shape:\n"
     "     the plan has no daily loss limit, the top-level block does, and the inventory\n"
     "     reports a live rule that cannot fire",
     '                    var sub = eff.DailyLoss;',
     '                    var sub = fm.DailyLoss;'),

    ("the TRAILING rule keeps the resolved BRANCH and reports the TOP-LEVEL AMOUNT. Every\n"
     "     state assertion passes and the number beside the row is a limit the operator is not\n"
     "     held to -- P1-42's lesson, one layer out",
     '                        sub.Amount, mapped && HasEquityReading(c.Account) ? 1 : 0, note);',
     '                        fm.TrailingDD.Amount, mapped ? 1 : 0, note);'),

    ("the DAILY-LOSS rule keeps the resolved branch and reports the top-level amount",
     '                        -Math.Abs(sub.Amount), mapped ? 1 : 0, note);',
     '                        -Math.Abs(fm.DailyLoss.Amount), mapped ? 1 : 0, note);'),

    ("evidence goes back to the MAP SIZE on the trailing rule. One mapped account turns all\n"
     "     96 accounts' firm rules green, 88 of them expired prop accounts",
     '                    return R(HasEquityReading(c.Account) ? (double?)c.Account.AccountEquity : null,\n'
     '                        sub.Amount, mapped && HasEquityReading(c.Account) ? 1 : 0, note);',
     '                    return R(HasEquityReading(c.Account) ? (double?)c.Account.AccountEquity : null,\n'
     '                        sub.Amount, fm.AccountFirmMap == null ? 0 : fm.AccountFirmMap.Count, note);'),

    ("evidence becomes unconditional on the trailing rule, so an UNMAPPED account renders as\n"
     "     firm-protected while the number in force is the guessed top-level one",
     '                        sub.Amount, mapped && HasEquityReading(c.Account) ? 1 : 0, note);',
     '                        sub.Amount, 1, note);'),

    ("evidence keys on `resolved` instead of `mapped` on the trailing rule. Looks stricter and\n"
     "     is wrong: a dangling mapping reports 0, the count stops varying with the collection,\n"
     "     and the derived EvidenceLabel check fails",
     '                        sub.Amount, mapped && HasEquityReading(c.Account) ? 1 : 0, note);',
     '                        sub.Amount, resolved ? 1 : 0, note);'),

    ("the trailing rule drops the MASTER switch. ComputeFirmMirror does not check\n"
     "     FirmMirror.Enabled -- its callers do -- so the reporter claims a rule the guard\n"
     "     never reaches",
     '                    if (fm == null || !fm.Enabled)\n'
     '                        return Off("firm mirror is off, so no firm trailing drawdown is evaluated for any account");',
     '                    if (fm == null)\n'
     '                        return Off("firm mirror is off, so no firm trailing drawdown is evaluated for any account");'),

    ("\"did it resolve?\" is asked with ContainsKey instead of TryGetValue plus a null check.\n"
     "     A FirmProfiles entry whose VALUE is null answers true while the resolver falls back,\n"
     "     so the note claims a plan's numbers are in force when the top-level block's are.\n"
     "     This is the hole the loop's candidate had, found by hand and not by the panel",
     '                    FirmProfile plan = null;\n'
     '                    bool resolved = mapped && fm.FirmProfiles != null\n'
     '                        && fm.FirmProfiles.TryGetValue(firmKey, out plan) && plan != null;\n'
     '                    var eff = RiskGuardAddOn.ResolveEffectiveFirmConfig(fm, c.AccountName);\n'
     '                    var sub = eff.TrailingDD;',
     '                    bool resolved = mapped && fm.FirmProfiles != null\n'
     '                        && fm.FirmProfiles.ContainsKey(firmKey);\n'
     '                    var eff = RiskGuardAddOn.ResolveEffectiveFirmConfig(fm, c.AccountName);\n'
     '                    var sub = eff.TrailingDD;'),

    ("the daily-loss reading loses its NEGATIVE sign. A loss then reads as being under a\n"
     "     POSITIVE limit. An assertion wrapped in Math.Abs let this survive, which is why the\n"
     "     assertion now names the sign",
     '                        -Math.Abs(sub.Amount), mapped ? 1 : 0, note);',
     '                        Math.Abs(sub.Amount), mapped ? 1 : 0, note);'),

    ("the trailing note drops the plan key. The row is correct and the operator cannot check\n"
     "     the number against the firm's rulebook, which is the only reason to map at all",
     '                        ? "resolved to plan \'" + firmKey + "\'; its TrailingDD numbers are in force"',
     '                        ? "resolved to a firm plan; its TrailingDD numbers are in force"'),
]


def run():
    build = subprocess.run(
        ['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if build.returncode != 0:
        return 'BUILD FAILED'
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if not m and '[FAIL]' not in ((res.stdout or '') + (res.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINAL = open(RULES, encoding='utf-8').read()

print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print('\nREFUSING TO RUN: baseline is RED (%s failing). Every mutant would score KILLED '
          'on pre-existing failures and this battery would prove nothing.' % m.group(2))
    sys.exit(2)

survivors = []
for name, old, new in MUTANTS:
    if ORIGINAL.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, ORIGINAL.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(RULES, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(RULES, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(RULES, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
