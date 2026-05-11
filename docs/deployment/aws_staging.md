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
INTERNLENS_AUTH_MODE=dev
```

Notes:

- `INTERNLENS_CORS_ORIGINS` is comma-separated.
- Relative paths are resolved from the repository root.
- For one-server staging, SQLite is acceptable. For real multi-user production, move this to a managed database.
- In `dev` auth mode, stored-profile APIs support temporary user scoping with the `X-InternLens-User-Id` header.
- After creating a Cognito User Pool, set `INTERNLENS_AUTH_MODE=cognito` plus the Cognito variables below so the API requires `Authorization: Bearer <Cognito JWT>`.

```text
INTERNLENS_COGNITO_REGION=us-east-2
INTERNLENS_COGNITO_USER_POOL_ID=your-user-pool-id
INTERNLENS_COGNITO_APP_CLIENT_ID=your-app-client-id
```

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
INTERNLENS_AUTH_MODE=dev
```

Current Amplify environment variables:

```text
AMPLIFY_MONOREPO_APP_ROOT=frontend
VITE_API_BASE_URL=https://d187u93cen5bw8.cloudfront.net
VITE_AUTH_MODE=dev
```

After enabling Cognito login in staging, add:

```text
VITE_AUTH_MODE=cognito
VITE_COGNITO_REGION=us-east-2
VITE_COGNITO_USER_POOL_ID=us-east-2_SV9to18Q1
VITE_COGNITO_APP_CLIENT_ID=e0p7dlk90s9bnbtqi4jvhi18i
```

Then set matching backend environment properties:

```text
INTERNLENS_AUTH_MODE=cognito
INTERNLENS_COGNITO_REGION=us-east-2
INTERNLENS_COGNITO_USER_POOL_ID=us-east-2_SV9to18Q1
INTERNLENS_COGNITO_APP_CLIENT_ID=e0p7dlk90s9bnbtqi4jvhi18i
```

The frontend requests only the `openid email` scopes so it works with the default Cognito quick-start app client.

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

## Automated Backend Deployment with CodePipeline

The frontend already deploys automatically through Amplify when `main` changes.
The backend can be brought into the same push-driven workflow with CodePipeline and CodeBuild:

```text
GitHub main push
  -> CodePipeline source stage
  -> CodeBuild test/package stage
  -> Elastic Beanstalk deploy stage
```

The repository root includes `buildspec.yml` for this backend pipeline.
It does two things:

- runs `python -m pytest -q`
- runs `python scripts/package_eb.py` as a source-bundle validation check

The CodeBuild output artifact is intentionally not `outputs/internlens_eb_backend.zip`.
CodePipeline packages the selected artifact files for the next action, so the artifact should expose the Beanstalk source-bundle layout directly:

```text
Procfile
requirements.txt
src/**/*
data/processed/jobs/**/*
```

### Console setup checklist

1. Open AWS CodePipeline in `us-east-2`.
2. Create a pipeline named something like `internlens-backend-staging`.
3. Choose or create a service role for CodePipeline.
4. Choose GitHub as the source provider and connect the `InternLens` repository.
5. Select the `main` branch.
6. Add a build stage using AWS CodeBuild.
7. Create a CodeBuild project named something like `internlens-backend-build`.
8. Use a managed Linux image with Python available.
9. Set the buildspec path to the repo-root default `buildspec.yml`.
10. Keep the primary build artifact as the build output artifact.
11. Add a deploy stage using Elastic Beanstalk.
12. Select the existing Elastic Beanstalk application and the `internlens-env` environment.
13. Use the CodeBuild output artifact as the deploy input artifact, not the original GitHub source artifact.
14. Save the pipeline and run it once manually.

### Required Elastic Beanstalk environment variables

For Cognito-backed staging auth, the Beanstalk environment must have:

```text
INTERNLENS_AUTH_MODE=cognito
INTERNLENS_COGNITO_REGION=us-east-2
INTERNLENS_COGNITO_USER_POOL_ID=us-east-2_SV9to18Q1
INTERNLENS_COGNITO_APP_CLIENT_ID=e0p7dlk90s9bnbtqi4jvhi18i
INTERNLENS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://main.d1d00e49guhewo.amplifyapp.com
```

After the first successful pipeline deployment, verify that the backend is running the latest code:

```powershell
$body = @{
  top_k = 1000
  include_feedback = $true
  exclude_dismissed = $true
  exclude_applied = $true
  include_debug = $true
  save_run = $true
} | ConvertTo-Json -Compress

Invoke-WebRequest `
  -Uri "https://d187u93cen5bw8.cloudfront.net/profiles/user_001/recommend" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

If Cognito mode is active, unauthenticated stored-profile calls should return `401`.
If `top_k=1000` still returns `422`, the Beanstalk environment is still running an older backend build.

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
For Cognito-protected staging without a test bearer token, validate health, auth enforcement, and deployed `top_k` schema with:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_deployment.py --base-url https://your-backend-host.example --top-k 1000 --expect-auth-required --output-file outputs\deployment_smoke_staging_auth.json
```

Generated deployment smoke reports under `outputs/deployment_smoke*.json` are ignored by git.

Latest CloudFront backend auth smoke:

```text
Base URL: https://d187u93cen5bw8.cloudfront.net
Profile ID: smoke_deploy_user
Overall: passed
- health: 200
- auth_required: 401
- openapi_schema: 200
Returned jobs: None
```

## Current Staging Limitations

- Cognito authentication mode is implemented, but staging should still be treated as a demo environment until auth rollout, callback/logout URLs, and operational settings are reviewed together.
- `X-InternLens-User-Id` remains only a development bridge for `INTERNLENS_AUTH_MODE=dev`.
- SQLite is still single-host prototype persistence, though the schema now scopes rows by user.
- Corpus refresh is not isolated as a separate scheduled worker.
- Generated raw/processed data can be large; avoid rewriting data directories during deploy.
- CORS should be restricted to the deployed frontend URL, not left broad.
- Frontend deploys are automatic from `main` through Amplify.
- Backend code or corpus changes should deploy through the `internlens-backend-staging` CodePipeline; if the frontend is current but API behavior is stale, check Source, Build, and Deploy status there first.
