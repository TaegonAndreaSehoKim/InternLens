# Week 5 Devlog

Week 5 covers Day 34-41.
The focus shifted from local UI polish to staging deployment readiness and an actual AWS-hosted demo path.

## Day 34 - Dashboard UI Density and Activity Surface

### Focus
Improve the local frontend from a demo landing-style page into a denser application workspace.

### What was done
- Reduced the oversized hero treatment and replaced it with a smaller app-style header.
- Added dashboard activity rendering from the existing `/profiles/{id}/dashboard` response.
- Added compact timestamp and activity-label helpers.
- Added recent-run timestamps in the dashboard.
- Added more visible recommendation-card details for:
  - eligibility status
  - recommendation code
  - source recommendation run for persisted job state
- Tightened visual spacing, card radius, and dashboard layout density.
- Added frontend tests for dashboard display helpers.

### Validation
- `npm run lint` -> passed
- `npm test` -> **6 passed**
- `npm run build` -> passed
- `pytest tests/test_profile_api.py -q` -> **24 passed**

### Result
The frontend now feels more like an operational application board and less like a landing page.
The dashboard uses more backend state already available through the API, especially activity history and recent run metadata.

---

## Day 35 - Staging Deployment Readiness

### Focus
Prepare InternLens for a small AWS-style staging/demo deployment without claiming production readiness.

### What was done
- Added backend configuration helpers under `src/api/settings.py`.
- Environment-variable controls now cover:
  - `INTERNLENS_CORS_ORIGINS`
  - `INTERNLENS_JOBS_DIR`
  - `INTERNLENS_DB_PATH`
- Kept local defaults intact for current development workflows.
- Added support for relative or absolute configured paths.
- Added `.env.example` and `frontend/.env.example`.
- Added a backend `Procfile` for hosts that support process declarations.
- Added `docs/deployment/aws_staging.md` with first-cut AWS staging guidance.
- Updated README with staging environment variables and deployment notes.
- Added API settings tests.

### Validation
- `pytest tests/test_api_settings.py tests/test_api_and_ranking.py tests/test_profile_api.py -q` -> **50 passed**
- `npm run lint` -> passed
- `npm test` -> **6 passed**
- `npm run build` -> passed
- `pytest -q` -> **171 passed**

### Result
The project became ready for a controlled staging deployment pass.
The recommended first deployment shape was:
- frontend on AWS Amplify Hosting
- FastAPI backend on Elastic Beanstalk
- SQLite only for single-server staging
- source refresh and promotion kept as operator-run scripts

---

## Day 36 - Deployment Smoke Script and Packaging

### Focus
Make deployed API verification and Elastic Beanstalk packaging repeatable.

### What was done
- Added `scripts/smoke_deployment.py`.
- The smoke script verifies the stored-profile product flow against a running API base URL:
  - `GET /health`
  - `POST /profiles` or `GET /profiles/{id}` when the smoke profile already exists
  - `POST /profiles/{id}/recommend`
  - `GET /profiles/{id}/dashboard`
- Added optional JSON report output under ignored `outputs/deployment_smoke*.json`.
- Added tests with a fake HTTP client.
- Added `.ebignore`.
- Added `scripts/package_eb.py` to create an Elastic Beanstalk backend source bundle.
- Added tests for the package script.
- Added root `amplify.yml` for the frontend monorepo build.
- Documented the commands in README and `docs/deployment/aws_staging.md`.

### Validation
- `pytest tests/test_smoke_deployment.py -q` -> **3 passed**
- `pytest tests/test_package_eb.py -q` -> **3 passed**
- `.\.venv\Scripts\python.exe scripts\package_eb.py` -> created `outputs/internlens_eb_backend.zip`
- `pytest -q` -> **177 passed**
- `npm run lint` -> passed
- `npm test` -> **6 passed**
- `npm run build` -> passed

### Result
InternLens gained a reusable smoke check and a repeatable backend packaging path for staging deploys.
The backend source bundle contains runtime backend files and the processed job corpus at the zip root.

---

## Day 37 - AWS Staging Deployment Completion

### Focus
Deploy the prototype to AWS and verify the browser-to-backend flow end to end.

