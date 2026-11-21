#!/usr/bin/env python3
"""One backup contract for every command that rewrites a ledger file.

Before a ledger is rewritten, its current bytes are copied beside it as
`<ledger name>.bak-YYYY-MM-DD-HHMMSS` (local time), then that ledger's backups
are pruned to the newest 5. The rewrite itself goes through a temp file and
`os.replace`, so a crash mid-write leaves either the old file or the new one,
never half of each.

Used by: `promote` and `archive` (run by the model, through the `backup` CLI
below), `set_aside.py convert --apply`, `row_budget.py split --apply`, and
`move_ledger.py` (which keeps the source until the copy is proven identical).

Usage:
  python3 ledger_backup.py backup --file <ledger.md> [--keep 5]
  python3 ledger_backup.py prune  --file <ledger.md> [--keep 5] [--dry-run]

Output (stdout, JSON):
  backup: {"backup": "<path>", "kept": [...], "pruned": [...]}
  prune:  {"ledger": "<name>", "kept": [...], "pruned": [...], "dry_run": bool}

Exit codes: 0 ok; 1 refused (backup name taken, nothing written); 2 usage error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
import sys
import tempfile
import time
from pathlib import Path

KEEP_DEFAULT = 5
STAMP_FORMAT = "%Y-%m-%d-%H%M%S"


class BackupRefused(Exception):
    """A backup could not be written safely; the ledger must not be rewritten."""


def backup_pattern(ledger_name: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(ledger_name)}\.bak-\d{{4}}-\d{{2}}-\d{{2}}-\d{{6}}$")


def backups_of(ledger: Path) -> list[Path]:
    """This ledger's backups, newest first (the stamp sorts chronologically)."""
    pattern = backup_pattern(ledger.name)
    return sorted((p for p in ledger.parent.iterdir() if pattern.match(p.name)),
                  key=lambda p: p.name, reverse=True)


def prune(ledger: Path, keep: int = KEEP_DEFAULT, dry_run: bool = False) -> dict:
    """Delete all but the newest `keep` backups of this one ledger. keep must be >= 1."""
    if keep < 1:
        raise ValueError("keep must be at least 1; keeping 0 would delete every backup")
    found = backups_of(ledger)
    kept, pruned = found[:keep], found[keep:]
    if not dry_run:
        for p in pruned:
            p.unlink()
    return {"ledger": ledger.name, "kept": [p.name for p in kept],
            "pruned": [p.name for p in pruned], "dry_run": dry_run}


def write_backup(ledger: Path, keep: int = KEEP_DEFAULT, clock=dt.datetime.now,
                 sleep=time.sleep) -> dict:
    """Copy the ledger's current bytes to a stamped backup, then prune.

    An existing backup is never overwritten. When this second's name is taken
    (two rewrites in one second, e.g. back-to-back row splits): a byte-identical
    backup is reused, since it already holds these bytes; otherwise wait for the
    next second and try once more, and refuse if that name is taken too."""
    if not ledger.is_file():
        raise BackupRefused(f"no ledger at {ledger}")
    data = ledger.read_bytes()
    target = None
    for attempt in range(2):
        candidate = ledger.with_name(f"{ledger.name}.bak-{clock().strftime(STAMP_FORMAT)}")
        try:
            with open(candidate, "xb") as fh:  # "x": fail rather than overwrite
                fh.write(data)
            target = candidate
            break
        except FileExistsError:
            if candidate.read_bytes() == data:
                result = prune(ledger, keep)
                return {"backup": str(candidate), "reused": True,
                        "kept": result["kept"], "pruned": result["pruned"]}
            if attempt == 0:
                sleep(1.05)
    if target is None:
        raise BackupRefused(f"backup {candidate.name} already exists with other content")
    if target.read_bytes() != data:
        target.unlink()
        raise BackupRefused(f"backup {target.name} did not read back identical; removed it")
    result = prune(ledger, keep)
    return {"backup": str(target), "reused": False, "kept": result["kept"], "pruned": result["pruned"]}


def atomic_write(path: Path, text: str) -> None:
    """Replace a file's contents in one step: temp file beside it, then os.replace.

    The temp file gets an unpredictable name from mkstemp (created exclusively,
    so a planted symlink is never followed), is fsynced before the swap, and
    takes the original file's permission bits (mkstemp creates it 0600)."""
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        if path.exists():
            os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up a ledger before rewriting it; prune old backups.")
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("backup", "prune"):
        p = sub.add_parser(name)
        p.add_argument("--file", required=True, help="the ledger file (e.g. UNFORGET.md)")
        p.add_argument("--keep", type=int, default=KEEP_DEFAULT,
                       help=f"backups to keep for this ledger, at least 1 (default {KEEP_DEFAULT})")
        if name == "prune":
            p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ledger = Path(args.file)
    if args.keep < 1:
        print(json.dumps({"error": "--keep must be at least 1; keeping 0 would delete every "
                                   "backup. Nothing was written or deleted."}), file=sys.stderr)
        return 2
    if not ledger.is_file():
        print(json.dumps({"error": f"ledger not found: {ledger}"}), file=sys.stderr)
        return 2
    if args.action == "prune":
        print(json.dumps(prune(ledger, args.keep, args.dry_run)))
        return 0
    try:
        print(json.dumps(write_backup(ledger, args.keep)))
    except BackupRefused as e:
        print(json.dumps({"error": f"refused: {e}"}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
