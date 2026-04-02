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


def test_load_all_job_postings_prefers_nested_job_over_legacy_flat_duplicate(tmp_path: Path) -> None:
    # If the same job_id exists in both the old flat layout and the nested
    # source/site layout, keep the nested version.
    _write_job(
        tmp_path / "lever_rws_001.json",
        "lever_rws_001",
        "legacy flat title",
    )
    _write_job(
        tmp_path / "lever" / "rws" / "lever_rws_001.json",
        "lever_rws_001",
        "nested canonical title",
    )

    jobs = load_all_job_postings(tmp_path)

    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "lever_rws_001"
    assert jobs[0]["title"] == "nested canonical title"


def test_load_all_job_postings_suppresses_duplicate_content_by_source_url(tmp_path: Path) -> None:
    # If two processed jobs point to the same source URL, keep only the richer one.
    _write_job(
        tmp_path / "greenhouse" / "cloudflare" / "job_a.json",
        "greenhouse_cloudflare_001",
        "consultant, developer platform",
    )
    _write_job(
        tmp_path / "greenhouse" / "cloudflare" / "job_b.json",
        "greenhouse_cloudflare_002",
        "consultant, developer platform",
    )

    first_path = tmp_path / "greenhouse" / "cloudflare" / "job_a.json"
    second_path = tmp_path / "greenhouse" / "cloudflare" / "job_b.json"

    first_payload = json.loads(first_path.read_text(encoding="utf-8"))
    second_payload = json.loads(second_path.read_text(encoding="utf-8"))

    first_payload["source"] = "greenhouse"
    first_payload["source_site"] = "cloudflare"
    first_payload["company"] = "cloudflare"
    first_payload["location"] = "Lisbon, Portugal"
    first_payload["source_url"] = "https://boards.greenhouse.io/cloudflare/jobs/123"
    first_payload["description"] = "short"

    second_payload["source"] = "greenhouse"
    second_payload["source_site"] = "cloudflare"
    second_payload["company"] = "cloudflare"
    second_payload["location"] = "Lisbon, Portugal"
    second_payload["source_url"] = "https://boards.greenhouse.io/cloudflare/jobs/123"
    second_payload["description"] = "This is the richer duplicate record with more content."
    second_payload["application_url"] = "https://boards.greenhouse.io/cloudflare/jobs/123/apply"

    first_path.write_text(json.dumps(first_payload, indent=2), encoding="utf-8")
    second_path.write_text(json.dumps(second_payload, indent=2), encoding="utf-8")

    jobs = load_all_job_postings(tmp_path)

    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "greenhouse_cloudflare_002"


def test_load_all_job_postings_suppresses_near_identical_title_duplicates(tmp_path: Path) -> None:
    # If title/company/location strongly indicate the same posting, keep one record.
    first_path = tmp_path / "greenhouse" / "waymo" / "job_a.json"
    second_path = tmp_path / "greenhouse" / "waymo" / "job_b.json"

    _write_job(first_path, "greenhouse_waymo_001", "Software Quality Ops Scenarios Specialist")
    _write_job(second_path, "greenhouse_waymo_002", "Software Quality Operations Scenarios Specialist")

    first_payload = json.loads(first_path.read_text(encoding="utf-8"))
    second_payload = json.loads(second_path.read_text(encoding="utf-8"))

    first_payload["source"] = "greenhouse"
    first_payload["source_site"] = "waymo"
    first_payload["company"] = "waymo"
    first_payload["location"] = "Mountain View, CA"
    first_payload["description"] = "short"

    second_payload["source"] = "greenhouse"
    second_payload["source_site"] = "waymo"
    second_payload["company"] = "waymo"
    second_payload["location"] = "Mountain View, CA"
    second_payload["description"] = "This duplicate has more descriptive detail and metadata."
    second_payload["team"] = "Operations"

    first_path.write_text(json.dumps(first_payload, indent=2), encoding="utf-8")
    second_path.write_text(json.dumps(second_payload, indent=2), encoding="utf-8")

    jobs = load_all_job_postings(tmp_path)

    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "greenhouse_waymo_002"
