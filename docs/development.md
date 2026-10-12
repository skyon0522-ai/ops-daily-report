# Development and verification

Create a virtual environment, activate it, and install development tools:

```sh
python -m pip install -e '.[dev]' build
python -m pytest -q
python scripts/check_demo.py
```

The suite checks header severity, per-service template grouping, baseline counts,
HTML escaping, safe file creation, first-run guidance, packaged demo behavior and
browser-launch failure handling. It includes the eight copied Drain3 cases.
The demo check compares the committed JSON, Markdown and HTML with a fresh run.

## Build and test the installed app

```sh
python -m build
python scripts/check_distribution.py dist/ops_daily_report-0.2.0-py3-none-any.whl --sdist dist/ops_daily_report-0.2.0.tar.gz
```

The distribution check inspects packaged logs and license notices, then creates
a fresh virtual environment outside the checkout and installs the wheel. It
runs the console command without source-path injection, checks the demo counts,
refuses a repeated output, and exercises the own-log-directory command.
The environment and outputs are temporary and removed after the check.

The GitHub workflow performs these checks on Windows and Linux with Python 3.10
and 3.12. A workflow definition is not an executed remote result; consult the
[workflow runs](https://github.com/skyon0522-ai/ops-daily-report/actions/workflows/checks.yml)
for a published revision's results.

## Verification limits

Tests cover defined source behavior and synthetic examples. They do not measure
production grouping accuracy, incident outcomes or anonymization. Validate
representative, appropriately handled logs before using counts for an operational
decision. The report interface and its design references are described in
[DESIGN.md](DESIGN.md); browser presentation requires a separate visual check.
