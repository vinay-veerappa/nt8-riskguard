"""Every entry refusal in `CanEnterTrade` must REPORT its reason.

`RiskManagerBase.CanEnterTrade` computes nine distinct reasons to refuse an entry --
gatekeeper, account blown, done for day, paused after consecutive losses, max trades, two
time fences, and two daily-loss limits. Until 2026-09-05 each was surfaced ONLY through
`if (DebugMode && CurrentBar % 100 == 0) Log(...)`: off by default, and on 1% of bars when
on. So a strategy that quietly stopped entering had nine possible causes and, on 99% of
bars, a record of none of them.

⚠️ A REFUSAL A CONSUMER CANNOT READ IS INDISTINGUISHABLE FROM THE STRATEGY NOT HAVING A
SETUP. That is the whole defect: "no trade" and "the framework said no" look identical
downstream, and the analysis that reads the difference (tvDownloadOHLC's decision log) can
only see what this class tells it. Same family as [[an-alarm-wired-to-a-dead-output]] --
the reason was computed correctly and delivered to nobody.

WHY THIS IS A COUNT AND NOT AN ABSENCE CHECK. "No bare `return false`" passes vacuously
the day someone restructures `CanEnterTrade` into a different shape
([[a-code-move-disarms-a-source-gate]], [[closing-the-last-instance-disarms-the-gate]]).
So the gate asserts a POSITIVE: exactly N refusals route through `Blocked`, and the hook
`Blocked` calls is still virtual and still reachable. A presence gate fails loudly where an
absence gate passes silently.

`RiskManagerBase` names `NinjaTrader.*` types, so no test build compiles it -- reading the
text is the only option, which is why the negative direction is asserted in --selftest
rather than trusted ([[a-source-gate-must-assert-the-condition]]).

Exits 1 if a refusal path is unreported, or if the hook has been made private/non-virtual.
"""
import os
import re
import sys

# Windows defaults stdout to cp1252 and this gate prints only when FAILING, so without
# this it would die exactly when it has something to say.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TARGET = os.path.join(REPO, 'strategies', 'Vinay', 'RiskManagerBase.cs')

#: Measured 2026-09-05. EXACT, not `>=`: a tenth refusal path that forgets to report is the
#: regression this exists to catch, and `>=` would wave it through.
EXPECTED_REFUSALS = 9

BLOCKED_CALL = re.compile(r'return\s+Blocked\s*\(\s*"([A-Za-z0-9_]+)"\s*,')
BARE_FALSE = re.compile(r'^\s*return\s+false\s*;\s*$', re.M)
HOOK = re.compile(r'protected\s+virtual\s+void\s+OnEntryBlocked\s*\(\s*string\s+reason\s*,'
                  r'\s*int\s+currentTime\s*\)')
HELPER = re.compile(r'private\s+bool\s+Blocked\s*\(\s*string\s+reason\s*,\s*int\s+currentTime\s*\)')
CALLS_HOOK = re.compile(r'OnEntryBlocked\s*\(\s*reason\s*,\s*currentTime\s*\)\s*;')


def strip_dead(src: str) -> str:
    """Mask comments and strings. A call inside a comment is not a call, and this repo has
    had three text searches report a load-bearing method wired while its site was dead."""
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    src = re.sub(r'^\s*//.*$', '', src, flags=re.M)
    # Blank the DOC-comment bodies only; leave code strings, since the reason literals we
    # count live in code.
    src = re.sub(r'^\s*///.*$', '', src, flags=re.M)
    return src


def extract_method(src: str, name: str) -> str:
    """Brace-match the method body. Splitting on text would take the first `}` and measure
    a region that stops before the code in question ([[state-the-region-a-gate-inspects]])."""
    m = re.search(r'(private|protected|public)[^\n]*\b' + name + r'\s*\(', src)
    if not m:
        return ''
    i = src.index('{', m.end() - 1)
    depth, j = 0, i
    while j < len(src):
        if src[j] == '{':
            depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    return ''


