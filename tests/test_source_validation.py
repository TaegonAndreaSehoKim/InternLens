from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.validate_sources as validate_script
from src.discovery.source_validation import (
    load_active_registry_keys,
    validate_discovered_sources,
    validate_source_record,
)


def test_load_active_registry_keys_reads_only_active_sources(tmp_path: Path) -> None:
    registry_dir = tmp_path / "data" / "source_registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "lever_targets.json").write_text(
        json.dumps(
            [
                {"site_name": "rws", "active": True},
                {"site_name": "ignored", "active": False},
            ]
        ),
        encoding="utf-8",
    )
    (registry_dir / "greenhouse_targets.json").write_text(
        json.dumps(
            [
                {"board_token": "waymo", "active": True},
                {"board_token": "cloudflare", "active": False},
            ]
        ),
        encoding="utf-8",
    )

    keys = load_active_registry_keys(tmp_path)

    assert keys == {("lever", "rws"), ("greenhouse", "waymo")}


def test_validate_source_record_marks_success_and_notes_active_registry() -> None:
    record = {
        "company": "Waymo",
        "source_type": "greenhouse",
        "source_identifier": "waymo",
        "status": "candidate",
    }

    def fake_fetch(board_token: str, *, timeout: float, limit: int | None, content: bool):
        assert board_token == "waymo"
        return [
            {"title": "Software Engineering Intern", "content": "Summer internship"},
            {"title": "Machine Learning Engineer", "content": "Full-time role"},
        ]

    updated = validate_source_record(
        record,
        timeout=20.0,
        limit=10,
        active_registry_keys={("greenhouse", "waymo")},
        validated_at="2026-04-04T12:00:00Z",
        greenhouse_fetch_fn=fake_fetch,
        greenhouse_normalize_fn=lambda job, source_identifier: {"ok": True},
    )

    assert updated["status"] == "validated"
    assert updated["internship_likelihood"] == 0.5
    assert updated["last_validated_at"] == "2026-04-04T12:00:00Z"
    assert "already present in active registry" in updated["validation_notes"]
    assert updated["source_score"] > 0.0


def test_validate_source_record_marks_fetch_failure_as_rejected() -> None:
    record = {
        "company": "Broken Co",
        "source_type": "lever",
        "source_identifier": "broken",
        "status": "candidate",
    }

    def fake_fetch(site_name: str, *, timeout: float, limit: int | None):
        raise RuntimeError("boom")

    updated = validate_source_record(
        record,
        timeout=20.0,
        limit=5,
        active_registry_keys=set(),
        lever_fetch_fn=fake_fetch,
    )

    assert updated["status"] == "rejected"
    assert "fetch failed" in updated["validation_notes"]
    assert updated["source_score"] == 0.0


def test_validate_discovered_sources_skips_non_candidates_by_default() -> None:
    records = [
        {
            "company": "Waymo",
            "source_type": "greenhouse",
            "source_identifier": "waymo",
            "status": "candidate",
        },
        {
            "company": "RWS",
            "source_type": "lever",
            "source_identifier": "rws",
            "status": "active",
        },
    ]

    validated_records, summary = validate_discovered_sources(
        records,
        timeout=20.0,
        limit=10,
        active_registry_keys=set(),
        include_non_candidate=False,
        greenhouse_fetch_fn=lambda board_token, *, timeout, limit, content: [
            {"title": "Engineering Intern", "content": "Internship"}
        ],
        greenhouse_normalize_fn=lambda job, source_identifier: {"ok": True},
    )

    assert summary == {"attempted": 1, "validated": 1, "rejected": 0, "skipped": 1}
    assert validated_records[0]["status"] == "validated"
    assert validated_records[1]["status"] == "active"


def test_validate_sources_script_updates_discovered_sources_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    input_path = tmp_path / "data" / "source_registry" / "discovered_sources.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(
        json.dumps(
            [
                {
                    "company": "Waymo",
                    "source_type": "greenhouse",
                    "source_identifier": "waymo",
                    "status": "candidate",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(validate_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        validate_script,
        "_parse_args",
        lambda: SimpleNamespace(
            input_file="data/source_registry/discovered_sources.json",
            timeout=20.0,
            limit=15,
            include_non_candidate=False,
        ),
    )
    monkeypatch.setattr(validate_script, "load_active_registry_keys", lambda project_root: set())
    monkeypatch.setattr(
        validate_script,
        "validate_discovered_sources",
        lambda records, timeout, limit, active_registry_keys, include_non_candidate: (
            [
                {
                    **records[0],
                    "status": "validated",
                    "validation_notes": "fetch succeeded with 3 jobs",
                    "source_score": 0.8,
                    "internship_likelihood": 0.67,
                }
            ],
            {"attempted": 1, "validated": 1, "rejected": 0, "skipped": 0},
        ),
    )

    validate_script.main()
    output = capsys.readouterr().out
    payload = json.loads(input_path.read_text(encoding="utf-8"))

    assert "Source validation complete" in output
    assert payload[0]["status"] == "validated"
