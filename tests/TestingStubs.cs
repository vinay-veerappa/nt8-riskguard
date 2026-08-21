#if TESTING
// Minimal stubs for the NinjaTrader types that RiskGuardAddOn.cs (and the rest of the
// addons) use but that only exist inside the NinjaTrader runtime.
//
// P2-27 step 1: the bulk of these stubs used to sit at the top of
// tests/RiskGuardAddOnTests.cs, above 1147 tests and a Main(). That made them
// unreachable from any other project -- nt8-mcp-bridge cannot reference a file that
// owns an entry point -- so its harness could not compile McpBridgeAddOn.cs at all.
// Moving them here is mechanical and semantically neutral: same compilation unit,
// same types, same members.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NinjaTrader.Cbi;

// --- MOCK DEFINITIONS TO AVOID NINJATRADER ASSEMBLY DEPENDENCY IN TEST ENVIRONMENT ---
namespace NinjaTrader.Cbi
{
    public enum MarketPosition { Flat, Long, Short }
    public enum Currency { UsDollar }
    public enum AccountItem { CashValue, RealizedProfitLoss, UnrealizedProfitLoss, NetLiquidation }

    public class AccountItemEventArgs : EventArgs
    {
        public AccountItem AccountItem { get; set; }
        public double Value { get; set; }
        public Currency Currency { get; set; }
    }
    // ALL SIXTEEN of NT8's OrderStates, in the order NinjaTrader.Cbi.OrderState declares
    // them. This stub used to carry ten, so six states could not be expressed by ANY test
    // and the suite was green at 686/0 while P0-59 was live on the box.
    //
    // Obtained by reflection, not by memory:
    //   [Reflection.Assembly]::LoadFrom("C:\Program Files\NinjaTrader 8\bin\NinjaTrader.Core.dll")
    //   [Enum]::GetNames($asm.GetType("NinjaTrader.Cbi.OrderState"))
    //
    // TestOrderLiveness_ClassifiesEveryNT8OrderState pins this list against
    // RiskGuardAddOn.Classify, so adding a state here without classifying it fails the
    // suite. Keeping the stub honest about the shape of the world is the whole point:
    // a test double we author is not evidence about NT8 unless something forces it to agree.
    public enum OrderState
    {
        Accepted, Cancelled, Filled, Initialized, PartFilled, CancelSubmitted,
        ChangeSubmitted, Submitted, TriggerPending, Rejected, Working, CancelPending,
        ChangePending, Suspended, AcceptedByRisk, Unknown
    }
    public enum OrderType { Limit, StopMarket, StopLimit, Market }
    public enum OrderAction { Buy, Sell, BuyToCover, SellShort }
    public enum TimeInForce { Day, Gtc }
    public enum PerformanceUnit { Currency, Percent, Pips, Points, Ticks }

    /// <summary>
    /// Stub of NT8's broker-provider enum. Only <c>Simulator</c> is load-bearing: it is
    /// how the copier tells a practice account from one that can lose real money, now
    /// that the account NAME is no longer trusted for that (P1-20).
    /// </summary>
    public enum Provider { NinjaTrader, Simulator, Playback, Rithmic, ContinuumFix, InteractiveBrokers }

    public class Instrument
    {
        public string FullName { get; set; }
        public MasterInstrument MasterInstrument { get; set; }
        public MarketData MarketData { get; set; }
        public Instrument(string name)
        {
            FullName = name;
            MasterInstrument = new MasterInstrument { Name = name, TickSize = 0.25 };
            MarketData = new MarketData { Last = new Last { Price = 0.0 } };
        }

        /// <summary>
        /// Stub of NT8's instrument lookup. Its absence was the ONLY thing forcing
        /// TradeCopierEngine.OnExecution (the entire trade-copy path, and the riskiest code in
        /// the addon) to sit inside `#if !TESTING`, i.e. compiled out of the test build with
        /// zero coverage. Registered instruments can be seeded by tests; unknown names resolve
        /// to a fresh instrument so symbol translation still works.
        /// </summary>
        public static Dictionary<string, Instrument> Registry =
            new Dictionary<string, Instrument>(StringComparer.OrdinalIgnoreCase);

        public static Instrument GetInstrument(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            Instrument found;
            if (Registry.TryGetValue(name, out found)) return found;
            var created = new Instrument(name);
            Registry[name] = created;
            return created;
        }
    }

