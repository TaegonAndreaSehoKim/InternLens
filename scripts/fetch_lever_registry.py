from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.ingestion.lever_client import (
    fetch_lever_postings,
    save_processed_lever_postings,
    save_raw_lever_snapshot,
)


def _looks_like_internship(job: Dict[str, Any]) -> bool:
    # Keep postings that look like internships based on title, description, or commitment text.
    title = str(job.get("text", "")).lower()
    description = str(job.get("descriptionPlain", "")).lower()

    categories = job.get("categories", {})
    commitment = ""
    if isinstance(categories, dict):
        commitment = str(categories.get("commitment", "")).lower()

    combined = f"{title} {description} {commitment}"

    internship_keywords = [
        "intern",
        "internship",
        "summer intern",
        "student intern",
    ]

    return any(keyword in combined for keyword in internship_keywords)


def _filter_internship_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Return only jobs that appear to be internship postings.
    return [job for job in jobs if _looks_like_internship(job)]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Lever jobs from a registry file.")
    parser.add_argument(
        "--registry-path",
        default="data/source_registry/lever_targets.json",
        help="Path to the Lever registry JSON file, relative to the project root.",
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

        site_name = str(item.get("site_name", "")).strip()
        if not site_name:
            continue

        entries.append(
            {
                "site_name": site_name,
                "active": bool(item.get("active", True)),
                "internship_only": bool(item.get("internship_only", False)),
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

    total_raw_jobs = 0
    total_processed_jobs = 0

    for entry in entries:
        site_name = entry["site_name"]
        internship_only = entry["internship_only"]

        print(f"=== Fetching Lever board: {site_name} ===")

        jobs = fetch_lever_postings(
            site_name,
            limit=args.limit,
            timeout=args.timeout,
        )

        raw_output_path = save_raw_lever_snapshot(
            site_name,
            jobs,
            project_root=PROJECT_ROOT,
        )

        if internship_only:
            jobs = _filter_internship_jobs(jobs)

        processed_paths = save_processed_lever_postings(
            site_name,
            jobs,
            project_root=PROJECT_ROOT,
        )

        print(f"Saved raw snapshot to: {raw_output_path}")
        print(
            f"Saved {len(processed_paths)} processed jobs to: "
            f"{PROJECT_ROOT / 'data' / 'processed' / 'jobs' / 'lever' / site_name}"
        )

        if internship_only and not jobs:
            print("No internship-like jobs matched the current filter.")

        total_raw_jobs += len(jobs)
        total_processed_jobs += len(processed_paths)
        print()

    print("=== Registry fetch complete ===")
    print(f"Total filtered jobs fetched: {total_raw_jobs}")
    print(f"Total processed jobs saved: {total_processed_jobs}")


if __name__ == "__main__":
    main()