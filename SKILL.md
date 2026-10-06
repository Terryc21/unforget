---
name: unforget
metadata:
  version: "2.10.0"
description: |
  A single source of truth for deferred work: paused plans, mid-task spillover,
  audit findings, and observed bugs. Kept in one UNFORGET.md per project so
  nothing slips between releases. Activate when the user asks "what's deferred?",
  "what's the backlog?", "prioritize my plans," "show me what's blocking release,"
  "what are my quick wins?", "show me the ten most urgent things," "only trivial fixes,"
  wants a scoped HTML ledger report, or wants to log something for later without losing it.
license: Apache-2.0
---

# unforget

> One shared skill for Codex and Claude Code. In Codex use `$unforget`; in Claude Code use `/unforget` (or `/unforget:unforget` for the plugin), followed by a subcommand.

**Read `reference/runtime.md` when first using this skill in a session.** It maps the examples below to the current host's tools, project instructions and companion settings. `/unforget` in references is workflow shorthand; all subcommands also work as `$unforget <subcommand>` requests in Codex.

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
| `/unforget list` | Show current state, filterable by section / Target / Urgency / age / staleness; `--view=` (all/open/done/split/next) picks which rows, `--group-by=` (target/section/none) picks the grouping, `--ledgers=`/`--all-ledgers` unions registered sibling ledgers, `--fresh` re-runs the display-preference interview | `reference/commands.md` |
| `/unforget report` / `list --html` | Create a standalone HTML table with default unfinished scope or user-selected ledgers, filters, columns and ranking, then open it in the user's browser | `reference/html-report.md` |
| `/unforget show` | Synthesized current-state read for ONE row (Finding/Impact/Fix, no history); `--full` appends the raw Detail block; markdown baseline, optional interactive card view where available | `reference/commands.md` |
| `/unforget scan` | Identify rows past their staleness threshold; read-only | `reference/commands.md` |
| `/unforget branch` | (format v2+) Atomically create a child ledger (header + parent pointer + registry entry, all-or-none) when work differs on the actor / lifespan / domain axis | `reference/branching.md` (summary in `reference/commands.md`) |
| `/unforget verify` | (format v2+) Integrity lint: contradictions, unproven "done", bloat, dangling detail-block pointers, stale recipes, registry drift; read-only; gates `archive`/`promote` | `reference/verify.md` |
| `/unforget archive` | Move completed (Done/Fixed) rows out of the active tables into an archive file; lightweight, run anytime; holds back "Done-but-owed" rows | `reference/commands.md` |
| `/unforget promote` | Release-time ritual: verify 🔴 THIS rows fixed, promote 🔵 NEXT to 🔴 THIS | `reference/promotion.md` (with backups in same file) |
| `/unforget --version` | Print version, install path, supported format-version; install-verification | `reference/commands.md` |

**Decision flowchart: which subcommand do I run?**

