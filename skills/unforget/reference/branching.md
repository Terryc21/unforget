# The branching model and the `branch` command

> Authoritative spec for when deferred work earns a NEW ledger vs. a row/section,
> and how a child ledger is created without split-brain (format v2+, from the
> Branching Model design). Grounded in three real ledgers already in use:
> `UNFORGET.md` (main), `TERRY-UNFORGET.md` (by-actor), `MI-UNFORGET.md`
> (by-lifespan).

## The core principle: default to NOT branching

Most deferred work is a **row** in the existing ledger with a `Target` value
(THIS/NEXT/LATER/SOMEDAY) or, at most, a new **section**. A new ledger is a heavier
commitment — its own home, its own recall, its own reconciliation — and it
introduces **split-brain risk** (a child ledger the parent/registry lose track of;
the exact failure that stranded TERRY/MI in a parallel tree until 2026-07-25).
Over-branching produces N ledgers nobody reconciles.

**A new ledger is justified ONLY when the work differs on one of three axes.** If
it differs only in *subject* but shares actor, lifespan, and working directory, it
is a section or a Target value — not a ledger.

## §2 — The three legitimate axes

A new ledger is warranted when the work differs from the parent on **≥1** axis:

| Axis | Test question | Real example | Earns a file? |
|---|---|---|---|
| **actor** | *Which **human** acts on this?* | `TERRY-UNFORGET` — only the user can do App Store Connect, Cloudflare, marketing calls. | Yes, even at identical discipline — "what can *I* act on now?" is a real query worth keeping clean. |
| **lifespan** | *Built-in end date AND a different discipline?* | `MI-UNFORGET` — a sprint; dies at Phase 6, cap 15, evict-on-done. | Only with a **different discipline** (cap / eviction / column shape). |
| **domain / working dir** | *A different repo, project, or subject entirely?* | book vs. Stuffolio vs. citation-ledger. | Yes — its own everything. |

Two corrections that keep the model honest:

- **Actor is humans only.** A different *human* reader justifies a file. A
  **machine/automation actor** (CI bot, scheduled agent) does NOT — that's
  over-branching into thin files nobody reads. Machine-actor work is a **Target
  value or a status tag** inside the actionable ledger.
- **Lifespan alone is not enough.** A plain time-box (a 2-week polish push using the
  SAME mark-then-archive discipline as the parent) is a **section with an end-date
  note**, not a child. Lifespan earns a ledger only when paired with a different
  discipline. The decisive sub-test: *does the sub-track use a DIFFERENT eviction
  discipline than its parent?* MI **evicts** done rows to a changelog (a cap forces
  closure); the main ledger **marks-then-archives**. Same discipline → section;
  different → child.

## §2.5 — The skill captures POLICY, it does not adjudicate

The governing stance: **the skill does not make judgment calls on the user's
behalf. It captures the user's POLICY once (at init / start-of-run), applies it
silently thereafter, and allows a per-row override.** A user-set policy is the
user's stated intent, not the AI's interpretation — which is harder for the AI to
rationalize around (directly relevant to deferral-laundering: a placement policy
the user set is firmer than a rule the AI reads and bends toward least resistance).

Two policies, recorded in the registry (§5) so they persist:

**Policy 1 — deferral aggressiveness** (`policy_deferral`). Controls the cascade's
"trivial" exit; full mechanics in `reference/deferral-gate.md`. Default
`aggressive` (trivial → do-now regardless of scope).

**Policy 2 — multi-axis placement tiebreak** (`policy_multiaxis`). When a row
qualifies for MORE THAN ONE ledger (e.g. user-only **and** sprint-scoped), the
policy picks the default owner, applied silently, **overridable per row**:

| `policy_multiaxis` | Default owner |
|---|---|
| **lifespan-wins** (recommended default) | the nearest-death container (the sprint ledger) owns it; it dies and takes the row with it. |
| **actor-wins** | user-only work always lives in TERRY so "what can I do now?" stays complete; the other ledger keeps a pointer. |
| **nearest-death-owns** | general form — the container with the closest end-condition owns multi-axis rows. |

Whatever the default, a specific multi-axis row may be placed in the other ledger,
leaving a **pointer** in the one the default would have chosen.

## §3 — The decision cascade (walk in order; first "no-branch" answer wins)

You only reach "new ledger" if all earlier redirects fail.

