#!/usr/bin/env python3
"""Regression bench for row VISIBILITY and the cell-count check.

Why this file exists
--------------------
On 2026-07-31, a field session against a mature 3-ledger installation found that
`ROW_ID_RE` did not match two real id shapes:

    A48a, A48b   a finding split into sub-rows with a letter suffix
    MI-08        a hyphenated prefix used by a scoped sibling ledger

Rows it does not match are invisible to EVERY check in the lint. The concrete
damage: two 🔴 THIS ship-blockers (A48a, A48b) were silently excluded from the
release gate, which reported 2 blockers when 4 existed, and an entire sibling
ledger (MI-UNFORGET, all rows hyphen-prefixed) reported `rows_checked: 0` while
looking perfectly healthy.

A false negative in the release gate is the worst failure this tool has: it does
not merely miss a problem, it actively reports "clear" over a blocker. These
tests exist so that class of bug cannot return silently.

Run:  python3 tests/test_row_visibility.py     (exit 0 = pass)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import parse_status  # noqa: E402

FAILURES = []


def check(label, actual, expected):
    ok = actual == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"  (got {actual!r}, want {expected!r})"))
    if not ok:
        FAILURES.append(label)


# --- 1. id grammar: shapes that MUST be visible ------------------------------
print("row-id grammar — must match:")
for rid in ["| A1 | x |", "| A48a | x |", "| A48b | x |", "| MI-08 | x |",
            "| S3 | x |", "| U12 | x |", "| **S12** | x |", "| 1 | x |",
            "| 12 | x |", "| ABC-99z | x |"]:
    check(f"matches {rid.split('|')[1].strip()!r}",
          bool(parse_status.ROW_ID_RE.match(rid)), True)

# --- 2. non-rows that must STAY invisible ------------------------------------
print("\nrow-id grammar — must NOT match (headers, separators, prose):")
for line in ["| # | Target | Finding |", "|---|---|---|", "| --- | --- |",
             "|  | |", "| Detail | x |", "| Risk: Fix | x |", "| Urgency | x |",
             "| Status | x |"]:
    check(f"ignores {line[:22]!r}",
          bool(parse_status.ROW_ID_RE.match(line)), False)

# --- 3. cell-count check: catches a stray pipe, no false positives -----------
LEDGER = """# t

<!-- unforget-format: v2 -->

| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|---|
| A1 | SOMEDAY | clean row | LOW | Low | Low | Good | 1 file | Small | `@status:open` |
| A2 | SOMEDAY | broken by grep 'a\\|b' | LOW | Low | Low | Good | 1 file | Small | `@status:open` |
| A3a | SOMEDAY | suffixed id, clean | LOW | Low | Low | Good | 1 file | Small | `@status:open` |

| # | Finding | Phase | Model | Status |
|---|---|---|---|---|
| MI-08 | narrower table must not false-positive | 3 | opus | `@status:open` |
"""

print("\ncell-count check:")
with tempfile.TemporaryDirectory() as td:
    f = Path(td) / "UNFORGET.md"
    f.write_text(LEDGER, encoding="utf-8")
    out = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_ledger.py"), "--file", str(f)],
        capture_output=True, text=True,
    )
    data = json.loads(out.stdout)

    # All four rows must be SEEN — including the suffixed and hyphenated ids.
    check("rows_checked counts every id shape", data["rows_checked"], 4)

    cc = [x for x in data["findings"] if x["check"] == "cell-count"]
    check("exactly one cell-count finding", len(cc), 1)
    check("flags the pipe-broken row", cc[0]["id"] if cc else None, "A2")
    check("cell-count is error severity",
          cc[0]["severity"] if cc else None, "error")
    # The 5-column sprint table must NOT be measured against the 10-column header.
    check("no false positive on the narrower table",
          [x["id"] for x in cc if x["id"] == "MI-08"], [])

# --- 4. contradiction matching: no false positives on ordinary prose ---------
# Bare substring matching produced three FP classes in the field (2026-07-31).
# A false contradiction sets archivable=False, so the row is held out of archive
# forever while a human hunts a conflict that was never there.
print("\ncontradiction matching:")
ROW = ("| A1 | THIS | finding | HIGH | Low | High | Good | 1 file | Small | {} |")
for cell, expect, label in [
    ("`@status:done-verified` · viewers can still open + view detail", False,
     "verb phrase 'still open +' is not a contradiction"),
    ("`@status:done-verified` · users can still open the sheet", False,
     "verb phrase 'still open the' is not a contradiction"),
    ("`@status:done-verified` · not a blocker", False,
     "negated 'blocker' is not a contradiction"),
    ("`@status:done-unverified` `@verified:code` · round-trip owed", False,
     "a row's own @status token is not narration"),
    ("`@status:done-verified` · the issue is still open", True,
     "adjective 'still open' IS a contradiction"),
    ("`@status:done-verified` · this is a blocker", True,
     "'blocker' IS a contradiction"),
    ("`@status:done-verified` · re-opened 07/30", True,
     "'re-opened' IS a contradiction"),
    ("`@status:withdrawn` · still broken", True,
     "withdrawn over 'still broken' IS a contradiction"),
]:
    got = any("narration says" in i
              for i in parse_status.parse_row(ROW.format(cell))["issues"])
    check(label, got, expect)

print()
if FAILURES:
    print(f"FAIL — {len(FAILURES)} assertion(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All row-visibility + cell-count assertions passed.")
