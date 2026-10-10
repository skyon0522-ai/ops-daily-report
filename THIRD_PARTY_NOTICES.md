# Third-party notices

This repository vendors a narrow subset of [Drain3](https://github.com/logpai/Drain3) at commit `0fb6d6e1828838fa05c8f6fa5cda878e02ea79c7` (version 0.9.11). `drain.py` and the copied upstream behavioral tests are MIT-licensed; their source attribution and license text are preserved in `src/ops_daily_report/_vendor/drain3/LICENSE.txt`. The copied `simple_profiler.py` carries an Apache-2.0 SPDX header; its license text is in `src/ops_daily_report/_vendor/drain3/LICENSE-APACHE-2.0.txt`.

The Drain algorithm source has one packaging-only adaptation: its profiler import is relative to this private vendored package. The upstream test file redirects its import and adds a terminal newline. Exact upstream and local file hashes are listed in [PROVENANCE.json](PROVENANCE.json).

The runtime dependency `cachetools==5.3.1` supports Drain3's in-memory LRU cache. The project does not include Drain3's `TemplateMiner`, persistence, broker adapters, or their additional dependencies.
