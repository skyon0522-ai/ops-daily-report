# Architecture

The CLI is the only entry point. It reads the selected local batches, constructs
one report data object and renders it into three formats. Each service has its
own parser instance.

```text
current/*.log + optional baseline/*.log
                  |
          supported header parser
          level + service + message
                  |
          copied Drain3 parser core
          per service: baseline, then current
                  |
        final templates + batch counts
                  |
            report data object
          /        |        \
        JSON    Markdown    HTML
                          local filters
```

## Source and added behavior

| Component | Responsibility |
| --- | --- |
| [parser.py](../src/ops_daily_report/parser.py) | Read selected files and extract supported headers; count unsupported lines as UNKNOWN without retaining their raw text. |
| [_vendor/drain3](../src/ops_daily_report/_vendor/drain3/) | Copied fixed-depth template-mining algorithm and profiler. |
| [report.py](../src/ops_daily_report/report.py) | Keep service groups separate, compare batch counts, and render Markdown. |
| [html_report.py](../src/ops_daily_report/html_report.py) | Escape template text and produce a self-contained, searchable HTML report. |
| [cli.py](../src/ops_daily_report/cli.py) | Parse options, print the summary and save outputs without replacing existing report files. |

Each service uses a separate miner to preserve service isolation even when a
parser's prefix-tree child limit is reached. Within each service, baseline and
current messages share one pass and the final templates.

The low-level Drain3 core is executed directly. The full upstream TemplateMiner,
serialized state, jsonpickle, Redis and Kafka adapters are not included. Report
JSON is a data export, not executable parser state or a baseline import format.

## Boundaries

This is an offline batch tool. It has no live tailing, multiline stack-trace
assembly, incident diagnosis, remediation or alert routing. Unsupported lines
remain counted, but their extracted level/service can be unknown. Message order,
parser settings and the selected batches can affect inferred templates.

The parser's published research evaluation does not certify this report's
accuracy. See [research](research.md), [usage](usage.md) and the runnable tests.
