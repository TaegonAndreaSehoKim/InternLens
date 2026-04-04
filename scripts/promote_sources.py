from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.discovery.source_discovery import load_json_list, save_json_list
from src.discovery.source_promotion import promote_validated_sources


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote validated discovered sources into active Lever and Greenhouse registries."
    )
    parser.add_argument(
        "--input-file",
        default="data/source_registry/discovered_sources.json",
        help="Path to the discovered sources JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--lever-registry",
        default="data/source_registry/lever_targets.json",
        help="Path to the Lever registry JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--greenhouse-registry",
        default="data/source_registry/greenhouse_targets.json",
        help="Path to the Greenhouse registry JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.45,
        help="Minimum source score required for promotion.",
    )
    parser.add_argument(
        "--allow-non-internship-sources",
        action="store_true",
        help="Allow promotion even when internship_likelihood is zero.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    input_path = PROJECT_ROOT / args.input_file
    lever_registry_path = PROJECT_ROOT / args.lever_registry
    greenhouse_registry_path = PROJECT_ROOT / args.greenhouse_registry

    discovered_records = load_json_list(input_path)
    lever_registry = load_json_list(lever_registry_path)
    greenhouse_registry = load_json_list(greenhouse_registry_path)

    updated_discovered, updated_lever, updated_greenhouse, summary = promote_validated_sources(
        discovered_records,
        lever_registry=lever_registry,
        greenhouse_registry=greenhouse_registry,
        min_score=args.min_score,
        require_internship_signal=not args.allow_non_internship_sources,
    )

    save_json_list(input_path, updated_discovered)
    save_json_list(lever_registry_path, updated_lever)
    save_json_list(greenhouse_registry_path, updated_greenhouse)

    print("##### Source promotion complete #####")
    print(f"Discovered sources updated: {input_path}")
    print(f"Lever registry updated: {lever_registry_path}")
    print(f"Greenhouse registry updated: {greenhouse_registry_path}")
    print(f"Promoted: {summary['promoted']}")
    print(f"Reactivated: {summary['reactivated']}")
    print(f"Already active: {summary['already_active']}")
    print(f"Skipped for status: {summary['skipped_status']}")
    print(f"Skipped for score: {summary['skipped_score']}")
    print(f"Skipped for internship signal: {summary['skipped_internship']}")
    print(f"Skipped unsupported: {summary['skipped_unsupported']}")


if __name__ == "__main__":
    main()
