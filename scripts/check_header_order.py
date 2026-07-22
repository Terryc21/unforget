#!/usr/bin/env python3
"""Lint UNFORGET-ledger table headers for canonical core-column order.

Finding #1 (a test fixture that reversed Target and Finding while claiming to
"mirror a Standard UNFORGET.md") existed because nothing enforced column order.
The canonical order is asserted only in prose in `reference/format.md` and then
copied by hand into every fixture, example, and README table. This lint is the
guard that makes that copy-by-hand safe: it scans a tree for UNFORGET-ledger
table headers and verifies the core columns appear in the canonical relative
order.

It checks **relative order of the core columns**, not exact string equality,
because legitimate variants exist and must pass:

  - Abbreviated headers (`Urg` for `Urgency`, `RFix` for `Risk: Fix`, `Blast`
    for `Blast Radius`) — same columns, shorter labels.
  - Appended extra columns (`1-Star Risk`, `Client`, `Sprint`) after `Status`.
  - Elided example rows (`| # | … | Status | 1-Star Risk |`) that show only a
    slice — these are skipped, not failed, because they aren't full headers.

What it does NOT treat as an UNFORGET ledger (and skips):

  - The skill's own roadmap/feedback rating tables (`# | Finding | Urgency |…`,
    no Target column) — a different table shape used in docs, not a ledger.
  - Any table whose header doesn't contain both `#` and a recognizable Target
    or Finding column.

Canonical core order (from `reference/format.md § Columns`):

  # → Target → Finding → Urgency → Risk: Fix → Risk: No Fix → ROI →
  Blast Radius → Fix Effort → Status

Compact/Lean/Continuous presets drop or rename columns; this lint validates the
*relative order of whatever core columns are present*, so a Lean header
(`# | Target | Finding | Urgency | Effort | Status`) passes — its columns are a
subsequence of the canonical order.

Usage:
  python3 check_header_order.py --root <dir> [--json]
  python3 check_header_order.py --help

Output (default): human-readable PASS/FAIL lines, one per offending header.
Output (--json): {"checked": N, "violations": [{"file","line","header","reason"}]}

Exit codes:
  0  all ledger headers are in canonical order
  1  one or more headers violate canonical order
  2  usage error / root not found
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Canonical core order. Each entry is (canonical-name, matchers) where matchers
# are lowercased substrings that identify the column from a (possibly
# abbreviated) header cell. Order in this list IS the canonical order.
CORE_COLUMNS = [
    ("#", ["#"]),
    ("Target", ["target"]),
    ("Finding", ["finding"]),
    ("Urgency", ["urgency", "urg"]),
    ("Risk: Fix", ["risk: fix", "rfix"]),
    ("Risk: No Fix", ["risk: no fix", "rno"]),
    ("ROI", ["roi"]),
    ("Blast Radius", ["blast"]),
    ("Fix Effort", ["fix effort", "effort"]),
    ("Status", ["status"]),
]

# A header must have BOTH of these to count as an UNFORGET ledger table (this is
# what excludes the roadmap/feedback tables that have Finding but no Target).
LEDGER_REQUIRED = ["target", "finding"]

HEADER_RE = re.compile(r"^\|\s*#\s*\|.*\|\s*$", re.MULTILINE)
ELISION = "…"


def classify_cell(cell: str) -> str | None:
    """Return the canonical column name a header cell maps to, or None."""
    low = cell.strip().lower()
    if not low:
        return None
    for name, matchers in CORE_COLUMNS:
        # exact '#' only matches a bare '#', not e.g. 'Finding' containing none
        if name == "#":
            if low == "#":
                return "#"
            continue
        if any(m in low for m in matchers):
            return name
    return None  # an extra/unknown column (e.g. 1-Star Risk, Client)


def check_header(header_line: str) -> str | None:
    """Return a violation reason, or None if the header is OK / not a ledger."""
    cells = [c.strip() for c in header_line.strip().strip("|").split("|")]
    low_join = " ".join(c.lower() for c in cells)

    # Elided example headers (contain the … placeholder) are illustrative slices,
    # not full ledger headers — skip.
    if ELISION in cells:
        return None

    # Must look like an UNFORGET ledger (has both Target and Finding).
    if not all(req in low_join for req in LEDGER_REQUIRED):
        return None  # not a ledger table; skip (roadmap/feedback docs, etc.)

    # Map each cell to a canonical column; keep only recognized core columns,
    # in the order they appear in the header.
    seen_order = []
    for cell in cells:
        name = classify_cell(cell)
        if name is not None:
            seen_order.append(name)

    # The observed core columns must be a subsequence of the canonical order
    # (extras are allowed and were dropped above; presets may omit columns).
    canonical = [name for name, _ in CORE_COLUMNS]
    canon_index = {name: i for i, name in enumerate(canonical)}
    last = -1
    for name in seen_order:
        idx = canon_index[name]
        if idx < last:
            # find the two columns that are out of order for a precise message
            return (
                f"core column '{name}' appears after a later-ranked column; "
                f"observed order {seen_order} is not a subsequence of canonical "
                f"{canonical}"
            )
        last = idx
    return None


def scan(root: Path) -> tuple[int, list[dict]]:
    checked = 0
    violations = []
    for md in sorted(root.rglob("*.md")):
        # skip nothing by path — a violation anywhere is a violation — but the
        # ledger-detection above naturally excludes non-ledger tables.
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in HEADER_RE.finditer(text):
            header = m.group(0)
            # only count headers that survive ledger detection as "checked"
            cells = [c.strip() for c in header.strip().strip("|").split("|")]
            low_join = " ".join(c.lower() for c in cells)
            if ELISION in cells or not all(r in low_join for r in LEDGER_REQUIRED):
                continue
            checked += 1
            reason = check_header(header)
            if reason:
                line = text[: m.start()].count("\n") + 1
                violations.append(
                    {
                        "file": str(md.relative_to(root)),
                        "line": line,
                        "header": header.strip(),
                        "reason": reason,
                    }
                )
    return checked, violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint UNFORGET-ledger table headers for canonical column order."
    )
    parser.add_argument("--root", required=True, help="Directory to scan recursively")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}), file=sys.stderr)
        return 2

    checked, violations = scan(root)

    if args.json:
        json.dump({"checked": checked, "violations": violations}, sys.stdout)
        sys.stdout.write("\n")
    else:
        for v in violations:
            print(f"FAIL  {v['file']}:{v['line']}  {v['reason']}")
            print(f"      {v['header']}")
        if violations:
            print(f"\n{len(violations)} of {checked} ledger headers out of order.")
        else:
            print(f"OK: {checked} UNFORGET-ledger headers all in canonical order.")

    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
