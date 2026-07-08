from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import scripts.check_corpus_health as health_script


def _write_job(path: Path, job_id: str, expires_at: str) -> None:
    payload = {
        "job_id": job_id,
        "company": "example",
        "title": f"{job_id} intern",
        "location": "remote",
        "description": "internship role",
        "min_qualifications": "python",
        "preferred_qualifications": "",
        "posting_date": "2026-05-01",
        "sponsorship_info": "",
        "employment_type": "internship",
        "source": "manual",
        "fetched_at": "2026-05-12T00:00:00+00:00",
        "expires_at": expires_at,
        "freshness_days": 7,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_corpus_health_report_counts_active_jobs(tmp_path: Path) -> None:
    jobs_dir = tmp_path / "jobs"
    _write_job(jobs_dir / "fresh.json", "fresh_job", "2026-05-20T00:00:00+00:00")
    _write_job(jobs_dir / "expired.json", "expired_job", "2026-05-01T00:00:00+00:00")

    report = health_script.build_corpus_health_report(
        jobs_dir,
        min_active_jobs=1,
        now=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )

    assert report["ok"] is True
    assert report["active_job_count"] == 1
    assert report["all_job_count"] == 2
    assert report["expired_or_filtered_job_count"] == 1
    assert report["latest_expires_at"] == "2026-05-20T00:00:00+00:00"


def test_build_corpus_health_report_fails_expired_only_corpus(tmp_path: Path) -> None:
    jobs_dir = tmp_path / "jobs"
    _write_job(jobs_dir / "expired.json", "expired_job", "2026-05-01T00:00:00+00:00")

    report = health_script.build_corpus_health_report(
        jobs_dir,
        min_active_jobs=1,
        now=datetime(2026, 5, 12, tzinfo=timezone.utc),
    )

    assert report["ok"] is False
    assert report["active_job_count"] == 0
    assert report["all_job_count"] == 1
