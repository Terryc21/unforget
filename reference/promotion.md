# unforget — Promotion + post-fix-sweep + backups reference

This file holds the release-time promote ritual, the post-fix-sweep workflow that closure recommendations point at, and the backup/recovery contract. Read it on `/unforget promote`, when discussing closure recommendations, or when recovering a broken UNFORGET.md.

---

## /unforget post-fix-sweep (workflow, not a command)

This is a **workflow that chains three skills**, not a single command. It's documented here because `/unforget` is the entry point most users hit first — the row that's about to be closed is the trigger for the rest of the loop.

### The three stages

1. **Surface** — `/unforget` (this skill) shows you a row that's been deferred. You're about to mark it Fixed because you think you fixed it (or someone else did).

2. **Verify** — Before trusting the closure, confirm the fix is real and the anti-pattern is actually gone from the current code. Use `/radar-suite focus on <symbol>` (or read the file directly) to check. **Stale Open rows are surprisingly common.** A fix can ship without anyone updating the ledger; six weeks later the row still says Open and a future audit assumes it's a live bug.

3. **Generalize** — If the fix replaced an anti-pattern with a corrected pattern, the same anti-pattern likely exists elsewhere in the codebase. Use `/bug-echo` with a one-sentence description of what the fix replaced. bug-echo scans the entire codebase for the same shape and rates each match BUG / OK / REVIEW. The output is bugs **that haven't fired yet** but are sitting in code with the same crash conditions as the one you just fixed.

### Why this loop is high-leverage

A standard audit skill (radar-suite, ESLint, custom linters) finds bugs by matching against a pre-built pattern catalog. The catalog reflects what the audit author thought was a bug at the time the rule was written.

The post-fix sweep finds bugs by matching against a pattern that **just demonstrated it was a real bug in your specific codebase**. The fix is the proof. Pattern matching after a real fix is dramatically more accurate than pattern matching from theory.

The other half of the leverage: bugs that haven't crashed yet are the highest-ROI thing in any audit cycle. They cost the same to fix as a crashed bug, but you don't pay the cost of the crash (lost user trust, support tickets, root-cause investigation under deadline). The post-fix sweep is the systematic way to find them.

### Example

A real-world run from the unforget development codebase:

1. **Surface:** `/unforget` showed an Open row "iPhone crash tap item: collapsibleSectionsStack" (had been Open for a month).
2. **Verify:** `/radar-suite focus on collapsibleSectionsStack` reported the bug had actually been fixed weeks earlier in two commits. The current code already had the corrected pattern. The UNFORGET row was stale. Marked Fixed with the historical narrative captured in the detail block.
3. **Generalize:** Extracted the anti-pattern in one sentence ("VStack with 12+ if-conditional children in one scope can crash on physical iPhone with SubstGenericParametersFromMetadata") and ran `/bug-echo` with that description. bug-echo found one BUG (a list-row view with the same density) and three WATCH sites (10–12 conditionals each, near the threshold). The list-row bug had never crashed because users hadn't accumulated enough records yet — but the conditions were identical. Fixed with the same split pattern.

Three skills, one loop. Total time: ~90 minutes. The unfired list-row bug — invisible to every standard audit because it hadn't fired — was the highest-leverage finding in the cycle.

### When to skip the loop

- Trivial fixes (typos, single-character changes, isolated state edits)
- Fixes to one-off code with no callers (truly localized)
- Fixes that are themselves cleanup of a prior failed migration (the pattern is already on its way out)
- When the user has explicit time pressure and just wants to ship the close

### Companion skill install URLs

If your prior `/unforget edit --status=Fixed` recommendation showed install URLs, those are:

- **radar-suite:** `https://github.com/Terryc21/radar-suite` — verifies the closure is real; multiple audit dimensions per skill in the suite
- **bug-echo:** `https://github.com/Terryc21/bug-echo` — generalizes the fix; produces a rated report

Both are Apache-2.0 licensed and install via the standard Claude Code plugin pattern (clone the repo, copy the skill directory into `~/.claude/skills/`, restart Claude Code) or one-line marketplace commands when those land.

---

## /unforget promote

Release-time ritual. Run at every release submission.

### Steps

1. **Verify** every `🔴 THIS` row has Status = Fixed. List any that don't and require an explicit demotion or fix.
2. **Promote** all `🔵 NEXT` rows to `🔴 THIS` (they are now the next release's blockers).
3. **Re-triage** all `🟡 LATER` rows that are still relevant to `🔵 NEXT`. Items no longer relevant get archived.
4. **Re-rank `⚪ SOMEDAY`** items 180 days or older: prompt user for promote / demote / archive.
5. **Stamp** the "Last promoted" line at the top of UNFORGET.md with new build/version + date.

This command DOES modify UNFORGET.md (unlike `/unforget scan`), so the user is shown a preview of every change before it's applied.

### Dry-run mode

`/unforget promote --dry-run` runs the same steps above but writes nothing. The skill renders the would-apply changes as a markdown diff inline in the Claude Code conversation. Each row that would be promoted, demoted, archived, re-stamped, or re-triaged appears as a before/after diff block.

To apply the same changes after reviewing the dry-run output, the user replies `apply` (or any explicit confirmation). The skill then re-runs `/unforget promote` without the `--dry-run` flag, picks up the same set of changes, creates the auto-backup (see "Backups and recovery" below), and writes the file.

To abandon the changes, the user replies `cancel` or anything else that is not an explicit confirmation. The skill exits without touching UNFORGET.md.

`--dry-run` does not create a backup file. Backups are only written by the real `promote`, on the path that actually modifies UNFORGET.md.

---

## Backups and recovery

Every `/unforget promote` (without `--dry-run`) writes a timestamped backup of the current UNFORGET.md before applying changes. Backups make destructive operations safe to refine: if a promote produces unexpected output, the previous file is one rename away.

### Naming

Backups land in the same directory as UNFORGET.md, named `UNFORGET.md.bak-YYYY-MM-DD-HHMMSS`. The timestamp uses local time. Example: `UNFORGET.md.bak-2026-05-02-143027`.

### Retention

The skill keeps the 5 most recent backups. During each `promote`, backups older than the 5 most recent are pruned silently. The retention count is fixed in v0.2 and is not user-configurable.

**Preferred implementation:** delegate retention to the helper script:

```
python3 scripts/prune_backups.py --keep 5 --dir <directory-containing-UNFORGET.md>
```

The script lists files matching `UNFORGET.md.bak-YYYY-MM-DD-HHMMSS`, sorts by timestamp, deletes any beyond the most recent N. Returns JSON `{"kept": [...], "pruned": [...]}` so the skill can surface the action in its post-promote summary.

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

## Algorithm fallback (Python unavailable)

When `python3` is not on PATH, the skill performs backup pruning manually:

1. List files in the UNFORGET.md directory matching `UNFORGET.md.bak-*`.
2. Sort lexicographically (the `YYYY-MM-DD-HHMMSS` format sorts identically to chronological order).
3. Keep the 5 most recent. Delete the rest.

The fallback is safe and deterministic for backup pruning specifically. The Python script exists primarily to keep the skill prose short and to give CI environments a programmatic surface.
