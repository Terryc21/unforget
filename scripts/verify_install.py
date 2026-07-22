#!/usr/bin/env python3
"""Verify an unforget install is intact and report the recall-trigger status.

Two concerns, one command, both feeding `/unforget --version`:

  1. Install integrity. The refactored skill (v0.2+) is a thin SKILL.md router
     that delegates to `reference/*.md` on demand and to `scripts/*.py` for
     deterministic work. If those companion files did not travel with the
     install (someone copied only SKILL.md, a partial clone, a broken symlink),
     the router silently fails the moment it tries to read a reference file.
     This check confirms every companion file the router depends on is
     reachable from the skill root, turning an undefined silent failure into a
     one-line diagnosis.

  2. Recall trigger. unforget only auto-activates on "what's deferred?" style
     questions when the project's CLAUDE.md / AGENTS.md carries a "Deferred Work
     Index" block pointing at UNFORGET.md. Without it, a populated ledger sits
     invisible and the skill looks broken when it is working as designed. This
     check reports whether that trigger is installed for the given project.

Usage:
  python3 verify_install.py --skill-root <dir> [--project-root <dir>]
  python3 verify_install.py --help

  --skill-root    Directory holding SKILL.md (the skill's own install dir).
  --project-root  Optional. If given, scan it for the recall-trigger block in
                  CLAUDE.md / AGENTS.md (and ./.claude/CLAUDE.md). Omit to skip
                  the recall check (integrity-only).

Output (stdout, JSON):
  {
    "skill_root": "<input>",
    "version": "1.0.0"|null,
    "integrity_ok": true|false,
    "companion_files_present": ["reference/commands.md", ...],
    "companion_files_missing": [...],
    "recall_checked": true|false,
    "recall_trigger_present": true|false|null,
    "recall_trigger_source": "CLAUDE.md"|".claude/CLAUDE.md"|"AGENTS.md"|null,
    "advisory": "<one-line summary for the LLM caller>"
  }

Exit codes:
  0  integrity OK (recall status is informational, never fails the command)
  1  integrity FAILED (one or more companion files missing)
  2  usage error / skill root not found
"""
import argparse
import json
import re
import sys
from pathlib import Path

# Companion files the refactored router depends on. If the router's delegation
# table in SKILL.md grows a new reference file or script, add it here so the
# integrity check keeps pace with what the prose actually reads.
REQUIRED_COMPANIONS = [
    "reference/format.md",
    "reference/init.md",
    "reference/surfaces.md",
    "reference/promotion.md",
    "reference/commands.md",
    "scripts/check_format_version.py",
    "scripts/scan_surfaces.py",
    "scripts/dedup_findings.py",
    "scripts/encode_project_path.py",
    "scripts/prune_backups.py",
]

VERSION_RE = re.compile(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)", re.MULTILINE)

# The recall trigger is a "Deferred Work Index" section pointing at UNFORGET.md.
# We match on both cues so a lightly reworded block still counts.
RECALL_MARKERS = ("Deferred Work Index", "UNFORGET.md")
RECALL_SOURCES = ["CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md"]


def read_version(skill_root: Path) -> str | None:
    skill_md = skill_root / "SKILL.md"
    if not skill_md.exists():
        return None
    match = VERSION_RE.search(skill_md.read_text(encoding="utf-8", errors="replace"))
    return match.group(1) if match else None


def check_integrity(skill_root: Path) -> tuple[list[str], list[str]]:
    present, missing = [], []
    for rel in REQUIRED_COMPANIONS:
        (present if (skill_root / rel).exists() else missing).append(rel)
    return present, missing


def check_recall(project_root: Path) -> tuple[bool, str | None]:
    for rel in RECALL_SOURCES:
        candidate = project_root / rel
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8", errors="replace")
        if all(marker in text for marker in RECALL_MARKERS):
            return True, rel
    return False, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify unforget install integrity and recall-trigger status."
    )
    parser.add_argument("--skill-root", required=True, help="Directory holding SKILL.md")
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project dir to scan for the recall-trigger block (optional)",
    )
    args = parser.parse_args()

    skill_root = Path(args.skill_root)
    if not (skill_root / "SKILL.md").exists():
        print(
            json.dumps({"error": f"SKILL.md not found under skill root: {skill_root}"}),
            file=sys.stderr,
        )
        return 2

    version = read_version(skill_root)
    present, missing = check_integrity(skill_root)
    integrity_ok = not missing

    if args.project_root is not None:
        recall_present, recall_source = check_recall(Path(args.project_root))
        recall_checked = True
    else:
        recall_present, recall_source, recall_checked = None, None, False

    if not integrity_ok:
        advisory = (
            f"install incomplete: {len(missing)} companion file(s) unreachable "
            f"({', '.join(missing)}); the router will fail when it delegates to a "
            "missing file — reinstall or repair the skill directory"
        )
    elif recall_checked and not recall_present:
        advisory = (
            "install intact, but no Deferred Work Index block found in the "
            "project's CLAUDE.md/AGENTS.md — deferred-work questions will NOT "
            "auto-route to unforget; run /unforget init to add the recall trigger"
        )
    elif recall_checked and recall_present:
        advisory = f"install intact; recall trigger installed in {recall_source}"
    else:
        advisory = "install intact; recall trigger not checked (no --project-root given)"

    result = {
        "skill_root": str(skill_root),
        "version": version,
        "integrity_ok": integrity_ok,
        "companion_files_present": present,
        "companion_files_missing": missing,
        "recall_checked": recall_checked,
        "recall_trigger_present": recall_present,
        "recall_trigger_source": recall_source,
        "advisory": advisory,
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0 if integrity_ok else 1


if __name__ == "__main__":
    sys.exit(main())
