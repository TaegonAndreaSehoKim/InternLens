from src.preprocessing.job_parser import load_all_job_postings
from src.ranking.baseline_scorer import rank_jobs
from src.ranking.feedback_reranker import (
    apply_feedback_reranking,
    build_feedback_lookup,
    load_feedback_profile,
)

JOBS_DIR = "data/sample_jobs"
FEEDBACK_PATH = "data/feedback/sample_feedback.json"


def test_load_feedback_profile_reads_valid_events() -> None:
    # The loader should preserve valid feedback events and normalize labels.
    feedback = load_feedback_profile(FEEDBACK_PATH)

    assert feedback["profile_id"] == "seho_001"
    assert len(feedback["events"]) == 3
    assert feedback["events"][0]["feedback_label"] == "applied"


def test_build_feedback_lookup_includes_known_jobs_only() -> None:
    # Only jobs present in the current corpus should be used for reranking.
    jobs = load_all_job_postings(JOBS_DIR)
    feedback = load_feedback_profile(FEEDBACK_PATH)

    lookup = build_feedback_lookup(jobs, feedback)

    assert "job_002" in lookup
    assert "job_005" in lookup
    assert "job_004" in lookup


def test_apply_feedback_reranking_adds_adjustment_fields() -> None:
    # Reranking should add feedback-specific fields without dropping any jobs.
    jobs = load_all_job_postings(JOBS_DIR)
    profile = {
        "degree_level": "master's",
        "grad_date": "2027-12",
        "preferred_roles": ["machine learning engineer intern", "applied scientist intern"],
        "preferred_locations": ["california", "remote"],
        "target_industries": ["ai", "tech"],
        "sponsorship_need": True,
        "extracted_skills": ["python", "pytorch", "machine learning", "data analysis"],
        "skill_set": {"python", "pytorch", "machine learning", "data analysis"},
    }
    ranked_jobs = rank_jobs(profile, jobs)
    feedback = load_feedback_profile(FEEDBACK_PATH)

    reranked = apply_feedback_reranking(ranked_jobs, jobs, feedback)

    assert len(reranked) == len(ranked_jobs)
    assert "feedback_adjustment" in reranked[0]
    assert "reranked_score" in reranked[0]
