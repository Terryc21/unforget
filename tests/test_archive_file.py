#!/usr/bin/env python3
"""One archive file per ledger, named in one place.

`init`, `archive` and `promote` once named three different destinations
(an `archive/` subfolder, `UNFORGET-archive-<date>.md` and `UNFORGET-archive.md`),
so archived history spread across files depending on which command moved it.
`reference/commands.md` § The archive file is now the only definition. These
tests keep the other references from naming a second destination, and keep the
archive file out of the active backlog.

Run:  python3 -m unittest discover -s tests -p test_archive_file.py
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "unforget"
sys.path.insert(0, str(SKILL / "scripts"))

import import_drift  # noqa: E402
import scan_surfaces  # noqa: E402

DOCS = sorted((SKILL / "reference").glob("*.md")) + [SKILL / "SKILL.md", ROOT / "README.md"]
DEFINITION = SKILL / "reference" / "commands.md"


class ArchiveFileTests(unittest.TestCase):
    def test_defined_once(self):
        hits = [p.name for p in DOCS if "### The archive file" in p.read_text(encoding="utf-8")]
        self.assertEqual(hits, ["commands.md"])

    def test_no_second_destination_named(self):
        # Dated archive files and an archive/ subfolder may be mentioned only in
        # the definition's "older archive files" note, never as a destination.
        # (Other files' dated archives, e.g. surfaces.md's skipped
        # `Deferred-archive-2026-05-01.md`, are examples, not destinations.)
        pattern = re.compile(r"archive-<date>|UNFORGET-archive-\d{4}-\d{2}-\d{2}|`archive/` subfolder")
        offenders = []
        for path in DOCS:
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line) and not (path == DEFINITION and "Older archive files" in line):
                    offenders.append(f"{path.name}:{n}")
        self.assertEqual(offenders, [])

    def test_init_archive_and_promote_point_at_the_definition(self):
        for name in ("init.md", "promotion.md"):
            text = (SKILL / "reference" / name).read_text(encoding="utf-8")
            self.assertIn("§ The archive file", text, name)

    def test_archive_files_never_count_as_active_ledgers(self):
        for name in ("UNFORGET-archive.md", "SITE-UNFORGET-archive.md"):
            self.assertTrue(import_drift.EXCLUDE_RE.search(name), name)
            self.assertTrue(scan_surfaces.ARCHIVE_FILENAME_RE.search(name), name)
        self.assertFalse(import_drift.EXCLUDE_RE.search("SITE-UNFORGET.md"))


if __name__ == "__main__":
    unittest.main()
