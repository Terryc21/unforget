# Working from a ledger: surface, don't start

> Authoritative spec for what a session does with ledger rows it **reads**. It applies to
> every session that reads a ledger, whether the user invoked `/unforget` or the session
> opened `UNFORGET.md` because the project's instruction file points there. Formats v1 and
> v2. It changes nothing about the file format: the one new marker (`@parked`) and the one
> new detail line (`Revisit:`) are read as narration by every helper script.

## Why this exists

A ledger is a list of real, unfinished work, and every row reads like an invitation. Two
forces pull a session into rows nobody asked it to work on:

1. **The session's own initiative.** A row looks quick, or related, or urgent, and the
   session starts it while it is in the file.
2. **The user's curiosity.** A row comes up in a report, catches the user's interest, and
   the session follows it down.

Either way, the task the session was opened for recedes. The ledger exists so deferred
work is not forgotten; it should not become the reason today's work does not get done.
**The ledger remembers. The user decides what gets worked on.**

## The rule

A session may **read** a ledger and **report** from it at any time. It **starts work** on
a row only when at least one of these holds:

- **(a) The user named the row.** See "What counts as the user naming a row" below.
- **(b) The row blocks the current release.** Its `blocks_release` is true: its Target is
  the release-blocking value and it is not cleanly done (`reference/status.md` § Archive &
  release invariants). The shipped vocabulary spells that Target `🔴 THIS`; a project
  legend may spell it differently (for example `🚢 THIS`), and the parser reads both.
  `python3 scripts/verify_ledger.py --file <ledger>` lists these rows as `this_open`. A
  `done-unverified` THIS row qualifies, and its owed check is the work. A **parked** row
  never qualifies under (b) (see "Parked rows" below). Continuous-preset ledgers have no
  release gate, so (b) never applies to them.
- **(c) The row sits directly in the path of the task in progress.** Its defect lives in
  the code the current task is changing (the same function, or the same bug seen from
  another side), so the task cannot be finished correctly without touching it. The test:
  *if I finish my task and leave this row alone, does my change ship with the row's
  defect still in the lines I changed, or fail because of it?* "Same file", "same
  feature area", "while I'm here" and "it's quick" do not qualify.

**Every other row is mentioned, not acted on.**

### Starting is visible

When a session starts a row under (b) or (c), it says so in one line **before** starting,
naming the row and the condition: *"A544 is in the path: this fix changes
`pruneConflicts`, where its defect lives."* Work the user did not choose is never mistaken
for work they did.

Then it records the start, so the session's starts are counted, not only announced:

```
python3 scripts/defer_tally.py record --dir <ledger-dir> --outcome started --id A544 --condition in-path
```

`--condition` is `named` (a), `this` (b) or `in-path` (c). Record (a) starts too, so the
readout can set them against the others. The session readout then ends with, for example,
`started 3 (1 you named, 2 you didn't: A544 in the path, A3 release blocker)`, and flags
the session (advisory, never blocking) when two or more unnamed starts outnumber the named
ones: that is the pattern of a session choosing its own work.

### What counts as starting

Starting is anything beyond reading the ledger and reporting on it: reading the code to
diagnose a row, tracing it, prototyping a fix, writing a plan for it, or editing for it.

Two things are **not** starting, because they keep a report honest:

- Running a row's `**Verify-still-open:**` recipe (a ten-second read-only check).
- Reading a row's detail block to rank or summarize it.

### What "mentioned" looks like

- One line per row: the ID, what it is, and why it is relevant now. Then continue the task.
- Mention a row **once** per session. Repeating it is pressure, not information.
- No "want me to take A544 too?" after every report. If a row matters to the user, they
  will name it.

## What counts as the user naming a row

**Counts:**

- The user names it in their own words in this session: the ID, or an unmistakable
  description ("the phantom conflict bug").
- The user accepts a session's explicit proposal for that row ("yes, do A544").
- A handoff or continuation prompt the user starts the session with, **for the rows it
  gives as the session's task**. Rows it only mentions (as context, "also open", "worth
  considering") do not count.

