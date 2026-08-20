"""P2-164: what counts as "a loss" for the escalating cooldown ladder, settled by measurement.

⚠️ THIS EXISTS BECAUSE RE-ASKING THE OPERATOR IS NOT HOW THIS CLOSES. They hold two defensible
views at once -- "any loss triggers me" and "a rail that charges eight minutes for a one-tick
scratch is a rail that gets switched off" -- and asked for the right answer rather than the one
they currently favour. The question is empirical.

THE CLAIM UNDER TEST, which is about THIS account and not about trading in general:
    a trade taken shortly after a loss is worse than a baseline trade.
If that holds only after REAL losses and not after scratches, the magnitude floor is measured and
its value falls out of the buckets. If it holds equally after both, viewpoint 1 is right on this
account's own evidence and the scratches count.

⚠️ AND THE COST IS PART OF THE ANSWER. A definition that pauses a third of the session is not
enforceable whatever the expectancy says, so this also reports how many minutes each candidate
definition would have paused, over the same history.

⚠️ REFUSE A CONCLUSION BELOW THE SAMPLE SIZE. A fitted floor from six observations is a preference
wearing a number. This script prints n for every bucket and says so when n is too small; if the
data cannot decide, the answer is viewpoint 1 -- the stricter rail -- not a guess.

SOURCE AND ITS LIMITS. There is no per-trade realized-PnL event in the ledger, so round trips are
reconstructed FIFO from `EXECUTION_UPDATE` records in `interventions.jsonl`. That means:
  * coverage starts when the guard started logging, and has a hole for every period it was down;
  * ⚠️ THE COPIER DUPLICATES ONE DECISION ACROSS MANY ACCOUNTS. Counting every account would weight
    a single operator decision by however many followers were live, so accounts are reported
    SEPARATELY and never pooled. The decision belongs to the account the operator trades by hand.
  * ⚠️ AND MOST OF THE VOLUME IS NOT THE OPERATOR TRADING. Measured 2026-08-20: the account with
    by far the largest sample (`Sim101`, n=125) is a SIM account whose executions are mostly
    copier-validation orders placed during hardening sessions plus ORB-strategy traffic --
    `SimCopy2`, `SimCopyTest1`, `Sim-ORB`, `Sim_All_Day_ORB` and `Playback101` are the same. A rail
    about the operator's TILT calibrated against test orders and an automated strategy would be
    measuring the wrong thing precisely, which is worse than measuring nothing. Only the funded
    account and the TAKEPROFIT evaluation accounts are discretionary, and the funded one has n=31.
    ⚠️ Do not raise n by pooling sim accounts in. The sample is small because the operator has
    traded 31 round trips through this guard, and that is the honest number.
"""
import collections
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Dollars per point. Micros are the operator's permitted set; the full-size roots are here only
# because a historical execution may predate the allow-list.
POINT_VALUE = {
    'MNQ': 2.0, 'MES': 5.0, 'MYM': 0.5, 'M2K': 5.0, 'MCL': 100.0, 'MGC': 10.0,
    'NQ': 20.0, 'ES': 50.0, 'YM': 5.0, 'RTY': 50.0, 'CL': 1000.0, 'GC': 100.0,
}

LEDGER_DIR = os.path.join(
    os.path.expanduser('~'), 'Documents', 'NinjaTrader 8', 'RiskGuard')


def parse_ts(s):
    # "2026-08-07T13:07:43.5185855Z" -> seconds since epoch, without pulling in a tz library.
    import datetime
    s = s.rstrip('Z')
    if '.' in s:
        head, frac = s.split('.', 1)
        frac = (frac + '000000')[:6]
        s = head + '.' + frac
        fmt = '%Y-%m-%dT%H:%M:%S.%f'
    else:
        fmt = '%Y-%m-%dT%H:%M:%S'
    return datetime.datetime.strptime(s, fmt).replace(
        tzinfo=datetime.timezone.utc).timestamp()


def load_executions():
    """Every EXECUTION_UPDATE, oldest first, from the live ledger and its archives."""
    paths = sorted(glob.glob(os.path.join(LEDGER_DIR, 'interventions.jsonl*')))
    if not paths:
        print('no ledger found under %s' % LEDGER_DIR)
        sys.exit(2)
    execs = []
    scanned = 0
    for p in paths:
        with open(p, encoding='utf-8', errors='replace') as f:
            for line in f:
                scanned += 1
                if 'EXECUTION_UPDATE' not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get('eventType') != 'EXECUTION_UPDATE':
                    continue
                data = d.get('data') or {}
                inst = data.get('instrument') or ''
                root = inst.split(' ')[0].upper()
                if root not in POINT_VALUE:
                    continue
                try:
                    execs.append({
                        'account': d.get('account'),
                        'root': root,
                        'action': data.get('action'),
                        'qty': int(data.get('quantity') or 0),
                        'price': float(data.get('price') or 0.0),
                        't': parse_ts(d.get('timestamp_utc')),
                    })
                except Exception:
                    continue
    execs.sort(key=lambda e: e['t'])
    print('scanned %d ledger line(s) across %d file(s); %d usable execution(s)'
          % (scanned, len(paths), len(execs)))
    return execs


