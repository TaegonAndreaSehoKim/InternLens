# Week 9 Devlog

## 2026-10-05 - Account-scoped browser state and session renewal (item 2)

### Changes
- Split browser draft, shortlist selection, and filter caches by Cognito user ID; kept a separate local demo cache.
- Discarded the old shared cache rather than attributing private profile content to a new account.
- Cleared account caches on sign-out and invalid sessions, and remounted the workspace when the account changes.
- Extracted an API client that gets the current Amplify access token for each request and retries a `401` once after a forced refresh.
- Checked token subjects before requests, including retries, so a profile mutation cannot use another account's session.
- Added regression coverage for draft isolation, cache clearing, token renewal, retry limits, and multipart uploads.

### Validation
- Backend full suite: **226 passed** (explicit temporary directory used because the default Windows pytest temp directory is inaccessible).
- Frontend full suite: **50 passed**.
- Frontend lint and production build: passed.
- Cognito SDK calls are mocked in regression tests; no real account sign-in was performed.

### Follow-up
- Continue with ranking freshness, degree eligibility, and sponsorship interpretation (item 3).

## 2026-10-05 - Posting age and eligibility interpretation (item 3)

### Changes
- Calculated posting freshness from posting dates at a shared evaluation time; kept `freshness_days` as the source-check validity period.
- Distinguished required PhD conditions from preferred qualifications, alternative degrees, and incidental mentions.
- Preserved explicit sponsorship restrictions with source evidence in both ATS normalizers and older job files loaded in memory.
- Shared requirement interpretation between ranking and job detail endpoints.
- Corrected the README role weight to 18% and clarified the source validity label in job details.
- Added end-to-end ATS normalization, loading, ranking, and API regression cases without regenerating the corpus.

### Validation
- Backend full suite: **265 passed**.
- Frontend full suite: **50 passed**; lint and production build passed.
- Existing sample-data and CLI/API tests passed in the full backend suite.

### Follow-up
- Add corpus readiness, explicit unavailable-data UI states, and safer snapshot replacement (item 4).

## 2026-10-05 - Corpus readiness and recoverable snapshots (item 4)

### Changes
- Added public `/ready` with active/total counts and source-check/expiry timestamps; kept `/health` as liveness.
- Shared the CLI corpus health check with the API and rejected missing or malformed data, including checks with a zero minimum.
- Returned `503` for empty/expired recommendations and distinguished unavailable data from connectivity problems in the workspace.
- Gated new matches on readiness, added a retry notice, and retained historical runs and saved-job views.
- Staged and validated processed snapshots outside the corpus tree before directory replacement; preserved previous data on normalization, serialization, and publication failures.
- Preserved a named backup when rollback itself fails and documented the publication gap and refresh cadence margin.

### Validation
- Targeted backend checks: **58 passed**.
- Backend full suite: **284 passed**.
- Frontend full suite: **58 passed**; lint and production build passed.
- Existing generated data was not refreshed or staged. The local corpus was fully expired during inspection; live AWS scheduling was not changed.

### Follow-up
- Add browser interaction coverage, frontend CI, and a labeled ranking evaluation (item 6).

## 2026-10-05 - Interaction CI and labeled ranking checks (item 6)

### Changes
- Added jsdom interaction coverage for account draft switching, profile edits and saving, readiness retry, recommendation runs, save/apply/hide/undo, failure recovery, search, and pagination.
- Added a Node 24 frontend CI job using `npm ci`, lint, Vitest, and the production build.
- Added a fixed-time benchmark with four candidate profiles, 15 synthetic jobs, and 60 explicit relevance/eligibility judgments.
- Measured Precision@2, nDCG@2, eligibility accuracy, blocked shortlist rate, and non-internship shortlist rate; each profile must pass thresholds independently.
- Added a CLI check to backend CI and tests proving bad rankings, empty shortlists, incomplete labels, and regressions fail the gate.
- Replaced two live Lever unit-test requests with deterministic HTTP transport fixtures.

