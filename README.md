# unforget

> A way of not losing sight or track of what is deferred.

A Claude Code skill that consolidates deferred work — paused plans, mid-task spillover, audit findings, and observed-but-not-yet-fixed bugs — into one structured file. Built so deferred items don't slip through the cracks between releases.

## The problem

Every developer defers things. The problem isn't the deferral. It's that deferred items end up scattered across:

- a `Deferred.md` at the repo root
- date-prefixed plan files in some "deferred" folder
- audit-tool ledgers (linters, code review tools, custom audit skills)
- Slack DMs to yourself
- comments in code (`// TODO: come back to this`)
- memory files for AI assistants
- paused plan files in `~/.claude/plans/`

Months later, when you ask "what's deferred?", the answer requires walking five surfaces. Items go stale. Some get fixed by accident. Some sit forever because nobody remembered them.

`unforget` collapses all deferral into ONE file, structured so you can scan, prioritize, and ship at a glance.

## What it does

- **Initializes** `UNFORGET.md` in your project (default path: `Documentation/Development/Deferred/UNFORGET.md`)
- **Captures** new deferrals in ≤30 seconds via `/unforget add`
- **Surfaces** stale items via `/unforget scan` (rows aging past their priority threshold)
- **Promotes** items toward shipping at each release via `/unforget promote`
- **Wires** itself into your project's CLAUDE.md / AGENTS.md so future AI sessions automatically read it when you ask "what's deferred?"

## The format

UNFORGET.md is one markdown file with **four sections**, each a **10-column rating table**:

| Section | What goes here | ID prefix |
|---|---|---|
| **Paused plans** | Work started, paused mid-execution. Each row links to a detail file. | P |
| **Session spillover** | Items surfaced mid-task in some other work. | S |
| **Audit findings** | Items from audit tools (linters, code review, audit skills) not fixed immediately. | A |
| **User-reported / observed** | Bugs noticed but not reproduced, friction observed. | U |

Each row gets rated across ten axes:

`# | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status`

The signature column is **Target** — the release-cycle commitment:

| Target | Meaning |
|---|---|
| 🚢 **THIS** | Must ship in current release cycle. Blocks submission. |
| 🚢+1 **NEXT** | First post-release point update. |
| 🚢+2 **LATER** | Two cycles out or more. |
| 🌫️ **SOMEDAY** | No commitment. Captured so it doesn't get lost. |

**Invariant:** 🚢 THIS is the only Target that blocks shipping. Everything else is post-release by definition. When you ship, NEXT auto-promotes to THIS, LATER promotes to NEXT, and you re-triage SOMEDAY.

## Why a Target column

Most backlog tools collapse "how bad is this?" and "when does it ship?" into a single Priority field. They're different questions:

- A 🟡 HIGH urgency item might still be deferred to the next update because the current release is days from submission.
- A 🟢 MEDIUM urgency item might jump to "this release" because it's a one-line fix you stumbled into.
- A ⚪ LOW item might sit in a release bucket for three cycles, then suddenly become 🚢 THIS because user feedback changed its weight.

Keeping Urgency and Target as separate columns lets either dimension shift without rewriting the other. Sort by Target column for ship-readiness; sort by Urgency × ROI for prioritization. Same data, different question.

## Quick start

```
# In any Claude Code session inside your project
/unforget init
```

You'll be asked:

1. **Where should UNFORGET.md live?** (default: `Documentation/Development/Deferred/UNFORGET.md`)
2. **How does this project ship?** (Discrete releases / Continuous deployment / Solo / Custom)
3. **Should I wire this into your CLAUDE.md / AGENTS.md?** (recommended: yes)

The skill creates the file, scaffolds the four sections, and adds a "Deferred Work Index" block to your AI instructions file so future sessions automatically read UNFORGET.md when you ask about deferred work.

Then, anywhere in any session:

```
/unforget add "API rate limiter sometimes returns 429 even when under quota"
```

The skill assigns the next ID, defaults Target to 🌫️ SOMEDAY (you can promote later), and appends the row to Section 2 (Session spillover). 30 seconds end-to-end.

