"""Mutation battery for P1-173: an active loss cooldown survives a recompile.

`CooldownUntil` is written on a consecutive-loss breach, read in `EvaluateRules` as the gate that
raises `COOLDOWN_BREACH` -> `FlattenPosition`, cleared by the session reset -- and was absent from
`AccountPersistedData` entirely. A restart, a recompile or a hot-swap set it to `DateTime.MinValue`,
so the rule could not fire for the remainder of a cooldown that was supposed to be running.

⚠️ THE ACTION THAT DEFEATED IT IS ONE THE OPERATOR ALREADY PERFORMS. The cooldown exists to
interrupt revenge trading after a run of losses, and NinjaScript's recompile button cleared it. Six
recompiles happened on this box on the day it was found, none of them for that reason.
[[a-successful-compile-wipes-static-state]].

FOUND BY A GATE, NOT BY READING THE CODE. `tools/check_account_state_persisted.py` was written for
`P1-170` and flagged this on its first run. Nothing was wrong with any line of the cooldown logic:
the defect was an OMISSION from a class, and an omission has no source location for a reviewer to
look at. That is the one defect shape a gate is strictly better at catching than a person.

WHY A BATTERY FOR THREE ASSIGNMENTS. Because a persisted deadline has two independent failure
directions and the tests for them look nearly identical:

  * not restored -> the defect, unchanged, and every test that asserts something is NOT flattened
    still passes;
  * restored WRONG -> re-armed rather than restored, so an account that has already served its
    cooldown is flattened for it after a restart. That is the direction that hurts the operator,
    and it is what the expired-cooldown control exists to catch. [[a-lockout-must-not-trap-you]].

THE GROUPS BELOW:

  1. IT IS PERSISTED AND RESTORED AT ALL, and the restored value still ENFORCES. A value that is
     read back but reaches no rule is [[configured-evaluated-enforcing]] again.
  2. IT IS RESTORED, NOT RE-ARMED. A deadline in the past stays in the past.

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: persisted, restored, and still enforcing -----------------------------------
    (GUARD, 'group 1: the restore is removed -- P1-173 exactly as measured. A recompile clears the '
            'cooldown, COOLDOWN_BREACH cannot fire for the rest of it, and the operator defeats '
            'the rail by pressing the button they already press',
     '                                    state.CooldownUntil = kvp.Value.CooldownUntil;',
     '                                    _ = kvp.Value.CooldownUntil;'),

    (GUARD, 'group 1: the SAVE stops writing it, so the restore reads a default. The restore line '
            'is present and correct and the field is in AccountPersistedData -- every source check '
            'that looks for either passes, and the behaviour is the defect. Written to nowhere is '
            'the shape [[dead-safety-machinery-gate]] exists for',
     '                            CooldownUntil = state.CooldownUntil,   // P1-173',
     '                            CooldownUntil = default(DateTime),   // P1-173'),

    (GUARD, 'group 1: restored from the LIVE state object rather than the persisted record, which '
            'on a freshly constructed AccountState is MinValue. The line exists, names the right '
            'field, and restores nothing',
     '                                    state.CooldownUntil = kvp.Value.CooldownUntil;',
     '                                    state.CooldownUntil = state.CooldownUntil;'),

    # ---- group 2: restored, not re-armed ----------------------------------------------------
    (GUARD, 'group 2: the deadline is RE-ARMED on restore instead of restored -- every restart '
            'starts a fresh cooldown from now. An account that has served its time is flattened '
            'for it, and a restart loop becomes a permanent cooldown. This is the failure '
            'direction that hurts the operator, and only the expired-cooldown control sees it. '
            '[[a-lockout-must-not-trap-you]]',
     '                                    state.CooldownUntil = kvp.Value.CooldownUntil;',
     '                                    state.CooldownUntil = DateTime.UtcNow.AddMinutes(15);'),

    (GUARD, 'group 2: a past deadline is clamped forward to now, which reads as harmless and is '
            'not: it converts "already served" into "expires this instant", and any evaluation '
            'racing that instant flattens a position on an account with no live cooldown',
     '                                    state.CooldownUntil = kvp.Value.CooldownUntil;',
     '                                    state.CooldownUntil = kvp.Value.CooldownUntil > DateTime.UtcNow\n'
     '                                        ? kvp.Value.CooldownUntil : DateTime.UtcNow.AddSeconds(30);'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # Encoding PINNED: a cp1252 default raises part-way through on a non-ASCII byte, between
    # applying a mutant and restoring it. [[a-battery-must-reach-its-restore-line]].
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
    # P2-148 / P1-153: a crash is not a detection.
    if not m and '[FAIL]' not in out:
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return result


baseline = run()
print('=== baseline ===\n  %s' % baseline)
if 'Failed = 0' not in baseline:
    print('baseline is RED; a battery against a red baseline scores nothing')
    sys.exit(2)

survivors = []
try:
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
finally:
    # The pin above closes the failure that has actually happened twice; this closes the class.
    restore()

print(chr(10) + 'restored originals;', run())

# Plain exit rule, not _battery.finish: this battery declares no EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions.
if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
