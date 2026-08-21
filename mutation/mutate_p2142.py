"""Mutation battery for P2-142: a deliberate DISARM survives, a persisted ARM still does not.

MEASURED: 84 `ARMED_ON_START` events in one 3 MB tail of `interventions.jsonl`, alongside 84
`INITIALIZE` and 171 `CONNECTION_CHANGE` -- every one a RECOMPILE rather than a restart, several
from an unrelated repo deploying NinjaScript. In `shadow` that is noise. In `live` it means the
guard re-arms itself minutes after an operator disarmed it, with no symptom other than a log line
that already appears 84 times.

The operator's rule is that ALL configuration is persistent, so the disarm has to survive.

⚠️ THE ASYMMETRY IS THE DESIGN, AND IT IS THE THING MOST LIKELY TO BE "TIDIED" AWAY. `FR-30/31`
deliberately refuses to rehydrate `_isArmed`, in writing, because a persisted `true` re-arming an
acting mode is how a guard comes to act on stale intent. So only the DISARM direction is honoured.
Two mutants below make the rule symmetrical -- in each direction -- because a future reader will
see two halves of one fact and reach for one line. The two directions carry OPPOSITE risk: a
wrongly-restored ARM makes a guard act on stale intent, a wrongly-restored DISARM only declines to
act. [[configured-evaluated-enforcing]].

THE GROUPS BELOW:

  1. THE DISARM IS HONOURED. Mutants that lose it -- the whole defect, restored.
  2. ⚠️ THE ARM IS STILL NOT HONOURED. `FR-30/31` must not be collateral damage.
  3. ⚠️ IT IS ACTUALLY PERSISTED. A field set in memory and never written satisfies every
     in-process test and is still lost by the recompile this entry is about. Configured but not
     persisted looks exactly like protection that does not exist.
  4. THE INTENT IS RECORDED AND CLEARED. A disarm that is never recorded cannot be honoured; one
     that is never cleared outlives the decision to undo it.
  5. RECOMPILE vs RESTART. A pid alone is not identity -- pids are RECYCLED -- so the start time
     is what makes it the same process. The unknown case must claim less, not more.
"""
import os, re, subprocess, sys


# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # ---- group 1: the disarm is honoured ----------------------------------------------------
    (GUARD, 'group 1: the persisted disarm is not consulted at all, which is the state the defect '
            'was FOUND in -- the guard re-arms itself after somebody else recompiles',
     '            if (_operatorDisarmedUtc.HasValue)',
     '            if (false)'),

    (GUARD, 'group 1: the disarm is consulted, logged, and then NOT applied -- the branch reports '
            'an unarmed guard and leaves it armed. A gate that is COMPUTED is not a gate that is '
            'USED, which has beaten four source checks in this project',
     '                _isArmed = false;\n'
     '                // Deliberately its own event, not UNPROTECTED_ON_START.',
     '                // Deliberately its own event, not UNPROTECTED_ON_START.'),

    (GUARD, 'group 1: the load stops rehydrating the disarm, so it is written to the state file and '
            'never read back -- persisted and inert',
     '                            _operatorDisarmedUtc = data.OperatorDisarmedUtc;',
     '                            _operatorDisarmedUtc = null;'),

    # ---- group 2: the arm is STILL not honoured ---------------------------------------------
    (GUARD, 'group 2: the rule is made SYMMETRICAL by rehydrating the armed flag too, which is '
            'exactly what FR-30/31 forbids -- a persisted `true` re-arms an acting mode',
     '                            _isArmed = false;\n'
     '                            // P2-142: the deliberate DISARM is rehydrated',
     '                            _isArmed = data.IsArmed;\n'
     '                            // P2-142: the deliberate DISARM is rehydrated'),

    (GUARD, 'group 2: the disarm branch arms instead of disarming -- the symmetry error in the '
            'other direction, where the recorded intent is honoured with its sign flipped',
     '            if (_operatorDisarmedUtc.HasValue)\n'
     '            {\n'
     '                _isArmed = false;',
     '            if (_operatorDisarmedUtc.HasValue)\n'
     '            {\n'
     '                _isArmed = true;'),

    # ---- group 3: it is actually persisted --------------------------------------------------
    (MODELS, 'group 3: the persisted field is dropped from the model, so the disarm lives only in '
             'memory and is lost by the very recompile this entry is about',
     '        public DateTime? OperatorDisarmedUtc { get; set; }',
     '        [Newtonsoft.Json.JsonIgnore] public DateTime? OperatorDisarmedUtc { get; set; }'),

    (GUARD, 'group 3: the capture stops writing the disarm, so it survives in this process and '
            'dies with it -- configured, evaluated, and not persisted',
     '                        OperatorDisarmedUtc = _operatorDisarmedUtc,',
     '                        OperatorDisarmedUtc = null,'),

    # ---- group 4: the intent is recorded and cleared ----------------------------------------
    (GUARD, 'group 4: disarming no longer RECORDS the intent, so there is nothing to honour and the '
            'whole mechanism is dead on the only path that sets it',
     '                _operatorDisarmedUtc = _isArmed ? (DateTime?)null : DateTime.UtcNow;',
     '                _operatorDisarmedUtc = null;'),

    (GUARD, 'group 4: arming no longer CLEARS the intent, so a disarm outlives the operator '
            'deciding to undo it and the guard comes up disarmed after being armed on purpose',
     '                _operatorDisarmedUtc = _isArmed ? (DateTime?)null : DateTime.UtcNow;',
     '                _operatorDisarmedUtc = DateTime.UtcNow;'),

    # ---- group 5: recompile vs restart ------------------------------------------------------
    (GUARD, 'group 5: the start time is ignored, so a RECYCLED pid reads as the same process and a '
            'genuine restart is reported as a recompile',
     '            if (Math.Abs((recordedStartUtc.Value - currentStartUtc).TotalSeconds) > 1.0)\n'
     '                return "a RESTART";',
     '            if (false)\n'
     '                return "a RESTART";'),

    (GUARD, 'group 5: an unrecorded host claims a RECOMPILE rather than a restart -- the unknown '
            'case must claim LESS, since an unknown process is more likely a new one',
     '            if (recordedPid == 0 || !recordedStartUtc.HasValue) return "a RESTART";',
     '            if (recordedPid == 0 || !recordedStartUtc.HasValue) return "a RECOMPILE";'),

    (GUARD, 'group 5: every start is a RECOMPILE, so the distinction the 84 log lines needed is '
            'reported but meaningless -- [[a-green-that-can-never-be-red]] applied to a message',
     '            if (recordedPid != currentPid) return "a RESTART";',
     '            if (false) return "a RESTART";'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # ⚠️ The encoding is PINNED. Without it the write uses the platform default (cp1252 here) and
    # raises part-way through on any non-ASCII byte, leaving a MUTANT on disk while the battery
    # reports having restored. [[a-battery-must-reach-its-restore-line]].
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

    # P2-148 / P1-153: a crash is not a detection. The harness prints its result line last, so an
    # unhandled exception used to leave 'NO RESULT LINE' and score as KILLED with nothing having
    # objected. A throwing test now prints [FAIL] and the run continues, which separates the cases.
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

# Plain exit rule, not _battery.finish: this battery declares no EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions -- reaching for the
# helper without a declaration removes the prompt to justify the next exemption someone adds.
if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
