"""Mutation battery for P1-167, the remaining half: one refusal per order per rule.

`ExecuteOrderUpdate` runs once per order EVENT, and no rule inside it recorded that it had already
refused a given order. So the platform's state-transition count -- a quantity no rule controls and
the broker chooses -- multiplied every cancel and every log line. Measured on the funded account
2026-08-19: one 3-lot MNQ order against a cap of 1 drew THREE identical
`PER_INSTRUMENT_CAP_CANCEL` lines at 06:14:19, and `SHADOW_PENDING_CANCEL` reported 96 withheld
cancels against far fewer offending orders -- inflating the one number an operator would use to
judge how often the guard intervened. [[measure-the-deployed-system]]

⚠️ THIS ENTRY WAS "PARTIALLY FIXED" ONCE BEFORE, FOR THE RULE IT HAD JUST BEEN MEASURED ON.
`P0-171` closed it for `DUPLICATE_ENTRY` only. This closes the other four, which is what the entry
asked for in the first place: it is the METHOD's shape, not one rule's.
[[fix-the-class-not-the-instance]]

THE GROUPS BELOW:

  1. THE DE-DUPLICATION WORKS, AND IS NOT TOO COARSE. Both directions matter and the coarse one is
     fail-OPEN: de-duplicating by anything broader than (rule, order) silences refusals the guard
     should make.
  2. ⚠️ THE KEY IS THE OBJECT REFERENCE, NOT `Order.Id`. Provider31 issues the id as a submission
     GUID and REPLACES IT ON ACCEPT while the Simulator never does, so an id-keyed set is written
     under one key and read under another: it never matches on the operator's own provider and
     every test passes on Sim101. And NT8's ids are not unique, so two genuinely different orders
     can share one and the second would be silently skipped. [[the-simulator-re-ids-nothing]]
  3. EVERY RULE IN THE METHOD, and the null-state branch. A rule that cannot remember must still
     ENFORCE -- on a path that cancels orders, a silently dropped refusal is the direction that
     costs money.

EXPECTED SURVIVOR: one, in group 2 -- declared and explained at the mutant itself.
"""
import os, re, subprocess, sys

