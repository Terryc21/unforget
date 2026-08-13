# unforget — Subcommand reference

This file holds the per-subcommand specs for everything except `/unforget init` (see `reference/init.md`) and `/unforget promote` (see `reference/promotion.md`). Read it on any specific subcommand listed below.

Subcommands here:
- `/unforget add` — capture a new deferral
- `/unforget edit` — refine a row's columns
- `/unforget import` — re-run the surface survey after init
- `/unforget list` — show current state, filterable
- `/unforget scan` — identify rows past their staleness threshold
- `/unforget branch` — atomically create a child ledger (operational summary here; full model in `reference/branching.md`)
- `/unforget archive` — move completed rows out of the active tables (lightweight; distinct from the release-time `promote` in `reference/promotion.md`)
- `/unforget --version` — install-verification health check

---

## /unforget add

Capture a new deferral. The friction point that makes or breaks the skill. Must be fast.

### Usage

```
/unforget add "Brief description of the thing being deferred"
```

### The deferral gate (format v2+) — runs FIRST, before anything else

Before `add` writes a row, it runs the **deferral gate** (full spec:
`reference/deferral-gate.md`). The gate exists because a deferred row looks
identical whether it was deferred for a good reason or because deferring was
frictionless — the *deferral-laundering* failure. The gate makes deferral cost
something and leave an auditable record. It runs above the ID/section routing:

0. **Trivial tripwire (§2).** If the would-be row is **Fix Effort = Trivial** AND
   **Blast Radius = ⚪ 1 file**, do NOT defer — **do it now.** Scope doesn't gate
   this: in-scope trivial → just do it; out-of-scope trivial → do it and log a
   one-line report line in the run summary (never silently defer, never silently
   fix). **Destructive exception:** if the trivial fix is on the always-stop list
   (data loss, file deletion, force-push, prod deploy), it does NOT auto-do —
   route to **needs-approval**, log `Status: needs approval`, and raise it at the
   end. Trivial ≠ safe.
0b. **"Why not now?" (§3).** Anything that clears the tripwire must name an
   allow-list deferral reason: `user-decision`, `scaffolding`, `scope`, or
   `external-block`. If none applies, the honest answer is **do it now** — do-now
   is the default, not the row. When a reason applies, **record it** in the row's
   detail block as `Deferred because: <tag>` so a later reader (or `scan`/`verify`)
   can check whether it held up.
