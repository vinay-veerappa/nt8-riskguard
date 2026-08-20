// P2-29 remainder, step 1. The independent top-level types that used to live at the bottom
// of RiskGuardAddOn.cs.
//
// ⚠️ THIS WAS A MOVE, NOT A REWRITE. Every type here is its own top-level type, not a member
// of RiskGuardAddOn, so nothing needed a `partial` keyword and no member was reshuffled.
// Both files sit in the same namespace and the same assembly, so every reference resolves
// exactly as before. That is the same operation that took RiskGuardWindow out in session 42.
//
// ⚠️ AND THE REASON P2-29 IS WORTH MORE THAN TIDINESS IS A HAZARD THIS FILE RE-CREATES:
// a pure code move SILENTLY DISARMED A SOURCE GATE last time. `mutate_p187.py`'s WarnOnly
// mutant survived after the window moved, because the test that kills it read
// `addons/RiskGuardAddOn.cs` BY NAME and the string it forbids had moved next door. The gate
// searched a file the string could no longer be in, found nothing, and PASSED.
//
// The two directions are not symmetric: a gate asserting a pattern is PRESENT fails loudly
// when pointed at the wrong file; one asserting a pattern is ABSENT passes vacuously. The
// remedy already exists -- `AllAddonCode()` concatenates every addons/*.cs and refuses an
// empty corpus -- which is why this move is safe to make now and was not before.
//
// The genuinely harder remainder is splitting RiskGuardAddOn ITSELF into
// {Core,Fsm,Rules,Actions,FirmMirror,Persistence} partials. That moves MEMBERS of one class
// rather than relocating independent types, and it is not this.
using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
#if !TESTING
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core;
#else
using NinjaTrader.Cbi;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core;
using NinjaTrader.Code;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
#endif

namespace NinjaTrader.NinjaScript.AddOns
{
    public enum GuardActionType
    {
        FlattenPosition,
        CancelAllOrders,
        CancelOrder,
        PlaceStopOrder
    }

    public class GuardAction
    {
        public string AccountName { get; set; }
        public GuardActionType ActionType { get; set; }
        public string Instrument { get; set; }
        public Instrument InstrumentObj { get; set; }
        public string OrderId { get; set; }
        public int Quantity { get; set; }
        public string RuleId { get; set; }
        // P1-19: other rules that demanded this same action and were coalesced into it.
        // Kept so merging does not erase why the action was taken.
        public List<string> MergedRuleIds { get; set; }
    }

    public class AccountState
    {
        public string AccountName { get; }
        public Dictionary<string, PositionState> Positions { get; } = new Dictionary<string, PositionState>();
        public double RealizedPnL { get; set; } = 0.0;
        // P1-17: realized PnL banked in *completed* sessions. RealizedPnL above is
        // session-scoped and zeroed at every reset, which is right for the daily-loss rule and
        // wrong for EvaluationTargetProfit -- a cumulative, multi-day prop evaluation target.
        // The total to evaluate a cumulative target against is TotalRealizedPnL below.
        // Accumulated once per session reset rather than per realized-PnL delta: a delta-based
        // total would be permanently corrupted by a single spurious tick (e.g. the broker
        // rebasing its own counter before our session reset runs), whereas a session total is
        // rebased every day and cannot drift.
        public double CumulativeRealizedPnL { get; set; } = 0.0;
        public double TotalRealizedPnL { get { return CumulativeRealizedPnL + RealizedPnL; } }
        // P1-16: realized PnL banked for the trade currently being closed, summed across its
        // partial exits and judged once at the flat transition. Deliberately not persisted --
        // a restart mid-trade settles it as a scratch rather than inventing a result.
        public double OpenTradeRealizedDelta { get; set; } = 0.0;
        // True from a flat transition until the next entry: the window in which a late fill
        // for the closed trade may still arrive and must revise its settlement.
        public bool ClosedTradeAwaitingLateFills { get; set; } = false;
        // The streak as it stood before the current trade was judged, so re-judging on a late
        // fill is a correction rather than a second increment.
        public int ConsecutiveLossesBeforeSettlement { get; set; } = 0;
        public double UnrealizedPnL { get; set; } = 0.0;
        public double PeakEquity { get; set; } = 0.0;
        public double PeakOpenGain { get; set; } = 0.0;
        public bool PeakGivebackTriggered { get; set; } = false;
        public double PeakGivebackLastTriggerUnrealized { get; set; } = double.NaN;
        public bool IsLockedOut { get; set; } = false;
        public DateTime LockoutUntil { get; set; } = DateTime.MinValue;
        public bool InitialLockoutFlattened { get; set; } = false;
        public DateTime LastLockoutFlattenAttempt { get; set; } = DateTime.MinValue;

        // P2-101. How many intervention attempts the CURRENT lockout phase has emitted, and
        // whether its give-up warning has been written. Both reset when a phase is entered.
        //
        // The retry's exit condition was "the position is still open", which in shadow mode is an
        // action the guard does not perform -- so it never exited. Measured 2026-08-14: ~12 lines
        // per minute per account, indefinitely, on three sim accounts AND the funded one, burying
        // interventions.jsonl. The general rule, and it is worth grepping for elsewhere: A RETRY
        // WHOSE EXIT CONDITION IS AN ACTION THE CURRENT MODE DOES NOT PERFORM WILL NEVER EXIT.
        public int LockoutPhaseAttempts { get; set; } = 0;
        public bool LockoutStuckLogged { get; set; } = false;

        /// <summary>
        /// P2-101. Everything the lockout PHASE machine owns, cleared together.
        ///
        /// Four call sites end a lockout -- the daily session reset, the deadline lapse, the
        /// not-locked-out sweep branch, and UnlockAccount -- and each had its own copy of the
        /// two-line reset. Adding a third field to the cluster meant editing all four, which is
        /// how P1-100's three readers happened. One method, four callers.
        /// </summary>
        public void ResetLockoutPhase()
        {
            CurrentLockoutPhase = LockoutPhase.None;
            InitialLockoutFlattened = false;
            LockoutPhaseAttempts = 0;
            LockoutStuckLogged = false;
        }
        // P2-46: order id -> first time seen inside the rate window. Keyed by id so one order
        // passing Submitted -> Accepted -> Working counts once, not three times.
        public Dictionary<string, DateTime> RecentOrderIds { get; set; } = new Dictionary<string, DateTime>();

        // P1-160: duplicate-entry anchors. Keyed by (instrument root, side) and stored by
        // Order OBJECT REFERENCE, because NT8's OrderId is neither unique nor stable.
        public Dictionary<string, RecentEntryAnchor> RecentEntryAnchors { get; set; } = new Dictionary<string, RecentEntryAnchor>();

