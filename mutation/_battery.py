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

P1-179 (the double-kill). `is_kill` and `score` below are the SHARED kill decision. Every battery
scored a mutant inline, and `failed_count > 0` was the whole test -- ANY reason the suite went red
read as "the mutant was detected", including a flaky test, a machine hiccup, or a collision with
another battery on the box. That is silent and it INFLATES (a mis-scored kill is a green battery
with no survivor and no warning), which is the opposite of the loud false-SURVIVOR that
`check_anchors.py` exists to catch. `score` re-runs an apparent kill and requires it to reproduce.

⚠️ It runs ONLY under `RG_DOUBLE_KILL`, which `tools/ci_local.py` sets. That is deliberate, not a
half-measure: the accident it guards (e.g. the `P1-175` temp-file collision) needs two batteries
CONTENDING on one machine, which happens only in the local parallel runner. GitHub CI runs one bin
per hosted runner with nothing else on the box, cannot reproduce the accident, and so pays nothing
-- the env var is unset there and every battery runs exactly once, its scoring byte-for-byte as
before. [[a-source-gate-must-assert-the-condition]]
"""
import os
import re
import sys

# ⚠️ Windows defaults stdout to cp1252. Every gate in this repo prints mutant
# descriptions and plan text full of non-ASCII, and it only needs to print them
# when it is FAILING -- so without this a gate dies exactly when it has something
# to say, and the traceback reads as a defect in the script rather than a finding.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

EXPECTED_PREFIX = 'EXPECTED SURVIVOR:'

# P1-179. Set by tools/ci_local.py only; see the module docstring for why it is local-only.
DOUBLE_KILL = os.environ.get('RG_DOUBLE_KILL') == '1'


def is_kill(res, base_failed=0):
    """The kill decision. A harness crash with no assertion is NOT a detection (P2-148 / P1-153):
    before that fix the first mutant to THROW killed the process before `RESULTS:` printed, and a
    missing result line scores KILLED, so a crash scored a free kill. A BUILD FAILED, a missing
    result line, or MORE failed assertions than the baseline had (`base_failed`, 0 for the green
    batteries) is a real detection. `res` is a battery `run()`'s return string."""
    if 'NO ASSERTION FAILED' in res:
        return False
    mm = re.search(r'Failed = (\d+)', res)
    # 'GATE FAILED' / 'GATE TIMEOUT' are produced only by mutate_p2136survive, whose run() drives a
    # gate rather than the suite; harmless elsewhere since no other battery's res can contain them.
    return (('BUILD FAILED' in res) or ('NO RESULT LINE' in res)
            or ('GATE FAILED' in res) or ('GATE TIMEOUT' in res)
            or (mm is not None and int(mm.group(1)) > base_failed))


def score(res, rerun, base_failed=0):
    """True iff the mutant is KILLED. Under DOUBLE_KILL an apparent kill must reproduce: `rerun()`
    re-runs the suite with the SAME mutant still applied -- the caller restores only AFTER scoring,
    in its `finally` -- and a kill that does not reproduce is scored a SURVIVOR, because a real
    detection is deterministic and an accident usually is not. A SURVIVOR is never re-run: it is
    already the loud, investigated outcome, and re-running it would only add cost to the case that
    already gets human attention (P1-179)."""
    if not is_kill(res, base_failed):
        return False
    if not DOUBLE_KILL:
        return True
    return is_kill(rerun(), base_failed)


def _description(mutant):
    """The mutant's description, whichever shape its battery uses.

    Single-file batteries hold `(name, old, new)`; the six that mutate TWO files hold
    `(path, name, old, new)`. Unpacking three from a four-tuple raises ValueError, so before
    this existed the FIRST four-tuple battery to declare an EXPECTED SURVIVOR would have
    crashed here -- and `tools/check_expected_survivors.py` REQUIRES a declaring battery to
    route through this function, so the gate would have been forcing a call into a crash.
    """
    if len(mutant) == 4:
        return mutant[1]
    if len(mutant) == 3:
        return mutant[0]
    raise ValueError(
        'a MUTANTS entry must be (name, old, new) or (path, name, old, new); got %d fields. '
        'Add the shape here rather than reshaping the battery to suit this helper.' % len(mutant))


def finish(survivors, mutants):
    """Print the verdict and exit. `survivors` is the list built by the battery's loop (mutant
    descriptions, with ' (ANCHOR)' appended for a find-string that did not match); `mutants` is
    the battery's MUTANTS list, from which the expectations are read."""
    declared = set(_description(m) for m in mutants
                   if _description(m).startswith(EXPECTED_PREFIX))

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
