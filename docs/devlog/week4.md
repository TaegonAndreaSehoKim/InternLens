# Week 4 Devlog

Week 4 covers Day 27-33.
The focus shifted from frontend workflow basics to source-discovery quality, promotion safety, and repeatable discovery evaluation.

## Day 27 - Seed Expansion and Discovery Dry Run

### Focus
Stress-test the company-seed-based discovery path with a much wider seed draft before tightening the source pipeline.

### What was done
- Added a larger working `company_seeds.json` draft under `data/source_registry/`.
- Expanded the seed list to `144` companies across AI, security, data, developer tools, fintech, marketplace, and autonomy targets.
- Ran discovery against the wider draft to see where the current implementation breaks before promoting any new sources.

### What the dry run showed
- Full discovery over the larger seed set is slow because company pages are fetched sequentially.
- Some careers pages returned `403 Forbidden` or `429 Too Many Requests`.
- Discovery quality was not yet clean enough for automatic registry changes.
- At least one false-positive Greenhouse candidate came from a helper/embed URL.

### Result
The larger seed list became a useful stress harness, but the discovery pipeline needed hardening before wide scans could be trusted.

---

## Day 28 - Discovery Hardening and Probe Evaluation

### Focus
Turn wide company-seed discovery from a fragile scan into a more inspectable candidate-generation workflow.

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
- Direct ATS probing and blocked-page records produced `82` records.
- Validation of the improved probe produced:
  - `68` validated sources
  - `1` rejected source
  - `13` blocked manual-review records
- Promotion-like candidates increased from `3` to `15` under the then-current heuristics.

### Validation
- `pytest tests/test_source_discovery.py -q` -> **20 passed**
- `pytest tests/test_run_source_pipeline.py tests/test_source_validation.py tests/test_source_promotion.py -q` -> **12 passed**
- `pytest -q` -> **145 passed**

### Result
Direct ATS probing materially improved source recall without changing the default discovery behavior.
Blocked-page records now preserve useful operator-review work without pretending that blocked careers pages are validated source records.

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
- Added same-site priority-link following for high-intent discovery pages.
- Added discovery method summaries.

### Probe and smoke results
- Revalidating the existing broad probe kept `68` validated ATS records, `1` rejected record, and `13` blocked manual-review records.
- Promotion dry-run on the latest probe promoted `0` new sources.
- A small seed-subset smoke found the same Figma candidate with and without priority-link following.

### Validation
- `pytest tests/test_source_discovery.py -q` -> **23 passed**
- `pytest tests/test_source_discovery.py tests/test_source_validation.py tests/test_source_promotion.py tests/test_run_source_pipeline.py -q` -> **44 passed**
- `pytest -q` -> **158 passed**

### Result
Broad discovery became more conservative and more explainable.
The system got better at showing why a source looks internship-relevant while avoiding automatic promotion of broad boards.

---

## Day 30 - Discovery Recall Measurement and Promotion Smoke

### Focus
Turn discovery recall and promotion quality checks into repeatable scripts instead of one-off manual command chains.

### What was done
- Added `scripts/compare_discovery_recall.py`.
- Added ignored comparison reports under `outputs/discovery_recall_compare*.json`.
- Added `scripts/smoke_promotion_candidates.py`.
- Added ignored promotion smoke reports under `outputs/promotion_candidate_smoke*.json`.
- Added tests for discovery recall comparison and promotion-candidate smoke reports.
- Prioritized high-intent discovery links before generic jobs/careers links.

### Smoke results
- A 30-seed recall comparison found:
  - baseline candidates: `2`
  - priority-follow candidates: `4`
  - added candidates: Anthropic and GitLab Greenhouse boards
  - warnings: `5 -> 9`
- Anthropic and GitLab validated as fetchable boards but had `internship_likelihood = 0.00`.
- Promotion-candidate smoke reported `Promotion candidates: 0`.

