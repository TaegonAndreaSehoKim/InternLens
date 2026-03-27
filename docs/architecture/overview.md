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
                |
                v
           Ranked Job Results
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
  * returns explanations, skill gaps, and component scores

* `scripts/run_baseline.py`

  * runs the ranking pipeline locally
  * prints results and exports JSON/CSV outputs

* `src/api/app.py`

  * exposes `/health` and `/recommend`
  * supports both file-based and inline profile payload inputs

## Current ranking logic

The baseline fit score is computed from:

* skill match
* role match
* location match

The role-matching step also reduces false positives by filtering overly generic title tokens, and skill matching includes lightweight alias normalization.

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

## Next evolution path

1. improve result explanations and demo clarity
2. add feedback-based reranking
3. add semantic retrieval
4. replace heuristic ranking with learning-to-rank
5. add persistence and deployment
