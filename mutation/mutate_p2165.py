"""Mutation battery for P2-165: two enforcement rules in `ExecuteOrderUpdate` that had no tests.

`ORDER_FLOOD_LOCKOUT` and `PER_INSTRUMENT_CAP_CANCEL` lived in an `internal` method the suite
could already drive -- `P1-160` had built the harness for a fourth rule in the same method -- and
neither had a single assertion against it. This was written as CHARACTERISATION first: assert what
the code does, then decide what is wrong.

⚠️ THE FILED ENTRY'S OWN TABLE WAS STALE. It named three rules; `BLACKLIST_CANCEL` had picked up
four tests from `P1-168` in the interval, including the very exit-is-never-refused guard the entry
hypothesised was missing. Counted before writing. [[closures-do-not-propagate-backwards]]

⚠️ AND THE HYPOTHESIS WAS RIGHT ABOUT THE WRONG RULE. The entry warned that a cancel path with no
`IsPositionReducingOrder` guard would strip a live position of its exit -- and pointed at the
blacklist, which had been fixed. The PER-INSTRUMENT CAP, which the entry did not suspect, still had
none, and it is the one where the trap is REACHABLE rather than hypothetical: `P1-160` measured the
platform turning two 1-lot MNQ entries into a position of 2, three times in six attempts, under the
operator's configured MNQ cap of 1. The flatten of that position is a 2-lot order against a cap of
1, so the guard cancelled the operator's exit and left them holding the oversized position the rule
exists to prevent. Fourteen of the sixteen characterisation tests passed on first run; the two that
failed are this.

THE GROUPS BELOW:

  1. THE CAP'S EXIT EXEMPTION, AND ITS CLAMP. Both halves are load-bearing in opposite directions:
     without the exemption the operator is trapped, and without the CLAMP the cap becomes opt-out
     by holding one lot, because `IsPositionReducingOrder` asks about direction only.
  2. THE RATE GOVERNOR'S COUNTING SEMANTICS. `P1-52` (group by OCO) and `P2-46` (count distinct
     keys, not state transitions) are both corrections recorded only in comments here -- the rule
     they describe was proved by nothing until now, so either could have been undone by an edit
     that read as a simplification.
  3. `P1-44`'s PROTECTIVE-ORDER GUARD. The asymmetric direction: a rate limit that cancels the stop
     covering a live position is worse than no rate limit at all.

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the cap's exit exemption and its clamp --------------------------------------
    (GUARD, 'group 1: the exemption is removed -- P2-165 exactly as measured. The cap refuses the '
            '2-lot order that flattens a 2-lot position, and the operator is held in the oversized '
            'position the rule exists to prevent, with no way out but one lot at a time',
     '                        if (e.Order.Quantity > perInstCap.MaxContracts && !capExitWithinPosition)',
     '                        if (e.Order.Quantity > perInstCap.MaxContracts)'),

    (GUARD, 'group 1: the CLAMP is dropped and the exemption becomes direction-only. A Sell 5 '
            'against a Long 1 satisfies IsPositionReducingOrder, so this closes 1 and opens an '
            'oversized 4 the other way -- the cap becomes opt-out by holding a single lot. This is '
            'the mutant that makes the fix WORSE than the defect, and it reads as a simplification',
     '                            && e.Order.Quantity <= capOpenQty;',
     '                            ;'),

    (GUARD, 'group 1: the exemption stops asking whether the order reduces at all, so any order '
            'under the open quantity is waved through -- an ENTRY that scales in is exempted by '
            'the guard written to let an exit out',
     '                            && IsPositionReducingOrder(e.Order, instState)\n'
     '                            && e.Order.Quantity <= capOpenQty;',
     '                            && e.Order.Quantity <= capOpenQty;'),

    (GUARD, 'group 1: the cap boundary moves to >=, so the operator\'s configured maximum is a size '
            'they can never trade. A cap is the largest PERMITTED quantity, not the first refused '
            'one',
     '                        if (e.Order.Quantity > perInstCap.MaxContracts && !capExitWithinPosition)',
     '                        if (e.Order.Quantity >= perInstCap.MaxContracts && !capExitWithinPosition)'),

    (GUARD, 'group 1: the cap is looked up by the FULL instrument name instead of the root, so it '
            'matches nothing the moment a contract month is attached -- which is every real order. '
            'A cap that expires at every roll, silently. Same shape as P1-159\'s sweep half',
     '_config.InstrumentLimits.TryGetValue(instRoot, out var perInstCap)',
     '_config.InstrumentLimits.TryGetValue(rawInst, out var perInstCap)'),

    # ---- group 2: the rate governor's counting semantics --------------------------------------
    (GUARD, 'group 2: P2-46 UNDONE -- the flood key carries the order STATE, so one order counted '
            'once per transition. This is the measured defect: a nominal limit of 5 fired at about '
            'three real orders per second, inside ordinary bracket submission, and the live log\'s '
            '"29-32 orders/sec" were transition counts rather than orders',
     '                                : (e.Order.Id != null ? e.Order.Id.ToString() : Guid.NewGuid().ToString());',
     '                                : (e.Order.Id != null ? e.Order.Id.ToString() + e.Order.OrderState : Guid.NewGuid().ToString());'),

    (GUARD, 'group 2: P1-52 UNDONE -- the OCO group is ignored and each leg counts separately, so '
            'an entry, its stop and its target put every ordinary bracketed trade three quarters of '
            'the way to a flood before the operator has done anything twice',
     '                            string floodKey = !string.IsNullOrEmpty(e.Order.Oco)\n'
     '                                ? e.Order.Oco\n'
     '                                : (e.Order.Id != null',
     '                            string floodKey = !string.IsNullOrEmpty(null)\n'
     '                                ? e.Order.Oco\n'
     '                                : (e.Order.Id != null'),

    (GUARD, 'group 2: every bracketed order collapses to ONE key regardless of which bracket it '
            'belongs to, so a runaway strategy that brackets each entry is invisible to the rule '
            'written to catch it. The mirror of the mutant above, and the reason grouping needs a '
            'negative control [[a-detector-needs-a-negative-test]]',
     '                                ? e.Order.Oco\n'
     '                                : (e.Order.Id != null',
     '                                ? "OCO"\n'
     '                                : (e.Order.Id != null'),

    (GUARD, 'group 2: the stale keys are never evicted, so the one-second window is a LIFETIME '
            'counter. Every account locks out eventually on a slow drip of ordinary trading, and '
            'the dictionary is a leak on a process that runs for weeks',
     '                            foreach (var staleId in staleOrderIds) stateModel.RecentOrderIds.Remove(staleId);',
     '                            foreach (var staleId in staleOrderIds) { }'),

    (GUARD, 'group 2: the flood boundary moves to >=, so the configured maximum is itself a flood. '
            'This is the boundary P2-46 already moved once and nothing held in place afterwards',
     '                            if (stateModel.RecentOrderIds.Count > maxPerSecond)',
     '                            if (stateModel.RecentOrderIds.Count >= maxPerSecond)'),

    (GUARD, 'group 2: a zero setting disables the rule instead of falling back to 5. Reads as a '
            'kindness, and it silently removes the rate governor from every config that has not '
            'set the field -- the direction in which a missing setting must never fail',
     '                                ? _config.Overtrading.MaxOrdersPerSecond : 5;',
     '                                ? _config.Overtrading.MaxOrdersPerSecond : int.MaxValue;'),

    (GUARD, 'group 2: the lockout does not name the rule that set it. P0-166 clears the counter of '
            'whichever rule locked, so an unattributed flood lockout forgives the wrong one on '
            'lapse -- and the loss streak is the counter next to it',
     '                                MarkRuleLockout(stateModel, "ORDER_FLOOD_LOCKOUT");',
     '                                MarkRuleLockout(stateModel, "MAX_TRADES_BREACH");'),

    # ---- group 3: P1-44's protective-order guard ----------------------------------------------
    (GUARD, 'group 3: P1-44 UNDONE -- the burst cancels the order that tripped it even when that '
            'order is the stop covering a live position. The account is locked out AND the position '
            'is left naked, which is the asymmetric direction: the rate limit is the least '
            'important thing on the screen at that moment',
     '                                if (!IsPositionReducingOrder(e.Order, stateModel))\n'
     '                                {\n'
     '                                    // P1-43: queued, not sent -- this block runs under _stateLock.',
     '                                if (true)\n'
     '                                {\n'
     '                                    // P1-43: queued, not sent -- this block runs under _stateLock.'),

    (GUARD, 'group 3: the guard is inverted, so ONLY protective orders are cancelled and the '
            'runaway entries sail through. The rate governor becomes a lockout with no teeth that '
            'also strips protection -- both failure directions at once',
     '                                if (!IsPositionReducingOrder(e.Order, stateModel))\n'
     '                                {\n'
     '                                    // P1-43: queued, not sent -- this block runs under _stateLock.',
     '                                if (IsPositionReducingOrder(e.Order, stateModel))\n'
     '                                {\n'
     '                                    // P1-43: queued, not sent -- this block runs under _stateLock.'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # Encoding PINNED: a cp1252 default raises part-way through on a non-ASCII byte, between
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
try:
    for target, name, old, new in MUTANTS:
        original = ORIGINALS[target]
        if original.count(old) != 1:
            print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
            survivors.append(name + ' (ANCHOR)')
            continue
        open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
        try:
            res = run()
            mm = re.search(r'Failed = (\d+)', res)
            undetected_crash = 'NO ASSERTION FAILED' in res
            killed = (not undetected_crash) and (
                ('BUILD FAILED' in res) or ('NO RESULT LINE' in res)
                or (mm is not None and int(mm.group(1)) > 0))
            print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
            if not killed:
                survivors.append(name)
        finally:
            restore()
finally:
    # The pin above closes the failure that has actually happened twice; this closes the class.
    restore()

print(chr(10) + 'restored originals;', run())

# Plain exit rule, not _battery.finish: this battery declares no EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions.
if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
