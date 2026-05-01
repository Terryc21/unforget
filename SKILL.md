---
name: unforget
version: 0.1.0
description: |
  A single source of truth for deferred work — paused plans, mid-task spillover,
  audit findings, and observed-but-not-yet-fixed bugs — organized so nothing slips
  through the cracks between releases. Use when the user asks "what's deferred?",
  "what's the backlog?", "prioritize my deferred work," "show me what's blocking
  release," or wants to log something for later without losing track of it.

  unforget enforces ONE file per project (UNFORGET.md by default), structured as
  four sections of 10-column rating tables, with a release-cycle Target column
  that promotes deferred items toward shipping at each release. The skill exists
  to prevent the most common deferral failure mode: items get logged in five
  different places and then nobody can find them when it matters.

  Subcommands:
  - /unforget init     — create UNFORGET.md, survey existing deferral artifacts, capture user-known items
  - /unforget add      — capture a new deferral (default: Session spillover)
  - /unforget edit     — refine an existing row's columns (Target, Urgency, etc.)
  - /unforget import   — re-run the surface survey after init (catches NEW artifacts)
  - /unforget list     — show current state, filterable by section / Target / Urgency
  - /unforget scan     — surface stale rows (rows aging past their priority threshold)
  - /unforget promote  — release-time ritual (verify THIS rows fixed; promote NEXT → THIS)
license: MIT
---

# unforget

> A way of not losing sight or track of what is deferred.

## Why this skill exists

Every developer defers things. The problem isn't the deferral — it's that deferred items end up scattered across:

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

The pattern was extracted from a real iOS project where deferred work had fragmented across five tracking surfaces and the consolidation freed ~3 hours of release-prep time per cycle.

---

## The format

UNFORGET.md is a single markdown file with **4 sections**, each containing a **10-column rating table**.

### Sections

| Section | What goes here | ID prefix |
|---|---|---|
| **1. Paused plans** | Work started, made progress, paused mid-execution. Each row points at a detail file. | P |
| **2. Session spillover** | Items that surfaced mid-task in some other work. Captured in 1-2 lines. | S |
| **3. Audit findings** | Items surfaced by audit tools (linters, code review, custom audit skills) that weren't fixed immediately. | A |
| **4. User-reported / observed** | Bugs noticed but not reproduced, friction observed, "this feels off" notes. Lower bar than audit findings. | U |

### Columns (Standard preset, 10-col)

`# | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status`

| Column | Meaning |
|---|---|
| **#** | Stable ID (P1, S2, A3, U4). Never reuse. |
| **Target** | Release-cycle commitment (see "Target values" below) |
| **Finding** | One-clause description. Multi-line OK. |
| **Urgency** | 🔴 CRITICAL / 🟡 HIGH / 🟢 MEDIUM / ⚪ LOW |
| **Risk: Fix** | What could break making the change. ⚪ Low / 🟢 Medium / 🟡 High / 🔴 Critical |
| **Risk: No Fix** | Cost of leaving it (crash, data loss, user-visible bug). Same scale. |
| **ROI** | 🟠 Excellent / 🟢 Good / 🟡 Marginal / 🔴 Poor |
| **Blast Radius** | ⚪ 1 file / 🟢 2-5 files / 🟡 6-15 files / 🔴 >15 files |
| **Fix Effort** | Trivial / Small / Medium / Large |
| **Status** | Open / In Progress / Fixed / Deferred / Skipped |

### Target values

| Target | Meaning |
|---|---|
| 🚢 **THIS** | Must ship in current release cycle. Blocks submission. |
| 🚢+1 **NEXT** | First post-release point update. Triaged as fixable but not blocking. |
| 🚢+2 **LATER** | Two cycles out or more. Real work, not yet scheduled. |
| 🌫️ **SOMEDAY** | No commitment. Captured so it doesn't get lost. May stay here forever. |

**Invariant:** `🚢 THIS` is the only Target that blocks shipping. At submission time, every `🚢 THIS` row must be Status = Fixed or have been demoted with a one-line reason.

