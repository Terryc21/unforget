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
python3 scripts/registry.py write --dir <ledger-dir> --json <f> # rewrite the block + regenerate the cache
python3 scripts/registry.py check --dir <ledger-dir>            # report README-vs-cache drift
```

- `read` returns `{block_present, global, ledgers, advisory}`. Exit 1 (not an
  error) when no block exists yet — the dir has a human README but no registry;
  init/import creates one.
- `write` takes a JSON `{global, ledgers}`, rewrites ONLY the marker block
  (human prose untouched), and regenerates the cache in normalized form so a
  fresh write is always in sync.
- `check` returns `cache_in_sync` (or `null` when there's no cache) and always
  reports `source_of_truth: "readme"`. Drift → exit 1 → regenerate the cache
  from the README.

**Algorithm fallback** (Python unavailable): find the text between
`<!-- unforget-registry:begin -->` and `<!-- unforget-registry:end -->` in
`README.md`. Parse the `**Global**` `| key | value |` table into config and the
`**Ledgers**` table into rows. Treat empty/`—` as null. On any README-vs-cache
disagreement, trust the README and rewrite the cache.
