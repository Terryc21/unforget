#!/usr/bin/env python3
r"""Parse unforget @status / @verified tokens from ledger rows.

Implements the structured-status feature (see reference/status.md, from the
Maintenance & Integrity design spec §1 and §3). A row's authoritative status is
a machine-readable token at the FRONT of the Status cell:

    | U5 | ... | `@status:done-verified` `@verified:device` device round-trip ... |

Tools read the token; the prose after it is human narration only. This script
extracts the token(s), validates the tier rules, and flags a token that
contradicts its own narration (the "self-contradicting row" failure).

Usage:
  python3 parse_status.py --row "| U5 | THIS | ... | \`@status:done-verified\` ... |"
  python3 parse_status.py --file <path-to-UNFORGET.md>
  python3 parse_status.py --help

With --row: parses a single row, prints one JSON object.
With --file: parses every table row that carries a status token, prints a JSON
array (rows with no token are reported with token_present=false so legacy rows
are visible, not silently skipped).

Output per row (stdout, JSON):
  {
    "id": "U5"|null,
    "token_present": true|false,
    "status": "done-verified"|...|null,
    "status_valid": true|false,           # status is a known enum value
    "verified": "device"|...|null,
    "verified_present": true|false,
    "tier_valid": true|false,             # §3a: done-verified backed correctly
    "contradiction": true|false,          # §1b: token disagrees with narration
    "archivable": true|false,             # §1c: done-verified or withdrawn only
    "blocks_release": true|false,         # §1c: THIS-target still-a-blocker
    "issues": ["<one-line problem>", ...], # empty when clean
    "narration": "<prose after the token, trimmed>"
  }

Exit codes:
  0  parsed; no integrity issues found across the parsed row(s)
  1  parsed, but at least one row has an issue (invalid tier / contradiction /
     unknown status)
  2  usage error / file not found / nothing parseable
"""
import argparse
import json
import re
import sys
from pathlib import Path

# --- Enums (design spec maintenance §1a, §3) ------------------------------

STATUS_VALUES = {
    "open",
    "in-progress",
    "done-verified",
    "done-unverified",
    "blocked",
    "withdrawn",
}

VERIFIED_VALUES = {"code", "device", "session-claimed", "user"}

# Tiers that are allowed to back a done-verified status (§3a). "code" is
# allowed only with an explicit code-is-sufficient note (pure-logic changes);
# we accept it here but the verify pass (Phase 3) is where the note is checked.
DONE_VERIFIED_OK_TIERS = {"device", "user", "code"}

# Narration phrases that contradict a "done"/closed token (§1b). These are the
# exact shapes that produced the U5 failure: a token saying closed/verified over
# a narration that still says re-opened / broken / owed.
CONTRADICTION_PHRASES = [
    "re-opened",
    "reopened",
    "still broken",
    "still open",
    "still owed",
    "device round-trip still owed",
    "device-verify owed",
    "not yet verified",
    "not verified",
    "unverified",
    "still blocked",
    "still failing",
    "does not work",
    "blocker",
]

STATUS_RE = re.compile(r"@status:\s*([a-z-]+)")
VERIFIED_RE = re.compile(r"@verified:\s*([a-z-]+)")
# A table data row starts with "| <id> |". Capture the id and the LAST cell
# (the Status cell) for token parsing.
ROW_ID_RE = re.compile(r"^\|\s*([A-Za-z]?\d+)\s*\|")


def status_cell(row: str) -> str:
    """Return the Status cell of a table row.

    The Status cell is the one that CARRIES the `@status:` token — found by
    content, not by position. This matters because the format allows an optional
    `1-Star Risk` column appended AFTER Status (reference/format.md § Optional
    column): a naive "last cell" would then read the risk strip, not the token,
    silently breaking list/archive/verify. When no cell carries a token (a legacy
    tokenless row, or a v2 row whose Status genuinely IS last), fall back to the
    last non-empty cell so those keep working unchanged.
    """
    cells = [c.strip() for c in row.rstrip().rstrip("|").split("|")]
    if not cells:
        return ""
    for cell in cells:
        if STATUS_RE.search(cell):
            return cell
    return cells[-1]


def target_is_this(row: str) -> bool:
    """True if the row's Target cell marks it a current-release blocker (THIS)."""
    # Target is the 2nd cell; accept the emoji forms and the plain word.
    return bool(re.search(r"\bTHIS\b|🔴|🚢 THIS", row.split("|")[2] if row.count("|") >= 2 else ""))