### Presets

`unforget init` offers three presets at setup. Each is opinionated and complete; users pick the closest fit, and the skill adapts the table format accordingly.

| Preset | Audience | Columns |
|---|---|---|
| **Standard** | Mobile/desktop apps shipping discrete releases | All 10 columns above with Target |
| **Lean** | Solo devs, side projects, junior devs | 6 columns: # / Target / Finding / Urgency / Effort / Status |
| **Continuous** | Web apps, services, libraries with continuous deployment | 9 columns; replaces Target with Window (🟢 NOW / 🟡 THIS WEEK / 🔵 THIS MONTH / 🌫️ SOMEDAY) |

Users on Standard or Lean can also append **extra columns** (Client, Sprint, Component, etc.) without modifying core columns. Removing or renaming core columns is intentionally not supported — it breaks comparability across projects and tooling.

---

## /unforget init

Bootstrap UNFORGET.md AND populate it with existing deferred items from across the project's tracking surfaces. Init is the highest-leverage moment in the skill's lifecycle — the deferred items the user already has are exactly the items most at risk of being lost.

The flow is seven phases, in order. Phases 1–4 are automated discovery and triage. Phase 5 is user-driven capture. Phase 6 is an optional deep-dump. Phase 7 writes the file and wires recall into the project.

### Phase 1 — Setup questions

Three short questions before any scanning happens:

1. **File path:** Default `Documentation/Development/Deferred/UNFORGET.md`. Other common choices: `UNFORGET.md` at root, `.deferred/UNFORGET.md`, `docs/UNFORGET.md`.
2. **Cadence preset:**
   > "How does this project ship?"
   > - Discrete releases (mobile app, library, versioned product) → **Standard** preset (10 columns, Target column)
   > - Continuous deployment (web app, service, internal tool) → **Continuous** preset (9 columns, Window column)
   > - Solo / side project / want minimal columns → **Lean** preset (6 columns)
   > - Custom — pick from a fixed pool of 12 columns
3. **CLAUDE.md / AGENTS.md wiring:** "Add a 'Deferred Work Index' section to the project's main AI instructions file?" — recommended yes; without it, future AI sessions don't auto-recall UNFORGET.md when the user asks "what's deferred."

These three questions take ≤90 seconds. After this, the user is hands-off until Phase 5.

### Phase 2 — Surface survey (read-only)

Scan the project for existing deferred-work artifacts across six tractable surfaces. NOTHING is imported yet — this phase only produces a candidate list.

**Universal exclusion rule (applies to ALL surfaces):** any path containing a segment named `archive` or `Archive` is skipped. Files in archive paths are intentionally retired and importing them re-pollutes the active backlog with old work the project already moved past. Same for `.git/`, `node_modules/`, `vendor/`, `Pods/`, and the project's `Documentation/Development/Archive/` (or equivalent) folder if one exists. The skill should still REPORT the count of skipped archive files so the user knows they exist; just don't import them.

| Surface | Signal | Confidence |
|---|---|---|
| **Deferred-named files** at repo root or `Documentation/`, `docs/`, `notes/` (excluding archive paths) | Filenames matching `Deferred.md`, `BACKLOG.md`, `TODO.md`, `*deferred*.md` | High |
| **Audit-tool ledgers** (excluding archive paths) | `.radar-suite/ledger.yaml`, `.eslint-todos`, `.audit/`, custom audit YAML | High when present |
| **Plan files** in `./plans/`, `./.claude/plans/` only — global `~/.claude/plans/` is **NOT** scanned by default because it produces dozens of completed-session noise hits per project | Markdown files referencing the project name; explicit status hints (`PAUSED:`, `ABORTED:`, `IN PROGRESS:` in title or first heading) | Medium — many will be done, not deferred. User can opt in to global scan via `/unforget import --plans=global` |
| **Code comments** | Regex `// (TODO\|FIXME\|HACK\|XXX\|MIGRATION-NOTE\|DEFERRED)\b` (word boundary, NO required colon — many comment styles use space or paren after the tag) across `Sources/`, `src/`, `lib/`, etc. | Variable — typically 0–50 hits depending on project age and code-review discipline |
| **GitHub issues** (if `gh` CLI authenticated AND repo accessible) | Open issues labeled `deferred`, `wontfix-for-now`, `post-release`, `backlog` | High when labeled |
| **Memory files** | Filename match `^deferred_*.md` or `^project_deferred_*.md` (strict — body-text "defer" matches produce too many false positives from book/feedback files that mention deferral in passing) | High when filename matches; deprioritized for body-only matches |

