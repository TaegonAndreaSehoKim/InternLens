# InternLens

InternLens is a lightweight internship discovery and ranking pipeline for public job boards.

It fetches public internship postings from ATS job boards, normalizes them into a shared schema, ranks them against a candidate profile, and exposes the results through both a CLI workflow and a FastAPI service.

The project started as a simple baseline recommender on static sample jobs, but it now supports multi-source ingestion, registry-driven batch fetches, blocker-aware ranking, shortlist-oriented CLI filters, and regression-tested API behavior.
It also includes a lightweight Vite/React frontend for the stored-profile recommendation workflow.

## Highlights

- **Live staging app:** `https://main.d1d00e49guhewo.amplifyapp.com`
- **AWS deployment:** frontend on Amplify, backend on Elastic Beanstalk behind CloudFront, and backend release automation through CodePipeline/CodeBuild.
- **Scheduled corpus refresh:** a weekly CodeBuild buildspec can refresh public ATS jobs, package the backend bundle, and deploy a new Elastic Beanstalk application version without a user request.
- **Real public-board ingestion:** Lever and Greenhouse fetchers save raw snapshots and normalized processed job records.
- **Explainable recommendations:** heuristic internship ranking returns fit reasons, blockers, action labels, and shortlist-friendly output.
- **Product workflow:** user-scoped stored profiles, Cognito-capable auth, recommendation runs, feedback, saved/applied/hidden job actions, dashboard activity, state-specific job views, searchable/paginated shortlist review, visible-by-default match signals, skill-gap actions, and job detail modals are available through the API and frontend.
- **Quality checkpoint:** Python suite currently passes at `188 passed`; frontend lint, tests, and production build are also passing.
- **Prototype boundary:** staging uses single-server SQLite and is not yet production hardened for authentication, multi-user persistence, or custom-domain operations.

## Current status

InternLens currently supports:
- Lever ingestion
- Greenhouse ingestion
- raw snapshot saving
- processed job normalization
- registry-driven batch fetching
- one-command corpus refresh across Lever and Greenhouse registries
- company-seed-based source discovery for candidate ATS sources
- checkpointed source discovery with structured warning summaries
- high-intent same-site discovery link following for student, internship, campus, and early-career pages
- opt-in direct ATS probing and blocked-page manual review records for broad seed scans
- dry-run source promotion diagnostics with internship signal examples
- discovery recall comparison and promotion-candidate smoke scripts for source-quality measurement
- baseline ranking with internship blockers
- shortlist-oriented CLI filters
- API endpoints for recommendation and job detail lookup
- user-scoped stored profile, feedback, recommendation history, job action, and dashboard APIs
- Cognito JWT auth mode for account-scoped API access, with development auth still available for local demos
- Vite/React frontend for account-scoped profile setup, dashboard review, recommendation runs, job actions, saved/applied/hidden review, searchable/paginated shortlist inspection, visible-by-default match signals, and job detail modals
- AWS staging deployment with Amplify frontend auto-deploys and a CodePipeline path for backend test/package/deploy to Elastic Beanstalk
- optional weekly backend corpus refresh/deploy path with `buildspec.weekly-refresh.yml`
- regression-tested iteration

Current architecture planning also includes a long-term source acquisition strategy centered on:
- company seeds
- source discovery
- source validation
- source scoring
- scheduled corpus refresh

