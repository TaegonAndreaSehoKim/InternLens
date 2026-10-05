from datetime import datetime, timezone
import json

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.ingestion.greenhouse_client import normalize_greenhouse_job
from src.ingestion.lever_client import normalize_lever_posting
from src.preprocessing.job_parser import load_all_job_postings
from src.ranking.baseline_scorer import score_job


NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)
PROFILE = {
    "degree_level": "Master's", "major": "computer science", "grad_date": "",
    "preferred_roles": ["Software Engineering Intern"], "preferred_locations": [],
    "sponsorship_need": True, "skill_set": {"python"}, "extracted_skills": ["Python"],
}


def job(**overrides):
    return {
        "job_id": "example", "company": "Example", "title": "Software Engineering Intern",
        "location": "Remote", "description": "Build Python software during an internship.",
        "min_qualifications": "Python", "preferred_qualifications": "", "posting_date": "2026-10-03",
        "sponsorship_info": "", "employment_type": "Internship", "source": "manual", **overrides,
    }


@pytest.mark.parametrize("field,text", [
    ("preferred_qualifications", "PhD in computer science preferred"),
    ("description", "A Ph.D. is preferred but not required."),
    ("description", "Bachelor, Master or PhD students welcome."),
    ("min_qualifications", "Currently pursuing a master's or Ph.D. degree."),
    ("min_qualifications", "A PhD is not required."),
    ("title", "MS/PhD Software Engineering Intern"),
    ("description", "Our team includes PhD researchers."),
    ("description", "Preferred qualifications: PhD in computer science."),
])
def test_optional_or_alternative_phd_does_not_block(field, text):
    result = score_job(PROFILE, job(**{field: text}), now=NOW)
    assert "This role appears to require a PhD" not in result["blocking_issues"]
    assert result["action_label"] != "Skip"


@pytest.mark.parametrize("field,text", [
    ("title", "PhD Software Engineering Intern"),
    ("min_qualifications", "Ph.D. in computer science"),
    ("description", "You must be enrolled in a doctoral program."),
    ("description", "This internship is for PhD candidates."),
    ("description", "A PhD is required. Preferred qualifications: Python."),
])
def test_required_phd_still_blocks_non_doctoral_candidates(field, text):
    posting = job(**{field: text})
    result = score_job(PROFILE, posting, now=NOW)
    assert "This role appears to require a PhD" in result["blocking_issues"]
    assert result["action_label"] == "Skip"
    doctoral = {**PROFILE, "degree_level": "Ph.D."}
    assert "This role appears to require a PhD" not in score_job(doctoral, posting, now=NOW)["blocking_issues"]


@pytest.mark.parametrize("text", [
    "No sponsorship is available for this role.",
    "Visa sponsorship is not available.",
    "We cannot provide visa sponsorship.",
    "We are unable to sponsor applicants.",
    "We do not offer employment sponsorship.",
    "Candidates must be authorized to work without current or future sponsorship.",
])
@pytest.mark.parametrize("source", ["greenhouse", "lever"])
def test_ats_sponsorship_evidence_survives_loading_and_blocks_ranking(tmp_path, source, text):
    description = f"Software engineering internship with Python. {text}"
    if source == "greenhouse":
        posting = normalize_greenhouse_job({"id": 1, "title": "Software Engineering Intern", "content": description}, "example", fetched_at=NOW)
    else:
        posting = normalize_lever_posting({"id": "1", "text": "Software Engineering Intern", "descriptionPlain": description}, "example", fetched_at=NOW)
    assert text.rstrip(".").lower() in posting["sponsorship_info"].lower()
    (tmp_path / "job.json").write_text(json.dumps(posting), encoding="utf-8")
    loaded = load_all_job_postings(tmp_path, now=NOW)[0]
    result = score_job(PROFILE, loaded, now=NOW)
    assert "Sponsorship is not available for this role" in result["blocking_issues"]
    assert result["action_label"] == "Skip"
    assert "Sponsorship is not available for this role" not in score_job({**PROFILE, "sponsorship_need": False}, loaded, now=NOW)["blocking_issues"]


