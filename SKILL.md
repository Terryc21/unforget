---
name: unforget
version: 1.6.0
description: |
  A single source of truth for deferred work: paused plans, mid-task spillover,
  audit findings, and observed bugs. Kept in one UNFORGET.md per project so
  nothing slips between releases. Activate when the user asks "what's deferred?",
  "what's the backlog?", "prioritize my plans," "show me what's blocking release,"
  or wants to log something for later without losing it.
license: Apache-2.0
---

# unforget

> Installed as a Claude Code plugin (current version: v1.0; plugin install available since v0.2). Manual install via `~/.claude/skills/unforget/` (invoked as `/skill unforget`) still works as a v0.1 fallback.

> A way of not losing sight or track of what is deferred.

## Why this skill exists

Every developer defers things. The problem isn't the deferral. The problem is that deferred items end up scattered across:

- a `Deferred.md` at the repo root
- date-prefixed plan files in some "deferred" folder
- audit-tool ledgers (radar-suite, ESLint TODO comments, etc.)
- Slack DMs to yourself
- comments in code (`// TODO: come back to this`)
- memory files for AI assistants
- paused plan files in `~/.claude/plans/`

When the user asks "what's deferred?" months later, the answer requires walking every one of those surfaces. Items go stale. Some get fixed by accident. Some sit forever because nobody remembered them.

`unforget` collapses all deferral into ONE file (`UNFORGET.md`) with a structured format that:

1. **Forces the deferral question** ("when does this ship?") via the Target column.
2. **Surfaces staleness** via a built-in scan command that flags items past their age threshold.
3. **Standardizes the format** so any developer reading any project's UNFORGET.md instantly recognizes the structure.

The pattern was extracted from a real Universal app (iOS, iPadOS, macOS) where deferred work had fragmented across five tracking surfaces. Consolidation freed roughly 3 hours of release-prep time per cycle.

---

## Format at-a-glance

UNFORGET.md is a single markdown file with **4 sections**, each containing a rating table whose width depends on the preset (10 columns for Standard, 9 for Compact / Continuous, 6 for Lean).

**Sections:** 1. Paused plans (P) · 2. Session spillover (S) · 3. Audit findings (A) · 4. User-reported / observed (U)

**Columns (Standard preset):** `# | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status`

**Target values:** 🔴 THIS (blocks current release) · 🔵 NEXT (next post-release update) · 🟡 LATER (two cycles out) · ⚪ SOMEDAY (no commitment)

**Invariant:** `🔴 THIS` is the only Target that blocks shipping. At submission time, every `🔴 THIS` row must be Status = Fixed or have been demoted with a one-line reason.

**Full format spec lives in `reference/format.md`:** column meanings, Status enum, detail-block format (closure pointer → body → verify-still-open recipe → spawn links), Standard / Compact / Lean / Continuous presets, and anti-patterns. Read that file when writing or validating a row.

**Open rows whose details cite specific file paths SHOULD carry a `**Verify-still-open:**` one-line recipe in the detail block** — a 10-second grep that confirms the row's premise still matches the current source. Rows decay independently of fixes (refactors move lines, parallel sessions ship silent fixes); the recipe makes that grep a structural checkpoint, not a habit. See `reference/format.md` § Verify-still-open recipe for the three-layer cascade.

---

## Subcommand surface

| Subcommand | One-line purpose | Full spec |
|---|---|---|
| `/unforget init` | Bootstrap UNFORGET.md and survey existing deferral artifacts across the project | `reference/init.md` (with surface detail in `reference/surfaces.md`) |
| `/unforget add` | Capture a new deferral (defaults to Section 2 / Session spillover); 30s end-to-end | `reference/commands.md` |
| `/unforget edit` | Refine a row's columns; closure recommendations on `--status=Fixed` | `reference/commands.md` |
| `/unforget import` | Re-run the surface survey after init (catches NEW artifacts) | `reference/commands.md` (surface detail in `reference/surfaces.md`) |
| `/unforget list` | Show current state, filterable by section / Target / Urgency / age / staleness | `reference/commands.md` |
| `/unforget scan` | Identify rows past their staleness threshold; read-only | `reference/commands.md` |
| `/unforget branch` | (format v2+) Atomically create a child ledger (header + parent pointer + registry entry, all-or-none) when work differs on the actor / lifespan / domain axis | `reference/branching.md` (summary in `reference/commands.md`) |
| `/unforget verify` | (format v2+) Integrity lint: contradictions, unproven "done", bloat, stale recipes, registry drift; read-only; gates `archive`/`promote` | `reference/verify.md` |
| `/unforget archive` | Move completed (Done/Fixed) rows out of the active tables into an archive file; lightweight, run anytime; holds back "Done-but-owed" rows | `reference/commands.md` |
| `/unforget promote` | Release-time ritual: verify 🔴 THIS rows fixed, promote 🔵 NEXT to 🔴 THIS | `reference/promotion.md` (with backups in same file) |
| `/unforget --version` | Print version, install path, supported format-version; install-verification | `reference/commands.md` |

