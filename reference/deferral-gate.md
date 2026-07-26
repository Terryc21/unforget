# The deferral gate: tripwire, why-not-now, and session accounting

> Authoritative spec for the gate that fires at `add` — the moment work is about
> to become a deferred row (format v2+, from the Deferral Gate design). It makes
> deferral **cost something** and **leave an auditable record**, instead of being
> free. The failure it targets is *deferral-laundering*: a row looks identical
> whether it was deferred for a good reason or because deferring was frictionless
> and self-flattering.

## The honesty this spec keeps (read first)

This gate is proposed by the same kind of system it constrains, so two truths are
stated up front — the spec is dishonest without them:

1. **The linguistic gate can be gamed.** If deferring requires typing a
   justification, the AI can write a plausible-sounding justification for a bad
   deferral — the same fluency that produces confident-wrong conclusions produces
   confident-wrong justifications. A required reason raises the cost of a bad
   deferral and creates a record; it does not *prevent* one.
2. **Therefore the real backstop is quantitative, not linguistic.** A single
   well-worded row hides a bad deferral; a **session defer/fix ratio of 7:2 does
   not.** The "why not now?" prompt is the speed bump; the accounting (§4) is the
   thing that actually catches a *pattern* of avoidance, because a ratio can't be
   rationalized the way a sentence can.

An implementation that ships only the "why not now?" prompt and drops the
accounting has shipped the evadable half and called it a gate.

## Where the gate sits

