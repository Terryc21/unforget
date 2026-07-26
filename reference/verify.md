# `/unforget verify` (a.k.a. doctor): the integrity lint

> Authoritative spec for the read-only integrity check (Maintenance & Integrity
> design spec §4). `verify` audits a ledger for the decay failures that let a
> row mislead a reader — and gates `archive`/`promote` so a ship decision can't
> be made over an unresolved contradiction or an unproven "done."

## What it does

Runs a set of checks over every row (and, given `--dir`, the registry), and
reports a **severity-ranked finding list** — most-severe first, each with the
row ID and a one-line defect. It is the checkpoint that turns "a row misled a
session" into "the lint caught it before it misled anyone."

**Read-only by default.** `verify` (no flags) NEVER edits — it reports; fixes are the
user's call. The one scoped exception is **`verify --fix`**, which offers to resolve
**char-budget findings only** by splitting an over-budget row into a bounded index +
a detail block, **per row with approval** (`scripts/row_budget.py`, lossless-verified
— it refuses any split it can't prove preserves every character). It never auto-edits
contradictions, tiers, or any other finding. See `reference/commands.md` §
`/unforget verify --fix` and `reference/format.md` § Row-length discipline.

## The checks (§4a)

| Check | Severity | Catches |
|---|---|---|
| **contradiction** — a `done-verified`/`withdrawn` token over narration that says "re-opened"/"still broken"/"still owed" | error | a row that contradicts itself (the U5 failure) |
| **tier** — `done-verified` with no `@verified` tier, or backed only by `session-claimed` | error | verification-laundering (a claim posing as a proof) |
| **unknown-value** — an `@status`/`@verified` value not in the enum | error | typos / drift in the token vocabulary |
| **this-blocker** — a 🔴 THIS row not proven (`done-verified` clean) | error if it CLAIMS done (`done-verified`/`done-unverified`); warn if merely open | a "done" ship-blocker that isn't actually proven |
| **char-budget** — a Status or Finding cell over the budget (default 400) | warn | the multi-KB bloat (Phase 7 owns the full row-length rule) |
| **stale-recipe** — a row whose Finding cites a file path but carries no verify-still-open recipe | warn | a premise that may have silently decayed as code moved |
| **registry / registry-drift** — no registry block, or the `.unforget.json` cache disagrees with the README | warn | a stranded/mis-registered ledger; cache drift |

**Errors fail the gate; warnings do not.** Warnings are hygiene the user should
address but that don't block a ship decision.

## Behavior (§4b)

- **On demand:** `/unforget verify` reports the finding list. Exit 1 when any
  error-severity finding exists (gate would fail), else exit 0.
- **As a pre-`archive` / pre-`promote` GATE:** those commands run `verify` first.
  A ship/relocation decision is refused while any error-severity finding stands —
  the same way `promote` already refuses over unresolved 🔴 THIS rows. See the
  gate wiring in `reference/promotion.md` and the archive steps in
  `reference/commands.md`.

## The `verify-still-open` recipe check (§4c)

The format already suggests open rows carry a 10-second grep recipe that
confirms the row's premise still matches source (`reference/format.md` §
Verify-still-open recipe). `verify` makes it enforceable: a row whose Finding
cites a file path but carries no recipe is flagged (stale-recipe, warn), because
its premise can silently decay when a refactor moves the cited code. This is the
structural catch for "the row now describes code that changed."

## Preferred implementation

```
python3 scripts/verify_ledger.py --file <UNFORGET.md> [--dir <ledger-dir>] [--char-budget N]
```

- `--dir` (the directory holding `README.md`/`.unforget.json`) enables the
  registry-drift check.
- `--char-budget` overrides the per-cell budget (default 400).
- Returns `{rows_checked, findings[], error_count, warn_count, gate_pass, advisory}`.
- **Exit 0** = gate passes (no errors; warnings may exist). **Exit 1** = gate
  FAILS (≥1 error; `archive`/`promote` should refuse). **Exit 2** = usage error.

**Algorithm fallback** (Python unavailable): for each row, parse its `@status`
token (see `reference/status.md`); flag as ERROR a contradiction (done/closed
token over "re-opened"/"still broken"/"still owed" narration), a `done-verified`
lacking a device/user tier or backed by `session-claimed`, an unknown status
value, and a THIS row that claims done but isn't cleanly `done-verified`. Flag as
WARN a Status/Finding cell over ~400 chars, a file-citing row with no
verify-still-open recipe, and (if a registry exists) a cache that disagrees with
the README. Gate fails if any ERROR is present.

## Backward compatibility

On a v1 (tokenless) ledger, `verify` produces only WARNINGS (bloat, stale-recipe,
open THIS rows) and **no errors** — the gate passes. A legacy ledger is never
blocked from archive/promote by the token checks, since it has no tokens to
violate. Warnings still surface real hygiene (e.g. a 7,000-char cell), inviting
an upgrade without forcing one.
