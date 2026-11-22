# tests/: unforget self-test suite

`bash tests/run.sh` runs everything below that doesn't need a language model. It needs only
`bash` and `python3` (3.9+): no pytest, no third-party packages. It prints `PASS:` per check
and ends with `All tests passed.`, or exits 1 with a diff or the failing test's output.

```bash
bash tests/run.sh
```

The suite has four layers:

1. **Golden diffs.** A helper script runs against a frozen fixture, its JSON is normalized,
   and the result is diffed against a file in `golden/`.
2. **Repo-wide checks.** Pass/fail rules over the whole repo, with no snapshot to drift.
3. **Unit tests.** One `test_*.py` per area, each runnable on its own.
4. **The behavioral corpus** in [`behavioral/`](behavioral/), which tests the prose the
   model follows (`add`, `edit`, `promote`, format-version handling) by structural assertions
   rather than exact diffs. `run.sh` runs its checker selftest and checks any results already
   produced; the model-driven half is run by hand, per [`behavioral/README.md`](behavioral/README.md).

The suite exists because the v0.2 Phase 4 retest caught three real bugs (T-8 path encoding,
T-12 audit-filename pattern, T-13 per-finding-ID extraction) only because the author walked
a real project by hand. These checks catch that class of bug on commit instead.

## 1. Golden diffs

| Helper | Golden | What it covers |
|---|---|---|
| `scripts/scan_surfaces.py` | `golden/scan_surfaces.json` | Run with `--include-comments` over `fixtures/sample-project/`. Surface 5 reports `not-a-git-repo`, since the fixture has no `.git/`. Surface 6 (memory files) is cleared during normalization, because the helper finds that folder from the runner's own working directory. |
| `scripts/check_format_version.py` | `golden/check_format_version.json` | The fixture's `UNFORGET.md`: its format marker and section headers. |
| `scripts/encode_project_path.py` | `golden/encode_project_path.json` | A fixed path string, so the result doesn't depend on the runner's disk. Pins the T-8 encoding rule. |
| `scripts/dedup_findings.py` | `golden/dedup_findings.json` | `fixtures/dedup-input.json`: two near-duplicate headlines merge and two distinct findings stay apart. |
| `scripts/verify_install.py` | `golden/verify_install.json` | Run with `--skill-root` only (no `--project-root`, so the recall check is skipped and the golden stays stable). Every companion file the skill names resolves (51 as of 11/22/2026), and the version agrees across all the places it's declared. `skill_root` is normalized to `<REPO_ROOT>`. |

### Re-baselining

When a helper's output changes on purpose, regenerate the goldens and read the diff before
committing it:

```bash
bash tests/run.sh --bless
git diff tests/golden/
```

A golden blessed without review brings back exactly the kind of bug these files exist to
catch.

### Why JSON, not the report a person sees

The candidate report shown to users is markdown the model writes from `scan_surfaces.py`'s
JSON, and its wording varies from session to session. Diffing the JSON exercises every
heuristic, filename pattern, regex and exclusion without tying the suite to prose that is
allowed to change.

## 2. Repo-wide checks

| Check | What it asserts |
|---|---|
| `scripts/check_header_order.py --root <repo>` | Every ledger table header in the repo lists its core columns in canonical order (`#`, `Target`, `Finding`, `Urgency`, …). It checks relative order, so abbreviated headers, extra columns appended after Status and the Lean preset all pass, and tables that aren't ledgers are skipped. Guards against a fixture that once swapped Target and Finding. |
| Example as fixture (inline in `run.sh`) | `examples/UNFORGET.md` is read as a real v2 ledger: it must be recognized as v2, every row must parse a `@status` token with no integrity issues, and cell reads must survive the columns appended after Status and the Compact preset. |
| `behavioral/run-behavioral.sh --selftest`, `--check` | The behavioral checker works, and any results already produced still pass. |
| `.claude-plugin/verify-manifest.sh` | `plugin.json` parses, its name matches `SKILL.md`, and the version and description agree across `SKILL.md`, `plugin.json` and `marketplace.json`. |