def round_trips(execs):
    """FIFO round trips per (account, root). A trade OPENS at the first execution that takes the
    position away from flat and CLOSES when it returns to flat. A flip closes and re-opens.

    ⚠️ The ENTRY time is what the ladder is measured against -- the interval that matters is
    loss-close -> next-ENTRY, not close -> close -- so both are recorded.
    """
    books = collections.defaultdict(list)   # (account, root) -> [ [signed_qty, price], ... ]
    opened = {}
    trades = []

    for e in execs:
        key = (e['account'], e['root'])
        sign = 1 if e['action'] in ('Buy', 'BuyToCover') else -1
        qty = e['qty']
        if qty <= 0:
            continue
        book = books[key]
        if not book:
            opened[key] = e['t']

        remaining = qty
        pnl = 0.0
        # Close against opposing lots first (FIFO), then open the residue.
        while remaining > 0 and book and (book[0][0] > 0) != (sign > 0):
            lot = book[0]
            take = min(remaining, abs(lot[0]))
            direction = 1 if lot[0] > 0 else -1
            pnl += direction * (e['price'] - lot[1]) * take * POINT_VALUE[e['root']]
            lot[0] -= direction * take
            remaining -= take
            if lot[0] == 0:
                book.pop(0)
        if remaining > 0:
            book.append([sign * remaining, e['price']])

        if pnl != 0.0 or (not book and key in opened):
            if not book:
                trades.append({
                    'account': e['account'], 'root': e['root'],
                    'entry_t': opened.get(key, e['t']), 'exit_t': e['t'], 'pnl': pnl,
                })
                opened.pop(key, None)
    return trades


def fmt_money(x):
    return ('%+.2f' % x).rjust(9)


