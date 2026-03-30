# InternLens

InternLens is a lightweight internship discovery and ranking pipeline for public job boards.

It fetches internship postings from public ATS sources, normalizes them into a shared schema, ranks them against a candidate profile, and exposes the results through both a CLI workflow and a FastAPI service.

The project started as a simple baseline recommender on static sample jobs, but it now supports multi-source ingestion, registry-driven batch fetches, blocker-aware ranking, shortlist-oriented CLI filters, and regression-tested API behavior. Current validation status: the full test suite is passing (`68 passed`).

---

## What the project does

InternLens supports the following end-to-end flow:

1. Fetch public job postings from ATS boards
2. Save raw snapshots for reproducibility
3. Normalize postings into a shared processed schema
4. Load a candidate profile
5. Score and rank postings using a baseline internship-focused heuristic
6. Optionally rerank with feedback signals
7. Inspect results from the CLI or API

The current implementation is intentionally simple and transparent. It is designed to be easy to extend, easy to debug, and good enough for a demo-quality internship search workflow.

---

## Current capabilities

### Ingestion
- Lever single-board fetch
- Lever raw snapshot saving
- Lever processed job normalization
- Lever registry-based batch fetch
- Greenhouse single-board fetch
- Greenhouse raw snapshot saving
- Greenhouse processed job normalization
- Greenhouse registry-based batch fetch

### Ranking
- baseline scoring against a candidate profile
- blocker-aware recommendations
- senior-role blocker
- non-internship blocker
- PhD requirement blocker
- explicit internship bonus
- internship-focused ranking order
- fallback skill extraction for sparse public postings
- reduced noisy fallback matching for non-technical internship titles

### Output / usability
- shortlist CLI workflow
- `--eligible-only` filter
- `--applyable-only` filter
- JSON and CSV exports
- API endpoint for `/recommend`
- API endpoint for `/jobs/{id}`

### Validation
- registry flow tests
- ingestion client tests
- ranking regression tests
- CLI filtering tests
- API tests
- full suite currently passing: `68 passed`

---

## Project structure

```text
InternLens/
├── data/
│   ├── raw/
│   │   ├── lever/
│   │   └── greenhouse/
│   ├── processed/
│   │   ├── jobs/
│   │   └── candidate_profile_example.json
│   ├── sample_jobs/
│   └── source_registry/
│       ├── lever_targets.json
│       └── greenhouse_targets.json
├── outputs/
├── scripts/
│   ├── fetch_lever_jobs.py
│   ├── fetch_lever_registry.py
│   ├── fetch_greenhouse_jobs.py
│   ├── fetch_greenhouse_registry.py
│   └── run_baseline.py
├── src/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── ranking/
│   └── api/
├── tests/
└── README.md
```

---

## Supported sources

### Lever
InternLens can fetch public Lever postings by board token / site name.

Examples already tested during development:
- `acds`
- `rws`

### Greenhouse
InternLens can fetch public Greenhouse postings by board token.

Examples already tested during development:
- `waymo`
- `honehealth`
- `cloudflare`

Greenhouse normalization now uses metadata-based geographic location extraction when available, which improves location quality compared with relying only on generic work-mode labels like `Hybrid` or `In-Office`.

---

## Installation

Create and activate a virtual environment, then install dependencies.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If you do not yet have a `requirements.txt`, install the packages already used in the project environment.

```bash
pip install fastapi uvicorn httpx pytest pandas
```

Add any other packages your local project already depends on.

---

## Candidate profile format

InternLens expects a processed candidate profile JSON file.

Example fields:

```json
{
  "profile_id": "seho_001",
  "resume_text": "Graduate student with Python, PyTorch, machine learning, and data analysis experience.",
  "degree_level": "Master's",
  "grad_date": "2027-12",
  "preferred_roles": [
    "Machine Learning Engineer Intern",
    "Applied Scientist Intern"
  ],
  "preferred_locations": ["California", "Remote"],
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
}
```

---

## Job schema

Processed jobs are normalized into a shared shape similar to:

```json
{
  "job_id": "greenhouse_cloudflare_123456",
  "source": "greenhouse",
  "source_site": "cloudflare",
  "source_job_id": "123456",
  "company": "cloudflare",
  "title": "Software Engineer Intern (Summer 2026)",
  "location": "Austin, US",
  "description": "...",
  "min_qualifications": "",
  "preferred_qualifications": "",
  "posting_date": "2026-03-30",
  "sponsorship_info": "",
  "employment_type": "Internship",
  "source_url": "https://...",
  "application_url": "https://...",
  "remote_status": "hybrid",
  "team": "Engineering"
}
```

