"""Turn a CI run's `BATTERY_SECONDS` lines into the TSV pack_ci_matrix.py reads.

The mutation step already prints, per battery:

    BATTERY_SECONDS mutate_p2136survive.py 626

so exact per-battery wall times are in every run's log. `gh run view --json jobs` only gives
per-JOB durations, and a job holds several batteries, so those cannot be packed -- reach for
this instead.

⚠️ DO NOT DERIVE THESE FROM TIMESTAMPS. Session 59 bracketed each battery between successive
`=== baseline ===` lines and produced a plausible-looking table in which 18 of 45 batteries
came out at ~1s. It was only obvious because a battery that runs the whole suite per mutant
cannot take a second; a subtler error would have packed the matrix on wrong weights, and
pack_ci_matrix.py's own docstring warns that such a plan "comes out looking balanced and is
not". The printed line is the measurement; anything else is a reconstruction of it.

Usage:
    gh run view <run-id> --log | grep -ao "BATTERY_SECONDS [^ ]* [0-9]*" | sort -u > secs.txt
    python tools/make_run_times.py secs.txt > run_times.tsv
    python tools/pack_ci_matrix.py --times run_times.tsv --bins 19
"""
import datetime as dt
import io
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
ENTRY = re.compile(r"\{\s*label:\s*\"(.+?)\"\s*,\s*batter(?:y|ies):\s*\"(.+?)\"\s*\}")

# filename -> the label piece pack_ci_matrix keys on. Built from ci.yml so the two naming
# schemes (mutate_p1_76.py vs "P1-76", mutate_f6.py vs "F-6") never need a second table.
fname_to_label = {}
for label, bats in ENTRY.findall(io.open(WORKFLOW, encoding="utf-8").read()):
    pieces = [p.strip() for p in label.split("+")]
    files = bats.split()
    if len(pieces) != len(files):
        print("REFUSING: bin %r has %d label pieces and %d batteries; the mapping would be a "
              "guess." % (label, len(pieces), len(files)), file=sys.stderr)
        sys.exit(2)
    for p, f in zip(pieces, files):
        fname_to_label[f] = p

secs = {}
for ln in io.open(sys.argv[1], encoding="utf-8", errors="replace"):
    m = re.search(r"BATTERY_SECONDS\s+(\S+)\s+(\d+)", ln)
    if m:
        secs[m.group(1)] = int(m.group(2))

missing = sorted(set(fname_to_label) - set(secs))
if missing:
    print("REFUSING: no BATTERY_SECONDS line for: %s. Packing on partial weights is how a bin "
          "ends up carrying two heavy batteries." % ", ".join(missing), file=sys.stderr)
    sys.exit(2)

# read_times() wants `name<TAB>startedAt<TAB>completedAt` and only uses the delta.
base = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
for f, n in sorted(secs.items(), key=lambda kv: -kv[1]):
    lbl = fname_to_label.get(f)
    if lbl is None:
        continue
    e = base + dt.timedelta(seconds=n)
    print("%s\t%s\t%s" % (lbl, base.isoformat().replace("+00:00", "Z"),
                          e.isoformat().replace("+00:00", "Z")))

print("%d batteries, total %ds (%.1f min) of battery compute"
      % (len(secs), sum(secs.values()), sum(secs.values()) / 60.0), file=sys.stderr)
