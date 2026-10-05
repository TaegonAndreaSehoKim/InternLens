from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Callable

from src.preprocessing.job_parser import REQUIRED_JOB_FIELDS
from src.preprocessing.profile_parser import normalize_candidate_profile
from src.ranking.baseline_scorer import rank_jobs
from src.ranking.output_filters import filter_results_for_output

HIGHER_IS_BETTER = {"precision_at_k", "ndcg_at_k", "eligibility_accuracy"}
LOWER_IS_BETTER = {"blocked_shortlist_rate", "non_internship_shortlist_rate"}


def _dcg(grades: list[int]) -> float:
    return sum((2 ** grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades))


def evaluate_benchmark(benchmark: dict[str, Any], *, ranker: Callable = rank_jobs) -> dict[str, Any]:
    """Compare actual shortlists against independently specified fixture labels."""
    top_k = benchmark["top_k"]
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    evaluated_at = datetime.fromisoformat(benchmark["evaluated_at"])
    if evaluated_at.tzinfo is None:
        raise ValueError("evaluated_at must include a timezone")
    jobs = [benchmark.get("job_defaults", {}) | job for job in benchmark["jobs"]]
    jobs_by_id = {job["job_id"]: job for job in jobs}
    if not jobs or len(jobs_by_id) != len(jobs):
        raise ValueError("Benchmark jobs must be nonempty and have unique IDs")
    if any(not set(REQUIRED_JOB_FIELDS).issubset(job) or type(job.get("is_internship")) is not bool for job in jobs):
        raise ValueError("Benchmark jobs require complete job fields and an explicit internship label")
    thresholds = benchmark["thresholds"]
    if set(thresholds) != HIGHER_IS_BETTER | LOWER_IS_BETTER or any(not 0 <= value <= 1 for value in thresholds.values()):
        raise ValueError("Provide all five metric thresholds between 0 and 1")
    profiles = benchmark["profiles"]
    if not profiles or len({profile["profile_name"] for profile in profiles}) != len(profiles):
        raise ValueError("Benchmark profiles must be nonempty and unique")

    reports, failures = [], []
    for case in profiles:
        name = case["profile_name"]
        labels = case["relevance"]
        ineligible = set(case["ineligible_job_ids"])
        if set(labels) != set(jobs_by_id) or not ineligible.issubset(jobs_by_id):
            raise ValueError(f"Incomplete or unknown labels for {name}")
        if any(type(grade) is not int or not 0 <= grade <= 3 for grade in labels.values()):
            raise ValueError("Relevance grades must be integers from 0 to 3")
        profile = normalize_candidate_profile(benchmark["candidate_profiles"][name])
        ranked = ranker(profile, jobs, now=evaluated_at)
        if len(ranked) != len(jobs) or {job["job_id"] for job in ranked} != set(jobs_by_id):
            raise ValueError("Ranker must return every benchmark job exactly once")
        shortlist = filter_results_for_output(ranked, eligible_only=True, applyable_only=True)[:top_k]
        ids = [job["job_id"] for job in shortlist]
        grades = [labels[job_id] for job_id in ids]
        ideal = sorted((grade for job_id, grade in labels.items() if job_id not in ineligible), reverse=True)[:top_k]
        ideal_dcg = _dcg(ideal)
        metrics = {
            "precision_at_k": sum(grade >= 2 for grade in grades) / top_k,
            "ndcg_at_k": _dcg(grades) / ideal_dcg if ideal_dcg else 0.0,
            "eligibility_accuracy": sum(bool(job.get("blocking_issues")) == (job["job_id"] in ineligible) for job in ranked) / len(ranked),
            "blocked_shortlist_rate": sum(job_id in ineligible for job_id in ids) / max(len(ids), 1),
            "non_internship_shortlist_rate": sum(not jobs_by_id[job_id]["is_internship"] for job_id in ids) / max(len(ids), 1),
        }
        for metric, value in metrics.items():
            threshold = thresholds[metric]
            if (value < threshold if metric in HIGHER_IS_BETTER else value > threshold):
                failures.append({"profile_name": name, "metric": metric, "actual": value, "threshold": threshold})
        eligibility_errors = [job["job_id"] for job in ranked if bool(job.get("blocking_issues")) != (job["job_id"] in ineligible)]
        reports.append({"profile_name": name, "metrics": metrics, "shortlist_job_ids": ids, "eligibility_errors": eligibility_errors})

    return {
        "benchmark": benchmark["name"], "description": benchmark["description"],
        "evaluated_at": evaluated_at.isoformat(), "top_k": top_k,
        "job_count": len(jobs), "judgment_count": len(jobs) * len(reports),
        "macro_metrics": {metric: sum(report["metrics"][metric] for report in reports) / len(reports) for metric in thresholds},
        "profiles": reports, "thresholds": thresholds, "failures": failures, "passed": not failures,
    }
