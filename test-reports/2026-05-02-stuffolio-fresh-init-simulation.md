# Test Report: Fresh /unforget init against Stuffolio (simulated)

**Date:** 2026-05-02
**Skill version:** v0.1 (SKILL.md only, pre-v0.2 plugin packaging)
**Method:** Manual simulation. SKILL.md read verbatim, then each phase walked against a scratch copy of Stuffolio with the live UNFORGET.md removed. Live Stuffolio repo never touched.
**Coverage:** Phase 1 (setup) + Phase 2 (surface survey) executed in detail. Phases 3-7 not executed; gaps already accumulated to a clear pattern.

---

## Why this test exists

After a few weeks of using v0.1 on Stuffolio, several user-safety gaps surfaced in the spec (header notice, format-version marker, ID stability rules, etc.). Those went into v0.2-roadmap.md. But a new question emerged: would the spec, run literally as written, actually produce a useful UNFORGET.md from Stuffolio's current state?

This test answers that question. It's a "what would a fresh adopter experience?" test, not a regression test on v0.1 features.

## Test setup

```
~/Desktop/unforget-test-2026-05-02/   ← rsync'd copy of Stuffolio working tree
                                          (excluded: .build, DerivedData, build, node_modules)
                                          (kept: Documentation, .agents, .radar-suite, .claude,
                                                 source files, all markdown)
                                          UNFORGET.md DELETED from this copy
```

Live Stuffolio at `/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio/` was untouched. Verified clean working tree before and after the test.

The simulator (this transcript) is both operator and auditor, which weakens the test's independence. Mitigated by quoting SKILL.md verbatim before each phase decision and noting where interpretation rather than literal execution was needed.

---

## Phase 1: Setup questions (3 of 3 passed)

| Question | SKILL.md spec | Result | Status |
|---|---|---|---|
| File path | "If `Documentation/` exists with subdirectories: default `Documentation/Development/Deferred/UNFORGET.md`" | Detected `Documentation/` with subdirs. Default `Documentation/Development/Deferred/UNFORGET.md` matches Stuffolio's actual location exactly. | 🟢 PASS |
| Cadence preset | Three options. Stuffolio is a discrete-release iOS/iPadOS/macOS app. | Standard preset (10 columns, Target column) is the right answer. Spec offers it. | 🟢 PASS |
| AI instructions wiring | "Scan the repo for any of these. If multiple are found, list them and let the user pick." | Detected `CLAUDE.md` + `.continue/`. Spec correctly handles multi-detection. | 🟢 PASS (T-1) |

Phase 1 worked as designed. The spec's "detect what the project actually uses and adapt" line in Q3 is real value — junior adopters won't know which AI file they're supposed to wire, and the auto-detection covers them.

## Phase 2: Surface survey (10 findings, mostly fail or partial)

Six surfaces. Findings T-2 through T-10 below.

### T-2: 🟡 HIGH — Universal exclusion rule excludes path segments but not filenames

**Where:** Phase 2, "Universal exclusion rule (applies to ALL surfaces): any path containing a segment named `archive` or `Archive` is skipped."

**What goes wrong:** Stuffolio has `Documentation/Development/Deferred/Deferred-archive-2026-05-01.md`. The path has no `archive` segment — the word "archive" is in the *filename*. A literal reading of the spec would not skip this file. It contains 22+ rows of historical deferrals from before the May 1 reorg. A fresh init would import them as fresh deferrals.

**Fix proposal:** Extend exclusion to cover filename match too. Skip files matching `*archive*.md` (case insensitive) regardless of path.

**Reproducible test case:** scratch copy of Stuffolio, file `Documentation/Development/Deferred/Deferred-archive-2026-05-01.md` exists with active-shape rows.

---

### T-3: 🟢 MEDIUM — Redirect-pointer files not detected

**Where:** Phase 2, Surface 1 (Deferred-named files).

**What goes wrong:** Stuffolio's root `Deferred.md` is a 12-line redirect pointer to `UNFORGET.md`, created when the project migrated from Deferred.md to UNFORGET.md as the canonical file. SKILL.md treats any `Deferred.md` at root as a real source. A naive run would try to parse the redirect's brief content (a heading "Deferred Work — MOVED" and a few paragraphs) as deferral entries. Either zero rows imported (best case) or 1-2 spurious rows (worst case).

