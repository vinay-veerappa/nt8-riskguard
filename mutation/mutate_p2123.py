"""Mutation battery for P2-123 (the per-ticker matrix tab reads the per-ticker config).

The defect was a tab named "Symbol & Per-Ticker Matrix" that contained no matrix: a hardcoded
six-row poster of asset classes, reading ZERO engine state, beside six TextBox fields declared
and never constructed. An operator who set {"NQ": 2, "ES": 1} saw no trace of it, while the
poster went on asserting the DEFAULT conversion -- so the screen actively contradicted the
config the copier was enforcing.

⚠️ THESE TESTS WERE WRITTEN AFTER THE CODE, not before it, and they all passed on their first
run. That is the weakest evidence position in this repo -- a suite written against an
implementation tends to assert what the implementation does rather than what it should do -- so
this battery is the only thing that says the assertions have teeth. Read the score, not the
1973.

The mutants divide into three groups, matching the three ways this tab can lie:

  * 1-4 make the tab state a number or a route the COPIER DOES NOT USE. Mutant 1 is the
    original defect in its purest form: echo the configured ratio back instead of asking the
    engine what is in force. It is the one assertion holding the architecture of the ticket.
  * 5-8 attack the ZERO that means "not applicable". ComputeEffectiveRatio answers 0.0 for
    fixed-lot and equity-based sizing because a ratio is meaningless there, and rendering that
    as "x0" tells a correctly configured operator their copier multiplies by zero. Same shape
    as CopierMetric.Measured, which P1-22 shipped wrong.
  * 9-13 soften or silence the warnings -- the rounding that DROPS a leader fill, the matrix
    root that copies nothing, and the empty-config headline that must not read as healthy.

⚠️ WHAT THIS BATTERY CANNOT REACH, stated so nobody reads the score as broader than it is.
TradeCopierWindow.cs is excluded from the test build (P2-27's open half), so no mutant can be
placed in it -- the harness would not compile it either way, and a mutant nothing compiles is
not evidence. The window is held only by the source gates in
TestP2123_TheWindowRendersTheTabFromTheView and by `nt_compile`. That is precisely why the
decisions live in CopierSymbolMatrixView, where they can be mutated at all.

⚠️ AND THE VISUAL HALF IS UNVALIDATED BY ANYTHING HERE. Nothing in this file, and nothing in
the suite, proves the tab LOOKS right. Opening Trade Copier Manager is what does that.

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

# No `import _battery` here on purpose -- see the exit at the foot of the file.

# P2-114: a non-ASCII character in a mutant DESCRIPTION raises UnicodeEncodeError inside
# print() on a cp1252 console -- BETWEEN applying a mutant and restoring it, which leaves a
# live mutant in the source tree.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEW = os.path.join(REPO, 'addons', 'CopierSymbolMatrixView.cs')
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

# (file, description, find, replace)
MUTANTS = [
    # ---- 1. THE DEFECT VERBATIM: the tab forms its own opinion about the ratio ----
    # Echoing rel.QuantityRatio back is exactly what a hand-written tab would have done, and it
    # is wrong the moment automatic conversion applies: the operator writes 3.0, the copier
    # uses 0.3. This is F-9's rule -- derive the display FROM the enforcer -- and it is the
    # single mutant that holds the architecture of the whole ticket.
    (VIEW,
     "the view computes its own ratio instead of asking the engine, so the tab shows the "
     "CONFIGURED number rather than the one in force -- the original defect, restated",
     '                double ratio = TradeCopierEngine.ComputeEffectiveRatio(rel, root);',
     '                double ratio = rel == null ? 0.0 : Math.Abs(rel.QuantityRatio);'),

    # ---- 2. the routing stops coming from the engine ----
    (VIEW,
     "the view assumes every root routes to itself instead of asking TranslateSymbol, so a "
     "custom mapping and an automatic mini/micro conversion both vanish from the screen",
     '                string follower = routeOf == null ? root : routeOf(rel, root);',
     '                string follower = root;'),

    # ---- 3. only PerTickerRatios is listed ----
    # A custom mapping is honoured in EVERY sizing mode and is the setting most likely to send
    # a copy somewhere unexpected. Listing one dictionary hides exactly that.
    (VIEW,
     "CustomSymbolMappings stops contributing roots, so a mapping with no ratio entry -- the "
     "setting most likely to route a copy somewhere unexpected -- is invisible",
     '            if (rel.CustomSymbolMappings != null)\n            {\n                foreach (var key in rel.CustomSymbolMappings.Keys)',
     '            if (false)\n            {\n                foreach (var key in rel.CustomSymbolMappings.Keys)'),

    # ---- 4. a custom mapping is attributed to the automatic table ----
    (VIEW,
     "a custom mapping is reported as the built-in mini/micro table, so an operator hunting a "
     "surprising route looks in the default table instead of their own config",
     '            if (hasCustom)\n                row.RoutingOrigin = CopierSymbolOrigin.CustomMapping;',
     '            if (false)\n                row.RoutingOrigin = CopierSymbolOrigin.CustomMapping;'),

    # ---- 5. THE ZERO. fixed lot starts rendering a ratio ----
    (VIEW,
     "RatioApplies answers true for fixed lot, so a correctly configured fixed-lot "
     "relationship renders x0 -- telling the operator their copier multiplies by zero",
     '            if (fixedLotMode) return false;\n            return mode == CopierSizingMode.QuantityRatio || mode == CopierSizingMode.PerTickerMatrix;',
     '            if (fixedLotMode) return false;\n            return true;'),

    # ---- 6. the FixedLotMode FLAG is ignored ----
    # The flag overrides the enum in ComputeEffectiveRatio. A view that reads only the enum
    # disagrees with the engine on exactly the relationships that set both.
    (VIEW,
     "the FixedLotMode flag is ignored, so a quantity-ratio relationship with fixed lots set "
     "renders a ratio the engine does not use",
     '            if (fixedLotMode) return false;',
     '            if (false) return false;'),

    # ---- 7. the not-applicable text becomes a number ----
    (VIEW,
     "RatioTextFor renders a number where the sizing mode ignores ratios, which is the "
     "CopierMetric.Measured confusion at a second surface",
     '            if (!ratioApplies)\n                return "not sized by ratio (" + SizingModeText(mode) + ")";',
     '            if (false)\n                return "not sized by ratio (" + SizingModeText(mode) + ")";'),

    # ---- 8. automatic conversion forgets the matrix-mode condition ----
    # This is the half the static poster got wrong: it claimed conversion happened "across all
    # futures asset classes", with no mention of either gating condition.
    (VIEW,
     "AutoConversionActive forgets that matrix mode disables conversion, so a matrix-mode "
     "relationship claims a conversion the copy path does not perform",
     '            return rel.AutoSymbolConversion && rel.SizingMode != CopierSizingMode.PerTickerMatrix;',
     '            return rel.AutoSymbolConversion;'),

    # ---- 9. the dropped 1-lot stops being reported ----
    (VIEW,
     "SmallestLeaderFillThatCopies always answers 1, so the rounding that silently DROPS a "
     "1-lot micro copy is never mentioned -- the caveat the original poster omitted",
     '                if (TradeCopierEngine.RoundToContracts(n * effectiveRatio) >= 1) return n;',
     '                if (n >= 1) return n;'),

    # ---- 10. THE ARITHMETIC ANSWER, which is the one I shipped first and it was WRONG ----
    # ceil(1/ratio) says 10 at ratio 0.1 and 3 at ratio 0.4. The copy path rounds midpoints TO
    # EVEN, so the honest answers are 6 and 2. This mutant restores the plausible-looking
    # arithmetic, and it must die: a tab that overstates what the operator needs is a surface
    # stating behaviour the engine does not perform, which is this ticket's own defect.
    (VIEW,
     "the smallest copyable fill is computed as ceil(1/ratio) instead of probed, which "
     "disagrees with the copy path by four contracts at ratio 0.1",
     '            for (int n = 1; n <= MaxProbedLeaderFill; n++)\n            {\n                if (TradeCopierEngine.RoundToContracts(n * effectiveRatio) >= 1) return n;\n            }\n            return 0;',
     '            if (effectiveRatio >= 1.0) return 1;\n            return (int)Math.Ceiling(1.0 / effectiveRatio);'),

    # ---- 11. a matrix root with no ratio stops saying it copies nothing ----
    (VIEW,
     "a per-ticker-matrix root with no ratio entry stops warning, so a relationship that "
     "copies NOTHING for that instrument renders clean",
     '                if (effectiveRatio <= 0.0)',
     '                if (false)'),

    # ---- 12. the warning count stops raising severity ----
    (VIEW,
     "a matrix that loses fills to rounding still reads healthy, because the warnings are "
     "counted and then not acted on",
     '                matrix.Severity = CopierStatusSeverity.Warn;',
     '                matrix.Severity = CopierStatusSeverity.Ok;'),

    # ---- 13. an empty configuration reads as a clean bill of health ----
    # "Nothing to show" and "nothing is wrong" must not look the same.
    (VIEW,
     "an unconfigured relationship reports Ok rather than Info, so an empty panel reads as a "
     "clean bill of health instead of an absence of information",
     '                matrix.Severity = CopierStatusSeverity.Info;\n                return matrix;',
     '                matrix.Severity = CopierStatusSeverity.Ok;\n                return matrix;'),

    # ---- 14. THE ENGINE SIDE: the promoted resolver loses its null guard ----
    # ComputeEffectiveRatio was a local function that could assume a non-null rel. Promoting it
    # to a public static exposed it to callers that cannot make that promise.
    (ENGINE,
     "the promoted ComputeEffectiveRatio drops its null guard, which the local function it was "
     "extracted from never needed and every new caller does",
     '        public static double ComputeEffectiveRatio(CopierRelationship rel, string symbolRoot)\n        {\n            if (rel == null) return 0.0;',
     '        public static double ComputeEffectiveRatio(CopierRelationship rel, string symbolRoot)\n        {\n            if (false) return 0.0;'),

    # ---- 14b. the SHARED rounding rule ----
    # RoundToContracts is now the one definition used by BOTH the copy path and the tab. Making
    # it truncate instead of round changes what the copier SENDS as well as what the tab says,
    # so the conformance test is the only thing that can tell the two apart.
    (ENGINE,
     "RoundToContracts truncates instead of rounding, which silently changes copy SIZING as "
     "well as the tab -- the hazard of sharing one rule between a reporter and an enforcer",
     '            return (int)Math.Round(rawQuantity);',
     '            return (int)rawQuantity;'),

    # ---- 15. the engine's micro multiplier is dropped ----
    # Not a mutation of the view at all: it proves the tab's numbers actually FOLLOW the
    # engine. If the tests still pass with the engine's conversion removed, the view is not
    # reading it.
    (ENGINE,
     "the engine stops applying the micro multiplier; if the tab's assertions survive this, "
     "the tab is not reading the engine's ratio at all",
     '                else if (symbolRoot == "MNQ" || symbolRoot == "MES" || symbolRoot == "MYM" || symbolRoot == "MCL" || symbolRoot == "MGC" || symbolRoot == "M2K")\n                    symbolMultiplier = 0.1;',
     '                else if (false)\n                    symbolMultiplier = 0.1;'),
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


originals = {p: open(p, encoding='utf-8').read() for p in (VIEW, ENGINE)}

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
try:
    for i, (path, name, old, new) in enumerate(MUTANTS, 1):
        print(f'\n=== mutant {i}/{len(MUTANTS)}: {name} ===')
        src = originals[path]
        if src.count(old) != 1:
            print(f'  [SKIP] {name}: anchor matched {src.count(old)} times in '
                  f'{os.path.basename(path)}')
            survivors.append(name + ' (ANCHOR)')
            continue
        open(path, 'w', encoding='utf-8', newline='').write(src.replace(old, new))
        res = run()
        killed = _battery.score(res, run)
        print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
        if not killed:
            survivors.append(name)
        open(path, 'w', encoding='utf-8', newline='').write(src)
finally:
    # try/finally: a battery killed mid-run otherwise leaves a LIVE MUTANT in the tree --
    # measured once already, when a stopped mutate_cm4 batch left one in TradeCopierEngine.cs
    # and a `git diff` skim did not find it.
    for p, text in originals.items():
        open(p, 'w', encoding='utf-8', newline='').write(text)

print('\nrestored originals;', run())

if survivors:
    print('\nSURVIVORS:')
    for s in survivors:
        print('  -', s)
else:
    print('\nSURVIVORS: none')

# Plain exit, NOT _battery.finish: this battery declares no EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions.
sys.exit(1 if survivors else 0)
