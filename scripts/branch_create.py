#!/usr/bin/env python3
r"""Atomically create a child unforget ledger (the `branch` command's deterministic half).

Implements the atomic child-creation of the branching model (see
reference/branching.md §8, from the Branching Model design spec §8-#4). Creating a
child ledger does three things TOGETHER, OR NONE — because those three drifting
apart IS the split-brain failure this exists to prevent (a child ledger the
parent/registry lost track of):

  1. SCAFFOLD the child's header (§4b) — axis, discipline, parent back-pointer, and
     (lifespan only) the death condition — plus its own format marker and empty
     section tables.
  2. WRITE the parent's pointer row (§4a) — exactly one row, pointer shape, never a
     copy of child rows.
  3. REGISTER the child (§5) via registry.py — name/path/role/axis/discipline/
     parent/death, so list/scan/import re-read where it lives.

The AXIS DECISION (which axis, is it a human actor, would it balloon the task) is
LLM judgment following the §3 cascade — NOT this script. This script is given the
axis and does the atomic write + the mechanical guards.

Atomicity: every artifact's content is built and every guard is checked BEFORE any
write. On a non-dry-run success all three are written, child first; if a later
write fails, the already-written files are rolled back so no half-branched state
remains. --dry-run reports the three artifacts and writes nothing.

Usage:
  python3 branch_create.py --dir <ledger-dir> --name <child-name> \
      --axis <actor|lifespan|domain> --parent <parent-file> \
      [--discipline "<one line>"] [--death "<condition>"] \
      [--target SOMEDAY] [--parent-id U18] [--actor-is-human] [--dry-run]

  --dir         the ledger directory (holds README.md registry + the ledgers)
  --name        the child ledger's name (also the filename stem: <name>.md unless
                --name already ends in .md)
  --axis        actor | lifespan | domain
  --parent      the parent ledger's filename (e.g. UNFORGET.md), relative to --dir
  --discipline  one-line discipline description for the child header/registry
  --death       REQUIRED for --axis=lifespan: when the child is archived/deleted
  --target      Target cell for the parent pointer row (default SOMEDAY)
  --parent-id   force the pointer row's id (default: next U-NN in the parent)
  --actor-is-human  assert (for --axis=actor) the actor is a HUMAN; without it an
                actor branch returns needs_confirmation and writes nothing
  --dry-run     report artifacts, write nothing

Output (stdout, JSON):
  {
    "ok": true|false,
    "dry_run": true|false,
    "child_path": "<path>"|null,
    "parent_path": "<path>"|null,
    "pointer_id": "U-NN"|null,
    "registered": true|false,
    "needs_confirmation": "<question>"|null,
    "refusal": "<reason>"|null,
    "artifacts": ["child header", "parent pointer row", "registry entry"],
    "advisory": "<one-line next step>"
  }

Exit codes:
  0  ok (created, or dry-run reported)
  1  refused (a guard failed) OR needs confirmation (actor-not-confirmed-human)
  2  usage error / dir or parent not found
"""
import argparse
import json
import re
import sys
from pathlib import Path

# registry.py lives beside this script; import it for the registry read/append so
# there is ONE registry writer, not two divergent implementations.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry  # type: ignore  # noqa: E402

FORMAT_MARKER = "<!-- unforget-format: v2 -->"
AXES = {"actor", "lifespan", "domain"}
ROW_ID_RE = re.compile(r"^\|\s*U-?(\d+)\s*\|", re.MULTILINE)

# The four canonical sections a standard child carries. A lifespan child with its
# own discipline (a cap/evict sprint) may diverge — but the scaffold starts from
# the standard shape; the user edits the discipline in afterward.
STANDARD_SECTIONS = [
    "1. Paused plans",
    "2. Session spillover",
    "3. Audit findings",
    "4. User-reported",
]

# The canonical 10-column header (must satisfy check_header_order.py).
HEADER_ROW = ("| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | "
              "ROI | Blast Radius | Fix Effort | Status |")
SEP_ROW = "|---|---|---|---|---|---|---|---|---|---|"


def next_pointer_id(parent_text: str) -> str:
    """Return the next U-NN id not already used in the parent."""
    nums = [int(m.group(1)) for m in ROW_ID_RE.finditer(parent_text)]
    n = (max(nums) + 1) if nums else 1
    return f"U{n}"


