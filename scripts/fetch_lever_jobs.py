from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.ingestion.lever_client import fetch_lever_postings

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch public Lever job postings.")
    parser.add_argument("--site-name", required=True, help="Lever site name, e.g. a board token from jobs.lever.co/<site_name>")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit for fetched jobs")
    parser.add_argument("--timeout", type=float, default=60.0, help="Request timeout in seconds")
    return parser.parse_args()

def main() -> None:
    args = _parse_args()
    jobs = fetch_lever_postings(
        args.site_name,
        limit=args.limit,
        timeout=args.timeout,
    )

    print(f"Fetched {len(jobs)} jobs from Lever site '{args.site_name}'")
    if jobs:
        print(json.dumps(jobs[0], indent=2)[:2000])
    else:
        print("No jobs returned. Check whether the site name is a valid Lever board token.")


if __name__ == "__main__":
    main()