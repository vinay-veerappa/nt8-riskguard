"""Mutation battery for P1-76 (a follower belongs to a direct relationship OR a group).

Why this battery exists, specifically:

The six P1-76 tests were written before the code, but the only "red" I ever saw from
them was a COMPILE ERROR -- DetectConfigConflicts did not exist yet. That is not
evidence. It is the same trap recorded in the handover's section 8: a failure from the
harness rather than from the assertion looks exactly like the evidence test-first work
depends on, and proves nothing about whether the test can detect the behaviour it
claims to pin. So every guard is reverted here and must turn the suite red.

Mutant 4 is the one that matters most. Before P1-76 the direct-over-group precedence
was produced by list insertion order plus .First(), pinned by nothing -- the existing
dedup test asserted only `count == 1` and the follower's NAME, never which side won.
That mutant restores exactly that state. If it survives, the new tie-break test is
decorative and reordering two statements can still flip live sizing in silence.

A crash counts as a kill (see section 5.14: a mutant that killed the runner produced
no result line and was scored a SURVIVOR).

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree. Measured in CI on
# mutate_p182.py, 2026-08-15. The subprocess encoding below is the OTHER half.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    # ---- the three refusals ----
    ("ApplyRelationshipRequest stops refusing, so a direct relationship can shadow a group again",
     '            var reserving = GroupReserving(leader, follower);\n            if (reserving != null)',
     '            var reserving = GroupReserving(leader, follower);\n            if (false)'),

    ("AddFollowerToGroup stops refusing, so a follower with a direct relationship joins a group",
     '                if (clash != null)\n                {\n                    CopierLog(followerAccount, "CONFIG_OVERLAP_REFUSED"',
     '                if (false)\n                {\n                    CopierLog(followerAccount, "CONFIG_OVERLAP_REFUSED"'),

    ("ApplyGroupRequest stops refusing, so a group can claim an already-directly-managed follower",
     '                if (clashes.Count > 0)',
     '                if (false)'),

    # ---- THE precedence mutant: restore the pre-P1-76 emergent tie-break ----
    ("the tie-break goes back to being emergent -- group entries are skipped ONLY when the direct "
     "relationship is quarantined, exactly as before P1-76, so the group's ratio wins for every "
     "healthy follower and nothing but list order decides it",
     '                        if (directRel != null)\n                        {\n                            continue;\n                        }',
     '                        if (!includeQuarantined && directRel != null && directRel.IsQuarantined)\n                        {\n                            continue;\n                        }'),

    ("the direct relationship stops winning altogether -- group entries are never skipped, so the\n"
     "     deduplication's .First() is the only thing standing between a follower and the wrong size",
     '                        if (directRel != null)\n                        {\n                            continue;\n                        }',
     ''),

    # ---- the deduplication is a SAFETY property, independent of P1-76 ----
    ("deduplication is removed, so one follower can receive two orders for one leader fill",
     '                result = result\n                    .GroupBy(r => r.FollowerAccountName, StringComparer.OrdinalIgnoreCase)\n                    .Select(g => g.First())\n                    .ToList();',
     ''),

    # ---- detection and reporting ----
    ("DetectConfigConflicts reports nothing, so a hand-edited overlap is invisible",
     '                        if (!hasDirect) continue;',
     '                        if (true) continue;'),

    ("the conflict is reported without naming the group, so the operator cannot find it",
     '                            GroupName = grp.GroupName,',
     '                            GroupName = null,'),

    ("LoadFromDisk stops reporting conflicts, so the only notice for a hand-edited file is gone",
     '                foreach (var conflict in DetectConfigConflicts())\n                {\n                    CopierLog(conflict.FollowerAccount, "CONFIG_OVERLAP_DETECTED", conflict.Detail);\n                }',
     ''),

    # ---- a load must NOT resolve a conflict by discarding config (P?-64's shape) ----
    ("the load 'resolves' the overlap by dropping the group entry -- operator config vanishing\n"
     "     without an error, which is the failure this rule was written to avoid",
     '                foreach (var conflict in DetectConfigConflicts())\n                {\n                    CopierLog(conflict.FollowerAccount, "CONFIG_OVERLAP_DETECTED", conflict.Detail);\n                }',
     '                foreach (var conflict in DetectConfigConflicts())\n                {\n                    CopierLog(conflict.FollowerAccount, "CONFIG_OVERLAP_DETECTED", conflict.Detail);\n                    var g0 = _groups.FirstOrDefault(g => g.GroupName == conflict.GroupName);\n                    if (g0 != null && g0.FollowerAccounts != null) g0.FollowerAccounts.RemoveAll(f => f.Equals(conflict.FollowerAccount, StringComparison.OrdinalIgnoreCase));\n                }'),

    # ---- case sensitivity: every account comparison in this engine is OrdinalIgnoreCase ----
    ("GroupReserving becomes case-SENSITIVE on the follower, so 'SIMCOPY2' bypasses the refusal",
     '                    g.FollowerAccounts.Any(f => !string.IsNullOrWhiteSpace(f)\n                                                && f.Equals(followerAccount, StringComparison.OrdinalIgnoreCase)));',
     '                    g.FollowerAccounts.Any(f => !string.IsNullOrWhiteSpace(f)\n                                                && f.Equals(followerAccount, StringComparison.Ordinal)));'),

    ("GroupReserving becomes case-SENSITIVE on the leader, same bypass by the other key",
     '                    g.LeaderAccountName.Equals(leaderAccount, StringComparison.OrdinalIgnoreCase) &&\n                    g.FollowerAccounts != null &&',
     '                    g.LeaderAccountName.Equals(leaderAccount, StringComparison.Ordinal) &&\n                    g.FollowerAccounts != null &&'),

    # ---- membership, not effect ----
    ("only ENABLED groups reserve their followers, so enabling a group is what silently creates\n"
     "     the overlap -- the exact click this rule exists to make impossible",
     '                return _groups.FirstOrDefault(g =>\n                    !string.IsNullOrWhiteSpace(g.LeaderAccountName) &&',
     '                return _groups.FirstOrDefault(g =>\n                    g.IsEnabled &&\n                    !string.IsNullOrWhiteSpace(g.LeaderAccountName) &&'),

    # ---- all-or-nothing on a group request ----
    ("a group request becomes PARTIAL instead of all-or-nothing: it is created without the\n"
     "     clashing followers, silently dropping accounts the operator explicitly named",
     '                if (clashes.Count > 0)\n                {',
     '                if (clashes.Count > 0)\n                {\n                    grp.FollowerAccounts.RemoveAll(f => clashes.Contains(f));\n                    UpsertGroup(grp, true);\n                    return grp;\n                }\n                if (false)\n                {'),
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
    return 'NO RESULT LINE'


original = open(ENGINE, encoding='utf-8').read()
print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print(f'\nREFUSING TO RUN: baseline is RED ({m.group(2)} failing). Every mutant would '
          'score KILLED on pre-existing failures and this battery would prove nothing.')
    sys.exit(2)

survivors = []
for name, old, new in MUTANTS:
    if original.count(old) != 1:
        print(f'  [SKIP] {name}: anchor matched {original.count(old)} times')
        survivors.append(name + ' (ANCHOR)')
        continue
    open(ENGINE, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    # A crash is a kill: the mutation stopped the suite completing.
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
    if not killed:
        survivors.append(name)

open(ENGINE, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