**Audit-ledger format-aware parsing:** for known formats (`radar-suite/ledger.yaml`, `eslint`, etc.), parse the structured fields (`status`, `urgency`, `severity`, `file:line`) so Phase 4 auto-fill can populate columns from real signals instead of guessing from prose. For unknown audit formats, fall back to filename-based heuristics and flag the rows as needing manual review.

**Cross-surface deduplication:** before producing the candidate report, run a fuzzy-match dedup pass. If the same item appears in Deferred.md AND a plan file AND a memory file (common — e.g., a paused migration shows up in all three), merge into ONE candidate row with the multi-source pointer recorded in the Finding cell. Without this step, the survey produces 3× duplicate rows for the same logical item.

**GitHub issues — three states, not two:**
- `gh` not installed → "GitHub issues skipped (`gh` CLI not available)"
- `gh` installed but `gh auth status` fails → "GitHub issues skipped (`gh` not authenticated; run `gh auth login` to enable)"
- `gh` authed but `gh issue list` returns empty → "GitHub issues: 0 open issues with deferral labels found"

The spec must distinguish these so the user knows whether the surface is silent because empty or silent because broken.

Output of Phase 2 is a candidate report. Example (numbers will vary; treat as illustrative, not as expected counts):

```
Found N candidate deferred items across 6 surfaces:

📁 Deferred-named files (2 active, 3 archive paths skipped)
  • Deferred.md (~22 active rows after stripping RESOLVED entries)
  • BACKLOG.md (3 items)

📋 Audit ledgers (1 active, 3 archive ledgers skipped)
  • .radar-suite/ledger.yaml — 17 fixed, 1 deferred (RS-019), 1 accepted (RS-011)

📂 Plan files (project-local: 0; global ~/.claude/plans/ NOT scanned by default)
  • Run /unforget import --plans=global to scan ~/.claude/plans/ — typically noisy, prefer to keep paused-plan rows in Section 1 captured directly via Phase 5 user-add.

💬 Code comments (variable — typically 0–50)
  • Word-boundary regex: // (TODO|FIXME|HACK|XXX|MIGRATION-NOTE|DEFERRED)\b
  • Default skip — most TODOs are noise; user can opt in via /unforget import --comments

📝 Memory files (filename match)
  • project_v2_v3_migration_diagnostic_apr30.md
  • project_deferred_worker_hygiene.md
  • deferred_test_suite_failures_apr30.md

🐙 GitHub issues — depends on `gh` state (see "three states" rule above)

🔁 Cross-surface dedup: K candidates merged from M raw matches.
```

### Phase 3 — Triage (per-surface yes/no/skip)

For each surface that returned candidates, ask the user a single question:

- **High-confidence surfaces** (Deferred-named files, audit ledgers, memory files): "Import all N rows from `<source>`?" Default yes.
- **Medium-confidence surfaces** (plan files): "Review N plan files one-by-one?" Default yes — for each plan, offer import / skip / "uncertain, mark as needs-review".
- **Low-confidence surfaces** (code comments): "Skim 24 code comments now?" Default skip — most TODOs are noise; the user can run `/unforget import --comments` later if desired.

The user can skip any surface entirely. Nothing is forced.

### Phase 4 — Auto-fill defaults from source signals

For each row that the user agreed to import, the skill auto-fills as many of the 10 columns as it can infer.

