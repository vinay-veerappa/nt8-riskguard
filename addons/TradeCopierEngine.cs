using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;

#if TESTING
using Newtonsoft.Json.Linq;
using Newtonsoft.Json;
// OnExecution now compiles in the test build, so it needs the Cbi types (Account, Order,
// Execution, Instrument, OrderAction, ...) which are provided by the stubs in
// RiskGuardAddOnTests.cs under the same namespace.
using NinjaTrader.Cbi;
using NinjaTrader.Code;
// UI2: ConfigFilePath is rooted in Globals.UserDataDir, which the test build stubs to
// BaseDirectory/MockUserData -- so the acceptance tests round-trip through the real
// property rather than through a path they were handed.
using NinjaTrader.Core;
#else
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Core;
#endif

namespace NinjaTrader.NinjaScript.AddOns
{
    public enum CopierExecutionMode { Executions, Orders }
    public enum CopierSizingMode { QuantityRatio, FixedLot, NetLiquidationRatio, AvailableCashPercent, PerTickerMatrix }

    /// <summary>
    /// The operator surfaces' request builders. UI2 / `P?-65`.
    ///
    /// WHY THIS IS IN CORE AND NOT IN THE WINDOW. The design's one rule is that a surface
    /// renders and dispatches: it never constructs a domain object. The window broke that
    /// at two sites -- build a fresh `CopierRelationship`/`CopierGroup` from the eight
    /// fields the Add form collects, `Upsert` it, save -- which WIPED `PerTickerRatios`,
    /// `CustomSymbolMappings`, `MaxSlippageTicks`, `Mode`, `DailyLossLimit` and
    /// `IsQuarantined`, because the form cannot see them and a fresh object carries
    /// defaults. That is the fifth and sixth instance of one defect; slice 3b deleted the
    /// third and fourth from the bridge.
    ///
    /// A request is a JObject, and `ApplyRelationshipRequest` merges it over what is
    /// stored, so a field the form does not mention survives. But an untested builder has
    /// its own failure mode, and it has already shipped once: `P1-74`'s `autoConversion`
    /// argument was not a field on anything, so `NormalizeRequest` dropped it and the
    /// argument had never done a thing. A MISSPELLED KEY IS SILENTLY IGNORED. That is why
    /// the mapping is here, where a test can assert every field arrives, rather than
    /// inline in a window the test build compiles away.
    /// </summary>
    public static class CopierRequests
    {
        /// <summary>Everything the window's "Add Relationship" form collects, and nothing else.</summary>
        public static JObject Relationship(
            string leaderAccount, string followerAccount, CopierSizingMode sizingMode,
            double quantityRatio, int maxPositionSize, bool autoSymbolConversion,
            bool stealthMode, bool armedForLive, bool isEnabled)
        {
            bool fixedLotMode = sizingMode == CopierSizingMode.FixedLot;
            int fixedLotSize = (int)Math.Round(quantityRatio);

            return new JObject
            {
                { "leaderAccount", leaderAccount },
                { "followerAccount", followerAccount },
                { "sizingMode", sizingMode.ToString() },
                { "quantityRatio", quantityRatio },
                { "maxPositionSize", maxPositionSize },
                { "autoSymbolConversion", autoSymbolConversion },
                { "stealthMode", stealthMode },
                { "armedForLive", armedForLive },
                { "isEnabled", isEnabled },
                { "fixedLotMode", fixedLotMode },
                { "fixedLotSize", fixedLotSize }
            };
        }

        /// <summary>Everything the window's "Add Group" form collects, and nothing else.</summary>
        public static JObject Group(
            string groupName, string leaderAccount, IEnumerable<string> followerAccounts,
            CopierSizingMode sizingMode, double quantityRatio, int maxPositionSize,
            bool autoSymbolConversion, bool stealthMode, bool armedForLive, bool isEnabled)
        {
            bool fixedLotMode = sizingMode == CopierSizingMode.FixedLot;
            int fixedLotSize = (int)Math.Round(quantityRatio);

            var followers = new JArray();
            if (followerAccounts != null)
            {
                foreach (var follower in followerAccounts)
                {
                    followers.Add(follower);
                }
            }

            return new JObject
            {
                { "groupName", groupName },
                { "leaderAccount", leaderAccount },
                { "followerAccounts", followers },
                { "sizingMode", sizingMode.ToString() },
                { "quantityRatio", quantityRatio },
                { "maxPositionSize", maxPositionSize },
                { "autoSymbolConversion", autoSymbolConversion },
                { "stealthMode", stealthMode },
                { "armedForLive", armedForLive },
                { "isEnabled", isEnabled },
                { "fixedLotMode", fixedLotMode },
                { "fixedLotSize", fixedLotSize }
            };
        }

        /// <summary>
        /// The row buttons: enable/disable, and releasing a quarantine. These used to mutate
        /// the STORED object in place and then Upsert it, so a write the engine went on to
        /// refuse had already taken effect in memory.
        /// </summary>
        public static JObject RelationshipEdit(string leaderAccount, string followerAccount,
                                               bool? isEnabled, bool? releaseQuarantine)
        {
            var req = new JObject
            {
                { "leaderAccount", leaderAccount },
                { "followerAccount", followerAccount }
            };

            if (isEnabled.HasValue)
            {
                req["isEnabled"] = isEnabled.Value;
            }

            if (releaseQuarantine == true)
            {
                req["isQuarantined"] = false;
            }

            return req;
        }

        /// <summary>The group row's enable/disable button. Same defect, group half.</summary>
        public static JObject GroupEdit(string groupName, bool? isEnabled)
        {
            var req = new JObject
            {
                { "groupName", groupName }
            };

            if (isEnabled.HasValue)
            {
                req["isEnabled"] = isEnabled.Value;
            }

            return req;
        }
    }

    public class CopierRelationship
    {
        public string Id { get; set; } = Guid.NewGuid().ToString();
        public string LeaderAccountName { get; set; } = "";
        public string FollowerAccountName { get; set; } = "";
        public bool IsEnabled { get; set; } = true;
        public bool ArmedForLive { get; set; } = false; // MUST default to false for safety
        public CopierExecutionMode Mode { get; set; } = CopierExecutionMode.Executions;
        public CopierSizingMode SizingMode { get; set; } = CopierSizingMode.QuantityRatio;
        public double QuantityRatio { get; set; } = 1.0;
        public bool FixedLotMode { get; set; } = false;
        public int FixedLotSize { get; set; } = 1;
        public bool AutoSymbolConversion { get; set; } = true;
        public Dictionary<string, double> PerTickerRatios { get; set; } = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string, string> CustomSymbolMappings { get; set; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        // P0-9 / P1-23: `EnableFollowerAtm` and `FollowerAtmStrategyName` were REMOVED here.
        // They were carried between DTOs and read by nothing -- not parsed from disk, not exposed
        // by the bridge API, not shown in the UI -- so they could not even be set, while implying
        // followers were getting an ATM bracket. Same "config must not lie" rule as P1-23.
        // The leader's real stop is now mirrored (P0-9); a copier-side DEFAULT bracket is
        // deliberately NOT reintroduced, because RiskGuard's auto-stop already owns "position with
        // no stop", and two independent stop sources on one position over-cover and flip it.
        public bool StealthMode { get; set; } = true;
        public int MaxPositionSize { get; set; } = 100;
        public double DailyLossLimit { get; set; } = 1000.0;
        public bool IsQuarantined { get; set; } = false;
        public string QuarantineReason { get; set; }

        // P1-22: these two were displayed in TradeCopierWindow (:799) but written by nothing --
        // the UI reported 0ms and 0.0t however badly a copy actually filled. Both are now
        // populated from the follower's own fill. LatencyMs is the LAST observed leader-fill ->
        // follower-fill gap; AvgSlippageTicks is a running mean, matching what the names claim.
        public double LatencyMs { get; set; }
        public double AvgSlippageTicks { get; set; }

        // P1-22: ticks of adverse slippage on an ENTRY copy that quarantine this relationship.
        // 0 disables the check. Signed so only slippage *against* the follower counts.
        public double MaxSlippageTicks { get; set; } = 0.0;
    }

    // ── UI1: the conformance read model ────────────────────────────────────────────
    // docs/UI_REDESIGN_DESIGN.md SS2. The UI's job is not to display numbers, it is to
    // answer "is each follower doing what I configured it to do". That is a comparison
    // -- configured vs actual vs verdict -- so it is computed HERE, once, against the
    // same enumeration and the same sizing function the copy path uses. A consumer that
    // recomputes it is a second implementation of the rule and will drift from the first.

    /// <summary>
    /// One relationship's verdict. Ordered by SEVERITY, not alphabetically, because the
    /// UI ranks by it: `Orphan` MUST outrank `Diverged`. An orphan is a live position on a
    /// funded account that nothing is managing -- the worst state this system can report.
    /// </summary>
    public enum CopierConformance
    {
        Idle = 0,        // leader flat AND follower flat. A PASS, not a blank row.
        Match = 1,       // actual == expected
        Shadow = 2,      // IsEnabled true, ArmedForLive false: configured, will not act
        Diverged = 3,    // both non-flat, quantity or side disagrees
        Orphan = 4,      // leader FLAT, follower NOT. Ranks above Diverged, deliberately.
        Quarantined = 5  // not copying at all, so agreement is meaningless
    }

    /// <summary>
    /// A measurement AND the number of samples behind it. The pair is the point: these
    /// metrics are SESSION-SCOPED and a recompile resets them, so a bare 0 cannot
    /// distinguish "no fill observed yet" from "a fill was observed and was perfect".
    /// That confusion was misdiagnosed as a broken measurement and cost two sessions as
    /// `P?-66`. `Samples == 0` means NEVER MEASURED and the UI must render it as "--".
    /// </summary>
    public class CopierMetric
    {
        public double Value { get; set; }
        public int Samples { get; set; }
        public bool Measured { get { return Samples > 0; } }
    }

    /// <summary>
    /// ONE ROW PER RELATIONSHIP **PER INSTRUMENT ROOT**, not one row per
    /// relationship. Conformance is per instrument: a follower can mirror NQ
    /// correctly while holding an unmanaged ES position, and a single aggregate
    /// row cannot say which one diverged. `InstrumentFullName` is null only for
    /// the placeholder row emitted when neither side holds anything.
    /// </summary>
    public class CopierSnapshotRow
    {
        public string RelationshipId { get; set; }
        public string LeaderAccountName { get; set; }
        public string FollowerAccountName { get; set; }
        public string GroupName { get; set; }          // null for a DIRECT relationship
        public string InstrumentFullName { get; set; }   // null when no instrument could be derived
        public CopierSizingMode SizingMode { get; set; }
        public double EffectiveRatio { get; set; }
        public bool IsEnabled { get; set; }
        public bool ArmedForLive { get; set; }
        public bool IsQuarantined { get; set; }
        public string QuarantineReason { get; set; }
        public bool StealthMode { get; set; }

        public MarketPosition LeaderSide { get; set; }
        public int LeaderQuantity { get; set; }        // ABSOLUTE; side is carried separately
        public MarketPosition ExpectedSide { get; set; }
        public int ExpectedQuantity { get; set; }
        public bool ExpectedIsClamped { get; set; }
        public MarketPosition ActualSide { get; set; }
        public int ActualQuantity { get; set; }

        public CopierMetric Latency { get; set; }
        public CopierMetric Slippage { get; set; }

        public CopierConformance Verdict { get; set; }
    }

    public class CopierSnapshot
    {
        public List<CopierSnapshotRow> Rows { get; set; }
        public DateTime TakenUtc { get; set; }
    }

    public class CopierGroup
    {
        public string Id { get; set; } = Guid.NewGuid().ToString();
        public string GroupName { get; set; } = "";
        public string LeaderAccountName { get; set; } = "";
        public bool IsEnabled { get; set; } = true;
        public bool ArmedForLive { get; set; } = false; // MUST default to false for safety
        public CopierExecutionMode Mode { get; set; } = CopierExecutionMode.Executions;
        public CopierSizingMode SizingMode { get; set; } = CopierSizingMode.QuantityRatio;
        public double QuantityRatio { get; set; } = 1.0;
        public bool FixedLotMode { get; set; } = false;
        public int FixedLotSize { get; set; } = 1;
        public bool AutoSymbolConversion { get; set; } = true;
        public Dictionary<string, double> PerTickerRatios { get; set; } = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
        public Dictionary<string, string> CustomSymbolMappings { get; set; } = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        public bool StealthMode { get; set; } = true;
        public int MaxPositionSize { get; set; } = 100;
        public double DailyLossLimit { get; set; } = 1000.0;
        public double MaxSlippageTicks { get; set; } = 0.0;   // P1-22
        public List<string> FollowerAccounts { get; set; } = new List<string>();

        public List<CopierRelationship> ToRelationships()
        {
            var list = new List<CopierRelationship>();
            if (FollowerAccounts == null) return list;
            foreach (var follower in FollowerAccounts)
            {
                if (string.IsNullOrWhiteSpace(follower)) continue;
                list.Add(new CopierRelationship
                {
                    Id = $"{Id}_{follower}",
                    LeaderAccountName = this.LeaderAccountName,
                    FollowerAccountName = follower.Trim(),
                    IsEnabled = this.IsEnabled,
                    ArmedForLive = this.ArmedForLive,
                    Mode = this.Mode,
                    SizingMode = this.SizingMode,
                    QuantityRatio = this.QuantityRatio,
                    FixedLotMode = this.FixedLotMode,
                    FixedLotSize = this.FixedLotSize,
                    AutoSymbolConversion = this.AutoSymbolConversion,
                    PerTickerRatios = this.PerTickerRatios != null ? new Dictionary<string, double>(this.PerTickerRatios, StringComparer.OrdinalIgnoreCase) : new Dictionary<string, double>(),
                    CustomSymbolMappings = this.CustomSymbolMappings != null ? new Dictionary<string, string>(this.CustomSymbolMappings, StringComparer.OrdinalIgnoreCase) : new Dictionary<string, string>(),
                    StealthMode = this.StealthMode,
                    MaxPositionSize = this.MaxPositionSize,
                    DailyLossLimit = this.DailyLossLimit,
                    MaxSlippageTicks = this.MaxSlippageTicks
                });
            }
            return list;
        }
    }

    public class CopierConfigPayload
    {
        public Dictionary<string, CopierRelationship> Relationships { get; set; } = new Dictionary<string, CopierRelationship>();
        public Dictionary<string, CopierGroup> Groups { get; set; } = new Dictionary<string, CopierGroup>();
    }

    public class TradeCopierEngine
    {
        private static readonly Lazy<TradeCopierEngine> _instance = new Lazy<TradeCopierEngine>(() => new TradeCopierEngine());
        public static TradeCopierEngine Instance => _instance.Value;

        private readonly List<CopierRelationship> _relationships = new List<CopierRelationship>();
        private readonly List<CopierGroup> _groups = new List<CopierGroup>();
        private readonly HashSet<string> _copiedExecutionIds = new HashSet<string>();
        private readonly Queue<string> _executionIdQueue = new Queue<string>();
        private const int MaxExecutionCacheSize = 5000;
        private readonly object _lock = new object();
        // P0-63. Accounts whose provider has been observed ignoring Account.Change(). Once marked,
        // the copier goes straight to cancel-then-create on that account without issuing another
        // doomed Change(). Session-scoped; cleared in ResetBracketsForTest so tests do not leak,
        // and in SyncFollowerStopOnce when the last active bracket for the account is stood down
        // so a provider reconfiguration mid-session is not permanently penalised.
        private readonly HashSet<string> _accountsIgnoringChange = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        public void AddRelationship(CopierRelationship rel) => UpsertRelationship(rel);

        public void UpsertRelationship(CopierRelationship rel, bool confirmLive = false)
        {
            if (rel == null || string.IsNullOrEmpty(rel.LeaderAccountName)) return;

            // Safety Gate: Disarm ArmedForLive unless confirmLive == true is explicitly passed
            if (rel.ArmedForLive && !confirmLive)
            {
                rel.ArmedForLive = false;
            }

            lock (_lock)
            {
                var existing = _relationships.FirstOrDefault(r => 
                    r.LeaderAccountName.Equals(rel.LeaderAccountName, StringComparison.OrdinalIgnoreCase) && 
                    r.FollowerAccountName.Equals(rel.FollowerAccountName, StringComparison.OrdinalIgnoreCase));
                
                if (existing != null)
                {
                    _relationships.Remove(existing);
                }
                _relationships.Add(rel);
            }
        }

        public void RemoveRelationship(string leaderAccount, string followerAccount = null)
        {
            lock (_lock)
            {
                _relationships.RemoveAll(r => 
                    r.LeaderAccountName.Equals(leaderAccount, StringComparison.OrdinalIgnoreCase) &&
                    (string.IsNullOrEmpty(followerAccount) || r.FollowerAccountName.Equals(followerAccount, StringComparison.OrdinalIgnoreCase)));
            }
        }

        public int CalculateScaledQuantity(int sourceQuantity, decimal scaleFactor)
        {
            if (sourceQuantity <= 0 || scaleFactor <= 0) return 0;
            decimal rawQuantity = (decimal)sourceQuantity * scaleFactor;
            decimal rounded = Math.Round(rawQuantity, 0, MidpointRounding.AwayFromZero);
            if (rounded > int.MaxValue) return int.MaxValue;
            return (int)rounded;
        }

        public int CalculateSafeFollowerDelta(int leaderTargetQty, int currentFollowerQty, bool isMarketOrder, out bool isBlocked)
        {
            isBlocked = false;
            int delta = leaderTargetQty - currentFollowerQty;
            if (delta == 0) return 0;

            if (isMarketOrder && currentFollowerQty == 0)
            {
                bool isLeaderShort = leaderTargetQty < 0;
                bool isLeaderLong = leaderTargetQty > 0;
                bool isOppositeMarketOrder = (isLeaderShort && delta > 0) || (isLeaderLong && delta < 0);

                if (isOppositeMarketOrder)
                {
                    isBlocked = true;
                    return 0;
                }
            }

            if (currentFollowerQty != 0 && ((currentFollowerQty > 0 && delta < 0) || (currentFollowerQty < 0 && delta > 0)))
            {
                int maxReduce = Math.Abs(currentFollowerQty);
                delta = Math.Sign(delta) * Math.Min(Math.Abs(delta), maxReduce);
            }

            return delta;
        }

#if !TESTING
        public void ReconcileFollowerPosition(Account leaderAccount, Account followerAccount, Instrument instrument)
        {
            if (leaderAccount == null || followerAccount == null || instrument == null) return;

            var leaderPosObj = leaderAccount.Positions.FirstOrDefault(p => p.Instrument == instrument);
            var followerPosObj = followerAccount.Positions.FirstOrDefault(p => p.Instrument == instrument);
            double leaderQty = leaderPosObj != null ? leaderPosObj.Quantity : 0;
            double followerQty = followerPosObj != null ? followerPosObj.Quantity : 0;

            if (Math.Abs(leaderQty) < double.Epsilon)
            {
                if (Math.Abs(followerQty) > double.Epsilon)
                {
                    System.Windows.Application.Current?.Dispatcher.InvokeAsync(() =>
                    {
                        var workingOrders = followerAccount.Orders
                            .Where(o => o.Instrument == instrument && (o.OrderState == OrderState.Working || o.OrderState == OrderState.Submitted))
                            .ToList();
                        foreach (var ord in workingOrders) { try { followerAccount.Cancel(new[] { ord }); } catch {} }
                        try { followerAccount.Flatten(new[] { instrument }); } catch {}
                    });
                }
                return;
            }

            bool directionMismatch = (leaderQty > 0 && followerQty < 0) || (leaderQty < 0 && followerQty > 0);
            if (directionMismatch)
            {
                System.Windows.Application.Current?.Dispatcher.InvokeAsync(() =>
                {
                    // P1-71: this FLATTENS a live follower position and logged to the Output tab
                    // only. A broker action with no audit-log entry is the single worst version of
                    // this defect -- the position disappears and nothing readable says who did it.
                    CopierLog(followerAccount != null ? followerAccount.Name : null,
                        "RECONCILER_DIRECTION_MISMATCH",
                        $"leader is {leaderQty} and follower is {followerQty} on "
                        + $"{(instrument != null ? instrument.FullName : "?")} -- opposite directions, "
                        + "so FLATTENING the follower. This is a broker action taken by the copier.");
                    try { followerAccount.Flatten(new[] { instrument }); } catch {}
                });
            }
        }
#endif

        public List<CopierRelationship> GetRelationships()
        {
            lock (_lock)
            {
                return new List<CopierRelationship>(_relationships);
            }
        }

        /// <summary>
        /// UI1 -- NOT IMPLEMENTED YET. Deliberately returns an EMPTY snapshot so the
        /// eighteen conformance tests compile and FAIL rather than failing to build:
        /// the agent-loop gate matches `expect_green` against the runner's failure
        /// lines and refuses a ticket whose tests are not already red, and a broken
        /// build is not a red test.
        ///
        /// The contract this must satisfy is agent/tickets_ui_snapshot.json (UI1).
        /// Four points that are easy to get wrong and are each a defect this repo has
        /// already paid for:
        ///   1. Enumerate through the SAME path the copier acts on -- the group
        ///      expansion plus `P1-76`'s direct-over-group precedence. A snapshot that
        ///      enumerates differently can report Match while the engine copies
        ///      something else, which is worse than no snapshot.
        ///   2. Derive expected quantity by CALLING `CalculateFollowerQuantity`, never
        ///      by reimplementing it. Note it opens `if (leaderQty <= 0) return 0`, so
        ///      it takes an ABSOLUTE quantity -- pass a signed one for a short leader
        ///      and it silently reports the follower should be flat.
        ///   3. Every metric carries its sample count. A latency rejected by the sanity
        ///      bound must NOT count as a sample; that path deliberately records no
        ///      number, and counting it restores the exact lie `P?-66` was.
        ///   4. THIS MUST NOT MUTATE. No `LoadFromDisk`, no config write, no counter
        ///      reset. `P1-69` destroyed the measurements it was asked to report and
        ///      `P1-75` DISARMED the prop-firm rules -- both were reads that mutated.
        /// </summary>
        public CopierSnapshot GetSnapshot()
        {
            List<CopierRelationship> relationshipsCopy;
            List<CopierGroup> groupsCopy;
            Dictionary<string, int> slippageCountsCopy;
            Dictionary<string, int> latencyCountsCopy;
            Dictionary<string, double> latencyValuesCopy;
            Dictionary<string, double> slippageValuesCopy;

            lock (_lock)
            {
                relationshipsCopy = new List<CopierRelationship>(_relationships);
                groupsCopy = new List<CopierGroup>(_groups);
                slippageCountsCopy = new Dictionary<string, int>(_slippageSampleCounts);
                latencyCountsCopy = new Dictionary<string, int>(_latencySampleCounts);

                latencyValuesCopy = new Dictionary<string, double>();
                slippageValuesCopy = new Dictionary<string, double>();
                foreach (var r in relationshipsCopy)
                {
                    latencyValuesCopy[r.Id] = r.LatencyMs;
                    slippageValuesCopy[r.Id] = r.AvgSlippageTicks;
                }
                foreach (var g in groupsCopy)
                {
                    foreach (var gr in g.ToRelationships())
                    {
                        if (!latencyValuesCopy.ContainsKey(gr.Id))
                            latencyValuesCopy[gr.Id] = gr.LatencyMs;
                        if (!slippageValuesCopy.ContainsKey(gr.Id))
                            slippageValuesCopy[gr.Id] = gr.AvgSlippageTicks;
                    }
                }
            }

            var leaders = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var r in relationshipsCopy)
                leaders.Add(r.LeaderAccountName);
            foreach (var g in groupsCopy)
                leaders.Add(g.LeaderAccountName);

            var activeRels = new List<CopierRelationship>();
            var groupNameByRelId = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var metricIdByRelId = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            foreach (var leader in leaders)
            {
                var active = GetActiveRelationshipsForLeaderFromCopies(leader, relationshipsCopy, groupsCopy, includeQuarantined: true);
                foreach (var rel in active)
                {
                    string groupName = DeriveGroupName(rel, groupsCopy);
                    string canonicalId = ResolveCanonicalRelationshipId(rel, relationshipsCopy);
                    activeRels.Add(CloneRelationship(rel));
                    groupNameByRelId[rel.Id] = groupName;
                    metricIdByRelId[rel.Id] = canonicalId ?? rel.Id;
                }
            }

            Account[] accounts = null;
            try
            {
                accounts = Account.All != null ? Account.All.ToArray() : null;
            }
            catch (Exception ex)
            {
                CopierLog(null, "SNAPSHOT_ACCOUNT_READ_FAILED",
                    string.Format("Failed to read Account.All for snapshot: {0}", ex.Message));
            }

            var positionsByAccount = new Dictionary<string, Position[]>(StringComparer.OrdinalIgnoreCase);
            if (accounts != null)
            {
                foreach (var account in accounts)
                {
                    if (account == null || string.IsNullOrEmpty(account.Name))
                        continue;
                    Position[] positions = null;
                    try
                    {
                        positions = account.Positions != null ? account.Positions.ToArray() : null;
                    }
                    catch (Exception ex)
                    {
                        CopierLog(account.Name, "SNAPSHOT_POSITION_READ_FAILED",
                            string.Format("Failed to read positions for account {0}: {1}", account.Name, ex.Message));
                    }
                    positionsByAccount[account.Name] = positions ?? new Position[0];
                }
            }

