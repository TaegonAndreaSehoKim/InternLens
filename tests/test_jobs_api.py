from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def _write_job(path: Path, payload: dict) -> None:
    # Write one processed job JSON file for jobs API tests.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def test_get_job_endpoint_returns_nested_crawled_job_details(tmp_path: Path) -> None:
    # Verify that /jobs/{id} can read a processed job from a nested crawled-jobs directory.
    job_path = tmp_path / "lever" / "rws" / "lever_rws_001.json"
    _write_job(
        job_path,
        {
            "job_id": "lever_rws_001",
            "source": "lever",
            "source_site": "rws",
            "source_job_id": "001",
            "company": "RWS",
            "title": "Machine Learning Intern",
            "location": "Remote",
            "description": "Example internship description",
            "min_qualifications": "",
            "preferred_qualifications": "",
            "posting_date": "2026-03-30",
            "sponsorship_info": "",
            "employment_type": "Internship",
            "source_url": "https://jobs.lever.co/rws/001",
            "application_url": "https://jobs.lever.co/rws/001/apply",
            "remote_status": "remote",
            "team": "TrainAI",
        },
    )

    response = client.get(
        "/jobs/lever_rws_001",
        params={"jobs_dir": str(tmp_path)},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["job_id"] == "lever_rws_001"
    assert body["source"] == "lever"
    assert body["source_site"] == "rws"
    assert body["title"] == "Machine Learning Intern"
    assert body["application_url"] == "https://jobs.lever.co/rws/001/apply"


def test_get_job_endpoint_returns_404_for_missing_job(tmp_path: Path) -> None:
    # Verify that /jobs/{id} returns a clean 404 when the requested job is missing.
    job_path = tmp_path / "lever" / "rws" / "lever_rws_001.json"
    _write_job(
        job_path,
        {
            "job_id": "lever_rws_001",
            "source": "lever",
            "source_site": "rws",
            "source_job_id": "001",
            "company": "RWS",
            "title": "Machine Learning Intern",
            "location": "Remote",
            "description": "Example internship description",
            "min_qualifications": "",
            "preferred_qualifications": "",
            "posting_date": "2026-03-30",
            "sponsorship_info": "",
            "employment_type": "Internship",
            "source_url": "https://jobs.lever.co/rws/001",
            "application_url": "https://jobs.lever.co/rws/001/apply",
            "remote_status": "remote",
            "team": "TrainAI",
        },
    )

    response = client.get(
        "/jobs/does_not_exist",
        params={"jobs_dir": str(tmp_path)},
    )
    body = response.json()

    assert response.status_code == 404
    assert "Job not found" in body["detail"]