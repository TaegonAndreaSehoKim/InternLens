# InternLens Architecture Overview

## High-level flow

```text
Candidate Profile (JSON or API payload)
                |
                v
        Profile Normalization
                |
                v
     Normalized Candidate Profile

Job Postings (JSON directory)
                |
                v
         Job Parsing / Cleanup
                |
                v
        Normalized Job Records

Normalized Profile + Jobs
                |
                v
        Baseline Ranking Engine
        - fit scoring
        - blocker checks
        - blocker-aware ordering
                |
                v
         Optional Feedback Reranker
                |
                v
     Ranked or Reranked Job Results
          /         |         \
         /          |          \
        v           v           v
 Console Output   JSON/CSV    FastAPI /recommend
```

## Main modules

* `src/preprocessing/profile_parser.py`

  * loads and normalizes candidate profile data
  * builds a reusable `skill_set`

* `src/preprocessing/job_parser.py`

  * loads and normalizes job posting files
  * prepares combined text fields for ranking and future retrieval

* `src/ranking/baseline_scorer.py`

  * computes baseline fit score
  * separates fit score from blocking constraints
  * applies blocker-aware ordering
  * returns explanations, skill gaps, and component scores

* `src/ranking/feedback_reranker.py`

  * loads feedback event data
  * computes lightweight similarity against previously labeled jobs
  * applies feedback adjustments to reranked results
  * preserves blocker-aware action ordering during reranking

* `scripts/run_baseline.py`

  * runs baseline ranking locally
  * optionally runs feedback-based reranking
  * prints results and exports JSON/CSV outputs

* `src/api/app.py`

  * exposes `/health` and `/recommend`
  * supports both file-based and inline profile payload inputs

## Current ranking logic

The baseline fit score is computed from:

* skill match
* role match
* location match

The role-matching step reduces false positives by filtering overly generic title tokens, and skill matching includes lightweight alias normalization.

## Current blocker logic

Blocking issues are evaluated separately from the numeric fit score so that a role can still be recognized as a strong fit even when the candidate cannot realistically apply.

At the current stage, the blocker layer includes:

- sponsorship mismatch
- expanded eligibility-style checks from job requirements

Examples currently covered include:

- non-internship job type
- explicit PhD requirement mismatch
- lightweight graduation timing mismatch checks

## Why fit score and blockers are separated

This separation is a deliberate design choice.

A job can be a strong relevance match based on skills, role, and location, while still being a poor application target because of a hard constraint. Keeping blockers outside the numeric fit score makes the ranking behavior easier to explain and easier to extend.

## Why blocker-aware ordering was added

Raw fit score alone is not enough for an application strategy tool.

InternLens now prioritizes recommendation buckets in this order:

1. **Apply Now**
2. **Apply Later**
3. **Skip**

This keeps blocked or clearly low-priority jobs from rising above stronger actionable targets, even when they share many fit signals.

## Feedback-based reranking v1

The current reranking layer is intentionally lightweight.

It uses simple feedback events such as `applied`, `saved`, and `skipped` to adjust ranking behavior based on prior user preferences.

Current v1 design choices:

- feedback is loaded from a small JSON profile
- similarity is based on conservative title and skill overlap
- generic title words are filtered to reduce noisy matches
- reranking adjusts score but still respects blocker-aware action ordering

This allows the project to demonstrate a first personalization step without introducing heavy model complexity.

## Next evolution path

1. improve feedback signal quality and reranking calibration
2. add API-level support for optional feedback input
3. improve explanation transparency for reranked results
4. add semantic retrieval
5. replace heuristic ranking with learning-to-rank
6. add persistence and deployment