### What was done
- Set up the AWS account safety baseline:
  - MFA enabled
  - Budget alerts configured
  - region kept at `us-east-2`
- Deployed the backend through Elastic Beanstalk:
  - application: `internlens`
  - environment: `Internlens-env`
  - platform: Python on Amazon Linux 2023
  - process command from `Procfile`
- Added backend environment properties:
  - `INTERNLENS_JOBS_DIR=data/processed/jobs`
  - `INTERNLENS_DB_PATH=data/app/internlens.db`
  - `INTERNLENS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://main.d1d00e49guhewo.amplifyapp.com`
- Added a CloudFront distribution in front of the Beanstalk backend so the API has an HTTPS endpoint.
- Verified the HTTPS backend with the deployment smoke script.
- Deployed the frontend through AWS Amplify Hosting.
- Set Amplify build environment variables:
  - `AMPLIFY_MONOREPO_APP_ROOT=frontend`
  - `VITE_API_BASE_URL=https://d187u93cen5bw8.cloudfront.net`
- Redeployed the Amplify frontend after environment-variable changes.
- Verified the deployed frontend could run the InternLens workflow against the HTTPS backend.

### Staging endpoints
- Frontend: `https://main.d1d00e49guhewo.amplifyapp.com`
- Backend HTTPS: `https://d187u93cen5bw8.cloudfront.net`
- Backend Beanstalk origin: `http://internlens-env.eba-dmbmusq3.us-east-2.elasticbeanstalk.com`

### Smoke result

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

### Result
InternLens is now reachable as a staged web app.
The deployed frontend can call the deployed backend over HTTPS, and the backend smoke flow confirms health, profile creation, recommendation execution, and dashboard retrieval.

---

## Day 38 - Dashboard Job-State UX Cleanup

### Focus
Make the dashboard and current shortlist behave more like a user-facing application board instead of exposing internal run and job-state mechanics.

### What was done
- Simplified the top-right frontend server status to online/offline style messaging.
- Renamed profile setup labels to more user-facing language:
  - `Candidate signal` -> `Candidate information`
  - `Profile ID` -> `User ID`
- Switched graduation input to a month picker and degree to a dropdown.
- Removed internal-looking dashboard identifiers from recent activity and recent shortlist cards.
- Changed activity labels from raw recommendation/run language to `Shortlist`, `Saved`, `Applied`, and `Hidden`.
- Added an activity scroll area so long histories do not stretch the whole page.
- Formatted activity job references as readable company/title/term text when snapshot data is available.
- Renamed `Dismiss` to `Hide role` and clarified that hidden roles are suppressed from future shortlists.
- Added immediate state feedback in recommendation cards:
  - `Mark applied` becomes `Undo applied`
  - `Hide role` becomes `Show again`
- Made saved run numbering stable, with earlier shortlists getting lower numbers while the newest shortlist stays at the top.
- Made dashboard summary counts clickable so `Shortlists`, `Saved`, `Applied`, and `Hidden` can drive the lower review panel.
- Added backend support for returning hidden job previews in the dashboard.
- Updated saved run retrieval so old shortlist snapshots are annotated with the latest saved/applied/hidden state.

### Validation
- `npm run lint` -> passed
- `npm test` -> **8 passed**
- `npm run build` -> passed
- `pytest tests/test_profile_api.py -q` -> **24 passed**
- `pytest -q` -> **177 passed**

### Result
The dashboard now gives clearer feedback after job actions and provides a direct way to review saved, applied, and hidden jobs.
Hidden jobs are now framed as a reversible shortlist suppression action rather than an ambiguous dismissal.

---

## Day 39 - User-Scoped Persistence Foundation

### Focus
Start the account-system migration by making stored workflow data separable by user before adding Cognito.

### What was done
- Added a `user_id` scope to persisted profiles, feedback events, recommendation runs, and job states.
- Kept local/demo compatibility through a default `local_user` scope.
- Added migration logic so older local SQLite databases are copied into the `local_user` scope.
- Allowed the API to accept `X-InternLens-User-Id` as a temporary development boundary for user-scoped requests.
- Added tests proving the same `profile_id` can exist separately for different user ids.
- Added API tests proving feedback and profile data do not leak across user headers.

