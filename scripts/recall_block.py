#!/usr/bin/env python3
r"""Write/read/update the maintained recall block in CLAUDE.md / AGENTS.md.

Implements the maintained "Deferred Work Index" recall block (see
reference/init.md § Recall block and reference/registry.md, from the Onboarding &
Registry design spec §4). The recall block is what makes future sessions FIND the
ledgers — without it the registry is correct but unread. Under the *maintained*
posture the skill owns a marker-delimited block in the project's agent-instructions
file and regenerates it whenever ledgers/locations change (init / import / branch /
move), so the block can't silently rot (the 2026-07-25 stale-pointer failure).

    <!-- unforget:begin — maintained by the unforget skill; do not hand-edit inside these markers -->
    ## Deferred Work Index
    ...ledger home, git posture, one line per registered ledger, read-triggers...
    <!-- unforget:end -->

The skill only ever rewrites BETWEEN the markers — never the user's surrounding
CLAUDE.md content (mirrors registry.py's block discipline). The block's content is
DERIVED from the registry (the source of truth), so this writer takes a registry
JSON (or reads it via registry.py given --dir) and renders the block from it.

Usage:
  # Render + write/update the block into an instructions file, from a registry:
  python3 recall_block.py write --file <CLAUDE.md> --dir <ledger-dir> \
      [--home "<display path>"]
  # Render + write from an explicit registry JSON (no --dir read):
  python3 recall_block.py write --file <CLAUDE.md> --registry <reg.json> [--home ...]
  # Report whether a maintained block is present and whether it's stale vs the registry:
  python3 recall_block.py check --file <CLAUDE.md> --dir <ledger-dir>
  # Print the rendered block to stdout without writing (for the manual posture):
  python3 recall_block.py render --dir <ledger-dir> [--home ...]
  python3 recall_block.py --help

Output (write/check, stdout, JSON):
  {
    "file": "<path>",
    "block_present": true|false,
    "action": "wrote"|"updated"|"would-write"|"none",
    "in_sync": true|false|null,   # check: does the file block match the registry render?
    "ledger_count": N,
    "advisory": "<one-line>"
  }

Exit codes:
  0  ok (written / present-and-in-sync / rendered)
  1  drift (check: file block is stale vs the registry) OR block absent (check)
  2  usage error / file or dir not found / no registry
"""
import argparse
import json
import sys
from pathlib import Path

# registry.py lives beside this script; reuse it as the single registry reader.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry  # type: ignore  # noqa: E402

BEGIN = "<!-- unforget:begin — maintained by the unforget skill; do not hand-edit inside these markers -->"
END = "<!-- unforget:end -->"

# Human-readable git-posture descriptions for the block header.
POSTURE_NOTE = {
    "split": "split — contents ignored, README/index tracked",
    "ignored": "ignored — local-only working notes, never committed",
    "committed": "committed — tracked in the repo, a team-shared backlog",
}


def extract_block(text: str) -> str | None:
    """Return the block text (inclusive of markers), or None if absent."""
    start = text.find(BEGIN)
    if start == -1:
        return None
    end = text.find(END, start)
    if end == -1:
        return None
    return text[start:end + len(END)]


def ledger_line(led: dict) -> str:
    """One bullet per registered ledger, naming role/axis/discipline/death."""
    name = led.get("name") or "?"
    path = led.get("path") or name
    role = led.get("role") or "main"
    bits = []
    axis = led.get("axis")
    if axis:
        bits.append(f"{axis} axis")
    disc = led.get("discipline")
    if disc:
        bits.append(disc)
    death = led.get("death")
    if death:
        bits.append(f"dies: {death}")
    parent = led.get("parent")
    if parent:
        bits.append(f"child of {parent}")
    tail = f" ({role}" + (" · " + " · ".join(bits) if bits else "") + ")"
    return f"- `{path}` — {name}{tail}."


def render_block(global_cfg: dict, ledgers: list[dict], home: str | None) -> str:
    posture = (global_cfg.get("git_posture") or "").strip().lower()
    posture_note = POSTURE_NOTE.get(posture, posture or "unset")
    home_disp = home or "(the ledger directory)"
    lines = [
        BEGIN,
        "## Deferred Work Index",
        "",
        f"**Ledger home:** `{home_disp}`  (git posture: {posture_note})",
        "",
    ]
    if ledgers:
        for led in ledgers:
            lines.append(ledger_line(led))
    else:
        lines.append("- (no ledgers registered yet — run `/unforget init` or `/unforget import`)")
    lines += [
        "",
        "Read the ledgers when the user asks \"what's deferred?\" / \"backlog?\" / \"prioritize,\" "
        "and before suggesting a release (check 🔴 THIS rows). Log new deferrals via the deferral "
        "gate — an item lives in exactly ONE ledger; siblings get a pointer row, not a copy.",
        END,
    ]
    return "\n".join(lines)


def upsert_block(text: str, new_block: str) -> tuple[str, str]:
    """Insert or replace the block. Returns (new_text, action)."""
    start = text.find(BEGIN)
    if start == -1:
        # append at end, leaving the user's content untouched
        joined = text.rstrip() + "\n\n" + new_block + "\n"
        return joined, "wrote"
    end = text.find(END, start)
    end = end + len(END) if end != -1 else len(text)
    return text[:start] + new_block + text[end:], "updated"


