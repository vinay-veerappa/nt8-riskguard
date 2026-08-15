"""Mutation battery for UI6 (the copier half of the browser UI).

The guard half answers "is this limit protecting me?". This half answers a
different question -- "is the follower actually where the leader is?" -- and it
has two properties that no amount of test-passing makes safe on its own:

  * MUTANT 1 sorts by the ENUM CAST instead of the stated severity rank. This is
    the mutant this whole file exists for. `CopierConformance` reads
    Idle=0, Match=1, Shadow=2, Diverged=3, Orphan=4, Quarantined=5 -- historical
    numbering, not severity -- so casting puts a HEALTHY Idle row at the top and an
    ORPHAN, where the leader is flat and the follower still holds a live position
    nothing is managing, BELOW a quarantined one. It is the single worst row this
    system can emit, sorted into the middle of the table.

  * MUTANTS 7-8 destroy the `measured` distinction. These metrics are
    SESSION-SCOPED and a recompile resets them, so a bare 0 cannot tell "no copy
    has filled yet" from "a copy filled and was perfect". That confusion was once
    misdiagnosed as a broken measurement and cost two sessions (P1-22). A page
    showing `0 ms` for a copier that has never filled is the defect restored.

MUTANT 6 ranks an UNKNOWN verdict as best rather than worst. A conformance value
added later and forgotten here must not land at the bottom of the table looking
healthy; ranking it worst is how it gets noticed.

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
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')

MUTANTS = [
    # ---- THE mutant: the enum's own integers are not severity ----
    ("the severity rank becomes the ENUM CAST, so a healthy Idle row sorts FIRST and an\n"
     "     ORPHAN -- a live position nothing is managing -- sorts below a quarantined one",
     '                case CopierConformance.Orphan:      return 0;',
     '                case CopierConformance.Orphan:      return (int)CopierConformance.Orphan;'),

    ("Orphan and Diverged swap, so 'the leader is flat and the follower is still in' ranks\n"
     "     below 'both are in and they disagree'. The comment on the enum says this ordering was\n"
     "     deliberate; nothing enforced it",
     '                case CopierConformance.Orphan:      return 0;\n',
     '                case CopierConformance.Orphan:      return 1;\n'),

    ("SHADOW ranks as healthy, so a relationship that is configured and will never act sorts\n"
     "     among the working ones -- the state most often mistaken for working",
     '                case CopierConformance.Shadow:      return 3;',
     '                case CopierConformance.Shadow:      return 6;'),

    ("Quarantined ranks as healthy, so a relationship that is not copying at all disappears\n"
     "     into the bottom of the table while the follower drifts from the leader",
     '                case CopierConformance.Quarantined: return 2;',
     '                case CopierConformance.Quarantined: return 6;'),

    ("two verdicts share a rank, so the ordering is no longer total and the table's row order\n"
     "     depends on the sort's stability rather than on severity",
     '                case CopierConformance.Match:       return 4;',
     '                case CopierConformance.Match:       return 5;'),

    ("an UNRECOGNISED verdict ranks BEST instead of worst, so a conformance value added later\n"
     "     and forgotten here lands at the bottom of the table looking healthy",
     '            return 0;\n        }\n\n        public static string ToJson(CopierSnapshot snapshot)',
     '            return 99;\n        }\n\n        public static string ToJson(CopierSnapshot snapshot)'),

    # ---- P1-22: a zero that was never measured is not a zero that was ----
    ("the latency metric is flattened to its VALUE, so the sample count is lost and a copier\n"
     "     that has never filled reports 0 ms exactly like one that filled perfectly. P1-22",
     '                    latency = r.Latency,',
     '                    latency = r.Latency == null ? 0.0 : r.Latency.Value,'),

    ("the slippage metric is flattened the same way",
     '                    slippage = r.Slippage,',
     '                    slippage = r.Slippage == null ? 0.0 : r.Slippage.Value,'),

    # ---- the rest of the row ----
    ("the severity stops travelling on the row, so the page has to re-derive an ordering in\n"
     "     JavaScript -- a second owner of the fact this file exists to state once",
     '                    severity = SeverityRank(r.Verdict)',
     '                    severity = 0'),

    ("the ACTUAL position is reported as the expected one, so every row matches and the whole\n"
     "     conformance idea reports success unconditionally",
     '                    actualQuantity = r.ActualQuantity,',
     '                    actualQuantity = r.ExpectedQuantity,'),

    ("the quarantine REASON is dropped, so a quarantined row cannot say what quarantined it",
     '                    quarantineReason = r.QuarantineReason,',
     '                    quarantineReason = (string)null,'),

    ("a missing copier serializes without an error, so 'the copier is not loaded' and 'the\n"
     "     copier mirrors nothing' render identically -- P2-83 on the copier side",
     '            if (snapshot == null)\n'
     '            {\n'
     '                return JsonConvert.SerializeObject(\n'
     '                    new { error = "the trade copier is not loaded, so no relationships can be reported" },\n'
     '                    GuardSnapshotJson.UiJsonSettings);\n'
     '            }\n',
     ''),
]


def run():
    b = subprocess.run(['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if 'Build succeeded' not in b.stdout:
        return 'BUILD FAILED'
    r = subprocess.run(['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
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
