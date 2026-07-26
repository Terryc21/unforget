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
  8. stale verify-still-open recipe               (a file-citing row lacking a recipe)
  9. registry drift                               (cache != README, or block absent)

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
# verify-still-open recipe is a stale-recipe risk. Detect a file-ish token.
FILE_CITE_RE = re.compile(r"[\w./-]+\.\w{1,5}\b")
RECIPE_MARKERS = ("verify-still-open", "verify still open")

# Severity ranking for "most-severe first" ordering.
SEVERITY_ORDER = {"error": 0, "warn": 1}


def status_cell(row: str) -> str:
    # Delegate to the one authoritative implementation, which finds the cell
    # carrying the @status token by CONTENT (so an appended 1-Star Risk column
    # after Status doesn't get read as the status). One source, not three.
    return parse_status.status_cell(row)


def finding_cell(row: str) -> str:
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    # Finding is the 3rd column (# | Target | Finding | ...)
    return cells[2] if len(cells) >= 3 else ""


def check_rows(text: str, char_budget: int) -> list[dict]:
    findings = []
    for line in text.splitlines():
        if not parse_status.ROW_ID_RE.match(line):
            continue
        parsed = parse_status.parse_row(line)
        rid = parsed["id"] or "?"

        # Checks 1-4: everything parse_status already flags is an integrity issue.
        for issue in parsed["issues"]:
            # Classify severity: contradiction + bad tier + unknown = error.
            findings.append({
                "severity": "error",
                "check": ("contradiction" if "narration says" in issue
                          else "unknown-value" if "unknown @" in issue
                          else "tier"),
                "id": rid,
                "message": issue,
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
        # carries no verify-still-open recipe anywhere in its cells.
        fcell = finding_cell(line)
        if FILE_CITE_RE.search(fcell):
            whole = line.lower()
            if not any(m in whole for m in RECIPE_MARKERS):
                findings.append({
                    "severity": "warn",
                    "check": "stale-recipe",
                    "id": rid,
                    "message": "row cites a file path but has no verify-still-open recipe; premise may have decayed",
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