        // P0-171. Both are RUNTIME-ONLY and deliberately absent from AccountPersistedData.
        //
        // ReplaySuppressionUntilUtc is stamped by OnConnectionStatusUpdate and covers the
        // reconnect burst; DuplicateEntryEvaluatedOrderIds makes one order draw one refusal
        // however many state transitions the platform reports for it. There are two because
        // they answer two different defects -- P0-171 and P1-167 -- not because either backs
        // the other up.
        //
        // ⚠️ THE TICKET SAID THE STAMP COVERS A POST-RECOMPILE REPLAY. IT DOES NOT, AND THERE
        // IS NO SUCH REPLAY TO COVER. Measured on this box 2026-08-19: SIX addon restarts
        // (03:29, 04:55, 05:42, 05:43, 15:18, 16:20) produced ZERO duplicate events, while the
        // day's only two clusters were 06:19 (9, the per-transition over-count) and 16:44 (45,
        // the reconnect). An assembly reload does not make NT8 re-send the session; a
        // reconnect does. Nor could the stamp cover it if it did -- subscribing to
        // Connection.ConnectionStatusUpdate does not replay past events, so a reload that
        // re-subscribes never sees a Connected event and never arms anything.
        //
        // Not persisting them is the point rather than an omission. A suppression deadline
        // restored from disk would be a suppression the guard cannot account for, and the set
        // is unbounded in principle -- it is bounded in practice only by a session's order
        // count, which a session reset clears along with everything else.
        public DateTime ReplaySuppressionUntilUtc { get; set; } = DateTime.MinValue;

        // ⚠️ KEYED BY OBJECT REFERENCE, NOT Order.Id, AND THE RULE 150 LINES AWAY SAYS SO IN AS
        // MANY WORDS: "Key by object reference, not Order.Id: NT8's OrderId is neither unique nor
        // stable." The P0-171 spec said to use the id; the id is the wrong key, and on THIS
        // operator's provider it is measurably the wrong key.
        //
        // Provider31 issues Order.Id as a submission GUID and REPLACES IT ON ACCEPT, while the
        // Simulator never does. Keyed on the id, the set is written under the submission id and
        // read under the accepted one: it never matches, P1-167 stays open on the live account,
        // and every test passes because Sim101 re-ids nothing. That is the whole of
        // [[the-simulator-re-ids-nothing]] -- never key on a value the broker owns.
        //
        // The other direction is worse. NT8's ids are not unique either, so two GENUINELY
        // different orders can share one, and the second would be silently skipped -- a refusal
        // the rule should have made and did not, which is the fail-OPEN direction.
        public HashSet<Order> DuplicateEntryEvaluatedOrders { get; set; }
            = new HashSet<Order>(OrderReferenceComparer.Instance);

        // Lockout phase: PendingCancel -> PendingFlatten -> Confirmed.
        // Only Confirmed stops emitting actions. This prevents the infinite
        // flatten loop where account.Flatten() fails silently but the sweep
        // keeps re-firing every second.
        public enum LockoutPhase { None, PendingCancel, PendingFlatten, Confirmed }
        public LockoutPhase CurrentLockoutPhase { get; set; } = LockoutPhase.None;



        /// <summary>
        /// P0-166. WHICH rule locked the account. A lockout pairs a trigger with a cure, and the
        /// cure that fits depends on the trigger: a session-scoped counter can only be cured by the
        /// session reset, while an order-rate burst really is cured by waiting. Without this field
        /// the lapse path cannot tell those apart, so "clear the counter when the cool-off ends"
        /// would be a blanket amnesty that forgave a loss streak because an unrelated flood lockout
        /// happened to expire. Persisted: a lockout survives a restart, so its reason must too.
        /// </summary>
        public string LockoutRuleId { get; set; } = null;
        
        // Session and Overtrading
        public DateTime LastSessionDate { get; set; } = DateTime.MinValue;
        public int TradesToday { get; set; } = 0;

        /// <summary>
        /// ⚠️ INJECTABLE CLOCK, AND ALL FOUR READS IN THIS CLASS GO THROUGH IT. Routing only the
        /// one a test needed would give AccountState TWO clocks -- a fake one for the debounce
        /// and the real one for the cooldown and the transition stamps -- and "a second reader of
        /// the same state that nobody compared" is the single most repeated defect shape in this
        /// repo (P1-100, P2-98/P1-99, P1-105). A half-injected clock is that shape by construction.
        ///
        /// Added because the trade-count test slept 1050ms to clear a 1000ms debounce. Driving the
        /// clock lets it assert the BOUNDARY instead of outlasting it, and CI runs this suite once
        /// per mutant (~660 times per full run), so the sleep was minutes of every run.
        ///
        /// Defaults to the real clock: production behaviour is unchanged and no caller moved.
        /// </summary>
        internal Func<DateTime> UtcNow = () => DateTime.UtcNow;
        public int ConsecutiveLosses { get; set; } = 0;
        public DateTime CooldownUntil { get; set; } = DateTime.MinValue;
        public double LastRealizedPnL { get; set; } = 0.0; // To track delta for consec losses
        public double SessionStartRealizedPnL { get; set; } = 0.0; // Baseline for session PnL

        // - Firm-mirror tracking (independent of discretionary PeakEquity) -
        public double FirmTrailingPeak { get; set; } = double.MinValue;
        public bool FirmFloorLocked { get; set; } = false;
        public DateTime FirmDailyDate { get; set; } = DateTime.MinValue;
        public double FirmDailyStartRealized { get; set; } = 0.0;
        public double FirmStartingBalance { get; set; } = 0.0;
        public bool LockoutWasShadowOnly { get; set; } = false;

        public AccountState(string name)
        {
            AccountName = name;
        }

        // P1-16: realized PnL arrives per execution, so a single trade exited in three partials
        // delivers three negative deltas. Counting each one as a "consecutive loss" made a
        // MaxConsecutiveLosses=3 lockout reachable from one losing trade, and put this counter
        // at odds with TradesToday, which is already debounced to the trade lifecycle.
        // Deltas are banked and judged once per trade. Three cases, because the relative order
        // of the realized-PnL event and the position-flat event is NOT guaranteed:
        //
        //  1. A trade is open  -> bank it; SettleClosedTrade judges the total at the flat
        //     transition. This is the fix: partial exits no longer count separately.
        //  2. The trade just closed and a late fill arrives -> revise the settlement in place
        //     rather than let the delta land on the next trade. This is why the running total
        //     and the pre-settlement streak are kept until the *next entry*, not cleared at
        //     settlement: re-judging from the snapshot is exact for any number of late fills,
        //     including one that flips the trade's net result from win to loss.
        //  3. No trade is tracked at all (the guard never saw the position, or this is a
        //     standalone adjustment) -> judge the delta on its own, preserving the pre-existing
        //     behaviour. Silently ignoring untracked realized losses would make the lockout
        //     less sensitive than before, which is not an acceptable trade for this fix.
        public void RecordRealizedDelta(double tradePnL, RiskConfig config)
        {
            OpenTradeRealizedDelta += tradePnL;

            if (ClosedTradeAwaitingLateFills)
            {
                ApplyTradeJudgement(config);
                return;
            }

            if (!HasOpenPosition())
            {
                ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
                ApplyTradeJudgement(config);
                OpenTradeRealizedDelta = 0.0;
                ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
            }
        }

