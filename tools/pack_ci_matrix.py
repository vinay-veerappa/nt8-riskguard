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

# Matches BOTH shapes on purpose: the pre-packing `battery: x.py` and the packed
# `batteries: "x.py y.py"`. Not for compatibility -- so that --apply is re-runnable
# against a file it has already rewritten. A packer that can only read the shape it
# replaces is a one-shot tool, and the next re-measure would have to hand-edit.
ENTRY = re.compile(r"\{\s*label:\s*(.+?)\s*,\s*batter(?:y|ies):\s*(.+?)\s*\}")
# The measured seconds live in the prose above each entry, as "NNNs".
SECONDS = re.compile(r"(\d+)s\b")

INDENT = " " * 10


def _unquote(s: str) -> str:
    return s.strip().strip('"').strip()


def parse_entry(line: str) -> tuple[str, list[str]] | None:
    """-> (label, [battery, ...]) for a matrix entry line, else None."""
    m = ENTRY.search(line)
    if not m:
        return None
    return _unquote(m.group(1)), _unquote(m.group(2)).split()


def read_entries() -> list[tuple[str, str]]:
    """-> [(label, battery)]. One row per BATTERY, so a packed file re-reads as the 33
    independent questions it still is -- the bins are a scheduling detail, not a merge."""
    out: list[tuple[str, str]] = []
    for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
        parsed = parse_entry(line)
        if parsed is None:
            continue
        label, bats = parsed
        # A packed label is "A+B"; split it back so each battery keeps its own name and
        # its own measured weight. Joining is lossy in one direction only, and this is it.
        labels = label.split("+") if len(bats) > 1 else [label]
        if len(labels) != len(bats):
            print("REFUSING: entry %r has %d label(s) for %d batteries -- the label must "
                  "name each one, or a failing job cannot be traced to a battery."
                  % (label, len(labels), len(bats)))
            sys.exit(2)
        out.extend((lab.strip(), bat) for lab, bat in zip(labels, bats))
    return out


def region_bounds(lines: list[str]) -> tuple[int, int]:
    """[start, end) of the matrix entry region: after `include:`, up to `steps:`."""
    start = next(i for i, l in enumerate(lines) if l.strip() == "include:") + 1
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "steps:")
    return start, end


