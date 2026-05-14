# AGENTS.md

## Purpose

This file gives future coding agents a practical operating guide for `InternLens`.
It is intentionally specific to the current project stage as of the latest local validation checkpoint.

## Project Snapshot

InternLens is currently a demoable internship discovery product prototype with:

- public ATS ingestion for Lever and Greenhouse
- raw snapshot saving under `data/raw/...`
- normalized processed job JSON output under `data/processed/jobs/...`
- registry-driven refresh and source discovery workflows
- heuristic internship ranking with blocker logic
- feedback-based reranking
- CLI output/export flow
- FastAPI endpoints for recommendations, job detail lookup, profiles, feedback, job actions, recommendation history, and dashboard data
- local SQLite-backed profile and recommendation persistence
- Vite/React frontend for profile setup, dashboard review, recommendation runs, and job actions
- GitHub Actions workflows for tests and corpus refresh artifacts
- regression coverage is healthy; confirm the latest exact count with `.\.venv\Scripts\python.exe -m pytest -q` when needed

This is not yet a production system. It is a strong prototype with real data, good test coverage, a usable local UI, and clear extension points.

## Current Development Stage

The project has moved past the "toy baseline" phase.

What is stable:

- source ingestion and normalization flow
- profile parsing and recursive job loading
- baseline ranking and blocker logic
- feedback reranking
- CLI shortlist workflow
- FastAPI request/response flow for recommendation and profile workflows
- SQLite-backed local profile, feedback, recommendation run, and job action persistence
- Vite/React dashboard workflow
- GitHub Actions test workflow
- test suite reliability

What is still in progress:

- shortlist precision cleanup for noisy public boards
- location normalization quality for ATS data
- cleanup of processed job layout drift in generated data
- source discovery quality for broad company-seed scans
- frontend empty states, error states, and job-state transition polish
- documentation consistency after changes

What is not built yet:

- learned ranking / embeddings / retrieval
- production-grade multi-user persistence
- frontend lint/test setup

## Source of Truth

Use these files first when reasoning about behavior:

- `README.md`
- `docs/architecture/overview.md`
- `docs/architecture/schema.md`
- `src/ranking/baseline_scorer.py`
- `src/ingestion/greenhouse_client.py`
- `src/ingestion/lever_client.py`
- `src/api/app.py`
- `src/storage/profile_store.py`
- `frontend/src/main.jsx`

For current quality expectations, read:

- `tests/test_api_and_ranking.py`
- `tests/test_baseline_scorer_seniority.py`
- `tests/test_greenhouse_client.py`
- `tests/test_lever_client.py`
- `tests/test_greenhouse_registry.py`
- `tests/test_lever_registry.py`
- `tests/test_profile_api.py`
- `tests/test_jobs_api.py`
- `tests/test_source_discovery.py`
- `tests/test_source_validation.py`
- `tests/test_source_promotion.py`
- `tests/test_run_source_pipeline.py`

## Working Principles

1. Preserve CLI/API parity.
   If ranking behavior changes, make sure both `scripts/run_baseline.py` and `src/api/app.py` still expose the same underlying logic.

2. Prefer small, test-backed changes.
   This repository is already in a productive state. Avoid large refactors unless the payoff is obvious and tests are expanded with the change.

3. Keep ranking interpretable.
   The current system is heuristic by design. New logic should remain explainable through reasons, blockers, and component scores.

4. Treat ingestion and ranking as separate layers.
   Normalize source-specific quirks in ingestion code instead of leaking ATS-specific assumptions into the scorer.

5. Preserve sample-data workflows.
   `data/sample_jobs` and `data/processed/candidate_profile_example.json` are still important for tests, demos, and quick local validation.

## Current Priorities

When choosing what to improve next, bias toward these:

- reduce false positives in internship ranking
- improve normalization quality for noisy ATS fields
- keep duplicate processed jobs controlled through loader and output suppression behavior
- keep shortlist outputs readable and demo-friendly
- harden company-seed-based source discovery before promoting broad scans
- improve frontend empty/error states and saved/applied/dismissed state transitions
- avoid changes that make explanations worse

Lower priority for now:

- architectural rewrites
- model-heavy experimentation
- broad dependency additions

## Known Risks and Footguns

1. Processed job duplication/layout drift exists in generated data.
   `data/processed/jobs` may contain nested source folders and older flat files. The loader suppresses duplicate `job_id` values and conservative content duplicates by default, but avoid rewriting the data tree unless the task explicitly requires regeneration.

2. Public ATS content is noisy.
   Greenhouse and Lever postings often have sparse or misleading structured fields. Avoid assuming clean `employment_type`, `location`, or qualification sections.

3. Generated outputs are not canonical fixtures.
   Files under `outputs/` are useful for manual inspection, but do not treat them as stable source-of-truth test fixtures.

4. Raw and processed data are large and evolving.
   Do not rewrite large data directories unless the task explicitly requires regeneration.

