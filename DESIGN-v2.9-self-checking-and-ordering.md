# DESIGN — v2.9: self-checking recipes, declared ordering, proof-on-close

**Status:** SPEC, not implemented. Written 2026-08-13.
**Scope:** three related additions to format v2. All additive and backward compatible; a
ledger that adopts none keeps working exactly as it does in v2.8.0.

---

## Why these are one release

All three attack the same defect from different sides: **the ledger is a durable record of
what was once found, and nothing notices when the recorded thing stops being true.** `verify`
today checks that rows are well-formed and internally consistent. It cannot check whether
they are *accurate*.

Each part covers one point in a row's life where that bites:

| Part | Moment | Question nothing answers today |
|---|---|---|
| 1 | Row sits open | Is this premise still true? |
| 2 | Row is picked | Can this be worked yet, and what does it unblock? |
| 3 | Row is closed | Did the fix work, and did it break anything else? |

That is not a hypothetical. Everything below was measured on one real 64-row ledger
(Stuffolio `UNFORGET.md`) during a single working session on 2026-08-13, in which nine rows
were worked. The ledger passed its own gate — 0 errors — throughout.

### What actually went wrong, row by row

| Row | The row said | Reality | Class |
|---|---|---|---|
| S14 | "`CLAUDE.md` points to a nonexistent file" | File existed; the pointer had resolved for weeks. The row's own recipe had been *inverted* to say so and never closed | **fixed, unnoticed** |
| S12 | recipe checked `GoBackButton(` | The file exported **7** symbols; a passing grep proved nothing about the other 6 | **recipe too narrow** |
| A61 | recipe predicted `setTaskCompleted` = 1 | Actual: **3** occurrences; only one was the bug | **prediction drifted** |
| A38 | "teardown enumerates 2 of **4** record types" | 3 child types + a root already deleted elsewhere. One real leak, not two | **characterization wrong** |
| A43 | "ST1 writes before setting the exclusion flag" | That is the only possible order — a resource value cannot be set on a file that does not exist | **premise impossible** |
| A44 | "2 files / Small" | One file (the other must never be converted), 284 lines, 43 untyped accesses | **effort mis-sized** |
| A42 | "~10 uncached O(n) passes per render" | At most 3 cards render; real cost 3–6 | **magnitude overstated** |

Two of the rows' **prescribed fixes would have introduced bugs** if followed literally:

- **A41** prescribed a `@State` cache refreshed via `onChange`. Rows on that screen mutate
  `auditStatus`/`lastVerifiedDate`, and one sort option sorts on `lastVerifiedDate` — so the
  cache would go stale on the screen's primary action and the list would visibly fail to
  reorder.
- **A43** was first "fixed" by excluding the enclosing directory. Per a note already in that
  codebase, directory-level `isExcludedFromBackup` does not cascade to files on iOS — the row
  would have read *fixed* while the large file kept being backed up. Caught before commit.

**The split this release is built on:** four of those seven failures are mechanically
detectable (fixed-unnoticed, too-narrow, drifted, impossible-to-observe). Three are not
(characterization, sizing, magnitude) — they required reading the code. Part 1 addresses the
first group and **states plainly that it cannot address the second**.

---

## Part 1 — Self-checking verify recipes

### The gap in one sentence

`verify`'s `stale-recipe` check (§4/Check 8) verifies that a recipe **exists**. It never runs
one. A row can carry a recipe that has been wrong for months and pass clean.

### The change: recipes carry their expected result

Today a recipe is prose, and the expected value is embedded in a sentence nobody re-executes:

```
**Verify-still-open:** `grep -c 'X' path/File.swift` = 1 → still uncached.
```

v2.9 makes the expectation *data*:

```markdown
**Verify:** `grep -c 'X' path/File.swift` → expect 1 [open]
**Verify:** `grep -c 'FamilyPreference' path/File.swift` → expect >=1 [closed]
```

- `→ expect <op><value>` — the assertion. Operators: `=`, `>=`, `<=`, `>`, `<`, `!=`.
- `[open]` / `[closed]` — **which state the expectation describes.** This is what makes an
  inverted recipe (S14) representable instead of a comment nobody reads.

Prose recipes stay valid and are reported as `unrunnable` — never as failures. A ledger
adopting nothing keeps its current behavior.

### `verify --run` and the four states

Executing a recipe yields four outcomes. Today's tool collapses all of these into
"a recipe exists":

