"""prune_backups.py keeps the newest N backups and never deletes anything else.

Each test builds its own temp directory, so nothing outside it is touched.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'skills' / 'unforget' / 'scripts' / 'prune_backups.py'

BACKUPS = [
    'UNFORGET.md.bak-2026-11-01-090000',
    'UNFORGET.md.bak-2026-11-02-090000',
    'UNFORGET.md.bak-2026-11-03-090000',
    'UNFORGET.md.bak-2026-11-03-120000',
    'UNFORGET.md.bak-2026-11-04-090000',
]
# Look like backups to a person, but are not the rotation's files.
BYSTANDERS = [
    'UNFORGET.md',
    'UNFORGET-pre-build33.md',
    'UNFORGET.md.bak-2026-11-01',          # no time part
    'UNFORGET.md.bak-2026-11-01-090000.txt',
    'notes.md',
]


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


class PruneBackupsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        for name in BACKUPS + BYSTANDERS:
            (self.dir / name).write_text(name)

    def names(self):
        return sorted(p.name for p in self.dir.iterdir())

    def test_keeps_newest_n_and_deletes_the_rest(self):
        code, out, _ = run('--keep', '2', '--dir', str(self.dir))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result['kept'], [BACKUPS[4], BACKUPS[3]])
        self.assertEqual(result['pruned'], [BACKUPS[2], BACKUPS[1], BACKUPS[0]])
        self.assertEqual(self.names(), sorted(BACKUPS[3:] + BYSTANDERS))

    def test_same_day_backups_sort_by_time(self):
        code, out, _ = run('--keep', '1', '--dir', str(self.dir), '--dry-run')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['kept'], [BACKUPS[4]])
        code, out, _ = run('--keep', '3', '--dir', str(self.dir), '--dry-run')
        self.assertEqual(json.loads(out)['kept'][-1], BACKUPS[2])  # 11-03 09:00 after 11-03 12:00

    def test_dry_run_deletes_nothing(self):
        before = self.names()
        code, out, _ = run('--keep', '1', '--dir', str(self.dir), '--dry-run')
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)['dry_run'])
        self.assertEqual(len(json.loads(out)['pruned']), 4)
        self.assertEqual(self.names(), before)

    def test_keep_zero_is_refused_and_deletes_nothing(self):
        before = self.names()
        code, out, err = run('--keep', '0', '--dir', str(self.dir))
        self.assertEqual(code, 2)
        self.assertEqual(out, '')
        self.assertIn('at least 1', json.loads(err)['error'])
        self.assertEqual(self.names(), before)

    def test_negative_keep_is_refused(self):
        before = self.names()
        code, _, _ = run('--keep', '-3', '--dir', str(self.dir))
        self.assertEqual(code, 2)
        self.assertEqual(self.names(), before)

    def test_keep_larger_than_count_deletes_nothing(self):
        code, out, _ = run('--keep', '50', '--dir', str(self.dir))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['pruned'], [])
        self.assertEqual(self.names(), sorted(BACKUPS + BYSTANDERS))

    def test_missing_directory_is_a_usage_error(self):
        code, _, err = run('--keep', '5', '--dir', str(self.dir / 'nope'))
        self.assertEqual(code, 2)
        self.assertIn('directory not found', json.loads(err)['error'])


if __name__ == '__main__':
    unittest.main()
