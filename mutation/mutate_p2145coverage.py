"""Mutation battery for P2-145: what counts as a coverage gap.

The audit's NAKED_POSITION predicate was, inline inside `RunGuardAudit`:

    if (!isProtected || covered < positionQty)

An OR whose two arms mean different things, raising one finding that named only one of them.
MEASURED across 245 logged findings in `interventions.jsonl` on this box:

    gap == positionQty - covered            245 of 245   the filed half of P2-145 did not exist
    fired with gap=0, all ProtectedPending   17          a FULLY COVERED position called naked
    fired reading Protected with gap 1-2      4          legitimate: Protected != fully covered

So 21 of 245 findings were wrong, in two different ways, and the suite was green throughout --
because every NAKED_POSITION test in this repo tests the THROTTLE (`AuditFindingThrottle`) and the
predicate needed `Account.All` to reach. `AssessCoverage` exists to be reachable.
[[a-detector-needs-a-negative-test]] is the whole shape: a predicate that fires on everything
passes every positive test ever written for it, and there were no negative ones.

THE GROUPS BELOW:

  1. THE NARROWING ITSELF -- requiring a real gap. Mutants here restore the old OR in its several
     spellings. Each must die on the 17 measured false alarms.
  2. ⚠️ THE TRUE POSITIVES THE NARROWING COULD HAVE EATEN. Silencing `gap=0` by demanding
     `Protected` would also silence the 4 legitimate partials, because `Protected` means "something
     is covering", not "everything is" (P1-36). A fix that trades one wrong answer for another is
     the standing hazard -- [[a-filter-that-matches-too-much]], where narrowing a match on a path
     that decides whether to FLATTEN has asymmetric failure directions.
  3. ⚠️ WHERE THE REMOVED ARM WENT. `!isProtected` was the only reporter of "fully covered while
     the state machine disagrees". Deleting rather than rehoming it would lose a signal silently,
     which is the one failure mode a green suite cannot show you.
  4. THE PARTIAL/TOTAL DISTINCTION, which is new reporting and therefore new surface. `covered=0`
     and `covered=1 of 2` are different operator situations and used to print identically.
  5. SIGN AND TOTALITY. `Position.Quantity` is absolute on NT8 (P0-96); a flat or absent position
     must never raise a phantom finding.
"""
import os
import re
import subprocess
import sys

