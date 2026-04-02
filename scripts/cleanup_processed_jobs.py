from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.job_parser import load_job_posting


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove legacy flat processed job files that duplicate nested source/site files."
    )
    parser.add_argument(
        "--jobs-dir",
        default="data/processed/jobs",
        help="Processed jobs directory, relative to the project root.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete duplicate legacy flat files. Without this flag, only print the plan.",
    )
    return parser.parse_args()


def find_legacy_flat_duplicates(jobs_dir: Path) -> List[Path]:
    # Detect top-level processed job files that already exist in nested canonical folders.
    nested_paths_by_job_id: dict[str, Path] = {}

    for file_path in sorted(jobs_dir.rglob("*.json")):
        relative_path = file_path.relative_to(jobs_dir)
        if len(relative_path.parts) <= 1:
            continue

        job = load_job_posting(file_path)
        nested_paths_by_job_id[job["job_id"]] = file_path

    duplicates: List[Path] = []
    for file_path in sorted(jobs_dir.glob("*.json")):
        job = load_job_posting(file_path)
        if job["job_id"] in nested_paths_by_job_id:
            duplicates.append(file_path)

    return duplicates


def remove_legacy_flat_duplicates(jobs_dir: Path, *, apply: bool) -> List[Path]:
    # Optionally delete the duplicate top-level files.
    duplicates = find_legacy_flat_duplicates(jobs_dir)

    if apply:
        for file_path in duplicates:
            file_path.unlink()

    return duplicates


def main() -> None:
    args = _parse_args()
    jobs_dir = PROJECT_ROOT / args.jobs_dir

    if not jobs_dir.exists():
        raise FileNotFoundError(f"Processed jobs directory not found: {jobs_dir}")

    duplicates = remove_legacy_flat_duplicates(jobs_dir, apply=args.apply)

    if not duplicates:
        print("No legacy flat duplicates found.")
        return

    print(f"Found {len(duplicates)} legacy flat duplicate files:")
    for file_path in duplicates:
        print(f"- {file_path}")

    if args.apply:
        print(f"Removed {len(duplicates)} duplicate files.")
    else:
        print("Dry run only. Re-run with --apply to delete them.")


if __name__ == "__main__":
    main()