        private bool HasOpenPosition()
        {
            foreach (var p in Positions.Values)
            {
                if (p.MarketPosition != MarketPosition.Flat) return true;
            }
            return false;
        }

        // Re-judges the current trade total from the streak as it stood before this trade was
        // settled, so calling it repeatedly as late fills arrive is idempotent rather than
        // cumulative. A scratch trade leaves the streak untouched in either direction.
        private void ApplyTradeJudgement(RiskConfig config)
        {
            ConsecutiveLosses = ConsecutiveLossesBeforeSettlement;

            if (OpenTradeRealizedDelta < -0.01)
                ConsecutiveLosses++;
            else if (OpenTradeRealizedDelta > 0.01)
                ConsecutiveLosses = 0;

            if (config != null && config.Overtrading != null
                && config.Overtrading.MaxConsecutiveLosses > 0
                && ConsecutiveLosses >= config.Overtrading.MaxConsecutiveLosses
                && config.Overtrading.CooldownMinutes > 0)
            {
                CooldownUntil = UtcNow().AddMinutes(config.Overtrading.CooldownMinutes);
            }
        }

        // Judges the trade that just closed. Called on flat transitions and on flips (a flip is
        // a close plus an entry in one update).
        private void SettleClosedTrade(RiskConfig config)
        {
            ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
            ApplyTradeJudgement(config);
            ClosedTradeAwaitingLateFills = true;
        }

        public bool UpdatePosition(Account account, Instrument instrument, MarketPosition position, int quantity, double avgPrice, double unrealizedPnL, RiskConfig config)
        {
            if (quantity == 0)
            {
                position = MarketPosition.Flat;
            }

            string instrumentName = instrument.FullName;
            if (!Positions.TryGetValue(instrumentName, out var pState))
            {
                pState = new PositionState(instrument);
                Positions[instrumentName] = pState;
            }

            bool stateChanged = false;

            bool wasNonFlat = pState.MarketPosition != MarketPosition.Flat;
            bool isNonFlat = position != MarketPosition.Flat;
            bool isFlip = wasNonFlat && isNonFlat && position != pState.MarketPosition;

            // Treat a flip as a close of the old trade followed by a new entry.
            if ((position == MarketPosition.Flat && wasNonFlat) || isFlip)
            {
                pState.LastFlatTransition = UtcNow();
                stateChanged = true;

                // P1-16: the trade is over -- judge it once, on its net realized result.
                SettleClosedTrade(config);

                if (isFlip)
                {
                    // NinjaTrader collapsed a close + reverse into one update.
                    // Log it so shadow data reveals how often flips occur.
                    NinjaTrader.Code.Output.Process(
                        $"[RiskGuard] FLIP detected on {AccountName}/{instrumentName}: " +
                        $"{pState.MarketPosition} -> {position}. Counted as close+entry.",
                        PrintTo.OutputTab1);
                }
            }

            // --- OPEN side: a new entry begins (flat->nonflat, or the new leg of a flip) ---
            if ((isNonFlat && !wasNonFlat) || isFlip)
            {
                pState.LastNonFlatTransition = UtcNow();

                // A flip closes the old position and opens a new opposite leg in one
                // update. Reset the per-open-position peak-giveback tracking so the
                // new leg is not judged against the prior direction's peak.
                if (isFlip)
                {
                    PeakOpenGain = 0.0;
                    PeakGivebackTriggered = false;
                    PeakGivebackLastTriggerUnrealized = double.NaN;
                }

                // Debounce multi-contract / split-order trade count increment:
                // Only increment TradesToday if this is a genuine new trade lifecycle
                // (either a flip, or position was flat for > 1000ms, or initial entry).
                bool isGenuineNewTrade = isFlip || pState.LastFlatTransition == DateTime.MinValue ||
                                         (UtcNow() - pState.LastFlatTransition).TotalMilliseconds > 1000;

                if (isGenuineNewTrade)
                {
                    TradesToday++; // Increment trade count
                }

                // P1-16: a new trade starts with a clean slate. Until this point the previous
                // trade's total and pre-settlement streak are deliberately retained so a late
                // fill can revise its judgement.
                ClosedTradeAwaitingLateFills = false;
                OpenTradeRealizedDelta = 0.0;
                ConsecutiveLossesBeforeSettlement = ConsecutiveLosses;
                stateChanged = true;
            }
            else if (position == MarketPosition.Flat && wasNonFlat)
            {
                pState.LastNonFlatTransition = DateTime.MinValue;
            }

            pState.MarketPosition = position;
            pState.Quantity = quantity;
            pState.AveragePrice = avgPrice;
            pState.UnrealizedPnL = unrealizedPnL;

            // When the account returns to flat, reset the per-open-position
            // peak-giveback tracking so it cannot carry into the next trade.
            if (position == MarketPosition.Flat && wasNonFlat)
            {
                bool accountNowFlat = true;
                foreach (var pos in Positions.Values)
                {
                    if (pos.MarketPosition != MarketPosition.Flat)
                    {
                        accountNowFlat = false;
                        break;
                    }
                }

                if (accountNowFlat)
                {
                    PeakOpenGain = 0.0;
                    PeakGivebackTriggered = false;
                    PeakGivebackLastTriggerUnrealized = double.NaN;
                }
            }

            return stateChanged;
        }

        public void RecordExecution(string instrument, string action, int quantity, double price)
        {
            // Simple calculation of PnL can be done if execution updates are matched,
            // but in practice NinjaTrader handles account balance updates directly.
        }
    }

    // P1-160: anchor record for the duplicate-entry rule. Stored by Order reference, not Id.
    /// <summary>
    /// Reference identity for Order, explicitly. HashSet&lt;Order&gt; would fall back to
    /// EqualityComparer&lt;Order&gt;.Default, which is whatever the PLATFORM's Order type decides
    /// Equals means -- a decision made in NinjaTrader's assembly, not this one, and free to change
    /// under a platform update. Stating it here makes the key a property of this code.
    /// </summary>
    internal sealed class OrderReferenceComparer : IEqualityComparer<Order>
    {
        internal static readonly OrderReferenceComparer Instance = new OrderReferenceComparer();

        public bool Equals(Order a, Order b)
        {
            return ReferenceEquals(a, b);
        }

        public int GetHashCode(Order o)
        {
            return System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(o);
        }
    }

    public class RecentEntryAnchor
    {
        public Order Order;
        public DateTime FirstSeenUtc;
    }

    // P1-160: shared name for orders placed by the trade copier, so the duplicate-entry guard
    // and the copier cannot drift apart on a rename.
    public static class CopierOrderNames
    {
        public const string Follow = "COPIER_FOLLOW";
    }

