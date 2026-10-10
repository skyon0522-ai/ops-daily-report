"""Report presentation must not execute log text or hide data without scripting."""

from copy import deepcopy
from html.parser import HTMLParser

from ops_daily_report.html_report import render_html


def fixture_report():
    return {
        'schema_version': 1,
        'engine': {'name': 'Drain3', 'settings': {'depth': 4}},
        'inputs': {'current_files': 1, 'baseline_files': 1},
        'totals': {
            'current': {'lines': 3, 'levels': {'ERROR': 2, 'INFO': 1}},
            'baseline': {'lines': 1, 'levels': {'ERROR': 1}},
        },
        'patterns': [
            {'id': 'a'*64, 'service': 'worker', 'template': 'Job <*> failed',
             'status': 'recurring', 'current_count': 2, 'baseline_count': 1,
             'delta': 1, 'levels': {'ERROR': 2}},
            {'id': 'b'*64, 'service': 'api', 'template': 'Started',
             'status': 'new', 'current_count': 1, 'baseline_count': 0,
             'delta': 1, 'levels': {'INFO': 1}},
        ],
    }


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external_resources = []
        self.inline_scripts = 0
        self.handlers = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'script':
            self.inline_scripts += 1
        for key, value in attrs:
            if key.startswith('on'):
                self.handlers.append(key)
            if key == 'src' or (tag == 'link' and key == 'href'):
                self.external_resources.append(value)


def test_untrusted_template_service_and_id_cannot_create_markup():
    report = fixture_report()
    report['patterns'][0].update(
        service='<img src=x onerror=alert(1)>',
        template='</code><script>alert(2)</script>',
        id='"><img src=x onerror=alert(3)>',
    )
    output = render_html(report)
    parser = ResourceParser()
    parser.feed(output)
    assert parser.inline_scripts == 1  # Only the static local filter implementation.
    assert parser.external_resources == []
    assert parser.handlers == []
    assert '&lt;script&gt;alert(2)&lt;/script&gt;' in output


def test_baseline_counts_and_non_script_content_are_readable():
    output = render_html(fixture_report())
    assert 'Baseline: 1 messages' in output
    assert 'Job &lt;*&gt; failed' in output
    assert 'data-status="recurring"' in output
    assert 'data-status="new"' in output
    assert 'Error / critical messages' in output
    assert '<td class="number">+1</td>' in output
    assert 'role="status" aria-live="polite"' in output


def test_no_baseline_is_distinguished_from_zero_baseline_counts():
    report = fixture_report()
    report['totals']['baseline'] = None
    report['inputs']['baseline_files'] = None
    for pattern in report['patterns']:
        pattern.update(status='uncompared', baseline_count=None, delta=None)
    output = render_html(report)
    assert 'No baseline selected' in output
    assert '<strong>—</strong><span>New template groups</span>' in output
    assert '<td class="number">—</td>' in output


def test_render_is_repeatable_and_does_not_mutate_report():
    report = fixture_report()
    before = deepcopy(report)
    assert render_html(report) == render_html(report)
    assert report == before


def test_empty_inputs_have_explicit_message():
    report = fixture_report()
    report['patterns'] = []
    report['totals']['current'] = {'lines': 0, 'levels': {}}
    output = render_html(report)
    assert 'No messages in the selected inputs.' in output


def test_input_notes_are_visible_and_escaped():
    report = fixture_report()
    report['inputs']['warnings'] = ['Unsupported <script> text omitted.']
    output = render_html(report)
    assert 'aria-label="Input notes"' in output
    assert 'Unsupported &lt;script&gt; text omitted.' in output
