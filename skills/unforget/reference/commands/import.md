# /unforget import

Part of the unforget command reference; the index is [../commands.md](../commands.md).

---

## /unforget import

Re-run the Phase 2 surface survey after `/unforget init` has already created the file. Useful when:

- New audit-tool runs have produced findings that should be captured
- A new `Deferred.md` or plan file appeared that wasn't there at init
- You want to run the Phase 6 deep-dump now that you didn't run at init
- You want to scan code comments (`--comments` flag) which init skipped by default

### Usage

```
/unforget import                         ·  re-run the standard survey (Phases 2 to 4 + 7)
/unforget import --comments              ·  include code comments (skipped by default)
/unforget import --deep                  ·  run the Phase 6 deep-dump questions
/unforget import --source=<path>         ·  survey a specific file or directory only
```

### Steps

Same as `/unforget init` Phases 2 to 4 and Phase 7 (see `reference/init.md` and `reference/surfaces.md` for the full surface specification), but operates against an EXISTING UNFORGET.md:

- New rows get appended with auto-assigned IDs (continuing the per-section sequence).
- Duplicate detection: if a survey row matches an existing UNFORGET.md row by similarity (fuzzy match on Finding text + source pointer), the skill flags it and asks whether to skip or import as a separate row.
- **Memory-dir pin maintenance:** the survey emits `pin_action` for Surface 6 (memory files). When `pin_action.action` is `write` (no pin present), patch `<!-- unforget-config: memory-dir=<encoded> -->` into UNFORGET.md directly under the `<!-- unforget-format: vN -->` marker as part of the same import write. When `pin_action.action` is `rewrite` (pin exists but resolved to a different encoded path), replace the existing marker line with the new value. When `pin_action.action` is `none`, leave the file alone. See `reference/surfaces.md` § Memory-dir config pin (post-resolution).
- The Phase 7 diff preview shows what's NEW, not the full file state.
- **Drift checks (format v2+):** `import` reconciles the registry against reality — this is the check set that would have caught the 2026-07-25 split-brain. Run `python3 scripts/import_drift.py --dir <ledger-dir> [--recall-file <CLAUDE.md/AGENTS.md>]` and report its findings most-severe first:
  - **registered-but-missing** (error) — a ledger in the registry not found on disk. Report the last-known path (`"MI-UNFORGET registered at <path> — not found; moved or deleted?"`) instead of silently proceeding. Turns a 20-minute "are they lost?" hunt into one line.
  - **found-but-unregistered** (warn) — a ledger-shaped file on disk (`*UNFORGET*.md`, `TERRY-*`, `MI-*`) not in the registry → **offer to register it**. This is the check that surfaces a stranded parallel-tree ledger.
  - **posture-mismatch** (warn) — a ledger whose actual git-tracked state disagrees with its registered `git_posture` (e.g. registered `ignored` but git tracks it) → flag.
  - **stale-recall** (warn, maintained policy) — a required block is stale, absent, malformed or unreadable. Resolve the configured `recall_file` or use `--recall-file`; offer the import repair path. Manual/none policies are not maintenance failures.
  The helper is **read-only** — it reports; you walk the fixes with the user (register the stranded file, rewrite the recall block, correct the posture). Exit 1 means drift was found. See `reference/init.md` § Phase 6b migration and `reference/registry.md`.
- **Recall-block maintenance (format v2+):** when the registry's recall mode is `maintained`, after importing new rows or registering a found ledger, refresh the Deferred Work Index block: `python3 scripts/recall_block.py write --file <recall-file> --dir <ledger-dir>`. It rewrites only between its markers; the user's surrounding content is untouched. This is what keeps the block from rotting between sessions.
- **Branch auto-suggest (format v2+):** after importing, if the newly-added rows reveal a repeated pattern that clears the `reference/branching.md` §3 cascade to "new ledger" for **≥2 related items** (same actor / lifespan-scope / subject cluster), `import` may *offer* a `/unforget branch` — naming the pattern it saw, never branching unilaterally, at most once per pattern. `import` is the more likely place to catch this than `add`, since it surfaces a batch at once (e.g. several stranded ledgers or a cluster of user-only findings). See `/unforget add` § Branch auto-suggest and `reference/branching.md` §6.

`/unforget import` is the second-most-important command after `/unforget add`. It's how the skill stays current with the project's evolving deferral surfaces.