0c. **Account (§4).** After the gate resolves, record the outcome into the
   per-session tally so the defer/fix ratio stays visible (the load-bearing
   backstop — a single justification can be gamed, a 7:2 ratio can't).

Run the gate + tally via the helper:

```
python3 scripts/defer_tally.py gate --effort <Effort> --blast "<Blast Radius>" \
    [--destructive] [--reason <tag>] [--policy <policy_deferral from registry>]
# after it resolves (do-now or a written row):
python3 scripts/defer_tally.py record --dir <ledger-dir> --outcome fixed-now
python3 scripts/defer_tally.py record --dir <ledger-dir> --outcome deferred --reason <tag>
```

`gate` exiting 1 with `reason_required:true` means the caller must resolve the
deferral — do the work now, or name a real allow-list reason — before a row is
written. Policy 1 strictness (`policy_deferral`) is read from the registry;
default `aggressive` (trivial → do-now regardless of scope). Only when the gate
routes to `defer` do the row-writing steps below run.

**Backward compatibility:** on a v1 (tokenless) ledger the gate still helps
(the tripwire and reason check are format-independent), but nothing about it
blocks the write path — it redirects and counts, never refuses (see
`reference/deferral-gate.md` § Anti-patterns).

### Steps

1. **Read UNFORGET.md** to find the next available ID in the chosen section.
2. **Default to Section 2 (Session spillover)** unless the user specifies a section. Section 2 is where most mid-task captures naturally belong.
3. **Auto-fill defaults** for the rating columns:
   - Target: `⚪ SOMEDAY` (most conservative; user can promote later)
   - Urgency: `⚪ LOW`
   - Risk: Fix / Risk: No Fix: `⚪ Low`
   - ROI: `🟢 Good`
   - Blast Radius: `⚪ 1 file`
   - Fix Effort: `Small`
   - Status: `Open`
4. **Ask the user to override any defaults** (single AskUserQuestion with all relevant fields, or accept the defaults to skip ahead).
5. **Append the row** to the chosen section (only reached when the gate routed to `defer`).
6. **Record the tally (format v2+):** `python3 scripts/defer_tally.py record --dir <ledger-dir> --outcome deferred --reason <tag>`. (A gate that routed to do-now instead records `--outcome fixed-now` — that path never reaches step 5.)
7. **Echo back** the new row ID and a one-line confirmation.
8. **Archive nudge (non-blocking):** count Fixed/Done rows in the active tables; if 5 or more, append the one-line archive nudge (see `/unforget archive` § The archive nudge). Never let it add latency or a prompt — the 30s speed target wins.

### Subsection flags (optional)

- `--paused` routes to Section 1 (Paused plans). Triggers an extra prompt for the detail-file pointer.
- `--audit` routes to Section 3 (Audit findings). Asks for the originating audit tool and finding ID.
- `--observed` routes to Section 4 (User-reported / observed).
- `--target=THIS|NEXT|LATER|SOMEDAY` sets Target without prompting.
- `--urgent` is shorthand for `--target=THIS --urgency=HIGH`.

### Branch auto-suggest (format v2+, on a repeated pattern only)

After capturing a row, `add` MAY offer to branch into a child ledger — but only when the `reference/branching.md` §3 cascade would land on "new ledger" for **≥2 related items**, a pattern rather than a one-off. This is how an emerging track (a cluster of user-only App Store Connect rows, a set of sprint-scoped items) gets noticed instead of silently accumulating in the main ledger — the 2026-07-25 split-brain failure was exactly a pattern no session spotted.

Rules:
- **Never branch unilaterally.** `add` *offers*; the user (or an obvious call) decides. The offer routes to `/unforget branch`.
- **≥2 related items, not 1.** "related" = same actor, same lifespan-scope, or same subject cluster across the recent adds. A single item never triggers a suggestion.
- **Name the pattern seen.** Don't ask a generic "want to branch?" — say what you saw: *"3 App-Store-Connect rows this session — split into a user-action ledger?"*
- **Non-blocking, at most once per pattern per session.** The suggestion must never add latency to the 30s `add` promise or nag; if it can't be made instantly, skip it.

### Speed target

30 seconds or less, end-to-end, for default usage. If the skill ever takes longer than 30 seconds to capture an item, it has failed at its core promise. The branch auto-suggest above is subject to this: it is an instant, non-blocking offer or it is skipped.

---

## /unforget edit

Refine a row's columns after import. Most useful immediately after `/unforget init` to upgrade auto-filled defaults.

### Usage

```
/unforget edit P3                       ·  open row P3 for editing
/unforget edit P3 --target=THIS          ·  change just the Target cell
/unforget edit P3 --status=done          ·  mark done (see status-token rule below)
/unforget edit S5 --urgency=HIGH --roi=Excellent
```

### Steps

1. Find the row by ID. Show its current 10 columns.
2. Prompt for which cells to update (or accept flag overrides if passed inline).
3. Show the diff (old value to new value for each changed cell).
4. Apply the change to UNFORGET.md.

### Status-token rule (format v2+)

When changing status, write the `@status:` token (see `reference/format.md` §
Status tokens and `reference/status.md`), not a bare word. Specifically for
marking something done:

- `--status=done` **requires a verification tier.** Ask (or infer from context)
  how it was checked and write `@verified:<tier>`.
- If the only backing is a session's own claim (no independent check), the
  result is **`@status:done-unverified` `@verified:session-claimed`**, NOT
  `done-verified`. A claim is not a verification. `done-verified` requires
  `device` or `user` (or `code` with an explicit code-is-sufficient note).
- Record provenance in the narration (who/what/when), e.g.
  `` `@status:done-verified` `@verified:device` · TF77 · 2026-07-25 ``.
- After writing, validate with `python3 scripts/parse_status.py --row "<row>"`;
  if it reports `tier_valid:false` or `contradiction:true`, fix before saving.

`/unforget edit` is the everyday command for keeping rows accurate. Pair with `/unforget list --age=30+` to find rows that need review.

### Budget check at write time (not just at scan/verify)

**Why this exists.** Char-budget overflow (`reference/verify.md` § Char-budget severity
escalation) is created one status change at a time — a row that appends a "still owed" /
"RESOLVED" / "prior arc" line at every edit instead of migrating older narration to the
detail block. Catching this only reactively, at the next `scan` or `verify`, means the row
has already crossed the hard threshold before anyone is told. `edit` is the moment the bloat
is actually written, so it's the cheaper place to catch it.

After applying any `--status=` change (step 4 above), run the same check `scan`/`verify` use
(`python3 scripts/row_budget.py check --file <path> --id <ID>`, or the char-count fallback) on
the cell just written. If the edit pushed the Status or Finding cell **past the soft budget**
(400 chars), offer the split inline rather than waiting for the user to hit it on a later
`scan`:

> "This status update pushes the row to 512 chars (budget: 400). Split into a bounded index +
> detail block now? (`/unforget verify --fix` would offer this later anyway.)"

**Advisory, never blocking.** This is a same-shape offer to the companion-skill handoff above:
surfaced once, easy to decline, never refused by `edit` itself. `edit`'s job is applying the
requested change; the split offer is a courtesy that catches the common case (one more status
line pushes an already-long row over) before it becomes a `verify`-blocking error later. If
the user declines, the change still applies — declining only means the row stays flagged at
the next `scan`/`verify`.

**Skip the offer** when the edit is not a status change (e.g. `--target=` or `--urgency=`
alone touch neither prose cell) or when the cell was already over budget before this edit (it
already surfaced at the last touch; don't re-nag on every subsequent edit to the same
over-budget row — one offer per edit that CROSSES the threshold, not one per edit to a row
already past it).

### Closure handoff (when marking a row done — format v2+)

When `/unforget edit <ID> --status=done` closes a row, unforget MAY offer a **companion-skill handoff** — a function-based recommendation fired at this earned transition. The full mechanic (the five functions, the global manifest, install-state detection, governance) is `reference/skill-handoffs.md`; this is the operational summary. It **supersedes** the older inline `/radar-suite` + `/bug-echo` prose: those hardcoded two URLs at the trigger and detected installs by *directory name* — both are the anti-patterns the handoff design fixes (one manifest, invocable-name detection).

**Which function fires:**
- closing a **code fix** (non-trivial closure) → `post-fix-sibling-scan` (default: bug-echo — generalize the fix, find its siblings).
- closing an **audit-finding** row → `audit-reverify` (default: radar-suite — confirm it held).

**How to express it** — resolve the function against what the session reports invocable, and say the resolver's `expression` verbatim:

```
python3 scripts/companions.py resolve --function post-fix-sibling-scan \
    --invocable "<the session's invocable skill names, comma-separated>"
```

The `--invocable` list is the AUTHORITATIVE install signal (the one-star-risk lesson: detect by invocable name, NEVER a dir find). The resolver returns one of three states: **installed** → "Run `/bug-echo` — …" (no URL); **not-installed** → one soft pointer with the manifest URL; **unset** → "no skill mapped … consider mapping one" (no URL invented). Surface exactly one line.

**Governance (the restraint — `reference/skill-handoffs.md` §5):**
- **At most once per function per session.** Ten code-fix closures offer the scan once, batched ("3 code-fixes closed — run `post-fix-sibling-scan`?"). Track which functions already fired this session.
- **A TRIVIAL close fires NOTHING.** A one-line typo / single-character / isolated-state fix gets no handoff. Only a closure that touched architecture, types, or a shared pattern earns one.
- **Suppress entirely when:** the status change was Open→Skipped/Deferred (not actually fixed), a no-op (done→done), the closure narrative is too short (< ~50 chars) to suggest a pattern, or the row is a non-code observation (a process/skill note).
- **Advisory, never blocking, never a defer.** The handoff means "do the scan NOW, while context is hot." "I'll run bug-echo later" logged as a row is deferral-laundering — the handoff's whole point is do-it-now.

The recommendation is informational; the user can ignore it and move on.

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
  - **stale-recall** (warn, only with `--recall-file`) — the maintained recall block's content doesn't match the registry → offer to rewrite it (`scripts/recall_block.py write`) if maintained; if manual, just warn.
  The helper is **read-only** — it reports; you walk the fixes with the user (register the stranded file, rewrite the recall block, correct the posture). Exit 1 means drift was found. See `reference/init.md` § Phase 6b migration and `reference/registry.md`.
- **Recall-block maintenance (format v2+):** when the registry's recall mode is `maintained`, after importing new rows or registering a found ledger, refresh the Deferred Work Index block: `python3 scripts/recall_block.py write --file <recall-file> --dir <ledger-dir>`. It rewrites only between its markers; the user's surrounding content is untouched. This is what keeps the block from rotting between sessions.
- **Branch auto-suggest (format v2+):** after importing, if the newly-added rows reveal a repeated pattern that clears the `reference/branching.md` §3 cascade to "new ledger" for **≥2 related items** (same actor / lifespan-scope / subject cluster), `import` may *offer* a `/unforget branch` — naming the pattern it saw, never branching unilaterally, at most once per pattern. `import` is the more likely place to catch this than `add`, since it surfaces a batch at once (e.g. several stranded ledgers or a cluster of user-only findings). See `/unforget add` § Branch auto-suggest and `reference/branching.md` §6.

`/unforget import` is the second-most-important command after `/unforget add`. It's how the skill stays current with the project's evolving deferral surfaces.

---

## /unforget list

Show current state. Default view is sorted by Target (🔴 THIS first), then Urgency (CRITICAL first).

### Usage

```
/unforget list                        ·  full table (--view=all --group-by=target, unchanged default)
/unforget list --target=THIS          ·  only ship-blockers
/unforget list --section=audit        ·  only Section 3
/unforget list --status=open          ·  filter by @status value (open/in-progress/done-verified/done-unverified/blocked/withdrawn)
/unforget list --stale                ·  only rows past their staleness threshold
/unforget list --age=30+              ·  only rows older than 30 days
/unforget list --view=<mode>          ·  all | open | done | split | next (see § View modes)
/unforget list --group-by=<axis>      ·  target | section | none (see § Grouping)
/unforget list --ledgers=<names>      ·  read across named sibling ledgers (see § Multi-ledger scope)
/unforget list --all-ledgers          ·  read across every registered ledger (see § Multi-ledger scope)
/unforget list --fresh                ·  re-run the display-preference interview, then list (see § Display-preference interview)
```

**Status is read from the `@status` token** (format v2+), not the prose — via `python3 scripts/parse_status.py --file <path>`. Two consequences:

- `--target=THIS` "ship-blockers" counts a 🔴 THIS row as blocking unless its token is `done-verified` or `withdrawn`. **A `done-unverified` THIS row is STILL a blocker** — it is not proven (the script returns `blocks_release:true` for it).
- `--status=<value>` filters on the token value. Legacy tokenless rows match their old word-status loosely (`Open`→`open`, `Fixed`→a done-* state). It is more granular than `--view` (e.g. `--status=blocked` alone has no `--view` equivalent) and keeps working unchanged; `--view=open`/`--view=done` are the named, common-case spellings for the two buckets most requests actually want.

### Output format

The skill renders the matching rows in the same 10-column format as UNFORGET.md, with a one-line summary at the top:

> "12 rows total: 2 🔴 THIS (release blockers), 5 🔵 NEXT, 5 ⚪ SOMEDAY. Stale: 1."

For the simplest case (`/unforget list` alone), this is the answer the user was actually looking for when they asked "what's deferred?"

**Archive nudge:** after the list output, if 5 or more Fixed/Done rows are sitting in the active tables, append the one-line archive nudge (see `/unforget archive` § The archive nudge). This is the moment the user is already looking at the ledger, so it is where accumulated-completed-row clutter is most usefully surfaced.

**Session defer/fix readout (format v2+):** after the list, append the deferral-gate session readout — `python3 scripts/defer_tally.py readout --dir <ledger-dir>` — as one line, e.g. `This session: 2 fixed inline · 7 deferred (reasons: 3 user-decision, 2 external-block, 2 scope).` When the helper raises the defer-heavy flag (exit 1), also append its advisory (`"7 deferred vs 2 fixed this session — worth a pass to see if any are actually do-now?"`). This is **advisory, never a prompt** — some sessions are legitimately defer-heavy (planning, blocked-on-devices). The reason breakdown is the point: 7 all-`user-decision` is legitimate, 7 all-`scope` is a tell. See `reference/deferral-gate.md` §4. Skip silently on a v1 ledger with no tally state.

### View modes (`--view=`)

**Why this exists.** The default single-table view interleaves open and closed work sorted by Target/Urgency, so a reader answering "what's actually left before ship?" has to visually filter out every `done-verified` / `withdrawn` row while scanning — on a ledger with 40+ rows across a dozen sections' worth of history, that's real work, and it's easy to misread a row's *current* status when the Status cell also narrates its history (a row that was open, got fixed, regressed, and got fixed again reads as a paragraph, not a token). `--view` does that filtering once, mechanically, instead of asking every reader to redo it — and separates "which rows" (`--view`) from "how grouped" (`--group-by`, next section) so the flag surface doesn't grow one bespoke flag per request.

**Status classification for every mode below** is via `python3 scripts/parse_status.py --file <path>` — the same source of truth `--status` already uses, no new parsing logic:

- **Open bucket** — every row where `archivable` is `false`. This includes `open`, `in-progress`, `blocked`, and **`done-unverified`**. A `done-unverified` row has code written but not proven against reality (device test, Sentry re-check, macOS build, etc.) — per `reference/status.md`, that is still open work, not done work, so it belongs in Open, not Completed. **This rule is load-bearing across every mode, not incidental** — a `--view` that put `done-unverified` in Completed would just relocate the exact misreading this feature exists to fix.
- **Completed bucket** — every row where `archivable` is `true`: `done-verified` or `withdrawn`.
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

**`--view=next`**: no table. A single recommended row plus a one-line reason, drawn from the Open bucket only (a Completed row is never "next"). Ranking is a **composite score**, shown in the reason so the pick is inspectable rather than a black box:

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

**Default is single-ledger, unchanged.** `/unforget list` (no scope flag) reads only the
ledger it's pointed at, exactly as today. Cross-ledger reads are opt-in, never automatic —
a project's sibling ledgers exist because their work was deliberately kept separate (a
different actor, a different lifespan/discipline, a different domain; see
`reference/branching.md` §2 for the three axes), and silently unioning them by default would
work against that separation the first time someone ran a routine `list` and got, say,
sprint-scoped rows mixed into a release read.

