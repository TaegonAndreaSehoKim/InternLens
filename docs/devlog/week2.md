# Week 2 Devlog

## Day 8 — Precision/Location Cleanup and Output Usability

### Focus
Improve public-board ranking usability and reduce noisy shortlist behavior, especially on Greenhouse sources.

### What was done
- Tightened baseline internship ranking logic.
- Added and refined blocker-aware shortlist behavior.
- Added CLI output filters:
  - `--eligible-only`
  - `--applyable-only`
- Improved Greenhouse normalization so geographic location could come from metadata instead of only generic work-mode labels such as `Hybrid` or `In-Office`.
- Prevented stale Greenhouse processed files from mixing old and new normalized outputs across reruns.
- Re-fetched and re-evaluated Cloudflare data after normalization updates.

### Result
- The shortlist output became much easier to inspect.
- Location quality improved from generic labels toward real geographic values like `Austin, US`, `London, UK`, and `Singapore`.
- Cloudflare shortlist quality improved noticeably, though some non-core internships still remained.
- Full test suite was stable at **68 passed** at the end of this stage.

### Key takeaway
Week 2 started with a shift from “make it run” to “make the output usable.” The system became much more demo-friendly after shortlist filtering and location cleanup.

---

## Day 9 — Recovery / No Development Day

### Status
- No feature development.
- No code changes.
- No ranking or ingestion updates.

### Notes
This was an intentional pause day to recover and keep pacing sustainable.

### Outcome
Project state was preserved as-is from the previous day, with the latest stable checkpoint ready for continuation.

---

## Day 10 — Cloudflare Shortlist Precision Improvement

### Focus
Reduce noisy fallback skill matches so non-technical internship titles stop surviving the shortlist too easily.

### Main problem at the start of the day
Cloudflare shortlist still contained several broad non-core internships that were inheriting noisy fallback matches from title/description heuristics.
Examples included roles in people/HR/marketing/product areas that were still being promoted because of broad AI, Python, or analytics wording.

### What was changed
- Refined fallback skill logic in `baseline_scorer.py`.
- Strengthened title-based gating so fallback title/description skill matching is used more conservatively.
- Added stronger separation between:
  - technical/data/research/engineering internship titles
  - non-technical internship titles
- Preserved strong behavior for technical roles such as:
  - Data Analytics Intern
  - Data Engineer Intern
  - Business Analyst Intern
  - Research / Security / Network-oriented internships
- Added regression tests for these new ranking rules.

### Validation
- `pytest tests/test_baseline_scorer_seniority.py -q` → **14 passed**
- `pytest -q` → **71 passed**

### Result
Cloudflare shortlist under `--applyable-only` became much tighter.
The visible shortlist reduced to a compact set centered on more relevant roles:
- Data Analytics Intern (Summer 2026)
- Business Analyst Intern, Revenue Operations (AI Innovation) (Summer 2026)
- DCSC Automation Coordinator Intern
- Network Deployment Engineer Intern (Summer 2026)
- Data Engineer Intern (Summer 2026)

### Why this matters
This was one of the biggest quality jumps so far.
The system moved closer to a real shortlist generator instead of a broad “internship dump.”

---

## Week 2 Snapshot (through Day 10)

### Current project state
InternLens currently supports:
- multi-source public ATS ingestion
  - Lever
  - Greenhouse
- raw snapshot saving
- processed schema normalization
- registry-driven batch fetching
- baseline ranking with blockers
- shortlist-oriented CLI filters
- API endpoints:
  - `/recommend`
  - `/jobs/{id}`

### Quality checkpoint
- Latest full test status: **71 passed**
- Cloudflare shortlist precision improved significantly
- Waymo shortlist remains highly focused under shortlist filters

### Remaining follow-up ideas
- Continue reducing remaining fallback-skill noise for edge-case internship titles.
- Refactor `baseline_scorer.py` so policy logic is split more cleanly.
- Polish docs and final demo flow.
