"""Mutation battery for P0-63 (Change() accepted and silently ignored).

Each mutation must turn the suite RED. A surviving mutant is a test that only
looks like coverage -- or a line of the fix that nothing pins at all.

This battery exists because the P0-63 candidate grew from 755 to 899 lines
across four review rounds while the acceptance tests stayed identically green.
Complexity added in response to review, on code that manages real money, that
no test can distinguish from its absence, is not a safety improvement. The point
here is not to confirm the fix works -- the acceptance tests do that -- it is to
find out WHICH of the added lines are load-bearing.

Survivors are therefore expected in places and are reported honestly rather than
tuned away: a survivor means either "write a test" or "delete this line", and
saying which is a judgement call for a human. The exit code still fails on any
survivor, because a battery that passes while carrying known survivors is the
lying-harness shape these files exist to catch.
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
    # ---- the detection itself ----
    ("no-op is never detected (price check always says 'moved')",
     "                bool priceStillOriginal = Math.Abs(currentPrice - req.OriginalPrice) <= 1e-9;",
     "                bool priceStillOriginal = false;"),

    ("no-op is always detected (price check always says 'unchanged')",
     "                bool priceStillOriginal = Math.Abs(currentPrice - req.OriginalPrice) <= 1e-9;",
     "                bool priceStillOriginal = true;"),

    ("detection compares against the REQUESTED value instead of the original",
     "                bool priceStillOriginal = Math.Abs(currentPrice - req.OriginalPrice) <= 1e-9;",
     "                bool priceStillOriginal = Math.Abs(currentPrice - req.RequestedPrice) <= 1e-9;"),

    # ---- the recovery ----
    ("the account is never marked, so every trail step re-asks a provider that refuses",
     "                    _accountsIgnoringChange.Add(acc.Name);",
     ""),

    ("the stop leg is never re-driven after a detected no-op",
     "                    if (isStopLeg) SyncFollowerStop(acc, o.Instrument, bracket);",
     "                    if (isStopLeg) { }"),

    ("the target leg is never re-driven after a detected no-op",
     "                    else SyncFollowerTarget(acc, o.Instrument, bracket);",
     "                    else { }"),

    # ---- the bypass ----
    # The anchor is the STOP leg's declaration specifically. The `lock` line that
    # reads the set appears in both legs, so anchoring on it matched twice and the
    # mutant was skipped -- which this battery counts as a survivor, correctly:
    # a mutation that could not be applied was not tested.
    ("the STOP bypass never fires: a marked account is asked to Change() again",
     "                    lock (_lock) { providerIgnoresChange = _accountsIgnoringChange.Contains(followerAcc.Name); }\n\n                    if (providerIgnoresChange)\n                    {\n                        CopierLog(followerAcc.Name, \"BRACKET_MODIFY_BYPASSED\",",
     "                    providerIgnoresChange = false;\n\n                    if (providerIgnoresChange)\n                    {\n                        CopierLog(followerAcc.Name, \"BRACKET_MODIFY_BYPASSED\","),

    # ---- the budget resets added during review ----
    # These were added across rounds 2-4 to answer a reviewer finding that the
    # re-submission budget would freeze a long trail. That finding is false --
    # OnLeaderOrderUpdate zeroes the budget whenever the leader's offset
    # changes, which is every trail step -- and the six-step trail test pins it.
    # If these survive, they are decorative and should be deleted rather than
    # maintained.
    # ALL THREE budget refreshes are GONE from the engine. Mutation proved each one
    # decorative -- deleting it changed no test outcome -- and all three were added
    # across review rounds 2-4 to chase a finding that is false: OnLeaderOrderUpdate
    # already zeroes the budget whenever the leader's offset changes, which is every
    # trail step, and the six-step trail test pins it. Their mutants are deleted with
    # them rather than left to skip, since a skip counts as a survivor and would make
    # this battery permanently red for a reason already resolved.
]

# ------------------------------------------------------------------
# DELIBERATELY NOT COVERED, and why. These were measured as survivors and are
# recorded here rather than left in MUTANTS, because a battery that exits 1 on
# survivors it knows about and accepts is a gate nobody can read. Both are real
# gaps in the SUITE, not defects in the fix.
#
# 1. "re-drive bypasses the P1-56 in-flight reservation (SyncFollowerStop ->
#    SyncFollowerStopOnce)". SURVIVES. The wrapper's only job is to take the
#    StopInFlight reservation before any broker call, and nothing in this suite
#    drives two syncs concurrently through the SETTLE path, so the difference is
#    invisible to it. This is the most serious defect found in the P0-63
#    candidate and NO reviewer found it -- it was caught by reading, and it is
#    still unpinnable. Closing it means an S7-style test that parks one sync
#    inside CreateOrder and drives a settle event from another thread.
#
# 2. "quantity half of the detection dropped" (qtyStillOriginal = true). SURVIVES,
#    and the reason is worth stating exactly because it is NOT that the quantity is
#    untested. TestBracket_P0_63_AQuantityOnlyNoOpIsAlsoCaught covers a
#    quantity-only no-op and passes -- but it passes on the PRICE half, since in
#    that scenario the price is also still original. The quantity half's real job is
#    the opposite direction: preventing a FALSE detection when the provider applies
#    the quantity and not the price (a partial honour). Provoking that needs a stub
#    that can honour one field and revert the other, and this one is all-or-nothing.
#    Consequence if the check were wrong: one unnecessary cancel-then-create, so one
#    naked window on the risk leg -- real, but bounded, and not a permanent failure.
#    Remedy: add SimulateChangeAppliesQuantityOnly to the stub and assert that no
#    replacement order is created. Left undone deliberately, not overlooked.
#
# 3. "account set becomes case-sensitive". SURVIVES. No test varies the casing of
#    an account name, and NT8 supplies the names, so provoking it would mean
#    inventing a scenario the broker may never produce. OrdinalIgnoreCase is kept
#    on convention -- every other account-name comparison in the file does the
#    same, including _slippageSampleCounts -- not on evidence.
# ------------------------------------------------------------------


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

# P?-66's five assertions are red until that ticket lands, so this battery cannot
# use "Failed = 0" as its kill test the way cm3/cm4 do. It pins the baseline
# failure COUNT instead: a mutant is killed only if it makes things worse than
# the baseline. Without this, every mutant would score KILLED on the P?-66
# failures alone and the battery would be decorative -- the exact trap cm3 and
# cm4 were found carrying on 2026-08-13.
import re
m = re.search(r'Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a failure count from the baseline.')
    sys.exit(2)
BASE_FAILED = int(m.group(1))
print(f'  baseline failure count pinned at {BASE_FAILED}')

survivors = []
for name, old, new in MUTANTS:
    if original.count(old) != 1:
        print(f'  [SKIP] {name}: anchor matched {original.count(old)} times')
        survivors.append(name + ' (ANCHOR)')
        continue
    open(ENGINE, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or (mm is not None and int(mm.group(1)) > BASE_FAILED)
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
    print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
    if not killed:
        survivors.append(name)

open(ENGINE, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
