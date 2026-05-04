# unforget scripts/

Deterministic helpers invoked by `SKILL.md` and `reference/*.md` prose. Each script reads JSON or a path argument and writes structured JSON to stdout. Errors go to stderr with a non-zero exit code.

**Design constraints (all scripts):**

1. **Python 3.9+ standard library only.** No `pip install` required. Imports are limited to `json`, `sys`, `os`, `re`, `pathlib`, `argparse`, `typing` (and equivalents). The skill must run on any machine with Python 3.9+.
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
