# unforget — Subcommand reference

This file holds the per-subcommand specs for everything except `/unforget init` (see `reference/init.md`) and `/unforget promote` (see `reference/promotion.md`). Read it on any specific subcommand listed below.

Subcommands here:
- `/unforget add` — capture a new deferral
- `/unforget edit` — refine a row's columns
- `/unforget import` — re-run the surface survey after init
- `/unforget list` — show current state, filterable
- `/unforget scan` — identify rows past their staleness threshold
- `/unforget archive` — move completed rows out of the active tables (lightweight; distinct from the release-time `promote` in `reference/promotion.md`)
- `/unforget --version` — install-verification health check

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
   - Target: `⚪ SOMEDAY` (most conservative; user can promote later)
   - Urgency: `⚪ LOW`
   - Risk: Fix / Risk: No Fix: `⚪ Low`
   - ROI: `🟢 Good`
   - Blast Radius: `⚪ 1 file`
   - Fix Effort: `Small`
   - Status: `Open`
4. **Ask the user to override any defaults** (single AskUserQuestion with all relevant fields, or accept the defaults to skip ahead).
5. **Append the row** to the chosen section.
6. **Echo back** the new row ID and a one-line confirmation.
7. **Archive nudge (non-blocking):** count Fixed/Done rows in the active tables; if 5 or more, append the one-line archive nudge (see `/unforget archive` § The archive nudge). Never let it add latency or a prompt — the 30s speed target wins.

### Subsection flags (optional)

- `--paused` routes to Section 1 (Paused plans). Triggers an extra prompt for the detail-file pointer.
- `--audit` routes to Section 3 (Audit findings). Asks for the originating audit tool and finding ID.
- `--observed` routes to Section 4 (User-reported / observed).
- `--target=THIS|NEXT|LATER|SOMEDAY` sets Target without prompting.
- `--urgent` is shorthand for `--target=THIS --urgency=HIGH`.

### Speed target

30 seconds or less, end-to-end, for default usage. If the skill ever takes longer than 30 seconds to capture an item, it has failed at its core promise.

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

### Closure recommendation prose (when marking a row Fixed)

When `/unforget edit <ID> --status=Fixed` runs against a row whose closure narrative is non-trivial (the new detail block exceeds ~50 chars and is not a Skipped/Deferred entry), emit a structured "Suggested next steps" block immediately after confirming the status change:

```
Row <ID> closed.

Suggested next steps (the post-fix sweep — see reference/promotion.md):

  1. Verify the closure is real. Stale Open ledger entries are common when
     a fix was shipped without updating the ledger.
       /radar-suite focus on <symbol-from-closure>
       (install: https://github.com/Terryc21/radar-suite)

  2. Generalize the fix to find unfired echoes elsewhere in the codebase.
     Extract the anti-pattern in one sentence, then run:
       /bug-echo "<your one-sentence pattern>"
       (install: https://github.com/Terryc21/bug-echo)

  Skip if: the fix was localized (typo, single-character bug, isolated state).
  Worth doing when: the fix touched architecture, types, or a shared pattern.
```

**Detect-then-recommend logic:** before printing each `(install: ...)` URL, check whether the recommended skill is already installed. The skill is considered installed if any of these are true:

- A directory matching `~/.claude/skills/<skill-name>/` exists (single-skill plugin layout)
- A directory matching `~/.claude/skills/<skill-name>/skills/<skill-name>/` exists (suite layout — radar-suite uses this)
- A `<skill-name>` entry appears in the project's plugin manifest (if Claude Code exposes one)

If the skill is detected as installed, omit the `(install: ...)` line. The user sees a clean two-step prompt; they don't need to be told where to get something they already have. If detection is uncertain (filesystem access failed, plugin manifest unavailable), include the install URL as a fallback — it's better to over-inform than under-inform.

**Version pinning (fail-soft).** The recommendation hardcodes the command surfaces `/radar-suite focus on <symbol>` and `/bug-echo "<pattern>"`. Both are owned by external skills whose CLI may evolve. Pin minimum-supported versions and emit a fail-soft warning when the installed version is older:

| Skill | Minimum supported | If installed and < min |
|---|---|---|
| `radar-suite` | 3.0 | Append after the suggested command: `(installed v<X>; recommended command may have changed in v3.0+. See https://github.com/Terryc21/radar-suite for the current surface.)` |
| `bug-echo` | 1.0 | Same pattern. |

