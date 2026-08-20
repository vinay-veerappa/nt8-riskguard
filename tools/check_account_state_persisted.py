"""Gate: every field on AccountState is CLASSIFIED -- persisted, or deliberately not.

WHY THIS EXISTS. P1-170: `RealizedPnL` is the number every PnL rail reads and was the one field in
its cluster absent from `AccountPersistedData`, while `LastRealizedPnL` and `SessionStartRealizedPnL`
-- the two values that derive it -- were both persisted. A recompile therefore left the daily-loss
rail reading `currentValue: 0` on an account down $347.75 against a $250 limit it had already
breached, and the next PnL tick handed the whole session's loss to the loss counter as one
fabricated trade.

Nothing was wrong with any individual line. The defect was an OMISSION, and an omission has no
source location for a reviewer to look at. That is what a gate is for.

⚠️ THIS IS A RATCHET, NOT AN AUDIT. The baseline below is the set of AccountState fields that were
already unpersisted when the gate was written. Most have never been reviewed, and this file does NOT
claim they are correctly classified -- inventing a justification for forty fields I had not studied
would be worse than no gate, because it would read as a review that happened. What the gate
guarantees is narrower and real: A FIELD ADDED FROM NOW ON MUST BE CLASSIFIED. Entries move from
UNREVIEWED to one of the deliberate lists as someone actually looks at them.

⚠️ It is a NAME match, not a semantic one. A field present in both classes is called persisted here;
whether the restore path actually reads it back is a different question and not one a name can
answer -- `RealizedPnL` would still have failed this gate, but a field that is persisted, written,
and never restored would pass it. That gap is real and unclosed.
"""
import os
import re
import sys

# stdout pinned before anything prints: a cp1252 console cannot encode the glyphs below, and a
# gate that dies while printing its finding reports nothing at all.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

# Deliberately runtime-only, each with the reason. Anything here has been looked at.
RUNTIME_ONLY = {
    'ReplaySuppressionUntilUtc':
        'P0-171. A reconnect-replay suppression deadline restored from disk is a suppression the '
        'guard cannot account for, on a rule whose whole safety argument is that its suppression '
        'is bounded by one window.',
    'DuplicateEntryEvaluatedOrders':
        'P0-171. Holds live Order object references, which cannot be serialised and must not '
        'outlive the session that created them. Cleared on session reset for the same reason.',
    'OpenTradeRealizedDelta':
        'P1-16, explicitly. Half a trade\'s realized PnL is not a result; persisting it would '
        'invent one across a restart. Settles as a scratch instead.',
    'ClosedTradeAwaitingLateFills':
        'P1-16. Scoped to the window between a flat transition and the next entry, which cannot '
        'span a restart.',
    'ConsecutiveLossesBeforeSettlement':
        'P1-16. The pre-settlement snapshot exists only to re-judge the trade currently closing.',
    'RecentOrderIds':
        'P2-46. A rate-limit window measured in seconds; nothing in it can still be inside the '
        'window after a restart.',
    'RecentEntryAnchors':
        'P1-160. Holds live Order object references and is bounded by a duplicate-entry window of '
        'about a second.',
    'RuleRefusedOrders':
        'P1-167. Holds live Order object references keyed by rule id, so it cannot be serialised '
        'and must not outlive the session that created them -- an order reference from last '
        'session can never come back, and a restored one would suppress a refusal for an order '
        'that no longer exists. Cleared on session reset with RecentEntryAnchors, for the same '
        'reason and in the same place.',
}

# Derived from persisted fields on restore -- NOT persisted, deliberately, because a stored copy
# would be a second source for one number, free to disagree with the identity that defines it.
DERIVED_ON_RESTORE = {
    'RealizedPnL':
        'P1-170. Reconstructed as LastRealizedPnL - SessionStartRealizedPnL, an identity that '
        'holds at every site writing any of the three.',
    'TotalRealizedPnL':
        'Computed property: CumulativeRealizedPnL + RealizedPnL. Has no backing field.',
}

# Persisted, but not by name in AccountPersistedData -- so a name match cannot see them.
PERSISTED_ELSEWHERE = {
    'AccountName':
        'It is the KEY of the AccountsData dictionary, so it is on disk by construction.',
    'IsLockedOut':
        'Persisted as membership of the top-level LockedOutAccounts list rather than as a field, '
        'and restored from it. P2-92.',
}

