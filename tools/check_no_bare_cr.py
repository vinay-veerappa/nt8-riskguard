"""No tracked file may contain a BARE CR -- a CR that is not part of a CRLF.

WHY THIS IS A GATE AND NOT A STYLE RULE. On 2026-08-19 `addons/RiskGuardModels.cs` was committed
containing two `\\r\\r\\n` sequences. Nothing visible changed: the file compiled, the suite was
3295/0, `git diff` looked normal, and every line still ended in CRLF. But Python opened in TEXT mode
translates `\\r\\r\\n` into TWO newlines, so every mutation battery that reads a source file to snapshot
it and writes it back produced a file 2 lines longer than the one it read:

    ORIGINALS = {p: open(p, encoding='utf-8').read() ...}   # universal newlines: \\r\\r\\n -> \\n\\n
    open(path, 'w', encoding='utf-8', newline='').write(text)

CI's post-battery check compares the tree against HEAD and, finding a difference, reports
`A MUTANT IS LIVE`. Six bins failed that way while EVERY MUTANT IN THEM HAD DIED. The gate that
exists to catch a live mutant fired on a condition that has nothing to do with mutants, and the fix
was two bytes.

⚠️ THAT IS THE REAL COST: a false `A MUTANT IS LIVE` is the most expensive kind of alarm, because the
honest response to it is to distrust the whole run. `--ignore-cr-at-eol` was already on the check and
did not help -- a bare CR is not a CR *at end of line*, it is content.

⚠️ HOW IT GOT THERE, because the idiom is still in use across this repo's tooling. A patch script
detects the target's line ending and re-applies it:

    nl = '\\r\\n' if '\\r\\n' in s else '\\n'
    s = s.replace(old, new.replace('\\n', nl))

If the script's OWN source was saved with CRLF, then a multi-line string literal inside it already
contains `\\r\\n`, and `.replace('\\n', nl)` rewrites that to `\\r\\r\\n`. The bug is invisible in the
script and invisible in the output. The correct idiom normalises FIRST:

    new.replace('\\r\\n', '\\n').replace('\\n', nl)

Exits 1 listing every offending file with a byte offset, so the repair is mechanical.
"""
import subprocess
import sys

# ⚠️ Windows defaults stdout to cp1252, and this gate only prints when it is FAILING -- so without
# this a gate dies exactly when it has something to say, and the traceback reads as a defect in the
# script rather than a finding.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Binary formats legitimately contain bare CR. Everything else in this repo is source or text.
BINARY_SUFFIXES = (
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.dll', '.exe', '.pdb', '.zip',
    '.parquet', '.pyc', '.woff', '.woff2', '.ttf', '.otf',
)


def main():
    listed = subprocess.run(['git', 'ls-files', '-z'], capture_output=True)
    if listed.returncode != 0:
        raise SystemExit('git ls-files failed -- refusing to report a clean tree without reading one')
    paths = [p for p in listed.stdout.decode('utf-8', 'replace').split('\0') if p]
    if not paths:
        raise SystemExit('git ls-files returned NOTHING -- this gate would pass vacuously')

    offenders = []
    inspected = 0
    for path in paths:
        if path.lower().endswith(BINARY_SUFFIXES):
            continue
        try:
            data = open(path, 'rb').read()
        except (OSError, IOError):
            continue
        inspected += 1
        if b'\x00' in data[:8192]:
            continue                      # genuinely binary despite its name
        hits = []
        for i, byte in enumerate(data):
            if byte == 13 and (i + 1 >= len(data) or data[i + 1] != 10):
                hits.append(i)
                if len(hits) >= 5:
                    break
        if hits:
            offenders.append((path, data.count(b'\r\r\n'), len(hits) >= 5, hits))

    if offenders:
        print('FAIL: %d tracked file(s) contain a BARE CR (a CR not followed by LF).' % len(offenders))
        print()
        for path, crcrlf, truncated, hits in offenders:
            where = ', '.join(str(h) for h in hits) + (', ...' if truncated else '')
            print('  * %s' % path)
            print('      %d occurrence(s) of \\r\\r\\n; bare CR at byte offset(s): %s' % (crcrlf, where))
        print()
        print('    A battery that snapshots one of these in TEXT mode writes it back LONGER than it')
        print('    read it, and CI reports A MUTANT IS LIVE for a run in which every mutant died.')
        print('    Repair mechanically:')
        print('      b = open(f, "rb").read()')
        print('      open(f, "wb").write(b.replace(b"\\r\\r\\n", b"\\r\\n"))')
        return 1

    print('OK: %d tracked text file(s) inspected, none contains a bare CR.' % inspected)
    return 0


if __name__ == '__main__':
    sys.exit(main())
