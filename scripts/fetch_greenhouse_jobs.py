from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.ingestion.greenhouse_client import (
    fetch_greenhouse_jobs,
    save_processed_greenhouse_jobs,
    save_raw_greenhouse_snapshot,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch public Greenhouse job postings.")
    parser.add_argument(
        "--board-token",
        required=True,
        help="Greenhouse board token, e.g. a token from boards.greenhouse.io/<board_token>",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for fetched jobs")
    parser.add_argument("--timeout", type=float, default=60.0, help="Request timeout in seconds")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    jobs = fetch_greenhouse_jobs(
        args.board_token,
        limit=args.limit,
        timeout=args.timeout,
        content=True,
    )

    raw_output_path = save_raw_greenhouse_snapshot(
        args.board_token,
        jobs,
        project_root=PROJECT_ROOT,
    )

    processed_paths = save_processed_greenhouse_jobs(
        args.board_token,
        jobs,
        project_root=PROJECT_ROOT,
    )

    processed_output_dir = PROJECT_ROOT / "data" / "processed" / "jobs" / "greenhouse" / args.board_token

    print(f"Saved raw snapshot to: {raw_output_path}")
    print(f"Saved {len(processed_paths)} processed jobs to: {processed_output_dir}")
    print(f"Fetched {len(jobs)} jobs from Greenhouse board '{args.board_token}'")

    if jobs:
        print(json.dumps(jobs[0], indent=2)[:2000])
    else:
        print("No jobs returned. Check whether the board token is valid.")


if __name__ == "__main__":
    main()