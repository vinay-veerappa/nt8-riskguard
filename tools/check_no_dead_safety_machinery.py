"""P2-24's class, made mechanical: safety machinery that is written and never called.

P2-24 was `CalculateSafeFollowerDelta` -- a method that computed a safe follower size and
was called by nothing, so the safety it described did not exist. It was closed in session
34 by deleting the method. In the SAME session the class recurred three more times:

  * `StartAuditTimer`        -- P3-30's guard audit shipped with nothing calling it, while
                                `AuditIntervalSeconds: 10` sat in the LIVE config describing
                                a ten-second audit that never ran. Fixed.
  * `RunCopierPreflight`     -- P3-34's preflight. Tests call it; production does not.
  * `ReconcileFollowerPosition` -- the handover records it as "called by the P3-31 timer".
                                The timer calls SyncFollowerStopOnce/SyncFollowerTargetOnce.

Three recurrences in one session is what turns a defect into a gate. A method in this
class passes every other check this repo runs: it compiles, the suite is green (its tests
call it directly), a source scan finds the field it reads, and the config surface that
advertises it looks configured. Only "does anything actually CALL this" separates them,
and that is the one question no other gate here asks.

Scope is deliberately narrow -- name shapes that in this codebase always mean "a periodic
or preflight safety entry point". Widening it to every private method would produce noise,
and a gate that is noisy is a gate nobody reads (section 0).

An entry point that is genuinely not wired yet goes in KNOWN_DEAD **with a reason and the
defect ID that will wire it**. That is the difference between a recorded gap and a silent
one; the gate fails if a KNOWN_DEAD entry is later wired, so the list cannot rot into a
permanent excuse.

Exits 1 on any unrecorded dead entry point, or on a KNOWN_DEAD entry that has since been
wired.
"""
import os
import re
import sys

# ⚠️ Windows defaults stdout to cp1252. Every gate in this repo prints mutant
# descriptions and plan text full of non-ASCII, and it only needs to print them
# when it is FAILING -- so without this a gate dies exactly when it has something
# to say, and the traceback reads as a defect in the script rather than a finding.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ADDONS = os.path.join(REPO, 'addons')

# Name shapes that mean "periodic or preflight safety entry point" in this codebase.
ENTRY_POINT = re.compile(
    r'^\s*(?:public|private|internal|protected)[\w\s]*?\s'
    r'(Start\w*Timer|Run\w*Preflight|Run\w*Audit|Reconcile\w+)\s*\(')

# Entry points known to be unwired, each with the reason and the ID that will wire it.
# Wiring one of these without removing it from here is also a failure: the gate must not
# be able to describe the code inaccurately in either direction.
KNOWN_DEAD = {
    # RunCopierPreflight was here. It is now called by TrySetCopierMode, which refuses the
    # transition to `live` when preflight fails -- and this gate is what reported that it had
    # been wired, which is the reason the WIRED-BUT-LISTED direction exists.
    'ReconcileFollowerPosition':
        "Sits inside `#if !TESTING`, so it has ZERO coverage, and it FLATTENS a live "
        "follower position. Wiring an uncovered flatten into a 5-second timer is not a "
        "drive-by change. Needs P2-27 coverage first, then P3-30's copier half.",
}


# ⚠️ A CALL INSIDE A STATICALLY-DEAD BRANCH IS NOT A CALL, and this gate could not see the
# difference until 2026-08-17. Measured: `mutate_p2136survive.py` wrapped the only production
# call site of `ReconcilePersistedBrackets` in `if (false)` and BOTH this gate and a C# source
# assertion still reported it WIRED, because the call text is right there. The whole restore path
# was dead and every gate this repo has was green.
#
# That is the third time an `if (false)` has beaten a text search here -- `P0-67`'s guard survived
# `if (false)` over the entire body at 2113/0, and a `-1 < 1022` ordering assertion passed on the
# baseline it existed to reject. A regex cannot see reachability, so the dead regions are DELETED
# before anything is searched. [[a-backstop-at-a-choke-point-is-unkillable]],
# [[a-source-gate-must-assert-the-condition]].
DEAD_HEAD = re.compile(r'\b(?:if|while)\s*\(\s*(?:false|0)\s*\)')


