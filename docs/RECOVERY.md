# Recovering a broken UNFORGET.md

UNFORGET.md is plain markdown, but the skill's commands depend on the format being intact. Every file created by `init` includes this notice at the top:

> **Allowed:** add new rows, edit row content, move rows between sections, mark rows Fixed / Deferred / Skipped, edit detail blocks.
>
> **Not allowed:** rename columns, reorder columns, add or remove core columns, rename the four section headers, split this file, delete the example row, renumber existing IDs, reuse retired IDs.

If something broke:

| What broke | How to fix |
|---|---|
| **Renamed a column header** (e.g., `Urg` → `Urgency Level`) | Rename it back. Column headers must match exactly. |
| **Reordered columns** | Restore the 10-column sequence: `# / Target / Finding / Urg / RFix / RNo / ROI / Blast / Effort / Status`. |
| **Added or removed core columns** | Restore the 10 core columns. Extra columns (Owner, Sprint, Component) are fine **after** the core columns. |
| **Renamed a section header** | Restore one of `## 1. Paused plans`, `## 2. Session spillover`, `## 3. Audit findings`, `## 4. User-reported / observed`. |
| **Split the file into multiple files** | Concatenate back into one. Multi-file splits defeat the "one ledger" promise. |
| **Renumbered or reused IDs** | If you have git history, restore the prior IDs and stop renumbering forever. If not, pick a fresh starting integer (e.g., P100) so old references at least don't conflict. |
| **Deleted the example row** | Restore from `examples/UNFORGET.md` in this repo. |

The format-version marker at the top of every file (`<!-- unforget-format: v1 -->`) tells future skill versions which format the file was created against. Don't remove it.

When in doubt: compare against [`../examples/UNFORGET.md`](../examples/UNFORGET.md); use `git checkout HEAD -- path/to/UNFORGET.md` to revert; or [open an issue](https://github.com/Terryc21/unforget/issues) if recovery is unclear.
