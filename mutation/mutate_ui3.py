"""Mutation battery for UI3 (the guard-side rule inventory).

Why this battery exists, specifically:

This registry exists to stop a config field from lying about whether it protects
anything. So the failure mode that matters is not "it crashes" -- it is "it reports
a rule as ENFORCING when that rule has never been able to fire". Every mutant below
makes the inventory *more reassuring than the truth*, which is the only direction
that can hurt someone here.

The four that matter most:

  * MUTANT 1 makes a rule with NO EVALUATOR report Enforcing. That is P1-77's lie
    told by the very instrument built to expose it. If it survives, this file is
    worse than nothing, because it is believed.

  * MUTANT 7 hardcodes the news shield's evidence to 1. The shield then reports
    green while `_newsEvents` is empty and `IsInNewsWindow` can only ever return
    false -- P2-25, restored, and invisible to every static check.

  * MUTANT 8 gives the consistency cap a do-nothing evaluator. This is the exact
    "just fill in the null" instinct the header of GuardRules.cs warns against, and
    a battery is the only thing that can prove the warning is enforced rather than
    decorative.

  * MUTANT 13 hardcodes the firm rules' evidence. "Loaded but unmapped, so none can
    fire" is a state this system has ALREADY BEEN IN (handover section 0), and this
    mutant reinstates it while reporting green.

MUTANT 6 pins the enum ORDER. Its test is green at baseline by construction -- it
asserts a decision, not an acceptance criterion, so it was excluded from the
test-first gate and this mutant is the only thing behind it. Same handling as UI2's
"there is deliberately no parameterless LoadFromDisk".

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
RULES = os.path.join(REPO, 'addons', 'GuardRules.cs')

MUTANTS = [
    # ---- DeriveState: each rung, and each one makes the report MORE reassuring ----
    ("a rule with NO EVALUATOR reports Enforcing -- P1-77's lie, told by the instrument\n"
     "     built to expose it. The most dangerous single mutant in this battery",
     '            if (def == null || def.Evaluator == null) return GuardRuleState.ConfiguredNotEvaluated;',
     '            if (def == null) return GuardRuleState.ConfiguredNotEvaluated;'),

    ("an INERT rule reports as enforcing, so a rule whose evidence set is empty reads\n"
     "     exactly like one that is working -- P2-25 restored",
     '            if (reading.EvidenceCount <= 0) return GuardRuleState.Inert;',
     ''),

    ("an EXCLUDED account reports its rules as Enforcing, so the operator believes limits\n"
     "     apply to an account the guard has been told to leave alone",
     '            if (!guardCanAct || accountExcluded) return GuardRuleState.EvaluatedNotEnforcing;',
     '            if (!guardCanAct) return GuardRuleState.EvaluatedNotEnforcing;'),

    ("shadow mode reports as Enforcing -- every rule on the box claims it can act when\n"
     "     none of them can. This is the whole point of the mode indicator",
     '            if (!guardCanAct || accountExcluded) return GuardRuleState.EvaluatedNotEnforcing;',
     '            if (accountExcluded) return GuardRuleState.EvaluatedNotEnforcing;'),

    ("a rule switched OFF by the operator reports INERT, which reads as a defect. The\n"
     "     inverse error: crying wolf about a deliberate choice trains the operator to\n"
     "     ignore red rows, which is how a real one gets missed",
     '            if (reading.DisabledByConfig) return GuardRuleState.Disabled;',
     ''),

    # ---- the ordering, whose test is green at baseline ----
    ("the worst state stops sorting first, so a UI ordering by severity buries\n"
     "     CONFIGURED-not-EVALUATED underneath the healthy rows",
     '        ConfiguredNotEvaluated = 0,',
     '        ConfiguredNotEvaluated = 9,'),

    # ---- THE evidence-count mutants: each one turns an INERT rule green ----
    # ⚠️ Re-anchored 2026-08-15 by P2-113, which gave the news events FILE its own rule -- and that
    # rule's evaluator reports the same event count, so this find-string went from one match to
    # two. check_anchors.py refuses a 2-match anchor for the reason that matters here: a mutant
    # that could land on either of two rules is not evidence about the one it names. The anchor
    # now carries the trailing `null)` argument, which only the shield's healthy branch has.
    ("the news shield hardcodes its evidence to 1, so it reports green with ZERO events\n"
     "     loaded and IsInNewsWindow structurally unable to return true. P2-25, and\n"
     "     invisible to every static check",
     '                            : R(null, null, c.NewsEventCount, null)',
     '                            : R(null, null, 1, null)'),

    # Re-anchored 2026-08-13 by F-9. The evidence expression this used to find --
    # `AccountFirmMap.Count` -- is GONE, because counting the whole map on a PerAccount rule
    # was itself a defect: one mapped account greened all 96 of the live box's accounts. The
    # evidence is now per-account (`mapped ? 1 : 0`), so the mutant that proves the same thing
    # is hardcoding THAT to 1. check_anchors.py caught the stale find-string; without it this
    # entry would have printed [SKIP] and scored a survivor for the rest of its life.
    ("the firm rules hardcode their evidence, so 'loaded but UNMAPPED, therefore none can\n"
     "     fire' reports green -- a state this system has already been in",
     '                        sub.Amount, mapped && HasEquityReading(c.Account) ? 1 : 0, note);',
     '                        sub.Amount, 1, note);'),

    # ---- the escape route the fix for the first three survivors OPENED ----
    ("a collection-backed rule loses its EvidenceLabel, so it is silently EXEMPTED from the\n"
     "     empty-collection check. This hole did not exist before that fix: scoping the check\n"
     "     to labelled rules is what made a missing label mean 'do not check me'",
     '                EvidenceLabel = "news events loaded",\n',
     ''),

    ("an EMPTY blocked-instruments list reports green, so 'nothing is blocked' looks\n"
     "     identical to 'blocking is working'",
     '                Evaluator = c => R(null, null,\n'
     '                    c.Config.BlockedInstruments == null ? 0 : c.Config.BlockedInstruments.Count)',
     '                Evaluator = c => R(null, null, 1)'),

    ("the aggregate contract cap hardcodes its evidence, so a cap across ZERO known\n"
     "     accounts reports as enforcing",
     '                    : R(null, c.Config.Sizing.MaxContractsAggregate,\n'
     '                        c.AllAccounts == null ? 0 : c.AllAccounts.Count)',
     '                    : R(null, c.Config.Sizing.MaxContractsAggregate, 1)'),

    # ---- THE "just fill in the null" mutant ----
    # P1-77 REPOINTED THIS ONTO THE REAL EVALUATOR. It used to ADD a do-nothing evaluator to a
    # rule that had none; the cap now HAS a working one, so the same hazard is NEUTERING it --
    # strictly stronger, because the row keeps looking answered while the rule evaluates nothing
    # and the config goes on advertising a 35% cap. Repointed, not retired.
    ("the consistency cap's evaluator always takes its DISABLED branch, so the rule reports a\n"
     "     tidy 'disabled' forever and never evaluates a single account -- an honest-looking row\n"
     "     over a cap that enforces nothing",
     # ⚠️ The anchor carries the R(...) line as well, because the cap and its THRESHOLD entry
     # share an identical evaluator opening -- two matches, which check_anchors.py rejects. A
     # mutant that could land on either of two rules is not evidence about the one it names.
     '                Evaluator = c => c.PropConfig == null || !c.PropConfig.EnableConsistencyCap\n'
     '                    ? Off("consistency cap disabled")\n'
     '                    : R(c.Account == null ? (double?)null : c.Account.RealizedPnL,',
     '                Evaluator = c => true || c.PropConfig == null || !c.PropConfig.EnableConsistencyCap\n'
     '                    ? Off("consistency cap disabled")\n'
     '                    : R(c.Account == null ? (double?)null : c.Account.RealizedPnL,'),

    # ---- the completeness gate itself ----
    ("a rule is DELETED from the registry, leaving its config field classified by nothing.\n"
     "     This is how P1-77, P2-25 and P2-78 all reached production, so the gate that\n"
     "     catches it must be proven to fire",
     # P1-81 DELETED the "Prop suite armed" entry this used to typo -- together with the config
     # leaf it classified, which is the correct way for a registry entry to disappear. Repointed
     # onto a rule that still exists; the gate under test is the COMPLETENESS one, not that entry.
     '                Name = "News events file", ConfigPath = "PropFirm.LocalNewsEventsFilePath",',
     '                Name = "News events file", ConfigPath = "PropFirm.LocalNewsEventsFilePathTYPO",'),

    ("a non-rule loses its REASON, so the escape hatch becomes a way to make an\n"
     "     inconvenient field go quiet without saying why",
     '            new GuardNonRule { ConfigPath = "Mode", Reason = "the guard\'s enforcement mode; it decides whether rules can ACT and is reported on the snapshot itself, not as a rule" },',
     '            new GuardNonRule { ConfigPath = "Mode", Reason = "" },'),

    # ⚠️ REPOINTED TWICE, and the second move is the interesting one. This mutant used to blank a
    # PARTICULAR rule's UnevaluatedReason: first the cap threshold's (P1-77 gave that one a real
    # evaluator), then the news events file's. P2-113 gave THAT one an evaluator too -- and it was
    # the last rule in the registry without one, so there is no longer any instance of the thing
    # this mutant used to corrupt.
    #
    # The instinct at that point is to retire the mutant. That would be wrong: the requirement is
    # not "this rule states its reason", it is "a rule that nothing evaluates cannot report red in
    # silence", and that requirement outlives every instance of it. So the mutant moves DOWN to the
    # mechanism -- the assignment in BuildSnapshot that carries the reason onto the row. It is
    # killed by the synthetic unevaluated rule the tests now inject, which is the same repair the
    # tests took: keep the subject, supply the instance.
    #
    # Strictly stronger than what it replaced. The old version could only ever prove one rule's
    # text was present; this proves no unevaluated rule of ANY kind can render mute.
    ("the reason is dropped on its way onto the row, so a rule nothing evaluates reports red\n"
     "     in silence -- and a red row with no cause is noise, which is how an operator learns\n"
     "     to ignore red rows",
     '                    unevaluatedRow.Note = def.UnevaluatedReason;',
     '                    unevaluatedRow.Note = null;'),

    # ---- P2-113: the row that told the operator the file was read by nothing ----------
    ("the news events file rule loses its evaluator and goes back to reporting\n"
     "     CONFIGURED-and-not-EVALUATED -- P2-113 exactly, and it is the FALSE-RED direction,\n"
     "     which is not the harmless one: a red row that is wrong teaches an operator to\n"
     "     discount red rows, and this one was 97 of them on every poll",
     '                    ? Off("no news events file configured")\n'
     '                    : R(null, null, c.NewsEventCount,\n'
     '                        c.NewsEventsLoadStatus ?? "the load outcome was not reported to this snapshot")',
     '                    ? Off("no news events file configured")\n'
     '                    : Off("no news events file configured")'),

    ("a news events file that loaded NOTHING reports as Enforcing, which is the P2-113 fix\n"
     "     overshooting into the reassuring direction -- the failure mode the whole registry\n"
     "     exists to prevent",
     '                    : R(null, null, c.NewsEventCount,\n'
     '                        c.NewsEventsLoadStatus ?? "the load outcome was not reported to this snapshot")',
     '                    : R(null, null, 1,\n'
     '                        c.NewsEventsLoadStatus ?? "the load outcome was not reported to this snapshot")'),

    ("the load status is dropped from the row, so 'your news file is missing', 'your news\n"
     "     file is corrupt' and 'your news file is empty' all render as the same INERT row --\n"
     "     the three silent failures P2-113 exists to tell apart",
     '                        c.NewsEventsLoadStatus ?? "the load outcome was not reported to this snapshot")\n'
     '            },',
     '                        null)\n'
     '            },'),
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


original = open(RULES, encoding='utf-8').read()
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
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(RULES, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
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
    open(RULES, 'w', encoding='utf-8', newline='').write(original)

open(RULES, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
