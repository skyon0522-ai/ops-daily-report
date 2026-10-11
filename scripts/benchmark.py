"""Repeat synthetic report measurements with GNU time on Linux or WSL."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def generate(size, scenario):
    target = ROOT / "benchmark-results/inputs" / str(size)
    for batch, count in (("current", size), ("baseline", size // 2)):
        directory = target / batch
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "synthetic.log"
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for i in range(count):
                if scenario == "many-services":
                    stream.write(
                        f"2026-10-10T12:00:00Z INFO service-{i}: Request completed\n"
                    )
                    continue
                level = ("INFO", "WARNING", "ERROR")[i % 3]
                stream.write(
                    f"2026-10-10T12:00:00Z {level} service-{i % 4}: "
                    f"request {i} completed operation-{i % 7}\n"
                )
    return target


def one(source, size):
    source = source.resolve()
    if not (source / "src/ops_daily_report/report.py").is_file():
        raise ValueError("Source must be an Ops Daily Report checkout")
    sys.path.insert(0, str(source / "src"))
    from ops_daily_report.report import build_report

    target = ROOT / "benchmark-results/inputs" / str(size)
    report = build_report(target / "current", target / "baseline")
    raw = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    print(json.dumps({
        "report_sha256": hashlib.sha256(raw).hexdigest(),
        "totals": report["totals"],
        "patterns": len(report["patterns"]),
    }))


def measure(source, label, sizes, scenario):
    source = source.resolve()
    destination = ROOT / "benchmark-results" / label
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    for size in sizes:
        generate(size, scenario)
        observations = []
        for index in range(6):
            metrics = destination / f"{size}-{index}.time.json"
            command = [
                "/usr/bin/time", "-f",
                '{"user_seconds":%U,"system_seconds":%S,"peak_rss_kib":%M}',
                "-o", str(metrics), sys.executable, "-B", str(Path(__file__)),
                "one", str(source), str(size),
            ]
            start = time.perf_counter()
            run = subprocess.run(
                command, capture_output=True, text=True, timeout=120,
                env=dict(os.environ, LC_ALL="C"),
            )
            elapsed = time.perf_counter() - start
            (destination / f"{size}-{index}.stderr").write_text(run.stderr)
            if run.returncode:
                raise RuntimeError(
                    f"measurement failed: size={size}, exit={run.returncode}; inspect stderr"
                )
            result = json.loads(run.stdout)
            sample = {
                "warmup": index == 0, "elapsed_seconds": elapsed,
                **json.loads(metrics.read_text()), **result,
            }
            observations.append(sample)
        assert len({sample["report_sha256"] for sample in observations}) == 1
        measured = observations[1:]
        records.append({
            "current_lines": size, "baseline_lines": size // 2,
            "command": command, "warmups": 1, "measured_runs": 5,
            "samples": observations,
            "summary": {
                "elapsed_median_seconds": statistics.median(s["elapsed_seconds"] for s in measured),
                "elapsed_min_seconds": min(s["elapsed_seconds"] for s in measured),
                "elapsed_max_seconds": max(s["elapsed_seconds"] for s in measured),
                "peak_rss_median_kib": statistics.median(s["peak_rss_kib"] for s in measured),
            },
        })
        receipt = {
            "label": label, "source": str(source), "runtime": sys.version,
            "scenario": scenario,
            "method": (
                "One excluded warm-up plus five process runs; parent elapsed includes "
                "Python startup. GNU time max RSS is a process high-water measure, "
                "not summed concurrent-tree memory. No cache clearing; synthetic inputs."
            ),
            "workloads": records,
        }
        (destination / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"label": label, "size": size, **records[-1]["summary"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("one", "measure"))
    parser.add_argument("source", type=Path)
    parser.add_argument("label")
    parser.add_argument("--sizes", default="1000,50000,200000")
    parser.add_argument("--scenario", choices=("few-services", "many-services"), default="few-services")
    args = parser.parse_args()
    if args.action == "one":
        one(args.source, int(args.label))
    else:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", args.label):
            parser.error("label must contain only letters, numbers, underscores or hyphens")
        if not Path("/usr/bin/time").is_file():
            parser.error("measurement requires GNU time on Linux or WSL")
        sizes = [int(n) for n in args.sizes.split(",")]
        if not sizes or any(size < 1 for size in sizes) or len(set(sizes)) != len(sizes):
            parser.error("sizes must be distinct positive integers")
        measure(args.source, args.label, sizes, args.scenario)
