#!/usr/bin/env python3
"""
sync_nt8.py
===========

Sync this repo's AddOn .cs files to the NinjaTrader 8 live compilation folder.

Source (repo, git-tracked):
    addons/*.cs  ->  %USERPROFILE%/Documents/NinjaTrader 8/bin/Custom/AddOns/

Usage:
    python tools/sync_nt8.py            # sync
    python tools/sync_nt8.py --verify   # show drift status only, exit 1 on drift
    python tools/sync_nt8.py --dry-run  # show what would be copied

This script is the SINGLE source-of-truth sync mechanism. Never manually copy
.cs files to the NT8 folder -- always run this script after editing NinjaScript
code.

Scope note (repo split, 2026-08-12): this tool descends from
tvDownloadOHLC's scripts/utils/sync_nt8_strategies.py, which also synced
strategies/ and indicators/. Those trees did NOT move here -- they stay in
tvDownloadOHLC along with the strategy/indicator half of that tool. This copy
owns the AddOns/ half only.

Shared-destination note: NT8 compiles every .cs in AddOns/ into one assembly,
and nt8-mcp-bridge deploys into the SAME folder. So files in AddOns/ that this
repo does not own are expected, not orphans, and are reported as unmanaged
without failing. Full-union parity is nt8-mcp-bridge's deploy tool's job,
because that repo is the one that knows about both trees -- the dependency
direction only runs that way (see docs/NT8_REPO_SPLIT_PLAN.md section 1).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
ADDONS_SRC = REPO_ROOT / "addons"

NT8_HOME = Path(os.environ.get("USERPROFILE", "")) / "Documents" / "NinjaTrader 8" / "bin" / "Custom"
ADDONS_DST = NT8_HOME / "AddOns"


def file_hash(path: Path) -> str:
    """MD5 of file content, normalised for drift comparison.

    Line endings are normalised to LF and a UTF-8 BOM is stripped before
    hashing. Files copied into the NT8 tree by other tools (or edited in NT8's
    own editor) come back CRLF while the repo keeps LF, and a raw byte hash
    then reports every single file as drifted.

    That is not hypothetical: it is exactly what happened on 2026-08-07, when a
    plain diff of the deployed addons showed 8216 changed lines on a 4108-line
    file. The files were byte-identical apart from carriage returns, but the
    false alarm was written into the deployment runbook as "the deployed
    sources have diverged" and cost real time to disprove. A drift check that
    cries wolf on every file teaches you to ignore it, which is worse than
    having no check at all.

    C# is insensitive to which one it gets, so a pure line-ending difference is
    not drift and must not trigger a redeploy.
    """
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.md5(data).hexdigest()


def sync_addon_files(dry_run: bool, verify: bool) -> dict:
    """Sync addons/*.cs to the NT8 AddOns/ folder."""
    result = {"copied": [], "identical": [], "missing_dst": [], "unmanaged_dst": []}

    if not ADDONS_DST.exists():
        print(f"  [ERROR] NT8 AddOns dir does not exist: {ADDONS_DST}")
        return result

    if not ADDONS_SRC.exists():
        print(f"  [ERROR] Source addons dir does not exist: {ADDONS_SRC}")
        return result

    src_files = sorted(ADDONS_SRC.glob("*.cs"))
    dst_files = set(f.name for f in ADDONS_DST.glob("*.cs"))
    src_names = set(f.name for f in src_files)

    for name in sorted(dst_files - src_names):
        result["unmanaged_dst"].append(name)

    for src_file in src_files:
        dst_file = ADDONS_DST / src_file.name

        if not dst_file.exists():
            result["missing_dst"].append(src_file.name)
            if not verify:
                if not dry_run:
                    shutil.copy2(src_file, dst_file)
                    print(f"  [COPIED]  {src_file.name}  (new file in AddOns/)")
                else:
                    print(f"  [DRY-RUN] {src_file.name}  (would copy to AddOns/)")
            continue

        if file_hash(src_file) == file_hash(dst_file):
            result["identical"].append(src_file.name)
            if verify:
                print(f"  [OK]      {src_file.name}")
        else:
            result["copied"].append(src_file.name)
            if not verify:
                if not dry_run:
                    shutil.copy2(src_file, dst_file)
                    print(f"  [SYNCED]  {src_file.name}  (content differed)")
                else:
                    print(f"  [DRY-RUN] {src_file.name}  (would sync)")
            else:
                print(f"  [DRIFT]   {src_file.name}  (source differs from NT8)")

    return result


def main():
    parser = argparse.ArgumentParser(description="Sync repo AddOn .cs files to the NT8 live folder.")
    parser.add_argument("--verify", action="store_true", help="Show drift status without copying.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be copied without copying.")
    args = parser.parse_args()

    print("=" * 70)
    print("NT8 AddOn Sync -- repo source -> NT8 live compilation folder")
    print("=" * 70)
    print(f"  Source:   {ADDONS_SRC}")
    print(f"  NT8 dest: {ADDONS_DST}")
    print()

    if not NT8_HOME.exists():
        print(f"[ERROR] NT8 Custom folder not found: {NT8_HOME}")
        print("        Is NinjaTrader 8 installed on this machine?")
        sys.exit(1)

    mode = "VERIFY" if args.verify else "DRY-RUN" if args.dry_run else "SYNC"
    print(f"Mode: {mode}")
    print()

    print(f"[AddOns/] {ADDONS_SRC} -> {ADDONS_DST}")
    result = sync_addon_files(args.dry_run, args.verify)

    print()
    print("=" * 70)
    total_synced = len(result["copied"])
    total_copied = len(result["missing_dst"])
    total_identical = len(result["identical"])
    total_drift = total_synced + total_copied
    unmanaged = result["unmanaged_dst"]

    if args.verify:
        if total_drift == 0:
            print(f"  ALL IN SYNC ({total_identical} files identical)")
        else:
            print(f"  DRIFT DETECTED: {total_drift} file(s) differ, {total_identical} identical")
            sys.exit(1)
    else:
        if args.dry_run:
            print(f"  DRY-RUN: {total_drift} file(s) would be synced, {total_identical} already identical")
        else:
            print(f"  DONE: {total_synced} synced, {total_copied} copied (new), {total_identical} already identical")

    if unmanaged:
        print(f"  Unmanaged files in AddOns/ (not owned by this repo -- expected if")
        print(f"  nt8-mcp-bridge is deployed into the same folder):")
        for name in unmanaged:
            print(f"    AddOns/{name}")

    print("=" * 70)


if __name__ == "__main__":
    main()