Detection: read the skill's `SKILL.md` frontmatter `version:` field at recommendation time. If the field is missing or unparseable, treat as unknown and fall through to the install URL (don't suppress, don't warn — uncertain detection should over-inform per the rule above). When the version is pinned in a v0.3+ release, bump the minimums in the table without changing the recommendation copy itself.

**When to suppress the prose entirely:**
- Status change was Open → Skipped or Open → Deferred (the row isn't actually fixed)
- Status change was Fixed → Fixed (no-op)
- The closure narrative is too short to suggest a meaningful pattern (under 50 chars or unchanged from the prior detail block)
- The row is in Section 2 (Session spillover) and represents a non-code observation (skill/process improvement)

**Once-per-project gate (the cross-promo marker).** Even when all the above filters pass, suppress the "Suggested next steps" block on every closure after the first. Repeated unsolicited cross-skill pitches in a tool the user installed expecting respect are a fast way to erode trust; once is helpful, twice is friction, ten times is noise.

The mechanism: the first time the recommendation fires for a given UNFORGET.md, write an HTML-comment marker near the top of the file:

```
<!-- unforget-cross-promo-shown: YYYY-MM-DD -->
```

On every subsequent closure, check for the marker. If present, suppress the "Suggested next steps" block silently — the user already saw it and either acted on it or didn't. If absent, emit the block and write the marker as part of the same edit.

**Re-show conditions.** The marker can be reset in two ways:
- **User opts in explicitly:** `/unforget edit <ID> --status=Fixed --sweep` forces the block to render even if the marker is present, useful when the user wants the prompt for a particular non-trivial closure.
- **Cooldown:** if the marker date is more than 90 days old, treat it as expired and re-show the block once. The expectation is that adopters who close one row every few months will benefit from a refresher; adopters who close many rows in a week will not.

**Marker placement.** Write the marker on a dedicated line just under the existing `<!-- unforget-format: vN -->` marker (or at line 1 if no format marker exists). Both markers are HTML comments, so they render invisibly in any markdown viewer.

For any row that does receive the prose, the recommendation is informational, not blocking. The user can ignore it and move on.

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

Same as `/unforget init` Phases 2 to 4 and Phase 7 (see `reference/init.md` and `reference/surfaces.md` for the full surface specification), but operates against an EXISTING UNFORGET.md:

- New rows get appended with auto-assigned IDs (continuing the per-section sequence).
- Duplicate detection: if a survey row matches an existing UNFORGET.md row by similarity (fuzzy match on Finding text + source pointer), the skill flags it and asks whether to skip or import as a separate row.
- **Memory-dir pin maintenance:** the survey emits `pin_action` for Surface 6 (memory files). When `pin_action.action` is `write` (no pin present), patch `<!-- unforget-config: memory-dir=<encoded> -->` into UNFORGET.md directly under the `<!-- unforget-format: vN -->` marker as part of the same import write. When `pin_action.action` is `rewrite` (pin exists but resolved to a different encoded path), replace the existing marker line with the new value. When `pin_action.action` is `none`, leave the file alone. See `reference/surfaces.md` § Memory-dir config pin (post-resolution).
- The Phase 7 diff preview shows what's NEW, not the full file state.

`/unforget import` is the second-most-important command after `/unforget add`. It's how the skill stays current with the project's evolving deferral surfaces.

---

## /unforget list

Show current state. Default view is sorted by Target (🔴 THIS first), then Urgency (CRITICAL first).

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

> "12 rows total: 2 🔴 THIS (release blockers), 5 🔵 NEXT, 5 ⚪ SOMEDAY. Stale: 1."

For the simplest case (`/unforget list` alone), this is the answer the user was actually looking for when they asked "what's deferred?"

**Archive nudge:** after the list output, if 5 or more Fixed/Done rows are sitting in the active tables, append the one-line archive nudge (see `/unforget archive` § The archive nudge). This is the moment the user is already looking at the ledger, so it is where accumulated-completed-row clutter is most usefully surfaced.

### Terminal-aware rendering

The full 10-column table is wide (typically 200+ characters with emoji-width quirks). On narrow terminals it wraps or renders as vertical blocks instead of horizontal rows. To stay readable:

- **Detect terminal width** at render time (`stty size` / `tput cols` / `os.get_terminal_size()`).
- **At ≥120 columns:** render the full 10-column Standard table (or whichever preset the file uses).
- **At <120 columns:** auto-fall-back to a 6-column compact projection: `# / Target / Finding / Urgency / Status` plus one user-chosen extra column (default `Effort`). This is the same shape as the **Lean** preset, reused for display only.
- **The on-disk file format never changes.** Compact rendering is presentation-only; UNFORGET.md still holds all 10 columns. Scrolling output back to a wider terminal restores the full view.

The user can override the auto-detection:

```
/unforget list --wide             ·  force the full table even at <120 cols (will wrap)
/unforget list --compact          ·  force the 6-column projection even at >=120 cols
/unforget list --extra=ROI        ·  pick a different sixth column for the compact projection
```

The auto-fallback is silent (no banner, no warning); the override flags are for power users who know what shape they want. Compact rendering eliminates the "Terminal width" warning callouts that adopters write into their own UNFORGET.md headers today.

---

## /unforget scan

Identify rows past their staleness threshold. Read-only. Never modifies the file.

### Staleness thresholds (default)

| Status / Target | Stale after |
|---|---|
| Status = Open or In Progress | 30 days |
| Status = Deferred AND Target = 🔵 NEXT | 90 days |
| Status = Deferred AND Target = 🟡 LATER | 180 days |
| Status = Deferred AND Target = ⚪ SOMEDAY | 365 days |
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

## /unforget archive

Move completed rows out of the active tables into a dated archive file. **Lightweight and safe to run anytime** — this is the everyday cleanup command, distinct from the heavyweight release-time `/unforget promote` ritual (see `reference/promotion.md`). `promote` re-triages the whole release cycle (verify THIS, roll NEXT→THIS, re-rank SOMEDAY, stamp the release line); `archive` does only the one job of clearing finished work out of view.

### Why this exists

`promote` was historically the only command that removed completed rows, but it is a release-submission ritual the user has to remember to invoke. In practice ledgers accumulate dozens of ✅ Done rows that were never cleared because nobody runs `promote` between releases — the single most common way an UNFORGET.md rots. `archive` is the low-friction alternative: one job, no release semantics, run it whenever the active tables feel cluttered. The `list` and `add` archive nudge (below) points here.

### Usage

```
/unforget archive                     ·  archive clean-Done rows (keeps "Done-but-owed" rows — see safety rule)
/unforget archive --dry-run           ·  show what WOULD be archived, write nothing
/unforget archive --all-done          ·  archive every Fixed/Done row, including "owed" ones (skip the safety hold)
```

### Safety rule (the important part): keep "Done-but-owed" rows

A row can read `✅ Done` / `Fixed` yet still carry residual work its own text signals. Archiving those hides real remaining work — the exact failure this skill exists to prevent. So by default a Done row is **held in the active tables** (not archived) when its Status or Finding text contains an owed-signal:

- `pending` / `owed` / `still owed`
- `eyeball` / `visual check` / `verify on device` / `device-verify` / `device round-trip`
- `delivery test` / `deploy owed` / `not yet deployed` / `awaiting deploy`
- `⏳` / `pending real-device`

Only a row that is Done/Fixed **and** carries no owed-signal is archived. `--all-done` overrides this hold (use when the user confirms the owed threads are moot). Rows that are `In Progress`, `Open`, `Deferred`, `Superseded`, or a self-declared "keep as marker" (e.g. a Withdrawn row whose text says to keep it) are never archived.

### Steps

1. **Read UNFORGET.md.** Identify every row whose Status is `Fixed` / `Done` (or a ✅-marked variant).
2. **Apply the owed-signal hold** (above) unless `--all-done`. Split into `archive` vs `keep (owed)`.
3. **Preview** — show the two lists (IDs + one-line title) and counts: "Archive N clean-Done rows; keep M Done-but-owed rows active." On `--dry-run`, stop here and write nothing.
4. **Confirm** with the user (single AskUserQuestion: proceed / show-full-rows / cancel).
5. **Back up first** — copy UNFORGET.md to a temp path before editing, so a mis-classification is recoverable.
6. **Write:** move the archived rows to `UNFORGET-archive.md` in the same directory as UNFORGET.md (create with a header if absent; append a dated `## Archived <date>` block if it exists). Remove those rows from the active tables. Preserve table structure — section headers and separator rows stay intact.
7. **Report** the before/after active row count and the archive-file path.

`archive` modifies UNFORGET.md, so (like `promote`) it always previews before writing. Unlike `promote`, it does not touch Target values, re-rank anything, or stamp release metadata — it only relocates finished rows. The archive file is never scanned by `init`/`import` (it lives under the archive-path exclusion rule in `reference/surfaces.md`), so archived rows do not re-enter the active backlog.

### The archive nudge (surfaced by `list` and `add`)

To make cleanup discoverable without forcing it, `/unforget list` and `/unforget add` append a one-line nudge when completed rows pile up. After their normal output, count rows whose Status is `Fixed` / `Done` in the active tables; if **5 or more**, append exactly one line:

```
💡 N completed rows are sitting in the active tables — run /unforget archive to move them out.
```

One line, non-blocking, informational — never a prompt or an action. Threshold is 5 by default; if UNFORGET.md has a `config` block at the top with `archive_nudge_threshold: N`, honor that instead (0 silences it). On `/unforget add`, skip the nudge if the add itself was slow — `add`'s 30-second speed promise wins; the nudge must never add latency or a question.

---

## /unforget --version

Print the installed skill's version, install path, format-version support, **install integrity**, and (when run in a project) the **recall-trigger status**. Useful for verifying a fresh install loaded correctly without running `init` against a real project.

### Output format

```
unforget v1.0.0
Install path: <detected at runtime>  (Claude Code plugin)
Supported format-version: v1
Subcommands: init, add, edit, import, list, scan, archive, promote, --version
Install integrity: ✓ all 10 companion files reachable
Recall trigger: ✓ installed in CLAUDE.md
```

When the install is broken or the recall trigger is missing, the last two lines carry the diagnosis instead:

```
Install integrity: ✗ 2 companion files unreachable (reference/commands.md, scripts/scan_surfaces.py)
                     → the router will fail when it delegates to a missing file; reinstall or repair the skill directory
Recall trigger: ✗ no Deferred Work Index block in this project's CLAUDE.md/AGENTS.md
                  → deferred-work questions will NOT auto-route here; run /unforget init to add it
```

The version string is read from the SKILL.md frontmatter `version` field. The install path is detected at runtime: plugin installs report the plugin directory, manual v0.1 installs report `~/.claude/skills/unforget/`. Supported format-version comes from the spec (currently `v1`; future versions will list multiple if backward compatibility is preserved).

### Install integrity

The refactored skill (v0.2+) is a thin SKILL.md router that delegates to `reference/*.md` on demand and to `scripts/*.py` for deterministic work. If those companion files did not travel with the install — a copy of only SKILL.md, a partial clone, a broken symlink — the router fails silently the first time it reads a reference file, and the failure surfaces as confusing mid-command behavior rather than a clear error.

`--version` closes that gap. **Preferred implementation:** delegate to `python3 scripts/verify_install.py --skill-root <dir> [--project-root <cwd>]` (returns JSON). It confirms every companion file the router depends on is reachable from the skill root, and — when `--project-root` is supplied — reports whether the recall trigger is installed. Report `integrity_ok` and `advisory` to the user on the two output lines above.

Algorithm fallback if Python is unavailable: for each path in the router's companion table (`reference/format.md`, `reference/init.md`, `reference/surfaces.md`, `reference/promotion.md`, `reference/commands.md`, and the five `scripts/*.py`), test existence relative to the skill root; report any that are missing.

### Recall trigger

unforget only auto-activates on "what's deferred?"-style questions when the project's `CLAUDE.md` / `AGENTS.md` carries a **Deferred Work Index** block pointing at UNFORGET.md (see `## How to use unforget alongside CLAUDE.md / AGENTS.md` in SKILL.md, and `reference/init.md` for the block itself). Without it, a populated ledger sits invisible and the skill looks broken when it is working as designed.

When `--version` runs inside a project directory, it scans `CLAUDE.md`, `.claude/CLAUDE.md`, and `AGENTS.md` for the block and reports `✓ installed in <file>` or `✗ missing` with the fix (`run /unforget init`). When run from a non-project directory (no `--project-root`), this line is omitted rather than reported as a failure.

### Behavior

- Read-only. Touches no files.
- Always succeeds as a *command* even when it reports a broken install: the integrity/recall lines are diagnostic content, not a command error. The only true non-response is the skill failing to load at all (in which case nothing prints, which is itself the signal the install did not take).
- Version, format-version, and integrity checks work from any directory. The recall-trigger line requires a project context; it is silently skipped otherwise.

After install, the user has no way to verify the skill loaded short of trying to use it. `/unforget --version` provides a no-side-effect health check. If the command does not respond, the install did not take. If it responds with the wrong version, the user knows to update before running `init` against a real project. If it responds with an integrity ✗, the user knows the companion files did not travel with the install before a single row is written.
