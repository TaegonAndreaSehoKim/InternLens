from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import (
    load_candidate_profile,
    normalize_candidate_profile,
)
from src.ranking.output_filters import filter_results_for_output, truncate_results
from src.ranking.baseline_scorer import (
    _has_description_internship_signal,
    _has_explicit_internship_signal,
    _looks_like_senior_role,
    rank_jobs,
)
from src.ranking.feedback_reranker import (
    apply_feedback_reranking,
    load_feedback_profile,
    normalize_feedback_profile,
)


app = FastAPI(
    title="InternLens API",
    description="Internship application strategy optimizer API",
    version="0.3.2",
)


class CandidateProfilePayload(BaseModel):
    profile_id: str
    resume_text: str
    degree_level: str
    grad_date: str
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    sponsorship_need: bool
    extracted_skills: List[str] = Field(default_factory=list)
    years_of_experience: int = 0
    notes: str = ""


class FeedbackEventPayload(BaseModel):
    job_id: str
    feedback_label: str


class FeedbackProfilePayload(BaseModel):
    profile_id: str
    events: List[FeedbackEventPayload] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    profile_path: Optional[str] = Field(
        default=None,
        description="Path to the candidate profile JSON file, relative to the project root.",
    )
    profile_data: Optional[CandidateProfilePayload] = Field(
        default=None,
        description="Inline candidate profile payload. If provided, this is used instead of profile_path.",
    )
    jobs_dir: str = Field(
        default="data/processed/jobs",
        description="Path to the directory containing job posting JSON files, relative to the project root.",
    )
    feedback_path: Optional[str] = Field(
        default=None,
        description="Optional path to a feedback JSON file, relative to the project root.",
    )
    feedback_data: Optional[FeedbackProfilePayload] = Field(
        default=None,
        description="Optional inline feedback payload. If provided, this is used instead of feedback_path.",
    )
    eligible_only: bool = Field(
        default=False,
        description="If true, return only jobs with no blocking issues.",
    )
    applyable_only: bool = Field(
        default=False,
        description="If true, return only jobs whose action label is not Skip.",
    )
    include_debug: bool = Field(
        default=False,
        description="If true, include raw scoring, blocker, and reranking debug fields in each result.",
    )
    top_k: int = Field(default=10, ge=1, le=100)

    @model_validator(mode="after")
    def validate_profile_source(self) -> "RecommendRequest":
        # Require at least one profile source so the endpoint has a ranking target.
        if self.profile_path is None and self.profile_data is None:
            raise ValueError("Either profile_path or profile_data must be provided.")
        return self


class FeedbackExplanation(BaseModel):
    source_job_id: str
    source_job_title: str
    feedback_label: str
    similarity: float
    adjustment: float
    shared_title_tokens: List[str]
    shared_skill_tokens: List[str]


class JobResult(BaseModel):
    job_id: str
    company: str
    title: str
    location: str
    score: Optional[float] = None
    action_label: Optional[str] = None
    matched_skills: Optional[List[str]] = None
    skill_gaps: Optional[List[str]] = None
    reasons: Optional[List[str]] = None
    blocking_issues: Optional[List[str]] = None
    component_scores: Optional[Dict[str, float]] = None
    recommendation: str
    fit_level: str
    eligibility_status: str
    summary: str
    why_apply: List[str]
    watchouts: List[str]
    application_link: Optional[str] = None

    # Expose reranking fields only when feedback-based reranking is applied.
    feedback_adjustment: Optional[float] = None
    reranked_score: Optional[float] = None
    feedback_explanations: Optional[List[FeedbackExplanation]] = None


class RecommendOverview(BaseModel):
    total_apply_now: int
    total_apply_later: int
    total_skip: int
    total_eligible: int
    total_blocked: int
    top_locations: List[str]
    common_blockers: List[str]
    highlighted_titles: List[str]


class RecommendResponse(BaseModel):
    profile_source: str
    jobs_dir: str
    feedback_source: Optional[str]
    reranking_applied: bool
    total_jobs_scored: int
    returned_jobs: int
    overview: RecommendOverview
    results: List[JobResult]


class JobDetailResponse(BaseModel):
    # Return one normalized job record through the API.
    job_id: str
    company: str
    title: str
    location: str
    description: str
    min_qualifications: str
    preferred_qualifications: str
    posting_date: str
    sponsorship_info: str
    employment_type: str
    source: str
    source_site: Optional[str] = None
    source_job_id: Optional[str] = None
    source_url: Optional[str] = None
    application_url: Optional[str] = None
    remote_status: Optional[str] = None
    team: Optional[str] = None
    short_description: str
    internship_signals: List[str]
    possible_requirements: List[str]
    possible_blockers: List[str]
    application_link: Optional[str] = None


def _build_profile_from_payload(profile_data: CandidateProfilePayload) -> Dict[str, Any]:
    # Reuse the shared normalization logic so file-based and inline inputs behave the same way.
    return normalize_candidate_profile(profile_data.model_dump())


