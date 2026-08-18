"""Mutation battery for slice 3b. Each mutation must turn the suite RED.

A surviving mutant is a test that only looks like coverage.
"""
import os, subprocess, sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    # ⚠️ RE-POINTED 2026-08-13. P1-85 restructured this block: the guessed "Sim101"
    # leader is gone and the branch is keyed on `isNew`, computed under the lock.
    # `check_anchors.py` caught both stale anchors the same day. Before that tool
    # existed, a stale anchor printed [SKIP] and scored a SURVIVOR -- but only the
    # next time somebody happened to run THIS battery, which is how mutate_ui2's
    # anchor stayed broken through a whole session.
    ("merge -> rebuild (group)",
     "                    grp = isNew\n                        ? new CopierGroup { GroupName = groupName, LeaderAccountName = leader ?? \"\" }\n                        : CloneConfig(existing);",
     "                    grp = new CopierGroup { GroupName = groupName, LeaderAccountName = leader ?? \"\" };"),

    ("merge -> rebuild (relationship)",
     "                rel = existing != null\n                    ? CloneConfig(existing)\n                    : new CopierRelationship();",
     "                rel = new CopierRelationship();"),

    ("clone removed: malformed request mutates stored group",
     "                        : CloneConfig(existing);",
     "                        : existing;"),

    ("group matrix comparer not re-applied",
     "            grp.PerTickerRatios = EnsureOrdinalIgnoreCase(grp.PerTickerRatios);\n            grp.CustomSymbolMappings = EnsureOrdinalIgnoreCase(grp.CustomSymbolMappings);",
     ""),

    ("explicit null no longer stripped (a null wipes stored config)",
     "                if (prop.Value == null || prop.Value.Type == JTokenType.Null)\n                    normalized.Remove(prop.Name);",
     "                if (false)\n                    normalized.Remove(prop.Name);"),

    ("relationship matrix comparer not re-applied",
     "            rel.PerTickerRatios = EnsureOrdinalIgnoreCase(rel.PerTickerRatios);\n            rel.CustomSymbolMappings = EnsureOrdinalIgnoreCase(rel.CustomSymbolMappings);\n\n            ApplyArmingGate",
     "\n            ApplyArmingGate"),

    ("arming gate ignores whether arming was requested (silently disarms)",
     "            if (armed && armingWasRequested && !confirmLive)",
     "            if (armed && !confirmLive)"),

    ("arming gate dropped entirely (arms without confirmLive)",
     "            if (armed && armingWasRequested && !confirmLive)\n                set(false);",
     "            if (false)\n                set(false);"),

    # WARNING This anchor was WIDER until 2026-08-13: it spanned ApplyArmingGate and
    # UpsertGroup as consecutive lines. P1-76 inserted its overlap check between them, the
    # anchor stopped matching, and the battery reported "(ANCHOR)" -- which it scores as a
    # SURVIVOR. That default is why the weakening was caught: an unrelated edit can silently
    # disarm another battery's mutant, and only refusing to score an unapplied mutant sees it.
    ("Upsert re-applies its own gate, undoing the preserved armed state",
     "            UpsertGroup(grp, true);",
     "            UpsertGroup(grp, confirmLive);"),

    ("`followers` spelling dropped",
     "            if (normalized[\"FollowerAccounts\"] == null && req[\"followers\"] is JArray followers)\n                normalized[\"FollowerAccounts\"] = followers;",
     ""),

    ("unknown-enum stripping dropped (a bad sizingMode should not wipe the config)",
     "            return RemoveUnknownEnums(normalized, targetType);",
     "            return normalized;"),

    # --- CM5: a collection named in the request replaces the stored one ---
    ("group collections are no longer replaced (matrix becomes append-only)",
     "            ClearCollectionsNamedIn(normalized, grp);\n",
     ""),

    ("relationship collections are no longer replaced",
     "            ClearCollectionsNamedIn(normalized, rel);\n",
     ""),

    # Tried and deliberately NOT kept: replacing dict.Clear() with a reassignment
    # to a fresh Dictionary<string,T> (default comparer). It is an EQUIVALENT
    # mutant -- the EnsureOrdinalIgnoreCase calls after PopulateObject restore the
    # comparer either way -- so it survives by design, not by missing coverage.
    # Clear() is kept for simplicity, not for P1-39.

    ("list-valued fields are not replaced",
     "                var list = current as System.Collections.IList;\n"
     "                if (list != null) list.Clear();",
     "                var list = current as System.Collections.IList;\n"
     "                if (false) list.Clear();"),
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
        print(f'  [SKIP] {name}: anchor matched {original.count(old)} times')
        survivors.append(name + ' (ANCHOR)')
        continue
    open(ENGINE, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    killed = 'Failed = 0' not in res
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
    print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
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

