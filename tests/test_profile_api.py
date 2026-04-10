from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import src.api.app as api_app


client = TestClient(api_app.app)


def _profile_payload() -> dict:
    return {
        "profile_id": "user_001",
        "resume_text": "Python, machine learning, ranking systems",
        "degree_level": "Master's",
        "grad_date": "2027-12",
        "preferred_roles": ["Machine Learning Engineer Intern"],
        "preferred_locations": ["Remote", "California"],
        "target_industries": ["AI", "Tech"],
        "sponsorship_need": True,
        "extracted_skills": ["Python", "Machine Learning"],
        "years_of_experience": 1,
        "notes": "Interested in recommender systems",
    }


def test_profile_create_get_and_update_flow(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    create_response = client.post("/profiles", json=_profile_payload())
    create_body = create_response.json()

    assert create_response.status_code == 201
    assert create_body["profile_id"] == "user_001"
    assert create_body["degree_level"] == "master's"
    assert "created_at" in create_body
    assert "updated_at" in create_body

    get_response = client.get("/profiles/user_001")
    get_body = get_response.json()

    assert get_response.status_code == 200
    assert get_body["profile_id"] == "user_001"
    assert get_body["preferred_roles"] == ["machine learning engineer intern"]

    update_response = client.patch(
        "/profiles/user_001",
        json={
            "preferred_locations": ["Remote"],
            "notes": "Updated profile note",
        },
    )
    update_body = update_response.json()

    assert update_response.status_code == 200
    assert update_body["preferred_locations"] == ["remote"]
    assert update_body["notes"] == "Updated profile note"


def test_profile_feedback_endpoints_store_and_return_events(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())

    feedback_response = client.post(
        "/profiles/user_001/feedback",
        json={
            "profile_id": "user_001",
            "events": [
                {"job_id": "job_123", "feedback_label": "applied"},
                {"job_id": "job_456", "feedback_label": "saved"},
            ],
        },
    )
    feedback_body = feedback_response.json()

    assert feedback_response.status_code == 201
    assert feedback_body["profile_id"] == "user_001"
    assert len(feedback_body["events"]) == 2
    assert feedback_body["events"][0]["feedback_label"] == "applied"
    assert "created_at" in feedback_body["events"][0]

    get_feedback_response = client.get("/profiles/user_001/feedback")
    get_feedback_body = get_feedback_response.json()

    assert get_feedback_response.status_code == 200
    assert len(get_feedback_body["events"]) == 2
    assert get_feedback_body["events"][1]["job_id"] == "job_456"


def test_profile_recommend_uses_stored_profile_and_feedback(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    client.post(
        "/profiles/user_001/feedback",
        json={
            "profile_id": "user_001",
            "events": [{"job_id": "job_seed", "feedback_label": "applied"}],
        },
    )

    def fake_load_all_job_postings(path: Path):
        assert path == api_app.PROJECT_ROOT / "data" / "processed" / "jobs"
        return [
            {
                "job_id": "job_a",
                "company": "example",
                "title": "machine learning engineer intern",
                "location": "remote",
                "description": "internship role",
                "min_qualifications": "python",
                "preferred_qualifications": "pytorch",
                "posting_date": "2026-04-10",
                "sponsorship_info": "",
                "employment_type": "Internship",
                "source": "manual",
                "source_url": "https://example.com/jobs/job_a",
            }
        ]

    ranked_job = {
        "job_id": "job_a",
        "company": "example",
        "title": "machine learning engineer intern",
        "location": "remote",
        "score": 88.0,
        "action_label": "Apply Now",
        "matched_skills": ["python"],
        "skill_gaps": [],
        "reasons": ["Strong skill overlap"],
        "blocking_issues": [],
        "component_scores": {
            "skill_score": 50.0,
            "role_score": 20.0,
            "location_score": 10.0,
            "internship_bonus": 8.0,
        },
        "source_url": "https://example.com/jobs/job_a",
        "application_url": "https://example.com/jobs/job_a/apply",
    }

    monkeypatch.setattr(api_app, "load_all_job_postings", fake_load_all_job_postings)
    monkeypatch.setattr(api_app, "rank_jobs", lambda profile, jobs: [ranked_job])

    def fake_apply_feedback_reranking(ranked_jobs, jobs, feedback_profile):
        assert feedback_profile["profile_id"] == "user_001"
        assert feedback_profile["events"][0]["feedback_label"] == "applied"
        reranked = dict(ranked_jobs[0])
        reranked["feedback_adjustment"] = 5.0
        reranked["reranked_score"] = 93.0
        reranked["feedback_explanations"] = []
        return [reranked]

    monkeypatch.setattr(api_app, "apply_feedback_reranking", fake_apply_feedback_reranking)

    response = client.post(
        "/profiles/user_001/recommend",
        json={"include_debug": True, "top_k": 1},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["profile_source"] == "stored_profile:user_001"
    assert body["feedback_source"] == "stored_feedback_events"
    assert body["reranking_applied"] is True
    assert body["jobs_dir"] == "data/processed/jobs"
    assert body["results"][0]["action_label"] == "Apply Now"
    assert body["results"][0]["feedback_adjustment"] == 5.0


def test_profile_recommend_returns_404_for_missing_profile(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    response = client.post("/profiles/missing/recommend", json={"top_k": 1})
    body = response.json()

    assert response.status_code == 404
    assert "Profile not found" in body["detail"]
