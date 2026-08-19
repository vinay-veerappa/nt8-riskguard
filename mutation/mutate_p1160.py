"""Mutation battery for P1-160: a duplicate entry is refused, and ONLY a duplicate.

MEASURED three times in six attempts on the funded account 2026-08-18, across two platforms: gaps
of 99ms, 26ms and 150ms, each turning two 1-lot orders into a position of 2. Tradovate's own order
list shows two SEPARATE orders, so the duplication happens upstream of NT8.

⚠️ THE HARM IS NOT THE SIZE, IT IS THE SILENT HALF-COVERAGE. At 03:50:57 the stop covered 1 of 2
and the FSM reported `Protected` -- correct by its own definition, since `Protected` means
something is covering rather than everything -- so the operator had a naked half that looked
covered on the chart AND in the guard's own state. A fully naked position at least announces itself
through the StopGuard FSM.

⚠️ THE DANGEROUS DIRECTION IS THE FALSE POSITIVE, NOT THE FALSE NEGATIVE, AND THAT SHAPES THE
WHOLE BATTERY. Failing to refuse a duplicate leaves the operator where they were this morning.
Refusing something that is NOT a duplicate can cancel a protective leg off a live position, which
is the failure the guard exists to prevent arriving by the guard's own hand. So the groups below
are weighted towards the exclusions, and groups 2 and 2b are the ones that matter most.

⚠️ EVERY ANCHOR IN THIS FILE MOVED ONCE ALREADY. The rule was first written INSIDE the rate
governor's `Submitted || Accepted` branch and was later lifted out into its own gate, which
re-indented every line of it by four spaces. Nineteen anchors stopped matching in one edit, and a
battery whose anchor does not match prints `[SKIP]` and scores a SURVIVOR rather than failing.
`mutation/check_anchors.py` is what catches that; run it after any move.
[[mutation-anchors-go-stale]].

THE GROUPS BELOW:

  1. THE RULE FIRES AT ALL, AND ONLY ONCE PER ORDER. The measured defect, restored; plus the
     multi-state double-count that `P2-46` already inflicted on the neighbouring rate governor.
  2. ⚠️ THE EXCLUSIONS. `OrderType.Market` is the clause that makes it structurally impossible to
     cancel a bracket leg; the position-reducing check and the copier-name check are the other two.
     Every mutant here is a live position losing cover, or two subsystems correcting each other.
  2b. ⚠️ THE FILL-ONLY PATH, AND IT IS THE ONE THE TICKET GOT WRONG. Two of the three measured
     duplicates produced exactly ONE event each, in state `Filled`, because they were placed on the
     broker platform rather than through NT8 -- which is how the operator normally trades.
  3. THE KEY. Instrument AND side, both halves. Dropping either turns unrelated trades into
     duplicates of each other.
  4. THE WINDOW IS CONSULTED, AND 0 MEANS OFF. `P1-84` is the precedent: a rule that read its own
     disable value as a threshold left live arming gated on nothing at all for weeks.
  5. IT REFUSES, IT DOES NOT PUNISH. A lockout for a broker glitch is how this gets switched off,
     and the lockout test is an OR so either half alone is a lockout (`P1-45`).
  6. THE REFUSAL IS DIAGNOSABLE. The operator's own words were "not sure why that is happening" --
     a log line that does not name both orders and the gap leaves them exactly there.
"""
import os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _battery

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')
COPIER = os.path.join(REPO, 'addons', 'TradeCopierEngine.cs')

