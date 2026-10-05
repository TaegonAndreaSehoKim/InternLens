from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import src.api.app as api
from src.preprocessing.corpus_health import build_corpus_health_report
from src.preprocessing.job_parser import REQUIRED_JOB_FIELDS

client = TestClient(api.app)


def write_job(directory, *, expired=False):
    directory.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    payload = {field: "" for field in REQUIRED_JOB_FIELDS} | {
        "job_id": "one", "title": "Software Engineering Intern", "company": "Example",
        "fetched_at": (now - timedelta(days=8 if expired else 1)).isoformat(),
        "expires_at": (now + timedelta(days=-1 if expired else 6)).isoformat(),
    }
    (directory / "one.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("state", ["active", "expired", "empty", "missing", "invalid"])
def test_readiness_distinguishes_liveness_and_corpus_availability(tmp_path, monkeypatch, state):
    directory = tmp_path / "jobs"
    if state in {"active", "expired"}:
        write_job(directory, expired=state == "expired")
    elif state in {"empty", "invalid"}:
        directory.mkdir()
        if state == "invalid":
            (directory / "bad.json").write_text("{}")
    monkeypatch.setattr(api, "DEFAULT_API_JOBS_DIR", str(directory))
    response = client.get("/ready")
    body = response.json()
    assert response.status_code == (200 if state == "active" else 503)
    assert body["status"] == ("ready" if state == "active" else "unavailable")
    assert body["active_job_count"] == int(state == "active")
    assert body["all_job_count"] == int(state in {"active", "expired"})
    assert "jobs_dir" not in body and str(directory) not in response.text
    assert client.get("/health").json() == {"status": "ok"}


def test_malformed_data_cannot_pass_a_zero_threshold(tmp_path):
    (tmp_path / "invalid.json").write_text("{}")
    report = build_corpus_health_report(tmp_path, min_active_jobs=0)
    assert not report["ok"]
    assert report["error"]


@pytest.mark.parametrize("expired", [True, False])
def test_recommend_returns_service_unavailable_for_expired_or_empty_data(tmp_path, expired):
    directory = tmp_path / "jobs"
    directory.mkdir()
    if expired:
        write_job(directory, expired=True)
    response = client.post("/recommend", json={
        "profile_path": "data/processed/candidate_profile_example.json", "jobs_dir": str(directory),
    })
    assert response.status_code == 503
    assert "source refresh" in response.json()["detail"]
