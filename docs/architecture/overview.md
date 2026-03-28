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
      - applied / saved / skipped signals
      - similarity-based score adjustment
      - explanation generation
                |
                v
        Final Ranked Job Results
          /         |          \
         /          |           \
        v           v            v
 Console Output   JSON/CSV   FastAPI /recommend
```

## Main modules

* `src/preprocessing/profile_parser.py`

  * loads and normalizes candidate profile data
  * builds a reusable `skill_set`
  * keeps file-based and inline profile normalization consistent

* `src/preprocessing/job_parser.py`

  * loads and normalizes job posting files
  * prepares combined text fields for ranking and future retrieval

* `src/ranking/baseline_scorer.py`

  * computes baseline fit score
  * separates fit score from blocking constraints
  * applies blocker-aware ordering
  * returns explanations, skill gaps, and component scores

* `src/ranking/feedback_reranker.py`

  * loads feedback events from JSON
  * builds a lookup over known jobs referenced in feedback
  * computes lightweight similarity-based score adjustments
  * generates compact explanation snippets for reranked jobs
  * preserves recommendation bucket ordering during reranking

* `scripts/run_baseline.py`

  * runs the ranking pipeline locally
  * can run baseline-only or feedback-aware reranking
  * prints results and exports JSON/CSV outputs
  * surfaces feedback explanation details when reranking is enabled

* `src/api/app.py`

  * exposes `/health` and `/recommend`
  * supports file-based and inline profile inputs
  * supports optional feedback-based reranking through `feedback_path`
  * returns explanation-aware reranking fields in API responses

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

This design also makes it possible to keep ordering intuitive:

1. **Apply Now**
2. **Apply Later**
3. **Skip**

Even when feedback reranking is applied, recommendation buckets stay stable and reranking only adjusts order within the policy-aware structure.

## Feedback reranking design (v1)

The current reranker uses a lightweight feedback file with events such as:

- `applied`
- `saved`
- `skipped`

It then:

1. maps feedback events to known job postings
2. extracts meaningful title tokens and a conservative skill phrase set
3. computes similarity between the current job and previously labeled jobs
4. applies small positive or negative adjustments based on feedback labels
5. generates explanation items for the strongest feedback contributors
6. preserves blocker-aware recommendation ordering in the final output

This keeps the reranker simple, explainable, and safe for an early portfolio-oriented implementation.

## Explanation output design

Each reranked result can now include a `feedback_explanations` field.

Each explanation item contains:

- source feedback job ID
- source feedback job title
- feedback label used for reranking
- computed similarity
- numeric adjustment contribution
- overlapping title tokens
- overlapping skill tokens

This makes the personalization layer easier to inspect during demos and easier to debug during iteration.

## API and output behavior

`/recommend` can return either baseline-only or feedback-aware results.

When feedback reranking is used, the response also includes:

- `feedback_source`
- `reranking_applied`
- `feedback_adjustment`
- `reranked_score`
- `feedback_explanations`

The local script flow mirrors this behavior by surfacing explanation details in console output and exported JSON/CSV artifacts.

## Current test coverage snapshot

The current test suite covers:

- baseline API health and recommendation flows
- inline and file-based profile inputs
- validation and file-not-found cases
- blocker-aware ranking behavior
- feedback file loading and lookup behavior
- feedback-aware reranking fields and API responses
- explanation field presence in reranking and API results

Current status: **17 passing tests**

## Next evolution path

1. add inline feedback payload support
2. improve explanation quality and score calibration
3. add semantic retrieval
4. replace heuristic ranking with learning-to-rank
5. add persistence and deployment
