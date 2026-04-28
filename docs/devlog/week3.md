# Week 3 Devlog

## Day 19-23 - School Exam Pause

### Status
- Active feature development paused for about one week because of the school exam period.
- No major code changes were made during this window.
- The project was intentionally left at the previous stable backend checkpoint rather than starting partially finished work.

### Why this is recorded
This pause explains the gap between development sessions and keeps the project timeline honest.
The project was not blocked technically; development capacity was temporarily redirected to coursework and exams.

### Outcome
- No architecture changes.
- No new features.
- No test baseline changes.
- Development resumed after exams with the existing profile, dashboard, and job-action APIs still stable.

---

## Day 24 - Frontend Environment Recovery and Dashboard MVP

### Focus
Restart development after the exam pause and begin turning the product backend into a visible user workflow.

### What was done
- Verified and repaired the local development environment.
- Recreated the Python virtual environment with Python 3.13 after the previous Python 3.14 environment exposed `_ctypes` DLL failures.
- Added a Vite/React frontend under `frontend/`.
- Added FastAPI CORS support for local frontend development from:
  - `http://localhost:5173`
  - `http://127.0.0.1:5173`
- Added `.gitignore` rules for frontend generated artifacts:
  - `frontend/node_modules/`
  - `frontend/dist/`
- Built the first frontend dashboard MVP with:
  - profile setup form
  - dashboard summary panel
  - recommendation run trigger
  - recent run loading
  - saved and applied job previews
  - job action buttons for save, applied, and dismiss

### Validation
- `npm run build` -> passed
- `pytest -q` -> **124 passed**

### Result
InternLens now has a browser-based entry point for the stored-profile recommendation flow.
The UI is still lightweight, but it can exercise the main product loop:
create or load a profile, run recommendations, inspect results, and record job actions.

### Key takeaway
This was the transition from API-only product work to a usable frontend surface.
The backend was already capable of supporting a dashboard; this step made that workflow visible and easier to demo.

---

## Day 25 - Frontend Session Persistence and API Status

### Focus
Make the new frontend less fragile during manual testing and demos.

### What was done
- Added local browser session persistence using `localStorage`.
- Restored profile form data, active profile ID, selected recommendation run, and recommendation filter after refresh.
- Added API health checking against `/health`.
- Added an online/offline/checking badge in the UI.
- Added a manual `Check API` action.
- Improved job-action refresh behavior so the UI avoids unnecessary run reloads when no run is selected.

### Validation
- `npm run build` -> passed
- `pytest -q` -> **124 passed**

### Result
The frontend now survives page refreshes more gracefully.
Users can tell whether the backend is reachable without opening browser developer tools or checking terminal logs.

### Why this matters
Session continuity is small but important product glue.
Without it, the UI feels like a thin API test page.
With it, the app starts to feel like a persistent workflow.

---

## Day 26 - Recommendation Results UI

### Focus
Make recommendation output easier to scan and act on.

### What was done
- Added recommendation filters:
  - `All`
  - `Apply Now`
  - `Apply Later`
  - `Skip`
- Added per-filter counts.
- Changed the frontend recommendation request to use `include_debug=true` so the UI can show score and action-label details.
- Split recommendation cards into clearer frontend components:
  - `JobCard`
  - `ScoreDial`
  - `EvidenceList`
- Added visual score dials.
- Added clearer action pills for `Apply Now`, `Apply Later`, and `Skip`.
- Added separate evidence sections for:
  - why the job fits
  - watchouts
- Added stronger visual treatment for high-priority and skipped jobs.

### Validation
- `npm run build` -> passed
- `pytest -q` -> **124 passed**

### Result
Recommendation results are now much easier to inspect.
The UI better communicates both the ranking decision and the next action a user should take.

### Key takeaway
This stage improved demo quality significantly.
The frontend is still not a complete application, but the recommendation list now feels closer to a real shortlist review tool.

---

## Week 3 Snapshot

### Current project state
InternLens now supports:
- ATS ingestion and normalization for Lever and Greenhouse
- source discovery, validation, promotion, and refresh workflows
- deduplicated processed job loading
- heuristic internship ranking with blockers
- feedback-aware reranking
- stored profiles
- persisted recommendation runs
- saved, dismissed, and applied job actions
- dashboard and activity APIs
- a Vite/React frontend for profile setup, dashboard review, recommendation runs, and job actions

### Latest quality checkpoint
- Frontend production build passing through `npm run build`
- Backend test suite stable at **158 passed** on the latest local recheck
- Python environment stabilized on Python 3.13

### Remaining next steps
- Improve frontend empty states and error messages.
- Add clearer applied/saved/dismissed state transitions in recommendation cards.
- Add screenshots or a short demo walkthrough once the UI flow stabilizes.
- Consider adding a lightweight frontend lint/test setup.
- Continue keeping docs updated at end-of-day checkpoints rather than after every feature commit.

---

## Day 27 - Seed Expansion and Discovery Dry Run

### Focus
Stress-test the company-seed-based discovery path with a much wider seed draft before tightening the source pipeline.

### What was done
- Added a larger working `company_seeds.json` draft under `data/source_registry/`.
- Expanded the seed list to `144` companies across AI, security, data, developer tools, fintech, marketplace, and autonomy targets.
- Ran discovery against the wider draft to see where the current implementation breaks before promoting any new sources.

