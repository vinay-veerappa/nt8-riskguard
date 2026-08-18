import io
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load(p):
    raw = io.open(p, "rb").read().decode("utf-8")
    return raw.replace("\r\n", "\n"), ("\r\n" if "\r\n" in raw else "\n")


def save(p, s, nl):
    io.open(p, "wb").write(s.replace("\n", nl).encode("utf-8"))


# ---------------------------------------------------------------------------------------
# 1. INSTANCE: drop mutate_p330's inverted-comparison mutant. Its anchor is the OLD inline
#    predicate, which P2-145 replaced -- so the only remaining occurrence is the comment in
#    RiskGuardAddOn.cs that quotes it, and the mutant was editing that comment.
# ---------------------------------------------------------------------------------------
p = "mutation/mutate_p330.py"
s, nl = load(p)

old = """    ("the coverage comparison is inverted to `covered > positionQty`. A partially covered\\n"
     "     position -- P0-55's exact shape -- stops being reported, and a fully covered one\\n"
     "     starts being reported. Both directions wrong from one character",
     'if (!isProtected || covered < positionQty)',
     'if (!isProtected || covered > positionQty)'),
"""
new = """    # ⚠️ MUTANT REMOVED 2026-08-18 (P2-152), and this note is the point of the removal.
    #
    # It inverted the coverage comparison in the audit's inline predicate:
    #     'if (!isProtected || covered < positionQty)' -> '... covered > positionQty'
    #
    # P2-145 replaced that predicate with `RiskGuardAddOn.AssessCoverage`, so the only
    # remaining occurrence of the find-string is the COMMENT in RiskGuardAddOn.cs that quotes
    # the old predicate to explain what it replaced. The mutant was editing a comment: no
    # effect, suite green, scored SURVIVED -- and `check_anchors.py` reported it healthy the
    # whole time, because the text still matched EXACTLY ONCE. An anchor that matches a comment
    # is as dead as one that matches nothing, and it is harder to see.
    #
    # ⚠️ NOT re-pointed at AssessCoverage, deliberately. mutate_p2145coverage.py groups 1 and 2
    # already mutate that comparison there, in more spellings than this one had (the state test,
    # the `<=` off-by-one, and the tempting wrong fix). Two batteries rewriting one line is a
    # collision risk for no extra evidence.
"""
assert s.count(old) == 1, "p330 mutant anchor matched %d" % s.count(old)
s = s.replace(old, new)
save(p, s, nl)
compile(io.open(p, encoding="utf-8").read(), p, "exec")
print("1/3 mutate_p330: inverted-comparison mutant removed")

# ---------------------------------------------------------------------------------------
# 2. CLASS: teach check_anchors.py that a comment-only match is a broken anchor.
# ---------------------------------------------------------------------------------------
p = "mutation/check_anchors.py"
s, nl = load(p)
assert "strip_cs_comments" not in s, "already hardened"

helper = '''

def strip_cs_comments(src):
    """`src` with every // and /* */ comment blanked to spaces, offsets preserved.

    ⚠️ WHY THIS EXISTS (P2-152). Counting occurrences cannot tell code from commentary, and
    this repo's comments quote the code they replaced -- deliberately, because that is how a
    defect's history stays readable. The two habits collide: when P2-145 replaced the audit's
    inline predicate, the comment explaining the change contained the old predicate verbatim,
    so mutate_p330's find-string still matched EXACTLY ONCE and this gate reported it healthy.
    The mutant was editing a comment. It had no effect, the suite stayed green, and it scored
    SURVIVED -- a mutant proving nothing while every gate said otherwise.
    [[mutation-anchors-go-stale]], in the form that is hardest to see: the anchor still matches,
    just the wrong thing.

    Offsets are preserved (comments become spaces, newlines are kept) so that a match position
    found in the ORIGINAL text indexes the same span here. That is what lets the caller ask
    "is this particular match inside a comment?" rather than the much weaker "does this text
    appear outside comments somewhere?" -- an anchor that legitimately SPANS a comment must
    still pass, and 13 of the 508 anchors in this repo do exactly that.
    """
    out = list(src)
    i, n = 0, len(src)
    in_line = in_block = in_str = in_chr = False
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ''
        if in_line:
            if c == '\\n':
                in_line = False
            else:
                out[i] = ' '
        elif in_block:
            if c == '*' and nxt == '/':
                out[i] = out[i + 1] = ' '
                i += 2
                in_block = False
                continue
            if c != '\\n':
                out[i] = ' '
        elif in_str:
            if c == '\\\\':
                i += 2
                continue
            if c == '"':
                in_str = False
        elif in_chr:
            if c == '\\\\':
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

'''

anchor_def = "def literal(node):"
assert s.count(anchor_def) == 1
s = s.replace(anchor_def, helper.lstrip("\n") + "\n" + anchor_def, 1)

old_count = """            hits = sources[path].count(old)
            checked += 1
            if hits != 1:
                short = (label or old).strip().splitlines()[0][:70]
                problems.append('  x %-16s matched %d time(s): %s'
                                % (os.path.basename(path), hits, short))
"""
new_count = """            hits = sources[path].count(old)
            checked += 1
            if hits != 1:
                short = (label or old).strip().splitlines()[0][:70]
                problems.append('  x %-16s matched %d time(s): %s'
                                % (os.path.basename(path), hits, short))
            else:
                # P2-152. Exactly one match is necessary and NOT sufficient: the one match may
                # be inside a comment, in which case the mutant edits prose and scores SURVIVED
                # while this gate calls it healthy. Ask about THIS match's span rather than
                # whether the text appears in code anywhere -- an anchor that spans a comment
                # is legitimate and 13 anchors here do.
                if path not in stripped_sources:
                    stripped_sources[path] = strip_cs_comments(sources[path])
                at = sources[path].find(old)
                if not stripped_sources[path][at:at + len(old)].strip():
                    short = (label or old).strip().splitlines()[0][:70]
                    problems.append(
                        '  x %-16s matches ONLY INSIDE A COMMENT, so the mutant edits prose '
                        'and can never be killed: %s' % (os.path.basename(path), short))
"""
assert s.count(old_count) == 1, "count block matched %d" % s.count(old_count)
s = s.replace(old_count, new_count)

old_src = "            if path not in sources:"
assert s.count(old_src) == 1
s = s.replace(old_src, old_src)  # no-op, keeps the anchor honest

# The stripped cache needs declaring beside `sources`.
old_decl = "    sources = {}"
if s.count(old_decl) == 1:
    s = s.replace(old_decl, "    sources = {}\n    stripped_sources = {}")
else:
    import re
    m = re.search(r"^(\s*)sources\s*=\s*\{\}\s*$", s, re.M)
    assert m, "could not find the sources cache declaration"
    s = s[:m.end()] + "\n%sstripped_sources = {}" % m.group(1) + s[m.end():]

save(p, s, nl)
compile(io.open(p, encoding="utf-8").read(), p, "exec")
print("2/3 check_anchors.py: comment-only anchors now fail")
print("3/3 done")
