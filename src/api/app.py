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
from src.ranking.baseline_scorer import rank_jobs


app = FastAPI(
    title="InternLens API",
    description="Internship application strategy optimizer API",
    version="0.2.0",
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
    top_k: int = Field(default=10, ge=1, le=100)

    @model_validator(mode="after")
    def validate_profile_source(self) -> "RecommendRequest":
        if self.profile_path is None and self.profile_data is None:
            raise ValueError("Either profile_path or profile_data must be provided.")
        return self


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


class RecommendResponse(BaseModel):
    profile_source: str
    jobs_dir: str
    total_jobs_scored: int
    returned_jobs: int
    results: List[JobResult]


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _normalize_list(values: List[str]) -> List[str]:
    normalized: List[str] = []
    for value in values:
        if isinstance(value, str) and value.strip():
            normalized.append(_normalize_text(value))
    return normalized


def _build_profile_from_payload(profile_data: CandidateProfilePayload) -> Dict[str, Any]:
    parsed_profile = {
        "profile_id": profile_data.profile_id,
        "resume_text": profile_data.resume_text,
        "degree_level": _normalize_text(profile_data.degree_level),
        "grad_date": str(profile_data.grad_date).strip(),
        "preferred_roles": _normalize_list(profile_data.preferred_roles),
        "preferred_locations": _normalize_list(profile_data.preferred_locations),
        "target_industries": _normalize_list(profile_data.target_industries),
        "sponsorship_need": bool(profile_data.sponsorship_need),
        "extracted_skills": _normalize_list(profile_data.extracted_skills),
        "years_of_experience": profile_data.years_of_experience,
        "notes": profile_data.notes,
    }
    parsed_profile["skill_set"] = set(parsed_profile["extracted_skills"])
    return parsed_profile


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    jobs_dir = PROJECT_ROOT / request.jobs_dir

    try:
        if request.profile_data is not None:
            profile = _build_profile_from_payload(request.profile_data)
            profile_source = "inline_profile_payload"
        else:
            profile_path = PROJECT_ROOT / str(request.profile_path)
            from src.preprocessing.profile_parser import load_candidate_profile

            profile = load_candidate_profile(profile_path)
            profile_source = str(request.profile_path)

        jobs = load_all_job_postings(jobs_dir)
        ranked_jobs = rank_jobs(profile, jobs)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    top_results = ranked_jobs[: request.top_k]
    job_results = [JobResult(**job) for job in top_results]

    return RecommendResponse(
        profile_source=profile_source,
        jobs_dir=request.jobs_dir,
        total_jobs_scored=len(ranked_jobs),
        returned_jobs=len(job_results),
        results=job_results,
    )