```
Is this a TRIVIAL fix?                       → APPLY POLICY 1 (deferral-gate).
                                               Default: DO IT NOW regardless of
                                               scope; report per scope. No row
                                               unless policy says defer.
        │ not trivial (or policy says defer)
Same actor, lifespan, and working dir?       → ROW in current ledger (pick a Target).
        │ differs on ≥1 axis
Differs only in SUBJECT, shares
actor + lifespan + working dir?              → SECTION in current ledger (new ## heading).
        │ differs on actor / lifespan / dir
Qualifies for MORE THAN ONE ledger?          → APPLY POLICY 2 for the default owner
                                               (per-row override allowed); then
                                               continue below for the CHOSEN axis.
        │ single axis (or resolved by Policy 2)
Actor axis (a different HUMAN acts on it)?   → SEPARATE FILE even at identical
                                               discipline (that's TERRY-UNFORGET).
                                               → branch --axis=actor.
                                               [machine actor → Target/tag, NOT a file]
        │ not a human-actor split
Lifespan AND a different discipline?         → NEW child ledger. → branch --axis=lifespan.
        │ lifespan but SAME discipline
                                             → SECTION with an end-date note (NOT a ledger).
        │ domain / different working dir
                                             → NEW independent ledger. → branch --axis=domain.
```

The hard exits, plainly:
- **Trivial → Policy 1 decides** (recommended: do-now regardless of scope; scope
  only changes reporting). Triviality, not scope, is what stops a thing becoming a row.
- **Multi-axis → Policy 2 decides** the default owner (recommended: lifespan wins),
  always per-row overridable. Axes **compose** — they are not mutually exclusive.
- **Actor → separate file even at identical discipline.**
- **Lifespan → ledger ONLY with a different discipline**; a plain time-box is a section.

## §4 — Parent ↔ child relationship (the anti-fragmentation glue)

When a child IS created, three conventions keep branching from becoming split-brain:

### §4a — The parent keeps a POINTER ROW, never a copy

The main ledger gets exactly **one row** pointing at the child, and never
duplicates the child's rows. **An item lives in exactly ONE ledger; the pointer is
a signpost, not a shadow copy.** Copies drift and reintroduce split-brain.

Pointer-row shape (fits the main 10-col format; only Finding + Status carry content;
unused columns take `—` filler):

```
| U18 | 🌫️ SOMEDAY | → child ledger `MI-UNFORGET.md` (multi-inventory sprint). This row is a POINTER; the live rows live there. Do not track sprint work here. | — | — | — | — | — | — | → see MI-UNFORGET.md |
```

### §4b — The child declares its axis + discipline IN ITS OWN HEADER

Every child opens with a "read before adding a row" header stating:
1. **which axis** made it a child (actor / lifespan / domain);
2. **its discipline** — column shape, cap, eviction rule, end-of-life plan;
3. **its parent** — a back-pointer to the ledger that owns its pointer row.

### §4c — Lifespan children declare their DEATH condition

A by-lifespan child (a sprint) must state *when it is archived or deleted*, so it
can't outlive its purpose and silently become a second permanent backlog (MI: "When
Phase 6 ships, this whole file is archived or deleted"). **`branch --axis=lifespan`
refuses without a death condition.**

## §5 — The registry (so the skill never loses a ledger again)

`branch` registers the child in the registry (see `reference/registry.md`), which
records per ledger: **name · path · role · axis · discipline · parent · death.**
`scan`/`import` gain the drift check: *a ledger named in the registry but not found
on disk* → flag, don't silently proceed. That single check turns a 20-minute "are
they lost?" hunt into a one-line "registered at `<path>` — not found; moved?"

## §6 — Auto-suggest: offer only on a REPEATED PATTERN (design §8-#3)

The skill stays quiet until the §3 cascade lands on "new ledger" for **≥2 related
items** — a pattern, not a one-off. Then it **offers** to branch (it never branches
unilaterally). Rationale: answer-only misses emerging tracks (the 2026-07-25 failure
— TERRY/MI existed but no session noticed); suggest-on-every-item nags and
over-branches. Two related items is the middle path.

- **"related"** = same actor, same lifespan-scope, or same subject cluster across the
  recent adds.
- When it offers, the skill **names the pattern it saw**: *"3 App-Store-Connect rows
  this session — split into a user-action ledger?"* — not a generic "want to branch?"
- One item does **not** trigger a suggestion. Wired into `add`/`import` (see
  `reference/commands.md`).

## §7 — Anti-patterns (what NOT to do)

- **A ledger per feature / chapter / sub-task.** A book *chapter* is a section; a
  different *book* is a ledger. A sub-feature is a Target value.
- **A child that shares the parent's discipline** (same columns, same
  mark-then-archive). That's a section wearing a filename — unless it's the actor axis.
- **Copying rows into the parent "for visibility."** One pointer row, not a shadow copy.
- **A lifespan child with no death condition.** A sprint that doesn't say when it dies
  becomes a second permanent backlog.
- **Branching to avoid reconciling.** Opening a fresh ledger because the current one
  is messy is avoidance, not organization (cousin of deferral-laundering).

## §8 — The `branch` command (atomic child creation, design §8-#4)

