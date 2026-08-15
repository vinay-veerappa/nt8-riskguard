// F-6. Push alerts (Discord / Telegram) -- the DECISION half.
//
// WHY THIS SHAPE. The events worth pushing already exist: every one of them passes through
// `LogEvent` and drains to `interventions.jsonl` at a single point in `ExecuteSafetySweep`'s
// `finally`, already outside the guard's lock. So this is a SINK on an existing stream, not new
// instrumentation, and nothing about rule evaluation changes to add it.
//
// ⚠️ NAMES NO NinjaTrader TYPE, so the test build executes it. The transport half (a socket, a
// timeout, a background thread) lives with the addon; everything that DECIDES anything lives
// here, because a decision that only `nt_compile` can check is a decision nothing checks.
//
// ⚠️ AND THE HAZARD IS NOT THE NETWORK, IT IS THE VOLUME. This repo has hit "an alarm that is
// always on is off" seven times. `NAKED_POSITION` alone repeated every 10s -- 180 lines in one
// log -- and `P2-107` found every rule without a latch streaming one line per evaluation. Piping
// that to a phone does not produce an alerted operator, it produces a muted channel, which is
// strictly worse than no alerts at all because it looks like coverage. Every rule below exists to
// stop that.
using System;
using System.Collections.Generic;
using System.Text;

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>What the sink decided about one event, and why.</summary>
    public sealed class GuardAlertDecision
    {
        public bool Send;
        /// <summary>Always populated -- on a refusal this is the reason, which is the thing an
        /// operator asking "why did I not get told" needs. A silent drop is unanswerable.</summary>
        public string Reason;
        public string Severity;
        public string Title;
        public string Body;
    }

    public sealed class GuardAlertSink
    {
        // Severity is a property of the EVENT, not of the message text. Classifying by scanning
        // the message for words like "breach" would make the channel's behaviour depend on
        // wording that gets edited for readability.
        private static readonly string[] CriticalEvents =
        {
            "DAILY_LOSS_BREACH", "TRAILING_DD_BREACH", "PEAK_GIVEBACK_BREACH",
            "MAX_SIZE_BREACH", "FIRM_DAILY_LOSS_BREACH", "FIRM_TRAILING_DD_BREACH",
            "LOCKOUT_IMPOSED", "EMERGENCY_FLATTEN", "LOCKOUT_SWEEP",
        };

        private static readonly string[] WarningEvents =
        {
            "NAKED_POSITION", "ORPHAN_STOP", "FSM_DIVERGENCE", "BLACKLIST_CANCEL",
            "PER_INSTRUMENT_CAP_CANCEL", "COPIER_QUARANTINED", "FILL_NOT_MEASURED",
            "LOCKOUT_STUCK", "ARMED_ON_START", "DISARMED",
        };

        /// <summary>
        /// ⚠️ AN UNKNOWN EVENT TYPE IS `info`, NOT `critical`. The opposite default reads as
        /// "fail safe" and is not: this repo adds event types constantly, and defaulting them
        /// loud means every new log line pages the operator until someone classifies it. The
        /// channel would be muted within a week and the muting would be invisible.
        /// </summary>
        public static string SeverityOf(string eventType)
        {
            if (string.IsNullOrWhiteSpace(eventType)) return "info";
            foreach (var e in CriticalEvents)
                if (string.Equals(e, eventType, StringComparison.OrdinalIgnoreCase)) return "critical";
            foreach (var e in WarningEvents)
                if (string.Equals(e, eventType, StringComparison.OrdinalIgnoreCase)) return "warning";
            return "info";
        }

        private static int RankOf(string severity)
        {
            if (string.Equals(severity, "critical", StringComparison.OrdinalIgnoreCase)) return 2;
            if (string.Equals(severity, "warning", StringComparison.OrdinalIgnoreCase)) return 1;
            return 0;
        }

        // The budget record, keyed by ACCOUNT + EVENT TYPE. `P2-107` established both halves of
        // this: the scope must carry the producer as well as the account (or one producer's
        // silence clears another's records), and the record clears when the CONDITION RESOLVES,
        // never on a timer -- a time-based expiry re-admits while the condition is still true,
        // which is the same defect on a slower clock.
        private readonly Dictionary<string, int> _sent =
            new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// ⚠️ THE SEPARATOR IS NOT DECORATION, and it was wrong on the first write. A bare
        /// concatenation makes account `AB` + event `C` the SAME key as account `A` + event `BC`:
        /// two unrelated conditions sharing one budget, so one silences the other and resolving
        /// either refills both. Found while writing the mutation battery -- reading the line had
        /// not found it, and neither had ten passing tests. A unit separator cannot occur in an
        /// NT8 account name or an event type, and it is written as an escape rather than a raw
        /// byte so that it is greppable and visible in a diff.
        /// </summary>
        private static string KeyOf(string account, string eventType)
        {
            return (account ?? "(null)") + "\u001F" + (eventType ?? "(null)");
        }

        /// <summary>
        /// How many alerts one (account, eventType) condition may produce before it goes quiet.
        ///
        /// ⚠️ THE 1 IS THE FIX, NOT A TUNING VALUE -- the same reasoning as `P2-101` and
        /// `P2-107`. A repeating condition's SECOND identical message carries no information the
        /// first did not; what changes an operator's decision is that it STARTED. Critical events
        /// get 3 because a breach that keeps deepening is genuinely new information, and the
        /// escalation is what you want to see.
        /// </summary>
        public static int BudgetFor(string severity)
        {
            return RankOf(severity) >= 2 ? 3 : 1;
        }

        /// <summary>
        /// Decides whether one event becomes a push.
        ///
        /// `minSeverity` is the operator's floor ("critical", "warning" or "info"). The default
        /// the config ships is "warning": `info` is the whole rest of the audit stream, and it
        /// belongs in `interventions.jsonl`, which is where it already is.
        /// </summary>
        public GuardAlertDecision Consider(string account, string eventType, string message,
                                           string mode, bool isArmed, string minSeverity)
        {
            var d = new GuardAlertDecision();
            d.Severity = SeverityOf(eventType);

            if (string.IsNullOrWhiteSpace(eventType))
            {
                d.Reason = "no eventType; refusing rather than pushing an unattributable alert";
                return d;
            }

            if (RankOf(d.Severity) < RankOf(minSeverity))
            {
                d.Reason = "severity '" + d.Severity + "' is below the configured floor '"
                         + (minSeverity ?? "warning") + "'";
                return d;
            }

            string key = KeyOf(account, eventType);
            int already;
            _sent.TryGetValue(key, out already);
            int budget = BudgetFor(d.Severity);
            if (already >= budget)
            {
                d.Reason = "budget spent: " + already + " of " + budget + " alert(s) already sent "
                         + "for " + eventType + " on " + account + ", and the condition has not "
                         + "resolved. Suppressing rather than repeating -- see interventions.jsonl "
                         + "for every occurrence.";
                return d;
            }

            _sent[key] = already + 1;
            d.Send = true;
            d.Reason = "sent " + (already + 1) + " of " + budget;
            d.Title = TitleFor(d.Severity, eventType, mode, isArmed);
            d.Body = BodyFor(account, eventType, message, mode, isArmed);
            return d;
        }

        /// <summary>
        /// The condition behind (account, eventType) is no longer true, so the next occurrence is
        /// news again and gets its budget back.
        ///
        /// ⚠️ THIS IS THE HALF THAT IS EASY TO LEAVE OUT, and leaving it out converts a budget
        /// into a permanent gag: the first `DAILY_LOSS_BREACH` of the session would be the only
        /// one you were ever told about, including the one three days later. `P2-107` had to take
        /// the accounts the producer EVALUATED, including the ones it decided needed nothing,
        /// precisely so this could be called.
        /// </summary>
        public void NoteResolved(string account, string eventType)
        {
            _sent.Remove(KeyOf(account, eventType));
        }

        /// <summary>Everything the sink is currently suppressing, so a status read can say so.</summary>
        public int SuppressedConditionCount { get { return _sent.Count; } }

        private static string TitleFor(string severity, string eventType, string mode, bool isArmed)
        {
            var sb = new StringBuilder();
            sb.Append(RankOf(severity) >= 2 ? "\U0001F6A8" : "⚠");
            sb.Append(' ');
            // ⚠️ THE MODE IS IN THE TITLE, NOT BURIED. In `shadow` the guard OBSERVES and does not
            // act (`P2-92`), so an alert reading "FLATTENED" would be a false statement about the
            // account -- and it is the statement an operator acts on at 3am. Shadow alerts say
            // WOULD.
            if (!IsActing(mode) || !isArmed) sb.Append("[WOULD] ");
            sb.Append(eventType);
            return sb.ToString();
        }

        private static string BodyFor(string account, string eventType, string message,
                                      string mode, bool isArmed)
        {
            var sb = new StringBuilder();
            sb.Append("account: ").Append(string.IsNullOrWhiteSpace(account) ? "(none)" : account);
            sb.Append("\nmode: ").Append(string.IsNullOrWhiteSpace(mode) ? "(unset)" : mode);
            sb.Append(isArmed ? " (armed)" : " (DISARMED)");
            if (!IsActing(mode) || !isArmed)
                sb.Append("\n⚠ nothing was done to this account -- the guard is observing. "
                        + "This is what it WOULD have done.");
            if (!string.IsNullOrWhiteSpace(message))
                sb.Append('\n').Append(message);
            return sb.ToString();
        }

        private static bool IsActing(string mode)
        {
            return string.Equals(mode, "live", StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// A webhook URL IS A CREDENTIAL: anyone holding it can post into the operator's channel.
        ///
        /// ⚠️ AND THIS ADDON ECHOES ITS CONFIG OVER HTTP on :7890 (`/api/riskguard/config`, and
        /// `nt_riskguard_inventory` reads the same structures), so a URL stored in config is a URL
        /// published unless something redacts it. The bridge already refuses to reconstruct
        /// NT8's saved broker credentials for exactly this reason; a secret this component itself
        /// introduces must not walk out the door the same day.
        ///
        /// Keeps enough to be recognisable -- an operator has to be able to tell which of two
        /// webhooks is configured without being shown either.
        /// </summary>
        public static string Redact(string url)
        {
            if (string.IsNullOrWhiteSpace(url)) return "(unset)";
            string trimmed = url.Trim();
            int scheme = trimmed.IndexOf("://", StringComparison.Ordinal);
            string host = trimmed;
            if (scheme >= 0)
            {
                int hostStart = scheme + 3;
                int slash = trimmed.IndexOf('/', hostStart);
                host = slash > hostStart ? trimmed.Substring(hostStart, slash - hostStart)
                                         : trimmed.Substring(hostStart);
            }
            if (string.IsNullOrWhiteSpace(host)) return "(malformed)";
            // The last four characters are the discriminator between two webhooks on one host.
            string tail = trimmed.Length >= 4 ? trimmed.Substring(trimmed.Length - 4) : "";
            return host + "/***" + tail;
        }
    }
}