def parse_row(row: str) -> dict:
    row_id_match = ROW_ID_RE.match(row)
    row_id = row_id_match.group(1) if row_id_match else None

    cell = status_cell(row)
    status_match = STATUS_RE.search(cell)
    verified_match = VERIFIED_RE.search(cell)

    status = status_match.group(1) if status_match else None
    verified = verified_match.group(1) if verified_match else None
    token_present = status is not None

    # Narration = everything in the Status cell after the token(s), with the
    # backtick-wrapped tokens themselves removed, lowercased for matching.
    narration = cell
    narration = re.sub(r"`?@status:[a-z-]+`?", "", narration)
    narration = re.sub(r"`?@verified:[a-z-]+`?", "", narration)
    narration = narration.strip(" `")
    narration_lc = narration.lower()

    issues: list[str] = []

    status_valid = status in STATUS_VALUES if token_present else True
    if token_present and not status_valid:
        issues.append(f"unknown @status value: {status!r}")

    verified_valid_value = verified in VERIFIED_VALUES if verified else True
    if verified and not verified_valid_value:
        issues.append(f"unknown @verified value: {verified!r}")

    # Tier rule (§3a): done-verified must be backed by device/user (or code w/ note).
    # session-claimed can NEVER back done-verified.
    tier_valid = True
    if status == "done-verified":
        if verified is None:
            tier_valid = False
            issues.append("done-verified has no @verified tier (needs device/user)")
        elif verified == "session-claimed":
            tier_valid = False
            issues.append(
                "done-verified backed only by @verified:session-claimed "
                "(a claim is not a verification; map to done-unverified)"
            )
        elif verified not in DONE_VERIFIED_OK_TIERS:
            tier_valid = False
            issues.append(f"done-verified backed by @verified:{verified} (needs device/user)")

    # Contradiction (§1b): a done/closed token over narration that still says
    # reopened/broken/owed/unverified.
    contradiction = False
    if status in ("done-verified", "done-unverified", "withdrawn"):
        for phrase in CONTRADICTION_PHRASES:
            if phrase in narration_lc:
                # done-unverified legitimately says "owed"/"unverified"; only a
                # done-VERIFIED or withdrawn row is contradicted by those.
                owed_phrases = {"still owed", "device round-trip still owed",
                                "device-verify owed", "not yet verified",
                                "not verified", "unverified"}
                if status == "done-unverified" and phrase in owed_phrases:
                    continue
                contradiction = True
                issues.append(f"token says {status} but narration says {phrase!r}")
                break

    # Archivable ONLY when the closure is CLEAN: withdrawn, or a done-verified
    # whose tier is valid and whose narration doesn't contradict it. A row whose
    # done-verified claim is invalid (bad/absent tier, or contradicted by its own
    # prose) is NOT archivable — archiving it would bury an unresolved integrity
    # problem, the exact failure this feature exists to prevent.
    archivable = status == "withdrawn" or (
        status == "done-verified" and tier_valid and not contradiction
    )
    blocks_release = target_is_this(row) and not archivable

    return {
        "id": row_id,
        "token_present": token_present,
        "status": status,
        "status_valid": status_valid,
        "verified": verified,
        "verified_present": verified is not None,
        "tier_valid": tier_valid,
        "contradiction": contradiction,
        "archivable": archivable,
        "blocks_release": blocks_release,
        "issues": issues,
        "narration": narration[:200],
    }


def parse_file(text: str) -> list[dict]:
    results = []
    for line in text.splitlines():
        if ROW_ID_RE.match(line):
            results.append(parse_row(line))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse unforget @status/@verified tokens and validate integrity."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--row", help="A single table row string to parse")
    group.add_argument("--file", help="Path to an UNFORGET.md to parse all rows")
    args = parser.parse_args()

    if args.row is not None:
        result = parse_row(args.row)
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
        return 1 if result["issues"] else 0

    target = Path(args.file)
    if not target.exists():
        print(json.dumps({"error": f"file not found: {target}"}), file=sys.stderr)
        return 2

    text = target.read_text(encoding="utf-8", errors="replace")
    results = parse_file(text)
    if not results:
        print(json.dumps({"error": "no table rows found"}), file=sys.stderr)
        return 2

    json.dump(results, sys.stdout)
    sys.stdout.write("\n")
    any_issue = any(r["issues"] for r in results)
    return 1 if any_issue else 0


if __name__ == "__main__":
    sys.exit(main())
