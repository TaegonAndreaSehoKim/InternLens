from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.discovery.source_discovery import load_json_list, save_json_list
from src.discovery.source_validation import load_active_registry_keys, validate_discovered_sources


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate discovered Lever and Greenhouse source candidates."
    )
    parser.add_argument(
        "--input-file",
        default="data/source_registry/discovered_sources.json",
        help="Path to the discovered sources JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Request timeout in seconds for each source validation fetch.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Optional per-source fetch limit for validation.",
    )
    parser.add_argument(
        "--include-non-candidate",
        action="store_true",
        help="Revalidate sources even when their status is not candidate.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    input_path = PROJECT_ROOT / args.input_file
    records = load_json_list(input_path)
    active_registry_keys = load_active_registry_keys(PROJECT_ROOT)

    validated_records, summary = validate_discovered_sources(
        records,
        timeout=args.timeout,
        limit=args.limit,
        active_registry_keys=active_registry_keys,
        include_non_candidate=args.include_non_candidate,
    )
    save_json_list(input_path, validated_records)

    print("##### Source validation complete #####")
    print(f"Input file updated: {input_path}")
    print(f"Sources attempted: {summary['attempted']}")
    print(f"Validated or active: {summary['validated']}")
    print(f"Rejected: {summary['rejected']}")
    print(f"Skipped: {summary['skipped']}")


if __name__ == "__main__":
    main()