5. Cloudflare is intentionally noisy.
   The current registry marks Cloudflare inactive by default because it is useful for evaluation but still requires precision safeguards.

6. Broad source discovery is not promotion-ready yet.
   The large company seed draft is useful for stress testing, but discovery can be slow and may hit `403` or `429`.
   Non-board ATS helper URLs are rejected, but broad boards can still look internship-relevant from sparse signal examples and should be reviewed through promotion dry-run output before registry changes.

## Editing Guidance

- Prefer modifying code in `src/` and `scripts/` before touching generated data.
- If you change ranking semantics, update or add tests before considering the task done.
- If you change normalization semantics, check both unit tests and downstream ranking behavior.
- If you add fields to API responses, update Pydantic response models and API tests together.
- If you add new CLI behavior, preserve existing flags and output file conventions unless there is a strong reason not to.
- Do not update tracked documentation or validation-count text after every code change. Defer README, architecture docs, and devlog synchronization to an explicit end-of-day documentation pass unless the user asks for docs in the same task.

## Documentation Policy

Documentation has grown with the product surface, so keep each file's job distinct:

- Keep `README.md` short and scannable.
  It should explain what InternLens does, the current product surface, the architecture map, quick start commands, AWS staging shape, documentation links, and the latest quality checkpoint. Move long setup notes, implementation details, and historical context into `docs/`.
- Use `docs/architecture/overview.md` for durable system behavior.
  Update it when API boundaries, persistence shape, frontend workflow, ranking semantics, or deployment architecture changes.
- Use focused architecture docs for deep details.
  Ranking behavior belongs in `docs/architecture/ranking_logic.md`; schema and data contracts belong in `docs/architecture/schema.md`; source acquisition behavior belongs in `docs/architecture/source_acquisition_strategy.md`.
- Use `docs/development/local_workflows.md` for commands and developer workflows.
  Put local API examples, refresh commands, smoke checks, and validation commands there instead of expanding the README.
- Use `docs/deployment/aws_staging.md` for AWS operational steps.
  Keep deployment, pipeline, environment variable, credential, smoke-test, and rollback guidance out of the README unless it is only a short pointer.
- Use `docs/devlog/week*.md` for chronological development notes.
  Devlog entries should capture what changed, why, validation results, and remaining follow-ups. Do not turn devlog entries into full implementation specs.
- Update validation counts only after running the matching checks in the same work session.
  If only targeted tests were run, say that clearly. Do not copy stale counts forward.
- Document user-visible changes in the same task when the user asks for a documentation pass, deployment handoff, or commit/push checkpoint.
  For ordinary code changes, keep docs limited to files required to explain changed behavior.
- Avoid committing generated data or runtime state as documentation evidence.
  Use summaries, command outputs, or small curated examples instead of tracking files under `outputs/` or `data/app/` unless the task explicitly requires a generated artifact.

## Validation Checklist

Run the full suite before closing substantial changes:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Useful targeted checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_and_ranking.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_baseline_scorer_seniority.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_greenhouse_client.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_lever_client.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_run_baseline_cli.py -q
```

Manual smoke checks when relevant:

```powershell
.\.venv\Scripts\python.exe scripts\run_baseline.py
.\.venv\Scripts\python.exe scripts\run_baseline.py --jobs-dir data\processed\jobs\greenhouse\waymo --applyable-only
.\.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload
cd frontend
npm run build
npm run dev
```

## Preferred Change Pattern

For most tasks:

1. Read the relevant module and its tests.
2. Make the smallest coherent code change.
3. Update tests to describe the intended behavior.
4. Run targeted tests.
5. Run the full suite if the change is non-trivial.
6. Mention any generated data or output files that changed as a side effect.

## Commit Convention

- Use Conventional Commit style messages matching existing history, such as `feat: ...`, `refactor: ...`, `docs: ...`, or `chore: ...`.
- Keep the subject line lowercase, concise, and focused on the main outcome.
- Group closely related code, config, and doc changes into one commit when they serve the same task.

## If You Need to Touch Data Layout

Be careful around:

- `data/processed/jobs`
- `data/raw`
- `data/source_registry`

Expect side effects on:

- ranking output volume
- duplicate loading behavior
- output JSON/CSV files
- docs that mention job counts or shortlist examples

If you change data layout semantics, document it in `README.md`.

## Near-Term Roadmap

Reasonable next milestones:

- harden source discovery by rejecting non-board ATS helper URLs and preserving partial results
- measure priority-link source discovery recall on larger seed subsets
- use promotion dry-run internship examples to tune validation and promotion thresholds
- tighten remaining non-core internship false positives
- improve company/team/location normalization
- improve frontend empty/error states and job action state transitions
- add a lightweight frontend lint/test setup
- prepare cleaner demo documentation and screenshots

## Default Mindset

This repository rewards pragmatic iteration over ambitious redesign.
Make the shortlist more useful, keep the system explainable, and do not silently break the current demo flow.