    public class MasterInstrument
    {
        public string Name { get; set; }
        public double TickSize { get; set; }
        public double RoundToTickSize(double value) => Math.Round(value / TickSize) * TickSize;
    }

    public class MarketData
    {
        public Last Last { get; set; }
        public Ask Ask { get; set; }
        public Bid Bid { get; set; }
    }

    public class Last
    {
        public double Price { get; set; }
    }

    public class Ask
    {
        public double Price { get; set; }
    }

    public class Bid
    {
        public double Price { get; set; }
    }

    public class Order
    {
        public string Id { get; set; }
        public string OrderId { get; set; }
        public string Name { get; set; }
        public string Oco { get; set; }
        public OrderState OrderState { get; set; }
        public OrderType OrderType { get; set; }
        public int Quantity { get; set; }
        public int Filled { get; set; }
        public Instrument Instrument { get; set; }
        public OrderAction OrderAction { get; set; }
        public double LimitPrice { get; set; }
        public double StopPrice { get; set; }
        // Required by TradeCopierEngine.OnExecution when mirroring the leader's TIF.
        public TimeInForce TimeInForce { get; set; } = TimeInForce.Day;
    }

    public class Position
    {
        public Instrument Instrument { get; set; }
        public MarketPosition MarketPosition { get; set; }
        public int Quantity { get; set; }
        public double AveragePrice { get; set; }
        public double UnrealizedPnL { get; set; }
        public double GetUnrealizedProfitLoss(PerformanceUnit unit) => UnrealizedPnL;
    }

    public class Execution
    {
        public Instrument Instrument { get; set; }
        public Order Order { get; set; }
        public int Quantity { get; set; }
        public double Price { get; set; }
        // Required by TradeCopierEngine.OnExecution (recursion guard + dedupe).
        public Account Account { get; set; }
        public string ExecutionId { get; set; }
        public string Name { get; set; }
        // P1-22: the copier measures latency as leader exec.Time -> follower exec.Time. Left
        // default here so tests that do not care still exercise the wall-clock fallback.
        public DateTime Time { get; set; }
        // P2-147. The real NT8 Execution carries a MarketPosition independent of its Order (it is
        // what ExtractTrades reads, and it is populated live). The stub omitted it until a test
        // needed to prove the null-Order drop captures it -- [[test-doubles-are-not-evidence]], the
        // stub should model the fields the code reads.
        public MarketPosition MarketPosition { get; set; }
    }

    public class Account
    {
        public string Name { get; set; }

        // Defaults to a LIVE provider on purpose. A test that forgets to say it is
        // simulated gets the strict treatment, which is the same fail-closed posture
        // the production gate now takes. Defaulting to Simulator would reproduce the
        // exact bug P1-20 fixes -- assuming safety instead of establishing it.
        public Provider Provider { get; set; } = Provider.NinjaTrader;
        public Dictionary<AccountItem, double> Values { get; set; } = new Dictionary<AccountItem, double>();
        public List<Order> Orders { get; set; } = new List<Order>();
        public List<Position> Positions { get; set; } = new List<Position>();
        public static List<Account> All { get; set; } = new List<Account>();
        public bool SimulateExitRejection { get; set; }

        // Broker rejection of the auto-stop at Submit time. This is the failure T2's
        // rollback exists for: the FSM has already been moved to ProtectedPending
        // (reserve-before-submit), so if the submit throws and nothing rolls it back,
        // the position is unprotected while the FSM claims otherwise.
        public bool SimulateSubmitFailure { get; set; }
        // Broker refuses the flatten. This is the case P1-11 turns on: if the protective stop
        // was already cancelled on the way in, a failed flatten leaves an open position with
        // nothing behind it.
        public bool SimulateFlattenFailure { get; set; }
        // Broker refuses an in-place modification. The bracket sync prefers Change() and falls
        // back to cancel-then-create; that fallback is the only path that can retire an OCO
        // group and so the only one that needs a fresh id (P0-9 item 1). Nothing could reach it
        // before this switch existed.
        public bool SimulateChangeFailure { get; set; }
        // Counts Flatten calls so a test can prove the fail-closed fallback ran.
        public int FlattenCallCount { get; private set; }

