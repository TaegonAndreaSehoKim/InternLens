# InternLens Overview

## Project summary

InternLens is a practical internship search product prototype that connects four core pieces of work:

1. public job board ingestion
2. candidate-profile-based ranking
3. shortlist-oriented inspection through CLI and API
4. stored-profile review through a lightweight frontend dashboard

The project began as a simple internship recommender over sample jobs, but it now supports real public ATS sources and a more realistic evaluation loop. At the current stage, the system can fetch public internships from Lever and Greenhouse boards, normalize them into a shared processed schema, rank them against a target candidate profile, persist user-scoped profile workflow state, and expose results through CLI, API, and a Vite/React frontend. The latest local backend checkpoint is `312 passed`, the latest weekly CodeBuild backend checkpoint is `200 passed`, and the frontend lint, test, and production build checks pass.

---

## Goals

The main goals of InternLens are:
- build a lightweight, understandable internship recommender
- move beyond static toy data into real public job board ingestion
- support iterative ranking improvements without breaking earlier behavior
- expose results both as a scriptable CLI flow and as an API
- support a local browser workflow for profile setup, recommendation review, and job actions
- maintain fast iteration through small, regression-tested changes

This is not meant to be a production hiring platform yet. It is a clean, extensible foundation for future internship discovery and ranking work.

---

## Architecture

### 1. Ingestion layer
InternLens currently supports:

#### Lever ingestion
- single-board fetch
- raw snapshot storage
- processed normalization
- registry-driven batch fetch

#### Greenhouse ingestion
- single-board fetch
- raw snapshot storage
- processed normalization
- registry-driven batch fetch
- metadata-aware geographic location extraction for boards that use work-mode labels such as `Hybrid` or `In-Office`

The ingestion layer saves:
- raw board snapshots for reproducibility
- processed per-job JSON files for ranking

Registry `company_name` metadata supplies a company display name, with the source identifier as a fallback. Lever department names remain separate from company identity; `team` uses the source team or falls back to the department. Promotion retains the discovered company name in new registry entries. Existing processed files and stored run snapshots are not rewritten by these normalization changes.

This keeps collection and ranking decoupled, which makes debugging and iteration easier.

Source refreshes normalize the complete response before staging validated JSON outside the corpus tree. The source directory is replaced only after staging succeeds, with rollback to the previous snapshot on a publication failure. A failed rollback preserves its backup path for operator recovery. Directory renames have a brief publication gap; this is not a concurrent-writer or crash-recovery transaction.

---

### 2. Preprocessing layer
The preprocessing layer loads:
- candidate profiles
- processed job directories

Candidate preferences such as role targets, graduation timing, sponsorship need, and extracted skills are turned into a baseline-friendly representation.

The job parser supports recursively loading processed jobs from source-specific directories. It also suppresses duplicate `job_id` values and conservative content duplicates by default so older flat files and nested source/site files can coexist during development.

Job detail endpoints use a bounded per-process `JobIndex` in `src/storage/job_index.py`. It checks a recursive file metadata fingerprint, parses a stable snapshot only when the corpus changes, and looks up records by ID. Edits, additions, deletions, and source-directory replacement invalidate the cache. Detail views preserve expired records and distinct content-duplicate IDs; recommendations still use the active loader on every run, so expiry is never bypassed by the detail cache. Fingerprint validation still scans file metadata; this is not a persistent database index.

Pydantic request/response contracts live in `src/api/models.py`, while `src/api/app.py` wires endpoints and workflow logic. In the frontend, profile selector catalogs live in `profileOptions.js` and the account form in `auth/AuthDialog.jsx`; the workspace keeps its existing workflow and styles.

---

### 3. Ranking layer
The ranking layer is currently heuristic and transparent.

It uses:
- weighted skill matching
- qualification coverage
- preferred role overlap
- major alignment
- location match
- posting freshness
- internship signal strength
- blocker logic

Important ranking improvements added so far:
- senior-role blocker
- non-internship blocker
- PhD blocker
- internship-aware ordering
- blocker-aware shortlist filters
- fallback skill extraction for sparse public postings
- priority-weighted skill scoring across required qualifications, title, preferred qualifications, and descriptions
- separate qualification coverage and freshness score components
- reduced noisy fallback skill matching for non-technical internship titles
- tighter shortlist precision for noisy public boards

This makes the current baseline much more useful than a simple keyword scorer.

---

### 4. Output layer
InternLens supports:
- CLI-based ranking inspection
- JSON export
- CSV export
- API recommendation endpoint
- job detail endpoint
- profile, feedback, recommendation run, job action, activity, and dashboard endpoints
- local Vite/React dashboard for the stored-profile recommendation workflow

Recent CLI improvements:
- `--eligible-only`
- `--applyable-only`
- `--suppress-similar-results`

These filters make it easier to inspect meaningful subsets rather than dumping the full ranked list.

