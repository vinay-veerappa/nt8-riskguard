"""Mutation battery for P3-34 (arm/shadow discipline extended to the copier).

The gate this defends decides whether a follower account receives a real order. Every
mutant below is a way of writing code that looks like a shadow mode and trades anyway.

The starting position matters, because it is not the one section 0 states. "The copier
acts regardless of guard mode" is half true: a LIVE follower was already gated three
ways (ArmedForLive, CanTrade, IsGuardProtecting -- and the last requires the guard's
mode to be "live", so a shadow guard already blocked it). A SIM follower was gated by
none of them. So what P3-34 adds is a copier mode of its OWN, deliberately not a
reading of the guard's: the operator drives sim copies while the guard sits in shadow,
which is how section 5.13's live validation was run.

What each mutant is defending:

  * MUTANT 1 makes IsCopierActingMode accept "shadow" too. The mode is honoured
    everywhere, reported everywhere, and submits orders -- the single most direct way
    for this feature to be decorative.

  * MUTANT 2 makes an UNRECOGNISED mode act. P1-87's exact shape: a comparison against
    literals whose fall-through is the permissive branch. Here the permissive branch
    places real orders, so a typo in a config field becomes the difference between
    observing and trading.

  * MUTANT 3 keeps the gate and deletes the `continue`, so the copy is logged as
    suppressed and then submitted anyway. The log says shadow; the broker disagrees.
    This is P1-70's class -- a log asserting an outcome it did not observe -- and it is
    the one a reviewer skimming the diff is least likely to catch, because the shape of
    the fix is entirely present.

  * MUTANT 4 moves the shadow log's detail out of the message, leaving "nothing was
    submitted" with no instrument, action or quantity. Correct and useless: the whole
    reason to run shadow is to read what WOULD have been sent (UI7).

  * MUTANT 5 makes TrySetCopierMode apply the mode before preflight can refuse it. The
    refusal is still returned and still logged, and the copier is live anyway -- P1-88's
    class exactly, an unwritten write reported as persisted, inverted.

  * MUTANT 6 makes preflight gate the mode change in BOTH directions, so leaving `live`
    can be refused. A gate that blocks the SAFE direction is one an operator routes
    around, and here routing around it means staying live.

  * MUTANT 7 makes LoadFromDisk adopt an unrecognised stored mode. Combined with the
    fail-closed gate this stops the copier with a config file that looks fine -- the
    P2-41 shape, where a default and an erasure are indistinguishable on disk.

  * MUTANT 8 flips the persisted default to "shadow". Nothing in the suite fails,
    because the tests set the mode explicitly -- but section 5.25's lesson is that a
    default only applies to fields ABSENT from the stored config, so this would silently
    stop a working copier on the next restart of a box whose config predates the field.
    Expected to be KILLED by the "live is the default" test; it is here because that
    test is the only thing standing between this feature and that outcome.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
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
COPIER = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    ("IsCopierActingMode accepts \"shadow\" as well. The mode is honoured everywhere, reported\n"
     "     everywhere, and submits orders -- the most direct way for this feature to be decorative",
     'return string.Equals(mode, "live", StringComparison.OrdinalIgnoreCase);\n        }\n\n        public static bool IsRecognisedCopierMode',
     'return string.Equals(mode, "live", StringComparison.OrdinalIgnoreCase)\n'
     '                || string.Equals(mode, "shadow", StringComparison.OrdinalIgnoreCase);\n        }\n\n'
     '        public static bool IsRecognisedCopierMode'),

    ("an UNRECOGNISED mode acts. P1-87's shape, with the permissive branch placing real orders --\n"
     "     a typo in a config field becomes the difference between observing and trading",
     '                string copierMode = GetCopierMode();\n                if (!IsCopierActingMode(copierMode))',
     '                string copierMode = GetCopierMode();\n                if (!IsCopierActingMode(copierMode) && IsRecognisedCopierMode(copierMode))'),

    ("the gate stays and the `continue` goes, so the copy is logged as suppressed and then\n"
     "     submitted anyway. The log says shadow and the broker disagrees -- P1-70's class, and\n"
     "     the shape of the fix is entirely present for anyone skimming the diff",
     '+ $"{leadOrderAction} {exec.Quantity}@{exec.Price} (isExit={isExit}).");\n                    continue;\n                }\n\n                try',
     '+ $"{leadOrderAction} {exec.Quantity}@{exec.Price} (isExit={isExit}).");\n                }\n\n                try'),

    ("the shadow line loses the order it would have sent. Correct and useless: the whole reason\n"
     "     to run shadow is to read what WOULD have gone out (UI7's finding, another place)",
     '$"copier mode is \'{copierMode}\', so nothing was submitted. WOULD have sent "\n'
     '                        + $"{targetInstrument.FullName} {followerAction} {targetQty} to "\n'
     '                        + $"\'{followerAcc.Name}\', mirroring leader \'{acctName}\' "',
     '$"copier mode is \'{copierMode}\', so nothing was submitted. "\n'
     '                        + $"" + $""\n'
     '                        + $"mirroring leader \'{acctName}\' "'),

    ("TrySetCopierMode applies the mode BEFORE preflight can refuse it. The refusal is still\n"
     "     returned and still logged, and the copier is live anyway -- P1-88 inverted",
     '            if (IsCopierActingMode(mode))\n            {\n                var preflight = RunCopierPreflight();',
     '            lock (_lock) { _copierMode = mode; }\n            if (IsCopierActingMode(mode))\n            {\n                var preflight = RunCopierPreflight();'),

    ("preflight gates the mode change in BOTH directions, so LEAVING live can be refused. A gate\n"
     "     that blocks the safe direction is one an operator routes around, and routing around\n"
     "     this one means staying live",
     '            if (IsCopierActingMode(mode))\n            {\n                var preflight',
     '            if (true)\n            {\n                var preflight'),

    ("LoadFromDisk adopts an unrecognised stored mode. With the fail-closed gate that stops the\n"
     "     copier with a config file that looks fine -- P2-41's shape, where a default and an\n"
     "     erasure are indistinguishable on disk",
     '                        if (IsRecognisedCopierMode(loadedMode))\n                        {\n                            _copierMode = loadedMode;',
     '                        if (true)\n                        {\n                            _copierMode = loadedMode;'),

    ("the default flips to \"shadow\". Section 5.25: a default only applies to fields ABSENT from\n"
     "     the stored config, so this silently stops a working copier on the next restart of any\n"
     "     box whose config predates the field",
     'private string _copierMode = "live";',
     'private string _copierMode = "shadow";'),

    ("SaveToDisk stops writing the mode, so it reverts to the default on the next restart with\n"
     "     nothing about the config file looking wrong. The write is the half a reader-only test\n"
     "     cannot see, which is why the round-trip test drives both",
     '                        ["CopierMode"] = _copierMode',
     '                        ["CopierModeUnused"] = _copierMode'),

    ("the UNRECOGNISED-mode refusal goes back to being silent in the audit log. It still returns\n"
     "     a refusal to the HTTP caller, so every response-shaped test stays green -- and an\n"
     "     operator grepping afterwards for why the copier is not in the mode they set finds\n"
     "     nothing. P1-71's class, and it was found on the LIVE box, not by reading the code",
     '                CopierLog(null, "MODE_CHANGE_REFUSED",\n'
     '                    $"refusing to put the copier in \'{mode}\': not one of live/shadow/disabled. "\n'
     '                    + $"Mode stays \'{GetCopierMode()}\'.");\n'
     '                return result;',
     '                return result;'),

    ("a successful mode change stops being logged. Nothing fails that looks at outcomes -- and\n"
     "     the log can no longer answer 'when did this become shadow?', which is the question\n"
     "     asked after a copier silently stops copying",
     '            CopierLog(null, "MODE_CHANGED",',
     '            if (false) CopierLog(null, "MODE_CHANGED",'),
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


ORIGINAL = open(COPIER, encoding='utf-8').read()

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
    open(COPIER, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(COPIER, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(COPIER, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
