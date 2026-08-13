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
| **char-budget** — a Status or Finding cell over the budget (default 400) | warn (error above `--char-budget-hard`, default 4x = 1600) | the multi-KB bloat (Phase 7 owns the full row-length rule) |
| **stale-recipe** — a row whose Finding cites a file path but carries no verify recipe (still-open or still-DONE) | warn | a premise that may have silently decayed as code moved |
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

## The `cell-count` check (§4d)

A ledger row must have exactly as many cells as its table's header declares. When it
does not, the cause is almost always an unescaped `|` inside cell prose — a
`grep -c 'a\|b'` verify recipe, a regex alternation, a nested table in a detail note.

The damage is silent and total: every positional column read past the stray pipe shifts
by one, so a Status token can land in a rating cell, a Target badge can be read as a
Finding, and `archive`/`promote` can misjudge a row. That is why this is **error**
severity rather than a warning.

The declared width is read from the nearest preceding header row, so a ledger holding
several tables of different widths (a 10-column Standard section beside a 5-column sprint
table) is handled correctly — the width is per-table, never a global constant.

**Writing a recipe that contains a pipe:** do not backslash-escape it. `\|` is itself
what Markdown splits on in most renderers. Phrase it as prose ("grep for BOTH terms") or
use `grep -E` with the alternation described rather than literal.

## Char-budget severity escalation (§4e)

**Why a warning wasn't enough.** The soft budget (400 chars, `reference/format.md` § Row-length
discipline) has existed since format v2, with `--fix` able to split any over-budget row
losslessly. Despite that, a real ledger (Stuffolio, 2026-08-13) carried a row at **3,707
characters** — 9x budget — through multiple `archive`/`promote` cycles, because `warn` severity
never refused the gate and nothing forced the split to happen. The row's own history (repeated
"RESOLVED", "still owed", "prior arc" narration appended at each status change rather than
migrated to the detail block) was the direct cause of a session misreading the row's *current*
status from its accreted prose — the exact failure `@status` tokens and the Detail block exist
to prevent, defeated by volume rather than by a missing token.

**Two severities, one budget.** `char-budget` now escalates past a second, harder threshold:

- **`--char-budget` (default 400):** unchanged soft budget. Over this: `warn`. Hygiene, not a
  gate blocker — most rows cross 400 briefly and get cleaned up at the next natural touch.
- **`--char-budget-hard` (default 4x the soft budget, i.e. 1600):** a NEW threshold. Over this:
  **`error`**. A row this far over budget is no longer "a bit long" — it is functionally a
  detail block wearing a table cell, and it is the shape that produced the Stuffolio misread.
  Gates `archive`/`promote` the same way a contradiction or an unproven THIS-blocker does.

**Why 4x and not the same threshold as the soft budget.** A hard error at 400 chars would fire
constantly on ordinary rows and train users to ignore `verify` output (the same failure mode
`v2.0.3`'s contradiction-false-positive fix and `v2.1.0`'s quoted-token fix both existed to
avoid). 4x gives real headroom for a row that's legitimately a little long, while still catching
the 9x-and-beyond cases where a row has clearly stopped being an index and started being a
history log. `--char-budget-hard` is independently configurable (registry-settable, same as
`--char-budget`) for ledgers that want a tighter or looser multiple.

**The fix path is unchanged and already sufficient.** `verify --fix` already offers the lossless
split (`scripts/row_budget.py`) for char-budget findings at either severity — escalating the
severity doesn't require new remediation tooling, only makes the existing one-command fix
mandatory before a ship decision instead of optional. See § What it does above.

## The verify recipe check (§4c)

The format already suggests open rows carry a 10-second grep recipe that
confirms the row's premise still matches source (`reference/format.md` §
Verify-still-open recipe). `verify` makes it enforceable: a row whose Finding
cites a file path but carries no recipe is flagged (stale-recipe, warn), because
its premise can silently decay when a refactor moves the cited code. This is the
structural catch for "the row now describes code that changed."

