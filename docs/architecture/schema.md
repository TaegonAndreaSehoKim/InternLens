# Schema Design

## Design goals

InternLens now needs to support both:

- manually curated sample postings
- crawled job postings from external public job boards

To keep the ranking pipeline stable, the project should store job data in two layers:

- **raw jobs**: source-specific payloads exactly as fetched
- **processed jobs**: normalized records used by retrieval, ranking, and API responses

This lets us re-run normalization without re-crawling and keeps source-specific parsing logic isolated from the recommendation engine.

---

## Raw Job Record

A raw job record represents one fetched posting before normalization.

### Required fields

| Field | Type | Description |
|---|---|---|
| raw_record_id | string | Unique identifier for the fetched raw record |
| source | string | Source platform such as `lever` or `greenhouse` |
| source_site | string | Source namespace or board token such as a Lever site name or Greenhouse board token |
| source_job_id | string | Platform-native job/posting identifier |
| source_url | string | Public URL used to view the posting |
| fetched_at | string | UTC timestamp for when the record was fetched |
| payload_format | string | Payload type such as `json` |
| raw_payload | object | Original source payload with minimal transformation |

### Optional fields

| Field | Type | Description |
|---|---|---|
| request_url | string | Exact API URL used to fetch the data |
| content_hash | string | Hash used for deduplication or change detection |
| crawl_run_id | string | Identifier for one crawl batch |
| is_active | boolean | Whether the job appeared active during fetch |

---

## Processed Job Record

A processed job record is the normalized form used by the current InternLens ranking and API layers.

### Required fields

| Field | Type | Description |
|---|---|---|
| job_id | string | InternLens job identifier used internally across ranking and API responses |
| source | string | Source platform such as `lever`, `greenhouse`, or `manual` |
| source_site | string | Site/board identifier from the source system |
| source_job_id | string | Original source-specific job/posting ID |
| company | string | Company name |
| title | string | Job title |
| location | string | Normalized location string |
| description | string | Main job description text |
| min_qualifications | string | Extracted or normalized required qualifications text |
| preferred_qualifications | string | Extracted or normalized preferred qualifications text |
| posting_date | string | Posting date in ISO-like string format if available |
| sponsorship_info | string | Sponsorship or work authorization information |
| employment_type | string | Internship, full-time, contract, etc. |
| source_url | string | Public application or detail page URL |
| created_at | string | Timestamp when the processed record was created |
| updated_at | string | Timestamp when the processed record was last refreshed |

### Optional fields

| Field | Type | Description |
|---|---|---|
| team | string | Team, department, or function |
| remote_status | string | `remote`, `hybrid`, `onsite`, or empty |
| application_url | string | Apply URL if different from source_url |
| salary_range | string | Compensation text if available |
| job_status | string | Open/closed if available |
| offices | list[string] | Source office hierarchy if available |
| departments | list[string] | Source department hierarchy if available |
| metadata | object | Preserved source-specific metadata |
| raw_record_id | string | Link back to the raw record that produced this processed job |
| combined_text | string | Concatenated search text for retrieval and ranking |

---

## Candidate Profile

The candidate profile remains the normalized representation used by ranking and recommendation.

| Field | Type | Description |
|---|---|---|
| profile_id | string | Unique profile identifier |
| resume_text | string | Full resume text |
| degree_level | string | Bachelor's, Master's, etc. |
| grad_date | string | Expected graduation date |
| preferred_roles | list[string] | Preferred job roles |
| preferred_locations | list[string] | Preferred job locations |
| sponsorship_need | boolean | Whether the candidate needs sponsorship |
| extracted_skills | list[string] | Skills extracted from resume |
| years_of_experience | integer | Optional experience estimate |
| notes | string | Extra candidate preferences or context |
| skill_set | list[string] | Normalized skill set used internally |

---

## Feedback Events

Feedback events represent candidate reactions that can later be used for reranking and personalization.

| Field | Type | Description |
|---|---|---|
| event_id | string | Unique feedback event identifier |
| profile_id | string | Candidate profile identifier |
| job_id | string | InternLens job identifier |
| feedback_type | string | `saved`, `applied`, `ignored`, `too_ambitious`, or compatible legacy values |
| created_at | string | Event timestamp |

### Notes
- The current reranker still uses a smaller label set in code.
- We may later map `ignored` and `too_ambitious` into different reranking penalties instead of treating everything as a generic skip.

---

## Directory layout for job data

### Raw data
```text
data/
└── raw/
    ├── lever/
    │   └── <site_name>/
    │       └── jobs_<timestamp>.json
    └── greenhouse/
        └── <board_token>/
            └── jobs_<timestamp>.json
```

### Processed data
```text
data/
└── processed/
    └── jobs/
        ├── lever/
        │   └── <site_name>/
        │       └── lever_<site_name>_<source_job_id>.json
        └── greenhouse/
            └── <board_token>/
                └── greenhouse_<board_token>_<source_job_id>.json
```

Older flat processed files may still exist at the root of `data/processed/jobs`.
The job parser recursively loads the tree and suppresses duplicate `job_id` values
and conservative content duplicates by default, preferring nested source/site paths
and richer records when duplicates are found.

---

## Normalization rules

To keep the rest of the pipeline stable:

- all text fields should be normalized to lowercase for internal matching
- source-specific nested fields should be flattened into the processed schema
- missing unsupported fields should default to empty strings or empty lists
- every processed job must include enough data to run:
  - blocker checks
  - ranking
  - retrieval
  - `/jobs/{id}`
  - `/recommend`

---

## Current implementation target

The current ingestion and source-management target is to keep the existing Lever
and Greenhouse refresh flow stable while hardening broader source acquisition:

1. discover candidate ATS sources from curated company seeds
2. validate discovered sources before promotion
3. promote only high-confidence, internship-relevant sources into active registries
4. refresh active Lever and Greenhouse registries into raw and processed data
5. preserve CLI/API/frontend ranking behavior while generated data evolves

Discovered source validation currently records `internship_likelihood` plus
`internship_signal_examples` so operators can inspect which posting titles
caused a source to look internship-relevant before promotion.

Source-quality smoke reports under `outputs/promotion_candidate_smoke*.json`
summarize temporary promotion/fetch/ranking checks. These reports are local
debug artifacts rather than canonical fixtures.
