# /unforget archive

Part of the unforget command reference; the index is [../commands.md](../commands.md).

---

## /unforget archive

Move completed rows out of the active tables into the ledger's archive file (§ The archive file, below). **Lightweight and safe to run anytime** — this is the everyday cleanup command, distinct from the heavyweight release-time `/unforget promote` ritual (see `reference/promotion.md`). `promote` re-triages the whole release cycle (verify THIS, roll NEXT→THIS, re-rank SOMEDAY, stamp the release line); `archive` does only the one job of clearing finished work out of view.

### Why this exists

`promote` was historically the only command that removed completed rows, but it is a release-submission ritual the user has to remember to invoke. In practice ledgers accumulate dozens of ✅ Done rows that were never cleared because nobody runs `promote` between releases — the single most common way an UNFORGET.md rots. `archive` is the low-friction alternative: one job, no release semantics, run it whenever the active tables feel cluttered. The `list` and `add` archive nudge (below) points here.

### Usage

```
/unforget archive                     ·  archive clean-Done rows (keeps "Done-but-owed" rows — see safety rule)
/unforget archive --dry-run           ·  show what WOULD be archived, write nothing
/unforget archive --all-done          ·  archive every Fixed/Done row, including "owed" ones (skip the safety hold)
```

### Safety rule (the important part): keep "Done-but-owed" rows

Archiving a row that still owes work hides real remaining work — the exact failure this skill exists to prevent. What is archivable is decided by the `@status` token (format v2+):

- **Archive ONLY** `@status:done-verified` and `@status:withdrawn`.
- **HOLD** `@status:done-unverified` — this is the "done-but-owed" state by definition (fixed, not yet ground-truth-checked). It stays in the active tables.
- Never archive `open`, `in-progress`, or `blocked`.

`--all-done` overrides the hold on `done-unverified` (use only when the user confirms the owed check is moot).

**Legacy fallback (tokenless rows):** a row with no `@status` token is classified the old way — a Done/Fixed row is held when its Status or Finding text contains an owed-signal (`pending` / `owed` / `still owed` / `eyeball` / `visual check` / `verify on device` / `device-verify` / `device round-trip` / `delivery test` / `deploy owed` / `not yet deployed` / `awaiting deploy` / `⏳`). This keeps pre-v2 ledgers safe until their rows are upgraded.

### Steps

0. **Integrity gate (format v2+).** Run `/unforget verify` first. If any **error-severity** finding stands (a contradiction, an unproven/`session-claimed` "done", an unknown status value, a THIS row claiming done but not cleanly `done-verified`), **STOP** and report — do not archive over a ledger whose "done" claims aren't trustworthy, because a bad `done-verified` is exactly what `archive` would relocate out of sight. Warnings do not block. A v1 (tokenless) ledger produces no errors and archiving proceeds.
1. **Read UNFORGET.md.** Run `python3 scripts/parse_status.py --file <path>`; a row is archivable when its result has `archivable:true` (i.e. a CLEAN `done-verified` — valid tier, no contradiction — or `withdrawn`). For tokenless legacy rows, fall back to the Fixed/Done + owed-signal heuristic above.
2. **Split** into `archive` (archivable) vs `keep` (`done-unverified`, owed-signal legacy rows, and everything not done). `--all-done` also archives `done-unverified`.
3. **Preview** — show the two lists (IDs + one-line title) and counts: "Archive N clean-Done rows; keep M Done-but-owed rows active." On `--dry-run`, stop here and write nothing.
4. **Confirm** with the user (single AskUserQuestion: proceed / show-full-rows / cancel).
5. **Back up first:** `python3 scripts/ledger_backup.py backup --file <ledger>`, so a mis-classification is recoverable (the contract is `reference/promotion.md` § Backups and recovery).
6. **Write:** move the archived rows to the ledger's archive file (§ The archive file), in a new dated block. Remove those rows from the active tables. Preserve table structure — section headers and separator rows stay intact.
7. **Report** the before/after active row count and the archive-file path.

`archive` modifies UNFORGET.md, so (like `promote`) it always previews before writing. Unlike `promote`, it does not touch Target values, re-rank anything, or stamp release metadata — it only relocates finished rows. The archive file is never scanned by `init`/`import` (it lives under the archive-path exclusion rule in `reference/surfaces.md`), so archived rows do not re-enter the active backlog.

### The archive file

Every command that moves rows out of a ledger (`archive`, `promote`, and `init` when it imports already-resolved items) writes to the **same file**, so a ledger's history lives in one place. This section is the only definition; the other references point here.

- **Name and place:** the ledger's own name with `-archive` added, in the same directory. `UNFORGET.md` archives to `UNFORGET-archive.md`; a child ledger `SITE-UNFORGET.md` archives to `SITE-UNFORGET-archive.md`. Each ledger has exactly one.
- **Created on first use**, with a short header: `# <ledger name> archive` and a line saying the rows are finished work kept for history, not action.
- **One dated block per run, appended at the end:** `## Archived YYYY-MM-DD (<command>)`, for example `## Archived 2026-11-18 (promote)`. Rows keep their exact text, including the `@status` token. Earlier blocks are never rewritten.
- **Never read as active work.** Its `-archive` name puts it outside `init`/`import` (the archive rule in `reference/surfaces.md`) and outside the ledger-discovery check (`scripts/import_drift.py`), so archived rows do not come back into the backlog.
- **Older archive files stay where they are.** A ledger set up by an earlier version may also have dated files such as `UNFORGET-archive-2026-05-02.md` or an `archive/` folder. They are left untouched and remain valid history; new runs append to the single file above.

### The archive nudge (surfaced by `list` and `add`)

To make cleanup discoverable without forcing it, `/unforget list` and `/unforget add` append a one-line nudge when completed rows pile up. After their normal output, count rows whose Status is `Fixed` / `Done` in the active tables; if **5 or more**, append exactly one line:

```
💡 N completed rows are sitting in the active tables — run /unforget archive to move them out.
```

One line, non-blocking, informational — never a prompt or an action. Threshold is 5 by default; the registry's `archive_nudge_threshold` key overrides it (`0` silences the nudge entirely), settable via the Thorough tier of `/unforget list --fresh` or by hand — see `reference/registry.md` § The schema. A legacy `config` block at the top of UNFORGET.md carrying `archive_nudge_threshold: N` is still honored if present, but the registry wins when both are set. On `/unforget add`, skip the nudge if the add itself was slow — `add`'s 30-second speed promise wins; the nudge must never add latency or a question.
