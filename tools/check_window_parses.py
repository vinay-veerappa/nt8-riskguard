"""Parse-check the addon sources the TEST BUILD CANNOT SEE.

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

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Files whose bodies the test build compiles away. Add to this list when another
# `#if !TESTING` file appears.
TARGETS = ['TradeCopierWindow.cs']

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

    work = tempfile.mkdtemp(prefix='nt8parse_')
    try:
        includes = ''
        for t in TARGETS:
            src = os.path.join(REPO, 'addons', t)
            if not os.path.exists(src):
                print('CANNOT RUN: %s is missing. SKIPPED, not passed.' % t)
                return 2
            includes += '    <Compile Include="%s" />\n' % src
        proj = os.path.join(work, 'ParseCheck.csproj')
        with open(proj, 'w', encoding='utf-8') as f:
            f.write(PROJECT % includes)

        r = subprocess.run(['dotnet', 'build', proj, '-v', 'q', '--nologo'],
                           capture_output=True, text=True)
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

        print('OK: %s parse(s) as valid C#.' % ', '.join(TARGETS))
        print('    This is NOT a compile -- type errors are out of scope by design. '
              'Run NT8\'s own compile before calling the window done.')
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
