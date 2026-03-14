# ops-daily-report

Minimal Python CLI scaffold for summarizing Linux logs.

## Scope of this first PR
- Project scaffolding only
- Basic parser + CLI wiring
- Pytest test suite setup
- Placeholder folders for docs and reports

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
ops-daily-report --log-dir sample_logs
```

## Project layout
- `src/ops_daily_report/` - package code
- `sample_logs/` - sample Linux log files
- `tests/` - pytest tests
- `docs/` - documentation placeholders
- `reports/` - generated outputs (later)

## Planned generated outputs (later)
- `reports/daily_summary.md`
- `reports/alerts.csv`
- `reports/run.log`