    public class FirmMirrorResult
    {
        public bool TrailingDDBreached { get; set; }
        public bool DailyLossBreached { get; set; }
        public double TrailingPeak { get; set; }
        public bool FloorLocked { get; set; }
        public double EffectiveFloor { get; set; }
        public double GuardFloor { get; set; }
        public double GuardDailyLimit { get; set; }
        public bool StateChanged { get; set; }
        public List<string> TraceLogs { get; set; } = new List<string>();
    }

    public class FirmDiagnosticsResult
    {
        public bool Success { get; set; }
        public List<string> Logs { get; set; } = new List<string>();
    }

    public class PositionState
    {
        public string Instrument { get; }
        public Instrument InstrumentObj { get; }
        public MarketPosition MarketPosition { get; set; } = MarketPosition.Flat;
        public int Quantity { get; set; }
        public double AveragePrice { get; set; }
        public double UnrealizedPnL { get; set; }
        public DateTime LastNonFlatTransition { get; set; } = DateTime.MinValue;
        public DateTime LastFlatTransition { get; set; } = DateTime.MinValue;

        public PositionState(Instrument instrument)
        {
            InstrumentObj = instrument;
            Instrument = instrument.FullName;
        }
    }

    internal static class RiskGuardOrderUtils
    {
        public static bool IsPositionReducingOrder(Order order, AccountState stateModel)
        {
            if (order == null || order.Instrument == null || stateModel == null) return false;
            string instrName = order.Instrument.FullName;
            if (!stateModel.Positions.TryGetValue(instrName, out var pState)) return false;

            if (pState.MarketPosition == MarketPosition.Long)
            {
                return order.OrderAction == OrderAction.Sell || order.OrderAction == OrderAction.SellShort;
            }
            else if (pState.MarketPosition == MarketPosition.Short)
            {
                return order.OrderAction == OrderAction.Buy || order.OrderAction == OrderAction.BuyToCover;
            }

            return false;
        }
    }

    // -
    // PER-POSITION GUARD STATE MACHINE (-6 of RiskGuardAddOn.md)
    // -
    // Tracks the protective-stop lifecycle for one (account, instrument) pair.
    // Eliminates the duplicate-SL race on OCO brackets by remembering that the
    // stop leg's Submitted event was already observed, so a later sweep or
    // re-entrant position update finds the FSM in ProtectedPending/Protected.
    public enum GuardFsmState
    {
        Unprotected,       // position open, no covering stop observed yet
        ProtectedPending,  // stop leg Submitted/Initialized/Accepted, not yet Working
        Protected,         // working stop covering the position
        FlattenPending,    // grace expired with OnMissing=Flatten, action emitted once
        Flat               // position closed; FSM entry awaiting cleanup
    }

    public class PositionGuardFsm
    {
        public string AccountName { get; }
        public string Instrument { get; }
        private GuardFsmState _state = GuardFsmState.Unprotected;
        public GuardFsmState State
        {
            get { return _state; }
            set
            {
                GuardFsmState previous = _state;
                _state = value;
                // Reset the per-episode auto-stop attempt counter when the FSM
                // reaches Protected (successful protection), reaches Flat (position
                // closed), transitions from Flat back to Unprotected (new episode),
                // or transitions from Protected back to Unprotected (protection
                // removed). We deliberately do NOT reset on Unprotected ->
                // ProtectedPending so that failed submit attempts continue to count
                // toward escalation.
                if (value == GuardFsmState.Protected && previous != value)
                    AutoStopAttempts = 0;
                else if (value == GuardFsmState.Flat && previous != value)
                    AutoStopAttempts = 0;
                else if (previous == GuardFsmState.Flat && value == GuardFsmState.Unprotected)
                    AutoStopAttempts = 0;
                else if (previous == GuardFsmState.Protected && value == GuardFsmState.Unprotected)
                    AutoStopAttempts = 0;
            }
        }
        public MarketPosition PositionSide { get; set; } = MarketPosition.Flat;
        public int PositionQuantity { get; set; }
        // P1-36. Coverage used to follow ONE Order. A trader covering a 6-lot position with two
        // working 3-lot stops therefore read as CoveredQuantity 3, the under-coverage rule fired,
        // and the guard attached a 3-lot auto-stop on top -- 9 lots of protection on a 6-lot
        // position, which flips it 3 lots the wrong way when the stops trigger. The guard
        // manufactured the reversal it exists to prevent.
        //
        // Coverage is now the SUM over every non-terminal protective stop working against this
        // position, and both `CoveredQuantity` and `RecognizedStopOrder` are DERIVED from that
        // list. They are read-only on purpose: the old pair had to be assigned together at nine
        // separate sites, and nothing stopped them drifting apart.
        //
        // NOTE: NT8 Order.OrderId is NOT unique and can change over the order's
        // lifetime (historical->live transition). Track recognised stops by the
        // Order object reference, not by id string. See RiskGuardAddOn.md -6.6.
        private readonly List<Order> _recognizedStops = new List<Order>();

        /// <summary>
        /// Drops stops that have gone terminal. Called on every read, so a cancelled or filled
        /// stop stops counting toward coverage the instant it is observed -- there is no window
        /// in which the FSM believes a dead order is protecting the position.
        /// </summary>
        private void PruneRecognizedStops()
        {
            _recognizedStops.RemoveAll(o => o == null || !RiskGuardAddOn.ProvidesCoverage(o.OrderState));
        }

        /// <summary>
        /// Adds a stop to the position's cover. Idempotent by object reference: NT8 raises
        /// OrderUpdate repeatedly for the same order, and counting one order twice would report
        /// cover that does not exist -- the same class of error as P1-36 itself, inverted.
        /// </summary>
        public void AddRecognizedStop(Order stop)
        {
            if (stop == null || !RiskGuardAddOn.ProvidesCoverage(stop.OrderState)) return;
            PruneRecognizedStops();
            if (_recognizedStops.Any(o => ReferenceEquals(o, stop))) return;
            _recognizedStops.Add(stop);
        }

        /// <summary>Removes one stop from the cover. Returns true if it was actually tracked.</summary>
        public bool RemoveRecognizedStop(Order stop)
        {
            if (stop == null) return false;
            int removed = _recognizedStops.RemoveAll(o => ReferenceEquals(o, stop));
            PruneRecognizedStops();
            return removed > 0;
        }

        /// <summary>True if this exact order is one of the stops currently covering the position.</summary>
        public bool IsRecognizedStop(Order stop)
        {
            if (stop == null) return false;
            return _recognizedStops.Any(o => ReferenceEquals(o, stop));
        }

        public void ClearRecognizedStops()
        {
            _recognizedStops.Clear();
        }

        /// <summary>Every live stop covering this position. Snapshot; safe to enumerate.</summary>
        public List<Order> RecognizedStops
        {
            get { PruneRecognizedStops(); return new List<Order>(_recognizedStops); }
        }

