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
  7. IDENTITY IS THE ORDER, NOT THE STRING THE BROKER PUT ON IT, and the set is bounded by the
     SESSION rather than by the process lifetime. The ticket said to key on Order.Id; the funded
     account's provider REPLACES Order.Id on accept while Sim101 never does, so the id-keyed
     version passes every test here and leaves P1-167 open on the live account.

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # ---- group 1: armed, by the reconnect, on the guard's own clock -------------------------
    (GUARD, 'group 1: the suppression is never armed. The fields exist, the rule consults them, '
            'the reconnect handler runs -- and the value stays DateTime.MinValue, so the measured '
            'defect is restored in full with every field looking present',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs);',
     '                        _ = replayState.UtcNow();'),

    (GUARD, 'group 1: armed off DateTime.UtcNow instead of the account\'s injectable clock, giving '
            'AccountState a SECOND clock -- the fake one for the rule and the real one for the '
            'suppression. [[a-second-reader-of-the-same-state]]',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs);',
     '                        replayState.ReplaySuppressionUntilUtc = DateTime.UtcNow\n'
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs);'),

    (GUARD, 'group 1: armed ONLY on Connected -- THE FIRST FIX, RESTORED. This mutant used to be '
            'the inverse of itself: the battery asserted that arming on any status was the '
            'DEFECT, and killed it against a test that asserted the same wrong thing. Two live '
            'reconnects then showed the replay arrives BEFORE Connected -- burst 44.275-44.471 '
            'against Connected at 44.711 on the natural event, and 44.619-44.686 against 44.773 '
            'on the induced one -- so arming on Connected suppresses nothing. It produced 17 '
            'false refusals on a live account WITH the first fix deployed. '
            '[[a-wrong-red-test-enforces-itself]]',
     '                    if (_config != null && _config.Overtrading != null\n'
     '                        && _config.Overtrading.ReconnectReplayGraceMs > 0',
     '                    if (e.Status.ToString() == \"Connected\"\n'
     '                        && _config != null && _config.Overtrading != null\n'
     '                        && _config.Overtrading.ReconnectReplayGraceMs > 0'),

    # ---- group 2: bounded by the CONFIGURED window ------------------------------------------
    (GUARD, 'group 2: the unit is minutes, not milliseconds. A 1000ms window becomes a 16-hour '
            'suppression -- the rule is off for the rest of the session and nothing says so',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs);',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMinutes(_config.Overtrading.ReconnectReplayGraceMs);'),

    (GUARD, 'group 2: the suppression runs ten windows, not one. Still bounded, still lapses, and '
            'still leaves nine windows in which a genuine duplicate is waved through',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs);',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs * 10);'),

    (GUARD, 'group 2: the length is hard-coded to 1000ms, which is the DEFAULT window -- so every '
            'test that does not change the window passes, and an operator who narrows the window '
            'to 250ms silently gets four times the suppression they configured',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs);',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMilliseconds(_config.Overtrading.DuplicateEntryWindowMs);'),

    (GUARD, 'group 2: the suppression never lapses. This is the mutant the ticket names as worse '
            'than the defect: the duplicate rule protects nothing from the first reconnect onward, '
            'and every other assertion in this battery still passes',
     '                        replayState.ReplaySuppressionUntilUtc = replayState.UtcNow()\n'
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs);',
     '                        replayState.ReplaySuppressionUntilUtc = DateTime.MaxValue;'),

    (GUARD, 'group 2: the grace is 2000ms -- above the INDUCED reconnect gap of 1167ms and '
            '27ms BELOW the natural one of 2027ms. It passes the induced regression test and '
            'fails the natural one, which is the entire reason the default is not set just '
            'above the worst sample available. With one sample it would have been',
     '                            .AddMilliseconds(_config.Overtrading.ReconnectReplayGraceMs);',
     '                            .AddMilliseconds(2000);'),

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
     '                                    stateModel.DuplicateEntryEvaluatedOrders.Add(e.Order);',
     '                                    _ = stateModel.DuplicateEntryEvaluatedOrders.Count;'),

    (GUARD, 'group 5: the set is written but never read -- the mirror image, and the shape of '
            '[[dead-safety-machinery-gate]]: a collection that fills up all session and decides '
            'nothing',
     '                            bool alreadyEvaluated = stateModel.DuplicateEntryEvaluatedOrders.Contains(e.Order);',
     '                            bool alreadyEvaluated = false;'),

    (GUARD, 'group 5: the set is keyed on the order id PLUS the observation time, so no two events '
            'for one order ever match. Written, read, and unable to answer yes',
     '                                    stateModel.DuplicateEntryEvaluatedOrders.Add(e.Order);',
     '                                    stateModel.DuplicateEntryEvaluatedOrders.Add(\n'
     '                                        new Order { Id = e.Order.Id, OrderState = e.Order.OrderState });'),

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

    # ---- group 7: identity is the ORDER, not the string the broker put on it ----------------
    (MODELS, 'group 7: the evaluated-order set is keyed on Order.Id instead of object reference. '
             'This is the ticket\'s own instruction and it is wrong: the funded account\'s provider '
             'REPLACES Order.Id on accept, so the set is written under the submission id and read '
             'under the accepted one and never matches -- P1-167 stays open on the live account '
             'while Sim101, which re-ids nothing, passes every test. '
             '[[the-simulator-re-ids-nothing]]',
     '        public bool Equals(Order a, Order b)\n'
     '        {\n'
     '            return ReferenceEquals(a, b);\n'
     '        }\n'
     '\n'
     '        public int GetHashCode(Order o)\n'
     '        {\n'
     '            return System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(o);\n'
     '        }',
     '        public bool Equals(Order a, Order b)\n'
     '        {\n'
     '            return a != null && b != null && a.Id == b.Id;\n'
     '        }\n'
     '\n'
     '        public int GetHashCode(Order o)\n'
     '        {\n'
     '            return o != null && o.Id != null ? o.Id.GetHashCode() : 0;\n'
     '        }'),

    (GUARD, 'group 7: the session reset stops clearing the evaluated-order set. Runtime-only means '
            'nothing on DISK grows; this guard runs for weeks between restarts, so the set '
            'accumulates every order object of every session for the life of the process and pins '
            'each one against collection',
     # Re-anchored 2026-08-20: P1-167 inserted RuleRefusedOrders.Clear() between these two lines,
     # so the two-line span stopped matching. Each half now anchors on its OWN line, which is what
     # it should have been -- a multi-line anchor is a claim about the lines BETWEEN the two it
     # cares about. [[mutation-anchors-go-stale]]
     '            stateModel.DuplicateEntryEvaluatedOrders.Clear();',
     '            _ = stateModel.DuplicateEntryEvaluatedOrders.Count;'),

    (GUARD, 'group 7: the session reset stops clearing the suppression deadline, so a stamp set at '
            '23:59 is carried into the next session -- a suppression nothing can account for, on a '
            'rule whose entire safety argument is that its suppression is bounded',
     '            stateModel.ReplaySuppressionUntilUtc = DateTime.MinValue;',
     '            _ = stateModel.ReplaySuppressionUntilUtc;'),

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
