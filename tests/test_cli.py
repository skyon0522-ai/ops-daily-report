import json
import sys
from pathlib import Path

from ops_daily_report.cli import _write_text, main


def test_cli_prints_readable_markdown_by_default(monkeypatch, capsys, tmp_path: Path):
    (tmp_path / "app.log").write_text(
        "INFO api: Started\nWARNING api: Disk pressure\nERROR api: Crash\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["ops-daily-report", "--log-dir", str(tmp_path)])

    rc = main()
    output = capsys.readouterr()

    assert rc == 0
    assert "# Ops Daily Report" in output.out
    assert "3 messages across 1 log file" in output.out
    assert "ERROR 1" in output.out
    assert "Baseline: none selected" in output.out
    assert output.err == ""


def test_cli_writes_json_markdown_and_html_to_separate_directory(monkeypatch, capsys, tmp_path: Path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "app.log").write_text("INFO api: Started\n", encoding="utf-8")
    output_dir = tmp_path / "reports"
    monkeypatch.setattr(
        "sys.argv",
        ["ops-daily-report", "--log-dir", str(logs), "--output-dir", str(output_dir)],
    )

    assert main() == 0
    assert "Wrote report.json, report.md and report.html" in capsys.readouterr().out
    assert {path.name for path in output_dir.iterdir()} == {"report.json", "report.md", "report.html"}
    assert json.loads((output_dir / "report.json").read_text(encoding="utf-8"))["totals"]["current"]["lines"] == 1
    assert "# Ops Daily Report" in (output_dir / "report.md").read_text(encoding="utf-8")
    assert "<title>Ops Daily Report</title>" in (output_dir / "report.html").read_text(encoding="utf-8")


def test_cli_refuses_to_overwrite_any_existing_report(monkeypatch, capsys, tmp_path: Path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "app.log").write_text("INFO api: Started\n", encoding="utf-8")
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    existing = output_dir / "report.json"
    existing.write_text("keep this\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["ops-daily-report", "--log-dir", str(logs), "--output-dir", str(output_dir)],
    )

    assert main() == 2
    output = capsys.readouterr()
    assert "Refusing to overwrite" in output.err
    assert existing.read_text(encoding="utf-8") == "keep this\n"
    assert {path.name for path in output_dir.iterdir()} == {"report.json"}


def test_cli_rejects_output_inside_input(monkeypatch, capsys, tmp_path: Path):
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "app.log").write_text("INFO api: Started\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["ops-daily-report", "--log-dir", str(logs), "--output-dir", str(logs / "reports")],
    )

    assert main() == 2
    assert "must be separate" in capsys.readouterr().err


def test_console_output_escapes_characters_unavailable_in_windows_code_page(monkeypatch):
    class LegacyConsole:
        encoding = "cp932"

        def __init__(self):
            self.value = ""

        def write(self, text):
            self.value += text

    console = LegacyConsole()
    monkeypatch.setattr(sys, "stdout", console)

    _write_text(console, "log message 🙃")

    assert console.value == r"log message \U0001f643"


def test_cli_success_path_is_safe_for_legacy_console_encoding(monkeypatch, tmp_path: Path):
    class LegacyConsole:
        encoding = "cp932"

        def __init__(self):
            self.value = ""

        def write(self, text):
            self.value += text

    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "app.log").write_text("INFO api: Started\n", encoding="utf-8")
    output_dir = tmp_path / "reports-🙃"
    console = LegacyConsole()
    monkeypatch.setattr("sys.stdout", console)
    monkeypatch.setattr(
        "sys.argv",
        ["ops-daily-report", "--log-dir", str(logs), "--output-dir", str(output_dir)],
    )

    assert main() == 0

    assert r"reports-\U0001f643" in console.value
    assert (output_dir / "report.json").is_file()
