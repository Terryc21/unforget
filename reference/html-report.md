# HTML ledger reports

Use `/unforget report` (or `/unforget list --html`) when the user wants a standalone,
ranked HTML table of ledger work. Natural-language requests such as “make an HTML
report of release blockers” invoke the same workflow. This is a presentation mode,
not a new ledger or a change to the default chat `list` behavior.

In Codex, invoke `$unforget report` or `$unforget list --html`. In Claude Code,
use `/unforget report` (plugin: `/unforget:unforget report`). Both follow this same
workflow and run the same generator. Resolve helpers from the loaded skill
directory, not the project working directory. See `reference/runtime.md` for tool
and path conventions; no host-specific preview tools are required.

## Defaults and user choices

An unqualified HTML request produces **unfinished work from the current canonical
ledger**, sorted by **release blocker → urgency → user impact**, with source details,
search, filters, sortable columns, light/dark mode and printing. Unfinished includes
open, in-progress, blocked, done-unverified and ambiguous legacy states. Verified
completion and withdrawn rows are excluded. Other ledgers require explicit scope,
a clearly established project-wide request, or the user's chosen all-ledger option.

Resolve choices in this order: explicit current request, accepted conversation
choices, then these HTML defaults. Existing terminal-list preferences do not
silently narrow an HTML report (e.g. a saved spillover-only filter). Do not rewrite
preferences unless asked to save a default.

If the user requests options or customization without specifying the outcome, ask:
**“What should the HTML table show?”** Offer **Unfinished work (recommended)**,
**Release blockers**, and **Custom scope and ranking**. With no preference provided,
use the default; do not delay a clear request with an interview. For custom scope,
ask only for missing choices that materially change the result, in the user's words:
which ledgers/items, which work statuses or release targets, and what should rank
first. Examples: “only my device checks,” “all ledgers, high urgency,” “small fixes
first,” “include completed work,” or “privacy items ranked by user impact.” Honor
natural-language criteria even when they are not dedicated script flags: resolve
and inspect the exact matching rows, then use a supported filter or an explicit
`--id` selection. Explain judgment-based matches; do not silently replace the query.

Optional controls include ledgers, sections, status, target, urgency, search text,
ordered sort criteria, visible columns, title and output path. Exact status filters
supersede the broader view. Choices apply to this report only. `--sort` specifies
precedence, not an opaque weighted score; state the order in the report.

## Build the snapshot

1. Resolve actual ledger files through the README registry (canonical over the
   cache) and the established project scope. Read source files now; do not use a
   prior report's checkboxes or counts as current evidence. Preserve format-version
   handling. A future/missing format is a disclosed best-effort read, never a write.
2. Include canonical rows once, keyed by **ledger + ID**. A view is not another
   source of truth. Attach verification procedures to their canonical defect rows;
   standalone owed checks may remain separate if they own distinct obligations.
   Reconcile transferred rows, rollups and view/source conflicts before selecting
   inputs; record unresolved discrepancies instead of silently closing them.
   The helper accepts explicit files and does not automatically resolve these
   project-specific relationships. Do not feed a view plus its canonical ledger
   just to make the report larger. If a supplementary file mixes duplicates and
   genuine obligations, use reviewed `--id` / `--exclude-id` selections and
   explain exclusions with `--note`; the original path and line remain intact.
3. For release-readiness reports, run the project's current verifier and any
   documented view-drift check. Use **ship_ready / this_open**, not **gate_pass**
   alone. Explain missing coverage and integrity errors. A report filter must not
   turn a subset into a project-wide all-clear. No ASC, live service or device claim
   follows from reading a ledger. Do not invent submission deadlines or promote
   later-target items to blockers because they sound urgent.
