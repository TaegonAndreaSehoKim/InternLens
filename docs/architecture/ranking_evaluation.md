# Ranking evaluation

`scripts/evaluate_ranking.py` evaluates the versioned fixture in `tests/fixtures/ranking_benchmark.json`. Candidate profiles, posting dates, evaluation time, relevance grades, and explicit eligibility labels are fixed in the fixture. The fixture contains 15 synthetic postings and 60 candidate/job judgments across software engineering, data/ML, marketing, and finance.

These are hand-authored regression examples, not independently human-reviewed real ATS labels. Passing the fixture demonstrates those scenarios remain intact; it does not establish production precision or generalization. Keep this distinction when reporting scores. Extend it with reviewed ATS examples and additional candidate constraints before treating it as a quality estimate.

The evaluator uses the same baseline scorer and output filters as CLI/API shortlists, with `eligible_only=True`, `applyable_only=True`, and `top_k=2`. A grade of 2 or 3 counts as relevant. Grades are 0 (unsuitable), 1 (adjacent), 2 (relevant), and 3 (strongly relevant). Eligibility labels cover explicit constraints supported by the current scorer, including required PhD conditions, sponsorship restrictions, and non-internship/senior positions.

| Metric | Definition |
| --- | --- |
| Precision@k | Relevant returned jobs divided by k; missing results contribute zero. |
| nDCG@k | Discounted graded relevance with gain `2^grade - 1`, divided by ideal relevance over expected-eligible jobs. |
| Eligibility accuracy | Correct blocked/unblocked decisions across all labeled jobs, including jobs filtered out of the shortlist. |
| Blocked shortlist rate | Returned jobs labeled ineligible divided by the number returned. |
| Non-internship shortlist rate | Returned jobs labeled non-internships divided by the number returned. |

An empty shortlist has zero precision and nDCG; its leakage rates are zero. Every candidate/job pair must be labeled, and the ranker must return each input job exactly once. Invalid fixtures fail validation instead of silently reducing the denominator.

Thresholds live in the fixture and are checked for every profile independently. Macro averages are also reported, but cannot mask a failing profile. `--check` exits nonzero on any failure and runs in the backend GitHub Actions job. The latest local fixture run had Precision@2, nDCG@2, and eligibility accuracy of 1.0, with both leakage rates at 0.0.

`scripts/generate_ranking_quality_report.py` remains useful for inspecting a live corpus across representative profiles. That unlabeled report is a sanity check and does not supply the metric labels used here.
