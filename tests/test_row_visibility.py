#!/usr/bin/env python3
"""Regression bench for row VISIBILITY and the cell-count check.

Why this file exists
--------------------
On 2026-07-31, a field session against a mature 3-ledger installation found that
`ROW_ID_RE` did not match two real id shapes:

    A48a, A48b   a finding split into sub-rows with a letter suffix
    MI-08        a hyphenated prefix used by a scoped sibling ledger

Rows it does not match are invisible to EVERY check in the lint. The concrete
damage: two 🔴 THIS ship-blockers (A48a, A48b) were silently excluded from the
release gate, which reported 2 blockers when 4 existed, and an entire sibling
ledger (MI-UNFORGET, all rows hyphen-prefixed) reported `rows_checked: 0` while
looking perfectly healthy.

A false negative in the release gate is the worst failure this tool has: it does
not merely miss a problem, it actively reports "clear" over a blocker. These
tests exist so that class of bug cannot return silently.

Run:  python3 tests/test_row_visibility.py     (exit 0 = pass)
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import parse_status  # noqa: E402
import verify_ledger  # noqa: E402

FAILURES = []


def check(label, actual, expected):
    ok = actual == expected
    print(f"  {'PASS' if ok else 'FAIL'}  {label}"
          + ("" if ok else f"  (got {actual!r}, want {expected!r})"))
    if not ok:
        FAILURES.append(label)


# --- 1. id grammar: shapes that MUST be visible ------------------------------
print("row-id grammar — must match:")
for rid in ["| A1 | x |", "| A48a | x |", "| A48b | x |", "| MI-08 | x |",
            "| S3 | x |", "| U12 | x |", "| **S12** | x |", "| 1 | x |",
            "| 12 | x |", "| ABC-99z | x |"]:
    check(f"matches {rid.split('|')[1].strip()!r}",
          bool(parse_status.ROW_ID_RE.match(rid)), True)

# --- 2. non-rows that must STAY invisible ------------------------------------
print("\nrow-id grammar — must NOT match (headers, separators, prose):")
for line in ["| # | Target | Finding |", "|---|---|---|", "| --- | --- |",
             "|  | |", "| Detail | x |", "| Risk: Fix | x |", "| Urgency | x |",
             "| Status | x |"]:
    check(f"ignores {line[:22]!r}",
          bool(parse_status.ROW_ID_RE.match(line)), False)

# --- 3. cell-count check: catches a stray pipe, no false positives -----------
LEDGER = """# t

<!-- unforget-format: v2 -->

| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|---|
| A1 | SOMEDAY | clean row | LOW | Low | Low | Good | 1 file | Small | `@status:open` |
| A2 | SOMEDAY | broken by grep 'a\\|b' | LOW | Low | Low | Good | 1 file | Small | `@status:open` |
| A3a | SOMEDAY | suffixed id, clean | LOW | Low | Low | Good | 1 file | Small | `@status:open` |

| # | Finding | Phase | Model | Status |
|---|---|---|---|---|
| MI-08 | narrower table must not false-positive | 3 | opus | `@status:open` |