4. Preserve original urgency, status, target, confidence and ratings. Normalize
   words, not emoji colors. Missing values are **Unrated**, not zero/None/probable.
   User-impact ratings may be sourced or estimated: if estimated, give a brief
   per-row basis. Severe = loss/privacy/core journey blocked; High = material task
   disruption; Moderate = meaningful friction; Low = limited reach/polish;
   Indirect = internal work. Leave uncertain impact Unrated. `blocked` is a work
   dependency; only an unresolved THIS commitment is a release blocker.
5. Run `scripts/html_report.py`. It reads Markdown tables by header, recognizes
   Standard/Compact/Lean and phase-ledger shapes, and rejects malformed row widths
   or duplicate IDs instead of silently omitting them. Read its warnings. Legacy
   “Fixed” alone is a completion claim; owed/partial narration keeps it unfinished.
   Ambiguous legacy states remain visible for reconciliation. Legacy semantics can
   differ by project: inspect them before relying on the automatic bucket.
6. Save to the requested path; otherwise use the workspace's normal deliverables
   directory (for example, `outputs/`). Avoid replacing an existing report
   unless requested; `--force` is for authorized refreshes. HTML is a derived
   snapshot and never a second authoritative backlog.
7. Check counts and blocker IDs against the selected sources; open the HTML and
   exercise search, blocker/status filters, sorting/reset and expanded details.
   Inspect desktop and narrow layouts when a browser is available. Otherwise
   disclose that visual verification was unavailable. Link the final HTML and
   report the included rows/blockers and any material coverage limit.
8. **Open the report for the user** once it is written and checked, in their default
   browser: `open "<path>"` on macOS, `xdg-open "<path>"` on Linux, `start "" "<path>"`
   on Windows. The page is interactive (search, sort, filters), so a full browser is
   the default. Opening is read-only and needs no confirmation. Then say where the file
   lives, so it can be reopened later.
   - **Skip it** when the user said not to open it, when the run is unattended (CI, a
     scheduled job, no display), or when the command is unavailable. Say the report was
     not opened and give the path.
   - **A host's own preview pane** (for example, a desktop app's file viewer) is an
     optional extra, not a replacement: some panes only open files inside the session's
     folders, and a report saved elsewhere shows an error there. Use the pane only for a
     report saved where the pane can open it.

## Helper usage

Paths below are examples. Resolve the helper relative to this skill directory.

```sh
python3 scripts/html_report.py --file /project/Documentation/Ledgers/UNFORGET.md \
  --output /workspace/outputs/ledger-report.html --title 'Project unfinished work'

python3 scripts/html_report.py --file /project/Documentation/Ledgers/UNFORGET.md \
  --file /project/Documentation/Ledgers/SITE-UNFORGET.md --blockers-only \
  --output /workspace/outputs/release-blockers.html

python3 scripts/html_report.py --file /project/Documentation/Ledgers/UNFORGET.md \
  --target NEXT --urgency high --sort effort,ux,urgency \
  --columns rank,id,blocker,finding,urgency,ux,status,effort \
  --output /workspace/outputs/next-small-fixes.html

python3 scripts/html_report.py --file /project/Documentation/Ledgers/UNFORGET.md \
  --limit 10 --sort blocker,urgency --output /workspace/outputs/top-ten.html
python3 scripts/html_report.py --file /project/Documentation/Ledgers/UNFORGET.md \
  --effort trivial --effort small --sort roi,urgency --output /workspace/outputs/quick-wins.html
```

`--limit N` shows the first N rows after sorting, for requests such as "top ten most
urgent". A cap never hides a release blocker: blockers ranked below the cut are still
shown and counted separately, and the report notes "Showing N of M matching rows". Ties
at the cut go to the lower fix effort unless `effort` is already in `--sort`. `--effort`
(`trivial|small|medium|large|unrated`) and `--roi` (`excellent|good|fair|marginal|poor|unrated`)
filter on the first recognized word of the cell, so "Small-Med" counts as small; repeat a
flag for several levels. Rows whose value has no recognizable level (for example "Done",
"N/A") are excluded by a named level, and the report counts them: rerun with
`--effort unrated` to see them, so an empty "trivial only" list is never mistaken for a
clean ledger. Blast radius is free text, so it has no filter. `roi` is also a sort key.

