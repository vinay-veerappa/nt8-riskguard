"""Mutation battery for P1-83 (config that is stored, settable, and read by nothing).

Three copier fields -- StealthMode, the copier's own DailyLossLimit, and the whole
CopierExecutionMode enum -- were persisted, settable from two surfaces, and
branched on nowhere. StealthMode was the worst of them: the NT8 window printed
"Stealth: ON" and the browser page rendered a "stealth" flag for a feature with
no implementation at all.

What each group is defending:

  * MUTANTS 1-3 reintroduce each dead field, one at a time. Each must be caught by
    the CLASS gate -- the test that walks the two DTOs by reflection and counts
    real uses in the engine -- and not by anything that names the fields. If a
    mutant survives, the gate is scoped wrongly and the fourth dead field will
    walk straight in.

  * MUTANT 4 reintroduces one WITH a fake read: a field assigned to a local that
    is then discarded. That is the cheapest way to satisfy any "is it referenced?"
    check, and the reason the guard-side needed a runtime registry (P2-25). This
    battery cannot claim the source scan catches P2-25's class -- it cannot -- but
    it must at least catch the version a person would actually write.

  * MUTANT 5 puts a display fragment back without the field behind it. This is
    what a half-done deletion looks like, and on a WPF file the test build
    compiles away entirely a source scan is the only gate there is.

  * MUTANT 6 re-emits the `stealthMode` key on the copier snapshot. That key is
    read by the browser page in the OTHER repo, so an emitter left behind is a
    surface asserting a protection nothing implements -- across a repo boundary,
    where no compiler is going to help.

⚠️ WHAT THIS BATTERY DELIBERATELY DOES NOT COVER. Two obvious ways to weaken the
gate are edits to the TEST file -- widening the scan from the engine to the window
(which would score StealthMode as READ, because the window displayed it), and
filling the exemption dictionary so nothing is examined. Batteries here only
mutate `addons/`, because the test file is protected and mutating it would make
every mutant trivially killable. Those two remain guarded by review, and by the
fact that the exemption dictionary demands a written reason per entry.

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
import _battery


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
COPIER = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')
WINDOW = os.path.join(REPO, 'addons', 'TradeCopierWindow.cs')
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')

MUTANTS = [
    (COPIER,
     "StealthMode comes back on the relationship: stored, serialized, settable, and branched\n"
     "     on by nothing",
     '        public int MaxPositionSize { get; set; } = 10;\n'
     '        public bool IsQuarantined { get; set; } = false;',
     '        public int MaxPositionSize { get; set; } = 10;\n'
     '        public bool StealthMode { get; set; } = true;\n'
     '        public bool IsQuarantined { get; set; } = false;'),

    (COPIER,
     "the copier's own DailyLossLimit comes back -- sitting in the config file beside the\n"
     "     guard's REAL PnLRules.DailyLossLimit, which is R4's confusion exactly",
     '        public bool IsQuarantined { get; set; } = false;',
     '        public double DailyLossLimit { get; set; } = 1000.0;\n'
     '        public bool IsQuarantined { get; set; } = false;'),

    (COPIER,
     "CopierExecutionMode comes back. The most consequential-sounding of the three -- copy on\n"
     "     execution against copy on order is a genuine design decision, and the config implied\n"
     "     the choice was yours",
     '    public enum CopierSizingMode',
     '    public enum CopierExecutionMode { Executions, Orders }\n'
     '    public enum CopierSizingMode'),

    (COPIER,
     "StealthMode comes back WITH a fake read -- assigned to a local that is thrown away.\n"
     "     The cheapest way to satisfy any 'is it referenced?' check, and the reason the guard\n"
     "     side needed a runtime registry rather than a linter (P2-25)",
     '        public int MaxPositionSize { get; set; } = 10;\n'
     '        public double MaxSlippageTicks { get; set; } = 0.0;',
     '        public int MaxPositionSize { get; set; } = 10;\n'
     '        public bool StealthMode { get; set; } = true;\n'
     '        internal void TouchStealth() { bool unused = this.StealthMode; }\n'
     '        public double MaxSlippageTicks { get; set; } = 0.0;'),

    (WINDOW,
     "a display fragment comes back without the field behind it. What a half-done deletion\n"
     "     looks like -- and on a file the test build compiles away entirely, a source scan is\n"
     "     the only gate there is",
     # REPOINTED, not retired (P1-121, session 49). The old anchor was the window's own
     # `string statusText = $"Mode: {rel.SizingMode} | ...` line, which no longer exists: the
     # row text is now built by CopierStatusView.RelationshipLine and the window only renders
     # it. check_anchors.py caught the break in the same commit that caused it, which is the
     # gate working. The mutant's MEANING is unchanged -- reintroduce a display fragment in the
     # window for a field with nothing behind it -- so it moves to the render site.
     '                Text = line.Text,',
     '                Text = "Stealth: ON | " + line.Text,'),

    (RULES,
     "the copier snapshot emits a stealthMode key again. The browser page in the OTHER repo\n"
     "     reads exactly this key, so an emitter left behind is a surface asserting a\n"
     "     protection nothing implements -- across a repo boundary, where no compiler helps",
     '                    quarantineReason = r.QuarantineReason,',
     '                    quarantineReason = r.QuarantineReason,\n'
     '                    stealthMode = true,'),
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


ORIGINALS = {path: open(path, encoding='utf-8').read() for path in (COPIER, WINDOW, RULES)}

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
    killed = _battery.score(res, run)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(path, 'w', encoding='utf-8', newline='').write(original)

for path, original in ORIGINALS.items():
    open(path, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored originals;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
