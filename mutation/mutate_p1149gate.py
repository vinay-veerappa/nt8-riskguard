"""Mutation battery for P1-149 (strategy side): the contract cap, applied BEFORE the order exists.

The bridge/order paths were fixed in nt8-mcp-bridge (addons/BridgeSizingGate.cs). This battery is
the SAME decision for the other order origin: a RiskManagerBase strategy consulting RiskGatekeeper
on its entry gate. RiskGatekeeper.CanTradeSize delegates to the pure ContractCapGate, which is what
this battery mutates -- RiskGatekeeper.cs itself names NinjaTrader.Cbi types and no test build
compiles it (P2-27), so the decision has to live somewhere a test can EXECUTE it.

MEASURED 2026-08-18 with `Sizing.MaxContractsPerAccount: 10` live in the config:

    Sim101   sell 1000 MES  -> FILLED. -$1,213 slippage on the fill alone.
    FUNDED   sell  501 MES   -> REJECTED by the PROP FIRM, not by us:
             "Your maximum order quantity has been met... Limit: 60 Current: 501"

THE GROUPS:

  1. THE ANTI-TRAP RULE, the one that must never regress. A cap that refuses the order CLOSING an
     over-cap position manufactures the state it bans -- [[a-lockout-must-not-trap-you]]. The branch
     protects the PARTIAL reduction that leaves a still-over-cap position (long 50, Sell 30 leaves
     20 over a cap of 10): without it the VERDICT happens to stay allowed via a negative resulting,
     but the reported ResultingQuantity is wrong, so the number is what pins the branch.
  2. WHAT IS MEASURED. The check is on the RESULTING position, not the order quantity, because the
     guard's reactive MAX_SIZE_BREACH asks `pos.Quantity > limit`. Two halves that measure different
     things disagree about the same account, and the symptom is the guard flattening an order the
     strategy had just approved.
  3. AGREEING WITH THE GUARD. A cap of 0 is reported as "no per-account contract cap". A gate that
     enforces what the inventory calls OFF is worse than either behaviour alone.
  4. BOUNDARIES AND SIGNS. `Position.Quantity` is ABSOLUTE on NT8 -- P0-96 is the copier reading the
     SIGN and DOUBLING a follower's short behind 1311 green tests.

⚠️ A CRASH IS NOT AUTOMATICALLY A KILL (P2-148 / P1-153): the harness prints its result line LAST, so
an unhandled exception leaves 'NO RESULT LINE', which used to score as a kill unconditionally. The
shared _battery.is_kill only counts a crash if a `[FAIL]` printed first.

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(REPO, 'addons', 'ContractCapGate.cs')

MUTANTS = [
    # ---- group 1: the anti-trap rule --------------------------------------------------------
    (TARGET,
     'group 1: THE ANTI-TRAP RULE GOES AWAY (if (false)). A reducing order is no longer waved '
     'through, so the position it LEAVES is computed by the cap arithmetic instead: a partial '
     'Sell 30 against long 50 reports a resulting of -30+50... i.e. a nonsense magnitude, and the '
     'number an operator reads is wrong on the exact path that must never lock them in. '
     '[[a-lockout-must-not-trap-you]]',
     '            if (opposes && orderQuantity <= held)',
     '            if (false)'),

    (TARGET,
     'group 1: a reducing order reports the position it STARTED with rather than what it leaves, so '
     'a partial exit from long 50 says it leaves 50. The verdict stays right and the number the '
     'caller logs is wrong -- and the number is the half an operator reads',
     '                    ResultingQuantity = held - orderQuantity',
     '                    ResultingQuantity = held'),

    (TARGET,
     'group 1: the anti-trap rule moves BELOW the cap test, so it can no longer pre-empt it. '
     'Ordering is the whole of this rule: a branch that runs second never runs at all',
     '            if (opposes && orderQuantity <= held)\n'
     '            {\n'
     '                return new ContractCapDecision\n'
     '                {\n'
     '                    Allowed = true,\n'
     '                    ResultingQuantity = held - orderQuantity\n'
     '                };\n'
     '            }',
     '            if (opposes && orderQuantity <= held && maxContracts < 0)\n'
     '            {\n'
     '                return new ContractCapDecision\n'
     '                {\n'
     '                    Allowed = true,\n'
     '                    ResultingQuantity = held - orderQuantity\n'
     '                };\n'
     '            }'),

    # ---- group 2: what is measured ----------------------------------------------------------
    (TARGET,
     'group 2: the existing position stops counting, so only the ORDER is measured. Long 8 with a '
     'cap of 10 admits a Buy 5 that leaves 13, and MAX_SIZE_BREACH then flattens all 13 -- which '
     'reads to an operator as the guard flattening an order the strategy approved',
     '            int resulting = opposes ? orderQuantity - held : held + orderQuantity;',
     '            int resulting = orderQuantity;'),

    (TARGET,
     'group 2: a reversal is measured as if it only added, so long 8 + Sell 20 reads as 28 rather '
     'than a short 12. Over-refusing looks safe and is not: it refuses legal exits-plus-entries and '
     'teaches the operator the gate is wrong',
     '            int resulting = opposes ? orderQuantity - held : held + orderQuantity;',
     '            int resulting = held + orderQuantity;'),

    # ---- group 3: agreeing with the guard ---------------------------------------------------
    (TARGET,
     'group 3: a cap of ZERO becomes enforcing, so an account the guard reports as "no per-account '
     'contract cap" refuses every order. The inventory screen and the entry path then say opposite '
     'things about the same setting',
     '            if (maxContracts <= 0)',
     '            if (maxContracts < 0)'),

    # ---- group 4: boundaries and signs ------------------------------------------------------
    (TARGET,
     'group 4: the cap boundary becomes exclusive, so a position exactly AT the configured maximum '
     'is refused and the cap silently means one less than it says',
     '            if (resulting <= maxContracts)',
     '            if (resulting < maxContracts)'),

    (TARGET,
     'group 4: the position quantity is used SIGNED. P0-96 shape: -8 held makes a reducing Buy 5 '
     'read as a reversal and REFUSE the order that lowers exposure. That family of defect doubled a '
     'real follower short behind 1311 green tests. [[nt8-position-quantity-is-absolute]]',
     '            int held = positionQuantity < 0 ? -positionQuantity : positionQuantity;',
     '            int held = positionQuantity;'),

    (TARGET,
     'group 4: the direction test inverts, so an order on the SAME side as the position is treated '
     'as reducing. Adding to a position is then the thing that is never refused',
     '            bool opposes = !flat && (longNow != buying);',
     '            bool opposes = !flat && (longNow == buying);'),
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

# Plain exit rule, not _battery.finish: this battery declares no EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions.
if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