| # | Why |
|---|---|
| HC-01 | a header with NO Status column must still set the width |
"""

print("\ncell-count check:")
with tempfile.TemporaryDirectory() as td:
    f = Path(td) / "UNFORGET.md"
    f.write_text(LEDGER, encoding="utf-8")
    out = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_ledger.py"), "--file", str(f)],
        capture_output=True, text=True,
    )
    data = json.loads(out.stdout)

    # All four rows must be SEEN — including the suffixed and hyphenated ids.
    check("rows_checked counts every id shape", data["rows_checked"], 5)

    cc = [x for x in data["findings"] if x["check"] == "cell-count"]
    check("exactly one cell-count finding", len(cc), 1)
    check("flags the pipe-broken row", cc[0]["id"] if cc else None, "A2")
    check("cell-count is error severity",
          cc[0]["severity"] if cc else None, "error")
    # The 5-column sprint table must NOT be measured against the 10-column header.
    check("no false positive on the narrower table",
          [x["id"] for x in cc if x["id"] == "MI-08"], [])
    # A header with no Status column is still a header. Before 2026-08-20 only a
    # header matching HEADER_CELL_RE (which requires the literal word "Status")
    # reset the width, so a 2-col table left `declared` pinned to the previous
    # table's 10 and every row under it errored. Shipped as 9 false errors on a
    # live AUDIT ledger, failing its gate.
    check("no false positive on a Status-less header",
          [x["id"] for x in cc if x["id"] == "HC-01"], [])

# --- 4. contradiction matching: no false positives on ordinary prose ---------
# Bare substring matching produced three FP classes in the field (2026-07-31).
# A false contradiction sets archivable=False, so the row is held out of archive
# forever while a human hunts a conflict that was never there.
print("\ncontradiction matching:")
ROW = ("| A1 | THIS | finding | HIGH | Low | High | Good | 1 file | Small | {} |")
for cell, expect, label in [
    ("`@status:done-verified` · viewers can still open + view detail", False,
     "verb phrase 'still open +' is not a contradiction"),
    ("`@status:done-verified` · users can still open the sheet", False,
     "verb phrase 'still open the' is not a contradiction"),
    ("`@status:done-verified` · not a blocker", False,
     "negated 'blocker' is not a contradiction"),
    ("`@status:done-unverified` `@verified:code` · round-trip owed", False,
     "a row's own @status token is not narration"),
    ("`@status:done-verified` · the issue is still open", True,
     "adjective 'still open' IS a contradiction"),
    ("`@status:done-verified` · this is a blocker", True,
     "'blocker' IS a contradiction"),
    ("`@status:done-verified` · re-opened 07/30", True,
     "'re-opened' IS a contradiction"),
    ("`@status:withdrawn` · still broken", True,
     "withdrawn over 'still broken' IS a contradiction"),
]:
    got = any("narration says" in i
              for i in parse_status.parse_row(ROW.format(cell))["issues"])
    check(label, got, expect)

# --- 5. status_cell reads the ROW's token, not one quoted in prose -----------
# Found 2026-08-11 editing a live ledger. `status_cell` scanned first-cell-FORWARD
# for the first cell carrying a token, and Finding precedes Status — so a row that
# quoted a status token illustratively (rows documenting the format do this, and so
# does any row citing a sibling row's state) had the QUOTED token become its status
# for every consumer: list, archive, and the release gate. Concrete damage: an
# `open` row quoting `done-verified` parsed as done-verified and failed the gate
# with a contradiction error that blamed the row's prose. Scanning backward returns
# the rightmost token, which is the real Status cell in every layout the format
# allows — including with the optional 1-Star Risk column appended after Status,
# since that column carries no token. Both directions are asserted below.
print("\nstatus_cell token selection:")
QUOTE = ("| A1 | THIS | sibling is `@status:done-verified` here | HIGH | Low | High "
         "| Good | 1 file | Small | `@status:open` · really open |")
check("a token quoted in Finding does not hijack status",
      parse_status.parse_row(QUOTE)["status"], "open")

RISK = ("| A2 | THIS | finding | HIGH | Low | High | Good | 1 file | Small "
        "| `@status:open` · open | 1★ MED |")
check("1-Star Risk column after Status still parses (no regression)",
      parse_status.parse_row(RISK)["status"], "open")

TIER = ("| A3 | THIS | cites `@status:open` sibling | HIGH | Low | High | Good "
        "| 1 file | Small | `@status:done-verified` `@verified:device` · done |")
check("quoted token does not shadow the real tier either",
      parse_status.parse_row(TIER)["verified"], "device")

# --- 6. quoted status tokens are warned about at WRITE time ------------------
# The parser fix above keeps the TOOL correct, but a quoted token is still a live
# hazard for humans: CLAUDE.md documents `grep -c '@status:done-verified'` as the
# ship-gate reading, and grep counts a quoted token as a real row. This is the
# original S70 report (2026-07-31): a row written ABOUT the token format made
# done-verified read 5 when the true count was 4. Warn where it can be fixed.
print("\nquoted-status-token warning:")
HDR = ("| # | Target | Finding | Urgency | Risk:Fix | Risk:No Fix | ROI | Blast "
       "| Effort | Status |\n|---|---|---|---|---|---|---|---|---|---|\n")


def _checks(row):
    findings, _blockers = verify_ledger.check_rows(HDR + row, 400)
    return findings


quoted = _checks(QUOTE)
check("warns when a Finding quotes a literal token",
      any(f["check"] == "quoted-status-token" for f in quoted), True)
check("the warning names the offending token",
      any("done-verified" in f["message"]
          for f in quoted if f["check"] == "quoted-status-token"), True)
check("it is a warn, not an error (does not block the gate)",
      all(f["severity"] == "warn"
          for f in quoted if f["check"] == "quoted-status-token"), True)

CLEAN = ("| A4 | THIS | an ordinary finding with no token | HIGH | Low | High "
         "| Good | 1 file | Small | `@status:open` · open |")
check("no false positive on a row with no quoted token",
      any(f["check"] == "quoted-status-token" for f in _checks(CLEAN)), False)

# A contradiction on a row that ALSO quotes a token is very likely caused by the
# quote. The bare message ("token says X but narration says Y") points the author
# at the innocent half — earned 2026-08-11, when it did exactly that.
BOTH = ("| A5 | THIS | cites `@status:done-verified` | HIGH | Low | High | Good "
        "| 1 file | Small | `@status:withdrawn` · still broken |")
contra = [f for f in _checks(BOTH) if f["check"] == "contradiction"]
check("contradiction fires alongside the quote", len(contra), 1)
check("contradiction message points at the quote, not the prose",
      "likely cause" in contra[0]["message"] if contra else False, True)

# --- ship_ready / this_open (§6b) -----------------------------------------
# The SHIP question is distinct from the ARCHIVE/PROMOTE gate. check_rows now
# also returns `blockers` — EVERY 🔴 THIS row still blocking release,
# regardless of status — so the caller can report this_open even for
# honestly-`open` rows that keep gate_pass true. Guards the 2026-09-05 misread:
# an open, device-reproduced ship-blocker read as "gate PASSES / ship ready".
print("\nship_ready / this_open:")


def _blockers(row):
    _findings, blockers = verify_ledger.check_rows(HDR + row, 400)
    return {b["id"] for b in blockers}


OPEN_THIS = ("| B1 | THIS | a device-reproduced blocker, honestly open | HIGH "
             "| Low | High | Good | 1 file | Small | `@status:open` · open |")
check("an OPEN 🔴 THIS row is a ship blocker (in this_open)",
      "B1" in _blockers(OPEN_THIS), True)
check("...but an open blocker is only a WARN, so the archive gate still passes",
      all(f["severity"] == "warn"
          for f in _checks(OPEN_THIS) if f["check"] == "this-blocker"), True)

UNVER_THIS = ("| B2 | THIS | code done, device proof owed | HIGH | Low | High "
              "| Good | 1 file | Small | `@status:done-unverified` · owed |")
check("a done-unverified 🔴 THIS row is a ship blocker",
      "B2" in _blockers(UNVER_THIS), True)
check("...and it IS an error (claims done without proof — blocks the gate too)",
      any(f["severity"] == "error"
          for f in _checks(UNVER_THIS) if f["check"] == "this-blocker"), True)

CLEAN_THIS = ("| B3 | THIS | proven and closed | HIGH | Low | High | Good "
              "| 1 file | Small | `@status:done-verified` `@verified:device` |")
check("a clean done-verified 🔴 THIS row is NOT a ship blocker",
      "B3" in _blockers(CLEAN_THIS), False)

OPEN_NEXT = ("| B4 | NEXT | open but targeted at a later release | HIGH | Low "
             "| High | Good | 1 file | Small | `@status:open` · open |")
check("an open row targeted NEXT (not THIS) is NOT a ship blocker",
      "B4" in _blockers(OPEN_NEXT), False)

print()
if FAILURES:
    print(f"FAIL — {len(FAILURES)} assertion(s): {', '.join(FAILURES)}")
    sys.exit(1)
print("All row-visibility + cell-count assertions passed.")
