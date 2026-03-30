from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import app
from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import load_candidate_profile
from src.ranking.baseline_scorer import rank_jobs, score_job


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "data" / "processed" / "candidate_profile_example.json"
JOBS_DIR = PROJECT_ROOT / "data" / "sample_jobs"


client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    # Basic smoke test for API liveness.
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommend_endpoint_with_inline_profile_returns_ranked_results() -> None:
    # Inline payloads should be normalized and scored the same way as file-based profiles.
    payload = {
        "profile_data": {
            "profile_id": "seho_001",
            "resume_text": "Graduate student with Python, PyTorch, machine learning, and data analysis experience.",
            "degree_level": "Master's",
            "grad_date": "2027-12",
            "preferred_roles": [
                "Machine Learning Engineer Intern",
                "Applied Scientist Intern",
            ],
            "preferred_locations": ["California", "Remote"],
            "target_industries": ["AI", "Tech"],
            "sponsorship_need": True,
            "extracted_skills": [
                "Python",
                "PyTorch",
                "Machine Learning",
                "Data Analysis",
            ],
            "years_of_experience": 1,
            "notes": "Interested in recommendation and ranking systems",
        },
        "jobs_dir": "data/sample_jobs",
        "top_k": 5,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()
    jobs = load_all_job_postings(JOBS_DIR)

    assert response.status_code == 200
    assert body["profile_source"] == "inline_profile_payload"
    assert body["total_jobs_scored"] == len(jobs)
    assert body["returned_jobs"] == 5
    assert len(body["results"]) == 5
    assert body["results"][0]["title"] == "applied scientist intern"


def test_example_ai_job_has_sponsorship_blocker() -> None:
    # A strong fit should still be skipped when a hard blocker exists.
    profile = load_candidate_profile(PROFILE_PATH)
    jobs = load_all_job_postings(JOBS_DIR)

    example_ai_job = next(job for job in jobs if job["job_id"] == "job_001")
    result = score_job(profile, example_ai_job)

    assert result["action_label"] == "Skip"
    assert "Sponsorship is not available for this role" in result["blocking_issues"]


def test_backend_job_ranks_below_applied_scientist_job() -> None:
    # Better-fitting roles should rank above weaker baseline matches.
    profile = load_candidate_profile(PROFILE_PATH)
    jobs = load_all_job_postings(JOBS_DIR)
    ranked_jobs = rank_jobs(profile, jobs)

    titles_in_order = [job["title"] for job in ranked_jobs]

    assert titles_in_order.index("applied scientist intern") < titles_in_order.index(
        "backend software engineer intern"
    )


def test_backend_job_has_lower_score_than_applied_scientist_job() -> None:
    # Check raw score ordering without involving final ranked list behavior.
    profile = load_candidate_profile(PROFILE_PATH)
    jobs = load_all_job_postings(JOBS_DIR)

    results_by_job_id = {job["job_id"]: score_job(profile, job) for job in jobs}

    assert results_by_job_id["job_002"]["score"] > results_by_job_id["job_004"]["score"]


def test_non_internship_job_triggers_blocker() -> None:
    # Non-intern postings should be filtered out by blocker logic.
    profile = load_candidate_profile(PROFILE_PATH)

    fake_job = {
        "job_id": "job_x",
        "company": "example",
        "title": "machine learning engineer",
        "location": "remote",
        "description": "Full-time machine learning engineer role.",
        "min_qualifications": "Python, machine learning",
        "preferred_qualifications": "PyTorch",
        "posting_date": "2026-03-27",
        "sponsorship_info": "Sponsorship available",
        "employment_type": "Full-time",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, fake_job)

    assert "This role does not appear to be an internship" in result["blocking_issues"]


def test_full_time_phd_job_triggers_multiple_blockers() -> None:
    # Some postings should trigger multiple blocker checks at once.
    profile = load_candidate_profile(PROFILE_PATH)
    jobs = load_all_job_postings(JOBS_DIR)

    phd_full_time_job = next(job for job in jobs if job["job_id"] == "job_006")
    result = score_job(profile, phd_full_time_job)

    assert "This role does not appear to be an internship" in result["blocking_issues"]
    assert "This role appears to require a PhD" in result["blocking_issues"]
    assert result["action_label"] == "Skip"


def test_rank_jobs_prioritizes_action_labels_before_raw_score() -> None:
    # A blocked high-fit job should not outrank an open apply target.
    profile = {
        "degree_level": "Master's",
        "grad_date": "2027-12",
        "preferred_roles": ["Machine Learning Engineer Intern", "Applied Scientist Intern"],
        "preferred_locations": ["California", "Remote"],
        "sponsorship_need": True,
        "skill_set": {"python", "pytorch", "machine learning", "data analysis"},
    }

    jobs = [
        {
            "job_id": "high_fit_blocked",
            "company": "research frontier",
            "title": "machine learning research engineer",
            "location": "new york, ny",
            "description": "We are hiring a full-time machine learning research engineer to work on advanced modeling systems.",
            "min_qualifications": "PhD in computer science, machine learning, Python",
            "preferred_qualifications": "PyTorch, deep learning, statistics",
            "posting_date": "2026-03-27",
            "sponsorship_info": "Sponsorship available",
            "employment_type": "Full-time",
            "source": "manual",
            "remote_status": "onsite",
        },
        {
            "job_id": "medium_fit_open",
            "company": "insight labs",
            "title": "machine learning engineer intern",
            "location": "irvine, ca",
            "description": "Internship role for ML product modeling.",
            "min_qualifications": "Python, PyTorch, machine learning",
            "preferred_qualifications": "SQL, data analysis",
            "posting_date": "2026-03-27",
            "sponsorship_info": "Sponsorship available",
            "employment_type": "Internship",
            "source": "manual",
            "remote_status": "onsite",
        },
    ]

    ranked = rank_jobs(profile, jobs)

    assert ranked[0]["job_id"] == "medium_fit_open"
    assert ranked[0]["action_label"] in {"Apply Now", "Apply Later"}
    assert ranked[1]["job_id"] == "high_fit_blocked"
    assert ranked[1]["action_label"] == "Skip"


def test_recommend_endpoint_with_profile_path_returns_ranked_results() -> None:
    # File-based profile input should remain supported for script/API parity.
    payload = {
        "profile_path": "data/processed/candidate_profile_example.json",
        "jobs_dir": "data/sample_jobs",
        "top_k": 3,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()
    jobs = load_all_job_postings(JOBS_DIR)

    assert response.status_code == 200
    assert body["profile_source"] == "data/processed/candidate_profile_example.json"
    assert body["total_jobs_scored"] == len(jobs)
    assert body["returned_jobs"] == 3
    assert len(body["results"]) == 3
    assert body["results"][0]["action_label"] == "Apply Now"


def test_recommend_endpoint_requires_profile_source() -> None:
    # The API contract requires either a file path or an inline profile payload.
    payload = {
        "jobs_dir": "data/sample_jobs",
        "top_k": 5,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()

    assert response.status_code == 422
    assert "Either profile_path or profile_data must be provided." in str(body)


def test_recommend_endpoint_with_feedback_path_applies_reranking() -> None:
    payload = {
        "profile_path": "data/processed/candidate_profile_example.json",
        "jobs_dir": "data/sample_jobs",
        "feedback_path": "data/feedback/sample_feedback.json",
        "top_k": 5,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["profile_source"] == "data/processed/candidate_profile_example.json"
    assert body["feedback_source"] == "data/feedback/sample_feedback.json"
    assert body["reranking_applied"] is True
    assert body["returned_jobs"] == 5
    assert "feedback_adjustment" in body["results"][0]
    assert "reranked_score" in body["results"][0]
    assert "feedback_explanations" in body["results"][0]
    assert isinstance(body["results"][0]["feedback_explanations"], list)


def test_recommend_endpoint_feedback_response_includes_explanation_items() -> None:
    payload = {
        "profile_path": "data/processed/candidate_profile_example.json",
        "jobs_dir": "data/sample_jobs",
        "feedback_path": "data/feedback/sample_feedback.json",
        "top_k": 6,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200

    jobs_with_explanations = [
        job for job in body["results"] if job["feedback_explanations"]
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


def test_recommend_endpoint_with_inline_feedback_applies_reranking() -> None:
    payload = {
        "profile_path": "data/processed/candidate_profile_example.json",
        "jobs_dir": "data/sample_jobs",
        "feedback_data": {
            "profile_id": "seho_001",
            "events": [
                {"job_id": "job_002", "feedback_label": "applied"},
                {"job_id": "job_005", "feedback_label": "saved"},
                {"job_id": "job_004", "feedback_label": "skipped"},
            ],
        },
        "top_k": 5,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["feedback_source"] == "inline_feedback_payload"
    assert body["reranking_applied"] is True
    assert body["returned_jobs"] == 5
    assert "feedback_adjustment" in body["results"][0]
    assert "reranked_score" in body["results"][0]
    assert "feedback_explanations" in body["results"][0]


def test_recommend_endpoint_inline_feedback_response_includes_explanation_items() -> None:
    payload = {
        "profile_path": "data/processed/candidate_profile_example.json",
        "jobs_dir": "data/sample_jobs",
        "feedback_data": {
            "profile_id": "seho_001",
            "events": [
                {"job_id": "job_002", "feedback_label": "applied"},
                {"job_id": "job_005", "feedback_label": "saved"},
                {"job_id": "job_004", "feedback_label": "skipped"},
            ],
        },
        "top_k": 6,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200

    jobs_with_explanations = [
        job for job in body["results"] if job["feedback_explanations"]
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


def test_recommend_endpoint_prefers_inline_feedback_over_feedback_path() -> None:
    payload = {
        "profile_path": "data/processed/candidate_profile_example.json",
        "jobs_dir": "data/sample_jobs",
        "feedback_path": "data/feedback/does_not_exist.json",
        "feedback_data": {
            "profile_id": "seho_001",
            "events": [
                {"job_id": "job_002", "feedback_label": "applied"},
                {"job_id": "job_005", "feedback_label": "saved"},
            ],
        },
        "top_k": 5,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["feedback_source"] == "inline_feedback_payload"
    assert body["reranking_applied"] is True


def test_recommend_endpoint_with_missing_feedback_file_returns_404() -> None:
    payload = {
        "profile_path": "data/processed/candidate_profile_example.json",
        "jobs_dir": "data/sample_jobs",
        "feedback_path": "data/feedback/does_not_exist.json",
        "top_k": 5,
    }

    response = client.post("/recommend", json=payload)
    body = response.json()

    assert response.status_code == 404
    assert "Feedback file not found" in body["detail"]