def mask_comments_and_strings(text):
    """
    Comments and string literals replaced by spaces, newlines kept so offsets and line numbers are
    unchanged.

    ⚠️ THIS IS NOT TIDINESS, IT IS THE FIRST VERSION'S BUG. Without it, `DynamicAtmManager.cs:854`
    -- a DOC COMMENT that says "replaced the entire guard with `if (false)` and the whole suite
    stayed green" -- was read as a dead branch, and the single-statement walk then deleted forward
    to the next `;`, taking the two REAL `ReconcileStopFromBroker` call sites with it. The gate
    reported a live, wired, load-bearing method as DEAD. A comment ABOUT a mutant is not a mutant.
    """
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] != '\n':
                out[i] = ' '
                i += 1
        elif c == '/' and i + 1 < n and text[i + 1] == '*':
            while i < n and not (text[i] == '*' and i + 1 < n and text[i + 1] == '/'):
                if text[i] != '\n':
                    out[i] = ' '
                i += 1
            for _ in range(2):
                if i < n:
                    out[i] = ' '
                    i += 1
        elif c == '@' and i + 1 < n and text[i + 1] == '"':
            out[i] = ' '
            i += 2
            out[i - 1] = ' '
            while i < n:
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':      # "" is an escaped quote
                        out[i] = out[i + 1] = ' '
                        i += 2
                        continue
                    out[i] = ' '
                    i += 1
                    break
                if text[i] != '\n':
                    out[i] = ' '
                i += 1
        elif c == '"' or c == "'":
            quote = c
            out[i] = ' '
            i += 1
            while i < n and text[i] != quote:
                if text[i] == '\\' and i + 1 < n:
                    out[i] = out[i + 1] = ' '
                    i += 2
                    continue
                if text[i] != '\n':
                    out[i] = ' '
                i += 1
            if i < n:
                out[i] = ' '
                i += 1
        else:
            i += 1
    return ''.join(out)


def strip_dead_branches(text):
    """Blank out `if (false)` / `while (0)` bodies, single-statement or braced, and `#if false`."""
    # Searched and walked on the MASKED copy so a `;` in a string or a mutant named in a comment
    # cannot move the boundaries; the ranges found are then blanked out of that same copy.
    text = mask_comments_and_strings(text)
    out = []
    i = 0
    while True:
        m = DEAD_HEAD.search(text, i)
        if m is None:
            out.append(text[i:])
            break

        out.append(text[i:m.start()])

        # Walk past the head to the body.
        j = m.end()
        while j < len(text) and text[j] in ' \t\r\n':
            j += 1

        if j < len(text) and text[j] == '{':
            depth = 0
            while j < len(text):
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
        else:
            # A single statement: to the next `;` at nesting depth 0.
            depth = 0
            while j < len(text):
                if text[j] in '({[':
                    depth += 1
                elif text[j] in ')}]':
                    depth -= 1
                elif text[j] == ';' and depth <= 0:
                    j += 1
                    break
                j += 1

        # Keep the NEWLINES so reported line numbers stay honest -- a gate that names the wrong
        # line is a gate an operator stops trusting.
        out.append('\n' * text.count('\n', m.start(), j))
        i = j

    stripped = ''.join(out)

    # `#if false` / `#if 0` regions, same reasoning.
    stripped = re.sub(r'#if\s+(?:false|0)\b.*?#endif',
                      lambda m: '\n' * m.group(0).count('\n'),
                      stripped, flags=re.DOTALL)
    return stripped


