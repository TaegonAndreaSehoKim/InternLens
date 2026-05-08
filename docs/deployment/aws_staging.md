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

## Elastic Beanstalk Backend Package

The backend deploy artifact should contain only the runtime backend files and the staging job corpus:

```text
Procfile
requirements.txt
src/
data/processed/jobs/
```

Do not upload the repository parent directory as the top-level folder inside the zip. Elastic Beanstalk expects the bundle root to contain files such as `Procfile` and `requirements.txt` directly.

Create the backend source bundle from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\package_eb.py
```

The default output is:

```text
outputs/internlens_eb_backend.zip
```

Use a code-only bundle only if `INTERNLENS_JOBS_DIR` is populated on the instance by another process:

```powershell
.\.venv\Scripts\python.exe scripts\package_eb.py --without-jobs
```

The repository also includes `.ebignore` so EB CLI packaging skips local environments, frontend files, tests, docs, raw snapshots, registries, and generated output.

## Elastic Beanstalk Console Flow

Use the same AWS region selected for the account setup, currently `us-east-2`.

1. Open Elastic Beanstalk.
2. Choose **Create application**.
3. Application name: `internlens`.
4. Environment tier: **Web server environment**.
5. Environment name: `internlens-staging`.
6. Platform: **Python**.
7. Application code: **Upload your code**.
8. Upload `outputs/internlens_eb_backend.zip`.
9. Presets: **Single instance** for the first staging deployment.
10. Do not attach an RDS database for the first cut.
11. Add the backend environment variables from this document before or immediately after environment creation.

After creation, open the environment URL and check:

```text
http://your-elastic-beanstalk-url/health
```

The expected response is a small JSON health payload.

## Current Staging Deployment

The current staging deployment was completed on May 7, 2026.

```text
Frontend:
https://main.d1d00e49guhewo.amplifyapp.com

Backend HTTPS:
https://d187u93cen5bw8.cloudfront.net

Backend Elastic Beanstalk origin:
http://internlens-env.eba-dmbmusq3.us-east-2.elasticbeanstalk.com
```

Current backend environment properties:

```text
INTERNLENS_JOBS_DIR=data/processed/jobs
INTERNLENS_DB_PATH=data/app/internlens.db
INTERNLENS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://main.d1d00e49guhewo.amplifyapp.com
```

Current Amplify environment variables:

```text
AMPLIFY_MONOREPO_APP_ROOT=frontend
VITE_API_BASE_URL=https://d187u93cen5bw8.cloudfront.net
```

CloudFront is used in front of the single-instance Elastic Beanstalk backend to provide an HTTPS API endpoint for the Amplify-hosted frontend.
The CloudFront origin is the Beanstalk environment domain over HTTP, with caching disabled and all API methods allowed.

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

For the current Amplify deployment, the root `amplify.yml` uses `appRoot: frontend`, runs `npm ci`, then `npm run build`, and publishes `dist`.
Pushing to `main` triggers the Amplify frontend build automatically, so frontend-only changes generally do not require a separate AWS console deployment step.

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

Create the backend source bundle:

```powershell
.\.venv\Scripts\python.exe scripts\package_eb.py
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

Latest CloudFront backend smoke:

```text
Base URL: https://d187u93cen5bw8.cloudfront.net
Profile ID: smoke_deploy_user
Overall: passed
- health: 200
- profile: 201
- recommend: 200
- dashboard: 200
Returned jobs: 3
```

## Current Staging Limitations

- No authentication yet.
- SQLite is single-host prototype persistence.
- Corpus refresh is not isolated as a separate scheduled worker.
- Generated raw/processed data can be large; avoid rewriting data directories during deploy.
- CORS should be restricted to the deployed frontend URL, not left broad.
- Frontend deploys are automatic from `main`, but backend code or corpus changes still require a new Elastic Beanstalk bundle/upload.
