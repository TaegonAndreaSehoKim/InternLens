from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


# These are the core skill phrases the baseline scorer knows how to detect.
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

# These aliases reduce false negatives when the same skill is written differently.
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

# Generic words like "engineer" or "intern" do not help much for role matching.
ROLE_STOPWORDS = {
    "intern",
    "internship",
    "engineer",
    "scientist",
    "developer",
    "software",
}

# Strong seniority indicators that should usually block internship recommendations.
SENIORITY_TITLE_PATTERNS = [
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\bstaff\b",
    r"\blead\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bprincipal\b",
    r"\bhead\b",
    r"\bvp\b",
    r"\bvice president\b",
    r"\bchief\b",
]

# Explicit internship indicators.
INTERNSHIP_TITLE_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\bco[- ]?op\b",
    r"\bsummer intern\b",
    r"\bstudent intern\b",
]

# We keep description-based internship matching stricter than title matching.
INTERNSHIP_DESCRIPTION_PATTERNS = [
    r"\bthis internship\b",
    r"\binternship program\b",
    r"\bsummer internship\b",
    r"\bco[- ]?op program\b",
    r"\bintern class\b",
    r"\bintern cohort\b",
]

# Recommendation ordering should reflect strategy, not only raw fit score.
ACTION_PRIORITY = {
    "Apply Now": 0,
    "Apply Later": 1,
    "Skip": 2,
}


def _tokenize(text: str) -> Set[str]:
    """Split lowercase text into unique whitespace tokens."""
    return set(text.lower().split())


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Avoid division-by-zero when overlap sets are empty."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _canonicalize_text(text: str) -> str:
    """
    Replace known aliases in free text so phrase matching becomes more stable.

    Example:
    - "ml" -> "machine learning"
    - "torch" -> "pytorch"
    """
    normalized = text.lower()
    for alias, canonical in sorted(SKILL_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        normalized = normalized.replace(alias, canonical)
    return normalized


def _canonicalize_skill(skill: str) -> str:
    """Normalize a single candidate skill into its canonical form."""
    normalized = skill.lower().strip()
    return SKILL_ALIASES.get(normalized, normalized)


def _extract_keywords_from_text(text: str) -> Set[str]:
    """Extract known skill keywords from normalized text."""
    canonical_text = _canonicalize_text(text)
    return {keyword for keyword in SKILL_KEYWORDS if keyword in canonical_text}


def _normalize_candidate_skills(profile: Dict[str, Any]) -> Set[str]:
    """Normalize the candidate skill set before comparing it to job text."""
    return {_canonicalize_skill(skill) for skill in profile["skill_set"]}


def _meaningful_role_tokens(text: str) -> Set[str]:
    """
    Tokenize a role string and drop generic title words.

    This makes role overlap more meaningful and reduces false positives.
    """
    tokens = _tokenize(text)
    return {token for token in tokens if token not in ROLE_STOPWORDS}


def _has_pattern_match(text: str, patterns: List[str]) -> bool:
    """Return True when any regex pattern matches the given text."""
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def _has_explicit_internship_signal(job: Dict[str, Any]) -> bool:
    """
    Detect explicit internship signals from the title or employment type.

    We intentionally treat title/employment_type as stronger evidence than
    general description text because descriptions may contain noisy boilerplate.
    """
    title = job["title"]
    employment_type = job["employment_type"]

    return _has_pattern_match(title, INTERNSHIP_TITLE_PATTERNS) or _has_pattern_match(
        employment_type, INTERNSHIP_TITLE_PATTERNS
    )


def _has_description_internship_signal(job: Dict[str, Any]) -> bool:
    """
    Detect stronger internship phrases from the description text only.

    This is kept stricter than title matching to reduce false positives in large
    public boards such as Cloudflare or Waymo.
    """
    return _has_pattern_match(job["description"], INTERNSHIP_DESCRIPTION_PATTERNS)

def _has_any_internship_signal(job: Dict[str, Any]) -> bool:
    """
    Return True when the posting has either explicit or strong description-based
    internship signals.
    """
    return _has_explicit_internship_signal(job) or _has_description_internship_signal(job)

def _looks_like_senior_role(job: Dict[str, Any]) -> bool:
    """
    Flag obviously senior titles so they do not crowd out true internship targets.

    If a role is explicitly labeled as an internship, we do not apply the
    seniority blocker even if some unusual wording is present.
    """
    if _has_explicit_internship_signal(job):
        return False

    return _has_pattern_match(job["title"], SENIORITY_TITLE_PATTERNS)


def _compute_internship_signal_bonus(job: Dict[str, Any]) -> float:
    """
    Give a stronger bonus to jobs that explicitly identify themselves as internships.

    This helps real internship postings surface above generic non-intern roles
    that happen to share location or title overlap.
    """
    if _has_explicit_internship_signal(job):
        return 0.30

    if _has_description_internship_signal(job):
        return 0.10

    return 0.0


def _compute_skill_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str], List[str]]:
    """
    Compare candidate skills with required/preferred job keywords.

    Required skills get a larger weight than preferred skills.
    """
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
    """
    Compare the job title to each preferred role and keep the best match.

    We return the best preferred role string so explanation text can use the
    full role instead of a single token like "applied" or "machine".
    """
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
    """
    Check whether the job location matches one of the candidate's preferences.

    v1 supports simple substring matching plus a special remote fallback.
    """
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
    """Extract a four-digit graduation year from strings like '2027-12'."""
    match = re.search(r"(20\d{2})", grad_date)
    if match:
        return int(match.group(1))
    return None


