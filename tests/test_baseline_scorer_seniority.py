from __future__ import annotations

from src.ranking.baseline_scorer import score_job
from src.ranking.baseline_scorer import rank_jobs


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

def test_rank_jobs_orders_blocked_roles_by_bucket() -> None:
    # Show blocker-free internships first, then PhD-blocked internships,
    # then non-intern roles, then senior roles.
    profile = _build_profile()

    jobs = [
        {
            "job_id": "true_intern",
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
        },
        {
            "job_id": "phd_intern",
            "company": "example",
            "title": "2026 Intern, PhD, Machine Learning Engineer, Simulation",
            "location": "Mountain View, CA",
            "description": "Internship role for PhD candidates.",
            "min_qualifications": "",
            "preferred_qualifications": "",
            "posting_date": "2026-03-30",
            "sponsorship_info": "",
            "employment_type": "Internship",
            "source": "manual",
            "remote_status": "",
        },
        {
            "job_id": "non_intern_ml",
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
        },
        {
            "job_id": "senior_role",
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
        },
    ]

    ranked = rank_jobs(profile, jobs)
    ranked_ids = [job["job_id"] for job in ranked]

    assert ranked_ids == [
        "true_intern",
        "phd_intern",
        "non_intern_ml",
        "senior_role",
    ]

def test_blocker_free_explicit_internship_gets_apply_later() -> None:
    # A clear internship with no blockers and some relevance signal should
    # not remain Skip.
    profile = _build_profile()

    internship_job = {
        "job_id": "true_intern",
        "company": "example",
        "title": "2026 Summer Intern, BS/MS, Software Engineering, Simulation",
        "location": "Mountain View, CA",
        "description": "Join our summer internship program building Python machine learning simulation systems.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "",
    }

    result = score_job(profile, internship_job)

    assert result["blocking_issues"] == []
    assert result["matched_skills"] != []
    assert result["action_label"] == "Apply Later"

def test_skill_match_uses_title_and_description_signals() -> None:
    # Sparse public postings may not have qualification fields, so title and
    # description should still contribute meaningful skill matches.
    profile = _build_profile()

    job = {
        "job_id": "title_desc_skill_role",
        "company": "example",
        "title": "Machine Learning Engineer Intern",
        "location": "Remote",
        "description": "Work with Python and PyTorch on machine learning systems.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert "machine learning" in result["matched_skills"]
    assert "python" in result["matched_skills"]
    assert "pytorch" in result["matched_skills"]
    assert any("Matched on key skills" in reason for reason in result["reasons"])

def test_structured_qualifications_take_priority_over_title_description_fallback() -> None:
    # When a job already has structured qualification fields, fallback signals
    # from title/description should not overpower the original ranking behavior.
    profile = _build_profile()

    job = {
        "job_id": "structured_job",
        "company": "example",
        "title": "Machine Learning Engineer Intern",
        "location": "Remote",
        "description": "Python PyTorch machine learning everywhere in the description.",
        "min_qualifications": "Experience with statistics",
        "preferred_qualifications": "Experience with recommendation systems",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    # Structured qualification fields are sparse here, so fallback should not
    # flood matched_skills with title/description-only keywords.
    assert "statistics" not in result["matched_skills"]
    assert "recommendation systems" not in result["matched_skills"]

def test_blocker_free_explicit_internship_without_relevance_signal_stays_skip() -> None:
    # Explicit internship language alone should not promote unrelated roles.
    profile = _build_profile()

    internship_job = {
        "job_id": "unrelated_intern",
        "company": "example",
        "title": "Sales Intern (Summer 2026)",
        "location": "In-Office",
        "description": "Join our summer internship program supporting sales operations and outreach.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "",
    }

    result = score_job(profile, internship_job)

    assert result["blocking_issues"] == []
    assert result["matched_skills"] == []
    assert result["action_label"] == "Skip"

def test_non_technical_intern_does_not_get_noisy_fallback_skill_matches() -> None:
    # Non-technical internship titles should not inherit noisy ML/Python matches
    # just because the description contains broad AI or tooling language.
    profile = _build_profile()

    job = {
        "job_id": "marketing_ops_intern",
        "company": "example",
        "title": "Marketing Operations Intern (Summer 2026)",
        "location": "Austin, US",
        "description": "Work with Python dashboards and machine learning-enabled campaign tooling.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "onsite",
    }

    result = score_job(profile, job)

    assert result["matched_skills"] == []
    assert result["action_label"] == "Skip"


def test_technical_intern_still_uses_fallback_skill_matches() -> None:
    # Technical titles should still benefit from title/description fallback matching.
    profile = _build_profile()

    job = {
        "job_id": "data_engineer_intern",
        "company": "example",
        "title": "Data Engineer Intern (Summer 2026)",
        "location": "Austin, US",
        "description": "Use Python and data analysis to build internal data workflows.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "onsite",
    }

    result = score_job(profile, job)

    assert "python" in result["matched_skills"]
    assert "data analysis" in result["matched_skills"]
    assert result["action_label"] == "Apply Later"