### Validation
- `pytest tests/test_compare_discovery_recall.py tests/test_source_discovery.py -q` -> **25 passed**
- `pytest tests/test_smoke_promotion_candidates.py tests/test_source_promotion.py -q` -> **12 passed**
- `pytest -q` -> **163 passed**

### Result
Discovery recall became measurable, and promotion quality could be checked through temporary fetch/rank smoke without touching tracked registries or generated corpus data.

---

## Day 31 - Frontend Safety Net and Larger Discovery Recall Check

### Focus
Continue stabilization after the recommendation UI and discovery smoke tooling reached a usable checkpoint.

### What was done
- Polished frontend job-state handling for saved, applied, dismissed, and cleared jobs.
- Added clearer empty-state and API-status treatment.
- Added a lightweight frontend quality setup:
  - `npm run lint`
  - `npm test`
  - pure recommendation UI helper tests with Vitest
- Ran a larger source discovery recall comparison over the first `60` company seeds.

### Larger recall result
- Baseline candidates: `4`
- Priority-follow candidates: `6`
- Added candidates:
  - Anthropic Greenhouse board
  - GitLab Greenhouse board
- Warning count increased from `17` to `36`.

### Result
Priority-link following improved raw source recall, but the first 60-seed run did not find new internship-rich boards beyond the same Anthropic and GitLab general boards.
The warning growth confirmed that broader priority-link scans needed noise control.

---

## Day 32 - Priority-Follow Warning Budget and Offset Recall Check

### Focus
Reduce noisy priority-link discovery fetches and compare recall on a different company-seed window.

### What was done
- Added a per-company priority-follow warning budget.
- Added a per-host priority-follow warning budget.
- Exposed the new budget controls through:
  - `scripts/discover_sources.py`
  - `scripts/compare_discovery_recall.py`
- Ran a second 60-seed recall comparison against the `60-120` seed window.

### Offset recall result
- Baseline candidates: `7`
- Priority-follow candidates: `9`
- Added candidates:
  - Checkr Greenhouse board: `checkr`
  - Checkr-linked Greenhouse board: `chile`
- Warning count increased from `14` to `29`.

### Result
The second seed window confirmed that priority-link following continues to improve raw source recall.
It also exposed a likely quality issue where a Checkr priority page linked to a `chile` Greenhouse board identifier.

---

## Day 33 - Recall Added-Source Smoke Gate

### Focus
Make promotion smoke easier to run directly from discovery recall comparison output.

### What was done
- Added `scripts/smoke_promotion_candidates.py --input-format recall-added`.
- Added `scripts/smoke_promotion_candidates.py --validate-input`.
- The smoke script can now read `added_sources` from a recall comparison report, validate those candidates, apply promotion thresholds, and fetch/rank only promotable sources.
- Added tests for recall-added input loading and validation-before-smoke behavior.

### Smoke result
- Input added sources: `2`
- Validation attempted: `2`
- Validation succeeded: `2`
- Promotion candidates: `0`
- Promotion summary:
  - `skipped_score: 2`
- Processed jobs: `0`

### Result
The new gate confirmed that the Checkr-related priority-follow additions are fetchable, but they do not clear the current promotion threshold.
This is the intended behavior: recall discoveries can now be checked through validation and promotion smoke without manual JSON extraction or registry changes.

---

## Week 4 Snapshot

### Current project state
- Source discovery is broader but more conservative.
- Promotion decisions are inspectable through dry-run and smoke reports.
- Priority-link recall can be measured across seed windows.
- Frontend lint/test commands now exist.

### Latest quality checkpoint
- Backend test suite reached **163 passed** during this week.
- Frontend checks added:
  - `npm run lint`
  - `npm test`
  - `npm run build`

### Remaining next steps
- Keep broad discovery output behind validation and promotion smoke gates.
- Improve company/board alignment checks before promotion.
- Continue reducing warning noise in priority-link scans.
