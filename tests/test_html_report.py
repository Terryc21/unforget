"""Observable report invariants, not wording snapshots."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/html_report.py'
spec=importlib.util.spec_from_file_location('html_report',SCRIPT)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
HEADER='<!-- unforget-format: v2 -->\n## Audit\n| # | Target | Finding | Urgency | Status |\n|---|---|---|---|---|\n'

class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'UNFORGET.md'
    def load(self,rows,header=HEADER):
        self.path.write_text(header+rows);return h.read_ledger(self.path)
    def args(self,*flags):
        a=h.parser().parse_args(['--file',str(self.path),'--output',str(Path(self.tmp.name)/'report.html'),*flags]);a.sort=a.sort.split(',');a.columns=a.columns.split(',');return a
    def test_owed_this_blocks_even_if_code_done(self):
        rows,_,_=self.load('| A48a | 🚢 THIS | Code repaired | 🟡 HIGH | @status:done-unverified @verified:code |\n| A48b | THIS | Closed | HIGH | @status:done-verified @verified:device |')
        selected=h.select(rows,self.args());self.assertEqual([r['id'] for r in selected],['A48a']);self.assertTrue(selected[0]['blocker'])
    def test_status_quote_in_finding_is_not_status(self):
        rows,_,_=self.load('| A1 | NEXT | Sibling @status:done-verified | LOW | @status:open |')
        self.assertEqual(rows[0]['status'],'open')
    def test_status_before_extra_column_no_trailing_pipe(self):
        header=HEADER.replace('Status |','Status | 1-Star Risk |').replace('|---|---|---|---|---|','|---|---|---|---|---|---|')
        rows,_,_=self.load('| MI-08 | THIS | item | HIGH | @status:open | None',header)
        self.assertEqual(rows[0]['status'],'open')
    def test_other_tables_are_not_obligations(self):
        rows,_,_=self.load('| A1 | THIS | item | HIGH | @status:open |\n\n| ID | Why |\n|---|---|\n| A1 | duplicate summary |')
        self.assertEqual(len(rows),1)
    def test_malformed_rejected(self):
        with self.assertRaises(ValueError):self.load('| A1 | THIS | missing cells |')
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):self.load('| A1 | THIS | one | HIGH | @status:open |\n| A1 | NEXT | two | LOW | @status:open |')
    def test_escaped_pipe_preserved(self):
        rows,_,_=self.load('| A1 | NEXT | A \\| B | LOW | @status:open |')
        self.assertIn('\\|',rows[0]['finding'])
    def test_this_in_finding_does_not_gate_phase_ledger(self):
        rows,_,_=self.load('| MI-18 | THIS is a quote | 4 | @status:open |','<!-- unforget-format: v2 -->\n| ID | Finding | Phase | Status |\n|---|---|---|---|\n')
        self.assertFalse(rows[0]['blocker'])
    def test_compact_this(self):
        rows,_,_=self.load('| A1 | **🔴 THIS · An item** | HIGH | @status:open |','<!-- unforget-format: v2 -->\n| # | Finding | Urgency | Status |\n|---|---|---|---|\n')
        self.assertTrue(rows[0]['blocker'])
    def test_legacy_partial_and_unknown_stay_visible(self):
        rows,_,warnings=self.load('| A1 | NEXT | item | LOW | Fixed; device owed |\n| A2 | NEXT | item | LOW | verified |\n| A3 | NEXT | item | LOW | Fixed |')
        self.assertEqual([r['id'] for r in h.select(rows,self.args())],['A1','A2']);self.assertTrue(warnings)
    def test_explicit_status_overrides_view(self):
        rows,_,_=self.load('| A1 | NEXT | item | LOW | @status:done-verified @verified:device |')
        self.assertEqual(len(h.select(rows,self.args('--status','done-verified'))),1)
    def test_custom_sort_and_unknown_last(self):
        rows,_,_=self.load('| A1 | NEXT | one | LOW | @status:open |\n| A2 | NEXT | two | HIGH | @status:open |\n| A3 | NEXT | three | — | @status:open |')
        h.annotate(rows,{'UNFORGET.md::A1':{'ux':'severe','ux_basis':'Recorded data loss.'}})
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--sort','ux,urgency'))],['A1','A2','A3'])
    def test_annotations_cannot_fake_closure(self):
        rows,_,_=self.load('| A1 | THIS | one | HIGH | @status:open |')
        with self.assertRaises(ValueError):h.annotate(rows,{'UNFORGET.md::A1':{'status':'done-verified'}})
        with self.assertRaises(ValueError):h.annotate(rows,{'UNFORGET.md::A1':{'ux':'severe'}})
    def test_filters_dont_erase_input_blocker_count_and_html_is_escaped(self):
        rows,sources,_=self.load('| A1 | THIS | private | HIGH | @status:open |\n| A2 | NEXT | <script>alert(1)</script> @@ROWS@@ | LOW | @status:open |')
        args=self.args('--target','NEXT');selected=h.select(rows,args)
        output=h.render(selected,[sources],[],args,1)
        self.assertIn('1 recorded release blockers across',output)
        self.assertNotIn('<script>alert(1)</script>',output)
        self.assertIn('&lt;script&gt;',output);self.assertIn('@@ROWS@@',output)
    def test_reviewed_subset_and_empty_results(self):
        rows,_,_=self.load('| A1 | THIS | one | HIGH | @status:open |\n| A2 | NEXT | two | LOW | @status:open |')
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--id','A2'))],['A2'])
        self.assertEqual(h.select(rows,self.args('--query','does not exist')),[])

if __name__=='__main__':unittest.main()
