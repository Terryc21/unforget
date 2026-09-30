# HTML report example

[![Unforget HTML report showing ranked unfinished work](unfinished-ledger.png)](unfinished-ledger.html)

**[Download the interactive HTML report](https://github.com/Terryc21/unforget/raw/refs/heads/main/examples/unfinished-ledger.html)**
and open the downloaded file in your browser. It works offline, with search,
release/status filters, sortable columns, expandable source ratings, dark mode
and printing. GitHub's file view shows the HTML source rather than running it.

The report comes from [UNFORGET.md](UNFORGET.md), the existing sanitized sample
ledger. It shows unfinished items, ranked by release blocker and recorded urgency.
The illustrative P0 format row demonstrates a release blocker. Completed and withdrawn work stays in
the source but is omitted from this view. User-impact estimates are omitted because
the sample does not record them. This is sample data, not a live release assessment.

From the repository root, regenerate the report with Python 3.9+:

```bash
python3 examples/generate_html.py
```

The script uses the shared HTML generator and template. It replaces only
`examples/unfinished-ledger.html`; the sample ledger stays unchanged. Source paths
are relative to the repository root, and the report records the source checksum
and generation time. The PNG is a browser screenshot; refresh it after visible
report changes.

For your own ledger, ask Codex `$unforget report`, or use `/unforget report` in
Claude Code (`/unforget:unforget report` for a plugin install). See the
[report options](../reference/html-report.md) for custom scopes and rankings.
