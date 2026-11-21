# /unforget list

Part of the unforget command reference; the index is [../commands.md](../commands.md).

---

## /unforget list

For standalone HTML output (`list --html` or `report`), read [html-report.md](html-report.md). Its unfinished-work defaults are separate from chat-list preferences; explicit criteria win.

Show current state. Default view is sorted by Target (🔴 THIS first), then Urgency (CRITICAL first).

### Usage

```
/unforget list                        ·  full table (--view=all --group-by=target, unchanged default)
/unforget list --target=THIS          ·  only ship-blockers
/unforget list --section=audit        ·  only Section 3
/unforget list --status=open          ·  filter by @status value (open/in-progress/done-verified/done-unverified/blocked/withdrawn)
/unforget list --stale                ·  only rows past their staleness threshold (ages from `scripts/row_age.py`)
/unforget list --parked               ·  include rows set aside by likelihood (left out by default; see § Output format)
/unforget list --age=30+              ·  only rows not changed for more than 30 days (`row_age.py` `age_days`)
/unforget list --view=<mode>          ·  all | open | done | split | next (see § View modes)
/unforget list --group-by=<axis>      ·  target | section | none (see § Grouping)
/unforget list --ledgers=<names>      ·  read across named sibling ledgers (see § Multi-ledger scope)
/unforget list --all-ledgers          ·  read across every registered ledger (see § Multi-ledger scope)
/unforget list --fresh                ·  re-run the display-preference interview, then list (see `list-preferences.md` § Display-preference interview)
```

**Status is read from the `@status` token** (format v2+), not the prose — via `python3 scripts/parse_status.py --file <path>`. Two consequences:

- `--target=THIS` "ship-blockers" counts a 🔴 THIS row as blocking unless its token is `done-verified` or `withdrawn`. **A `done-unverified` THIS row is STILL a blocker** — it is not proven (the script returns `blocks_release:true` for it).
- `--status=<value>` filters on the token value. Legacy tokenless rows match their old word-status loosely (`Open`→`open`, `Fixed`→a done-* state). It is more granular than `--view` (e.g. `--status=blocked` alone has no `--view` equivalent) and keeps working unchanged; `--view=open`/`--view=done` are the named, common-case spellings for the two buckets most requests actually want.

### Output format

The skill renders the matching rows in the same 10-column format as UNFORGET.md, with a one-line summary at the top:

> "12 rows total: 2 🔴 THIS (release blockers), 5 🔵 NEXT, 5 ⚪ SOMEDAY. Stale: 1."

For the simplest case (`/unforget list` alone), this is the answer the user was actually looking for when they asked "what's deferred?"

**Set-aside rows (format v2+):** rows set aside by likelihood (`@parked:likelihood`) are not actionable work, so `list` leaves them out unless `--parked` is given, and prints the classifier's one line in their place, from `python3 scripts/set_aside.py classify --file <ledger> --dir <ledger-dir>` (`summary_line`, e.g. `Set aside: 9 (rare 5, improbable 4)`). A set-aside row that still blocks release is never left out. When `park_policy` is `ask` or `auto` and the classifier returns candidates, follow `reference/pickup.md` § Who decides. See `reference/pickup.md` § Setting rows aside by likelihood.

**Rows waiting for the user (format v2+):** when `python3 scripts/verify_ledger.py --file <ledger>` returns a non-empty `parked_waiting`, print one line ahead of the table: `N rows logged by a session are waiting for you: <IDs>`. These rows are shown in the table as usual; the line is there so the user can tell which rows they have never triaged. See `reference/pickup.md` § How parked rows appear.

**Archive nudge:** after the list output, if 5 or more Fixed/Done rows are sitting in the active tables, append the one-line archive nudge (see `/unforget archive` § The archive nudge). This is the moment the user is already looking at the ledger, so it is where accumulated-completed-row clutter is most usefully surfaced.