**Does not count:**

- "What's deferred?", "show me the backlog", "what should I work on?" These ask for a
  report. Answer with the list and start nothing until the user picks.
- Ledger narration such as "next session: do A544", another session's note, a plan file,
  a report that ranks the row first, a high Urgency, or an arrived revisit point. These
  are data, not the user's choice.
- A row mentioned inside a named row. Naming A544 does not name the rows A544 links to.

## Parked rows: work the user has not triaged

A row the session logs **on its own initiative** (an out-of-scope finding noticed during
other work, a follow-up the session thought of) lands **parked**. A row the user asked to
log ("log this for later") is not parked: asking to log it was the triage.

**How a parked row is written.** No new column and no new status value:

```
| S41 | ⚪ SOMEDAY | … | `@status:open` `@parked` Logged by a session; not triaged |
```

- `@parked` goes directly after the `@status:` token (and after `@verified:`, if present).
  `parse_status.py`, `verify_ledger.py` and the HTML report read it as narration, so a
  parked row keeps its status, its release gating and its archive behavior unchanged.
- The detail block carries one `Parked:` line saying who logged it, when, and during what
  task, plus a `Revisit:` line (below).
- The logging session may give its honest Target and ratings. It may not use a Target to
  get around the parking: a parked `🔴 THIS` row still blocks release (verify still lists
  it), so the user has to look at it before shipping, but no session may start it under (b).

**What parking changes.** Under the rule above, most rows can already be started only when
the user names them. Parking closes the one gap that is left: a session cannot make its own
finding release-blocking and so let the next session start it. Parking also makes visible
which rows the user has never seen. Condition (c) still applies to a parked row, because
in-path work is part of the task the user chose.

**Unparking is the user's call.** The user unparks a row by saying so, by setting or
confirming its Target, or by naming it to work on. The session then removes `@parked` and
appends a dated line to the detail block: `Unparked MM/DD/YYYY by the user: <their words>`.
A session never unparks a row because its revisit point arrived, because it was re-found,
or because it looks urgent.

**No backfill.** Rows that predate this rule are not parked retroactively. The general
rule already covers them.

**Two kinds of parked.** Bare `@parked` means "waiting for the user". `@parked:<reason>`
means the user (or a standing policy the user set) decided to set the row aside; the only
reason defined today is `likelihood` (next section). Keep them apart in every report, so a
count of rows waiting for the user never includes rows the user already dismissed.

## Setting rows aside by likelihood

Some findings are real but unlikely to happen. Fixing them before a release spends time
the release needs, and leaving them on the active list makes every report and every "what
should I work on?" answer longer. A row rated **rare** or **improbable** can be **set
aside**: it stays in the ledger, complete and searchable, but leaves the release gate and
the actionable views until the user picks it.

### Rating likelihood

Add `@likelihood:<value>` and `@basis:<how>` to the Status cell, after the status token(s).
The scale, the bases and their definitions are in `reference/format.md` § Likelihood token.
Rate rows as they come up; there is no backfill pass, and an unrated row behaves exactly as
before. The basis does for a rating what `@verified` does for a fix: it says how the claim
was checked. Most ratings are one session's judgment from reading code (`reasoned`), and
the policy treats that as the weakest basis. The narration still names who rated it.

