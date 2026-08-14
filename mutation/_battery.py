"""Shared exit logic for the mutation batteries, for the one case the batteries got wrong.

⚠️ **WHY THIS EXISTS.** Every battery ended with `sys.exit(1 if survivors else 0)`, which is
right for the 22 batteries whose every mutant must die. Two batteries declare a mutant that is
*expected* to survive and say so in prose:

  * `mutate_p330.py` — the lock-scope mutant. The audit's broker reads are not driven by the lock
    invariant, so no test can see it move.
  * `mutate_p096.py` — the reconciler mutant. `ReconcileFollowerPosition` is inside `#if !TESTING`
    and is called by nothing (`check_no_dead_safety_machinery.py` records it as KNOWN_DEAD), so no
    test in this suite can reach it.

Both were therefore **red by design**, and CI failed on every push from the moment they landed —
**10 consecutive runs across three sessions**, discovered 2026-08-14 (session 36). The prose said
"expected to SURVIVE"; the exit code said FAIL; nothing reconciled the two. That is this repo's
own recurring lesson — *a gate nobody reads is a comment* — instantiated **inside the gate**, and
it is worse than the version in the docs, because a permanently red CI trains its readers to stop
looking at a signal that is otherwise the only thing checking 24 batteries and 263 anchors.

**The rule.** A mutant's description declares its own expectation; there is no second list to
drift out of step with it (a second copy of a fact is a second thing to forget). A description
beginning `EXPECTED SURVIVOR:` must survive. Everything else must die.

**It fails in BOTH directions**, like `tools/check_no_dead_safety_machinery.py`:

  * an UNEXPECTED survivor fails — the battery's whole purpose;
  * an expected survivor that gets **KILLED** also fails. That is good news — a test now reaches
    it — but it means the declaration is stale, and a stale exemption is how an allowlist rots
    into a blanket. Delete the marker in the same commit as the test that earned it.

A broken ANCHOR always fails, expected or not: a mutant whose find-string no longer matches
proves nothing at all, which is what `mutation/check_anchors.py` exists for.
"""
import sys

EXPECTED_PREFIX = 'EXPECTED SURVIVOR:'


def finish(survivors, mutants):
    """Print the verdict and exit. `survivors` is the list built by the battery's loop (mutant
    descriptions, with ' (ANCHOR)' appended for a find-string that did not match); `mutants` is
    the battery's MUTANTS list, from which the expectations are read."""
    declared = set(name for name, _old, _new in mutants if name.startswith(EXPECTED_PREFIX))

    anchor_breaks = sorted(s for s in survivors if s.endswith(' (ANCHOR)'))
    survived = set(s for s in survivors if not s.endswith(' (ANCHOR)'))

    unexpected = sorted(survived - declared)
    stale = sorted(declared - survived)

    print('\nSURVIVORS:', sorted(survived) if survived else 'none')
    if declared:
        print('EXPECTED to survive:', len(declared))

    ok = True

    for a in anchor_breaks:
        print('\nFAIL: anchor did not match -- ' + a)
        print('      A mutant whose find-string no longer matches proves NOTHING, and scores a')
        print('      false survivor. Re-anchor it; see mutation/check_anchors.py.')
        ok = False

    for u in unexpected:
        print('\nFAIL: unexpected survivor -- ' + u)
        print('      No test can tell this mutant from the real code. Write one, or declare the')
        print('      mutant EXPECTED SURVIVOR: with the reason no test can reach it.')
        ok = False

    for s in stale:
        print('\nFAIL: an EXPECTED SURVIVOR was KILLED -- ' + s)
        print('      That is good news: a test now reaches it. But the declaration is now FALSE,')
        print('      and a stale exemption is how an allowlist rots into a blanket. Remove the')
        print('      EXPECTED SURVIVOR: marker in the same commit as the test that earned it.')
        ok = False

    if ok:
        print('\nOK: every mutant died except the %d declared unreachable, and each of those'
              % len(declared))
        print('    survived exactly as declared.' if declared else '    -- none declared.')

    sys.exit(0 if ok else 1)
