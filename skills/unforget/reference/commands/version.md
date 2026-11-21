# /unforget --version

Part of the unforget command reference; the index is [../commands.md](../commands.md).

---

## /unforget --version

Print the installed skill's version, install path, format-version support, **install integrity**, and (when run in a project) the **recall-trigger status**. Useful for verifying a fresh install loaded correctly without running `init` against a real project.

### Output format

```
unforget v2.6.0
Install path: <detected at runtime>  (Claude Code plugin)
Supported format-version: v1, v2
Subcommands: init, add, edit, import, list, scan, branch, verify, archive, promote, --version
Install integrity: ✓ all companion files reachable
Version declarations: ✓ all 5 sites agree (2.7.0)
Recall trigger: ✓ installed in CLAUDE.md
```

(The exact companion-file count is whatever `verify_install.py`'s `REQUIRED_COMPANIONS` list holds — report the count it returns, not a hardcoded number.)

When the install is broken or the recall trigger is missing, the last two lines carry the diagnosis instead:

```
Install integrity: ✗ 2 companion files unreachable (reference/commands.md, scripts/scan_surfaces.py)
                     → the router will fail when it delegates to a missing file; reinstall or repair the skill directory
Recall trigger: ✗ no Deferred Work Index block in this project's CLAUDE.md/AGENTS.md
                  → deferred-work questions will NOT auto-route here; run /unforget import to repair an existing ledger (init only for bootstrap)
```

The version string is read from SKILL.md frontmatter `metadata.version` (legacy top-level `version` remains readable). Detect the actual loaded skill directory at runtime for either host, including plugin installs and symlinked checkouts; do not assume a Claude-only path. Supported format-version comes from the spec (currently `v1` and `v2`, backward compatible; a future `v3` would list here too once it lands).

### Version reconciliation

The version is reconciled across **six** possible declarations: `SKILL.md`'s frontmatter, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the newest `### vN.N.N` heading in root `CHANGELOG.md` (legacy fallback: SKILL.md), the README's shields.io badge cache-buster (`&v=N.N.N`), and the README's `**Maturity:** vN.N.N` bullet. Nothing used to compare them, so the plugin manifest sat **five releases stale** (2.1.0 while everything else read 2.6.0) with no check noticing — found 2026-08-13, the third instance of doc-vs-code drift in a single session (the others: the changelog describing `verify` checks the code didn't implement, and a test golden pinned to an old version).

The two README sites were added after the first pass shipped covering only three: bumping to 2.7.0 still required hand-grepping the README, which is precisely the manual step this check exists to eliminate. A check that covers most of the sites still leaves the release manual.

`--version` now reconciles all declared sources and reports `versions_in_sync` + `declared_versions`. Rules:

- **Only sources that actually declare a version vote.** A manual (v0.1) install with no plugin manifest is not drift — it simply has one fewer declaration. Same for an unparseable manifest, or a README with no badge/Maturity line: undeclared, never a crash.
- **The README patterns are deliberately narrow**, anchored to the badge URL and the literal `**Maturity:**` bullet. Ordinary prose mentioning `v1.0.3` or "upgrading from 2.4.0" is NOT a declaration and must not be read as one — verified against a README containing exactly those strings.
- **SKILL.md's frontmatter is canonical**, because that is what `read_version` — and therefore the `unforget vN.N.N` line above — already reports.
- **Drift is ADVISORY, never a failure.** A stale manifest misreports what is installed; unlike a missing companion file it does not break the router, so it does not fail the command (exit stays 0). A missing companion still exits 1 and still outranks drift in the advisory line.

The line reads `Version declarations: ✗ SKILL.md declares 2.6.0, but plugin_manifest=2.1.0` when they disagree — naming the offending source and both values, so the fix is obvious without hunting.

### Install integrity

The refactored skill (v0.2+) is a thin SKILL.md router that delegates to `reference/*.md` on demand and to `scripts/*.py` for deterministic work. If those companion files did not travel with the install — a copy of only SKILL.md, a partial clone, a broken symlink — the router fails silently the first time it reads a reference file, and the failure surfaces as confusing mid-command behavior rather than a clear error.

`--version` closes that gap. **Preferred implementation:** delegate to `python3 scripts/verify_install.py --skill-root <dir> [--project-root <cwd>]` (returns JSON). It confirms every companion file the router depends on is reachable from the skill root, and — when `--project-root` is supplied — reports whether the recall trigger is installed. Report `integrity_ok` and `advisory` to the user on the two output lines above.

Algorithm fallback if Python is unavailable: for each path in the router's companion table (`reference/format.md`, `reference/init.md`, `reference/surfaces.md`, `reference/promotion.md`, `reference/commands.md` and each file in `reference/commands/`, and the runtime helpers listed in `scripts/verify_install.py`), test existence relative to the skill root; report any that are missing.

### Recall trigger

unforget only auto-activates on "what's deferred?"-style questions when the project's `CLAUDE.md` / `AGENTS.md` carries a **Deferred Work Index** block pointing at UNFORGET.md (see `## How to use unforget alongside CLAUDE.md / AGENTS.md` in SKILL.md, and `reference/init.md` for the block itself). Without it, a populated ledger sits invisible and the skill looks broken when it is working as designed.

When `--version` runs inside a project directory, it scans `CLAUDE.md`, `.claude/CLAUDE.md`, and `AGENTS.md` for the block and reports `✓ installed in <file>` or `✗ missing` with the fix (`run /unforget import` for an existing ledger; `init` only for bootstrap). When run from a non-project directory (no `--project-root`), this line is omitted rather than reported as a failure.

### Behavior

- Read-only. Touches no files.
- Always succeeds as a *command* even when it reports a broken install: the integrity/recall lines are diagnostic content, not a command error. The only true non-response is the skill failing to load at all (in which case nothing prints, which is itself the signal the install did not take).
- Version, format-version, and integrity checks work from any directory. The recall-trigger line requires a project context; it is silently skipped otherwise.

After install, the user has no way to verify the skill loaded short of trying to use it. `/unforget --version` provides a no-side-effect health check. If the command does not respond, the install did not take. If it responds with the wrong version, the user knows to update before running `init` against a real project. If it responds with an integrity ✗, the user knows the companion files did not travel with the install before a single row is written.

### Repair an existing ledger's recall block

For an existing ledger, use `/unforget import` (Codex: `$unforget import`) to reconcile the
actual registry and repair only its authorized recall block. Do not rerun onboarding.
Read `registry.py read --dir <ledger-dir>`, confirm the configured maintained `recall_file`,
then run `recall_block.py write --dir <ledger-dir> --file <resolved-recall-file>` and
`import_drift.py --dir <ledger-dir> --recall-file <resolved-recall-file>` to verify the repair.
The ledger and unrelated instruction text remain untouched. Malformed markers require
explicit correction before the write; absent markers permit appending a new block.
`init` still refuses when a ledger already exists; reserve it for genuine bootstrap.
