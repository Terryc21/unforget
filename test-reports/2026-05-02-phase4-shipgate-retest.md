# Test Report: Phase 4 Stuffolio re-test (post-T-3/T-7/T-8/T-9/T-12/T-13)

**Date:** 2026-05-02
**Skill version:** v0.2 Phase 4 (commits `691ee1a`, `d3c8dd7`, `f47dd58`, `fb66a09`, `24c322f`, `43564db`, `07545ec`)
**Method:** Phase 2 surface walk against the unmodified scratch copy at `~/Desktop/unforget-test-2026-05-02/` using post-Phase 4 spec heuristics. Live Stuffolio repo never touched.
**Goal:** Confirm Phase 4 ship gate (≥42 candidates total, Surface 2 per-finding rows ≥30).

---

## Result

**Ship gate: PASS by a wide margin.**

| Metric | Phase 4 ship gate | Measured | Status |
|---|---|---|---|
| Total candidates | ≥42 | **121** | ✅ PASS |
| Surface 2 per-finding rows | ≥30 | **54** | ✅ PASS |

| Surface | Phase 3 result | Phase 4 result | Net change | Notes |
|---|---|---|---|---|
| Surface 1 (Deferred-named, post-T-3 redirect skip) | 20 | 19 | -1 | T-3 working: root `Deferred.md` (11 lines, contains "MOVED" + path ref to UNFORGET.md) is now correctly classified as a redirect and skipped with a status note rather than parsed as a backlog. |
| Surface 2 audit-report files (T-12) | 0 | **35** | **+35** | T-12 working: post-rewrite pattern `scratch/audit-*-YYYY-MM-DD.md` matches the actual radar-suite v3+ output. 85 audit files in `scratch/`, 35 of which contain at least one severity-tier or per-finding ID heading (heuristic 7 fires). |
| Surface 2 + T-13 per-finding rows | 0 | **54** | **+54** | T-13 working: per-finding ID regex `^#+\s+[A-Z]+-[A-Z][0-9]+:` extracts 54 distinct findings (e.g., `### CONC-H1:`, `### RS-019:`) across 11 ID-coded reports. The other 24 audit reports use severity-tier section headings only, so they surface as file-level candidates without per-finding extraction. |
| Surface 2 ledger.yaml metadata | 1 (metadata, not row) | 1 (metadata, not row) | 0 | `.radar-suite/ledger.yaml` audit-run metadata role unchanged from Phase 3. Hardcoded allowlist (T-12) means other yaml in `.radar-suite/` is explicitly skipped. |
| Surface 3 (plan files, post-T-6 with `.agents/plans/`) | 5 | 5 | 0 | Unchanged from Phase 3. T-6 already shipped in Phase 3. |
| Surface 1b heuristics 1-6 | 1 | 5 | +4 | Same heuristics as Phase 3, but now scoped includes 92 scratch files. 5 files match (4 are scratch audit reports caught by heuristics 1/3, 1 is `Documentation/Development/FUTURE_FEATURES.md`). |
| Surface 6 (memory, post-T-8 ancestor walk + T-9 meta-doc skip) | 4 | 3 | -1 | T-8 ancestor-walk fallback critical: cwd-encoded path `-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio/memory/` is empty. Parent-encoded path `-Volumes-2-TB-Drive-Coding-GitHubDeskTop/memory/` contains 4 deferred-named files. T-9 meta-doc check correctly flags `deferred_work_index.md` (matches "single source of truth", "format:", "how to use" — 4 phrase hits) for user prompt instead of auto-import. Net 3 candidates. |
| **TOTAL (raw)** | **30** | **121** | **+91** | Pre-dedup count. Even with aggressive dedup (Surface 1b heuristics 1/3 overlap with Surface 2 file recognition for 4 of 5 files), deduped total is ≥117. |

---

## T-3 verification (redirect-pointer detection)

