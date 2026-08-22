"""Mutation battery for P2-132: the sizing rules report where they stand, and whether they fired.

Slice (a) shipped v1.62.0 with NO battery -- it rested on three suite tests. This battery covers
BOTH slices: the per-account cap's `state.Positions` source (slice a) and the aggregate cap's
cross-account SUM + the breach flag + the last-fired timestamp (slice b).

THE GROUPS:

  1. THE PER-ACCOUNT SOURCE (slice a). Neuter MaxPositionQuantity to a constant, or read the wrong
     field, and the per-account cap reports null/0 instead of the live position -- the exact defect
     slice (a) closed. The per-account tests die.

  2. THE AGGREGATE VALUE (slice b). Neuter TotalPositionQuantity, or AggregateNormalizedQuantity's
     per-account add, and the aggregate cap reports the wrong number. The value tests die.

  3. THE BREACH FLAG (slice b). Force the aggregate breach comparison constant or invert it; neuter
     the copier normalization so it uses the gross sum under ExpectedCopies > 1 (disagreeing with the
     enforcer); force the per-account flag false in the evaluator OR drop it at the population site;
     or swap the RESOLVED per-instrument limit for the flat default (the funded-account MNQ:1 defect).
     The breach tests -- including the negative control and the copies test -- die.

  4. THE LAST-FIRED TIMESTAMP (slice b). Drop the RecordRuleFired write (kills recency for every
     rule), drop the aggregate cap's RecordRuleFired call (the aggregate is not lockout-capable, so
     it is the only writer of ITS recency -- a green that can never be red), or neuter LastFiredOf.
     The fired-rule tests die.

⚠️ The negative control (under-limit is NOT breached) is load-bearing: a Breached flag that is true
whenever a limit exists passes every positive test. [[detector-needs-a-negative-test]]
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')

MUTANTS = [
    # ---- group 1: the per-account source (slice a) ------------------------------------------
    (GUARD, 'group 1: MaxPositionQuantity is forced to 0, so the per-account cap reports 0 instead '
            'of the live position -- slice (a) regressed; the per-account tests die',
     'snapshot.MaxPositionQuantity = maxPosQty;',
     'snapshot.MaxPositionQuantity = 0;'),

    (RULES, 'group 1: the per-account evaluator reads TotalPositionQuantity instead of '
            'MaxPositionQuantity, so a multi-instrument account reports the wrong number; the '
            'per-account tests die',
     'c.Account == null ? (double?)null : c.Account.MaxPositionQuantity',
     'c.Account == null ? (double?)null : c.Account.TotalPositionQuantity'),

    # ---- group 2: the aggregate sum (slice b) ------------------------------------------------
    (GUARD, 'group 2: TotalPositionQuantity is forced to 0, so the aggregate cap reports 0 instead '
            'of the cross-account sum; the sum tests die',
     'snapshot.TotalPositionQuantity = totalPosQty;',
     'snapshot.TotalPositionQuantity = 0;'),

    (RULES, 'group 2: AggregateNormalizedQuantity neuters its per-account add, so the aggregate cap '
            'reports 0 regardless of the accounts; the sum tests die',
     'total += a.TotalPositionQuantity;',
     'total += 0;'),

    # ---- group 3: the breach flag (slice b) --------------------------------------------------
    (RULES, 'group 3: the aggregate breach comparison is forced TRUE, so an under-limit value reads '
            'breached -- the negative control dies',
     'normalized > c.Config.Sizing.MaxContractsAggregate',
     'true'),

    (RULES, 'group 3: the aggregate breach comparison is INVERTED, so a breach reads healthy and an '
            'under-limit value reads breached -- both breach tests die',
     'normalized > c.Config.Sizing.MaxContractsAggregate',
     'normalized <= c.Config.Sizing.MaxContractsAggregate'),

    (RULES, 'group 3: the copier normalization is neutered -- the aggregate always uses the gross '
            'SUM, never the max single account, so under ExpectedCopies > 1 it disagrees with the '
            'enforcer; the copies test dies',
     'return copies > 1 ? maxSingle : total;',
     'return total;'),

    (RULES, 'group 3: the per-account breach flag is forced FALSE, so a breached position reads '
            'healthy in the evaluator; the per-account breach test dies',
     'c.Account != null && c.Account.MaxPositionQuantityBreached',
     'false'),

    (GUARD, 'group 3: the per-account breach flag is dropped at the POPULATION site, so the resolved '
            'per-instrument breach never reaches the snapshot; the population breach tests die',
     'snapshot.MaxPositionQuantityBreached = maxBreached;',
     'snapshot.MaxPositionQuantityBreached = false;'),

    (GUARD, 'group 3: the per-account breach uses the profile DEFAULT cap instead of the RESOLVED '
            'per-instrument limit, so a per-symbol InstrumentLimit below the account default is '
            'missed -- the funded-account MNQ:1 defect; the InstrumentLimit population test dies',
     'ResolveMaxContracts(resolvedProfile, baseSymbol, pos.Instrument)',
     'resolvedProfile.DefaultMaxContracts'),

    # ---- group 4: the last-fired timestamp (slice b) -----------------------------------------
    (GUARD, 'group 4: the recording write in RecordRuleFired is dropped, so no rule -- per-account '
            'OR aggregate -- ever records a firing; the fired-rule tests die',
     'st.RuleLastFired[ruleId] = st.UtcNow();',
     '/* dropped */'),

    (GUARD, 'group 4: the aggregate breach never calls RecordRuleFired, so the aggregate row reads '
            '"never fired" no matter how often it fires -- a green that can never be red; the '
            'aggregate-firing test dies',
     'RecordRuleFired(st, "AGGREGATE_SIZE_BREACH");',
     '/* dropped */'),

    (RULES, 'group 4: LastFiredOf returns null unconditionally, so a fired rule reports "never '
            'fired"; the fired-rule test dies',
     'return account.RuleLastFired.TryGetValue(ruleId, out t) ? (DateTime?)t : null;',
     'return null;'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


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
    result = m.group(0) if m else 'NO RESULT LINE'
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

print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
