#!/usr/bin/env python3
"""Regenerate the public HTML example using the shared report generator.

Run from any directory: python3 /path/to/unforget/examples/generate_html.py
Only examples/unfinished-ledger.html is replaced; the source ledger is read-only.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import html_report as report


def main():
    source = ROOT / 'examples' / 'UNFORGET.md'
    output = ROOT / 'examples' / 'unfinished-ledger.html'
    args = report.parser().parse_args([
        '--file', str(source), '--output', str(output),
        '--title', 'Unforget · unfinished work',
        '--sort', 'blocker,urgency',
        '--columns', 'rank,id,blocker,finding,urgency,status,effort',
        '--scope-note', 'Example from the bundled sample ledger. Unfinished work, ranked by release blockers, then recorded urgency.',
        '--note', 'Sample data for demonstration; not a live release assessment. P0 is the source ledger\'s illustrative release-blocker row.',
        '--note', 'Source paths are relative to the repository root. User-impact estimates are omitted because the sample does not record them.',
    ])
    args.sort = args.sort.split(',')
    args.columns = args.columns.split(',')
    rows, manifest, warnings = report.read_ledger(source)
    # Keep provenance reproducible without embedding the publisher's local paths.
    relative_source = source.relative_to(ROOT).as_posix()
    manifest['path'] = relative_source
    for row in rows:
        row['source'] = relative_source
    selected = report.select(rows, args)
    html = report.render(selected, [manifest], warnings, args,
                         sum(row['blocker'] for row in rows))
    output.write_text(html, encoding='utf-8')
    print(f'{output.name}: {len(selected)} unfinished items, '
          f'{sum(row["blocker"] for row in selected)} included blockers')


if __name__ == '__main__':
    main()
