"""Mutation battery for P0-96: the copier read a position's SIDE off the SIGN of its quantity.

⚠️ THIS ONE PLACED A REAL, WRONG-DIRECTION ORDER, AND 1300 GREEN TESTS DID NOT SEE IT.

`Position.Quantity` in NT8 is ABSOLUTE -- the side lives in `MarketPosition`, which is
why that property exists. Every one of the ~1300 tests in this suite already models a
short as `MarketPosition.Short` with a POSITIVE quantity; not one uses a negative
quantity. Two places read the sign anyway:

  1. The copy path's exit alignment:

         if (currentFollowerPos < 0) followerAction = OrderAction.BuyToCover;  // UNREACHABLE
         else if (currentFollowerPos > 0) followerAction = OrderAction.Sell;   // BOTH sides

     So a leader COVERING A SHORT sent the follower a Sell. A Sell does not close a
     short -- it DOUBLES it, in a direction the leader has already left. The copier's own
     log said so plainly once a test drove it:

         COPY_SUBMITTED: MNQ 03-26 Sell 1 submitted to 'SimFollower'
                         mirroring leader 'SimLeader' BuyToCover 1@18000 (isExit=True)

     P0-5's family (`Copier exit sizing is not position-mirroring -> follower reverses`).

  2. `ReconcileFollowerPosition`'s direction check compared the signs of two quantities
     that are never negative, so `directionMismatch` could never be true -- the only
     branch in that method that takes a broker action was unreachable.

Both now read `MarketPosition`. What each mutant defends:

  * MUTANT 1 restores the sign comparison on the copy path. The shipped defect. Killed
    only by the short-exit test; every long-side test stays green under it, which is why
    it survived this long.

  * MUTANT 2 swaps the two arms, so a long exit covers and a short exit sells. Checks
    that both sides are pinned rather than one.

  * MUTANT 3 DELETES the exit-alignment block entirely. `followerAction` already defaults
    to the leader's action, so this is invisible unless a test has the follower on the
    OPPOSITE side to the leader -- the case the block exists for. That test was written
    because this mutant survived the first draft of this battery.

  * MUTANT 4 makes the alignment fire on every copy, not just exits, so an ENTRY gets
    turned into whatever closes the current position. Scaling into a winner would reverse
    it.

  * MUTANT 5 restores the sign comparison in the reconciler, returning it to a branch that
    cannot fire. ⚠️ Expected to SURVIVE: `ReconcileFollowerPosition` is inside
    `#if !TESTING` and is called by nothing (`check_no_dead_safety_machinery.py` records
    it as KNOWN_DEAD), so no test in this suite can reach it. Recorded here rather than
    left to be rediscovered -- when P2-27 makes that method testable, this mutant is the
    test to write first.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
COPIER = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    ("the copy path goes back to reading the SIDE off the SIGN of the quantity. The shipped\n"
     "     defect: a leader covering a short sends the follower a Sell, which doubles the short",
     '                    if (currentFollowerSide == MarketPosition.Short) followerAction = OrderAction.BuyToCover;\n'
     '                    else if (currentFollowerSide == MarketPosition.Long) followerAction = OrderAction.Sell;',
     '                    if (currentFollowerPos < 0) followerAction = OrderAction.BuyToCover;\n'
     '                    else if (currentFollowerPos > 0) followerAction = OrderAction.Sell;'),

    ("the two arms are swapped, so a long exit covers and a short exit sells. Checks that BOTH\n"
     "     sides are pinned, not just the one the defect broke",
     '                    if (currentFollowerSide == MarketPosition.Short) followerAction = OrderAction.BuyToCover;\n'
     '                    else if (currentFollowerSide == MarketPosition.Long) followerAction = OrderAction.Sell;',
     '                    if (currentFollowerSide == MarketPosition.Short) followerAction = OrderAction.Sell;\n'
     '                    else if (currentFollowerSide == MarketPosition.Long) followerAction = OrderAction.BuyToCover;'),

    ("the exit-alignment block is DELETED. followerAction already defaults to the leader's\n"
     "     action, so this is invisible unless a test puts the follower on the OPPOSITE side to\n"
     "     the leader -- which is the only reason the block exists",
     '                else if (isExit)\n                {',
     '                else if (false)\n                {'),

    ("the alignment fires on EVERY copy, not just exits, so an ENTRY becomes whatever closes\n"
     "     the current position -- scaling into a winner would reverse it",
     '                else if (isExit)\n                {',
     '                else if (true)\n                {'),

    ("EXPECTED SURVIVOR: the RECONCILER goes back to comparing signs, returning its only\n"
     "     broker-acting branch to one that cannot fire. ReconcileFollowerPosition is inside\n"
     "     `#if !TESTING` and is called by nothing, so no test here can reach it. When P2-27\n"
     "     makes it testable, this is the first test to write",
     '            bool directionMismatch =\n'
     '                (leaderSide == MarketPosition.Long && followerSide == MarketPosition.Short)\n'
     '                || (leaderSide == MarketPosition.Short && followerSide == MarketPosition.Long);',
     '            bool directionMismatch = (leaderQty > 0 && followerQty < 0) || (leaderQty < 0 && followerQty > 0);'),
]


def run():
    build = subprocess.run(
        ['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    if build.returncode != 0:
        return 'BUILD FAILED'
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINAL = open(COPIER, encoding='utf-8').read()

print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print('\nREFUSING TO RUN: baseline is RED (%s failing). Every mutant would score KILLED '
          'on pre-existing failures and this battery would prove nothing.' % m.group(2))
    sys.exit(2)

survivors = []
for name, old, new in MUTANTS:
    if ORIGINAL.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, ORIGINAL.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(COPIER, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(COPIER, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(COPIER, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())
_battery.finish(survivors, MUTANTS)
