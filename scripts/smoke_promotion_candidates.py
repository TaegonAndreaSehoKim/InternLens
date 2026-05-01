from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.fetch_greenhouse_registry import run_registry_fetch as run_greenhouse_registry_fetch
from scripts.fetch_lever_registry import run_registry_fetch as run_lever_registry_fetch
from src.discovery.source_discovery import load_json_list, save_json_list, utc_now_iso
from src.discovery.source_promotion import promote_validated_sources
from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import load_candidate_profile
from src.ranking.baseline_scorer import rank_jobs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test discovered-source promotion candidates through fetch and ranking in a temp workspace."
    )
    parser.add_argument("--input-file", default="data/source_registry/discovered_sources.json")
    parser.add_argument("--lever-registry", default="data/source_registry/lever_targets.json")
    parser.add_argument("--greenhouse-registry", default="data/source_registry/greenhouse_targets.json")
    parser.add_argument("--profile-path", default="data/processed/candidate_profile_example.json")
    parser.add_argument("--output-file", default="outputs/promotion_candidate_smoke.json")
    parser.add_argument("--min-score", type=float, default=0.45)
    parser.add_argument("--allow-non-internship-sources", action="store_true")
    parser.add_argument("--min-internship-likelihood", type=float, default=0.08)
    parser.add_argument("--direct-probe-min-score", type=float, default=0.5)
    parser.add_argument("--direct-probe-min-internship-likelihood", type=float, default=0.12)
    parser.add_argument("--reactivate-inactive-sources", action="store_true")
    parser.add_argument("--fetch-timeout", type=float, default=60.0)
    parser.add_argument("--fetch-limit", type=int, default=None)
    parser.add_argument("--greenhouse-all-jobs", action="store_true")
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def _registry_key(record: Dict[str, Any]) -> tuple[str, str]:
    source_type = str(record.get("source_type", "")).strip().lower()
    if source_type == "lever":
        return source_type, str(record.get("site_name", "")).strip()
    if source_type == "greenhouse":
        return source_type, str(record.get("board_token", "")).strip()
    return source_type, ""


def _source_key(record: Dict[str, Any]) -> tuple[str, str]:
    return (
        str(record.get("source_type", "")).strip().lower(),
        str(record.get("source_identifier", "")).strip(),
    )


def _candidate_keys(
    original_records: Sequence[Dict[str, Any]],
    updated_records: Sequence[Dict[str, Any]],
) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for original, updated in zip(original_records, updated_records):
        if str(original.get("status", "")).strip().lower() == "active":
            continue
        if str(updated.get("status", "")).strip().lower() != "active":
            continue
        key = _source_key(updated)
        if all(key):
            keys.add(key)
    return keys


def _filter_registry_for_candidates(
    registry: Sequence[Dict[str, Any]],
    candidate_keys: set[tuple[str, str]],
    *,
    source_type: str,
) -> List[Dict[str, Any]]:
    return [
        dict(entry)
        for entry in registry
        if _registry_key({"source_type": source_type, **entry}) in candidate_keys
    ]


def _promotion_candidate_records(
    records: Sequence[Dict[str, Any]],
    candidate_keys: set[tuple[str, str]],
) -> List[Dict[str, Any]]:
    return [dict(record) for record in records if _source_key(record) in candidate_keys]


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _rank_temp_jobs(
    *,
    temp_root: Path,
    profile_path: Path,
    top_k: int,
) -> Dict[str, Any]:
    jobs_root = temp_root / "data" / "processed" / "jobs"
    if not jobs_root.exists():
        return {
            "processed_jobs": 0,
            "action_counts": {},
            "blocker_counts": {},
            "top_results": [],
        }

    try:
        jobs = load_all_job_postings(jobs_root)
    except ValueError:
        return {
            "processed_jobs": 0,
            "action_counts": {},
            "blocker_counts": {},
            "top_results": [],
        }

    profile = load_candidate_profile(profile_path)
    ranked = rank_jobs(profile, jobs)
    action_counts = Counter(str(job.get("action_label", "")) for job in ranked)
    blocker_counts = Counter(
        str(blocker)
        for job in ranked
        for blocker in job.get("blocking_issues", [])
    )

    return {
        "processed_jobs": len(jobs),
        "action_counts": dict(sorted(action_counts.items())),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "top_results": [
            {
                "company": job.get("company", ""),
                "title": job.get("title", ""),
                "score": job.get("score", 0),
                "action_label": job.get("action_label", ""),
                "blocking_issues": job.get("blocking_issues", []),
                "source": job.get("source", ""),
                "source_site": job.get("source_site", ""),
            }
            for job in ranked[: max(0, top_k)]
        ],
    }


