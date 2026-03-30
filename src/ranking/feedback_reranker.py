from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


# Keep the first version intentionally small and interpretable.
VALID_FEEDBACK_LABELS = {"applied", "saved", "skipped"}

# Positive feedback boosts similar jobs, while skipped feedback lowers them.
FEEDBACK_WEIGHTS = {
    "applied": 1.0,
    "saved": 0.5,
    "skipped": -0.75,
}

ACTION_PRIORITY = {
    "Apply Now": 0,
    "Apply Later": 1,
    "Skip": 2,
}

# Reuse a small, explicit skill vocabulary so feedback similarity
# focuses on meaningful signals instead of generic text tokens.
KNOWN_SKILL_PHRASES = {
    "python",
    "pytorch",
    "machine learning",
    "data analysis",
    "sql",
    "aws",
    "docker",
    "deep learning",
    "statistics",
    "recommendation systems",
    "kubernetes",
}

# Ignore generic title words so feedback similarity is driven more by
# meaningful specialization words than by common role boilerplate.
GENERIC_ROLE_TOKENS = {
    "intern",
    "engineer",
    "scientist",
    "software",
    "developer",
    "research",
    "role",
    "position",
}

MAX_FEEDBACK_EXPLANATIONS = 3


def _normalize_text(text: str) -> str:
    """Normalize free text for simple token-based comparisons."""
    return " ".join(text.lower().strip().split())


def _tokenize_title(title: str) -> Set[str]:
    """Split a job title into a set of normalized tokens."""
    return set(_normalize_text(title).split())


def _meaningful_title_tokens(title: str) -> Set[str]:
    """Keep only title tokens that carry specialization signal."""
    return {
        token
        for token in _tokenize_title(title)
        if token and token not in GENERIC_ROLE_TOKENS
    }


def _extract_job_skill_set(job: Dict[str, Any]) -> Set[str]:
    """
    Extract a conservative skill set from the job record by matching
    against a small known skill phrase vocabulary.
    """
    combined_text = " ".join(
        [
            str(job.get("title", "")),
            str(job.get("description", "")),
            str(job.get("min_qualifications", "")),
            str(job.get("preferred_qualifications", "")),
        ]
    ).lower()

    matched_skills = {
        skill_phrase
        for skill_phrase in KNOWN_SKILL_PHRASES
        if skill_phrase in combined_text
    }

    return matched_skills


def normalize_feedback_profile(feedback: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize feedback data from either file or inline payload."""
    if "profile_id" not in feedback:
        raise ValueError("Feedback data must include 'profile_id'.")

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


def load_feedback_profile(file_path: str | Path) -> Dict[str, Any]:
    """Load and validate a simple feedback JSON file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Feedback file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        feedback = json.load(f)

    return normalize_feedback_profile(feedback)


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
            "job_title": job["title"],
            "title_tokens": _meaningful_title_tokens(job["title"]),
            "skill_tokens": _extract_job_skill_set(job),
        }

    return feedback_lookup


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Return a safe ratio without raising on empty denominators."""
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _compute_similarity_details(
    current_job: Dict[str, Any],
    feedback_job: Dict[str, Any],
) -> Tuple[float, List[str], List[str]]:
    """Return similarity plus overlapping title/skill tokens for explanation."""
    current_title_tokens = _meaningful_title_tokens(current_job["title"])
    current_skill_tokens = _extract_job_skill_set(current_job)

    title_overlap = sorted(current_title_tokens & feedback_job["title_tokens"])
    skill_overlap = sorted(current_skill_tokens & feedback_job["skill_tokens"])

    title_score = _safe_ratio(len(title_overlap), max(len(feedback_job["title_tokens"]), 1))
    skill_score = _safe_ratio(len(skill_overlap), max(len(feedback_job["skill_tokens"]), 1))

    # Put slightly more weight on skill overlap because it is more stable
    # than generic job title wording.
    similarity = (0.4 * title_score) + (0.6 * skill_score)
    return similarity, title_overlap, skill_overlap


def _compute_similarity(current_job: Dict[str, Any], feedback_job: Dict[str, Any]) -> float:
    """Compatibility wrapper for simple similarity-only use cases."""
    similarity, _, _ = _compute_similarity_details(current_job, feedback_job)
    return similarity


def compute_feedback_adjustment(
    current_job: Dict[str, Any],
    feedback_lookup: Dict[str, Dict[str, Any]],
) -> Tuple[float, List[Dict[str, Any]]]:
    """Aggregate reranking adjustments and collect explanation snippets."""
    adjustment = 0.0
    explanations: List[Dict[str, Any]] = []

    for feedback_job_id, feedback_job in feedback_lookup.items():
        # Do not use a job's own feedback event to rerank itself.
        if current_job["job_id"] == feedback_job_id:
            continue

        similarity, title_overlap, skill_overlap = _compute_similarity_details(
            current_job,
            feedback_job,
        )
        label_weight = FEEDBACK_WEIGHTS[feedback_job["feedback_label"]]
        raw_contribution = similarity * label_weight * 15.0
        adjustment += raw_contribution

        # Skip zero-signal items so explanations stay concise.
        if similarity <= 0:
            continue

        explanations.append(
            {
                "source_job_id": feedback_job_id,
                "source_job_title": feedback_job["job_title"],
                "feedback_label": feedback_job["feedback_label"],
                "similarity": round(similarity, 3),
                "adjustment": round(raw_contribution, 2),
                "shared_title_tokens": title_overlap,
                "shared_skill_tokens": skill_overlap,
            }
        )

    explanations.sort(key=lambda item: abs(item["adjustment"]), reverse=True)
    return round(adjustment, 2), explanations[:MAX_FEEDBACK_EXPLANATIONS]


def apply_feedback_reranking(
    ranked_jobs: List[Dict[str, Any]],
    jobs: List[Dict[str, Any]],
    feedback_profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Attach feedback-based score adjustments and return a reranked list."""
    feedback_lookup = build_feedback_lookup(jobs, feedback_profile)

    reranked_results = []
    for ranked_job in ranked_jobs:
        adjustment, explanations = compute_feedback_adjustment(ranked_job, feedback_lookup)
        updated_job = dict(ranked_job)
        updated_job["feedback_adjustment"] = adjustment
        updated_job["reranked_score"] = round(updated_job["score"] + adjustment, 2)
        updated_job["feedback_explanations"] = explanations
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