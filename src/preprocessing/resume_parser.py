from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


MAX_RESUME_BYTES = 5 * 1024 * 1024

SKILL_KEYWORDS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "c++",
    "c#",
    "go",
    "rust",
    "r",
    "sql",
    "swift",
    "kotlin",
    "scala",
    "matlab",
    "bash",
    "machine learning",
    "deep learning",
    "generative ai",
    "natural language processing",
    "computer vision",
    "recommender systems",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "pandas",
    "numpy",
    "statistics",
    "experiment design",
    "a/b testing",
    "data visualization",
    "etl",
    "feature engineering",
    "react",
    "node.js",
    "fastapi",
    "django",
    "flask",
    "rest apis",
    "graphql",
    "html",
    "css",
    "aws",
    "azure",
    "google cloud",
    "docker",
    "kubernetes",
    "linux",
    "git",
    "ci/cd",
    "terraform",
    "databricks",
    "snowflake",
    "airflow",
    "spark",
    "postgresql",
    "mongodb",
    "redis",
    "tableau",
    "power bi",
    "excel",
    "salesforce",
    "market research",
    "financial modeling",
    "operations",
    "project management",
    "program management",
    "business strategy",
    "competitive analysis",
    "accounting",
    "corporate finance",
    "valuation",
    "risk management",
    "audit",
    "tax",
    "user research",
    "figma",
    "wireframing",
    "prototyping",
    "seo",
    "email marketing",
    "content strategy",
    "copywriting",
    "brand strategy",
    "social media strategy",
    "clinical research",
    "biology",
    "chemistry",
    "bioinformatics",
    "biostatistics",
    "epidemiology",
    "policy analysis",
    "legal research",
    "writing",
    "editing",
    "public speaking",
    "supply chain",
    "logistics",
    "procurement",
]

MAJOR_KEYWORDS = [
    "computer science",
    "software engineering",
    "computer engineering",
    "data science",
    "artificial intelligence",
    "machine learning",
    "information systems",
    "information technology",
    "cybersecurity",
    "electrical engineering",
    "mechanical engineering",
    "civil engineering",
    "industrial engineering",
    "aerospace engineering",
    "biomedical engineering",
    "chemical engineering",
    "environmental engineering",
    "mathematics",
    "statistics",
    "physics",
    "chemistry",
    "biology",
    "biochemistry",
    "bioinformatics",
    "public health",
    "business administration",
    "marketing",
    "finance",
    "accounting",
    "economics",
    "operations management",
    "supply chain management",
    "human resources",
    "psychology",
    "political science",
    "public policy",
    "law",
    "education",
    "communications",
    "journalism",
    "graphic design",
    "product design",
    "ux design",
    "environmental science",
    "sustainability",
]

ROLE_RULES: List[Tuple[str, List[str]]] = [
    ("Machine Learning Engineer Intern", ["machine learning", "deep learning", "pytorch", "tensorflow"]),
    ("Data Science Intern", ["data science", "statistics", "pandas", "numpy", "data analysis"]),
    ("Data Engineering Intern", ["etl", "airflow", "spark", "sql", "databricks", "snowflake"]),
    ("Software Engineering Intern", ["software engineering", "python", "java", "javascript", "typescript", "c++", "git"]),
    ("Backend Engineering Intern", ["backend", "fastapi", "django", "flask", "node.js", "postgresql"]),
    ("Frontend Engineering Intern", ["frontend", "react", "javascript", "typescript", "html", "css"]),
    ("Cybersecurity Intern", ["cybersecurity", "security", "threat", "risk management"]),
    ("Product Design Intern", ["figma", "wireframing", "prototyping", "user research"]),
    ("Marketing Intern", ["marketing", "seo", "content strategy", "copywriting", "brand strategy"]),
    ("Finance Intern", ["finance", "financial modeling", "valuation", "corporate finance"]),
    ("Business Analyst Intern", ["business strategy", "competitive analysis", "operations", "analytics"]),
    ("Supply Chain Intern", ["supply chain", "logistics", "procurement"]),
    ("Policy Intern", ["policy analysis", "public policy", "government affairs"]),
    ("Clinical Research Intern", ["clinical research", "biology", "public health", "epidemiology"]),
]

