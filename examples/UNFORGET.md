# Examples

### Example row

| P0 | 🔴 THIS | Example: short finding under 50 chars | 🟡 HIGH | 🟢 Med | 🟡 High | 🟠 Excellent | 🟢 ~3 fls | Med | Open |

The Finding is a one-clause summary; full context lives in the Detail block under `P0` below.

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
| **Status** | One of: `Open`, `Fixed`, `Deferred`, `Skipped`. Do not invent new values. |

### Target values

| Target | Meaning |
|---|---|
| 🔴 **THIS** | Must ship in current release cycle. Blocks submission. |
| 🔵 **NEXT** | First post-release point update. |
| 🟡 **LATER** | Two cycles out or more. |
| ⚪ **SOMEDAY** | No commitment. Captured so it doesn't get lost. |

**Invariant:** `🔴 THIS` is the only Target that blocks shipping.

---

## 1. Paused plans

Plans that started, made some progress, and were intentionally paused.

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast      | Effort | Status   |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|------------|--------|----------|
| P1 | 🟡 LATER   | Schema v3 migration paused (rollback path unclear)   | 🟢 MED  | 🟡 High | 🟢 Med  | 🟢 Good      | 🟢 ~7 fls  | Med    | Deferred |
| P2 | 🔵 NEXT    | Test suite: 23 flaky tests, 4 root causes            | 🟡 HIGH | ⚪ Low  | 🟢 Med  | 🟠 Excellent | 🟡 ~10 fls | Med    | Deferred |
| P3 | 🔴 THIS    | Wallet pass server signing not yet implemented       | 🟡 HIGH | 🟢 Med  | 🟡 High | 🟠 Excellent | 🟢 ~4 fls  | Med    | Fixed    |
| P4 | 🟡 LATER   | Search relevance overhaul (phases 1-4 done, 5-7 TBD) | 🟢 MED  | 🟢 Med  | 🟢 Med  | 🟢 Good      | 🟡 ~8 fls  | Lrg    | Open     |
| P5 | ⚪ SOMEDAY | Third-party API access REJECTED 2026-03-10           | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | ⚪ 0 fls   | Triv   | Deferred |
| P6 | 🔵 NEXT    | Wallet pass: build server signing endpoint           | 🟢 MED  | 🟢 Med  | 🟢 Med  | 🟢 Good      | 🟢 ~4 fls  | Med    | Deferred |

### Detail - Paused plans

- **P1** - Migration to v3 schema crashed at app launch with "Duplicate version checksums detected." V2 and V3 reference same model types -> identical checksums. Three resolution options open (fork V2, custom stage, defer entirely). Plan: `~/.claude/plans/v3-migration.md`. Files: 5 models + AppSchema + migration plan.
- **P2** - Plan with full root-cause grouping at `Documentation/Deferred/test-suite-failures.md`. Group A (race conditions) closed 2026-04-12. Re-run full suite first per Pickup Workflow.
- **P3** - **CLOSED 2026-04-20: hidden the menu entry until server signing lands. Spawns: P6.** Every item that showed the Wallet feature failed when the user completed the flow. Blocked on server `/api/wallet/sign-pass` + Apple Pass Type ID. Pre-submission decision: complete the worker endpoint OR hide the menu item (~30 min if hiding). Chose hiding for build 13; future endpoint work tracked at row P6.
- **P4** - Phases 1-4 shipped + deployed (commits `45f90604`, `38aacfca`). Pending: Phase 5 (Best Buy + PCGS), Phase 6 (manual fallbacks), and 26 audit findings (1 CRITICAL / 9 HIGH / 11 MEDIUM / 5 LOW from 2026-04-01 audits). Plan: `~/.claude/plans/search-overhaul.md`.
- **P5** - Reopen window closes 2026-05-15. Working alternative ships via the public OAuth tier. External dependency (no project files affected).
- **P6** - **Spawned-from: P3.** Server endpoint, Pass Type ID, and client wiring needed before Wallet feature can re-enable. 4-phase plan in `Documentation/Deferred/wallet-pass-archive.md` (Apple Developer Portal, Worker endpoint, Client update, Testing). Currently hidden from UI by `Sources/ViewModels/WalletViewModel.swift:244` early-return. Restore by deleting that line.

---

## 2. Session spillover

Items that surfaced mid-task in some other session. Captured here in 1-2 lines so they don't get lost.

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast     | Effort | Status   |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|-----------|--------|----------|
| S1 | 🔵 NEXT    | Sentry breadcrumbs: 2 paths missing user_id          | 🟢 MED  | ⚪ Low  | 🟢 Med  | 🟠 Excellent | 🟢 2 fls  | Triv   | Open     |
| S2 | 🟡 LATER   | DateFormatter cached in 4 spots (perf, not correct.) | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | 🟢 4 fls  | Sml    | Open     |
| S3 | 🔵 NEXT    | Empty-state copy: 3 strings hardcoded English        | 🟢 MED  | ⚪ Low  | 🟢 Med  | 🟢 Good      | 🟢 3 fls  | Sml    | Open     |
| S4 | ⚪ SOMEDAY | Color asset catalog has 12 unused entries            | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | ⚪ 1 fl   | Triv   | Open     |

