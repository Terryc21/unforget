# /unforget show

Part of the unforget command reference; the index is [../commands.md](../commands.md).

---

## /unforget show

Show ONE row's current state as a short, synthesized read: what's wrong, its impact, and the
fix. No table, no accreted history. This is the read-time answer to a problem `list`/`--view`
can't solve on their own: a row's rating columns compare well across many rows, but its Detail
block is an append-only history log (`reference/format.md` § Row-length discipline) that grows
without bound and is never re-summarized. A reader who scrolls to a row's detail today gets the
FULL accreted narrative — every arc, every reversal, every "still owed" and "RESOLVED" in the
order they were written — when what they almost always want is: what's true about this row
right now. `show` renders that, on demand, per row, instead of asking every row to compress
itself into an already-crowded table cell (which is what the char-budget rule does) or asking
every reader to mentally re-derive "current" from a paragraph of history (which is what caused
the 2026-08-13 A65 misread this feature traces back to).

### Usage

```
/unforget show A65                    ·  synthesized current-state card for row A65
/unforget show A65 --full             ·  the synthesis, THEN the complete raw Detail-block history below it
```

### What gets shown

Three fields, always in this order, each one to three sentences:

- **Finding** — what's wrong, current tense. Not "was buried" if it's now fixed; not "fixed"
  if a later event reopened it. Reflects the row's LATEST arc only.
- **Impact** — why it matters if left as-is. Pull from the row's Risk:No-Fix column and/or the
  Detail block's own stated consequence, not re-derived from scratch.
- **Fix** — what closes it, or what's blocking closure. For an `open` row: the proposed
  approach. For `done-unverified`: what's already done and specifically what verification step
  remains (device test, macOS build, Sentry re-check, etc.) — name the step, don't just say
  "unverified." For `done-verified`/`withdrawn`: one line confirming what happened and how it
  was proven.

Below the three fields, one line of provenance: `<ID> · <Target> · <@status token> · last
touched <date if known>`. This is the ONLY place the raw token appears in `show`'s default
output — the three fields above are prose, not a re-print of table cells.

### How the synthesis is derived (mechanical, not model-generated)

**Deterministic extraction, not an LLM call per row.** A summary generated fresh by the model
at display time would be more fluent, but non-deterministic between runs and too expensive to
default to when `list --view=next` or a future batch flow might want this per row across many
rows at once. Instead:

- **Finding and Impact** come from the row's own table cells (Finding, Risk:No-Fix) — these are
  already supposed to be current-state, single-sentence fields per the row-length discipline
  rule; `show` is mostly reformatting them into prose, not inventing new text.
- **Fix** is derived from the LAST dated entry in the Detail block's history (§2b: "a status
  CHANGE appends a dated line to the detail block; the table cell's one-line status is REPLACED
  to the latest" — so the most recent dated line IS the current fix-state by construction, not
  a guess). If the Detail block has no dated history yet (a freshly logged row), fall back to
  the row's Finding cell's own stated fix, if any.
- **This is why §2b (history is appended to the block, REPLACED in the cell) matters more than
  it looks:** `show`'s reliability depends on "most recent dated entry = current truth" holding.
  A ledger that violates §2b (appends new arcs without dating them, or buries the current state
  mid-block instead of at the end) will make `show` synthesize a stale or wrong Fix. This is a
  reason to enforce §2b more than it is a reason to complicate `show`'s extraction logic.
- **No caching, no write-back.** `show` recomputes from the current file on every call. A
  cached summary is one more artifact that can drift from the history under it — precisely the
  staleness problem this feature exists to fix. The recomputation is cheap (regex/string
  extraction, not a model call), so there's no performance reason to cache.

### `--full`: the escape hatch

`--full` prints the synthesis card, then a `---`, then the row's complete raw Detail-block
content verbatim — unabridged, in original order, nothing summarized or dropped. This is not a
fallback for when the synthesis is wrong; it's how a reader gets the FULL history when they
genuinely need it (auditing a reversal, understanding why an earlier fix didn't hold, writing a
postmortem). **Nothing is ever deleted or hidden from the file** — `show`'s default view is a
different lens on the same content, not a smaller copy of it. This is the same non-negotiable
as the row-length split's hard rule ("the budget MOVES history to the detail block; it NEVER
deletes it") applied one level up: showing less by default never means keeping less on disk.

### Failure modes

