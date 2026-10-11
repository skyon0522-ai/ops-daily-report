from __future__ import annotations

import json
from pathlib import Path

import pytest

import ops_daily_report.report as report_module
from ops_daily_report.report import build_report, render_markdown


def _write(directory: Path, name: str, content: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(content, encoding="utf-8")


def test_shared_final_template_comparison_reports_new_recurring_and_absent(tmp_path: Path):
    baseline = tmp_path / "baseline"
    current = tmp_path / "current"
    _write(
        baseline,
        "system.log",
        "Mar 14 00:01:11 host app[1]: ERROR Health check failed for shard 3 after 120 ms\n"
        "Mar 14 00:01:12 host app[1]: WARNING Queue depth 18 on pool blue\n"
        "Mar 14 00:01:13 host app[1]: INFO Started serving requests\n"
        "Mar 14 00:01:14 host app[1]: ERROR Disk pressure on node 5\n",
    )
    _write(
        current,
        "system.log",
        "2026-10-10T00:01:11Z ERROR app: Health check failed for shard 4 after 135 ms\n"
        "Mar 14 00:01:12 host app[1]: ERROR Health check failed for shard 4 after 141 ms\n"
        "2026-10-10T00:01:13Z WARNING app: Queue depth 24 on pool blue\n"
        "2026-10-10T00:01:14Z INFO app: Started serving requests\n"
        "2026-10-10T00:01:15Z ERROR database: Connection timeout on node 2\n"
        "unstructured line with ERROR mentioned later\n",
    )
    source_before = (current / "system.log").read_bytes()

    report = build_report(current, baseline)
    by_text = {item["template"]: item for item in report["patterns"]}

    assert report["totals"]["current"] == {
        "lines": 6,
        "levels": {"ERROR": 3, "WARNING": 1, "INFO": 1, "DEBUG": 0, "CRITICAL": 0, "UNKNOWN": 1},
    }
    assert report["totals"]["baseline"]["lines"] == 4
    assert by_text["Health check failed for shard <*> after <*> ms"]["status"] == "recurring"
    assert by_text["Health check failed for shard <*> after <*> ms"]["current_count"] == 2
    assert by_text["Health check failed for shard <*> after <*> ms"]["baseline_count"] == 1
    assert by_text["Connection timeout on node 2"]["status"] == "new"
    assert by_text["Disk pressure on node 5"]["status"] == "absent"
    assert "Unsupported log line" in by_text
    assert report["inputs"]["current_unparsed_lines"] == 1
    assert report["inputs"]["warnings"]
    assert (current / "system.log").read_bytes() == source_before
    assert "new means" in render_markdown(report).lower()


def test_report_without_baseline_is_explicitly_uncompared(tmp_path: Path):
    current = tmp_path / "current"
    _write(current, "app.log", "INFO api: Started\n")

    report = build_report(current)

    assert report["totals"]["baseline"] is None
    assert report["inputs"]["baseline_files"] is None
    assert report["patterns"][0]["status"] == "uncompared"
    assert report["patterns"][0]["baseline_count"] is None
    assert report["patterns"][0]["delta"] is None


def test_empty_directory_is_valid_but_no_log_files_are_reported(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()

    report = build_report(empty)

    assert report["totals"]["current"]["lines"] == 0
    assert report["inputs"]["current_files"] == 0
    assert report["inputs"]["warnings"] == [
        "Current input contains no .log files; zero messages were analyzed."
    ]
    assert report["patterns"] == []
    assert "No messages in the selected inputs" in render_markdown(report)


def test_missing_input_directory_fails_instead_of_claiming_zero(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_report(tmp_path / "missing")


def test_pattern_ids_and_order_are_repeatable(tmp_path: Path):
    current = tmp_path / "current"
    _write(
        current,
        "app.log",
        "ERROR api: failed to open item 31\nWARNING api: queue at 10\nERROR api: failed to open item 43\n",
    )

    first = build_report(current)
    second = build_report(current)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert all(len(pattern["id"]) == 64 for pattern in first["patterns"])
    assert first["patterns"][0]["levels"]["ERROR"] > 0


def test_markdown_escapes_untrusted_pattern_markup_and_table_pipes(tmp_path: Path):
    current = tmp_path / "current"
    _write(current, "app.log", "INFO api: <img src=x>|**untrusted**\n")

    output = render_markdown(build_report(current))

    assert "&lt;img src=x>\\|\\*\\*untrusted\\*\\*" in output
    assert "| INFO api |" not in output


def test_services_remain_separate_even_when_each_drain_tree_has_one_child_slot(
    monkeypatch, tmp_path: Path
):
    current = tmp_path / "current"
    _write(
        current,
        "app.log",
        "INFO alpha: Same operation completed\nINFO beta: Same operation completed\n",
    )
    monkeypatch.setattr(
        report_module,
        "DRAIN_SETTINGS",
        {"depth": 4, "sim_th": 0.4, "max_children": 1},
    )

    report = build_report(current)

    assert {(item["service"], item["template"]) for item in report["patterns"]} == {
        ("alpha", "Same operation completed"),
        ("beta", "Same operation completed"),
    }
    assert report["engine"]["settings"]["miner_scope"] == "per_service"


def test_report_does_not_materialize_files_with_read_text(monkeypatch, tmp_path: Path):
    current = tmp_path / "current"
    baseline = tmp_path / "baseline"
    _write(current, "app.log", "INFO alpha: Completed item 42\nINFO beta: Started\n")
    _write(baseline, "app.log", "INFO alpha: Completed item 31\n")

    def reject_full_read(*args, **kwargs):
        raise AssertionError("The report must iterate input files")

    monkeypatch.setattr(Path, "read_text", reject_full_read)
    report = build_report(current, baseline)

    assert report["totals"]["current"]["lines"] == 2
    assert report["totals"]["baseline"]["lines"] == 1
    assert len(report["patterns"]) == 2