            var rows = new List<CopierSnapshotRow>();
            foreach (var rel in activeRels)
            {
                string groupName;
                groupNameByRelId.TryGetValue(rel.Id, out groupName);
                string metricId;
                metricIdByRelId.TryGetValue(rel.Id, out metricId);

                double latencyValue;
                latencyValuesCopy.TryGetValue(metricId, out latencyValue);
                int latencySamples;
                latencyCountsCopy.TryGetValue(metricId, out latencySamples);
                double slippageValue;
                slippageValuesCopy.TryGetValue(metricId, out slippageValue);
                int slippageSamples;
                slippageCountsCopy.TryGetValue(metricId, out slippageSamples);

                rows.AddRange(BuildRowsForRelationship(rel, groupName, latencyValue, latencySamples, slippageValue, slippageSamples, positionsByAccount));
            }

            return new CopierSnapshot
            {
                Rows = rows,
                TakenUtc = DateTime.UtcNow
            };

            List<CopierRelationship> GetActiveRelationshipsForLeaderFromCopies(string leader, List<CopierRelationship> relationships, List<CopierGroup> groups, bool includeQuarantined)
            {
                var result = new List<CopierRelationship>();
                var directFollowers = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

                foreach (var r in relationships)
                {
                    if (!string.Equals(r.LeaderAccountName, leader, StringComparison.OrdinalIgnoreCase))
                        continue;
                    if (!includeQuarantined && r.IsQuarantined)
                        continue;
                    result.Add(r);
                    directFollowers.Add(r.FollowerAccountName);
                }

                foreach (var g in groups)
                {
                    if (!string.Equals(g.LeaderAccountName, leader, StringComparison.OrdinalIgnoreCase))
                        continue;
                    foreach (var gr in g.ToRelationships())
                    {
                        if (!includeQuarantined && gr.IsQuarantined)
                            continue;
                        if (directFollowers.Contains(gr.FollowerAccountName))
                            continue;
                        result.Add(gr);
                    }
                }

                return result;
            }

            string DeriveGroupName(CopierRelationship rel, List<CopierGroup> groups)
            {
                foreach (var g in groups)
                {
                    if (g.FollowerAccounts == null)
                        continue;
                    if (string.Equals(g.LeaderAccountName, rel.LeaderAccountName, StringComparison.OrdinalIgnoreCase)
                        && g.FollowerAccounts.Any(f => string.Equals(f, rel.FollowerAccountName, StringComparison.OrdinalIgnoreCase)))
                        return g.GroupName;
                }
                return null;
            }

            string ResolveCanonicalRelationshipId(CopierRelationship rel, List<CopierRelationship> relationships)
            {
                var canonical = relationships.FirstOrDefault(r => r.Id == rel.Id);
                if (canonical != null)
                    return canonical.Id;
                canonical = relationships.FirstOrDefault(r =>
                    string.Equals(r.LeaderAccountName, rel.LeaderAccountName, StringComparison.OrdinalIgnoreCase) &&
                    string.Equals(r.FollowerAccountName, rel.FollowerAccountName, StringComparison.OrdinalIgnoreCase));
                return canonical != null ? canonical.Id : null;
            }

            CopierRelationship CloneRelationship(CopierRelationship source)
            {
                return new CopierRelationship
                {
                    Id = source.Id,
                    LeaderAccountName = source.LeaderAccountName,
                    FollowerAccountName = source.FollowerAccountName,
                    IsEnabled = source.IsEnabled,
                    ArmedForLive = source.ArmedForLive,
                    Mode = source.Mode,
                    SizingMode = source.SizingMode,
                    QuantityRatio = source.QuantityRatio,
                    FixedLotMode = source.FixedLotMode,
                    FixedLotSize = source.FixedLotSize,
                    AutoSymbolConversion = source.AutoSymbolConversion,
                    PerTickerRatios = source.PerTickerRatios != null
                        ? new Dictionary<string, double>(source.PerTickerRatios, StringComparer.OrdinalIgnoreCase)
                        : new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase),
                    CustomSymbolMappings = source.CustomSymbolMappings != null
                        ? new Dictionary<string, string>(source.CustomSymbolMappings, StringComparer.OrdinalIgnoreCase)
                        : new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase),
                    StealthMode = source.StealthMode,
                    MaxPositionSize = source.MaxPositionSize,
                    DailyLossLimit = source.DailyLossLimit,
                    IsQuarantined = source.IsQuarantined,
                    QuarantineReason = source.QuarantineReason,
                    LatencyMs = source.LatencyMs,
                    AvgSlippageTicks = source.AvgSlippageTicks,
                    MaxSlippageTicks = source.MaxSlippageTicks
                };
            }

            List<CopierSnapshotRow> BuildRowsForRelationship(CopierRelationship rel, string groupName, double latencyValue, int latencySamples, double slippageValue, int slippageSamples, Dictionary<string, Position[]> positionsByAccount)
            {
                var rows = new List<CopierSnapshotRow>();

                Position[] leaderPositions;
                positionsByAccount.TryGetValue(rel.LeaderAccountName, out leaderPositions);
                if (leaderPositions == null)
                    leaderPositions = new Position[0];

                Position[] followerPositions;
                positionsByAccount.TryGetValue(rel.FollowerAccountName, out followerPositions);
                if (followerPositions == null)
                    followerPositions = new Position[0];

                var followerRoots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var fp in followerPositions)
                {
                    string root = GetRootFromPosition(fp);
                    if (!string.IsNullOrEmpty(root))
                        followerRoots.Add(root);
                }

                if (rel.CustomSymbolMappings != null && rel.CustomSymbolMappings.Count > 0)
                {
                    var mappedLeaderRoots = new HashSet<string>(rel.CustomSymbolMappings.Keys, StringComparer.OrdinalIgnoreCase);
                    var mappedFollowerRoots = new HashSet<string>(rel.CustomSymbolMappings.Values, StringComparer.OrdinalIgnoreCase);

                    foreach (var kvp in rel.CustomSymbolMappings)
                    {
                        Position leaderPos = FindPositionByRoot(leaderPositions, kvp.Key);
                        Position followerPos = FindPositionByRoot(followerPositions, kvp.Value);
                        rows.Add(BuildSnapshotRow(rel, groupName, latencyValue, latencySamples, slippageValue, slippageSamples, leaderPos, followerPos, kvp.Key, kvp.Value));
                    }

                    foreach (var root in followerRoots)
                    {
                        if (mappedFollowerRoots.Contains(root))
                            continue;
                        Position leaderPos = FindPositionByRoot(leaderPositions, root);
                        Position followerPos = FindPositionByRoot(followerPositions, root);
                        rows.Add(BuildSnapshotRow(rel, groupName, latencyValue, latencySamples, slippageValue, slippageSamples, leaderPos, followerPos, root, root));
                    }

                    foreach (var lp in leaderPositions)
                    {
                        string root = GetRootFromPosition(lp);
                        if (string.IsNullOrEmpty(root))
                            continue;
                        if (mappedLeaderRoots.Contains(root))
                            continue;
                        if (followerRoots.Contains(root))
                            continue;
                        rows.Add(BuildSnapshotRow(rel, groupName, latencyValue, latencySamples, slippageValue, slippageSamples, lp, null, root, root));
                    }
                }
                else
                {
                    foreach (var root in followerRoots)
                    {
                        Position leaderPos = FindPositionByRoot(leaderPositions, root);
                        Position followerPos = FindPositionByRoot(followerPositions, root);
                        rows.Add(BuildSnapshotRow(rel, groupName, latencyValue, latencySamples, slippageValue, slippageSamples, leaderPos, followerPos, root, root));
                    }

                    foreach (var lp in leaderPositions)
                    {
                        string root = GetRootFromPosition(lp);
                        if (string.IsNullOrEmpty(root))
                            continue;
                        if (followerRoots.Contains(root))
                            continue;
                        rows.Add(BuildSnapshotRow(rel, groupName, latencyValue, latencySamples, slippageValue, slippageSamples, lp, null, root, root));
                    }

                    if (rows.Count == 0)
                        rows.Add(BuildSnapshotRow(rel, groupName, latencyValue, latencySamples, slippageValue, slippageSamples, null, null, null, null));
                }

