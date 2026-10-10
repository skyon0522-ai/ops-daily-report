"""Command-line entry point for offline daily log reports."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from .report import build_report, render_markdown


def build_parser():
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Group local log messages into reviewable templates and counts."
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("sample_logs"),
        help="Directory of current top-level UTF-8 .log files (default: sample_logs)",
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
    args = build_parser().parse_args()
    try:
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
                f"Wrote report.json, report.md and report.html to {args.output_dir}\n",
            )
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        _write_text(sys.stderr, f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
