"""Verify a ticket's expect_green strings against the suite's ACTUAL failure lines.

This exists because UI1 lost a whole loop run to ONE string: the ticket said
"after one latency is actually recorded" and the test said "after one measured
fill". Comparing them by eye is how that happened; a set difference cannot make
that mistake.

Usage: python agent/_check_expect_green.py agent/tickets_ui_config.json [TICKET_ID]
Exits non-zero if either direction is non-empty.
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def suite_failures():
    tests = os.path.join(REPO, "tests")
    subprocess.run(["dotnet", "build", "RiskGuardTests.csproj", "-v", "q", "--nologo"],
                   cwd=tests, capture_output=True, text=True)
    r = subprocess.run(["dotnet", "run", "--project", "RiskGuardTests.csproj", "--no-build"],
                       cwd=tests, capture_output=True, text=True)
    out = set()
    for line in r.stdout.splitlines():
        m = re.match(r"\s*\[FAIL\]\s*(.*)$", line)
        if m:
            out.add(m.group(1).strip())
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "agent/tickets_ui_config.json"
    wanted_id = sys.argv[2] if len(sys.argv) > 2 else None
    doc = json.load(open(os.path.join(REPO, path), encoding="utf-8"))

    fails = suite_failures()
    bad = False
    for t in doc["tickets"]:
        if wanted_id and t["id"] != wanted_id:
            continue
        eg = set(t["expect_green"])
        missing = sorted(eg - fails)
        extra = sorted(fails - eg)
        print("ticket %s: %d expect_green, %d suite failures, %d matched"
              % (t["id"], len(eg), len(fails), len(eg & fails)))
        # A string that is NOT failing right now can never go red-then-green, so
        # the test-first gate is VACUOUS for it -- the run passes without the
        # implementation having done anything.
        for s in missing:
            print("  [NOT RED] expect_green string matches no current failure: %r" % s)
            bad = True
        # A failure nobody claimed means either a forgotten acceptance criterion
        # or a test that was already broken before this ticket.
        for s in extra:
            print("  [UNCLAIMED] failing but absent from expect_green: %r" % s)
            bad = True
        if not missing and not extra:
            print("  OK -- expect_green is exactly the set of current failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