Creating a child ledger does its artifacts **together, or none** — because those
drifting apart IS the split-brain failure. Manual steps or overloading `init`/`add`
reintroduce the miss-one-step risk.

### Usage

```
/unforget branch <name> --axis=<actor|lifespan|domain> [--parent=<ledger>] \
    [--discipline="<one line>"] [--death="<condition>"] [--target=SOMEDAY] [--dry-run]
```

### The atomic artifacts (three, or four with a maintained recall block)

1. **Scaffold the child's header** (§4b) — axis, discipline, parent back-pointer,
   and (lifespan only) the death condition. The child is written with its own
   `<!-- unforget-format: v2 -->` marker and empty section tables ready for rows.
2. **Write the parent's pointer row** (§4a) — exactly one row in the parent, in the
   pointer shape, with `→ see <child>` in the Status cell. Never a copy of child rows.
3. **Register the child** (§5) — a registry entry (name, path, role, axis,
   discipline, parent, death) via `scripts/registry.py`, so `list`/`scan`/`import`
   re-read where it lives.
4. **Update the maintained recall block** (onboarding §4) — *only when the registry
   declares `recall_block: maintained` + a `recall_file`*: rebuild the Deferred Work
   Index from the just-updated registry so the child appears immediately. Skipped for
   `manual`/`none` or registry-less projects.

**Atomicity:** all present artifacts, or none. The helper builds every artifact's
content and checks every guard *before* any write; a failure on any one rolls the
others back (child deleted, parent/registry/recall restored to their prior bytes) —
no half-branched state. `--dry-run` reports the artifacts it *would* write and touches
nothing.

### Guards (refuse rather than half-create)

- **Name already registered** → refuse ("`<name>` is already a registered ledger at
  `<path>`"). No duplicate ledgers.
- **`--axis=lifespan` with no `--death`** → refuse and **prompt** for the death
  condition. A lifespan child MUST declare when it dies (§4c).
- **`--axis=actor`** → confirm it is a **HUMAN** actor. A machine/automation actor
  is redirected to a Target value or status tag inside the actionable ledger, NOT a
  new file (§2). The script surfaces this as a `needs_confirmation` flag; the LLM
  asks before proceeding.
- **`--axis=<x>` with the same discipline as the parent** (lifespan/domain) → warn:
  a same-discipline split is usually a section, not a ledger (§7). Actor axis is
  exempt (it earns a file at identical discipline).

### The recall block

When the registry declares a **maintained** recall block (`recall_block: maintained`
+ a `recall_file`), `branch` updates it as a **fourth atomic artifact** — it rebuilds
the marker-delimited Deferred Work Index (`scripts/recall_block.py`) from the
just-updated registry so the new child appears immediately, and rolls it back with the
other three on any write failure. When there is **no** maintained recall block (a
`manual`/`none` project, or no registry yet), `branch` skips it — the child stays
reachable through the parent's pointer row, which points at the canonical index. This
keeps `branch` atomic whether or not a maintained recall block is configured.

### After creating

Report all three (or four) artifact paths and a one-line next step: *"Child
`<name>` created at `<path>`, pointer U-NN in `<parent>`, registered. Add rows with
`/unforget add --ledger=<name>`."*

## Preferred implementation

The **axis decision** (which axis, is it a human actor, would it balloon) is LLM
judgment following the §3 cascade — not a script. The **atomic write** is
deterministic and delegates to the helper:

```
python3 scripts/branch_create.py --dir <ledger-dir> --name <name> \
    --axis <actor|lifespan|domain> --parent <parent-file> \
    [--discipline "<one line>"] [--death "<condition>"] \
    [--target SOMEDAY] [--parent-id U18] [--recall-home "<display path>"] [--dry-run]
```

It returns `{ok, dry_run, child_path, parent_path, pointer_id, registered,
recall_updated, needs_confirmation, refusal, artifacts, advisory}`. On a guard failure
it returns `ok:false` with a `refusal` string and writes nothing. On success
(non-dry-run) it has written all present artifacts atomically (three, or four when a
maintained recall block is configured — `recall_updated:true`). Registry and recall
read/write reuse `scripts/registry.py` and `scripts/recall_block.py`.

**Algorithm fallback** (Python unavailable): (1) create `<child>.md` with a
`<!-- unforget-format: v2 -->` marker and a header naming the axis, discipline,
parent back-pointer, and — if lifespan — the death condition, plus empty section
tables; (2) append one pointer row to the parent (pointer shape, `→ see <child>` in
Status), reusing the next `U-NN` id; (3) add a registry row (name/path/role/axis/
discipline/parent/death) to the ledger `README.md` block; (4) if a maintained recall
block exists, add a bullet for the child to it. Do all present steps or roll back by
hand. Refuse if the name is already registered, if a lifespan branch has no death
condition, or (for actor) if the actor is not a human.
