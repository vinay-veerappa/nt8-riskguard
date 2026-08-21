"""Mutation battery for F-6: the push-alert sink's decision half.

⚠️ THE FAILURE THIS FEATURE HAS TO SURVIVE IS VOLUME, NOT SILENCE.

A sink that forwards every audited event does not produce an alerted operator, it produces a
MUTED CHANNEL -- and a muted channel looks exactly like coverage. That is strictly worse than
having no alerts, because the operator believes they would be told. This repo has hit "an alarm
that is always on is off" seven times (P3-30's audit, P2-98's FILL_NOT_MEASURED, P2-101's
LOCKOUT_STUCK, P2-107's whole class, P2-108's NAKED_POSITION at 10s intervals); F-6 is the first
component whose entire job is to stand between that stream and a phone.

So the mutants split into two families, and the second is the one that matters:

  * The LOUD mutants (1, 2, 6, 7) restore the flood in various shapes. These are easy to kill --
    any count-based assertion catches them.

  * The QUIET mutants (3, 4, 5, 8) make the sink send LESS. Every one of them passes every
    "the repeat was suppressed" test in the file, because suppression is exactly what those
    tests assert. A budget that never refills, a floor that refuses everything, a severity
    table that classifies nothing as reportable -- all of them look like a working filter from
    the inside and deliver nothing. They are killable ONLY by the negative controls, which is
    why half the F-6 tests are negative controls. P3-30 shipped a detector behind three
    positive-only acceptance tests that matched nothing at all.

  * MUTANT 9 is the honesty one. `shadow` does not act (P2-92), so an alert whose title omits
    [WOULD] tells the operator their account was flattened when it was not -- on a phone, at
    3am, to someone who cannot check. P1-105's lesson delivered by push notification.

  * MUTANT 10 is the credential one. This addon echoes its config over HTTP on :7890, so a
    webhook URL that is not redacted is a webhook URL published. A secret the feature itself
    introduces must not leave by the door the feature opened.

  * MUTANT 11 removes the reason from a refusal. The operator's real question is never "did it
    send" but "why was I not told", and a silent drop cannot answer it.
"""
import os
import re
import subprocess
import sys

# P2-114: the battery's OWN stdout. A non-ASCII character in a mutant DESCRIPTION raises
# UnicodeEncodeError inside print() on a cp1252 console -- and it raises BETWEEN applying a
# mutant and restoring it, which leaves a LIVE MUTANT in the source tree.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import _battery


REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SINK = os.path.join(REPO, 'addons', 'GuardAlertSink.cs')

# (description, target file, find, replace)
MUTANTS = [
    ("LOUD: the budget is removed, so every evaluation of an unresolved condition pushes again --\n"
     "     the measured P2-108 stream (180 NAKED_POSITION lines) arrives as 180 notifications",
     SINK,
     '            if (already >= budget)',
     '            if (false)'),

    ("LOUD: the warning budget becomes the critical one, so a 10-second repeating condition\n"
     "     sends three times instead of once. The partial fix -- the flood is bounded and still\n"
     "     triples every routine warning",
     SINK,
     '            return RankOf(severity) >= 2 ? 3 : 1;',
     '            return 3;'),

    ("QUIET: the budget never refills, because NoteResolved stops clearing. Every suppression\n"
     "     test still passes -- suppression is what they assert -- and the guard goes permanently\n"
     "     silent about a rule after its first episode. The FIRST daily-loss breach of the week is\n"
     "     the only one the operator is ever told about, including the one three days later",
     SINK,
     '            _sent.Remove(KeyOf(account, eventType));',
     '            { }'),

    ("QUIET and the worst of them: the budget is zero, so NOTHING is ever pushed. A channel that\n"
     "     is configured, enabled, reports no errors, and is silent -- indistinguishable from a\n"
     "     calm trading day",
     SINK,
     '            return RankOf(severity) >= 2 ? 3 : 1;',
     '            return 0;'),

    ("QUIET: every event classifies as info, so with the shipped 'warning' floor the sink refuses\n"
     "     everything. The severity table looks populated and is consulted; it just never agrees\n"
     "     that anything matters",
     SINK,
     '                if (string.Equals(e, eventType, StringComparison.OrdinalIgnoreCase)) return "critical";',
     '                if (false) return "critical";'),

    ("LOUD and fail-DANGEROUS in the other direction: an unknown event type defaults to critical,\n"
     "     so every event type added next Tuesday pages the operator until someone classifies it.\n"
     "     Reads as fail-safe; mutes the channel within a week and the muting is invisible",
     SINK,
     '            return "info";\n        }\n\n        private static int RankOf',
     '            return "critical";\n        }\n\n        private static int RankOf'),

    ("LOUD: the budget scope drops the EVENT TYPE, so one condition's budget silences every other\n"
     "     condition on that account -- and inversely, resolving any one of them refills all of\n"
     "     them. P2-107's mutant 6 at a new surface; passes every single-event-type test",
     SINK,
     '            return (account ?? "(null)") + "\\u001F" + (eventType ?? "(null)");',
     '            return (account ?? "(null)");'),

    ("LOUD: the budget scope drops the ACCOUNT, so 96 accounts share one budget. Account 1's\n"
     "     breach silences the other 95, and every single-account test passes",
     SINK,
     '            return (account ?? "(null)") + "\\u001F" + (eventType ?? "(null)");',
     '            return (eventType ?? "(null)");'),

    ("THE HONESTY ONE: the [WOULD] marker is dropped, so a shadow alert claims the guard acted.\n"
     "     P2-92 made shadow observation-only; this tells the operator their account was flattened\n"
     "     when nothing was. Delivered to a phone, to someone who cannot check",
     SINK,
     '            if (!IsActing(mode) || !isArmed) sb.Append("[WOULD] ");',
     '            if (false) sb.Append("[WOULD] ");'),

    ("THE CREDENTIAL ONE: Redact returns the URL. This addon publishes its config over HTTP on\n"
     "     :7890, so the webhook secret leaves by the door this feature opened",
     SINK,
     '            string tail = trimmed.Length >= 4 ? trimmed.Substring(trimmed.Length - 4) : "";\n'
     '            return host + "/***" + tail;',
     '            return trimmed;'),

    # ⚠️ THIS MUTANT WAS REWRITTEN. Its first version spliced the assignment into
    # `var unused = (...` and produced UNBALANCED PARENS, so it died of BUILD FAILED -- it never
    # expressed the defect it names, and no test could have been missing. Third instance of
    # P1-99's lesson in this codebase: a mutant's VERDICT is only evidence once you have read
    # what the mutant actually does. This version compiles and states the defect exactly.
    ("a refusal stops carrying its reason. The operator's question is never 'did it send' but\n"
     "     'why was I not told', and a silent drop cannot answer it",
     SINK,
     '                d.Reason = "budget spent: " + already + " of " + budget + " alert(s) already sent "\n'
     '                         + "for " + eventType + " on " + account + ", and the condition has not "\n'
     '                         + "resolved. Suppressing rather than repeating -- see interventions.jsonl "\n'
     '                         + "for every occurrence.";',
     '                d.Reason = null;'),
]


