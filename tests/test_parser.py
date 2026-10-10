from pathlib import Path

import pytest

from ops_daily_report.parser import (
    LEVELS,
    load_log_lines,
    load_logs_from_dir,
    parse_log_line,
    summarize_log_lines,
)


def test_rfc3164_header_extracts_service_and_severity():
    item = parse_log_line("Mar 14 00:01:11 host app[123]: WARNING High memory usage")

    assert (item.service, item.severity, item.message, item.recognized_header) == (
        "app",
        "WARNING",
        "High memory usage",
        True,
    )


def test_iso_header_and_simple_level_header_are_supported():
    iso = parse_log_line("2026-10-10T00:01:11Z ERROR api: Health check failed")
    simple = parse_log_line("WARN Queue depth is high")

    assert (iso.service, iso.severity, iso.message) == ("api", "ERROR", "Health check failed")
    assert (simple.service, simple.severity, simple.message) == ("unknown", "WARNING", "Queue depth is high")


def test_message_words_do_not_set_severity_and_unsupported_text_is_discarded():
    info = parse_log_line("INFO worker: completed after ERROR recovery")
    unsupported = parse_log_line("unstructured ERROR-like text")

    assert info.severity == "INFO"
    assert unsupported.severity == "UNKNOWN"
    assert unsupported.recognized_header is False
    assert unsupported.message == "Unsupported log line"


def test_summarize_counts_every_line_and_all_explicit_levels():
    summary = summarize_log_lines(
        ["INFO ready", "WARN backlog", "CRITICAL failed", "random ERROR text"]
    )

    assert summary == {
        "total_lines": 4,
        "ERROR": 0,
        "WARNING": 1,
        "INFO": 1,
        "DEBUG": 0,
        "CRITICAL": 1,
        "UNKNOWN": 1,
    }
    assert len(LEVELS) == 6


def test_load_is_top_level_case_insensitive_and_deterministic(tmp_path: Path):
    (tmp_path / "b.LOG").write_text("ERROR second\n", encoding="utf-8")
    (tmp_path / "a.log").write_text("INFO first\n", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("INFO ignored\n", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "nested.log").write_text("INFO nested\n", encoding="utf-8")

    records, files = load_log_lines(tmp_path)

    assert files == 2
    assert [name for name, _ in records] == ["a.log", "b.LOG"]
    assert load_logs_from_dir(tmp_path) == ["INFO first", "ERROR second"]


def test_missing_and_non_directory_inputs_are_reported(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_log_lines(tmp_path / "missing")
    file_path = tmp_path / "file.log"
    file_path.write_text("INFO ready\n", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        load_log_lines(file_path)