### Validation
- `pytest tests/test_profile_store.py tests/test_profile_api.py -q` -> **28 passed**
- `pytest -q` -> **179 passed**

### Result
The backend storage model is now ready for real account integration.
The next production step is to replace the temporary user header with Cognito JWT validation and move persistence from single-host SQLite to RDS PostgreSQL.

---

## Day 40 - Cognito Auth Boundary Scaffold

### Focus
Prepare the backend to accept real Cognito tokens while keeping local/demo development unblocked.

### What was done
- Added `src/api/auth.py` for API user resolution.
- Added `INTERNLENS_AUTH_MODE` with two modes:
  - `dev`: use `X-InternLens-User-Id` or fall back to `local_user`
  - `cognito`: require `Authorization: Bearer <Cognito JWT>`
- Added Cognito JWT verification settings:
  - `INTERNLENS_COGNITO_REGION`
  - `INTERNLENS_COGNITO_USER_POOL_ID`
  - `INTERNLENS_COGNITO_APP_CLIENT_ID`
- Added JWT signature verification through Cognito JWKS.
- Validated token issuer, token type, app client, and subject extraction.
- Added auth unit tests for dev mode, missing Cognito token rejection, and Cognito subject extraction.

### Validation
- `pytest tests/test_api_auth.py tests/test_profile_store.py tests/test_profile_api.py -q` -> **31 passed**

### Result
The API now has a clean place to switch from development user scoping to real Cognito-backed account identity.
The remaining account-system work is mostly AWS Cognito setup and frontend login/session integration.

---

## Day 41 - Frontend Cognito Login Scaffold

### Focus
Connect the React frontend to the Cognito OIDC flow while keeping local development in demo mode by default.

### What was done
- Added `react-oidc-context` and `oidc-client-ts`.
- Added frontend auth environment variables:
  - `VITE_AUTH_MODE`
  - `VITE_COGNITO_REGION`
  - `VITE_COGNITO_USER_POOL_ID`
  - `VITE_COGNITO_APP_CLIENT_ID`
- Added a sign-in gate for `VITE_AUTH_MODE=cognito`.
- Configured Cognito authority, client id, redirect URI, logout redirect URI, authorization code flow, and `openid email` OIDC scopes.
- Added bearer-token attachment to stored-profile API calls.
- Added signed-in account display and sign-out action in the app header.
- Kept `VITE_AUTH_MODE=dev` as the default so the current local/demo workflow remains available.

### Validation
- `npm run lint` -> passed
- `npm test` -> **8 passed**
- `npm run build` -> passed
- `pytest tests/test_api_auth.py tests/test_profile_store.py tests/test_profile_api.py -q` -> **31 passed**

### Result
The frontend is now ready to use the created Cognito User Pool once Amplify and Elastic Beanstalk environment variables are switched from `dev` to `cognito`.

---

## Week 5 Snapshot

### Current project state
- Local development remains supported.
- Backend packaging and deployment smoke checks are repeatable.
- AWS staging deployment is live.
- Frontend is hosted through Amplify.
- Backend is hosted through Elastic Beanstalk and exposed over HTTPS through CloudFront.
- Dashboard job actions now have clearer user-facing labels and reversible state transitions.
- The dashboard can show shortlist, saved, applied, and hidden job views from the summary counts.
- Stored workflow data is now user-scoped in preparation for Cognito-backed accounts.
- Backend auth can now run in development header mode or Cognito JWT mode.
- Frontend auth can now run in development mode or Cognito Hosted UI mode.

### Week 5 quality checkpoint
- Backend tests: **182 passed**
- Frontend checks:
  - `npm run lint` -> passed
  - `npm test` -> **8 passed**
  - `npm run build` -> passed
- Deployment smoke against CloudFront backend: passed.

### Remaining next steps
- Verify the staging Cognito rollout before treating authentication as production-ready.
- Move persistence off single-host SQLite to RDS PostgreSQL before real multi-user use.
- Decide whether to add a custom domain for frontend and API.
- Add a short demo walkthrough or screenshots for presentation use.
- Keep iterating on frontend empty states, error states, and dashboard copy.