Confirmed: `./Deferred.md` is 11 lines (under the 30-line threshold) and contains both `MOVED` and a path reference to `Documentation/Development/Deferred/UNFORGET.md`. Both T-3 conditions hold; the file is correctly classified as a redirect pointer and skipped. Without T-3, this file would have surfaced as a Surface 1 match and its 11-line redirect text would have been parsed as deferral entries.

## T-7 verification (gh fourth state)

Not exercised by this test (the scratch copy is on GitHub via the live Stuffolio repo's git config). Spec change is observable but the GitHub-issues surface returns the same result it did under Phase 3's three-states block when the repo IS on GitHub. The fourth state matters for non-GitHub projects (GitLab, Bitbucket, self-hosted), which can be exercised in a separate test against a non-GitHub project.

## T-8 verification (memory paths per AI tool)

**Major finding during retest:** the originally spec'd path-encoding rule was wrong in two ways:

1. **Spaces are NOT preserved.** Real Claude Code encoding replaces each whitespace character with `-`. Working dir `/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio` encodes to `-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio`, not `-Volumes-2 TB Drive-Coding-GitHubDeskTop-Stufflio`. Verified by direct inspection of `~/.claude/projects/`.

2. **Memory may live at an ancestor's encoded path, not the cwd's.** Stufflio's memory lives under `-Volumes-2-TB-Drive-Coding-GitHubDeskTop/memory/` (the parent dir's encoding), not `-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio/memory/` (the project leaf's encoding). The cwd-encoded path was empty; only ancestor-walk discovered the 4 memory files.

Both corrections shipped in commit `07545ec` as a follow-up to the original T-8 commit `24c322f`. Without these corrections, the Phase 4 retest's Surface 6 would have returned 0 candidates (matching the v0.1 behavior) and the user would never know memory existed. This is a high-impact accuracy fix for an existing surface, not just a spec polish item.

## T-9 verification (memory meta-file content shape)

Confirmed: `deferred_work_index.md` matches 4 of the meta-doc phrases (case-insensitive). T-9 correctly flags it for user prompt instead of auto-importing. Without T-9, the file's prose ("single source of truth is now `Documentation/Development/Deferred/DEFERRED.md`") would be parsed as a phantom finding row.

## T-12 verification (Surface 2 radar-suite filename)

Confirmed: 85 files in `scratch/` match `audit-*-YYYY-MM-DD.md`. Phase 3 spec matched 0 of these. The single largest coverage source for radar-suite-using projects is now visible.

## T-13 verification (audit-report heading heuristic)

Confirmed: 54 per-finding ID headings extracted across 11 ID-coded audit reports. The remaining 24 reports surface as file-level candidates only (severity-tier headings present, but no per-finding ID headings) — that's correct behavior; those reports are older v3 alpha output that summarize at the section level rather than itemizing per-finding.

---

## Spec gaps surfaced this retest

Two corrections were applied during the retest (both committed):

1. **T-8 path-encoding rule** — fixed in commit `07545ec` (whitespace becomes dash, not preserved).
2. **T-8 ancestor-walk fallback** — added in same commit (memory may live at parent-encoded path).

No further spec gaps surfaced. Phase 4 is complete.

---

## Methodology notes

The simulation walked surfaces by running the spec heuristics as shell `find` / `grep` invocations against the scratch dir. The `Surface 2 audit-report files` count (35) and the `Surface 2 + T-13 per-finding rows` count (54) are independent: the 35 file-level candidates surface as "audit report file" candidates per Surface 2 file recognition; the 54 per-finding rows are extracted from the 11 of those 35 reports that use ID-coded headings. The remaining 24 reports surface as file-level only.

Cross-surface dedup (a Phase 2 spec feature) would collapse some duplicates between Surface 1b heuristics 1/3 and Surface 2 audit-report files (4 of the 5 Surface 1b matches are also Surface 2 matches). Even with full dedup, the deduped total is ≥117 candidates, far exceeding the ≥42 ship gate.

The ship gate was conservative — Phase 4 cleared it by a factor of ~3x. The bulk of the lift came from T-12 (file recognition) and T-13 (per-finding extraction), as predicted.