**Decision flowchart: which subcommand do I run?**

- **No UNFORGET.md exists in the project yet** → `/unforget init`
- **You want to capture one new item, fast** → `/unforget add "<finding>"`
- **You want to update an existing row's columns** → `/unforget edit <ID>`
- **A new audit / plan / memory file appeared since init** → `/unforget import`
- **The user just asked "what's deferred?"** → `/unforget list` (or `/unforget list --target=THIS` for ship-blockers only)
- **You want to find rows that have aged past their thresholds** → `/unforget scan`
- **Deferred work differs on actor (a different *human* acts on it) / lifespan (a sprint with its own discipline) / domain (a different repo or subject)** → `/unforget branch` (but default to a row or section — see `reference/branching.md`)
- **Completed rows have piled up and you want them out of the active view** → `/unforget archive` (lightweight; use this between releases instead of `promote`)
- **You're about to ship a release** → `/unforget promote`
- **You want to verify the install loaded correctly** → `/unforget --version`
- **A row is being closed (`/unforget edit <ID> --status=Fixed`) and you want the post-fix sweep** → see `reference/promotion.md` § post-fix-sweep

---

## Companion files

This SKILL.md is intentionally thin. The full spec is split across `reference/*.md` files loaded on demand:

| File | What's in it | Loaded when |
|---|---|---|
| `reference/format.md` | Column definitions, Status / Target enums, detail-block format, presets, anti-patterns | Writing or validating a row |
| `reference/init.md` | Phases 1–7 of the init walkthrough, success criteria | Running `/unforget init` |
| `reference/surfaces.md` | Six core surfaces, Surface 1b general doc scanning, redirect-pointer pre-check, memory-dir resolution, path encoding, meta-file pre-check, audit-tool format-aware parsing, cross-surface dedup, GitHub-issues four states, algorithm fallback | Running `init` or `import`, or auditing surface behavior |
| `reference/promotion.md` | Promote ritual, dry-run mechanics, post-fix-sweep workflow, backups and recovery | Running `/unforget promote` or marking a row Fixed |
| `reference/commands.md` | Per-subcommand specs for `add`, `edit`, `import`, `list`, `scan`, `archive`, `--version` (incl. `--version`'s install-integrity + recall-trigger checks) | Running any of those subcommands |
| `reference/status.md` | (format v2+) `@status` / `@verified` tokens: the status enum, the `done-verified`-requires-device/user rule, the token↔narration contradiction rule, archive invariant, provenance | Reading/writing a row's status; running `archive`/`list`/`edit` |
| `reference/registry.md` | (format v2+) the registry: schema (global config + per-ledger), README-canonical rule (README wins over the `.unforget.json` cache), where it lives | Resolving where ledgers live / reading persisted posture & policies |
| `reference/verify.md` | (format v2+) the `verify`/doctor integrity lint: the checks, read-only rule, archive/promote gating, enforceable verify-still-open recipe | Running `/unforget verify`; before `archive`/`promote` |
| `reference/deferral-gate.md` | (format v2+) the deferral gate at `add`: the trivial tripwire, the "why not now?" allow-list, and the session defer/fix accounting that backs it | Running `/unforget add`; showing the session readout on `list` |
| `reference/branching.md` | (format v2+) the branching model: the three axes (actor / lifespan / domain), the decision cascade, parent/child conventions, and the atomic `branch` command | Deciding whether work earns a child ledger; running `/unforget branch` |
| `reference/skill-handoffs.md` | (format v2+) companion skill handoffs: the 5 functions, the global manifest, install-state detection by invocable name, frequency governance, the shipped-default disclosure | Firing a companion recommendation at a done/promote/verify transition |
| `scripts/*.py` | Deterministic helpers (surface scan, fuzzy dedup, path encoding, format-version check, backup prune, status-token parse, registry read/write, integrity verify, deferral gate + tally, atomic branch creation, recall-block writer, import drift detector, row-length check + lossless split, companion manifest + resolver). JSON in / JSON out. Standard library only. See `scripts/README.md`. | Whenever the corresponding reference file delegates to a script |

**Spec-substitution principle.** This SKILL.md is the index, not the spec. When implementing or modifying any subcommand, `Read` the linked reference file before acting. The reference files are authoritative.

---

## How to use unforget alongside CLAUDE.md / AGENTS.md

The skill works best when the project's main AI instructions file has a section that points at UNFORGET.md as the canonical deferral source. `/unforget init` offers to add this for you. Example block:

```markdown
## Deferred Work Index

**Single source of truth:** `Documentation/Development/Deferred/UNFORGET.md`

Read this file when:
- The user asks "what's deferred?", "what's the backlog?", "prioritize my plans," or any variant.
- Before suggesting a release / submission, to check 🔴 THIS rows for unresolved blockers.
- When a task in the current session needs to be deferred, log a row here. Do NOT create a new tracking file unless the entry needs detail beyond one row.

**Format:** 10-column rating table per section. **Sections:** Paused plans / Session spillover / Audit findings / User-reported.

**Target column** is the release-cycle commitment: 🔴 THIS / 🔵 NEXT / 🟡 LATER / ⚪ SOMEDAY.

Never log deferred items elsewhere. Memory files, plan files, and audit ledgers are detail stores; UNFORGET.md is the index.
```

This block is what makes the skill's recall trigger work. Without it, future AI sessions don't know to read UNFORGET.md when the user asks about deferred work.

---

## Compatibility notes

- **Non-Claude-Code use:** UNFORGET.md is plain markdown. The format works fine in any editor, on GitHub, in Linear, etc. The slash commands require Claude Code, but the file itself is portable.
- **Multi-user / team use:** UNFORGET.md commits to git like any other markdown. Concurrent edits use standard merge resolution. Status changes between Open / In Progress / Fixed should be done atomically per row to minimize merge churn.
- **Other AI assistants:** The "Deferred Work Index" block in CLAUDE.md / AGENTS.md works for any AI that reads project instructions. Cursor, Copilot, Aider, etc. can all benefit from the recall trigger pattern.
- **CI integration:** `/unforget scan` output is structured markdown. A simple GitHub Action can run the scan weekly and post the report to a Slack channel or open an issue. The `scripts/*.py` helpers are standalone and can be invoked from CI without Claude Code.
- **Python 3.9+:** the helper scripts under `scripts/` use Python 3.9+ standard library only (no third-party deps). When Python is unavailable, each `reference/*.md` file that delegates to a script keeps an "Algorithm fallback" paragraph the LLM can re-derive from. The fallback is functional but slower and non-deterministic; install Python 3.9+ for the canonical implementation.

### Format-version contract

Every read operation (`add`, `list`, `promote`, `scan`, `edit`, `import`, `verify`) checks for an HTML comment marker of the form `<!-- unforget-format: vN -->` near the top of UNFORGET.md. The marker declares which version of the unforget file format the file conforms to. This skill (v1.6) supports formats `v1` and `v2`. `v2` adds the `@status`/`@verified` status tokens, the registry, the `verify` lint, the deferral gate, branching, the onboarding/recall-block wiring, the row-length discipline (bounded index rows + lossless splits), and the companion-skill handoffs (function→manifest, invocable-name detection); a `v1` file has none of those and is read/written as a legacy ledger (tokens optional, never required). Three cases:

- **Marker absent.** The skill prompts: "this file may not be in unforget format; proceed anyway?" Default response is no. If the user proceeds, the skill operates as best it can without format guarantees, and recommends adding `<!-- unforget-format: v2 -->` near the top of the file to silence the prompt on future reads.
- **Marker recognized (`v1` or `v2`).** The skill proceeds normally. A `v1` file is treated as a legacy ledger: the v2-only features (status tokens, registry, `verify` errors) simply don't apply; nothing is required or auto-added until the file is upgraded to `v2`.
- **Marker is a future version (`v3` or higher).** The skill prints: "this file declares unforget format vN, but this skill version supports up to v2. Operating in read-only mode; writes are refused." Read-only operations (`list`, `scan`, `verify`, and `promote --dry-run`) still work. Write operations (`add`, `edit`, `import`, and `promote` without `--dry-run`) refuse with a one-line error pointing to the version mismatch and recommending a skill upgrade.

**Preferred implementation:** delegate the marker read to `python3 scripts/check_format_version.py <path-to-UNFORGET.md>` (returns JSON). Algorithm fallback if Python is unavailable: read the first 30 lines of the file, grep for `<!-- unforget-format: v` (case sensitive), parse the version digit, compare against supported.

---

## Anti-patterns (summary)

Things this skill deliberately does NOT do: custom column reordering · custom rating scales · per-row column visibility · renaming core columns · multiple files · auto-deferring on the user's behalf.

See `reference/format.md § Anti-patterns` for why each is banned — that file is the single source; this line is only the index.

---

## Changelog

### v1.6.0 — companion skill handoffs (2026-07-26) · format v2 · **v1.1 design build COMPLETE**
Phase 8, the final phase: unforget recommends OTHER skills at earned ledger transitions —
function-based, not skill+URL hardcoded through trigger points, so a companion link rots in ONE
place (the manifest), never twelve.

- **Five fixed functions** (`reference/skill-handoffs.md`): `post-fix-sibling-scan`,
  `ship-risk-scoring`, `audit-reverify`, `forward-bug-hunt`, `verify-against-reality`. Each fires
  at a specific ledger transition and names the earned reason — never a generic "you might like
  these skills" footer.
- **One global manifest** (`~/.claude/unforget-companions.md`, `scripts/companions.py`): function →
  skill → invoke → url, the ONLY place a companion URL is written. Projects inherit it. Ships a
  default mapping the author's skills, **disclosed at init** (overridable in one place; unforget
  works with no manifest at all).
