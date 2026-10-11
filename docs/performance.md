# Language choice and resource observations

Python remains the implementation language. The app executes the pinned Drain3
Python parser directly. A rewrite would need to preserve its template evolution,
service isolation and baseline-first ordering. No equivalent Rust port or
cross-language comparison was tested here. Instead, this revision removes an
observed input-retention cost in the report pipeline.

## Implementation change

The previous report retained raw input strings, parsed message objects and
service-specific message lists. The current report reads chunks, stores compact
message/severity pairs grouped by service, and accumulates input totals during
reading. It then runs one service miner at a time, with baseline messages before
current messages. It avoids retaining normalized record objects and duplicate
service strings per message. The
compatibility `load_log_lines()` helper still returns a materialized list;
the CLI's report path uses the iterator. Copied Drain3 algorithm and notices
are unchanged.

The reader preserves the former UTF-8 decoding errors and `splitlines()`
separator behavior, including long lines and chunk boundaries. The complete
suite passed 47 tests, including the eight copied-source cases. The fixed demo's
JSON, Markdown and HTML matched the committed outputs. Each measured input
produced the same canonical report SHA-256 before and after the change.

## Observations on 2026-10-11

Fixed synthetic logs use four services, three severity levels and repeating
message shapes. They are stress cases, not measured customer traffic. Each
case uses one excluded warm-up and five measured process runs. Elapsed time
includes interpreter startup and report construction; it excludes log
generation, file export, browser rendering and dependency installation.

| Current + baseline lines | Before median seconds | After median seconds | Before peak RSS median MiB | After peak RSS median MiB |
| --- | ---: | ---: | ---: | ---: |
| 1,000 + 500 | 0.503 | 0.425 | 21.3 | 21.1 |
| 50,000 + 25,000 | 0.896 | 0.840 | 46.3 | 31.7 |
| 200,000 + 100,000 | 2.182 | 2.121 | 123.7 | 64.7 |

The largest case reduced the measured peak RSS median by 47.7%.
An additional stress case used 20,000 distinct services, 20,000 current messages
and 10,000 baseline messages. Its peak RSS median changed from
65.6 to 67.3 MiB;
its elapsed median changed from 2.060
to 0.831 seconds. The output matched.
This case showed no memory improvement: observed RSS was about 2.6% higher.
It is separate from the four-service benchmark command below.
Timing observations do not establish a general speedup or a production SLA.
The machine used AMD Ryzen AI 7 350, WSL2 Ubuntu 24.04, CPython 3.12.3,
cachetools 5.3.1 and GNU time. Memory is GNU time's process high-water RSS,
not the sum of concurrent child processes. Files were read through the Windows
mount; cache state, host scheduling and other work can affect timings. System
caches were not cleared.

## Reproduce the current implementation

After installing the existing project dependencies, use Linux or WSL with
GNU time available:

```sh
python scripts/benchmark.py measure . current --sizes 1000,50000,200000
python scripts/benchmark.py measure . many-services --sizes 20000 --scenario many-services
```

The command writes synthetic inputs and repeated observations beneath
`benchmark-results/`. It measures the current checkout. To compare revisions,
run the same script with the previous checkout as its source and a distinct
label. The measured previous source was commit `6c0db912fe32f67198d6889835b2d1a2c20d2555`.
No cross-language speed ratio is claimed.

## Limits

Memory still grows with buffered messages, the number of services, clusters,
templates, output patterns and the largest individual line. This is not a
constant-memory guarantee for arbitrary logs. If both input directories contain
invalid files, the baseline is now read first, so the first reported input error
may differ. Either invalid input still fails. A rejected fully streaming variant
held all service miners at once and increased the high-cardinality case's RSS
to 99.5 MiB; it is not the implementation proposed here. The synthetic cases
do not establish grouping accuracy, maximum supported input size, sustained
ingestion capacity or production safety. Python interpreter and parser costs
remain; native acceleration would require a separate measured, behavior-matched
comparison if an actual workload makes those costs material.

The measurement procedure follows the repeated-run and warm-up pattern in
[Hyperfine](https://github.com/sharkdp/hyperfine). Resource selection follows
[the USE method](https://www.brendangregg.com/usemethod.html). These references
guide the investigation; they do not validate this app's results.