**Format-aware mapping** is preferred over prose-based heuristics. When the source has a structured format (radar-suite YAML ledgers with explicit `status`/`urgency`/`severity` fields; ESLint-disable directives with rule names; etc.), parse the structured fields directly. Fall back to prose heuristics only when the source is unstructured (plain markdown, code comments).

| Column | Inferred from |
|---|---|
| **#** | Auto-assigned next ID per section (P1, P2, ...) |
| **Target / Window** | Map "release-blocker" / "must-fix" / explicit `target: THIS` → 🚢 THIS. "Post-release" / `target: NEXT` → 🚢+1 NEXT. "Future" / no tag → 🌫️ SOMEDAY. |
| **Finding** | Title or first line of source. Truncate at ~150 chars; full detail stays in source file (linked from the row). |
| **Urgency** | Structured format: pass through `urgency` / `severity` field. Prose: CRITICAL/HIGH/MEDIUM/LOW pass through; ERROR/WARNING/INFO map to HIGH/MEDIUM/LOW. No tag → ⚪ LOW. |
| **Risk: Fix** | Default ⚪ Low — needs human judgment. The skill shouldn't guess. |
| **Risk: No Fix** | If source mentions "data loss", "crash", "user-visible" → 🟡 High. Default ⚪ Low. |
| **ROI** | Default 🟢 Good. |
| **Blast Radius** | If source has structured `files:` list, count and map. If prose mentions file count → map. "Many files" → 🟡 6-15 files. Default ⚪ 1 file. |
| **Fix Effort** | Map source size estimates ("4-6 hours" → Medium, "trivial" → Trivial, "large refactor" → Large). Default Small. |
| **Status** | Open by default. "RESOLVED" / "FIXED" / "DONE" / structured `status: fixed` → Fixed (auto-archive — see Phase 7). "In progress" / structured `status: in_progress` → In Progress. Structured `status: deferred` → Deferred. Structured `status: accepted` → Skipped. |
| **Section** | Per-source mapping: Deferred-named files → Section 1 (Paused plans). Plan files → Section 1. Audit ledgers → Section 3 (Audit findings). Memory files → Section 1 (if filename starts `project_deferred_`) or Section 2 (if filename starts `deferred_` and content is session-spillover-shaped). Code comments → Section 4 (User-reported). GitHub issues → Section 1 if labeled `paused`/`blocked`, Section 4 otherwise. |

The skill is honest about not getting this perfect. Most cells will be defaults; the user upgrades them as they go via `/unforget edit`.

### Phase 5 — User-add pass (the most important phase)

The survey can't find items that exist only in the user's head, in a Slack DM, in a personal notes app, or in tacit knowledge from past sessions. After Phase 4, the skill explicitly invites the user to surface these:

> "Survey complete. N rows queued for import. Anything else you want to add before I write UNFORGET.md?
>
> Common things the survey can't find:
> - Bugs you've noticed but haven't logged anywhere
> - Friction you've felt while using the app
> - Items mentioned in Slack DMs, notes apps, or paper notebooks
> - Things you remember from past sessions that aren't in any file
> - 'I should really fix that someday' thoughts you've had
>
> Add items one at a time. Type 'done' when finished, or 'skip' to proceed without adding any."

For each item the user types, the skill:

1. **Picks a section automatically** based on phrasing (bug language → Section 4; "I started ... but didn't finish" → Section 1; everything else → Section 2). User can override.
2. **Auto-assigns the next ID** in that section.
3. **Sets conservative defaults** for the 10 columns (Target = 🌫️ SOMEDAY, Urgency = ⚪ LOW, etc.).
4. **Echoes** the captured row and moves to the next item.

The user is rattling off items, not filling out forms. Triage refinement happens later via `/unforget edit`. Speed matters more than completeness here — every item captured is one less item lost.

This phase typically catches 5–15 rows on a real project's first init. They're often the highest-value rows in the eventual file because no other surface contains them.

### Phase 6 — Deep-dump pass (optional, default skip)

For users who want to do a thorough deferral audit at adoption time:

> "Want to do a deeper deferral inventory? I can ask you 8–10 questions to surface items you might not remember on first pass. Takes 5–10 minutes. [yes / no / maybe later]"