import _battery

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # ---- group 1: the de-duplication works, and is not too coarse -----------------------------
    (MODELS, 'group 1: MarkRefusedOnce always says "first time" -- P1-167 exactly as measured. One '
             'order draws one refusal per state transition, and the audit record is inflated by a '
             'factor the broker chooses',
     '            return seen.Add(order);',
     '            seen.Add(order);\n            return true;'),

    (MODELS, 'group 1: the set is shared across rules, so the FIRST rule to refuse an order '
             'silences every other rule for that order. The operator fixes the instrument, '
             'resubmits, and hits an unexplained cap refusal that was never reported the first '
             'time. Fail-OPEN, and it reads as a simplification',
     '            if (!RuleRefusedOrders.TryGetValue(ruleId, out seen))\n'
     '            {\n'
     '                seen = new HashSet<Order>(OrderReferenceComparer.Instance);\n'
     '                RuleRefusedOrders[ruleId] = seen;\n'
     '            }',
     '            if (!RuleRefusedOrders.TryGetValue("ALL", out seen))\n'
     '            {\n'
     '                seen = new HashSet<Order>(OrderReferenceComparer.Instance);\n'
     '                RuleRefusedOrders["ALL"] = seen;\n'
     '            }'),

    (MODELS, 'group 1: a null order SUPPRESSES the refusal instead of passing it through. Nothing '
             'to remember must never mean nothing to enforce, and this is the fail-CLOSED direction '
             'on a path that cancels orders',
     '            if (order == null) return true;   // nothing to remember; never suppress a refusal',
     '            if (order == null) return false;'),

    # ---- group 2: the key is the object reference ---------------------------------------------
    (MODELS, 'EXPECTED SURVIVOR: group 2 -- dropping the explicit comparer. THE SUITE CANNOT SEE '
             'THIS MOVE, AND SAYING SO IS THE POINT rather than an excuse. `new HashSet<Order>()` '
             'falls back to Object.Equals, and the TEST STUB Order overrides neither Equals nor '
             'GetHashCode -- so under the stub the default comparer IS reference equality and this '
             'mutant is genuinely equivalent. It is NOT equivalent against NinjaTrader own Order '
             'type, whose equality this repo neither controls nor can observe from here: if NT8 '
             'overrides Equals to compare ids, the set silently becomes id-keyed, Provider31 '
             'replaces the id on accept, the lookup never matches, and P1-167 is back on the live '
             'account behind a green suite. The explicit comparer is protection against a type the '
             'harness REPLACES, which is exactly the gap a test double leaves. '
             '[[test-doubles-are-not-evidence]]',
     '                seen = new HashSet<Order>(OrderReferenceComparer.Instance);\n'
     '                RuleRefusedOrders[ruleId] = seen;',
     '                seen = new HashSet<Order>();\n'
     '                RuleRefusedOrders[ruleId] = seen;'),

    (MODELS, 'group 2: the comparer is changed to compare Order.Id -- the same defect one layer '
             'down, and the half the suite CAN see. Two genuinely different orders sharing an id '
             'collide, so the second is silently skipped: a refusal the rule should have made and '
             'did not.\n'
             '             ⚠️ BOTH METHODS ARE MUTATED TOGETHER AND THAT IS THE FINDING. Changing '
             'Equals ALONE is a no-op: GetHashCode still returns the reference hash, two objects '
             'sharing an Id land in different buckets, and Equals is never called to notice. That '
             'version of this mutant SURVIVED, and reading it as a missing test would have been '
             'wrong -- an IEqualityComparer is only as keyed as its WEAKER half, so a half-mutation '
             'proves nothing and a half-FIX would have been just as invisible',
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

    # ---- group 3: every rule in the method, and the null-state branch -------------------------
    (GUARD, 'group 3: the per-instrument cap loses its de-duplication -- the rule the over-count '
            'was MEASURED on, three identical lines at 06:14:19',
     '                                if (instState == null || instState.MarkRefusedOnce("PER_INSTRUMENT_CAP_CANCEL", e.Order))',
     '                                if (true)'),

    (GUARD, 'group 3: the blacklist loses its de-duplication. This is the rule carrying the '
            'operator discipline contract -- every full-size future blocked -- so its audit line is '
            'the one they actually read',
     '                            if (!IsPositionReducingOrder(e.Order, instState)\n'
     '                                && (instState == null || instState.MarkRefusedOnce("BLACKLIST_CANCEL", e.Order)))',
     '                            if (!IsPositionReducingOrder(e.Order, instState))'),

    (GUARD, 'group 3: the lockout refusal loses its de-duplication -- the third rule with the same '
            'shape, and the one that fires most often because a lockout persists across events',
     # Re-anchored 2026-08-20: P2-162 routes this refusal through the `refuseRule` variable so a
     # cooldown refusal can share the block with a distinct rule id.
     '                                        if (stateModel.MarkRefusedOnce(refuseRule, e.Order))',
     '                                        if (true)'),

    (GUARD, 'group 3: the rate governor loses its de-duplication, so the tripping order is queued '
            'for cancel once per transition for as long as the window stays over its bound',
     '                                if (!IsPositionReducingOrder(e.Order, stateModel)\n'
     '                                    && stateModel.MarkRefusedOnce("ORDER_FLOOD_LOCKOUT", e.Order))',
     '                                if (!IsPositionReducingOrder(e.Order, stateModel))'),

    (GUARD, 'group 3: the cap FAILS CLOSED on an untracked account -- there is no state to remember '
            'the refusal in, so the refusal is dropped entirely. On a path that cancels orders in an '
            'over-cap instrument a silently dropped refusal is the direction that costs money, and '
            '`instState == null ||` reads like defensive noise until you ask WHICH WAY it fails',
     '                                if (instState == null || instState.MarkRefusedOnce("PER_INSTRUMENT_CAP_CANCEL", e.Order))',
     '                                if (instState != null && instState.MarkRefusedOnce("PER_INSTRUMENT_CAP_CANCEL", e.Order))'),

    (GUARD, 'group 3: the session reset stops clearing the sets, so order references from every past '
            'session accumulate for the life of the process -- a leak on a guard that runs for '
            'weeks, and one no test would notice because the refusals still work',
     '            stateModel.RuleRefusedOrders.Clear();',
     '            _ = stateModel.RuleRefusedOrders.Count;'),
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
# enforces the pairing in BOTH directions -- the day NT8's Order equality becomes observable from
# the harness, that declaration starts being KILLED and is reported STALE rather than passing
# quietly. Delete the marker in the same commit as the test that earns it.
_battery.finish(survivors, MUTANTS)
