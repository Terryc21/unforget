---
name: unforget
version: 0.1.0
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

### Detail blocks

Each section table is followed by a `### Detail - <section name>` subsection. Detail blocks hold the prose context that doesn't fit in the 10-column table (the why, the file paths, the linked plan refs, the resolution history). One detail bullet per ID; the bullet starts with the ID in bold (`- **P1** - ...`).

**Detail block format (three parts in order):**

1. **Closure pointer (only if the row is closed).** Lead the body with `**CLOSED YYYY-MM-DD: [one-sentence summary of how it closed].**` This pointer is what makes a closed row's outcome scannable; future readers see "what happened" without reading the full body. For Open rows, skip this part entirely.
2. **Body.** History, files, plan refs, context, gotchas. Free-form prose. Length is whatever the row needs; some rows are one sentence, some are five paragraphs. The Finding cell in the table is the headline; the body is the article.
3. **Spawn links (only if the row is part of a chain).** `Spawned-from: <ID>` if this row was created by closing another row (e.g., a workaround that spawned a real-fix follow-up). `Spawns: <ID>` if closing this row created a follow-up row. Both directions are recorded so the chain can be walked from either end.

**Example (closed row with a spawned follow-up):**

```
- **P3** - **CLOSED 2026-04-20: hidden the menu entry until server signing lands. Spawns: P6.** Every item that showed the Wallet feature failed when the user completed the flow. Blocked on server `/api/wallet/sign-pass` + Apple Pass Type ID. Pre-submission decision: complete the worker endpoint OR hide the menu item (~30 min if hiding). Chose hiding for build 13; future endpoint work tracked at row P6.
```

**Example (open row with no spawn link):**

```
- **P4** - Search relevance overhaul. Phases 1-4 (term weighting, stop words, fuzzy match, synonym expansion) shipped in build 11. Phases 5-7 (personalization, click-through learning, query rewriting) require a Cloudflare D1 schema we don't have yet. Plan: `~/.claude/plans/search-overhaul.md`.
```

The format is intentionally simple: closure pointer, body, spawn links. The skill's `add` / `edit` / `promote` flows preserve this structure when they touch a detail block. Hand-editing a detail block is fine as long as the three parts stay in order and the closure pointer (if present) stays at the top.

### Presets

`unforget init` offers three presets at setup. Each is opinionated and complete; users pick the closest fit, and the skill adapts the table format accordingly.

| Preset | Audience | Columns |
|---|---|---|
| **Standard** | Mobile/desktop apps shipping discrete releases | All 10 columns above with Target |
| **Lean** | Solo devs, side projects, junior devs | 6 columns: # / Target / Finding / Urgency / Effort / Status |
| **Continuous** | Web apps, services, libraries with continuous deployment | 9 columns; replaces Target with Window (🟢 NOW / 🟡 THIS WEEK / 🔵 THIS MONTH / 🌫️ SOMEDAY) |

Users on Standard or Lean can also append **extra columns** (Client, Sprint, Component, etc.) without modifying core columns. Removing or renaming core columns is intentionally not supported, because it breaks comparability across projects and tooling.

---

## /unforget init

Bootstrap UNFORGET.md AND populate it with existing deferred items from across the project's tracking surfaces. Init is the highest-leverage moment in the skill's lifecycle. The deferred items the user already has are exactly the items most at risk of being lost.

The flow is seven phases, in order. Phases 1 through 4 are automated discovery and triage. Phase 5 is user-driven capture. Phase 6 is an optional deep-dump. Phase 7 writes the file and wires recall into the project.

**Re-running init policy:** if `init` runs against a project that already has an UNFORGET.md (at the recommended `Documentation/Development/Deferred/UNFORGET.md` path or any other path the user previously chose), abort BEFORE Phase 1 with this message:

