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
  - /unforget init     — create UNFORGET.md and wire it into project conventions
  - /unforget add      — capture a new deferral (default: Session spillover)
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

Bootstrap UNFORGET.md and wire it into the project's conventions.

### Steps

1. **Confirm the file path.** Default: `Documentation/Development/Deferred/UNFORGET.md`. Ask if the user prefers a different path (`UNFORGET.md` at root is also common; some users want `.deferred/UNFORGET.md` or `docs/`).

2. **Ask the cadence question:**
   > "How does this project ship?"
   > - Discrete releases (mobile app, library, versioned product) → **Standard** preset
   > - Continuous deployment (web app, service, internal tool) → **Continuous** preset
   > - Solo / side project / want minimal columns → **Lean** preset
   > - Custom — I'll pick from a column pool

3. **Generate UNFORGET.md** with:
   - Title block (`# Deferred Work — Single Source of Truth`)
   - "Last promoted" date stamp (today)
   - "How to use this file" section explaining the chosen preset
   - The four section headers with empty 10-column tables
   - Promotion ritual block at the bottom

4. **Optionally wire CLAUDE.md / AGENTS.md / README.md.** Ask:
   > "Should I add a 'Deferred Work Index' section to your project's main AI instructions file (CLAUDE.md / AGENTS.md / etc.) so future sessions automatically read UNFORGET.md when you ask 'what's deferred'?"
   >
   > Recommended: Yes — without this, the skill's recall trigger is opt-in per session.

5. **Confirm the existing-deferral migration:** if there are existing deferral artifacts (a root-level Deferred.md, TODO files, an issues backlog), offer to migrate them in batch or one-at-a-time. Skip if greenfield.

### Success criteria

- UNFORGET.md exists at the chosen path with 4 empty section tables.
- The format key + Target/Window legend + promotion ritual are present.
- (Optional) CLAUDE.md / AGENTS.md has a Deferred Work Index section pointing at the file.
- The user can now run `/unforget add` without needing to remember the format.

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
