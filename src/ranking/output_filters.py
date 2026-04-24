from __future__ import annotations

import re
from typing import Any, Dict, List


TITLE_TOKEN_ALIASES = {
    "ops": "operations",
    "engineering": "engineer",
}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _optional_fields_match(left: Dict[str, Any], right: Dict[str, Any], field: str) -> bool:
    left_value = _normalize_text(left.get(field, ""))
    right_value = _normalize_text(right.get(field, ""))
    return not left_value or not right_value or left_value == right_value


def _title_tokens(title: str) -> set[str]:
    return {
        TITLE_TOKEN_ALIASES.get(token, token)
        for token in re.findall(r"[a-z0-9]+", _normalize_text(title))
    }


def _title_similarity(left_title: str, right_title: str) -> float:
    left_tokens = _title_tokens(left_title)
    right_tokens = _title_tokens(right_title)

    if not left_tokens or not right_tokens:
        return 0.0

    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return overlap / union


def _looks_like_similar_result(existing: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
    if _normalize_text(existing.get("company", "")) != _normalize_text(candidate.get("company", "")):
        return False

    if not _optional_fields_match(existing, candidate, "source"):
        return False

    if not _optional_fields_match(existing, candidate, "source_site"):
        return False

    if not _optional_fields_match(existing, candidate, "employment_type"):
        return False

    if not _optional_fields_match(existing, candidate, "remote_status"):
        return False

    if not _optional_fields_match(existing, candidate, "team"):
        return False

    existing_application_url = _normalize_text(existing.get("application_url", ""))
    candidate_application_url = _normalize_text(candidate.get("application_url", ""))
    if (
        existing_application_url
        and candidate_application_url
        and existing_application_url == candidate_application_url
    ):
        return True

    existing_source_url = _normalize_text(existing.get("source_url", ""))
    candidate_source_url = _normalize_text(candidate.get("source_url", ""))
    if existing_source_url and candidate_source_url and existing_source_url == candidate_source_url:
        return True

    return _title_similarity(existing.get("title", ""), candidate.get("title", "")) >= 0.9


def suppress_similar_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Keep only the highest-ranked item when multiple visible results look like
    # the same posting repeated across locations or duplicate feeds.
    accepted: List[Dict[str, Any]] = []

    for candidate in results:
        if any(_looks_like_similar_result(existing, candidate) for existing in accepted):
            continue
        accepted.append(candidate)

    return accepted


def filter_results_for_output(
    results: List[Dict[str, Any]],
    *,
    eligible_only: bool,
    applyable_only: bool,
    suppress_similar: bool = False,
) -> List[Dict[str, Any]]:
    # Keep only results that satisfy the selected visibility filters.
    filtered = results

    if eligible_only:
        filtered = [job for job in filtered if not job.get("blocking_issues")]

    if applyable_only:
        filtered = [job for job in filtered if job.get("action_label") != "Skip"]

    if suppress_similar:
        filtered = suppress_similar_results(filtered)

    return filtered


def truncate_results(results: List[Dict[str, Any]], top_k: int | None) -> List[Dict[str, Any]]:
    # Apply optional top-k truncation after visibility filtering.
    if top_k is None:
        return results
    return results[:top_k]
