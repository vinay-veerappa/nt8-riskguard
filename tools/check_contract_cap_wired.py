"""P1-149 sub-task 2, made mechanical: the strategy-side contract cap must stay WIRED.

`RiskGatekeeper.CanTradeSize` -> `ContractCapGate` is the pre-trade size refusal for the
RiskManagerBase entry path. ContractCapGate is pure and mutation-tested (`RiskGuardTests.csproj`
compiles and EXECUTES it); RiskGatekeeper and RiskManagerBase name `NinjaTrader.*` types, so NO
test build compiles them (mirrors McpBridgeAddOn.cs's exclusion, P2-27). That leaves ONE link with
no executable coverage: does `RiskManagerBase.EnterTrade` actually CALL `CanTradeSize` before it
places the order? A decision written inside an NT8-typed file can only be checked by reading the
text -- so this gate reads it.

This is the [[dead-safety-machinery-gate]] class, narrowed to the one call that closes the
enforcement gap. A cap that is configured, rendered in the UI and evaluated reactively, but whose
pre-trade half is commented out or stranded in a dead branch, is worse than no cap: it reads as
protection that does not exist ([[configured-evaluated-enforcing]]).

⚠️ A CALL IN A COMMENT OR AN `if (false)` IS NOT A CALL. Three times in this repo a text search has
reported a load-bearing method WIRED while its only call site was dead
([[a-source-gate-must-assert-the-condition]], [[a-backstop-at-a-choke-point-is-unkillable]]). So
comments and strings are masked and dead branches are deleted BEFORE the search, and the negative
direction is asserted in the self-test rather than trusted.

Exits 1 if the call is absent, or present only in a comment / dead branch.
"""
import os
import re
import sys

# ⚠️ Windows defaults stdout to cp1252; this gate prints plan text full of non-ASCII, and only when
# FAILING -- so without this it dies exactly when it has something to say. [[a-battery-must-reach-its-restore-line]]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TARGET = os.path.join(REPO, 'strategies', 'Vinay', 'RiskManagerBase.cs')
# The value SOURCE. Enforcement without a cap value is inert -- the exact defect found 2026-08-21:
# RegisterAndMonitor built AccountRiskParameters without MaxContractsPerAccount, so the cap was always
# 0 and the refusal could never fire. This gate now also proves the cap is populated FROM the guard's
# single source of truth (RiskConfig.Sizing.MaxContractsPerAccount), not left to default or duplicated.
TARGET_ADDON = os.path.join(REPO, 'addons', 'RiskManagerAddOn.cs')

CALL = re.compile(r'\bRiskGatekeeper\s*\.\s*CanTradeSize\s*\(')
# The cap flows into the registered parameters from ResolveContractCap(), and ResolveContractCap()
# reads the guard's ONE number. Both must be live for the cap to be non-zero and single-sourced.
CAP_ASSIGN = re.compile(r'MaxContractsPerAccount\s*=\s*ResolveContractCap\s*\(')
CAP_SOURCE = re.compile(r'\bSizing\s*\.\s*MaxContractsPerAccount\b')
DEAD_HEAD = re.compile(r'\b(?:if|while)\s*\(\s*(?:false|0)\s*\)')


