"""Mutation battery for P1-133: the ATM manager looked its own legs up by an id the BROKER owns.

MEASURED LIVE on the funded 50K (TAKEPROFITPRO524207503, Provider31), 2026-08-16:

    nt_place_atm_order ->  stopOrderId: "f953ea2b50bb43759747e0cb6beab2cc"   <- a GUID
    nt_orders          ->  name "Stop_15bc730b", orderId: "613562531447"     <- the broker's id
    ATM_STOP_ORDER_NOT_FOUND x3, then ATM_STOP_MOVE_ABANDONED

NT8 assigns a GUID at submission and the broker REPLACES Order.OrderId once it accepts. The NT8
Simulator never re-ids anything, so breakeven and trailing worked on Sim101 and nowhere else.

⚠️ THIS BATTERY EXISTS BECAUSE A GREEN SUITE IS THE WEAKEST POSSIBLE EVIDENCE HERE. 2038 tests
were green while the defect was live, for exactly one reason: the stub handed out a stable GUID
per order. TradeCopierEngine.cs:4477 wrote that prediction down two years ago. So the mutants
below are aimed less at the fix than at the EVIDENCE for it -- group 1 asks whether the new tests
would still fail if the fix were undone, group 4 asks whether the stub still models a real broker.

⚠️ GROUP 3 IS THE ONE TO KNOW. The fix changed a method's SIGNATURE (an id in, a name in) and the
first attempt at this ticket changed the callee and not its caller. Four agent-loop rounds spent
themselves on that, with the identical 21 regressions each time, because the caller was outside
every editable region. A mutant that reverts just the caller restores the whole defect while
AtmOrderIdentity sits there fully tested.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

IDENT = os.path.join(REPO, 'addons', 'AtmOrderIdentity.cs')
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')
STUB = os.path.join(REPO, 'tests', 'TestingStubs.cs')
TESTS = os.path.join(REPO, 'tests', 'RiskGuardAddOnTests.cs')

MUTANTS = [
    # ---- group 1: the identity itself ---------------------------------------------------------
    (IDENT,
     "⚠️ THE DEFECT, RESTORED IN ONE LINE: the match goes back to Order.OrderId. Everything\n"
     "     else about the fix stays -- the class, the name builders, the five call sites -- and\n"
     "     the feature is dead again on every real connection",
     '            return string.Equals(order.Name, name, StringComparison.Ordinal);',
     '            return string.Equals(order.OrderId, name, StringComparison.Ordinal);'),

    (IDENT,
     "a BLANK name matches everything instead of nothing, so a bracket with an unset id\n"
     "     resolves to the FIRST order on the account. On the funded 50K that is somebody else's\n"
     "     working order, and this class MOVES what it finds",
     '            if (order == null || string.IsNullOrWhiteSpace(name)) return false;',
     '            if (order == null) return false;\n'
     '            if (string.IsNullOrWhiteSpace(name)) return true;'),

    (IDENT,
     "the comparison goes case-insensitive. These names are constructed by this file, so a\n"
     "     case-insensitive match can only ever ADMIT something that is not ours",
     '            return string.Equals(order.Name, name, StringComparison.Ordinal);',
     '            return string.Equals(order.Name, name, StringComparison.OrdinalIgnoreCase);'),

    (IDENT,
     "the two finders stop being distinguishable: FindLiveByName drops its liveness test, so\n"
     "     a FILLED or CANCELLED stop is returned as the live one and P1-130's whole\n"
     "     absent-vs-terminal distinction collapses",
     '                if (NameMatches(order, name) && RiskGuardAddOn.OccupiesSlot(order.OrderState))\n'
     '                    return order;',
     '                if (NameMatches(order, name))\n'
     '                    return order;'),

    (IDENT,
     "liveness becomes a hand-rolled list again -- Working only -- which is P1-130 verbatim,\n"
     "     and P1-131 in the bridge, and the reason OccupiesSlot is shared in the first place",
     '                if (NameMatches(order, name) && RiskGuardAddOn.OccupiesSlot(order.OrderState))',
     '                if (NameMatches(order, name) && order.OrderState == OrderState.Working)'),

    # ---- group 2: the names, which must agree with what the placer wrote -----------------------
    (IDENT,
     "the stop's name gains a separator the placer does not use, so the lookup and the\n"
     "     placement disagree by one character and nothing is ever found. This is the failure the\n"
     "     ONE-definition class exists to make impossible",
     '            return "Stop_" + bracketId;',
     '            return "Stop-" + bracketId;'),

    (IDENT,
     "the entry and stop names collide. Both legs then resolve to whichever comes first in\n"
     "     account.Orders, so a breakeven move can be applied to the ENTRY order",
     '            return "AtmEntry_" + bracketId;',
     '            return "Stop_" + bracketId;'),

    # ---- group 3: the wiring, and the caller that beat four agent-loop rounds -------------------
    (ATM,
     "⚠️ THE CALLER REVERTS ALONE: RequestStopMove goes back to passing bracket.StopOrderId --\n"
     "     the submission GUID -- into a ModifyStopPrice that now wants a NAME. The whole defect\n"
     "     is back while AtmOrderIdentity remains fully tested and every one of its own tests\n"
     "     passes. This is the exact shape that cost four loop rounds",
     '            if (!ModifyStopPrice(account, AtmOrderIdentity.StopName(bracket.BracketId), newStopPrice))',
     '            if (!ModifyStopPrice(account, bracket.StopOrderId, newStopPrice))'),

    (ATM,
     "the RECONCILER alone reverts to the stale id. The writer still moves the stop, so\n"
     "     breakeven appears to work -- but nothing ever reads back what the broker did, and\n"
     "     CurrentStopPrice silently becomes this monitor's wish again. That is P0-67 restored",
     '            Order live = AtmOrderIdentity.FindLiveByName(account, stopName);',
     '            Order live = null;\n'
     '            foreach (Order o in account.Orders)\n'
     '                if (o.OrderId == bracket.StopOrderId && RiskGuardAddOn.OccupiesSlot(o.OrderState)) { live = o; break; }'),

    (ATM,
     "the ENTRY-liveness check alone reverts. It fails toward FORGETTING: a resting entry\n"
     "     matches nothing, the bracket is discarded while flat, and the fill that follows is\n"
     "     managed by nobody",
     '                            AtmOrderIdentity.NameMatches(o, AtmOrderIdentity.EntryName(bracket.BracketId)) &&',
     '                            o.OrderId == bracket.EntryOrderId &&'),

    (ATM,
     "the PLACER writes a name the lookups do not build, by concatenating in place again.\n"
     "     Every leg is then unfindable from the instant it is created -- the drift the single\n"
     "     definition exists to prevent",
     '                var stopOrder = account.CreateOrder(instrument, exitAction, OrderType.StopMarket, TimeInForce.Day, calculatedQty, 0, stopPrice, ocoId, AtmOrderIdentity.StopName(bracketId), null);',
     '                var stopOrder = account.CreateOrder(instrument, exitAction, OrderType.StopMarket, TimeInForce.Day, calculatedQty, 0, stopPrice, ocoId, "StopOrder_" + bracketId, null);'),

    (ATM,
     "the DIAGNOSTIC lookup reverts to the id, so a stop that is present but terminal is\n"
     "     reported as absent entirely. P1-130 separated those two messages precisely because a\n"
     "     risk surface that cries naked at a protected position trains the operator to discount\n"
     "     the line that will one day be true",
     '                Order present = AtmOrderIdentity.FindByName(account, orderName);',
     '                Order present = null;\n'
     '                foreach (Order o in account.Orders) if (o.OrderId == orderName) { present = o; break; }'),

    # ---- group 4: the EVIDENCE -- does the stub still model a real broker? ----------------------
    (STUB,
     "⚠️ THE STUB STOPS RE-IDING. Order.OrderId becomes settable-but-ignored, so every test\n"
     "     goes back to modelling the ONE broker whose behaviour is not the product. If this\n"
     "     survives, the suite has quietly reverted to the state that hid this defect for two\n"
     "     years and no future reader would know",
     '        public string OrderId { get; set; }',
     '        private string _oid; public string OrderId { get { return _oid ?? "STABLE-GUID"; } set { } }'),

    (TESTS,
     "the re-id helper becomes a no-op while still being CALLED, so all three P1-133 tests\n"
     "     read as if they drive a broker re-id and drive nothing. A test that names a hazard it\n"
     "     does not exercise is worse than no test, because it closes the question",
     '            order.OrderId = brokerId;',
     '            if (brokerId == null) order.OrderId = brokerId;'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


def run():
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'tests/RiskGuardTests.csproj', '--nologo', '-v', 'q'],
        cwd=REPO, capture_output=True, text=True,
        encoding='utf-8', errors='replace')
    if 'error CS' in (res.stdout + res.stderr):
        return 'BUILD FAILED'
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    return m.group(0) if m else 'NO RESULT LINE'


print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print('\nREFUSING TO RUN: baseline is RED (%s failing).' % m.group(2))
    sys.exit(2)

survivors = []

for target, name, old, new in MUTANTS:
    original = ORIGINALS[target]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    restore()

restore()
print('\nrestored originals;', run())

print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