def report_account(account, trades, min_n):
    trades = sorted(trades, key=lambda t: t['exit_t'])
    n = len(trades)
    print()
    print('=' * 78)
    print('ACCOUNT %s -- %d reconstructed round trip(s)' % (account, n))
    print('=' * 78)
    if n < min_n:
        print('  n = %d, below the %d-trade floor. NO CONCLUSION from this account.'
              % (n, min_n))
        return

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    baseline = sum(t['pnl'] for t in trades) / n
    print('  baseline expectancy over ALL trades: %s  (n=%d, %d win / %d loss)'
          % (fmt_money(baseline), n, len(wins), len(losses)))

    # --- the claim: is the trade AFTER a loss worse than baseline? ---------------------------
    # Bucketed by the SIZE of the preceding loss, which is the axis the decision turns on.
    size_buckets = [
        ('scratch   |loss| <= $10', lambda p: 0 < -p <= 10),
        ('small     $10 < |loss| <= $25', lambda p: 10 < -p <= 25),
        ('medium    $25 < |loss| <= $50', lambda p: 25 < -p <= 50),
        ('large     |loss| > $50', lambda p: -p > 50),
    ]
    print()
    print('  EXPECTANCY OF THE NEXT TRADE, by the size of the loss before it')
    print('  %-32s %9s %6s   %s' % ('preceding loss', 'next E[$]', 'n', 'vs baseline'))
    for label, pred in size_buckets:
        nxt = [trades[i + 1]['pnl'] for i in range(n - 1) if pred(trades[i]['pnl'])]
        if not nxt:
            print('  %-32s %9s %6d   --' % (label, '-', 0))
            continue
        e = sum(nxt) / len(nxt)
        flag = '' if len(nxt) >= min_n else '  ⚠️ n too small'
        print('  %-32s %s %6d   %s%s'
              % (label, fmt_money(e), len(nxt), fmt_money(e - baseline), flag))

    # After a WIN, as the control. Without it, "worse after a loss" has nothing to be worse than.
    nxt_win = [trades[i + 1]['pnl'] for i in range(n - 1) if trades[i]['pnl'] > 0]
    if nxt_win:
        e = sum(nxt_win) / len(nxt_win)
        print('  %-32s %s %6d   %s'
              % ('CONTROL: after a WIN', fmt_money(e), len(nxt_win),
                 fmt_money(e - baseline)))

    # --- the gap axis: does the damage decay with time? --------------------------------------
    gap_buckets = [(0, 2), (2, 5), (5, 15), (15, 60), (60, 10 ** 9)]
    print()
    print('  EXPECTANCY OF THE NEXT TRADE AFTER ANY LOSS, by minutes from loss-close to next ENTRY')
    print('  %-32s %9s %6s   %s' % ('gap', 'next E[$]', 'n', 'vs baseline'))
    for lo, hi in gap_buckets:
        vals = []
        for i in range(n - 1):
            if trades[i]['pnl'] >= 0:
                continue
            gap = (trades[i + 1]['entry_t'] - trades[i]['exit_t']) / 60.0
            if lo <= gap < hi:
                vals.append(trades[i + 1]['pnl'])
        label = '%g - %s min' % (lo, 'inf' if hi > 10 ** 8 else '%g' % hi)
        if not vals:
            print('  %-32s %9s %6d   --' % (label, '-', 0))
            continue
        e = sum(vals) / len(vals)
        flag = '' if len(vals) >= min_n else '  ⚠️ n too small'
        print('  %-32s %s %6d   %s%s'
              % (label, fmt_money(e), len(vals), fmt_money(e - baseline), flag))

    # --- the cost of each candidate definition ------------------------------------------------
    # The P2-161 ladder as specified: 2, 4, 8 minutes on consecutive losses, then the lockout.
    print()
    print('  COST OF EACH CANDIDATE DEFINITION over this same history')
    print('  (P2-161 ladder: 2/4/8 min on consecutive losses, then a %d-loss lockout)' % 3)
    print('  %-28s %8s %9s %9s %7s' % ('a loss is...', 'losses', 'paused', 'active', 'lockouts'))
    # ⚠️ THE DENOMINATOR IS ACTIVE TRADING TIME, NOT WALL CLOCK. The first version of this divided
    # by (last exit - first entry), which on this history is 11.6 DAYS -- nights and weekends
    # included -- and reported 1.2% for a definition that pauses a fifth of the time the operator
    # is actually at the screen. A percentage is only as meaningful as what it is a percentage OF.
    import datetime
    per_day = collections.defaultdict(lambda: [None, None])
    for t in trades:
        day = datetime.datetime.fromtimestamp(
            t['entry_t'], datetime.timezone.utc).strftime('%Y-%m-%d')
        lo, hi = per_day[day]
        per_day[day] = [t['entry_t'] if lo is None else min(lo, t['entry_t']),
                        t['exit_t'] if hi is None else max(hi, t['exit_t'])]
    span_min = sum((hi - lo) / 60.0 for lo, hi in per_day.values())
    for label, floor in [('any negative', 0.0), ('|loss| > $10', 10.0),
                         ('|loss| > $25', 25.0), ('|loss| > $50', 50.0)]:
        streak = 0
        paused = 0.0
        lockouts = 0
        ladder = [2, 4, 8]
        counted = 0
        for t in trades:
            if -t['pnl'] > floor and t['pnl'] < 0:
                counted += 1
                streak += 1
                if streak >= 4:
                    lockouts += 1
                    paused += 60
                    streak = 0
                else:
                    paused += ladder[streak - 1]
            elif t['pnl'] > 0:
                streak = 0
        pct = (100.0 * paused / span_min) if span_min > 0 else 0.0
        print('  %-28s %8d %8.0fm %8.1f%% %7d'
              % (label, counted, paused, pct, lockouts))
    print('  denominator: %.0f minutes of ACTIVE trading across %d day(s) -- the sum of each'
          % (span_min, len(per_day)))
    print('  trading day (first entry to last exit), NOT wall clock -- wall clock would divide'
          ' by nights and weekends and understate every row above by an order of magnitude.')


def main():
    min_n = 30
    execs = load_executions()
    trades = round_trips(execs)
    if not trades:
        print('no round trips could be reconstructed -- nothing to measure')
        return 1
    by_acct = collections.defaultdict(list)
    for t in trades:
        by_acct[t['account']].append(t)

    print()
    print('round trips per account (NEVER pooled -- the copier duplicates one decision):')
    for a, ts in sorted(by_acct.items(), key=lambda kv: -len(kv[1])):
        print('  %-28s %5d' % (a, len(ts)))

    for a, ts in sorted(by_acct.items(), key=lambda kv: -len(kv[1])):
        report_account(a, ts, min_n)

    print()
    print('⚠️ READ THE n COLUMN BEFORE THE $ COLUMN. A bucket below %d is reported so the gap is'
          % min_n)
    print('   visible, not so it can be used. If no bucket clears the floor, the measurement has')
    print('   not decided anything and the answer is viewpoint 1 -- the stricter rail.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
