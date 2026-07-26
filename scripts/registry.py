#!/usr/bin/env python3
r"""Read/write the unforget registry.

The registry is the re-read source of truth for where ledgers live, the git
posture, and the persisted policies (see reference/registry.md, from the
Onboarding & Registry design spec §3). It has two forms:

- CANONICAL: a marker-delimited block inside the ledger directory's README.md:

      <!-- unforget-registry:begin -->
      ...a GLOBAL key/value table and a LEDGERS table...
      <!-- unforget-registry:end -->

  Human-readable and hand-editable. Lives inside README.md so it travels with
  the ledgers and (under the Split git posture) is the one tracked artifact.

- CACHE (optional): a `.unforget.json` sibling the skill may also write for
  cheap parsing. It is regenerable from the README. If the two DISAGREE, the
  README wins (a human edited it; the human is authoritative).

The skill only ever rewrites BETWEEN the markers, never the human prose around
them.

Usage:
  python3 registry.py read   --dir <ledger-dir>            # emit registry as JSON (README canonical)
  python3 registry.py write  --dir <ledger-dir> --json <f> # write block from a JSON file (rewrites cache too)
  python3 registry.py check  --dir <ledger-dir>            # report README-vs-cache drift
  python3 registry.py --help

Output (read/check, stdout, JSON):
  {
    "dir": "<ledger-dir>",
    "block_present": true|false,
    "global": { "git_posture": "...", "policy_deferral": "...", ... },
    "ledgers": [ { "name": "...", "path": "...", "role": "...", ... }, ... ],
    "cache_present": true|false,
    "cache_in_sync": true|false|null,   # null when no cache
    "source_of_truth": "readme",
    "advisory": "<one-line summary>"
  }

Exit codes:
  0  ok
  1  drift detected (check) OR block absent (read)
  2  usage error / dir not found / no README
"""
import argparse
import json
import re
import sys
from pathlib import Path

BEGIN = "<!-- unforget-registry:begin -->"
END = "<!-- unforget-registry:end -->"
README_NAME = "README.md"
CACHE_NAME = ".unforget.json"

# Recognized keys for the GLOBAL block (spec §3a). Unknown keys are preserved
# (round-tripped) rather than dropped, so a newer skill's keys survive an older
# read/write cycle.
GLOBAL_KEYS = [
    "git_posture",
    "recall_block",
    "recall_file",
    "recall_home",
    "policy_deferral",
    "policy_multiaxis",
    "ratio_flag_threshold",
    "stale_trivial_sessions",
    "row_char_budget",
]

LEDGER_COLUMNS = ["name", "path", "role", "axis", "discipline", "parent", "death"]


# --- README block parsing --------------------------------------------------

def extract_block(text: str) -> str | None:
    """Return the text BETWEEN the registry markers, or None if absent."""
    start = text.find(BEGIN)
    if start == -1:
        return None
    end = text.find(END, start)
    if end == -1:
        return None
    return text[start + len(BEGIN):end]


def parse_kv_table(block: str) -> dict:
    """Parse the GLOBAL key|value markdown table into a dict."""
    result = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        key, val = cells
        # skip header + separator rows
        if key.lower() in ("key", "setting", "") or set(key) <= set("-: "):
            continue
        # store empty/placeholder as None
        result[key] = None if val in ("", "-", "—", "(unset)") else val
    return result


def parse_ledger_table(block: str) -> list[dict]:
    """Parse the LEDGERS markdown table into a list of dicts."""
    rows = []
    header = None
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        # a header row that names the ledger columns
        low = [c.lower() for c in cells]
        if "name" in low and "path" in low:
            header = low
            continue
        if header is None:
            continue
        if set("".join(cells)) <= set("-: "):  # separator row
            continue
        row = {}
        for i, col in enumerate(header):
            if col in LEDGER_COLUMNS and i < len(cells):
                v = cells[i]
                row[col] = None if v in ("", "-", "—") else v
        if row.get("name"):
            rows.append(row)
    return rows


def read_registry(dir_path: Path) -> dict:
    readme = dir_path / README_NAME
    if not readme.exists():
        return {"error": f"no README.md in {dir_path}"}
    text = readme.read_text(encoding="utf-8", errors="replace")
    block = extract_block(text)
    if block is None:
        return {
            "dir": str(dir_path),
            "block_present": False,
            "global": {},
            "ledgers": [],
            "advisory": "no registry block; run init/import to create one",
        }
    # The block holds two tables: split on the LEDGERS header. Parse both.
    global_cfg = parse_kv_table(block)
    ledgers = parse_ledger_table(block)
    return {
        "dir": str(dir_path),
        "block_present": True,
        "global": global_cfg,
        "ledgers": ledgers,
        "advisory": f"{len(ledgers)} ledger(s) registered",
    }


# --- README block rendering ------------------------------------------------

