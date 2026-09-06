"""B9 fork change #3: CoverTheQueen/FixedTP1TP2 breakeven fires on an INTRABAR touch.

The close-only breakeven check left the runner's stop at full risk through a bar
that reached the queen/TP1 level and closed back -- the protection arriving a bar
late, exactly when it mattered most. The fork carried this change; the decision
(2026-09-05) was to land it. This gate keeps it landed.

Reads `strategies/Vinay/RiskManagerBase.cs` the way check_entry_refusals_reported.py
does: no test build compiles this file (it names NinjaTrader.* types), so the
assertions are structural -- but each is checked in its FAILING direction too, so a
rewrite that satisfies the letter and not the intent fails here.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TARGET = os.path.join(REPO, 'strategies', 'Vinay', 'RiskManagerBase.cs')


def extract_method(src: str, name: str) -> str:
    """Brace-match the method body, the way check_entry_refusals_reported.py does."""
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


def strip_comments(src: str) -> str:
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    src = re.sub(r'^\s*//.*$', '', src, flags=re.M)
    src = re.sub(r'^\s*///.*$', '', src, flags=re.M)
    return src


def check(src: str):
    """Returns (failures, notes). Pure, so --selftest can drive it both ways."""
    fails, notes = [], []
    code = strip_comments(src)

    cq = extract_method(code, 'ManageCoverTheQueen')
    fx = extract_method(code, 'ManageFixedTP1TP2')
    if not cq:
        fails.append('ManageCoverTheQueen not found -- the gate cannot inspect a '
                     'region it cannot locate.')
        return fails, notes
    if not fx:
        fails.append('ManageFixedTP1TP2 not found -- the gate cannot inspect a '
                     'region it cannot locate.')
        return fails, notes

    # CoverTheQueen: the queen trigger must read the bar's High/Low, not just the
    # close. A close-only comparison (`currentPrice >= entryPrice + queenPts`)
    # was the defect; the touch form is `High[0] >= ...` / `Low[0] <= ...`.
    cq_touch = bool(re.search(r'High\[0\]\s*>=\s*entryPrice\s*\+\s*queenPts', cq)
                    and re.search(r'Low\[0\]\s*<=\s*entryPrice\s*-\s*queenPts', cq))
    notes.append('ManageCoverTheQueen: intrabar touch trigger present = %s'
                 % cq_touch)
    if not cq_touch:
        fails.append('ManageCoverTheQueen does not trigger the breakeven on the '
                     'bar TOUCHING the queen level (High[0]/Low[0]); it compares '
                     'the close alone, so the runner stays at full risk through a '
                     'bar that reached the target and closed back.')

    # FixedTP1TP2: the runner breakeven fires on leg1 filled OR the bar touching
    # the captured TP1 price.
    fx_touch = bool(re.search(r'touched', fx)
                    and re.search(r'High\[0\]\s*>=\s*customTp1Price', fx)
                    and re.search(r'Low\[0\]\s*<=\s*customTp1Price', fx))
    notes.append('ManageFixedTP1TP2: intrabar touch trigger present = %s' % fx_touch)
    if not fx_touch:
        fails.append('ManageFixedTP1TP2 does not fire the breakeven on the bar '
                     'TOUCHING the leg1 level; close-only again.')

    # The captured TP1 price must exist and be captured at entry.
    if not re.search(r'protected double customTp1Price\s*=\s*double\.NaN', code):
        fails.append('the `customTp1Price` field is gone -- the intrabar trigger '
                     'has nothing to compare against.')
    enter = extract_method(code, 'EnterTrade')
    if not enter or 'customTp1Price    = double.NaN;   // set below for FixedTP1TP2' not in enter:
        fails.append('EnterTrade no longer RESETS customTp1Price at entry -- a '
                     'stale TP1 from a previous trade would fire the breakeven on '
                     'the wrong level.')
    fx_body_capture = re.search(r'customTp1Price\s*=\s*tp1;', extract_method(code, 'EnterTrade') or '')
    if not fx_body_capture:
        fails.append('EnterTrade no longer CAPTURES customTp1Price from the '
                     'FixedTP1TP2 branch -- the intrabar trigger is dead code.')

    return fails, notes


def selftest() -> int:
    """The negative direction, asserted rather than trusted."""
    good = open(TARGET, encoding='utf-8').read()
    cases = []

    f, _ = check(good)
    cases.append(('the real file passes', not f, f))

    # The regression this exists to catch: the touch reverted to close-only.
    bad = good.replace('? (High[0] >= entryPrice + queenPts)',
                       '? (currentPrice >= entryPrice + queenPts)', 1)
    bad = bad.replace(': (Low[0] <= entryPrice - queenPts)',
                      ': (currentPrice <= entryPrice - queenPts)', 1)
    f, _ = check(bad)
    cases.append(('a close-only CoverTheQueen FAILS',
                  any('close alone' in x for x in f), f))

    # The captured TP1 price gone.
    bad = good.replace('customTp1Price = tp1;', '// captured price deleted', 1)
    f, _ = check(bad)
    cases.append(('a missing TP1 capture FAILS',
                  any('dead code' in x for x in f), f))

    ok = True
    for name, passed, fails in cases:
        print('  [%s] %s' % ('ok  ' if passed else 'FAIL', name))
        for x in fails:
            print('        %s' % x)
        ok = ok and passed
    print('  selftest: %d case(s)' % len(cases))
    return 0 if ok else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(selftest())
    src = open(TARGET, encoding='utf-8').read()
    fails, notes = check(src)
    for n in notes:
        print('  note: %s' % n)
    for f in fails:
        print('  FAIL: %s' % f)
    print('OK: the intrabar breakeven is landed in ManageCoverTheQueen and '
          'ManageFixedTP1TP2' if not fails else
          'FAIL: %d problem(s)' % len(fails))
    sys.exit(0 if not fails else 1)