Latest validation state:
- full test suite passing
- current total: `188 passed`
- frontend lint, Vitest, and production build passing with `npm run lint`, `npm test -- --run` (`21 passed`), and `npm run build`
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
- `--suppress-similar-results`
- JSON export
- CSV export
- API endpoint for `/recommend`
- API endpoint for `/jobs/{id}`
- profile persistence and stored-feedback recommendation flow
- shared output filtering between CLI and API, including optional similar-result suppression
- local frontend dashboard workflow with clickable saved/applied/hidden state summaries, searchable result review, visible card signals, optional signal hiding, and job detail lookup

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
- source pipeline tests
- source recall and promotion smoke tests
- profile API tests
- full suite currently passing: `188 passed`
- frontend lint, test, and build checks with `npm run lint`, `npm test -- --run`, and `npm run build`
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
- the current working seed draft contains `144` companies to stress-test discovery breadth before later pruning
- a full discovery run over the larger seed draft is currently slow because page fetches are sequential
- some company careers pages now return `403` or `429`, so partial discovery results are expected during wide scans
- Greenhouse embed/helper URLs such as `boards.greenhouse.io/embed/...` are rejected as non-board URLs
- discovery follows a limited number of same-site high-intent links such as student, internship, campus, university, jobs, and early-career pages
- discovery output includes a method summary so broad scans show whether candidates came from careers pages, priority links, direct seed URLs, or direct ATS probes

### Validate discovered ATS source candidates

```bash
python scripts/validate_sources.py
```

Useful notes:
- the script reads `data/source_registry/discovered_sources.json`
- by default it validates only sources whose status is `candidate`
- validation checks fetch success, non-empty results, normalization success, and internship density
- validation records `internship_signal_examples` and includes those titles in `validation_notes` when internship-like postings are detected
- active registry duplicates are noted in `validation_notes` but are not auto-promoted or removed

### Promote validated sources into active registries

```bash
python scripts/promote_sources.py
```

Useful notes:
- the script reads `data/source_registry/discovered_sources.json`
- only sources with status `validated` are promotable
- by default the source must meet a minimum score and a minimum internship-likelihood threshold
- direct ATS probe candidates must meet stricter score and internship-likelihood safeguards
- matching inactive registry entries are skipped by default; use `--reactivate-inactive-sources` to explicitly reactivate them
- use `--dry-run` to inspect promotion decisions without writing registry files

### Compare discovery recall with priority-link following

```bash
python scripts/compare_discovery_recall.py --seed-limit 30
```

Useful notes:
- this compares source discovery with `--priority-follow-limit 0` against the configured priority-follow limit
- the report includes candidate-count delta, warning-count delta, method summaries, and added/removed source records
- generated reports are written under `outputs/discovery_recall_compare*.json` and are ignored by git
- a recent 30-seed smoke found two additional `priority_link_scan` Greenhouse candidates, Anthropic and GitLab, while also adding four extra `404` warnings

### Smoke test promotion candidates through fetch and ranking

```bash
python scripts/smoke_promotion_candidates.py --input-file data/source_registry/discovered_sources.json
```

Useful notes:
- this computes promotion candidates, writes temporary registries, fetches into a temporary workspace, ranks the temporary processed jobs, and writes a compact report
- it does not modify the tracked registries or generated corpus
- generated reports are written under `outputs/promotion_candidate_smoke*.json` and are ignored by git
- recent Anthropic/GitLab recall candidates validated as general boards with `internship_likelihood=0.00`, so the smoke reported `Promotion candidates: 0`

### Run the full source lifecycle in one command

```bash
python scripts/run_source_pipeline.py
```

Useful notes:
- this runs discovery, validation, promotion, and corpus refresh in order
- each stage can be skipped with `--skip-discovery`, `--skip-validation`, `--skip-promotion`, or `--skip-refresh`
- use `--greenhouse-only` or `--lever-only` to limit the refresh step
- use `--refresh-limit` to cap per-source fetch volume during a dry run or smoke test
- source discovery and promotion safeguards can be tuned with flags such as `--priority-follow-limit`, `--min-internship-likelihood`, and direct-probe threshold options

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

To collapse near-duplicate multi-location shortlist items:

```bash
python scripts/run_baseline.py --jobs-dir data/processed/jobs/greenhouse/cloudflare --applyable-only --suppress-similar-results
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

Start the frontend in a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

The frontend expects the API at `http://127.0.0.1:8000` by default.
Set `VITE_API_BASE_URL` if the backend is running somewhere else.

Deployment-relevant environment variables:

```text
INTERNLENS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
INTERNLENS_JOBS_DIR=data/processed/jobs
INTERNLENS_DB_PATH=data/app/internlens.db
INTERNLENS_AUTH_MODE=dev
INTERNLENS_COGNITO_REGION=us-east-2
INTERNLENS_COGNITO_USER_POOL_ID=
INTERNLENS_COGNITO_APP_CLIENT_ID=
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_AUTH_MODE=dev
VITE_COGNITO_REGION=us-east-2
VITE_COGNITO_USER_POOL_ID=
VITE_COGNITO_APP_CLIENT_ID=
```

See `.env.example`, `frontend/.env.example`, and `docs/deployment/aws_staging.md` for staging notes.

Main endpoints:
- `POST /recommend`
- `GET /jobs/{id}`
- `POST /profiles`
- `GET /profiles/{id}`
- `PATCH /profiles/{id}`
- `GET /profiles/{id}/summary`
- `GET /profiles/{id}/activity`
- `GET /profiles/{id}/dashboard`
- `POST /profiles/{id}/feedback`
- `GET /profiles/{id}/feedback`
- `POST /profiles/{id}/recommend`
- `GET /profiles/{id}/recommendations`
- `GET /profiles/{id}/recommendations/{run_id}`
- `GET /profiles/{id}/saved-jobs`
- `GET /profiles/{id}/dismissed-jobs`
- `GET /profiles/{id}/applied-jobs`
- `POST /profiles/{id}/jobs/{job_id}/action`

