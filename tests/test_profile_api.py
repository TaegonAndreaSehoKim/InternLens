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
        "major": "Computer Science",
        "grad_date": "2027-12",
        "preferred_roles": ["Machine Learning Engineer Intern"],
        "preferred_locations": ["Remote", "California"],
        "target_industries": ["AI", "Tech"],
        "sponsorship_need": True,
        "extracted_skills": ["Python", "Machine Learning"],
        "years_of_experience": 1,
        "notes": "Interested in recommender systems",
    }


def _account_profile_payload() -> dict:
    payload = _profile_payload().copy()
    payload.pop("profile_id")
    return payload


def _patch_ranked_jobs(monkeypatch, ranked_jobs: list[dict]) -> None:
    monkeypatch.setattr(
        api_app,
        "load_all_job_postings",
        lambda path: [
            {
                "job_id": ranked_job["job_id"],
                "company": ranked_job["company"],
                "title": ranked_job["title"],
                "location": ranked_job["location"],
                "description": "internship role",
                "min_qualifications": "python",
                "preferred_qualifications": "pytorch",
                "posting_date": "2026-04-10",
                "sponsorship_info": "",
                "employment_type": "Internship",
                "source": "manual",
                "source_url": ranked_job.get("source_url", f"https://example.com/jobs/{ranked_job['job_id']}"),
            }
            for ranked_job in ranked_jobs
        ],
    )
    monkeypatch.setattr(
        api_app,
        "rank_jobs",
        lambda profile, jobs: ranked_jobs,
    )


