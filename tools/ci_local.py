"""Run the whole CI suite locally, in parallel, on this box.

WHY. GitHub-hosted `windows-latest` gives 20 ACCOUNT-WIDE job slots shared with the sibling repo,
so this repo's 19 bins + `checks` saturate the account on its own and the sibling queues behind it.
This box has 24 cores and measured **2.4x faster per mutant** than a hosted runner (8.07s vs
~19.6s for one rebuild-and-run of the ~3400-test suite, 2026-08-20).

⚠️ THIS DOES NOT REPLACE GITHUB ACTIONS, AND DELIBERATELY SO. A local pass proves the tree you have
is good; only CI proves the commit you PUSHED was checked, and nothing here runs on a commit you
forgot to run it on. Both, not either.

⚠️ AND SELF-HOSTED GITHUB RUNNERS WERE REJECTED ON PURPOSE. Both repos are PUBLIC and the workflow
triggers on `pull_request`, so a self-hosted runner would let any fork's PR execute arbitrary code
on the machine running NinjaTrader against a funded account. GitHub's own documentation advises
against exactly that pairing. This script has no network surface at all.

HOW THE ISOLATION WORKS, and it is the whole design:

  ⚠️ A MUTATION BATTERY OWNS ITS SOURCE TREE FOR THE LENGTH OF ITS RUN. It writes a mutant into the
  real file, runs the suite, and restores. Two batteries in one tree interleave and corrupt each
  other -- one takes the other's mutant as its `originals` snapshot and writes it back in its own
  `finally`, leaving a live mutant behind a green suite. That has happened here twice.
  [[mutation-battery-killed-leaves-a-mutant]]

  So each worker gets its OWN `git worktree`. A battery can only ever see its own checkout, and a
  worker that dies mid-mutant leaves the damage inside a directory this script then deletes --
  which makes the leftover-mutant hazard structurally impossible rather than merely unlikely.

  ⚠️ It also means a gate can safely run in the main tree WHILE batteries run, which is otherwise
  forbidden: a gate reading source with a mutant applied reports a FALSE RED, and a false red is
  the one you act on. [[a-killed-mutation-battery-leaves-a-mutant]]

WHAT IT TESTS. `HEAD`, not your working tree, because that is what you are about to push. If the
tree is dirty it says so loudly and names the files; `--include-uncommitted` copies modified
tracked files into each worktree instead, for the iterate-before-committing case.
"""
import argparse
import ast
import concurrent.futures
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKTREE_ROOT = os.path.join(REPO, '.ci-local')
PRINT_LOCK = threading.Lock()


def say(*parts):
    with PRINT_LOCK:
        print(*parts, flush=True)


def run(cmd, cwd=REPO, timeout=1800, env=None):
    full_env = None
    if env:
        full_env = dict(os.environ)
        full_env.update(env)
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=timeout, env=full_env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# P1-179. Batteries run with the double-kill armed HERE and nowhere else: an apparent kill is
# re-verified once and must reproduce, so a suite that goes red from cross-worktree contention
# (the hazard the comment in worker() describes) scores a SURVIVOR rather than a silent free kill.
# GitHub CI never sets this -- one bin per runner cannot contend -- so its scoring is unchanged.
BATTERY_ENV = {'RG_DOUBLE_KILL': '1'}


def mutant_count(path):
    """Number of entries in the battery's MUTANTS list, WITHOUT executing it.

    Used only to order the queue longest-first, which shortens the tail. Parsed rather than
    imported because importing a battery RUNS it -- it would start mutating this very tree.
    """
    try:
        tree = ast.parse(open(path, encoding='utf-8', errors='replace').read())
    except Exception:
        return 1
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == 'MUTANTS':
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        return max(1, len(node.value.elts))
    return 1


def dirty_files():
    _, out = run(['git', 'status', '--porcelain'])
    return [l[3:].strip() for l in out.splitlines() if l.strip()]


def make_worktrees(n, include_uncommitted):
    if os.path.isdir(WORKTREE_ROOT):
        run(['git', 'worktree', 'prune'])
        shutil.rmtree(WORKTREE_ROOT, ignore_errors=True)
    os.makedirs(WORKTREE_ROOT, exist_ok=True)
    paths = []
    modified = [f for f in dirty_files() if os.path.isfile(os.path.join(REPO, f))]
    for i in range(n):
        wt = os.path.join(WORKTREE_ROOT, 'w%d' % i)
        rc, out = run(['git', 'worktree', 'add', '--detach', wt, 'HEAD'])
        if rc != 0:
            say('  worktree %d FAILED: %s' % (i, out.strip()[:300]))
            return paths
        if include_uncommitted:
            for f in modified:
                src = os.path.join(REPO, f)
                dst = os.path.join(wt, f)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        paths.append(wt)
    return paths


