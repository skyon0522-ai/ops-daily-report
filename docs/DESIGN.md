# Report interface design

The reader is an engineer reviewing a selected batch of local service logs. The
report should help them find repeated error-level messages, compare their counts
with an explicitly selected baseline, and inspect the underlying templates.

## Inspected references

- [Grafana Explore: logs](https://grafana.com/docs/grafana/latest/visualizations/explore/logs-integration/), inspected 2026-10-10: visible result counts, explicit level filters, client-side search, wrapped log text, and progressive disclosure for details. This report adopts those interaction patterns, not Grafana source, logos, or its live telemetry integrations.
- [Drain3 0.9.11](https://github.com/logpai/Drain3/tree/0fb6d6e1828838fa05c8f6fa5cda878e02ea79c7): an actual copied parser supplies message templates. See the source manifest for the copied files and packaging changes.
- [linear-tui README](https://github.com/k1-c/linear-tui/blob/fa79ffed365c2deff1916022abe8652989682216/README.md): show the working result, then installation, usage, development and reference material.
- [linear-tui installation and first run](https://github.com/k1-c/linear-tui#install), inspected 2026-10-13: make the installed command the entry point, use a short installation path, and link detailed documentation after useful commands. Ops Daily Report adopts that order with a packaged, account-free demo; no Linear code or visual assets are copied.

## Adopted structure

The single-file HTML report starts with batch totals, then searchable template
groups. A row shows its service, template, comparison status, counts and current
levels. Method details follow the results. The same information is available as
JSON and Markdown; no browser or JavaScript is needed to run the CLI.

The README keeps the existing report screenshot, then gives installation, an
installed synthetic demo, an own-data command, and documentation links. A bare
command prints help without creating files. The demo includes both batches in
the package, writes into a named directory, and refuses existing report files.
Opening a browser requires `--open`; a launch failure preserves the reports and
prints a warning. These changes remove a checkout-relative first-run dependency
without changing the report's approved layout.

## Implementation constraints

Use semantic controls, visible keyboard focus, a live result-count announcement,
text labels in addition to color, and wrapping for long templates. At narrow
widths the table scrolls within its labeled region. Print hides filter controls
and shows all rows. All assets are inline; there are no external fonts, scripts,
requests or tracking. Escape every template and service before HTML output.

Counts describe the selected inputs. New means absent from the selected baseline,
not an anomaly. Template mining is not redaction: review reports before sharing.
The app has no incident diagnosis, remediation, date filtering or live tailing.
