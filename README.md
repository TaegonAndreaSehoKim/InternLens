# InternLens

InternLens is an internship application strategy optimizer that ranks job postings by candidate fit and recommends **Apply Now**, **Apply Later**, or **Skip**.

## Why I built it

I built this project after struggling to get past the resume screen for graduate-level summer internships. The goal was to create a system that helps prioritize where to apply by combining profile data, job requirements, ranking logic, explainable decision signals, and lightweight personalization.

## What it does

Given a candidate profile and a set of internship postings, InternLens:

- parses candidate and job data
- ranks jobs using a baseline scoring pipeline
- separates **fit score** from **blocking constraints**
- applies **blocker-aware ordering** so recommendation buckets stay intuitive
- optionally applies **feedback-based reranking** using prior applied / saved / skipped signals
- returns:
  - score
  - action label
  - matched skills
  - skill gaps
  - blocking issues
  - reasons
  - optional reranking fields when feedback is used

This makes it possible to distinguish between a role that is a good fit but blocked by eligibility constraints and a role that is simply a weak fit.

## Current ranking logic

The baseline fit score is computed from:

- skill match
- role match
- location match

Blocking constraints are handled separately from the numeric fit score so that a posting can still be recognized as relevant even when the candidate cannot realistically apply.

The final baseline ordering is recommendation-aware:

1. **Apply Now**
2. **Apply Later**
3. **Skip**

Within each recommendation bucket, InternLens uses blocker count and score to order results.

## Current blocker logic

The current blocker layer includes:

- sponsorship mismatch
- expanded eligibility-style checks from job requirements

Examples of eligibility-style checks currently covered include:

- non-internship job type
- explicit PhD requirement mismatch
- lightweight graduation timing mismatch checks

## Feedback-based reranking (v1)

InternLens now supports an optional feedback reranking step.

When a feedback file is provided, the system uses prior job interaction signals such as:

- `applied`
- `saved`
- `skipped`

The reranker computes a lightweight similarity signal using meaningful title tokens and a small known skill vocabulary, then adjusts the original score.

Important behavior:

- reranking does **not** override blocker-aware recommendation ordering
- feedback boosts are applied within the existing recommendation policy
- API and script outputs expose:
  - `feedback_adjustment`
  - `reranked_score`

## Current features

- candidate profile parsing
- job posting parsing
- baseline ranking engine
- skill alias normalization
- role matching with generic token filtering
- blocking constraint handling
- blocker-aware ordering
- feedback-based reranking
- JSON / CSV result export
- FastAPI endpoints (`/health`, `/recommend`)
- inline profile payload support for `/recommend`
- optional `feedback_path` support for `/recommend`
- pytest coverage for core API, ranking, and reranking behavior

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

### Baseline request

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

### Feedback-aware request

```json
{
  "profile_path": "data/processed/candidate_profile_example.json",
  "jobs_dir": "data/sample_jobs",
  "feedback_path": "data/feedback/sample_feedback.json",
  "top_k": 5
}
```

## Example API response fields

When feedback reranking is applied, `/recommend` also returns:

- `feedback_source`
- `reranking_applied`
- `feedback_adjustment` for each job result
- `reranked_score` for each job result

## Notes on the demo data

The sample dataset includes blocker-oriented examples to make recommendation behavior easier to understand. In particular, `job_006` helps demonstrate how a posting can look relevant on fit signals but still be recommended as **Skip** because of blocker logic.

The sample feedback data demonstrates how previously applied, saved, and skipped jobs can slightly adjust ranking order without overriding hard eligibility constraints.

## Current test coverage snapshot

The current project test suite covers:

- `/health`
- `/recommend` with inline profile payloads
- `/recommend` with profile file paths
- `/recommend` with optional feedback reranking
- missing feedback file handling
- blocker-aware ranking behavior
- feedback reranker loading and enrichment behavior

## Next steps

- improve explanation quality and recommendation transparency
- expand feedback signal design beyond simple label weights
- add semantic retrieval for better matching recall
- replace heuristic ranking with learning-to-rank
- add persistence and deployment