### What the dry run showed
- Full discovery over the larger seed set is currently slow because discovery fetches company pages sequentially.
- Some careers pages returned `403 Forbidden` or `429 Too Many Requests`, which means the current HTML-fetch strategy is not robust enough for broad scans.
- Discovery quality is not clean enough yet:
  - some good candidates were found, such as `honehealth`, `figma`, `vercel`, and a few Lever/Greenhouse boards
  - at least one false-positive Greenhouse candidate was produced from an embed helper URL, yielding `source_identifier = "embed"`
- The generated `discovered_sources.json` from this run is useful for debugging, but it is not yet trustworthy enough to treat as canonical registry input.

### Result
The larger seed list is useful as a stress harness, but the discovery pipeline still needs hardening before wide scans become reliable.

### Immediate next fixes
- reject non-board Greenhouse embed URLs during discovery
- preserve partial results during long runs
- handle `403` and `429` more gracefully
- consider limited parallelism after correctness issues are fixed first

---

## Day 28 - Discovery Hardening and Probe Evaluation

### Focus
Turn the wide company-seed discovery path from a fragile scan into a more inspectable candidate-generation workflow.

### What was done
- Rejected non-board ATS helper URLs such as Greenhouse `embed` paths.
- Normalized nested Lever and Greenhouse URLs back to source identifiers.
- Added checkpointed discovery saves through `--checkpoint-size` and `--discovery-checkpoint-size`.
- Added structured discovery warnings with reason summaries.
- Added opt-in direct ATS probing with `--probe-direct-ats`.
- Added opt-in blocked-page manual review records with `--record-blocked-sources`.
- Suppressed noisy direct-probe miss details while preserving their summary counts.

### Probe results
- Baseline discovery over `144` seeds found `14` candidates.
- Validation of the baseline probe produced `13` validated sources and `1` rejected source.
- Discovery with direct ATS probing and blocked-page records produced `82` records.
- Validation of the improved probe produced:
  - `68` validated sources
  - `1` rejected source
  - `13` blocked manual-review records
- Promotion-like candidates increased from `3` to `15` under the current score and internship-signal heuristics.

### Validation
- `pytest tests/test_source_discovery.py -q` -> **20 passed**
- `pytest tests/test_run_source_pipeline.py tests/test_source_validation.py tests/test_source_promotion.py -q` -> **12 passed**
- `pytest -q` -> **145 passed**

### Result
Direct ATS probing materially improved source recall without changing the default discovery behavior.
Blocked-page records now preserve useful operator-review work without pretending that blocked careers pages are validated source records.

### Remaining next fixes
- Tune source promotion thresholds for direct-probe candidates.
- Keep manual-review records out of automatic promotion.
- Decide whether probe output files should stay local-only or become explicit debugging artifacts.

---

## Day 29 - Source Promotion Safeguards and Discovery Diagnostics

### Focus
Make broad source discovery safer to inspect before any new sources are promoted into active registries.

### What was done
- Added `promote_sources.py --dry-run` so promotion decisions can be inspected without writing registry files.
- Added direct-probe-specific promotion safeguards for minimum score and internship likelihood.
- Added a global minimum internship-likelihood threshold for promotion.
- Stopped inactive registry entries from being reactivated unless `--reactivate-inactive-sources` is explicitly passed.
- Tightened Lever internship matching so words such as `internal` and `international` do not create internship false positives.
- Aligned Greenhouse validation internship matching with the stricter refresh filter.
- Increased the default validation sample from `25` to `100` jobs.
- Preserved blocked/manual-review records during `--include-non-candidate` revalidation.
- Marked promoted Lever sources as `internship_only` by default.
- Added validation `internship_signal_examples` and surfaced those examples in promotion dry-run output.
- Added same-site priority-link following for high-intent discovery pages such as student, internship, campus, university, jobs, and early-career pages.
- Added discovery method summaries so broad runs show whether candidates came from careers pages, priority links, direct seed URLs, or direct ATS probes.

### Probe and smoke results
- Revalidating the existing broad probe with stricter rules kept `68` validated ATS records, `1` rejected record, and `13` blocked manual-review records.
- Promotion dry-run on the latest probe promoted `0` new sources.
- Cloudflare remained skipped because it is inactive in the registry by default.
- Zoox showed internship signal examples but was still blocked by the direct-probe safeguard.
- A small seed-subset smoke comparing `--priority-follow-limit 0` and `5` found the same Figma candidate in both cases, so the new priority-link logic is safer but still needs broader recall measurement.

### Validation
- `pytest tests/test_source_discovery.py -q` -> **23 passed**
- `pytest tests/test_source_discovery.py tests/test_source_validation.py tests/test_source_promotion.py tests/test_run_source_pipeline.py -q` -> **44 passed**
- `pytest -q` -> **158 passed**

### Result
Broad discovery is now more conservative and more inspectable.
The system is better at explaining why a source looks internship-relevant, while avoiding automatic promotion of broad public boards that would likely hurt shortlist quality.

### Remaining next fixes
- Measure priority-link recall on a larger seed subset.
- Use dry-run internship examples to tune validation and promotion thresholds.
- Consider a repeatable promotion smoke script that fetches temporary promoted candidates and reports applyable ranking counts.
