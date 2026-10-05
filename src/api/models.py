from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from src.api.settings import DEFAULT_JOBS_DIR, env_value

DEFAULT_API_JOBS_DIR = env_value("INTERNLENS_JOBS_DIR", DEFAULT_JOBS_DIR)


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


class CorpusReadinessResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    checked_at: str
    active_job_count: int
    all_job_count: int
    expired_or_filtered_job_count: int
    latest_fetched_at: Optional[str]
    latest_expires_at: Optional[str]
    message: str


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
    department: Optional[str] = None
    fetched_at: Optional[str] = None
    expires_at: Optional[str] = None
    freshness_days: Optional[int] = None
    short_description: str
    internship_signals: List[str]
    possible_requirements: List[str]
    possible_blockers: List[str]
    application_link: Optional[str] = None
