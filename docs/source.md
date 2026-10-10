# Copied source and licenses

This reconstruction reuses the existing `ops-daily-report` package and CLI
entry point at `abe2959f20d4e51da6db5cf28b1ae66b2fa79623`, then adds an executable,
vendored subset of [Drain3 0.9.11](https://github.com/logpai/Drain3/tree/0fb6d6e1828838fa05c8f6fa5cda878e02ea79c7).

## Copied component

| Upstream file | Local role | Adaptation |
| --- | --- | --- |
| `drain3/drain.py` | The template-mining algorithm executed by `report.py`. | One profiler import changed to a relative package import. |
| `drain3/simple_profiler.py` | The parser's profiler dependency. | None. |
| `tests/test_drain.py` | Eight source-behavior tests of the copied parser. | Import redirected to the vendored package; terminal newline added. |
| `LICENSE.txt` | Original MIT notice. | None. |

The exact commit is `0fb6d6e1828838fa05c8f6fa5cda878e02ea79c7`.
[PROVENANCE.json](../PROVENANCE.json) records original/local SHA-256 hashes,
paths, adaptations and the dependency pin. Small package initializers are local;
upstream `TemplateMiner` and its persistence/broker integrations are not copied.

## Licenses

The application retains its [MIT license](../LICENSE). Copied Drain3 algorithm
code and tests retain their MIT notices. The copied profiler's SPDX header
specifies Apache-2.0; its full license text is included alongside the source.
See [third-party notices](../THIRD_PARTY_NOTICES.md) for the license paths.

`cachetools==5.3.1` is a runtime dependency matching the selected upstream
lockfile. It is installed as a dependency, not claimed as copied project code.

## What this repository adds

Header-based level extraction, per-service parser isolation, shared baseline/
current passes within each service, comparison statuses, deterministic exports,
escaped report presentation, local browser filters and input/output handling are
app code. They are tested separately from the copied source cases. The parser
and the additions are not an incident diagnosis or anomaly-detection system.
