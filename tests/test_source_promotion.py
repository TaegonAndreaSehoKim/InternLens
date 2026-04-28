from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.promote_sources as promote_script
from src.discovery.source_promotion import promote_validated_sources


def test_promote_validated_sources_adds_new_entries_to_registries() -> None:
    discovered = [
        {
            "company": "Acme",
            "source_type": "lever",
            "source_identifier": "acme",
            "status": "validated",
            "source_score": 0.7,
            "internship_likelihood": 0.8,
        },
        {
            "company": "Waymo",
            "source_type": "greenhouse",
            "source_identifier": "waymo-new",
            "status": "validated",
            "source_score": 0.66,
            "internship_likelihood": 0.4,
        },
    ]

    updated_discovered, lever_registry, greenhouse_registry, summary = promote_validated_sources(
        discovered,
        lever_registry=[],
        greenhouse_registry=[],
        min_score=0.45,
        require_internship_signal=True,
        promoted_at="2026-04-04T12:00:00Z",
    )

    assert summary["promoted"] == 2
    assert lever_registry[0]["site_name"] == "acme"
    assert lever_registry[0]["internship_only"] is True
    assert greenhouse_registry[0]["board_token"] == "waymo-new"
    assert all(record["status"] == "active" for record in updated_discovered)
    assert all(record["last_promoted_at"] == "2026-04-04T12:00:00Z" for record in updated_discovered)


def test_promote_validated_sources_marks_promoted_lever_entries_internship_only() -> None:
    discovered = [
        {
            "company": "Focused Lever",
            "source_type": "lever",
            "source_identifier": "focusedlever",
            "status": "validated",
            "source_score": 0.48,
            "internship_likelihood": 0.08,
            "discovery_method": "careers_page_scan",
        }
    ]

    _, lever_registry, _, summary = promote_validated_sources(
        discovered,
        lever_registry=[],
        greenhouse_registry=[],
        min_score=0.45,
        require_internship_signal=True,
        min_internship_likelihood=0.08,
        promoted_at="2026-04-04T12:00:00Z",
    )

    assert summary["promoted"] == 1
    assert lever_registry[0]["internship_only"] is True


def test_promote_validated_sources_reactivates_existing_inactive_entry() -> None:
    discovered = [
        {
            "company": "Cloudflare",
            "source_type": "greenhouse",
            "source_identifier": "cloudflare",
            "status": "validated",
            "source_score": 0.6,
            "internship_likelihood": 0.2,
        }
    ]
    greenhouse_registry = [
        {
            "board_token": "cloudflare",
            "active": False,
            "notes": "too noisy before",
        }
    ]

    updated_discovered, _, updated_greenhouse, summary = promote_validated_sources(
        discovered,
        lever_registry=[],
        greenhouse_registry=greenhouse_registry,
        min_score=0.45,
        require_internship_signal=True,
        reactivate_inactive_sources=True,
        promoted_at="2026-04-04T12:00:00Z",
    )

    assert summary["reactivated"] == 1
    assert updated_discovered[0]["status"] == "active"
    assert updated_greenhouse[0]["active"] is True
    assert "promoted from discovered sources" in updated_greenhouse[0]["notes"]


def test_promote_validated_sources_skips_inactive_entry_by_default() -> None:
    discovered = [
        {
            "company": "Cloudflare",
            "source_type": "greenhouse",
            "source_identifier": "cloudflare",
            "status": "validated",
            "source_score": 0.6,
            "internship_likelihood": 0.2,
        }
    ]
    greenhouse_registry = [
        {
            "board_token": "cloudflare",
            "active": False,
            "notes": "too noisy before",
        }
    ]

    updated_discovered, _, updated_greenhouse, summary = promote_validated_sources(
        discovered,
        lever_registry=[],
        greenhouse_registry=greenhouse_registry,
        min_score=0.45,
        require_internship_signal=True,
        promoted_at="2026-04-04T12:00:00Z",
    )

    assert summary["skipped_inactive"] == 1
    assert summary["reactivated"] == 0
    assert updated_discovered[0]["status"] == "validated"
    assert updated_greenhouse[0]["active"] is False


