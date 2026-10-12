"""Verify package contents and the normal installed CLI, without the checkout."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import venv
import zipfile


PACKAGE_FILES = (
    "ops_daily_report/demo_logs/current/system.log",
    "ops_daily_report/demo_logs/baseline/system.log",
    "ops_daily_report/_vendor/drain3/LICENSE.txt",
    "ops_daily_report/_vendor/drain3/LICENSE-APACHE-2.0.txt",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--sdist", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    wheel = args.wheel.resolve()
    with zipfile.ZipFile(wheel) as archive:
        for name in PACKAGE_FILES:
            assert archive.read(name) == (root / "src" / name).read_bytes(), name
        notices = [name for name in archive.namelist() if ".dist-info/" in name and name.endswith("/LICENSE")]
        assert notices and archive.read(notices[0]) == (root / "LICENSE").read_bytes(), "App MIT license missing"
    if args.sdist:
        with tarfile.open(args.sdist.resolve()) as archive:
            members = {member.name.split("/", 1)[-1]: member for member in archive.getmembers()}
            for name in (*[f"src/{name}" for name in PACKAGE_FILES], "LICENSE", "PROVENANCE.json"):
                assert archive.extractfile(members[name]).read() == (root / name).read_bytes(), name
    print("Distribution contents: sample logs, copied license notices and app license verified.")

    with tempfile.TemporaryDirectory(prefix="ops-daily-installed-") as temporary:
        work = Path(temporary)
        environment = work / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        executable_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        python = executable_dir / ("python.exe" if os.name == "nt" else "python")
        cli = executable_dir / ("ops-daily-report.exe" if os.name == "nt" else "ops-daily-report")

        def run(arguments, expected=0):
            result = subprocess.run([str(argument) for argument in arguments], cwd=work,
                                    capture_output=True, text=True, encoding="utf-8",
                                    env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            assert result.returncode == expected, result.stdout + result.stderr
            return result

        run([python, "-m", "pip", "install", wheel])
        installed = run([python, "-c", "import ops_daily_report; print(ops_daily_report.__file__)"])
        assert "site-packages" in installed.stdout, installed.stdout
        before = set(work.iterdir())
        guidance = run([cli])
        assert "ops-daily-report demo" in guidance.stdout
        assert set(work.iterdir()) == before
        run([cli, "demo"])
        output = work / "ops-daily-demo"
        report = json.loads((output / "report.json").read_text(encoding="utf-8"))
        assert report["totals"]["current"]["lines"] == 6
        assert report["totals"]["baseline"]["lines"] == 4
        assert report["inputs"]["current_files"] == report["inputs"]["baseline_files"] == 1
        assert {path.name for path in output.iterdir()} == {"report.html", "report.json", "report.md"}
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir()}
        repeated = run([cli, "demo"], expected=2)
        assert "Refusing to overwrite" in repeated.stderr
        assert hashes == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir()}
        run([cli, "demo", "--output-dir", "another-demo"])
        logs = work / "my logs"
        logs.mkdir()
        (logs / "service.log").write_text("INFO api: Started\nERROR api: Failed\n", encoding="utf-8")
        run([cli, "--log-dir", logs, "--output-dir", "own-report"])
        own = json.loads((work / "own-report/report.json").read_text(encoding="utf-8"))
        assert own["totals"]["current"]["lines"] == 2 and own["totals"]["baseline"] is None
        assert own["totals"]["current"]["levels"]["ERROR"] == 1
        summary = run([cli, "--log-dir", logs])
        assert "2 messages across 1 log file" in summary.stdout
        print(f"Installed CLI: {installed.stdout.strip()}")
        print("Fresh-venv smoke: no-args help, packaged comparison, repeat refusal, explicit output and own logs passed.")


if __name__ == "__main__":
    main()
