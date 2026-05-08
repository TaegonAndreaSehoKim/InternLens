from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

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
    parser.add_argument(
        "--checkpoint-size",
        type=int,
        default=25,
        help="Save merged discovery output after this many seed companies. Use 0 to save only at the end.",
    )
    parser.add_argument(
        "--min-priority",
        type=int,
        default=None,
        help="Only scan seed companies whose priority is at least this value.",
    )
    parser.add_argument(
        "--max-seeds",
        type=int,
        default=None,
        help="Scan at most this many seed companies, preferring higher-priority seeds.",
    )
    parser.add_argument(
        "--probe-direct-ats",
        action="store_true",
        help="Try a small number of seed-derived Lever/Greenhouse board tokens when page scanning finds no source.",
    )
    parser.add_argument(
        "--record-blocked-sources",
        action="store_true",
        help="Record blocked or rate-limited seed pages as manual_review records for later operator review.",
    )
    parser.add_argument(
        "--direct-probe-limit",
        type=int,
        default=1,
        help="Maximum jobs to fetch per direct ATS probe.",
    )
    parser.add_argument(
        "--max-direct-probe-identifiers",
        type=int,
        default=2,
        help="Maximum seed-derived source identifiers to probe per company.",
    )
    parser.add_argument(
        "--priority-follow-limit",
        type=int,
        default=5,
        help="Maximum same-site high-intent links to follow per company during discovery.",
    )
    parser.add_argument(
        "--priority-follow-warning-budget",
        type=int,
        default=8,
        help="Maximum failed priority-link fetches allowed per company before suppressing remaining priority links.",
    )
    parser.add_argument(
        "--priority-follow-domain-warning-budget",
        type=int,
        default=2,
        help="Maximum failed priority-link fetches allowed per same-site domain per company.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    requested_seed_path = PROJECT_ROOT / args.seed_file
    resolved_seed_path = resolve_seed_path(requested_seed_path)
    output_path = PROJECT_ROOT / args.output_file

    all_seeds = load_json_list(resolved_seed_path)
    seeds = select_seed_subset(
        all_seeds,
        min_priority=args.min_priority,
        max_seeds=args.max_seeds,
    )
    existing_sources = load_json_list(output_path)
    checkpoint_size = int(getattr(args, "checkpoint_size", 25))
    probe_direct_ats = bool(getattr(args, "probe_direct_ats", False))
    record_blocked_sources = bool(getattr(args, "record_blocked_sources", False))
    direct_probe_limit = int(getattr(args, "direct_probe_limit", 1))
    max_direct_probe_identifiers = int(getattr(args, "max_direct_probe_identifiers", 2))
    priority_follow_limit = int(getattr(args, "priority_follow_limit", 5))
    priority_follow_warning_budget = int(getattr(args, "priority_follow_warning_budget", 8))
    priority_follow_domain_warning_budget = int(getattr(args, "priority_follow_domain_warning_budget", 2))
    discovered_sources = []
    errors = []
    merged_sources = list(existing_sources)

    for seed_batch in iter_seed_batches(seeds, checkpoint_size):
        batch_sources, batch_errors = discover_sources(
            seed_batch,
            timeout=args.timeout,
            probe_direct_ats=probe_direct_ats,
            record_blocked_sources=record_blocked_sources,
            direct_probe_limit=direct_probe_limit,
            max_direct_probe_identifiers=max_direct_probe_identifiers,
            priority_follow_limit=priority_follow_limit,
            priority_follow_warning_budget=priority_follow_warning_budget,
            priority_follow_domain_warning_budget=priority_follow_domain_warning_budget,
        )
        discovered_sources = merge_discovered_sources(discovered_sources, batch_sources)
        errors.extend(batch_errors)
        merged_sources = merge_discovered_sources(merged_sources, batch_sources)
        save_json_list(output_path, merged_sources)

    if not seeds:
        save_json_list(output_path, merged_sources)

    print("##### Source discovery complete #####")
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


if __name__ == "__main__":
    main()
