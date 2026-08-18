"""Mutation battery for P2-136's "survive it" half: the ATM bracket registry across a recompile.

A SUCCESSFUL NinjaScript compile hot-swaps `bin/Custom` into a NEW ASSEMBLY. `DynamicAtmManager`'s
registry lives behind `private static readonly Lazy<DynamicAtmManager> _instance` -- which reads as
"survives anything" and does not survive this. The new assembly gets a fresh `Lazy`, so
`_activeBrackets` starts EMPTY while the position and both broker-side legs are untouched.

MEASURED, on a box with 377 minutes of uptime and NO restart:

    18 x CONNECTION_CHANGE -> INITIALIZE -> ARMED_ON_START in 2.5 hours   every one a recompile
    bracket 1a48f3cf registered 23:16 against an open 1-lot MNQ position
                     absent from the registry by 23:17:3x, position still long 1
                     nothing logged

⚠️ AND SOMEBODY ELSE'S DEPLOY DOES IT TO YOU: the 23:17:56 compile came from another process
deploying unrelated `range_probability` NinjaScript in a different repo.

⚠️ WHY THIS IS WORSE THAN LOSING THE STOP. The stop and target still REST AT THE BROKER, so every
surface an operator checks reports the trade as protected -- and it is, at its opening price, with a
stop that will never move again. [[a-successful-compile-wipes-static-state]].

THE GROUPS BELOW:

  1. ⚠️ THE IDENTITY CHECK, WHICH IS THE ENTIRE SAFETY ARGUMENT AND IS NOT "IS THERE A POSITION".
     A record says "account SimAtm, symbol MNQ". A two-day-old file plus an unrelated MANUAL MNQ
     trade on that account satisfies that description exactly, and restoring on it would attach this
     monitor to a position it did not create and start moving the OPERATOR'S OWN STOP on a funded
     account. The leg named `Stop_<bracketId>` is what makes the record ours: bracket-unique, chosen
     by this addon, and per P1-133 the one identity the broker does not replace.
  2. THE PRICE. `P0-67` one layer up: a price written before a compile is this monitor's last WISH,
     not the broker's truth, and `Account.Change()` is a request the Simulator has been measured
     accepting and silently discarding. Trust the file and the trail LATCHES.
  3. DIRECTION. Every breakeven and trail price downstream is signed by `IsLong`.
  4. ⚠️ "NOT RESTORABLE NOW" vs "NEVER RESTORABLE", which is where this entry's own first diagnosis
     went wrong. An `ARMED_ON_START` burst IS a connection cycle and this code runs during one, so an
     account that has not appeared yet must DEFER; a flat position is answered and DROPS. Both
     failure directions are live: dropping too eagerly discards a live bracket, keeping too long
     re-announces the same line forever, and an unbounded defer is a record that never leaves.
  5. ⚠️ CONSUMED ONCE -- and read `P1-143` before trusting this line's older form. It used to say
     the once-only guard is "what makes resetting the retry budget safe". It never was: the guard is
     a per-INSTANCE dictionary and ONE nt_compile produces 3-4 fresh instances, measured 15s apart.
     The reset is GONE (group 8); the budget is carried in the file and cleared only where a move is
     OBSERVED to have taken. What group 5 still covers is the other half -- not clobbering a bracket
     the live sweep has already advanced.
  6. ⚠️ THE WIRING, AND IT IS THE GROUP MOST LIKELY TO SHIP DEAD. Nothing in this assembly
     referenced `DynamicAtmManager` at all before this ticket -- it is reached solely through the
     bridge's `/api/order/atm` -- and `EnsureMonitor` is called from `PlaceBracket` ONLY. So the
     restore could have shipped tested, mutation-covered, deployed and never once run, and a bracket
     could be restored into a registry with no timer moving its stop: restored and still unmanaged.
     [[dead-safety-machinery-gate]], [[report-the-outcome-not-the-call]].
  7. LOUD vs SILENT, in BOTH directions. A missing file is a box that never placed a managed bracket
     -- the ordinary state -- and a line there is a line on every startup. A file that exists and
     cannot be parsed means something WAS being managed and is not any more.
     [[an-inapplicable-state-is-not-unreadable]], [[detector-needs-a-negative-test]].

  8. ⚠️ P1-143 -- THE BUDGET IS CARRIED ACROSS THE RESTORE, and every mutant in that group is a line
     that shipped, green and deployed, for a day. Its negative control is the load-bearing one: a
     CONFIRMED move must still clear the carried budget, or "do not reset it" quietly becomes "a
     recovered bracket stays abandoned forever".

⚠️ A CRASH IS NOT AUTOMATICALLY A KILL, and it used to be -- see `P2-148`. The harness prints its
result line LAST, so any unhandled exception leaves 'NO RESULT LINE', which the scoring counted as a
kill unconditionally. That is right when assertions failed on the way down and WRONG when the mutant
merely broke the harness. A crash now counts only if the run printed at least one `[FAIL]` first.
The first thing that rule found was a false kill in this very file: the group 1 mutant had been
scored KILLED for three sessions while nothing detected it.

Exits non-zero on any survivor, and exits 2 rather than running against a red baseline.
"""
import os
import re
import subprocess
import sys