def build_child(name_stem: str, axis: str, parent_name: str,
                discipline: str | None, death: str | None) -> str:
    """Scaffold the child ledger content (§4b/§4c)."""
    disc = discipline or "(same 10-column format as the parent; edit this line to state the child's discipline)"
    lines = [
        FORMAT_MARKER,
        f"# {name_stem} — deferred-work ledger (child of {parent_name})",
        "",
        "## Why this file is different (read before adding a row)",
        "",
        f"- **Axis:** {axis} — this is why the work earned its own ledger, not a row or section in the parent.",
        f"- **Discipline:** {disc}",
        f"- **Parent:** `{parent_name}` (owns this file's pointer row). An item lives in exactly ONE ledger.",
    ]
    if axis == "lifespan":
        lines.append(f"- **Death condition:** {death} "
                     "— when this holds, the whole file is archived or deleted. "
                     "A lifespan child must not outlive its purpose.")
    lines += ["", "---", ""]
    for section in STANDARD_SECTIONS:
        lines += [f"## {section}", "", HEADER_ROW, SEP_ROW, ""]
    return "\n".join(lines) + "\n"


def build_pointer_row(pointer_id: str, target: str, child_name: str,
                      axis: str) -> str:
    """The parent's single pointer row (§4a) — pointer shape, — filler."""
    finding = (f"→ child ledger `{child_name}` ({axis} axis). This row is a POINTER; "
               f"the live rows live there. Do not track that work here.")
    status = f"→ see {child_name}"
    return (f"| {pointer_id} | {target} | {finding} | — | — | — | — | — | — | {status} |")


def insert_pointer_row(parent_text: str, pointer_row: str) -> str:
    """Append the pointer row under Section 1 (Paused plans) if present, else EOF.

    Paused plans is where a pointer to another tracking surface belongs; if the
    parent lacks that section (a non-standard parent) fall back to appending at
    end-of-file so the row is never lost.
    """
    lines = parent_text.splitlines()
    # find the Section 1 header, then the last table row under it before the next
    # '## ' header, and insert after it.
    sec1 = None
    for i, line in enumerate(lines):
        if re.match(r"^#+\s.*1\. Paused plans", line):
            sec1 = i
            break
    if sec1 is None:
        return parent_text.rstrip() + "\n" + pointer_row + "\n"
    # scan forward to the end of this section
    end = len(lines)
    for j in range(sec1 + 1, len(lines)):
        if re.match(r"^##\s", lines[j]):
            end = j
            break
    # insert after the last non-blank line within the section
    insert_at = end
    while insert_at - 1 > sec1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, pointer_row)
    return "\n".join(lines) + ("\n" if parent_text.endswith("\n") else "")


