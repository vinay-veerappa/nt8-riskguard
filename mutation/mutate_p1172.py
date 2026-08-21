"""Mutation battery for P1-172: `ConsecutiveLosses` read 17 on an account that took 16 trades.

That value cannot occur. A consecutive-loss streak cannot exceed the trades that produced it, and
it resets to 0 on any win, so it cannot exceed the trades since the last win either. Two
independent defects reached one counter:

  (a) THE RECONNECT REPLAY WAS JUDGED AS A SEQUENCE OF LOSING TRADES. Case 3 of
      `RecordRealizedDelta` judges any negative realized delta arriving while every tracked
      position reads Flat as a losing trade ON ITS OWN -- correct for the standalone adjustment
      `P1-16` wrote it for, and wrong for a replay, because the guard DID see those positions and
      is being re-told about the same fills. `P0-171` measured one Disconnected->Connected cycle
      replaying 118 orders and all 59 executions inside two seconds with the account flat.

  (b) THE ENTRY REFUSAL READ THE RAW COUNTER WITH NO DEADLINE. `LockoutBinds(...) ||
      ConsecutiveLosses >= Max` -- an OR, with nothing on the right-hand side that can expire. The
      counter had exactly three cures and none could run: a winning trade needs the action this
      rule blocks, so the cure requires the thing it forbids; the session reset is 22:00Z; and the
      lockout lapse never fired because `EvaluateRules` claims its lockout only `if (!IsLockedOut)`
      while DAILY_LOSS_BREACH already held an EOD lockout whose deadline is MinValue and by design
      never lapses. **(b) is the load-bearing half** -- it is what turns a wrong count into a
      temporary wrong count instead of a session-long trading ban.

⚠️ THE FIX ADDS A DEADLINE AND LOOSENS NOTHING. The refusal still fires on the same event; when a
lockout already exists this block is skipped entirely and that lockout keeps its own scope. Group 3
is what holds that line, and it is the group to read first.

THE GROUPS BELOW:

  1. THE REPLAY SUPPRESSION, AND ITS BOUND. Suppressing always is `P1-16` undone -- it refused to
     blind case 3 to untracked losses and was right to. Only the JUDGEMENT is suppressed; the money
     is still recorded, because the daily-loss rail reads it.
  2. THE CURE. A refusal that owns no deadline is a session-long ban, and the attribution matters
     as much as the deadline: `P0-166`'s cure clears the counter of whichever rule the attribution
     NAMES.
  3. ⚠️ THE CURE MUST NOT CLOBBER AN EXISTING LOCKOUT. `!IsLockedOut` is not redundant with
     `!LockoutBinds` -- a shadow-only lockout and a disarmed-bypass account are both `IsLockedOut`
     with `LockoutBinds` false. Arming there would re-attribute another rule's lockout and convert
     an EOD one into a 60-minute one, handing back an account the prop firm's own rail has stopped.
  4. THE INVARIANT IS REPORTED. `ConsecutiveLosses <= TradesToday` is free and nothing compared
     them, which is why an impossible value sat in persisted state unremarked: a refusal writes to
     interventions.jsonl, an increment wrote nowhere.

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # ---- group 1: the replay suppression and its bound ----------------------------------------
    (MODELS, 'group 1: the suppression is removed -- P1-172(a) exactly as measured. Every replayed '
             'negative execution is judged as its own losing trade, and a 16-trade session '
             'produces a streak of 17',
     '                if (UtcNow() <= ReplaySuppressionUntilUtc)\n'
     '                {\n'
     '                    OpenTradeRealizedDelta = 0.0;\n'
     '                    ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;\n'
     '                    return;\n'
     '                }\n',
     ''),

    (MODELS, 'group 1: the window test is inverted, so judgement is suppressed EVERYWHERE EXCEPT '
             'the replay. This is P1-16 undone -- the streak goes blind to real losses on positions '
             'the guard never saw, which is the trade P1-16 explicitly refused to make',
     '                if (UtcNow() <= ReplaySuppressionUntilUtc)',
     '                if (UtcNow() > ReplaySuppressionUntilUtc)'),

    (MODELS, 'group 1: the banked total is NOT cleared on suppression, so the replayed amount lands '
             'on the next genuine trade and is judged as part of it -- turning a win into a loss and '
             'incrementing the counter this exists to protect. The subtle one: it suppresses '
             'correctly and then leaks',
     '                    OpenTradeRealizedDelta = 0.0;\n'
     '                    ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;\n'
     '                    return;',
     '                    ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;\n'
     '                    return;'),

    (GUARD, 'group 1: the realized amount is not recorded, so suppressing the verdict also '
            'suppresses the money. DAILY_LOSS_BREACH reads RealizedPnL, so this disarms the daily '
            'loss rail for the length of every reconnect window',
     '                            state.RealizedPnL = newRealizedPnL;',
     '                            state.RealizedPnL = state.RealizedPnL;'),

    # ---- group 2: the cure -------------------------------------------------------------------
    (GUARD, 'group 2: the cure is removed -- P1-172(b) exactly as measured. The streak refuses '
            'every entry with no deadline attached to it by anything, and the only cure left is the '
            '22:00Z session reset, for a counter whose value is partly fabricated',
     '                            MarkRuleLockout(stateModel, "CONSECUTIVE_LOSS_BREACH",\n'
     '                                $"{stateModel.ConsecutiveLosses} consecutive losses against a "',
     '                            MarkRuleLockout(stateModel, "MAX_TRADES_BREACH",\n'
     '                                $"{stateModel.ConsecutiveLosses} consecutive losses against a "'),

    (GUARD, 'group 2: the cure is armed but carries no DEADLINE, so IsLockedOut is set with '
            'LockoutUntil at MinValue -- which EvaluateLockoutPhase reads as "no deadline", never '
            'lapses, and therefore never clears the counter. A cure that cannot complete, which is '
            'P0-166\'s shape restored one reader over',
     '                            stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.LockoutMinutes);\n'
     '                            _stateDirty = true;\n'
     '                            entryLockoutBinds = LockoutBinds(accountName, stateModel);',
     '                            _stateDirty = true;\n'
     '                            entryLockoutBinds = LockoutBinds(accountName, stateModel);'),

    (GUARD, 'group 2: the raw-counter clause loses its `> 0` guard, so an UNSET MaxConsecutiveLosses '
            'makes `0 >= 0` true and every entry on the account is refused. A missing setting must '
            'never fail in the refuse-everything direction',
     '                        bool streakAtCap = _config.Overtrading.MaxConsecutiveLosses > 0\n'
     '                            && stateModel.ConsecutiveLosses >= _config.Overtrading.MaxConsecutiveLosses;',
     '                        bool streakAtCap =\n'
     '                            stateModel.ConsecutiveLosses >= _config.Overtrading.MaxConsecutiveLosses;'),

    (GUARD, 'group 2: arming the cure REPLACES the refusal instead of accompanying it, so the order '
            'that tripped the streak is allowed through while the lockout is set. Strictly worse '
            'than the defect, and it reads as tidier control flow',
     # Re-anchored 2026-08-20: P2-162 added `|| cooldownActive` to this refusal condition.
     '                        if (entryLockoutBinds || streakAtCap || cooldownActive)\n'
     '                        {\n'
     '                            if (e.Order.OrderState == OrderState.Submitted || e.Order.OrderState == OrderState.Accepted || e.Order.OrderState == OrderState.Working)\n'
     '                            {\n'
     '                                if (!IsPositionReducingOrder(e.Order, stateModel))',
     '                        if (false)\n'
     '                        {\n'
     '                            if (e.Order.OrderState == OrderState.Submitted || e.Order.OrderState == OrderState.Accepted || e.Order.OrderState == OrderState.Working)\n'
     '                            {\n'
     '                                if (!IsPositionReducingOrder(e.Order, stateModel))'),

    (GUARD, 'group 2: the streak refusal stops exempting reducing orders, so a phantom streak traps '
            'the operator in a position -- which is the ONLY reason P1-172 is filed P1 and not P0. '
            '[[a-lockout-must-not-trap-you]]',
     '                            if (e.Order.OrderState == OrderState.Submitted || e.Order.OrderState == OrderState.Accepted || e.Order.OrderState == OrderState.Working)\n'
     '                            {\n'
     '                                if (!IsPositionReducingOrder(e.Order, stateModel))\n'
     '                                {\n'
     '                                    if (e.Order.OrderType == OrderType.Limit',
     '                            if (e.Order.OrderState == OrderState.Submitted || e.Order.OrderState == OrderState.Accepted || e.Order.OrderState == OrderState.Working)\n'
     '                            {\n'
     '                                if (true)\n'
     '                                {\n'
     '                                    if (e.Order.OrderType == OrderType.Limit'),

    # ---- group 3: the cure must not clobber an existing lockout -------------------------------
    (GUARD, 'group 3: `!IsLockedOut` is dropped, so the cure arms over a lockout another rule '
            'already owns. It RE-ATTRIBUTES that lockout to CONSECUTIVE_LOSS_BREACH, and P0-166 '
            'clears the counter of whichever rule the attribution names -- so on lapse the loss '
            'streak is forgiven because the daily-loss lockout expired. Reads as a redundant guard',
     '                        if (streakAtCap && !entryLockoutBinds && !stateModel.IsLockedOut\n'
     '                            && stateModel.LockoutUntil <= DateTime.UtcNow',
     '                        if (streakAtCap && !entryLockoutBinds\n'
     '                            && stateModel.LockoutUntil <= DateTime.UtcNow'),

    (GUARD, 'group 3: the existing-deadline test is dropped, so every refused entry RE-ARMS the '
            'deadline. The cure then never lapses while the operator keeps trying, and each attempt '
            'to trade extends the ban that is refusing it -- a retry whose exit condition its own '
            'action resets. [[a-retry-that-cannot-exit]]',
     '                            && stateModel.LockoutUntil <= DateTime.UtcNow\n'
     '                            && _config.Overtrading.LockoutMinutes > 0)',
     '                            && _config.Overtrading.LockoutMinutes > 0)'),

    # ---- group 4: the invariant is reported ---------------------------------------------------
    (GUARD, 'group 4: the invariant is never reported, so a phantom increment writes NOWHERE. This '
            'is the state the defect was found in -- an arithmetically impossible value sitting in '
            'persisted state, because nothing compared the two counters and nothing logged an '
            'increment',
     '                            if (state.ConsecutiveLosses > streakBefore\n'
     '                                && state.ConsecutiveLosses > state.TradesToday)',
     '                            if (false)'),

    (GUARD, 'group 4: the invariant fires on every increment rather than only impossible ones, so '
            'it reports every ordinary losing trade as a violation. An alarm that always fires is an '
            'alarm the operator learns to ignore, which is the same as not having one',
     '                            if (state.ConsecutiveLosses > streakBefore\n'
     '                                && state.ConsecutiveLosses > state.TradesToday)',
     '                            if (state.ConsecutiveLosses > streakBefore)'),

    (GUARD, 'group 4: the invariant CLAMPS instead of reporting. Reads as the helpful fix and is '
            'the wrong one: it hides the next mechanism that inflates this counter, which is '
            'precisely what cost a session to find the first time',
     '                                LogEvent(accountName, "COUNTER_INVARIANT_VIOLATED",',
     '                                state.ConsecutiveLosses = state.TradesToday;\n'
     '                                LogEvent(accountName, "NOT_THE_EVENT_ANYONE_READS",'),
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
            killed = _battery.score(res, run)
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
