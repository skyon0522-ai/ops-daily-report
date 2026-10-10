"""Check that the committed synthetic demo still matches generated output."""

import json
from pathlib import Path

from ops_daily_report.html_report import render_html
from ops_daily_report.report import build_report, render_markdown


def main():
    root = Path(__file__).resolve().parents[1]
    report = build_report(root / 'examples/current', root / 'examples/baseline')
    expected = root / 'examples/reports'
    if report != json.loads((expected / 'report.json').read_text(encoding='utf-8')):
        raise SystemExit('Demo JSON differs; inspect input or report behavior before updating it.')
    for filename, rendered in [('report.md', render_markdown(report)), ('report.html', render_html(report))]:
        if rendered != (expected / filename).read_text(encoding='utf-8'):
            raise SystemExit(f'Demo {filename} differs; inspect the change before updating it.')
    print('Synthetic demo: JSON, Markdown and HTML match.')


if __name__ == '__main__':
    main()
