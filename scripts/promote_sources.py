from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.discovery.source_discovery import load_json_list, save_json_list
from src.discovery.source_promotion import promote_validated_sources


def _record_label(record: dict) -> str:
    return (
        f"{record.get('company', '')} | {record.get('source_type', '')} | "
        f"{record.get('source_identifier', '')} | score={float(record.get('source_score', 0.0) or 0.0):.2f} | "
        f"internship={float(record.get('internship_likelihood', 0.0) or 0.0):.2f} | "
        f"method={record.get('discovery_method', '')}"
    )


def _promotion_candidate_key(record: dict) -> tuple[str, str]:
    return (
        str(record.get("source_type", "")).strip(),
        str(record.get("source_identifier", "")).strip(),
    )


def _print_record_section(title: str, records: list[dict]) -> None:
    if not records:
        return
    print(title)
    for record in records:
        print(f"- {_record_label(record)}")


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
    parser.add_argument(
        "--min-internship-likelihood",
        type=float,
        default=0.08,
        help="Minimum internship likelihood required for promotion when internship signal is required.",
    )
    parser.add_argument(
        "--direct-probe-min-score",
        type=float,
        default=0.5,
        help="Minimum source score required for sources found by direct ATS probing.",
    )
    parser.add_argument(
        "--direct-probe-min-internship-likelihood",
        type=float,
        default=0.12,
        help="Minimum internship likelihood required for sources found by direct ATS probing.",
    )
    parser.add_argument(
        "--reactivate-inactive-sources",
        action="store_true",
        help="Allow promotion to reactivate registry entries that are currently marked inactive.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print promotion decisions without updating discovered source or registry files.",
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
        min_internship_likelihood=args.min_internship_likelihood,
        direct_probe_min_score=args.direct_probe_min_score,
        direct_probe_min_internship_likelihood=args.direct_probe_min_internship_likelihood,
        reactivate_inactive_sources=args.reactivate_inactive_sources,
    )

    dry_run = bool(getattr(args, "dry_run", False))

    if not dry_run:
        save_json_list(input_path, updated_discovered)
        save_json_list(lever_registry_path, updated_lever)
        save_json_list(greenhouse_registry_path, updated_greenhouse)

    print("##### Source promotion dry run #####" if dry_run else "##### Source promotion complete #####")
    if dry_run:
        print(f"Discovered sources checked: {input_path}")
        print(f"Lever registry checked: {lever_registry_path}")
        print(f"Greenhouse registry checked: {greenhouse_registry_path}")
    else:
        print(f"Discovered sources updated: {input_path}")
        print(f"Lever registry updated: {lever_registry_path}")
        print(f"Greenhouse registry updated: {greenhouse_registry_path}")
    print(f"Promoted: {summary['promoted']}")
    print(f"Reactivated: {summary['reactivated']}")
    print(f"Already active: {summary['already_active']}")
    print(f"Skipped inactive registry entries: {summary['skipped_inactive']}")
    print(f"Skipped for status: {summary['skipped_status']}")
    print(f"Skipped for score: {summary['skipped_score']}")
    print(f"Skipped for internship signal: {summary['skipped_internship']}")
    print(f"Skipped for direct probe safeguard: {summary['skipped_direct_probe']}")
    print(f"Skipped unsupported: {summary['skipped_unsupported']}")

    if dry_run:
        promoted_keys = {
            _promotion_candidate_key(updated)
            for original, updated in zip(discovered_records, updated_discovered)
            if original.get("status") != "active" and updated.get("status") == "active"
        }
        promoted_records = [
            record
            for record in discovered_records
            if _promotion_candidate_key(record) in promoted_keys
        ]
        inactive_keys = {
            ("lever", str(entry.get("site_name", "")).strip())
            for entry in lever_registry
            if not bool(entry.get("active", True))
        } | {
            ("greenhouse", str(entry.get("board_token", "")).strip())
            for entry in greenhouse_registry
            if not bool(entry.get("active", True))
        }
        skipped_inactive = [
            record
            for record in discovered_records
            if _promotion_candidate_key(record) in inactive_keys
            and str(record.get("status", "")).lower() == "validated"
        ]
        skipped_direct_probe = [
            record
            for original, record in zip(updated_discovered, discovered_records)
            if original.get("status") == record.get("status")
            and str(record.get("status", "")).lower() == "validated"
            and str(record.get("discovery_method", "")).lower() == "direct_ats_probe"
            and float(record.get("source_score", 0.0) or 0.0) >= args.min_score
            and (
                args.allow_non_internship_sources
                or float(record.get("internship_likelihood", 0.0) or 0.0) >= args.min_internship_likelihood
            )
            and _promotion_candidate_key(record) not in promoted_keys
            and _promotion_candidate_key(record) not in inactive_keys
        ]

        _print_record_section("Would promote or reactivate:", promoted_records)
        _print_record_section("Skipped by direct probe safeguard:", skipped_direct_probe)
        _print_record_section("Skipped inactive registry entries:", skipped_inactive)


if __name__ == "__main__":
    main()
