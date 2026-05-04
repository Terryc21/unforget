#!/usr/bin/env python3
"""Prune UNFORGET.md.bak-YYYY-MM-DD-HHMMSS backups, keeping the N most recent.

Lists files in the target directory matching `UNFORGET.md.bak-*`, sorts by
the encoded timestamp (which sorts identically to chronological order),
and deletes any beyond the most recent --keep N.

Files renamed to remove the `.bak-` infix (e.g., `UNFORGET-pre-build33.md`)
are not recognized as backups and are NOT touched.

Usage:
  python3 prune_backups.py --keep 5 --dir <directory-containing-UNFORGET.md>
  python3 prune_backups.py --keep 5 --dir <dir> --dry-run
  python3 prune_backups.py --help

Output (stdout, JSON):
  {
    "directory": "<dir>",
    "keep": 5,
    "dry_run": false,
    "kept": [...filenames sorted newest first...],
    "pruned": [...filenames sorted newest first...]
  }

Exit codes: 0 on success, 2 on usage error / directory not found.
"""
import argparse
import json
import re
import sys
from pathlib import Path

BACKUP_RE = re.compile(r"^UNFORGET\.md\.bak-\d{4}-\d{2}-\d{2}-\d{6}$")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prune UNFORGET.md backups, keeping the N most recent."
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Number of most-recent backups to retain (default: 5).",
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="Directory containing UNFORGET.md and its .bak files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be pruned without deleting anything.",
    )
    args = parser.parse_args()

    target_dir = Path(args.dir)
    if not target_dir.is_dir():
        print(
            json.dumps({"error": f"directory not found: {target_dir}"}),
            file=sys.stderr,
        )
        return 2

    if args.keep < 0:
        print(json.dumps({"error": "--keep must be >= 0"}), file=sys.stderr)
        return 2

    backups = sorted(
        (p for p in target_dir.iterdir() if BACKUP_RE.match(p.name)),
        key=lambda p: p.name,
        reverse=True,
    )

    kept = backups[: args.keep]
    pruned = backups[args.keep :]

    if not args.dry_run:
        for p in pruned:
            try:
                p.unlink()
            except OSError as e:
                print(
                    json.dumps({"error": f"failed to delete {p.name}: {e}"}),
                    file=sys.stderr,
                )
                return 2

    result = {
        "directory": str(target_dir),
        "keep": args.keep,
        "dry_run": args.dry_run,
        "kept": [p.name for p in kept],
        "pruned": [p.name for p in pruned],
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
