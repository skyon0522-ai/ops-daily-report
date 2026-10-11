"""Parse the small set of documented log headers without guessing severity."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
import re


LEVELS = ("ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL", "UNKNOWN")
_LEVEL_ALIASES = {
    "ERROR": "ERROR",
    "ERR": "ERROR",
    "WARNING": "WARNING",
    "WARN": "WARNING",
    "INFO": "INFO",
    "DEBUG": "DEBUG",
    "CRITICAL": "CRITICAL",
    "FATAL": "CRITICAL",
}
_KNOWN_LEVEL_TOKENS = set(_LEVEL_ALIASES) | {
    "ALERT", "EMERG", "EMERGENCY", "NOTICE", "PANIC", "SEVERE", "TRACE"
}
_LEVEL_PREFIX = re.compile(
    r"^\[?(?P<level>[A-Za-z]+)\]?(?:(?:\s*:\s*)|(?:\s+))(?P<rest>.*)$"
)
_RFC3164 = re.compile(
    r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+"
    r"\d{2}:\d{2}:\d{2}\s+\S+\s+"
    r"(?P<service>[A-Za-z0-9_.:/-]+)(?:\[\d+\])?:\s*(?P<body>.*)$"
)
_ISO8601 = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s+(?P<body>.*)$"
)
_SERVICE_MESSAGE = re.compile(r"^(?P<service>[A-Za-z0-9_.:/-]+):\s*(?P<message>.*)$")


@dataclass(frozen=True)
class ParsedLogLine:
    """A normalized record; unsupported raw text is intentionally discarded."""

    service: str
    severity: str
    message: str
    recognized_header: bool


def _severity_and_message(body: str) -> tuple[str, str, bool]:
    match = _LEVEL_PREFIX.match(body)
    if match is None or match.group("level").upper() not in _KNOWN_LEVEL_TOKENS:
        return "UNKNOWN", body.strip(), False
    severity = _LEVEL_ALIASES.get(match.group("level").upper(), "UNKNOWN")
    return severity, match.group("rest").strip(), True


def _service_and_message(rest: str) -> tuple[str, str]:
    match = _SERVICE_MESSAGE.match(rest)
    if match is None:
        return "unknown", rest
    return match.group("service").casefold(), match.group("message")


def parse_log_line(line: str) -> ParsedLogLine:
    """Parse RFC3164-like, ISO-8601, or level-prefixed text log headers.

    Severity is read only from the header position. A word such as ``ERROR``
    appearing later in a message never changes its level.
    """

    rfc = _RFC3164.match(line)
    if rfc is not None:
        severity, message, _has_level = _severity_and_message(rfc.group("body"))
        return ParsedLogLine(
            rfc.group("service").casefold(), severity, message, True
        )

    iso = _ISO8601.match(line)
    if iso is not None:
        severity, rest, _has_level = _severity_and_message(iso.group("body"))
        service, message = _service_and_message(rest)
        return ParsedLogLine(service, severity, message, True)

    # Useful for small application logs that omit timestamps, while still
    # requiring a severity token at the beginning rather than in the message.
    severity, rest, has_level = _severity_and_message(line.strip())
    if has_level:
        service, message = _service_and_message(rest)
        return ParsedLogLine(service, severity, message, True)

    return ParsedLogLine("unknown", "UNKNOWN", "Unsupported log line", False)


def scan_log_lines(log_dir: Path) -> tuple[Iterator[tuple[str, str]], int]:
    """Iterate top-level UTF-8 logs without retaining the complete input batch."""

    directory = Path(log_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Log directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Log path is not a directory: {directory}")

    paths = sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".log"),
        key=lambda path: path.name.casefold(),
    )
    def records() -> Iterator[tuple[str, str]]:
        for path in paths:
            try:
                with path.open(encoding="utf-8") as stream:
                    pending: list[str] = []
                    separators = tuple("\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029")
                    while chunk := stream.read(65536):
                        for part in chunk.splitlines(keepends=True):
                            if part.endswith(separators):
                                if pending:
                                    pending.append(part)
                                    line = "".join(pending)
                                    pending.clear()
                                else:
                                    line = part
                                yield path.name, line[:-2] if line.endswith("\r\n") else line[:-1]
                            else:
                                pending.append(part)
                    if pending:
                        yield path.name, "".join(pending)
            except UnicodeDecodeError as exc:
                raise ValueError(f"Log file is not valid UTF-8: {path}") from exc

    return records(), len(paths)


def load_log_lines(log_dir: Path) -> tuple[list[tuple[str, str]], int]:
    """Compatibility helper that materializes all supported input lines."""

    records, file_count = scan_log_lines(log_dir)
    return list(records), file_count


def summarize_log_lines(lines: list[str]) -> dict[str, int]:
    """Keep the baseline line/severity summary using explicit header levels."""

    counts: Counter[str] = Counter()
    for line in lines:
        counts[parse_log_line(line).severity] += 1
    return {"total_lines": len(lines), **{level: counts[level] for level in LEVELS}}


def load_logs_from_dir(log_dir: Path) -> list[str]:
    """Compatibility helper returning the raw lines from supported input files."""

    records, _ = load_log_lines(log_dir)
    return [line for _, line in records]
