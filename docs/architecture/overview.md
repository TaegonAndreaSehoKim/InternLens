# InternLens Overview

## Project summary

InternLens is a practical internship search pipeline that connects three core pieces of work:

1. public job board ingestion
2. candidate-profile-based ranking
3. shortlist-oriented inspection through CLI and API

The project began as a simple internship recommender over sample jobs, but it now supports real public ATS sources and a more realistic evaluation loop. At the current stage, the system can fetch public internships from Lever and Greenhouse boards, normalize them into a shared processed schema, rank them against a target candidate profile, and export shortlist-style results. The current validation state is `71 passed`.

---

## Goals

The main goals of InternLens are:
- build a lightweight, understandable internship recommender
- move beyond static toy data into real public job board ingestion
- support iterative ranking improvements without breaking earlier behavior
- expose results both as a scriptable CLI flow and as an API
- maintain fast iteration through small, regression-tested changes

This is not meant to be a production hiring platform yet. It is a clean, extensible foundation for future internship discovery and ranking work.

---

## Architecture

### 1. Ingestion layer
InternLens currently supports:

#### Lever ingestion
- single-board fetch
- raw snapshot storage
- processed normalization
- registry-driven batch fetch

#### Greenhouse ingestion
- single-board fetch
- raw snapshot storage
- processed normalization
- registry-driven batch fetch
- metadata-aware geographic location extraction for boards that use work-mode labels such as `Hybrid` or `In-Office`

The ingestion layer saves:
- raw board snapshots for reproducibility
- processed per-job JSON files for ranking

This keeps collection and ranking decoupled, which makes debugging and iteration easier.

---

### 2. Preprocessing layer
The preprocessing layer loads:
- candidate profiles
- processed job directories

Candidate preferences such as role targets, graduation timing, sponsorship need, and extracted skills are turned into a baseline-friendly representation.

The job parser supports recursively loading processed jobs from source-specific directories.

---

### 3. Ranking layer
The ranking layer is currently heuristic and transparent.

It uses:
- skill overlap
- preferred role overlap
- location match
- internship bonus
- blocker logic

Important ranking improvements added so far:
- senior-role blocker
- non-internship blocker
- PhD blocker
- internship-aware ordering
- blocker-aware shortlist filters
- fallback skill extraction for sparse public postings
- reduced noisy fallback skill matching for non-technical internship titles
- tighter shortlist precision for noisy public boards

This makes the current baseline much more useful than a simple keyword scorer.

---

### 4. Output layer
InternLens supports:
- CLI-based ranking inspection
- JSON export
- CSV export
- API recommendation endpoint
- job detail endpoint

Recent CLI improvements:
- `--eligible-only`
- `--applyable-only`

These filters make it easier to inspect meaningful subsets rather than dumping the full ranked list.

---

## Current development status

### What is working well
- multi-source public job ingestion is working
- registry-based batch fetching is working
- processed schema generation is working
- ranking is stable enough for demo use
- tests are strong enough to support iterative changes safely
- the CLI now supports shortlist-style filtering
- API behavior remains stable after ranking refinements

### What improved most recently
Recent work focused on:
- reducing ranking noise for public internship boards
- improving Greenhouse location normalization using metadata
- reducing noisy fallback skill matches for non-technical internships
- making shortlist display easier to inspect
- tightening Cloudflare shortlist precision so non-core internship roles drop out more often

The latest validation state shows:
- `71 passed`
- Cloudflare re-fetched with improved location extraction
- Cloudflare applyable-only shortlist reduced to a much smaller, more relevant subset
- Waymo shortlist remains very small and focused under applyable-only filtering

---

## Example current behavior

### Waymo
The Waymo shortlist is now very narrow. Under applyable-only filtering, it effectively surfaces a single clearly relevant internship target rather than a noisy wall of blocked roles. That is a strong sign that blocker logic and internship prioritization are working.

### Cloudflare
Cloudflare remains noisier than Waymo, but it is much more usable than before.

Recent visible shortlist examples include:
- Data Analytics Intern
- Business Analyst Intern, Revenue Operations (AI Innovation)
- DCSC Automation Coordinator Intern
- Network Deployment Engineer Intern
- Data Engineer Intern

These now appear with real geographic locations such as:
- Austin, US
- London, UK
- Singapore

instead of generic work-mode-only labels dominating the output.

---

## Why the project matters

InternLens now demonstrates a real iterative ML/IR-style workflow:
- collect external data
- normalize it
- design scoring logic
- validate output behavior
- add regression tests
- refine precision over time

That makes it useful as:
- a portfolio project
- a search / ranking prototype
- an internship recommender demo
- a foundation for future retrieval and reranking work

It also shows good engineering discipline:
- reproducible raw snapshots
- source-specific normalization
- CLI utilities for debugging
- API exposure
- test-backed iteration

---

## Main limitations

### Ranking limitations
- the baseline is still heuristic
- fallback skill extraction can still overgeneralize in some postings
- some broad AI-adjacent or operations internships may still remain in the shortlist
- there is no learned relevance model yet

### Data limitations
- public ATS data is inconsistent
- work-mode and location fields vary by board
- some postings duplicate across locations
- structured qualification fields are often sparse

### Product limitations
- shortlist filtering is useful, but still CLI-first
- there is no polished front-end yet
- deduplication and grouping are still basic
- company normalization remains lightweight

---

## Recommended next steps

The strongest next steps are:

1. refine shortlist precision further
   - reduce remaining non-core internship noise
   - tighten relevance requirements for `Apply Later`

2. improve normalization quality
   - better company normalization
   - better hybrid/in-office handling
   - better deduplication across repeated multi-location postings

3. strengthen retrieval/ranking sophistication
   - embeddings or vector retrieval
   - learned reranking
   - feedback-aware personalization

4. improve presentation
   - cleaner API responses
   - shortlist summaries
   - possibly a thin front-end demo

---

## Bottom line

InternLens is now a small but credible internship discovery system.

It is no longer just a script that scores static sample jobs. It now supports:
- real public ATS ingestion
- processed data generation
- blocker-aware internship ranking
- shortlist filtering
- API access
- regression-tested iteration

That makes the project demoable today and extensible tomorrow.