        /// <summary>
        /// The largest live stop covering the position, or null. Retained because the diagnostics
        /// surface and the qty-only-update path both want "the" stop, and because a single-stop
        /// position -- overwhelmingly the common case -- still has an unambiguous answer.
        /// It is NOT the coverage figure: use <see cref="CoveredQuantity"/> for that.
        /// </summary>
        public Order RecognizedStopOrder
        {
            get
            {
                PruneRecognizedStops();
                Order best = null;
                foreach (var o in _recognizedStops)
                    if (best == null || o.Quantity > best.Quantity) best = o;
                return best;
            }
        }

        public Order AutoStopOrder { get; set; }
        public string EntryOcoId { get; set; }   // best-effort join key; may be empty for external brackets
        public DateTime EntryTime { get; set; } = DateTime.MinValue;
        public DateTime GraceDeadline { get; set; } = DateTime.MinValue;
        public DateTime LastTransitionTime { get; set; } = DateTime.UtcNow;
        // One-shot grace timer: fires exactly at EntryTime + StopGuard.StopAttachSeconds.
        // Cancelled when the FSM reaches Protected or Flat. This replaces the sweep
        // polling of GraceDeadline with an instant event-driven trigger.
        public Timer GraceTimer { get; set; }

        /// <summary>
        /// Total quantity covered by every live protective stop on this position (P1-36).
        /// Derived, never assigned -- there is no way to record coverage that no order backs.
        /// </summary>
        public int CoveredQuantity
        {
            get
            {
                PruneRecognizedStops();
                int total = 0;
                foreach (var o in _recognizedStops) total += o.Quantity;
                return total;
            }
        }
        // True while a one-shot grace timer is armed.
        public bool GracePending { get; set; }
        // True once a grace action has been emitted and its outcome is still pending.
        public bool GraceEmitted { get; set; }
        // Monotonically increasing generation counter to invalidate stale timer callbacks.
        public long GraceGeneration { get; set; }
        // Number of auto-stop submit attempts in the current unprotected episode.
        // Escalation to flatten happens when this exceeds MaxAutoStopAttempts.
        public int AutoStopAttempts { get; set; }

        public PositionGuardFsm(string accountName, string instrument)
        {
            AccountName = accountName;
            Instrument = instrument;
        }
    }

    /// <summary>
    /// P2-41. `POST /api/riskguard/config` did `req.ToObject&lt;RiskConfig&gt;()` and handed the
    /// result straight to `SaveAndReloadConfig`. Deserialising a partial body into a complete
    /// `RiskConfig` gives every OMITTED field its default -- and that default was then written to
    /// `RiskGuard/config.json` and reloaded live. A caller posting `{"ExcludedAccounts":["X"]}` to
    /// add one exclusion also reset `Mode` to shadow, `MinShadowSessions` to 0, `EnableWindowGate`
    /// to false, and every StopGuard/PnLRules/FirmMirror value to its default -- destroying the
    /// live risk configuration. The response then said `"applied"` and echoed the REQUEST, so
    /// nothing about the reply revealed it.
    ///
    /// This lives here, not in `McpBridgeAddOn.cs`, because that file is excluded from the test
    /// build (WPF dependencies). The merge is pure JSON manipulation with nothing NinjaTrader
    /// about it, so keeping it here is what makes it testable at all.
    /// </summary>
    public static class RiskConfigMerge
    {
        /// <summary>
        /// Returns <paramref name="live"/> with only the keys present in <paramref name="patch"/>
        /// replaced. Nested objects merge recursively; arrays are REPLACED, not concatenated.
        ///
        /// Arrays replace deliberately. Union semantics would make `ExcludedAccounts` an
        /// append-only list with no way to remove an entry through the API, and concatenation is
        /// the exact mechanism behind P1-39 -- a list that grew on every write until a default
        /// could never be deleted. Replace is also what a caller means by sending an array.
        /// </summary>
        public static JObject Merge(JObject live, JObject patch)
        {
            if (live == null) return patch == null ? new JObject() : (JObject)patch.DeepClone();
            var merged = (JObject)live.DeepClone();
            if (patch == null) return merged;

            merged.Merge(patch, new JsonMergeSettings
            {
                MergeArrayHandling = MergeArrayHandling.Replace,
                // A caller who explicitly sends null means "clear this", which is a different
                // instruction from omitting the key. Omitted keys never appear in `patch` at all,
                // so they are untouched either way.
                MergeNullValueHandling = MergeNullValueHandling.Merge
            });
            return merged;
        }

        /// <summary>
        /// Convenience for the bridge: merge a partial body onto the live config and hand back a
        /// typed config plus the merged document to echo. Echoing the RESULT rather than the
        /// request is half the fix -- the old reply looked identical whether the merge happened
        /// or not.
        /// </summary>
        public static RiskConfig Apply(RiskConfig liveConfig, JObject patch, out JObject mergedJson)
        {
            var live = liveConfig == null ? new JObject() : JObject.FromObject(liveConfig);
            mergedJson = Merge(live, patch);
            return mergedJson.ToObject<RiskConfig>();
        }

        public static RiskConfig DeepCopy(RiskConfig source)
        {
            if (source == null)
            {
                return null;
            }

            return Apply(source, null, out _);
        }
    }

    public class PersistedStateData
    {
        public bool IsArmed { get; set; }
        public string Mode { get; set; }
        public List<string> LockedOutAccounts { get; set; } = new List<string>();
        // FR-29: count of completed shadow sessions. Persisted across restarts.
        public int ShadowSessionsCompleted { get; set; }
        // P1-37: the session date the counter was last incremented for. This MUST travel
        // with the counter. Persisting one without the other is what let a restart re-count
        // the same day -- the counter came back, the "already counted today" marker did not,
        // and MinShadowSessions could be satisfied by recompiling three times.
        public DateTime LastShadowSessionDate { get; set; } = DateTime.MinValue;
        
        // P2-142: WHEN an operator deliberately disarmed, or null if none has.
        //
        // ⚠️ THIS IS NOT `IsArmed` AND MUST NEVER BECOME IT. `IsArmed` is deliberately NOT
        // rehydrated (FR-30/31: a persisted `true` must never silently re-arm a guard across a
        // restart). This field is the opposite direction only: it carries a deliberate DISARM so
        // that arming remains an act and disarming is not undone by somebody else's recompile.
        //
        // Nullable because three states have to be distinguishable and a bool only carries two:
        // "an operator disarmed at T", "no operator has disarmed", and -- for an old state file
        // written before this field existed -- "unknown", which reads as null and so behaves as
        // the safe answer, arming per mode. A bool would have made a fresh install and a
        // deliberate disarm identical.
        public DateTime? OperatorDisarmedUtc { get; set; }

        // P2-142: identity of the process that wrote this state, so a RECOMPILE can be told from a
        // RESTART. A NinjaScript recompile builds a new assembly inside the SAME process and wipes
        // every static singleton, which this code counted as a new session -- 84 ARMED_ON_START
        // events in one 3 MB tail were 84 "sessions" by that reckoning and one by the operator's.
        public int HostProcessId { get; set; }
        public DateTime? HostProcessStartUtc { get; set; }