def load_registry(args) -> dict:
    if getattr(args, "registry", None):
        src = Path(args.registry)
        if not src.exists():
            return {"error": f"registry json not found: {src}"}
        obj = json.loads(src.read_text(encoding="utf-8"))
        return {"global": obj.get("global", {}), "ledgers": obj.get("ledgers", [])}
    d = Path(args.dir)
    if not d.is_dir():
        return {"error": f"not a directory: {d}"}
    reg = registry.read_registry(d)
    if "error" in reg:
        return reg
    return {"global": reg.get("global", {}), "ledgers": reg.get("ledgers", [])}


def resolve_home(args, reg: dict) -> str | None:
    """The display home: an explicit --home wins; else the registry's recall_home.

    Persisting recall_home in the registry (not just passing it at write time) is
    what lets `check` re-render an identical block — otherwise a block written with
    --home would always read as stale because the checker rendered with home=None.
    When --home is given AND differs from the stored value, persist the new value so
    writer and checker stay agreed.
    """
    stored = (reg.get("global") or {}).get("recall_home")
    return args.home if args.home is not None else stored


def do_write(args, write: bool) -> dict:
    reg = load_registry(args)
    if "error" in reg:
        return {"error": reg["error"]}
    home = resolve_home(args, reg)
    # If an explicit --home was given that differs from the stored value, persist it
    # to the registry so `check` re-renders an identical block (writer/checker agree).
    if write and args.home is not None and getattr(args, "dir", None):
        stored = (reg.get("global") or {}).get("recall_home")
        if args.home != stored:
            g = dict(reg.get("global") or {})
            g["recall_home"] = args.home
            try:
                registry.write_registry(Path(args.dir), g, reg.get("ledgers", []))
                reg["global"] = g
            except OSError:
                pass  # non-fatal: the block still renders with the resolved home
    new_block = render_block(reg["global"], reg["ledgers"], home)
    target = Path(args.file)
    existing = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
    had_block = extract_block(existing) is not None
    new_text, action = upsert_block(existing, new_block) if existing else (new_block + "\n", "wrote")
    if not write:
        action = "would-write"
    elif not existing:
        target.write_text(new_block + "\n", encoding="utf-8")
    else:
        target.write_text(new_text, encoding="utf-8")
    return {
        "file": str(target),
        "block_present": True,
        "action": action,
        "in_sync": None,
        "ledger_count": len(reg["ledgers"]),
        "advisory": (f"recall block {action} in {target.name} "
                     f"({len(reg['ledgers'])} ledger(s))"),
        "_had_block": had_block,
    }


def do_check(args) -> dict:
    reg = load_registry(args)
    if "error" in reg:
        return {"error": reg["error"]}
    target = Path(args.file)
    if not target.exists():
        return {"file": str(target), "block_present": False, "action": "none",
                "in_sync": None, "ledger_count": len(reg["ledgers"]),
                "advisory": f"{target.name} not found; no recall block"}
    text = target.read_text(encoding="utf-8", errors="replace")
    current = extract_block(text)
    if current is None:
        return {"file": str(target), "block_present": False, "action": "none",
                "in_sync": None, "ledger_count": len(reg["ledgers"]),
                "advisory": "no maintained recall block; run init/import to add one"}
    expected = render_block(reg["global"], reg["ledgers"], resolve_home(args, reg))
    in_sync = current.strip() == expected.strip()
    return {
        "file": str(target),
        "block_present": True,
        "action": "none",
        "in_sync": in_sync,
        "ledger_count": len(reg["ledgers"]),
        "advisory": ("recall block matches the registry" if in_sync
                     else "recall block is STALE vs the registry — rewrite (init/import) to refresh"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write/read/update the maintained recall block in CLAUDE.md / AGENTS.md.")
    sub = parser.add_subparsers(dest="action", required=True)

    for name in ("write", "render"):
        p = sub.add_parser(name)
        if name == "write":
            p.add_argument("--file", required=True, help="the agent-instructions file (CLAUDE.md/AGENTS.md)")
        p.add_argument("--dir", help="ledger directory (registry source)")
        p.add_argument("--registry", help="explicit registry JSON {global, ledgers}")
        p.add_argument("--home", default=None, help="display path for the ledger home")

    c = sub.add_parser("check")
    c.add_argument("--file", required=True, help="the agent-instructions file")
    c.add_argument("--dir", help="ledger directory (registry source)")
    c.add_argument("--registry", help="explicit registry JSON")
    c.add_argument("--home", default=None, help="display path for the ledger home")

    args = parser.parse_args()

    if args.action in ("write", "render") and not (args.dir or args.registry):
        print(json.dumps({"error": f"{args.action} needs --dir or --registry"}), file=sys.stderr)
        return 2

    if args.action == "render":
        reg = load_registry(args)
        if "error" in reg:
            print(json.dumps(reg), file=sys.stderr)
            return 2
        sys.stdout.write(render_block(reg["global"], reg["ledgers"], resolve_home(args, reg)) + "\n")
        return 0

    if args.action == "write":
        result = do_write(args, write=True)
        if "error" in result:
            print(json.dumps(result), file=sys.stderr)
            return 2
        result.pop("_had_block", None)
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 0

    # check
    result = do_check(args)
    if "error" in result:
        print(json.dumps(result), file=sys.stderr)
        return 2
    json.dump(result, sys.stdout); sys.stdout.write("\n")
    if not result["block_present"]:
        return 1
    return 0 if result["in_sync"] else 1


if __name__ == "__main__":
    sys.exit(main())
