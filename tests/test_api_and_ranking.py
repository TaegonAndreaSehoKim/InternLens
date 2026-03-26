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
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommend_endpoint_with_inline_profile_returns_ranked_results() -> None:
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

    assert response.status_code == 200
    assert body["profile_source"] == "inline_profile_payload"
    assert body["total_jobs_scored"] == 5
    assert body["returned_jobs"] == 5
    assert len(body["results"]) == 5
    assert body["results"][0]["title"] == "applied scientist intern"


def test_example_ai_job_has_sponsorship_blocker() -> None:
    profile = load_candidate_profile(PROFILE_PATH)
    jobs = load_all_job_postings(JOBS_DIR)

    example_ai_job = next(job for job in jobs if job["job_id"] == "job_001")
    result = score_job(profile, example_ai_job)

    assert result["action_label"] == "Skip"
    assert "Sponsorship is not available for this role" in result["blocking_issues"]


def test_backend_job_ranks_below_applied_scientist_job() -> None:
    profile = load_candidate_profile(PROFILE_PATH)
    jobs = load_all_job_postings(JOBS_DIR)
    ranked_jobs = rank_jobs(profile, jobs)

    titles_in_order = [job["title"] for job in ranked_jobs]

    assert titles_in_order.index("applied scientist intern") < titles_in_order.index(
        "backend software engineer intern"
    )


def test_backend_job_has_lower_score_than_applied_scientist_job() -> None:
    profile = load_candidate_profile(PROFILE_PATH)
    jobs = load_all_job_postings(JOBS_DIR)

    results_by_job_id = {job["job_id"]: score_job(profile, job) for job in jobs}

    assert results_by_job_id["job_002"]["score"] > results_by_job_id["job_004"]["score"]

def test_non_internship_job_triggers_blocker() -> None:
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