from src.preprocessing.job_parser import load_all_job_postings
from src.ranking.baseline_scorer import rank_jobs
from src.ranking.feedback_reranker import (
    apply_feedback_reranking,
    build_feedback_lookup,
    load_feedback_profile,
    normalize_feedback_profile,
)

JOBS_DIR = "data/sample_jobs"
FEEDBACK_PATH = "data/feedback/sample_feedback.json"


def test_load_feedback_profile_reads_valid_events() -> None:
    # The loader should preserve valid feedback events and normalize labels.
    feedback = load_feedback_profile(FEEDBACK_PATH)

    assert feedback["profile_id"] == "seho_001"
    assert len(feedback["events"]) == 3
    assert feedback["events"][0]["feedback_label"] == "applied"


def test_normalize_feedback_profile_normalizes_inline_payload() -> None:
    # Inline feedback payloads should be normalized the same way as file-based input.
    raw_feedback = {
        "profile_id": " seho_001 ",
        "events": [
            {
                "job_id": " job_002 ",
                "feedback_label": " Applied ",
            },
            {
                "job_id": "job_005",
                "feedback_label": " SAVED ",
            },
        ],
    }

    normalized = normalize_feedback_profile(raw_feedback)

    assert normalized["profile_id"] == "seho_001"
    assert normalized["events"][0]["job_id"] == "job_002"
    assert normalized["events"][0]["feedback_label"] == "applied"
    assert normalized["events"][1]["feedback_label"] == "saved"


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
    assert "feedback_explanations" in reranked[0]
    assert isinstance(reranked[0]["feedback_explanations"], list)


def test_apply_feedback_reranking_includes_explanation_keys() -> None:
    # Explanation rows should expose the source feedback and overlap details.
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

    jobs_with_explanations = [
        job for job in reranked if job.get("feedback_explanations")
    ]
    assert len(jobs_with_explanations) > 0

    explanation = jobs_with_explanations[0]["feedback_explanations"][0]
    assert "source_job_id" in explanation
    assert "source_job_title" in explanation
    assert "feedback_label" in explanation
    assert "similarity" in explanation
    assert "adjustment" in explanation
    assert "shared_title_tokens" in explanation
    assert "shared_skill_tokens" in explanation