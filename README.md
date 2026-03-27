# InternLens

InternLens is an internship application strategy optimizer that ranks job postings by candidate fit and recommends **Apply Now**, **Apply Later**, or **Skip**.

## Why I built it

I built this project after struggling to get past the resume screen for graduate-level summer internships. The goal was to create a system that helps prioritize where to apply by combining profile data, job requirements, ranking logic, and explainable decision signals.

## What it does

Given a candidate profile and a set of internship postings, InternLens:

- parses candidate and job data
- computes a baseline fit score
- evaluates blocking constraints separately from fit
- applies blocker-aware ranking order for final recommendation priority
- optionally reranks jobs using lightweight user feedback signals
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

The final baseline ordering is blocker-aware. InternLens prioritizes:

1. **Apply Now**
2. **Apply Later**
3. **Skip**

Within each action bucket, jobs are ordered using blocker count and score-based ranking signals.

## Current blocker logic

The current blocker layer includes:

- sponsorship mismatch
- expanded eligibility-style checks from job requirements

Examples of eligibility-style checks currently covered include:

- non-internship job type
- explicit PhD requirement mismatch
- lightweight graduation timing mismatch checks

## Feedback-based reranking v1

InternLens now includes an optional feedback-based reranking layer.

This reranker uses lightweight feedback events such as:

- `applied`
- `saved`
- `skipped`

The current v1 behavior:

- loads feedback from a small JSON profile
- compares new jobs against previously seen jobs using title and skill similarity
- boosts jobs that look more like positively marked jobs
- penalizes jobs that look more like skipped jobs
- preserves blocker-aware action ordering so reranking does not push blocked jobs above stronger actionable targets

This feature is intentionally simple and explainable. It is designed as a practical first step toward personalization rather than a full learning-to-rank system.

## Current features

- candidate profile parsing
- job posting parsing
- baseline ranking engine
- skill alias normalization
- role matching with generic token filtering
- blocking constraint handling
- blocker-aware ranking order
- feedback-based reranking v1
- JSON / CSV result export
- FastAPI endpoints (`/health`, `/recommend`)
- inline profile payload support for `/recommend`
- pytest coverage for ranking, reranking, and API behavior

## Project structure

```text
InternLens/
├── data/
│   ├── feedback/
│   ├── processed/
│   └── sample_jobs/
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
python scripts/run_baseline.py --feedback-path data/feedback/sample_feedback.json
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

The feedback sample file provides a simple personalization demo for reranking behavior without changing the baseline scorer.

## Next steps

- improve feedback signals and adjustment calibration
- add API support for optional feedback-based reranking
- improve explanation transparency for reranked results
- add semantic retrieval for better matching recall
- replace heuristic ranking with learning-to-rank
- add persistence and deployment
