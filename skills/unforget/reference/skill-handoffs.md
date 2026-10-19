# Companion skill handoffs

> Authoritative spec for how unforget recommends OTHER skills at earned ledger
> transitions (format v2+, from the Companion Skill Handoffs design). The
> recommendation points at a **capability (a function)**, never a hardcoded
> skill+URL scattered through trigger points — so a companion link rots in ONE
> place (the manifest), never twelve. Earned, contextual, advisory, gracefully
> degrading, and with disclosed (not covert) self-promotion.

## Why function-based, not skill-based

The core principle, each point learned from a real failure:

- **Link rot has one address, not twelve.** A URL baked into every trigger is the
  stale-pointer failure with a longer fuse. The manifest holds the link once;
  triggers reference the *function*.
- **The landscape is plural.** A user who prefers an Axiom auditor for post-fix
  scanning maps the function to it in one edit — unforget is not married to one
  skill roster.
- **Graceful degradation.** Recommend the *function*; install-state decides how it
  is expressed (run the command if installed; one soft pointer if not). unforget
  works fully with **no manifest at all** — handoffs simply don't fire.
- **Injection hygiene.** A tool that reflexively emits "install code from this URL"
  is the *shape* of a malicious skill. Function-based + install-state-checked +
  single-manifest keeps URL surfacing rare, transparent, and user-sourced.

## §2 — The five functions (fixed; unforget owns the left column)

| Function slug | Fires at this ledger transition | Shipped-default skill |
|---|---|---|
| `post-fix-sibling-scan` | a row closes with a **code change** | bug-echo |
| `ship-risk-scoring` | a **🔴 THIS** row nears promote/release | one-star-risk |
| `audit-reverify` | an **audit-finding** row is being closed | radar-suite |
| `forward-bug-hunt` | the deferral gate **can't infer a pattern** / no recent fix | bug-prospector |
| `verify-against-reality` | `verify` finds a **done-verified w/o device/user evidence** | (unset — suggest one) |

Kept to five deliberately — more becomes an unmaintained catalog (the branching
over-branching failure, applied to functions). Each firing is **earned**: it maps to
a specific transition on a specific row, and the recommendation names the reason
("you just marked a code-fix done → this finds its siblings"), never a generic "you
might like these skills" footer.

## §3 — The manifest (global default, projects inherit)

A `function → skill → invoke → url` table. The left column is fixed (the five
functions); the right columns are user-owned. It lives in ONE global file —
`~/.claude/unforget-companions.md` — marker-delimited so the skill rewrites only
between its markers. Projects **inherit** it (the per-project registry references it,
does not copy it); a project may override a single row locally in its registry if it
genuinely needs a different skill there (rare). **The global manifest is the ONLY
place a companion URL is written** — nothing else in unforget hardcodes a link.

### The shipped default (disclosed, not covert)

unforget SHIPS a default manifest mapping the functions to the author's companion
skills (bug-echo, one-star-risk, radar-suite, bug-prospector; the fifth ships
**unset** with a suggestion). This is self-promotion, and the disclosure is
**mandatory at init**:

> The default manifest recommends the author's companion skills. It is
> user-overridable in one place (the global manifest), and unforget functions fully
> with **no manifest at all** — handoffs simply don't fire. Swap any mapping freely;
> map a function to an Axiom skill or any other, or unset it.

A tool that silently steered users to its author's products would be the bad
version. A tool that says "here's my suggested set, swap freely, I work without it"
is the honest one.

## §4 — Install-state detection (the anti-stale-link mechanic)

**Installation is checked at RECOMMEND-TIME, not read from the manifest.** The
manifest says what *should* fill a function; whether it's actually available is
checked live.

### Detect by INVOCABLE NAME, not directory name

