// P2-136, the "survive it" half. The registry of managed ATM brackets, written where a NinjaScript
// hot-swap cannot reach it, and the decision about which of those records may be picked back up.
//
// WHY THIS EXISTS. `DynamicAtmManager`'s registry lives behind
// `private static readonly Lazy<DynamicAtmManager> _instance` -- which reads as "survives anything"
// and does not survive a successful compile. NT8 hot-swaps `bin/Custom` into a NEW ASSEMBLY, the new
// assembly gets a fresh `Lazy`, and `_activeBrackets` starts EMPTY while the position and both
// broker-side legs are untouched. Measured on a box with 377 minutes of uptime and no restart:
// **18** `ARMED_ON_START` bursts in 2.5 hours, every one a recompile; bracket `1a48f3cf` registered
// at 23:16 against an open 1-lot MNQ position was gone from the registry by 23:17:3x with the
// position still long 1. The stop and target still RESTED AT THE BROKER, so every surface an
// operator checks reported the trade as protected -- protected at its original price, and it would
// never move again. [[a-successful-compile-wipes-static-state]].
//
// ⚠️ AND SOMEBODY ELSE'S DEPLOY DOES THIS TO YOU. The 23:17:56 compile came from another process
// deploying unrelated `range_probability` NinjaScript in a different repo. Deploying an indicator
// that has nothing to do with the guard discards the guard's ATM state.
//
// ⚠️ THE IDENTITY CHECK IS THE WHOLE SAFETY ARGUMENT, AND IT IS NOT "IS THERE A POSITION".
// A record says "account SimAtm, symbol MNQ". A file two days old plus an unrelated manual MNQ trade
// on that account satisfies that description exactly -- and restoring on it would attach this
// monitor's trailing logic to a position it did not create and start MOVING THE OPERATOR'S OWN STOP.
// So a record is only picked up when the LIVE ORDER NAMED `Stop_<bracketId>` is still working at the
// broker. That name is bracket-unique, this addon chose it, and per `P1-133` it is the one identity
// the broker does not replace. A value we own cannot vary by provider.
//
// ⚠️ NOTHING HERE TRUSTS A PRICE FROM THE FILE. `CurrentStopPrice` on a restored bracket is read off
// the live order that was just found, and `RequestedStopPrice`/`OutstandingStopMoveKind` are reset to
// "nothing outstanding". `P0-67` is exactly this lesson one layer down: a polling monitor does not
// need settle events, it needs to stop believing its own writes -- and a price recorded before a
// compile is this monitor's last wish, not the broker's truth.
//
// ⚠️ "NOT RESTORABLE NOW" AND "NEVER RESTORABLE" ARE DIFFERENT, and conflating them is how P2-136's
// own first diagnosis went wrong. That reading blamed a transient `Account.All` miss during a
// connection cycle; it was the wrong cause for THAT measurement, but the transient is real -- an
// `ARMED_ON_START` burst is a connection cycle, and this class runs during one. So an absent or
// not-yet-populated account DEFERS the record and keeps it on disk, while a flat position DROPS it.
// The deferral is BOUNDED and its give-up is announced, because an unbounded defer is a record that
// never leaves and a silent give-up is [[a-recovery-budget-is-not-a-policy]].
//
// It names `Account`, `Order` and `Position` and nothing else from NT8, all of which the test build
// stubs, so every line here is EXECUTED by tests rather than scanned (`P2-27`). `tools/sync_nt8.py`
// globs `addons/*.cs`, so it needs no registration to ship.
using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using NinjaTrader.Cbi;

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>
    /// What may be done with one persisted record. Every value below is a DIFFERENT FACT about the
    /// live world, and the reasons are not interchangeable: `Finished` is the ordinary case and is
    /// good news, `Unprotected` is a live position with no protective leg, and `Deferred` is "ask
    /// again" rather than any answer at all.
    /// </summary>
    public enum AtmRestoreVerdict
    {
        /// <summary>The named stop is live, the position agrees with the record: pick it back up.</summary>
        Restored,

        /// <summary>Flat, or no position in that symbol. The trade ended while nothing was watching.</summary>
        Finished,

        /// <summary>
        /// The position is OPEN and the leg named `Stop_&lt;bracketId&gt;` is not live at the broker.
        /// Deliberately NOT restored: a bracket with no stop to move would report as managed while
        /// managing nothing, which is the very shape `P2-136` exists to remove.
        /// [[dead-safety-machinery-gate]].
        /// </summary>
        Unprotected,

        /// <summary>
        /// The live position runs the other way from the record. The named stop may well be there,
        /// so this is not an identity failure -- it is a position that was reversed by hand while our
        /// leg rested. Every breakeven and trail computation downstream is signed by `IsLong`, so
        /// restoring would compute the wrong direction on a real position.
        /// </summary>
        Mismatched,

        /// <summary>Nothing could be READ about the account yet. Keep the record and ask again.</summary>
        Deferred,

        /// <summary>Deferred <see cref="MaxRestoreDeferrals"/> times without ever becoming readable.</summary>
        DeferralExhausted,

        /// <summary>The record itself is unusable -- no bracket id, account or symbol to check.</summary>
        Unreadable
    }

    public class AtmRestoreDecision
    {
        public ActiveBracket Bracket;
        public AtmRestoreVerdict Verdict;
        public string Reason;

        /// <summary>
        /// Whether the record stays on disk for another attempt. Derived from the verdict in one
        /// place rather than set by each branch, so a new verdict cannot forget to answer it.
        /// </summary>
        public bool KeepOnDisk
        {
            get { return Verdict == AtmRestoreVerdict.Deferred; }
        }
    }

    /// <summary>One persisted record: the bracket, plus how many times picking it up has been deferred.</summary>
    public class PersistedAtmBracket
    {
        public ActiveBracket Bracket { get; set; }

        /// <summary>
        /// Lives HERE and not on <see cref="ActiveBracket"/> deliberately. It is a fact about this
        /// file, not about the trade, and `ActiveBracket` is serialised into the bridge's public API
        /// payload -- a retry counter for a disk format has no business being advertised there.
        /// </summary>
        public int RestoreDeferrals { get; set; }
    }

    public class PersistedAtmBracketFile
    {
        public int SchemaVersion { get; set; }
        public DateTime SavedUtc { get; set; }
        public List<PersistedAtmBracket> Brackets { get; set; }
    }

    public static class AtmBracketPersistence
    {
        public const int SchemaVersion = 1;

        /// <summary>
        /// Bounded, and three rather than one because the condition this covers is a connection
        /// cycle, which spans more than one sweep. Unbounded would leave a record on disk forever;
        /// one attempt would drop a live bracket because `Account.All` had not filled in yet.
        /// </summary>
        public const int MaxRestoreDeferrals = 3;

        /// <summary>
        /// The decision for one record against the live world.
        ///
        /// ⚠️ THE ORDER OF THESE CHECKS IS THE ANSWER, not an implementation detail. With more than
        /// one condition true, the reported reason must be the one that BINDS -- the one that makes
        /// restoring impossible -- rather than whichever is noticed first.
        /// [[rank-refusal-reasons-by-what-binds]].
        /// </summary>
        public static AtmRestoreDecision Decide(PersistedAtmBracket record, IEnumerable<Account> accounts)
        {
            if (record == null || record.Bracket == null)
                return Unusable(null, "the record carries no bracket");

            ActiveBracket b = record.Bracket;

            if (string.IsNullOrWhiteSpace(b.BracketId))
                return Unusable(b, "the record carries no bracket id, so its protective leg cannot be named");
            if (string.IsNullOrWhiteSpace(b.AccountName))
                return Unusable(b, b.BracketId + ": the record names no account");
            if (string.IsNullOrWhiteSpace(b.Symbol))
                return Unusable(b, b.BracketId + ": the record names no symbol");

            Account account = null;
            if (accounts != null)
            {
                foreach (Account candidate in accounts)
                {
                    if (candidate != null && candidate.Name != null
                        && candidate.Name.Equals(b.AccountName, StringComparison.OrdinalIgnoreCase))
                    {
                        account = candidate;
                        break;
                    }
                }
            }

            if (account == null)
                return Defer(record, "account '" + b.AccountName + "' is not in Account.All yet");

            // ⚠️ An account that reports NO orders and NO positions has not necessarily gone idle --
            // during a connection cycle it is an account that has not synced. Both look identical
            // from here, so this defers rather than answering, and the bounded budget above is what
            // stops that being permanent. Reading it as idle would drop a live bracket.
            bool anyOrders = account.Orders != null && account.Orders.Count > 0;
            bool anyPositions = account.Positions != null && account.Positions.Count > 0;
            if (!anyOrders && !anyPositions)
                return Defer(record, "account '" + account.Name + "' reports no orders and no positions, so it has not synced yet");

            Position position = null;
            if (account.Positions != null)
            {
                foreach (Position candidate in account.Positions)
                {
                    if (candidate != null && candidate.Instrument != null
                        && candidate.Instrument.MasterInstrument != null
                        && candidate.Instrument.MasterInstrument.Name != null
                        && candidate.Instrument.MasterInstrument.Name.Equals(b.Symbol, StringComparison.OrdinalIgnoreCase))
                    {
                        position = candidate;
                        break;
                    }
                }
            }

            // ⚠️ `Position.Quantity` is ABSOLUTE on NT8 and never negative; the side is
            // `MarketPosition`. Reading the sign here would make every short look flat.
            // [[nt8-position-quantity-is-absolute]].
            if (position == null || Math.Abs(position.Quantity) == 0)
            {
                return new AtmRestoreDecision
                {
                    Bracket = b,
                    Verdict = AtmRestoreVerdict.Finished,
                    Reason = b.BracketId + ": " + b.Symbol + " is flat on '" + account.Name
                        + "', so the trade ended while the registry was empty and there is nothing to manage."
                };
            }

            bool positionIsLong = position.MarketPosition == MarketPosition.Long;
            if (positionIsLong != b.IsLong)
            {
                return new AtmRestoreDecision
                {
                    Bracket = b,
                    Verdict = AtmRestoreVerdict.Mismatched,
                    Reason = b.BracketId + ": the record is " + (b.IsLong ? "LONG" : "SHORT") + " and the live "
                        + b.Symbol + " position on '" + account.Name + "' is "
                        + (positionIsLong ? "LONG" : "SHORT")
                        + ", so every breakeven and trail price for it would be computed the wrong way. "
                        + "Not managed; the position keeps whatever protection it has."
                };
            }

            // THE IDENTITY CHECK. Not "is there a position" -- see the header. `FindLiveByName` uses
            // the guard's shared `OccupiesSlot` predicate rather than a hand-written state list,
            // because a resting stop is `Working` on one provider and `Accepted` on another and
            // `P1-130`/`P1-131` were both a local list disagreeing with its neighbour.
            Order liveStop = AtmOrderIdentity.FindLiveByName(account, AtmOrderIdentity.StopName(b.BracketId));
            if (liveStop == null)
            {
                return new AtmRestoreDecision
                {
                    Bracket = b,
                    Verdict = AtmRestoreVerdict.Unprotected,
                    Reason = b.BracketId + ": the " + b.Symbol + " position on '" + account.Name
                        + "' is still OPEN and no live order named '" + AtmOrderIdentity.StopName(b.BracketId)
                        + "' remains at the broker, so this position has no protective stop and is not "
                        + "being managed. It is NOT picked back up, because a bracket with no stop to "
                        + "move would report as managed while managing nothing."
                };
            }

            // The price comes from the ORDER, never from the file. See the header: a price written
            // before a compile is this monitor's last wish. P0-67 one layer down.
            b.CurrentStopPrice = liveStop.StopPrice;

            // Nothing is outstanding across a hot-swap: whatever was in flight either took or did
            // not, and the next sweep's ReconcileStopFromBroker is what finds out.
            b.RequestedStopPrice = double.NaN;
            b.OutstandingStopMoveKind = ActiveBracket.StopMoveKind.None;

            // ⚠️ THE BUDGET IS RESET, AND THE INVARIANT THAT MAKES THAT SAFE IS THE CALLER'S.
            // A new assembly against a possibly-new connection is a new episode, so a bracket that
            // had given up deserves to try again -- and `StopMoveAbandonAnnounced` is cleared with it
            // so the second failure is not swallowed as already-said. This is only safe because a
            // record is consumed ONCE: `RestoreInto` refuses a bracket id already in the registry.
            // Without that, a file re-read on every sweep would launder the retry budget every five
            // seconds and turn a bounded retry into an order flood.
            b.StopModifyAttempts = 0;
            b.StopMoveAbandonAnnounced = false;
            b.LastStopMoveFailureReason = null;

            return new AtmRestoreDecision
            {
                Bracket = b,
                Verdict = AtmRestoreVerdict.Restored,
                Reason = b.BracketId + ": picked back up after a NinjaScript recompile. The "
                    + b.Symbol + " position on '" + account.Name + "' is still open and its stop '"
                    + AtmOrderIdentity.StopName(b.BracketId) + "' is live at "
                    + liveStop.StopPrice.ToString("0.#####")
                    + ", read from the order rather than from the saved file. Breakeven and trailing resume."
            };
        }

        public static List<AtmRestoreDecision> DecideAll(PersistedAtmBracketFile file, IEnumerable<Account> accounts)
        {
            List<AtmRestoreDecision> decisions = new List<AtmRestoreDecision>();
            if (file == null || file.Brackets == null)
                return decisions;

            List<Account> snapshot = accounts == null ? new List<Account>() : accounts.ToList();
            foreach (PersistedAtmBracket record in file.Brackets)
                decisions.Add(Decide(record, snapshot));

            return decisions;
        }

        /// <summary>
        /// What goes back to disk after a restore pass: the deferred records with their budget spent
        /// by one, and NOTHING else. A record that was answered -- restored, finished, unprotected,
        /// mismatched, unusable -- is answered, and leaving it would make the same announcement every
        /// sweep for the life of the process.
        /// </summary>
        public static PersistedAtmBracketFile Remaining(IEnumerable<AtmRestoreDecision> decisions,
            IEnumerable<PersistedAtmBracket> originals)
        {
            PersistedAtmBracketFile file = new PersistedAtmBracketFile
            {
                SchemaVersion = SchemaVersion,
                SavedUtc = DateTime.UtcNow,
                Brackets = new List<PersistedAtmBracket>()
            };
            if (decisions == null || originals == null)
                return file;

            List<PersistedAtmBracket> pool = originals.ToList();
            foreach (AtmRestoreDecision decision in decisions)
            {
                if (!decision.KeepOnDisk) continue;

                PersistedAtmBracket record = pool.FirstOrDefault(r =>
                    r != null && r.Bracket != null && decision.Bracket != null
                    && string.Equals(r.Bracket.BracketId, decision.Bracket.BracketId, StringComparison.Ordinal));
                if (record == null) continue;

                record.RestoreDeferrals = record.RestoreDeferrals + 1;
                file.Brackets.Add(record);
            }

            return file;
        }

        public static string Serialise(IEnumerable<ActiveBracket> brackets)
        {
            PersistedAtmBracketFile file = new PersistedAtmBracketFile
            {
                SchemaVersion = SchemaVersion,
                SavedUtc = DateTime.UtcNow,
                Brackets = new List<PersistedAtmBracket>()
            };
            if (brackets != null)
            {
                foreach (ActiveBracket b in brackets)
                {
                    if (b == null) continue;
                    file.Brackets.Add(new PersistedAtmBracket { Bracket = b, RestoreDeferrals = 0 });
                }
            }
            return Serialise(file);
        }

        public static string Serialise(PersistedAtmBracketFile file)
        {
            // ⚠️ `RequestedStopPrice` defaults to `double.NaN`, and Json.NET's DEFAULT float handling
            // writes a bare `NaN`, which is not valid JSON and which any other reader of this file
            // will reject. It is pinned to a quoted string here and Json.NET reads that back to NaN.
            // The field is reset on restore anyway, so this is about the file staying parseable.
            return JsonConvert.SerializeObject(file, new JsonSerializerSettings
            {
                Formatting = Formatting.Indented,
                FloatFormatHandling = FloatFormatHandling.String
            });
        }

        /// <summary>
        /// Reads the file, or returns null if it cannot be read.
        ///
        /// ⚠️ NULL MEANS "COULD NOT READ", AND AN EMPTY FILE IS NOT THAT. A file listing zero
        /// brackets is a registry that was saved and was empty -- the ordinary state of a box with no
        /// ATM trade on -- and returning null for it would make a normal startup indistinguishable
        /// from corruption. [[an-inapplicable-state-is-not-unreadable]].
        /// </summary>
        public static PersistedAtmBracketFile Deserialise(string json)
        {
            if (string.IsNullOrWhiteSpace(json)) return null;
            try
            {
                PersistedAtmBracketFile file = JsonConvert.DeserializeObject<PersistedAtmBracketFile>(json);
                if (file == null) return null;
                if (file.Brackets == null) file.Brackets = new List<PersistedAtmBracket>();
                return file;
            }
            catch
            {
                return null;
            }
        }

        private static AtmRestoreDecision Unusable(ActiveBracket b, string why)
        {
            return new AtmRestoreDecision
            {
                Bracket = b,
                Verdict = AtmRestoreVerdict.Unreadable,
                Reason = "a persisted ATM bracket record cannot be checked and is discarded: " + why + "."
            };
        }

        private static AtmRestoreDecision Defer(PersistedAtmBracket record, string why)
        {
            ActiveBracket b = record.Bracket;
            if (record.RestoreDeferrals >= MaxRestoreDeferrals)
            {
                return new AtmRestoreDecision
                {
                    Bracket = b,
                    Verdict = AtmRestoreVerdict.DeferralExhausted,
                    Reason = b.BracketId + ": giving up on picking this bracket back up after "
                        + record.RestoreDeferrals + " attempts, the last of which found that " + why
                        + ". If its position is open it is no longer managed and its stop will not move again."
                };
            }

            return new AtmRestoreDecision
            {
                Bracket = b,
                Verdict = AtmRestoreVerdict.Deferred,
                Reason = b.BracketId + ": not picked back up on this attempt because " + why
                    + ". The record is kept and will be tried again ("
                    + (record.RestoreDeferrals + 1) + " of " + MaxRestoreDeferrals + ")."
            };
        }
    }
}