def _patch_single_ranked_job(monkeypatch) -> None:
    _patch_ranked_jobs(
        monkeypatch,
        [
            {
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
        ],
    )


def test_profile_create_get_and_update_flow(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    create_response = client.post("/profiles", json=_profile_payload())
    create_body = create_response.json()

    assert create_response.status_code == 201
    assert create_body["profile_id"] == "user_001"
    assert create_body["degree_level"] == "master's"
    assert create_body["major"] == "computer science"
    assert create_body["majors"] == ["computer science"]
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


def test_profile_create_accepts_multiple_majors(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    payload = _profile_payload() | {"majors": ["Computer Science", "Statistics"]}
    response = client.post("/profiles", json=payload)
    body = response.json()

    assert response.status_code == 201
    assert body["major"] == "computer science"
    assert body["majors"] == ["computer science", "statistics"]


def test_profile_api_scopes_data_by_user_header(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    first_profile = _profile_payload() | {"notes": "first account"}
    second_profile = _profile_payload() | {"notes": "second account"}
    first_headers = {"X-InternLens-User-Id": "cognito-sub-a"}
    second_headers = {"X-InternLens-User-Id": "cognito-sub-b"}

    assert client.post("/profiles", json=first_profile, headers=first_headers).status_code == 201
    assert client.post("/profiles", json=second_profile, headers=second_headers).status_code == 201

    client.post(
        "/profiles/user_001/feedback",
        json={
            "profile_id": "user_001",
            "events": [{"job_id": "job_a", "feedback_label": "saved"}],
        },
        headers=first_headers,
    )

    first_response = client.get("/profiles/user_001", headers=first_headers)
    second_response = client.get("/profiles/user_001", headers=second_headers)
    first_feedback = client.get("/profiles/user_001/feedback", headers=first_headers)
    second_feedback = client.get("/profiles/user_001/feedback", headers=second_headers)

    assert first_response.status_code == 200
    assert first_response.json()["notes"] == "first account"
    assert second_response.status_code == 200
    assert second_response.json()["notes"] == "second account"
    assert len(first_feedback.json()["events"]) == 1
    assert second_feedback.json()["events"] == []


def test_account_profile_api_uses_current_user_default_profile(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    first_headers = {"X-InternLens-User-Id": "cognito-sub-a"}
    second_headers = {"X-InternLens-User-Id": "cognito-sub-b"}

    first_payload = _account_profile_payload() | {"notes": "first account"}
    second_payload = _account_profile_payload() | {"notes": "second account"}

    first_create = client.put("/me/profile", json=first_payload, headers=first_headers)
    second_create = client.put("/me/profile", json=second_payload, headers=second_headers)

    assert first_create.status_code == 200
    assert second_create.status_code == 200
    assert first_create.json()["profile_id"] == "default"

    first_response = client.get("/me/profile", headers=first_headers)
    second_response = client.get("/me/profile", headers=second_headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["notes"] == "first account"
    assert second_response.json()["notes"] == "second account"


def test_account_profile_recommendation_and_job_action_flow(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)
    _patch_single_ranked_job(monkeypatch)

    headers = {"X-InternLens-User-Id": "cognito-sub-a"}

    assert client.put("/me/profile", json=_account_profile_payload(), headers=headers).status_code == 200

    recommend_response = client.post("/me/recommend", json={"top_k": 1}, headers=headers)
    recommend_body = recommend_response.json()

    assert recommend_response.status_code == 200
    assert recommend_body["run_id"]
    assert recommend_body["returned_jobs"] == 1

    action_response = client.post(
        "/me/jobs/job_a/action",
        json={"action": "save", "run_id": recommend_body["run_id"]},
        headers=headers,
    )

    assert action_response.status_code == 200
    assert action_response.json()["job_state"]["state"] == "saved"

    dashboard_response = client.get("/me/dashboard", headers=headers)
    saved_jobs_response = client.get("/me/saved-jobs", headers=headers)
    run_response = client.get(f"/me/recommendations/{recommend_body['run_id']}", headers=headers)

    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["summary"]["saved_jobs_count"] == 1
    assert saved_jobs_response.json()["jobs"][0]["job_id"] == "job_a"
    assert run_response.json()["results"][0]["user_job_state"] == "saved"


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


def test_profile_summary_aggregates_activity(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    client.post(
        "/profiles/user_001/feedback",
        json={
            "profile_id": "user_001",
            "events": [
                {"job_id": "job_a", "feedback_label": "saved"},
                {"job_id": "job_b", "feedback_label": "applied"},
            ],
        },
    )
    _patch_ranked_jobs(
        monkeypatch,
        [
            {
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
            },
            {
                "job_id": "job_b",
                "company": "example",
                "title": "data science intern",
                "location": "remote",
                "score": 82.0,
                "action_label": "Apply Now",
                "matched_skills": ["python"],
                "skill_gaps": [],
                "reasons": ["Relevant role match"],
                "blocking_issues": [],
                "component_scores": {
                    "skill_score": 45.0,
                    "role_score": 20.0,
                    "location_score": 10.0,
                    "internship_bonus": 7.0,
                },
                "source_url": "https://example.com/jobs/job_b",
                "application_url": "https://example.com/jobs/job_b/apply",
            },
        ],
    )

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 2}).json()["run_id"]
    client.post("/profiles/user_001/jobs/job_a/save", json={"run_id": run_id})
    client.post("/profiles/user_001/jobs/job_b/dismiss", json={"run_id": run_id})
    client.post("/profiles/user_001/jobs/job_a/action", json={"action": "apply", "run_id": run_id})

    summary_response = client.get("/profiles/user_001/summary")
    summary_body = summary_response.json()

    assert summary_response.status_code == 200
    assert summary_body["profile_id"] == "user_001"
    assert summary_body["recommendation_run_count"] == 1
    assert summary_body["saved_jobs_count"] == 0
    assert summary_body["dismissed_jobs_count"] == 1
    assert summary_body["applied_jobs_count"] == 1
    assert summary_body["feedback_event_count"] == 5
    assert summary_body["feedback_label_counts"] == {"saved": 2, "applied": 2, "skipped": 1}
    assert summary_body["last_recommendation_at"] is not None
    assert summary_body["last_feedback_at"] is not None
    assert summary_body["last_saved_job_at"] is None
    assert summary_body["last_dismissed_job_at"] is not None
    assert summary_body["last_applied_job_at"] is not None


def test_profile_activity_returns_recent_mixed_events(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    client.post(
        "/profiles/user_001/feedback",
        json={
            "profile_id": "user_001",
            "events": [{"job_id": "job_a", "feedback_label": "saved"}],
        },
    )
    _patch_ranked_jobs(
        monkeypatch,
        [
            {
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
        ],
    )

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 1}).json()["run_id"]
    client.post("/profiles/user_001/jobs/job_a/save", json={"run_id": run_id})

    activity_response = client.get("/profiles/user_001/activity?limit=4")
    activity_body = activity_response.json()

    assert activity_response.status_code == 200
    assert activity_body["profile_id"] == "user_001"
    assert len(activity_body["activities"]) == 4
    assert {item["activity_type"] for item in activity_body["activities"]} == {
        "recommendation_run",
        "feedback",
        "saved",
    }


def test_profile_dashboard_returns_combined_snapshot(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    client.post(
        "/profiles/user_001/feedback",
        json={
            "profile_id": "user_001",
            "events": [{"job_id": "job_a", "feedback_label": "saved"}],
        },
    )
    _patch_ranked_jobs(
        monkeypatch,
        [
            {
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
            },
            {
                "job_id": "job_b",
                "company": "example",
                "title": "data science intern",
                "location": "remote",
                "score": 82.0,
                "action_label": "Apply Now",
                "matched_skills": ["python"],
                "skill_gaps": [],
                "reasons": ["Relevant role match"],
                "blocking_issues": [],
                "component_scores": {
                    "skill_score": 45.0,
                    "role_score": 20.0,
                    "location_score": 10.0,
                    "internship_bonus": 7.0,
                },
                "source_url": "https://example.com/jobs/job_b",
                "application_url": "https://example.com/jobs/job_b/apply",
            },
        ],
    )

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 2}).json()["run_id"]
    client.post("/profiles/user_001/jobs/job_a/save", json={"run_id": run_id})
    client.post("/profiles/user_001/jobs/job_b/action", json={"action": "apply", "run_id": run_id})

    response = client.get(
        "/profiles/user_001/dashboard?activity_limit=2&run_limit=1&saved_job_limit=1&applied_job_limit=1"
    )
    body = response.json()

    assert response.status_code == 200
    assert body["profile_id"] == "user_001"
    assert body["summary"]["recommendation_run_count"] == 1
    assert body["summary"]["saved_jobs_count"] == 1
    assert body["summary"]["applied_jobs_count"] == 1
    assert len(body["activity"]["activities"]) == 2
    assert len(body["recent_runs"]) == 1
    assert body["recent_runs"][0]["run_id"] == run_id
    assert len(body["saved_jobs"]) == 1
    assert body["saved_jobs"][0]["job_id"] == "job_a"
    assert body["dismissed_jobs"] == []
    assert len(body["applied_jobs"]) == 1
    assert body["applied_jobs"][0]["job_id"] == "job_b"
    assert [action["action"] for action in body["recommended_next_actions"]] == [
        "apply_saved_job",
        "review_applied_job",
        "refresh_recommendations",
    ]
    assert body["recommended_next_actions"][0]["target_job_id"] == "job_a"


def test_profile_dashboard_recommends_first_run_for_empty_profile(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())

    response = client.get("/profiles/user_001/dashboard")
    body = response.json()

    assert response.status_code == 200
    assert body["summary"]["recommendation_run_count"] == 0
    assert body["activity"]["activities"] == []
    assert body["recent_runs"] == []
    assert body["saved_jobs"] == []
    assert body["applied_jobs"] == []
    assert body["recommended_next_actions"] == [
        {
            "action": "run_recommendation",
            "label": "Run your first recommendation",
            "description": "Create a recommendation run from the stored profile and current job corpus.",
            "priority": 1,
            "target_job_id": None,
            "target_run_id": None,
        }
    ]


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
        json={"include_debug": True, "suppress_similar_results": True, "top_k": 1},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["profile_source"] == "stored_profile:user_001"
    assert body["feedback_source"] == "stored_feedback_events"
    assert body["reranking_applied"] is True
    assert body["jobs_dir"] == "data/processed/jobs"
    assert body["run_id"].startswith("run_")
    assert body["results"][0]["action_label"] == "Apply Now"
    assert body["results"][0]["feedback_adjustment"] == 5.0

    runs_response = client.get("/profiles/user_001/recommendations")
    runs_body = runs_response.json()

    assert runs_response.status_code == 200
    assert len(runs_body["runs"]) == 1
    assert runs_body["runs"][0]["run_id"] == body["run_id"]
    assert runs_body["runs"][0]["suppress_similar_results"] is True

    run_detail_response = client.get(f"/profiles/user_001/recommendations/{body['run_id']}")
    run_detail_body = run_detail_response.json()

    assert run_detail_response.status_code == 200
    assert run_detail_body["run_id"] == body["run_id"]
    assert run_detail_body["results"][0]["job_id"] == "job_a"


def test_profile_recommend_can_skip_run_persistence(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    _patch_single_ranked_job(monkeypatch)

    response = client.post(
        "/profiles/user_001/recommend",
        json={"save_run": False, "top_k": 1},
    )
    body = response.json()

    assert response.status_code == 200
    assert "run_id" not in body

    runs_response = client.get("/profiles/user_001/recommendations")
    runs_body = runs_response.json()

    assert runs_response.status_code == 200
    assert runs_body["runs"] == []


def test_saved_and_dismissed_job_state_flow(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    _patch_single_ranked_job(monkeypatch)

    recommend_response = client.post("/profiles/user_001/recommend", json={"top_k": 1})
    run_id = recommend_response.json()["run_id"]

    save_response = client.post(
        "/profiles/user_001/jobs/job_a/save",
        json={"run_id": run_id},
    )
    save_body = save_response.json()

    assert save_response.status_code == 201
    assert save_body["state"] == "saved"
    assert save_body["source_run_id"] == run_id
    assert save_body["job_snapshot"]["job_id"] == "job_a"
    assert save_body["job_snapshot"]["recommendation"] == "apply_now"

    saved_response = client.get("/profiles/user_001/saved-jobs")
    saved_body = saved_response.json()

    assert saved_response.status_code == 200
    assert saved_body["state"] == "saved"
    assert len(saved_body["jobs"]) == 1
    assert saved_body["jobs"][0]["job_id"] == "job_a"

    saved_recommend_response = client.post("/profiles/user_001/recommend", json={"top_k": 1})
    saved_recommend_body = saved_recommend_response.json()

    assert saved_recommend_response.status_code == 200
    assert saved_recommend_body["results"][0]["job_id"] == "job_a"
    assert saved_recommend_body["results"][0]["user_job_state"] == "saved"
    assert saved_recommend_body["results"][0]["user_job_state_source_run_id"] == run_id

    dismiss_response = client.post(
        "/profiles/user_001/jobs/job_a/dismiss",
        json={"run_id": run_id},
    )
    dismiss_body = dismiss_response.json()

    assert dismiss_response.status_code == 201
    assert dismiss_body["state"] == "dismissed"

    saved_after_dismiss = client.get("/profiles/user_001/saved-jobs").json()
    dismissed_after_dismiss = client.get("/profiles/user_001/dismissed-jobs").json()
    feedback_after_dismiss = client.get("/profiles/user_001/feedback").json()

    assert saved_after_dismiss["jobs"] == []
    assert len(dismissed_after_dismiss["jobs"]) == 1
    assert dismissed_after_dismiss["jobs"][0]["job_id"] == "job_a"
    assert [event["feedback_label"] for event in feedback_after_dismiss["events"]] == ["saved", "skipped"]

    clear_dismiss_response = client.delete("/profiles/user_001/jobs/job_a/dismiss")
    assert clear_dismiss_response.status_code == 200

    dismissed_after_clear = client.get("/profiles/user_001/dismissed-jobs").json()
    feedback_after_clear = client.get("/profiles/user_001/feedback").json()
    assert dismissed_after_clear["jobs"] == []
    assert [event["feedback_label"] for event in feedback_after_clear["events"]] == ["saved", "skipped"]


def test_unified_job_action_endpoint_handles_save_dismiss_and_clear(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    _patch_single_ranked_job(monkeypatch)

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 1}).json()["run_id"]

    save_response = client.post(
        "/profiles/user_001/jobs/job_a/action",
        json={"action": "save", "run_id": run_id},
    )
    save_body = save_response.json()

    assert save_response.status_code == 200
    assert save_body["action"] == "save"
    assert save_body["job_state"]["state"] == "saved"
    assert save_body["job_state"]["source_run_id"] == run_id
    assert save_body["feedback_synced"] is True
    assert save_body["feedback_label"] == "saved"

    dismiss_response = client.post(
        "/profiles/user_001/jobs/job_a/action",
        json={"action": "dismiss", "run_id": run_id},
    )
    dismiss_body = dismiss_response.json()

    assert dismiss_response.status_code == 200
    assert dismiss_body["action"] == "dismiss"
    assert dismiss_body["job_state"]["state"] == "dismissed"
    assert dismiss_body["feedback_synced"] is True
    assert dismiss_body["feedback_label"] == "skipped"

    duplicate_dismiss_response = client.post(
        "/profiles/user_001/jobs/job_a/action",
        json={"action": "dismiss", "run_id": run_id},
    )
    duplicate_dismiss_body = duplicate_dismiss_response.json()

    assert duplicate_dismiss_response.status_code == 200
    assert duplicate_dismiss_body["feedback_synced"] is False
    assert duplicate_dismiss_body["feedback_label"] is None

    clear_response = client.post(
        "/profiles/user_001/jobs/job_a/action",
        json={"action": "clear"},
    )
    clear_body = clear_response.json()

    assert clear_response.status_code == 200
    assert clear_body["action"] == "clear"
    assert clear_body["job_state"] is None
    assert clear_body["feedback_synced"] is False
    assert client.get("/profiles/user_001/saved-jobs").json()["jobs"] == []
    assert client.get("/profiles/user_001/dismissed-jobs").json()["jobs"] == []
    assert [event["feedback_label"] for event in client.get("/profiles/user_001/feedback").json()["events"]] == [
        "saved",
        "skipped",
    ]


def test_unified_job_action_endpoint_tracks_applied_jobs(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    _patch_single_ranked_job(monkeypatch)

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 1}).json()["run_id"]

    apply_response = client.post(
        "/profiles/user_001/jobs/job_a/action",
        json={"action": "apply", "run_id": run_id},
    )
    apply_body = apply_response.json()

    assert apply_response.status_code == 200
    assert apply_body["action"] == "apply"
    assert apply_body["job_state"]["state"] == "applied"
    assert apply_body["job_state"]["source_run_id"] == run_id
    assert apply_body["feedback_synced"] is True
    assert apply_body["feedback_label"] == "applied"

    applied_response = client.get("/profiles/user_001/applied-jobs")
    applied_body = applied_response.json()

    assert applied_response.status_code == 200
    assert applied_body["state"] == "applied"
    assert len(applied_body["jobs"]) == 1
    assert applied_body["jobs"][0]["job_id"] == "job_a"
    assert [event["feedback_label"] for event in client.get("/profiles/user_001/feedback").json()["events"]] == [
        "applied"
    ]


def test_profile_recommend_excludes_dismissed_jobs_by_default(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    _patch_ranked_jobs(
        monkeypatch,
        [
            {
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
            },
            {
                "job_id": "job_b",
                "company": "example",
                "title": "data science intern",
                "location": "remote",
                "score": 82.0,
                "action_label": "Apply Now",
                "matched_skills": ["python"],
                "skill_gaps": [],
                "reasons": ["Relevant role match"],
                "blocking_issues": [],
                "component_scores": {
                    "skill_score": 45.0,
                    "role_score": 20.0,
                    "location_score": 10.0,
                    "internship_bonus": 7.0,
                },
                "source_url": "https://example.com/jobs/job_b",
                "application_url": "https://example.com/jobs/job_b/apply",
            },
        ],
    )

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 2}).json()["run_id"]
    dismiss_response = client.post("/profiles/user_001/jobs/job_a/dismiss", json={"run_id": run_id})
    assert dismiss_response.status_code == 201

    response = client.post("/profiles/user_001/recommend", json={"top_k": 2})
    body = response.json()

    assert response.status_code == 200
    assert [result["job_id"] for result in body["results"]] == ["job_b"]


def test_profile_recommend_can_include_dismissed_jobs(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    _patch_ranked_jobs(
        monkeypatch,
        [
            {
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
            },
            {
                "job_id": "job_b",
                "company": "example",
                "title": "data science intern",
                "location": "remote",
                "score": 82.0,
                "action_label": "Apply Now",
                "matched_skills": ["python"],
                "skill_gaps": [],
                "reasons": ["Relevant role match"],
                "blocking_issues": [],
                "component_scores": {
                    "skill_score": 45.0,
                    "role_score": 20.0,
                    "location_score": 10.0,
                    "internship_bonus": 7.0,
                },
                "source_url": "https://example.com/jobs/job_b",
                "application_url": "https://example.com/jobs/job_b/apply",
            },
        ],
    )

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 2}).json()["run_id"]
    dismiss_response = client.post("/profiles/user_001/jobs/job_a/dismiss", json={"run_id": run_id})
    assert dismiss_response.status_code == 201

    response = client.post(
        "/profiles/user_001/recommend",
        json={"top_k": 2, "exclude_dismissed": False},
    )
    body = response.json()

    assert response.status_code == 200
    assert [result["job_id"] for result in body["results"]] == ["job_a", "job_b"]
    assert body["results"][0]["user_job_state"] == "dismissed"
    assert body["results"][0]["user_job_state_source_run_id"] == run_id
    assert "user_job_state_updated_at" in body["results"][0]


def test_profile_recommend_excludes_applied_jobs_by_default(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    _patch_ranked_jobs(
        monkeypatch,
        [
            {
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
            },
            {
                "job_id": "job_b",
                "company": "example",
                "title": "data science intern",
                "location": "remote",
                "score": 82.0,
                "action_label": "Apply Now",
                "matched_skills": ["python"],
                "skill_gaps": [],
                "reasons": ["Relevant role match"],
                "blocking_issues": [],
                "component_scores": {
                    "skill_score": 45.0,
                    "role_score": 20.0,
                    "location_score": 10.0,
                    "internship_bonus": 7.0,
                },
                "source_url": "https://example.com/jobs/job_b",
                "application_url": "https://example.com/jobs/job_b/apply",
            },
        ],
    )

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 2}).json()["run_id"]
    apply_response = client.post(
        "/profiles/user_001/jobs/job_a/action",
        json={"action": "apply", "run_id": run_id},
    )
    assert apply_response.status_code == 200

    response = client.post("/profiles/user_001/recommend", json={"top_k": 2})
    body = response.json()

    assert response.status_code == 200
    assert [result["job_id"] for result in body["results"]] == ["job_b"]


def test_profile_recommend_can_include_applied_jobs(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())
    _patch_ranked_jobs(
        monkeypatch,
        [
            {
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
            },
            {
                "job_id": "job_b",
                "company": "example",
                "title": "data science intern",
                "location": "remote",
                "score": 82.0,
                "action_label": "Apply Now",
                "matched_skills": ["python"],
                "skill_gaps": [],
                "reasons": ["Relevant role match"],
                "blocking_issues": [],
                "component_scores": {
                    "skill_score": 45.0,
                    "role_score": 20.0,
                    "location_score": 10.0,
                    "internship_bonus": 7.0,
                },
                "source_url": "https://example.com/jobs/job_b",
                "application_url": "https://example.com/jobs/job_b/apply",
            },
        ],
    )

    run_id = client.post("/profiles/user_001/recommend", json={"top_k": 2}).json()["run_id"]
    apply_response = client.post(
        "/profiles/user_001/jobs/job_a/action",
        json={"action": "apply", "run_id": run_id},
    )
    assert apply_response.status_code == 200

    run_detail_response = client.get(f"/profiles/user_001/recommendations/{run_id}")
    run_detail_body = run_detail_response.json()

    assert run_detail_response.status_code == 200
    assert run_detail_body["results"][0]["user_job_state"] == "applied"
    assert run_detail_body["results"][0]["user_job_state_source_run_id"] == run_id
    assert "user_job_state_updated_at" in run_detail_body["results"][0]

    response = client.post(
        "/profiles/user_001/recommend",
        json={"top_k": 2, "exclude_applied": False},
    )
    body = response.json()

    assert response.status_code == 200
    assert [result["job_id"] for result in body["results"]] == ["job_a", "job_b"]
    assert body["results"][0]["user_job_state"] == "applied"
    assert body["results"][0]["user_job_state_source_run_id"] == run_id
    assert "user_job_state_updated_at" in body["results"][0]


def test_save_job_rejects_missing_recommendation_run(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())

    response = client.post(
        "/profiles/user_001/jobs/job_a/save",
        json={"run_id": "run_missing"},
    )
    body = response.json()

    assert response.status_code == 404
    assert "Recommendation run not found" in body["detail"]


def test_unified_job_action_clear_returns_404_when_state_missing(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())

    response = client.post(
        "/profiles/user_001/jobs/job_a/action",
        json={"action": "clear"},
    )
    body = response.json()

    assert response.status_code == 404
    assert "Job state not found" in body["detail"]


def test_profile_recommendation_run_detail_returns_404_for_missing_run(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())

    response = client.get("/profiles/user_001/recommendations/run_missing")
    body = response.json()

    assert response.status_code == 404
    assert "Recommendation run not found" in body["detail"]


def test_profile_recommend_returns_404_for_missing_profile(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    response = client.post("/profiles/missing/recommend", json={"top_k": 1})
    body = response.json()

    assert response.status_code == 404
    assert "Profile not found" in body["detail"]


def test_profile_summary_returns_404_for_missing_profile(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    response = client.get("/profiles/missing/summary")
    body = response.json()

    assert response.status_code == 404
    assert "Profile not found" in body["detail"]


def test_profile_activity_rejects_invalid_limit(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())

    response = client.get("/profiles/user_001/activity?limit=0")
    body = response.json()

    assert response.status_code == 400
    assert "limit must be between 1 and 100" in body["detail"]


def test_profile_activity_returns_404_for_missing_profile(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    response = client.get("/profiles/missing/activity")
    body = response.json()

    assert response.status_code == 404
    assert "Profile not found" in body["detail"]


def test_profile_dashboard_rejects_invalid_limits(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    client.post("/profiles", json=_profile_payload())

    response = client.get("/profiles/user_001/dashboard?activity_limit=0")
    body = response.json()

    assert response.status_code == 400
    assert "activity_limit must be between 1 and 100" in body["detail"]


def test_profile_dashboard_returns_404_for_missing_profile(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "internlens.db"
    monkeypatch.setattr(api_app, "_database_path", lambda: db_path)

    response = client.get("/profiles/missing/dashboard")
    body = response.json()

    assert response.status_code == 404
    assert "Profile not found" in body["detail"]