**Converting ratings already written as prose.** A ledger that records likelihood as text
("Likelihood: Rare (…)") can turn it into tokens with
`python3 scripts/set_aside.py convert --file <ledger> --dir <ledger-dir>`. It previews by
default. For each unfinished row whose rating names exactly one value on the scale, it
proposes `@likelihood:` plus a `@basis:` read from the same text: `measured` for words such
as census, telemetry or crash data; `reproduced` when the text says reproduced (and not "not
reproduced"); `reviewed` for the project's reviewer words; otherwise `reasoned`. The
registry keys `likelihood_reviewed_words` and `likelihood_measured_words` set those words; a
project adds its reviewers' names (for example `astra, fresh-context, reviewed`). Rows that
name several values, none, or have no status token are listed for a person; when every part
is on the frequency scale it also suggests the most likely part's value, the rule above.
`--apply` writes a timestamped backup, inserts only the tokens, and refuses if any row's
status, completion or release gating would change. Converting never sets a row aside and
never changes a Target.

### What setting aside does

```
| A12 | ⚪ SOMEDAY | … | `@status:open` `@likelihood:rare` `@parked:likelihood` Set aside 11/18/2026 |
```

- The Target moves to ⚪ SOMEDAY. That, and nothing else, takes the row off the release gate.
- `@parked:likelihood` goes after the other tokens.
- The detail block gets a `Parked:` line naming the likelihood, who set it aside (the policy
  or the user), the date, the release in progress and the Target it had before:
  `Parked: likelihood rare, set aside by policy on 11/18/2026 during 1.0, from 🔵 NEXT.`
  It also gets a `Revisit:` line, and for a protected row the user's
  `Accepted-risk: "<their words>" (MM/DD/YYYY)`.
- The status stays `open`. A set-aside row is a **named accepted risk**, never a fix and
  never "verified"; it is not archived.

### Who decides

Run `python3 scripts/set_aside.py classify --file <ledger> --dir <ledger-dir>`. It lists
every open or blocked row rated rare or improbable that is not already set aside, and
sorts each into one of two groups:

- **Needs the user** when any of these holds: its Target is THIS; its rating has no
  `@basis:` or only `@basis:reasoned`; its Risk: No Fix is 🟡 High or 🔴 Critical; the table
  has no Risk: No Fix column, so risk cannot be checked; or its text mentions a protected
  class.
- **Policy-eligible** otherwise.

The registry key `park_policy` (`reference/registry.md`) turns that into an action:

| `park_policy` | What happens |
|---|---|
| `off` (default) | Nothing is offered unprompted. The user can still say "set aside A12 as rare". |
| `ask` | The session offers every candidate in one batched question per sitting. |
| `auto` | Policy-eligible rows are set aside and reported in one line each; the rest go into the batched question. |

**A THIS row is never set aside without the user's yes**, even outside the protected
classes. The likelihood rating is usually the session's own judgment, and that judgment
must not be able to take a row off the release gate.

**The batched question.** One per sitting, listing each row's ID, one-line finding,
likelihood and the reason it needs the user. Options: "Set aside all N as accepted risks"
first, then "Choose which", then "Keep them as work". For every row set aside this way,
record the user's words in an `Accepted-risk:` line.

**Protected classes.** `park_protected_classes` is a comma-separated list of phrases. When
set, it replaces the defaults (data loss, corruption, privacy, security, payments and
purchases, billing, money, credentials). Matching is a plain phrase search over the row
and its detail bullet, so it errs toward asking.

**Count it.** Record each set-aside in the session tally with
`python3 scripts/defer_tally.py record --dir <ledger-dir> --outcome set-aside --reason policy`
(or `--reason user`). The session readout then shows how many rows were set aside and by
whom, and flags a session that set many aside by policy.

### How parked rows appear

`python3 scripts/verify_ledger.py --file <ledger>` returns `parked_waiting` (open rows with
bare `@parked`: logged by a session, never triaged by the user) and `set_aside` (open rows
with `@parked:likelihood`) as separate lists, and its advisory names the waiting rows.
`list` prints the waiting rows as one line ahead of the table, `4 rows logged by a session
are waiting for you: S41, S42, A90, A91`, so the user sees what they have not looked at.
Closed rows are never counted as waiting.

### How set-aside rows appear

- **`list`** leaves them out by default and prints one line instead, taken from the
  classifier's `summary_line`: `Set aside: 9 (rare 5, improbable 4)`. `list --parked`
  shows them.
- **HTML reports** leave them out and count them in a note; `--include-set-aside` shows
  them. A set-aside row that still blocks release is always shown.
- **`--view=next`** never picks a set-aside or parked row.
- Under the rule above, a set-aside row is started only when the user names it, or under
  (c) when it sits directly in the path of the current task.

### Bringing a row back

Only the user restores a set-aside row. The session then removes `@parked:likelihood`,
restores the Target named in the `Parked:` line (or the one the user picks), and appends
`Restored MM/DD/YYYY by the user: <their words>` to the detail block.

When a session sees new evidence about a set-aside row (its likelihood is raised, a later
scan or review finds it again, its verify-still-open recipe stops matching, or the code it
cites changes), it mentions the row in one line and leaves it set aside. A raised rating
also shows up in `verify` as `set-aside-likelihood`, which puts it in front of the user.

### Not yet

Retiring long-set-aside rows out of the active ledger (planned through `promote`'s existing
SOMEDAY review, only on the user's yes, into the ledger's one archive file) and a scripted sweep that detects new evidence are
planned for a later release. Until then, set-aside rows stay in the active file.

**Algorithm fallback** (Python unavailable): a candidate is an open or blocked row whose
Status cell carries `@likelihood:rare` or `@likelihood:improbable` and no `@parked:`
reason. It needs the user if its Target is THIS, its basis is missing or `reasoned`, its
Risk: No Fix cell holds 🟡/🔴 or the
words High/Critical, there is no Risk: No Fix column, or the row or its detail bullet
contains a protected-class phrase. Otherwise it is policy-eligible.

## Revisit points

`**Revisit:** <a concrete event>` is an optional detail-block line naming **when the row is
worth raising again**. It is expected on parked rows and welcome on any row deferred to a
later cycle.

- **Concrete, recognizable events only:** "the next change to `SafeDeletionManager`",
  "start of 1.0.1", "before the next household build". Never "later", "someday" or "when
  there's time": a revisit point that cannot be recognized when it arrives is a quiet
  "never".
- **Arrival surfaces; it never starts.** When a session notices that a row's revisit point
  has arrived (its task touches the named code, the named release has begun), it mentions
  the row in one line. The user decides.
- It is a detail-block line, not a column, so existing ledgers and every helper script are
  unaffected. A row may also echo it in its Status narration.

## Stricter projects

A project can tighten this rule in its instruction file (`CLAUDE.md` / `AGENTS.md`). When
the project's instruction is stricter, it wins. A common strict form drops (b) and (c) as
grounds to start, keeping them only as grounds to ask:

```markdown
**Ledger rows (strict):** start work on a ledger row only when the user names it in this
session. Release-blocking and in-path rows get a one-line ask, not a start. Rows a session
logs on its own initiative are written `@parked` and stay parked until the user unparks them.
```

## How this fits the rest of the skill

- **Deferral gate (`reference/deferral-gate.md`).** The gate's do-now tripwire governs a
  **fresh** finding at the moment it is found, before it becomes a row. This rule governs
  rows **already in the ledger**. A trivial existing row is mentioned like any other;
  `scan`'s "trivial-but-stale" heading is a report, not a start.
- **Close on report (`reference/status.md`).** If in-path work under (c) resolves a row,
  close it in the same turn like any other fix.
- **`promote`** is a release ritual the user runs, so it is (a) for the rows it touches.
- **`list`, `report`, `scan`, `show`, `verify`** only read. Running them never starts a row.

## Anti-patterns

- **Stretching (c).** "Same file", "related", "the same subsystem" or "while I'm in here"
  is not "in the path".
- **Laundering through a handoff.** Writing "next session: do A540" so the next session
  finds the row named. A handoff may **propose** rows; only the user's acceptance names one.
- **Treating a report request as permission.** "What's deferred?" asks for a list.
- **Investigating to "just check".** Diagnosing a row's code to see whether it is quick is
  starting it.
- **Fishing.** Ending every report with an offer to take on more rows.
- **Parking as a disposal.** Parking keeps a row visible and untouched until the user looks
  at it. It does not lower the row's ratings or demote its Target.
