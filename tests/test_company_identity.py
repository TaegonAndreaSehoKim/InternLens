from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import scripts.fetch_greenhouse_registry as greenhouse_registry
import scripts.fetch_lever_registry as lever_registry
import scripts.fetch_greenhouse_jobs as greenhouse_cli
import scripts.fetch_lever_jobs as lever_cli
from src.api.app import app
from src.ingestion.greenhouse_client import normalize_greenhouse_job
from src.ingestion.lever_client import normalize_lever_posting
from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import load_candidate_profile
from src.ranking.baseline_scorer import score_job

LEVER_POSTING = {"id": "one", "text": "Software Engineering Intern", "descriptionPlain": "Build Python services.", "categories": {"department": "Engineering", "team": "Platform", "commitment": "Internship", "location": "Remote"}}
GREENHOUSE_JOB = {"id": "one", "title": "Software Engineering Intern", "content": "Build Python services.", "departments": [{"name": "Engineering"}], "location": {"name": "Remote"}}


def test_lever_department_is_not_used_as_the_company():
    posting = normalize_lever_posting(LEVER_POSTING, "acme")
    assert posting["company"] == "acme"
    assert posting["department"] == "Engineering"
    assert posting["team"] == "Platform"


def test_lever_team_falls_back_to_department_without_changing_company():
    posting = normalize_lever_posting(LEVER_POSTING | {"categories": {"department": "Engineering"}}, "acme", company_name="Acme Holdings")
    assert posting["company"] == "Acme Holdings"
    assert posting["team"] == "Engineering"


@pytest.mark.parametrize("normalizer,payload", [(normalize_lever_posting, LEVER_POSTING), (normalize_greenhouse_job, GREENHOUSE_JOB)])
def test_verified_company_name_does_not_change_source_identifiers(normalizer, payload):
    posting = normalizer(payload, "acme", company_name="  Acme Holdings  ")
    fallback = normalizer(payload, "acme", company_name="  ")
    assert posting["company"] == "Acme Holdings"
    assert fallback["company"] == "acme"
    assert posting["job_id"] == fallback["job_id"]
    assert posting["source_site"] == "acme"
    assert posting["department"] == "Engineering"


@pytest.mark.parametrize("module,source_key,fetch_name,payload", [
    (lever_registry, "site_name", "fetch_lever_postings", LEVER_POSTING),
    (greenhouse_registry, "board_token", "fetch_greenhouse_jobs", GREENHOUSE_JOB),
])
def test_registry_company_identity_survives_storage_ranking_and_detail_api(tmp_path, monkeypatch, module, source_key, fetch_name, payload):
    registry = tmp_path / "sources.json"
    registry.write_text(json.dumps([{source_key: "acme", "company_name": "Acme Holdings", "active": True}]))
    monkeypatch.setattr(module, fetch_name, lambda *args, **kwargs: [payload])
    kwargs = {"internship_only": False} if module is greenhouse_registry else {}
    summary = module.run_registry_fetch(registry_path=registry, timeout=1, limit=None, only_active=True, project_root=tmp_path, **kwargs)
    assert summary["total_processed_jobs"] == 1
    jobs_dir = tmp_path / "data/processed/jobs"
    posting = load_all_job_postings(jobs_dir)[0]
    assert posting["company"] == "Acme Holdings"
    profile = load_candidate_profile("data/processed/candidate_profile_example.json")
    assert score_job(profile, posting)["company"] == "Acme Holdings"
    response = TestClient(app).get(f"/jobs/{posting['job_id']}", params={"jobs_dir": str(jobs_dir)})
    assert response.status_code == 200
    assert response.json()["company"] == "Acme Holdings"
    assert response.json()["department"] == "Engineering"


@pytest.mark.parametrize("module,flag,fetch_name,payload", [
    (lever_cli, "--site-name", "fetch_lever_postings", LEVER_POSTING),
    (greenhouse_cli, "--board-token", "fetch_greenhouse_jobs", GREENHOUSE_JOB),
])
def test_single_source_cli_accepts_verified_company_name(tmp_path, monkeypatch, module, flag, fetch_name, payload):
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, fetch_name, lambda *args, **kwargs: [payload])
    monkeypatch.setattr("sys.argv", ["fetch", flag, "acme", "--company-name", "Acme Holdings"])
    module.main()
    assert load_all_job_postings(tmp_path / "data/processed/jobs")[0]["company"] == "Acme Holdings"
