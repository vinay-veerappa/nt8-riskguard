"""Mutation battery for P1-156: arming ON START seeds FSMs for already-open positions.

MEASURED LIVE on the funded account `TAKEPROFITPRO524207503` 2026-08-18, minutes after deploying
v1.45.0: `nt_riskguard_state` returned ZERO FSMs while the account held MNQ SEP26 **Short 6**, with
`nt_health` reporting the guard loaded, `shadow`, `isArmed: true`, `guarding: true`. Armed, and
covering nothing. Found by checking coverage after a deploy rather than by any test or gate.

The event order after a recompile is the whole defect:

    SUBSCRIBE          isArmed:false    <- SeedFsmsForExistingPositions runs HERE, but the broker
                                           has not delivered positions yet, so it seeds nothing
    CONNECTION_CHANGE  Connected        <- positions arrive; AuditPosition ->
                                           ExecutePositionUpdateDetails -> UpdateFsmOnPosition ...
    INITIALIZE
    ARMED_ON_START     isArmed:true     <- ... which returned early on `if (!_isArmed) return;`

Two guards conspire. `SubscribeToAccount` early-returns on `_subscribedAccounts.Contains`, so the
connection-change re-subscribe is a no-op and the seeding inside it never re-runs. And a STATIC
position generates no further position update, so nothing seeds it afterwards -- the gap persists
for the life of the trade.

⚠️ THIS IS `P1-15` THROUGH A DIFFERENT DOOR, AND THAT IS THE LESSON WORTH MORE THAN THE FIX.
`P1-15` added seeding to the RE-ARM path (`ToggleArmed`) for precisely this reason, with a test and
a comment explaining that otherwise "the guard is armed and reports healthy while covering
nothing". `ApplyInitialArmState` -- the OTHER path that sets `_isArmed = true` -- never learned the
same clause. [[a-second-reader-of-the-same-state]]: a predicate learns a clause and the other
readers never do. Count the sites before closing the ticket.

THE GROUPS BELOW:

  1. THE SEEDING HAPPENS AT ALL. The defect, restored.
  2. ⚠️ IT HAPPENS ON THE ARMED PATH ONLY, AND AFTER ARMING. Seeding before `_isArmed = true`, or
     on the disarmed branch, is a fix that looks right and does nothing -- the FSM paths return
     early while disarmed, which is the very reason the gap exists.
  3. THE SEED COVERS EVERY SUBSCRIBED ACCOUNT, not the first one it finds. 97 accounts exist on
     this box and the funded one is not first.
"""
import os, re, subprocess, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the seeding happens at all ------------------------------------------------
    (GUARD, 'group 1: arm-on-start stops seeding entirely -- the measured defect, an armed guard '
            'with zero FSMs against a live Short 6 on a funded account',
     '                foreach (var accName in _subscribedAccounts)\n'
     '                {\n'
     '                    var seedAccount = Account.All.FirstOrDefault(a => a.Name == accName);\n'
     '                    if (seedAccount != null) SeedFsmsForExistingPositions(seedAccount);\n'
     '                }',
     '                // seeding removed'),

    (GUARD, 'group 1: the seed is called but its RESULT is discarded by looking up nothing -- the '
            'loop runs, the call never happens, and a source scan still finds the line',
     '                    if (seedAccount != null) SeedFsmsForExistingPositions(seedAccount);',
     '                    if (seedAccount == null) SeedFsmsForExistingPositions(seedAccount);'),

    # ---- group 2: on the armed path, AFTER arming -------------------------------------------
    (GUARD, 'group 2: the seed moves to the DISARMED branch, where the FSM paths return early on '
            '!_isArmed -- a fix that reads correctly and does nothing, which is how this gap '
            'existed in the first place',
     '            if (_isArmed)\n'
     '            {\n'
     '                // P1-156.',
     '            if (!_isArmed)\n'
     '            {\n'
     '                // P1-156.'),

    # ---- group 3: every subscribed account --------------------------------------------------
    (GUARD, 'group 3: only the FIRST subscribed account is seeded. 97 accounts exist on this box '
            'and the funded one is not first, so the account that matters is the one missed',
     '                    if (seedAccount != null) SeedFsmsForExistingPositions(seedAccount);\n'
     '                }',
     '                    if (seedAccount != null) { SeedFsmsForExistingPositions(seedAccount); break; }\n'
     '                }'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # ⚠️ Encoding PINNED: a cp1252 default raises part-way through on a non-ASCII byte, between
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
for target, name, old, new in MUTANTS:
    original = ORIGINALS[target]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    try:
        res = run()
        mm = re.search(r'Failed = (\d+)', res)
        undetected_crash = 'NO ASSERTION FAILED' in res
        killed = (not undetected_crash) and (
            ('BUILD FAILED' in res) or ('NO RESULT LINE' in res)
            or (mm is not None and int(mm.group(1)) > 0))
        print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
        if not killed:
            survivors.append(name)
    finally:
        restore()

restore()
print(chr(10) + 'restored originals;', run())

if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
