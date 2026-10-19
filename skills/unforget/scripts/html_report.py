#!/usr/bin/env python3
"""Read-only HTML ledger report. Python 3.9+, standard library only.

See reference/html-report.md. Explicit --file inputs prevent unrelated-ledger scans.
Optional annotations add editorial UX/next-action notes without changing source data.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import importlib.util
from urllib.parse import quote
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_status

CLOSED = {'done-verified', 'withdrawn', 'legacy-complete'}
STATES = {'open', 'in-progress', 'blocked', 'done-unverified', 'done-verified', 'withdrawn'}
URGENCY = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'unrated': 4}
IMPACT = {'severe': 0, 'high': 1, 'moderate': 2, 'low': 3, 'indirect': 4, 'unrated': 5}
TARGET = {'THIS': 0, 'NEXT': 1, 'LATER': 2, 'SOMEDAY': 3, 'Unassigned': 4}
DEFAULT_COLUMNS = ['id', 'finding', 'target', 'status', 'ux', 'owner', 'next']
COLUMNS = ['rank', 'id', 'ledger', 'blocker', 'target', 'finding', 'urgency', 'ux', 'status', 'effort', 'roi', 'owner', 'next', 'verification', 'last_checked', 'reconciliation', 'readiness']
OWNER_KINDS = {'user', 'assistant', 'person', 'team', 'unassigned'}
OWNER_SOURCES = {'recorded', 'explicit', 'suggested'}
SORTS = ['blocker', 'urgency', 'ux', 'target', 'effort', 'roi', 'id', 'ledger', 'status']
EFFORT = {'trivial': 0, 'small': 1, 'medium': 2, 'large': 3, 'unrated': 4}
EFFORT_WORDS = {'triv': 'trivial', 'trivial': 'trivial', 'sml': 'small', 'small': 'small',
                'med': 'medium', 'medium': 'medium', 'lrg': 'large', 'large': 'large'}
ROI = {'excellent': 0, 'good': 1, 'fair': 2, 'marginal': 3, 'poor': 4, 'unrated': 5}
ROI_WORDS = {'excel': 'excellent', 'excellent': 'excellent', 'good': 'good', 'fair': 'fair',
             'marginal': 'marginal', 'poor': 'poor'}
DELIMITER = re.compile(r'^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$')
ID = re.compile(r'(?:[A-Za-z]+-?)?\d+[a-z]?$', re.I)
E = html.escape


def cells(line):
    return [c.strip() for c in re.split(r'(?<!\\)\|', line.strip().strip('|'))]


def plain(text):
    return re.sub(r'[*`~]', '', text).strip()


def level(text, choices, default):
    match = re.search(r'\b(' + '|'.join(choices) + r')\b', text, re.I)
    return match[1].lower() if match else default


def word_level(text, words):
    """First recognized word wins ("Small-Med" is small); no match is 'unrated'."""
    # Escape each word (a project word like "M+" or "(S)" is text, not a pattern) and
    # use lookarounds, since \b cannot sit after a word that ends in punctuation.
    alternation = '|'.join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    match = re.search(r'(?<!\w)(' + alternation + r')(?!\w)', text, re.I)
    return words[match[1].lower()] if match else 'unrated'


# Per-project vocabulary, keyed by ledger path. Kept off the row so --query and
# the rendered row data never see it.
VOCAB = {}
VOCAB_KEYS = dict(effort_words=('effort', EFFORT), roi_words=('roi', ROI))


def parse_word_map(value, levels):
    """'XS=trivial, S=small' -> ({'xs': 'trivial', 's': 'small'}, [problems])."""
    mapping, problems = {}, []
    for part in (value or '').split(','):
        part = part.strip()
        if not part: continue
        word, sep, lvl = part.partition('=')
        word, lvl = word.strip().lower(), lvl.strip().lower()
        if not sep or not word or lvl not in levels or lvl == 'unrated':
            problems.append(part)
        else:
            mapping[word] = lvl
    return mapping, problems


def load_vocab(ledger_dir):
    """Read report_* keys from the project's registry (README.md block).

    report_effort_words / report_roi_words: 'WORD=level, ...' added to the built-in
    words (a project word wins over a built-in one). report_effort_column /
    report_roi_column: extra header names, comma-separated, tried after the defaults.
    Returns (vocab, notes). A missing registry is not an error: built-ins apply.
    """
    try:
        import registry
        reg = registry.read_registry(Path(ledger_dir))
    except Exception as exc:
        return {}, [f'{ledger_dir}: registry unreadable ({exc}); built-in report words only.']
    if reg.get('error') and 'no README.md' not in reg['error']:
        # read_registry reports a malformed block by returning an error, not raising.
        return {}, [f"{ledger_dir}: registry unreadable ({reg['error']}); built-in report words only."]
    cfg = reg.get('global', {}) or {}
    vocab, notes = {}, []
    for key, (field, levels) in VOCAB_KEYS.items():
        mapping, problems = parse_word_map(cfg.get('report_' + key), levels)
        if mapping: vocab[field + '_words'] = mapping
        if problems:
            notes.append(f"report_{key}: ignored {', '.join(problems)} (use WORD=level; levels: {', '.join(l for l in levels if l != 'unrated')}).")
    for field in ('effort', 'roi'):
        cols = [c.strip().lower() for c in (cfg.get(f'report_{field}_column') or '').split(',') if c.strip()]
        if cols: vocab[field + '_columns'] = cols
    if vocab:
        counts = ', '.join(f"{k.replace('_', ' ')}: {len(v)}" for k, v in vocab.items())
        notes.append(f'Project vocabulary from {Path(ledger_dir) / "README.md"} ({counts}).')
    return vocab, notes


INTERNAL = {'vocab_key'}


def public(row):
    """The row without internal keys: never searched, never rendered."""
    return {k: v for k, v in row.items() if k not in INTERNAL}


def words_for(row, field, builtin):
    # vocab_key, not source: callers may rewrite source (e.g. to a relative path).
    custom = VOCAB.get(row.get('vocab_key') or row.get('source', ''), {}).get(field + '_words')
    return {**builtin, **custom} if custom else builtin


def effort_of(row):
    return word_level(row['effort'], words_for(row, 'effort', EFFORT_WORDS))


def roi_of(row):
    return word_level(row.get('roi', ''), words_for(row, 'roi', ROI_WORDS))


def read_ledger(path):
    """Read declared Status tables, preserving unresolved legacy states visibly."""
    path = Path(path).resolve()
    text = path.read_text(encoding='utf-8')
    lines, headers, section, rows, warnings, seen = text.splitlines(), [], '', [], [], set()
    marker = re.search(r'<!--\s*unforget-format:\s*v(\d+)\s*-->', text)
    if not marker or int(marker[1]) not in (1, 2):
        warnings.append(f'{path.name}: missing or unsupported format marker; read-only best-effort snapshot.')
    details = parse_status.detail_blocks(text)
    vocab, vocab_notes = load_vocab(path.parent)
    VOCAB[str(path)] = vocab
    warnings.extend(vocab_notes)

    def column(data, defaults, field):
        for name in list(defaults) + vocab.get(field + '_columns', []):
            if name in data: return data[name]
        return ''
    for n, line in enumerate(lines, 1):
        if line.startswith('#'):
            section = line.lstrip('# ').strip()
        if not line.startswith('|'):
            continue
        values = cells(line)
        if n < len(lines) and DELIMITER.match(lines[n]):
            headers = [plain(v).lower() for v in values]
            continue
        if 'status' not in headers or headers[0] not in ('#', 'id') or not ID.fullmatch(plain(values[0])):
            continue
        if len(values) != len(headers):
            raise ValueError(f'{path}:{n}: {len(values)} cells, expected {len(headers)}. Resolve the malformed row before exporting.')
        data = dict(zip(headers, values))
        ident = plain(values[0])
        if ident in seen:
            raise ValueError(f'{path}:{n}: duplicate ID {ident}; reconcile before exporting.')
        seen.add(ident)
        status_text = data['status']
        evaluated = parse_status.parse_row(line, headers, details.get(ident, ''), fields=data)
        status = evaluated['effective_status']
        if evaluated['issues']:
            warnings.extend(f'{path.name}:{n}: {ident}: {issue}' for issue in evaluated['issues'])
        elif status == 'unknown':
            warnings.append(f'{path.name}:{n}: {ident} has ambiguous status; retained as unknown.')
        finding = data.get('finding', data.get('check', ''))
        target_text = data.get('target', '')
        if not target_text:
            compact = re.match(r'^\**\s*[🔴🔵🟡⚪🚢🌫️ ]*\b(THIS|NEXT|LATER|SOMEDAY)\b\s*·', finding)
            target_text = compact[1] if compact else ''
        target = level(target_text, ['THIS','NEXT','LATER','SOMEDAY'], 'Unassigned')
        target = target.upper() if target != 'Unassigned' else target
        urgency = level(data.get('urgency', data.get('urg', '')), ['critical','crit','high','medium','med','low'], 'unrated')
        if urgency == 'crit': urgency = 'critical'
        if urgency == 'med': urgency = 'medium'
        rows.append(dict(id=ident, ledger=path.name, source=str(path), line=n, section=section,
                         finding=finding, status=status, target=target, urgency=urgency,
                         blocker=evaluated['blocks_release'], completed=evaluated['completed'],
                         integrity_issues=evaluated['issues'],
                         ux='unrated', ux_basis='', owner='', next='', effort=column(data, ('fix effort', 'effort', 'est'), 'effort') or 'Unrated',
                         roi=column(data, ('roi',), 'roi'), vocab_key=str(path), original=data, notes=[], detail=details.get(ident,''),
                         owner_kind='unassigned', owner_source='', owner_basis='',
                         verification=data.get('verification needed',''), verification_owed=status=='done-unverified',
                         last_checked=data.get('last checked',''), check_basis='', dependencies=data.get('dependencies',''),
                         reconciliation='', readiness='unknown', readiness_basis=''))
        row=rows[-1]
        recorded_owner=data.get('who acts next',data.get('owner',data.get('assignee','')))
        if recorded_owner and plain(recorded_owner).lower() not in ('—','-','unassigned','not recorded'):
            row.update(owner=plain(recorded_owner),owner_kind='person',owner_source='recorded',owner_basis='Assignment in the source table.')

    return rows, dict(path=str(path), ledger=path.name, sha256=hashlib.sha256(text.encode()).hexdigest(), rows=len(rows)), warnings


def annotate(rows, annotations):
    """Annotations never override ledger status, target, or release-gate membership."""
    if not isinstance(annotations, dict): raise ValueError('Annotations must be an object keyed by ledger::ID.')
    keyed = {r['ledger']+'::'+r['id']: r for r in rows}
    allowed = {'ux','ux_basis','owner','owner_kind','owner_source','owner_basis','next','title','notes',
               'verification','verification_owed','last_checked','check_basis','dependencies',
               'reconciliation','readiness','readiness_basis'}
    for key, note in annotations.items():
        if key not in keyed: raise ValueError(f'Annotation does not match an input row: {key}')
        if not isinstance(note, dict) or set(note)-allowed:
            raise ValueError(f'{key}: annotations can only add presentation fields, not change source status or target.')
        for field, value in note.items():
            valid = (isinstance(value, list) and all(isinstance(v,str) for v in value)) if field=='notes' else (type(value) is bool if field=='verification_owed' else isinstance(value,str))
            if not valid: raise ValueError(f'{key}: invalid annotation type for {field}.')
        if 'ux' in note and (note['ux'] not in IMPACT or (note['ux']!='unrated' and not note.get('ux_basis'))):
            raise ValueError(f'{key}: UX estimate needs a valid level and ux_basis.')
        for field, choices in [('owner_kind',OWNER_KINDS),('owner_source',OWNER_SOURCES),('readiness',{'ready','waiting','unknown'})]:
            if field in note and note[field] not in choices: raise ValueError(f'{key}: invalid {field}.')
        if note.get('last_checked'):
            try: dt.date.fromisoformat(note['last_checked'])
            except ValueError: raise ValueError(f'{key}: last_checked must be an ISO date (YYYY-MM-DD).')
            if not note.get('check_basis'): raise ValueError(f'{key}: last_checked needs check_basis describing the actual check.')
        if note.get('readiness')=='ready' and not note.get('readiness_basis'):
            raise ValueError(f'{key}: ready needs readiness_basis; open alone does not mean ready.')
        row=keyed[key]
        assignment_fields={'owner','owner_kind','owner_source','owner_basis'}
        if assignment_fields & note.keys():
            # Never inherit recorded provenance when an annotation changes an assignment.
            source=note.get('owner_source','suggested')
            if source in {'recorded','explicit'} and not note.get('owner_basis'):
                raise ValueError(f'{key}: confirmed assignment needs owner_basis citing the source or instruction.')
            row.update(owner='',owner_kind='unassigned',owner_source=source,
                       owner_basis=note.get('owner_basis','Report suggestion; assignment has not been confirmed.'))
            if note.get('owner') and 'owner_kind' not in note: row['owner_kind']='person'
        row.update(note)
        if row['owner_kind'] in {'person','team'} and not row['owner'].strip():
            raise ValueError(f'{key}: named person/team needs an owner.')
        # A report cannot dismiss a check owed by the canonical status.
        if row['status']=='done-unverified': row['verification_owed']=True


def project_settings(directory):
    """Read only the registry beside each input; no global identity guesses or cache writes."""
    spec=importlib.util.spec_from_file_location('unforget_report_registry',Path(__file__).with_name('registry.py'))
    registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry)
    config=registry.read_registry(Path(directory)).get('global', {}) or {}
    mode=config.get('report_user_label') or 'you'
    if mode not in {'you','name'}: raise ValueError('report_user_label must be you or name.')
    return {'user_name':config.get('report_user_name') or '', 'user_label':mode,
            'assistant_label':config.get('report_assistant_label') or 'Coding assistant'}


def prepare_presentation(rows, settings=None):
    """Resolve labels and conservative suggestions without changing source obligations."""
    settings=settings or {}
    for r in rows:
        cfg=settings.get(str(Path(r['source']).parent),{})
        name=cfg.get('user_name','')
        user=name if cfg.get('user_label')=='name' and name else 'You'
        assistant=cfg.get('assistant_label') or 'Coding assistant'
        raw=r['owner'].strip()
        if raw.lower() in {'you','user','project user'} or (name and raw.casefold()==name.casefold()): r['owner_kind']='user'
        elif raw.lower() in {'assistant','coding assistant'}: r['owner_kind']='assistant'
        text=plain(r['finding']+' '+r['original']['status'])
        if r['owner_kind']=='unassigned' and not r['owner_source']:
            names=['USER','HUMAN']+([re.escape(name)] if name else [])
            if re.search(r'\b(?:'+'|'.join(names)+r')[- ](?:ONLY|ACTION)\b',text,re.I):
                r.update(owner_kind='user',owner_source='recorded',owner_basis='Source explicitly marks this as a user-only action.')
            elif re.search(r'\b(?:needs?|requires?|awaiting|blocked on)\s+(?:a\s+)?(?:physical device|device test|account access|user decision|your confirmation)\b',text,re.I):
                r.update(owner_kind='user',owner_source='suggested',owner_basis='The source describes a device, account, or decision requirement.')
            elif re.match(r'^(?:fix|rewrite|update|remove|add)\b',text,re.I) and re.search(r'\b(?:copy|code|test|script|documentation|HTML|CSS)\b',text,re.I) and r['status'] in {'open','in-progress'}:
                r.update(owner_kind='assistant',owner_source='suggested',owner_basis='The finding describes an implementation task; assignment has not been confirmed.')
        if r['owner_kind']=='user': r['owner']=user
        elif r['owner_kind']=='assistant': r['owner']=assistant
        elif r['owner_kind']=='unassigned': r['owner']='Unassigned'
        if r['verification'] and not r['completed']: r['verification_owed']=True
        if r['status']=='done-unverified': r['verification_owed']=True
        if r['dependencies'] or r['status']=='blocked' or r['verification_owed']: r['readiness']='waiting'
        if r['reconciliation'] or r['completed'] or r['status']=='unknown' or r['integrity_issues']: r['readiness']='unknown'


def sort_key(row, fields):
    keys = dict(blocker=not row['blocker'], urgency=URGENCY[row['urgency']], ux=IMPACT[row['ux']],
                target=TARGET[row['target']],
                effort=EFFORT[effort_of(row)], roi=ROI[roi_of(row)],
                id=row['id'], ledger=row['ledger'], status=row['status'])
    return tuple(keys[k] for k in fields)+(row['ledger'],row['line'])


def select(rows, args):
    """Filter, sort, then cap. Records what it did in args.select_info for the report notes."""
    result, unclassified = [], dict(effort=0, roi=0)
    for r in rows:
        key=r['ledger']+'::'+r['id']
        if args.id and key not in args.id and r['id'] not in args.id: continue
        if args.exclude_id and (key in args.exclude_id or r['id'] in args.exclude_id): continue
        if args.status:
            if r['status'] not in args.status: continue
        elif args.view == 'unfinished' and r['completed']: continue
        elif args.view == 'completed' and not r['completed']: continue
        if args.blockers_only and not r['blocker']: continue
        if args.target and r['target'] not in args.target: continue
        if args.urgency and r['urgency'] not in args.urgency: continue
        if args.ledger and r['ledger'] not in args.ledger: continue
        if args.section and not any(s.casefold() in r['section'].casefold() for s in args.section): continue
        if args.query and args.query.casefold() not in json.dumps(public(r),ensure_ascii=False).casefold(): continue
        # Effort and ROI filters run last so the unclassified counts cover only rows
        # every other filter let through: those are the rows the filter may be hiding.
        for field, wanted, of in (('effort', args.effort, effort_of), ('roi', args.roi, roi_of)):
            if wanted:
                level_ = of(r)
                if level_ == 'unrated' and 'unrated' not in wanted: unclassified[field] += 1
                if level_ not in wanted: break
        else:
            result.append(r.copy())
    fields = list(args.sort)
    if args.limit and 'effort' not in fields: fields.append('effort')  # ties at the cut: faster fix first
    result.sort(key=lambda r:sort_key(r,fields))
    matched, extra = len(result), 0
    if args.limit and matched > args.limit:
        head = result[:args.limit]
        beyond = [r for r in result[args.limit:] if r['blocker']]  # a cap never hides a release blocker
        extra = len(beyond)
        result = head + beyond
    for n,r in enumerate(result,1):r['rank']=n
    args.select_info = dict(matched=matched, shown=len(result), extra_blockers=extra, unclassified=unclassified)
    return result


def selection_notes(args):
    """Report notes describing what select() cut or could not classify. Call after select()."""
    info, notes = args.select_info, []
    if args.limit and info['matched'] > args.limit:
        tail = f"; {info['extra_blockers']} more release blocker(s) are shown beyond the limit." if info['extra_blockers'] else '.'
        notes.append(f"Showing {info['shown'] - info['extra_blockers']} of {info['matched']} matching rows (limit {args.limit}, ties broken by lowest fix effort){tail}")
    for field, flag in (('effort', args.effort), ('roi', args.roi)):
        if flag and info['unclassified'][field]:
            notes.append(f"{info['unclassified'][field]} row(s) that passed every other filter have no recognizable {field} and are excluded by --{field}; rerun with --{field} unrated to see them, or map their words with report_{field}_words in the ledger README's registry block.")
    return notes


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--file',action='append',required=True,type=Path,help='Canonical input ledger; repeat for multiple ledgers.')
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--title',default='Unfinished ledger')
    p.add_argument('--view',choices=['unfinished','all','completed'],default='unfinished')
    p.add_argument('--blockers-only',action='store_true')
    p.add_argument('--status',action='append',choices=sorted(STATES|{'unknown','legacy-complete'}))
    p.add_argument('--target',action='append',choices=list(TARGET))
    p.add_argument('--urgency',action='append',choices=list(URGENCY))
    p.add_argument('--ledger',action='append')
    p.add_argument('--section',action='append')
    p.add_argument('--query')
    p.add_argument('--effort',action='append',choices=list(EFFORT),help='Fix effort level (trivial, small, medium, large, unrated); repeat for several.')
    p.add_argument('--roi',action='append',choices=list(ROI),help='ROI level (excellent, good, fair, marginal, poor, unrated); repeat for several.')
    p.add_argument('--limit',type=int,help='Show at most N rows after sorting; release blockers beyond the cut are still shown and counted.')
    p.add_argument('--id',action='append',help='Include an ID or filename.md::ID; repeat for a reviewed custom subset.')
    p.add_argument('--exclude-id',action='append',help='Exclude a reviewed duplicate/pointer ID or filename.md::ID.')
    p.add_argument('--sort',default='blocker,urgency,ux',help='Ordered comma-separated keys: '+','.join(SORTS))
    p.add_argument('--columns',default=','.join(DEFAULT_COLUMNS),help='Visible columns: '+','.join(COLUMNS))
    p.add_argument('--annotations',type=Path)
    p.add_argument('--user-name',help='Explicit project user name; never inferred from paths or login names.')
    p.add_argument('--user-label',choices=['you','name'],help='Override the registry display preference for this report.')
    p.add_argument('--assistant-label',help='Override Coding assistant for this report.')
    p.add_argument('--timezone',help='IANA timezone for generation time, e.g. America/Denver.')
    p.add_argument('--scope-note',default='Only the explicitly listed source ledgers were read.')
    p.add_argument('--note',action='append',default=[])
    p.add_argument('--force',action='store_true',help='Replace an existing HTML output when explicitly requested.')
    return p


def render(rows, sources, warnings, args, total_blockers):
    template=(Path(__file__).resolve().parent.parent/'assets/html-report.html').read_text(encoding='utf-8')
    labels={'id':'ID','finding':'Item','ux':'User impact','blocker':'Release gate','effort':'Fix effort',
            'roi':'Value (ROI)', 'target':'Release target','owner':'Who acts next','next':'Next action','last_checked':'Last checked',
            'verification':'Verification needed','reconciliation':'Needs reconciliation'}
    statuses={'done-unverified':'Awaiting verification','done-verified':'Verified complete','in-progress':'In progress',
              'legacy-complete':'Completed (legacy claim)','open':'Open','blocked':'Blocked','withdrawn':'Withdrawn','unknown':'Needs review'}
    heads=''.join(f'<th scope="col"><button data-col="{n}">{E(labels.get(k,k.title()))} ↕</button></th>' for n,k in enumerate(args.columns))
    body=[]
    source_order = {(r['ledger'], r['line']): n for n, r in enumerate(sorted(rows, key=lambda r: (r['ledger'], r['line'])))}
    for r in rows:
        vals=[]
        for col in args.columns:
            value=str(r.get(col,''))
            if col=='finding':
                title=r.get('title') or plain(r['finding'])
                short=title if len(title)<=180 else title[:177].rsplit(' ',1)[0]+'…'
                source_path=Path(r.get('source_link') or r['source'])
                uri=source_path.as_uri() if source_path.is_absolute() else quote(source_path.as_posix(),safe='/')
                details=f'<p><b>Source:</b> <a href="{E(uri,quote=True)}">{E(r["ledger"])}</a> · line {r["line"]}</p>'
                for label,key,default in [('Who acts next','owner','Unassigned'),('Assignment evidence','owner_basis','Not recorded'),
                    ('Next action','next','Not recorded'),('Verification needed','verification','Procedure not recorded' if r['verification_owed'] else 'Not recorded'),
                    ('Last checked','last_checked','Not recorded'),('Check evidence','check_basis','Not recorded'),
                    ('Dependencies','dependencies','Not recorded'),('Readiness evidence','readiness_basis','Not recorded')]:
                    details+=f'<p><b>{label}:</b> {E(r.get(key) or default)}</p>'
                if r['reconciliation']: details+='<p class="notice"><b>Needs reconciliation:</b> '+E(r['reconciliation'])+'</p>'
                if r['ux_basis']:details+='<p><b>User-impact estimate:</b> '+E(r['ux_basis'])+'</p>'
                details+=''.join('<p class="notice">'+E(n)+'</p>' for n in r['integrity_issues'] + r['notes'])
                details+='<dl>'+''.join(f'<dt>{E(k.title())}</dt><dd>{E(v)}</dd>' for k,v in r['original'].items())+'</dl>'
                if r['detail']: details+='<details><summary>Evidence and history from the ledger</summary><pre>'+E(r['detail'])+'</pre></details>'
                badges=('<span class="badge reconciliation">Needs reconciliation</span>' if r['reconciliation'] else '')
                if r['blocker']: badges+='<span class="badge blocker">Release blocker</span>'
                value=f'<strong>{E(short)}</strong>{badges}<details><summary>Evidence, verification &amp; ratings</summary>{details}</details>'
            elif col=='blocker':value='<span class="badge">'+('Blocks release' if r['blocker'] else 'Not gated')+'</span>'
            elif col=='ux':value=E(r['ux'].title())+(' <small>Estimated · basis in details</small>' if r['ux']!='unrated' else '')
            elif col=='owner':
                value=E(r['owner'] or 'Unassigned')
                if r['owner_source']:
                    text={'suggested':'Suggested','recorded':'Recorded assignment','explicit':'Explicitly assigned'}[r['owner_source']]
                    value+=f'<small class="assignment {E(r["owner_source"])}">{text}</small>'
            elif col=='status':value=E(statuses[r['status']])
            else:value=E(value or 'Not recorded')
            sortvalue=sort_key(r,[col])[0] if col in SORTS else r.get(col,'')
            if isinstance(sortvalue,bool):sortvalue=int(sortvalue)
            vals.append(f'<td data-label="{E(labels.get(col,col.title()),quote=True)}" data-value="{E(str(sortvalue),quote=True)}">{value}</td>')
        search=' '.join(' '.join(str(v) for v in public(r).values()).casefold().split())
        # Each quick filter is independent of presentation wording and never changes the source gate.
        flags={'mine':r['owner_kind']=='user','ready':r['readiness']=='ready',
               'verification':r['verification_owed'],'reconciliation':bool(r['reconciliation'])}
        attrs=' '.join(f'data-{k}="{str(v).lower()}"' for k,v in flags.items())
        body.append(f'<tr data-source-order="{source_order[(r["ledger"], r["line"])]}" data-rank="{r["rank"]}" data-blocker="{str(r["blocker"]).lower()}" data-status="{E(r["status"])}" data-ledger="{E(r["ledger"])}" data-search="{E(search,quote=True)}" {attrs}>'+''.join(vals)+'</tr>')
    criteria={k:getattr(args,k) for k in ['view','id','exclude_id','status','target','urgency','ledger','section','query','effort','roi','limit','blockers_only','sort','columns'] if getattr(args,k)}
    options=lambda key: '<option value="">All</option>'+''.join(f'<option value="{E(v,quote=True)}">{E(statuses.get(v,v) if key=="status" else v)}</option>' for v in sorted({str(r[key]) for r in rows}))
    now=dt.datetime.now().astimezone()
    if getattr(args,'timezone',None):
        from zoneinfo import ZoneInfo
        now=now.astimezone(ZoneInfo(args.timezone))
    data={'TITLE':E(args.title),'DATE':E(now.isoformat(timespec='seconds')),
          'HAS_BLOCKERS':str(total_blockers>0).lower(),'COUNT':str(len(rows)),'BLOCKERS':str(sum(r['blocker'] for r in rows)),'TOTAL_BLOCKERS':str(total_blockers),
          'UNFINISHED':str(sum(not r['completed'] for r in rows)),
          'RECONCILE':str(sum(bool(r['reconciliation']) for r in rows)),
          'OWED':str(sum(r['verification_owed'] for r in rows)), 'HEADERS':heads,'ROWS':''.join(body),
          'SCOPE':E(args.scope_note),'CRITERIA':E(json.dumps(criteria,ensure_ascii=False)),
          'NOTES':''.join('<li>'+E(x)+'</li>' for x in args.note+warnings),
          'SELECTION':''.join('<p class="notice"><b>'+E(x)+'</b></p>' for x in (selection_notes(args) if getattr(args,'select_info',None) else [])),
          'SOURCES':''.join(f'<li>{E(s["path"])} · {s["rows"]} source rows · SHA-256 <code>{s["sha256"]}</code></li>' for s in sources),
          'STATUS_OPTIONS':options('status'),'LEDGER_OPTIONS':options('ledger')}
    return re.sub(r'@@([A-Z_]+)@@',lambda m:data[m[1]],template)


def main():
    p=parser();args=p.parse_args()
    try:
        args.sort=args.sort.split(',');args.columns=args.columns.split(',')
        if not args.sort or set(args.sort)-set(SORTS):raise ValueError('Unknown sort key.')
        if not args.columns or set(args.columns)-set(COLUMNS) or len(set(args.columns))!=len(args.columns):raise ValueError('Unknown or duplicate column.')
        if 'finding' not in args.columns or 'id' not in args.columns:raise ValueError('Keep id and finding columns so provenance remains reachable.')
        if args.limit is not None and args.limit < 1:raise ValueError('--limit must be at least 1.')
        paths=[p.resolve() for p in args.file]
        if len(set(paths))!=len(paths) or len({p.name for p in paths})!=len(paths):raise ValueError('Input ledger paths and names must be distinct.')
        output=args.output.resolve()
        if output.suffix.lower() not in ('.html','.htm'):raise ValueError('Output must be an HTML file.')
        if output in paths or output==getattr(args.annotations,'resolve',lambda:None)():raise ValueError('Output cannot replace an input.')
        if output.exists() and not args.force:raise ValueError('Output exists; use a new filename or --force for an authorized replacement.')
        rows,sources,warnings=[],[],[]
        for path in paths:
            r,s,w=read_ledger(path);rows+=r;sources.append(s);warnings+=w
        settings={}
        for path in paths:
            cfg=project_settings(path.parent)
            for field in ('user_name','user_label','assistant_label'):
                if getattr(args,field,None) is not None: cfg[field]=getattr(args,field)
            settings[str(path.parent)]=cfg
        if args.annotations:annotate(rows,json.loads(args.annotations.read_text(encoding='utf-8')))
        prepare_presentation(rows,settings)
        selected=select(rows,args)
        report=render(selected,sources,warnings,args,sum(r['blocker'] for r in rows))
        warnings=warnings+selection_notes(args)   # still reported to the caller on stdout
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(report,encoding='utf-8')
        print(json.dumps(dict(output=str(output),rows=len(selected),matched=args.select_info['matched'],unclassified=args.select_info['unclassified'],blockers_in_report=sum(r['blocker'] for r in selected),blockers_in_inputs=sum(r['blocker'] for r in rows),warnings=warnings)))
    except (ValueError,OSError,TypeError,KeyError) as e:p.error(str(e))

if __name__=='__main__':main()