        // P0-63. The broker ACCEPTS the change and then silently ignores it. Distinct from
        // SimulateChangeFailure above in the only way that matters: no exception, no rejection,
        // no log line -- the order settles back at the values it already had. This is what
        // `provider: Simulator` does to every Account.Change(), which is why the mirrored stop
        // has never trailed once.
        //
        // This stub could not express that until 2026-08-13, and that is the whole reason a
        // 926-test suite never saw the defect. `Account.Change()` is a REQUEST: the caller writes
        // the desired values onto the Order object and Change() asks the provider to honour them.
        // The stub had no provider-side copy of those fields, so the caller's own writes were the
        // only thing any test could read back and every Change() "worked" by construction.
        // Same lesson as the six OrderStates this stub used to omit -- a double that cannot
        // represent the failure is not coverage.
        public bool SimulateChangeIsSilentNoOp { get; set; }

        // P0-62 / P1-70. The provider honours the PRICE and refuses the QUANTITY -- established by
        // a live trade on 2026-08-10: one Change() carried `2@29742.5` and the order went
        // `1@29743.5` -> `1@29742.5`. So a protective leg cannot be GROWN by modification.
        //
        // This third case is the one the stub could not express even after SimulateChangeIsSilentNoOp
        // was added, and its absence was recorded as an open suite gap in mutation/mutate_p0_63.py
        // ("a SimulateChangeAppliesQuantityOnly stub flag for the partial-honour case"). It matters
        // beyond P0-62: a partial honour settles AWAY from the original values, so the no-op detector
        // correctly does not fire -- which makes it the one path where "the change took" and "the
        // change took what I asked for" come apart, and therefore the only way a confirmation line
        // can be honestly wrong.
        public bool SimulateChangeSettlesOneTickAway { get; set; }

        /// <summary>Tick the partial-honour simulation shifts the settled price by.</summary>
        public double SimulateSettleTickSize { get; set; } = 0.25;

        /// <summary>The provider's copy of the mutable order fields, which is the authoritative one.</summary>
        private class ProviderHeld
        {
            public double StopPrice;
            public double LimitPrice;
            public int Quantity;
        }

        // Reference-keyed: the stub Order does not override equality, so this is object identity
        // by construction. Keying on OrderId would reproduce P0-59/P3-30 inside the harness.
        private readonly Dictionary<Order, ProviderHeld> _providerHeld =
            new Dictionary<Order, ProviderHeld>();
        private readonly HashSet<Order> _unhonouredChanges = new HashSet<Order>();

        private void CaptureProviderValues(Order o)
        {
            _providerHeld[o] = new ProviderHeld
            {
                StopPrice = o.StopPrice, LimitPrice = o.LimitPrice, Quantity = o.Quantity
            };
        }

        /// <summary>
        /// What price the broker would actually TRIGGER this order at -- the provider's copy, not
        /// the caller's request. This is the only honest question to assert on: `order.StopPrice`
        /// is whatever we last wrote onto the object, so reading it back proves nothing about
        /// whether the broker agreed. Asserting on it is what would have made a P0-63 test pass
        /// while the live stop sat unmoved.
        /// </summary>
        public double ProviderStopPrice(Order o)
        {
            lock (_ordersLock)
            {
                ProviderHeld held;
                return _providerHeld.TryGetValue(o, out held) ? held.StopPrice : double.NaN;
            }
        }

        /// <summary>As <see cref="ProviderStopPrice"/>, for the target leg's limit price.</summary>
        public double ProviderLimitPrice(Order o)
        {
            lock (_ordersLock)
            {
                ProviderHeld held;
                return _providerHeld.TryGetValue(o, out held) ? held.LimitPrice : double.NaN;
            }
        }

