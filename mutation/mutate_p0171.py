"""Mutation battery for P0-171 + P1-167: a reconnect replay is not a burst of duplicates, and
one order draws one refusal.

MEASURED on the funded account TAKEPROFITPRO524207503 on 2026-08-19, with no trading taking place.
One Disconnected -> Connected cycle at 16:44 replayed 118 distinct orders inside a single second,
every one already in state Filled, and all 59 executions inside two. The duplicate-entry rule timed
them by when the GUARD FIRST SAW them, so every pair fell inside any window: 45 false refusals from
one event, out of 36 connection events that day and 54 duplicate events total. Separately, order
35996 drew THREE refusals at 881ms, 884ms and 917ms, because ExecuteOrderUpdate runs once per order
EVENT and no rule recorded that it had already refused a given order.

WHY THIS BATTERY IS THE EVIDENCE, and not the 3352-test suite. The fix is TWO mechanisms and a
boundary, and each one is a switch that can be left in the wrong position while the whole suite
stays green:

  * a suppression that never arms is the defect, unchanged;
  * a suppression that never LAPSES is worse than the defect, because the rule then protects
    nothing and says nothing -- [[a-green-that-can-never-be-red]];
  * a suppression that stops the REFUSAL but still lets a replayed order become an ANCHOR moves the
    false positive off the replay and onto the next genuine entry, by which time the operator is
    actually trading;
  * an evaluated-order set that is written but never read, or read but never written, leaves
    P1-167 exactly where it was.

THE GROUPS BELOW:

  1. THE SUPPRESSION IS ARMED, BY THE RECONNECT, ON THE GUARD'S OWN CLOCK. The measured sequence is
     FOUR events -- Disconnecting, Disconnected, Connecting, Connected, spanning five seconds -- so
     arming on the wrong one starts the window before the replay and it has lapsed by the time it
     is needed. That failure is silent and looks exactly like the fix not working.
  2. IT IS BOUNDED BY THE CONFIGURED WINDOW. Not by a constant that happens to equal the default,
     and not by a unit nobody re-read.
  3. THE BOUNDARY IS WHERE THE SPEC SAYS. At-or-before, to the millisecond.
  4. A SUPPRESSED ORDER DOES NOT ANCHOR. The half that is easy to half-do.
  5. ONE ORDER, ONE REFUSAL. The set is both written and read, and keyed on the order.
  6. NEITHER MECHANISM MAY DISABLE THE RULE. The negative controls. Every assertion in groups 1-5
     is satisfied by a rule that never fires at all.

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
    # ---- group 1: armed, by the reconnect, on the guard's own clock -------------------------
    (GUARD, 'group 1: the suppression is never armed. The fields exist, the rule consults them, '
            'the reconnect handler runs -- and the value stays DateTime.MinValue, so the measured '
            'defect is restored in full with every field looking present',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs);',
     '                            _ = replayState.UtcNow();'),

    (GUARD, 'group 1: armed off DateTime.UtcNow instead of the account\'s injectable clock, giving '
            'AccountState a SECOND clock -- the fake one for the rule and the real one for the '
            'suppression. [[a-second-reader-of-the-same-state]]',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs);',
     '                            replayState.ReplaySuppressionUntilUtc = DateTime.UtcNow\n'
     '                                .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs);'),

    (GUARD, 'group 1: armed on ANY connection status, not just Connected. The measured sequence '
            'starts four seconds before the reconnect, so a 1000ms suppression armed at '
            'Disconnected has already lapsed when the replay lands -- the guard carries a '
            'suppression, logs nothing unusual, and refuses all 45 orders anyway',
     '                    if (e.Status.ToString() == "Connected")\n                    {\n'
     '                        // P0-171. A reconnect makes NT8 REPLAY the session',
     '                    if (e.Status != null)\n                    {\n'
     '                        // P0-171. A reconnect makes NT8 REPLAY the session'),

    # ---- group 2: bounded by the CONFIGURED window ------------------------------------------
    (GUARD, 'group 2: the unit is minutes, not milliseconds. A 1000ms window becomes a 16-hour '
            'suppression -- the rule is off for the rest of the session and nothing says so',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs);',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMinutes(_config.Overtrading.DuplicateEntryWindowMs);'),

    (GUARD, 'group 2: the suppression runs ten windows, not one. Still bounded, still lapses, and '
            'still leaves nine windows in which a genuine duplicate is waved through',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs);',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs * 10);'),

    (GUARD, 'group 2: the length is hard-coded to 1000ms, which is the DEFAULT window -- so every '
            'test that does not change the window passes, and an operator who narrows the window '
            'to 250ms silently gets four times the suppression they configured',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs);',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMilliseconds(1000);'),

    (GUARD, 'group 2: the suppression never lapses. This is the mutant the ticket names as worse '
            'than the defect: the duplicate rule protects nothing from the first reconnect onward, '
            'and every other assertion in this battery still passes',
     '                            replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                                .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs);',
     '                            replayState.ReplaySuppressionUntilUtc = DateTime.MaxValue;'),

    # ---- group 3: the boundary is where the spec says ---------------------------------------
    (GUARD, 'group 3: the boundary is exclusive, so an order arriving on the exact deadline is '
            'evaluated. One millisecond of the replay is unprotected, which is the whole burst '
            'when 118 orders arrive inside one second',
     '                            bool replaySuppressed = dupNow <= stateModel.ReplaySuppressionUntilUtc;',
     '                            bool replaySuppressed = dupNow < stateModel.ReplaySuppressionUntilUtc;'),

    # ---- group 4: a suppressed order does not ANCHOR ----------------------------------------
    (GUARD, 'group 4: the FIRST replayed order is evaluated and becomes an anchor; only the rest '
            'are suppressed. No refusal is logged during the replay, so the burst looks fixed -- '
            'and the next genuine entry is refused against an order from before the reconnect',
     '                            bool replaySuppressed = dupNow <= stateModel.ReplaySuppressionUntilUtc;',
     '                            bool replaySuppressed = dupNow <= stateModel.ReplaySuppressionUntilUtc\n'
     '                                && stateModel.RecentEntryAnchors.Count > 0;'),

    # ---- group 5: one order, one refusal ----------------------------------------------------
    (GUARD, 'group 5: the evaluated-order set is read but never written. P1-167 is restored in '
            'full: one duplicate order draws one refusal per state transition, and '
            'SHADOW_PENDING_CANCEL over-reports again',
     '                                    stateModel.DuplicateEntryEvaluatedOrderIds.Add(e.Order.Id);',
     '                                    _ = stateModel.DuplicateEntryEvaluatedOrderIds.Count;'),

    (GUARD, 'group 5: the set is written but never read -- the mirror image, and the shape of '
            '[[dead-safety-machinery-gate]]: a collection that fills up all session and decides '
            'nothing',
     '                            bool alreadyEvaluated = stateModel.DuplicateEntryEvaluatedOrderIds.Contains(e.Order.Id);',
     '                            bool alreadyEvaluated = false;'),

    (GUARD, 'group 5: the set is keyed on the order id PLUS the observation time, so no two events '
            'for one order ever match. Written, read, and unable to answer yes',
     '                                    stateModel.DuplicateEntryEvaluatedOrderIds.Add(e.Order.Id);',
     '                                    stateModel.DuplicateEntryEvaluatedOrderIds.Add(e.Order.Id + dupNow.Ticks);'),

    # ---- group 6: neither mechanism may disable the rule ------------------------------------
    (GUARD, 'group 6: the whole rule is switched off at the choke point. Every assertion about '
            'something NOT being refused passes; only the negative controls can see this. '
            '[[a-backstop-at-a-choke-point-is-unkillable]]',
     '                            if (isEntry && !replaySuppressed && !alreadyEvaluated)',
     '                            if (false)'),

    (GUARD, 'group 6: the already-evaluated test is inverted, so an order is evaluated ONLY on its '
            'second event. Nothing is ever refused on first sight',
     '                            if (isEntry && !replaySuppressed && !alreadyEvaluated)',
     '                            if (isEntry && !replaySuppressed && alreadyEvaluated)'),

    (GUARD, 'group 6: the reducing-position exclusion is dropped from the entry test. An order that '
            'CLOSES a position becomes refusable, which is the one failure direction this rule may '
            'never take. [[a-lockout-must-not-trap-you]]',
     '                            bool isEntry = e.Order.OrderType == OrderType.Market\n'
     '                                && !IsPositionReducingOrder(e.Order, stateModel)\n'
     '                                && !string.Equals(e.Order.Name, CopierOrderNames.Follow, StringComparison.Ordinal);',
     '                            bool isEntry = e.Order.OrderType == OrderType.Market\n'
     '                                && !string.Equals(e.Order.Name, CopierOrderNames.Follow, StringComparison.Ordinal);'),
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
