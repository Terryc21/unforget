# unforget

![Version](https://img.shields.io/github/v/tag/Terryc21/unforget?label=version&cacheSeconds=3600&v=2.8.0) ![Last commit](https://img.shields.io/github/last-commit/Terryc21/unforget?cacheSeconds=3600) ![Stars](https://img.shields.io/github/stars/Terryc21/unforget?style=flat&cacheSeconds=3600) ![Issues](https://img.shields.io/github/issues/Terryc21/unforget?cacheSeconds=3600) ![License](https://img.shields.io/github/license/Terryc21/unforget?cacheSeconds=3600) ![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet)

> **One file. Four sections. Nothing slips.**

**Everything you meant to come back to, in one place.**

You put things off — a bug you couldn't reproduce, a plan you paused, a warning you'd rather
fix later. Right now those live in a `TODO` comment, a plan file, an audit report, a note to
yourself, and your memory. Months later, "what did I put off?" means checking all of them.

unforget puts them in one file, sorted by whether they block your next release.

*4 min read · [every command](reference/commands.md) · [the format](reference/format.md)*

---

## What it makes

One `UNFORGET.md` in your project. Each row is something you deferred:

```markdown
| #  | Target   | Finding                                  | Urgency   | Effort  | Status |
|----|----------|------------------------------------------|-----------|---------|--------|
| A1 | 🔴 THIS  | Paywall lists a feature that ships free  | 🟡 HIGH   | Trivial | `@status:done-verified` |
| A2 | 🔵 NEXT  | Slow loading on the inventory screen     | 🟢 MEDIUM | Small   | `@status:open` |
```

**Target** is the column that matters: *when does this have to be done?*

| | |
|---|---|
| 🔴 **THIS** | Before the next release. This is the only one that stops you shipping. |
| 🔵 **NEXT** | The release after that. |
| 🟡 **LATER** | Further out. |
| ⚪ **SOMEDAY** | No promise. Written down so it isn't lost. |

When you ship, NEXT becomes THIS automatically, and LATER becomes NEXT.

Underneath the table, each row gets a few lines of detail: why it matters, which files, and a
command to check whether it's still a problem. The table is the index; the detail is the story.

**[See a full example →](examples/UNFORGET.md)**

---

## Why "done" isn't good enough

Every row carries a status the skill can read, and there are two kinds of done:

- **`done-verified`** — fixed, and somebody checked
- **`done-unverified`** — the code is written, nobody confirmed it works

That second one still counts as **open**. It shows up in your list, and it stops a release
until it's proven.

> This exists because of a specific mistake: marking something done, believing it, and shipping.
> A row that says "done" because someone *said* so is not the same as a row that says done
> because it was checked, and only one of them should let you ship.

---

## Try it

Run these **one at a time**, waiting for the first to confirm before the second:

```
/plugin marketplace add Terryc21/unforget
```

```
/plugin install unforget@unforget
```

Then, in a project:

```
/unforget init
```

Setup takes 5 to 15 minutes, once per project. It asks where to keep the file, looks through
your project for things you've already deferred (TODO comments, plan files, audit reports,
GitHub issues, notes), and shows you what it found before writing anything.

The step that finds the most is the one where **it asks what's on your mind** — the things no
search could have found.

<details>
<summary><strong>Why two separate commands?</strong></summary>

Pasting both `/plugin` lines at once makes Claude Code read the second line as an argument to
the first. Run them separately.
</details>

