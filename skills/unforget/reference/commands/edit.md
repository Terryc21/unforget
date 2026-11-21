# /unforget edit

Part of the unforget command reference; the index is [../commands.md](../commands.md).

---

## /unforget edit

Refine a row's columns after import. Most useful immediately after `/unforget init` to upgrade auto-filled defaults.

### Usage

```
/unforget edit P3                       ·  open row P3 for editing
/unforget edit P3 --target=THIS          ·  change just the Target cell
/unforget edit P3 --status=done          ·  mark done (see status-token rule below)
/unforget edit S5 --urgency=HIGH --roi=Excellent
```

### Steps

1. Find the row by ID. Show its current 10 columns.
2. Prompt for which cells to update (or accept flag overrides if passed inline).
3. Show the diff (old value to new value for each changed cell).
4. Apply the change to UNFORGET.md.

**Change only the requested cells.** A Target-only or rating-only edit preserves
the Status cell byte-for-byte, including a legacy word-status in a v2 ledger.
Do not add status/verification tokens or migrate the row opportunistically.
Write status tokens when Status itself changes, or when the user explicitly
requests a format migration; the verification-evidence rules still apply.

### Status-token rule (format v2+)

When changing status, write the `@status:` token (see `reference/format.md` §
Status tokens and `reference/status.md`), not a bare word. Specifically for
marking something done:

- `--status=done` **requires a verification tier.** Ask (or infer from context)
  how it was checked and write `@verified:<tier>`.
- If the only backing is a session's own claim (no independent check), the
  result is **`@status:done-unverified` `@verified:session-claimed`**, NOT
  `done-verified`. A claim is not a verification. `done-verified` requires
  `device` or `user` (or `code` with an explicit code-is-sufficient note).
- Record provenance in the narration (who/what/when), e.g.
  `` `@status:done-verified` `@verified:device` · TF77 · 2026-07-25 ``.
- After writing, validate with `python3 scripts/parse_status.py --row "<row>"`;
  if it reports `tier_valid:false` or `contradiction:true`, fix before saving.

`/unforget edit` is the everyday command for keeping rows accurate. Pair with `/unforget list --age=30+` to find rows that need review.

### Budget check at write time (not just at scan/verify)

**Why this exists.** Char-budget overflow (`reference/verify.md` § Char-budget severity
escalation) is created one status change at a time — a row that appends a "still owed" /
"RESOLVED" / "prior arc" line at every edit instead of migrating older narration to the
detail block. Catching this only reactively, at the next `scan` or `verify`, means the row
has already crossed the hard threshold before anyone is told. `edit` is the moment the bloat
is actually written, so it's the cheaper place to catch it.

After applying any `--status=` change (step 4 above), run the same check `scan`/`verify` use
(`python3 scripts/row_budget.py check --file <path> --id <ID>`, or the char-count fallback) on
the cell just written. If the edit pushed the Status or Finding cell **past the soft budget**
(400 chars), offer the split inline rather than waiting for the user to hit it on a later
`scan`:

> "This status update pushes the row to 512 chars (budget: 400). Split into a bounded index +
> detail block now? (`/unforget verify --fix` would offer this later anyway.)"

**Advisory, never blocking.** This is a same-shape offer to the companion-skill handoff above:
surfaced once, easy to decline, never refused by `edit` itself. `edit`'s job is applying the
requested change; the split offer is a courtesy that catches the common case (one more status
line pushes an already-long row over) before it becomes a `verify`-blocking error later. If
the user declines, the change still applies — declining only means the row stays flagged at
the next `scan`/`verify`.

**Skip the offer** when the edit is not a status change (e.g. `--target=` or `--urgency=`
alone touch neither prose cell) or when the cell was already over budget before this edit (it
already surfaced at the last touch; don't re-nag on every subsequent edit to the same
over-budget row — one offer per edit that CROSSES the threshold, not one per edit to a row
already past it).

### Closure handoff (when marking a row done — format v2+)

When `/unforget edit <ID> --status=done` closes a row, unforget MAY offer a **companion-skill handoff** — a function-based recommendation fired at this earned transition. The full mechanic (the five functions, the global manifest, install-state detection, governance) is `reference/skill-handoffs.md`; this is the operational summary. It **supersedes** the older inline `/radar-suite` + `/bug-echo` prose: those hardcoded two URLs at the trigger and detected installs by *directory name* — both are the anti-patterns the handoff design fixes (one manifest, invocable-name detection).

**Which function fires:**
- closing a **code fix** (non-trivial closure) → `post-fix-sibling-scan` (default: bug-echo — generalize the fix, find its siblings).
- closing an **audit-finding** row → `audit-reverify` (default: radar-suite — confirm it held).

**How to express it** — resolve the function against what the session reports invocable, and say the resolver's `expression` verbatim:

```
python3 scripts/companions.py resolve --function post-fix-sibling-scan \
    --invocable "<the session's invocable skill names, comma-separated>"
```

The `--invocable` list is the AUTHORITATIVE install signal (the one-star-risk lesson: detect by invocable name, NEVER a dir find). The resolver returns one of three states: **installed** → "Run `/bug-echo` — …" (no URL); **not-installed** → one soft pointer with the manifest URL; **unset** → "no skill mapped … consider mapping one" (no URL invented). Surface exactly one line.

**Governance (the restraint — `reference/skill-handoffs.md` §5):**
- **At most once per function per session.** Ten code-fix closures offer the scan once, batched ("3 code-fixes closed — run `post-fix-sibling-scan`?"). Track which functions already fired this session.
- **A TRIVIAL close fires NOTHING.** A one-line typo / single-character / isolated-state fix gets no handoff. Only a closure that touched architecture, types, or a shared pattern earns one.
- **Suppress entirely when:** the status change was Open→Skipped/Deferred (not actually fixed), a no-op (done→done), the closure narrative is too short (< ~50 chars) to suggest a pattern, or the row is a non-code observation (a process/skill note).
- **Advisory, never blocking, never a defer.** The handoff means "do the scan NOW, while context is hot." "I'll run bug-echo later" logged as a row is deferral-laundering — the handoff's whole point is do-it-now.

The recommendation is informational; the user can ignore it and move on.
