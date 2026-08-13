---
name: unforget
version: 2.5.0
description: |
  A single source of truth for deferred work: paused plans, mid-task spillover,
  audit findings, and observed bugs. Kept in one UNFORGET.md per project so
  nothing slips between releases. Activate when the user asks "what's deferred?",
  "what's the backlog?", "prioritize my plans," "show me what's blocking release,"
  or wants to log something for later without losing it.
license: Apache-2.0
---

# unforget

> Installed as a Claude Code plugin (current version: v1.0; plugin install available since v0.2). Manual install via `~/.claude/skills/unforget/` (invoked as `/skill unforget`) still works as a v0.1 fallback.

> A way of not losing sight or track of what is deferred.

## Why this skill exists

Every developer defers things. The problem isn't the deferral. The problem is that deferred items end up scattered across:

- a `Deferred.md` at the repo root
- date-prefixed plan files in some "deferred" folder
- audit-tool ledgers (radar-suite, ESLint TODO comments, etc.)
- Slack DMs to yourself
- comments in code (`// TODO: come back to this`)
- memory files for AI assistants
- paused plan files in `~/.claude/plans/`

When the user asks "what's deferred?" months later, the answer requires walking every one of those surfaces. Items go stale. Some get fixed by accident. Some sit forever because nobody remembered them.

`unforget` collapses all deferral into ONE file (`UNFORGET.md`) with a structured format that:

1. **Forces the deferral question** ("when does this ship?") via the Target column.
2. **Surfaces staleness** via a built-in scan command that flags items past their age threshold.
3. **Standardizes the format** so any developer reading any project's UNFORGET.md instantly recognizes the structure.

The pattern was extracted from a real Universal app (iOS, iPadOS, macOS) where deferred work had fragmented across five tracking surfaces. Consolidation freed roughly 3 hours of release-prep time per cycle.

---

## Format at-a-glance

UNFORGET.md is a single markdown file with **4 sections**, each containing a rating table whose width depends on the preset (10 columns for Standard, 9 for Compact / Continuous, 6 for Lean).

**Sections:** 1. Paused plans (P) · 2. Session spillover (S) · 3. Audit findings (A) · 4. User-reported / observed (U)

**Columns (Standard preset):** `# | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status`

**Target values:** 🔴 THIS (blocks current release) · 🔵 NEXT (next post-release update) · 🟡 LATER (two cycles out) · ⚪ SOMEDAY (no commitment)

**Invariant:** `🔴 THIS` is the only Target that blocks shipping. At submission time, every `🔴 THIS` row must be Status = Fixed or have been demoted with a one-line reason.

**Full format spec lives in `reference/format.md`:** column meanings, Status enum, detail-block format (closure pointer → body → verify-still-open recipe → spawn links), Standard / Compact / Lean / Continuous presets, and anti-patterns. Read that file when writing or validating a row.

**Open rows whose details cite specific file paths SHOULD carry a `**Verify-still-open:**` one-line recipe in the detail block** — a 10-second grep that confirms the row's premise still matches the current source. Rows decay independently of fixes (refactors move lines, parallel sessions ship silent fixes); the recipe makes that grep a structural checkpoint, not a habit. See `reference/format.md` § Verify-still-open recipe for the three-layer cascade.

---

## Subcommand surface

| Subcommand | One-line purpose | Full spec |
|---|---|---|
| `/unforget init` | Bootstrap UNFORGET.md and survey existing deferral artifacts across the project | `reference/init.md` (with surface detail in `reference/surfaces.md`) |
| `/unforget add` | Capture a new deferral (defaults to Section 2 / Session spillover); 30s end-to-end | `reference/commands.md` |
| `/unforget edit` | Refine a row's columns; closure recommendations on `--status=Fixed` | `reference/commands.md` |
| `/unforget import` | Re-run the surface survey after init (catches NEW artifacts) | `reference/commands.md` (surface detail in `reference/surfaces.md`) |
| `/unforget list` | Show current state, filterable by section / Target / Urgency / age / staleness; `--view=` (all/open/done/split/next) picks which rows, `--group-by=` (target/section/none) picks the grouping, `--ledgers=`/`--all-ledgers` unions registered sibling ledgers | `reference/commands.md` |
| `/unforget show` | Synthesized current-state read for ONE row (Finding/Impact/Fix, no history); `--full` appends the raw Detail block; markdown baseline, optional interactive card view where available | `reference/commands.md` |
| `/unforget scan` | Identify rows past their staleness threshold; read-only | `reference/commands.md` |
| `/unforget branch` | (format v2+) Atomically create a child ledger (header + parent pointer + registry entry, all-or-none) when work differs on the actor / lifespan / domain axis | `reference/branching.md` (summary in `reference/commands.md`) |
| `/unforget verify` | (format v2+) Integrity lint: contradictions, unproven "done", bloat, stale recipes, registry drift; read-only; gates `archive`/`promote` | `reference/verify.md` |
| `/unforget archive` | Move completed (Done/Fixed) rows out of the active tables into an archive file; lightweight, run anytime; holds back "Done-but-owed" rows | `reference/commands.md` |
| `/unforget promote` | Release-time ritual: verify 🔴 THIS rows fixed, promote 🔵 NEXT to 🔴 THIS | `reference/promotion.md` (with backups in same file) |
| `/unforget --version` | Print version, install path, supported format-version; install-verification | `reference/commands.md` |

**Decision flowchart: which subcommand do I run?**

