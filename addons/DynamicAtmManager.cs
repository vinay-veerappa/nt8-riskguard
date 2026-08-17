using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Code;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;

namespace NinjaTrader.NinjaScript.AddOns
{
    public enum AtmStrategyType
    {
        FixedTicks,
        AtrAdaptive,
        SwingPoint,
        DrawdownShield,
        ScaledRunner,
        VolatilityScaled,
        SessionAdaptive,
        KellyOptimal
    }

    public class AtmInstrumentProfile
    {
        public string Symbol { get; set; }
        public double TickSize { get; set; }
        public double PointValue { get; set; }
        public double DefaultATR { get; set; }
        public AtmStrategyType DefaultStrategy { get; set; }
        public int MaxContracts { get; set; }
        public double RiskPerTradePct { get; set; }
        public double RthMultiplier { get; set; }
        public double EthMultiplier { get; set; }
    }

    public class AtmStrategyConfig
    {
        public string Name { get; set; } = "PropFirm_Standard";
        public AtmStrategyType Type { get; set; } = AtmStrategyType.DrawdownShield;
        public int StopTicks { get; set; }
        public int TargetTicks { get; set; }
        public double AtrMultiplierSL { get; set; } = 1.5;
        public double AtrMultiplierTP { get; set; } = 2.5;
        public int AtrPeriod { get; set; } = 14;
        public int SwingLookbackBars { get; set; } = 5;
        public int SwingBufferTicks { get; set; } = 4;
        public int BreakevenTriggerTicks { get; set; } = 12;
        public int BreakevenOffsetTicks { get; set; } = 2;
        public double PartialProfitPct { get; set; } = 0.50;
        public double TrailMultiplier { get; set; } = 2.0;
        public double RiskPerTrade { get; set; } = 200.0;
        public double KellyFraction { get; set; } = 0.25;
        public double WinRate { get; set; } = 0.55;
        public double AvgRR { get; set; } = 2.0;
    }

    public class ActiveBracket
    {
        public string BracketId { get; set; }
        public string Symbol { get; set; }
        public string AccountName { get; set; }
        public bool IsLong { get; set; }
        public double EntryPrice { get; set; }
        public int Quantity { get; set; }
        public AtmStrategyConfig Config { get; set; }
        public string OcoId { get; set; }
        // ⚠️ P1-133: REPORTING FIELDS ONLY. These hold the id NT8 assigned at SUBMISSION, and the
        // broker replaces `Order.OrderId` with its own the moment it accepts -- so after that
        // instant these three strings match nothing on any real connection. They are kept because
        // the bridge's API payload returns them. NEVER feed one to a lookup: use
        // `AtmOrderIdentity.FindLiveByName(account, AtmOrderIdentity.StopName(BracketId))`.
        // Keying on these is what made breakeven and trailing work on `Sim101` and nowhere else.
        public string EntryOrderId { get; set; }
        public string StopOrderId { get; set; }
        public string TargetOrderId { get; set; }
        public double CurrentStopPrice { get; set; }
        public double CurrentTargetPrice { get; set; }
        public bool BreakevenTriggered { get; set; }

        // P0-67. `CurrentStopPrice` used to be written by the CALLER, unconditionally, immediately
        // after asking the broker to move the stop:
        //
        //     ModifyStopPrice(account, bracket.StopOrderId, newStop);
        //     bracket.CurrentStopPrice = newStop;      // <-- whether or not the broker agreed
        //
        // `Account.Change()` is a REQUEST, and on `provider: Simulator` it is accepted and silently
        // discarded (P0-63, confirmed live 2026-08-13). So the cache recorded a price the broker had
        // refused, and every later comparison -- `newStop > bracket.CurrentStopPrice` -- was made
        // against fiction. The trail then LATCHED: the cache said the stop was already at the better
        // price, so no further move was ever attempted.
        //
        // The fix is structural rather than a check bolted on: `CurrentStopPrice` is now only ever
        // assigned FROM THE LIVE ORDER, on the next sweep. A polling monitor does not need settle
        // events -- it needs to stop believing its own writes.
        //
        // NaN means "no move outstanding". Set when a request is issued, cleared when the sweep sees
        // what the broker did with it.
        public double RequestedStopPrice { get; set; } = double.NaN;

        // Bounded, because the retry is what makes a refused move recoverable, and an unbounded
        // retry against a provider that always refuses is an order flood.
        public int StopModifyAttempts { get; set; }

        // P2-134. The give-up line is said ONCE per episode; this records that it has been said.
        //
        // ⚠️ There is NO clear anywhere, and that is the finding rather than an omission. The
        // first draft cleared it from a SETTER on StopModifyAttempts, which fires on any
        // assignment of 0 -- and `ActiveBracket` is serialised into the bridge's API payload, so a
        // deserialiser writing the default would silently re-arm the announcement with nothing
        // having recovered. Asking instead where the CONDITION resolves (P2-107) gives the real
        // answer: it never does. Past MaxStopModifyAttempts `RequestStopMove` returns before it
        // asks, a confirm needs an outstanding request, and the counter is reset only on a
        // confirm. Abandonment is permanent for a bracket -- which is what "not asking again for
        // this bracket" says -- so the episode boundary is the BRACKET, and a clear would be a
        // line that can never run, reading as a release valve that works.
        public bool StopMoveAbandonAnnounced { get; set; }

        // P2-134. What was actually OBSERVED the last time a stop move failed. The abandon line
        // used to assert "refused by the provider" for every failure, and this counter is spent by
        // two different ones -- ModifyStopPrice never asking (no live order) and the provider
        // declining a move that WAS sent. Name the observed reason; do not infer a cause.
        public string LastStopMoveFailureReason { get; set; }
        public bool PartialProfitTaken { get; set; }
        public DateTime CreatedAt { get; set; }
        public bool IsComplete { get; set; }
    }

    public class BracketResult
    {
        public string Status { get; set; }
        public string BracketId { get; set; }
        public string OcoId { get; set; }
        public string EntryOrderId { get; set; }
        public string StopOrderId { get; set; }
        public string TargetOrderId { get; set; }
        public double StopPrice { get; set; }
        public double TargetPrice { get; set; }
        public int CalculatedQuantity { get; set; }
        public string StrategyName { get; set; }
        public string Note { get; set; }
        public string Error { get; set; }
    }

