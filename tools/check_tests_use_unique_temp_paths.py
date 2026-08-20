"""Gate: no test builds a FIXED filename under %TEMP%.

WHY THIS EXISTS. `P1-175`. `Path.GetTempPath()` is MACHINE-GLOBAL, so a fixed name under it is one
file shared by every suite process on the box. Five sites did that -- `test_cm2_*.json`,
`test_cm3_group.json`, `test_copier_group_config.json`, `test_p1_76_overlap.json`,
`test_p1_75_prop_limits.json` -- and they were the entire cause of the flakiness measured
2026-08-20: six concurrent suites in six SEPARATE worktrees produced 0/1/1/2/2/3 failures out of
3434 assertions, never the same set, while each worktree run alone was 3434/0.

⚠️ AND THE CONSEQUENCE WAS NOT A FLAKY TEST, IT WAS A CORRUPTED EVIDENCE STANDARD. Every mutation
battery in this repo scores `Failed > 0` as a DETECTION. A collision during a mutant run therefore
marks that mutant KILLED when nothing killed it -- no survivor, no warning, a green battery, and a
score better than the suite earned. GitHub CI cannot reproduce it (one bin per hosted runner, no
contention), so the defect was invisible until the suite was run in parallel locally.

WHAT IT CHECKS. Every `Path.GetTempPath()` in the test file must have a uniquifier within a small
window: `Guid.NewGuid()`, the process id, or `TempFileForTest` / `TestRunTag`, which carry both.

⚠️ IT IS A TEXT CHECK AND CANNOT SEE REACHABILITY, so it has the usual limit: a site that builds a
path by string concatenation across many lines would slip past. The window is deliberately small
rather than large -- a wide window passes anything near a Guid used for something else, and a gate
that cannot fail is worse than no gate. NEGATIVE CONTROL below proves it can still fail.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(REPO, 'tests', 'RiskGuardAddOnTests.cs')

UNIQUIFIERS = ('Guid.NewGuid', 'TempFileForTest', 'TestRunTag',
               'GetCurrentProcess', 'ProcessId')
WINDOW = 2   # the line itself plus this many following lines


def offending(text):
    lines = text.split('\n')
    bad = []
    for i, line in enumerate(lines):
        if 'GetTempPath' not in line:
            continue
        window = '\n'.join(lines[i:i + 1 + WINDOW])
        if any(u in window for u in UNIQUIFIERS):
            continue
        bad.append((i + 1, line.strip()))
    return bad


def main():
    if not os.path.isfile(TESTS):
        print('FAIL: %s not found -- this gate would otherwise pass vacuously' % TESTS)
        return 1
    text = open(TESTS, encoding='utf-8', errors='replace').read()

    # ⚠️ REFUSE TO PASS VACUOUSLY. If the pattern this gate polices has vanished from the file
    # entirely, that is far more likely to be a moved helper than a solved problem, and a gate
    # inspecting zero sites reports OK forever. [[state-the-region-a-gate-inspects]]
    total = text.count('GetTempPath')
    if total == 0:
        print('FAIL: no GetTempPath call sites found at all. Either the temp-path helper moved out')
        print('      of this file -- in which case point this gate at it -- or the file is wrong.')
        print('      A gate over an empty set is not a passing gate.')
        return 1

    # NEGATIVE CONTROL. The gate must FAIL on the shape it forbids; a matcher that cannot fail is
    # the failure mode this repo keeps rediscovering. [[a-source-gate-must-assert-the-condition]]
    control = ('void X()\n{\n'
               '    string f = Path.Combine(Path.GetTempPath(), "fixed_name.json");\n}\n')
    if not offending(control):
        print('FAIL: the NEGATIVE CONTROL was not flagged, so this gate cannot fail and')
        print('      proves nothing about the %d real site(s) it just inspected.' % total)
        return 1

    bad = offending(text)
    print('  GetTempPath call sites inspected  %d' % total)
    print('  uniquifiers accepted              %s' % ', '.join(UNIQUIFIERS))
    print('  window                            the line + %d following line(s)' % WINDOW)
    print('  negative control                  flagged, so the gate can fail')

    if bad:
        print()
        print('FAIL: %d test(s) build a FIXED filename under %%TEMP%%:' % len(bad))
        for n, line in bad:
            print('  * line %d: %s' % (n, line[:140]))
        print()
        print('    %TEMP% is machine-global, so this is ONE file shared by every suite process on')
        print('    the box. Use TempFileForTest(name) -- it carries the process id and a per-run')
        print('    GUID, and returns a stable path within one run so a caller may ask twice.')
        print('    P1-175: five such sites made six concurrent suites fail 0/1/1/2/2/3 out of 3434,')
        print('    and a collision during a mutant run scores that mutant KILLED for free.')
        return 1

    print()
    print('OK: every temp path in the suite is unique per process, so the suite can be run in')
    print('    parallel without one process reading another\'s fixture.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
