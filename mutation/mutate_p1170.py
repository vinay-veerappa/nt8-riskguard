"""Mutation battery for P1-170: the daily-loss rail's input survives a recompile, and the first
tick afterwards is not a losing trade.

MEASURED on the funded account TAKEPROFITPRO524207503 on 2026-08-19, minutes after v1.51.0 was
deployed, read straight off nt_riskguard_inventory:

    { "name": "Daily loss limit", "configPath": "PnLRules.DailyLossLimit",
      "state": "EvaluatedNotEnforcing", "currentValue": 0, "limit": -250 }

currentValue 0 on an account that was down $347.75 -- breached by $96 and reporting a flat day. The
rule was enabled, was being evaluated, had the right limit, and was reading a number that said there
was nothing to enforce. [[configured-evaluated-enforcing]].

RealizedPnL is what every PnL rail reads and is the one number in its cluster that is not persisted;
LastRealizedPnL and SessionStartRealizedPnL both are, and RealizedPnL is exactly their difference at
every site in the addon that writes any of the three. The restore path had everything it needed and
reconstructed nothing. [[a-successful-compile-wipes-static-state]].

⚠️ IT DOES NOT MERELY UNDER-REPORT, IT FABRICATES A LOSS -- and that half is quieter and worse. Left
at 0.0, the next AccountItemUpdate computed its delta against zero and handed the whole session's
loss to RecordRealizedDelta as ONE losing trade. On the funded account ConsecutiveLosses went 16 ->
17 while TradesToday stayed 16, and that arithmetic impossibility -- a streak longer than the
session's trade count -- is the only reason any of this was visible.

WHY A BATTERY FOR ONE LINE OF ARITHMETIC. Because it is a SUBTRACTION and every number in the
measured case is negative, so the two most likely ways to write it wrong -- inverting the operands,
or dropping a term -- both reproduce something loss-shaped that a suite built around this ticket's
own figures can wave through. The two negative controls (a flat session, and a WINNING session) exist
for exactly that, and groups 1 and 2 are what prove they bind.

THE GROUPS BELOW:

  1. THE RECONSTRUCTION HAPPENS AT ALL, and is not quietly re-zeroed.
  2. IT IS THE RIGHT ARITHMETIC, IN THE RIGHT DIRECTION, FROM THE RIGHT TWO FIELDS.

EXPECTED SURVIVOR: one, in group 2 -- see its description. It is equivalent because the
reconstruction reads the PERSISTED RECORD rather than the live state object, which is a
deliberate choice that makes the line order-independent.
"""
import os, re, subprocess, sys

import _battery

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: it happens at all -----------------------------------------------------------
    (GUARD, 'group 1: the reconstruction is removed -- P1-170 restored exactly as measured, with '
            'the daily rail reading 0 on an account down $347 and the next tick fabricating a '
            'losing trade',
     '                                    state.RealizedPnL =\n'
     '                                        kvp.Value.LastRealizedPnL - kvp.Value.SessionStartRealizedPnL;',
     '                                    state.UnrealizedPnL = state.UnrealizedPnL;'),

    (GUARD, 'group 1: the line is present and assigns ZERO. Every source check that looks for an '
            'assignment to RealizedPnL in the restore path passes, and the behaviour is the defect. '
            'A regex cannot see a value -- [[a-source-gate-must-assert-the-condition]]',
     '                                    state.RealizedPnL =\n'
     '                                        kvp.Value.LastRealizedPnL - kvp.Value.SessionStartRealizedPnL;',
     '                                    state.RealizedPnL = 0.0;'),

    # ---- group 2: the right arithmetic, direction and operands --------------------------------
    (GUARD, 'group 2: the operands are inverted. Every number in the measured case is negative, so '
            'this still restores a loss-shaped value and only a WINNING session can see it -- which '
            'is the day nobody is looking at the daily-loss rail',
     '                                        kvp.Value.LastRealizedPnL - kvp.Value.SessionStartRealizedPnL;',
     '                                        kvp.Value.SessionStartRealizedPnL - kvp.Value.LastRealizedPnL;'),

    (GUARD, 'group 2: the subtrahend is dropped, so the SESSION total becomes the broker\'s '
            'ALL-TIME total. On an account carrying prior-session losses this locks a clean account '
            'out on its first evaluation after a recompile',
     '                                        kvp.Value.LastRealizedPnL - kvp.Value.SessionStartRealizedPnL;',
     '                                        kvp.Value.LastRealizedPnL;'),

    (GUARD, 'group 2: the wrong second field -- CumulativeRealizedPnL is banked PRIOR sessions, not '
            'this session\'s starting mark. It is the neighbouring persisted double and the one an '
            'autocomplete offers next',
     '                                        kvp.Value.LastRealizedPnL - kvp.Value.SessionStartRealizedPnL;',
     '                                        kvp.Value.LastRealizedPnL - kvp.Value.CumulativeRealizedPnL;'),

    (GUARD, 'EXPECTED SURVIVOR: reconstructed from the LIVE state object rather than the persisted record. '
            'EQUIVALENT, and the reason the real line reads kvp.Value instead. Both fields are '
            'assigned from kvp.Value immediately above, so state.X and kvp.Value.X are the same '
            'number at this point and no test can separate them. Reading the persisted record '
            'directly makes the reconstruction ORDER-INDEPENDENT: it cannot be broken by moving '
            'the two assignments below it, which is a hazard the state.X form would have and '
            'which no single mutant can demonstrate because it needs two edits. The design '
            'removes the hazard rather than testing for it -- so this mutant is kept to record '
            'that choice, not to score it',
     '                                    state.RealizedPnL =\n'
     '                                        kvp.Value.LastRealizedPnL - kvp.Value.SessionStartRealizedPnL;',
     '                                    state.RealizedPnL =\n'
     '                                        state.LastRealizedPnL - state.SessionStartRealizedPnL;'),

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

# Routed through _battery.finish because group 2 declares one EXPECTED SURVIVOR, and the helper
# enforces the pairing in BOTH directions -- a declaration that starts being KILLED is reported
# STALE rather than passing quietly, which is what would happen the day the reconstruction is
# changed to read the live state object.
_battery.finish(survivors, MUTANTS)
