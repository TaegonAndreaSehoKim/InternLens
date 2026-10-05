from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from src.ranking.baseline_scorer import rank_jobs
from src.ranking.evaluation import evaluate_benchmark

FIXTURE = Path(__file__).parent / "fixtures/ranking_benchmark.json"


@pytest.fixture
def benchmark():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_curated_labels_pass_for_each_profile_at_a_fixed_time(benchmark):
    report = evaluate_benchmark(benchmark)
    assert report["passed"]
    assert report["judgment_count"] == 60
    assert report["macro_metrics"]["precision_at_k"] == 1.0
    assert all(not profile["eligibility_errors"] for profile in report["profiles"])
    assert evaluate_benchmark(deepcopy(benchmark)) == report


def test_metrics_detect_bad_relevance_eligibility_and_non_internship_leakage(benchmark):
    def broken_ranker(profile, jobs, *, now):
        ranked = rank_jobs(profile, jobs, now=now)
        wrong = [job for job in ranked if job["job_id"] in {"phd_required", "international"}]
        for job in wrong:
            job.update(blocking_issues=[], action_label="Apply Now")
        return wrong + [job for job in ranked if job not in wrong]

    report = evaluate_benchmark(benchmark, ranker=broken_ranker)
    metrics = report["profiles"][0]["metrics"]
    assert not report["passed"]
    assert metrics["precision_at_k"] == 0
    assert metrics["ndcg_at_k"] == 0
    assert metrics["blocked_shortlist_rate"] == 1
    assert metrics["non_internship_shortlist_rate"] == 0.5
    assert metrics["eligibility_accuracy"] == pytest.approx(13 / 15)


def test_empty_shortlist_cannot_pass_quality_gate(benchmark):
    def empty_shortlist(profile, jobs, *, now):
        return [job | {"action_label": "Skip"} for job in rank_jobs(profile, jobs, now=now)]

    report = evaluate_benchmark(benchmark, ranker=empty_shortlist)
    assert not report["passed"]
    assert report["macro_metrics"]["precision_at_k"] == 0
    assert all(not profile["shortlist_job_ids"] for profile in report["profiles"])


@pytest.mark.parametrize("change", ["missing_label", "unknown_blocker", "duplicate_job", "missing_field", "missing_threshold", "naive_time"])
def test_incomplete_benchmarks_fail_instead_of_improving_metrics(benchmark, change):
    if change == "missing_label":
        benchmark["profiles"][0]["relevance"].pop("software")
    elif change == "unknown_blocker":
        benchmark["profiles"][0]["ineligible_job_ids"].append("unknown")
    elif change == "duplicate_job":
        benchmark["jobs"].append(benchmark["jobs"][0])
    elif change == "missing_field":
        benchmark["jobs"][0].pop("description")
    elif change == "missing_threshold":
        benchmark["thresholds"].pop("precision_at_k")
    else:
        benchmark["evaluated_at"] = "2026-10-05"
    with pytest.raises(ValueError):
        evaluate_benchmark(benchmark)


def test_cli_check_writes_report_and_exits_nonzero_on_regression(benchmark, tmp_path):
    benchmark["profiles"][0]["relevance"] = {job_id: 0 for job_id in benchmark["profiles"][0]["relevance"]}
    fixture = tmp_path / "labels.json"
    output = tmp_path / "report.json"
    fixture.write_text(json.dumps(benchmark), encoding="utf-8")
    result = subprocess.run([sys.executable, "scripts/evaluate_ranking.py", "--benchmark", str(fixture), "--output-file", str(output), "--check"], capture_output=True, text=True)
    assert result.returncode == 1
    assert "FAILED cs_engineering/precision_at_k" in result.stdout
    assert not json.loads(output.read_text())["passed"]