    internal class BarData
    {
        public double[] High { get; set; }
        public double[] Low { get; set; }
        public double[] Close { get; set; }
        public double[] Open { get; set; }
        public long[] Volume { get; set; }
        public DateTime[] Time { get; set; }
        public int Count { get; set; }
    }

    public class DynamicAtmManager
    {
        private static readonly Lazy<DynamicAtmManager> _instance = new Lazy<DynamicAtmManager>(() => new DynamicAtmManager());
        public static DynamicAtmManager Instance { get { return _instance.Value; } }

        private readonly Dictionary<string, ActiveBracket> _activeBrackets;
        private readonly object _bracketLock;
        private Timer _monitorTimer;
        private bool _monitoring;

        private static readonly Dictionary<string, AtmInstrumentProfile> _profiles;
        private static readonly object _profileLock = new object();

        static DynamicAtmManager()
        {
            _profiles = new Dictionary<string, AtmInstrumentProfile>(StringComparer.OrdinalIgnoreCase)
            {
                { "ES", new AtmInstrumentProfile { Symbol = "ES", TickSize = 0.25, PointValue = 50.0, DefaultATR = 8.0, DefaultStrategy = AtmStrategyType.SwingPoint, MaxContracts = 20, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.5 } },
                { "NQ", new AtmInstrumentProfile { Symbol = "NQ", TickSize = 0.25, PointValue = 20.0, DefaultATR = 30.0, DefaultStrategy = AtmStrategyType.AtrAdaptive, MaxContracts = 10, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 2.0 } },
                { "MES", new AtmInstrumentProfile { Symbol = "MES", TickSize = 0.25, PointValue = 5.0, DefaultATR = 8.0, DefaultStrategy = AtmStrategyType.SwingPoint, MaxContracts = 50, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.5 } },
                { "MNQ", new AtmInstrumentProfile { Symbol = "MNQ", TickSize = 0.25, PointValue = 2.0, DefaultATR = 30.0, DefaultStrategy = AtmStrategyType.AtrAdaptive, MaxContracts = 50, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 2.0 } },
                { "CL", new AtmInstrumentProfile { Symbol = "CL", TickSize = 0.01, PointValue = 1000.0, DefaultATR = 0.80, DefaultStrategy = AtmStrategyType.AtrAdaptive, MaxContracts = 5, RiskPerTradePct = 0.005, RthMultiplier = 1.0, EthMultiplier = 1.0 } },
                { "GC", new AtmInstrumentProfile { Symbol = "GC", TickSize = 0.1, PointValue = 100.0, DefaultATR = 12.0, DefaultStrategy = AtmStrategyType.FixedTicks, MaxContracts = 10, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.2 } },
                { "RTY", new AtmInstrumentProfile { Symbol = "RTY", TickSize = 0.1, PointValue = 50.0, DefaultATR = 20.0, DefaultStrategy = AtmStrategyType.AtrAdaptive, MaxContracts = 10, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.5 } },
                { "M2K", new AtmInstrumentProfile { Symbol = "M2K", TickSize = 0.1, PointValue = 5.0, DefaultATR = 20.0, DefaultStrategy = AtmStrategyType.AtrAdaptive, MaxContracts = 50, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.5 } },
                { "YM", new AtmInstrumentProfile { Symbol = "YM", TickSize = 1.0, PointValue = 5.0, DefaultATR = 150.0, DefaultStrategy = AtmStrategyType.FixedTicks, MaxContracts = 10, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.3 } },
                { "MYM", new AtmInstrumentProfile { Symbol = "MYM", TickSize = 1.0, PointValue = 0.5, DefaultATR = 150.0, DefaultStrategy = AtmStrategyType.FixedTicks, MaxContracts = 50, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.3 } },
                { "ZB", new AtmInstrumentProfile { Symbol = "ZB", TickSize = 0.03125, PointValue = 31.25, DefaultATR = 0.5, DefaultStrategy = AtmStrategyType.FixedTicks, MaxContracts = 10, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.0 } },
                { "ZN", new AtmInstrumentProfile { Symbol = "ZN", TickSize = 0.015625, PointValue = 15.625, DefaultATR = 0.3, DefaultStrategy = AtmStrategyType.FixedTicks, MaxContracts = 10, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.0 } },
                { "6E", new AtmInstrumentProfile { Symbol = "6E", TickSize = 0.00005, PointValue = 6.25, DefaultATR = 0.002, DefaultStrategy = AtmStrategyType.FixedTicks, MaxContracts = 10, RiskPerTradePct = 0.01, RthMultiplier = 1.0, EthMultiplier = 1.0 } }
            };
        }

        public DynamicAtmManager()
        {
            _activeBrackets = new Dictionary<string, ActiveBracket>();
            _bracketLock = new object();
        }

        public static AtmInstrumentProfile GetProfile(string rootSymbol)
        {
            AtmInstrumentProfile profile;
            lock (_profileLock)
            {
                if (_profiles.TryGetValue(rootSymbol, out profile))
                    return profile;
            }
            return null;
        }

        public static void RegisterProfile(AtmInstrumentProfile profile)
        {
            lock (_profileLock)
            {
                _profiles[profile.Symbol] = profile;
            }
        }