- **No UNFORGET.md exists in the project yet** → `/unforget init`
- **You want to capture one new item, fast** → `/unforget add "<finding>"`
- **You want to update an existing row's columns** → `/unforget edit <ID>`
- **A new audit / plan / memory file appeared since init** → `/unforget import`
- **The user wants an HTML ledger table or custom ranked report** → `/unforget report` (read `reference/html-report.md`; default unfinished, current ledger, blockers → urgency → user impact; open the finished page in the user's browser unless they said not to, step 8).
- **The user wants a cut of the ledger** ("top ten most urgent", "quick wins", "only trivial fixes") → `/unforget report` with `--limit`, `--effort`, `--roi` and `--sort` (read `reference/html-report.md`); state the "Showing N of M" line and any unclassified-row count the report prints, then open the page in the user's browser unless they said not to (`reference/html-report.md` step 8).
- **The user just asked "what's deferred?"** → `/unforget list` (or `/unforget list --target=THIS` for ship-blockers only)
- **You've picked one row to actually work on and want its current state, not its whole history** → `/unforget show <ID>` (add `--full` for the complete raw history)
- **You want to find rows that have aged past their thresholds** → `/unforget scan`
- **The user wants to change how `list`/`scan` display by default, or says "run fresh" / "ask me what I want to see"** → `/unforget list --fresh` (depth-gated interview, saved per-project; see `reference/commands.md` § Display-preference interview)
- **Deferred work differs on actor (a different *human* acts on it) / lifespan (a sprint with its own discipline) / domain (a different repo or subject)** → `/unforget branch` (but default to a row or section — see `reference/branching.md`)
- **Completed rows have piled up and you want them out of the active view** → `/unforget archive` (lightweight; use this between releases instead of `promote`)
- **You're about to ship a release** → `/unforget promote`
- **You want to verify the install loaded correctly** → `/unforget --version`
- **You just reported a fix for something that has a ledger row** → update that row in the same turn, with the honest status and its proof (`done-verified` with a `Code-is-sufficient:` reason drawn from this session's evidence, or `done-unverified` naming the owed check), and end the report with the row's new state (`reference/status.md` § Close on report). Say "verified" only when the row says so.
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
| `reference/html-report.md` | HTML defaults, user choices, scope/provenance, generator and verification | Creating an HTML report or `list --html` |
| `reference/status.md` | (format v2+) `@status` / `@verified` tokens: the status enum, the `done-verified`-requires-device/user rule, the token↔narration contradiction rule, archive invariant, provenance, and close-on-report (update the row in the same turn a fix is reported) | Reading/writing a row's status; running `archive`/`list`/`edit`; reporting a fix |
| `reference/registry.md` | (format v2+) the registry: schema (global config + per-ledger), README-canonical rule (README wins over the `.unforget.json` cache), where it lives | Resolving where ledgers live / reading persisted posture & policies |
| `reference/verify.md` | (format v2+) the `verify`/doctor integrity lint: the checks, read-only rule, archive/promote gating, enforceable verify-still-open recipe | Running `/unforget verify`; before `archive`/`promote` |
| `reference/deferral-gate.md` | (format v2+) the deferral gate at `add`: the trivial tripwire, the "why not now?" allow-list, and the session defer/fix accounting that backs it | Running `/unforget add`; showing the session readout on `list` |
| `reference/branching.md` | (format v2+) the branching model: the three axes (actor / lifespan / domain), the decision cascade, parent/child conventions, and the atomic `branch` command | Deciding whether work earns a child ledger; running `/unforget branch` |
| `reference/skill-handoffs.md` | (format v2+) companion skill handoffs: the 5 functions, the global manifest, install-state detection by invocable name, frequency governance, the shipped-default disclosure | Firing a companion recommendation at a done/promote/verify transition |
| `scripts/*.py` | Deterministic helpers (surface scan, fuzzy dedup, path encoding, format-version check, backup prune, status-token parse, registry read/write, integrity verify, deferral gate + tally, atomic branch creation, recall-block writer, import drift detector, row-length check + lossless split, companion manifest + resolver, display-preference resolver). JSON in / JSON out. Standard library only. See `scripts/README.md`. | Whenever the corresponding reference file delegates to a script |

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

- **Codex and Claude Code:** both load this same skill and run the same Python helpers. See `reference/runtime.md` for host conventions. UNFORGET.md remains plain markdown that other editors and assistants can read.
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

## 🛑 Asking the user anything: the governing rule

**Ask about the OUTCOME in the user's words. Never about the mechanism in the skill's words.**

This governs **every** question this skill puts to a user — the `--fresh` display interview, `init`'s onboarding questions, a `branch` confirmation, an `edit` prompt, and any question added later. It is not a `--fresh` rule that happens to generalize; it is a skill-wide rule that `--fresh` happened to expose.

The reference files below are written for the **implementer**, so they name config keys (`display_view`, `git_posture`, `archive_nudge_threshold`) and flag values (`all`/`open`/`split`, `maintained`/`manual`/`none`). **Those names are specification, not prompt copy.** Translate every one before it reaches a user.

1. **Name what the user GETS, not what gets configured.** "Only unfinished work, everything, or one 'do this next' pick" — never "a view preset." A user should never have to model this skill's internals to answer this skill's own question. If an option can only be understood by someone who has read the reference file, it is not written yet.
2. **Ask about the result, not the effort.** *"What do you want the table to display?"* — never *"How much do you want to set?"* An effort-framed question makes the user budget time before knowing what they'd get, and forces every option to re-explain the subject from scratch.
3. **No interview bookkeeping in the prompt.** No question counts in labels or descriptions. A count answers "how long is this," competing with "what am I choosing" at the moment of decision.

**Origin (2026-08-13).** A live `--fresh` run rendered `reference/commands.md`'s key names straight into the prompt; the user's report was that it gave "not much context as to how to answer." The repair took three passes — key names → outcomes, then effort-framing → outcome-framing, then removing question counts the *second* pass had added — because each pass fixed only what was pointed at, with no stated principle to apply. This rule is here, in the index every session reads, so the next question is written right the first time rather than corrected after a user hits it.

**Where the rule is applied today (v2.8.0):** `reference/commands.md § Display-preference interview` (all seven `--fresh` questions) and `reference/init.md` (git posture, cadence, recall — the three of its five that named mechanism; the file-path question was already outcome-framed and was deliberately left alone). Both files carry an `**Ask as:**` line per question giving the wording that reaches the user.

⚠️ **`init` deserves the most care of any interview in this skill** — it is the only one where every respondent is new by definition. A confused user in `--fresh` already has a ledger and can decline; a confused user in `init` never gets one. Apply this rule hardest there.

See `reference/commands.md § The governing rule for EVERY question in this interview` for the long form and worked examples.

---

## Anti-patterns (summary)

Things this skill deliberately does NOT do: custom column reordering · custom rating scales · per-row column visibility · renaming core columns · multiple files · auto-deferring on the user's behalf.

See `reference/format.md § Anti-patterns` for why each is banned — that file is the single source; this line is only the index.

---

## Release history

See [CHANGELOG.md](CHANGELOG.md) for current and historical release notes.

---

## License

Apache License 2.0. See LICENSE.