def build_promotion_candidate_smoke(
    *,
    discovered_records: Sequence[Dict[str, Any]],
    lever_registry: Sequence[Dict[str, Any]],
    greenhouse_registry: Sequence[Dict[str, Any]],
    profile_path: Path,
    min_score: float,
    require_internship_signal: bool,
    min_internship_likelihood: float,
    direct_probe_min_score: float,
    direct_probe_min_internship_likelihood: float,
    reactivate_inactive_sources: bool,
    fetch_timeout: float,
    fetch_limit: int | None,
    greenhouse_all_jobs: bool,
    top_k: int,
) -> Dict[str, Any]:
    promoted_at = utc_now_iso()
    updated_records, updated_lever, updated_greenhouse, promotion_summary = promote_validated_sources(
        discovered_records,
        lever_registry=lever_registry,
        greenhouse_registry=greenhouse_registry,
        min_score=min_score,
        require_internship_signal=require_internship_signal,
        min_internship_likelihood=min_internship_likelihood,
        direct_probe_min_score=direct_probe_min_score,
        direct_probe_min_internship_likelihood=direct_probe_min_internship_likelihood,
        reactivate_inactive_sources=reactivate_inactive_sources,
        promoted_at=promoted_at,
    )

    candidate_keys = _candidate_keys(discovered_records, updated_records)
    candidate_records = _promotion_candidate_records(updated_records, candidate_keys)
    candidate_lever = _filter_registry_for_candidates(updated_lever, candidate_keys, source_type="lever")
    candidate_greenhouse = _filter_registry_for_candidates(
        updated_greenhouse,
        candidate_keys,
        source_type="greenhouse",
    )

    with tempfile.TemporaryDirectory(prefix="internlens-promotion-smoke-") as temp_dir:
        temp_root = Path(temp_dir)
        registry_dir = temp_root / "data" / "source_registry"
        lever_path = registry_dir / "lever_targets.json"
        greenhouse_path = registry_dir / "greenhouse_targets.json"
        save_json_list(lever_path, candidate_lever)
        save_json_list(greenhouse_path, candidate_greenhouse)

        lever_fetch_summary = run_lever_registry_fetch(
            registry_path=lever_path,
            timeout=fetch_timeout,
            limit=fetch_limit,
            only_active=True,
            project_root=temp_root,
        )
        greenhouse_fetch_summary = run_greenhouse_registry_fetch(
            registry_path=greenhouse_path,
            timeout=fetch_timeout,
            limit=fetch_limit,
            only_active=True,
            internship_only=not greenhouse_all_jobs,
            project_root=temp_root,
        )
        ranking_summary = _rank_temp_jobs(
            temp_root=temp_root,
            profile_path=profile_path,
            top_k=top_k,
        )

    return {
        "generated_at": utc_now_iso(),
        "promotion_summary": promotion_summary,
        "candidate_count": len(candidate_records),
        "candidate_sources": candidate_records,
        "fetch_summary": {
            "lever": lever_fetch_summary,
            "greenhouse": greenhouse_fetch_summary,
            "total_entries_fetched": int(lever_fetch_summary["entries_fetched"])
            + int(greenhouse_fetch_summary["entries_fetched"]),
            "total_processed_jobs": int(lever_fetch_summary["total_processed_jobs"])
            + int(greenhouse_fetch_summary["total_processed_jobs"]),
        },
        "ranking_summary": ranking_summary,
    }


def _print_summary(report: Dict[str, Any], output_path: Path) -> None:
    print("##### Promotion candidate smoke complete #####")
    print(f"Report written: {output_path}")
    print(f"Promotion candidates: {report['candidate_count']}")
    print(f"Promotion summary: {report['promotion_summary']}")
    print(f"Processed jobs: {report['ranking_summary']['processed_jobs']}")
    print(f"Action counts: {report['ranking_summary']['action_counts']}")
    print(f"Blocker counts: {report['ranking_summary']['blocker_counts']}")
    if report["candidate_sources"]:
        print("Candidate sources:")
        for record in report["candidate_sources"]:
            print(
                f"- {record.get('company', '')} | {record.get('source_type', '')} | "
                f"{record.get('source_identifier', '')}"
            )


def main() -> None:
    args = _parse_args()
    input_path = PROJECT_ROOT / args.input_file
    lever_registry_path = PROJECT_ROOT / args.lever_registry
    greenhouse_registry_path = PROJECT_ROOT / args.greenhouse_registry
    profile_path = PROJECT_ROOT / args.profile_path
    output_path = PROJECT_ROOT / args.output_file

    report = build_promotion_candidate_smoke(
        discovered_records=load_json_list(input_path),
        lever_registry=load_json_list(lever_registry_path),
        greenhouse_registry=load_json_list(greenhouse_registry_path),
        profile_path=profile_path,
        min_score=args.min_score,
        require_internship_signal=not args.allow_non_internship_sources,
        min_internship_likelihood=args.min_internship_likelihood,
        direct_probe_min_score=args.direct_probe_min_score,
        direct_probe_min_internship_likelihood=args.direct_probe_min_internship_likelihood,
        reactivate_inactive_sources=args.reactivate_inactive_sources,
        fetch_timeout=args.fetch_timeout,
        fetch_limit=args.fetch_limit,
        greenhouse_all_jobs=args.greenhouse_all_jobs,
        top_k=args.top_k,
    )
    _write_json(output_path, report)
    _print_summary(report, output_path)


if __name__ == "__main__":
    main()
