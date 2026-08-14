"""An ordering list must not name a defect that is already CLOSED.

⚠️ **WHAT THIS CATCHES, measured 2026-08-14 (session 39).** The handover's "what to do next"
blocks had been carrying **six closed IDs**. `P2-95`, `P2-93` and `P2-94` were closed in session
34 and still headed the order of work nine sessions later; all three `P?-` UI write items were
closed in §5.13 and §5.21 and were still listed as outstanding. CLAUDE.md's anchor in the
consumer repo told a reader to *"weigh `P2-95` first now"* for those nine sessions.

Nobody added them back. Each session record ends with an "Order from here" block, and each one
was written by copying the previous session's and striking the item just closed -- so an item
closed *without* being at the head of the list was never struck by anybody. **Closures propagate
forward into the record and never backwards into the ordering**, which is the same failure §0
warns about one level down: a hand-maintained summary of entries that are themselves maintained.

The cost is not cosmetic. The ordering block is the one thing a session reads before choosing
what to work on, so a stale entry spends a whole session's attention on work already done -- and
the reader who notices cannot tell which of the remaining entries are also wrong.

**The check, and it fails in BOTH directions** so neither half can rot:

  * every defect ID named inside an ordering block MUST be an entry in the plan whose heading
    status is OPEN. A CLOSED, FIXED or SUPERSEDED entry named as work-to-do fails;
  * every `### Pn-m.` heading in the plan MUST carry a recognised status token, because the
    first half is only as good as the status it reads. This is the half that would have rotted:
    when this was written **14 entries carried no status at all** -- including the whole
    `P0-1`...`P0-8` block, closed since phase 1 and recorded as closed only in prose two hundred
    lines above the entries.

⚠️ Status is read from a **token at the end of the heading**, never by searching the line for the
substring `CLOSED`. `P1-105`'s heading is *"`nt_close_position` reports `positionClosed: true`
after submitting nothing -- OPEN"*, and a substring check reads that open defect as closed. That
is not hypothetical: it is how the first draft of this audit lost it.

Exits non-zero on any violation. Wired into CI beside `check_expected_survivors.py`.
"""
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PLAN = os.path.join(REPO, 'docs', 'RISKGUARD_COPIER_HARDENING_PLAN.md')
HANDOVER = os.path.join(REPO, 'docs', 'RISKGUARD_HARDENING_HANDOVER.md')

# A plan entry heading: "### P1-106. <title> -- <STATUS ...>", optionally struck through with ~~.
HEADING = re.compile(r'^### (~~)?(?P<id>P[0-9?]+-[0-9]+)\.\s*(?P<rest>.*)$')

DEFECT_ID = re.compile(r'\bP[0-9?]+-[0-9]+\b')

# ⚠️ An ordering block legitimately CITES closed defects -- the prior art that tells you how to fix
# the open one. `P1-106`'s entry names `P1-97` (read the position, not the label) and `P1-44`
# (`IsPositionReducingOrder`), both closed, both the reason the fix is cheap. A check that flagged
# those would be wrong in the direction that gets checks deleted.
#
# So a closed ID is exempt only when it is marked closed WITHIN 60 characters of itself. That
# keeps the catch this gate exists for: the real drift was a trailing enumeration reading
# "then `P1-105`, `P2-103`, `P2-95`." -- an unmarked list, which is still flagged. Deciding by
# POSITION instead (first ID in the item is the work, later ones are citations) was the other
# candidate and it fails exactly there, since all three sat mid-sentence.
#
# ⚠️ The window was 30 first, and 30 makes you REWRITE HONEST PROSE to satisfy the gate -- a
# sentence naming three closed IDs before the word "closed" tripped it. Contorting the text to
# pass is how a check starts costing more than it returns, and the repo has that lesson already:
# *a too-broad test gets the CODE broken to satisfy it*. 60 still flags the drift this exists
# for, because that line carried no marker at all.
CITATION_WINDOW = 60
CITATION_MARK = re.compile(r'✅|\bclosed\b', re.IGNORECASE)

# Read the status from the LAST em-dash / double-hyphen separated segment of the heading, not
# from anywhere in the line. See the docstring: `positionClosed` sits mid-title in an OPEN entry.
SEPARATOR = re.compile(r'\s(?:—|--)\s')

CLOSED_TOKENS = ('CLOSED', 'FIXED', 'SUPERSEDED', 'DONE', 'RESOLVED')
OPEN_TOKENS = ('OPEN', 'DEFERRED', 'HONESTLY REPORTED')

# PARTIALLY / HALF CLOSED means work REMAINS, so an ordering list may legitimately name it.
PARTIAL_PREFIXES = ('PARTIALLY ', 'HALF ')

# ⚠️ WHICH blocks this polices, and why not all of them. Every session record ends with its own
# ordering block, and those are HISTORY -- they record the order that session chose, which is the
# reusable part. Rewriting them to match today's closures would falsify the record, exactly as
# §5.6's own convention says (finished items are struck through, not deleted). So the gate reads
# only the LIVE navigation surfaces, and treats a struck-through heading as history by
# construction:
#
#   1. §0's `| **Do next** |` state-table row;
#   2. the first NOT-struck-through `> ### Do next:` blockquote in §5.6;
#   3. the LAST `### Order from here` block in the file -- the newest, which is the one §0 sends
#      a reader to.
ROW_START = re.compile(r'^\|\s*\*\*do next\*\*\s*\|', re.IGNORECASE)
DO_NEXT = re.compile(r'^>\s*###\s+(?P<struck>~~)?\s*Do next\b', re.IGNORECASE)
ORDER_FROM_HERE = re.compile(r'^###\s+(?P<struck>~~)?\s*Order from here\b', re.IGNORECASE)