def _build_feedback_from_payload(feedback_data: FeedbackProfilePayload) -> Dict[str, Any]:
    # Reuse the shared normalization logic so file-based and inline inputs behave the same way.
    return normalize_feedback_profile(feedback_data.model_dump())


def _recommendation_code(action_label: str) -> str:
    return action_label.lower().replace(" ", "_")


def _fit_level(score: float) -> str:
    if score >= 70:
        return "strong"
    if score >= 40:
        return "moderate"
    return "weak"


def _eligibility_status(blocking_issues: List[str]) -> str:
    return "blocked" if blocking_issues else "eligible"


def _application_link(job: Dict[str, Any]) -> Optional[str]:
    return str(job.get("application_url") or job.get("source_url") or "") or None


def _build_watchouts(job: Dict[str, Any]) -> List[str]:
    watchouts: List[str] = []

    for blocker in job.get("blocking_issues", []):
        watchouts.append(blocker)

    if not watchouts:
        skill_gaps = job.get("skill_gaps", [])
        if skill_gaps:
            watchouts.append(f"Skill gaps to review: {', '.join(skill_gaps[:3])}")

    return watchouts[:3]


def _build_user_summary(job: Dict[str, Any]) -> str:
    fit_level = _fit_level(float(job.get("score", 0)))
    eligibility_status = _eligibility_status(job.get("blocking_issues", []))
    reasons = job.get("reasons", [])

    if eligibility_status == "blocked":
        if reasons:
            return f"{fit_level.capitalize()} fit, but currently blocked: {reasons[0]}"
        return f"{fit_level.capitalize()} fit, but currently blocked by posting constraints."

    if reasons:
        return f"{fit_level.capitalize()} fit for this internship search: {reasons[0]}"

    return f"{fit_level.capitalize()} fit based on the current baseline signals."


def _enrich_job_result(job: Dict[str, Any], *, include_debug: bool) -> Dict[str, Any]:
    enriched = dict(job)
    enriched["recommendation"] = _recommendation_code(job["action_label"])
    enriched["fit_level"] = _fit_level(float(job["score"]))
    enriched["eligibility_status"] = _eligibility_status(job.get("blocking_issues", []))
    enriched["summary"] = _build_user_summary(job)
    enriched["why_apply"] = list(job.get("reasons", []))[:3]
    enriched["watchouts"] = _build_watchouts(job)
    enriched["application_link"] = _application_link(job)

    if not include_debug:
        for field in (
            "score",
            "action_label",
            "matched_skills",
            "skill_gaps",
            "reasons",
            "blocking_issues",
            "component_scores",
            "feedback_adjustment",
            "reranked_score",
            "feedback_explanations",
        ):
            enriched[field] = None

    return enriched


def _top_locations(jobs: List[Dict[str, Any]]) -> List[str]:
    location_counts = Counter(
        job["location"]
        for job in jobs
        if str(job.get("location", "")).strip()
    )
    return [location for location, _count in location_counts.most_common(3)]


def _common_blockers(jobs: List[Dict[str, Any]]) -> List[str]:
    blocker_counts = Counter(
        blocker
        for job in jobs
        for blocker in job.get("blocking_issues", [])
    )
    return [blocker for blocker, _count in blocker_counts.most_common(3)]


def _highlighted_titles(jobs: List[Dict[str, Any]]) -> List[str]:
    highlighted = [
        job["title"]
        for job in jobs
        if job.get("action_label") != "Skip"
    ]
    return highlighted[:3]


def _build_recommend_overview(jobs: List[Dict[str, Any]]) -> RecommendOverview:
    action_counts = Counter(job.get("action_label", "") for job in jobs)
    total_blocked = sum(1 for job in jobs if job.get("blocking_issues"))
    total_eligible = len(jobs) - total_blocked

    return RecommendOverview(
        total_apply_now=action_counts.get("Apply Now", 0),
        total_apply_later=action_counts.get("Apply Later", 0),
        total_skip=action_counts.get("Skip", 0),
        total_eligible=total_eligible,
        total_blocked=total_blocked,
        top_locations=_top_locations(jobs),
        common_blockers=_common_blockers(jobs),
        highlighted_titles=_highlighted_titles(jobs),
    )


