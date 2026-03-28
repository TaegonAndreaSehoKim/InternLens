# Week 1 Dev Log

## Day 1 Summary
- Created the GitHub repository and added the initial README with the project overview.
- Set up the initial project folder structure for source code, data, tests, and documentation.
- Added placeholder files to preserve empty directories in the repository.
- Resolved the branch mismatch between `master` and `main`.
- Pushed the initial project structure to GitHub.

## Key Decisions
- GitHub will serve as the single source of truth for code, documentation, and development history.
- Project notes, architecture drafts, and weekly logs will be stored directly in the repository instead of using external tools.
- The project will be positioned as an internship application strategy optimizer, not a generic job recommendation tool.
- Early development will prioritize a simple, explainable baseline before moving to more advanced retrieval and ranking methods.

## Next Steps
- Define the schema for job postings.
- Define the schema for the candidate profile.
- Create the first architecture notes.
- Start organizing the files needed for the baseline pipeline.

## Reflection
Day 1 was mainly about setting up the project foundation. Although no application logic was implemented yet, establishing the repository structure and documentation workflow was important for keeping development organized from the beginning.

## Day 2 Summary
- Defined the initial schema for job postings and candidate profiles.
- Documented the schema in `docs/architecture/schema.md`.
- Created sample JSON files for one job posting and one candidate profile.
- Prepared the project structure for the baseline matching pipeline.
- Updated the sample candidate graduation date to match the expected real profile timeline more closely.

## Day 3 Summary
- Implemented parsers for candidate profiles and job postings.
- Built the first baseline ranking pipeline using skill match, role match, and location preference.
- Refactored the scoring logic to separate fit score from blocking constraints such as sponsorship availability.
- Improved the skill scoring method to measure coverage of job-required keywords instead of comparing against the full candidate skill inventory.
- Ran the first end-to-end baseline example and verified that the output was interpretable.

## Day 4 Summary
- Added multiple sample internship postings to make ranking comparisons more realistic.
- Improved the baseline ranking logic by filtering overly generic role-title tokens and adding simple skill alias normalization.
- Added JSON and CSV export for ranked results through `run_baseline.py`.
- Built the first FastAPI version of the project with `/health` and `/recommend` endpoints.
- Extended `/recommend` to support inline profile payloads in addition to file-based profile input.
- Added pytest coverage for core API behavior, sponsorship blocking, ranking order, and blocker-focused cases.
- Added an architecture overview document and started documenting the current system flow more clearly.
- Expanded blocker logic beyond sponsorship to include additional eligibility-style checks.
- Added a blocker-focused sample job to verify that non-internship and PhD-related constraints are surfaced correctly.

## Key Decisions
- Stopped further heuristic tuning once the baseline ranking became reasonably interpretable.
- Shifted focus from score tweaking to productization: exports, API, tests, and project documentation.
- Kept fit score and blocking constraints separate so that the system can distinguish between "good fit but blocked" and "weak fit."

## Problems Encountered
- Some IDE type warnings appeared when response objects were returned as plain dictionaries instead of typed response models.
- Test expectations had to be updated after adding more sample jobs to the dataset.
- Documentation started to drift slightly from the current implementation as blocker logic expanded.

## Next Steps
- Update `README.md` and `docs/architecture/overview.md` so the documentation matches the current blocker logic.
- Consider adding one more blocker-focused example if needed for demo clarity.
- Decide whether the next major step should be feedback-based reranking or semantic retrieval.

## Day 5

Today I focused on improving InternLens from a working baseline into a more product-like recommendation tool.

### What I changed
- Cleaned up repo hygiene by fixing `.gitignore` behavior and removing tracked IDE artifacts.
- Updated ranking to use **blocker-aware ordering** so actionable jobs stay above skipped jobs.
- Unified candidate profile normalization for both file-based input and inline API payloads.
- Improved explanation text to make recommendation reasons read more naturally.
- Added **feedback-based reranking v1** using simple feedback signals such as `applied`, `saved`, and `skipped`.
- Connected feedback reranking to both the local script flow and the FastAPI `/recommend` endpoint.
- Updated README and architecture docs to reflect the latest ranking and reranking behavior.

### Validation
- Expanded tests and ended the session with **15 passing tests**.
- Manually verified the `/recommend` endpoint with feedback input.

### Next steps
- Consider adding inline feedback payload support in the API.
- Improve reranking explainability.
- Decide whether to continue improving feedback reranking or move toward semantic retrieval.

## Day 6

Today I focused on making feedback-based personalization more transparent and easier to demo.

### What I changed
- Extended `feedback_reranker.py` so reranking now produces compact explanation items instead of only numeric score adjustments.
- Added `feedback_explanations` to each reranked result, including:
  - source feedback job ID
  - source feedback job title
  - feedback label
  - similarity
  - adjustment
  - shared title tokens
  - shared skill tokens
- Updated the FastAPI response model so `/recommend` exposes explanation-aware reranking output.
- Updated `run_baseline.py` so local console output and exported CSV/JSON files also include feedback explanation details.
- Added new tests for explanation fields in both reranking logic and API responses.
- Added `tests/conftest.py` so `pytest -q` works cleanly without requiring manual `PYTHONPATH` setup.
- Updated project documentation to match the current reranking behavior.

### Validation
- Ran the local script with `--feedback-path` and confirmed explanation details appeared in reranked output.
- Ran the full test suite and ended the session with **17 passing tests**.

### Key decisions
- Kept the explanation format lightweight and token-based instead of introducing heavier semantic similarity logic too early.
- Preserved blocker-aware ordering so personalization remains visible but does not override recommendation policy.
- Prioritized explainability and demo clarity over aggressive score optimization.

### Problems encountered
- `pytest` initially failed during test collection because the `src` package was not on the import path by default.
- Documentation lagged behind the newly added explanation fields and needed another consistency pass.

### Next steps
- Add inline feedback payload support so reranking can be tested without a file dependency.
- Revisit whether blocked jobs should receive capped feedback boosts within the `Skip` bucket.
- Improve explanation phrasing further so API and console outputs read more naturally in demos.
- Decide whether the next major milestone should be richer feedback calibration or semantic retrieval.