def render_block(global_cfg: dict, ledgers: list[dict]) -> str:
    lines = [BEGIN, "", "### unforget registry", "",
             "> Machine-maintained. Do not hand-edit between the markers except to",
             "> correct a value; the skill rewrites this block on init/import/branch.",
             "", "**Global**", "", "| key | value |", "|---|---|"]
    for key in GLOBAL_KEYS:
        val = global_cfg.get(key)
        lines.append(f"| {key} | {val if val not in (None, '') else '(unset)'} |")
    # preserve any unknown keys
    for key, val in global_cfg.items():
        if key not in GLOBAL_KEYS:
            lines.append(f"| {key} | {val if val not in (None, '') else '(unset)'} |")
    lines += ["", "**Ledgers**", "",
              "| " + " | ".join(LEDGER_COLUMNS) + " |",
              "|" + "|".join(["---"] * len(LEDGER_COLUMNS)) + "|"]
    for led in ledgers:
        lines.append("| " + " | ".join(str(led.get(c) or "—") for c in LEDGER_COLUMNS) + " |")
    lines += ["", END]
    return "\n".join(lines)


def write_registry(dir_path: Path, global_cfg: dict, ledgers: list[dict]) -> dict:
    readme = dir_path / README_NAME
    if not readme.exists():
        # create a minimal README carrying just the block
        text = f"# Ledgers\n\n{render_block(global_cfg, ledgers)}\n"
        readme.write_text(text, encoding="utf-8")
    else:
        text = readme.read_text(encoding="utf-8", errors="replace")
        new_block = render_block(global_cfg, ledgers)
        start = text.find(BEGIN)
        if start == -1:
            # append the block at the end, leaving human content untouched
            text = text.rstrip() + "\n\n" + new_block + "\n"
        else:
            end = text.find(END, start)
            end = end + len(END) if end != -1 else len(text)
            text = text[:start] + new_block + text[end:]
        readme.write_text(text, encoding="utf-8")

    # Write the cache mirror. Cache the NORMALIZED form (re-read from the README
    # we just wrote), not the raw input, so a fresh write is always in sync with
    # a subsequent README read. Otherwise a caller who omits null fields
    # (e.g. no `axis`) would produce a cache that structurally differs from the
    # README read (which fills every column with explicit null), and `check`
    # would spuriously report drift immediately after a write.
    cache = dir_path / CACHE_NAME
    normalized = read_registry(dir_path)
    cache_obj = {"global": normalized["global"], "ledgers": normalized["ledgers"]}
    cache.write_text(json.dumps(cache_obj, indent=2) + "\n", encoding="utf-8")
    return {"dir": str(dir_path), "wrote_readme_block": True,
            "wrote_cache": str(cache), "ledgers": len(ledgers)}


# --- cache reconciliation --------------------------------------------------

def check_drift(dir_path: Path) -> dict:
    readme_reg = read_registry(dir_path)
    cache = dir_path / CACHE_NAME
    if "error" in readme_reg:
        return {**readme_reg, "cache_present": cache.exists()}
    if not cache.exists():
        return {**readme_reg, "cache_present": False, "cache_in_sync": None,
                "source_of_truth": "readme",
                "advisory": "no cache; README is the source of truth"}
    try:
        cache_obj = json.loads(cache.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {**readme_reg, "cache_present": True, "cache_in_sync": False,
                "source_of_truth": "readme",
                "advisory": "cache unreadable; README wins — regenerate cache"}
    in_sync = (cache_obj.get("global") == readme_reg["global"]
               and cache_obj.get("ledgers") == readme_reg["ledgers"])
    return {**readme_reg, "cache_present": True, "cache_in_sync": in_sync,
            "source_of_truth": "readme",
            "advisory": ("cache matches README" if in_sync
                         else "cache DRIFTED from README; README wins — regenerate cache")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read/write the unforget registry.")
    parser.add_argument("action", choices=["read", "write", "check"])
    parser.add_argument("--dir", required=True, help="Ledger directory (holds README.md)")
    parser.add_argument("--json", help="For write: path to a JSON file {global, ledgers}")
    args = parser.parse_args()

    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        print(json.dumps({"error": f"not a directory: {dir_path}"}), file=sys.stderr)
        return 2

    if args.action == "read":
        result = read_registry(dir_path)
        if "error" in result:
            print(json.dumps(result), file=sys.stderr)
            return 2
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 0 if result["block_present"] else 1

    if args.action == "check":
        result = check_drift(dir_path)
        if "error" in result:
            print(json.dumps(result), file=sys.stderr)
            return 2
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 0 if result.get("cache_in_sync") in (True, None) else 1

    # write
    if not args.json:
        print(json.dumps({"error": "write requires --json <file>"}), file=sys.stderr)
        return 2
    src = Path(args.json)
    if not src.exists():
        print(json.dumps({"error": f"json file not found: {src}"}), file=sys.stderr)
        return 2
    payload = json.loads(src.read_text(encoding="utf-8"))
    result = write_registry(dir_path, payload.get("global", {}), payload.get("ledgers", []))
    json.dump(result, sys.stdout); sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
