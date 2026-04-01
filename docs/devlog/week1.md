# Week 1 Dev Log

## Day 1 Summary
- Created the GitHub repository and added the initial README with the project overview.
- Set up the initial project folder structure for source code, data, tests, and documentation.
- Added placeholder files to preserve empty directories in the repository.
- Resolved the branch mismatch between `master` and `main`.
- Pushed the initial project structure to GitHub.

## Day 1 Key Decisions
- GitHub will be the single source of truth for code, documentation, and development history.
- Project notes, architecture drafts, and weekly logs will be stored directly in the repository.
- The project will be positioned as an internship application strategy optimizer, not a generic job recommender.
- Early development will prioritize a simple, explainable baseline before moving to more advanced retrieval and ranking methods.

## Day 1 Problems Encountered
- The local branch name and remote branch name were inconsistent at the start.
- The initial repository structure had to be stabilized before real implementation work could begin.

## Day 1 Next Steps
- Define the schema for job postings.
- Define the schema for the candidate profile.
- Create the first architecture notes.
- Start organizing the files needed for the baseline pipeline.

## Day 1 Reflection
Day 1 focused on building the project foundation. There was no application logic yet, but setting up the repository structure and documentation workflow was necessary to keep the rest of development organized.

## Day 2 Summary
- Defined the initial schema for job postings and candidate profiles.
- Documented the schema in `docs/architecture/schema.md`.
- Created sample JSON files for one job posting and one candidate profile.
- Prepared the project structure for the baseline matching pipeline.
- Updated the sample candidate graduation date to better match the expected real profile timeline.

## Day 2 Key Decisions
- The project will use a shared normalized schema so ingestion and ranking can remain decoupled.
- Sample JSON files will be used early to validate parser and ranking behavior before real public-board ingestion is added.

## Day 2 Problems Encountered
- The schema needed to stay simple enough for a baseline implementation while still covering future ingestion needs.

## Day 2 Next Steps
- Implement parsers for candidate profiles and job postings.
- Build the first baseline ranking flow.
- Verify that the ranking output is readable and interpretable.

## Day 2 Reflection
Day 2 converted the initial idea into concrete data structures. Once the schema existed, the implementation path for parsing and baseline ranking became much clearer.

## Day 3 Summary
- Implemented parsers for candidate profiles and job postings.
- Built the first baseline ranking pipeline using skill match, role match, and location preference.
- Refactored the scoring logic to separate fit score from blocking constraints such as sponsorship availability.
- Improved the skill scoring method to measure coverage of job-required keywords instead of comparing against the full candidate skill inventory.
- Ran the first end-to-end baseline example and verified that the output was interpretable.

## Day 3 Key Decisions
- Fit score and blocking constraints should remain separate so the system can distinguish between a strong fit and an ineligible role.
- Ranking output should stay explainable even if it remains heuristic-based.

## Day 3 Problems Encountered
- Early scoring behavior was too naive and needed small adjustments before the results looked reasonable.

## Day 3 Next Steps
- Add more sample postings to make ranking comparisons more realistic.
- Export ranked results to files.
- Start exposing the pipeline through a lightweight API.

## Day 3 Reflection
Day 3 was the first real product milestone. The project moved from static schemas to an actual end-to-end ranking flow.

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

## Day 4 Key Decisions
- Stop further heuristic tuning once the baseline ranking became reasonably interpretable.
- Shift focus from raw score tweaking to productization: exports, API, tests, and docs.
- Keep fit score and blocking constraints separate so “good fit but blocked” remains visible.

## Day 4 Problems Encountered
- Some IDE type warnings appeared when response objects were returned as plain dictionaries instead of typed response models.
- Test expectations had to be updated after adding more sample jobs.
- Documentation started to drift from the current implementation as blocker logic expanded.

## Day 4 Next Steps
- Update `README.md` and `docs/architecture/overview.md` so docs match the blocker-aware logic.
- Decide whether the next major step should be feedback-based reranking or semantic retrieval.

## Day 4 Reflection
Day 4 turned the baseline into a more complete mini-product by adding exports, API access, tests, and clearer documentation.