If yes, the skill walks through prompts like:

- "Are there features in your app that 'mostly work but ___'?"
- "Are there parts of the codebase you avoid touching? Why?"
- "Are there bugs you've seen but couldn't reproduce reliably?"
- "Are there user requests you didn't reject but also didn't schedule?"
- "Are there workarounds you've put in place that should be replaced with proper fixes?"
- "Are there third-party dependencies you'd like to remove or replace?"
- "Are there tests you've muted or skipped that you want to fix later?"
- "Are there docs that are out of date or missing entirely?"

Each prompt that surfaces an item gets captured as a row (same flow as Phase 5 — section auto-pick, conservative defaults, fast capture).

Most users skip Phase 6 the first time and run it later when they have more time. That's fine — `/unforget import --deep` makes Phase 6 re-runnable on demand.

### Phase 7 — Diff preview, write file, wire recall

Before any file is written, show the user a summary diff:

```
About to create UNFORGET.md at <path> with:

  Section 1 (Paused plans): 24 rows
    • 22 from Deferred.md
    • 2 from memory files

  Section 2 (Session spillover): 3 rows
    • 3 from Phase 5 user-add

  Section 3 (Audit findings): 5 rows
    • 5 from .radar-suite/ledger.yaml

  Section 4 (User-reported): 1 row
    • 1 from Phase 5 user-add

Total: 33 rows imported, 0 needing date stamps, 18 RESOLVED items moved to archive section.
24 code comments NOT imported (run /unforget import --comments later if desired).

Proceed? [yes / preview each section / cancel]
```

User can preview each section before committing. If they cancel, no files are touched. If they proceed:

1. **Write UNFORGET.md** with all imported rows in their assigned sections.
2. **Move RESOLVED / FIXED items** to a separate archive file (`UNFORGET-archive-<date>.md` in the same directory).
3. **Optionally rename / replace the source files**: e.g., replace root `Deferred.md` with a redirect pointer to UNFORGET.md (preserving git history). Always ask before modifying any source file.
4. **Wire CLAUDE.md / AGENTS.md** with the Deferred Work Index section (if user agreed in Phase 1).
5. **Print a final summary** with the row count, the path, the next-step suggestion ("run `/unforget list --target=THIS` to see release blockers").

### Success criteria for `/unforget init`

After init runs:

- UNFORGET.md exists at the chosen path with rows imported from existing surfaces and items captured from the user's memory.
- Source files (Deferred.md, ledgers, etc.) are either archived or replaced with redirects — never silently deleted.
- CLAUDE.md / AGENTS.md has a Deferred Work Index section so future AI sessions auto-recall UNFORGET.md.
- The user can run `/unforget list --target=THIS` and see exactly what's blocking the next release, in one screen.

---

## /unforget edit

Refine a row's columns after import. Most useful immediately after `/unforget init` to upgrade auto-filled defaults.

### Usage

```
/unforget edit P3                       — open row P3 for editing
/unforget edit P3 --target=THIS          — change just the Target cell
/unforget edit P3 --status=Fixed         — mark Fixed (next promotion will archive)
/unforget edit S5 --urgency=HIGH --roi=Excellent
```

### Steps

1. Find the row by ID. Show its current 10 columns.
2. Prompt for which cells to update (or accept flag overrides if passed inline).
3. Show the diff (old → new for each changed cell).
4. Apply the change to UNFORGET.md.

`/unforget edit` is the everyday command for keeping rows accurate. Pair with `/unforget list --age=30+` to find rows that need review.

---

## /unforget import

Re-run the Phase 2 surface survey after `/unforget init` has already created the file. Useful when:

- New audit-tool runs have produced findings that should be captured
- A new `Deferred.md` or plan file appeared that wasn't there at init
- You want to run the Phase 6 deep-dump now that you didn't run at init
- You want to scan code comments (`--comments` flag) which init skipped by default

### Usage

