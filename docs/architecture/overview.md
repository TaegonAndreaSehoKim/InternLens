# InternLens Overview

## Project summary

InternLens is a practical internship search product prototype that connects four core pieces of work:

1. public job board ingestion
2. candidate-profile-based ranking
3. shortlist-oriented inspection through CLI and API
4. stored-profile review through a lightweight frontend dashboard

The project began as a simple internship recommender over sample jobs, but it now supports real public ATS sources and a more realistic evaluation loop. At the current stage, the system can fetch public internships from Lever and Greenhouse boards, normalize them into a shared processed schema, rank them against a target candidate profile, persist profile workflow state, and expose results through CLI, API, and a Vite/React frontend. The current local validation state is `163 passed`, and the frontend production build passes with `npm run build`.

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

This keeps collection and ranking decoupled, which makes debugging and iteration easier.

---

### 2. Preprocessing layer
The preprocessing layer loads:
- candidate profiles
- processed job directories

Candidate preferences such as role targets, graduation timing, sponsorship need, and extracted skills are turned into a baseline-friendly representation.

The job parser supports recursively loading processed jobs from source-specific directories. It also suppresses duplicate `job_id` values and conservative content duplicates by default so older flat files and nested source/site files can coexist during development.

---

### 3. Ranking layer
The ranking layer is currently heuristic and transparent.

It uses:
- skill overlap
- preferred role overlap
- location match
- internship bonus
- blocker logic

Important ranking improvements added so far:
- senior-role blocker
- non-internship blocker
- PhD blocker
- internship-aware ordering
- blocker-aware shortlist filters
- fallback skill extraction for sparse public postings
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
InternLens now includes SQLite-backed local persistence for:
- profiles
- feedback events
- recommendation run snapshots
- saved, dismissed, and applied job states

The frontend uses these APIs to support:
- profile setup and restoration
- API health checks
- dashboard summary review
- recommendation runs and historical run loading
- filtering by `Apply Now`, `Apply Later`, and `Skip`
- job actions for save, applied, and dismiss

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
- the Vite/React frontend can exercise the main demo workflow
- GitHub Actions runs backend tests and has a scheduled/manual corpus refresh artifact workflow

### What improved most recently
Recent work focused on:
- reducing ranking noise for public internship boards
- improving Greenhouse location normalization using metadata
- reducing noisy fallback skill matches for non-technical internships
- making shortlist display easier to inspect
- tightening Cloudflare shortlist precision so non-core internship roles drop out more often
- adding profile persistence, dashboard APIs, and recommendation run history
- adding a Vite/React frontend with session persistence, API health status, recommendation filters, score dials, and job action buttons
- stress-testing company-seed-based source discovery with a larger seed draft
- hardening source discovery with ATS URL normalization, checkpointed saves, structured warning summaries, opt-in direct ATS probing, and blocked-page manual review records
- tightening source promotion safeguards for direct ATS probe candidates and inactive registry entries
- adding high-intent same-site priority-link following for student, internship, campus, and early-career discovery pages
- adding promotion dry-run diagnostics that show internship signal examples
- adding discovery recall comparison and promotion-candidate smoke scripts to connect source discovery changes to ranking quality

The latest validation state shows:
- `163 passed`
- `npm run build` passing in `frontend/`
- Cloudflare re-fetched with improved location extraction
- Cloudflare applyable-only shortlist reduced to a much smaller, more relevant subset
- Waymo shortlist remains very small and focused under applyable-only filtering

---

## Example current behavior

### Waymo
The Waymo shortlist is now very narrow. Under applyable-only filtering, it effectively surfaces a single clearly relevant internship target rather than a noisy wall of blocked roles. That is a strong sign that blocker logic and internship prioritization are working.

### Cloudflare
Cloudflare remains noisier than Waymo, but it is much more usable than before.

Recent visible shortlist examples include:
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
- some broad AI-adjacent or operations internships may still remain in the shortlist
- there is no learned relevance model yet

### Data limitations
- public ATS data is inconsistent
- work-mode and location fields vary by board
- some postings duplicate across locations
- structured qualification fields are often sparse

### Product limitations
- shortlist filtering is useful, but the frontend still needs stronger empty states and error states
- saved/applied/dismissed state transitions in recommendation cards can be clearer
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
   - clearer saved/applied/dismissed state transitions
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
- regression-tested iteration

That makes the project demoable today and extensible tomorrow.
