"""Mutation battery for P2-98: a partial fill measured only its FIRST slice.

A partial fill delivers several `Execution`s for the SAME `Order` object. The pending-copy
entry was consumed on the first of them, so every later slice missed the lookup. Two
consequences, measured live 2026-08-13 on four copies that all filled 1+9:

  * the metric described the SMALLEST slice -- `slippage=2 ticks` came from one contract
    while the nine carrying the risk went unmeasured; and

  * each later slice raised `FILL_NOT_MEASURED`, whose text asserted "OrderId is
    display-only and must never be used as the map key". That trap is real, but it was not
    the cause here, and a routine event that sends its reader after a defect which is not
    there is how the event stops being read at all (P3-30's audit, same failure).

The fix moves the grain of a measurement from the SLICE to the COPY: accumulate across
slices, report once when the order is done, weight the average by quantity, and take the
latency reading once -- on the first slice, because it measures how long the copy took to
REACH the market, not how long the market took to fill it.

What each mutant defends:

  * MUTANT 1 restores the shipped defect: the entry is consumed on every fill. The
    1-lot slice speaks for the copy again.
  * MUTANT 2 makes the LAST slice speak for the copy instead of the first -- the same
    defect wearing the other hat, which a test asserting only "not 4.0 ticks" would miss.
  * MUTANT 3 stops ACCUMULATING quantity (last slice wins), so a 1+9 fill never reaches
    its order quantity and the measurement is lost entirely.
  * MUTANT 4 divides by the slice count rather than the filled quantity: an UNWEIGHTED
    mean, in which a 1-lot slice counts for as much as the 9 lots beside it.
  * MUTANT 5 re-evaluates latency on every slice, so the reading becomes time-to-LAST-fill
    -- liquidity, reported as though it were the copier's responsiveness.
  * MUTANT 6 is the subtle one, and it is the rule P?-66 was closed on: a REJECTED reading
    is re-evaluated on the next slice and a plausible number is manufactured out of the
    same disagreeing clocks that produced the rejected one.
  * MUTANT 7 records a rejected latency anyway.
  * MUTANT 8 drops the terminal-order-state completion signal, so a copy cancelled after a
    partial fill is never measured and its entry sits until the FIFO reaps it.
  * MUTANT 9 drops the quantity completion signal, leaving only a state the stub never
    sets -- nothing is ever measured.
  * MUTANT 10 turns `>=` into `>`, so a copy that fills exactly completes one contract late,
    i.e. never.
  * MUTANT 11 measures an INCOMPLETE copy: the early return goes, and 1 of 10 is announced
    as a finished measurement.
  * MUTANT 12 renames the FILL_SLICE event, checking that the partial-fill path is pinned by
    the name an operator would grep for and not merely by "something was logged".
  * MUTANT 13 restores the false diagnosis in FILL_NOT_MEASURED.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
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


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
COPIER = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    ("the pending entry is consumed on EVERY fill, as it was. The shipped defect: the first\n"
     "     slice is measured and every later one is reported as a lookup miss",
     '                    if (copyComplete)\n                    {\n                        _pendingCopies.Remove(exec.Order);',
     '                    if (true)\n                    {\n                        _pendingCopies.Remove(exec.Order);'),

    ("the LAST slice speaks for the whole copy instead of the first -- the same defect the\n"
     "     other way round, invisible to a test that only asserts 'not the first slice'",
     '                        pending.FollowerNotional += exec.Price * sliceQty;',
     '                        pending.FollowerNotional = exec.Price * (pending.FilledQuantity);'),

    ("quantity stops ACCUMULATING (last slice wins), so a 1+9 copy never reaches its order\n"
     "     quantity and is never measured at all",
     '                        pending.FilledQuantity += sliceQty;',
     '                        pending.FilledQuantity = sliceQty;'),

    ("the average is UNWEIGHTED -- divided by the number of slices rather than the contracts\n"
     "     they carried, so a 1-lot counts for as much as the 9 beside it",
     '                ? pending.FollowerNotional / pending.FilledQuantity',
     '                ? pending.FollowerNotional / pending.SliceCount'),

    ("latency is re-evaluated on every slice, making the reading time-to-LAST-fill: that is\n"
     "     liquidity, reported as though it were the copier's responsiveness",
     '                    if (!pending.LatencyEvaluated)',
     '                    if (true)'),

    ("a REJECTED latency is re-evaluated on the next slice, so a plausible figure is\n"
     "     manufactured out of the same disagreeing clocks that produced the rejected one.\n"
     "     P?-66's rule, and the reason the verdict is carried on the pending entry",
     '                    if (!pending.LatencyEvaluated)',
     '                    if (!pending.LatencyAccepted)'),

    ("a rejected latency is recorded anyway",
     '            if (pending.LatencyAccepted)\n            {\n                lock (_lock)\n                {\n                    rel.LatencyMs = pending.LatencyMs;',
     '            if (true)\n            {\n                lock (_lock)\n                {\n                    rel.LatencyMs = pending.LatencyMs;'),

    ("the terminal-order-state completion signal goes, so a copy cancelled or rejected after a\n"
     "     partial fill is never measured and its entry sits until the FIFO reaps it",
     '                    copyComplete = RiskGuardAddOn.IsTerminal(exec.Order.OrderState)\n'
     '                        || orderQty <= 0\n'
     '                        || pending.FilledQuantity >= orderQty;',
     '                    copyComplete = orderQty <= 0\n'
     '                        || pending.FilledQuantity >= orderQty;'),

    ("the QUANTITY completion signal goes, leaving only an order state the provider may not\n"
     "     have set yet -- and that the test stub never sets at all",
     '                    copyComplete = RiskGuardAddOn.IsTerminal(exec.Order.OrderState)\n'
     '                        || orderQty <= 0\n'
     '                        || pending.FilledQuantity >= orderQty;',
     '                    copyComplete = RiskGuardAddOn.IsTerminal(exec.Order.OrderState)\n'
     '                        || orderQty <= 0;'),

    ("off by one: a copy that fills exactly completes one contract late, i.e. never",
     '                        || pending.FilledQuantity >= orderQty;',
     '                        || pending.FilledQuantity > orderQty;'),

    ("an INCOMPLETE copy is measured: 1 of 10 filled is announced as a finished reading",
     '            if (!copyComplete)\n            {',
     '            if (false)\n            {'),

    ("the partial-fill event is renamed, checking that the path is pinned by the name an\n"
     "     operator would grep for rather than by 'something was logged'",
     '"FILL_SLICE",',
     '"FILL_PARTIAL",'),

    ("FILL_NOT_MEASURED goes back to asserting the OrderId-as-key bug as the cause -- a\n"
     "     diagnosis that was false for every miss actually seen live",
     '                    string.Format("No pending copy for order \'{0}\' (OrderId {1}, state {2}); this fill is not measured. "',
     '                    string.Format("Pending-copy lookup missed for order \'{0}\' (OrderId {1}, state {2}). OrderId is display-only and must never be used as the map key. "'),
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
