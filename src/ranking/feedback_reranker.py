from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set


# Keep the first version intentionally small and interpretable.
VALID_FEEDBACK_LABELS = {"applied", "saved", "skipped"}

# Positive feedback boosts similar jobs, while skipped feedback lowers them.
FEEDBACK_WEIGHTS = {
    "applied": 1.0,
    "saved": 0.5,
    "skipped": -0.75,
}


def _normalize_text(text: str) -> str:
    """Normalize free text for simple token-based comparisons."""
    return " ".join(text.lower().strip().split())


def _tokenize_title(title: str) -> Set[str]:
    """Split a job title into a set of normalized tokens."""
    return set(_normalize_text(title).split())


def _extract_job_skill_set(job: Dict[str, Any]) -> Set[str]:
    """Extract lightweight skill-like tokens from job qualification fields."""
    skills = set()

    for field_name in ("min_qualifications", "preferred_qualifications"):
        field_value = job.get(field_name, "")
        if isinstance(field_value, str) and field_value.strip():
            tokens = [token.strip(" ,.;:()[]") for token in field_value.lower().split()]
            skills.update(token for token in tokens if token)

    return skills


def load_feedback_profile(file_path: str | Path) -> Dict[str, Any]:
    """Load and validate a simple feedback JSON file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Feedback file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        feedback = json.load(f)

    if "profile_id" not in feedback:
        raise ValueError("Feedback file must include 'profile_id'.")

    events = feedback.get("events", [])
    if not isinstance(events, list):
        raise ValueError("'events' must be a list.")

    normalized_events = []
    for event in events:
        if "job_id" not in event or "feedback_label" not in event:
            raise ValueError("Each feedback event must include 'job_id' and 'feedback_label'.")

        label = _normalize_text(str(event["feedback_label"]))
        if label not in VALID_FEEDBACK_LABELS:
            raise ValueError(f"Unsupported feedback label: {label}")

        normalized_events.append(
            {
                "job_id": str(event["job_id"]).strip(),
                "feedback_label": label,
            }
        )

    return {
        "profile_id": str(feedback["profile_id"]).strip(),
        "events": normalized_events,
    }


def build_feedback_lookup(
    jobs: List[Dict[str, Any]],
    feedback_profile: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Join feedback events with known jobs and cache comparison features."""
    job_lookup = {job["job_id"]: job for job in jobs}
    feedback_lookup: Dict[str, Dict[str, Any]] = {}

    for event in feedback_profile["events"]:
        job_id = event["job_id"]
        if job_id not in job_lookup:
            # Ignore feedback tied to jobs outside the current corpus.
            continue

        job = job_lookup[job_id]
        feedback_lookup[job_id] = {
            "feedback_label": event["feedback_label"],
            "title_tokens": _tokenize_title(job["title"]),
            "skill_tokens": _extract_job_skill_set(job),
        }

    return feedback_lookup


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return a safe ratio without raising on empty denominators."""
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _compute_similarity(current_job: Dict[str, Any], feedback_job: Dict[str, Any]) -> float:
    """Estimate similarity between a current job and a feedback-tagged reference job."""
    current_title_tokens = _tokenize_title(current_job["title"])
    current_skill_tokens = _extract_job_skill_set(current_job)

    title_overlap = current_title_tokens & feedback_job["title_tokens"]
    skill_overlap = current_skill_tokens & feedback_job["skill_tokens"]

    title_score = _safe_ratio(len(title_overlap), max(len(feedback_job["title_tokens"]), 1))
    skill_score = _safe_ratio(len(skill_overlap), max(len(feedback_job["skill_tokens"]), 1))

    # Title overlap matters a bit more because title usually captures the target role faster.
    return (0.6 * title_score) + (0.4 * skill_score)


def compute_feedback_adjustment(
    current_job: Dict[str, Any],
    feedback_lookup: Dict[str, Dict[str, Any]],
) -> float:
    """Aggregate reranking adjustments from all known feedback examples."""
    adjustment = 0.0

    for feedback_job_id, feedback_job in feedback_lookup.items():
        # Do not use a job's own feedback event to rerank itself.
        if current_job["job_id"] == feedback_job_id:
            continue

        similarity = _compute_similarity(current_job, feedback_job)
        label_weight = FEEDBACK_WEIGHTS[feedback_job["feedback_label"]]
        adjustment += similarity * label_weight * 15.0

    return round(adjustment, 2)

ACTION_PRIORITY = {
        "Apply Now": 0,
        "Apply Later": 1,
        "Skip": 2,
    }

def apply_feedback_reranking(
    ranked_jobs: List[Dict[str, Any]],
    jobs: List[Dict[str, Any]],
    feedback_profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Attach feedback-based score adjustments and return a reranked list."""
    feedback_lookup = build_feedback_lookup(jobs, feedback_profile)

    reranked_results = []
    for ranked_job in ranked_jobs:
        adjustment = compute_feedback_adjustment(ranked_job, feedback_lookup)
        updated_job = dict(ranked_job)
        updated_job["feedback_adjustment"] = adjustment
        updated_job["reranked_score"] = round(updated_job["score"] + adjustment, 2)
        reranked_results.append(updated_job)

    return sorted(
        reranked_results,
        key=lambda job: (
            ACTION_PRIORITY.get(job["action_label"], 99),
            len(job["blocking_issues"]),
            -job["reranked_score"],
            job["title"],
        ),
    )
