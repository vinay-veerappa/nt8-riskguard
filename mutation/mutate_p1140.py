"""Mutation battery for P1-140: the partial-profit order that joined the protective OCO group.

`PlaceBracket` creates the stop and the target at the FULL position quantity, both carrying the
bracket's `ocoId`. `MonitorTickCore`'s DrawdownShield partial block then submitted a THIRD order
into that same group at HALF the quantity. Measured red at baseline: a two-lot bracket past its
partial trigger left THREE orders carrying the bracket's OCO id.

Every outcome NT8 can pick is a defect. The new order JOINS the live group -- live-validated in
this repo by `TestBracket_P0_9_ALateTargetJoinsTheLiveStopsOcoGroup`, and the copier is built on
it -- so the partial's fill cancels the stop AND the target and the remaining lot is unprotected.
If it does not cancel, the stop is still sized for two against a position of one and firing it
FLIPS the position (`P1-56`'s shape, already found in the copier). If the id is refused, the
partial silently never happens and `PartialProfitTaken = true` on the next line means it is never
retried.

⚠️ NOTHING HAD EVER EXECUTED THIS BLOCK. `partialQty = (int)Math.Floor(Quantity * 0.50)` is ZERO
for one lot and `if (partialQty > 0)` skips everything -- and every test in the suite and every
live bracket measured on this box has been one lot. `DrawdownShield`, the only type with a partial
block, is the DEFAULT `AtmStrategyConfig.Type`.

⚠️ GROUP 1 IS THE DEFECT ITSELF, and it is the mutant to keep: it puts the submission back. A fix
that merely stops SAYING something is not the same as a fix that stops submitting.

⚠️ GROUP 2 ATTACKS THE SINK, which the agent loop has already got wrong once in this file.
`Code.Output.Process` writes the NT8 output tab, which no operator surface and no audit query
reads -- the announcement exists, names the right bracket, and reaches nobody.
[[an-alarm-wired-to-a-dead-output]].

⚠️ GROUP 3 ATTACKS THE LATCH IN BOTH DIRECTIONS. Never set: a line every five seconds for the life
of a winning trade, which is the spam `P2-134` and `P2-135` were about. Read but never announced:
silence, which is the failure this whole entry is about.

⚠️ GROUP 4 ATTACKS THE `partialQty > 0` GUARD, and the mutant that removes it is the one a positive
test cannot see: it makes the line fire on every ONE-LOT bracket -- which is every bracket this box
has ever placed. A detector that fires on everything passes every positive test written for it.
[[detector-needs-a-negative-test]].

⚠️ GROUP 5 ATTACKS THE GATE'S TWO CLAUSES. `!PartialProfitTaken` is redundant TODAY, because nothing
assigns it -- and the follow-on ID that makes partials real assigns it again, at which point a gate
asking only "have we announced?" re-evaluates a partial already taken.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

# ⚠️ REQUIRED. Without it one non-ASCII character in a mutant description raises
# UnicodeEncodeError inside print() on a cp1252 console -- AFTER the mutant is applied and BEFORE it
# is restored, leaving a LIVE MUTANT in the source tree. Twice for real in this repo.
# tools/check_batteries_pin_encoding.py is the gate. [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')

# ⚠️ THE ANNOUNCEMENT LITERAL IS REPEATED IN FULL AT EACH SITE RATHER THAN HOISTED INTO A CONSTANT,
# and that is not an oversight. check_anchors.py reads these tuples STATICALLY and refuses to skip an
# entry it cannot parse -- a `CONST + '...'` find-string reported three BROKEN ANCHORS here on the
# first run. Silently skipping them would be worse: an unparsed anchor is an unvalidated one, and an
# anchor that stops matching scores a SURVIVOR. [[mutation-anchors-go-stale]].
MUTANTS = [
    # ---- group 1: THE DEFECT, restored --------------------------------------------------------
    (ATM,
     "⚠️ THE DEFECT, RESTORED: the partial order is submitted again, into the stop and\n"
     "     target's OWN OCO group, at HALF their quantity. Its fill cancels both protective legs\n"
     "     and the remaining lot is naked. This is P1-140 exactly: three members in a group of two",
     '                                    RiskGuardAddOn.LogFromComponent(bracket.AccountName, "ATM_PARTIAL_PROFIT_UNAVAILABLE",\n'
     '                                        $"{bracket.BracketId}: partial profit of {partialQty} of {bracket.Quantity} cannot be taken "\n'
     '                                        + $"because the order would join the protective OCO group \'{bracket.OcoId}\' and cancel the "\n'
     '                                        + "remaining stop and target, leaving the rest of the position unprotected.");\n'
     '                                    bracket.PartialProfitUnavailableAnnounced = true;',
     '                                    var exitAction = isLong ? OrderAction.Sell : OrderAction.Buy;\n'
     '                                    var partialOrder = account.CreateOrder(position.Instrument, exitAction, OrderType.Limit, TimeInForce.Day, partialQty, partialTarget, 0, bracket.OcoId, "Partial_" + bracket.BracketId, null);\n'
     '                                    account.Submit(new[] { partialOrder });\n'
     '                                    bracket.PartialProfitUnavailableAnnounced = true;'),

    # ---- group 2: the SINK ---------------------------------------------------------------------
    (ATM,
     "⚠️ THE ANNOUNCEMENT GOES TO THE WRONG SINK: Code.Output.Process writes the NT8\n"
     "     output tab, which no operator surface and no audit query reads. It exists, it is\n"
     "     correct, and it reaches nobody. The loop shipped this exact substitution once already",
     '                                    RiskGuardAddOn.LogFromComponent(bracket.AccountName, "ATM_PARTIAL_PROFIT_UNAVAILABLE",\n'
     '                                        $"{bracket.BracketId}: partial profit of {partialQty} of {bracket.Quantity} cannot be taken "\n'
     '                                        + $"because the order would join the protective OCO group \'{bracket.OcoId}\' and cancel the "\n'
     '                                        + "remaining stop and target, leaving the rest of the position unprotected.");\n',
     '                                    NinjaTrader.Code.Output.Process($"{bracket.BracketId} partial unavailable", PrintTo.OutputTab1);\n'),

    # ---- group 3: the latch, both directions --------------------------------------------------
    (ATM,
     "the latch is never SET, so the line is said on every sweep for the life of a winning\n"
     "     trade -- once every five seconds, which is the spam P2-134 and P2-135 were about",
     '                                    bracket.PartialProfitUnavailableAnnounced = true;',
     '                                    bracket.PartialProfitUnavailableAnnounced = false;'),

    (ATM,
     "the announcement is DROPPED and only the latch is set, so a partial that cannot be taken\n"
     "     is silent -- indistinguishable from a bracket that never reached the trigger, which is\n"
     "     the failure this entry is about",
     '                                    RiskGuardAddOn.LogFromComponent(bracket.AccountName, "ATM_PARTIAL_PROFIT_UNAVAILABLE",\n'
     '                                        $"{bracket.BracketId}: partial profit of {partialQty} of {bracket.Quantity} cannot be taken "\n'
     '                                        + $"because the order would join the protective OCO group \'{bracket.OcoId}\' and cancel the "\n'
     '                                        + "remaining stop and target, leaving the rest of the position unprotected.");\n',
     ''),

    # ---- group 4: the quantity guard and what the message carries ------------------------------
    (ATM,
     "⚠️ THE `partialQty > 0` GUARD GOES, so the line fires on every ONE-LOT bracket --\n"
     "     which is every bracket this box has ever placed. A detector that fires on everything\n"
     "     passes every positive test written for it; only the negative control sees this",
     '                                if (partialQty > 0)',
     '                                if (partialQty >= 0)'),

    (ATM,
     "the quantity in the message becomes the FULL position rather than the partial, so the\n"
     "     operator is told a 2-lot partial was unavailable on a 2-lot position -- the message\n"
     "     still fires, still names a number, and the number is wrong",
     '$"{bracket.BracketId}: partial profit of {partialQty} of {bracket.Quantity} cannot be taken "',
     '$"{bracket.BracketId}: partial profit of {bracket.Quantity} of {bracket.Quantity} cannot be taken "'),

    (ATM,
     "the REASON goes: the message no longer names the OCO group it would have had to join, so\n"
     "     'a partial did not happen' is indistinguishable from never having tried and there is\n"
     "     nothing to grep for when someone asks why",
     '                                        + $"because the order would join the protective OCO group \'{bracket.OcoId}\' and cancel the "\n'
     '                                        + "remaining stop and target, leaving the rest of the position unprotected.");',
     '                                        + "and was not taken.");'),

    # ---- group 5: the gate's two clauses ------------------------------------------------------
    (ATM,
     "the `!PartialProfitTaken` clause goes. Redundant TODAY -- nothing assigns it -- and the\n"
     "     follow-on ID that makes partials real assigns it again, at which point this gate\n"
     "     re-evaluates a partial that has ALREADY been taken and reports it unavailable",
     '                        if (!bracket.PartialProfitTaken\n'
     '                            && !bracket.PartialProfitUnavailableAnnounced\n'
     '                            && bracket.BreakevenTriggered)',
     '                        if (!bracket.PartialProfitUnavailableAnnounced\n'
     '                            && bracket.BreakevenTriggered)'),

    (ATM,
     "the latch clause is no longer READ, so the block re-enters every sweep even though the\n"
     "     latch is being set -- the same five-second line, reached by dropping the reader\n"
     "     instead of the writer",
     '                        if (!bracket.PartialProfitTaken\n'
     '                            && !bracket.PartialProfitUnavailableAnnounced\n'
     '                            && bracket.BreakevenTriggered)',
     '                        if (!bracket.PartialProfitTaken\n'
     '                            && bracket.BreakevenTriggered)'),

    (ATM,
     "PartialProfitTaken is assigned true again, as the latch. It reports that a partial WAS\n"
     "     taken when none was, on the flag the bridge payload publishes as `partialProfitTaken`,\n"
     "     and gives one bool two meanings -- which is what P1-139 removed from this same file",
     '                                    bracket.PartialProfitUnavailableAnnounced = true;',
     '                                    bracket.PartialProfitTaken = true;'),
]

ORIGINALS = {}
for target, _, _, _ in MUTANTS:
    if target not in ORIGINALS:
        # ⚠️ NO newline='' ON THE READ -- check_anchors.py enforces it. The gate matches anchors
        # against universal-newline text, so a battery searching CRLF text is validated against a
        # string it never looks for: the anchor reads `ok` and the mutant scores a SURVIVOR. The
        # WRITE keeps newline='' so the file is rewritten as read. [[mutation-anchors-go-stale]].
        ORIGINALS[target] = open(target, encoding='utf-8').read()


def restore():
    for target, text in ORIGINALS.items():
        open(target, 'w', encoding='utf-8', newline='').write(text)


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
    # try/finally as well as the encoding pin: the pin closes the failure that has happened twice,
    # the finally closes every other way of leaving the loop with a mutant applied.
    try:
        res = run()
        mm = re.search(r'Failed = (\d+)', res)
        killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
            or (mm is not None and int(mm.group(1)) > 0)
        # P2-148: the verdict above cannot tell a detection from a crash.
        if 'NO ASSERTION FAILED' in res:
            killed = False
        print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
        if not killed:
            survivors.append(name)
    finally:
        restore()

restore()
print('\nrestored originals;', run())

# The PLAIN exit, not _battery.finish: this battery declares no expected survivor, and
# check_expected_survivors.py enforces that difference in both directions.
sys.exit(1 if survivors else 0)
