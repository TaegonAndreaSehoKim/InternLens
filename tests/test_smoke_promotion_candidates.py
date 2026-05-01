from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.smoke_promotion_candidates as smoke_script


def test_build_promotion_candidate_smoke_fetches_only_promotable_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    discovered = [
        {
            "company": "Acme",
            "source_type": "lever",
            "source_identifier": "acme",
            "status": "validated",
            "source_score": 0.8,
            "internship_likelihood": 0.5,
        },
        {
            "company": "Too Broad",
            "source_type": "greenhouse",
            "source_identifier": "toobroad",
            "status": "validated",
            "source_score": 0.4,
            "internship_likelihood": 0.0,
        },
    ]
    fetched_registries: dict[str, list[dict]] = {}

    def fake_lever_fetch(*, registry_path, timeout, limit, only_active, project_root):
        fetched_registries["lever"] = json.loads(Path(registry_path).read_text(encoding="utf-8"))
        return {"entries_fetched": 1, "total_filtered_jobs": 1, "total_processed_jobs": 1}

    def fake_greenhouse_fetch(*, registry_path, timeout, limit, only_active, internship_only, project_root):
        fetched_registries["greenhouse"] = json.loads(Path(registry_path).read_text(encoding="utf-8"))
        return {"entries_fetched": 0, "total_filtered_jobs": 0, "total_processed_jobs": 0}

    monkeypatch.setattr(smoke_script, "run_lever_registry_fetch", fake_lever_fetch)
    monkeypatch.setattr(smoke_script, "run_greenhouse_registry_fetch", fake_greenhouse_fetch)
    monkeypatch.setattr(
        smoke_script,
        "_rank_temp_jobs",
        lambda **kwargs: {
            "processed_jobs": 1,
            "action_counts": {"Apply Later": 1},
            "blocker_counts": {},
            "top_results": [{"title": "Software Engineering Intern"}],
        },
    )

    report = smoke_script.build_promotion_candidate_smoke(
        discovered_records=discovered,
        lever_registry=[],
        greenhouse_registry=[],
        profile_path=tmp_path / "profile.json",
        min_score=0.45,
        require_internship_signal=True,
        min_internship_likelihood=0.08,
        direct_probe_min_score=0.5,
        direct_probe_min_internship_likelihood=0.12,
        reactivate_inactive_sources=False,
        fetch_timeout=60.0,
        fetch_limit=None,
        greenhouse_all_jobs=False,
        top_k=10,
    )

    assert report["promotion_summary"]["promoted"] == 1
    assert report["promotion_summary"]["skipped_score"] == 1
    assert report["candidate_count"] == 1
    assert report["candidate_sources"][0]["source_identifier"] == "acme"
    assert fetched_registries["lever"][0]["site_name"] == "acme"
    assert fetched_registries["greenhouse"] == []
    assert report["fetch_summary"]["total_entries_fetched"] == 1
    assert report["ranking_summary"]["action_counts"] == {"Apply Later": 1}


def test_smoke_promotion_candidates_main_writes_report(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    registry_dir = tmp_path / "data" / "source_registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "discovered_sources.json").write_text("[]", encoding="utf-8")
    (registry_dir / "lever_targets.json").write_text("[]", encoding="utf-8")
    (registry_dir / "greenhouse_targets.json").write_text("[]", encoding="utf-8")
    output_path = tmp_path / "outputs" / "promotion_candidate_smoke.json"

    monkeypatch.setattr(smoke_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        smoke_script,
        "_parse_args",
        lambda: SimpleNamespace(
            input_file="data/source_registry/discovered_sources.json",
            lever_registry="data/source_registry/lever_targets.json",
            greenhouse_registry="data/source_registry/greenhouse_targets.json",
            profile_path="data/processed/candidate_profile_example.json",
            output_file="outputs/promotion_candidate_smoke.json",
            min_score=0.45,
            allow_non_internship_sources=False,
            min_internship_likelihood=0.08,
            direct_probe_min_score=0.5,
            direct_probe_min_internship_likelihood=0.12,
            reactivate_inactive_sources=False,
            fetch_timeout=60.0,
            fetch_limit=None,
            greenhouse_all_jobs=False,
            top_k=10,
        ),
    )
    monkeypatch.setattr(
        smoke_script,
        "build_promotion_candidate_smoke",
        lambda **kwargs: {
            "generated_at": "2026-05-01T12:00:00Z",
            "promotion_summary": {"promoted": 1},
            "candidate_count": 1,
            "candidate_sources": [
                {
                    "company": "Acme",
                    "source_type": "lever",
                    "source_identifier": "acme",
                }
            ],
            "fetch_summary": {"total_entries_fetched": 1, "total_processed_jobs": 1},
            "ranking_summary": {
                "processed_jobs": 1,
                "action_counts": {"Apply Later": 1},
                "blocker_counts": {},
                "top_results": [],
            },
        },
    )

    smoke_script.main()
    output = capsys.readouterr().out
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert "Promotion candidate smoke complete" in output
    assert "Promotion candidates: 1" in output
    assert "Processed jobs: 1" in output
    assert payload["candidate_sources"][0]["source_identifier"] == "acme"
