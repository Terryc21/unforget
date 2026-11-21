# unforget: subcommand reference (index)

Each subcommand's spec is its own file under `reference/commands/`, so a command loads only
what it needs. `/unforget init` is in `reference/init.md` and `/unforget promote` in
`reference/promotion.md`. `/unforget report` (`list --html`) is in `reference/html-report.md`.

| Subcommand | File | What it covers |
|---|---|---|
| `/unforget add` | [commands/add.md](commands/add.md) | capture a new deferral (the deferral gate, the row, the detail block) |
| `/unforget edit` | [commands/edit.md](commands/edit.md) | refine a row's columns; the status-token rule, the row-length check, the closure handoff |
| `/unforget import` | [commands/import.md](commands/import.md) | re-run the surface survey after init; registry drift |
| `/unforget list` | [commands/list.md](commands/list.md) | show current state: filters, output format, `--view`, `--group-by`, multi-ledger scope, terminal rendering |
| `/unforget list --fresh` | [commands/list-preferences.md](commands/list-preferences.md) | `list --fresh`: the display-preference interview and how its answers are saved |
| `/unforget show` | [commands/show.md](commands/show.md) | one row's current state (Finding, Impact, Fix); `--full` adds the raw detail block |
| `/unforget scan` | [commands/scan.md](commands/scan.md) | rows past their staleness threshold (ages from `scripts/row_age.py`) |
| `/unforget branch` | [commands/branch.md](commands/branch.md) | atomically create a child ledger (full model in `branching.md`) |
| `/unforget verify` | [commands/verify.md](commands/verify.md) | the integrity lint and `verify --fix` |
| `/unforget archive` | [commands/archive.md](commands/archive.md) | move completed rows out of the active tables; the archive file |
| `/unforget --version` | [commands/version.md](commands/version.md) | `--version`: install check, version reconciliation, recall trigger |

## Where each section went

Until 11/21/2026 all of these were sections of this one file. A reference elsewhere to
`commands.md` § *Some heading* now lives in the file listed here.

- **[commands/add.md](commands/add.md):** Usage; The deferral gate (format v2+) — runs FIRST, before anything else; Steps; Subsection flags (optional); Branch auto-suggest (format v2+, on a repeated pattern only); Speed target
- **[commands/edit.md](commands/edit.md):** Usage; Steps; Status-token rule (format v2+); Budget check at write time (not just at scan/verify); Closure handoff (when marking a row done — format v2+)
- **[commands/import.md](commands/import.md):** Usage; Steps
- **[commands/list.md](commands/list.md):** Usage; Output format; View modes (`--view=`); Grouping (`--group-by=`); Multi-ledger scope (`--ledgers=` / `--all-ledgers`); Algorithm fallback (Python unavailable) — `--view`, `--group-by`, `--ledgers`/`--all-ledgers`; Terminal-aware rendering
- **[commands/list-preferences.md](commands/list-preferences.md):** Display-preference interview (`--fresh`); 🛑 The governing rule for EVERY question in this interview; Runtime execution: the `--fresh` flow, step by step; Persisting multi-ledger interview answers
- **[commands/show.md](commands/show.md):** Usage; What gets shown; How the synthesis is derived (mechanical, not model-generated); `--full`: the escape hatch; Failure modes; Algorithm fallback (Python unavailable); Interactive presentation (optional, environment-gated)
- **[commands/scan.md](commands/scan.md):** Where the ages come from; Staleness thresholds (default); Row-length (char-budget) lint (format v2+, maintenance §2c); Trivial-staleness cross-check (format v2+, deferral-gate §4d); Output structure; Recommendation values; Scheduling
- **[commands/branch.md](commands/branch.md):** Usage; The axis decision is YOURS; the write is the script's; Steps; The recall block (the 4th atomic artifact, when maintained); Auto-suggest (offer on a REPEATED pattern, never branch unilaterally); Backward compatibility
- **[commands/verify.md](commands/verify.md):** Usage; Steps; `/unforget verify --fix` (row-length splits only, format v2+, maintenance §2); Gate role; Backward compatibility
- **[commands/archive.md](commands/archive.md):** Why this exists; Usage; Safety rule (the important part): keep "Done-but-owed" rows; Steps; The archive file; The archive nudge (surfaced by `list` and `add`)
- **[commands/version.md](commands/version.md):** Output format; Version reconciliation; Install integrity; Recall trigger; Behavior; Repair an existing ledger's recall block
