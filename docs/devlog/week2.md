# Week 2 Devlog

## Day 8 — Precision/Location Cleanup and Output Usability

### Focus
Improve public-board ranking usability and reduce noisy shortlist behavior, especially on Greenhouse sources.

### What was done
- Tightened baseline internship ranking logic.
- Added and refined blocker-aware shortlist behavior.
- Added CLI output filters:
  - `--eligible-only`
  - `--applyable-only`
- Improved Greenhouse normalization so geographic location could come from metadata instead of only generic work-mode labels such as `Hybrid` or `In-Office`.
- Prevented stale Greenhouse processed files from mixing old and new normalized outputs across reruns.
- Re-fetched and re-evaluated Cloudflare data after normalization updates.

### Result
- The shortlist output became much easier to inspect.
- Location quality improved from generic labels toward real geographic values like `Austin, US`, `London, UK`, and `Singapore`.
- Cloudflare shortlist quality improved noticeably, though some non-core internships still remained.
- Full test suite was stable at **68 passed** at the end of this stage.

### Key takeaway
Week 2 started with a shift from “make it run” to “make the output usable.” The system became much more demo-friendly after shortlist filtering and location cleanup.

---

## Day 9 — Recovery / No Development Day

### Status
- No feature development.
- No code changes.
- No ranking or ingestion updates.

### Notes
This was an intentional pause day to recover and keep pacing sustainable.

### Outcome
Project state was preserved as-is from the previous day, with the latest stable checkpoint ready for continuation.

---

## Day 10 — Cloudflare Shortlist Precision Improvement

### Focus
Reduce noisy fallback skill matches so non-technical internship titles stop surviving the shortlist too easily.

### Main problem at the start of the day
Cloudflare shortlist still contained several broad non-core internships that were inheriting noisy fallback matches from title/description heuristics.
Examples included roles in people/HR/marketing/product areas that were still being promoted because of broad AI, Python, or analytics wording.

### What was changed
- Refined fallback skill logic in `baseline_scorer.py`.
- Strengthened title-based gating so fallback title/description skill matching is used more conservatively.
- Added stronger separation between:
  - technical/data/research/engineering internship titles
  - non-technical internship titles
- Preserved strong behavior for technical roles such as:
  - Data Analytics Intern
  - Data Engineer Intern
  - Business Analyst Intern
  - Research / Security / Network-oriented internships
- Added regression tests for these new ranking rules.

### Validation
- `pytest tests/test_baseline_scorer_seniority.py -q` → **14 passed**
- `pytest -q` → **71 passed**

### Result
Cloudflare shortlist under `--applyable-only` became much tighter.
The visible shortlist reduced to a compact set centered on more relevant roles:
- Data Analytics Intern (Summer 2026)
- Business Analyst Intern, Revenue Operations (AI Innovation) (Summer 2026)
- DCSC Automation Coordinator Intern
- Network Deployment Engineer Intern (Summer 2026)
- Data Engineer Intern (Summer 2026)

### Why this matters
This was one of the biggest quality jumps so far.
The system moved closer to a real shortlist generator instead of a broad “internship dump.”

---

## Week 2 Snapshot (through Day 10)

### Current project state
InternLens currently supports:
- multi-source public ATS ingestion
  - Lever
  - Greenhouse
- raw snapshot saving
- processed schema normalization
- registry-driven batch fetching
- baseline ranking with blockers
- shortlist-oriented CLI filters
- API endpoints:
  - `/recommend`
  - `/jobs/{id}`

### Quality checkpoint
- Latest full test status: **71 passed**
- Cloudflare shortlist precision improved significantly
- Waymo shortlist remains highly focused under shortlist filters

### Remaining follow-up ideas
- Continue reducing remaining fallback-skill noise for edge-case internship titles.
- Refactor `baseline_scorer.py` so policy logic is split more cleanly.
- Polish docs and final demo flow.

---

## Day 11-12 - Dedupe, API Summaries, and Corpus Refresh

### Focus
Stabilize the processed job corpus, make recommendation output easier to consume, and add a repeatable refresh path for Lever and Greenhouse data.

