from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence

from src.ingestion.greenhouse_client import fetch_greenhouse_jobs, normalize_greenhouse_job
from src.ingestion.lever_client import fetch_lever_postings, normalize_lever_posting

from .source_discovery import load_json_list, utc_now_iso


def _looks_like_greenhouse_internship(job: Dict[str, Any]) -> bool:
    title = str(job.get("title", "")).lower()
    content = str(job.get("content", "")).lower()
    return any(
        marker in f"{title} {content}"
        for marker in (" intern ", " internship", "co-op", "co op", "summer internship")
    ) or title.startswith("intern") or " intern" in title


def _looks_like_lever_internship(job: Dict[str, Any]) -> bool:
    title = str(job.get("text", "")).lower()
    description = str(job.get("descriptionPlain", "")).lower()
    categories = job.get("categories", {})
    commitment = ""
    if isinstance(categories, dict):
        commitment = str(categories.get("commitment", "")).lower()
    combined = f"{title} {description} {commitment}"
    return any(marker in combined for marker in ("intern", "internship", "summer intern", "student intern"))


def _iter_normalized_jobs(
    raw_jobs: Iterable[Dict[str, Any]],
    *,
    source_type: str,
    source_identifier: str,
    lever_normalize_fn: Callable[[Dict[str, Any], str], Dict[str, Any]],
    greenhouse_normalize_fn: Callable[[Dict[str, Any], str], Dict[str, Any]],
) -> tuple[int, int]:
    normalized_count = 0
    failed_count = 0

    for raw_job in raw_jobs:
        try:
            if source_type == "lever":
                lever_normalize_fn(raw_job, source_identifier)
            else:
                greenhouse_normalize_fn(raw_job, source_identifier)
            normalized_count += 1
        except Exception:
            failed_count += 1

    return normalized_count, failed_count


def load_active_registry_keys(project_root: Path) -> set[tuple[str, str]]:
    active_keys: set[tuple[str, str]] = set()

    lever_path = project_root / "data" / "source_registry" / "lever_targets.json"
    for entry in load_json_list(lever_path):
        if not bool(entry.get("active", True)):
            continue
        site_name = str(entry.get("site_name", "")).strip()
        if site_name:
            active_keys.add(("lever", site_name))

    greenhouse_path = project_root / "data" / "source_registry" / "greenhouse_targets.json"
    for entry in load_json_list(greenhouse_path):
        if not bool(entry.get("active", True)):
            continue
        board_token = str(entry.get("board_token", "")).strip()
        if board_token:
            active_keys.add(("greenhouse", board_token))

    return active_keys


def _status_after_validation(previous_status: str, *, success: bool) -> str:
    normalized_previous = previous_status.strip().lower() or "candidate"

    if normalized_previous == "active":
        return "active" if success else "inactive"
    if normalized_previous == "inactive":
        return "inactive"
    if normalized_previous == "validated" and success:
        return "validated"
    return "validated" if success else "rejected"


def _score_source(
    *,
    internship_likelihood: float,
    normalized_ratio: float,
    duplicate_in_active_registry: bool,
) -> float:
    score = (internship_likelihood * 0.6) + (normalized_ratio * 0.3) + 0.1
    if duplicate_in_active_registry:
        score -= 0.15
    return round(max(0.0, min(score, 1.0)), 2)