- **No UNFORGET.md exists in the project yet** → `/unforget init`
- **You want to capture one new item, fast** → `/unforget add "<finding>"`
- **You want to update an existing row's columns** → `/unforget edit <ID>`
- **A new audit / plan / memory file appeared since init** → `/unforget import`
- **The user just asked "what's deferred?"** → `/unforget list` (or `/unforget list --target=THIS` for ship-blockers only)
- **You've picked one row to actually work on and want its current state, not its whole history** → `/unforget show <ID>` (add `--full` for the complete raw history)
- **You want to find rows that have aged past their thresholds** → `/unforget scan`
- **Deferred work differs on actor (a different *human* acts on it) / lifespan (a sprint with its own discipline) / domain (a different repo or subject)** → `/unforget branch` (but default to a row or section — see `reference/branching.md`)
- **Completed rows have piled up and you want them out of the active view** → `/unforget archive` (lightweight; use this between releases instead of `promote`)
- **You're about to ship a release** → `/unforget promote`
- **You want to verify the install loaded correctly** → `/unforget --version`
- **A row is being closed (`/unforget edit <ID> --status=Fixed`) and you want the post-fix sweep** → see `reference/promotion.md` § post-fix-sweep

---

## Companion files

This SKILL.md is intentionally thin. The full spec is split across `reference/*.md` files loaded on demand:

| File | What's in it | Loaded when |
|---|---|---|
| `reference/format.md` | Column definitions, Status / Target enums, detail-block format, presets, anti-patterns | Writing or validating a row |
| `reference/init.md` | Phases 1–7 of the init walkthrough, success criteria | Running `/unforget init` |
| `reference/surfaces.md` | Six core surfaces, Surface 1b general doc scanning, redirect-pointer pre-check, memory-dir resolution, path encoding, meta-file pre-check, audit-tool format-aware parsing, cross-surface dedup, GitHub-issues four states, algorithm fallback | Running `init` or `import`, or auditing surface behavior |
| `reference/promotion.md` | Promote ritual, dry-run mechanics, post-fix-sweep workflow, backups and recovery | Running `/unforget promote` or marking a row Fixed |
| `reference/commands.md` | Per-subcommand specs for `add`, `edit`, `import`, `list`, `show`, `scan`, `archive`, `--version` (incl. `--version`'s install-integrity + recall-trigger checks) | Running any of those subcommands |
| `reference/status.md` | (format v2+) `@status` / `@verified` tokens: the status enum, the `done-verified`-requires-device/user rule, the token↔narration contradiction rule, archive invariant, provenance | Reading/writing a row's status; running `archive`/`list`/`edit` |
| `reference/registry.md` | (format v2+) the registry: schema (global config + per-ledger), README-canonical rule (README wins over the `.unforget.json` cache), where it lives | Resolving where ledgers live / reading persisted posture & policies |
| `reference/verify.md` | (format v2+) the `verify`/doctor integrity lint: the checks, read-only rule, archive/promote gating, enforceable verify-still-open recipe | Running `/unforget verify`; before `archive`/`promote` |
| `reference/deferral-gate.md` | (format v2+) the deferral gate at `add`: the trivial tripwire, the "why not now?" allow-list, and the session defer/fix accounting that backs it | Running `/unforget add`; showing the session readout on `list` |
| `reference/branching.md` | (format v2+) the branching model: the three axes (actor / lifespan / domain), the decision cascade, parent/child conventions, and the atomic `branch` command | Deciding whether work earns a child ledger; running `/unforget branch` |
| `reference/skill-handoffs.md` | (format v2+) companion skill handoffs: the 5 functions, the global manifest, install-state detection by invocable name, frequency governance, the shipped-default disclosure | Firing a companion recommendation at a done/promote/verify transition |
| `scripts/*.py` | Deterministic helpers (surface scan, fuzzy dedup, path encoding, format-version check, backup prune, status-token parse, registry read/write, integrity verify, deferral gate + tally, atomic branch creation, recall-block writer, import drift detector, row-length check + lossless split, companion manifest + resolver). JSON in / JSON out. Standard library only. See `scripts/README.md`. | Whenever the corresponding reference file delegates to a script |

**Spec-substitution principle.** This SKILL.md is the index, not the spec. When implementing or modifying any subcommand, `Read` the linked reference file before acting. The reference files are authoritative.

---

## How to use unforget alongside CLAUDE.md / AGENTS.md

The skill works best when the project's main AI instructions file has a section that points at UNFORGET.md as the canonical deferral source. `/unforget init` offers to add this for you. Example block:

```markdown
## Deferred Work Index

**Single source of truth:** `Documentation/Development/Deferred/UNFORGET.md`

Read this file when:
- The user asks "what's deferred?", "what's the backlog?", "prioritize my plans," or any variant.
- Before suggesting a release / submission, to check 🔴 THIS rows for unresolved blockers.
- When a task in the current session needs to be deferred, log a row here. Do NOT create a new tracking file unless the entry needs detail beyond one row.

**Format:** 10-column rating table per section. **Sections:** Paused plans / Session spillover / Audit findings / User-reported.

**Target column** is the release-cycle commitment: 🔴 THIS / 🔵 NEXT / 🟡 LATER / ⚪ SOMEDAY.

Never log deferred items elsewhere. Memory files, plan files, and audit ledgers are detail stores; UNFORGET.md is the index.
```

This block is what makes the skill's recall trigger work. Without it, future AI sessions don't know to read UNFORGET.md when the user asks about deferred work.

---

## Compatibility notes

- **Non-Claude-Code use:** UNFORGET.md is plain markdown. The format works fine in any editor, on GitHub, in Linear, etc. The slash commands require Claude Code, but the file itself is portable.
- **Multi-user / team use:** UNFORGET.md commits to git like any other markdown. Concurrent edits use standard merge resolution. Status changes between Open / In Progress / Fixed should be done atomically per row to minimize merge churn.
- **Other AI assistants:** The "Deferred Work Index" block in CLAUDE.md / AGENTS.md works for any AI that reads project instructions. Cursor, Copilot, Aider, etc. can all benefit from the recall trigger pattern.
- **CI integration:** `/unforget scan` output is structured markdown. A simple GitHub Action can run the scan weekly and post the report to a Slack channel or open an issue. The `scripts/*.py` helpers are standalone and can be invoked from CI without Claude Code.
- **Python 3.9+:** the helper scripts under `scripts/` use Python 3.9+ standard library only (no third-party deps). When Python is unavailable, each `reference/*.md` file that delegates to a script keeps an "Algorithm fallback" paragraph the LLM can re-derive from. The fallback is functional but slower and non-deterministic; install Python 3.9+ for the canonical implementation.

### Format-version contract

Every read operation (`add`, `list`, `promote`, `scan`, `edit`, `import`, `verify`) checks for an HTML comment marker of the form `<!-- unforget-format: vN -->` near the top of UNFORGET.md. The marker declares which version of the unforget file format the file conforms to. This skill (v2.0) supports formats `v1` and `v2`. `v2` adds the `@status`/`@verified` status tokens, the registry, the `verify` lint, the deferral gate, branching, the onboarding/recall-block wiring, the row-length discipline (bounded index rows + lossless splits), and the companion-skill handoffs (function→manifest, invocable-name detection); a `v1` file has none of those and is read/written as a legacy ledger (tokens optional, never required). Three cases:

- **Marker absent.** The skill prompts: "this file may not be in unforget format; proceed anyway?" Default response is no. If the user proceeds, the skill operates as best it can without format guarantees, and recommends adding `<!-- unforget-format: v2 -->` near the top of the file to silence the prompt on future reads.
- **Marker recognized (`v1` or `v2`).** The skill proceeds normally. A `v1` file is treated as a legacy ledger: the v2-only features (status tokens, registry, `verify` errors) simply don't apply; nothing is required or auto-added until the file is upgraded to `v2`.
- **Marker is a future version (`v3` or higher).** The skill prints: "this file declares unforget format vN, but this skill version supports up to v2. Operating in read-only mode; writes are refused." Read-only operations (`list`, `scan`, `verify`, and `promote --dry-run`) still work. Write operations (`add`, `edit`, `import`, and `promote` without `--dry-run`) refuse with a one-line error pointing to the version mismatch and recommending a skill upgrade.

**Preferred implementation:** delegate the marker read to `python3 scripts/check_format_version.py <path-to-UNFORGET.md>` (returns JSON). Algorithm fallback if Python is unavailable: read the first 30 lines of the file, grep for `<!-- unforget-format: v` (case sensitive), parse the version digit, compare against supported.

---

## Anti-patterns (summary)

Things this skill deliberately does NOT do: custom column reordering · custom rating scales · per-row column visibility · renaming core columns · multiple files · auto-deferring on the user's behalf.

See `reference/format.md § Anti-patterns` for why each is banned — that file is the single source; this line is only the index.

---

## Changelog

### v2.5.0 — `/unforget show`: one-row synthesis instead of the full history dump (2026-08-13) · minor

New subcommand. Read-only, additive, no change to on-disk format or any existing command.

- **`/unforget show <ID>`** renders three fields for ONE row: Finding (current-state, not
  history), Impact (why it matters left as-is), Fix (what closes it, or the specific
  verification step still owed for a `done-unverified` row). Deterministic extraction, not a
  per-call model summary: Finding/Impact come from the row's own table cells; Fix comes from
  the LAST dated entry in the Detail block, which the row-length discipline's §2b append rule
  already guarantees is the current state (history is appended, the cell's status is REPLACED
  to latest) — `show` leans on that existing invariant rather than adding new logic to find
  "what's current." No caching; recomputed fresh every call, same anti-staleness principle as
  the char-budget and view-mode work above.
- **`--full`** prints the synthesis, then the complete raw Detail-block history verbatim below
  it — the escape hatch for when the full accreted narrative (a reversal, a postmortem) is
  actually wanted. Nothing is ever hidden from the file, only from the DEFAULT view; same
  non-negotiable as the row-length split's "moves history, never deletes it" rule, applied one
  level up.
- **Markdown is the baseline everywhere**, per this skill's own stated portability goal ("works
  fine in any editor, on GitHub, in Linear... other AI assistants" — § Compatibility notes).
  Nothing about the default `show` output depends on any rendering capability beyond stdout.
  **Carries its own Algorithm fallback** (`reference/commands.md` § `/unforget show` §
  Algorithm fallback), same as every other non-trivial command in this file — table/string
  extraction only, no ranking or cross-row logic, so the fallback is a close mirror of the
  preferred path rather than a simplified approximation.
- **Interactive card presentation is optional and environment-gated, never a silent swap.**
  Where a richer surface exists (e.g. Claude's Artifact/widget rendering), `show` may OFFER a
  click-through card view of the same three fields — explicitly opt-in, generated from the same
  deterministic extraction (no separate logic, no separate drift risk), and it degrades to
  nothing (not to an error) anywhere that capability is absent.
- **Deliberately does not touch `list`'s rating table.** Comparing rows (Urgency/ROI/Risk
  across many) and reading one row deeply are different tasks — the interactive view carries no
  rating columns and is not meant to answer "what's next" (that stays `list`/`--view=next`'s
  job). Extending this pattern to a multi-row interactive `list` is a real design question
  flagged as explicitly out of scope for this version, not assumed as a natural follow-on.
- **Origin:** a live demo built from Stuffolio's own open rows, prompted by "these summaries
  take up a lot of vertical space — what if selecting a row is when a brief description
  displays, instead of the list itself." The follow-up question ("would we lose the 11-column
  table?") is what drew the comparison-vs-reading distinction this design rests on: no, because
  they were never the same job.
- Full spec: `reference/commands.md` § `/unforget show` (including § Interactive presentation).

### v2.4.0 — `list --ledgers=` / `--all-ledgers`: opt-in cross-ledger reads (2026-08-13) · minor

Additive, backward compatible: `/unforget list` with no scope flag is single-ledger, unchanged.

- **`--ledgers=<names>` / `--all-ledgers`** union rows from sibling ledgers already declared in
  the registry (`role`/`axis`/`parent`/`death` per `reference/registry.md`) — no new registry
  field, and no globbing for stray `*UNFORGET*.md` files. A name not present in the registry is
  an error, not a silent skip.
- **Default stays opt-in, by design decision, not just default caution.** The alternative
  (auto-union every discovered ledger file, narrow with a flag) was considered and rejected: it
  would make `branch`'s side effect silently change tomorrow's `list` output with no flag
  touched, and it would surface files the registry exists specifically to avoid losing track of
  or confusing with real ledgers.
- **Three safety levels, not one blanket "combine":** reading (`--view=all/open/done/split`) is
  a safe, unconditional union — output gains a Ledger column whenever more than one ledger is in
  scope. Ranking (`--view=next --all-ledgers`) is axis-aware: an `axis:actor` sibling
  (a different human's work, e.g. a project's TERRY-only ledger) or an `axis:lifespan` sibling
  (has a `death` condition — meant to disappear) is never presented as an undifferentiated top
  pick; the source ledger is always named, and an actor-scoped top result gets an explicit
  best-non-actor-scoped alternative alongside it. Writes (`archive`/`edit`/`promote`) are
  entirely out of scope for these flags — they keep operating on the one ledger they're pointed
  at, same as today.
- **Origin:** a follow-up to the `--view=`/`--group-by=` work above, prompted by "would a user
  choose or combine which ledgers to work from?" The axis-aware ranking rule specifically
  guards against the failure a blind cross-ledger `--view=next` would invite: surfacing a row
  scoped to a different actor or a dying sprint ledger as if it were a permanent, generally
  actionable "next," which would misrepresent exactly the separation `branch`'s three axes
  (`reference/branching.md` §2) were designed to preserve.
- **Algorithm fallback** for `--ledgers=`/`--all-ledgers` is covered in the SAME fallback
  paragraph as `--view=`/`--group-by=` (see v2.2.0 entry below) — one combined recipe for all
  three `list` extensions, not a separate one per flag.
- Full spec: `reference/commands.md` § Multi-ledger scope (under `/unforget list`).

### v2.3.0 — char-budget hard error + write-time budget offer at `edit` (2026-08-13) · minor

- **`char-budget` escalates to `error` past a hard threshold** (default 4x the soft budget,
  1600 chars; new `--char-budget-hard` flag). Previously `char-budget` was `warn` at every
  size, so a row could sit at any length indefinitely without ever blocking `archive`/`promote`.
  **Origin:** a real ledger (Stuffolio, 2026-08-13) carried a row at 3,707 chars — 9x the 400
  soft budget — through repeated ship cycles; its accreted "RESOLVED" / "still owed" / "prior
  arc" history (never migrated to the detail block that already existed for it) directly caused
  a session to misread the row's current status. The lossless split (`verify --fix`,
  `scripts/row_budget.py`) already existed and already worked; what was missing was a severity
  that made using it mandatory before shipping, not optional. Applies to v1 (tokenless) ledgers
  too — the failure this catches doesn't depend on `@status` tokens being present. Full spec:
  `reference/verify.md` § Char-budget severity escalation.
