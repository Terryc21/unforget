"""ASC unforget 1 regressions. Only disposable projects/memory/recipes are used."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get('UNFORGET_TEST_ROOT', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / 'scripts'))
import parse_status as ps
import registry
import recall_block as recall
import row_budget as rb
import recipe
import scan_surfaces as scan
import html_report as report
import display_prefs as prefs
import import_drift
import verify_ledger as verify
import verify_install

HEADER = '| # | Target | Finding | Urgency | Effort | Status | Risk |\n|---|---|---|---|---|---|---|\n'
def ledger(status='`@status:open`', finding='Issue', target='THIS'):
    return '<!-- unforget-format: v2 -->\n## 3. Audit findings\n\n' + HEADER + f'| A1 | {target} | {finding} | High | Sml | {status} | Low |\n'

def cli(script, *args):
    return subprocess.run([sys.executable, str(ROOT/'scripts'/script), *map(str,args)], capture_output=True, text=True)

class Regressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='unforget regression ')
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def write(self, name, text):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
    def seed_registry(self, **cfg):
        registry.write_registry(self.root, cfg, [{'name':'UNFORGET.md','path':'UNFORGET.md'}, {'name':'CHILD.md','path':'CHILD.md'}])
        self.write('UNFORGET.md',ledger());self.write('CHILD.md',ledger())
    def test_F8_harness_space_path_counts_fail_pass_skip(self):
        dst=self.root/'path with spaces'/'behavioral'
        shutil.copytree(ROOT/'tests/behavioral',dst,ignore=shutil.ignore_patterns('result.md'))
        case=dst/'03-edit-target';result=case/'result.md';result.write_bytes((case/'input.md').read_bytes())
        direct=subprocess.run([sys.executable,str(dst/'check_behavioral.py'),'--case',str(case)],capture_output=True,text=True)
        self.assertNotEqual(direct.returncode,0)
        def run():return subprocess.run(['bash',str(dst/'run-behavioral.sh'),'--check'],capture_output=True,text=True)
        bad=run();self.assertNotEqual(bad.returncode,0);self.assertIn('1 run,',bad.stdout);self.assertIn('1 failed.',bad.stdout)
        result.write_text(result.read_text().replace('| A1 | 🟡 LATER |','| A1 | 🔴 THIS |'))
        good=run();self.assertEqual(good.returncode,0,good.stdout);self.assertIn('1 run,',good.stdout)
        result.unlink();missing=run();self.assertIn('0 run,',missing.stdout);self.assertIn('skipped, 0 failed.',missing.stdout)
        listing=subprocess.run(['bash',str(dst/'run-behavioral.sh'),'--list'],capture_output=True,text=True)
        self.assertEqual(listing.returncode,0);self.assertIn('03-edit-target',listing.stdout)
    def test_F14_supported_v2_future_v3_unchanged(self):
        for version,allowed in [('v2',True),('v3',False)]:
            p=self.write(version+'.md',ledger().replace('v2',version));before=p.read_bytes()
            result=json.loads(cli('check_format_version.py',p).stdout)
            self.assertEqual(result['recognized'],allowed)
            self.assertEqual(result['writable'],allowed)
            self.assertEqual(p.read_bytes(),before)
        self.assertIn('v3', (ROOT/'tests/behavioral/06-format-version-refusal/input.md').read_text().splitlines()[0])
    def test_F1_registry_malformed_refuses_without_any_write(self):
        b,e=registry.BEGIN,registry.END
        for malformed in [b+'\nHUMAN',e+'\nHUMAN',e+b,b+b+e,b+e+e,b+e+b+e]:
            with self.subTest(markers=malformed):
                readme=self.write('README.md','opening\n'+malformed+'\ntrailing human\n');cache=self.write('.unforget.json','cache sentinel')
                payload=self.write('payload.json','{"global":{},"ledgers":[]}')
                before=[p.read_bytes() for p in (readme,cache)]
                result=cli('registry.py','write','--dir',self.root,'--json',payload)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual([p.read_bytes() for p in (readme,cache)],before)
    def test_F1_recall_preflights_before_registry_home(self):
        self.seed_registry(recall_home='old')
        for name in ['AGENTS.md','CLAUDE.md']:
            for malformed in [recall.BEGIN,recall.END,recall.END+recall.BEGIN,recall.BEGIN*2+recall.END,recall.BEGIN+recall.END*2]:
                p=self.write(name,'human\n'+malformed+'\ntrailing rules')
                files=[p,self.root/'README.md',self.root/'.unforget.json'];before=[x.read_bytes() for x in files]
                out=cli('recall_block.py','write','--dir',self.root,'--file',p,'--home','new')
                self.assertNotEqual(out.returncode,0)
                self.assertEqual([x.read_bytes() for x in files],before)
    def test_F1_valid_append_update_idempotent(self):
        self.seed_registry()
        for name in ['AGENTS.md','CLAUDE.md']:
            p=self.write(name,'Human instructions\n\n')
            args=['write','--dir',self.root,'--file',p]
            self.assertEqual(cli('recall_block.py',*args).returncode,0)
            first=p.read_bytes();self.assertTrue(first.startswith(b'Human instructions\n\n'))
            self.assertEqual(cli('recall_block.py',*args).returncode,0);self.assertEqual(p.read_bytes(),first)
    def test_F1_branch_malformed_recall_is_atomic(self):
        p=self.write('AGENTS.md',recall.BEGIN+'\nHUMAN')
        self.seed_registry(recall_block='maintained',recall_file=str(p))
        files=[p,self.root/'README.md',self.root/'.unforget.json',self.root/'UNFORGET.md'];before=[x.read_bytes() for x in files]
        out=cli('branch_create.py','--dir',self.root,'--parent','UNFORGET.md','--name','NEW','--axis','domain','--discipline','other')
        self.assertNotEqual(out.returncode,0)
        self.assertEqual([x.read_bytes() for x in files],before)
        self.assertFalse((self.root/'NEW.md').exists())
    def spec(self,cmd,expected=0):return dict(id='A1',command=cmd,op='=',expected=expected,describes='closed')
    def test_F4_mutators_rejected_before_launch(self):
        self.write('file.txt','X\n')
        for cmd in ["python3 -c \"open('sentinel','w').write('x')\"",'find . -delete','sed -i x file.txt','awk x file.txt','rg -c --pre cat X file.txt','grep -c --include=x X file.txt','grep -c X ../out','grep -c X /tmp/out','grep -c X file.txt; touch sentinel']:
            with self.subTest(cmd=cmd), patch.object(recipe.subprocess,'run') as run:
                out=recipe.run_recipe(self.spec(cmd),self.root)
                self.assertEqual(out['outcome'],'UNRUNNABLE');run.assert_not_called()
        self.assertFalse((self.root/'sentinel').exists())
    def test_F4_symlink_escape_rejected(self):
        outside=self.root.parent/(self.root.name+' outside');outside.write_text('X')
        try:
            (self.root/'link').symlink_to(outside)
            with patch.object(recipe.subprocess,'run') as run:
                self.assertEqual(recipe.run_recipe(self.spec('grep -c X link'),self.root)['outcome'],'UNRUNNABLE');run.assert_not_called()
        finally:outside.unlink()
    def test_F6_real_count_zero_positive_multifile(self):
        self.write('one.txt','X\nX\n');self.write('two file.txt','X\n')
        for tool in ['grep','rg']:
            if not shutil.which(tool):continue
            for args,expected in [("-c X one.txt",2),("-c X -- one.txt",2),("-c Z one.txt",0),("-c X one.txt 'two file.txt'",3),("-c -e --pre one.txt",0)]:
                with self.subTest(tool=tool,args=args):
                    out=recipe.run_recipe(self.spec(tool+' '+args,expected),self.root)
                    self.assertEqual(out['outcome'],'FIXED',out);self.assertEqual(out['actual'],expected)
        out=recipe.run_recipe(self.spec('grep --not-a-real-option X one.txt'),self.root)
        self.assertEqual(out['outcome'],'UNRUNNABLE')
    def test_F6_errors_never_become_zero(self):
        self.write('one.txt','X')
        for rc,stdout,stderr in [(2,'',''),(-9,'',''),(0,'',''),(0,'1\nbad',''),(1,'3',''),(0,'0','permission denied')]:
            with patch.object(recipe.subprocess,'run',return_value=subprocess.CompletedProcess([],rc,stdout,stderr)):
                self.assertEqual(recipe.run_recipe(self.spec('grep -c X one.txt'),self.root)['outcome'],'DECAYED')
        for err in [FileNotFoundError(),PermissionError(),subprocess.TimeoutExpired('grep',5)]:
            with patch.object(recipe.subprocess,'run',side_effect=err):
                self.assertEqual(recipe.run_recipe(self.spec('grep -c X one.txt'),self.root)['outcome'],'DECAYED')
    def test_F12_memory_pin_containment(self):
        mem=self.root/'memory root';mem.mkdir();outside=self.root/'outside';outside.mkdir()
        (outside/'deferred_secret.md').write_text('private synthetic')
        valid=mem/'-encoded-name'/'memory';valid.mkdir(parents=True);(valid/'deferred_work.md').write_text('Work')
        p=self.write('pin.md','<!-- unforget-config: memory-dir=-encoded-name -->')
        self.assertEqual(len(scan.scan_memory_files(self.root,p,mem)['candidates']),1)
        for pin in [str(outside),'../../outside',r'..\outside','C:\\outside']:
            p.write_text(f'<!-- unforget-config: memory-dir={pin} -->')
            out=scan.scan_memory_files(self.root,p,mem);self.assertEqual(out['candidates'],[]);self.assertEqual(out['pin_action']['action'],'invalid')
        (mem/'escape').symlink_to(outside);p.write_text('<!-- unforget-config: memory-dir=escape -->')
        self.assertEqual(scan.scan_memory_files(self.root,p,mem)['pin_action']['action'],'invalid')
        (valid/'deferred_escape.md').symlink_to(outside/'deferred_secret.md');p.write_text('<!-- unforget-config: memory-dir=-encoded-name -->')
        with patch.object(scan,'read_text',wraps=scan.read_text) as read:
            out=scan.scan_memory_files(self.root,p,mem)
            self.assertEqual(len(out['candidates']),1)
            self.assertNotIn(valid/'deferred_escape.md',[c.args[0] for c in read.call_args_list])
    def test_F11_code_sufficiency_local_nonempty(self):
        base=ledger('`@status:done-verified` `@verified:code`')
        for tail,closed in [('',False),('\n### Detail - audit\n- **A1** - Evidence\n  Code-is-sufficient: Pure function; deterministic coverage.',True),('\n### Detail - audit\n- **A2** - Evidence\n  Code-is-sufficient: Other row',False),('\n### Detail - audit\n- **A1** - Evidence\n  Code-is-sufficient:   \n',False)]:
            parsed=ps.parse_file(base+tail)[0];self.assertEqual(parsed['archivable'],closed);self.assertEqual(parsed['blocks_release'],not closed)
        for tier,note,closed in [('code','Code-is-sufficient: Pure function tested.',True),('code','tests passed',False),('session-claimed','Code-is-sufficient: reason',False),('device','',True),('user','',True),('code','Code-is-sufficient: still broken',False)]:
            parsed=ps.parse_file(ledger(f'`@status:done-verified` `@verified:{tier}` {note}'))[0]
            self.assertEqual(parsed['archivable'],closed,(tier,note,parsed))
    def test_F3_html_verifier_closure_parity(self):
        cases=[('`@status:done-verified`',False),('`@status:done-verified` `@verified:session-claimed`',False),('`@status:done-verified` `@verified:device` still broken',False),('`@status:done-verified` `@verified:code`',False),('`@status:done-verified` `@verified:code` Code-is-sufficient: deterministic logic',True),('`@status:open`',False),('`@status:blocked`',False),('`@status:done-unverified`',False),('`@status:withdrawn` still broken',False),('`@status:done-verified` `@verified:device`',True),('Not fixed',False),('Fixed; not verified',False),('Fixed; verification failed',False),('Done; failed on device',False),('Fixed; device verification pending',False),('Open; unit tests passed',False),('Fixed',True)]
        for status,closed in cases:
            with self.subTest(status=status):
                p=self.write('UNFORGET.md',ledger(status));rows,_,warnings=report.read_ledger(p)
                self.assertEqual(rows[0]['completed'],closed);self.assertEqual(rows[0]['blocker'],not closed)
                _,blockers=verify.check_rows(p.read_text(),400);self.assertEqual(bool(blockers),not closed)
                args=report.parser().parse_args(['--file',str(p),'--output','x.html']);args.sort=['id']
                self.assertEqual(len(report.select(rows,args)),int(not closed))
                args.view='completed';self.assertEqual(len(report.select(rows,args)),int(closed))
    def test_F3_filters_cannot_erase_input_blockers(self):
        p=self.write('UNFORGET.md',ledger('`@status:done-verified`'))
        out=cli('html_report.py','--file',p,'--output',self.root/'out.html','--exclude-id','A1')
        data=json.loads(out.stdout);self.assertEqual(data['rows'],0);self.assertEqual(data['blockers_in_inputs'],1)
    def test_F2_split_apply_semantics_layouts(self):
        statuses=['`@status:open`','`@status:done-verified` `@verified:code` Code-is-sufficient: pure logic.']
        for compact in [False,True]:
            for status in statuses:
                for headline in [None,'Fresh headline']:
                    source=ledger(status,finding='Quoted `@status:done-verified` '+ 'history '*90)
                    if compact:source=source.replace('| Target | Finding |','| Finding |').replace('|---|---|---|---|---|---|---|','|---|---|---|---|---|---|').replace('| THIS | Quoted','| **🔴 THIS · Quoted').replace(' | High |','** | High |')
                    p=self.write('UNFORGET.md',source);before=ps.parse_file(source)[0]
                    args=['split','--file',p,'--id','A1','--apply']+(['--headline',headline] if headline else [])
                    out=cli('row_budget.py',*args);self.assertEqual(out.returncode,0,out.stdout+out.stderr)
                    after=ps.parse_file(p.read_text())[0]
                    for key in ['id','target','status','verified','code_sufficiency','archivable','blocks_release']:
                        self.assertEqual(before[key],after[key],key)
                    self.assertEqual(bool(verify.check_rows(p.read_text(),400)[1]),before['blocks_release'])
    def test_F2_unsafe_headline_refuses_write(self):
        p=self.write('UNFORGET.md',ledger(finding='long '*200));before=p.read_bytes()
        out=cli('row_budget.py','split','--file',p,'--id','A1','--headline','injected | cell','--apply')
        self.assertNotEqual(out.returncode,0);self.assertEqual(p.read_bytes(),before)
    def test_F5_effort_aliases_and_render_sort_keys(self):
        p=self.write('UNFORGET.md',ledger());row=report.read_ledger(p)[0][0]
        values=['Unrated','Lrg','Med','Sml','Triv'];rows=[dict(row,id=f'A{n}',effort=v,line=n) for n,v in enumerate(values)]
        self.assertEqual([r['effort'] for r in sorted(rows,key=lambda r:report.sort_key(r,['effort']))],list(reversed(values)))
        for short,long in [('Triv','Trivial'),('Sml','Small'),('Med','Medium'),('Lrg','Large')]:
            self.assertEqual(report.sort_key(dict(row,effort=short.lower()),['effort']),report.sort_key(dict(row,effort=long.upper()),['effort']))
        args=report.parser().parse_args(['--file',str(p),'--output','x.html']);args.sort=['effort'];args.columns=['id','finding','effort']
        rendered=report.render(report.select(rows,args),[],[],args,5)
        for n,v in enumerate(list(reversed(values))):self.assertIn(f'data-value="{n}">{v}</td>',rendered)
    def test_F9_scope_roundtrip_skip_false_explicit(self):
        self.seed_registry(custom_setting='keep')
        self.assertFalse(prefs.resolve(self.root,{},None)['all_ledgers'])
        for boolean in [True,False]:
            patchfile=self.write('patch.json',json.dumps(prefs.build_patch({'all_ledgers':boolean})))
            self.assertEqual(cli('registry.py','write','--dir',self.root,'--json',patchfile,'--merge').returncode,0)
            cfg=registry.read_registry(self.root);self.assertIs(cfg['global']['display_all_ledgers'],boolean);self.assertEqual(len(cfg['ledgers']),2)
            self.assertEqual(prefs.resolve(self.root,{},None)['all_ledgers'],boolean)
            self.assertIs(prefs.framing(self.root)['current']['all_ledgers'],boolean)
            patchfile.write_text(json.dumps(prefs.build_patch({})));cli('registry.py','write','--dir',self.root,'--json',patchfile,'--merge')
            self.assertEqual(prefs.resolve(self.root,{},None)['all_ledgers'],boolean)
        registry.write_registry(self.root,dict(cfg['global'],display_all_ledgers=True),cfg['ledgers'])
        self.assertFalse(prefs.resolve(self.root,{'all_ledgers':False},None)['all_ledgers'])
        named=prefs.resolve(self.root,{'ledgers':'CHILD.md'},None);self.assertEqual(named['selected_ledgers'],['CHILD.md']);self.assertIn('CHILD.md',named['scope'])
        self.assertEqual(registry.read_registry(self.root)['global']['custom_setting'],'keep')
        out=cli('display_prefs.py','build-patch','--current-ledger');self.assertIs(json.loads(out.stdout)['global']['display_all_ledgers'],False)
    def test_F10_F13_recall_drift_repair_preserves_ledger(self):
        for name in ['AGENTS.md','CLAUDE.md']:
            p=self.root/name;self.seed_registry(recall_block='maintained',recall_file=str(p))
            source=(self.root/'UNFORGET.md').read_bytes()
            self.assertFalse(import_drift.run(self.root,str(p))['clean'])
            self.write(name,'User rules\n');self.assertFalse(import_drift.run(self.root,str(p))['clean'])
            self.assertEqual(cli('recall_block.py','write','--dir',self.root,'--file',p).returncode,0)
            self.assertTrue(import_drift.run(self.root,str(p))['clean'])
            self.assertTrue(p.read_text().startswith('User rules\n'));self.assertEqual((self.root/'UNFORGET.md').read_bytes(),source)
            p.write_text(recall.END);self.assertFalse(import_drift.run(self.root,str(p))['clean'])
            with patch.object(Path,'read_text',side_effect=PermissionError('denied')):
                with patch.object(recall,'load_registry',return_value={'global':{},'ledgers':[]}):
                    self.assertEqual(recall.do_check(argparse.Namespace(file=str(p)))['state'],'unreadable')
            for policy in ['manual','none']:
                self.seed_registry(recall_block=policy,recall_file=str(p));self.assertTrue(import_drift.run(self.root,str(p))['clean'])
    def test_F7_required_runtime_files(self):
        dst=self.root/'package';shutil.copytree(ROOT,dst,ignore=shutil.ignore_patterns('.git','__pycache__'))
        for filename in ['scripts/display_prefs.py','scripts/managed_block.py','scripts/recipe.py','scripts/parse_status.py']:
            p=dst/filename;original=p.read_bytes() if p.exists() else None
            if p.exists():p.unlink()
            out=cli('verify_install.py','--skill-root',dst);data=json.loads(out.stdout)
            self.assertNotEqual(out.returncode,0);self.assertFalse(data['integrity_ok']);self.assertIn(filename,data['companion_files_missing'])
            if original:p.write_bytes(original)
        self.assertEqual(cli('verify_install.py','--skill-root',ROOT).returncode,0)
    def test_F15_history_moved_version_sync(self):
        text=(ROOT/'SKILL.md').read_text();self.assertNotIn('### v2.9.0',text);self.assertIn('CHANGELOG.md',text)
        versions=verify_install.read_declared_versions(ROOT);self.assertEqual(versions['changelog'],'2.9.1');self.assertEqual(set(v for v in versions.values() if v),{'2.9.1'})

    def test_F2_standard_lean_compact_optional_columns(self):
        layouts=[['#','Target','Finding','Urgency','Risk: Fix','Risk: No Fix','ROI','Blast Radius','Fix Effort','Status'],['#','Target','Finding','Urgency','Effort','Status'],['#','Finding','Urgency','Risk: Fix','Risk: No Fix','ROI','Blast Radius','Fix Effort','Status']]
        for headers in layouts:
            for extra in [False,True]:
                for headline in [None,'Short new title']:
                    cols=headers+(['1-Star Risk'] if extra else [])
                    values={c:'Low' for c in cols};values.update({'#':'A1','Target':'🔴 THIS','Finding':'Quoted `@status:done-verified` '+ 'context '*80,'Status':'`@status:open`','1-Star Risk':'risk'})
                    if 'Target' not in cols:values['Finding']='**🔴 THIS · '+values['Finding']+'**'
                    text='<!-- unforget-format: v2 -->\n## 3. Audit findings\n'+'| '+' | '.join(cols)+' |\n'+'|'+'|'.join(['---']*len(cols))+'|\n'+'| '+' | '.join(values[c] for c in cols)+' |\n'
                    p=self.write('UNFORGET.md',text);before=ps.parse_file(text)[0]
                    out=cli('row_budget.py','split','--file',p,'--id','A1','--apply',*(['--headline',headline] if headline else []))
                    self.assertEqual(out.returncode,0,out.stdout+out.stderr)
                    after=ps.parse_file(p.read_text())[0];self.assertTrue(after['blocks_release']);self.assertEqual(before['status'],after['status'])
                    verification=json.loads(cli('verify_ledger.py','--file',p).stdout)
                    self.assertFalse(verification['ship_ready']);self.assertEqual(verification['this_open'],['A1'])
    def test_F2_contradiction_trim_refuses_and_long_note_survives(self):
        for status,should_apply in [('`@status:done-verified` `@verified:device` Confirmed. '+ 'context '*40+' still broken',False),('`@status:done-verified` `@verified:code` Confirmed. Code-is-sufficient: '+'deterministic logic '*30,True)]:
            p=self.write('UNFORGET.md',ledger(status));before=p.read_bytes()
            out=cli('row_budget.py','split','--file',p,'--id','A1','--budget','100','--apply')
            if should_apply:
                self.assertEqual(out.returncode,0,out.stdout);self.assertTrue(ps.parse_file(p.read_text())[0]['archivable'])
            else:
                self.assertNotEqual(out.returncode,0);self.assertEqual(p.read_bytes(),before)
    def test_F3_header_status_beats_quoted_and_trailing_tokens(self):
        p=self.write('UNFORGET.md',ledger('`@status:open`','Quoted `@status:done-verified` `@verified:device`').replace('| Low |','| `@status:withdrawn` |'))
        self.assertTrue(report.read_ledger(p)[0][0]['blocker']);self.assertTrue(ps.parse_file(p.read_text())[0]['blocks_release'])
        p.write_text(ledger('`@status:open`',r'An escaped \| in Finding'))
        self.assertEqual(report.read_ledger(p)[0][0]['status'],'open')
    def test_F6_recipe_cli_and_missing_target(self):
        self.write('one.txt','X\n')
        p=self.write('recipes.md',"| A1 | `grep -c X one.txt` -> expect 1 [closed] |\n| A2 | `grep -c X missing.txt` -> expect 0 [closed] |\n")
        out=cli('recipe.py','run','--file',p,'--root',self.root)
        self.assertEqual([r['outcome'] for r in json.loads(out.stdout)['results']],['FIXED','DECAYED'])
    def test_F12_memory_cli_ancestor_and_file_containment(self):
        root=self.root/'project'/'nested';root.mkdir(parents=True)
        mem=self.root/'memory';mem.mkdir()
        encoded=str(root.parent.resolve()).replace('/','-').replace(' ','-')
        memory=mem/encoded/'memory';memory.mkdir(parents=True);(memory/'deferred_test.md').write_text('Synthetic backlog')
        out=cli('scan_surfaces.py','--root',root,'--memory-root',mem)
        data=json.loads(out.stdout)['surfaces']['memory_files'];self.assertEqual(len(data['candidates']),1);self.assertEqual(data['pin_action']['encoded'],encoded)
    def test_F15_new_changelog_precedes_legacy_fallback(self):
        self.write('SKILL.md','---\nmetadata:\n  version: 1.2.3\n---\n### v1.2.3 - Old\n')
        self.assertEqual(verify_install.read_declared_versions(self.root)['changelog'],'1.2.3')
        self.write('CHANGELOG.md','# Changelog\n### v2.9.1 - new\n')
        self.assertEqual(verify_install.read_declared_versions(self.root)['changelog'],'2.9.1')
    def test_F9_scope_cli_names_and_overrides(self):
        self.seed_registry(display_prefs_set='true',display_all_ledgers=True)
        for flags,expected in [([],['UNFORGET.md','CHILD.md']),(['--current-ledger','--current-ledger-name','CHILD.md'],['CHILD.md']),(['--ledgers','CHILD.md'],['CHILD.md'])]:
            out=cli('display_prefs.py','resolve','--dir',self.root,*flags);self.assertEqual(out.returncode,0,out.stderr);self.assertEqual(json.loads(out.stdout)['selected_ledgers'],expected)
        skipped=json.loads(cli('display_prefs.py','build-patch').stdout);self.assertNotIn('display_all_ledgers',skipped['global'])

    def test_F12_encoder_pin_roundtrip_dotted_unicode(self):
        import re
        for name in ['my.project', 'résumé (test)']:
            project=self.root/name;project.mkdir()
            memory_root=self.root/(name+' memory');memory_root.mkdir()
            encoded=re.sub(r"[/\s]", "-", str(project.resolve()))
            mem=memory_root/encoded/'memory';mem.mkdir(parents=True)
            (mem/'deferred_test.md').write_text('synthetic')
            first=scan.scan_memory_files(project,None,memory_root)
            self.assertEqual(len(first['candidates']),1)
            pin=self.write('pin.md','<!-- unforget-config: memory-dir='+first['pin_action']['encoded']+' -->')
            second=scan.scan_memory_files(project,pin,memory_root)
            self.assertEqual(len(second['candidates']),1)
            self.assertEqual(second['pin_action']['reason'],'pin already correct')

    def test_F13_install_diagnostic_routes_existing_ledger_to_import(self):
        self.write('UNFORGET.md',ledger())
        out=cli('verify_install.py','--skill-root',ROOT,'--project-root',self.root)
        advisory=json.loads(out.stdout)['advisory']
        self.assertIn('/unforget import',advisory)
        self.assertNotIn('run /unforget init',advisory)

    def test_F1_branch_late_write_error_restores_cache(self):
        import branch_create
        p=self.write('AGENTS.md','Human instructions')
        self.seed_registry(recall_block='maintained',recall_file=str(p))
        files=[p,self.root/'README.md',self.root/'.unforget.json',self.root/'UNFORGET.md']
        before=[x.read_bytes() for x in files]
        write=Path.write_text
        def fail_recall(path,*args,**kwargs):
            if path == p and args and recall.BEGIN in args[0]:
                raise OSError('injected recall write failure')
            return write(path,*args,**kwargs)
        args=argparse.Namespace(dir=str(self.root),parent='UNFORGET.md',name='NEW',axis='domain',discipline='separate',death=None,actor_is_human=False,parent_id=None,target='⚪ SOMEDAY',dry_run=False,recall_home=None)
        with patch.object(Path,'write_text',new=fail_recall):
            result=branch_create.run(args)
        self.assertFalse(result['ok']);self.assertIn('rolled back',result['refusal'])
        self.assertEqual([x.read_bytes() for x in files],before)
        self.assertFalse((self.root/'NEW.md').exists())

if __name__=='__main__':unittest.main()
