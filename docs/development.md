# Development and verification

Create a virtual environment and install the package as described in the README.
Run the app checks and the committed-demo consistency check:

```sh
python -m pytest -q
python scripts/check_demo.py
```

The installed CLI can produce a fresh bundle:

```sh
ops-daily-report --log-dir examples/current --baseline-dir examples/baseline --output-dir reports/check-run
```

## What was checked locally

The reconstruction was checked on Windows with Python 3.12.14, pytest 9.1.1 and
cachetools 5.3.1, in a task-local virtual environment.

| Check | Observed result |
| --- | --- |
| Project suite | 33 passed, including the eight copied upstream Drain3 cases. |
| Original Drain3 cases | Eight passed against the unadapted algorithm, profiler and test files after their SHA-256 hashes matched the pinned upstream source. |
| Synthetic demo | Current 6 messages, baseline 4; 2 new, 3 recurring and 1 absent template groups. Counts are conserved. |
| Export consistency | JSON, Markdown and HTML match a fresh report from the included synthetic inputs. |
| Browser presentation | 31 checks passed across 1440px, 390px and 320px widths, including local filters, empty search, reset/focus, print and JavaScript-disabled reading. No external network requests occurred. |
| Distribution | A built wheel includes the copied MIT and Apache-2.0 license texts. |

Checks cover explicit header severity, unsupported input, changing numeric fields,
per-service isolation under a low tree-child limit, baseline comparison,
repeatable output, empty/missing input, invalid UTF-8, output overlap/replacement,
legacy-console output and HTML escaping. See [tests](../tests/) for the actual
assertions and [source](source.md) for the upstream boundary.

The browser checks and wheel inspection are local verification records. The
GitHub workflow runs the Python tests, demo check and installed CLI on Python
3.10 and 3.12. Python 3.10 and remote CI were not executed during this local
reconstruction; consult [workflow runs](https://github.com/skyon0522-ai/ops-daily-report/actions/workflows/checks.yml)
for the published revision's actual results.

## Limits of these checks

This is verification of source behavior and specified examples. It is not a
production benchmark, real-incident evaluation, anonymization test or measurement
of grouping accuracy across arbitrary log formats. Test passes do not establish
business outcomes. Validate representative, appropriately handled logs before
using reports for an operational decision.
