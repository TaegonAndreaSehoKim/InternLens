from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _normalize_text(text: str) -> str:
    """
    Convert text to lowercase and collapse extra whitespace.
    Example:
        "  Machine   Learning Intern " -> "machine learning intern"
    """
    return " ".join(text.lower().strip().split())


def _normalize_list(values: List[str]) -> List[str]:
    """
    Normalize a list of strings and drop empty values.
    """
    normalized = []
    for value in values:
        if isinstance(value, str) and value.strip():
            normalized.append(_normalize_text(value))
    return normalized


def load_candidate_profile(file_path: str | Path) -> Dict[str, Any]:
    """
    Load a candidate profile JSON file and return a normalized dictionary
    that is easy to use for downstream scoring and ranking.
    """
    path = Path(file_path)

    # Fail early if the input file does not exist.
    if not path.exists():
        raise FileNotFoundError(f"Candidate profile file not found: {path}")

    # Read the JSON file.
    with path.open("r", encoding="utf-8") as f:
        profile = json.load(f)

    # These fields are required for the first baseline pipeline.
    required_fields = [
        "profile_id",
        "resume_text",
        "degree_level",
        "grad_date",
        "preferred_roles",
        "preferred_locations",
        "sponsorship_need",
        "extracted_skills",
    ]

    # Report exactly which required fields are missing.
    missing_fields = [field for field in required_fields if field not in profile]
    if missing_fields:
        raise ValueError(f"Missing required profile fields: {missing_fields}")

    # Build a normalized version of the candidate profile.
    parsed_profile = {
        "profile_id": profile["profile_id"],
        "resume_text": profile["resume_text"],
        "degree_level": _normalize_text(profile["degree_level"]),
        "grad_date": str(profile["grad_date"]).strip(),
        "preferred_roles": _normalize_list(profile.get("preferred_roles", [])),
        "preferred_locations": _normalize_list(profile.get("preferred_locations", [])),
        "target_industries": _normalize_list(profile.get("target_industries", [])),
        "sponsorship_need": bool(profile["sponsorship_need"]),
        "extracted_skills": _normalize_list(profile.get("extracted_skills", [])),
        "years_of_experience": profile.get("years_of_experience", 0),
        "notes": profile.get("notes", ""),
    }

    # Store skills as a set to make overlap checks faster later.
    parsed_profile["skill_set"] = set(parsed_profile["extracted_skills"])

    return parsed_profile