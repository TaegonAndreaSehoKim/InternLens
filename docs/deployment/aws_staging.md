# AWS Staging Deployment Notes

## Goal

This is a staging/demo deployment path for InternLens, not a production architecture.
The goal is to make the current prototype reachable from a browser while keeping source refresh and registry promotion controlled manually.

## Recommended First Cut

- Frontend: AWS Amplify Hosting, or S3 plus CloudFront
- Backend: Elastic Beanstalk Python platform, Lightsail, or a small EC2 instance
- Persistence: SQLite on the backend host for staging only
- Corpus: include `data/processed/jobs` with the backend deploy artifact, or copy it onto the host before starting the API
- Source refresh: run manually from a trusted operator machine or backend shell, not as a public endpoint

## Backend Environment

Set these variables in the backend hosting environment:

```text
INTERNLENS_CORS_ORIGINS=https://your-frontend-host.example
INTERNLENS_JOBS_DIR=data/processed/jobs
INTERNLENS_DB_PATH=data/app/internlens.db
```

Notes:

- `INTERNLENS_CORS_ORIGINS` is comma-separated.
- Relative paths are resolved from the repository root.
- For one-server staging, SQLite is acceptable. For real multi-user production, move this to a managed database.

## Frontend Environment

Set this before building the frontend:

```text
VITE_API_BASE_URL=https://your-backend-host.example
```

Then build:

```powershell
cd frontend
npm install
npm run build
```

Deploy `frontend/dist` through Amplify Hosting or S3/CloudFront.

## Backend Start Command

For a Linux host or Elastic Beanstalk environment that supports `Procfile`, the repository includes:

```text
web: uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000}
```

Manual start command:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

Linux equivalent:

```bash
python -m uvicorn src.api.app:app --host 0.0.0.0 --port "${PORT:-8000}"
```

## Pre-Deploy Checklist

Run locally before packaging:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run lint
npm test
npm run build
```

Smoke the backend after deploy:

```text
GET /health
POST /profiles
POST /profiles/{profile_id}/recommend
GET /profiles/{profile_id}/dashboard
```

Or run the deployment smoke script:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_deployment.py --base-url https://your-backend-host.example --output-file outputs\deployment_smoke_staging.json
```

The smoke script creates or loads a test profile, runs stored-profile recommendations, and fetches the dashboard snapshot.
Generated deployment smoke reports under `outputs/deployment_smoke*.json` are ignored by git.

## Current Staging Limitations

- No authentication yet.
- SQLite is single-host prototype persistence.
- Corpus refresh is not isolated as a separate scheduled worker.
- Generated raw/processed data can be large; avoid rewriting data directories during deploy.
- CORS should be restricted to the deployed frontend URL, not left broad.