### Validation
- Backend full suite: **294 passed**.
- Frontend full suite: **65 passed**; lint and production build passed.
- Curated benchmark: Precision@2 **1.0**, nDCG@2 **1.0**, eligibility accuracy **1.0**, both leakage rates **0.0**.
- The benchmark is synthetic and independent human review remains pending; no production quality claim or live Cognito/browser layout check is implied.
- New development dependencies and the lockfile were added; generated job data was unchanged.

### Follow-up
- Separate module responsibilities, add indexed corpus lookup, correct company identity normalization, and synchronize current documentation (item 7).

## 2026-10-05 - Module boundaries, detail lookup, and company metadata (item 7)

### Changes
- Extracted 30 API request/response models into `src/api/models.py`, keeping their names and endpoint contracts stable.
- Moved profile selector catalogs and the account form out of `main.jsx` into dedicated modules; retained the existing workspace flow and styling.
- Added a bounded per-process job ID index for detail endpoints, with file metadata invalidation, stable-snapshot checks, defensive copies, and canonical duplicate rules.
- Kept ranking on the active loader so cached detail records cannot bypass expiry in new recommendations.
- Used optional registry/company CLI metadata for company display names and stored Lever departments separately, with team fallback.
- Added display names to 20 existing registry entries and retained discovered company names during new-source promotion. Active flags, source/job IDs, and output paths were unchanged.
- Corrected processed-schema required fields, capitalization guidance, stale checkpoint links, and historical corpus examples.
- Made the readiness retry available after an initial API connection failure, with an interaction regression test.

### Validation
- Targeted backend checks before new cases: **87 passed**; index/identity integration checks: **39 passed**.
- Backend full suite: **309 passed**; the curated ranking gate passed with unchanged metrics.
- Frontend full suite: **68 passed**; lint and production build passed.
- Account form tests covered email sign-in challenges and retrying a wrong sign-up confirmation code with mocked SDK calls.
- Read-only local timing across 12 repetitions: median full-corpus detail parsing **123.71 ms**, warm indexed lookup **23.35 ms**. These are local measurements, not a deployment latency guarantee.
- Generated jobs/raw data and existing user runtime changes were not regenerated or staged; only small source registry metadata changed.

### Remaining product work
- Review the synthetic ranking labels with real ATS examples and more candidate constraints.
- Refresh the expired local/deployed corpus when operationally appropriate; readiness now exposes unavailable data.
- Broader API authorization/path hardening and CSS consolidation remain separate follow-ups.

## 2026-10-05 - Local corpus refresh and OneDrive cleanup recovery

### Changes
- Refreshed the local active registries: all 21 sources succeeded, saving 233 processed jobs (95 Lever and 138 Greenhouse).
- Fixed cleanup of read-only Windows/OneDrive snapshot backups, which interrupted the first refresh after successful publication.
- Retried removal only inside the verified temporary workspace; persistent cleanup failures now log the workspace path without masking successful publication or the original error.
- Ignored temporary snapshot directories in Git and retained the existing failed-rollback recovery behavior.
- Kept refreshed raw/processed files and health/refresh reports local; no generated data or runtime state was staged.

### Validation
- Snapshot regressions: **14 passed**; backend full suite: **312 passed**.
- Local corpus health: **233 active**, **233 total**, **0 expired or filtered**.
- In-process API smoke with the refreshed corpus: `/ready` returned **200**, the sample profile returned **10** eligible/applyable recommendations, and the first job detail returned **200**.
- Latest source check: **2026-10-05T22:35:05Z**; latest validity expiry: **2026-10-12T22:35:05Z**.
- Frontend files and checks were unchanged in this refresh task; no deployed corpus was updated.

## 2026-10-05 - Snapshot regression portability

### Changes
- Diagnosed the failed GitHub Actions run for `025cc1f`: 311 backend tests passed, but the new read-only backup regression compared POSIX directory-relative removal paths with absolute retry paths.
- Recorded the actual backup directory in the test so Windows and Linux validate the same target, while preserving the publication, permission-scope, retry-count, and cleanup assertions.
- Snapshot cleanup behavior and refreshed local job data were unchanged.

### Validation
- Windows backend full suite: **312 passed** after the test correction.