- **Install-state detection by INVOCABLE NAME, never a dir find** (the one-star-risk lesson —
  `one-star-risk` is invocable but has no dir of that name). Three states: installed → run the
  command, no URL; not-installed → one soft pointer with the manifest URL; unset → say so, invent
  no URL. `verify` gains a rot check for entries neither installed nor reachable.
- **Governance:** at most once/function/session; a **trivial close fires nothing**; advisory,
  never blocking, and never a way to *defer* the scan (a handoff means do-it-now-while-context-is-hot).
- **Reconciled** the pre-existing inline `/radar-suite`+`/bug-echo` closure block (which hardcoded
  two URLs and detected installs by directory name) into this function/manifest system across
  `edit`, `promote`, `deferral-gate`, and `verify`.

With Phase 8 the **v1.1 design build is complete** — all eight phases (status tokens, registry,
verify lint, deferral gate, branching, onboarding, row-length, companion handoffs) shipped.
Backward compatible throughout: every feature degrades cleanly on a v1 ledger.

### v1.5.0 — row-length discipline (2026-07-26) · format v2
Phase 7 of the v1.1 design build: the **row-length rule** that keeps a ledger Readable. A row is a
one-line INDEX; history/context/verification narration belongs in a detail block, not fused into an
ever-growing Finding or Status cell. The 2026-07-25 failure was a ~155KB ledger with multi-KB rows
whose Reads truncated and *misled* the reader — a bounded index prevents exactly that.