# Deliberately reset by a restart. ⚠️ These are REASONED, not measured -- each says why, and none
# has a test proving the reset is harmless.
RESET_BY_DESIGN = {
    'Positions':
        'Re-derived from the broker on subscribe and on reconnect. A stored copy would be a '
        'second, staler answer to a question the broker already answers.',
    'UnrealizedPnL':
        'Recomputed from the broker feed on every position update; a persisted value is wrong the '
        'moment the market moves.',
    'InitialLockoutFlattened':
        'P2-101 phase machinery. Reset on phase entry; a restart mid-lockout should re-attempt '
        'the flatten rather than believe a previous process already did it.',
    'LastLockoutFlattenAttempt':
        'P2-101. The retry clock for the above, meaningless across a process boundary.',
    'LockoutPhaseAttempts':
        'P2-101. Per-phase attempt count, reset on phase entry.',
    'LockoutStuckLogged':
        'P2-101. Whether THIS phase has already written its give-up warning.',
    'CurrentLockoutPhase':
        'P2-101. Re-entered from None after a restart, which re-runs the cancel/flatten sequence. '
        'The lockout itself survives via LockedOutAccounts; only the phase restarts.',
}

# ⚠️ SUSPECTED INSTANCES OF P1-170'S CLASS, each with a filed ID. Listed so the gate passes while
# naming them, rather than burying them in a baseline. Empty is the goal, not the norm: an entry
# leaves here by being FIXED, and CooldownUntil left on 2026-08-20 by being added to
# AccountPersistedData under P1-173 -- after which the name match picks it up and no declaration
# is needed at all.
SUSPECTED_DEFECT = {}

# ⚠️ NOT REVIEWED. The state of the world when this gate was written. Do not read this list as a
# set of decisions -- read it as a to-do. Moving an entry out of here requires deciding what it
# actually is and writing the reason down.
#
# ✅ IT IS EMPTY, and staying empty is the goal. The three that were here -- PeakOpenGain,
# PeakGivebackTriggered and PeakGivebackLastTriggerUnrealized -- were P1-174, and they left by
# being added to AccountPersistedData in v1.52.6, exactly as the note here predicted.
#
# ⚠️ THEY DID NOT LEAVE BY THEMSELVES, AND THAT WAS A HOLE IN THIS GATE. The name match DID
# pick them up once persisted -- so for a session they were counted as persisted AND still printed
# as unreviewed on every run. The stale check below could not see it, because it only asked whether
# a declared name is still an AccountState property, and it was. A declaration and a persistence
# are MUTUALLY EXCLUSIVE CLAIMS about one field; `contradicted` now says so.
# [[closures-do-not-propagate-backwards]]
#
# ⚠️ `set()`, NOT `{}`. Emptying a set literal makes an empty DICT, and this gate unions it
# with real sets -- so the obvious edit crashes with a TypeError instead of passing. Loud, and
# therefore the good version of that failure; the quiet version is an `All` over an empty sequence
# returning true. [[closing-the-last-instance-disarms-the-gate]]
UNREVIEWED_BASELINE = set()


def _class_body(text, name):
    m = re.search(r'\bclass\s+' + re.escape(name) + r'\b', text)
    if not m:
        return None
    i = text.index('{', m.end())
    depth = 0
    for j in range(i, len(text)):
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
            if depth == 0:
                return text[i:j]
    return None


PROP = re.compile(r'^\s*public\s+(?:readonly\s+)?[\w<>,\[\]\?\. ]+?\s+(\w+)\s*(?:\{|=>)', re.M)

# A nested type declaration matches the property shape exactly -- `public enum LockoutPhase {`
# parses as "public <type> <name> {". Caught by AccountState declaring the LockoutPhase enum
# inside itself, which the gate then demanded be persisted.
NOT_A_PROPERTY = (' enum ', ' class ', ' struct ', ' interface ', ' void ')


def props(body):
    out = []
    for m in PROP.finditer(body):
        line = body[m.start():m.end()]
        # A '(' before the brace means a method, not a property.
        if '(' in line:
            continue
        if any(k in line for k in NOT_A_PROPERTY):
            continue
        out.append(m.group(1))
    return out


