"""Mutation battery for P2-113: the news events file that "nothing ever opens".

WHAT WAS MEASURED, before any code was written:

    nt_riskguard_inventory ->  "ConfiguredNotEvaluated": 97
                               [ { "rule": "News events file", "accounts": 97 } ]

97 rows, on every poll, on every account, saying `PropFirm.LocalNewsEventsFilePath` is read by
nothing -- with a stated reason beginning "NO CODE READS THIS". `LoadNewsEventsFromDisk` had been
opening it since P2-25 closed, two days earlier.

⚠️ THIS IS F-9's CLASS IN THE PESSIMISTIC DIRECTION, and that direction is not the harmless one.
Every other ticket in this registry defends against a row that reads GREENER than the truth. This
one read redder, and the cost is the same mechanism: a red row that is wrong is how an operator
learns to discount red rows. There were 97 of them per poll.

⚠️ AND NOTHING RE-READS A REASON. `UnevaluatedReason` is prose written once, at the moment a gap
is found, describing the codebase rather than the operator's box. It cannot go stale loudly. Every
mutant in the first group below restores some version of "the row asserts a fact about the code";
the second group defends the thing that replaced it, which is a fact about THIS BOX -- whether the
operator's news file actually loaded.

The four ways a news file fails to load are ALL SILENT, and the silent ones are ranked worst-first
here deliberately:

    []                     parses perfectly, loads zero events   <- the quiet one
    { not json             swallowed by a bare catch
    C:\\absent.json         File.Exists returns false, method returns
    ""                     no path configured at all

The first is the dangerous one and MUTANT 6 is its mutant: a well-formed empty file is the only
failure that looks like a success at every surface. An operator who configured a news file and got
an empty one has protection they believe in and do not have.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# See mutate_p2108.py: the battery's OWN stdout must be utf-8, or a non-ASCII character in a
# mutant description raises between applying a mutant and restoring it, leaving a live mutant.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

SUITE = os.path.join(REPO, 'addons', 'PropFirmProtectionSuite.cs')
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the loader goes back to failing silently ------------------------------
    (SUITE,
     "THE SHIPPED SHAPE: the catch swallows the failure without recording it, so an unparseable\n"
     "     news file is indistinguishable from one that was never configured. This is the line\n"
     "     P2-113 changed, restored",
     '            catch (Exception ex)\n'
     '            {\n'
     '                // Deliberately still swallowed -- and deliberately no longer silent.\n'
     '                NewsEventsLoadStatus = "the news events file could not be read (" + ex.GetType().Name\n'
     '                    + ": " + ex.Message + "): " + filePath;\n'
     '            }',
     '            catch { }'),

    (SUITE,
     "a MISSING file returns without saying so, so the status still describes whatever loaded\n"
     "     last -- the operator points the config at a path that does not exist and the inventory\n"
     "     goes on reporting the previous file's events",
     '            if (!File.Exists(filePath))\n'
     '            {\n'
     '                NewsEventsLoadStatus = "the configured news events file does not exist: " + filePath;\n'
     '                return;\n'
     '            }',
     '            if (!File.Exists(filePath)) return;'),

    (SUITE,
     "THE QUIET ONE: a well-formed but EMPTY news file reports as a healthy load. `[]` parses,\n"
     "     the count is zero, and the only failure that looks exactly like a success at every\n"
     "     other surface stops being called out. Weigh the quiet failure above the loud one",
     '                NewsEventsLoadStatus = events.Count == 0\n'
     '                    ? "the news events file loaded and is EMPTY, so the shield cannot fire: " + filePath\n'
     '                    : string.Format("{0} news event(s) loaded from {1}", events.Count, filePath);',
     '                NewsEventsLoadStatus = string.Format("{0} news event(s) loaded from {1}", events.Count, filePath);'),

    (SUITE,
     "the initial status claims a successful load before anything has been loaded. A guard that\n"
     "     never calls the loader -- no path configured, or an exception earlier in startup --\n"
     "     then reports the news file as healthy for the life of the process",
     '        public string NewsEventsLoadStatus { get; private set; } = "no news events file configured";',
     '        public string NewsEventsLoadStatus { get; private set; } = "news events loaded";'),

    (SUITE,
     "an empty PATH reports the same text as a successful load, so 'I never configured one' and\n"
     "     'mine loaded' are the same row",
     '            if (string.IsNullOrEmpty(filePath))\n'
     '            {\n'
     '                NewsEventsLoadStatus = "no news events file configured";\n'
     '                return;\n'
     '            }',
     '            if (string.IsNullOrEmpty(filePath))\n'
     '            {\n'
     '                NewsEventsLoadStatus = "news events loaded";\n'
     '                return;\n'
     '            }'),

    (SUITE,
     "a file that DESERIALIZES TO NULL is treated as a load. JsonConvert returns null for the\n"
     "     literal `null`, and the old code fell through to leave the previous list in place",
     '                if (events == null)\n'
     '                {\n'
     '                    NewsEventsLoadStatus = "the news events file parsed to nothing: " + filePath;\n'
     '                    return;\n'
     '                }',
     '                if (events == null) return;'),

    # ---- group 2: the registry stops reporting what the loader learned -------------------
    (RULES,
     "the news events file goes back to having NO EVALUATOR, which is P2-113 verbatim: 97 rows\n"
     "     per poll reporting CONFIGURED-and-not-EVALUATED for a path that is read on every\n"
     "     startup. A rule declared without an evaluator reports that state BY CONSTRUCTION, so\n"
     "     nothing downstream can catch this",
     '                Evaluator = c => c.PropConfig == null\n'
     '                        || string.IsNullOrEmpty(c.PropConfig.LocalNewsEventsFilePath)\n'
     '                    ? Off("no news events file configured")',
     '                UnevaluatedReason = "nothing reads this",\n'
     '                Evaluator = null ?? (c => c.PropConfig == null\n'
     '                        || string.IsNullOrEmpty(c.PropConfig.LocalNewsEventsFilePath)\n'
     '                    ? Off("no news events file configured")'),

    (GUARD,
     "the load status never reaches the snapshot, so every row falls back to 'the load outcome\n"
     "     was not reported' and the four distinguishable failures collapse into one shrug. The\n"
     "     seam between the suite that KNOWS and the registry that REPORTS is the whole fix",
     '                PropFirmProtectionSuite.Instance.NewsEventCount,\n'
     '                PropFirmProtectionSuite.Instance.NewsEventsLoadStatus);',
     '                PropFirmProtectionSuite.Instance.NewsEventCount);'),
]

ORIGINALS = {}
for _t, _, _, _ in MUTANTS:
    if _t not in ORIGINALS:
        ORIGINALS[_t] = open(_t, encoding='utf-8').read()


def restore():
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


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
    killed = _battery.score(res, run)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    restore()

restore()
print('\nrestored originals;', run())

print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
