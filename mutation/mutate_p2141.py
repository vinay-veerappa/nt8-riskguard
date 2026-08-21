"""Mutation battery for P2-141: a breakeven config that cannot be honoured is refused.

Breakeven fires once price has travelled `BreakevenTriggerTicks` (`ShouldTriggerBreakeven`) and
places the stop at `entry + BreakevenOffsetTicks * tickSize` (`CalculateBreakevenStopPrice`). For a
long, that stop is at or ABOVE the market whenever `offset >= trigger`, so a sell-stop there is
invalid and the provider holds the old price -- permanently, for the life of the position.

MEASURED LIVE on the funded account `TAKEPROFITPRO524207503` (Provider31), bracket `302e7759`,
placed with trigger 1 / offset 2 -- values `nt_place_atm_order` accepted without comment:

    19:06:20  ATM_STOP_MOVE_REQUESTED   stop 30067 -> 30077.5   (ABOVE the price that triggered it)
    19:06:25  ATM_STOP_CHANGE_IGNORED   provider holds 30067 (attempt 1 of 3)
    19:06:40  ATM_STOP_MOVE_ABANDONED   3 stop moves failed ... The stop is still at 30067

Twenty seconds from fill to a permanently abandoned stop on a healthy winning position.

THE GROUPS BELOW:

  1. THE BOUNDARY. `>` instead of `>=` leaves `offset == trigger` live -- a stop exactly at the
     market, which is not a valid resting stop. This is the off-by-one the ticket most expected to
     be got wrong, so it gets its own mutant and its own test.
  2. ⚠️ THE OPPOSITE DIRECTION. A validator that refuses everything passes every refusal test ever
     written for it ([[a-detector-needs-a-negative-test]]). These mutants must die on the two
     ACCEPT controls, not on the refusals.
  3. WHERE THE REFUSAL SITS. A refusal that computes correctly and then lets the orders go out is
     worse than no refusal: it reports failure while the bracket is live
     ([[report-the-outcome-not-the-call]]).
  4. WHAT THE REFUSAL SAYS. "Invalid breakeven configuration" sends the operator to read source to
     find out which of two knobs to turn. Both numbers, and which is which, or it is not an answer.
  5. THE AUDIT ROW'S SUBJECT. `LogFromComponent`'s first parameter is the ACCOUNT. The loop's
     candidate passed the component name there, which files the row against an account that does
     not exist.
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')

MUTANTS = [
    # ---- group 1: the boundary --------------------------------------------------------------
    (ATM, 'group 1: the comparison becomes `>`, so an offset EXACTLY at the trigger is accepted '
          'and the breakeven stop rests exactly at the market -- the off-by-one this defect turns on',
     '            if (breakevenOffsetTicks >= breakevenTriggerTicks)',
     '            if (breakevenOffsetTicks > breakevenTriggerTicks)'),

    # ---- group 2: the opposite direction ----------------------------------------------------
    (ATM, 'group 2: the comparison is inverted, so every PLACEABLE config is refused and the '
          'default 12/2 stops working -- a validator that refuses everything passes every refusal '
          'test ever written for it',
     '            if (breakevenOffsetTicks >= breakevenTriggerTicks)',
     '            if (breakevenOffsetTicks <= breakevenTriggerTicks)'),

    (ATM, 'group 2: the validator never refuses anything, which is the state the defect was '
          'FOUND in -- it must not be reachable by deleting one line',
     '            if (breakevenOffsetTicks >= breakevenTriggerTicks)',
     '            if (false)'),

    # ---- group 3: where the refusal sits ----------------------------------------------------
    (ATM, 'group 3: the refusal is computed, logged and recorded on the result -- and then the '
          'method CARRIES ON and submits the bracket anyway. A gate that is COMPUTED is not a gate '
          'that is USED, which has beaten four source checks in this project',
     '                result.Status = "error";\n'
     '                result.Error = breakevenRefusal;\n'
     '                return result;',
     '                result.Status = "error";\n'
     '                result.Error = breakevenRefusal;'),

    (ATM, 'group 3: the refusal stops setting an error STATUS, so the caller reads a bracket that '
          'was never placed as one that was -- the quiet failure, not the loud one',
     '                result.Status = "error";\n'
     '                result.Error = breakevenRefusal;',
     '                result.Error = breakevenRefusal;'),

    # ---- group 4: what the refusal says ----------------------------------------------------
    (ATM, 'group 4: the message names only the offset, so the operator cannot tell which of two '
          'knobs to turn without reading source',
     '                    breakevenOffsetTicks,\n'
     '                    breakevenTriggerTicks);',
     '                    breakevenOffsetTicks,\n'
     '                    breakevenOffsetTicks);'),

    (ATM, 'group 4: the message loses the word "trigger", so a text search by an operator who was '
          'told which knob to turn finds nothing',
     'must be less than breakevenTriggerTicks ({1})',
     'must be less than the other value ({1})'),

    # ---- group 5: the audit row's subject ---------------------------------------------------
    (ATM, 'EXPECTED SURVIVOR: the audit row is filed against the COMPONENT name instead '
          'of the account, which is what the loop candidate did and what the hand review caught. '
          'UNREACHABLE BY TEST: RiskGuardAddOn.LogFromComponent is a no-op when Instance is null '
          'and the ATM tests clear it, so nothing logged from here is observable from the harness '
          '-- the same reason cited by the reconciler tests. Kept because the DEFECT is real: '
          'LogFromComponent(string account, ...) takes an account first, and a row naming a '
          'component is a row about an account that does not exist.',
     '                RiskGuardAddOn.LogFromComponent(account != null ? account.Name : "", "ATM_BRACKET_REFUSED",',
     '                RiskGuardAddOn.LogFromComponent("DynamicAtmManager", "ATM_BRACKET_REFUSED",'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # ⚠️ The encoding is PINNED. Without it the write uses the platform default (cp1252 here) and
    # raises part-way through on any non-ASCII byte, leaving a MUTANT on disk while the battery
    # reports having restored. [[a-battery-must-reach-its-restore-line]].
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

    # P2-148: a crash is not a detection. The harness prints its result line last, so any unhandled
    # exception leaves 'NO RESULT LINE' -- which scores as KILLED whether or not anything objected.
    # P1-153 made a throwing test print [FAIL] and carry on, so this now separates the two cases.
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

# Routed through _battery.finish because the group 5 mutant declares itself an EXPECTED
# SURVIVOR. tools/check_expected_survivors.py enforces the pairing in BOTH directions, and
# finish() reports a declaration that has started being KILLED as STALE rather than letting it
# pass quietly -- which is how an exemption rots into a free pass.
_battery.finish(survivors, MUTANTS)