### What was done
- Added duplicate suppression in job loading so legacy flat processed files no longer distort ranking results.
- Added `scripts/cleanup_processed_jobs.py` and removed older duplicate processed files from the root of `data/processed/jobs`.
- Expanded `/recommend` to return user-facing summaries such as:
  - overview counts
  - fit and eligibility labels
  - short recommendation summaries
  - `why_apply` and `watchouts`
- Expanded `/jobs/{id}` with short description, internship signals, possible requirements, blocker hints, and application link fields.
- Added `.github/workflows/python-tests.yml` to run `pytest -q` in CI.
- Added `scripts/refresh_job_corpus.py` plus `.github/workflows/refresh-job-corpus.yml` for scheduled or manual Lever/Greenhouse corpus refresh.
- Documented the long-term source acquisition plan in `docs/architecture/source_acquisition_strategy.md`.
- Added example seed and discovered-source files under `data/source_registry/`.

### Validation
- `pytest -q` -> **79 passed**

### Result
- The corpus is safer to load end-to-end without duplicate inflation.
- The API moved closer to a user-facing contract instead of a debug-first engine response.
- Lever and Greenhouse refresh now have a single orchestration entry point and a basic scheduled workflow.
- Source acquisition direction is now documented clearly enough to guide the next discovery implementation.

### Key takeaway
This stage shifted the project from "prototype pieces that work" toward "a backend pipeline that can be refreshed, explained, and evolved." The remaining gap is no longer core ingestion or ranking plumbing; it is source discovery and a user-facing recommendation flow built on top of the refreshed corpus.

---

## Day 13-14 - Source Discovery, Validation, and Promotion

### Focus
Reduce manual ATS registry maintenance by adding a full candidate-source workflow:
- discover new ATS sources from company seeds
- validate whether those sources are usable
- promote validated sources into active refresh registries

### What was done
- Added `scripts/discover_sources.py` and `src/discovery/source_discovery.py`.
- Implemented seed-based source discovery using `homepage_url` and `careers_url`.
- Added ATS URL extraction for:
  - `jobs.lever.co/<site_name>`
  - `boards.greenhouse.io/<board_token>`
  - `job-boards.greenhouse.io/<board_token>`
- Added `scripts/validate_sources.py` and `src/discovery/source_validation.py`.
- Implemented validation checks for discovered sources:
  - fetch success
  - non-empty job payload
  - normalization success
  - internship density estimate
  - duplicate detection against active registries
- Added `scripts/promote_sources.py` and `src/discovery/source_promotion.py`.
- Implemented promotion rules so validated sources can be inserted into:
  - `data/source_registry/lever_targets.json`
  - `data/source_registry/greenhouse_targets.json`
- Added safe reactivation behavior for inactive registry entries instead of duplicating them.
- Preserved source lifecycle metadata such as:
  - `last_validated_at`
  - `last_promoted_at`
  - `source_score`
  - `internship_likelihood`
- Updated README usage docs for discovery, validation, and promotion.

### Validation
- `pytest tests/test_source_discovery.py -q` -> **6 passed**
- `pytest tests/test_source_validation.py -q` -> **5 passed**
- `pytest tests/test_source_promotion.py -q` -> **4 passed**
- `pytest -q` -> **94 passed**

### Result
- InternLens now has a scriptable source lifecycle:
  - `discover_sources.py`
  - `validate_sources.py`
  - `promote_sources.py`
- New source candidates no longer need to be inserted manually at the registry stage.
- Discovery is still conservative because it produces candidates only.
- Validation now acts as a quality gate before production refresh.
- Promotion now gives a controlled path from discovered source to active registry target.

### Why this matters
This was a structural backend improvement rather than a ranking tweak.
Before this stage, InternLens could refresh only sources that were already known.
After this stage, the project can begin from company seeds and move sources through a staged pipeline with explicit control points.

### Updated Week 2 status
InternLens now supports:
- ATS ingestion
- corpus refresh
- duplicate suppression
- heuristic ranking
- API summaries
- company-seed-based source discovery
- discovered-source validation
- validated-source promotion into active registries

Latest quality checkpoint:
- full test suite stable at **94 passed**

### Remaining next steps
- add stricter promotion heuristics for noisy boards
- add source validation reports or promotion dry-run output
- connect the refreshed internal corpus to a default user-facing recommendation API flow
