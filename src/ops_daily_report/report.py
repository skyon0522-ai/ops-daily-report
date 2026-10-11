"""Offline template reports with an optional, explicitly selected baseline."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path

from ._vendor.drain3 import Drain
from .parser import LEVELS, parse_log_line, scan_log_lines


DRAIN3_COMMIT = "0fb6d6e1828838fa05c8f6fa5cda878e02ea79c7"
DRAIN_SETTINGS = {"depth": 4, "sim_th": 0.4, "max_children": 1000}


def build_report(log_dir: Path, baseline_dir: Path | None = None) -> dict:
    """Build a deterministic report from local logs without changing the inputs."""

    by_pattern: dict[tuple[str, str], dict] = {}
    service_batches: dict[str, dict[str, list[tuple[str, str]]]] = {}
    snapshots = {}
    warnings = []
    # Each service has its own miner so Drain's max_children fallback cannot
    # merge patterns from different services. Within each miner, baseline is
    # always processed before current and final templates apply to both.
    for batch_name, directory in (("baseline", baseline_dir), ("current", log_dir)):
        if directory is None:
            continue
        lines, file_count = scan_log_lines(Path(directory))
        counts: Counter[str] = Counter()
        line_count = unparsed = 0
        for _, line in lines:
            item = parse_log_line(line)
            line_count += 1
            counts[item.severity] += 1
            unparsed += not item.recognized_header
            service = item.service or "unknown"
            service_batches.setdefault(service, {"baseline": [], "current": []})[
                batch_name
            ].append((item.message, item.severity))
        snapshots[batch_name] = {
            "files": file_count, "unparsed": unparsed,
            "totals": {"lines": line_count, "levels": {level: counts[level] for level in LEVELS}},
        }
        if file_count == 0:
            warnings.append(f"{batch_name.capitalize()} input contains no .log files; zero messages were analyzed.")
        if unparsed:
            warnings.append(
                f"{unparsed} line(s) in {batch_name} input did not match a supported header; "
                "they are grouped as UNKNOWN without retaining the raw text."
            )

    for service in sorted(service_batches):
        miner = Drain(**DRAIN_SETTINGS)
        clusters: dict[int, dict] = {}
        for batch_name in ("baseline", "current"):
            for message, severity in service_batches[service][batch_name]:
                cluster, _change = miner.add_log_message(message)
                record = clusters.get(cluster.cluster_id)
                if record is None:
                    record = {"baseline_count": 0, "current_count": 0, "levels": Counter()}
                    clusters[cluster.cluster_id] = record
                record[f"{batch_name}_count"] += 1
                if batch_name == "current":
                    record["levels"][severity] += 1
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
        baseline_count = record["baseline_count"] if baseline_dir is not None else None
        if baseline_dir is None:
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
            "current_files": snapshots["current"]["files"],
            "baseline_files": snapshots["baseline"]["files"] if baseline_dir is not None else None,
            "current_unparsed_lines": snapshots["current"]["unparsed"],
            "baseline_unparsed_lines": snapshots["baseline"]["unparsed"] if baseline_dir is not None else None,
            "warnings": warnings,
        },
        "totals": {
            "current": snapshots["current"]["totals"],
            "baseline": snapshots["baseline"]["totals"] if baseline_dir is not None else None,
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
