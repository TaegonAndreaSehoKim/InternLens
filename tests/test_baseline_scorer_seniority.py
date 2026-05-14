from __future__ import annotations

from src.ranking.baseline_scorer import score_job
from src.ranking.baseline_scorer import rank_jobs


def _build_profile() -> dict:
    return {
        "degree_level": "Master's",
        "major": "computer science",
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

def test_people_team_intern_does_not_get_noisy_fallback_skill_matches() -> None:
    profile = _build_profile()

    job = {
        "job_id": "people_team_intern",
        "company": "example",
        "title": "People Team Intern - HR Operations & AI Innovation (Summer 2026)",
        "location": "Austin, US",
        "description": "Support Python dashboards and machine learning-enabled internal workflows.",
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


def test_product_manager_intern_does_not_get_noisy_python_match() -> None:
    profile = _build_profile()

    job = {
        "job_id": "product_manager_intern",
        "company": "example",
        "title": "Product Manager Intern (Summer 2026)",
        "location": "Austin, US",
        "description": "Work with Python-based product dashboards and AI feature planning.",
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


def test_business_analyst_intern_keeps_fallback_skill_matching_but_stays_skip() -> None:
    profile = _build_profile()

    job = {
        "job_id": "business_analyst_intern",
        "company": "example",
        "title": "Business Analyst Intern, Revenue Operations (AI Innovation) (Summer 2026)",
        "location": "Austin, US",
        "description": "Use data analysis and Python to evaluate operational trends.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "onsite",
    }

    result = score_job(profile, job)

    assert "data analysis" in result["matched_skills"]
    assert result["action_label"] == "Skip"


def test_digital_marketing_intern_stays_skip_despite_analytics_match() -> None:
    profile = _build_profile()

    job = {
        "job_id": "digital_marketing_intern",
        "company": "example",
        "title": "Digital Marketing Intern",
        "location": "Springdale, AR",
        "description": (
            "Join an internship program as a creative marketing intern supporting "
            "campaigns, content, and social media reporting."
        ),
        "min_qualifications": (
            "Pursuing a degree in Marketing, Communications, Graphic Design, or a "
            "related field. Experience with social media platforms and analytics tools."
        ),
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Graphic Design/ Marketing",
        "team": "Work-Based Learning",
        "source": "manual",
        "remote_status": "onsite",
    }

    result = score_job(profile, job)

    assert "data analysis" in result["matched_skills"]
    assert result["action_label"] == "Skip"


def test_core_data_intern_ranks_above_marketing_intern_with_analytics_match() -> None:
    profile = _build_profile()
    marketing_job = {
        "job_id": "digital_marketing_intern",
        "company": "example",
        "title": "Digital Marketing Intern",
        "location": "Springdale, AR",
        "description": "Join an internship program supporting social media reporting.",
        "min_qualifications": "Experience with social media platforms and analytics tools.",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Graphic Design/ Marketing",
        "team": "Work-Based Learning",
        "source": "manual",
        "remote_status": "onsite",
    }
    data_job = {
        "job_id": "data_science_intern",
        "company": "example",
        "title": "Data Science Intern",
        "location": "Remote",
        "description": "Use Python and machine learning to analyze product data.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Data Science",
        "source": "manual",
        "remote_status": "remote",
    }

    ranked = rank_jobs(profile, [marketing_job, data_job])

    assert ranked[0]["job_id"] == "data_science_intern"
    assert ranked[1]["job_id"] == "digital_marketing_intern"
    assert ranked[1]["action_label"] == "Skip"


def test_data_analytics_intern_still_gets_apply_later_without_business_context() -> None:
    profile = _build_profile()

    job = {
        "job_id": "data_analytics_intern",
        "company": "example",
        "title": "Data Analytics Intern (Summer 2026)",
        "location": "Austin, US",
        "description": "Use Python and data analysis to evaluate operational trends.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source": "manual",
        "remote_status": "onsite",
    }

    result = score_job(profile, job)

    assert "data analysis" in result["matched_skills"]
    assert result["action_label"] == "Apply Later"


def test_major_alignment_boosts_relevant_role() -> None:
    profile = _build_profile()
    job = {
        "job_id": "systems_intern",
        "company": "example",
        "title": "Software Systems Intern",
        "location": "Remote",
        "description": "Build backend systems and developer tooling.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Engineering",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["component_scores"]["major_score"] > 0
    assert any("Major aligns" in reason for reason in result["reasons"])


def test_marketing_major_can_recommend_marketing_internship() -> None:
    profile = {
        **_build_profile(),
        "major": "marketing",
        "preferred_roles": ["Digital Marketing Intern"],
        "target_industries": ["Advertising"],
        "skill_set": {"market research", "content strategy", "social media strategy"},
        "extracted_skills": ["market research", "content strategy", "social media strategy"],
    }
    job = {
        "job_id": "digital_marketing_intern",
        "company": "example",
        "title": "Digital Marketing Intern",
        "location": "Remote",
        "description": "Support campaign analysis, content strategy, brand work, and social media reporting.",
        "min_qualifications": "Pursuing a degree in Marketing, Communications, or a related field.",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Marketing",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["component_scores"]["major_score"] > 0
    assert result["action_label"] in {"Apply Now", "Apply Later"}


def test_multiple_majors_can_match_secondary_major() -> None:
    profile = {
        **_build_profile(),
        "major": "computer science",
        "majors": ["computer science", "marketing"],
        "preferred_roles": ["Digital Marketing Intern"],
        "target_industries": ["Advertising"],
        "skill_set": {"market research", "content strategy"},
        "extracted_skills": ["market research", "content strategy"],
    }
    job = {
        "job_id": "marketing_secondary_major",
        "company": "example",
        "title": "Digital Marketing Intern",
        "location": "Remote",
        "description": "Support campaign analysis, content strategy, brand work, and social media reporting.",
        "min_qualifications": "Pursuing a degree in Marketing, Communications, or a related field.",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Marketing",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["component_scores"]["major_score"] > 0
    assert any("Major aligns" in reason for reason in result["reasons"])


def test_empty_location_preferences_accept_any_location_without_location_reason() -> None:
    profile = {
        **_build_profile(),
        "preferred_locations": [],
    }
    job = {
        "job_id": "any_location_intern",
        "company": "example",
        "title": "Machine Learning Intern",
        "location": "Austin, TX",
        "description": "Build machine learning tools with Python.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Engineering",
        "source": "manual",
        "remote_status": "onsite",
    }

    result = score_job(profile, job)

    assert result["component_scores"]["location_score"] == 1.0
    assert "Location matches a preferred target" not in result["reasons"]


def test_empty_role_preferences_accept_any_title_without_role_reason() -> None:
    profile = {
        **_build_profile(),
        "preferred_roles": [],
    }
    job = {
        "job_id": "open_role_preference",
        "company": "example",
        "title": "Data Science Intern",
        "location": "Remote",
        "description": "Use Python and machine learning to analyze product data.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Data",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["component_scores"]["role_score"] == 1.0
    assert not any("Title aligns with preferred role" in reason for reason in result["reasons"])


def test_empty_role_preferences_do_not_create_relevance_by_themselves() -> None:
    profile = {
        **_build_profile(),
        "major": "other",
        "majors": ["other"],
        "preferred_roles": [],
        "skill_set": set(),
        "extracted_skills": [],
    }
    job = {
        "job_id": "irrelevant_open_role_preference",
        "company": "example",
        "title": "Events Intern",
        "location": "Remote",
        "description": "Support event logistics and guest check-in.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Events",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["component_scores"]["role_score"] == 1.0
    assert result["action_label"] == "Skip"


def test_qualification_coverage_boosts_required_skill_matches() -> None:
    profile = _build_profile()
    covered_job = {
        "job_id": "covered_required_skills",
        "company": "example",
        "title": "Machine Learning Engineer Intern",
        "location": "Remote",
        "description": "Join an internship program building ML systems.",
        "min_qualifications": "Python, machine learning",
        "preferred_qualifications": "PyTorch",
        "posting_date": "2026-03-30",
        "freshness_days": 7,
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Engineering",
        "source": "manual",
        "remote_status": "remote",
    }
    weak_coverage_job = {
        **covered_job,
        "job_id": "weak_required_skills",
        "min_qualifications": "SQL, statistics",
        "preferred_qualifications": "AWS",
    }

    covered_result = score_job(profile, covered_job)
    weak_result = score_job(profile, weak_coverage_job)

    assert covered_result["component_scores"]["qualification_coverage_score"] > weak_result[
        "component_scores"
    ]["qualification_coverage_score"]
    assert covered_result["score"] > weak_result["score"]
    assert any("qualification" in reason.lower() for reason in covered_result["reasons"])


def test_required_skill_match_counts_more_than_preferred_skill_match() -> None:
    base_profile = {
        **_build_profile(),
        "skill_set": {"python"},
        "extracted_skills": ["python"],
    }
    required_match_job = {
        "job_id": "required_python",
        "company": "example",
        "title": "Software Engineering Intern",
        "location": "Remote",
        "description": "Join an internship program building services.",
        "min_qualifications": "Python",
        "preferred_qualifications": "AWS",
        "posting_date": "2026-03-30",
        "freshness_days": 7,
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Engineering",
        "source": "manual",
        "remote_status": "remote",
    }
    preferred_match_job = {
        **required_match_job,
        "job_id": "preferred_python",
        "min_qualifications": "AWS",
        "preferred_qualifications": "Python",
    }

    required_result = score_job(base_profile, required_match_job)
    preferred_result = score_job(base_profile, preferred_match_job)

    assert required_result["component_scores"]["skill_score"] > preferred_result[
        "component_scores"
    ]["skill_score"]
    assert required_result["component_scores"]["qualification_coverage_score"] > preferred_result[
        "component_scores"
    ]["qualification_coverage_score"]


def test_matched_skills_are_ordered_by_skill_priority() -> None:
    profile = {
        **_build_profile(),
        "skill_set": {"python", "aws"},
        "extracted_skills": ["python", "aws"],
    }
    job = {
        "job_id": "priority_order",
        "company": "example",
        "title": "Software Engineering Intern",
        "location": "Remote",
        "description": "Join an internship program building services.",
        "min_qualifications": "AWS",
        "preferred_qualifications": "Python",
        "posting_date": "2026-03-30",
        "freshness_days": 7,
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Engineering",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["matched_skills"][:2] == ["aws", "python"]


def test_skill_gaps_show_required_skills_before_preferred_skills() -> None:
    profile = {
        **_build_profile(),
        "skill_set": {"python"},
        "extracted_skills": ["python"],
    }
    job = {
        "job_id": "priority_gaps",
        "company": "example",
        "title": "Software Engineering Intern",
        "location": "Remote",
        "description": "Join an internship program building services.",
        "min_qualifications": "SQL",
        "preferred_qualifications": "AWS",
        "posting_date": "2026-03-30",
        "freshness_days": 7,
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Engineering",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["skill_gaps"][:2] == ["sql", "aws"]


def test_freshness_score_uses_normalized_freshness_days() -> None:
    profile = _build_profile()
    recent_job = {
        "job_id": "recent_data_intern",
        "company": "example",
        "title": "Data Science Intern",
        "location": "Remote",
        "description": "Use Python and machine learning to analyze product data.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "",
        "freshness_days": 3,
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Data",
        "source": "manual",
        "remote_status": "remote",
    }
    stale_job = {
        **recent_job,
        "job_id": "stale_data_intern",
        "freshness_days": 240,
    }

    recent_result = score_job(profile, recent_job)
    stale_result = score_job(profile, stale_job)

    assert recent_result["component_scores"]["freshness_score"] == 1.0
    assert stale_result["component_scores"]["freshness_score"] == 0.0
    assert recent_result["score"] > stale_result["score"]


def test_neutral_defaults_alone_do_not_create_apply_later() -> None:
    profile = {
        **_build_profile(),
        "major": "other",
        "majors": ["other"],
        "preferred_roles": [],
        "preferred_locations": [],
        "skill_set": set(),
        "extracted_skills": [],
    }
    job = {
        "job_id": "generic_program_intern",
        "company": "example",
        "title": "Program Intern",
        "location": "Remote",
        "description": "Join an internship program and support internal coordination.",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "",
        "freshness_days": 2,
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Programs",
        "source": "manual",
        "remote_status": "remote",
    }

    result = score_job(profile, job)

    assert result["blocking_issues"] == []
    assert result["matched_skills"] == []
    assert result["component_scores"]["role_score"] == 1.0
    assert result["component_scores"]["location_score"] == 1.0
    assert result["action_label"] == "Skip"
