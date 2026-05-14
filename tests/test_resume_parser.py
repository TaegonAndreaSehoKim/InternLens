from __future__ import annotations

import pytest

from src.preprocessing.resume_parser import extract_resume_text
from src.preprocessing.resume_parser import parse_resume_text


def test_parse_resume_text_extracts_profile_signals() -> None:
    resume_text = """
    Jane Candidate
    Education
    Bachelor of Science in Computer Science, expected graduation May 2027.
    Skills
    Python, SQL, Docker, AWS
    Projects
    Built React and FastAPI applications.
    Interested in software engineering, backend services, and AI products.
    Open to Remote roles in New York.
    """

    parsed = parse_resume_text(resume_text)

    assert parsed["degree_level"] == "Bachelor's"
    assert parsed["grad_date"] == "2027-05"
    assert parsed["major"] == "Computer Science"
    assert "Computer Science" in parsed["majors"]
    assert "Python" in parsed["extracted_skills"]
    assert "AWS" in parsed["extracted_skills"]
    assert "Software Engineering Intern" in parsed["preferred_roles"]
    assert "AI" in parsed["target_industries"]
    assert "Remote" in parsed["preferred_locations"]
    assert parsed["suggestions"]["extracted_skills"][0]["confidence"] == "high"
    assert "Skills:" in parsed["suggestions"]["extracted_skills"][0]["evidence"][0]
    assert any(
        item["field"] == "grad_date" and item["confidence"] == "high"
        for item in parsed["suggestions"]["education"]
    )
    assert parsed["warnings"] == []


def test_parse_resume_text_warns_when_core_signals_are_missing() -> None:
    parsed = parse_resume_text("Volunteer coordinator with community event experience.")

    assert parsed["major"] == "Other"
    assert parsed["extracted_skills"] == []
    assert parsed["preferred_roles"] == []
    assert parsed["warnings"]


def test_extract_resume_text_rejects_unsupported_file_type() -> None:
    with pytest.raises(ValueError, match="Unsupported resume file type"):
        extract_resume_text("resume.png", b"not text")
