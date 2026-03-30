from __future__ import annotations

import json
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


def load_all_job_postings(directory_path: str | Path) -> List[Dict[str, Any]]:
    """Load all JSON job posting files from a directory tree."""
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Job directory not found: {directory}")

    jobs: List[Dict[str, Any]] = []

    # Use recursive glob so crawled jobs under nested source/site folders are also loaded.
    for file_path in sorted(directory.rglob("*.json")):
        jobs.append(load_job_posting(file_path))

    if not jobs:
        raise ValueError(f"No job posting JSON files found in: {directory}")

    return jobs