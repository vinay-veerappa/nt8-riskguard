"""Mutation battery for UI2 (one config owner; the window dispatches requests).

Why this battery exists, specifically:

UI2's 12 acceptance tests went from red to green in ONE loop round, which is the
best result any ticket here has had -- and is exactly the situation UI1 proved you
cannot trust. There, 18 red-then-green tests were followed by ten upheld review
defects and then by 2 of 12 mutants surviving. A clean first round is evidence
about the implementer, not about the tests.

This battery is also the first here to mutate TWO files. Four of its mutants edit
TradeCopierWindow.cs, whose whole body is `#if !TESTING` -- the suite compiles it
away and cannot execute one line of it, so four acceptance tests read it as TEXT
instead. A source-text check is a weaker instrument than an execution and it is
the only one available, which makes "does it actually fail when the defect comes
back?" a question worth spending compute on rather than assuming. Mutants 12-15
put each original defect back, verbatim.

The three that matter most:

  * MUTANT 3 INSERTS a parameterless LoadFromDisk(). Its test
    (TestUi2_ThereIsDeliberatelyNoParameterlessLoad) is GREEN AT BASELINE by
    construction -- it pins a decision, not an acceptance criterion, so it was
    excluded from expect_green and the test-first gate never covered it. This
    mutant is the only thing standing behind it. P1-69 was a read that destroyed
    the measurements it was asked to report; a convenient load is how the next
    surface repeats it.

  * MUTANT 10 clears the reason of an ACTIVE quarantine -- the P1-79 invariant
    inverted. Worse than the defect it replaces: the released case merely keeps
    stale text, this one deletes the explanation of a follower that has actually
    stopped copying.

  * MUTANT 17 reinstates the disarming branch the review panel filed THREE
    BLOCKERs about. The finding was wrong -- it misread `armed && armingWasRequested
    && !confirmLive` -- but the invariant it pointed at was pinned by nothing until
    this ticket. This mutant is what makes the three tests written in response real
    rather than decorative.

A crash counts as a kill (handover section 5.14: a mutant that killed the runner
produced no result line and was scored a SURVIVOR).

Exits non-zero on any survivor, and exits 2 rather than running against a red
baseline -- where every mutant would score KILLED on pre-existing failures.
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGINE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')
WINDOW = os.path.join(REPO, 'addons', 'TradeCopierWindow.cs')

# (description, target file, find, replace)
MUTANTS = [
    # ---- the path, and the two defects it closes ----
    (ENGINE,
     "ConfigFilePath goes back to the file the WINDOW used, so the UI writes somewhere\n"
     "     nothing reads and every operator change is discarded at the next restart -- P?-64\n"
     "     reinstated verbatim",
     'get { return Path.Combine(Globals.UserDataDir, "RiskGuard", "copier_config.json"); }',
     'get { return Path.Combine(Globals.UserDataDir, "CopierConfig.json"); }'),

    (ENGINE,
     "the parameterless save becomes a no-op, so every surface that stopped naming a path\n"
     "     silently stops persisting anything at all",
     '        public void SaveToDisk()\n        {\n            SaveToDisk(ConfigFilePath);\n        }',
     '        public void SaveToDisk()\n        {\n        }'),

    (ENGINE,
     "a parameterless LoadFromDisk() is ADDED -- the P1-69 footgun made convenient again.\n"
     "     This is the ONLY thing pinning that decision: its test is green at baseline and\n"
     "     was therefore excluded from the test-first gate",
     '        public void SaveToDisk()\n        {\n            SaveToDisk(ConfigFilePath);\n        }',
     '        public void LoadFromDisk()\n        {\n            LoadFromDisk(ConfigFilePath);\n        }\n\n'
     '        public void SaveToDisk()\n        {\n            SaveToDisk(ConfigFilePath);\n        }'),

    (ENGINE,
     "the two save overloads stop being one serializer: the parameterless one writes its\n"
     "     own file directly, which is how two surfaces drift apart while both look correct",
     '            SaveToDisk(ConfigFilePath);',
     '            try { Directory.CreateDirectory(Path.GetDirectoryName(ConfigFilePath));\n'
     '                  File.WriteAllText(ConfigFilePath, "{}"); } catch {}'),

    # ---- the request builders: a dropped key is SILENT (P1-74) ----
    (ENGINE,
     "the Add-relationship builder drops maxPositionSize, so the operator's position cap\n"
     "     never reaches the engine and the field appears to do nothing -- P1-74's shape",
     '                { "maxPositionSize", maxPositionSize },\n                { "autoSymbolConversion", autoSymbolConversion },\n'
     '                { "armedForLive", armedForLive },\n'
     '                { "isEnabled", isEnabled },\n                { "fixedLotMode", fixedLotMode },\n'
     '                { "fixedLotSize", fixedLotSize }\n            };\n        }\n\n'
     '        /// <summary>Everything the window\'s "Add Group" form collects, and nothing else.</summary>',
     '                { "autoSymbolConversion", autoSymbolConversion },\n'
     '                { "armedForLive", armedForLive },\n'
     '                { "isEnabled", isEnabled },\n                { "fixedLotMode", fixedLotMode },\n'
     '                { "fixedLotSize", fixedLotSize }\n            };\n        }\n\n'
     '        /// <summary>Everything the window\'s "Add Group" form collects, and nothing else.</summary>'),

    (ENGINE,
     "one builder key is MISSPELLED ('autoSymbol' for 'autoSymbolConversion'). It drops\n"
     "     an unrecognised key without an error, so the control silently does nothing --\n"
     "     which is P1-74 exactly, and the reason the keys are asserted rather than proofread",
     '                { "autoSymbolConversion", autoSymbolConversion },\n                { "armedForLive", armedForLive },\n'
     '                { "isEnabled", isEnabled },\n                { "fixedLotMode", fixedLotMode },\n'
     '                { "fixedLotSize", fixedLotSize }\n            };\n        }\n\n'
     '        /// <summary>Everything the window\'s "Add Group" form collects, and nothing else.</summary>',
     '                { "autoSymbol", autoSymbolConversion },\n                { "armedForLive", armedForLive },\n'
     '                { "isEnabled", isEnabled },\n                { "fixedLotMode", fixedLotMode },\n'
     '                { "fixedLotSize", fixedLotSize }\n            };\n        }\n\n'
     '        /// <summary>Everything the window\'s "Add Group" form collects, and nothing else.</summary>'),

    (ENGINE,
     "the group builder sends followerAccounts as a comma-joined STRING rather than a\n"
     "     JArray, so the checkbox list arrives as one nonsense account name",
     '                { "followerAccounts", followers },',
     '                { "followerAccounts", string.Join(",", followers.Select(f => (string)f)) },'),

    (ENGINE,
     "the group builder omits groupName, so ApplyGroupRequest falls back to 'DefaultGroup'\n"
     "     and every edit creates a new group instead of updating the named one",
     '                { "groupName", groupName },\n                { "leaderAccount", leaderAccount },',
     '                { "leaderAccount", leaderAccount },'),

    # ---- edits carry ONE field: absent must mean absent ----
    (ENGINE,
     "a row edit carries isQuarantined UNCONDITIONALLY, so clicking Disable also releases\n"
     "     a live quarantine -- a button doing something it does not say it does",
     '            if (releaseQuarantine == true)\n            {\n                req["isQuarantined"] = false;\n            }',
     '            req["isQuarantined"] = false;'),

    (ENGINE,
     "GroupEdit carries isEnabled even when the caller passed null, so an edit that means\n"
     "     'change nothing else' disables the group",
     '        public static JObject GroupEdit(string groupName, bool? isEnabled)\n        {\n'
     '            var req = new JObject\n            {\n                { "groupName", groupName }\n            };\n\n'
     '            if (isEnabled.HasValue)\n            {\n                req["isEnabled"] = isEnabled.Value;\n            }',
     '        public static JObject GroupEdit(string groupName, bool? isEnabled)\n        {\n'
     '            var req = new JObject\n            {\n                { "groupName", groupName }\n            };\n\n'
     '            req["isEnabled"] = isEnabled ?? false;'),

    # ---- P1-79, the quarantine-reason invariant ----
    (ENGINE,
     "the P1-79 invariant is deleted, so releasing a quarantine keeps its REASON and the\n"
     "     UI reports 'Margin / Order Rejection' about a relationship that is copying fine",
     '            if (!rel.IsQuarantined)\n                rel.QuarantineReason = null;',
     ''),

    (ENGINE,
     "the P1-79 invariant is INVERTED, clearing the reason of an ACTIVE quarantine. Worse\n"
     "     than the defect it replaces: the operator is told a follower stopped copying and\n"
     "     not why",
     '            if (!rel.IsQuarantined)\n                rel.QuarantineReason = null;',
     '            if (rel.IsQuarantined)\n                rel.QuarantineReason = null;'),

    # ---- the window. Four defects put back verbatim. ----
    # These are the only mutants here whose test is a SOURCE-TEXT check rather than an
    # execution, which is exactly why they are worth running: the whole file is
    # `#if !TESTING` and no assertion can reach its behaviour.
    (WINDOW,
     "one window save site names a path again (P?-64). If this survives, the source-text\n"
     "     check that replaced an untestable execution proves nothing",
     '                TradeCopierEngine.Instance.SaveToDisk();\n                RefreshUI();\n            };\n            actions.Children.Add(deleteBtn);\n\n            Grid.SetColumn(actions, 1);\n            grid.Children.Add(actions);\n\n            card.Child = grid;\n            return card;\n        }\n\n        private UIElement CreateGroupCard(CopierGroup grp)',
     '                TradeCopierEngine.Instance.SaveToDisk(Path.Combine(Globals.UserDataDir, "CopierConfig.json"));\n                RefreshUI();\n            };\n            actions.Children.Add(deleteBtn);\n\n            Grid.SetColumn(actions, 1);\n            grid.Children.Add(actions);\n\n            card.Child = grid;\n            return card;\n        }\n\n        private UIElement CreateGroupCard(CopierGroup grp)'),

    (WINDOW,
     "the Add button builds a fresh CopierRelationship again (P?-65) -- the subset write\n"
     "     that wipes the ratio matrix, the symbol map and the slippage cap",
     '                var req = CopierRequests.Relationship(\n                    leader, follower, mode, ratio, maxPos, autoSymbol, armed, true);',
     '                var rel = new CopierRelationship { LeaderAccountName = leader, FollowerAccountName = follower };\n'
     '                var req = CopierRequests.Relationship(\n                    leader, follower, mode, ratio, maxPos, autoSymbol, armed, true);'),

    (WINDOW,
     "a row button assigns to the STORED object before writing, so a write the engine\n"
     "     refuses has already landed in memory and the redraw shows it as applied",
     '                bool nextEnabled = !rel.IsEnabled;',
     '                rel.IsEnabled = !rel.IsEnabled;\n                bool nextEnabled = rel.IsEnabled;'),

    (WINDOW,
     "one dispatch stops checking for the refusal it can now receive, so a P1-76 overlap\n"
     "     refusal saves and redraws as though it had succeeded",
     # Anchor re-pointed 2026-08-13. UI7 rewrote this block (the two-argument overload
     # became the three-argument one and the message gained `+ refusal`), so the old
     # find-string stopped matching -- and a battery whose anchor misses prints [SKIP]
     # and scores the mutant as a SURVIVOR. It had been doing that silently since UI7
     # landed, which is to say this mutant was not being tested at all.
     #
     # Found by a fresh pair of eyes re-running the whole suite of batteries after an
     # unrelated refactor, not by the commit that broke it. That is the argument for
     # running every battery on every change rather than the one you think you touched.
     '                string refusal;\n'
     '                var result = TradeCopierEngine.Instance.ApplyGroupRequest(req, grp.ArmedForLive, out refusal);\n'
     '                if (result == null)\n                {\n'
     '                    MessageBox.Show("The engine refused to toggle this group.\\n\\n" + refusal, "Toggle Refused", MessageBoxButton.OK, MessageBoxImage.Warning);\n'
     '                    return;\n                }',
     '                string refusal;\n'
     '                TradeCopierEngine.Instance.ApplyGroupRequest(req, grp.ArmedForLive, out refusal);'),

    # ---- the arming gate: what three BLOCKERs claimed, made real ----
    (ENGINE,
     "the arming gate fires when arming was NOT requested -- the defect the review panel\n"
     "     filed three BLOCKERs about. The finding was a misreading, but the invariant was\n"
     "     pinned by nothing; this is what makes the three tests written in reply real",
     '            if (armed && armingWasRequested && !confirmLive)\n                set(false);',
     '            if (armed && !confirmLive)\n                set(false);'),

    (ENGINE,
     "the arming gate is deleted outright, so an Add form with the armed box UNCHECKED\n"
     "     still arms the relationship against a live account",
     '            if (armed && armingWasRequested && !confirmLive)\n                set(false);',
     ''),
]


def run():
    b = subprocess.run(['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    if 'Build succeeded' not in b.stdout:
        return 'BUILD FAILED'
    r = subprocess.run(['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
                       cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith('RESULTS:'):
            return line.strip()
    return 'NO RESULT LINE'


originals = {p: open(p, encoding='utf-8').read() for p in (ENGINE, WINDOW)}

print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print('\nREFUSING TO RUN: baseline is RED (%s failing). Every mutant would score '
          'KILLED on pre-existing failures and this battery would prove nothing.' % m.group(2))
    sys.exit(2)

survivors = []
for path, name, old, new in MUTANTS:
    src = originals[path]
    if src.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, src.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(path, 'w', encoding='utf-8', newline='').write(src.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    # A crash is a kill: the mutation stopped the suite completing.
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    open(path, 'w', encoding='utf-8', newline='').write(src)

for p, src in originals.items():
    open(p, 'w', encoding='utf-8', newline='').write(src)
print('\nrestored originals;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
