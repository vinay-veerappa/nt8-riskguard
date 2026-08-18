"""Check every mutation battery's anchors WITHOUT running a single mutant.

⚠️ WHY THIS EXISTS. A battery whose find-string no longer matches prints `[SKIP]`
and scores that mutant a SURVIVOR -- but only when the battery is RUN, and a
battery is only run when the suite is green. So an anchor broken by an unrelated
commit stays invisible for exactly as long as it takes to notice, and this repo
has been caught twice: `mutate_ui2.py`'s anchor was broken by the UI7 commit and
went unnoticed because only the battery that "looked touched" was re-run.

Each battery run is minutes of `dotnet build` per mutant. This is a substring
count, so it is instant -- which means it can be run after EVERY commit that
touches `addons/`, including while the suite is red.

It imports nothing: importing a battery module executes it, because they run at
import time by design. It reads the MUTANTS list out of the source instead.

Exits non-zero if any anchor does not match exactly once.
"""
import ast
import glob
import io
import os
import re
import sys

# ⚠️ Windows defaults stdout to cp1252. Every gate in this repo prints mutant
# descriptions and plan text full of non-ASCII, and it only needs to print them
# when it is FAILING -- so without this a gate dies exactly when it has something
# to say, and the traceback reads as a defect in the script rather than a finding.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# A READ that pins newline='' -- i.e. `open(..., ...).read()` carrying newline='' with no 'w'/'a'
# mode. Deliberately narrow: the WRITE half (`open(path, 'w', ..., newline='')`) is correct and
# every battery does it. See the block in main() for what this defends.
READS_WITH_RAW_NEWLINES = re.compile(
    r"open\((?![^)]*['\"][wa])[^)]*newline=''[^)]*\)\s*\.\s*read\(\)")

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def strip_cs_comments(src):
    """`src` with every // and /* */ comment blanked to spaces, offsets and lines preserved.

    ⚠️ WHY THIS EXISTS (P2-152). Counting occurrences cannot tell code from commentary, and
    this repo's comments quote the code they replaced -- deliberately, because that is how a
    defect's history stays readable. The two habits collide. When P2-145 replaced the audit's
    inline predicate, the comment explaining the change contained the old predicate verbatim,
    so mutate_p330's find-string still matched EXACTLY ONCE and this gate reported it healthy.
    The mutant was editing a comment: no effect, suite green, scored SURVIVED -- a mutant
    proving nothing while every gate said otherwise. [[mutation-anchors-go-stale]] in the form
    that is hardest to see, because the anchor still matches. It matches the wrong thing.

    Offsets are preserved (comments become spaces, newlines kept) so a match position found in
    the ORIGINAL text indexes the same span here. That is what lets the caller ask "is THIS
    match inside a comment?" rather than the much weaker "does this text appear outside
    comments somewhere?" -- an anchor may legitimately SPAN a comment, and 13 of the 508
    anchors in this repo do exactly that. The weaker question fails all 13.
    """
    out = list(src)
    i, n = 0, len(src)
    in_line = in_block = in_str = in_chr = False
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if in_line:
            if c == '\n':
                in_line = False
            else:
                out[i] = ' '
        elif in_block:
            if c == '*' and nxt == '/':
                out[i] = out[i + 1] = ' '
                i += 2
                in_block = False
                continue
            if c != '\n':
                out[i] = ' '
        elif in_str:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                in_str = False
        elif in_chr:
            if c == '\\':
                i += 2
                continue
            if c == "'":
                in_chr = False
        else:
            if c == '/' and nxt == '/':
                in_line = True
                out[i] = ' '
            elif c == '/' and nxt == '*':
                in_block = True
                out[i] = ' '
            elif c == '"':
                in_str = True
            elif c == "'":
                in_chr = True
        i += 1
    return ''.join(out)


