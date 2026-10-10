"""Offline, escaped HTML presentation of a generated report."""

from html import escape


def render_html(report: dict) -> str:
    current = report['totals']['current']
    baseline = report['totals']['baseline']
    patterns = report['patterns']
    levels = current['levels']
    errors = levels.get('ERROR', 0) + levels.get('CRITICAL', 0)
    new_count = sum(p['status'] == 'new' for p in patterns)
    baseline_label = 'No baseline selected' if baseline is None else f"Baseline: {baseline['lines']:,} messages"
    new_value = '—' if baseline is None else str(new_count)
    warnings = report['inputs'].get('warnings', [])
    input_notes = ('<section class="input-notes" aria-label="Input notes"><strong>Input notes</strong><ul>'
                   + ''.join(f'<li>{escape(str(note))}</li>' for note in warnings)
                   + '</ul></section>') if warnings else ''
    rows = []
    for pattern in patterns:
        service = escape(str(pattern['service']))
        template = escape(str(pattern['template']))
        status = pattern['status']
        status_class = status if status in {'new', 'recurring', 'absent', 'uncompared'} else 'uncompared'
        counts = pattern['levels']
        severity = ('ERROR' if counts.get('ERROR', 0) or counts.get('CRITICAL', 0)
                    else 'WARNING' if counts.get('WARNING', 0) else 'OTHER')
        level_text = ', '.join(f'{escape(str(key))} {int(value)}' for key, value in counts.items() if value) or 'No current messages'
        prior = '—' if pattern['baseline_count'] is None else f"{pattern['baseline_count']:,}"
        delta = '—' if pattern['delta'] is None else f"{pattern['delta']:+,}"
        identifier = escape(str(pattern['id']), quote=True)
        rows.append(f'''<tr data-status="{status_class}" data-severity="{severity}">
<td><span class="service">{service}</span><code class="template">{template}</code>
<details><summary>Group details</summary><p class="group-id">ID: {identifier}</p><p>{level_text}</p></details></td>
<td><span class="badge {status_class}">{escape(str(status).capitalize())}</span></td>
<td class="number">{int(pattern['current_count']):,}</td><td class="number">{prior}</td><td class="number">{delta}</td>
<td class="levels">{level_text}</td></tr>''')
    rows_html = '\n'.join(rows)
    if not rows:
        rows_html = '<tr><td colspan="6">No messages in the selected inputs.</td></tr>'
    engine = report['engine']
    settings = escape(str(engine.get('settings', {})))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>Ops Daily Report</title>