**Scope comes from the registry, not from re-discovering files.** The registry already
records every ledger's `role` (`main`/`child`), `axis`, `parent`, and `death` condition
(`reference/registry.md` § The schema) — that's the authoritative sibling declaration, and
this feature adds no new registry field. `--ledgers=`/`--all-ledgers` read that existing
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
once in the registry and invoked per-call, keeps the default behavior stable and keeps scope a
decision the user makes, not one the tool infers.

**Composes with `--view` and `--group-by`.** `--all-ledgers --view=split --group-by=section`
is a legitimate combination: union everything registered, bucket into Open/Completed, group
each bucket by section — with the Ledger column making clear which file each row's section
label belongs to.

### Algorithm fallback (Python unavailable) — `--view`, `--group-by`, `--ledgers`/`--all-ledgers`

The base `list` filters (`--target=`, `--section=`, `--status=`, `--stale`, `--age=`) are simple
enough to apply by eye against the rendered table and have never needed a fallback. The three
additions in this file do, because they depend on logic beyond "filter the visible columns":

- **`--view=open` / `--view=done`:** for each row, read its `@status` token per
  `reference/status.md`'s fallback (first-cell-BACKWARD-scanned `@status:` token; ignore any
  token that appears earlier in the row, e.g. inside Finding prose, per the v2.1.0 quoted-token
  fix). `open`/`in-progress`/`blocked`/`done-unverified` → Open bucket. `done-verified`/
  `withdrawn` → Completed bucket. Legacy tokenless rows: word `Open` → Open bucket, word `Fixed`
  (or equivalent closed word-status) → Completed bucket. A row matching neither → Unparsed.
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

### Display-preference interview (`--fresh`)

**Why this exists.** `--view`/`--group-by`/`--section`/wide-vs-compact are all opt-in flags with
a hardcoded default (`all`/`target`/every-section/auto-width) — a user who always wants the same
shape has to keep re-typing it, or live with the default. `--fresh` is the explicit request to
set (or re-set) that default once, interactively, so every *plain* `list`/`scan` call afterward
applies it silently with no prompt.

**`--fresh` ALWAYS re-interviews — it never reads the cache to decide whether to ask.** This is
the one deliberate exception to "don't nag": the whole point of typing `--fresh` is to be asked
again, distinct from a bare `list` (which must never prompt) and from re-reading the ledger from
disk (a separate, unrelated meaning of "fresh" — re-run against live state — that a bare
`list`/`scan` already does on every call by not caching row content).

**Step 0 — the depth gate, every `--fresh` call, no exceptions:**

> "How much do you want to set? **Quick** (1 question — just a view preset) · **Standard** (3-4
> questions — view, grouping, sections, verbosity) · **Thorough** (Standard + staleness
> thresholds, archive-nudge threshold, multi-ledger union default)."

The chosen depth governs ONLY this run of the interview — it is not itself saved. Answer with
`AskUserQuestion` (or the CLI equivalent); this is the one question `--fresh` cannot skip.

**Quick (1 question):** a single view-preset pick, mapped straight to `display_view` (+ a sane
paired `display_group_by`, not asked separately):
- "What's left" → `display_view=open`, `display_group_by=target`
- "Everything" → `display_view=split`, `display_group_by=target`
- "What's next" → `display_view=next`, `display_group_by=target`

**Standard (adds, each independently skippable — see below):**
- View mode (`all`/`open`/`done`/`split`/`next`) — same five choices as `--view=`.
- Grouping (`target`/`section`/`none`) — same three choices as `--group-by=`.
- Default section scope (`display_sections`) — **`all` (every section) or ONE named section**
  (`paused` / `spillover` / `audit` / `observed`), matching what `--section=` actually accepts.
  ⚠️ Do NOT offer an arbitrary multi-section subset: every documented `--section=` usage is
  singular (`--section=audit`, "only Section 3"), so a saved subset would imply a filter
  capability the underlying flag does not have. If `--section=` is ever widened to accept a
  comma-separated list, widen this question at the same time — not before.