        public BracketResult PlaceBracket(
            Account account,
            Instrument instrument,
            string actionStr,
            int quantity,
            AtmStrategyConfig config,
            double currentPrice,
            double tickSize,
            double pointValue)
        {
            var result = new BracketResult();
            bool isLong = actionStr.Equals("buy", StringComparison.OrdinalIgnoreCase);
            string symbol = instrument.MasterInstrument.Name;

            AtmInstrumentProfile profile = GetProfile(symbol);
            if (profile == null)
            {
                profile = new AtmInstrumentProfile
                {
                    Symbol = symbol,
                    TickSize = tickSize,
                    PointValue = pointValue,
                    DefaultATR = 10.0 * tickSize,
                    DefaultStrategy = AtmStrategyType.FixedTicks,
                    MaxContracts = 10,
                    RiskPerTradePct = 0.01,
                    RthMultiplier = 1.0,
                    EthMultiplier = 1.0
                };
            }

            double stopPrice = 0;
            double targetPrice = 0;
            int calculatedQty = quantity;

            switch (config.Type)
            {
                case AtmStrategyType.FixedTicks:
                {
                    int stopTicks = config.StopTicks > 0 ? config.StopTicks : 8;
                    int targetTicks = config.TargetTicks > 0 ? config.TargetTicks : 16;
                    stopPrice = isLong ? (currentPrice - stopTicks * tickSize) : (currentPrice + stopTicks * tickSize);
                    targetPrice = isLong ? (currentPrice + targetTicks * tickSize) : (currentPrice - targetTicks * tickSize);
                    result.StrategyName = "FixedTicks";
                    break;
                }

                case AtmStrategyType.AtrAdaptive:
                {
                    double atr = GetATR(instrument, config.AtrPeriod);
                    if (atr <= 0) atr = profile.DefaultATR * tickSize;
                    double slDist = atr * config.AtrMultiplierSL;
                    double tpDist = atr * config.AtrMultiplierTP;
                    stopPrice = isLong ? (currentPrice - slDist) : (currentPrice + slDist);
                    targetPrice = isLong ? (currentPrice + tpDist) : (currentPrice - tpDist);
                    result.StrategyName = "AtrAdaptive";
                    break;
                }

                case AtmStrategyType.SwingPoint:
                {
                    double swing = FindSwingPoint(instrument, isLong, config.SwingLookbackBars);
                    if (swing > 0)
                    {
                        double buffer = config.SwingBufferTicks * tickSize;
                        stopPrice = isLong ? (swing - buffer) : (swing + buffer);
                    }
                    else
                    {
                        int fallbackTicks = 10;
                        stopPrice = isLong ? (currentPrice - fallbackTicks * tickSize) : (currentPrice + fallbackTicks * tickSize);
                    }
                    targetPrice = isLong
                        ? (currentPrice + (currentPrice - stopPrice) * 2.0)
                        : (currentPrice - (stopPrice - currentPrice) * 2.0);
                    result.StrategyName = "SwingPoint";
                    break;
                }

                case AtmStrategyType.DrawdownShield:
                {
                    int stopTicks = config.StopTicks > 0 ? config.StopTicks : 10;
                    int targetTicks = config.TargetTicks > 0 ? config.TargetTicks : 20;
                    stopPrice = isLong ? (currentPrice - stopTicks * tickSize) : (currentPrice + stopTicks * tickSize);
                    targetPrice = isLong ? (currentPrice + targetTicks * tickSize) : (currentPrice - targetTicks * tickSize);
                    result.StrategyName = "DrawdownShield";
                    break;
                }

                case AtmStrategyType.ScaledRunner:
                {
                    int stopTicks = config.StopTicks > 0 ? config.StopTicks : 8;
                    int targetTicks = config.TargetTicks > 0 ? config.TargetTicks : 30;
                    stopPrice = isLong ? (currentPrice - stopTicks * tickSize) : (currentPrice + stopTicks * tickSize);
                    targetPrice = isLong ? (currentPrice + targetTicks * tickSize) : (currentPrice - targetTicks * tickSize);
                    result.StrategyName = "ScaledRunner";
                    break;
                }

                case AtmStrategyType.VolatilityScaled:
                {
                    double atr = GetATR(instrument, config.AtrPeriod);
                    if (atr <= 0) atr = profile.DefaultATR * tickSize;
                    double riskPerContract = atr * config.AtrMultiplierSL * pointValue;
                    if (riskPerContract > 0)
                    {
                        calculatedQty = (int)Math.Floor(config.RiskPerTrade / riskPerContract);
                        if (calculatedQty < 1) calculatedQty = 1;
                        if (calculatedQty > profile.MaxContracts) calculatedQty = profile.MaxContracts;
                    }
                    double slDist = atr * config.AtrMultiplierSL;
                    double tpDist = atr * config.AtrMultiplierTP;
                    stopPrice = isLong ? (currentPrice - slDist) : (currentPrice + slDist);
                    targetPrice = isLong ? (currentPrice + tpDist) : (currentPrice - tpDist);
                    result.StrategyName = "VolatilityScaled";
                    break;
                }

                case AtmStrategyType.SessionAdaptive:
                {
                    bool isRTH = IsRTH(GetEasternTime());
                    double multiplier = isRTH ? profile.RthMultiplier : profile.EthMultiplier;
                    int baseStopTicks = config.StopTicks > 0 ? config.StopTicks : 8;
                    int baseTargetTicks = config.TargetTicks > 0 ? config.TargetTicks : 16;
                    int stopTicks = (int)Math.Round(baseStopTicks * multiplier);
                    int targetTicks = (int)Math.Round(baseTargetTicks * multiplier);
                    stopPrice = isLong ? (currentPrice - stopTicks * tickSize) : (currentPrice + stopTicks * tickSize);
                    targetPrice = isLong ? (currentPrice + targetTicks * tickSize) : (currentPrice - targetTicks * tickSize);
                    result.StrategyName = "SessionAdaptive";
                    break;
                }

                case AtmStrategyType.KellyOptimal:
                {
                    double kellyPct = config.KellyFraction * (config.WinRate - (1.0 - config.WinRate) / config.AvgRR);
                    if (kellyPct < 0) kellyPct = 0.01;
                    double atr = GetATR(instrument, config.AtrPeriod);
                    if (atr <= 0) atr = profile.DefaultATR * tickSize;
                    double riskPerContract = atr * config.AtrMultiplierSL * pointValue;
                    if (riskPerContract > 0)
                    {
                        calculatedQty = (int)Math.Floor((config.RiskPerTrade * kellyPct) / riskPerContract);
                        if (calculatedQty < 1) calculatedQty = 1;
                        if (calculatedQty > profile.MaxContracts) calculatedQty = profile.MaxContracts;
                    }
                    double slDist = atr * config.AtrMultiplierSL;
                    double tpDist = atr * config.AtrMultiplierTP;
                    stopPrice = isLong ? (currentPrice - slDist) : (currentPrice + slDist);
                    targetPrice = isLong ? (currentPrice + tpDist) : (currentPrice - tpDist);
                    result.StrategyName = "KellyOptimal";
                    break;
                }
            }

            if (stopPrice <= 0 || targetPrice <= 0)
            {
                result.Status = "error";
                result.Error = "Could not calculate stop/target prices";
                return result;
            }

            string ocoId = Guid.NewGuid().ToString();
            string bracketId = Guid.NewGuid().ToString().Substring(0, 8);
            string entryName = AtmOrderIdentity.EntryName(bracketId);

            var entryAction = isLong ? OrderAction.Buy : OrderAction.Sell;
            var exitAction = isLong ? OrderAction.Sell : OrderAction.Buy;

            try
            {
                var entryOrder = account.CreateOrder(instrument, entryAction, OrderType.Market, TimeInForce.Day, calculatedQty, 0, 0, string.Empty, entryName, null);
                if (entryOrder == null)
                {
                    result.Status = "error";
                    result.Error = "Failed to create entry order";
                    return result;
                }
                var stopOrder = account.CreateOrder(instrument, exitAction, OrderType.StopMarket, TimeInForce.Day, calculatedQty, 0, stopPrice, ocoId, AtmOrderIdentity.StopName(bracketId), null);
                var targetOrder = account.CreateOrder(instrument, exitAction, OrderType.Limit, TimeInForce.Day, calculatedQty, targetPrice, 0, ocoId, AtmOrderIdentity.TargetName(bracketId), null);

                var validOrders = new[] { entryOrder, stopOrder, targetOrder }
                    .Where(o => o != null && o.OrderState != OrderState.CancelPending && o.OrderState != OrderState.Cancelled)
                    .ToArray();

                if (validOrders.Length > 0)
                {
                    account.Submit(validOrders);
                }

                result.Status = "submitted";
                result.BracketId = bracketId;
                result.OcoId = ocoId;
                result.EntryOrderId = entryOrder.OrderId;
                result.StopOrderId = stopOrder != null ? stopOrder.OrderId : null;
                result.TargetOrderId = targetOrder != null ? targetOrder.OrderId : null;
                result.StopPrice = stopPrice;
                result.TargetPrice = targetPrice;
                result.CalculatedQuantity = calculatedQty;

                bool needsMonitor = (config.Type == AtmStrategyType.DrawdownShield || config.Type == AtmStrategyType.ScaledRunner);
                if (needsMonitor)
                {
                    var bracket = new ActiveBracket
                    {
                        BracketId = bracketId,
                        Symbol = symbol,
                        AccountName = account.Name,
                        IsLong = isLong,
                        EntryPrice = currentPrice,
                        Quantity = calculatedQty,
                        Config = config,
                        OcoId = ocoId,
                        EntryOrderId = entryOrder.OrderId,
                        StopOrderId = stopOrder != null ? stopOrder.OrderId : null,
                        TargetOrderId = targetOrder != null ? targetOrder.OrderId : null,
                        CurrentStopPrice = stopPrice,
                        CurrentTargetPrice = targetPrice,
                        BreakevenTriggered = false,
                        PartialProfitTaken = false,
                        CreatedAt = DateTime.UtcNow,
                        IsComplete = false
                    };
                    RegisterBracket(bracket);
                    EnsureMonitor();
                    result.Note = "Bracket registered for breakeven/trailing monitoring";
                }

                List<string> rejectedOrders = new List<string>();
                foreach (var o in new[] { stopOrder, targetOrder })
                {
                    if (o != null && (o.OrderState == OrderState.Rejected || o.OrderState == OrderState.Cancelled))
                        rejectedOrders.Add(o.Name + " state=" + o.OrderState);
                }
                if (rejectedOrders.Count > 0)
                {
                    result.Status = "partial_submit";
                    result.Note = (result.Note ?? "") + " Some exit orders rejected: " + string.Join(", ", rejectedOrders);
                }
            }
            catch (Exception ex)
            {
                result.Status = "error";
                result.Error = ex.Message;
            }

            return result;
        }

