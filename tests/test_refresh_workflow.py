from pathlib import Path


def test_refresh_workflow_verifies_corpus_health_before_uploading_artifact() -> None:
    workflow = Path(".github/workflows/refresh-job-corpus.yml").read_text(encoding="utf-8")

    refresh_index = workflow.index("python scripts/refresh_job_corpus.py")
    health_index = workflow.index("python scripts/check_corpus_health.py --min-active-jobs 1")
    upload_index = workflow.index("actions/upload-artifact@v7")

    assert refresh_index < health_index < upload_index
    assert "--max-failed-sources 2" in workflow
    assert "--report-file outputs/corpus_refresh_report.json" in workflow
    assert "if: always()" in workflow
    assert "outputs/corpus_refresh_report.json" in workflow
    assert "outputs/corpus_health.json" in workflow
    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v7" in workflow
    assert "actions/upload-artifact@v7" in workflow


def test_python_test_workflow_uses_current_node24_actions() -> None:
    workflow = Path(".github/workflows/python-tests.yml").read_text(encoding="utf-8")

    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v7" in workflow
