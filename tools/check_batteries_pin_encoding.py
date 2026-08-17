"""Every mutation battery must pin an explicit encoding on its subprocess captures.

⚠️ WHY THIS EXISTS. On Windows, `subprocess.run(..., capture_output=True, text=True)` decodes the
child's output with the LOCALE codec, which is cp1252 here and on GitHub's windows runners. The
bridge test suite prints test names, and one non-ASCII character in one of them is enough:
`fh.read()` raises `UnicodeDecodeError` on a reader THREAD, the exception is printed but not
propagated, `res.stdout` comes back **None**, and the battery dies with a `TypeError` from `re`
before it has run a single mutant.

That is not a test failure and does not read like one. It is `an alarm that is always on is off`
in its other form -- a check that CANNOT RUN reports nothing, and the batteries are this repo's
whole evidence standard.

⚠️ AND THE REASON IT IS A GATE RATHER THAN A FIXED BUG: all four batteries had it. A bulk patch
fixed three and printed `SKIP mutate_p190.py (matched 0)` for the fourth, because that one's
`run()` builds and runs in two steps and did not match the patch's anchor. **The skip was printed,
read, and not acted on** -- and CI went red on the very next push, on a battery that had nothing
to do with the change. A human reading a tool's honest report is not a gate; this is.

It parses with `ast` rather than grepping for a string, and it prints the number of calls actually
inspected -- see the nt8-riskguard handover on the four gates in these repos that were caught
proving nothing by searching a region nobody had bounded.

⚠️ P2-114, 2026-08-15: THIS GATE ONLY EVER CHECKED HALF OF THE HAZARD, AND THE OTHER HALF FIRED IN
CI THE DAY IT WAS PORTED HERE. Everything above concerns the encoding of the CHILD's output. The
battery's OWN `print()` has the same problem in the other direction: a non-ASCII character in a
mutant DESCRIPTION raises `UnicodeEncodeError` on a cp1252 console, and it raises BETWEEN applying
a mutant and restoring it -- so it leaves a LIVE MUTANT in the working tree. That is strictly worse
than the decode half, which fails before the first mutant is applied.

Measured: `mutate_p182.py` crashed exactly this way on the GitHub windows runner while passing
locally, because a repointed mutant description had gained one warning sign.

⚠️ AND THE REASON THE GATE MISSED IT IS ITS OWN LESSON RESTATED. Its docstring said "every mutation
battery must pin an explicit encoding on its subprocess captures", and it enforced precisely that
sentence. The sentence was the bug: the hazard is *the battery's encoding assumptions*, of which
the subprocess capture is one. **State the hazard a gate is for, then check every surface it has** --
`state-the-region-a-gate-inspects` applied to a hazard rather than to a file.

⚠️ It was also MISSING FROM THIS REPO ENTIRELY while the handover cited it as protecting these
batteries -- the fourth per-repo gate gap after `check_anchors.py`, `check_ci_runs_every_battery.py`
and `check_bridge_parses.py`. On arrival it failed **56 subprocess captures across 29 batteries**:
this repo's batteries had never pinned either half, and had only survived because the C# suite's
own output happens to be ASCII today.
"""
import ast
import os
import sys

# ⚠️ This gate enforces the DECODE half of the encoding hazard and was itself missing the
# ENCODE half -- and a text sweep for 'reconfigure' could not see that, because this file
# CONTAINS that string as the thing it searches for. Detection by substring over a region
# nobody bounded; check_tools_pin_stdout.py parses instead, and found it.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MUTATION = os.path.join(REPO, 'mutation')


def captures_output(call):
    """True if this subprocess.run call captures the child's output as TEXT.

    A capture that stays as bytes cannot raise a decode error, so it is not this gate's business.
    """
    kw = {k.arg: k.value for k in call.keywords if k.arg}
    def truthy(name):
        node = kw.get(name)
        return isinstance(node, ast.Constant) and node.value is True
    return truthy('capture_output') and (truthy('text') or truthy('universal_newlines'))


