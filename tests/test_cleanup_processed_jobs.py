from __future__ import annotations

import json
from pathlib import Path

from scripts.cleanup_processed_jobs import find_legacy_flat_duplicates, remove_legacy_flat_duplicates


def _write_job(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def test_find_legacy_flat_duplicates_returns_only_top_level_duplicates(tmp_path: Path) -> None:
    payload = {
        "job_id": "lever_rws_001",
        "source": "lever",
        "source_site": "rws",
        "source_job_id": "001",
        "company": "RWS",
        "title": "Machine Learning Intern",
        "location": "Remote",
        "description": "Example internship",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source_url": "https://jobs.lever.co/rws/001",
    }

    root_file = tmp_path / "lever_rws_001.json"
    nested_file = tmp_path / "lever" / "rws" / "lever_rws_001.json"
    unrelated_file = tmp_path / "lever" / "rws" / "lever_rws_002.json"

    _write_job(root_file, payload)
    _write_job(nested_file, payload)
    _write_job(
        unrelated_file,
        {
            **payload,
            "job_id": "lever_rws_002",
            "source_job_id": "002",
            "source_url": "https://jobs.lever.co/rws/002",
        },
    )

    duplicates = find_legacy_flat_duplicates(tmp_path)

    assert duplicates == [root_file]


def test_remove_legacy_flat_duplicates_deletes_files_when_apply_true(tmp_path: Path) -> None:
    payload = {
        "job_id": "lever_rws_001",
        "source": "lever",
        "source_site": "rws",
        "source_job_id": "001",
        "company": "RWS",
        "title": "Machine Learning Intern",
        "location": "Remote",
        "description": "Example internship",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "Internship",
        "source_url": "https://jobs.lever.co/rws/001",
    }

    root_file = tmp_path / "lever_rws_001.json"
    nested_file = tmp_path / "lever" / "rws" / "lever_rws_001.json"

    _write_job(root_file, payload)
    _write_job(nested_file, payload)

    removed = remove_legacy_flat_duplicates(tmp_path, apply=True)

    assert removed == [root_file]
    assert not root_file.exists()
    assert nested_file.exists()
