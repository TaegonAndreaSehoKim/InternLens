from pathlib import Path


def test_refresh_workflow_verifies_corpus_health_before_uploading_artifact() -> None:
    workflow = Path(".github/workflows/refresh-job-corpus.yml").read_text(encoding="utf-8")

    refresh_index = workflow.index("python scripts/refresh_job_corpus.py")
    health_index = workflow.index("python scripts/check_corpus_health.py --min-active-jobs 1")
    upload_index = workflow.index("actions/upload-artifact@v4")

    assert refresh_index < health_index < upload_index
    assert "outputs/corpus_health.json" in workflow
