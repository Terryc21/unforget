# unforget — Subcommand reference

This file holds the per-subcommand specs for everything except `/unforget init` (see `reference/init.md`) and `/unforget promote` (see `reference/promotion.md`). Read it on any specific subcommand listed below.

Subcommands here:
- `/unforget add` — capture a new deferral
- `/unforget edit` — refine a row's columns
- `/unforget import` — re-run the surface survey after init
- `/unforget list` — show current state, filterable
- `/unforget scan` — identify rows past their staleness threshold
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

## /unforget --version

Print the installed skill's version, install path, and the format-version it supports. Useful for verifying a fresh install loaded correctly without running `init` against a real project.

### Output format

```
unforget v0.2.0
Install path: ~/.claude/plugins/unforget/  (Claude Code plugin)
Supported format-version: v1
Subcommands: init, add, edit, import, list, scan, promote, --version
```

The version string is read from the SKILL.md frontmatter `version` field. The install path is detected at runtime: plugin installs report the plugin directory, manual v0.1 installs report `~/.claude/skills/unforget/`. Supported format-version comes from the spec (currently `v1`; future versions will list multiple if backward compatibility is preserved).

### Behavior

- Read-only. Touches no files.
- Always succeeds (or fails to respond entirely; there is no error case).
- Does not require a project context; works from any directory.
- Does not check for an existing UNFORGET.md or scan any surface.

After install, the user has no way to verify the skill loaded short of trying to use it. `/unforget --version` provides a no-side-effect health check. If the command does not respond, the install did not take. If it responds with the wrong version, the user knows to update before running `init` against a real project.
