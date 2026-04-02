from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_JOB_FIELDS = [
    "job_id",
    "company",
    "title",
    "location",
    "description",
    "min_qualifications",
    "preferred_qualifications",
    "posting_date",
    "sponsorship_info",
    "employment_type",
    "source",
]


def _coerce_text(value: Any) -> str:
    # Convert nullable values into normalized strings.
    if value is None:
        return ""
    return str(value).strip()


def _normalize_compare_text(value: Any) -> str:
    # Normalize text for conservative duplicate comparisons.
    return " ".join(str(value or "").strip().lower().split())


def _normalize_compare_url(value: Any) -> str:
    # Normalize URLs while preserving query strings that identify postings.
    url = _normalize_compare_text(value)
    return url.rstrip("/")


TITLE_TOKEN_ALIASES = {
    "ops": "operations",
}


def _title_tokens(title: str) -> set[str]:
    # Compare titles using alphanumeric tokens only.
    return {
        TITLE_TOKEN_ALIASES.get(token, token)
        for token in re.findall(r"[a-z0-9]+", _normalize_compare_text(title))
    }


def _title_similarity(left_title: str, right_title: str) -> float:
    # Use a simple token overlap score for near-identical title detection.
    left_tokens = _title_tokens(left_title)
    right_tokens = _title_tokens(right_title)

    if not left_tokens or not right_tokens:
        return 0.0

    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return overlap / union


def _relative_directory_depth(root: Path, file_path: Path) -> int:
    # Prefer jobs saved under nested source/site folders over legacy flat files.
    relative_path = file_path.relative_to(root)
    return max(len(relative_path.parts) - 1, 0)


def _should_prefer_job_file(root: Path, existing_path: Path, candidate_path: Path) -> bool:
    # When duplicate job_ids appear, treat deeper source-aware paths as canonical.
    existing_depth = _relative_directory_depth(root, existing_path)
    candidate_depth = _relative_directory_depth(root, candidate_path)

    if candidate_depth != existing_depth:
        return candidate_depth > existing_depth

    # For same-depth duplicates, keep the first deterministic match encountered.
    return False


def _job_richness_score(job: Dict[str, Any]) -> int:
    # Prefer records with more populated metadata and longer descriptive text.
    weighted_fields = [
        "description",
        "min_qualifications",
        "preferred_qualifications",
        "source_url",
        "application_url",
        "team",
        "remote_status",
        "posting_date",
        "employment_type",
    ]

    score = 0
    for field in weighted_fields:
        value = _coerce_text(job.get(field, ""))
        if value:
            score += 10
            score += min(len(value), 200)

    return score


def _jobs_share_duplicate_content(existing_job: Dict[str, Any], candidate_job: Dict[str, Any]) -> bool:
    # Suppress only conservative duplicates so multi-location postings survive.
    existing_url = _normalize_compare_url(existing_job.get("source_url", ""))
    candidate_url = _normalize_compare_url(candidate_job.get("source_url", ""))

    if existing_url and candidate_url and existing_url == candidate_url:
        return True

    if _normalize_compare_text(existing_job.get("source", "")) != _normalize_compare_text(
        candidate_job.get("source", "")
    ):
        return False

    existing_source_site = _normalize_compare_text(existing_job.get("source_site", ""))
    candidate_source_site = _normalize_compare_text(candidate_job.get("source_site", ""))
    if (
        existing_source_site
        and candidate_source_site
        and existing_source_site != candidate_source_site
    ):
        return False

    if _normalize_compare_text(existing_job.get("company", "")) != _normalize_compare_text(
        candidate_job.get("company", "")
    ):
        return False

    if _normalize_compare_text(existing_job.get("location", "")) != _normalize_compare_text(
        candidate_job.get("location", "")
    ):
        return False

    return _title_similarity(existing_job.get("title", ""), candidate_job.get("title", "")) >= 0.9


def _should_prefer_duplicate_content(
    root: Path,
    existing_path: Path,
    existing_job: Dict[str, Any],
    candidate_path: Path,
    candidate_job: Dict[str, Any],
) -> bool:
    # Keep the richer duplicate, then prefer canonical nested paths.
    existing_richness = _job_richness_score(existing_job)
    candidate_richness = _job_richness_score(candidate_job)

    if candidate_richness != existing_richness:
        return candidate_richness > existing_richness

    existing_depth = _relative_directory_depth(root, existing_path)
    candidate_depth = _relative_directory_depth(root, candidate_path)
    if candidate_depth != existing_depth:
        return candidate_depth > existing_depth

    return False


def _suppress_duplicate_content(
    root: Path,
    jobs_with_paths: List[tuple[Path, Dict[str, Any]]],
) -> List[tuple[Path, Dict[str, Any]]]:
    # Remove conservative content duplicates that survive job_id-level dedup.
    accepted: List[tuple[Path, Dict[str, Any]]] = []

    for candidate_path, candidate_job in jobs_with_paths:
        duplicate_index = next(
            (
                index
                for index, (_existing_path, existing_job) in enumerate(accepted)
                if _jobs_share_duplicate_content(existing_job, candidate_job)
            ),
            None,
        )

        if duplicate_index is None:
            accepted.append((candidate_path, candidate_job))
            continue

        existing_path, existing_job = accepted[duplicate_index]
        if _should_prefer_duplicate_content(
            root,
            existing_path,
            existing_job,
            candidate_path,
            candidate_job,
        ):
            accepted[duplicate_index] = (candidate_path, candidate_job)

    return accepted


def load_job_posting(file_path: str | Path) -> Dict[str, Any]:
    # Load one job posting JSON file and preserve optional metadata fields.
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Job posting file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError(f"Job posting JSON must be an object: {path}")

    for field in REQUIRED_JOB_FIELDS:
        if field not in payload:
            raise ValueError(f"Missing required job field '{field}' in: {path}")

    # Start from the original payload so optional fields such as source_site,
    # source_job_id, source_url, application_url, remote_status, and team survive.
    job: Dict[str, Any] = dict(payload)

    # Normalize required text fields.
    for field in REQUIRED_JOB_FIELDS:
        job[field] = _coerce_text(payload.get(field, ""))

    # Normalize common optional metadata fields when present.
    optional_text_fields = [
        "source_site",
        "source_job_id",
        "source_url",
        "application_url",
        "remote_status",
        "team",
    ]
    for field in optional_text_fields:
        if field in payload:
            job[field] = _coerce_text(payload.get(field, ""))

    return job


def load_all_job_postings(
    directory_path: str | Path,
    *,
    suppress_duplicate_content: bool = True,
) -> List[Dict[str, Any]]:
    """Load all JSON job posting files from a directory tree."""
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Job directory not found: {directory}")

    selected_jobs: Dict[str, tuple[Path, Dict[str, Any]]] = {}

    # Use recursive glob so crawled jobs under nested source/site folders are also loaded.
    for file_path in sorted(directory.rglob("*.json")):
        job = load_job_posting(file_path)
        job_id = job["job_id"]

        existing = selected_jobs.get(job_id)
        if existing is None or _should_prefer_job_file(directory, existing[0], file_path):
            selected_jobs[job_id] = (file_path, job)

    jobs_with_paths = sorted(
        selected_jobs.values(),
        key=lambda item: str(item[0]).lower(),
    )

    if suppress_duplicate_content:
        jobs_with_paths = _suppress_duplicate_content(directory, jobs_with_paths)

    jobs = [job for _path, job in jobs_with_paths]

    if not jobs:
        raise ValueError(f"No job posting JSON files found in: {directory}")

    return jobs
