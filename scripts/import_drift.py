#!/usr/bin/env python3
r"""Detect drift between the unforget registry and reality (the `import` reconciler).

Implements the drift checks of the Onboarding & Registry design spec §5 (see
reference/init.md § import drift). `import` re-surveys and reconciles the registry
against what is actually on disk and in git, catching the failures that stranded
TERRY/MI in a parallel tree on 2026-07-25. Four checks:

  1. registered-but-missing — a ledger in the registry not found on disk. Turns a
     20-minute "are they lost?" hunt into one line naming the last-known path.
  2. found-but-unregistered — a ledger-shaped file on disk but not in the registry.
     This is the check that would have SURFACED the parallel-tree files instead of
     leaving them stranded.
  3. posture-mismatch — a ledger whose actual git-tracked state disagrees with the
     registered git_posture (e.g. registered "ignored" but git is tracking it).
  4. stale-recall — reported via recall_block.py separately; this script flags it
     when --recall-file is given and the block is stale vs the registry.

Read-only. It REPORTS drift; the LLM (following reference/init.md) walks the fixes
with the user. It never moves, registers, or rewrites on its own.

Usage:
  python3 import_drift.py --dir <ledger-dir> [--recall-file <CLAUDE.md>]
  python3 import_drift.py --help

  --dir          the ledger directory (holds README.md registry + the ledgers)
  --recall-file  optional: also check the maintained recall block for staleness

Output (stdout, JSON):
  {
    "dir": "<ledger-dir>",
    "registered": N,
    "found_on_disk": M,
    "findings": [
      {"check": "registered-but-missing", "severity": "error",
       "ledger": "MI-UNFORGET", "path": "<last-known>", "message": "..."},
      {"check": "found-but-unregistered", "severity": "warn",
       "file": "TERRY-UNFORGET.md", "message": "..."},
      {"check": "posture-mismatch", "severity": "warn", "ledger": "...",
       "registered": "ignored", "actual": "tracked", "message": "..."},
      {"check": "stale-recall", "severity": "warn", "file": "...", "message": "..."}
    ],
    "clean": true|false,
    "advisory": "<one-line summary>"
  }

Exit codes:
  0  no drift (registry matches reality)
  1  drift found (≥1 finding)
  2  usage error / dir not found / no registry
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry  # type: ignore  # noqa: E402
import recall_block  # type: ignore  # noqa: E402

# A "ledger-shaped" file on disk: an UNFORGET-family markdown file. Matches the
# main ledger and the by-actor / by-lifespan naming already in use (TERRY-*, MI-*),
# plus any *UNFORGET*.md. Case-insensitive.
LEDGER_FILE_RE = re.compile(r"(unforget.*\.md|^(terry|mi)-.*\.md)$", re.IGNORECASE)
# Files that MATCH the ledger name shape but are NOT active ledgers: archives, backup
# copies, the registry README, changelogs (the evict-target of a capped child), and
# handoff/design/continuation docs that happen to carry a ledger token in the name.
# Excluding these keeps the found-but-unregistered check from crying wolf on the very
# companion files that live alongside a real ledger.
EXCLUDE_RE = re.compile(
    r"(-archive|\.bak|README|CHANGELOG|HANDOFF|CONTINUATION|^DESIGN-)", re.IGNORECASE)


def find_ledger_files(dir_path: Path) -> list[str]:
    out = []
    for p in sorted(dir_path.iterdir()):
        if not p.is_file():
            continue
        name = p.name
        if EXCLUDE_RE.search(name):
            continue
        if LEDGER_FILE_RE.search(name):
            out.append(name)
    return out


def git_tracked(dir_path: Path, filename: str) -> bool | None:
    """True if git tracks the file, False if not, None if not a git repo / git absent."""
    try:
        r = subprocess.run(
            ["git", "-C", str(dir_path), "ls-files", "--error-unmatch", filename],
            capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return None


def posture_expects_tracked(posture: str, filename: str) -> bool | None:
    """What the registered posture implies for this file's git-tracked state.

    - committed → tracked
    - ignored   → NOT tracked
    - split     → ledger CONTENTS not tracked, but a README/index IS. We only
      posture-check ledger files here (README is excluded from the scan), so a
      split posture implies NOT tracked for a ledger file.
    Returns True/False, or None when the posture doesn't constrain it.
    """
    p = (posture or "").strip().lower()
    if p == "committed":
        return True
    if p in ("ignored", "split"):
        return False
    return None


def run(dir_path: Path, recall_file: str | None) -> dict:
    reg = registry.read_registry(dir_path)
    if "error" in reg:
        return {"error": reg["error"]}

    registered = reg.get("ledgers", [])
    reg_by_name = {(l.get("name") or "").lower(): l for l in registered}
    reg_paths = {(l.get("path") or l.get("name") or "").lower() for l in registered}
    posture = (reg.get("global") or {}).get("git_posture")

    findings = []

    # 1. registered-but-missing
    for led in registered:
        path = led.get("path") or led.get("name")
        if not path:
            continue
        if not (dir_path / path).exists():
            findings.append({
                "check": "registered-but-missing", "severity": "error",
                "ledger": led.get("name"), "path": path,
                "message": (f"`{led.get('name')}` registered at `{path}` — not found on disk; "
                            "moved or deleted?"),
            })

    # 2. found-but-unregistered
    disk = find_ledger_files(dir_path)
    for name in disk:
        stem = name[:-3] if name.endswith(".md") else name
        if name.lower() in reg_paths or stem.lower() in reg_by_name:
            continue
        findings.append({
            "check": "found-but-unregistered", "severity": "warn",
            "file": name,
            "message": (f"`{name}` looks like a ledger but is not in the registry — "
                        "offer to register it (this is the stranded-parallel-tree check)."),
        })

    # 3. posture-mismatch (only when git + a posture are both present)
    if posture:
        want = None
        for led in registered:
            path = led.get("path") or led.get("name")
            if not path or not (dir_path / path).exists():
                continue
            want = posture_expects_tracked(posture, path)
            if want is None:
                continue
            actual = git_tracked(dir_path, path)
            if actual is None:
                continue  # not a git repo / git absent — can't check
            if actual != want:
                findings.append({
                    "check": "posture-mismatch", "severity": "warn",
                    "ledger": led.get("name"),
                    "registered": posture,
                    "actual": "tracked" if actual else "not-tracked",
                    "message": (f"`{led.get('name')}` registered posture `{posture}` implies "
                                f"{'tracked' if want else 'not-tracked'}, but git has it "
                                f"{'tracked' if actual else 'not-tracked'}."),
                })

    # 4. stale-recall (only if a recall file is given)
    if recall_file:
        class _A:  # minimal args shim for recall_block.do_check
            pass
        a = _A()
        a.file = recall_file
        a.dir = str(dir_path)
        a.registry = None
        a.home = None
        rc = recall_block.do_check(a)
        if "error" not in rc and rc.get("block_present") and rc.get("in_sync") is False:
            findings.append({
                "check": "stale-recall", "severity": "warn",
                "file": recall_file,
                "message": ("the maintained recall block is stale vs the registry — "
                            "rewrite it (init/import) to refresh the paths/ledger list."),
            })

    clean = not findings
    err_count = sum(1 for f in findings if f["severity"] == "error")
    return {
        "dir": str(dir_path),
        "registered": len(registered),
        "found_on_disk": len(disk),
        "findings": findings,
        "clean": clean,
        "advisory": ("registry matches reality; no drift" if clean else
                     f"{len(findings)} drift finding(s) ({err_count} error). "
                     "Reconcile before trusting the registry."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect registry↔reality drift (the import reconciler).")
    parser.add_argument("--dir", required=True, help="ledger directory (registry + ledgers)")
    parser.add_argument("--recall-file", default=None, help="also check the recall block for staleness")
    args = parser.parse_args()

    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        print(json.dumps({"error": f"not a directory: {dir_path}"}), file=sys.stderr)
        return 2

    result = run(dir_path, args.recall_file)
    if "error" in result:
        print(json.dumps(result), file=sys.stderr)
        return 2
    json.dump(result, sys.stdout); sys.stdout.write("\n")
    return 0 if result["clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
