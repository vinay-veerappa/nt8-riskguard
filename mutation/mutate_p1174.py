"""Mutation battery for P1-174: the peak-giveback rail's per-position state survives a recompile.

`PeakOpenGain`, `PeakGivebackTriggered` and `PeakGivebackLastTriggerUnrealized` are the
peak-giveback rule's working state and none was persisted. A recompile set the peak to `0.0`, and
the rule's next evaluation found `UnrealizedPnL > 0` and RE-BASELINED the peak to the CURRENT
unrealized -- so the giveback was measured from a lower high and fired late or not at all, for as
long as that position stayed open.

⚠️ THE RULE ALREADY SET `_stateDirty = true` FOR ALL THREE, on both branches: the flag that
schedules a state write, for fields the writer did not carry. A write to nowhere. That is better
evidence than any argument about whether persisting is worthwhile, and it is why this was filed
rather than left in the gate's unreviewed baseline.

Third instance of `P1-170`'s class, found by `tools/check_account_state_persisted.py` -- the gate
written for the first one. This entry empties that gate's baseline.

THE GROUPS BELOW:

  1. THE THREE FIELDS ARE PERSISTED AND RESTORED. Losing any one of them is a different defect:
     the peak is the measurement, the latch is what stops a giveback being acted on twice, and the
     sentinel is what "has not triggered" means.
  2. ⚠️ THE NaN ROUND-TRIP. JSON HAS NO NaN LITERAL. The live field uses NaN for "has not
     triggered"; a state file written before this field existed deserializes 0.0, and 0.0 is a
     LEGITIMATE trigger level. Restoring it raw invents a trigger at breakeven for every existing
     account on first load. This group is the one that would ship silently.
  3. THE STALE-PEAK BOUND HOLDS. A peak belonging to a position that closed while the guard was
     down must be discarded the moment the account reads flat, or the giveback fires EARLY on the
     next position. That is the only direction in which this fix can hurt the operator.

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
# [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: all three are persisted and restored --------------------------------------
    (GUARD, 'group 1: the PEAK is not restored -- P1-174 exactly as measured. The next evaluation '
            're-baselines it to the current unrealized and the giveback is measured from a lower '
            'high, for as long as the position stays open',
     '                                    state.PeakOpenGain = kvp.Value.PeakOpenGain;',
     '                                    _ = kvp.Value.PeakOpenGain;'),

    (GUARD, 'group 1: the LATCH is not restored, so a giveback already acted on is acted on again '
            'after a recompile. The peak survives and the protection double-fires -- a second '
            'intervention on a position the operator has already been trimmed out of',
     '                                    state.PeakGivebackTriggered = kvp.Value.PeakGivebackTriggered;',
     '                                    _ = kvp.Value.PeakGivebackTriggered;'),

    (GUARD, 'group 1: the SAVE stops writing the peak, so the restore reads a default. The restore '
            'line is present, the DTO field exists, and every source check for either passes',
     '                            PeakOpenGain = state.PeakOpenGain,   // P1-174',
     '                            PeakOpenGain = 0.0,   // P1-174'),

    # ---- group 2: the NaN round-trip --------------------------------------------------------
    (GUARD, 'group 2: the sentinel is restored RAW. JSON has no NaN literal, so every state file '
            'that predates this field deserializes 0.0 -- a LEGITIMATE trigger level -- and the '
            'guard comes up believing the giveback already fired at breakeven on every account it '
            'tracks. This is the mutant that would ship silently: it needs no new code path, only '
            'the absence of one line of normalisation',
     '                                    state.PeakGivebackLastTriggerUnrealized =\n'
     '                                        kvp.Value.PeakGivebackLastTriggerUnrealized == 0.0\n'
     '                                            ? double.NaN\n'
     '                                            : kvp.Value.PeakGivebackLastTriggerUnrealized;',
     '                                    state.PeakGivebackLastTriggerUnrealized =\n'
     '                                        kvp.Value.PeakGivebackLastTriggerUnrealized;'),

    (GUARD, 'group 2: the normalisation is inverted -- a real trigger level is thrown away and only '
            'the absent case is kept. The mirror image, and it reads almost identically',
     '                                        kvp.Value.PeakGivebackLastTriggerUnrealized == 0.0\n'
     '                                            ? double.NaN\n'
     '                                            : kvp.Value.PeakGivebackLastTriggerUnrealized;',
     '                                        double.IsNaN(kvp.Value.PeakGivebackLastTriggerUnrealized)\n'
     '                                            ? 0.0\n'
     '                                            : double.NaN;'),

    # ---- group 3: the stale-peak bound -----------------------------------------------------
    (GUARD, 'group 3: the flat branch stops discarding the peak, so a high belonging to a position '
            'that closed while the guard was down survives into the NEXT position and the giveback '
            'fires early. This is the only direction in which persisting these can hurt the '
            'operator, and it is what bounds the whole fix. [[a-lockout-must-not-trap-you]]',
     '                        stateModel.PeakOpenGain = 0.0;\n'
     '                        stateModel.PeakGivebackTriggered = false;\n'
     '                        stateModel.PeakGivebackLastTriggerUnrealized = double.NaN;\n'
     '                        _stateDirty = true;\n'
     '                    }\n'
     '                }',
     '                        _stateDirty = true;\n'
     '                    }\n'
     '                }'),
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
