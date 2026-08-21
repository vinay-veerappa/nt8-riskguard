"""Mutation battery for P2-147: a null-Order execution is classified by the reconnect-replay window.

Measured 2026-08-21: 537/537 null-Order copier executions arrived INSIDE the reconnect-replay window
(0 outside). They are NT8 re-sending the session on connect -- historical fills, already Filled, no
Order -- and copying one would manufacture a phantom follower position, so the drop is correct. The
copier now tells the expected connect-replay case (dropped quietly, EXEC_REPLAY_IGNORED) from the
never-observed live case (dropped but logged LOUD, EXEC_NULL_ORDER_LIVE), reusing the SAME
reconnect-replay stamp the duplicate-entry rule uses (P0-171). [[a-second-reader-of-the-same-state]].

THE GROUPS:

  1. THE CLASSIFICATION. Invert the branch, or force the window predicate constant, and the two cases
     swap or collapse. Both tests die: the within-window test expects the quiet replay label, the
     outside test expects the loud live label.
  2. THE PREDICATE. Flip `<=` to `>` in AccountState.IsWithinReplayWindow and an open window reads
     closed -- a replay is mislabelled live.
  3. THE ACCESSOR. Neuter RiskGuardAddOn.IsWithinReconnectReplayWindow to always-false and every
     replay is mislabelled live.

⚠️ The severity of the two branches is NOT symmetric, which is why they are labelled apart rather
than both "ignored": a live fill with no Order is a copy that silently did not happen, and folding it
into the expected-replay noise is the fail-quiet direction. [[weigh-the-quiet-failure-above-the-loud]]
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TCE = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the classification ---------------------------------------------------------
    (TCE, 'group 1: the connect-replay branch is INVERTED, so a replayed historical fill is logged '
          'as a live divergence and a (hypothetical) live fill as a replay -- both tests die',
     'if (connectReplay)',
     'if (!connectReplay)'),

    (TCE, 'group 1: the window check is forced FALSE at the call site, so every null-Order exec -- '
          'including a connect replay -- is logged LOUD as live; the within-window test dies',
     '&& guard.IsWithinReconnectReplayWindow(exec.Account.Name)',
     '&& false'),

    (TCE, 'group 1: the quiet replay label is replaced with the loud live label, so a connect replay '
          'reads as a live divergence; the within-window test dies',
     '"EXEC_REPLAY_IGNORED"',
     '"EXEC_NULL_ORDER_LIVE"'),

    (TCE, 'group 1: the loud live label is replaced with the quiet replay label, so a live null-Order '
          'fill is folded into the expected-replay noise -- the fail-quiet direction; outside test dies',
     '"EXEC_NULL_ORDER_LIVE"',
     '"EXEC_REPLAY_IGNORED"'),

    # ---- group 2: the predicate --------------------------------------------------------------
    (MODELS, 'group 2: IsWithinReplayWindow flips `<=` to `>`, so an OPEN window reads closed and a '
             'connect replay is mislabelled live; the within-window test dies',
     'IsWithinReplayWindow() => UtcNow() <= ReplaySuppressionUntilUtc',
     'IsWithinReplayWindow() => UtcNow() > ReplaySuppressionUntilUtc'),

    # ---- group 3: the accessor ---------------------------------------------------------------
    (GUARD, 'group 3: the guard accessor is neutered to always-false, so no account is ever seen as '
            'within the replay window and every replay is mislabelled live; the within-window test dies',
     'st != null && st.IsWithinReplayWindow()',
     'st != null && false'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # Encoding PINNED -- without it a non-ASCII byte raises mid-write, leaving a live mutant while
    # the battery reports restored. [[a-battery-must-reach-its-restore-line]].
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


def run():
    try:
        p = subprocess.run(
            ['dotnet', 'run', '--project', os.path.join(REPO, 'tests', 'RiskGuardTests.csproj'),
             '--nologo', '-v', 'q'],
            cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=900)
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    out = (p.stdout or '') + (p.stderr or '')
    if 'error CS' in out:
        return 'BUILD FAILED'
    m = re.search(r'Passed = (\d+), Failed = (\d+)', out)
    result = m.group(0) if m else 'NO RESULT LINE'
    if not m and '[FAIL]' not in out:
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return result


baseline = run()
print('=== baseline ===\n  %s' % baseline)
if 'Failed = 0' not in baseline:
    print('baseline is RED; a battery against a red baseline scores nothing')
    sys.exit(2)

survivors = []
for target, name, old, new in MUTANTS:
    original = ORIGINALS[target]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    try:
        res = run()
        killed = _battery.score(res, run)
        print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
        if not killed:
            survivors.append(name)
    finally:
        restore()

restore()
print(chr(10) + 'restored originals;', run())

print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