def test_promote_validated_sources_skips_low_score_and_non_validated_records() -> None:
    discovered = [
        {
            "company": "Low Score",
            "source_type": "lever",
            "source_identifier": "low-score",
            "status": "validated",
            "source_score": 0.3,
            "internship_likelihood": 0.6,
        },
        {
            "company": "Candidate Co",
            "source_type": "greenhouse",
            "source_identifier": "candidate-co",
            "status": "candidate",
            "source_score": 0.9,
            "internship_likelihood": 0.9,
        },
    ]

    updated_discovered, lever_registry, greenhouse_registry, summary = promote_validated_sources(
        discovered,
        lever_registry=[],
        greenhouse_registry=[],
        min_score=0.45,
        require_internship_signal=True,
        promoted_at="2026-04-04T12:00:00Z",
    )

    assert summary["skipped_score"] == 1
    assert summary["skipped_status"] == 1
    assert lever_registry == []
    assert greenhouse_registry == []
    assert updated_discovered[0]["status"] == "validated"
    assert updated_discovered[1]["status"] == "candidate"


def test_promote_validated_sources_applies_direct_probe_safeguard() -> None:
    discovered = [
        {
            "company": "Broad Board",
            "source_type": "greenhouse",
            "source_identifier": "broad",
            "status": "validated",
            "source_score": 0.47,
            "internship_likelihood": 0.12,
            "discovery_method": "direct_ats_probe",
        },
        {
            "company": "Focused Board",
            "source_type": "greenhouse",
            "source_identifier": "focused",
            "status": "validated",
            "source_score": 0.5,
            "internship_likelihood": 0.16,
            "discovery_method": "direct_ats_probe",
        },
    ]

    updated_discovered, _, greenhouse_registry, summary = promote_validated_sources(
        discovered,
        lever_registry=[],
        greenhouse_registry=[],
        min_score=0.45,
        require_internship_signal=True,
        direct_probe_min_score=0.5,
        direct_probe_min_internship_likelihood=0.12,
        promoted_at="2026-04-04T12:00:00Z",
    )

    assert summary["promoted"] == 1
    assert summary["skipped_direct_probe"] == 1
    assert [entry["board_token"] for entry in greenhouse_registry] == ["focused"]
    assert updated_discovered[0]["status"] == "validated"
    assert updated_discovered[1]["status"] == "active"


def test_promote_validated_sources_applies_global_internship_threshold() -> None:
    discovered = [
        {
            "company": "Barely Related",
            "source_type": "lever",
            "source_identifier": "barelyrelated",
            "status": "validated",
            "source_score": 0.8,
            "internship_likelihood": 0.04,
            "discovery_method": "careers_page_scan",
        },
        {
            "company": "Minimum Signal",
            "source_type": "lever",
            "source_identifier": "minimumsignal",
            "status": "validated",
            "source_score": 0.8,
            "internship_likelihood": 0.08,
            "discovery_method": "careers_page_scan",
        },
    ]

    updated_discovered, lever_registry, _, summary = promote_validated_sources(
        discovered,
        lever_registry=[],
        greenhouse_registry=[],
        min_score=0.45,
        require_internship_signal=True,
        min_internship_likelihood=0.08,
        promoted_at="2026-04-04T12:00:00Z",
    )

    assert summary["promoted"] == 1
    assert summary["skipped_internship"] == 1
    assert [entry["site_name"] for entry in lever_registry] == ["minimumsignal"]
    assert [record["status"] for record in updated_discovered] == ["validated", "active"]


def test_promote_validated_sources_skips_manual_review_records() -> None:
    discovered = [
        {
            "company": "Blocked Co",
            "source_type": "manual_review",
            "source_identifier": "blockedco",
            "status": "blocked",
            "source_score": 1.0,
            "internship_likelihood": 1.0,
            "discovery_method": "blocked_page_review",
        },
        {
            "company": "Manual Validated",
            "source_type": "manual_review",
            "source_identifier": "manualvalidated",
            "status": "validated",
            "source_score": 1.0,
            "internship_likelihood": 1.0,
            "discovery_method": "blocked_page_review",
        },
    ]

    updated_discovered, lever_registry, greenhouse_registry, summary = promote_validated_sources(
        discovered,
        lever_registry=[],
        greenhouse_registry=[],
        min_score=0.45,
        require_internship_signal=True,
        promoted_at="2026-04-04T12:00:00Z",
    )

    assert summary["skipped_status"] == 1
    assert summary["skipped_unsupported"] == 1
    assert lever_registry == []
    assert greenhouse_registry == []
    assert [record["status"] for record in updated_discovered] == ["blocked", "validated"]