        /// <summary>
        /// The change round trip completing. NT8 raises OrderUpdate when an order leaves
        /// ChangeSubmitted/ChangePending, carrying whatever the PROVIDER holds -- which on a
        /// Simulator account is the pre-change values.
        ///
        /// The revert is deliberately applied HERE and not inside Change(). If Change() reverted
        /// synchronously, a fix that read the order back on the line after Change() would pass
        /// this suite and still fail live, because live the revert has not happened yet at that
        /// point. Verification has to hang off the settle event, so the double has to make the
        /// synchronous shortcut fail.
        ///
        /// THIS BEHAVIOUR IS NOT ASSUMED. It is copied from a live NT8 trace on a follower
        /// scaling 1 -> 2 lots, recorded in RiskGuardAddOn.AcceptsModification's docstring and
        /// the basis of P0-61:
        ///
        ///     34412 ChangeSubmitted  qty 1 @ 29822.25   (first change in flight)
        ///     34412 ChangePending    qty 2 @ 29822.5    (our second change)
        ///     34412 Working          qty 1 @ 29822.25   (reverted -- BOTH changes lost)
        ///
        /// Read the third line: on settling to `Working` the ORDER OBJECT ITSELF read back the
        /// ORIGINAL quantity and price. NT8 owns those fields and restores them; a local write
        /// followed by an ignored Change() does not survive the round trip. P0-63's probe table
        /// says the same thing three more times ("asked qty 1 -> 2, result qty 1"), as does stop
        /// 34410, which was created at 29753.5, logged `stop moved to 1@29754.5`, and *ended at
        /// 29753.5*.
        ///
        /// Recorded at this length because the 2026-08-13 review panel and arbiter concluded the
        /// opposite -- that NT8 leaves the desired values on the object, so no read-back could
        /// ever detect a no-op -- and escalated the ticket on it. That conclusion is refuted by
        /// the trace above. If you are about to raise it again, produce a live trace first.
        /// </summary>
        public void SettleChange(Order o)
        {
            lock (_ordersLock)
            {
                ProviderHeld held;
                if (_unhonouredChanges.Remove(o) && _providerHeld.TryGetValue(o, out held))
                {
                    o.StopPrice = held.StopPrice;
                    o.LimitPrice = held.LimitPrice;
                    o.Quantity = held.Quantity;
                }
            }
            o.OrderState = OrderState.Working;
            TriggerOrderUpdate(o);
        }

        /// <summary>
        /// Fires on every call that reaches the broker (Cancel/Flatten/CreateOrder/Submit).
        /// Lets a test assert the invariant the design doc claims but the code did not keep:
        /// none of these may run while `_stateLock` is held (P1-10, P1-35). Reviewers cannot
        /// check this reliably by reading -- the offending sites are nested three calls deep
        /// inside a lock block -- so it is checked mechanically instead.
        /// </summary>
        public static Action<string> BrokerCallObserver;

        private static void ObserveBrokerCall(string method)
        {
            var obs = BrokerCallObserver;
            if (obs != null) obs(method);
        }

        public event EventHandler<PositionEventArgs> PositionUpdate;
        public event EventHandler<OrderEventArgs> OrderUpdate;
        public event EventHandler<ExecutionEventArgs> ExecutionUpdate;
        public event EventHandler<AccountItemEventArgs> AccountItemUpdate;

        public double Get(AccountItem item, Currency currency)
        {
            return Values.ContainsKey(item) ? Values[item] : 0.0;
        }

        public void Cancel(Order[] orders)
        {
            ObserveBrokerCall("Cancel");
            foreach (var o in orders)
            {
                o.OrderState = OrderState.Cancelled;
            }
        }

        public void Cancel(List<Order> orders)
        {
            ObserveBrokerCall("Cancel");
            foreach (var o in orders)
            {
                o.OrderState = OrderState.Cancelled;
            }
        }

        // P1-19: records exactly which instruments each Flatten call was asked to close.
        // The defect is in what ExecuteAction *requests* -- it ignored action.Instrument and
        // passed every instrument on the account -- so the request is the thing to assert on.
        public List<string> LastFlattenRequest = new List<string>();

        public void Flatten(Instrument[] instruments)
        {
            ObserveBrokerCall("Flatten");
            LastFlattenRequest = instruments == null
                ? new List<string>()
                : instruments.Where(i => i != null).Select(i => i.FullName).ToList();
            FlattenCallCount++;
            if (SimulateFlattenFailure)
                throw new Exception("Simulated broker rejection at Flatten.");
            Positions.Clear();
            Orders.Clear();
        }

        public Order CreateOrder(Instrument instrument, OrderAction action, OrderType type, TimeInForce tif, int qty, double limit, double stop, string oco, string name, object custom)
        {
            ObserveBrokerCall("CreateOrder");
            var o = new Order
            {
                Id = Guid.NewGuid().ToString(),
                OrderId = Guid.NewGuid().ToString(),
                Name = name,
                Oco = oco,
                OrderState = OrderState.Initialized,
                OrderType = type,
                Quantity = qty,
                Instrument = instrument,
                OrderAction = action,
                LimitPrice = limit,
                StopPrice = stop
            };
            return o;
        }

        // S7 drives copies from several threads at once. NT8 manages Account.Orders internally;
        // an unsynchronised List<T> here would corrupt or throw under that burst and the test
        // would be measuring the stub, not the engine.
        private readonly object _ordersLock = new object();

