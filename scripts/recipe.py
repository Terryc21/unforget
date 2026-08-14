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

# Allowlist. Everything else reports `unrunnable` rather than executing.
#
# `security` and `git` are deliberately ABSENT. One recipe in the source corpus is
# `security find-generic-password -s github-pat -a $USER -w`, and per that tool's own
# usage text `-w` means "Display only the password on stdout" -- the entire output is
# a credential. `git` is a large surface with write subcommands and is not worth the
# exposure for the five read-only uses found.
ALLOWED_COMMANDS = frozenset({
    "grep", "rg", "ls", "test", "find", "awk", "sed", "wc", "head", "tail", "python3",
})

# Shell metacharacters. Their presence makes a recipe unrunnable rather than being
# escaped: no shell is ever spawned, and a `|` inside a markdown table cell splits
# the row anyway (it broke a real row in the source ledger).
SHELL_CHARS = ("|", ";", "&&", "||", ">", "<", "`", "$(", "$", "~", "*", "?", "\n")

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


def screen(command: str) -> str | None:
    """Return a refusal reason, or None if the command may run."""
    for ch in SHELL_CHARS:
        if ch in command:
            return f"contains shell metacharacter {ch!r} (no shell is spawned; rewrite it without one)"
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return f"unparseable: {exc}"
    if not argv:
        return "empty command"
    if argv[0] not in ALLOWED_COMMANDS:
        return f"{argv[0]!r} is not on the allowlist"
    for token in argv[1:]:
        if token.startswith("/"):
            return "absolute path (recipes must be repo-relative)"
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

    argv = shlex.split(recipe["command"])
    try:
        proc = subprocess.run(
            argv, cwd=root, capture_output=True, text=True,
            timeout=TIMEOUT_SECONDS, shell=False,
        )
    except FileNotFoundError:
        result.update(outcome=Outcome.DECAYED, detail=f"{argv[0]!r} not found", actual=None)
        return result
    except subprocess.TimeoutExpired:
        result.update(outcome=Outcome.DECAYED, detail=f"timed out after {TIMEOUT_SECONDS}s", actual=None)
        return result

    stdout = proc.stdout.strip()

    # A missing target is DECAYED, never a passing zero. This is the false-pass the
    # runner exists to catch: a grep on a moved path prints nothing and exits
    # non-zero, which reads identically to "the defect is gone".
    stderr_low = proc.stderr.lower()
    if "no such file" in stderr_low or "not found" in stderr_low:
        result.update(
            outcome=Outcome.DECAYED,
            detail="target path does not exist -- the recipe can no longer observe what it checks",
            actual=None,
        )
        return result

    # grep -c prints one count per file when given several; sum them.
    numbers = re.findall(r"^(?:.*:)?(\d+)$", stdout, re.M)
    if numbers:
        actual = sum(int(n) for n in numbers)
    elif stdout == "":
        # Exit 1 with no output is grep's "no matches": a real zero.
        actual = 0
    else:
        result.update(
            outcome=Outcome.DECAYED,
            detail=f"output is not a count: {stdout[:60]!r}",
            actual=None,
        )
        return result

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