- **Row not found:** exact error naming the ID and the file searched, no guessing at a close match silently.
- **Row has no Detail block at all** (either never split, or the pointer is broken — this is
  exactly what `reference/verify.md`'s `detail-pointer` check flags; `show`'s job here is to
  degrade gracefully at read time, not to run that check itself): synthesize Finding/Impact from
  the table cells alone, and say so explicitly in the Fix line (`"No detail history on file —
  fix approach not recorded."`) rather than inventing one.
- **Multiple ledgers, ambiguous ID:** if `--ledgers=`/`--all-ledgers` scope is active (see
  § Multi-ledger scope under `/unforget list`) and the ID exists in more than one registered
  ledger, `show` asks which one rather than picking silently.

### Algorithm fallback (Python unavailable)

Locate the row by ID in the ledger's table (same lookup `edit`/`list` already do). Extract:

- **Finding** — the row's Finding cell, minus any `**bold title**` markup, minus any
  `→ see detail block **<ID>**` pointer text, rewritten as a plain current-tense sentence (drop
  parenthetical asides and file:line citations — those belong in the Detail block, not the
  synthesis).
- **Impact** — the row's Risk:No-Fix cell, rewritten as prose the same way.
- **Fix** — find the `### Detail - <section>` block matching this row's section, then the
  `- **<ID>** -` bullet within it. If the bullet contains a `**Status history:**` sub-line (the
  v2-format dated-history convention), take the LAST dated or most-recently-appended clause in
  it — per § How the synthesis is derived above, the row-length discipline's §2b rule (history
  is appended, the cell is replaced to latest) means the last entry IS the current state, not
  merely the most recent claim. If the bullet has no dated sub-line, take the bullet's own last
  sentence. If no bullet exists for this ID at all, fall back to any fix-shaped clause already
  present in the Finding cell, and if none, say plainly that no fix approach is on record — do
  not synthesize one.
- Render the three as short prose paragraphs, then the one-line provenance
  (`<ID> · <Target> · <@status token> · <date if the Detail bullet carries one>`).
- **`--full`:** after the synthesis, print a `---` divider, then the row's Detail-block bullet
  verbatim, unedited, in full.

This is table-and-string manipulation only — no ranking, no cross-row logic — so the fallback
is a close mirror of the preferred implementation, not a simplified approximation of it.

### Interactive presentation (optional, environment-gated)

**Markdown is the baseline and the fallback everywhere.** The three-field card above renders
as plain markdown — headings, prose, nothing else — because `unforget` is explicitly meant to
work in "any editor, on GitHub, in Linear" and for "other AI assistants" beyond Claude Code
(`reference/../SKILL.md` § Compatibility notes). A feature that only worked in one rendering
environment would contradict that portability goal, so nothing above this line depends on any
capability beyond writing text to stdout.

**Where a richer interactive surface is available, `show` MAY offer it instead — never as a
silent substitution, always as an explicit choice.** Concretely, in an environment that
supports rendering an interactive HTML/widget view (for example, Claude's `Artifact` or
`show_widget` surfaces), `show <ID>` with no other flags still prints the markdown card by
default, and additionally offers: `"Render this as an interactive card? (click-through to full
history, no scrolling)"`. Only on explicit accept does it build a small self-contained view:

- **List-then-detail, not a permanent dashboard.** The pattern that worked when this was
  demoed: a compact one-line-per-row list (ID badge + finding, no rating columns — those stay
  in the terminal table, this is a reading surface for ONE row at a time) that expands into the
  same three fields (Finding / Impact / Fix) on selection, with a `--full`-equivalent link/toggle
  back to the raw Detail block for that row only.
- **Never the table's replacement.** The interactive view has NO rating columns (Urgency, ROI,
  Risk, Effort) and is not meant to answer "what should I work on next" — that comparison task
  stays in `list`'s table, full stop (see the earlier discussion: comparison and single-row
  reading are different tasks, not competing views of the same data).
- **Generated fresh per call, matching the markdown baseline's no-cache rule.** The interactive
  view is built from the same deterministic extraction `show` already does — it is a different
  renderer for the same computed fields, not a separate feature with its own logic or its own
  drift risk.
- **Degrades to nothing, never to broken.** In any environment without this capability, `show`
  behaves exactly as the baseline section above describes and never mentions the interactive
  option — no dead flag, no "not supported here" error. The offer only appears where it can
  actually be fulfilled.
- **A future `/unforget list --interactive` (or similar) extending this to the multi-row list
  itself is a natural next step but explicitly NOT specified here** — this section covers
  single-row `show` only, since that's the concrete case that was designed and demoed. Widening
  it to `list` would need its own pass at how rating-column comparison and card-based reading
  coexist in one view, which is a real design question, not just "reuse the same renderer."