        public void RegisterBracket(ActiveBracket bracket)
        {
            lock (_bracketLock)
            {
                _activeBrackets[bracket.BracketId] = bracket;
            }
        }

        public void RemoveBracket(string bracketId)
        {
            lock (_bracketLock)
            {
                _activeBrackets.Remove(bracketId);
            }
        }

        public List<ActiveBracket> GetActiveBrackets()
        {
            lock (_bracketLock)
            {
                return _activeBrackets.Values.Where(b => !b.IsComplete).ToList();
            }
        }

        public object GetBracketStatus(string bracketId)
        {
            lock (_bracketLock)
            {
                ActiveBracket b;
                if (_activeBrackets.TryGetValue(bracketId, out b))
                {
                    return new
                    {
                        bracketId = b.BracketId,
                        symbol = b.Symbol,
                        account = b.AccountName,
                        isLong = b.IsLong,
                        entryPrice = b.EntryPrice,
                        quantity = b.Quantity,
                        strategy = b.Config != null ? b.Config.Type.ToString() : "Unknown",
                        currentStop = b.CurrentStopPrice,
                        currentTarget = b.CurrentTargetPrice,
                        breakevenTriggered = b.BreakevenTriggered,
                        partialProfitTaken = b.PartialProfitTaken,
                        isComplete = b.IsComplete,
                        ageSeconds = (DateTime.UtcNow - b.CreatedAt).TotalSeconds
                    };
                }
                return new { error = "bracket not found" };
            }
        }

        private void EnsureMonitor()
        {
            if (_monitoring) return;
            _monitoring = true;
            _monitorTimer = new Timer(MonitorTick, null, 5000, 5000);
        }

