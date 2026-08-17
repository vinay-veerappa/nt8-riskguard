"""Every gate and battery must pin stdout to UTF-8, or it dies when it has something to say.

WHY THIS EXISTS. `mutation/check_anchors.py` was found crashing outright:

    UnicodeEncodeError: 'charmap' codec can't encode characters in position 44-45

Windows defaults stdout to cp1252. This repo's convention is that every mutant description and
every plan entry is full of non-ASCII -- the ⚠️ that marks a hazard -- and a gate only PRINTS
those strings when it is reporting a problem. So a gate could run green for months and then, on
the first run where it had a finding, die with a traceback that reads as a defect in the script.

⚠️ That is exactly what happened, and the cost was invisible: while `check_anchors.py` could not
run, it was checking NOTHING, and nothing said so. The run after the fix reported **434 anchors,
1 broken** -- a real broken anchor that had been sitting behind a crash.

Twelve of this repo's twelve tools and batteries were unpinned. They had been surviving on the
accident that they mostly print ASCII.

⚠️ AND `check_batteries_pin_encoding.py` ALREADY ENFORCED THIS -- for a region that did not
include the crashing file. It walks `mutation/mutate_*.py`. `mutation/check_anchors.py` is in the
same directory under a different prefix, and every script in `tools/` is outside it entirely, so
twelve unpinned scripts sat behind a green gate whose header describes exactly their hazard.
Fifth instance of *state the region a gate inspects* -- and the two gates are deliberately kept
separate rather than merged, because they enforce the same rule for different reasons: a battery
that dies mid-run leaves a LIVE MUTANT in the working tree, while a tool that dies just stops
checking.

⚠️ A TEXT SWEEP CANNOT FIND THESE. Scanning for the string `reconfigure` reports
`check_batteries_pin_encoding.py` as compliant, because that file CONTAINS the string as the
thing it searches for. It was the one script the sweep missed and this gate caught. Parse; do not
grep.

Exits non-zero if any script under tools/ or mutation/ prints without pinning stdout.
"""
import ast
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCANNED = ('tools', 'mutation')

# This file is itself in scope -- it must satisfy its own rule, and it does.
unpinned = []
scanned = []

for folder in SCANNED:
    root = os.path.join(REPO, folder)
    if not os.path.isdir(root):
        print('MISSING DIRECTORY: %s -- this gate cannot inspect what is not there' % folder)
        sys.exit(2)
    for name in sorted(os.listdir(root)):
        if not name.endswith('.py'):
            continue
        path = os.path.join(root, name)
        rel = '%s/%s' % (folder, name)
        try:
            src = io.open(path, encoding='utf-8').read()
            tree = ast.parse(src)
        except (OSError, SyntaxError) as exc:
            # NOT a skip. A file this gate cannot read is a file it is not inspecting, and a
            # check that silently drops its subject is the failure mode this repo keeps finding.
            print('UNREADABLE: %s (%s)' % (rel, exc))
            sys.exit(2)

        # Does it print at all? A module that never writes to stdout cannot die on encoding.
        prints = any(
            isinstance(n, ast.Call)
            and (getattr(n.func, 'id', None) == 'print'
                 or getattr(n.func, 'attr', None) in ('write', 'print'))
            for n in ast.walk(tree)
        )
        if not prints:
            continue

        scanned.append(rel)
        # Parse for the call rather than grepping the text, so a mention in a comment or a
        # docstring -- like the one in this file's own header -- does not count as doing it.
        pinned = False
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            if getattr(n.func, 'attr', None) != 'reconfigure':
                continue
            target = n.func.value
            if getattr(target, 'attr', None) == 'stdout' or getattr(target, 'id', None) == 'stdout':
                if any(k.arg == 'encoding' for k in n.keywords):
                    pinned = True
                    break
        if not pinned:
            unpinned.append(rel)

# ⚠️ POSITIVE CONTROL, derived rather than a literal. A gate that inspects nothing prints "ok",
# and this one would if the AST walk stopped matching the print shape. State what was inspected.
if len(scanned) < 5:
    print('only %d printing script(s) found under %s; the AST walk has probably stopped '
          'matching, and this gate is reporting on an empty set'
          % (len(scanned), '/'.join(SCANNED)))
    sys.exit(2)

print('%d printing script(s) inspected under %s' % (len(scanned), ', '.join(SCANNED)))

if unpinned:
    print('\n%d script(s) print without pinning stdout to UTF-8. On Windows these die with a '
          'UnicodeEncodeError the first time they print a ⚠️ -- which is the first time they '
          'have a finding:' % len(unpinned))
    for u in unpinned:
        print('  x', u)
    print("\nAdd, after the imports:\n"
          "    sys.stdout.reconfigure(encoding='utf-8', errors='replace')")
    sys.exit(1)

print('OK: every printing script pins stdout, so a gate can report a finding without dying on it.')