def _check_blocking_constraints(profile: Dict[str, Any], job: Dict[str, Any]) -> List[str]:
    """
    Detect hard constraints that should override a strong fit score.

    The key design choice is to keep blockers separate from fit scoring.
    A job can still be relevant on paper while being unrealistic to apply to.
    """
    blockers: List[str] = []

    sponsorship_text = job["sponsorship_info"].lower()
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

    # Require explicit or strong internship evidence instead of a loose substring check.
    if not _has_any_internship_signal(job):
        blockers.append("This role does not appear to be an internship")

    if _looks_like_senior_role(job):
        blockers.append("This role appears to be a senior-level position")

    if "phd" in combined_text and "phd" not in degree_level:
        blockers.append("This role appears to require a PhD")

    if grad_year is not None:
        year_matches = re.findall(r"20\d{2}", combined_text)
        mentioned_years = {int(year) for year in year_matches}

        if mentioned_years:
            close_year_match = (
                grad_year in mentioned_years
                or (grad_year - 1) in mentioned_years
                or (grad_year + 1) in mentioned_years
            )
            mentions_graduation = any(
                keyword in combined_text
                for keyword in ["graduate", "graduation", "graduating", "expected to graduate"]
            )
            if mentions_graduation and not close_year_match:
                blockers.append("Graduation timing may not match this role")

    return blockers


def _generate_reasons(
    skill_score: float,
    role_score: float,
    best_preferred_role: Optional[str],
    location_score: float,
    internship_bonus: float,
    matched_skills: List[str],
    blockers: List[str],
) -> List[str]:
    """
    Build short, product-style explanation text for the recommendation output.
    """
    reasons: List[str] = []

    if skill_score >= 0.35 and matched_skills:
        reasons.append(f"Matched on key skills: {', '.join(matched_skills[:4])}")

    if role_score >= 0.34 and best_preferred_role:
        reasons.append(f"Title aligns with preferred role: {best_preferred_role}")

    if internship_bonus > 0:
        reasons.append("Posting explicitly identifies this as an internship")

    if location_score >= 1.0:
        reasons.append("Location matches a preferred target")

    if blockers:
        reasons.append("Blocked by eligibility constraints in the posting")

    if not reasons:
        reasons.append("Limited match signals beyond the current baseline heuristics")

    return reasons[:3]


