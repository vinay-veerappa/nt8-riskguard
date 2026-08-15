"""Mutation battery for UI4 (the producer for the guard rule inventory).

UI3's battery proved the REGISTRY honest. This one proves the BUILDER cannot take
that honesty back, which is a different job: every guarantee UI3 bought is now
mediated by one method, and each of the mutants below is a plausible way of
writing that method so the page is calmer than the box.

Every mutant makes the snapshot MORE REASSURING than the truth. That is the only
direction that can cost money here, and it is why there are no "does it crash"
mutants: a crash blanks the page, which is bad, but a green row on a rule that
cannot fire is what gets an account blown.

The five that matter most:

  * MUTANT 2 makes CanAct ignore the MODE, so `shadow` reports Enforcing. This box
    has spent its entire life in shadow-and-armed, and "armed" is precisely the
    word an operator reads as "protected". If it survives, the mode indicator is
    decorative.

  * MUTANT 5 turns a THROWN evaluator into a healthy reading. A rule that could
    not be checked would then report exactly like one that passed -- the single
    worst outcome available to this file, and the easiest to write by accident
    while "making the null-config case not throw".

  * MUTANT 8 hardcodes the news count inside the context. P2-25 restored at the
    last possible moment: the registry is correct, the rule is correct, and the
    number is forged on the way in.

  * MUTANT 9 substitutes a DEFAULT RiskConfig for the one passed in, so a box with
    no config loaded reports every default limit as though the operator had set
    it. That is `configured / evaluated / enforcing` collapsed into a lie.

  * MUTANT 6 stops populating UnevaluatedRules. A box with no accounts then renders
    an empty page, and "nothing to show" and "nothing is wrong" become the same
    picture -- the hazard this list was added to close.

MUTANTS 15/16 pin a fix rather than a behaviour: the registry accessors returned
their backing List, so any caller could Add a rule. Both are listed because the
defect was in TWO identical accessors, and a fix applied to only the one a test
names is how a widened surface survives.

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
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
SUITE = os.path.join(REPO, 'addons', 'PropFirmProtectionSuite.cs')

# (file, description, old, new)
MUTANTS = [
    # ---- CanAct: the two halves of "can this rule actually do anything" ----
    (RULES,
     "CanAct ignores ARMING, so a disarmed guard reports every rule as Enforcing",
     '            return mode == "live" && isArmed;',
     '            return mode == "live";'),

    (RULES,
     "CanAct ignores the MODE, so shadow-and-armed -- the state this box has lived in\n"
     "     for its entire life -- reports every rule as Enforcing",
     '            return mode == "live" && isArmed;',
     '            return isArmed;'),

    # ---- the DeriveState call: the builder's two chances to lie to the ladder ----
    (RULES,
     "the builder tells DeriveState the guard can always act, so the ladder is fed a\n"
     "     constant and the mode/arming rungs become unreachable",
     '                        row.State = DeriveState(def, reading, canAct, account.IsExcluded);',
     '                        row.State = DeriveState(def, reading, true, account.IsExcluded);'),

    (RULES,
     "the builder drops the EXCLUSION, so an account the guard was told to leave alone\n"
     "     reports its limits as enforcing",
     '                        row.State = DeriveState(def, reading, canAct, account.IsExcluded);',
     '                        row.State = DeriveState(def, reading, canAct, false);'),

    # ---- THE containment mutant ----
    (RULES,
     "an evaluator that THREW is turned into a healthy reading, so a rule that could not\n"
     "     be checked reports exactly like one that passed. The worst outcome this file has",
     '                            failureNote = ex.GetType().Name + ": " + ex.Message;',
     '                            failureNote = ex.GetType().Name + ": " + ex.Message;\n'
     '                            reading = new GuardRuleReading { EvidenceCount = 1 };'),

    # ---- the zero-account page ----
    (RULES,
     "UnevaluatedRules is never populated, so a box with no accounts renders an empty,\n"
     "     entirely reassuring page -- 'nothing to show' and 'nothing is wrong' made identical",
     '                    snapshot.UnevaluatedRules.Add(unevaluatedRow);',
     ''),

    (RULES,
     "rules with no evaluator are omitted from each ACCOUNT's inventory, so P1-77 is\n"
     "     invisible exactly where an operator looks for it",
     '                    for (int i = 0; i < accounts.Count; i++)\n'
     '                    {\n'
     '                        var accountRules = snapshot.Accounts[i];\n'
     '                        var row = new GuardRuleRow();',
     '                    for (int i = 0; i < 0; i++)\n'
     '                    {\n'
     '                        var accountRules = snapshot.Accounts[i];\n'
     '                        var row = new GuardRuleRow();'),

    # ---- the context: forging the evidence on the way IN ----
    (RULES,
     "the news count is hardcoded in the context, so P2-25 is restored at the last\n"
     "     possible moment -- correct registry, correct rule, forged input",
     '                            context.NewsEventCount = newsEventCount;',
     '                            context.NewsEventCount = 1;'),

    (RULES,
     "a DEFAULT RiskConfig is substituted for the one passed in, so a box with no config\n"
     "     loaded reports every default limit as though the operator had chosen it",
     '                            context.Config = config;',
     '                            context.Config = config ?? new RiskConfig();'),

    # ---- the header, which must describe the world the rows came from ----
    (RULES,
     "the snapshot's MODE is hardcoded to live, so rows derived in shadow sit under a\n"
     "     header claiming the guard is acting",
     '            snapshot.Mode = mode;',
     '            snapshot.Mode = "live";'),

    (RULES,
     "the snapshot always reports ARMED",
     '            snapshot.IsArmed = isArmed;',
     '            snapshot.IsArmed = true;'),

    # ---- the per-account flags, which are WHY a row is amber ----
    (RULES,
     "the excluded flag is dropped from the account row, so a wall of amber has no stated\n"
     "     cause and reads as a malfunction rather than a setting",
     '                accountRules.IsExcluded = account.IsExcluded;',
     '                accountRules.IsExcluded = false;'),

    (RULES,
     "the locked-out flag is dropped from the account row",
     '                accountRules.IsLockedOut = account.IsLockedOut;',
     '                accountRules.IsLockedOut = false;'),

    (RULES,
     "the account's EQUITY is dropped, so a page cannot tell a funded account from one of the\n"
     "     88 expired prop accounts the connection still lists -- and must either show 96 rows of\n"
     "     noise or hide accounts on a guess",
     '                accountRules.AccountEquity = account.AccountEquity;',
     '                accountRules.AccountEquity = 0;'),

    (RULES,
     "the account's trade count is dropped, so 'traded today' cannot rescue an account whose\n"
     "     equity has not synced yet -- and hiding a LIVE account is the one direction this\n"
     "     design refuses to fail in",
     '                accountRules.TradesToday = account.TradesToday;',
     '                accountRules.TradesToday = 0;'),

    # ---- the evidence and the note, as DISPLAYED ----
    (RULES,
     "the row's evidence count is forged to 1, so the state is right and the number beside\n"
     "     it says the news shield is watching an event it does not have",
     '                            row.EvidenceCount = reading.EvidenceCount;',
     '                            row.EvidenceCount = 1;'),

    (RULES,
     "the reading's NOTE is dropped, so an INERT row no longer says WHAT is missing --\n"
     "     which is the only part of it that tells the operator what to do",
     '                            row.Note = reading.Note;',
     '                            row.Note = null;'),

    # REPLACES A MUTANT THAT SURVIVED AND WAS RIGHT TO. It deleted a last-resort note
    # covering "an evaluator returns null rather than throwing" -- which no evaluator
    # does, so nothing could reach it. Unreachable defensive state is unpinnable by
    # definition, and the registry is read-only now, so a test cannot even inject a
    # null-returning rule to reach it. The fallback was DELETED and the case made
    # impossible instead: returning a reading is a contract asserted over every rule.
    # This mutant breaks that contract at its source, so the trade is not a loss of
    # coverage.
    (RULES,
     "the shared reading helper returns null, so EVERY evaluator silently produces no\n"
     "     reading and every rule goes red with nothing to say -- the contract that replaced\n"
     "     an unreachable fallback has to be worth more than the fallback was",
     '            return new GuardRuleReading { CurrentValue = current, Limit = limit, EvidenceCount = evidence, Note = note };',
     '            return null;'),

    (RULES,
     "the null-account guard is removed, so a null list throws and blanks the inventory",
     '            if (accounts == null) accounts = new List<RiskGuardAddOn.AccountStateSnapshot>();',
     ''),

    # ---- the registry accessors: the fix, and its twin ----
    (RULES,
     "the RULES accessor hands back its backing list again, so any caller can Add a rule\n"
     "     and claim protection this codebase does not implement",
     '        public static IList<GuardRuleDefinition> Rules { get { return _rules.AsReadOnly(); } }',
     '        public static IList<GuardRuleDefinition> Rules { get { return _rules; } }'),

    (RULES,
     "the NON-RULES accessor hands back its backing list -- the twin of the mutant above,\n"
     "     and the one a fix aimed at the test's wording would have missed",
     '        public static IList<GuardNonRule> NonRules { get { return _nonRules.AsReadOnly(); } }',
     '        public static IList<GuardNonRule> NonRules { get { return _nonRules; } }'),

    # ---- the host edge ----
    (GUARD,
     "BuildGuardSnapshot reports the guard as live regardless of its real mode",
     '                mode = _mode;',
     '                mode = "live";'),

    (SUITE,
     "the suite hardcodes its news-event count, so every caller -- including the one rule\n"
     "     P2-25 is about -- is told an event is loaded when none is",
     '                    return _newsEvents.Count;',
     '                    return 1;'),
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


originals = {p: open(p, encoding='utf-8').read() for p in (RULES, GUARD, SUITE)}

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
    original = originals[path]
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
    open(path, 'w', encoding='utf-8', newline='').write(original)

for p, s in originals.items():
    open(p, 'w', encoding='utf-8', newline='').write(s)
print('\nrestored originals;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
