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
    "software engineering",
    "simulation",
    "computer vision",
    "llm",
    "vlm",
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
    "software engineer": "software engineering",
    "software engineering intern": "software engineering",
    "software development": "software engineering",
    "cv": "computer vision",
    "vision language model": "vlm",
    "large language model": "llm",
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

TECHNICAL_TITLE_FALLBACK_KEYWORDS = [
    "engineer",
    "engineering",
    "developer",
    "software",
    "scientist",
    "research",
    "researcher",
    "data",
    "analytics",
    "analytic",
    "analyst",
    "security",
    "network",
    "infrastructure",
    "platform",
    "automation",
    "systems",
    "machine learning",
    "ai",
]

STRONG_TECHNICAL_TITLE_FALLBACK_KEYWORDS = [
    "data",
    "analytics",
    "analytic",
    "analyst",
    "engineer",
    "engineering",
    "developer",
    "software",
    "scientist",
    "research",
    "researcher",
    "security",
    "network",
    "automation",
]

NON_TECHNICAL_TITLE_FALLBACK_KEYWORDS = [
    "marketing",
    "people",
    "hr",
    "human resources",
    "sales",
    "revenue",
    "operations",
    "enablement",
    "audit",
    "legal",
    "tax",
    "finance",
    "account executive",
    "partnerships",
    "events",
    "brand",
    "product manager",
    "program manager",
    "customer success",
    "recruiter",
    "talent",
]

NON_CORE_BUSINESS_INTERNSHIP_KEYWORDS = [
    "business analyst",
    "content marketing",
    "digital marketing",
    "email marketing",
    "graphic design",
    "marketing",
    "revenue operations",
    "sales operations",
    "marketing operations",
    "people operations",
    "hr operations",
    "human resources",
    "communications",
    "social media",
    "product manager",
    "product management",
    "customer success",
    "recruiter",
    "talent",
    "finance",
    "tax",
    "legal",
    "audit",
    "partnerships",
    "brand",
    "events",
]

CORE_TECHNICAL_TITLE_OVERRIDE_KEYWORDS = [
    "engineer",
    "engineering",
    "developer",
    "software",
    "scientist",
    "research",
    "researcher",
    "network",
    "security",
    "infrastructure",
    "platform",
]

BUSINESS_PROFILE_KEYWORDS = [
    "business",
    "marketing",
    "communications",
    "finance",
    "accounting",
    "economics",
    "operations",
    "supply chain",
    "human resources",
    "policy",
    "political science",
    "public policy",
    "law",
    "education",
    "journalism",
    "design",
]