# Pinned before anything prints. Several mutant descriptions below contain a non-ASCII warning
# glyph, and on a cp1252 console print() raises UnicodeEncodeError -- which happens AFTER a mutant
# is applied and BEFORE restore(), leaving a live mutant in the tree. Measured in CI on
# mutate_p182.py, 2026-08-15. [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the narrowing itself ----------------------------------------------------------
    # The old predicate, restored exactly. Fires on every position whose state is not `Protected`,
    # including the 17 measured ProtectedPending rows that were fully covered.
    (GUARD, 'group 1: the OLD predicate restored -- any state but Protected is naked, so 17 '
            'measured FULLY COVERED positions are reported as uncovered again',
     '            if (covered < positionQty)\n'
     '            {\n'
     '                return new CoverageAssessment\n'
     '                {\n'
     '                    Finding = CoverageFinding.NakedPosition,',
     '            if (covered < positionQty || state != GuardFsmState.Protected)\n'
     '            {\n'
     '                return new CoverageAssessment\n'
     '                {\n'
     '                    Finding = CoverageFinding.NakedPosition,'),

    # The same defect spelled as an off-by-one rather than a state test. `<=` calls a position
    # naked at the exact moment it becomes fully covered -- the most ordinary state there is.
    (GUARD, 'group 1: the gap test becomes <=, so a position covered EXACTLY is naked. The '
            'ordinary case -- one stop for the whole position -- is the one that breaks',
     '            if (covered < positionQty)',
     '            if (covered <= positionQty)'),

    # ---- group 2: the true positives the narrowing could have eaten -----------------------------
    # The tempting wrong fix: silence gap=0 by demanding Protected. Kills the 17 AND the 4.
    (GUARD, 'group 2: the fix that silences the 17 by demanding Protected -- which also silences '
            'the 4 measured LEGITIMATE partials, because Protected means "something is covering" '
            'and not "everything is" (P1-36). One wrong answer traded for another',
     '            if (covered < positionQty)\n'
     '            {\n'
     '                return new CoverageAssessment\n'
     '                {\n'
     '                    Finding = CoverageFinding.NakedPosition,',
     '            if (covered < positionQty && state != GuardFsmState.Protected)\n'
     '            {\n'
     '                return new CoverageAssessment\n'
     '                {\n'
     '                    Finding = CoverageFinding.NakedPosition,'),

    # ---- group 3: where the removed arm went ----------------------------------------------------
    # Delete the rehomed signal instead of moving it. A green suite cannot show you a finding that
    # simply stopped existing, which is exactly why this gets a mutant.
    (GUARD, 'group 3: full coverage under a disagreeing state reports NOTHING -- the arm that was '
            'removed from the OR is deleted rather than rehomed, and an FSM stuck Unprotected '
            'behind a complete stop becomes invisible. [[dead-safety-machinery-gate]]',
     '            return new CoverageAssessment { Finding = CoverageFinding.CoverageDisagrees, Gap = 0 };',
     '            return new CoverageAssessment { Finding = CoverageFinding.None, Gap = 0 };'),

    # ProtectedPending stops counting as agreement -> the 17 come back through the OTHER branch,
    # now mislabelled as a disagreement rather than as nakedness. Still wrong, differently.
    (GUARD, 'group 3: ProtectedPending stops counting as state agreement, so the 17 measured rows '
            'return as FSM_COVERAGE_DISAGREES instead of NAKED_POSITION -- quieter, still false, '
            'and this single line is what the whole defect turns on',
     '            bool stateAgrees = hasFsm\n'
     '                && (state == GuardFsmState.Protected || state == GuardFsmState.ProtectedPending);',
     '            bool stateAgrees = hasFsm\n'
     '                && (state == GuardFsmState.Protected);'),

    # The reverse: every state agrees, so group 3's finding can never fire at all.
    (GUARD, 'group 3: every state counts as agreement, so FSM_COVERAGE_DISAGREES is a finding with '
            'no input that produces it -- [[a-green-that-can-never-be-red]]',
     '            bool stateAgrees = hasFsm\n'
     '                && (state == GuardFsmState.Protected || state == GuardFsmState.ProtectedPending);',
     '            bool stateAgrees = hasFsm;'),

    # ---- group 4: the partial/total distinction --------------------------------------------------
    (GUARD, 'group 4: everything is reported as PARTIAL, so a position with no stop at all reads '
            'like one with half a stop -- the two situations an operator most needs separated',
     '                    Partial = covered > 0',
     '                    Partial = true'),

    (GUARD, 'group 4: nothing is ever reported as partial, so the 4 measured Protected-with-a-gap '
            'rows lose the only field that says half the position IS covered',
     '                    Partial = covered > 0',
     '                    Partial = false'),

    # ---- group 5: sign and totality --------------------------------------------------------------
    # P0-96: Position.Quantity is absolute. A negative quantity means the caller is confused, and
    # answering it as a finding invents an alarm out of a bug elsewhere.
    (GUARD, 'group 5: a flat or negative position raises a finding -- Position.Quantity is '
            'ABSOLUTE on NT8 (P0-96) so a negative is a caller bug, and turning it into a naked '
            'alarm manufactures a gap from nothing',
     '            if (positionQty <= 0)\n'
     '                return new CoverageAssessment { Finding = CoverageFinding.None };',
     '            if (positionQty < 0)\n'
     '                return new CoverageAssessment { Finding = CoverageFinding.None };'),

    # The gap arithmetic itself -- the half of P2-145 that was FILED and proved not to exist. It is
    # mutated anyway, because "measured correct in 245 rows" is a statement about the past.
    (GUARD, 'group 5: the gap stops being position - covered, which is the half of P2-145 that was '
            'filed and measured NOT to exist (245/245 consistent). Held then; mutated so it cannot '
            'quietly start being true',
     '                    Gap = positionQty - covered,',
     '                    Gap = positionQty,'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # ⚠️ The encoding is PINNED. Without it the write uses the platform default (cp1252 here) and
    # raises part-way through on any non-ASCII byte in the file -- leaving a MUTANT on disk while
    # the battery reports having restored. [[a-battery-must-reach-its-restore-line]].
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


def run():
    try:
        p = subprocess.run(
            ['dotnet', 'run', '--project', os.path.join(REPO, 'tests', 'RiskGuardTests.csproj'),
             '--nologo', '-v', 'q'],
            cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=900)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    out = (p.stdout or '') + (p.stderr or '')
    if 'error CS' in out:
        return 'BUILD FAILED'
    m = re.search(r'Passed = (\d+), Failed = (\d+)', out)
    result = m.group(0) if m else 'NO RESULT LINE'

    # P2-148: a crash is not a detection. The harness prints its result line last, so any unhandled
    # exception leaves 'NO RESULT LINE' -- which scores as KILLED whether or not anything objected.
    # Require at least one [FAIL] before believing a crash was a detection.
    if not m and '[FAIL]' not in out:
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return result


baseline = run()
print('=== baseline ===\n  %s' % baseline)
if 'Failed = 0' not in baseline:
    print('baseline is RED; a battery against a red baseline scores nothing')
    sys.exit(2)

survivors = []
for target, name, old, new in MUTANTS:
    original = ORIGINALS[target]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    try:
        res = run()
        killed = _battery.score(res, run)
        print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
        if not killed:
            survivors.append(name)
    finally:
        restore()

restore()
print('\nrestored originals;', run())

print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
