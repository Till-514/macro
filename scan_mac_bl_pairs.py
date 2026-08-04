#!/usr/bin/env python3
"""Scan .mac and .1.bl files and report matching file-name pairs.

The script only reads file names. It does not modify, move, or delete any
scanned files.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MAC_SUFFIX = ".mac"
BL_SUFFIX = ".1.bl"


@dataclass(frozen=True)
class FoundFile:
    name: str
    base_name: str
    file_type: str
    path: str


def get_target_file(path: Path) -> FoundFile | None:
    name_lower = path.name.casefold()

    if name_lower.endswith(MAC_SUFFIX):
        return FoundFile(
            name=path.name,
            base_name=path.name[: -len(MAC_SUFFIX)],
            file_type=MAC_SUFFIX,
            path=str(path.resolve()),
        )

    if name_lower.endswith(BL_SUFFIX):
        return FoundFile(
            name=path.name,
            base_name=path.name[: -len(BL_SUFFIX)],
            file_type=BL_SUFFIX,
            path=str(path.resolve()),
        )

    return None


def get_target_list_item(item: str) -> FoundFile | None:
    path = Path(item)
    name_lower = path.name.casefold()

    if name_lower.endswith(MAC_SUFFIX):
        return FoundFile(
            name=path.name,
            base_name=path.name[: -len(MAC_SUFFIX)],
            file_type=MAC_SUFFIX,
            path=item,
        )

    if name_lower.endswith(BL_SUFFIX):
        return FoundFile(
            name=path.name,
            base_name=path.name[: -len(BL_SUFFIX)],
            file_type=BL_SUFFIX,
            path=item,
        )

    return None


def iter_files_from_directory(directory: Path) -> Iterable[FoundFile]:
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue

        found = get_target_file(path)
        if found is None:
            continue

        yield found


def iter_files_from_list_file(list_file: Path) -> Iterable[FoundFile]:
    encodings = ("utf-8-sig", "utf-8", "gbk", "mbcs")
    lines: list[str] | None = None

    for encoding in encodings:
        try:
            lines = list_file.read_text(encoding=encoding).splitlines()
            break
        except UnicodeDecodeError:
            continue

    if lines is None:
        raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode {list_file}")

    for line in lines:
        item = line.strip().strip('"')
        if not item:
            continue

        found = get_target_list_item(item)
        if found is None:
            continue

        yield found


def collect_files(input_path: Path) -> dict[str, dict[str, list[FoundFile]]]:
    grouped: dict[str, dict[str, list[FoundFile]]] = {}

    if input_path.is_dir():
        files = iter_files_from_directory(input_path)
    else:
        files = iter_files_from_list_file(input_path)

    for found in files:
        key = found.base_name.casefold()
        grouped.setdefault(key, {MAC_SUFFIX: [], BL_SUFFIX: []})[found.file_type].append(found)

    return grouped


def join_paths(files: list[FoundFile]) -> str:
    return " | ".join(file.path for file in files)


def write_matched_csv(path: Path, grouped: dict[str, dict[str, list[FoundFile]]]) -> int:
    count = 0
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["base_name", "mac_count", "bl_count", "mac_files", "bl_files"])

        for key in sorted(grouped):
            mac_files = grouped[key][MAC_SUFFIX]
            bl_files = grouped[key][BL_SUFFIX]
            if not mac_files or not bl_files:
                continue

            display_name = mac_files[0].base_name if mac_files else bl_files[0].base_name
            writer.writerow(
                [
                    display_name,
                    len(mac_files),
                    len(bl_files),
                    join_paths(mac_files),
                    join_paths(bl_files),
                ]
            )
            count += 1

    return count


def write_unmatched_csv(path: Path, grouped: dict[str, dict[str, list[FoundFile]]]) -> int:
    count = 0
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["base_name", "file_type", "file_name", "file_path", "missing_type"])

        for key in sorted(grouped):
            mac_files = grouped[key][MAC_SUFFIX]
            bl_files = grouped[key][BL_SUFFIX]

            if mac_files and bl_files:
                continue

            missing_type = BL_SUFFIX if mac_files else MAC_SUFFIX
            existing_files = mac_files or bl_files
            for found in existing_files:
                writer.writerow(
                    [
                        found.base_name,
                        found.file_type,
                        found.name,
                        found.path,
                        missing_type,
                    ]
                )
                count += 1

    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan .mac and .1.bl files by the same base file name. Output one CSV "
            "for matched names and one CSV for unmatched files."
        )
    )
    parser.add_argument(
        "input",
        help="Directory to scan recursively, or a text file containing one file path/name per line.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help="Directory for output CSV files. Default: current directory.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        parser.error(f"input path does not exist: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    grouped = collect_files(input_path)

    matched_path = output_dir / "matched_mac_bl.csv"
    unmatched_path = output_dir / "unmatched_mac_bl.csv"

    matched_count = write_matched_csv(matched_path, grouped)
    unmatched_count = write_unmatched_csv(unmatched_path, grouped)

    print(f"Matched base name(s): {matched_count}")
    print(f"Unmatched file(s): {unmatched_count}")
    print(f"Matched CSV: {matched_path}")
    print(f"Unmatched CSV: {unmatched_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