        // Dictionary for per-account persisted data
        public Dictionary<string, AccountPersistedData> AccountsData { get; set; } = new Dictionary<string, AccountPersistedData>();

        public DateTime Timestamp { get; set; }
    }

    public class AccountPersistedData
    {
        public DateTime LastSessionDate { get; set; }
        public int TradesToday { get; set; }
        public int ConsecutiveLosses { get; set; }
        public double PeakEquity { get; set; }
        public double LastRealizedPnL { get; set; }
        public double SessionStartRealizedPnL { get; set; }
        public string LockoutRuleId { get; set; }   // P0-166
        // P1-17: must persist -- a cumulative evaluation target that resets on recompile is
        // not cumulative.
        public double CumulativeRealizedPnL { get; set; }
        public double FirmTrailingPeak { get; set; }
        public bool FirmFloorLocked { get; set; }
        public DateTime FirmDailyDate { get; set; }
        public double FirmDailyStartRealized { get; set; }
        public double FirmStartingBalance { get; set; }
        // P1-54: the lockout DEADLINE must persist, not just the fact of the lockout. The
        // top-level LockedOutAccounts name list restored IsLockedOut = true with LockoutUntil
        // left at MinValue, so any restart -- and a recompile is a restart here -- silently
        // converted a 60-minute lockout into one that lasts until the session reset.
        public DateTime LockoutUntil { get; set; }
        public bool LockoutWasShadowOnly { get; set; }
        // P1-173, and it is P1-54 one field over: a DEADLINE has to persist, not just the fact
        // that something was triggered. CooldownUntil is written on a consecutive-loss breach and
        // read in EvaluateRules as the gate that raises COOLDOWN_BREACH -> FlattenPosition, and it
        // was absent from this class entirely -- so a restart set it to MinValue and the rule could
        // not fire for the remainder of a cooldown that was supposed to be running.
        //
        // ⚠️ THE ACTION THAT DEFEATED IT IS ONE THE OPERATOR ALREADY PERFORMS. The cooldown exists
        // to interrupt revenge trading after a run of losses; NinjaScript's recompile button
        // cleared it. Six recompiles happened on this box on the day it was found, none for that
        // reason. [[a-successful-compile-wipes-static-state]].
        //
        // Found by tools/check_account_state_persisted.py on its first run. Nothing was wrong with
        // any line of the cooldown code -- the defect was an OMISSION from this class, which has no
        // source location for a reviewer to look at.
        public DateTime CooldownUntil { get; set; }
        // P1-174, the third instance of the recompile-wipes-state class. The peak-giveback
        // rail's PER-POSITION state. A recompile set PeakOpenGain to 0.0, and the rule's next
        // evaluation found UnrealizedPnL > 0 and RE-BASELINED the peak to the CURRENT unrealized
        // -- so the giveback was measured from a lower high and fired late or not at all, for as
        // long as that position stayed open.
        //
        // ⚠️ THE RULE ALREADY SET _stateDirty = true FOR THESE THREE, on both branches. That is
        // the flag which schedules a state write, for fields the writer did not carry: a write to
        // nowhere, and better evidence than any argument about whether persisting is worthwhile.
        //
        // ⚠️ NOT the same as PeakEquity, which is the ACCOUNT-level peak behind
        // TRAILING_DD_BREACH and was always persisted. Account peak durable, position peak not,
        // is exactly the asymmetry that hid this.
        public double PeakOpenGain { get; set; }
        public bool PeakGivebackTriggered { get; set; }
        // Persisted as a plain double: JSON has no NaN literal, so a DTO that predates this field
        // deserializes it as 0.0 rather than NaN. The restore normalises that -- see there.
        public double PeakGivebackLastTriggerUnrealized { get; set; }
    }

    // -
    // CONFIGURATION MODELS
    // -

    public class InstrumentProfile
    {
        public int MaxContracts { get; set; } = 5;
    }

    public class AccountRiskProfile
    {
        public string ProfileName { get; set; } = "Default";
        public string AccountNamePattern { get; set; } = ".*";

        public double DailyLossLimit { get; set; } = 0.0;
        public double TrailingDrawdown { get; set; } = 0.0;
        public int MaxTradesPerSession { get; set; } = 0;
        public int DefaultMaxContracts { get; set; } = 0;

        public Dictionary<string, InstrumentProfile> InstrumentProfiles { get; set; } = new Dictionary<string, InstrumentProfile>(StringComparer.OrdinalIgnoreCase);
    }

    /// <summary>
    /// P2-163. Not a bool, because "blocked" and "not on the allow-list" are different things for the
    /// operator to act on -- one is a day-by-day exclusion they set, the other means the instrument
    /// was never in the permitted set at all.
    /// </summary>
    public enum InstrumentPermission
    {
        Permitted,
        Blocked,
        NotAllowed
    }

    public class PerInstrumentRiskConfig
    {
        // Only MaxContracts is enforced. Per-instrument blocking is intentionally
        // not a property here; blocking has exactly one mechanism: BlockedInstruments.
        // See P2-78.
        public int MaxContracts { get; set; } = 10;
    }