```
/unforget import                         — re-run the standard survey (Phases 2–4 + 7)
/unforget import --comments              — include code comments (skipped by default)
/unforget import --deep                  — run the Phase 6 deep-dump questions
/unforget import --source=<path>         — survey a specific file or directory only
```

### Steps

Same as `/unforget init` Phases 2–4 and Phase 7, but operates against an EXISTING UNFORGET.md:

- New rows get appended with auto-assigned IDs (continuing the per-section sequence).
- Duplicate detection: if a survey row matches an existing UNFORGET.md row by similarity (fuzzy match on Finding text + source pointer), the skill flags it and asks whether to skip or import as a separate row.
- The Phase 7 diff preview shows what's NEW, not the full file state.

`/unforget import` is the second-most-important command after `/unforget add`. It's how the skill stays current with the project's evolving deferral surfaces.

---

## /unforget add

Capture a new deferral. The friction point that makes or breaks the skill — must be fast.

### Usage

```
/unforget add "Brief description of the thing being deferred"
```

### Steps

1. **Read UNFORGET.md** to find the next available ID in the chosen section.
2. **Default to Section 2 (Session spillover)** unless the user specifies a section. Section 2 is where most mid-task captures naturally belong.
3. **Auto-fill defaults** for the rating columns:
   - Target: `🌫️ SOMEDAY` (most conservative; user can promote later)
   - Urgency: `⚪ LOW`
   - Risk: Fix / Risk: No Fix: `⚪ Low`
   - ROI: `🟢 Good`
   - Blast Radius: `⚪ 1 file`
   - Fix Effort: `Small`
   - Status: `Open`
4. **Ask the user to override any defaults** (single AskUserQuestion with all relevant fields, or accept the defaults to skip ahead).
5. **Append the row** to the chosen section.
6. **Echo back** the new row ID and a one-line confirmation.

### Subsection flags (optional)

- `--paused` → Section 1 (Paused plans). Triggers an extra prompt for the detail-file pointer.
- `--audit` → Section 3 (Audit findings). Asks for the originating audit tool and finding ID.
- `--observed` → Section 4 (User-reported / observed).
- `--target=THIS|NEXT|LATER|SOMEDAY` → set Target without prompting.
- `--urgent` → shorthand for `--target=THIS --urgency=HIGH`.

### Speed target

≤30 seconds end-to-end for default usage. If the skill ever takes longer than 30 seconds to capture an item, it has failed at its core promise.

---

## /unforget list

Show current state. Default view is sorted by Target (🚢 THIS first), then Urgency (CRITICAL first).

### Usage

```
/unforget list                        — full table
/unforget list --target=THIS          — only ship-blockers
/unforget list --section=audit        — only Section 3
/unforget list --status=Open          — exclude Fixed/Skipped
/unforget list --stale                — only rows past their staleness threshold
/unforget list --age=30+              — only rows older than 30 days
```

### Output format

The skill renders the matching rows in the same 10-column format as UNFORGET.md, with a one-line summary at the top:

> "12 rows total: 2 🚢 THIS (release blockers), 5 🚢+1 NEXT, 5 🌫️ SOMEDAY. Stale: 1."

For the simplest case (`/unforget list` alone), this is the answer the user was actually looking for when they asked "what's deferred?"

---

## /unforget scan

Identify rows past their staleness threshold. Read-only — never modifies the file.

### Staleness thresholds (default)

| Status / Target | Stale after |
|---|---|
| Status = Open or In Progress | 30 days |
| Status = Deferred AND Target = 🚢+1 NEXT | 90 days |
| Status = Deferred AND Target = 🚢+2 LATER | 180 days |
| Status = Deferred AND Target = 🌫️ SOMEDAY | 365 days |
| Status = Skipped | never stale |
| Status = Fixed | never stale (but flag as ready-for-archive) |

These thresholds can be customized in a config block at the top of UNFORGET.md.

### Output structure

