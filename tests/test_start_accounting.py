"""Review #7: the pickup rule's starts are counted, and parked rows waiting for the user are listed.

reference/pickup.md lets a session start a row the user did not name when it blocks
the release (b) or sits in the task's path (c). Those starts are now recorded in the
session tally, and verify_ledger lists bare-@parked rows apart from set-aside ones.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills' / 'unforget' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import defer_tally  # noqa: E402

HEADER = ('<!-- unforget-format: v2 -->\n## 3. Audit findings\n\n'
          '| # | Target | Finding | Urgency | Risk: Fix | Risk: No Fix | ROI | Blast Radius | Fix Effort | Status |\n'
          '|---|---|---|---|---|---|---|---|---|---|\n')


def row(rid, target, status):
    return f'| {rid} | {target} | Finding {rid} | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | Small | {status} |\n'


class StartTallyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_no_starts_leaves_the_readout_unchanged(self):
        r = defer_tally.record(self.dir, 'fixed-now', None)
        self.assertNotIn('started', r['readout'])

    def test_unnamed_starts_are_listed_by_id(self):
        defer_tally.record(self.dir, 'started', None, 'A1', 'named')
        defer_tally.record(self.dir, 'started', None, 'A12', 'in-path')
        r = defer_tally.record(self.dir, 'started', None, 'A3', 'this')
        self.assertIn("started 3 (1 you named, 2 you didn't: A12 in the path, A3 release blocker)",
                      r['readout'])
        self.assertTrue(r['flag'])
        self.assertIn("didn't name", r['advisory'])

    def test_named_starts_alone_never_flag(self):
        for rid in ('A1', 'A2', 'A3'):
            r = defer_tally.record(self.dir, 'started', None, rid, 'named')
        self.assertFalse(r['flag'])
        self.assertIn('started 3 (3 you named, 0 you didn\'t)', r['readout'])

    def test_one_unnamed_start_does_not_flag(self):
        r = defer_tally.record(self.dir, 'started', None, 'A3', 'this')
        self.assertFalse(r['flag'])

    def test_unknown_condition_is_refused(self):
        with self.assertRaises(ValueError):
            defer_tally.record(self.dir, 'started', None, 'A1', 'quick')

    def test_tally_survives_reload_and_reset_clears_it(self):
        defer_tally.record(self.dir, 'started', None, 'A3', 'this')
        state = defer_tally.load_state(self.dir)
        self.assertEqual(state['started'], {'this': 1})
        self.assertEqual(state['started_unnamed'], [['A3', 'this']])
        subprocess.run([sys.executable, str(SCRIPTS / 'defer_tally.py'), 'reset', '--dir', str(self.dir)],
                       capture_output=True, check=True)
        self.assertEqual(defer_tally.load_state(self.dir)['started'], {})

    def test_old_state_file_without_started_still_loads(self):
        (self.dir / defer_tally.STATE_NAME).write_text('{"fixed_now": 2, "deferred": 1, "reasons": {}}')
        r = defer_tally.record(self.dir, 'started', None, 'A9', 'in-path')
        self.assertEqual(r['session']['fixed_now'], 2)
        self.assertIn('A9 in the path', r['readout'])

    def test_cli_started_needs_id_and_condition(self):
        base = [sys.executable, str(SCRIPTS / 'defer_tally.py'), 'record', '--dir', str(self.dir),
                '--outcome', 'started']
        self.assertEqual(subprocess.run(base, capture_output=True).returncode, 2)
        ok = subprocess.run(base + ['--id', 'A3', '--condition', 'this'], capture_output=True, text=True)
        self.assertIn('A3 release blocker', json.loads(ok.stdout)['readout'])


class ParkedWaitingTests(unittest.TestCase):
    def test_verify_lists_waiting_rows_apart_from_set_aside_and_closed(self):
        text = HEADER + ''.join([
            row('A1', '⚪ SOMEDAY', '`@status:open` `@parked` Logged by a session'),
            row('A2', '🔴 THIS', '`@status:open` `@parked`'),
            row('A3', '⚪ SOMEDAY', '`@status:open` `@likelihood:rare` `@basis:reviewed` `@parked:likelihood`'),
            row('A4', '⚪ SOMEDAY', '`@status:withdrawn` `@parked`'),
            row('A5', '🔵 NEXT', '`@status:open`'),
        ])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'UNFORGET.md'
            path.write_text(text, encoding='utf-8')
            out = json.loads(subprocess.run([sys.executable, str(SCRIPTS / 'verify_ledger.py'), '--file',
                                             str(path)], capture_output=True, text=True).stdout)
        self.assertEqual(out['parked_waiting'], ['A1', 'A2'])
        self.assertEqual(out['set_aside'], ['A3'])
        self.assertIn('2 row(s) logged by a session are waiting for you: A1, A2', out['advisory'])
        self.assertIn('A2', out['this_open'], 'a parked THIS row still blocks release')


if __name__ == '__main__':
    unittest.main()
