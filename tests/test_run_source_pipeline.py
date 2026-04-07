from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import scripts.run_source_pipeline as pipeline_script


def test_main_runs_all_pipeline_steps_in_order(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        pipeline_script,
        "_parse_args",
        lambda: SimpleNamespace(
            seed_file="data/source_registry/company_seeds.json",
            discovered_file="data/source_registry/discovered_sources.json",
            lever_registry="data/source_registry/lever_targets.json",
            greenhouse_registry="data/source_registry/greenhouse_targets.json",
            discovery_timeout=20.0,
            validation_timeout=20.0,
            validation_limit=25,
            include_non_candidate=False,
            promotion_min_score=0.45,
            allow_non_internship_sources=False,
            refresh_timeout=60.0,
            refresh_limit=None,
            refresh_include_inactive=False,
            greenhouse_all_jobs=False,
            greenhouse_only=False,
            lever_only=False,
            skip_discovery=False,
            skip_validation=False,
            skip_promotion=False,
            skip_refresh=False,
        ),
    )
    monkeypatch.setattr(pipeline_script, "PROJECT_ROOT", tmp_path)

    calls: list[str] = []

    monkeypatch.setattr(
        pipeline_script,
        "_run_discovery",
        lambda args: calls.append("discovery") or {"stored_candidates": 3},
    )
    monkeypatch.setattr(
        pipeline_script,
        "_run_validation",
        lambda args: calls.append("validation") or {"validated": 2},
    )
    monkeypatch.setattr(
        pipeline_script,
        "_run_promotion",
        lambda args: calls.append("promotion") or {"promoted": 1},
    )
    monkeypatch.setattr(
        pipeline_script,
        "_run_refresh",
        lambda args: calls.append("refresh") or {"total_processed_jobs": 5},
    )

    pipeline_script.main()
    output = capsys.readouterr().out

    assert calls == ["discovery", "validation", "promotion", "refresh"]
    assert "Source pipeline complete" in output


def test_main_can_skip_selected_steps(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        pipeline_script,
        "_parse_args",
        lambda: SimpleNamespace(
            seed_file="data/source_registry/company_seeds.json",
            discovered_file="data/source_registry/discovered_sources.json",
            lever_registry="data/source_registry/lever_targets.json",
            greenhouse_registry="data/source_registry/greenhouse_targets.json",
            discovery_timeout=20.0,
            validation_timeout=20.0,
            validation_limit=25,
            include_non_candidate=False,
            promotion_min_score=0.45,
            allow_non_internship_sources=False,
            refresh_timeout=60.0,
            refresh_limit=None,
            refresh_include_inactive=False,
            greenhouse_all_jobs=False,
            greenhouse_only=False,
            lever_only=False,
            skip_discovery=True,
            skip_validation=False,
            skip_promotion=True,
            skip_refresh=False,
        ),
    )
    monkeypatch.setattr(pipeline_script, "PROJECT_ROOT", tmp_path)

    calls: list[str] = []

    monkeypatch.setattr(
        pipeline_script,
        "_run_discovery",
        lambda args: calls.append("discovery") or {},
    )
    monkeypatch.setattr(
        pipeline_script,
        "_run_validation",
        lambda args: calls.append("validation") or {},
    )
    monkeypatch.setattr(
        pipeline_script,
        "_run_promotion",
        lambda args: calls.append("promotion") or {},
    )
    monkeypatch.setattr(
        pipeline_script,
        "_run_refresh",
        lambda args: calls.append("refresh") or {},
    )

    pipeline_script.main()
    output = capsys.readouterr().out

    assert calls == ["validation", "refresh"]
    assert "Source pipeline complete" in output


def test_run_refresh_rejects_conflicting_source_flags(tmp_path: Path, monkeypatch) -> None:
    args = SimpleNamespace(
        lever_registry="data/source_registry/lever_targets.json",
        greenhouse_registry="data/source_registry/greenhouse_targets.json",
        refresh_timeout=60.0,
        refresh_limit=None,
        refresh_include_inactive=False,
        greenhouse_all_jobs=False,
        greenhouse_only=True,
        lever_only=True,
    )
    monkeypatch.setattr(pipeline_script, "PROJECT_ROOT", tmp_path)

    try:
        pipeline_script._run_refresh(args)
        assert False, "Expected ValueError for conflicting source flags"
    except ValueError as exc:
        assert "Choose at most one" in str(exc)