Not every field is populated equally across sources. Public ATS data is noisy, so normalization is intentionally conservative.

---

## How to fetch postings

### Fetch a single Lever board

```bash
python scripts/fetch_lever_jobs.py --site-name acds --limit 20 --timeout 60
```

### Fetch all active Lever registry targets

```bash
python scripts/fetch_lever_registry.py --only-active
```

### Fetch a single Greenhouse board

```bash
python scripts/fetch_greenhouse_jobs.py --board-token waymo --limit 50 --timeout 60
python scripts/fetch_greenhouse_jobs.py --board-token cloudflare --limit 200 --timeout 60
```

### Fetch all active Greenhouse registry targets

```bash
python scripts/fetch_greenhouse_registry.py --only-active --internship-only
```

---

## How to run the baseline ranker

### Run on sample jobs

```bash
python scripts/run_baseline.py
```

### Run on a processed source directory

```bash
python scripts/run_baseline.py --jobs-dir data/processed/jobs/greenhouse/waymo
python scripts/run_baseline.py --jobs-dir data/processed/jobs/greenhouse/cloudflare
```

### Show only blocker-free jobs

```bash
python scripts/run_baseline.py --jobs-dir data/processed/jobs/greenhouse/waymo --eligible-only
```

### Show only non-Skip recommendations

```bash
python scripts/run_baseline.py --jobs-dir data/processed/jobs/greenhouse/cloudflare --applyable-only
```

### Combine filters for a shortlist-style view

```bash
python scripts/run_baseline.py --jobs-dir data/processed/jobs/greenhouse/cloudflare --eligible-only --applyable-only
```

Current behavior from recent validation:
- `waymo --applyable-only` surfaces a very small shortlist centered on a real target internship
- `cloudflare --applyable-only` produces a narrower internship subset than before, with examples such as `Data Analytics Intern`, `Data Engineer Intern`, `Business Analyst Intern`, `Network Deployment Engineer Intern`, and `Marketing: AI Discoverability & Optimization Intern` in the visible shortlist.

---

## API usage

Start the API server:

```bash
uvicorn src.api.main:app --reload
```

Main endpoints:
- `POST /recommend`
- `GET /jobs/{id}`

### Example recommend request

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
    "preferred_locations": ["California", "Remote"],
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

---

## Ranking logic (baseline)

The current baseline is heuristic-based and intentionally interpretable.

### Positive signals
- overlap with candidate skills
- overlap with preferred roles
- location match
- explicit internship language
- some fallback skill extraction from title/description when structured qualifications are sparse

### Blocking signals
- job does not appear to be an internship
- role appears to be senior-level
- role appears to require a PhD
- graduation timing mismatch
- sponsorship conflicts

### Output labels
- `Apply Now`
- `Apply Later`
- `Skip`

These labels are not meant to be perfect hiring predictions. They are meant to provide a simple shortlist-oriented baseline that is easy to inspect and improve.

---

## Testing

Run the full test suite:

```bash
pytest -q
```

Current status:
- full test suite passing
- `68 passed` as of the latest validation log

Useful targeted test commands:

```bash
pytest tests/test_greenhouse_client.py -q
pytest tests/test_baseline_scorer_seniority.py -q
pytest tests/test_run_baseline_cli.py -q
pytest tests/test_api_and_ranking.py -q
```

---

## Known limitations

- ranking is still heuristic and not learned
- fallback skill extraction can still overmatch broad terms in some postings
- some non-core internships can still survive ranking if they resemble technical/data roles
- company normalization is lightweight
- location preference scoring can still be refined for hybrid/in-office jobs
- duplicate-looking multi-location internships may still appear as separate postings

---

## Why this project is useful

InternLens now demonstrates more than a toy static recommender.

It shows a realistic small-scale workflow for:
- public internship ingestion
- schema normalization
- candidate-profile ranking
- shortlist generation
- API exposure
- regression-tested iteration

That makes it a strong base for future work such as:
- better profile extraction
- vector or embedding-based retrieval
- learned reranking
- deduplication
- company/role taxonomy normalization
- personalized feedback loops

---

## Next steps

Planned follow-up improvements:
- reduce remaining ranking noise for broad non-core internships
- refine hybrid/in-office location preference handling
- improve deduplication for repeated internship postings
- clean up company and team normalization
- expand final demo documentation
- prepare a more polished shortlist UX for the API layer
