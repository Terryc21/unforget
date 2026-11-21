# /unforget list --fresh: the display-preference interview

Part of the unforget command reference; the index is [../commands.md](../commands.md).
The interview that sets what a plain `/unforget list` shows. The list command itself is
[list.md](list.md).

---

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

---

### 🛑 The governing rule for EVERY question in this interview

**Ask about the OUTCOME in the user's words. Never about the mechanism in the skill's words.**

📍 **This is the skill-wide rule, stated canonically in `SKILL.md § Asking the user anything`** —
it governs `init`'s onboarding questions and every `branch`/`edit` prompt too, not just this
interview. What follows is the long form with worked examples; if the two ever disagree,
SKILL.md wins.

This governs every question below — Q0, the Standard four, the Thorough three, and any question
added later. The question lists in this section are written for the **implementer**, so they
name config keys (`display_view`, `display_verbosity`, `archive_nudge_threshold`) and flag
values (`all`/`open`/`done`/`split`/`next`). **Those names are specification, not prompt copy.**
Translate every one before it reaches a user.

Three sub-rules, each learned from a real failure:

1. **Name what the user GETS, not what gets configured.** "Only unfinished work, everything, or
   one 'do this next' pick" — never "a view preset." A user should never have to model this
   skill's internals to answer this skill's own question. If an option can only be understood by
   someone who has read this file, it is not written yet.
2. **Ask about the result, not the effort.** The gate question is *"What do you want the Unforget
   table to display?"* — NOT *"How much do you want to set?"* An effort-framed question makes the
   user budget time before they know what they'd get, and forces every option to re-explain the
   subject from scratch.
3. **No interview bookkeeping in the prompt.** No question counts in labels or descriptions. A
   count answers "how long is this," which competes with "what am I choosing" at the moment of
   decision. Relative scope is already conveyed by each tier's description.

**Origin (2026-08-13, one live `--fresh` session).** The interview was first rendered straight
from this section's key names; the user's report: it gave "not much context as to how to
answer." The repair took three passes — key names → outcomes, then effort-framing → outcome-
framing, then removing the question counts that the first pass had *added*. Each pass fixed only
what was pointed at, because there was no stated principle to apply. **This rule exists so the
next question is written right the first time, rather than corrected after a user hits it.**

⚠️ The sub-rules are the durable part; the specific wording below is one correct rendering of
them, not the only one. Re-render freely for context (naming the project's actual sibling
ledgers, say) — but never re-render back toward mechanism, effort, or counts.

**Step 0 — the depth gate, every `--fresh` call, no exceptions:**

