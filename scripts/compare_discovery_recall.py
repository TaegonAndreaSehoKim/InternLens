from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.discovery.source_discovery import (
    discover_sources,
    load_json_list,
    resolve_seed_path,
    summarize_discovery_methods,
    summarize_discovery_warnings,
    utc_now_iso,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare source discovery recall with and without priority-link following."
    )
    parser.add_argument("--seed-file", default="data/source_registry/company_seeds.json")
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--seed-limit", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--baseline-priority-follow-limit", type=int, default=0)
    parser.add_argument("--priority-follow-limit", type=int, default=5)
    parser.add_argument("--probe-direct-ats", action="store_true")
    parser.add_argument("--record-blocked-sources", action="store_true")
    parser.add_argument("--direct-probe-limit", type=int, default=1)
    parser.add_argument("--max-direct-probe-identifiers", type=int, default=2)
    parser.add_argument(
        "--output-file",
        default="outputs/discovery_recall_compare.json",
        help="Path for the comparison JSON report, relative to the project root.",
    )
    return parser.parse_args()


def _source_key(record: Dict[str, Any]) -> tuple[str, str]:
    return (
        str(record.get("source_type", "")).strip(),
        str(record.get("source_identifier", "")).strip(),
    )


def _source_label(record: Dict[str, Any]) -> str:
    return (
        f"{record.get('company', '')} | {record.get('source_type', '')} | "
        f"{record.get('source_identifier', '')} | method={record.get('discovery_method', '')}"
    )


def _select_seeds(
    seeds: Sequence[Dict[str, Any]],
    *,
    offset: int,
    limit: int,
) -> List[Dict[str, Any]]:
    start = max(0, offset)
    if limit <= 0:
        return list(seeds[start:])
    return list(seeds[start : start + limit])


def _run_discovery(
    seeds: Sequence[Dict[str, Any]],
    *,
    timeout: float,
    priority_follow_limit: int,
    probe_direct_ats: bool,
    record_blocked_sources: bool,
    direct_probe_limit: int,
    max_direct_probe_identifiers: int,
    discovered_at: str,
) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    return discover_sources(
        seeds,
        timeout=timeout,
        priority_follow_limit=priority_follow_limit,
        probe_direct_ats=probe_direct_ats,
        record_blocked_sources=record_blocked_sources,
        direct_probe_limit=direct_probe_limit,
        max_direct_probe_identifiers=max_direct_probe_identifiers,
        discovered_at=discovered_at,
    )


def _summarize_run(
    *,
    records: Sequence[Dict[str, Any]],
    warnings: Sequence[Dict[str, str]],
) -> Dict[str, Any]:
    return {
        "candidate_count": len(records),
        "method_summary": summarize_discovery_methods(records),
        "warning_count": len(warnings),
        "warning_summary": summarize_discovery_warnings(warnings),
    }


def build_recall_comparison(
    *,
    seeds: Sequence[Dict[str, Any]],
    timeout: float,
    baseline_priority_follow_limit: int,
    priority_follow_limit: int,
    probe_direct_ats: bool,
    record_blocked_sources: bool,
    direct_probe_limit: int,
    max_direct_probe_identifiers: int,
    discovered_at: str | None = None,
) -> Dict[str, Any]:
    discovered_at_value = discovered_at or utc_now_iso()
    baseline_records, baseline_warnings = _run_discovery(
        seeds,
        timeout=timeout,
        priority_follow_limit=baseline_priority_follow_limit,
        probe_direct_ats=probe_direct_ats,
        record_blocked_sources=record_blocked_sources,
        direct_probe_limit=direct_probe_limit,
        max_direct_probe_identifiers=max_direct_probe_identifiers,
        discovered_at=discovered_at_value,
    )
    follow_records, follow_warnings = _run_discovery(
        seeds,
        timeout=timeout,
        priority_follow_limit=priority_follow_limit,
        probe_direct_ats=probe_direct_ats,
        record_blocked_sources=record_blocked_sources,
        direct_probe_limit=direct_probe_limit,
        max_direct_probe_identifiers=max_direct_probe_identifiers,
        discovered_at=discovered_at_value,
    )

    baseline_by_key = {_source_key(record): record for record in baseline_records}
    follow_by_key = {_source_key(record): record for record in follow_records}
    added_keys = sorted(set(follow_by_key) - set(baseline_by_key))
    removed_keys = sorted(set(baseline_by_key) - set(follow_by_key))

    return {
        "generated_at": utc_now_iso(),
        "config": {
            "seed_count": len(seeds),
            "timeout": timeout,
            "baseline_priority_follow_limit": baseline_priority_follow_limit,
            "priority_follow_limit": priority_follow_limit,
            "probe_direct_ats": probe_direct_ats,
            "record_blocked_sources": record_blocked_sources,
            "direct_probe_limit": direct_probe_limit,
            "max_direct_probe_identifiers": max_direct_probe_identifiers,
        },
        "baseline": _summarize_run(records=baseline_records, warnings=baseline_warnings),
        "priority_follow": _summarize_run(records=follow_records, warnings=follow_warnings),
        "delta": {
            "candidate_count": len(follow_records) - len(baseline_records),
            "warning_count": len(follow_warnings) - len(baseline_warnings),
            "added_source_count": len(added_keys),
            "removed_source_count": len(removed_keys),
        },
        "added_sources": [follow_by_key[key] for key in added_keys],
        "removed_sources": [baseline_by_key[key] for key in removed_keys],
    }


def _write_report(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _print_summary(report: Dict[str, Any], output_path: Path) -> None:
    baseline = report["baseline"]
    priority_follow = report["priority_follow"]
    delta = report["delta"]

    print("##### Discovery recall comparison complete #####")
    print(f"Report written: {output_path}")
    print(f"Seeds compared: {report['config']['seed_count']}")
    print(
        "Candidate count: "
        f"{baseline['candidate_count']} -> {priority_follow['candidate_count']} "
        f"(delta {delta['candidate_count']:+d})"
    )
    print(
        "Warning count: "
        f"{baseline['warning_count']} -> {priority_follow['warning_count']} "
        f"(delta {delta['warning_count']:+d})"
    )
    print("Baseline method summary:")
    for method, count in baseline["method_summary"].items():
        print(f"- {method}: {count}")
    print("Priority-follow method summary:")
    for method, count in priority_follow["method_summary"].items():
        print(f"- {method}: {count}")

    if report["added_sources"]:
        print("Added sources:")
        for record in report["added_sources"]:
            print(f"- {_source_label(record)}")
    else:
        print("Added sources: none")


def main() -> None:
    args = _parse_args()
    seed_path = resolve_seed_path(PROJECT_ROOT / args.seed_file)
    output_path = PROJECT_ROOT / args.output_file
    seeds = _select_seeds(
        load_json_list(seed_path),
        offset=args.seed_offset,
        limit=args.seed_limit,
    )

    report = build_recall_comparison(
        seeds=seeds,
        timeout=args.timeout,
        baseline_priority_follow_limit=args.baseline_priority_follow_limit,
        priority_follow_limit=args.priority_follow_limit,
        probe_direct_ats=args.probe_direct_ats,
        record_blocked_sources=args.record_blocked_sources,
        direct_probe_limit=args.direct_probe_limit,
        max_direct_probe_identifiers=args.max_direct_probe_identifiers,
    )
    _write_report(output_path, report)
    _print_summary(report, output_path)


if __name__ == "__main__":
    main()
