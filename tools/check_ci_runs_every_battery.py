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

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
BATTERIES = REPO / "mutation"


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


def execution_sites(text: str, name: str) -> int:
    """How many places in the comment-stripped workflow actually run `name`."""
    escaped = re.escape(name)
    matrix = re.findall(r"battery:\s*%s(?:\s|$|[,}])" % escaped, text)
    runs = re.findall(r"run:.*%s" % escaped, text)
    return len(matrix) + len(runs)


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

    counts = {b: execution_sites(text, b) for b in batteries}
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

    print(f"\nOK: all {len(batteries)} mutation batteries are executed by CI, exactly once each.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
