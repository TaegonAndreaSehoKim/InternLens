from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
    parser.add_argument(
        "--min-successful-sources",
        type=int,
        default=1,
        help="Minimum source boards that must refresh successfully.",
    )
    parser.add_argument(
        "--max-failed-sources",
        type=int,
        default=0,
        help="Maximum source board failures allowed after retries.",
    )
    parser.add_argument(
        "--report-file",
        default=None,
        help="Optional JSON refresh report path, relative to the project root.",
    )
    return parser.parse_args()


def _should_run_lever(args: argparse.Namespace) -> bool:
    return not args.greenhouse_only


def _should_run_greenhouse(args: argparse.Namespace) -> bool:
    return not args.lever_only


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_project_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _source_records(summary: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    records = summary.get(key, [])
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def run_refresh(args: argparse.Namespace) -> Dict[str, Any]:
    min_successful_sources = int(getattr(args, "min_successful_sources", 1))
    max_failed_sources = int(getattr(args, "max_failed_sources", 0))

    if min_successful_sources < 0:
        raise ValueError("--min-successful-sources must be greater than or equal to 0.")
    if max_failed_sources < 0:
        raise ValueError("--max-failed-sources must be greater than or equal to 0.")

    if args.greenhouse_only and args.lever_only:
        raise ValueError("Choose at most one of --greenhouse-only or --lever-only.")

    started_at = _utc_now_iso()
    provider_summaries: Dict[str, Dict[str, Any]] = {}
    successful_sources: List[Dict[str, Any]] = []
    failed_sources: List[Dict[str, Any]] = []
    total_entries_selected = 0
    total_entries = 0
    total_entries_failed = 0
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
        provider_summaries["lever"] = lever_summary
        total_entries_selected += int(
            lever_summary.get("entries_selected", lever_summary["entries_fetched"])
        )
        total_entries += int(lever_summary["entries_fetched"])
        total_entries_failed += int(lever_summary.get("entries_failed", 0))
        total_filtered_jobs += int(lever_summary["total_filtered_jobs"])
        total_processed_jobs += int(lever_summary["total_processed_jobs"])
        successful_sources.extend(_source_records(lever_summary, "successful_sources"))
        failed_sources.extend(_source_records(lever_summary, "failed_sources"))
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
        provider_summaries["greenhouse"] = greenhouse_summary
        total_entries_selected += int(
            greenhouse_summary.get("entries_selected", greenhouse_summary["entries_fetched"])
        )
        total_entries += int(greenhouse_summary["entries_fetched"])
        total_entries_failed += int(greenhouse_summary.get("entries_failed", 0))
        total_filtered_jobs += int(greenhouse_summary["total_filtered_jobs"])
        total_processed_jobs += int(greenhouse_summary["total_processed_jobs"])
        successful_sources.extend(_source_records(greenhouse_summary, "successful_sources"))
        failed_sources.extend(_source_records(greenhouse_summary, "failed_sources"))
        print()

    ok = total_entries >= min_successful_sources and total_entries_failed <= max_failed_sources
    report = {
        "started_at": started_at,
        "completed_at": _utc_now_iso(),
        "policy": {
            "min_successful_sources": min_successful_sources,
            "max_failed_sources": max_failed_sources,
        },
        "entries_selected": total_entries_selected,
        "successful_source_count": total_entries,
        "failed_source_count": total_entries_failed,
        "total_filtered_jobs": total_filtered_jobs,
        "total_processed_jobs": total_processed_jobs,
        "successful_sources": successful_sources,
        "failed_sources": failed_sources,
        "provider_summaries": provider_summaries,
        "ok": ok,
    }

    report_file = getattr(args, "report_file", None)
    if report_file:
        report_path = _resolve_project_path(report_file)
        _write_report(report_path, report)
    else:
        report_path = None

    print("##### Corpus refresh complete #####")
    print(f"Registry entries selected: {total_entries_selected}")
    print(f"Registry entries fetched: {total_entries}")
    print(f"Registry entries failed: {total_entries_failed}")
    print(f"Filtered jobs saved: {total_filtered_jobs}")
    print(f"Processed job files saved: {total_processed_jobs}")
    print(f"Minimum successful sources: {min_successful_sources}")
    print(f"Maximum failed sources: {max_failed_sources}")
    if report_path is not None:
        print(f"Refresh report: {report_path}")
    print(f"Overall: {'passed' if ok else 'failed'}")

    return report


def main() -> None:
    args = _parse_args()
    report = run_refresh(args)

    if not report["ok"]:
        raise SystemExit(
            "Corpus refresh policy failed: "
            f"{report['successful_source_count']} successful source(s), "
            f"{report['failed_source_count']} failed source(s), "
            f"minimum successful is {report['policy']['min_successful_sources']} and "
            f"maximum failed is {report['policy']['max_failed_sources']}."
        )


if __name__ == "__main__":
    main()
