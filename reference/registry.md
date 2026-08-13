# The registry: the re-read source of truth

> Authoritative spec for where ledgers live, the git posture, and the persisted
> policies (Onboarding & Registry design spec §3). The registry exists so the
> skill NEVER re-guesses a location, posture, or policy — and never loses a
> sibling ledger. Everything the skill relies on lives in a re-read record, not
> in an assistant's memory (memory drifts; a stranded ledger once got reported
> "missing" because there was no registry to name it).

## Where it lives

In the ledger directory itself, alongside the ledgers it describes:

- **`README.md`** — holds the CANONICAL registry, in a marker-delimited block.
- **`.unforget.json`** — an OPTIONAL machine cache (regenerable from the README).

Under the Split git posture the `README.md` is the one tracked artifact and the
`.unforget.json` is gitignored as a cache.

## The canonical form: a block in README.md

The skill owns exactly one delimited block; it rewrites ONLY between the markers
and never touches the surrounding human prose:

```markdown
<!-- unforget-registry:begin -->

### unforget registry

**Global**

| key | value |
|---|---|
| git_posture | split |
| recall_block | maintained |
| recall_file | CLAUDE.md |
| policy_deferral | aggressive |
| policy_multiaxis | lifespan-wins |
| ratio_flag_threshold | 3 |
| stale_trivial_sessions | 2 |

**Ledgers**

| name | path | role | axis | discipline | parent | death |
|---|---|---|---|---|---|---|
| UNFORGET.md | UNFORGET.md | main | — | standard-10col | — | — |
| TERRY-UNFORGET.md | TERRY-UNFORGET.md | child | actor | standard-10col | UNFORGET.md | — |
| MI-UNFORGET.md | MI-UNFORGET.md | child | lifespan | capped-evict | UNFORGET.md | Phase 6 ships |

<!-- unforget-registry:end -->
```

## The schema (§3a)

**Global** (one per registry):

| key | values |
|---|---|
| `git_posture` | `ignored` \| `committed` \| `split` |
| `recall_block` | `maintained` \| `manual` \| `none` |
| `recall_file` | path to the CLAUDE.md / AGENTS.md carrying the recall block |
| `recall_home` | display path shown as the recall block's "Ledger home"; persisted so `recall_block.py check` re-renders an identical block (writer/checker agree) |
| `policy_deferral` | `aggressive` \| `conservative` \| `same-file-only` (deferral-gate Policy 1) |
| `policy_multiaxis` | `lifespan-wins` \| `actor-wins` \| `nearest-death` (branching Policy 2) |
| `ratio_flag_threshold` | integer; deferral-gate defer/fix ratio flag (default 3) |
| `stale_trivial_sessions` | integer; deferral-gate aging cross-check (default 2) |
| `row_char_budget` | integer; row-length index budget per Finding/Status cell (default 400; `scan`/`verify`/`row_budget.py`) |
| `display_view` | `all` \| `open` \| `done` \| `split` \| `next`; saved `list --view=` default (§ Display-preference interview) |
| `display_group_by` | `target` \| `section` \| `none`; saved `list --group-by=` default |
| `display_verbosity` | `auto` (default — keep terminal-width auto-detection) \| `full` \| `compact`; saved column-width preference. `full`/`compact` PIN the width, overriding auto-detect |
| `display_sections` | `all`, or ONE of `paused` \| `spillover` \| `audit` \| `observed`; saved `--section=` default. Single-or-all only — `--section=` does not accept a list |
| `display_prefs_set` | `true` \| `(unset)`; whether the display-preference interview has ever completed (distinct from the fields above being absent, which can also mean "asked, declined to set") |
| `archive_nudge_threshold` | integer; completed-row count at which `list`/`add` append the archive nudge (default 5; `0` silences it). See `reference/commands.md` § The archive nudge |
| `stale_days_this` | integer; days before an Open/In-Progress row is stale (default 30). See `reference/commands.md` § Staleness thresholds |
| `stale_days_next` | integer; days before a Deferred 🔵 NEXT row is stale (default 90) |
| `stale_days_later` | integer; days before a Deferred 🟡 LATER row is stale (default 180) |
| `stale_days_someday` | integer; days before a Deferred ⚪ SOMEDAY row is stale (default 365) |

