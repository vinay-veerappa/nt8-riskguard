"""Mutation battery for P2-134: the give-up line repeated forever, and guessed its own cause.

MEASURED LIVE 2026-08-16, four identical lines in twenty seconds --

    19:56:03  ATM_STOP_MOVE_ABANDONED  15bc730b: 3 consecutive stop moves were refused by the
                                       provider; not asking again for this bracket.
    19:56:13  (same)   19:56:18  (same)   19:56:23  (same)

-- from a line whose own text promises it will not recur. The attempt COUNTER was correctly
capped (that half is P1-130 working); it is the ANNOUNCEMENT that sat on the path every sweep
takes. Ninth instance of *an alarm that is always on is off*.

Second half: `StopModifyAttempts` is spent by TWO different failures -- `RequestStopMove` when
`ModifyStopPrice` found no live order (the provider was never asked, nothing was submitted) and
`ReconcileStopFromBroker` when a move WAS sent and the provider is not holding it (a genuine
refusal). The text asserted the second for both, and the ABSENT and TERMINAL cases produced
byte-identical messages.

⚠️ GROUPS 2 AND 3 ARE THE ONES TO KNOW.

Group 2 attacks the SCOPE. A suppression is worthless if it is wider than the thing it
describes: a static latch, or one keyed by account, silences the give-up line for every position
after the first, and every single-bracket test still passes. That is P2-107's producer-scope
lesson at a second site.

Group 3 attacks the EVIDENCE. Two of these mutate the TESTS, because the suppression assertions
are the kind that pass when the subject disappears: "exactly once" is satisfied by never, and
"the two messages differ" is satisfied by two different constants. If the positive controls can
be deleted without the suite noticing, the tests are decoration.

⚠️ THIS BATTERY USED TO SAY A LATCH CLEAR WAS DELIBERATELY NOT MUTATED BECAUSE IT COULD NOT
EXIST. That was wrong, and the correction is the most useful thing here. The claim was: past the
cap `RequestStopMove` returns before it asks, a confirm needs an outstanding request, and the
counter resets only on a confirm -- so abandonment is permanent for a bracket and a clear would
be a line that can never run. **The step it missed:** the `CHANGE_IGNORED` branch does not clear
`RequestedStopPrice`, so the request stays OUTSTANDING after the budget is spent, and a provider
that honours it late is confirmed on a later sweep with **no new `RequestStopMove` call at all**.
The clear exists as of P2-135 and `mutate_p2135.py` carries the mutant for it.

The lesson is not about this latch. **An argument that a line can never run is exactly the
argument to check by naming the input that runs it** -- and if you cannot, that is a finding
either way. [[a-green-that-can-never-be-red]] inverted.

A crash counts as a kill (handover section 5.14).

⚠️ TWO OF THESE DIE AS `NO RESULT LINE`, WHICH IS AN OPAQUE KILL, so it was reproduced by hand
rather than accepted. Applying the `if (false)` mutant on its own prints, first and by name:

    [FAIL] P2-134: the bracket IS abandoned and does say so (positive control -- got 0
           ATM_STOP_MOVE_ABANDONED lines across 20 sweeps)

-- so the positive controls are what catch it, which is the thing this battery is here to prove.
The run then fails hard enough not to reach its RESULTS line. **A kill you cannot explain is not
evidence; re-drive it until you can name the assertion that fired.**

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')
TESTS = os.path.join(REPO, 'tests', 'RiskGuardAddOnTests.cs')

MUTANTS = [
    # ---- group 1: the suppression itself -------------------------------------------------------
    (ATM,
     "⚠️ THE DEFECT, RESTORED IN ONE LINE: the latch is never consulted, so the give-up line\n"
     "     goes back onto the path every sweep takes. 17 lines across 20 sweeps in the suite,\n"
     "     four in twenty seconds live, from a message that says it will not repeat",
     '            if (bracket.StopMoveAbandonAnnounced)\n                return;',
     '            if (false)\n                return;'),

    (ATM,
     "the latch is READ but never SET, which is the same defect one statement later and is\n"
     "     the shape a careless edit produces. The first sweep's announcement no longer records\n"
     "     itself, so every subsequent sweep believes it is the first",
     '            bracket.StopMoveAbandonAnnounced = true;',
     '            bracket.StopMoveAbandonAnnounced = false;'),

    (ATM,
     "the suppression swallows the RETURN as well as the log, so a bracket past its budget\n"
     "     starts asking again -- the announcement is quiet AND the bound is gone. This is the\n"
     "     mutant that proves the fix suppressed only the logging",
     '                return false;\n'
     '            }\n'
     '\n'
     '            // P1-130. EVERY failed request spends the budget',
     '                return bracket.StopMoveAbandonAnnounced;\n'
     '            }\n'
     '\n'
     '            // P1-130. EVERY failed request spends the budget'),

    # ---- group 2: the SCOPE, which is where a suppression turns into deletion -------------------
    (ATM,
     "⚠️ THE LATCH GOES STATIC: one bracket's announcement silences every other bracket on\n"
     "     the box. The operator is told once, ever, that trailing died -- and the next position\n"
     "     fails in silence. P2-107's producer-scope lesson at a second site",
     '        public bool StopMoveAbandonAnnounced { get; set; }',
     '        private static bool _sharedAnnounced;\n'
     '        public bool StopMoveAbandonAnnounced { get { return _sharedAnnounced; } set { _sharedAnnounced = value; } }'),

    # ---- group 3: the reason, which must be OBSERVED rather than inferred -----------------------
    (ATM,
     "the message goes back to ASSERTING a cause: 'refused by the provider' on a path where\n"
     "     nothing was ever submitted. The counter is shared with the one failure where a refusal\n"
     "     really did happen, and this is the assumption that made the two indistinguishable",
     '{MaxStopModifyAttempts} stop moves failed, last observed "',
     '{MaxStopModifyAttempts} consecutive stop moves were refused by the provider. Last: "'),

    (ATM,
     "the ABSENT and TERMINAL failures record the SAME reason, so the give-up line reports a\n"
     "     constant again. The two situations are not the same news -- that is the whole content\n"
     "     of P1-130 -- and this collapses them one layer below the message",
     "                    failureReason = $\"the stop order '{orderName}' is {present.OrderState} and no longer live\";",
     "                    failureReason = $\"no order with name '{orderName}' is on '{account.Name}' at all\";"),

    (ATM,
     "the reason is recorded but never READ -- the give-up line stops quoting it. A value\n"
     "     that is COMPUTED is not a value that is USED, and four mutants have already beaten a\n"
     "     source gate on exactly that distinction",
     '+ $"reason: {bracket.LastStopMoveFailureReason ?? "not recorded"}. Not asking again for this "',
     '+ $"reason: unknown. Not asking again for this "'),

    (ATM,
     "the REFUSAL path stops recording its reason, so a move the provider genuinely declined\n"
     "     is reported with whatever ModifyStopPrice last said -- or 'not recorded'. The one\n"
     "     failure where 'refused' is TRUE is the one that loses its name",
     '                    bracket.LastStopMoveFailureReason = $"provider holds {brokerPrice} instead of requested {requested}";',
     '                    bracket.LastStopMoveFailureReason = bracket.LastStopMoveFailureReason;'),

    (ATM,
     "the null fallback goes away, so a bracket restored from the bridge payload carrying a\n"
     "     count but no reason prints 'last observed reason: .' -- a well-formed sentence that\n"
     "     reads as a fact about the failure rather than as a gap in what we recorded",
     '{bracket.LastStopMoveFailureReason ?? "not recorded"}',
     '{bracket.LastStopMoveFailureReason}'),

    # ---- group 4: the EVIDENCE -- do the tests still assert anything? ---------------------------
    (ATM,
     "⚠️ THE ANNOUNCEMENT IS SWALLOWED ENTIRELY -- the over-correction, and the failure\n"
     "     direction that is WORSE than the defect: the trail has stopped and the operator is\n"
     "     never told. This is what the positive controls in all three tests are for, so if it\n"
     "     survives, 'exactly once' is being satisfied by never",
     '            RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_MOVE_ABANDONED",',
     '            if (false) RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_MOVE_ABANDONED",'),

    (ATM,
     "the latch is keyed by ACCOUNT rather than by bracket, which is the realistic version of\n"
     "     the static mutant above -- one give-up line per account, ever. The next position on\n"
     "     that account fails in silence, and every single-bracket test still passes",
     '        public bool StopMoveAbandonAnnounced { get; set; }',
     '        private static readonly System.Collections.Generic.Dictionary<string, bool> _perAccountAnnounced = new System.Collections.Generic.Dictionary<string, bool>();\n'
     '        public bool StopMoveAbandonAnnounced\n'
     '        {\n'
     '            get { bool v; return _perAccountAnnounced.TryGetValue(AccountName ?? "", out v) && v; }\n'
     '            set { _perAccountAnnounced[AccountName ?? ""] = value; }\n'
     '        }'),
]

# ⚠️ TWO MUTANTS WERE REMOVED FROM THIS LIST RATHER THAN CHASED, and the reason is worth keeping.
# Both survived the first run and NEITHER was a missing test:
#
#   * one weakened a test's own positive control (`abandoned >= 1` -> `>= 0`). A mutant that makes
#     an assertion LOOSER cannot fail a suite whose code is correct -- it is unkillable by
#     construction. The way to prove a positive control is load-bearing is to break the CODE it
#     guards, which is what the `if (false)` mutant above now does.
#   * one gave two brackets the same BracketId, described as "the test can no longer tell a scoped
#     suppression from a global one". It does not: `AddBracketForTest` keys by id, so the second
#     bracket REPLACES the first, arrives with its own fresh latch, and announces -- the count is
#     still 2 and nothing about scope was expressed. Replaced by the account-keyed mutant above.
#
# Third and fourth instance of P1-99's lesson: **read what a surviving mutant DOES before
# concluding a test is missing.**

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


def run():
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'tests/RiskGuardTests.csproj', '--nologo', '-v', 'q'],
        cwd=REPO, capture_output=True, text=True,
        encoding='utf-8', errors='replace')
    if 'error CS' in (res.stdout + res.stderr):
        return 'BUILD FAILED'
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    return m.group(0) if m else 'NO RESULT LINE'


print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('baseline did not produce a result line; refusing to run')
    sys.exit(2)
if int(m.group(2)) != 0:
    print('baseline is RED; a battery against a red baseline scores nothing')
    sys.exit(2)

survivors = []
print('\n=== mutants ===')

for target, name, old, new in MUTANTS:
    original = ORIGINALS[target]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    restore()

restore()
print('\nrestored originals;', run())

print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
