# Codex and Claude Code runtime conventions

This repository is the shared implementation for both hosts. Use the same ledger,
references, Python helpers and HTML template. Host differences belong here.

| Convention | Codex | Claude Code |
|---|---|---|
| Explicit request | `$unforget report` | `/unforget report` for standalone skills; `/unforget:unforget report` for the plugin |
| Personal skill folder | `~/.agents/skills/unforget/` | `~/.claude/skills/unforget/` |
| New project recall instructions | `AGENTS.md` | `CLAUDE.md` |
| Personal companion manifest | `${CODEX_HOME:-$HOME/.codex}/unforget-companions.md` | `~/.claude/unforget-companions.md` |

Claude Code releases that recognize a plugin manifest inside a skill folder can
expose the namespaced plugin command there too. Use the command shown in the `/`
menu; the subcommand and workflow stay the same. Do not install duplicate copies
through both the marketplace and personal skills directory.

## Running the workflow

- Resolve bundled resources relative to the loaded `SKILL.md`, including through a
  symlink. Run helpers by absolute path and quote paths containing spaces.
- Names such as Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion and Skill in
  references describe operations. Map them to available host tools. In Codex use
  file/shell tools and `rg`; a Skill call means load the named skill if available.
  Do not assume Claude tools or Codex desktop tools exist in the other host.
- Carry forward the user's scope and answers. Use an available question tool or
  ordinary chat only for missing information; do not copy another host's tool JSON.
- Use a companion skill only if installed. Use delegation only when authorized and
  supported by the current session; otherwise do the work sequentially and disclose
  any unavailable independent review. Never claim an unavailable skill ran.
- For every `scripts/companions.py` command in Codex, pass `--file` with the Codex
  companion manifest from the table. The script's legacy default is Claude's path.
  Preserve an explicitly configured manifest instead of migrating it silently.

## Existing project data

Discover the project's actual ledger and registry before choosing paths. Preserve
existing recall settings; when creating a new instruction file, use the host's
filename above. If the user wants both hosts, wire both instruction files to the
same canonical ledger. Never create separate Codex and Claude backlogs.

Claude plan/memory paths in `reference/surfaces.md` identify existing Claude data.
In Codex, treat those as optional, project-scoped import sources; do not invent a
Codex equivalent or create Claude state. Read only the sources relevant to the
requested project and import scope.

Use the user's requested output location and current workspace conventions. HTML
reports are ordinary local files; either host can generate them with Python 3.9+
and the standard library. No app-specific preview or browser tool is required.
