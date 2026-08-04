#!/usr/bin/env python3
"""Collect files from matched_mac_bl.csv into macro and bl folders."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
from pathlib import Path


MAC_SUFFIX = ".mac"
BL_SUFFIX = ".1.bl"
MODEL_SUFFIXES = (".z3prt", ".z3prt.z3bak", ".sldprt")


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    encodings = ("utf-8-sig", "utf-8", "gbk", "mbcs")

    for encoding in encodings:
        try:
            with csv_path.open("r", newline="", encoding=encoding) as file:
                return list(csv.DictReader(file))
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode {csv_path}")


def split_path_cell(value: str) -> list[Path]:
    return [Path(item.strip().strip('"')) for item in value.split(" | ") if item.strip()]


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []

    for path in paths:
        key = str(path).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)

    return result


def get_source_root(paths: list[Path], source_root: Path | None) -> Path:
    if source_root is not None:
        return source_root.resolve()

    existing_paths = [path.resolve() for path in paths if path.exists()]
    if not existing_paths:
        return Path.cwd()
    if len(existing_paths) == 1:
        return existing_paths[0].parent

    common_path = Path(os.path.commonpath(existing_paths))
    return common_path if common_path.is_dir() else common_path.parent


def get_relative_path(path: Path, source_root: Path) -> Path:
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(source_root)
    except ValueError:
        drive = resolved_path.drive.rstrip(":")
        parts = [part for part in resolved_path.parts[1:] if part]
        return Path(drive, *parts) if drive else Path(*parts)


def copy_paths(paths: list[Path], output_dir: Path, source_root: Path) -> tuple[int, int]:
    copied_count = 0
    missing_count = 0

    for source_path in unique_paths(paths):
        if not source_path.is_file():
            print(f"Missing source file: {source_path}")
            missing_count += 1
            continue

        target_path = output_dir / get_relative_path(source_path, source_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied_count += 1

    return copied_count, missing_count


def derive_pair_path(path: Path) -> Path | None:
    name_lower = path.name.casefold()

    if name_lower.endswith(MAC_SUFFIX):
        return path.with_name(path.name[: -len(MAC_SUFFIX)] + BL_SUFFIX)

    if name_lower.endswith(BL_SUFFIX):
        return path.with_name(path.name[: -len(BL_SUFFIX)] + MAC_SUFFIX)

    return None


def get_model_key_from_macro_name(path: Path) -> str:
    name_lower = path.name.casefold()

    if name_lower.endswith(MAC_SUFFIX):
        base_name = path.name[: -len(MAC_SUFFIX)]
    elif name_lower.endswith(BL_SUFFIX):
        base_name = path.name[: -len(BL_SUFFIX)]
    else:
        base_name = path.stem

    return base_name[:-4] if base_name.casefold().endswith("_prt") else base_name


def is_model_file(path: Path) -> bool:
    name_lower = path.name.casefold()
    return any(name_lower.endswith(suffix) for suffix in MODEL_SUFFIXES)


def find_related_model_files(search_dir: Path, model_keys: list[str]) -> list[Path]:
    key_set = {key.casefold() for key in model_keys if key}
    found: list[Path] = []

    if not search_dir.is_dir():
        raise NotADirectoryError(f"BL search directory does not exist: {search_dir}")

    for path in search_dir.rglob("*"):
        if not path.is_file() or not is_model_file(path):
            continue

        name_lower = path.name.casefold()
        if any(key in name_lower for key in key_set):
            found.append(path)

    return unique_paths(found)


def collect_macro_paths(rows: list[dict[str, str]]) -> tuple[list[Path], list[str]]:
    macro_paths: list[Path] = []
    model_keys: list[str] = []

    for row in rows:
        mac_paths = split_path_cell(row.get("mac_files", ""))
        bl_paths = split_path_cell(row.get("bl_files", ""))

        for mac_path in mac_paths:
            macro_paths.append(mac_path)
            pair_path = derive_pair_path(mac_path)
            if pair_path is not None:
                macro_paths.append(pair_path)
            model_keys.append(get_model_key_from_macro_name(mac_path))

        for bl_path in bl_paths:
            macro_paths.append(bl_path)

    return unique_paths(macro_paths), model_keys


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read matched_mac_bl.csv, copy .mac/.1.bl files into macro, and "
            "copy related .Z3PRT/.z3bak/.SLDPRT files into bl."
        )
    )
    parser.add_argument(
        "csv",
        nargs="?",
        default="matched_mac_bl.csv",
        help="Input CSV generated by scan_mac_bl_pairs.py. Default: matched_mac_bl.csv",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="matched_collected_files",
        help="Output folder. It will contain macro and bl folders. Default: matched_collected_files",
    )
    parser.add_argument(
        "--bl-search-dir",
        required=True,
        help="Folder used to search related .Z3PRT, .Z3PRT.z3bak, and .SLDPRT files.",
    )
    parser.add_argument(
        "--macro-source-root",
        help="Root folder used to preserve relative paths under the macro folder.",
    )
    parser.add_argument(
        "--bl-source-root",
        help="Root folder used to preserve relative paths under the bl folder. Default: --bl-search-dir.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    output_dir = Path(args.output_dir)
    bl_search_dir = Path(args.bl_search_dir)

    if not csv_path.is_file():
        parser.error(f"CSV file does not exist: {csv_path}")
    if not bl_search_dir.is_dir():
        parser.error(f"BL search directory does not exist: {bl_search_dir}")

    rows = read_csv_rows(csv_path)
    macro_paths, model_keys = collect_macro_paths(rows)
    model_paths = find_related_model_files(bl_search_dir, model_keys)

    macro_output_dir = output_dir / "macro"
    bl_output_dir = output_dir / "bl"
    macro_source_root = get_source_root(
        macro_paths,
        Path(args.macro_source_root) if args.macro_source_root else None,
    )
    bl_source_root = Path(args.bl_source_root).resolve() if args.bl_source_root else bl_search_dir.resolve()

    macro_copied, macro_missing = copy_paths(macro_paths, macro_output_dir, macro_source_root)
    bl_copied, bl_missing = copy_paths(model_paths, bl_output_dir, bl_source_root)

    print(f"Macro source root: {macro_source_root}")
    print(f"BL source root: {bl_source_root}")
    print(f"Copied macro file(s): {macro_copied}")
    print(f"Missing macro file(s): {macro_missing}")
    print(f"Copied BL related file(s): {bl_copied}")
    print(f"Missing BL related file(s): {bl_missing}")
    print(f"Output folder: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
