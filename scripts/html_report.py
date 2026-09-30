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
from pathlib import Path

CLOSED = {'done-verified', 'withdrawn', 'legacy-complete'}
STATES = {'open', 'in-progress', 'blocked', 'done-unverified', 'done-verified', 'withdrawn'}
URGENCY = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'unrated': 4}
IMPACT = {'severe': 0, 'high': 1, 'moderate': 2, 'low': 3, 'indirect': 4, 'unrated': 5}
TARGET = {'THIS': 0, 'NEXT': 1, 'LATER': 2, 'SOMEDAY': 3, 'Unassigned': 4}
COLUMNS = ['rank', 'id', 'ledger', 'blocker', 'target', 'finding', 'urgency', 'ux', 'status', 'effort', 'owner']
SORTS = ['blocker', 'urgency', 'ux', 'target', 'effort', 'id', 'ledger', 'status']
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


def read_ledger(path):
    """Read declared Status tables, preserving unresolved legacy states visibly."""
    path = Path(path).resolve()
    text = path.read_text(encoding='utf-8')
    lines, headers, section, rows, warnings, seen = text.splitlines(), [], '', [], [], set()
    marker = re.search(r'<!--\s*unforget-format:\s*v(\d+)\s*-->', text)
    if not marker or int(marker[1]) not in (1, 2):
        warnings.append(f'{path.name}: missing or unsupported format marker; read-only best-effort snapshot.')
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
        tokens = re.findall(r'@status:\s*([a-z-]+)', status_text)
        if len(tokens) > 1:
            raise ValueError(f'{path}:{n}: multiple status tokens in {ident}.')
        status = tokens[0] if tokens else 'unknown'
        if tokens and status not in STATES:
            status = 'unknown'
            warnings.append(f'{path.name}:{n}: {ident} has an invalid status token; retained as unknown.')
        if not tokens:
            # Owed/partial evidence takes precedence over a legacy completion word.
            if re.search(r'owed|unverified|partial|mostly.fixed|not run|skipped|re.open', status_text, re.I):
                status = 'done-unverified' if re.search(r'fixed|passed|done', status_text, re.I) else 'unknown'
            elif re.search(r'\b(fixed|closed|done|passed|withdrawn)\b', status_text, re.I):
                status = 'legacy-complete'
            elif re.search(r'\bin[ -]progress\b', status_text, re.I):
                status = 'in-progress'
            elif re.search(r'\bblocked\b', status_text, re.I):
                status = 'blocked'
            elif re.search(r'\b(open|deferred)\b', status_text, re.I):
                status = 'open'
            else:
                warnings.append(f'{path.name}:{n}: {ident} has ambiguous legacy status; retained as unknown.')
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
                         blocker=target == 'THIS' and status not in CLOSED,
                         ux='unrated', ux_basis='', owner='', next='', effort=data.get('fix effort', data.get('effort', data.get('est', 'Unrated'))),
                         original=data, notes=[]))
    return rows, dict(path=str(path), ledger=path.name, sha256=hashlib.sha256(text.encode()).hexdigest(), rows=len(rows)), warnings


def annotate(rows, annotations):
    """Only presentation fields are editable; status and gate stay source-derived."""
    keyed = {r['ledger']+'::'+r['id']: r for r in rows}
    for key, note in annotations.items():
        if key not in keyed: raise ValueError(f'Annotation does not match an input row: {key}')
        if set(note) - {'ux','ux_basis','owner','next','title','notes'}:
            raise ValueError(f'{key}: annotations can only add presentation fields, not change source status or target.')
        if any(not isinstance(v, str) for k,v in note.items() if k != 'notes') or ('notes' in note and (not isinstance(note['notes'],list) or not all(isinstance(v,str) for v in note['notes']))):
            raise ValueError(f'{key}: invalid annotation types.')
        if 'ux' in note and (note['ux'] not in IMPACT or (note['ux'] != 'unrated' and not note.get('ux_basis'))):
            raise ValueError(f'{key}: UX estimate needs a valid level and ux_basis.')
        keyed[key].update(note)


def sort_key(row, fields):
    effort = level(row['effort'], ['trivial','small','medium','med','large'], 'unrated')
    keys = dict(blocker=not row['blocker'], urgency=URGENCY[row['urgency']], ux=IMPACT[row['ux']],
                target=TARGET[row['target']], effort={'trivial':0,'small':1,'medium':2,'med':2,'large':3}.get(effort,4),
                id=row['id'], ledger=row['ledger'], status=row['status'])
    return tuple(keys[k] for k in fields)+(row['ledger'],row['line'])


def select(rows, args):
    result=[]
    for r in rows:
        key=r['ledger']+'::'+r['id']
        if args.id and key not in args.id and r['id'] not in args.id: continue
        if args.exclude_id and (key in args.exclude_id or r['id'] in args.exclude_id): continue
        if args.status:
            if r['status'] not in args.status: continue
        elif args.view == 'unfinished' and r['status'] in CLOSED: continue
        elif args.view == 'completed' and r['status'] not in CLOSED: continue
        if args.blockers_only and not r['blocker']: continue
        if args.target and r['target'] not in args.target: continue
        if args.urgency and r['urgency'] not in args.urgency: continue
        if args.ledger and r['ledger'] not in args.ledger: continue
        if args.section and not any(s.casefold() in r['section'].casefold() for s in args.section): continue
        if args.query and args.query.casefold() not in json.dumps(r,ensure_ascii=False).casefold(): continue
        result.append(r.copy())
    result.sort(key=lambda r:sort_key(r,args.sort))
    for n,r in enumerate(result,1):r['rank']=n
    return result


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
    p.add_argument('--id',action='append',help='Include an ID or filename.md::ID; repeat for a reviewed custom subset.')
    p.add_argument('--exclude-id',action='append',help='Exclude a reviewed duplicate/pointer ID or filename.md::ID.')
    p.add_argument('--sort',default='blocker,urgency,ux',help='Ordered comma-separated keys: '+','.join(SORTS))
    p.add_argument('--columns',default=','.join(COLUMNS),help='Visible columns: '+','.join(COLUMNS))
    p.add_argument('--annotations',type=Path)
    p.add_argument('--scope-note',default='Only the explicitly listed source ledgers were read.')
    p.add_argument('--note',action='append',default=[])
    p.add_argument('--force',action='store_true',help='Replace an existing HTML output when explicitly requested.')
    return p