**Migration note (2026-08-13).** `archive_nudge_threshold` and the four `stale_days_*` keys were
previously specified as living in a `config` block at the top of UNFORGET.md. They now live
here, in the registry, alongside every other tunable. The move was safe: **no reader was ever
implemented for them** (the only `<!-- unforget-config: ... -->` marker any script parses is
`memory-dir`, in `scan_surfaces.py`), and no ledger was found carrying them. Readers SHOULD
still honor a legacy in-file config block if one exists, preferring the registry when both are
present — cheap insurance for a ledger not surveyed here, not a long-term dual-store contract.

**Per ledger** (one row each):

| column | meaning |
|---|---|
| `name` | filename (e.g. `UNFORGET.md`) |
| `path` | absolute or dir-relative path |
| `role` | `main` \| `child` |
| `axis` | children only: `actor` \| `lifespan` \| `domain` |
| `discipline` | `standard-10col` \| `capped-evict` \| … |
| `parent` | children only: the parent ledger's name |
| `death` | lifespan children only: the end condition |

Unknown global keys are **preserved** on a read/write cycle (a newer skill's keys
survive an older one's round-trip), never silently dropped.

## README-canonical rule (§3b) — the important invariant

- The **README block is canonical.** It is human-readable and hand-editable.
- The **`.unforget.json` is a cache**, regenerable from the README.
- **If the two disagree, the README wins** — a human edited it, and the human is
  authoritative. This avoids the classic "the JSON drifted from the doc, which
  is real now?" failure. The cache is a speed optimization, never a second
  source of truth.

So: read from the README; use the cache only as a fast path when it is in sync;
regenerate the cache after any README change.

## Preferred implementation

```
python3 scripts/registry.py read  --dir <ledger-dir>            # emit registry JSON (README canonical)
python3 scripts/registry.py write --dir <ledger-dir> --json <f> # REPLACE the block + regenerate the cache
python3 scripts/registry.py write --dir <ledger-dir> --json <f> --merge  # PATCH: unmentioned keys survive
python3 scripts/registry.py check --dir <ledger-dir>            # report README-vs-cache drift
```

- `read` returns `{block_present, global, ledgers, advisory}`. Exit 1 (not an
  error) when no block exists yet — the dir has a human README but no registry;
  init/import creates one.
- `write` takes a JSON `{global, ledgers}`, rewrites ONLY the marker block
  (human prose untouched), and regenerates the cache in normalized form so a
  fresh write is always in sync.
- **`write --merge` is PATCH semantics and is REQUIRED for any partial write.** Keys present in
  the payload win (an explicit null clears them); keys absent keep their current value; a
  payload with no `ledgers` key leaves the ledger table untouched. Without `--merge`, `write`
  REPLACES the block wholesale — a one-key payload therefore unsets every other global key **and
  empties the Ledgers table**. Measured 2026-08-13 against a 9-key/3-ledger registry: a bare
  `{"global": {"display_view": "open"}}` write left 9 nulls and **0 registered ledgers**. Any
  caller writing fewer than all keys (the display-preference interview, a single policy change)
  must pass `--merge`; full-state writers (`init`, `branch`) may use either.
- `check` returns `cache_in_sync` (or `null` when there's no cache) and always
  reports `source_of_truth: "readme"`. Drift → exit 1 → regenerate the cache
  from the README.

**Algorithm fallback** (Python unavailable): find the text between
`<!-- unforget-registry:begin -->` and `<!-- unforget-registry:end -->` in
`README.md`. Parse the `**Global**` `| key | value |` table into config and the
`**Ledgers**` table into rows. Treat empty/`—` as null. On any README-vs-cache
disagreement, trust the README and rewrite the cache.
