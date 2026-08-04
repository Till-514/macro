#!/usr/bin/env python3
"""Extract unique [ImportLog] lines whose import result is Excellent.

The script keeps the original log line in the output file and de-duplicates
records by the imported file path field.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


def parse_csv_prefix(line: str, max_fields: int = 4) -> list[str]:
    """Parse the first CSV-like fields from a line.

    Log lines can contain quoted Windows paths. We only need the first fields,
    so this tolerant parser stops early and does not require the rest of the
    line to be valid CSV.
    """
    fields: list[str] = []
    current: list[str] = []
    in_quotes = False
    i = 0

    while i < len(line):
        char = line[i]

        if char == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                current.append('"')
                i += 2
                continue
            in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            fields.append("".join(current))
            current = []
            if len(fields) >= max_fields:
                return fields
        else:
            current.append(char)

        i += 1

    fields.append("".join(current).rstrip("\r\n"))
    return fields


def iter_log_files(path: Path) -> Iterable[Path]:
    if path.is_dir():
        yield from sorted(path.rglob("*.log"))
    else:
        yield path


def read_lines(path: Path) -> Iterable[str]:
    encodings = ("utf-8-sig", "utf-8", "gbk", "mbcs")
    last_error: UnicodeDecodeError | None = None

    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding) as file:
                yield from file
            return
        except UnicodeDecodeError as error:
            last_error = error

    if last_error is not None:
        raise last_error


def extract_excellent_lines(input_path: Path) -> list[str]:
    seen_paths: set[str] = set()
    excellent_lines: list[str] = []

    for log_file in iter_log_files(input_path):
        for line in read_lines(log_file):
            if "[ImportLog]" not in line:
                continue

            fields = parse_csv_prefix(line, max_fields=4)
            if len(fields) < 4:
                continue

            imported_path = fields[1].strip()
            result = fields[3].strip()
            dedupe_key = imported_path.lower()

            if result == "Excellent" and dedupe_key not in seen_paths:
                seen_paths.add(dedupe_key)
                excellent_lines.append(line)

    return excellent_lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read a log file or directory, keep unique [ImportLog] lines whose "
            "result field is Excellent, and write the original lines to a file."
        )
    )
    parser.add_argument("input", help="Path to a log file, or a directory containing .log files")
    parser.add_argument(
        "-o",
        "--output",
        default="import_excellent.log",
        help="Output file path. Default: import_excellent.log",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        parser.error(f"input path does not exist: {input_path}")

    excellent_lines = extract_excellent_lines(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(excellent_lines), encoding="utf-8")

    print(f"Found {len(excellent_lines)} unique Excellent import line(s).")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
