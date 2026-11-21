# /unforget verify

Part of the unforget command reference; the index is [../commands.md](../commands.md).

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
5. No separate backup step: `row_budget.py split --apply` backs the ledger up before each split (`reference/promotion.md` § Backups and recovery).

`--fix` is strictly additive: without it, `verify` is read-only exactly as before. It exists only because a row-length split is mechanical and lossless-verifiable — the one integrity finding safe to auto-resolve with approval. See `reference/format.md` § Row-length discipline.

### Gate role

`verify` also runs automatically **before `archive` and `promote`**. An error-severity finding (a contradiction, an unproven/`session-claimed` "done", an unknown status value, or a THIS row that claims done but isn't cleanly `done-verified`) **blocks** the ship/relocation decision until resolved — the same discipline as `promote`'s existing 🔴 THIS check. Warnings never block. See `reference/promotion.md` and `/unforget archive` steps.

### Backward compatibility

On a v1 (tokenless) ledger, `verify` emits only warnings (bloat, stale-recipe, open THIS rows) and no errors, so the gate passes. A legacy ledger is never blocked by the token checks.
