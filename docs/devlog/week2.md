# Week 2 - Day 1 Dev Log

## Summary

Today focused on improving ranking precision, Greenhouse normalization quality, and shortlist usability.

The project remains stable after these changes, and the current validation state is `68 passed`.

---

## Completed today

### 1. Ranking refinement
- reduced noisy fallback skill matching for non-technical internship titles
- kept fallback skill matching for technical, research, engineering, and data-oriented roles
- preserved ranking stability through regression tests

### 2. Greenhouse location normalization
- improved geographic location extraction using Greenhouse metadata
- reduced dependence on generic work-mode labels such as `Hybrid` and `In-Office`
- cleaned stale processed Greenhouse outputs before writing new normalized files

### 3. CLI shortlist usability
- confirmed `--eligible-only` behavior
- confirmed `--applyable-only` behavior
- verified combined shortlist-style filtering for public board outputs

### 4. Real-board validation
- re-fetched Cloudflare postings
- re-ran ranking after normalization updates
- verified that shortlist outputs are narrower and easier to inspect than before

---

## Validation

### Tests
- `pytest tests/test_baseline_scorer_seniority.py -q` passed
- `pytest tests/test_greenhouse_client.py -q` passed
- full test suite passed
- current total: `68 passed`

### Output checks
- Waymo shortlist remains very focused
- Cloudflare shortlist now shows more meaningful geographic location values such as:
  - Austin, US
  - London, UK
  - Singapore
- Cloudflare applyable-only output is smaller and more interpretable than previous runs

---

## Current project state

InternLens now supports:
- Lever ingestion
- Greenhouse ingestion
- raw snapshot saving
- processed job normalization
- registry-driven batch fetch
- blocker-aware ranking
- shortlist-oriented CLI output filters
- API endpoints for recommendation and job detail lookup
- stable regression-tested iteration

---

## Remaining follow-up

### Ranking
- reduce remaining non-core internship noise
- further tighten relevance criteria for `Apply Later`

### Normalization
- continue refining hybrid/in-office location handling
- improve company and team normalization
- improve deduplication for repeated internship postings

### Product / docs
- update docs to reflect week 2 progress
- prepare cleaner final demo examples
- continue improving shortlist readability

---

## Outcome

Today’s work moved the project from “works technically” toward “looks cleaner in a demo.”

The ranking is still heuristic, but the system now behaves much more like a practical internship discovery pipeline instead of a toy scorer over sample jobs.
