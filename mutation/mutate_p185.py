"""Mutation battery for P1-85 (the copier must not invent an account).

Four guessed identities on the write path and two on the load path. What makes
this battery necessary rather than decorative is that most of the interesting
ways to get it wrong still LOOK like a refusal:

  * MUTANTS 1-4 restore the four fallbacks outright. Each one is the defect, and
    each mutates a different call site -- because a fix applied to three of four
    sites is the shape this repo keeps finding (P1-69, P1-75, and the accepted-
    write half that survived the first UI7 run).

  * MUTANT 5 swaps IsNullOrWhiteSpace for a null check. `{"leaderAccount": ""}`
    then sails through, and every test that sends a MISSING account still passes,
    because missing and blank are different inputs. This is the finding the review
    panel upheld on the first landing.

  * MUTANT 6 refuses the blank leader on create only, not on edit. That is what
    the first landing actually shipped, and the tests written for it went green.

  * MUTANT 7 refuses without setting the reason. The write is still refused, so
    every "was it refused?" assertion holds -- and the operator is back to a bare
    null, which is precisely the state UI7 existed to end.

  * MUTANTS 8-9 are the load path. 8 puts the skip report back on Console.WriteLine:
    the entry is still dropped, the suite's "was it dropped?" assertions still
    pass, and the operator's config silently shrinks at startup -- P?-64's shape.
    9 loads the undecipherable entry anyway with a blank name, which is the
    failure the refusal exists to prevent, arriving through the load path instead.

  * MUTANT 10 restores the DTO initialisers. Nothing constructs these without
    naming the accounts any more, so this mutant asks whether the SOURCE SCAN is
    real or whether it only ever looked at the call sites.

A crash counts as a kill (handover section 5.14).

Exits non-zero on any survivor, and exits 2 rather than running against a red
baseline.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    # ---- the four guesses, restored one at a time ----
    ("the relationship request guesses the LEADER again",
     '            string leader = ReqStr(req, "leaderAccount") ?? ReqStr(req, "LeaderAccountName");\n'
     '            string follower = ReqStr(req, "followerAccount") ?? ReqStr(req, "FollowerAccountName");',
     '            string leader = ReqStr(req, "leaderAccount") ?? ReqStr(req, "LeaderAccountName") ?? "Sim101";\n'
     '            string follower = ReqStr(req, "followerAccount") ?? ReqStr(req, "FollowerAccountName");'),

    ("the relationship request guesses the FOLLOWER again -- the other half, which is where\n"
     "     a one-sided fix always leaves the hole",
     '            string follower = ReqStr(req, "followerAccount") ?? ReqStr(req, "FollowerAccountName");',
     '            string follower = ReqStr(req, "followerAccount") ?? ReqStr(req, "FollowerAccountName") ?? "SimCopy2";'),

    ("the group request guesses the GROUP NAME again. Groups are looked up BY name, so this\n"
     "     is not a stray create -- an unnamed write silently EDITS whatever is stored there",
     '            string groupName = ReqStr(req, "groupName") ?? ReqStr(req, "GroupName");',
     '            string groupName = ReqStr(req, "groupName") ?? ReqStr(req, "GroupName") ?? "DefaultGroup";'),

    ("a NEW group gets a guessed leader again",
     '                        ? new CopierGroup { GroupName = groupName, LeaderAccountName = leader ?? "" }',
     '                        ? new CopierGroup { GroupName = groupName, LeaderAccountName = leader ?? "Sim101" }'),

    # ---- missing and blank are different inputs ----
    ("the relationship refusal tests for null instead of blank, so `\"\"` and `\"   \"` sail\n"
     "     through. Every test that omits an account still passes -- omitted and blank are not\n"
     "     the same input, which is why the panel had to find this rather than the suite",
     '            if (string.IsNullOrWhiteSpace(leader) || string.IsNullOrWhiteSpace(follower))',
     '            if (leader == null || follower == null)'),

    # ⚠️ THIS MUTANT SURVIVED ITS FIRST RUN, and the survival was the finding.
    # It used to narrow the PRE-merge blank-leader check to the create path -- exactly
    # the incomplete fix the review panel flagged -- and the suite stayed green, because
    # a SECOND check after the merge silently covered for it. Two statements of one rule
    # means neither is load-bearing and neither can be tested. The rule now lives in one
    # place, so this points at that place and the mutant kills.
    ("the blank-leader refusal applies to CREATE only, not to edits. This is what the first\n"
     "     landing shipped, and its tests were green",
     '            if (string.IsNullOrWhiteSpace(grp.LeaderAccountName))',
     '            if (isNew && string.IsNullOrWhiteSpace(grp.LeaderAccountName))'),

    # ---- refused, but silently ----
    ("the group-name refusal returns null WITHOUT a reason. Still refused, so every\n"
     "     'was it refused?' assertion holds, and the operator is back to a bare null",
     '                refusalReason = "refused to apply group request: the group name was missing. A group request must name the group it applies to.";',
     '                refusalReason = null;'),

    # ---- the load path ----
    ("the skipped relationship goes back to Console.WriteLine. The entry is still dropped and\n"
     "     the suite's drop assertions still pass -- the operator's config just shrinks at\n"
     "     startup with nothing in the guard log to say so (P?-64's shape)",
     '                        CopierLog(key, "CONFIG_ENTRY_SKIPPED", string.Format(\n'
     '                            "[LoadFromDisk] Skipping invalid relationship \'{0}\': could not derive FollowerAccountName from key.",\n'
     '                            key));',
     '                        Console.WriteLine("[LoadFromDisk] Skipping invalid relationship: " + key);'),

    ("the undecipherable group is LOADED with a blank leader instead of skipped. The exact\n"
     "     state the write path refuses, arriving through the load path instead",
     '                    CopierLog(key, "CONFIG_ENTRY_SKIPPED", string.Format(\n'
     '                        "[LoadFromDisk] Skipping invalid group \'{0}\': could not derive LeaderAccountName from key.",\n'
     '                        key));\n'
     '                    grp = null;\n'
     '                    return false;',
     '                    normalized["LeaderAccountName"] = "";'),

    # ---- is the source scan real? ----
    ("the DTO initialisers name Sim101/SimCopy2 again. No construction path relies on them\n"
     "     now, so this asks whether the source scan is a real gate or whether it only ever\n"
     "     looked at the call sites",
     '        public string LeaderAccountName { get; set; } = "";\n'
     '        public string FollowerAccountName { get; set; } = "";',
     '        public string LeaderAccountName { get; set; } = "Sim101";\n'
     '        public string FollowerAccountName { get; set; } = "SimCopy2";'),
]


def run():
    build = subprocess.run(
        ['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    if build.returncode != 0:
        return 'BUILD FAILED'
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    return m.group(0) if m else 'NO RESULT LINE'


ORIGINAL = open(ENGINE, encoding='utf-8').read()

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
    open(ENGINE, 'w', encoding='utf-8', newline='').write(ORIGINAL.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(ENGINE, 'w', encoding='utf-8', newline='').write(ORIGINAL)

open(ENGINE, 'w', encoding='utf-8', newline='').write(ORIGINAL)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
