# DESIGN — v2.10: offering the ledger view at the right moment

**Status:** SPEC, not implemented. Written 2026-10-06.
**Scope:** when a session should offer the user a view of the ledger, and one format
addition (1-Star Risk and Confidence columns) that makes a "review risk" view possible.
The row limit, effort and ROI filters and the presets are already implemented (see
`CHANGELOG.md`, Unreleased); this note covers only what needs a decision first.

---

## Why

Sessions read and write the ledger constantly, and the user almost never sees it. A session
runs `verify`, edits a row, closes another, and reports a gate summary. The user hears
"gate clear, N errors" and either trusts it or opens a file that is hundreds of KB.
The report and list commands already render any cut of the ledger; nothing prompts the offer.

Measured on one real 234-row ledger (2026-10-06): 29 unfinished rows were Trivial fixes, and
13 further rows carried an effort value no filter could classify ("Done", "N/A"). Neither
fact is visible unless someone asks for that exact cut.

## Part 1 — Triggers (judgment: changes how every session behaves)

Offer on **events**, not on a timer or a usage count. A periodic offer fires when nothing has
changed and teaches the user to dismiss it.

| # | Event | Why it earns an offer |
|---|---|---|
| 1 | A session is about to recommend archiving, promoting or submitting | The decision depends on the backlog's shape, not only on `ship_ready` |
| 2 | A session changed the ledger (rows added, closed, retargeted) | A delta ("3 rows changed") reads far better than the whole file |
| 3 | Session start, only if the ledger changed since the user last saw it | Needs the marker below; an unchanged ledger produces no offer |

**Never offer** when nothing changed, when the user declined in this session, or when the
session is mid-task on something unrelated.

**The offer is one line** naming what changed, then the choices (Part 2). It never prints the
table inline: the full ledger is too large. The table goes to the HTML report; the terminal
gets the "Showing N of M" summary.

**Last-shown marker.** Trigger 3 needs to know what the user last saw. Store, beside the
existing display preferences, the ledger's content hash and a per-row state hash at the time
of the last offer the user accepted. "Changed" means either differs. Open: the exact key and
file (see Decisions).

## Part 2 — Presets and "choose my own" (already implemented as flags)

The offer carries four presets, each mapping to existing flags:

| Preset | Flags |
|---|---|
| Top 10 by urgency | `--limit 10 --sort blocker,urgency` |
| Quick wins | `--effort trivial --effort small --sort roi,urgency` |
| Ship blockers | `--blockers-only` |
| Choose my own | the existing display-preference interview |

Every view states "Showing N of M" and the count of rows it could not classify. A cap never
hides a release blocker. A "trivial only" list is also a finding: the ledger's own tripwire
says trivial fixes should be done, not logged, so a non-empty list means some were deferred.

## Part 3 — 1-Star Risk and Confidence columns (format change)

A "rank by App Store review risk" view needs the data on the row. Some ledgers already carry
it in their local rating spec; the 10-column default does not.

- **Additive and optional.** Two new optional columns after the existing ones. A ledger without
  them reads as before; filters on them treat missing as `unrated` and count those rows.
- **`verify`** gains no new error. A missing column is not a defect.
- **Migration:** none forced. Rows are rated as they are touched, as with every other column.
- **Risk:** the column header set is matched by position in some helpers (`row_budget.py`,
  header-order checks). Each must be audited before the columns ship. This is the one-way-ish
  part of this note and why it needs a decision before code.

## What the user experiences

- **Before:** the ledger is something sessions talk about. The user gets a gate summary and
  must open a large file to see anything, or ask for a specific cut by name.
- **After:** at the moments that matter (a ship decision, or after a session moved rows) the
  user gets one line and can pick a view in one step; when nothing changed, nothing is said.

## Decisions needed

1. **Triggers:** all three, or only 1 and 2? Recommendation: 1 and 2 first; add 3 once the
   marker is proven cheap and correct.
2. **Marker location:** the display-preferences file (per project, already read each time) or a
   new file. Recommendation: the preferences file.
3. **Columns:** add 1-Star Risk and Confidence to the default ledger format, or leave them to
   local rating specs? Recommendation: add as optional, after the helper audit above.
4. **Suppression:** a "stop offering" switch, per session and persistent. Recommendation: both,
   in the same vocabulary the rating and weeds rules already use.