### 5. Persistence and frontend layer
InternLens now includes user-scoped SQLite-backed local persistence for:
- profiles
- feedback events
- recommendation run snapshots
- saved, hidden, and applied job states

The current API accepts a temporary `X-InternLens-User-Id` header in `dev` auth mode to scope stored-profile data. This preserves the local demo flow through the default `local_user` scope. When `INTERNLENS_AUTH_MODE=cognito`, the backend validates a Cognito bearer token and uses the verified JWT `sub` as the user scope.
The frontend has the matching switch: `VITE_AUTH_MODE=dev` keeps the existing demo behavior, while `VITE_AUTH_MODE=cognito` uses an in-app email/password form backed by the existing Cognito user pool and sends the access token to the API.

Browser profile drafts, shortlist selection, and filters are cached separately for each Cognito `sub`, with a separate `local_user` cache for the demo. The legacy shared cache is discarded because its account owner cannot be established. Signing out or ending an invalid session clears that account's cache. Account changes remount the workspace so in-memory state is also isolated.

Authenticated API requests obtain the current access token through Amplify `fetchAuthSession`, which refreshes expired tokens when possible. A `401` triggers one forced refresh and retry before returning to sign-in. Tokens must belong to the workspace's user; a token from another account is rejected before sending profile data.

The frontend uses these APIs to support:
- profile setup and restoration
- reviewable resume upload parsing with confidence and evidence snippets for profile prefill
- account-scoped `/me/...` profile, dashboard, recommendation, and job-action calls for the browser workflow
- searchable structured selectors for roles, skills, locations, and industries
- simple online/offline API health status
- separate job-data readiness, unavailable-data messages, and a retry control; new shortlists require current data while saved jobs and historical runs remain accessible
- in-app Cognito login, sign-up, and email confirmation when `VITE_AUTH_MODE=cognito`
- dashboard summary review
- dashboard saved/applied/hidden job review
- recommendation runs and historical run loading
- filtering by `Apply Now`, `Apply Later`, and `Skip`
- searching shortlist results by company, role, location, matched skills, and skill gaps
- job actions for save, applied, and hidden states
- undo controls for saved, applied, and hidden job states
- visible-by-default recommendation-card signals with optional hiding
- plain-language score explanations
- job detail modal backed by `GET /jobs/{job_id}`

---

## Current development status

### What is working well
- multi-source public job ingestion is working
- registry-based batch fetching is working
- processed schema generation is working
- ranking is stable enough for demo use
- tests are strong enough to support iterative changes safely
- the CLI now supports shortlist-style filtering
- API behavior remains stable after ranking refinements
- stored-profile, feedback, recommendation history, and job action APIs are working
- the Vite/React frontend can exercise the main demo workflow, including clickable dashboard state summaries
- Cognito JWT auth mode can scope stored workflow data by signed-in account while development auth remains available for local demos
- GitHub Actions runs backend tests, frontend lint/interaction tests/build, and a fixed-time labeled ranking regression check; a separate scheduled/manual workflow produces corpus refresh artifacts
- AWS staging is live with Amplify for the frontend, Elastic Beanstalk for the backend, and CloudFront for HTTPS API access
- a weekly AWS refresh/deploy path now refreshes the staging job corpus through EventBridge and CodeBuild

### What improved most recently
Recent work focused on:
- reducing ranking noise for public internship boards
- improving Greenhouse location normalization using metadata
- reducing noisy fallback skill matches for non-technical internships
- making shortlist display easier to inspect
- tightening Cloudflare shortlist precision so non-core internship roles drop out more often
- adding profile persistence, dashboard APIs, and recommendation run history
- adding a Vite/React frontend with session persistence, API health status, recommendation filters, score dials, and job action buttons
- cleaning up dashboard UX so users see saved/applied/hidden state transitions instead of internal run identifiers
- making dashboard summary counts open the matching shortlist, saved, applied, or hidden job view
- adding local Cognito login/sign-out flow validation and clearer profile-save feedback
- expanding the active internship source corpus from priority company seeds
- paginating full shortlist results in the frontend while increasing API result limits
- demoting non-core marketing/communications internships that were overpromoted by broad analytics wording
- adding account-scoped `/me/...` API aliases so browser users no longer handle profile IDs directly
- redesigning Profile Setup around searchable structured selectors and quality checks instead of broad free-text entry
- making shortlist review searchable, with visible-by-default match signals, optional signal hiding, and job detail lookup
- adding direct skill-gap actions so users can update profile skills from recommendation cards before rerunning matches
- adding score explanations and an unsaved-profile banner so users understand why a role ranked where it did and when profile edits need saving
- adding server-rendered frontend component tests for shortlist cards, profile readiness, job detail modal context, and skill-gap action wiring
- stress-testing company-seed-based source discovery with a larger seed draft
- hardening source discovery with ATS URL normalization, checkpointed saves, structured warning summaries, opt-in direct ATS probing, and blocked-page manual review records
- tightening source promotion safeguards for direct ATS probe candidates and inactive registry entries
- adding high-intent same-site priority-link following for student, internship, campus, and early-career discovery pages
- adding promotion dry-run diagnostics that show internship signal examples
- adding discovery recall comparison and promotion-candidate smoke scripts to connect source discovery changes to ranking quality
- adding scheduled AWS corpus refresh automation that deploys refreshed job data back to the staging backend
- splitting the fit score into clearer weighted components for skills, qualification coverage, role fit, major fit, location, freshness, and internship signal strength
- adding resume upload parsing so profile setup can review evidence-backed suggestions for skills, majors, roles, industries, locations, education timeline, and background text

