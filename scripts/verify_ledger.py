#!/usr/bin/env python3
r"""verify / doctor: the unforget integrity lint.

Read-only. Audits a ledger for the decay failures the Maintenance & Integrity
design spec (§4) targets — the checks that turn "a row misled a session" into
"the lint caught it before it misled anyone." Reuses parse_status (Phase 1) for
status/tier/contradiction and registry (Phase 2) for drift.

Checks (§4a):
  1. status-token ↔ narration disagreement      (a done/closed token over "re-opened"/"still owed")
  2. done-verified without a device/user tier    (verification-laundering)
  3. @verified:session-claimed backing done-verified  (a claim is not a proof)
  4. unknown @status / @verified value
  5. done-unverified would be archived            (only relevant with --archiving; see note)
  6. THIS-target + not-proven still blocks release
  7. table cell over the char budget              (bloat; Phase 7 owns the full rule)
  8. stale verify recipe                          (a file-citing row lacking a recipe;
                                                   still-open OR still-done both count)
  9. registry drift                               (cache != README, or block absent)
 10. cell-count != the table's declared width     (an unescaped '|' shifting every column)

Findings are returned most-severe first. This command NEVER edits — fixes are the
user's call (a future `verify --fix` proposes edits with approval).

Usage:
  python3 verify_ledger.py --file <UNFORGET.md> [--dir <ledger-dir>] [--char-budget N]
  python3 verify_ledger.py --help

  --dir enables the registry-drift check (the dir holding README.md/.unforget.json).
  --char-budget overrides the per-cell character budget (default 400).

Output (stdout, JSON):
  {
    "file": "<path>",
    "rows_checked": N,
    "findings": [
      {"severity": "error"|"warn", "check": "<slug>", "id": "<row id>",
       "message": "<one-line defect>"},
      ...
    ],
    "error_count": N,
    "warn_count": N,
    "gate_pass": true|false,   # false when any error-severity finding exists
    "advisory": "<one-line summary>"
  }

Exit codes:
  0  no error-severity findings (gate passes; warnings may still be present)
  1  at least one error-severity finding (gate FAILS; archive/promote should refuse)
  2  usage error / file not found
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

# Reuse the Phase 1 / Phase 2 helpers (same scripts/ dir).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_status  # noqa: E402
import registry  # noqa: E402

DEFAULT_CHAR_BUDGET = 400  # per-cell soft budget; Phase 7 formalizes/《configures》 this
# A row that cites a file path in its Finding/detail but carries no
# verify recipe is a stale-recipe risk. Detect a file-ish token.
#
# The naive form `[\w./-]+\.\w{1,5}\b` also matched ordinary prose: abbreviations
# ("e.g", "i.e") and decimals ("0.50", "3.99") all look like <stem>.<ext>. That
# inflated the warning count and trained users to ignore the check. Require
# EITHER a path separator plus any short extension (so `Sources/Foo.bar` still
# counts), OR a known source/doc extension on a bare filename.
_SOURCE_EXT = (
    "swift|js|jsx|ts|tsx|py|rb|go|rs|java|kt|mm|cpp|hpp|sh|bash|zsh|"
    "json|yml|yaml|toml|plist|xcstrings|xcconfig|entitlements|pbxproj|"
    "md|txt|csv|sql|html|css|cfg|ini|lock|env"
)
FILE_CITE_RE = re.compile(
    r"(?:[\w.-]*/[\w.-]+\.\w{1,5}"       # path separator: Sources/Foo.swift
    rf"|[\w.-]+\.(?:{_SOURCE_EXT}))\b",  # or a known extension: Foo.swift
    re.IGNORECASE,
)
# A `done-unverified` row's recipe asks the INVERSE question — "is the fix still
# in place?" — so it is legitimately labelled `Verify-still-DONE:`. Matching only
# the "open" spelling flagged those rows as recipe-less, which pushed authors to
# relabel a still-DONE recipe as still-open: silencing the warning by inverting
# the recipe's stated meaning. Accept both spellings instead.
RECIPE_MARKERS = (
    "verify-still-open",
    "verify still open",
    "verify-still-done",
    "verify still done",
)
# A literal status token quoted inside a Finding cell. Matches the same shape
# parse_status.STATUS_RE does, so the write-time warning and the parser agree on
# what counts as a token.
STATUS_TOKEN_RE = re.compile(r"@status:\s*([a-z-]+)")

# Severity ranking for "most-severe first" ordering.
SEVERITY_ORDER = {"error": 0, "warn": 1}


def status_cell(row: str) -> str:
    # Delegate to the one authoritative implementation, which finds the cell
    # carrying the @status token by CONTENT (so an appended 1-Star Risk column
    # after Status doesn't get read as the status). One source, not three.
    return parse_status.status_cell(row)


def finding_cell(row: str) -> str:
    # Delegate to the preset-aware locator (Compact drops the Target column, so a
    # fixed index 2 would return Urgency there). One source, not three.
    return parse_status.finding_cell(row)


HEADER_CELL_RE = re.compile(r"^\|\s*#?\s*\|.*\bStatus\b.*\|\s*$")


def _declared_width(line: str) -> int:
    """Column count declared by a table header row, or 0 if not a header."""
    if not HEADER_CELL_RE.match(line):
        return 0
    return len(parse_status.data_cells(line))


def check_rows(text: str, char_budget: int) -> list[dict]:
    findings = []
    declared = 0  # width of the most recent header row; 0 = unknown
    for line in text.splitlines():
        # Track the enclosing table's declared width. A ledger legitimately holds
        # several tables of DIFFERENT widths (Standard 10-col sections alongside a
        # 5-col sprint table), so the width is per-table, never a global constant.
        width = _declared_width(line)
        if width:
            declared = width
            continue

        if not parse_status.ROW_ID_RE.match(line):
            continue
        parsed = parse_status.parse_row(line)
        rid = parsed["id"] or "?"

        # Check 10 (U5): cell count != the enclosing table's declared width.
        # Root cause is almost always an unescaped `|` inside cell prose — a
        # `grep -c 'a\|b'` recipe, a regex alternation, a table drawn in a
        # detail note. The damage is silent: every positional column read
        # (Target, Urgency, Status) shifts by one, so a status token can land
        # in a rating cell and a ship-blocker can be misread as a rating.
        # Error severity: it corrupts data the other checks depend on.
        if declared:
            actual = len(parse_status.data_cells(line))
            if actual != declared:
                findings.append({
                    "severity": "error",
                    "check": "cell-count",
                    "id": rid,
                    "message": (
                        f"row has {actual} cells; the table declares {declared}. "
                        "Almost always an unescaped '|' in cell prose — every column "
                        "read past that point is shifted."
                    ),
                })

        # Check 4b: a status token quoted ILLUSTRATIVELY in the Finding cell.
        # `status_cell` scans last-cell-backward so the row's REAL status still
        # parses correctly, but a quoted token is still a live hazard: every
        # human-run `grep -c '@status:done-verified'` over the file counts it,
        # which is the exact reading CLAUDE.md documents for the ship gate. Warn
        # at WRITE time, naming the token, so the author fixes it here rather
        # than discovering a miscount later. Suggest breaking the literal.
        quoted = STATUS_TOKEN_RE.findall(finding_cell(line))
        if quoted:
            findings.append({
                "severity": "warn",
                "check": "quoted-status-token",
                "id": rid,
                "message": (
                    f"Finding cell quotes {len(quoted)} literal status token(s) "
                    f"({', '.join('@status:' + q for q in sorted(set(quoted)))}); "
                    "a human `grep -c` over this file will count them as real rows. "
                    "Break the literal (e.g. insert a separator after the '@')."
                ),
            })

        # Checks 1-4: everything parse_status already flags is an integrity issue.
        for issue in parsed["issues"]:
            # Classify severity: contradiction + bad tier + unknown = error.
            # A contradiction on a row that ALSO quotes a token in its Finding is
            # very likely caused by the quote, not by the narration the message
            # names — say so, or the author edits the innocent half. (Earned
            # 2026-08-11: the bare message sent an editor after their prose while
            # a quoted token was the actual cause.)
            check = ("contradiction" if "narration says" in issue
                     else "unknown-value" if "unknown @" in issue
                     else "tier")
            message = issue
            if check == "contradiction" and quoted:
                message += (
                    " — NOTE: this row also quotes a literal status token in its "
                    "Finding cell; that quote is the likely cause. Fix the quote "
                    "before rewriting the narration."
                )
            findings.append({
                "severity": "error",
                "check": check,
                "id": rid,
                "message": message,
            })

        # Check 6: THIS-target + not proven → still blocks release (a warn, since
        # it is expected while work is open; error only if the row CLAIMS done).
        if parsed["blocks_release"]:
            sev = "error" if parsed["status"] in ("done-verified", "done-unverified") else "warn"
            findings.append({
                "severity": sev,
                "check": "this-blocker",
                "id": rid,
                "message": f"🔴 THIS row not proven (status={parsed['status']}); still a release blocker",
            })

        # Check 7: per-cell char budget (bloat). Flag the Status and Finding cells.
        for cell_name, cell_val in (("status", status_cell(line)), ("finding", finding_cell(line))):
            if len(cell_val) > char_budget:
                findings.append({
                    "severity": "warn",
                    "check": "char-budget",
                    "id": rid,
                    "message": f"{cell_name} cell is {len(cell_val)} chars (budget {char_budget}); move history to a detail block",
                })

        # Check 8: stale-recipe risk — a Finding that cites a file but the row
        # carries no verify recipe anywhere in its cells.
        # Skip POINTER rows: a branch pointer's Finding cites the CHILD ledger's
        # filename ("→ see RELEASE-1.0.md"), which trips the file-cite regex, but a
        # pointer is a signpost, not a work item — asking it for a verify recipe is
        # a false positive (every branched ledger would carry one).
        # Skip CLEANLY-CLOSED rows for the same reason: a withdrawn or clean
        # done-verified row cites files as the EVIDENCE FOR CLOSURE, not as a live
        # premise needing recheck. Reuse `archivable` rather than a status list, so
        # done-unverified (device round-trip still owed) and blocked keep tripping —
        # those are exactly the premises that CAN decay.
        fcell = finding_cell(line)
        is_pointer = "this row is a pointer" in line.lower() or "→ see " in status_cell(line).lower()
        is_closed = parse_status.parse_row(line).get("archivable", False)
        if not is_pointer and not is_closed and FILE_CITE_RE.search(fcell):
            whole = line.lower()
            if not any(m in whole for m in RECIPE_MARKERS):
                findings.append({
                    "severity": "warn",
                    "check": "stale-recipe",
                    "id": rid,
                    "message": "row cites a file path but has no verify recipe (still-open or still-done); premise may have decayed",
                })

    return findings


def check_registry(dir_path: Path) -> list[dict]:
    findings = []
    result = registry.check_drift(dir_path)
    if "error" in result:
        return findings  # no README — not a ledger-dir concern for verify
    if not result.get("block_present"):
        findings.append({
            "severity": "warn", "check": "registry",
            "id": "-", "message": "no registry block in README; run init/import to create one",
        })
        return findings
    if result.get("cache_in_sync") is False:
        findings.append({
            "severity": "warn", "check": "registry-drift",
            "id": "-", "message": "registry cache drifted from README; README wins — regenerate the cache",
        })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="verify/doctor: unforget integrity lint (read-only).")
    parser.add_argument("--file", required=True, help="Path to UNFORGET.md")
    parser.add_argument("--dir", help="Ledger dir (enables registry-drift check)")
    parser.add_argument("--char-budget", type=int, default=DEFAULT_CHAR_BUDGET)
    args = parser.parse_args()

    target = Path(args.file)
    if not target.exists():
        print(json.dumps({"error": f"file not found: {target}"}), file=sys.stderr)
        return 2

    text = target.read_text(encoding="utf-8", errors="replace")
    findings = check_rows(text, args.char_budget)
    rows_checked = sum(1 for ln in text.splitlines() if parse_status.ROW_ID_RE.match(ln))

    if args.dir:
        findings += check_registry(Path(args.dir))

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 9), f["check"], f["id"]))
    error_count = sum(1 for f in findings if f["severity"] == "error")
    warn_count = sum(1 for f in findings if f["severity"] == "warn")
    gate_pass = error_count == 0

    result = {
        "file": str(target),
        "rows_checked": rows_checked,
        "findings": findings,
        "error_count": error_count,
        "warn_count": warn_count,
        "gate_pass": gate_pass,
        "advisory": (
            f"{error_count} error(s), {warn_count} warning(s); "
            + ("gate PASSES" if gate_pass else "gate FAILS — archive/promote should refuse")
        ),
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(main())