**Fix proposal:** Detect short files (< 30 lines) containing pointer phrases ("MOVED", "see also", absolute or relative path references to UNFORGET.md or another deferral file). Skip with a status line: "Redirect pointer detected at `Deferred.md`; 0 items to import."

---

### T-4: 🟡 HIGH — `.radar-suite/` directory has 7 yaml files; spec only knows about `ledger.yaml`

**Where:** Phase 2, Surface 2 (Audit-tool ledgers).

**What goes wrong:** Real radar-suite v3 produces:
- `ledger.yaml` (the one SKILL.md expects)
- 5 `*-handoff.yaml` files (inter-skill state, not deferred items)
- `project.yaml` (project config)
- `session-prefs.yaml` (UI preferences)

SKILL.md says ".radar-suite/ledger.yaml" but doesn't restrict scanning to that one file. A naive "scan all yaml under `.radar-suite/`" would parse files with the wrong schema, either erroring out or producing garbage rows.

**Fix proposal:** Hardcode the file list per known audit tool. radar-suite → `ledger.yaml` only. Explicitly skip other yaml files in `.radar-suite/`.

---

### T-5: 🔴 CRITICAL — radar-suite ledger.yaml format has drifted from what SKILL.md expects

**Where:** Phase 2 + Phase 4 (format-aware mapping).

**What goes wrong:** SKILL.md says radar-suite's ledger.yaml has `status` / `urgency` / `severity` / `file:line` fields per finding. radar-suite v3's ledger.yaml has top-level `version`, `project`, `build`, `audit_mode`, `audit_started`, `prior_audit_baseline`, and `sessions[]` — where each session is an audit-run record with `timestamp`, `skill`, `new_findings`, `fixes_applied`, `overall_grade`, etc. Per-finding fields exist deeper but in a different shape than SKILL.md describes.

The "format-aware mapping" promise in Phase 4 cannot be delivered against this format. The skill would fall back to prose heuristics or import nothing.

**Fix proposal:** Either:
1. Pin radar-suite version compatibility in SKILL.md and update the format spec to match v3.
2. Use scratch reports (`scratch/*-radar-*-2026-MM-DD.md`) as the radar-suite deferral source instead of ledger.yaml. These are markdown files that DO contain per-finding text suitable for prose heuristics.
3. Both.

---

### T-6: 🟡 HIGH — `.agents/plans/` directory not in default scan paths

**Where:** Phase 2, Surface 3 (Plan files).

**What goes wrong:** Stuffolio has 4 plan files in `.agents/plans/` (radar-suite and audit plans). SKILL.md only lists `./plans/` and `./.claude/plans/`. The `.agents/` convention is used by multiple Claude-ecosystem skills. A literal scan would miss all 4.

**Fix proposal:** Add `.agents/plans/` to default scan paths. Or generalize: scan `**/plans/*.md` excluding archive and node_modules.

---

### T-7: 🟢 MEDIUM — `gh` surface fails on non-git directories; spec lists 3 states, doesn't cover 4th

**Where:** Phase 2, Surface 5 (GitHub issues).