    // P1-39: every List property below carries ObjectCreationHandling.Replace. Json.NET's
    // default (Auto) REUSES a collection that a property initializer already populated and
    // *appends* the deserialized items to it, so each load re-added the initializer's contents.
    // Only WindowsET/Days had non-empty initializers and therefore actually corrupted, but any
    // default added to the others later would silently become the same bug.
    //
    // This is deliberately per-property and NOT set on the serializer. The dictionaries here
    // (InstrumentLimits, and FirmMirrorConfig's AccountFirmMap/FirmProfiles) are constructed
    // with StringComparer.OrdinalIgnoreCase; Replace would discard that instance and hand back
    // a fresh Dictionary using the default comparer, quietly making instrument and firm lookups
    // case-sensitive. They are empty-initialized, so appending to them is already correct.
    public class RiskConfig
    {
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<AccountRiskProfile> Profiles { get; set; } = new List<AccountRiskProfile>();
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<string> ExcludedAccounts { get; set; } = new List<string>();
        // Accounts listed here MAY bypass a persisted lockout when the guard is disarmed.
        // Accounts NOT listed here keep their lockout enforced even when disarmed (safe default for prop-firm accounts).
        // Default empty = lockouts persist for ALL accounts regardless of armed state.
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<string> LockoutBypassWhileDisarmedAccounts { get; set; } = new List<string>();
        public string Mode { get; set; } = "shadow";
        public bool EnableWindowGate { get; set; } = false;
        // FR-29: minimum completed shadow sessions before live-mode arming is permitted (soft gate).
        // Set to 0 to disable. The counter is persisted in PersistedStateData and incremented on session reset.
        // P1-84. Was 0, and RunPreflight's FR-29 gate reads
        // `MinShadowSessions > 0 && _shadowSessionsCompleted < MinShadowSessions` -- so zero
        // does not relax the precondition, it SWITCHES IT OFF, and live arming was gated on
        // nothing at all. Five is roughly a week of sessions watched without the guard wanting
        // to intervene wrongly, before it can be pointed at live money.
        public int MinShadowSessions { get; set; } = 5;
        public int AuditIntervalSeconds { get; set; } = 10;
        public Dictionary<string, PerInstrumentRiskConfig> InstrumentLimits { get; set; } = new Dictionary<string, PerInstrumentRiskConfig>(StringComparer.OrdinalIgnoreCase);
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        /// <summary>
        /// P2-163 / P1-168. DEFAULT-DENY, and it lives here rather than on `PropFirmProfile` because
        /// it and `BlockedInstruments` are one question -- "may this account trade this instrument" --
        /// and a question with its two halves in two config objects gets two answers.
        ///
        /// There WAS an `AllowedInstruments` on `PropFirmProfile`, defaulting to
        /// `NQ, MNQ, ES, MES, YM, MYM, CL, MCL, GC, MGC, RTY, M2K`. Its only reader anywhere was a
        /// unit test that built its own list and asserted `Contains("MNQ")` on it -- so the default
        /// that PERMITTED every full-size contract was never consulted by anything. Deleted rather
        /// than deprecated, which is the precedent `P1-81` set in that same file for `ArmedForLive`.
        ///
        /// ⚠️ The default is MICROS ONLY, and that is a deliberate behaviour change. With
        /// `DailyLossLimit: 250`, ONE full-size contract at the guard's own catastrophe-stop distance
        /// is $200 -- 80% of the day in a single trade (ES 16 ticks x $12.50, NQ 40 ticks x $5.00).
        /// The instrument restriction is not a preference; it is what makes the daily limit coherent.
        ///
        /// ⚠️ An EMPTY list permits everything. That is the documented escape hatch, not an oversight:
        /// default-deny driven by a list that an upgrade could deserialize as empty would otherwise
        /// refuse every order on the account, and "fail closed" applied to a legitimately empty set is
        /// how 95 of 97 accounts once got painted WORST. A list you have emptied on purpose reads the
        /// same as one an upgrade lost, so this errs toward not trapping the operator -- the guard
        /// still has BlockedInstruments, the caps, and the P&L rails.
        /// </summary>
        public List<string> AllowedInstruments { get; set; } =
            new List<string> { "MNQ", "MES", "MYM", "MCL", "MGC", "M2K" };

        /// <summary>
        /// The day-by-day override. Checked FIRST and wins over the allow-list, because the operator
        /// asked to be able to exclude an instrument they normally trade (MNQ) without rewriting the
        /// permitted set.
        /// </summary>
        public List<string> BlockedInstruments { get; set; } = new List<string>();
        public AlertsConfig Alerts { get; set; } = new AlertsConfig();
        public SizingConfig Sizing { get; set; } = new SizingConfig();
        public OvertradingConfig Overtrading { get; set; } = new OvertradingConfig();
        public StopGuardConfig StopGuard { get; set; } = new StopGuardConfig();
        public PnLRulesConfig PnLRules { get; set; } = new PnLRulesConfig();
        public FirmMirrorConfig FirmMirror { get; set; } = new FirmMirrorConfig();
        // FR-35/36: override friction for override_with_friction enforcement mode.
        public OverrideConfig Override { get; set; } = new OverrideConfig();
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<WindowConfig> WindowsET { get; set; } = new List<WindowConfig>
        {
            new WindowConfig { Name = "NY_AM_Macro", Start = "09:50", End = "11:10" },
            new WindowConfig { Name = "NY_PM_Macro", Start = "13:50", End = "15:10" }
        };
    }

    // FR-35/36: friction-gated lockout override. When Mode == "override_with_friction",
    // escaping a lockout requires typing the exact confirm phrase AND waiting wait_seconds
    // (enforced minimum 30s). This prevents one-click panic bypasses.
    public class OverrideConfig
    {
        public string ConfirmPhrase { get; set; } = "I understand locked means locked";
        // FR-36 enforced minimum: clamped to >= 30 at validation time.
        public int WaitSeconds { get; set; } = 120;
    }

    public class FirmMirrorConfig
    {
        public bool Enabled { get; set; } = false;
        public FirmTrailingDDConfig TrailingDD { get; set; } = new FirmTrailingDDConfig();
        public FirmDailyLossConfig DailyLoss { get; set; } = new FirmDailyLossConfig();
        public int DailyResetHourUtc { get; set; } = 22;
        public int DailyResetMinuteUtc { get; set; } = 0;
        // P2-95: populated by ResolveEffectiveFirmConfig from the matched FirmProfile.
        // Not serialized in config — it is a transient carrier so ComputeFirmMirror can
        // use the plan's stated AccountSize as the starting balance instead of the
        // heuristic (balance - realized - unrealized), which is session-scoped and wrong
        // by the account's lifetime profit. JsonIgnore because it is never user-configured.
        [JsonIgnore]
        public double ResolvedAccountSize { get; set; } = 0.0;
        // Per-firm profiles: map account name -> firm name. The matching FirmProfile in FirmProfiles
        // supplies the firm-specific drawdown/daily-loss rules. Falls back to TrailingDD/DailyLoss above
        // when an account is not mapped or the firm name is not found.
        public Dictionary<string, string> AccountFirmMap { get; set; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string, FirmProfile> FirmProfiles { get; set; } = new Dictionary<string, FirmProfile>(StringComparer.OrdinalIgnoreCase);
    }

    // Per-firm rules researched 2026-08-02. All four firms use EOD trailing drawdown for evaluations;
    // daily loss limits vary (TPT has none). Reset boundary is CME Globex rollover (~22:00 UTC).
    public class FirmProfile
    {
        public string Name { get; set; } = "";

        /// <summary>
        /// The account size these dollar amounts were derived for, or 0 for "not stated".
        ///
        /// CONFIG_DEFAULTS R3: a dollar limit is derived from the account, never guessed. None of
        /// the four researched profiles stated a size, which is why `Apex` carried 2000 while Apex
        /// publishes 2500 on a 50k and 3000 on a 100k -- tighter than the firm's own number, which
        /// is the safe direction, but nothing in the file said which direction it was. Keys are
        /// now plan names (`Apex-100K`), and this is the machine-readable half of that: preflight
        /// compares it against the account's observed equity, so a 100k account mapped to a 50k
        /// plan is refused instead of silently protected at the wrong threshold.
        ///
        /// 0 means unstated and is NOT an error -- the check is opt-in per plan, because an
        /// operator adding a plan should not be blocked from arming until they have researched a
        /// number they may not have. A plan that states nothing is checked for nothing.
        /// </summary>
        public double AccountSize { get; set; } = 0.0;

        public FirmTrailingDDConfig TrailingDD { get; set; } = new FirmTrailingDDConfig();
        public FirmDailyLossConfig DailyLoss { get; set; } = new FirmDailyLossConfig();
    }

