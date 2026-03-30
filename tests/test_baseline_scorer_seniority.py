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

def test_non_intern_ml_role_is_blocked_even_if_title_matches() -> None:
    # A strong ML title should still be blocked when the posting does not look like an internship.
    profile = _build_profile()
    job = {
        "job_id": "non_intern_ml_role",
        "company": "example",
        "title": "Machine Learning Engineer - VLM/LLM Integration",
        "location": "Mountain View, CA, USA",
        "description": "Build production ML systems for multimodal models.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "",
        "source": "manual",
        "remote_status": "",
    }

    result = score_job(profile, job)

    assert result["action_label"] == "Skip"
    assert "This role does not appear to be an internship" in result["blocking_issues"]


def test_true_internship_surfaces_above_non_intern_ml_role() -> None:
    # Explicit internship language should beat a non-intern ML role once the blocker is enforced.
    profile = _build_profile()

    internship_job = {
        "job_id": "intern_role",
        "company": "example",
        "title": "2026 Summer Intern, BS/MS, Software Engineering, Simulation",
        "location": "Mountain View, CA",
        "description": "Join our summer internship program building simulation systems.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "",
    }

    non_intern_ml_job = {
        "job_id": "non_intern_ml_role",
        "company": "example",
        "title": "Machine Learning Engineer - VLM/LLM Integration",
        "location": "Mountain View, CA, USA",
        "description": "Build production ML systems for multimodal models.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "",
        "source": "manual",
        "remote_status": "",
    }

    internship_result = score_job(profile, internship_job)
    non_intern_result = score_job(profile, non_intern_ml_job)

    assert "This role does not appear to be an internship" not in internship_result["blocking_issues"]
    assert "This role does not appear to be an internship" in non_intern_result["blocking_issues"]