        public void Submit(Order[] orders)
        {
            ObserveBrokerCall("Submit");
            if (SimulateSubmitFailure)
                throw new Exception("Simulated broker rejection at Submit.");

            foreach (var o in orders)
            {
                o.OrderState = OrderState.Submitted;
                if (SimulateExitRejection && (o.Name.StartsWith("Stop_") || o.Name.StartsWith("Target_")))
                    o.OrderState = OrderState.Rejected;
                // What the provider now holds. A later Change() is measured against this.
                lock (_ordersLock) { Orders.Add(o); CaptureProviderValues(o); }
            }
        }

        /// <summary>Snapshot of Orders safe to enumerate while other threads are submitting.</summary>
        public List<Order> OrdersSnapshot()
        {
            lock (_ordersLock) { return new List<Order>(Orders); }
        }

        // Change() is a broker call like Cancel/Flatten/Submit and must be observed as one, or
        // the P1-10 lock-scope check silently exempts it -- the same shape of blind spot that let
        // P1-43's four `account.Cancel` calls sit under the lock unnoticed.
        public void Change(Order[] orders)
        {
            ObserveBrokerCall("Change");
            if (SimulateChangeFailure)
                throw new Exception("Simulated broker rejection at Change.");
            foreach (var o in orders)
            {
                lock (_ordersLock)
                {
                    // The caller's desired values are LEFT IN PLACE either way -- that is what
                    // makes a read-back on the next line indistinguishable between the two cases,
                    // and it is exactly the trap P0-63 set live. Only SettleChange tells them
                    // apart, because only settling asks the provider what it actually holds.
                    if (SimulateChangeIsSilentNoOp) _unhonouredChanges.Add(o);
                    else if (SimulateChangeSettlesOneTickAway)
                    {
                        // The provider MOVES the order but not to the requested price -- a tick-
                        // boundary rounding, which is ordinary broker behaviour. The point is the
                        // resulting state: it differs from the original (so the no-op detector
                        // correctly stays quiet) AND from the request (so "it moved" and "it moved
                        // to what I asked" come apart). That is the only condition under which a
                        // confirmation line can be honestly wrong.
                        CaptureProviderValues(o);
                        if (_providerHeld[o].StopPrice > 0)
                            _providerHeld[o].StopPrice -= SimulateSettleTickSize;
                        if (_providerHeld[o].LimitPrice > 0)
                            _providerHeld[o].LimitPrice -= SimulateSettleTickSize;
                        _unhonouredChanges.Add(o);
                    }
                    else CaptureProviderValues(o);
                }
                o.OrderState = OrderState.Working;
            }
        }

        /// <summary>
        /// Fills `o` and retires the rest of its OCO group, which is what "one cancels the other"
        /// means and is the single OCO behaviour we depend on. Modelled here because the copier's
        /// re-submission logic has to tell "my protective leg was lost" from "my protective leg
        /// was retired because its sibling filled" -- and re-submitting in the second case places
        /// an order against a position that has just been closed, which is P0-50's orphan
        /// arriving by the route the pairing itself opens.
        ///
        /// Deliberately NOT modelled: whether cancelling one leg retires the group. That is
        /// plausible and unverified, so the copier is written to be correct either way rather
        /// than to match a guess encoded here.
        /// </summary>
        public void FillOrderAndRetireOcoGroup(Order o)
        {
            o.OrderState = OrderState.Filled;

            List<Order> siblings;
            lock (_ordersLock)
            {
                siblings = string.IsNullOrEmpty(o.Oco)
                    ? new List<Order>()
                    : Orders.Where(x => x != null && !ReferenceEquals(x, o)
                        && string.Equals(x.Oco, o.Oco, StringComparison.Ordinal)
                        && x.OrderState != OrderState.Filled
                        && x.OrderState != OrderState.Cancelled
                        && x.OrderState != OrderState.Rejected).ToList();
            }

            foreach (var s in siblings) s.OrderState = OrderState.Cancelled;

            TriggerOrderUpdate(o);
            foreach (var s in siblings) TriggerOrderUpdate(s);
        }

        public void TriggerPositionUpdate(Position p)
        {
            PositionUpdate?.Invoke(this, new PositionEventArgs { Position = p });
        }

        public void TriggerOrderUpdate(Order o)
        {
            OrderUpdate?.Invoke(this, new OrderEventArgs { Order = o });
        }

        public void TriggerExecutionUpdate(Execution ex)
        {
            ExecutionUpdate?.Invoke(this, new ExecutionEventArgs { Execution = ex });
        }

