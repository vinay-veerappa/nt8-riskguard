using System;
using System.IO;
using System.Collections.Generic;

#if TESTING
using Newtonsoft.Json.Linq;
using Newtonsoft.Json;
#else
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
#endif

namespace NinjaTrader.NinjaScript.AddOns
{
    public class EconomicNewsEvent
    {
        public DateTime EventTimeUtc { get; set; }
        public string Title { get; set; } = "CPI Release";
        public string Currency { get; set; } = "USD";
        public string Impact { get; set; } = "High";
    }

    public class PropFirmProfile
    {
        public string Name { get; set; } = "Apex Trader Funding";
        public List<string> AllowedInstruments { get; set; } = new List<string> { "NQ", "MNQ", "ES", "MES", "YM", "MYM", "CL", "MCL", "GC", "MGC", "RTY", "M2K" };
        public List<string> BlockedInstruments { get; set; } = new List<string> { "ZB", "ZN", "6E", "6B" };
    }

    public class PropFirmProtectionConfig
    {
        // P1-81: `ArmedForLive` WAS HERE and is deleted, not deprecated. It defaulted to
        // false "for safety" and had its own confirmLive gate, and NO PROP RULE EVER READ IT --
        // the news shield, the profit-target lock and the peak-equity giveback are all reached
        // through the GUARD's mode and arming. So it had two readings and both were false:
        // "the prop rules are off until I arm this" (they are not) and "arming this turns them
        // on" (it does not).
        //
        // Deleted rather than wired up because this system should have ONE arming answer and the
        // guard's own mode is it. A second flag the prop rules must ALSO satisfy creates a state
        // where the operator has armed the guard, believes the prop rules are live, and a
        // separate switch silently holds them off -- P3-34's defect inverted.
        //
        // ⚠️ NOT to be confused with CopierRelationship.ArmedForLive, which is LOAD-BEARING:
        // `rel.IsEnabled && !rel.ArmedForLive` is what puts a copier relationship in Shadow.
        // Same name, different type, opposite consequence.
        public bool EnableNewsShield { get; set; } = false; // P2-25: the news-shield rule is inert (no loader populates _newsEvents). Default OFF so the config does not assert protection that does not exist. Re-enable after implementing the rule.
        public int NewsBufferMinutesBefore { get; set; } = 2;
        public int NewsBufferMinutesAfter { get; set; } = 2;
        public string LocalNewsEventsFilePath { get; set; } = "";
        public bool EnableProfitTargetLock { get; set; } = true;
        public double EvaluationTargetProfit { get; set; } = 3000.0;
        public bool EnablePeakEquityProtection { get; set; } = true;
        public double MaxPeakGivebackPct { get; set; } = 0.30;
        // P1-40: absolute floor, in dollars, below which an open gain is not treated as an
        // established peak. The giveback rule is proportional, so without this a one-tick peak
        // ($0.50 on MNQ) makes any retrace a >=100% giveback and flattens the position seconds
        // after entry. Set to 0 for the old, purely proportional behaviour.
        public double MinPeakGainDollars { get; set; } = 50.0;
        public bool EnableConsistencyCap { get; set; } = false; // P1-77: the consistency-cap rule is never evaluated. Default OFF so the config does not assert protection that does not exist. Re-enable after implementing the rule.
        public double MaxDailyProfitPctOfTarget { get; set; } = 0.35;
    }

    public class PropFirmProtectionSuite
    {
        private static readonly Lazy<PropFirmProtectionSuite> _instance = new Lazy<PropFirmProtectionSuite>(() => new PropFirmProtectionSuite());
        public static PropFirmProtectionSuite Instance => _instance.Value;

        private readonly List<EconomicNewsEvent> _newsEvents = new List<EconomicNewsEvent>();
        private readonly object _lock = new object();
        public PropFirmProtectionConfig Config { get; private set; } = new PropFirmProtectionConfig();

        /// <summary>
        /// How many news events are loaded. This is `P2-25`'s evidence count, and it is the only
        /// number that distinguishes a working news shield from one that can never fire -- so it
        /// is exposed rather than inferred, and the rule inventory reads it here.
        /// </summary>
        public int NewsEventCount
        {
            get
            {
                lock (_lock)
                {
                    return _newsEvents.Count;
                }
            }
        }

        public void AddTestNewsEvent(EconomicNewsEvent ev)
        {
            lock (_lock)
            {
                _newsEvents.Add(ev);
            }
        }

