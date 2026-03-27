from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import re

from typing import Optional


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

SKILL_ALIASES = {
    "ml": "machine learning",
    "machine-learning": "machine learning",
    "torch": "pytorch",
    "pytorch lightning": "pytorch",
    "stats": "statistics",
    "statistical analysis": "statistics",
    "recsys": "recommendation systems",
    "recommendation system": "recommendation systems",
    "recommendation engine": "recommendation systems",
    "analytics": "data analysis",
}

ROLE_STOPWORDS = {
    "intern",
    "internship",
    "engineer",
    "scientist",
    "developer",
    "software",
}


def _tokenize(text: str) -> set[str]:
    return set(text.lower().split())


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _canonicalize_text(text: str) -> str:
    normalized = text.lower()
    for alias, canonical in sorted(SKILL_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        normalized = normalized.replace(alias, canonical)
    return normalized


def _canonicalize_skill(skill: str) -> str:
    normalized = skill.lower().strip()
    return SKILL_ALIASES.get(normalized, normalized)


def _extract_keywords_from_text(text: str) -> Set[str]:
    canonical_text = _canonicalize_text(text)
    return {keyword for keyword in SKILL_KEYWORDS if keyword in canonical_text}


def _normalize_candidate_skills(profile: Dict[str, Any]) -> Set[str]:
    return {_canonicalize_skill(skill) for skill in profile["skill_set"]}


def _meaningful_role_tokens(text: str) -> Set[str]:
    tokens = _tokenize(text)
    return {token for token in tokens if token not in ROLE_STOPWORDS}


def _compute_skill_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    candidate_skills = _normalize_candidate_skills(profile)

    required_keywords = _extract_keywords_from_text(job["min_qualifications"])
    preferred_keywords = _extract_keywords_from_text(job["preferred_qualifications"])

    required_matches = sorted(candidate_skills & required_keywords)
    preferred_matches = sorted(candidate_skills & preferred_keywords)
    matched_skills = sorted(set(required_matches + preferred_matches))

    required_overlap_score = _safe_ratio(len(required_matches), len(required_keywords))
    preferred_overlap_score = _safe_ratio(len(preferred_matches), len(preferred_keywords))

    skill_score = min(1.0, required_overlap_score * 0.75 + preferred_overlap_score * 0.25)

    return skill_score, matched_skills, required_matches


def _compute_role_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str], Optional[str]]:
    title_tokens = _meaningful_role_tokens(job["title"])

    if not profile["preferred_roles"]:
        return 0.0, [], None

    best_score = 0.0
    best_overlap_tokens: List[str] = []
    best_preferred_role: Optional[str] = None

    for preferred_role in profile["preferred_roles"]:
        role_tokens = _meaningful_role_tokens(preferred_role)
        overlap_tokens = sorted(title_tokens & role_tokens)
        score = _safe_ratio(len(overlap_tokens), max(len(role_tokens), 1))

        if score > best_score:
            best_score = score
            best_overlap_tokens = overlap_tokens
            best_preferred_role = preferred_role

    return best_score, best_overlap_tokens, best_preferred_role


def _compute_location_match(profile: Dict[str, Any], job: Dict[str, Any]) -> float:
    job_location = job["location"]

    for preferred_location in profile["preferred_locations"]:
        if preferred_location in job_location:
            return 1.0

    if "remote" in job.get("remote_status", "") and any(
        preferred == "remote" for preferred in profile["preferred_locations"]
    ):
        return 1.0

    return 0.0


def _extract_grad_year(grad_date: str) -> Optional[int]:
    match = re.search(r"(20\d{2})", grad_date)
    if match:
        return int(match.group(1))
    return None


def _check_blocking_constraints(profile: Dict[str, Any], job: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []

    sponsorship_text = job["sponsorship_info"].lower()
    employment_type = job["employment_type"].lower()
    combined_text = " ".join(
        [
            job["title"],
            job["description"],
            job["min_qualifications"],
            job["preferred_qualifications"],
            job["employment_type"],
        ]
    ).lower()

    degree_level = profile["degree_level"].lower()
    grad_year = _extract_grad_year(profile["grad_date"])

    if profile["sponsorship_need"] and "no sponsorship" in sponsorship_text:
        blockers.append("Sponsorship is not available for this role")

    if "intern" not in employment_type and "intern" not in combined_text:
        blockers.append("This role does not appear to be an internship")

    if "phd" in combined_text and "phd" not in degree_level:
        blockers.append("This role appears to require a PhD")

    if grad_year is not None:
        year_matches = re.findall(r"20\d{2}", combined_text)
        mentioned_years = {int(year) for year in year_matches}

        if mentioned_years:
            if grad_year not in mentioned_years and (grad_year - 1) not in mentioned_years and (grad_year + 1) not in mentioned_years:
                if any(keyword in combined_text for keyword in ["graduate", "graduation", "graduating", "expected to graduate"]):
                    blockers.append("Graduation timing may not match this role")

    return blockers


def _generate_reasons(
    skill_score: float,
    role_score: float,
    best_preferred_role: Optional[str],
    location_score: float,
    matched_skills: List[str],
    blockers: List[str],
) -> List[str]:
    reasons: List[str] = []

    if skill_score >= 0.35 and matched_skills:
        reasons.append(f"Matched on key skills: {', '.join(matched_skills[:4])}")

    if role_score >= 0.34 and best_preferred_role:
        reasons.append(f"Title aligns with preferred role: {best_preferred_role}")

    if location_score >= 1.0:
        reasons.append("Location matches a preferred target")

    if blockers:
        reasons.append("Blocked by eligibility constraints in the posting")

    if not reasons:
        reasons.append("Limited match signals beyond the current baseline heuristics")

    return reasons[:3]


def _generate_skill_gaps(profile: Dict[str, Any], job: Dict[str, Any]) -> List[str]:
    candidate_skills = _normalize_candidate_skills(profile)

    required_keywords = _extract_keywords_from_text(job["min_qualifications"])
    preferred_keywords = _extract_keywords_from_text(job["preferred_qualifications"])

    missing_required = sorted(required_keywords - candidate_skills)
    missing_preferred = sorted(preferred_keywords - candidate_skills)

    gaps = missing_required + [skill for skill in missing_preferred if skill not in missing_required]

    return gaps[:4]


def score_job(profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    skill_score, matched_skills, _ = _compute_skill_match(profile, job)
    role_score, _, best_preferred_role = _compute_role_match(profile, job)
    location_score = _compute_location_match(profile, job)
    blockers = _check_blocking_constraints(profile, job)

    raw_score = (
        skill_score * 0.60
        + role_score * 0.25
        + location_score * 0.15
    )

    bounded_score = max(0.0, min(1.0, raw_score))
    final_score = round(bounded_score * 100, 2)

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
        best_preferred_role=best_preferred_role,
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
        "component_scores": {
            "skill_score": round(skill_score, 4),
            "role_score": round(role_score, 4),
            "location_score": round(location_score, 4),
        },
    }


ACTION_PRIORITY = {
    "Apply Now": 0,
    "Apply Later": 1,
    "Skip": 2,
}


def _ranking_sort_key(job: Dict[str, Any]) -> tuple[int, int, float, str]:
    return (
        ACTION_PRIORITY.get(job["action_label"], 99),
        len(job["blocking_issues"]),
        -job["score"],
        job["title"],
    )


def rank_jobs(profile: Dict[str, Any], jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored_jobs = [score_job(profile, job) for job in jobs]
    return sorted(scored_jobs, key=_ranking_sort_key)