"""Offline template reports with an optional, explicitly selected baseline."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path

from ._vendor.drain3 import Drain
from .parser import LEVELS, ParsedLogLine, load_log_lines, parse_log_line


DRAIN3_COMMIT = "0fb6d6e1828838fa05c8f6fa5cda878e02ea79c7"
DRAIN_SETTINGS = {"depth": 4, "sim_th": 0.4, "max_children": 1000}


def _read_snapshot(directory: Path, label: str) -> tuple[list[ParsedLogLine], int, int, list[str]]:
    raw_records, file_count = load_log_lines(directory)
    parsed = [parse_log_line(line) for _, line in raw_records]
    unparsed = sum(not item.recognized_header for item in parsed)
    warnings = []
    if file_count == 0:
        warnings.append(f"{label.capitalize()} input contains no .log files; zero messages were analyzed.")
    if unparsed:
        warnings.append(
            f"{unparsed} line(s) in {label} input did not match a supported header; "
            "they are grouped as UNKNOWN without retaining the raw text."
        )
    return parsed, file_count, unparsed, warnings


def _totals(records: list[ParsedLogLine]) -> dict:
    counts = Counter(item.severity for item in records)
    return {"lines": len(records), "levels": {level: counts[level] for level in LEVELS}}


def build_report(log_dir: Path, baseline_dir: Path | None = None) -> dict:
    """Build a deterministic report from local logs without changing the inputs."""

    current, current_files, current_unparsed, warnings = _read_snapshot(Path(log_dir), "current")
    baseline = None
    baseline_files = None
    baseline_unparsed = None
    if baseline_dir is not None:
        baseline_records, baseline_files, baseline_unparsed, baseline_warnings = _read_snapshot(
            Path(baseline_dir), "baseline"
        )
        baseline = baseline_records
        warnings = baseline_warnings + warnings
    else:
        baseline_records = []

    by_pattern: dict[tuple[str, str], dict] = {}
    service_batches: dict[str, dict[str, list[ParsedLogLine]]] = {}
    for batch_name, batch in (("baseline", baseline_records), ("current", current)):
        for item in batch:
            service_batches.setdefault(item.service or "unknown", {"baseline": [], "current": []})[
                batch_name
            ].append(item)

    # Each service has its own miner so Drain's max_children fallback cannot
    # merge patterns from different services. Within each miner, baseline is
    # always processed before current and final templates apply to both.
    for service in sorted(service_batches):
        miner = Drain(**DRAIN_SETTINGS)
        clusters: dict[int, dict] = {}
        for batch_name in ("baseline", "current"):
            for item in service_batches[service][batch_name]:
                cluster, _change = miner.add_log_message(item.message)
                record = clusters.setdefault(
                    cluster.cluster_id,
                    {"baseline_count": 0, "current_count": 0, "levels": Counter()},
                )
                record[f"{batch_name}_count"] += 1
                if batch_name == "current":
                    record["levels"][item.severity] += 1

        for cluster_id, record in clusters.items():
            template = miner.id_to_cluster[cluster_id].get_template() or "(empty message)"
            key = (service, template)
            pattern = by_pattern.setdefault(
                key,
                {
                    "service": service,
                    "template": template,
                    "baseline_count": 0,
                    "current_count": 0,
                    "levels": Counter(),
                },
            )
            pattern["baseline_count"] += record["baseline_count"]
            pattern["current_count"] += record["current_count"]
            pattern["levels"].update(record["levels"])

    patterns = []
    for (service, template), record in by_pattern.items():
        current_count = record["current_count"]
        baseline_count = record["baseline_count"] if baseline is not None else None
        if baseline is None:
            status = "uncompared"
            delta = None
        elif current_count == 0:
            status = "absent"
            delta = -baseline_count
        elif baseline_count == 0:
            status = "new"
            delta = current_count
        else:
            status = "recurring"
            delta = current_count - baseline_count
        pattern_id = sha256(f"{service}\0{template}".encode("utf-8")).hexdigest()
        patterns.append(
            {
                "id": pattern_id,
                "service": service,
                "template": template,
                "current_count": current_count,
                "baseline_count": baseline_count,
                "delta": delta,
                "status": status,
                "levels": {level: record["levels"][level] for level in LEVELS},
            }
        )

    def order(pattern: dict) -> tuple:
        levels = pattern["levels"]
        severity = 0 if levels["ERROR"] or levels["CRITICAL"] else 1 if levels["WARNING"] else 2
        status = {"new": 0, "recurring": 1, "uncompared": 2, "absent": 3}[pattern["status"]]
        return severity, status, -pattern["current_count"], pattern["service"], pattern["template"]

    patterns.sort(key=order)
    return {
        "schema_version": 1,
        "engine": {
            "name": "Drain3",
            "commit": DRAIN3_COMMIT,
            "settings": {
                **DRAIN_SETTINGS,
                "miner_scope": "per_service",
                "shared_pass_order": "baseline_then_current",
            },
        },
        "inputs": {
            "current_files": current_files,
            "baseline_files": baseline_files,
            "current_unparsed_lines": current_unparsed,
            "baseline_unparsed_lines": baseline_unparsed,
            "warnings": warnings,
        },
        "totals": {
            "current": _totals(current),
            "baseline": _totals(baseline) if baseline is not None else None,
        },
        "patterns": patterns,
    }


def render_markdown(report: dict) -> str:
    """Render a readable plain-text report; templates can still contain secrets."""

    current = report["totals"]["current"]
    baseline = report["totals"]["baseline"]
    levels = current["levels"]
    lines = [
        "# Ops Daily Report",
        "",
        f"Current: {current['lines']:,} messages across {report['inputs']['current_files']} log file(s).",
        f"Error / critical: {levels['ERROR'] + levels['CRITICAL']:,}; warning: {levels['WARNING']:,}; "
        f"unknown level: {levels['UNKNOWN']:,}.",
    ]
    if baseline is None:
        lines.extend(["", "Baseline: none selected. Pattern statuses are marked **uncompared**."])
    else:
        lines.extend(
            [
                "",
                f"Baseline: {baseline['lines']:,} messages across {report['inputs']['baseline_files']} log file(s).",
                "New means absent from this selected baseline snapshot; it does not mean anomalous.",
            ]
        )
    if report["inputs"]["warnings"]:
        lines.extend(["", "## Input notes", ""])
        lines.extend(f"- {warning}" for warning in report["inputs"]["warnings"])
    lines.extend(
        [
            "",
            "## Message patterns",
            "",
            "| Status | Service | Message template | Current | Baseline | Change | Current levels |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )

    def cell(value: object) -> str:
        text = str(value).replace("\\", "\\\\")
        for character in "`*_{}[]()#+-.!|":
            text = text.replace(character, "\\" + character)
        return text.replace("&", "&amp;").replace("<", "&lt;")

    if report["patterns"]:
        for pattern in report["patterns"]:
            prior = "-" if pattern["baseline_count"] is None else f"{pattern['baseline_count']:,}"
            delta = "-" if pattern["delta"] is None else f"{pattern['delta']:+,}"
            current_levels = ", ".join(
                f"{level} {count}"
                for level, count in pattern["levels"].items()
                if count
            ) or "-"
            cells = [pattern["status"], pattern["service"], pattern["template"],
                     f"{pattern['current_count']:,}", prior, delta, current_levels]
            safe_cells = [cell(value.replace("\r", " ").replace("\n", " ")) if isinstance(value, str) else cell(value) for value in cells]
            lines.append("| " + " | ".join(safe_cells) + " |")
    else:
        lines.append("| - | - | No messages in the selected inputs. | 0 | - | - | - |")
    lines.extend(
        [
            "",
            "## Method and sharing",
            "",
            "Drain3 groups similar message text into templates. Baseline messages are processed first, then current messages; final templates are used for both counts.",
            f"Settings: `{report['engine']['settings']}`.",
            "Severity comes from supported log headers. Unsupported lines are counted as UNKNOWN without retaining their raw text.",
            "Template grouping does not diagnose incidents or prove that a new pattern is anomalous. Review templates in all report formats for sensitive text before sharing. No raw log excerpts are intentionally included.",
            "",
        ]
    )
    return "\n".join(lines)
