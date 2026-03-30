from src.ingestion.lever_client import _build_request_url, fetch_lever_postings
from pathlib import Path
from src.ingestion.lever_client import save_raw_lever_snapshot

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