from __future__ import annotations

from typing import Any, Dict, List


def filter_results_for_output(
    results: List[Dict[str, Any]],
    *,
    eligible_only: bool,
    applyable_only: bool,
) -> List[Dict[str, Any]]:
    # Keep only results that satisfy the selected visibility filters.
    filtered = results

    if eligible_only:
        filtered = [job for job in filtered if not job.get("blocking_issues")]

    if applyable_only:
        filtered = [job for job in filtered if job.get("action_label") != "Skip"]

    return filtered


def truncate_results(results: List[Dict[str, Any]], top_k: int | None) -> List[Dict[str, Any]]:
    # Apply optional top-k truncation after visibility filtering.
    if top_k is None:
        return results
    return results[:top_k]
