# unforget — Promotion + post-fix-sweep + backups reference

This file holds the release-time promote ritual, the post-fix-sweep workflow that closure recommendations point at, and the backup/recovery contract. Read it on `/unforget promote`, when discussing closure recommendations, or when recovering a broken UNFORGET.md.

**`promote` vs `archive`:** `/unforget promote` is the heavyweight release ritual documented below (verify 🔴 THIS, roll 🔵 NEXT → 🔴 THIS, re-rank ⚪ SOMEDAY, stamp the release line). If all you want is to clear completed rows out of the active view *between* releases, use the lightweight `/unforget archive` instead (spec in `reference/commands.md`) — it relocates finished rows without any release-cycle re-triage. Route day-to-day cleanup through `archive`; reserve `promote` for the release boundary. (`promote` still archives completed 🔴 THIS/🔵 NEXT rows as part of its ritual. The two write to the same file, the ledger's `<name>-archive.md` beside it, defined in `reference/commands.md` § The archive file, and share the same "don't archive Done-but-owed rows" safety rule.)

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

### Companion skills (format v2+): resolved via the manifest, not hardcoded here

The verify + generalize steps above map to unforget's companion **functions** —
`audit-reverify` (verify the closure is real) and `post-fix-sibling-scan` (generalize
the fix). Their skill mappings and URLs live in **one place**, the global companion
manifest (`reference/skill-handoffs.md`), NOT hardcoded at this trigger. The
shipped-default fillers are radar-suite and bug-echo respectively, but the user can
map either function to an Axiom auditor or any other skill in the manifest. To surface
the right expression (run the command if installed; one soft pointer with the URL if
not; nothing invented if unset), resolve the function against what the session reports
invocable:

```
python3 scripts/companions.py resolve --function post-fix-sibling-scan --invocable "<names>"
```

Detection is by **invocable name**, never a directory find (the one-star-risk lesson).
Companion skills are Apache-2.0 and optional; unforget's promote ritual works fully
with none installed.

---

## /unforget promote

Release-time ritual. Run at every release submission.

### Steps

0. **Integrity gate (format v2+).** Run `/unforget verify` first (`python3 scripts/verify_ledger.py --file <UNFORGET.md> --dir <ledger-dir>`). If it reports any **error-severity** finding — a self-contradicting row, a `done-verified` with no device/user tier or backed only by `session-claimed`, an unknown status value, or a 🔴 THIS row that *claims* done but isn't cleanly `done-verified` — **STOP.** You cannot make a release decision over a ledger whose "done" claims aren't trustworthy. Report the findings and require they be resolved before promotion continues. Warnings (bloat, stale-recipe, registry drift) do not block. On a v1 (tokenless) ledger this gate produces no errors and promotion proceeds normally.
1. **Verify** every `🔴 THIS` row is resolved. With tokens (v2+): the row's `@status` must be `done-verified` (clean) or `withdrawn`, or the row must be explicitly demoted. A `done-unverified` THIS row is NOT resolved: it still owes a check and remains a blocker. Without tokens (v1): Status is a clear completion word (Fixed, Done, Closed, Withdrawn) with nothing owed. List any that don't qualify and require an explicit demotion or fix.
2. **Back up, then promote.** Run `python3 scripts/ledger_backup.py backup --file <UNFORGET.md>` before the first write (§ Backups and recovery; skipped on `--dry-run`). Then promote all `🔵 NEXT` rows to `🔴 THIS` (they are now the next release's blockers).
3. **Re-triage** all `🟡 LATER` rows that are still relevant to `🔵 NEXT`. Items no longer relevant get archived.
4. **Re-rank `⚪ SOMEDAY`** items 180 days or older: prompt user for promote / demote / archive.
5. **Stamp** the "Last promoted" line at the top of UNFORGET.md with new build/version + date.
6. **Ship-risk handoff (format v2+, optional).** A 🔴 THIS row nearing release is the earned transition for the `ship-risk-scoring` companion function (default: one-star-risk — score what a shaky release risks). Resolve it against what's invocable — `python3 scripts/companions.py resolve --function ship-risk-scoring --invocable "<names>"` — and say the resolver's one-line expression. Governance per `reference/skill-handoffs.md` §5: advisory, once/session, never blocking, and never a way to defer the actual release check. Full mechanic in `reference/skill-handoffs.md`.

Every row `promote` archives (completed rows in step 1, LATER rows no longer relevant in step 3, SOMEDAY rows the user chooses to archive in step 4) goes to the ledger's archive file in one `## Archived <date> (promote)` block. See `reference/commands.md` § The archive file.

This command DOES modify UNFORGET.md (unlike `/unforget scan`), so the user is shown a preview of every change before it's applied.

### Dry-run mode

`/unforget promote --dry-run` runs the same steps above but writes nothing. The skill renders the would-apply changes as a markdown diff inline in the Claude Code conversation. Each row that would be promoted, demoted, archived, re-stamped, or re-triaged appears as a before/after diff block.

To apply the same changes after reviewing the dry-run output, the user replies `apply` (or any explicit confirmation). The skill then re-runs `/unforget promote` without the `--dry-run` flag, picks up the same set of changes, creates the auto-backup (see "Backups and recovery" below), and writes the file.

To abandon the changes, the user replies `cancel` or anything else that is not an explicit confirmation. The skill exits without touching UNFORGET.md.

`--dry-run` does not create a backup file. Backups are only written by the real `promote`, on the path that actually modifies UNFORGET.md.

---

## Backups and recovery

**One contract, every command that rewrites a ledger.** Before a ledger file is rewritten, its current bytes are copied beside it as a stamped backup, and that ledger's backups are pruned to the newest 5. The helper is `scripts/ledger_backup.py`; no command invents its own backup.

| Command | How it backs up |
|---|---|
| `/unforget promote` (not `--dry-run`) | Run `python3 scripts/ledger_backup.py backup --file <ledger>` before writing. |
| `/unforget archive` (not `--dry-run`) | Same command, before moving rows out. |
| `/unforget verify --fix` | `row_budget.py split --apply` backs up on its own before each split. |
| `set_aside.py convert --apply` | Backs up on its own before inserting tokens. |
| `init` migration (`move_ledger.py --apply`) | Backs up the source before removing it or turning it into a redirect. |

`add` and `edit` change one row in view of the user and are not backed up; git, or the last backup above, covers them. Dry runs never write a backup.

### Naming

Backups sit beside the ledger, named `<ledger name>.bak-YYYY-MM-DD-HHMMSS` in local time: `UNFORGET.md.bak-2026-05-02-143027`, or `SITE-UNFORGET.md.bak-2026-05-02-143027` for a child ledger. An existing backup is never overwritten. Two rewrites in the same second reuse the backup when the bytes are identical, and otherwise wait for the next second.

### Retention

Each ledger keeps its own 5 most recent backups; `ledger_backup.py backup` prunes after writing, so retention needs no separate step. To prune without backing up, run `python3 scripts/ledger_backup.py prune --file <ledger> --keep 5`. Both refuse `--keep 0`, which would delete every backup. (`scripts/prune_backups.py --dir <dir>` still prunes `UNFORGET.md` backups only, for older callers.)

To keep a backup past the 5-deep window, rename it so it no longer ends in `.bak-<stamp>` (for example, `UNFORGET.md.bak-2026-05-02-143027` to `UNFORGET-pre-build33.md`). Renamed files are not recognized as backups and are never pruned.

### `.gitignore` recommendation

Backup files are local recovery artifacts, not project history, and should not be committed. The recommended `.gitignore` line, which covers child ledgers too, is:

```
*.md.bak-*
```

The init flow can offer to add this entry when the project is first wired up.

### Recovering from a broken ledger

If a ledger becomes unparseable (manual edit error, merge conflict left in place, mistaken structural change), the user has two paths:

1. Rename the most recent backup back to the ledger's name, replacing the broken file. This restores the state from before the most recent rewrite listed above.
2. Follow unforget's [`docs/RECOVERY.md`](https://github.com/Terryc21/unforget/blob/main/docs/RECOVERY.md), which covers manual repair when no backup is available.

Path 1 is fastest when the break happened during or after the most recent backed-up command. Path 2 is the fallback when the break predates the oldest retained backup.

---

## Algorithm fallback (Python unavailable)

When `python3` is not on PATH, the skill backs up and prunes by hand:

0. Copy the ledger to `<ledger name>.bak-<YYYY-MM-DD-HHMMSS>` beside it, and confirm the copy is the same size as the ledger before rewriting anything.
1. List files in the ledger's directory matching `<ledger name>.bak-*`.
2. Sort lexicographically (the `YYYY-MM-DD-HHMMSS` format sorts identically to chronological order).
3. Keep the 5 most recent. Delete the rest.

The fallback is safe and deterministic for backup pruning specifically. The Python script exists primarily to keep the skill prose short and to give CI environments a programmatic surface.