- **The two-part row** (`reference/format.md` § Row-length discipline). The table row carries a
  compact index (a one-line finding summary + the `@status`/`@verified` tokens + a one-line
  status); the unbounded content lives in a `### Detail - <section>` bullet. History is **appended**
  to the block, never grown in the cell.
- **`scripts/row_budget.py`.** `check` flags Finding/Status cells over the budget (default 400,
  registry-configurable via `row_char_budget`). `split` turns an over-budget row into a bounded
  index + a detail-block bullet holding the **full original content verbatim** — and returns
  `lossless:true` only when every character is provably preserved, **refusing** otherwise. The hard
  rule: the budget MOVES history to the block, it NEVER deletes it.
- **Wired:** `scan` gains the char-budget lint; **`verify --fix`** offers the split for char-budget
  findings *only*, per row, with approval (the one integrity finding safe to auto-resolve because
  it's mechanical and lossless-verifiable). `verify` with no flags stays read-only exactly as before.

Backward compatible: the rule flags legacy over-long rows but never blocks on them; a split is
always offered, never forced, and only ever moves content — a legacy ledger keeps working untouched.

### v1.4.0 — onboarding, registry wiring, and the maintained recall block (2026-07-26) · format v2
Phase 6 of the v1.1 design build: `init`/`import` now write and reconcile the two persisted
surfaces the whole system depends on — the **registry** and the **maintained recall block** — so
nothing the skill relies on lives only in memory (the through-line of the onboarding design). This
is the fix for the 2026-07-25 split-brain (ledgers stranded in a parallel tree) and stale-pointer
(a CLAUDE.md index that described an old layout) failures.

- **Onboarding questions** (`reference/init.md`). `init` adds the **git-posture** question (split /
  committed / ignored — split recommended, and the skill writes the `.gitignore` rules itself,
  incl. ignoring the ephemeral `.unforget-session.json` and `.unforget.json` cache), and upgrades
  the recall question to **maintained / manual / none**. It writes the registry + the two policy
  defaults (Policy 1 deferral, Policy 2 multi-axis) at the end.
- **The maintained recall block** (`reference/init.md`, `scripts/recall_block.py`). A
  marker-delimited Deferred Work Index in CLAUDE.md/AGENTS.md, rebuilt from the registry by
  init/import/branch so it can't rot — rewriting only between its markers, never the user's
  content. `branch` now updates it as a **fourth atomic artifact** (rolls back with the other three
  on any write failure).
- **`import` drift detection** (`scripts/import_drift.py`). Reconciles the registry against reality
  — **registered-but-missing** (error), **found-but-unregistered** (the stranded-parallel-tree
  check), **posture-mismatch**, and **stale-recall**. Read-only; reports, you fix.
- **Migration for already-messy projects** (`reference/init.md` § Phase 6b, `reference/surfaces.md`
  § non-standard locations). `init` ASKS for out-of-repo ledger locations (rather than a disk-wide
  scan), proposes consolidation, and **verifies byte-identical before removing any original** — the
  one-way-door discipline for not losing a ledger during a move.

Backward compatible: all of it is v2; a v1 ledger keeps working, and a project with no registry
just gets the pre-v2 behavior (branch stays reachable via the parent pointer, no recall
maintenance).

### v1.3.0 — branching + the `branch` command (2026-07-26) · format v2
Phase 5 of the v1.1 design build: the **branching model** and an atomic `/unforget branch`
command. The default is still NOT to branch — most deferred work is a row or a section. A new
ledger is justified only when work differs from the parent on one of three axes.

- **The three axes** (`reference/branching.md` §2): **actor** (a different *human* acts on it —
  earns a file even at identical discipline, that's what a `TERRY-UNFORGET` is; a machine/
  automation actor does NOT — that's a Target value or tag), **lifespan** (a sprint — earns a
  ledger only when paired with a *different discipline* like a cap/eviction, not a plain
  time-box), and **domain** (a different repo/subject). Plus the decision cascade (§3) and the two
  placement policies (§2.5).
- **The atomic `branch` command** (§8, `scripts/branch_create.py`). Creating a child does three
  things **together, or none** — scaffold the child header (axis, discipline, parent back-pointer,
  death condition if lifespan), write the parent's single pointer row (never a copy of child
  rows), and register the child. A failure on any one rolls the others back — no half-branched
  state. That structural atomicity makes the 2026-07-25 split-brain (a child the parent/registry
  lost track of) impossible. Guards refuse rather than half-create: a duplicate name, a lifespan
  child with no death condition, or an unconfirmed non-human actor.