**Both polarities count.** A `done-unverified` row's recipe asks the INVERSE
question — "is the fix still in place?" — and is legitimately labelled
`**Verify-still-DONE:**`. The check accepts `Verify-still-open` and
`Verify-still-DONE` equally. Matching only the "open" spelling flagged those rows
as recipe-less, which pressured authors to relabel a still-DONE recipe as
still-open — silencing the warning by inverting the recipe's stated meaning. Pick
the label that matches what the command actually checks, not the one the linter
recognizes.

## Preferred implementation

```
python3 scripts/verify_ledger.py --file <UNFORGET.md> [--dir <ledger-dir>] [--char-budget N] [--char-budget-hard N]
```

- `--dir` (the directory holding `README.md`/`.unforget.json`) enables the
  registry-drift check.
- `--char-budget` overrides the soft per-cell budget (default 400; over this: warn).
- `--char-budget-hard` overrides the hard per-cell budget (default 4x `--char-budget`,
  i.e. 1600; over this: **error**, gates `archive`/`promote`). See § Char-budget severity
  escalation.
- Returns `{rows_checked, findings[], error_count, warn_count, gate_pass, advisory}`.
- **Exit 0** = gate passes (no errors; warnings may exist). **Exit 1** = gate
  FAILS (≥1 error; `archive`/`promote` should refuse). **Exit 2** = usage error.

**Algorithm fallback** (Python unavailable): for each row, parse its `@status`
token (see `reference/status.md`); flag as ERROR a contradiction (done/closed
token over "re-opened"/"still broken"/"still owed" narration), a `done-verified`
lacking a device/user tier or backed by `session-claimed`, an unknown status
value, a THIS row that claims done but isn't cleanly `done-verified`, **and now a
Status/Finding cell over ~1600 chars (4x the soft budget)**. Flag as WARN a
Status/Finding cell over ~400 chars but under the hard threshold, a file-citing
row with no verify recipe (`Verify-still-open` or `Verify-still-DONE` both
satisfy it), and (if a registry exists) a cache that disagrees with the README.
Gate fails if any ERROR is present.

## Companion handoffs at verify (format v2+)

Two companion-skill handoffs (full mechanic: `reference/skill-handoffs.md`) attach to
`verify`:

- **`verify-against-reality`** — when `verify` finds a `done-verified` row lacking
  device/user evidence (the tier check), it may offer the `verify-against-reality`
  function (a device/sim-test skill, unset by default) so the claim gets checked
  against reality rather than left as an over-claim. Resolve via
  `python3 scripts/companions.py resolve --function verify-against-reality --invocable "<names>"`
  and say the resolver's expression. Governance applies: once/session, advisory only.
- **Manifest rot check (§4c).** `verify` runs
  `python3 scripts/companions.py rotcheck --invocable "<the session's invocable skills>"`
  and reports any manifest entry whose skill is neither invocable NOR carries a URL —
  "companion `X` for `<function>` is neither installed nor reachable; update the
  manifest." An **unset** function is NOT rot (it's an honest gap). This is a WARN; it
  never blocks the gate. Rot is detected, never silently served.

## Backward compatibility

On a v1 (tokenless) ledger, `verify` produces only WARNINGS from the **token**
checks (contradiction, tier, unknown-value, this-blocker) and **no errors** from
them — a legacy ledger is never blocked from archive/promote by checks that need
tokens it doesn't have.

**The char-budget hard-error is the one exception, and it applies to v1 ledgers too.**
A 7,000-char cell is exactly as misleading on a tokenless ledger as on a v2 one — the
failure this escalation exists to catch (a row's current state buried in accreted prose)
has nothing to do with whether tokens are present. Gating archive/promote on it is
consistent with treating it as a real defect rather than a v2-only nicety. `verify --fix`'s
lossless split works identically on a v1 ledger (it operates on cell content, not on
`@status` tokens), so the remediation path is available before the gate is ever hit.

The companion handoffs above are advisory and never affect the gate.
