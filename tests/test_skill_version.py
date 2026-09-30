"""Portable metadata and backwards-compatible installed-version reporting."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_install import read_version


class SkillVersionTests(unittest.TestCase):
    def check(self, content, expected):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'SKILL.md').write_text(content)
            self.assertEqual(read_version(root), expected)

    def test_portable_metadata(self):
        self.check('---\nname: unforget\nmetadata:\n  version: "2.9.0"\n---\nBody', '2.9.0')

    def test_legacy_release(self):
        self.check('---\nname: unforget\nversion: 2.8.0\n---\n', '2.8.0')

    def test_no_version_in_body(self):
        self.check('---\nname: unforget\n---\nversion: 9.9.9\n', None)

    def test_metadata_precedes_legacy(self):
        self.check('---\nversion: 2.8.0\nmetadata:\n  version: 2.9.0\n---\n', '2.9.0')

    def test_no_unrelated_nested_version(self):
        self.check('---\nmetadata:\n  other:\n    version: 9.9.9\n---\n', None)

    def test_crlf(self):
        self.check('---\r\nmetadata:\r\n  version: 2.9.0\r\n---\r\n', '2.9.0')


if __name__ == '__main__':
    unittest.main()
