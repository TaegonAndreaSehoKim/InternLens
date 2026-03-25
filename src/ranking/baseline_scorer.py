from __future__ import annotations

from typing import Any, Dict, List, Tuple

# A small controlled keyword list for the baseline version.
# This can be expanded later or replaced with a more robust skill extraction pipeline.
SKILL_KEYWORDS = [
    "python",
    "sql",
    "pytorch",
    "tensorflow",
    "aws",
    "docker",
    "kubernetes",
    "airflow",
    "spark",
    "machine learning",
    "deep learning",
    "recommendation systems",
    "data analysis",
    "statistics",
]


def _tokenize(text: str) -> set[str]:
    """
    A simple whitespace-based tokenizer for baseline matching.
    """
    return set(text.lower().split())


def _safe_ratio(numerator: int, denominator: int) -> float:
    """
    Compute a ratio safely without dividing by zero.
    """
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _extract_keywords_from_text(text: str) -> Set[str]:
    """
    Extract known skill keywords that appear in the given text.
    This is a simple rule-based baseline extractor.
    """
    text = text.lower()
    return {keyword for keyword in SKILL_KEYWORDS if keyword in text}


def _compute_skill_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """
    Measure how well the candidate covers the job's required and preferred skills.

    Important:
    This version scores against the job's requested skills, not against the
    full size of the candidate's skill set. That makes the score much more
    interpretable for ranking.
    """
    candidate_skills = profile["skill_set"]

    required_keywords = _extract_keywords_from_text(job["min_qualifications"])
    preferred_keywords = _extract_keywords_from_text(job["preferred_qualifications"])

    required_matches = sorted(candidate_skills & required_keywords)
    preferred_matches = sorted(candidate_skills & preferred_keywords)
    matched_skills = sorted(set(required_matches + preferred_matches))

    # Score against job-side demand instead of candidate-side inventory.
    required_overlap_score = _safe_ratio(len(required_matches), len(required_keywords))
    preferred_overlap_score = _safe_ratio(len(preferred_matches), len(preferred_keywords))

    # Give more weight to required qualifications.
    skill_score = min(1.0, required_overlap_score * 0.75 + preferred_overlap_score * 0.25)

    return skill_score, matched_skills, required_matches


def _compute_role_match(profile: Dict[str, Any], job: Dict[str, Any]) -> float:
    """
    Compute a simple token-overlap score between the candidate's preferred roles
    and the current job title.
    """
    title_tokens = _tokenize(job["title"])

    if not profile["preferred_roles"]:
        return 0.0

    best_score = 0.0

    # Use the best match across all preferred role names.
    for preferred_role in profile["preferred_roles"]:
        role_tokens = _tokenize(preferred_role)
        overlap = len(title_tokens & role_tokens)
        score = _safe_ratio(overlap, max(len(role_tokens), 1))
        best_score = max(best_score, score)

    return best_score


def _compute_location_match(profile: Dict[str, Any], job: Dict[str, Any]) -> float:
    """
    Compute a simple location match score.
    Returns 1.0 for a match and 0.0 otherwise.
    """
    job_location = job["location"]

    # If any preferred location appears in the job location text, treat it as a match.
    for preferred_location in profile["preferred_locations"]:
        if preferred_location in job_location:
            return 1.0

    # Handle simple remote preference matching.
    if "remote" in job.get("remote_status", "") and any(
        preferred == "remote" for preferred in profile["preferred_locations"]
    ):
        return 1.0

    return 0.0


def _check_blocking_constraints(profile: Dict[str, Any], job: Dict[str, Any]) -> List[str]:
    """
    Check hard constraints that may make a job effectively ineligible,
    even if the overall fit score is strong.
    """
    blockers: List[str] = []

    sponsorship_text = job["sponsorship_info"]

    if profile["sponsorship_need"] and "no sponsorship" in sponsorship_text:
        blockers.append("Sponsorship is not available for this role")

    return blockers


def _generate_reasons(
    skill_score: float,
    role_score: float,
    location_score: float,
    matched_skills: List[str],
    blockers: List[str],
) -> List[str]:
    """
    Generate human-readable explanation strings from the baseline scoring signals.
    """
    reasons: List[str] = []

    if skill_score >= 0.35 and matched_skills:
        reasons.append(f"Strong skill overlap in: {', '.join(matched_skills[:4])}")

    if role_score >= 0.5:
        reasons.append("Preferred role title aligns well with the job title")

    if location_score >= 1.0:
        reasons.append("Location preference matches this opportunity")

    if blockers:
        reasons.append("This role has a blocking eligibility constraint")

    # Fallback reason when no major signal is strong enough.
    if not reasons:
        reasons.append("This role was ranked mainly from baseline text and preference signals")

    return reasons[:3]


def _generate_skill_gaps(profile: Dict[str, Any], job: Dict[str, Any]) -> List[str]:
    """
    Generate missing skills by comparing the candidate's skills against
    the job's extracted required and preferred keywords.
    """
    candidate_skills = profile["skill_set"]

    required_keywords = _extract_keywords_from_text(job["min_qualifications"])
    preferred_keywords = _extract_keywords_from_text(job["preferred_qualifications"])

    # Prioritize missing required skills first, then preferred skills.
    missing_required = sorted(required_keywords - candidate_skills)
    missing_preferred = sorted(preferred_keywords - candidate_skills)

    gaps = missing_required + [skill for skill in missing_preferred if skill not in missing_required]

    return gaps[:4]


def score_job(profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score one job for one candidate profile and return the final result dictionary.

    Important design note:
    - The fit score measures how well the job matches the candidate.
    - Blocking issues are handled separately instead of being mixed directly
      into the numeric score.
    """
    skill_score, matched_skills, _ = _compute_skill_match(profile, job)
    role_score = _compute_role_match(profile, job)
    location_score = _compute_location_match(profile, job)
    blockers = _check_blocking_constraints(profile, job)

    # Compute a pure fit score without mixing in hard eligibility blockers.
    raw_score = (
        skill_score * 0.60
        + role_score * 0.25
        + location_score * 0.15
    )

    # Clamp the score to [0, 1].
    bounded_score = max(0.0, min(1.0, raw_score))

    # Convert to a 100-point scale for easier interpretation.
    final_score = round(bounded_score * 100, 2)

    # Decide the action label separately from the fit score.
    if blockers:
        action_label = "Skip"
    elif final_score >= 70:
        action_label = "Apply Now"
    elif final_score >= 45:
        action_label = "Apply Later"
    else:
        action_label = "Skip"

    reasons = _generate_reasons(
        skill_score=skill_score,
        role_score=role_score,
        location_score=location_score,
        matched_skills=matched_skills,
        blockers=blockers,
    )

    skill_gaps = _generate_skill_gaps(profile, job)

    return {
        "job_id": job["job_id"],
        "company": job["company"],
        "title": job["title"],
        "location": job["location"],
        "score": final_score,
        "action_label": action_label,
        "matched_skills": matched_skills,
        "skill_gaps": skill_gaps,
        "reasons": reasons,
        "blocking_issues": blockers,
        # Keep component scores for debugging and analysis.
        "component_scores": {
            "skill_score": round(skill_score, 4),
            "role_score": round(role_score, 4),
            "location_score": round(location_score, 4),
        },
    }


def rank_jobs(profile: Dict[str, Any], jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score all jobs and return them sorted by descending score.
    """
    scored_jobs = [score_job(profile, job) for job in jobs]
    return sorted(scored_jobs, key=lambda x: x["score"], reverse=True)