- Verbosity (`display_verbosity`) — **`auto` (default) / `full` / `compact`.** `auto` preserves
  the existing terminal-width auto-detection (§ Terminal-aware rendering: ≥120 cols → full
  10-column, <120 → compact 6-column projection); `full`/`compact` pin the width regardless of
  terminal size, the saved-default equivalent of the per-call `--wide`/`--compact` overrides.
  ⚠️ **`auto` must be the default and the skip-value.** Saving a pinned `full` permanently
  defeats the auto-fallback that exists *because* the 10-column table is unreadable under 120
  columns — a user who answers "full" on a wide monitor would otherwise get a wrapped mess on a
  laptop forever, with no signal why. Pinning is a deliberate power-user choice, never a
  side effect of answering a setup question.

**Thorough (adds, also independently skippable):**

- Staleness thresholds — the four Target-tier day counts from § `/unforget scan`, saved as
  `stale_days_this` / `stale_days_next` / `stale_days_later` / `stale_days_someday`
  (defaults 30 / 90 / 180 / 365). Offer them as one grouped question, not four separate ones;
  skipping keeps every current value.
- Archive-nudge threshold (`archive_nudge_threshold`, default 5; `0` silences the nudge) — see
  `/unforget archive` § The archive nudge.
- Multi-ledger union default — whether a plain `list` (no `--ledgers=`/`--all-ledgers` flag)
  should behave as if `--all-ledgers` were always passed. Default stays no (§ Multi-ledger
  scope's opt-in-only design is not overridden by this — the interview can only change what a
  BARE `list` defaults to, never make cross-ledger reads silently automatic without the user
  having chosen that here).

**Every question past Q0 is skippable — "keep current / use default" is always an explicit
option, never buried.** A user who picked Standard or Thorough to get more control is not then
forced to answer every field; skipping one leaves that key's prior value (or the hardcoded
default, on a true first run) untouched. This mirrors the `edit`/`branch` guard pattern
elsewhere in this skill: offering more control is not the same as requiring more input.

**First-run framing differs from re-run framing (same questions, different lead-in) — this is
presentation only, not a second code path:**
- **No `display_prefs_set` in the registry yet (true first run):** lead with "No display
  preference saved yet for this ledger." before Q0.
- **`display_prefs_set: true` already (an explicit re-run):** lead with "Currently: view=<X>,
  group-by=<Y>[, ...]. Want to change it?" before Q0, so the user sees what they're revising
  rather than re-answering blind.

**Writing the result.** After the interview (at whatever depth), write the answered keys — and
ONLY the answered keys; skipped questions leave their prior registry value untouched — via:

```
python3 scripts/registry.py write --dir <ledger-dir> --json <payload> --merge
```

🛑 **`--merge` is MANDATORY here and the payload must contain only the answered keys.** `write`
without `--merge` REPLACES the whole block: a payload of `{"global": {"display_view": "open"}}`
renders a registry in which every other global key is `(unset)` **and the entire Ledgers table
is empty** — measured, not theorized (2026-08-13: a bare write against a 9-key/3-ledger registry
left 0 ledgers registered). That is precisely the stranded-ledger failure the registry exists to
prevent, so the partial-write path must never be taken without `--merge`. With `--merge`, keys
absent from the payload keep their current value and the ledger table is preserved untouched.
Always set `display_prefs_set: true` on ANY
completed interview, even Quick-depth with just one answer, so a later bare `--fresh` gets the
re-run framing instead of the first-run one. Then run `list` (or `scan`, if invoked via
`scan --fresh`) using the just-saved preferences.

### Runtime execution: the `--fresh` flow, step by step

The steps below are what actually RUNS when a user types `list --fresh`. Each step names the
helper call or the question; the ordering is load-bearing (framing must precede Q0, the write
must precede the render, and nothing may prompt outside steps 2-4).

**Step 1 — framing (no prompt).** `python3 scripts/display_prefs.py framing --dir <ledger-dir>`.
Print the returned `lead_in` verbatim as one line. Do not paraphrase it — it is the only
signal distinguishing "you haven't set this yet" from "here's what you're revising," and a
re-run that reads like a first run makes the user re-answer blind.

**Step 2 — Q0, the depth gate (one `AskUserQuestion`, cannot be skipped).** Offer exactly the
three depths, Quick first (it is the common case, and the header/label limits mean the depth
labels must stay short):

| Option label | Description shown |
|---|---|
| `Quick` | 1 question — just a view preset |
| `Standard` | 3-4 questions — view, grouping, sections, verbosity |
| `Thorough` | Standard + staleness thresholds, archive nudge, multi-ledger default |

If the user dismisses Q0 rather than answering, **abort the interview and render the list with
existing settings** — a dismissed question is not an answer, and a read command must never be
left half-configured. Say one line: "Interview cancelled — listing with current settings."

**Step 3 — the depth-appropriate questions (one `AskUserQuestion`, batched).** Ask the chosen
tier's questions **in a single call with multiple questions**, not one call per field: four
sequential prompts for Standard would make the interview feel like an interrogation, and
`AskUserQuestion` takes up to 4 questions per call for exactly this reason. Quick is 1 question;
Standard is 4; Thorough is Standard's 4 followed by a SECOND call carrying its extra 3 (the
4-question cap forces the split — do not silently drop the overflow).

Every question in this step carries an explicit **"Keep current"** option (first position, and
labelled with the current value when one exists, e.g. `Keep current (open)`). That is what makes
"independently skippable" real rather than aspirational — a skip must be one visible click, not
a dismissal the user has to guess is safe.

**Step 4 — write (no prompt).** Convert the answers, dropping every "Keep current":

```
python3 scripts/display_prefs.py build-patch --view <v> [--group-by <g>] [...]
python3 scripts/registry.py write --dir <ledger-dir> --json <payload> --merge
```

🛑 Take `build-patch`'s `global` object as-is and pass `--merge`. Never hand-assemble the
payload and never omit the flag — see the merge warning below.

**Step 5 — render (no prompt).** `python3 scripts/display_prefs.py resolve --dir <ledger-dir>`
with any flags the ORIGINAL command also carried, then render `list` using the resolved
settings. Confirm what was saved in one line — "Saved: view=open, group-by=target. Future
`list` calls use this; `--fresh` to change." — so the user knows the setting persisted and how
to revisit it, without a second prompt.

**`scan --fresh`** runs the identical five steps and then renders `scan` instead of `list`.
The interview is shared; only the final render differs.

**Interaction with the other flags.** `--fresh` composes with everything: `list --fresh
--target=THIS` interviews, saves, then renders THIS-only. A flag passed alongside `--fresh`
applies to the render (step 5) but is NOT saved as a preference — saving happens only from
interview answers, so a one-off filter can never silently become a permanent default.

**Preferred implementation.** The deterministic halves — precedence, defaults, validation, and
building a safe merge payload — are `scripts/display_prefs.py`; the interview's *judgment*
(which questions, how worded, whether an answer makes sense) stays with the LLM, the same split
`defer_tally.py` draws for the deferral gate:

```
python3 scripts/display_prefs.py framing --dir <ledger-dir>          # first-run vs re-run lead-in
python3 scripts/display_prefs.py build-patch --view open [...]       # answers -> a --merge payload
python3 scripts/display_prefs.py resolve --dir <ledger-dir> [flags]  # effective settings for this call
```

- `framing` returns `{first_run, current, lead_in}` — use `lead_in` verbatim before Q0.
- `build-patch` emits `{global, requires_merge, write_command}` containing ONLY answered keys
  plus `display_prefs_set`; feed its `global` to `registry.py write --merge`. A skipped question
  is omitted, never written as null (an explicit null would CLEAR the prior value — the opposite
  of skipping).
- `resolve` applies `flag > registry > default` and reports a `sources` map naming which layer
  each value came from, so a surprising render is inspectable rather than mysterious. Pass
  `--term-width` to have `verbosity=auto` resolve to `full`/`compact`; omit it to get
  `effective_width: null` and do your own detection.
