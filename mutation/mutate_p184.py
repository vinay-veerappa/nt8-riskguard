"""Mutation battery for P1-84 (three defaults that make the guard easy to switch off).

A battery over three literals looks like overkill until you notice what the tests
have to be to be worth anything. None of them pins a number -- one asserts an
inequality between two files, one is conditional on a neighbouring field, one
reads the addon source. Each of those is a way to be subtly wrong.

What each group is defending:

  * The R5 stop-attach-deadline and OnMissing-default mutants MOVED to mutate_p1151.py
    on 2026-08-20, when the operator reversed the decision they defended (OnMissing now
    defaults to AutoStop, StopAttachSeconds to a short 5, and a Flatten penalty's
    hand-speed floor is enforced at preflight, not by the default). See the note at the
    head of MUTANTS. What remains here is R4 (the copier cap) and R2 (MinShadowSessions).

  * MUTANTS restore the copier's 100-contract cap, one DTO at a time. The second is
    here because the group carries its own copy, and the first version of the
    test only looked at the relationship -- a fix applied to one of two identical
    declarations is P1-69's and P1-75's shape and this repo keeps finding it.

  * MUTANT 6 raises the copier's cap to just above the guard's. It is the one
    that proves the assertion is an INEQUALITY and not a pinned 10: at 11 against
    the guard's 10 the copier's cap is dead again, by one contract.

  * MUTANT 7 puts MinShadowSessions back to 0, which does not relax the arming
    precondition -- it switches it off, because RunPreflight short-circuits at
    `> 0`.

  * MUTANT 8 removes that short-circuit instead. Now zero WOULD be a real (if
    permissive) threshold, and the test's premise is gone. It must fail rather
    than quietly keep passing, because a test whose reasoning has evaporated is
    worse than no test -- it reports a defect that is no longer there and hides
    the one that is.

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
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
COPIER = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')
# P2-29: the config DTOs moved to RiskGuardModels.cs (a MOVE, not a rewrite -- they are
# their own top-level types, not members of RiskGuardAddOn). check_anchors.py caught all
# four of these in the same commit; they are REPOINTED, never retired, because the
# subject is unchanged -- the default they defend is the same default.
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # ---- R5 (the stop-attach deadline and OnMissing default) MOVED to mutate_p1151.py 2026-08-20.
    # The operator reversed the decision the old R5 mutants defended: OnMissing now defaults to
    # AutoStop and StopAttachSeconds to a short 5, and the deadline floor is enforced at PREFLIGHT
    # (a Flatten penalty needs >= 15s, refused there) rather than by the shipped default. Those
    # anchors -- `StopAttachSeconds = 15` and `OnMissing = "Flatten"` -- no longer exist, and the
    # new defaults + c3 guard + bps pricing are mutation-covered by mutate_p1151.py. Removed here
    # rather than re-anchored: mutating the new default seconds would score a SURVIVOR because
    # nothing pins the exact value now (the floor moved to preflight). ----

    # ---- R4: two names for one concept ----
    (COPIER,
     "the RELATIONSHIP cap goes back to 100 -- roughly $4.5M of MNQ notional, which is not a\n"
     "     cap but the absence of one",
     '        public int MaxPositionSize { get; set; } = 10;\n'
     '        public bool IsQuarantined { get; set; } = false;',
     '        public int MaxPositionSize { get; set; } = 100;\n'
     '        public bool IsQuarantined { get; set; } = false;'),

    (COPIER,
     "the GROUP cap goes back to 100. The other half -- and the first draft of the test only\n"
     "     looked at the relationship, which is exactly how P1-69 and P1-75 happened",
     '        public int MaxPositionSize { get; set; } = 10;\n'
     '        public double MaxSlippageTicks { get; set; } = 0.0;',
     '        public int MaxPositionSize { get; set; } = 100;\n'
     '        public double MaxSlippageTicks { get; set; } = 0.0;'),

    (COPIER,
     "the relationship cap goes to 11 -- ONE above the guard's. Dead again, by one contract.\n"
     "     This is what proves the assertion is an inequality between two files and not a\n"
     "     pinned 10 that happens to match",
     '        public int MaxPositionSize { get; set; } = 10;\n'
     '        public bool IsQuarantined { get; set; } = false;',
     '        public int MaxPositionSize { get; set; } = 11;\n'
     '        public bool IsQuarantined { get; set; } = false;'),

    # ---- the arming precondition ----
    (MODELS,
     "MinShadowSessions goes back to 0, which does not relax the arming gate -- it switches\n"
     "     it off, because RunPreflight short-circuits at `> 0`",
     'public int MinShadowSessions { get; set; } = 5;',
     'public int MinShadowSessions { get; set; } = 0;'),

    (GUARD,
     "the preflight short-circuit is removed instead. Zero would then be a real threshold and\n"
     "     the test's whole premise is gone -- it must FAIL rather than keep passing, because a\n"
     "     test whose reasoning has evaporated hides the defect that replaced it",
     '                && _config.MinShadowSessions > 0\n',
     '                && true\n'),
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


ORIGINALS = {path: open(path, encoding='utf-8').read() for path in (GUARD, COPIER, MODELS)}

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
