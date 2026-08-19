"""Mutation battery for P0-166: a lockout's cure must be able to clear its trigger.

MEASURED LIVE on the funded account `TAKEPROFITPRO524207503`, 2026-08-19: eight identical cycles
between 07:15Z and 14:16Z, one an hour, each one

    LOCKOUT_LAPSED    ... the account is tradeable again.
    SHADOW_LOCKOUT    Rule DAILY_LOSS_BREACH ... no flatten executed.
    LOCKOUT_CONFIRMED ... all orders cancelled, position flat.

five seconds apart, with 80 `ENTRY_CANCEL` events in between. It would not have stopped on its own.
The account was in `shadow`, so every cancel was withheld -- in `live` the day is gone, and the
hourly "tradeable again" is an active invitation to place an order that is then cancelled.

`DAILY_LOSS_BREACH` triggers on session realized PnL, `TRAILING_DD_BREACH` on `PeakEquity`,
`MAX_TRADES_BREACH` on `TradesToday`. All three are cleared by exactly one thing, `SESSION_RESET`.
All three cured themselves with a 60-minute deadline. A deadline that lapses back into the same true
condition is not a cure, it is a loop -- [[a-retry-that-cannot-exit]] with the exit condition owned
by a counter the timeout cannot touch.

THE GROUPS BELOW:

  1. THE THREE HARD RAILS LOCK TO THE SESSION BOUNDARY. `MinValue` is the existing documented idiom
     for "no deadline"; the mutants restore the timeout and prove each rule is asserted separately,
     because fixing one and copying the wrong line into the next two is the obvious failure.
  2. WARNING: `CONSECUTIVE_LOSS_BREACH` KEEPS ITS TIMEOUT. This is the group that stops the fix
     over-reaching. Making it EOD would settle `P2-164` -- what counts as a loss, on which the
     operator holds two opposing views and asked for the right answer -- silently, from a bug fix.
     The mutant that makes it EOD must be KILLED.
  3. THE COOL-OFF ACTUALLY COOLS SOMETHING OFF. Clearing `ConsecutiveLosses` on lapse is the other
     half of leaving that rule on a timeout: without it the counter is still at its cap and the next
     evaluation re-locks with the account flat. And it is keyed on the rule that LOCKED -- a blanket
     clear is an amnesty that forgives a loss streak because an unrelated flood lockout expired.
     [[a-filter-that-matches-too-much]].
  4. THE LOCKOUT SAYS WHAT IT MEASURED. Eight hours of this read as routine because the line named
     a rule and no numbers. A rail whose log cannot answer "was that real?" costs a session to
     reconstruct from `nt_accounts` after the fact.
  5. THE RULES THAT CORRECTLY USE A TIMEOUT STILL DO. `ORDER_FLOOD_LOCKOUT`'s trigger IS cured by
     one second of time, and an operator's `LockAccount(name, minutes)` means what it says. Every
     detector needs a negative control, and a fix of the shape "stop using timeouts" is one
     over-generalisation away from ending a session over a double-clicked button.
     [[detector-needs-a-negative-test]].

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the three hard rails lock to the session boundary --------------------------
    (GUARD, 'group 1: the daily loss cure goes back to a 60-minute deadline -- the measured defect '
            'restored exactly, eight re-locks an hour apart and an hourly false all-clear',
     '                    ApplySessionScopedCure(stateModel);   // P0-166\n'
     '                    _stateDirty = true;\n'
     '                }\n'
     '            }\n'
     '\n'
     '            // Trailing Drawdown',
     '                    if (_config.PnLRules.LockoutMinutes > 0)\n'
     '                        stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.PnLRules.LockoutMinutes);\n'
     '                    _stateDirty = true;\n'
     '                }\n'
     '            }\n'
     '\n'
     '            // Trailing Drawdown'),

    (GUARD, 'group 1: the helper is called everywhere but does nothing -- every call site reads '
            'correctly and no lockout changes. A source scan for ApplySessionScopedCure finds four '
            'hits and proves nothing, which is why the assertion is on LockoutUntil',
     '        private void ApplySessionScopedCure(AccountState st)\n'
     '        {\n'
     '            st.LockoutUntil = DateTime.MinValue;\n'
     '        }',
     '        private void ApplySessionScopedCure(AccountState st)\n'
     '        {\n'
     '            // cure not applied\n'
     '        }'),

    (GUARD, 'group 1: the cure sets a deadline one minute out instead of no deadline. The loop is '
            'the same loop, 60x faster, and every assertion phrased as "there IS a lockout" still '
            'passes -- only an assertion on the DEADLINE catches it',
     '        private void ApplySessionScopedCure(AccountState st)\n'
     '        {\n'
     '            st.LockoutUntil = DateTime.MinValue;\n'
     '        }',
     '        private void ApplySessionScopedCure(AccountState st)\n'
     '        {\n'
     '            st.LockoutUntil = DateTime.UtcNow.AddMinutes(1);\n'
     '        }'),

    (GUARD, 'group 1: the TRAILING drawdown rail keeps the timeout while the other two are fixed. '
            'PeakEquity only resets at the session boundary, so this one re-locks forever too -- and '
            'a fix applied to the rule that was MEASURED, missing its two siblings, is the single '
            'likeliest way to half-close this entry',
     '                        + $"{stateModel.PeakEquity:F2}, against a {profile.TrailingDrawdown:F2} drawdown limit.");\n'
     '                    ApplySessionScopedCure(stateModel);   // P0-166',
     '                        + $"{stateModel.PeakEquity:F2}, against a {profile.TrailingDrawdown:F2} drawdown limit.");\n'
     '                    if (_config.PnLRules.LockoutMinutes > 0)\n'
     '                        stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.PnLRules.LockoutMinutes);'),

    (GUARD, 'group 1: the MAX TRADES rail keeps the timeout. An hour does not give the trades back, '
            'so the same loop runs on any account that hits its per-session cap',
     '                        $"{stateModel.TradesToday} trades against a {profile.MaxTradesPerSession} per-session cap.");\n'
     '                    ApplySessionScopedCure(stateModel);   // P0-166',
     '                        $"{stateModel.TradesToday} trades against a {profile.MaxTradesPerSession} per-session cap.");\n'
     '                    if (_config.Overtrading.LockoutMinutes > 0)\n'
     '                        stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.LockoutMinutes);'),

    (GUARD, 'group 1: the lapse guard stops honouring MinValue, so a session-scoped lockout expires '
            'immediately on the next evaluation. The cure is set correctly and released instantly -- '
            'the fix is entirely present and entirely undone one method away',
     '            if (stateModel.IsLockedOut\n'
     '                && stateModel.LockoutUntil > DateTime.MinValue\n'
     '                && DateTime.UtcNow >= stateModel.LockoutUntil)',
     '            if (stateModel.IsLockedOut\n'
     '                && DateTime.UtcNow >= stateModel.LockoutUntil)'),

    # ---- group 2: the consecutive-loss rule KEEPS its timeout --------------------------------
    (GUARD, 'group 2: THE MUTANT THIS BATTERY EXISTS FOR. The consecutive-loss rule is made EOD too '
            '-- uniform, tidy, and it decides P2-164 from inside a bug fix: three scratches would '
            'end the funded session, which is the exact outcome the operator asked to have measured '
            'rather than assumed',
     '                    if (_config.Overtrading.LockoutMinutes > 0)\n'
     '                    {\n'
     '                        stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.LockoutMinutes);\n'
     '                    }\n'
     '                    _stateDirty = true;\n'
     '                }\n'
     '            }\n'
     '\n'
     '            if (DateTime.UtcNow < stateModel.CooldownUntil)',
     '                    ApplySessionScopedCure(stateModel);\n'
     '                    _stateDirty = true;\n'
     '                }\n'
     '            }\n'
     '\n'
     '            if (DateTime.UtcNow < stateModel.CooldownUntil)'),

    # ---- group 3: the cool-off cools something off, and only for its own rule ----------------
    (GUARD, 'group 3: the counter is not cleared on lapse. The cool-off ends, the counter is still '
            'at its cap, and the next evaluation re-locks with the account flat and the trader '
            'having done nothing -- the same loop as the daily rail, reached by a different road',
     '                if (lapsedRule == "CONSECUTIVE_LOSS_BREACH")\n'
     '                    stateModel.ConsecutiveLosses = 0;',
     '                // counter not cleared on lapse'),

    (GUARD, 'group 3: the clear is unconditional, so ANY lapsing lockout forgives the loss streak. '
            'An order-rate burst expiring after 60 seconds would wipe a real streak of losses -- a '
            'filter that matches too much, on the permissive side',
     '                if (lapsedRule == "CONSECUTIVE_LOSS_BREACH")\n'
     '                    stateModel.ConsecutiveLosses = 0;',
     '                stateModel.ConsecutiveLosses = 0;'),

    (GUARD, 'group 3: the rule id is read AFTER it is cleared, so lapsedRule is always null and the '
            'counter is never cleared for anyone. Ordering, not logic -- the kind of defect that '
            'reads correctly line by line',
     '                string lapsedRule = stateModel.LockoutRuleId;   // P0-166: read before it is cleared',
     '                string lapsedRule = null;'),

    (GUARD, 'group 3: the rule id is never recorded, so the lapse path cannot tell which cure '
            'applies and the keyed clear never fires. The field exists, is persisted, is read -- and '
            'is written by nobody',
     '            st.LockoutRuleId = ruleId;   // P0-166: the lapse path needs to know which cure applies',
     '            // rule id not recorded'),

    (GUARD, 'group 3: the rule id is left set after the lockout releases, so a later unrelated lapse '
            'reads a stale reason and clears the loss counter on its authority. Stale state that '
            'only misbehaves on the SECOND lockout of a session',
     '                stateModel.LockoutRuleId = null;\n'
     '                _stateDirty = true;\n'
     '                LogEvent(stateModel.AccountName, "LOCKOUT_LAPSED",',
     '                _stateDirty = true;\n'
     '                LogEvent(stateModel.AccountName, "LOCKOUT_LAPSED",'),

    # ---- group 4: the lockout says what it measured ------------------------------------------
    (GUARD, 'group 4: the detail is computed and dropped on the floor. Every caller passes its '
            'numbers, the parameter is there, and the log line is exactly as uninformative as the '
            'one that made eight hours of re-locking read as routine. [[an-alarm-wired-to-a-dead-output]]',
     '                    + (string.IsNullOrEmpty(detail) ? "" : " " + detail));',
     '                    );'),

    (GUARD, 'group 4: the daily-loss detail names the loss but not the LIMIT, so the log says the '
            'account lost 346.25 and still cannot answer whether that breached anything',
     '                        $"Realized {currentPnL:F2} against a {profile.DailyLossLimit:F2} limit.");',
     '                        $"Realized {currentPnL:F2}.");'),

    (GUARD, 'group 4: the lapse no longer names the rule that locked, so the pair cannot be joined '
            'in the log -- which is how the hourly cycle was found in the first place',
     '                    + (string.IsNullOrEmpty(lapsedRule) ? "." : $" (locked by {lapsedRule})."));',
     '                    + ".");'),

    # ---- group 5: the rules that correctly use a timeout still do ----------------------------
    (GUARD, 'group 5: the ORDER FLOOD lockout is made session-scoped. Its trigger genuinely IS cured '
            'by one second of time, so this ends the trading session over a double-clicked button -- '
            'the over-generalisation that "stop using timeouts" leads to',
     '                                if (_config.Overtrading.LockoutMinutes > 0)\n'
     '                                {\n'
     '                                    stateModel.LockoutUntil = DateTime.UtcNow.AddMinutes(_config.Overtrading.LockoutMinutes);\n'
     '                                }',
     '                                ApplySessionScopedCure(stateModel);'),

    (GUARD, 'group 5: an operator timeout is swallowed into an EOD hold. LockAccount(name, 30) is an '
            'explicit instruction with a duration in it; answering it with "the rest of the session" '
            'is the guard overriding the person it reports to',
     '                        state.LockoutUntil = DateTime.UtcNow.AddMinutes(minutes);\n'
     '                        state.InitialLockoutFlattened = false; // force flatten sweep',
     '                        state.LockoutUntil = DateTime.MinValue;\n'
     '                        state.InitialLockoutFlattened = false; // force flatten sweep'),

    (GUARD, 'group 5: the operator UNLOCK stops clearing the recorded reason, so a manual release '
            'leaves a stale rule id that the next lapse acts on. The release path is the one an '
            'operator reaches for when a rail has already misfired',
     '                    state.LockoutRuleId = null;   // P0-166\n'
     '                    state.PeakEquity = 0.0;',
     '                    state.PeakEquity = 0.0;'),

    (GUARD, 'group 5: the SESSION RESET stops clearing the reason. The session boundary is the cure '
            'for all three hard rails, so a reason surviving it is a reason that outlives the '
            'lockout it explains -- for the whole of the next day',
     '            stateModel.LockoutRuleId = null;   // P0-166\n'
     '            stateModel.ResetLockoutPhase();   // P2-101',
     '            stateModel.ResetLockoutPhase();   // P2-101'),
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
# tools/check_expected_survivors.py enforces the pairing in BOTH directions -- reaching for the
# helper without a declaration removes the prompt to justify the next exemption someone adds.
if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