MAJOR_MATCH_KEYWORDS = {
    "computer science": ["software", "engineer", "developer", "backend", "frontend", "full stack", "systems", "python", "java", "javascript"],
    "software engineering": ["software", "engineer", "developer", "backend", "frontend", "full stack", "testing", "devops"],
    "computer engineering": ["embedded", "firmware", "hardware", "systems", "electrical", "software", "robotics"],
    "data science": ["data", "analytics", "machine learning", "statistics", "experiment", "sql", "python", "model"],
    "artificial intelligence": ["ai", "machine learning", "deep learning", "llm", "computer vision", "model", "research"],
    "machine learning": ["machine learning", "deep learning", "model", "pytorch", "tensorflow", "ai", "research"],
    "information systems": ["systems", "business analyst", "data", "analytics", "process", "crm", "database"],
    "information technology": ["it", "support", "systems", "network", "cloud", "security", "infrastructure"],
    "cybersecurity": ["security", "threat", "risk", "incident", "compliance", "network", "governance"],
    "electrical engineering": ["electrical", "electronics", "hardware", "circuit", "firmware", "embedded", "power"],
    "mechanical engineering": ["mechanical", "manufacturing", "cad", "thermal", "robotics", "hardware"],
    "civil engineering": ["civil", "construction", "structural", "transportation", "infrastructure"],
    "industrial engineering": ["operations", "process", "manufacturing", "supply chain", "quality", "optimization"],
    "aerospace engineering": ["aerospace", "flight", "avionics", "propulsion", "systems", "manufacturing"],
    "biomedical engineering": ["biomedical", "medical device", "clinical", "biology", "healthcare", "lab"],
    "chemical engineering": ["chemical", "process", "materials", "manufacturing", "energy", "lab"],
    "environmental engineering": ["environmental", "sustainability", "climate", "water", "energy"],
    "mathematics": ["math", "statistics", "quantitative", "modeling", "optimization", "analysis"],
    "statistics": ["statistics", "data", "analytics", "experiment", "forecast", "model", "risk"],
    "physics": ["physics", "research", "simulation", "modeling", "hardware", "quantum"],
    "chemistry": ["chemistry", "lab", "materials", "pharmaceutical", "research"],
    "biology": ["biology", "lab", "clinical", "research", "biotech", "life sciences"],
    "biochemistry": ["biochemistry", "biology", "chemistry", "lab", "biotech", "pharmaceutical"],
    "bioinformatics": ["bioinformatics", "biology", "genomics", "data", "python", "statistics", "research"],
    "neuroscience": ["neuroscience", "research", "clinical", "lab", "psychology", "biology"],
    "public health": ["public health", "clinical", "epidemiology", "healthcare", "policy", "research"],
    "nursing": ["nursing", "clinical", "patient", "healthcare", "medical"],
    "pharmacy": ["pharmacy", "pharmaceutical", "clinical", "drug", "regulatory"],
    "business administration": ["business", "strategy", "operations", "management", "sales", "customer"],
    "marketing": ["marketing", "content", "brand", "growth", "social media", "campaign", "seo"],
    "finance": ["finance", "financial", "investment", "valuation", "risk", "fp&a", "banking"],
    "accounting": ["accounting", "audit", "tax", "financial reporting", "compliance"],
    "economics": ["economics", "economic", "policy", "research", "market", "forecast", "quantitative"],
    "operations management": ["operations", "process", "program", "project", "supply chain", "logistics"],
    "supply chain management": ["supply chain", "logistics", "procurement", "inventory", "manufacturing"],
    "human resources": ["human resources", "people", "talent", "recruiting", "hr", "employee"],
    "psychology": ["psychology", "research", "user research", "people", "behavior", "clinical"],
    "sociology": ["sociology", "research", "policy", "community", "social impact"],
    "political science": ["policy", "government", "public affairs", "political", "regulatory"],
    "public policy": ["policy", "government", "regulatory", "public affairs", "advocacy"],
    "international relations": ["international", "policy", "government", "communications", "partnerships"],
    "law": ["legal", "law", "compliance", "policy", "contract", "regulatory"],
    "education": ["education", "curriculum", "instructional", "teaching", "program"],
    "communications": ["communications", "public relations", "media", "writing", "content"],
    "journalism": ["journalism", "editorial", "media", "writing", "content"],
    "english": ["writing", "editing", "content", "communications", "editorial"],
    "graphic design": ["graphic design", "visual design", "brand", "creative", "illustration"],
    "product design": ["product design", "ux", "ui", "prototype", "figma", "design"],
    "ux design": ["ux", "user research", "design", "prototype", "usability", "figma"],
    "architecture": ["architecture", "design", "construction", "urban", "planning"],
    "urban planning": ["urban", "planning", "policy", "transportation", "community"],
    "environmental science": ["environmental", "sustainability", "climate", "research", "energy"],
    "sustainability": ["sustainability", "climate", "esg", "environmental", "energy"],
}


def _title_supports_fallback_skill_matching(title: str) -> bool:
    """
    Use title/description fallback skills only for roles that look technical,
    data-oriented, research-oriented, or engineering-oriented.

    Negative business/people/marketing signals should usually override weak
    AI-flavored wording such as "AI Innovation".
    """
    normalized_title = _canonicalize_text(title.lower())

    has_positive_signal = any(
        keyword in normalized_title
        for keyword in TECHNICAL_TITLE_FALLBACK_KEYWORDS
    )
    has_strong_positive_signal = any(
        keyword in normalized_title
        for keyword in STRONG_TECHNICAL_TITLE_FALLBACK_KEYWORDS
    )
    has_negative_signal = any(
        keyword in normalized_title
        for keyword in NON_TECHNICAL_TITLE_FALLBACK_KEYWORDS
    )

    # Strong technical titles like Data Engineer / Security Engineer /
    # Business Analyst / Research Engineer should still get fallback support.
    if has_strong_positive_signal:
        return True

    # Non-technical titles should not inherit noisy ML/Python matches from
    # broad descriptions or AI-innovation wording.
    if has_negative_signal:
        return False

    if has_positive_signal:
        return True

    return False


