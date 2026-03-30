from __future__ import annotations

import json
from pathlib import Path

from src.preprocessing.job_parser import load_all_job_postings
from src.ranking.baseline_scorer import rank_jobs


def _write_job(path: Path, payload: dict) -> None:
    # Write one processed job JSON file for an end-to-end ranking smoke test.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def test_rank_jobs_accepts_nested_crawled_lever_jobs(tmp_path: Path) -> None:
    # Verify that nested crawled jobs can be loaded by the parser and ranked by the baseline ranker.
    crawled_jobs_dir = tmp_path / "lever" / "rws"

    _write_job(
        crawled_jobs_dir / "lever_rws_intern_001.json",
        {
            "job_id": "lever_rws_intern_001",
            "source": "lever",
            "source_site": "rws",
            "source_job_id": "intern_001",
            "company": "RWS",
            "title": "Machine Learning Intern",
            "location": "Remote",
            "description": "Python, PyTorch, machine learning internship work on AI data systems.",
            "min_qualifications": "",
            "preferred_qualifications": "",
            "posting_date": "2026-03-30",
            "sponsorship_info": "",
            "employment_type": "Internship",
            "source_url": "https://jobs.lever.co/rws/intern_001",
            "application_url": "https://jobs.lever.co/rws/intern_001/apply",
            "remote_status": "remote",
            "team": "TrainAI",
        },
    )

    _write_job(
        crawled_jobs_dir / "lever_rws_contract_001.json",
        {
            "job_id": "lever_rws_contract_001",
            "source": "lever",
            "source_site": "rws",
            "source_job_id": "contract_001",
            "company": "RWS",
            "title": "AI Data Specialist",
            "location": "Nairobi",
            "description": "Temporary contract work for AI data annotation and evaluation.",
            "min_qualifications": "",
            "preferred_qualifications": "",
            "posting_date": "2026-03-30",
            "sponsorship_info": "",
            "employment_type": "Temporary/Contract",
            "source_url": "https://jobs.lever.co/rws/contract_001",
            "application_url": "https://jobs.lever.co/rws/contract_001/apply",
            "remote_status": "remote",
            "team": "TrainAI",
        },
    )

    profile = {
        "degree_level": "Master's",
        "grad_date": "2027-12",
        "preferred_roles": ["Machine Learning Engineer Intern", "Applied Scientist Intern"],
        "preferred_locations": ["California", "Remote"],
        "target_industries": ["AI", "Tech"],
        "sponsorship_need": True,
        "skill_set": {"python", "pytorch", "machine learning", "data analysis"},
        "extracted_skills": ["python", "pytorch", "machine learning", "data analysis"],
    }

    jobs = load_all_job_postings(tmp_path)
    ranked = rank_jobs(profile, jobs)

    assert len(ranked) == 2
    assert {job["job_id"] for job in ranked} == {
        "lever_rws_intern_001",
        "lever_rws_contract_001",
    }
    assert ranked[0]["job_id"] == "lever_rws_intern_001"