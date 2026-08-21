"""Mutation battery for P1-71 and P1-70 -- the copier's audit log.

P1-71: a named relationship dropped a copy in silence.
P1-70: the log asserted a modification had happened before the provider settled.

The deliverable for this defect is an INVARIANT, not a set of log lines: every
relationship named in COPY_BEGIN produces exactly one terminal outcome event.
So the mutants here attack the invariant from both directions:

  * remove an outcome  -> a relationship goes silent again (the original defect)
  * add an outcome     -> a NON-terminal event is renamed to look terminal, which
                          inflates the count and would let a real drop hide behind
                          a warning

The second direction matters more than it looks. The convention is what makes the
invariant self-maintaining -- a skip path added next year is counted because of how
it is named -- so the boundary between "terminal" and "informational" is itself
load-bearing and has to be pinned by a test rather than by a comment.

Written the same day as the fix, because the four P1-71 tests were written
ALONGSIDE the fix and had therefore never been seen to fail. That is the
lying-harness shape this directory exists to catch, and it does not stop applying
just because the author is aware of it.

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    # ---- direction 1: remove an outcome, and a relationship goes silent ----
    ("the vanished-account path returns in silence again (the original P1-71 defect)",
     '                    CopierLog(rel.FollowerAccountName, "COPY_SKIPPED_ACCOUNT_MISSING",',
     '                    CopierLog(rel.FollowerAccountName, "ACCOUNT_MISSING_UNCOUNTED",'),

    ("a successful copy stops announcing itself, so the invariant can be met by skips alone",
     '                        CopierLog(followerAcc.Name, "COPY_SUBMITTED",',
     '                        CopierLog(followerAcc.Name, "SUBMITTED_UNCOUNTED",'),

    ("an exit with nothing to close goes quiet -- the most frequent benign skip",
     '                        CopierLog(followerAcc.Name, "COPY_SKIPPED_NO_POSITION_TO_EXIT",',
     '                        CopierLog(followerAcc.Name, "NO_POSITION_UNCOUNTED",'),

    ("refusing a disarmed LIVE follower stops reaching the audit log",
     '                    CopierLog(followerAcc.Name, "COPY_BLOCKED_NOT_ARMED",',
     '                    CopierLog(followerAcc.Name, "NOT_ARMED_UNCOUNTED",'),

    # ---- direction 2: inflate the count with a non-terminal event ----
    # Both of these events fire on a copy that PROCEEDS. If either is named into the
    # terminal convention, one relationship reports two outcomes -- and then a second
    # relationship dropping in silence still totals the right number.
    ("the quarantine notice is renamed to look terminal, so a quarantined exit double-counts",
     '                    CopierLog(rel.FollowerAccountName, "QUARANTINE_EXIT_ALLOWED",',
     '                    CopierLog(rel.FollowerAccountName, "COPY_SKIPPED_QUARANTINED",'),

    ("the clamp WARNING is renamed to look terminal, so a clamped copy double-counts",
     '                    CopierLog(followerAcc.Name, "COPY_QTY_CLAMPED",',
     '                    CopierLog(followerAcc.Name, "COPY_SKIPPED_QTY_CLAMPED",'),

    # ---- P1-70: the modify log must describe a request, then an observed outcome ----
    ("the modify request is announced as a completed modification again (the P1-70 defect)",
     '                            CopierLog(followerAcc.Name, "BRACKET_MODIFY_REQUESTED",',
     '                            CopierLog(followerAcc.Name, "BRACKET_MODIFIED",'),

    ("the settle confirmation disappears, so an honoured change is never recorded as honoured",
     '                    CopierLog(acc.Name, isStopLeg ? "BRACKET_MODIFY_CONFIRMED" : "BRACKET_TARGET_MODIFY_CONFIRMED",',
     '                    CopierLog(acc.Name, isStopLeg ? "MODIFY_CONFIRMED_UNPINNED" : "TARGET_CONFIRMED_UNPINNED",'),

    ("the confirmation reports the REQUESTED values instead of the settled ones, hiding a partial honour",
     '                        + $"at {currentQty}@{currentPrice} (requested {req.RequestedQuantity}@{req.RequestedPrice}, "',
     '                        + $"at {req.RequestedQuantity}@{req.RequestedPrice} (requested {req.RequestedQuantity}@{req.RequestedPrice}, "'),
]

# Known-unpinnable, kept OUT of the executable list and documented instead -- a
# battery carrying a permanent survivor becomes the thing it exists to catch:
#
#   COPY_FAILED_CREATE_ORDER_NULL -- the NT8 test stub's CreateOrder never returns
#   null, so no test can reach this branch. It is the path that produced no trace at
#   all in production and it is the one this suite cannot exercise. Closing it needs a
#   stub flag (SimulateCreateOrderReturnsNull), which belongs with the other stub gaps
#   recorded in mutate_p0_63.py rather than being faked here.
#
#   COPY_FAILED_SUBMIT -- same reason: Submit does not throw in the stub.
#
#   SYMBOL_TRANSLATION_UNRESOLVED -- reachable only with AutoSymbolConversion mapping
#   to a name Instrument.GetInstrument refuses, which the stub's registry resolves
#   permissively. Non-terminal, so it does not affect the invariant either way.
#
# STILL OPEN, and stated precisely because a vague gap gets forgotten: the
# QUANTITY-refusal partial honour (P0-62's exact live shape -- `2@29742.5` requested,
# `1@29742.5` delivered) is NOT covered. The confirmation line's settled-vs-requested
# divergence is now pinned by SimulateChangeSettlesOneTickAway, which is a realistic
# provider rounding and kills the mutant -- but it exercises the PRICE, not the quantity.
#
# Reaching the quantity case needs the mirrored stop to GROW, and the mirrored stop's size
# is Math.Min(qty, livePos.Quantity) where `qty` is the BRACKET's recorded quantity, not
# the leader stop's. Three attempts failed to grow it: raising the leader's position,
# driving a second follower entry (DriveFollowerEntry SETS the position rather than adding
# to it), and setting the follower position directly all left the request at qty 1.
# Whoever closes it should start at FollowerBracket.Quantity and how a scale-in updates it,
# NOT at the test.


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

# Refuse a red baseline. Scoring every mutant KILLED against an already-failing
# suite is how cm3 and cm4 were decorative until 2026-08-13.
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
    killed = _battery.score(res, run)
    print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
    if not killed:
        survivors.append(name)

open(ENGINE, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
