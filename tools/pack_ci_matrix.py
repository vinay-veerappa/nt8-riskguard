#!/usr/bin/env python3
"""Bin-pack the mutation batteries into a fixed number of CI jobs, longest-first.

⚠️ WHY PACKING, WHEN SHARDING IS WHAT MADE THIS FAST. Session 37 split one 1h56m job into
a 24-way matrix and got 12-20 min. At 33 batteries that same shape is now working against
itself: measured on run 31911413509, **20 of 33 jobs QUEUED** behind the ~20 concurrent
slots, the worst waiting 375s. Past the slot count, another job is not another runner --
it is another wait.

So the floor is no longer "checks + the longest battery". It is:

    checks + (total_battery_compute / slots) + per_job_overhead

which no amount of further splitting improves. Packing into exactly `slots` balanced jobs
is what reaches it.

⚠️ AND THE PER-JOB OVERHEAD IS REAL: 31s of checkout + setup-dotnet, measured. At 33 jobs
that is 17 minutes of compute spent on scaffolding; at 20 it is 10. Fewer, fuller jobs pay
it fewer times.

⚠️ THE ONE THING PACKING MUST NOT COST is the property that made the matrix safe in the
first place: every battery rewrites the SAME shared source files in place, so two running
CONCURRENTLY in one working tree corrupt each other -- that is how a killed batch left a
live mutate_cm4 mutant in TradeCopierEngine.cs. Batteries packed into one job run
SEQUENTIALLY in that job's own checkout, so the hazard does not return. Each restores its
originals before the next starts, which is the same guarantee a local sequential run has.

Usage:
    python tools/pack_ci_matrix.py --times run_times.tsv --bins 20
    python tools/pack_ci_matrix.py --bins 20          # uses the seconds in ci.yml comments
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

ENTRY = re.compile(r"\{\s*label:\s*([^,]+?),\s*battery:\s*([a-z0-9_]+\.py)\s*\}")
# The measured seconds live in the prose above each entry, as "NNNs".
SECONDS = re.compile(r"(\d+)s\b")


def read_entries() -> list[tuple[str, str]]:
    text = WORKFLOW.read_text(encoding="utf-8")
    return [(m.group(1).strip(), m.group(2)) for m in ENTRY.finditer(text)]


def read_times(path: Path | None) -> dict[str, float]:
    """label -> seconds, from a `name\tstartedAt\tcompletedAt` TSV (gh run view)."""
    if path is None:
        return {}
    import datetime as dt

    out: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3 or not parts[1] or parts[1] == "null":
            continue
        s = dt.datetime.fromisoformat(parts[1].replace("Z", "+00:00"))
        e = dt.datetime.fromisoformat(parts[2].replace("Z", "+00:00"))
        out[parts[0].strip()] = (e - s).total_seconds()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--times", type=Path, default=None)
    ap.add_argument("--bins", type=int, default=20)
    args = ap.parse_args()

    entries = read_entries()
    if not entries:
        print("REFUSING: no matrix entries found -- the workflow shape changed.")
        return 2

    times = read_times(args.times)
    missing = [lab for lab, _ in entries if lab not in times]
    if times and missing:
        # ⚠️ Do NOT silently default a missing weight to zero: a battery weighted 0 packs
        # into whichever bin is fullest and makes the worst bin worse, while the printed
        # plan looks balanced. Refuse instead.
        print("REFUSING: no measured time for: %s" % ", ".join(sorted(missing)))
        return 2
    if not times:
        print("REFUSING: --times is required; packing on guessed weights produces a plan "
              "that looks balanced and is not.")
        return 2

    # Longest Processing Time first: sort descending, drop each into the emptiest bin.
    # Simple, and within 4/3 of optimal -- far inside the noise of runner variance.
    work = sorted(((times[lab], lab, bat) for lab, bat in entries), reverse=True)
    bins: list[list[tuple[float, str, str]]] = [[] for _ in range(args.bins)]
    loads = [0.0] * args.bins
    for secs, lab, bat in work:
        i = loads.index(min(loads))
        bins[i].append((secs, lab, bat))
        loads[i] += secs

    total = sum(times[lab] for lab, _ in entries)
    print("batteries      : %d" % len(entries))
    print("bins           : %d" % args.bins)
    print("total compute  : %.0fs (%.1f min)" % (total, total / 60))
    print("heaviest bin   : %.0fs   lightest %.0fs   ideal %.0fs"
          % (max(loads), min(loads), total / args.bins))
    print("predicted wall : ~%.1f min (checks 96s + heaviest bin + 31s overhead)"
          % ((96 + max(loads) + 31) / 60))
    print()
    for i, b in enumerate(sorted(bins, key=lambda x: -sum(t for t, _, _ in x))):
        names = " ".join(bat for _, _, bat in b)
        # ⚠️ `for _, _, lab in b` here printed the FILENAME as the label on the first run --
        # the tuple is (secs, label, battery) and the third element is the battery. Harmless
        # in a plan, and exactly the kind of index slip that would have shipped a matrix whose
        # job names told you nothing about which battery failed.
        labels = "+".join(lab for _, lab, _ in b)
        print("          - { label: \"%s\", batteries: \"%s\" }   # %.0fs"
              % (labels, names, sum(t for t, _, _ in b)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
