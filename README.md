# unforget

![Status](https://img.shields.io/badge/status-v0.2.0-blue) ![License](https://img.shields.io/github/license/Terryc21/unforget) ![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)

> A way of not losing sight or track of what is deferred.

A Claude Code skill that consolidates deferred work (paused plans, mid-task spillover, audit findings, and observed-but-not-yet-fixed bugs) into one structured file. Built so deferred items don't slip through the cracks between releases.

## See it first

Here's what an UNFORGET.md actually looks like (excerpt from [`examples/UNFORGET.md`](examples/UNFORGET.md), which is a sanitized version of a real shipping project's file):

```markdown
## 1. Paused plans

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast      | Effort | Status   |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|------------|--------|----------|
| P1 | 🟡 LATER   | Schema v3 migration paused (rollback path unclear)   | 🟢 MED  | 🟡 High | 🟢 Med  | 🟢 Good      | 🟢 ~7 fls  | Med    | Deferred |
| P2 | 🔵 NEXT    | Test suite: 23 flaky tests, 4 root causes            | 🟡 HIGH | ⚪ Low  | 🟢 Med  | 🟠 Excellent | 🟡 ~10 fls | Med    | Deferred |
| P3 | 🔴 THIS    | Wallet pass server signing not yet implemented       | 🟡 HIGH | 🟢 Med  | 🟡 High | 🟠 Excellent | 🟢 ~4 fls  | Med    | Fixed    |
| P4 | 🟡 LATER   | Search relevance overhaul (phases 1-4 done, 5-7 TBD) | 🟢 MED  | 🟢 Med  | 🟢 Med  | 🟢 Good      | 🟡 ~8 fls  | Lrg    | Open     |
| P5 | ⚪ SOMEDAY | Third-party API access REJECTED 2026-03-10           | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | ⚪ 0 fls   | Triv   | Deferred |

### Detail - Paused plans

- **P3** - **CLOSED 2026-04-20: hidden the menu entry until server signing lands. Spawns: P6.** Every item that showed the Wallet feature failed when the user completed the flow. Blocked on server `/api/wallet/sign-pass` + Apple Pass Type ID. Chose hiding for build 13; future endpoint work tracked at row P6.
```

That's the format: one file, four sections, one rating table per section, one detail block per row. The Target column on the left is the release-cycle commitment (🔴 THIS / 🔵 NEXT / 🟡 LATER / ⚪ SOMEDAY); the rest of the columns rate the row across the standard axes (urgency, risk if you fix it, risk if you don't, ROI, blast radius, effort, current status). The detail block under the table holds the prose context, including the closure pointer that makes a closed row's outcome scannable from the next reader's first glance.

The full `examples/UNFORGET.md` shows all four sections populated with varied Targets, Statuses, and a closed-with-spawn pattern (P3 → P6).

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
- **Lets you capture new deferred items in 30 seconds** with `/unforget add`.
- **Lets you refine any row later** with `/unforget edit` if the auto-filled defaults don't match what you actually think.
- **Re-scans on demand** with `/unforget import` to catch new audit reports or plan files that appeared since the first run.
- **Flags stale rows** with `/unforget scan` when items have been sitting too long for their priority level. Read-only; never modifies the file.
- **Walks you through release prep** with `/unforget promote`. At each release, this verifies all 🔴 THIS rows are Fixed, then bumps NEXT into THIS so the next cycle is set up.
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
| 🔴 **THIS** | Must ship in current release cycle. Blocks submission. |
| 🔵 **NEXT** | First post-release point update. |
| 🟡 **LATER** | Two cycles out or more. |
| ⚪ **SOMEDAY** | No commitment. Captured so it doesn't get lost. |

**Invariant:** 🔴 THIS is the only Target that blocks shipping. Everything else is post-release by definition. When you ship, NEXT auto-promotes to THIS, LATER promotes to NEXT, and you re-triage SOMEDAY.

## Why a Target column

Most backlog tools have one Priority field that tries to answer two different questions: "how bad is this?" and "when does it ship?" Those are different questions, and squashing them together hides useful information. Some examples:

- An item rated 🟡 HIGH urgency might still wait for the next update, because the current release is going out the door tomorrow and you can't fit one more change.
- An item rated 🟢 MEDIUM urgency might jump into "this release" because it turned out to be a one-line fix you stumbled into while reviewing other code.
- An item rated ⚪ LOW might sit in the backlog for three release cycles, then suddenly become 🔴 THIS because real user feedback made it more urgent.

Keeping Urgency and Target as separate columns lets either one change without rewriting the other. Sort by Target when you're asking "what blocks shipping?" Sort by Urgency × ROI when you're asking "what should I work on first?" Same rows, different lens.

## Install

> [!NOTE]
> **v0.2.0 (shipped 2026-05-02).** The skill installs as a Claude Code plugin: two one-line commands and `/unforget` is available in any project session. Claude reads the skill file and walks you through setup. If you'd rather not use Claude at all, UNFORGET.md is plain markdown; you can edit it by hand in any text editor.

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

> **Why two separate blocks?** If you copy both `/plugin` lines at once and paste them into Claude Code, the slash-command dispatcher treats the first `/plugin` as the command and the rest of the paste as its arguments. Run them one at a time to avoid that trap.

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

## Quick start

In any Claude Code session inside your project, run:

```
/unforget init
```

This walks you through a one-time setup that takes 5 to 15 minutes. Here's what each step does, in plain English:

1. **A few setup questions** (under 2 minutes). Where should UNFORGET.md live? How often do you ship? Should I wire your CLAUDE.md (or AGENTS.md, or whatever AI instruction file your editor uses) so future sessions automatically know about UNFORGET.md?
2. **I look around your project for deferred items.** I scan six places where deferred work tends to hide: a `Deferred.md` file at the root, audit-tool reports, paused plan files, `// TODO` comments in your code, GitHub issues labeled "deferred" or "later", and AI memory files. I make a list. Nothing is moved yet.
3. **You decide what to import.** For each place I found items, you say: "import them all", "let me look at them one at a time", or "skip this source." You're in charge.
4. **I fill in the rating columns with safe defaults.** Each row has 10 columns (urgency, risk, effort, etc.). I take a conservative guess. You can upgrade any row later with `/unforget edit`.
5. **I ask what else is on your mind.** Bugs you've noticed but never wrote down, friction you've felt, "I should fix that someday" thoughts. You list them, I capture them. This step usually catches the most important rows because they're the ones no automated scan could find.
6. **Optional deep questions.** If you want a thorough audit at adoption time, I'll ask 8 to 10 guided questions. Most people skip this and run it later with `/unforget import --deep`.
7. **You preview, I write.** Before anything is saved, I show you exactly what's about to land in UNFORGET.md. If it looks right, I write the file, redirect (or archive) the old sources I imported from, and wire the recall trigger into your AI instruction file. Nothing is ever silently deleted.

After init, capturing a new deferred item takes 30 seconds:

```
/unforget add "API rate limiter sometimes returns 429 even when under quota"
```

I assign an ID, default the Target to ⚪ SOMEDAY (you can promote it later when it matters more), and append the row to Section 2 (Session spillover).

When you're ready to ship a release:

```
/unforget list --target=THIS
```

You see only the rows that block submission. Fix them, mark them Fixed, run `/unforget promote`, and ship.

### Reading UNFORGET.md outside Claude

UNFORGET.md is a markdown file with wide tables (10 columns). Reading it in a plain terminal can be cramped. To see it laid out cleanly:

- **GitHub or GitLab**: just open the file in the web UI. Tables render natively.
- **Any markdown viewer app**: [MacDown](https://macdown.uranusjr.com/) (Mac, free), [Marked 2](https://marked2app.com/) (Mac, paid), [Obsidian](https://obsidian.md/) (cross-platform, free), [Typora](https://typora.io/) (cross-platform, paid). Open UNFORGET.md in any of them and the tables look like real tables.
- **VS Code**: install the built-in "Markdown Preview" (cmd-shift-V on Mac, ctrl-shift-V on Windows/Linux).
- **Claude Code itself**: ask Claude to summarize the file or filter it. The skill's `/unforget list` command also formats output for you.

If a row's tables ever look broken in your terminal (rendered as vertical blocks instead of horizontal rows), widen the window or read the file in one of the apps above. The data is fine; only the rendering needs more space.

### Command reference

The plugin install (v0.2+) drops the `/skill` prefix. If you installed via the v0.1 fallback path, prefix every command with `/skill` (e.g., `/skill unforget init`).

| Command | What it does |
|---|---|
| `/unforget init` | First-time setup. Creates UNFORGET.md, scans for existing deferred items, captures items you have in mind. Run once per project. |
| `/unforget add` | Add a new deferred item (defaults to Section 2: Session spillover). |
| `/unforget edit <ID>` | Update any column on an existing row (raise the Urgency, change the Target, mark Fixed, etc.). |
| `/unforget import` | Re-scan your project for new deferred items that appeared after init (a new audit report, a new plan file, etc.). |
| `/unforget list` | Show what's in the file. Filter by section, Target, Urgency, or staleness. |
| `/unforget scan` | Find rows that have been sitting too long for their priority. Doesn't change the file; just tells you what's stale. |
| `/unforget promote` | Release-time check. Verifies all 🔴 THIS rows are Fixed, then promotes 🔵 NEXT rows up to 🔴 THIS for the next cycle. |
| `/unforget --version` | Print version, install path, and supported format-version. Useful for verifying a fresh install loaded correctly without running `init` against a real project. |

## Feedback wanted

[Open an issue](https://github.com/Terryc21/unforget/issues) describing how the skill held up on your project: what worked, what felt wrong, what was missing. Real-project feedback is what shapes v0.2 and catches gaps the source project never surfaced. Especially helpful: small repos, non-Apple projects (web, Android, backend, libraries), projects that use Cursor / Aider / Copilot instead of Claude Code, and continuous-deployment workflows.

## Four preset modes

Not every project ships the same way. During `init` you'll pick one of four table shapes. Each one is ready to go; you don't have to design columns yourself.

| Preset | Best for | What's different |
|---|---|---|
| **Standard** | Mobile or desktop apps that ship discrete releases (App Store, Play Store, GitHub Releases) | Full 10-column table with Target values 🔴 THIS / 🔵 NEXT / 🟡 LATER / ⚪ SOMEDAY |
| **Compact** | Same release-cycle semantics as Standard, but you want a narrower table (terminal use, narrow screens) | 9 columns. Target is dropped as a dedicated column and inlined as a leading badge inside the Finding cell (e.g., `**🔴 THIS · Apple Wallet pass broken promise**`). All other columns identical to Standard. |
| **Lean** | Solo developers, side projects, anyone learning the format | Same Target column, but only 6 columns total (Finding, Urgency, Effort, Status, plus Target). Less to fill in per row. |
| **Continuous** | Web apps, services, libraries that deploy multiple times a day | Replaces "Target" (release-based) with "Window" (time-based): 🟢 NOW / 🟡 THIS WEEK / 🔵 THIS MONTH / ⚪ SOMEDAY |

If your team needs extra fields (a Client column, a Sprint number, a Component tag), you can add them. What you can't do is remove or rename the core columns; that breaks the format and makes it hard to compare projects, share rows across teams, or use future tooling.

## Why this isn't "just another to-do system"

There are dozens of task trackers out there. Here's what's different about this one:

1. **It's a format, not an app.** UNFORGET.md is plain markdown. It renders correctly on GitHub, in any text editor, and in Linear's markdown viewer. You're never locked into a specific company's product or stuck migrating data if you change tools.
2. **The Target column has a defined release ritual.** Most trackers have a "priority" field that changes meaning depending on who looks at it. The Target column has only four possible values, and there's a specific moment (release time) when each one shifts up the chain. That predictability is the point.
3. **Your AI assistant reads it automatically.** When you ask Claude (or Cursor, or Aider) "what's deferred?", it already knows where to look. The skill wires this up during init so you never have to remember to point at the file.
4. **It catches stale items before users do.** Most trackers grow forever. `unforget scan` flags rows that have been sitting too long for their priority level so you can decide whether to fix them, downgrade them, or close them.
5. **Capture is fast.** If logging a deferred item ever takes longer than 30 seconds, this skill has failed at its main job. That's the bar to beat.

## When to use unforget vs an existing tracker (Jira, Linear, GitHub Projects)

If your team already pays for a project tracker, the obvious question is: "why would I add another one?" Honest answer:

**Use unforget when:**

- You're a solo or small-team developer.
- Deferred items currently scatter across `Deferred.md`, plan files, memory files, and audit ledgers (the five-surfaces problem this skill exists to solve).
- You want a tracker that the AI can read alongside your code (Claude, Cursor, Aider, Copilot all read project files; UNFORGET.md is just one more).
- You don't have a separate non-developer audience (PMs, designers, support) that needs to file or read tickets.

**Use Jira / Linear / GitHub Projects when:**

- You have a separate non-developer audience that files or reads tickets.
- You need ticket assignment, sprints, story points, custom workflows, or integrations with non-development systems.
- The tracker is your team's source of truth for *all* work, not just deferrals.

**Coexistence pattern:** UNFORGET.md is for *code-adjacent technical debt with release-cycle commitment*. The external tracker is for cross-functional work. Cross-link as needed: an UNFORGET.md row's detail block can point at `JIRA-1234`, and the Jira ticket can link to the row in the file. The two systems don't fight; they just answer different questions.

## How it works with other tools

- **Audit tools (linters, code review skills, custom audits):** When an audit finds an issue you decide not to fix right away, it becomes a row in Section 3 (Audit findings). The original tool name and finding ID are preserved so you can trace the row back to its source.
- **Planning tools (Claude Code `/plan`, `/loop`, hand-written plan files):** When you pause a plan partway through, it becomes a row in Section 1 (Paused plans) with a link to the plan file. The plan file keeps the detail; UNFORGET.md just tells you the plan exists and where to find it.
- **Scheduled runs (`/schedule`):** You can schedule `/unforget scan` to run weekly or every other week. The output is plain markdown, so you can paste it into Slack, email, or a GitHub Issue.
- **AI memory files:** Memory is for context that survives across sessions (the "why" behind a decision). UNFORGET.md is for tracking (the "what" and "when"). Use both; don't duplicate. If you find yourself writing the same fact in both places, put it in memory and reference it from UNFORGET.md.

## The post-fix sweep (a three-skill workflow)

`unforget` pairs with two companion skills to form a high-leverage loop: **surface → verify → generalize**. The loop catches a class of bugs that no single audit tool finds: **bugs that haven't crashed yet but have the same shape as one that just did**.

### The three stages

1. **Surface** — `/unforget` shows you a deferred row you're about to mark Fixed.
2. **Verify** — Before trusting the closure, confirm the fix is real. Use `/radar-suite` (or read the file directly) to check that the anti-pattern is actually gone from the current code. Stale Open rows are surprisingly common; a fix can ship without anyone updating the ledger.
3. **Generalize** — If the fix replaced an anti-pattern with a corrected pattern, the same anti-pattern likely lives elsewhere in your codebase. Run `/bug-echo` with a one-sentence description of what the fix replaced. bug-echo scans the whole codebase for the same shape and rates each match.

### Why this is different from running an auditor cold

A standard audit skill matches code against a catalog of known anti-patterns assembled in advance. The catalog reflects what the audit author thought was a bug at the time the rule was written.

The post-fix sweep matches code against an anti-pattern that **just demonstrated it was a real bug in your specific codebase**. The fix is the proof. After-the-fact pattern matching beats theoretical pattern matching every time, and it's the systematic way to find unfired bugs sitting under the same conditions that just produced a real one.

### Worked example (from the unforget development codebase)

| Stage | Command | Result |
|---|---|---|
| Surface | `/unforget` | Showed an Open row "iPhone crash tap item: collapsibleSectionsStack" that had been Open for a month |
| Verify | `/radar-suite focus on collapsibleSectionsStack` | Reported the bug had actually shipped fixed weeks earlier in two specific commits. Current code already had the corrected pattern. The row was stale. Closed as Fixed. |
| Generalize | `/bug-echo "VStack with 12+ if-conditional children in one scope can crash on physical iPhone"` | Found one BUG (a list-row view with 16 children in its type tree, identical conditions to the original) and three WATCH sites at 10–12 conditionals each. Fixed the BUG with the same split pattern; documented the WATCH sites with defensive comments. |

Total time: ~90 minutes. The list-row bug had never crashed because users hadn't accumulated enough records yet, but the runtime conditions were identical to the original. It would have hit a real user eventually. The post-fix sweep caught it before that.

### When to skip the loop

- Trivial fixes (typos, single-character changes, isolated state edits)
- Fixes to one-off code with no callers
- Cleanup of an already-failed migration where the pattern is on its way out

### Companion skill installs

| Skill | What it adds | URL |
|---|---|---|
| **radar-suite** | Verifies the closure is real; multiple audit dimensions | `https://github.com/Terryc21/radar-suite` |
| **bug-echo** | Generalizes the fix; rated report of every echo | `https://github.com/Terryc21/bug-echo` |

When you mark a row Fixed in unforget, the closure flow detects which of these are already installed and only shows install URLs for the ones missing — a clean prompt for users who already have everything, a self-bootstrapping prompt for users who don't.

## What this works with

- **Claude Code:** This is its native home. All the slash commands in this README work in Claude Code today.
- **Other AI assistants (Cursor, Copilot, Aider, Continue, Warp):** The pattern is just a markdown file plus an instruction line in your project's AI instruction file. Any AI that reads project instructions can be told to look at UNFORGET.md. The interactive setup flow is Claude-specific, but you can write the file by hand and any AI can read it.
- **No AI at all:** UNFORGET.md is plain markdown. You can create and maintain it by hand in any text editor. The format is what matters; the skill is just there to make adoption faster.
- **Teams:** UNFORGET.md commits to git like any other markdown file. If two teammates edit the same row at the same time, you'll get a normal git merge conflict. One thing to watch: the table cells are pipe-separated, and a botched conflict resolution can silently corrupt the column shape (a stray `|` or a missing one breaks rendering for the whole table). After resolving, render the file in a markdown viewer to confirm the tables still look right before committing.

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

This marker tells future skill versions which format the file was created against. Don't remove it. If a future version changes the format, the skill will read this marker first and either auto-migrate or warn you before doing anything destructive.

### When in doubt

- Compare against `examples/UNFORGET.md` in this repo. That's the canonical reference for what a valid file looks like.
- If `git status` shows recent changes to UNFORGET.md and the skill commands started failing after, `git diff` shows what was changed. `git checkout HEAD -- path/to/UNFORGET.md` reverts to the last committed version.
- If you can't recover, [open an issue](https://github.com/Terryc21/unforget/issues) describing what happened. Recovery patterns we missed will get added to this list.

## Origin

`unforget` came out of a real shipping app: [Stuffolio](https://stuffolio.app), a Universal app for iOS, iPadOS, and macOS built from a single Swift codebase, currently shipping at build 33. Deferred work in that project had spread across five different tracking surfaces (a Deferred.md, plan files, audit ledgers, memory entries, and code comments). Consolidating to a single file removed a chunk of pre-release-prep time, mostly because nobody had to walk five surfaces anymore to answer "what's left before we ship?"

Here's an honest look at what's solid and where outside feedback would help most:

- **The 10-column table format is solid.** It's been used through an actual App Store submission cycle in the source project. Rows, sections, the Target column, and the promotion ritual all do what they say.
- **The setup flow (the seven phases) is specified in detail and tested.** Two rounds of nondestructive testing (one complex multiplatform app, one minimal third-party skill) caught 13 small gaps in the spec, all fixed. It works today; what would sharpen it most is feedback from projects whose shape differs from the source — non-Apple stacks, continuous-deployment workflows, libraries, anything other than "mobile app shipping discrete releases."
- **The install path got smoother in v0.2.** v0.1 required cloning a git repo and invoking with `/skill unforget`. v0.2 ships as a Claude Code plugin: two one-line commands to install, and you invoke as `/unforget` (no prefix). The features don't change; only the install experience does. The clone-and-copy fallback still works for environments where plugin install isn't available yet.

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

The format is stable through v0.2 but the project shape it knows best is the one it came from (a single-developer mobile app shipping discrete releases). The most valuable thing you can do is try it on a project shape it hasn't seen and tell me where the format broke down. [Open an issue](https://github.com/Terryc21/unforget/issues) describing what didn't fit. Real failures are more useful than feature suggestions.

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

## Support this project

If unforget saves you a release-prep cycle, a coffee is appreciated. Issue reports about what worked or didn't are equally useful: the skill ships at v0.2 but real-project feedback is what shapes v0.3.

<a href="https://buymeacoffee.com/stuffolio">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>