INDUSTRY_RULES: List[Tuple[str, List[str]]] = [
    ("AI", ["ai", "machine learning", "deep learning", "generative ai", "artificial intelligence"]),
    ("Enterprise Software", ["software", "developer", "backend", "frontend", "cloud"]),
    ("Data Infrastructure", ["data engineering", "etl", "spark", "airflow", "snowflake"]),
    ("Cybersecurity", ["cybersecurity", "security", "threat"]),
    ("Fintech", ["finance", "banking", "payments", "risk"]),
    ("Healthcare", ["clinical", "healthcare", "public health", "biology"]),
    ("Biotech", ["biology", "bioinformatics", "biotech", "lab"]),
    ("Advertising", ["marketing", "brand", "content", "social media"]),
    ("Consulting", ["strategy", "operations", "business analyst"]),
    ("Public Policy", ["policy", "government", "public affairs"]),
    ("Supply Chain", ["supply chain", "logistics", "procurement"]),
    ("Education", ["education", "curriculum", "instructional"]),
    ("Climate Tech", ["sustainability", "climate", "environmental"]),
]

LOCATION_KEYWORDS = [
    "remote",
    "california",
    "new york",
    "texas",
    "washington",
    "massachusetts",
    "georgia",
    "seattle",
    "san francisco",
    "san jose",
    "mountain view",
    "los angeles",
    "san diego",
    "austin",
    "dallas",
    "houston",
    "boston",
    "cambridge",
    "new york city",
    "chicago",
    "atlanta",
    "washington dc",
    "denver",
    "toronto",
    "vancouver",
    "london",
    "berlin",
    "singapore",
    "seoul",
    "tokyo",
]

MONTHS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}

DISPLAY_LABELS = {
    "a/b testing": "A/B Testing",
    "aws": "AWS",
    "azure": "Azure",
    "c#": "C#",
    "c++": "C++",
    "ci/cd": "CI/CD",
    "css": "CSS",
    "etl": "ETL",
    "fastapi": "FastAPI",
    "fp&a": "FP&A",
    "google cloud": "Google Cloud",
    "html": "HTML",
    "javascript": "JavaScript",
    "mongodb": "MongoDB",
    "node.js": "Node.js",
    "postgresql": "PostgreSQL",
    "power bi": "Power BI",
    "pytorch": "PyTorch",
    "scikit-learn": "Scikit-learn",
    "seo": "SEO",
    "sql": "SQL",
    "typescript": "TypeScript",
    "ux design": "UX Design",
}

SECTION_ALIASES = {
    "education": "education",
    "skills": "skills",
    "technical skills": "skills",
    "technologies": "skills",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "projects": "projects",
    "project experience": "projects",
    "certifications": "certifications",
    "awards": "awards",
    "summary": "summary",
    "objective": "summary",
}

SECTION_CONFIDENCE = {
    "skills": "high",
    "education": "high",
    "experience": "medium",
    "projects": "medium",
    "certifications": "medium",
    "summary": "low",
    "awards": "low",
    "other": "low",
}

CONFIDENCE_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().replace("\u00a0", " ").split())


