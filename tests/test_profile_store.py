from __future__ import annotations

import sqlite3
from pathlib import Path

from src.storage.profile_store import (
    create_profile,
    create_recommendation_run,
    get_profile,
    get_recommendation_run,
    initialize_database,
    list_recommendation_runs,
)


def _profile_payload() -> dict:
    return {
        "profile_id": "user_001",
        "resume_text": "Python, machine learning, ranking systems",
        "degree_level": "master's",
        "grad_date": "2027-12",
        "preferred_roles": ["machine learning engineer intern"],
        "preferred_locations": ["remote", "california"],
        "target_industries": ["ai", "tech"],
        "sponsorship_need": True,
        "extracted_skills": ["python", "machine learning"],
        "years_of_experience": 1,
        "notes": "Interested in recommender systems",
    }


def test_initialize_database_migrates_recommendation_runs_for_suppress_similar_flag(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "internlens.db"

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE recommendation_runs (
                run_id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                jobs_dir TEXT NOT NULL,
                top_k INTEGER NOT NULL,
                eligible_only INTEGER NOT NULL,
                applyable_only INTEGER NOT NULL,
                include_feedback INTEGER NOT NULL,
                include_debug INTEGER NOT NULL,
                reranking_applied INTEGER NOT NULL,
                feedback_source TEXT,
                total_jobs_scored INTEGER NOT NULL,
                returned_jobs INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(recommendation_runs)").fetchall()
        }

    assert "suppress_similar_results" in columns


def test_create_recommendation_run_persists_suppress_similar_flag(tmp_path: Path) -> None:
    db_path = tmp_path / "internlens.db"
    create_profile(db_path, _profile_payload())

    run = create_recommendation_run(
        db_path,
        profile_id="user_001",
        jobs_dir="data/processed/jobs",
        top_k=5,
        eligible_only=False,
        applyable_only=True,
        suppress_similar_results=True,
        include_feedback=True,
        include_debug=False,
        reranking_applied=False,
        feedback_source=None,
        total_jobs_scored=12,
        returned_jobs=3,
        results=[
            {
                "job_id": "job_a",
                "company": "example",
                "title": "machine learning engineer intern",
                "location": "remote",
                "recommendation": "apply_now",
                "fit_level": "strong",
                "eligibility_status": "eligible",
                "summary": "Strong match for your profile.",
                "why_apply": ["Strong skill overlap"],
                "watchouts": [],
            }
        ],
    )

    listed_runs = list_recommendation_runs(db_path, "user_001")
    stored_run = get_recommendation_run(db_path, "user_001", run["run_id"])

    assert run["suppress_similar_results"] is True
    assert listed_runs[0]["suppress_similar_results"] is True
    assert stored_run is not None
    assert stored_run["suppress_similar_results"] is True


def test_profiles_are_scoped_by_user_id(tmp_path: Path) -> None:
    db_path = tmp_path / "internlens.db"
    first_profile = _profile_payload() | {"notes": "first user"}
    second_profile = _profile_payload() | {"notes": "second user"}

    create_profile(db_path, first_profile, user_id="cognito-sub-a")
    create_profile(db_path, second_profile, user_id="cognito-sub-b")

    first = get_profile(db_path, "user_001", user_id="cognito-sub-a")
    second = get_profile(db_path, "user_001", user_id="cognito-sub-b")

    assert first is not None
    assert first["user_id"] == "cognito-sub-a"
    assert first["notes"] == "first user"
    assert second is not None
    assert second["user_id"] == "cognito-sub-b"
    assert second["notes"] == "second user"
    assert get_profile(db_path, "user_001", user_id="missing-user") is None
