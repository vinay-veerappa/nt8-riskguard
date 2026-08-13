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
    'RunCopierPreflight':
        "P3-34 shipped preflight but not its caller. Where the copier 'arms' is a design "
        "decision (the copier acts regardless of guard mode -- that is the open half of "
        "P3-34), so wiring it is part of closing P3-34, not a drive-by fix.",
    'ReconcileFollowerPosition':
        "Sits inside `#if !TESTING`, so it has ZERO coverage, and it FLATTENS a live "
        "follower position. Wiring an uncovered flatten into a 5-second timer is not a "
        "drive-by change. Needs P2-27 coverage first, then P3-30's copier half.",
}


def call_sites(name, sources):
    """Call sites for `name`, excluding its own declaration and commented-out lines."""
    hits = []
    call = re.compile(r'\b' + re.escape(name) + r'\s*\(')
    for path, text in sources.items():
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith('//') or stripped.startswith('*'):
                continue
            if not call.search(line):
                continue
            if ENTRY_POINT.match(line):      # the declaration itself
                continue
            hits.append('%s:%d' % (os.path.basename(path), lineno))
    return hits


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
