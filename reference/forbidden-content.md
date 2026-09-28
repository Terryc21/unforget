# The forbidden-content guard: declared types, surfaced as advisory

## The honesty this spec keeps (read first)

`UNFORGET.md` is the file where deferred work accumulates, which makes it the
file most likely to acquire something that should not be written down: a
credential fragment, a customer name, an internal hostname, a private path.
This guard is the cheapest place to notice that, because it sits on the write
path and the write is where a value gets committed to a file that other tools
then read, summarise, mirror, or publish.

Three limits, stated before the design so they aren't discovered later:

1. **This is not a scanner.** It never reads the ledger, the repo, or git
   history. It checks the text handed to it. A secret that is already in the
   ledger is not found by this guard — only one about to be *added* is.
2. **This is not a redactor.** It never rewrites text. It reports a type and
   hands the decision back to the caller, which is the only party that knows
   whether the value was a real secret or a quoted one.
3. **Regexes are the repo's, and regexes are weak.** A determined secret
   split across two fields, base64'd, or written in prose will pass. This
   raises the cost of an accident. It is not a control you rely on alone.

## Where the guard sits

It fires at exactly two places: **`add` and `edit`**, at the moment row text is
assembled and before the write.

```
candidate row text
        │
   ┌────▼─────────────────────────────┐
   │  FORBIDDEN-CONTENT GUARD         │
   │  1. load declared types          │
   │  2. scan → matched TYPE NAMES    │
   │  3. report; never echo the text  │
   └────┬─────────────────────────────┘
        │ (clean → proceed; match → advisory or refusal)
        ▼
   write, or hand back for paraphrase
```

Its *strictness* is **the registry global** (`policy_redaction`), read the same
way the deferral gate reads `policy_deferral`; its *mechanism* is
`scripts/guard_scan.py`. The guard never **writes**; the caller's subcommand
decides what a finding means (see §4).

`list`, `scan`, and `show` never invoke it — they read, they don't write.

## §1 — Declaration

A repo-local `.unforget-guard.json` in the ledger directory:

```json
{
  "policy_redaction": "warn",
  "forbidden_types": [
    {"name": "credential-fragment", "pattern": "sk-[A-Za-z0-9]{16,}"},
    {"name": "private-hostname",   "pattern": "\\b[a-z0-9-]+\\.internal\\b"}
  ]
}
```

Each entry needs `name` and `pattern`. The **name is the interface**: it is what
gets reported, and what a human reads to decide whether the finding is real.
Names should be short, hyphenated, and say what the *category* is, never what
the value is.

An absent file means "this repo declares nothing" and the guard is a no-op.

## §2 — Policy (registry global, set at init / start-of-run)

| `policy_redaction` | Behaviour on a match |
|---|---|
| **off** (default) | Nothing is checked. The default, so existing repos are unaffected. |
| **warn** | `advisory` names the type. The write proceeds. |
| **block** | `advisory` names the type. The write is refused; the caller paraphrases. |

Read from the registry global block (per `reference/registry.md`), with
`.unforget-guard.json`'s own `policy_redaction` taking precedence so a repo can
pin the behaviour without a registry edit. Unset anywhere = `off`.

## §3 — Report the type, never the text

**This is the load-bearing rule, and it is not negotiable.**

```json
{"checked": true, "policy": "block", "clean": false,
 "types": ["credential-fragment"],
 "advisory": "forbidden content matched (credential-fragment) — the write is
  refused. Paraphrase to describe the problem without the value; do not repeat
  the matched text."}
```

A guard that prints the match re-leaks the thing it caught, and worse, it puts
that text into the agent's context, from where it can be echoed into a row, a
commit message, or a summary. `tests/test_guard_scan.py` asserts this against
the literal secret bytes, so a regression fails the suite rather than shipping.

## §4 — What a finding means (the caller's job)

The guard is deterministic: it answers "did a declared type match?". Deciding
what to do is the LLM's, guided by this spec:

- **warn, and the match was a real value** → rewrite the row to describe the
  *problem* ("the staging deploy key was pasted into a runbook") without the
  value. Do not repeat the matched text in the rewrite.
- **warn, and the match was a false positive** → say so and proceed. A quoted
  error message or a regex that matches ordinary prose is not a finding.
- **block** → do not write. Either paraphrase, or ask the user to narrow the
  pattern. Never disable the policy to get a write through.

A guard that fires on everything trains people to switch it off, which is worse
than no guard. When a pattern is too broad, the fix is the pattern.

## §5 — Failure modes are loud

A declaration that cannot be honoured is a **usage error (exit 2)**, never a
silent pass:

| Case | Result |
|---|---|
| Unreadable or non-JSON config | exit 2, message names the path |
| Config is not an object | exit 2 |
| Entry missing `name` or `pattern` | exit 2 |
| **Invalid regex** | exit 2, message names the type |

The invalid-regex row is the one that matters most. A typo'd pattern compiles
to something that matches nothing, and a guard that silently matches nothing is
indistinguishable from a repo with nothing to declare — the exact failure this
guard exists to prevent. So a bad pattern is loud, always.

## §6 — Worked examples

| Candidate | Declared | Result |
|---|---|---|
| "Retry logic swallows the underlying error" | credential, hostname | clean; `checked: true` |
| "key `sk-ABC…` rotated" | credential | `credential-fragment`; block refuses |
| "deploys to billing-api.internal" | credential, hostname | `private-hostname` only |
| anything, no `.unforget-guard.json` | — | `checked: false`, exit 0 |
| anything, `policy_redaction: off` | credential | `checked: false`, exit 0 |
| anything, `pattern: "([unclosed"` | — | exit 2, usage error |

## §7 — Anti-patterns (what this must NOT become)

- **Not a scanner.** No repo walk, no git history, no ledger re-read. That job
  belongs to a secret-scanner, which does it better.
- **Not a redactor.** Silent rewriting of a row is worse than refusing it: the
  agent then doesn't know the value was there.
- **Not a hard block on `warn`.** Two tiers exist so the safe one is the default.
- **Not a place for repo-specific rules.** The mechanism is generic (secrets,
  private hosts, internal paths). What a given repo forbids is that repo's
  declaration, not engine code.
- **Never echo the match.** §3, restated because it is the one rule that makes
  this safe to ship.

## Preferred implementation

```
# check candidate text against the repo's declared types:
python3 scripts/guard_scan.py --dir <ledger-dir> --stdin   # or --text "..."

Output: {"checked": bool, "policy": str, "clean": bool,
         "types": [str], "advisory": str}

Exit codes:
  0  ok / no match / nothing declared
  1  a declared type matched (warn or block)
  2  usage error / unreadable or malformed declaration
```

Stdlib only. The check is cheap (one compiled regex per declared type over one
string) and belongs on the write path unconditionally — an `off` policy returns
`{"checked": false}` without compiling anything.