@pytest.mark.parametrize("text", ["Visa sponsorship is available.", "No sponsorship required.", "Candidates with or without sponsorship needs are welcome.", ""])
def test_unknown_or_non_restrictive_sponsorship_does_not_block(text):
    result = score_job(PROFILE, job(description=text, sponsorship_info=text), now=NOW)
    assert "Sponsorship is not available for this role" not in result["blocking_issues"]


def test_old_processed_records_get_sponsorship_evidence_without_regenerating_files(tmp_path):
    path = tmp_path / "job.json"
    original = json.dumps(job(description="Python internship. Visa sponsorship is not available."))
    path.write_text(original, encoding="utf-8")
    loaded = load_all_job_postings(tmp_path, now=NOW)[0]
    assert "not available" in loaded["sponsorship_info"]
    assert path.read_text(encoding="utf-8") == original
    assert "Sponsorship is not available for this role" in score_job(PROFILE, loaded, now=NOW)["blocking_issues"]


def test_refreshed_old_posting_does_not_receive_new_posting_freshness():
    old = normalize_greenhouse_job({"id": 1, "title": "Software Engineering Intern", "content": "Python internship", "updated_at": "2020-01-01T00:00:00Z"}, "example", fetched_at=NOW)
    recent = normalize_greenhouse_job({"id": 2, "title": "Software Engineering Intern", "content": "Python internship", "updated_at": "2026-10-03T00:00:00Z"}, "example", fetched_at=NOW)
    assert old["freshness_days"] == recent["freshness_days"] == 7
    assert score_job(PROFILE, old, now=NOW)["component_scores"]["freshness_score"] == 0
    assert score_job(PROFILE, recent, now=NOW)["component_scores"]["freshness_score"] == 1
    assert score_job(PROFILE, old, now=datetime(2020, 1, 2))["component_scores"]["freshness_score"] == 1


def test_unknown_posting_age_is_neutral_despite_a_short_ttl():
    result = score_job(PROFILE, job(posting_date="", freshness_days=1), now=NOW)
    assert result["component_scores"]["freshness_score"] == 0.5


@pytest.mark.parametrize("source", ["greenhouse", "lever"])
@pytest.mark.parametrize("description,blocked", [
    ("Minimum qualifications: currently pursuing a Ph.D. degree.", True),
    ("Minimum qualifications: currently pursuing a master's or Ph.D. degree.", False),
    ("Preferred qualifications: PhD in computer science.", False),
])
def test_ats_degree_requirements_survive_loading_without_blocking_alternatives(tmp_path, source, description, blocked):
    description = f"Python software engineering internship. {description}"
    if source == "greenhouse":
        posting = normalize_greenhouse_job({"id": 1, "title": "Software Engineering Intern", "content": description}, "example", fetched_at=NOW)
    else:
        posting = normalize_lever_posting({"id": "1", "text": "Software Engineering Intern", "descriptionPlain": description}, "example", fetched_at=NOW)
    (tmp_path / "job.json").write_text(json.dumps(posting), encoding="utf-8")
    result = score_job(PROFILE, load_all_job_postings(tmp_path, now=NOW)[0], now=NOW)
    assert ("This role appears to require a PhD" in result["blocking_issues"]) is blocked


def test_detail_and_recommendation_api_agree_about_degree_and_sponsorship(tmp_path):
    posting = job(description="Python internship. A PhD is preferred but not required. Visa sponsorship is not available.")
    (tmp_path / "job.json").write_text(json.dumps(posting), encoding="utf-8")
    client = TestClient(app)
    detail = client.get("/jobs/example", params={"jobs_dir": str(tmp_path)}).json()
    assert "This posting may require a PhD" not in detail["possible_blockers"]
    assert "This posting states sponsorship is not available" in detail["possible_blockers"]
    profile = {**PROFILE, "profile_id": "example", "resume_text": "Python projects"}
    profile.pop("skill_set")
    response = client.post("/recommend", json={"profile_data": profile, "jobs_dir": str(tmp_path), "include_debug": True})
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["blocking_issues"] == ["Sponsorship is not available for this role"]
