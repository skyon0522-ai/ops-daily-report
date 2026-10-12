import json
import sys
import webbrowser
from pathlib import Path

import pytest

from ops_daily_report.cli import _write_text, main


def test_no_arguments_offer_demo_and_own_data_without_creating_files(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ops-daily-report"])

    assert main() == 0

    output = capsys.readouterr()
    assert "ops-daily-report demo" in output.out
    assert "--log-dir PATH" in output.out
    assert output.err == ""
    assert not list(tmp_path.iterdir())


def test_demo_uses_packaged_comparison_outside_checkout(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ops-daily-report", "demo"])
    monkeypatch.setattr(webbrowser, "open", lambda *_: pytest.fail("Browser must be opt-in"))

    assert main() == 0

    report = json.loads((tmp_path / "ops-daily-demo/report.json").read_text(encoding="utf-8"))
    assert report["totals"]["current"]["lines"] == 6
    assert report["totals"]["baseline"]["lines"] == 4
    assert report["inputs"]["current_files"] == report["inputs"]["baseline_files"] == 1
    assert {pattern["status"] for pattern in report["patterns"]} == {"new", "recurring", "absent"}
    assert "HTML report:" in capsys.readouterr().out


def test_demo_repeat_refuses_replacement_and_keeps_every_file(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["ops-daily-report", "demo"])
    assert main() == 0
    output_dir = tmp_path / "ops-daily-demo"
    before = {path.name: path.read_bytes() for path in output_dir.iterdir()}

    assert main() == 2

    assert "Refusing to overwrite" in capsys.readouterr().err
    assert {path.name: path.read_bytes() for path in output_dir.iterdir()} == before


def test_demo_can_use_an_explicit_output_and_open_the_saved_report(monkeypatch, tmp_path):
    output_dir = tmp_path / "demo with spaces"
    monkeypatch.setattr(sys, "argv", ["ops-daily-report", "demo", "--output-dir", str(output_dir), "--open"])
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda uri: opened.append(uri) or True)

    assert main() == 0

    assert opened == [(output_dir / "report.html").resolve().as_uri()]
    assert (output_dir / "report.html").is_file()


@pytest.mark.parametrize("failure", [False, webbrowser.Error("no browser"), OSError("launch failed")])
def test_browser_failure_keeps_successful_reports(monkeypatch, capsys, tmp_path, failure):
    output_dir = tmp_path / "report"
    monkeypatch.setattr(sys, "argv", ["ops-daily-report", "demo", "--output-dir", str(output_dir), "--open"])

    def open_browser(uri):
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(webbrowser, "open", open_browser)

    assert main() == 0

    assert "warning: Browser could not open the report" in capsys.readouterr().err
    assert {path.name for path in output_dir.iterdir()} == {"report.json", "report.md", "report.html"}


@pytest.mark.parametrize("arguments", [
    ["demo", "--log-dir", "logs"],
    ["demo", "--baseline-dir", "logs"],
    ["--output-dir", "report"],
    ["--log-dir", "logs", "--open"],
])
def test_incomplete_or_conflicting_commands_show_actionable_errors(monkeypatch, capsys, arguments):
    monkeypatch.setattr(sys, "argv", ["ops-daily-report", *arguments])

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    assert "error:" in capsys.readouterr().err


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
