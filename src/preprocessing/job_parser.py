from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _normalize_text(text: str) -> str:
    """Convert text to lowercase and collapse extra whitespace."""
    return " ".join(text.lower().strip().split())


def _extract_text(value: Any) -> str:
    """Safely convert a JSON value to a normalized string."""
    if value is None:
        return ""
    return _normalize_text(str(value))


def load_job_posting(file_path: str | Path) -> Dict[str, Any]:
    """
    Load a single job posting JSON file and return a normalized dictionary
    that can be used by the ranking pipeline.
    """
    path = Path(file_path)

    # Fail early if the job file path is invalid.
    if not path.exists():
        raise FileNotFoundError(f"Job posting file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        job = json.load(f)

    # These fields are required for the baseline scorer and API output.
    required_fields = [
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

    missing_fields = [field for field in required_fields if field not in job]
    if missing_fields:
        raise ValueError(f"Missing required job fields: {missing_fields}")

    # Normalize the fields once here so downstream code can assume a stable schema.
    parsed_job = {
        "job_id": job["job_id"],
        "company": _extract_text(job["company"]),
        "title": _extract_text(job["title"]),
        "location": _extract_text(job["location"]),
        "description": _extract_text(job["description"]),
        "min_qualifications": _extract_text(job["min_qualifications"]),
        "preferred_qualifications": _extract_text(job["preferred_qualifications"]),
        "posting_date": str(job["posting_date"]).strip(),
        "sponsorship_info": _extract_text(job["sponsorship_info"]),
        "employment_type": _extract_text(job["employment_type"]),
        "source": _extract_text(job["source"]),
        # Keep optional fields present so consumers do not need repeated .get() calls.
        "salary_range": _extract_text(job.get("salary_range", "")),
        "team": _extract_text(job.get("team", "")),
        "remote_status": _extract_text(job.get("remote_status", "")),
        "application_url": _extract_text(job.get("application_url", "")),
    }

    # This combined text is useful for future retrieval or richer heuristic matching.
    parsed_job["combined_text"] = " ".join(
        [
            parsed_job["title"],
            parsed_job["description"],
            parsed_job["min_qualifications"],
            parsed_job["preferred_qualifications"],
        ]
    ).strip()

    return parsed_job


def load_all_job_postings(directory_path: str | Path) -> List[Dict[str, Any]]:
    """Load all JSON job posting files from a directory."""
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Job directory not found: {directory}")

    jobs: List[Dict[str, Any]] = []

    # Use sorted order so tests and outputs remain deterministic.
    for file_path in sorted(directory.glob("*.json")):
        jobs.append(load_job_posting(file_path))

    if not jobs:
        raise ValueError(f"No job posting JSON files found in: {directory}")

    return jobs