    public class FirmTrailingDDConfig
    {
        public bool Enabled { get; set; } = false;
        public string Type { get; set; } = "intraday";
        public bool IncludesUnrealized { get; set; } = true;
        public double Amount { get; set; } = 2500.0;
        public double Buffer { get; set; } = 300.0;
        public double LockAtProfit { get; set; } = 0.0;
    }

    public class FirmDailyLossConfig
    {
        public bool Enabled { get; set; } = false;
        public string Basis { get; set; } = "realized";
        public double Amount { get; set; } = 1500.0;
        public double Buffer { get; set; } = 200.0;
    }

    /// <summary>
    /// F-6. What the guard decides to push, and nothing about HOW it is delivered.
    ///
    /// ⚠️ THERE IS NO WEBHOOK URL HERE, ON PURPOSE. This addon publishes its config over HTTP on
    /// :7890 (`/api/riskguard/config`, and `nt_riskguard_inventory` reads the same structures), so
    /// a secret stored here is a secret published. The URL lives with the RELAY, in
    /// tvDownloadOHLC's `discord_webhooks.json`, and never enters this process at all -- which is
    /// strictly better than redacting it on the way out, because there is nothing to redact.
    /// </summary>
    public class AlertsConfig
    {
        public bool Enabled { get; set; } = true;

        /// <summary>"critical", "warning" or "info". An UNRECOGNISED value falls back to
        /// "warning" rather than to the lowest rank -- see GuardAlertSink.FloorRankOf, where
        /// treating a typo as rank 0 would have pushed the entire audit stream.</summary>
        public string MinSeverity { get; set; } = "warning";
    }

    public class SizingConfig
    {
        public int MaxContractsPerAccount { get; set; } = 10;
        public int MaxContractsAggregate { get; set; } = 20;
        public int ExpectedCopies { get; set; } = 1; // intended N-way mirror across accounts
    }

    public class OvertradingConfig
    {
        public int MaxTradesPerSession { get; set; } = 8;
        public int CooldownMinutes { get; set; } = 5;
        public int MaxConsecutiveLosses { get; set; } = 3;
        // P2-46: was hardcoded at 5 in the order-rate governor, unlike every other limit here.
        public int MaxOrdersPerSecond { get; set; } = 5;
        public int LockoutMinutes { get; set; } = 60;

        // `P1-160`. Two entries for the same instrument and side inside this window are a
        // duplicate, not a scale-in. 0 switches the rule off, matching every other limit here.
        //
        // ⚠️ 1000ms is a DELIBERATE default, not a placeholder. The measured duplicate gaps
        // were 26ms, 99ms and 150ms, so the margin is nearly sevenfold -- and the value is bounded
        // from the other side by what a human can do on purpose: nobody places two separate
        // entries a second apart and means both. A rule that ships at 0 is a rule nobody turns on.
        public int DuplicateEntryWindowMs { get; set; } = 1000;

        /// <summary>
        /// P0-171, SECOND ATTEMPT. How long after ANY connection transition the duplicate-entry
        /// rule stays suppressed, because NT8 replays the session inside that window and the rule
        /// times orders by when the guard first SAW them.
        ///
        /// ⚠️ THIS IS NOT THE DUPLICATE WINDOW, AND USING THE DUPLICATE WINDOW IS WHAT FAILED.
        /// The first fix armed the suppression on `Connected` for one 1000ms window. Measured on
        /// two real reconnects, that covers nothing, because THE REPLAY ARRIVES BEFORE
        /// `Connected` DOES:
        ///
        ///     event            16:44 (natural)   00:34 (induced)
        ///     Connecting       42.444            43.519
        ///     replay burst     44.275 - 44.471   44.619 - 44.686
        ///     Connected        44.711            44.773     <- 240ms / 87ms AFTER the burst
        ///
        /// So the value has to span `Connecting` -> end of replay, measured at 2027ms and 1167ms.
        /// 1000ms misses both. 2000ms misses the natural one BY 27ms, which is why the default is
        /// not "just above the worst sample": 5000ms leaves ~3s of margin on both.
        ///
        /// It is re-armed on EVERY transition (Disconnecting, Disconnected, Connecting, Connected),
        /// so the arm that actually covers the burst is the latest one before it. Still bounded --
        /// 5s from the last transition and then the rule is live again.
        /// </summary>
        public int ReconnectReplayGraceMs { get; set; } = 5000;
    }

    public class StopGuardConfig
    {
        public string OnMissing { get; set; } = "Flatten"; // "AutoStop", "Flatten"

        // P1-84 / R5. Was 3, which is the single most likely reason this system gets switched
        // off: three seconds from fill to a working stop, and OnMissing above is "Flatten", so
        // entering manually and reaching for the mouse to place the stop gets you flattened on
        // a day when nothing was wrong. A default that fires on a normal day is a default that
        // disarms the guard, and a guard that is off during the one session that mattered has
        // provided exactly nothing.
        //
        // WARNING: THE NUMBER IS ONLY RIGHT FOR "Flatten", and that pairing is deliberate. If OnMissing
        // were "AutoStop" a much shorter deadline would be correct, because an invented stop is
        // recoverable and being taken out of the trade is not. It stays a plain default rather
        // than a value computed from OnMissing: a getter that recomputes would let a config
        // reload move a deadline while a grace timer was already running, and would read
        // OnMissing off one thread while another wrote it. The relationship is real; expressing
        // it as a mechanism costs more than it is worth. The test that guards this is
        // conditional on OnMissing for exactly the same reason.
        public int StopAttachSeconds { get; set; } = 15;

        public int MaxAutoStopAttempts { get; set; } = 2;
        public Dictionary<string, int> Offsets { get; set; } = new Dictionary<string, int>
        {
            { "NQ", 40 },
            { "MNQ", 40 },
            { "ES", 16 },
            { "MES", 16 },
            { "default", 30 }
        };
    }

    public class PnLRulesConfig
    {
        public double DailyLossLimit { get; set; } = 1000.0;
        public double TrailingDrawdown { get; set; } = 1500.0;
        public int LockoutMinutes { get; set; } = 60;
    }

    public class WindowConfig
    {
        public string Name { get; set; }
        public string Start { get; set; }
        public string End { get; set; }
        // P1-39: non-empty initializer + Json.NET's default Auto handling meant every load
        // appended another Mon-Fri to whatever the file declared. Live Days lists had reached
        // 20-25 entries. Harmless to the gate itself (Days parses into a HashSet) but it is
        // what made the corruption visible and unbounded.
        [JsonProperty(ObjectCreationHandling = ObjectCreationHandling.Replace)]
        public List<string> Days { get; set; } = new List<string> { "Monday", "Tuesday", "Wednesday", "Thursday", "Friday" };
    }

    public class ParsedWindow
    {
        public TimeSpan Start { get; set; }
        public TimeSpan End { get; set; }
        public HashSet<DayOfWeek> Days { get; set; }
    }
}
