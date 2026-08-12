#!/usr/bin/env python3
"""Every mutation battery on disk must be invoked by the CI workflow.

Why this exists: it has been got wrong twice. `mutate_p0_63.py` arrived in session 17,
after `ci/github-workflow-ci.yml` had been written and parked, and had to be added when
the workflow was activated. Then session 20 added `mutate_p1_71.py` and
`mutate_p0_67.py`, and CI ran three of five for a day. Both times CI was **weaker than
the local gate while looking complete**, which is the exact failure mode this project
keeps paying for -- see the handover's section 8, "a gate that cannot fail is worse than
no gate".

A battery nobody runs is not a gate. This is a text check, not a YAML one, on purpose:
it cares only that the filename appears as something CI executes, so it does not break
when the step layout changes.

Exit 0 = every battery is wired. Exit 1 = at least one is not.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
BATTERIES = REPO / "mutation"


def main() -> int:
    if not WORKFLOW.exists():
        print(f"FAIL: no workflow at {WORKFLOW.relative_to(REPO)}")
        return 1

    text = WORKFLOW.read_text(encoding="utf-8")
    batteries = sorted(p.name for p in BATTERIES.glob("mutate_*.py"))

    if not batteries:
        # Deleting every battery and passing would be the same vacuous-gate defect.
        print(f"FAIL: no mutate_*.py found in {BATTERIES.relative_to(REPO)}")
        return 1

    missing = [b for b in batteries if b not in text]

    for b in batteries:
        print(f"  {'MISSING' if b in missing else 'ok     '}  {b}")

    if missing:
        print()
        print(f"FAIL: {len(missing)} of {len(batteries)} batteries are never run by CI:")
        for b in missing:
            print(f"    mutation/{b}")
        print()
        print("Add a step to .github/workflows/ci.yml in the same commit that adds the")
        print("battery. A battery that only runs on the machine that wrote it is not a gate.")
        return 1

    print(f"\nOK: all {len(batteries)} mutation batteries are invoked by CI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
