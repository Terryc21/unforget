# unforget — Surface survey reference

This file holds the full surface-survey specification: the six core surfaces, Surface 1b (general documentation scanning), the redirect-pointer pre-check, memory-directory resolution, the Claude Code path-encoding rule, the meta-file pre-check, audit-tool format-aware parsing, cross-surface deduplication, the GitHub-issues four-state branch, and the algorithm fallback.

Read this file on `/unforget init` (Phase 2), `/unforget import`, or any time surface-related behavior needs auditing.

**Preferred implementation:** delegate the entire scan to `python3 scripts/scan_surfaces.py --root <path>`. The script returns a JSON candidate list grouped by surface. The `## Algorithm fallback (Python unavailable)` section at the end of this file is the prose fallback for environments without Python 3.

---

## Six core surfaces

Scan the project for existing deferred-work artifacts across six tractable surfaces. NOTHING is imported in this phase; the survey only produces a candidate list.

**Universal exclusion rule (applies to ALL surfaces):** any path containing a segment named `archive` or `Archive` is skipped. Files in archive paths are intentionally retired, and importing them re-pollutes the active backlog with old work the project already moved past. Same for `.git/`, `node_modules/`, `vendor/`, `Pods/`, and the project's `Documentation/Development/Archive/` (or equivalent) folder if one exists. **In addition, any markdown file whose filename matches `*archive*.md` (case insensitive) is skipped regardless of path** so that files like `Deferred-archive-2026-05-01.md` sitting in an active directory are not wrongly imported as fresh deferrals. The skill should still REPORT the count of skipped archive files (path-based and filename-based combined) so the user knows they exist; just don't import them.

| Surface | Signal | Confidence |
|---|---|---|
| **Deferred-named files** at repo root or `Documentation/`, `docs/`, `notes/` (excluding archive paths) | Filenames matching `Deferred.md`, `BACKLOG.md`, `TODO.md`, `*deferred*.md`, `*roadmap*.md`, `ROADMAP.md`, `*plan*.md` (case insensitive). **Plus a content-shape heuristic:** files containing 3 or more headings matching `Tier N` / `Phase N` / `Priority N` patterns are flagged as deferral artifacts even if their filename does not match the regex above. | High |
| **Audit-tool reports** (excluding archive paths) | radar-suite v3+: per-finding source is `scratch/audit-*-YYYY-MM-DD.md` (markdown, e.g., `audit-concurrency-2026-04-25.md`); `.radar-suite/ledger.yaml` is read for audit-run metadata only. Other tools: `.eslint-todos`, `.audit/`, custom audit YAML. | High when present |
| **Plan files** in `./plans/`, `./.claude/plans/`, `./.agents/plans/` (and any other `**/plans/*.md` excluding archive paths) only. Global `~/.claude/plans/` is **NOT** scanned by default because it produces dozens of completed-session noise hits per project. | Markdown files referencing the project name; explicit status hints (`PAUSED:`, `ABORTED:`, `IN PROGRESS:` in title or first heading) | Medium. Many will be done, not deferred. User can opt in to global scan via `/unforget import --plans=global`. |
| **Code comments** | Regex `// (TODO\|FIXME\|HACK\|XXX\|MIGRATION-NOTE\|DEFERRED)\b` (word boundary, NO required colon, because many comment styles use space or paren after the tag) across `Sources/`, `src/`, `lib/`, etc. | Variable, typically 0 to 50 hits depending on project age and code-review discipline |
| **GitHub issues** (if `gh` CLI authenticated AND repo accessible) | Open issues labeled `deferred`, `wontfix-for-now`, `post-release`, `backlog` | High when labeled |
| **Memory files** | Filename match `^deferred_*.md` or `^project_deferred_*.md` (strict, because body-text "defer" matches produce too many false positives from book/feedback files that mention deferral in passing) | High when filename matches; deprioritized for body-only matches |

### Surface 1: Deferred-named files — redirect-pointer pre-check

Before parsing a Surface 1-matched file, check whether it is a redirect pointer rather than a real backlog. A file qualifies as a redirect pointer if BOTH conditions hold:

1. The file is fewer than 30 lines.
2. The file body contains at least one of: the literal phrase `MOVED`, the literal phrase `see also`, or a relative or absolute path reference to `UNFORGET.md` or another deferral file (e.g., `Documentation/Development/Deferred/UNFORGET.md`).

When both conditions hold, skip the file with a status note: `<file>: redirect pointer skipped (points to <target>)`. Do not parse it as a backlog. The user is informed the file was found but not imported. Stuffolio repro: a project's root `Deferred.md` is a 12-line redirect to `Documentation/Development/Deferred/UNFORGET.md`. Without this pre-check, the redirect text would be parsed as deferral entries.

### Surface 6: Memory directory location, per detected AI tool

The memory-file scan needs to know where memory files live. The location depends on which AI assistant the project is wired to (detected during Phase 1: `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.aider.conf.yml`, etc.). If multiple AI tools are wired, scan each detected tool's memory directory and merge results.

| Detected AI tool | Memory directory |
|---|---|
| **Claude Code** (`CLAUDE.md` or `AGENTS.md` present) | `~/.claude/projects/<encoded-project-path>/memory/` |
| **Cursor** (`.cursorrules` present) | TODO: research and pin in v0.3. For v0.2, fall back to filename-only scan in repo root. |
| **Aider** (`.aider.conf.yml` present) | TODO: research and pin in v0.3. For v0.2, fall back to filename-only scan in repo root. |

**Claude Code path-encoding rule:** the current working directory is converted to a dash-separated string with each `/` replaced by `-` AND each whitespace character (space, tab) also replaced by `-`. The leading `/` becomes a leading `-`. Example: working directory `/Volumes/2 TB Drive/Coding/GitHubDeskTop/Stufflio` encodes to `-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio`, so memory files live at `~/.claude/projects/-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio/memory/`. The skill must compute this path from the cwd at scan time, not hardcode it.

**Preferred implementation:** delegate path encoding to the helper script:

```
python3 scripts/encode_project_path.py "<absolute-path>"
```

The script returns a JSON object `{"path": "<input>", "encoded": "<encoded>", "memory_dir": "~/.claude/projects/<encoded>/memory/"}`. See `scripts/encode_project_path.py` for the exact rule.

**Memory directory fallback (Claude Code):** Claude Code stores per-project memory at the encoded directory matching the cwd, but historically projects opened from a parent directory may have memory under that parent's encoded path instead (e.g., a session opened in `/Volumes/2 TB Drive/Coding/GitHubDeskTop/` for a Stufflio task may have written memory under `-Volumes-2-TB-Drive-Coding-GitHubDeskTop/memory/` rather than `-Volumes-2-TB-Drive-Coding-GitHubDeskTop-Stufflio/memory/`). When the cwd-encoded directory is empty or missing, walk up the cwd one segment at a time and check each ancestor's encoded directory. Stop walking at `~` or after 4 ancestor levels, whichever comes first. Report each ancestor scanned: "Memory files: scanned cwd-encoded path (0 files), parent-encoded path (4 files)."

If the encoded directory does not exist, the surface reports "Memory files: directory not found at `<path>`" rather than silently scanning zero files. The user knows the surface tried and where it looked.

### Surface 6: Memory meta-file content-shape pre-check

Filename matching alone catches both real findings and meta-docs. Files that match `^deferred_*.md` or `^project_deferred_*.md` but whose body describes the deferral system rather than containing actual findings should not be auto-imported. Before importing a Surface 6 match, scan the body for meta-doc phrases:

- The literal phrase `single source of truth`
- The literal phrase `format:` (lowercase, with colon, indicating a format-spec doc)
- The literal phrase `how to use`
- The literal phrase `index of` or `pointer to`

If any phrase is detected, prompt the user instead of auto-importing: `<file>: looks like a meta-doc (matched: '<phrase>'). Import anyway? [yes / no / preview]`. Stuffolio repro: `deferred_work_index.md` is a meta-doc that points at `Documentation/Development/Deferred/UNFORGET.md`; it contains zero deferred-work rows. Without this pre-check, its prose ("single source of truth is now `Documentation/Development/Deferred/DEFERRED.md`") would be parsed as a finding.