def _display_label(value: str) -> str:
    return DISPLAY_LABELS.get(value, value.title())


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase.lower()).replace("\\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text))


def _ordered_matches(text: str, candidates: Iterable[str]) -> List[str]:
    return [
        _display_label(candidate)
        for candidate in candidates
        if _contains_phrase(text, candidate)
    ]


def _score_rules(text: str, rules: List[Tuple[str, List[str]]], limit: int = 5) -> List[str]:
    scored: List[Tuple[int, str]] = []
    for label, keywords in rules:
        score = sum(1 for keyword in keywords if _contains_phrase(text, keyword))
        if score:
            scored.append((score, label))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [label for _, label in scored[:limit]]


def _section_name(line: str) -> str | None:
    cleaned = re.sub(r"[^a-zA-Z ]", "", line).strip().lower()
    if len(cleaned.split()) > 4:
        return None
    return SECTION_ALIASES.get(cleaned)


def _sectionize_resume(text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {"other": []}
    current = "other"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading = _section_name(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue

        sections.setdefault(current, []).append(line)

    return sections


def _evidence_item(section: str, line: str) -> str:
    return f"{section.title()}: {line.strip()[:160]}"


def _suggestion(
    field: str,
    value: Any,
    confidence: str,
    evidence: List[str],
) -> Dict[str, Any]:
    return {
        "field": field,
        "value": value,
        "confidence": confidence,
        "evidence": evidence[:2],
    }


def _empty_suggestions() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "extracted_skills": [],
        "majors": [],
        "preferred_roles": [],
        "target_industries": [],
        "preferred_locations": [],
        "education": [],
        "profile_flags": [],
    }


def _candidate_suggestions(
    sections: Dict[str, List[str]],
    candidates: Iterable[str],
    *,
    field: str,
    preferred_sections: set[str],
    limit: int,
    fallback_confidence: str | None = None,
) -> List[Dict[str, Any]]:
    matches: Dict[str, Dict[str, Any]] = {}

    for section, lines in sections.items():
        section_text = _normalize_text(" ".join(lines))
        section_confidence = (
            "high"
            if section in preferred_sections
            else fallback_confidence or SECTION_CONFIDENCE.get(section, "low")
        )
        for candidate in candidates:
            if not _contains_phrase(section_text, candidate):
                continue

            evidence = [
                _evidence_item(section, line)
                for line in lines
                if _contains_phrase(_normalize_text(line), candidate)
            ]
            existing = matches.get(candidate)
            if existing is None or CONFIDENCE_RANK[section_confidence] > CONFIDENCE_RANK[existing["confidence"]]:
                matches[candidate] = {
                    "field": field,
                    "value": _display_label(candidate),
                    "confidence": section_confidence,
                    "evidence": evidence[:2] or [_evidence_item(section, "matched section text")],
                }
            elif evidence:
                existing["evidence"] = list(dict.fromkeys(existing["evidence"] + evidence))[:2]

    ordered = sorted(
        matches.values(),
        key=lambda item: (-CONFIDENCE_RANK[item["confidence"]], str(item["value"]).lower()),
    )
    return ordered[:limit]


def _rule_suggestions(
    normalized_text: str,
    sections: Dict[str, List[str]],
    rules: List[Tuple[str, List[str]]],
    *,
    field: str,
    limit: int,
) -> List[Dict[str, Any]]:
    scored: List[Tuple[int, Dict[str, Any]]] = []

    for label, keywords in rules:
        matched_keywords = [keyword for keyword in keywords if _contains_phrase(normalized_text, keyword)]
        if not matched_keywords:
            continue

        evidence: List[str] = []
        best_confidence = "low"
        for section, lines in sections.items():
            for line in lines:
                normalized_line = _normalize_text(line)
                if any(_contains_phrase(normalized_line, keyword) for keyword in matched_keywords):
                    evidence.append(_evidence_item(section, line))
                    if CONFIDENCE_RANK[SECTION_CONFIDENCE.get(section, "low")] > CONFIDENCE_RANK[best_confidence]:
                        best_confidence = SECTION_CONFIDENCE.get(section, "low")

        if len(matched_keywords) >= 2 and best_confidence == "low":
            best_confidence = "medium"

        scored.append(
            (
                len(matched_keywords),
                _suggestion(field, label, best_confidence, evidence or [f"Matched keywords: {', '.join(matched_keywords[:3])}"]),
            )
        )

    scored.sort(key=lambda item: (-item[0], -CONFIDENCE_RANK[item[1]["confidence"]], item[1]["value"]))
    return [suggestion for _, suggestion in scored[:limit]]


def _extract_degree(text: str) -> str:
    if _contains_phrase(text, "phd") or _contains_phrase(text, "doctor of philosophy"):
        return "PhD"
    if _contains_phrase(text, "master") or _contains_phrase(text, "ms") or _contains_phrase(text, "m.s."):
        return "Master's"
    if _contains_phrase(text, "bachelor") or _contains_phrase(text, "bs") or _contains_phrase(text, "b.s."):
        return "Bachelor's"
    if _contains_phrase(text, "associate"):
        return "Associate"
    if _contains_phrase(text, "bootcamp") or _contains_phrase(text, "certificate"):
        return "Bootcamp / Certificate"
    return ""


def _degree_suggestion(sections: Dict[str, List[str]], normalized_text: str) -> Dict[str, Any] | None:
    degree = _extract_degree(normalized_text)
    if not degree:
        return None

    education_lines = sections.get("education", [])
    evidence = [_evidence_item("education", line) for line in education_lines[:2]]
    confidence = "high" if education_lines else "medium"
    return _suggestion("degree_level", degree, confidence, evidence or ["Degree wording found in resume text"])


def _extract_graduation_date(text: str) -> str:
    month_year = re.search(
        r"(?:expected\s+)?(?:graduation|graduate|graduating|class\s+of)?\s*"
        r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"[\s,]+(20\d{2})",
        text,
    )
    if month_year:
        month = MONTHS[month_year.group(1)]
        return f"{month_year.group(2)}-{month}"

    year_month = re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])", text)
    if year_month:
        return f"{year_month.group(1)}-{int(year_month.group(2)):02d}"

    year = re.search(r"(?:graduation|graduate|graduating|class\s+of)[^\n.]{0,40}\b(20\d{2})\b", text)
    if year:
        return f"{year.group(1)}-05"

    return ""


def _graduation_suggestion(sections: Dict[str, List[str]], normalized_text: str) -> Dict[str, Any] | None:
    grad_date = _extract_graduation_date(normalized_text)
    if not grad_date:
        return None

    evidence_lines = [
        line
        for line in sections.get("education", []) + sections.get("other", [])
        if re.search(r"(graduat|class\s+of|20\d{2})", line, re.IGNORECASE)
    ]
    confidence = "high" if evidence_lines and any(line in sections.get("education", []) for line in evidence_lines) else "medium"
    return _suggestion(
        "grad_date",
        grad_date,
        confidence,
        [_evidence_item("education", evidence_lines[0])] if evidence_lines else ["Graduation date pattern found in resume text"],
    )


