"""Mutation battery for P1-82 (a switch whose rule cannot fire must not default ON).

The change itself is four literals, which is exactly why it needs a battery: a
four-literal diff is the kind that gets reviewed by eye, half-applied, and
reverted by the next person who "restores a sensible default".

What each group is defending:

  * MUTANTS 1-2 flip the two PROPERTY initializers back. This is the whole defect
    restored, and it is here mostly to prove the gate fires at all -- a battery
    whose obvious mutant survives is measuring nothing.

  * MUTANTS 3-4 are the ones this file exists for. They flip only the PARSER's
    fallback, leaving the property at false. Every config file on this box
    predates both fields, so the parser fallback is what actually runs in
    production -- and the class gate (TestP182_AFlagThatCannotFireMustNotDefaultOn)
    constructs a config with `new`, so it CANNOT see this. Only the
    two-copies-agree test can. If mutant 3 or 4 survives, the fix is cosmetic:
    green in the suite, unchanged on the operator's box.

  * MUTANTS 5-6 flip the two GENUINELY WORKING switches off. They are the control
    group, and their kill has to come from a real rule going quiet rather than
    from the P1-82 tests -- the profit-target lock and the peak-equity protection
    are evaluated and enforcing, and defaulting them off would remove protection
    that DOES exist. That is the mirror image of the defect and must not be a
    silent way to satisfy R2.

  * MUTANT 7 makes the class gate's premise vanish by handing the news shield an
    evaluator that reports evidence it does not have. A rule that lies about its
    evidence count reports Enforcing, drops out of the CNE/INERT scan, and its
    default stops being checked at all. This is the "do-nothing evaluator" the
    registry's own header warns about, aimed at P1-82 instead of at the inventory.

  * MUTANT 8 narrows the class gate itself into an instance gate by making
    BuildSnapshot skip the unevaluated rules. The consistency cap then never
    reaches the scan. A gate that silently stops scanning is the failure this
    repo keeps finding (a battery that prints [SKIP] scores a SURVIVOR for the
    same reason).

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red
baseline.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROP = os.path.join(REPO, 'addons', 'PropFirmProtectionSuite.cs')
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')

MUTANTS = [
    # ---- the defect, restored outright ----
    (PROP,
     "the news shield's PROPERTY defaults back to true, so the config asserts a protection\n"
     "     whose rule has never been able to fire (P2-25)",
     'public bool EnableNewsShield { get; set; } = false;',
     'public bool EnableNewsShield { get; set; } = true;'),

    (PROP,
     "the consistency cap's PROPERTY defaults back to true -- the half that a one-sided\n"
     "     fix leaves behind, which is P1-69's and P1-75's shape (P1-77)",
     'public bool EnableConsistencyCap { get; set; } = false;',
     'public bool EnableConsistencyCap { get; set; } = true;'),

    # ---- THE mutants: the second copy, which is the one that runs in production ----
    (PROP,
     "ONLY the news shield's PARSER fallback goes back to true. The property still says\n"
     "     false, so the class gate passes -- and every config file that predates the field,\n"
     "     which is all of them, still loads with the shield ON",
     '(jObj["newsShield"] != null ? (bool)jObj["newsShield"] : false)',
     '(jObj["newsShield"] != null ? (bool)jObj["newsShield"] : true)'),

    (PROP,
     "ONLY the consistency cap's PARSER fallback goes back to true. Same trap, other half",
     '(jObj["enableConsistencyCap"] != null ? (bool)jObj["enableConsistencyCap"] : false)',
     '(jObj["enableConsistencyCap"] != null ? (bool)jObj["enableConsistencyCap"] : true)'),

    # ---- the control group: switches that guard something REAL ----
    (PROP,
     "the profit-target lock defaults OFF. It is evaluated and enforcing, so this removes\n"
     "     protection that genuinely exists -- the mirror image of the defect, and it must not\n"
     "     be a quiet way to satisfy R2",
     'public bool EnableProfitTargetLock { get; set; } = true;',
     'public bool EnableProfitTargetLock { get; set; } = false;'),

    (PROP,
     "peak-equity protection defaults OFF. Same control, and the rule that stops a winner\n"
     "     round-tripping (P1-40 lives inside it)",
     'public bool EnablePeakEquityProtection { get; set; } = true;',
     'public bool EnablePeakEquityProtection { get; set; } = false;'),

    # ---- make the gate's premise disappear rather than fail ----
    #
    # ⚠️ RETIRED 2026-08-15, and retired rather than repointed because it was a DUPLICATE. Its
    # find-string was `: R(null, null, c.NewsEventCount,` at 20 spaces of indent, and the line it
    # matched sits at 28 -- a SUBSTRING match, on the same line as the "+1 on the healthy branch"
    # mutant thirty lines below, producing a byte-identical mutated file. Two entries, one edit:
    # this battery's count has overstated its coverage by one since the day it was written.
    #
    # Nothing found that. It surfaced only because P2-113 added a second rule reporting the same
    # count, which took the substring from one match to two and made check_anchors.py refuse it.
    # The general lesson, and it applies to every battery here: AN ANCHOR THAT IS A SUBSTRING OF A
    # LONGER LINE CAN SILENTLY BE THE SAME ANCHOR AS ANOTHER. A mutant list is an inventory, and
    # this repo has now been caught three times trusting a hand-maintained one. Anchor on whole
    # lines including their indent.

    # ---- P1-86: turning the switch off must not downgrade the defect ----
    (RULES,
     "P1-86 RESTORED: the news shield asks whether it is switched ON before it asks whether\n"
     "     it CAN fire. With P1-82's default that reports Disabled -- 'not a defect' -- for a\n"
     "     rule that has never been able to fire. This is the exact pair the hardening plan\n"
     "     warned about, and the two changes are only safe together",
     '                Evaluator = c => c.PropConfig == null\n'
     '                    ? Off("news shield disabled")\n'
     '                    : c.NewsEventCount == 0',
     '                Evaluator = c => c.PropConfig == null || !c.PropConfig.EnableNewsShield\n'
     '                    ? Off("news shield disabled")\n'
     '                    : c.NewsEventCount == 0'),

    (RULES,
     "the zero-event branch reports Off instead of a zero-evidence reading. Same downgrade,\n"
     "     reached without touching the ordering -- Disabled either way",
     # Re-anchored 2026-08-15 by P2-113, which rewrote the note this branch carries. The BRANCH is
     # what the mutant is about and it is unchanged; only its text moved.
     '                        ? R(null, null, 0,\n'
     '                            "NO NEWS EVENTS ARE LOADED, so this cannot fire. "',
     '                        ? Off("no news events loaded")\n'
     '                            .Also("NO NEWS EVENTS ARE LOADED, so this cannot fire. "'),

    (RULES,
     # ⚠️ REPOINTED by P2-113, and the reason is the ticket. This mutant used to delete '(P2-25)'
     # from the note, on the argument that a red row must name its culprit. That argument was
     # right and its instance went bad: P2-25 CLOSED, and a note blaming a fixed defect for the
     # operator's empty event list is worse than one blaming nothing. The requirement survives in
     # its correct form -- the row must state the CONDITION -- so the mutant now deletes that.
     "the INERT note stops stating the condition. The row is still red and the operator still\n"
     "     cannot find out WHY -- 'refused' without the culprit is the defect UI7 closed, told\n"
     "     here. ⚠️ It used to delete a TICKET NUMBER from this note; P2-113 is what a pinned\n"
     "     ticket number becomes once the ticket closes",
     '                            "NO NEWS EVENTS ARE LOADED, so this cannot fire. "\n',
     '                            ""\n'),

    (RULES,
     "the shield reports one event when it has none. It leaves the INERT band entirely and\n"
     "     reads as Enforcing -- a rule lying about its evidence is what EvidenceCount exists\n"
     "     to make impossible",
     '                            : R(null, null, c.NewsEventCount, null)',
     '                            : R(null, null, c.NewsEventCount + 1, null)'),

    (RULES,
     "BuildSnapshot stops reporting the rules nothing evaluates. The consistency cap never\n"
     "     reaches the scan, so the class gate narrows to an instance gate in silence",
     '                if (def.Evaluator == null)\n                {\n                    var unevaluatedRow = new GuardRuleRow();',
     '                if (def.Evaluator == null)\n                {\n                    continue;\n                    var unevaluatedRow = new GuardRuleRow();'),
]


def run():
    build = subprocess.run(
        ['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    if build.returncode != 0:
        return 'BUILD FAILED'
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINALS = {path: open(path, encoding='utf-8').read() for path in (PROP, RULES)}

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
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(path, 'w', encoding='utf-8', newline='').write(original)

for path, original in ORIGINALS.items():
    open(path, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored originals;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
