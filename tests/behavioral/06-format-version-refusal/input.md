<!-- unforget-format: v2 -->

# UNFORGET — behavioral fixture

## 1. Paused plans

| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 🔴 THIS | Migrate feature to new API | 🟢 MEDIUM | 🟢 Medium | 🟡 High | 🟢 Good | ⚪ 1 file | Small | Open |

### Detail — Paused plans

- **P1** — Phases 1-2 shipped; phases 3-4 blocked on a schema we don't have yet. Plan: `~/.claude/plans/migrate.md`.

## 2. Session spillover

| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 🔵 NEXT | Fix concurrency warning in Manager | 🟢 MEDIUM | ⚪ Low | 🟢 Medium | 🟢 Good | ⚪ 1 file | Trivial | Open |

### Detail — Session spillover

- **S1** — Surfaced mid-refactor. `Manager.swift` emits a Sendable warning under strict concurrency.

## 3. Audit findings

| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 🟡 LATER | N+1 query on list screen | 🟡 HIGH | 🟢 Medium | 🟡 High | 🟠 Excellent | 🟢 2-5 files | Medium | Open |

### Detail — Audit findings

- **A1** — Perf audit 2026-07-14. List fetches thumbnails per-row instead of batching. **Verify-still-open:** `grep -rn "thumbnail" Sources/List/` — expect: per-row fetch still in `ListRow.swift`.

## 4. User-reported

| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |
|---|---|---|---|---|---|---|---|---|---|
| U1 | 🔵 NEXT | Tester saw a flash on launch | 🟢 MEDIUM | ⚪ Low | 🟢 Medium | 🟢 Good | ⚪ 1 file | Small | Open |

### Detail — User-reported

- **U1** — External tester reported a white flash on cold launch. Not reproduced yet.