        // P2-25: load news events from LocalNewsEventsFilePath. This is the loader
        // that was missing -- without it, _newsEvents is always empty and the news
        // shield can never fire. Called from UpdateConfig when a config with a
        // non-empty path is applied, and can be called directly to refresh.
        public void LoadNewsEventsFromDisk(string filePath)
        {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath)) return;
            try
            {
                string json = File.ReadAllText(filePath);
                var events = JsonConvert.DeserializeObject<List<EconomicNewsEvent>>(json);
                if (events != null)
                {
                    lock (_lock)
                    {
                        _newsEvents.Clear();
                        _newsEvents.AddRange(events);
                    }
                }
            }
            catch { }
        }

        public void UpdateConfig(PropFirmProtectionConfig config, bool confirmLive = false)
        {
            if (config == null) return;

            // P1-81: the "Safety Gate" that disarmed ArmedForLive was here. It went with the flag
            // -- a gate on a value nothing reads protects nothing. `confirmLive` is deliberately
            // left in the signature: changing a public method signature is a separate decision
            // from deleting a dead field, and bundling the two would hide one inside the other.

            lock (_lock)
            {
                Config = config;
            }

            // P2-25: load news events if a path is configured
            if (!string.IsNullOrEmpty(config.LocalNewsEventsFilePath))
                LoadNewsEventsFromDisk(config.LocalNewsEventsFilePath);
        }

        public bool IsInNewsWindow(DateTime nowUtc, int bufferMinutesBefore, int bufferMinutesAfter)
        {
            lock (_lock)
            {
                foreach (var ev in _newsEvents)
                {
                    if (!string.Equals(ev.Impact, "High", StringComparison.OrdinalIgnoreCase)) continue;
                    var startWindow = ev.EventTimeUtc.AddMinutes(-bufferMinutesBefore);
                    var endWindow = ev.EventTimeUtc.AddMinutes(bufferMinutesAfter);
                    if (nowUtc >= startWindow && nowUtc <= endWindow)
                    {
                        return true;
                    }
                }
            }
            return false;
        }

        public bool EvaluateProfitTargetLock(double currentRealizedPnL, PropFirmProtectionConfig config = null)
        {
            var cfg = config ?? Config;
            if (cfg == null || !cfg.EnableProfitTargetLock) return false;
            return currentRealizedPnL >= cfg.EvaluationTargetProfit;
        }

        /// <summary>
        /// P1-77. The consistency cap: has the day's realised profit exceeded the share of the
        /// evaluation target the firm allows in one day?
        ///
        /// ⚠️ THIS RULE EXISTED AS CONFIG AND NOTHING ELSE. `EnableConsistencyCap` (default TRUE)
        /// and `MaxDailyProfitPctOfTarget` (0.35) appeared at exactly two sites each — the
        /// declaration and the JSON parser — for the life of the addon. An operator reading the
        /// config, or an agent reading it over the API, was told the consistency rule was on with
        /// a 35% cap. It had never capped anything. A prop consistency breach is an
        /// ACCOUNT-FAILURE condition: exceed it once and the evaluation is void however good the
        /// rest of the account looks, so the failure mode was believing you were covered against
        /// the one rule that silently disqualifies you.
        ///
        /// ⚠️ THE ACTION IS NOT FLATTEN, and that is not a preference. Hitting a profit cap is not
        /// a risk event, and flattening a winner to enforce a consistency rule REALISES the very
        /// P&amp;L the rule is about — it would cause the breach it exists to prevent. This returns
        /// a breach so the caller can refuse new ENTRIES; open positions run.
        ///
        /// ⚠️ AN UNCOMPUTABLE CAP RETURNS FALSE, NOT TRUE. 35% of a zero evaluation target is
        /// zero, and a naive `pnl >= cap` then breaches on any profit at all — on every account
        /// with no target set, which is most of the 96. That is `P1-40`'s shape (a proportional
        /// test with no floor, firing on a single tick) and `P3-30`'s (a detector that fires on
        /// everything). A rule that cannot be computed must report NOTHING.
        /// </summary>
        /// <param name="dayRealizedPnL">The account's realised P&amp;L for the session, in dollars.</param>
        public bool EvaluateConsistencyCap(double dayRealizedPnL, PropFirmProtectionConfig config = null)
        {
            var cfg = config ?? Config;
            if (cfg == null || !cfg.EnableConsistencyCap) return false;

            // No target, no cap. See the note above: this is the branch that stops the rule
            // firing on every account that has never been given an evaluation target.
            if (cfg.EvaluationTargetProfit <= 0) return false;

            // A losing or flat day cannot breach a PROFIT cap. Guarded explicitly rather than
            // left to the comparison, because the comparison alone is correct only while the cap
            // is positive, and that is a second thing to be true rather than one.
            if (dayRealizedPnL <= 0) return false;

            double cap = cfg.EvaluationTargetProfit * cfg.MaxDailyProfitPctOfTarget;
            if (cap <= 0) return false;

            return dayRealizedPnL >= cap;
        }

        public bool EvaluatePeakEquityGiveback(double peakOpenGain, double currentUnrealized, PropFirmProtectionConfig config = null)
        {
            // Both arguments must be unrealized-only PnL in dollars. Passing a
            // total-equity peak combined with unrealized PnL causes spurious
            // giveback breaches when the account is flat after a profitable session.
            var cfg = config ?? Config;
            if (cfg == null || !cfg.EnablePeakEquityProtection || peakOpenGain <= 0 || currentUnrealized >= peakOpenGain) return false;
            // P1-40: the test below is proportional, so without an absolute floor a peak of one
            // tick ($0.50 on MNQ) turns any retrace into a >=100% giveback. Live on 2026-08-07
            // that fired six times in 36 seconds, first 2.4s after entry with the position down
            // $1.00; in an acting mode it would flatten nearly every trade on entry. Below the
            // floor there is no meaningful profit to protect, and the daily-loss and stop-guard
            // rules already cover the downside.
            if (peakOpenGain < cfg.MinPeakGainDollars) return false;
            double giveback = peakOpenGain - currentUnrealized;
            double givebackPct = giveback / peakOpenGain;
            return givebackPct >= cfg.MaxPeakGivebackPct;
        }

        public void LoadFromDisk(string filePath)
        {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath)) return;
            try
            {
                string json = File.ReadAllText(filePath);
                var dict = JsonConvert.DeserializeObject<Dictionary<string, JObject>>(json);
                JObject jObj = null;
                if (dict != null && dict.ContainsKey("global")) jObj = dict["global"];
                else if (!string.IsNullOrWhiteSpace(json)) jObj = JObject.Parse(json);

                if (jObj != null)
                {
                    var cfg = ParseConfig(jObj);
                    UpdateConfig(cfg);
                }
            }
            catch {}
        }

        public void SaveToDisk(string filePath)
        {
            if (string.IsNullOrEmpty(filePath)) return;
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(filePath));
                lock (_lock)
                {
                    var dict = new Dictionary<string, PropFirmProtectionConfig> { ["global"] = Config };
                    File.WriteAllText(filePath, JsonConvert.SerializeObject(dict, Formatting.Indented));
                }
            }
            catch {}
        }

        public PropFirmProtectionConfig ParseConfig(JObject jObj)
        {
            if (jObj == null) return new PropFirmProtectionConfig();
            return new PropFirmProtectionConfig
            {
                // P1-81: ArmedForLive is deliberately IGNORED rather than rejected. An operator's
                // prop_limits.json still carries the key and must keep parsing -- absent,
                // present-and-unknown and present-and-malformed are different inputs (P3-111),
                // and only one of them is a caller error worth refusing.
                EnableNewsShield = jObj["EnableNewsShield"] != null ? (bool)jObj["EnableNewsShield"] : (jObj["enableNewsShield"] != null ? (bool)jObj["enableNewsShield"] : (jObj["newsShield"] != null ? (bool)jObj["newsShield"] : false)),
                NewsBufferMinutesBefore = jObj["NewsBufferMinutesBefore"] != null ? (int)jObj["NewsBufferMinutesBefore"] : (jObj["newsBufferMinutesBefore"] != null ? (int)jObj["newsBufferMinutesBefore"] : 2),
                NewsBufferMinutesAfter = jObj["NewsBufferMinutesAfter"] != null ? (int)jObj["NewsBufferMinutesAfter"] : (jObj["newsBufferMinutesAfter"] != null ? (int)jObj["newsBufferMinutesAfter"] : 2),
                LocalNewsEventsFilePath = jObj["LocalNewsEventsFilePath"]?.ToString() ?? jObj["localNewsEventsFilePath"]?.ToString() ?? "",
                EnableProfitTargetLock = jObj["EnableProfitTargetLock"] != null ? (bool)jObj["EnableProfitTargetLock"] : (jObj["enableProfitTargetLock"] != null ? (bool)jObj["enableProfitTargetLock"] : (jObj["profitTargetLock"] != null ? (bool)jObj["profitTargetLock"] : true)),
                EvaluationTargetProfit = jObj["EvaluationTargetProfit"] != null ? (double)jObj["EvaluationTargetProfit"] : (jObj["evaluationTargetProfit"] != null ? (double)jObj["evaluationTargetProfit"] : (jObj["profitTarget"] != null ? (double)jObj["profitTarget"] : 3000.0)),
                EnablePeakEquityProtection = jObj["EnablePeakEquityProtection"] != null ? (bool)jObj["EnablePeakEquityProtection"] : (jObj["enablePeakEquityProtection"] != null ? (bool)jObj["enablePeakEquityProtection"] : (jObj["peakEquityProtection"] != null ? (bool)jObj["peakEquityProtection"] : true)),
                MaxPeakGivebackPct = jObj["MaxPeakGivebackPct"] != null ? (double)jObj["MaxPeakGivebackPct"] : (jObj["maxPeakGivebackPct"] != null ? (double)jObj["maxPeakGivebackPct"] : (jObj["givebackPct"] != null ? (double)jObj["givebackPct"] : 0.30)),
                MinPeakGainDollars = jObj["MinPeakGainDollars"] != null ? (double)jObj["MinPeakGainDollars"] : (jObj["minPeakGainDollars"] != null ? (double)jObj["minPeakGainDollars"] : 50.0),
                EnableConsistencyCap = jObj["EnableConsistencyCap"] != null ? (bool)jObj["EnableConsistencyCap"] : (jObj["enableConsistencyCap"] != null ? (bool)jObj["enableConsistencyCap"] : false),
                MaxDailyProfitPctOfTarget = jObj["MaxDailyProfitPctOfTarget"] != null ? (double)jObj["MaxDailyProfitPctOfTarget"] : (jObj["maxDailyProfitPctOfTarget"] != null ? (double)jObj["maxDailyProfitPctOfTarget"] : 0.35)
            };
        }
    }
}
