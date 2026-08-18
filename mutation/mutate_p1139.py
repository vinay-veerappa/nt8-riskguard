"""Mutation battery for P1-139: the stop that moved AGAINST a live position.

One refused trailing move made the breakeven branch ask the broker to put the stop BACK at
breakeven. `BreakevenTriggered` carried three meanings -- "breakeven has been reached" to the
breakeven branch, "the trail may run" to the trailing branch, and, since P0-67, "retry the
outstanding move" to the reconciler. Clearing it to retry a BREAKEVEN move is correct and is what
P0-67 was for; clearing it to retry a TRAIL move recomputes the target from ENTRY, which knows
nothing about how far the trail has carried the stop.

Measured red at baseline: a long from 20000.00 with the stop trailed to 20010.00 has one move to
20013.00 refused, and the SAME sweep requests 20000.50 -- 9.5 points of locked profit handed back,
logged as `requested stop 20010 -> 20000.5` as though it were an advance.

⚠️ GROUP 1 ATTACKS DIRECTION, AND IT MUST BE ATTACKED ON BOTH SIDES. "Better" is HIGHER for a long
and LOWER for a short. A long-only suite cannot see the flipped comparison, because every ATM test
in this file was long until P1-139 added a short. Two mutants, one per side.

⚠️ GROUP 2 ATTACKS THE BASELINE SENTINEL, WHICH IS WHERE THE OBVIOUS FIX KILLS EVERY SHORT.
`CurrentStopPrice` is 0 on a bracket that has never reconciled. Read as a price rather than as "no
baseline", a short's first move -- 19999.50 against 0 -- is wrong-way and is refused for the life of
the position. The round-2 arbiter UPHELD a finding demanding exactly that reading, and the patch
honoured it by defaulting the field to NaN, which GetBracketStatus serialises into the bridge's ATM
status payload where it stops being a number. The decision was reversed by measurement.
[[an-inapplicable-state-is-not-unreadable]].

⚠️ GROUP 3 ATTACKS THE HALF THAT IS EASY TO MISS: guarding the direction ALONE latches the trail
off. The trailing block is gated on `BreakevenTriggered`, so if the breakeven branch keeps being
refused without recording that breakeven was REACHED, the stop never moves again -- P0-67's original
defect restored by its own repair. Deleting `alreadyAtBreakeven` leaves a green-looking guard and a
dead trail. [[a-fix-can-commit-its-own-defect]].

⚠️ GROUP 4 ATTACKS THE KIND, NOT ITS PRESENCE. The re-arm must fire for a refused BREAKEVEN move and
must NOT fire for a refused TRAIL move. A condition that ignores the kind restores the defect; one
inverted to `Trail` breaks P0-67's retry. Both keep the field, the enum and the plumbing intact, so
every test that merely checks the kind is recorded still passes.

⚠️ GROUP 5 ATTACKS THE COST OF OUR OWN REFUSAL. A refusal this class makes on its own behalf is not
a provider refusal: spending `StopModifyAttempts` on it means three wrong-way requests abandon a
bracket whose stop is in perfect shape, and leaving `RequestedStopPrice` set blocks every later move
for the life of the position, because RequestStopMove returns early while one is in flight.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

# ⚠️ REQUIRED. Without it one non-ASCII character in a mutant description raises
# UnicodeEncodeError inside print() on a cp1252 console -- AFTER the mutant is applied and BEFORE
# it is restored, leaving a LIVE MUTANT in the source tree. That has happened twice in this repo
# (mutate_p182.py in CI, then mutate_p2135.py on its first run, which left the P2-135 defect
# itself sitting in DynamicAtmManager.cs). tools/check_batteries_pin_encoding.py is the gate.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')

MUTANTS = [
    # ---- group 1: direction, both sides --------------------------------------------------------
    (ATM,
     "⚠️ THE DEFECT, RESTORED: the wrong-way guard goes away entirely, so RequestStopMove asks\n"
     "     the broker for whatever it is handed. This is P1-139: stop 20010 -> 20000.5 on a live\n"
     "     long, five seconds after one refusal",
     '            if (bracket.CurrentStopPrice > 0)\n'
     '            {\n'
     '                bool wrongWay = bracket.IsLong',
     '            if (false)\n'
     '            {\n'
     '                bool wrongWay = bracket.IsLong'),

    (ATM,
     "the direction is INVERTED: a long now refuses improvements and accepts loosening. Every\n"
     "     long assertion in the file flips, which is the point -- this is the mutant a suite\n"
     "     that only tested presence of the guard would miss",
     '                bool wrongWay = bracket.IsLong\n'
     '                    ? (newStopPrice <= bracket.CurrentStopPrice)\n'
     '                    : (newStopPrice >= bracket.CurrentStopPrice);',
     '                bool wrongWay = bracket.IsLong\n'
     '                    ? (newStopPrice >= bracket.CurrentStopPrice)\n'
     '                    : (newStopPrice <= bracket.CurrentStopPrice);'),

    (ATM,
     "the SHORT side is dropped -- both branches use the long comparison. A short's stop then\n"
     "     only ever moves UP, away from price, which is the wrong way for a short. Nothing in\n"
     "     this file tested a short at all before P1-139",
     '                bool wrongWay = bracket.IsLong\n'
     '                    ? (newStopPrice <= bracket.CurrentStopPrice)\n'
     '                    : (newStopPrice >= bracket.CurrentStopPrice);',
     '                bool wrongWay = (newStopPrice <= bracket.CurrentStopPrice);'),

    (ATM,
     "EQUAL prices stop being refused, so a redundant Change() reaches the broker. P0-61: a\n"
     "     second change while one is in flight reverts the order, so a no-op request is pure\n"
     "     risk with nothing to gain",
     '                    ? (newStopPrice <= bracket.CurrentStopPrice)\n'
     '                    : (newStopPrice >= bracket.CurrentStopPrice);',
     '                    ? (newStopPrice < bracket.CurrentStopPrice)\n'
     '                    : (newStopPrice > bracket.CurrentStopPrice);'),

    # ---- group 2: the baseline sentinel, where the obvious fix kills every short ----------------
    (ATM,
     "⚠️ AN UNSET BASELINE IS READ AS A PRICE: the `> 0` gate goes, so a bracket that has never\n"
     "     reconciled compares against 0. For a SHORT, better is LOWER, so its first move\n"
     "     (19999.50 against 0) is wrong-way and is refused forever. The round-2 arbiter upheld a\n"
     "     finding demanding this reading; it was reversed by measurement",
     '            if (bracket.CurrentStopPrice > 0)\n'
     '            {\n'
     '                bool wrongWay = bracket.IsLong',
     '            if (true)\n'
     '            {\n'
     '                bool wrongWay = bracket.IsLong'),

    (ATM,
     "the non-positive TARGET check goes, so a garbage price computed from a garbage entry is\n"
     "     forwarded to the broker as a stop",
     '            if (newStopPrice <= 0)',
     '            if (false)'),

    # ---- group 3: the half that latches the trail off ------------------------------------------
    (ATM,
     "⚠️ THE OTHER HALF, REMOVED: `alreadyAtBreakeven` never fires, so a stop already better\n"
     "     than breakeven produces a wrong-way request that the guard refuses -- leaving\n"
     "     BreakevenTriggered false, and the trailing block is gated on it. The guard is green\n"
     "     and the trail is dead. P0-67's defect restored by its own repair",
     '                                bool alreadyAtBreakeven = bracket.CurrentStopPrice > 0\n'
     '                                    && (isLong ? bracket.CurrentStopPrice >= beStop : bracket.CurrentStopPrice <= beStop);\n'
     '                                if (alreadyAtBreakeven)\n'
     '                                {\n'
     '                                    bracket.BreakevenTriggered = true;\n'
     '                                    bracket.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;\n'
     '                                }\n'
     '                                else if (RequestStopMove(account, bracket, beStop, "breakeven trigger reached", ActiveBracket.StopMoveKind.Breakeven))\n'
     '                                {\n'
     '                                    bracket.BreakevenTriggered = true;\n'
     '                                }\n'
     '                            }\n'
     '                        }\n'
     '\n'
     '                        if (bracket.BreakevenTriggered)',
     '                                if (RequestStopMove(account, bracket, beStop, "breakeven trigger reached", ActiveBracket.StopMoveKind.Breakeven))\n'
     '                                {\n'
     '                                    bracket.BreakevenTriggered = true;\n'
     '                                }\n'
     '                            }\n'
     '                        }\n'
     '\n'
     '                        if (bracket.BreakevenTriggered)'),

    (ATM,
     "`alreadyAtBreakeven` fires but stops RECORDING it -- the request is skipped and the flag\n"
     "     stays false. Same dead trail, reached by omission rather than by deletion, and the\n"
     "     wrong-way log is silent so there is nothing to grep for either",
     '                                if (alreadyAtBreakeven)\n'
     '                                {\n'
     '                                    bracket.BreakevenTriggered = true;\n'
     '                                    bracket.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;\n'
     '                                }\n'
     '                                else if (RequestStopMove(account, bracket, beStop, "breakeven trigger reached", ActiveBracket.StopMoveKind.Breakeven))\n'
     '                                {\n'
     '                                    bracket.BreakevenTriggered = true;\n'
     '                                }\n'
     '                            }\n'
     '                        }\n'
     '\n'
     '                        if (bracket.BreakevenTriggered)',
     '                                if (alreadyAtBreakeven)\n'
     '                                {\n'
     '                                    bracket.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;\n'
     '                                }\n'
     '                                else if (RequestStopMove(account, bracket, beStop, "breakeven trigger reached", ActiveBracket.StopMoveKind.Breakeven))\n'
     '                                {\n'
     '                                    bracket.BreakevenTriggered = true;\n'
     '                                }\n'
     '                            }\n'
     '                        }\n'
     '\n'
     '                        if (bracket.BreakevenTriggered)'),

    # ---- group 4: the KIND, not its presence ---------------------------------------------------
    (ATM,
     "⚠️ THE RE-ARM STOPS ASKING WHICH MOVE WAS LOST: the kind clause goes, so a refused TRAIL\n"
     "     move clears BreakevenTriggered again and the breakeven branch recomputes from ENTRY.\n"
     "     The enum, the field and all the plumbing stay -- so every test that checks the kind is\n"
     "     RECORDED still passes",
     '                        if (bracket.OutstandingStopMoveKind == ActiveBracket.StopMoveKind.Breakeven\n'
     '                            && bracket.BreakevenTriggered',
     '                        if (bracket.BreakevenTriggered'),

    (ATM,
     "the kind clause is INVERTED to Trail, so a refused BREAKEVEN move never retries -- which\n"
     "     is the case P0-67 was written for -- while a refused trail move loosens the stop",
     '                        if (bracket.OutstandingStopMoveKind == ActiveBracket.StopMoveKind.Breakeven\n'
     '                            && bracket.BreakevenTriggered',
     '                        if (bracket.OutstandingStopMoveKind == ActiveBracket.StopMoveKind.Trail\n'
     '                            && bracket.BreakevenTriggered'),

    (ATM,
     "the trailing call site claims to be a BREAKEVEN move. The kind is still recorded, still\n"
     "     read, still compared -- and it is a lie, so a refused trail move re-arms exactly as\n"
     "     it did at baseline. The defect returns with every mechanism intact",
     '                                RequestStopMove(account, bracket, newStop, "trailing stop advanced", ActiveBracket.StopMoveKind.Trail);',
     '                                RequestStopMove(account, bracket, newStop, "trailing stop advanced", ActiveBracket.StopMoveKind.Breakeven);'),

    # ---- group 5: what our own refusal costs ---------------------------------------------------
    (ATM,
     "our own refusal starts spending the provider-refusal budget, so three wrong-way requests\n"
     "     abandon a bracket whose stop is in perfect shape and ATM_STOP_MOVE_ABANDONED says the\n"
     "     position will not trail again -- about a position that is trailing correctly",
     '                        + $"wrong-way move to {newStopPrice}.");\n'
     '                    bracket.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;',
     '                        + $"wrong-way move to {newStopPrice}.");\n'
     '                    bracket.StopModifyAttempts++;\n'
     '                    bracket.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;'),

    (ATM,
     "the refused request is left OUTSTANDING, so RequestStopMove's in-flight check blocks\n"
     "     every later move for the life of the position. The stop is protected from being\n"
     "     loosened by never moving again, which is the failure this ticket also has to avoid",
     '                        + $"wrong-way move to {newStopPrice}.");\n'
     '                    bracket.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;',
     '                        + $"wrong-way move to {newStopPrice}.");\n'
     '                    bracket.RequestedStopPrice = newStopPrice;\n'
     '                    bracket.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;'),

]

ORIGINALS = {}
for target, _, _, _ in MUTANTS:
    if target not in ORIGINALS:
        # ⚠️ NO newline='' ON THE READ, and check_anchors.py enforces it. This battery was written
        # with it and the gate refused: the gate matches anchors against universal-newline text, so
        # a battery that searches CRLF text is being validated against a string it never looks for
        # -- the anchor reads "ok" and the mutant scores a SURVIVOR. The WRITE keeps newline='' so
        # the file is rewritten byte-for-byte as read. [[mutation-anchors-go-stale]].
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
    # try/finally as well as the encoding pin above: the pin closes the one failure that has
    # actually happened twice, the finally closes EVERY way of leaving the loop with a mutant
    # applied, including a KeyboardInterrupt.
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

# ⚠️ The PLAIN exit, not _battery.finish, and check_expected_survivors.py enforces the
# difference in both directions. This battery declares NO expected survivor: its one
# candidate was DELETED instead, because the arbiter finding it defended against was
# measured unreachable. Reaching for the helper without a declaration removes the prompt
# to justify the next exemption someone adds.
sys.exit(1 if survivors else 0)
