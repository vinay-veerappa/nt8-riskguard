"""Mutation battery for P2-161 (the escalating loss cooldown) and P2-162 (refuse the entry rather
than flatten the fill), plus P2-164's loss-floor input to the streak.

P2-161 replaced a cool-off that fired ONCE at the consecutive-loss limit -- so losses 1..N-1 cost
nothing and the one it set was subsumed by the 60-minute lockout on the same tick -- with a ladder:
each loss below the cap arms base * 2^(n-1) minutes, the cap is the hard lockout, and a WIN resets
the escalation to the base (not merely the counter). The durations are the whole point, so the
mutants below move the exponent, the boundary and the base; a test that only checks "a cooldown was
set" survives every one of them.

P2-162 makes a running cooldown REFUSE an entry in ExecuteOrderUpdate, mirroring the lockout's
ENTRY_CANCEL, instead of letting it fill and flattening it in EvaluateRules. The flatten stays as a
backstop for a position that already exists. The refusal is logged as COOLDOWN_CANCEL so the audit
names the cause and the de-dup key is distinct from ENTRY_CANCEL.

P2-164 is the loss definition: a net loss must clear LossFloorDollars to count; default 0 counts
every negative, matching today's semantics.

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # ---- P2-161: the ladder's arithmetic (RiskGuardModels.cs) ---------------------------------
    (MODELS, 'P2-161: the exponent loses its -1, so every rung is doubled -- loss 1 pays the loss-2 '
             'pause. This is the exact off-by-one the filed entry warned is invisible to a test that '
             'only asserts a cooldown was set',
     'int exponent = Math.Min(ConsecutiveLosses - 1, 20);',
     'int exponent = Math.Min(ConsecutiveLosses, 20);'),

    (MODELS, 'P2-161: the exponent is pinned to 0, so the ladder flattens back into a single fixed '
             'pause -- the defect P2-161 exists to remove, wearing the new code',
     'int exponent = Math.Min(ConsecutiveLosses - 1, 20);',
     'int exponent = Math.Min(0, 20);'),

    (MODELS, 'P2-161: the base multiply becomes zero, so every pause is now+0 -- a cooldown that '
             'expires the instant it is set is no cooldown at all',
     'long pause = (long)config.Overtrading.CooldownMinutes * (1L << exponent);',
     'long pause = (long)config.Overtrading.CooldownMinutes * (0L << exponent);'),

    (MODELS, 'P2-161: the lower bound moves to > 1, so the FIRST loss arms no cooldown -- losses '
             '1..N-1 costing nothing is the original defect',
     '                && ConsecutiveLosses >= 1',
     '                && ConsecutiveLosses > 1'),

    (MODELS, 'P2-161: the upper bound becomes <=, so the ladder ALSO fires at the cap, laying a '
             'cooldown deadline over the CONSECUTIVE_LOSS_BREACH lockout that owns loss N -- two '
             'overlapping deadlines and an ambiguous audit',
     '                && ConsecutiveLosses < config.Overtrading.MaxConsecutiveLosses)',
     '                && ConsecutiveLosses <= config.Overtrading.MaxConsecutiveLosses)'),

    # ---- P2-164: the loss floor (RiskGuardModels.cs) ------------------------------------------
    (MODELS, 'P2-164: the loss floor is ignored and the threshold collapses to the float-noise '
             'epsilon, so a sub-floor scratch counts as a loss again -- the three-dollar scratches '
             'that locked the funded account out on 2026-08-18',
     'double lossThreshold = -(lossFloor > 0.01 ? lossFloor : 0.01);',
     'double lossThreshold = -(0.01);'),

    # ---- P2-162: refuse the entry during a cooldown (RiskGuardAddOn.cs) ------------------------
    (GUARD, 'P2-162 UNDONE: the cooldown drops out of the refusal condition, so an entry placed '
            'during a cooldown is no longer cancelled -- it fills and is flattened in EvaluateRules '
            'at a commission and slippage, which is exactly the defect',
     'if (entryLockoutBinds || streakAtCap || cooldownActive)',
     'if (entryLockoutBinds || streakAtCap)'),

    (GUARD, 'P2-162: the cooldown window is inverted, so entries are refused when NO cooldown is '
            'running and waved through during one -- the refusal fires on the wrong half of the '
            'clock. The negative control (no cooldown -> untouched) is what catches this',
     'bool cooldownActive = DateTime.UtcNow < stateModel.CooldownUntil;',
     'bool cooldownActive = DateTime.UtcNow > stateModel.CooldownUntil;'),

    (GUARD, 'P2-162: the cooldown refusal is logged as ENTRY_CANCEL, so the audit misattributes it '
            'to the lockout and -- worse -- it de-duplicates against a real lockout refusal on the '
            'same order, suppressing one of two distinct refusals [[a-second-reader-of-the-same-state]]',
     '                                            ? "ENTRY_CANCEL" : "COOLDOWN_CANCEL";',
     '                                            ? "ENTRY_CANCEL" : "ENTRY_CANCEL";'),
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
            mm = re.search(r'Failed = (\d+)', res)
            undetected_crash = 'NO ASSERTION FAILED' in res
            killed = (not undetected_crash) and (
                ('BUILD FAILED' in res) or ('NO RESULT LINE' in res)
                or (mm is not None and int(mm.group(1)) > 0))
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
