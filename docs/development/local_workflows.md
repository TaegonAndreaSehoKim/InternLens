# Local Workflows

This document keeps detailed setup, source-refresh, CLI, API, and validation commands out of the top-level README.

Run commands from the repository root unless a section says otherwise.

## Install

Backend dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Frontend dependencies:

```powershell
cd frontend
npm install
```

## Run Locally

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload
```

Frontend:

```powershell
cd frontend
npm run dev
```

Default local backend URL:

```text
http://127.0.0.1:8000
```

Default local frontend URL:

```text
http://127.0.0.1:5173
```

## Environment Variables

Common backend variables:

```text
INTERNLENS_AUTH_MODE=dev
INTERNLENS_DB_PATH=data/app/internlens.db
INTERNLENS_JOBS_DIR=data/processed/jobs
INTERNLENS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

For Cognito-backed local testing:

```text
INTERNLENS_AUTH_MODE=cognito
INTERNLENS_COGNITO_REGION=us-east-2
INTERNLENS_COGNITO_USER_POOL_ID=us-east-2_SV9to18Q1
INTERNLENS_COGNITO_APP_CLIENT_ID=e0p7dlk90s9bnbtqi4jvhi18i
```

Common frontend variables:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_AUTH_MODE=dev
```

For Cognito-backed frontend testing:

```text
VITE_AUTH_MODE=cognito
VITE_COGNITO_REGION=us-east-2
VITE_COGNITO_USER_POOL_ID=us-east-2_SV9to18Q1
VITE_COGNITO_APP_CLIENT_ID=e0p7dlk90s9bnbtqi4jvhi18i
```

## Source Refresh

Refresh active Lever and Greenhouse registry targets:

```powershell
.\.venv\Scripts\python.exe scripts\refresh_job_corpus.py
```

Useful variants:

```powershell
.\.venv\Scripts\python.exe scripts\refresh_job_corpus.py --greenhouse-only
.\.venv\Scripts\python.exe scripts\refresh_job_corpus.py --lever-only
.\.venv\Scripts\python.exe scripts\refresh_job_corpus.py --timeout 180
.\.venv\Scripts\python.exe scripts\refresh_job_corpus.py --include-inactive
.\.venv\Scripts\python.exe scripts\refresh_job_corpus.py --greenhouse-all-jobs
```

Fetch active registry targets directly:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_lever_registry.py --only-active
.\.venv\Scripts\python.exe scripts\fetch_greenhouse_registry.py --only-active --internship-only
```

Run the full source lifecycle:

```powershell
.\.venv\Scripts\python.exe scripts\run_source_pipeline.py
```

Useful source-pipeline options:

```powershell
.\.venv\Scripts\python.exe scripts\run_source_pipeline.py --skip-discovery
.\.venv\Scripts\python.exe scripts\run_source_pipeline.py --skip-validation
.\.venv\Scripts\python.exe scripts\run_source_pipeline.py --skip-promotion
.\.venv\Scripts\python.exe scripts\run_source_pipeline.py --skip-refresh
.\.venv\Scripts\python.exe scripts\run_source_pipeline.py --refresh-limit 25
```

Discovery/promotion tools:

```powershell
.\.venv\Scripts\python.exe scripts\discover_sources.py
.\.venv\Scripts\python.exe scripts\validate_sources.py
.\.venv\Scripts\python.exe scripts\promote_sources.py --dry-run
.\.venv\Scripts\python.exe scripts\compare_discovery_recall.py
.\.venv\Scripts\python.exe scripts\smoke_promotion_candidates.py
```

Source promotion should stay operator-reviewed. Do not auto-promote broad discovered boards without inspecting dry-run output.

## Baseline Ranking CLI

Run on sample jobs:

```powershell
.\.venv\Scripts\python.exe scripts\run_baseline.py
```

Run on processed jobs:

```powershell
.\.venv\Scripts\python.exe scripts\run_baseline.py --jobs-dir data\processed\jobs
```

Run on a specific source:

```powershell
.\.venv\Scripts\python.exe scripts\run_baseline.py --jobs-dir data\processed\jobs\greenhouse\waymo
.\.venv\Scripts\python.exe scripts\run_baseline.py --jobs-dir data\processed\jobs\greenhouse\cloudflare
```

Shortlist-style filters:

```powershell
.\.venv\Scripts\python.exe scripts\run_baseline.py --eligible-only
.\.venv\Scripts\python.exe scripts\run_baseline.py --applyable-only
.\.venv\Scripts\python.exe scripts\run_baseline.py --eligible-only --applyable-only
.\.venv\Scripts\python.exe scripts\run_baseline.py --applyable-only --suppress-similar-results
```

## API Workflow

Health:

```http
GET /health
```

Account-scoped browser aliases:

```http
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

Developer profile endpoints:

```http
PUT /profiles/{profile_id}
GET /profiles/{profile_id}
GET /profiles/{profile_id}/dashboard
POST /profiles/{profile_id}/recommend
GET /profiles/{profile_id}/recommendations
GET /profiles/{profile_id}/recommendations/{run_id}
POST /profiles/{profile_id}/jobs/{job_id}/action
```

Job detail:

```http
GET /jobs/{job_id}
```

Stored-profile recommendation requests save run snapshots by default. Use `save_run=false` for one-off requests.

Job action payload:

```json
{
  "action": "save",
  "run_id": "run_abc123"
}
```

Supported actions:

- `save`
- `apply`
- `dismiss`
- `clear`

Hidden jobs are suppressed from future shortlists until the user clears the hidden state.

## Deployment Smoke

Unauthenticated staging auth/schema smoke:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_deployment.py --base-url https://d187u93cen5bw8.cloudfront.net --top-k 1000 --expect-auth-required --output-file outputs\deployment_smoke_staging_auth.json
```

If you have a Cognito bearer token, pass it with:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_deployment.py --base-url https://d187u93cen5bw8.cloudfront.net --bearer-token <token> --output-file outputs\deployment_smoke_staging.json
```

Generated deployment smoke reports under `outputs/deployment_smoke*.json` are ignored by git.

## Validation

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Useful targeted tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_and_ranking.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_profile_api.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_jobs_api.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_run_source_pipeline.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_package_eb.py tests/test_weekly_refresh_buildspec.py -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm test -- --run
npm run build
```

## Generated Data Guidance

Be careful around:

- `data/raw`
- `data/processed/jobs`
- `outputs`
- `data/app`

`data/app` contains local SQLite data and should not be committed.

Generated raw/processed job data may be useful for demos, but it can be large and noisy. Avoid broad regeneration unless the task explicitly calls for it.
