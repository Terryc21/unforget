# unforget

![Status](https://img.shields.io/badge/status-v0.1%20spec--only-orange) ![License](https://img.shields.io/github/license/Terryc21/unforget) ![Last Commit](https://img.shields.io/github/last-commit/Terryc21/unforget) ![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet) ![Visitors](https://komarev.com/ghpvc/?username=Terryc21&repo=unforget&label=visitors&color=blue) ![GitHub stars](https://img.shields.io/github/stars/Terryc21/unforget?style=flat)

<a href="https://buymeacoffee.com/stuffolio">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>

> [!WARNING]
> **Beta. v0.1 is spec-only.** The seven-phase init flow, four-section structure, and 10-column rating table are fully specified in [SKILL.md](SKILL.md) and validated against two real projects (one complex, one minimal). The slash-command runtime handlers (`/unforget init`, `/unforget add`, etc.) **are not yet implemented**. They ship in v0.2.
>
> **What works today:** the UNFORGET.md file format itself. You can hand-create a file using the structure described below and use it manually. Several projects already do this.
>
> **What doesn't work yet:** typing `/unforget add "..."` will not currently fire any handler. Until v0.2, all interaction is manual file edits.
>
> **Beta testers wanted.** If you try the format on your own project (manual or AI-assisted edits), please [open an issue](https://github.com/Terryc21/unforget/issues) describing what worked, what felt wrong, or what was missing. Real-project feedback is what shapes v0.2's runtime implementation. Especially valuable: minimal repos, non-iOS projects, projects with non-CLAUDE.md AI instruction files (Warp, Cursor, Aider, Continue), and continuous-deployment workflows.

> A way of not losing sight or track of what is deferred.

A Claude Code skill that consolidates deferred work (paused plans, mid-task spillover, audit findings, and observed-but-not-yet-fixed bugs) into one structured file. Built so deferred items don't slip through the cracks between releases.

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
- **Surveys** existing deferral artifacts (Deferred.md / audit ledgers / plan files / code comments / GitHub issues / memory files) and offers to import them as rows
- **Invites you to capture** items the survey can't find: bugs in your head, friction you've felt, "I should fix that someday" thoughts
- **Captures** new deferrals in 30 seconds or less via `/unforget add`
- **Refines** rows via `/unforget edit` (upgrade auto-filled defaults to your real ratings)
- **Re-surveys** after init via `/unforget import` (catches new artifacts as they appear)
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

The signature column is **Target**, the release-cycle commitment:

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

`init` runs a seven-phase flow that takes 5 to 15 minutes the first time:

1. **Setup questions** (90 seconds or less): file path, cadence preset, whether to wire CLAUDE.md / AGENTS.md.
2. **Surface survey**: scans six tracking surfaces (Deferred.md / audit ledgers / plan files / code comments / GitHub issues / memory files) and produces a candidate list. Nothing imported yet.
3. **Triage**: for each surface, you decide: import all / one-by-one / skip.
4. **Auto-fill**: the skill maps source signals to the 10 columns with conservative defaults (you upgrade later via `/unforget edit`).
5. **User-add pass**: the skill asks: "What else? Bugs in your head, friction you've felt, items in Slack DMs, things you remember from past sessions?" You rattle off items, the skill captures each with conservative defaults. This phase typically catches 5 to 15 rows that no survey could find. Often the highest-value rows in the eventual file.
6. **Optional deep-dump**: 8 to 10 guided prompts for users who want a thorough adoption-time audit. Default skip; runnable later via `/unforget import --deep`.
7. **Diff preview, write, wire**: shows you exactly what's about to be imported, then writes UNFORGET.md, archives or redirects source files (never silent delete), and wires CLAUDE.md / AGENTS.md.

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

### Subcommand reference

| Command | What it does |
|---|---|
| `/unforget init` | Bootstrap UNFORGET.md, survey existing artifacts, capture user-known items |
| `/unforget add` | Capture a new deferral (default section: Session spillover) |
| `/unforget edit <ID>` | Refine a row's columns (Target, Urgency, etc.) |
| `/unforget import` | Re-run the surface survey after init (catches new artifacts) |
| `/unforget list` | Show current state, filterable by section / Target / Urgency / staleness |
| `/unforget scan` | Identify stale rows (read-only, never modifies the file) |
| `/unforget promote` | Release-time ritual (verify THIS rows fixed; promote NEXT to THIS) |

## Three preset modes

Different projects ship differently. `unforget init` offers three preset table shapes. Each is opinionated and complete; no column-picking needed:

| Preset | Audience | Target column |
|---|---|---|
| **Standard** | Mobile/desktop apps shipping discrete releases | 🚢 THIS / 🚢+1 NEXT / 🚢+2 LATER / 🌫️ SOMEDAY |
| **Lean** | Solo devs, side projects, junior devs | Same Target values, but only 6 columns total (Finding / Urgency / Effort / Status) |
| **Continuous** | Web apps, services, libraries with continuous deployment | Replaces Target with Window: 🟢 NOW / 🟡 THIS WEEK / 🔵 THIS MONTH / 🌫️ SOMEDAY |

Power users can append **extra columns** (Client, Sprint, Component, etc.) without modifying the core columns. Removing or renaming core columns is intentionally not supported, because it breaks comparability across projects.

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

`unforget` was extracted from a real iOS project (Stuffolio) where deferred work had fragmented across five tracking surfaces. Consolidation freed roughly 3 hours of release-prep time per cycle.

What's field-tested vs. what's spec at v0.1:

- **The 10-column table format.** Battle-tested in the source project against an actual App Store submission cycle. Rows, sections, Target column, promotion ritual all proven to work in practice.
- **The seven-phase init flow.** Designed from the source project's actual migration experience but specified for general use; not yet field-tested on a second project.
- **The slash-command implementations.** Currently spec-only. SKILL.md describes what each command does; the runtime handlers haven't been written yet. v0.2 closes that gap.

Use the file format today (it works as plain markdown). The slash-command surface lands in v0.2.

## Companion Skills

`unforget` came out of [Stuffolio](https://stuffolio.app)'s skill family. A set of Claude Code skills that grew from real shipping work and were extracted as standalone tools. Worth pairing with `unforget`:

| Skill | What it does |
|---|---|
| [**radar-suite**](https://github.com/Terryc21/radar-suite) | 8 audit skills that find bugs in Swift/SwiftUI apps before users do. Every finding cites a real file:line pattern in your codebase, not generic advice. Audit findings that aren't fixed immediately become rows in `unforget`'s Section 3 (Audit findings). |
| [**bug-prospector**](https://github.com/Terryc21/bug-prospector) | Mines for hidden bugs that pattern-based auditors miss. Behavioral and contextual issues regex can't catch. Outputs feed naturally into `unforget`'s Section 4 (User-reported / observed). |
| [**bug-echo**](https://github.com/Terryc21/bug-echo) | After you fix a bug, finds other instances of the same pattern across your codebase. The instances you don't fix immediately become `unforget` rows. |

All three follow the same opinionated-defaults design philosophy as `unforget` and integrate cleanly via the four-section structure.

## License

Apache License 2.0. See LICENSE.

## Contributing

This is an early-stage skill. If you try it and the format breaks down for your workflow, please open an issue describing the failure mode. That's the most useful feedback. Pull requests welcome for:

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
