"""Mutation battery for P3-30's guard audit -- specifically its instrument matching.

⚠️ THIS DEFECT SHIPPED, AND THE THREE TESTS IT SHIPPED WITH COULD NOT SEE IT.

`RunGuardAudit` keyed both of its broker reads on `Instrument.ToString()`. Every FSM
in this addon is keyed on `Instrument.FullName` -- 19 call sites -- so nothing the
audit looked up ever matched. The consequence on a live box is not a missed finding,
it is the opposite: a correctly protected account reported NAKED_POSITION,
ORPHAN_STOP *and* FSM_DIVERGENCE, every 10 seconds, forever.

The three acceptance tests shipped with it are all POSITIVE-ONLY -- each asserts that
its event WAS emitted. A total matching failure emits every event, so all three pass
under the defect. That is the reusable lesson and it is why mutant 1 exists: the fix
is one identifier, and only a NEGATIVE test can defend it.

What each mutant is defending:

  * MUTANT 1 restores `ToString()` on the position read. This is the shipped defect.
    It is killed only by the silence test; the three positive tests stay green.

  * MUTANT 2 restores `ToString()` on the ORDER read. Same class, other half -- this
    one alone breaks ORPHAN_STOP and FSM_DIVERGENCE while NAKED_POSITION still works,
    so it checks that the silence test covers both reads and not just the first.

  * MUTANT 3 drops the flat-position filter. `account.Positions` can carry a flat
    Position, and without the filter a FLAT account reports NAKED_POSITION on every
    tick of the audit timer. The FSM-seeding sweep has always filtered these; the
    audit did not.

  * MUTANT 4 drops only the `Quantity <= 0` half of that filter, keeping the
    MarketPosition check. A reviewer reading the diff sees a flat filter and moves on.

  * MUTANT 5 puts `|| !hasFsm` back on the ORPHAN_STOP condition. A stop covering a
    LIVE position is not an orphan -- P0-50's class is a stop left working on a FLAT
    account. The untracked-position case is already reported as NAKED_POSITION, so
    this re-reports it under a name whose meaning is the opposite of the situation.

  * MUTANT 6 inverts the coverage comparison to `covered > positionQty`. A partially
    covered position -- the exact P0-55 shape -- stops being reported while a fully
    covered one starts being reported. Both directions wrong from one character.

  * MUTANT 7 makes the audit hold `_stateLock` across the broker reads. P1-10/P1-12:
    a broker call under the state lock is how this addon deadlocks. Nothing in the
    suite fails, because the test stubs never block -- so this one is expected to be
    a documented SURVIVOR if the lock invariant does not drive the audit path.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    ("the POSITION read goes back to Instrument.ToString(), which matches no FSM key --\n"
     "     the shipped defect. All three positive acceptance tests stay green under it;\n"
     "     only the silence test can see it",
     'string instrument = pos.Instrument == null ? string.Empty : pos.Instrument.FullName;',
     'string instrument = pos.Instrument == null ? string.Empty : pos.Instrument.ToString();'),

    ("the ORDER read goes back to Instrument.ToString(). NAKED_POSITION still works, so\n"
     "     this checks the silence test covers BOTH broker reads and not just the first",
     '                        string instrument = order.Instrument.FullName;',
     '                        string instrument = order.Instrument.ToString();'),

    ("the flat-position filter is removed entirely. account.Positions can carry a flat\n"
     "     Position, and a FLAT account then reports NAKED_POSITION on every audit tick",
     '                        if (pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0)\n'
     '                            continue;',
     '                        if (pos == null)\n'
     '                            continue;'),

    ("only the `Quantity <= 0` half of the flat filter is dropped. A reviewer reading the\n"
     "     diff sees a flat filter and moves on",
     '                        if (pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0)\n'
     '                            continue;\n'
     '                        // FullName, not ToString()',
     '                        if (pos == null || pos.MarketPosition == MarketPosition.Flat)\n'
     '                            continue;\n'
     '                        // FullName, not ToString()'),

    ("`|| !hasFsm` goes back on the ORPHAN_STOP condition, so a stop correctly covering a\n"
     "     LIVE position is reported as an orphan -- a name that means the opposite of the\n"
     "     situation, and a duplicate of the NAKED_POSITION already emitted for it",
     '                        if (!hasPosition)\n                        {\n                            LogEvent(accountName, "ORPHAN_STOP",',
     '                        if (!hasPosition || !hasFsm)\n                        {\n                            LogEvent(accountName, "ORPHAN_STOP",'),

    ("the coverage comparison is inverted to `covered > positionQty`. A partially covered\n"
     "     position -- P0-55's exact shape -- stops being reported, and a fully covered one\n"
     "     starts being reported. Both directions wrong from one character",
     'if (!isProtected || covered < positionQty)',
     'if (!isProtected || covered > positionQty)'),

    ("EXPECTED SURVIVOR: the audit holds _stateLock across the broker reads (P1-10/P1-12: a\n"
     "     broker call under the state lock is how this addon deadlocks). Survives unless the lock\n"
     "     invariant drives the audit path -- recorded here rather than left to be rediscovered",
     '            try\n            {\n                foreach (Account account in Account.All)\n                {\n                    string accountName = account.Name;',
     '            try\n            {\n                lock (_stateLock)\n                foreach (Account account in Account.All)\n                {\n                    string accountName = account.Name;'),
]


def run():
    build = subprocess.run(
        ['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    if build.returncode != 0:
        return 'BUILD FAILED'
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINAL = open(GUARD, encoding='utf-8').read()

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
    open(GUARD, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(GUARD, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(GUARD, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())
_battery.finish(survivors, MUTANTS)