def pins_own_stdout(src):
    """True if this battery reconfigures its OWN stdout to a codec that cannot raise.

    Parsed, not grepped, and BOTH keywords are required. `reconfigure(encoding='utf-8')` alone
    still raises on a character utf-8 can encode but the terminal cannot render on some consoles;
    `errors='replace'` is what makes print() total. A gate that accepted either half would pass
    the shape that still crashes.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr == 'reconfigure'):
            continue
        target = f.value
        if not (isinstance(target, ast.Attribute) and target.attr == 'stdout'
                and isinstance(target.value, ast.Name) and target.value.id == 'sys'):
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        enc = kw.get('encoding')
        err = kw.get('errors')
        if isinstance(enc, ast.Constant) and isinstance(enc.value, str) \
                and enc.value.lower().replace('-', '') == 'utf8' \
                and isinstance(err, ast.Constant) and err.value in ('replace', 'backslashreplace'):
            return True
    return False


def is_subprocess_run(call):
    f = call.func
    return isinstance(f, ast.Attribute) and f.attr == 'run' \
        and isinstance(f.value, ast.Name) and f.value.id == 'subprocess'


def main():
    if not os.path.isdir(MUTATION):
        print('FAIL: no mutation/ directory -- refusing to pass vacuously')
        return 1

    batteries = sorted(f for f in os.listdir(MUTATION)
                       if f.startswith('mutate_') and f.endswith('.py'))
    if not batteries:
        print('FAIL: no mutate_*.py found -- refusing to pass vacuously')
        return 1

    inspected = 0
    stdout_pinned = 0
    problems = []
    for name in batteries:
        path = os.path.join(MUTATION, name)
        src = open(path, encoding='utf-8').read()

        # P2-114, the ENCODE half. A battery that prints only ASCII is safe today and is one
        # repointed description away from not being -- and the failure lands mid-run, between
        # applying a mutant and restoring it. So this is required of EVERY battery rather than
        # only of the ones that currently carry a non-ASCII character: a conditional requirement
        # would be satisfied by the very edit that breaks it.
        if pins_own_stdout(src):
            stdout_pinned += 1
        else:
            problems.append(
                '%s: does not pin its OWN stdout encoding. Add\n'
                "        sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
                '      near the imports. Without it, one non-ASCII character in a mutant '
                'description raises UnicodeEncodeError inside print() on a cp1252 console -- '
                'AFTER a mutant is applied and BEFORE it is restored, leaving a live mutant in '
                'the source tree (measured in CI on mutate_p182.py, 2026-08-15).' % name)

        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            # Refuse what cannot be parsed rather than skipping it: a battery this gate cannot
            # read is exactly the battery it would otherwise silently exempt.
            problems.append('%s: could not parse (%s)' % (name, exc))
            continue

        found_any = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not is_subprocess_run(node):
                continue
            if not captures_output(node):
                continue
            found_any = True
            inspected += 1
            kw = {k.arg for k in node.keywords if k.arg}
            if 'encoding' not in kw:
                problems.append(
                    '%s:%d: subprocess.run captures text output with no explicit encoding= '
                    '(decodes as cp1252 on Windows; one non-ASCII test name makes stdout None)'
                    % (name, node.lineno))

        if not found_any:
            problems.append(
                '%s: no text-capturing subprocess.run found at all. Either it does not run the '
                'suite, or it does so in a shape this gate cannot see -- both need a human.'
                % name)

    print('batteries: %d   text-capturing subprocess.run calls inspected: %d   '
          'own-stdout pins found: %d'
          % (len(batteries), inspected, stdout_pinned))
    for b in batteries:
        print('  ' + b)

    if problems:
        print('\nFAIL:')
        for p in problems:
            print('  * ' + p)
        return 1

    print('\nOK: every battery pins an explicit encoding on every text capture (DECODE, the '
          'child), and on its own stdout (ENCODE, itself). Both halves, because they fail at '
          'different moments: the decode half before the first mutant, the encode half between '
          'applying one and restoring it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
