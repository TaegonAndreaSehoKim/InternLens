# InternLens

InternLens is a lightweight internship discovery and ranking pipeline for public job boards.

It fetches public internship postings from ATS job boards, normalizes them into a shared schema, ranks them against a candidate profile, and exposes the results through both a CLI workflow and a FastAPI service.

The project started as a simple baseline recommender on static sample jobs, but it now supports multi-source ingestion, registry-driven batch fetches, blocker-aware ranking, shortlist-oriented CLI filters, and regression-tested API behavior.

## Current status

InternLens currently supports:
- Lever ingestion
- Greenhouse ingestion
- raw snapshot saving
- processed job normalization
- registry-driven batch fetching
- one-command corpus refresh across Lever and Greenhouse registries
- company-seed-based source discovery for candidate ATS sources
- baseline ranking with internship blockers
- shortlist-oriented CLI filters
- API endpoints for recommendation and job detail lookup
- regression-tested iteration

Current architecture planning also includes a long-term source acquisition strategy centered on:
- company seeds
- source discovery
- source validation
- source scoring
- scheduled corpus refresh

Latest validation state:
- full test suite passing
- current total: `94 passed`
- Cloudflare shortlist narrowed to a small applyable-only subset focused on more relevant roles such as Data Analytics Intern, Business Analyst Intern, DCSC Automation Coordinator Intern, Network Deployment Engineer Intern, and Data Engineer Intern
- GitHub Actions test workflow added for `push` and `pull_request` on `main`

---

## What the project does

InternLens supports the following flow:

1. Fetch public job postings from ATS boards
2. Save raw snapshots for reproducibility
3. Normalize jobs into a shared processed schema
4. Load a candidate profile
5. Score and rank postings using a baseline internship-focused heuristic
6. Optionally rerank with feedback signals
7. Inspect results through the CLI or API

The current implementation is intentionally simple and transparent. It is designed to be easy to extend, easy to debug, and good enough for demo-quality internship search workflows.

---

## Core capabilities

### Ingestion

#### Lever
- single-board fetch
- raw snapshot saving
- processed job normalization
- registry-based batch fetch

#### Greenhouse
- single-board fetch
- raw snapshot saving
- processed job normalization
- registry-based batch fetch
- metadata-aware geographic location extraction for boards that use generic work-mode labels such as `Hybrid` or `In-Office`

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
- tighter shortlist precision for noisy public boards such as Cloudflare

### Output / usability
- shortlist CLI workflow
- `--eligible-only`
- `--applyable-only`
- JSON export
- CSV export
- API endpoint for `/recommend`
- API endpoint for `/jobs/{id}`

