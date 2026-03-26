# InternLens

InternLens is an internship application strategy optimizer that ranks job postings by candidate fit and returns **Apply Now / Apply Later / Skip** recommendations.

## Why I built it

I built this project after struggling to get past the resume screen for graduate-level summer internships. The goal was to create a system that helps prioritize where to apply by combining profile data, job requirements, ranking logic, and explainable decision signals.

## What it does

Given a candidate profile and a set of internship postings, InternLens:

- parses candidate and job data
- ranks jobs using a baseline scoring pipeline
- separates **fit score** from **blocking constraints**
- returns:
  - score
  - action label
  - matched skills
  - skill gaps
  - blocking issues
  - reasons

## Current features

- candidate profile parsing
- job posting parsing
- baseline ranking engine
- skill alias normalization
- blocking constraint handling
- JSON / CSV result export
- FastAPI endpoints (`/health`, `/recommend`)
- pytest coverage for core API and ranking behavior

## Project structure

```text
InternLens/
├── data/
├── outputs/
├── scripts/
│   └── run_baseline.py
├── src/
│   ├── api/
│   │   └── app.py
│   ├── preprocessing/
│   └── ranking/
├── tests/
├── requirements.txt
└── README.md
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/run_baseline.py
uvicorn src.api.app:app --reload
python -m pytest -q
```

## Example API input

```json
{
  "profile_data": {
    "profile_id": "seho_001",
    "resume_text": "Graduate student with Python, PyTorch, machine learning, and data analysis experience.",
    "degree_level": "Master's",
    "grad_date": "2027-12",
    "preferred_roles": [
      "Machine Learning Engineer Intern",
      "Applied Scientist Intern"
    ],
    "preferred_locations": [
      "California",
      "Remote"
    ],
    "target_industries": ["AI", "Tech"],
    "sponsorship_need": true,
    "extracted_skills": [
      "Python",
      "PyTorch",
      "Machine Learning",
      "Data Analysis"
    ],
    "years_of_experience": 1,
    "notes": "Interested in recommendation and ranking systems"
  },
  "jobs_dir": "data/sample_jobs",
  "top_k": 5
}
```

## Next steps

- richer blocker logic
- semantic retrieval
- learning-to-rank models
- feedback-based reranking
- deployment