def _profile_supports_non_core_business(profile: Dict[str, Any]) -> bool:
    profile_context = _canonicalize_text(
        " ".join(
            [
                str(profile.get("major", "")),
                " ".join(profile.get("preferred_roles", [])),
                " ".join(profile.get("target_industries", [])),
            ]
        )
    )

    return any(keyword in profile_context for keyword in BUSINESS_PROFILE_KEYWORDS)


def _looks_like_non_core_business_internship(job: Dict[str, Any], profile: Dict[str, Any] | None = None) -> bool:
    """
    Identify internship titles that look adjacent to business/ops work rather
    than core engineering, research, or platform roles.

    This is intentionally conservative and is used to prevent noisy adjacent
    roles from outranking core engineering, research, or data internships.
    """
    normalized_context = _canonicalize_text(
        " ".join(
            [
                str(job.get("title", "")),
                str(job.get("team", "")),
            ]
        )
    )

    if "operations research" in normalized_context:
        return False

    has_non_core_signal = any(
        keyword in normalized_context
        for keyword in NON_CORE_BUSINESS_INTERNSHIP_KEYWORDS
    ) or "coordinator" in normalized_context
    has_core_technical_override = any(
        keyword in normalized_context
        for keyword in CORE_TECHNICAL_TITLE_OVERRIDE_KEYWORDS
    )

    if profile is not None and _profile_supports_non_core_business(profile):
        return False

    return has_non_core_signal and not has_core_technical_override

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

def _extract_job_skill_keywords(job: Dict[str, Any]) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
    """
    Extract skill keywords from multiple job fields.

    We still trust qualifications the most, but title and description should
    contribute lighter-weight signals so sparse postings are not invisible.
    """
    required_keywords = _extract_keywords_from_text(job["min_qualifications"])
    preferred_keywords = _extract_keywords_from_text(job["preferred_qualifications"])
    title_keywords = _extract_keywords_from_text(job["title"])
    description_keywords = _extract_keywords_from_text(job["description"])

    return required_keywords, preferred_keywords, title_keywords, description_keywords

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
    Compare candidate skills with job keywords from qualifications, title,
    and description.

    Required/preferred qualifications remain the primary source of truth.
    Title/description are used only as fallback signals when qualification
    fields are sparse and the title looks technical enough to trust them.
    """
    candidate_skills = _normalize_candidate_skills(profile)

    (
        required_keywords,
        preferred_keywords,
        title_keywords,
        description_keywords,
    ) = _extract_job_skill_keywords(job)

    has_structured_qualifications = bool(required_keywords or preferred_keywords)

    required_matches = sorted(candidate_skills & required_keywords)
    preferred_matches = sorted(candidate_skills & preferred_keywords)

    if has_structured_qualifications:
        # For curated/sample jobs, trust structured qualification fields first.
        matched_skills = sorted(set(required_matches + preferred_matches))

        required_overlap_score = _safe_ratio(len(required_matches), len(required_keywords))
        preferred_overlap_score = _safe_ratio(len(preferred_matches), len(preferred_keywords))

        skill_score = min(
            1.0,
            (required_overlap_score * 0.75)
            + (preferred_overlap_score * 0.25),
        )
    else:
        use_fallback = _title_supports_fallback_skill_matching(job["title"])

        if use_fallback:
            title_matches = sorted(candidate_skills & title_keywords)
            description_matches = sorted(candidate_skills & description_keywords)
        else:
            title_matches = []
            description_matches = []

        matched_skills = sorted(set(required_matches + preferred_matches + title_matches + description_matches))

        required_overlap_score = _safe_ratio(len(required_matches), len(required_keywords))
        preferred_overlap_score = _safe_ratio(len(preferred_matches), len(preferred_keywords))
        title_overlap_score = _safe_ratio(len(title_matches), len(title_keywords))
        description_overlap_score = _safe_ratio(len(description_matches), len(description_keywords))

        skill_score = min(
            1.0,
            (required_overlap_score * 0.50)
            + (preferred_overlap_score * 0.20)
            + (title_overlap_score * 0.20)
            + (description_overlap_score * 0.10),
        )

    return skill_score, matched_skills, required_matches

def _compute_role_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str], Optional[str]]:
    """
    Compare the job title to each preferred role and keep the best match.

    We return the best preferred role string so explanation text can use the
    full role instead of a single token like "applied" or "machine".
    If no preferred roles are provided, treat title fit as neutral so the
    candidate can search across all internship roles without a title penalty.
    """
    title_tokens = _meaningful_role_tokens(job["title"])

    preferred_roles = [
        str(role)
        for role in profile.get("preferred_roles", [])
        if str(role).strip()
    ]

    if not preferred_roles:
        return 1.0, [], None

    best_score = 0.0
    best_overlap_tokens: List[str] = []
    best_preferred_role: Optional[str] = None

    for preferred_role in preferred_roles:
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

    v1 supports simple substring matching plus a stricter remote fallback.
    Generic labels such as "In-Office" should not count as matching a preferred
    geographic target like California.
    """
    job_location = job["location"].lower().strip()
    remote_status = job.get("remote_status", "").lower().strip()
    preferred_locations = [
        str(location).lower().strip()
        for location in profile.get("preferred_locations", [])
        if str(location).strip()
    ]

    if not preferred_locations:
        return 1.0

    generic_non_geographic_locations = {
        "in-office",
        "in office",
        "onsite",
        "on-site",
        "office",
    }

    for preferred in preferred_locations:
        if preferred == "remote":
            continue

        if job_location in generic_non_geographic_locations:
            continue

        if preferred and preferred in job_location:
            return 1.0

    if remote_status == "remote" and any(
        preferred_location == "remote"
        for preferred_location in preferred_locations
    ):
        return 1.0

    return 0.0


