# /unforget add

Part of the unforget command reference; the index is [../commands.md](../commands.md).

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
   - Status: `` `@status:open` `` (format v2+; a v1 ledger keeps the word `Open`). Steps 4b and the status-token rule both build on this token, so never write a tokenless row into a v2 ledger.
4. **Ask the user to override any defaults** (single AskUserQuestion with all relevant fields, or accept the defaults to skip ahead).
4b. **Park it if the session, not the user, decided to log it** (`reference/pickup.md` § Parked rows). An out-of-scope finding noticed during other work, or a follow-up the session thought of, gets `@parked` right after its status token and two detail-block lines: `Parked: logged by a session on <MM/DD/YYYY> during <task>; not triaged by the user.` and `Revisit: <a concrete event>`. A row the user asked to log is not parked. Never use the Target to get around parking: a parked 🔴 THIS row still blocks release, but no session may start it until the user unparks it.
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
