"""Mutation battery for P2-135, P2-136 and P3-137: the three things the ATM manager knew and
never told anyone.

All three are the same shape -- state that EXISTS and is reported to nobody -- and all three were
invisible on every surface an operator has.

P2-135. `ATM_STOP_MOVE_ABANDONED` was emitted from the TOP of `RequestStopMove`, so it was said
only if something CALLED that method again after the budget was already spent. Of the two sites
that spend it, only one has a caller afterwards. Measured live on `Sim101`, bracket `75726b75`:
three `ATM_STOP_CHANGE_IGNORED` lines ending "attempt 3 of 3", then nothing for the life of the
position. The give-up line was reachable only when the trade was WINNING.

P2-136. Both removal branches dropped a bracket SILENTLY, so one that stopped being managed was
indistinguishable from one that was never added. Bracket `1a48f3cf`, 2026-08-17: registered at
23:16 with an open 1-lot position, gone by 23:17:3x, position still long 1, nothing logged.

P3-137/a. `IsComplete` was assigned true nowhere -- two filters and one API field inert -- while
the three fields that answer "has this given up, and why?" were not exposed at all.

⚠️ GROUP 2 IS THE ONE TO KNOW, AND IT IS NOT HYPOTHETICAL. The agent loop's own patch wired the
P2-136 announcement to `NinjaTrader.Code.Output.Process` instead of `RiskGuardAddOn.LogFromComponent`.
Those are DIFFERENT SINKS: `Output.Process` writes the NT8 output tab, which no operator surface
and no audit query reads. The announcement existed, was correct, named the right bracket -- and
reached nobody, which is the defect it was added to fix, reintroduced by the fix. Two mutants
here restore that, one per branch, because a fix whose output nobody consumes passes every gate
that checks the fix exists. [[an-alarm-wired-to-a-dead-output]].

⚠️ GROUP 3 ATTACKS ORDER, NOT PRESENCE. `AnnounceStopMoveAbandonmentIfNeeded` must be called
AFTER `LastStopMoveFailureReason` is set. Called before, it still fires, still says "3 stop moves
failed", and still looks right in every test that only counts announcements -- while reporting
the PREVIOUS failure, or "not recorded". Moving a call one line is the smallest edit that keeps a
feature working and makes it lie.

⚠️ GROUP 4 ATTACKS THE TWO BRANCHES SAYING THE SAME THING. A flat position with no working entry
is a finished trade and is entirely normal; an account absent from `Account.All` is a bracket
orphaned while its position may still be open. One sentence for both turns a routine event and a
serious one into the same line, and every assertion that "a release was announced" still passes.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

# ⚠️ REQUIRED, and this battery proved it the hard way on its first run. Without this, one
# non-ASCII character in a mutant description raises UnicodeEncodeError inside print() on a
# cp1252 console -- AFTER the mutant is applied and BEFORE it is restored, leaving a LIVE MUTANT
# in the source tree. It happened here: the crash left the P2-135 defect itself sitting in
# DynamicAtmManager.cs, and a commit at that moment would have shipped back the bug this battery
# exists to prove was fixed. tools/check_batteries_pin_encoding.py is the gate; it already named
# this failure from mutate_p182.py in CI on 2026-08-15, so this is the SECOND instance.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')
TESTS = os.path.join(REPO, 'tests', 'RiskGuardAddOnTests.cs')

MUTANTS = [
    # ---- group 1: P2-135, the announcement goes back to where nothing calls it ------------------
    (ATM,
     "⚠️ THE DEFECT, RESTORED: the reconciler's refusal stops announcing, so the give-up\n"
     "     line is reachable only from RequestStopMove -- which, on this path, nothing calls\n"
     "     again. This is P2-135 exactly: budget spent 3 of 3, announcements 0",
     '                        bracket.LastStopMoveFailureReason = $"provider holds {brokerPrice} instead of requested {requested}";\n'
     '                        AnnounceStopMoveAbandonmentIfNeeded(account, bracket);',
     '                        bracket.LastStopMoveFailureReason = $"provider holds {brokerPrice} instead of requested {requested}";'),

    (ATM,
     "EXPECTED SURVIVOR: the ModifyStopPrice site stops announcing. It survived on the first\n"
     "     run and the reason is real rather than a test gap: on THIS path the breakeven caller\n"
     "     does re-ask next sweep, so the top-of-method check announces anyway. The call is kept\n"
     "     because it announces one 5-second sweep EARLIER, and no test can distinguish five\n"
     "     seconds. Declared rather than deleted so the redundancy is a recorded decision -- if\n"
     "     the top-of-method check is ever removed, this stops being redundant and the mutant\n"
     "     starts failing, which is the signal wanted",
     '                bracket.StopModifyAttempts++;\n'
     '                AnnounceStopMoveAbandonmentIfNeeded(account, bracket);',
     '                bracket.StopModifyAttempts++;'),

    (ATM,
     "the latch clear goes away, so a bracket that RECOVERED and later failed again never\n"
     "     announces the second failure -- on a position the operator believes is trailing. This\n"
     "     is the line P2-134 argued could never run, and the loop proved reachable",
     '                    bracket.StopMoveAbandonAnnounced = false;',
     '                    bracket.StopMoveAbandonAnnounced = true;'),

    # ---- group 2: THE SINK -- the defect the loop's own patch shipped ---------------------------
    (ATM,
     "⚠️ THE RELEASE LINE GOES TO THE WRONG SINK (orphan branch): Code.Output.Process writes\n"
     "     the NT8 output tab, which no operator surface and no audit query reads. The\n"
     "     announcement exists, is correct, and reaches nobody. The loop's patch did this",
     '                        RiskGuardAddOn.LogFromComponent(bracket.AccountName, "ATM_BRACKET_RELEASED",\n'
     '                            $"{bracket.BracketId}: account',
     '                        NinjaTrader.Code.Output.Process($"{bracket.BracketId} released", PrintTo.OutputTab1);\n'
     '                        if (false) RiskGuardAddOn.LogFromComponent(bracket.AccountName, "ATM_BRACKET_RELEASED",\n'
     '                            $"{bracket.BracketId}: account'),

    (ATM,
     "the same wrong sink on the FINISHED-TRADE branch, which is the one that fires on every\n"
     "     normal exit and so is the one an operator would notice missing last",
     '                            RiskGuardAddOn.LogFromComponent(bracket.AccountName, "ATM_BRACKET_RELEASED",\n'
     '                                $"{bracket.BracketId}: {bracket.Symbol} position is flat',
     '                            NinjaTrader.Code.Output.Process($"{bracket.BracketId} released", PrintTo.OutputTab1);\n'
     '                            if (false) RiskGuardAddOn.LogFromComponent(bracket.AccountName, "ATM_BRACKET_RELEASED",\n'
     '                                $"{bracket.BracketId}: {bracket.Symbol} position is flat'),

    # ---- group 3: ORDER, not presence ----------------------------------------------------------
    (ATM,
     "⚠️ THE ANNOUNCEMENT MOVES ONE LINE EARLIER, before the reason is recorded. It still\n"
     "     fires, still counts once, still says '3 stop moves failed' -- and reports the\n"
     "     PREVIOUS failure or 'not recorded'. The smallest edit that keeps a feature working\n"
     "     and makes it lie",
     '                        bracket.StopModifyAttempts++;\n'
     '                        bracket.LastStopMoveFailureReason = $"provider holds {brokerPrice} instead of requested {requested}";\n'
     '                        AnnounceStopMoveAbandonmentIfNeeded(account, bracket);',
     '                        bracket.StopModifyAttempts++;\n'
     '                        AnnounceStopMoveAbandonmentIfNeeded(account, bracket);\n'
     '                        bracket.LastStopMoveFailureReason = $"provider holds {brokerPrice} instead of requested {requested}";'),

    (ATM,
     "the budget check inside the announcer is dropped, so it announces on the FIRST failure.\n"
     "     'Not asking again for this bracket' said after attempt 1 of 3, while it goes on to\n"
     "     ask twice more -- a message that contradicts what the code then does",
     '            if (bracket.StopModifyAttempts < MaxStopModifyAttempts)\n'
     '                return;',
     '            if (false)\n'
     '                return;'),

    # ---- group 4: the two branches must not say the same thing ---------------------------------
    (ATM,
     "⚠️ BOTH REMOVAL BRANCHES SAY THE SAME SENTENCE, so a routine finished trade and a\n"
     "     bracket ORPHANED with its position possibly still open are one line. Every assertion\n"
     "     that 'a release was announced' still passes",
     '                            $"{bracket.BracketId}: {bracket.Symbol} position is flat and no entry "\n'
     '                                + "order is still working, so the trade is finished and the bracket "\n'
     '                                + "is released. Nothing further is managed for it.");',
     '                            $"{bracket.BracketId}: account \'{bracket.AccountName}\' is no longer in "\n'
     '                                + "Account.All, so this bracket is ORPHANED and no longer managed. Its "\n'
     '                                + "position may still be open, and its stop will not move again.");'),

    (ATM,
     "the release line stops naming WHICH bracket. An operator with two positions open cannot\n"
     "     act on 'a bracket was released', and a test that only asserts a line was emitted\n"
     "     passes under this",
     '                                $"{bracket.BracketId}: {bracket.Symbol} position is flat and no entry "',
     '                                $"a bracket: {bracket.Symbol} position is flat and no entry "'),

    # ---- group 5: P3-137a, the status ----------------------------------------------------------
    (ATM,
     "the status reports a CONSTANT zero attempts rather than the bracket's own count, which\n"
     "     is the P3-137 defect in a new field: a value that can never change, advertised to\n"
     "     every consumer as if it were state",
     '                        stopModifyAttempts = b.StopModifyAttempts,',
     '                        stopModifyAttempts = 0,'),

    (ATM,
     "the observed reason is dropped from the status, so 'has this given up?' is answerable\n"
     "     and 'why' is not -- and the only other evidence is a log line that, before P2-135,\n"
     "     might never have been emitted",
     '                        lastStopMoveFailureReason = b.LastStopMoveFailureReason,',
     ''),

    # ---- group 6: the latch ---------------------------------------------------------------------
    #
    # ⚠️ THIS GROUP REPLACED TWO TEST-MUTANTS THAT COULD NOT BE KILLED BY CONSTRUCTION, and the
    # reason is worth keeping. One re-added the caller line whose ABSENCE is the P2-135 test's
    # whole point; the other replaced a passing precondition with Assert(true, ...). Both
    # SURVIVED, and neither survival meant anything: with the fix in place the first still
    # passes, and DELETING A PASSING ASSERTION CAN NEVER FAIL A SUITE. A mutant whose kill
    # condition cannot occur is a permanent survivor wearing the costume of a finding. Whether an
    # assertion RUNS is proved by source mutants, which is what the rest of this file is.
    (ATM,
     "the announcer stops SETTING its latch, so it fires on every sweep once the budget is\n"
     "     spent -- P2-134 restored through the new code path. The reconciler increments\n"
     "     unconditionally, so the count keeps rising and the announcement keeps coming",
     '            bracket.StopMoveAbandonAnnounced = true;\n'
     '        }',
     '        }'),
]

ORIGINALS = {ATM: open(ATM, encoding='utf-8').read(),
             TESTS: open(TESTS, encoding='utf-8').read()}


def restore():
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
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if not m and '[FAIL]' not in ((p.stdout or '') + (p.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return m.group(0) if m else 'NO RESULT LINE'


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
    # try/finally as well as the encoding pin above. The pin closes the one failure that has
    # actually happened twice; the finally closes EVERY way of leaving the loop with a mutant
    # applied, including the next one nobody has thought of. A restore that depends on reaching
    # the end of an iteration is a restore that a KeyboardInterrupt also skips.
    try:
        res = run()
        killed = _battery.score(res, run)
        print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
        if not killed:
            survivors.append(name)
    finally:
        restore()

restore()
print('\nrestored originals;', run())

# _battery.finish, NOT a plain sys.exit: this battery declares an EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions -- a plain exit
# beside a declaration would report the expected survivor as a failure forever, and a
# declaration with no survivor is just as wrong.
_battery.finish(survivors, MUTANTS)
