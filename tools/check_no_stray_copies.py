#!/usr/bin/env python3
"""
check_no_stray_copies.py -- there is exactly one copy of each addon source.

Before the split there were FOUR copies of the same addon drifting against each other,
and one of them (`mcp/ninjatrader-mcp/nt8-addon/McpBridgeAddOn.cs`) turned out to be a
HARDLINK to the file NT8 compiles -- so every deploy silently dirtied an unrelated repo,
and the mirrored copy was 15 hunks behind before anyone noticed. See handover section 5.3a.

This check fails if an AddOn .cs appears anywhere outside addons/, so a fifth copy cannot
be introduced quietly.

tests/ is exempt: the test suite and the NT8 API stubs are .cs files, but they are not
AddOn sources and NT8 never compiles them.

Exit 0 = clean, 1 = a stray copy exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ⚠️ Windows defaults stdout to cp1252. Every gate in this repo prints mutant
# descriptions and plan text full of non-ASCII, and it only needs to print them
# when it is FAILING -- so without this a gate dies exactly when it has something
# to say, and the traceback reads as a defect in the script rather than a finding.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO_ROOT = Path(__file__).resolve().parents[1]
ADDONS = REPO_ROOT / "addons"
EXEMPT_DIRS = {"tests", "obj", "bin", ".git"}


def main() -> int:
    owned = set(p.name for p in ADDONS.glob("*.cs"))
    if not owned:
        print("FAIL: addons/ contains no .cs files at all -- is this the right repo?")
        return 1

    strays = []
    for path in REPO_ROOT.rglob("*.cs"):
        rel = path.relative_to(REPO_ROOT)
        if rel.parts[0] in EXEMPT_DIRS or rel.parts[0] == "addons":
            continue
        strays.append(rel)

    duplicates = [rel for rel in strays if rel.name in owned]

    if duplicates:
        print("STRAY COPY: an addon source exists outside addons/.")
        for rel in duplicates:
            print("  {0}".format(rel.as_posix()))
        print()
        print("addons/ is the only real copy. A second one drifts, and the one that drifts")
        print("is the one nobody is testing.")
        return 1

    if strays:
        print("OK: no duplicate addon sources. Unrelated .cs outside addons/ (informational):")
        for rel in strays:
            print("  {0}".format(rel.as_posix()))
        return 0

    print("OK: {0} addon source(s), no copies outside addons/.".format(len(owned)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