def _extract_years_of_experience(text: str) -> int:
    matches = [
        int(match)
        for match in re.findall(r"\b([0-9]|1[0-9]|20)\+?\s+(?:years?|yrs?)\s+(?:of\s+)?experience\b", text)
    ]
    return max(matches) if matches else 0


def _years_suggestion(normalized_text: str) -> Dict[str, Any] | None:
    years = _extract_years_of_experience(normalized_text)
    if years <= 0:
        return None
    return _suggestion("years_of_experience", years, "medium", [f"Found explicit experience duration: {years} years"])


def _extract_resume_text_from_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page for page in pages if page.strip())


def _extract_resume_text_from_docx(content: bytes) -> str:
    from docx import Document

    document = Document(BytesIO(content))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


def extract_resume_text(filename: str, content: bytes) -> str:
    if len(content) > MAX_RESUME_BYTES:
        raise ValueError("Resume file is too large. Upload a file under 5 MB.")

    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        return _extract_resume_text_from_pdf(content)
    if suffix == ".docx":
        return _extract_resume_text_from_docx(content)

    raise ValueError("Unsupported resume file type. Upload .txt, .md, .pdf, or .docx.")


def parse_resume_text(text: str) -> Dict[str, Any]:
    normalized = _normalize_text(text)
    sections = _sectionize_resume(text)
    suggestions = _empty_suggestions()
    suggestions["extracted_skills"] = _candidate_suggestions(
        sections,
        SKILL_KEYWORDS,
        field="extracted_skills",
        preferred_sections={"skills", "certifications"},
        limit=20,
    )
    suggestions["majors"] = _candidate_suggestions(
        sections,
        MAJOR_KEYWORDS,
        field="majors",
        preferred_sections={"education"},
        limit=5,
    )
    suggestions["preferred_roles"] = _rule_suggestions(
        normalized,
        sections,
        ROLE_RULES,
        field="preferred_roles",
        limit=5,
    )
    suggestions["target_industries"] = _rule_suggestions(
        normalized,
        sections,
        INDUSTRY_RULES,
        field="target_industries",
        limit=5,
    )
    suggestions["preferred_locations"] = _candidate_suggestions(
        sections,
        LOCATION_KEYWORDS,
        field="preferred_locations",
        preferred_sections={"summary", "other"},
        limit=5,
        fallback_confidence="low",
    )

    for education_suggestion in (
        _degree_suggestion(sections, normalized),
        _graduation_suggestion(sections, normalized),
    ):
        if education_suggestion:
            suggestions["education"].append(education_suggestion)

    years_suggestion = _years_suggestion(normalized)
    if years_suggestion:
        suggestions["profile_flags"].append(years_suggestion)

    if re.search(r"\b(sponsorship|visa|h-?1b|opt|cpt)\b", normalized):
        suggestions["profile_flags"].append(
            _suggestion("sponsorship_need", True, "medium", ["Visa or sponsorship wording found in resume text"])
        )

    skills = [item["value"] for item in suggestions["extracted_skills"]]
    majors = [item["value"] for item in suggestions["majors"]]
    roles = [item["value"] for item in suggestions["preferred_roles"]]
    industries = [item["value"] for item in suggestions["target_industries"]]
    locations = [item["value"] for item in suggestions["preferred_locations"]]
    warnings: List[str] = []

    if not skills:
        warnings.append("No known skills were found. Add skills manually before matching.")
    if not majors:
        warnings.append("No major was detected. Choose a major manually.")
    if not roles:
        warnings.append("No target role was inferred. Add preferred roles if you want a narrower search.")

    return {
        "resume_text": text.strip(),
        "degree_level": _extract_degree(normalized),
        "major": majors[0] if majors else "Other",
        "majors": majors,
        "grad_date": _extract_graduation_date(normalized),
        "preferred_roles": roles,
        "preferred_locations": locations[:5],
        "target_industries": industries,
        "sponsorship_need": bool(re.search(r"\b(sponsorship|visa|h-?1b|opt|cpt)\b", normalized)),
        "extracted_skills": skills[:20],
        "years_of_experience": _extract_years_of_experience(normalized),
        "notes": "Imported from resume. Review detected fields before saving.",
        "suggestions": suggestions,
        "warnings": warnings,
    }


def parse_resume_file(filename: str, content: bytes) -> Dict[str, Any]:
    text = extract_resume_text(filename, content)
    if len(text.strip()) < 30:
        raise ValueError("Could not extract enough resume text from this file.")
    return parse_resume_text(text)
