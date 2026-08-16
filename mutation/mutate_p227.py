"""Mutation battery for P2-27 / P1-117 (the shared guard-config value validator).

Every mutant reinstates a real defect, and several of them are defects THIS TICKET ACTUALLY
SHIPPED before being caught -- which is the reason to read the list rather than the score:

  * mutant 2 is the ticket's own first spec. It said the guard's modes are shadow/live/DISABLED,
    the loop implemented exactly that, 1792 tests went green and BOTH reviewers returned
    APPROVE(0). `disabled` is TradeCopierEngine's mode, not the guard's.
  * mutant 3 is the ticket's second spec. It said case-INSENSITIVE, and preflight is ordinal.
  * mutant 9 is the first implementation's message text, which told an operator that `PURE` was
    refused because "mode is case-sensitive" -- a fix that does not work. It passed every gate
    and one reviewer's APPROVE(0), and was caught by hand-reading the patch.

⚠️ THE POINT OF THE AGREEMENT MUTANTS (2, 3). This class has one job -- never accept a config
that preflight will refuse -- and the test that pins it drives seven modes through BOTH this
validator and the real RunPreflight(). A mutant that widens the accepted set must therefore die
on that test and not on a hand-written expectation, which is what makes the pinning honest.

⚠️ MUTANT 7 IS THE ONE TO KNOW. Every requirement in this ticket is about REFUSING something, so
an unconditional refusal satisfies all of them and ships a validator that makes the endpoint
unusable. Same shape as P2-115's constant `false` and F-17's always-refuse. The six acceptance
cases are the only thing that bans it.

Exits non-zero on any survivor.
"""
import os, re, subprocess, sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, 'addons', 'GuardConfigEdit.cs')

MUTANTS = [
    # ---- 1. the defect verbatim: the validator validates nothing ----
    ("the validator accepts everything, which is the state before this class existed",
     '            string modeProblem = RefuseMode(mode);',
     '            if (true) return null;\n            string modeProblem = RefuseMode(mode);'),

    # ---- 2. the ticket's OWN first spec ----
    ("`disabled` is accepted again -- the COPIER's mode on the guard's field, which preflight "
     "then refuses, leaving the guard disarmed at the next restart",
     '            if (mode == "shadow" || mode == "live")',
     '            if (mode == "shadow" || mode == "live" || mode == "disabled")'),

    # ---- 3. the ticket's SECOND spec ----
    ("the mode match goes case-insensitive again, so `SHADOW` is accepted and preflight refuses it",
     '            if (mode == "shadow" || mode == "live")',
     '            if (string.Equals(mode, "shadow", StringComparison.OrdinalIgnoreCase)\n'
     '                || string.Equals(mode, "live", StringComparison.OrdinalIgnoreCase))'),

    # ---- 4. the core numeric rule ----
    ("a trailing drawdown of ZERO is accepted -- no limit at all, and GuardRules reports the "
     "rule Off while the API said applied",
     '            if (!(trailingDrawdown > 0.0))',
     '            if (trailingDrawdown < 0.0)'),

    # ---- 5. the NaN clause, which no test covered until the battery was written ----
    ("the obvious `<= 0` form comes back, which ACCEPTS NaN -- a limit no comparison can satisfy",
     '            if (!(trailingDrawdown > 0.0))',
     '            if (trailingDrawdown <= 0.0)'),

    # ---- 6. the other numeric rule ----
    ("a MinShadowSessions of -1 is accepted",
     '            if (minShadowSessions < 0)',
     '            if (minShadowSessions < -1)'),

    # ---- 7. the constant. Every requirement is a refusal, so this satisfies all of them ----
    ("the validator REFUSES EVERYTHING, which satisfies every negative requirement in the ticket "
     "and makes the endpoint unusable",
     '            string modeProblem = RefuseMode(mode);',
     '            if (true) return "refused";\n            string modeProblem = RefuseMode(mode);'),

    # ---- 8. partial writes ----
    ("an omitted mode is refused, so every PARTIAL write fails -- P2-41's merge is the reason "
     "the endpoint takes partial bodies at all",
     '            if (string.IsNullOrWhiteSpace(mode))',
     '            if (mode == null)'),

    # ---- 9. the first implementation's message defect ----
    ("the case advice goes back onto `pure`, telling the operator to fix a case that is not the "
     "problem -- P3-118's defect committed by the class built to prevent it",
     '                return "Mode \'" + mode + "\' is recognised but NOT IMPLEMENTED -- only \'live\' acts, "',
     '                return "Mode \'" + mode + "\' is case-sensitive and not implemented -- only \'live\' acts, "'),

    # ---- 10. the refusal has to name the FIELD ----
    ("the trailing-drawdown refusal stops naming the field, so a UI renders it beside one of a "
     "dozen inputs with nothing saying which",
     '                return "Trailing drawdown must be greater than zero. Zero is not a tight limit, "\n'
     '                     + "it is no limit -- the guard reports the rule as off.";',
     '                return "Invalid value.";'),

    # ---- 11. the refusal has to name the alternatives (P1-90's standard) ----
    ("the mode refusal stops naming the valid modes",
     '            return "Mode \'" + mode + "\' is not a guard mode. Valid: \'shadow\', \'live\'.";',
     '            return "Mode is not valid.";'),
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


original = open(SRC, encoding='utf-8').read()
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
    open(SRC, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    mm = re.search(r'Failed = (\d+)', res)
    # A crash is a kill: the mutation stopped the suite completing.
    killed = ('BUILD FAILED' in res) or ('NO RESULT LINE' in res) \
        or (mm is not None and int(mm.group(1)) > 0)
    print(f'  [{"KILLED" if killed else "SURVIVED"}] {name}: {res}')
    if not killed:
        survivors.append(name)

open(SRC, 'w', encoding='utf-8', newline='').write(original)
print('\nrestored original;', run())
print('\nSURVIVORS:', survivors if survivors else 'none')

sys.exit(1 if survivors else 0)
