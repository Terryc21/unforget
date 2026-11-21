# /unforget scan

Part of the unforget command reference; the index is [../commands.md](../commands.md).

---

## /unforget scan

Identify rows past their staleness threshold. Read-only. Never modifies the file.

### Where the ages come from

Run `python3 scripts/row_age.py --file <ledger> --dir <ledger-dir>` and use its output; never
estimate a row's age. For each row it returns `logged` (first seen), `touched` (last changed),
`age_days` (days since `touched`), `stale`, and `date_source`:

- **`git`**: dates from the ledger's commit history (one `git log -p` pass).
- **`uncommitted`**: the row was edited in the working tree and not committed yet, so it was
  touched today.
- **`text`**: git can't date it (a gitignored, local-only ledger, or one never committed), so the
  dates come from those written in the row and its detail block. Say so in the scan output: a
  written date may name an event the row cites rather than an edit to the row.

Rows it cannot date either way come back in `needs_date`; they fill the scan's **Needs date
stamp** section, and are never given a guessed age. A bulk rewrite of the ledger (a format
migration, a token conversion) counts as a git touch for every row it changed.

### Staleness thresholds (default)

A row is stale when it has not changed for longer than its Target's threshold:

| Row | Stale after |
|---|---|
| `open`, `in-progress`, `blocked` or `done-unverified`, Target 🔴 THIS (or no Target) | 30 days |
| same, Target 🔵 NEXT | 90 days |
| same, Target 🟡 LATER | 180 days |
| same, Target ⚪ SOMEDAY | 365 days |
| `done-verified` or `withdrawn` | never stale (listed as ready for archive) |

A v1 ledger's words map the same way: Open, In Progress and Deferred age by Target; Fixed and
Skipped never go stale.

These thresholds are customizable via the registry's `stale_days_this` / `stale_days_next` /
`stale_days_later` / `stale_days_someday` keys (`reference/registry.md` § The schema), settable
through the Thorough tier of `/unforget list --fresh` (`list-preferences.md` § Display-preference interview) or by
hand. A legacy `config` block at the top of UNFORGET.md is still honored if present, but the
registry wins when both are set — see the migration note in `reference/registry.md`.

### Row-length (char-budget) lint (format v2+, maintenance §2c)

`scan` also flags rows that have outgrown the **index budget** — the exact bloat that made a ledger un-Readable (multi-KB rows, Reads that truncate and mislead). Run `python3 scripts/row_budget.py check --file <UNFORGET.md> [--dir <ledger-dir>]`; it returns every Finding/Status cell over the budget (default 400 chars, or the registry's `row_char_budget`). Surface these under an **"Over the index budget (move history to a detail block)"** heading with the cell and its char count, recommendation **investigate** (usually resolvable by a split). This is read-only in `scan`; the split itself is offered by `verify --fix` (below) or run manually. See `reference/format.md` § Row-length discipline.

### Trivial-staleness cross-check (format v2+, deferral-gate §4d)

`scan` sharpens one flag that ties back to the deferral gate: a row that is **Fix
Effort = Trivial AND has survived ≥N sessions un-done** is a near-certain
"should've just done it" — triviality + staleness together is the hindsight
signal that a past deferral was deferral-laundering. Surface these under a
**"Trivial-but-stale (should've been do-now)"** heading in the scan output with
recommendation **investigate** (usually resolvable to a quick do-now). `N` is
registry-configurable via `stale_trivial_sessions` (read from the registry global
block); this is how the user *learns* the pattern over time, not just catches it
in the moment. Read-only like the rest of `scan`. On a v1 ledger with no effort
column populated, this cross-check is skipped.

### Output structure

```
# UNFORGET.md Stale-Scan, <date>

**Ledger snapshot:** N rows across 4 sections.
**Stale rows:** N
**Needs date stamp:** N
**Fixed rows ready for archive:** N

## Stale items
| ID | Target | Status | Age (days) | Title | Recommendation |
| ... |

## Needs date stamp
| ID | Target | Title |
| ... |

## Fixed rows ready for archive
| ID | Title |
| ... |

## Summary
<2-3 sentence narrative covering: how many rows are healthy, which sections need
the most attention, any patterns worth surfacing.>
```

### Recommendation values

For each stale row, the scan picks ONE:

- **investigate**: stale and may need fresh diagnosis
- **promote**: should move toward THIS (e.g., NEXT deferred too long)
- **demote**: Urgency was overstated; downgrade Target
- **archive**: no longer relevant; move to historical archive

Default to **investigate** if uncertain. The scan never modifies UNFORGET.md. It only reports.

### Scheduling

`/unforget scan` is safe to run on demand. For automated recurring scans, the user can schedule it via Claude Code's `/schedule` skill (or any cron-like external scheduler). The skill output is plain markdown, suitable for posting to Slack, email, or GitHub Actions summary.
