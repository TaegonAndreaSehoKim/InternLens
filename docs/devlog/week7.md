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

## Day 50 - Visible Signals and Frontend Component Coverage

### Focus
Restore recommendation-card transparency while keeping the newer shortlist workflow test-backed.

### What was done
- Changed recommendation cards so match signals are visible by default again.
- Kept `Hide signals` as the optional action for users who want a more compact card.
- Added plain-language score explanations to each job card, summarizing:
  - matched skills
  - strong profile signals
  - missing or unclear skill gaps
- Improved the job detail modal with:
  - matched skills
  - skill gaps
  - score explanation context
  - collapsed full posting text
- Added a top-level unsaved-profile banner so users know to save profile edits before running a fresh shortlist.
- Added server-rendered frontend component tests for:
  - visible-by-default recommendation signals
  - hidden signal mode
  - profile readiness summary
  - job detail modal match context
  - score explanation text
  - skill-gap add action wiring

### Validation
- `npm run lint` -> passed
- `npm test -- --run` -> **21 passed**
- `npm run build` -> passed

### Result
The shortlist is transparent by default again, but users still have a compact mode. The most important review components now have direct regression coverage beyond pure helper tests.

---

## Day 51 - Weekly AWS Corpus Refresh Automation

### Focus
Make the staging backend refresh its job corpus without a manual user request.

### What was done
- Added and hardened `buildspec.weekly-refresh.yml` for the scheduled backend refresh path.
- Added tests for the weekly buildspec so the refresh/package/deploy steps stay explicit.
- Created AWS resources for the weekly automation:
  - CodeBuild project `internlens-weekly-corpus-refresh`
  - EventBridge rule `internlens-weekly-corpus-refresh`
  - schedule `cron(0 9 ? * MON *)`
  - CodeBuild role `internlens-weekly-corpus-refresh-codebuild-role`
  - EventBridge role `internlens-weekly-corpus-refresh-events-role`
  - SNS topic `internlens-weekly-refresh-alerts`
  - failure rule `internlens-weekly-corpus-refresh-failures`
- Added email subscription for `helios473@gmail.com`; it remains pending until the AWS confirmation email is accepted.
- Replaced root CLI usage with an IAM user credential path and documented credential rotation guidance.
- Simplified the top-level README and moved detailed local commands into `docs/development/local_workflows.md`.

### Validation
- Weekly CodeBuild manual run -> **succeeded**
- Refreshed processed jobs saved in build -> **167**
- Backend tests inside CodeBuild -> **200 passed**
- Elastic Beanstalk deployed version -> `weekly-corpus-20260514031631-5d9ae2d3b1fa`
- Elastic Beanstalk health -> `Ready / Green`
- CloudFront smoke check -> passed

### Result
The staging backend now has a working weekly job-corpus refresh and deploy loop. The README is much shorter and points readers to focused docs for local workflows and AWS operations.

---

## Day 52 - Ranking Score V2

### Focus
Make the recommendation score more expressive without hiding the decision behind an opaque model.

### What was done
- Added a README ranking diagram so the scoring flow is visible near the top of the project page.
- Added `docs/architecture/ranking_logic.md` as the detailed scoring reference.
- Split the fit score into clearer weighted components:
  - skill match: `35%`
  - qualification coverage: `17%`
  - preferred role match: `18%`
  - major match: `12%`
  - location fit: `8%`
  - freshness: `4%`
  - internship signal: `6%`
- Added priority-weighted skill scoring:
  - required qualification: `1.00`
  - title signal: `0.70`
  - preferred qualification: `0.55`
  - description signal: `0.35`
- Ordered matched skills and skill gaps by priority so user-facing cards can show the most important signals first.
- Kept blockers separate from fit score so ineligible roles still become `Skip`.
- Prevented neutral defaults from broad profile settings from creating `Apply Now` or `Apply Later` without a real skill, role, or major signal.

### Validation
- `pytest tests/test_baseline_scorer_seniority.py tests/test_api_and_ranking.py -q` -> **50 passed**
- `pytest -q` -> **206 passed**

### Result
The scorer is still heuristic and explainable, but it now distinguishes required skills from weaker text mentions, accounts for structured qualification coverage, and uses freshness as a light tie-breaker.

---

## Day 53 - Score Breakdown UX and Ranking Quality Report

### Focus
Make ranking v2 easier to inspect in the product UI and add a repeatable quality report for representative candidate profiles.

### What was done
- Expanded job-card match breakdown from the older four-signal view to the full ranking v2 component set:
  - skills
  - qualification coverage
  - role
  - major
  - location
  - freshness
  - internship signal
- Changed skill gap display so gaps appear in scorer priority order with visible priority labels.
- Kept the score breakdown user-facing instead of exposing raw debug fields.
- Added `scripts/generate_ranking_quality_report.py` to generate Markdown and JSON quality reports for CS engineering, data/ML, marketing/growth, and finance/analyst profiles.
- Ignored generated `outputs/ranking_quality_report.*` files.

### Validation
- `npm test -- --run main.components.test.jsx` -> **6 passed**
- `pytest tests/test_generate_ranking_quality_report.py -q` -> **2 passed**
- `pytest -q` -> **208 passed**
- `npm run lint`, `npm test -- --run` (**21 passed**), and `npm run build` -> passed
- Generated `outputs/ranking_quality_report.md` and `outputs/ranking_quality_report.json` locally.

### Result
Users can now see why a score is high or low without reading raw component data, and ranking changes can be sanity-checked against multiple profile archetypes.

---

## Week 7 Snapshot

### Current project state
- Backend staging deployment is automated through CodePipeline and CodeBuild.
- Weekly corpus refresh is automated through EventBridge and CodeBuild, then deployed to Elastic Beanstalk.
- Cognito-protected staging smoke checks can validate health, auth enforcement, and deployed schema.
- The frontend uses `/me/...` account-scoped APIs for the main browser workflow.
- Profile Setup collects structured recommendation signals through searchable selectors.
- Recommendation cards explain matches more clearly with fit summaries, matched skills, skill gaps, visible-by-default signals, score explanations, job detail lookup, and check items.
- Ranking v2 separates skill match, qualification coverage, role fit, major fit, location, freshness, and internship signal into documented component scores.
- Job cards now show the full ranking v2 score breakdown, and the repo has a representative ranking quality report script.
- Shortlist review supports search, sorting, 20-item pagination, optional signal hiding, and account-scoped job actions.
- Frontend coverage now includes server-rendered component checks for the main shortlist review pieces.

### Latest quality checkpoint
- Local backend tests after ranking quality updates: **208 passed**
- Backend tests in latest weekly CodeBuild: **200 passed**
- Frontend checks:
  - `npm run lint` -> passed
  - `npm test -- --run` -> **21 passed**
  - `npm run build` -> passed

### Remaining next steps
- Confirm the SNS email subscription from `helios473@gmail.com`.
- Continue tightening ranking precision for broader non-CS candidate profiles.
- Review whether the profile taxonomy should move from hardcoded frontend constants to a shared config file.
- Expand frontend tests from static server-render checks toward browser-level interaction coverage.
- Improve dashboard copy and empty states now that profile setup and shortlist review are less free-form.
- Plan managed database migration before treating multi-user persistence as production-ready.
