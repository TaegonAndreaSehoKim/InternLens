# Week 8 Devlog

Week 8 focused on making recommendation quality easier to inspect, reducing profile setup friction with reviewable resume import, and hardening scheduled corpus refreshes against temporary public ATS failures.

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

## Day 54 - Resume Import for Profile Setup

### Focus
Reduce profile setup friction by letting users upload a resume and review parsed recommendation signals before saving.

### What was done
- Added `src/preprocessing/resume_parser.py` for local resume parsing.
- Supported `.txt`, `.md`, `.pdf`, and `.docx` files through `python-multipart`, `pypdf`, and `python-docx`.
- Added `POST /me/profile/resume` to parse an uploaded resume into account-profile fields without saving automatically.
- Extracted profile fields from resume text:
  - skills
  - majors
  - preferred role hints
  - target industries
  - preferred locations
  - degree level
  - graduation date
  - sponsorship hints
  - years of experience
  - background text
- Added section-aware parsing so education and skills sections produce stronger suggestions than loose resume text.
- Returned grouped suggestions with confidence labels and short evidence snippets.
- Added a resume import review panel to Profile Setup with accept-all, individual add, and dismiss controls.
- Kept manual selectors as the final user-controlled source of truth before saving.

### Validation
- `pytest tests/test_resume_parser.py tests/test_profile_api.py -q` -> **32 passed**
- `npm test -- --run main.components.test.jsx` -> **10 passed**
- `pytest -q` -> **212 passed**
- `npm run lint`, `npm test -- --run` (**25 passed**), and `npm run build` -> passed

### Result
Profile setup can now start from a resume upload instead of requiring users to manually enter every signal.
The feature remains explainable and reviewable because parsed values are shown as evidence-backed suggestions before they are added to the form.

---

## Day 55 - Resilient Scheduled Corpus Refresh

### Focus
Prevent a temporary failure from one public ATS board from terminating the entire scheduled refresh without diagnostics.

### What was done
- Added a shared HTTP retry helper for Lever and Greenhouse requests.
- Retried connection errors, timeouts, invalid JSON responses, `408`, `425`, `429`, and `5xx` responses up to three attempts with exponential backoff and `Retry-After` support.
- Kept permanent client errors such as `404` fail-fast at the individual request level.
- Changed registry refresh loops to record a failed source and continue attempting the remaining boards.
- Added `outputs/corpus_refresh_report.json` with:
  - selected, successful, and failed source counts
  - per-provider summaries
  - processed job counts
  - final source error details
  - the applied success/failure policy
- Kept local refresh strict by default while allowing the full GitHub and AWS jobs to tolerate at most two final board failures.
- Required at least one successfully refreshed source before corpus health validation.
- Kept the non-expired corpus health gate before AWS packaging and deployment.
- Made the GitHub artifact upload run even after refresh or health failure so diagnostics remain downloadable.
- Added refresh reports and health reports to the weekly CodeBuild artifacts.
- Updated GitHub Actions from the Node 20-based action versions to current `v7` releases.
- Confirmed the original GitHub Actions run `#120` succeeded when its failed job was rerun, supporting the transient-source-failure diagnosis.

### Validation
- Retry, registry isolation, refresh policy, workflow, buildspec, pipeline, and promotion smoke tests -> passed
- `pytest -q` -> **226 passed**
- `npm run lint` -> passed
- `npm test -- --run` -> **30 passed**
- `npm run build` -> passed
- `git diff --check` -> passed

### Result
Scheduled refreshes now distinguish a small partial ATS outage from an unhealthy corpus. They preserve source-level evidence, continue useful work across the registry, and still block deployment when the tolerated failure limit or corpus health gate is exceeded.

---

## Week 8 Snapshot

### Current project state
- Backend staging deployment is automated through CodePipeline and CodeBuild.
- Weekly corpus refresh is automated through EventBridge and CodeBuild, then deployed to Elastic Beanstalk.
- Scheduled Lever and Greenhouse refreshes retry transient failures, isolate failed boards, and produce source-level JSON diagnostics.
- Cognito-protected staging smoke checks can validate health, auth enforcement, and deployed schema.
- The frontend uses `/me/...` account-scoped APIs for the main browser workflow.
- Profile Setup can import resume files, then lets users review evidence-backed structured suggestions before saving.
- Recommendation cards explain matches more clearly with fit summaries, matched skills, skill gaps, visible-by-default signals, score explanations, job detail lookup, and check items.
- Ranking v2 separates skill match, qualification coverage, role fit, major fit, location, freshness, and internship signal into documented component scores.
- Job cards now show the full ranking v2 score breakdown, and the repo has a representative ranking quality report script.
- Shortlist review supports search, sorting, 20-item pagination, optional signal hiding, and account-scoped job actions.
- Frontend coverage now includes server-rendered component checks for the main shortlist review pieces.

### Latest quality checkpoint
- Local backend tests after refresh resilience updates: **226 passed**
- Backend tests in latest weekly CodeBuild: **200 passed**
- Frontend checks:
  - `npm run lint` -> passed
  - `npm test -- --run` -> **30 passed**
  - `npm run build` -> passed

### Remaining next steps
- Confirm the SNS email subscription from `helios473@gmail.com`.
- Review scheduled `corpus_refresh_report.json` artifacts and tune the two-source failure allowance if registry size changes materially.
- Continue tightening ranking precision for broader non-CS candidate profiles.
- Review whether the profile taxonomy should move from hardcoded frontend constants to a shared config file.
- Expand frontend tests from static server-render checks toward browser-level interaction coverage.
- Improve dashboard copy and empty states now that profile setup and shortlist review are less free-form.
- Plan managed database migration before treating multi-user persistence as production-ready.