def _short_description(description: str, *, max_length: int = 220) -> str:
    normalized = " ".join(str(description or "").split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _internship_signals(job: Dict[str, Any]) -> List[str]:
    signals: List[str] = []

    if _has_explicit_internship_signal(job):
        signals.append("Explicit internship wording in title or employment type")
    if _has_description_internship_signal(job):
        signals.append("Internship program wording in description")
    if str(job.get("remote_status", "")).strip():
        signals.append(f"Work mode: {job['remote_status']}")
    if str(job.get("team", "")).strip():
        signals.append(f"Team: {job['team']}")

    return signals[:4]


def _extract_requirement_items(job: Dict[str, Any]) -> List[str]:
    combined_parts = [
        str(job.get("min_qualifications", "")),
        str(job.get("preferred_qualifications", "")),
    ]
    normalized = "\n".join(part for part in combined_parts if part.strip())

    raw_items = [
        item.strip(" -")
        for item in normalized.replace("\r", "\n").split("\n")
        if item.strip()
    ]
    if raw_items:
        return raw_items[:4]

    description = " ".join(str(job.get("description", "")).split())
    sentences = [
        sentence.strip()
        for sentence in description.split(".")
        if sentence.strip()
    ]
    return sentences[:2]


def _possible_posting_blockers(job: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    combined_text = " ".join(
        [
            str(job.get("title", "")),
            str(job.get("description", "")),
            str(job.get("min_qualifications", "")),
            str(job.get("preferred_qualifications", "")),
            str(job.get("employment_type", "")),
            str(job.get("sponsorship_info", "")),
        ]
    ).lower()

    if not (_has_explicit_internship_signal(job) or _has_description_internship_signal(job)):
        blockers.append("This posting may not be an internship")
    if _looks_like_senior_role(job):
        blockers.append("This posting looks senior-level")
    if "phd" in combined_text:
        blockers.append("This posting may require a PhD")
    if "no sponsorship" in combined_text:
        blockers.append("This posting states sponsorship is not available")

    return blockers[:4]


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend", response_model=RecommendResponse, response_model_exclude_none=True)
def recommend(request: RecommendRequest) -> RecommendResponse:
    jobs_dir = PROJECT_ROOT / request.jobs_dir

    try:
        # Resolve the candidate profile from either inline payload or file path.
        if request.profile_data is not None:
            profile = _build_profile_from_payload(request.profile_data)
            profile_source = "inline_profile_payload"
        else:
            profile_path = PROJECT_ROOT / str(request.profile_path)
            profile = load_candidate_profile(profile_path)
            profile_source = str(request.profile_path)

        jobs = load_all_job_postings(jobs_dir)
        ranked_jobs = rank_jobs(profile, jobs)

        # Apply optional feedback-based reranking only when feedback data is provided.
        reranking_applied = False
        feedback_source: Optional[str] = None
        final_jobs = ranked_jobs

        if request.feedback_data is not None:
            feedback_profile = _build_feedback_from_payload(request.feedback_data)
            final_jobs = apply_feedback_reranking(ranked_jobs, jobs, feedback_profile)
            reranking_applied = True
            feedback_source = "inline_feedback_payload"
        elif request.feedback_path is not None:
            feedback_path = PROJECT_ROOT / request.feedback_path
            feedback_profile = load_feedback_profile(feedback_path)
            final_jobs = apply_feedback_reranking(ranked_jobs, jobs, feedback_profile)
            reranking_applied = True
            feedback_source = str(request.feedback_path)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    visible_jobs = filter_results_for_output(
        final_jobs,
        eligible_only=request.eligible_only,
        applyable_only=request.applyable_only,
    )
    top_results = truncate_results(visible_jobs, request.top_k)
    enriched_results = [
        _enrich_job_result(job, include_debug=request.include_debug)
        for job in top_results
    ]
    job_results = [JobResult(**job) for job in enriched_results]

    return RecommendResponse(
        profile_source=profile_source,
        jobs_dir=request.jobs_dir,
        feedback_source=feedback_source,
        reranking_applied=reranking_applied,
        total_jobs_scored=len(final_jobs),
        returned_jobs=len(job_results),
        overview=_build_recommend_overview(visible_jobs),
        results=job_results,
    )


@app.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, jobs_dir: str = "data/processed/jobs") -> JobDetailResponse:
    # Read one job from the processed jobs directory tree.
    jobs_dir_path = PROJECT_ROOT / jobs_dir

    try:
        jobs = load_all_job_postings(
            jobs_dir_path,
            suppress_duplicate_content=False,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    job = next((item for item in jobs if item["job_id"] == job_id), None)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobDetailResponse(
        job_id=job["job_id"],
        company=job["company"],
        title=job["title"],
        location=job["location"],
        description=job["description"],
        min_qualifications=job["min_qualifications"],
        preferred_qualifications=job["preferred_qualifications"],
        posting_date=job["posting_date"],
        sponsorship_info=job["sponsorship_info"],
        employment_type=job["employment_type"],
        source=job["source"],
        source_site=job.get("source_site"),
        source_job_id=job.get("source_job_id"),
        source_url=job.get("source_url"),
        application_url=job.get("application_url"),
        remote_status=job.get("remote_status"),
        team=job.get("team"),
        short_description=_short_description(job.get("description", "")),
        internship_signals=_internship_signals(job),
        possible_requirements=_extract_requirement_items(job),
        possible_blockers=_possible_posting_blockers(job),
        application_link=_application_link(job),
    )
