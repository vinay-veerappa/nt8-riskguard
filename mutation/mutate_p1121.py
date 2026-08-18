"""Mutation battery for P1-121 (the copier window reports what the copier DOES).

The defect was a display that could not be wrong-looking: a green "[ ENGINE: ACTIVE ]"
assigned once at construction and never again, over rows that read `Armed: LIVE` without ever
consulting the global copier mode. So a `disabled` copier -- one that submits nothing at all --
rendered as a healthy screen.

That shape is why this battery leans on NEGATIVE controls. Almost every mutant below is an
attempt to make a status line say something reassuring that the copier has not earned, because
that is the only direction the defect ever failed in:

  * mutants 1-3 make the row claim to be live while the global mode is not acting -- the defect
    verbatim, at each of the three precedence branches that keep it honest.
  * mutants 4-5 attack the two zeros. A latency of 0 means both "nothing has filled" and "it
    filled instantly", and P1-22 shipped the first as if it were the second. Mutant 5 is the
    one that matters: it makes EVERY metric read as measured, which is the direction an
    operator cannot detect, because a plausible number invites no question.
  * mutant 6 makes the view decide for itself which modes act instead of asking the engine.
    This is F-9's drift reintroduced -- a reported state that no longer tracks the enforced
    one -- and it is the single assertion that holds the architecture of the ticket.
  * mutants 9-10 soften the header: a conflict that lowers severity, and an all-quarantined
    copier that reads as merely warning.

⚠️ WHAT THIS BATTERY CANNOT REACH, stated so nobody reads the score as broader than it is.
TradeCopierWindow.cs is excluded from the test build (P2-27's open half), so no mutant can be
placed in it -- the harness would not compile it either way, and a mutant nothing compiles is
not evidence. The window is held only by the source gates in
TestP1121_TheWindowDelegatesItsStatusTextToTheView and by `nt_compile`. That is exactly why the
decisions were moved OUT of the window into CopierStatusView, where they can be mutated at all:
the split is not tidiness, it is the difference between having evidence and not.

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

# No `import _battery` here on purpose -- see the exit at the foot of the file.

# P2-114: a non-ASCII character in a mutant DESCRIPTION raises UnicodeEncodeError inside
# print() on a cp1252 console -- BETWEEN applying a mutant and restoring it, which leaves a
# live mutant in the source tree.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEW = os.path.join(REPO, 'addons', 'CopierStatusView.cs')
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

# (file, description, find, replace)
MUTANTS = [
    # ---- 1. THE DEFECT VERBATIM: a row ignores the global mode ----
    # The anchor runs down to the Detail line on purpose. The shorter version -- ending at the
    # INERT text -- matched TWICE, because RelationshipLine and GroupLine share that branch
    # verbatim, and a 2-match anchor scores a false SURVIVOR rather than a false pass. The
    # word that distinguishes them is "relationship" vs "group" in the Detail.
    (VIEW,
     "a relationship row stops consulting the global copier mode, so an armed row under a "
     "shadow or disabled copier claims to be live again -- the defect this ticket exists to fix",
     '            if (!IsActing(copierMode))\n            {\n                return new CopierHeadline\n                {\n                    Text = basics + " | INERT - copier mode is \'" + copierMode + "\'",\n                    Severity = CopierStatusSeverity.Warn,\n                    Detail = "This relationship is enabled"',
     '            if (false)\n            {\n                return new CopierHeadline\n                {\n                    Text = basics + " | INERT - copier mode is \'" + copierMode + "\'",\n                    Severity = CopierStatusSeverity.Warn,\n                    Detail = "This relationship is enabled"'),

    # ---- 2. the same omission on the GROUP row ----
    (VIEW,
     "a group row stops consulting the global copier mode -- the same defect at the second "
     "renderer, which is where P1-100's lesson says to look",
     '            if (!IsActing(copierMode))\n            {\n                return new CopierHeadline\n                {\n                    Text = basics + " | INERT - copier mode is \'" + copierMode + "\'",\n                    Severity = CopierStatusSeverity.Warn,\n                    Detail = "This group is enabled"',
     '            if (false)\n            {\n                return new CopierHeadline\n                {\n                    Text = basics + " | INERT - copier mode is \'" + copierMode + "\'",\n                    Severity = CopierStatusSeverity.Warn,\n                    Detail = "This group is enabled"'),

    # ---- 3. quarantine stops outranking ----
    (VIEW,
     "a quarantined relationship no longer reports its quarantine, so the one row state the "
     "operator did NOT choose is the one that gets hidden",
     '            if (isQuarantined)\n            {\n                return new CopierHeadline\n                {\n                    Text = basics + " | QUARANTINED - not copying",',
     '            if (false)\n            {\n                return new CopierHeadline\n                {\n                    Text = basics + " | QUARANTINED - not copying",'),

    # ---- 4. an unmeasured metric renders as a number ----
    (VIEW,
     "MetricText prints a value it never measured -- P1-22 verbatim, where the UI showed "
     "Latency: 0ms whether or not any copy had ever filled",
     '            if (metric == null || !metric.Measured)\n                return label + ": " + NotMeasured;',
     '            if (metric == null)\n                return label + ": " + NotMeasured;'),

    # ---- 5. the inverse, and the more dangerous direction ----
    # ENGINE, not VIEW: CopierMetric is declared beside the engine that populates it. The
    # predicate is one line and it is the whole basis on which the view refuses to print.
    (ENGINE,
     "Measured is ignored the other way: every metric reads as measured, so a fabricated "
     "number is presented with a sample count of zero and invites no question",
     '        public bool Measured { get { return Samples > 0; } }',
     '        public bool Measured { get { return Samples >= 0; } }'),

    # ---- 6. THE ARCHITECTURE: the view forms its own opinion ----
    (VIEW,
     "the view decides for itself which modes act instead of asking the engine -- F-9's drift "
     "reintroduced, where the reported state stops tracking the enforced one",
     '            return TradeCopierEngine.IsCopierActingMode(copierMode);',
     '            return string.Equals(copierMode, "live", StringComparison.OrdinalIgnoreCase)\n                || string.Equals(copierMode, "shadow", StringComparison.OrdinalIgnoreCase);'),

    # ---- 7. an unrecognised mode stops failing closed ----
    (VIEW,
     "an unrecognised copier mode is no longer called out, so a typo in the config reads as an "
     "ordinary non-acting mode and no surface anywhere tells the operator",
     '            if (!TradeCopierEngine.IsRecognisedCopierMode(copierMode))',
     '            if (false)'),

    # ---- 8. the header stops counting armed and counts everything ----
    (VIEW,
     "the header counts every relationship as armed, so a copier with nothing armed reports a "
     "row of live relationships",
     '                    if (r.IsEnabled && r.ArmedForLive && !r.IsQuarantined) armed++;',
     '                    if (r.IsEnabled) armed++;'),

    # ---- 9. a conflict lowers the severity ----
    (VIEW,
     "a config conflict OVERWRITES the severity instead of raising it, so a conflict on a "
     "critical copier reads as a mere warning",
     '                headline.Severity = Worse(headline.Severity, CopierStatusSeverity.Warn);',
     '                headline.Severity = CopierStatusSeverity.Warn;'),

    # ---- 10. all-quarantined softens to a warning ----
    (VIEW,
     "a copier whose every enabled relationship is quarantined reports Warn rather than "
     "Critical -- nothing is being copied and the header does not say so loudly",
     '            if (quarantined > 0 && quarantined >= enabled)',
     '            if (false)'),

    # ---- 11. nothing configured reads as healthy ----
    (VIEW,
     "a live copier with no relationships at all reports Ok, which is the original defect in "
     "miniature: a green header over a screen that copies nothing",
     '            if (total == 0)\n            {\n                return new CopierHeadline\n                {\n                    Text = "[ COPIER LIVE - NOTHING CONFIGURED ]",\n                    Severity = CopierStatusSeverity.Warn,',
     '            if (total == 0)\n            {\n                return new CopierHeadline\n                {\n                    Text = "[ COPIER LIVE - NOTHING CONFIGURED ]",\n                    Severity = CopierStatusSeverity.Ok,'),

    # ---- 12. Worse() picks the wrong end ----
    (VIEW,
     "Worse returns the LESSER severity, so every escalation in the file silently becomes a "
     "de-escalation while each individual branch still looks correct",
     '            return (int)a >= (int)b ? a : b;',
     '            return (int)a <= (int)b ? a : b;'),

    # ---- 13. the engine hands back a sample count it did not measure ----
    (ENGINE,
     "GetRelationshipMetrics reports one sample for a relationship that has never been "
     "measured, which re-manufactures the exact zero the view exists to refuse",
     '                latency = new CopierMetric { Value = rel.LatencyMs, Samples = latencySamples };',
     '                latency = new CopierMetric { Value = rel.LatencyMs, Samples = latencySamples + 1 };'),

    # ---- 14. the null guard on the engine read ----
    (ENGINE,
     "GetRelationshipMetrics throws on a null relationship instead of reporting unmeasured -- "
     "it is called from a 2-second UI timer for every card, so a throw blanks the whole panel",
     '            if (rel == null)\n            {\n                latency = new CopierMetric { Value = 0, Samples = 0 };\n                slippage = new CopierMetric { Value = 0, Samples = 0 };\n                return;\n            }',
     '            if (rel == null && DateTime.MinValue > DateTime.MaxValue)\n            {\n                latency = new CopierMetric { Value = 0, Samples = 0 };\n                slippage = new CopierMetric { Value = 0, Samples = 0 };\n                return;\n            }'),
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
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if '[FAIL]' not in ((r.stdout or '') + (r.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return 'NO RESULT LINE'


originals = {p: open(p, encoding='utf-8').read() for p in (VIEW, ENGINE)}

print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print(f'\nREFUSING TO RUN: baseline is RED ({m.group(2)} failing). Every mutant would '
          'score KILLED on pre-existing failures and this battery would prove nothing.')
    sys.exit(2)

survivors = []
try:
    for i, (path, name, old, new) in enumerate(MUTANTS, 1):
        print(f'\n=== mutant {i}/{len(MUTANTS)}: {name} ===')
        src = originals[path]
        if src.count(old) != 1:
            print(f'  [SKIP] {name}: anchor matched {src.count(old)} times in '
                  f'{os.path.basename(path)}')
            survivors.append(name + ' (ANCHOR)')
            continue
        open(path, 'w', encoding='utf-8', newline='').write(src.replace(old, new))
        res = run()
        mm = re.search(r'Failed = (\d+)', res)
        # A crash is a kill: the mutation stopped the suite completing.
        killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
            or (mm is not None and int(mm.group(1)) > 0)
        # P2-148: the verdict above cannot tell a detection from a crash.
        if 'NO ASSERTION FAILED' in res:
            killed = False
        print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
        if not killed:
            survivors.append(name)
        open(path, 'w', encoding='utf-8', newline='').write(src)
finally:
    # try/finally: a battery killed mid-run otherwise leaves a LIVE MUTANT in the tree --
    # measured once already, when a stopped mutate_cm4 batch left one in TradeCopierEngine.cs
    # and a `git diff` skim did not find it.
    for p, text in originals.items():
        open(p, 'w', encoding='utf-8', newline='').write(text)

print('\nrestored originals;', run())

# Plain exit, NOT _battery.finish: this battery declares no EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions -- reaching for the
# helper without a declaration removes the prompt to justify the next exemption someone adds.
# It caught this file on its first run, when the helper had been copied over out of habit.
sys.exit(1 if survivors else 0)
