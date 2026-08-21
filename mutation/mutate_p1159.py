"""Mutation battery for P1-159: one cap dictionary, both enforcement points.

`InstrumentLimits` was read by exactly ONE production site -- the per-ORDER check in
`ExecuteOrderUpdate`, against `e.Order.Quantity`. So `MNQ: 1` refused a 3-lot ORDER and permitted
three 1-lot orders that built the identical 3-lot POSITION. The rule that looks at position size,
`MAX_SIZE_BREACH`, resolves its cap through `ResolveMaxContracts`, which had never heard of
`InstrumentLimits`.

MEASURED LIVE on the funded account 2026-08-18: the config carries `MNQ: 1` beside
`MaxContractsPerAccount: 5` and an EMPTY `Profiles` list, so every position resolved to 5 and the
cap the operator had configured bound nothing that could lose money. A duplicate entry that session
produced MNQ 2 with no rule firing.

The fix merges `_config.InstrumentLimits` into the resolved profile inside `CreateDynamicProfile`,
so `ResolveMaxContracts` keeps the signature `P1-149` gave it and BOTH of its callers -- the
reactive sweep and the bridge's pre-trade `EffectiveMaxContracts` -- are fixed by one edit. That
shape is the whole point: two copies of a cap rule is [[a-second-reader-of-the-same-state]], and
`P1-149` extracted this method specifically to end it.

THE GROUPS BELOW:

  1. THE MERGE HAPPENS, AND ITS RESULT IS USED. A merged dictionary that is computed and then not
     assigned is [[a-source-gate-must-assert-the-condition]] in its live form -- four mutants in
     this project have beaten a gate meant to prove a value is USED.
  2. ⚠️ THE TWO CAPS COMBINE BY MINIMUM, NOT BY PRECEDENCE. Both directions are mutated, because
     each precedence order looks correct from one test and silently discards the other surface's
     number. A cap is a maximum; the minimum of two maxima cannot permit more than either intended.
  3. ⚠️ THE GLOBAL LIMIT BINDS EVEN WITH NO PER-ACCOUNT PROFILE. This is the operator's ACTUAL
     configuration -- `Profiles` is empty -- so a fix that only tightens existing profile entries
     passes a plausible-looking test and changes nothing on the machine that matters.
  4. THE LOOKUP STAYS CASE-INSENSITIVE. `RiskGuardModels.cs` warns about this in writing beside the
     `InstrumentLimits` declaration, and the pre-fix line supplied no comparer at all.
  5. THE OPERATOR'S CONFIG IS NOT MUTATED. The pre-fix line ALIASED the config object's own
     dictionary. Merging into the alias writes derived caps back where a later save persists them
     as though they had been typed -- a silent, permanent edit to a risk configuration.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the merge happens, and its result is used ---------------------------------
    (GUARD, 'group 1: the global limits are never merged, which is the measured defect exactly -- '
            'a funded account whose config says MNQ 1 resolving every MNQ position to 5',
     '            if (_config.InstrumentLimits != null)',
     '            if (false)'),

    (GUARD, 'group 1: the merged dictionary is COMPUTED and then not USED -- the profile keeps the '
            'old aliased dictionary. Every line of the fix is present to a source scan and none of '
            'it reaches the enforcer',
     '                InstrumentProfiles = mergedProfiles,',
     '                InstrumentProfiles = baseProfile.InstrumentProfiles ?? new Dictionary<string, InstrumentProfile>(),'),

    (GUARD, 'group 1: the base profile\'s own per-instrument entries are dropped rather than copied, '
            'so configuring a cap per ACCOUNT stops working the moment this merge exists -- a fix '
            'that closes one hole by opening another',
     '                foreach (var kvp in baseProfile.InstrumentProfiles)\n'
     '                {\n'
     '                    mergedProfiles[kvp.Key] = kvp.Value;\n'
     '                }',
     '                // base entries not copied'),

    # ---- group 2: minimum, not precedence ---------------------------------------------------
    (GUARD, 'group 2: the per-account profile always wins, so a GLOBAL limit tighter than the '
            'profile is silently discarded. Passes any test written only from the operator\'s '
            'current config, where Profiles is empty and the branch never runs',
     '                            MaxContracts = Math.Min(existing.MaxContracts, globalCap)',
     '                            MaxContracts = existing.MaxContracts'),

    (GUARD, 'group 2: the global limit always wins, so a per-ACCOUNT cap tighter than the global '
            'one is silently discarded -- the opposite precedence, equally plausible, and the '
            'reason both directions are asserted',
     '                            MaxContracts = Math.Min(existing.MaxContracts, globalCap)',
     '                            MaxContracts = globalCap'),

    (GUARD, 'group 2: the caps combine by MAXIMUM -- the one direction that can PERMIT more than '
            'either configured surface intended, and the only genuinely unsafe way to be wrong here',
     '                            MaxContracts = Math.Min(existing.MaxContracts, globalCap)',
     '                            MaxContracts = Math.Max(existing.MaxContracts, globalCap)'),

    # ---- group 3: it binds with no per-account profile --------------------------------------
    (GUARD, 'group 3: a global limit binds ONLY where a per-account profile already exists. This is '
            'the mutant that matters most: the operator\'s live `Profiles` list is EMPTY, so this '
            'restores the defect completely on the only machine it was measured on, while looking '
            'like a working merge',
     '                    else\n'
     '                    {\n'
     '                        mergedProfiles[kvp.Key] = new InstrumentProfile { MaxContracts = globalCap };\n'
     '                    }',
     '                    else\n'
     '                    {\n'
     '                        // no profile entry: global limit not applied\n'
     '                    }'),

    # ---- group 4: the lookup stays case-insensitive -----------------------------------------
    (GUARD, 'group 4: the merged dictionary drops StringComparer.OrdinalIgnoreCase, making every '
            'instrument cap lookup case-SENSITIVE -- a hand-edited `mnq` key caps nothing, and the '
            'models file warns about this exact hazard in writing',
     '            var mergedProfiles = new Dictionary<string, InstrumentProfile>(StringComparer.OrdinalIgnoreCase);',
     '            var mergedProfiles = new Dictionary<string, InstrumentProfile>();'),

    # ---- group 5: the operator's config is not mutated --------------------------------------
    (GUARD, 'group 5: the merge writes back into the CALLER\'s dictionary instead of a copy, so '
            'derived caps land in _config.Profiles[i] where the next config save persists them as '
            'though the operator had typed them, and each resolution compounds against the last. '
            'Numerically identical on the first pass, which is why it needs its own test',
     '            var mergedProfiles = new Dictionary<string, InstrumentProfile>(StringComparer.OrdinalIgnoreCase);\n'
     '\n'
     '            if (baseProfile.InstrumentProfiles != null)\n'
     '            {\n'
     '                foreach (var kvp in baseProfile.InstrumentProfiles)\n'
     '                {\n'
     '                    mergedProfiles[kvp.Key] = kvp.Value;\n'
     '                }\n'
     '            }',
     '            var mergedProfiles = baseProfile.InstrumentProfiles\n'
     '                ?? new Dictionary<string, InstrumentProfile>(StringComparer.OrdinalIgnoreCase);'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # ⚠️ Encoding PINNED: a cp1252 default raises part-way through on a non-ASCII byte, between
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
# tools/check_expected_survivors.py enforces the pairing in BOTH directions -- reaching for the
# helper without a declaration removes the prompt to justify the next exemption someone adds.
if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