        /// <summary>
        /// How many handlers are attached to ExecutionUpdate. P1-21's subscribe pass now runs on
        /// every connection change, so "attached exactly once" is the invariant that stops a
        /// flapping broker from copying each fill N times. Asserted directly rather than through
        /// order counts, because OnExecution's ExecutionId dedupe would mask a doubled handler
        /// and the test would pass while proving nothing.
        /// </summary>
        public int ExecutionUpdateHandlerCount
        {
            get
            {
                var d = ExecutionUpdate;
                return d == null ? 0 : d.GetInvocationList().Length;
            }
        }

        public void TriggerAccountItemUpdate(AccountItem item, double value)
        {
            AccountItemUpdate?.Invoke(this, new AccountItemEventArgs { AccountItem = item, Value = value, Currency = Currency.UsDollar });
        }
    }

    public class Connection
    {
        public static event EventHandler<ConnectionStatusEventArgs> ConnectionStatusUpdate;
        public static void TriggerConnectionStatusUpdate(ConnectionStatusEventArgs e)
        {
            ConnectionStatusUpdate?.Invoke(null, e);
        }
    }

    public class ConnectionStatusEventArgs : EventArgs
    {
        public object Status { get; set; }
        public dynamic Connection { get; set; }
    }

    public class PositionEventArgs : EventArgs
    {
        public Position Position { get; set; }
    }

    public class OrderEventArgs : EventArgs
    {
        public Order Order { get; set; }
    }

    public class ExecutionEventArgs : EventArgs
    {
        public Execution Execution { get; set; }
    }
}

namespace NinjaTrader.Core
{
    public static class Globals
    {
        public static string UserDataDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "MockUserData");
    }
}

namespace NinjaTrader.Code
{
    public enum PrintTo { OutputTab1 }
    public static class Output
    {
        public static void Process(string msg, PrintTo tab)
        {
            Console.WriteLine("[OUTPUT] " + msg);
        }
    }
}

namespace NinjaTrader.NinjaScript
{
    public enum State
    {
        SetDefaults,
        Configure,
        Terminated
    }

    public class AddOnBase
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public State State { get; set; }
        protected virtual void OnStateChange() {}
    }
}

namespace NinjaTrader.Data
{
    public class BarsPeriod
    {
        public BarsPeriodType BarsPeriodType { get; set; }
        public int Value { get; set; }
    }
    public enum BarsPeriodType { Minute, Day, Hour }

    public enum ErrorCode { NoError, GeneralError, NotImplemented, DataNotAvailable }

    public class Bars
    {
        public int Count { get; set; }
        private readonly double[] _high;
        private readonly double[] _low;
        private readonly double[] _close;
        private readonly double[] _open;
        private readonly long[] _volume;
        private readonly DateTime[] _time;

        public Bars(double[] high, double[] low, double[] close, double[] open, long[] volume, DateTime[] time)
        {
            _high = high; _low = low; _close = close; _open = open; _volume = volume; _time = time;
            Count = close != null ? close.Length : 0;
        }

        public double GetHigh(int idx) => _high[idx];
        public double GetLow(int idx) => _low[idx];
        public double GetClose(int idx) => _close[idx];
        public double GetOpen(int idx) => _open[idx];
        public long GetVolume(int idx) => _volume[idx];
        public DateTime GetTime(int idx) => _time[idx];
    }

    public class BarsRequest : IDisposable
    {
        public Instrument Instrument { get; }
        public int Count { get; }
        public BarsPeriod BarsPeriod { get; set; }
        public Bars Bars { get; set; }
        public Action<BarsRequest, ErrorCode, string> Callback { get; set; }

        public BarsRequest(Instrument instrument, int count)
        {
            Instrument = instrument;
            Count = count;
        }

        public void Request(Action<BarsRequest, ErrorCode, string> callback)
        {
            Callback = callback;
            if (TestBarsFactory != null)
            {
                Bars = TestBarsFactory(this);
            }
            callback(this, Bars != null ? ErrorCode.NoError : ErrorCode.GeneralError, Bars != null ? null : "No test bars supplied");
        }

        public void Dispose() { }

        public static Func<BarsRequest, Bars> TestBarsFactory { get; set; }
    }
}

namespace NinjaTrader.Cbi
{
    public enum ConnectionStatus { Connected, Disconnected, Connecting, ConnectionLost }
}

#endif
