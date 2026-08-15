"""Mutation battery for P2-107: the same repeated-action family as P2-101, on a different path.

⚠️ THE FINDING IS THE SECOND INSTANCE, NOT THE INSTANCE.

P2-101 bounded a lockout retry that could never exit in `shadow`. Within the hour, in that fix's
own validation run and on the first two accounts anyone looked at, the same shape turned up
somewhere else: `PEAK_GIVEBACK_BREACH` re-emitting its flatten on EVERY evaluation --

    10:14:22  Sim-ORB  [SHADOW] Would execute action FlattenPosition triggered by PEAK_GIVEBACK_BREACH
    10:14:25 ... 10:14:32, 10:14:33, 10:14:41, 10:14:42     -- 7 in ~20 seconds

-- driven by account updates rather than a timer, so with no spacing at all and a rate set by
market data. Two instances in one hour is the signal that a bound written INTO each producer is a
bound the sixth producer will not have. So the de-duplication moved to where actions leave the
guard: `GuardActionDeduplicator` behind `DispatchActions`, which all five emission sites now use.

Sixth instance of AN ALARM THAT IS ALWAYS ON IS OFF.

⚠️ The suite was 1436 green BEFORE this change and 1436 green AFTER it, because every existing
test drives one event and a de-duplicator only speaks on the second. Same shape as P1-100's 1355
and P0-96's 1311: a green suite through a behaviour change means the behaviour was never covered.

What each mutant defends. The interesting ones are 5, 6 and 11 -- each is a *plausible* way to
write this that is silently wrong in a direction no single-event test can see:

  * MUTANT 1 restores the shipped defect outright: no budget, everything dispatched, every time.

  * MUTANT 2 is THE PARTIAL FIX: one budget for every mode. The stream stops growing without
    limit -- the visible symptom -- and shadow still emits six identical observations where the
    first one is the entire product. Exactly P2-101's mutant 2, deliberately: the same wrong fix
    is available here and the reader should meet it twice.

  * MUTANT 3 is the fail-DANGEROUS direction: the observing budget for everyone, so a live guard
    gets ONE flatten attempt and cannot retry a broker rejection.

  * MUTANT 4 is the fail-OPEN direction: budget zero. The quietest possible guard, and it never
    acts on anything.

  * MUTANT 5 deletes the clearing pass. Every test that drives a persisting condition still
    passes -- suppression is exactly what they assert -- and the guard goes permanently silent
    about a rule after its first episode. A one-shot mute is not de-duplication.

  * MUTANT 6 drops the PRODUCER from the scope, so one producer's silence clears another's
    record. AccountItemUpdate does not evaluate the lockout rules, so its batches legitimately
    lack their keys; under this mutant nearly every batch clears nearly everything and the whole
    mechanism does nothing -- while passing every test that drives a single producer.

  * MUTANT 7 drops the ACCOUNT from the scope, so two live accounts clear each other on every
    tick and both repeat forever: the measured defect, with one extra step.

  * MUTANT 8 lets a key repeated inside one batch spend an attempt each time, so a three-deep
    batch burns half the live budget before a single retry has happened.

  * MUTANT 9 suppresses in SILENCE. This is the inverse of the defect and it is the one worth
    being afraid of: the operator sees neither the action nor any statement that it was withheld,
    and every count-based assertion about noise gets quieter, not louder.

  * MUTANT 10 announces the suppression every single time, which moves the original defect from
    the action to the line about the action. P2-101's mutant 6 in a new place.

  * MUTANT 11 iterates the accounts that PRODUCED actions instead of the accounts that were
    EVALUATED. This is the natural way to write the loop and it is wrong: an account that
    produced nothing is never filtered, so its record never clears, so mutant 5's failure happens
    per-account instead of globally.

  * MUTANT 12 drops an out-of-scope action instead of dispatching it. It trades a logging defect
    for a risk defect -- a flatten silently discarded because a producer named its scope wrongly.

  * MUTANT 13 routes the operator's panic button through the de-duplicator. Pressing it twice
    then flattens once, because the machinery recognised the second press. An operator repeating
    themselves is not a duplicate.

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


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEDUP = os.path.join(REPO, 'addons', 'GuardActionDeduplicator.cs')
ADDON = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

# (description, target file, find, replace)
MUTANTS = [
    ("the SHIPPED DEFECT: no budget at all, so every evaluation of an unresolved condition\n"
     "     dispatches the action again",
     DEDUP,
     '                    if (record.Attempts >= budget)',
     '                    if (false)'),

    ("THE PARTIAL FIX: one budget for every mode. The stream stops growing without limit --\n"
     "     the visible symptom -- and shadow still emits six identical observations",
     DEDUP,
     '            return isActingMode ? ActingBudget : ObservingBudget;',
     '            return ActingBudget;'),

    ("the fail-DANGEROUS direction: the observing budget for everyone, so a live guard gets one\n"
     "     flatten attempt and cannot retry a broker rejection",
     DEDUP,
     '            return isActingMode ? ActingBudget : ObservingBudget;',
     '            return ObservingBudget;'),

    ("the fail-OPEN direction: budget zero. The quietest possible guard, which acts on nothing",
     DEDUP,
     '            return isActingMode ? ActingBudget : ObservingBudget;',
     '            return 0;'),

    ("the clearing pass is deleted, so a record NEVER clears: the guard goes permanently silent\n"
     "     about a rule after its first episode, and a one-shot mute is not de-duplication",
     DEDUP,
     '                foreach (var key in stale) records.Remove(key);',
     '                foreach (var key in stale) { }'),

    ("the scope loses the PRODUCER, so one producer's silence clears another's record -- and\n"
     "     nearly every batch clears nearly everything while single-producer tests all pass",
     DEDUP,
     '            return (producer ?? "") + ScopeSeparator + (accountName ?? "");',
     '            return (accountName ?? "");'),

    ("the scope loses the ACCOUNT, so two live accounts clear each other on every tick and both\n"
     "     repeat forever: the measured defect with one extra step",
     DEDUP,
     '            return (producer ?? "") + ScopeSeparator + (accountName ?? "");',
     '            return (producer ?? "");'),

    ("a key repeated inside one batch spends an attempt each time, so a three-deep batch burns\n"
     "     half the live budget before a single retry has happened",
     DEDUP,
     '                    if (!seen.Add(key))',
     '                    if (false)'),

    ("suppression in SILENCE -- the inverse of the defect. The operator sees neither the action\n"
     "     nor any statement that it was withheld, and every noise count gets quieter",
     DEDUP,
     '                        decision.AnnounceSuppression = !record.Announced;',
     '                        decision.AnnounceSuppression = false;'),

    ("the suppression is announced EVERY time, moving the original defect from the action to the\n"
     "     line about the action",
     DEDUP,
     '                        record.Announced = true;',
     '                        record.Announced = false;'),

    ("the dispatcher iterates the accounts that PRODUCED actions instead of the accounts that\n"
     "     were EVALUATED -- the natural way to write the loop, and it means an account that\n"
     "     produced nothing is never filtered, so its record never clears",
     ADDON,
     '            foreach (var name in evaluated)\n'
     '            {\n'
     '                List<GuardAction> list;\n'
     '                if (!byAccount.TryGetValue(name, out list)) list = new List<GuardAction>();',
     '            foreach (var name in new List<string>(byAccount.Keys))\n'
     '            {\n'
     '                List<GuardAction> list;\n'
     '                if (!byAccount.TryGetValue(name, out list)) list = new List<GuardAction>();'),

    ("an out-of-scope action is DROPPED instead of dispatched, trading a logging defect for a\n"
     "     risk defect: a flatten silently discarded because a producer named its scope wrongly",
     ADDON,
     '            foreach (var a in unscoped)\n'
     '            {\n'
     '                LogEvent(a.AccountName, "ACTION_UNSCOPED",',
     '            foreach (var a in new List<GuardAction>())\n'
     '            {\n'
     '                LogEvent(a.AccountName, "ACTION_UNSCOPED",'),

    ("the operator's panic button is routed through the de-duplicator, so pressing it twice\n"
     "     flattens once because the machinery recognised the second press",
     ADDON,
     '            return ProcessAction(action, forceLive: true);',
     '            DispatchActions(new List<GuardAction> { action }, "ManualFlatten",\n'
     '                new List<string> { accountName });\n'
     '            return "DISPATCHED";'),

    # -- Added in a SECOND round, because a battery that goes 13/13 on its first run is the
    # -- moment to distrust it, not the moment to stop. Each of these five asks about a part of
    # -- the fix no mutant above touched: the key's own fields, the session reset, the wiring of
    # -- a real event handler, and the account scope the sweep depends on.

    ("the key drops the RULE, so two different rules demanding the same action on one account\n"
     "     collapse into each other and the second rule's breach is never announced at all",
     DEDUP,
     '            return (accountName ?? "") + "|" + (ruleId ?? "") + "|"\n'
     '                 + (actionType ?? "") + "|" + (instrument ?? "");',
     '            return (accountName ?? "") + "|"\n'
     '                 + (actionType ?? "") + "|" + (instrument ?? "");'),

    ("the key drops the ACTION TYPE, so a flatten and an order-cancel for one account and rule\n"
     "     are the same demand, and whichever arrives second is silently withheld",
     DEDUP,
     '            return (accountName ?? "") + "|" + (ruleId ?? "") + "|"\n'
     '                 + (actionType ?? "") + "|" + (instrument ?? "");',
     '            return (accountName ?? "") + "|" + (ruleId ?? "") + "|"\n'
     '                 + (instrument ?? "");'),

    ("the daily session reset stops clearing the records, so a suppression is carried across the\n"
     "     session boundary and the rule fires on the new day saying nothing",
     ADDON,
     '                        _actionDedup.ClearAccount(accName);',
     '                        if (false) _actionDedup.ClearAccount(accName);'),

    ("THE P3-30 SHAPE: the machinery is all there and the AccountItemUpdate handler -- the very\n"
     "     path the defect was measured on -- goes back to dispatching around it. Everything that\n"
     "     tests DispatchActions directly still passes",
     ADDON,
     '                if (actions != null)\n'
     '                    DispatchActions(actions, "AccountItemUpdate", new List<string> { accountName });',
     '                if (actions != null)\n'
     '                    foreach (var a in CoalesceActions(actions)) ProcessAction(a);'),

    ("the account-wide producers declare an EMPTY evaluated scope, so the sweep and aggregate\n"
     "     sizing bypass de-duplication entirely through the fail-open path",
     ADDON,
     '            var names = new List<string>();\n'
     '            lock (_stateLock)',
     '            var names = new List<string>();\n'
     '            if (names != null) return names;\n'
     '            lock (_stateLock)'),
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


ORIGINALS = {path: open(path, encoding='utf-8').read() for path in (DEDUP, ADDON)}


def restore():
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


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
for name, path, old, new in MUTANTS:
    original = ORIGINALS[path]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(path, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
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

# The plain exit, not _battery.finish: this battery declares NO expected survivor, and
# check_expected_survivors.py requires the plain form in that case. Reaching for the helper
# "just in case" would let a future EXPECTED SURVIVOR: marker be added with nothing forcing a
# second look at whether the declaration is honest.
if survivors:
    print('\nSURVIVORS (%d):' % len(survivors))
    for s in survivors:
        print('  * ' + s)
    print('\n  No test can tell these mutants from the real code. Write one, or declare the\n'
          '  mutant EXPECTED SURVIVOR: with the reason no test can reach it.')
else:
    print('\nSURVIVORS: none -- all %d mutants died.' % len(MUTANTS))
sys.exit(1 if survivors else 0)
