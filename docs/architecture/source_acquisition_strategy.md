# Source Acquisition Strategy

## Goal

InternLens should evolve from:

- manually maintained ATS registry entries

to:

- company-centered source discovery
- validated source management
- scheduled corpus refresh
- user-facing recommendation over a curated internal job corpus

The objective is not to crawl every internship posting on the internet.
The objective is to maintain a high-quality, refreshable internship corpus that is:

- recent
- relevant
- deduplicated
- explainable
- cheap to maintain

---

## Design principle

The most effective long-term strategy is:

1. manage companies, not only ATS tokens
2. discover likely high-value job sources
3. validate sources before promoting them into production refresh
4. prioritize source quality over raw source count

This is a better fit for InternLens than a broad search-engine-style crawler.

---

## Recommended source hierarchy

InternLens should collect postings using a layered source strategy.

### Tier 1: direct ATS / company-controlled sources

Examples:
- Lever public boards
- Greenhouse public boards
- other company-hosted ATS pages later

Why this tier matters:
- best freshness
- best canonical URLs
- lowest ambiguity about job ownership

### Tier 2: structured company metadata

Examples:
- `JobPosting` JSON-LD
- sitemap job pages
- machine-readable careers feeds

Why this tier matters:
- cheaper than brittle HTML parsing
- often includes cleaner location, date, and apply URL fields

### Tier 3: discovery/search sources

Examples:
- careers page scanning
- homepage to careers-page link extraction
- search-discovered ATS links

Why this tier matters:
- useful for discovering new sources
- should feed candidate sources, not automatically become production sources

### Tier 4: operator-curated sources

Examples:
- manually approved target companies
- user-requested companies
- domain-specific internship-heavy companies

Why this tier matters:
- highest precision
- excellent for maintaining a practical recommendation corpus

---

## Why not “crawl everything”

Trying to gather all Lever and Greenhouse postings globally is not the right system goal.

Problems:
- there is no clean global board index
- source discovery cost becomes high very quickly
- quality drops faster than coverage rises
- duplicate and irrelevant jobs overwhelm the ranking stage
- internship recommendation needs quality more than breadth

InternLens should target:

- high-quality company sources
- internship-heavy companies
- companies aligned with target roles
- a corpus that stays useful for real recommendation

---

## Company-centered operating model

The long-term system should treat a company as the main entity.

Each company can have:
- homepage URL
- careers URL
- known ATS sources
- source quality score
- refresh history
- validation history
- source status

That means the system’s primary question becomes:

- “Which company sources should we trust and refresh?”

not:

- “Which ATS tokens happen to be known right now?”

---

## Data model proposal

### 1. Company seed record

This is the starting input for discovery.

Suggested fields:

| Field | Type | Description |
|---|---|---|
| company | string | Company display name |
| homepage_url | string | Company homepage |
| careers_url | string | Known careers page if available |
| priority | integer | Relative importance for refresh/discovery |
| industries | list[string] | Optional company tags |
| target_roles | list[string] | Role families relevant to InternLens |
| preferred_regions | list[string] | Optional regional hints |
| notes | string | Operator notes |

### 2. Discovered source record

This is a candidate source found during discovery.

Suggested fields:

| Field | Type | Description |
|---|---|---|
| company | string | Company name |
| source_type | string | `lever`, `greenhouse`, `jsonld`, `html`, etc. |
| source_identifier | string | Board token / site name / source-specific ID |
| careers_url | string | Parent careers page |
| discovery_url | string | The exact URL where the source was found |
| discovered_at | string | Discovery timestamp |
| discovery_method | string | `careers_page_scan`, `manual`, `search`, etc. |
| status | string | `candidate`, `validated`, `active`, `inactive`, `rejected` |
| validation_notes | string | Validation result summary |
| source_score | number | Overall source quality score |
| internship_likelihood | number | Estimated internship relevance |

### 3. Active refresh target

This is the production-ready registry entry used by fetch scripts.

Suggested fields:

| Field | Type | Description |
|---|---|---|
| source_type | string | `lever` or `greenhouse` |
| source_identifier | string | Board token or site name |
| company | string | Company name |
| active | boolean | Whether refresh should include it |
| internship_only | boolean | Whether to keep internship filtering on |
| last_validated_at | string | Latest successful validation timestamp |
| last_refreshed_at | string | Latest successful refresh timestamp |
| source_score | number | Source quality score |
| notes | string | Operational notes |