- **`/unforget edit` now offers the split at write time**, not just reactively at the next
  `scan`/`verify` — checked once per status-changing edit, right after the change is applied,
  only when the edit CROSSES the soft-budget threshold (not re-offered on every subsequent edit
  to a row already over budget). Advisory, same shape as the existing companion-skill handoff:
  easy to decline, never blocks the edit itself. Catches the bloat where it's actually created
  (one status change at a time) instead of only where it's later discovered. Full spec:
  `reference/commands.md` § Budget check at write time (under `/unforget edit`).

### v2.2.0 — `list --view=` / `--group-by=`: named row-selection modes, orthogonal grouping (2026-08-13) · minor

Additive, backward compatible: new opt-in flags, no change to the default `list` output or the
on-disk file format.

- **`--view=<all|open|done|split|next>`** picks which rows show. `all` is today's unchanged
  default (one table, everything). `open`/`done` are named equivalents of filtering to just the
  Open or Completed bucket — the common-case spelling for "what's left" / "what shipped."
  `split` renders both as two headed tables in one output (with counts, so the reader doesn't
  count rows by hand). `next` skips the table entirely and returns one recommended row plus a
  one-line reason, ranked by a composite of ship-risk (Target × Urgency × Risk:No-Fix),
  closest-to-done (a `done-unverified` row needing only a verification step outranks one needing
  new code, all else equal), and ROI — the dominant factor is named in the reason so the pick is
  inspectable, not a black box, and ties break toward lower Fix Effort.
- **`--group-by=<target|section|none>`** is the orthogonal axis: controls how the rows `--view`
  selected are grouped/sorted, never which rows are included. `target` (default, unchanged) is
  today's 🔴 THIS → 🔵 NEXT → 🟡 LATER → ⚪ SOMEDAY grouping. `section` groups by Paused
  Plans / Session Spillover / Audit Findings / User-Reported instead — combined with
  `--view=split` this produces one Open/Completed pair per section. `none` is a flat
  Urgency-sorted list for piping elsewhere.
