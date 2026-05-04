#!/usr/bin/env python3
"""Scan a project root for deferred-work artifacts across the six unforget surfaces.

Implements the surface specification in `reference/surfaces.md`:
  Surface 1  — Deferred-named files (with redirect-pointer pre-check)
  Surface 1b — General documentation scanning (7 heuristics)
  Surface 2  — Audit-tool reports (radar-suite v3+, ESLint, etc.)
  Surface 3  — Plan files in project-local plan dirs
  Surface 4  — Code comments (TODO/FIXME/HACK/XXX/MIGRATION-NOTE/DEFERRED)
  Surface 5  — GitHub issues (skipped here; needs `gh` CLI; report state only)
  Surface 6  — Memory files (Claude Code, with meta-doc pre-check)

The script is read-only. It produces a JSON candidate list grouped by surface;
the LLM (or a downstream tool) decides what to import.

Universal exclusions: `archive`/`Archive` path segments, `.git/`, `node_modules/`,
`vendor/`, `Pods/`, files matching `*archive*.md` (case-insensitive).

Usage:
  python3 scan_surfaces.py --root <path>
  python3 scan_surfaces.py --root <path> --include-comments
  python3 scan_surfaces.py --help

Output (stdout, JSON):
  {
    "root": "<path>",
    "surfaces": {
      "deferred_named_files":   {"candidates": [...], "skipped": [...], "notes": [...]},
      "general_documentation":  {"candidates": [...], "notes": [...]},
      "audit_reports":          {"candidates": [...], "notes": [...]},
      "plan_files":             {"candidates": [...], "notes": [...]},
      "code_comments":          {"candidates": [...], "notes": [...]},
      "github_issues":          {"state": "skipped|empty|...", "notes": [...]},
      "memory_files":           {"candidates": [...], "notes": [...]}
    },
    "summary": {"total_candidates": N, "total_skipped": M}
  }

Exit codes: 0 on success, 2 on usage error.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

# Universal excludes
EXCLUDED_DIR_NAMES = {
    "archive",
    "Archive",
    ".git",
    "node_modules",
    "vendor",
    "Pods",
    ".build",
    "DerivedData",
}
ARCHIVE_FILENAME_RE = re.compile(r"archive", re.IGNORECASE)

# Surface 1: filename regex
DEFERRED_FILENAME_RE = re.compile(
    r"(deferred|backlog|todo|roadmap|plan)\.md$|^deferred.*\.md$|^.*deferred.*\.md$|^roadmap\.md$",
    re.IGNORECASE,
)
TIER_PHASE_PRIORITY_HEADING_RE = re.compile(
    r"^#+\s+(Tier|Phase|Priority)\s+\d+", re.IGNORECASE | re.MULTILINE
)

# Surface 1: redirect pointer pre-check
REDIRECT_HINT_PHRASES = ("MOVED", "see also", "UNFORGET.md")
REDIRECT_MAX_LINES = 30

# Surface 1b: documentation heuristics
DEFERRED_HEADING_RE = re.compile(r"^#+\s+.*\bDeferred\b", re.IGNORECASE | re.MULTILINE)
PENDING_HEADING_RE = re.compile(r"^#+\s+.*\bPending\b", re.IGNORECASE | re.MULTILINE)
TODO_HEADING_RE = re.compile(r"^#+\s+.*\bTODO\b", re.IGNORECASE | re.MULTILINE)
PHASE_N_HEADING_RE = re.compile(
    r"^#+\s+.*Phase\s*\d+\s+(pending|deferred|todo)", re.IGNORECASE | re.MULTILINE
)
DATE_PREFIX_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
DEFERRED_PREFIX_HEADING_RE = re.compile(
    r"^#+\s+DEFERRED:", re.IGNORECASE | re.MULTILINE
)
AUDIT_REPORT_TIER_HEADING_RE = re.compile(
    r"^#+\s+(CRITICAL|HIGH|MEDIUM|LOW)\s+Issues", re.MULTILINE
)
AUDIT_REPORT_FINDING_ID_RE = re.compile(
    r"^#+\s+[A-Z]+-[A-Z]?[0-9]+:", re.MULTILINE
)

# Surface 2: audit filename patterns
AUDIT_FILENAME_RE = re.compile(r"^audit-[a-z0-9-]+-\d{4}-\d{2}-\d{2}\.md$")
RADAR_LEDGER_PATH = ".radar-suite/ledger.yaml"

# Surface 4: code comment regex
CODE_COMMENT_RE = re.compile(
    r"//\s*(TODO|FIXME|HACK|XXX|MIGRATION-NOTE|DEFERRED)\b"
)
CODE_DIRS = ("Sources", "src", "lib", "app", "internal", "pkg")
CODE_EXTS = (".swift", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".m", ".mm", ".c", ".cc", ".cpp", ".h", ".hpp")

# Surface 6: memory file regex
MEMORY_FILENAME_RE = re.compile(r"^(deferred|project_deferred)_.*\.md$")
META_DOC_PHRASES = (
    "single source of truth",
    "format:",
    "how to use",
    "index of",
    "pointer to",
)


def is_excluded_path(p: Path) -> bool:
    parts = set(p.parts)
    if parts & EXCLUDED_DIR_NAMES:
        return True
    if p.suffix == ".md" and ARCHIVE_FILENAME_RE.search(p.name):
        return True
    return False


def walk_files(root: Path, include_subpath: str | None = None) -> Iterable[Path]:
    base = root / include_subpath if include_subpath else root
    if not base.exists():
        return
    for dirpath, dirnames, filenames in os.walk(base):
        # Filter excluded dirs in place to prune the walk
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES]
        for fname in filenames:
            p = Path(dirpath) / fname
            if not is_excluded_path(p.relative_to(root)):
                yield p


def read_text(p: Path, max_bytes: int = 1_000_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    except OSError:
        return ""


def is_redirect_pointer(p: Path) -> tuple[bool, str]:
    text = read_text(p, max_bytes=10_000)
    lines = text.splitlines()
    if len(lines) >= REDIRECT_MAX_LINES:
        return False, ""
    for phrase in REDIRECT_HINT_PHRASES:
        if phrase.lower() in text.lower():
            return True, phrase
    return False, ""


def scan_deferred_named(root: Path) -> dict:
    candidates = []
    skipped = []
    notes = []

    search_roots = [root, root / "Documentation", root / "docs", root / "notes"]
    seen: set[Path] = set()
    for base in search_roots:
        if not base.exists():
            continue
        for p in walk_files(root, include_subpath=str(base.relative_to(root)) if base != root else None):
            if p in seen:
                continue
            seen.add(p)
            if not p.suffix == ".md":
                continue

            matched = bool(DEFERRED_FILENAME_RE.search(p.name))
            if not matched:
                # Content-shape heuristic
                text = read_text(p, max_bytes=200_000)
                tier_count = len(TIER_PHASE_PRIORITY_HEADING_RE.findall(text))
                if tier_count >= 3:
                    matched = True

            if not matched:
                continue

            is_redirect, hint = is_redirect_pointer(p)
            if is_redirect:
                skipped.append(
                    {
                        "path": str(p.relative_to(root)),
                        "reason": f"redirect pointer (matched: '{hint}')",
                    }
                )
                continue

            candidates.append(
                {"path": str(p.relative_to(root)), "kind": "deferred_named"}
            )

    return {"candidates": candidates, "skipped": skipped, "notes": notes}


def scan_general_docs(root: Path) -> dict:
    candidates = []
    notes = []
    search_roots = [
        root / "Documentation" / "Development",
        root / "Documentation" / "Notes",
        root / "scratch",
        root / "docs" / "notes",
        root / "notes",
        root / "dev-docs",
    ]
    for base in search_roots:
        if not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            if is_excluded_path(p.relative_to(root)):
                continue

            text = read_text(p, max_bytes=200_000)
            matched_heuristics = []

            if DEFERRED_HEADING_RE.search(text):
                matched_heuristics.append(1)
            if PENDING_HEADING_RE.search(text):
                matched_heuristics.append(2)
            if TODO_HEADING_RE.search(text):
                matched_heuristics.append(3)
            if PHASE_N_HEADING_RE.search(text):
                matched_heuristics.append(4)
            if DATE_PREFIX_FILE_RE.match(p.name):
                matched_heuristics.append(5)
            if DEFERRED_PREFIX_HEADING_RE.search(text):
                matched_heuristics.append(6)
            # Heuristic 7 fires only on audit-format files (Surface 2 scope)
            if AUDIT_FILENAME_RE.match(p.name):
                if AUDIT_REPORT_TIER_HEADING_RE.search(text) or AUDIT_REPORT_FINDING_ID_RE.search(text):
                    matched_heuristics.append(7)

            if matched_heuristics:
                candidates.append(
                    {
                        "path": str(p.relative_to(root)),
                        "heuristics": matched_heuristics,
                    }
                )
    return {"candidates": candidates, "notes": notes}


def scan_audit_reports(root: Path) -> dict:
    candidates = []
    notes = []
    scratch = root / "scratch"
    if scratch.is_dir():
        for p in scratch.glob("*.md"):
            if is_excluded_path(p.relative_to(root)):
                continue
            if AUDIT_FILENAME_RE.match(p.name):
                candidates.append(
                    {"path": str(p.relative_to(root)), "format": "radar-suite-v3"}
                )

    ledger = root / RADAR_LEDGER_PATH
    if ledger.exists():
        candidates.append(
            {"path": RADAR_LEDGER_PATH, "format": "radar-suite-ledger"}
        )

    eslint_todos = root / ".eslint-todos"
    if eslint_todos.exists():
        candidates.append({"path": ".eslint-todos", "format": "eslint"})

    audit_dir = root / ".audit"
    if audit_dir.is_dir():
        for p in audit_dir.rglob("*"):
            if p.is_file() and not is_excluded_path(p.relative_to(root)):
                candidates.append({"path": str(p.relative_to(root)), "format": "custom-audit"})

    return {"candidates": candidates, "notes": notes}


def scan_plan_files(root: Path) -> dict:
    candidates = []
    notes = []
    plan_roots = [
        root / "plans",
        root / ".claude" / "plans",
        root / ".agents" / "plans",
    ]
    for base in plan_roots:
        if not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            if is_excluded_path(p.relative_to(root)):
                continue
            text = read_text(p, max_bytes=20_000)
            status_hint = None
            for hint in ("PAUSED:", "ABORTED:", "IN PROGRESS:"):
                if hint in text[:500]:
                    status_hint = hint
                    break
            candidates.append(
                {
                    "path": str(p.relative_to(root)),
                    "status_hint": status_hint,
                }
            )
    notes.append("Global ~/.claude/plans/ NOT scanned by default")
    return {"candidates": candidates, "notes": notes}


def scan_code_comments(root: Path, include: bool) -> dict:
    candidates = []
    notes = []
    if not include:
        notes.append("Skipped by default; pass --include-comments to scan")
        return {"candidates": candidates, "notes": notes}

    for code_dir in CODE_DIRS:
        base = root / code_dir
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix not in CODE_EXTS:
                continue
            if is_excluded_path(p.relative_to(root)):
                continue
            try:
                text = read_text(p, max_bytes=500_000)
            except Exception:
                continue
            for ln, line in enumerate(text.splitlines(), 1):
                m = CODE_COMMENT_RE.search(line)
                if m:
                    candidates.append(
                        {
                            "path": str(p.relative_to(root)),
                            "line": ln,
                            "tag": m.group(1),
                            "snippet": line.strip()[:200],
                        }
                    )
    return {"candidates": candidates, "notes": notes}


def scan_github_issues(root: Path) -> dict:
    """Report state only; this script never invokes `gh`."""
    notes = []
    git_dir = root / ".git"
    if not git_dir.exists():
        return {"state": "not-a-git-repo", "notes": ["No .git directory; skip gh"]}
    # Read .git/config for an origin url (lightweight; no `git` invocation)
    config = git_dir / "config"
    has_github_origin = False
    if config.exists():
        try:
            text = config.read_text(encoding="utf-8", errors="replace")
            has_github_origin = "github.com" in text
        except OSError:
            pass
    if not has_github_origin:
        return {
            "state": "non-github-remote",
            "notes": ["origin remote does not point at github.com; skip gh"],
        }
    # We don't call `gh` from this script — that's the LLM's job
    notes.append(
        "GitHub remote detected; invoke `gh issue list -L 200 --label deferred,wontfix-for-now,post-release,backlog` separately"
    )
    return {"state": "github-detected-defer-to-gh-cli", "notes": notes}


def scan_memory_files(root: Path) -> dict:
    """Use scripts/encode_project_path.py logic to find Claude Code memory dir."""
    candidates = []
    notes = []
    home = Path.home()
    abs_root = root.resolve()
    encoded = re.sub(r"[/\s]", "-", str(abs_root))
    primary = home / ".claude" / "projects" / encoded / "memory"

    paths_to_scan: list[Path] = []
    if primary.is_dir():
        paths_to_scan.append(primary)
        notes.append(f"primary memory dir: {primary}")
    else:
        notes.append(f"primary memory dir not found: {primary}")
        # Ancestor walk fallback (up to 4 levels)
        cur = abs_root
        for _ in range(4):
            cur = cur.parent
            if cur == cur.parent:
                break
            ancestor_encoded = re.sub(r"[/\s]", "-", str(cur))
            ancestor_dir = home / ".claude" / "projects" / ancestor_encoded / "memory"
            if ancestor_dir.is_dir():
                paths_to_scan.append(ancestor_dir)
                notes.append(f"ancestor memory dir: {ancestor_dir}")

    for memdir in paths_to_scan:
        for p in memdir.glob("*.md"):
            if not MEMORY_FILENAME_RE.match(p.name):
                continue
            text = read_text(p, max_bytes=50_000)
            meta_hits = [phrase for phrase in META_DOC_PHRASES if phrase.lower() in text.lower()]
            candidates.append(
                {
                    "path": str(p),
                    "memory_dir": str(memdir),
                    "meta_doc_phrases_matched": meta_hits,
                    "looks_like_meta": bool(meta_hits),
                }
            )
    return {"candidates": candidates, "notes": notes}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan a project root for deferred-work artifacts (read-only)."
    )
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument(
        "--include-comments",
        action="store_true",
        help="Include code-comment surface (skipped by default)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"root not found: {root}"}), file=sys.stderr)
        return 2

    surfaces = {
        "deferred_named_files": scan_deferred_named(root),
        "general_documentation": scan_general_docs(root),
        "audit_reports": scan_audit_reports(root),
        "plan_files": scan_plan_files(root),
        "code_comments": scan_code_comments(root, args.include_comments),
        "github_issues": scan_github_issues(root),
        "memory_files": scan_memory_files(root),
    }

    total_candidates = 0
    total_skipped = 0
    for s in surfaces.values():
        total_candidates += len(s.get("candidates", []))
        total_skipped += len(s.get("skipped", []))

    result = {
        "root": str(root),
        "surfaces": surfaces,
        "summary": {
            "total_candidates": total_candidates,
            "total_skipped": total_skipped,
        },
    }
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
