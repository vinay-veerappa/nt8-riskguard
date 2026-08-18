"""Mutation battery for UI7 (a refusal that says why).

The engine refuses a write by returning null. UI7 makes it return the REASON as
well, and this battery exists because every interesting way to get that wrong
still returns null on refusal -- so the existing P1-76 tests, which check only
that the write was refused, stay green through all of it.

What each group is defending:

  * MUTANTS 1-2 drop the reason and log a generic line instead. The refusal still
    works, nothing throws, and the operator is back to "the engine refused" with
    no way to find out what to change. This is the state UI7 was written to leave.

  * MUTANT 3 is the one this file is really for. It sets the reason to its OWN
    wording instead of handing over the string that was logged. Everything passes
    a casual read -- there is a reason, it is accurate today, it names the group.
    It is a SECOND copy of an explanation, and the next person to improve the log
    line improves only the log line. The test that pins them as one string is the
    only thing standing between here and that drift.

  * MUTANT 4 names only the first clashing follower. The group refusal is
    ALL-OR-NOTHING on purpose (a group created minus an account you named is
    P1-23's shape), so a reason listing one of three sends the operator round the
    loop twice more and makes a deterministic refusal feel flaky.

  * MUTANT 7 sets a reason on the ACCEPTED path too. Now `reason != null` no
    longer means "refused" -- and the bridge branch this whole ticket exists to
    fix is about to be written against exactly that test.

  * MUTANTS 9-10 mutate TradeCopierWindow.cs, not the engine: they put a surface
    back on the reason-losing overload. That file's body is entirely `#if !TESTING`
    so there is no executable path to assert against, and the source scan is the
    only gate. A gate that is never proven to fire is decoration -- and this repo
    has caught nine of those.

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
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')
WINDOW = os.path.join(REPO, 'addons', 'TradeCopierWindow.cs')

MUTANTS = [
    # ---- the reason is simply not produced ----
    (ENGINE,
     "the RELATIONSHIP refusal logs a generic line and returns no reason, so the operator is\n"
     "     back to 'the engine refused' with nothing to act on",
     '                refusalReason = string.Format(\n'
     '                    "refused to create a direct relationship for \'{0}\' under leader \'{1}\': it is already a member "',
     '                refusalReason = null;\n'
     '                string unused = string.Format(\n'
     '                    "refused to create a direct relationship for \'{0}\' under leader \'{1}\': it is already a member "'),

    (ENGINE,
     "the GROUP refusal returns no reason. Same defect, other half -- and the half a\n"
     "     single-sided fix always leaves behind (P1-69 was exactly this shape)",
     '                    refusalReason = string.Format(\n'
     '                        "refused group \'{0}\' under leader \'{1}\': {2} of its followers already have a direct "',
     '                    refusalReason = null;\n'
     '                    string unusedG = string.Format(\n'
     '                        "refused group \'{0}\' under leader \'{1}\': {2} of its followers already have a direct "'),

    # ---- THE drift mutant ----
    (ENGINE,
     "the reason is a SECOND copy of the explanation rather than the string that was logged.\n"
     "     Accurate today, and the next edit to the log line will not reach it",
     '                CopierLog(follower, "CONFIG_OVERLAP_REFUSED", refusalReason);',
     '                CopierLog(follower, "CONFIG_OVERLAP_REFUSED", "refused to create a direct relationship for \'"\n'
     '                    + follower + "\' under leader \'" + leader + "\': it is already a member of group \'"\n'
     '                    + reserving.GroupName + "\'.");'),

    # ---- the all-or-nothing refusal explained as if it were partial ----
    (ENGINE,
     "the group refusal names only the FIRST clashing follower, so an all-or-nothing refusal\n"
     "     reads as a one-account problem and the operator loops",
     '                        grp.GroupName, grp.LeaderAccountName, clashes.Count, string.Join(", ", clashes));',
     '                        grp.GroupName, grp.LeaderAccountName, clashes.Count, clashes[0]);'),

    # ---- the malformed-body path ----
    (ENGINE,
     "a null RELATIONSHIP request goes back to a bare null, so a malformed POST body makes the\n"
     "     engine look silent and the surface look broken",
     '            if (req == null)\n'
     '            {\n'
     '                refusalReason = "the request was empty, so there was nothing to apply.";\n'
     '                return null;\n'
     '            }\n'
     '            string leader = ReqStr(req, "leaderAccount")',
     '            if (req == null) return null;\n'
     '            string leader = ReqStr(req, "leaderAccount")'),

    (ENGINE,
     "a null GROUP request goes back to a bare null -- the other half again",
     '            if (req == null)\n'
     '            {\n'
     '                refusalReason = "the request was empty, so there was nothing to apply.";\n'
     '                return null;\n'
     '            }\n'
     '            string groupName = ReqStr(req, "groupName")',
     '            if (req == null) return null;\n'
     '            string groupName = ReqStr(req, "groupName")'),

    # ---- the reason stops meaning "refused" ----
    (ENGINE,
     "an ACCEPTED relationship write also reports a reason, so `reason != null` stops meaning\n"
     "     refused -- and the bridge branch this ticket exists to fix is written against that test",
     '        public CopierRelationship ApplyRelationshipRequest(JObject req, bool confirmLive, out string refusalReason)\n'
     '        {\n'
     '            refusalReason = null;',
     '        public CopierRelationship ApplyRelationshipRequest(JObject req, bool confirmLive, out string refusalReason)\n'
     '        {\n'
     '            refusalReason = "ok";'),

    (ENGINE,
     "an ACCEPTED group write also reports a reason",
     '        public CopierGroup ApplyGroupRequest(JObject req, bool confirmLive, out string refusalReason)\n'
     '        {\n'
     '            refusalReason = null;',
     '        public CopierGroup ApplyGroupRequest(JObject req, bool confirmLive, out string refusalReason)\n'
     '        {\n'
     '            refusalReason = "ok";'),

    # ---- a SURFACE back on the reason-losing overload ----
    (WINDOW,
     "the quarantine-release button goes back to the two-argument overload, so the one button\n"
     "     whose refusal is hardest to guess at explains nothing",
     '                    string refusal;\n'
     '                    var result = TradeCopierEngine.Instance.ApplyRelationshipRequest(req, rel.ArmedForLive, out refusal);',
     '                    string refusal = null;\n'
     '                    var result = TradeCopierEngine.Instance.ApplyRelationshipRequest(req, rel.ArmedForLive);'),

    (WINDOW,
     "the Add Group form goes back to the two-argument overload -- the site with the MOST to\n"
     "     explain, since a group refusal can name several accounts at once",
     '                string refusal;\n'
     '                var result = TradeCopierEngine.Instance.ApplyGroupRequest(req, armed, out refusal);',
     '                string refusal = null;\n'
     '                var result = TradeCopierEngine.Instance.ApplyGroupRequest(req, armed);'),
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


ORIGINALS = {path: open(path, encoding='utf-8').read() for path in (ENGINE, WINDOW)}

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
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    # P2-148: the verdict above cannot tell a detection from a crash.
    if 'NO ASSERTION FAILED' in res:
        killed = False
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(path, 'w', encoding='utf-8', newline='').write(original)

for path, original in ORIGINALS.items():
    open(path, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored originals;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
