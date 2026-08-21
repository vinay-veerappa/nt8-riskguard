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

  * MUTANT 3 drops the flat-position filter; MUTANT 4 drops only its `Quantity <= 0` half.
    ⚠️ BOTH ARE `EXPECTED SURVIVOR:` AS OF P2-145 (v1.44.0), with the reason on each marker.
    In short: the defect they expressed needed the old inline predicate, whose `!isProtected`
    arm fired on a flat position with gap=0. `AssessCoverage` now answers `positionQty <= 0`
    with `None` before anything else, so the caller's filter is no longer observable and no
    test can reach these. The equivalent coverage moved to mutate_p2145coverage.py group 5,
    which mutates that answer where it is now given. Neither the filter nor the totality check
    should be removed to make these killable again.

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

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


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

    ("EXPECTED SURVIVOR: as of P2-145 (v1.44.0) this mutant is EQUIVALENT and cannot be\n"
     "     killed, and the defect it expressed WAS real. The old inline predicate was\n"
     "     `!isProtected || covered < positionQty`. On a flat position that reads\n"
     "     `covered(0) < positionQty(0)` FALSE or `!isProtected` TRUE -- so a flat position with\n"
     "     no FSM fired NAKED_POSITION with gap=0 on every audit tick, and the caller's filter\n"
     "     was the only thing between that and the log. `AssessCoverage` now answers\n"
     "     `positionQty <= 0` with `CoverageFinding.None` before anything else, so removing the\n"
     "     caller's filter has no observable effect and no test can distinguish it.\n"
     "     THE COVERAGE MOVED RATHER THAN VANISHING: mutate_p2145coverage.py group 5 mutates\n"
     "     `positionQty <= 0` to `< 0` directly -- the same question, asked where it is now\n"
     "     answered. Do NOT delete the caller's filter (defence in depth, and it skips work) and\n"
     "     do NOT weaken AssessCoverage to make this killable again, which would be making the\n"
     "     code worse to keep a battery green. [[a-gate-evidence-changes-with-shape]]:\n"
     "     restructuring what a gate READS changes what it proves while its own code is untouched.\n"
     "     If this is ever KILLED, `_battery.finish` fails and that is correct -- it means the\n"
     "     totality check went away and this declaration is stale.\n"
     "     ORIGINAL INTENT: the flat-position filter is removed entirely.\n"
     "     account.Positions can carry a flat Position, and a FLAT account then reported\n"
     "     NAKED_POSITION on every audit tick",
     '                        if (pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0)\n'
     '                            continue;',
     '                        if (pos == null)\n'
     '                            continue;'),

    ("EXPECTED SURVIVOR: as of P2-145 (v1.44.0) this mutant is EQUIVALENT and cannot be\n"
     "     killed, and the defect it expressed WAS real. The old inline predicate was\n"
     "     `!isProtected || covered < positionQty`. On a flat position that reads\n"
     "     `covered(0) < positionQty(0)` FALSE or `!isProtected` TRUE -- so a flat position with\n"
     "     no FSM fired NAKED_POSITION with gap=0 on every audit tick, and the caller's filter\n"
     "     was the only thing between that and the log. `AssessCoverage` now answers\n"
     "     `positionQty <= 0` with `CoverageFinding.None` before anything else, so removing the\n"
     "     caller's filter has no observable effect and no test can distinguish it.\n"
     "     THE COVERAGE MOVED RATHER THAN VANISHING: mutate_p2145coverage.py group 5 mutates\n"
     "     `positionQty <= 0` to `< 0` directly -- the same question, asked where it is now\n"
     "     answered. Do NOT delete the caller's filter (defence in depth, and it skips work) and\n"
     "     do NOT weaken AssessCoverage to make this killable again, which would be making the\n"
     "     code worse to keep a battery green. [[a-gate-evidence-changes-with-shape]]:\n"
     "     restructuring what a gate READS changes what it proves while its own code is untouched.\n"
     "     If this is ever KILLED, `_battery.finish` fails and that is correct -- it means the\n"
     "     totality check went away and this declaration is stale.\n"
     "     ORIGINAL INTENT: only the `Quantity <= 0` half of the flat filter is dropped. A\n"
     "     reviewer reading the diff sees a flat filter and moves on. Equivalent for the\n"
     "     same reason and by the same single line: MarketPosition.Flat implies Quantity 0\n"
     "     on NT8, so both halves of that filter collapse to one test",
     '                        if (pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0)\n'
     '                            continue;\n'
     '                        // FullName, not ToString()',
     '                        if (pos == null || pos.MarketPosition == MarketPosition.Flat)\n'
     '                            continue;\n'
     '                        // FullName, not ToString()'),

    ("`|| !hasFsm` goes back on the ORPHAN_STOP condition, so a stop correctly covering a\n"
     "     LIVE position is reported as an orphan -- a name that means the opposite of the\n"
     "     situation, and a duplicate of the NAKED_POSITION already emitted for it",
     # P2-108 REPOINTED THIS ANCHOR. The finding is no longer logged inline -- it is recorded and
     # emitted at the end of the pass through AuditFindingThrottle -- so the old find-string
     # (`if (!hasPosition) { LogEvent(...ORPHAN_STOP...)`) stopped matching. REPOINTED, NOT
     # RETIRED: the mutant still expresses exactly the same defect (a stop correctly covering a
     # LIVE position reported as an orphan), it just attacks the condition rather than the log
     # call. `check_anchors.py` caught this in the same commit that broke it.
     '                        if (!hasPosition)\n                        {\n                            firedKeys.Add(orphanKey);',
     '                        if (!hasPosition || !hasFsm)\n                        {\n                            firedKeys.Add(orphanKey);'),

    # ⚠️ MUTANT REMOVED 2026-08-18 (P2-152), and this note is the point of the removal.
    #
    # It inverted the coverage comparison in the audit's inline predicate:
    #     'if (!isProtected || covered < positionQty)' -> '... covered > positionQty'
    #
    # P2-145 replaced that predicate with `RiskGuardAddOn.AssessCoverage`, so the only
    # remaining occurrence of the find-string is the COMMENT in RiskGuardAddOn.cs that quotes
    # the old predicate to explain what it replaced. The mutant was editing a comment: no
    # effect, suite green, scored SURVIVED -- and `check_anchors.py` reported it healthy the
    # whole time, because the text still matched EXACTLY ONCE. An anchor that matches a comment
    # is as dead as one that matches nothing, and it is harder to see.
    #
    # ⚠️ NOT re-pointed at AssessCoverage, deliberately. mutate_p2145coverage.py groups 1 and 2
    # already mutate that comparison there, in more spellings than this one had (the state test,
    # the `<=` off-by-one, and the tempting wrong fix). Two batteries rewriting one line is a
    # collision risk for no extra evidence.

    ("EXPECTED SURVIVOR: the audit holds _stateLock across the broker reads (P1-10/P1-12: a\n"
     "     broker call under the state lock is how this addon deadlocks). Survives unless the lock\n"
     "     invariant drives the audit path -- recorded here rather than left to be rediscovered",
     '            try\n            {\n                foreach (Account account in Account.All)\n                {\n                    string accountName = account.Name;',
     '            try\n            {\n                lock (_stateLock)\n                foreach (Account account in Account.All)\n                {\n                    string accountName = account.Name;'),
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
    killed = _battery.score(res, run)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(GUARD, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(GUARD, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())
_battery.finish(survivors, MUTANTS)
