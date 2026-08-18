"""Mutation battery for P2-108: the audit findings that repeated every 10 seconds, forever.

MEASURED ON THE DEPLOYED BOX under Market Replay, 2026-08-15 -- one position with no stop,
guard in `shadow`, sampled every 30s:

    t+30s   NAKED_POSITION=3    ACTION_SUPPRESSED=0
    t+60s   NAKED_POSITION=6    ACTION_SUPPRESSED=0
    t+90s   NAKED_POSITION=9    ACTION_SUPPRESSED=0
    t+120s  NAKED_POSITION=12   ACTION_SUPPRESSED=0

Perfectly linear, one per 10s, indefinitely. 12-in-120s is the exact figure the ticket was filed
with, reproduced a session later on a different account.

⚠️ `ACTION_SUPPRESSED = 0` is the load-bearing number: `P2-107`'s GuardActionDeduplicator cannot
help, because these are `LogEvent` calls with no action behind them, on a path `DispatchActions`
never sees. The zero PROVES that rather than assuming it.

⚠️ AND THE CLASS IS BIGGER THAN THE TICKET: the audit emits THREE findings from one loop on one
timer -- NAKED_POSITION, ORPHAN_STOP, FSM_DIVERGENCE -- all unbounded. Mutant 8 is the source gate
that keeps all three routed.

What each mutant defends:

  * MUTANT 1 IS THE SHIPPED DEFECT: Admit returns everything fired, so the throttle does nothing
    and the log goes back to one line per finding per pass, forever.

  * MUTANT 2 caches the acting budget, so `shadow` gets 6 lines instead of 1. Looks like a
    simplification; it is a 6x regression of the measured defect.

  * MUTANT 3 clears records for every key NOT fired, rather than for evaluated-and-not-fired. A
    pass that examined nothing -- a disconnected account, a connection blip -- then re-admits the
    entire backlog. The defect returning through the door marked recovery.

  * MUTANT 4 drops the finding type from the key, so NAKED_POSITION resolving clears ORPHAN_STOP's
    record for the same instrument and the throttle does NOTHING -- while every single-finding test
    still passes. `P2-107`'s producer-scope lesson verbatim.

  * MUTANT 5 never clears the record, so once a finding is suppressed it stays suppressed for the
    life of the process. THE OPPOSITE DEFECT and the more dangerous one: attach a stop, take a new
    naked position, and the alarm that exists to tell you never speaks again. *An alarm that is
    always on is off* -- and so is one that is permanently muted.

  * MUTANT 6 is the off-by-one: `count <= budget` admits one more line than the budget says.

  * MUTANT 7 makes FirstSuppression always false, so the log goes quiet with NO announcement. The
    operator cannot tell "resolved" from "still true and no longer mentioned", which is the
    screaming-alarm defect inverted rather than fixed.

  * MUTANT 8 is the SOURCE gate: a finding logged inline from inside the audit loop, bypassing the
    throttle entirely. That is how the defect was written in the first place.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# ⚠️ THE BATTERY'S OWN STDOUT, not the child's. `check_batteries_pin_encoding.py` made every
# battery pin an encoding on the SUBPROCESS capture, because cp1252 there returned None and killed
# the run before its first mutant. This is the other half and it bit immediately: a non-ASCII
# character in a MUTANT DESCRIPTION raised UnicodeEncodeError inside `print()` on a cp1252 console
# -- and it raised BETWEEN applying the mutant and restoring it, so it left a LIVE MUTANT in
# AuditFindingThrottle.cs. A `git diff` did not show it, because the file was still untracked.
#
# That is the *a killed battery leaves a mutant* hazard arriving through a path nobody chose: the
# battery was not stopped by hand, it died printing its own output. Re-run the suite after any
# battery that does not reach its restore line.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

THROTTLE = os.path.join(REPO, 'addons', 'AuditFindingThrottle.cs')
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    (THROTTLE,
     "THE SHIPPED DEFECT: the throttle admits everything, so the log goes back to one line per\n"
     "     finding per pass -- 12 in 120 seconds, forever, which is what was measured",
     '                if (count < budget)\n'
     '                {\n'
     '                    _emitted[key] = count + 1;\n'
     '                    admitted.Add(key);\n'
     '                }',
     '                {\n'
     '                    _emitted[key] = count + 1;\n'
     '                    admitted.Add(key);\n'
     '                }'),

    (THROTTLE,
     "the budget ignores the mode and always allows 6, so `shadow` -- where the guard's whole\n"
     "     product is ONE observation -- logs six lines per finding instead of one",
     '            return isActingMode ? ActingBudget : ObservingBudget;',
     '            return ActingBudget;'),

    (THROTTLE,
     "the ACCOUNT scope is dropped from the clearing rule, so records clear for every key not\n"
     "     fired regardless of whether its account was examined -- a pass that examined NOTHING\n"
     "     then re-admits the whole backlog, the defect returning through the door marked recovery",
     '                         .Where(k => examined.Contains(AccountOf(k)) && !firedSet.Contains(k))',
     '                         .Where(k => !firedSet.Contains(k))'),

    (THROTTLE,
     "⚠️ THE DEFECT THE SUITE COULD NOT SEE AND THE DEPLOYED BOX DID. AccountOf reads the wrong\n"
     "     key segment, so no examined account ever matches and NOTHING is ever cleared: the\n"
     "     alarm mutes itself permanently the first time it is suppressed. This shipped as\n"
     "     `evaluatedKeys` -- keys built from OPEN positions -- so a position CLOSING, the\n"
     "     commonest way a naked position resolves, left the record forever. 8 unit tests and\n"
     "     8/8 mutants passed under it; closing and re-opening a position on the box did not",
     '            return parts.Length >= 2 ? parts[1] : string.Empty;',
     '            return parts.Length >= 3 ? parts[2] : string.Empty;'),

    (THROTTLE,
     "the key drops the FINDING TYPE, so NAKED_POSITION resolving clears ORPHAN_STOP's record\n"
     "     for the same instrument and the throttle does nothing -- while every single-finding\n"
     "     test still passes (P2-107's producer-scope lesson)",
     '            return (findingType ?? "?") + "|" + (account ?? "?") + "|" + (instrument ?? "?");',
     '            return (account ?? "?") + "|" + (instrument ?? "?");'),

    (THROTTLE,
     "the record is NEVER cleared, so a finding suppressed once stays suppressed for the life\n"
     "     of the process. THE OPPOSITE DEFECT: attach a stop, take a new naked position, and the\n"
     "     alarm that exists to tell you never speaks again",
     '                _emitted.Remove(key);\n                _announcedSuppression.Remove(key);',
     '                _announcedSuppression.Remove(key);'),

    (THROTTLE,
     "the off-by-one: `count <= budget` admits one more line than the budget states",
     '                if (count < budget)',
     '                if (count <= budget)'),

    (THROTTLE,
     "FirstSuppression never fires, so the log goes quiet with NO announcement and the operator\n"
     "     cannot tell 'resolved' from 'still true and no longer mentioned' -- the screaming-alarm\n"
     "     defect inverted rather than fixed",
     '            return _announcedSuppression.Add(key);',
     '            return false;'),

    (GUARD,
     "a finding is logged INLINE from inside the audit loop, bypassing the throttle entirely --\n"
     "     which is exactly how this defect was written the first time (SOURCE gate)",
     '                            firedKeys.Add(nakedKey);',
     '                            LogEvent(accountName, "NAKED_POSITION", "inline");\n'
     '                            firedKeys.Add(nakedKey);'),
]

ORIGINALS = {}
for _t, _, _, _ in MUTANTS:
    if _t not in ORIGINALS:
        ORIGINALS[_t] = open(_t, encoding='utf-8').read()


def restore():
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


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
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
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
