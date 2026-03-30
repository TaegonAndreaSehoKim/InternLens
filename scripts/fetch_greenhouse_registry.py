from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.ingestion.greenhouse_client import (
    fetch_greenhouse_jobs,
    save_processed_greenhouse_jobs,
    save_raw_greenhouse_snapshot,
)


INTERNSHIP_TITLE_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\bco[- ]?op\b",
]

INTERNSHIP_CONTENT_PATTERNS = [
    r"\bthis internship\b",
    r"\binternship program\b",
    r"\bsummer internship\b",
    r"\bco[- ]?op program\b",
    r"\bintern class\b",
    r"\bintern cohort\b",
]


def _has_pattern_match(text: str, patterns: List[str]) -> bool:
    # Return True when any regex pattern matches the given text.
    return any(re.search(pattern, text) for pattern in patterns)


def _looks_like_internship(job: Dict[str, Any]) -> bool:
    # Keep jobs that look like internships based on stronger title/content rules.
    title = str(job.get("title", "")).lower()
    content = str(job.get("content", "")).lower()

    # Title matches are the strongest signal.
    if _has_pattern_match(title, INTERNSHIP_TITLE_PATTERNS):
        return True

    # Description matches are allowed only for strong internship phrases.
    if _has_pattern_match(content, INTERNSHIP_CONTENT_PATTERNS):
        return True

    return False


def _filter_internship_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Return only jobs that appear to be internship postings.
    return [job for job in jobs if _looks_like_internship(job)]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Greenhouse jobs from a registry file.")
    parser.add_argument(
        "--registry-path",
        default="data/source_registry/greenhouse_targets.json",
        help="Path to the Greenhouse registry JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional per-board fetch limit.",
    )
    parser.add_argument(
        "--only-active",
        action="store_true",
        help="Fetch only registry entries where active=true.",
    )
    parser.add_argument(
        "--internship-only",
        action="store_true",
        help="Apply internship-like filtering to all fetched boards.",
    )
    return parser.parse_args()


def _load_registry(registry_path: Path) -> List[Dict[str, Any]]:
    # Load registry entries from JSON.
    if not registry_path.exists():
        raise FileNotFoundError(f"Registry file not found: {registry_path}")

    with registry_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("Registry JSON must be a list of entries.")

    entries: List[Dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        board_token = str(item.get("board_token", "")).strip()
        if not board_token:
            continue

        entries.append(
            {
                "board_token": board_token,
                "active": bool(item.get("active", True)),
                "notes": str(item.get("notes", "")).strip(),
            }
        )

    return entries


def main() -> None:
    args = _parse_args()
    registry_path = PROJECT_ROOT / args.registry_path
    entries = _load_registry(registry_path)

    if args.only_active:
        entries = [entry for entry in entries if entry["active"]]

    if not entries:
        print("No registry entries to fetch.")
        return

    total_filtered_jobs = 0
    total_processed_jobs = 0

    for entry in entries:
        board_token = entry["board_token"]

        print(f"=== Fetching Greenhouse board: {board_token} ===")

        jobs = fetch_greenhouse_jobs(
            board_token,
            limit=args.limit,
            timeout=args.timeout,
            content=True,
        )

        raw_output_path = save_raw_greenhouse_snapshot(
            board_token,
            jobs,
            project_root=PROJECT_ROOT,
        )

        if args.internship_only:
            jobs = _filter_internship_jobs(jobs)

        processed_paths = save_processed_greenhouse_jobs(
            board_token,
            jobs,
            project_root=PROJECT_ROOT,
        )

        print(f"Saved raw snapshot to: {raw_output_path}")
        print(
            f"Saved {len(processed_paths)} processed jobs to: "
            f"{PROJECT_ROOT / 'data' / 'processed' / 'jobs' / 'greenhouse' / board_token}"
        )

        if args.internship_only and not jobs:
            print("No internship-like jobs matched the current filter.")

        total_filtered_jobs += len(jobs)
        total_processed_jobs += len(processed_paths)
        print()

    print("=== Registry fetch complete ===")
    print(f"Total filtered jobs fetched: {total_filtered_jobs}")
    print(f"Total processed jobs saved: {total_processed_jobs}")


if __name__ == "__main__":
    main()