        /// <summary>
        /// P2-112. Takes ownership of `work` and returns TRUE if it will be run on the UI thread;
        /// returns FALSE if there is no dispatcher, in which case THE CALLER MUST RUN IT.
        ///
        /// The `#if` is deliberately this small. Before P2-112 the whole of MonitorTick was
        /// `#if TESTING MonitorTickCore(); #else <the dispatcher branch> #endif`, so the branch
        /// holding the defect existed in no test build at all and the ten ATM tests drove a body
        /// the shipped assembly does not contain -- P2-27's shape, at the loop that moves stops.
        /// Only the WPF lookup needs the platform, so only the WPF lookup is behind the directive;
        /// the control flow below is compiled into both builds and the tests drive both branches
        /// through this seam.
        ///
        /// `return false` here is NOT the fail-open shape TestP1_13_... bans. That shape is a bare
        /// `return;` that abandons the work. This returns to a caller that then does it.
        /// </summary>
#if TESTING
        internal Func<Action, bool> TryMarshal = _ => false;
#else
        internal Func<Action, bool> TryMarshal = work =>
        {
            var dispatcher = System.Windows.Application.Current?.Dispatcher;
            if (dispatcher == null) return false;
            dispatcher.InvokeAsync(() => work());
            return true;
        };
#endif

        // STATIC, because the message below says "once per session" and the condition really is
        // process-wide: there is one WPF application object, not one per manager. Instance scope
        // would make that claim true only by leaning on the Lazy<> singleton above -- an invariant
        // enforced somewhere else, which is how a log line starts describing something it did not
        // observe. Reset by reflection in the P2-112 tests; production never writes it twice.
        private static int _noDispatcherAnnounced;

        private void MonitorTick(object _)
        {
            try
            {
                // NT8 Account/Order/Position objects are NOT thread-safe, so the sweep goes to the
                // UI dispatcher whenever there is one. That path is unchanged by P2-112.
                if (TryMarshal(MonitorTickCore))
                    return;

                // P2-112. There is no dispatcher, and this used to `return`. That was P1-13's
                // fail-open verbatim at a subsystem P1-13 never inspected: the 5-second sweep
                // returned immediately FOREVER, so breakeven stops never moved, trailing never
                // advanced, refused moves were never even detected -- and nothing logged a word.
                //
                // There is nothing to marshal TO. `Application.Current == null` means the process
                // has no WPF application object and therefore no UI thread anywhere, so the choice
                // is between doing the sweep on this thread and not doing it. Not doing it is the
                // defect. Running here is safe in the way that matters: the race worth fearing is
                // with a UI-thread broker call, and on this path no UI thread exists to make one.
                //
                // ONCE. A line every 5 seconds for the life of the process is P2-108 verbatim, and
                // an alarm that is always on is off. The fallback is announced, not narrated.
                if (System.Threading.Interlocked.Exchange(ref _noDispatcherAnnounced, 1) == 0)
                {
                    RiskGuardAddOn.LogFromComponent("", "ATM_MONITOR_NO_DISPATCHER",
                        "Dynamic ATM monitor has no WPF dispatcher; the sweep will run on the timer thread. " +
                        "Breakeven and trailing stop moves will still be attempted, but NinjaTrader broker objects are not thread-safe. " +
                        "An unusual stop move failure may be related to this fallback. This message is logged once per session.");
                }

                MonitorTickCore();
            }
            catch (Exception ex)
            {
                try { NinjaTrader.Code.Output.Process("[AtmMonitor] Dispatcher error: " + ex.Message, PrintTo.OutputTab1); } catch { }
            }
        }

#if TESTING
        /// <summary>
        /// P0-67. Drives one sweep synchronously. Added because NOT ONE test drove `MonitorTickCore`
        /// before 2026-08-13 -- the ten existing ATM tests all exercise pure helpers
        /// (ShouldTriggerBreakeven, CalculateBreakevenStopPrice), so the loop holding the third
        /// `Account.Change()` call site had zero coverage and the defect was invisible to a
        /// 987-test suite. That is `P2-27`'s shape: the riskiest code was the least covered.
        /// </summary>
        internal void MonitorTickForTest() { MonitorTickCore(); }

        /// <summary>Registers a bracket without going through PlaceBracket's broker calls.</summary>
        internal void AddBracketForTest(ActiveBracket b)
        {
            lock (_bracketLock) { _activeBrackets[b.BracketId] = b; }
        }

        internal ActiveBracket GetBracketForTest(string id)
        {
            lock (_bracketLock)
            {
                ActiveBracket b;
                return _activeBrackets.TryGetValue(id, out b) ? b : null;
            }
        }
#endif

