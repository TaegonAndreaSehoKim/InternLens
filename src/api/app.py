from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import (
    load_candidate_profile,
    normalize_candidate_profile,
)
from src.preprocessing.resume_parser import parse_resume_file
from src.storage.profile_store import (
    DEFAULT_USER_ID,
    add_feedback_events,
    clear_profile_job_state,
    create_recommendation_run,
    create_profile,
    default_database_path,
    get_recommendation_run,
    get_feedback_events,
    get_profile_job_state,
    get_profile,
    list_profile_job_states,
    list_recommendation_runs,
    upsert_profile_job_state,
    update_profile,
)
from src.api.auth import current_user_id
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
from src.api.settings import DEFAULT_CORS_ORIGINS, DEFAULT_JOBS_DIR, env_list, env_value, resolve_project_path


DEFAULT_API_JOBS_DIR = env_value("INTERNLENS_JOBS_DIR", DEFAULT_JOBS_DIR)
CORS_ORIGINS = env_list("INTERNLENS_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)

app = FastAPI(
    title="InternLens API",
    description="Internship application strategy optimizer API",
    version="0.3.2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PROFILE_FIELDS = (
    "profile_id",
    "resume_text",
    "degree_level",
    "major",
    "majors",
    "grad_date",
    "preferred_roles",
    "preferred_locations",
    "target_industries",
    "sponsorship_need",
    "extracted_skills",
    "years_of_experience",
    "notes",
)
ACCOUNT_PROFILE_ID = "default"


class CandidateProfilePayload(BaseModel):
    profile_id: str
    resume_text: str
    degree_level: str
    major: str = "Other"
    majors: List[str] = Field(default_factory=list)
    grad_date: str
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    sponsorship_need: bool
    extracted_skills: List[str] = Field(default_factory=list)
    years_of_experience: int = 0
    notes: str = ""


class AccountProfilePayload(BaseModel):
    resume_text: str
    degree_level: str
    major: str = "Other"
    majors: List[str] = Field(default_factory=list)
    grad_date: str
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    sponsorship_need: bool
    extracted_skills: List[str] = Field(default_factory=list)
    years_of_experience: int = 0
    notes: str = ""


class ResumeParseResponse(BaseModel):
    filename: str
    parsed_profile: AccountProfilePayload
    suggestions: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    extracted_text_preview: str = ""


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
        default=DEFAULT_API_JOBS_DIR,
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
    suppress_similar_results: bool = Field(
        default=False,
        description="If true, suppress near-duplicate recommendation results that look like the same posting.",
    )
    top_k: int = Field(default=10, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_profile_source(self) -> "RecommendRequest":
        # Require at least one profile source so the endpoint has a ranking target.
        if self.profile_path is None and self.profile_data is None:
            raise ValueError("Either profile_path or profile_data must be provided.")
        return self


class ProfileUpdatePayload(BaseModel):
    resume_text: Optional[str] = None
    degree_level: Optional[str] = None
    major: Optional[str] = None
    majors: Optional[List[str]] = None
    grad_date: Optional[str] = None
    preferred_roles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    target_industries: Optional[List[str]] = None
    sponsorship_need: Optional[bool] = None
    extracted_skills: Optional[List[str]] = None
    years_of_experience: Optional[int] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_non_empty_update(self) -> "ProfileUpdatePayload":
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one profile field must be provided for update.")
        return self


class StoredFeedbackEvent(BaseModel):
    job_id: str
    feedback_label: str
    created_at: Optional[str] = None


class StoredProfileResponse(CandidateProfilePayload):
    created_at: str
    updated_at: str


class StoredFeedbackResponse(BaseModel):
    profile_id: str
    events: List[StoredFeedbackEvent]


class JobStateRequest(BaseModel):
    run_id: Optional[str] = None


class JobActionRequest(BaseModel):
    action: Literal["save", "dismiss", "apply", "clear"]
    run_id: Optional[str] = None


class ProfileRecommendRequest(BaseModel):
    jobs_dir: str = Field(
        default=DEFAULT_API_JOBS_DIR,
        description="Path to the directory containing job posting JSON files, relative to the project root.",
    )
    eligible_only: bool = Field(default=False)
    applyable_only: bool = Field(default=False)
    include_debug: bool = Field(default=False)
    suppress_similar_results: bool = Field(default=False)
    include_feedback: bool = Field(
        default=True,
        description="If true, apply reranking based on persisted feedback events for this profile.",
    )
    exclude_dismissed: bool = Field(
        default=True,
        description="If true, suppress jobs the user has already marked as dismissed.",
    )
    exclude_applied: bool = Field(
        default=True,
        description="If true, suppress jobs the user has already marked as applied.",
    )
    save_run: bool = Field(
        default=True,
        description="If true, persist this recommendation run and its result snapshot.",
    )
    top_k: int = Field(default=10, ge=1, le=1000)


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
    posting_date: Optional[str] = None
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
    fetched_at: Optional[str] = None
    expires_at: Optional[str] = None
    freshness_days: Optional[int] = None
    user_job_state: Optional[str] = None
    user_job_state_source_run_id: Optional[str] = None
    user_job_state_updated_at: Optional[str] = None

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
    run_id: Optional[str] = None
    profile_source: str
    jobs_dir: str
    feedback_source: Optional[str]
    reranking_applied: bool
    total_jobs_scored: int
    returned_jobs: int
    overview: RecommendOverview
    results: List[JobResult]


class RecommendationRunSummary(BaseModel):
    run_id: str
    profile_id: str
    jobs_dir: str
    top_k: int
    eligible_only: bool
    applyable_only: bool
    suppress_similar_results: bool = False
    include_feedback: bool
    include_debug: bool
    reranking_applied: bool
    feedback_source: Optional[str]
    total_jobs_scored: int
    returned_jobs: int
    created_at: str


class RecommendationRunListResponse(BaseModel):
    profile_id: str
    runs: List[RecommendationRunSummary]


class StoredJobStateSnapshot(BaseModel):
    job_id: str
    company: str
    title: str
    location: str
    posting_date: Optional[str] = None
    recommendation: str
    fit_level: str
    eligibility_status: str
    summary: str
    why_apply: List[str]
    watchouts: List[str]
    matched_skills: Optional[List[str]] = None
    skill_gaps: Optional[List[str]] = None
    component_scores: Optional[Dict[str, float]] = None
    fetched_at: Optional[str] = None
    expires_at: Optional[str] = None
    freshness_days: Optional[int] = None
    application_link: Optional[str] = None


class StoredJobState(BaseModel):
    profile_id: str
    job_id: str
    state: str
    source_run_id: Optional[str]
    job_snapshot: Optional[StoredJobStateSnapshot] = None
    created_at: str
    updated_at: str


class StoredJobStateListResponse(BaseModel):
    profile_id: str
    state: str
    jobs: List[StoredJobState]


class JobActionResponse(BaseModel):
    profile_id: str
    job_id: str
    action: str
    job_state: Optional[StoredJobState] = None
    feedback_synced: bool = False
    feedback_label: Optional[str] = None


class ProfileSummaryResponse(BaseModel):
    profile_id: str
    recommendation_run_count: int
    saved_jobs_count: int
    dismissed_jobs_count: int
    applied_jobs_count: int
    feedback_event_count: int
    feedback_label_counts: Dict[str, int]
    last_recommendation_at: Optional[str] = None
    last_feedback_at: Optional[str] = None
    last_saved_job_at: Optional[str] = None
    last_dismissed_job_at: Optional[str] = None
    last_applied_job_at: Optional[str] = None


class ProfileActivityItem(BaseModel):
    activity_type: str
    created_at: str
    job_id: Optional[str] = None
    run_id: Optional[str] = None
    label: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None


class ProfileActivityResponse(BaseModel):
    profile_id: str
    activities: List[ProfileActivityItem]


class DashboardNextAction(BaseModel):
    action: str
    label: str
    description: str
    priority: int
    target_job_id: Optional[str] = None
    target_run_id: Optional[str] = None


class ProfileDashboardResponse(BaseModel):
    profile_id: str
    summary: ProfileSummaryResponse
    recommended_next_actions: List[DashboardNextAction]
    activity: ProfileActivityResponse
    recent_runs: List[RecommendationRunSummary]
    saved_jobs: List[StoredJobState]
    dismissed_jobs: List[StoredJobState]
    applied_jobs: List[StoredJobState]


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
    fetched_at: Optional[str] = None
    expires_at: Optional[str] = None
    freshness_days: Optional[int] = None
    short_description: str
    internship_signals: List[str]
    possible_requirements: List[str]
    possible_blockers: List[str]
    application_link: Optional[str] = None


def _database_path() -> Path:
    configured_path = env_value("INTERNLENS_DB_PATH", "")
    if configured_path:
        return resolve_project_path(PROJECT_ROOT, configured_path)
    return default_database_path(PROJECT_ROOT)


def _build_profile_from_payload(profile_data: CandidateProfilePayload) -> Dict[str, Any]:
    # Reuse the shared normalization logic so file-based and inline inputs behave the same way.
    return normalize_candidate_profile(profile_data.model_dump())


def _build_account_profile_from_payload(profile_data: AccountProfilePayload) -> Dict[str, Any]:
    return normalize_candidate_profile(
        profile_data.model_dump() | {"profile_id": ACCOUNT_PROFILE_ID}
    )


def _build_feedback_from_payload(feedback_data: FeedbackProfilePayload) -> Dict[str, Any]:
    # Reuse the shared normalization logic so file-based and inline inputs behave the same way.
    return normalize_feedback_profile(feedback_data.model_dump())


def _profile_response_payload(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {field: profile[field] for field in PROFILE_FIELDS if field in profile} | {
        "created_at": profile["created_at"],
        "updated_at": profile["updated_at"],
    }


def _profile_input_payload(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {field: profile[field] for field in PROFILE_FIELDS if field in profile}


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


def _annotate_results_with_job_state(
    jobs: List[Dict[str, Any]],
    job_state_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    annotated_jobs: List[Dict[str, Any]] = []
    for job in jobs:
        enriched_job = dict(job)
        enriched_job.pop("user_job_state", None)
        enriched_job.pop("user_job_state_source_run_id", None)
        job_state = job_state_by_id.get(str(job.get("job_id")))
        if job_state is not None:
            enriched_job["user_job_state"] = job_state["state"]
            enriched_job["user_job_state_source_run_id"] = job_state.get("source_run_id")
            enriched_job["user_job_state_updated_at"] = job_state.get("updated_at")
        annotated_jobs.append(enriched_job)
    return annotated_jobs


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


def _build_feedback_profile_from_events(profile_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
    return normalize_feedback_profile(
        {
            "profile_id": profile_id,
            "events": [
                {
                    "job_id": event["job_id"],
                    "feedback_label": event["feedback_label"],
                }
                for event in events
            ],
        }
    )


def _stored_job_state_response(state_payload: Dict[str, Any]) -> StoredJobState:
    snapshot = state_payload.get("job_snapshot")
    return StoredJobState(
        profile_id=state_payload["profile_id"],
        job_id=state_payload["job_id"],
        state=state_payload["state"],
        source_run_id=state_payload.get("source_run_id"),
        job_snapshot=StoredJobStateSnapshot(**snapshot) if snapshot is not None else None,
        created_at=state_payload["created_at"],
        updated_at=state_payload["updated_at"],
    )


def _apply_job_action(
    profile_id: str,
    job_id: str,
    action: str,
    run_id: Optional[str],
    *,
    user_id: str = DEFAULT_USER_ID,
) -> JobActionResponse:
    stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
    if stored_profile is None:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

    if action in {"save", "dismiss", "apply"}:
        state_by_action = {
            "save": "saved",
            "dismiss": "dismissed",
            "apply": "applied",
        }
        feedback_label_by_action = {
            "save": "saved",
            "dismiss": "skipped",
            "apply": "applied",
        }
        state = state_by_action[action]
        existing_state = get_profile_job_state(_database_path(), profile_id, job_id, user_id=user_id)
        should_sync_feedback = existing_state is None or existing_state["state"] != state
        try:
            stored_state = upsert_profile_job_state(
                _database_path(),
                profile_id=profile_id,
                user_id=user_id,
                job_id=job_id,
                state=state,
                source_run_id=run_id,
            )
            if should_sync_feedback:
                add_feedback_events(
                    _database_path(),
                    profile_id,
                    [{"job_id": job_id, "feedback_label": feedback_label_by_action[action]}],
                    user_id=user_id,
                )
        except ValueError as e:
            detail = str(e)
            if "Profile not found" in detail or "Recommendation run not found" in detail:
                raise HTTPException(status_code=404, detail=detail) from e
            raise HTTPException(status_code=400, detail=detail) from e

        return JobActionResponse(
            profile_id=profile_id,
            job_id=job_id,
            action=action,
            job_state=_stored_job_state_response(stored_state),
            feedback_synced=should_sync_feedback,
            feedback_label=feedback_label_by_action[action] if should_sync_feedback else None,
        )

    existing_state = get_profile_job_state(_database_path(), profile_id, job_id, user_id=user_id)
    if existing_state is None:
        raise HTTPException(status_code=404, detail=f"Job state not found: {job_id}")

    try:
        cleared = clear_profile_job_state(
            _database_path(),
            profile_id,
            job_id,
            existing_state["state"],
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not cleared:
        raise HTTPException(status_code=404, detail=f"Job state not found: {job_id}")

    return JobActionResponse(
        profile_id=profile_id,
        job_id=job_id,
        action=action,
        job_state=None,
    )


def _build_profile_activity(
    profile_id: str,
    *,
    recommendation_runs: List[Dict[str, Any]],
    feedback_events: List[Dict[str, Any]],
    saved_jobs: List[Dict[str, Any]],
    dismissed_jobs: List[Dict[str, Any]],
    applied_jobs: List[Dict[str, Any]],
    limit: int,
) -> ProfileActivityResponse:
    activities: List[Dict[str, Any]] = []

    activities.extend(
        {
            "activity_type": "recommendation_run",
            "created_at": run["created_at"],
            "run_id": run["run_id"],
            "label": "recommendation run",
            "summary": f"Returned {run['returned_jobs']} jobs from {run['jobs_dir']}",
        }
        for run in recommendation_runs
    )
    activities.extend(
        {
            "activity_type": "feedback",
            "created_at": event["created_at"],
            "job_id": event["job_id"],
            "label": event["feedback_label"],
            "summary": f"Marked {event['job_id']} as {event['feedback_label']}",
        }
        for event in feedback_events
    )
    activities.extend(
        {
            "activity_type": state["state"],
            "created_at": state["updated_at"],
            "job_id": state["job_id"],
            "run_id": state.get("source_run_id"),
            "label": state["state"],
            "title": state.get("job_snapshot", {}).get("title") if state.get("job_snapshot") else None,
            "summary": (
                f"{state['state'].capitalize()} {state.get('job_snapshot', {}).get('title', state['job_id'])}"
            ),
        }
        for state in saved_jobs + dismissed_jobs + applied_jobs
    )

    activities.sort(key=lambda item: (item["created_at"], item["activity_type"]), reverse=True)
    return ProfileActivityResponse(
        profile_id=profile_id,
        activities=[ProfileActivityItem(**item) for item in activities[:limit]],
    )


def _build_profile_summary(
    profile_id: str,
    *,
    recommendation_runs: List[Dict[str, Any]],
    feedback_events: List[Dict[str, Any]],
    saved_jobs: List[Dict[str, Any]],
    dismissed_jobs: List[Dict[str, Any]],
    applied_jobs: List[Dict[str, Any]],
) -> ProfileSummaryResponse:
    feedback_label_counts = dict(Counter(event["feedback_label"] for event in feedback_events))
    return ProfileSummaryResponse(
        profile_id=profile_id,
        recommendation_run_count=len(recommendation_runs),
        saved_jobs_count=len(saved_jobs),
        dismissed_jobs_count=len(dismissed_jobs),
        applied_jobs_count=len(applied_jobs),
        feedback_event_count=len(feedback_events),
        feedback_label_counts=feedback_label_counts,
        last_recommendation_at=recommendation_runs[0]["created_at"] if recommendation_runs else None,
        last_feedback_at=feedback_events[-1]["created_at"] if feedback_events else None,
        last_saved_job_at=saved_jobs[0]["updated_at"] if saved_jobs else None,
        last_dismissed_job_at=dismissed_jobs[0]["updated_at"] if dismissed_jobs else None,
        last_applied_job_at=applied_jobs[0]["updated_at"] if applied_jobs else None,
    )


def _build_dashboard_next_actions(
    *,
    recommendation_runs: List[Dict[str, Any]],
    saved_jobs: List[Dict[str, Any]],
    applied_jobs: List[Dict[str, Any]],
) -> List[DashboardNextAction]:
    actions: List[Dict[str, Any]] = []

    if not recommendation_runs:
        actions.append(
            {
                "action": "run_recommendation",
                "label": "Run your first recommendation",
                "description": "Create a recommendation run from the stored profile and current job corpus.",
                "priority": 1,
            }
        )
    else:
        actions.append(
            {
                "action": "refresh_recommendations",
                "label": "Refresh recommendations",
                "description": "Run recommendations again to include the latest corpus and feedback state.",
                "priority": 3,
                "target_run_id": recommendation_runs[0]["run_id"],
            }
        )

    if saved_jobs:
        top_saved_job = saved_jobs[0]
        snapshot = top_saved_job.get("job_snapshot") or {}
        actions.append(
            {
                "action": "apply_saved_job",
                "label": "Apply to a saved job",
                "description": f"Review and apply to {snapshot.get('title', top_saved_job['job_id'])}.",
                "priority": 1,
                "target_job_id": top_saved_job["job_id"],
                "target_run_id": top_saved_job.get("source_run_id"),
            }
        )

    if applied_jobs:
        top_applied_job = applied_jobs[0]
        snapshot = top_applied_job.get("job_snapshot") or {}
        actions.append(
            {
                "action": "review_applied_job",
                "label": "Review applied job",
                "description": f"Track follow-up for {snapshot.get('title', top_applied_job['job_id'])}.",
                "priority": 2,
                "target_job_id": top_applied_job["job_id"],
                "target_run_id": top_applied_job.get("source_run_id"),
            }
        )

    actions.sort(key=lambda item: (item["priority"], item["action"]))
    return [DashboardNextAction(**item) for item in actions[:3]]


def _build_recommend_response(
    *,
    profile: Dict[str, Any],
    profile_source: str,
    jobs_dir: str,
    eligible_only: bool,
    applyable_only: bool,
    include_debug: bool,
    suppress_similar_results: bool,
    top_k: int,
    feedback_profile: Optional[Dict[str, Any]] = None,
    feedback_source: Optional[str] = None,
    excluded_job_ids: Optional[set[str]] = None,
    job_state_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
    run_id: Optional[str] = None,
) -> RecommendResponse:
    jobs_dir_path = resolve_project_path(PROJECT_ROOT, jobs_dir)

    jobs = load_all_job_postings(jobs_dir_path)
    ranked_jobs = rank_jobs(profile, jobs)

    reranking_applied = False
    final_jobs = ranked_jobs
    if feedback_profile is not None:
        final_jobs = apply_feedback_reranking(ranked_jobs, jobs, feedback_profile)
        reranking_applied = True

    visible_jobs = filter_results_for_output(
        final_jobs,
        eligible_only=eligible_only,
        applyable_only=applyable_only,
        suppress_similar=suppress_similar_results,
    )
    if excluded_job_ids:
        visible_jobs = [job for job in visible_jobs if job.get("job_id") not in excluded_job_ids]
    if job_state_by_id:
        visible_jobs = _annotate_results_with_job_state(visible_jobs, job_state_by_id)
    top_results = truncate_results(visible_jobs, top_k)
    enriched_results = [
        _enrich_job_result(job, include_debug=include_debug)
        for job in top_results
    ]
    job_results = [JobResult(**job) for job in enriched_results]

    return RecommendResponse(
        run_id=run_id,
        profile_source=profile_source,
        jobs_dir=jobs_dir,
        feedback_source=feedback_source,
        reranking_applied=reranking_applied,
        total_jobs_scored=len(final_jobs),
        returned_jobs=len(job_results),
        overview=_build_recommend_overview(visible_jobs),
        results=job_results,
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.put("/me/profile", response_model=StoredProfileResponse)
def upsert_account_profile_endpoint(
    profile_data: AccountProfilePayload,
    user_id: str = Depends(current_user_id),
) -> StoredProfileResponse:
    try:
        normalized_profile = _build_account_profile_from_payload(profile_data)
        existing_profile = get_profile(_database_path(), ACCOUNT_PROFILE_ID, user_id=user_id)
        if existing_profile is None:
            stored_profile = create_profile(_database_path(), normalized_profile, user_id=user_id)
        else:
            stored_profile = update_profile(_database_path(), normalized_profile, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return StoredProfileResponse(**_profile_response_payload(stored_profile))


@app.get("/me/profile", response_model=StoredProfileResponse)
def get_account_profile_endpoint(
    user_id: str = Depends(current_user_id),
) -> StoredProfileResponse:
    return get_profile_endpoint(ACCOUNT_PROFILE_ID, user_id=user_id)


@app.post("/me/profile/resume", response_model=ResumeParseResponse)
async def parse_account_resume_endpoint(
    file: UploadFile = File(...),
    user_id: str = Depends(current_user_id),
) -> ResumeParseResponse:
    try:
        content = await file.read()
        parsed = parse_resume_file(file.filename or "resume", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse resume: {e}") from e

    warnings = parsed.pop("warnings", [])
    suggestions = parsed.pop("suggestions", {})
    payload = AccountProfilePayload(**parsed)
    preview = " ".join(payload.resume_text.split())[:360]
    return ResumeParseResponse(
        filename=file.filename or "resume",
        parsed_profile=payload,
        suggestions=suggestions,
        warnings=warnings,
        extracted_text_preview=preview,
    )


@app.get("/me/dashboard", response_model=ProfileDashboardResponse)
def get_account_dashboard_endpoint(
    activity_limit: int = 10,
    run_limit: int = 5,
    saved_job_limit: int = 5,
    dismissed_job_limit: int = 5,
    applied_job_limit: int = 5,
    user_id: str = Depends(current_user_id),
) -> ProfileDashboardResponse:
    return get_profile_dashboard_endpoint(
        ACCOUNT_PROFILE_ID,
        activity_limit=activity_limit,
        run_limit=run_limit,
        saved_job_limit=saved_job_limit,
        dismissed_job_limit=dismissed_job_limit,
        applied_job_limit=applied_job_limit,
        user_id=user_id,
    )


@app.get("/me/saved-jobs", response_model=StoredJobStateListResponse)
def list_account_saved_jobs_endpoint(
    user_id: str = Depends(current_user_id),
) -> StoredJobStateListResponse:
    return list_saved_jobs_endpoint(ACCOUNT_PROFILE_ID, user_id=user_id)


@app.get("/me/dismissed-jobs", response_model=StoredJobStateListResponse)
def list_account_dismissed_jobs_endpoint(
    user_id: str = Depends(current_user_id),
) -> StoredJobStateListResponse:
    return list_dismissed_jobs_endpoint(ACCOUNT_PROFILE_ID, user_id=user_id)


@app.get("/me/applied-jobs", response_model=StoredJobStateListResponse)
def list_account_applied_jobs_endpoint(
    user_id: str = Depends(current_user_id),
) -> StoredJobStateListResponse:
    return list_applied_jobs_endpoint(ACCOUNT_PROFILE_ID, user_id=user_id)


@app.post("/me/jobs/{job_id}/action", response_model=JobActionResponse)
def account_job_action_endpoint(
    job_id: str,
    job_action: JobActionRequest,
    user_id: str = Depends(current_user_id),
) -> JobActionResponse:
    return job_action_endpoint(ACCOUNT_PROFILE_ID, job_id, job_action, user_id=user_id)


@app.get("/me/recommendations/{run_id}", response_model=RecommendResponse, response_model_exclude_none=True)
def get_account_recommendation_run_endpoint(
    run_id: str,
    user_id: str = Depends(current_user_id),
) -> RecommendResponse:
    return get_profile_recommendation_run(ACCOUNT_PROFILE_ID, run_id, user_id=user_id)


@app.post("/me/recommend", response_model=RecommendResponse, response_model_exclude_none=True)
def recommend_for_account_endpoint(
    request: ProfileRecommendRequest,
    user_id: str = Depends(current_user_id),
) -> RecommendResponse:
    return recommend_for_profile(ACCOUNT_PROFILE_ID, request, user_id=user_id)


@app.post("/profiles", response_model=StoredProfileResponse, status_code=201)
def create_profile_endpoint(
    profile_data: CandidateProfilePayload,
    user_id: str = Depends(current_user_id),
) -> StoredProfileResponse:
    try:
        normalized_profile = _build_profile_from_payload(profile_data)
        stored_profile = create_profile(_database_path(), normalized_profile, user_id=user_id)
    except ValueError as e:
        detail = str(e)
        if "already exists" in detail:
            raise HTTPException(status_code=409, detail=detail) from e
        raise HTTPException(status_code=400, detail=detail) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return StoredProfileResponse(**_profile_response_payload(stored_profile))


@app.get("/profiles/{profile_id}", response_model=StoredProfileResponse)
def get_profile_endpoint(
    profile_id: str,
    user_id: str = Depends(current_user_id),
) -> StoredProfileResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    if stored_profile is None:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

    return StoredProfileResponse(**_profile_response_payload(stored_profile))


@app.patch("/profiles/{profile_id}", response_model=StoredProfileResponse)
def update_profile_endpoint(
    profile_id: str,
    profile_update: ProfileUpdatePayload,
    user_id: str = Depends(current_user_id),
) -> StoredProfileResponse:
    try:
        existing_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if existing_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

        merged_profile = _profile_input_payload(existing_profile)
        merged_profile.update(profile_update.model_dump(exclude_none=True))
        merged_profile["profile_id"] = profile_id
        normalized_profile = normalize_candidate_profile(merged_profile)
        stored_profile = update_profile(_database_path(), normalized_profile, user_id=user_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return StoredProfileResponse(**_profile_response_payload(stored_profile))


@app.get("/profiles/{profile_id}/feedback", response_model=StoredFeedbackResponse)
def get_profile_feedback_endpoint(
    profile_id: str,
    user_id: str = Depends(current_user_id),
) -> StoredFeedbackResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
        events = get_feedback_events(_database_path(), profile_id, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return StoredFeedbackResponse(profile_id=profile_id, events=[StoredFeedbackEvent(**event) for event in events])


@app.get("/profiles/{profile_id}/summary", response_model=ProfileSummaryResponse)
def get_profile_summary_endpoint(
    profile_id: str,
    user_id: str = Depends(current_user_id),
) -> ProfileSummaryResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

        feedback_events = get_feedback_events(_database_path(), profile_id, user_id=user_id)
        recommendation_runs = list_recommendation_runs(_database_path(), profile_id, user_id=user_id)
        saved_jobs = list_profile_job_states(_database_path(), profile_id, "saved", user_id=user_id)
        dismissed_jobs = list_profile_job_states(_database_path(), profile_id, "dismissed", user_id=user_id)
        applied_jobs = list_profile_job_states(_database_path(), profile_id, "applied", user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return _build_profile_summary(
        profile_id=profile_id,
        recommendation_runs=recommendation_runs,
        feedback_events=feedback_events,
        saved_jobs=saved_jobs,
        dismissed_jobs=dismissed_jobs,
        applied_jobs=applied_jobs,
    )


@app.get("/profiles/{profile_id}/activity", response_model=ProfileActivityResponse)
def get_profile_activity_endpoint(
    profile_id: str,
    limit: int = 20,
    user_id: str = Depends(current_user_id),
) -> ProfileActivityResponse:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100.")

    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

        feedback_events = get_feedback_events(_database_path(), profile_id, user_id=user_id)
        recommendation_runs = list_recommendation_runs(_database_path(), profile_id, user_id=user_id)
        saved_jobs = list_profile_job_states(_database_path(), profile_id, "saved", user_id=user_id)
        dismissed_jobs = list_profile_job_states(_database_path(), profile_id, "dismissed", user_id=user_id)
        applied_jobs = list_profile_job_states(_database_path(), profile_id, "applied", user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return _build_profile_activity(
        profile_id,
        recommendation_runs=recommendation_runs,
        feedback_events=feedback_events,
        saved_jobs=saved_jobs,
        dismissed_jobs=dismissed_jobs,
        applied_jobs=applied_jobs,
        limit=limit,
    )


@app.get("/profiles/{profile_id}/dashboard", response_model=ProfileDashboardResponse)
def get_profile_dashboard_endpoint(
    profile_id: str,
    activity_limit: int = 10,
    run_limit: int = 5,
    saved_job_limit: int = 5,
    dismissed_job_limit: int = 5,
    applied_job_limit: int = 5,
    user_id: str = Depends(current_user_id),
) -> ProfileDashboardResponse:
    if activity_limit < 1 or activity_limit > 100:
        raise HTTPException(status_code=400, detail="activity_limit must be between 1 and 100.")
    if run_limit < 1 or run_limit > 50:
        raise HTTPException(status_code=400, detail="run_limit must be between 1 and 50.")
    if saved_job_limit < 1 or saved_job_limit > 50:
        raise HTTPException(status_code=400, detail="saved_job_limit must be between 1 and 50.")
    if dismissed_job_limit < 1 or dismissed_job_limit > 50:
        raise HTTPException(status_code=400, detail="dismissed_job_limit must be between 1 and 50.")
    if applied_job_limit < 1 or applied_job_limit > 50:
        raise HTTPException(status_code=400, detail="applied_job_limit must be between 1 and 50.")

    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

        feedback_events = get_feedback_events(_database_path(), profile_id, user_id=user_id)
        recommendation_runs = list_recommendation_runs(_database_path(), profile_id, user_id=user_id)
        saved_jobs = list_profile_job_states(_database_path(), profile_id, "saved", user_id=user_id)
        dismissed_jobs = list_profile_job_states(_database_path(), profile_id, "dismissed", user_id=user_id)
        applied_jobs = list_profile_job_states(_database_path(), profile_id, "applied", user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return ProfileDashboardResponse(
        profile_id=profile_id,
        summary=_build_profile_summary(
            profile_id=profile_id,
            recommendation_runs=recommendation_runs,
            feedback_events=feedback_events,
            saved_jobs=saved_jobs,
            dismissed_jobs=dismissed_jobs,
            applied_jobs=applied_jobs,
        ),
        recommended_next_actions=_build_dashboard_next_actions(
            recommendation_runs=recommendation_runs,
            saved_jobs=saved_jobs,
            applied_jobs=applied_jobs,
        ),
        activity=_build_profile_activity(
            profile_id,
            recommendation_runs=recommendation_runs,
            feedback_events=feedback_events,
            saved_jobs=saved_jobs,
            dismissed_jobs=dismissed_jobs,
            applied_jobs=applied_jobs,
            limit=activity_limit,
        ),
        recent_runs=[RecommendationRunSummary(**run) for run in recommendation_runs[:run_limit]],
        saved_jobs=[_stored_job_state_response(job_state) for job_state in saved_jobs[:saved_job_limit]],
        dismissed_jobs=[_stored_job_state_response(job_state) for job_state in dismissed_jobs[:dismissed_job_limit]],
        applied_jobs=[_stored_job_state_response(job_state) for job_state in applied_jobs[:applied_job_limit]],
    )


@app.post("/profiles/{profile_id}/feedback", response_model=StoredFeedbackResponse, status_code=201)
def add_profile_feedback_endpoint(
    profile_id: str,
    feedback_data: FeedbackProfilePayload,
    user_id: str = Depends(current_user_id),
) -> StoredFeedbackResponse:
    if feedback_data.profile_id != profile_id:
        raise HTTPException(status_code=400, detail="Feedback payload profile_id must match the URL profile_id.")

    try:
        normalized_feedback = _build_feedback_from_payload(feedback_data)
        events = add_feedback_events(_database_path(), profile_id, normalized_feedback["events"], user_id=user_id)
    except ValueError as e:
        detail = str(e)
        if "Profile not found" in detail:
            raise HTTPException(status_code=404, detail=detail) from e
        raise HTTPException(status_code=400, detail=detail) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return StoredFeedbackResponse(profile_id=profile_id, events=[StoredFeedbackEvent(**event) for event in events])


@app.get("/profiles/{profile_id}/saved-jobs", response_model=StoredJobStateListResponse)
def list_saved_jobs_endpoint(
    profile_id: str,
    user_id: str = Depends(current_user_id),
) -> StoredJobStateListResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
        job_states = list_profile_job_states(_database_path(), profile_id, "saved", user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return StoredJobStateListResponse(
        profile_id=profile_id,
        state="saved",
        jobs=[_stored_job_state_response(job_state) for job_state in job_states],
    )


@app.get("/profiles/{profile_id}/dismissed-jobs", response_model=StoredJobStateListResponse)
def list_dismissed_jobs_endpoint(
    profile_id: str,
    user_id: str = Depends(current_user_id),
) -> StoredJobStateListResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
        job_states = list_profile_job_states(_database_path(), profile_id, "dismissed", user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return StoredJobStateListResponse(
        profile_id=profile_id,
        state="dismissed",
        jobs=[_stored_job_state_response(job_state) for job_state in job_states],
    )


@app.get("/profiles/{profile_id}/applied-jobs", response_model=StoredJobStateListResponse)
def list_applied_jobs_endpoint(
    profile_id: str,
    user_id: str = Depends(current_user_id),
) -> StoredJobStateListResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
        job_states = list_profile_job_states(_database_path(), profile_id, "applied", user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return StoredJobStateListResponse(
        profile_id=profile_id,
        state="applied",
        jobs=[_stored_job_state_response(job_state) for job_state in job_states],
    )


@app.post("/profiles/{profile_id}/jobs/{job_id}/action", response_model=JobActionResponse)
def job_action_endpoint(
    profile_id: str,
    job_id: str,
    job_action: JobActionRequest,
    user_id: str = Depends(current_user_id),
) -> JobActionResponse:
    try:
        return _apply_job_action(profile_id, job_id, job_action.action, job_action.run_id, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e


@app.post("/profiles/{profile_id}/jobs/{job_id}/save", response_model=StoredJobState, status_code=201)
def save_job_endpoint(
    profile_id: str,
    job_id: str,
    job_state: JobStateRequest,
    user_id: str = Depends(current_user_id),
) -> StoredJobState:
    try:
        response = _apply_job_action(profile_id, job_id, "save", job_state.run_id, user_id=user_id)
        if response.job_state is None:
            raise HTTPException(status_code=500, detail="Saved job state was not returned.")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return response.job_state


@app.post("/profiles/{profile_id}/jobs/{job_id}/dismiss", response_model=StoredJobState, status_code=201)
def dismiss_job_endpoint(
    profile_id: str,
    job_id: str,
    job_state: JobStateRequest,
    user_id: str = Depends(current_user_id),
) -> StoredJobState:
    try:
        response = _apply_job_action(profile_id, job_id, "dismiss", job_state.run_id, user_id=user_id)
        if response.job_state is None:
            raise HTTPException(status_code=500, detail="Dismissed job state was not returned.")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return response.job_state


@app.delete("/profiles/{profile_id}/jobs/{job_id}/save", response_model=StoredJobState)
def unsave_job_endpoint(
    profile_id: str,
    job_id: str,
    user_id: str = Depends(current_user_id),
) -> StoredJobState:
    try:
        existing_state = get_profile_job_state(_database_path(), profile_id, job_id, user_id=user_id)
        if existing_state is None or existing_state["state"] != "saved":
            raise HTTPException(status_code=404, detail=f"Saved job not found: {job_id}")
        _apply_job_action(profile_id, job_id, "clear", None, user_id=user_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return _stored_job_state_response(existing_state)


@app.delete("/profiles/{profile_id}/jobs/{job_id}/dismiss", response_model=StoredJobState)
def undismiss_job_endpoint(
    profile_id: str,
    job_id: str,
    user_id: str = Depends(current_user_id),
) -> StoredJobState:
    try:
        existing_state = get_profile_job_state(_database_path(), profile_id, job_id, user_id=user_id)
        if existing_state is None or existing_state["state"] != "dismissed":
            raise HTTPException(status_code=404, detail=f"Dismissed job not found: {job_id}")
        _apply_job_action(profile_id, job_id, "clear", None, user_id=user_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return _stored_job_state_response(existing_state)


@app.get("/profiles/{profile_id}/recommendations", response_model=RecommendationRunListResponse)
def list_profile_recommendations(
    profile_id: str,
    user_id: str = Depends(current_user_id),
) -> RecommendationRunListResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
        runs = list_recommendation_runs(_database_path(), profile_id, user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    return RecommendationRunListResponse(
        profile_id=profile_id,
        runs=[RecommendationRunSummary(**run) for run in runs],
    )


@app.get("/profiles/{profile_id}/recommendations/{run_id}", response_model=RecommendResponse, response_model_exclude_none=True)
def get_profile_recommendation_run(
    profile_id: str,
    run_id: str,
    user_id: str = Depends(current_user_id),
) -> RecommendResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
        run = get_recommendation_run(_database_path(), profile_id, run_id, user_id=user_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Recommendation run not found: {run_id}")
        saved_jobs = list_profile_job_states(_database_path(), profile_id, "saved", user_id=user_id)
        dismissed_jobs = list_profile_job_states(_database_path(), profile_id, "dismissed", user_id=user_id)
        applied_jobs = list_profile_job_states(_database_path(), profile_id, "applied", user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    job_state_by_id = {
        job_state["job_id"]: job_state
        for job_state in saved_jobs + dismissed_jobs + applied_jobs
    }

    return RecommendResponse(
        run_id=run["run_id"],
        profile_source=f"stored_profile:{profile_id}",
        jobs_dir=run["jobs_dir"],
        feedback_source=run["feedback_source"],
        reranking_applied=run["reranking_applied"],
        total_jobs_scored=run["total_jobs_scored"],
        returned_jobs=run["returned_jobs"],
        overview=_build_recommend_overview(run["results"]),
        results=[
            JobResult(**result)
            for result in _annotate_results_with_job_state(run["results"], job_state_by_id)
        ],
    )


@app.post("/recommend", response_model=RecommendResponse, response_model_exclude_none=True)
def recommend(request: RecommendRequest) -> RecommendResponse:
    try:
        if request.profile_data is not None:
            profile = _build_profile_from_payload(request.profile_data)
            profile_source = "inline_profile_payload"
        else:
            profile_path = resolve_project_path(PROJECT_ROOT, str(request.profile_path))
            profile = load_candidate_profile(profile_path)
            profile_source = str(request.profile_path)

        feedback_profile: Optional[Dict[str, Any]] = None
        feedback_source: Optional[str] = None
        if request.feedback_data is not None:
            feedback_profile = _build_feedback_from_payload(request.feedback_data)
            feedback_source = "inline_feedback_payload"
        elif request.feedback_path is not None:
            feedback_path = resolve_project_path(PROJECT_ROOT, request.feedback_path)
            feedback_profile = load_feedback_profile(feedback_path)
            feedback_source = str(request.feedback_path)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e

    try:
        return _build_recommend_response(
            profile=profile,
            profile_source=profile_source,
            jobs_dir=request.jobs_dir,
            eligible_only=request.eligible_only,
            applyable_only=request.applyable_only,
            include_debug=request.include_debug,
            suppress_similar_results=request.suppress_similar_results,
            top_k=request.top_k,
            feedback_profile=feedback_profile,
            feedback_source=feedback_source,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e


@app.post("/profiles/{profile_id}/recommend", response_model=RecommendResponse, response_model_exclude_none=True)
def recommend_for_profile(
    profile_id: str,
    request: ProfileRecommendRequest,
    user_id: str = Depends(current_user_id),
) -> RecommendResponse:
    try:
        stored_profile = get_profile(_database_path(), profile_id, user_id=user_id)
        if stored_profile is None:
            raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

        normalized_profile = normalize_candidate_profile(_profile_input_payload(stored_profile))
        excluded_job_ids: set[str] = set()
        job_state_by_id: Dict[str, Dict[str, Any]] = {}

        feedback_profile: Optional[Dict[str, Any]] = None
        feedback_source: Optional[str] = None
        if request.include_feedback:
            stored_events = get_feedback_events(_database_path(), profile_id, user_id=user_id)
            if stored_events:
                feedback_profile = _build_feedback_profile_from_events(profile_id, stored_events)
                feedback_source = "stored_feedback_events"

        saved_jobs = list_profile_job_states(_database_path(), profile_id, "saved", user_id=user_id)
        dismissed_jobs = list_profile_job_states(_database_path(), profile_id, "dismissed", user_id=user_id)
        applied_jobs = list_profile_job_states(_database_path(), profile_id, "applied", user_id=user_id)
        job_state_by_id = {
            job_state["job_id"]: job_state
            for job_state in saved_jobs + dismissed_jobs + applied_jobs
        }

        if request.exclude_dismissed:
            excluded_job_ids = {job_state["job_id"] for job_state in dismissed_jobs}
        if request.exclude_applied:
            excluded_job_ids.update(job_state["job_id"] for job_state in applied_jobs)

        response = _build_recommend_response(
            profile=normalized_profile,
            profile_source=f"stored_profile:{profile_id}",
            jobs_dir=request.jobs_dir,
            eligible_only=request.eligible_only,
            applyable_only=request.applyable_only,
            include_debug=request.include_debug,
            suppress_similar_results=request.suppress_similar_results,
            top_k=request.top_k,
            feedback_profile=feedback_profile,
            feedback_source=feedback_source,
            excluded_job_ids=excluded_job_ids,
            job_state_by_id=job_state_by_id,
        )

        if request.save_run:
            persisted_run = create_recommendation_run(
                _database_path(),
                profile_id=profile_id,
                user_id=user_id,
                jobs_dir=request.jobs_dir,
                top_k=request.top_k,
                eligible_only=request.eligible_only,
                applyable_only=request.applyable_only,
                suppress_similar_results=request.suppress_similar_results,
                include_feedback=request.include_feedback,
                include_debug=request.include_debug,
                reranking_applied=response.reranking_applied,
                feedback_source=response.feedback_source,
                total_jobs_scored=response.total_jobs_scored,
                returned_jobs=response.returned_jobs,
                results=[result.model_dump(exclude_none=True) for result in response.results],
            )
            response.run_id = persisted_run["run_id"]

        return response
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {e}") from e


@app.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, jobs_dir: str = DEFAULT_API_JOBS_DIR) -> JobDetailResponse:
    # Read one job from the processed jobs directory tree.
    jobs_dir_path = resolve_project_path(PROJECT_ROOT, jobs_dir)

    try:
        jobs = load_all_job_postings(
            jobs_dir_path,
            suppress_duplicate_content=False,
            include_expired=True,
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
        fetched_at=job.get("fetched_at"),
        expires_at=job.get("expires_at"),
        freshness_days=job.get("freshness_days"),
        short_description=_short_description(job.get("description", "")),
        internship_signals=_internship_signals(job),
        possible_requirements=_extract_requirement_items(job),
        possible_blockers=_possible_posting_blockers(job),
        application_link=_application_link(job),
    )
