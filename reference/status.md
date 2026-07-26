# Structured status: `@status` and `@verified` tokens

> Authoritative spec for the machine-readable status feature (format v2+).
> Governs how a row's status is written, read, and validated. When any command
> needs a row's status, it reads the TOKEN defined here — never the prose.

## Why this exists

A free-text Status cell can contradict itself: a row whose cell opens "RE-OPENED
/ still owed" and ends "✅ CLOSED" reads as closed to a skimmer and open to a
careful reader. That actually happened (the U5 failure) and misled a session
twice. The fix: one authoritative, machine-readable token that is THE status.
Prose after it is human narration only.

Principle: *keep judgment out of prose and in a structured field the tool can
read.* Status, and how a "done" was verified, are judgments — so they get tokens.

## The `@status` token

Every row's Status cell begins with exactly one status token:

```
`@status:<value>` <optional human narration follows>
```

### Enum (the only valid values)

| Value | Meaning |
|---|---|
| `open` | Not started. |
| `in-progress` | Actively being worked. |
| `done-verified` | Fixed AND checked against ground truth. Requires a `@verified` tier (see below). |
| `done-unverified` | Fixed in code or claimed done, but NOT yet ground-truth-checked. The "done-but-owed" state. |
| `blocked` | Cannot proceed; the narration names the blocker. |
| `withdrawn` | Retracted / not-a-bug / superseded. |

`done-unverified` is the important one: it is a real, first-class state for work
that is done enough to stop touching but not proven enough to archive. Before
this existed, such rows either falsely read as closed or cluttered the active
table.

## The `@verified` token (required on `done-verified`)

Any `done-*` status may carry a verification tier naming *how* the claim was
checked. It is REQUIRED on `done-verified`.

```
`@verified:<tier>`
```

| Tier | Means |
|---|---|
| `code` | Compiles / unit tests green / static trace. NOT proven in the real system. |
| `device` | Exercised on real hardware / real data / the actual runtime. |
| `user` | The user confirmed it by eyeball or real use. |
| `session-claimed` | A session asserted done; NO independent check. The weakest tier — a flag, not a proof. |

### The rule that makes it bite (§3a)

- `@status:done-verified` **requires** `@verified:device` or `@verified:user`
  (or `@verified:code` *with an explicit code-is-sufficient note* for pure-logic
  changes where code is itself ground truth — e.g. a parser with exhaustive
  tests).
- **`@verified:session-claimed` can NEVER back `done-verified`.** A claim is not
  a verification. Such a row is `done-unverified` at best. This encodes the
  project rule *"verified means checked against ground truth, never that a claim
  was made."*

### Provenance stamp (anti-laundering)

A `done-*` row should record who/what verified it and when, in the narration:

```
`@status:done-verified` `@verified:device` · TF77 · 2026-07-25 — round-trip confirmed
`@status:done-unverified` `@verified:code` · session 2026-07-24 — 59/59 green, device owed
```

So a later reader (or the verify pass) can check whether a "device" claim has
device evidence in the detail block. A `@verified:device` token with no device
evidence is the exact over-claim this stamp makes visible.

## The contradiction rule (§1b)

If the token says a row is `done-verified` or `withdrawn` but the narration
still says "re-opened", "still broken", "still owed", "unverified", "blocker",
etc., that is a **lint error** — the token and the prose disagree, and the token
is supposed to be authoritative. The verify pass (Phase 3) flags it. Note a
`done-unverified` row saying "owed"/"unverified" is NOT a contradiction — that
is the honest meaning of the state.

## Archive & release invariants (§1c)

- `archive` moves **only** `done-verified` and `withdrawn`. **`done-unverified`
  is HELD BACK** — it still owes a check; archiving it would bury an open
  obligation.
- A `🔴 THIS` (current-release) row still counts as a release blocker unless its
  token is `done-verified` or `withdrawn`. A `done-unverified` THIS row is STILL
  a blocker — it is not proven.

## Backward compatibility (legacy rows)

Rows written before format v2 have no token. They are NOT errors: a tokenless
row is reported `token_present: false` and passes through `list`/`scan`/`archive`
as-is (a legacy row is never auto-archived, since it is not `done-verified`).
The verify pass flags tokenless rows as "upgrade when touched," but nothing
blocks on them. New and edited rows get a token.

## How commands use this

- `list` / `scan` / `archive` / `edit` / `promote` read the `@status` token,
  never the prose, to decide state.
- `edit --status=done` requires a `@verified` tier; if only `session-claimed` is
  available, the status becomes `done-unverified`, not `done-verified`.
- `archive` uses the archive invariant above.

## Preferred implementation

Delegate parsing and validation to the helper:

```
python3 scripts/parse_status.py --row "<the table row>"
python3 scripts/parse_status.py --file <path-to-UNFORGET.md>
```

It returns JSON per row: `status`, `verified`, `status_valid`, `tier_valid`,
`contradiction`, `archivable`, `blocks_release`, and an `issues` list (empty when
clean). Exit code 1 means at least one row has an integrity issue.

**Algorithm fallback** (if Python is unavailable): the status token is the first
`@status:<value>` in the Status cell; the tier is the first `@verified:<tier>`.
Validate: `status` is in the enum; if `done-verified`, a `@verified` of `device`
or `user` (or `code` with a note) is present and it is not `session-claimed`;
and no contradiction phrase ("re-opened", "still broken", "still owed",
"unverified", "blocker") appears in the narration of a `done-verified`/
`withdrawn` row. `archivable` = status is `done-verified` or `withdrawn`.