Current validation and benchmark details are recorded in [week 9](../devlog/week9.md) and the [README quality checkpoint](../../README.md#quality-checkpoint). Earlier corpus inspections and deployment runs remain historical examples; job availability and shortlist volume depend on the currently deployed snapshot.

---

## Earlier corpus inspection examples

### Waymo
A previous Waymo corpus inspection produced a very narrow applyable-only shortlist. Its size is an example of blocker and internship filtering, not a guarantee about the current public board.

### Cloudflare
Previous Cloudflare inspections were noisier than Waymo and informed precision safeguards.

Previously inspected shortlist examples included:
- Data Analytics Intern
- Business Analyst Intern, Revenue Operations (AI Innovation)
- DCSC Automation Coordinator Intern
- Network Deployment Engineer Intern
- Data Engineer Intern

These now appear with real geographic locations such as:
- Austin, US
- London, UK
- Singapore

instead of generic work-mode-only labels dominating the output.

---

## Why the project matters

InternLens now demonstrates a real iterative ML/IR-style workflow:
- collect external data
- normalize it
- design scoring logic
- validate output behavior
- add regression tests
- refine precision over time

That makes it useful as:
- a portfolio project
- a search / ranking prototype
- an internship recommender demo
- a foundation for future retrieval and reranking work

It also shows good engineering discipline:
- reproducible raw snapshots
- source-specific normalization
- CLI utilities for debugging
- API exposure
- test-backed iteration

---

## Main limitations

### Ranking limitations
- the baseline is still heuristic
- fallback skill extraction can still overgeneralize in some postings
- some broad AI-adjacent or operations internships may still remain in the shortlist, though non-core marketing and communications internships are now demoted more aggressively
- there is no learned relevance model yet

### Data limitations
- public ATS data is inconsistent
- work-mode and location fields vary by board
- some postings duplicate across locations
- structured qualification fields are often sparse

### Product limitations
- shortlist filtering, search, pagination, visible signals, optional signal hiding, score explanations, and job detail lookup are useful, but the frontend still needs stronger empty states and error states across the full workflow
- saved/applied/hidden state transitions are now clearer, but dashboard copy and broader interaction polish still need iteration
- corpus-level deduplication is in place, but grouping similar multi-location results is still conservative and optional
- company normalization remains lightweight
- source discovery is scriptable and now preserves partial broad-scan results, rejects non-board ATS helper URLs, follows limited high-intent same-site links, and summarizes discovery methods
- direct ATS probe candidates are still intentionally conservative; broad boards can show internship signals without meeting automatic promotion safeguards
- promotion-candidate smoke testing is available, but current priority-link additions can still surface general boards with no internship density
- blocked-page manual review records help track `403`, `406`, and `429` pages without treating them as promotion-ready sources

---

## Recommended next steps

The strongest next steps are:

1. refine shortlist precision further
   - reduce remaining non-core internship noise
   - tighten relevance requirements for `Apply Later`

2. improve normalization quality
   - better company normalization
   - better hybrid/in-office handling
   - better deduplication across repeated multi-location postings

3. strengthen retrieval/ranking sophistication
   - embeddings or vector retrieval
   - learned reranking
   - feedback-aware personalization

4. improve presentation
   - clearer frontend empty and error states
   - browser-level interaction tests for shortlist search, signal hiding, job detail modal, and job actions
   - more polished saved/applied/hidden dashboard views
   - demo screenshots or a short walkthrough

5. harden source discovery
   - measure priority-link recall on larger seed subsets
   - keep blocked/manual-review records out of automatic promotion
   - use dry-run internship signal examples and promotion-candidate smoke reports to tune validation and promotion thresholds

---

## Bottom line

InternLens is now a small but credible internship discovery system.

It is no longer just a script that scores static sample jobs. It now supports:
- real public ATS ingestion
- processed data generation
- blocker-aware internship ranking
- shortlist filtering
- API access
- stored profile and feedback workflows
- a local frontend dashboard
- AWS staging deployment
- regression-tested iteration

That makes the project demoable today and extensible tomorrow.