- **Fails safe by construction:** a missing README, an unparseable value, or a bogus enum
  (`display_view: banana`) all fall back to the hardcoded default rather than raising — a read
  command must never be taken down by a malformed tunable. A stray `display_*` key with no
  `display_prefs_set: true` is treated as absent, so a half-written registry cannot silently
  change how `list` renders.

**Plain `list`/`scan` (no `--fresh`) — silent read, no prompt, ever.** If `display_prefs_set` is
`true` in the registry, apply `display_view`/`display_group_by`/`display_sections`/
`display_verbosity` (and, at Thorough, the staleness/archive-nudge/multi-ledger keys) as the
call's defaults — exactly as if the user had passed the equivalent flags. An explicit flag on
the call (`list --view=next`) always overrides the saved preference for that one call; the
saved preference only fills in what wasn't explicitly passed. If `display_prefs_set` is absent
(no interview has ever run), fall back to today's hardcoded defaults (`--view=all
--group-by=target`, every section, auto-width) — a read command must never block or nag waiting
for setup that was never done. This is the same "advisory, never blocking" discipline as the
deferral gate's tally and the char-budget write-time offer elsewhere in this skill.

**Scope: per-project, in this ledger's registry — not global.** `display_prefs_*` lives beside
`policy_deferral`/`git_posture` in the SAME per-directory registry (`reference/registry.md` §
The schema), not in a `~/.claude`-level file. A project with unusual needs (e.g. a ledger that
unions several sibling ledgers by convention) can set its own defaults without affecting any
other project's ledger. A sibling ledger (`TERRY-UNFORGET.md`, `MI-UNFORGET.md`) has its OWN
registry row but shares the SAME `display_prefs_*` global keys as its parent (the global block
is one per registry file, not per ledger-row) — running `--fresh` while pointed at a child
ledger sets the shared project-wide preference, same as running it against the parent.

**Algorithm fallback (Python unavailable):** ask Step 0, then the depth-appropriate questions
above via plain text prompts (numbered choices), skipping any the user doesn't answer. Read the
registry's Global table by hand (`reference/registry.md`'s own fallback), patch in the
`display_*` keys the user answered plus `display_prefs_set: true`, and rewrite the whole
`**Global**` table preserving every other key verbatim (do not drop unanswered/unknown keys).

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

---

## /unforget show

Show ONE row's current state as a short, synthesized read: what's wrong, its impact, and the
fix. No table, no accreted history. This is the read-time answer to a problem `list`/`--view`
can't solve on their own: a row's rating columns compare well across many rows, but its Detail
block is an append-only history log (`reference/format.md` § Row-length discipline) that grows
without bound and is never re-summarized. A reader who scrolls to a row's detail today gets the
FULL accreted narrative — every arc, every reversal, every "still owed" and "RESOLVED" in the
order they were written — when what they almost always want is: what's true about this row
right now. `show` renders that, on demand, per row, instead of asking every row to compress
itself into an already-crowded table cell (which is what the char-budget rule does) or asking
every reader to mentally re-derive "current" from a paragraph of history (which is what caused
the 2026-08-13 A65 misread this feature traces back to).

### Usage

```
/unforget show A65                    ·  synthesized current-state card for row A65
/unforget show A65 --full             ·  the synthesis, THEN the complete raw Detail-block history below it
```

### What gets shown

Three fields, always in this order, each one to three sentences:

- **Finding** — what's wrong, current tense. Not "was buried" if it's now fixed; not "fixed"
  if a later event reopened it. Reflects the row's LATEST arc only.
- **Impact** — why it matters if left as-is. Pull from the row's Risk:No-Fix column and/or the
  Detail block's own stated consequence, not re-derived from scratch.
- **Fix** — what closes it, or what's blocking closure. For an `open` row: the proposed
  approach. For `done-unverified`: what's already done and specifically what verification step
  remains (device test, macOS build, Sentry re-check, etc.) — name the step, don't just say
  "unverified." For `done-verified`/`withdrawn`: one line confirming what happened and how it
  was proven.

Below the three fields, one line of provenance: `<ID> · <Target> · <@status token> · last
touched <date if known>`. This is the ONLY place the raw token appears in `show`'s default
output — the three fields above are prose, not a re-print of table cells.

### How the synthesis is derived (mechanical, not model-generated)

**Deterministic extraction, not an LLM call per row.** A summary generated fresh by the model
at display time would be more fluent, but non-deterministic between runs and too expensive to
default to when `list --view=next` or a future batch flow might want this per row across many
rows at once. Instead:

- **Finding and Impact** come from the row's own table cells (Finding, Risk:No-Fix) — these are
  already supposed to be current-state, single-sentence fields per the row-length discipline
  rule; `show` is mostly reformatting them into prose, not inventing new text.
- **Fix** is derived from the LAST dated entry in the Detail block's history (§2b: "a status
  CHANGE appends a dated line to the detail block; the table cell's one-line status is REPLACED
  to the latest" — so the most recent dated line IS the current fix-state by construction, not
  a guess). If the Detail block has no dated history yet (a freshly logged row), fall back to
  the row's Finding cell's own stated fix, if any.
- **This is why §2b (history is appended to the block, REPLACED in the cell) matters more than
  it looks:** `show`'s reliability depends on "most recent dated entry = current truth" holding.
  A ledger that violates §2b (appends new arcs without dating them, or buries the current state
  mid-block instead of at the end) will make `show` synthesize a stale or wrong Fix. This is a
  reason to enforce §2b more than it is a reason to complicate `show`'s extraction logic.
- **No caching, no write-back.** `show` recomputes from the current file on every call. A
  cached summary is one more artifact that can drift from the history under it — precisely the
  staleness problem this feature exists to fix. The recomputation is cheap (regex/string
  extraction, not a model call), so there's no performance reason to cache.

### `--full`: the escape hatch

`--full` prints the synthesis card, then a `---`, then the row's complete raw Detail-block
content verbatim — unabridged, in original order, nothing summarized or dropped. This is not a
fallback for when the synthesis is wrong; it's how a reader gets the FULL history when they
genuinely need it (auditing a reversal, understanding why an earlier fix didn't hold, writing a
postmortem). **Nothing is ever deleted or hidden from the file** — `show`'s default view is a
different lens on the same content, not a smaller copy of it. This is the same non-negotiable
as the row-length split's hard rule ("the budget MOVES history to the detail block; it NEVER
deletes it") applied one level up: showing less by default never means keeping less on disk.

### Failure modes

- **Row not found:** exact error naming the ID and the file searched, no guessing at a close match silently.
- **Row has no Detail block at all** (either never split, or the pointer is broken — this is
  exactly what `reference/verify.md`'s `detail-pointer` check flags; `show`'s job here is to
  degrade gracefully at read time, not to run that check itself): synthesize Finding/Impact from
  the table cells alone, and say so explicitly in the Fix line (`"No detail history on file —
  fix approach not recorded."`) rather than inventing one.
- **Multiple ledgers, ambiguous ID:** if `--ledgers=`/`--all-ledgers` scope is active (see
  § Multi-ledger scope under `/unforget list`) and the ID exists in more than one registered
  ledger, `show` asks which one rather than picking silently.

### Algorithm fallback (Python unavailable)

Locate the row by ID in the ledger's table (same lookup `edit`/`list` already do). Extract:

- **Finding** — the row's Finding cell, minus any `**bold title**` markup, minus any
  `→ see detail block **<ID>**` pointer text, rewritten as a plain current-tense sentence (drop
  parenthetical asides and file:line citations — those belong in the Detail block, not the
  synthesis).
