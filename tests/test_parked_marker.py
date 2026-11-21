#!/usr/bin/env python3
"""The `@parked` marker must be invisible to status, gating and verification.

Why this file exists
--------------------
`reference/pickup.md` adds `@parked` to the Status cell of rows a session logs on
its own initiative. The design promise is that this is NOT a format change: every
helper reads the marker as narration, so a parked row keeps its status, its
release gating (a parked THIS row still blocks release) and its verify result.
If a parser ever starts treating `@parked` as a status, or the marker hides a
release blocker, these tests fail.

Run:  python3 -m unittest discover -s tests -p test_parked_marker.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "unforget" / "scripts"
EXAMPLE = ROOT / "examples" / "UNFORGET.md"
PARKED = "`@status:open` `@parked` Logged by a session; Revisit: next build"


def park_open_rows(text: str) -> tuple[str, list[str]]:
    """Add @parked after the status token of every open table row; return ids."""
    out, ids = [], []
    for line in text.splitlines(keepends=True):
        if line.startswith("|") and "`@status:open` |" in line:
            ids.append(line.split("|")[1].strip())
            line = line.replace("`@status:open` |", PARKED + " |", 1)
        out.append(line)
    return "".join(out), ids


def run(script: str, path: Path) -> dict | list:
    r = subprocess.run([sys.executable, str(SCRIPTS / script), "--file", str(path)],
                       capture_output=True, text=True)
    return json.loads(r.stdout)


class ParkedMarkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base_text = EXAMPLE.read_text(encoding="utf-8")
        parked_text, cls.ids = park_open_rows(base_text)
        cls.base = Path(cls.tmp.name) / "base.md"
        cls.parked = Path(cls.tmp.name) / "parked.md"
        cls.base.write_text(base_text, encoding="utf-8")
        cls.parked.write_text(parked_text, encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_fixture_has_parked_rows_including_a_blocker(self):
        self.assertGreaterEqual(len(self.ids), 2)
        rows = {r["id"]: r for r in run("parse_status.py", self.parked)}
        self.assertTrue(any(rows[i]["blocks_release"] for i in self.ids),
                        "fixture needs a parked THIS row to test gating")

    def test_parse_status_ignores_marker(self):
        keys = ("status", "verified", "status_valid", "tier_valid", "contradiction",
                "archivable", "blocks_release", "issues")
        base = {r["id"]: r for r in run("parse_status.py", self.base)}
        parked = {r["id"]: r for r in run("parse_status.py", self.parked)}
        self.assertEqual(base.keys(), parked.keys())
        for row_id in base:
            for key in keys:
                self.assertEqual(base[row_id].get(key), parked[row_id].get(key),
                                 f"{row_id}.{key} changed when parked")

    def test_verify_result_unchanged_and_blocker_still_listed(self):
        base = run("verify_ledger.py", self.base)
        parked = run("verify_ledger.py", self.parked)
        base.pop("file")
        parked.pop("file")
        # Parking is reported (parked_waiting, and a clause on the advisory), but
        # changes no finding, count, gate or blocker list.
        waiting = parked.pop("parked_waiting")
        self.assertEqual(base.pop("parked_waiting"), [])
        self.assertEqual(base.pop("set_aside"), parked.pop("set_aside"))
        self.assertEqual(base.pop("advisory"),
                         re.sub(r"; \d+ row\(s\) logged by a session are waiting for you: [^;(]*?(?= \(|$)",
                                "", parked.pop("advisory")))
        self.assertEqual(base, parked)
        open_ids = {r["id"] for r in run("parse_status.py", self.parked) if not r["completed"]}
        self.assertEqual(set(waiting), set(self.ids) & open_ids)
        self.assertTrue(set(self.ids) & set(parked["this_open"]),
                        "a parked THIS row must still block release")


if __name__ == "__main__":
    unittest.main()
