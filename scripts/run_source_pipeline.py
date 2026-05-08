from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.fetch_greenhouse_registry import run_registry_fetch as run_greenhouse_registry_fetch
from scripts.fetch_lever_registry import run_registry_fetch as run_lever_registry_fetch
from src.discovery.source_discovery import (
    discover_sources,
    format_discovery_warning,
    iter_seed_batches,
    load_json_list,
    merge_discovered_sources,
    resolve_seed_path,
    save_json_list,
    select_seed_subset,
    summarize_discovery_methods,
    summarize_discovery_warnings,
    visible_discovery_warnings,
)
from src.discovery.source_promotion import promote_validated_sources
from src.discovery.source_validation import load_active_registry_keys, validate_discovered_sources


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full InternLens source pipeline: discover, validate, promote, and refresh."
    )
    parser.add_argument("--seed-file", default="data/source_registry/company_seeds.json")
    parser.add_argument("--discovered-file", default="data/source_registry/discovered_sources.json")
    parser.add_argument("--lever-registry", default="data/source_registry/lever_targets.json")
    parser.add_argument("--greenhouse-registry", default="data/source_registry/greenhouse_targets.json")
    parser.add_argument("--min-priority", type=int, default=None)
    parser.add_argument("--max-seeds", type=int, default=None)
    parser.add_argument("--discovery-timeout", type=float, default=20.0)
    parser.add_argument("--discovery-checkpoint-size", type=int, default=25)
    parser.add_argument("--probe-direct-ats", action="store_true")
    parser.add_argument("--record-blocked-sources", action="store_true")
    parser.add_argument("--direct-probe-limit", type=int, default=1)
    parser.add_argument("--max-direct-probe-identifiers", type=int, default=2)
    parser.add_argument("--priority-follow-limit", type=int, default=5)
    parser.add_argument("--validation-timeout", type=float, default=20.0)
    parser.add_argument("--validation-limit", type=int, default=100)
    parser.add_argument("--include-non-candidate", action="store_true")
    parser.add_argument("--promotion-min-score", type=float, default=0.45)
    parser.add_argument("--allow-non-internship-sources", action="store_true")
    parser.add_argument("--min-internship-likelihood", type=float, default=0.08)
    parser.add_argument("--refresh-timeout", type=float, default=60.0)
    parser.add_argument("--refresh-limit", type=int, default=None)
    parser.add_argument("--refresh-include-inactive", action="store_true")
    parser.add_argument("--greenhouse-all-jobs", action="store_true")
    parser.add_argument("--greenhouse-only", action="store_true")
    parser.add_argument("--lever-only", action="store_true")
    parser.add_argument("--skip-discovery", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    parser.add_argument("--skip-promotion", action="store_true")
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--direct-probe-min-score", type=float, default=0.5)
    parser.add_argument("--direct-probe-min-internship-likelihood", type=float, default=0.12)
    parser.add_argument("--reactivate-inactive-sources", action="store_true")
    return parser.parse_args()


def _should_run_lever(args: argparse.Namespace) -> bool:
    return not args.greenhouse_only


def _should_run_greenhouse(args: argparse.Namespace) -> bool:
    return not args.lever_only


def _run_discovery(args: argparse.Namespace) -> Dict[str, Any]:
    requested_seed_path = PROJECT_ROOT / args.seed_file
    resolved_seed_path = resolve_seed_path(requested_seed_path)
    discovered_path = PROJECT_ROOT / args.discovered_file

    all_seeds = load_json_list(resolved_seed_path)
    seeds = select_seed_subset(
        all_seeds,
        min_priority=args.min_priority,
        max_seeds=args.max_seeds,
    )
    existing_sources = load_json_list(discovered_path)
    checkpoint_size = int(getattr(args, "discovery_checkpoint_size", 25))
    probe_direct_ats = bool(getattr(args, "probe_direct_ats", False))
    record_blocked_sources = bool(getattr(args, "record_blocked_sources", False))
    direct_probe_limit = int(getattr(args, "direct_probe_limit", 1))
    max_direct_probe_identifiers = int(getattr(args, "max_direct_probe_identifiers", 2))
    priority_follow_limit = int(getattr(args, "priority_follow_limit", 5))
    discovered_sources: list[Dict[str, Any]] = []
    errors: list[Dict[str, str]] = []
    merged_sources = list(existing_sources)

    for seed_batch in iter_seed_batches(seeds, checkpoint_size):
        batch_sources, batch_errors = discover_sources(
            seed_batch,
            timeout=args.discovery_timeout,
            probe_direct_ats=probe_direct_ats,
            record_blocked_sources=record_blocked_sources,
            direct_probe_limit=direct_probe_limit,
            max_direct_probe_identifiers=max_direct_probe_identifiers,
            priority_follow_limit=priority_follow_limit,
        )
        discovered_sources = merge_discovered_sources(discovered_sources, batch_sources)
        errors.extend(batch_errors)
        merged_sources = merge_discovered_sources(merged_sources, batch_sources)
        save_json_list(discovered_path, merged_sources)

    if not seeds:
        save_json_list(discovered_path, merged_sources)

    print("##### Discovery step complete #####")
    print(f"Seed file used: {resolved_seed_path}")
    print(f"Seed companies available: {len(all_seeds)}")
    print(f"Seed companies scanned: {len(seeds)}")
    print(f"Checkpoint size: {checkpoint_size}")
    print(f"Discovered source candidates: {len(discovered_sources)}")
    print(f"Total stored candidates: {len(merged_sources)}")
    if discovered_sources:
        print("Discovery method summary:")
        for method, count in summarize_discovery_methods(discovered_sources).items():
            print(f"- {method}: {count}")
    if errors:
        visible_warnings = visible_discovery_warnings(errors)
        print("Warning summary:")
        for reason, count in summarize_discovery_warnings(errors).items():
            print(f"- {reason}: {count}")
        if visible_warnings:
            print("Warnings:")
            for error in visible_warnings:
                print(f"- {format_discovery_warning(error)}")
    print()

    return {
        "seed_path": resolved_seed_path,
        "seeds_available": len(all_seeds),
        "seeds_scanned": len(seeds),
        "discovered_candidates": len(discovered_sources),
        "stored_candidates": len(merged_sources),
        "warnings": errors,
    }


def _run_validation(args: argparse.Namespace) -> Dict[str, int]:
    discovered_path = PROJECT_ROOT / args.discovered_file
    records = load_json_list(discovered_path)
    active_registry_keys = load_active_registry_keys(PROJECT_ROOT)

    validated_records, summary = validate_discovered_sources(
        records,
        timeout=args.validation_timeout,
        limit=args.validation_limit,
        active_registry_keys=active_registry_keys,
        include_non_candidate=args.include_non_candidate,
    )
    save_json_list(discovered_path, validated_records)

    print("##### Validation step complete #####")
    print(f"Sources attempted: {summary['attempted']}")
    print(f"Validated or active: {summary['validated']}")
    print(f"Rejected: {summary['rejected']}")
    print(f"Skipped: {summary['skipped']}")
    print()

    return summary


def _run_promotion(args: argparse.Namespace) -> Dict[str, int]:
    discovered_path = PROJECT_ROOT / args.discovered_file
    lever_registry_path = PROJECT_ROOT / args.lever_registry
    greenhouse_registry_path = PROJECT_ROOT / args.greenhouse_registry

    discovered_records = load_json_list(discovered_path)
    lever_registry = load_json_list(lever_registry_path)
    greenhouse_registry = load_json_list(greenhouse_registry_path)

    updated_discovered, updated_lever, updated_greenhouse, summary = promote_validated_sources(
        discovered_records,
        lever_registry=lever_registry,
        greenhouse_registry=greenhouse_registry,
        min_score=args.promotion_min_score,
        require_internship_signal=not args.allow_non_internship_sources,
        min_internship_likelihood=args.min_internship_likelihood,
        direct_probe_min_score=args.direct_probe_min_score,
        direct_probe_min_internship_likelihood=args.direct_probe_min_internship_likelihood,
        reactivate_inactive_sources=args.reactivate_inactive_sources,
    )

    save_json_list(discovered_path, updated_discovered)
    save_json_list(lever_registry_path, updated_lever)
    save_json_list(greenhouse_registry_path, updated_greenhouse)

    print("##### Promotion step complete #####")
    print(f"Promoted: {summary['promoted']}")
    print(f"Reactivated: {summary['reactivated']}")
    print(f"Already active: {summary['already_active']}")
    print(f"Skipped inactive registry entries: {summary['skipped_inactive']}")
    print(f"Skipped for status: {summary['skipped_status']}")
    print(f"Skipped for score: {summary['skipped_score']}")
    print(f"Skipped for internship signal: {summary['skipped_internship']}")
    print(f"Skipped for direct probe safeguard: {summary['skipped_direct_probe']}")
    print(f"Skipped unsupported: {summary['skipped_unsupported']}")
    print()

    return summary


def _run_refresh(args: argparse.Namespace) -> Dict[str, int]:
    if args.greenhouse_only and args.lever_only:
        raise ValueError("Choose at most one of --greenhouse-only or --lever-only.")

    total_entries = 0
    total_filtered_jobs = 0
    total_processed_jobs = 0

    if _should_run_lever(args):
        print("##### Refreshing Lever sources #####")
        lever_summary = run_lever_registry_fetch(
            registry_path=PROJECT_ROOT / args.lever_registry,
            timeout=args.refresh_timeout,
            limit=args.refresh_limit,
            only_active=not args.refresh_include_inactive,
            project_root=PROJECT_ROOT,
        )
        total_entries += int(lever_summary["entries_fetched"])
        total_filtered_jobs += int(lever_summary["total_filtered_jobs"])
        total_processed_jobs += int(lever_summary["total_processed_jobs"])
        print()

    if _should_run_greenhouse(args):
        print("##### Refreshing Greenhouse sources #####")
        greenhouse_summary = run_greenhouse_registry_fetch(
            registry_path=PROJECT_ROOT / args.greenhouse_registry,
            timeout=args.refresh_timeout,
            limit=args.refresh_limit,
            only_active=not args.refresh_include_inactive,
            internship_only=not args.greenhouse_all_jobs,
            project_root=PROJECT_ROOT,
        )
        total_entries += int(greenhouse_summary["entries_fetched"])
        total_filtered_jobs += int(greenhouse_summary["total_filtered_jobs"])
        total_processed_jobs += int(greenhouse_summary["total_processed_jobs"])
        print()

    print("##### Refresh step complete #####")
    print(f"Registry entries fetched: {total_entries}")
    print(f"Filtered jobs saved: {total_filtered_jobs}")
    print(f"Processed job files saved: {total_processed_jobs}")
    print()

    return {
        "entries_fetched": total_entries,
        "total_filtered_jobs": total_filtered_jobs,
        "total_processed_jobs": total_processed_jobs,
    }


def main() -> None:
    args = _parse_args()

    if args.greenhouse_only and args.lever_only:
        raise ValueError("Choose at most one of --greenhouse-only or --lever-only.")

    if not args.skip_discovery:
        _run_discovery(args)

    if not args.skip_validation:
        _run_validation(args)

    if not args.skip_promotion:
        _run_promotion(args)

    if not args.skip_refresh:
        _run_refresh(args)

    print("##### Source pipeline complete #####")


if __name__ == "__main__":
    main()
