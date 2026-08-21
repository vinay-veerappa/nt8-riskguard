"""Mutation battery for P2-101: a shadow lockout retried its flatten forever.

⚠️ ONE ALARM THAT COULD NOT STOP AND ONE THAT COULD NOT START, IN THE SAME BLOCK.

The lockout phase machine re-emits its flatten while the position is open. In `shadow`,
`ProcessAction` answers "SHADOW (SKIPPED)" for every action, so the position cannot close, so the
exit condition is permanently true. Measured on the deployed box 2026-08-14: a
`LOCKOUT_FLATTEN_RETRY` plus a `SHADOW_ACTION` every 5 seconds, on three sim accounts AND the
funded 50K TPT PRO, indefinitely -- about 12 lines per minute per account into
`interventions.jsonl`. That file is the audit record, both of that session's live findings came out
of it, and this was burying it.

THE GENERAL RULE, and it is worth grepping for elsewhere: A RETRY WHOSE EXIT CONDITION IS AN ACTION
THE CURRENT MODE DOES NOT PERFORM WILL NEVER EXIT.

⚠️ The second half is the sharper one. `LOCKOUT_STUCK` -- the warning that exists to tell an
operator the guard is not getting the position closed -- read:

    UtcNow > stateModel.LastLockoutFlattenAttempt.AddSeconds(30)

while the retry immediately above it set `LastLockoutFlattenAttempt = UtcNow` every 5 seconds. The
interval it measured was reset by the loop it was watching, so it could never reach 30. Thirteen
rounds of retries produced ZERO stuck lines. Both are now keyed on the attempt COUNT, from one
method (`LockoutPhaseAttemptBudget`), so the retry and the give-up cannot drift apart.

What each mutant defends:

  * MUTANT 1 restores the shipped defect: the flatten retry loses its budget check and streams
    forever. Killed by the only tests here that sweep the same unclosable position more than twice.

  * MUTANT 2 is THE PARTIAL FIX: one budget for every mode. It bounds the loop -- the log stops
    growing without limit, which is the visible symptom -- and still emits six identical
    observations in shadow, where the first one is the entire product. Bounding a loop is not the
    same as knowing why it could not exit.

  * MUTANT 3 sets the budget to zero, which is the fail-OPEN direction: nothing is ever attempted,
    so a live lockout stops flattening anything. The cheapest way to make a noisy loop quiet.

  * MUTANT 4 stops EnterLockoutPhase resetting the count, so PendingFlatten inherits the cancel
    phase's spent budget and the position gets no flatten attempt at all.

  * MUTANT 5 is a DECLARED EXPECTED SURVIVOR, and the declaration is the finding. Dropping the
    reset from ResetLockoutPhase changes nothing observable, because every route back into a phase
    goes through EnterLockoutPhase, which resets on entry -- that is mutant 4, and it dies. The
    lines stay anyway: that method's contract is "everything the phase machine owns", and a reset
    clearing three of four fields is how the fourth gets forgotten. A surviving mutant does not
    always mean a missing test; P1-99's battery taught the same thing, and the answer there was
    also to say so rather than contrive an assertion.

  * MUTANT 6 never sets LockoutStuckLogged, so the give-up warning repeats every sweep -- the
    original defect moved from the retry to the alarm about the retry.

  * MUTANT 7 restores the unreachable stuck condition, keyed on an interval the retry resets. It
    is the one that proves the new warning can actually FIRE, which the old one never could.

A crash counts as a kill (handover section 5.14).
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
ADDON = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
# P2-29: one anchor below moved to RiskGuardModels.cs when the independent top-level
# types left RiskGuardAddOn.cs (a MOVE, not a rewrite -- they are their own types, not
# members of RiskGuardAddOn). This battery was single-file; every mutant now names its
# own file, because a battery that GUESSES which file holds an anchor is exactly the
# ambiguity check_anchors.py exists to remove.
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    (ADDON,
     "the SHIPPED DEFECT: the flatten retry loses its budget and streams forever while the\n"
     "     position stays open -- which in shadow is always",
     '                    if (DateTime.UtcNow > stateModel.LastLockoutFlattenAttempt.AddSeconds(5)\n'
     '                        && stateModel.LockoutPhaseAttempts < LockoutPhaseAttemptBudget())',
     '                    if (DateTime.UtcNow > stateModel.LastLockoutFlattenAttempt.AddSeconds(5))'),

    (ADDON,
     "THE PARTIAL FIX: one budget for every mode. The log stops growing without limit -- the\n"
     "     visible symptom -- and shadow still emits six identical observations where the first is\n"
     "     the whole product",
     '            return IsActingMode() ? 6 : 1;',
     '            return 6;'),

    (ADDON,
     "the budget is ZERO, the fail-OPEN direction: the quietest possible loop, and a live lockout\n"
     "     that flattens nothing",
     '            return IsActingMode() ? 6 : 1;',
     '            return 0;'),

    (ADDON,
     "entering a phase no longer resets the count, so PendingFlatten inherits the cancel phase's\n"
     "     spent budget and the position never gets a flatten attempt",
     '            stateModel.CurrentLockoutPhase = phase;\n'
     '            stateModel.LockoutPhaseAttempts = 0;',
     '            stateModel.CurrentLockoutPhase = phase;'),

    (MODELS,
     "EXPECTED SURVIVOR: the count survives an unlock. UNKILLABLE BY CONSTRUCTION, and the\n"
     "     reason is worth reading rather than testing around: every route back into a phase\n"
     "     goes through EnterLockoutPhase, which resets the count on entry, so a lockout can\n"
     "     never observe a stale one whatever ResetLockoutPhase does. Those two lines stay\n"
     "     anyway -- that method's contract is 'everything the phase machine owns', and a\n"
     "     reset clearing three of four fields is how the fourth gets forgotten. MUTANT 4\n"
     "     covers the reset that IS load-bearing. If a change to EnterLockoutPhase ever makes\n"
     "     this reachable, this battery FAILS on the stale declaration and says so",
     '            InitialLockoutFlattened = false;\n'
     '            LockoutPhaseAttempts = 0;',
     '            InitialLockoutFlattened = false;'),

    (ADDON,
     "the give-up warning never records that it fired, so it repeats every sweep: the original\n"
     "     defect moved from the retry to the alarm about the retry",
     '                stateModel.LockoutStuckLogged = true;',
     '                stateModel.LockoutStuckLogged = false;'),

    (ADDON,
     "the UNREACHABLE stuck condition returns -- keyed on an interval the retry resets every 5s,\n"
     "     so the one alarm that would tell an operator the position is not closing never fires",
     '            bool exhausted = stateModel.LockoutPhaseAttempts >= LockoutPhaseAttemptBudget();',
     '            bool exhausted = DateTime.UtcNow > stateModel.LastLockoutFlattenAttempt.AddSeconds(30);'),
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


ORIGINALS = {p: open(p, encoding='utf-8').read() for p in (ADDON, MODELS)}

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
    if ORIGINALS[path].count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, ORIGINALS[path].count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(path, 'w', encoding='utf-8', newline='').write(ORIGINALS[path].replace(old, new))
    res = run()
    killed = _battery.score(res, run)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    [open(q, 'w', encoding='utf-8', newline='').write(t) for q, t in ORIGINALS.items()]

[open(q, 'w', encoding='utf-8', newline='').write(t) for q, t in ORIGINALS.items()]
print('\nrestored original;', run())
_battery.finish(survivors, MUTANTS)