def check(src: str):
    """Returns (failures, notes). Pure, so --selftest can drive it both ways."""
    fails, notes = [], []
    code = strip_dead(src)

    if not HOOK.search(code):
        fails.append('OnEntryBlocked(string reason, int currentTime) is not `protected '
                     'virtual`. A non-virtual hook cannot be observed by a subclass, so '
                     'every refusal becomes unreportable again.')
    if not HELPER.search(code):
        fails.append('the `Blocked(reason, currentTime)` helper is gone. Without one '
                     'funnel, each refusal site has to remember to report -- and the one '
                     'that forgets is silent.')
    elif not CALLS_HOOK.search(extract_method(code, 'Blocked')):
        fails.append('`Blocked` does not call OnEntryBlocked(reason, currentTime). It '
                     'returns false and tells nobody, which is the defect wearing the '
                     'fix\'s name.')

    body = extract_method(code, 'CanEnterTrade')
    if not body:
        fails.append('CanEnterTrade not found in %s -- the gate cannot inspect a region '
                     'it cannot locate, and reporting OK here would be vacuous.' % TARGET)
        return fails, notes

    reasons = BLOCKED_CALL.findall(body)
    notes.append('CanEnterTrade: %d refusal(s) reported: %s'
                 % (len(reasons), ', '.join(reasons) or '(none)'))
    if len(reasons) != EXPECTED_REFUSALS:
        fails.append('CanEnterTrade routes %d refusal(s) through Blocked(); expected %d. '
                     'If a path was legitimately added or removed, change '
                     'EXPECTED_REFUSALS in the same commit and say which.'
                     % (len(reasons), EXPECTED_REFUSALS))
    if any(not r.strip() for r in reasons):
        fails.append('a Blocked() call passes an empty reason -- "unstated" in a log is '
                     'the same dead end as no log.')

    bare = BARE_FALSE.findall(body)
    if bare:
        fails.append('CanEnterTrade still has %d bare `return false;` -- a refusal nobody '
                     'is told about. Route it through Blocked("<reason>", currentTime).'
                     % len(bare))
    return fails, notes


def selftest() -> int:
    """The negative direction, asserted rather than trusted."""
    good = open(TARGET, encoding='utf-8').read()
    cases = []

    f, _ = check(good)
    cases.append(('the real file passes', not f, f))

    # A tenth refusal that forgets to report.
    bad = good.replace('return Blocked("maxTrades", currentTime);',
                       'return false;', 1)
    f, _ = check(bad)
    # Matched on 'nobody is told about', not on the rendered literal: the message
    # contains 'return false;' WITH the semicolon, and asserting the semicolon-less
    # form silently matched nothing. [[a-substring-assertion-catches-the-identifier]]
    cases.append(('a bare `return false` FAILS',
                  any('nobody is told about' in x for x in f), f))

    # The hook demoted.
    bad = good.replace('protected virtual void OnEntryBlocked',
                       'private void OnEntryBlocked', 1)
    f, _ = check(bad)
    cases.append(('a non-virtual hook FAILS', any('protected virtual' in x for x in f), f))

    # The helper stops reporting -- returns false and tells nobody.
    bad = good.replace('            OnEntryBlocked(reason, currentTime);\n', '', 1)
    f, _ = check(bad)
    cases.append(('a Blocked() that reports nothing FAILS',
                  any('tells nobody' in x for x in f), f))

    # A refusal deleted outright: the count must notice.
    bad = good.replace('return Blocked("doneForDay", currentTime);',
                       'return true;', 1)
    f, _ = check(bad)
    cases.append(('a removed refusal FAILS the count',
                  any('expected %d' % EXPECTED_REFUSALS in x for x in f), f))

    ok = True
    for name, passed, detail in cases:
        print('  [%s] %s' % ('PASS' if passed else 'FAIL', name))
        if not passed:
            ok = False
            print('        got: %s' % detail)
    return 0 if ok else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        print('check_entry_refusals_reported --selftest')
        sys.exit(selftest())

    if not os.path.exists(TARGET):
        print('FAILED: %s does not exist.' % TARGET)
        sys.exit(1)

    # THE NEGATIVE CONTROL RUNS ALWAYS, not as a separate CI step. A control that
    # can be skipped eventually is, and `check_ci_runs_every_battery.py` requires
    # each gate to be wired EXACTLY ONCE -- so a second step invoking --selftest
    # would fail the wiring gate and the obvious fix would be to drop the control.
    print('check_entry_refusals_reported: negative controls')
    if selftest() != 0:
        print('\n  FAILED: the gate cannot detect its own defect. Nothing it says '
              'about the real file is worth reading.')
        sys.exit(1)
    print()

    failures, notes = check(open(TARGET, encoding='utf-8').read())
    print('Entry-refusal reporting in strategies/Vinay/RiskManagerBase.cs:')
    for n in notes:
        print('  %s' % n)
    if failures:
        print()
        for f in failures:
            print('  FAILED: %s' % f)
        sys.exit(1)
    print('  OK: every refusal reports its reason through the virtual hook.')
    sys.exit(0)
