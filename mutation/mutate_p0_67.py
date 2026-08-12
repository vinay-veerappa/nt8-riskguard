"""Mutation battery for P0-67 (the THIRD Account.Change() site cached a refused price).

Every mutant here reinstates a piece of the original defect, so each one must turn
the suite red. The three tests being pinned were written the same day as the fix and
had never been watched to fail -- and in this case the risk was higher than usual,
because `MonitorTickCore` had ZERO test coverage before them. A fix to code nothing
executed, verified by tests written alongside it, is two unchecked claims stacked.

The first mutant is the defect verbatim: write the requested price into the cache.
If that survives, the tests are decorative.

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')

MUTANTS = [
    # ---- the defect itself ----
    ("the cache records the REQUESTED price again, exactly as it did before the fix",
     '            bracket.CurrentStopPrice = brokerPrice;',
     '            bracket.CurrentStopPrice = double.IsNaN(requested) ? brokerPrice : requested;'),
    # NOTE: the first version of this mutant read bracket.RequestedStopPrice, which the
    # reconcile has already reset to NaN by this line -- so it was a no-op and SURVIVED,
    # which read as "the tests do not catch the original defect". They do. A mutant that
    # cannot change behaviour is a broken mutant, and it is indistinguishable from a
    # missing test until you check. Use the local `requested`.

    ("the cache is never updated at all, so trailing can never advance",
     '            bracket.CurrentStopPrice = brokerPrice;',
     ''),

    # ---- the detection ----
    ("a refused move is treated as honoured (the comparison always says 'it took')",
     '                if (Math.Abs(brokerPrice - requested) <= 1e-9)',
     '                if (true)'),

    ("a honoured move is treated as refused, so a working trail is abandoned as broken",
     '                if (Math.Abs(brokerPrice - requested) <= 1e-9)',
     '                if (false)'),

    # ---- the recovery ----
    ("breakeven is never re-armed, so the trail stays latched on an honest cache",
     '                    if (bracket.BreakevenTriggered && bracket.StopModifyAttempts < MaxStopModifyAttempts)\n                        bracket.BreakevenTriggered = false;',
     '                    if (false)\n                        bracket.BreakevenTriggered = false;'),

    ("the refusal counter never increments, so the retry is unbounded -- an order flood",
     '                    bracket.StopModifyAttempts++;',
     ''),

    ("the attempt cap never fires, same flood by the other route",
     '            if (bracket.StopModifyAttempts >= MaxStopModifyAttempts)',
     '            if (false)'),

    # ---- the reconcile has to actually run ----
    ("the sweep stops reconciling against the broker before deciding",
     '                    ReconcileStopFromBroker(account, bracket);',
     ''),

    ("ModifyStopPrice reports success even when no working stop order exists",
     '                RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_ORDER_NOT_FOUND",',
     '                if (true) return true;\n                RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_ORDER_NOT_FOUND",'),

    # ---- the in-flight reservation, found by the trail test rather than by reading ----
    ("two Change() calls can land on one stop order in a single sweep again -- which per P0-61 "
     "reverts the order and loses both",
     '            if (!double.IsNaN(bracket.RequestedStopPrice))',
     '            if (false)'),
]


def run():
    b = subprocess.run(['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    if 'Build succeeded' not in b.stdout:
        return 'BUILD FAILED'
    r = subprocess.run(['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith('RESULTS:'):
            return line.strip()
    return 'NO RESULT LINE'


original = open(ATM, encoding='utf-8').read()
print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print(f'\nREFUSING TO RUN: baseline is RED ({m.group(2)} failing). Every mutant would '
          'score KILLED on pre-existing failures and this battery would prove nothing.')
    sys.exit(2)

survivors = []
for name, old, new in MUTANTS:
    if original.count(old) != 1:
        print(f'  [SKIP] {name}: anchor matched {original.count(old)} times')
        survivors.append(name + ' (ANCHOR)')
        continue
    open(ATM, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    # A crash is a kill: the mutation stopped the suite completing.
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
    if not killed:
        survivors.append(name)

open(ATM, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