def test_promote_sources_script_updates_all_target_files(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    registry_dir = tmp_path / "data" / "source_registry"
    registry_dir.mkdir(parents=True, exist_ok=True)

    discovered_path = registry_dir / "discovered_sources.json"
    lever_path = registry_dir / "lever_targets.json"
    greenhouse_path = registry_dir / "greenhouse_targets.json"

    discovered_path.write_text(
        json.dumps(
            [
                {
                    "company": "Acme",
                    "source_type": "lever",
                    "source_identifier": "acme",
                    "status": "validated",
                    "source_score": 0.8,
                    "internship_likelihood": 0.7,
                }
            ]
        ),
        encoding="utf-8",
    )
    lever_path.write_text("[]", encoding="utf-8")
    greenhouse_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(promote_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        promote_script,
        "_parse_args",
        lambda: SimpleNamespace(
            input_file="data/source_registry/discovered_sources.json",
            lever_registry="data/source_registry/lever_targets.json",
            greenhouse_registry="data/source_registry/greenhouse_targets.json",
            min_score=0.45,
            allow_non_internship_sources=False,
            min_internship_likelihood=0.08,
            direct_probe_min_score=0.5,
            direct_probe_min_internship_likelihood=0.12,
            reactivate_inactive_sources=False,
        ),
    )

    promote_script.main()
    output = capsys.readouterr().out
    discovered_payload = json.loads(discovered_path.read_text(encoding="utf-8"))
    lever_payload = json.loads(lever_path.read_text(encoding="utf-8"))

    assert "Source promotion complete" in output
    assert discovered_payload[0]["status"] == "active"
    assert lever_payload[0]["site_name"] == "acme"


def test_promote_sources_script_dry_run_does_not_update_files(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    registry_dir = tmp_path / "data" / "source_registry"
    registry_dir.mkdir(parents=True, exist_ok=True)

    discovered_path = registry_dir / "discovered_sources.json"
    lever_path = registry_dir / "lever_targets.json"
    greenhouse_path = registry_dir / "greenhouse_targets.json"

    discovered_payload = [
        {
            "company": "Promote Me",
            "source_type": "lever",
            "source_identifier": "promoteme",
            "status": "validated",
            "source_score": 0.9,
            "internship_likelihood": 0.7,
            "discovery_method": "careers_page_scan",
        },
        {
            "company": "Too Broad",
            "source_type": "greenhouse",
            "source_identifier": "toobroad",
            "status": "validated",
            "source_score": 0.47,
            "internship_likelihood": 0.08,
            "discovery_method": "direct_ats_probe",
            "internship_signal_examples": ["MBA Product Manager Intern"],
        },
        {
            "company": "Inactive Co",
            "source_type": "greenhouse",
            "source_identifier": "inactiveco",
            "status": "validated",
            "source_score": 0.9,
            "internship_likelihood": 0.5,
            "discovery_method": "direct_ats_probe",
        },
    ]
    greenhouse_payload = [
        {
            "board_token": "inactiveco",
            "active": False,
            "notes": "disabled manually",
        }
    ]

    discovered_original = json.dumps(discovered_payload, indent=2)
    lever_original = "[]"
    greenhouse_original = json.dumps(greenhouse_payload, indent=2)
    discovered_path.write_text(discovered_original, encoding="utf-8")
    lever_path.write_text(lever_original, encoding="utf-8")
    greenhouse_path.write_text(greenhouse_original, encoding="utf-8")

    monkeypatch.setattr(promote_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        promote_script,
        "_parse_args",
        lambda: SimpleNamespace(
            input_file="data/source_registry/discovered_sources.json",
            lever_registry="data/source_registry/lever_targets.json",
            greenhouse_registry="data/source_registry/greenhouse_targets.json",
            min_score=0.45,
            allow_non_internship_sources=False,
            min_internship_likelihood=0.08,
            direct_probe_min_score=0.5,
            direct_probe_min_internship_likelihood=0.12,
            reactivate_inactive_sources=False,
            dry_run=True,
        ),
    )

    promote_script.main()
    output = capsys.readouterr().out

    assert "Source promotion dry run" in output
    assert "Would promote or reactivate:" in output
    assert "Promote Me | lever | promoteme" in output
    assert "Skipped by direct probe safeguard:" in output
    assert "Too Broad | greenhouse | toobroad" in output
    assert "examples=MBA Product Manager Intern" in output
    assert "Skipped inactive registry entries:" in output
    assert "Inactive Co | greenhouse | inactiveco" in output
    direct_section = output.split("Skipped by direct probe safeguard:", 1)[1].split(
        "Skipped inactive registry entries:",
        1,
    )[0]
    assert "Inactive Co | greenhouse | inactiveco" not in direct_section
    assert discovered_path.read_text(encoding="utf-8") == discovered_original
    assert lever_path.read_text(encoding="utf-8") == lever_original
    assert greenhouse_path.read_text(encoding="utf-8") == greenhouse_original