`POST /recommend` now defaults to the internal processed corpus under `data/processed/jobs`.
`jobs_dir` is still supported as an override for testing, debugging, or focused evaluation runs.

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
  "include_debug": false,
  "eligible_only": false,
  "applyable_only": false,
  "top_k": 5
}
```

Useful notes:
- omit `jobs_dir` to use the internal refreshed corpus by default
- set `jobs_dir` only when you want to evaluate a specific source subset or local fixture directory
- `include_debug=true` adds raw score, blocker, match, and reranking fields back into each result
- `eligible_only=true` keeps only jobs with no blocking issues
- `applyable_only=true` keeps only jobs whose action label is not `Skip`

### Stored profile flow

Create a persisted profile:

```json
POST /profiles
{
  "profile_id": "user_001",
  "resume_text": "Python, machine learning, ranking systems",
  "degree_level": "Master's",
  "grad_date": "2027-12",
  "preferred_roles": ["Machine Learning Engineer Intern"],
  "preferred_locations": ["Remote", "California"],
  "target_industries": ["AI", "Tech"],
  "sponsorship_need": true,
  "extracted_skills": ["Python", "Machine Learning"],
  "years_of_experience": 1,
  "notes": "Interested in recommender systems"
}
```

Store feedback events for that profile:

```json
POST /profiles/user_001/feedback
{
  "profile_id": "user_001",
  "events": [
    {"job_id": "job_002", "feedback_label": "applied"},
    {"job_id": "job_005", "feedback_label": "saved"}
  ]
}
```

Request recommendations from the stored profile:

```json
POST /profiles/user_001/recommend
{
  "top_k": 10,
  "eligible_only": false,
  "applyable_only": false,
  "include_feedback": true,
  "exclude_dismissed": true,
  "include_debug": false,
  "save_run": true
}
```

List saved recommendation runs for that profile:

```json
GET /profiles/user_001/recommendations
```

Fetch a saved recommendation run snapshot:

```json
GET /profiles/user_001/recommendations/run_abc123
```

Useful notes:
- stored-profile APIs are currently scoped by `X-InternLens-User-Id`; when the header is absent, the backend uses `local_user` for local/demo compatibility
- set `INTERNLENS_AUTH_MODE=cognito` to require `Authorization: Bearer <Cognito JWT>` and derive the user scope from the token subject
- the browser app uses account-scoped `/me/...` endpoints so the user does not have to choose or type a profile ID
- stored-profile recommendation calls now save a run snapshot by default
- set `save_run=false` when you want a one-off recommendation without history
- saved runs let the app show prior recommendation sessions without recomputing immediately
- stored-profile recommendation calls suppress previously hidden jobs by default
- result items from stored-profile recommendations and saved run snapshots can include the latest `user_job_state`
- when `VITE_AUTH_MODE=cognito`, the frontend uses Cognito Hosted UI and sends the Cognito access token as a bearer token on API requests
- the frontend asks the API for a larger shortlist snapshot and paginates visible results in groups of 20, so users can review the full available result set without a long scrolling wall
- profile setup now uses searchable structured selectors for roles, skills, locations, and industries, with free-text background kept as optional context
- shortlist review includes search across company, role, location, matched skills, and skill gaps
- recommendation cards show detailed match evidence by default, and users can hide signals or open a job detail modal when needed
- visible skill gaps can be added back into profile skills directly from the recommendation card, then saved before the next shortlist run
- score explanations summarize matched skills, strong profile signals, and missing or unclear skill gaps in plain language
- unsaved profile changes are surfaced in a top-level banner so users know to save before rerunning matches
- component-level frontend tests now cover shortlist review defaults, hidden signal mode, profile readiness, job detail modal context, score explanations, and skill-gap action wiring

Save, apply, or hide a job from a stored-profile workflow:

```json
POST /profiles/user_001/jobs/job_a/action
{
  "action": "save",
  "run_id": "run_abc123"
}
```

Supported actions are:
- `save`: keep the role in the saved list
- `apply`: mark the role as applied
- `dismiss`: hide the role from future recommendation shortlists
- `clear`: undo the current saved, applied, or hidden state

Clear a previously saved, applied, or hidden state:

```json
POST /profiles/user_001/jobs/job_a/action
{
  "action": "clear"
}
```

Fetch a profile dashboard snapshot:

```json
GET /profiles/user_001/dashboard
```

The dashboard response combines:
- summary counts
- recent activity
- recent recommendation runs
- saved, applied, and hidden job previews

In the frontend, clicking the dashboard `Shortlists`, `Saved`, `Applied`, or `Hidden` count changes the lower review panel to the matching job set. Hidden jobs are not deleted; they are suppressed from future shortlists until the user chooses `Show again`.
The same review panel supports search, sorting, 20-item pagination, visible-by-default match signals with optional hiding, and a job detail modal backed by `GET /jobs/{job_id}`.

The frontend's account-scoped workflow calls these profile aliases:

```json
PUT /me/profile
GET /me/profile
GET /me/dashboard
POST /me/recommend
GET /me/recommendations/{run_id}
POST /me/jobs/{job_id}/action
GET /me/saved-jobs
GET /me/applied-jobs
GET /me/dismissed-jobs
```

These aliases map the signed-in account to an internal default profile and keep profile IDs out of the user-facing workflow. The older `/profiles/{profile_id}/...` endpoints remain available for CLI, tests, and developer compatibility.

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
- current total: `188 passed`
- frontend lint, tests, and build passing with `npm run lint`, `npm test -- --run`, and `npm run build`
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
- direct ATS probing improves source recall but can surface broad non-internship boards that still need validation and promotion thresholds
- promotion dry-runs now show internship signal examples, making false positives easier to inspect before registry changes
- promotion-candidate smoke reports now connect source promotion decisions to temporary fetch and ranking results
- blocked-page manual review records are operator cues, not promotion-ready source records
- `/recommend` still exposes `jobs_dir` for developer flexibility even though the default flow now uses the internal corpus
- the API still exposes `include_debug` because development and evaluation workflows need access to raw ranking fields
- the full source lifecycle is now scriptable, but it still depends on curated company seeds rather than broad autonomous discovery
- persisted user data is user-scoped and Cognito JWT validation is available, but single-server SQLite should be replaced with managed database persistence before real multi-user use

---

## Staging deployment

InternLens is deployed as a small AWS staging/demo environment, but it is not yet production hardened.

Current staging shape:
- frontend hosted with AWS Amplify Hosting
- FastAPI backend running on Elastic Beanstalk
- CloudFront in front of the backend to provide an HTTPS API endpoint
- backend release automation through CodePipeline and CodeBuild
- SQLite used only for single-server staging persistence
- source refresh and promotion scripts kept as manual operator actions, not public web actions

Current staging URLs:

```text
Frontend:
https://main.d1d00e49guhewo.amplifyapp.com