### Detail - Session spillover

- **S1** - Surfaced while debugging a TestFlight crash. `LoginManager.signOut()` and `OnboardingViewModel.complete()` clear the user_id from breadcrumbs before the next event fires, so subsequent crashes show empty user. Affects post-logout crash triage.
- **S2** - Found while reading code in PerformanceProfiler. Four call sites construct DateFormatter inside hot loops. Each construction is ~5ms. Move to lazy properties on the owning view models.
- **S3** - Caught by manual scan: `Text("No items yet")`, `Text("Try a different search")`, `Text("All caught up!")` in three different view files. None are in `Localizable.xcstrings`. Run `/skill axiom-localization` after fixing.
- **S4** - 12 colors in `Assets.xcassets` have zero references. Cleanup is mechanical but easy to skip in routine PRs. Worth a 30-min cleanup pass before audit-readiness review.

---

## 3. Audit findings

Items from audit tools (linters, code review skills, custom audits) not fixed immediately.

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast      | Effort | Status   |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|------------|--------|----------|
| A1 | 🔴 THIS    | radar-suite: 3 force unwraps in critical paths       | 🔴 CRIT | 🟢 Med  | 🔴 Crit | 🟠 Excellent | 🟢 3 fls   | Sml    | Fixed    |
| A2 | 🔵 NEXT    | radar-suite: ObservableObject + @Published (legacy)  | 🟢 MED  | ⚪ Low  | 🟢 Med  | 🟢 Good      | 🟡 ~9 fls  | Med    | Open     |
| A3 | 🟡 LATER   | code-review: 6 oversized files (>800 lines)          | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | 🟢 6 fls   | Med    | Deferred |
| A4 | 🔵 NEXT    | radar-suite: try? swallowing errors in 14 spots      | 🟢 MED  | 🟢 Med  | 🟢 Med  | 🟢 Good      | 🟡 ~14 fls | Med    | Open     |
| A5 | ⚪ SOMEDAY | radar-suite: 47 async calls without .task modifier   | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | 🔴 >15 fls | Lrg    | Open     |

### Detail - Audit findings

- **A1** - **CLOSED 2026-04-18 commit `2ce6d3f5`.** radar-suite found three force unwraps in payment flow: `PaymentManager.swift:204`, `ReceiptValidator.swift:88`, `SubscriptionStore.swift:156`. Two were on guaranteed-non-nil values (kept with documentation comments); one was a real risk (replaced with guard let + Sentry breadcrumb). Tests added for the converted path.
- **A2** - radar-suite finding ID `MOD-001`. Migration path: ObservableObject + @Published -> @Observable macro. Spec: `Documentation/Architecture/Modernization.md`. Incremental approach - convert when touching a file, don't chase the chain.
- **A3** - code-review-tool flagged 6 files >800 lines. None are causing problems today; tracked for future split. List: `MainView.swift` (1240), `OrderManager.swift` (910), `SearchService.swift` (864), `SettingsView.swift` (823), `ChatViewModel.swift` (812), `ReportGenerator.swift` (806).
- **A4** - radar-suite finding ID `ERR-003`. Convert `try?` calls that silently swallow real errors. Use `ModelContext+Logging.swift`'s `fetchWithLogging()` helper. Targets are listed in the radar report.
- **A5** - radar-suite finding ID `ASY-008`. View-level async calls that should use `.task` modifier for auto-cancellation. Bulk migration; defer until a clean sprint.

---

## 4. User-reported / observed

Bugs noticed but not reproduced; friction observed.

| #  | Target     | Finding                                              | Urg     | RFix    | RNo     | ROI          | Blast    | Effort | Status   |
|----|------------|------------------------------------------------------|---------|---------|---------|--------------|----------|--------|----------|
| U1 | 🔵 NEXT    | iPad: keyboard doesn't dismiss on first sheet open   | 🟢 MED  | ⚪ Low  | 🟢 Med  | 🟢 Good      | 🟢 2 fls | Sml    | Open     |
| U2 | 🟡 LATER   | macOS: window position not restored after hiber.     | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | 🟢 1 fl  | Sml    | Open     |
| U3 | ⚪ SOMEDAY | TestFlight: 1 user reported chart colors look wrong  | ⚪ LOW  | ⚪ Low  | ⚪ Low  | 🟡 Marginal  | ⚪ 1 fl  | Triv   | Open     |

### Detail - User-reported / observed

- **U1** - Reproduced manually 2026-04-19 on iPad Pro 13" simulator. First time presenting `AddItemSheet`, the keyboard appears but Done button doesn't fire. Subsequent opens work. Likely SwiftUI focus state initialization race. Worth a 30-min spike.
- **U2** - macOS window saves position to UserDefaults, but hibernation seems to skip the save. Cosmetic only; no data loss. Affects `WindowGroup`-based apps on macOS 14+.
- **U3** - TestFlight feedback from one user, no screenshot attached. Possibly colorblind accessibility issue with chart series colors (currently 3 of the 5 are warm colors). Need user follow-up before changing anything.

---

## Cross-references

- v0.2 plan files in `~/.claude/plans/`
- Audit reports in `.agents/research/`
- Sentry dashboard for crash signal
