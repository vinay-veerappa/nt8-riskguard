"""Mutation battery for P0-180 (an AutoStop rejected by the guard's own arbiter).

The defect: `EvaluateGraceExpiry` reserved the FSM to `ProtectedPending` BEFORE the
action it emitted reached the arbiter, and `ValidateInvariant` rejects a
`PlaceStopOrder` in that state -- so the guard rejected its own first stop and the
position stayed naked. Suite-green for the life of the feature because grace-expiry,
the arbiter and the executor were each driven in isolation; nothing carried the SAME
action from emission through the arbiter. Caught live on Sim101 2026-08-20.

The fix removed the premature reserve (GraceEmitted already suppresses re-emission) and
left the real reserve-before-submit in ExecuteAction, AFTER the arbiter. These mutants
each re-introduce a way for the guard to reject or mis-handle its own protective stop;
`TestP0180_GraceExpiryAutoStopSurvivesItsOwnArbiter` must kill every one.

  * MUTANT 1 puts the premature `ProtectedPending` reserve back in EvaluateGraceExpiry --
    the exact live defect. P0-180 kills it because the arbiter then rejects the stop and
    no CreateOrder reaches the broker.

  * MUTANT 2 widens the arbiter to also reject `Unprotected`. Now even the corrected flow
    is refused; P0-180's admit-and-create assertions fail.

  * MUTANT 3 has the executor's reserve-before-submit set `Unprotected` instead of
    `ProtectedPending`. The stop is still placed, but the FSM no longer records the
    protection it just reserved -- P0-180's final assertion (and P0-3's T2) catch it.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- MUTANT 1: the exact live defect -- pre-reserve ProtectedPending before the arbiter ----
    (GUARD,
     "EvaluateGraceExpiry pre-reserves ProtectedPending before the arbiter, so the guard\n"
     "     rejects its own first stop -- the P0-180 live defect, verbatim",
     '                        RuleId = "MISSING_STOP_ATTACH"\n'
     '                    });\n'
     '                    // P0-180: do NOT reserve ProtectedPending here. This ran BEFORE the arbiter,',
     '                        RuleId = "MISSING_STOP_ATTACH"\n'
     '                    });\n'
     '                    fsm.State = GuardFsmState.ProtectedPending;\n'
     '                    // P0-180: do NOT reserve ProtectedPending here. This ran BEFORE the arbiter,'),

    # ---- MUTANT 2: the arbiter also rejects Unprotected, refusing the corrected flow ----
    (GUARD,
     "the arbiter widens to reject Unprotected too, so even the corrected flow is refused",
     '                if (fsm.State == GuardFsmState.Protected || fsm.State == GuardFsmState.ProtectedPending)',
     '                if (fsm.State == GuardFsmState.Protected || fsm.State == GuardFsmState.ProtectedPending || fsm.State == GuardFsmState.Unprotected)'),

    # ---- MUTANT 3: the executor reserve records the wrong state ----
    (GUARD,
     "the executor's reserve-before-submit records Unprotected, so the FSM does not track the\n"
     "     protection it just placed",
     '                        localFsm.State = GuardFsmState.ProtectedPending;\n'
     '                        reserved = true;',
     '                        localFsm.State = GuardFsmState.Unprotected;\n'
     '                        reserved = true;'),
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
    # P2-148: a crash is NOT a detection. Require at least one [FAIL] before a missing
    # result line is scored a kill.
    if not m and '[FAIL]' not in ((res.stdout or '') + (res.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINALS = {path: open(path, encoding='utf-8').read() for path in (GUARD,)}

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
for path, name, old, new in MUTANTS:
    original = ORIGINALS[path]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(path, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    killed = _battery.score(res, run)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(path, 'w', encoding='utf-8', newline='').write(original)

for path, original in ORIGINALS.items():
    open(path, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored originals;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