## Day 5 Summary
- Cleaned up repo hygiene by fixing `.gitignore` behavior and removing tracked IDE artifacts.
- Updated ranking to use blocker-aware ordering so actionable jobs stay above skipped jobs.
- Unified candidate profile normalization for both file-based input and inline API payloads.
- Improved explanation text to make recommendation reasons read more naturally.
- Added feedback-based reranking v1 using simple signals such as `applied`, `saved`, and `skipped`.
- Connected feedback reranking to both the local script flow and the FastAPI `/recommend` endpoint.
- Updated README and architecture docs to reflect the latest ranking and reranking behavior.

## Day 5 Key Decisions
- Treat feedback reranking as a lightweight personalization layer rather than replacing the baseline ranker.
- Keep explanation text simple and readable for demo use.
- Continue using small, test-backed increments instead of large refactors.

## Day 5 Problems Encountered
- Repository hygiene issues had to be fixed before continuing with clean commits.
- Documentation needed another alignment pass after reranking behavior changed.

## Day 5 Next Steps
- Add inline feedback payload support in the API.
- Improve reranking explainability.
- Decide whether to continue feedback improvements or move toward semantic retrieval.

## Day 5 Reflection
Day 5 made the project feel more personalized and product-like. The system started moving beyond pure baseline ranking toward user-specific reranking behavior.

## Day 6 Summary
- Extended `feedback_reranker.py` so reranking now produces compact explanation items instead of only numeric score adjustments.
- Added `feedback_explanations` to each reranked result, including feedback source title, label, similarity, adjustment, and shared token signals.
- Updated the FastAPI response model so `/recommend` exposes explanation-aware reranking output.
- Updated `run_baseline.py` so local console output and exported CSV/JSON files also include feedback explanation details.
- Added new tests for explanation fields in reranking logic and API responses.
- Added `tests/conftest.py` so `pytest -q` works cleanly without manual `PYTHONPATH` setup.
- Updated project documentation to match the current reranking behavior.

## Day 6 Key Decisions
- Keep the explanation format lightweight and token-based instead of introducing heavier semantic similarity logic too early.
- Preserve blocker-aware ordering so personalization remains visible without overriding policy logic.
- Prioritize explainability and demo clarity over aggressive score optimization.

## Day 6 Problems Encountered
- `pytest` initially failed during test collection because the `src` package was not on the import path by default.
- Documentation again lagged behind the newly added explanation fields and needed another consistency pass.

## Day 6 Next Steps
- Add inline feedback payload support so reranking can be tested without a file dependency.
- Revisit whether blocked jobs should receive capped feedback boosts within the `Skip` bucket.
- Continue improving explanation phrasing.

## Day 6 Reflection
Day 6 improved transparency. The reranking system became easier to explain in both the API and the CLI, which helps demo quality and debugging.

## Day 7 Summary
- Refactored feedback validation into shared normalization logic so file-based and inline feedback use the same rules.
- Added `feedback_data` support to `/recommend` alongside the existing `feedback_path` option.
- Added typed payload models for inline feedback events and feedback profiles.
- Set the API to prioritize inline feedback when both `feedback_data` and `feedback_path` are provided.
- Added tests for inline feedback normalization, inline reranking behavior, and input-priority handling.
- Updated README, architecture notes, and dev log entries to reflect the new API behavior.

## Day 7 Key Decisions
- Reuse shared normalization instead of duplicating validation logic in the API layer.
- Keep file-based feedback support backward compatible.
- Treat inline feedback as the higher-priority source because it is the most explicit request payload.

## Day 7 Problems Encountered
- Documentation needed another update pass after the API contract changed.
- Care was needed to keep behavior consistent across file-based and inline feedback flows.

## Day 7 Next Steps
- Improve feedback score calibration and explanation phrasing.
- Decide whether blocked jobs should receive capped reranking boosts.
- Evaluate whether the next milestone should be semantic retrieval or stronger learning-to-rank style scoring.

## Day 7 Reflection
Day 7 completed the first round of feedback-driven personalization by making the API input model more flexible and easier to use.
