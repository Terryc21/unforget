#!/usr/bin/env python3
"""Structural assertion checker for unforget behavioral test cases.

Behavioral tests exercise the LLM following the skill's prose (add / edit /
promote / list / format-version handling). Unlike the deterministic `scripts/`
helpers, the LLM's output is not byte-for-byte reproducible — wording,
whitespace, and column padding vary run to run. Exact golden diffing does not
apply here. What IS stable is the *structure* of a correct result:

  - a new row landed in the right section with the right ID prefix
  - a Target / Status / Urgency cell holds the expected enum value
  - the four-part detail-block order is preserved
  - a format-version refusal actually refused (no write happened)

This checker reads an `assertions.txt` file (one assertion per line, `#`
comments allowed) and evaluates each against a produced `result.md`. It is the
mechanical half of the harness; the semantic half (did the LLM pick a sensible
Target?) stays a human read of the diff, per README.

Assertion grammar (one per line):

  contains        <substring>          result contains the literal substring
  absent          <substring>          result does NOT contain the substring
  regex           <python-regex>       result matches the regex (MULTILINE)
  row_in_section  <SECTION_NO> <ID>    a table row whose first cell is <ID>
                                       appears under section <SECTION_NO>'s header
  cell            <ID> <COL> <VALUE>   the row for <ID> has <VALUE> in column
                                       <COL> (COL = the header text, e.g. Target)
  detail_order    <ID>                 the detail block for <ID> keeps the
                                       four-part order (closure→body→verify→spawn),
                                       skipping absent parts
  unchanged_from  <path>               result is byte-identical to <path>
                                       (for refusal cases: nothing was written)

Usage:
  python3 check_behavioral.py --case <case-dir> [--result <result.md>]

  <case-dir>   holds assertions.txt, input.md, command.txt, expected.md.
  --result     the LLM-produced file to check. Defaults to <case-dir>/result.md.
               For `unchanged_from input.md` cases, point it at whatever the
               command was allowed to touch.

Output: one line per assertion (PASS/FAIL), a summary, exit 0 iff all pass.
Exit codes: 0 all passed · 1 one or more failed · 2 usage / missing files.
"""
import argparse
import re
import sys
from pathlib import Path

SECTION_HEADER_RE = {
    "1": re.compile(r"^#+\s.*1\.\s*Paused plans", re.MULTILINE | re.IGNORECASE),
    "2": re.compile(r"^#+\s.*2\.\s*Session spillover", re.MULTILINE | re.IGNORECASE),
    "3": re.compile(r"^#+\s.*3\.\s*Audit findings", re.MULTILINE | re.IGNORECASE),
    "4": re.compile(r"^#+\s.*4\.\s*User-reported", re.MULTILINE | re.IGNORECASE),
}


def _section_span(text: str, section_no: str) -> tuple[int, int]:
    """Return (start, end) char offsets of a section's body (header to next
    top-or-second-level header, or EOF)."""
    header_re = SECTION_HEADER_RE[section_no]
    m = header_re.search(text)
    if not m:
        return (-1, -1)
    start = m.end()
    # next section header of the form "## N." ends this span
    nxt = re.compile(r"^#+\s.*[1-4]\.\s", re.MULTILINE)
    for cand in nxt.finditer(text, start):
        return (start, cand.start())
    return (start, len(text))


def _find_row(text: str, row_id: str) -> str | None:
    """Return the full markdown table-row line whose first data cell is row_id."""
    row_re = re.compile(rf"^\|\s*{re.escape(row_id)}\s*\|.*$", re.MULTILINE)
    m = row_re.search(text)
    return m.group(0) if m else None


def _header_cells(text: str, near_offset: int) -> list[str]:
    """Find the nearest preceding table header row and split its cells."""
    header = None
    for m in re.finditer(r"^\|\s*#\s*\|.*$", text, re.MULTILINE):
        if m.start() <= near_offset:
            header = m.group(0)
        else:
            break
    if header is None:
        # fall back to the first header anywhere
        m = re.search(r"^\|\s*#\s*\|.*$", text, re.MULTILINE)
        header = m.group(0) if m else ""
    return [c.strip() for c in header.strip().strip("|").split("|")]


def _row_cells(row_line: str) -> list[str]:
    return [c.strip() for c in row_line.strip().strip("|").split("|")]


def assert_contains(text, arg, _case):
    return arg in text, f"substring {arg!r} present"


def assert_absent(text, arg, _case):
    return arg not in text, f"substring {arg!r} absent"