MUTANTS = [
    # ---- group 1: the rule fires at all, and once per order ---------------------------------
    (GUARD, 'group 1: the whole rule goes dead -- the measured defect restored, two 1-lot orders '
            '99ms apart building a position of 2 with nothing objecting',
     '                        if (dupWindowMs > 0 && dupObservable)',
     '                        if (false)'),

    (GUARD, 'group 1: the duplicate is detected and the cancel is never queued, so the guard '
            'announces the problem and does nothing about it. A COMPUTED gate is not a USED gate, '
            'and four source checks in this project have been beaten by exactly that',
     '                                            _pendingCancels.Add(new PendingCancelEntry(account, e.Order, PendingCancelIntent.Intervention));\n'
     '                                            LogEvent(accountName, "DUPLICATE_ENTRY",',
     '                                            LogEvent(accountName, "DUPLICATE_ENTRY",'),

    (GUARD, 'group 1: the same Order object on a LATER state transition is treated as a new order, '
            'so every entry ever placed is its own duplicate and gets cancelled. One NT8-native '
            'order now presents four times -- Submitted, Accepted, Working, Filled -- and the ATM '
            'entry measured on 2026-08-18 logged `Initialized` twice on top of that. This is P2-46 '
            'in the neighbouring rate governor, one rule over',
     '                                        if (!ReferenceEquals(anchor.Order, e.Order) && gapMs < dupWindowMs)',
     '                                        if (gapMs < dupWindowMs)'),

    # ---- group 2: the exclusions ------------------------------------------------------------
    (GUARD, 'group 2: the OrderType.Market restriction is dropped. THE WORST MUTANT IN THIS FILE: '
            'a bracket stop and target are both sells arriving 3-11ms apart, and while the position '
            'still reads Flat neither is position-reducing -- so the guard cancels the TARGET as a '
            'duplicate of the STOP and strips a live position of the cover the operator did place',
     '                            bool isEntry = e.Order.OrderType == OrderType.Market',
     '                            bool isEntry = true'),

    (GUARD, 'group 2: the position-reducing exclusion is dropped, so two market orders CLOSING a '
            'position count as duplicates of each other and the second exit is cancelled -- the '
            'guard refusing to let the operator get flat, which is not a risk control',
     '                                && !IsPositionReducingOrder(e.Order, stateModel)',
     '                                && true'),

    (GUARD, 'group 2: the copier exclusion is dropped. When the LEADER suffers a duplicate the '
            'copier mirrors both legs faithfully; cancelling the second puts the follower out of '
            'conformance, the reconciler corrects it, and the guard refuses it again -- two '
            'subsystems correcting each other, which is worse than the duplicate',
     '                                && !string.Equals(e.Order.Name, CopierOrderNames.Follow, StringComparison.Ordinal);',
     '                                && true;'),

    (COPIER, 'group 2: the copier stops tagging its follow orders with the shared constant, so the '
             'exclusion above still LOOKS right and matches nothing. The constant exists precisely '
             'so a rename cannot disarm the exclusion in silence',
     '                        CopierOrderNames.Follow,',
     '                        "FOLLOW",'),

    # ---- group 2b: the fill-only path (measured) --------------------------------------------
    (GUARD, 'group 2b: Filled is dropped from the gate, so the rule sees only orders NT8 itself '
            'submitted. TWO OF THE THREE MEASURED DUPLICATES produced exactly one event each, in '
            'state Filled, because they were placed on the broker platform -- which is how the '
            'operator normally trades. Correct, tested, and blind to the majority of its cases',
     '                            || e.Order.OrderState == OrderState.Filled;',
     '                            ;'),

    (GUARD, 'group 2b: the state gate is removed entirely, so the rule also runs on Cancelled and '
            'Rejected -- a REJECTED duplicate would still be anchored, and that anchor would then '
            'shadow the genuine entry that follows it',
     '                        if (dupWindowMs > 0 && dupObservable)',
     '                        if (dupWindowMs > 0 || dupObservable)'),

    (GUARD, 'group 2b: the explicit gap check is dropped, leaving the window enforced only as a '
            'side effect of the pruning pass. Two events inside one DateTime tick share a '
            'timestamp, the anchor is not older than the cutoff, so it survives -- and a window '
            'the operator set to 0 can still cancel an order. Killed only by the frozen-clock '
            'boundary test, because wall-clock timing cannot reach the boundary on purpose',
     '                                        if (!ReferenceEquals(anchor.Order, e.Order) && gapMs < dupWindowMs)',
     '                                        if (!ReferenceEquals(anchor.Order, e.Order))'),

    (GUARD, 'group 2b: the gap comparison is loosened to <=, so a gap of exactly the window counts '
            'as a duplicate. The off-by-one at the boundary, in the direction that REFUSES a '
            'legitimate order rather than missing a duplicate',
     '                                        if (!ReferenceEquals(anchor.Order, e.Order) && gapMs < dupWindowMs)',
     '                                        if (!ReferenceEquals(anchor.Order, e.Order) && gapMs <= dupWindowMs)'),

    # ---- group 3: the key -------------------------------------------------------------------
    (GUARD, 'group 3: the instrument is dropped from the key, so an MES entry is a duplicate of an '
            'MNQ entry placed moments earlier -- two unrelated trades, one of them cancelled',
     '                                    string dupKey = dupInstRoot + "|" + side;',
     '                                    string dupKey = side;'),

    (GUARD, 'group 3: the SIDE is dropped from the key, so a reversal -- sell to close, buy to open '
            '-- reads as a duplicate and the new entry is cancelled. The operator flips and the '
            'guard silently refuses the second half',
     '                                    string dupKey = dupInstRoot + "|" + side;',
     '                                    string dupKey = dupInstRoot;'),

    (GUARD, 'group 3: Buy and BuyToCover are separated, so a duplicate arriving with the other '
            'long-side label slips through. The two are one direction and the platform picks which '
            'label it sends -- the same lesson as reading OrderAction as a fact about the position',
     '                                string side = (e.Order.OrderAction == OrderAction.Buy || e.Order.OrderAction == OrderAction.BuyToCover)',
     '                                string side = (e.Order.OrderAction == OrderAction.Buy)'),

    # ---- group 4: the window, and the anchor's own lifecycle --------------------------------
    (GUARD, 'group 4: the anchor is never REFRESHED on a non-duplicate entry, so it keeps the '
            'timestamp of the first trade of the day and every later gap is measured from there. '
            'The rule then protects trade one and nothing after it -- and this is what a surviving '
            'mutant against the old pruning pass was hiding, because every test opened one trade',
     '                                            anchor.Order = e.Order;\n'
     '                                            anchor.FirstSeenUtc = dupNow;',
     '                                            // anchor not refreshed'),

    (GUARD, 'group 4: a REJECTED or CANCELLED anchor is kept, so the operator\'s immediate retry is '
            'cancelled as a duplicate of an order that does not exist. They end with no position '
            'and two refusals, from a rule meant to stop them holding TWICE what they intended -- '
            'the worst false positive available on this path',
     '                        if (dupWindowMs > 0\n'
     '                            && (e.Order.OrderState == OrderState.Rejected\n'
     '                                || e.Order.OrderState == OrderState.Cancelled))',
     '                        if (false)'),

    (GUARD, 'group 4: only a Rejection drops the anchor, not a Cancellation, so pulling an order '
            'by hand and re-entering is refused. Half a fix reads exactly like a whole one',
     '                            && (e.Order.OrderState == OrderState.Rejected\n'
     '                                || e.Order.OrderState == OrderState.Cancelled))',
     '                            && (e.Order.OrderState == OrderState.Rejected))'),

    (GUARD, 'EXPECTED SURVIVOR: the enable is relaxed from `> 0` to `>= 0`, so a window of 0 no '
            'longer short-circuits. EQUIVALENT MUTANT, and deliberately so: `gapMs < dupWindowMs` '
            'at the decision point means a window of 0 can never match however the rule is '
            'entered, which is exactly the defence-in-depth that check was added for. It is kept '
            'as a mutant because the DEFECT it models is real in the P1-84 sense -- a rule reading '
            'its own disable value as a threshold -- and if the gap check is ever removed this '
            'mutant stops being equivalent and starts being a live order cancelled by a rule the '
            'operator switched off. Its partner mutant, deleting the gap check, IS killed.',
     '                        if (dupWindowMs > 0 && dupObservable)',
     '                        if (dupWindowMs >= 0 && dupObservable)'),

    (MODELS, 'group 4: the default window ships at 0, so the rule is present, correct, tested, and '
             'off on every machine until somebody discovers it in a config file. '
             '[[dead-safety-machinery-gate]] as a DEFAULT rather than as dead code',
     '        public int DuplicateEntryWindowMs { get; set; } = 1000;',
     '        public int DuplicateEntryWindowMs { get; set; } = 0;'),

    # ---- group 5: it refuses, it does not punish --------------------------------------------
    (GUARD, 'group 5: the duplicate also locks the account out. The operator did not do this -- '
            'their platform did -- and losing the session to a broker glitch is exactly how a rail '
            'stops being tolerated. Note the lockout test is an OR, so the flag alone is enough',
     '                                            LogEvent(accountName, "DUPLICATE_ENTRY",',
     '                                            MarkRuleLockout(stateModel, "DUPLICATE_ENTRY");\n'
     '                                            LogEvent(accountName, "DUPLICATE_ENTRY",'),

    (GUARD, 'group 5: the FIRST order is cancelled instead of the duplicate. The same number of '
            'working orders and the opposite outcome -- and on the measured 03:50:57 case the '
            'first order is the one the stop was sized against',
     '                                            _pendingCancels.Add(new PendingCancelEntry(account, e.Order, PendingCancelIntent.Intervention));',
     '                                            _pendingCancels.Add(new PendingCancelEntry(account, anchor.Order, PendingCancelIntent.Intervention));'),

    (GUARD, 'group 5: the cancel is marked Cleanup rather than Intervention, so it is sent in '
            'SHADOW too -- a mode whose whole contract is that it observes and does not act on the '
            'trader\'s orders. Shadow would start cancelling live orders with no announcement',
     '                                            _pendingCancels.Add(new PendingCancelEntry(account, e.Order, PendingCancelIntent.Intervention));',
     '                                            _pendingCancels.Add(new PendingCancelEntry(account, e.Order, PendingCancelIntent.Cleanup));'),

    # ---- group 6: the refusal is diagnosable ------------------------------------------------
    (GUARD, 'group 6: the refusal no longer names the FIRST order, so the pair cannot be found in '
            'the log and the operator is left exactly where they started -- "not sure why that is '
            'happening", which is the sentence this entry exists to answer',
     '                                                + $"{e.Order.OrderAction} duplicated anchor order {anchor.Order.Id} "',
     '                                                + $"{e.Order.OrderAction} duplicated an earlier order "'),

    (GUARD, 'group 6: the gap is dropped from the message, so a 99ms platform duplicate and a '
            'deliberate re-entry near the window edge read identically -- and the gap is the only '
            'number that says which one it was',
     '                                                + $"({gapMs:F0}ms within {dupWindowMs}ms window).");',
     '                                                + $"(within the duplicate window).");'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # ⚠️ Encoding PINNED: a cp1252 default raises part-way through on a non-ASCII byte, between
    # applying a mutant and restoring it. [[a-battery-must-reach-its-restore-line]].
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
    # P2-148 / P1-153: a crash is not a detection.
    if not m and '[FAIL]' not in out:
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return result


baseline = run()
print('=== baseline ===\n  %s' % baseline)
if 'Failed = 0' not in baseline:
    print('baseline is RED; a battery against a red baseline scores nothing')
    sys.exit(2)

survivors = []
try:
    for target, name, old, new in MUTANTS:
        original = ORIGINALS[target]
        if original.count(old) != 1:
            print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
            survivors.append(name + ' (ANCHOR)')
            continue
        open(target, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
        try:
            res = run()
            mm = re.search(r'Failed = (\d+)', res)
            undetected_crash = 'NO ASSERTION FAILED' in res
            killed = (not undetected_crash) and (
                ('BUILD FAILED' in res) or ('NO RESULT LINE' in res)
                or (mm is not None and int(mm.group(1)) > 0))
            print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
            if not killed:
                survivors.append(name)
        finally:
            restore()
finally:
    # The pin above closes the failure that has actually happened twice; this closes the class.
    restore()

print(chr(10) + 'restored originals;', run())

# Routed through _battery.finish because group 4 declares one EXPECTED SURVIVOR, and the helper
# enforces the pairing in BOTH directions -- a declaration that starts being KILLED is reported
# STALE rather than passing quietly, which is what would happen the day someone removes the gap
# check and makes that mutant non-equivalent again.
_battery.finish(survivors, MUTANTS)