> UNFORGET.md already exists at `<path>`. Init is intended to bootstrap a project, not re-bootstrap it.
>
> - To add new items that have appeared since init (a new audit report, a new plan file, items you've thought of since), run `/unforget import`.
> - To capture a single new item, run `/unforget add "<finding>"`.
> - To start over from scratch (rare, usually only after a format-version migration or a corrupted file), delete or rename `<path>` and re-run `/unforget init`.

The skill must NOT silently overwrite or merge into an existing UNFORGET.md. The init flow makes destructive changes (renames source files, archives RESOLVED rows, wires the AI instruction file); running it twice would re-do all of that against a file that already has user data and risk losing rows. The abort is the safety net.

### Phase 1: Setup questions

Three short questions before any scanning happens:

1. **File path.** The default depends on what the project already has. Check the repo first:
   - If `Documentation/` exists with subdirectories: default `Documentation/Development/Deferred/UNFORGET.md` (matches projects with formal docs trees, like iOS/macOS apps)
   - If `docs/` exists: default `docs/UNFORGET.md` (matches conventional library / web projects)
   - If neither exists: default `UNFORGET.md` at repo root (matches minimal single-purpose repos like skills, CLI tools, small libraries)

   Always offer the user the chance to override. The point is to not impose a directory structure the project doesn't already use.

2. **Cadence preset.**
   > "How does this project ship?"
   > - Discrete releases (mobile app, library, versioned product) routes to **Standard** preset (10 columns, Target column)
   > - Continuous deployment (web app, service, internal tool) routes to **Continuous** preset (9 columns, Window column)
   > - Solo / side project / want minimal columns routes to **Lean** preset (6 columns)
   > - Custom: pick from a fixed pool of 12 columns

3. **AI instructions file wiring.** Different AI tools use different conventions:
   - Claude Code: `CLAUDE.md`
   - Anthropic Agent SDK / generic: `AGENTS.md`
   - Warp: `WARP.md`
   - Cursor: `.cursorrules` or `.cursor/rules/`
   - Aider: `.aider.conf.yml`
   - Continue: `.continue/`

   Scan the repo for any of these. If exactly one is found, ask: "Add a 'Deferred Work Index' section to `<filename>` so future AI sessions auto-recall UNFORGET.md when you ask 'what's deferred'?" If multiple are found, list them and let the user pick which to wire (or all, or none). If none is found, ask whether to create a `CLAUDE.md` or `AGENTS.md`. Recommended yes; without it, the recall trigger is opt-in per session.

   The wiring step shouldn't hardcode filenames. It should detect what the project actually uses and adapt.

These three questions take 90 seconds or less. After this, the user is hands-off until Phase 5.

### Phase 2: Surface survey (read-only)

Scan the project for existing deferred-work artifacts across six tractable surfaces. NOTHING is imported yet; this phase only produces a candidate list.

**Universal exclusion rule (applies to ALL surfaces):** any path containing a segment named `archive` or `Archive` is skipped. Files in archive paths are intentionally retired, and importing them re-pollutes the active backlog with old work the project already moved past. Same for `.git/`, `node_modules/`, `vendor/`, `Pods/`, and the project's `Documentation/Development/Archive/` (or equivalent) folder if one exists. **In addition, any markdown file whose filename matches `*archive*.md` (case insensitive) is skipped regardless of path** so that files like `Deferred-archive-2026-05-01.md` sitting in an active directory are not wrongly imported as fresh deferrals. The skill should still REPORT the count of skipped archive files (path-based and filename-based combined) so the user knows they exist; just don't import them.

| Surface | Signal | Confidence |
|---|---|---|
| **Deferred-named files** at repo root or `Documentation/`, `docs/`, `notes/` (excluding archive paths) | Filenames matching `Deferred.md`, `BACKLOG.md`, `TODO.md`, `*deferred*.md`, `*roadmap*.md`, `ROADMAP.md`, `*plan*.md` (case insensitive). **Plus a content-shape heuristic:** files containing 3 or more headings matching `Tier N` / `Phase N` / `Priority N` patterns are flagged as deferral artifacts even if their filename does not match the regex above. | High |
| **Audit-tool reports** (excluding archive paths) | radar-suite v3+: per-finding source is `scratch/audit-*-YYYY-MM-DD.md` (markdown, e.g., `audit-concurrency-2026-04-25.md`); `.radar-suite/ledger.yaml` is read for audit-run metadata only. Other tools: `.eslint-todos`, `.audit/`, custom audit YAML. | High when present |
| **Plan files** in `./plans/`, `./.claude/plans/`, `./.agents/plans/` (and any other `**/plans/*.md` excluding archive paths) only. Global `~/.claude/plans/` is **NOT** scanned by default because it produces dozens of completed-session noise hits per project. | Markdown files referencing the project name; explicit status hints (`PAUSED:`, `ABORTED:`, `IN PROGRESS:` in title or first heading) | Medium. Many will be done, not deferred. User can opt in to global scan via `/unforget import --plans=global`. |
| **Code comments** | Regex `// (TODO\|FIXME\|HACK\|XXX\|MIGRATION-NOTE\|DEFERRED)\b` (word boundary, NO required colon, because many comment styles use space or paren after the tag) across `Sources/`, `src/`, `lib/`, etc. | Variable, typically 0 to 50 hits depending on project age and code-review discipline |
| **GitHub issues** (if `gh` CLI authenticated AND repo accessible) | Open issues labeled `deferred`, `wontfix-for-now`, `post-release`, `backlog` | High when labeled |
| **Memory files** | Filename match `^deferred_*.md` or `^project_deferred_*.md` (strict, because body-text "defer" matches produce too many false positives from book/feedback files that mention deferral in passing) | High when filename matches; deprioritized for body-only matches |

**Redirect-pointer pre-check (Surface 1):** before parsing a Surface 1-matched file, check whether it is a redirect pointer rather than a real backlog. A file qualifies as a redirect pointer if BOTH conditions hold:

1. The file is fewer than 30 lines.
2. The file body contains at least one of: the literal phrase `MOVED`, the literal phrase `see also`, or a relative or absolute path reference to `UNFORGET.md` or another deferral file (e.g., `Documentation/Development/Deferred/UNFORGET.md`).

When both conditions hold, skip the file with a status note: `<file>: redirect pointer skipped (points to <target>)`. Do not parse it as a backlog. The user is informed the file was found but not imported. Stuffolio repro: a project's root `Deferred.md` is a 12-line redirect to `Documentation/Development/Deferred/UNFORGET.md`. Without this pre-check, the redirect text would be parsed as deferral entries.

**Memory directory location, per detected AI tool (Surface 6):** the memory-file scan needs to know where memory files live. The location depends on which AI assistant the project is wired to (detected during Phase 1: `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.aider.conf.yml`, etc.). If multiple AI tools are wired, scan each detected tool's memory directory and merge results.

| Detected AI tool | Memory directory |
|---|---|
| **Claude Code** (`CLAUDE.md` or `AGENTS.md` present) | `~/.claude/projects/<encoded-project-path>/memory/` |
| **Cursor** (`.cursorrules` present) | TODO: research and pin in v0.3. For v0.2, fall back to filename-only scan in repo root. |
| **Aider** (`.aider.conf.yml` present) | TODO: research and pin in v0.3. For v0.2, fall back to filename-only scan in repo root. |

**Claude Code path-encoding rule:** the current working directory is converted to a dash-separated string with each `/` replaced by `-` AND each whitespace character (space, tab) also replaced by `-`. The leading `/` becomes a leading `-`. Example: working directory `/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio` encodes to `-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio`, so memory files live at `~/.claude/projects/-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio/memory/`. The skill must compute this path from the cwd at scan time, not hardcode it.

**Memory directory fallback (Claude Code):** Claude Code stores per-project memory at the encoded directory matching the cwd, but historically projects opened from a parent directory may have memory under that parent's encoded path instead (e.g., a session opened in `/Volumes/2 TB Drive/Coding/GitHubDeskTop/` for a Stufflio task may have written memory under `-Volumes-2-TB-Drive-Coding-GitHubDeskTop/memory/` rather than `-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio/memory/`). When the cwd-encoded directory is empty or missing, walk up the cwd one segment at a time and check each ancestor's encoded directory. Stop walking at `~` or after 4 ancestor levels, whichever comes first. Report each ancestor scanned: "Memory files: scanned cwd-encoded path (0 files), parent-encoded path (4 files)."

If the encoded directory does not exist, the surface reports "Memory files: directory not found at `<path>`" rather than silently scanning zero files. The user knows the surface tried and where it looked.

**Memory meta-file content-shape pre-check (Surface 6):** filename matching alone catches both real findings and meta-docs. Files that match `^deferred_*.md` or `^project_deferred_*.md` but whose body describes the deferral system rather than containing actual findings should not be auto-imported. Before importing a Surface 6 match, scan the body for meta-doc phrases:

- The literal phrase `single source of truth`
- The literal phrase `format:` (lowercase, with colon, indicating a format-spec doc)
- The literal phrase `how to use`
- The literal phrase `index of` or `pointer to`

If any phrase is detected, prompt the user instead of auto-importing: `<file>: looks like a meta-doc (matched: '<phrase>'). Import anyway? [yes / no / preview]`. Stuffolio repro: `deferred_work_index.md` is a meta-doc that points at `Documentation/Development/Deferred/UNFORGET.md`; it contains zero deferred-work rows. Without this pre-check, its prose ("single source of truth is now `Documentation/Development/Deferred/DEFERRED.md`") would be parsed as a finding.

### Surface 1b: General documentation scanning

The six surfaces above catch deferral artifacts in conventional locations (Deferred-named files, audit ledgers, plan dirs, code, GitHub issues, memory). They miss the much larger set of deferred work that lives inside ordinary project documentation: dated planning notes, scratch audit reports, design docs with "Deferred" sections, hand-written backlog rollups. In a complex project, these locations hold roughly 80% of the actively-deferred items.

**Scan paths (excluding archive paths and the universal exclusions):**
- `Documentation/Development/*.md`
- `Documentation/Notes/*.md`
- `scratch/*.md`
- Equivalents (`docs/notes/`, `notes/`, `dev-docs/`, etc.) discovered during Phase 1 setup

**Heuristics (seven total). Any single match flags the file as a candidate:**

1. Heading text contains the literal word **`Deferred`** (case insensitive).
2. Heading text contains the literal word **`Pending`** (case insensitive).
3. Heading text contains the literal word **`TODO`** (case insensitive).
4. Heading text matches the pattern **`Phase N pending`** / **`Phase N deferred`** / **`Phase N todo`** (case insensitive, N is any digit).
5. Filename starts with a **date prefix** (`YYYY-MM-DD-*.md`), which conventionally marks a session/incident write-up that often contains rollup deferrals.
6. Heading begins with the explicit prefix **`DEFERRED:`** (case insensitive).
7. **Audit-report shape (scoped):** heading text matches a severity-tier prefix (`HIGH Issues`, `MEDIUM Issues`, `LOW Issues`, `CRITICAL Issues`) OR a per-finding ID pattern (regex `^#+\s+[A-Z]+-[A-Z][0-9]+:`, e.g., `### CONC-H1: ...`, `### RS-019: ...`). **This heuristic only fires on files Surface 2 already identified as audit reports** (post-T-12: any file matching `scratch/audit-*-YYYY-MM-DD.md` or another known audit-tool format). It never fires on prose docs that happen to use `## HIGH PRIORITY` headings, eliminating a large false-positive class.

**Behavior on match: each candidate prompts the user.** Surface 1b never auto-imports. Prose-shape detection is fuzzy by nature; a heading containing the word "Deferred" can mean "items being deferred from this work" or "deferred work that was already completed and archived in this doc" or "discussion of deferred work in general". The user is the safety net that distinguishes those cases. The skill's job is to surface candidates and the user's job is to decide.

**Audit-report rollup (heuristic 7):** when heuristic 7 fires, treat each per-finding ID heading inside the report as a candidate finding row. The severity-tier section header (`## HIGH Issues`, etc.) provides the urgency signal for findings beneath it (HIGH → 🟡 HIGH, MEDIUM → 🟢 MEDIUM, LOW → ⚪ LOW, CRITICAL → 🔴 CRITICAL). To avoid prompt fatigue on reports with 10+ findings, the user prompt rolls up per-report rather than per-finding: "Import N findings from `<audit-file>`?" with a yes / no / per-finding-review choice.

**Output format:** report each match as a one-line candidate (`<file>: <heading text> (heuristic <N>)`) under a `📄 General documentation` group in the Phase 2 summary. Audit-report files (heuristic 7) report as a single grouped line per file: `<file>: N findings (heuristic 7)`. Counts roll up the same way as the six core surfaces.

**Audit-tool format-aware parsing:**

For **radar-suite v3+** (the supported version; pin compatibility to v3 and above), the deferred-work source is split across two files per audit run:

- `scratch/audit-<domain>-YYYY-MM-DD.md` is the per-finding source. These are markdown reports containing the actual deferred items in prose form, with severity tags (🔴 / 🟡 / 🟢), heading-level findings, and inline file:line references. Real radar-suite filenames look like `audit-concurrency-2026-04-25.md`, `audit-codable-2026-03-31.md`, `audit-energy-2026-02-28.md`. Use prose heuristics to extract Finding text + urgency from each section. The earlier v3 alpha pattern `*-radar-*-YYYY-MM-DD.md` is no longer current; do not match on it.
- `.radar-suite/ledger.yaml` is read for audit-run metadata only. Map: `audit_started` → row date stamp; `sessions[].skill` → audit-tool name (which radar skill produced the finding); `sessions[].timestamp` → recency signal for staleness scoring. Do NOT attempt to extract per-finding rows from `ledger.yaml`; the v3 schema records audit-run summaries (counts, grades, baselines), not individual findings.
- **Hardcoded allowlist inside `.radar-suite/`:** only `ledger.yaml` is read. All other yaml files (`*-handoff.yaml`, `project.yaml`, `session-prefs.yaml`, plus any future schema additions) are inter-skill state or config and are explicitly skipped, even if they contain words like "deferred" or "pending" in their bodies. The allowlist is the safety net: when radar-suite adds new yaml files in future versions, the skill defaults to ignoring them rather than mis-importing them.

For **other known formats** (`.eslint-todos`, etc.), parse the structured fields (`status`, `urgency`, `severity`, `file:line`) directly so Phase 4 auto-fill can populate columns from real signals.

For **unknown audit formats**, fall back to filename-based heuristics and flag the rows as needing manual review.

**Cross-surface deduplication:** before producing the candidate report, run a fuzzy-match dedup pass. If the same item appears in Deferred.md AND a plan file AND a memory file (common, e.g., a paused migration shows up in all three), merge into ONE candidate row with the multi-source pointer recorded in the Finding cell. Without this step, the survey produces 3x duplicate rows for the same logical item.

**GitHub issues, four states, not two:**
- `gh` not installed: "GitHub issues skipped (`gh` CLI not available)"
- `gh` installed but `gh auth status` fails: "GitHub issues skipped (`gh` not authenticated; run `gh auth login` to enable)"
- `gh` available but project is not on GitHub: "GitHub issues skipped (project not on GitHub)". Detection runs before invoking `gh`. Conditions: `git rev-parse --git-dir` succeeds AND `git remote get-url origin 2>/dev/null` returns a URL containing `github.com`. If either check fails (no `.git/` directory, missing `origin` remote, or `origin` points at GitLab / Bitbucket / a self-hosted Git server), surface this fourth state and skip the `gh` invocation entirely.
- `gh` authed and project is on GitHub but `gh issue list` returns empty: "GitHub issues: 0 open issues with deferral labels found"

The spec must distinguish these so the user knows whether the surface is silent because empty or silent because broken. The fourth state matters because invoking `gh issue list` against a non-GitHub repo prints a confusing error rather than a clean "skipped" status.

Output of Phase 2 is a candidate report. Example (numbers will vary; treat as illustrative, not as expected counts):

```
Found N candidate deferred items across 6 surfaces:

📁 Deferred-named files (2 active, 3 archive paths skipped)
  • Deferred.md (~22 active rows after stripping RESOLVED entries)
  • BACKLOG.md (3 items)

📋 Audit ledgers (1 active, 3 archive ledgers skipped)
  • .radar-suite/ledger.yaml: 17 fixed, 1 deferred (RS-019), 1 accepted (RS-011)

📂 Plan files (project-local: 0; global ~/.claude/plans/ NOT scanned by default)
  • Run /unforget import --plans=global to scan ~/.claude/plans/. Typically noisy. Prefer to keep paused-plan rows in Section 1 captured directly via Phase 5 user-add.

💬 Code comments (variable, typically 0 to 50)
  • Word-boundary regex: // (TODO|FIXME|HACK|XXX|MIGRATION-NOTE|DEFERRED)\b
  • Default skip. Most TODOs are noise; user can opt in via /unforget import --comments

📝 Memory files (filename match)
  • project_v2_v3_migration_diagnostic_apr30.md
  • project_deferred_worker_hygiene.md
  • deferred_test_suite_failures_apr30.md

🐙 GitHub issues: depends on `gh` state (see "four states" rule above)

🔁 Cross-surface dedup: K candidates merged from M raw matches.
```

**Empty-case branch:** if ALL surfaces return zero candidates (common in minimal projects: single-skill repos, fresh greenfield codebases, small libraries), skip Phase 3 (no triage needed) and Phase 4 (nothing to auto-fill) entirely. Jump directly to Phase 5 with a different framing message:

> "No existing deferral artifacts found. That's fine. Most projects start UNFORGET.md from the user's tacit knowledge anyway. Let's go straight to capturing what's in your head."

The empty case is a feature, not a failure. Many users will adopt unforget at greenfield project start; the spec must handle that gracefully without producing a confusing "0 candidates, proceed?" prompt that has no actionable next step.

### Phase 3: Triage (per-surface yes/no/skip)

For each surface that returned candidates, ask the user a single question:

- **High-confidence surfaces** (Deferred-named files, audit ledgers, memory files): "Import all N rows from `<source>`?" Default yes.
- **Medium-confidence surfaces** (plan files): "Review N plan files one-by-one?" Default yes. For each plan, offer import / skip / "uncertain, mark as needs-review".
- **Low-confidence surfaces** (code comments): "Skim 24 code comments now?" Default skip. Most TODOs are noise; the user can run `/unforget import --comments` later if desired.

The user can skip any surface entirely. Nothing is forced.

### Phase 4: Auto-fill defaults from source signals

For each row that the user agreed to import, the skill auto-fills as many of the 10 columns as it can infer.

**Format-aware mapping** is preferred over prose-based heuristics. When the source has a structured format (radar-suite YAML ledgers with explicit `status`/`urgency`/`severity` fields; ESLint-disable directives with rule names; etc.), parse the structured fields directly. Fall back to prose heuristics only when the source is unstructured (plain markdown, code comments).

| Column | Inferred from |
|---|---|
| **#** | Auto-assigned next ID per section (P1, P2, ...) |
| **Target / Window** | Map "release-blocker" / "must-fix" / explicit `target: THIS` to 🚢 THIS. "Post-release" / `target: NEXT` to 🚢+1 NEXT. "Future" / no tag to 🌫️ SOMEDAY. |
| **Finding** | Title or first line of source. Truncate at ~150 chars; full detail stays in source file (linked from the row). |
| **Urgency** | Structured format: pass through `urgency` / `severity` field. Prose: CRITICAL/HIGH/MEDIUM/LOW pass through; ERROR/WARNING/INFO map to HIGH/MEDIUM/LOW. No tag becomes ⚪ LOW. |
| **Risk: Fix** | Default ⚪ Low. Needs human judgment. The skill shouldn't guess. |
| **Risk: No Fix** | If source mentions "data loss", "crash", "user-visible", set to 🟡 High. Default ⚪ Low. |
| **ROI** | Default 🟢 Good. |
| **Blast Radius** | If source has structured `files:` list, count and map. If prose mentions file count, map. "Many files" becomes 🟡 6-15 files. Default ⚪ 1 file. |
| **Fix Effort** | Map source size estimates ("4-6 hours" to Medium, "trivial" to Trivial, "large refactor" to Large). Default Small. |
| **Status** | Open by default. "RESOLVED" / "FIXED" / "DONE" / structured `status: fixed` becomes Fixed (auto-archive; see Phase 7). "In progress" / structured `status: in_progress` becomes In Progress. Structured `status: deferred` becomes Deferred. Structured `status: accepted` becomes Skipped. |
| **Section** | Per-source mapping: Deferred-named files to Section 1 (Paused plans). Plan files to Section 1. Audit ledgers to Section 3 (Audit findings). Memory files to Section 1 (if filename starts `project_deferred_`) or Section 2 (if filename starts `deferred_` and content is session-spillover-shaped). Code comments to Section 4 (User-reported). GitHub issues to Section 1 if labeled `paused`/`blocked`, Section 4 otherwise. |

The skill is honest about not getting this perfect. Most cells will be defaults; the user upgrades them as they go via `/unforget edit`.

**Conservative defaults (when no signal is present):** when a source provides no signal for a column, the skill must use exactly these values rather than guessing. Pinning these values in the spec keeps behavior consistent across versions and across implementations.

| Column | Conservative default | Override condition |
|---|---|---|
| **Target / Window** | `🌫️ SOMEDAY` | Source explicitly says "release-blocker" / `target: THIS` / similar. Never auto-promote to THIS without an explicit signal. |
| **Urgency** | `🟢 MEDIUM` | Source explicitly says CRITICAL / HIGH / LOW. Treat ERROR as HIGH, WARNING as MEDIUM, INFO as LOW. |
| **Risk: Fix** | `⚪ Low` | No automatic override. Risk: Fix needs human judgment; the skill never guesses higher than Low. |
| **Risk: No Fix** | `⚪ Low` | Source body contains "data loss", "crash", "user-visible", "corruption", or "security" — promote to `🟡 High`. |
| **ROI** | `🟢 Good` | No automatic override. The user upgrades to `🟠 Excellent` or downgrades to `🟡 Marginal` / `🔴 Poor` via `/unforget edit`. |
| **Blast Radius** | `⚪ 1 file` | Source has a structured `files:` list — count and map (1 → ⚪, 2-5 → 🟢, 6-15 → 🟡, >15 → 🔴). Prose "many files" → 🟡 6-15 files. |
| **Fix Effort** | `Small` | Source explicitly says "trivial" / "4-6 hours" / "large refactor" — map accordingly. Default Small (not Medium) keeps the bar for promoting effort intentionally low. |
| **Status** | `Open` | Source explicitly says "RESOLVED" / "FIXED" / "DONE" / `status: fixed` → Fixed. `status: in_progress` → In Progress. `status: deferred` → Deferred. `status: accepted` → Skipped. |

These defaults are the contract: a row imported with no signal looks identical regardless of which surface produced it. The user's first pass after init is to upgrade the rows that matter; the defaults are the floor, not the ceiling.

### Phase 5: User-add pass (the most important phase)

The survey can't find items that exist only in the user's head, in a Slack DM, in a personal notes app, or in tacit knowledge from past sessions. After Phase 4, the skill explicitly invites the user to surface these.

**The opening sentence and prompt list both branch on context.**

**If Phase 2 found rows** (N > 0):
> "Survey complete. N rows queued for import. Anything else you want to add before I write UNFORGET.md?"

**If Phase 2 found nothing** (empty-case from Phase 2):
> "Let's start the brain dump. What deferred work is in your head right now?"

**The prompt list adapts to project type** (inferred from the cadence preset chosen in Phase 1):

**For user-facing applications** (Standard preset, mobile/desktop apps):
> Common things the survey can't find:
> - Bugs you've noticed but haven't logged anywhere
> - Friction you've felt while using the app
> - Items mentioned in Slack DMs, notes apps, or paper notebooks
> - Things you remember from past sessions that aren't in any file
> - "I should really fix that someday" thoughts you've had

**For services / web apps** (Continuous preset):
> Common things the survey can't find:
> - Edge cases you've seen in logs but haven't reproduced
> - Performance issues you've felt but haven't measured
> - Tech debt items mentioned in PR review but not filed
> - Monitoring / alerting gaps you've noticed
> - Configuration drift between staging and prod

**For libraries / tools / skills** (Lean preset, or Continuous on a non-app project):
> Common things the survey can't find:
> - Edge cases you've seen but didn't handle
> - Tests you skipped or muted
> - Documentation gaps you've noticed
> - Behavior that feels off but you couldn't pin down
> - Breaking changes you've been delaying
> - "I should refactor that" notes that never made it to a file

In all cases, the closing line is the same:

> "Add items one at a time. Type 'done' when finished, or 'skip' to proceed without adding any."

For each item the user types, the skill:

1. **Picks a section automatically** based on phrasing (bug language to Section 4; "I started ... but didn't finish" to Section 1; everything else to Section 2). User can override.
2. **Auto-assigns the next ID** in that section.
3. **Sets conservative defaults** for the 10 columns (Target = 🌫️ SOMEDAY, Urgency = ⚪ LOW, etc.).
4. **Echoes** the captured row and moves to the next item.

The user is rattling off items, not filling out forms. Triage refinement happens later via `/unforget edit`. Speed matters more than completeness here. Every item captured is one less item lost.

This phase typically catches 5 to 15 rows on a real project's first init. They're often the highest-value rows in the eventual file because no other surface contains them.

### Phase 6: Deep-dump pass (optional, default skip)

For users who want to do a thorough deferral audit at adoption time:

> "Want to do a deeper deferral inventory? I can ask you 8 to 10 questions to surface items you might not remember on first pass. Takes 5 to 10 minutes. [yes / no / maybe later]"

If yes, the skill walks through prompts like:

- "Are there features in your app that 'mostly work but ___'?"
- "Are there parts of the codebase you avoid touching? Why?"
- "Are there bugs you've seen but couldn't reproduce reliably?"
- "Are there user requests you didn't reject but also didn't schedule?"
- "Are there workarounds you've put in place that should be replaced with proper fixes?"
- "Are there third-party dependencies you'd like to remove or replace?"
- "Are there tests you've muted or skipped that you want to fix later?"
- "Are there docs that are out of date or missing entirely?"

Each prompt that surfaces an item gets captured as a row (same flow as Phase 5: section auto-pick, conservative defaults, fast capture).

Most users skip Phase 6 the first time and run it later when they have more time. That's fine. `/unforget import --deep` makes Phase 6 re-runnable on demand.

### Phase 7: Diff preview, write file, wire recall

Before any file is written, show the user a summary diff. **Empty sections collapse to a single line** so the preview stays readable on minimal projects.

**Populated case (most sections have rows):**
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

**Minimal case (most sections empty, common on greenfield or single-purpose repos):**
```
About to create UNFORGET.md at <path> with:

  Section 2 (Session spillover): 3 rows from Phase 5 user-add
  (Sections 1, 3, 4 will be created with headers but no rows yet.)

Total: 3 rows imported.

Proceed? [yes / preview the rows / cancel]
```

The collapsed form removes noise on minimal projects where most sections are empty. Each section header still gets written to UNFORGET.md so future `/unforget add` calls have a place to land. The preview just doesn't enumerate each empty section.

User can preview the rows before committing. If they cancel, no files are touched. If they proceed:

1. **Write UNFORGET.md** with all imported rows in their assigned sections.
2. **Move RESOLVED / FIXED items** to a separate archive file (`UNFORGET-archive-<date>.md` in the same directory).
3. **Optionally rename / replace the source files**: e.g., replace root `Deferred.md` with a redirect pointer to UNFORGET.md (preserving git history). Always ask before modifying any source file.
4. **Wire CLAUDE.md / AGENTS.md** with the Deferred Work Index section (if user agreed in Phase 1).
5. **Print a final summary** with the row count, the path, the next-step suggestion ("run `/unforget list --target=THIS` to see release blockers").

### Success criteria for `/unforget init`

After init runs:

- UNFORGET.md exists at the chosen path with rows imported from existing surfaces and items captured from the user's memory.
- Source files (Deferred.md, ledgers, etc.) are either archived or replaced with redirects, never silently deleted.
- CLAUDE.md / AGENTS.md has a Deferred Work Index section so future AI sessions auto-recall UNFORGET.md.
- The user can run `/unforget list --target=THIS` and see exactly what's blocking the next release, in one screen.

---

## /unforget edit

Refine a row's columns after import. Most useful immediately after `/unforget init` to upgrade auto-filled defaults.

### Usage

```
/unforget edit P3                       ·  open row P3 for editing
/unforget edit P3 --target=THIS          ·  change just the Target cell
/unforget edit P3 --status=Fixed         ·  mark Fixed (next promotion will archive)
/unforget edit S5 --urgency=HIGH --roi=Excellent
```

### Steps

1. Find the row by ID. Show its current 10 columns.
2. Prompt for which cells to update (or accept flag overrides if passed inline).
3. Show the diff (old value to new value for each changed cell).
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
/unforget import                         ·  re-run the standard survey (Phases 2 to 4 + 7)
/unforget import --comments              ·  include code comments (skipped by default)
/unforget import --deep                  ·  run the Phase 6 deep-dump questions
/unforget import --source=<path>         ·  survey a specific file or directory only
```

### Steps

Same as `/unforget init` Phases 2 to 4 and Phase 7, but operates against an EXISTING UNFORGET.md:

- New rows get appended with auto-assigned IDs (continuing the per-section sequence).
- Duplicate detection: if a survey row matches an existing UNFORGET.md row by similarity (fuzzy match on Finding text + source pointer), the skill flags it and asks whether to skip or import as a separate row.
- The Phase 7 diff preview shows what's NEW, not the full file state.

`/unforget import` is the second-most-important command after `/unforget add`. It's how the skill stays current with the project's evolving deferral surfaces.

---

## /unforget add

Capture a new deferral. The friction point that makes or breaks the skill. Must be fast.

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

- `--paused` routes to Section 1 (Paused plans). Triggers an extra prompt for the detail-file pointer.
- `--audit` routes to Section 3 (Audit findings). Asks for the originating audit tool and finding ID.
- `--observed` routes to Section 4 (User-reported / observed).
- `--target=THIS|NEXT|LATER|SOMEDAY` sets Target without prompting.
- `--urgent` is shorthand for `--target=THIS --urgency=HIGH`.

### Speed target

30 seconds or less, end-to-end, for default usage. If the skill ever takes longer than 30 seconds to capture an item, it has failed at its core promise.

---

## /unforget list

Show current state. Default view is sorted by Target (🚢 THIS first), then Urgency (CRITICAL first).

### Usage

```
/unforget list                        ·  full table
/unforget list --target=THIS          ·  only ship-blockers
/unforget list --section=audit        ·  only Section 3
/unforget list --status=Open          ·  exclude Fixed/Skipped
/unforget list --stale                ·  only rows past their staleness threshold
/unforget list --age=30+              ·  only rows older than 30 days
```

### Output format

The skill renders the matching rows in the same 10-column format as UNFORGET.md, with a one-line summary at the top:

> "12 rows total: 2 🚢 THIS (release blockers), 5 🚢+1 NEXT, 5 🌫️ SOMEDAY. Stale: 1."

For the simplest case (`/unforget list` alone), this is the answer the user was actually looking for when they asked "what's deferred?"

---

## /unforget scan

Identify rows past their staleness threshold. Read-only. Never modifies the file.

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

---

## /unforget promote

Release-time ritual. Run at every release submission.

### Steps

1. **Verify** every `🚢 THIS` row has Status = Fixed. List any that don't and require an explicit demotion or fix.
2. **Promote** all `🚢+1 NEXT` rows to `🚢 THIS` (they are now the next release's blockers).
3. **Re-triage** all `🚢+2 LATER` rows that are still relevant to `🚢+1 NEXT`. Items no longer relevant get archived.
4. **Re-rank `🌫️ SOMEDAY`** items 180 days or older: prompt user for promote / demote / archive.
5. **Stamp** the "Last promoted" line at the top of UNFORGET.md with new build/version + date.

This command DOES modify UNFORGET.md (unlike `/unforget scan`), so the user is shown a preview of every change before it's applied.

### Dry-run mode

`/unforget promote --dry-run` runs the same steps above but writes nothing. The skill renders the would-apply changes as a markdown diff inline in the Claude Code conversation. Each row that would be promoted, demoted, archived, re-stamped, or re-triaged appears as a before/after diff block.

To apply the same changes after reviewing the dry-run output, the user replies `apply` (or any explicit confirmation). The skill then re-runs `/unforget promote` without the `--dry-run` flag, picks up the same set of changes, creates the auto-backup (see "Backups and recovery" below), and writes the file.

To abandon the changes, the user replies `cancel` or anything else that is not an explicit confirmation. The skill exits without touching UNFORGET.md.

`--dry-run` does not create a backup file. Backups are only written by the real `promote`, on the path that actually modifies UNFORGET.md.

---

## How to use unforget alongside CLAUDE.md / AGENTS.md

The skill works best when the project's main AI instructions file has a section that points at UNFORGET.md as the canonical deferral source. `/unforget init` offers to add this for you. Example block:

```markdown
## Deferred Work Index

**Single source of truth:** `Documentation/Development/Deferred/UNFORGET.md`

Read this file when:
- The user asks "what's deferred?", "what's the backlog?", "prioritize my plans," or any variant.
- Before suggesting a release / submission, to check 🚢 THIS rows for unresolved blockers.
- When a task in the current session needs to be deferred, log a row here. Do NOT create a new tracking file unless the entry needs detail beyond one row.

**Format:** 10-column rating table per section. **Sections:** Paused plans / Session spillover / Audit findings / User-reported.

**Target column** is the release-cycle commitment: 🚢 THIS / 🚢+1 NEXT / 🚢+2 LATER / 🌫️ SOMEDAY.

Never log deferred items elsewhere. Memory files, plan files, and audit ledgers are detail stores; UNFORGET.md is the index.
```

This block is what makes the skill's recall trigger work. Without it, future AI sessions don't know to read UNFORGET.md when the user asks about deferred work.

---

## Anti-patterns

Things this skill deliberately does NOT do, and why:

- **Custom column reordering.** Breaks comparability across projects.
- **Custom rating scales.** Letting one user use 🔴/🟡/🟢/⚪ and another use P0/P1/P2/P3 makes the format un-shareable.
- **Per-row column visibility.** Hiding columns on some rows but not others. Devolves into chaos.
- **Renaming core columns.** "Call Urgency 'Priority' instead." Skill becomes incompatible with itself.
- **Multiple files.** UNFORGET.md is the index. Detail files (per-plan markdown) are linked FROM rows, not duplicates of them.
- **Auto-deferring things the AI thinks should be deferred.** Deferral is a user decision. The skill captures, organizes, and surfaces; it doesn't decide on the user's behalf.

---

## Backups and recovery

Every `/unforget promote` (without `--dry-run`) writes a timestamped backup of the current UNFORGET.md before applying changes. Backups make destructive operations safe to refine: if a promote produces unexpected output, the previous file is one rename away.

### Naming

Backups land in the same directory as UNFORGET.md, named `UNFORGET.md.bak-YYYY-MM-DD-HHMMSS`. The timestamp uses local time. Example: `UNFORGET.md.bak-2026-05-02-143027`.

### Retention

The skill keeps the 5 most recent backups. During each `promote`, backups older than the 5 most recent are pruned silently. The retention count is fixed in v0.2 and is not user-configurable.

If a user wants to preserve a specific backup beyond the 5-deep window, they should rename it to remove the `.bak-` infix (for example, `UNFORGET.md.bak-2026-05-02-143027` to `UNFORGET-pre-build33.md`). Renamed files are no longer recognized as backups and will not be pruned.

### `.gitignore` recommendation

Backup files are local recovery artifacts, not project history, and should not be committed. The recommended `.gitignore` line is:

```
UNFORGET.md.bak-*
```

The init flow can offer to add this entry when the project is first wired up.

### Recovering from a broken UNFORGET.md

If UNFORGET.md becomes unparseable (manual edit error, merge conflict left in place, mistaken structural change), the user has two paths:

1. Rename the most recent backup back to `UNFORGET.md`, replacing the broken file. This restores the state from before the most recent `promote`.
2. Follow the "Recovering a broken UNFORGET.md" section in the project's `README.md`, which covers manual repair when no backup is available.

Path 1 is fastest when the break happened during or after the most recent `promote`. Path 2 is the fallback when the break predates the oldest retained backup.

`--dry-run` mode never creates a backup, so dry-runs cannot be used as an explicit checkpoint. Use the inline diff output of `--dry-run` for review; rely on the auto-backup written by the real `promote` for rollback.

---

## Compatibility notes

- **Non-Claude-Code use:** UNFORGET.md is plain markdown. The format works fine in any editor, on GitHub, in Linear, etc. The slash commands require Claude Code, but the file itself is portable.
- **Multi-user / team use:** UNFORGET.md commits to git like any other markdown. Concurrent edits use standard merge resolution. Status changes between Open / In Progress / Fixed should be done atomically per row to minimize merge churn.
- **Other AI assistants:** The "Deferred Work Index" block in CLAUDE.md / AGENTS.md works for any AI that reads project instructions. Cursor, Copilot, Aider, etc. can all benefit from the recall trigger pattern.
- **CI integration:** `/unforget scan` output is structured markdown. A simple GitHub Action can run the scan weekly and post the report to a Slack channel or open an issue.
- **Format-version compatibility:** every read operation (`add`, `list`, `promote`, `scan`, `edit`, `import`) checks for an HTML comment marker of the form `<!-- unforget-format: vN -->` near the top of UNFORGET.md. The marker declares which version of the unforget file format the file conforms to. v0.2 of the skill supports format `v1`. Three cases:
  - **Marker absent.** The skill prompts: "this file may not be in unforget format; proceed anyway?" Default response is no. If the user proceeds, the skill operates as best it can without format guarantees, and recommends adding `<!-- unforget-format: v1 -->` near the top of the file to silence the prompt on future reads.
  - **Marker recognized (`v1`).** The skill proceeds normally.
  - **Marker is a future version (`v2` or higher when the skill is v0.2).** The skill prints: "this file declares unforget format vN, but this skill version supports up to v1. Operating in read-only mode; writes are refused." Read-only operations (`list`, `scan`, and `promote --dry-run`) still work. Write operations (`add`, `edit`, `import`, and `promote` without `--dry-run`) refuse with a one-line error pointing to the version mismatch and recommending a skill upgrade.

---

## License

Apache License 2.0. See LICENSE.
