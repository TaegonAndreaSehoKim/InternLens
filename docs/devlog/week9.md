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
