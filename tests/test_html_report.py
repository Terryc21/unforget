"""Observable report invariants, not wording snapshots."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/html_report.py'
spec=importlib.util.spec_from_file_location('html_report',SCRIPT)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
HEADER='<!-- unforget-format: v2 -->\n## Audit\n| # | Target | Finding | Urgency | Status |\n|---|---|---|---|---|\n'

class LedgerHelpers:
    """Temp-ledger helpers shared by the test classes (a mixin, so no class inherits another's tests)."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'UNFORGET.md'
    def load(self,rows,header=HEADER):
        self.path.write_text(header+rows);return h.read_ledger(self.path)
    def args(self,*flags):
        a=h.parser().parse_args(['--file',str(self.path),'--output',str(Path(self.tmp.name)/'report.html'),*flags]);a.sort=a.sort.split(',');a.columns=a.columns.split(',');return a

class ReportTests(LedgerHelpers, unittest.TestCase):
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
    def test_abbreviated_urgency_header_and_critical_value(self):
        rows,_,_=self.load('| A1 | NEXT | one | HIGH | @status:open |\n| A2 | NEXT | two | CRIT | @status:open |\n| A3 | NEXT | three | MED | @status:open |', HEADER.replace('Urgency', 'Urg'))
        selected=h.select(rows,self.args())
        self.assertEqual([r['id'] for r in selected],['A2','A1','A3'])
        self.assertEqual([r['urgency'] for r in selected],['critical','high','medium'])
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



HEADER_RATED='<!-- unforget-format: v2 -->\n## Audit\n| # | Target | Finding | Urgency | ROI | Fix Effort | Status |\n|---|---|---|---|---|---|---|\n'

class LimitAndFilterTests(LedgerHelpers, unittest.TestCase):
    def rated(self,rows):
        return self.load(rows,HEADER_RATED)[0]
    def test_limit_caps_rows_and_reports_matched(self):
        rows=self.rated('| A1 | NEXT | a | HIGH | Good | Small | @status:open |\n| A2 | NEXT | b | MED | Good | Small | @status:open |\n| A3 | NEXT | c | LOW | Good | Small | @status:open |')
        a=self.args('--limit','2');selected=h.select(rows,a)
        self.assertEqual([r['id'] for r in selected],['A1','A2'])
        self.assertEqual((a.select_info['matched'],a.select_info['shown'],a.select_info['extra_blockers']),(3,2,0))
    def test_limit_never_hides_a_release_blocker(self):
        rows=self.rated('| A1 | NEXT | a | HIGH | Good | Small | @status:open |\n| A2 | NEXT | b | HIGH | Good | Small | @status:open |\n| A3 | THIS | blocker | LOW | Good | Small | @status:open |')
        a=self.args('--limit','1','--sort','urgency');selected=h.select(rows,a)
        self.assertEqual([r['id'] for r in selected],['A1','A3'])
        self.assertEqual(a.select_info['extra_blockers'],1)
    def test_tie_at_the_cut_goes_to_the_faster_fix(self):
        rows=self.rated('| A1 | NEXT | a | HIGH | Good | Large | @status:open |\n| A2 | NEXT | b | HIGH | Good | Trivial | @status:open |')
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--limit','1','--sort','urgency'))],['A2'])
    def test_effort_filter_and_unclassified_count(self):
        rows=self.rated('| A1 | NEXT | a | HIGH | Good | Trivial | @status:open |\n| A2 | NEXT | b | HIGH | Good | Small-Med | @status:open |\n| A3 | NEXT | c | HIGH | Good | Done | @status:open |\n| A4 | NEXT | d | HIGH | Good | 🟢 Triv | @status:open |')
        a=self.args('--effort','trivial');selected=h.select(rows,a)
        self.assertEqual(sorted(r['id'] for r in selected),['A1','A4'])
        self.assertEqual(a.select_info['unclassified']['effort'],1)
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--effort','unrated'))],['A3'])
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--effort','small'))],['A2'])
    def test_roi_filter_and_sort(self):
        rows=self.rated('| A1 | NEXT | a | HIGH | 🟢 Good | Small | @status:open |\n| A2 | NEXT | b | HIGH | 🟠 Excellent | Small | @status:open |\n| A3 | NEXT | c | HIGH | 🔵 High | Small | @status:open |')
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--sort','roi'))],['A2','A1','A3'])
        a=self.args('--roi','excellent');self.assertEqual([r['id'] for r in h.select(rows,a)],['A2'])
        self.assertEqual(a.select_info['unclassified']['roi'],1)
    def test_cut_note_is_visible_not_collapsed(self):
        rows=self.rated('| A1 | NEXT | a | HIGH | Good | Small | @status:open |\n| A2 | NEXT | b | LOW | Good | Small | @status:open |')
        a=self.args('--limit','1');page=h.render(h.select(rows,a),[],[],a,0)
        shown=page.find('Showing 1 of 2');collapsed=page.find('<summary>Criteria')
        self.assertNotEqual(shown,-1);self.assertLess(shown,collapsed)
    def test_no_limit_means_no_cap(self):
        rows=self.rated('| A1 | NEXT | a | HIGH | Good | Small | @status:open |\n| A2 | NEXT | b | LOW | Good | Small | @status:open |')
        a=self.args();self.assertEqual(len(h.select(rows,a)),2);self.assertEqual(a.select_info['matched'],2)



def registry_readme(*pairs):
    rows=''.join(f'| {k} | {v} |\n' for k,v in pairs)
    return ('# Ledgers\n\n<!-- unforget-registry:begin -->\n\n**Global**\n\n| key | value |\n|---|---|\n'
            + rows + '\n<!-- unforget-registry:end -->\n')

class VocabularyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name);self.path=self.dir/'UNFORGET.md'
    def load(self,rows,header,*pairs):
        if pairs:(self.dir/'README.md').write_text(registry_readme(*pairs))
        self.path.write_text(header+rows);return h.read_ledger(self.path)
    def args(self,*flags):
        a=h.parser().parse_args(['--file',str(self.path),'--output',str(self.dir/'r.html'),*flags]);a.sort=a.sort.split(',');a.columns=a.columns.split(',');return a
    SIZE='<!-- unforget-format: v2 -->\n## Audit\n| # | Target | Finding | Urgency | Size | Value | Status |\n|---|---|---|---|---|---|---|\n'
    ROWS='| A1 | NEXT | a | HIGH | XS | High | @status:open |\n| A2 | NEXT | b | HIGH | L | Low | @status:open |\n| A3 | NEXT | c | HIGH | M | High | @status:open |'
    def test_project_words_and_columns_classify_rows(self):
        rows,_,warnings=self.load(self.ROWS,self.SIZE,('report_effort_column','Size'),('report_roi_column','Value'),
                                  ('report_effort_words','XS=trivial, S=small, M=medium, L=large'),('report_roi_words','High=good, Low=poor'))
        a=self.args('--effort','trivial');self.assertEqual([r['id'] for r in h.select(rows,a)],['A1'])
        self.assertEqual(a.select_info['unclassified']['effort'],0)
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--roi','good'))],['A1','A3'])
        self.assertTrue(any('Project vocabulary' in w for w in warnings))
    def test_without_registry_the_same_rows_are_unclassified(self):
        rows,_,_=self.load(self.ROWS,self.SIZE)   # negative control: no README, no mapping
        a=self.args('--effort','trivial');self.assertEqual(h.select(rows,a),[])
        self.assertEqual(a.select_info['unclassified']['effort'],3)
    def test_project_word_overrides_builtin(self):
        hdr='<!-- unforget-format: v2 -->\n## Audit\n| # | Target | Finding | Urgency | Fix Effort | Status |\n|---|---|---|---|---|---|\n'
        rows,_,_=self.load('| A1 | NEXT | a | HIGH | Small | @status:open |',hdr,('report_effort_words','Small=trivial'))
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--effort','trivial'))],['A1'])
    def test_bad_entries_are_reported_not_applied(self):
        hdr='<!-- unforget-format: v2 -->\n## Audit\n| # | Target | Finding | Urgency | Fix Effort | Status |\n|---|---|---|---|---|---|\n'
        rows,_,warnings=self.load('| A1 | NEXT | a | HIGH | XS | @status:open |',hdr,('report_effort_words','XS=tiny, S'))
        self.assertTrue(any('ignored XS=tiny, S' in w for w in warnings))
        self.assertEqual(h.select(rows,self.args('--effort','trivial')),[])
    def test_vocabulary_survives_a_rewritten_source_path(self):
        rows,_,_=self.load(self.ROWS,self.SIZE,('report_effort_column','Size'),('report_effort_words','XS=trivial'))
        for r in rows: r['source']='UNFORGET.md'   # what examples/generate_html.py does
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--effort','trivial'))],['A1'])
    def test_internal_path_key_never_reaches_the_page(self):
        rows,_,_=self.load(self.ROWS,self.SIZE)
        for r in rows: r['source']='UNFORGET.md'
        a=self.args();page=h.render(h.select(rows,a),[],[],a,0)
        self.assertNotIn(self.tmp.name.casefold(),page.casefold())   # the page lowercases its search text
        self.assertEqual(h.select(rows,self.args('--query',Path(self.tmp.name).name)),[])
    def test_punctuated_project_words_are_text_not_patterns(self):
        rows,_,_=self.load('| A1 | NEXT | a | HIGH | M+ | @status:open |\n| A2 | NEXT | b | HIGH | (S) | @status:open |\n| A3 | NEXT | c | HIGH | MMM | @status:open |',
                           self.SIZE.replace('| Value ','').replace('|---|---|---|---|---|---|---|','|---|---|---|---|---|---|'),
                           ('report_effort_column','Size'),('report_effort_words','M+=large, (S)=small'))
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--effort','large'))],['A1'])
        self.assertEqual([r['id'] for r in h.select(rows,self.args('--effort','small'))],['A2'])
        a=self.args('--effort','large');h.select(rows,a);self.assertEqual(a.select_info['unclassified']['effort'],1)  # MMM
    def test_malformed_registry_is_reported_not_silently_ignored(self):
        (self.dir/'README.md').write_text('<!-- unforget-registry:begin -->\n| report_effort_words | XS=trivial |\n')  # no end marker
        self.path.write_text(self.SIZE+self.ROWS)
        _,_,warnings=h.read_ledger(self.path)
        self.assertTrue(any('registry unreadable' in w for w in warnings))
    def test_vocabulary_does_not_leak_into_query(self):
        hdr='<!-- unforget-format: v2 -->\n## Audit\n| # | Target | Finding | Urgency | Fix Effort | Status |\n|---|---|---|---|---|---|\n'
        rows,_,_=self.load('| A1 | NEXT | a | HIGH | Small | @status:open |',hdr,('report_effort_words','Zebra=trivial'))
        self.assertEqual(h.select(rows,self.args('--query','zebra')),[])


