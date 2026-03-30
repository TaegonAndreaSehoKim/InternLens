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
    parser = argparse.ArgumentParser(description="Fetch public Lever job postings.")
    parser.add_argument("--site-name", required=True, help="Lever site name, e.g. a board token from jobs.lever.co/<site_name>")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for fetched jobs")
    parser.add_argument("--timeout", type=float, default=60.0, help="Request timeout in seconds")
    parser.add_argument(
        "--internship-only",
        action="store_true",
        help="Keep only postings that look like internships",
    )
    return parser.parse_args()

def main() -> None:
    args = _parse_args()
    jobs = fetch_lever_postings(
        args.site_name,
        limit=args.limit,
        timeout=args.timeout,
    )

    if args.internship_only:
        jobs = _filter_internship_jobs(jobs)

    raw_output_path = save_raw_lever_snapshot(
        args.site_name,
        jobs,
        project_root=PROJECT_ROOT,
    )

    processed_paths = save_processed_lever_postings(
        args.site_name,
        jobs,
        project_root=PROJECT_ROOT,
    )

    print(f"Saved raw snapshot to: {raw_output_path}")
    print(f"Saved {len(processed_paths)} processed jobs to: {PROJECT_ROOT / 'data' / 'processed' / 'jobs'}")
    print(f"Fetched {len(jobs)} jobs from Lever site '{args.site_name}'")

    if jobs:
        print(json.dumps(jobs[0], indent=2)[:2000])
    else:
        print("No jobs returned. Check whether the site name is a valid Lever board token.")


if __name__ == "__main__":
    main()