- **Impact** — the row's Risk:No-Fix cell, rewritten as prose the same way.
- **Fix** — find the `### Detail - <section>` block matching this row's section, then the
  `- **<ID>** -` bullet within it. If the bullet contains a `**Status history:**` sub-line (the
  v2-format dated-history convention), take the LAST dated or most-recently-appended clause in
  it — per § How the synthesis is derived above, the row-length discipline's §2b rule (history
  is appended, the cell is replaced to latest) means the last entry IS the current state, not
  merely the most recent claim. If the bullet has no dated sub-line, take the bullet's own last
  sentence. If no bullet exists for this ID at all, fall back to any fix-shaped clause already
  present in the Finding cell, and if none, say plainly that no fix approach is on record — do
  not synthesize one.
- Render the three as short prose paragraphs, then the one-line provenance
  (`<ID> · <Target> · <@status token> · <date if the Detail bullet carries one>`).
- **`--full`:** after the synthesis, print a `---` divider, then the row's Detail-block bullet
  verbatim, unedited, in full.

This is table-and-string manipulation only — no ranking, no cross-row logic — so the fallback
is a close mirror of the preferred implementation, not a simplified approximation of it.

### Interactive presentation (optional, environment-gated)

**Markdown is the baseline and the fallback everywhere.** The three-field card above renders
as plain markdown — headings, prose, nothing else — because `unforget` is explicitly meant to
work in "any editor, on GitHub, in Linear" and for "other AI assistants" beyond Claude Code
(`reference/../SKILL.md` § Compatibility notes). A feature that only worked in one rendering
environment would contradict that portability goal, so nothing above this line depends on any
capability beyond writing text to stdout.

**Where a richer interactive surface is available, `show` MAY offer it instead — never as a
silent substitution, always as an explicit choice.** Concretely, in an environment that
supports rendering an interactive HTML/widget view (for example, Claude's `Artifact` or
`show_widget` surfaces), `show <ID>` with no other flags still prints the markdown card by
default, and additionally offers: `"Render this as an interactive card? (click-through to full
history, no scrolling)"`. Only on explicit accept does it build a small self-contained view:

- **List-then-detail, not a permanent dashboard.** The pattern that worked when this was
  demoed: a compact one-line-per-row list (ID badge + finding, no rating columns — those stay
  in the terminal table, this is a reading surface for ONE row at a time) that expands into the
  same three fields (Finding / Impact / Fix) on selection, with a `--full`-equivalent link/toggle
  back to the raw Detail block for that row only.
- **Never the table's replacement.** The interactive view has NO rating columns (Urgency, ROI,
  Risk, Effort) and is not meant to answer "what should I work on next" — that comparison task
  stays in `list`'s table, full stop (see the earlier discussion: comparison and single-row
  reading are different tasks, not competing views of the same data).
- **Generated fresh per call, matching the markdown baseline's no-cache rule.** The interactive
  view is built from the same deterministic extraction `show` already does — it is a different
  renderer for the same computed fields, not a separate feature with its own logic or its own
  drift risk.
- **Degrades to nothing, never to broken.** In any environment without this capability, `show`
  behaves exactly as the baseline section above describes and never mentions the interactive
  option — no dead flag, no "not supported here" error. The offer only appears where it can
  actually be fulfilled.
- **A future `/unforget list --interactive` (or similar) extending this to the multi-row list
  itself is a natural next step but explicitly NOT specified here** — this section covers
  single-row `show` only, since that's the concrete case that was designed and demoed. Widening
  it to `list` would need its own pass at how rating-column comparison and card-based reading
  coexist in one view, which is a real design question, not just "reuse the same renderer."

---

## /unforget scan

Identify rows past their staleness threshold. Read-only. Never modifies the file.

### Staleness thresholds (default)

| Status / Target | Stale after |
|---|---|
| Status = Open or In Progress | 30 days |
| Status = Deferred AND Target = 🔵 NEXT | 90 days |
| Status = Deferred AND Target = 🟡 LATER | 180 days |
| Status = Deferred AND Target = ⚪ SOMEDAY | 365 days |
| Status = Skipped | never stale |
| Status = Fixed | never stale (but flag as ready-for-archive) |

These thresholds are customizable via the registry's `stale_days_this` / `stale_days_next` /
`stale_days_later` / `stale_days_someday` keys (`reference/registry.md` § The schema), settable
through the Thorough tier of `/unforget list --fresh` (§ Display-preference interview) or by
hand. A legacy `config` block at the top of UNFORGET.md is still honored if present, but the
registry wins when both are set — see the migration note in `reference/registry.md`.

### Row-length (char-budget) lint (format v2+, maintenance §2c)

