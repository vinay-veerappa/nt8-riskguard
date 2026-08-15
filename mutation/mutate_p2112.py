"""Mutation battery for P2-112: the ATM breakeven monitor that silently never ran.

WHAT WAS WRONG:

    private void MonitorTick(object _)
        var dispatcher = System.Windows.Application.Current?.Dispatcher;
        if (dispatcher == null) return;              <-- forever

`P1-13`'s fail-open verbatim, at a subsystem `P1-13` never inspected, on the 5-second loop that
moves breakeven stops and advances trailing stops. With no dispatcher the sweep returned
immediately for the life of the process: stops never moved, refused moves were never detected,
and nothing logged a word.

WHY IT SURVIVED AS LONG AS IT DID, and the thing the first two mutants are really about: the whole
dispatch decision sat behind `#if TESTING`, so the branch holding the defect existed in NO test
build. The ten existing ATM tests drove `MonitorTickCore()` -- a body the shipped assembly does not
contain. That is `P2-27`'s shape, and it means a battery that only mutates behaviour would miss the
class. Mutant 1 restores the shipped shape; mutant 2 restores the SEPARATION defect (a `#if` around
the control flow) without restoring the fail-open, because those are two different mistakes and
only one of them is what anybody would notice.

THE THREE-WAY TENSION this defends, and every mutant below sits on one axis of it:

    do the work       <- mutant 1, 3: not doing it is P2-112 itself
    but not TWICE     <- mutant 4:    running inline as well as marshalling puts Account.Change()
                                      on a Timer thread on every box that HAS a UI
    and say so ONCE   <- mutant 5, 6: silence is the original defect; every 5 seconds is P2-108

⚠️ MUTANT 6 IS THE ONE THE REVIEW PANEL FOUND AND I HAD NOT. The announcement flag was instance-
scoped while the message it guards says "once per session". Today that is true only because of the
`Lazy<>` singleton three hundred lines up -- an invariant enforced somewhere else, which is exactly
how a log line starts describing something it did not observe. Driven negative before being
believed: with an instance field the second manager announces again and the test reports `got 2`.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

# See mutate_p2108.py: the battery's OWN stdout must be utf-8, or a non-ASCII character in a
# mutant description raises between applying a mutant and restoring it, leaving a live mutant.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')

MUTANTS = [
    # ---- axis 1: the sweep stops happening ------------------------------------------------
    (ATM,
     "THE SHIPPED SHAPE, restored: no dispatcher means return, forever. Breakeven stops never\n"
     "     move, trailing never advances, ReconcileStopFromBroker never runs so a refused move is\n"
     "     never even detected, and nothing logs. P1-13's fail-open at the loop that moves stops",
     '                if (TryMarshal(MonitorTickCore))\n'
     '                    return;',
     '                if (TryMarshal(MonitorTickCore))\n'
     '                    return;\n'
     '                return;'),

    (ATM,
     "THE SEPARATION DEFECT WITHOUT THE FAIL-OPEN: the control flow goes back behind `#if\n"
     "     TESTING`, so the test build drives a body the shipped assembly does not contain. The\n"
     "     production behaviour here is arguably FINE -- that is the point. This is P2-27's shape\n"
     "     on its own, and a battery that only mutates behaviour cannot see it",
     '                if (TryMarshal(MonitorTickCore))\n'
     '                    return;',
     '#if TESTING\n'
     '                MonitorTickCore();\n'
     '                return;\n'
     '#else\n'
     '                if (TryMarshal(MonitorTickCore))\n'
     '                    return;\n'
     '#endif'),

    (ATM,
     "the fallback announces and then does NOTHING. This is the subtlest restoration of the\n"
     "     defect: every surface now reports the condition, an operator reading the log believes\n"
     "     the sweep is degraded rather than absent, and the stop still never moves. A log line is\n"
     "     not a remedy",
     '                MonitorTickCore();\n'
     '            }\n'
     '            catch (Exception ex)\n'
     '            {\n'
     '                try { NinjaTrader.Code.Output.Process("[AtmMonitor] Dispatcher error: " + ex.Message, PrintTo.OutputTab1); } catch { }',
     '            }\n'
     '            catch (Exception ex)\n'
     '            {\n'
     '                try { NinjaTrader.Code.Output.Process("[AtmMonitor] Dispatcher error: " + ex.Message, PrintTo.OutputTab1); } catch { }'),

    # ---- axis 2: the sweep happens TWICE ---------------------------------------------------
    (ATM,
     "THE CHEAP FIX, and the one a reader arrives at first: delete the dispatcher and always run\n"
     "     inline. It passes the no-dispatcher test. It also puts Account.Change() on a Timer\n"
     "     thread on every box that HAS a UI, which is every box in normal use -- NT8\n"
     "     Account/Order/Position objects are not thread-safe. The negative test is what bans it",
     '                if (TryMarshal(MonitorTickCore))\n'
     '                    return;',
     '                TryMarshal(MonitorTickCore);'),

    # ---- axis 3: the announcement -----------------------------------------------------------
    (ATM,
     "the fallback becomes SILENT again. The sweep still runs, so nothing is unprotected -- but\n"
     "     the one condition under which broker calls move to a timer thread is undiagnosable, and\n"
     "     it is the condition an operator would want named when a stop move behaves oddly",
     '                if (System.Threading.Interlocked.Exchange(ref _noDispatcherAnnounced, 1) == 0)\n'
     '                {\n'
     '                    RiskGuardAddOn.LogFromComponent("", "ATM_MONITOR_NO_DISPATCHER",',
     '                if (false)\n'
     '                {\n'
     '                    RiskGuardAddOn.LogFromComponent("", "ATM_MONITOR_NO_DISPATCHER",'),

    (ATM,
     "the announcement fires EVERY SWEEP: one line per 5 seconds for the life of the process,\n"
     "     which is P2-108 verbatim and the seventh instance of `an alarm that is always on is\n"
     "     off`. Replaces a silent defect with an unreadable one",
     '                if (System.Threading.Interlocked.Exchange(ref _noDispatcherAnnounced, 1) == 0)',
     '                if (System.Threading.Interlocked.Exchange(ref _noDispatcherAnnounced, 1) >= 0)'),

    (ATM,
     "⚠️ THE ONE THE REVIEW PANEL FOUND AND I DID NOT: the flag goes back to INSTANCE scope while\n"
     "     the message it guards still says `once per session`. True today only because of the\n"
     "     Lazy<> singleton three hundred lines up -- an invariant enforced somewhere else, which\n"
     "     is how a log line starts describing something it did not observe",
     '        private static int _noDispatcherAnnounced;',
     '        private int _noDispatcherAnnounced;'),

    # ---- the seam's own contract ------------------------------------------------------------
    (ATM,
     "TryMarshal reports SUCCESS when there is no dispatcher, so the caller believes the work is\n"
     "     on the UI thread and skips it. The fail-open moves one level down, where the gate that\n"
     "     bans `if (dispatcher == null) return;` cannot see it -- the shape is now a lie in a\n"
     "     return VALUE rather than an early exit",
     '            var dispatcher = System.Windows.Application.Current?.Dispatcher;\n'
     '            if (dispatcher == null) return false;',
     '            var dispatcher = System.Windows.Application.Current?.Dispatcher;\n'
     '            if (dispatcher == null) return true;'),

    (ATM,
     "EXPECTED SURVIVOR: the production TryMarshal body is rewritten to marshal and ALSO report\n"
     "     failure, so the sweep runs on both threads. It lives behind `#else`, so no test build\n"
     "     compiles it and no test can reach it. Recorded rather than hidden: this is the residue\n"
     "     of P2-27 that shrinking the `#if` reduced but did not remove, and the only evidence\n"
     "     available for these four lines is `nt_compile` plus the live drive",
     '            dispatcher.InvokeAsync(() => work());\n'
     '            return true;',
     '            dispatcher.InvokeAsync(() => work());\n'
     '            return false;'),
]

# ⚠️ NO `newline=''` ON THIS READ, and it is not a style choice. With it, Python hands back the
# file's REAL line endings -- CRLF in this repo, in every fresh checkout -- while the anchors above
# are written with '\n'. Every multi-line anchor then matches NOTHING and scores a false survivor.
#
# This battery shipped with it and passed 9/9 locally, because earlier battery runs had already
# rewritten the worktree copy to LF. CI, which only ever has a fresh checkout, scored 2/9 -- the two
# single-line anchors -- and the other seven printed `[SKIP] anchor matched 0 times`.
# A LOCAL WORKTREE IS NOT A FRESH CHECKOUT. mutation/check_anchors.py now refuses this outright,
# because it reads the target with universal newlines and would otherwise be validating a string
# no battery ever searches.
#
# The WRITE below keeps newline='', which is correct: it stops Python translating on the way out.
ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


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
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    restore()

restore()
print('\nrestored originals;', run())

# The verdict is `_battery.finish`'s and not this file's. It reads the expectations out of MUTANTS
# itself, so there is no second list to drift, and it fails in BOTH directions -- an unexpected
# survivor AND a declared one that has since become killable, because that makes the declaration
# false. Hand-rolling it here is what tools/check_expected_survivors.py exists to catch, and it
# caught this battery's first draft.
_battery.finish(survivors, MUTANTS)
