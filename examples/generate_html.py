#!/usr/bin/env python3
"""Regenerate the public HTML example using the shared report generator.

Run from any directory: python3 /path/to/unforget/examples/generate_html.py
Replaces every page listed in PAGES (or only the pages named on the command line);
the source ledger is read-only.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import html_report as report


COMMON_NOTE = 'Source paths are relative to the repository root; source links open the adjacent sample ledger. User impact remains Unrated because no assessment is recorded.'
SAMPLE_NOTE = 'Fictional demonstration: assignments, next steps and check evidence come from report-annotations.json. No real work or release has been verified.'
PAGES = [
    ('unfinished-ledger.html', [
        '--title', 'Unforget · unfinished work',
        '--sort', 'blocker,urgency',
        '--scope-note', 'Fictional demo with illustrative assignments and check evidence. Unfinished work, ranked by release blockers, then recorded urgency.',
        '--note', SAMPLE_NOTE + " P0 is the source ledger's illustrative release-blocker row.",
        '--note', COMMON_NOTE,
    ]),
    ('top-10.html', [
        '--title', 'Unforget · ten most urgent',
        '--sort', 'blocker,urgency', '--limit', '10',
        '--columns', 'rank,id,finding,status,effort,roi,owner,next',
        '--scope-note', 'Fictional demo with illustrative assignments and check evidence. The ten most urgent unfinished items, ship blockers first.',
        '--note', SAMPLE_NOTE,
        '--note', COMMON_NOTE,
    ]),
    ('trivial-fixes.html', [
        '--title', 'Unforget · trivial fixes only',
        '--effort', 'trivial',
        '--sort', 'urgency,roi',
        '--columns', 'rank,id,finding,status,effort,roi,owner,next',
        '--scope-note', 'Fictional demo with illustrative assignments and check evidence. Only the fixes rated trivial, most urgent first.',
        '--note', SAMPLE_NOTE,
        '--note', COMMON_NOTE,
    ]),
    ('best-value.html', [
        '--title', 'Unforget · best value first',
        '--sort', 'roi,urgency,effort',
        '--columns', 'rank,id,finding,status,effort,roi,owner,next',
        '--scope-note', 'Fictional demo with illustrative assignments and check evidence. Everything unfinished, ranked by value for the effort, then urgency, then fix effort.',
        '--note', SAMPLE_NOTE,
        '--note', COMMON_NOTE,
    ]),
    ('ship-blockers.html', [
        '--title', 'Unforget · ship blockers',
        '--blockers-only',
        '--columns', 'rank,id,finding,status,effort,roi,owner,next',
        '--scope-note', 'Fictional demo with illustrative assignments and check evidence. Only what stands between you and the next release.',
        '--note', SAMPLE_NOTE + " P0 is the source ledger's illustrative release-blocker row.",
        '--note', COMMON_NOTE,
    ]),
    ('quick-wins.html', [
        '--title', 'Unforget · quick wins',
        '--effort', 'trivial', '--effort', 'small',
        '--sort', 'roi,urgency', '--limit', '5',
        '--columns', 'rank,id,finding,status,effort,roi,owner,next',
        '--scope-note', 'Fictional demo with illustrative assignments and check evidence. Trivial and small fixes, best value for the effort first, cut to five rows.',
        '--note', SAMPLE_NOTE,
        '--note', COMMON_NOTE,
    ]),
]


def build(source, name, flags):
    output = ROOT / 'examples' / name
    args = report.parser().parse_args(['--file', str(source), '--output', str(output), *flags])
    args.sort = args.sort.split(',')
    args.columns = args.columns.split(',')
    rows, manifest, warnings = report.read_ledger(source)
    annotations = json.loads((source.parent / 'report-annotations.json').read_text(encoding='utf-8'))
    report.annotate(rows, annotations)
    report.prepare_presentation(rows)
    # Keep provenance reproducible without embedding the publisher's local paths.
    relative_source = source.relative_to(ROOT).as_posix()
    manifest['path'] = relative_source
    for row in rows:
        row['source'] = relative_source
        row['source_link'] = source.name
    selected = report.select(rows, args)
    html = report.render(selected, [manifest], warnings, args,
                         sum(row['blocker'] for row in rows))
    output.write_text(html, encoding='utf-8')
    print(f'{output.name}: {len(selected)} of {args.select_info["matched"]} items, '
          f'{sum(row["blocker"] for row in selected)} included blockers')


def main():
    source = ROOT / 'examples' / 'UNFORGET.md'
    only = set(sys.argv[1:])   # optional: page names to regenerate
    for name, flags in PAGES:
        if not only or name in only:
            build(source, name, flags)


if __name__ == '__main__':
    main()
