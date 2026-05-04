# unforget — Format reference

This file holds the column definitions, enum values, detail-block contract, presets, and anti-patterns. Read it when writing or validating a row.

---

## The format

UNFORGET.md is a single markdown file with **4 sections**, each containing a **10-column rating table**.

### Sections

| Section | What goes here | ID prefix |
|---|---|---|
| **1. Paused plans** | Work started, made progress, paused mid-execution. Each row points at a detail file. | P |
| **2. Session spillover** | Items that surfaced mid-task in some other work. Captured in 1-2 lines. | S |
| **3. Audit findings** | Items surfaced by audit tools (linters, code review, custom audit skills) that weren't fixed immediately. | A |
| **4. User-reported / observed** | Bugs noticed but not reproduced, friction observed, "this feels off" notes. Lower bar than audit findings. | U |

### Columns (Standard preset, 10-col)

`# | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status`

| Column | Meaning |
|---|---|
| **#** | Stable ID (P1, S2, A3, U4). Never reuse. |
| **Target** | Release-cycle commitment (see "Target values" below) |
| **Finding** | One-clause description. Multi-line OK. |
| **Urgency** | 🔴 CRITICAL / 🟡 HIGH / 🟢 MEDIUM / ⚪ LOW |
| **Risk: Fix** | What could break making the change. ⚪ Low / 🟢 Medium / 🟡 High / 🔴 Critical |
| **Risk: No Fix** | Cost of leaving it (crash, data loss, user-visible bug). Same scale. |
| **ROI** | 🟠 Excellent / 🟢 Good / 🟡 Marginal / 🔴 Poor |
| **Blast Radius** | ⚪ 1 file / 🟢 2-5 files / 🟡 6-15 files / 🔴 >15 files |
| **Fix Effort** | Trivial / Small / Medium / Large |
| **Status** | Open / In Progress / Fixed / Deferred / Skipped |

### Target values

| Target | Meaning |
|---|---|
| 🔴 **THIS** | Must ship in current release cycle. Blocks submission. |
| 🔵 **NEXT** | First post-release point update. Triaged as fixable but not blocking. |
| 🟡 **LATER** | Two cycles out or more. Real work, not yet scheduled. |
| ⚪ **SOMEDAY** | No commitment. Captured so it doesn't get lost. May stay here forever. |

**Invariant:** `🔴 THIS` is the only Target that blocks shipping. At submission time, every `🔴 THIS` row must be Status = Fixed or have been demoted with a one-line reason.

### Detail blocks

Each section table is followed by a `### Detail - <section name>` subsection. Detail blocks hold the prose context that doesn't fit in the 10-column table (the why, the file paths, the linked plan refs, the resolution history). One detail bullet per ID; the bullet starts with the ID in bold (`- **P1** - ...`).

**Detail block format (three parts in order):**

1. **Closure pointer (only if the row is closed).** Lead the body with `**CLOSED YYYY-MM-DD: [one-sentence summary of how it closed].**` This pointer is what makes a closed row's outcome scannable; future readers see "what happened" without reading the full body. For Open rows, skip this part entirely.
2. **Body.** History, files, plan refs, context, gotchas. Free-form prose. Length is whatever the row needs; some rows are one sentence, some are five paragraphs. The Finding cell in the table is the headline; the body is the article.
3. **Spawn links (only if the row is part of a chain).** `Spawned-from: <ID>` if this row was created by closing another row (e.g., a workaround that spawned a real-fix follow-up). `Spawns: <ID>` if closing this row created a follow-up row. Both directions are recorded so the chain can be walked from either end.

**Example (closed row with a spawned follow-up):**

```
- **P3** - **CLOSED 2026-04-20: hidden the menu entry until server signing lands. Spawns: P6.** Every item that showed the Wallet feature failed when the user completed the flow. Blocked on server `/api/wallet/sign-pass` + Apple Pass Type ID. Pre-submission decision: complete the worker endpoint OR hide the menu item (~30 min if hiding). Chose hiding for build 13; future endpoint work tracked at row P6.
```

**Example (open row with no spawn link):**

