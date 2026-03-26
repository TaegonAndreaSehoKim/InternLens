from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import load_candidate_profile
from src.ranking.baseline_scorer import rank_jobs


app = FastAPI(
    title="InternLens API",
    description="Internship application strategy optimizer API",
    version="0.1.0",
)


class RecommendRequest(BaseModel):
    profile_path: str = Field(
        default="data/processed/candidate_profile_example.json",
        description="Path to the candidate profile JSON file, relative to the project root.",
    )
    jobs_dir: str = Field(
        default="data/sample_jobs",
        description="Path to the directory containing job posting JSON files, relative to the project root.",
    )
    top_k: int = Field(default=10, ge=1, le=100)


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
    profile_path: str
    jobs_dir: str
    total_jobs_scored: int
    returned_jobs: int
    results: List[JobResult]


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    profile_path = PROJECT_ROOT / request.profile_path
    jobs_dir = PROJECT_ROOT / request.jobs_dir

    try:
        profile = load_candidate_profile(profile_path)
        jobs = load_all_job_postings(jobs_dir)
        ranked_jobs = rank_jobs(profile, jobs)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    top_results = ranked_jobs[: request.top_k]

    return RecommendResponse(
        profile_path=request.profile_path,
        jobs_dir=request.jobs_dir,
        total_jobs_scored=len(ranked_jobs),
        returned_jobs=len(top_results),
        results=top_results,
    )
