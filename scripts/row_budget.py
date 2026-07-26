#!/usr/bin/env python3
r"""Row-length discipline: flag over-budget table cells and split them losslessly.

Implements the row-length rule (see reference/format.md § Row-length discipline,
from the Maintenance & Integrity design spec §2). A ledger row is meant to be a
one-line INDEX; the history/context/verification narration belongs in a detail
block BELOW the tables, not fused into an ever-growing Finding or Status cell. The
2026-07-25 failure was a ~155KB ledger with multi-KB rows whose Reads truncated and
MISLED the reader — the exact thing a bounded index prevents.

Two modes:

  check  — flag every table cell (Finding, Status) over the char budget. Read-only.
           This is the `scan`/`verify` char-budget lint, formalized and configurable.
  split  — for an over-budget row, produce a BOUNDED index row + a detail-block
           bullet holding the overflow. LOSSLESS by construction: the tool never
           deletes content — it moves the full original cell verbatim into the
           detail block and leaves a short headline + pointer in the table. Emits a
           unified plan (old row → new row + detail bullet) for --dry-run, or writes
           it with --apply.

The BUDGET is a soft index budget (default 400 chars/cell), registry-configurable
via `row_char_budget` (falls back to the default). The hard rule from the spec:
**the budget moves history to the detail block; it NEVER deletes it.** A split that
can't be shown to preserve every character of the original cell refuses.

Usage:
  # flag over-budget cells (read-only):
  python3 row_budget.py check --file <UNFORGET.md> [--budget N] [--dir <ledger-dir>]

  # plan/apply a lossless split of one row's over-budget cell(s):
  python3 row_budget.py split --file <UNFORGET.md> --id U5 [--budget N] \
      [--headline "<optional one-line summary>"] [--apply]

  python3 row_budget.py --help

check output (stdout, JSON):
  {
    "file": "<path>", "budget": N,
    "over_budget": [ {"id": "U5", "cell": "finding"|"status", "chars": M}, ... ],
    "count": K, "advisory": "<one-line>"
  }

split output (stdout, JSON):
  {
    "id": "U5", "budget": N, "applied": true|false,
    "lossless": true|false,        # every char of the original cell is preserved
    "new_row": "<the bounded index row>",
    "detail_bullet": "<the '- **U5** - ...' block bullet>",
    "detail_section": "### Detail - <section>",
    "refusal": "<reason>"|null,
    "advisory": "<one-line>"
  }

Exit codes:
  check: 0 no rows over budget · 1 ≥1 over budget · 2 usage error
  split: 0 planned/applied · 1 refused (not over budget / not lossless / id absent) · 2 usage
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_status  # type: ignore  # noqa: E402
try:
    import registry  # type: ignore
except ImportError:  # registry is optional for the budget read
    registry = None

DEFAULT_BUDGET = 400
SECTION_RE = re.compile(r"^##\s+(.*)$")
DETAIL_HEADER_RE = re.compile(r"^###\s+Detail\b", re.IGNORECASE)


def cells_of(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def finding_cell(row: str) -> str:
    c = cells_of(row)
    return c[2] if len(c) >= 3 else ""


def status_cell(row: str) -> str:
    c = cells_of(row)
    return c[-1] if c else ""


def read_budget(args) -> int:
    if getattr(args, "budget", None):
        return args.budget
    d = getattr(args, "dir", None)
    if d and registry is not None:
        try:
            reg = registry.read_registry(Path(d))
            val = (reg.get("global") or {}).get("row_char_budget")
            if val is not None:
                return int(str(val).strip())
        except (ValueError, TypeError, OSError):
            pass
    return DEFAULT_BUDGET


# --- check -----------------------------------------------------------------

def check(text: str, budget: int) -> list[dict]:
    over = []
    for line in text.splitlines():
        if not parse_status.ROW_ID_RE.match(line):
            continue
        rid = (parse_status.ROW_ID_RE.match(line).group(1))
        for name, val in (("finding", finding_cell(line)), ("status", status_cell(line))):
            if len(val) > budget:
                over.append({"id": rid, "cell": name, "chars": len(val)})
    return over


# --- split (lossless index + detail block) ---------------------------------

def find_row(text: str, rid: str) -> tuple[int, str] | None:
    for i, line in enumerate(text.splitlines()):
        m = parse_status.ROW_ID_RE.match(line)
        if m and m.group(1) == rid:
            return i, line
    return None


def section_of(lines: list[str], row_index: int) -> str:
    """The nearest '## ' section header above the row (for the detail block name)."""
    for i in range(row_index, -1, -1):
        m = SECTION_RE.match(lines[i])
        if m:
            return m.group(1).strip()
    return "Session spillover"


def make_headline(finding: str, budget: int, override: str | None) -> str:
    """A bounded one-line finding summary for the index row.

    If the caller supplies --headline, use it (the LLM's judgment call). Otherwise
    derive a mechanical, lossless-safe headline: the first sentence (up to the first
    '. ' or ' — ' or a hard cap), with an explicit pointer to the detail block. The
    FULL original finding is preserved in the detail bullet, so truncating the
    headline loses nothing — the pointer says where the rest lives.
    """
    if override:
        head = override.strip()
    else:
        # first natural break, else a hard word-boundary cap under the budget.
        cut = len(finding)
        for sep in (". ", " — ", "; "):
            j = finding.find(sep)
            if 0 < j < cut:
                cut = j
        cap = budget - 40  # leave room for the pointer
        if cut > cap:
            cut = finding.rfind(" ", 0, cap)
            if cut <= 0:
                cut = cap
        head = finding[:cut].rstrip(" .;—")
        # Strip a leading markdown emphasis marker (`**bold**`, `*em*`) so a
        # truncated headline doesn't open bold it never closes (a render artifact,
        # not information loss — the full text is verbatim in the block). Also drop
        # any dangling unmatched `**` left by the cut.
        head = head.lstrip("*_ ")
        if head.count("**") % 2:
            head = head.replace("**", "")
    return f"{head} → see detail block **{{id}}**"


def build_index_row(orig_row: str, rid: str, headline: str) -> str:
    """Replace the Finding cell with the bounded headline; keep every other cell.

    The Status cell KEEPS its @status token (the machine-readable status must stay in
    the table for list/archive), but any long narration after the token moves to the
    detail block. We only trim the Status narration, never the token.
    """
    # Split the row into leading '', cells..., trailing ''.
    parts = orig_row.rstrip("\n").split("|")
    # parts[0] is '' (leading pipe), parts[-1] is '' (trailing pipe).
    # Table columns are parts[1:-1]. Finding is index 3 in that 1-based pipe layout:
    # parts = ['', ' # ', ' Target ', ' Finding ', ... , ' Status ', '']
    if len(parts) < 5:
        return orig_row  # not a well-formed row; leave untouched
    # Finding is parts[3]; Status is parts[-2].
    parts[3] = f" {headline.replace('{id}', rid)} "
    # Trim Status narration to just the token + a one-line current status.
    status_val = parts[-2].strip()
    tok = re.match(r"(`?@status:[a-z-]+`?(?:\s*`?@verified:[a-z-]+`?)?)", status_val)
    if tok:
        remainder = status_val[tok.end():].strip()
        if len(status_val) > 200 and remainder:
            # keep the token + first clause of the remainder; rest goes to the block.
            first = re.split(r"[.;]", remainder, maxsplit=1)[0].strip()
            parts[-2] = f" {tok.group(1)} {first} → history in detail block "
    return "|".join(parts)


def build_detail_bullet(rid: str, finding: str, status_val: str) -> str:
    """A detail-block bullet holding the FULL original cell content, verbatim.

    Format per reference/format.md § Detail blocks: `- **<ID>** - <body>`. We move
    the complete original Finding (and the Status narration beyond its token) so no
    character is lost.
    """
    body = finding.strip()
    # append the Status narration (everything after the @status/@verified tokens)
    tok = re.match(r"`?@status:[a-z-]+`?(?:\s*`?@verified:[a-z-]+`?)?", status_val.strip())
    narration = status_val.strip()[tok.end():].strip() if tok else status_val.strip()
    if narration:
        body = f"{body}\n\n  **Status history:** {narration}"
    return f"- **{rid}** - {body}"


def losslessness(original_finding: str, original_status: str,
                 detail_bullet: str, index_row: str) -> bool:
    """Verify every char of the original cells survives in row+bullet.

    The check: the original Finding text and the original Status narration (beyond
    its token) must each appear, contiguous, in the detail bullet. The index row may
    truncate/summarize freely — but only because the full text is provably in the
    block. If the full original text is NOT present in the bullet, the split would
    lose information and must refuse.
    """
    fnd = original_finding.strip()
    if fnd and fnd not in detail_bullet:
        return False
    tok = re.match(r"`?@status:[a-z-]+`?(?:\s*`?@verified:[a-z-]+`?)?", original_status.strip())
    narration = original_status.strip()[tok.end():].strip() if tok else original_status.strip()
    if narration and narration not in detail_bullet:
        return False
    return True


def split_row(text: str, rid: str, budget: int, headline: str | None) -> dict:
    result = {"id": rid, "budget": budget, "applied": False, "lossless": False,
              "new_row": None, "detail_bullet": None, "detail_section": None,
              "refusal": None, "advisory": ""}
    found = find_row(text, rid)
    if not found:
        result["refusal"] = f"row {rid} not found"
        return result
    idx, row = found
    finding = finding_cell(row)
    status_val = status_cell(row)
    if len(finding) <= budget and len(status_val) <= budget:
        result["refusal"] = (f"row {rid} is within budget "
                             f"(finding {len(finding)}, status {len(status_val)} ≤ {budget}); "
                             "nothing to split")
        return result

    lines = text.splitlines()
    section = section_of(lines, idx)
    head = make_headline(finding, budget, headline)
    new_row = build_index_row(row, rid, head)
    bullet = build_detail_bullet(rid, finding, status_val)

    lossless = losslessness(finding, status_val, bullet, new_row)
    result.update({
        "lossless": lossless,
        "new_row": new_row,
        "detail_bullet": bullet,
        "detail_section": f"### Detail - {section}",
    })
    if not lossless:
        result["refusal"] = ("split would not preserve the full original cell text in the "
                             "detail bullet — refusing (the budget moves history, never deletes it)")
        return result
    result["advisory"] = (f"row {rid}: index row bounded to a headline; full content moved to "
                          f"the '{section}' detail block. Lossless.")
    return result


def apply_split(path: Path, text: str, rid: str, plan: dict) -> bool:
    """Write the split: replace the row in place, append the bullet under the
    matching '### Detail - <section>' block (create it if absent). Idempotent enough
    for a one-shot apply; the caller has already validated losslessness."""
    lines = text.splitlines()
    found = find_row(text, rid)
    if not found:
        return False
    idx, _ = found
    lines[idx] = plan["new_row"]

    section_header = plan["detail_section"]
    # find the detail block; append the bullet at its end, else create it at EOF.
    detail_idx = None
    for i, line in enumerate(lines):
        if line.strip() == section_header:
            detail_idx = i
            break
    if detail_idx is None:
        lines += ["", section_header, "", plan["detail_bullet"]]
    else:
        # insert after the last bullet line of that block (before the next '## '/'### ')
        end = len(lines)
        for j in range(detail_idx + 1, len(lines)):
            if re.match(r"^(##|###)\s", lines[j]):
                end = j
                break
        insert_at = end
        while insert_at - 1 > detail_idx and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, plan["detail_bullet"])

    path.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Row-length discipline: flag and split over-budget rows.")
    sub = parser.add_subparsers(dest="action", required=True)

    c = sub.add_parser("check", help="flag table cells over the char budget (read-only)")
    c.add_argument("--file", required=True)
    c.add_argument("--budget", type=int, default=None)
    c.add_argument("--dir", default=None, help="ledger dir (reads row_char_budget from the registry)")

    s = sub.add_parser("split", help="plan/apply a lossless index+detail-block split of one row")
    s.add_argument("--file", required=True)
    s.add_argument("--id", required=True, help="the row ID to split")
    s.add_argument("--budget", type=int, default=None)
    s.add_argument("--dir", default=None)
    s.add_argument("--headline", default=None, help="optional one-line finding summary for the index row")
    s.add_argument("--apply", action="store_true", help="write the split (default: dry-run plan)")

    args = parser.parse_args()
    target = Path(args.file)
    if not target.exists():
        print(json.dumps({"error": f"file not found: {target}"}), file=sys.stderr)
        return 2
    text = target.read_text(encoding="utf-8", errors="replace")
    budget = read_budget(args)

    if args.action == "check":
        over = check(text, budget)
        result = {
            "file": str(target), "budget": budget, "over_budget": over,
            "count": len(over),
            "advisory": ("all rows within the index budget" if not over else
                         f"{len(over)} cell(s) over the {budget}-char index budget; "
                         "split with `row_budget.py split --id <ID>`"),
        }
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 1 if over else 0

    # split
    plan = split_row(text, args.id, budget, args.headline)
    if plan["refusal"]:
        json.dump(plan, sys.stdout); sys.stdout.write("\n")
        return 1
    if args.apply:
        ok = apply_split(target, text, args.id, plan)
        plan["applied"] = ok
        if not ok:
            plan["refusal"] = "apply failed (row vanished between plan and write)"
            json.dump(plan, sys.stdout); sys.stdout.write("\n")
            return 1
        plan["advisory"] += " (applied)"
    json.dump(plan, sys.stdout); sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
