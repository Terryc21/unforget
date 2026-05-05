# Continuation prompt — unforget v0.3-feedback work

**Last session ended:** 2026-05-04 (updated 2026-05-04 evening)
**Branch:** `main` (caught up with `origin/main`; #6 shipped as `12eb3f9`, #3 shipped as `dc9c4be`)

---

## Paste this prompt into the next Claude Code session

> I'm continuing v0.3-feedback work on the unforget skill at `/Volumes/2 TB Drive/Coding/GitHub/unforget`. Ten items have shipped across two sessions, spread across these commits:
>
> - `6c84d50` #1 progressive-disclosure tiering
> - `e2c6144` #11 scripts/ directory
> - `2dfba3f` #12 frontmatter strip
> - `c0fe867` #0 Compact preset
> - `866218a` #13 + #14 + #15 cross-promo gate + README + tracker section
> - `08419c7` #7 + #9 + Continuous-preset header smaller fix
> - `12eb3f9` #6 persist memory-dir to config comment (closes the previous-session continuation)
> - `dc9c4be` #3 self-test corpus (15-of-16-files commit; mangled message body, no Summary line; `tests/golden/check_format_version.json` was missed and ships in a follow-up)
>
> **No uncommitted work pending from prior sessions.** All items through #3 are on `origin/main`.
>
> **Cleanups still owed (cosmetic, non-blocking):**
> 1. `dc9c4be` commit message — single mashed paragraph (paste from Desktop ate newlines). User-decided to leave on main; web-UI Reword later if desired. Do NOT force-push to amend.
> 2. The follow-up commit that added `tests/golden/check_format_version.json` + this CONTINUATION update should be the last thing on top of `dc9c4be`.
>
> **Then stop.** The remaining items (#4 doctor, #5 detail-block convention, #8 promotion history, #2 migrate, #10 fresh) each warrant their own session per the recommended ordering in `v0.3-feedback.md`.
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
reference/surfaces.md               180 lines  (#6 pin spec landed in 12eb3f9)
reference/promotion.md              134 lines
reference/commands.md               300 lines
scripts/scan_surfaces.py            ~545 lines (#6 pin logic landed in 12eb3f9)
scripts/encode_project_path.py      56 lines
scripts/dedup_findings.py           193 lines
scripts/check_format_version.py     120 lines
scripts/prune_backups.py            103 lines
scripts/README.md                   53 lines
README.md                           393 lines  (was 354 pre-#14)
tests/                              new tree   (#3 corpus landed in dc9c4be)
  run.sh                              bash harness with --bless flag
  normalize.py                        JSON normalizer (path strip, sort, suppress)
  README.md                           coverage matrix + re-baselining workflow
  fixtures/                           sample-project + dedup-input.json
  golden/                             4 JSON goldens (1 missed in dc9c4be, see follow-up)
```

### Items shipped across both sessions, in order

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
| 6 | Persist memory-dir to config comment | `12eb3f9` |
| 3 | Self-test corpus (`tests/`) | `dc9c4be` (+ follow-up for missed golden) |

### Items remaining

Per `v0.3-feedback.md` recommended landing order:

| # | Title | Why next | New session? |
|---|---|---|---|
| 4 | `/unforget doctor` artifact health check | Verifies #2 + #8 once they land | YES — new subcommand spec |
| 5 | Detail-block length convention + `--detail` edit flow | Independent | YES — pairs naturally with #4 if light |
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

All session-end commits are on `origin/main`: through `12eb3f9` (#6) and `dc9c4be` (#3). The follow-up commit that ships `tests/golden/check_format_version.json` + this CONTINUATION update lands on top of `dc9c4be`. Push via GitHub Desktop ⌘P as usual.