def _profile_majors(profile: Dict[str, Any]) -> List[str]:
    majors = profile.get("majors", [])
    if isinstance(majors, list):
        normalized_majors = [
            _canonicalize_text(str(major).strip().lower())
            for major in majors
            if str(major).strip()
        ]
        if normalized_majors:
            return normalized_majors

    major = _canonicalize_text(str(profile.get("major", "")).strip().lower())
    return [major] if major else []


def _compute_major_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Tuple[float, List[str]]:
    majors = [major for major in _profile_majors(profile) if major and major != "other"]
    if not majors:
        return 0.0, []

    keywords = sorted({
        keyword
        for major in majors
        for keyword in MAJOR_MATCH_KEYWORDS.get(major, [])
    })
    if not keywords:
        return 0.0, []

    job_context = _canonicalize_text(
        " ".join(
            [
                str(job.get("title", "")),
                str(job.get("team", "")),
                str(job.get("description", "")),
                str(job.get("min_qualifications", "")),
                str(job.get("preferred_qualifications", "")),
                str(job.get("employment_type", "")),
            ]
        )
    )

    matches = sorted({keyword for keyword in keywords if keyword in job_context})
    if not matches:
        return 0.0, []

    # Major is an important directional signal, but it should not overpower
    # explicit skills and preferred-role alignment.
    return min(1.0, 0.35 + (0.13 * len(matches))), matches


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
    has_location_preferences: bool,
    major_score: float,
    major_matches: List[str],
    internship_bonus: float,
    matched_skills: List[str],
    blockers: List[str],
) -> List[str]:
    """
    Build short, product-style explanation text for the recommendation output.
    """
    reasons: List[str] = []

    if skill_score >= 0.15 and matched_skills:
        reasons.append(f"Matched on key skills: {', '.join(matched_skills[:4])}")

    if role_score >= 0.34 and best_preferred_role:
        reasons.append(f"Title aligns with preferred role: {best_preferred_role}")

    if major_score >= 0.35 and major_matches:
        reasons.append(f"Major aligns with posting signals: {', '.join(major_matches[:3])}")

    if internship_bonus > 0:
        reasons.append("Posting explicitly identifies this as an internship")

    if has_location_preferences and location_score >= 1.0:
        reasons.append("Location matches a preferred target")

    if blockers:
        reasons.append("Blocked by eligibility constraints in the posting")

    if not reasons:
        reasons.append("Limited match signals beyond the current baseline heuristics")

    return reasons[:3]


