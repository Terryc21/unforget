# unforget scripts/

Deterministic helpers invoked by `SKILL.md` and `reference/*.md` prose. Each script reads JSON or a path argument and writes structured JSON to stdout. Errors go to stderr with a non-zero exit code.

**Design constraints (all scripts):**

1. **Python standard library only.** No `pip install` required. Imports are limited to `json`, `sys`, `os`, `re`, `pathlib`, `argparse`, `typing` (and equivalents). The format-v2 scripts (`parse_status.py`, `registry.py`, `verify_ledger.py`, `defer_tally.py`) use `X | None` type-union syntax and require **Python 3.10+**; the older v1 helpers run on 3.9+.
2. **JSON in / JSON out.** Each script reads a path or stdin and writes structured JSON to stdout. The LLM parses the JSON; it does not re-derive the algorithm.
3. **Pure where possible.** No global state, no side effects beyond what each CLI advertises. `prune_backups.py` deletes files; the rest are read-only.
4. **Algorithm fallback in prose.** When Python is unavailable, each `reference/*.md` file that delegates to a script keeps an "Algorithm fallback" paragraph. The fallback is functional but slower and non-deterministic.

## Scripts

| Script | Purpose | Used by |
|---|---|---|
| `encode_project_path.py` | Encode an absolute path to Claude Code's per-project memory-dir name (slash → dash, whitespace → dash, leading dash). | `reference/surfaces.md` § Surface 6 |
| `scan_surfaces.py` | Scan a project root for deferred-work artifacts across the six surfaces + Surface 1b. Read-only. Pass `--unforget-md <path>` to enable memory-dir pin resolution and emit `pin_action` for Surface 6. | `reference/init.md` Phase 2; `reference/commands.md` § `/unforget import` |
| `dedup_findings.py` | Fuzzy-merge duplicate candidate findings across surfaces (Jaccard on tokenized headlines). | `reference/surfaces.md` § Cross-surface deduplication |
| `check_format_version.py` | Read `<!-- unforget-format: vN -->` marker; report whether the skill can write or must operate read-only. | `SKILL.md` § Format-version contract |
| `prune_backups.py` | Backup rotation. Lists `UNFORGET.md.bak-YYYY-MM-DD-HHMMSS`, sorts by timestamp, deletes any beyond the most recent N (default 5). | `reference/promotion.md` § Retention |
| `verify_install.py` | Verify companion-file integrity (all `reference/*.md` + `scripts/*.py` reachable) and report recall-trigger status. | `reference/commands.md` § `/unforget --version` |
| `check_header_order.py` | Lint every UNFORGET-ledger table header in a tree for canonical core-column order (Target before Finding before …). Read-only. Tolerates abbreviations, appended extra columns, and preset omissions; skips non-ledger tables (roadmap/feedback docs). | `tests/run.sh` (repo invariant) |
| `parse_status.py` | (format v2+) Parse a row's `@status`/`@verified` tokens; validate the tier rule and detect a token↔narration contradiction; report `archivable`/`blocks_release`. Read-only. | `reference/status.md`; `list`/`archive`/`edit` |
| `registry.py` | (format v2+) Read/write the registry (README-canonical block + `.unforget.json` cache); report cache-vs-README drift. README wins on disagreement. | `reference/registry.md` |
| `verify_ledger.py` | (format v2+) Run the integrity lint (contradiction, tier, unknown-value, THIS-blocker, char-budget, stale-recipe, registry drift); return a severity-ranked finding list and a gate pass/fail. Read-only. | `reference/verify.md`; before `archive`/`promote` |
| `defer_tally.py` | (format v2+) The deferral gate's deterministic half: route a would-be deferral (trivial tripwire + why-not-now allow-list) and keep the per-session defer/fix tally with the defer-heavy flag. Writes the ephemeral `.unforget-session.json` state file. | `reference/deferral-gate.md`; `/unforget add`, `list` |
| `branch_create.py` | (format v2+) Atomically create a child ledger — scaffold the child header, write the parent's pointer row, register the child, and (when maintained) update the recall block, all-or-none (rolls back on any failure). Guards refuse a duplicate name / a lifespan child with no death condition / an unconfirmed non-human actor. Reuses `registry.py` + `recall_block.py`. | `reference/branching.md`; `/unforget branch` |
| `recall_block.py` | (format v2+) Write/read/update the maintained Deferred Work Index block in CLAUDE.md/AGENTS.md, rendered from the registry. Rewrites only between its markers; `check` reports staleness vs the registry. | `reference/init.md`; `/unforget init`, `import`, `branch` |
| `import_drift.py` | (format v2+) Reconcile the registry against reality — registered-but-missing, found-but-unregistered, posture-mismatch, stale-recall. Read-only; severity-ranked findings. Reuses `registry.py` + `recall_block.py`. | `reference/init.md`; `/unforget import` |
| `row_budget.py` | (format v2+) Row-length discipline: `check` flags Finding/Status cells over the char budget (registry `row_char_budget`, default 400); `split` produces a bounded index row + a detail-block bullet holding the full content verbatim — lossless-verified, refuses any split it can't prove preserves every character. | `reference/format.md` § Row-length discipline; `/unforget scan`, `verify --fix` |
| `companions.py` | (format v2+) Companion-skill handoffs: read/write the GLOBAL manifest (5 fixed functions → user-owned skill/invoke/url), `resolve` a function to its install-state expression (detection by INVOCABLE name passed via `--invocable`, never a dir find), `rotcheck` for entries neither installed nor reachable. | `reference/skill-handoffs.md`; `/unforget edit --status=done`, `promote`, `verify` |

## Invoking from the skill

Each subcommand spec in `reference/*.md` includes a "Preferred implementation" line that points at the script and an "Algorithm fallback" paragraph for environments without Python 3. The pattern is:

```
To <do thing>, run `python3 scripts/<name>.py <args>` and parse the JSON.
Algorithm fallback if Python is unavailable: see `reference/<file>.md` § Algorithm fallback.
```

## Running standalone

The scripts are usable outside Claude Code (CI, GitHub Actions, cron):

```bash
# Validate a project's UNFORGET.md format version
python3 scripts/check_format_version.py /path/to/UNFORGET.md

# Discover deferred-work artifacts across a project
python3 scripts/scan_surfaces.py --root /path/to/project

# Discover artifacts AND get a pin_action for Surface 6 memory-dir
python3 scripts/scan_surfaces.py --root /path/to/project --unforget-md /path/to/UNFORGET.md

# Pipe scan output through dedup
python3 scripts/scan_surfaces.py --root . | python3 scripts/dedup_findings.py --candidates -

# Rotate backups
python3 scripts/prune_backups.py --keep 5 --dir /path/to/UNFORGET.md/dir
```

All scripts support `--help`.

## Tests

A self-test corpus (`tests/fixtures/`) is queued for a future v0.3 cycle (item #3 in `v0.3-feedback.md`). Until then, smoke tests are run manually against the real Stuffolio repo (`/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio`), which has 44 active deferred rows across the six surfaces.
