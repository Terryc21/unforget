# Recovering a broken UNFORGET.md

UNFORGET.md is plain markdown, and you can edit it by hand. Unforget's commands read it by position and by marker, though, so some hand edits break them.

> **Safe by hand:** add new rows, edit row content, move rows between sections, change a row's status, edit detail blocks, append extra columns after the core ones.
>
> **Breaks the tools:** renaming, reordering, adding or removing core columns; renaming the four section headers; renumbering existing IDs; reusing retired IDs; deleting the format marker.

In a format v2 ledger (`<!-- unforget-format: v2 -->` at the top), a row's status is the `@status:` token in its Status cell, not the word around it. Change the token (`open`, `in-progress`, `done-verified`, `done-unverified`, `blocked`, `withdrawn`), and give a done row its `@verified:` tier. `skills/unforget/reference/format.md` § Status tokens has the full rules.

Run `/unforget verify` after a hand edit. It catches a row with the wrong number of cells, a row whose ID it can't read, and a closed row whose words say it is still live, and names the row each time.

If something broke:

| What broke | How to fix |
|---|---|
| **Renamed a column header** (e.g., `Urg` → `Urgency Level`) | Rename it back. Core column headers must match. |
| **Reordered columns** | Restore your preset's order. Standard is `# / Target / Finding / Urgency / Risk: Fix / Risk: No Fix / ROI / Blast Radius / Fix Effort / Status`; Compact, Lean and Continuous are listed in `skills/unforget/reference/format.md` § Presets. |
| **Added or removed core columns** | Restore your preset's core columns. Extra columns (Owner, Sprint, Component, 1-Star Risk) are fine **after** the core columns. |
| **Renamed a section header** | Restore one of `## 1. Paused plans`, `## 2. Session spillover`, `## 3. Audit findings`, `## 4. User-reported / observed`. |
| **Moved rows into a new file by hand** | Unforget reads only the ledgers in its registry, so rows in a hand-made file drop out of `list` and the release check. Move them back, or create the file with `/unforget branch`, which writes the child ledger, a pointer in the parent and the registry entry together. |
| **A closed row whose words say it is still live** (e.g., `@status:done-verified` next to "still broken") | `/unforget verify` reports it as a contradiction. Set the `@status:` token to the row's real state. |
| **Renumbered or reused IDs** | If you have git history, restore the prior IDs and stop renumbering. If not, pick a fresh starting integer (e.g., P100) so old references at least don't conflict. |
| **Deleted the format marker** | Put `<!-- unforget-format: v2 -->` (or `v1` for an older ledger) back near the top. Without it, each command asks whether the file is an Unforget ledger at all, and the default answer is no. |

When in doubt: compare against [`../examples/UNFORGET.md`](../examples/UNFORGET.md); use `git checkout HEAD -- path/to/UNFORGET.md` to revert; or [open an issue](https://github.com/Terryc21/unforget/issues) if recovery is unclear.
