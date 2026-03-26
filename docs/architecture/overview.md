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
      - skill match
      - role match
      - location match
      - blocking constraints
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

The baseline score is computed from:

* skill match
* role match
* location match

Blocking issues are handled separately from the numeric score so that a role can still be recognized as a strong fit even when the candidate cannot realistically apply.

## Current blocker logic

The current implementation checks blocker conditions separately from the fit score. At this stage, the blocker logic includes:

- sponsorship mismatch
- non-internship job type
- explicit PhD requirement mismatch
- lightweight graduation timing mismatch checks

## Next evolution path

1. strengthen blocker logic
2. improve result explanations
3. add semantic retrieval
4. replace heuristic ranking with learning-to-rank
5. add persistence and deployment
