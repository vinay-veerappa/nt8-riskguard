"""Mutation battery for P1-99: the copier sized each leader EXECUTION independently.

⚠️ THIS ONE LEFT A FOLLOWER FLAT AGAINST A LEADER LONG 100, WITH NO ERROR ANYWHERE.

The copy path runs per Execution, and `CalculateFollowerQuantity` was handed `exec.Quantity` --
the SLICE. A leader order is not its fills: 100 MNQ under a MNQ->NQ conversion is 10 NQ however
the book delivers it. Sized slice by slice it became a function of the FILL SHAPE:

    5 + 95     -> 0 + 10 = 10   correct BY LUCK (this is the shape the live box produced)
    10 x 10    -> 10 x 1  = 10   correct
    11 + 89    -> 1 + 9   = 10   correct
    20 x 5     -> 20 x 0  =  0   EVERY SLICE DROPPED

The last one is the defect: twenty routine `COPY_SKIPPED_SUB_MINIMUM` lines, leader long 100,
follower FLAT. Found by driving the deployed box while validating P2-98, not by review and not
by the suite -- because every copy-path test in this repo sends ONE execution for the full
quantity, and `LeaderExec` builds a fresh Order for each. That shortcut is the shared blind spot
of P2-98 (follower side) and this (leader side).

The fix moves the GRAIN of the decision from the execution to the ORDER: each slice recomputes
the target from the cumulative leader quantity and copies the DELTA against what has already
gone. Rounding cannot accumulate, because every slice re-derives the whole target rather than
adding to it.

What each mutant defends:

  * MUTANT 1 restores the shipped defect -- size from `exec.Quantity`. Killed only by a test that
    sends more than one execution for one order; the whole pre-existing suite stays green.

  * MUTANT 2 is THE WRONG FIX, and it is the one to know. Flooring each slice's delta at 1 makes
    the 5+95 case work and turns 20 x 5 into a TWENTY-contract copy against a 10-contract order:
    double the leader, same direction. It looks like a fix because the drops stop.

  * MUTANT 3 clamps the CUMULATIVE against remaining capacity instead of clamping the delta.
    Subtracts the already-copied slices twice, so with MaxPositionSize 10 a 50+50 fill copies 5
    and then nothing -- follower silently at half size, and every event reads as success.

  * MUTANT 4 routes EXITS through the accumulator too. Exits already mirror the follower's actual
    position (P0-6), so this defers the close of a position the leader has left -- P0-5's failure
    arriving through P1-99's own fix. The asymmetry is the point.

  * MUTANT 5 shares ONE running total across relationships instead of keying by rel.Id, so the
    first follower's copy satisfies the second follower's target.

  * MUTANT 6 assigns the cumulative instead of accumulating it, which is mutant 1 by another
    route -- and the route a careless edit would actually take.

  * MUTANT 7 drops the per-order progress on EVERY execution rather than when the order is done,
    restarting the count each slice. Also mutant 1's behaviour, reached from the cleanup.

  * MUTANT 8 credits the TARGET rather than what was actually submitted, so a copy reduced by the
    capacity clamp has its shortfall forgiven and never re-offered.

  * MUTANT 9 removes the terminal-state half of the completion test, keeping only the quantity
    half. P2-98's lesson on the other side of the copier: an order cancelled after a partial fill
    never reaches its quantity, so its progress entry survives to the FIFO bound.

A crash counts as a kill (handover section 5.14).
"""
import os
import re
import subprocess
import sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
COPIER = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    ("the SHIPPED DEFECT: entries are sized from this EXECUTION's quantity again, not the leader\n"
     "     order's cumulative fill. A 100-lot filling 20 x 5 copies NOTHING",
     '                        rel, cumulativeLeaderQty, exec.Instrument.FullName, 0, false,',
     '                        rel, exec.Quantity, exec.Instrument.FullName, 0, false,'),

    ("THE WRONG FIX: each slice's delta is floored at 1, so twenty sub-minimum slices become\n"
     "     TWENTY contracts on a ten-contract order -- double the leader, same direction, and the\n"
     "     COPY_SKIPPED lines stop, which is what makes it look right",
     '                    int delta = Math.Max(0, cumulativeTarget - alreadyCopiedThisOrder);',
     '                    int delta = Math.Max(1, cumulativeTarget - alreadyCopiedThisOrder);'),

    # ⚠️ The FIRST draft of this mutant only changed the position argument from 0 to
    # currentFollowerPos, and it SURVIVED -- correctly, because the cumulative is read from the
    # PRE-CLAMP out-param, which that argument cannot reach. It was proving nothing. The real
    # defect is taking the RETURN value instead, which is what actually clamps the cumulative.
    ("the CUMULATIVE is clamped against remaining capacity -- the RETURN value instead of the\n"
     "     pre-clamp out-param -- so the delta subtracts the already-copied slices a SECOND time and\n"
     "     the follower ends at half size with every event reading as success",
     '                    CalculateFollowerQuantity(\n'
     '                        rel, cumulativeLeaderQty, exec.Instrument.FullName, 0, false,\n'
     '                        out bool cumulativeRefused, out cumulativeTarget);',
     '                    bool cumulativeRefused;\n'
     '                    cumulativeTarget = CalculateFollowerQuantity(\n'
     '                        rel, cumulativeLeaderQty, exec.Instrument.FullName, currentFollowerPos, false,\n'
     '                        out cumulativeRefused);'),

    ("EXITS are routed through the entry accumulator too. P0-6's clamp already mirrors the\n"
     "     follower's real position, so this defers closing a position the leader has already left",
     '                if (isExit)\n                {\n                    // UNCHANGED, and deliberately so.',
     '                if (false)\n                {\n                    // UNCHANGED, and deliberately so.'),

    ("ONE running total is shared across relationships instead of keying by rel.Id, so the first\n"
     "     follower's copy satisfies the second follower's target",
     '                            orderProgress.CopiedByRelationshipId.TryGetValue(rel.Id, out alreadyCopiedThisOrder);',
     '                            orderProgress.CopiedByRelationshipId.TryGetValue("shared", out alreadyCopiedThisOrder);'),

    ("the cumulative is ASSIGNED rather than accumulated -- mutant 1 by the route a careless edit\n"
     "     would actually take",
     '                    orderProgress.CumulativeLeaderQty += exec.Quantity;',
     '                    orderProgress.CumulativeLeaderQty = exec.Quantity;'),

    ("the per-order progress is dropped on EVERY execution instead of when the order is done, so\n"
     "     the count restarts each slice",
     '                bool leaderOrderDone =\n'
     '                    RiskGuardAddOn.IsTerminal(exec.Order.OrderState)\n'
     '                    || (exec.Order.Quantity > 0 && cumulativeLeaderQty >= exec.Order.Quantity);',
     '                bool leaderOrderDone = true;'),

    ("the TARGET is credited rather than what was actually submitted, so a copy reduced by the\n"
     "     capacity clamp has its shortfall forgiven instead of re-offered on a later slice",
     '                                orderProgress.CopiedByRelationshipId[rel.Id] = prior + targetQty;',
     '                                orderProgress.CopiedByRelationshipId[rel.Id] = cumulativeTarget;'),

    ("the terminal-STATE half of the completion test is removed, keeping only the quantity half.\n"
     "     An order cancelled after a partial fill never reaches its quantity, so its entry lives\n"
     "     to the FIFO bound -- P2-98's lesson on the other side of the copier",
     '                    RiskGuardAddOn.IsTerminal(exec.Order.OrderState)\n'
     '                    || (exec.Order.Quantity > 0 && cumulativeLeaderQty >= exec.Order.Quantity);',
     '                    (exec.Order.Quantity > 0 && cumulativeLeaderQty >= exec.Order.Quantity);'),
]


def run():
    build = subprocess.run(
        ['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if build.returncode != 0:
        return 'BUILD FAILED'
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if not m and '[FAIL]' not in ((res.stdout or '') + (res.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
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
    killed = _battery.score(res, run)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(COPIER, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(COPIER, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')
sys.exit(1 if survivors else 0)
