# Usage

## Generate a report

Choose directories that contain the log batches you want to compare. The CLI
reads top-level `*.log` files in filename order. It does not choose calendar days
or query remote log stores.

```sh
ops-daily-report --log-dir examples/current --baseline-dir examples/baseline --output-dir reports/demo
```

Open `reports/demo/report.html` in a browser. Search a message template or service,
filter comparison status, or show groups containing error/critical messages.
Reset filters to restore all groups. Markdown and JSON exports are in the same
directory. JavaScript is optional; without it, all groups remain readable.

For a single batch, omit `--baseline-dir`. Comparison fields are then uncomputed,
not zero. To print a terminal summary only, omit `--output-dir`.

```sh
ops-daily-report --log-dir sample_logs
ops-daily-report --log-dir /path/to/current --baseline-dir /path/to/previous --output-dir reports/new-run
```

Outputs are not overwritten. Select a fresh output directory for the next run.
Input logs are not modified. Missing directories and unreadable files produce an
error; an existing empty directory produces an explicit empty report.

## Read the comparison

| Status | Meaning |
| --- | --- |
| New | A final template group has current messages and no baseline messages. |
| Recurring | A final template group has messages in both selected batches. |
| Absent | A final template group has baseline messages and no current messages. |
| Uncompared | No baseline was selected. |

Change is current count minus baseline count. These are counts, not rates. If the
batches have different durations, traffic levels or collection coverage, the
counts alone do not establish that reliability improved or worsened.

Each service has a separate miner. Baseline messages are mined first and current
messages second, with both batches using the final templates from the same run.
A group's ID describes that final service/template pair; it is
not a permanent event ID across future runs or template generalization.

## Data handling

The report contains templates, services and counts. It does not intentionally add
raw log excerpts or absolute input paths. A template can retain names, identifiers,
addresses or other sensitive text, particularly for a group with one message.
Template mining is not anonymization. Review HTML, Markdown and JSON before
sharing them, and keep operational logs and generated reports out of Git.

No cloud, model, telemetry or account connection is used when running the CLI.
Installing dependencies requires package access; running the installed app does
not.

## Supported text headers

Input files are UTF-8. These header shapes are recognized:

```text
Mar 14 00:01:11 host app[123]: ERROR Health check failed
2026-10-10T00:01:11Z ERROR app: Health check failed
ERROR app: Health check failed
```

The first form extracts the syslog-style service name and optional PID. The
second accepts an ISO-shaped timestamp, an optional fractional part and offset,
then a level and optional `service:` prefix. The third begins with a recognized
level token. These are text-header patterns, not full RFC or calendar validation.
Service names are case-folded for grouping. Missing service names use `unknown`.

`ERR` maps to `ERROR`, `WARN` to `WARNING`, and `FATAL` to `CRITICAL`. `INFO`,
`DEBUG` and `CRITICAL` retain their names. Other recognized level tokens such as
`NOTICE` or `TRACE` are reported as `UNKNOWN`. A word later in the message body
does not change its level.

Unrecognized header shapes are counted in input notes and grouped under the
fixed template `Unsupported log line`. Their raw text is discarded by the
report parser. Recognized headers with an unknown level can retain message
text in templates, so the sharing review still applies.