---

## File layout proposal

Suggested additions under `data/source_registry/`:

```text
data/
  source_registry/
    company_seeds.json
    discovered_sources.json
    lever_targets.json
    greenhouse_targets.json
```

Roles:

- `company_seeds.json`
  - seed list for discovery
- `discovered_sources.json`
  - candidate sources discovered and scored
- `lever_targets.json`
  - active production refresh targets for Lever
- `greenhouse_targets.json`
  - active production refresh targets for Greenhouse

---

## Source scoring

InternLens should not treat every discovered source equally.

Use a simple score to rank refresh value.

### Suggested score dimensions

| Dimension | Meaning |
|---|---|
| internship density | how often the source contains internships |
| technical role density | frequency of software/data/ML/security/network roles |
| data quality | structured fields, reliable location, stable URLs |
| freshness | how recently the source produced current jobs |
| uniqueness | whether it adds new jobs rather than duplicates |
| refresh reliability | whether fetches succeed consistently |

### Example heuristic formula

```text
source_score =
  (internship_density * 0.30) +
  (technical_role_density * 0.25) +
  (data_quality * 0.20) +
  (freshness * 0.15) +
  (refresh_reliability * 0.10)
```

This does not need to be statistically perfect.
It needs to help InternLens refresh the most useful sources first.

---

## Discovery strategy

Discovery should be incremental and conservative.

### Phase 1: known company discovery

Input:
- `company_seeds.json`

Process:
- read homepage and careers URLs
- extract ATS links
- classify likely source type
- store candidate source records

Primary targets:
- `jobs.lever.co/<site_name>`
- `boards.greenhouse.io/<board_token>`
- `job-boards.greenhouse.io/<board_token>`

### Phase 2: source validation

For each discovered candidate:
- attempt a real fetch
- check whether payload is non-empty
- check whether job pages normalize correctly
- estimate internship density

If validation passes:
- mark as `validated`

### Phase 3: promotion

Only promoted sources should enter:
- `lever_targets.json`
- `greenhouse_targets.json`

Promotion conditions can be:
- successful fetch
- at least one meaningful internship-like posting
- acceptable data quality
- no obvious duplication with an existing active source

---

## Refresh strategy

Refresh should be source-aware rather than blindly global.

### Default policy

- refresh active sources on a schedule
- refresh higher-scoring sources first
- preserve raw snapshots
- update processed jobs only after normalization succeeds

### Suggested cadence

- daily refresh for active sources
- more frequent refresh for high-score companies later if needed

### Refresh modes

1. full refresh
   - all active sources

2. priority refresh
   - only top-scoring sources

3. targeted refresh
   - one company or one ATS source

---

## Deduplication policy

Deduplication must happen at more than one layer.

### Layer 1: source-level dedupe

- do not store the same ATS source twice
- key by `(source_type, source_identifier)`

### Layer 2: job-level dedupe

- dedupe by `job_id`
- dedupe conservative near-duplicates by:
  - canonical URL
  - company
  - location
  - title similarity

### Layer 3: corpus-level dedupe

- a company may expose similar jobs across multiple pages or locations
- keep variants only when they are materially distinct

---

## Recommended phased implementation

### Milestone 1: discovery MVP

Deliver:
- `company_seeds.json`
- `discovered_sources.json`
- `scripts/discover_sources.py`
- ATS URL extraction from known careers pages

Goal:
- produce candidate Lever/Greenhouse sources automatically

### Milestone 2: validation and promotion

Deliver:
- validation logic
- source scoring
- promotion path into active registries

Goal:
- reduce manual registry maintenance

### Milestone 3: source-aware refresh policy

Deliver:
- source score aware refresh
- refresh reporting
- stale source handling

Goal:
- spend refresh budget on high-value sources

### Milestone 4: user-facing corpus-backed recommendation

Deliver:
- `/recommend` no longer depends on caller-provided `jobs_dir`
- recommendation uses internal refreshed corpus by default

Goal:
- move from test/developer API to user-facing product flow

---

## Immediate next step

The next practical implementation should be:

1. add `company_seeds.json`
2. add `discovered_sources.json`
3. implement `scripts/discover_sources.py`
4. extract Lever/Greenhouse URLs from seed company careers pages
5. save discovered candidates without auto-promoting them

This gives InternLens a controlled transition from:

- manually entered ATS tokens

to:

- semi-automated source discovery and management

without destabilizing the current refresh and ranking system.