def entry_status(rest):
    """Return ('open'|'closed'|None, raw_token) for a plan heading.

    ⚠️ The status is the FIRST separated segment that opens with a recognised token, not the last
    one. Several headings carry an explanation after the status that itself contains em-dashes
    (`P1-72`'s is eight lines long), so reading the tail lands somewhere in the prose.
    """
    for seg in SEPARATOR.split(rest)[1:]:
        tail = seg.strip().lstrip('✅⚠️~* ').rstrip('~* ').strip()
        upper = tail.upper()
        for pre in PARTIAL_PREFIXES:
            if upper.startswith(pre) and any(t in upper for t in CLOSED_TOKENS):
                return 'open', tail
        for tok in CLOSED_TOKENS:
            if upper.startswith(tok):
                return 'closed', tail
        for tok in OPEN_TOKENS:
            if upper.startswith(tok):
                return 'open', tail
    return None, rest


def load_plan():
    statuses, unstated = {}, []
    for line in open(PLAN, encoding='utf-8'):
        m = HEADING.match(line.rstrip('\n'))
        if not m:
            continue
        state, tail = entry_status(m.group('rest'))
        if state is None:
            unstated.append((m.group('id'), m.group('rest')[:70]))
        else:
            statuses[m.group('id')] = state
    return statuses, unstated


def _span(lines, start, is_quote):
    """Lines of the block opened at index `start`, to the next heading at the same level."""
    out = []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if is_quote:
            if DO_NEXT.match(line) or not line.startswith('>'):
                break
        elif line.startswith('#'):
            break
        if line.strip():
            out.append((i + 1, line))
    return out


def ordering_blocks(path):
    """Return (label, [(line_number, text), ...]) for each LIVE ordering surface."""
    lines = open(path, encoding='utf-8').read().splitlines()
    found = []

    for i, line in enumerate(lines):
        if ROW_START.match(line):
            found.append(('S0 "Do next" row', [(i + 1, line)]))
            break

    for i, line in enumerate(lines):
        m = DO_NEXT.match(line)
        if m:
            if m.group('struck'):
                continue                      # superseded by convention; history, not a list
            found.append(('S5.6 live "Do next"', [(i + 1, line)] + _span(lines, i, True)))
            break

    last = None
    for i, line in enumerate(lines):
        m = ORDER_FROM_HERE.match(line)
        if m and not m.group('struck'):
            last = i
    if last is not None:
        found.append(('newest "Order from here"', _span(lines, last, False)))

    return found


def main():
    if not os.path.exists(PLAN) or not os.path.exists(HANDOVER):
        print('REFUSING: plan or handover not found. This check would pass vacuously.')
        return 2

    statuses, unstated = load_plan()
    if not statuses:
        print('REFUSING: no plan entry headings parsed. This check would pass vacuously.')
        return 2

    blocks = ordering_blocks(HANDOVER)
    if len(blocks) < 3:
        print('REFUSING: expected 3 live ordering surfaces, found %d %s.\n'
              '          Either the markers changed or the file did; a check that inspects\n'
              '          nothing reports nothing.'
              % (len(blocks), [b[0] for b in blocks]))
        return 2

    problems = []
    named = set()
    inspected = 0

    for label, lines in blocks:
        inspected += len(lines)
        for lineno, line in lines:
            for m in DEFECT_ID.finditer(line):
                did = m.group(0)
                state = statuses.get(did)
                if state == 'closed':
                    near = line[max(0, m.start() - CITATION_WINDOW):m.end() + CITATION_WINDOW]
                    if CITATION_MARK.search(near):
                        continue          # cited as prior art, and says so
                named.add(did)
                if state is None:
                    problems.append(
                        '%s:%d (%s) names %s, which has no entry in the plan.\n'
                        '    An ordering list is not the place to introduce an ID.'
                        % (os.path.basename(HANDOVER), lineno, label, did))
                elif state == 'closed':
                    problems.append(
                        '%s:%d (%s) lists %s as work to do, but its plan entry is CLOSED.\n'
                        '    Strike it in the commit that closes it. If work REMAINS inside a\n'
                        '    closed entry, that work needs its own ID -- IDs are never reused,\n'
                        '    so a remainder hiding under a closed one is invisible to every count.'
                        % (os.path.basename(HANDOVER), lineno, label, did))

    for label, lines in blocks:
        print('  %-26s %d line(s)' % (label, len(lines)))
    print('  distinct IDs named as next     %d' % len(named))
    print('  plan entries with a status     %d' % len(statuses))
    print('  plan entries WITHOUT a status  %d' % len(unstated))
    print('')

    if unstated:
        print('FAIL: %d plan entr(y/ies) carry no status token, so the check above cannot read\n'
              '      them. Append " -- OPEN" or " -- CLOSED <date>" to each heading:\n' % len(unstated))
        for did, rest in unstated:
            print('  * %-8s %s' % (did, rest.encode('ascii', 'replace').decode('ascii')))
        print('')

    if problems:
        print('FAIL: %d ordering entr(y/ies) name a defect that is not open:\n' % len(problems))
        for p in problems:
            print('  * ' + p + '\n')

    if problems or unstated:
        return 1

    print('OK: every ID named as work-to-do is an OPEN plan entry, and every plan entry states')
    print('    its status. Neither half can pass while the other is unmaintained.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