def validate_source_record(
    record: Dict[str, Any],
    *,
    timeout: float,
    limit: int | None,
    active_registry_keys: set[tuple[str, str]],
    validated_at: str | None = None,
    lever_fetch_fn: Callable[..., List[Dict[str, Any]]] = fetch_lever_postings,
    greenhouse_fetch_fn: Callable[..., List[Dict[str, Any]]] = fetch_greenhouse_jobs,
    lever_normalize_fn: Callable[[Dict[str, Any], str], Dict[str, Any]] = normalize_lever_posting,
    greenhouse_normalize_fn: Callable[[Dict[str, Any], str], Dict[str, Any]] = normalize_greenhouse_job,
) -> Dict[str, Any]:
    updated = dict(record)
    source_type = str(record.get("source_type", "")).strip().lower()
    source_identifier = str(record.get("source_identifier", "")).strip()
    previous_status = str(record.get("status", "candidate"))
    validated_at_value = validated_at or utc_now_iso()

    updated["last_validated_at"] = validated_at_value

    if source_type not in {"lever", "greenhouse"} or not source_identifier:
        updated["status"] = _status_after_validation(previous_status, success=False)
        updated["validation_notes"] = "unsupported source type or missing source identifier"
        updated["source_score"] = 0.0
        updated["internship_likelihood"] = 0.0
        return updated

    duplicate_in_active_registry = (source_type, source_identifier) in active_registry_keys

    try:
        if source_type == "lever":
            raw_jobs = lever_fetch_fn(source_identifier, timeout=timeout, limit=limit)
            internship_count = sum(1 for job in raw_jobs if _looks_like_lever_internship(job))
        else:
            raw_jobs = greenhouse_fetch_fn(source_identifier, timeout=timeout, limit=limit, content=True)
            internship_count = sum(1 for job in raw_jobs if _looks_like_greenhouse_internship(job))
    except Exception as exc:
        updated["status"] = _status_after_validation(previous_status, success=False)
        updated["validation_notes"] = f"fetch failed: {exc}"
        updated["source_score"] = 0.0
        updated["internship_likelihood"] = 0.0
        return updated

    total_jobs = len(raw_jobs)
    if total_jobs == 0:
        updated["status"] = _status_after_validation(previous_status, success=False)
        updated["validation_notes"] = "fetch succeeded but returned no jobs"
        updated["source_score"] = 0.0
        updated["internship_likelihood"] = 0.0
        return updated

    normalized_count, failed_count = _iter_normalized_jobs(
        raw_jobs,
        source_type=source_type,
        source_identifier=source_identifier,
        lever_normalize_fn=lever_normalize_fn,
        greenhouse_normalize_fn=greenhouse_normalize_fn,
    )

    internship_likelihood = round(internship_count / total_jobs, 2)
    normalized_ratio = normalized_count / total_jobs
    success = normalized_count > 0

    note_parts = [
        f"fetch succeeded with {total_jobs} jobs",
        f"normalized {normalized_count}/{total_jobs}",
        f"internship density {internship_likelihood:.2f}",
    ]
    if failed_count:
        note_parts.append(f"{failed_count} normalization failures")
    if duplicate_in_active_registry:
        note_parts.append("already present in active registry")

    updated["status"] = _status_after_validation(previous_status, success=success)
    updated["validation_notes"] = "; ".join(note_parts)
    updated["source_score"] = _score_source(
        internship_likelihood=internship_likelihood,
        normalized_ratio=normalized_ratio,
        duplicate_in_active_registry=duplicate_in_active_registry,
    )
    updated["internship_likelihood"] = internship_likelihood
    return updated


def validate_discovered_sources(
    records: Sequence[Dict[str, Any]],
    *,
    timeout: float,
    limit: int | None,
    active_registry_keys: set[tuple[str, str]],
    include_non_candidate: bool,
    validated_at: str | None = None,
    lever_fetch_fn: Callable[..., List[Dict[str, Any]]] = fetch_lever_postings,
    greenhouse_fetch_fn: Callable[..., List[Dict[str, Any]]] = fetch_greenhouse_jobs,
    lever_normalize_fn: Callable[[Dict[str, Any], str], Dict[str, Any]] = normalize_lever_posting,
    greenhouse_normalize_fn: Callable[[Dict[str, Any], str], Dict[str, Any]] = normalize_greenhouse_job,
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    validated_records: List[Dict[str, Any]] = []
    attempted = 0
    succeeded = 0
    rejected = 0
    skipped = 0

    for record in records:
        status = str(record.get("status", "candidate")).strip().lower()
        should_validate = include_non_candidate or status == "candidate"

        if not should_validate:
            validated_records.append(dict(record))
            skipped += 1
            continue

        attempted += 1
        updated = validate_source_record(
            record,
            timeout=timeout,
            limit=limit,
            active_registry_keys=active_registry_keys,
            validated_at=validated_at,
            lever_fetch_fn=lever_fetch_fn,
            greenhouse_fetch_fn=greenhouse_fetch_fn,
            lever_normalize_fn=lever_normalize_fn,
            greenhouse_normalize_fn=greenhouse_normalize_fn,
        )
        validated_records.append(updated)

        updated_status = str(updated.get("status", "")).strip().lower()
        if updated_status in {"validated", "active"}:
            succeeded += 1
        elif updated_status == "rejected":
            rejected += 1

    return validated_records, {
        "attempted": attempted,
        "validated": succeeded,
        "rejected": rejected,
        "skipped": skipped,
    }