**Session defer/fix readout (format v2+):** after the list, append the deferral-gate session readout — `python3 scripts/defer_tally.py readout --dir <ledger-dir>` — as one line, e.g. `This session: 2 fixed inline · 7 deferred (reasons: 3 user-decision, 2 external-block, 2 scope).` When rows were started this session it also says how many and why, naming the ones the user did not choose (`reference/pickup.md` § Starting is visible). When the helper raises the defer-heavy flag (exit 1), also append its advisory (`"7 deferred vs 2 fixed this session — worth a pass to see if any are actually do-now?"`). This is **advisory, never a prompt** — some sessions are legitimately defer-heavy (planning, blocked-on-devices). The reason breakdown is the point: 7 all-`user-decision` is legitimate, 7 all-`scope` is a tell. See `reference/deferral-gate.md` §4. Skip silently on a v1 ledger with no tally state.

### View modes (`--view=`)

**Why this exists.** The default single-table view interleaves open and closed work sorted by Target/Urgency, so a reader answering "what's actually left before ship?" has to visually filter out every `done-verified` / `withdrawn` row while scanning — on a ledger with 40+ rows across a dozen sections' worth of history, that's real work, and it's easy to misread a row's *current* status when the Status cell also narrates its history (a row that was open, got fixed, regressed, and got fixed again reads as a paragraph, not a token). `--view` does that filtering once, mechanically, instead of asking every reader to redo it — and separates "which rows" (`--view`) from "how grouped" (`--group-by`, next section) so the flag surface doesn't grow one bespoke flag per request.

**Status classification for every mode below** is via `python3 scripts/parse_status.py --file <path>` — the same source of truth `--status` already uses, no new parsing logic:

- **Open bucket** — every row where `completed` is `false`. This includes `open`, `in-progress`, `blocked`, and **`done-unverified`**. A `done-unverified` row has code written but not proven against reality (device test, Sentry re-check, macOS build, etc.) — per `reference/status.md`, that is still open work, not done work, so it belongs in Open, not Completed. **This rule is load-bearing across every mode, not incidental** — a `--view` that put `done-unverified` in Completed would just relocate the exact misreading this feature exists to fix.
- **Completed bucket** — every row where `completed` is `true`: clean `done-verified`/`withdrawn`, or an unambiguous legacy completion. `archivable` is stricter and excludes tokenless rows.
- Legacy tokenless rows (pre-format-v2) are classified by their loose word-status mapping, same as `--status` does (`Open`→Open bucket, `Fixed`→Completed bucket); a row that cannot be classified at all is listed under a third **Unparsed** heading in modes that show more than one bucket, rather than silently dropped — silent misclassification is worse than a visible "couldn't tell" bucket.

**`--view=all`** (default, unchanged): one table, every matched row, sorted per `--group-by` (default: Target then Urgency). This is today's existing behavior — nothing about it changes.

**`--view=open`**: one table, Open bucket only. Named equivalent of `--status=open` filtered to just that bucket, but framed as a view rather than a raw token filter — the common-case spelling for "what's left."

**`--view=done`**: one table, Completed bucket only. Named equivalent for "what shipped."

**`--view=split`**: two (or three) tables in one output:

```
## Open (N rows)
<10-column table, sorted per --group-by>

## Completed (M rows)
<10-column table, same columns, sorted per --group-by>

## Unparsed (K rows)            ← omitted entirely when K = 0
<rows parse_status.py could not classify — shown so nothing is silently dropped>
```

Each heading carries its own count so `--view=split` alone answers "how much is actually left" without the reader counting rows. The one-line summary and archive nudge (see § Output format above) still print once, above all tables.

**`--view=next`**: no table. A single **proposed** row plus a one-line reason, drawn from the Open bucket only (a Completed row is never "next"). Parked rows, bare or set aside, are never the pick. The pick is a report, not an instruction: under `reference/pickup.md` the session starts it only when the user says so, so end the line by asking rather than starting (`"…Want me to start on it?"`). Ranking is a **composite score**, shown in the reason so the pick is inspectable rather than a black box:

