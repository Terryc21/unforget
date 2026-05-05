#!/usr/bin/env python3
"""Normalize a script's JSON output for golden-file diffing.

The deterministic helpers under `scripts/` produce JSON that is logically
deterministic but contains machine-specific or order-dependent fields:

  - Absolute paths (`root`, `path`) vary by user / checkout location.
  - `memory_files.notes` leaks the user's home dir (Surface 6).
  - Candidate arrays are emitted in `os.walk` / `Path.rglob` order, which
    is filesystem-ordered, not lexicographic.

This script reads JSON from stdin, applies normalization rules, and writes
the result to stdout. Used by `tests/run.sh` between helper invocation and
golden-file diff.

Usage:
  python3 tests/normalize.py --kind <kind> --repo-root <abs-path>

Kinds:
  scan_surfaces          -- output of scripts/scan_surfaces.py
  check_format_version   -- output of scripts/check_format_version.py
  encode_project_path    -- output of scripts/encode_project_path.py (no-op)
  dedup_findings         -- output of scripts/dedup_findings.py
"""
import argparse
import json
import sys


REPO_ROOT_PLACEHOLDER = "<REPO_ROOT>"


def replace_repo_root(value, repo_root: str):
    if isinstance(value, str):
        return value.replace(repo_root, REPO_ROOT_PLACEHOLDER)
    return value


def normalize_scan_surfaces(data: dict, repo_root: str) -> dict:
    # Strip repo-root from top-level "root"
    if "root" in data:
        data["root"] = replace_repo_root(data["root"], repo_root)

    surfaces = data.get("surfaces", {})

    # Sort each candidate list by `path` (fall back to JSON repr)
    for surface_name, payload in surfaces.items():
        if isinstance(payload, dict) and "candidates" in payload:
            payload["candidates"] = sorted(
                payload["candidates"],
                key=lambda c: (c.get("path", ""), c.get("line", 0), c.get("tag", "")),
            )
        if isinstance(payload, dict) and "skipped" in payload:
            payload["skipped"] = sorted(
                payload["skipped"], key=lambda s: s.get("path", "")
            )

    # Surface 6: memory_files leaks the user's home dir into `notes`.
    # Replace with a stable marker; the real value is machine-specific.
    if "memory_files" in surfaces:
        mf = surfaces["memory_files"]
        if "notes" in mf:
            mf["notes"] = ["<machine-specific note suppressed>"] if mf["notes"] else []
        # candidates are unstable in the test environment — clear them.
        # The fixture deliberately does NOT plant a real Surface 6 hit.
        if mf.get("candidates"):
            mf["candidates"] = ["<unstable in test env; cleared>"]

    return data


def normalize_check_format_version(data: dict, repo_root: str) -> dict:
    if "path" in data:
        data["path"] = replace_repo_root(data["path"], repo_root)
    return data


def normalize_dedup_findings(data: dict, repo_root: str) -> dict:
    # No paths to strip — candidates are already deterministic given fixed input.
    # Sort the top-level candidates by headline for stable ordering.
    if "candidates" in data:
        data["candidates"] = sorted(data["candidates"], key=lambda c: c.get("headline", ""))
    return data


def normalize_encode_project_path(data: dict, repo_root: str) -> dict:
    # Pure string transform; no normalization needed.
    return data


NORMALIZERS = {
    "scan_surfaces": normalize_scan_surfaces,
    "check_format_version": normalize_check_format_version,
    "encode_project_path": normalize_encode_project_path,
    "dedup_findings": normalize_dedup_findings,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize helper JSON for golden diff.")
    parser.add_argument("--kind", required=True, choices=sorted(NORMALIZERS.keys()))
    parser.add_argument("--repo-root", required=True, help="Absolute repo-root path to strip")
    args = parser.parse_args()

    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"normalize.py: invalid JSON on stdin: {e}", file=sys.stderr)
        return 2

    normalized = NORMALIZERS[args.kind](data, args.repo_root)
    json.dump(normalized, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
