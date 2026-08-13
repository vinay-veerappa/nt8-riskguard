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
    (RULES,
     "the news shield reports one piece of evidence it does not have. It stops being INERT,\n"
     "     drops out of the CNE/INERT scan, and its default is no longer checked by anything --\n"
     "     the registry header's 'do-nothing evaluator' hazard, aimed at P1-82",
     '                    : R(null, null, c.NewsEventCount,',
     '                    : R(null, null, c.NewsEventCount + 1,'),

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
