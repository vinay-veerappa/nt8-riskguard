"""Mutation battery for P2-150: PlaceBracket read its exit legs' OrderState in the same breath
as Submit(), so `partial_submit` was a status no live input could ever set.

Submit is ASYNCHRONOUS. Measured from interventions.jsonl, eight bridge-placed brackets on
2026-08-10, a stop leg's state sequence was Initialized -> Submitted (+21ms) -> Accepted (+132ms);
the Rejected/Cancelled verdict arrives 20-200ms later on OnOrderUpdate. So at the instant the old
loop ran, every leg that would LATER be rejected was still Initialized, the predicate was false,
and "partial_submit" was unreachable -- [[a-green-that-can-never-be-red]]. The fix reports
"pending_legs" with the leg ids, and leaves the actual detection to the guard's own net.

THE GROUPS:

  1. THE STATUS IS HONEST. "pending_legs", not "submitted" (over-claims acceptance) and not the
     dead "partial_submit". Every successful-placement test now pins pending_legs, so a regress to
     "submitted" dies across the whole ATM suite.
  2. ⚠️ THE SYNCHRONOUS VERDICT DOES NOT COME BACK. This is the flagship: re-introducing a read of
     stopOrder.OrderState right after Submit sets "partial_submit" AGAIN -- but only the P2-150
     test can see it, because it is the only one that drives the stub's (unrealistic) synchronous
     rejection. The 14 normal tests stay green under this mutant, which is exactly why the P2-150
     test had to exist. [[test-doubles-are-not-evidence]].
  3. THE CALLER IS TOLD WHY. The note names that acceptance is pending and points at the leg ids;
     without it "pending_legs" is a status with no remedy.
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')

MUTANTS = [
    # ---- group 1: the status is honest ------------------------------------------------------
    (ATM, 'group 1: the status regresses to "submitted", which over-claims that the protective '
          'legs are accepted when their acceptance is not yet known -- the exact false confidence '
          'the ticket is about. Dies across the whole ATM suite, which now pins pending_legs',
     '                result.Status = "pending_legs";',
     '                result.Status = "submitted";'),

    (ATM, 'group 1: the status is hardcoded to the dead "partial_submit" -- the value that could '
          'never be reached by any live input is now the one always returned',
     '                result.Status = "pending_legs";',
     '                result.Status = "partial_submit";'),

    # ---- group 2: the synchronous verdict does not come back (flagship) ----------------------
    (ATM, 'group 2: the synchronous OrderState read is RE-INTRODUCED, setting "partial_submit" '
          'from a leg state that in production is still Initialized at this instant. Under the '
          'stub\'s (unrealistic) synchronous rejection it fires, and ONLY the P2-150 test drives '
          'that -- the 14 normal tests stay green, which is why that test exists',
     '                string legNote = "Exit-leg acceptance is not known at submission; read the stop/target "\n'
     '                    + "order ids for the live state.";\n'
     '                result.Note = string.IsNullOrEmpty(result.Note) ? legNote : result.Note + " " + legNote;',
     '                if (stopOrder != null && (stopOrder.OrderState == OrderState.Rejected || stopOrder.OrderState == OrderState.Cancelled))\n'
     '                    result.Status = "partial_submit";'),

    # ---- group 3: the caller is told why ----------------------------------------------------
    (ATM, 'group 3: the pending-legs note is dropped, so the caller gets a bare "pending_legs" '
          'with no instruction to read the leg ids -- a status with no remedy',
     '                result.Note = string.IsNullOrEmpty(result.Note) ? legNote : result.Note + " " + legNote;',
     '                result.Note = result.Note;'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # Encoding PINNED -- without it a non-ASCII byte raises mid-write, leaving a live mutant while
    # the battery reports restored. [[a-battery-must-reach-its-restore-line]].
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
print(chr(10) + 'restored originals;', run())
_battery.finish(survivors, MUTANTS)
