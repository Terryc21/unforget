"""Review #8: staleness has dates behind it (row_age.py).

Builds throwaway git repos with fixed commit dates, plus a non-git ledger for
the written-date fallback. Nothing outside the temp directory is touched.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'skills' / 'unforget' / 'scripts' / 'row_age.py'
TODAY = '2026-11-21'
HEADER = ('<!-- unforget-format: v2 -->\n## 3. Audit findings\n\n'
          '| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |\n'
          '|---|---|---|---|---|---|---|---|---|---|\n')


def row(rid, target, finding, status='`@status:open`'):
    return f'| {rid} | {target} | {finding} | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | Small | {status} |\n'


def ages(path, *extra):
    r = subprocess.run([sys.executable, str(SCRIPT), '--file', str(path), '--today', TODAY, *extra],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    out['by_id'] = {x['id']: x for x in out['rows']}
    return out


class GitDatedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.ledger = self.dir / 'UNFORGET.md'
        self.git('init', '-q')

    def git(self, *args, date=None):
        env = dict(os.environ)
        if date:
            env['GIT_AUTHOR_DATE'] = env['GIT_COMMITTER_DATE'] = f'{date}T12:00:00'
        subprocess.run(['git', '-C', str(self.dir), '-c', 'user.name=t', '-c', 'user.email=t@example.com',
                        '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *args],
                       check=True, capture_output=True, env=env)

    def commit(self, text, date):
        self.ledger.write_text(text, encoding='utf-8')
        self.git('add', 'UNFORGET.md')
        self.git('commit', '-q', '-m', date, date=date)

    def test_logged_and_touched_come_from_commits(self):
        a1 = row('A1', '🔵 NEXT', 'First')
        self.commit(HEADER + a1 + row('A2', '🔴 THIS', 'Second'), '2026-01-01')
        self.commit(HEADER + a1 + row('A2', '🔴 THIS', 'Second, edited'), '2026-11-01')
        self.commit(HEADER + a1 + row('A2', '🔴 THIS', 'Second, edited') + row('A3', '⚪ SOMEDAY', 'Third'),
                    '2026-11-10')
        out = ages(self.ledger)
        self.assertTrue(out['git'])
        a1, a2, a3 = (out['by_id'][k] for k in ('A1', 'A2', 'A3'))
        self.assertEqual((a1['logged'], a1['touched'], a1['date_source']), ('2026-01-01', '2026-01-01', 'git'))
        self.assertEqual((a2['logged'], a2['touched']), ('2026-01-01', '2026-11-01'))
        self.assertEqual((a3['logged'], a3['touched']), ('2026-11-10', '2026-11-10'))
        self.assertEqual(a1['age_days'], 324)
        self.assertTrue(a1['stale'], 'NEXT, untouched for 324 days > 90')
        self.assertFalse(a2['stale'], 'THIS, touched 20 days ago <= 30')
        self.assertEqual(out['stale'], ['A1'])

    def test_uncommitted_edit_counts_as_today(self):
        self.commit(HEADER + row('A1', '🔵 NEXT', 'First'), '2026-01-01')
        self.ledger.write_text(HEADER + row('A1', '🔵 NEXT', 'First, edited now') + row('A2', '🔵 NEXT', 'New'),
                               encoding='utf-8')
        out = ages(self.ledger)
        a1, a2 = out['by_id']['A1'], out['by_id']['A2']
        self.assertEqual((a1['logged'], a1['touched'], a1['uncommitted']), ('2026-01-01', TODAY, True))
        self.assertEqual((a2['logged'], a2['touched'], a2['date_source']), (TODAY, TODAY, 'uncommitted'))
        self.assertEqual(out['stale'], [])

    def test_done_verified_and_withdrawn_never_go_stale(self):
        self.commit(HEADER
                    + row('A1', '🔵 NEXT', 'Done', '`@status:done-verified` `@verified:device`')
                    + row('A2', '⚪ SOMEDAY', 'Dropped', '`@status:withdrawn`')
                    + row('A3', '🔵 NEXT', 'Owed', '`@status:done-unverified`'), '2020-01-01')
        out = ages(self.ledger)
        self.assertTrue(out['by_id']['A1']['ready_to_archive'])
        self.assertIsNone(out['by_id']['A1']['threshold'])
        self.assertEqual(out['stale'], ['A3'], 'done-unverified still owes a check, so it ages')

    def test_untracked_ledger_in_a_repo_falls_back_to_written_dates(self):
        (self.dir / 'other.txt').write_text('x')
        self.git('add', 'other.txt')
        self.git('commit', '-q', '-m', 'other', date='2026-01-01')
        self.ledger.write_text(HEADER + row('A1', '🔵 NEXT', 'Seen 2026-03-01, recheck 2026-04-15'),
                               encoding='utf-8')
        out = ages(self.ledger)
        self.assertFalse(out['git'])
        a1 = out['by_id']['A1']
        self.assertEqual((a1['logged'], a1['touched'], a1['date_source']), ('2026-03-01', '2026-04-15', 'text'))
        self.assertIn('dated from dates written in the row', out['advisory'])


class WrittenDateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / 'UNFORGET.md'

    def test_formats_future_dates_detail_blocks_and_undatable_rows(self):
        self.ledger.write_text(
            HEADER
            + row('A1', '🔵 NEXT', 'Found 07/04/2026; due 2027-01-01')
            + row('A2', '🔵 NEXT', 'Only the detail block has a date')
            + row('A3', '🔵 NEXT', 'No date anywhere, build 40, A1.2')
            + '\n### Detail — Audit findings\n\n- **A2** — Logged 2026-10-30 by a session.\n',
            encoding='utf-8')
        out = ages(self.ledger)
        a1, a2 = out['by_id']['A1'], out['by_id']['A2']
        self.assertEqual((a1['logged'], a1['touched']), ('2026-07-04', '2026-07-04'), 'a future date is not an edit')
        self.assertEqual(a2['touched'], '2026-10-30')
        self.assertEqual([n['id'] for n in out['needs_date']], ['A3'])
        self.assertNotIn('A3', out['by_id'], 'an undatable row gets no guessed age')
        self.assertEqual(out['stale'], ['A1'])

    def test_bad_today_is_a_usage_error(self):
        self.ledger.write_text(HEADER, encoding='utf-8')
        r = subprocess.run([sys.executable, str(SCRIPT), '--file', str(self.ledger), '--today', '11/21/2026'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()
