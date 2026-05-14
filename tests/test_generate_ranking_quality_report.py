from __future__ import annotations

from scripts.generate_ranking_quality_report import build_quality_report
from scripts.generate_ranking_quality_report import render_markdown_report


def _job(job_id: str, title: str, description: str, min_qualifications: str = "") -> dict:
    return {
        "job_id": job_id,
        "company": "Example",
        "title": title,
        "location": "Remote",
        "description": description,
        "min_qualifications": min_qualifications,
        "preferred_qualifications": "",
        "posting_date": "2026-05-10",
        "freshness_days": 3,
        "sponsorship_info": "",
        "employment_type": "Internship",
        "team": "Engineering",
        "source": "manual",
        "remote_status": "remote",
    }


def test_build_quality_report_scores_representative_profiles() -> None:
    jobs = [
        _job(
            "software_intern",
            "Software Engineering Intern",
            "Build backend services with Python and SQL.",
            "Python",
        ),
        _job(
            "marketing_intern",
            "Marketing Intern",
            "Support brand campaigns and social media reporting.",
            "Data analysis",
        ),
    ]

    report = build_quality_report(jobs, top_k=1)

    assert report["top_k"] == 1
    assert {profile["profile_name"] for profile in report["profiles"]} == {
        "cs_engineering",
        "data_ml",
        "marketing_growth",
        "finance_analyst",
    }
    assert all(profile["top_jobs"] for profile in report["profiles"])


def test_render_markdown_report_includes_profile_sections() -> None:
    jobs = [
        _job(
            "data_intern",
            "Data Scientist Intern",
            "Use Python, SQL, statistics, and machine learning.",
            "Python",
        )
    ]
    report = build_quality_report(jobs, top_k=1)

    markdown = render_markdown_report(report)

    assert "# Ranking Quality Report" in markdown
    assert "## cs_engineering" in markdown
    assert "## finance_analyst" in markdown
    assert "| Rank | Action | Score | Company | Role | Location | Matched | Gaps |" in markdown
    assert "Data Scientist Intern" in markdown