```
# UNFORGET.md Stale-Scan — <date>

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

- **investigate** — stale and may need fresh diagnosis
- **promote** — should move toward THIS (e.g., NEXT deferred too long)
- **demote** — Urgency was overstated; downgrade Target
- **archive** — no longer relevant; move to historical archive

Default to **investigate** if uncertain. The scan never modifies UNFORGET.md — it only reports.

### Scheduling

`/unforget scan` is safe to run on demand. For automated recurring scans, the user can schedule it via Claude Code's `/schedule` skill (or any cron-like external scheduler). The skill output is plain markdown, suitable for posting to Slack, email, or GitHub Actions summary.

---

## /unforget promote

Release-time ritual. Run at every release submission.

### Steps

1. **Verify** every `🚢 THIS` row has Status = Fixed. List any that don't and require an explicit demotion or fix.
2. **Promote** all `🚢+1 NEXT` rows → `🚢 THIS` (they are now the next release's blockers).
3. **Re-triage** all `🚢+2 LATER` rows that are still relevant → `🚢+1 NEXT`. Items no longer relevant get archived.
4. **Re-rank `🌫️ SOMEDAY`** items ≥180 days old: prompt user for promote / demote / archive.
5. **Stamp** the "Last promoted" line at the top of UNFORGET.md with new build/version + date.

This command DOES modify UNFORGET.md (unlike `/unforget scan`), so the user is shown a preview of every change before it's applied.

---

## How to use unforget alongside CLAUDE.md / AGENTS.md

The skill works best when the project's main AI instructions file has a section that points at UNFORGET.md as the canonical deferral source. `/unforget init` offers to add this for you. Example block:

```markdown
## Deferred Work Index

**Single source of truth:** `Documentation/Development/Deferred/UNFORGET.md`

Read this file when:
- The user asks "what's deferred?", "what's the backlog?", "prioritize my plans," or any variant.
- Before suggesting a release / submission — to check 🚢 THIS rows for unresolved blockers.
- When a task in the current session needs to be deferred — log a row here, do NOT create a new tracking file unless the entry needs detail beyond one row.

**Format:** 10-column rating table per section. **Sections:** Paused plans / Session spillover / Audit findings / User-reported.

**Target column** is the release-cycle commitment: 🚢 THIS / 🚢+1 NEXT / 🚢+2 LATER / 🌫️ SOMEDAY.

Never log deferred items elsewhere. Memory files, plan files, and audit ledgers are detail stores; UNFORGET.md is the index.
```

This block is what makes the skill's recall trigger work — without it, future AI sessions don't know to read UNFORGET.md when the user asks about deferred work.

---

## Anti-patterns

Things this skill deliberately does NOT do, and why:

- **Custom column reordering.** Breaks comparability across projects.
- **Custom rating scales.** Letting one user use 🔴/🟡/🟢/⚪ and another use P0/P1/P2/P3 makes the format un-shareable.
- **Per-row column visibility.** Hiding columns on some rows but not others. Devolves into chaos.
- **Renaming core columns.** "Call Urgency 'Priority' instead." Skill becomes incompatible with itself.
- **Multiple files.** UNFORGET.md is the index. Detail files (per-plan markdown) are linked FROM rows, not duplicates of them.
- **Auto-deferring things the AI thinks should be deferred.** Deferral is a user decision. The skill captures, organizes, and surfaces — it doesn't decide on the user's behalf.

---

## Compatibility notes

- **Non-Claude-Code use:** UNFORGET.md is plain markdown. The format works fine in any editor, on GitHub, in Linear, etc. The slash commands require Claude Code, but the file itself is portable.
- **Multi-user / team use:** UNFORGET.md commits to git like any other markdown. Concurrent edits use standard merge resolution. Status changes between Open / In Progress / Fixed should be done atomically per row to minimize merge churn.
- **Other AI assistants:** The "Deferred Work Index" block in CLAUDE.md / AGENTS.md works for any AI that reads project instructions. Cursor, Copilot, Aider, etc. can all benefit from the recall trigger pattern.
- **CI integration:** `/unforget scan` output is structured markdown. A simple GitHub Action can run the scan weekly and post the report to a Slack channel or open an issue.

---

## License

MIT. See LICENSE.