Backend HTTPS:
https://d187u93cen5bw8.cloudfront.net

Backend Elastic Beanstalk origin:
http://internlens-env.eba-dmbmusq3.us-east-2.elasticbeanstalk.com
```

The backend includes a `Procfile`:

```text
web: uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
```

Create the Elastic Beanstalk backend bundle from the repository root:

```bash
python scripts/package_eb.py
```

This writes `outputs/internlens_eb_backend.zip` with `Procfile`, `requirements.txt`, `src/`, and the current `data/processed/jobs` corpus at the zip root. `.ebignore` keeps local environments, frontend assets, tests, docs, raw snapshots, and generated output out of Beanstalk packaging.

The frontend deploy is configured with the root `amplify.yml`. Amplify uses `frontend` as the app root, runs `npm ci`, builds with `npm run build`, and publishes `dist`.

Backend deployment can be automated with AWS CodePipeline and CodeBuild using the repo-root `buildspec.yml`. The current staging pipeline is:

```text
GitHub main
  -> CodePipeline: internlens-backend-staging
  -> CodeBuild: internlens-backend-build
  -> Elastic Beanstalk: internlens / Internlens-env
```

The build runs the Python regression suite, validates the Elastic Beanstalk source bundle, and emits the Beanstalk runtime files as the CodeBuild output artifact. The Elastic Beanstalk deploy action must use the CodeBuild output artifact, not the original GitHub source artifact. The CodePipeline service role also needs Elastic Beanstalk deploy permissions, including `elasticbeanstalk:CreateApplicationVersion`.

Backend deploys are expected to run after changes are pushed to `main`. If the frontend is current but API behavior is stale, check the CodePipeline deploy status before changing frontend configuration.

For automatic weekly job-corpus refreshes, create a separate scheduled CodeBuild project that uses `buildspec.weekly-refresh.yml`.
That buildspec runs the public ATS refresh, packages the refreshed `data/processed/jobs` corpus into a backend bundle, uploads the bundle to S3, creates a new Elastic Beanstalk application version, and updates the staging environment.
Trigger it weekly with EventBridge Scheduler or an EventBridge rule; do not expose corpus refresh as a public API endpoint.

Required scheduled-refresh CodeBuild environment variables:

```text
EB_APPLICATION_NAME=internlens
EB_ENVIRONMENT_NAME=Internlens-env
EB_ARTIFACT_BUCKET=<s3-bucket-for-eb-source-bundles>
EB_ARTIFACT_PREFIX=internlens-backend
```

Current deployed environment values:

```text
AMPLIFY_MONOREPO_APP_ROOT=frontend
VITE_API_BASE_URL=https://d187u93cen5bw8.cloudfront.net
INTERNLENS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://main.d1d00e49guhewo.amplifyapp.com
```

Before deploying:

```bash
python -m pytest -q
cd frontend
npm run lint
npm test
npm run build
```

For details, see `docs/deployment/aws_staging.md`.

After deploying the backend, run:

```bash
python scripts/smoke_deployment.py --base-url https://d187u93cen5bw8.cloudfront.net --top-k 1000 --expect-auth-required
```

Latest Cognito-protected staging smoke passed against the CloudFront backend with health returning `200`, protected stored-profile access returning `401` without a bearer token, and the deployed OpenAPI schema showing `top_k` support up to `1000`.

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
- improve frontend empty states and error messages
- expand frontend tests from server-rendered component checks toward browser interaction coverage
- improve profile-save and shortlist-run guidance around unsaved changes
- continue refining ranking noise for broad non-core internships
- continue improving company, team, and location normalization
- measure source-discovery recall on larger seed subsets and use promotion-candidate smoke reports to judge quality
- refine source validation and promotion thresholds using dry-run signal examples and applyable ranking counts
- prepare cleaner demo documentation and screenshots
