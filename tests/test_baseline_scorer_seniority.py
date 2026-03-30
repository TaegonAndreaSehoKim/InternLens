from __future__ import annotations

from src.ranking.baseline_scorer import score_job


def _build_profile() -> dict:
    return {
        "degree_level": "Master's",
        "grad_date": "2027-12",
        "preferred_roles": ["Machine Learning Engineer Intern", "Applied Scientist Intern"],
        "preferred_locations": ["California", "Remote"],
        "target_industries": ["AI", "Tech"],
        "sponsorship_need": True,
        "skill_set": {"python", "pytorch", "machine learning", "data analysis"},
        "extracted_skills": ["python", "pytorch", "machine learning", "data analysis"],
    }


def test_senior_title_triggers_blocker() -> None:
    # Senior-level titles should not surface as internship recommendations.
    profile = _build_profile()
    job = {
        "job_id": "senior_ml_role",
        "company": "example",
        "title": "Senior Machine Learning Engineer",
        "location": "Remote",
        "description": "Build production ML systems.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["action_label"] == "Skip"
    assert "This role appears to be a senior-level position" in result["blocking_issues"]


def test_explicit_internship_signal_adds_bonus_and_reason() -> None:
    # Explicit internship language should raise the score and add an explanation.
    profile = _build_profile()

    internship_job = {
        "job_id": "intern_role",
        "company": "example",
        "title": "Backend Platform Intern",
        "location": "Remote",
        "description": "Join our summer internship program building developer tools.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "remote",
    }

    regular_job = {
        "job_id": "regular_role",
        "company": "example",
        "title": "Backend Platform Engineer",
        "location": "Remote",
        "description": "Build developer tools for production systems.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "",
        "source": "manual",
        "remote_status": "remote",
    }

    internship_result = score_job(profile, internship_job)
    regular_result = score_job(profile, regular_job)

    assert internship_result["score"] > regular_result["score"]
    assert "Posting explicitly identifies this as an internship" in internship_result["reasons"]