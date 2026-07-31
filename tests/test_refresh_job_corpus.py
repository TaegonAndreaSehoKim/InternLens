from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.refresh_job_corpus as refresh_script


def test_main_refreshes_both_sources_and_prints_summary(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        refresh_script,
        "_parse_args",
        lambda: SimpleNamespace(
            timeout=60.0,
            limit=None,
            include_inactive=False,
            greenhouse_all_jobs=False,
            greenhouse_only=False,
            lever_only=False,
        ),
    )
    monkeypatch.setattr(refresh_script, "PROJECT_ROOT", tmp_path)

    lever_calls: list[dict] = []
    greenhouse_calls: list[dict] = []

    def fake_run_lever_registry_fetch(**kwargs):
        lever_calls.append(kwargs)
        return {
            "entries_fetched": 2,
            "total_filtered_jobs": 3,
            "total_processed_jobs": 3,
        }

    def fake_run_greenhouse_registry_fetch(**kwargs):
        greenhouse_calls.append(kwargs)
        return {
            "entries_fetched": 1,
            "total_filtered_jobs": 4,
            "total_processed_jobs": 4,
        }

    monkeypatch.setattr(refresh_script, "run_lever_registry_fetch", fake_run_lever_registry_fetch)
    monkeypatch.setattr(refresh_script, "run_greenhouse_registry_fetch", fake_run_greenhouse_registry_fetch)

    refresh_script.main()
    output = capsys.readouterr().out

    assert len(lever_calls) == 1
    assert len(greenhouse_calls) == 1
    assert "##### Refreshing Lever sources #####" in output
    assert "##### Refreshing Greenhouse sources #####" in output
    assert "Registry entries fetched: 3" in output
    assert "Filtered jobs saved: 7" in output
    assert "Processed job files saved: 7" in output


def test_main_can_refresh_only_greenhouse(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        refresh_script,
        "_parse_args",
        lambda: SimpleNamespace(
            timeout=60.0,
            limit=50,
            include_inactive=True,
            greenhouse_all_jobs=True,
            greenhouse_only=True,
            lever_only=False,
        ),
    )
    monkeypatch.setattr(refresh_script, "PROJECT_ROOT", tmp_path)

    def fake_run_greenhouse_registry_fetch(**kwargs):
        assert kwargs["only_active"] is False
        assert kwargs["internship_only"] is False
        assert kwargs["limit"] == 50
        return {
            "entries_fetched": 2,
            "total_filtered_jobs": 10,
            "total_processed_jobs": 10,
        }

    monkeypatch.setattr(
        refresh_script,
        "run_greenhouse_registry_fetch",
        fake_run_greenhouse_registry_fetch,
    )
    monkeypatch.setattr(
        refresh_script,
        "run_lever_registry_fetch",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("Lever should not run")),
    )

    refresh_script.main()
    output = capsys.readouterr().out

    assert "##### Refreshing Lever sources #####" not in output
    assert "##### Refreshing Greenhouse sources #####" in output


def test_main_rejects_conflicting_source_flags(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        refresh_script,
        "_parse_args",
        lambda: SimpleNamespace(
            timeout=60.0,
            limit=None,
            include_inactive=False,
            greenhouse_all_jobs=False,
            greenhouse_only=True,
            lever_only=True,
        ),
    )
    monkeypatch.setattr(refresh_script, "PROJECT_ROOT", tmp_path)

    try:
        refresh_script.main()
        assert False, "Expected ValueError for conflicting source flags"
    except ValueError as exc:
        assert "Choose at most one" in str(exc)


def test_main_tolerates_limited_source_failures_and_writes_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report_path = tmp_path / "outputs" / "corpus_refresh_report.json"
    monkeypatch.setattr(
        refresh_script,
        "_parse_args",
        lambda: SimpleNamespace(
            timeout=60.0,
            limit=None,
            include_inactive=False,
            greenhouse_all_jobs=False,
            greenhouse_only=False,
            lever_only=False,
            min_successful_sources=1,
            max_failed_sources=1,
            report_file=report_path,
        ),
    )
    monkeypatch.setattr(refresh_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        refresh_script,
        "run_lever_registry_fetch",
        lambda **kwargs: {
            "entries_selected": 2,
            "entries_fetched": 1,
            "entries_failed": 1,
            "total_filtered_jobs": 2,
            "total_processed_jobs": 2,
            "successful_sources": [{"provider": "lever", "source_id": "healthy"}],
            "failed_sources": [
                {
                    "provider": "lever",
                    "source_id": "broken",
                    "error_type": "RuntimeError",
                    "message": "HTTP 503",
                }
            ],
        },
    )
    monkeypatch.setattr(
        refresh_script,
        "run_greenhouse_registry_fetch",
        lambda **kwargs: {
            "entries_selected": 1,
            "entries_fetched": 1,
            "entries_failed": 0,
            "total_filtered_jobs": 3,
            "total_processed_jobs": 3,
            "successful_sources": [{"provider": "greenhouse", "source_id": "healthy"}],
            "failed_sources": [],
        },
    )

    refresh_script.main()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["entries_selected"] == 3
    assert report["successful_source_count"] == 2
    assert report["failed_source_count"] == 1
    assert report["failed_sources"][0]["source_id"] == "broken"


def test_main_fails_policy_after_writing_failure_report(tmp_path: Path, monkeypatch) -> None:
    report_path = tmp_path / "outputs" / "corpus_refresh_report.json"
    monkeypatch.setattr(
        refresh_script,
        "_parse_args",
        lambda: SimpleNamespace(
            timeout=60.0,
            limit=None,
            include_inactive=False,
            greenhouse_all_jobs=False,
            greenhouse_only=False,
            lever_only=False,
            min_successful_sources=1,
            max_failed_sources=0,
            report_file=report_path,
        ),
    )
    monkeypatch.setattr(refresh_script, "PROJECT_ROOT", tmp_path)
    failed_summary = {
        "entries_selected": 1,
        "entries_fetched": 0,
        "entries_failed": 1,
        "total_filtered_jobs": 0,
        "total_processed_jobs": 0,
        "successful_sources": [],
        "failed_sources": [
            {
                "provider": "lever",
                "source_id": "broken",
                "error_type": "RuntimeError",
                "message": "HTTP 503",
            }
        ],
    }
    monkeypatch.setattr(
        refresh_script,
        "run_lever_registry_fetch",
        lambda **kwargs: failed_summary,
    )
    monkeypatch.setattr(
        refresh_script,
        "run_greenhouse_registry_fetch",
        lambda **kwargs: {
            **failed_summary,
            "failed_sources": [
                {
                    **failed_summary["failed_sources"][0],
                    "provider": "greenhouse",
                    "source_id": "also-broken",
                }
            ],
        },
    )

    try:
        refresh_script.main()
        assert False, "Expected SystemExit for refresh policy failure"
    except SystemExit as exc:
        assert "Corpus refresh policy failed" in str(exc)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is False
    assert report["successful_source_count"] == 0
    assert report["failed_source_count"] == 2
