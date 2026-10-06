"""companions.py init --force must never damage content outside its managed block."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'companions.py'
sys.path.insert(0, str(SCRIPT.parent))
import companions  # noqa: E402


def seed(path):
    return subprocess.run([sys.executable, str(SCRIPT), 'init', '--force', '--file', str(path)],
                          capture_output=True, text=True)


class CompanionsInitForceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'unforget-companions.md'

    def test_missing_end_marker_refuses_and_changes_nothing(self):
        original = 'my notes\n' + companions.BEGIN + '\nold table\n\nMY OWN TEXT AFTER\n'
        self.path.write_text(original)
        result = seed(self.path)
        self.assertEqual(result.returncode, 1)
        self.assertIn('refused', result.stdout)
        self.assertEqual(self.path.read_text(), original)

    def test_paired_markers_replace_only_the_block(self):
        original = 'before\n' + companions.BEGIN + '\nold\n' + companions.END + '\nafter\n'
        self.path.write_text(original)
        self.assertEqual(seed(self.path).returncode, 0)
        text = self.path.read_text()
        self.assertTrue(text.startswith('before\n'))
        self.assertTrue(text.endswith('after\n'))
        self.assertNotIn('\nold\n', text)
        self.assertEqual((text.count(companions.BEGIN), text.count(companions.END)), (1, 1))

    def test_no_markers_appends_and_keeps_content(self):
        self.path.write_text('just my notes\n')
        self.assertEqual(seed(self.path).returncode, 0)
        text = self.path.read_text()
        self.assertTrue(text.startswith('just my notes\n'))
        self.assertEqual((text.count(companions.BEGIN), text.count(companions.END)), (1, 1))


if __name__ == '__main__':
    unittest.main()
