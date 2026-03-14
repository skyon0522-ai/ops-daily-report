from pathlib import Path

from ops_daily_report.cli import main


def test_cli_prints_summary(monkeypatch, capsys, tmp_path: Path) -> None:
    (tmp_path / "app.log").write_text(
        "INFO Started\nWARNING Disk\nERROR Crash\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("sys.argv", ["ops-daily-report", "--log-dir", str(tmp_path)])

    rc = main()
    output = capsys.readouterr().out

    assert rc == 0
    assert "Ops Daily Report (scaffold)" in output
    assert "total_lines=3" in output
    assert "errors=1" in output
    assert "warnings=1" in output
    assert "infos=1" in output