When you're ready to ship:

```
/unforget list --target=THIS
```

You see exactly which rows block submission. Fix them, mark them Fixed, run `/unforget promote`, and ship.

## Three preset modes

Different projects ship differently. `unforget init` offers three preset table shapes — each opinionated and complete, no column-picking needed:

| Preset | Audience | Target column |
|---|---|---|
| **Standard** | Mobile/desktop apps shipping discrete releases | 🚢 THIS / 🚢+1 NEXT / 🚢+2 LATER / 🌫️ SOMEDAY |
| **Lean** | Solo devs, side projects, junior devs | Same Target values, but only 6 columns total (Finding / Urgency / Effort / Status) |
| **Continuous** | Web apps, services, libraries with continuous deployment | Replaces Target with Window: 🟢 NOW / 🟡 THIS WEEK / 🔵 THIS MONTH / 🌫️ SOMEDAY |

Power users can append **extra columns** (Client, Sprint, Component, etc.) without modifying the core columns. Removing or renaming core columns is intentionally not supported — it breaks comparability across projects.

## Why this isn't "just another todo system"

There are 50 task trackers. The differentiators here:

1. **It's a pattern, not an app.** UNFORGET.md is plain markdown. Renders fine on GitHub, in any editor, in Linear's markdown view. No vendor lock-in.
2. **The Target column with promotion ritual.** Most tools have a priority field. None have a release-cycle column with a defined promotion ceremony.
3. **Mandatory recall trigger via CLAUDE.md / AGENTS.md.** Future AI sessions automatically read your UNFORGET.md when you ask "what's deferred." No remembering to mention it.
4. **Built-in staleness detection.** Most tools accumulate forever. `unforget scan` flags items that have aged past their priority's threshold so you can re-triage before users feel the impact.
5. **30-second capture.** If logging an item ever takes longer than 30 seconds, the skill has failed at its core promise.

## How it integrates with other skills

- **Audit tools (radar-suite, custom audit skills, ESLint, etc.):** Findings that aren't fixed immediately become rows in Section 3 (Audit findings) with the originating tool/finding ID preserved.
- **Plan tools (Claude Code `/plan`, `/loop`, manual plan files):** A paused plan becomes a row in Section 1 (Paused plans) with a pointer to the plan file. The plan file remains the detail; UNFORGET.md is the index.
- **Schedule (`/schedule`):** Schedule `/unforget scan` to run weekly or biweekly. Output is structured markdown, suitable for posting to Slack, email, or a GitHub Issue.
- **Memory entries:** Use memory for context that survives across sessions (the "why" behind a decision). Use UNFORGET.md for tracking (the "what" and "when"). Don't duplicate.

## Compatibility

- **Claude Code:** Native skill. Slash commands work as documented.
- **Other AI assistants:** The Deferred Work Index pattern in CLAUDE.md / AGENTS.md works for any AI that reads project instructions (Cursor, Copilot, Aider, etc.).
- **No AI:** UNFORGET.md is just markdown. Edit by hand if you prefer. The format is the value, not the tooling.
- **Teams:** Commits to git like any other markdown. Concurrent edits resolve via standard merge.

## Origin

`unforget` was extracted from a real iOS project (Stuffolio) where deferred work had fragmented across five tracking surfaces and the consolidation freed ~3 hours of release-prep time per cycle. The 10-column table format and Target/promotion ritual are battle-tested against an actual App Store submission cycle.

## License

MIT. See LICENSE.

## Contributing

This is an early-stage skill. If you try it and the format breaks down for your workflow, please open an issue describing the failure mode — that's the most useful feedback. Pull requests welcome for:

- Additional preset modes (e.g., academic / research / open-source-maintainer)
- Improved scan heuristics
- Better integration with specific other skills or tools
- Clearer error messages for malformed UNFORGET.md files

Things this skill will NOT accept (see Anti-patterns in SKILL.md):

- Per-row column visibility
- Custom column reordering of core columns
- Renaming core columns
- Multiple-file UNFORGET.md splits

The opinionation is the value.
