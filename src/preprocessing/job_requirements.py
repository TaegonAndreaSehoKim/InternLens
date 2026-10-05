"""Conservative, source-independent interpretation of posting requirements."""

from __future__ import annotations

import re
from typing import Any, Dict


PH_D_PATTERN = re.compile(r"\b(?:ph\.?\s*d\.?|doctorate|doctoral|dphil)\b", re.I)
ALTERNATIVE_DEGREE_PATTERN = re.compile(r"\b(?:bachelor(?:'s)?|master(?:'s)?|bs|ms|msc|bsc|undergraduate)\b", re.I)
OPTIONAL_DEGREE_PATTERN = re.compile(r"\b(?:preferred|optional|not required|not necessary|nice to have|bonus|welcome|encouraged|desirable|do not need)\b|\ba plus\b", re.I)
REQUIRED_DEGREE_PATTERN = re.compile(r"\b(?:must|required|requires?|requirement|minimum|qualifications|only|enrolled|pursuing|candidates|students|program)\b", re.I)
UNAVAILABLE_SPONSORSHIP_PATTERNS = [
    r"\bno\s+(?:(?:visa|immigration|employment|employer|work(?:\s+visa)?)\s+)?sponsorship\b(?!\s+(?:is\s+)?(?:required|needed|necessary|restrictions|limitations)\b)",
    r"\bsponsorship\s+(?:is\s+|will\s+be\s+)?(?:not\s+(?:available|offered|provided|supported)|unavailable)\b",
    r"\b(?:cannot|can't|do\s+not|don't|does\s+not|doesn't|will\s+not|won't|unable\s+to|not\s+able\s+to)\s+(?:currently\s+)?(?:provide|offer|support)\s+(?:(?:visa|immigration|employment|employer|work(?:\s+visa)?)\s+)?sponsorship\b",
    r"\b(?:cannot|can't|do\s+not|don't|will\s+not|won't|unable\s+to|not\s+able\s+to)\s+sponsor\b",
    r"(?<!with or )\bwithout\s+(?:current\s+or\s+future\s+)?(?:(?:visa|employment|employer|work(?:\s+visa)?)\s+)?sponsorship\b",
]


def _clauses(text: str) -> list[str]:
    # Normalize dotted degree names before splitting at sentence boundaries.
    normalized = re.sub(r"\bph\.?\s*d\.?", "PhD", str(text), flags=re.I).replace("’", "'")
    return [clause.strip() for clause in re.split(r"[\n;.!?]+", normalized) if clause.strip()]


def is_phd_degree(text: str) -> bool:
    return bool(PH_D_PATTERN.search(text))


def _required_phd_clause(clause: str, *, structured: bool) -> bool:
    if not is_phd_degree(clause) or OPTIONAL_DEGREE_PATTERN.search(clause):
        return False
    if ALTERNATIVE_DEGREE_PATTERN.search(clause) and re.search(r"\bor\b|/|\b(?:accepted|eligible)\b", clause, re.I):
        return False
    return structured or bool(REQUIRED_DEGREE_PATTERN.search(clause))


def requires_phd(job: Dict[str, Any]) -> bool:
    # Titles and minimum qualifications identify the target degree. A preferred
    # qualification or an incidental mention in the description does not.
    for field in ("title", "min_qualifications"):
        if any(_required_phd_clause(clause, structured=True) for clause in _clauses(job.get(field, ""))):
            return True
    required_description = re.split(r"\bpreferred qualifications\b", str(job.get("description", "")), flags=re.I)[0]
    return any(_required_phd_clause(clause, structured=False) for clause in _clauses(required_description))


def extract_sponsorship_info(text: str) -> str:
    """Keep explicit negative policy evidence; leave unknown policy empty."""
    for clause in _clauses(text):
        if any(re.search(pattern, clause, re.I) for pattern in UNAVAILABLE_SPONSORSHIP_PATTERNS):
            return f"No sponsorship: {clause[:600]}"
    return ""


def sponsorship_is_unavailable(job: Dict[str, Any]) -> bool:
    return any(extract_sponsorship_info(str(job.get(field, ""))) for field in (
        "sponsorship_info", "description", "min_qualifications", "preferred_qualifications",
    ))
