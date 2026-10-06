#!/usr/bin/env python3
"""Regenerate the public HTML example using the shared report generator.

Run from any directory: python3 /path/to/unforget/examples/generate_html.py
Replaces examples/unfinished-ledger.html and examples/quick-wins.html (or only the\npages named on the command line); the source ledger is read-only.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import html_report as report


COMMON_NOTE = 'Source paths are relative to the repository root. User-impact estimates are omitted because the sample does not record them.'
SAMPLE_NOTE = 'Sample data for demonstration; not a live release assessment.'
PAGES = [
    ('unfinished-ledger.html', [
        '--title', 'Unforget · unfinished work',
        '--sort', 'blocker,urgency',
        '--columns', 'rank,id,blocker,finding,urgency,status,effort',
        '--scope-note', 'Example from the bundled sample ledger. Unfinished work, ranked by release blockers, then recorded urgency.',
        '--note', SAMPLE_NOTE + " P0 is the source ledger's illustrative release-blocker row.",
        '--note', COMMON_NOTE,
    ]),
    ('quick-wins.html', [
        '--title', 'Unforget · quick wins',
        '--effort', 'trivial', '--effort', 'small',
        '--sort', 'roi,urgency', '--limit', '5',
        '--columns', 'rank,id,blocker,finding,urgency,status,effort',
        '--scope-note', 'Example from the bundled sample ledger. Trivial and small fixes, best value for the effort first, cut to five rows.',
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
    # Keep provenance reproducible without embedding the publisher's local paths.
    relative_source = source.relative_to(ROOT).as_posix()
    manifest['path'] = relative_source
    for row in rows:
        row['source'] = relative_source
    selected = report.select(rows, args)
    warnings.extend(report.selection_notes(args))
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