```
- **P4** - Search relevance overhaul. Phases 1-4 (term weighting, stop words, fuzzy match, synonym expansion) shipped in build 11. Phases 5-7 (personalization, click-through learning, query rewriting) require a Cloudflare D1 schema we don't have yet. Plan: `~/.claude/plans/search-overhaul.md`.
```

The format is intentionally simple: closure pointer, body, spawn links. The skill's `add` / `edit` / `promote` flows preserve this structure when they touch a detail block. Hand-editing a detail block is fine as long as the three parts stay in order and the closure pointer (if present) stays at the top.

### Presets

`unforget init` offers three presets at setup. Each is opinionated and complete; users pick the closest fit, and the skill adapts the table format accordingly.

| Preset | Audience | Columns |
|---|---|---|
| **Standard** | Mobile/desktop apps shipping discrete releases | All 10 columns above with Target |
| **Compact** | Projects that prefer a narrower table; same release-cycle semantics as Standard | 9 columns. Drops the dedicated Target column and inlines Target as a leading badge inside the Finding cell (e.g., `**🔴 THIS · Apple Wallet pass broken promise**`). All other columns identical to Standard. |
| **Lean** | Solo devs, side projects, junior devs | 6 columns: # / Target / Finding / Urgency / Effort / Status |
| **Continuous** | Web apps, services, libraries with continuous deployment | 9 columns; replaces Target with Window (🟢 NOW / 🟡 THIS WEEK / 🔵 THIS MONTH / ⚪ SOMEDAY) |

Users on Standard, Compact, or Lean can also append **extra columns** (Client, Sprint, Component, etc.) without modifying core columns. Removing or renaming core columns is intentionally not supported, because it breaks comparability across projects and tooling.

### Compact preset detail

Compact preserves Standard's release-cycle semantics; only the rendering changes. Conversion is mechanical:

- Standard cell: `🔴 THIS` in column 2, `Apple Wallet pass broken promise` in column 3.
- Compact cell: column 2 is dropped; column 3 (Finding) becomes `**🔴 THIS · Apple Wallet pass broken promise**`.

The leading `**🔴 THIS · ...**` form is the contract: a literal Target badge (one of `🔴 THIS` / `🔵 NEXT` / `🟡 LATER` / `⚪ SOMEDAY`), the literal middle dot ` · ` separator, and the original Finding text. Bold the whole prefix-plus-Finding so the badge stays visually anchored.

**Why Compact exists.** A 10-column rating table can wrap or render as vertical blocks in narrow terminals. Compact saves one column without losing the Target signal: `grep '🔴 THIS'` still finds ship-blockers, the Finding cell gets more room before hitting its character limit, and tooling that reads the file can still parse Target via a simple regex on the leading badge.

**When to pick Compact at init.** Compact is offered alongside Standard / Lean / Continuous in Phase 1's preset prompt for projects that report narrow terminals or that already use the inlined-badge convention informally. Conversion between Standard and Compact is lossless and can be done at any time by `/unforget edit` or a future `/unforget migrate` flow.

**Tooling expectations.** Read operations (`list`, `scan`, `promote --dry-run`) detect the preset from the column count and section headers and adapt parsing accordingly. Write operations (`add`, `edit`, `import`, `promote`) preserve the preset that's already in use; the skill never auto-converts a Compact file to Standard or vice versa.

---

## Anti-patterns

Things this skill deliberately does NOT do, and why:

- **Custom column reordering.** Breaks comparability across projects.
- **Custom rating scales.** Letting one user use 🔴/🟡/🟢/⚪ and another use P0/P1/P2/P3 makes the format un-shareable.
- **Per-row column visibility.** Hiding columns on some rows but not others. Devolves into chaos.
- **Renaming core columns.** "Call Urgency 'Priority' instead." Skill becomes incompatible with itself.
- **Multiple files.** UNFORGET.md is the index. Detail files (per-plan markdown) are linked FROM rows, not duplicates of them.
- **Auto-deferring things the AI thinks should be deferred.** Deferral is a user decision. The skill captures, organizes, and surfaces; it doesn't decide on the user's behalf.
