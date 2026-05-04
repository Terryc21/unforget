#!/usr/bin/env python3
"""Check the unforget format-version marker in an UNFORGET.md file.

Reads the first 30 lines of the target file and grep for an HTML comment
of the form `<!-- unforget-format: vN -->`. Reports the version (if present),
whether it is recognized by this skill version, and basic structural
sanity checks (presence of the four section headers).

Usage:
  python3 check_format_version.py <path-to-UNFORGET.md>
  python3 check_format_version.py --help

Output (stdout, JSON):
  {
    "path": "<input>",
    "marker_present": true|false,
    "format_version": "v1"|null,
    "supported_versions": ["v1"],
    "recognized": true|false,
    "writable": true|false,
    "section_headers_found": ["1. Paused plans", ...],
    "section_headers_missing": [...],
    "advisory": "<one-line summary for the LLM caller>"
  }

Exit codes:
  0  marker present and recognized
  1  marker absent OR future-version (skill should treat as read-only or prompt)
  2  usage error / file not found
"""
import argparse
import json
import re
import sys
from pathlib import Path

SUPPORTED_VERSIONS = ["v1"]
HEADER_LINES_TO_SCAN = 30
EXPECTED_SECTION_HEADERS = [
    "1. Paused plans",
    "2. Session spillover",
    "3. Audit findings",
    "4. User-reported",
]
MARKER_RE = re.compile(r"<!--\s*unforget-format:\s*(v\d+)\s*-->")


def find_marker(lines: list[str]) -> str | None:
    for line in lines[:HEADER_LINES_TO_SCAN]:
        match = MARKER_RE.search(line)
        if match:
            return match.group(1)
    return None


def find_section_headers(text: str) -> tuple[list[str], list[str]]:
    found = []
    missing = []
    for header in EXPECTED_SECTION_HEADERS:
        if re.search(rf"^#+\s.*{re.escape(header)}", text, re.MULTILINE):
            found.append(header)
        else:
            missing.append(header)
    return found, missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check unforget format-version marker and structural sanity."
    )
    parser.add_argument("path", help="Path to UNFORGET.md")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(json.dumps({"error": f"file not found: {target}"}), file=sys.stderr)
        return 2

    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    version = find_marker(lines)
    found, missing = find_section_headers(text)

    if version is None:
        recognized = False
        writable = False
        advisory = (
            "marker absent; prompt user to confirm format and recommend adding "
            "<!-- unforget-format: v1 --> near top of file"
        )
    elif version in SUPPORTED_VERSIONS:
        recognized = True
        writable = True
        advisory = f"marker recognized ({version}); proceed normally"
    else:
        recognized = False
        writable = False
        advisory = (
            f"marker {version} is newer than supported {SUPPORTED_VERSIONS}; "
            "operate in read-only mode and recommend skill upgrade"
        )

    result = {
        "path": str(target),
        "marker_present": version is not None,
        "format_version": version,
        "supported_versions": SUPPORTED_VERSIONS,
        "recognized": recognized,
        "writable": writable,
        "section_headers_found": found,
        "section_headers_missing": missing,
        "advisory": advisory,
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0 if recognized else 1


if __name__ == "__main__":
    sys.exit(main())