def run(args) -> dict:
    result = {
        "ok": False, "dry_run": args.dry_run, "child_path": None,
        "parent_path": None, "pointer_id": None, "registered": False,
        "needs_confirmation": None, "refusal": None,
        "artifacts": ["child header", "parent pointer row", "registry entry"],
        "advisory": "",
    }

    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        result["refusal"] = f"not a directory: {dir_path}"
        return result

    if args.axis not in AXES:
        result["refusal"] = f"unknown axis {args.axis!r} (want actor|lifespan|domain)"
        return result

    name_stem = args.name[:-3] if args.name.endswith(".md") else args.name
    child_name = f"{name_stem}.md"
    child_path = dir_path / child_name
    parent_path = dir_path / args.parent
    result["child_path"] = str(child_path)
    result["parent_path"] = str(parent_path)

    # --- guards (refuse rather than half-create) ---------------------------

    if not parent_path.exists():
        result["refusal"] = f"parent ledger not found: {parent_path}"
        return result

    if child_path.exists():
        result["refusal"] = f"a file already exists at {child_path}; refusing to overwrite"
        return result

    # name already registered? (§8 guard)
    reg = registry.read_registry(dir_path)
    existing = {(l.get("name") or "").lower() for l in reg.get("ledgers", [])}
    if name_stem.lower() in existing or child_name.lower() in existing:
        result["refusal"] = f"{name_stem!r} is already a registered ledger; no duplicate ledgers"
        return result

    # lifespan needs a death condition (§4c)
    if args.axis == "lifespan" and not (args.death and args.death.strip()):
        result["refusal"] = ("--axis=lifespan requires --death: a lifespan child MUST declare "
                             "when it is archived or deleted (else it becomes a second permanent backlog)")
        return result

    # actor must be a human (§2) — confirmed via --actor-is-human, else ask
    if args.axis == "actor" and not args.actor_is_human:
        result["needs_confirmation"] = (
            "actor axis is HUMANS ONLY. Confirm a different HUMAN acts on this work "
            "(re-run with --actor-is-human). A machine/automation actor is a Target "
            "value or status tag inside the actionable ledger, NOT a new ledger.")
        return result

    # same-discipline warning for lifespan/domain (actor is exempt — earns a file
    # at identical discipline). Advisory only; does not block.
    if args.axis in ("lifespan", "domain") and not (args.discipline and args.discipline.strip()):
        result["advisory"] = ("no --discipline given: a same-discipline split is usually a SECTION, "
                              "not a ledger (§7). State the child's distinct discipline, or reconsider.")

    # --- build all artifact content BEFORE writing anything ----------------

    parent_text = parent_path.read_text(encoding="utf-8", errors="replace")
    pointer_id = args.parent_id or next_pointer_id(parent_text)
    result["pointer_id"] = pointer_id

    child_content = build_child(name_stem, args.axis, args.parent,
                                args.discipline, args.death)
    pointer_row = build_pointer_row(pointer_id, args.target, child_name, args.axis)
    new_parent_text = insert_pointer_row(parent_text, pointer_row)

    reg_ledgers = list(reg.get("ledgers", []))
    reg_ledgers.append({
        "name": name_stem,
        "path": child_name,
        "role": f"{args.axis}-child",
        "axis": args.axis,
        "discipline": (args.discipline or None),
        "parent": args.parent,
        "death": (args.death or None),
    })

    if args.dry_run:
        result["ok"] = True
        result["advisory"] = (result["advisory"] + " " if result["advisory"] else "") + (
            f"DRY RUN — would write child {child_name}, pointer {pointer_id} in {args.parent}, "
            f"and register {name_stem}. Nothing written.")
        return result

    # --- atomic write: child → parent → registry, roll back on failure -----

    written: list[Path] = []
    try:
        child_path.write_text(child_content, encoding="utf-8")
        written.append(child_path)

        parent_backup = parent_text  # keep original for rollback
        parent_path.write_text(new_parent_text, encoding="utf-8")
        written.append(parent_path)  # (rolled back to backup, not deleted)

        registry.write_registry(dir_path, reg.get("global", {}), reg_ledgers)
        result["registered"] = True
    except OSError as exc:
        # roll back: delete the freshly-created child, restore the parent text.
        for p in written:
            try:
                if p == child_path:
                    p.unlink(missing_ok=True)
                elif p == parent_path:
                    p.write_text(parent_backup, encoding="utf-8")
            except OSError:
                pass
        result["ok"] = False
        result["refusal"] = f"write failed ({exc}); rolled back — no half-branched state"
        return result

    result["ok"] = True
    result["advisory"] = (
        f"Child {name_stem} created at {child_name}, pointer {pointer_id} in {args.parent}, "
        f"registered. Add rows with /unforget add --ledger={name_stem}.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomically create a child unforget ledger.")
    parser.add_argument("--dir", required=True, help="ledger directory (holds README.md + ledgers)")
    parser.add_argument("--name", required=True, help="child ledger name / filename stem")
    parser.add_argument("--axis", required=True, help="actor | lifespan | domain")
    parser.add_argument("--parent", required=True, help="parent ledger filename, relative to --dir")
    parser.add_argument("--discipline", default=None, help="one-line discipline description")
    parser.add_argument("--death", default=None, help="death condition (required for lifespan)")
    parser.add_argument("--target", default="⚪ SOMEDAY", help="Target cell for the pointer row")
    parser.add_argument("--parent-id", default=None, help="force the pointer row id (default next U-NN)")
    parser.add_argument("--actor-is-human", action="store_true",
                        help="(actor axis) assert the actor is a human")
    parser.add_argument("--dry-run", action="store_true", help="report artifacts, write nothing")
    args = parser.parse_args()

    result = run(args)
    json.dump(result, sys.stdout); sys.stdout.write("\n")
    if result["refusal"] or result["needs_confirmation"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