def _generate_skill_gaps(profile: Dict[str, Any], job: Dict[str, Any]) -> List[str]:
    """Surface a few missing required/preferred skills for explanation output."""
    candidate_skills = _normalize_candidate_skills(profile)

    required_keywords = _extract_keywords_from_text(job["min_qualifications"])
    preferred_keywords = _extract_keywords_from_text(job["preferred_qualifications"])

    missing_required = sorted(required_keywords - candidate_skills)
    missing_preferred = sorted(preferred_keywords - candidate_skills)

    gaps = missing_required + [skill for skill in missing_preferred if skill not in missing_required]

    return gaps[:4]


def score_job(profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score one job, derive a recommendation label, and attach explanations.
    """
    skill_score, matched_skills, _ = _compute_skill_match(profile, job)
    role_score, _, best_preferred_role = _compute_role_match(profile, job)
    location_score = _compute_location_match(profile, job)
    internship_bonus = _compute_internship_signal_bonus(job)
    blockers = _check_blocking_constraints(profile, job)

    # Fit score is intentionally separated from blockers.
    raw_score = (
        (skill_score * 0.60)
        + (role_score * 0.25)
        + (location_score * 0.15)
        + internship_bonus
    )

    bounded_score = max(0.0, min(1.0, raw_score))
    final_score = round(bounded_score * 100, 2)

    has_explicit_internship = _has_explicit_internship_signal(job)

    if blockers:
        action_label = "Skip"
    elif final_score >= 70:
        action_label = "Apply Now"
    elif final_score >= 45:
        action_label = "Apply Later"
    elif has_explicit_internship:
        # If the role is clearly an internship and there are no blockers,
        # do not let it fall all the way to Skip just because the baseline
        # heuristics are still sparse.
        action_label = "Apply Later"
    else:
        action_label = "Skip"

    reasons = _generate_reasons(
        skill_score=skill_score,
        role_score=role_score,
        best_preferred_role=best_preferred_role,
        location_score=location_score,
        internship_bonus=internship_bonus,
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
            "internship_bonus": round(internship_bonus, 4),
        },
    }


def _blocking_sort_bucket(job: Dict[str, Any]) -> int:
    """
    Group blocked jobs into more useful buckets for display order.

    Bucket order:
    0 = no blockers
    1 = internship-like roles blocked only by degree timing / PhD constraints
    2 = roles blocked because they are not internships
    3 = roles blocked because they are senior-level
    4 = all other blocked roles
    """
    blockers = job["blocking_issues"]

    if not blockers:
        return 0

    blocker_text = " | ".join(blockers).lower()

    has_non_intern = "does not appear to be an internship" in blocker_text
    has_senior = "senior-level position" in blocker_text
    has_phd = "require a phd" in blocker_text
    has_grad_timing = "graduation timing may not match this role" in blocker_text

    if (has_phd or has_grad_timing) and not has_non_intern and not has_senior:
        return 1

    if has_non_intern and not has_senior:
        return 2

    if has_senior:
        return 3

    return 4


def _ranking_sort_key(job: Dict[str, Any]) -> tuple[int, int, int, float, float, str]:
    """
    Sort by recommendation priority, then blocker bucket, then blocker count,
    then internship signal strength, then score.

    This keeps:
    - blocker-free internships first
    - internship-like but blocked-by-PhD roles next
    - obvious non-intern or senior roles lower
    """
    internship_bonus = float(job["component_scores"].get("internship_bonus", 0.0))

    return (
        ACTION_PRIORITY.get(job["action_label"], 99),
        _blocking_sort_bucket(job),
        len(job["blocking_issues"]),
        -internship_bonus,
        -job["score"],
        job["title"],
    )


def rank_jobs(profile: Dict[str, Any], jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Score all jobs and return them in final recommendation order."""
    scored_jobs = [score_job(profile, job) for job in jobs]
    return sorted(scored_jobs, key=_ranking_sort_key)