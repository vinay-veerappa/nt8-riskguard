"""Mutation battery for slice 2 (cross-instrument matrix rules).

Each mutation must turn the suite RED. A surviving mutant is a test that only
looks like coverage. Run after any edit to TranslateSymbol,
ResolveFollowerInstrument, ArePricesComparable, or the PerTickerMatrix branch
of CalculateFollowerQuantity.
"""
import os
import subprocess
import sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    # --- slice 2's core: the refusal must be gone from BOTH halves together ---
    ("TranslateSymbol re-refuses a cross-instrument mapping in matrix mode",
     "                return customTarget.ToUpper() + remainder;",
     "                if (rel.SizingMode == CopierSizingMode.PerTickerMatrix\n"
     "                    && customTarget.ToUpper() != root) return root + remainder;\n"
     "                return customTarget.ToUpper() + remainder;"),

    ("an explicit mapping is gated on AutoSymbolConversion",
     "            if (rel != null && rel.CustomSymbolMappings != null\n"
     "                && rel.CustomSymbolMappings.TryGetValue(root, out var customTarget)",
     "            if (rel != null && rel.AutoSymbolConversion && rel.CustomSymbolMappings != null\n"
     "                && rel.CustomSymbolMappings.TryGetValue(root, out var customTarget)"),

    ("ResolveFollowerInstrument short-circuits on AutoSymbolConversion again",
     "            string translated = TranslateSymbol(leaderInstrument.FullName, rel);",
     "            if (!rel.AutoSymbolConversion) return leaderInstrument;\n"
     "            string translated = TranslateSymbol(leaderInstrument.FullName, rel);"),

    # --- the ratio is keyed by the LEADER root; guessing rebuilds defect 2 ---
    ("the ratio falls back to the MAPPED root when the leader root has no rule",
     "                if (!hasRatio)\n                {\n                    // No usable ratio",
     "                if (!hasRatio && rel.CustomSymbolMappings != null\n"
     "                    && rel.CustomSymbolMappings.TryGetValue(symbol, out var fb)\n"
     "                    && rel.PerTickerRatios != null\n"
     "                    && rel.PerTickerRatios.TryGetValue(fb.ToUpper(), out ratio)\n"
     "                    && ratio > 0.0) { hasRatio = true; }\n"
     "                if (!hasRatio)\n                {\n                    // No usable ratio"),

    # --- slice 1's validation must still apply on the shared path ---
    ("a negative ratio is taken as an absolute value",
     "                    if (!double.IsNaN(ratio) && !double.IsInfinity(ratio) && ratio > 0.0)\n"
     "                    {\n                        hasRatio = true;\n                    }",
     "                    if (!double.IsNaN(ratio) && !double.IsInfinity(ratio) && ratio != 0.0)\n"
     "                    {\n                        ratio = Math.Abs(ratio); hasRatio = true;\n                    }"),

    ("a ratio rounding to zero is silently skipped instead of refused",
     "                    if (rawCopyQty < 1 && !isExit)",
     "                    if (false)"),

    ("a missing rule copies unscaled instead of failing closed on entry",
     "                        isClamped = true;\n                        return 0;\n                    }\n"
     "                    // Exit with no rule: mirror leaderQty",
     "                        isClamped = true;\n                    }\n"
     "                    // Exit with no rule: mirror leaderQty"),

    # --- P1-22 must survive ---
    ("MNQ and MES are declared price comparable",
     '                case "MNQ": return b == "NQ";',
     '                case "MNQ": return b == "NQ" || b == "MES";'),

    ("every pair is declared comparable",
     "            if (string.IsNullOrEmpty(leaderRoot) || string.IsNullOrEmpty(followerRoot)) return false;",
     "            if (string.IsNullOrEmpty(leaderRoot) || string.IsNullOrEmpty(followerRoot)) return false;\n"
     "            return true;"),

    # --- matrix mode must still never auto-convert ---
    ("matrix mode consults the mini/micro auto table",
     "            if (rel == null || (rel.AutoSymbolConversion && rel.SizingMode != CopierSizingMode.PerTickerMatrix))",
     "            if (rel == null || rel.AutoSymbolConversion)"),
]


def run():
    b = subprocess.run(['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if 'Build succeeded' not in b.stdout:
        return 'BUILD FAILED'
    r = subprocess.run(['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    for line in r.stdout.splitlines():
        if line.startswith('RESULTS:'):
            return line.strip()
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if '[FAIL]' not in ((r.stdout or '') + (r.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return 'NO RESULT LINE'


original = open(ENGINE, encoding='utf-8').read()
print('=== baseline ===')
baseline = run()
print(' ', baseline)

# A RED baseline makes this entire battery vacuous, and it is reachable in normal
# use. `killed` below is computed as "Failed = 0 is absent from the result line", so
# if the suite already has failures then EVERY mutant scores KILLED whether or not
# anything detected it, and the run reports a clean sweep having tested nothing.
#
# Test-first work reaches this state by design: acceptance tests are written red and
# stay red until the fix lands. Running a battery in that window is how you get a
# green light that proves nothing -- the same lying-harness shape these batteries
# exist to catch, one level up. Found 2026-08-13 with 8 P0-63/P?-66 assertions red.
if 'Failed = 0' not in baseline:
    print()
    print('REFUSING TO RUN: the baseline suite is NOT GREEN, so every mutant would be')
    print('scored KILLED regardless of whether the suite actually detected it. Land the')
    print('fix first (or stash the red acceptance tests), then re-run this battery.')
    sys.exit(2)

survivors = []
for name, old, new in MUTANTS:
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(ENGINE, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    killed = 'Failed = 0' not in res
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)

open(ENGINE, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

# Exit non-zero when anything survived. Without this the script printed
# "SURVIVORS: [...]" and still exited 0, so a CI step that ran it was a green light
# that proved nothing -- the same lying-harness shape these batteries exist to catch.
# An ANCHOR skip counts as a survivor: a mutation that could not be applied was not
# tested, and silently downgrading that to a pass is how coverage rots.
sys.exit(1 if survivors else 0)

