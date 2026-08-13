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

  3. Version reconciliation. The version is declared in three places (SKILL.md
     frontmatter, .claude-plugin/plugin.json, the newest changelog heading) and
     nothing used to compare them — so the plugin manifest sat FIVE releases
     stale without any check noticing (measured 2026-08-13). Drift is ADVISORY,
     not a failure: a wrong manifest version misreports what is installed, but
     unlike a missing companion file it does not break the router. Reported in
     `versions_in_sync` / `declared_versions` and surfaced in the advisory.

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
    "versions_in_sync": true|false,
    "declared_versions": {"skill_md": "2.6.0", "plugin_manifest": "2.6.0",
                          "changelog": "2.6.0"},   # null == that source declares none
    "integrity_ok": true|false,
    "companion_files_present": ["reference/commands.md", ...],
    "companion_files_missing": [...],
    "recall_checked": true|false,
    "recall_trigger_present": true|false|null,
    "recall_trigger_source": "CLAUDE.md"|".claude/CLAUDE.md"|"AGENTS.md"|null,
    "advisory": "<one-line summary for the LLM caller>"
  }

Exit codes:
  0  integrity OK (recall status AND version drift are informational, never fail
     the command — see concern 3 above)
  1  integrity FAILED (one or more companion files missing)
  2  usage error / skill root not found
"""

from __future__ import annotations
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
    # format v2 reference specs
    "reference/status.md",
    "reference/registry.md",
    "reference/verify.md",
    "reference/deferral-gate.md",
    "reference/branching.md",
    "reference/skill-handoffs.md",
    # v1 helpers
    "scripts/check_format_version.py",
    "scripts/scan_surfaces.py",
    "scripts/dedup_findings.py",
    "scripts/encode_project_path.py",
    "scripts/prune_backups.py",
    # format v2 helpers
    "scripts/parse_status.py",
    "scripts/registry.py",
    "scripts/verify_ledger.py",
    "scripts/defer_tally.py",
    "scripts/branch_create.py",
    "scripts/recall_block.py",
    "scripts/import_drift.py",
    "scripts/row_budget.py",
    "scripts/companions.py",
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


# The version is declared in more than one place, and nothing used to reconcile
# them. Measured 2026-08-13 on a real install: SKILL.md frontmatter said 2.6.0
# and the changelog's newest entry said 2.6.0, but `.claude-plugin/plugin.json`
# still said 2.1.0 -- FIVE releases stale, silently, because the only reader
# (read_version, above) looks at the frontmatter alone. Same doc-vs-code drift
# class as the changelog-ahead-of-code gap and the stale test golden, all three
# found in one session. This check subjects the skill's OWN metadata to the
# "measure, don't cite" rule it applies to everything else.
CHANGELOG_RE = re.compile(r"^###\s+v([0-9]+\.[0-9]+\.[0-9]+)", re.MULTILINE)


def read_declared_versions(skill_root: Path) -> dict:
    """Every place a version is declared, keyed by source. Absent -> None.

    A source that does not exist reports None rather than being omitted, so a
    missing plugin manifest stays visible instead of quietly shrinking the set
    of things being compared.
    """
    versions: dict[str, str | None] = {"skill_md": read_version(skill_root)}

    manifest = skill_root / ".claude-plugin" / "plugin.json"
    manifest_version = None
    if manifest.exists():
        try:
            manifest_version = json.loads(
                manifest.read_text(encoding="utf-8", errors="replace")
            ).get("version")
        except (ValueError, OSError):
            manifest_version = None  # unparseable == undeclared, never a crash
    versions["plugin_manifest"] = manifest_version

    # Newest changelog heading in SKILL.md. Headings are newest-first, so the
    # FIRST match is the current release.
    skill_md = skill_root / "SKILL.md"
    changelog_version = None
    if skill_md.exists():
        match = CHANGELOG_RE.search(skill_md.read_text(encoding="utf-8", errors="replace"))
        changelog_version = match.group(1) if match else None
    versions["changelog"] = changelog_version

    return versions


def check_version_sync(skill_root: Path) -> tuple[bool, dict, str | None]:
    """Reconcile every declared version. Returns (in_sync, versions, complaint).

    Only sources that actually declare a version participate: an absent manifest
    or a changelog-less SKILL.md is not a mismatch, it is simply not a vote. A
    disagreement among those that DO declare one is the finding. SKILL.md's
    frontmatter is treated as canonical because it is what `read_version` (and
    therefore `/unforget --version`) already reports.
    """
    versions = read_declared_versions(skill_root)
    declared = {src: v for src, v in versions.items() if v}
    if len(set(declared.values())) <= 1:
        return True, versions, None

    canonical = versions.get("skill_md")
    offenders = [f"{src}={v}" for src, v in sorted(declared.items()) if v != canonical]
    complaint = (
        f"version drift: SKILL.md declares {canonical}, but {', '.join(offenders)}. "
        "Bring every declaration to the same value — a stale manifest ships the wrong "
        "version to anyone installing the plugin."
    )
    return False, versions, complaint


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
    versions_in_sync, declared_versions, version_complaint = check_version_sync(skill_root)

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
    elif not versions_in_sync:
        # Ranked above the recall lines but below missing companions: drift
        # misreports what is installed, while a missing companion breaks the
        # router outright.
        advisory = f"install intact, but {version_complaint}"
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
        "versions_in_sync": versions_in_sync,
        "declared_versions": declared_versions,
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
