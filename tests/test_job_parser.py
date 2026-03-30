from __future__ import annotations

import json
from pathlib import Path

from src.preprocessing.job_parser import load_all_job_postings


def _write_job(path: Path, job_id: str, title: str) -> None:
    # Write one minimal valid job posting JSON file for parser tests.
    payload = {
        "job_id": job_id,
        "company": "example",
        "title": title,
        "location": "remote",
        "description": "example description",
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": "2026-03-30",
        "sponsorship_info": "",
        "employment_type": "internship",
        "source": "manual",
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def test_load_all_job_postings_reads_top_level_json_files(tmp_path: Path) -> None:
    # The parser should still support the original flat directory layout.
    _write_job(tmp_path / "job_001.json", "job_001", "applied scientist intern")
    _write_job(tmp_path / "job_002.json", "job_002", "ml engineer intern")

    jobs = load_all_job_postings(tmp_path)

    assert len(jobs) == 2
    assert {job["job_id"] for job in jobs} == {"job_001", "job_002"}


def test_load_all_job_postings_reads_nested_json_files(tmp_path: Path) -> None:
    # The parser should also load crawled jobs saved under nested source/site folders.
    _write_job(
        tmp_path / "lever" / "rws" / "lever_rws_001.json",
        "lever_rws_001",
        "ai data specialist",
    )
    _write_job(
        tmp_path / "lever" / "rws" / "lever_rws_002.json",
        "lever_rws_002",
        "ml annotator",
    )

    jobs = load_all_job_postings(tmp_path)

    assert len(jobs) == 2
    assert {job["job_id"] for job in jobs} == {"lever_rws_001", "lever_rws_002"}