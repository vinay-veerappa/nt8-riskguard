"""Mutation battery for the sim/live classifier -- `P2-38`, extended 2026-08-15 for Playback.

⚠️ THIS DID NOT EXIST UNTIL SESSION 42, AND THAT IS THE FIRST FINDING. Twenty-seven batteries, and
NONE of them mutated `IsSimulationAccount` -- the single predicate that decides whether an account
can lose real money. It gates `confirmLive` on order placement, strategy deployment, and T5's
requirement that a live follower be protected by RiskGuard. `P2-38` was a real defect in it
(`Name.StartsWith("Sim")` exempted a funded account called "SimpsonFund") and its fix shipped with
tests but no mutants. The riskiest predicate in the repo was the least mutated -- `P2-27`'s shape.

WHAT CHANGED AND WHY IT NEEDED A BATTERY. `Provider.Playback` was added, reversing the doc
comment's own recorded decision ("Playback is deliberately NOT exempt"). The reversal is defensible
-- Market Replay is how the position-dependent tickets get driven with the market shut, and
Playback101 classifying as LIVE would mean `confirmLive: true` on every replay order, rehearsing
the exact flag that protects the funded 50K against an account that cannot lose a cent. But
**widening a safety classifier is the direction `P2-38` itself failed in**, so it does not ship on
tests alone.

⚠️ THE MUTANT THAT MATTERS IS 3. Every positive assertion -- Sim101 is sim, Playback101 is sim --
passes just as happily under a classifier widened ONE VALUE TOO FAR. Only the negative half
(Rithmic, InteractiveBrokers, NinjaTrader are live) can tell the difference. That is
`detector-needs-a-negative-test` applied to the money switch: a classifier that says "simulated" to
everything passes every positive test ever written for it.

What each mutant defends:

  * MUTANT 1 restores `P2-38` VERBATIM: the name prefix goes back, so a funded account called
    "SimpsonFund" is exempted from BOTH live gates at once.

  * MUTANT 2 fails OPEN on null. The doc comment's floor is that anything unidentifiable stays
    live; this makes an unresolvable account simulated, which is the one direction that costs money.

  * MUTANT 3 widens to "anything that is not NinjaTrader", so Rithmic and InteractiveBrokers -- both
    real money -- classify as simulated. THE ONE VALUE TOO FAR. Killable only by the negative tests.

  * MUTANT 4 drops Simulator and keeps only Playback, so Sim101 becomes live. The opposite error:
    harmless to money, and it would break every sim workflow in the repo while looking like a
    tightening.

  * MUTANT 5 makes it unconditionally true -- every funded account on the box classifies as
    simulated. The whole gate, deleted, in one word.
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
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    ("P2-38 RESTORED VERBATIM: the name prefix goes back, so a funded account called\n"
     "     'SimpsonFund' is exempt from confirmLive AND from T5's guarded-follower requirement",
     '            return account.Provider == Provider.Simulator\n'
     '                || account.Provider == Provider.Playback;',
     '            return account.Provider == Provider.Simulator\n'
     '                || account.Provider == Provider.Playback\n'
     '                || (account.Name != null && account.Name.StartsWith("Sim"));'),

    ("the null case fails OPEN, so an account this cannot identify is treated as SIMULATED --\n"
     "     the one direction that costs money, and the floor the doc comment sets",
     '            if (account == null) return false;',
     '            if (account == null) return true;'),

    ("THE ONE VALUE TOO FAR: widened to 'anything that is not NinjaTrader', so Rithmic and\n"
     "     InteractiveBrokers -- real money both -- classify as simulated. EVERY POSITIVE TEST\n"
     "     STILL PASSES; only the negative half can catch this",
     '                || account.Provider == Provider.Playback;',
     '                || account.Provider != Provider.NinjaTrader;'),

    ("Simulator is dropped and only Playback remains, so Sim101 classifies as LIVE. Harmless\n"
     "     to money and breaks every sim workflow in the repo, while reading like a tightening",
     '            return account.Provider == Provider.Simulator\n',
     '            return account.Provider == Provider.Playback\n'),

    ("the gate is deleted in one word: every funded account on the box classifies as simulated",
     '            if (account == null) return false;\n'
     '            return account.Provider == Provider.Simulator\n'
     '                || account.Provider == Provider.Playback;',
     '            return true;'),
]

ORIGINAL = open(ENGINE, encoding='utf-8').read()


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
    open(ENGINE, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(old, new))
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
    open(ENGINE, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(ENGINE, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())

print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
