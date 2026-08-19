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


def names_match(name, failure):
    """The SAME rule agent_loop.gates uses -- whole-identifier, not substring.

    ⚠️ This started life as exact set equality, which is a DIFFERENT test from the
    one the loop applies, so this helper could pass a ticket the loop refuses and
    refuse one the loop accepts. A checker that models something other than the gate
    it is checking is the thing this repo keeps catching (handover §5.0). The loop
    matches an expect_green string ANYWHERE inside a failure line, on word
    boundaries, which is what lets an assertion carry a trailing "(got 3, expected 4)"
    without the ticket having to predict the numbers.
    """
    return re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", failure, re.IGNORECASE) is not None


def suite_failures():
    tests = os.path.join(REPO, "tests")
    # ⚠️ ENCODING PINNED. `text=True` alone decodes with the platform default, which is
    # cp1252 here, and the suite prints the arrows and warning glyphs its own test names
    # carry. The reader thread then raised UnicodeDecodeError, `r.stdout` came back None,
    # and this checker died with an AttributeError -- so THE GATE COULD NOT RUN AT ALL,
    # which is how a ticket reaches the loop with unverified expect_green strings. Same
    # class the mutation batteries pin against. [[a-battery-must-reach-its-restore-line]].
    subprocess.run(["dotnet", "build", "RiskGuardTests.csproj", "-v", "q", "--nologo"],
                   cwd=tests, capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
    r = subprocess.run(["dotnet", "run", "--project", "RiskGuardTests.csproj", "--no-build"],
                       cwd=tests, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.stdout is None:
        raise SystemExit("the suite produced no stdout -- refusing to report an empty failure set")
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
        missing = sorted(s for s in eg if not any(names_match(s, f) for f in fails))
        extra = sorted(f for f in fails if not any(names_match(s, f) for s in eg))
        matched = len(eg) - len(missing)
        print("ticket %s: %d expect_green, %d suite failures, %d matched"
              % (t["id"], len(eg), len(fails), matched))
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
