from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.discovery.source_discovery import (
    discover_sources,
    load_json_list,
    merge_discovered_sources,
    resolve_seed_path,
    save_json_list,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover candidate Lever and Greenhouse sources from company seed URLs."
    )
    parser.add_argument(
        "--seed-file",
        default="data/source_registry/company_seeds.json",
        help="Path to the company seed JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--output-file",
        default="data/source_registry/discovered_sources.json",
        help="Path to the discovered sources JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Request timeout in seconds for each scanned page.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    requested_seed_path = PROJECT_ROOT / args.seed_file
    resolved_seed_path = resolve_seed_path(requested_seed_path)
    output_path = PROJECT_ROOT / args.output_file

    seeds = load_json_list(resolved_seed_path)
    existing_sources = load_json_list(output_path)
    discovered_sources, errors = discover_sources(seeds, timeout=args.timeout)
    merged_sources = merge_discovered_sources(existing_sources, discovered_sources)
    save_json_list(output_path, merged_sources)

    print("##### Source discovery complete #####")
    print(f"Seed file used: {resolved_seed_path}")
    print(f"Seed companies scanned: {len(seeds)}")
    print(f"Discovered source candidates: {len(discovered_sources)}")
    print(f"Total stored candidates: {len(merged_sources)}")

    if errors:
        print("Warnings:")
        for error in errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()