**What goes wrong:** When scanned directory is not a git working tree (or git remote isn't GitHub), `gh issue list` fails with "fatal: not a git repository". Spec lists 3 states (gh missing / gh not authed / gh authed and empty). This 4th state isn't covered. Fresh adopters running init in a non-git directory or a self-hosted-git project would see a confusing failure.

**Fix proposal:** Add 4th state. Detect missing `.git/` or non-GitHub remote before invoking `gh`. Skip the surface gracefully: "GitHub issues skipped (project not on GitHub)."

---

### T-8: 🟡 HIGH — Memory file scan path is hardcoded-implicit

**Where:** Phase 2, Surface 6 (Memory files).

**What goes wrong:** SKILL.md says memory files match `^deferred_*.md` or `^project_deferred_*.md`. It doesn't say *where* memory files live. For Claude Code: `~/.claude/projects/<encoded-project-path>/memory/`. For Cursor / Aider: different paths. SKILL.md is silent on which to scan. A literal execution either fails (wrong path) or hardcodes Claude Code's path (excludes other AI tools).

**Fix proposal:** Detect AI tool from Phase 1 wiring step. Use the right memory path per detected tool. Document the path mapping explicitly.

---

### T-9: 🟢 MEDIUM — Memory survey would import meta-files

**Where:** Phase 2, Surface 6 (Memory files).

**What goes wrong:** Stuffolio's memory directory has `deferred_work_index.md` — a meta-document describing how the project organizes deferred work, not a deferred item. SKILL.md's filename-match regex catches it. Importing it creates a spurious row whose Finding text is something like "Single source of truth is now Documentation/...".

**Fix proposal:** Add a content-shape check before importing memory files. If the file looks like a meta-doc (contains phrases like "single source of truth", "format:", "how to use"), flag it for user decision rather than auto-importing.

---

### T-10: 🔴 CRITICAL — Surface coverage misses ~80% of real deferred items

**Where:** Phase 2 + Phase 5.

**What goes wrong:** Live Stuffolio UNFORGET.md has roughly 60 active rows across all four sections. The Phase 2 survey, even with all the above fixes applied, would find around 9 real candidates:

- Deferred.md root: 0 (redirect pointer, T-3)
- `Deferred-archive-2026-05-01.md`: 22+ if T-2 not fixed (wrong: archive); 0 if T-2 fixed (correct: skipped)
- `.radar-suite/ledger.yaml`: 0 parseable findings (T-5)
- Plan files (`.agents/plans/`, `.claude/plans/`): ~5 if T-6 fixed
- Code comments: skipped by default
- GitHub issues: depends on `gh` working
- Memory files: 3 valid + 1 noise (T-9)

**That's ~9 real candidates out of ~60 actual rows.** The remaining ~50 rows are in surfaces SKILL.md doesn't currently scan:

| Where the missed rows actually live | Count (rough) |
|---|---|
| `scratch/*.md` audit reports | ~10 |
| `Documentation/Development/*.md` (e.g., `2026-04-30-test-suite-failures.md`) | ~5 |
| Per-skill scratch handoff yamls or fix plans | ~10 |
| Tacit knowledge / "things in user's head" | ~25 |

Phase 5 (user-add) is supposed to cover the tacit knowledge. But expecting a fresh adopter to dump 50 deferred items off the top of their head is unrealistic. The deep-dump (Phase 6) helps, but it's optional and rarely run.

**Fix proposal:** Expand Phase 2 to scan `Documentation/Development/*.md` (and equivalents like `Documentation/Notes/*.md`) for files whose content shape suggests deferral artifacts. Heuristics: heading text matching "Deferred", "Pending", "TODO", "Phase N pending"; date-prefix file names; explicit "DEFERRED:" prefixes in headings. Same idea for `scratch/*.md`.

This won't catch the 25 tacit-knowledge items. For those, recommend Phase 6 (deep-dump) be promoted to default-on for first-time adoption rather than opt-in.

---

### T-11: 🔴 CRITICAL — The unforget repo's own roadmap is invisible to its own skill (eating dogfood)

**Where:** Phase 2, Surface 1 (Deferred-named files) plus Phase 2 in general.

**What goes wrong:** While planning v0.2, this question came up: would the skill, run on the unforget public repo itself, find the v0.2 work that's tracked there?

The repo's deferred-work tracking lives in `v0.2-roadmap.md`. Walking SKILL.md's Phase 2 surfaces against this repo:

- **Deferred-named files:** `v0.2-roadmap.md` doesn't match the regex (`Deferred.md`, `BACKLOG.md`, `TODO.md`, `*deferred*.md`). Missed.
- **Audit-tool ledgers:** none.
- **Plan files:** none in `./plans/` or `./.claude/plans/`.
- **Code comments:** repo has no source code, only markdown.
- **GitHub issues:** none yet.
- **Memory files:** none for this project.

**The skill finds zero items in its own roadmap.** ~30 distinct v0.2 proposals across 6 tiers, all invisible to the skill that's supposed to surface deferred work.

This is T-10 happening in real time on the unforget repo itself. The skill can't find its own backlog.

**Why this is the strongest evidence for T-10's must-ship status:** any skill that fails its own self-test is in trouble. We can't reasonably expect adopters to trust the skill on their projects when it doesn't work on the project that built it. The fix isn't a future nice-to-have — it's the difference between v0.2 being honest about its own state and v0.2 shipping with a credibility hole.

**Fix proposal:** Either:
1. **Add roadmap-shaped filenames to Surface 1 regex.** Append `*roadmap*.md`, `ROADMAP.md`, `*plan*.md` (case insensitive). Easy. Catches the unforget case directly.
2. **Add a content-shape heuristic.** Any markdown file containing 3+ headings that look like priority tiers ("Tier N", "Phase N", "Priority N") gets flagged as a deferral artifact. Slower but more robust.

Recommend doing both. Filename regex is the cheap catch; content-shape catches the cases where users don't follow the naming convention.

**Action:** This finding is now Tier 6 item T-11 in `v0.2-roadmap.md` and should be folded into the must-ship subset alongside T-10.

---

## Summary

| # | Severity | Status |
|---|---|---|
| T-1 | 🟢 PASS | Spec works |
| T-2 | 🟡 HIGH | Spec gap |
| T-3 | 🟢 MEDIUM | Spec gap |
| T-4 | 🟡 HIGH | Spec gap |
| T-5 | 🔴 CRITICAL | Spec drift |
| T-6 | 🟡 HIGH | Spec gap |
| T-7 | 🟢 MEDIUM | Spec gap |
| T-8 | 🟡 HIGH | Spec gap |
| T-9 | 🟢 MEDIUM | Spec gap |
| T-10 | 🔴 CRITICAL | Coverage gap |
| T-11 | 🔴 CRITICAL | Self-test failure (the skill misses its own roadmap) |

**Pattern:** SKILL.md was written assuming a relatively clean project — one Deferred.md, one ledger, plans in `./plans/`, memory files in a known location. Real Stuffolio after several months of active use has multiple deferral surfaces in non-standard locations, an audit tool whose schema has evolved past what the spec assumes, redirect pointers from prior migrations, and complex memory directories. A fresh adopter running v0.1 init verbatim against Stuffolio would get a partial UNFORGET.md (~9 of ~60 rows), would incorrectly import ~22 archive rows, would miss ~50 real rows, and would have no way to know any of this was wrong.

**What this means for v0.1.x:** the safety hardening shipped today (header notice, format-version marker, recovery section, example file) is still useful — it protects the file *after* it's written. But the *adoption path* (Phase 2 survey) doesn't deliver against a real complex project. The fixes above need to land before v0.2 ships to avoid making bad first impressions on adopters.

**What this means for Stuffolio specifically:** the live UNFORGET.md is the source of truth and should not be regenerated by re-running init. The hand-curated state today is more valuable than what any v0.1 init would produce.

## Methodology notes for future re-tests

If re-running this test after spec fixes land:
1. Make a fresh scratch copy from current Stuffolio (`rsync -a` excluding `.build`, `DerivedData`, `build`, `node_modules`, `.git/objects/pack`).
2. Delete UNFORGET.md from the scratch copy only.
3. Read the latest SKILL.md verbatim.
4. Walk each phase against the scratch copy, capturing the candidate list at each surface.
5. Compare candidate count to the live UNFORGET.md row count — surface-by-surface coverage matters more than total count.
6. Don't run Phases 3-7 unless the surface coverage is above ~70% of live rows. Below that threshold, the test exits with a coverage-gap finding and the rest of the flow doesn't add information.

The test took ~30 minutes end-to-end. Most of the time was reading SKILL.md and inspecting actual project file shapes. Minutes spent on actual surface scans: ~5.

### Scratch directory retention

The scratch copy used for this test is at `~/Desktop/unforget-test-2026-05-02/` (~141MB). Kept after the test rather than deleted, because Tier 6 spec fixes (T-2, T-5, T-6, T-10, T-11) all need re-test runs against the same surfaces. Re-creating the scratch copy each time is ~2 minutes of rsync, but keeping the existing copy avoids drift between test runs.

**Cleanup trigger:** delete after v0.2 ships, or after any Stuffolio change that would invalidate the scratch (e.g., a major reorganization of `Documentation/`, `.radar-suite/`, or the deferred-work tracker location). Until then, the path is a stable testing fixture.
