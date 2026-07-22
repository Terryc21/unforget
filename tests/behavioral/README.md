# tests/behavioral/ — behavioral-golden corpus

The `tests/` script corpus (one level up) diffs the **deterministic helpers**
under `scripts/` against golden JSON. That is the easy half. The hard half —
and where unforget's real regressions live — is the **prose the LLM follows**:
`add` picking the right section and defaults, `edit` preserving the four-part
detail-block order, `promote` refusing to ship past an open 🔴 THIS row, the
format-version contract refusing writes on a future-version file. None of that
is a script; it is instructions a model executes, and a refactor like the
v0.2 monolith→router split can silently break it while every script golden
still passes.

This corpus tests that layer. It cannot exact-diff (LLM output varies in
wording and whitespace), so instead each case ships **structural assertions**
that a correct result must satisfy, checked by `check_behavioral.py`.

## Layout

Each `NN-name/` case directory holds:

| File | Role |
|---|---|
| `input.md` | The starting `UNFORGET.md` the command runs against. |
| `command.txt` | The exact `/unforget …` line to run. |
| `assertions.txt` | Structural invariants a correct result must satisfy (grammar below). |
| `expected.md` *(optional)* | A hand-written reference result, for humans reading the diff. Not diffed mechanically. |
| `result.md` | **Produced per run** by the LLM half. Git-ignored; never committed. |

## The two halves

The LLM half is not automatable from a plain shell — it needs a Claude Code
session. So running a case is a short manual (or session-driven) loop:

1. Copy the case's `input.md` into a scratch project as `UNFORGET.md`.
2. In a Claude Code session in that project, run the line from `command.txt`.
3. Copy the resulting `UNFORGET.md` back to the case dir as `result.md`.
   *For interactive commands (`promote`), save the assistant's **reported
   output** as `result.md` instead — those cases assert on what the skill
   said, not on a file write. Each `assertions.txt` says which.*
4. Run the checker: `bash run-behavioral.sh --check`.

The checker half is fully automated and CI-safe:

```bash
bash run-behavioral.sh --check      # check every case that has a result.md; SKIP the rest
bash run-behavioral.sh --list       # print each case's command (drives the LLM half)
bash run-behavioral.sh --selftest   # prove the checker discriminates (no LLM needed)
```

`--check` never fails on a missing `result.md` (reports SKIPPED), so it is safe
to run in CI where the LLM half hasn't been performed. `--selftest` is the
guard-that-guards-the-guard: it synthesizes a known-good and known-bad result
for a canary case and confirms the checker passes the first and fails the
second. Run it after any edit to `check_behavioral.py`.

## Assertion grammar (`assertions.txt`)

One assertion per line; blank lines and `#` comments ignored.

| Assertion | Meaning |
|---|---|
| `contains <substring>` | result contains the literal substring |
| `absent <substring>` | result does **not** contain the substring |
| `regex <python-regex>` | result matches the regex (MULTILINE) |
| `row_in_section <N> <ID>` | a table row with first cell `<ID>` appears under section `<N>`'s header |
| `cell <ID> <COL> <VALUE>` | the row for `<ID>` has `<VALUE>` in column `<COL>` (COL = header text, e.g. `Target`; VALUE matched as a substring so emoji cells like `🔴 THIS` match on `THIS`) |
| `detail_order <ID>` | the detail block for `<ID>` keeps four-part order (closure → body → verify → spawn), skipping absent parts |
| `unchanged_from <path>` | result is byte-identical to `<path>` (refusal cases: nothing was written) |

## Seed cases

| Case | Exercises | Key assertion |
|---|---|---|
| `01-add-session-spillover` | `add` with no flag defaults to Section 2 | `row_in_section 2 S2` |
| `02-add-audit-section` | `add --section=3` routes to Audit findings | `row_in_section 3 A2` |
| `03-edit-target` | `edit --target=THIS` changes only that cell | `cell A1 Target THIS` + neighbors untouched |
| `04-edit-status-fixed` | `edit --status=Fixed` prepends a CLOSED pointer | `detail_order S1` |
| `05-promote-blocked-by-open-this` | `promote` won't silently ship an open 🔴 THIS | names the blocker (assert on reported output) |
| `06-format-version-refusal` | a `v2` file refuses writes | `unchanged_from input.md` |

## Adding a case

1. `mkdir NN-name`, drop in `input.md`, `command.txt`, `assertions.txt`.
2. Prefer assertions that pin **structure and enums**, not exact prose — the
   LLM's wording is not contractual, its column values and placement are.
3. If your case has a clean deterministic answer, add an `expected.md` for the
   human reader.
4. Run `--selftest` if you touched the checker, then run your case.
