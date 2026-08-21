"""Mutation battery for P2-155: the ATM monitor latch was per-INSTANCE, so a hot-swap orphaned it.

`_monitoring`/`_monitorTimer` live on the DynamicAtmManager singleton. An NT8 recompile wipes the
statics, so the Lazy<> singleton is rebuilt: a NEW manager becomes Instance and restores the brackets
from disk, while the OLD manager's System.Threading.Timer -- rooted by the runtime's timer queue, not
by the wiped static field -- keeps firing every 5s against a stale _activeBrackets and double-manages
the same broker orders the new Instance now owns. [[a-successful-compile-wipes-static-state]].

The fix: the timer callback refuses to sweep unless `this` is the current Instance, and a superseded
manager disposes its own timer so the orphan self-terminates within one tick.

THE GROUPS:

  1. THE GUARD COMPARES AGAINST Instance. Invert it, or make it a tautology, and a superseded manager
     sweeps again -- the defect verbatim. Both die because the orphan test asserts the stop did NOT
     move.
  2. THE GUARD ACTUALLY STOPS THE SWEEP. Drop the `return` after the self-terminate and the orphan
     falls through into the sweep it was meant to skip -- self-terminated AND still managing.
  3. THE ORPHAN REALLY LETS GO. Skip `_monitoring = false` and it never re-arms cleanly; skip
     `_monitorTimer = null` and it keeps a disposed timer. Each is asserted directly, because a
     superseded manager that still reads as monitoring is a half-fix that looks whole.

⚠️ Every other ATM test drives MonitorTickCore directly, which by design does NOT check supersession,
so a guard that never fired would pass all of them. Only TestAtm_P2155_ASupersededManagerStopsSweeping
drives the FULL callback -- these mutants are why it had to.
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')

MUTANTS = [
    # ---- group 1: the guard compares against the current owner ------------------------------
    (ATM, 'group 1: the supersession guard is INVERTED, so the current owner stops sweeping and an '
          'orphan sweeps on -- the exact double-management the fix removes. Dies: the orphan moves the '
          'stop the new manager already owns',
     '            if (!ReferenceEquals(this, _activeManager))',
     '            if (ReferenceEquals(this, _activeManager))'),

    (ATM, 'group 1: the guard is made a TAUTOLOGY (compares this to this, not to _activeManager), so '
          'it is always false and no manager is ever treated as superseded -- the orphan sweeps',
     '            if (!ReferenceEquals(this, _activeManager))',
     '            if (!ReferenceEquals(this, this))'),

    (ATM, 'group 1: the constructor stops claiming ownership (_activeManager left null), so EVERY '
          'manager reads as superseded and no sweep ever runs -- dies across the P2-112 tests, which '
          'drive the full callback on the current manager and expect the sweep to run',
     '            _activeManager = this;',
     '            _activeManager = null;'),

    # ---- group 2: the guard actually stops the sweep ----------------------------------------
    (ATM, 'group 2: the `return` after self-terminating is dropped, so a superseded manager stops its '
          'timer and then falls through into the very sweep it was meant to skip -- it moves the stop '
          'anyway on this tick',
     '                StopMonitorBecauseSuperseded();\n                return;',
     '                StopMonitorBecauseSuperseded();'),

    # ---- group 3: the orphan really lets go -------------------------------------------------
    (ATM, 'group 3: the orphan never clears _monitoring, so it still reads as monitoring after '
          'self-terminating -- a later EnsureMonitor sees monitoring==true and refuses to re-arm',
     '            _monitoring = false;\n            Timer t = _monitorTimer;',
     '            Timer t = _monitorTimer;'),

    (ATM, 'group 3: the orphan disposes the timer but keeps the field, holding a disposed timer '
          'reference instead of dropping it',
     '            Timer t = _monitorTimer;\n            _monitorTimer = null;',
     '            Timer t = _monitorTimer;'),
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

# Plain exit, NOT _battery.finish: every mutant here must die (no EXPECTED SURVIVOR), and
# tools/check_expected_survivors.py requires a battery reaching for finish() to declare one.
print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