def run():
    build = subprocess.run(
        ['dotnet', 'build', 'RiskGuardTests.csproj', '-v', 'q', '--nologo'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
        encoding='utf-8', errors='replace')
    if build.returncode != 0:
        return 'BUILD FAILED'
    res = subprocess.run(
        ['dotnet', 'run', '--project', 'RiskGuardTests.csproj', '--no-build'],
        cwd=os.path.join(REPO, 'tests'), capture_output=True, text=True,
        encoding='utf-8', errors='replace')
    m = re.search(r'Passed = \d+, Failed = \d+', res.stdout)
    # P2-148: a crash is NOT a detection. The harness prints its result line
    # last, so an unhandled exception leaves none -- which every spelling of
    # `killed` below scored as KILLED. Require at least one [FAIL] first.
    if not m and '[FAIL]' not in ((res.stdout or '') + (res.stderr or '')):
        return 'NO RESULT LINE + NO ASSERTION FAILED (harness died undetected)'
    return m.group(0) if m else 'NO RESULT LINE'


# ⚠️ NO newline='' ON THE READ. mutate_p2112.py scored 9/9 locally and 2/9 in CI for exactly
# that: the working tree had been normalised to LF by earlier runs while every blob is CRLF, so
# the battery's own '\n' anchors matched locally and matched nothing on a fresh checkout.
ORIGINALS = {path: open(path, encoding='utf-8').read() for path in (SINK,)}


def restore():
    for path, text in ORIGINALS.items():
        open(path, 'w', encoding='utf-8', newline='').write(text)


print('=== baseline ===')
baseline = run()
print(' ', baseline)

m = re.search(r'Passed = (\d+), Failed = (\d+)', baseline)
if not m:
    print('\nREFUSING TO RUN: could not read a result line from the baseline.')
    sys.exit(2)
if int(m.group(2)) != 0:
    print('\nREFUSING TO RUN: baseline is RED (%s failing). Every mutant would score KILLED '
          'on pre-existing failures and this battery would prove nothing.' % m.group(2))
    sys.exit(2)

survivors = []
for name, path, old, new in MUTANTS:
    original = ORIGINALS[path]
    if original.count(old) != 1:
        print('  [SKIP] %s: anchor matched %d times' % (name, original.count(old)))
        survivors.append(name + ' (ANCHOR)')
        continue
    open(path, 'w', encoding='utf-8', newline='').write(original.replace(old, new))
    res = run()
    killed = _battery.score(res, run)
    print('  [%s] %s: %s' % ('KILLED' if killed else 'SURVIVED', name, res))
    if not killed:
        survivors.append(name)
    restore()

restore()
print('\nrestored originals;', run())

# The plain exit, not _battery.finish: this battery declares NO expected survivor, and
# check_expected_survivors.py requires the plain form in that case.
if survivors:
    print('\nSURVIVORS (%d):' % len(survivors))
    for s in survivors:
        print('  * ' + s)
    print('\n  No test can tell these mutants from the real code. Write one, or declare the\n'
          '  mutant EXPECTED SURVIVOR: with the reason no test can reach it.')
else:
    print('\nSURVIVORS: none -- all %d mutants died.' % len(MUTANTS))
sys.exit(1 if survivors else 0)