| State | Condition | Meaning | Severity |
|---|---|---|---|
| **HOLDS** | ran; matched the `[open]` expectation | Row still true | info |
| **FIXED** | ran; matched the `[closed]` expectation | Someone fixed it and never closed the row (**S14**) | **warn** |
| **DRIFTED** | ran; matched neither | Premise changed under the row (**A61**: expected 1, found 3) | **warn** |
| **DECAYED** | command errored, or path does not exist | Recipe can no longer observe its target (**S12**, and a moved path in `S3`) | **warn** |

`DECAYED` is the load-bearing one. A grep against a moved path prints nothing and exits
non-zero — which reads identically to "the defect is gone" if you only look at the count.
That false-pass mode is why the expectation must be checked separately from the exit status.

### Execution safety

Recipes are executed, so this is a code-execution surface in a file that may be shared.

- **Allowlist only:** `grep`, `rg`, `ls`, `test`, `find`, `awk`, `sed`, `wc`, `python3` —
  refuse anything else and report `unrunnable`, not an error.
- **No shell.** Parse to `argv` and run without a shell; a recipe containing `|`, `;`, `&&`,
  `>`, backticks, or `$(` is `unrunnable`. (This also sidesteps the table-cell pipe problem
  that broke a row in the source ledger — a `|` inside a recipe splits the markdown row.)
- **Read-only + sandboxed:** refuse any recipe whose argv contains a write-capable flag;
  execute with the ledger's repo as cwd; refuse absolute paths outside it.
- **Timeout** 5s per recipe, `--jobs` parallel, default 8.
- `--run` is **opt-in**. Bare `verify` stays read-only and does not execute anything.

### Gating

`--run` findings are `warn`, not `error` — they do **not** gate `archive`/`promote` in v2.9.

Rationale: severity escalation should follow field data, the same caution that kept the
char-budget hard threshold at 4× rather than 1×. A `FIXED` result is a strong signal but
still needs a human to confirm the row is genuinely closed rather than partially addressed
(**A44** in the source session was partially fixed and deliberately left open — an
auto-closer would have gotten that wrong).

### New verification tier

`@verified:recipe` — "premise mechanically re-checked." Ranked **below** `@verified:code`
(a human read it) and far below `device`/`user`. It may never back `done-verified`, same rule
as `session-claimed`.

**This is the honest boundary and it belongs in the docs, not just the code:** a green recipe
means *the row is worth reading*, not *the row is correct*. A38's wrong record-type count,
A44's mis-sizing, and A42's overstated magnitude would all pass a recipe check cleanly.
Claiming otherwise would rebuild the exact false-confidence failure this skill's own
documentation warns about (an audit that cannot model a thing reports it CLEAN).

---

## Part 2 — Declared ordering

### The gap

The format has no dependency concept. `blocked` is a *status* meaning "waiting on something
external," with no field naming what. Measured on the source ledger: **five real ordering
relationships, all in prose, none machine-readable.**

### Four relations, not one

Collapsing these into a generic `depends-on` would lose the information that makes each
useful — and would mislabel work as unstartable when it isn't.

| Relation | Meaning | Effect on ordering | Live example |
|---|---|---|---|
| `blocked-by: X` | Cannot start until X ships | **Hard.** Excluded from `--view=next` | A49 was blocked-by A48, U2 |
| `latent-until: X` | Fixable now; harmless until X lands | Soft — lowers urgency, not startability | A38 latent-until A37 |
| `same-root: X` | One cause, two rows | Fixing X likely closes this | A51 same-root A36 |
| `sibling: X` | Complementary halves | Shipping one alone is partial | A13 sibling A14 |

Only `blocked-by` is a hard constraint. **A38 was `latent-until: A37` and was fixed anyway,
correctly, in the source session** — a single `depends-on` field would have hidden it.

### Where it lives

Not a column: an 11th/12th column blows the width budget and the row-length rule. It goes in
the detail block as one parseable line:

```markdown
- **A38** — blocked-by: none · latent-until: A37 · same-root: none · sibling: none
```

Omitted relations default to `none`. A row with no dependency line is unconstrained — no
migration required.

### What it enables

1. **`--view=next` stops recommending blocked work.** Today it ranks on severity alone and
   would hand you a row whose prerequisite is open.
2. **`verify` well-formedness:** target row exists · no cycles · **not already closed**.
   That last one is the A49 case exactly — its block resolved and it was hand-noticed on
   08/11, an unknown stretch after the fact.
3. **A mechanical fix order.** The Phase 1/2/3 sequencing in the source session was human
   judgment from reading rows; with `blocked-by` recorded it is a topological sort. It would
   also have surfaced that A51 was probably free once A36 shipped.