`scan` also flags rows that have outgrown the **index budget** — the exact bloat that made a ledger un-Readable (multi-KB rows, Reads that truncate and mislead). Run `python3 scripts/row_budget.py check --file <UNFORGET.md> [--dir <ledger-dir>]`; it returns every Finding/Status cell over the budget (default 400 chars, or the registry's `row_char_budget`). Surface these under an **"Over the index budget (move history to a detail block)"** heading with the cell and its char count, recommendation **investigate** (usually resolvable by a split). This is read-only in `scan`; the split itself is offered by `verify --fix` (below) or run manually. See `reference/format.md` § Row-length discipline.

### Trivial-staleness cross-check (format v2+, deferral-gate §4d)

`scan` sharpens one flag that ties back to the deferral gate: a row that is **Fix
Effort = Trivial AND has survived ≥N sessions un-done** is a near-certain
"should've just done it" — triviality + staleness together is the hindsight
signal that a past deferral was deferral-laundering. Surface these under a
**"Trivial-but-stale (should've been do-now)"** heading in the scan output with
recommendation **investigate** (usually resolvable to a quick do-now). `N` is
registry-configurable via `stale_trivial_sessions` (read from the registry global
block); this is how the user *learns* the pattern over time, not just catches it
in the moment. Read-only like the rest of `scan`. On a v1 ledger with no effort
column populated, this cross-check is skipped.

### Output structure

```
# UNFORGET.md Stale-Scan, <date>

**Ledger snapshot:** N rows across 4 sections.
**Stale rows:** N
**Needs date stamp:** N
**Fixed rows ready for archive:** N

## Stale items
| ID | Target | Status | Age (days) | Title | Recommendation |
| ... |

## Needs date stamp
| ID | Target | Title |
| ... |

## Fixed rows ready for archive
| ID | Title |
| ... |

## Summary
<2-3 sentence narrative covering: how many rows are healthy, which sections need
the most attention, any patterns worth surfacing.>
```

### Recommendation values

For each stale row, the scan picks ONE:

- **investigate**: stale and may need fresh diagnosis
- **promote**: should move toward THIS (e.g., NEXT deferred too long)
- **demote**: Urgency was overstated; downgrade Target
- **archive**: no longer relevant; move to historical archive

Default to **investigate** if uncertain. The scan never modifies UNFORGET.md. It only reports.

### Scheduling

`/unforget scan` is safe to run on demand. For automated recurring scans, the user can schedule it via Claude Code's `/schedule` skill (or any cron-like external scheduler). The skill output is plain markdown, suitable for posting to Slack, email, or GitHub Actions summary.

---

## /unforget branch

Atomically create a **child ledger** (format v2+). The everyday default is NOT to branch — most deferred work is a row or a section. A new ledger is justified only when the work differs from the parent on one of three axes (actor / lifespan / domain). **Full model, the decision cascade, and the anti-patterns: `reference/branching.md`** — read it before running this. This section is the operational summary.

### Usage

```
/unforget branch <name> --axis=<actor|lifespan|domain> [--parent=<ledger>] \
    [--discipline="<one line>"] [--death="<condition>"] [--target=SOMEDAY] [--dry-run]
```

### The axis decision is YOURS; the write is the script's

Deciding *whether* to branch and *on which axis* is judgment — walk the §3 cascade in `reference/branching.md` (first "no-branch" answer wins: trivial → do-now; same actor/lifespan/dir → a row; subject-only → a section; only a real axis difference → a ledger). Do NOT branch to avoid reconciling a messy ledger (that's avoidance, a cousin of deferral-laundering). Once the axis is settled, the **atomic write** is deterministic:

```
python3 scripts/branch_create.py --dir <ledger-dir> --name <name> \
    --axis <actor|lifespan|domain> --parent <parent-file> \
    [--discipline "<one line>"] [--death "<condition>"] [--actor-is-human] [--dry-run]
```

### Steps

1. **Confirm the axis** via the `reference/branching.md` §3 cascade. If the work doesn't clear the cascade to "new ledger," STOP — it's a row or a section, not a branch.
2. **Run the helper.** It creates three artifacts **atomically — all, or none**: (a) the child's header (axis, discipline, parent back-pointer, death condition if lifespan) with its own `<!-- unforget-format: v2 -->` marker and empty section tables; (b) the parent's single **pointer row** (never a copy of child rows); (c) the **registry entry**. A failure on any one rolls back the others — no half-branched state.
3. **Honor the guards** (the helper returns them; do not force past them):
   - `refusal` "already a registered ledger" → the name is taken; pick another or edit the existing child.
   - `refusal` on `--axis=lifespan` with no `--death` → a lifespan child MUST declare its death condition; ask the user and re-run with `--death="…"`.
   - `needs_confirmation` on `--axis=actor` → the actor axis is **humans only**. Confirm a different *human* acts on the work, then re-run with `--actor-is-human`. A machine/automation actor is a Target value or a status tag inside the actionable ledger, NOT a new file.
   - `advisory` "no --discipline" on lifespan/domain → a same-discipline split is usually a section, not a ledger; state the child's distinct discipline or reconsider.
4. **`--dry-run` first** when unsure — it reports the three artifacts it would write and touches nothing.
5. **Report** all three artifact paths and the next step (`/unforget add --ledger=<name>`).

### The recall block (the 4th atomic artifact, when maintained)

When the registry declares a **maintained** recall block (`recall_block: maintained` + a `recall_file`), `branch` updates it as a **fourth atomic artifact** — it rebuilds the marker-delimited Deferred Work Index from the just-updated registry so the new child appears immediately (else the block goes stale the moment the child is created). Pass `--recall-home "<display path>"` for the header. This artifact rolls back with the others on any write failure. When there is **no** maintained recall block (a `manual`/`none` project, or no registry), `branch` simply skips it — the child stays reachable through the parent's pointer row, which points at the canonical index.

### Auto-suggest (offer on a REPEATED pattern, never branch unilaterally)

`add`/`import` may *offer* a branch — but only when the §3 cascade lands on "new ledger" for **≥2 related items** (a pattern, not a one-off). See `/unforget add` § Branch auto-suggest and `reference/branching.md` §6. One item never triggers a suggestion; the skill names the pattern it saw when it offers.

### Backward compatibility

`branch` is a format-v2 command. It writes v2 children. It reads the registry (a v2 feature); on a project with no registry block, register the parent first (via `import`/`init`) so the child has a home and the parent can carry its pointer.

---

## /unforget verify

Read-only integrity lint (format v2+). Audits the ledger for the decay failures a row can hide — a self-contradicting status, an unproven "done", bloat, a stale premise, registry drift — and reports a severity-ranked finding list. Full spec: `reference/verify.md`.

### Usage

```
/unforget verify                      ·  lint the ledger; report findings most-severe first
/unforget verify --char-budget=600    ·  override the per-cell char budget
```

### Steps

1. Run `python3 scripts/verify_ledger.py --file <UNFORGET.md> --dir <ledger-dir>`.
2. Render the findings: errors first, then warnings; each as `[severity] check ID — message`.
3. Report the one-line summary (`N errors, M warnings; gate PASSES/FAILS`).
4. **Report-only by default.** `verify` (no flags) only reports; walk any fix per finding with approval. The one scoped exception is `--fix` for row-length splits (below).

### `/unforget verify --fix` (row-length splits only, format v2+, maintenance §2)

`verify --fix` offers to resolve **char-budget** findings — and only those — by splitting an over-budget row into a bounded index row + a detail block, **per row, with approval**. It never auto-edits contradictions, tiers, or any other finding (those need human judgment). Steps:

1. Run the normal `verify` lint; collect the `char-budget` findings.
2. For each over-budget row, run `python3 scripts/row_budget.py split --file <UNFORGET.md> --id <ID>` (dry-run) and show the plan: the proposed bounded index row and the detail-block bullet.
3. **Confirm per row** (the split moves history; the user should see it). Optionally pass a `--headline "<summary>"` for a better one-line index than the mechanical derivation.
4. On approval, apply with `--apply`. The helper returns `lossless:true` only when every character of the original cells is provably preserved in the detail block, and **refuses** otherwise — so an approved split can never silently drop history.
5. Back up UNFORGET.md before the first split (same discipline as `archive`/`promote`).

`--fix` is strictly additive: without it, `verify` is read-only exactly as before. It exists only because a row-length split is mechanical and lossless-verifiable — the one integrity finding safe to auto-resolve with approval. See `reference/format.md` § Row-length discipline.

### Gate role

`verify` also runs automatically **before `archive` and `promote`**. An error-severity finding (a contradiction, an unproven/`session-claimed` "done", an unknown status value, or a THIS row that claims done but isn't cleanly `done-verified`) **blocks** the ship/relocation decision until resolved — the same discipline as `promote`'s existing 🔴 THIS check. Warnings never block. See `reference/promotion.md` and `/unforget archive` steps.

### Backward compatibility

On a v1 (tokenless) ledger, `verify` emits only warnings (bloat, stale-recipe, open THIS rows) and no errors, so the gate passes. A legacy ledger is never blocked by the token checks.

---

## /unforget archive

Move completed rows out of the active tables into a dated archive file. **Lightweight and safe to run anytime** — this is the everyday cleanup command, distinct from the heavyweight release-time `/unforget promote` ritual (see `reference/promotion.md`). `promote` re-triages the whole release cycle (verify THIS, roll NEXT→THIS, re-rank SOMEDAY, stamp the release line); `archive` does only the one job of clearing finished work out of view.

### Why this exists

`promote` was historically the only command that removed completed rows, but it is a release-submission ritual the user has to remember to invoke. In practice ledgers accumulate dozens of ✅ Done rows that were never cleared because nobody runs `promote` between releases — the single most common way an UNFORGET.md rots. `archive` is the low-friction alternative: one job, no release semantics, run it whenever the active tables feel cluttered. The `list` and `add` archive nudge (below) points here.

### Usage

```
/unforget archive                     ·  archive clean-Done rows (keeps "Done-but-owed" rows — see safety rule)
/unforget archive --dry-run           ·  show what WOULD be archived, write nothing
/unforget archive --all-done          ·  archive every Fixed/Done row, including "owed" ones (skip the safety hold)
```

### Safety rule (the important part): keep "Done-but-owed" rows

Archiving a row that still owes work hides real remaining work — the exact failure this skill exists to prevent. What is archivable is decided by the `@status` token (format v2+):

- **Archive ONLY** `@status:done-verified` and `@status:withdrawn`.
- **HOLD** `@status:done-unverified` — this is the "done-but-owed" state by definition (fixed, not yet ground-truth-checked). It stays in the active tables.
- Never archive `open`, `in-progress`, or `blocked`.

`--all-done` overrides the hold on `done-unverified` (use only when the user confirms the owed check is moot).

**Legacy fallback (tokenless rows):** a row with no `@status` token is classified the old way — a Done/Fixed row is held when its Status or Finding text contains an owed-signal (`pending` / `owed` / `still owed` / `eyeball` / `visual check` / `verify on device` / `device-verify` / `device round-trip` / `delivery test` / `deploy owed` / `not yet deployed` / `awaiting deploy` / `⏳`). This keeps pre-v2 ledgers safe until their rows are upgraded.

### Steps

0. **Integrity gate (format v2+).** Run `/unforget verify` first. If any **error-severity** finding stands (a contradiction, an unproven/`session-claimed` "done", an unknown status value, a THIS row claiming done but not cleanly `done-verified`), **STOP** and report — do not archive over a ledger whose "done" claims aren't trustworthy, because a bad `done-verified` is exactly what `archive` would relocate out of sight. Warnings do not block. A v1 (tokenless) ledger produces no errors and archiving proceeds.
1. **Read UNFORGET.md.** Run `python3 scripts/parse_status.py --file <path>`; a row is archivable when its result has `archivable:true` (i.e. a CLEAN `done-verified` — valid tier, no contradiction — or `withdrawn`). For tokenless legacy rows, fall back to the Fixed/Done + owed-signal heuristic above.
2. **Split** into `archive` (archivable) vs `keep` (`done-unverified`, owed-signal legacy rows, and everything not done). `--all-done` also archives `done-unverified`.
3. **Preview** — show the two lists (IDs + one-line title) and counts: "Archive N clean-Done rows; keep M Done-but-owed rows active." On `--dry-run`, stop here and write nothing.
4. **Confirm** with the user (single AskUserQuestion: proceed / show-full-rows / cancel).
5. **Back up first** — copy UNFORGET.md to a temp path before editing, so a mis-classification is recoverable.
6. **Write:** move the archived rows to `UNFORGET-archive.md` in the same directory as UNFORGET.md (create with a header if absent; append a dated `## Archived <date>` block if it exists). Remove those rows from the active tables. Preserve table structure — section headers and separator rows stay intact.
7. **Report** the before/after active row count and the archive-file path.

`archive` modifies UNFORGET.md, so (like `promote`) it always previews before writing. Unlike `promote`, it does not touch Target values, re-rank anything, or stamp release metadata — it only relocates finished rows. The archive file is never scanned by `init`/`import` (it lives under the archive-path exclusion rule in `reference/surfaces.md`), so archived rows do not re-enter the active backlog.

### The archive nudge (surfaced by `list` and `add`)

To make cleanup discoverable without forcing it, `/unforget list` and `/unforget add` append a one-line nudge when completed rows pile up. After their normal output, count rows whose Status is `Fixed` / `Done` in the active tables; if **5 or more**, append exactly one line:

```
💡 N completed rows are sitting in the active tables — run /unforget archive to move them out.
```

One line, non-blocking, informational — never a prompt or an action. Threshold is 5 by default; the registry's `archive_nudge_threshold` key overrides it (`0` silences the nudge entirely), settable via the Thorough tier of `/unforget list --fresh` or by hand — see `reference/registry.md` § The schema. A legacy `config` block at the top of UNFORGET.md carrying `archive_nudge_threshold: N` is still honored if present, but the registry wins when both are set. On `/unforget add`, skip the nudge if the add itself was slow — `add`'s 30-second speed promise wins; the nudge must never add latency or a question.

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
Version declarations: ✓ SKILL.md, plugin manifest, changelog all agree (2.6.0)
Recall trigger: ✓ installed in CLAUDE.md
```

(The exact companion-file count is whatever `verify_install.py`'s `REQUIRED_COMPANIONS` list holds — report the count it returns, not a hardcoded number.)

When the install is broken or the recall trigger is missing, the last two lines carry the diagnosis instead:

```
Install integrity: ✗ 2 companion files unreachable (reference/commands.md, scripts/scan_surfaces.py)
                     → the router will fail when it delegates to a missing file; reinstall or repair the skill directory
Recall trigger: ✗ no Deferred Work Index block in this project's CLAUDE.md/AGENTS.md
                  → deferred-work questions will NOT auto-route here; run /unforget init to add it
```

The version string is read from the SKILL.md frontmatter `version` field. The install path is detected at runtime: plugin installs report the plugin directory, manual v0.1 installs report `~/.claude/skills/unforget/`. Supported format-version comes from the spec (currently `v1` and `v2`, backward compatible; a future `v3` would list here too once it lands).

### Version reconciliation

The version is declared in **three** places: `SKILL.md`'s frontmatter, `.claude-plugin/plugin.json`, and the newest `### vN.N.N` changelog heading. Nothing used to compare them, so the plugin manifest sat **five releases stale** (2.1.0 while everything else read 2.6.0) with no check noticing — found 2026-08-13, the third instance of doc-vs-code drift in a single session (the others: the changelog describing `verify` checks the code didn't implement, and a test golden pinned to an old version).

`--version` now reconciles all three and reports `versions_in_sync` + `declared_versions`. Rules:

- **Only sources that actually declare a version vote.** A manual (v0.1) install with no plugin manifest is not drift — it simply has one fewer declaration. Same for an unparseable manifest: undeclared, never a crash.
- **SKILL.md's frontmatter is canonical**, because that is what `read_version` — and therefore the `unforget vN.N.N` line above — already reports.
- **Drift is ADVISORY, never a failure.** A stale manifest misreports what is installed; unlike a missing companion file it does not break the router, so it does not fail the command (exit stays 0). A missing companion still exits 1 and still outranks drift in the advisory line.

The line reads `Version declarations: ✗ SKILL.md declares 2.6.0, but plugin_manifest=2.1.0` when they disagree — naming the offending source and both values, so the fix is obvious without hunting.

### Install integrity

The refactored skill (v0.2+) is a thin SKILL.md router that delegates to `reference/*.md` on demand and to `scripts/*.py` for deterministic work. If those companion files did not travel with the install — a copy of only SKILL.md, a partial clone, a broken symlink — the router fails silently the first time it reads a reference file, and the failure surfaces as confusing mid-command behavior rather than a clear error.

`--version` closes that gap. **Preferred implementation:** delegate to `python3 scripts/verify_install.py --skill-root <dir> [--project-root <cwd>]` (returns JSON). It confirms every companion file the router depends on is reachable from the skill root, and — when `--project-root` is supplied — reports whether the recall trigger is installed. Report `integrity_ok` and `advisory` to the user on the two output lines above.

Algorithm fallback if Python is unavailable: for each path in the router's companion table (`reference/format.md`, `reference/init.md`, `reference/surfaces.md`, `reference/promotion.md`, `reference/commands.md`, and the five `scripts/*.py`), test existence relative to the skill root; report any that are missing.

### Recall trigger

unforget only auto-activates on "what's deferred?"-style questions when the project's `CLAUDE.md` / `AGENTS.md` carries a **Deferred Work Index** block pointing at UNFORGET.md (see `## How to use unforget alongside CLAUDE.md / AGENTS.md` in SKILL.md, and `reference/init.md` for the block itself). Without it, a populated ledger sits invisible and the skill looks broken when it is working as designed.

When `--version` runs inside a project directory, it scans `CLAUDE.md`, `.claude/CLAUDE.md`, and `AGENTS.md` for the block and reports `✓ installed in <file>` or `✗ missing` with the fix (`run /unforget init`). When run from a non-project directory (no `--project-root`), this line is omitted rather than reported as a failure.

### Behavior

- Read-only. Touches no files.
- Always succeeds as a *command* even when it reports a broken install: the integrity/recall lines are diagnostic content, not a command error. The only true non-response is the skill failing to load at all (in which case nothing prints, which is itself the signal the install did not take).
- Version, format-version, and integrity checks work from any directory. The recall-trigger line requires a project context; it is silently skipped otherwise.

After install, the user has no way to verify the skill loaded short of trying to use it. `/unforget --version` provides a no-side-effect health check. If the command does not respond, the install did not take. If it responds with the wrong version, the user knows to update before running `init` against a real project. If it responds with an integrity ✗, the user knows the companion files did not travel with the install before a single row is written.
