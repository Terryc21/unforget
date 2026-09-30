#!/usr/bin/env python3
"""Parse and (optionally) execute the verify recipes carried by ledger rows.

WHY THIS EXISTS
---------------
`verify`'s `stale-recipe` check confirms a recipe EXISTS. It never runs one. A row
can carry a recipe that has been wrong for months and pass the gate clean.

Measured on one real 64-row ledger in a single session (2026-08-13), four failure
classes that a runner catches and a human review did not:

  fixed-unnoticed  a row's own recipe already reported the CLOSED value; the fix had
                   shipped weeks earlier and nobody closed the row
  too-narrow       recipe checked 1 of the 7 symbols the file exported
  drifted          recipe predicted a count of 1; the real count was 3
  decayed          recipe pointed at a moved path, so it printed nothing and exited
                   non-zero -- indistinguishable from "the defect is gone"

`decayed` is the load-bearing one. A grep against a path that no longer exists looks
exactly like a passing check if you only read the count, which is why the expectation
must be compared separately from the exit status.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
A recipe verifies a PREMISE, never a JUDGMENT. Three real defects from the same
session pass a recipe check cleanly: a row that miscounted record types, one that
sized a 284-line refactor as "Small", and one that overstated a cost by 3x. Those
need a human read. Claiming otherwise would rebuild the false-confidence failure this
tool exists to prevent.

GRAMMAR
-------
    **Verify:** `grep -c 'X' path/File.swift` -> expect 1 [open]
    **Verify:** `grep -c 'Y' path/File.swift` -> expect >=1 [closed]

  -> expect <op><value>   assertion; operators = >= <= > < !=  (bare number means =)
  [open] / [closed]       WHICH STATE the expectation describes. This is what makes
                          an inverted recipe representable instead of a prose aside.

Prose recipes (no `expect` clause) stay valid and report `unrunnable`. A ledger that
adopts nothing keeps working exactly as before.

USAGE
    python3 recipe.py parse --file UNFORGET.md
    python3 recipe.py run   --file UNFORGET.md --root /path/to/repo
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

# --- grammar ---------------------------------------------------------------

# The command, then the assertion. Both the em-dash and ASCII arrow forms are
# accepted: ledgers are hand-written markdown and both occur (the detail-pointer
# check was blind to em-dash ledgers for a full release for exactly this reason).
RECIPE_RE = re.compile(
    r"`([^`]+)`"                       # the command, in backticks
    r"\s*(?:->|→|=>)\s*"               # arrow
    r"expect\s*(=|>=|<=|>|<|!=)?\s*"   # optional operator (default =)
    r"(-?\d+)"                         # expected integer
    r"\s*\[(open|closed)\]",           # which state this describes
    re.IGNORECASE,
)

ROW_ID_RE = re.compile(r"^\|\s*\*{0,2}([A-Za-z]{0,3}-?\d+[a-z]?)\*{0,2}\s*\|")

# Only count searches: grep/rg -c [-i] [-F|-E] [-e] PATTERN [--] FILE...
# No shell, recursive search, preprocessors, config, or executable wrappers.
SHELL_CHARS = ("|", ";", "&", ">", "<", "`", "$", "\n", "\r")

TIMEOUT_SECONDS = 5


class Outcome:
    HOLDS = "HOLDS"            # ran, matched the [open] expectation
    FIXED = "FIXED"            # ran, matched the [closed] expectation
    DRIFTED = "DRIFTED"        # ran, matched neither
    DECAYED = "DECAYED"        # could not observe its target at all
    UNRUNNABLE = "UNRUNNABLE"  # prose, or refused by policy


def parse_recipes(text: str) -> list[dict]:
    """Every runnable recipe in the ledger, tagged with its row id."""
    out = []
    for line in text.split("\n"):
        m = ROW_ID_RE.match(line)
        if not m:
            continue
        rid = m.group(1)
        if rid.lower() in ("#", "id"):
            continue
        for rm in RECIPE_RE.finditer(line):
            command, op, value, state = rm.groups()
            out.append({
                "id": rid,
                "command": command.strip(),
                "op": op or "=",
                "expected": int(value),
                "describes": state.lower(),
            })
    return out


def command_args(command: str) -> tuple[list[str], list[str]]:
    if any(ch in command for ch in SHELL_CHARS):
        raise ValueError("shell syntax is unsupported")
    argv = shlex.split(command)
    if not argv or argv[0] not in ("grep", "rg"):
        raise ValueError("only grep/rg count searches are supported")
    tool = argv.pop(0)
    opts = []
    while argv and argv[0].startswith("-") and argv[0] not in ("-e", "--"):
        opt = argv.pop(0)
        if opt not in ("-c", "--count", "-i", "-F", "-E") or (tool == "rg" and opt == "-E"):
            raise ValueError("unsupported search option: " + opt)
        opts.append(opt)
    if not any(o in ("-c", "--count") for o in opts):
        raise ValueError("a count option (-c) is required")
    if argv and argv[0] in ("-e", "--"):
        argv.pop(0)
    if len(argv) < 2:
        raise ValueError("a pattern and explicit regular files are required")
    pattern, *files = argv
    if files and files[0] == "--":
        files = files[1:]
    if not files:
        raise ValueError("explicit regular files are required")
    for name in files:
        if name.startswith(("-", "/", "~")) or ".." in Path(name).parts or "\\" in name:
            raise ValueError("files must be in-root relative paths, not options or traversal")
    # Force numeric-only output; patterns cannot become filenames or options.
    prefix = [tool, "--no-config"] if tool == "rg" else [tool]
    return prefix + opts + ["-h" if tool == "grep" else "--no-filename", "-e", pattern, "--"], files


def screen(command: str) -> str | None:
    try:
        command_args(command)
    except ValueError as exc:
        return str(exc)
    return None


def compare(actual: int, op: str, expected: int) -> bool:
    return {
        "=": actual == expected,
        "!=": actual != expected,
        ">=": actual >= expected,
        "<=": actual <= expected,
        ">": actual > expected,
        "<": actual < expected,
    }[op]


def run_recipe(recipe: dict, root: Path) -> dict:
    """Execute one recipe and classify it into one of the four states."""
    result = dict(recipe)

    refusal = screen(recipe["command"])
    if refusal:
        result.update(outcome=Outcome.UNRUNNABLE, detail=refusal, actual=None)
        return result

    prefix, files = command_args(recipe["command"])
    root = root.resolve()
    paths = []
    for name in files:
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            result.update(outcome=Outcome.UNRUNNABLE, detail="file escapes recipe root", actual=None)
            return result
        if not path.is_file():
            result.update(outcome=Outcome.DECAYED, detail="target is not a regular file", actual=None)
            return result
        paths.append(path)
    actual = 0
    # One process per file makes grep/rg's zero-match and multi-file counts unambiguous.
    for path in paths:
        try:
            proc = subprocess.run(prefix + [str(path)], cwd=root, capture_output=True,
                                  text=True, timeout=TIMEOUT_SECONDS, shell=False)
        except (OSError, subprocess.SubprocessError) as exc:
            result.update(outcome=Outcome.DECAYED, detail=str(exc), actual=None)
            return result
        output = proc.stdout.strip()
        no_match = proc.returncode == 1 and output in ("", "0")
        if proc.stderr or (not no_match and (proc.returncode != 0 or not re.fullmatch(r"[0-9]+", output))):
            result.update(outcome=Outcome.DECAYED, detail="search failed or returned malformed count", actual=None)
            return result
        actual += int(output or "0")

    result["actual"] = actual
    matches = compare(actual, recipe["op"], recipe["expected"])

    if recipe["describes"] == "open":
        # Expectation describes the STILL-BROKEN state.
        result["outcome"] = Outcome.HOLDS if matches else Outcome.DRIFTED
        if not matches:
            result["detail"] = (
                f"expected {recipe['op']}{recipe['expected']}, got {actual} -- "
                "the premise moved; re-read the row before trusting it"
            )
    else:
        # Expectation describes the FIXED state.
        result["outcome"] = Outcome.FIXED if matches else Outcome.HOLDS
        if matches:
            result["detail"] = (
                f"recipe reports the CLOSED value ({recipe['op']}{recipe['expected']}, "
                f"got {actual}) -- this row looks already fixed; confirm and close it"
            )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["parse", "run"])
    ap.add_argument("--file", required=True)
    ap.add_argument("--root", default=".", help="repo root that recipe paths resolve against")
    ap.add_argument("--only", help="limit to one row id")
    args = ap.parse_args()

    text = Path(args.file).read_text(encoding="utf-8")
    recipes = parse_recipes(text)
    if args.only:
        recipes = [r for r in recipes if r["id"] == args.only]

    if args.mode == "parse":
        print(json.dumps({"count": len(recipes), "recipes": recipes}, indent=2))
        return 0

    root = Path(args.root).resolve()
    results = [run_recipe(r, root) for r in recipes]
    counts: dict[str, int] = {}
    for r in results:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1

    print(json.dumps({
        "checked": len(results),
        "counts": counts,
        # Anything not HOLDS wants a human read.
        "needs_attention": [r for r in results if r["outcome"] != Outcome.HOLDS],
        "results": results,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
