"""Mutation battery for P2-163 + P1-168: instrument permission is ONE question, asked at BOTH points.

⚠️ THIS BATTERY IS THE PRIMARY EVIDENCE FOR THIS ENTRY, not a supplement to it. The acceptance tests
were written AFTER the implementation -- the order was inverted because the change was discovered
mid-session while closing P0-166 -- so "the tests pass" says much less than usual here. What the
tests being load-bearing rests on is each mutant below dying.

P2-163: `AllowedInstruments` lived on `PropFirmProfile` and had exactly ONE reader in the whole
solution: a unit test that constructed its own list and asserted `Contains("MNQ")` against that. So
its default -- which explicitly PERMITTED `NQ, ES, YM, CL, GC, RTY` -- was consulted by nothing, and
the live mechanism was `BlockedInstruments`, which is default-ALLOW: `SI`, `NG`, `HG`, `6E`, `ZB` and
every future product ever listed were permitted because absence meant yes.
`PropFirmProfile.BlockedInstruments` (defaulting to ZB/ZN/6E/6B) had ZERO readers, not even a test.

P1-168, MEASURED on the funded account 2026-08-19: of the 99 orders the guard saw, **17 arrived only
as `Filled`** -- never `Submitted`, never `Accepted`, never `Working` -- because a market order that
fills instantly is reported once, already terminal. Resting orders DID show their full lifecycle in
the same log, so this is the platform, not a dropped event. Every per-order rule gated on the live
states is blind to all 17, and the blocking rule was the one such rule with NO position-level
backstop. `P1-159` closed this exact shape for the contract cap and closed it for that rule only.

⚠️ WHY THE DEFAULT MATTERS AT THIS OPERATOR'S SETTINGS: with `DailyLossLimit: 250`, ONE full-size
contract at the guard's own catastrophe-stop distance is $200 -- 80% of the day in a single trade
(ES 16 ticks x $12.50, NQ 40 ticks x $5.00). The instrument restriction is what makes the daily limit
coherent, so a mutant that quietly re-permits the full-size contracts is a mutant that removes the
daily limit.

THE GROUPS BELOW:

  1. DEFAULT-DENY ACTUALLY DENIES, AND THE DEFAULT IS THE MICROS. The measured defect is restored by
     re-listing the full-size contracts, which is what the deleted field's default did.
  2. THE ALLOW-LIST IS CONSULTED AT ALL, AND THE BLOCK LIST STILL WINS. Precedence is mutated in both
     directions: each order looks right from one test and discards the other list's answer.
  3. ⚠️ AN EMPTY LIST PERMITS. This is the group that stops the fix trapping the operator. Default-deny
     driven by a list an upgrade could deserialize as empty would refuse every order on the account,
     and fail-closed applied to a legitimately empty set is how 95 of 97 accounts once got painted
     WORST. [[an-inapplicable-state-is-not-unreadable]].
  4. THE POSITION ENFORCEMENT POINT EXISTS AND IS USED. Without it the rule is blind to the 17
     measured orders and P1-168 is restored in full while every per-order test still passes.
  5. ⚠️ AN EXIT IS NEVER REFUSED, AND A REFUSAL DOES NOT COST THE SESSION. The two ways this fix could
     hurt the operator more than the defect did. [[a-lockout-must-not-trap-you]].
  6. THE ANSWER IS ONE ANSWER. Three callers share the predicate; a caller that stops using it is a
     second reader of one question. [[a-second-reader-of-the-same-state]].

EXPECTED SURVIVOR: none declared.
"""
import os, re, subprocess, sys

# Pinned before anything prints: a non-ASCII glyph in a description raises UnicodeEncodeError on a
# cp1252 console, and it raises BETWEEN applying a mutant and restoring it.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')
MODELS = os.path.join(REPO, 'addons', 'RiskGuardModels.cs')

