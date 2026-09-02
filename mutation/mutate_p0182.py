"""Mutation battery for P0-182 (a stale execution reset the session state BACKWARD,
ping-ponging 44+ times in one second and wedging NT8's UI thread).

The defect: `RiskManagerAddOn.OnExecutionUpdate` called `RiskGatekeeper.ResetDay` on
EVERY execution event whenever the stored TradingDate differed from the fill's date.
No monotonic guard, so a replayed/stale fill dated the day BEFORE the stored state
moved the state BACKWARD (9/1 -> 8/31), and the next current-dated event moved it
forward again. Caught live 2026-09-01 on the firm-boundary rollover (22:00 UTC) when
account re-subscription replayed historical fills against LFE02559938020006.

The fix routes the decision through `SessionResetGate` (addons/SessionResetGate.cs):
forward applies, same-day is a no-op, backward is refused. These mutants each
re-introduce a way for a stale date to damage the session state;
`TestSessionResetGate_*` must kill every one.

  * MUTANT 1 makes the gate ACCEPT a backward move (the exact live defect: the
    monotonic guard is gone). The backward-leg assertions fail.

  * MUTANT 2 makes the gate apply a reset on SAME-day events too -- every ordinary
    fill wipes the session counters. The same-day-noop assertions fail.

  * MUTANT 3 reports the wrong EffectiveDate on the refusal -- the state would move
    to the STALE date even though Apply is false if a caller ever trusted the field.
    The refused-leg EffectiveDate assertions fail.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GATE = os.path.join(REPO, 'addons', 'SessionResetGate.cs')

MUTANTS = [
    # ---- MUTANT 1: the exact live defect -- backward dates accepted ----
    (GATE,
     "the gate accepts a BACKWARD date (monotonic guard removed) -- the P0-182 live defect, verbatim",
     '            if (eventDate.Date > storedDate.Date)\n'
     '            {',
     '            if (eventDate.Date > storedDate.Date || eventDate.Date < storedDate.Date)\n'
     '            {'),

    # ---- MUTANT 2: same-day events also trigger a reset (counter wipe on every fill) ----
    (GATE,
     "a same-day re-detect APPLIES a reset, so every ordinary fill wipes the session counters",
     '            if (eventDate.Date == storedDate.Date)\n'
     '            {\n'
     '                // A same-day re-detect is a benign no-op: nothing changes, no reset, no save.\n'
     '                d.Apply         = false;',
     '            if (eventDate.Date == storedDate.Date)\n'
     '            {\n'
     '                // A same-day re-detect is a benign no-op: nothing changes, no reset, no save.\n'
     '                d.Apply         = true;'),

    # ---- MUTANT 3: the refusal reports the STALE date as the effective one ----
    (GATE,
     "the refusal reports the STALE event date as EffectiveDate, so a trusting caller moves the\n"
     "     state backward anyway",
     '            // eventDate < storedDate: a stale/replayed event. Refuse; the caller drops it.\n'
     '            d.Apply         = false;\n'
     '            d.Reason        = "stale-date-refused";\n'
     '            d.EffectiveDate = storedDate.Date;',
     '            // eventDate < storedDate: a stale/replayed event. Refuse; the caller drops it.\n'
     '            d.Apply         = false;\n'
     '            d.Reason        = "stale-date-refused";\n'
     '            d.EffectiveDate = eventDate.Date;'),
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
    # P2-148: a crash is NOT a detection. Require at least one [FAIL] before a missing
    # result line is scored a kill.
    if not m and '[FAIL]' not in ((res.stdout or '') + (res.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINALS = {path: open(path, encoding='utf-8').read() for path in (GATE,)}

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
    original = ORIGINALS[path]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(path, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    killed = _battery.score(res, run)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(path, 'w', encoding='utf-8', newline='').write(original)

for path, original in ORIGINALS.items():
    open(path, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored originals;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)