## 3. Unit tests

Each file runs on its own, for example
`python3 -m unittest discover -s tests -p test_set_aside.py`. Tests that write files work in
temporary directories; none touches a real ledger, a real memory folder or the network.

| File | What it covers |
|---|---|
| `test_row_visibility.py` | Every row in a ledger is seen by the parser, and the cell-count check catches rows with the wrong number of cells. |
| `test_html_report.py` | What the HTML report does, not its wording: which rows block release, that a status quoted in a Finding isn't read as the row's status, that malformed and duplicate rows are refused, that unknown statuses stay visible, and the sort order. |
| `test_skill_version.py` | The installed version is read from `SKILL.md`'s metadata first, falls back to the older release field, and ignores unrelated version strings. |
| `test_review_regressions.py` | Regressions from an earlier review of unforget (its findings are numbered F1, F4, …): managed writes and rollback, closing and splitting rows, recipes, memory containment, scope and recall, packaging and format controls. |
| `test_parked_marker.py` | `@parked` changes no row's status, release gating or `verify` result; a parked THIS row still blocks release. |
| `test_set_aside.py` | Setting rows aside by likelihood: who may set a row aside, the `@basis` rules, `verify`'s checks, the report, the session tally, `set_aside.py convert` (including filling the Likelihood column), and the row-length budget. |
| `test_archive_file.py` | Each ledger has one archive file, named in one place. |
| `test_companions.py` | `companions.py init --force` never damages text outside its managed block. |
| `test_prune_backups.py` | `prune_backups.py` keeps the newest N backups, deletes nothing in `--dry-run`, never touches look-alike files, and refuses `--keep 0`. |
| `test_ledger_moves.py` | `ledger_backup.py` (one backup contract: never overwrite, keep five, atomic writes that keep the file's mode) and `move_ledger.py` (a move removes the original only after the copy is proven byte-identical). |
| `test_start_accounting.py` | Rows a session starts on its own are recorded and tallied, and `verify` lists parked rows waiting for the user. |
| `test_row_age.py` | `row_age.py` dates rows from git history, falls back to dates written in the row, and lists rows it can't date instead of guessing. |
| `test_command_refs.py` | Every reference to the split command spec (`reference/commands/<command>.md`) names a file and heading that exist. |
| `test_github_surface.py` | The GitHub issue survey matches any deferral label, reads only the `origin` remote, and finds the repository from a linked worktree or a submodule. One live check against GitHub runs only with `GH_LIVE=1`. |

## Not covered

- **Surface 6 (memory files).** Testing it needs either a `--memory-dir` flag on
  `scan_surfaces.py` or a mock `~/.claude/projects/` tree in the fixture. Neither exists, so
  the golden leaves Surface 6 out.
- **The live GitHub query.** The suite never calls `gh` unless `GH_LIVE=1` is set.

## File layout

```
tests/
├── README.md                     this file
├── run.sh                        the harness
├── normalize.py                  JSON normalizer for the golden diffs
├── test_*.py                     unit tests (table above)
├── behavioral/                   behavioral corpus: 7 cases, checker, runner
├── fixtures/
│   ├── dedup-input.json          input for dedup_findings
│   └── sample-project/           a synthetic project for scan_surfaces
│       ├── Deferred.md                                  Surface 1: redirect
│       ├── Documentation/Development/UNFORGET.md        Surface 1: target
│       ├── scratch/audit-concurrency-2026-05-02.md      Surface 2: severity tiers
│       ├── scratch/audit-data-model-2026-05-02.md       Surface 2: per-finding IDs
│       ├── .claude/plans/paused-migration-plan.md       Surface 3: paused plan
│       └── Sources/SampleManager.swift                  Surface 4: TODO/FIXME/HACK/MIGRATION-NOTE
└── golden/
    ├── check_format_version.json
    ├── dedup_findings.json
    ├── encode_project_path.json
    ├── scan_surfaces.json
    └── verify_install.json
```
