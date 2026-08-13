<!-- unforget-format: v2 -->
# Examples

A sanitized-but-real UNFORGET.md in **format v2**. The Status cell leads with a
machine-readable `@status:` token (and, on a "done", a `@verified:` tier) so tools read
the token, never the prose — a row can't quietly contradict itself, and a "done" isn't
done until it's checked. This file also shows the optional **`1-Star Risk`** 11th column
(most rows are `⚪ n/a`; the value is the risky few).

## 1. Paused plans

Plans that started, made some progress, and were intentionally paused.

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast      | Effort | Status | 1-Star Risk |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|------------|--------|--------|-------------|
| P1 | 🟡 LATER   | Schema v3 migration paused (rollback path unclear)   | 🟢 MED  | 🟡 High | 🟢 Med  | 🟢 Good      | 🟢 ~7 fls  | Med    | `@status:blocked` rollback path unclear | `risk‹───────────›clear`<br>⚪ n/a |
| P2 | 🔵 NEXT    | Test suite: 23 flaky tests, 4 root causes            | 🟡 HIGH | ⚪ Low  | 🟢 Med  | 🟠 Excellent | 🟡 ~10 fls | Med    | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |
| P3 | 🔴 THIS    | Wallet pass server signing not yet implemented       | 🟡 HIGH | 🟢 Med  | 🟡 High | 🟠 Excellent | 🟢 ~4 fls  | Med    | `@status:done-verified` `@verified:device` menu hidden, build 13 | `risk‹────★──────›clear`<br>🟡 Watch (mid) |
| P4 | 🟡 LATER   | Search relevance overhaul (phases 1-4 done, 5-7 TBD) | 🟢 MED  | 🟢 Med  | 🟢 Med  | 🟢 Good      | 🟡 ~8 fls  | Lrg    | `@status:in-progress` → history in detail block | `risk‹───────────›clear`<br>⚪ n/a |
| P5 | ⚪ SOMEDAY | Third-party API access rejected 2026-03-10           | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | ⚪ 0 fls   | Triv   | `@status:withdrawn` using public OAuth tier instead | `risk‹───────────›clear`<br>⚪ n/a |
| P6 | 🔵 NEXT    | Wallet pass: build server signing endpoint           | 🟢 MED  | 🟢 Med  | 🟢 Med  | 🟢 Good      | 🟢 ~4 fls  | Med    | `@status:open` | `risk‹─────★─────›clear`<br>🟡 Watch (mid) |

### Detail - Paused plans

- **P1** - Migration to v3 schema crashed at app launch with "Duplicate version checksums detected." V2 and V3 reference same model types -> identical checksums. Blocked: three resolution options open (fork V2, custom stage, defer entirely), none picked. Plan: `~/.claude/plans/v3-migration.md`. Files: 5 models + AppSchema + migration plan.
- **P2** - Plan with full root-cause grouping at `Documentation/Deferred/test-suite-failures.md`. Group A (race conditions) closed 2026-04-12. Re-run full suite first per Pickup Workflow.
- **P3** - **CLOSED 2026-04-20: hid the menu entry until server signing lands. Spawns: P6.** `@verified:device` — confirmed on device that the Wallet menu no longer appears. Every item that showed the Wallet feature failed when the user completed the flow. Blocked on server `/api/wallet/sign-pass` + Apple Pass Type ID. Pre-submission decision: complete the worker endpoint OR hide the menu item (~30 min if hiding). Chose hiding for build 13; future endpoint work tracked at row P6. **1-Star Risk 🟡 Watch:** a half-built payment/wallet feature reaching a user is a classic one-star trigger; hiding it drops the exposure but the endpoint work (P6) is why it's not yet Clear.
- **P4** - Bounded index row; full history here (this is the row-length-discipline split — the table cell stays a one-liner, the history lives in the block). Phases 1-4 shipped + deployed (commits `45f90604`, `38aacfca`). In progress: Phase 5 (Best Buy + PCGS sources). Pending: Phase 6 (manual fallbacks) and 26 audit findings (1 CRITICAL / 9 HIGH / 11 MEDIUM / 5 LOW from the 2026-04-01 audits). Plan: `~/.claude/plans/search-overhaul.md`.
- **P5** - **WITHDRAWN 2026-05-01: not pursuing the third-party tier.** Reopen window closed 2026-05-15; the working alternative ships via the public OAuth tier, so this is superseded rather than deferred. External dependency (no project files affected).
- **P6** - **Spawned-from: P3.** Server endpoint, Pass Type ID, and client wiring needed before the Wallet feature can re-enable. 4-phase plan in `Documentation/Deferred/wallet-pass-archive.md` (Apple Developer Portal, Worker endpoint, Client update, Testing). Currently hidden from UI by `Sources/ViewModels/WalletViewModel.swift:244` early-return. Restore by deleting that line. **1-Star Risk 🟡 Watch:** re-enabling a payment path is exactly where a signing bug becomes a one-star review; ship it only once the endpoint is device-verified.