<details>
<summary><strong>Installing by hand</strong></summary>

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/Terryc21/unforget.git ~/.claude/skills/unforget
```

Then use `/skill unforget` (with the prefix). Update later with `git pull` in that folder.
</details>

---

## Day to day

Something comes up while you're working on something else:

```
/unforget add "rate limiter returns 429 even when under quota"
```

Takes seconds. If it took longer, you'd stop doing it.

Getting ready to ship:

```
/unforget list --target=THIS
```

That's your blocking list. Fix them, then `/unforget promote` checks they're really done and
rolls everything forward.

**[All the commands →](reference/commands.md)**

---

## Is this for you?

**Probably yes if:** you work alone or in a small team, the things you've deferred are scattered
across several places, and you'd like your AI assistant to be able to read the list.

**Probably not if:** people outside your dev team need to file or read tickets, or you need
sprints and story points. Jira and Linear do that; this doesn't try to.

They work together fine — unforget for the technical debt near your code, the other tracker for
work that crosses teams.

### What makes it different from a to-do list

- **It's a file, not an app.** Plain markdown. Renders on GitHub, opens in any editor, follows
  your repo. Nothing to lock you in.
- **It knows about shipping.** One column says when, and one moment each release moves everything
  forward.
- **Your AI reads it without being asked.** Setup wires it into your CLAUDE.md.
- **It notices things going stale.** `/unforget scan` finds rows sitting far longer than their
  priority suggests.

### The part nobody designed: it turns into case law

This one wasn't planned, and it's the most interesting thing the format does.

Three features got added for small, separate reasons: rows can link to each other (`[[A72]]`),
each closed row keeps a detail block explaining *why* it was fixed that way, and those blocks
record the dead ends — the hypotheses you tried and threw away. None of that was meant to build
anything bigger.

But past a certain number of closed rows, they cross a line together. A new bug stops being
solved from scratch and starts being *argued against precedent*: "this is the same shape as that
row we closed in June — make the fix look like that one." A wrong-but-plausible fix gets caught
by a closed row that already says *don't do the obvious thing here, and here's why.* The ledger
quietly became a place you compare a current problem against related problems you already solved.

**Why git can't do this.** Grepping your commit history finds fixes that *shipped*. It cannot
find the two things that actually save time on the next bug: the hypotheses you tried and
abandoned (you don't commit a theory you disproved), and the reason a plausible fix is wrong.
Those live in the closed rows, not the diff.

Once a ledger is mature enough, it's worth naming that second use explicitly. A `PRECEDENTS.md`
file — a one-line-per-entry index that *points at* the closed rows carrying reusable shapes and
traps, without copying them — makes "what did we already learn about this?" a lookup instead of a
memory. It references the rows; the rows stay the source of truth.

🛑 **Only build the index on a mature ledger.** With three closed rows, an index manufactures
false precedent from whatever you happened to fix *first* — superstition wearing a CANON label.
The signals that say a ledger is ready: a real share of rows closed (not a handful), many rows
cited by other rows, a reference shape that recurred across months rather than one early fix, and
citations that point at *closed* work. Measure before you formalize. On a young ledger, skip it —
the format is a to-do list first, and only earns the second use with age.

---

## Where it's solid, where it isn't

**Solid.** The format has been through a real App Store release cycle on
[Stuffolio](https://stuffolio.app), the app it came from. Setup has been tested twice against
different project shapes, which caught 13 gaps that are now fixed.

**Untested.** It knows one shape well: a single developer shipping an app in distinct releases.
Web services, libraries, continuous deployment, non-Apple stacks — there's a Continuous preset
for time-based work instead of release-based, but nobody has really put it through its paces.

**Real limits, worth knowing before you start:**

- **It assumes one person keeps the file tidy.** Teams can share it through git, but there's no
  assigning, no comment threads, no notifications.
- **It doesn't sync to anything.** No Jira, no Linear, no GitHub Issues. You can paste links; nothing
  updates itself.
- **You decide when to run the release check.** Forget, and nothing moves forward on its own.

**What would help most:** try it on a project that isn't a mobile app and tell me where the format
falls apart. [Open an issue](https://github.com/Terryc21/unforget/issues) — small repos, web
backends, Android, libraries, or a Cursor or Aider workflow are all more useful than another
iOS report.

---

## Fits with what you already use

Audit tools and linters drop their unfixed findings straight in. Paused plans become a row that
points back at the plan file. Any AI that reads your project instructions can read the file —
Cursor, Copilot, Aider, Continue. It works with no AI at all, since it's just markdown.

It commits to git like any other file. After a merge conflict, open it in a preview to check the
table survived — a misplaced `|` breaks a table quietly.

**[Pairing it with the bug-finding skills →](docs/POST_FIX_SWEEP.md)** ·
**[If the file gets mangled →](docs/RECOVERY.md)**

---

## Digging deeper

| | |
|---|---|
| **[Every command](reference/commands.md)** | Full detail on each one |
| **[The format](reference/format.md)** | Columns, statuses, and the optional 1-star-risk column |
| **[Setup](reference/init.md)** | What `init` does, step by step |
| **[Release ritual](reference/promotion.md)** | What `promote` checks before letting you ship |
| **[Splitting the file](reference/branching.md)** | When a sprint or someone else's list earns its own |
| **[Recovery](docs/RECOVERY.md)** | Repairing a broken file |
| **[SKILL.md](SKILL.md)** | The instructions Claude follows, and the full changelog |

**Reading the file outside Claude.** Ten columns is wide. GitHub and GitLab render it fine, as do
VS Code's preview, Obsidian, Typora, Bear, MacDown, iA Writer, and Marked 2. If a table looks
broken in a narrow terminal, the file is fine — the window is too small.

---

## Contributing

The format is stable. What it needs is exposure to project shapes it hasn't seen.

Pull requests welcome for new presets, better staleness rules, integrations, and clearer errors.

Three things it won't take, because each breaks a promise the format makes: hiding columns on
some rows, renaming or reordering the core columns, and splitting UNFORGET.md into several files.

---

## Related skills

[**bug-echo**](https://github.com/Terryc21/bug-echo) — find the same bug elsewhere after a fix ·
[**bug-prospector**](https://github.com/Terryc21/bug-prospector) — hunt for bugs before a release ·
[**workflow-audit**](https://github.com/Terryc21/workflow-audit) — trace SwiftUI behaviour ·
[**radar-suite**](https://github.com/Terryc21/radar-suite) — six skills tracing user paths ·
[**prompter**](https://github.com/Terryc21/prompter) — rewrite prompts before running them ·
[**skill-reviewer**](https://github.com/Terryc21/skill-reviewer) — candid reviews of other skills ·
[**tutorial-creator**](https://github.com/Terryc21/tutorial-creator) — lessons from your own code

---

**New to Claude Code?** A *skill* is a set of written instructions Claude Code knows how to
follow. Type `/unforget add "..."` and it adds a row to your file and tells you what it did.
Nothing to memorise, and the file stays plain markdown you can edit yourself.

**Terry Nyberg**, [Coffee & Code LLC](https://stuffolio.app/). It came out of
[Stuffolio](https://stuffolio.app), where deferred work had spread across five different places
and pre-release prep meant checking all of them. If unforget has caught something for you,
[a coffee](https://buymeacoffee.com/stuffolio) is appreciated — though a note about how it went
on a project unlike mine is worth more.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/stuffolio)

Apache 2.0 — see [LICENSE](LICENSE).
