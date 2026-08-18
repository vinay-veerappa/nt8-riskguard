import io
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

p = "mutation/mutate_p330.py"
raw = io.open(p, "rb").read().decode("utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"
s = raw.replace("\r\n", "\n")

if "EXPECTED SURVIVOR:" in s:
    print("already declared")
    sys.exit(1)

REASON = (
    "EXPECTED SURVIVOR: as of P2-145 (v1.44.0) this mutant is EQUIVALENT and cannot be\n"
    "     killed. The defect it expressed was real: the old inline predicate was\n"
    "     `!isProtected || covered < positionQty`, and on a flat position that is\n"
    "     `covered(0) < positionQty(0)` false OR `!isProtected` TRUE -- so a flat position with\n"
    "     no FSM fired NAKED_POSITION with gap=0, every audit tick. The caller's filter was the\n"
    "     only thing standing between that and the log. `AssessCoverage` now answers\n"
    "     `positionQty <= 0` with `CoverageFinding.None` before anything else, so removing the\n"
    "     caller's filter has no observable effect and no test can distinguish it.\n"
    "     ⚠️ THE COVERAGE MOVED RATHER THAN VANISHING: mutate_p2145coverage.py group 5 mutates\n"
    "     `positionQty <= 0` to `< 0` directly, which is the same defect asked at the place that\n"
    "     now decides it. Do NOT delete the caller's filter -- it is defence in depth and skips\n"
    "     work -- and do not weaken AssessCoverage to make this killable again, which would be\n"
    "     making the code worse to keep a battery green. [[a-gate-evidence-changes-with-shape]]:\n"
    "     restructuring what a gate READS changes what it proves while its own code is untouched.\n"
    "     If this mutant is ever KILLED, `_battery.finish` fails and that is correct -- it means\n"
    "     the totality check went away and this declaration is stale.\n"
    "     ORIGINAL INTENT: "
)

edits = [
    ('    ("the flat-position filter is removed entirely. account.Positions can carry a flat\\n"\n'
     '     "     Position, and a FLAT account then reports NAKED_POSITION on every audit tick",',
     '    ("' + REASON.replace("\n", '\\n"\n     "') + 'the flat-position filter is removed entirely.\\n"\n'
     '     "     account.Positions can carry a flat Position, and a FLAT account then reported\\n"\n'
     '     "     NAKED_POSITION on every audit tick",'),

    ('    ("only the `Quantity <= 0` half of the flat filter is dropped. A reviewer reading the\\n"\n'
     '     "     diff sees a flat filter and moves on",',
     '    ("' + REASON.replace("\n", '\\n"\n     "') + 'only the `Quantity <= 0` half of the flat\\n"\n'
     '     "     filter is dropped. A reviewer reading the diff sees a flat filter and moves on.\\n"\n'
     '     "     Equivalent for the same reason, and by the same single line: MarketPosition.Flat\\n"\n'
     '     "     implies Quantity 0 on NT8, so both halves of that filter collapse to one test",'),
]

for old, new in edits:
    assert s.count(old) == 1, "anchor matched %d times:\n%s" % (s.count(old), old[:120])
    s = s.replace(old, new)

# The header narrative has to agree with the markers, or the file argues with itself.
hdr_old = """  * MUTANT 3 drops the flat-position filter. `account.Positions` can carry a flat
    Position, and without the filter a FLAT account reports NAKED_POSITION on every
    tick of the audit timer. The FSM-seeding sweep has always filtered these; the
    audit did not.

  * MUTANT 4 drops only the `Quantity <= 0` half of that filter, keeping the
    MarketPosition check. A reviewer reading the diff sees a flat filter and moves on."""
hdr_new = """  * MUTANT 3 drops the flat-position filter, and MUTANT 4 drops only its `Quantity <= 0`
    half. ⚠️ BOTH ARE DECLARED `EXPECTED SURVIVOR:` AS OF P2-145 (v1.44.0) and the reason is
    on each marker. In short: the defect they expressed needed the old inline predicate, whose
    `!isProtected` arm fired on a flat position with gap=0; `AssessCoverage` now answers
    `positionQty <= 0` with `None` before anything else, so the caller's filter is no longer
    observable and no test can reach these. The equivalent coverage moved to
    mutate_p2145coverage.py group 5, which mutates that answer at the place that now gives it.
    Neither the filter nor the totality check should be removed to make these killable again."""
assert s.count(hdr_old) == 1, "header anchor %d" % s.count(hdr_old)
s = s.replace(hdr_old, hdr_new)

io.open(p, "wb").write(s.replace("\n", nl).encode("utf-8"))
compile(io.open(p, encoding="utf-8").read(), p, "exec")
print("mutants 3 and 4 declared EXPECTED SURVIVOR; header reconciled; file parses")