<style>
:root{{--ink:#172c3e;--muted:#516678;--line:#d6e0e6;--brand:#16615c;--paper:#fff;--bg:#f3f6f8}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1280px;margin:auto;padding:40px 28px 60px}}a{{color:var(--brand)}}h1{{font-size:clamp(28px,4vw,40px);line-height:1.2;margin:8px 0 14px;letter-spacing:-.025em}}
h2{{font-size:23px;line-height:1.3;margin:0}}p{{margin:0 0 14px}}.eyebrow{{color:var(--brand);font-weight:700;letter-spacing:.08em;font-size:14px}}
.intro{{max-width:72ch;color:var(--muted)}}.context{{display:flex;flex-wrap:wrap;gap:8px 20px;color:var(--muted);margin:20px 0}}
.input-notes{{padding:16px 20px;margin:0 0 24px;background:#fff8e7;border:1px solid #e6d6a4;border-radius:8px;overflow-wrap:anywhere}}.input-notes ul{{margin:8px 0 0;padding-left:22px}}
.stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:24px 0 32px}}
.stat{{padding:18px 20px;background:var(--paper);border:1px solid var(--line);border-radius:10px}}.stat strong{{display:block;font-size:32px;line-height:1.2;font-variant-numeric:tabular-nums}}.stat span{{display:block;margin-top:8px;color:var(--muted)}}
.panel{{background:var(--paper);border:1px solid var(--line);border-radius:12px;overflow:hidden}}.panel-head{{padding:24px 24px 0}}.panel-head p{{color:var(--muted);margin:10px 0 0}}
.filters{{display:flex;flex-wrap:wrap;align-items:end;gap:14px;padding:20px 24px}}label{{display:flex;flex-direction:column;gap:5px;font-weight:600}}label.search{{flex:1;min-width:min(220px,100%)}}
input,select,button{{font:inherit;min-height:44px;border:1px solid #a6b8c5;border-radius:6px;padding:8px 12px;background:white;color:var(--ink);max-width:100%}}button{{cursor:pointer;font-weight:600}}input:focus-visible,select:focus-visible,button:focus-visible,summary:focus-visible,.table-scroll:focus-visible{{outline:3px solid #197a74;outline-offset:3px}}
.result-count{{padding:0 24px 14px;color:var(--muted)}}.table-scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;text-align:left}}caption{{text-align:left;padding:0 24px 12px;color:var(--muted)}}th{{padding:12px 16px;background:#edf3f5;white-space:nowrap;font-size:14px;color:#40596a}}td{{padding:18px 16px;border-top:1px solid var(--line);vertical-align:top}}th:first-child,td:first-child{{padding-left:24px;min-width:300px;width:48%}}.service{{font-weight:700;display:block;margin-bottom:6px}}.template{{display:block;font:15px/1.6 ui-monospace,"Cascadia Code",Consolas,monospace;overflow-wrap:anywhere;white-space:pre-wrap;color:#193e52}}.number{{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}}.levels{{min-width:155px;color:var(--muted);font-size:14px}}.badge{{display:inline-block;padding:3px 9px;border-radius:5px;font-size:14px;font-weight:600;white-space:nowrap}}.new{{background:#ddf2ee;color:#13584d}}.recurring{{background:#e5eef7;color:#285172}}.absent{{background:#eeeef2;color:#55576a}}.uncompared{{background:#eff2f4;color:#526371}}details{{margin-top:12px}}summary{{cursor:pointer;color:var(--brand);font-size:14px;min-height:28px}}details p{{margin:8px 0 0;font-size:14px;color:var(--muted)}}.group-id{{overflow-wrap:anywhere}}.method{{margin-top:28px;max-width:85ch}}.method summary{{font-size:18px;font-weight:700}}.method p{{font-size:16px}}.footer{{margin-top:32px;font-size:14px;color:var(--muted)}}[hidden]{{display:none!important}}.no-results{{padding:22px 24px;color:var(--muted)}}
@media(max-width:700px){{main{{padding:24px 16px 40px}}.stats{{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}.stat{{padding:14px}}.stat strong{{font-size:27px}}.filters,.panel-head{{padding-left:16px;padding-right:16px}}.filters label{{width:100%}}.filters button{{width:100%}}.result-count{{padding-left:16px}}th:first-child,td:first-child{{padding-left:16px;min-width:250px}}}}
@media print{{body{{background:white}}main{{max-width:none;padding:0}}.filters,.result-count,.no-results{{display:none}}tr[hidden]{{display:table-row!important}}.table-scroll{{overflow:visible}}.panel{{border:0}}th,td{{padding:10px 7px!important}}th:first-child,td:first-child{{min-width:0}}.levels{{min-width:0}}.stats{{gap:8px}}.stat{{padding:10px}}.footer{{margin-top:16px}}}}
</style></head><body><main>
<header><div class="eyebrow">LOCAL LOG REVIEW</div><h1>Ops Daily Report</h1>
<p class="intro">Review repeated messages and compare template counts with a selected baseline. Start with error-level groups, then inspect new and recurring patterns.</p>
<div class="context"><span>{baseline_label}</span><span>{int(report['inputs']['current_files'])} current log files</span><span>Offline · no data upload</span></div></header>
<section class="stats" aria-label="Current input summary">
<div class="stat"><strong>{int(current['lines']):,}</strong><span>Current messages</span></div>
<div class="stat"><strong>{int(errors):,}</strong><span>Error / critical messages</span></div>
<div class="stat"><strong>{new_value}</strong><span>New template groups</span></div>
<div class="stat"><strong>{int(levels.get('UNKNOWN',0)):,}</strong><span>Unknown-level messages</span></div></section>
{input_notes}
<section class="panel" aria-labelledby="groups-title"><div class="panel-head"><h2 id="groups-title">Template groups</h2>
<p>New means not seen in this baseline. Counts depend on the selected batch sizes; they are not normalized rates.</p></div>
<div class="filters" hidden id="filters"><label class="search">Search templates or services<input id="search" type="search" placeholder="e.g. timeout" autocomplete="off"></label>
<label>Comparison<select id="status"><option value="">All statuses</option><option value="new">New</option><option value="recurring">Recurring</option><option value="absent">Absent</option><option value="uncompared">Uncompared</option></select></label>
<label>Current level<select id="severity"><option value="">All levels</option><option value="ERROR">Error / critical</option><option value="WARNING">Warning, no errors</option><option value="OTHER">Other / no current messages</option></select></label><button id="reset" type="button">Reset filters</button></div>
<p class="result-count" id="result-count" role="status" aria-live="polite">{len(patterns)} template groups</p>
<noscript><p class="result-count">All groups are shown. Enable JavaScript for local search and filters.</p></noscript>
<div class="table-scroll" role="region" aria-label="Template counts, scroll horizontally for all columns" tabindex="0"><table>
<thead><tr><th scope="col">Service / message template</th><th scope="col">Status</th><th scope="col">Current</th><th scope="col">Baseline</th><th scope="col">Change</th><th scope="col">Current levels</th></tr></thead><tbody>{rows_html}</tbody></table></div>
<p class="no-results" id="no-results" hidden>No groups match these filters. Reset filters to see all groups.</p></section>
<details class="method"><summary>Method and sharing notes</summary>
<p>Drain3 groups similar message text into templates. Each service has a separate miner. Baseline messages are processed first, followed by current messages. This comparison uses the final templates for both batches.</p>
<p>Settings: <code>{settings}</code>. Severity comes from supported log headers. Unsupported lines remain visible as unknown-level messages.</p>
<p>Template grouping does not diagnose incidents or prove that a new pattern is anomalous. Templates can still contain sensitive text: review all report formats before sharing. No raw log excerpts are intentionally added.</p>
<p>Readable export: <a href="report.md">Markdown</a> · Structured export: <a href="report.json">JSON</a></p></details>
<footer class="footer">Ops Daily Report · Drain3 parser core · Single-file HTML with local controls</footer>
</main><script>
(()=>{{
const rows=Array.from(document.querySelectorAll('tbody tr[data-status]'));
const search=document.getElementById('search'),status=document.getElementById('status'),severity=document.getElementById('severity');
function apply(){{const query=search.value.trim().toLowerCase();let shown=0;
for(const row of rows){{const matches=(!query||row.cells[0].textContent.toLowerCase().includes(query))&&(!status.value||row.dataset.status===status.value)&&(!severity.value||row.dataset.severity===severity.value);row.hidden=!matches;if(matches)shown++;}}
document.getElementById('result-count').textContent=shown+' of '+rows.length+' template groups';document.getElementById('no-results').hidden=shown>0||rows.length===0;}}
search.addEventListener('input',apply);status.addEventListener('change',apply);severity.addEventListener('change',apply);
document.getElementById('reset').addEventListener('click',()=>{{search.value='';status.value='';severity.value='';apply();search.focus();}});
document.getElementById('filters').hidden=false;apply();
}})();
</script></body></html>'''
