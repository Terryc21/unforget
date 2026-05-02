# unforget

![Status](https://img.shields.io/badge/status-v0.1%20beta-yellow) ![License](https://img.shields.io/github/license/Terryc21/unforget) ![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)

> [!NOTE]
> **Beta, v0.1.** The skill works today. Install it once (instructions below), then run `/skill unforget init` in any project session. Claude reads the skill file and walks you through setup.
>
> v0.2 will ship as a Claude Code plugin so you can install with one command and drop the `/skill` prefix when invoking it. Same features, smoother install.
>
> If you'd rather not use Claude at all, UNFORGET.md is plain markdown. You can edit it by hand in any text editor.

> A way of not losing sight or track of what is deferred.

A Claude Code skill that consolidates deferred work (paused plans, mid-task spillover, audit findings, and observed-but-not-yet-fixed bugs) into one structured file. Built so deferred items don't slip through the cracks between releases.

If unforget saves you a release-prep cycle, a [coffee](https://buymeacoffee.com/stuffolio) is appreciated. Issue reports about what worked or didn't are even more useful at v0.1.

<a href="https://buymeacoffee.com/stuffolio">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>

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

- **Creates `UNFORGET.md`** in your project (the default location is `Documentation/Development/Deferred/UNFORGET.md`, but you choose during setup).
- **Looks at where deferred work is already living** in your project (a `Deferred.md` at the root, audit reports, plan files, `// TODO` comments, GitHub issues, AI memory files) and offers to pull them in as rows.
- **Asks you what's on your mind** that the scan couldn't find: bugs you noticed but didn't write down, friction you've felt, "I should fix that someday" thoughts. This usually catches the most valuable rows.
- **Lets you capture new deferred items in 30 seconds** with `/skill unforget add`.
- **Lets you refine any row later** with `/skill unforget edit` if the auto-filled defaults don't match what you actually think.
- **Re-scans on demand** with `/skill unforget import` to catch new audit reports or plan files that appeared since the first run.
- **Flags stale rows** with `/skill unforget scan` when items have been sitting too long for their priority level. Read-only; never modifies the file.
- **Walks you through release prep** with `/skill unforget promote`. At each release, this verifies all 🚢 THIS rows are Fixed, then bumps NEXT into THIS so the next cycle is set up.
- **Updates your project's AI instruction file** (CLAUDE.md, AGENTS.md, or whichever your editor uses) so future AI sessions automatically know to read UNFORGET.md when you ask "what's deferred?"

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

Most backlog tools have one Priority field that tries to answer two different questions: "how bad is this?" and "when does it ship?" Those are different questions, and squashing them together hides useful information. Some examples:

- An item rated 🟡 HIGH urgency might still wait for the next update, because the current release is going out the door tomorrow and you can't fit one more change.
- An item rated 🟢 MEDIUM urgency might jump into "this release" because it turned out to be a one-line fix you stumbled into while reviewing other code.
- An item rated ⚪ LOW might sit in the backlog for three release cycles, then suddenly become 🚢 THIS because real user feedback made it more urgent.

Keeping Urgency and Target as separate columns lets either one change without rewriting the other. Sort by Target when you're asking "what blocks shipping?" Sort by Urgency × ROI when you're asking "what should I work on first?" Same rows, different lens.

## Install

Clone this repo into Claude Code's skills directory:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Terryc21/unforget.git ~/.claude/skills/unforget
```

That's it. Claude Code picks up the skill the next time you start a session. To verify, type `/skill unforget` in any project; you should see the skill respond.

**To update later:** `cd ~/.claude/skills/unforget && git pull`.

**Manual install** (if you can't or don't want to clone): download `SKILL.md` from this repo, then:

```bash
mkdir -p ~/.claude/skills/unforget
cp ~/Downloads/SKILL.md ~/.claude/skills/unforget/
```

### See an example before installing

If you'd like to see what a populated UNFORGET.md looks like before deciding to install, check out [`examples/UNFORGET.md`](examples/UNFORGET.md) in this repo. It's a sanitized version of a real project's file with all four sections filled in, varied Targets and Statuses, and a closed-with-spawn pattern (P3 → P6) showing how follow-up work gets tracked.

## Quick start

In any Claude Code session inside your project, run:

```
/skill unforget init
```

This walks you through a one-time setup that takes 5 to 15 minutes. Here's what each step does, in plain English:

1. **A few setup questions** (under 2 minutes). Where should UNFORGET.md live? How often do you ship? Should I wire your CLAUDE.md (or AGENTS.md, or whatever AI instruction file your editor uses) so future sessions automatically know about UNFORGET.md?
2. **I look around your project for deferred items.** I scan six places where deferred work tends to hide: a `Deferred.md` file at the root, audit-tool reports, paused plan files, `// TODO` comments in your code, GitHub issues labeled "deferred" or "later", and AI memory files. I make a list. Nothing is moved yet.
3. **You decide what to import.** For each place I found items, you say: "import them all", "let me look at them one at a time", or "skip this source." You're in charge.
4. **I fill in the rating columns with safe defaults.** Each row has 10 columns (urgency, risk, effort, etc.). I take a conservative guess. You can upgrade any row later with `/skill unforget edit`.
5. **I ask what else is on your mind.** Bugs you've noticed but never wrote down, friction you've felt, "I should fix that someday" thoughts. You list them, I capture them. This step usually catches the most important rows because they're the ones no automated scan could find.
6. **Optional deep questions.** If you want a thorough audit at adoption time, I'll ask 8 to 10 guided questions. Most people skip this and run it later with `/skill unforget import --deep`.
7. **You preview, I write.** Before anything is saved, I show you exactly what's about to land in UNFORGET.md. If it looks right, I write the file, redirect (or archive) the old sources I imported from, and wire the recall trigger into your AI instruction file. Nothing is ever silently deleted.

After init, capturing a new deferred item takes 30 seconds:

```
/skill unforget add "API rate limiter sometimes returns 429 even when under quota"
```

I assign an ID, default the Target to 🌫️ SOMEDAY (you can promote it later when it matters more), and append the row to Section 2 (Session spillover).

When you're ready to ship a release:

```
/skill unforget list --target=THIS
```

You see only the rows that block submission. Fix them, mark them Fixed, run `/skill unforget promote`, and ship.

### Reading UNFORGET.md outside Claude

UNFORGET.md is a markdown file with wide tables (10 columns). Reading it in a plain terminal can be cramped. To see it laid out cleanly:

- **GitHub or GitLab**: just open the file in the web UI. Tables render natively.
- **Any markdown viewer app**: [MacDown](https://macdown.uranusjr.com/) (Mac, free), [Marked 2](https://marked2app.com/) (Mac, paid), [Obsidian](https://obsidian.md/) (cross-platform, free), [Typora](https://typora.io/) (cross-platform, paid). Open UNFORGET.md in any of them and the tables look like real tables.
- **VS Code**: install the built-in "Markdown Preview" (cmd-shift-V on Mac, ctrl-shift-V on Windows/Linux).
- **Claude Code itself**: ask Claude to summarize the file or filter it. The skill's `/skill unforget list` command also formats output for you.

If a row's tables ever look broken in your terminal (rendered as vertical blocks instead of horizontal rows), widen the window or read the file in one of the apps above. The data is fine; only the rendering needs more space.

### Command reference

In v0.1 every command is prefixed with `/skill`. In v0.2 (when this ships as a plugin) the prefix goes away and you'll just type `/unforget add`, etc.

| Command | What it does |
|---|---|
| `/skill unforget init` | First-time setup. Creates UNFORGET.md, scans for existing deferred items, captures items you have in mind. Run once per project. |
| `/skill unforget add` | Add a new deferred item (defaults to Section 2: Session spillover). |
| `/skill unforget edit <ID>` | Update any column on an existing row (raise the Urgency, change the Target, mark Fixed, etc.). |
| `/skill unforget import` | Re-scan your project for new deferred items that appeared after init (a new audit report, a new plan file, etc.). |
| `/skill unforget list` | Show what's in the file. Filter by section, Target, Urgency, or staleness. |
| `/skill unforget scan` | Find rows that have been sitting too long for their priority. Doesn't change the file; just tells you what's stale. |
| `/skill unforget promote` | Release-time check. Verifies all 🚢 THIS rows are Fixed, then promotes 🚢+1 NEXT rows up to 🚢 THIS for the next cycle. |

## Feedback wanted

[Open an issue](https://github.com/Terryc21/unforget/issues) describing how the skill held up on your project: what worked, what felt wrong, what was missing. Real-project feedback is what shapes v0.2 and catches gaps the source project never surfaced. Especially helpful: small repos, non-Apple projects (web, Android, backend, libraries), projects that use Cursor / Aider / Copilot instead of Claude Code, and continuous-deployment workflows.

## Three preset modes

Not every project ships the same way. During `init` you'll pick one of three table shapes. Each one is ready to go; you don't have to design columns yourself.

| Preset | Best for | What's different |
|---|---|---|
| **Standard** | Mobile or desktop apps that ship discrete releases (App Store, Play Store, GitHub Releases) | Full 10-column table with Target values 🚢 THIS / 🚢+1 NEXT / 🚢+2 LATER / 🌫️ SOMEDAY |
| **Lean** | Solo developers, side projects, anyone learning the format | Same Target column, but only 6 columns total (Finding, Urgency, Effort, Status, plus Target). Less to fill in per row. |
| **Continuous** | Web apps, services, libraries that deploy multiple times a day | Replaces "Target" (release-based) with "Window" (time-based): 🟢 NOW / 🟡 THIS WEEK / 🔵 THIS MONTH / 🌫️ SOMEDAY |

If your team needs extra fields (a Client column, a Sprint number, a Component tag), you can add them. What you can't do is remove or rename the core columns; that breaks the format and makes it hard to compare projects, share rows across teams, or use future tooling.

## Why this isn't "just another to-do system"

There are dozens of task trackers out there. Here's what's different about this one:

1. **It's a format, not an app.** UNFORGET.md is plain markdown. It renders correctly on GitHub, in any text editor, and in Linear's markdown viewer. You're never locked into a specific company's product or stuck migrating data if you change tools.
2. **The Target column has a defined release ritual.** Most trackers have a "priority" field that changes meaning depending on who looks at it. The Target column has only four possible values, and there's a specific moment (release time) when each one shifts up the chain. That predictability is the point.
3. **Your AI assistant reads it automatically.** When you ask Claude (or Cursor, or Aider) "what's deferred?", it already knows where to look. The skill wires this up during init so you never have to remember to point at the file.
4. **It catches stale items before users do.** Most trackers grow forever. `unforget scan` flags rows that have been sitting too long for their priority level so you can decide whether to fix them, downgrade them, or close them.
5. **Capture is fast.** If logging a deferred item ever takes longer than 30 seconds, this skill has failed at its main job. That's the bar to beat.

## How it works with other tools

- **Audit tools (linters, code review skills, custom audits):** When an audit finds an issue you decide not to fix right away, it becomes a row in Section 3 (Audit findings). The original tool name and finding ID are preserved so you can trace the row back to its source.
- **Planning tools (Claude Code `/plan`, `/loop`, hand-written plan files):** When you pause a plan partway through, it becomes a row in Section 1 (Paused plans) with a link to the plan file. The plan file keeps the detail; UNFORGET.md just tells you the plan exists and where to find it.
- **Scheduled runs (`/schedule`):** You can schedule `/skill unforget scan` to run weekly or every other week. The output is plain markdown, so you can paste it into Slack, email, or a GitHub Issue.
- **AI memory files:** Memory is for context that survives across sessions (the "why" behind a decision). UNFORGET.md is for tracking (the "what" and "when"). Use both; don't duplicate. If you find yourself writing the same fact in both places, put it in memory and reference it from UNFORGET.md.

## What this works with

- **Claude Code:** This is its native home. All the slash commands in this README work in Claude Code today.
- **Other AI assistants (Cursor, Copilot, Aider, Continue, Warp):** The pattern is just a markdown file plus an instruction line in your project's AI instruction file. Any AI that reads project instructions can be told to look at UNFORGET.md. The interactive setup flow is Claude-specific, but you can write the file by hand and any AI can read it.
- **No AI at all:** UNFORGET.md is plain markdown. You can create and maintain it by hand in any text editor. The format is what matters; the skill is just there to make adoption faster.
- **Teams:** UNFORGET.md commits to git like any other markdown file. If two teammates edit the same row at the same time, you'll get a normal git merge conflict; resolve it the way you'd resolve any markdown conflict.

## Recovering a broken UNFORGET.md

UNFORGET.md is plain markdown, but the skill's commands (`add`, `list`, `promote`, `scan`) depend on the format being intact. If someone (or some tool) breaks it, here's how to recover.

### The format-protection header

Every UNFORGET.md created by `init` includes a notice at the top calling out what's allowed and what isn't:

> **Allowed:** add new rows, edit row content, move rows between sections, mark rows Fixed / Deferred / Skipped, edit detail block content.
>
> **Not allowed:** rename columns, reorder columns, add or remove core columns, rename the four section headers, split this file across multiple files, delete the "Example row" near the top, renumber existing IDs, reuse retired IDs.

If you're reading this section because you (or a teammate, or an AI) did one of the "not allowed" things, the recovery path depends on which:

| What broke | How to fix |
|---|---|
| **Renamed a column header** (e.g., `Urg` -> `Urgency Level`) | Rename it back. Column headers must match the example UNFORGET.md exactly. |
| **Reordered columns** | Reorder back to the original 10-column sequence: `# / Target / Finding / Urg / RFix / RNo / ROI / Blast / Effort / Status`. |
| **Added or removed core columns** | The skill won't recognize extra columns and will silently miscount when removing. Restore the 10 core columns. Extra columns (Owner, Sprint, Component) are fine **after** the core columns; they don't break anything. |
| **Renamed a section header** | Rename to one of the four canonical headers: `## 1. Paused plans`, `## 2. Session spillover`, `## 3. Audit findings`, `## 4. User-reported / observed`. |
| **Split the file into multiple files** | Concatenate them back into one. UNFORGET.md is intentionally a single file; multi-file splits defeat the "one ledger" promise. |
| **Renumbered or reused IDs** | This one is harder. If you can find git history for the file, restore the prior IDs and stop renumbering forever. If you can't, accept the loss: cross-references in plan files, commits, and detail blocks now point at wrong rows. Pick a fresh starting integer (e.g., P100) for new rows so old references at least don't conflict. |
| **Deleted the example row** | Restore from `examples/UNFORGET.md` in this repo. The example row is referenced by the skill's onboarding documentation. |

### The format-version marker

At the top of UNFORGET.md you'll see:

```html
<!-- unforget-format: v1 -->
```

This marker tells future skill versions which format the file was created against. Don't remove it. If a future v0.2 changes the format, the skill will read this marker first and either auto-migrate or warn you before doing anything destructive.

### When in doubt

- Compare against `examples/UNFORGET.md` in this repo. That's the canonical reference for what a valid file looks like.
- If `git status` shows recent changes to UNFORGET.md and the skill commands started failing after, `git diff` shows what was changed. `git checkout HEAD -- path/to/UNFORGET.md` reverts to the last committed version.
- If you can't recover, [open an issue](https://github.com/Terryc21/unforget/issues) describing what happened. Recovery patterns we missed will get added to this list.

## Origin

`unforget` came out of a real shipping app: Stuffolio, a Universal app for iOS, iPadOS, and macOS built from a single Swift codebase. Deferred work in that project had spread across five different tracking surfaces (a Deferred.md, plan files, audit ledgers, memory entries, and code comments). Pulling everything into one file freed roughly 3 hours of release-prep time per cycle, mostly because nobody had to walk five surfaces anymore to answer "what's left before we ship?"

Here's an honest look at what's solid in v0.1 and what's still earning its stripes:

- **The 10-column table format is solid.** It's been used through an actual App Store submission cycle in the source project. Rows, sections, the Target column, and the promotion ritual all do what they say.
- **The setup flow (the seven phases) is specified in detail and tested.** Two rounds of nondestructive testing (one complex multiplatform app, one minimal third-party skill) caught 13 small gaps in the spec, all fixed. It works today, but it hasn't been used for months in a production project other than the source. Your real-world feedback is what makes v0.2 better.
- **The install path will get smoother in v0.2.** Today you clone a git repo and invoke with `/skill unforget`. v0.2 will be a Claude Code plugin: one-line install, and you invoke it as `/unforget` (no `/skill` prefix). The features don't change; only the install experience does.

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

This skill is early-stage, so the most valuable thing you can do is try it and tell me where the format broke down for your workflow. [Open an issue](https://github.com/Terryc21/unforget/issues) describing what didn't fit. Real failures are more useful than feature suggestions.

Pull requests are welcome for:

- More preset modes (academic / research / open-source maintainer / consultant-with-multiple-clients / others I haven't thought of)
- Smarter scan rules (better signals for "this row is stale")
- Cleaner integration with specific tools (your linter, your task tracker, your CI system)
- Clearer error messages when UNFORGET.md gets corrupted or malformed

A few things this skill **won't** accept, and why (the SKILL.md "Anti-patterns" section explains in detail):

- **Hiding columns per row.** Every row needs all 10 columns. Hiding columns inconsistently breaks scanning.
- **Reordering or renaming the core columns.** Sharing rows across projects (or across teams) only works if the format is identical everywhere.
- **Splitting UNFORGET.md across multiple files.** "One file, four sections" is the whole point. Splitting it puts you back in the scattered-across-five-surfaces problem this skill exists to solve.

The strict opinions about format are the value, even when they're inconvenient.
