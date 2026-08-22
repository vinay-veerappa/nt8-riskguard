"""Mutation battery for P2-119 / P1-117 (the config-save chokepoint and its outcome report).

Several mutants reinstate defects THE AGENT-LOOP PATCH ACTUALLY SHIPPED and that survived a
green build, 1833 passing tests, and a two-model review panel. Read the list, not the score:

  * mutant 6 is the patch's own `newMode = oldMode` blank-fill. It validated the LIVE mode and
    then serialised the blank one -- validating one config and persisting another, which is
    strictly worse than the defect being fixed: it does not merely fail to report an outcome,
    it reports a success about the wrong object. The panel caught this one (finding #8).
  * mutant 7 is the same shape on PnLRules: a missing section was backfilled from the config
    being REPLACED, so "remove the trailing drawdown rule" passed preflight against the limit
    it was removing.
  * mutant 3 is the changed-check's CASE rule. When this battery was first written the mutant
    relaxed Ordinal -> OrdinalIgnoreCase and SURVIVED, and the reason was the useful part: every
    mode pair in the acceptance tests differed under both comparisons, so nothing could tell them
    apart. `shadow` -> `SHADOW` was the discriminator the battery demanded. Then P3-118 made all
    four readers of Mode case-insensitive (RefuseChange included) AND made SHADOW a valid mode --
    which turned that discriminator into an EQUIVALENT mutant (both comparisons accept a valid
    mode). The kill moved to the pure/override case: an unchanged case-variant of an UNIMPLEMENTED
    mode (pure -> PURE) is a change under Ordinal and gets refused, trapping the operator on a
    value they did not touch -- the P2-119 defect in the mode field. A surviving mutant is
    sometimes a missing test; a newly-equivalent one is sometimes a moved test.

⚠️ WHAT NO MUTANT HERE CAN CATCH, stated so nobody reads this battery as broader than it is.
The single most dangerous defect in the reviewed patch was that `ConfigSaveResult` was NESTED
inside `GuardConfigEdit`. That builds green, passes every test, and FAILS NINJATRADER'S COMPILE,
because `RiskGuardWindow.cs` names the type unqualified and is `#if !TESTING` -- invisible to
`dotnet build`, and only syntax-checked by tools/check_window_parses.py. It cannot be expressed
as a mutant because the mutant would not compile in the harness either, which is the whole
point: the harness and NinjaTrader do not compile the same set of files. `nt_compile` is the
only gate for that class, and it is not optional.

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDIT = os.path.join(REPO, 'addons', 'GuardConfigEdit.cs')
ADDON = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

# (file, description, find, replace). The file is per-mutant because this ticket's behaviour
# is a JOIN across three of them -- the validator, the chokepoint that calls it, and the copy
# helper that makes its old/new comparison meaningful. A battery pinned to one file would have
# scored full marks on a third of the change.
MUTANTS = [
    # ---- 1. the defect verbatim: the outcome is not reported ----
    (ADDON,
     "a failed write reports Saved = true -- the defect this ticket exists to fix, where every "
     "caller announces a success nobody observed",
     '                    return new ConfigSaveResult { Saved = false, Error = ex.Message };',
     '                    return new ConfigSaveResult { Saved = true, Error = ex.Message };'),

    # ---- 2. REMOVED. It was a placeholder 4-tuple of Nones, filtered out at runtime, and
    # mutation/check_anchors.py correctly REFUSED it: "could not read it statically". That gate
    # was hardened in session 47 to refuse what it cannot parse rather than print ok over it,
    # and it caught this on its first opportunity. The numbering below is deliberately NOT
    # closed up -- the docstring above and several tests cite mutants by number.

    # ---- 3. the changed-check goes case-SENSITIVE ----
    # P3-118 made the four readers of Mode case-insensitive, and RefuseChange (the fourth) with
    # them. This mutant reverts the changed-check to Ordinal: a case-only edit of an UNIMPLEMENTED
    # mode (pure -> PURE) then reads as a CHANGE, gets re-validated, and is REFUSED -- trapping the
    # operator on a value they did not change, which is the P2-119 defect in the mode field.
    # (Was originally the reverse relaxation; it became an equivalent mutant once SHADOW was a valid
    # mode, so the kill was moved to the pure/override case where Ordinal and IgnoreCase still differ.)
    (EDIT,
     "the mode changed-check goes case-sensitive, so an unchanged case-variant of an unimplemented "
     "mode (pure -> PURE) is re-validated and REFUSED -- trapping the operator on a value they did "
     "not change; TestP2119_AnUnchangedCaseVariantOfABadModeDoesNotTrap dies.",
     '            if (!string.Equals(oldMode, newMode, StringComparison.OrdinalIgnoreCase))',
     '            if (!string.Equals(oldMode, newMode, StringComparison.Ordinal))'),

    # ---- 4. the NaN comparison, which is the whole reason .Equals is used ----
    (EDIT,
     "`!=` replaces `.Equals` for the trailing drawdown, so an UNCHANGED NaN reads as a change "
     "and the operator is refused the save that would repair it -- trapped by the validator",
     '            if (!newTrailingDrawdown.Equals(oldTrailingDrawdown))',
     '            if (newTrailingDrawdown != oldTrailingDrawdown)'),

    # ---- 5. the not-trapped clause removed: validate regardless of change ----
    (EDIT,
     "the trailing-drawdown check ignores whether this write CHANGED it, so a config already "
     "holding a bad value refuses every subsequent save -- including the account-exclusion "
     "toggle, which is how an account is put BACK under the guard (P1-106's shape)",
     '            if (!newTrailingDrawdown.Equals(oldTrailingDrawdown))\n'
     '            {\n'
     '                string refusal = RefuseTrailingDrawdown(newTrailingDrawdown);',
     '            if (true)\n'
     '            {\n'
     '                string refusal = RefuseTrailingDrawdown(newTrailingDrawdown);'),

    # ---- 6. THE PATCH'S OWN blank-mode backfill ----
    (ADDON,
     "the blank-mode backfill returns: a config with Mode = \"\" is validated against the LIVE "
     "mode and then serialised blank. Validated one object, persisted another, and reported "
     "success about the first.",
     '                string newMode = newConfig.Mode;',
     '                string newMode = string.IsNullOrWhiteSpace(newConfig.Mode) ? oldMode : newConfig.Mode;'),

    # ---- 7. THE PATCH'S OWN PnLRules backfill ----
    (ADDON,
     "a missing PnLRules section is backfilled from the config being REPLACED, so removing the "
     "trailing drawdown rule passes preflight against the limit it removes",
     '                double newTrailing = TrailingDrawdownOf(newConfig);',
     '                double newTrailing = newConfig.PnLRules == null ? oldTrailing : newConfig.PnLRules.TrailingDrawdown;'),

    # ---- 8. the validator is never consulted ----
    (ADDON,
     "the refusal is computed and then IGNORED -- the write proceeds anyway. A gate that a "
     "value is COMPUTED is not a gate that it is USED, which has beaten four source checks in "
     "this project already.",
     '                if (refusal != null)\n'
     '                {\n'
     '                    LogEvent("SYSTEM", "CONFIG_REFUSE", refusal);',
     '                if (false)\n'
     '                {\n'
     '                    LogEvent("SYSTEM", "CONFIG_REFUSE", refusal);'),

    # ---- 9. the first-write path stops being strict ----
    (ADDON,
     "with NO existing config, the strict Refuse is swapped for RefuseChange against nulls, so "
     "the very first config written to a fresh box is never validated at all",
     '                    : GuardConfigEdit.Refuse(newMode, newTrailing, newSessions);',
     '                    : null;'),

    # ---- 10. DeepCopy stops copying ----
    (MODELS,
     "DeepCopy returns its SOURCE. The window then edits the live config in place again, so the "
     "chokepoint compares every value against itself and permits everything -- P1-117 restored, "
     "with the whole P2-119 mechanism still present and inert",
     '            return Apply(source, null, out _);',
     '            return source;'),

    # ---- 11. the warning reads the wrong object ----
    (ADDON,
     "EXPECTED SURVIVOR: the post-save warning is computed from the caller's object instead of "
     "the RELOADED config. UNKILLABLE BY CONSTRUCTION, and the reason is worth more than the "
     "mutant: `_config` at that point is a JSON round trip of `newConfig`, so the two agree on "
     "every field Refuse examines, and no input can separate them. Reading the reloaded config "
     "is still the correct source -- the warning describes what the guard is NOW RUNNING, and "
     "the day LoadConfig normalises or rejects anything, the caller's object stops being that. "
     "Kept as a mutant because it documents an invariant a future change could break: if "
     "LoadConfig ever alters what it read, this becomes killable and the marker must come off.",
     '                        : GuardConfigEdit.Refuse(_config.Mode, TrailingDrawdownOf(_config),\n'
     '                                                 _config.MinShadowSessions);',
     '                        : GuardConfigEdit.Refuse(newConfig.Mode, TrailingDrawdownOf(newConfig),\n'
     '                                                 newConfig.MinShadowSessions);'),

    # ---- 12. the null guard ----
    (ADDON,
     "a null config is accepted and serialised, writing the literal `null` to config.json",
     '                if (newConfig == null)',
     '                if (false)'),
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


originals = {p: open(p, encoding='utf-8').read() for p in (EDIT, ADDON, MODELS)}

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
    for path, name, old, new in MUTANTS:
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
    # ⚠️ try/finally, which mutate_p227.py does NOT have. A battery killed mid-run leaves a
    # LIVE MUTANT in the tree -- measured once already, when a stopped mutate_cm4 batch left
    # one in TradeCopierEngine.cs and a `git diff` skim did not find it. Three files makes
    # that worse, not better.
    for p, text in originals.items():
        open(p, 'w', encoding='utf-8', newline='').write(text)

print('\nrestored originals;', run())

# Routed through _battery.finish because mutant 11 declares itself an EXPECTED SURVIVOR.
# tools/check_expected_survivors.py enforces the pairing in BOTH directions -- a battery that
# declares one MUST use this, and a battery that declares none must NOT -- so the exemption
# cannot be introduced later without something forcing a second look at whether it is honest.
_battery.finish(survivors, MUTANTS)