- **Status classification** (all `--view` modes) is via `parse_status.py`'s existing
  `archivable` field — `open`/`in-progress`/`blocked`/**`done-unverified`** count as Open,
  `done-verified`/`withdrawn` count as Completed. **`done-unverified` staying in Open, not
  Completed, is the load-bearing rule across every mode** — code-written-but-not-proven is
  still open work by this skill's own status tiering, and `--view=next` explicitly flags when
  the top pick is a verification step rather than new code so it doesn't read as "start from
  scratch." Legacy tokenless rows use the same loose word-status mapping `--status` already
  applies; unclassifiable rows land in an **Unparsed** heading (`split` mode) rather than being
  silently dropped into either bucket.
- **Origin:** a live 61-row ledger, read start-to-finish by an agent asked for "what's open,"
  under-reported by 18 rows on the first pass, then separately misread a row's *current* status
  from its own history narration (a row that had gone open → fixed → regressed → fixed again
  read as still-open from the prose alone, even though its token was `done-verified`).
  Re-deriving "open vs. done" by eye from one merged, sorted-by-Target table is exactly the
  failure mode `@status` tokens exist to prevent (see `reference/status.md`). The two-axis
  design (rather than a single `--split` flag, the first cut of this feature) came from a
  follow-up ask: separate "which rows" from "how grouped" so open-only, done-only, combined, and
  a future grouping request don't each need their own bespoke flag.
- **Composes with existing filters** (`--target=`, `--section=`, `--stale`, `--age=`); a
  `--view=<mode>` combined with a bucket-picking `--status=<value>` is redundant, so `--status=`
  wins if both are passed.
- **Carries an Algorithm fallback** (`reference/commands.md` § `/unforget list` § Algorithm
  fallback) — every existing command spec in this file has one and these flags initially didn't;
  added so a Python-unavailable environment (or a human without this skill loaded) has a written
  recipe for `--view`/`--group-by`'s logic, not just the base filters `list` already covered.
- **Storage untouched by design.** UNFORGET.md stays one file, one table per section — see
  `reference/commands.md` § View modes for why splitting the file itself would work against this
  skill's "single source of truth" premise.
- Full spec: `reference/commands.md` § View modes and § Grouping (under `/unforget list`).

### v2.1.0 — quoted status tokens no longer hijack a row's status (2026-08-11) · minor

Bug fix, backward compatible, but a **behavior** change in the parser — hence minor, not patch.

- **`parse_status.status_cell` now scans last-cell-BACKWARD.** It scanned first-forward for
  the first cell carrying an `@status:` token, and Finding precedes Status. A row that quoted
  a token illustratively — rows documenting the format do this, and so does any row citing a
  sibling row's state — had the QUOTED token silently become its status for `list`, `archive`,
  and the release gate. Found on a live ledger 2026-08-11: an `open` row citing a closed
  sibling parsed as `done-verified` and failed the gate. Backward scanning returns the real
  Status cell in every layout the format allows, including with the optional `1-Star Risk`
  column appended (it carries no token). Regression-tested both directions.
- **New `quoted-status-token` warning (warn, not error).** The parser fix keeps the tool
  correct, but a quoted token still corrupts the `grep -c` reading that ledger docs commonly
  prescribe for humans. Fires at write time and names the offending token.
- **Contradiction messages now point at the quote.** When a row both contradicts and quotes a
  token, the bare "token says X but narration says Y" sent authors to edit their prose — the
  innocent half. It now names the quote as the likely cause.
- **`FILE_CITE_RE` no longer matches ordinary prose.** `[\w./-]+\.\w{1,5}` counted `e.g`,
  `i.e`, and decimals like `0.50` as file citations, inflating `stale-recipe` warnings and
  training users to ignore the check. Now requires a path separator or a known source/doc
  extension. Measured on a 3-ledger installation: 33 → 27 warnings on the worst file.

### v2.0.3 — contradiction false positives (2026-07-31) · patch

Bug fix only, backward compatible. The §1b contradiction check matched its phrase list
as bare substrings, which fired on ordinary prose. Three classes found in the field:

- **`"still open"` matched a VERB phrase.** "viewers can still open + view detail" — a
  sentence about a UI affordance — was read as "this row is still open," contradicting its
  own `done` token. Now distinguishes the adjective (clause-final: "the issue is still
  open") from the verb (takes an object or conjunction: "still open the sheet", "still
  open + view"). Only the adjective contradicts.
- **`"blocker"` matched its own negation.** "not a blocker" was read as "is a blocker."
  Negation-aware now (`not` / `never` / `no longer` / `isn't` / `wasn't` within two words).
- **`"unverified"` matched the row's own `@status:done-unverified` token.** The narration
  is stripped of `@status:`/`@verified:` tokens before scanning, so a token can no longer
  be read as prose about itself.

Matching is also word-bounded now, so a phrase inside a longer word no longer fires.

**Why this mattered.** A false contradiction sets `archivable` to False, so the row is held
out of `archive` indefinitely while a human is sent to reconcile a real sentence against a
conflict that never existed. On the source installation it produced a phantom 5th error over
a ledger whose true error count was 4.

8 regression cases added to `tests/test_row_visibility.py` (4 false-positive shapes, 4 real
contradictions that must still fire), verified to fail against the old matcher.

### v2.0.2 — release-gate false negative (2026-07-31) · patch

Bug fixes only, backward compatible. A first-ever `verify` run against a mature
three-ledger installation found that the row-id pattern was matching too little, and that
rows it missed were invisible to **every** check in the lint:

- **`ROW_ID_RE` accepted at most one leading letter and no suffix.** Real ids skipped in the
  field: `A48a`/`A48b` (a finding split into sub-rows), `MI-08` (a hyphen-prefixed sibling
  ledger), `**S12**` (bold-wrapped). Consequence: two 🔴 THIS ship-blockers were excluded
  from the release gate, which reported **2 blockers over a ledger holding 4** — and
  reported it as a clean number. An entire sibling ledger reported `rows_checked: 0` while
  appearing healthy. Widened to an optional 1-3 letter prefix (optional hyphen), digits,
  optional letter suffix, optional bold. Strictly wider: every previously-matching row still
  matches, bare-numeric ids still work, headers and separators still correctly do not.

- **New check 10, `cell-count`.** Flags a row whose cell count differs from its table's
  declared header width. The cause is nearly always an unescaped `|` in cell prose (a
  `grep 'a\|b'` recipe, a regex alternation), which silently shifts every positional column
  read past it — a status token can land in a rating cell. Error severity. Width is tracked
  per-table, so a 10-column section and a 5-column sprint table coexist without false
  positives.

- **Regression bench.** `tests/test_row_visibility.py` (23 assertions) covers the id grammar
  positively and negatively plus the cell-count check, builds its own fixture, and is wired
  into `tests/run.sh`. The shared fixture project exercised none of these id shapes, which is
  precisely why the bug survived to production.

### v2.0.1 — column-layout robustness (2026-07-26) · patch
Bug fixes only, no new features, backward compatible. A refreshed example that finally
exercised the format's own optional/variable columns surfaced a family of positional
table-cell reads that broke when the column layout wasn't the Standard 10:

- **Status was read by position, not content.** `parse_status.status_cell` (and its copies
  in `verify_ledger`/`row_budget`) took the *last* table cell as Status — so an appended
  `1-Star Risk` column made the risk strip get read as the status, silently breaking
  `list`/`archive`/`verify` (zero tokens found). Now the Status cell is located by the cell
  carrying the `@status` token; the three copies are consolidated into one.
- **Finding was read as a fixed index.** `finding_cell` used `cells[2]`, which is *Urgency*
  under the **Compact** preset (that preset drops the Target column). Now a single
  preset-aware locator (detects the Compact `**🔴 THIS · …**` badge) that both call sites
  delegate to. `target_is_this` hardened the same way.
- **The `verify --fix` / `row_budget split` path** (`build_index_row`) read Finding/Status
  by fixed index; now by content, so a split of a 1-Star-column row preserves the risk
  strip and bounds the real Status.
- **`branch` wrote a fixed 10-column pointer row.** Now `build_pointer_row` derives the
  column set from the parent's actual header and places content by column name, so a
  Lean/Compact/Continuous/1-Star parent gets a correctly-shaped pointer row.

All found via `/bug-echo` on the first fix; each fix reproduced before and after, with
regression guards added to the test suite (proven to fail if the fix regresses). The
refreshed `examples/UNFORGET.md` now shows format v2 (real `@status` tokens, a
`done-unverified` owed row, a lossless split) plus the optional `1-Star Risk` column.

### v2.0.0 — the format-v2 milestone (2026-07-26) · **the eight-phase design build, complete**
**A milestone, NOT a breaking change.** The major bump marks scope, not incompatibility: every v1
ledger keeps working untouched, no migration is forced, and the skill reads and writes both v1 and
v2. What earns the `2.0.0` is that this is a categorically more capable tool than v1.0 — eight
phases (shipped incrementally as v1.1.0 through v1.6.0, now tagged together as v2.0.0) added the
whole format-v2 layer: **structured `@status`/`@verified`
tokens** (a row can't contradict itself; a "done" isn't done until it's verified), a **registry**
(where every ledger lives + git posture + policies), the **`verify` integrity lint** (gates
archive/promote), the **deferral gate** (trivial tripwire + why-not-now + session accounting), the
**`branch` command** (atomic child ledgers), **onboarding wiring** (a maintained CLAUDE.md recall
block + drift reconciliation), **row-length discipline** (bounded index rows + lossless splits), and
**companion skill handoffs** (below). Backward compatible throughout; a v1 (tokenless) ledger is
never blocked by any v2 check.

The final phase, companion skill handoffs: unforget recommends OTHER skills at earned ledger
transitions — function-based, not skill+URL hardcoded through trigger points, so a companion link
rots in ONE place (the manifest), never twelve.

- **Five fixed functions** (`reference/skill-handoffs.md`): `post-fix-sibling-scan`,
  `ship-risk-scoring`, `audit-reverify`, `forward-bug-hunt`, `verify-against-reality`. Each fires
  at a specific ledger transition and names the earned reason — never a generic "you might like
  these skills" footer.
- **One global manifest** (`~/.claude/unforget-companions.md`, `scripts/companions.py`): function →
  skill → invoke → url, the ONLY place a companion URL is written. Projects inherit it. Ships a
  default mapping the author's skills, **disclosed at init** (overridable in one place; unforget
  works with no manifest at all).
- **Install-state detection by INVOCABLE NAME, never a dir find** (the one-star-risk lesson —
  `one-star-risk` is invocable but has no dir of that name). Three states: installed → run the
  command, no URL; not-installed → one soft pointer with the manifest URL; unset → say so, invent
  no URL. `verify` gains a rot check for entries neither installed nor reachable.
- **Governance:** at most once/function/session; a **trivial close fires nothing**; advisory,
  never blocking, and never a way to *defer* the scan (a handoff means do-it-now-while-context-is-hot).
- **Reconciled** the pre-existing inline `/radar-suite`+`/bug-echo` closure block (which hardcoded
  two URLs and detected installs by directory name) into this function/manifest system across
  `edit`, `promote`, `deferral-gate`, and `verify`.

With Phase 8 the **v1.1 design build is complete** — all eight phases (status tokens, registry,
verify lint, deferral gate, branching, onboarding, row-length, companion handoffs) shipped.
Backward compatible throughout: every feature degrades cleanly on a v1 ledger.

### v1.5.0 — row-length discipline (2026-07-26) · format v2
Phase 7 of the v1.1 design build: the **row-length rule** that keeps a ledger Readable. A row is a
one-line INDEX; history/context/verification narration belongs in a detail block, not fused into an
ever-growing Finding or Status cell. The 2026-07-25 failure was a ~155KB ledger with multi-KB rows
whose Reads truncated and *misled* the reader — a bounded index prevents exactly that.

- **The two-part row** (`reference/format.md` § Row-length discipline). The table row carries a
  compact index (a one-line finding summary + the `@status`/`@verified` tokens + a one-line
  status); the unbounded content lives in a `### Detail - <section>` bullet. History is **appended**
  to the block, never grown in the cell.
- **`scripts/row_budget.py`.** `check` flags Finding/Status cells over the budget (default 400,
  registry-configurable via `row_char_budget`). `split` turns an over-budget row into a bounded
  index + a detail-block bullet holding the **full original content verbatim** — and returns
  `lossless:true` only when every character is provably preserved, **refusing** otherwise. The hard
  rule: the budget MOVES history to the block, it NEVER deletes it.
- **Wired:** `scan` gains the char-budget lint; **`verify --fix`** offers the split for char-budget
  findings *only*, per row, with approval (the one integrity finding safe to auto-resolve because
  it's mechanical and lossless-verifiable). `verify` with no flags stays read-only exactly as before.

Backward compatible: the rule flags legacy over-long rows but never blocks on them; a split is
always offered, never forced, and only ever moves content — a legacy ledger keeps working untouched.

### v1.4.0 — onboarding, registry wiring, and the maintained recall block (2026-07-26) · format v2
Phase 6 of the v1.1 design build: `init`/`import` now write and reconcile the two persisted
surfaces the whole system depends on — the **registry** and the **maintained recall block** — so
nothing the skill relies on lives only in memory (the through-line of the onboarding design). This
is the fix for the 2026-07-25 split-brain (ledgers stranded in a parallel tree) and stale-pointer
(a CLAUDE.md index that described an old layout) failures.

- **Onboarding questions** (`reference/init.md`). `init` adds the **git-posture** question (split /
  committed / ignored — split recommended, and the skill writes the `.gitignore` rules itself,
  incl. ignoring the ephemeral `.unforget-session.json` and `.unforget.json` cache), and upgrades
  the recall question to **maintained / manual / none**. It writes the registry + the two policy
  defaults (Policy 1 deferral, Policy 2 multi-axis) at the end.
- **The maintained recall block** (`reference/init.md`, `scripts/recall_block.py`). A
  marker-delimited Deferred Work Index in CLAUDE.md/AGENTS.md, rebuilt from the registry by
  init/import/branch so it can't rot — rewriting only between its markers, never the user's
  content. `branch` now updates it as a **fourth atomic artifact** (rolls back with the other three
  on any write failure).
- **`import` drift detection** (`scripts/import_drift.py`). Reconciles the registry against reality
  — **registered-but-missing** (error), **found-but-unregistered** (the stranded-parallel-tree
  check), **posture-mismatch**, and **stale-recall**. Read-only; reports, you fix.
- **Migration for already-messy projects** (`reference/init.md` § Phase 6b, `reference/surfaces.md`
  § non-standard locations). `init` ASKS for out-of-repo ledger locations (rather than a disk-wide
  scan), proposes consolidation, and **verifies byte-identical before removing any original** — the
  one-way-door discipline for not losing a ledger during a move.

Backward compatible: all of it is v2; a v1 ledger keeps working, and a project with no registry
just gets the pre-v2 behavior (branch stays reachable via the parent pointer, no recall
maintenance).

### v1.3.0 — branching + the `branch` command (2026-07-26) · format v2
Phase 5 of the v1.1 design build: the **branching model** and an atomic `/unforget branch`
command. The default is still NOT to branch — most deferred work is a row or a section. A new
ledger is justified only when work differs from the parent on one of three axes.

- **The three axes** (`reference/branching.md` §2): **actor** (a different *human* acts on it —
  earns a file even at identical discipline, that's what a `TERRY-UNFORGET` is; a machine/
  automation actor does NOT — that's a Target value or tag), **lifespan** (a sprint — earns a
  ledger only when paired with a *different discipline* like a cap/eviction, not a plain
  time-box), and **domain** (a different repo/subject). Plus the decision cascade (§3) and the two
  placement policies (§2.5).
- **The atomic `branch` command** (§8, `scripts/branch_create.py`). Creating a child does three
  things **together, or none** — scaffold the child header (axis, discipline, parent back-pointer,
  death condition if lifespan), write the parent's single pointer row (never a copy of child
  rows), and register the child. A failure on any one rolls the others back — no half-branched
  state. That structural atomicity makes the 2026-07-25 split-brain (a child the parent/registry
  lost track of) impossible. Guards refuse rather than half-create: a duplicate name, a lifespan
  child with no death condition, or an unconfirmed non-human actor.
- **Auto-suggest on a repeated pattern** (§6). `add`/`import` *offer* a branch — never branch
  unilaterally — only when the cascade lands on "new ledger" for ≥2 related items, naming the
  pattern seen. One item never triggers it. This is how an emerging track gets noticed instead of
  silently accumulating.

Backward compatible: `branch` writes v2 children and reads the registry; on a project with no
registry, register the parent first. The recall block still points at the canonical index; a
child is reachable via the parent's pointer row (the marker-delimited recall-block writer that
would add a per-child pointer line is Phase 6).

### v1.2.0 — deferral gate (2026-07-26) · format v2
Phase 4 of the v1.1 design build: the **deferral gate**, which fires at `/unforget add` — the
moment work is about to become a deferred row. It targets *deferral-laundering*: a row looks
identical whether it was deferred for a good reason or because deferring was frictionless and
self-flattering. The gate makes deferral cost something and leave an auditable record.

- **Trivial tripwire** (`reference/deferral-gate.md` §2). A would-be row that is Fix Effort =
  Trivial AND Blast Radius = ⚪ 1 file is redirected to **do it now** — scope doesn't gate it
  (out-of-scope trivial → do it and log a one-line report). A trivial-but-**destructive** change
  (deletion, force-push, prod deploy) is the exception: it routes to needs-approval, never
  auto-done. Trivial ≠ safe.
- **"Why not now?" allow-list** (§3). Everything that clears the tripwire must name one of four
  deferral reasons — `user-decision`, `scaffolding`, `scope`, `external-block` — recorded in the
  row as `Deferred because: <tag>` so a later reader (or `scan`/`verify`) can check whether it
  held up. No valid reason → do-now is the default, not a row.
- **Session defer/fix accounting** (§4, the load-bearing backstop). A per-session tally surfaces on
  `list` and at session end — `2 fixed inline · 7 deferred (reasons: …)`. A defer-heavy ratio
  (default ≥ 3× fixed) raises a gentle, **advisory-never-blocking** flag. The linguistic gate can
  be gamed per row; a ratio can't — this half is why the gate is honest, not decorative.
- **`scan` trivial-staleness cross-check** (§4d). A Trivial row that has survived ≥N sessions
  un-done is flagged as a near-certain "should've just done it" — how the pattern is learned over
  time, not just caught in the moment.
- New `scripts/defer_tally.py` (tripwire routing + tally math; writes the ephemeral, git-ignored
  `.unforget-session.json`) and `reference/deferral-gate.md`. Thresholds (`ratio_flag_threshold`,
  `stale_trivial_sessions`) and strictness (`policy_deferral`, default `aggressive`) are read from
  the registry. Backward compatible: the gate helps on a v1 ledger and never blocks the write path.

### v1.1.0 — status tokens, registry, verify lint (2026-07-26) · format v2
The first implemented slice of the v1.1 design (Phases 1–3 of the build plan). Introduces
**format `v2`** (the skill reads/writes both v1 and v2; v1 ledgers keep working untouched).
Every feature traces to a real failure seen while running the skill on a large, long-lived
ledger — not a hypothetical.

- **Structured status tokens** (`reference/status.md`, `scripts/parse_status.py`). A row's status
  is now a machine-readable `@status:` token (`open` / `in-progress` / `done-verified` /
  `done-unverified` / `blocked` / `withdrawn`) that tools read instead of parsing prose — so a row
  can no longer contradict itself. `done-unverified` is a first-class "done-but-owed" state.
- **Verification tier** (`@verified:` = `code` / `device` / `user` / `session-claimed`).
  `done-verified` requires `device` or `user` (or `code` with a note); **`session-claimed` can
  never back `done-verified`** — a claim is not a verification.
- **Registry** (`reference/registry.md`, `scripts/registry.py`). A re-read source of truth for
  where ledgers live and the persisted git-posture / policy settings, in a marker-delimited block
  in the ledger `README.md` (canonical) with an optional `.unforget.json` cache. If the two
  disagree, the README wins.
- **`verify` / doctor lint** (`reference/verify.md`, `scripts/verify_ledger.py`). A new read-only
  subcommand that catches contradictions, unproven/`session-claimed` "done", unknown status
  values, cell bloat, stale verify-still-open recipes, and registry drift. It **gates
  `archive`/`promote`**: an error-severity finding blocks a ship or relocation decision.

**Archive & release invariants:** `archive` now moves only a *clean* `done-verified` (valid tier,
no contradiction) or `withdrawn`, and holds `done-unverified`. A 🔴 THIS row counts as a release
blocker unless it is cleanly `done-verified` or `withdrawn`.

**Backward compatibility:** a v1 (tokenless) ledger produces no errors — the v2-only features
simply don't apply until the file is upgraded to v2. No big-bang reformat; rows gain tokens as
they're touched.

### The v1.1 design build is complete
All eight phases have shipped: status tokens (P1), registry (P2), verify lint (P3), deferral gate
(P4), branching (P5), onboarding/recall wiring (P6), row-length discipline (P7), and companion
skill handoffs (P8). The five `DESIGN-*.md` documents that specified this build are now fully
implemented. Future work is v1.2+ (see the deferred list in earlier design notes).

### v1.0.4 — docs (2026-07-26)
Documentation only, no behavior change: recorded the v1.1 design pass as a changelog entry and a
forward-looking README section. Patch bump so existing installs picked up the updated docs.

### v1.0.3 and earlier
Shipping skill: init / add / edit / import / list / scan / archive / promote / `--version`, the
10-column rating format, the format-version contract, and the `scripts/*.py` deterministic
helpers. This is the implemented baseline the v1.1 design builds on.

---

## License

Apache License 2.0. See LICENSE.