def drop_worktrees():
    for name in sorted(os.listdir(WORKTREE_ROOT)) if os.path.isdir(WORKTREE_ROOT) else []:
        run(['git', 'worktree', 'remove', '--force', os.path.join(WORKTREE_ROOT, name)])
    run(['git', 'worktree', 'prune'])
    shutil.rmtree(WORKTREE_ROOT, ignore_errors=True)


def phase_gates():
    """Every gate script, plus the anchor check. Fast, and safe to run beside the batteries
    because they mutate worktrees and these read the main tree."""
    scripts = sorted(
        [os.path.join('tools', f) for f in os.listdir(os.path.join(REPO, 'tools'))
         if f.startswith('check_') and f.endswith('.py')]
        + [os.path.join('mutation', 'check_anchors.py')])
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(run, [sys.executable, s]): s for s in scripts}
        for fut in concurrent.futures.as_completed(futs):
            s = futs[fut]
            rc, out = fut.result()
            results.append((s, rc, out))
            say('  [%s] %s' % ('ok  ' if rc == 0 else 'FAIL', s))
    return results


def phase_suite():
    rc, out = run(['dotnet', 'build', 'tests/RiskGuardTests.csproj', '--nologo', '-v', 'q'])
    if 'error CS' in out or rc != 0:
        say('  [FAIL] build')
        return False, out
    # ⚠️ `dotnet run --no-build` after a FAILED build runs the PREVIOUS assembly and prints a green
    # RESULTS line, so the build result is checked first and separately. Same reason CI does.
    rc, out = run(['dotnet', 'run', '--project', 'tests/RiskGuardTests.csproj',
                   '--no-build', '--nologo', '-v', 'q'])
    import re
    m = re.search(r'Passed = (\d+), Failed = (\d+)', out)
    if not m:
        say('  [FAIL] suite produced NO RESULT LINE')
        return False, out
    ok = int(m.group(2)) == 0
    say('  [%s] suite %s' % ('ok  ' if ok else 'FAIL', m.group(0)))
    return ok, out