# ⚠️ REQUIRED, and the gate is tools/check_batteries_pin_encoding.py. Without it one non-ASCII
# character in a mutant description raises UnicodeEncodeError inside print() on a cp1252 console --
# AFTER a mutant is applied and BEFORE it is restored, leaving a LIVE MUTANT in the source tree.
# That has happened twice here, once leaving the P2-135 defect itself sitting in
# DynamicAtmManager.cs. [[a-battery-must-reach-its-restore-line]].
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ATM = os.path.join(REPO, 'addons', 'DynamicAtmManager.cs')
PERSIST = os.path.join(REPO, 'addons', 'AtmBracketPersistence.cs')
GUARD = os.path.join(REPO, 'addons', 'RiskGuardAddOn.cs')

MUTANTS = [
    # ---- group 1: the identity check ------------------------------------------------------------
    # ⚠️ REWRITTEN TWICE ON 2026-08-18 (P2-148), AND BOTH REWRITES ARE THE LESSON.
    #
    # v1 mutated only the `if` to `if (false)`. That CANNOT express the defect it describes: control
    # reaches `liveStop.StopPrice` with liveStop null and throws, so nothing is ever adopted. It
    # scored KILLED on 'NO RESULT LINE' -- the harness dying, not a test objecting.
    #
    # v2 also neutralised the price assignment. Still threw, because there is a THIRD dereference --
    # `liveStop.StopPrice.ToString()` inside the Restored Reason. A null check is not one line just
    # because the `if` is; counting the dereferences is the work.
    #
    # ⚠️ AND v2 THREW IN A DIFFERENT TEST ENTIRELY --
    # TestAtm_P1130_AStopMoveThatFindsNoOrderIsCountedAndBounded, registered EARLIER in Main than any
    # P2-136 test. `ReconcilePersistedBrackets` runs at the top of every `MonitorTickCore`, so every
    # ATM sweep in the suite drives the restore path: a defect there kills tests that have nothing to
    # do with it, before the tests that would diagnose it ever run.
    #
    # A faithful mutant lets the adoption HAPPEN: no live order found, adopt anyway, keep the FILE's
    # price. Exactly what this class's header warns against.
    # [[check-the-exemplar-belongs-to-the-class]].
    #
    # ⚠️ All three edits are ONE mutant deliberately. Split, each survives alone and proves
    # nothing: the `if` alone throws, and each price fallback alone is EQUIVALENT, because the guard
    # above returns before liveStop can be null at either site.
    (PERSIST,
     "⚠️ THE IDENTITY CHECK GOES AWAY: any open position in the right symbol is adopted, keeping\n"
     "     the FILE's price because no named order was found. A file two days old plus an unrelated\n"
     "     MANUAL trade on that account is picked up, and this monitor starts moving a stop the\n"
     "     operator placed, on a funded account",
     '            if (liveStop == null)\n'
     '            {\n'
     '                return new AtmRestoreDecision\n'
     '                {\n'
     '                    Bracket = b,\n'
     '                    Verdict = AtmRestoreVerdict.Unprotected,\n'
     '                    Reason = b.BracketId + ": the " + b.Symbol + " position on \'" + account.Name\n'
     '                        + "\' is still OPEN and no live order named \'" + AtmOrderIdentity.StopName(b.BracketId)\n'
     '                        + "\' remains at the broker, so this position has no protective stop and is not "\n'
     '                        + "being managed. It is NOT picked back up, because a bracket with no stop to "\n'
     '                        + "move would report as managed while managing nothing."\n'
     '                };\n'
     '            }\n'
     '\n'
     '            // The price comes from the ORDER, never from the file. See the header: a price written\n'
     '            // before a compile is this monitor\'s last wish. P0-67 one layer down.\n'
     '            b.CurrentStopPrice = liveStop.StopPrice;\n'
     '\n'
     '            // Nothing is outstanding across a hot-swap: whatever was in flight either took or did\n'
     '            // not, and the next sweep\'s ReconcileStopFromBroker is what finds out.\n'
     '            b.RequestedStopPrice = double.NaN;\n'
     '            b.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;\n'
     '\n'
     '            // ⚠️ THE RETRY BUDGET IS CARRIED, NOT RESET, AND THIS IS `P1-143`. It used to be reset\n'
     '            // here, on the reasoning that "a new assembly against a possibly-new connection is a new\n'
     '            // episode, so a bracket that had given up deserves to try again", guarded by the claim\n'
     '            // that a record is consumed ONCE because `RestoreInto` refuses an id already in the\n'
     '            // registry.\n'
     '            //\n'
     '            // That guard is PER-INSTANCE and the condition is not. Measured on the box the day after\n'
     '            // it shipped: one `nt_compile` produced FOUR `InitializeRiskGuard` runs 15s apart, each\n'
     '            // on a fresh static context with an empty registry, so one bracket was restored four\n'
     '            // times and a refused stop was handed four fresh budgets of `MaxStopModifyAttempts`. The\n'
     '            // order flood the old comment warned about, arriving through the door it did not\n'
     '            // consider: not a re-read within an instance, but a NEW INSTANCE.\n'
     '            //\n'
     '            // "A new assembly is a new episode" is true of a RESTART and false of a COMPILE, which is\n'
     '            // the same distinction `P2-142` records from the other side. So nothing is cleared here.\n'
     '            // `StopModifyAttempts`, `StopMoveAbandonAnnounced` and `LastStopMoveFailureReason` are\n'
     '            // plain serialised properties of `ActiveBracket`, so they survive in the file and simply\n'
     '            // stand. The event that SHOULD clear them already does: `ReconcileStopFromBroker`\'s\n'
     '            // CONFIRMED branch clears both when a move is observed to have actually taken, which is\n'
     '            // a recovery that happened rather than one that is merely possible.\n'
     '\n'
     '            return new AtmRestoreDecision\n'
     '            {\n'
     '                Bracket = b,\n'
     '                Verdict = AtmRestoreVerdict.Restored,\n'
     '                Reason = b.BracketId + ": picked back up after a NinjaScript recompile. The "\n'
     '                    + b.Symbol + " position on \'" + account.Name + "\' is still open and its stop \'"\n'
     '                    + AtmOrderIdentity.StopName(b.BracketId) + "\' is live at "\n'
     '                    + liveStop.StopPrice.ToString("0.#####")',
     '            if (false)\n'
     '            {\n'
     '                return new AtmRestoreDecision\n'
     '                {\n'
     '                    Bracket = b,\n'
     '                    Verdict = AtmRestoreVerdict.Unprotected,\n'
     '                    Reason = b.BracketId + ": the " + b.Symbol + " position on \'" + account.Name\n'
     '                        + "\' is still OPEN and no live order named \'" + AtmOrderIdentity.StopName(b.BracketId)\n'
     '                        + "\' remains at the broker, so this position has no protective stop and is not "\n'
     '                        + "being managed. It is NOT picked back up, because a bracket with no stop to "\n'
     '                        + "move would report as managed while managing nothing."\n'
     '                };\n'
     '            }\n'
     '\n'
     '            // The price comes from the ORDER, never from the file. See the header: a price written\n'
     '            // before a compile is this monitor\'s last wish. P0-67 one layer down.\n'
     '            b.CurrentStopPrice = liveStop == null ? b.CurrentStopPrice : liveStop.StopPrice;\n'
     '\n'
     '            // Nothing is outstanding across a hot-swap: whatever was in flight either took or did\n'
     '            // not, and the next sweep\'s ReconcileStopFromBroker is what finds out.\n'
     '            b.RequestedStopPrice = double.NaN;\n'
     '            b.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;\n'
     '\n'
     '            // ⚠️ THE RETRY BUDGET IS CARRIED, NOT RESET, AND THIS IS `P1-143`. It used to be reset\n'
     '            // here, on the reasoning that "a new assembly against a possibly-new connection is a new\n'
     '            // episode, so a bracket that had given up deserves to try again", guarded by the claim\n'
     '            // that a record is consumed ONCE because `RestoreInto` refuses an id already in the\n'
     '            // registry.\n'
     '            //\n'
     '            // That guard is PER-INSTANCE and the condition is not. Measured on the box the day after\n'
     '            // it shipped: one `nt_compile` produced FOUR `InitializeRiskGuard` runs 15s apart, each\n'
     '            // on a fresh static context with an empty registry, so one bracket was restored four\n'
     '            // times and a refused stop was handed four fresh budgets of `MaxStopModifyAttempts`. The\n'
     '            // order flood the old comment warned about, arriving through the door it did not\n'
     '            // consider: not a re-read within an instance, but a NEW INSTANCE.\n'
     '            //\n'
     '            // "A new assembly is a new episode" is true of a RESTART and false of a COMPILE, which is\n'
     '            // the same distinction `P2-142` records from the other side. So nothing is cleared here.\n'
     '            // `StopModifyAttempts`, `StopMoveAbandonAnnounced` and `LastStopMoveFailureReason` are\n'
     '            // plain serialised properties of `ActiveBracket`, so they survive in the file and simply\n'
     '            // stand. The event that SHOULD clear them already does: `ReconcileStopFromBroker`\'s\n'
     '            // CONFIRMED branch clears both when a move is observed to have actually taken, which is\n'
     '            // a recovery that happened rather than one that is merely possible.\n'
     '\n'
     '            return new AtmRestoreDecision\n'
     '            {\n'
     '                Bracket = b,\n'
     '                Verdict = AtmRestoreVerdict.Restored,\n'
     '                Reason = b.BracketId + ": picked back up after a NinjaScript recompile. The "\n'
     '                    + b.Symbol + " position on \'" + account.Name + "\' is still open and its stop \'"\n'
     '                    + AtmOrderIdentity.StopName(b.BracketId) + "\' is live at "\n'
     '                    + b.CurrentStopPrice.ToString("0.#####")'),

    (PERSIST,
     "the identity lookup stops caring whether our leg is LIVE, so a FILLED or CANCELLED stop\n"
     "     still counts as protection. That is P1-130/P1-131's shape -- the state list disagreeing\n"
     "     with its neighbour -- and it restores a bracket over a position with nothing beneath it",
     '            Order liveStop = AtmOrderIdentity.FindLiveByName(account, AtmOrderIdentity.StopName(b.BracketId));',
     '            Order liveStop = AtmOrderIdentity.FindByName(account, AtmOrderIdentity.StopName(b.BracketId));'),

    (PERSIST,
     "the leg is looked up by the record's own SYMBOL rather than by the bracket-unique name, so\n"
     "     any of our stops on that account matches any of our records. Two ATM brackets on one\n"
     "     account and each restores against the other's stop",
     '            Order liveStop = AtmOrderIdentity.FindLiveByName(account, AtmOrderIdentity.StopName(b.BracketId));',
     '            Order liveStop = null;\n'
     '            foreach (Order candidate in account.Orders)\n'
     '            {\n'
     '                if (candidate != null && candidate.Name != null\n'
     '                    && candidate.Name.StartsWith("Stop_", StringComparison.Ordinal))\n'
     '                { liveStop = candidate; break; }\n'
     '            }'),

    # ---- group 2: the price -------------------------------------------------------------------
    (PERSIST,
     "⚠️ P0-67 UNDONE ONE LAYER UP: the restored stop price comes from the FILE instead of the\n"
     "     live order. The file holds this monitor's last WISH, and Account.Change() is a request\n"
     "     the Simulator accepts and discards -- so the trail latches on a price the broker never\n"
     "     had, exactly as it did before P0-67",
     '            b.CurrentStopPrice = liveStop.StopPrice;',
     '            b.CurrentStopPrice = b.CurrentStopPrice;'),

    (PERSIST,
     "an in-flight stop move survives the hot-swap, so the reconciler judges this sweep's broker\n"
     "     price against the LAST assembly's outstanding request -- and RequestStopMove returns\n"
     "     early while one is in flight, so no move is ever attempted again",
     '            b.RequestedStopPrice = double.NaN;\n'
     '            b.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;',
     '            b.OutstandingStopMoveKind = b.OutstandingStopMoveKind;'),

    # ---- group 3: direction --------------------------------------------------------------------
    (PERSIST,
     "⚠️ THE DIRECTION CHECK GOES AWAY: a LONG record is restored over a SHORT position, and\n"
     "     every breakeven and trail price for it is then computed with the wrong sign against a\n"
     "     real position. P1-139's guard would refuse the resulting move -- a backstop catching a\n"
     "     decision that should not have been made",
     '            if (positionIsLong != b.IsLong)',
     '            if (false)'),

    (PERSIST,
     "the position's side is read from the SIGN of Quantity instead of MarketPosition.\n"
     "     Position.Quantity is ABSOLUTE on NT8 and never negative, so every short now reads as\n"
     "     long and the mismatch check passes on the one case it exists for",
     '            bool positionIsLong = position.MarketPosition == MarketPosition.Long;',
     '            bool positionIsLong = position.Quantity >= 0;'),

    (PERSIST,
     "a flat position is detected by the SIGN rather than the magnitude, so a short position\n"
     "     reads as finished and its bracket is dropped while the position is open",
     '            if (position == null || Math.Abs(position.Quantity) == 0)',
     '            if (position == null || position.Quantity < 0)'),

    # ---- group 4: defer vs drop ----------------------------------------------------------------
    (PERSIST,
     "⚠️ AN UNREADABLE ACCOUNT IS DROPPED INSTEAD OF DEFERRED. An ARMED_ON_START burst IS a\n"
     "     connection cycle -- 18 measured in 2.5 hours -- and this code runs during one, so a\n"
     "     live bracket is discarded for a reason that resolves a second later",
     '            get { return Verdict == AtmRestoreVerdict.Deferred; }',
     '            get { return false; }'),

    (PERSIST,
     "NOTHING ever leaves the disk, so every answered record -- finished, unprotected,\n"
     "     mismatched -- is re-decided and re-announced on every sweep for the life of the\n"
     "     process. An alarm that is always on is off",
     '            get { return Verdict == AtmRestoreVerdict.Deferred; }',
     '            get { return true; }'),

    (PERSIST,
     "the deferral becomes UNBOUNDED: a record whose account never appears is retried forever\n"
     "     and the give-up is never announced. A bounded retry with no policy is what let an\n"
     "     alert relay stay dead for seven hours",
     '            if (record.RestoreDeferrals >= MaxRestoreDeferrals)',
     '            if (false)'),

    (PERSIST,
     "the deferral budget never SPENDS, so the bound exists and can never be reached -- a retry\n"
     "     whose exit condition nothing advances never exits",
     '                record.RestoreDeferrals = record.RestoreDeferrals + 1;',
     '                record.RestoreDeferrals = record.RestoreDeferrals;'),

    (PERSIST,
     "the budget is spent on the FIRST attempt only, so what reads as three retries is one.\n"
     "     Every single-attempt assertion still passes",
     '        public const int MaxRestoreDeferrals = 3;',
     '        public const int MaxRestoreDeferrals = 1;'),

    # ---- group 5: consumed once ----------------------------------------------------------------
    (ATM,
     "⚠️ THE CONSUMED-ONCE INVARIANT GOES AWAY: the persisted copy OVERWRITES a bracket the\n"
     "     sweep is already advancing. That laundered StopModifyAttempts back to zero on every\n"
     "     read, turning MaxStopModifyAttempts = 3 into an unbounded order flood, and it replaces\n"
     "     the live object so the sweep's stop moves and the registry diverge",
     '                        alreadyLive = _activeBrackets.ContainsKey(decision.Bracket.BracketId);\n'
     '                        if (!alreadyLive)\n'
     '                            _activeBrackets[decision.Bracket.BracketId] = decision.Bracket;',
     '                        alreadyLive = false;\n'
     '                        _activeBrackets[decision.Bracket.BracketId] = decision.Bracket;'),

    # ---- group 6: the wiring -------------------------------------------------------------------
    # ⚠️ THIS PAIR IS WHY THE CODE MOVED, AND THE HISTORY IS THE POINT. The first version of this
    # group had ONE mutant: `if (false)` in front of the restore's only startup call, in
    # InitializeRiskGuard. It SURVIVED a 2176/0 suite, a green check_anchors, and
    # check_no_dead_safety_machinery -- which still read WIRED, because the ATM manager's own sweep
    # also calls the method and that gate asks "is this called by anything", not "is it called by a
    # driver that runs". Nothing could kill it: NT8's startup path is not driveable from the test
    # build, and a C# source assertion finds the call text sitting inside the dead branch.
    #
    # So the GUARANTEED driver moved to `ExecuteSafetySweep` -- internal, already driven by the
    # suite, and on a timer started unconditionally at init rather than one that starts only when a
    # bracket is PLACED. The init call is now for immediacy only, which is why there is no mutant
    # against it alone: with the sweep in place, killing it does not kill the restore, so its
    # survival would be correct rather than a gap. [[a-backstop-at-a-choke-point-is-unkillable]].
    (GUARD,
     "⚠️ THE GUARANTEED DRIVER GOES AWAY: the guard's five-second sweep stops restoring, leaving\n"
     "     only the init-time attempt -- which runs during a connection cycle, and after a\n"
     "     recompile with no new order there is no ATM timer to retry on either",
     '            try { DynamicAtmManager.Instance.ReconcilePersistedBrackets(); }\n'
     '            catch (Exception ex)\n'
     '            {\n'
     '                LogEvent("SYSTEM", "ERROR", "ATM bracket restore failed during the safety sweep: " + ex.Message);',
     '            try { if (false) DynamicAtmManager.Instance.ReconcilePersistedBrackets(); }\n'
     '            catch (Exception ex)\n'
     '            {\n'
     '                LogEvent("SYSTEM", "ERROR", "ATM bracket restore failed during the safety sweep: " + ex.Message);'),

    # ⚠️ A CONTROL FOR THE SCORING ITSELF, not for the restore. `run()` consults
    # check_no_dead_safety_machinery.py, and a gate that is wired into scoring but never actually
    # fails would make every mutant above look killed for the wrong reason. This injects an unwired
    # `Reconcile*` entry point, which the C# suite cannot see at all -- it compiles, nothing calls
    # it, 2180/0 stays green -- so if this is not KILLED, the gate is not in the loop.
    # [[a-green-that-can-never-be-red]]: for any status, name the input that makes it false.
    (GUARD,
     "CONTROL FOR THE SCORING: an unwired `Reconcile*` safety entry point is injected. The C#\n"
     "     suite cannot see it -- it compiles and nothing calls it -- so a KILL here proves\n"
     "     check_no_dead_safety_machinery.py is genuinely part of this battery's scoring, and a\n"
     "     SURVIVAL means every gate-dependent result above is worthless",
     '        internal static void LogFromComponent(string account, string eventType, string message)',
     '        internal void ReconcileNothingAtAll() { }\n'
     '        internal static void LogFromComponent(string account, string eventType, string message)'),

    (ATM,
     "the whole restore returns before doing anything, whatever calls it. Weaker than the wiring\n"
     "     mutants above and kept as the floor: if this survives, nothing in this battery is\n"
     "     measuring the restore at all",
     '            if (!_persistedRestorePending) return;',
     '            if (true) return;\n'
     '            if (!_persistedRestorePending) return;'),

    (ATM,
     "the sweep stops retrying, so the ONLY attempt is the one at init -- which runs during a\n"
     "     connection cycle, which is exactly when Account.All is not yet populated. The deferral\n"
     "     machinery survives intact with nothing ever asking again",
     '            // P2-136. The retry half. An init-time attempt runs during a connection cycle, so the\n'
     '            // account it needs may not be in `Account.All` yet; this is what asks again.\n'
     '            ReconcilePersistedBrackets();',
     '            // P2-136. The retry half. An init-time attempt runs during a connection cycle, so the\n'
     '            // account it needs may not be in `Account.All` yet; this is what asks again.\n'
     '            if (false) ReconcilePersistedBrackets();'),

    (ATM,
     "⚠️ RESTORED AND STILL UNMANAGED: the bracket goes back into the registry and no timer is\n"
     "     started. EnsureMonitor is called from PlaceBracket ONLY, so after a recompile nothing\n"
     "     sweeps -- the bracket is in the dictionary, the UI reports it, and its stop never\n"
     "     moves. Every membership assertion passes",
     '            if (restored > 0)\n'
     '                EnsureMonitor();',
     '            if (false)\n'
     '                EnsureMonitor();'),

    (ATM,
     "the sweep stops SAVING, so only the state at placement is ever on disk. A restore then\n"
     "     reinstates a bracket as if breakeven had never been reached -- and the breakeven branch\n"
     "     asks the broker to move the stop back DOWN, which is P1-139 arriving by a new route",
     '            if (active.Count > 0)\n'
     '                SaveBracketsToDisk();',
     '            if (false)\n'
     '                SaveBracketsToDisk();'),

    (ATM,
     "a restored bracket is not written back, so the restore UNDOES ITSELF on the next compile.\n"
     "     With 18 compiles measured in 2.5 hours that is minutes",
     '                _persistedRestorePending = false;\n'
     '                // Rewrite from the LIVE registry rather than emptying the file: brackets restored a',
     '                _persistedRestorePending = false;\n'
     '                if (false)\n'
     '                // Rewrite from the LIVE registry rather than emptying the file: brackets restored a'),

    # ---- group 7: loud vs silent, both directions ----------------------------------------------
    (ATM,
     "a MISSING file is reported as a failure, so every box that has never placed a managed\n"
     "     bracket gets an alarm on every startup. A detector that fires on everything passes\n"
     "     every positive test written for it",
     '                    _persistedRestorePending = false;\n'
     '                    return;\n'
     '                }\n'
     '                file = AtmBracketPersistence.Deserialise(System.IO.File.ReadAllText(_bracketStateFile));',
     '                    _persistedRestorePending = false;\n'
     '                    RiskGuardAddOn.LogFromComponent("", "ATM_BRACKET_RESTORE_FAILED",\n'
     '                        "no persisted ATM bracket registry was found, so nothing will move again.");\n'
     '                    return;\n'
     '                }\n'
     '                file = AtmBracketPersistence.Deserialise(System.IO.File.ReadAllText(_bracketStateFile));'),

    (PERSIST,
     "an UNPARSEABLE file returns an empty registry instead of null, so corruption reads as 'no\n"
     "     brackets were being managed' and the loud branch becomes unreachable. That is the\n"
     "     silent direction on a path where something WAS being managed",
     '            catch\n'
     '            {\n'
     '                return null;\n'
     '            }',
     '            catch\n'
     '            {\n'
     '                return new PersistedAtmBracketFile { Brackets = new List<PersistedAtmBracket>() };\n'
     '            }'),

    (PERSIST,
     "an EMPTY file is treated as unreadable, so the ordinary state of a box with no ATM trade\n"
     "     on becomes a corruption alarm. This is the conflation that painted 95 of 97 accounts\n"
     "     as the worst thing on a page",
     '                if (file.Brackets == null) file.Brackets = new List<PersistedAtmBracket>();\n'
     '                return file;',
     '                if (file.Brackets == null || file.Brackets.Count == 0) return null;\n'
     '                return file;'),

    (PERSIST,
     "the NaN pin goes away, so the registry is written with a bare `NaN` token -- not valid\n"
     "     JSON -- and every other reader of the file rejects the whole registry over a field\n"
     "     that is reset on restore anyway",
     '                FloatFormatHandling = FloatFormatHandling.String',
     '                FloatFormatHandling = FloatFormatHandling.DefaultValue'),
    # ---- group 6: P1-143, the budget must be CARRIED across the restore -------------------------
    # These mutants re-introduce the defect this battery's own subject SHIPPED WITH. P2-136's fix
    # reset the retry budget on restore, justified by "a record is consumed ONCE" -- true per
    # instance, and one nt_compile makes 3-4 instances. Every mutant below is a line that was in the
    # tree, green, deployed and live for a day.
    (PERSIST,
     "\u26a0\ufe0f P1-143 ITSELF, PUT BACK: the spent refusal budget is reset on restore. A provider that\n"
     "     always refuses gets a fresh MaxStopModifyAttempts on every assembly, and a compile makes\n"
     "     3-4 of those -- the bounded retry the budget exists to be becomes an order flood",
     '            return new AtmRestoreDecision\n'
     '            {\n'
     '                Bracket = b,\n'
     '                Verdict = AtmRestoreVerdict.Restored,',
     '            b.StopModifyAttempts = 0;\n'
     '            return new AtmRestoreDecision\n'
     '            {\n'
     '                Bracket = b,\n'
     '                Verdict = AtmRestoreVerdict.Restored,'),

    (PERSIST,
     "P1-143's quiet half: the ABANDON LATCH is cleared on restore, so the giving-up message is\n"
     "     re-said once per assembly. This is what kept the four resets from being obvious -- each\n"
     "     new instance believed it had never announced anything",
     '            return new AtmRestoreDecision\n'
     '            {\n'
     '                Bracket = b,\n'
     '                Verdict = AtmRestoreVerdict.Restored,',
     '            b.StopMoveAbandonAnnounced = false;\n'
     '            return new AtmRestoreDecision\n'
     '            {\n'
     '                Bracket = b,\n'
     '                Verdict = AtmRestoreVerdict.Restored,'),

    (PERSIST,
     "the recorded failure REASON is nulled on restore, so the abandon message that does survive\n"
     "     prints 'not recorded' instead of what the provider actually said. An alarm that keeps\n"
     "     firing and stops saying why",
     '            return new AtmRestoreDecision\n'
     '            {\n'
     '                Bracket = b,\n'
     '                Verdict = AtmRestoreVerdict.Restored,',
     '            b.LastStopMoveFailureReason = null;\n'
     '            return new AtmRestoreDecision\n'
     '            {\n'
     '                Bracket = b,\n'
     '                Verdict = AtmRestoreVerdict.Restored,'),

    # The NEGATIVE CONTROL, and it is the load-bearing one. "Carry the budget" must not become
    # "nothing can ever clear it", which would leave a recovered bracket permanently abandoned and
    # would pass every other mutant in this group.
    (ATM,
     "\u26a0\ufe0f the OPPOSITE failure to P1-143: an OBSERVED, CONFIRMED move no longer clears the carried\n"
     "     budget, so a bracket that genuinely recovered stays abandoned forever. Carrying a budget\n"
     "     across a compile is only safe while the event that SHOULD clear it still does",
     "                        bracket.StopModifyAttempts = 0;\n"
     "                        // P2-135. The abandonment episode ends where the CONDITION resolves, which is",
     "                        // P2-135. The abandonment episode ends where the CONDITION resolves, which is"),

    (ATM,
     "the per-instance guard stops guarding, so a later sweep's file re-read OVERWRITES a bracket\n"
     "     the monitor has already advanced -- discarding a stop price it moved. P1-143 removed the\n"
     "     budget reset from behind this guard; the clobbering half is still real",
     "                        alreadyLive = _activeBrackets.ContainsKey(decision.Bracket.BracketId);",
     "                        alreadyLive = false;"),
]