        private void MonitorTickCore()
        {
            List<ActiveBracket> toRemove = new List<ActiveBracket>();
            List<ActiveBracket> active;

            lock (_bracketLock)
            {
                active = _activeBrackets.Values.Where(b => !b.IsComplete).ToList();
            }

            foreach (var bracket in active)
            {
                try
                {
                    Account account = Account.All.FirstOrDefault(a => a.Name.Equals(bracket.AccountName, StringComparison.OrdinalIgnoreCase));
                    if (account == null)
                    {
                        toRemove.Add(bracket);
                        continue;
                    }

                    Position position = account.Positions.FirstOrDefault(p =>
                        p.Instrument.MasterInstrument.Name.Equals(bracket.Symbol, StringComparison.OrdinalIgnoreCase));

                    if (position == null || Math.Abs(position.Quantity) == 0)
                    {
                        bool entryStillWorking = account.Orders.Any(o =>
                            AtmOrderIdentity.NameMatches(o, AtmOrderIdentity.EntryName(bracket.BracketId)) &&
                            (o.OrderState == OrderState.Working || o.OrderState == OrderState.Submitted || o.OrderState == OrderState.Accepted));
                        if (!entryStillWorking)
                        {
                            toRemove.Add(bracket);
                        }
                        continue;
                    }

                    // P0-67: before ANY decision, find out what the broker actually holds. Every
                    // comparison below (`newStop > bracket.CurrentStopPrice`) is only meaningful if
                    // the cache is the broker's truth rather than this monitor's last wish.
                    ReconcileStopFromBroker(account, bracket);

                    double currentPrice = 0;
                    var md = position.Instrument.MarketData;
                    if (md != null && md.Last != null)
                        currentPrice = md.Last.Price;
                    if (currentPrice <= 0 && md != null && md.Ask != null)
                        currentPrice = md.Ask.Price;
                    if (currentPrice <= 0 && md != null && md.Bid != null)
                        currentPrice = md.Bid.Price;
                    if (currentPrice <= 0) continue;
                    double tickSize = position.Instrument.MasterInstrument.TickSize;
                    bool isLong = bracket.IsLong;
                    double entryPrice = bracket.EntryPrice;

                    if (bracket.Config.Type == AtmStrategyType.DrawdownShield)
                    {
                        if (!bracket.BreakevenTriggered && ShouldTriggerBreakeven(bracket.Config, entryPrice, currentPrice, isLong, tickSize))
                        {
                            double beStop = CalculateBreakevenStopPrice(entryPrice, isLong, tickSize, bracket.Config.BreakevenOffsetTicks);
                            // P0-67: BreakevenTriggered is set on the REQUEST so the move is not
                            // spammed every 5 seconds; ReconcileStopFromBroker un-sets it if the
                            // provider refused, which is what makes the retry happen.
                            if (RequestStopMove(account, bracket, beStop, "breakeven trigger reached"))
                                bracket.BreakevenTriggered = true;
                        }

                        if (!bracket.PartialProfitTaken && bracket.BreakevenTriggered)
                        {
                            double partialTarget = isLong
                                ? (entryPrice + (bracket.CurrentTargetPrice - entryPrice) * bracket.Config.PartialProfitPct)
                                : (entryPrice - (entryPrice - bracket.CurrentTargetPrice) * bracket.Config.PartialProfitPct);
                            bool partialHit = isLong ? (currentPrice >= partialTarget) : (currentPrice <= partialTarget);
                            if (partialHit)
                            {
                                int partialQty = (int)Math.Floor(bracket.Quantity * bracket.Config.PartialProfitPct);
                                if (partialQty > 0)
                                {
                                    var exitAction = isLong ? OrderAction.Sell : OrderAction.Buy;
                                    var partialOrder = account.CreateOrder(position.Instrument, exitAction, OrderType.Limit, TimeInForce.Day, partialQty, partialTarget, 0, bracket.OcoId, "Partial_" + bracket.BracketId, null);
                                    account.Submit(new[] { partialOrder });
                                }
                                bracket.PartialProfitTaken = true;
                            }
                        }
                    }

                    if (bracket.Config.Type == AtmStrategyType.ScaledRunner)
                    {
                        if (!bracket.BreakevenTriggered && ShouldTriggerBreakeven(bracket.Config, entryPrice, currentPrice, isLong, tickSize))
                        {
                            double beStop = CalculateBreakevenStopPrice(entryPrice, isLong, tickSize, bracket.Config.BreakevenOffsetTicks);
                            // P0-67: BreakevenTriggered is set on the REQUEST so the move is not
                            // spammed every 5 seconds; ReconcileStopFromBroker un-sets it if the
                            // provider refused, which is what makes the retry happen.
                            if (RequestStopMove(account, bracket, beStop, "breakeven trigger reached"))
                                bracket.BreakevenTriggered = true;
                        }

                        if (bracket.BreakevenTriggered)
                        {
                            double trailDist = tickSize * bracket.Config.StopTicks * bracket.Config.TrailMultiplier;
                            double newStop = isLong
                                ? (currentPrice - trailDist)
                                : (currentPrice + trailDist);
                            bool stopMoved = isLong ? (newStop > bracket.CurrentStopPrice) : (newStop < bracket.CurrentStopPrice);
                            if (stopMoved)
                            {
                                RequestStopMove(account, bracket, newStop, "trailing stop advanced");
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    try { NinjaTrader.Code.Output.Process("[AtmMonitor] Error monitoring bracket " + bracket.BracketId + ": " + ex.Message, PrintTo.OutputTab1); } catch { }
                }
            }

            if (toRemove.Count > 0)
            {
                lock (_bracketLock)
                {
                    foreach (var b in toRemove)
                        _activeBrackets.Remove(b.BracketId);
                }
            }
        }

        /// <summary>
        /// Maximum consecutive refused stop moves before this bracket stops asking. Three is the
        /// copier's number for the same situation and the same reason: enough to ride out a transient
        /// refusal, few enough that a provider which always refuses does not become an order flood.
        /// </summary>
        internal const int MaxStopModifyAttempts = 3;

        /// <summary>
        /// P0-67. Returns true only if a working stop order was found and the change was REQUESTED --
        /// which is not the same as honoured, and the caller must not treat it as such. It used to
        /// return void and swallow its own exceptions, so no caller could tell the difference between
        /// "moved", "no such order", and "threw".
        /// </summary>
        private bool ModifyStopPrice(Account account, string orderName, double newStopPrice, out string failureReason)
        {
            failureReason = null;
            try
            {
                Order live = AtmOrderIdentity.FindLiveByName(account, orderName);
                if (live != null)
                {
                    live.StopPrice = newStopPrice;
                    account.Change(new[] { live });
                    return true;
                }

                // P1-130. The two ways this fails are NOT the same news, and the old message
                // asserted the more alarming one for both: "the position may be unprotected" was
                // printed 55 times against a stop that was resting perfectly and had merely not
                // been ADVANCED. A risk surface that cries naked at a protected position trains
                // the operator to discount the line that will one day be true.
                Order present = AtmOrderIdentity.FindByName(account, orderName);

                if (present == null)
                {
                    failureReason = $"no order with name '{orderName}' is on '{account.Name}' at all";
                    RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_ORDER_NOT_FOUND",
                        $"no order with name '{orderName}' is on '{account.Name}' at all, so the move to "
                        + $"{newStopPrice} was not requested. The bracket's stop cannot be located; "
                        + "check the account for an unmanaged position.");
                }
                else
                {
                    failureReason = $"the stop order '{orderName}' is {present.OrderState} and no longer live";
                    RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_ORDER_NOT_FOUND",
                        $"the stop order '{orderName}' on '{account.Name}' is {present.OrderState} and no "
                        + $"longer live, so the move to {newStopPrice} was not requested."
                        + (RiskGuardAddOn.IsTerminal(present.OrderState)
                            ? " It is terminal, so THE POSITION MAY BE UNPROTECTED."
                            : " It is on its way out; the stop was not moved."));
                }
                return false;
            }
            catch (Exception ex)
            {
                failureReason = $"requesting a stop move threw {ex.GetType().Name}";
                RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_MODIFY_THREW",
                    $"requesting a stop move to {newStopPrice} on order '{orderName}' threw "
                    + $"{ex.GetType().Name}: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// P0-67. Requests a stop move and records it as OUTSTANDING. Deliberately does NOT touch
        /// `CurrentStopPrice`: that is assigned only from the live order, in ReconcileStopFromBroker.
        /// </summary>
        private bool RequestStopMove(Account account, ActiveBracket bracket, double newStopPrice, string reason)
        {
            // Found by the P0-67 trail test, not by reading: in the ScaledRunner branch the breakeven
            // move and the trailing move can BOTH fire in one sweep, so two Change() calls landed on
            // the same stop order back to back. Per NT8 semantics established by a controlled live
            // trade on 2026-08-10 (P0-61), a second change while one is in flight is dropped AND
            // REVERTS THE ORDER -- it ends at neither the first request's values nor the second's. So
            // the flood the cap was meant to prevent was also silently undoing itself.
            //
            // One outstanding request per bracket, which is the same reservation the copier keeps with
            // bracket.StopInFlight and for the same reason.
            if (!double.IsNaN(bracket.RequestedStopPrice))
            {
                RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_MOVE_IN_FLIGHT",
                    $"{bracket.BracketId}: a move to {bracket.RequestedStopPrice} is already in flight, "
                    + $"so the request for {newStopPrice} ({reason}) is being held back. A second "
                    + "Change() while one is in flight reverts the order and loses both.");
                return false;
            }

            if (bracket.StopModifyAttempts >= MaxStopModifyAttempts)
            {
                if (!bracket.StopMoveAbandonAnnounced)
                {
                    RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_MOVE_ABANDONED",
                        $"{bracket.BracketId}: {MaxStopModifyAttempts} stop moves failed, last observed "
                        // ⚠️ The fallback is not decoration. Both sites that spend the budget set
                        // the reason, but a bracket restored from the bridge's payload carries the
                        // count without it -- and "last observed reason: ." reads as a truth about
                        // the failure rather than as a gap in what we recorded.
                        + $"reason: {bracket.LastStopMoveFailureReason ?? "not recorded"}. Not asking again for this "
                        + $"bracket. The stop is still at {bracket.CurrentStopPrice} and will NOT trail. "
                        + "Intervene manually.");
                    bracket.StopMoveAbandonAnnounced = true;
                }
                return false;
            }

            // P1-130. EVERY failed request spends the budget, including the one where the order is
            // not in `account.Orders` at all.
            //
            // ⚠️ The first draft of this fix counted ONLY the "present but no longer live" case, on
            // the reasoning that a transient absence should not abandon a healthy bracket. That
            // reasoning is plausible and it reinstates the defect this ticket was filed for: an
            // order that is genuinely gone -- replaced, purged, never registered -- is absent on
            // EVERY sweep, so the budget is never spent, `MaxStopModifyAttempts` is never reached,
            // and the 5-second retry runs for the life of the position. That is the 55 log lines
            // measured on the live box, restored by a narrower condition.
            //
            // The cost of counting it is bounded and visible: three sweeps, fifteen seconds, and
            // then ATM_STOP_MOVE_ABANDONED says so once and names the price the stop is left at. A
            // bound that is occasionally early is a bound; one that cannot be reached is not.
            if (!ModifyStopPrice(account, AtmOrderIdentity.StopName(bracket.BracketId), newStopPrice, out string failureReason))
            {
                bracket.LastStopMoveFailureReason = failureReason;
                bracket.StopModifyAttempts++;
                return false;
            }

            bracket.RequestedStopPrice = newStopPrice;
            RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_MOVE_REQUESTED",
                $"{bracket.BracketId}: {reason} -- requested stop {bracket.CurrentStopPrice} -> "
                + $"{newStopPrice}. NOT yet honoured; the next sweep reports what the broker did.");
            return true;
        }

