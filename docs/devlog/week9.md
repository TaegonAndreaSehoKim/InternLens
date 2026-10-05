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
