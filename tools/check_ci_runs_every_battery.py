#!/usr/bin/env python3
"""Every mutation battery on disk must be EXECUTED by the CI workflow.

Why this exists: it has been got wrong twice. `mutate_p0_63.py` arrived in session 17,
after `ci/github-workflow-ci.yml` had been written and parked, and had to be added when
the workflow was activated. Then session 20 added `mutate_p1_71.py` and
`mutate_p0_67.py`, and CI ran three of five for a day. Both times CI was **weaker than
the local gate while looking complete**, which is the exact failure mode this project
keeps paying for -- see the handover's section 8, "a gate that cannot fail is worse than
no gate".

⚠️ **WHY IT IS NO LONGER A PLAIN SUBSTRING CHECK (2026-08-14, session 37).** It used to
ask only whether the filename appeared anywhere in `ci.yml`, which was honest while every
battery had its own `run:` step. Session 37 moved them into a `strategy.matrix`, and every
matrix entry in that file carries a long prose comment ABOVE it naming the battery. A
battery deleted from the matrix but left described in its comment would still have passed
the old check -- a gate reporting "all 24 wired" while running 23. That is this repo's own
recurring defect (`a gate nobody reads is a comment`) turned inside out: a comment being
read as a gate.

So comments are stripped first, and the name must then appear in a form that actually
runs something:

  * `battery: mutate_x.py` -- a matrix entry, or
  * a `run:` line naming it (the pre-matrix shape, still valid).

It also fails on a DUPLICATE entry: two matrix rows for one battery burn a concurrency
slot re-proving something, and on the free plan's 20 parallel jobs a wasted slot pushes a
real battery into the next wave.

Exit 0 = every battery is wired exactly once. Exit 1 = at least one is not.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ⚠️ Windows defaults stdout to cp1252. Every gate in this repo prints mutant
# descriptions and plan text full of non-ASCII, and it only needs to print them
# when it is FAILING -- so without this a gate dies exactly when it has something
# to say, and the traceback reads as a defect in the script rather than a finding.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
BATTERIES = REPO / "mutation"
# The gate scripts live in both directories: tools/check_*.py, plus mutation/check_anchors.py.
GATE_DIRS = (REPO / "tools", REPO / "mutation")


def strip_comments(text: str) -> str:
    """Drop YAML comments. Line-based: everything from the first `#` on a line goes.

    That is exact for this workflow, which has no `#` inside a quoted scalar -- and if one
    is ever added, this check gets STRICTER (it stops seeing part of a run line), never
    laxer. A gate whose failure mode is a false alarm is the acceptable direction.
    """
    out = []
    for line in text.splitlines():
        hash_at = line.find("#")
        out.append(line if hash_at < 0 else line[:hash_at])
    return "\n".join(out)


# A packed matrix entry: `- { label: "A+B", batteries: "mutate_a.py mutate_b.py" }`.
# ⚠️ Deliberately does NOT match the pre-packing singular `battery: mutate_a.py`. That shape
# stopped RUNNING anything the moment the run step became a loop over `matrix.batteries`, so
# matching it would report a battery as wired that CI never executes -- this gate's own
# original defect, one shape later. A reverted entry now reads as MISSING, which is loud.
ENTRY = re.compile(r"\{\s*label:\s*(?P<label>.+?)\s*,\s*batteries:\s*\"(?P<batteries>[^\"]*)\"\s*\}")

# ...and the list must be CONSUMED, not merely declared. A gate that a value is COMPUTED is
# not a gate that it is USED -- four mutants in this project have now beaten a source check
# that assumed otherwise. If the run step stops iterating this list, every battery below is
# declared and none of them run, and the count above would still say "all 33 wired".
CONSUMES = re.compile(r"for\s+\w+\s+in\s+\$\{\{\s*matrix\.batteries\s*\}\}")


def execution_sites(text: str) -> dict[str, int]:
    """battery filename -> how many times the comment-stripped workflow actually runs it.

    Tokenised on whitespace rather than substring-matched: `mutate_p199.py` is a substring of
    nothing here today, but `mutate_p1_71.py` and `mutate_p1_76.py` differ by one character
    and a packed list puts them on ONE line, which is where a substring check starts counting
    a neighbour's name as its own.
    """
    counts: dict[str, int] = {}
    for m in ENTRY.finditer(text):
        for name in m.group("batteries").split():
            counts[name] = counts.get(name, 0) + 1
    # The pre-matrix shape, still valid: a `run:` line naming the battery directly.
    for m in re.finditer(r"run:.*?(mutate_[a-z0-9_]+\.py)", text):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


# ⚠️ THE SLOT ALLOWANCE IS 20 JOBS ACCOUNT-WIDE, SHARED WITH `nt8-mcp-bridge` -- not 20 per
# workflow. 19 leaves exactly one for the sibling repo, whose CI is a single job.
#
# This is a GATE and not a comment because the fact was already documented, correctly, at the
# top of ci.yml since session 45, and session 48 still hand-edited the matrix to 21 bins. The
# measurement: 21 bins + the bridge's 1 job = 22 against 20, two batteries queued 302s and
# 314s, and the run went 726s -> 853s. The one that started 1 SECOND after the bridge's job
# ended is the whole proof. From inside a waiting run none of that is visible, so the failure
# presents as an unexplained regression in a push that changed nothing about timing.
#
# Costs nothing to hold: UI4 is 493s of work and the ideal bin at 19 is 451s, so UI4 -- not
# the bin count -- is the floor at 17, 18, 19 AND 20 bins. All four predict the same ~10.3
# min. Raising this number buys zero and re-admits the queue.
MAX_BINS = 19


def main() -> int:
    if not WORKFLOW.exists():
        print(f"FAIL: no workflow at {WORKFLOW.relative_to(REPO)}")
        return 1

    text = strip_comments(WORKFLOW.read_text(encoding="utf-8"))
    batteries = sorted(p.name for p in BATTERIES.glob("mutate_*.py"))

    if not batteries:
        # Deleting every battery and passing would be the same vacuous-gate defect.
        print(f"FAIL: no mutate_*.py found in {BATTERIES.relative_to(REPO)}")
        return 1

    if not CONSUMES.search(text):
        print("FAIL: the matrix declares `batteries:` lists, but no run step iterates")
        print("      `${{ matrix.batteries }}`. Every battery below would be listed and none")
        print("      of them executed, and the per-battery count would still read 'wired'.")
        return 1

    # Counted HERE, before the per-battery verdicts, because that is the only position where
    # it can fire. Placed after them it was unreachable: no matrix entries means every battery
    # reads as missing, which returns first -- a branch with no input that reaches it, which is
    # the "green that can never be red" this repo has been caught shipping before. From here
    # the reachable input is real and specific: the run step still loops over
    # `matrix.batteries` (CONSUMES passed, just above) while the entry list is empty or has
    # changed shape enough that ENTRY no longer matches it.
    bins = len(ENTRY.findall(text))
    if bins == 0:
        print("FAIL: a run step iterates `${{ matrix.batteries }}` but no matrix entry parsed.")
        print("      Either the list is empty or its shape changed. Every check below would")
        print("      then be inspecting nothing, so this refuses rather than reporting on it.")
        return 1
    if bins > MAX_BINS:
        print(f"FAIL: the matrix has {bins} bins; the ceiling is {MAX_BINS}.")
        print()
        print("GitHub allows 20 concurrent jobs ACCOUNT-WIDE, shared with nt8-mcp-bridge. Past")
        print("that, another bin is not another runner -- it is another WAIT, and the wait is")
        print("invisible from inside the run doing the waiting. Measured: 21 bins pushed")
        print("alongside the bridge ran 853s against the 726s the arrangement it replaced took.")
        print()
        print("Re-pack instead of adding a bin -- the bins are an OUTPUT of the packer, so")
        print("'which existing bin has room' is the wrong question:")
        print("    python tools/pack_ci_matrix.py --times run_times.tsv --bins 19 --apply")
        return 1

    sites = execution_sites(text)
    counts = {b: sites.get(b, 0) for b in batteries}
    # A name wired in the workflow that has no file on disk is the mirror failure: the matrix
    # spends a slot on `python mutation/<gone>.py`, which exits non-zero for a reason that has
    # nothing to do with mutation. Cheap to catch here, and nothing else looks.
    orphans = sorted(set(sites) - set(batteries))
    missing = [b for b in batteries if counts[b] == 0]
    duplicated = [b for b in batteries if counts[b] > 1]

    for b in batteries:
        n = counts[b]
        state = "MISSING" if n == 0 else ("x%d    " % n if n > 1 else "ok     ")
        print(f"  {state}  {b}")

    if missing:
        print()
        print(f"FAIL: {len(missing)} of {len(batteries)} batteries are never run by CI:")
        for b in missing:
            print(f"    mutation/{b}")
        print()
        print("Add a matrix entry to .github/workflows/ci.yml in the same commit that adds")
        print("the battery. A battery that only runs on the machine that wrote it is not a")
        print("gate. NOTE: comments are stripped before this check, so describing a battery")
        print("in the prose above a matrix entry does not count as running it.")
        return 1

    if orphans:
        print()
        print(f"FAIL: {len(orphans)} battery/batteries are wired but do not exist on disk:")
        for b in orphans:
            print(f"    mutation/{b}")
        print()
        print("The job will fail on a missing file, which reads like a mutation failure and is")
        print("not one. Remove the matrix entry in the same commit that removes the battery.")
        return 1

    if duplicated:
        print()
        print(f"FAIL: {len(duplicated)} battery/batteries are wired more than once:")
        for b in duplicated:
            print(f"    mutation/{b}  ({counts[b]} execution sites)")
        print()
        print("Two rows for one battery re-prove the same thing and burn a concurrency slot;")
        print("the free plan runs 20 jobs at once and there are more batteries than that, so")
        print("a wasted slot pushes a real battery into the next wave.")
        return 1

    # ---- the gate scripts ----------------------------------------------------------------
    # Added 2026-08-18, and it is the CLASS of the defect this file was already written for.
    # Both repos' copies globbed mutation/ only, so no gate script in either repo was ever
    # required to be wired anywhere. The bridge was found with tools/check_bridge_parses.py on
    # disk and unrun since the day it was written -- the only automated reader of
    # McpBridgeAddOn.cs, which no test build compiles. This side happened to be fully wired,
    # which is luck, not a mechanism; the gap could open here on the next gate written.
    #
    # Matched on the REPO-RELATIVE PATH rather than the bare name, so `python tools/x.py` and
    # `python mutation/x.py` are not interchangeable evidence for the same basename.
    gates = sorted(
        set(g.relative_to(REPO).as_posix()
            for d in GATE_DIRS if d.is_dir()
            for g in d.glob("check_*.py")))
    if not gates:
        print("FAIL: no check_*.py under tools/ or mutation/. This half would pass vacuously.")
        return 1

    print()
    gate_problems = []
    for rel in gates:
        n = len(re.findall(r"run:[^\n]*" + re.escape(rel), text))
        state = "MISSING" if n == 0 else ("x%d    " % n if n > 1 else "ok     ")
        print(f"  {state}  {rel}")
        if n != 1:
            gate_problems.append((rel, n))

    if gate_problems:
        print()
        print(f"FAIL: {len(gate_problems)} gate(s) are not wired exactly once:")
        for rel, n in gate_problems:
            print(f"    {rel}  ({n} execution sites)")
        print()
        print("A gate nobody executes cannot fail, and from outside it is indistinguishable")
        print("from one that passes. Wire it in the same commit that writes it.")
        return 1

    print(f"\nOK: all {len(batteries)} mutation batteries are executed by CI, exactly once")
    print(f"    each, in {bins} bins (ceiling {MAX_BINS}, to leave a slot for the sibling repo),")
    print(f"    and all {len(gates)} gate scripts are executed exactly once each.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
