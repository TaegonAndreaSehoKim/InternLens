from src.ingestion.lever_client import _build_request_url, fetch_lever_postings
from pathlib import Path
from src.ingestion.lever_client import (
    _build_request_url,
    fetch_lever_postings,
    normalize_lever_posting,
    save_processed_lever_postings,
    save_raw_lever_snapshot,
)

def test_build_request_url_appends_mode_json() -> None:
    url = _build_request_url("rws")
    assert url == "https://api.lever.co/v0/postings/rws?mode=json"


def test_fetch_lever_postings_returns_list() -> None:
    jobs = fetch_lever_postings("rws", limit=3, timeout=60)

    assert isinstance(jobs, list)
    assert len(jobs) <= 3


def test_fetch_lever_postings_items_are_dicts_when_present() -> None:
    jobs = fetch_lever_postings("rws", limit=3, timeout=60)

    if jobs:
        assert isinstance(jobs[0], dict)
        assert "id" in jobs[0]

def test_save_raw_lever_snapshot_writes_json_file(tmp_path: Path) -> None:
    postings = [
        {"id": "job_123", "text": "Example Job"},
        {"id": "job_456", "text": "Another Job"},
    ]

    output_path = save_raw_lever_snapshot(
        "rws",
        postings,
        project_root=tmp_path,
    )

    assert output_path.exists()
    assert output_path.suffix == ".json"
    assert "data" in str(output_path)
    assert "raw" in str(output_path)
    assert "lever" in str(output_path)
    assert "rws" in str(output_path)

def test_normalize_lever_posting_maps_core_fields() -> None:
    # Verify that the main Lever fields are mapped into InternLens fields.
    posting = {
        "id": "abc123",
        "text": "AI Data Specialist",
        "descriptionPlain": "Remote AI data work.",
        "createdAt": 1741982801320,
        "hostedUrl": "https://jobs.lever.co/example/abc123",
        "applyUrl": "https://jobs.lever.co/example/abc123/apply",
        "workplaceType": "remote",
        "categories": {
            "commitment": "Temporary/Contract",
            "department": "RWS",
            "location": "Florida",
            "team": "TrainAI",
        },
    }

    normalized = normalize_lever_posting(posting, "rws")

    assert normalized["job_id"] == "lever_rws_abc123"
    assert normalized["source"] == "lever"
    assert normalized["source_site"] == "rws"
    assert normalized["source_job_id"] == "abc123"
    assert normalized["company"] == "RWS"
    assert normalized["title"] == "AI Data Specialist"
    assert normalized["location"] == "Florida"
    assert normalized["description"] == "Remote AI data work."
    assert normalized["employment_type"] == "Temporary/Contract"
    assert normalized["remote_status"] == "remote"
    assert normalized["source_url"] == "https://jobs.lever.co/example/abc123"
    assert normalized["application_url"] == "https://jobs.lever.co/example/abc123/apply"
    assert normalized["team"] == "TrainAI"

from pathlib import Path
import json


def test_save_processed_lever_postings_writes_normalized_files(tmp_path: Path) -> None:
    # Verify that each posting is normalized and saved as one processed JSON file.
    postings = [
        {
            "id": "abc123",
            "text": "AI Data Specialist",
            "descriptionPlain": "Remote AI data work.",
            "createdAt": 1741982801320,
            "hostedUrl": "https://jobs.lever.co/example/abc123",
            "applyUrl": "https://jobs.lever.co/example/abc123/apply",
            "workplaceType": "remote",
            "categories": {
                "commitment": "Temporary/Contract",
                "department": "RWS",
                "location": "Florida",
                "team": "TrainAI",
            },
        },
        {
            "id": "def456",
            "text": "ML Annotator",
            "descriptionPlain": "Annotation work.",
            "createdAt": 1741982801320,
            "hostedUrl": "https://jobs.lever.co/example/def456",
            "applyUrl": "https://jobs.lever.co/example/def456/apply",
            "workplaceType": "remote",
            "categories": {
                "commitment": "Part-time",
                "department": "RWS",
                "location": "Alabama",
                "team": "TrainAI",
            },
        },
    ]

    saved_paths = save_processed_lever_postings(
        "rws",
        postings,
        project_root=tmp_path,
    )

    assert len(saved_paths) == 2

    for path in saved_paths:
        assert path.exists()
        assert path.suffix == ".json"
        assert "lever" in str(path)
        assert "rws" in str(path)

    with saved_paths[0].open("r", encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["source"] == "lever"
    assert payload["source_site"] == "rws"
    assert payload["job_id"].startswith("lever_rws_")