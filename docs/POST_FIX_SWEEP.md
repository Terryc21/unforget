# The post-fix sweep — a three-skill workflow

`unforget` pairs with two companion skills ([radar-suite](https://github.com/Terryc21/radar-suite) and [bug-echo](https://github.com/Terryc21/bug-echo)) to form a high-leverage loop: **surface → verify → generalize**. The loop catches a class of bugs that no single audit tool finds: **bugs that haven't crashed yet but have the same shape as one that just did**.

## The three stages

1. **Surface** — `/unforget` shows you a deferred row you're about to mark Fixed.
2. **Verify** — Before trusting the closure, confirm the fix is real. Use `/radar-suite` (or read the file directly) to check that the anti-pattern is actually gone from the current code. Stale Open rows are surprisingly common; a fix can ship without anyone updating the ledger.
3. **Generalize** — If the fix replaced an anti-pattern with a corrected pattern, the same anti-pattern likely lives elsewhere in your codebase. Run `/bug-echo` with a one-sentence description of what the fix replaced. bug-echo scans the whole codebase for the same shape and rates each match.

## Why this is different from running an auditor cold

A standard audit skill matches code against a catalog of known anti-patterns assembled in advance. The catalog reflects what the audit author thought was a bug at the time the rule was written.

The post-fix sweep matches code against an anti-pattern that **just demonstrated it was a real bug in your specific codebase**. The fix is the proof. After-the-fact pattern matching beats theoretical pattern matching every time, and it's the systematic way to find unfired bugs sitting under the same conditions that just produced a real one.

## Worked example (from the unforget development codebase)

| Stage | Command | Result |
|---|---|---|
| Surface | `/unforget` | Showed an Open row "iPhone crash tap item: collapsibleSectionsStack" that had been Open for a month |
| Verify | `/radar-suite focus on collapsibleSectionsStack` | Reported the bug had actually shipped fixed weeks earlier in two specific commits. Current code already had the corrected pattern. The row was stale. Closed as Fixed. |
| Generalize | `/bug-echo "VStack with 12+ if-conditional children in one scope can crash on physical iPhone"` | Found one BUG (a list-row view with 16 children in its type tree, identical conditions to the original) and three WATCH sites at 10–12 conditionals each. Fixed the BUG with the same split pattern; documented the WATCH sites with defensive comments. |

Total time: ~90 minutes. The list-row bug had never crashed because users hadn't accumulated enough records yet, but the runtime conditions were identical to the original. It would have hit a real user eventually. The post-fix sweep caught it before that.

## When to skip the loop

- Trivial fixes (typos, single-character changes, isolated state edits)
- Fixes to one-off code with no callers
- Cleanup of an already-failed migration where the pattern is on its way out

## Companion skill installs

| Skill | What it adds | URL |
|---|---|---|
| **radar-suite** | Verifies the closure is real; multiple audit dimensions | `https://github.com/Terryc21/radar-suite` |
| **bug-echo** | Generalizes the fix; rated report of every echo | `https://github.com/Terryc21/bug-echo` |

When you mark a row Fixed in unforget, the closure flow detects which of these are already installed and only shows install URLs for the ones missing — a clean prompt for users who already have everything, a self-bootstrapping prompt for users who don't.
