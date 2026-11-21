"""ledger_backup.py (one backup contract) and move_ledger.py (verified moves).

Review #9: backups worked differently in each command. Review #6: migration
removed originals after a comparison only the model claimed to have made.
Every test works in its own temp directory.
"""
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills' / 'unforget' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import ledger_backup  # noqa: E402
import move_ledger  # noqa: E402
import scan_surfaces  # noqa: E402

LEDGER = ('<!-- unforget-format: v2 -->\n# TERRY\n\n## 1. Paused plans\n\n'
          '| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |\n'
          '|---|---|---|---|---|---|---|---|---|---|\n'
          '| P1 | 🔵 NEXT | Thing — with “quotes” | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | Small | `@status:open` |\n')


def fixed_clock(*stamps):
    """A clock returning each given (h, m, s) on 2026-11-21 in turn, then repeating the last."""
    times = [dt.datetime(2026, 11, 21, h, m, s) for h, m, s in stamps]
    state = {'i': 0}

    def now():
        t = times[min(state['i'], len(times) - 1)]
        state['i'] += 1
        return t
    return now


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def names(self, d=None):
        return sorted(p.name for p in (d or self.dir).iterdir())


class LedgerBackupTests(TempDirCase):
    def setUp(self):
        super().setUp()
        self.ledger = self.dir / 'TERRY.md'
        self.ledger.write_text(LEDGER, encoding='utf-8')

    def test_backup_is_byte_identical_and_named_after_the_ledger(self):
        r = ledger_backup.write_backup(self.ledger, clock=fixed_clock((9, 0, 0)))
        self.assertEqual(Path(r['backup']).name, 'TERRY.md.bak-2026-11-21-090000')
        self.assertEqual(Path(r['backup']).read_bytes(), self.ledger.read_bytes())
        self.assertFalse(r['reused'])

    def test_keeps_five_per_ledger_and_leaves_other_ledgers_alone(self):
        other = self.dir / 'UNFORGET.md'
        other.write_text('x')
        for s in range(3):
            ledger_backup.write_backup(other, clock=fixed_clock((8, 0, s)))
        for s in range(7):
            self.ledger.write_text(LEDGER + f'<!-- edit {s} -->\n')
            ledger_backup.write_backup(self.ledger, clock=fixed_clock((9, 0, s)))
        mine = [n for n in self.names() if n.startswith('TERRY.md.bak-')]
        theirs = [n for n in self.names() if n.startswith('UNFORGET.md.bak-')]
        self.assertEqual(mine, [f'TERRY.md.bak-2026-11-21-09000{s}' for s in range(2, 7)])
        self.assertEqual(len(theirs), 3)

    def test_same_second_identical_bytes_reuses_the_backup(self):
        clock = fixed_clock((9, 0, 0))
        ledger_backup.write_backup(self.ledger, clock=clock)
        r = ledger_backup.write_backup(self.ledger, clock=clock)
        self.assertTrue(r['reused'])
        self.assertEqual(len([n for n in self.names() if '.bak-' in n]), 1)

    def test_same_second_new_bytes_waits_for_the_next_second(self):
        sleeps = []
        clock = fixed_clock((9, 0, 0), (9, 0, 0), (9, 0, 1))
        ledger_backup.write_backup(self.ledger, clock=clock)
        self.ledger.write_text(LEDGER + 'changed\n')
        r = ledger_backup.write_backup(self.ledger, clock=clock, sleep=sleeps.append)
        self.assertEqual(Path(r['backup']).name, 'TERRY.md.bak-2026-11-21-090001')
        self.assertEqual(len(sleeps), 1)
        first = self.dir / 'TERRY.md.bak-2026-11-21-090000'
        self.assertEqual(first.read_text(), LEDGER, 'an earlier backup must never be overwritten')

    def test_refuses_rather_than_overwrite_a_different_backup(self):
        (self.dir / 'TERRY.md.bak-2026-11-21-090000').write_text('older content')
        with self.assertRaises(ledger_backup.BackupRefused):
            ledger_backup.write_backup(self.ledger, clock=fixed_clock((9, 0, 0)), sleep=lambda s: None)
        self.assertEqual((self.dir / 'TERRY.md.bak-2026-11-21-090000').read_text(), 'older content')

    def test_prune_refuses_keep_zero(self):
        with self.assertRaises(ValueError):
            ledger_backup.prune(self.ledger, keep=0)
        r = subprocess.run([sys.executable, str(SCRIPTS / 'ledger_backup.py'), 'prune',
                            '--file', str(self.ledger), '--keep', '0'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_cli_backup(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / 'ledger_backup.py'), 'backup',
                            '--file', str(self.ledger)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(json.loads(r.stdout)['backup']).read_text(encoding='utf-8'), LEDGER)

    def test_atomic_write_leaves_no_temp_file(self):
        ledger_backup.atomic_write(self.ledger, 'new\n')
        self.assertEqual(self.ledger.read_text(), 'new\n')
        self.assertEqual(self.names(), ['TERRY.md'])

    def test_atomic_write_keeps_the_file_mode(self):
        self.ledger.chmod(0o644)
        ledger_backup.atomic_write(self.ledger, 'new\n')
        self.assertEqual(self.ledger.stat().st_mode & 0o777, 0o644)

    def test_atomic_write_ignores_a_planted_symlink_at_the_old_temp_name(self):
        victim = self.dir / 'victim.txt'
        victim.write_text('keep me')
        (self.dir / '.TERRY.md.unforget-tmp').symlink_to(victim)
        ledger_backup.atomic_write(self.ledger, 'new\n')
        self.assertEqual(victim.read_text(), 'keep me')
        self.assertEqual(self.ledger.read_text(), 'new\n')

    def test_atomic_write_failure_leaves_ledger_and_no_temp(self):
        with mock.patch.object(ledger_backup.os, 'replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                ledger_backup.atomic_write(self.ledger, 'new\n')
        self.assertEqual(self.ledger.read_text(encoding='utf-8'), LEDGER)
        self.assertEqual(self.names(), ['TERRY.md'])


class CommandsUseTheContractTests(TempDirCase):
    """set_aside convert --apply and row_budget split --apply both back up through ledger_backup."""

    def test_set_aside_convert_backs_up_and_prunes(self):
        import set_aside
        ledger = self.dir / 'UNFORGET.md'
        ledger.write_text(LEDGER.replace('Thing — with “quotes”', 'Thing. Likelihood: Rare (reviewed)'),
                          encoding='utf-8')
        for s in range(6):
            (self.dir / f'UNFORGET.md.bak-2026-01-01-00000{s}').write_text('old')
        text = ledger.read_text(encoding='utf-8')
        plan = set_aside.plan_conversion(text, ['reviewed'], ['measured'])
        self.assertEqual([a['id'] for a in plan['add']], ['P1'], plan)
        r = set_aside.apply_conversion(ledger, text, plan)
        self.assertTrue(r['applied'], r)
        self.assertEqual(Path(r['backup']).read_text(encoding='utf-8'), text)
        self.assertEqual(len([n for n in self.names() if n.startswith('UNFORGET.md.bak-')]), 5)

    def test_row_budget_split_backs_up(self):
        ledger = self.dir / 'UNFORGET.md'
        long_row = LEDGER.replace('Thing — with “quotes”', 'Long finding. ' + 'detail ' * 120)
        ledger.write_text(long_row + '\n### Detail — Paused plans\n\n- **P1** — note\n', encoding='utf-8')
        before = ledger.read_text(encoding='utf-8')
        r = subprocess.run([sys.executable, str(SCRIPTS / 'row_budget.py'), 'split', '--file', str(ledger),
                            '--id', 'P1', '--apply'], capture_output=True, text=True)
        out = json.loads(r.stdout)
        self.assertTrue(out.get('applied'), out)
        self.assertEqual(Path(out['backup']).read_text(encoding='utf-8'), before)
        self.assertNotEqual(ledger.read_text(encoding='utf-8'), before)


class MoveLedgerTests(TempDirCase):
    def setUp(self):
        super().setUp()
        (self.dir / 'old').mkdir()
        (self.dir / 'new').mkdir()
        self.src = self.dir / 'old' / 'TERRY.md'
        self.dst = self.dir / 'new' / 'TERRY.md'
        self.src.write_text(LEDGER, encoding='utf-8')
        self.original = self.src.read_bytes()

    def test_dry_run_writes_nothing(self):
        code, r = move_ledger.move(self.src, self.dst, redirect=False, apply=False)
        self.assertEqual(code, 0)
        self.assertFalse(r['applied'])
        self.assertFalse(self.dst.exists())
        self.assertEqual(self.names(self.src.parent), ['TERRY.md'])

    def test_apply_copies_identical_then_removes_source_keeping_a_backup(self):
        code, r = move_ledger.move(self.src, self.dst, redirect=False, apply=True)
        self.assertEqual(code, 0, r)
        self.assertEqual(self.dst.read_bytes(), self.original)
        self.assertFalse(self.src.exists())
        self.assertEqual(r['source_action'], 'removed')
        self.assertEqual(Path(r['backup']).read_bytes(), self.original)

    def test_redirect_pointer_is_recognized_by_the_survey(self):
        code, r = move_ledger.move(self.src, self.dst, redirect=True, apply=True)
        self.assertEqual(code, 0, r)
        self.assertEqual(r['source_action'], 'redirected')
        is_redirect, _ = scan_surfaces.is_redirect_pointer(self.src)
        self.assertTrue(is_redirect, self.src.read_text())
        self.assertIn('../new/TERRY.md', self.src.read_text())

    def test_bad_copy_is_removed_and_source_untouched(self):
        real = Path.read_bytes
        dst = self.dst

        def corrupt(path):
            data = real(path)
            return data[:-1] + b'?' if path == dst else data
        with mock.patch.object(Path, 'read_bytes', autospec=True, side_effect=corrupt):
            code, r = move_ledger.move(self.src, self.dst, redirect=False, apply=True)
        self.assertEqual(code, 1)
        self.assertIn('did not read back identical', r['error'])
        self.assertFalse(self.dst.exists(), 'the bad copy must be removed')
        self.assertEqual(self.src.read_bytes(), self.original)
        self.assertEqual(self.names(self.src.parent), ['TERRY.md'], 'no backup when nothing moved')

    def test_destination_with_other_content_is_never_overwritten(self):
        self.dst.write_text('someone else\n')
        code, r = move_ledger.move(self.src, self.dst, redirect=False, apply=True)
        self.assertEqual(code, 1)
        self.assertEqual(self.dst.read_text(), 'someone else\n')
        self.assertEqual(self.src.read_bytes(), self.original)

    def test_rerun_after_interrupted_move_finishes_it(self):
        self.dst.write_bytes(self.original)  # the copy landed, the removal didn't
        code, r = move_ledger.move(self.src, self.dst, redirect=False, apply=True)
        self.assertEqual(code, 0, r)
        self.assertFalse(self.src.exists())
        self.assertIn('no copy needed', r['steps'][0])

    def test_same_file_is_a_usage_error(self):
        code, r = move_ledger.move(self.src, self.src, redirect=False, apply=True)
        self.assertEqual(code, 2)
        self.assertEqual(self.src.read_bytes(), self.original)

    def test_cli_round_trip(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / 'move_ledger.py'), '--src', str(self.src),
                            '--dst', str(self.dst), '--apply'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)['sha256'],
                         __import__('hashlib').sha256(self.original).hexdigest())


if __name__ == '__main__':
    unittest.main()