        /// <summary>
        /// P0-67, and the heart of the fix. Takes the LIVE order's stop price as the truth, compares
        /// it against any outstanding request, and says which of the three things happened: honoured,
        /// refused, or moved by someone else.
        ///
        /// Called at the top of every sweep for every bracket, so a refused move is detected within
        /// one 5-second tick with no settle event and no extra broker call.
        /// </summary>
        private void ReconcileStopFromBroker(Account account, ActiveBracket bracket)
        {
            string stopName = AtmOrderIdentity.StopName(bracket.BracketId);
            Order live = AtmOrderIdentity.FindLiveByName(account, stopName);
            if (live == null) return;      // closing, filled, or replaced -- nothing to reconcile

            double brokerPrice = live.StopPrice;
            double requested = bracket.RequestedStopPrice;

            if (!double.IsNaN(requested))
            {
                if (Math.Abs(brokerPrice - requested) <= 1e-9)
                {
                    RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_MOVE_CONFIRMED",
                        $"{bracket.BracketId}: provider honoured the move; stop is at {brokerPrice}.");
                    bracket.StopModifyAttempts = 0;
                    // P2-134. ⚠️ NO `StopMoveAbandonAnnounced = false` here, and the omission is
                    // deliberate. The ticket's spec asked for one, by analogy to P2-107's "the
                    // record clears when the CONDITION resolves" -- right in general and wrong
                    // here, because this condition cannot resolve while the latch is set: past
                    // MaxStopModifyAttempts `RequestStopMove` returns before it asks, a confirm
                    // needs an outstanding request, and the counter is reset only here. So the
                    // latch is only ever true when this line is unreachable, and the clear would
                    // be a no-op that reads as a working release valve. Abandonment is permanent
                    // for a bracket -- which is exactly what "not asking again for this bracket"
                    // says -- and the episode boundary is the bracket itself.
                }
                else
                {
                    // The move was requested and the broker is not holding it. This is P0-63's
                    // behaviour at the third call site, and the reason the trail latched: the old
                    // code would have recorded `requested` and never looked again.
                    bracket.StopModifyAttempts++;
                    bracket.LastStopMoveFailureReason = $"provider holds {brokerPrice} instead of requested {requested}";
                    RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_CHANGE_IGNORED",
                        $"{bracket.BracketId}: requested stop {requested} but the provider holds "
                        + $"{brokerPrice} (attempt {bracket.StopModifyAttempts} of "
                        + $"{MaxStopModifyAttempts}). Treating the BROKER's price as the truth. "
                        + "Same root cause as P0-63.");

                    // Re-arm so the next sweep re-evaluates and retries. Without this the trail is
                    // still latched -- just latched on a correct cache instead of a false one.
                    if (bracket.BreakevenTriggered && bracket.StopModifyAttempts < MaxStopModifyAttempts)
                        bracket.BreakevenTriggered = false;
                }
                bracket.RequestedStopPrice = double.NaN;
            }
            else if (Math.Abs(brokerPrice - bracket.CurrentStopPrice) > 1e-9 && bracket.CurrentStopPrice > 0)
            {
                // Nobody here asked for this. An ATM strategy, the user, or another add-on moved it.
                RiskGuardAddOn.LogFromComponent(account.Name, "ATM_STOP_MOVED_EXTERNALLY",
                    $"{bracket.BracketId}: stop is at {brokerPrice}, cache said "
                    + $"{bracket.CurrentStopPrice}, and this monitor did not request a move. Adopting "
                    + "the broker's price -- something else is managing this leg.");
            }

