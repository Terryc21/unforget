---
name: unforget
version: 0.2.0
description: |
  A single source of truth for deferred work (paused plans, mid-task spillover,
  audit findings, and observed-but-not-yet-fixed bugs), organized so nothing slips
  through the cracks between releases. Use when the user asks "what's deferred?",
  "what's the backlog?", "prioritize my deferred work," "show me what's blocking
  release," or wants to log something for later without losing track of it.

  unforget enforces ONE file per project (UNFORGET.md by default), structured as
  four sections of 10-column rating tables, with a release-cycle Target column
  that promotes deferred items toward shipping at each release. The skill exists
  to prevent the most common deferral failure mode: items get logged in five
  different places and then nobody can find them when it matters.

  Subcommands:
  - /unforget init     ·  create UNFORGET.md, survey existing deferral artifacts, capture user-known items
  - /unforget add      ·  capture a new deferral (default: Session spillover)
  - /unforget edit     ·  refine an existing row's columns (Target, Urgency, etc.)
  - /unforget import   ·  re-run the surface survey after init (catches NEW artifacts)
  - /unforget list     ·  show current state, filterable by section / Target / Urgency
  - /unforget scan     ·  surface stale rows (rows aging past their priority threshold)
  - /unforget promote  ·  release-time ritual (verify THIS rows fixed; promote NEXT to THIS)
  - /unforget --version ·  print skill version, install path, and supported format-version (install-verification)
license: Apache-2.0
---

# unforget

> Installed as a Claude Code plugin in v0.2+. Manual install via `~/.claude/skills/unforget/` (invoked as `/skill unforget`) still works as a v0.1 fallback.

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

When the user asks "what's deferred?" months later, the answer requires walking five surfaces. Items go stale. Some get fixed by accident. Some sit forever because nobody remembered them.

`unforget` collapses all deferral into ONE file (`UNFORGET.md`) with a structured format that:

1. **Forces the deferral question** ("when does this ship?") via the Target column.
2. **Surfaces staleness** via a built-in scan command that flags items past their age threshold.
3. **Standardizes the format** so any developer reading any project's UNFORGET.md instantly recognizes the structure.

The pattern was extracted from a real Universal app (iOS, iPadOS, macOS) where deferred work had fragmented across five tracking surfaces. Consolidation freed roughly 3 hours of release-prep time per cycle.

---

## Format at-a-glance

UNFORGET.md is a single markdown file with **4 sections**, each containing a **10-column rating table**.

**Sections:** 1. Paused plans (P) · 2. Session spillover (S) · 3. Audit findings (A) · 4. User-reported / observed (U)

**Columns (Standard preset):** `# | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status`

**Target values:** 🔴 THIS (blocks current release) · 🔵 NEXT (next post-release update) · 🟡 LATER (two cycles out) · ⚪ SOMEDAY (no commitment)

**Invariant:** `🔴 THIS` is the only Target that blocks shipping. At submission time, every `🔴 THIS` row must be Status = Fixed or have been demoted with a one-line reason.

**Full format spec — column meanings, Status enum, detail-block format (closure pointer → body → spawn links), Standard / Lean / Continuous presets, and anti-patterns — lives in `reference/format.md`.** Read that file when writing or validating a row.

---

## Subcommand surface

| Subcommand | One-line purpose | Full spec |
|---|---|---|
| `/unforget init` | Bootstrap UNFORGET.md and survey existing deferral artifacts across the project | `reference/init.md` (with surface detail in `reference/surfaces.md`) |
| `/unforget add` | Capture a new deferral (defaults to Section 2 / Session spillover); 30s end-to-end | `reference/commands.md` |
| `/unforget edit` | Refine a row's columns; closure recommendations on `--status=Fixed` | `reference/commands.md` |
| `/unforget import` | Re-run the surface survey after init (catches NEW artifacts) | `reference/commands.md` (surface detail in `reference/surfaces.md`) |
| `/unforget list` | Show current state, filterable by section / Target / Urgency / age / staleness | `reference/commands.md` |
| `/unforget scan` | Identify rows past their staleness threshold; read-only | `reference/commands.md` |
| `/unforget promote` | Release-time ritual: verify 🔴 THIS rows fixed, promote 🔵 NEXT to 🔴 THIS | `reference/promotion.md` (with backups in same file) |
| `/unforget --version` | Print version, install path, supported format-version; install-verification | `reference/commands.md` |

**Decision flowchart — which subcommand do I run?**

- **No UNFORGET.md exists in the project yet** → `/unforget init`
- **You want to capture one new item, fast** → `/unforget add "<finding>"`
- **You want to update an existing row's columns** → `/unforget edit <ID>`
- **A new audit / plan / memory file appeared since init** → `/unforget import`
- **The user just asked "what's deferred?"** → `/unforget list` (or `/unforget list --target=THIS` for ship-blockers only)
- **You want to find rows that have aged past their thresholds** → `/unforget scan`
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
| `reference/commands.md` | Per-subcommand specs for `add`, `edit`, `import`, `list`, `scan`, `--version` | Running any of those subcommands |
| `scripts/*.py` | Deterministic helpers (surface scan, fuzzy dedup, path encoding, format-version check, backup prune). JSON in / JSON out. Standard library only. See `scripts/README.md`. | Whenever the corresponding reference file delegates to a script |

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

Every read operation (`add`, `list`, `promote`, `scan`, `edit`, `import`) checks for an HTML comment marker of the form `<!-- unforget-format: vN -->` near the top of UNFORGET.md. The marker declares which version of the unforget file format the file conforms to. v0.2 of the skill supports format `v1`. Three cases:

- **Marker absent.** The skill prompts: "this file may not be in unforget format; proceed anyway?" Default response is no. If the user proceeds, the skill operates as best it can without format guarantees, and recommends adding `<!-- unforget-format: v1 -->` near the top of the file to silence the prompt on future reads.
- **Marker recognized (`v1`).** The skill proceeds normally.
- **Marker is a future version (`v2` or higher when the skill is v0.2).** The skill prints: "this file declares unforget format vN, but this skill version supports up to v1. Operating in read-only mode; writes are refused." Read-only operations (`list`, `scan`, and `promote --dry-run`) still work. Write operations (`add`, `edit`, `import`, and `promote` without `--dry-run`) refuse with a one-line error pointing to the version mismatch and recommending a skill upgrade.

**Preferred implementation:** delegate the marker read to `python3 scripts/check_format_version.py <path-to-UNFORGET.md>` (returns JSON). Algorithm fallback if Python is unavailable: read the first 30 lines of the file, grep for `<!-- unforget-format: v` (case sensitive), parse the version digit, compare against supported.

---

## Anti-patterns (summary)

Things this skill deliberately does NOT do, and why. Full discussion in `reference/format.md`.

- **Custom column reordering.** Breaks comparability across projects.
- **Custom rating scales.** Letting one user use 🔴/🟡/🟢/⚪ and another use P0/P1/P2/P3 makes the format un-shareable.
- **Per-row column visibility.** Devolves into chaos.
- **Renaming core columns.** Skill becomes incompatible with itself.
- **Multiple files.** UNFORGET.md is the index. Detail files (per-plan markdown) are linked FROM rows, not duplicates of them.
- **Auto-deferring things the AI thinks should be deferred.** Deferral is a user decision. The skill captures, organizes, and surfaces; it doesn't decide on the user's behalf.

---

## License

Apache License 2.0. See LICENSE.
