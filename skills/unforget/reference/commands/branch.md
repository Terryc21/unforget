# /unforget branch

Part of the unforget command reference; the index is [../commands.md](../commands.md).

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

`branch` is a format-v2 command. It writes v2 children. It reads the registry (a v2 feature); on a project with no registry block, register the existing parent first via `import` so the child has a home and the parent can carry its pointer.
