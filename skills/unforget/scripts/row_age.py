#!/usr/bin/env python3
"""Row ages from git history, so staleness is measured, not guessed.

`scan`, `list --stale` and `list --age=` need each row's age, but a ledger row
carries no date. This script reads the ledger's git history in one pass and
records, for every row ID:

  logged   the date of the first commit that added a table row with that ID
  touched  the date of the last commit that added or changed that row's line

A row edited in the working tree but not committed is touched today (and logged
today if no commit has it yet). Staleness is measured from `touched`: a row is
stale when no one has changed it for longer than its threshold.

When git cannot date a row (the ledger is gitignored, as a local-only ledger is,
or was never committed), the script falls back to the dates written in the row and
its detail block (YYYY-MM-DD or MM/DD/YYYY, none later than today): logged is the
earliest, touched the latest. Each row says which it used in `date_source`
("git", "uncommitted" or "text"), because a date someone wrote is weaker evidence
than a commit: it may name an event the row cites rather than an edit to the row.
A bulk rewrite of the ledger (a format migration, a token conversion) counts as a
git touch for every row it changed.

Thresholds come from the Target (registry keys `stale_days_this|next|later|someday`,
defaults 30/90/180/365). Open, in-progress, blocked and done-unverified rows age;
done-verified and withdrawn rows never go stale (they are ready to archive). A row
with no Target (Continuous preset, Lean rows without one) uses the THIS threshold.

Rows the script cannot date either way are listed under `needs_date`, never given
a guessed age.

Usage:
  python3 row_age.py --file <ledger.md> [--dir <ledger-dir>] [--today YYYY-MM-DD]

Output (stdout, JSON):
  {"file", "git": true|false, "today", "thresholds": {...},
   "rows": [{"id", "target", "status", "logged", "touched", "date_source", "age_days",
             "logged_days", "uncommitted", "threshold", "stale", "ready_to_archive"}],
   "stale": ["<id>", ...], "needs_date": [{"id", "reason"}], "advisory"}

Exit codes: 0 ok; 2 usage error. Read-only: never writes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_status  # noqa: E402
import registry  # noqa: E402

DEFAULT_THRESHOLDS = {"THIS": 30, "NEXT": 90, "LATER": 180, "SOMEDAY": 365}
REGISTRY_KEYS = {"THIS": "stale_days_this", "NEXT": "stale_days_next",
                 "LATER": "stale_days_later", "SOMEDAY": "stale_days_someday"}
COMMIT_MARK = "\x00commit "
TEXT_DATE_RE = re.compile(r"(?<![\d/-])(?:(20\d\d)-(\d\d)-(\d\d)|(\d\d)/(\d\d)/(20\d\d))(?![\d/-])")


def text_dates(text: str, today: dt.date) -> list[dt.date]:
    """Dates written in a row or detail block, none later than today."""
    found = []
    for m in TEXT_DATE_RE.finditer(text):
        y, mo, d = (m[1], m[2], m[3]) if m[1] else (m[6], m[4], m[5])
        try:
            day = dt.date(int(y), int(mo), int(d))
        except ValueError:
            continue
        if day <= today:
            found.append(day)
    return found


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def read_thresholds(dir_path: Path | None) -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if dir_path is None:
        return thresholds
    reg = registry.read_registry(dir_path)
    glob = reg.get("global") or {} if "error" not in reg else {}
    for target, key in REGISTRY_KEYS.items():
        try:
            thresholds[target] = int(str(glob.get(key)).strip())
        except (TypeError, ValueError):
            pass
    return thresholds


def row_id(line: str) -> str | None:
    m = parse_status.ROW_ID_RE.match(line)
    return m[1] if m else None


def history(path: Path) -> tuple[dict, dict, str | None]:
    """(logged, touched, reason-if-undatable) from one `git log -p` pass."""
    cwd = path.parent
    if git(cwd, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        return {}, {}, "not in a git repository"
    tracked = git(cwd, "ls-files", "--error-unmatch", "--", path.name)
    if tracked.returncode != 0:
        return {}, {}, "the ledger has never been committed"
    log = git(cwd, "log", "--reverse", "--no-color", "--no-ext-diff", "-U0", "-p",
              "--format=%x00commit %cI", "--", path.name)
    logged, touched = {}, {}
    date = None
    for line in log.stdout.splitlines():
        if line.startswith(COMMIT_MARK):
            date = line[len(COMMIT_MARK):].strip()[:10]
            continue
        if date is None or not line.startswith("+") or line.startswith("+++"):
            continue
        rid = row_id(line[1:])
        if rid:
            logged.setdefault(rid, date)
            touched[rid] = date
    return logged, touched, None


def committed_lines(path: Path) -> set[str]:
    rel = git(path.parent, "ls-files", "--full-name", "--", path.name).stdout.strip()
    shown = git(path.parent, "show", f"HEAD:{rel}") if rel else None
    return set(shown.stdout.splitlines()) if shown and shown.returncode == 0 else set()


def ages(path: Path, dir_path: Path | None, today: dt.date) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    thresholds = read_thresholds(dir_path)
    logged, touched, reason = history(path)
    in_head = committed_lines(path) if reason is None else set()
    today_s = today.isoformat()

    rows, stale, needs_date = [], [], []
    lines_by_id = {}
    for line in text.splitlines():
        rid = row_id(line)
        if rid:
            lines_by_id.setdefault(rid, line)
    details = parse_status.detail_blocks(text)
    for parsed in parse_status.parse_file(text):
        rid = parsed["id"]
        line = lines_by_id.get(rid, "")
        uncommitted = reason is None and line not in in_head
        if uncommitted:
            t, lg, source = today_s, logged.get(rid) or today_s, "uncommitted"
        elif rid in touched:
            t, lg, source = touched[rid], logged[rid], "git"
        else:
            written = text_dates(line + "\n" + details.get(rid, ""), today)
            if not written:
                needs_date.append({"id": rid, "reason": (reason or "the row's ID is in no commit")
                                   + "; no date written in the row or its detail block"})
                continue
            t, lg, source = max(written).isoformat(), min(written).isoformat(), "text"
        target = parsed.get("target")
        threshold = thresholds.get(target or "THIS", thresholds["THIS"])
        ready = bool(parsed.get("archivable"))
        age = (today - dt.date.fromisoformat(t)).days
        is_stale = (not ready) and age > threshold
        if is_stale:
            stale.append(rid)
        rows.append({
            "id": rid, "target": target, "status": parsed.get("status"),
            "logged": lg, "touched": t, "date_source": source, "age_days": age,
            "logged_days": (today - dt.date.fromisoformat(lg)).days if lg else None,
            "uncommitted": uncommitted, "threshold": None if ready else threshold,
            "stale": is_stale, "ready_to_archive": ready,
        })
    rows.sort(key=lambda r: -r["age_days"])
    from_text = sum(1 for r in rows if r["date_source"] == "text")
    advisory = (f"{len(stale)} stale row(s)" + (f": {', '.join(stale)}" if stale else "")
                + (f"; {from_text} row(s) dated from dates written in the row, not git"
                   if from_text else "")
                + (f"; {len(needs_date)} row(s) need a date ({needs_date[0]['reason']})"
                   if needs_date else ""))
    return {"file": str(path), "git": reason is None, "today": today_s,
            "thresholds": thresholds, "rows": rows, "stale": stale,
            "needs_date": needs_date, "advisory": advisory}


def main() -> int:
    parser = argparse.ArgumentParser(description="Row ages from git history (read-only).")
    parser.add_argument("--file", required=True, help="the ledger (e.g. UNFORGET.md)")
    parser.add_argument("--dir", default=None, help="ledger directory, for registry thresholds")
    parser.add_argument("--today", default=None, help="YYYY-MM-DD (default: today, local time)")
    args = parser.parse_args()
    path = Path(args.file)
    if not path.is_file():
        print(json.dumps({"error": f"file not found: {path}"}), file=sys.stderr)
        return 2
    try:
        today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    except ValueError:
        print(json.dumps({"error": "--today must be YYYY-MM-DD"}), file=sys.stderr)
        return 2
    print(json.dumps(ages(path.resolve(), Path(args.dir) if args.dir else None, today)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
