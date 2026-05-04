# unforget — `/unforget init` reference

This file holds the seven-phase init walkthrough. Read it only on `/unforget init` (or when planning init's behavior).

For the surface-survey detail (six surfaces + Surface 1b general doc scanning + redirect-pointer / meta-doc / path-encoding rules) referenced by Phase 2 below, see `reference/surfaces.md`.

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

Scan the project for existing deferred-work artifacts across six tractable surfaces, plus Surface 1b for general documentation. NOTHING is imported yet; this phase only produces a candidate list.

**Full surface specification — six core surfaces, Surface 1b doc-scanning heuristics, redirect-pointer pre-check, memory-dir resolution, path encoding, meta-file pre-check, audit-tool format-aware parsing, cross-surface deduplication, GitHub-issues four states, and the empty-case branch — lives in `reference/surfaces.md`.** Read that file before implementing or modifying Phase 2 behavior.

**Preferred implementation:** delegate the scan to the helper script:

```
python3 scripts/scan_surfaces.py --root <path>
```

The script returns a JSON candidate list grouped by surface. The skill orchestrates Phase 3 (triage) and Phase 4 (auto-fill) against that JSON. If Python is unavailable, see `reference/surfaces.md` § Algorithm fallback for the prose algorithm the LLM can re-derive.

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

🐙 GitHub issues: depends on `gh` state (see "four states" rule in surfaces.md)

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
| **Target / Window** | Map "release-blocker" / "must-fix" / explicit `target: THIS` to 🔴 THIS. "Post-release" / `target: NEXT` to 🔵 NEXT. "Future" / no tag to ⚪ SOMEDAY. |
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
| **Target / Window** | `⚪ SOMEDAY` | Source explicitly says "release-blocker" / `target: THIS` / similar. Never auto-promote to THIS without an explicit signal. |
| **Urgency** | `🟢 MEDIUM` | Source explicitly says CRITICAL / HIGH / LOW. Treat ERROR as HIGH, WARNING as MEDIUM, INFO as LOW. |
| **Risk: Fix** | `⚪ Low` | No automatic override. Risk: Fix needs human judgment; the skill never guesses higher than Low. |
| **Risk: No Fix** | `⚪ Low` | Promote to `🟡 High` when the source body contains "data loss", "crash", "user-visible", "corruption", or "security". |
| **ROI** | `🟢 Good` | No automatic override. The user upgrades to `🟠 Excellent` or downgrades to `🟡 Marginal` / `🔴 Poor` via `/unforget edit`. |
| **Blast Radius** | `⚪ 1 file` | If the source has a structured `files:` list, count and map (1 → ⚪, 2-5 → 🟢, 6-15 → 🟡, >15 → 🔴). Prose "many files" maps to 🟡 6-15 files. |
| **Fix Effort** | `Small` | When the source explicitly says "trivial" / "4-6 hours" / "large refactor", map accordingly. Default Small (not Medium) keeps the bar for promoting effort intentionally low. |
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
3. **Sets conservative defaults** for the 10 columns (Target = ⚪ SOMEDAY, Urgency = ⚪ LOW, etc.).
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