- **Auto-suggest on a repeated pattern** (§6). `add`/`import` *offer* a branch — never branch
  unilaterally — only when the cascade lands on "new ledger" for ≥2 related items, naming the
  pattern seen. One item never triggers it. This is how an emerging track gets noticed instead of
  silently accumulating.

Backward compatible: `branch` writes v2 children and reads the registry; on a project with no
registry, register the parent first. The recall block still points at the canonical index; a
child is reachable via the parent's pointer row (the marker-delimited recall-block writer that
would add a per-child pointer line is Phase 6).

### v1.2.0 — deferral gate (2026-07-26) · format v2
Phase 4 of the v1.1 design build: the **deferral gate**, which fires at `/unforget add` — the
moment work is about to become a deferred row. It targets *deferral-laundering*: a row looks
identical whether it was deferred for a good reason or because deferring was frictionless and
self-flattering. The gate makes deferral cost something and leave an auditable record.

- **Trivial tripwire** (`reference/deferral-gate.md` §2). A would-be row that is Fix Effort =
  Trivial AND Blast Radius = ⚪ 1 file is redirected to **do it now** — scope doesn't gate it
  (out-of-scope trivial → do it and log a one-line report). A trivial-but-**destructive** change
  (deletion, force-push, prod deploy) is the exception: it routes to needs-approval, never
  auto-done. Trivial ≠ safe.