def main():
    text = open(MODELS, encoding='utf-8').read()

    state_body = _class_body(text, 'AccountState')
    persisted_body = _class_body(text, 'AccountPersistedData')
    if state_body is None or persisted_body is None:
        print('FAIL: could not locate AccountState and/or AccountPersistedData in %s'
              % os.path.relpath(MODELS, REPO))
        return 1

    state_props = props(state_body)
    persisted_props = set(props(persisted_body))

    # ⚠️ Refuse to pass vacuously. A parse that finds nothing must not read as "all classified".
    # [[closing-the-last-instance-disarms-the-gate]] and [[state-the-region-a-gate-inspects]].
    if len(state_props) < 20 or len(persisted_props) < 10:
        print('FAIL: parsed only %d AccountState and %d AccountPersistedData properties, which is '
              'too few to be a real read of these classes. The parser has stopped matching -- fix '
              'it rather than trusting this run.' % (len(state_props), len(persisted_props)))
        return 1

    unclassified = []
    for p in state_props:
        if p in persisted_props:
            continue
        if (p in RUNTIME_ONLY or p in DERIVED_ON_RESTORE or p in UNREVIEWED_BASELINE
                or p in PERSISTED_ELSEWHERE or p in RESET_BY_DESIGN or p in SUSPECTED_DEFECT):
            continue
        unclassified.append(p)

    # A declaration that has stopped applying is as bad as a missing one: it reads as a decision
    # that was made about something no longer there. Fail in that direction too.
    known = set(state_props)
    stale = sorted((set(RUNTIME_ONLY) | set(DERIVED_ON_RESTORE) | UNREVIEWED_BASELINE
                    | set(PERSISTED_ELSEWHERE) | set(RESET_BY_DESIGN)
                    | set(SUSPECTED_DEFECT)) - known)

    # ⚠️ THE SECOND STALENESS DIRECTION, and the one this gate was blind to. A field that is BOTH
    # declared here and present in AccountPersistedData carries two contradictory claims: the
    # declaration says "deliberately not persisted, here is why" and the DTO says "persisted". Only
    # one can be true, and whichever it is, the other is a decision recorded about a world that no
    # longer exists. P1-174's three fields sat in the unreviewed baseline for a session AFTER being
    # persisted, printed as unreviewed on every run, because the check above only asked whether the
    # name was still an AccountState property -- which it was. RUNTIME_ONLY is the dangerous one to
    # leave: it reads as a considered reason not to persist a field that IS persisted.
    contradicted = sorted((set(RUNTIME_ONLY) | set(DERIVED_ON_RESTORE) | UNREVIEWED_BASELINE
                           | set(RESET_BY_DESIGN) | set(SUSPECTED_DEFECT))
                          & set(persisted_props))

    print('  AccountState properties         %d' % len(state_props))
    print('  of those, in AccountPersistedData %d'
          % sum(1 for p in state_props if p in persisted_props))
    print('  declared runtime-only           %d' % len(RUNTIME_ONLY))
    print('  declared derived-on-restore     %d' % len(DERIVED_ON_RESTORE))
    print('  persisted elsewhere             %d' % len(PERSISTED_ELSEWHERE))
    print('  reset by design                 %d' % len(RESET_BY_DESIGN))
    print('  SUSPECTED DEFECT                %d  %s'
          % (len(SUSPECTED_DEFECT), ', '.join(sorted(SUSPECTED_DEFECT)) or '-'))
    print('  unreviewed baseline             %d  %s'
          % (len(UNREVIEWED_BASELINE), ', '.join(sorted(UNREVIEWED_BASELINE)) or '-'))

    if unclassified:
        print()
        print('FAIL: %d AccountState field(s) are neither persisted nor classified:' % len(unclassified))
        for p in unclassified:
            print('  * %s' % p)
        print()
        print('    Decide which it is and say so, in ONE of three places:')
        print('      - add it to AccountPersistedData and to BOTH copy sites, if a rail reads it;')
        print('      - RUNTIME_ONLY here, with the reason it must not survive a restart;')
        print('      - DERIVED_ON_RESTORE here, if the restore path reconstructs it.')
        print('    P1-170 is what this catches: the daily-loss rail read 0 on an account down $347')
        print('    because one field in a cluster of three was left out, and no line was wrong.')
        return 1

    if stale:
        print()
        print('FAIL: %d declaration(s) name a field AccountState no longer has:' % len(stale))
        for p in stale:
            print('  * %s' % p)
        print('    A declaration about a field that is gone reads as a decision someone made.')
        return 1

    if contradicted:
        print()
        print('FAIL: %d field(s) are BOTH declared here and persisted in AccountPersistedData:'
              % len(contradicted))
        for p in contradicted:
            print('  * %s' % p)
        print('    Those are contradictory claims about the same field. Delete the declaration --')
        print('    the DTO membership is the live fact and the name match already classifies it.')
        print('    P1-174 is what this catches: three fields kept printing as UNREVIEWED for a')
        print('    session after they were persisted, because the check above only asked whether')
        print('    the declared name was still an AccountState property, and it was.')
        return 1

    print()
    print('OK: every AccountState field is persisted, declared runtime-only, declared derived,')
    print('    or in the unreviewed baseline -- every declaration still names a real field, and')
    print('    no field is both declared and persisted.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
