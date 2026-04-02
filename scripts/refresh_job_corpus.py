from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.fetch_greenhouse_registry import run_registry_fetch as run_greenhouse_registry_fetch
from scripts.fetch_lever_registry import run_registry_fetch as run_lever_registry_fetch


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the processed internship corpus from Lever and Greenhouse registry sources."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds for each source fetch.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional per-board fetch limit for both sources.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Also fetch registry entries marked inactive.",
    )
    parser.add_argument(
        "--greenhouse-all-jobs",
        action="store_true",
        help="Disable internship-only filtering for Greenhouse sources.",
    )
    parser.add_argument(
        "--greenhouse-only",
        action="store_true",
        help="Refresh only Greenhouse sources.",
    )
    parser.add_argument(
        "--lever-only",
        action="store_true",
        help="Refresh only Lever sources.",
    )
    return parser.parse_args()


def _should_run_lever(args: argparse.Namespace) -> bool:
    return not args.greenhouse_only


def _should_run_greenhouse(args: argparse.Namespace) -> bool:
    return not args.lever_only


def main() -> None:
    args = _parse_args()

    if args.greenhouse_only and args.lever_only:
        raise ValueError("Choose at most one of --greenhouse-only or --lever-only.")

    total_entries = 0
    total_filtered_jobs = 0
    total_processed_jobs = 0

    if _should_run_lever(args):
        print("##### Refreshing Lever sources #####")
        lever_summary = run_lever_registry_fetch(
            registry_path=PROJECT_ROOT / "data" / "source_registry" / "lever_targets.json",
            timeout=args.timeout,
            limit=args.limit,
            only_active=not args.include_inactive,
            project_root=PROJECT_ROOT,
        )
        total_entries += int(lever_summary["entries_fetched"])
        total_filtered_jobs += int(lever_summary["total_filtered_jobs"])
        total_processed_jobs += int(lever_summary["total_processed_jobs"])
        print()

    if _should_run_greenhouse(args):
        print("##### Refreshing Greenhouse sources #####")
        greenhouse_summary = run_greenhouse_registry_fetch(
            registry_path=PROJECT_ROOT / "data" / "source_registry" / "greenhouse_targets.json",
            timeout=args.timeout,
            limit=args.limit,
            only_active=not args.include_inactive,
            internship_only=not args.greenhouse_all_jobs,
            project_root=PROJECT_ROOT,
        )
        total_entries += int(greenhouse_summary["entries_fetched"])
        total_filtered_jobs += int(greenhouse_summary["total_filtered_jobs"])
        total_processed_jobs += int(greenhouse_summary["total_processed_jobs"])
        print()

    print("##### Corpus refresh complete #####")
    print(f"Registry entries fetched: {total_entries}")
    print(f"Filtered jobs saved: {total_filtered_jobs}")
    print(f"Processed job files saved: {total_processed_jobs}")


if __name__ == "__main__":
    main()
