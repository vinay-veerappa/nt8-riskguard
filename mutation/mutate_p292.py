"""Mutation battery for P2-92 (`shadow` mode must be observation-only).

`ProcessAction` gated EXECUTION on mode, so a shadow breach flattened nothing -- but
ten rule paths set `IsLockedOut` before dispatch, outside any mode check, and
`CanTrade` read that flag ABOVE its own `if (!_isArmed) return true;` hatch. So in
shadow: nothing was flattened AND the account stopped being allowed to trade.
`CanTrade` is the universal pre-trade gate, so that silently halted the copier and
every strategy.

The fix records the AUTHORITY a lockout was imposed under, in a second field, rather
than changing what `IsLockedOut` means -- because eight existing tests breach a rule
in the default mode (which is `shadow`) and assert the flag, and a fix that stopped
writing it would have broken all eight and been indistinguishable, from the test
output, from a fix that broke the guard.

WHAT EACH GROUP IS DEFENDING:

  * MUTANT 1 restores the defect: `CanTrade` stops consulting the authority. Every
    lockout bites in every mode again.

  * MUTANT 2 is the WRONG FIX, and it is the reason the authority is a stored field
    instead of a mode check at read time. `CanTrade` consults the CURRENT mode
    directly, which looks equivalent and is not: an operator locked out in `live` can
    then escape by switching to `shadow`. That is FR-30 / judge-loop P1-4's concern
    through a different setting, and `LockoutBypassWhileDisarmedAccounts` cannot
    mitigate it because the guard is armed.

  * MUTANT 3 inverts the authority sense in the helper. Shadow breaches enforce and
    live breaches do not -- the maximally wrong outcome, and a single `!`.

  * MUTANT 4 hardcodes the authority to "acting", which is what a merge conflict or a
    hasty revert produces. Shadow lockouts bite again and nothing else changes.

  * MUTANT 5 hardcodes it to "shadow only". Now a LIVE breach does not stop trading,
    which is a protection REMOVAL on a funded account -- the direction that costs
    money, from the same one-line edit as mutant 4.

  * MUTANT 6 renames the persisted DTO field so it no longer round-trips. Nothing
    fails at compile or in memory; the authority is simply lost across a restart, and
    every restored lockout reads as enforced. That is the FAIL-CLOSED direction, so it
    is the mutant most likely to survive -- it must be killed by the legacy-state-file
    test's live counterpart, not by luck.

  * MUTANT 7 gives the persisted DTO field an `= true` initializer, which inverts the
    fail-closed default for every state file that predates the field: absence would
    then read as "shadow only" and RELEASE the lockout. This is P1-54's lesson
    (`LockoutUntil` must not be shortened by an upgrade) in the other direction.

  * MUTANT 8 gates `LockAccount` on the mode too -- the cheapest way to satisfy a
    naive reading of "gate every lockout site". A lockout the operator explicitly
    asked for then evaporates in shadow.

  * MUTANT 9 drops the explicit `LockoutWasShadowOnly = false` from `LockAccount`, so
    a manual lockout on an account that already breached in shadow INHERITS the shadow
    authority and is silently ignored. This is the one finding the review panel got
    right, out of four it upheld.

  * MUTANT 10 stops the rehydration path restoring the authority. Combined with the
    field's default that is fail-closed, so it survives on safety -- and it means a
    shadow observation is promoted to an enforced lockout by a restart, which is a
    protection INCREASE nobody asked for and which will read as a phantom lockout.

  * MUTANT 11 removes the `SHADOW_LOCKOUT` log line. Nothing breaks, and the shadow
    session -- whose entire purpose is to collect what the guard WOULD have done, and
    which `MinShadowSessions` gates arming on -- records nothing. `P1-71`'s class: an
    outcome that happens and leaves no readable trace.

WHAT IS NOT MUTATED, and it was a real gap until P2-94 closed it: a TIMED manual
lockout now stops new orders because CanTrade reads LockoutUntil as well as
IsLockedOut. The two mutants above were re-anchored on the new condition when
P2-94 widened the lockout test from `IsLockedOut` alone to
`IsLockedOut || (LockoutUntil > MinValue && UtcNow < LockoutUntil)`.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red
baseline.
"""
import os
import re
import subprocess
import sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
# P2-29: one anchor below moved to RiskGuardModels.cs when the independent top-level
# types left RiskGuardAddOn.cs (a MOVE, not a rewrite -- they are their own types, not
# members of RiskGuardAddOn). This battery was single-file; every mutant now names its
# own file, because a battery that GUESSES which file holds an anchor is exactly the
# ambiguity check_anchors.py exists to remove.
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # P1-100 moved the predicate these two defend out of CanTrade and into `LockoutBinds`,
    # which is now its ONE home -- CanTrade, IsAccountLocked and the entry-cancel block all
    # call it. The anchors were repointed there rather than retired: the invariant did not
    # change, only its address, and `check_anchors.py` is what noticed. Both mutants are now
    # strictly stronger, because a single edit here regresses all three readers at once.
    (GUARD,
     "the shared predicate stops consulting the authority -- the defect, restored. Every\n"
     "     lockout bites in every mode, so a shadow breach halts the copier, every strategy\n"
     "     and (since P1-100) every order the bridge places",
     '            if (state.LockoutWasShadowOnly) return false;',
     '            if (false) return false;'),

    (GUARD,
     "THE WRONG FIX: the shared predicate consults the CURRENT mode instead of the stored\n"
     "     authority. Looks equivalent; it is not. An operator locked out in live escapes by\n"
     "     switching to shadow, which is FR-30 / P1-4's bypass through a different setting",
     '            if (state.LockoutWasShadowOnly) return false;',
     '            if (!IsActingMode()) return false;'),

    (GUARD,
     "the authority sense is INVERTED in the helper: shadow breaches enforce and live breaches\n"
     "     do not. One character, maximally wrong",
     'st.LockoutWasShadowOnly = !IsActingMode();',
     'st.LockoutWasShadowOnly = IsActingMode();'),

    (GUARD,
     "the helper hardcodes 'acting' -- what a hasty revert or a bad merge produces. Shadow\n"
     "     lockouts bite again and nothing else looks different",
     'st.LockoutWasShadowOnly = !IsActingMode();',
     'st.LockoutWasShadowOnly = false;'),

    (GUARD,
     "the helper hardcodes 'shadow only', so a LIVE breach no longer stops trading. Same size\n"
     "     of edit as the mutant above, opposite direction, and this one removes protection from a\n"
     "     funded account",
     'st.LockoutWasShadowOnly = !IsActingMode();',
     'st.LockoutWasShadowOnly = true;'),

    (GUARD,
     "the authority stops being WRITTEN to the persisted state. Nothing fails in memory; it is\n"
     "     lost across every restart, and each restored lockout reads as enforced. That is the\n"
     "     fail-closed direction, so this is the mutant most likely to survive on safety",
     'LockoutWasShadowOnly = state.LockoutWasShadowOnly',
     'LockoutWasShadowOnly = false'),

    (MODELS,
     "the persisted DTO field defaults to TRUE, inverting fail-closed for every state file that\n"
     "     predates it: absence would read as 'shadow only' and RELEASE the lockout. P1-54's lesson\n"
     "     in the other direction",
     # ⚠️ RE-ANCHORED 2026-08-20. This used to end in "\n    }" to pin the DTO's copy of the
     # field rather than AccountState's, by relying on it being the LAST member before the class
     # brace. P1-173 added CooldownUntil after it and the anchor matched zero times -- a battery
     # disarmed by an unrelated field being appended. The bare newline is enough on its own:
     # AccountState's copy reads "{ get; set; } = false;" so it cannot match, and the anchor no
     # longer depends on anything's POSITION. [[mutation-anchors-go-stale]].
     'public bool LockoutWasShadowOnly { get; set; }\n',
     'public bool LockoutWasShadowOnly { get; set; } = true;\n'),

    (GUARD,
     "LockAccount is gated on the mode too -- the cheapest way to satisfy a naive reading of\n"
     "     'gate every lockout site'. A lockout the operator explicitly asked for evaporates in\n"
     "     shadow",
     'state.LockoutWasShadowOnly = false;',
     'state.LockoutWasShadowOnly = !IsActingMode();'),

    (GUARD,
     "LockAccount stops clearing the authority, so a manual lockout on an account that already\n"
     "     breached in SHADOW inherits the shadow authority and is silently ignored. The one\n"
     "     finding the review panel got right out of the four it upheld",
     'state.LockoutWasShadowOnly = false;',
     ''),

    (GUARD,
     "the rehydration path stops restoring the authority. Fail-closed, so it survives on safety,\n"
     "     and it means a restart PROMOTES a shadow observation into an enforced lockout -- a\n"
     "     phantom lockout with no breach behind it",
     'state.LockoutWasShadowOnly = kvp.Value.LockoutWasShadowOnly;',
     ''),

    (GUARD,
     "the SHADOW_LOCKOUT log line goes. Nothing breaks, and the shadow session -- whose whole\n"
     "     purpose is to record what the guard WOULD have done, and which MinShadowSessions gates\n"
     "     arming on -- records nothing. P1-71's class",
     'LogEvent(st.AccountName, "SHADOW_LOCKOUT"',
     'if (false) LogEvent(st.AccountName, "SHADOW_LOCKOUT"'),
]


def run():
    build = subprocess.run(
        ['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if build.returncode != 0:
        return 'BUILD FAILED'
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if not m and '[FAIL]' not in ((res.stdout or '') + (res.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINALS = {p: open(p, encoding='utf-8').read() for p in (GUARD, MODELS)}

print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print('\nREFUSING TO RUN: baseline is RED (%s failing). Every mutant would score KILLED '
          'on pre-existing failures and this battery would prove nothing.' % m.group(2))
    sys.exit(2)

survivors = []
for path, name, old, new in MUTANTS:
    if ORIGINALS[path].count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, ORIGINALS[path].count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(path, 'w', encoding='utf-8', newline='').write(ORIGINALS[path].replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    [open(q, 'w', encoding='utf-8', newline='').write(t) for q, t in ORIGINALS.items()]

[open(q, 'w', encoding='utf-8', newline='').write(t) for q, t in ORIGINALS.items()]
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
