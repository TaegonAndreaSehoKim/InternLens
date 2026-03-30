from __future__ import annotations

import json
from pathlib import Path

from src.ingestion.greenhouse_client import (
    _build_jobs_url,
    fetch_greenhouse_jobs,
    normalize_greenhouse_job,
    save_processed_greenhouse_jobs,
    save_raw_greenhouse_snapshot,
)


def test_build_jobs_url_appends_content_true() -> None:
    # The request URL should include the board token and content=true.
    url = _build_jobs_url("acme", content=True)
    assert url == "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"


def test_build_jobs_url_without_content_flag() -> None:
    # The request URL should omit the querystring when content=False.
    url = _build_jobs_url("acme", content=False)
    assert url == "https://boards-api.greenhouse.io/v1/boards/acme/jobs"


def test_normalize_greenhouse_job_maps_core_fields() -> None:
    # Verify that the main Greenhouse fields are mapped into InternLens fields.
    job = {
        "id": 127817,
        "title": "Vault Designer",
        "updated_at": "2016-01-14T10:55:28-05:00",
        "location": {"name": "NYC"},
        "absolute_url": "https://boards.greenhouse.io/vaulttec/jobs/127817",
        "content": "This is the job description. &lt;p&gt;Any HTML included&lt;/p&gt;",
        "departments": [
            {
                "id": 13583,
                "name": "Department of Departments",
            }
        ],
        "offices": [
            {
                "id": 8787,
                "name": "New York City",
                "location": "New York, NY, United States",
            }
        ],
    }

    normalized = normalize_greenhouse_job(job, "vaulttec")

    assert normalized["job_id"] == "greenhouse_vaulttec_127817"
    assert normalized["source"] == "greenhouse"
    assert normalized["source_site"] == "vaulttec"
    assert normalized["source_job_id"] == "127817"
    assert normalized["company"] == "vaulttec"
    assert normalized["title"] == "Vault Designer"
    assert normalized["location"] == "NYC"
    assert "This is the job description." in normalized["description"]
    assert normalized["posting_date"] == "2016-01-14"
    assert normalized["source_url"] == "https://boards.greenhouse.io/vaulttec/jobs/127817"
    assert normalized["application_url"] == "https://boards.greenhouse.io/vaulttec/jobs/127817"
    assert normalized["team"] == "Department of Departments"


def test_save_raw_greenhouse_snapshot_writes_json_file(tmp_path: Path) -> None:
    # Saving a raw snapshot should create one JSON file under the raw data directory.
    jobs = [
        {"id": 127817, "title": "Vault Designer"},
        {"id": 127818, "title": "Product Engineer"},
    ]

    output_path = save_raw_greenhouse_snapshot(
        "vaulttec",
        jobs,
        project_root=tmp_path,
    )

    assert output_path.exists()
    assert output_path.suffix == ".json"
    assert "data" in str(output_path)
    assert "raw" in str(output_path)
    assert "greenhouse" in str(output_path)
    assert "vaulttec" in str(output_path)


def test_save_processed_greenhouse_jobs_writes_normalized_files(tmp_path: Path) -> None:
    # Verify that each job is normalized and saved as one processed JSON file.
    jobs = [
        {
            "id": 127817,
            "title": "Vault Designer",
            "updated_at": "2016-01-14T10:55:28-05:00",
            "location": {"name": "NYC"},
            "absolute_url": "https://boards.greenhouse.io/vaulttec/jobs/127817",
            "content": "Description one",
            "departments": [],
            "offices": [],
        },
        {
            "id": 127818,
            "title": "Product Engineer",
            "updated_at": "2016-01-15T10:55:28-05:00",
            "location": {"name": "San Francisco, CA"},
            "absolute_url": "https://boards.greenhouse.io/vaulttec/jobs/127818",
            "content": "Description two",
            "departments": [],
            "offices": [],
        },
    ]

    saved_paths = save_processed_greenhouse_jobs(
        "vaulttec",
        jobs,
        project_root=tmp_path,
    )

    assert len(saved_paths) == 2

    for path in saved_paths:
        assert path.exists()
        assert path.suffix == ".json"
        assert "greenhouse" in str(path)
        assert "vaulttec" in str(path)

    with saved_paths[0].open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["source"] == "greenhouse"
    assert payload["source_site"] == "vaulttec"
    assert payload["job_id"].startswith("greenhouse_vaulttec_")


def test_fetch_greenhouse_jobs_reads_jobs_array(monkeypatch) -> None:
    # Verify that the fetch function extracts the jobs list from the API payload.
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "jobs": [
                    {"id": 1, "title": "Role A"},
                    {"id": 2, "title": "Role B"},
                ]
            }

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url: str) -> DummyResponse:
            return DummyResponse()

    monkeypatch.setattr("src.ingestion.greenhouse_client.httpx.Client", DummyClient)

    jobs = fetch_greenhouse_jobs("vaulttec", timeout=60, limit=1, content=True)

    assert isinstance(jobs, list)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Role A"

def test_infer_remote_status_treats_in_office_as_onsite() -> None:
    # In-Office labels should not be promoted to remote just because the
    # description contains unrelated policy language.
    from src.ingestion.greenhouse_client import _infer_remote_status

    remote_status = _infer_remote_status(
        location="In-Office",
        description="Our company supports remote collaboration tools.",
        title="Software Engineer Intern (Summer 2026)",
    )

    assert remote_status == "onsite"


def test_normalize_greenhouse_job_keeps_in_office_roles_from_becoming_remote() -> None:
    # Generic in-office labels should not be treated as geographic locations.
    job = {
        "id": 999001,
        "title": "Software Engineer Intern (Summer 2026)",
        "updated_at": "2026-03-30T10:55:28-05:00",
        "location": {"name": "In-Office"},
        "absolute_url": "https://boards.greenhouse.io/example/jobs/999001",
        "content": "This internship may collaborate with remote teammates.",
        "departments": [],
        "offices": [],
    }

    normalized = normalize_greenhouse_job(job, "example")

    assert normalized["location"] == ""
    assert normalized["remote_status"] == "onsite"