- **"Why not now?" allow-list** (§3). Everything that clears the tripwire must name one of four
  deferral reasons — `user-decision`, `scaffolding`, `scope`, `external-block` — recorded in the
  row as `Deferred because: <tag>` so a later reader (or `scan`/`verify`) can check whether it
  held up. No valid reason → do-now is the default, not a row.
- **Session defer/fix accounting** (§4, the load-bearing backstop). A per-session tally surfaces on
  `list` and at session end — `2 fixed inline · 7 deferred (reasons: …)`. A defer-heavy ratio
  (default ≥ 3× fixed) raises a gentle, **advisory-never-blocking** flag. The linguistic gate can
  be gamed per row; a ratio can't — this half is why the gate is honest, not decorative.
- **`scan` trivial-staleness cross-check** (§4d). A Trivial row that has survived ≥N sessions
  un-done is flagged as a near-certain "should've just done it" — how the pattern is learned over
  time, not just caught in the moment.
- New `scripts/defer_tally.py` (tripwire routing + tally math; writes the ephemeral, git-ignored
  `.unforget-session.json`) and `reference/deferral-gate.md`. Thresholds (`ratio_flag_threshold`,
  `stale_trivial_sessions`) and strictness (`policy_deferral`, default `aggressive`) are read from
  the registry. Backward compatible: the gate helps on a v1 ledger and never blocks the write path.

### v1.1.0 — status tokens, registry, verify lint (2026-07-26) · format v2
The first implemented slice of the v1.1 design (Phases 1–3 of the build plan). Introduces
**format `v2`** (the skill reads/writes both v1 and v2; v1 ledgers keep working untouched).
Every feature traces to a real failure seen while running the skill on a large, long-lived
ledger — not a hypothetical.

- **Structured status tokens** (`reference/status.md`, `scripts/parse_status.py`). A row's status
  is now a machine-readable `@status:` token (`open` / `in-progress` / `done-verified` /
  `done-unverified` / `blocked` / `withdrawn`) that tools read instead of parsing prose — so a row
  can no longer contradict itself. `done-unverified` is a first-class "done-but-owed" state.
- **Verification tier** (`@verified:` = `code` / `device` / `user` / `session-claimed`).
  `done-verified` requires `device` or `user` (or `code` with a note); **`session-claimed` can
  never back `done-verified`** — a claim is not a verification.
- **Registry** (`reference/registry.md`, `scripts/registry.py`). A re-read source of truth for
  where ledgers live and the persisted git-posture / policy settings, in a marker-delimited block
  in the ledger `README.md` (canonical) with an optional `.unforget.json` cache. If the two
  disagree, the README wins.
- **`verify` / doctor lint** (`reference/verify.md`, `scripts/verify_ledger.py`). A new read-only
  subcommand that catches contradictions, unproven/`session-claimed` "done", unknown status
  values, cell bloat, stale verify-still-open recipes, and registry drift. It **gates
  `archive`/`promote`**: an error-severity finding blocks a ship or relocation decision.

**Archive & release invariants:** `archive` now moves only a *clean* `done-verified` (valid tier,
no contradiction) or `withdrawn`, and holds `done-unverified`. A 🔴 THIS row counts as a release
blocker unless it is cleanly `done-verified` or `withdrawn`.

**Backward compatibility:** a v1 (tokenless) ledger produces no errors — the v2-only features
simply don't apply until the file is upgraded to v2. No big-bang reformat; rows gain tokens as
they're touched.

### The v1.1 design build is complete
All eight phases have shipped: status tokens (P1), registry (P2), verify lint (P3), deferral gate
(P4), branching (P5), onboarding/recall wiring (P6), row-length discipline (P7), and companion
skill handoffs (P8). The five `DESIGN-*.md` documents that specified this build are now fully
implemented. Future work is v1.2+ (see the deferred list in earlier design notes).

### v1.0.4 — docs (2026-07-26)
Documentation only, no behavior change: recorded the v1.1 design pass as a changelog entry and a
forward-looking README section. Patch bump so existing installs picked up the updated docs.

### v1.0.3 and earlier
Shipping skill: init / add / edit / import / list / scan / archive / promote / `--version`, the
10-column rating format, the format-version contract, and the `scripts/*.py` deterministic
helpers. This is the implemented baseline the v1.1 design builds on.

---

## License

Apache License 2.0. See LICENSE.