- **Ship-risk** — Target (🔴 THIS weighted highest) × Urgency × Risk:No-Fix severity.
- **Closest-to-done** — `done-unverified` rows need one verification step, not new code; weighted up when the remaining work is a device/build/Sentry check rather than implementation.
- **ROI** — the row's own 🟠/🟢/🟡/🔴 ROI rating.

Output shape: `"<ID> — <one-line finding>. <why this one, naming the dominant factor>."` e.g. `"A27 — household share scope may render a blank inventory. Highest ship-risk open item: 🚢 THIS, 🔴 risk-no-fix, repro-gated."` If the top-ranked row is `done-unverified`, say so explicitly (`"...code done, needs a 2-Apple-ID device round-trip to close."`) so "next" doesn't read as "start from scratch." Ties broken by lowest Fix Effort (prefer the faster win when scores are equal).

**Composability.** Every `--view` mode combines with the existing filters (`--target=`, `--section=`, `--stale`, `--age=`) — the filter narrows the row set first, then `--view` buckets/ranks the narrowed set. `--view=<mode>` combined with `--status=<value>` is redundant when the value already picks one bucket (`--status=open` + `--view=done` contradict) — honor `--status=` and ignore `--view` in that case, since a single-value filter has nothing left to bucket.

**Not a storage change.** Every `--view` mode is presentation-only, same principle as the compact-vs-wide terminal fallback below: UNFORGET.md keeps its one-file, one-table-per-section format on disk. This is deliberate — splitting the *file* into open/completed documents would break the "single source of truth, one file per project" design goal this skill exists to enforce (see § Why this skill exists) and would need every completed row to migrate back on a regression (exactly the done→broken→done-again case A65-shaped rows hit in practice). Splitting the *display* gets the readability win without that cost.

**Default-view question (explicitly NOT changed here):** this section adds `--view` as opt-in; it does not change the default for a bare `/unforget list`. Revisit only if usage shows most `list` calls immediately follow up with `--view=`; until then, keep the default output backward-compatible for anyone scripting against it.

### Grouping (`--group-by=`)

Orthogonal to `--view` — controls *how* the matched rows are grouped/sorted within whichever table(s) `--view` produces, not which rows are shown.

- **`--group-by=target`** (default, unchanged): group/sort by 🔴 THIS / 🔵 NEXT / 🟡 LATER / ⚪ SOMEDAY, then Urgency within each group. Today's existing sort.
- **`--group-by=section`**: group by ledger section (Paused Plans / Session Spillover / Audit Findings / User-Reported), Target+Urgency sort within each section. Combined with `--view=split`, this produces one Open/Completed pair per section rather than one pair overall — useful when sections are owned by different people or track genuinely different kinds of work.
- **`--group-by=none`**: flat list, Urgency-only sort, no grouping headers. For piping into something else that does its own grouping.

`--group-by` never changes which rows are included — that's `--view`'s job exclusively. The two axes are independent by design so the flag surface doesn't grow one bespoke flag per new request; a future "group by owner" or "group by effort" is another `--group-by` value, not a new top-level flag.

### Multi-ledger scope (`--ledgers=` / `--all-ledgers`)

**Default is single-ledger unless explicitly saved otherwise.** `/unforget list` without
a scope flag uses `display_all_ledgers` when set; otherwise it reads the current ledger.
Cross-ledger scope is opt-in through a request or a saved interview answer —
a project's sibling ledgers exist because their work was deliberately kept separate (a
different actor, a different lifespan/discipline, a different domain; see
`reference/branching.md` §2 for the three axes), and silently unioning them by default would
work against that separation the first time someone ran a routine `list` and got, say,
sprint-scoped rows mixed into a release read.

**Scope comes from the registry, not from re-discovering files.** The registry already
records every ledger's `role` (`main`/`child`), `axis`, `parent`, and `death` condition
(`reference/registry.md` § The schema) — that's the authoritative sibling declaration, and
the union reads the existing ledger table; its saved default is `display_all_ledgers`. `--ledgers=`/`--all-ledgers` read that existing
table; they do not glob for `*UNFORGET*.md` in the project. A file that looks like a ledger
but was never registered is not in scope, on purpose — an unregistered file is exactly the
"stranded ledger" failure the registry exists to prevent (`reference/registry.md`'s own
opening rationale).

