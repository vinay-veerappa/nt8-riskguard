#!/usr/bin/env python3
"""`RiskGuardAddOn.Version` must equal the newest git tag reachable from HEAD.

Why this exists: that constant is what `GET /api/riskguard/version` reports, so it is
how an operator or an agent finds out what is running on a live account. It is
hand-maintained, and on 2026-08-13 it drifted within hours: `v1.2.0` was tagged,
deployed and compiled while the constant still said `1.1.0`, so the box reported the
previous release. `docs/VERSION.md` says to trust the tag over the constant -- true, and
not a reason to leave the constant lying.

This is the same defect class as everything else fixed that day: a report that does not
match what it describes. P0-68 (`nt_change_order` claiming "modified" without observing
it), P1-70 (a log line claiming success before settle), P1-74 (an argument that was not
a field). A version string is a report too.

Deliberately compares against the newest tag REACHABLE FROM HEAD (`git describe
--tags --abbrev=0`), not the newest tag in the repo, so docs-only commits sitting on top
of a release still pass -- the same narrowing `deploy.py`'s staleness guard needed after
its first version over-fired on documentation.

Exit 0 = they agree. Exit 1 = drift, or no tag could be resolved.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "addons" / "RiskGuardAddOn.cs"
PATTERN = re.compile(r'public\s+const\s+string\s+Version\s*=\s*"([^"]+)"')


def main() -> int:
    if not SOURCE.exists():
        print(f"FAIL: {SOURCE.relative_to(REPO)} not found")
        return 1

    m = PATTERN.search(SOURCE.read_text(encoding="utf-8", errors="replace"))
    if not m:
        # Renaming or removing the constant must fail here rather than pass by absence:
        # a check that silently skips when its subject disappears is a vacuous gate, and
        # this repo has shipped several (handover section 8).
        print("FAIL: could not find `public const string Version = \"...\"` in "
              f"{SOURCE.relative_to(REPO)}")
        return 1
    constant = m.group(1)

    proc = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=REPO, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print("FAIL: could not resolve a git tag reachable from HEAD.")
        print("      " + (proc.stderr or "").strip())
        print()
        print("      On a CI runner this usually means a shallow checkout with no tags.")
        print("      Use actions/checkout with `fetch-depth: 0`. Do NOT make this check")
        print("      skip instead -- a gate that passes when it cannot see its subject is")
        print("      worse than no gate.")
        return 1

    tag = proc.stdout.strip()
    normalised = tag[1:] if tag.startswith("v") else tag

    print(f"  constant : {constant}   ({SOURCE.relative_to(REPO)})")
    print(f"  git tag  : {tag}   (newest reachable from HEAD)")

    if constant != normalised:
        print()
        print(f"FAIL: the addon reports {constant} but the deployed release is {tag}.")
        print("      GET /api/riskguard/version is how an operator finds out what is")
        print("      running on a live account, so this is a wrong answer to that")
        print("      question. Bump the constant in the SAME commit as the tag.")
        return 1

    print(f"\nOK: the addon reports the release it is part of ({tag}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
