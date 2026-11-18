#!/usr/bin/env python3
"""Setting rows aside by likelihood (reference/pickup.md), phase 1.

What these tests hold:
  - a protected-class, high-risk or THIS row is never set aside by policy alone;
  - unrated, `uncertain` and closed rows are never candidates;
  - the likelihood/parking tokens never change status or the release gate;
  - verify errors on a protected set-aside with no quoted user acceptance;
  - the HTML report leaves set-aside rows out by default, counts them, and never
    hides one that still blocks release;
  - the session readout counts set-asides and is unchanged when there are none.

Run:  python3 -m unittest discover -s tests -p test_set_aside.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "unforget" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import defer_tally  # noqa: E402
import parse_status  # noqa: E402
import set_aside  # noqa: E402
import verify_ledger  # noqa: E402

HEADER = ("| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |\n"
          "|---|---|---|---|---|---|---|---|---|---|\n")


def row(rid, target, finding, risk_no_fix, status):
    return (f"| {rid} | {target} | {finding} | 🟢 MEDIUM | ⚪ Low | {risk_no_fix} | 🟢 Good | "
            f"⚪ 1 file | Small | {status} |\n")


LEDGER = (
    "# UNFORGET\n\n<!-- unforget-format: v2 -->\n\n## 3. Audit findings\n\n" + HEADER
    + row("A1", "🔵 NEXT", "Tooltip flickers on resize", "⚪ Low", "`@status:open` `@likelihood:rare`")
    + row("A2", "🔵 NEXT", "Restore can cause data loss on retry", "⚪ Low", "`@status:open` `@likelihood:rare`")
    + row("A3", "🔴 THIS", "Badge shows stale count", "⚪ Low", "`@status:open` `@likelihood:improbable`")
    + row("A4", "🟡 LATER", "Sync stalls on airplane mode", "🟡 High", "`@status:open` `@likelihood:rare`")
    + row("A5", "🔵 NEXT", "Unrated cosmetic glitch", "⚪ Low", "`@status:open`")
    + row("A6", "🔵 NEXT", "Maybe a race in thumbnails", "⚪ Low", "`@status:open` `@likelihood:uncertain`")
    + row("A7", "🔵 NEXT", "Closed rare glitch", "⚪ Low",
          "`@status:withdrawn` `@likelihood:rare` not reproducible")
    + row("A8", "⚪ SOMEDAY", "Old set-aside glitch", "⚪ Low",
          "`@status:open` `@likelihood:rare` `@parked:likelihood` policy")
)

LEAN = (
    "# U\n\n<!-- unforget-format: v2 -->\n\n## 2. Session spillover\n\n"
    "| # | Target | Finding | Urgency | Effort | Status |\n|---|---|---|---|---|---|\n"
    "| S1 | 🔵 NEXT | Rare lean glitch | ⚪ LOW | Small | `@status:open` `@likelihood:rare` |\n"
)


def candidates(text, policy="auto", classes=None):
    result = set_aside.classify(text, policy, set_aside.parse_classes(classes))
    return {c["id"]: c for c in result["candidates"]}, result


class ClassifierTests(unittest.TestCase):
    def test_low_risk_rare_row_is_policy_eligible(self):
        found, _ = candidates(LEDGER)
        self.assertEqual(found["A1"]["eligibility"], "policy-eligible")
        self.assertEqual(found["A1"]["action"], "auto")

    def test_protected_class_row_never_auto(self):
        found, _ = candidates(LEDGER)
        self.assertEqual(found["A2"]["eligibility"], "needs-user")
        self.assertEqual(found["A2"]["action"], "ask")
        self.assertTrue(any("data loss" in r for r in found["A2"]["reasons"]))

    def test_this_row_never_auto(self):
        found, _ = candidates(LEDGER)
        self.assertEqual(found["A3"]["action"], "ask")
        self.assertIn("blocks the current release (Target THIS)", found["A3"]["reasons"])

    def test_high_risk_row_never_auto(self):
        found, _ = candidates(LEDGER)
        self.assertEqual(found["A4"]["action"], "ask")

    def test_unrated_uncertain_closed_and_already_set_aside_are_not_candidates(self):
        found, result = candidates(LEDGER)
        for rid in ("A5", "A6", "A7", "A8"):
            self.assertNotIn(rid, found)
        self.assertEqual(result["set_aside"]["ids"], ["A8"])
        self.assertEqual(result["summary_line"], "Set aside: 1 (rare 1)")

    def test_policy_off_offers_nothing_and_ask_asks_everything(self):
        off, _ = candidates(LEDGER, "off")
        self.assertEqual({c["action"] for c in off.values()}, {"none"})
        ask, _ = candidates(LEDGER, "ask")
        self.assertEqual({c["action"] for c in ask.values()}, {"ask"})

    def test_no_risk_column_needs_the_user(self):
        found, _ = candidates(LEAN)
        self.assertEqual(found["S1"]["action"], "ask")
        self.assertIn("no Risk: No Fix rating to check", found["S1"]["reasons"])

    def test_custom_classes_replace_defaults(self):
        found, _ = candidates(LEDGER, classes="tooltip")
        self.assertEqual(found["A1"]["action"], "ask")
        self.assertEqual(found["A2"]["action"], "auto")


class TokenNeutralityTests(unittest.TestCase):
    KEYS = ("status", "completed", "archivable", "blocks_release", "issues", "effective_status")

    def test_tokens_do_not_change_status_or_gate(self):
        plain = LEDGER.replace(" `@likelihood:rare`", "").replace(" `@likelihood:improbable`", "") \
                      .replace(" `@likelihood:uncertain`", "").replace(" `@parked:likelihood`", "")
        before = {r["id"]: r for r in parse_status.parse_file(plain)}
        after = {r["id"]: r for r in parse_status.parse_file(LEDGER)}
        for rid in before:
            for key in self.KEYS:
                self.assertEqual(before[rid][key], after[rid][key], f"{rid}.{key}")
        self.assertTrue(after["A8"]["set_aside"])
        self.assertEqual(after["A1"]["likelihood"], "rare")
        self.assertFalse(after["A1"]["parked"])


class VerifyTests(unittest.TestCase):
    def checks(self, text):
        findings, _ = verify_ledger.check_rows(text, 400)
        return {(f["check"], f["id"], f["severity"]) for f in findings}

    def test_protected_set_aside_without_acceptance_is_an_error(self):
        text = LEDGER.replace(
            "`@status:open` `@likelihood:rare` |\n| A3",
            "`@status:open` `@likelihood:rare` `@parked:likelihood` |\n| A3", 1)
        self.assertIn(("set-aside-unaccepted", "A2", "error"), self.checks(text))

    def test_bare_acceptance_does_not_count_but_quoted_words_do(self):
        base = "| A2 | ⚪ SOMEDAY | Restore can cause data loss on retry | 🟢 MEDIUM | ⚪ Low | ⚪ Low | 🟢 Good | ⚪ 1 file | Small | "
        bare = "# U\n\n" + HEADER + base + "`@status:open` `@likelihood:rare` `@parked:likelihood` Accepted-risk: yes |\n"
        quoted = "# U\n\n" + HEADER + base + ('`@status:open` `@likelihood:rare` `@parked:likelihood` '
                                              'Accepted-risk: "park it, rare enough" (11/18/2026) |\n')
        self.assertIn(("set-aside-unaccepted", "A2", "error"), self.checks(bare))
        self.assertNotIn(("set-aside-unaccepted", "A2", "error"), self.checks(quoted))

    def test_set_aside_still_this_and_unrated_warn(self):
        text = "# U\n\n" + HEADER + row("A9", "🔴 THIS", "Glitch", "⚪ Low", "`@status:open` `@parked:likelihood`")
        found = self.checks(text)
        self.assertIn(("set-aside-still-this", "A9", "warn"), found)
        self.assertIn(("set-aside-unrated", "A9", "warn"), found)

    def test_unknown_likelihood_warns(self):
        text = "# U\n\n" + HEADER + row("A9", "🔵 NEXT", "Glitch", "⚪ Low", "`@status:open` `@likelihood:sometimes`")
        self.assertIn(("likelihood-value", "A9", "warn"), self.checks(text))

    def test_example_ledger_gets_no_new_checks(self):
        text = (ROOT / "examples" / "UNFORGET.md").read_text(encoding="utf-8")
        new = {"likelihood-value", "set-aside-unrated", "set-aside-likelihood",
               "set-aside-still-this", "set-aside-unaccepted"}
        self.assertFalse({c for c, _, _ in self.checks(text)} & new)


class ReportTests(unittest.TestCase):
    def run_report(self, text, *extra):
        with tempfile.TemporaryDirectory() as d:
            ledger, out = Path(d) / "UNFORGET.md", Path(d) / "r.html"
            ledger.write_text(text, encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "html_report.py"), "--file", str(ledger),
                                "--output", str(out), *extra], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(r.stdout)

    def test_set_aside_rows_left_out_and_counted(self):
        data = self.run_report(LEDGER)
        self.assertEqual(data["set_aside_hidden"], {"rare": 1})
        self.assertTrue(any("Set aside as unlikely" in w for w in data["warnings"]))
        shown = self.run_report(LEDGER, "--include-set-aside")
        self.assertEqual(shown["set_aside_hidden"], {})
        self.assertEqual(shown["rows"], data["rows"] + 1)

    def test_set_aside_blocker_is_never_hidden(self):
        text = "# U\n\n<!-- unforget-format: v2 -->\n\n" + HEADER + row(
            "A9", "🔴 THIS", "Glitch", "⚪ Low", "`@status:open` `@likelihood:rare` `@parked:likelihood`")
        data = self.run_report(text)
        self.assertEqual(data["blockers_in_report"], 1)
        self.assertEqual(data["set_aside_hidden"], {})


class TallyTests(unittest.TestCase):
    def test_readout_counts_set_asides_and_is_unchanged_without_them(self):
        with tempfile.TemporaryDirectory() as d:
            plain = defer_tally.record(Path(d), "fixed-now", None)["readout"]
            self.assertEqual(plain, "This session: 1 fixed inline · 0 deferred (reasons: none).")
            defer_tally.record(Path(d), "set-aside", "policy")
            out = defer_tally.record(Path(d), "set-aside", "user")
            self.assertTrue(out["readout"].endswith("· 2 set aside (policy 1, you 1)."))


if __name__ == "__main__":
    unittest.main()