⚠️ **The one-star-risk lesson (2026-07-25):** detecting "is skill X installed?" by
`find`-ing a directory named X is UNRELIABLE — the invocation name ≠ the plugin/dir
name. `bug-echo`, `radar-suite`, `bug-prospector` resolved as plugin dirs, but
`one-star-risk` did NOT match a dir of that name despite being invocable (it's under a
different plugin name). **Detection MUST key off the invocable skill name** — what
the session's skill/command list reports — never a filesystem `find`.

Implementation: the LLM knows the session's available-skills list; it passes that list
to the resolver (`companions.py resolve --invocable "<names>"`), which does the
manifest lookup + the three-state logic against it. The script never does a dir find.

### The three expression states

| Install state | What the handoff says |
|---|---|
| **Installed** (invocable) | Recommend the ACTION: "Run `/bug-echo` — you just fixed a pattern; it'll find siblings." **No URL.** |
| **Not installed, manifest has a URL** | ONE soft pointer: "`post-fix-sibling-scan` isn't installed — `bug-echo` fills it (URL)." URL surfaced from the manifest only. |
| **Function unset in manifest** | "No skill mapped for `post-fix-sibling-scan` — consider mapping one." **No URL invented.** |

### Rot detection (ties to `verify`)

`verify` gains a manifest check: an entry whose skill is neither invocable NOR carries
a URL → flag ("companion `X` for `<function>` is neither installed nor reachable —
update the manifest"). An **unset** function is NOT rot — it's an honest gap. Rot is
*detected*, never silently served.

## §5 — Frequency governance (don't become spam)

Same restraint as branching's auto-suggest and the deferral flag — earned, rare,
advisory:

- **At most once per function per session.** Closing ten code-fixes offers the scan
  once, batched ("3 code-fixes closed this session — run `post-fix-sibling-scan`?").
- **Only on high-value transitions.** **A trivial close fires NOTHING.** (This is the
  hard rule: a one-line typo fix does not trigger a sibling scan.)
- **Advisory, never blocking, never a dependency.** unforget runs fully standalone; a
  handoff is an offer the user ignores freely.
- **Never a way to DEFER the real check.** A handoff suggests doing MORE
  verification/scanning **now, while context is hot** — "I'll run bug-echo later"
  logged as a row is deferral-laundering, the exact thing the gate targets. The
  handoff's whole point is do-it-now.

## §6 — The transitions (where handoffs fire)

| Transition | Function fired |
|---|---|
| `edit --status=done` on a **code fix** (non-trivial closure) | `post-fix-sibling-scan` |
| `edit --status=done` on an **audit-finding** row | `audit-reverify` |
| `promote` / a 🔴 THIS row nears release | `ship-risk-scoring` |
| deferral gate finds **no pattern to infer** | `forward-bug-hunt` |
| `verify` finds a **done-verified w/o device/user evidence** | `verify-against-reality` |

## Preferred implementation

```
# seed the shipped default manifest at init (idempotent; discloses):
python3 scripts/companions.py init [--file <manifest>]

# resolve a function at a transition, given what the session reports invocable:
python3 scripts/companions.py resolve --function post-fix-sibling-scan \
    --invocable "<comma-separated invocable skill names>"

# rot check (called by verify):
python3 scripts/companions.py rotcheck --invocable "<names>"
```

`resolve` returns `{function, skill, state, invoke, url, expression, advisory}` — say
the `expression` verbatim (it already encodes the earned reason and the correct
state). The `--invocable` list is the AUTHORITATIVE install signal (§4a) — the LLM
supplies it from the session's available-skills list, never a dir find. Governance
(once/function/session, skip on trivial) is the LLM's to enforce per §5; the script is
stateless and resolves a single function on demand.

**Algorithm fallback** (Python unavailable): read the five-row manifest table from the
global `unforget-companions.md`. For the function that just fired, look up its skill;
if that skill name is in the session's invocable-skill list, recommend the invoke
command with no URL; if not and a URL is present, give one soft pointer with the URL;
if the function is unset, say so and invent no URL. Fire at most once per function per
session, and never on a trivial close.