def _generate_skill_gaps(profile: Dict[str, Any], job: Dict[str, Any]) -> List[str]:
    """Surface a few missing skills for explanation output."""
    candidate_skills = _normalize_candidate_skills(profile)

    (
        required_keywords,
        preferred_keywords,
        title_keywords,
        _description_keywords,
    ) = _extract_job_skill_keywords(job)

    has_structured_qualifications = bool(required_keywords or preferred_keywords)

    missing_required = sorted(required_keywords - candidate_skills)
    missing_preferred = sorted(preferred_keywords - candidate_skills)

    gaps = missing_required + [skill for skill in missing_preferred if skill not in missing_required]

    if not has_structured_qualifications and _title_supports_fallback_skill_matching(job["title"]):
        missing_title = sorted(title_keywords - candidate_skills)
        gaps += [skill for skill in missing_title if skill not in gaps]

    return gaps[:4]


def score_job(profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score one job, derive a recommendation label, and attach explanations.
    """
    skill_score, matched_skills, _ = _compute_skill_match(profile, job)
    role_score, _, best_preferred_role = _compute_role_match(profile, job)
    has_role_preferences = any(
        str(role).strip() for role in profile.get("preferred_roles", [])
    )
    location_score = _compute_location_match(profile, job)
    has_location_preferences = any(
        str(location).strip() for location in profile.get("preferred_locations", [])
    )
    major_score, major_matches = _compute_major_match(profile, job)
    internship_bonus = _compute_internship_signal_bonus(job)
    blockers = _check_blocking_constraints(profile, job)

    # Fit score is intentionally separated from blockers.
    raw_score = (
        (skill_score * 0.50)
        + (role_score * 0.22)
        + (major_score * 0.18)
        + (location_score * 0.10)
        + internship_bonus
    )

    bounded_score = max(0.0, min(1.0, raw_score))
    final_score = round(bounded_score * 100, 2)

    has_explicit_internship = _has_explicit_internship_signal(job)
    looks_like_non_core_business_internship = _looks_like_non_core_business_internship(job, profile)
    has_relevance_signal = (
        bool(matched_skills)
        or (has_role_preferences and role_score >= 0.20)
        or major_score >= 0.35
    )

    if blockers:
        action_label = "Skip"
    elif looks_like_non_core_business_internship:
        action_label = "Skip"
    elif final_score >= 70:
        action_label = "Apply Now"
    elif final_score >= 45:
        action_label = "Apply Later"
    elif (
        has_explicit_internship
        and has_relevance_signal
        and not looks_like_non_core_business_internship
    ):
        # A clear internship can still be Apply Later even when the baseline
        # score is modest, but only if we see some role or skill relevance.
        action_label = "Apply Later"
    else:
        action_label = "Skip"

    reasons = _generate_reasons(
        skill_score=skill_score,
        role_score=role_score,
        best_preferred_role=best_preferred_role,
        location_score=location_score,
        has_location_preferences=has_location_preferences,
        major_score=major_score,
        major_matches=major_matches,
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
        "source": job.get("source"),
        "source_site": job.get("source_site"),
        "source_job_id": job.get("source_job_id"),
        "source_url": job.get("source_url"),
        "application_url": job.get("application_url"),
        "remote_status": job.get("remote_status"),
        "team": job.get("team"),
        "employment_type": job.get("employment_type"),
        "posting_date": job.get("posting_date"),
        "fetched_at": job.get("fetched_at"),
        "expires_at": job.get("expires_at"),
        "freshness_days": job.get("freshness_days"),
        "score": final_score,
        "action_label": action_label,
        "matched_skills": matched_skills,
        "skill_gaps": skill_gaps,
        "reasons": reasons,
        "blocking_issues": blockers,
        "component_scores": {
            "skill_score": round(skill_score, 4),
            "role_score": round(role_score, 4),
            "major_score": round(major_score, 4),
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