def read_blocks() -> dict[str, list[str]]:
    """battery filename -> the comment lines directly above its entry.

    ⚠️ The prose is the point. Each block records why that battery exists and what its
    survivors meant -- it is the densest documentation in the repo, and repacking must
    MOVE it, never drop it. A rewrite that silently discarded it would look like a clean
    diff and cost more than the four minutes this whole change is buying.
    """
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start, end = region_bounds(lines)
    blocks: dict[str, list[str]] = {}
    pending: list[str] = []
    for i in range(start, end):
        line = lines[i]
        parsed = parse_entry(line)
        if parsed is None:
            if line.strip().startswith("#"):
                pending.append(line.rstrip())
            elif not line.strip():
                pending = []          # a blank line ends a block
            continue
        _, bats = parsed
        # A bin's block belongs to its FIRST battery when re-read; on the first (unpacked)
        # pass each entry has exactly one battery, so this is exact. On a re-pack the
        # blocks travel together, which is the behaviour we want anyway.
        blocks[bats[0]] = pending
        pending = []
    return blocks


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
    ap.add_argument("--apply", action="store_true",
                    help="rewrite the matrix in ci.yml (default: print the plan only)")
    # ⚠️ MEASURED (run 31911413509): checkout 5s + setup-dotnet 25s + setup-python 0s. A job's
    # duration from `gh run view` INCLUDES it, so the raw times are not battery weights -- and
    # the error is not uniform: it inflates a 2-battery bin by 62s against a singleton's 31s,
    # so packing on raw times systematically UNDER-fills the packed bins. That is the exact
    # "looks balanced and is not" this tool refuses to do with missing weights; a weight that
    # is wrong by a known constant deserves the same treatment as one that is absent.
    ap.add_argument("--overhead", type=float, default=31.0,
                    help="per-job setup seconds included in each measured time (measured: 31)")
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

    # Strip the setup each measured job paid ONCE, leaving the battery's own work. A packed
    # bin pays it once too, not once per battery, so this is what makes the bin totals below
    # mean "how long this job will take" rather than "the sum of things that never co-ran".
    work_secs = {lab: max(1.0, times[lab] - args.overhead) for lab, _ in entries}

    # Longest Processing Time first: sort descending, drop each into the emptiest bin.
    # Simple, and within 4/3 of optimal -- far inside the noise of runner variance.
    work = sorted(((work_secs[lab], lab, bat) for lab, bat in entries), reverse=True)
    bins: list[list[tuple[float, str, str]]] = [[] for _ in range(args.bins)]
    loads = [0.0] * args.bins
    for secs, lab, bat in work:
        i = loads.index(min(loads))
        bins[i].append((secs, lab, bat))
        loads[i] += secs

    total_raw = sum(times[lab] for lab, _ in entries)
    total = sum(work_secs.values())
    slowest = max(loads) + args.overhead
    print("batteries      : %d" % len(entries))
    print("bins           : %d" % args.bins)
    print("measured jobs  : %.0fs (%.1f min) including %.0fs x %d setup"
          % (total_raw, total_raw / 60, args.overhead, len(entries)))
    print("battery compute: %.0fs (%.1f min) with setup removed" % (total, total / 60))
    print("heaviest bin   : %.0fs   lightest %.0fs   ideal %.0fs   (work only)"
          % (max(loads), min(loads), total / args.bins))
    print("slowest job    : %.0fs (heaviest bin + %.0fs setup, paid once)"
          % (slowest, args.overhead))
    print("predicted wall : ~%.1f min (checks 96s + slowest job)" % ((96 + slowest) / 60))
    # ⚠️ The floor is whichever is larger: the ideal bin, or the LONGEST SINGLE battery --
    # no packing splits a battery. Say so, or the next person reads a plan that cannot be
    # beaten as one that merely was not.
    longest = max(work_secs.values())
    longest_lab = max(work_secs, key=lambda k: work_secs[k])
    if longest > total / args.bins:
        print("floor          : %s alone is %.0fs of work -- packing cannot go below "
              "~%.1f min until that battery is split."
              % (longest_lab, longest, (96 + longest + args.overhead) / 60))
    print()
    ordered = sorted(bins, key=lambda x: -sum(t for t, _, _ in x))
    emitted: list[str] = []
    for b in ordered:
        names = " ".join(bat for _, _, bat in b)
        # ⚠️ `for _, _, lab in b` here printed the FILENAME as the label on the first run --
        # the tuple is (secs, label, battery) and the third element is the battery. Harmless
        # in a plan, and exactly the kind of index slip that would have shipped a matrix whose
        # job names told you nothing about which battery failed.
        labels = "+".join(lab for _, lab, _ in b)
        # The decomposition is carried in the comment on purpose: once packed, `gh run view`
        # reports the BIN's duration, not each battery's, so the next re-measure would have
        # no weights to pack on. The run step also prints a per-battery `BATTERY_SECONDS`
        # line for the same reason -- see the note beside it in ci.yml.
        parts = " + ".join("%s %.0fs" % (lab, t) for t, lab, _ in sorted(b, reverse=True))
        line = ("%s- { label: \"%s\", batteries: \"%s\" }   # %.0fs = %s"
                % (INDENT, labels, names, sum(t for t, _, _ in b), parts))
        emitted.append(line)
        print(line)

    if not args.apply:
        print("\n(plan only -- pass --apply to rewrite the matrix in ci.yml)")
        return 0

    blocks = read_blocks()
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start, end = region_bounds(lines)

    body: list[str] = []
    for b, line in zip(ordered, emitted):
        for _, _, bat in sorted(b, reverse=True):
            body.extend(blocks.get(bat, []))
        body.append(line)
        body.append("")
    while body and not body[-1].strip():
        body.pop()

    new = lines[:start] + body + lines[end:]
    WORKFLOW.write_text("\n".join(new) + "\n", encoding="utf-8")

    # ⚠️ Assert the rewrite kept every battery, by RE-READING the file rather than trusting
    # the list we just built from. The failure this guards against is the one that would look
    # like a clean diff: a battery whose prose survived while its entry did not.
    after = {bat for _, bat in read_entries()}
    before = {bat for lab, bat in entries}
    if after != before:
        print("\nFAIL: the rewrite changed the battery set -- restore ci.yml from git.")
        print("  lost:  %s" % (sorted(before - after) or "none"))
        print("  added: %s" % (sorted(after - before) or "none"))
        return 2

    print("\nAPPLIED: %d batteries in %d jobs, all %d still wired."
          % (len(before), args.bins, len(after)))
    print("Now run: python tools/check_ci_runs_every_battery.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
