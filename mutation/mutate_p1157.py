"""Mutation battery for P1-157: the auto-stop hands over to the operator's own stop.

THE PRECONDITION FOR EVER TURNING `OnMissing: AutoStop` ON. The operator forgets a stop, the guard
places one, and then the operator attaches their own bracket. Without a handover both stay working
and ONE position carries TWO stops. On a fast move both can fill before the flat-teardown cancels
the survivor -- which does not leave you flat, it leaves you REVERSED. That is precisely the
failure the guard exists to prevent, arriving by the guard's own hand, and it is the same shape as
`P1-56` (a stop sized for two against a position of one) and `P1-140`.

⚠️ THE CONDITION IS FULL COVERAGE BY SOMEONE ELSE, NOT THE APPEARANCE OF ANOTHER STOP. The two
directions are NOT symmetric and only one of them is safe to get wrong:

  * withdraw too EAGERLY -> the remainder of a partly-covered position loses its only cover, and
    the guard has cancelled the protection it just placed;
  * withdraw too LATE  -> two stops for a while, which is the flip hazard above.

Neither is acceptable, so coverage is summed EXCLUDING the auto-stop and must reach the whole
position. [[a-filter-that-matches-too-much]] is the same lesson on a path that decides whether a
position keeps its protection.

THE GROUPS BELOW:

  1. THE HANDOVER HAPPENS. Mutants restoring the two-stops state.
  2. ⚠️ IT REQUIRES FULL COVERAGE. Mutants that withdraw on partial coverage -- the eager
     direction, which strips a live position of its only stop.
  3. THE AUTO-STOP IS THE ONE THAT GOES. Cancelling the OPERATOR's stop instead would be the same
     count of working orders and the exact opposite outcome.
  4. THE CANCEL IS QUEUED, NOT SENT UNDER THE LOCK. `_stateLock` is held here; the teardown
     comment a few lines up says a nested lock only hides the violation.
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the handover happens ------------------------------------------------------
    (GUARD, 'group 1: the handover never runs, so a position that gets an operator stop keeps the '
            'guard stop too -- two stops on one position, which is the state this entry exists to '
            'end and the reason AutoStop could not be turned on',
     '                            if (fsm.AutoStopOrder != null && !ReferenceEquals(order, fsm.AutoStopOrder))',
     '                            if (false)'),

    (GUARD, 'group 1: the auto-stop reference is dropped but the ORDER is never cancelled -- the '
            'guard forgets its own stop while the broker keeps working it. Untracked and live is '
            'worse than tracked and live, because nothing will clean it up later',
     '                                    if (OccupiesSlot(toCancel.OrderState))\n'
     '                                        _pendingCancels.Add(new PendingCancelEntry(\n'
     '                                            account, toCancel, PendingCancelIntent.Cleanup));',
     '                                    // cancel not queued'),

    # ---- group 2: it requires FULL coverage -------------------------------------------------
    (GUARD, 'group 2: the auto-stop is withdrawn on the mere APPEARANCE of another stop, so a '
            'PARTIAL operator stop strips the remainder of its only cover -- the guard cancelling '
            'the protection it just placed. The eager direction, and the dangerous one',
     '                                if (fsm.PositionQuantity > 0 && coveredByOthers >= fsm.PositionQuantity)',
     '                                if (fsm.PositionQuantity > 0 && coveredByOthers > 0)'),

    (GUARD, 'group 2: coverage is summed INCLUDING the auto-stop, so the guard\'s own order counts '
            'towards the total that justifies removing it -- it withdraws itself the moment it is '
            'placed, on a position with no operator stop at all',
     '                                    if (!ReferenceEquals(o, fsm.AutoStopOrder)) coveredByOthers += o.Quantity;',
     '                                    coveredByOthers += o.Quantity;'),

    (GUARD, 'group 2: the off-by-one -- coverage must EXCEED the position rather than meet it, so '
            'an exactly-covering operator stop never triggers the handover and the ordinary case '
            '(one stop for the whole position) is the one that keeps two',
     '                                if (fsm.PositionQuantity > 0 && coveredByOthers >= fsm.PositionQuantity)',
     '                                if (fsm.PositionQuantity > 0 && coveredByOthers > fsm.PositionQuantity)'),

    # ---- group 3: the auto-stop is the one that goes ----------------------------------------
    (GUARD, 'group 3: the OPERATOR\'s stop is withdrawn instead of the guard\'s. The same number of '
            'working orders and the exact opposite outcome: the operator\'s chosen risk is removed '
            'and the guard\'s catastrophe stop is what remains',
     '                                    var toCancel = fsm.AutoStopOrder;',
     '                                    var toCancel = order;'),

    # ---- group 4: queued, not sent under the lock -------------------------------------------
    (GUARD, 'EXPECTED SURVIVOR: the cancel is sent INLINE while _stateLock is held, rather than '
            'queued for DrainPendingCancels. UNREACHABLE BY UNIT TEST: lock SCOPE is not '
            'observable from a test that calls the method -- the stub Account.Cancel succeeds '
            'either way and the re-entrancy hazard needs a concurrent caller to manifest. The '
            'real detector is a SOURCE gate, and the agent-loop profile has one '
            '(lock_name="_stateLock", agent/nt8_riskguard.py:27) -- but it runs only on '
            'loop-authored changes, and this fix was hand-written, so nothing checked it. '
            'Filed as P2-158 to port that check into CI. Kept as a mutant because the DEFECT '
            'is real: a broker call under the lock is the re-entrancy corruption P2-107 and '
            'P1-35 both came from.',
     '                                        _pendingCancels.Add(new PendingCancelEntry(\n'
     '                                            account, toCancel, PendingCancelIntent.Cleanup));',
     '                                        account.Cancel(new[] { toCancel });'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # ⚠️ Encoding PINNED: a cp1252 default raises part-way through on a non-ASCII byte, between
    # applying a mutant and restoring it. [[a-battery-must-reach-its-restore-line]].
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


def run():
    try:
        p = subprocess.run(
            ['dotnet', 'run', '--project', os.path.join(REPO, 'tests', 'RiskGuardTests.csproj'),
             '--nologo', '-v', 'q'],
            cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=900)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    out = (p.stdout or '') + (p.stderr or '')
    if 'error CS' in out:
        return 'BUILD FAILED'
    m = re.search(r'Passed = (\d+), Failed = (\d+)', out)
    result = m.group(0) if m else 'NO RESULT LINE'
    # P2-148 / P1-153: a crash is not a detection.
    if not m and '[FAIL]' not in out:
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return result


baseline = run()
print('=== baseline ===\n  %s' % baseline)
if 'Failed = 0' not in baseline:
    print('baseline is RED; a battery against a red baseline scores nothing')
    sys.exit(2)

survivors = []
for target, name, old, new in MUTANTS:
    original = ORIGINALS[target]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    try:
        res = run()
        killed = _battery.score(res, run)
        print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
        if not killed:
            survivors.append(name)
    finally:
        restore()

restore()
print(chr(10) + 'restored originals;', run())

# Routed through _battery.finish because group 4 declares itself an EXPECTED SURVIVOR, and the
# helper enforces the pairing in BOTH directions -- a declaration that starts being KILLED is
# reported STALE rather than passing quietly.
_battery.finish(survivors, MUTANTS)