            // THE fix, in one line: the cache is what the broker holds. Never what was asked for.
            bracket.CurrentStopPrice = brokerPrice;
        }

        public bool ShouldTriggerBreakeven(AtmStrategyConfig config, double entryPrice, double currentPrice, bool isLong, double tickSize)
        {
            double diff = isLong ? (currentPrice - entryPrice) : (entryPrice - currentPrice);
            double ticksGain = diff / tickSize;
            return ticksGain >= config.BreakevenTriggerTicks;
        }

        public double CalculateBreakevenStopPrice(double entryPrice, bool isLong, double tickSize, int offsetTicks)
        {
            double offset = offsetTicks * tickSize;
            return isLong ? (entryPrice + offset) : (entryPrice - offset);
        }

        private double GetATR(Instrument instrument, int period)
        {
            try
            {
                if (period <= 0) period = 14;
                BarData bars = FetchBars(instrument, BarsPeriodType.Minute, 1, period + 5);
                if (bars == null || bars.Count < period + 1) return 0;

                double sum = 0;
                int count = 0;
                for (int i = bars.Count - period; i < bars.Count; i++)
                {
                    double high = bars.High[i];
                    double low = bars.Low[i];
                    double prevClose = i > 0 ? bars.Close[i - 1] : bars.Close[i];
                    double tr = Math.Max(high - low, Math.Max(Math.Abs(high - prevClose), Math.Abs(low - prevClose)));
                    sum += tr;
                    count++;
                }
                return count > 0 ? sum / count : 0;
            }
            catch (Exception ex)
            {
                try { NinjaTrader.Code.Output.Process("[AtmMonitor] GetATR error: " + ex.Message, PrintTo.OutputTab1); } catch { }
                return 0;
            }
        }

        private double FindSwingPoint(Instrument instrument, bool isLong, int lookback)
        {
            try
            {
                BarData bars = FetchBars(instrument, BarsPeriodType.Minute, 5, lookback + 5);
                if (bars == null || bars.Count < lookback + 2) return 0;

                if (isLong)
                {
                    double lowest = double.MaxValue;
                    for (int i = bars.Count - lookback; i < bars.Count; i++)
                    {
                        double low = bars.Low[i];
                        if (low < lowest) lowest = low;
                    }
                    return lowest;
                }
                else
                {
                    double highest = double.MinValue;
                    for (int i = bars.Count - lookback; i < bars.Count; i++)
                    {
                        double high = bars.High[i];
                        if (high > highest) highest = high;
                    }
                    return highest;
                }
            }
            catch (Exception ex)
            {
                try { NinjaTrader.Code.Output.Process("[AtmMonitor] FindSwingPoint error: " + ex.Message, PrintTo.OutputTab1); } catch { }
                return 0;
            }
        }

        private static BarData FetchBars(Instrument instrument, BarsPeriodType periodType, int periodValue, int count)
        {
            BarData result = null;
            var done = new ManualResetEventSlim(false);
            var barsPeriod = new BarsPeriod { BarsPeriodType = periodType, Value = periodValue };
            var request = new BarsRequest(instrument, count) { BarsPeriod = barsPeriod };
            request.Request((req, code, msg) =>
            {
                if (code == ErrorCode.NoError && req.Bars != null)
                {
                    var bars = req.Bars;
                    int n = bars.Count;
                    int start = Math.Max(0, n - count);
                    int copied = n - start;
                    result = new BarData
                    {
                        High = new double[copied],
                        Low = new double[copied],
                        Close = new double[copied],
                        Open = new double[copied],
                        Volume = new long[copied],
                        Time = new DateTime[copied],
                        Count = copied
                    };
                    for (int i = 0; i < copied; i++)
                    {
                        int src = start + i;
                        result.High[i] = bars.GetHigh(src);
                        result.Low[i] = bars.GetLow(src);
                        result.Close[i] = bars.GetClose(src);
                        result.Open[i] = bars.GetOpen(src);
                        result.Volume[i] = bars.GetVolume(src);
                        result.Time[i] = bars.GetTime(src);
                    }
                }
                done.Set();
            });
            if (!done.Wait(TimeSpan.FromSeconds(10)))
                return null;
            request.Dispose();
            return result;
        }

        private static DateTime GetEasternTime()
        {
            try
            {
                return TimeZoneInfo.ConvertTimeBySystemTimeZoneId(DateTime.UtcNow, "Eastern Standard Time");
            }
            catch
            {
                return DateTime.Now;
            }
        }

        private static bool IsRTH(DateTime time)
        {
            if (time.DayOfWeek == DayOfWeek.Saturday || time.DayOfWeek == DayOfWeek.Sunday)
                return false;
            int hour = time.Hour;
            int minute = time.Minute;
            int totalMinutes = hour * 60 + minute;
            return totalMinutes >= 570 && totalMinutes < 960;
        }
    }
}
