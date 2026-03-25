from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _normalize_text(text: str) -> str:
    """
    Convert text to lowercase and collapse extra whitespace.
    """
    return " ".join(text.lower().strip().split())


def _extract_text(value: Any) -> str:
    """
    Safely convert a JSON value to a normalized string.
    Return an empty string if the value is None.
    """
    if value is None:
        return ""
    return _normalize_text(str(value))


def load_job_posting(file_path: str | Path) -> Dict[str, Any]:
    """
    Load a single job posting JSON file and return a normalized dictionary
    that can be used by the ranking pipeline.
    """
    path = Path(file_path)

    # Fail early if the file path is invalid.
    if not path.exists():
        raise FileNotFoundError(f"Job posting file not found: {path}")

    # Read the JSON file.
    with path.open("r", encoding="utf-8") as f:
        job = json.load(f)

    # These fields are required for the first baseline version.
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

    # Report missing required fields clearly.
    missing_fields = [field for field in required_fields if field not in job]
    if missing_fields:
        raise ValueError(f"Missing required job fields: {missing_fields}")

    # Normalize all important text fields.
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
        # Optional fields default to an empty string.
        "salary_range": _extract_text(job.get("salary_range", "")),
        "team": _extract_text(job.get("team", "")),
        "remote_status": _extract_text(job.get("remote_status", "")),
        "application_url": _extract_text(job.get("application_url", "")),
    }

    # Combine major text fields into one block for future search/retrieval use.
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
    """
    Load all JSON job posting files from a directory.
    """
    directory = Path(directory_path)

    # Fail early if the directory does not exist.
    if not directory.exists():
        raise FileNotFoundError(f"Job directory not found: {directory}")

    jobs: List[Dict[str, Any]] = []

    # Read all JSON files in sorted order for stable behavior.
    for file_path in sorted(directory.glob("*.json")):
        jobs.append(load_job_posting(file_path))

    # Raise an error if no sample job files were found.
    if not jobs:
        raise ValueError(f"No job posting JSON files found in: {directory}")

    return jobs