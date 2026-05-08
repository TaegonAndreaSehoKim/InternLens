# Week 6 Devlog

Week 6 covers Day 42 onward.
The focus moved from basic account scaffolding into local Cognito validation, a larger internship corpus, shortlist quality cleanup, and more usable full-result review.

---

## Day 42 - Cognito Local Validation and Session Polish

### Focus
Verify the account-system path locally and make login/logout behavior usable from the browser.

### What was done
- Confirmed Cognito User Pool and app client values for local development.
- Added localhost callback/logout URLs in Cognito so the Vite app can complete sign-in and sign-out.
- Fixed sign-out routing so users return to the app instead of landing on an error page.
- Clarified that local backend Cognito mode requires the `INTERNLENS_COGNITO_*` environment variable names.
- Kept the frontend `.env.local` ignored while using it for local Cognito settings.

### Result
The local app can run in Cognito mode with a signed-in account, and API calls use the Cognito access token as the user boundary.

---

## Day 43 - Source Corpus Expansion

### Focus
Increase the number of available internship postings without promoting broad source-discovery noise blindly.

### What was done
- Added source-discovery seed controls for priority and seed-count bounded scans.
- Ran a priority company-seed discovery pass and promoted a small reviewed set of sources.
- Expanded active registry coverage to include additional Greenhouse and Lever boards such as Airbnb, Cloudflare, Okta, Scale AI, Zscaler, and Palantir.
- Refreshed processed jobs from the active registry.
- Increased the frontend recommendation request size so the UI can review more than the previous 20-role shortlist cap.

### Result
The local corpus now has a larger internship pool for recommendation runs while keeping promotion decisions explicit and reviewable.

---

## Day 44 - Ranking Quality and Full Shortlist Review

### Focus
Fix visible ranking noise and make large shortlists easier to inspect.

### What was done
- Investigated a case where `Digital Marketing Intern` outranked data-focused internships because broad `analytics tools` wording matched `data analysis`.
- Expanded non-core business internship detection for marketing, communications, social media, and graphic design roles.
- Prevented non-core business internships from being promoted to `Apply Now` or `Apply Later` solely through high raw score signals.
- Added regression coverage showing that a digital marketing internship can still match `data analysis` text but should remain `Skip`.
- Raised API recommendation `top_k` validation from 100 to 1000.
- Changed the frontend to request a larger recommendation snapshot and paginate visible results 20 at a time.
- Added `Previous` and `Next` controls above and below the job list.
- Added profile-save status feedback so save failures and successes are visible instead of looking like no-op button clicks.
- Fixed server health display so failed profile restoration no longer incorrectly marks a healthy API as offline.

### Validation
- `pytest -q` -> **185 passed**
- `npm run lint` -> passed
- `npm test -- --run` -> **8 passed**
- `npm run build` -> passed

### Result
Shortlists now preserve the full available result set while keeping the review panel manageable, and the most visible marketing-role false positive is covered by regression tests.

---

## Week 6 Snapshot

### Current project state
- Cognito mode works locally when the frontend and backend use matching Cognito environment settings.
- The active source corpus is larger and includes more high-priority public ATS boards.
- Recommendation runs can return a larger result snapshot.
- The frontend paginates shortlist review in 20-role pages.
- Profile save and API health feedback are more visible to the user.
- Non-core marketing and communications internships are less likely to pollute the top of technical/data shortlists.

### Latest quality checkpoint
- Backend tests: **185 passed**
- Frontend checks:
  - `npm run lint` -> passed
  - `npm test -- --run` -> **8 passed**
  - `npm run build` -> passed

### Remaining next steps
- Continue tightening ranking precision for broad AI-adjacent and operations internships.
- Improve frontend empty/error states across saved, applied, hidden, and recommendation views.
- Decide when to redeploy the backend bundle after API/ranking changes.
- Move persistence from SQLite to a managed database before real multi-user use.
- Add a short demo walkthrough or screenshots once the UI stabilizes further.