                return rows;
            }

            CopierSnapshotRow BuildSnapshotRow(CopierRelationship rel, string groupName, double latencyValue, int latencySamples, double slippageValue, int slippageSamples, Position leaderPos, Position followerPos, string leaderRoot, string followerRoot)
            {
                Instrument instrument = leaderPos != null ? leaderPos.Instrument : (followerPos != null ? followerPos.Instrument : null);
                string rawSymbol = instrument != null ? instrument.FullName : leaderRoot;

                MarketPosition leaderSide = leaderPos != null ? leaderPos.MarketPosition : MarketPosition.Flat;
                int leaderQty = leaderPos != null ? Math.Abs(leaderPos.Quantity) : 0;

                MarketPosition actualSide = followerPos != null ? followerPos.MarketPosition : MarketPosition.Flat;
                int actualQty = followerPos != null ? Math.Abs(followerPos.Quantity) : 0;


                bool expectedIsClamped;
                int expectedQty;
                MarketPosition expectedSide;

                if (leaderQty > 0 && !string.IsNullOrEmpty(rawSymbol))
                {
                    bool rawClamped;
                    int rawTarget = CalculateFollowerQuantity(rel, leaderQty, rawSymbol, 0, false, out rawClamped);

                    bool isExit;
                    if (actualSide == MarketPosition.Flat)
                        isExit = false;
                    else if (actualSide != leaderSide)
                        isExit = true;
                    else
                        isExit = actualQty > rawTarget;

                    expectedQty = CalculateFollowerQuantity(rel, leaderQty, rawSymbol, actualQty, isExit, out expectedIsClamped);
                    expectedSide = expectedQty > 0 ? leaderSide : MarketPosition.Flat;
                }
                else
                {
                    expectedQty = 0;
                    expectedSide = MarketPosition.Flat;
                    expectedIsClamped = false;
                }

                string ratioRoot = !string.IsNullOrEmpty(leaderRoot) ? leaderRoot : GetRootFromInstrument(instrument);
                double effectiveRatio = !string.IsNullOrEmpty(ratioRoot) ? ComputeEffectiveRatio(rel, ratioRoot) : 0.0;

                CopierConformance verdict;
                if (rel.IsQuarantined)
                    verdict = CopierConformance.Quarantined;
                else if (leaderSide == MarketPosition.Flat && actualSide != MarketPosition.Flat)
                    verdict = CopierConformance.Orphan;
                else if (rel.IsEnabled && !rel.ArmedForLive)
                    verdict = CopierConformance.Shadow;
                else
                {
                    MarketPosition effectiveExpectedSide = expectedSide;
                    int effectiveExpectedQty = expectedQty;
                    if (expectedIsClamped && expectedQty == 0)
                    {
                        effectiveExpectedSide = actualSide;
                        effectiveExpectedQty = actualQty;
                    }

                    if (effectiveExpectedSide != actualSide || effectiveExpectedQty != actualQty)
                        verdict = CopierConformance.Diverged;
                    else if (leaderSide == MarketPosition.Flat && actualSide == MarketPosition.Flat)
                        verdict = CopierConformance.Idle;
                    else
                        verdict = CopierConformance.Match;
                }

                return new CopierSnapshotRow
                {
                    RelationshipId = rel.Id,
                    LeaderAccountName = rel.LeaderAccountName,
                    FollowerAccountName = rel.FollowerAccountName,
                    GroupName = groupName,
                    InstrumentFullName = instrument != null ? instrument.FullName : null,
                    SizingMode = rel.SizingMode,
                    EffectiveRatio = effectiveRatio,
                    IsEnabled = rel.IsEnabled,
                    ArmedForLive = rel.ArmedForLive,
                    IsQuarantined = rel.IsQuarantined,
                    QuarantineReason = rel.QuarantineReason,
                    StealthMode = rel.StealthMode,
                    LeaderSide = leaderSide,
                    LeaderQuantity = leaderQty,
                    ExpectedSide = expectedSide,
                    ExpectedQuantity = expectedQty,
                    ExpectedIsClamped = expectedIsClamped,
                    ActualSide = actualSide,
                    ActualQuantity = actualQty,
                    Latency = new CopierMetric { Value = latencyValue, Samples = latencySamples },
                    Slippage = new CopierMetric { Value = slippageValue, Samples = slippageSamples },
                    Verdict = verdict
                };
            }

            string GetRootFromPosition(Position p)
            {
                if (p == null || p.Instrument == null || p.Instrument.MasterInstrument == null)
                    return null;
                return p.Instrument.MasterInstrument.Name;
            }

            string GetRootFromInstrument(Instrument instrument)
            {
                if (instrument == null || instrument.MasterInstrument == null)
                    return null;
                return instrument.MasterInstrument.Name;
            }

            Position FindPositionByRoot(Position[] positions, string root)
            {
                if (positions == null || string.IsNullOrEmpty(root))
                    return null;
                foreach (var p in positions)
                {
                    if (p == null)
                        continue;
                    string pRoot = GetRootFromPosition(p);
                    if (string.Equals(pRoot, root, StringComparison.OrdinalIgnoreCase))
                        return p;
                }
                return null;
            }

            double ComputeEffectiveRatio(CopierRelationship rel, string symbolRoot)
            {
                if (rel.SizingMode == CopierSizingMode.PerTickerMatrix)
                {
                    double ratio;
                    if (rel.PerTickerRatios != null && rel.PerTickerRatios.TryGetValue(symbolRoot, out ratio)
                        && !double.IsNaN(ratio) && !double.IsInfinity(ratio) && ratio > 0.0)
                        return ratio;
                    return 0.0;
                }

                if (rel.FixedLotMode || rel.SizingMode == CopierSizingMode.FixedLot)
                    return 0.0;

                if (rel.SizingMode == CopierSizingMode.NetLiquidationRatio || rel.SizingMode == CopierSizingMode.AvailableCashPercent)
                    return 0.0;

                double absRatio = Math.Abs(rel.QuantityRatio);
                if (rel.PerTickerRatios != null && rel.PerTickerRatios.TryGetValue(symbolRoot, out double tickerRatio))
                    absRatio = Math.Abs(tickerRatio);

                double symbolMultiplier = 1.0;
                if (rel.AutoSymbolConversion)
                {
                    if (symbolRoot == "NQ" || symbolRoot == "ES" || symbolRoot == "YM" || symbolRoot == "CL" || symbolRoot == "GC" || symbolRoot == "RTY")
                        symbolMultiplier = 10.0;
                    else if (symbolRoot == "MNQ" || symbolRoot == "MES" || symbolRoot == "MYM" || symbolRoot == "MCL" || symbolRoot == "MGC" || symbolRoot == "M2K")
                        symbolMultiplier = 0.1;
                }

                return absRatio * symbolMultiplier;
            }
        }

        // ── P1-76: a follower belongs to a direct relationship OR a group, never both ──
        //
        // Operator decision, 2026-08-13, from the observation that it was "not clear what
        // configuration applies and for what". It was not clear in the CODE either:
        // GetActiveRelationshipsForLeader added directs, expanded groups, then deduplicated
        // with .First(), so direct won purely because directs went into the list first.
        // Nothing named that and no test pinned it -- reordering two statements would have
        // flipped every group's ratio, sizing mode, conversion flag and position cap over
        // every direct relationship, silently, with the suite still green.
        //
        // ⚠️ The asymmetry below is deliberate and load-bearing:
        //
        //   OPERATOR WRITES REFUSE.  ApplyRelationshipRequest, ApplyGroupRequest and
        //   AddFollowerToGroup will not create an overlap. That is the whole point: one
        //   place to look for what applies to a follower.
        //
        //   LoadFromDisk TOLERATES AND REPORTS.  A load that refused would silently drop
        //   config the operator can plainly see in the file, which is exactly P?-64's and
        //   P2-41's failure shape and worse than the overlap it prevents. So a hand-edited
        //   file loads intact, logs CONFIG_OVERLAP_DETECTED per overlap, and exposes the
        //   conflict through DetectConfigConflicts() for the API and the UI to render.
        //
        // Membership, not effect: a DISABLED group still reserves its followers. Enabling a
        // group is one click, and that click must not be the thing that creates the overlap.

        public class CopierConfigConflict
        {
            public string LeaderAccount { get; set; }
            public string FollowerAccount { get; set; }
            public string GroupName { get; set; }
            public string Detail { get; set; }
        }

        /// <summary>
        /// Every follower covered by BOTH a direct relationship and a group for the same
        /// leader. Empty is the healthy state. Non-empty means a hand-edited config file:
        /// the write paths cannot produce this.
        /// </summary>
        public List<CopierConfigConflict> DetectConfigConflicts()
        {
            var conflicts = new List<CopierConfigConflict>();
            lock (_lock)
            {
                foreach (var grp in _groups)
                {
                    if (grp.FollowerAccounts == null || string.IsNullOrWhiteSpace(grp.LeaderAccountName)) continue;
                    foreach (var follower in grp.FollowerAccounts)
                    {
                        if (string.IsNullOrWhiteSpace(follower)) continue;
                        bool hasDirect = _relationships.Any(r =>
                            r.LeaderAccountName.Equals(grp.LeaderAccountName, StringComparison.OrdinalIgnoreCase) &&
                            r.FollowerAccountName.Equals(follower, StringComparison.OrdinalIgnoreCase));
                        if (!hasDirect) continue;

                        conflicts.Add(new CopierConfigConflict
                        {
                            LeaderAccount = grp.LeaderAccountName,
                            FollowerAccount = follower,
                            GroupName = grp.GroupName,
                            Detail = string.Format(
                                "'{0}' is covered by BOTH a direct relationship and group '{1}' under leader '{2}'. "
                                + "The DIRECT relationship applies and the group's settings are ignored for this "
                                + "follower. Remove one of the two. Write paths refuse to create this; it can only "
                                + "come from editing copier_config.json by hand.",
                                follower, grp.GroupName, grp.LeaderAccountName),
                        });
                    }
                }
            }
            return conflicts;
        }

        /// <summary>
        /// Caller must NOT hold _lock. Returns the group that already reserves this
        /// follower, or null when the pairing is free.
        /// </summary>
        private CopierGroup GroupReserving(string leaderAccount, string followerAccount)
        {
            if (string.IsNullOrWhiteSpace(leaderAccount) || string.IsNullOrWhiteSpace(followerAccount)) return null;
            lock (_lock)
            {
                return _groups.FirstOrDefault(g =>
                    !string.IsNullOrWhiteSpace(g.LeaderAccountName) &&
                    g.LeaderAccountName.Equals(leaderAccount, StringComparison.OrdinalIgnoreCase) &&
                    g.FollowerAccounts != null &&
                    g.FollowerAccounts.Any(f => !string.IsNullOrWhiteSpace(f)
                                                && f.Equals(followerAccount, StringComparison.OrdinalIgnoreCase)));
            }
        }

        /// <summary>
        /// Caller must NOT hold _lock. True when a direct relationship already covers this
        /// leader/follower pairing.
        /// </summary>
        private bool DirectRelationshipExists(string leaderAccount, string followerAccount)
        {
            if (string.IsNullOrWhiteSpace(leaderAccount) || string.IsNullOrWhiteSpace(followerAccount)) return false;
            lock (_lock)
            {
                return _relationships.Any(r =>
                    r.LeaderAccountName.Equals(leaderAccount, StringComparison.OrdinalIgnoreCase) &&
                    r.FollowerAccountName.Equals(followerAccount, StringComparison.OrdinalIgnoreCase));
            }
        }

        public void UpsertGroup(CopierGroup group, bool confirmLive = false)
        {
            if (group == null || string.IsNullOrWhiteSpace(group.GroupName)) return;

            if (group.ArmedForLive && !confirmLive)
            {
                group.ArmedForLive = false;
            }

            lock (_lock)
            {
                var existing = _groups.FirstOrDefault(g => 
                    g.GroupName.Equals(group.GroupName, StringComparison.OrdinalIgnoreCase));
                
                if (existing != null)
                {
                    _groups.Remove(existing);
                }
                _groups.Add(group);
            }
        }

        public void RemoveGroup(string groupName)
        {
            if (string.IsNullOrWhiteSpace(groupName)) return;
            lock (_lock)
            {
                _groups.RemoveAll(g => g.GroupName.Equals(groupName, StringComparison.OrdinalIgnoreCase));
            }
        }

        public List<CopierGroup> GetGroups()
        {
            lock (_lock)
            {
                return new List<CopierGroup>(_groups);
            }
        }

        public CopierGroup GetGroup(string groupName)
        {
            if (string.IsNullOrWhiteSpace(groupName)) return null;
            lock (_lock)
            {
                return _groups.FirstOrDefault(g => g.GroupName.Equals(groupName, StringComparison.OrdinalIgnoreCase));
            }
        }

        public bool AddFollowerToGroup(string groupName, string followerAccount)
        {
            if (string.IsNullOrWhiteSpace(groupName) || string.IsNullOrWhiteSpace(followerAccount)) return false;
            lock (_lock)
            {
                var grp = _groups.FirstOrDefault(g => g.GroupName.Equals(groupName, StringComparison.OrdinalIgnoreCase));
                if (grp == null) return false;

                // P1-76, the mirror of the check in ApplyRelationshipRequest. Read inline
                // rather than through DirectRelationshipExists because _lock is already held
                // here and it is re-entrant -- calling the helper would work, but a re-entrant
                // acquisition that reads as an independent one is how P1-35 hid.
                var clash = _relationships.FirstOrDefault(r =>
                    !string.IsNullOrWhiteSpace(grp.LeaderAccountName) &&
                    r.LeaderAccountName.Equals(grp.LeaderAccountName, StringComparison.OrdinalIgnoreCase) &&
                    r.FollowerAccountName.Equals(followerAccount, StringComparison.OrdinalIgnoreCase));
                if (clash != null)
                {
                    CopierLog(followerAccount, "CONFIG_OVERLAP_REFUSED", string.Format(
                        "refused to add '{0}' to group '{1}': it already has a direct relationship under leader "
                        + "'{2}'. Remove that relationship first, or leave it out of the group. Note the direct "
                        + "relationship is NOT modified by this refusal.",
                        followerAccount, groupName, grp.LeaderAccountName));
                    return false;
                }

                if (grp.FollowerAccounts == null) grp.FollowerAccounts = new List<string>();
                if (!grp.FollowerAccounts.Any(f => f.Equals(followerAccount, StringComparison.OrdinalIgnoreCase)))
                {
                    grp.FollowerAccounts.Add(followerAccount.Trim());
                }
                return true;
            }
        }

        public bool RemoveFollowerFromGroup(string groupName, string followerAccount)
        {
            if (string.IsNullOrWhiteSpace(groupName) || string.IsNullOrWhiteSpace(followerAccount)) return false;
            lock (_lock)
            {
                var grp = _groups.FirstOrDefault(g => g.GroupName.Equals(groupName, StringComparison.OrdinalIgnoreCase));
                if (grp == null || grp.FollowerAccounts == null) return false;

                grp.FollowerAccounts.RemoveAll(f => f.Equals(followerAccount, StringComparison.OrdinalIgnoreCase));
                return true;
            }
        }

        /// <param name="includeQuarantined">
        /// P1-22: pass true for an EXIT copy. A quarantined relationship must still be able to
        /// close the follower out; blocking its exits strands it in a position the leader has
        /// already left. Defaults to false so every existing caller keeps the old behaviour.
        /// </param>
        public List<CopierRelationship> GetActiveRelationshipsForLeader(string leaderAccount, bool includeQuarantined = false)
        {
            var result = new List<CopierRelationship>();
            if (string.IsNullOrWhiteSpace(leaderAccount)) return result;

            lock (_lock)
            {
                var direct = _relationships.Where(r =>
                    r.IsEnabled &&
                    (includeQuarantined || !r.IsQuarantined) &&
                    r.LeaderAccountName.Equals(leaderAccount, StringComparison.OrdinalIgnoreCase));
                result.AddRange(direct);

                var matchingGroups = _groups.Where(g => 
                    g.IsEnabled && 
                    g.LeaderAccountName.Equals(leaderAccount, StringComparison.OrdinalIgnoreCase));

                foreach (var group in matchingGroups)
                {
                    foreach (var rel in group.ToRelationships())
                    {
                        var directRel = _relationships.FirstOrDefault(r =>
                            r.LeaderAccountName.Equals(leaderAccount, StringComparison.OrdinalIgnoreCase) &&
                            r.FollowerAccountName.Equals(rel.FollowerAccountName, StringComparison.OrdinalIgnoreCase));

                        // P1-76: THE DIRECT RELATIONSHIP WINS. Stated here rather than left to
                        // emerge from the order of the two AddRange blocks plus .First() below,
                        // which is how it worked until 2026-08-13 -- reordering two statements
                        // would have flipped every group's ratio, sizing mode, conversion flag
                        // and position cap over every direct relationship, silently, with the
                        // whole suite green. The write paths now refuse to create this overlap
                        // at all; this branch only covers a hand-edited config file, which
                        // LoadFromDisk deliberately tolerates and reports.
                        //
                        // A direct relationship that is DISABLED or QUARANTINED still wins and
                        // still suppresses the group entry. Both of those states mean "this
                        // follower does not copy right now"; a group silently resuming copying
                        // for it would be the opposite of what the operator asked for. This
                        // REPLACES a narrower guard that skipped only the quarantined case --
                        // that guard is now subsumed, not lost, and the quarantine behaviour is
                        // still pinned by the P1-22 quarantine test.
                        if (directRel != null)
                        {
                            continue;
                        }

                        result.Add(rel);
                    }
                }

                // Deduplicate by FollowerAccountName so an account doesn't receive duplicate
                // orders. This is a SAFETY property and stays even though P1-76 makes the
                // direct-vs-group case unreachable: it still catches the SAME follower listed
                // in two different groups, whose resolution is otherwise _groups list order.
                result = result
                    .GroupBy(r => r.FollowerAccountName, StringComparer.OrdinalIgnoreCase)
                    .Select(g => g.First())
                    .ToList();
            }
            return result;
        }

        public string TranslateSymbol(string rawSymbol, CopierRelationship rel = null)
        {
            if (string.IsNullOrEmpty(rawSymbol)) return rawSymbol;

            // P1-23: substitute the parsed ROOT only, and match case-insensitively.
            // The previous implementation ran rawSymbol.Replace(root, target) across the whole
            // string, which is fragile against any later occurrence of the root, and compared an
            // upper-cased root against the raw string -- so a lower-case instrument name matched
            // nothing, returned untranslated, and the copy silently went to the LEADER's contract
            // on a follower configured for the converted one.
            int split = rawSymbol.IndexOf(' ');
            string root = (split >= 0 ? rawSymbol.Substring(0, split) : rawSymbol).ToUpper();
            string remainder = split >= 0 ? rawSymbol.Substring(split) : string.Empty;

            // 1. Relationship custom overrides. An explicit mapping is honoured in
            // every sizing mode, INCLUDING PerTickerMatrix -- that is slice 2.
            //
            // Slice 1 returned the symbol untranslated here when a matrix-mode
            // mapping named a different root, so the sizing branch could refuse
            // the entry. Both halves of that refusal are gone together: leaving
            // one would route the copy to one instrument and size it in another,
            // which is the defect slice 1 was fixing.
            //
            // Note this is deliberately NOT gated on AutoSymbolConversion. That
            // flag governs the automatic mini/micro table below, not an override
            // the operator wrote out by hand.
            if (rel != null && rel.CustomSymbolMappings != null
                && rel.CustomSymbolMappings.TryGetValue(root, out var customTarget)
                && !string.IsNullOrEmpty(customTarget))
            {
                return customTarget.ToUpper() + remainder;
            }

            // 2. Bidirectional Mini <-> Micro default matrix.
            // When SizingMode is PerTickerMatrix, auto conversion is DISABLED to enforce
            // same-instrument sizing. Cross-instrument mapping must be done via explicit
            // CustomSymbolMappings (which will be refused in matrix mode), not the auto table.
            if (rel == null || (rel.AutoSymbolConversion && rel.SizingMode != CopierSizingMode.PerTickerMatrix))
            {
                string mapped = null;
                switch (root)
                {
                    case "NQ":  mapped = "MNQ"; break;
                    case "ES":  mapped = "MES"; break;
                    case "YM":  mapped = "MYM"; break;
                    case "CL":  mapped = "MCL"; break;
                    case "GC":  mapped = "MGC"; break;
                    case "RTY": mapped = "M2K"; break;
                    case "MNQ": mapped = "NQ";  break;
                    case "MES": mapped = "ES";  break;
                    case "MYM": mapped = "YM";  break;
                    case "MCL": mapped = "CL";  break;
                    case "MGC": mapped = "GC";  break;
                    case "M2K": mapped = "RTY"; break;
                }
                if (mapped != null) return mapped + remainder;
            }

            return rawSymbol;
        }

        public int CalculateFollowerQuantity(CopierRelationship rel, int leaderQty, string rawSymbol, int currentFollowerPosition, bool isExit, out bool isClamped)
        {
            isClamped = false;
            if (leaderQty <= 0) return 0;

            // Guard against null relationship - convenience overload at line 536 can pass null
            if (rel == null)
            {
                return 0;
            }

            int rawCopyQty;

            // P1-23: PerTickerMatrix sizing mode - SAME INSTRUMENT ONLY
            // This must be evaluated BEFORE NetLiquidationRatio and QuantityRatio branches
            // to prevent fall-through defects. Cross-instrument mapping via CustomSymbolMappings
            // is REFUSED in matrix mode (slice 2), even if operator configured it deliberately.
            if (rel.SizingMode == CopierSizingMode.PerTickerMatrix)
            {
                string symbol = rawSymbol.Split(' ')[0].ToUpper();

                // SLICE 2. One rule is (leader root -> follower root, ratio), and
                // BOTH halves are keyed by the LEADER root:
                //
                //     CustomSymbolMappings["MNQ"] = "MES"   <- where it goes
                //     PerTickerRatios["MNQ"]      = 3.0     <- how many
                //
                // So there is no cross-instrument BRANCH any more, and that is the
                // design rather than a simplification: a separate branch is how the
                // instrument and the quantity came to be decided from two different
                // keys in the first place (slice 1's defect 2, which routed an MES
                // leader fill to ES while sizing it in MES contracts). The lookup
                // below is the same lookup for same- and cross-instrument rules.
                //
                // A ratio keyed by the FOLLOWER root is therefore NOT a rule. It
                // fails closed like any other missing rule -- looking it up under
                // the mapped root as a fallback would rebuild defect 2 as a feature.
                double ratio = 0.0;
                bool hasRatio = false;

                if (rel.PerTickerRatios != null && rel.PerTickerRatios.TryGetValue(symbol, out ratio))
                {
                    // Validate ratio: NaN, Infinity, zero, and negative are all treated as no rule
                    // A negative ratio is a REFUSAL, not an absolute value - Math.Abs must not apply
                    if (!double.IsNaN(ratio) && !double.IsInfinity(ratio) && ratio > 0.0)
                    {
                        hasRatio = true;
                    }
                }

                if (!hasRatio)
                {
                    // No usable ratio: fail closed on entries, never on exits
                    if (!isExit)
                    {
                        string mappedTo = null;
                        if (rel.CustomSymbolMappings != null
                            && rel.CustomSymbolMappings.TryGetValue(symbol, out var mappedRoot)
                            && !string.IsNullOrEmpty(mappedRoot)
                            && mappedRoot.ToUpper() != symbol)
                        {
                            mappedTo = mappedRoot.ToUpper();
                        }

                        NinjaTrader.Code.Output.Process(
                            "[CopierEngine] BLOCKED entry copy: PerTickerMatrix has no rule for " + symbol + ". "
                            + "Refusing to size " + rel.LeaderAccountName + " -> " + rel.FollowerAccountName
                            + " rather than silently copying unscaled. Add a PerTickerRatios entry or use QuantityRatio/FixedLot."
                            + (mappedTo == null
                                ? string.Empty
                                : " NOTE: " + symbol + " is mapped to " + mappedTo + ", so the ratio must be keyed by "
                                  + symbol + " (the LEADER root), not " + mappedTo + "."),
                            PrintTo.OutputTab1);
                        isClamped = true;
                        return 0;
                    }
                    // Exit with no rule: mirror leaderQty, let existing exit clamp handle it.
                    //
                    // Reviewed and kept deliberately. A PARTIAL leader exit can
                    // therefore flatten the follower completely -- leader out of 5 of
                    // 10, follower holding 1, clamp caps the mirrored 5 at 1. That is
                    // accepted: on this path there is no usable ratio BY DEFINITION,
                    // so there is nothing to scale the exit by, and a flat follower is
                    // safer than one stranded in a position the leader has left. The
                    // copier fails closed on entries and never on exits.
                    rawCopyQty = leaderQty;
                }
                else
                {
                    // Compute quantity: round(leaderQty * ratio) with AwayFromZero, NO symbolMultiplier
                    // The ratio IS the contract count in the follower's instrument
                    rawCopyQty = (int)Math.Round(leaderQty * ratio, MidpointRounding.AwayFromZero);

                    // A ratio that rounds to zero is also a refusal on entry
                    if (rawCopyQty < 1 && !isExit)
                    {
                        NinjaTrader.Code.Output.Process(
                            "[CopierEngine] BLOCKED entry copy: PerTickerMatrix ratio " + ratio + " for " + symbol
                            + " rounds to 0 with leaderQty " + leaderQty + ". Refusing rather than silently skipping. "
                            + "Adjust ratio or use QuantityRatio/FixedLot.",
                            PrintTo.OutputTab1);
                        isClamped = true;
                        return 0;
                    }

                    // An exit that rounds below one contract is deliberately NOT
                    // special-cased here. The shared sub-one-contract guard below
                    // already floors an exit to 1 when the follower holds a
                    // position, and returns 0 when it holds none -- and a local
                    // copy of that rule reached the same answer by both paths,
                    // which is how a redundant guard hides a later divergence.
                }
            }
            else if (rel.FixedLotMode || rel.SizingMode == CopierSizingMode.FixedLot)
            {
                // Fixed-lot: entries use the configured lot size; exits mirror the leader's exit quantity.
                rawCopyQty = isExit ? leaderQty : rel.FixedLotSize;
            }
            else if (rel.SizingMode == CopierSizingMode.NetLiquidationRatio
                  || rel.SizingMode == CopierSizingMode.AvailableCashPercent)
            {
                // P1-23: these are declared in CopierSizingMode but never implemented. They used
                // to fall through to the QuantityRatio branch, so a small follower configured for
                // equity-scaling silently received the FULL leader size -- the P0-6 over-size
                // failure arriving through the config instead of the conversion matrix.
                //
                // Fail closed on ENTRIES rather than guess at a size. Never on exits: blocking an
                // exit strands the follower in a position the leader has already left, which is
                // the P0-5 failure and is worse than an unscaled one.
                if (!isExit)
                {
                    NinjaTrader.Code.Output.Process(
                        $"[CopierEngine] BLOCKED entry copy: sizing mode {rel.SizingMode} is declared but not implemented. "
                        + $"Refusing to size {rel.LeaderAccountName} -> {rel.FollowerAccountName} rather than silently copying 1:1. "
                        + "Use QuantityRatio or FixedLot.", PrintTo.OutputTab1);
                    isClamped = true;
                    return 0;
                }
                rawCopyQty = leaderQty;
            }
            else
            {
                // QuantityRatio mode (default)
                double absRatio = Math.Abs(rel.QuantityRatio);
                string symbol = rawSymbol.Split(' ')[0].ToUpper();

                // 1. Check Per-Ticker Ratio Overrides
                if (rel.PerTickerRatios != null && rel.PerTickerRatios.TryGetValue(symbol, out double tickerRatio))
                {
                    absRatio = Math.Abs(tickerRatio);
                }

                // 2. Bidirectional Symbol Multiplier (Mini -> Micro 10x, Micro -> Mini 0.1x)
                double symbolMultiplier = 1.0;
                if (rel.AutoSymbolConversion)
                {
                    if (symbol == "NQ" || symbol == "ES" || symbol == "YM" || symbol == "CL" || symbol == "GC" || symbol == "RTY")
                    {
                        symbolMultiplier = 10.0; // Mini -> Micro
                    }
                    else if (symbol == "MNQ" || symbol == "MES" || symbol == "MYM" || symbol == "MCL" || symbol == "MGC" || symbol == "M2K")
                    {
                        symbolMultiplier = 0.1; // Micro -> Mini
                    }
                }

                rawCopyQty = (int)Math.Round(leaderQty * absRatio * symbolMultiplier);
            }

            if (rawCopyQty < 1)
            {
                // Entries: skip. Flooring a sub-one-contract conversion up to 1 is
                // exactly the P0-6 notional blowout (1 MNQ -> 1 NQ is 10x).
                //
                // Exits are the opposite case and must NOT be skipped. Rounding an
                // exit down to 0 strands the follower in a position the leader has
                // already left, and because every partial exit rounds down
                // independently the position may never close at all: a leader who
                // entered 10 MNQ (follower: 1 NQ) and exits in any increment below
                // 10 produces 0 each time -- note Math.Round(0.5) is 0 under
                // banker's rounding, so even a 5+5 exit strands it. Exit at least
                // one contract whenever the follower actually holds one; the clamp
                // below caps it at the real position size, so this can only reduce.
                if (!isExit || currentFollowerPosition == 0)
                {
                    isClamped = false;
                    return 0;
                }
                rawCopyQty = 1;
            }

            if (isExit)
            {
                int positionSize = Math.Abs(currentFollowerPosition);
                if (rawCopyQty > positionSize)
                {
                    isClamped = positionSize > 0;
                    rawCopyQty = positionSize;
                }
                return Math.Max(0, rawCopyQty);
            }

            // Position-level Clamping: Cap against follower's resulting total position size
            int availableCapacity = Math.Max(0, rel.MaxPositionSize - Math.Abs(currentFollowerPosition));
            int finalQty = Math.Min(rawCopyQty, availableCapacity);

            if (rawCopyQty > availableCapacity)
            {
                isClamped = true;
            }

            return Math.Max(0, finalQty);
        }

        public int CalculateFollowerQuantity(CopierRelationship rel, int leaderQty, string rawSymbol, bool isExit = false)
        {
            return CalculateFollowerQuantity(rel, leaderQty, rawSymbol, 0, isExit, out _);
        }

        private bool DeduplicateExecutionId(string execId)
        {
            if (string.IsNullOrEmpty(execId)) return false;
            lock (_lock)
            {
                if (_copiedExecutionIds.Contains(execId)) return true;

                _copiedExecutionIds.Add(execId);
                _executionIdQueue.Enqueue(execId);
                while (_executionIdQueue.Count > MaxExecutionCacheSize)
                {
                    string oldest = _executionIdQueue.Dequeue();
                    _copiedExecutionIds.Remove(oldest);
                }
                return false;
            }
        }

        // The canonical field name for each accepted alias. `leaderAccount` is a
        // different NAME from `LeaderAccountName`, not a different case of it, so
        // Json.NET will not map it on its own (settled in session 14, §4x).
        //
        // This lived inside LoadFromDisk until session 15. It is static now because
        // the MCP bridge needs exactly the same normalisation, and while it was a
        // captured local the bridge could not reach it -- so the bridge hand-wrote a
        // field list instead, which is the whole of slice 3b's defect.
        private static readonly Dictionary<string, string> ConfigAliasMap = BuildConfigAliasMap();

        private static Dictionary<string, string> BuildConfigAliasMap()
        {
            var aliasMap = new Dictionary<string, string>
            {
                { "leaderAccount", "LeaderAccountName" },
                { "followerAccount", "FollowerAccountName" },
                { "groupName", "GroupName" },
                { "followerAccounts", "FollowerAccounts" }
            };
            foreach (string canonical in new[]
            {
                "Id", "LeaderAccountName", "FollowerAccountName", "IsEnabled", "ArmedForLive",
                "QuantityRatio", "FixedLotMode", "FixedLotSize", "AutoSymbolConversion",
                "MaxPositionSize", "DailyLossLimit", "IsQuarantined", "MaxSlippageTicks",
                "SizingMode", "Mode", "PerTickerRatios", "CustomSymbolMappings", "StealthMode",
                "GroupName", "FollowerAccounts"
            })
            {
                string alias = char.ToLowerInvariant(canonical[0]) + canonical.Substring(1);
                if (!aliasMap.ContainsKey(alias))
                    aliasMap.Add(alias, canonical);
            }
            return aliasMap;
        }

        public void LoadFromDisk(string filePath)
        {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath)) return;

            try
            {
                string json = File.ReadAllText(filePath);
                var jRoot = JObject.Parse(json);

                lock (_lock)
                {
                    _relationships.Clear();
                    _groups.Clear();

                    var relsObj = jRoot["Relationships"] as JObject ?? jRoot["relationships"] as JObject;
                    var grpsObj = jRoot["Groups"] as JObject ?? jRoot["groups"] as JObject;
                    bool hasStructuredSections = relsObj != null || grpsObj != null;

                    if (hasStructuredSections)
                    {
                        if (relsObj != null)
                        {
                            foreach (var kv in relsObj)
                            {
                                if (kv.Value is JObject jObj && TryParseRelationship(jObj, kv.Key, false, out var rel))
                                    _relationships.Add(rel);
                            }
                        }

                        if (grpsObj != null)
                        {
                            foreach (var kv in grpsObj)
                            {
                                if (kv.Value is JObject jObj && TryParseGroup(jObj, kv.Key, out var grp))
                                    _groups.Add(grp);
                            }
                        }
                    }
                    else
                    {
                        var dict = JsonConvert.DeserializeObject<Dictionary<string, JObject>>(json);
                        if (dict != null)
                        {
                            foreach (var kv in dict)
                            {
                                if (TryParseRelationship(kv.Value, kv.Key, true, out var rel))
                                    _relationships.Add(rel);
                            }
                        }
                    }
                }

                // P1-76. A load TOLERATES an overlap and REPORTS it; it must never resolve one
                // by dropping config, because operator config vanishing without an error is
                // exactly P?-64's and P2-41's failure shape and is worse than the overlap.
                // Reported OUTSIDE the lock: CopierLog reaches RiskGuardAddOn.LogFromComponent,
                // and holding _lock across another component's logging is the lock-scope rule
                // this project has paid for repeatedly (P1-10, P1-43).
                foreach (var conflict in DetectConfigConflicts())
                {
                    CopierLog(conflict.FollowerAccount, "CONFIG_OVERLAP_DETECTED", conflict.Detail);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[LoadFromDisk EXCEPTION] {ex}");
            }
        }

        // ---- slice 3a's config normalisation, lifted to statics in slice 3b ----
        // These were local functions inside LoadFromDisk. They are unchanged in
        // behaviour; the only difference is that they are now reachable from the
        // MCP bridge, which is the point. `internal` and not `public`: the addons
        // and the test harness compile into one assembly, so the tests can EXECUTE
        // these rather than assert on source text, without widening the API.

        internal static bool TryParseRelationship(JObject source, string key, bool isFlatLegacy, out CopierRelationship rel)
        {
            rel = new CopierRelationship();
            try
            {
                var normalized = NormalizeConfigObject(source);
                normalized = RemoveUnknownEnums(normalized, typeof(CopierRelationship));

                if (!normalized.ContainsKey("LeaderAccountName"))
                    normalized["LeaderAccountName"] = isFlatLegacy ? key : (key.Contains("_") ? key.Split('_')[0] : key);
                if (!normalized.ContainsKey("FollowerAccountName"))
                {
                    if (isFlatLegacy || !key.Contains("_"))
                    {
                        Console.WriteLine($"[LoadFromDisk] Skipping invalid relationship '{key}': could not derive FollowerAccountName from key.");
                        rel = null;
                        return false;
                    }
                    normalized["FollowerAccountName"] = key.Split('_')[1];
                }

                JsonConvert.PopulateObject(normalized.ToString(), rel);
                rel.PerTickerRatios = EnsureOrdinalIgnoreCase(rel.PerTickerRatios);
                rel.CustomSymbolMappings = EnsureOrdinalIgnoreCase(rel.CustomSymbolMappings);

                if (string.IsNullOrEmpty(rel.Id))
                    rel.Id = Guid.NewGuid().ToString();

                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[LoadFromDisk] Skipping invalid relationship '{key}': {ex.Message}");
                rel = null;
                return false;
            }
        }

        internal static bool TryParseGroup(JObject source, string key, out CopierGroup grp)
        {
            grp = new CopierGroup();
            try
            {
                var normalized = NormalizeConfigObject(source);
                normalized = RemoveUnknownEnums(normalized, typeof(CopierGroup));

                if (!normalized.ContainsKey("GroupName"))
                    normalized["GroupName"] = key;
                if (!normalized.ContainsKey("LeaderAccountName"))
                {
                    Console.WriteLine($"[LoadFromDisk] Skipping invalid group '{key}': could not derive LeaderAccountName from key.");
                    grp = null;
                    return false;
                }

                JsonConvert.PopulateObject(normalized.ToString(), grp);
                grp.PerTickerRatios = EnsureOrdinalIgnoreCase(grp.PerTickerRatios);
                grp.CustomSymbolMappings = EnsureOrdinalIgnoreCase(grp.CustomSymbolMappings);

                if (string.IsNullOrEmpty(grp.Id))
                    grp.Id = Guid.NewGuid().ToString();

                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[LoadFromDisk] Skipping invalid group '{key}': {ex.Message}");
                grp = null;
                return false;
            }
        }

        internal static JObject NormalizeConfigObject(JObject source)
        {
            var target = new JObject();
            foreach (var prop in source.Properties())
            {
                if (!ConfigAliasMap.ContainsKey(prop.Name))
                    target[prop.Name] = prop.Value;
            }
            foreach (var prop in source.Properties())
            {
                if (ConfigAliasMap.TryGetValue(prop.Name, out string canonical))
                {
                    if (!target.ContainsKey(canonical))
                    {
                        target[canonical] = prop.Value;
                    }
                    else if (target[canonical] is JObject existingObj && prop.Value is JObject aliasObj)
                    {
                        var merged = new JObject(aliasObj);
                        foreach (var p in existingObj.Properties())
                        {
                            merged[p.Name] = p.Value;
                        }
                        target[canonical] = merged;
                    }
                }
            }
            return target;
        }

        internal static JObject RemoveUnknownEnums(JObject source, Type targetType)
        {
            var clone = (JObject)source.DeepClone();
            foreach (var prop in targetType.GetProperties())
            {
                Type enumType = Nullable.GetUnderlyingType(prop.PropertyType) ?? prop.PropertyType;
                if (!enumType.IsEnum)
                    continue;
                bool isFlags = Attribute.IsDefined(enumType, typeof(FlagsAttribute));
                JToken token = clone[prop.Name];
                if (token == null)
                    continue;
                bool keep = false;
                if (token.Type == JTokenType.String)
                {
                    string s = token.Value<string>();
                    if (!string.IsNullOrEmpty(s))
                    {
                        try
                        {
                            object parsed = Enum.Parse(enumType, s, true);
                            if (Enum.IsDefined(enumType, parsed) || isFlags)
                                keep = true;
                        }
                        catch { }
                    }
                }
                else if (token.Type == JTokenType.Integer)
                {
                    try
                    {
                        long v = token.Value<long>();
                        object enumVal = Enum.ToObject(enumType, v);
                        if (Enum.IsDefined(enumType, enumVal) || isFlags)
                            keep = true;
                    }
                    catch { }
                }
                if (!keep)
                    clone.Remove(prop.Name);
            }
            return clone;
        }

        internal static Dictionary<string, T> EnsureOrdinalIgnoreCase<T>(IDictionary<string, T> source)
        {
            if (source == null)
                return new Dictionary<string, T>(StringComparer.OrdinalIgnoreCase);
            return new Dictionary<string, T>(source, StringComparer.OrdinalIgnoreCase);
        }

        // ---- the MCP bridge's request -> object mapping (slice 3b) ----
        //
        // MERGE, not rebuild. The previous version constructed a brand new object
        // from a hand-written field list and handed it to Upsert*, which removes
        // the existing object and adds the new one wholesale; the bridge's next
        // line is SaveToDisk. So every field the caller did not mention reverted
        // to an initialiser default and was written over the stored config -- a
        // set_group carrying {groupName, quantityRatio} destroyed the ratio
        // matrix, the sizing mode, the symbol mappings and the follower list.
        //
        // Completing the field list would not have fixed that; the next omitted
        // field is destroyed just the same. The fix has to be a merge: start from
        // what is stored and apply only the keys actually PRESENT in the request.
        // PopulateObject does exactly that, and reusing slice 3a's normalisation
        // means there is no longer a second remembered subset to drift from the
        // loader's.
        //
        // Lives here and not in the bridge because McpBridgeAddOn.cs is
        // <Compile Remove>d from RiskGuardTests.csproj for its WPF deps -- left
        // there, this could only be pinned by source-text regex.

        private static string ReqStr(JObject req, string key)
        {
            JToken tok = req == null ? null : req[key];
            return tok == null || tok.Type == JTokenType.Null ? null : tok.ToString();
        }

        // A collection NAMED in the request is replaced by it; an absent or null one
        // is left alone. Found on the sim accounts after slice 3b shipped: merge
        // semantics had made every collection append-only, because PopulateObject
        // reuses the existing dictionary instance and merges keys INTO it, never
        // removing one. So `perTickerRatios: {}` was a no-op and an operator could
        // not remove a ticker rule, fix a typo'd mapping, or drop a follower without
        // deleting the whole relationship.
        //
        // The instance is cleared rather than reassigned because that is simpler --
        // NOT, as first written here, to protect the OrdinalIgnoreCase comparer.
        // A mutant that reassigned a fresh Dictionary<string,T> (default comparer)
        // survived the whole suite: the EnsureOrdinalIgnoreCase calls after
        // PopulateObject restore the comparer either way. Recorded because the
        // plausible-sounding version of that claim is false, and the next reader
        // would otherwise treat this line as load-bearing for P1-39. It is not.
        private static void ClearCollectionsNamedIn(JObject normalized, object target)
        {
            if (normalized == null || target == null) return;

            foreach (var prop in normalized.Properties())
            {
                var pi = target.GetType().GetProperty(prop.Name);
                if (pi == null) continue;

                object current = pi.GetValue(target, null);
                if (current == null || current is string) continue;

                var dict = current as System.Collections.IDictionary;
                if (dict != null) { dict.Clear(); continue; }

                var list = current as System.Collections.IList;
                if (list != null) list.Clear();
            }
        }

        private static T CloneConfig<T>(T source)
        {
            // Deep clone so a malformed request cannot half-apply to the stored
            // object on its way to throwing. Session 14's rule holds on the write
            // path too: a malformed NUMBER fails closed rather than landing a zero
            // limit, and here it must also leave what is already stored alone.
            return JsonConvert.DeserializeObject<T>(JsonConvert.SerializeObject(source));
        }

        // `followers` is the bridge's own spelling and is not a field on either
        // type, so the alias map does not carry it. PopulateObject would silently
        // ignore it and the caller's follower list would vanish.
        private static JObject NormalizeRequest(JObject req, Type targetType)
        {
            var normalized = NormalizeConfigObject(req);
            if (normalized["FollowerAccounts"] == null && req["followers"] is JArray followers)
                normalized["FollowerAccounts"] = followers;

            // An explicit null means "not specified", not "wipe it". Json.NET's
            // default NullValueHandling would set the property to null, so
            // {"perTickerRatios": null} -- which is what a JS client sends for an
            // untouched field -- would null out the ratio matrix and hand a
            // NullReferenceException to whatever sizes the next fill. Under merge
            // semantics an absent field and a null field mean the same thing.
            foreach (var prop in normalized.Properties().ToList())
            {
                if (prop.Value == null || prop.Value.Type == JTokenType.Null)
                    normalized.Remove(prop.Name);
            }

            return RemoveUnknownEnums(normalized, targetType);
        }

        /// <summary>
        /// UI7. FOR CALLERS THAT ALREADY KNOW THE REQUEST CANNOT BE REFUSED -- which in
        /// practice means test fixtures, and nothing else. An OPERATOR SURFACE must call the
        /// three-argument overload, because a surface is precisely the caller with a person
        /// waiting to be told what to change.
        ///
        /// This is not a style preference. The bridge's two write branches discarded the
        /// refusal and then dereferenced the null they were handed (`rel.IsEnabled`), so a
        /// refused write reached the operator as a NullReferenceException -- after SaveToDisk
        /// had already run. The NT8 window checked the null but could still only say "the
        /// engine refused", because the reason existed nowhere but the copier log.
        /// `TestUi7_NoOperatorSurfaceCallsTheReasonLosingOverload` holds that line.
        /// </summary>
        public CopierGroup ApplyGroupRequest(JObject req, bool confirmLive)
        {
            string ignored;
            return ApplyGroupRequest(req, confirmLive, out ignored);
        }

        /// <summary>
        /// Returns null on refusal, exactly as before, and sets <paramref name="refusalReason"/>
        /// to the reason -- which is null on success, so the two agree and either can be tested.
        ///
        /// The reason string is built ONCE and handed to both the log and the caller. Writing it
        /// twice would be the shorter diff and the reliable bug: two explanations of one refusal
        /// drift apart, and the operator reads whichever of them nobody maintained.
        /// </summary>
        public CopierGroup ApplyGroupRequest(JObject req, bool confirmLive, out string refusalReason)
        {
            refusalReason = null;
            if (req == null)
            {
                refusalReason = "the request was empty, so there was nothing to apply.";
                return null;
            }
            string groupName = ReqStr(req, "groupName") ?? ReqStr(req, "GroupName");

            if (string.IsNullOrWhiteSpace(groupName))
            {
                refusalReason = "refused to apply group request: the group name was missing. A group request must name the group it applies to.";
                CopierLog(string.Empty, "MISSING_GROUP_NAME_REFUSED", refusalReason);
                return null;
            }

            string leader = ReqStr(req, "leaderAccount") ?? ReqStr(req, "LeaderAccountName");

            CopierGroup grp;
            bool isNew;
            lock (_lock)
            {
                var existing = _groups.FirstOrDefault(g =>
                    g.GroupName.Equals(groupName, StringComparison.OrdinalIgnoreCase));
                isNew = existing == null;
                grp = isNew
                    ? new CopierGroup { GroupName = groupName, LeaderAccountName = leader ?? "" }
                    : CloneConfig(existing);
            }

            if (isNew && string.IsNullOrWhiteSpace(leader))
            {
                refusalReason = string.Format(
                    "refused to create group '{0}': the leader account was missing. A new group must name the "
                    + "leader account that its followers will copy.",
                    groupName);
                CopierLog(groupName, "MISSING_GROUP_LEADER_REFUSED", refusalReason);
                return null;
            }

            var normalized = NormalizeRequest(req, typeof(CopierGroup));
            bool armingWasRequested = normalized["ArmedForLive"] != null;

            // Only the keys present in `normalized` are written; everything else on
            // `grp` is whatever was stored. This throws on a malformed value, which
            // is deliberate -- the clone above means the stored object is untouched.
            ClearCollectionsNamedIn(normalized, grp);
            JsonConvert.PopulateObject(normalized.ToString(), grp);

            // GroupName was established when the group was cloned or created, so an
            // explicit re-assertion here is unnecessary.
            //
            // The comparer re-application is NOT inert, though it looks it:
            // PopulateObject reuses the initialiser's dictionary instance, so the
            // request path keeps OrdinalIgnoreCase on its own. What this catches
            // is a STORED object whose dictionary is null -- Upsert* accepts one,
            // and without this the next lookup throws.
            grp.PerTickerRatios = EnsureOrdinalIgnoreCase(grp.PerTickerRatios);
            grp.CustomSymbolMappings = EnsureOrdinalIgnoreCase(grp.CustomSymbolMappings);

            ApplyArmingGate(grp.ArmedForLive, armingWasRequested, confirmLive, v => grp.ArmedForLive = v);

            // P1-76. Checked HERE rather than at the top, because the merge above is what
            // decides the group's final leader and follower list -- a partial update that
            // does not mention followerAccounts inherits the stored list, and that list is
            // what has to be checked. `grp` is a CLONE, so returning now leaves the stored
            // group untouched.
            //
            // ALL-OR-NOTHING on purpose: if one named follower clashes, the whole request is
            // refused. Creating the group minus that account would silently drop something
            // the operator explicitly named, which is the same "config must not lie" defect
            // as P1-23 and the dead autoConversion argument (P1-74).
            if (grp.FollowerAccounts != null && !string.IsNullOrWhiteSpace(grp.LeaderAccountName))
            {
                var clashes = grp.FollowerAccounts
                    .Where(f => !string.IsNullOrWhiteSpace(f) && DirectRelationshipExists(grp.LeaderAccountName, f))
                    .ToList();
                if (clashes.Count > 0)
                {
                    refusalReason = string.Format(
                        "refused group '{0}' under leader '{1}': {2} of its followers already have a direct "
                        + "relationship ({3}). The ENTIRE request was refused -- creating the group without them "
                        + "would silently drop accounts you named. Remove those relationships, or leave those "
                        + "accounts out of the group.",
                        grp.GroupName, grp.LeaderAccountName, clashes.Count, string.Join(", ", clashes));
                    CopierLog(grp.LeaderAccountName, "CONFIG_OVERLAP_REFUSED", refusalReason);
                    return null;
                }
            }

            UpsertGroup(grp, true);
            return grp;
        }

        /// <summary>UI7. See <see cref="ApplyGroupRequest(JObject, bool)"/> -- fixtures only, never a surface.</summary>
        public CopierRelationship ApplyRelationshipRequest(JObject req, bool confirmLive)
        {
            string ignored;
            return ApplyRelationshipRequest(req, confirmLive, out ignored);
        }

        /// <summary>UI7. Null on refusal, with <paramref name="refusalReason"/> set to the one string that was also logged.</summary>
        public CopierRelationship ApplyRelationshipRequest(JObject req, bool confirmLive, out string refusalReason)
        {
            refusalReason = null;
            if (req == null)
            {
                refusalReason = "the request was empty, so there was nothing to apply.";
                return null;
            }
            string leader = ReqStr(req, "leaderAccount") ?? ReqStr(req, "LeaderAccountName");
            string follower = ReqStr(req, "followerAccount") ?? ReqStr(req, "FollowerAccountName");

            if (string.IsNullOrWhiteSpace(leader) || string.IsNullOrWhiteSpace(follower))
            {
                string missing;
                if (string.IsNullOrWhiteSpace(leader) && string.IsNullOrWhiteSpace(follower))
                    missing = "leader account and the follower account were";
                else if (string.IsNullOrWhiteSpace(leader))
                    missing = "leader account was";
                else
                    missing = "follower account was";

                refusalReason = string.Format(
                    "refused to apply relationship request: the {0} missing. A relationship applies to exactly "
                    + "one leader account and one follower account, so both must be named.",
                    missing);
                string logAccount = !string.IsNullOrWhiteSpace(follower) ? follower
                    : !string.IsNullOrWhiteSpace(leader) ? leader
                    : string.Empty;
                CopierLog(logAccount, "MISSING_ACCOUNT_REFUSED", refusalReason);
                return null;
            }

            // P1-76. Refuse before touching anything: a follower already reserved by a group
            // cannot also have a direct relationship. Returning null rather than throwing
            // keeps this consistent with the method's existing "null means no" contract, and
            // the caller reports it -- but the REASON has to be logged here, because the
            // caller does not know which group is responsible.
            var reserving = GroupReserving(leader, follower);
            if (reserving != null)
            {
                refusalReason = string.Format(
                    "refused to create a direct relationship for '{0}' under leader '{1}': it is already a member "
                    + "of group '{2}'. A follower belongs to a direct relationship OR a group, never both, so that "
                    + "there is exactly one place to look for what applies to it. Remove it from the group first, "
                    + "or change the group instead.",
                    follower, leader, reserving.GroupName);
                CopierLog(follower, "CONFIG_OVERLAP_REFUSED", refusalReason);
                return null;
            }

            CopierRelationship rel;
            lock (_lock)
            {
                var existing = _relationships.FirstOrDefault(r =>
                    r.LeaderAccountName.Equals(leader, StringComparison.OrdinalIgnoreCase) &&
                    r.FollowerAccountName.Equals(follower, StringComparison.OrdinalIgnoreCase));
                rel = existing != null
                    ? CloneConfig(existing)
                    : new CopierRelationship();
            }

            var normalized = NormalizeRequest(req, typeof(CopierRelationship));
            bool armingWasRequested = normalized["ArmedForLive"] != null;

            ClearCollectionsNamedIn(normalized, rel);
            JsonConvert.PopulateObject(normalized.ToString(), rel);

            // UI2: a reason without a quarantine is stale data; state this as a domain invariant.
            if (!rel.IsQuarantined)
                rel.QuarantineReason = null;

            // As in ApplyGroupRequest: the key re-assertions were inert (the
            // fallbacks are byte-identical to the initialiser defaults), the
            // comparer guard is not.
            rel.PerTickerRatios = EnsureOrdinalIgnoreCase(rel.PerTickerRatios);
            rel.CustomSymbolMappings = EnsureOrdinalIgnoreCase(rel.CustomSymbolMappings);

            ApplyArmingGate(rel.ArmedForLive, armingWasRequested, confirmLive, v => rel.ArmedForLive = v);
            UpsertRelationship(rel, true);
            return rel;
        }

        // The safety gate, stated once for both halves.
        //
        // Arming still requires confirmLive, exactly as before. What merge
        // semantics ADD is the other direction: a request that never mentions
        // armedForLive leaves the stored value alone. It has to, or nudging a
        // ratio on a live group would silently stop it copying -- the leader
        // trades and the follower does not, which is P0-9's failure shape reached
        // from a new direction. An explicit armedForLive:false still disarms
        // without confirmation; refusing to disarm is not a safe default.
        //
        // Because the gate is decided here, Upsert* is called with confirmLive:true
        // so it does not re-apply its own gate and undo the preserved value.
        private static void ApplyArmingGate(bool armed, bool armingWasRequested, bool confirmLive, Action<bool> set)
        {
            if (armed && armingWasRequested && !confirmLive)
                set(false);
        }

        /// <summary>
        /// THE copier config file. One owner, in core, so that every surface -- the NT8
        /// window, the bridge's six write sites, and the startup load -- names the same
        /// file by naming this instead of a path.
        ///
        /// UI2 / `P?-64`. Before this existed the window wrote
        /// `UserDataDir/CopierConfig.json` at seven call sites while the bridge and the
        /// startup load read `UserDataDir/RiskGuard/copier_config.json`. Both files
        /// existed on the operator's box with different contents, and every change made
        /// in the window was silently discarded at the next NT8 restart. Nothing errored;
        /// the config simply was not there any more.
        /// </summary>
        public static string ConfigFilePath
        {
            get { return Path.Combine(Globals.UserDataDir, "RiskGuard", "copier_config.json"); }
        }

        /// <summary>
        /// Save to <see cref="ConfigFilePath"/>. This is the overload every surface should
        /// call; the path-taking one stays for the tests, which need to write somewhere
        /// disposable.
        /// </summary>
        /// <remarks>
        /// ⚠️ THE ASYMMETRY IS DELIBERATE: there is a parameterless SAVE and there is
        /// deliberately NO parameterless LOAD. A convenient `LoadFromDisk()` is exactly
        /// the footgun `P1-69` fired -- the bridge's `get` action called it and threw away
        /// the in-memory latency and slippage measurements it had been asked to report.
        /// A save is safe to make easy. A load is not, so the two callers that legitimately
        /// need one (startup, and an explicit operator reload) say
        /// `LoadFromDisk(TradeCopierEngine.ConfigFilePath)` and are visible in a grep.
        /// </remarks>
        public void SaveToDisk()
        {
            SaveToDisk(ConfigFilePath);
        }

        public void SaveToDisk(string filePath)
        {
            if (string.IsNullOrEmpty(filePath)) return;
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(filePath));
                lock (_lock)
                {
                    var jRels = new JObject();
                    foreach (var rel in _relationships)
                    {
                        jRels[rel.LeaderAccountName + "_" + rel.FollowerAccountName] = JObject.Parse(JsonConvert.SerializeObject(rel));
                    }

                    var jGrps = new JObject();
                    foreach (var grp in _groups)
                    {
                        jGrps[grp.GroupName] = JObject.Parse(JsonConvert.SerializeObject(grp));
                    }

                    var jRoot = new JObject
                    {
                        ["Relationships"] = jRels,
                        ["Groups"] = jGrps
                    };

                    string jsonToSave = jRoot.ToString(Formatting.Indented);
                    File.WriteAllText(filePath, jsonToSave);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[SaveToDisk EXCEPTION] {ex}");
            }
        }

        /// <summary>
        /// True only when the account is demonstrably a NinjaTrader simulation account.
        ///
        /// This is the switch that decides whether an account can lose real money, so it
        /// must not be inferred from the account NAME. Names are chosen by the user, and
        /// the previous `Name.StartsWith("Sim")` test exempted a funded account called
        /// "SimpsonFund" -- or "Simplex Capital", or any prop firm starting with those
        /// three letters -- from BOTH live gates at once: the `ArmedForLive` check and
        /// T5's requirement that a live follower be protected by RiskGuard (P1-20).
        ///
        /// Fails closed by construction: a null account, an unset provider, or anything
        /// this cannot positively identify as the simulator is treated as live. Playback
        /// is deliberately NOT exempt -- it costs nothing to arm a relationship for a
        /// playback run, and guessing wrong in the other direction costs money.
        /// </summary>
        internal static bool IsSimulationAccount(Account account)
        {
            if (account == null) return false;
            return account.Provider == Provider.Simulator;
        }

        // ------------------------------------------------------------------
        // ACCOUNT EVENT SUBSCRIPTIONS (P1-21)
        //
        // The copier's ExecutionUpdate handlers used to be attached by McpBridgeAddOn in a
        // single pass over Account.All at State.Configure. Any account that came online after
        // that pass -- a broker connecting late, a reconnect, an account added from the
        // Control Center -- never raised OnExecution. A relationship whose leader arrived late
        // was therefore silently dead: enabled in the config, listed in the UI, copying
        // nothing. RiskGuard already solves this by re-running its subscribe pass on every
        // Connection.ConnectionStatusUpdate (RiskGuardAddOn.OnConnectionStatusUpdate); this
        // mirrors that.
        //
        // The bookkeeping lives here, not in McpBridgeAddOn, because that file is excluded
        // from the test build by RiskGuardTests.csproj -- an untestable subscription is how
        // this defect survived in the first place.
        // ------------------------------------------------------------------

        // Held only across event add/remove, which touch no broker call and cannot re-enter.
        // Deliberately NOT _lock: OnExecution takes that one, and a subscribe pass must never
        // be able to serialise behind an in-flight copy.
        private readonly object _subscriptionLock = new object();

        // The Account objects this engine instance has attached to, so teardown can detach
        // from exactly those. Reference identity, not name: a reconnect that hands back a new
        // Account object for the same name must be treated as a new subscription target.
        private readonly HashSet<Account> _subscribedAccounts = new HashSet<Account>();

        /// <summary>
        /// Attaches the copier's execution handler to every account NT8 currently knows about.
        /// Safe to call repeatedly, and meant to be: once at startup and again on every
        /// connection-status change. Returns the number of accounts newly subscribed.
        /// </summary>
        public int RefreshAccountSubscriptions()
        {
            int added = 0;
            lock (_subscriptionLock)
            {
                foreach (Account acc in Account.All.ToList())
                {
                    if (acc == null) continue;

                    // `-=` is a no-op when the handler is not attached, so re-running the pass
                    // cannot double-deliver an execution. Note this only dedupes handlers owned
                    // by *this* engine instance -- it cannot detach one left behind by a
                    // previous instance, which is why Terminated must call
                    // UnsubscribeAllAccounts.
                    acc.ExecutionUpdate -= OnAccountExecutionUpdate;
                    acc.ExecutionUpdate += OnAccountExecutionUpdate;

                    // P0-9: the leader's protective legs are only visible as OrderUpdate events;
                    // they never produce an execution until they fire.
                    acc.OrderUpdate -= OnAccountOrderUpdate;
                    acc.OrderUpdate += OnAccountOrderUpdate;

                    // P0-49: and the follower's own position is the ONLY authoritative source for
                    // the anchor the mirrored stop hangs off. ExecutionUpdate alone is not enough:
                    // NT8 raises it BEFORE PositionUpdate, so a bracket anchored at execution time
                    // reads a position that does not exist yet.
                    acc.PositionUpdate -= OnAccountPositionUpdate;
                    acc.PositionUpdate += OnAccountPositionUpdate;

                    if (_subscribedAccounts.Add(acc)) added++;
                }
            }
            return added;
        }

        /// <summary>
        /// Detaches from every account subscribed by this engine instance. Must run at
        /// State.Terminated: NT8 reloads every AddOn on each recompile, and a handler left
        /// attached to a surviving Account object would keep delivering executions to the dead
        /// engine alongside the new one -- every fill copied twice.
        /// </summary>
        public int UnsubscribeAllAccounts()
        {
            lock (_subscriptionLock)
            {
                int count = _subscribedAccounts.Count;
                foreach (Account acc in _subscribedAccounts)
                {
                    if (acc == null) continue;
                    acc.ExecutionUpdate -= OnAccountExecutionUpdate;
                    acc.OrderUpdate -= OnAccountOrderUpdate;
                    acc.PositionUpdate -= OnAccountPositionUpdate;
                }
                _subscribedAccounts.Clear();
                return count;
            }
        }

        /// <summary>Number of accounts currently subscribed by this engine instance.</summary>
        public int SubscribedAccountCount
        {
            get { lock (_subscriptionLock) { return _subscribedAccounts.Count; } }
        }

        private void OnAccountExecutionUpdate(object sender, ExecutionEventArgs e)
        {
            if (e != null && e.Execution != null)
            {
                OnExecution(e.Execution);
            }
        }

        private void OnAccountOrderUpdate(object sender, OrderEventArgs e)
        {
            if (e == null || e.Order == null) return;
            Account acct = sender as Account;
            OnLeaderOrderUpdate(acct, e.Order);
            // The same event on a FOLLOWER account is how a rejected or cancelled mirrored stop
            // becomes visible. The first implementation subscribed to it and then discarded it,
            // because OnLeaderOrderUpdate returns early for an account with no relationships --
            // the notification was arriving and being thrown away.
            OnFollowerOrderUpdate(acct, e.Order);
        }

        /// <summary>
        /// A mirrored protective leg went terminal while the follower still holds the position.
        /// Re-submit, bounded by <see cref="MaxBracketStopAttempts"/> /
        /// <see cref="MaxBracketTargetAttempts"/>.
        /// </summary>
        /// <summary>
        /// P0-61. One of our legs has settled out of a change. If a sync deferred an instruction
        /// while that change was in flight, re-drive it now and report that we did.
        ///
        /// A dedicated flag rather than the existing `*ResyncOwed`: that one is consumed by
        /// `SyncFollowerStop`'s own pass loop the moment it is set, which would re-drive
        /// immediately -- while the leg is still mid-change -- and burn the pass budget deferring
        /// three times before giving up. The two signals mean different things and cannot share
        /// storage: "a concurrent sync had a newer instruction" versus "the broker was busy, come
        /// back when it is not".
        /// </summary>
        private bool ReDriveDeferredLeg(Account followerAcc, Order order)
        {
            FollowerBracket bracket;
            string key = BracketKey(followerAcc.Name, order.Instrument.FullName);
            lock (_lock)
            {
                if (!_followerBrackets.TryGetValue(key, out bracket)) return false;

                bool isStop = ReferenceEquals(bracket.WorkingStop, order) && bracket.StopChangeDeferred;
                bool isTarget = ReferenceEquals(bracket.WorkingTarget, order) && bracket.TargetChangeDeferred;
                if (!isStop && !isTarget) return false;

                // Cleared before the sync, not after: if the sync defers again -- the broker can
                // start another change on its own account -- it sets the flag again, and a flag
                // cleared afterwards would erase that.
                if (isStop) bracket.StopChangeDeferred = false;
                else bracket.TargetChangeDeferred = false;
            }

            CopierLog(followerAcc.Name, "BRACKET_DEFERRED_REDRIVE",
                $"{order.Instrument.FullName}: the leg settled to {order.OrderState}; "
                + "re-applying the instruction deferred while its change was in flight.");

            SyncFollowerBracket(followerAcc, order.Instrument, bracket);
            return true;
        }

        private void OnFollowerOrderUpdate(Account followerAcc, Order order)
        {
            if (followerAcc == null || order == null || order.Instrument == null) return;

            // P0-63. Detect a provider that accepts Change() but silently ignores it. Verified on
            // the settle event (AcceptsModification), gated to the exact order the request was made
            // against, and re-driven through the in-flight-reserving wrappers -- never the Once
            // methods, which would let two syncs run concurrently on one bracket (P1-56).
            bool VerifyAndRecoverIgnoredChange(Account acc, Order o)
            {
                string key = BracketKey(acc.Name, o.Instrument.FullName);
                FollowerBracket bracket;
                bool isStopLeg;
                bool isTargetLeg;
                LegChangeRequest req;
                bool deferred;
                lock (_lock)
                {
                    if (!_followerBrackets.TryGetValue(key, out bracket)) return false;
                    isStopLeg = ReferenceEquals(bracket.WorkingStop, o);
                    isTargetLeg = ReferenceEquals(bracket.WorkingTarget, o);
                    if (!isStopLeg && !isTargetLeg) return false;
                    req = isStopLeg ? bracket.StopChangeRequest : bracket.TargetChangeRequest;
                    deferred = isStopLeg ? bracket.StopChangeDeferred : bracket.TargetChangeDeferred;
                }

                if (req == null || req.Order == null || !ReferenceEquals(req.Order, o)) return false;

                double currentPrice = isStopLeg ? o.StopPrice : o.LimitPrice;
                int currentQty = o.Quantity;

                bool priceStillOriginal = Math.Abs(currentPrice - req.OriginalPrice) <= 1e-9;
                bool qtyStillOriginal = currentQty == req.OriginalQuantity;

                if (!priceStillOriginal || !qtyStillOriginal)
                {
                    // The order is not sitting at the values it held before the request.
                    // Treat as honoured (or at least not a positive no-op) and clear the record.
                    lock (_lock)
                    {
                        if (isStopLeg) bracket.StopChangeRequest = null;
                        else bracket.TargetChangeRequest = null;
                    }

                    // P1-70: this is the ONLY place a modification can honestly be called done --
                    // the provider has settled the order and it is not at its pre-request values.
                    // It was silent, which is why the optimistic line upstream looked necessary.
                    // Note "took" is not the same as "took exactly": a provider that applies the
                    // price and refuses the quantity (P0-62's shape) lands here too, so the settled
                    // values are printed rather than the requested ones.
                    bool exact = Math.Abs(currentPrice - req.RequestedPrice) <= 1e-9
                                 && currentQty == req.RequestedQuantity;
                    CopierLog(acc.Name, isStopLeg ? "BRACKET_MODIFY_CONFIRMED" : "BRACKET_TARGET_MODIFY_CONFIRMED",
                        $"{o.Instrument.FullName}: provider settled the {(isStopLeg ? "stop" : "target")} "
                        + $"at {currentQty}@{currentPrice} (requested {req.RequestedQuantity}@{req.RequestedPrice}, "
                        + $"was {req.OriginalQuantity}@{req.OriginalPrice})"
                        + (exact
                            ? " -- modified in place, so no unprotected window."
                            : " -- ⚠ PARTIALLY honoured: it moved, but not to the requested values.")
                        + (deferred ? " A deferred instruction is still pending." : ""));
                    return false;
                }

                // Positive evidence that Change() was accepted and ignored. Do NOT clear the
                // P0-61 deferred flags here -- the re-drive below will apply the latest desired
                // state, and clearing them before broker work starts would discard an owed
                // instruction if the wrapper has to back off. Do NOT clear StopChangeRequest /
                // TargetChangeRequest here either: the re-drive's cancel-then-create path will
                // clear it when the old order is actually replaced, and leaving it in place lets
                // a backed-off re-drive still verify the same order on its next settle event.
                // No budget refresh here either. It was added during review and mutation testing
                // showed nothing pins it, which matches the reasoning: the account is marked on the
                // FIRST detection, so at most one doomed Change() is ever spent per instruction,
                // and OnLeaderOrderUpdate zeroes the budget whenever the leader's offset changes.
                // Where the budget DOES bind -- repeated syncs at an unchanged offset -- it is
                // doing its job, and resetting it there is how an order flood starts.
                lock (_lock)
                {
                    _accountsIgnoringChange.Add(acc.Name);
                }

                CopierLog(acc.Name, isStopLeg ? "BRACKET_STOP_CHANGE_IGNORED" : "BRACKET_TARGET_CHANGE_IGNORED",
                    $"{o.Instrument.FullName}: provider ignored Change() for {(isStopLeg ? "stop" : "target")} "
                    + $"(still {currentQty}@{currentPrice}, requested {req.RequestedQuantity}@{req.RequestedPrice})"
                    + (deferred ? " with a deferred instruction pending" : "")
                    + "; falling back to cancel-then-create.");

                try
                {
                    if (isStopLeg) SyncFollowerStop(acc, o.Instrument, bracket);
                    else SyncFollowerTarget(acc, o.Instrument, bracket);
                }
                catch (Exception redriveEx)
                {
                    // P0-63. The re-drive itself failed (e.g., an unexpected exception escaped the
                    // wrapper). Do NOT consume the event as if it were handled, and do NOT clear
                    // the request record: the next OrderUpdate for the same still-working order
                    // must be allowed to re-detect the no-op and retry. Returning false also lets
                    // P0-61's ReDriveDeferredLeg run for this event, so a deferred instruction is
                    // not dropped just because the cancel-then-create path hit a transient fault.
                    CopierLog(acc.Name, isStopLeg ? "BRACKET_STOP_REDRIVE_FAILED" : "BRACKET_TARGET_REDRIVE_FAILED",
                        $"{o.Instrument.FullName}: {redriveEx.Message}. Leaving change record in place so the next settle event retries.");
                    return false;
                }

                return true;
            }

            // P0-61 / P0-63 settle hook. It must come BEFORE the OccupiesSlot return below.
            //
            // P0-61: A leg that has just settled out of ChangeSubmitted/ChangePending still occupies
            // a slot, so the early return would drop this event -- and the instruction we deferred
            // while the change was in flight would be lost, leaving the leg at its old price and
            // size for the life of the position. ReDriveDeferredLeg re-applies it.
            //
            // P0-63: Verify that a Change() which returned without throwing actually took. If the
            // leg is still at its pre-change values, mark the account and re-drive through the
            // in-flight-reserving wrappers.
            if (RiskGuardAddOn.AcceptsModification(order.OrderState))
            {
                if (VerifyAndRecoverIgnoredChange(followerAcc, order)) return;
                if (ReDriveDeferredLeg(followerAcc, order)) return;
            }

            if (RiskGuardAddOn.OccupiesSlot(order.OrderState)) return;   // still there; nothing lost
            if (order.OrderState == OrderState.Filled) return;                 // it did its job

            string key = BracketKey(followerAcc.Name, order.Instrument.FullName);
            FollowerBracket bracket;
            bool isStopLeg;
            Order sibling;
            lock (_lock)
            {
                if (!_followerBrackets.TryGetValue(key, out bracket)) return;
                isStopLeg = ReferenceEquals(bracket.WorkingStop, order);
                bool isTargetLeg = ReferenceEquals(bracket.WorkingTarget, order);
                if (!isStopLeg && !isTargetLeg) return;                        // not one of ours
                sibling = isStopLeg ? bracket.WorkingTarget : bracket.WorkingStop;
                // Do NOT clear WorkingStop/WorkingTarget here. An honest reference keeps the
                // ReferenceEquals guard meaningful during an in-flight sync, and it lets a second
                // sync modify the existing order instead of creating a duplicate. The re-drive
                // will replace it once the broker work resolves.
            }

            // A leg whose OCO sibling has FILLED was not lost -- it was retired, which is what
            // "one cancels the other" means. Re-submitting here would place a protective order
            // against a position that has just been closed, because NT8 raises ExecutionUpdate
            // before PositionUpdate (P0-49's ordering) and the follower therefore still reads as
            // open. That is P0-50's orphan, arriving by a route that did not exist until targets
            // were mirrored. The follower's position update releases the bracket a beat later.
            if (sibling != null && sibling.OrderState == OrderState.Filled)
            {
                CopierLog(followerAcc.Name, "BRACKET_LEG_RETIRED_BY_OCO",
                    $"{order.Instrument.FullName} mirrored {(isStopLeg ? "stop" : "target")} went "
                    + $"{order.OrderState} because its OCO sibling filled; not re-submitting.");
                return;
            }

            NinjaTrader.Code.Output.Process(
                $"[CopierEngine] {(isStopLeg ? "BRACKET_STOP_LOST" : "BRACKET_TARGET_LOST")}: {followerAcc.Name} {order.Instrument.FullName} mirrored {(isStopLeg ? "stop" : "target")} went {order.OrderState}; re-submitting.",
                PrintTo.OutputTab1);

            SyncFollowerBracket(followerAcc, order.Instrument, bracket);
        }

        // ------------------------------------------------------------------
        // BRACKET REPLICATION (P0-9)
        //
        // Followers received bare market orders with no protective legs. Their only cover was
        // RiskGuard's StopAttachSeconds grace -> RiskGuardAutoStop at a FIXED TICK OFFSET from
        // average price, which bears no relation to the leader's actual stop; and if RiskGuard is
        // disarmed, in shadow, or the follower is excluded, there was no stop at all.
        //
        // The leader's stop is mirrored by DISTANCE, not by price, and anchored to the follower's
        // own fill. Copying the leader's stop price would be wrong the moment the follower filled
        // anywhere else -- which is exactly what P1-22 now measures as slippage -- and wrong by an
        // entire price scale on a micro/mini conversion.
        //
        //     followerStop = followerEntry -/+ |leaderPositionAvgPrice - leaderStopPrice|
        //
        // SCOPE: both protective legs. The stop shipped first because it is what makes the
        // follower not-naked; the target (P0-9 item 1) followed once P1-56 closed and the OCO id
        // rule was pinned by live test (handover 4p). The two are NOT symmetric and the asymmetry
        // is deliberate throughout: the stop is risk and always wins, the target is upside and is
        // never allowed to disturb the stop.
        //
        // The OCO rule, in one line: an id can be JOINED while its group still has a live member,
        // and is REJECTED once every leg has gone terminal. So a leg that is modified in place
        // keeps its id, a leg created beside a live sibling joins it, and only a leg re-created
        // after its group may have been retired needs a fresh one.
        // ------------------------------------------------------------------

        // P0-63. A snapshot of the last Change() issued against a bracket leg, so the settle event
        // can detect a provider that accepts Change() but silently ignores it.
        private class LegChangeRequest
        {
            public Order Order;
            public double OriginalPrice;
            public double RequestedPrice;
            public int OriginalQuantity;
            public int RequestedQuantity;
        }

        private class FollowerBracket
        {
            public string RelationshipId;
            public string FollowerAccountName;
            public string InstrumentFullName;
            public MarketPosition FollowerSide = MarketPosition.Flat;
            public int FollowerQuantity;
            public double FollowerEntryPrice = double.NaN;   // the anchor; NaN until the follower fills
            // SIGNED offset from the leader's average entry to its stop, in points.
            // Negative = stop below entry, positive = above. NaN until the leader's stop appears.
            // It must stay signed: a leader trailing its stop INTO PROFIT puts the stop above
            // entry on a long, and an absolute distance would mirror that as a loss of the same
            // size on the follower -- turning the leader's locked-in gain into open risk.
            public double StopOffset = double.NaN;
            public Order WorkingStop;                        // the follower's live protective order

            // In-flight reservation for the bracket stop sync. Set under _lock before the first
            // broker call and cleared exactly once in a finally, so a second sync arriving while
            // one is between _lock and Submit sees the reservation and backs off.
            public bool StopInFlight;

            // Set under _lock by a sync that backed off because StopInFlight was true. The sync
            // holding the reservation re-drives the sync after its broker work resolves, so the
            // newer size/price is not dropped.
            public bool StopResyncOwed;

            // Bounded re-submission. Raised by review of the first implementation: if Submit
            // threw, or the broker rejected the stop moments later, WorkingStop ended up null
            // with a perfectly valid offset and NOTHING re-triggered submission -- the follower
            // stayed naked for the life of the position. Re-submission fixes that, and the
            // counter is what stops a persistently-rejecting instrument turning it into an
            // order flood (the failure mode P2-46 and the flood cluster already cost us once).
            public int StopAttempts;

            // P0-9 item (1). SIGNED offset from the leader's average entry to its PROFIT TARGET,
            // same convention and same reason as StopOffset. NaN until the leader's target
            // appears -- a leader with no target simply leaves this NaN and the follower gets a
            // stop only, which is exactly the behaviour that shipped before this existed.
            public double TargetOffset = double.NaN;
            public Order WorkingTarget;

            // The target leg carries its own reservation, budget and owed-flag rather than
            // sharing the stop's. Sharing would let an in-flight target sync make the RISK leg
            // wait, which is the wrong way round: upside must never delay protection.
            public bool TargetInFlight;
            public bool TargetResyncOwed;
            public int TargetAttempts;

            // The OCO id both legs currently belong to. Assigned when the first leg is created
            // and joined by the second, so the follower's target and stop cancel each other the
            // way the leader's do. Re-minted only where the group may have gone terminal --
            // see ResolveOcoIdForRecreatedLeg.
            //
            // The stop carries an id even when the bracket has no target. A group of one is
            // harmless, and it is what lets a later target JOIN rather than forcing the
            // protective stop to be cancelled and re-created into a new group.
            public string OcoId;

            // P0-61. A sync computed a new price/size for this leg while a change against it was
            // already in flight, so it declined to act. Cleared and re-driven when the leg
            // settles (ReDriveDeferredLeg). NOT the same as *ResyncOwed -- see that method.
            public bool StopChangeDeferred;
            public bool TargetChangeDeferred;

            // P0-63. The last Change() request issued against each leg, together with the pre-change
            // values and the order it was issued against. Verified when the leg settles.
            public LegChangeRequest StopChangeRequest;
            public LegChangeRequest TargetChangeRequest;
        }

        // How many EXTRA passes the reservation holder will re-drive the sync for, after a
        // concurrent sync backed off and left a newer instruction owed. Two, so a partial fill
        // plus one trail step is absorbed, and then it gives up loudly rather than ping-ponging.
        // Deliberately a named constant: the loop bound and the "this was the last pass" test
        // must be the same number, and as two literals they were one edit away from disagreeing.
        private const int MaxBracketResyncPasses = 2;

        // After this many failed attempts on one position the copier stops trying and says so.
        // Escalating forever against a broker that will not accept the order is a flood; giving
        // up silently is a naked follower. Neither is acceptable, so it gives up LOUDLY.
        private const int MaxBracketStopAttempts = 3;

        // The same bound for the target leg, and a separate counter. Nothing in the reasoning
        // above is specific to stops: a broker that keeps rejecting the limit leg would otherwise
        // be answered forever. Kept apart from StopAttempts so a churning target cannot spend the
        // budget that keeps the follower protected.
        private const int MaxBracketTargetAttempts = 3;

        // Keyed "<followerAccount>|<instrumentFullName>", ordinal-insensitive.
        private readonly Dictionary<string, FollowerBracket> _followerBrackets =
            new Dictionary<string, FollowerBracket>(StringComparer.OrdinalIgnoreCase);

        private static string BracketKey(string followerAccount, string instrumentFullName)
        {
            return (followerAccount ?? "") + "|" + (instrumentFullName ?? "");
        }

        /// <summary>
        /// P0-55. Re-drives the stop mirror for every protective stop the leader already has
        /// working on this instrument.
        ///
        /// `OnLeaderOrderUpdate` can only anchor a distance if the leader's position exists when
        /// it runs. An ATM stop routinely reaches `Accepted` BEFORE the leader's PositionUpdate --
        /// NT8 raises ExecutionUpdate first, and a partial fill widens the gap -- and once accepted
        /// it raises no further OrderUpdate. So the one event that used to be discarded, the
        /// leader's own PositionUpdate, is the only remaining chance to compute the offset.
        ///
        /// Idempotent by construction: OnLeaderOrderUpdate only recomputes the offset and syncs,
        /// and re-submits only when the distance actually changed.
        /// </summary>
        private void ReevaluateLeaderStops(Account leaderAccount, Instrument instrument)
        {
            if (leaderAccount == null || instrument == null) return;

            List<Order> candidates;
            try
            {
                // BOTH protective legs, not just the stop. The first cut of the target work
                // filtered on IsStopType here and silently left the target unanchored -- the live
                // trace read "re-evaluating 1 working protective stop(s)" on a two-legged bracket,
                // which is exactly the off-by-one-leg a stop-shaped test cannot see.
                candidates = leaderAccount.Orders
                    .Where(o => o != null && o.Instrument != null
                        && o.Instrument.FullName.Equals(instrument.FullName, StringComparison.OrdinalIgnoreCase)
                        && (RiskGuardAddOn.IsStopType(o) || o.OrderType == OrderType.Limit)
                        && RiskGuardAddOn.ProvidesCoverage(o.OrderState)
                        && (string.IsNullOrEmpty(o.Name) || !o.Name.Contains("COPIER")))
                    .ToList();
            }
            catch { return; }

            if (candidates.Count == 0) return;

            CopierLog(leaderAccount.Name, "BRACKET_REANCHOR",
                $"leader position for {instrument.FullName} landed; re-evaluating {candidates.Count} "
                + "working protective leg(s) that may have been accepted before it.");

            foreach (var o in candidates)
                OnLeaderOrderUpdate(leaderAccount, o);
        }

        /// <summary>
        /// A leader order changed. If it is the protective stop for the leader's open position,
        /// work out its distance from the leader's average entry and push that distance to every
        /// follower of that leader.
        /// </summary>
        internal void OnLeaderOrderUpdate(Account leaderAccount, Order order)
        {
            if (leaderAccount == null || order == null || order.Instrument == null) return;

            // Never react to our own protective legs, or we would mirror a mirror.
            if (!string.IsNullOrEmpty(order.Name) && order.Name.Contains("COPIER")) return;

            List<CopierRelationship> rels = GetActiveRelationshipsForLeader(leaderAccount.Name);
            if (rels.Count == 0) return;

            Position leaderPos = leaderAccount.Positions.FirstOrDefault(p =>
                p.Instrument != null &&
                p.Instrument.FullName.Equals(order.Instrument.FullName, StringComparison.OrdinalIgnoreCase));

            // No leader position: either the stop is gone, or it is an entry order. Either way
            // there is nothing to anchor a distance to right now.
            //
            // P0-55: this abandon is recoverable and used to be silent, which is why a naked
            // follower looked like nothing had happened. ReevaluateLeaderStops re-drives us from
            // the leader's PositionUpdate; log it so the recovery is visible when it works, and
            // conspicuous when it does not.
            // A bracket has TWO protective legs: the stop is the risk leg, the limit is the
            // target. Both are on the protective side of the position and both are mirrored as a
            // signed distance from the leader's anchor. IsProtectiveSide is what keeps a leader's
            // resting ENTRY limit out of this -- a buy limit under a long position is not a leg.
            bool isStopLeg   = RiskGuardAddOn.IsStopType(order);
            bool isTargetLeg = !isStopLeg && order.OrderType == OrderType.Limit;

            if (leaderPos == null || leaderPos.MarketPosition == MarketPosition.Flat)
            {
                if ((isStopLeg || isTargetLeg) && RiskGuardAddOn.ProvidesCoverage(order.OrderState))
                {
                    double pendingPx = isStopLeg ? order.StopPrice : order.LimitPrice;
                    CopierLog(leaderAccount.Name, "BRACKET_NO_LEADER_POSITION",
                        $"{(isStopLeg ? "stop" : "target")} '{order.Name}' @{pendingPx} on "
                        + $"{order.Instrument.FullName} has no leader position to anchor to yet; "
                        + "deferred until the leader's position update.");
                }
                return;
            }

            if (!isStopLeg && !isTargetLeg) return;
            if (!RiskGuardAddOn.IsProtectiveSide(order, leaderPos.MarketPosition)) return;
            if (!RiskGuardAddOn.ProvidesCoverage(order.OrderState)) return;

            double leaderAnchor = leaderPos.AveragePrice;
            double legPrice = isStopLeg ? order.StopPrice : order.LimitPrice;
            if (leaderAnchor <= 0 || legPrice <= 0) return;

            // Signed, deliberately. See FollowerBracket.StopOffset: Math.Abs here mirrors a
            // trailed-into-profit stop onto the wrong side of the follower's entry.
            double offset = legPrice - leaderAnchor;
            if (Math.Abs(offset) <= 0) return;

            // A scale-out leader has several targets and the follower has one mirrored leg, so
            // there is no honest answer to "which one". Last-seen makes the follower's exit an
            // artefact of NT8's event ordering; nearest exits the follower's WHOLE position at the
            // leader's first partial. Refuse instead, and say so -- the follower keeps its stop
            // and still exits when the leader's target fills are copied, which is exactly the
            // behaviour that shipped before targets were mirrored.
            //
            // Not applied to stops: several working stops on one leader position is a
            // reconciliation problem (P1-36, P3-30), and dropping the risk leg over it would be
            // the wrong trade in the wrong direction.
            bool targetIsAmbiguous = isTargetLeg && CountLeaderTargetLegs(leaderAccount, order.Instrument, leaderPos) > 1;
            if (targetIsAmbiguous)
            {
                CopierLog(leaderAccount.Name, "BRACKET_TARGET_AMBIGUOUS",
                    $"{order.Instrument.FullName}: the leader has more than one working target, so no "
                    + "single mirrored target is correct. Withdrawing any target already mirrored; the "
                    + "follower keeps its stop and exits on the copied leader fills.");
            }

            foreach (var rel in rels)
            {
                Account followerAcc = Account.All.FirstOrDefault(a =>
                    a.Name.Equals(rel.FollowerAccountName, StringComparison.OrdinalIgnoreCase));
                if (followerAcc == null) continue;

                Instrument targetInstrument = ResolveFollowerInstrument(rel, order.Instrument);
                if (targetInstrument == null) continue;

                // A distance in the leader's points is only meaningful on the follower's
                // instrument if the two track the same underlying at the same scale. Reuses
                // P1-22's rule: a CustomSymbolMappings entry may legitimately point ES at NQ,
                // where a mirrored distance would be a fabricated risk level.
                if (!ArePricesComparable(RootOf(order.Instrument.FullName), RootOf(targetInstrument.FullName)))
                {
                    NinjaTrader.Code.Output.Process(
                        $"[CopierEngine] BRACKET_SKIPPED_INCOMPARABLE: {order.Instrument.FullName} -> {targetInstrument.FullName} do not share a price scale; not mirroring the leader's stop for {followerAcc.Name}.",
                        PrintTo.OutputTab1);
                    continue;
                }

                string key = BracketKey(followerAcc.Name, targetInstrument.FullName);
                FollowerBracket bracket;
                Order ambiguousTarget = null;
                lock (_lock)
                {
                    if (!_followerBrackets.TryGetValue(key, out bracket))
                    {
                        bracket = new FollowerBracket
                        {
                            RelationshipId = rel.Id,
                            FollowerAccountName = followerAcc.Name,
                            InstrumentFullName = targetInstrument.FullName
                        };
                        _followerBrackets[key] = bracket;
                    }
                    // A leader that genuinely moves a leg is a new instruction, so it earns a
                    // fresh re-submission budget. A repeat of the same offset does not -- that is
                    // the path a rejecting broker would otherwise use to reset the bound forever.
                    if (isStopLeg)
                    {
                        if (double.IsNaN(bracket.StopOffset) || Math.Abs(bracket.StopOffset - offset) > 1e-9)
                            bracket.StopAttempts = 0;
                        bracket.StopOffset = offset;
                    }
                    else if (targetIsAmbiguous)
                    {
                        // Forget the distance so no later sync re-places it, and take down the leg
                        // we already mirrored. Cancelled outside the lock, below.
                        bracket.TargetOffset = double.NaN;
                        bracket.TargetAttempts = 0;
                        ambiguousTarget = bracket.WorkingTarget;
                        bracket.WorkingTarget = null;
                    }
                    else
                    {
                        if (double.IsNaN(bracket.TargetOffset) || Math.Abs(bracket.TargetOffset - offset) > 1e-9)
                            bracket.TargetAttempts = 0;
                        bracket.TargetOffset = offset;
                    }
                }

                if (ambiguousTarget != null && RiskGuardAddOn.OccupiesSlot(ambiguousTarget.OrderState))
                {
                    try { followerAcc.Cancel(new[] { ambiguousTarget }); }
                    catch (Exception aex)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_TARGET_CANCEL_FAILED",
                            $"{targetInstrument.FullName}: {aex.Message}. A mirrored target may still be "
                            + "working while the leader scales out; the stop is unaffected.");
                    }
                }

                // The anchor may not exist yet -- the leader can attach its legs before our copy
                // fills. Both syncs are a no-op until the fill lands, and the follower's own fill
                // drives them again at that point.
                SyncFollowerBracket(followerAcc, targetInstrument, bracket);
            }
        }

        /// <summary>
        /// How many working protective LIMIT legs the leader has against this position. More than
        /// one means the leader is scaling out, and a single mirrored target cannot represent that.
        ///
        /// Reads `leaderAccount.Orders` directly and swallows a concurrent-modification throw, as
        /// ReevaluateLeaderStops does: NT8 owns that collection and can mutate it under us. A throw
        /// here reports 0, which mirrors nothing -- deliberately the same direction as the refusal.
        /// </summary>
        private static int CountLeaderTargetLegs(Account leaderAccount, Instrument instrument, Position leaderPos)
        {
            try
            {
                return leaderAccount.Orders.Count(o => o != null && o.Instrument != null
                    && o.OrderType == OrderType.Limit
                    && o.Instrument.FullName.Equals(instrument.FullName, StringComparison.OrdinalIgnoreCase)
                    && RiskGuardAddOn.ProvidesCoverage(o.OrderState)
                    && RiskGuardAddOn.IsProtectiveSide(o, leaderPos.MarketPosition)
                    && (string.IsNullOrEmpty(o.Name) || !o.Name.Contains("COPIER")));
            }
            catch { return 0; }
        }

        // `internal` so the harness can execute it: this and TranslateSymbol must
        // name the same follower instrument, and nothing was checking that.
        internal Instrument ResolveFollowerInstrument(CopierRelationship rel, Instrument leaderInstrument)
        {
            if (leaderInstrument == null) return null;

            // Deliberately NOT short-circuiting on AutoSymbolConversion. That test
            // used to sit here, ahead of the mapping, while TranslateSymbol -- which
            // the actual copy path uses -- honours an explicit CustomSymbolMappings
            // entry regardless of the flag. With the flag off and a cross mapping
            // set, the copy went to MES while the bracket was computed against MNQ,
            // and ArePricesComparable(MNQ, MNQ) is true, so a leader stop distance
            // in MNQ points would be mirrored onto an MES position as a FABRICATED
            // risk level -- the hazard P1-22's guard exists to prevent, reached by
            // making one decision in two places.
            //
            // TranslateSymbol already applies the flag correctly (explicit mappings
            // always, the automatic mini/micro table only when enabled), so there is
            // exactly one answer to "which instrument does this follower trade?".
            string translated = TranslateSymbol(leaderInstrument.FullName, rel);
            if (string.Equals(translated, leaderInstrument.FullName, StringComparison.OrdinalIgnoreCase))
                return leaderInstrument;

            return Instrument.GetInstrument(translated) ?? leaderInstrument;
        }

        /// <summary>
        /// Brings the follower's protective stop into line with the bracket. Submits one if none
        /// exists, replaces it if the leader moved its stop or the follower's size changed, and
        /// does nothing at all until both the anchor and the distance are known.
        /// Broker calls are made OUTSIDE `_lock`.
        /// </summary>
        /// <summary>
        /// P3-30. What this leg should be, and what to do about the legs the BROKER actually
        /// holds -- as opposed to the single Order reference this engine happens to be caching.
        ///
        /// This is the whole point of the reconciler. Both leg syncs used to decide from
        /// `bracket.WorkingStop` / `bracket.WorkingTarget` alone and never enumerated
        /// `followerAcc.Orders`, so a leg that existed at the broker but was not the one we
        /// held a reference to was invisible -- and therefore permanent. That is what "two
        /// working COPIER_TARGETs against one lot" was on 2026-08-10 (P0-59): not a leg placed
        /// wrongly, a leg nothing was capable of noticing afterwards.
        ///
        /// Returns only <paramref name="legName"/>'s actions, so the two legs keep their
        /// deliberately asymmetric handling (§4r) while sharing one decision.
        /// </summary>
        /// <param name="submitInFlight">
        /// P3-31's half, and NOT the same thing as <c>bracket.StopInFlight</c>. The bracket flags
        /// are mutual exclusion between two SYNCS; this is "an order has been submitted and has
        /// not appeared in `Account.Orders` yet". Passing the bracket flag here was the first
        /// wiring of this function and it placed no stop at all: `SyncFollowerStop` sets the
        /// reservation before calling in, so the reconcile suppressed the very Create the sync
        /// existed to make. The event-driven callers pass false, because the reservation already
        /// serialises them and the submitted leg is recorded in `bracket.WorkingStop` -- which is
        /// folded into `owned` below -- before any second pass can run. A timer-driven caller
        /// (P3-31 proper) is what needs a real ledger, and does not exist yet.
        /// </param>
        private List<ReconcileAction> DecideLegActions(
            Account followerAcc, Instrument instrument, FollowerBracket bracket,
            string legName, bool submitInFlight, out DesiredBracket desired)
        {
            desired = null;
            var empty = new List<ReconcileAction>();
            if (followerAcc == null || instrument == null || bracket == null) return empty;

            MarketPosition bracketSide;
            int bracketQty;
            double entry, stopOffset, targetOffset;
            lock (_lock)
            {
                bracketSide = bracket.FollowerSide;
                bracketQty = bracket.FollowerQuantity;
                entry = bracket.FollowerEntryPrice;
                stopOffset = bracket.StopOffset;
                targetOffset = bracket.TargetOffset;
            }

            // P0-50: the LIVE position, re-read immediately before any decision to touch the
            // broker. On 2026-08-07 three COPIER_STOPs were submitted against a FLAT Sim-ORB
            // after the trade had closed, each cancelling the last, because the decision was
            // made from a stale snapshot. **An orphan stop on a flat account is not a
            // leftover, it is a new position in the opposite direction the moment it
            // triggers.**
            Position livePos = null;
            try
            {
                livePos = followerAcc.Positions.FirstOrDefault(p =>
                    p.Instrument != null &&
                    p.Instrument.FullName.Equals(instrument.FullName, StringComparison.OrdinalIgnoreCase));
            }
            catch { }

            MarketPosition liveSide = livePos == null ? MarketPosition.Flat : livePos.MarketPosition;
            int liveQty = livePos == null ? 0 : livePos.Quantity;

            desired = CopierBracketReconciler.ComputeDesiredBracket(
                bracketSide, bracketQty, liveSide, liveQty,
                entry, stopOffset, targetOffset,
                // The instrument's OWN rounder, not a reimplementation: the desired price is
                // compared against the price on the working order, and a one-tick disagreement
                // between two rounders would fail every comparison and re-drive the leg forever.
                delegate(double p) { return RoundLegToTick(instrument, p); });

            var owned = CopierBracketReconciler.CollectCandidateOrders(followerAcc, instrument);

            // The engine's own cached references, folded in. `Account.Orders` is the source of
            // truth and finds the duplicates the cache cannot -- but a leg submitted moments ago
            // may not have appeared there yet, and the cache is the only thing that knows about
            // it. Feeding both makes the union of what either can see; Reconcile de-duplicates
            // by reference, so a leg in both lists is still one leg.
            AddCandidate(owned, bracket.WorkingStop);
            AddCandidate(owned, bracket.WorkingTarget);

            // The same flag for both legs: this call only ever consumes one of them, and the
            // caller is asking about the leg it named.
            var all = CopierBracketReconciler.Reconcile(desired, owned, submitInFlight, submitInFlight);

            var mine = new List<ReconcileAction>();
            foreach (var a in all)
                if (a.Leg.Name == legName) mine.Add(a);
            return mine;
        }

        /// <summary>
        /// Appends a cached leg to the candidate list. Deliberately does NOT de-duplicate:
        /// `Reconcile` does that by reference, because it is the function that has to be right
        /// about "one order is one leg" whatever list it is handed. A second check here looked
        /// like a safety net and was unreachable -- a mutation removing it left the whole suite
        /// green, which is how it was found.
        /// </summary>
        private static void AddCandidate(List<Order> orders, Order o)
        {
            if (orders == null || o == null) return;
            orders.Add(o);
        }

        private void SyncFollowerStopOnce(Account followerAcc, Instrument instrument, FollowerBracket bracket)
        {
            if (followerAcc == null || instrument == null || bracket == null) return;

            DesiredBracket desired;
            var actions = DecideLegActions(
                followerAcc, instrument, bracket, CopierBracketReconciler.OwnedStopName,
                false, out desired);
            if (desired == null || actions.Count == 0) return;

            // ---- the position is gone, or is not the one this bracket was built for ----
            //
            // Every owned leg is Forbidden here, and the reconcile has already said so. The
            // bracket is stood down as well: it must not go on believing it protects something.
            if (!desired.HasPosition)
            {
                string stoodDownAccount = null;
                lock (_lock)
                {
                    stoodDownAccount = bracket.FollowerAccountName;
                    bracket.FollowerQuantity = 0;
                    bracket.FollowerSide = MarketPosition.Flat;

                    // P0-63. If this was the last active bracket for the account, clear the
                    // provider-ignore mark. The account may be reconfigured to a different
                    // provider before its next use; permanently bypassing Change() on a real
                    // provider would reopen the naked window on every trail step.
                    bool anyOtherActive = false;
                    foreach (var kvp in _followerBrackets)
                    {
                        FollowerBracket other = kvp.Value;
                        if (other == bracket) continue;
                        if (other.FollowerQuantity != 0
                            && string.Equals(other.FollowerAccountName, stoodDownAccount, StringComparison.OrdinalIgnoreCase))
                        {
                            anyOtherActive = true;
                            break;
                        }
                    }
                    if (!anyOtherActive) _accountsIgnoringChange.Remove(stoodDownAccount);
                }
                foreach (var a in actions)
                {
                    if (a.Verb != ReconcileVerb.Cancel) continue;
                    try { followerAcc.Cancel(new[] { a.Subject }); } catch { }
                }
                NinjaTrader.Code.Output.Process(
                    $"[CopierEngine] BRACKET_ABORTED_FLAT: {followerAcc.Name} {instrument.FullName}: {desired.Reason}; no stop placed.",
                    PrintTo.OutputTab1);
                return;
            }

            // ---- duplicates go first, whatever happens to the keeper ----
            //
            // This is the action the old sync could not produce at all, and the reason this
            // path was rewritten. Cancelling a duplicate is not a submission, so it does not
            // spend the attempt budget: refusing to clean up because a leg has been rejected
            // three times would leave two stops behind one position (P1-56 -- qty 1 AND qty 2
            // behind 2 lots, which FLIPS the follower when both fire).
            var keeperActions = new List<ReconcileAction>();
            foreach (var a in actions)
            {
                bool isDuplicateSweep = a.Verb == ReconcileVerb.Cancel
                    && a.Reason != null && a.Reason.StartsWith("duplicate");
                if (!isDuplicateSweep) { keeperActions.Add(a); continue; }
                try
                {
                    followerAcc.Cancel(new[] { a.Subject });
                    CopierLog(followerAcc.Name, "BRACKET_DUPLICATE_CANCELLED",
                        $"{instrument.FullName}: {a.Reason}. The event-driven sync could not see this leg "
                        + "at all -- it read one cached Order reference and never enumerated the account.");
                }
                catch (Exception dex)
                {
                    CopierLog(followerAcc.Name, "BRACKET_DUPLICATE_CANCEL_FAILED",
                        $"{instrument.FullName}: {dex.Message}. TWO protective stops may still be working; "
                        + "the follower will be FLIPPED if both fire.");
                }
            }
            if (keeperActions.Count == 0) return;

            // P0-61. A change against this leg is already in flight, so the broker must not be
            // touched this pass -- NT8 drops the second change AND reverts the order. But the
            // newer instruction must not be LOST either, or the leg keeps the old price and size
            // for the life of the position, which is the same under-covered follower by a quieter
            // route. `ReDriveDeferredLeg` re-applies it when the leg settles.
            //
            // Its own flag, NOT `StopResyncOwed`: that one is consumed by SyncFollowerStop's pass
            // loop the instant it is set, which re-drives while the leg is still mid-change and
            // burns the pass budget deferring. See ReDriveDeferredLeg.
            foreach (var a in keeperActions)
            {
                if (a.Verb != ReconcileVerb.Defer) continue;
                lock (_lock) { bracket.StopChangeDeferred = true; }
                CopierLog(followerAcc.Name, "BRACKET_DEFERRED",
                    $"{instrument.FullName}: {a.Reason}");
                return;
            }

            Order toModify = null;
            Order toCancel = null;
            bool wantsCreate = false;
            foreach (var a in keeperActions)
            {
                if (a.Verb == ReconcileVerb.Modify) toModify = a.Subject;
                else if (a.Verb == ReconcileVerb.Cancel) toCancel = a.Subject;
                else if (a.Verb == ReconcileVerb.Create) wantsCreate = true;
            }

            double stopPrice = desired.Stop.Price;
            int qty = desired.Stop.Quantity;
            OrderAction action = desired.Stop.Action;

            lock (_lock)
            {
                if (bracket.StopAttempts >= MaxBracketStopAttempts)
                {
                    // Bounded: keep retrying a broker that will not accept the order and the
                    // copier becomes the order flood it was hardened against.
                    return;
                }
                bracket.StopAttempts++;
            }

            var livePos = followerAcc.Positions.FirstOrDefault(p =>
                p.Instrument != null &&
                p.Instrument.FullName.Equals(instrument.FullName, StringComparison.OrdinalIgnoreCase));
            if (livePos == null) return;

            try
            {
                // Outside the lock: Cancel/Change/CreateOrder/Submit are broker calls, and holding
                // _lock across them is the P1-10/P1-35 violation.

                // Re-clamped to the live position one last time. `desired.Quantity` was already
                // clamped when it was computed, but the position can move between the decision
                // and here, and a stop larger than the position FLIPS it on trigger.
                int liveQty = Math.Min(qty, livePos.Quantity);
                bool providerIgnoresChange = false;

                // A leader trailing its stop is the ordinary case, and cancel-then-create left the
                // follower unprotected on EVERY trail step, between the cancel and the new order's
                // acceptance. Modify the working order instead: one order, no window.
                //
                // The original P0-9 note said "cancel-then-replace, not modify", to stop a stale
                // stop working beside a new one -- that over-covers and flips the follower when
                // both fire. Change() cannot produce that state: there is only ever one order.
                // Verified available: the connection serving every account here advertises the
                // OrderChange feature (/api/connections). Any failure falls through to the
                // cancel-then-create path below, so an unsupporting connection degrades rather
                // than breaks.
                //
                if (toModify != null)
                {
                    lock (_lock) { providerIgnoresChange = _accountsIgnoringChange.Contains(followerAcc.Name); }

                    if (providerIgnoresChange)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_MODIFY_BYPASSED",
                            $"{instrument.FullName}: provider ignored a previous Change() on {followerAcc.Name}; "
                            + "falling back to cancel-then-create.");
                        // P0-63. Clear the stale request record NOW, before any broker call. If a
                        // prior Change() was issued against this order and its settle event has not
                        // yet arrived, leaving the record set would make the subsequent Canceled
                        // event look like a fresh no-op and re-drive, producing a duplicate stop.
                        lock (_lock) { bracket.StopChangeRequest = null; }
                        // The leg the broker refused to change becomes the leg to replace. Both
                        // halves must be set: cancelling without creating is a naked follower,
                        // and it is the failure this fallback exists to avoid.
                        toCancel = toModify;
                        wantsCreate = true;
                    }
                    else
                    {
                        try
                        {
                            // P0-63. Capture the broker's true pre-change values. If the Order
                            // object still carries a previous requested value because an earlier
                            // Change() was ignored and the settle event has not yet updated the
                            // object, fall back to the original recorded for that request.
                            double currentPrice = toModify.StopPrice;
                            int currentQty = toModify.Quantity;
                            double originalPrice = currentPrice;
                            int originalQty = currentQty;

                            LegChangeRequest existing;
                            lock (_lock) { existing = bracket.StopChangeRequest; }
                            if (existing != null && ReferenceEquals(existing.Order, toModify)
                                && Math.Abs(currentPrice - existing.RequestedPrice) <= 1e-9
                                && currentQty == existing.RequestedQuantity)
                            {
                                originalPrice = existing.OriginalPrice;
                                originalQty = existing.OriginalQuantity;
                            }

                            toModify.StopPrice = stopPrice;
                            toModify.Quantity = liveQty;
                            followerAcc.Change(new[] { toModify });

                            lock (_lock)
                            {
                                bracket.WorkingStop = toModify;
                                bracket.StopChangeRequest = new LegChangeRequest
                                {
                                    Order = toModify,
                                    OriginalPrice = originalPrice,
                                    RequestedPrice = stopPrice,
                                    OriginalQuantity = originalQty,
                                    RequestedQuantity = liveQty
                                };
                            }

                            // P1-70: this used to be BRACKET_MODIFIED, asserting "stop moved ... in
                            // place ... no cancel/replace, so no unprotected window" -- three claims
                            // it cannot make yet. Change() is a REQUEST. NT8 leaves the caller's
                            // desired values on the Order until the provider settles, so at this
                            // instant the order *reads* as changed whether or not it was. On
                            // 2026-08-13 this line was written to the live audit log and contradicted
                            // by BRACKET_STOP_CHANGE_IGNORED in the same millisecond.
                            // The confirmation now lives where the evidence is: on settle, in
                            // DetectAndRecoverIgnoredChange.
                            CopierLog(followerAcc.Name, "BRACKET_MODIFY_REQUESTED",
                                $"{instrument.FullName} stop change REQUESTED: {liveQty}@{stopPrice} "
                                + $"(from {originalQty}@{originalPrice}, leader offset "
                                + $"{bracket.StopOffset:+0.##;-0.##}, follower entry {bracket.FollowerEntryPrice}). "
                                + "Not confirmed yet: the provider has not settled it. The settle "
                                + "event says whether it was honoured, ignored, or partly applied.");
                            return;
                        }
                        catch (Exception cex)
                        {
                            CopierLog(followerAcc.Name, "BRACKET_MODIFY_FAILED",
                                $"{instrument.FullName}: {cex.Message}. Falling back to cancel-then-create.");
                            // The leg the broker refused to change becomes the leg to replace. Both
                            // halves must be set: cancelling without creating is a naked follower,
                            // and it is the failure this fallback exists to avoid.
                            toCancel = toModify;
                            wantsCreate = true;
                        }
                    }
                }

                // Cancel the leg we are replacing. If the cancel itself fails, do NOT proceed
                // to CreateOrder/Submit -- a working old leg plus a new leg is the duplicate-
                // stop defect that flips the follower (P1-56).
                bool cancelFailed = false;
                if (toCancel != null)
                {
                    try
                    {
                        followerAcc.Cancel(new[] { toCancel });
                    }
                    catch (Exception cex)
                    {
                        cancelFailed = true;
                        lock (_lock)
                        {
                            if (bracket.StopChangeRequest != null
                                && ReferenceEquals(bracket.StopChangeRequest.Order, toCancel))
                            {
                                bracket.StopChangeRequest = null;
                            }
                        }
                        CopierLog(followerAcc.Name, "BRACKET_CANCEL_FAILED",
                            $"{instrument.FullName}: {cex.Message}. The old stop is still working; "
                            + "not creating a replacement to avoid two protective stops.");
                    }
                }
                if (cancelFailed) return;

                // NOTE: no P0-63 budget refresh here, deliberately. One was added across review
                // rounds 2-4 to answer a finding that a long trail on an ignoring provider would
                // exhaust MaxBracketStopAttempts. That finding is false: OnLeaderOrderUpdate
                // already zeroes StopAttempts whenever the leader's mirrored offset changes, which
                // is every trail step, and TestBracket_P0_63_ALongTrailIsNotStoppedByTheReSubmission
                // Budget pins it over six steps. Mutation testing then confirmed the refresh was
                // decorative -- deleting it changed no test outcome. Unpinned defensive state on the
                // risk leg is not free: it is one more way for the bound that stops an order flood
                // to be reset by accident.
                //
                // A cancel with no create is the reservation case: a submit for this leg is
                // already in flight, so the replacement is that one, not a second one.
                if (!wantsCreate) return;

                // The OCO id for the order about to be created.
                //
                // Re-creating a leg is the ONE case that can need a fresh id: the cancel above may
                // have retired the whole group, and NT8 rejects an id once every leg has gone
                // terminal (handover 4p). A rejected stop is a naked follower, so this path does
                // not gamble -- it mints a fresh id and takes the target down with it, because a
                // working order cannot be moved between groups (there is no OcoChanged field) and
                // a target left in the retired group is paired with nothing. The target sync that
                // follows every stop sync rebuilds it in the new group.
                //
                // Whether cancelling one leg really retires the group is NOT established. This is
                // written to be correct either way; the cost when it does not is one rebuilt
                // target, on a path only reached when Change() has already failed.
                string oco;
                Order staleTarget = null;
                lock (_lock)
                {
                    if (toCancel != null)
                    {
                        staleTarget = bracket.WorkingTarget;
                        bracket.WorkingTarget = null;
                        bracket.OcoId = Guid.NewGuid().ToString();
                        bracket.StopChangeRequest = null;
                    }
                    else
                    {
                        // First creation. If the target got there first its group is live, so
                        // join it -- that is licensed by the live test in handover 4p.
                        string live = LiveLegOcoId(bracket, null);
                        if (!string.IsNullOrEmpty(live)) bracket.OcoId = live;
                        else if (string.IsNullOrEmpty(bracket.OcoId)) bracket.OcoId = Guid.NewGuid().ToString();
                    }
                    oco = bracket.OcoId;
                }

                if (staleTarget != null && RiskGuardAddOn.OccupiesSlot(staleTarget.OrderState))
                {
                    try { followerAcc.Cancel(new[] { staleTarget }); }
                    catch (Exception tex)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_TARGET_CANCEL_FAILED",
                            $"{instrument.FullName}: {tex.Message}. The stale target may still be working "
                            + "in the retired OCO group; the stop below is unaffected.");
                    }
                }

                Order stop = followerAcc.CreateOrder(
                    instrument, action, OrderType.StopMarket, TimeInForce.Day,
                    liveQty, 0, stopPrice, oco, "COPIER_STOP", null);

                if (stop == null)
                {
                    // P0-63. The old leg was cancelled but no replacement could be created. Ask
                    // the in-flight wrapper to re-drive so the follower is not left naked.
                    lock (_lock) { bracket.StopResyncOwed = true; }
                    NinjaTrader.Code.Output.Process(
                        $"[CopierEngine] BRACKET_SUBMIT_FAILED on {followerAcc.Name} {instrument.FullName}: CreateOrder returned null. The follower is UNPROTECTED; will retry.",
                        PrintTo.OutputTab1);
                    return;
                }
                followerAcc.Submit(new[] { stop });

                // Deliberately does NOT reset StopAttempts. The failure this bound exists for is a
                // broker that ACCEPTS the submit and rejects the order a moment later, so
                // "Submit did not throw" is not evidence of protection and resetting here makes
                // the bound unreachable. The budget is refreshed only by a genuinely new
                // instruction from the leader, or by the bracket being released when the follower
                // goes flat. (Caught by this test failing at 21 submissions.)
                lock (_lock) { bracket.WorkingStop = stop; }

                NinjaTrader.Code.Output.Process(
                    $"[CopierEngine] BRACKET_MIRRORED: {followerAcc.Name} {instrument.FullName} stop {liveQty}@{stopPrice} (leader offset {bracket.StopOffset:+0.##;-0.##}, follower entry {bracket.FollowerEntryPrice}).",
                    PrintTo.OutputTab1);
            }
            catch (Exception ex)
            {
                // P0-63. If the cancel itself threw, the old order is still working and the
                // request record still points at it. Leave the record set and the next OrderUpdate
                // will re-detect the no-op and re-drive forever. Clear it when the order we were
                // trying to cancel is the one the record belongs to.
                int attempts;
                lock (_lock)
                {
                    attempts = bracket.StopAttempts;
                    if (toCancel != null && bracket.StopChangeRequest != null
                        && ReferenceEquals(bracket.StopChangeRequest.Order, toCancel))
                    {
                        bracket.StopChangeRequest = null;
                    }
                }
                bool exhausted = attempts >= MaxBracketStopAttempts;
                NinjaTrader.Code.Output.Process(
                    $"[CopierEngine] BRACKET_SUBMIT_FAILED on {followerAcc.Name} {instrument.FullName} "
                    + $"(attempt {attempts}/{MaxBracketStopAttempts}): {ex.Message}. The follower is UNPROTECTED"
                    + (exhausted
                        ? " and the copier has GIVEN UP on this position -- RiskGuard's auto-stop is the only remaining cover, and only if it is armed and live."
                        : "; it will retry on the next leader stop update or follower fill."),
                    PrintTo.OutputTab1);
            }
        }

        private void SyncFollowerStop(Account followerAcc, Instrument instrument, FollowerBracket bracket)
        {
            if (followerAcc == null || instrument == null || bracket == null) return;

            lock (_lock)
            {
                if (bracket.StopInFlight)
                {
                    bracket.StopResyncOwed = true;
                    return;
                }
                bracket.StopInFlight = true;
            }

            try
            {
                for (int pass = 0; pass <= MaxBracketResyncPasses; pass++)
                {
                    SyncFollowerStopOnce(followerAcc, instrument, bracket);

                    bool owed;
                    lock (_lock)
                    {
                        owed = bracket.StopResyncOwed;
                        bracket.StopResyncOwed = false;
                    }

                    if (!owed)
                        break;

                    if (pass == MaxBracketResyncPasses)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_RESYNC_BOUND",
                            $"{instrument.FullName}: re-sync bound reached; stopping to avoid order flood.");
                        break;
                    }
                }
            }
            finally
            {
                lock (_lock)
                {
                    bracket.StopInFlight = false;
                }
            }
        }

        /// <summary>
        /// Snaps a mirrored leg price to the instrument's tick.
        ///
        /// Both legs are computed from the follower's AVERAGE fill price, and an average across
        /// partial fills at different prices is routinely off-tick -- so the leg is off-tick even
        /// though every price the leader gave us was clean. A live COPIER_TARGET sat Rejected at
        /// 29905.625 on MNQ, whose tick is 0.25. NT8 rounds off-tick prices silently on some paths
        /// (the ATM path's own 29897.419 was rounded at Submitted) and rejects on others; the
        /// copier does not need to know which, because it has no reason to send one either way.
        ///
        /// RiskGuard's auto-stop already does this before submitting. Failing safe on a throw
        /// returns the price unrounded, which is exactly what happened before this existed.
        /// </summary>
        private static double RoundLegToTick(Instrument instrument, double price)
        {
            try
            {
                if (instrument == null || instrument.MasterInstrument == null) return price;
                if (instrument.MasterInstrument.TickSize <= 0) return price;
                return instrument.MasterInstrument.RoundToTickSize(price);
            }
            catch { return price; }
        }

        /// <summary>
        /// The OCO id of a leg of this bracket that is still live, or null if the group is dead.
        /// Must be called under `_lock`.
        ///
        /// Reads the ORDER's id rather than `bracket.OcoId`: the cached value records what we last
        /// intended, the order records what the broker actually has, and only the second one
        /// answers "is there a group to join".
        /// </summary>
        private static string LiveLegOcoId(FollowerBracket bracket, Order exclude)
        {
            Order[] legs = { bracket.WorkingStop, bracket.WorkingTarget };
            foreach (var leg in legs)
            {
                if (leg == null || ReferenceEquals(leg, exclude)) continue;
                if (!RiskGuardAddOn.OccupiesSlot(leg.OrderState)) continue;
                if (!string.IsNullOrEmpty(leg.Oco)) return leg.Oco;
            }
            return null;
        }

        /// <summary>
        /// P0-9 item (1). Brings the follower's profit target into line with the bracket, paired
        /// with the mirrored stop by a shared OCO id.
        ///
        /// A sibling of the stop sync rather than a branch inside it, and the asymmetry between
        /// them is the design:
        ///
        /// - the stop is RISK. It may re-mint the OCO id and tear the target down to rebuild the
        ///   pair, because a rejected stop is a naked follower.
        /// - the target is UPSIDE. It joins whatever live group the stop is in and never cancels
        ///   or re-creates the stop. If the target never places at all, the follower still exits
        ///   when the leader's own target fill is copied -- which is what happened before this
        ///   existed, so the worst case here is the previous behaviour.
        /// </summary>
        private void SyncFollowerTargetOnce(Account followerAcc, Instrument instrument, FollowerBracket bracket)
        {
            if (followerAcc == null || instrument == null || bracket == null) return;

            DesiredBracket desired;
            var actions = DecideLegActions(
                followerAcc, instrument, bracket, CopierBracketReconciler.OwnedTargetName,
                false, out desired);
            if (desired == null || actions.Count == 0) return;

            // P0-50 on the target leg. An orphan LIMIT against a flat account opens a position
            // when it fills exactly as an orphan stop does when it triggers.
            //
            // Note what this deliberately does NOT do: it leaves FollowerQuantity and FollowerSide
            // alone. Zeroing them here would let a target sync switch the stop sync off.
            if (!desired.HasPosition)
            {
                foreach (var a in actions)
                {
                    if (a.Verb != ReconcileVerb.Cancel) continue;
                    try { followerAcc.Cancel(new[] { a.Subject }); } catch { }
                }
                lock (_lock) { bracket.WorkingTarget = null; }
                CopierLog(followerAcc.Name, "BRACKET_TARGET_ABORTED",
                    $"{instrument.FullName}: {desired.Reason}; no target placed.");
                return;
            }

            // Duplicates first, and outside the attempt budget -- see the stop leg for why.
            // Two working COPIER_TARGETs behind one lot is the defect that opened P0-59, and it
            // was permanent precisely because nothing enumerated the account's orders.
            var keeperActions = new List<ReconcileAction>();
            foreach (var a in actions)
            {
                bool isDuplicateSweep = a.Verb == ReconcileVerb.Cancel
                    && a.Reason != null && a.Reason.StartsWith("duplicate");
                if (!isDuplicateSweep) { keeperActions.Add(a); continue; }
                try
                {
                    followerAcc.Cancel(new[] { a.Subject });
                    CopierLog(followerAcc.Name, "BRACKET_DUPLICATE_CANCELLED",
                        $"{instrument.FullName}: {a.Reason}.");
                }
                catch (Exception dex)
                {
                    CopierLog(followerAcc.Name, "BRACKET_DUPLICATE_CANCEL_FAILED",
                        $"{instrument.FullName}: {dex.Message}. Two targets may still be working.");
                }
            }
            if (keeperActions.Count == 0) return;

            // As the stop leg: a change already in flight means wait, not push. Its own owed
            // flag, not the stop's -- an in-flight target must never make the RISK leg queue.
            foreach (var a in keeperActions)
            {
                if (a.Verb != ReconcileVerb.Defer) continue;
                lock (_lock) { bracket.TargetChangeDeferred = true; }
                CopierLog(followerAcc.Name, "BRACKET_TARGET_DEFERRED",
                    $"{instrument.FullName}: {a.Reason}");
                return;
            }

            Order toModify = null;
            Order toCancel = null;
            bool wantsCreate = false;
            foreach (var a in keeperActions)
            {
                if (a.Verb == ReconcileVerb.Modify) toModify = a.Subject;
                else if (a.Verb == ReconcileVerb.Cancel) toCancel = a.Subject;
                else if (a.Verb == ReconcileVerb.Create) wantsCreate = true;
            }

            double targetPrice = desired.Target.Price;
            int qty = desired.Target.Quantity;
            OrderAction action = desired.Target.Action;

            lock (_lock)
            {
                if (bracket.TargetAttempts >= MaxBracketTargetAttempts) return;
                bracket.TargetAttempts++;
            }

            var livePos = followerAcc.Positions.FirstOrDefault(p =>
                p.Instrument != null &&
                p.Instrument.FullName.Equals(instrument.FullName, StringComparison.OrdinalIgnoreCase));
            if (livePos == null) return;

            try
            {
                // Broker calls outside `_lock` (P1-10/P1-35), as the stop sync does.
                int liveQty = Math.Min(qty, livePos.Quantity);
                bool providerIgnoresChange = false;

                // Modify in place where possible: it preserves OCO group membership -- confirmed
                // live on 2026-08-10, a trailed leg kept both its orderId and its oco -- so the
                // pair survives without any id being re-minted.
                if (toModify != null)
                {
                    lock (_lock) { providerIgnoresChange = _accountsIgnoringChange.Contains(followerAcc.Name); }

                    if (providerIgnoresChange)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_TARGET_MODIFY_BYPASSED",
                            $"{instrument.FullName}: provider ignored a previous Change() on {followerAcc.Name}; "
                            + "falling back to cancel-then-create.");
                        // P0-63. Clear the stale request record before any broker call so a later
                        // Canceled event cannot be mistaken for a fresh no-op and re-driven.
                        lock (_lock) { bracket.TargetChangeRequest = null; }
                        toCancel = toModify;
                        wantsCreate = true;
                    }
                    else
                    {
                        try
                        {
                            // P0-63. Capture the broker's true pre-change values, falling back to
                            // the original recorded for an earlier ignored Change() if the Order
                            // object still carries that requested value.
                            double currentPrice = toModify.LimitPrice;
                            int currentQty = toModify.Quantity;
                            double originalPrice = currentPrice;
                            int originalQty = currentQty;

                            LegChangeRequest existing;
                            lock (_lock) { existing = bracket.TargetChangeRequest; }
                            if (existing != null && ReferenceEquals(existing.Order, toModify)
                                && Math.Abs(currentPrice - existing.RequestedPrice) <= 1e-9
                                && currentQty == existing.RequestedQuantity)
                            {
                                originalPrice = existing.OriginalPrice;
                                originalQty = existing.OriginalQuantity;
                            }

                            toModify.LimitPrice = targetPrice;
                            toModify.Quantity = liveQty;
                            followerAcc.Change(new[] { toModify });

                            lock (_lock)
                            {
                                bracket.WorkingTarget = toModify;
                                bracket.TargetChangeRequest = new LegChangeRequest
                                {
                                    Order = toModify,
                                    OriginalPrice = originalPrice,
                                    RequestedPrice = targetPrice,
                                    OriginalQuantity = originalQty,
                                    RequestedQuantity = liveQty
                                };
                            }

                            // P1-70, same as the stop leg: a request, not an outcome.
                            CopierLog(followerAcc.Name, "BRACKET_TARGET_MODIFY_REQUESTED",
                                $"{instrument.FullName} target change REQUESTED: {liveQty}@{targetPrice} "
                                + $"(leader offset {bracket.TargetOffset:+0.##;-0.##}, follower entry "
                                + $"{bracket.FollowerEntryPrice}). Not confirmed yet: the provider has "
                                + "not settled it. The settle event says whether it was honoured.");
                            return;
                        }
                        catch (Exception cex)
                        {
                            CopierLog(followerAcc.Name, "BRACKET_TARGET_MODIFY_FAILED",
                                $"{instrument.FullName}: {cex.Message}. Falling back to cancel-then-create.");
                            toCancel = toModify;
                            wantsCreate = true;
                        }
                    }
                }

                // If the cancel itself fails, do NOT create a replacement -- two working targets
                // behind one position closes the position when the first fills and leaves the
                // second as an orphan LIMIT that opens a new position (P0-50).
                bool cancelFailed = false;
                if (toCancel != null)
                {
                    try
                    {
                        followerAcc.Cancel(new[] { toCancel });
                    }
                    catch (Exception cex)
                    {
                        cancelFailed = true;
                        lock (_lock)
                        {
                            if (bracket.TargetChangeRequest != null
                                && ReferenceEquals(bracket.TargetChangeRequest.Order, toCancel))
                            {
                                bracket.TargetChangeRequest = null;
                            }
                        }
                        CopierLog(followerAcc.Name, "BRACKET_TARGET_CANCEL_FAILED",
                            $"{instrument.FullName}: {cex.Message}. The old target is still working; "
                            + "not creating a replacement to avoid two targets.");
                    }
                }
                if (cancelFailed) return;

                // No P0-63 budget refresh here either, and for the same measured reason as the stop
                // leg above.
                //
                // A cancel with no create means a target submit is already in flight.
                if (!wantsCreate) return;

                string oco;
                lock (_lock)
                {
                    // Join the stop's group if it is live -- an id can be joined while its group
                    // still has a live member (handover 4p). Only mint a fresh one when there is
                    // no live sibling, which is the case NT8 actually rejects.
                    //
                    // Unlike the stop's re-create path this never cancels the sibling to force a
                    // rebuild. If the cancel above did retire the group, the stop's own
                    // OrderUpdate re-submits it and the pair reforms a beat later; cancelling a
                    // working protective stop to tidy up an OCO group is not a trade worth making.
                    if (toCancel != null)
                    {
                        bracket.TargetChangeRequest = null;
                    }
                    string live = LiveLegOcoId(bracket, toCancel);
                    bracket.OcoId = !string.IsNullOrEmpty(live) ? live : Guid.NewGuid().ToString();
                    oco = bracket.OcoId;
                }

                Order target = followerAcc.CreateOrder(
                    instrument, action, OrderType.Limit, TimeInForce.Day,
                    liveQty, targetPrice, 0, oco, "COPIER_TARGET", null);

                if (target == null)
                {
                    CopierLog(followerAcc.Name, "BRACKET_TARGET_FAILED",
                        $"{instrument.FullName}: CreateOrder returned null. The follower keeps its stop "
                        + "and still exits when the leader's target fill is copied; only fill quality is lost.");
                    return;
                }

                followerAcc.Submit(new[] { target });
                lock (_lock) { bracket.WorkingTarget = target; }

                CopierLog(followerAcc.Name, "BRACKET_TARGET_MIRRORED",
                    $"{instrument.FullName} target {liveQty}@{targetPrice} "
                    + $"(leader offset {bracket.TargetOffset:+0.##;-0.##}, follower entry {bracket.FollowerEntryPrice}, oco {oco}).");
            }
            catch (Exception ex)
            {
                // P0-63. If the cancel itself threw, the old order is still working and the
                // request record still points at it. Clear it when the order we were trying to
                // cancel is the one the record belongs to, so the next OrderUpdate does not
                // re-detect a stale no-op and spin.
                int attempts;
                lock (_lock)
                {
                    attempts = bracket.TargetAttempts;
                    if (toCancel != null && bracket.TargetChangeRequest != null
                        && ReferenceEquals(bracket.TargetChangeRequest.Order, toCancel))
                    {
                        bracket.TargetChangeRequest = null;
                    }
                }
                CopierLog(followerAcc.Name, "BRACKET_TARGET_FAILED",
                    $"{instrument.FullName} (attempt {attempts}/{MaxBracketTargetAttempts}): {ex.Message}. "
                    + "The stop is unaffected and the follower still exits on the copied leader target fill"
                    + (attempts >= MaxBracketTargetAttempts ? "; the copier has given up on mirroring this target." : "."));
            }
        }

        /// <summary>
        /// P1-56's reservation, applied to the target leg. Its own flags, not the stop's: sharing
        /// one would let an in-flight target sync make the RISK leg wait its turn.
        /// </summary>
        private void SyncFollowerTarget(Account followerAcc, Instrument instrument, FollowerBracket bracket)
        {
            if (followerAcc == null || instrument == null || bracket == null) return;

            lock (_lock)
            {
                if (bracket.TargetInFlight)
                {
                    bracket.TargetResyncOwed = true;
                    return;
                }
                bracket.TargetInFlight = true;
            }

            try
            {
                for (int pass = 0; pass <= MaxBracketResyncPasses; pass++)
                {
                    SyncFollowerTargetOnce(followerAcc, instrument, bracket);

                    bool owed;
                    lock (_lock)
                    {
                        owed = bracket.TargetResyncOwed;
                        bracket.TargetResyncOwed = false;
                    }

                    if (!owed)
                        break;

                    if (pass == MaxBracketResyncPasses)
                    {
                        CopierLog(followerAcc.Name, "BRACKET_TARGET_RESYNC_BOUND",
                            $"{instrument.FullName}: re-sync bound reached; stopping to avoid order flood.");
                        break;
                    }
                }
            }
            finally
            {
                lock (_lock)
                {
                    bracket.TargetInFlight = false;
                }
            }
        }

        /// <summary>
        /// Syncs both legs, STOP FIRST, always.
        ///
        /// Every call site goes through this rather than driving one leg directly. The legs share
        /// an OCO group, so a site that syncs only one of them leaves the pair half-rebuilt -- and
        /// that is a mistake that reads as correct at the call site. Stop first because protection
        /// precedes upside, and because it gives the target a live group to join.
        /// </summary>
        private void SyncFollowerBracket(Account followerAcc, Instrument instrument, FollowerBracket bracket)
        {
            SyncFollowerStop(followerAcc, instrument, bracket);
            SyncFollowerTarget(followerAcc, instrument, bracket);
        }

        /// <summary>
        /// The follower is flat in this instrument: cancel every protective leg we placed and drop
        /// the bracket. An orphaned leg left working would open a brand new position -- the stop
        /// when it triggers, the target when it fills.
        /// </summary>
        private void ReleaseFollowerBracket(Account followerAcc, string instrumentFullName)
        {
            if (followerAcc == null) return;
            string key = BracketKey(followerAcc.Name, instrumentFullName);

            var toCancel = new List<Order>();
            lock (_lock)
            {
                FollowerBracket bracket;
                if (!_followerBrackets.TryGetValue(key, out bracket)) return;
                if (bracket.WorkingStop != null && RiskGuardAddOn.OccupiesSlot(bracket.WorkingStop.OrderState))
                    toCancel.Add(bracket.WorkingStop);
                if (bracket.WorkingTarget != null && RiskGuardAddOn.OccupiesSlot(bracket.WorkingTarget.OrderState))
                    toCancel.Add(bracket.WorkingTarget);
                _followerBrackets.Remove(key);
            }

            if (toCancel.Count == 0) return;
            try
            {
                followerAcc.Cancel(toCancel.ToArray());   // outside the lock, as above
                NinjaTrader.Code.Output.Process(
                    $"[CopierEngine] BRACKET_RELEASED: {followerAcc.Name} {instrumentFullName} is flat; cancelled {toCancel.Count} mirrored leg(s).",
                    PrintTo.OutputTab1);
            }
            catch (Exception ex)
            {
                NinjaTrader.Code.Output.Process(
                    $"[CopierEngine] BRACKET_RELEASE_FAILED on {followerAcc.Name} {instrumentFullName}: {ex.Message}. A protective leg may still be working against a flat position.",
                    PrintTo.OutputTab1);
            }
        }

        /// <summary>Number of follower brackets currently tracked (test/diagnostic seam).</summary>
        internal int TrackedBracketCount { get { lock (_lock) { return _followerBrackets.Count; } } }

        /// <summary>
        /// Drops all bracket state. The engine is a singleton, so without this one test's
        /// brackets become the next test's starting conditions.
        /// </summary>
        internal void ResetBracketsForTest()
        {
            lock (_lock)
            {
                _followerBrackets.Clear();
                _accountsIgnoringChange.Clear();
            }
        }

        internal double GetMirroredStopPriceForTest(string followerAccount, string instrumentFullName)
        {
            lock (_lock)
            {
                FollowerBracket b;
                if (!_followerBrackets.TryGetValue(BracketKey(followerAccount, instrumentFullName), out b)) return double.NaN;
                return b.WorkingStop != null ? b.WorkingStop.StopPrice : double.NaN;
            }
        }

        /// <summary>
        /// The side the bracket believes the follower holds (test/diagnostic seam). `Flat` means
        /// the bracket has been stood down and no leg may be placed for it.
        ///
        /// Alongside the hook above rather than inside `#if TESTING`, deliberately: P1-47 compiled
        /// clean under net8.0 with the suite green and broke the net48 build, because the methods
        /// sat inside the conditional.
        /// </summary>
        internal MarketPosition GetBracketSideForTest(string followerAccount, string instrumentFullName)
        {
            lock (_lock)
            {
                FollowerBracket b;
                if (!_followerBrackets.TryGetValue(BracketKey(followerAccount, instrumentFullName), out b))
                    return MarketPosition.Flat;
                return b.FollowerSide;
            }
        }

        // ------------------------------------------------------------------
        // COPY LATENCY AND SLIPPAGE (P1-22)
        //
        // Every copy went out as a bare OrderType.Market with no reference to what the leader
        // actually paid, no measurement of the gap, and no ceiling on it -- while
        // TradeCopierWindow.cs:799 rendered `LatencyMs` and `AvgSlippageTicks` as though they
        // were real. Nothing anywhere wrote either field, so the UI reported 0ms / 0.0t however
        // badly a copy filled. A displayed number that is never computed is worse than no
        // number: it reads as evidence that the copy was clean.
        //
        // The follower's own fill is the only place this can be observed, and it arrives as an
        // ExecutionUpdate on the follower account -- which OnExecution drops at recursion guard
        // 1. So the measurement hooks in immediately before that drop.
        // ------------------------------------------------------------------

        private class PendingCopy
        {
            public string RelationshipId;
            public string LeaderAccountName;
            public string FollowerAccountName;
            public DateTime LeaderExecTime;    // raw exec.Time; never converted (see ObserveFollowerFill)
            public DateTime SubmittedUtc;
            public double LeaderFillPrice;
            public double FollowerTickSize;
            public bool PriceComparable;
            public bool FollowerIsBuy;
            public bool IsEntry;
        }

        /// <summary>
        /// Reference identity for Order keys. **`Order.OrderId` must not be used as a key**: NT8
        /// does not guarantee it is unique, and it can change over an order's lifetime across the
        /// historical->live transition. `RiskGuardAddOn.cs:4481` already carries that warning and
        /// tracks recognised stops by object reference for the same reason (RiskGuardAddOn.md
        /// §6.6). Keying on the id here would mis-attribute a fill to the wrong copy and could
        /// quarantine the wrong relationship -- and no test would catch it, because the test stub
        /// hands out a stable GUID per order.
        ///
        /// `RuntimeHelpers.GetHashCode` is used rather than `order.GetHashCode()` so the map is
        /// unaffected if Order ever overrides equality.
        /// </summary>
        private sealed class OrderReferenceComparer : IEqualityComparer<Order>
        {
            public static readonly OrderReferenceComparer Instance = new OrderReferenceComparer();
            public bool Equals(Order x, Order y) { return ReferenceEquals(x, y); }
            public int GetHashCode(Order obj) { return System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(obj); }
        }

        // Keyed by the follower Order object. Bounded FIFO for the same reason
        // `_copiedExecutionIds` is: a copy whose fill never arrives (rejected, cancelled,
        // expired) would otherwise leak an entry per order forever, and hold the Order alive with
        // it. P1-14 is this exact defect elsewhere in the addon.
        private readonly Dictionary<Order, PendingCopy> _pendingCopies =
            new Dictionary<Order, PendingCopy>(OrderReferenceComparer.Instance);
        private readonly Queue<Order> _pendingCopyQueue = new Queue<Order>();
        private const int MaxPendingCopies = 2000;

        // Sample counts for the running slippage mean, keyed by relationship id. Held here rather
        // than on CopierRelationship so the persisted config does not accumulate telemetry.
        private readonly Dictionary<string, int> _slippageSampleCounts =
            new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// True when two instrument roots track the same underlying at the same price, so a fill
        /// price on one can be compared to a fill price on the other. Equal roots qualify, as does
        /// either direction of the built-in mini/micro matrix (NQ/MNQ fill at the same index
        /// level). A root pairing that only exists because of `CustomSymbolMappings` does not:
        /// mapping ES to NQ is legitimate, but their prices are unrelated and a "slippage" figure
        /// derived from them would be pure noise -- and could quarantine a healthy relationship.
        /// </summary>
        internal static bool ArePricesComparable(string leaderRoot, string followerRoot)
        {
            if (string.IsNullOrEmpty(leaderRoot) || string.IsNullOrEmpty(followerRoot)) return false;
            if (leaderRoot.Equals(followerRoot, StringComparison.OrdinalIgnoreCase)) return true;

            string a = leaderRoot.ToUpper();
            string b = followerRoot.ToUpper();
            switch (a)
            {
                case "NQ":  return b == "MNQ";
                case "ES":  return b == "MES";
                case "YM":  return b == "MYM";
                case "CL":  return b == "MCL";
                case "GC":  return b == "MGC";
                case "RTY": return b == "M2K";
                case "MNQ": return b == "NQ";
                case "MES": return b == "ES";
                case "MYM": return b == "YM";
                case "MCL": return b == "CL";
                case "MGC": return b == "GC";
                case "M2K": return b == "RTY";
            }
            return false;
        }

        private static string RootOf(string fullName)
        {
            if (string.IsNullOrEmpty(fullName)) return null;
            int split = fullName.IndexOf(' ');
            return (split >= 0 ? fullName.Substring(0, split) : fullName).ToUpper();
        }

        private void RecordPendingCopy(
            Order followerOrder, CopierRelationship rel, Execution leaderExec,
            Instrument targetInstrument, OrderAction followerAction, bool isExit)
        {
            if (followerOrder == null || rel == null || leaderExec == null) return;

            double tickSize = 0.0;
            if (targetInstrument != null && targetInstrument.MasterInstrument != null)
                tickSize = targetInstrument.MasterInstrument.TickSize;

            var pending = new PendingCopy
            {
                RelationshipId = rel.Id,
                LeaderAccountName = rel.LeaderAccountName,
                FollowerAccountName = rel.FollowerAccountName,
                LeaderExecTime = leaderExec.Time,
                SubmittedUtc = DateTime.UtcNow,
                LeaderFillPrice = leaderExec.Price,
                FollowerTickSize = tickSize,
                PriceComparable = ArePricesComparable(
                    RootOf(leaderExec.Instrument != null ? leaderExec.Instrument.FullName : null),
                    RootOf(targetInstrument != null ? targetInstrument.FullName : null)),
                FollowerIsBuy = followerAction == OrderAction.Buy || followerAction == OrderAction.BuyToCover,
                IsEntry = !isExit
            };

            lock (_lock)
            {
                if (!_pendingCopies.ContainsKey(followerOrder)) _pendingCopyQueue.Enqueue(followerOrder);
                _pendingCopies[followerOrder] = pending;
                while (_pendingCopyQueue.Count > MaxPendingCopies)
                {
                    Order oldest = _pendingCopyQueue.Dequeue();
                    _pendingCopies.Remove(oldest);
                }
            }
        }

        /// <summary>
        /// Called when an execution lands on an account that is a follower somewhere. If it
        /// matches a copy this engine submitted, records how long it took and how far it filled
        /// from the leader, and quarantines the relationship if an ENTRY slipped past
        /// `MaxSlippageTicks`.
        /// </summary>
        private Dictionary<string, int> _latencySampleCounts = new Dictionary<string, int>();

        private void ObserveFollowerFill(Execution exec)
        {
            if (exec == null || exec.Order == null)
            {
                // `exec` itself may be the null one, hence the guarded read.
                CopierLog(exec != null && exec.Account != null ? exec.Account.Name : null,
                    "FILL_ORDER_MISSING", "Execution or execution.Order was null; cannot observe follower fill.");
                return;
            }

            PendingCopy pending = null;
            CopierRelationship rel = null;
            bool pendingFound = false;
            lock (_lock)
            {
                PruneMetricCountsLocked();

                // Matched on the Order object, never on OrderId -- see OrderReferenceComparer.
                pendingFound = _pendingCopies.TryGetValue(exec.Order, out pending);
                if (pendingFound)
                    _pendingCopies.Remove(exec.Order);

                // Resolve the canonical stored relationship. A group-derived relationship is a
                // fresh object from ToRelationships(), so writing the metric onto the instance
                // OnExecution was handed would update a copy that is discarded.
                if (pendingFound)
                {
                    rel = _relationships.FirstOrDefault(r => r.Id == pending.RelationshipId)
                          ?? _relationships.FirstOrDefault(r =>
                                r.LeaderAccountName.Equals(pending.LeaderAccountName, StringComparison.OrdinalIgnoreCase) &&
                                r.FollowerAccountName.Equals(pending.FollowerAccountName, StringComparison.OrdinalIgnoreCase));
                }
            }

            if (!pendingFound)
            {
                CopierLog(exec.Account != null ? exec.Account.Name : null, "FILL_NOT_MEASURED",
                    string.Format("Pending-copy lookup missed for order '{0}' (OrderId {1}). OrderId is display-only and must never be used as the map key.",
                        exec.Order.Name, exec.Order.OrderId));
                return;
            }

            if (rel == null)
            {
                CopierLog(pending.FollowerAccountName, "FILL_RELATIONSHIP_MISSING",
                    string.Format("Could not resolve canonical relationship for pending copy on follower account '{0}' (relationship id {1}).",
                        pending.FollowerAccountName, pending.RelationshipId));
                return;
            }

            // Latency. Both timestamps come from NT8 executions, so they are subtracted raw --
            // exec.Time's DateTimeKind is not dependable and converting one side only would
            // inject the UTC offset as latency. When the leader timestamp is absent (the field
            // is optional and some feeds leave it default) fall back to wall-clock since submit.
            bool usedRawSubtraction = pending.LeaderExecTime != default(DateTime) && exec.Time != default(DateTime);
            double latencyMs;
            if (usedRawSubtraction)
                latencyMs = (exec.Time - pending.LeaderExecTime).TotalMilliseconds;
            else
                latencyMs = (DateTime.UtcNow - pending.SubmittedUtc).TotalMilliseconds;

            // A negative or absurd figure means the clocks disagree, not that the copy was fast.
            // Recording it would make the UI lie in a new direction.
            bool latencyAccepted = latencyMs >= 0 && latencyMs < 600000;
            if (latencyAccepted)
            {
                lock (_lock)
                {
                    rel.LatencyMs = latencyMs;
                    int n;
                    _latencySampleCounts.TryGetValue(rel.Id, out n);
                    n++;
                    _latencySampleCounts[rel.Id] = n;
                }
            }
            else if (latencyMs < 0 || latencyMs >= 600000)
            {
                CopierLog(rel.FollowerAccountName, "LATENCY_REJECTED",
                    string.Format("Latency {0:F1} ms rejected by sanity bound. UsedRawSubtraction={1}, LeaderExecTime={2:O}, FollowerExecTime={3:O}, SubmittedUtc={4:O}.",
                        latencyMs, usedRawSubtraction, pending.LeaderExecTime, exec.Time, pending.SubmittedUtc));
            }

            if (!pending.PriceComparable || pending.FollowerTickSize <= 0
                || pending.LeaderFillPrice <= 0 || exec.Price <= 0)
            {
                string failing = string.Empty;
                if (!pending.PriceComparable)
                    failing = "PriceComparable=false";
                if (pending.FollowerTickSize <= 0)
                    failing = failing.Length > 0 ? failing + ", FollowerTickSize<=0" : "FollowerTickSize<=0";
                if (pending.LeaderFillPrice <= 0)
                    failing = failing.Length > 0 ? failing + ", LeaderFillPrice<=0" : "LeaderFillPrice<=0";
                if (exec.Price <= 0)
                    failing = failing.Length > 0 ? failing + ", FollowerFillPrice<=0" : "FollowerFillPrice<=0";

                CopierLog(rel.FollowerAccountName, "SLIPPAGE_NOT_COMPARABLE",
                    string.Format("Slippage skipped for relationship {0} on follower '{1}' because prices are not comparable. Failing conditions: {2}. Values: PriceComparable={3}, FollowerTickSize={4}, LeaderFillPrice={5}, FollowerFillPrice={6}.",
                        rel.Id, pending.FollowerAccountName, failing, pending.PriceComparable, pending.FollowerTickSize, pending.LeaderFillPrice, exec.Price));
                return;
            }

            double rawTicks = (exec.Price - pending.LeaderFillPrice) / pending.FollowerTickSize;
            // Positive always means WORSE for the follower: a buy filled above the leader, or a
            // sell filled below it. Without this the sign is meaningless and a threshold on it
            // would fire on favourable fills.
            double ticks = pending.FollowerIsBuy ? rawTicks : -rawTicks;

            lock (_lock)
            {
                int n;
                _slippageSampleCounts.TryGetValue(rel.Id, out n);
                n++;
                _slippageSampleCounts[rel.Id] = n;
                rel.AvgSlippageTicks = rel.AvgSlippageTicks + (ticks - rel.AvgSlippageTicks) / n;
            }

            // Report `latencyMs`, the figure this fill actually produced -- NOT `rel.LatencyMs`,
            // which is the stored reading and is stale (or 0 on a first fill) precisely when the
            // measurement was rejected. Printing the stored value here would put a number in the
            // log that nothing computed for this fill, in the line that claims the fill was
            // measured: P1-22's own defect, reproduced inside P1-22's instrumentation. When the
            // bound rejected the reading, this line and LATENCY_REJECTED now agree on the figure.
            string latencyNote = latencyAccepted ? string.Empty : " (REJECTED by sanity bound, not recorded)";
            CopierLog(rel.FollowerAccountName, "FILL_MEASURED",
                string.Format("Fill measured for relationship {0}: latency={1:0.##} ms{2}, slippage={3:0.##} ticks.",
                    rel.Id, latencyMs, latencyNote, ticks));

            if (rel.MaxSlippageTicks <= 0 || ticks <= rel.MaxSlippageTicks) return;

            // Quarantine is ENTRY-ONLY, and quarantined relationships still copy exits
            // (see OnExecution). IsQuarantined otherwise blocks every copy including the one
            // that closes the follower out, which would strand it in a position the leader has
            // already left -- the P0-5 failure, reached by a different route. Same asymmetry as
            // P0-6's exit clamp and P1-23's fail-closed sizing modes.
            if (pending.IsEntry)
            {
                rel.IsQuarantined = true;
                rel.QuarantineReason = string.Format(
                    "Entry slipped {0:F1} ticks against the follower vs the leader fill (limit {1:F1}). Exits are still copied.",
                    ticks, rel.MaxSlippageTicks);
                // P1-71: this BLOCKS every future entry on the relationship and went to the Output
                // tab only. A state change that silences the copier belongs in the audit log --
                // otherwise "the copier stopped copying" has no recorded cause.
                CopierLog(rel.FollowerAccountName, "SLIPPAGE_QUARANTINE",
                    $"{rel.LeaderAccountName} -> {rel.FollowerAccountName} entry slipped {ticks:F1} "
                    + $"ticks (limit {rel.MaxSlippageTicks:F1}). NEW ENTRIES ARE NOW BLOCKED on this "
                    + "relationship; exits are still copied. Clear IsQuarantined to resume.");
            }
            else
            {
                CopierLog(rel.FollowerAccountName, "SLIPPAGE_ON_EXIT",
                    $"{rel.LeaderAccountName} -> {rel.FollowerAccountName} exit slipped {ticks:F1} "
                    + $"ticks (limit {rel.MaxSlippageTicks:F1}). Deliberately NOT quarantining: that "
                    + "would strand the follower in a position the leader has left.");
            }
        }

        private void PruneMetricCountsLocked()
        {
            var validIds = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var r in _relationships)
            {
                if (r == null)
                    continue;
                validIds.Add(r.Id);
            }

            foreach (var g in _groups)
            {
                if (g == null || g.FollowerAccounts == null)
                    continue;
                foreach (var f in g.FollowerAccounts)
                {
                    if (string.IsNullOrWhiteSpace(f))
                        continue;
                    validIds.Add(string.Format("{0}_{1}", g.Id, f.Trim()));
                }
            }

            var latencyKeys = new List<string>(_latencySampleCounts.Keys);
            foreach (var k in latencyKeys)
            {
                if (!validIds.Contains(k))
                    _latencySampleCounts.Remove(k);
            }

            var slippageKeys = new List<string>(_slippageSampleCounts.Keys);
            foreach (var k in slippageKeys)
            {
                if (!validIds.Contains(k))
                    _slippageSampleCounts.Remove(k);
            }
        }

        /// <summary>
        /// P0-9: a fill landed on a follower account. Re-reads the follower's real position and
        /// either anchors the bracket to it (and syncs the stop) or, if the position is now flat,
        /// releases the bracket so no orphan stop is left working.
        ///
        /// The position is re-read from the account rather than accumulated from executions:
        /// the fill may be our copy, the mirrored stop firing, or something the operator did by
        /// hand, and only the broker knows the resulting net.
        /// </summary>
        private void UpdateFollowerBracketOnFill(Execution exec)
        {
            if (exec == null || exec.Account == null || exec.Instrument == null) return;

            // P0-49: a flat read on the EXECUTION path is ambiguous, and which way it resolves is
            // the difference between a released bracket and a naked follower:
            //
            //   - exit fill        -> genuinely flat, release.
            //   - entry fill       -> NT8 simply has not raised PositionUpdate yet. Releasing here
            //                         throws away the bracket the leader's stop offset is waiting
            //                         on, and nothing ever rebuilds it.
            //
            // The anchor tells them apart. If this bracket has never held a position
            // (FollowerEntryPrice is NaN) there is nothing to exit FROM, so a flat read means the
            // position event is still in flight -- leave it alone and let OnAccountPositionUpdate
            // do the work. Once an anchor exists, flat means flat.
            bool anchored;
            lock (_lock)
            {
                FollowerBracket existing;
                anchored = _followerBrackets.TryGetValue(
                               BracketKey(exec.Account.Name, exec.Instrument.FullName), out existing)
                           && existing != null
                           && !double.IsNaN(existing.FollowerEntryPrice);
            }

            UpdateFollowerBracketFromPosition(exec.Account, exec.Instrument, releaseWhenFlat: anchored);
        }

        /// <summary>
        /// A follower account's position changed. This is the authoritative anchor source for the
        /// mirrored stop (P0-49).
        /// </summary>
        private void OnAccountPositionUpdate(object sender, PositionEventArgs e)
        {
            if (e == null || e.Position == null || e.Position.Instrument == null) return;
            Account acct = sender as Account;
            if (acct == null) return;

            bool isFollower;
            lock (_lock)
            {
                isFollower =
                    _relationships.Any(r => r.IsEnabled
                        && r.FollowerAccountName.Equals(acct.Name, StringComparison.OrdinalIgnoreCase))
                    || _groups.Any(g => g.IsEnabled && g.FollowerAccounts != null
                        && g.FollowerAccounts.Any(f => f.Equals(acct.Name, StringComparison.OrdinalIgnoreCase)));
            }

            // P0-55: a LEADER's position update used to be discarded here, and it is the last
            // event that will ever mention a stop accepted before the position existed. An
            // account can be both a leader and a follower, so these are two ifs, not a branch.
            if (GetActiveRelationshipsForLeader(acct.Name).Count > 0)
                ReevaluateLeaderStops(acct, e.Position.Instrument);

            if (!isFollower) return;

            UpdateFollowerBracketFromPosition(acct, e.Position.Instrument, releaseWhenFlat: true);
        }

        /// <summary>
        /// Re-derives the bracket's anchor from the follower's live position and syncs the stop.
        ///
        /// P0-49. This used to run ONLY from the follower's ExecutionUpdate, and it re-read
        /// `Positions` to find the anchor. **NT8 raises ExecutionUpdate BEFORE PositionUpdate**, so
        /// on the entry fill the position did not exist yet: the method took the flat branch,
        /// released the bracket, and returned. The anchor was never set, and nothing re-triggered
        /// it -- an ATM stop sits at `Accepted` and raises no further OrderUpdate, so
        /// `OnLeaderOrderUpdate` never fired again either. **The follower stayed naked for the
        /// entire trade**, and the stop finally appeared minutes later when the position closed
        /// and the events happened to line up. Observed live on 2026-08-07, MNQ SEP26: entry
        /// 15:43:21, `MISSING_STOP_FLATTEN` at 15:43:24, `COPIER_STOP` at 15:45:22.
        ///
        /// `releaseWhenFlat` is the crux. From a PositionUpdate, flat means **flat** and the
        /// bracket must be released. From an ExecutionUpdate, flat is ambiguous -- it may simply
        /// mean the position event has not landed yet -- so the execution path must NOT release,
        /// and instead waits for the position event that is always coming.
        /// </summary>
        private void UpdateFollowerBracketFromPosition(Account followerAcc, Instrument instrument, bool releaseWhenFlat)
        {
            if (followerAcc == null || instrument == null) return;
            string instrumentName = instrument.FullName;

            Position pos = followerAcc.Positions.FirstOrDefault(p =>
                p.Instrument != null &&
                p.Instrument.FullName.Equals(instrumentName, StringComparison.OrdinalIgnoreCase));

            if (pos == null || pos.MarketPosition == MarketPosition.Flat || pos.Quantity <= 0)
            {
                if (releaseWhenFlat) ReleaseFollowerBracket(followerAcc, instrumentName);
                return;
            }

            string key = BracketKey(followerAcc.Name, instrumentName);
            FollowerBracket bracket;
            lock (_lock)
            {
                if (!_followerBrackets.TryGetValue(key, out bracket))
                {
                    bracket = new FollowerBracket
                    {
                        FollowerAccountName = followerAcc.Name,
                        InstrumentFullName = instrumentName
                    };
                    _followerBrackets[key] = bracket;
                }
                bracket.FollowerEntryPrice = pos.AveragePrice;
                bracket.FollowerSide = pos.MarketPosition;
                bracket.FollowerQuantity = pos.Quantity;
            }

            SyncFollowerBracket(followerAcc, instrument, bracket);
        }

        // OnExecution is deliberately NOT behind `#if !TESTING`. It is the trade-copy
        // path - the riskiest code in this file - and excluding it left it with zero
        // test coverage. It compiles against the NinjaTrader stubs in
        // RiskGuardAddOnTests.cs (Account.All/CreateOrder/Submit, Instrument.GetInstrument,
        // NinjaTrader.Code.Output).
        /// <summary>
        /// Dual sink. Output.Process alone reaches the NT8 Output tab and nothing a human or a
        /// tool can read afterwards, which is why the 2026-08-09 exit-mirror failure could not be
        /// explained from the logs. Everything routed through here also lands in RiskGuard's
        /// structured log, and so in the bridge's event stream.
        /// </summary>
        /// <summary>
        /// Test seam, same shape and same justification as the stub broker's BrokerCallObserver.
        /// Several behaviours in this file are observable ONLY as a log line, and P1-22's
        /// measurement is the extreme case: the entire defect there is that a silent early return
        /// is indistinguishable from a clean copy. A test cannot assert against an NT8 Output tab
        /// or a background log-writer thread, so it asserts here.
        /// </summary>
        internal static Action<string, string, string> CopierLogObserver;

        private static void CopierLog(string account, string eventType, string message)
        {
            NinjaTrader.Code.Output.Process($"[CopierEngine] {eventType}: {message}", PrintTo.OutputTab1);
            RiskGuardAddOn.LogFromComponent(account, "COPIER_" + eventType, message);
            var obs = CopierLogObserver;
            if (obs != null) obs(account, eventType, message);
        }

        public void OnExecution(Execution exec)
        {
            // Every early return below used to be SILENT. On 2026-08-09 a leader exit did not
            // mirror to its follower and no path could be ruled in or out, because a dropped
            // execution left no trace at all. Each exit now says which one it was.
            if (exec == null || exec.Account == null || exec.Quantity <= 0)
            {
                CopierLog(exec != null && exec.Account != null ? exec.Account.Name : "UNKNOWN",
                    "EXEC_IGNORED", "execution was null, had no account, or had quantity <= 0.");
                return;
            }

            // Skip copy if order is null (cannot determine order direction safely)
            if (exec.Order == null)
            {
                CopierLog(exec.Account.Name, "EXEC_IGNORED",
                    $"execution {exec.ExecutionId} has no Order, so its direction cannot be determined.");
                return;
            }

            string acctName = exec.Account.Name;

            CopierLog(acctName, "EXEC_SEEN",
                $"{exec.Instrument?.FullName} {exec.Order.OrderAction} {exec.Quantity}@{exec.Price} "
                + $"order='{exec.Order.Name}' execId={exec.ExecutionId}");

            // Recursion Guard 1: Followers can NEVER act as Leaders (prevents copy feedback loops)
            bool isFollowerAccount;
            lock (_lock)
            {
                bool isFollowerInDirect = _relationships.Any(r => r.IsEnabled && r.FollowerAccountName.Equals(acctName, StringComparison.OrdinalIgnoreCase));
                bool isFollowerInGroups = _groups.Any(g => g.IsEnabled && g.FollowerAccounts != null && g.FollowerAccounts.Any(f => f.Equals(acctName, StringComparison.OrdinalIgnoreCase)));
                isFollowerAccount = isFollowerInDirect || isFollowerInGroups;
            }

            if (isFollowerAccount)
            {
                // P1-22: a copy coming back as a follower fill is the ONLY observation the copier
                // ever gets of what its own order actually cost. Measure it before the recursion
                // guard drops the execution.
                ObserveFollowerFill(exec);
                // P0-9: the same event is where the bracket learns its anchor, and where a
                // follower going flat releases it.
                UpdateFollowerBracketOnFill(exec);
                CopierLog(acctName, "EXEC_IS_FOLLOWER",
                    "account is a follower in at least one relationship, so it can never act as a "
                    + "leader; fill observed and bracket updated, no copy attempted.");
                return;
            }

            bool copierOriginated;
            lock (_lock)
            {
                // Recursion Guard 2: Ignore executions originated by copier placement
                copierOriginated =
                    (!string.IsNullOrEmpty(exec.Order.Name) && exec.Order.Name.Contains("COPIER"))
                    || (exec.Name != null && exec.Name.Contains("COPIER"));
            }
            if (copierOriginated)
            {
                CopierLog(acctName, "EXEC_SELF_ORIGINATED",
                    $"order '{exec.Order.Name}' / exec '{exec.Name}' contains COPIER, so this is our "
                    + "own placement coming back; dropped to prevent a feedback loop.");
                return;
            }

            // Redelivery Guard 3: Deduplicate exact duplicate socket redelivery of same execution ID (bounded FIFO queue)
            if (DeduplicateExecutionId(exec.ExecutionId))
            {
                CopierLog(acctName, "EXEC_DUPLICATE",
                    $"execution {exec.ExecutionId} was already processed; socket redelivery dropped.");
                return;
            }

            // P1-22: a quarantined relationship must still be able to CLOSE the follower. Blocking
            // its exits strands it in a position the leader has already left -- the P0-5 failure
            // reached by another route. Entries stay blocked.
            OrderAction leadAction = exec.Order.OrderAction;
            bool leaderIsExiting = leadAction == OrderAction.Sell || leadAction == OrderAction.BuyToCover;

            List<CopierRelationship> activeRels =
                GetActiveRelationshipsForLeader(acctName, includeQuarantined: leaderIsExiting);

            if (activeRels.Count == 0)
            {
                // The single most likely explanation for a leader fill that mirrors nothing, and
                // until now the least visible: it is indistinguishable from the copier never
                // having seen the execution at all.
                CopierLog(acctName, "NO_ACTIVE_RELATIONSHIPS",
                    $"no enabled relationship has '{acctName}' as leader "
                    + $"(isExit={leaderIsExiting}, quarantined included={leaderIsExiting}); nothing to copy to.");
                return;
            }

            CopierLog(acctName, "COPY_BEGIN",
                $"{activeRels.Count} active relationship(s), isExit={leaderIsExiting}: "
                + string.Join(", ", activeRels.Select(r => r.FollowerAccountName)));

            foreach (var rel in activeRels)
            {
                if (rel.IsQuarantined)
                {
                    // NOT a terminal outcome -- the exit is copied anyway, so this must not match
                    // the COPY_SUBMITTED/SKIPPED_/BLOCKED_/FAILED_ convention the P1-71 invariant
                    // counts, or a genuine drop could hide behind it.
                    CopierLog(rel.FollowerAccountName, "QUARANTINE_EXIT_ALLOWED",
                        $"{rel.LeaderAccountName} -> {rel.FollowerAccountName} is quarantined "
                        + $"({rel.QuarantineReason}), but this is an exit, so it is copied anyway.");
                }

                Account followerAcc = Account.All.FirstOrDefault(a => a.Name.Equals(rel.FollowerAccountName, StringComparison.OrdinalIgnoreCase));
                if (followerAcc == null)
                {
                    // P1-71: this was `if (followerAcc == null) continue;` -- no log of any kind. A
                    // relationship naming an account that no longer exists in NT8 dropped every copy
                    // in total silence, and the config is the only place the name appears.
                    CopierLog(rel.FollowerAccountName, "COPY_SKIPPED_ACCOUNT_MISSING",
                        $"relationship {rel.Id} names follower account '{rel.FollowerAccountName}', "
                        + "which is not in Account.All -- renamed, removed, or not connected in this "
                        + "NT8 instance. Nothing was copied. Fix the relationship or the account: "
                        + "this will drop EVERY copy silently until one of them changes.");
                    continue;
                }

                bool isSimFollower = IsSimulationAccount(followerAcc);

                // SAFETY GATE: Disarmed copier MUST NOT place orders on non-Sim (live) accounts
                if (!rel.ArmedForLive && !isSimFollower)
                {
                    CopierLog(followerAcc.Name, "COPY_BLOCKED_NOT_ARMED",
                        $"follower '{followerAcc.Name}' is LIVE (provider {followerAcc.Provider}) and "
                        + "the relationship is not ArmedForLive; refusing to place the copy.");
                    continue;
                }

                // Determine target Instrument (AutoSymbolConversion e.g. NQ -> MNQ)
                Instrument targetInstrument = exec.Instrument;
                if (rel.AutoSymbolConversion && exec.Instrument != null)
                {
                    string translatedSymbolName = TranslateSymbol(exec.Instrument.FullName, rel);
                    if (!string.Equals(translatedSymbolName, exec.Instrument.FullName, StringComparison.OrdinalIgnoreCase))
                    {
                        var resolvedInst = Instrument.GetInstrument(translatedSymbolName);
                        if (resolvedInst != null)
                        {
                            targetInstrument = resolvedInst;
                        }
                        else
                        {
                            // P1-71: silent at baseline, and it does NOT skip the copy -- it falls
                            // through and trades the LEADER's instrument on the follower. That is a
                            // wrong-instrument copy presented as a normal one, so it is logged loudly
                            // and deliberately kept out of the terminal-outcome convention.
                            CopierLog(followerAcc.Name, "SYMBOL_TRANSLATION_UNRESOLVED",
                                $"AutoSymbolConversion mapped '{exec.Instrument.FullName}' to "
                                + $"'{translatedSymbolName}', which does not resolve to an instrument. "
                                + $"FALLING BACK to the leader's own instrument "
                                + $"'{exec.Instrument.FullName}' -- check CustomSymbolMappings.");
                        }
                    }
                }

                // RiskGuard tradeability and protection checks (outside _lock to avoid lock-ordering with RiskGuard)
                var riskGuard = RiskGuardAddOn.Instance;
                if (riskGuard != null)
                {
                    if (!riskGuard.CanTrade(acctName, exec.Instrument.FullName, "TradeCopier"))
                    {
                        CopierLog(followerAcc.Name, "COPY_BLOCKED_LEADER_LOCKED",
                            $"LEADER account '{acctName}' is locked for {exec.Instrument.FullName}, so "
                            + $"the copy to '{followerAcc.Name}' was not placed. Note this is the "
                            + "leader's lockout, not the follower's.");
                        continue;
                    }

                    if (!riskGuard.CanTrade(followerAcc.Name, targetInstrument.FullName, "TradeCopier"))
                    {
                        CopierLog(followerAcc.Name, "COPY_BLOCKED_FOLLOWER_LOCKED",
                            $"follower account '{followerAcc.Name}' is locked for "
                            + $"{targetInstrument.FullName}; copy not placed.");
                        continue;
                    }

                    if (!isSimFollower && !riskGuard.IsGuardProtecting(followerAcc.Name))
                    {
                        CopierLog(followerAcc.Name, "COPY_BLOCKED_NO_GUARD",
                            $"follower '{followerAcc.Name}' is LIVE but RiskGuard is not protecting it; "
                            + $"skipping copy for {targetInstrument.FullName}.");
                        continue;
                    }
                }
                else
                {
                    if (!isSimFollower)
                    {
                        CopierLog(followerAcc.Name, "COPY_BLOCKED_NO_GUARD",
                            $"RiskGuard is UNAVAILABLE (no instance) and follower '{followerAcc.Name}' "
                            + $"is LIVE; skipping copy for {targetInstrument.FullName}.");
                        continue;
                    }
                }

                OrderAction leadOrderAction = leadAction;
                bool isExit = leaderIsExiting;   // computed once above; the quarantine gate uses it too

                int currentFollowerPos = 0;
                var followerPositionObj = followerAcc.Positions.FirstOrDefault(p => p.Instrument.FullName.Equals(targetInstrument.FullName, StringComparison.OrdinalIgnoreCase));
                if (followerPositionObj != null)
                {
                    currentFollowerPos = followerPositionObj.Quantity;
                }

                bool isClamped;
                int targetQty = CalculateFollowerQuantity(rel, exec.Quantity, exec.Instrument.FullName, currentFollowerPos, isExit, out isClamped);
                if (targetQty <= 0)
                {
                    if (isExit && currentFollowerPos == 0)
                    {
                        CopierLog(followerAcc.Name, "COPY_SKIPPED_NO_POSITION_TO_EXIT",
                            $"follower '{followerAcc.Name}' holds no position in "
                            + $"{targetInstrument.FullName}, so the leader's exit has nothing to close. "
                            + "This is usually correct -- but if the follower SHOULD have been in, the "
                            + "entry copy is what failed, and its own outcome event says why.");
                    }
                    else if (isClamped)
                    {
                        CopierLog(followerAcc.Name, "COPY_SKIPPED_CLAMPED_TO_ZERO",
                            $"follower '{followerAcc.Name}' is already at MaxPositionSize "
                            + $"{rel.MaxPositionSize} (currently {currentFollowerPos}); no room for the "
                            + "copy, so nothing was placed.");
                    }
                    else
                    {
                        CopierLog(followerAcc.Name, "COPY_SKIPPED_SUB_MINIMUM",
                            $"scaled quantity for {targetInstrument.FullName} on '{followerAcc.Name}' "
                            + $"came out below 1 contract from leader qty {exec.Quantity} "
                            + $"(ratio {rel.QuantityRatio}, sizing {rel.SizingMode}); nothing placed.");
                    }
                    continue;
                }

                if (isClamped)
                {
                    // NOT terminal: the copy proceeds, at a REDUCED size. Deliberately outside the
                    // P1-71 outcome convention -- a size change is not an outcome, and counting it
                    // as one would let a later drop hide behind it.
                    CopierLog(followerAcc.Name, "COPY_QTY_CLAMPED",
                        $"copy quantity for {targetInstrument.FullName} on '{followerAcc.Name}' clamped "
                        + $"to {targetQty} by MaxPositionSize {rel.MaxPositionSize} "
                        + $"(current position {currentFollowerPos}). The copy IS being placed, smaller "
                        + "than the leader's -- so the follower is now deliberately out of ratio.");
                }

                OrderAction followerAction = leadOrderAction;

                // Handle Inverse / Fade Trading (QuantityRatio < 0)
                if (rel.QuantityRatio < 0)
                {
                    if (leadOrderAction == OrderAction.Buy) followerAction = OrderAction.Sell;
                    else if (leadOrderAction == OrderAction.Sell) followerAction = OrderAction.BuyToCover;
                    else if (leadOrderAction == OrderAction.SellShort) followerAction = OrderAction.Buy;
                    else if (leadOrderAction == OrderAction.BuyToCover) followerAction = OrderAction.SellShort;
                }
                else if (isExit)
                {
                    // Align exit order action with follower's current position direction if non-zero
                    if (currentFollowerPos < 0) followerAction = OrderAction.BuyToCover;
                    else if (currentFollowerPos > 0) followerAction = OrderAction.Sell;
                }

                TimeInForce tif = (exec.Order.TimeInForce != TimeInForce.Gtc) ? exec.Order.TimeInForce : TimeInForce.Day;

                try
                {
                    Order followerOrder = followerAcc.CreateOrder(
                        targetInstrument,
                        followerAction,
                        OrderType.Market,
                        tif,
                        targetQty,
                        0,
                        0,
                        "",
                        "COPIER_FOLLOW",
                        null
                    );

                    // Submit follower order
                    if (followerOrder != null)
                    {
                        followerAcc.Submit(new[] { followerOrder });

                        // P1-22: remember what the leader paid so the follower's fill can be
                        // measured against it. Recorded only after a successful Submit -- an
                        // order that never reached the broker has no fill coming, and its entry
                        // would sit in the pending map until evicted.
                        RecordPendingCopy(followerOrder, rel, exec, targetInstrument, followerAction, isExit);

                        // P1-71: the terminal SUCCESS outcome. Without it, "exactly one outcome per
                        // relationship" could be satisfied by logging skips only, and the invariant
                        // would prove nothing.
                        CopierLog(followerAcc.Name, "COPY_SUBMITTED",
                            $"{targetInstrument.FullName} {followerAction} {targetQty} submitted to "
                            + $"'{followerAcc.Name}' mirroring leader '{acctName}' "
                            + $"{leadOrderAction} {exec.Quantity}@{exec.Price} (isExit={isExit}).");
                    }
                    else
                    {
                        // P1-71: CreateOrder returning null was completely silent, and it is the one
                        // failure that looks identical to "the copier never saw the execution".
                        CopierLog(followerAcc.Name, "COPY_FAILED_CREATE_ORDER_NULL",
                            $"CreateOrder returned null for {targetInstrument.FullName} "
                            + $"{followerAction} {targetQty} on '{followerAcc.Name}'; nothing was "
                            + "submitted. Usually the instrument is not tradeable on that account.");
                    }
                }
                catch (Exception ex)
                {
                    CopierLog(followerAcc.Name, "COPY_FAILED_SUBMIT",
                        $"placing {targetInstrument.FullName} {followerAction} {targetQty} on "
                        + $"'{followerAcc.Name}' threw {ex.GetType().Name}: {ex.Message}");
                }
            }
        }

    }
}