ORIGINALS = {p: open(p, encoding='utf-8').read() for p in {m[0] for m in MUTANTS}}


def restore():
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


def dead_machinery_gate():
    """
    ⚠️ SCORED ALONGSIDE THE SUITE, and the reason is measured. The mutant that puts `if (false)` in
    front of the only production call to `ReconcilePersistedBrackets` -- which kills the entire
    restore path -- CANNOT be killed by any C# assertion in this repo: NT8's startup path is not
    driveable from the test build, and a source assertion still finds the call text sitting inside
    the dead branch. It survived a 2176/0 suite.

    `check_no_dead_safety_machinery.py` is the gate that answers "does anything actually CALL this",
    and as of 2026-08-17 it deletes statically-dead branches before searching. So the honest scoring
    question is not "does the C# suite catch this" but "does any gate we run catch this", and the
    battery asks the gate directly rather than declaring an exemption. The alternative was an
    expected-survivor declaration, which records the hole instead of closing it.
    """
    try:
        p = subprocess.run(
            [sys.executable, os.path.join(REPO, 'tools', 'check_no_dead_safety_machinery.py')],
            cwd=REPO, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=120)
    except subprocess.TimeoutExpired:
        return 'GATE TIMEOUT'
    return None if p.returncode == 0 else 'DEAD-MACHINERY GATE FAILED'


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

    # ⚠️ A CRASH IS NOT A DETECTION, and without this the two are indistinguishable. The harness
    # prints its result line last, so an unhandled exception anywhere leaves 'NO RESULT LINE' --
    # which the scoring below counts as KILLED. That is right when assertions failed first and the
    # crash was a consequence; it is a FALSE KILL when the mutant merely broke the harness and
    # nothing detected it. Measured here: the `alreadyLive = false` mutant crashes the run with a
    # NullReferenceException, and it IS caught -- two P2-134 assertions fail on the way down. The
    # scoring could not tell, so it is told: the run must have printed at least one [FAIL].
    if not m and '[FAIL]' not in out:
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'

    # Only consulted when the suite is green: a red suite has already scored the mutant, and running
    # the gate anyway would make a build failure and a wiring failure print the same line.
    if result.endswith('Failed = 0'):
        gate = dead_machinery_gate()
        if gate:
            return result + ' + ' + gate
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
    # try/finally as well as the encoding pin above: the pin closes the one failure that has
    # actually happened twice, the finally closes EVERY way of leaving the loop with a mutant
    # applied, including a KeyboardInterrupt.
    try:
        res = run()
        mm = re.search(r'Failed = (\d+)', res)
        # Order matters: the undetected-crash verdict CONTAINS 'NO RESULT LINE', so it has to be
        # excluded before that substring is read as a kill.
        undetected_crash = 'NO ASSERTION FAILED' in res
        killed = (not undetected_crash) and (
            ('BUILD FAILED' in res) or ('NO RESULT LINE' in res)
            or ('GATE FAILED' in res) or ('GATE TIMEOUT' in res)
            or (mm is not None and int(mm.group(1)) > 0))
        print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
        if not killed:
            survivors.append(name)
    finally:
        restore()

restore()
print('\nrestored originals;', run())

print('\n%d/%d mutants killed' % (len(MUTANTS) - len(survivors), len(MUTANTS)))
if survivors:
    print('\nSURVIVORS -- each is a test the suite does not have:')
    for s in survivors:
        print('  *', s)
sys.exit(1 if survivors else 0)