---

## Surface 1b: General documentation scanning

The six surfaces above catch deferral artifacts in conventional locations (Deferred-named files, audit ledgers, plan dirs, code, GitHub issues, memory). They miss the much larger set of deferred work that lives inside ordinary project documentation: dated planning notes, scratch audit reports, design docs with "Deferred" sections, hand-written backlog rollups. In a complex project, these locations hold roughly 80% of the actively-deferred items.

**Scan paths (excluding archive paths and the universal exclusions):**
- `Documentation/Development/*.md`
- `Documentation/Notes/*.md`
- `scratch/*.md`
- Equivalents (`docs/notes/`, `notes/`, `dev-docs/`, etc.) discovered during Phase 1 setup

**Heuristics (seven total). Any single match flags the file as a candidate:**

1. Heading text contains the literal word **`Deferred`** (case insensitive).
2. Heading text contains the literal word **`Pending`** (case insensitive).
3. Heading text contains the literal word **`TODO`** (case insensitive).
4. Heading text matches the pattern **`Phase N pending`** / **`Phase N deferred`** / **`Phase N todo`** (case insensitive, N is any digit).
5. Filename starts with a **date prefix** (`YYYY-MM-DD-*.md`), which conventionally marks a session/incident write-up that often contains rollup deferrals.
6. Heading begins with the explicit prefix **`DEFERRED:`** (case insensitive).
7. **Audit-report shape (scoped):** heading text matches a severity-tier prefix (`HIGH Issues`, `MEDIUM Issues`, `LOW Issues`, `CRITICAL Issues`) OR a per-finding ID pattern (regex `^#+\s+[A-Z]+-[A-Z][0-9]+:`, e.g., `### CONC-H1: ...`, `### RS-019: ...`). **This heuristic only fires on files Surface 2 already identified as audit reports** (post-T-12: any file matching `scratch/audit-*-YYYY-MM-DD.md` or another known audit-tool format). It never fires on prose docs that happen to use `## HIGH PRIORITY` headings, eliminating a large false-positive class.

**Behavior on match: each candidate prompts the user.** Surface 1b never auto-imports. Prose-shape detection is fuzzy by nature; a heading containing the word "Deferred" can mean "items being deferred from this work" or "deferred work that was already completed and archived in this doc" or "discussion of deferred work in general". The user is the safety net that distinguishes those cases. The skill's job is to surface candidates and the user's job is to decide.

**Audit-report rollup (heuristic 7):** when heuristic 7 fires, treat each per-finding ID heading inside the report as a candidate finding row. The severity-tier section header (`## HIGH Issues`, etc.) provides the urgency signal for findings beneath it (HIGH → 🟡 HIGH, MEDIUM → 🟢 MEDIUM, LOW → ⚪ LOW, CRITICAL → 🔴 CRITICAL). To avoid prompt fatigue on reports with 10+ findings, the user prompt rolls up per-report rather than per-finding: "Import N findings from `<audit-file>`?" with a yes / no / per-finding-review choice.

**Output format:** report each match as a one-line candidate (`<file>: <heading text> (heuristic <N>)`) under a `📄 General documentation` group in the Phase 2 summary. Audit-report files (heuristic 7) report as a single grouped line per file: `<file>: N findings (heuristic 7)`. Counts roll up the same way as the six core surfaces.

---

## Audit-tool format-aware parsing

For **radar-suite v3+** (the supported version; pin compatibility to v3 and above), the deferred-work source is split across two files per audit run:

