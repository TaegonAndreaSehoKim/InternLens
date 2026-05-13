# Week 7 Devlog

Week 7 focused on closing the staging deployment loop, making the account-based browser workflow less profile-ID-driven, and improving Profile Setup so recommendation inputs are structured instead of relying on free-form text.

---

## Day 45 - Backend Pipeline Verification and Auth Smoke Checks

### Focus
Confirm that backend changes are actually reaching staging and make deployment smoke checks useful after Cognito protection is enabled.

### What was done
- Added `buildspec.yml` for the backend CodePipeline/CodeBuild path.
- Documented the staging pipeline in README:
  - `internlens-backend-staging`
  - `internlens-backend-build`
  - Elastic Beanstalk `internlens / Internlens-env`
- Fixed the CodePipeline deploy permission issue by adding Elastic Beanstalk deploy permissions to the CodePipeline service role.
- Verified the deployed CloudFront backend showed the newer OpenAPI schema with `top_k` maximum `1000`.
- Confirmed Cognito-protected endpoints return `401` without a bearer token.
- Extended `scripts/smoke_deployment.py` with:
  - `--expect-auth-required`
  - `--bearer-token`
  - OpenAPI schema validation for protected staging smoke checks.

### Result
The project now has a repeatable backend release path and a smoke test mode that works for Cognito-protected staging without needing to create an unauthenticated test profile.

---

## Day 46 - Account-Scoped Browser Workflow

### Focus
Remove user-facing profile IDs from the browser flow and make account data use the authenticated user boundary.

### What was done
- Added account-scoped API aliases:
  - `PUT /me/profile`
  - `GET /me/profile`
  - `GET /me/dashboard`
  - `POST /me/recommend`
  - `GET /me/recommendations/{run_id}`
  - `POST /me/jobs/{job_id}/action`
  - `/me/saved-jobs`, `/me/applied-jobs`, `/me/dismissed-jobs`
- Mapped the signed-in account to an internal default profile ID so the browser no longer needs `profile_id` input or storage.
- Kept existing `/profiles/{profile_id}/...` endpoints for tests, CLI compatibility, and development workflows.
- Updated the frontend to call `/me/...` endpoints.
- Added API tests for account-scoped profile, recommendation, job action, dashboard, and saved-job flows.

### Validation
- `pytest -q` -> **188 passed**
- `npm run lint` -> passed
- `npm test -- --run` -> **8 passed**
- `npm run build` -> passed

### Result
The browser workflow now behaves like an account-based product instead of a profile-ID demo.

---

## Day 47 - Profile Setup and Recommendation UX Polish

### Focus
Reduce confusing UI states and make recommendation cards easier to understand.

### What was done
- Added Profile Setup state messaging:
  - not saved yet
  - saved to this account
  - unsaved changes
- Restored the signed-in account profile from `/me/profile` into the form instead of relying on local storage defaults.
- Blocked `Find matches` when the current form has unsaved changes.
- Improved recommendation cards with:
  - a plain fit summary
  - matched-skill chips
  - combined `why_apply` and `reasons`
  - `What to check` instead of raw watchout wording
- Kept job action UX improvements for saved, applied, hidden, and undo states.

### Result
The app now gives clearer feedback about which profile is being used and why each recommendation appears.

---

## Day 48 - Structured Profile Inputs

### Focus
Stop relying on users to write ideal free-form profile text and collect cleaner ranking signals.

### What was done
- Replaced broad text inputs for roles, skills, locations, and industries with structured multi-select flows.
- Added a Profile quality checklist:
  - target role selected
  - core skills selected
  - location preference selected
  - education timeline set
  - background context added
  - industry preference added
- Made required checklist items gate profile saving and recommendation runs.
- Changed the default profile form from demo-filled values to empty values so users do not accidentally save a generic profile.
- Moved `Resume text` into optional `Additional background`.
- Reworked the selector UI from always-visible chip groups into searchable multi-select fields:
  - selected items stay visible as compact chips
  - suggestions appear only after typing
  - unmatched entries can be added as custom values
- Expanded role, skill, location, and industry suggestions beyond computer engineering:
  - design, UX, marketing, sales, finance, operations, supply chain
  - HR, legal, healthcare, biotech, policy, education, nonprofit
  - sustainability, communications, journalism, and broader engineering fields

### Validation
- `npm run lint` -> passed
- `npm test -- --run` -> **8 passed**
- `npm run build` -> passed

### Result
Profile Setup is now more structured, less noisy on screen, and better prepared for candidates outside the CS/data track.

---

## Day 49 - Shortlist Review Workflow Polish

### Focus
Make the shortlist review surface easier to scan without hiding the explanation data that makes ranking trustworthy.

### What was done
- Added search to the shortlist review panel across:
  - company
  - role title
  - location
  - matched skills
  - skill gaps
- Kept recommendation cards compact by default and moved detailed evidence behind `Show signals`.
- Added expandable card sections for:
  - matched skills
  - skill gaps
  - eligibility notes
  - match breakdown
  - fit and watchout evidence
- Added direct skill-gap actions so a visible missing skill can be added to profile skills from the recommendation card.
- Added a job detail modal backed by `GET /jobs/{job_id}` with:
  - summary
  - requirements
  - preferred qualifications
  - internship signals
  - possible blockers
  - source freshness
  - apply/source links
- Simplified the Profile quality card into a `Matching readiness` summary, with optional and completed details collapsed.
- Removed an unused frontend selector component while making lint part of the validation pass.

### Validation
- `npm run lint` -> passed
- `npm test -- --run` -> **15 passed**
- `npm run build` -> passed

### Result
Shortlist review now behaves more like a working application board: compact by default, searchable, explainable on demand, and actionable when the user sees a skill gap.

---

## Week 7 Snapshot

### Current project state
- Backend staging deployment is automated through CodePipeline and CodeBuild.
- Cognito-protected staging smoke checks can validate health, auth enforcement, and deployed schema.
- The frontend uses `/me/...` account-scoped APIs for the main browser workflow.
- Profile Setup collects structured recommendation signals through searchable selectors.
- Recommendation cards explain matches more clearly with fit summaries, matched skills, skill gaps, expandable signals, job detail lookup, and check items.
- Shortlist review supports search, sorting, 20-item pagination, expandable match evidence, and account-scoped job actions.

### Latest quality checkpoint
- Backend tests: **188 passed**
- Frontend checks:
  - `npm run lint` -> passed
  - `npm test -- --run` -> **15 passed**
  - `npm run build` -> passed

### Remaining next steps
- Continue tightening ranking precision for broader non-CS candidate profiles.
- Review whether the profile taxonomy should move from hardcoded frontend constants to a shared config file.
- Add component-level frontend tests for the shortlist review panel, job detail modal, and profile setup interactions.
- Improve dashboard copy and empty states now that profile setup and shortlist review are less free-form.
- Plan managed database migration before treating multi-user persistence as production-ready.
