# InternLens

InternLens is an internship application strategy optimizer that ranks job postings by candidate fit and recommends **Apply Now**, **Apply Later**, or **Skip**.

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

This makes it possible to distinguish between a role that is a good fit but blocked by eligibility constraints and a role that is simply a weak fit.

## Current ranking logic

The current baseline fit score is computed from:

- skill match
- role match
- location match

Blocking constraints are handled separately from the numeric fit score so that a posting can still be recognized as relevant even when the candidate cannot realistically apply.

## Current blocker logic

The current blocker layer includes:

- sponsorship mismatch
- expanded eligibility-style checks from job requirements

Examples of eligibility-style checks currently covered include:

- non-internship job type
- explicit PhD requirement mismatch
- lightweight graduation timing mismatch checks

## Current features

- candidate profile parsing
- job posting parsing
- baseline ranking engine
- skill alias normalization
- role matching with generic token filtering
- blocking constraint handling
- JSON / CSV result export
- FastAPI endpoints (`/health`, `/recommend`)
- inline profile payload support for `/recommend`
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

## Notes on the demo data

The sample dataset includes blocker-oriented examples to make recommendation behavior easier to understand. In particular, `job_006` helps demonstrate how a posting can look relevant on fit signals but still be recommended as **Skip** because of blocker logic.

## Next steps

- improve explanation quality and recommendation transparency
- add feedback-based reranking
- add semantic retrieval for better matching recall
- replace heuristic ranking with learning-to-rank
- add persistence and deployment