def mask_comments_and_strings(text):
    """Comments and string literals -> spaces, newlines kept so line numbers are unchanged. A call
    NAMED in a doc comment or a log string is not a call; without this, such a mention reads as
    wiring (the regression `check_no_dead_safety_machinery.py` documents)."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] != '\n':
                out[i] = ' '; i += 1
        elif c == '/' and i + 1 < n and text[i + 1] == '*':
            while i < n and not (text[i] == '*' and i + 1 < n and text[i + 1] == '/'):
                if text[i] != '\n':
                    out[i] = ' '
                i += 1
            for _ in range(2):
                if i < n:
                    out[i] = ' '; i += 1
        elif c == '@' and i + 1 < n and text[i + 1] == '"':
            out[i] = ' '; i += 2; out[i - 1] = ' '
            while i < n:
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        out[i] = out[i + 1] = ' '; i += 2; continue
                    out[i] = ' '; i += 1; break
                if text[i] != '\n':
                    out[i] = ' '
                i += 1
        elif c == '"' or c == "'":
            quote = c
            out[i] = ' '; i += 1
            while i < n and text[i] != quote:
                if text[i] == '\\' and i + 1 < n:
                    out[i] = out[i + 1] = ' '; i += 2; continue
                if text[i] != '\n':
                    out[i] = ' '
                i += 1
            if i < n:
                out[i] = ' '; i += 1
        else:
            i += 1
    return ''.join(out)


def strip_dead_branches(text):
    """Blank `if (false)` / `while (0)` bodies (braced or single-statement) and `#if false`. Searched
    and walked on the MASKED copy so a `;` in a string cannot move a boundary."""
    text = mask_comments_and_strings(text)
    out = []
    i = 0
    while True:
        m = DEAD_HEAD.search(text, i)
        if m is None:
            out.append(text[i:]); break
        out.append(text[i:m.start()])
        j = m.end()
        while j < len(text) and text[j] in ' \t\r\n':
            j += 1
        if j < len(text) and text[j] == '{':
            depth = 0
            while j < len(text):
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        j += 1; break
                j += 1
        else:
            depth = 0
            while j < len(text):
                if text[j] in '({[':
                    depth += 1
                elif text[j] in ')}]':
                    depth -= 1
                elif text[j] == ';' and depth <= 0:
                    j += 1; break
                j += 1
        out.append('\n' * text.count('\n', m.start(), j))
        i = j
    stripped = ''.join(out)
    stripped = re.sub(r'#if\s+(?:false|0)\b.*?#endif',
                      lambda mm: '\n' * mm.group(0).count('\n'),
                      stripped, flags=re.DOTALL)
    return stripped


def live_lines(text, regex):
    """Line numbers where `regex` matches in real (non-comment, non-dead) code."""
    stripped = strip_dead_branches(text)
    return [n for n, line in enumerate(stripped.splitlines(), 1) if regex.search(line)]


def live_call_sites(text):
    """Line numbers of real (non-comment, non-dead) `RiskGatekeeper.CanTradeSize(` call sites."""
    return live_lines(text, CALL)


def self_test():
    """⚠️ THE NEGATIVE CONTROL, run on every invocation. The dangerous direction is a FALSE WIRED:
    a commented-out or dead call reported as present, letting a disarmed cap ship. A detector with
    no negative test fires on everything."""
    live = 'void EnterTrade() { var d = RiskGatekeeper.CanTradeSize(a,1,s,p,q); }'
    commented = '// RiskGatekeeper.CanTradeSize(a,1,s,p,q) -- was here\nvoid EnterTrade() {}'
    block_comment = '/* RiskGatekeeper.CanTradeSize(a,1,s,p,q); */\nvoid EnterTrade() {}'
    dead_inline = 'void EnterTrade() { if (false) RiskGatekeeper.CanTradeSize(a,1,s,p,q); }'
    dead_block = 'void EnterTrade() { if (false)\n{\n  RiskGatekeeper.CanTradeSize(a,1,s,p,q);\n}\n}'
    in_string = 'void EnterTrade() { Log("call RiskGatekeeper.CanTradeSize(); really"); }'
    absent = 'void EnterTrade() { EnterLong(1, "x"); }'

    problems = []
    if not live_call_sites(live):
        problems.append('a plain call was NOT detected -- the gate would fail on wired code')
    for label, src in (('a comment', commented), ('a block comment', block_comment),
                       ('a string literal', in_string),
                       ('an inline if (false)', dead_inline),
                       ('a braced if (false)', dead_block),
                       ('no call at all', absent)):
        if live_call_sites(src):
            problems.append('a call present only in %s was reported WIRED -- a disarmed cap '
                            'would pass this gate' % label)
    # Value-source controls: the cap must be POPULATED from the guard's number, live.
    assign_live = 'var p = new AccountRiskParameters { MaxContractsPerAccount = ResolveContractCap() };'
    assign_dead = '// MaxContractsPerAccount = ResolveContractCap() -- removed\nvar p = new X();'
    source_live = 'int ResolveContractCap() { return cfg.Sizing.MaxContractsPerAccount; }'
    source_dead = '// return cfg.Sizing.MaxContractsPerAccount;\nint ResolveContractCap(){return 0;}'
    if not live_lines(assign_live, CAP_ASSIGN):
        problems.append('a live MaxContractsPerAccount = ResolveContractCap() was NOT detected')
    if live_lines(assign_dead, CAP_ASSIGN):
        problems.append('a commented-out cap assignment was reported wired -- an inert cap would pass')
    if not live_lines(source_live, CAP_SOURCE):
        problems.append('a live Sizing.MaxContractsPerAccount read was NOT detected')
    if live_lines(source_dead, CAP_SOURCE):
        problems.append('a commented-out cap-source read was reported wired')
    if problems:
        print('SELF-TEST FAILED -- this gate cannot be trusted:\n')
        for p in problems:
            print('  * ' + p)
        sys.exit(1)


self_test()

if not os.path.exists(TARGET):
    print('FAILED: %s does not exist. RiskManagerBase is the strategy-side consumer of the '
          'contract cap; if it moved, update this gate to its new path.' % TARGET)
    sys.exit(1)

text = open(TARGET, encoding='utf-8').read()
sites = live_call_sites(text)

failures = []
print('Contract-cap ENFORCEMENT in strategies/Vinay/RiskManagerBase.cs:')
if sites:
    print('  [WIRED] RiskGatekeeper.CanTradeSize called at line(s): %s'
          % ', '.join(str(s) for s in sites))
else:
    print('  [DEAD]  RiskGatekeeper.CanTradeSize is called by NOTHING live in RiskManagerBase.cs.')
    failures.append('the pre-trade refusal is not wired on the entry path (absent, commented, or in a '
                    'dead branch) -- wire RiskGatekeeper.CanTradeSize into EnterTrade or delete it.')

print('\nContract-cap VALUE SOURCE in addons/RiskManagerAddOn.cs:')
if not os.path.exists(TARGET_ADDON):
    failures.append('%s does not exist -- the registrar that populates the cap moved.' % TARGET_ADDON)
else:
    addon = open(TARGET_ADDON, encoding='utf-8').read()
    assign = live_lines(addon, CAP_ASSIGN)
    source = live_lines(addon, CAP_SOURCE)
    if assign:
        print('  [WIRED] MaxContractsPerAccount = ResolveContractCap() at line(s): %s'
              % ', '.join(str(s) for s in assign))
    else:
        print('  [DEAD]  the registered parameters never get MaxContractsPerAccount from ResolveContractCap().')
        failures.append('RiskManagerAddOn does not populate MaxContractsPerAccount -- the cap defaults '
                        'to 0 and the refusal can never fire (the inert-cap defect of 2026-08-21).')
    if source:
        print('  [WIRED] reads Sizing.MaxContractsPerAccount (guard single source) at line(s): %s'
              % ', '.join(str(s) for s in source))
    else:
        print('  [DEAD]  ResolveContractCap never reads Sizing.MaxContractsPerAccount.')
        failures.append('the cap is not read from the guard config (RiskConfig.Sizing.MaxContractsPerAccount) '
                        '-- a second, divergent source is the defect [[a-second-reader-of-the-same-state]] warns of.')

if failures:
    print('\nFAILED:')
    for f in failures:
        print('  * ' + f)
    sys.exit(1)

print('\nOK: the contract cap is enforced on the entry path AND populated from the guard single source.')
sys.exit(0)
