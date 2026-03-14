"""Basic log parsing helpers for Linux-style text logs."""

from collections import Counter
from pathlib import Path


LEVEL_KEYWORDS = {
    "error": "ERROR",
    "warn": "WARNING",
    "warning": "WARNING",
    "info": "INFO",
}


def summarize_log_lines(lines: list[str]) -> dict[str, int]:
    """Count common log level keywords in a list of log lines."""
    counts: Counter[str] = Counter()
    for line in lines:
        lowered = line.lower()
        for keyword, label in LEVEL_KEYWORDS.items():
            if keyword in lowered:
                counts[label] += 1
                break
    return {
        "total_lines": len(lines),
        "ERROR": counts["ERROR"],
        "WARNING": counts["WARNING"],
        "INFO": counts["INFO"],
    }


def load_logs_from_dir(log_dir: Path) -> list[str]:
    """Load all *.log files from a directory and return normalized lines."""
    lines: list[str] = []
    for path in sorted(log_dir.glob("*.log")):
        lines.extend(path.read_text(encoding="utf-8").splitlines())
    return lines
