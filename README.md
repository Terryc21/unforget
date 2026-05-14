# unforget

![Status](https://img.shields.io/badge/status-v0.2.0-blue) ![License](https://img.shields.io/github/license/Terryc21/unforget) ![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet) ![Last commit](https://img.shields.io/github/last-commit/Terryc21/unforget) ![Stars](https://img.shields.io/github/stars/Terryc21/unforget?style=flat) ![Issues](https://img.shields.io/github/issues/Terryc21/unforget)

> **One file. Four sections. Nothing slips.**

A Claude Code skill that consolidates deferred work (paused plans, mid-task spillover, audit findings, and observed-but-not-yet-fixed bugs) into one structured file. Built so deferred items don't slip through the cracks between releases.

## TL;DR

- **Problem:** deferred work scatters across `Deferred.md`, `// TODO` comments, plan files, audit ledgers, AI memory files, and your head. Months later, "what's deferred?" requires walking five surfaces.
- **Solution:** one `UNFORGET.md` file with four sections (Paused plans / Session spillover / Audit findings / User-reported), each a 10-column rating table with a Target column tied to your release cycle.
- **Install:** two `/plugin` commands in Claude Code (below); skill is then available as `/unforget` in any project.
- **Maintain:** `/unforget add` captures a new row in 30 seconds. `/unforget promote` runs the release-time ritual.
- **Rescan anytime:** `/unforget import` re-runs the 6-surface scan to catch new deferred items that appeared after init (new audit reports, plan files, memory entries, TODO comments). Has duplicate detection so it won't double-import.
- **AI-ready:** the skill wires your project's AI instruction file so future sessions automatically know to read UNFORGET.md when you ask "what's deferred?"
- **Maturity:** v0.2.0; used through an actual App Store submission cycle in the source project; setup flow specified in detail with two rounds of nondestructive testing.

## Install

Run these two commands **one at a time** in Claude Code. Wait for Step 1 to confirm "Successfully added marketplace" before running Step 2.

Step 1 — add the marketplace:

```
/plugin marketplace add Terryc21/unforget
```

Step 2 — install the plugin:

```
/plugin install unforget@unforget
```

The skill is now available. To verify, type `/unforget` in any project session; you should see the skill respond. No `/skill` prefix needed.

<details>
<summary><strong>Why two separate commands?</strong></summary>

If you copy both `/plugin` lines at once and paste them into Claude Code, the slash-command dispatcher treats the first `/plugin` as the command and the rest of the paste as its arguments. Run them one at a time to avoid that trap.
</details>

<details>
<summary><strong>v0.1 manual install (legacy fallback)</strong></summary>

If the v0.2 plugin path isn't available in your environment, the v0.1 manual install still works:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Terryc21/unforget.git ~/.claude/skills/unforget
```

Then invoke as `/skill unforget` (with the prefix). To update later: `cd ~/.claude/skills/unforget && git pull`.

If you don't want to clone, download `SKILL.md` and copy it manually:

```bash
mkdir -p ~/.claude/skills/unforget
cp ~/Downloads/SKILL.md ~/.claude/skills/unforget/
```

</details>

## Maturity — where this is solid (and where feedback would help)

Honest assessment from the project author:

- **The 10-column table format is solid.** Used through an actual App Store submission cycle in the source project ([Stuffolio](https://stuffolio.app)). Rows, sections, the Target column, and the release-promotion ritual all do what they say.
- **The setup flow is specified in detail and tested.** Two rounds of non-destructive testing — one against a complex multiplatform app, one against a minimal third-party skill — caught 13 small gaps in the spec, all fixed. It works today.
- **What would sharpen it most:** feedback from projects whose shape differs from the source. Non-Apple stacks, continuous-deployment workflows, libraries, single-page apps, anything other than "mobile app shipping discrete releases." [Open an issue](https://github.com/Terryc21/unforget/issues) if you try it on something different and the format breaks down.
- **The install path got smoother in v0.2.** v0.1 required cloning a git repo. v0.2 ships as a Claude Code plugin: two one-line commands and you invoke as `/unforget` (no prefix). The clone-and-copy fallback still works.

## See it first

Excerpt from [`examples/UNFORGET.md`](examples/UNFORGET.md) (a sanitized version of a real shipping project's file):

```markdown
## 1. Paused plans

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast      | Effort | Status   |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|------------|--------|----------|
| P1 | 🟡 LATER   | Schema v3 migration paused (rollback path unclear)   | 🟢 MED  | 🟡 High | 🟢 Med  | 🟢 Good      | 🟢 ~7 fls  | Med    | Deferred |
| P2 | 🔵 NEXT    | Test suite: 23 flaky tests, 4 root causes            | 🟡 HIGH | ⚪ Low  | 🟢 Med  | 🟠 Excellent | 🟡 ~10 fls | Med    | Deferred |
| P3 | 🔴 THIS    | Wallet pass server signing not yet implemented       | 🟡 HIGH | 🟢 Med  | 🟡 High | 🟠 Excellent | 🟢 ~4 fls  | Med    | Fixed    |

### Detail - Paused plans

- **P3** - **CLOSED 2026-04-20: hidden the menu entry until server signing lands. Spawns: P6.** Every item that showed the Wallet feature failed when the user completed the flow. Blocked on server `/api/wallet/sign-pass` + Apple Pass Type ID. Chose hiding for build 13; future endpoint work tracked at row P6.
```

The Target column on the left is the release-cycle commitment. The other columns rate the row across the standard axes (urgency, risk if you fix it, risk if you don't, ROI, blast radius, effort, status). The detail block under the table holds prose context, including the closure pointer that makes a closed row's outcome scannable. See [`examples/UNFORGET.md`](examples/UNFORGET.md) for the full file with all four sections populated.

## The problem

Deferred work scatters across three places, then more:

- a `Deferred.md` at the repo root, or a "deferred" folder somewhere
- `// TODO:` comments in code, audit-tool reports, paused plan files
- memory files for AI assistants, Slack DMs to yourself, your head

Months later, when you ask "what's deferred?", the answer requires walking five surfaces. Items go stale. Some get fixed by accident. Some sit forever because nobody remembered them.

`unforget` collapses all deferral into ONE file, structured so you can scan, prioritize, and ship at a glance.

## How it works

### The format

UNFORGET.md is one markdown file with **four sections**, each a **10-column rating table**:

| Section | What goes here | ID prefix |
|---|---|---|
| **Paused plans** | Work started, paused mid-execution. Each row links to a detail file. | P |
| **Session spillover** | Items surfaced mid-task in some other work. | S |
| **Audit findings** | Items from audit tools (linters, code review, audit skills) not fixed immediately. | A |
| **User-reported / observed** | Bugs noticed but not reproduced, friction observed. | U |

Each row has ten columns: `# | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status`.

The signature column is **Target**, the release-cycle commitment:

| Target | Meaning |
|---|---|
| 🔴 **THIS** | Must ship in current release cycle. Blocks submission. |
| 🔵 **NEXT** | First post-release point update. |
| 🟡 **LATER** | Two cycles out or more. |
| ⚪ **SOMEDAY** | No commitment. Captured so it doesn't get lost. |

🔴 THIS is the only Target that blocks shipping. When you ship, NEXT auto-promotes to THIS, LATER promotes to NEXT, and you re-triage SOMEDAY.

### Why Target is its own column

Most backlog tools have one Priority field that tries to answer two different questions: "how bad is this?" and "when does it ship?" Those are different questions, and squashing them together hides useful information. Keeping Urgency and Target as separate columns lets either one change without rewriting the other. Sort by Target when you're asking "what blocks shipping?" Sort by Urgency × ROI when you're asking "what should I work on first?" Same rows, different lens.

For example: an item rated 🟡 HIGH urgency might still be 🟡 LATER, because the current release is going out the door tomorrow and you can't fit one more change. An item rated ⚪ LOW urgency might sit at ⚪ SOMEDAY for three release cycles, then suddenly become 🔴 THIS because real user feedback made it more urgent.

### What the skill does

- **Creates `UNFORGET.md`** in your project (default location is `Documentation/Development/Deferred/UNFORGET.md`, but you choose during setup).
- **Imports existing deferred work.** Scans a `Deferred.md` at the root, audit reports, plan files, `// TODO` comments, GitHub issues, AI memory files. You decide what to pull in.
- **Captures new items in 30 seconds** with `/unforget add`, with safe defaults you can refine later via `/unforget edit`.
- **Re-scans on demand** with `/unforget import` for new audit reports or plan files since the first run.
- **Flags stale rows** with `/unforget scan` (read-only).
- **Runs release prep** with `/unforget promote`: verifies all 🔴 THIS rows are Fixed, then bumps NEXT into THIS.
- **Wires your project's AI instruction file** (CLAUDE.md, AGENTS.md) so future AI sessions automatically know to read UNFORGET.md when you ask "what's deferred?"

## Quick start

In any Claude Code session inside your project:

```
/unforget init
```

A one-time setup, 5 to 15 minutes. In summary:

1. **Setup questions** (under 2 min): where should UNFORGET.md live, how often do you ship, should we wire your CLAUDE.md / AGENTS.md.
2. **Scan for existing deferred work** in six places (Deferred.md, audit reports, plan files, `// TODO` comments, GitHub issues, AI memory).
3. **You decide what to import** — all, one-at-a-time, or skip.
4. **Conservative defaults** filled into the rating columns; refine later with `/unforget edit`.
5. **You add what's on your mind** that no scan could find. Usually catches the most valuable rows.
6. **Optional deep-audit questions** (8–10 questions). Most people skip and run `/unforget import --deep` later.
7. **Preview, then write.** Nothing is silently moved or deleted.

After init, capture new items in 30 seconds:

```
/unforget add "API rate limiter sometimes returns 429 even when under quota"
```

The new row gets an ID, defaults the Target to ⚪ SOMEDAY, and lands in Section 2 (Session spillover).

At release time:

```
/unforget list --target=THIS
```

Shows only the rows that block submission. Fix them, mark them Fixed, run `/unforget promote`, ship.

### Command reference

| Command | What it does |
|---|---|
| `/unforget init` | First-time setup. Creates UNFORGET.md, scans for existing deferred items, captures items you have in mind. Run once per project. |
| `/unforget add` | Add a new deferred item (defaults to Section 2: Session spillover). |
| `/unforget edit <ID>` | Update any column on an existing row (raise the Urgency, change the Target, mark Fixed, etc.). |
| `/unforget import` | Re-scan your project for new deferred items that appeared after init. |
| `/unforget list` | Show what's in the file. Filter by section, Target, Urgency, or staleness. |
| `/unforget scan` | Find rows that have been sitting too long for their priority. Read-only. |
| `/unforget promote` | Release-time check. Verifies all 🔴 THIS rows are Fixed, then promotes 🔵 NEXT rows up to 🔴 THIS for the next cycle. |
| `/unforget --version` | Print version, install path, and supported format-version. Useful for verifying a fresh install loaded correctly. |

### Reading UNFORGET.md outside Claude

UNFORGET.md is a markdown file with wide tables (10 columns). For best readability:

- **GitHub or GitLab**: just open the file in the web UI; tables render natively.
- **Markdown viewer apps**: [MacDown](https://macdown.uranusjr.com/) (Mac, free), [Marked 2](https://marked2app.com/) (Mac, paid), [Obsidian](https://obsidian.md/) or [Typora](https://typora.io/) (cross-platform).
- **VS Code**: built-in Markdown Preview (cmd-shift-V on Mac).

If tables ever look broken in a narrow terminal (rendered as vertical blocks), widen the window or use one of the apps above. The data is fine; only the rendering needs more space.

## Four preset modes

Not every project ships the same way. During `init` you'll pick one of four table shapes:

| Preset | Best for | What's different |
|---|---|---|
| **Standard** | Mobile or desktop apps that ship discrete releases (App Store, Play Store, GitHub Releases) | Full 10-column table with Target values 🔴 THIS / 🔵 NEXT / 🟡 LATER / ⚪ SOMEDAY |
| **Compact** | Same semantics as Standard, but narrower (terminal use, narrow screens) | 9 columns. Target is dropped as a dedicated column and inlined as a leading badge inside the Finding cell. |
| **Lean** | Solo developers, side projects, anyone learning the format | Same Target column, but only 6 columns total (Finding, Urgency, Effort, Status, plus Target). Less to fill in per row. |
| **Continuous** | Web apps, services, libraries that deploy multiple times a day | Replaces "Target" (release-based) with "Window" (time-based): 🟢 NOW / 🟡 THIS WEEK / 🔵 THIS MONTH / ⚪ SOMEDAY |

Teams can add extra fields (Client, Sprint, Component) after the core columns. The core 10 columns can't be removed or renamed without breaking the format and giving up cross-project compatibility.

## When to use unforget (and when not)

**Use unforget when:**

- You're a solo or small-team developer.
- Deferred items currently scatter across `Deferred.md`, plan files, memory files, and audit ledgers.
- You want a tracker your AI can read alongside your code (Claude, Cursor, Aider, Copilot all read project files).
- You don't have a separate non-developer audience (PMs, designers, support) that needs to file or read tickets.

**Use Jira / Linear / GitHub Projects when:**

- You have a non-developer audience that files or reads tickets.
- You need sprints, story points, custom workflows, integrations with non-dev systems.
- The tracker is your team's source of truth for *all* work, not just deferrals.

The two coexist cleanly. UNFORGET.md is for *code-adjacent technical debt with release-cycle commitment*; the external tracker is for cross-functional work. Cross-link as needed.

### What's different from "just another to-do app"

1. **Format, not an app.** UNFORGET.md is plain markdown — renders on GitHub, in any editor, in Linear's preview. Never locked in.
2. **Defined release ritual.** Target has four values and one promotion moment. Predictable.
3. **AI reads it automatically.** Wire-up during `init`; you never have to remember to point at the file.
4. **Catches stale items.** `unforget scan` flags rows that have been sitting too long for their priority.
5. **30-second capture.** If logging an item takes longer than that, the skill failed.

## Companion skills

`unforget` ships alongside three skills from the same source project ([Stuffolio](https://stuffolio.app)):

| Skill | What it does | How it feeds into unforget |
|---|---|---|
| [**radar-suite**](https://github.com/Terryc21/radar-suite) | 8 audit skills that find bugs in Swift/SwiftUI apps. Every finding cites a real file:line, not generic advice. | Unfixed findings become rows in Section 3 (Audit findings). |
| [**bug-prospector**](https://github.com/Terryc21/bug-prospector) | Mines for hidden bugs that pattern-based auditors miss. Behavioral and contextual issues regex can't catch. | Outputs feed naturally into Section 4 (User-reported / observed). |
| [**bug-echo**](https://github.com/Terryc21/bug-echo) | After you fix a bug, finds other instances of the same pattern across your codebase. | Instances not fixed immediately become unforget rows. |

For the high-leverage **surface → verify → generalize** workflow that pairs all three, see [`docs/POST_FIX_SWEEP.md`](docs/POST_FIX_SWEEP.md).

## How it works with other tools

- **Audit tools** (linters, code review skills, custom audits): findings you don't fix immediately become rows in Section 3. The original tool name and finding ID are preserved.
- **Planning tools** (Claude Code `/plan`, `/loop`, plan files): paused plans become rows in Section 1, linking out to the plan file. UNFORGET.md is the index; the plan file keeps the detail.
- **Scheduled runs** (`/schedule`): you can run `/unforget scan` weekly. Output is plain markdown — paste it into Slack, email, or a GitHub Issue.
- **AI memory files**: memory is for context (the "why"). UNFORGET.md is for tracking (the "what" and "when"). Don't duplicate.
- **Other AI assistants** (Cursor, Copilot, Aider, Continue, Warp): the file is plain markdown plus one instruction line in your AI instruction file. Any AI that reads project instructions can read UNFORGET.md. The interactive `init` flow is Claude-specific.
- **No AI at all**: works fine. The format is what matters; the skill just makes adoption faster.
- **Teams**: commits to git like any other markdown file. After resolving a merge conflict, render in a markdown viewer to confirm the tables still look right — botched `|` placement can silently corrupt column shape.

## Recovering a broken UNFORGET.md

UNFORGET.md is plain markdown, but the skill's commands depend on the format being intact. Every file created by `init` includes this notice at the top:

> **Allowed:** add new rows, edit row content, move rows between sections, mark rows Fixed / Deferred / Skipped, edit detail blocks.
>
> **Not allowed:** rename columns, reorder columns, add or remove core columns, rename the four section headers, split this file, delete the example row, renumber existing IDs, reuse retired IDs.

If something broke:

| What broke | How to fix |
|---|---|
| **Renamed a column header** (e.g., `Urg` → `Urgency Level`) | Rename it back. Column headers must match exactly. |
| **Reordered columns** | Restore the 10-column sequence: `# / Target / Finding / Urg / RFix / RNo / ROI / Blast / Effort / Status`. |
| **Added or removed core columns** | Restore the 10 core columns. Extra columns (Owner, Sprint, Component) are fine **after** the core columns. |
| **Renamed a section header** | Restore one of `## 1. Paused plans`, `## 2. Session spillover`, `## 3. Audit findings`, `## 4. User-reported / observed`. |
| **Split the file into multiple files** | Concatenate back into one. Multi-file splits defeat the "one ledger" promise. |
| **Renumbered or reused IDs** | If you have git history, restore the prior IDs and stop renumbering forever. If not, pick a fresh starting integer (e.g., P100) so old references at least don't conflict. |
| **Deleted the example row** | Restore from `examples/UNFORGET.md` in this repo. |

The format-version marker at the top of every file (`<!-- unforget-format: v1 -->`) tells future skill versions which format the file was created against. Don't remove it.

When in doubt: compare against [`examples/UNFORGET.md`](examples/UNFORGET.md); use `git checkout HEAD -- path/to/UNFORGET.md` to revert; or [open an issue](https://github.com/Terryc21/unforget/issues) if recovery is unclear.

## Origin

`unforget` came out of [Stuffolio](https://stuffolio.app), a Universal app for iOS, iPadOS, and macOS shipping at build 33. Deferred work in that project had spread across five tracking surfaces (a Deferred.md, plan files, audit ledgers, memory entries, and code comments). Consolidating to a single file removed a chunk of pre-release-prep time — nobody had to walk five surfaces anymore to answer "what's left before we ship?"

See [Maturity](#maturity--where-this-is-solid-and-where-feedback-would-help) above for an honest assessment of what's solid and where outside feedback would help most.

## Contributing

The format is stable through v0.2 but the project shape it knows best is the one it came from (a single-developer mobile app shipping discrete releases). The most valuable thing you can do is try it on a project shape it hasn't seen and tell me where the format broke down. [Open an issue](https://github.com/Terryc21/unforget/issues). Especially helpful: small repos, non-Apple stacks (web, Android, backend, libraries), Cursor / Aider / Copilot workflows, continuous-deployment workflows.

Pull requests welcome for:

- More preset modes (academic, open-source maintainer, consultant-with-multiple-clients)
- Smarter scan rules (better signals for "this row is stale")
- Cleaner integration with specific tools (linters, task trackers, CI systems)
- Clearer error messages when UNFORGET.md gets corrupted

Things this skill **won't** accept:

- **Hiding columns per row** — breaks scanning.
- **Reordering or renaming core columns** — breaks cross-project compatibility.
- **Splitting UNFORGET.md** — defeats the "one file, four sections" promise.

## License

Apache License 2.0. See [LICENSE](LICENSE).