---

### Example row

| P0 | 🔴 THIS | Example: short finding under 50 chars | 🟡 HIGH | 🟢 Med | 🟡 High | 🟠 Excellent | 🟢 ~3 fls | Med | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |

The Finding is a one-clause **index**; full context lives in the Detail block under `P0`.
When a Finding or Status cell would outgrow ~400 chars, the history moves to the detail
block (losslessly) and the row stays a bounded one-liner — see P4 above.

### Column reference

| Column | Meaning |
|---|---|
| **#** | Stable ID. Format: section prefix + integer (P1, S2, A3, U4). Never reuse. Never renumber. |
| **Target** | Release-cycle commitment. See "Target values" below. |
| **Finding** | One-clause description, ≤50 chars. |
| **Urg** | Urgency: 🔴 CRITICAL / 🟡 HIGH / 🟢 MED / ⚪ LOW |
| **RFix** | Risk: Fix. ⚪ Low / 🟢 Med / 🟡 High / 🔴 Critical |
| **RNo** | Risk: No Fix. Same scale as RFix. |
| **ROI** | Return on effort. 🟠 Excellent / 🟢 Good / 🟡 Marginal / 🔴 Poor |
| **Blast** | Blast Radius. ⚪ 1 fl / 🟢 2-5 fls / 🟡 6-15 fls / 🔴 >15 fls |
| **Effort** | Triv / Sml / Med / Lrg |
| **Status** | `@status:` token first, then optional narration. Enum: `open` · `in-progress` · `done-verified` · `done-unverified` · `blocked` · `withdrawn`. A `done-verified` needs a `@verified:` tier of `device` or `user` (or `code` with a note); `session-claimed` can never back it. |
| **1-Star Risk** *(optional 11th)* | Exposure to an App Store one-star review, as a risk strip (`At risk · Watch · Clear`) with a `★` marking the band. Appended, not core — omit it if you don't ship a public app. Advisory only; never drives the ship-gate. |

### Status tokens at a glance (what this file shows)

| Token | Means | Archivable? |
|---|---|---|
| `@status:open` | not started | no |
| `@status:in-progress` | actively being worked | no |
| `@status:done-verified` `@verified:device`/`user` | fixed AND checked against ground truth | **yes** |
| `@status:done-unverified` `@verified:code` | fixed / claimed, NOT yet ground-truth-checked (the "done-but-owed" state) | **held back** |
| `@status:blocked` | can't proceed; narration names the blocker | no |
| `@status:withdrawn` | retracted / not-a-bug / superseded | **yes** |

### Target values

| Target | Meaning |
|---|---|
| 🔴 **THIS** | Must ship in current release cycle. Blocks submission. |
| 🔵 **NEXT** | First post-release point update. |
| 🟡 **LATER** | Two cycles out or more. |
| ⚪ **SOMEDAY** | No commitment. Captured so it doesn't get lost. |

**Invariant:** `🔴 THIS` is the only Target that blocks shipping. A `🔴 THIS` row still
counts as a blocker unless its token is `done-verified` or `withdrawn` — a
`done-unverified` THIS row is NOT proven, so it still blocks.

### The `1-Star Risk` strip

The strip is one unbroken inline-code span (spaces would let the column wrap), paired
with the band glyph + zone word on the next line so color is never the only cue:

```
`risk‹★──────────›clear`<br>🔴 At risk (deep)      — riskiest; ★ deep in the At-risk third
`risk‹─────★─────›clear`<br>🟡 Watch (mid)          — middle band
`risk‹──────────★›clear`<br>🟢 Clear (border)       — safe; ★ at the Clear border
`risk‹───────────›clear`<br>⚪ n/a                   — not a user-visible App Store risk
```

The **band** (🔴/🟡/🟢/⚪) is firm; the star's position within it is only a *lean*
(`deep` / `mid` / `border`), never a percentage. Most rows are `⚪ n/a` — paused plans,
internal spillover, and audit findings usually aren't user-facing risks.

---

## 2. Session spillover

Items that surfaced mid-task in some other session. Captured here in 1-2 lines so they don't get lost.

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast     | Effort | Status | 1-Star Risk |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|-----------|--------|--------|-------------|
| S1 | 🔵 NEXT    | Sentry breadcrumbs: 2 paths missing user_id          | 🟢 MED  | ⚪ Low  | 🟢 Med  | 🟠 Excellent | 🟢 2 fls  | Triv   | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |
| S2 | 🟡 LATER   | DateFormatter cached in 4 spots (perf, not correct.) | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | 🟢 4 fls  | Sml    | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |
| S3 | 🔵 NEXT    | Empty-state copy: 3 strings hardcoded English        | 🟢 MED  | ⚪ Low  | 🟢 Med  | 🟢 Good      | 🟢 3 fls  | Sml    | `@status:done-unverified` `@verified:code` strings extracted, not yet eyeballed on device | `risk‹────────★──›clear`<br>🟢 Clear (mid) |
| S4 | ⚪ SOMEDAY | Color asset catalog has 12 unused entries            | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | ⚪ 1 fl   | Triv   | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |

### Detail - Session spillover

- **S1** - Surfaced while debugging a TestFlight crash. `LoginManager.signOut()` and `OnboardingViewModel.complete()` clear the user_id from breadcrumbs before the next event fires, so subsequent crashes show empty user. Affects post-logout crash triage.
- **S2** - Found while reading code in PerformanceProfiler. Four call sites construct DateFormatter inside hot loops. Each construction is ~5ms. Move to lazy properties on the owning view models.
- **S3** - **`@status:done-unverified` `@verified:code` — the "done-but-owed" state.** Caught by manual scan: `Text("No items yet")`, `Text("Try a different search")`, `Text("All caught up!")` in three view files, none in `Localizable.xcstrings`. The strings are extracted and the catalog builds (code-verified), but nobody has confirmed the empty states still read right on a device — so this is NOT `done-verified` yet, and `archive` will hold it back until the device check happens. **1-Star Risk 🟢 Clear:** user-facing copy, but low exposure — worst case is an untranslated empty state, an annoyance rather than a one-star trigger.
- **S4** - 12 colors in `Assets.xcassets` have zero references. Cleanup is mechanical but easy to skip in routine PRs. Worth a 30-min cleanup pass before audit-readiness review.

---

## 3. Audit findings

Items from audit tools (linters, code review skills, custom audits) not fixed immediately.

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast      | Effort | Status | 1-Star Risk |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|------------|--------|--------|-------------|
| A1 | 🔴 THIS    | radar-suite: 3 force unwraps in critical paths       | 🔴 CRIT | 🟢 Med  | 🔴 Crit | 🟠 Excellent | 🟢 3 fls   | Sml    | `@status:done-verified` `@verified:code` guard + tests, commit `2ce6d3f5` | `risk‹★──────────›clear`<br>🔴 At risk (deep) |
| A2 | 🔵 NEXT    | radar-suite: ObservableObject + @Published (legacy)  | 🟢 MED  | ⚪ Low  | 🟢 Med  | 🟢 Good      | 🟡 ~9 fls  | Med    | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |
| A3 | 🟡 LATER   | code-review: 6 oversized files (>800 lines)          | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | 🟢 6 fls   | Med    | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |
| A4 | 🔵 NEXT    | radar-suite: try? swallowing errors in 14 spots      | 🟢 MED  | 🟢 Med  | 🟢 Med  | 🟢 Good      | 🟡 ~14 fls | Med    | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |
| A5 | ⚪ SOMEDAY | radar-suite: 47 async calls without .task modifier   | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | 🔴 >15 fls | Lrg    | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |

### Detail - Audit findings

- **A1** - **CLOSED 2026-04-18 commit `2ce6d3f5`. `@verified:code`** (pure-logic change: a guard replacing a force-unwrap, covered by new tests — code is ground truth here). radar-suite found three force unwraps in the payment flow: `PaymentManager.swift:204`, `ReceiptValidator.swift:88`, `SubscriptionStore.swift:156`. Two were on guaranteed-non-nil values (kept with documentation comments); one was a real crash risk (replaced with guard let + Sentry breadcrumb). Tests added for the converted path. **1-Star Risk 🔴 At risk (deep):** a force-unwrap crash in the *payment* flow is the highest-exposure one-star trigger there is — a user who can't complete a purchase and gets a crash is the review you fear. Now fixed, but the row records why it was ranked deepest.
- **A2** - radar-suite finding ID `MOD-001`. Migration path: ObservableObject + @Published -> @Observable macro. Spec: `Documentation/Architecture/Modernization.md`. Incremental approach - convert when touching a file, don't chase the chain.
- **A3** - code-review-tool flagged 6 files >800 lines. None are causing problems today; tracked for future split. List: `MainView.swift` (1240), `OrderManager.swift` (910), `SearchService.swift` (864), `SettingsView.swift` (823), `ChatViewModel.swift` (812), `ReportGenerator.swift` (806).
- **A4** - radar-suite finding ID `ERR-003`. Convert `try?` calls that silently swallow real errors. Use `ModelContext+Logging.swift`'s `fetchWithLogging()` helper. Targets are listed in the radar report.
- **A5** - radar-suite finding ID `ASY-008`. View-level async calls that should use `.task` modifier for auto-cancellation. Bulk migration; defer until a clean sprint.

---

## 4. User-reported / observed

Bugs noticed but not reproduced; friction observed.

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast    | Effort | Status | 1-Star Risk |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|----------|--------|--------|-------------|
| U1 | 🔵 NEXT    | iPad: keyboard doesn't dismiss on first sheet open   | 🟢 MED  | ⚪ Low  | 🟢 Med  | 🟢 Good      | 🟢 2 fls | Sml    | `@status:in-progress` reproduced, spike open | `risk‹──────★────›clear`<br>🟡 Watch (border) |
| U2 | 🟡 LATER   | macOS: window position not restored after hiber.     | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | 🟢 1 fl  | Sml    | `@status:open` | `risk‹───────────›clear`<br>⚪ n/a |
| U3 | ⚪ SOMEDAY | TestFlight: 1 user reported chart colors look wrong  | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | ⚪ 1 fl  | Triv   | `@status:blocked` awaiting user follow-up | `risk‹───★───────›clear`<br>🟡 Watch (mid) |

### Detail - User-reported / observed

- **U1** - Reproduced manually 2026-04-19 on iPad Pro 13" simulator (`@status:in-progress` — a repro exists but no fix yet). First time presenting `AddItemSheet`, the keyboard appears but Done button doesn't fire; subsequent opens work. Likely SwiftUI focus-state initialization race. **1-Star Risk 🟡 Watch (border):** a first-run input trap on iPad is user-facing friction a reviewer can hit on their very first session — near the At-risk border because it's on the *first* open, not a deep edge case.
- **U2** - macOS window saves position to UserDefaults, but hibernation seems to skip the save. Cosmetic only; no data loss. Affects `WindowGroup`-based apps on macOS 14+.
- **U3** - **`@status:blocked` — awaiting user follow-up.** TestFlight feedback from one user, no screenshot attached. Possibly a colorblind-accessibility issue with chart series colors (currently 3 of the 5 are warm colors, which can collapse for deuteranopia). Can't proceed without the user's follow-up. **1-Star Risk 🟡 Watch:** an accessibility complaint that reaches TestFlight can reach a review; mid-band because it's one unconfirmed report, not a reproduced defect.

---

## Cross-references

- v0.2 plan files in `~/.claude/plans/`
- Audit reports in `.agents/research/`
- Sentry dashboard for crash signal
- Companion skills (verify a closure, generalize a fix, score ship-risk) resolve through the global companion manifest — see the repo's `reference/skill-handoffs.md`.
