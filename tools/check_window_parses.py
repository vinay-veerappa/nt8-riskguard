"""Parse-check EVERY addon source -- especially the parts the test build cannot see.

(It checked exactly one file until 2026-08-16, under a name and a docstring that
read as though it checked the class. See `targets()` for what that cost.)

WHAT THIS IS FOR. `RiskGuardTests.csproj` defines `TESTING`, and
`TradeCopierWindow.cs` is one 1100-line `#if !TESTING` block. So `dotnet build`
compiles it to NOTHING: a stray brace, an unterminated string or a missing
semicolon in that file passes every gate this repo has, and is first reported by
NinjaTrader's own compiler -- at which point a compile error in ANY addon `.cs`
stops EVERY addon loading, RiskGuard included. That is why `P1-72`..`P1-75` could
only be compile-checked by deploying.

WHAT THIS IS NOT. It is a PARSER check, not a compile. It reports only CS1xxx
diagnostics -- the ones the lexer and parser raise -- and deliberately ignores
CS0xxx, which are binder errors about types this project does not reference
(`AddOnBase`, `NTMenuItem`, `Brushes`, ...). So it answers "is this file
syntactically valid C#?" and NOT "does it type-check?".

  ⚠️ A PASS HERE IS NOT A COMPILE. NT8's own compile is still required before the
  window is called done, and nothing in this script substitutes for it.

Bounding what a check proves is the point. The alternative attempted first --
referencing NinjaTrader's real assemblies to do a full compile -- pulled in
`NinjaTrader.Custom.dll`, which already CONTAINS a compiled copy of these same
sources, so every type resolved twice and the errors were about the harness
rather than the code. A check whose failures are its own artefacts is worse than
a narrower check that means exactly what it says.

Exit codes: 0 clean, 1 syntax errors found, 2 could not run (no SDK).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ⚠️ Windows defaults stdout to cp1252. Every gate in this repo prints mutant
# descriptions and plan text full of non-ASCII, and it only needs to print them
# when it is FAILING -- so without this a gate dies exactly when it has something
# to say, and the traceback reads as a defect in the script rather than a finding.
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def targets():
    """Every addon source, in the same way deploy ships them.

    ⚠️ THIS WAS A HAND-TYPED LIST OF ONE, AND IT HAD DRIFTED. It read
    `TARGETS = ['TradeCopierWindow.cs']` with a comment saying "add to this list
    when another `#if !TESTING` file appears". One did: `P2-29` split the WPF
    dashboard out into `RiskGuardWindow.cs`, nobody came back here, and this
    script printed `OK: TradeCopierWindow.cs parse(s) as valid C#` -- true, and
    read as a verdict on a file it had never opened. FIVE addon sources contain
    `#if !TESTING` regions today; it was checking one.

    That is the fourth hand-typed inventory in this project to drift, after
    `BridgeTests.csproj`'s eight files, `check_bridge_parses.py`'s two of six,
    and `sync_nt8_strategies.py`'s flat `Indicators/`. All four had a comment
    telling the next person to maintain them, and the comment is what failed.

    Globbing everything rather than the `#if !TESTING` subset is deliberate:
    "which files can the test build not see" is a judgement that goes stale the
    same way, and this is a SYNTAX check, so running it over a file that does
    compile costs a second and cannot produce a false finding. The region is now
    the one that matters -- what NinjaTrader compiles, where one bad brace stops
    every addon loading.
    """
    names = sorted(f for f in os.listdir(os.path.join(REPO, 'addons'))
                   if f.endswith('.cs'))
    if not names:
        raise RuntimeError('no addon sources found under addons/')
    return names

PROJECT = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <OutputType>Library</OutputType>
    <EnableDefaultItems>false</EnableDefaultItems>
    <LangVersion>latest</LangVersion>
    <NoWarn>$(NoWarn);CS0169;CS0414;CS0649</NoWarn>
  </PropertyGroup>
  <ItemGroup>
%s  </ItemGroup>
</Project>
"""


def main():
    if shutil.which('dotnet') is None:
        print('CANNOT RUN: no dotnet SDK on PATH. This check is being SKIPPED, not passed.')
        return 2

    try:
        target_files = targets()
    except RuntimeError as exc:
        print('CANNOT RUN: %s. SKIPPED, not passed.' % exc)
        return 2

    work = tempfile.mkdtemp(prefix='nt8parse_')
    try:
        includes = ''
        for t in target_files:
            src = os.path.join(REPO, 'addons', t)
            if not os.path.exists(src):
                print('CANNOT RUN: %s is missing. SKIPPED, not passed.' % t)
                return 2
            includes += '    <Compile Include="%s" />\n' % src
        proj = os.path.join(work, 'ParseCheck.csproj')
        with open(proj, 'w', encoding='utf-8') as f:
            f.write(PROJECT % includes)

        # ⚠️ encoding pinned. `text=True` alone decodes as cp1252 on Windows, and one
        # non-ASCII byte in a build line kills the reader thread -- which surfaces as
        # empty output and scores as a PASS here, because `syntax` would be empty. Same
        # hazard `check_batteries_pin_encoding.py` exists for, one directory over; that
        # gate reads mutation/, so nothing was watching this file.
        r = subprocess.run(['dotnet', 'build', proj, '-v', 'q', '--nologo'],
                           capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        # CS1xxx == lexer/parser. CS0xxx == binder, i.e. the types we deliberately
        # did not reference, which is expected and not a finding.
        syntax = sorted(set(
            line.strip() for line in (r.stdout + r.stderr).splitlines()
            if re.search(r'error CS1\d{3}:', line)))

        for line in syntax:
            print('  [SYNTAX] %s' % line)

        if syntax:
            print('\n%d syntax error(s) in code the test build compiles away. '
                  'NT8 would refuse the WHOLE Custom assembly for these, which stops '
                  'every addon loading -- RiskGuard included.' % len(syntax))
            return 1

        print('OK: %d addon source(s) parse as valid C#: %s'
              % (len(target_files), ', '.join(target_files)))
        print('    This is NOT a compile -- type errors are out of scope by design. '
              'Run NT8\'s own compile before calling the window done.')
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
