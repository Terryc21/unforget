# Continuation prompt — unforget v0.3-feedback work

**Last session ended:** 2026-05-04
**Branch:** `main` (4 commits ahead of `origin/main`; #6 mid-flight in working tree will become a 5th once committed)

---

## Paste this prompt into the next Claude Code session

> I'm continuing v0.3-feedback work on the unforget skill at `/Volumes/2 TB Drive/Coding/GitHub/unforget`. Eight items shipped across the last session (#1, #11, #12, #0, #13, #14, #15, #7, #9 + Continuous-preset smaller fix), spread across these commits:
>
> - `6c84d50` #1 progressive-disclosure tiering
> - `e2c6144` #11 scripts/ directory
> - `2dfba3f` #12 frontmatter strip
> - `c0fe867` #0 Compact preset
> - `866218a` #13 + #14 + #15 cross-promo gate + README + tracker section
> - `08419c7` #7 + #9 + Continuous-preset header smaller fix
>
> **Pending uncommitted work — item #6 (persist memory-dir to config comment), spec done, code in progress.**
>
> Working tree has these modified files:
> - `reference/surfaces.md` — adds the "Memory-dir config pin (post-resolution)" subsection under Surface 6. **Spec is complete.**
> - `scripts/scan_surfaces.py` — adds `MEMORY_DIR_PIN_RE`, `read_memory_dir_pin()`, refactors `scan_memory_files(root)` → `scan_memory_files(root, unforget_md=None)` with three-tier resolution (pin → cwd-encoded → ancestor walk), wires `--unforget-md <path>` flag. Returns a new `pin_action` field per memory_files surface. **Code is complete and smoke-tested.**
>
> **Smoke test verified before stopping:**
> ```
> cd /Volumes/2\ TB\ Drive/Coding/GitHubDeskTop/Stufflio
> python3 /Volumes/2\ TB\ Drive/Coding/GitHub/unforget/scripts/scan_surfaces.py --root . --unforget-md Documentation/Development/Deferred/UNFORGET.md
> ```
> Returned `pin_action: {action: write, encoded: -Volumes-2-TB-Drive-Coding-GitHubDeskTop, reason: no pin present; caller should write one}`. The script correctly resolved through the ancestor walk (Stuffolio's memory lives under the parent's encoded dir) and signals the caller should write the pin.
>
> **What still needs to happen for #6 to close:**
> 1. `scripts/README.md` — the `scan_surfaces.py` row in the script table needs the new `--unforget-md` flag mentioned. Same for the "Running standalone" example block.
> 2. `reference/init.md` Phase 7 — when init writes UNFORGET.md, it should include `<!-- unforget-config: memory-dir=<encoded> -->` directly under the format-version marker IF Surface 6 found files (i.e., `pin_action.action != "none"`). Add a sentence to Phase 7 step 1 describing this.
> 3. `reference/commands.md` `/unforget import` — when import re-resolves and `pin_action` returns `write` or `rewrite`, the LLM should patch the marker into UNFORGET.md as part of the import write. Add a sentence noting this.
> 4. Smoke-verify against Stuffolio one more time, then commit as `feat(spec+scripts): persist memory-dir to config comment (#6)`.
>
> **Then stop.** The remaining items (#3 test corpus, #4 doctor, #5 detail-block convention, #8 promotion history, #2 migrate, #10 fresh) each warrant their own session per the recommended ordering in `v0.3-feedback.md`.
>
> Read `v0.3-feedback.md` (untracked in repo root) and `CONTINUATION-2026-05-04.md` (this file) for full context. The `v0.3-feedback.md` line numbers are stale post-#1 split — work from the file structure, not the line refs.
>
> Run preferences from memory: never use em dashes (use colons or restructured sentences); commits go through GitHub Desktop ⌘P normally, but CLI override applies for this skill-writing session if I confirm.

---

## Quick reference (next-session orientation)

### Repo state at end of last session

```
SKILL.md                            163 lines  (was 907 pre-#1)
reference/format.md                 129 lines
reference/init.md                   285 lines
reference/surfaces.md               180 lines  (UNCOMMITTED — pin spec added)
reference/promotion.md              134 lines
reference/commands.md               300 lines
scripts/scan_surfaces.py            ~545 lines (UNCOMMITTED — pin logic added)
scripts/encode_project_path.py      56 lines
scripts/dedup_findings.py           193 lines
scripts/check_format_version.py     120 lines
scripts/prune_backups.py            103 lines
scripts/README.md                   53 lines
README.md                           393 lines  (was 354 pre-#14)
```

### Items shipped this session, in order

| # | Title | Commit |
|---|---|---|
| 1 | Progressive-disclosure tiering (SKILL.md split) | `6c84d50` |
| 11 | `scripts/` directory (5 Python helpers) | `e2c6144` |
| 12 | Strip frontmatter description | `2dfba3f` |
| 0 | Compact preset (9-col, inlined Target badge) | `c0fe867` |
| 13 | Cross-promotion gate (once-per-project marker) | `866218a` |
| 14 | README structure overhaul | `866218a` |
| 15 | Tracker-coexistence section (Jira/Linear/GitHub) | `866218a` |
| 7 | Cross-skill version pinning | `08419c7` |
| 9 | Terminal-aware list rendering | `08419c7` |
| Continuous header fields | Smaller fix | `08419c7` |

### Items remaining

Per `v0.3-feedback.md` recommended landing order:

| # | Title | Why next | New session? |
|---|---|---|---|
| 6 | Persist memory-dir to config comment | **In progress, spec + code done; needs 3 doc patches + commit (~10 min)** | No — finish in next session immediately |
| 3 | Self-test corpus (`tests/fixtures/`) | Tests the 5 scripts from #11 | YES — different mental mode (test infra) |
| 4 | `/unforget doctor` artifact health check | Verifies #2 + #8 once they land | YES — new subcommand spec |
| 5 | Detail-block length convention + `--detail` edit flow | Independent | Could pair with #6 if light |
| 8 | Structured promotion history | Pairs with v0.3 F1 archive policy (waits) | After F1 lands |
| 2 | `/unforget migrate` | Waits on v0.3 T1 (Wake-up field) | After T1 lands |
| 10 | Spec or retire `/unforget fresh` | Waits on v0.3 C2 (retired-ID tracking) | After C2 lands |

### Working preferences from memory

- **Em dashes:** Never use them. Use colons or restructured sentences. Inherited em dashes in pre-existing prose (Terry's voice in original SKILL.md / README.md) are NOT being scrubbed; only newly-authored prose follows the rule.
- **Stufflio vs Stuffolio:** The directory path is genuinely `Stufflio` (typo in the filesystem); the app and branding are `Stuffolio`. Both are correct; don't try to "fix" path examples.
- **Commit policy:** Standing preference is push via GitHub Desktop ⌘P, not Terminal CLI. The current skill-writing session was granted a one-time CLI commit override. Re-confirm before using CLI commits in the next session.
- **Plugin manifest:** `.claude-plugin/plugin.json` was touched in #12 (description strip). Confirm any future edits don't reintroduce the long-form description.
- **`v0.3-feedback.md` line numbers:** Stale after #1 (the split moved most prose into reference/). Work from the file structure, not the line refs.

### Smoke test commands (memorize for next session)

```bash
# Validate format-version marker on Stuffolio's live UNFORGET.md
python3 scripts/check_format_version.py "/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio/Documentation/Development/Deferred/UNFORGET.md"

# End-to-end scan + dedup against Stuffolio
python3 scripts/scan_surfaces.py --root "/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio" --unforget-md "/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio/Documentation/Development/Deferred/UNFORGET.md" | python3 scripts/dedup_findings.py --candidates -

# Path encoding sanity
python3 scripts/encode_project_path.py "/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio"
# Expected: "encoded": "-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio"
```

### Files NOT to touch in next session

- `examples/UNFORGET.md` — canonical reference; only update when a format change requires it
- `LICENSE` — Apache-2.0; don't modify
- `.claude-plugin/marketplace.json` — only changes when shipping a new plugin version
- `v0.2-*.md`, `v0.3-roadmap.md`, `v0.3-feedback.md` — historical planning docs; the feedback doc may stay untracked

### Push checklist

4 unpushed commits at session end (`2dfba3f`, `c0fe867`, `866218a`, `08419c7`). #6 will become the 5th once committed in the next session. Push via GitHub Desktop ⌘P after #6 commits, before starting #3.
