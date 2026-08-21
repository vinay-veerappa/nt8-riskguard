"""Mutation battery for P1-151: the AutoStop policy decided 2026-08-20.

The operator settled the StopGuard question: OnMissing is AutoStop (never flatten a manual entry),
the attached stop is ~5 basis points of the entry price on ANY instrument (price-relative, not a
fixed tick count), and a Flatten penalty -- if anyone chooses it -- must carry a deadline past
manual hand speed, refused at preflight (c3). The pricing is a pure static (ComputeAutoStopOffsetTicks)
so it is unit-testable; these mutants move the bps arithmetic, the floor, the override precedence,
the preflight guard and the two shipped defaults.

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # ---- the bps arithmetic (ComputeAutoStopOffsetTicks) --------------------------------------
    (GUARD, 'the bps divisor becomes 1000 instead of 10000, so every AutoStop is 10x too wide -- '
            '50 bps, not 5. A stop an order of magnitude away is a catastrophe stop the operator '
            'never chose',
     'double distance = avgPrice * (bps / 10000.0);',
     'double distance = avgPrice * (bps / 1000.0);'),

    (GUARD, 'the tick conversion multiplies instead of divides, so the offset scales with tick '
            'size the wrong way and the 5 bps distance is meaningless',
     'int t = (int)Math.Round(distance / tickSize, MidpointRounding.AwayFromZero);',
     'int t = (int)Math.Round(distance * tickSize, MidpointRounding.AwayFromZero);'),

    (GUARD, 'the one-tick floor is removed, so a sub-tick bps distance rounds to ZERO -- a stop at '
            'the entry price, which is no stop at all and would reject or fill instantly',
     'return t < 1 ? 1 : t;',
     'return t;'),

    (GUARD, 'a zero/unset StopDistanceBps stops falling back to 5 and is taken literally, so a '
            'missing setting yields a zero-distance stop -- the direction a missing setting must '
            'never fail',
     'double bps = (sg != null && sg.StopDistanceBps > 0.0) ? sg.StopDistanceBps : 5.0;',
     'double bps = (sg != null && sg.StopDistanceBps > 0.0) ? sg.StopDistanceBps : 0.0;'),

    (GUARD, 'the per-instrument override lookup is dropped, so an explicit Offsets entry is ignored '
            'and the escape hatch silently does nothing',
     'if (sg != null && sg.Offsets != null && sg.Offsets.TryGetValue(symbolName, out ticks))\n'
     '                return ticks;',
     'if (false && sg != null && sg.Offsets != null && sg.Offsets.TryGetValue(symbolName, out ticks))\n'
     '                return ticks;'),

    # ---- the c3 preflight guard (a Flatten penalty needs a safe deadline) ---------------------
    (GUARD, 'the Flatten-deadline preflight guard is disarmed (< 15 becomes < 0), so Flatten paired '
            'with the short AutoStop-era default is armed and flattens a manual entry on a normal '
            'day -- the original P1-84 danger, reopened by the shorter default',
     'if (onMissing == "Flatten" && _config.StopGuard != null && _config.StopGuard.StopAttachSeconds < 15)',
     'if (onMissing == "Flatten" && _config.StopGuard != null && _config.StopGuard.StopAttachSeconds < 0)'),

    (GUARD, 'the c3 guard reads AutoStop instead of Flatten, so it refuses the safe default and '
            'waves through the dangerous Flatten pairing -- both failure directions at once',
     'if (onMissing == "Flatten" && _config.StopGuard != null && _config.StopGuard.StopAttachSeconds < 15)',
     'if (onMissing == "AutoStop" && _config.StopGuard != null && _config.StopGuard.StopAttachSeconds < 15)'),

    # ---- the two shipped defaults (RiskGuardModels.cs) ----------------------------------------
    (MODELS, 'the default action reverts to Flatten -- the decision the operator explicitly '
             'reversed, and the one that flattens their own manual entries',
     'public string OnMissing { get; set; } = "AutoStop"; // "AutoStop", "Flatten"',
     'public string OnMissing { get; set; } = "Flatten"; // "AutoStop", "Flatten"'),

    (MODELS, 'the default AutoStop distance is halved to 2.5 bps -- a tighter stop than decided, so '
             'the guard takes the operator out on ordinary noise. Pins the exact 5.0',
     'public double StopDistanceBps { get; set; } = 5.0;',
     'public double StopDistanceBps { get; set; } = 2.5;'),
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
    restore()

print(chr(10) + 'restored originals;', run())

if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
