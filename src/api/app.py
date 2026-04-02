from __future__ import annotations

import sys
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
from src.ranking.baseline_scorer import rank_jobs
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
        default="data/sample_jobs",
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
    score: float
    action_label: str
    matched_skills: List[str]
    skill_gaps: List[str]
    reasons: List[str]
    blocking_issues: List[str]
    component_scores: Dict[str, float]

    # Expose reranking fields only when feedback-based reranking is applied.
    feedback_adjustment: Optional[float] = None
    reranked_score: Optional[float] = None
    feedback_explanations: Optional[List[FeedbackExplanation]] = None


class RecommendResponse(BaseModel):
    profile_source: str
    jobs_dir: str
    feedback_source: Optional[str]
    reranking_applied: bool
    total_jobs_scored: int
    returned_jobs: int
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


def _build_profile_from_payload(profile_data: CandidateProfilePayload) -> Dict[str, Any]:
    # Reuse the shared normalization logic so file-based and inline inputs behave the same way.
    return normalize_candidate_profile(profile_data.model_dump())


def _build_feedback_from_payload(feedback_data: FeedbackProfilePayload) -> Dict[str, Any]:
    # Reuse the shared normalization logic so file-based and inline inputs behave the same way.
    return normalize_feedback_profile(feedback_data.model_dump())


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend", response_model=RecommendResponse)
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

    top_results = final_jobs[: request.top_k]
    job_results = [JobResult(**job) for job in top_results]

    return RecommendResponse(
        profile_source=profile_source,
        jobs_dir=request.jobs_dir,
        feedback_source=feedback_source,
        reranking_applied=reranking_applied,
        total_jobs_scored=len(final_jobs),
        returned_jobs=len(job_results),
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
    )
