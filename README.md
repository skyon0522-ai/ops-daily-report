# Ops Daily Report

Turn local service logs into a searchable, offline report of repeated messages
and changes from a selected baseline. Review the HTML in your browser, or use
the Markdown and JSON exports. Your input logs stay unchanged.

![Synthetic comparison report](docs/assets/report.png)

Search templates or services, filter comparison status or current level, and
expand a group's details. The single-file report also works without JavaScript.

## Install

Requires Python 3.10 or later. From a downloaded or cloned checkout:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

<details>
<summary>Windows PowerShell, without activation</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\ops-daily-report.exe demo
```

Use the full executable path when working in another directory.

</details>

If you have the built wheel, install it instead with
`python -m pip install /path/to/ops_daily_report-0.2.0-py3-none-any.whl`.
After installation, the command works from any directory.

## Try it

```sh
ops-daily-report demo
```

The packaged synthetic logs produce `ops-daily-demo/report.html`, plus Markdown
and JSON. The command prints the full HTML path. Add `--open` to ask your default
browser to open it. To repeat the demo, choose a fresh directory:

```sh
ops-daily-report demo --output-dir reports/another-demo --open
```

The example compares 6 current messages with 4 baseline messages: health-check
failures increase, a database timeout appears, and disk-pressure messages are
absent. These are review cues; a new template does not establish an incident.
No accounts, containers or external services are needed to run the app.

## Use your own logs

```sh
ops-daily-report --log-dir /path/to/current --baseline-dir /path/to/previous --output-dir reports/new-run
```

Inputs are top-level UTF-8 `*.log` files with supported headers. Omit
`--baseline-dir` for a single batch, or omit `--output-dir` for a terminal summary.
Saved report files are never overwritten. Use a new output directory for each
run, and review templates for sensitive text before sharing exports.

## Documentation

- [Usage, supported headers and comparison meanings](docs/usage.md)
- [Implementation and data flow](docs/architecture.md)
- [Development, tests and distribution checks](docs/development.md)
- [Copied source and licenses](docs/source.md)
- [Research basis and resource observations](docs/research.md)
- [Committed synthetic demo outputs](examples/reports/)
- [Security and problem reporting](SECURITY.md)

## Limits and license

This is a local batch-review tool. It does not select calendar days, stream live
logs, assemble multiline stack traces, diagnose incidents or send alerts.
Unsupported lines remain counted as unknown. Template grouping can merge or
split events; counts depend on the selected inputs. No production accuracy or
incident outcome is claimed.

The parser executes a copied, pinned subset of
[Drain3](https://github.com/logpai/Drain3/tree/0fb6d6e1828838fa05c8f6fa5cda878e02ea79c7).
This project adds header-based levels, service separation, batch comparisons,
safe exports and local search. The app is MIT-licensed; copied components retain
their MIT and Apache-2.0 notices. See [source and licenses](docs/source.md).