class ActionReportTests(LedgerHelpers, unittest.TestCase):
    def test_project_names_do_not_leak_between_inputs(self):
        rows,_,_=self.load('| A1 | NEXT | USER ACTION: confirm account setting | HIGH | @status:open |')
        row=rows[0]
        h.prepare_presentation(rows,{str(self.path.resolve().parent):{'user_name':'Morgan','user_label':'name'}})
        self.assertEqual(row['owner'],'Morgan');self.assertEqual(row['owner_source'],'recorded')
        rows,_,_=self.load('| A1 | NEXT | Needs account access | HIGH | @status:open |')
        h.prepare_presentation(rows)
        self.assertEqual(rows[0]['owner'],'You');self.assertEqual(rows[0]['owner_source'],'suggested')
        self.assertNotIn('Morgan',str(rows))
    def test_unknown_is_unassigned_not_user(self):
        rows,_,_=self.load('| A1 | NEXT | Product discussion | HIGH | @status:open |')
        h.prepare_presentation(rows)
        self.assertEqual(rows[0]['owner'],'Unassigned');self.assertEqual(rows[0]['readiness'],'unknown')
    def test_suggestions_and_confirmed_named_owners(self):
        rows,_,_=self.load('| A1 | NEXT | Fix HTML copy | HIGH | @status:open |')
        h.prepare_presentation(rows)
        self.assertEqual(rows[0]['owner'],'Coding assistant');self.assertEqual(rows[0]['owner_source'],'suggested')
        h.annotate(rows,{'UNFORGET.md::A1':{'owner':'Release team','owner_kind':'team','owner_source':'explicit','owner_basis':'User assigned the release team.'}})
        h.prepare_presentation(rows)
        self.assertEqual(rows[0]['owner'],'Release team');self.assertEqual(rows[0]['owner_source'],'explicit')
    def test_changing_recorded_owner_cannot_inherit_confirmation(self):
        header=HEADER.replace('Status |','Status | Owner |').replace('|---|---|---|---|---|','|---|---|---|---|---|---|')
        rows,_,_=self.load('| A1 | NEXT | Fix HTML copy | HIGH | @status:open | Robin |',header)
        h.annotate(rows,{'UNFORGET.md::A1':{'owner':'Alex'}})
        self.assertEqual(rows[0]['owner_source'],'suggested')
    def test_last_checked_requires_actual_evidence_and_is_not_generated(self):
        rows,_,_=self.load('| A1 | NEXT | fix | HIGH | @status:open |')
        with self.assertRaises(ValueError):h.annotate(rows,{'UNFORGET.md::A1':{'last_checked':'2026-10-07'}})
        with self.assertRaises(ValueError):h.annotate(rows,{'UNFORGET.md::A1':{'last_checked':'2026-02-30','check_basis':'Checked'}})
        h.prepare_presentation(rows)
        self.assertEqual(rows[0]['last_checked'],'')
    def test_reconciliation_and_dependencies_prevent_ready(self):
        rows,_,_=self.load('| A1 | THIS | Fix | HIGH | @status:open |')
        h.annotate(rows,{'UNFORGET.md::A1':{'readiness':'ready','readiness_basis':'Reviewed','reconciliation':'Source conflicts with current files.'}})
        h.prepare_presentation(rows)
        self.assertNotEqual(rows[0]['readiness'],'ready');self.assertTrue(rows[0]['blocker']);self.assertEqual(rows[0]['status'],'open')
        rows[0]['reconciliation']='';rows[0]['dependencies']='Account access';rows[0]['readiness']='ready'
        h.prepare_presentation(rows);self.assertEqual(rows[0]['readiness'],'waiting')
    def test_annotations_cannot_dismiss_canonical_verification(self):
        rows,_,_=self.load('| A1 | THIS | Fix | HIGH | @status:done-unverified |')
        h.annotate(rows,{'UNFORGET.md::A1':{'verification_owed':False,'readiness':'ready','readiness_basis':'Code compiles'}})
        h.prepare_presentation(rows)
        self.assertTrue(rows[0]['verification_owed']);self.assertNotEqual(rows[0]['readiness'],'ready');self.assertTrue(rows[0]['blocker'])
    def test_details_and_annotation_html_are_escaped(self):
        rows,source,_=self.load('| A1 | NEXT | Fix | HIGH | @status:open |\n\n### Detail\n- **A1** - <img src=x onerror=alert(1)> evidence\n\n- **A2** - unrelated evidence')
        h.annotate(rows,{'UNFORGET.md::A1':{'owner':'<script>bad</script>','reconciliation':'<svg onload=bad()>','last_checked':'2026-10-07','check_basis':'Read file'}})
        h.prepare_presentation(rows);out=h.render(h.select(rows,self.args()),[source],[],self.args(),0)
        self.assertNotIn('<script>bad</script>',out);self.assertNotIn('<img src=x',out);self.assertIn('&lt;img',out)
        self.assertIn('onerror=alert(1)',rows[0]['detail']);self.assertNotIn('unrelated evidence',rows[0]['detail'])
    def test_registry_is_scoped_and_readme_beats_cache(self):
        (self.path.parent/'README.md').write_text('<!-- unforget-registry:begin -->\n**Global**\n| key | value |\n|---|---|\n| report_user_name | Sam |\n| report_user_label | name |\n**Ledgers**\n<!-- unforget-registry:end -->')
        (self.path.parent/'.unforget.json').write_text('{"global":{"report_user_name":"Wrong person"}}')
        self.assertEqual(h.project_settings(self.path.parent)['user_name'],'Sam')
    def test_named_assignee_requires_name_and_confirmed_provenance_requires_basis(self):
        rows,_,_=self.load('| A1 | NEXT | Fix | HIGH | @status:open |')
        with self.assertRaises(ValueError):h.annotate(rows,{'UNFORGET.md::A1':{'owner_kind':'person'}})
        with self.assertRaises(ValueError):h.annotate(rows,{'UNFORGET.md::A1':{'owner':'Alex','owner_source':'explicit'}})


    def test_invalid_closure_cannot_be_presented_as_ready(self):
        rows,_,_=self.load('| A1 | THIS | Fix | HIGH | @status:done-verified |')
        h.annotate(rows,{'UNFORGET.md::A1':{'readiness':'ready','readiness_basis':'Implementation reviewed'}})
        h.prepare_presentation(rows)
        self.assertFalse(rows[0]['completed'])
        self.assertTrue(rows[0]['blocker'])
        self.assertNotEqual(rows[0]['readiness'],'ready')

    def test_gallery_source_link_resolves_beside_report(self):
        rows,source,_=self.load('| A1 | NEXT | Fix | HIGH | @status:open |')
        rows[0]['source']='examples/UNFORGET.md'
        rows[0]['source_link']='UNFORGET.md'
        h.prepare_presentation(rows)
        out=h.render(h.select(rows,self.args()),[source],[],self.args(),0)
        self.assertIn('href="UNFORGET.md"',out)
        self.assertNotIn('href="examples/UNFORGET.md"',out)

if __name__=='__main__':unittest.main()
