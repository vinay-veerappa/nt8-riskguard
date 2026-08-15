"""Mutation battery for P1-100: a SHADOW-only lockout blocked real orders.

⚠️ THIS ONE FROZE AN ACCOUNT IN THE MODE THAT EXISTS TO TOUCH NOTHING.

Measured on the deployed box 2026-08-14. Guard armed, in `shadow`. A 100-lot MNQ entry tripped
MAX_SIZE_BREACH and DAILY_LOSS_BREACH; both logged `SHADOW_LOCKOUT ... no flatten executed` and
nothing was flattened -- P2-92 working exactly as designed. Then every order was refused:

    nt_place_order Sim101 MNQ Sell 100 Market      -> "Order blocked: Account Sim101 is locked out."
    nt_place_order Sim101 MNQ Buy 1 Limit @ 20000  -> "Order blocked: Account Sim101 is locked out."

The second probe is the evidence: a limit 10,000 points from the market can never fill, so nothing
about that ORDER is risky. The ACCOUNT was gated. It fails closed, which is the right direction to
fail -- but `shadow` is what an operator is told to evaluate the guard in, and an operator whose
account freezes during evaluation switches the guard off.

`CanTrade` was correct. The bridge's three order paths (PlaceOrder, PlaceOcoOrder, PlaceAtmOrder)
and GET /api/lockout ask `RiskGuardAddOn.IsAccountLocked`, which returned the RAW `IsLockedOut`
flag. Neither P2-92's authority test nor P2-94's deadline test had ever reached it: both landed in
CanTrade, and nothing compared the two readers. So it was wrong in BOTH directions -- it refused on
a shadow observation, and it reported "free to trade" for the whole 60 minutes of a TIMED manual
lockout, which is P2-94 verbatim surviving at a second reader nine days after P2-94 was closed.

⚠️ The entire suite -- 1355 tests -- stayed green through the fix. Every test that touched this set
`IsLockedOut = true` directly, and that is the one combination where all three readers agree.
P1-90's shape: state fixed in one place and read in several.

The fix is a single predicate, `LockoutBinds`, with every reader calling it and none re-deriving it.

What each mutant defends:

  * MUTANT 1 restores the shipped defect -- IsAccountLocked returns the raw flag again. Killed by
    the shadow test AND the timed-manual test, i.e. in both of the directions it was wrong.

  * MUTANT 2 drops the deadline half of the lockout test: P2-94 regressed, same reasoning.

  * MUTANT 3 drops the disarmed-bypass clause, so a lockout binds through a disarm even for an
    account explicitly listed for bypass -- and, worse, the bridge would refuse an order the
    guard's own gate had just decided to allow. That silent disagreement is the whole defect.

  * MUTANT 4 points the entry-cancel block in OnOrderUpdate back at the raw flag. DrainPendingCancels
    withholds the broker call in shadow (P0-51), so nothing is actually cancelled -- the observable
    is the LOG: `ENTRY_CANCEL: Cancelled order N because account is locked out` written into
    interventions.jsonl for an order nobody touched. Killed only by a test that observes LogEvent.

⚠️ The two mutants you would expect to find here -- deleting the shadow-authority clause, and the
WRONG FIX that keys it on the current mode instead -- live in `mutate_p292.py`, whose anchors were
REPOINTED at `LockoutBinds` when P1-100 extracted it. The invariant is P2-92's; only its address
changed. Duplicating them here would mean two batteries to update the next time it moves, and one
of them would eventually be the stale one.

A crash counts as a kill (handover section 5.14).
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


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ADDON = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    ("the SHIPPED DEFECT: IsAccountLocked returns the RAW IsLockedOut flag again, so the bridge's\n"
     "     order paths refuse on a shadow observation and admit orders during a timed lockout",
     '                return LockoutBinds(accountName);',
     '                if (_accountStates.TryGetValue(accountName, out var raw)) return raw.IsLockedOut;\n'
     '                return false;'),

    ("P2-94 regressed at the shared predicate: the DEADLINE half of the lockout test is gone, so a\n"
     "     timed manual lockout stops refusing anything while the sweep flattens the fills",
     '            bool underLockout = state.IsLockedOut\n'
     '                || (state.LockoutUntil > DateTime.MinValue && DateTime.UtcNow < state.LockoutUntil);',
     '            bool underLockout = state.IsLockedOut;'),

    ("the disarmed-BYPASS clause is dropped, so the bridge refuses an order the guard's own gate\n"
     "     has just decided to allow -- the silent disagreement this whole entry is about",
     '            return !bypassAllowed;',
     '            return true;'),

    ("the entry-cancel block in OnOrderUpdate reads the raw flag again, writing\n"
     "     `ENTRY_CANCEL: Cancelled order N` into the audit record for an order shadow mode never\n"
     "     touched. The observable is the LOG, not the order state",
     '                        if (LockoutBinds(accountName, stateModel)',
     '                        if (stateModel.IsLockedOut'),
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
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINAL = open(ADDON, encoding='utf-8').read()

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
for name, old, new in MUTANTS:
    if ORIGINAL.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, ORIGINAL.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(ADDON, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(ADDON, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(ADDON, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')
sys.exit(1 if survivors else 0)