The gate fires at exactly one place: **`add` — the first thing it does**, before
any Target/section/ledger routing (it sits *above* the branching cascade's first
step; the cascade's "trivial?" exit IS this gate).

```
something is about to be deferred
        │
   ┌────▼─────────────────────────────┐
   │  DEFERRAL GATE                    │
   │  1. trivial tripwire   (§2)       │
   │  2. "why not now?"     (§3)       │
   │  3. record + account   (§4)       │
   └────┬─────────────────────────────┘
        │ (survives the gate = legitimately deferred)
        ▼
   → row / section / ledger
```

Its *strictness* is **Policy 1** (§5), read from the registry global block
(`policy_deferral`); its *mechanism* is this spec. `add`, `list`, and `edit` are
where it surfaces; the write path never hard-blocks (the gate redirects and
counts — it never *refuses* a deferral; see Anti-patterns).

## §2 — The trivial tripwire (cheapest, highest-value)

**Rule:** a would-be row that is **Fix Effort = Trivial** AND **Blast Radius =
⚪ 1 file** does not get deferred — the gate redirects to **DO IT NOW.** No
justification prompt; triviality is self-evidently do-now.

- **Columns, not judgment.** The ledger already carries `Fix Effort` and
  `Blast Radius`. The tripwire reads the signal the row would carry anyway — no
  new data, no AI judgment to launder. (Deciding *whether* a change is Trivial is
  the LLM's call; once the two columns are set, the routing is mechanical — that
  split is why the script takes the columns as input.)
- **Scope does NOT gate the tripwire.** Trivial → do-now *regardless* of
  in/out-of-scope. Scope only decides **reporting** (mirrors Terry-style
  opportunistic-findings rules, and any adopter's equivalent):
  - **in-scope trivial** → just do it, no mention needed;
  - **out-of-scope trivial** → do it, and log a **one-line report line** in the
    run summary — never silently defer, never silently fix.
- **Destructive exception (trivial ≠ safe).** If the trivial fix is on the
  always-stop list (data loss, file deletion, force-push / history rewrite, prod
  deploy), it does **not** auto-do. It routes to **needs-approval**, logs with
  `Status: needs approval`, and is raised at the end. The always-stop rule wins
  over the do-now tripwire, every time.
- **Policy 1 override (§5).** `conservative` lets trivial-out-of-scope defer
  anyway (offered, not recommended — it re-opens the leak). `same-file-only`
  does-now only when the file is already open in the task.

**What the tripwire kills:** the single most common laundering case — "I'll just
log this one-liner" for something that takes less time to fix than to write up.

## §3 — The "why not now?" gate (everything not trivial)

A would-be row that clears the tripwire must pass a **justification check**:
deferral is only legitimate for a reason on a **fixed allow-list.** If none
apply, the honest answer is do-now.

### §3a — The allow-list (the ONLY valid reasons to defer)

| Reason tag | Means |
|---|---|
| `user-decision` | Needs a decision only the user can make (a one-way door, a product call, a naming choice). |
| `scaffolding` | Needs tools / a device / a second account / a working dir / a build this session can't produce. |
| `scope` | Genuinely out of scope AND non-trivial — doing it now would balloon the task past its purpose. |
| `external-block` | Blocked on something external (a CI run, a third party, a deploy, another person). |

The chosen tag is **stored in the row** — a `Deferred because: <tag>` line in the
detail block (or a short inline tag). That makes the justification **auditable**:
a later reader (or `scan`/`verify`) can check whether the stated reason held up.
An `external-block` that's sat for five sessions with no CI in sight is a visible
lie the record now carries.

### §3b — What is NOT on the list (→ means "do it now")

- *"It's easy to just log it."* ← the core deferral-laundering tell.
- *"I'll be thorough and capture it for later."* ← thoroughness theater.
- *"It's not strictly part of what I was asked."* ← scope **alone** doesn't
  justify deferral if the fix is small; that's §2's job. For non-trivial
  out-of-scope, `scope` must *actually* hold (it would balloon the task), not
  just "it's adjacent."
- *"I'm not sure how to do it right now."* ← a reason to investigate now or ask,
  not to defer silently.

### §3c — The mechanic

`add` requires the deferring party (usually the AI) to **name which allow-list
reason applies.** If it cannot map the deferral to a reason, the gate's response
is: **"No valid deferral reason — do it now, or tell me which reason applies."**
Do-now is the default, not the row. (Exit 1 from `defer_tally.py gate` with
`reason_required:true` is exactly this state — the caller must resolve it, either
by doing the work now or by naming a real reason.)

### §3d — Honest limit (from the top)

This is the gameable half. The AI *can* pick `scope` for something that wouldn't
balloon the task. The mitigations are: (a) the reason is *recorded*, so it can be
checked later, and (b) the accounting in §4 catches the *pattern* even when
individual justifications pass. The gate does not claim to stop a determined bad
deferral — it raises its cost and logs its excuse.

## §4 — Session accounting (the load-bearing backstop)

The linguistic half is evadable per row; the pattern is not. The skill keeps a
**per-session defer/fix tally** and surfaces it, because the ratio is the signal
no single well-worded justification can hide.

### §4a — What's counted

- **fixed-now:** items the tripwire (§2) or a do-now decision (§3) resolved in the
  moment.
- **deferred:** items that became rows, tallied by their allow-list reason.

The tally lives in a small **`.unforget-session.json`** state file in the ledger
directory — ephemeral, per-session, **git-ignored** (it is churn, not a record).
The registry (README-canonical) holds the *thresholds*; the state file holds the
*counts*. Call `defer_tally.py record` after each gate resolution;
`defer_tally.py reset` starts a fresh session.

### §4b — Where it surfaces

- On **`list`** and at **session end / summary**: a one-line readout —
  `This session: 2 fixed inline · 7 deferred (reasons: 3 user-decision, 2 external-block, 2 scope).`
- The **reason breakdown matters.** 7 deferrals all `user-decision` is legitimate
  (genuinely can't act); 7 all `scope` is a tell.

### §4c — The threshold that flags

- A defer-heavy ratio (default flag: **deferred ≥ 3× fixed-now**, or ≥ 3 with zero
  fixes) surfaces a gentle prompt: *"7 deferred vs 2 fixed this session — worth a
  pass to see if any are actually do-now?"*
- The prompt is **advisory, never blocking.** Some sessions *are* legitimately
  defer-heavy — a planning session, or a blocked-on-devices session (the
  FS-cluster case). The flag invites a look; it does not judge, and it never
  refuses a deferral. The `3` is registry-configurable via `ratio_flag_threshold`.

### §4d — The aging cross-check (ties to `scan`)

`scan` sharpens a flag: a row that is **Trivial-effort AND has survived ≥N
sessions un-done** is a near-certain "should've just done it." Triviality +
staleness together is the hindsight signal that a past deferral was laundering —
which is how the user *learns the pattern* over time, not just catches it in the
moment. `N` is registry-configurable via `stale_trivial_sessions`.

## §5 — Policy 1 (set at init / start-of-run)

The gate's strictness is one user-set policy, recorded in the registry
(`policy_deferral`) so it persists and isn't re-litigated each run:

| `policy_deferral` | Trivial tripwire (§2) | "Why not now?" (§3) |
|---|---|---|
| **aggressive** (recommended default) | trivial → do-now regardless of scope | strict allow-list; do-now is default |
| **conservative** | trivial-out-of-scope may defer | allow-list still applies but scope alone can pass |
| **same-file-only** | do-now if file already open, else defer | allow-list applies |

Start-of-run *may* re-confirm ("still aggressive this session?") but does not force
a re-answer.

## Companion handoff: no pattern to infer → `forward-bug-hunt` (format v2+)

When the gate can't infer a pattern from a recent fix (no closure to generalize from,
just a fresh deferral), unforget MAY offer the **`forward-bug-hunt`** companion
function (default: bug-prospector) — a forward hunt for bugs rather than a
fix-generalizing echo. Full mechanic: `reference/skill-handoffs.md`. Resolve via
`python3 scripts/companions.py resolve --function forward-bug-hunt --invocable "<names>"`
and say the resolver's expression. Governance is the gate's own ethos: **advisory,
once/session, and NEVER a way to defer the hunt** — "I'll run bug-prospector later"
logged as a row is deferral-laundering; the handoff means run it now while context is
hot.

## §6 — Worked examples (run through the gate)

| Situation | Tripwire (§2) | Gate (§3) | Result |
|---|---|---|---|
| 1-line typo in an unrelated file (mid-debug) | Trivial + 1 file → **do-now** | — | Fixed now; logged as an out-of-scope report line. NOT a row. |
| A device-verify (needs a TF build + device) | not trivial | `scaffolding` | Legitimately deferred; row carries `Deferred because: scaffolding`. |
| "Rename app in App Store Connect" | not trivial | `user-decision` | Deferred; reason recorded. |
| A medium refactor, adjacent but not asked | not trivial | `scope` ONLY if it would balloon the task; else do-now | Genuinely task-ballooning → defer w/ reason. "adjacent, ~30 min" → do-now. Gate forces the honest call. |
| "I'll capture this cleanup for later" (no reason) | maybe trivial | no valid reason | Gate: **do it now, or name the reason.** The laundering case, caught. |
| Deleting a stale file (trivial but destructive) | trivial BUT destructive | — | Does NOT auto-do; logs `needs approval`, raised at end. |

## §7 — Anti-patterns (what the gate must NOT become)

- **A blocker.** The gate never *refuses* a deferral. It redirects trivial work,
  demands a reason for the rest, and counts — the human can always override. A
  gate that blocks becomes friction the user routes around by not running the
  skill.
- **Shame-driven.** The accounting flag is a neutral *"worth a look?"*, not
  *"you deferred too much."* Over-correcting into "never defer" is its own failure
  (scope-creep every task).
- **Trusting the justification as proof.** A recorded reason is auditable
  evidence, not a guarantee (§3d). The presence of a justification must not
  *close* the question; the accounting (§4) and aging cross-check (§4d) are what
  keep it honest.
- **Silent trivial-fixing of destructive things.** Trivial ≠ safe; the
  always-stop list wins over the do-now tripwire.

## Preferred implementation

Delegate the deterministic routing and counting to the helper:

```
# route a would-be deferral (tripwire + why-not-now):
python3 scripts/defer_tally.py gate --effort Trivial --blast "⚪ 1 file" \
    [--destructive] [--reason external-block] [--policy aggressive]

# record an outcome, then read the session readout:
python3 scripts/defer_tally.py record --dir <ledger-dir> --outcome deferred --reason scope
python3 scripts/defer_tally.py readout --dir <ledger-dir>
python3 scripts/defer_tally.py reset --dir <ledger-dir>
```

`gate` returns `{route, reason_required, reason_valid, trivial, destructive,
advisory}` (exit 1 when a deferral needs a reason it didn't get).
`record`/`readout` return `{session, ratio, flag, threshold, readout, advisory}`
(exit 1 when the defer-heavy flag is raised). The `--dir` is the ledger directory;
`ratio_flag_threshold` and `stale_trivial_sessions` are read from the registry
global block when present, else defaults (3 and the scan default) apply.

**Algorithm fallback** (Python unavailable): the tripwire is `Fix Effort` is
Trivial AND `Blast Radius` names one file → do-now, UNLESS the change is
destructive (always-stop list) → needs-approval. Otherwise the deferral must name
one of `user-decision` / `scaffolding` / `scope` / `external-block`; no valid
reason → do-now. For the tally, keep a running count of fixed-now vs deferred (by
reason) for the session; the readout is `This session: F fixed inline · D
deferred (reasons: …)`; flag when `D ≥ 3 × F` (or `D ≥ 3` when `F = 0`) — advisory,
never blocking.