- `scratch/audit-<domain>-YYYY-MM-DD.md` is the per-finding source. These are markdown reports containing the actual deferred items in prose form, with severity tags (🔴 / 🟡 / 🟢), heading-level findings, and inline file:line references. Real radar-suite filenames look like `audit-concurrency-2026-04-25.md`, `audit-codable-2026-03-31.md`, `audit-energy-2026-02-28.md`. Use prose heuristics to extract Finding text + urgency from each section. The earlier v3 alpha pattern `*-radar-*-YYYY-MM-DD.md` is no longer current; do not match on it.
- `.radar-suite/ledger.yaml` is read for audit-run metadata only. Map: `audit_started` → row date stamp; `sessions[].skill` → audit-tool name (which radar skill produced the finding); `sessions[].timestamp` → recency signal for staleness scoring. Do NOT attempt to extract per-finding rows from `ledger.yaml`; the v3 schema records audit-run summaries (counts, grades, baselines), not individual findings.
- **Hardcoded allowlist inside `.radar-suite/`:** only `ledger.yaml` is read. All other yaml files (`*-handoff.yaml`, `project.yaml`, `session-prefs.yaml`, plus any future schema additions) are inter-skill state or config and are explicitly skipped, even if they contain words like "deferred" or "pending" in their bodies. The allowlist is the safety net: when radar-suite adds new yaml files in future versions, the skill defaults to ignoring them rather than mis-importing them.

For **other known formats** (`.eslint-todos`, etc.), parse the structured fields (`status`, `urgency`, `severity`, `file:line`) directly so Phase 4 auto-fill can populate columns from real signals.

For **unknown audit formats**, fall back to filename-based heuristics and flag the rows as needing manual review.

---

## Cross-surface deduplication

Before producing the candidate report, run a fuzzy-match dedup pass. If the same item appears in Deferred.md AND a plan file AND a memory file (common, e.g., a paused migration shows up in all three), merge into ONE candidate row with the multi-source pointer recorded in the Finding cell. Without this step, the survey produces 3x duplicate rows for the same logical item.

**Preferred implementation:** delegate dedup to the helper script:

```
python3 scripts/dedup_findings.py --candidates <file.json>
```

Reads the JSON candidate list emitted by `scan_surfaces.py` (or any equivalent producer); writes a JSON list with merged duplicates and `sources: [...]` arrays on each merged candidate. Algorithm: token-based similarity on the Finding headline; threshold and tie-breaking documented in the script header.

---

## GitHub issues — four states, not two

- `gh` not installed: "GitHub issues skipped (`gh` CLI not available)"
- `gh` installed but `gh auth status` fails: "GitHub issues skipped (`gh` not authenticated; run `gh auth login` to enable)"
- `gh` available but project is not on GitHub: "GitHub issues skipped (project not on GitHub)". Detection runs before invoking `gh`. Conditions: `git rev-parse --git-dir` succeeds AND `git remote get-url origin 2>/dev/null` returns a URL containing `github.com`. If either check fails (no `.git/` directory, missing `origin` remote, or `origin` points at GitLab / Bitbucket / a self-hosted Git server), surface this fourth state and skip the `gh` invocation entirely.
- `gh` authed and project is on GitHub but `gh issue list` returns empty: "GitHub issues: 0 open issues with deferral labels found"

The spec must distinguish these so the user knows whether the surface is silent because empty or silent because broken. The fourth state matters because invoking `gh issue list` against a non-GitHub repo prints a confusing error rather than a clean "skipped" status.

---

## Algorithm fallback (Python unavailable)

When `python3` is not on PATH, the skill falls back to LLM-driven enumeration of the surfaces above. The cost is determinism (the same surface scanned in two sessions can return slightly different candidates) and speed (the model re-derives the algorithm from this prose every call). The fallback is functional but inferior; install Python 3.9+ for the canonical implementation.

The fallback procedure:

1. **Scan filesystem.** For each of the six surfaces, walk the conventional directories listed in the surface table above. Apply the universal exclusion rule (skip archive paths, `.git/`, `node_modules/`, `vendor/`, `Pods/`).
2. **Filter candidates per surface.** Apply the filename regex / content heuristic / structured-field parse documented in the surface row.
3. **Apply per-surface pre-checks** in order: redirect-pointer pre-check (Surface 1), meta-doc pre-check (Surface 6), heuristic-7 audit-report scope check (Surface 1b).
4. **Emit grouped candidate report** in the format shown at the end of `reference/init.md` § Phase 2.
5. **Run cross-surface dedup** by comparing Finding headlines pairwise; merge candidates with substantial token overlap (~70% Jaccard similarity on tokenized headlines).

The fallback is safe to use for one-off init runs on small projects but should not be relied on for repeat imports — the non-determinism compounds across sessions.
