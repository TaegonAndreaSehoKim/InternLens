from __future__ import annotations

from scripts.run_baseline import _filter_results_for_output, _truncate_results


def test_filter_results_for_output_keeps_all_when_no_filters_are_enabled() -> None:
    # When no output filters are enabled, all ranked jobs should remain visible.
    jobs = [
        {"job_id": "job_1", "blocking_issues": [], "action_label": "Apply Later"},
        {"job_id": "job_2", "blocking_issues": ["This role does not appear to be an internship"], "action_label": "Skip"},
    ]

    visible_jobs = _filter_results_for_output(
        jobs,
        eligible_only=False,
        applyable_only=False,
    )

    assert [job["job_id"] for job in visible_jobs] == ["job_1", "job_2"]


def test_filter_results_for_output_drops_blocked_jobs_when_eligible_only_true() -> None:
    # When eligible_only is on, only blocker-free jobs should remain.
    jobs = [
        {"job_id": "job_1", "blocking_issues": [], "action_label": "Apply Later"},
        {"job_id": "job_2", "blocking_issues": ["This role does not appear to be an internship"], "action_label": "Skip"},
        {"job_id": "job_3", "blocking_issues": [], "action_label": "Skip"},
    ]

    visible_jobs = _filter_results_for_output(
        jobs,
        eligible_only=True,
        applyable_only=False,
    )

    assert [job["job_id"] for job in visible_jobs] == ["job_1", "job_3"]


def test_filter_results_for_output_drops_skip_jobs_when_applyable_only_true() -> None:
    # When applyable_only is on, only Apply Now / Apply Later jobs should remain.
    jobs = [
        {"job_id": "job_1", "blocking_issues": [], "action_label": "Apply Later"},
        {"job_id": "job_2", "blocking_issues": [], "action_label": "Skip"},
        {"job_id": "job_3", "blocking_issues": ["This role appears to require a PhD"], "action_label": "Skip"},
        {"job_id": "job_4", "blocking_issues": [], "action_label": "Apply Now"},
    ]

    visible_jobs = _filter_results_for_output(
        jobs,
        eligible_only=False,
        applyable_only=True,
    )

    assert [job["job_id"] for job in visible_jobs] == ["job_1", "job_4"]


def test_filter_results_for_output_supports_combined_filters() -> None:
    # Combined filters should keep only jobs that are both blocker-free and applyable.
    jobs = [
        {"job_id": "job_1", "blocking_issues": [], "action_label": "Apply Later"},
        {"job_id": "job_2", "blocking_issues": [], "action_label": "Skip"},
        {"job_id": "job_3", "blocking_issues": ["This role appears to require a PhD"], "action_label": "Skip"},
        {"job_id": "job_4", "blocking_issues": [], "action_label": "Apply Now"},
    ]

    visible_jobs = _filter_results_for_output(
        jobs,
        eligible_only=True,
        applyable_only=True,
    )

    assert [job["job_id"] for job in visible_jobs] == ["job_1", "job_4"]


def test_truncate_results_applies_top_k_after_filtering() -> None:
    # top_k should be applied after the visible result set is prepared.
    jobs = [
        {"job_id": "job_1"},
        {"job_id": "job_2"},
        {"job_id": "job_3"},
    ]

    visible_jobs = _truncate_results(jobs, top_k=2)

    assert [job["job_id"] for job in visible_jobs] == ["job_1", "job_2"]