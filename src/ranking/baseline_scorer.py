from __future__ import annotations

from typing import Any, Dict, List, Tuple


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


def _compute_skill_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """
    Measure how well the candidate's extracted skills overlap with
    the job's required and preferred qualification text.

    Returns:
        skill_score: baseline skill match score in [0, 1]
        matched_skills: all matched skills
        required_matches: skills found in required qualifications
    """
    candidate_skills = profile["skill_set"]

    required_text = job["min_qualifications"]
    preferred_text = job["preferred_qualifications"]

    # Check whether each candidate skill appears in the required/preferred text.
    required_matches = sorted([skill for skill in candidate_skills if skill in required_text])
    preferred_matches = sorted([skill for skill in candidate_skills if skill in preferred_text])

    matched_skills = sorted(set(required_matches + preferred_matches))

    # In this baseline, the score is based on how many candidate skills appear in the job text.
    required_overlap_score = _safe_ratio(len(required_matches), max(len(candidate_skills), 1))
    preferred_overlap_score = _safe_ratio(len(preferred_matches), max(len(candidate_skills), 1))

    # Weight required qualifications more than preferred ones.
    skill_score = min(1.0, required_overlap_score * 0.7 + preferred_overlap_score * 0.3)

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
    Generate a small list of missing skills by checking common ML/data keywords
    found in the job qualifications but missing from the candidate profile.
    """
    candidate_skills = profile["skill_set"]

    # This is a manually defined keyword list for the first baseline version.
    required_keywords = [
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
    ]

    combined_text = f"{job['min_qualifications']} {job['preferred_qualifications']}"
    gaps = []

    for keyword in required_keywords:
        if keyword in combined_text and keyword not in candidate_skills:
            gaps.append(keyword)

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