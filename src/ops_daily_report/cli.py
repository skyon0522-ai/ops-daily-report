"""Command-line entry point for offline daily log reports."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import webbrowser
from contextlib import ExitStack
from importlib.resources import files
from tempfile import TemporaryDirectory

from .report import build_report, render_markdown


def build_parser():
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Group local log messages into reviewable templates and counts.",
        epilog="Try: ops-daily-report demo | Your logs: ops-daily-report --log-dir PATH",
    )
    parser.add_argument(
        "command", nargs="?", choices=["demo"],
        help="Create a comparison report from packaged synthetic logs",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        help="Directory of current top-level UTF-8 .log files",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        help="Optional directory of baseline top-level UTF-8 .log files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Write report.json, report.md and report.html here; existing names are never overwritten",
    )
    parser.add_argument(
        "--open", dest="open_report", action="store_true",
        help="Open the saved HTML report in your default browser (requires --output-dir, or demo)",
    )
    return parser


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _write_bundle(output_dir: Path, report: dict) -> None:
    from .html_report import render_html

    documents = {
        "report.json": json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        "report.md": render_markdown(report),
        "report.html": render_html(report),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {name: output_dir / name for name in documents}
    existing = [str(path) for path in targets.values() if path.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing report file(s): " + ", ".join(existing)
        )

    created: list[Path] = []
    try:
        for name, content in documents.items():
            target = targets[name]
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            created.append(target)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
    except OSError:
        for target in created:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        raise


def _write_text(stream, text: str) -> None:
    encoding = stream.encoding or "utf-8"
    # Keep interactive output usable on legacy Windows code pages; UTF-8 files
    # remain the lossless export for any characters the console cannot display.
    safe_text = text.encode(encoding, errors="backslashreplace").decode(encoding)
    stream.write(safe_text)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "demo":
        if args.log_dir is not None or args.baseline_dir is not None:
            parser.error("demo uses packaged logs; omit --log-dir and --baseline-dir")
        args.output_dir = args.output_dir or Path("ops-daily-demo")
    elif args.log_dir is None:
        if args.baseline_dir is not None or args.output_dir is not None or args.open_report:
            parser.error("provide --log-dir PATH, or run ops-daily-report demo")
        parser.print_help()
        return 0
    if args.open_report and args.output_dir is None:
        parser.error("--open requires --output-dir")
    try:
        with ExitStack() as resources:
            if args.command == "demo":
                samples = files("ops_daily_report").joinpath("demo_logs")
                temporary = Path(resources.enter_context(TemporaryDirectory(prefix="ops-daily-demo-")))
                for batch in ("current", "baseline"):
                    directory = temporary / batch
                    directory.mkdir()
                    (directory / "system.log").write_bytes(samples.joinpath(f"{batch}/system.log").read_bytes())
                args.log_dir = temporary / "current"
                args.baseline_dir = temporary / "baseline"
            if args.output_dir is not None:
                output = args.output_dir.resolve()
                input_dirs = [args.log_dir.resolve()]
                if args.baseline_dir is not None:
                    input_dirs.append(args.baseline_dir.resolve())
                if any(_overlap(output, input_dir) for input_dir in input_dirs):
                    raise ValueError("--output-dir must be separate from the current and baseline log directories")

            report = build_report(args.log_dir, args.baseline_dir)
        if args.output_dir is None:
            _write_text(sys.stdout, render_markdown(report))
        else:
            _write_bundle(args.output_dir, report)
            _write_text(
                sys.stdout,
                f"Wrote report.json, report.md and report.html to {args.output_dir}\n"
                f"HTML report: {(args.output_dir / 'report.html').resolve()}\n",
            )
            if args.open_report:
                try:
                    opened = webbrowser.open((args.output_dir / "report.html").resolve().as_uri())
                except (webbrowser.Error, OSError) as exc:
                    _write_text(sys.stderr, f"warning: Browser could not open the report: {exc}\n")
                else:
                    if not opened:
                        _write_text(sys.stderr, "warning: Browser could not open the report; open the HTML path above.\n")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        _write_text(sys.stderr, f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