### The honest limit

Same boundary as Part 1. `verify` can check a **declared** dependency is well-formed. It
cannot **discover** an undeclared one. A38's latency on A37 was found by a human reading two
rows; nothing derives that from a codebase.

Worth noting anyway: all five relationships in the source ledger were *already written down*
in prose. The information exists — it is just not in a form anything can act on.

### Explicitly out of scope

A dependency **graph visualization**. At 39 open rows the four relations plus a
topological `--view=next` deliver the value; a renderer is cost without a demonstrated need.

---

---

## Part 3 — Closing a row must require proof, not assertion

### The gap

Parts 1 and 2 keep an **open** row honest. Neither says anything about the moment that
matters most: **closing** one. Today `edit --status=done-verified` is an assertion. Nothing
asks what was run, whether it passed, or whether anything else broke.

Measured on the source session: **nine rows were worked and eight closed as
`done-unverified`** — code written, nothing compiled, because the working volume could not
build. That is the honest outcome and the status tier for it already exists. What is missing
is that the ledger records *that* a proof is owed without recording *which* proof, so the
next session has to re-derive it from prose.

Worse, two distinct things are conflated under one word:

- **Does the fix work?** (the row's own claim)
- **Did the fix break something else?** (everything the row does not mention)

A row can be perfectly closed on the first and silently wrong on the second.

### The change: a `Proof` line, symmetric with `Verify`

```markdown
- **A38** — proof: `xcodebuild test -only-testing:StuffolioTests/LegacyTeardownCoverageTests` → expect pass
  regression: `xcodebuild test -only-testing:StuffolioTests/LegacyShareManagerTests` → expect pass
  owed: build [X10]
```

Three fields, each answering a different question:

| Field | Question | Missing today |
|---|---|---|
| `proof:` | What run demonstrates this fix works? | Named in prose, or not at all |
| `regression:` | What run demonstrates nothing else broke? | **Nothing represents this** |
| `owed:` | What proof cannot run here, and where must it? | Buried in status prose |

`owed:` is what makes a cross-machine workflow legible. A row closed on one volume that
still needs a device run, a macOS build, or a Sentry re-check says so as data, not as a
sentence a future session must notice.

### The rule

**`done-verified` requires a `proof:` that ran and passed.** A row whose `proof:` is absent,
`unrunnable`, or failing may not be `done-verified` — it is `done-unverified`, which is
already a first-class state. This makes the existing "`done-verified` requires
device/user tier" rule enforceable rather than advisory.

`regression:` is **recommended, not required**, and its absence is reported (`info`) rather
than blocking. Requiring it everywhere would push people to name a trivial passing test to
satisfy the checker — worse than an honest blank.

### The guard-test discipline, promoted from practice to spec

Three guard tests were written in the source session (A38, A71, and by extension A61). Each
was validated the same way, and it is the part worth standardizing:

> **A regression guard must be shown to fail against the pre-fix state.**

A test that passes after a fix proves nothing on its own — it may pass against *anything*.
Both guards were checked by reproducing their logic outside the compiler and asserting the
pre-fix input fails. One of them, A38's, would have passed vacuously if a regex had gone
stale; it carries an explicit non-empty assertion for exactly that reason.

`verify` cannot check this property mechanically. It **can** require the claim be recorded:

```markdown
  proof-negative: verified 2026-08-13 — fails against pre-fix list
```

An unrecorded `proof-negative` on a row citing a new test is an `info`, not an error. The
value is that "I checked this the cheap way" becomes visible instead of assumed.

### Why this is not just "run the tests"

A full suite run answers "did anything break" but not "did *this* fix work" — a fix with no
covering test passes the suite trivially. Conversely a targeted test answers the first and
not the second. Both fields exist because they are different questions, and today's format
represents neither.

### The honest limit

`verify --run` can execute a `proof:` and report pass/fail. It cannot judge whether the proof
is *adequate* — whether the test actually exercises the defect. That is the same boundary as
Parts 1 and 2, and it is why `proof-negative` is a recorded human claim rather than a
computed one.

---

## Implementation order

1. Recipe grammar + parser (`scripts/recipe.py`) — no execution. Report `unrunnable`.
2. `verify --run` with the four states and the safety rules.
3. Dependency line grammar + well-formedness checks in `verify`.
4. `--view=next` honors `blocked-by`.
5. `@verified:recipe` tier in `reference/status.md`.
6. `proof:` / `regression:` / `owed:` grammar; `done-verified` gated on a passing `proof:`.
7. `proof-negative` recorded claim + `info` when absent on a row citing a new test.

Steps 1–2, 3–4, and 6–7 are independent and can ship separately. **6 depends on 1–2** — the
proof runner is the recipe runner, same parser, same allowlist, same four states.

---

## Build notes

Resolutions to the questions an implementer hits first. Every number below was measured
across the three source ledgers (`UNFORGET.md`, `TERRY-UNFORGET.md`, `MI-UNFORGET.md`) on
2026-08-13, not estimated.

**Recipe corpus as it exists today — 111 backticked commands:**

| First token | Count | Note |
|---|---|---|
| `grep` | 94 | 85% of the corpus |
| `git` | 5 | all `remote get-url` |
| `ls` | 4 | |
| `find` | 2 | one is the bare word `find`, not a command |
| `awk` | 1 | a range-scoped function body scan |
| `security` | 1 | ⚠️ see Safety below |
| prose false-positives | 2 | `convention`, `command -v gh` |

Path style: **86 relative · 5 absolute.** Pipes: **1** (the row that broke its own table).

### 1. Migration — do NOT report 111 `unrunnable` on first run

A wall of noise on day one trains people to ignore the check, which is the failure the
em-dash bug demonstrated (a check that can only false-positive gets tuned out).

**Resolution:** `--run` is **opt-in per recipe**. A recipe without the `→ expect` clause is
skipped silently and not counted as a finding. Only recipes that declare an expectation are
executed. Adoption is then row-by-row, at the moment someone touches a row anyway.

`verify --run --propose` is the one-time helper: it parses prose recipes of the existing
shapes (`= N`, `≥ N`, `>= N`, `= 0`) and prints the v2.9 line it *would* write, without
writing it. **Measured feasibility: 74 of 111** carry both a `grep -c` command and an
explicit expected number, so one narrow pattern converts two-thirds; the remaining 37 stay
prose until hand-edited.

⚠️ Note the two counts differ and it matters: **94** recipes *start with* `grep`, but only
**74** state a number a parser can extract. The other 20 are greps whose expectation lives in
a sentence ("→ still uncached", "→ both gated"). Sizing this work off the 94 would overstate
what automation can do by a quarter — the same overstatement class as A42's "~10 passes."

### 2. Repo root — the registry does not know it

Recipes cite paths relative to *something* the registry has never recorded. The ledger dir is
known; the source tree is not.

**Resolution:** add one optional global registry key, `source_root`, defaulting to the
ledger dir's nearest ancestor containing `.git`. Resolution order for a recipe path:
absolute → used as-is (and must pass the sandbox check below) · relative → resolved against
`source_root`.

Both styles already occur in the wild (86 vs 5), so **both must keep working** — rewriting
5 absolute paths as part of this release would be scope creep with no benefit.

### 3. Pipes — a documented no-pipe rule, not an escape

Exactly one recipe in 111 contains a pipe, and it broke the row it was written in: the `\|`
inside `grep -n 'A\|B'` was read by markdown as a column break, so the row parsed as 11 cells
against a 10-column table and failed the gate. It was fixed by rewriting the command
pipe-free, not by escaping it.

**Resolution:** recipes are **pipe-free by rule**, which falls out of "no shell" anyway
(§ Execution safety). A recipe containing `|` is `unrunnable` with a message naming the
table-cell hazard and suggesting the rewrite. An HTML entity (`&#124;`) is deliberately NOT
adopted: no ledger in the corpus uses one, and it would make the command non-copy-pasteable —
trading a parse failure for a usability failure.

Alternation is expressible without a pipe: `grep -n 'DETAIL_.*_RE = '` replaced
`grep -n 'A\|B'` in the source incident and returned strictly more useful output.

### 4. Safety — the corpus contains a live credential-printing command

One existing recipe is `security find-generic-password -s github-pat -a $USER -w`. Per
`security help find-generic-password`, `-w` is *"Display only the password on stdout"* — so
this recipe's entire output **is a credential**. It is a legitimate manual check; it must
never be executed by a runner or have its output captured into a report.

Three rules follow, and they are not theoretical:

- **`security` is not on the allowlist.** Neither is `git`, despite 5 uses — `git` is a
  large surface with write subcommands, and `remote get-url` is not worth the exposure.
  Both report `unrunnable`.
- **Never echo recipe stdout verbatim.** Report only the extracted value compared against
  the expectation (`expected 1, got 3`). A runner that printed output would have leaked the
  PAT above.
- **`$USER`, `$(…)`, backticks, `~` → `unrunnable`.** No variable expansion, which follows
  from "no shell" but is worth stating because the corpus already contains one.

### 5. Session-start integration

`--run` belongs in the session-open flow, so a session learns which rows decayed *before*
picking work rather than mid-fix. That is how the source session went wrong: four stale
recipes were discovered one at a time, each after the row had already been selected.

**Resolution:** not automatic. A skill that silently executes commands at session start is
the wrong default for a shared, git-committed file. Instead `list` reports a one-line
summary when any row carries a runnable recipe that has not been run this session —
`3 rows have unverified premises · run: /unforget verify --run` — and the user decides.

### 6. Test strategy — Part 3's rule applied to Part 3

The bench is 328 lines (`tests/test_row_visibility.py` + `normalize.py`) against ~2,900 lines
of touched spec and code. This release adds an execution surface, so the guards matter more
than usual.

Minimum bench, each written to **fail against the pre-change state** per this spec's own
regression-guard rule:

| Guard | Must fail before |
|---|---|
| A `[closed]`-matching recipe on an open row reports **FIXED** | today: no state at all |
| A moved path reports **DECAYED**, not a passing 0-count | today: silent false pass |
| An expectation mismatch reports **DRIFTED** with both values | today: nothing compares |
| A piped recipe reports `unrunnable`, never executes | — |
| `security`/`git`/`$USER` report `unrunnable` | — |
| Recipe stdout never appears in report output | ⚠️ the PAT-leak guard |
| A `blocked-by` cycle is an error | today: no relation exists |
| A `blocked-by` naming a closed row is a warn | the A49 case |
| `done-verified` with a failing `proof:` is refused | today: assertion only |

Fixture ledgers must include an **em-dash** variant. The detail-pointer check was blind to
em-dash ledgers for a full release because every fixture used ASCII hyphens — the same
monoculture would hide the next parser bug.

### 7. Open decisions — NOT resolved here

- **Does `--run` ever gate `archive`/`promote`?** Spec says no for v2.9 (warn only). Revisit
  after field data, same escalation caution as the char-budget hard threshold.
- **Should `--propose` be able to write?** Currently print-only. Writing 94 auto-converted
  recipes unattended is a large unattended edit to a file that is the single source of truth.

---

## Version

Minor → **v2.9.0**. Additive, backward compatible, no forced migration. Per this repo's
`--version` reconciliation, bumping means updating all five declaration sites: SKILL.md
frontmatter, `.claude-plugin/plugin.json`, the newest changelog heading, the README badge
cache-buster, and the README `**Maturity:**` bullet.

## Provenance

Every failure class above is a measured incident from one session on 2026-08-13 against
Stuffolio's `UNFORGET.md` (64 rows) and `TERRY-UNFORGET.md` (55 rows), not a hypothetical.
Both ledgers passed `verify` with **0 errors** before, during, and after — which is the
argument for this release in one sentence.

Session tally, as the sizing evidence:

- **9 rows worked** → 6 `done-unverified`, 2 `done-verified`, 1 left open. Nothing compiled:
  the working volume's signing certificate is revoked, so `xcodebuild` fails before any Swift
  compiles. The two `done-verified` are precisely the rows provable *without* a compiler —
  a deletion of provably-unreferenced code, and a doc pointer whose target was checked to
  exist. **That distinction is exactly what `owed:` is for**: 6 rows owe a build, 2 owe
  nothing, and today only prose says which.
- **3 rows had wrong premises** (S14 already fixed, A43's ST1 not a defect, A44 mis-sized).
- **2 prescribed fixes would have caused bugs** if followed literally (A41's cache, A43's
  directory-level exclusion).
- **5 ordering relationships** existed in prose, none machine-readable.
- **3 guard tests** written, each validated by showing it fails against the pre-fix state.

The counterfactual is the point: following the rows literally would have shipped two
regressions and re-done one already-fixed item, while the gate reported clean.

## What this spec does NOT claim

Stated plainly so a later reader does not over-trust the release:

- A recipe verifies a **premise**, never a **judgment**. A38's wrong record-type count,
  A44's mis-sizing, and A42's overstated magnitude all pass a recipe check cleanly.
- `verify` checks **declared** dependencies. It cannot discover undeclared ones.
- A `proof:` that passes does not mean the proof is **adequate** — only that it ran.

Each of those is a human read, and the spec's job is to make the boundary visible rather
than to paper over it.