### Validation
- ingestion client tests
- registry flow tests
- ranking regression tests
- CLI filtering tests
- API tests
- deduplication cleanup tests
- source discovery tests
- source validation tests
- source promotion tests
- full suite currently passing: `94 passed`
- GitHub Actions workflow for automated `pytest -q`

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
│       ├── greenhouse_targets.json
│       ├── company_seeds.example.json
│       └── discovered_sources.example.json
├── docs/
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── schema.md
│   │   └── source_acquisition_strategy.md
│   └── devlog/
│       ├── week1.md
│       └── week2.md
├── outputs/
├── scripts/
│   ├── fetch_lever_jobs.py
│   ├── fetch_lever_registry.py
│   ├── fetch_greenhouse_jobs.py
│   ├── fetch_greenhouse_registry.py
│   └── run_baseline.py
├── src/
│   ├── api/
│   ├── ingestion/
│   ├── preprocessing/
│   └── ranking/
├── tests/
├── requirements.txt
└── README.md
```

---

## Supported sources

### Lever
InternLens can fetch public Lever postings by board token / site name.

Examples used during development:
- `acds`
- `rws`

### Greenhouse
InternLens can fetch public Greenhouse postings by board token.

Examples used during development:
- `waymo`
- `honehealth`
- `cloudflare`

Greenhouse normalization now prefers metadata-based geographic location when available. This improves output quality for boards where the top-level location is only a work-mode label.

---

## Installation

Create and activate a virtual environment, then install dependencies.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If needed, install the packages already used in the project environment.

```bash
pip install fastapi uvicorn httpx pytest pandas
```

---

## Candidate profile format

InternLens expects a processed candidate profile JSON file.

Example:

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

## Processed job schema

Processed jobs are normalized into a shared shape similar to this:

```json
{
  "job_id": "greenhouse_cloudflare_123456",
  "source": "greenhouse",
  "source_site": "cloudflare",
  "source_job_id": "123456",
  "company": "Cloudflare",
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

Not every field is populated equally across sources. Public ATS data is noisy, so normalization remains intentionally conservative.

---

## How to fetch postings

### Fetch a single Lever board

```bash
python scripts/fetch_lever_jobs.py --site-name acds --limit 20 --timeout 60
```

### Fetch active Lever registry targets

```bash
python scripts/fetch_lever_registry.py --only-active
```

### Fetch a single Greenhouse board

```bash
python scripts/fetch_greenhouse_jobs.py --board-token waymo --limit 50 --timeout 60
python scripts/fetch_greenhouse_jobs.py --board-token cloudflare --limit 200 --timeout 60
```

### Fetch active Greenhouse registry targets

```bash
python scripts/fetch_greenhouse_registry.py --only-active --internship-only
```

### Refresh the full internal job corpus

```bash
python scripts/refresh_job_corpus.py
```

Useful options:

```bash
python scripts/refresh_job_corpus.py --greenhouse-only
python scripts/refresh_job_corpus.py --lever-only
python scripts/refresh_job_corpus.py --include-inactive
python scripts/refresh_job_corpus.py --greenhouse-all-jobs
```

This command is the preferred entry point for keeping the internal recommendation corpus fresh.
It runs both registry flows, saves raw snapshots, and updates processed jobs in one pass.

### Discover new candidate ATS sources from company seeds

```bash
python scripts/discover_sources.py
```

Useful notes:
- the script looks for `data/source_registry/company_seeds.json`
- if that file is missing, it falls back to `data/source_registry/company_seeds.example.json`
- discovered candidates are written to `data/source_registry/discovered_sources.json`
- the script records candidate sources only and does not auto-promote them into active registries

### Validate discovered ATS source candidates

```bash
python scripts/validate_sources.py
```

Useful notes:
- the script reads `data/source_registry/discovered_sources.json`
- by default it validates only sources whose status is `candidate`
- validation checks fetch success, non-empty results, normalization success, and internship density
- active registry duplicates are noted in `validation_notes` but are not auto-promoted or removed

### Promote validated sources into active registries

```bash
python scripts/promote_sources.py
```

Useful notes:
- the script reads `data/source_registry/discovered_sources.json`
- only sources with status `validated` are promotable
- by default the source must meet a minimum score and have at least some internship signal
- matching inactive registry entries are reactivated instead of duplicated

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

### Combine filters for shortlist-style inspection

```bash
python scripts/run_baseline.py --jobs-dir data/processed/jobs/greenhouse/cloudflare --eligible-only --applyable-only
```

Recent validation examples:
- Waymo applyable-only output is very small and focused.
- Cloudflare applyable-only output is now much narrower than before and currently surfaces a shortlist centered on more relevant roles such as:
  - Data Analytics Intern
  - Business Analyst Intern, Revenue Operations (AI Innovation)
  - DCSC Automation Coordinator Intern
  - Network Deployment Engineer Intern
  - Data Engineer Intern

---

## API usage

Start the API server:

```bash
uvicorn src.api.app:app --reload
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

## Baseline ranking logic

The current baseline is heuristic-based and intentionally interpretable.

### Positive signals
- overlap with candidate skills
- overlap with preferred roles
- location match
- explicit internship language
- limited fallback skill extraction from title/description when structured qualifications are sparse and the title looks technical enough to trust

### Blocking signals
- role does not appear to be an internship
- role appears to be senior-level
- role appears to require a PhD
- graduation timing mismatch
- sponsorship conflicts

### Output labels
- `Apply Now`
- `Apply Later`
- `Skip`

These labels are not intended as perfect hiring predictions. They are intended to provide a shortlist-oriented baseline that is transparent and easy to improve.

---

## Testing

Run the full suite:

```bash
pytest -q
```

Useful targeted runs:

```bash
pytest tests/test_greenhouse_client.py -q
pytest tests/test_baseline_scorer_seniority.py -q
pytest tests/test_run_baseline_cli.py -q
pytest tests/test_api_and_ranking.py -q
```

Current status:
- full test suite passing
- current total: `94 passed`
- GitHub Actions workflow runs `pytest -q` on `push` and `pull_request` to `main`
- GitHub Actions also includes a scheduled/manual corpus refresh workflow for Lever and Greenhouse registry sources

---

## Known limitations

- ranking is still heuristic, not learned
- fallback skill extraction can still overgeneralize in some postings
- some broad AI-adjacent or operations internships may still survive ranking if they resemble technical/data roles
- company normalization remains lightweight
- hybrid/in-office preference handling can still be refined further
- duplicate-looking multi-location internships may still appear as separate postings
- source discovery, validation, and promotion are now scriptable, but source quality thresholds still need human tuning

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
- continue refining hybrid/in-office location preference handling
- improve deduplication for repeated internship postings
- improve company and team normalization
- add company-seed-based source discovery and validation
- polish shortlist summaries in the API layer
- prepare cleaner demo outputs and documentation
