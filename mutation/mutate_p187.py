"""Mutation battery for P1-87 (an unrecognised stop action must not mean silence).

The dispatch compared OnMissing against two exact literals with no else, so any
other value -- a lower-case "flatten", a typo, an empty string, or the "WarnOnly"
the declaration advertised -- emitted NO ACTION for a position with no stop.

⚠️ This defect was found by a mutant SURVIVING, not by review: mutate_p184's
mutant 3 changed OnMissing from "Flatten" to "AutoStop" and all 1180 tests stayed
green. And a test in this suite ASSERTED the defect as correct behaviour
("No action generated when OnMissing is WarnOnly"), so the suite was not merely
silent about it -- it was defending it.

What each group is defending:

  * MUTANT 1 restores the `else if (== "Flatten")`, which is the defect exactly.

  * MUTANT 2 is the interesting one. It makes the fallback do nothing while
    KEEPING the else branch, so the shape of the fix survives and the behaviour
    does not. A reviewer skimming the diff sees an else and moves on.

  * MUTANT 3 gives the fallback its own RuleId. Everything passes and the log is
    now split across two names for one outcome, which makes one of them
    unfindable afterwards -- the same reasoning that keeps the two group-refusal
    events separate in the copier.

  * MUTANT 4 removes the preflight check. The position is still protected, so
    every dispatch test stays green, and the operator is never told their
    configured action is not the one in force.

  * MUTANT 5 keeps the preflight check but drops the offending value from the
    message. The refusal is correct and useless: "unrecognised value" without the
    value is not actionable, which is UI7's finding in another place.

  * MUTANT 6 puts "WarnOnly" back in the settings dropdown. Nothing breaks at
    runtime -- preflight now catches it -- but a surface is offering an action the
    guard has never implemented, which is how it got into a config file in the
    first place.

⚠️ WHAT IS NOT MUTATED, and it is a real gap. Making the fallback place an
AutoStop instead of flattening would survive: the tests require a PROTECTIVE
action, not specifically a flatten. That is deliberate -- pinning the exact
fallback would duplicate the OnMissing dispatch tests -- but it means the CHOICE
of Flatten as the fallback rests on the comment beside it, not on a test.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red
baseline.
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


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
# P2-29 REPOINTED ONE ANCHOR HERE. The settings dropdown moved to its own file when the ~720-line
# WPF dashboard left RiskGuardAddOn.cs; the find-string did not change, the FILE did. That made
# every entry below a 4-tuple, because a battery with two file constants and no explicit target
# per mutant has no unambiguous default -- and check_anchors.py refuses what it cannot read
# rather than printing `ok` over it.
#
# The anchor was REPOINTED, NOT RETIRED. It is the only mutant defending a UI surface from
# offering an action the guard has never implemented, which is how "WarnOnly" reached a config
# file in the first place. Deleting it because a refactor moved the line would have traded a
# defect's only guard for the convenience of not editing this file.
WINDOW = os.path.join(REPO, 'addons', 'RiskGuardWindow.cs')

MUTANTS = [
    (GUARD,
     "the else branch goes back to `else if (== \"Flatten\")`, so every other spelling emits\n"
     "     NO ACTION for a position with no stop -- the defect, restored",
     '                else\n                {\n                    // P1-87.',
     '                else if (_config.StopGuard.OnMissing == "Flatten")\n                {\n                    // P1-87.'),

    (GUARD,
     "the else branch STAYS but stops adding the action. The shape of the fix survives and\n"
     "     the behaviour does not -- a reviewer skimming the diff sees an else and moves on",
     '                    actions.Add(new GuardAction\n'
     '                    {\n'
     '                        AccountName = account.Name,\n'
     '                        ActionType = GuardActionType.FlattenPosition,',
     '                    if (false) actions.Add(new GuardAction\n'
     '                    {\n'
     '                        AccountName = account.Name,\n'
     '                        ActionType = GuardActionType.FlattenPosition,'),

    (GUARD,
     "the fallback gets its own RuleId. Everything passes, and one outcome is now split\n"
     "     across two names in a log that is grepped by RuleId -- so one of them is\n"
     "     unfindable after the fact",
     '                        RuleId = "MISSING_STOP_FLATTEN"',
     '                        RuleId = "MISSING_STOP_UNRECOGNISED_ACTION"'),

    (GUARD,
     "the preflight check is removed. The position is still protected, so every dispatch\n"
     "     test stays green -- and the operator is never told the action they configured is\n"
     "     not the one in force",
     '            if (onMissing != "AutoStop" && onMissing != "Flatten")',
     '            if (false)'),

    (GUARD,
     "preflight still refuses, but the message drops the offending value. Correct and\n"
     "     useless: 'unrecognised value' without the value is not actionable, which is UI7's\n"
     "     finding told in another place",
     'result.Fail("STOP_GUARD_ON_MISSING", $"Unrecognised StopGuard.OnMissing value \'{onMissing}\'");',
     'result.Fail("STOP_GUARD_ON_MISSING", "Unrecognised StopGuard.OnMissing value");'),

    (WINDOW,
     "WarnOnly goes back in the settings dropdown. Nothing breaks at runtime now that\n"
     "     preflight catches it -- but a surface is again OFFERING an action the guard has\n"
     "     never implemented, which is how it reached a config file to begin with",
     '            _onMissingCombo.Items.Add("Flatten");',
     '            _onMissingCombo.Items.Add("Flatten");\n            _onMissingCombo.Items.Add("WarnOnly");'),
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


# P2-29: two target files now, so the originals are a dict keyed by path. Restoring ALL of them
# after every mutant, not just the one touched: a battery killed mid-run leaves a live mutant in
# the tree, and the suite then fails naming a feature nobody edited.
ORIGINALS = {}
for _target, _, _, _ in MUTANTS:
    if _target not in ORIGINALS:
        ORIGINALS[_target] = open(_target, encoding='utf-8').read()


def restore():
    for _path, _text in ORIGINALS.items():
        open(_path, 'w', encoding='utf-8', newline='').write(_text)

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
for target, name, old, new in MUTANTS:
    original = ORIGINALS[target]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    restore()

restore()
print('\nrestored originals;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
