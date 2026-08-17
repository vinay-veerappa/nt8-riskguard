#!/usr/bin/env python3
"""
check_direction.py -- enforce the one-way dependency rule.

nt8-mcp-bridge depends on this repo; this repo must never depend on the bridge.
If that inverts, the two repos are mutually recursive and the split is dead
(docs/NT8_REPO_SPLIT_PLAN.md section 1).

Comments are stripped before checking, deliberately. Four places in addons/ explain
in prose WHY a piece of code lives here rather than in the bridge -- for example that
McpBridgeAddOn.cs is excluded from the test build, so testable logic has to sit on
this side. That reasoning is the most useful thing in those files and a check that
forbids naming the bridge would get it deleted rather than obeyed.

Exit 0 = clean, 1 = violation.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
ADDONS = REPO_ROOT / "addons"

# Types owned by nt8-mcp-bridge. Naming one in executable code inverts the dependency.
FORBIDDEN = ("McpBridgeAddOn",)

BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"')


def strip_comments(text: str) -> str:
    """Remove block comments, line comments, and string literals.

    String literals go too: a log message that happens to mention the bridge by name
    is prose, not a dependency.
    """
    text = BLOCK_COMMENT.sub("", text)
    text = STRING_LITERAL.sub('""', text)
    out = []
    for line in text.split("\n"):
        idx = line.find("//")
        out.append(line[:idx] if idx >= 0 else line)
    return "\n".join(out)


def main() -> int:
    violations = []
    for path in sorted(ADDONS.glob("*.cs")):
        code = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        for lineno, line in enumerate(code.split("\n"), start=1):
            for name in FORBIDDEN:
                if name in line:
                    violations.append((path.name, lineno, name, line.strip()))

    if violations:
        print("DIRECTION VIOLATION: this repo must not depend on nt8-mcp-bridge.")
        for filename, lineno, name, text in violations:
            print("  {0}:{1}  names {2}".format(filename, lineno, name))
            print("      {0}".format(text[:120]))
        print()
        print("The bridge depends on the core, never the reverse. Move the code that needs")
        print("the bridge into the bridge, or give the core a seam the bridge calls into.")
        return 1

    print("OK: no addon source names a bridge-owned type ({0} files checked).".format(
        len(list(ADDONS.glob("*.cs")))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
