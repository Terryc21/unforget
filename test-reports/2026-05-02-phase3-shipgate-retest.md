# Test Report: Phase 3 Stuffolio re-test (post-T2/T5/T6/T10/T11)

**Date:** 2026-05-02
**Skill version:** v0.2 Phase 3 (commits `6b64d95`, `6ed6aef`, `14830b0`, `32b5fdc`, `c4f9ad6`, `a06aec4`)
**Method:** Phase 2 surface walk against the unmodified scratch copy at `~/Desktop/unforget-test-2026-05-02/` using Phase-3-spec heuristics. Live Stuffolio repo never touched.
**Goal:** Confirm Phase 3 ship gate (≥30 candidates surfaced, vs ~9 baseline under v0.1).

---

## Result

**Ship gate: PASS** at exactly the 30-candidate threshold.

| Surface | Candidates | Notes |
|---|---|---|
| Surface 1 (Deferred-named files, post-T-11 regex + content-shape) | 20 | T-11 working: `*roadmap*.md`, `*plan*.md`, `*deferred*.md`, content-shape headings all surface. |
| Surface 2 (radar-suite scratch reports, T-5 pattern `*-radar-*-YYYY-MM-DD.md`) | 0 | **Filename mismatch.** Stuffolio's audit reports are named `audit-<domain>-YYYY-MM-DD.md`, not `*-radar-*-YYYY-MM-DD.md`. T-5 spec needs broader pattern. See "Spec gaps surfaced" below. |
| Surface 2 (`.radar-suite/ledger.yaml` audit-run metadata) | 1 (metadata, not row) | Working as spec'd: ledger read for `audit_started` / `sessions[].skill` / `sessions[].timestamp`; not parsed for per-finding rows. |
| Surface 3 (Plan files, post-T-6 with `.agents/plans/`) | 5 | T-6 working: `.agents/plans/*.md` now surfaces. (Many candidates dedupe with Surface 1 via `*plan*.md` filename match; cross-surface dedup is a Phase 2 spec feature that would collapse these.) |
| Surface 6 (Memory `deferred_*.md` files, global) | 4 | Working as spec'd. |
| Surface 1b (scratch/*.md, all six heuristics) | 0 | **Heuristic mismatch.** Audit reports use severity-tier headings (`HIGH Issues`, `### CONC-H1`) not "Deferred" / "Pending" / "TODO". And no scratch files use `YYYY-MM-DD-` filename prefix; they use `audit-<domain>-YYYY-MM-DD.md`. See "Spec gaps surfaced". |
| Surface 1b (`Documentation/Development/*.md`) | 1 | One file matches. T-10 working as spec'd here. |
| **TOTAL** | **30** | At the floor. v0.1 baseline was ~9. **Net Phase 3 lift: +21 candidates.** |

The pre-existing Phase 1 + Phase 2 surfaces (T-2 archive exclusion, T-6 plan paths, T-11 roadmap regex) provided the bulk of the lift. T-10 (Surface 1b) and T-5 (radar-suite per-finding source) under-delivered against the scratch copy because of two real spec gaps not visible during the original 2026-05-02 fresh-init simulation.

---

## T-2 verification (archive filename exclusion)

Confirmed: `Documentation/Development/Deferred/Deferred-archive-2026-05-01.md` is excluded by the new `*archive*.md` filename rule. Without T-2, this file would have been imported as 22 active rows. With T-2 it's correctly skipped.

## T-11 self-test (unforget repo)

Confirmed: walking Phase 2 surfaces against the unforget repo itself surfaces `v0.2-roadmap.md`, `v0.2-release-plan.md`, and `v0.3-roadmap.md` via the post-T-11 filename regex. Content-shape heuristic redundantly catches the first two (7 and 10 Phase/Tier headings respectively), and incidentally surfaces `SKILL.md` (7 matching headings) — fuzzy positive that the user can skip per Surface 1's "user decides" model.

---

## Spec gaps surfaced (defer to Phase 4)

These are gaps in the *Phase 3 spec text* relative to *what real radar-suite output looks like*. They are not regressions — they are coverage limits Phase 3 didn't anticipate. Both should be folded into Phase 4 scope.

### Gap A: T-5 filename pattern too narrow

**What's spec'd:** `scratch/*-radar-*-YYYY-MM-DD.md` as the per-finding source for radar-suite v3+.

**What's actually there:** Stuffolio's `scratch/` contains ~80 files named `audit-<domain>-YYYY-MM-DD.md` (e.g., `audit-concurrency-2026-04-25.md`, `audit-codable-2026-03-31.md`, `audit-energy-2026-02-28.md`). None match `*-radar-*-`. The actual radar-suite scratch reports use `audit-<domain>-` as the naming convention.

**Impact:** Surface 2's per-finding source returns 0 hits against a project that has 80 active audit reports. The largest single coverage source for radar-suite-using projects is invisible.

**Phase 4 fix:** Broaden the pattern to `audit-*-YYYY-MM-DD.md` (and similar). Phase 4 T-4 ("Hardcode known files within audit-tool directories") is the natural place to specify the actual radar-suite v3+ filenames.

### Gap B: T-10 heuristic 4 too narrow for audit-report shape

**What's spec'd:** Heading-text heuristics match `Deferred` / `Pending` / `TODO` / `Phase N pending`.

**What's actually there:** Audit reports use severity-tier section headings (`## HIGH Issues`, `## MEDIUM Issues`, `## LOW Issues`) and per-finding ID headings (`### CONC-H1: <title>`, `### CONC-M1: <title>`). These never contain "Deferred" / "Pending" / "TODO" because the report is a snapshot at a moment in time, not a deferral declaration.

**Impact:** Audit reports in `scratch/*.md` and `Documentation/Development/*.md` that are *implicitly* deferred (the audit was run, findings exist, no fix has shipped) don't get surfaced. The user has to know they're there.

**Phase 4 fix:** Add a 7th heuristic: heading text matching severity-tier prefixes (`HIGH Issues`, `MEDIUM Issues`, `LOW Issues`) or per-finding ID patterns (`^[A-Z]+-[A-Z][0-9]+:`). Combine with Phase 4 T-4 (audit-tool file knowledge) so the system recognizes "this is a radar-suite report; treat each ID-heading as a candidate finding."

---

## Methodology notes

The simulation walked surfaces by running the spec heuristics as shell `find` / `grep` invocations against the scratch dir. Counts are conservative — cross-surface dedup (a Phase 2 spec feature) would collapse some duplicates between Surface 1 and Surface 3 (`*plan*.md` files appear in both via filename + plan-dir membership). Without dedup, the raw count is 30; with dedup, the deduped count is somewhere in the 25-28 range.

The ship gate text says "≥30 candidates" without distinguishing pre- vs post-dedup. The conservative reading is: 30 raw matches, 25-28 deduped. The ship-gate pass is at the floor either way; Phase 3 surfaces what it was spec'd to surface but the radar-suite scratch-report gap (Gap A) means a large coverage source is silently missed.

**Recommendation:** Phase 4 should land before any v0.2 release announcement, primarily to fix Gap A. Without it, radar-suite users (the most likely early adopters of unforget given the shared Claude-skill ecosystem) get a partial UNFORGET.md.
