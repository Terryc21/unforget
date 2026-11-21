#!/usr/bin/env python3
"""Move a ledger to a new home, removing the original only after a proven-identical copy.

`init`'s migration step (reference/init.md § Phase 6b) consolidates scattered
ledgers. Its rule is: copy, confirm the destination is byte-for-byte identical,
and only then remove the source or replace it with a redirect pointer. Before
this script that comparison was something the model said it had done. Here it
is a check the script makes, and the source is untouched unless it passes.

Default is a dry run that prints the plan. With --apply:
  1. Refuse if the destination exists with different bytes (never overwrite).
  2. Copy the source's bytes to the destination (exclusive create).
  3. Read the destination back; compare bytes and SHA-256 with the source.
     On any mismatch: delete the copy this run made, leave the source, exit 1.
  4. Back up the source beside itself (`<name>.bak-<stamp>`, via ledger_backup).
  5. Remove the source, or with --redirect replace it with a short pointer that
     the surface survey recognizes as a redirect (fewer than 30 lines, says MOVED,
     names the new path), so it is never re-imported as a backlog.

A destination that already exists with identical bytes counts as copied (a
re-run after an interrupted move finishes the job).

Usage:
  python3 move_ledger.py --src <old/TERRY.md> --dst <new/TERRY.md> [--redirect] [--apply]

Output (stdout, JSON): {"src", "dst", "sha256", "bytes", "applied", "steps": [...],
"source_action": "removed"|"redirected"|"kept", "backup": <path|null>}
Exit codes: 0 ok (or dry run); 1 refused, nothing removed; 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_backup  # noqa: E402


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redirect_text(src: Path, dst: Path) -> str:
    try:
        target = os.path.relpath(dst.resolve(), src.resolve().parent)
    except ValueError:  # different drives on Windows
        target = str(dst.resolve())
    return (f"# {src.name}: MOVED\n\n"
            f"This ledger MOVED to `{target}` (absolute: `{dst.resolve()}`).\n"
            f"Edit it there. This pointer is kept so old links still lead somewhere.\n")


def move(src: Path, dst: Path, redirect: bool, apply: bool) -> tuple[int, dict]:
    result = {"src": str(src), "dst": str(dst), "applied": False, "steps": [],
              "source_action": "kept", "backup": None}
    if not src.is_file():
        return 2, {**result, "error": f"source not found: {src}"}
    if src.resolve() == dst.resolve():
        return 2, {**result, "error": "source and destination are the same file"}
    if not dst.parent.is_dir():
        return 2, {**result, "error": f"destination directory does not exist: {dst.parent}"}

    data = src.read_bytes()
    digest = sha256(data)
    result.update(sha256=digest, bytes=len(data))
    already = dst.exists()
    if already and dst.read_bytes() != data:
        return 1, {**result, "error": "refused: destination exists with different content; "
                                      "nothing was copied or removed"}

    plan = (["destination already holds identical bytes; no copy needed"] if already
            else [f"copy {len(data)} bytes to {dst}"])
    plan += ["read the copy back; compare bytes and SHA-256 with the source",
             f"back up the source as {src.name}.bak-<stamp>",
             (f"replace the source with a MOVED pointer to {dst}" if redirect
              else "remove the source")]
    result["steps"] = plan
    if not apply:
        return 0, {**result, "advisory": "dry run; nothing written. Re-run with --apply."}

    created = False
    if not already:
        try:
            with open(dst, "xb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            created = True
        except FileExistsError:
            return 1, {**result, "error": "refused: destination appeared during the move"}

    copy = dst.read_bytes()
    if copy != data or sha256(copy) != digest:
        if created:
            dst.unlink()
        return 1, {**result, "error": "refused: the copy did not read back identical; removed the "
                                      "copy, the source is untouched"}
    if src.read_bytes() != data:
        return 1, {**result, "error": "refused: the source changed during the move; the copy is "
                                      "kept at the destination, the source is untouched"}

    try:
        result["backup"] = ledger_backup.write_backup(src)["backup"]
    except ledger_backup.BackupRefused as e:
        return 1, {**result, "error": f"refused: {e}; the copy is verified, the source is untouched"}

    if redirect:
        ledger_backup.atomic_write(src, redirect_text(src, dst))
        result["source_action"] = "redirected"
    else:
        src.unlink()
        result["source_action"] = "removed"
    result["applied"] = True
    return 0, result


def main() -> int:
    parser = argparse.ArgumentParser(description="Move a ledger; remove the original only after a verified copy.")
    parser.add_argument("--src", required=True)
    parser.add_argument("--dst", required=True)
    parser.add_argument("--redirect", action="store_true",
                        help="leave a MOVED pointer at the old path instead of removing it")
    parser.add_argument("--apply", action="store_true", help="perform the move (default: dry run)")
    args = parser.parse_args()
    code, result = move(Path(args.src), Path(args.dst), args.redirect, args.apply)
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    sys.exit(main())