def assert_regex(text, arg, _case):
    return bool(re.search(arg, text, re.MULTILINE)), f"regex /{arg}/ matches"


def assert_row_in_section(text, arg, _case):
    section_no, row_id = arg.split(None, 1)
    start, end = _section_span(text, section_no)
    if start < 0:
        return False, f"section {section_no} header not found"
    row = _find_row(text[start:end], row_id.strip())
    return row is not None, f"row {row_id.strip()} under section {section_no}"


def assert_cell(text, arg, _case):
    row_id, col, value = arg.split(None, 2)
    row = _find_row(text, row_id)
    if row is None:
        return False, f"row {row_id} not found (cell check)"
    headers = _header_cells(text, text.index(row))
    cells = _row_cells(row)
    if col not in headers:
        return False, f"column {col!r} not in header {headers}"
    idx = headers.index(col)
    if idx >= len(cells):
        return False, f"row {row_id} has no cell at column {col}"
    actual = cells[idx]
    return value in actual, f"{row_id}.{col} == {value!r} (got {actual!r})"


def assert_detail_order(text, arg, _case):
    row_id = arg.strip()
    # detail bullet begins "- **<ID>** - ..." and runs to the next "- **" bullet
    bullet_re = re.compile(
        rf"-\s*\*\*{re.escape(row_id)}\*\*.*?(?=\n-\s*\*\*|\Z)", re.DOTALL
    )
    m = bullet_re.search(text)
    if m is None:
        return False, f"detail bullet for {row_id} not found"
    body = m.group(0)
    # positions of the four parts; absent parts skip
    order_keys = [
        ("closure", re.compile(r"\*\*CLOSED\s+\d{4}-\d{2}-\d{2}")),
        ("verify", re.compile(r"\*\*Verify-still-open:\*\*")),
        ("spawn", re.compile(r"(Spawned-from|Spawns):")),
    ]
    positions = []
    for name, rx in order_keys:
        mm = rx.search(body)
        if mm:
            positions.append((name, mm.start()))
    ok = positions == sorted(positions, key=lambda p: p[1])
    # closure (if present) must be at/near the start; verify before spawn
    order_names = [p[0] for p in positions]
    if "closure" in order_names and order_names[0] != "closure":
        ok = False
    if "verify" in order_names and "spawn" in order_names:
        ok = ok and order_names.index("verify") < order_names.index("spawn")
    return ok, f"detail parts for {row_id} in order {order_names or '(none)'}"


def assert_unchanged_from(text, arg, case_dir):
    baseline = (case_dir / arg).read_text(encoding="utf-8")
    return text == baseline, f"result byte-identical to {arg} (no write happened)"


HANDLERS = {
    "contains": assert_contains,
    "absent": assert_absent,
    "regex": assert_regex,
    "row_in_section": assert_row_in_section,
    "cell": assert_cell,
    "detail_order": assert_detail_order,
    "unchanged_from": assert_unchanged_from,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check unforget behavioral assertions.")
    parser.add_argument("--case", required=True, help="Case directory")
    parser.add_argument("--result", default=None, help="Produced result.md (default <case>/result.md)")
    args = parser.parse_args()

    case_dir = Path(args.case)
    assertions_path = case_dir / "assertions.txt"
    if not assertions_path.exists():
        print(f"check_behavioral: no assertions.txt in {case_dir}", file=sys.stderr)
        return 2

    result_path = Path(args.result) if args.result else case_dir / "result.md"
    if not result_path.exists():
        print(
            f"check_behavioral: result not found: {result_path}\n"
            f"  Run the case first (see tests/behavioral/README.md) so the LLM "
            f"produces it, then re-check.",
            file=sys.stderr,
        )
        return 2

    text = result_path.read_text(encoding="utf-8")
    failures = 0
    total = 0
    for raw in assertions_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        total += 1
        kind, _, arg = line.partition(" ")
        handler = HANDLERS.get(kind)
        if handler is None:
            print(f"FAIL  unknown assertion kind: {kind!r}")
            failures += 1
            continue
        try:
            ok, detail = handler(text, arg.strip(), case_dir)
        except Exception as e:  # a malformed assertion should fail loudly, not crash the suite
            ok, detail = False, f"assertion error: {e}"
        print(f"{'PASS' if ok else 'FAIL'}  {kind}: {detail}")
        if not ok:
            failures += 1

    print(f"\n{total - failures}/{total} assertions passed in {case_dir.name}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