def render(rows, sources, warnings, args, total_blockers):
    template=(Path(__file__).resolve().parent.parent/'assets/html-report.html').read_text(encoding='utf-8')
    labels={'id':'Item','ux':'User impact (estimate)','blocker':'Release gate','effort':'Fix effort'}
    heads=''.join(f'<th scope="col"><button data-col="{n}">{E(labels.get(k,k.title()))} ↕</button></th>' for n,k in enumerate(args.columns))
    body=[]
    for r in rows:
        vals=[]
        for col in args.columns:
            value=str(r.get(col,''))
            if col=='finding':
                title=r.get('title') or plain(r['finding'])
                short=title if len(title)<=180 else title[:177].rsplit(' ',1)[0]+'…'
                details='<p><b>Source:</b> '+E(r['source'])+' : '+str(r['line'])+'</p>'
                if r['next']:details+='<p><b>Next action:</b> '+E(r['next'])+'</p>'
                if r['ux_basis']:details+='<p><b>User-impact estimate:</b> '+E(r['ux_basis'])+'</p>'
                details+=''.join('<p class="notice">'+E(n)+'</p>' for n in r['notes'])
                details+='<dl>'+''.join(f'<dt>{E(k.title())}</dt><dd>{E(v)}</dd>' for k,v in r['original'].items())+'</dl>'
                value=f'<strong>{E(short)}</strong><details><summary>Source, ratings &amp; remaining work</summary>{details}</details>'
            elif col=='blocker':value='<span class="badge">'+('Blocks release' if r['blocker'] else 'Not gated')+'</span>'
            elif col=='ux':value=E(r['ux'].title())+(' <small>estimated</small>' if r['ux']!='unrated' else '')
            else:value=E(value or 'Not recorded')
            sortvalue=sort_key(r,[col])[0] if col in SORTS else r.get(col,'')
            if isinstance(sortvalue,bool):sortvalue=int(sortvalue)
            vals.append(f'<td data-value="{E(str(sortvalue),quote=True)}">{value}</td>')
        search=' '.join(str(v) for v in r.values()).casefold()
        body.append(f'<tr data-rank="{r["rank"]}" data-blocker="{str(r["blocker"]).lower()}" data-status="{E(r["status"])}" data-ledger="{E(r["ledger"])}" data-search="{E(search,quote=True)}">'+''.join(vals)+'</tr>')
    criteria={k:getattr(args,k) for k in ['view','id','exclude_id','status','target','urgency','ledger','section','query','blockers_only','sort','columns'] if getattr(args,k)}
    options=lambda key: '<option value="">All</option>'+''.join(f'<option value="{E(v,quote=True)}">{E(v)}</option>' for v in sorted({str(r[key]) for r in rows}))
    data={'TITLE':E(args.title),'DATE':E(dt.datetime.now().astimezone().isoformat(timespec='seconds')),
          'COUNT':str(len(rows)),'BLOCKERS':str(sum(r['blocker'] for r in rows)),'TOTAL_BLOCKERS':str(total_blockers),
          'OWED':str(sum(r['status']=='done-unverified' for r in rows)), 'HEADERS':heads,'ROWS':''.join(body),
          'SCOPE':E(args.scope_note),'CRITERIA':E(json.dumps(criteria,ensure_ascii=False)),
          'NOTES':''.join('<li>'+E(x)+'</li>' for x in args.note+warnings),
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
        paths=[p.resolve() for p in args.file]
        if len(set(paths))!=len(paths) or len({p.name for p in paths})!=len(paths):raise ValueError('Input ledger paths and names must be distinct.')
        output=args.output.resolve()
        if output.suffix.lower() not in ('.html','.htm'):raise ValueError('Output must be an HTML file.')
        if output in paths or output==getattr(args.annotations,'resolve',lambda:None)():raise ValueError('Output cannot replace an input.')
        if output.exists() and not args.force:raise ValueError('Output exists; use a new filename or --force for an authorized replacement.')
        rows,sources,warnings=[],[],[]
        for path in paths:
            r,s,w=read_ledger(path);rows+=r;sources.append(s);warnings+=w
        if args.annotations:annotate(rows,json.loads(args.annotations.read_text(encoding='utf-8')))
        selected=select(rows,args)
        report=render(selected,sources,warnings,args,sum(r['blocker'] for r in rows))
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(report,encoding='utf-8')
        print(json.dumps(dict(output=str(output),rows=len(selected),blockers_in_report=sum(r['blocker'] for r in selected),blockers_in_inputs=sum(r['blocker'] for r in rows),warnings=warnings)))
    except (ValueError,OSError,TypeError,KeyError) as e:p.error(str(e))

if __name__=='__main__':main()