def worker(wt, work, results, log_dir):
    while True:
        try:
            battery = work.get_nowait()
        except queue.Empty:
            return
        started = time.time()
        rc, out = run([sys.executable, os.path.join('mutation', battery)], cwd=wt, env=BATTERY_ENV)

        # ⚠️ A RED BASELINE IS NOT A MUTATION FINDING, AND UNDER LOAD IT IS USUALLY A FLAKE.
        # Measured 2026-08-20 while building this: six suites run concurrently in six SEPARATE
        # worktrees produced 0, 1, 1, 2, 2 and 3 failures out of 3434 assertions, non-deterministic
        # and never the same set. Alone, every one of those worktrees is 3434/0. So the suite has
        # load-sensitive tests -- a pre-existing property this tool EXPOSED rather than caused, and
        # filed as its own entry.
        #
        # Two consequences, and the second is the dangerous one:
        #   * a flake aborts a battery at its baseline, which merely wastes the run;
        #   * a flake DURING a mutant scores that mutant KILLED, because every battery reads
        #     `Failed > 0` as a detection. That direction is silent and it inflates the score.
        # Retrying the whole battery once on a red baseline costs one run and removes the first;
        # the second is why `--jobs` defaults low rather than to the core count.
        # ⚠️ P1-179 now closes the second (silent, inflating) direction directly: batteries run with
        # RG_DOUBLE_KILL, so a flake DURING a mutant no longer scores a free kill -- the re-run does
        # not reproduce it and it is scored a SURVIVOR. This retry stays as belt-and-suspenders for
        # the baseline case, which the double-kill does not cover (a red baseline aborts before any
        # mutant is scored).
        if rc != 0 and 'baseline is RED' in out:
            say('  [retry] %-28s red baseline, likely a load flake' % battery)
            rc, out = run([sys.executable, os.path.join('mutation', battery)], cwd=wt, env=BATTERY_ENV)
        secs = time.time() - started
        with open(os.path.join(log_dir, battery + '.log'), 'w',
                  encoding='utf-8', errors='replace') as f:
            f.write(out)
        results.append((battery, rc, secs, out))
        say('  [%s] %-28s %5.0fs' % ('ok  ' if rc == 0 else 'FAIL', battery, secs))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--jobs', type=int, default=0,
                    # argparse formats this string, so a literal percent must be doubled --
                    # '%TEMP%' raises "badly formed help string" at import time, which is a
                    # crash on --help rather than anything the tests would catch.
                    help='parallel worktrees; default is cores//2 capped at 12. Raised back to '
                         'this once P1-175 was fixed -- the fixed %%TEMP%% filenames that made '
                         'the suite load-sensitive are gone, and 12 concurrent runs measured '
                         '3434/0 twice over. The baseline retry is kept as cheap insurance, not '
                         'because a known cause remains.')
    ap.add_argument('--include-uncommitted', action='store_true',
                    help='copy modified tracked files into each worktree instead of testing HEAD')
    ap.add_argument('--keep', action='store_true', help='leave the worktrees for inspection')
    ap.add_argument('--only', choices=['gates', 'suite', 'batteries'], action='append',
                    help='run only these phases (repeatable)')
    args = ap.parse_args()

    phases = set(args.only or ['gates', 'suite', 'batteries'])
    jobs = args.jobs or min(12, max(1, (os.cpu_count() or 4) // 2))
    t0 = time.time()

    dirty = dirty_files()
    print('=' * 72)
    print('LOCAL CI  --  %d worker(s), testing %s'
          % (jobs, 'YOUR WORKING TREE' if args.include_uncommitted else 'HEAD'))
    if dirty:
        # Loud, because the difference between "the tree I have" and "the commit I am about to
        # push" is exactly the gap a local run is supposed to close.
        print('⚠️  %d uncommitted change(s); %s'
              % (len(dirty),
                 'they ARE included' if args.include_uncommitted
                 else 'they are NOT tested (pass --include-uncommitted)'))
        for f in dirty[:10]:
            print('      %s' % f)
    print('=' * 72)

    failures = []

    if 'gates' in phases:
        print('\n-- gates --')
        for s, rc, out in phase_gates():
            if rc != 0:
                failures.append(('gate ' + s, out))

    if 'suite' in phases:
        print('\n-- build + suite --')
        ok, out = phase_suite()
        if not ok:
            failures.append(('suite', out))

    if 'batteries' in phases:
        batteries = sorted(
            f for f in os.listdir(os.path.join(REPO, 'mutation'))
            if f.startswith('mutate_') and f.endswith('.py'))
        # Longest-first: with a shared queue this is what keeps the tail short.
        batteries.sort(key=lambda b: -mutant_count(os.path.join(REPO, 'mutation', b)))
        print('\n-- %d batteries across %d worktree(s) --' % (len(batteries), jobs))

        log_dir = os.path.join(REPO, '.ci-local-logs')
        shutil.rmtree(log_dir, ignore_errors=True)
        os.makedirs(log_dir, exist_ok=True)

        print('   creating worktrees...')
        wts = make_worktrees(jobs, args.include_uncommitted)
        if not wts:
            print('   could not create any worktree; aborting the battery phase')
            failures.append(('worktrees', 'none created'))
        else:
            work = queue.Queue()
            for b in batteries:
                work.put(b)
            results = []
            threads = [threading.Thread(target=worker, args=(wt, work, results, log_dir))
                       for wt in wts]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            for b, rc, secs, out in results:
                if rc != 0:
                    failures.append(('battery ' + b, out))
            if not args.keep:
                drop_worktrees()
            else:
                print('   worktrees kept under %s' % WORKTREE_ROOT)
            print('   logs under %s' % log_dir)

    elapsed = time.time() - t0
    print('\n' + '=' * 72)
    if failures:
        print('FAIL in %.1f min -- %d failing item(s):' % (elapsed / 60.0, len(failures)))
        for name, out in failures:
            print('\n  * %s' % name)
            tail = [l for l in out.strip().splitlines() if l.strip()][-6:]
            for l in tail:
                print('      %s' % l[:160])
        return 1
    print('OK in %.1f min -- gates, suite and every battery green.' % (elapsed / 60.0))
    print('⚠️  This proves the tree you RAN it on. Only CI proves the commit you PUSHED.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