**Usage:**

```
/unforget list --ledgers=MI-UNFORGET.md              ·  union with one named sibling
/unforget list --ledgers=MI-UNFORGET.md,TERRY-UNFORGET.md   ·  union with several, by name
/unforget list --all-ledgers                          ·  union with every registered ledger (main + all children)
```

Names are matched against the registry's `name` column (`python3 scripts/registry.py read
--dir <ledger-dir>`), not re-typed paths — a name not present in the registry is an error
("`MI-UNFORGET.md` is not registered in this project; run `/unforget branch` or add it to the
registry first"), not a silent no-op.

**What "combine" means depends on the operation — three different safety levels, not one:**

1. **Reading (`--view=all`/`open`/`done`/`split`)** — safe to union unconditionally. Rows from
   different ledgers are just more rows in the same table; nothing about display conflates
   their identity. Each row's own ID is already unique within its ledger by convention, and the
   output should carry a **Ledger** column (or a leading badge) whenever more than one ledger
   is in scope, so a reader always knows which file a row came from — this is the one
   presentation change multi-ledger scope requires.
2. **Ranking (`--view=next`)** — safe to union, but **axis-aware, not blind.** A straight
   composite-score comparison across ledgers would rank a `TERRY-UNFORGET.md` row (axis:
   `actor` — a different human's work by definition) as "next" in a general session where
   Terry-only work may not even be actionable right now, or rank a soon-to-die
   `MI-UNFORGET.md` row (axis: `lifespan`, has a `death` condition) as equally durable to a
   permanent main-ledger row. `--view=next --all-ledgers` MUST name the source ledger in its
   one-line output (`"A27 (UNFORGET.md) — ..."`, not just `"A27 — ..."`), and when the
   top-ranked row's ledger has `axis: actor` set to someone other than the current session's
   assumed actor, say so explicitly rather than presenting it as an undifferentiated top pick
   (`"top pick is TERRY-UNFORGET S12 — actor-scoped to Terry; here's the best NON-Terry-scoped
   row too"`). This is advisory phrasing, not a filter — the row still surfaces, just labeled.
3. **Writes (`archive`/`edit`/`promote`)** — **out of scope for `--ledgers=`/`--all-ledgers`
   entirely.** Those commands keep operating on exactly the one ledger they're pointed at, full
   stop. A mis-scoped read just shows an extra row with a label; a mis-scoped write moves or
   mutates a row in the wrong file, which is a different risk class and gets no shortcut here.
   Editing a sibling ledger means pointing the command at that ledger directly, the same as
   today — multi-ledger scope is a `list`/`scan`/`--view=next` feature only.

**Why the registry and not auto-discovery.** The alternative — union every `*UNFORGET*.md`
found under the project root by default, let a flag narrow instead of widen — was considered
and rejected. It would mean a bare `/unforget list` could silently change its answer as new
sibling ledgers get created (a `branch` call today changes tomorrow's default output with no
flag touched), and it would surface unregistered stray files the registry was built specifically
to stop the skill from losing track of or confusing with real ledgers. Explicit opt-in, declared
through a saved interview answer or an explicit per-call flag, keeps the default behavior stable and keeps scope a
decision the user makes, not one the tool infers.

**Composes with `--view` and `--group-by`.** `--all-ledgers --view=split --group-by=section`
is a legitimate combination: union everything registered, bucket into Open/Completed, group
each bucket by section — with the Ledger column making clear which file each row's section
label belongs to.

### Algorithm fallback (Python unavailable) — `--view`, `--group-by`, `--ledgers`/`--all-ledgers`

The base `list` filters (`--target=`, `--section=`, `--status=`, `--stale`, `--age=`) are simple
enough to apply by eye against the rendered table and have never needed a fallback. The three
additions in this file do, because they depend on logic beyond "filter the visible columns":