MUTANTS = [
    # ---- group 1: default-deny denies, and the default is the micros ------------------------
    (MODELS, 'group 1: the default permitted set goes back to including the full-size contracts, '
             'which is exactly what the deleted PropFirmProfile field defaulted to. One ES stop is '
             '80% of a 250 daily limit, so this mutant removes the daily limit',
     '            new List<string> { "MNQ", "MES", "MYM", "MCL", "MGC", "M2K" };',
     '            new List<string> { "NQ", "MNQ", "ES", "MES", "YM", "MYM", "CL", "MCL", "GC", "MGC", "RTY", "M2K" };'),

    (MODELS, 'group 1: the default permitted set ships EMPTY, which by this rule\'s own escape hatch '
             'means PERMIT EVERYTHING. The field exists, is documented, is read, is enforced at two '
             'points -- and is off on every machine until somebody types into it. '
             '[[dead-safety-machinery-gate]] as a DEFAULT rather than as dead code',
     '            new List<string> { "MNQ", "MES", "MYM", "MCL", "MGC", "M2K" };',
     '            new List<string>();'),

    # ---- group 2: consulted at all, and the block list still wins ---------------------------
    (GUARD, 'group 2: the allow-list loop is skipped, so the method can only ever answer Permitted or '
            'Blocked -- default-ALLOW restored, which is the state P2-163 was filed against',
     '            foreach (var a in _config.AllowedInstruments)\n'
     '                if (string.Equals(a, root, StringComparison.OrdinalIgnoreCase))\n'
     '                    return InstrumentPermission.Permitted;\n'
     '\n'
     '            return InstrumentPermission.NotAllowed;',
     '            return InstrumentPermission.Permitted;'),

    (GUARD, 'group 2: the BLOCK list is no longer consulted, so the operator\'s day-by-day exclusion '
            'stops existing. It reads as still working because a blocked micro is on the permitted '
            'list and comes back Permitted -- the exact instrument the operator wanted excluded',
     '            if (_config.BlockedInstruments != null)\n'
     '                foreach (var b in _config.BlockedInstruments)\n'
     '                    if (string.Equals(b, root, StringComparison.OrdinalIgnoreCase))\n'
     '                        return InstrumentPermission.Blocked;',
     '            // block list not consulted'),

    (GUARD, 'group 2: the comparison becomes ordinal, so a lowercase config entry silently matches '
            'nothing. This is the PRE-EXISTING defect in the old blocking path -- List.Contains '
            'against an upper-cased root -- and it made a typed-in block simply not exist',
     '                    if (string.Equals(b, root, StringComparison.OrdinalIgnoreCase))\n'
     '                        return InstrumentPermission.Blocked;',
     '                    if (string.Equals(b, root, StringComparison.Ordinal))\n'
     '                        return InstrumentPermission.Blocked;'),

    (GUARD, 'group 2: the contract month is not stripped, so "MNQ SEP26" matches no list entry and '
            'every instrument becomes NotAllowed -- including the ones the operator trades. A roll to '
            'the next month would un-permit the instrument',
     "            string root = instrument.Split(' ')[0].ToUpper();",
     '            string root = instrument.ToUpper();'),

    # ---- group 3: an empty list PERMITS -----------------------------------------------------
    (GUARD, 'group 3: an empty permitted list starts DENYING everything. Fail-closed sounds right and '
            'is wrong here: an upgrade that deserializes the list as empty would refuse every order '
            'on a funded account, and the operator cannot tell that from a list they emptied on '
            'purpose. [[an-inapplicable-state-is-not-unreadable]]',
     '            if (_config.AllowedInstruments == null || _config.AllowedInstruments.Count == 0)\n'
     '                return InstrumentPermission.Permitted;',
     '            if (_config.AllowedInstruments == null || _config.AllowedInstruments.Count == 0)\n'
     '                return InstrumentPermission.NotAllowed;'),

    (GUARD, 'group 3: the null/empty check is dropped entirely. A null list throws inside the guard\'s '
            'own order handler, on every order event, for an account whose config simply omitted the '
            'key',
     '            if (_config.AllowedInstruments == null || _config.AllowedInstruments.Count == 0)\n'
     '                return InstrumentPermission.Permitted;\n'
     '\n',
     '\n'),

    # ---- group 4: the POSITION enforcement point -------------------------------------------
    (GUARD, 'group 4: THE MUTANT FOR P1-168. The position sweep no longer checks instrument '
            'permission, so the rule binds only through a per-order cancel that 17 of the 99 measured '
            'orders never reach. Every per-order test still passes and the rail does not bind for an '
            'instantly-filled market order, which is the ordinary case',
     '                    var posPermission = ResolveInstrumentPermission(pos.Instrument);\n'
     '                    if (posPermission != InstrumentPermission.Permitted)',
     '                    var posPermission = InstrumentPermission.Permitted;\n'
     '                    if (posPermission != InstrumentPermission.Permitted)'),

    (GUARD, 'group 4: the position check is COMPUTED and the action never QUEUED. A source scan '
            'finds the call, the enum, the comparison and a fully-populated GuardAction -- and '
            'nothing flattens. Four mutants in this project have beaten a gate meant to prove a '
            'value is USED. (The first version of this mutant appended `if (false) { }` AFTER the '
            'Add, which is a no-op: it survived because it was not a mutation at all. A survivor '
            'is evidence only once the mutant provably changes behaviour.)',
     '                        actions.Add(new GuardAction\n'
     '                        {\n'
     '                            AccountName = stateModel.AccountName,\n'
     '                            ActionType = GuardActionType.FlattenPosition,\n'
     '                            Instrument = pos.Instrument,\n'
     '                            InstrumentObj = pos.InstrumentObj,\n'
     '                            Quantity = pos.Quantity,\n'
     '                            RuleId = "INSTRUMENT_NOT_PERMITTED"\n'
     '                        });',
     '                        var discardedAction = new GuardAction\n'
     '                        {\n'
     '                            AccountName = stateModel.AccountName,\n'
     '                            ActionType = GuardActionType.FlattenPosition,\n'
     '                            Instrument = pos.Instrument,\n'
     '                            InstrumentObj = pos.InstrumentObj,\n'
     '                            Quantity = pos.Quantity,\n'
     '                            RuleId = "INSTRUMENT_NOT_PERMITTED"\n'
     '                        };\n'
     '                        if (discardedAction == null) actions.Add(discardedAction);'),

    (GUARD, 'group 4: the position rule fires on PERMITTED instruments instead -- inverted. It '
            'flattens every legitimate position and leaves the refused ones alone, and a detector that '
            'fires on everything passes every positive test written for it. '
            '[[detector-needs-a-negative-test]]',
     '                    if (posPermission != InstrumentPermission.Permitted)\n'
     '                    {\n'
     '                        actions.Add(new GuardAction\n'
     '                        {\n'
     '                            AccountName = stateModel.AccountName,\n'
     '                            ActionType = GuardActionType.FlattenPosition,\n'
     '                            Instrument = pos.Instrument,',
     '                    if (posPermission == InstrumentPermission.Permitted)\n'
     '                    {\n'
     '                        actions.Add(new GuardAction\n'
     '                        {\n'
     '                            AccountName = stateModel.AccountName,\n'
     '                            ActionType = GuardActionType.FlattenPosition,\n'
     '                            Instrument = pos.Instrument,'),

    # ---- group 5: it must not trap, and must not cost the session ---------------------------
    (GUARD, 'group 5: THE WORST MUTANT IN THIS FILE. The position-reducing exclusion is dropped from '
            'the per-order refusal, so the guard cancels the order that would CLOSE a position in an '
            'instrument it has just decided is not permitted -- trapping the operator in the exact '
            'instrument the rule wants them out of, while the position sweep tries to flatten it. '
            '[[a-lockout-must-not-trap-you]]',
     # Re-anchored 2026-08-20: P1-167 added the de-duplication clause to this condition, so it is
     # no longer a single line. The mutant still drops ONLY the reducing-order exclusion and keeps
     # the de-duplication, because dropping both would not isolate what this mutant is about.
     # [[mutation-anchors-go-stale]]
     '                            if (!IsPositionReducingOrder(e.Order, instState)\n'
     '                                && (instState == null || instState.MarkRefusedOnce("BLACKLIST_CANCEL", e.Order)))',
     '                            if (instState == null || instState.MarkRefusedOnce("BLACKLIST_CANCEL", e.Order))'),

    (GUARD, 'group 5: the account state is never fetched, so IsPositionReducingOrder is handed null, '
            'returns false for everything, and every exit reads as an entry. The same trap as above, '
            'reached by a line that looks like an unused variable rather than a policy change',
     '                    AccountState instState;\n'
     '                    _accountStates.TryGetValue(accountName, out instState);',
     '                    AccountState instState = null;'),

    (GUARD, 'group 5: a non-permitted position ALSO locks the account out for the session. A mistyped '
            'symbol would end the trading day, which is how a rail stops being tolerated -- and the '
            'operator can simply switch to a permitted instrument instead',
     '                            RuleId = "INSTRUMENT_NOT_PERMITTED"\n'
     '                        });',
     '                            RuleId = "INSTRUMENT_NOT_PERMITTED"\n'
     '                        });\n'
     '                        MarkRuleLockout(stateModel, "INSTRUMENT_NOT_PERMITTED");'),

    # ---- group 6: one question, one answer -------------------------------------------------
    # F-15: CanTrade now has a reason-channel overload. The anchor targets the
    # instrument-permission check in the NEW overload (out string reason).
    (GUARD, 'group 6: CanTrade stops using the shared predicate and goes back to its own '
            'default-ALLOW block-list read. The pre-trade gate then permits what the order path '
            'cancels and the position path flattens -- one question with two answers, which is the '
            'shape P1-159 was filed to end',
     '                    var perm = ResolveInstrumentPermission(instrument);\n'
     '                    if (perm != InstrumentPermission.Permitted)\n'
     '                    {\n'
     '                        reason = DescribeInstrumentDenial(perm);\n'
     '                        return false;\n'
     '                    }',
     '                    string canRoot = instrument.Split(\' \')[0].ToUpper();\n'
     '                    if (_config.BlockedInstruments != null && _config.BlockedInstruments.Contains(canRoot))\n'
     '                    {\n'
     '                        reason = "is blacklisted";\n'
     '                        return false;\n'
     '                    }'),

    (GUARD, 'group 6: the refusal message stops naming which list denied the order. "Blocked" and '
            '"never permitted" are two different edits for the operator to make, and the old message '
            'said only "is blacklisted" for both',
     '                                    + DescribeInstrumentDenial(instPermission) + ".");',
     '                                    + ".");'),

    (GUARD, 'group 6: the denial description answers Blocked for everything, so an instrument that was '
            'never on the permitted list tells the operator to go and edit a block list it is not on',
     '            return p == InstrumentPermission.Blocked\n'
     '                ? "it is on BlockedInstruments"\n'
     '                : "it is not on AllowedInstruments (the permitted set is default-deny)";',
     '            return "it is on BlockedInstruments";'),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    # Encoding PINNED: a cp1252 default raises part-way through on a non-ASCII byte, between
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
            killed = _battery.score(res, run)
            print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
            if not killed:
                survivors.append(name)
        finally:
            restore()
finally:
    # The pin above closes the failure that has actually happened twice; this closes the class.
    restore()

print(chr(10) + 'restored originals;', run())

# Plain exit rule, not _battery.finish: this battery declares no EXPECTED SURVIVOR, and
# tools/check_expected_survivors.py enforces the pairing in BOTH directions -- reaching for the
# helper without a declaration removes the prompt to justify the next exemption someone adds.
if survivors:
    print(chr(10) + 'SURVIVORS -- each is a test the suite does not have:')
    for s_ in survivors:
        print('  *', s_)
else:
    print(chr(10) + 'SURVIVORS: none')
sys.exit(1 if survivors else 0)
