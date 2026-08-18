"""Mutation battery for UI1 (the conformance snapshot).

Why this battery exists, specifically:

The 18 original UI1 tests were written RED, before the implementation, and every one
of them turned green. That looked like evidence and was not enough. The review panel
then found ten upheld defects in exactly the code those 18 tests passed against, and
three of them were things no assertion could have caught, because every one of the 18
used ONE instrument, ONE relationship and a fresh engine -- the suite could not
REPRESENT a second instrument, so no test over it could fail on one.

That is the same lesson as the NT8 stub that omitted six OrderStates, and it is why
this battery exists rather than a fourth review round: a test that cannot express the
failure is not coverage, and only a mutant proves which is which.

The two that matter most:

  * MUTANT 7 restores the exact defect that shipped in the first green implementation
    -- a leader position the follower does not mirror reported as a verdict that reads
    as fine. If it survives, the snapshot can still hide a copier that copied nothing,
    which is the single divergence this whole ticket was written to surface.

  * MUTANT 11 makes a rejected latency count as a sample. If it survives, the metric
    pair can report `Samples > 0` with a stale or zero value -- a FALSE "measured" --
    which is `P?-66` inverted, and worse than the original defect because it reads as
    a real reading rather than an obvious blank.

MUTANT 4 is the selection guard. Ui1Row() originally took the first row matching the
account name, which is how all 18 passed against code that counted an unrelated ES
position as the NQ mirror. The assertions were sound; the SELECTION was accidental.

A crash counts as a kill (see handover section 5.14: a mutant that killed the runner
produced no result line and was scored a SURVIVOR).

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    # ---- verdict precedence: each rung of the chain, independently ----
    ("QUARANTINED stops winning, so a quarantined relationship whose positions happen to\n"
     "     AGREE reports MATCH -- the copier is not copying and the UI calls it correct",
     '                if (rel.IsQuarantined)\n                    verdict = CopierConformance.Quarantined;',
     '                if (false)\n                    verdict = CopierConformance.Quarantined;'),

    ("ORPHAN stops being detected, so a live position on a funded account that the leader\n"
     "     has already left is reported as an ordinary divergence",
     '                else if (leaderSide == MarketPosition.Flat && actualSide != MarketPosition.Flat)\n                    verdict = CopierConformance.Orphan;',
     '                else if (false)\n                    verdict = CopierConformance.Orphan;'),

    ("SHADOW stops being detected, so a disarmed relationship reports DIVERGED -- the\n"
     "     consequence -- and hides the cause, sending the operator after a copier fault\n"
     "     that does not exist",
     '                else if (rel.IsEnabled && !rel.ArmedForLive)\n                    verdict = CopierConformance.Shadow;',
     '                else if (false)\n                    verdict = CopierConformance.Shadow;'),

    # ---- THE selection mutant: per-instrument attribution ----
    ("instrument filtering is removed -- any position on the account answers for any root,\n"
     "     so a follower's unrelated ES position becomes the mirror of the leader's NQ.\n"
     "     This is the defect the original 18 passed against",
     '                    string pRoot = GetRootFromPosition(p);\n                    if (string.Equals(pRoot, root, StringComparison.OrdinalIgnoreCase))\n                        return p;',
     '                    return p;'),

    # ---- enumeration ----
    ("the snapshot stops asking for quarantined relationships, so a quarantined follower\n"
     "     vanishes from the display entirely -- config disappearing without an error",
     'includeQuarantined: true);',
     'includeQuarantined: false);'),

    # ---- expected quantity comes from the engine, not a second copy ----
    # ⚠️ RETIRED MUTANT, recorded rather than deleted.
    #
    # "the leader quantity loses its Math.Abs" SURVIVED, and it is UNKILLABLE BY
    # CONSTRUCTION rather than evidence of a test gap. In NT8 -- and faithfully in the
    # stub -- Position.Quantity is the ABSOLUTE contract count and direction lives in
    # MarketPosition, so a short position is Quantity=2/Short, never -2. The Math.Abs is
    # defensive and cannot change behaviour the platform is able to produce.
    #
    # The tempting "fix" was to teach the stub to emit a negative quantity. That is worse
    # than the gap: a double that can express a failure the real system CANNOT manufactures
    # evidence for a defect that does not exist -- the mirror image of a double that cannot
    # express a real one, which is how six omitted OrderStates hid a live P0 behind a green
    # suite. Keep the Math.Abs (the ticket asks for it and it costs nothing); do not keep a
    # mutant that can only ever survive.
    #
    # Replaced by the mutant below, which attacks what the short-leader test actually
    # defends: that the SIDE is carried separately and taken from the leader.
    ("the expected side is hardcoded Long, so a correctly mirrored SHORT position reports a\n"
     "     divergence on every short trade -- the side stops being derived from the leader",
     '                    expectedSide = expectedQty > 0 ? leaderSide : MarketPosition.Flat;',
     '                    expectedSide = expectedQty > 0 ? MarketPosition.Long : MarketPosition.Flat;'),

    # ---- THE suppressed-failure mutant ----
    ("a leader position the follower does not mirror is suppressed entirely, so the copier\n"
     "     having copied NOTHING produces no row at all",
     '                    rows.Add(BuildSnapshotRow(rel, groupName, latencyValue, latencySamples, slippageValue, slippageSamples, lp, null, root, root));\n                    }\n\n                    if (rows.Count == 0)',
     '                    }\n\n                    if (rows.Count == 0)'),

    ("the clamped-to-zero reconciliation is removed, so a relationship at its position cap\n"
     "     reports a permanent false DIVERGED",
     '                    if (expectedIsClamped && expectedQty == 0)\n                    {\n                        effectiveExpectedSide = actualSide;\n                        effectiveExpectedQty = actualQty;\n                    }',
     ''),

    ("side divergence stops being checked, so a follower holding the right SIZE in the\n"
     "     WRONG DIRECTION reports MATCH",
     '                    if (effectiveExpectedSide != actualSide || effectiveExpectedQty != actualQty)',
     '                    if (effectiveExpectedQty != actualQty)'),

    # ---- metrics: the pair is the whole point ----
    ("the sample count is hardcoded to 1, so 'never measured' becomes indistinguishable\n"
     "     from 'measured once' -- the exact confusion this ticket removes",
     '                    Latency = new CopierMetric { Value = latencyValue, Samples = latencySamples },',
     '                    Latency = new CopierMetric { Value = latencyValue, Samples = 1 },'),

    # ---- THE false-measured mutant ----
    ("a latency REJECTED by the sanity bound counts as a sample, so the pair reports\n"
     "     Samples > 0 against a stale or zero value -- a FALSE 'measured', which is worse\n"
     "     than a blank because it reads as a real reading",
     # P2-98 moved the accept/reject verdict onto the pending copy, because it is now taken
     # once per COPY (on the first slice) rather than once per fill. Re-anchored, same mutant.
     '            if (pending.LatencyAccepted)\n            {\n                lock (_lock)\n                {\n                    rel.LatencyMs = pending.LatencyMs;',
     '            if (true)\n            {\n                lock (_lock)\n                {\n                    if (pending.LatencyAccepted) rel.LatencyMs = pending.LatencyMs;'),

    ("the latency counter is never incremented, so a genuinely measured fill still reports\n"
     "     'never measured' and the operator distrusts a working measurement",
     '                    _latencySampleCounts[rel.Id] = n;',
     ''),
]


def run():
    b = subprocess.run(['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if 'Build succeeded' not in b.stdout:
        return 'BUILD FAILED'
    r = subprocess.run(['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    for line in r.stdout.splitlines():
        if line.startswith('RESULTS:'):
            return line.strip()
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if '[FAIL]' not in ((r.stdout or '') + (r.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return 'NO RESULT LINE'


original = open(ENGINE, encoding='utf-8').read()
print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print(f'\nREFUSING TO RUN: baseline is RED ({m.group(2)} failing). Every mutant would '
          'score KILLED on pre-existing failures and this battery would prove nothing.')
    sys.exit(2)

survivors = []
for name, old, new in MUTANTS:
    if original.count(old) != 1:
        print(f'  [SKIP] {name}: anchor matched {original.count(old)} times')
        survivors.append(name + ' (ANCHOR)')
        continue
    open(ENGINE, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    # A crash is a kill: the mutation stopped the suite completing.
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
    print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
    if not killed:
        survivors.append(name)

open(ENGINE, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