### Project vocabulary

A ledger whose rows use other words (T-shirt sizes, story points, "High"/"Low" ROI, usually
from older notes or another tool) maps them once in its registry block (the ledger directory's `README.md`, see
`reference/registry.md`). Example rows in the Global table:

```
| report_effort_column | Size |
| report_effort_words  | XS=trivial, S=small, M=medium, L=large |
| report_roi_words     | High=good, OK=fair, Low=poor |
```

Project words are added to the built-in ones, and a project word wins where both name the
same word. Column names are tried after the defaults. Entries that are not `WORD=level` or
name an unknown level are listed in the report's notes and not applied. The report states
when a project vocabulary was used and how many words it held. The words are kept off the
rows, so `--query` never matches them. When a filter still finds unclassified rows, its note
names the key to add.

This is a read-only translation for reports, not a second rating scale (`reference/format.md`
§ Anti-patterns): new rows still use the standard values.

When a user asks for a filter and the report counts unclassified rows, offer to map them:
show the unrecognized values, propose levels, and write only what the user confirms, with
`registry.py write --merge` (never a bare write).

`--view unfinished|all|completed`; repeatable `--status`, `--target`, `--urgency`,
`--ledger`, `--section`; `--query` searches the row's source/presentation text.
`--id` and `--exclude-id` accept repeated IDs or `filename.md::ID` keys for reviewed
custom subsets; qualify IDs when ledgers reuse them. Filters combine with AND; repeated values within a field use OR. `--section`
uses case-insensitive substring matching. Sort keys: `blocker,urgency,ux,target,
effort,roi,id,ledger,status`. Keep `id` and `finding` columns to retain source access.
Each supplied file must have a distinct filename. `--scope-note` describes scope;
repeatable `--note` records gate results, limitations and reconciliation decisions.
These notes are data, not executable HTML. Run `--help` for exact supported values.

The output distinguishes **blockers included** from **blockers in input files
before filters**. Neither is automatically the whole-project gate. It preserves
raw cells under row details, path/line citations, generation time and source hashes.
It has no external assets, scripts or network calls and no completion checkboxes
that could be confused with real ledger status.

### Optional presentation annotations

Use `--annotations /workspace/work/report-notes.json` for concise titles, actors,
next actions and user-impact estimates. Keys are `filename.md::ID`:

```json
{
  "UNFORGET.md::A230": {
    "title": "Verify restored items survive relaunch",
    "ux": "severe",
    "ux_basis": "Source describes a restored item being purged at launch.",
    "owner": "Device verification",
    "next": "Run the documented restore and relaunch acceptance check.",
    "notes": ["Related verification procedure is recorded in V-07."]
  }
}
```

Allowed impact values: severe, high, moderate, low, indirect, unrated. An estimate
requires `ux_basis`. Annotations cannot alter status, target or blocker membership.
Do not copy Stuffolio's IDs, release assumptions, source paths or ratings into
another project's report. The bundled asset is the reusable visual model; a user's
provided HTML can guide style without supplying current ledger facts.

### Closure integrity and effort order

Header-aware Status extraction feeds `parse_status.py`'s shared closure evaluator.
Invalid verified claims stay in unfinished scope, retain THIS blocking status, and show
integrity issues in both report warnings and source details. Filters affect included rows,
never input-wide blockers. Annotations cannot remove integrity issues. Negated or mixed
legacy states such as "Not fixed" or "Open; unit tests passed" remain unfinished.

Effort sorting treats Triv/Trivial, Sml/Small, Med/Medium and Lrg/Large identically,
case-insensitively. Unknowns sort last; generation and browser sorting use the same numeric
key, preserving the source spelling and stable ties.
