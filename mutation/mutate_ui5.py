"""Mutation battery for UI5 (the JSON contract for the browser UI).

Why a battery for fifteen lines of serializer settings:

The bridge route that serves this payload is one line and is UNTESTABLE --
`McpBridgeAddOn.cs` is excluded from the test build (`P2-27`). So the contract was
put in core precisely so it could be verified, and a contract nobody can break in
a test is not a contract. Every mutant below is a single-token change to a
`JsonSerializerSettings` field, which is exactly how this would really regress: a
future edit "tidying up" the settings object.

Each one is also a defect this repo has already had, in a new place:

  * MUTANT 1 drops the enum converter, so states cross as INTEGERS. The page then
    has to hardcode the enum's integer order -- an order UI3's battery pins for a
    completely unrelated reason (worst sorts first). Reordering the enum for the
    sort would silently relabel every row in the UI.

  * MUTANT 2 sets NullValueHandling.Ignore, dropping `"limit": null`. A page
    reading `row.limit ?? 0` then shows a limit of ZERO for a rule that has none.
    That is UI1's copier-metrics defect verbatim -- a bare 0 meaning "not
    applicable" -- one layer further out.

  * MUTANT 4 makes a null snapshot serialize as the four characters `null`. The
    page gets nothing to render and nothing to say, so the operator sees a blank
    screen. `P2-83` reached by a third route.

MUTANT 3 (camelCase dropped) is the mildest and is included anyway: the page reads
these exact characters, and PascalCase would break every field at once while every
C#-side test still passed.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red
baseline.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')

MUTANTS = [
    ("the enum converter is dropped, so every state crosses as an INTEGER and the page must\n"
     "     hardcode an enum order that exists for an unrelated reason",
     '            Converters = { new StringEnumConverter() },',
     ''),

    ("nulls are OMITTED, so a rule with no numeric limit loses the key entirely and a page\n"
     "     reading `row.limit ?? 0` renders a limit of zero -- UI1's bare-zero defect, one layer out",
     '            NullValueHandling = NullValueHandling.Include,',
     '            NullValueHandling = NullValueHandling.Ignore,'),

    ("camelCase is dropped, so every field the page reads is renamed at once while every\n"
     "     C#-side assertion still passes",
     '''            ContractResolver = new DefaultContractResolver
            {
                NamingStrategy = new CamelCaseNamingStrategy { ProcessDictionaryKeys = false }
            },''',
     ''),

    ("a missing snapshot serializes to the literal `null`, leaving the page with nothing to\n"
     "     render and nothing to say -- a blank screen, which is P2-83 by a third route",
     '            if (snapshot == null)\n'
     '            {\n'
     '                return JsonConvert.SerializeObject(\n'
     '                    new { error = "the RiskGuard add-on is not loaded, so no rule inventory exists to report" },\n'
     '                    UiJsonSettings);\n'
     '            }\n',
     ''),

    ("the error object loses its message, so the page can detect that something is wrong and\n"
     "     still cannot tell the operator what",
     '                    new { error = "the RiskGuard add-on is not loaded, so no rule inventory exists to report" },',
     '                    new { error = "" },'),

    # ---- the fleet summary, added after measuring the real box: 96 accounts x 25 rules ----
    ("dictionary keys are camel-cased, so the fleet says `inert` where the detail rows say\n"
     "     `Inert` -- the same fact spelled two ways in one payload, and the page cannot tell\n"
     "     which view it is holding. This was a REAL defect, caught by a test rather than a browser",
     '                NamingStrategy = new CamelCaseNamingStrategy { ProcessDictionaryKeys = false }',
     '                NamingStrategy = new CamelCaseNamingStrategy { ProcessDictionaryKeys = true }'),

    ("the worst state is taken as the HIGHEST enum value rather than the lowest, so an account\n"
     "     with one unevaluated rule and twenty-four enforcing ones is ranked by its BEST row --\n"
     "     the fleet then sorts the most broken account to the bottom",
     '                    if (worst == null || (int)row.State < (int)worst.Value) worst = row.State;',
     '                    if (worst == null || (int)row.State > (int)worst.Value) worst = row.State;'),

    ("the fleet summary stops carrying the rules nothing evaluates, so an operator who only\n"
     "     ever opens the fleet view never learns that five rules are evaluated by nothing",
     '                unevaluatedRules = snapshot.UnevaluatedRules',
     '                unevaluatedRules = new List<GuardRuleRow>()'),

    # Written first as `ruleCount = 25` and it SURVIVED -- because 25 IS the number of
    # rules in the registry today, so the mutant reinstated the truth and could not change
    # any outcome. A mutant that cannot fail is as useless as a test that cannot fail
    # (handover section 5.14): read the mutant before concluding the test is weak.
    ("the per-account rule COUNT is hardcoded, so an account missing rules still reports a full\n"
     "     inventory in the fleet view",
     '                    ruleCount = acct.Rules == null ? 0 : acct.Rules.Count,',
     '                    ruleCount = 99,'),
]


def run():
    b = subprocess.run(['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    if 'Build succeeded' not in b.stdout:
        return 'BUILD FAILED'
    r = subprocess.run(['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith('RESULTS:'):
            return line.strip()
    return 'NO RESULT LINE'


original = open(RULES, encoding='utf-8').read()
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
for name, old, new in MUTANTS:
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(RULES, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(RULES, 'w', encoding='utf-8', newline='').write(original)

open(RULES, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
