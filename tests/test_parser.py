from pathlib import Path

from ops_daily_report.parser import load_logs_from_dir, summarize_log_lines


def test_summarize_log_lines_counts_keywords() -> None:
    lines = [
        "INFO boot complete",
        "warning disk getting full",
        "ERROR cannot open file",
        "random line",
    ]

    summary = summarize_log_lines(lines)

    assert summary == {
        "total_lines": 4,
        "ERROR": 1,
        "WARNING": 1,
        "INFO": 1,
    }


def test_load_logs_from_dir_reads_log_files(tmp_path: Path) -> None:
    (tmp_path / "a.log").write_text("INFO one\n", encoding="utf-8")
    (tmp_path / "b.log").write_text("ERROR two\n", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("WARNING three\n", encoding="utf-8")

    lines = load_logs_from_dir(tmp_path)

    assert lines == ["INFO one", "ERROR two"]
