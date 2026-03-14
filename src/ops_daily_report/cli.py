"""CLI entry point for ops-daily-report."""

from argparse import ArgumentParser
from pathlib import Path

from .parser import load_logs_from_dir, summarize_log_lines


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Summarize Linux log files")
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("sample_logs"),
        help="Directory containing .log files (default: sample_logs)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    lines = load_logs_from_dir(args.log_dir)
    summary = summarize_log_lines(lines)

    print("Ops Daily Report (scaffold)")
    print(f"total_lines={summary['total_lines']}")
    print(f"errors={summary['ERROR']}")
    print(f"warnings={summary['WARNING']}")
    print(f"infos={summary['INFO']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
