#!/usr/bin/env python3
r"""Companion-skill handoffs: read/write the global manifest and resolve a function
to its install-state expression.

Implements the companion-skill handoff mechanic (see reference/skill-handoffs.md,
from the Companion Skill Handoffs design spec). unforget recommends OTHER skills at
earned ledger transitions — function-based, not skill+URL hardcoded through trigger
points, so a companion link rots in ONE place (the manifest), never twelve.

Five FIXED functions (the left column; unforget owns these), each mapping to a
user-owned skill / invoke / url (the right columns):

  post-fix-sibling-scan   — a row closes with a code change
  ship-risk-scoring       — a 🔴 THIS row nears promote/release
  audit-reverify          — an audit-finding row is being closed
  forward-bug-hunt        — the deferral gate can't infer a pattern
  verify-against-reality  — verify finds a done-verified w/o device/user evidence

The manifest is GLOBAL (~/.claude/unforget-companions.md by default; projects inherit
it), a marker-delimited table so the skill rewrites only between its markers.

THE CRITICAL DETECTION RULE (§4a, the one-star-risk lesson): install-state is
detected by INVOCABLE SKILL NAME, never a directory `find` — the invocation name ≠
the plugin/dir name (`one-star-risk` is invocable but has no dir of that name). This
script CANNOT see the session's skill list (that's runtime state), so the caller
PASSES it via --invocable (comma-separated, or a file with one name per line). The
script does the manifest resolution + the three-state expression logic against that
authoritative list.

Usage:
  # seed the shipped-default manifest (idempotent; won't clobber a customized one):
  python3 companions.py init [--file <manifest>] [--force]

  # read the manifest as JSON:
  python3 companions.py read [--file <manifest>]

  # resolve one function to its handoff expression, given what's invocable:
  python3 companions.py resolve --function post-fix-sibling-scan \
      --invocable "bug-echo,radar-suite,one-star-risk"   # or --invocable-file <f>

  # rot check (for verify §4c): every mapped skill neither invocable nor URL-bearing:
  python3 companions.py rotcheck --invocable "bug-echo,radar-suite" [--file <manifest>]

  python3 companions.py --help

resolve output (stdout, JSON):
  {
    "function": "post-fix-sibling-scan",
    "skill": "bug-echo"|null,
    "state": "installed" | "not-installed" | "unset",
    "invoke": "/bug-echo"|null,
    "url": "https://..."|null,          # surfaced ONLY when not-installed
    "expression": "<the one-line handoff the LLM should say>",
    "advisory": "<context>"
  }

Exit codes:
  0  ok
  1  rotcheck found a rotted entry / resolve found an unset function
  2  usage error / manifest unreadable
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

BEGIN = "<!-- unforget-companions:begin — maintained by the unforget skill; edit the skill/invoke/url freely -->"
END = "<!-- unforget-companions:end -->"

# The 5 fixed functions (§2). Left column is unforget's; DO NOT let callers add
# functions — a growing catalog is the over-branching failure applied to functions.
FUNCTIONS = [
    "post-fix-sibling-scan",
    "ship-risk-scoring",
    "audit-reverify",
    "forward-bug-hunt",
    "verify-against-reality",
]

# The shipped default manifest (§3c) — the author's companion skills. DISCLOSED at
# init, user-overridable in one place, and unforget works with NO manifest at all.
SHIPPED_DEFAULT = {
    "post-fix-sibling-scan": ("bug-echo", "/bug-echo", "https://github.com/Terryc21/bug-echo"),
    "ship-risk-scoring": ("one-star-risk", "/one-star-risk", "https://github.com/Terryc21/one-star-risk"),
    "audit-reverify": ("radar-suite", "/radar-suite", "https://github.com/Terryc21/radar-suite"),
    "forward-bug-hunt": ("bug-prospector", "/bug-prospector", "https://github.com/Terryc21/bug-prospector"),
    # 5th function ships UNSET with a suggestion (§8 lean) — no obvious single author skill.
    "verify-against-reality": (None, None, None),
}

# Why each function fires — used in the resolved expression so the handoff names the
# EARNED reason, never a generic "you might like these skills."
FIRE_REASON = {
    "post-fix-sibling-scan": "you just closed a code fix — this finds its siblings elsewhere",
    "ship-risk-scoring": "a 🔴 THIS row is nearing release — this scores its ship risk",
    "audit-reverify": "you're closing an audit finding — this re-verifies it held",
    "forward-bug-hunt": "no pattern to infer from a recent fix — this hunts forward for bugs",
    "verify-against-reality": "a done-verified row lacks device/user evidence — this checks it against reality",
}

DEFAULT_MANIFEST = Path.home() / ".claude" / "unforget-companions.md"


def render(mapping: dict) -> str:
    """Render the marker-delimited manifest table from a {function: (skill, invoke, url)} map."""
    lines = [
        BEGIN,
        "# unforget companion manifest  (global; projects inherit)",
        "",
        "> The default recommends the author's companion skills. It is user-overridable here in one",
        "> place, and unforget functions fully with NO manifest at all — handoffs simply don't fire.",
        "> Swap any mapping freely (map a function to an Axiom skill or any other), or unset it.",
        "",
        "| function | skill | invoke | url (only used if not installed) |",
        "|---|---|---|---|",
    ]
    for fn in FUNCTIONS:
        skill, invoke, url = mapping.get(fn, (None, None, None))
        lines.append(f"| {fn} | {skill or '(unset)'} | {invoke or '—'} | {url or '—'} |")
    lines += ["", END]
    return "\n".join(lines)


def parse(text: str) -> dict:
    """Parse the manifest table between the markers into {function: (skill, invoke, url)}."""
    start = text.find(BEGIN)
    end = text.find(END, start) if start != -1 else -1
    block = text[start:end] if (start != -1 and end != -1) else text
    mapping = {}
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        fn = cells[0]
        if fn not in FUNCTIONS:  # skip header/separator/unknown rows
            continue
        skill = None if cells[1] in ("", "(unset)", "—") else cells[1]
        invoke = None if cells[2] in ("", "—") else cells[2]
        url = None if cells[3] in ("", "—") else cells[3]
        mapping[fn] = (skill, invoke, url)
    # fill any function absent from the file as unset
    for fn in FUNCTIONS:
        mapping.setdefault(fn, (None, None, None))
    return mapping


def read_manifest(path: Path) -> dict:
    if not path.exists():
        return {fn: (None, None, None) for fn in FUNCTIONS}
    return parse(path.read_text(encoding="utf-8", errors="replace"))


def invocable_set(args) -> set:
    """The authoritative set of invocable skill names, passed in by the caller."""
    names = set()
    if getattr(args, "invocable", None):
        names |= {n.strip().lstrip("/") for n in args.invocable.split(",") if n.strip()}
    if getattr(args, "invocable_file", None):
        p = Path(args.invocable_file)
        if p.exists():
            names |= {ln.strip().lstrip("/") for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()}
    return names


def resolve(mapping: dict, fn: str, invocable: set) -> dict:
    skill, invoke, url = mapping.get(fn, (None, None, None))
    reason = FIRE_REASON.get(fn, "an earned ledger transition")
    if skill is None:
        return {
            "function": fn, "skill": None, "state": "unset", "invoke": None, "url": None,
            "expression": f"No skill mapped for `{fn}` — {reason}. Consider mapping one in the companion manifest.",
            "advisory": "function unset in the manifest; no URL invented",
        }
    # detection by INVOCABLE NAME (§4a) — never a dir find.
    if skill.lstrip("/") in invocable:
        return {
            "function": fn, "skill": skill, "state": "installed",
            "invoke": invoke, "url": None,  # no URL when installed
            "expression": f"Run `{invoke}` — {reason}.",
            "advisory": f"{skill} is invocable; recommend the action, no URL",
        }
    # not installed: ONE soft pointer, URL surfaced from the manifest only.
    return {
        "function": fn, "skill": skill, "state": "not-installed",
        "invoke": invoke, "url": url,
        "expression": (f"`{fn}` isn't installed — `{skill}` fills it"
                       + (f" ({url})" if url else "") + f". {reason[0].upper()}{reason[1:]}."),
        "advisory": "not invocable; one soft manifest-sourced pointer",
    }


def rotcheck(mapping: dict, invocable: set) -> list:
    """A mapped skill that is neither invocable NOR carries a URL is rotted (§4c)."""
    rotted = []
    for fn in FUNCTIONS:
        skill, invoke, url = mapping.get(fn, (None, None, None))
        if skill is None:
            continue  # unset is not rot — it's an honest gap
        if skill.lstrip("/") not in invocable and not url:
            rotted.append({
                "function": fn, "skill": skill,
                "message": f"companion `{skill}` for `{fn}` is neither installed nor reachable — update the manifest",
            })
    return rotted


def main() -> int:
    parser = argparse.ArgumentParser(description="unforget companion-skill manifest + handoff resolver.")
    sub = parser.add_subparsers(dest="action", required=True)

    i = sub.add_parser("init", help="seed the shipped-default manifest (won't clobber a customized one)")
    i.add_argument("--file", default=str(DEFAULT_MANIFEST))
    i.add_argument("--force", action="store_true", help="overwrite an existing manifest")

    r = sub.add_parser("read", help="print the manifest as JSON")
    r.add_argument("--file", default=str(DEFAULT_MANIFEST))

    rs = sub.add_parser("resolve", help="resolve a function to its handoff expression")
    rs.add_argument("--function", required=True, choices=FUNCTIONS)
    rs.add_argument("--file", default=str(DEFAULT_MANIFEST))
    rs.add_argument("--invocable", default=None, help="comma-separated invocable skill names")
    rs.add_argument("--invocable-file", default=None, help="file with one invocable skill name per line")

    rc = sub.add_parser("rotcheck", help="flag manifest entries neither installed nor reachable")
    rc.add_argument("--file", default=str(DEFAULT_MANIFEST))
    rc.add_argument("--invocable", default=None)
    rc.add_argument("--invocable-file", default=None)

    args = parser.parse_args()
    path = Path(args.file)

    if args.action == "init":
        if path.exists() and not args.force:
            existing = read_manifest(path)
            print(json.dumps({
                "file": str(path), "action": "kept",
                "advisory": "a manifest already exists; kept it (pass --force to reseed). "
                            "The default recommends the author's skills, is overridable here, and "
                            "unforget works with no manifest at all.",
                "functions": {fn: existing[fn][0] for fn in FUNCTIONS},
            }))
            return 0
        path.parent.mkdir(parents=True, exist_ok=True)
        # rewrite only between markers if the file exists with other content
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            start = text.find(BEGIN)
            if start != -1:
                e = text.find(END, start)
                e = e + len(END) if e != -1 else len(text)
                text = text[:start] + render(SHIPPED_DEFAULT) + text[e:]
            else:
                text = text.rstrip() + "\n\n" + render(SHIPPED_DEFAULT) + "\n"
            path.write_text(text, encoding="utf-8")
        else:
            path.write_text(render(SHIPPED_DEFAULT) + "\n", encoding="utf-8")
        print(json.dumps({
            "file": str(path), "action": "seeded",
            "disclosure": ("The default manifest recommends the author's companion skills "
                           "(bug-echo, one-star-risk, radar-suite, bug-prospector; the 5th is unset). "
                           "It is user-overridable in this one file, and unforget functions fully with "
                           "no manifest at all — handoffs simply don't fire. Swap any mapping freely."),
            "functions": {fn: SHIPPED_DEFAULT[fn][0] for fn in FUNCTIONS},
        }))
        return 0

    if args.action == "read":
        mapping = read_manifest(path)
        print(json.dumps({"file": str(path),
                          "manifest": {fn: {"skill": mapping[fn][0], "invoke": mapping[fn][1],
                                            "url": mapping[fn][2]} for fn in FUNCTIONS}}))
        return 0

    if args.action == "resolve":
        mapping = read_manifest(path)
        result = resolve(mapping, args.function, invocable_set(args))
        json.dump(result, sys.stdout); sys.stdout.write("\n")
        return 1 if result["state"] == "unset" else 0

    # rotcheck
    mapping = read_manifest(path)
    rotted = rotcheck(mapping, invocable_set(args))
    print(json.dumps({"file": str(path), "rotted": rotted, "clean": not rotted,
                      "advisory": ("no rotted companion entries" if not rotted
                                   else f"{len(rotted)} companion entry(ies) neither installed nor reachable")}))
    return 1 if rotted else 0


if __name__ == "__main__":
    sys.exit(main())