- **`--view=open` / `--view=done`:** locate Status by its table header, then apply the
  shared contract in `reference/status.md`: only clean verified/withdrawn claims or clear
  legacy completion belong in Completed. Missing tiers, missing code-sufficiency notes,
  session claims and contradictions remain Open. Ambiguous legacy rows remain Unparsed.
- **`--view=split`:** run the `--view=open` and `--view=done` classification above once each
  over the same filtered row set (do not re-filter between the two), render as two headed
  tables with their own row counts, Unparsed as a third heading only if non-empty.
- **`--view=next`:** restrict to the Open bucket (never rank a Completed row as next). For each
  candidate, compute three ranks and combine: (1) ship-risk = Target weight (THIS highest, then
  NEXT, LATER, SOMEDAY) × Urgency weight (CRITICAL highest) × the row's own Risk:No-Fix
  indicator; (2) closest-to-done = `done-unverified` rows outrank `open`/`in-progress`/`blocked`
  rows, since the remaining work is a verification step rather than new code; (3) ROI = the
  row's own 🟠/🟢/🟡/🔴 rating, highest first. Sum or otherwise combine the three (exact weights
  are a judgment call, not a fixed formula) and take the top row; on a tie, prefer lower Fix
  Effort. State the dominant factor in the one-line output, and if the winner is
  `done-unverified`, name the specific verification step from its Detail block rather than
  saying only "unverified."
- **`--group-by=section` / `--group-by=none`:** re-sort the already-selected row set. `section`
  groups by which of the four table sections (Paused Plans / Session Spillover / Audit Findings
  / User-Reported) each row belongs to, Target-then-Urgency sort within each group. `none` is a
  flat list sorted by Urgency alone, no group headings.
- **`--ledgers=<names>` / `--all-ledgers`:** read the registry block from `README.md` between
  the `<!-- unforget-registry:begin -->` / `:end` markers (see `reference/registry.md`'s own
  fallback for the exact parse); for `--ledgers=`, keep only the named rows from the **Ledgers**
  table, error if a name isn't present; for `--all-ledgers`, keep every row regardless of
  `role`. Read and concatenate each named ledger's matching rows, tag each with its source
  ledger's `name`, then apply whichever `--view`/`--group-by` was also requested to the
  combined set. For `--view=next` specifically, do not blindly combine across ledgers: check
  each candidate ledger's registry `axis` value — a candidate from an `axis: actor` ledger
  belongs to a different human's declared work, and a candidate from an `axis: lifespan` ledger
  is inside a container with a stated `death` condition; name the source ledger in the output
  either way, and when the top-ranked candidate is actor-scoped, also surface the best
  non-actor-scoped candidate as a labeled alternative rather than presenting only the one pick.


### Terminal-aware rendering

The full 10-column table is wide (typically 200+ characters with emoji-width quirks). On narrow terminals it wraps or renders as vertical blocks instead of horizontal rows. To stay readable:

- **Detect terminal width** at render time (`stty size` / `tput cols` / `os.get_terminal_size()`).
- **At ≥120 columns:** render the full 10-column Standard table (or whichever preset the file uses).
- **At <120 columns:** auto-fall-back to a 6-column compact projection: `# / Target / Finding / Urgency / Status` plus one user-chosen extra column (default `Effort`). This is the same shape as the **Lean** preset, reused for display only.
- **The on-disk file format never changes.** Compact rendering is presentation-only; UNFORGET.md still holds all 10 columns. Scrolling output back to a wider terminal restores the full view.

The user can override the auto-detection:

```
/unforget list --wide             ·  force the full table even at <120 cols (will wrap)
/unforget list --compact          ·  force the 6-column projection even at >=120 cols
/unforget list --extra=ROI        ·  pick a different sixth column for the compact projection
```

The auto-fallback is silent (no banner, no warning); the override flags are for power users who know what shape they want. Compact rendering eliminates the "Terminal width" warning callouts that adopters write into their own UNFORGET.md headers today.