def call_sites(name, sources):
    """Call sites for `name`, excluding its own declaration, comments and dead branches."""
    hits = []
    call = re.compile(r'\b' + re.escape(name) + r'\s*\(')
    for path, text in sources.items():
        for lineno, line in enumerate(strip_dead_branches(text).splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith('//') or stripped.startswith('*'):
                continue
            if not call.search(line):
                continue
            if ENTRY_POINT.match(line):      # the declaration itself
                continue
            hits.append('%s:%d' % (os.path.basename(path), lineno))
    return hits


def self_test():
    """
    ⚠️ THE NEGATIVE CONTROL, and it runs on every invocation.

    A dead-branch stripper that strips too much makes every call site vanish and this gate then
    fails on the whole repo -- loud, and someone fixes it. A stripper that strips NOTHING makes the
    gate pass on the exact mutant it was written for -- silent, and it stays broken for sessions.
    So the second direction is asserted here rather than trusted. A gate whose own detector has no
    negative test is a detector that fires on everything.
    """
    live = 'void Caller() { ReconcileThing(); }'
    dead_inline = 'void Caller() { try { if (false) ReconcileThing(); } catch {} }'
    dead_block = 'void Caller() { if (false)\n{\n    ReconcileThing();\n}\n}'
    dead_pp = 'void Caller() {\n#if false\n    ReconcileThing();\n#endif\n}'
    # The regression the masker exists for: a doc comment DESCRIBING an `if (false)` mutant, with a
    # real call after it. This is the shape that made the gate call a wired method dead.
    commented = ('/// replaced the guard with `if (false)` and the suite stayed green\n'
                 'void Caller() { ReconcileThing(); }')
    # And the same hazard from a string literal, which the walk would also have run through.
    in_string = 'void Caller() { Log("if (false) is how it broke; really"); ReconcileThing(); }'

    problems = []
    for label, src in (('a plain call', live),
                       ('a call after a comment mentioning if (false)', commented),
                       ('a call after a string containing if (false) and a semicolon', in_string)):
        if 'ReconcileThing' not in strip_dead_branches(src):
            problems.append('%s was stripped -- the stripper is too greedy, and a greedy '
                            'stripper reports WIRED methods as dead' % label)
    for label, src in (('inline if (false)', dead_inline),
                       ('braced if (false)', dead_block),
                       ('#if false', dead_pp)):
        if 'ReconcileThing' in strip_dead_branches(src):
            problems.append('a call inside %s was NOT stripped -- the mutant that beat this gate '
                            'on 2026-08-17 would beat it again' % label)
    if problems:
        print('SELF-TEST FAILED -- this gate cannot be trusted:\n')
        for p in problems:
            print('  * ' + p)
        sys.exit(1)


self_test()


sources = {}
for fname in sorted(os.listdir(ADDONS)):
    if fname.endswith('.cs'):
        path = os.path.join(ADDONS, fname)
        sources[path] = open(path, encoding='utf-8').read()

declared = {}
for path, text in sources.items():
    for line in text.splitlines():
        m = ENTRY_POINT.match(line)
        if m:
            declared.setdefault(m.group(1), path)

failures = []
print('Safety entry points declared in addons/:\n')
for name in sorted(declared):
    sites = call_sites(name, sources)
    recorded = name in KNOWN_DEAD
    if sites:
        status = 'WIRED'
        if recorded:
            status = 'WIRED-BUT-LISTED'
            failures.append(
                '%s is wired (%s) but is still listed in KNOWN_DEAD. Remove it from the '
                'list -- a gate that misdescribes the code in EITHER direction is worse '
                'than no gate.' % (name, ', '.join(sites[:3])))
    else:
        status = 'KNOWN-DEAD' if recorded else 'DEAD'
        if not recorded:
            failures.append(
                '%s is declared in %s and called by NOTHING. This is P2-24\'s class: '
                'safety machinery that compiles, passes its own tests, and does not run. '
                'Wire it, delete it, or record it in KNOWN_DEAD with the ID that will '
                'wire it.' % (name, os.path.basename(declared[name])))
    print('  [%-16s] %-30s %s' % (status, name, ', '.join(sites[:3]) if sites else '--'))

for name in sorted(KNOWN_DEAD):
    if name not in declared:
        failures.append(
            '%s is in KNOWN_DEAD but is no longer declared in addons/. If it was deleted, '
            'remove the entry.' % name)

if failures:
    print('\nFAILED:\n')
    for f in failures:
        print('  * ' + f + '\n')
    sys.exit(1)

print('\nOK: every safety entry point is either wired or recorded as KNOWN_DEAD with a reason.')
print('    %d recorded dead: %s' % (len(KNOWN_DEAD), ', '.join(sorted(KNOWN_DEAD))))
