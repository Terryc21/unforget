#!/usr/bin/env python3
"""Encode an absolute filesystem path to Claude Code's per-project memory-dir name.

The Claude Code path-encoding rule: replace each `/` with `-` AND each
whitespace character (space, tab) with `-`. The leading `/` becomes a
leading `-`.

Example:
  /Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio
    -> -Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio

Memory directory at: ~/.claude/projects/<encoded>/memory/

Usage:
  python3 encode_project_path.py "<absolute-path>"
  python3 encode_project_path.py --help

Output (stdout, JSON):
  {
    "path": "<input>",
    "encoded": "<encoded>",
    "memory_dir": "~/.claude/projects/<encoded>/memory/"
  }

Exit codes: 0 on success, 2 on usage error.
"""
import argparse
import json
import re
import sys


def encode(path: str) -> str:
    return re.sub(r"[/\s]", "-", path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Encode an absolute path to Claude Code's memory-dir name."
    )
    parser.add_argument("path", help="Absolute filesystem path to encode.")
    args = parser.parse_args()

    encoded = encode(args.path)
    result = {
        "path": args.path,
        "encoded": encoded,
        "memory_dir": f"~/.claude/projects/{encoded}/memory/",
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