> "What do you want the Unforget table to display? **Quick** — pick what a plain `/unforget
> list` shows: only unfinished work, everything, or a single 'do this next' pick ·
> **Standard** — the above, plus how rows are sorted, which categories appear, and whether the
> table renders full-width or condensed · **Thorough** — the above, plus how long an item sits
> before it's flagged as going stale, when to be reminded to clear out finished items, and
> whether to include this project's other ledgers."

🛑 **Lead every option with what the user GETS. No question count anywhere in the prompt.**
The tier names are this skill's vocabulary, not the user's: "just a view preset," "grouping,"
"verbosity," "multi-ledger union default" all name internal config keys, so an option list built
from them tells a first-time user only how many questions they're in for — never what they'd be
choosing. That makes the depth gate unanswerable for exactly the person it most needs to serve.
Translate to outcomes every time; never pass the key names through verbatim. (Origin
2026-08-13: a live `--fresh` run rendered this line's own key-name shorthand into the prompt and
the user reported it gave "not much context as to how to answer.")

⚠️ **Q0 asks the user to commit to a depth before seeing any of its questions** — a structural
property of the gate, not a wording bug. Because of that, **Quick is the right steer for anyone
unfamiliar**: say so plainly when the situation warrants, and note that `--fresh` can be re-run
any time to go deeper. Never imply the choice is irreversible.

The chosen depth governs ONLY this run of the interview — it is not itself saved. Answer with
`AskUserQuestion` (or the CLI equivalent); this is the one question `--fresh` cannot skip.

**Quick (1 question):** a single view-preset pick, mapped straight to `display_view` (+ a sane
paired `display_group_by`, not asked separately):
- "What's left" → `display_view=open`, `display_group_by=target`
- "Everything" → `display_view=split`, `display_group_by=target`
- "What's next" → `display_view=next`, `display_group_by=target`

**Standard (adds, each independently skippable — see below).** Each bullet gives the key and its
values (spec), then **Ask as:** — the outcome-framed wording that actually reaches the user, per
the governing rule above. Never prompt with the key name or the raw flag values.

- View mode (`all`/`open`/`done`/`split`/`next`) — same five choices as `--view=`.
  **Ask as:** *"Which rows should a plain list show?"* → "Only what's unfinished" (`open`) ·
  "Everything, done and not-done together" (`all`) · "Everything, split into two tables"
  (`split`) · "Only what's finished" (`done`) · "Skip the table — just tell me what to work on
  next" (`next`).
- Grouping (`target`/`section`/`none`) — same three choices as `--group-by=`.
  **Ask as:** *"What order should rows appear in?"* → "Most urgent to ship first" (`target`) ·
  "Grouped by where they came from — paused plans, session notes, audits, things you reported"
  (`section`) · "One flat list, no headings" (`none`).
- Default section scope (`display_sections`) — **`all` (every section) or ONE named section**
  (`paused` / `spillover` / `audit` / `observed`), matching what `--section=` actually accepts.
  **Ask as:** *"Which kinds of work should show up?"* → "All of them" (`all`) · "Only paused
  plans" (`paused`) · "Only things set aside mid-session" (`spillover`) · "Only audit findings"
  (`audit`) · "Only things you reported yourself" (`observed`).
  ⚠️ Do NOT offer an arbitrary multi-section subset: every documented `--section=` usage is
  singular (`--section=audit`, "only Section 3"), so a saved subset would imply a filter
  capability the underlying flag does not have. If `--section=` is ever widened to accept a
  comma-separated list, widen this question at the same time — not before.
- Verbosity (`display_verbosity`) — **`auto` (default) / `full` / `compact`.** `auto` preserves
  the existing terminal-width auto-detection (`list.md` § Terminal-aware rendering: ≥120 cols → full
  10-column, <120 → compact 6-column projection); `full`/`compact` pin the width regardless of
  terminal size, the saved-default equivalent of the per-call `--wide`/`--compact` overrides.
  **Ask as:** *"How wide should the table be?"* → "Fit it to my window automatically" (`auto`)
  · "Always show every column, even if it wraps" (`full`) · "Always show the short version"
  (`compact`).
  ⚠️ **`auto` must be the default and the skip-value.** Saving a pinned `full` permanently
  defeats the auto-fallback that exists *because* the 10-column table is unreadable under 120
  columns — a user who answers "full" on a wide monitor would otherwise get a wrapped mess on a
  laptop forever, with no signal why. Pinning is a deliberate power-user choice, never a
  side effect of answering a setup question.

**Thorough (adds, also independently skippable).** Same convention — key and values first
(spec), then **Ask as:** for the wording that reaches the user.

- Staleness thresholds — the four Target-tier day counts from `scan.md` (`/unforget scan`), saved as
  `stale_days_this` / `stale_days_next` / `stale_days_later` / `stale_days_someday`
  (defaults 30 / 90 / 180 / 365). Offer them as one grouped question, not four separate ones;
  skipping keeps every current value.
  **Ask as:** *"How long should something sit before it gets flagged as going stale?"* — offer
  the four tiers as one grouped choice in plain terms ("ship-blockers after 30 days, next-release
  work after 90, later work after 180, someday-maybe after a year"), with "keep these" first.
  Never prompt with the key names or the phrase "staleness threshold."
- Archive-nudge threshold (`archive_nudge_threshold`, default 5; `0` silences the nudge) — see
  `/unforget archive` § The archive nudge.
  **Ask as:** *"How many finished items should pile up before I remind you to clear them out?"*
  — and when the ledger already exceeds the current value, say so, since the reminder will fire
  immediately ("you have 21 finished items now, so this fires on your next list").
- Multi-ledger union default — whether a plain `list` (no `--ledgers=`/`--all-ledgers` flag)
  should behave as if `--all-ledgers` were always passed. Default stays no (`list.md` § Multi-ledger
  scope's opt-in-only design is not overridden by this — the interview can only change what a
  BARE `list` defaults to, never make cross-ledger reads silently automatic without the user
  having chosen that here).
  **Ask as:** *"Should a plain list also include this project's other ledgers?"* — and **name
  them, with what each holds** ("Terry-only actions, and the multi-inventory sprint"), read from
  the registry. "Multi-ledger union default" is meaningless to anyone who has not read
  `reference/branching.md`; the ledgers' actual names and purposes are not.

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

**Step 2 — Q0, the depth gate (one `AskUserQuestion`, cannot be skipped).** Ask it as
**"What do you want the Unforget table to display?"** — the question names the OUTCOME the user
is choosing, not the size of the interview. ("How much do you want to set?" asks the user to
budget effort before they know what they'd get; every option then has to re-explain the subject
from scratch.) Offer exactly the three depths, Quick first (it is the common case, and the
header/label limits mean the depth labels must stay short):

| Option label | Description shown |
|---|---|
| `Quick` | Pick what a plain `/unforget list` shows: only unfinished work, everything, or one "do this next" pick. |
| `Standard` | The above, plus how rows are sorted, which categories appear, and full-width vs condensed table. |
| `Thorough` | The above, plus how long before an item is flagged as going stale, when to be reminded to clear out finished items, and whether to include this project's other ledgers. |

🛑 **Labels are the bare tier name — `Quick`, `Standard`, `Thorough`. No question count in the
label.** A count is interview bookkeeping, not a description of the outcome, and putting it in
the label makes "how long is this" compete with "what am I choosing" at the exact moment the
user is deciding. The descriptions already convey relative size by getting longer, and each
tier's own question set names its scope. (Origin 2026-08-13, same live `--fresh` session as the
outcome-first rule below: the counts were added in that fix and removed one turn later as noise
once the descriptions were doing the work.)

🛑 **These descriptions are outcome-first on purpose — do not "simplify" them back to key names.**
`view preset` / `grouping` / `verbosity` / `multi-ledger default` are internal config keys; an
option list written in those terms reads as jargon to anyone who has not read this file, leaving
the question count as the only usable signal. State what the user gets; the
descriptions show relative size by getting longer, so no count is needed anywhere in the option. Substitute the ledger's real numbers where they help (e.g. name how many sibling
ledgers "this project's other ledgers" actually means).

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


### Persisting multi-ledger interview answers

Save the full-interview all-ledgers answer as `display_all_ledgers` through
`display_prefs.py build-patch --all-ledgers` (true) or `--current-ledger` (false), followed
by registry `write --merge`. Omit both flags for a skipped answer, preserving its prior
value including false. Resolve with explicit `--ledgers <names>` or `--current-ledger`
when requested; those override saved scope. Supply `--current-ledger-name` when the current
ledger is a sibling. Name every selected ledger in the user-facing scope. New installations
default to one current ledger. This preference governs terminal list/scan; HTML keeps its
separately documented explicit-scope defaults.