def literal(node):
    """Fold a `'a' 'b'` / `'a' + 'b'` string expression down to its value."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = literal(node.left), literal(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def paths_in(tree, module_path):
    """The `NAME = os.path.join(REPO, 'addons', 'X.cs')` constants at module level."""
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        call = node.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == 'join'):
            continue
        parts = [literal(a) for a in call.args[1:]]
        if any(p is None for p in parts):
            continue
        out[target.id] = os.path.join(REPO, *parts)
    return out


def mutants_in(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id == 'MUTANTS':
            return node.value
    return None


def main():
    bad = 0
    checked = 0
    for battery in sorted(glob.glob(os.path.join(REPO, 'mutation', 'mutate_*.py'))):
        name = os.path.basename(battery)
        battery_src = io.open(battery, encoding='utf-8').read()
        tree = ast.parse(battery_src)
        consts = paths_in(tree, battery)
        mutants = mutants_in(tree)

        # ⚠️ THIS GATE READS THE TARGET WITH UNIVERSAL NEWLINES (below), so every anchor it
        # verifies is matched against text whose line endings are '\n'. A battery that reads its
        # ORIGINALS with `newline=''` gets the file's REAL endings instead -- CRLF in this repo --
        # and its multi-line anchors then match NOTHING, while this gate goes on reporting them ok.
        #
        # Measured 2026-08-15: mutate_p2112.py was the only battery of 32 to do that. Locally it
        # scored 9/9 and this gate printed 334/0, because earlier battery runs had already rewritten
        # the worktree copy to LF. On a FRESH CHECKOUT -- which is all CI ever has -- 7 of its 9
        # anchors matched 0 times and scored as survivors. A LOCAL WORKTREE IS NOT A FRESH CHECKOUT,
        # and the two disagreed precisely because the gate and the battery read the file differently.
        #
        # So this is not a style rule: it is the condition under which this gate's evidence is
        # about the same string the battery will search. Fail loudly rather than validate a
        # different string. (Writing with newline='' is correct and untouched -- it stops Python
        # translating on the way OUT. Only the READ is banned.)
        if READS_WITH_RAW_NEWLINES.search(battery_src):
            bad += 1
            checked += 1
            print("%-24s x reads its ORIGINALS with newline='' -- this gate matches anchors "
                  "against\n%-24s   universal-newline text, so it would validate a string the "
                  "battery never searches.\n%-24s   Drop newline='' from the READ (keep it on the "
                  "write)." % (name, '', ''))
            continue

        if mutants is None or not isinstance(mutants, (ast.List, ast.Tuple)):
            print('%-24s SKIPPED -- no literal MUTANTS list to read' % name)
            continue

        # A battery is either 3-tuples (one implicit file) or 4-tuples (path first).
        default_path = None
        for key in ('TARGET', 'SOURCE', 'ENGINE', 'ADDON'):
            if key in consts:
                default_path = consts[key]
                break
        if default_path is None and len(consts) == 1:
            default_path = list(consts.values())[0]

        sources = {}
        stripped_sources = {}
        problems = []
        for entry in mutants.elts:
            if not isinstance(entry, (ast.Tuple, ast.List)):
                continue
            items = list(entry.elts)
            # 4-tuples name their target file with a module constant. Both orders occur --
            # (PATH, label, old, new) and (label, PATH, old, new) -- so find the Name rather
            # than assuming a position.
            if len(items) == 4:
                named = [i for i, it in enumerate(items) if isinstance(it, ast.Name)]
                if len(named) == 1 and named[0] in (0, 1):
                    path = consts.get(items[named[0]].id)
                    label = literal(items[1 - named[0]])
                    old = literal(items[2])
                else:
                    path = label = old = None
            elif len(items) == 3:
                path = default_path
                old = literal(items[1])
                label = literal(items[0])
            else:
                path = label = old = None

            # ⚠️ An unrecognised entry shape used to `continue`, so a battery whose tuples this
            # parser could not read printed `ok` having checked NOTHING. P2-107's battery landed
            # with its file constant second, all 18 anchors were skipped in silence, and the
            # gate reported clean -- which is *a gate nobody reads is a comment* wearing the
            # gate's own output. Not being able to read an entry is a FAILURE, not a skip: this
            # check's whole product is the count of anchors it verified.
            if path is None or old is None:
                checked += 1
                problems.append('  ? entry %d: could not read it statically (%d element(s)). This '
                                'check cannot skip what it cannot parse.' % (len(problems) + 1, len(items)))
                continue
            if path not in sources:
                sources[path] = io.open(path, encoding='utf-8').read()
            hits = sources[path].count(old)
            checked += 1
            if hits != 1:
                short = (label or old).strip().splitlines()[0][:70]
                problems.append('  x %-16s matched %d time(s): %s'
                                % (os.path.basename(path), hits, short))
            else:
                # P2-152. Exactly one match is necessary and NOT sufficient: that one match may
                # be inside a comment, in which case the mutant edits prose, cannot be killed,
                # and this gate calls it healthy. Ask about THIS match's span, not whether the
                # text appears in code anywhere -- an anchor that SPANS a comment is legitimate.
                if path not in stripped_sources:
                    stripped_sources[path] = strip_cs_comments(sources[path])
                at = sources[path].find(old)
                if not stripped_sources[path][at:at + len(old)].strip():
                    short = (label or old).strip().splitlines()[0][:70]
                    problems.append(
                        '  x %-16s matches ONLY INSIDE A COMMENT, so the mutant edits prose and '
                        'can never be killed: %s' % (os.path.basename(path), short))

        if problems:
            bad += len(problems)
            print('%-24s %d BROKEN ANCHOR(S)' % (name, len(problems)))
            for p in problems:
                print(p)
        else:
            print('%-24s ok' % name)

    print('\n%d anchor(s) checked, %d broken' % (checked, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
