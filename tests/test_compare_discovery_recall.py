from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.compare_discovery_recall as compare_script


def test_build_recall_comparison_reports_added_priority_sources(monkeypatch) -> None:
    seeds = [{"company": "Acme", "homepage_url": "https://acme.com"}]

    def fake_discover_sources(seeds, timeout, priority_follow_limit, **kwargs):
        if priority_follow_limit == 0:
            return (
                [
                    {
                        "company": "Acme",
                        "source_type": "greenhouse",
                        "source_identifier": "acme-main",
                        "discovery_method": "homepage_scan",
                    }
                ],
                [{"reason": "timeout"}],
            )

        return (
            [
                {
                    "company": "Acme",
                    "source_type": "greenhouse",
                    "source_identifier": "acme-main",
                    "discovery_method": "homepage_scan",
                },
                {
                    "company": "Acme",
                    "source_type": "lever",
                    "source_identifier": "acme-university",
                    "discovery_method": "priority_link_scan",
                },
            ],
            [],
        )

    monkeypatch.setattr(compare_script, "discover_sources", fake_discover_sources)

    report = compare_script.build_recall_comparison(
        seeds=seeds,
        timeout=15.0,
        baseline_priority_follow_limit=0,
        priority_follow_limit=5,
        probe_direct_ats=False,
        record_blocked_sources=False,
        direct_probe_limit=1,
        max_direct_probe_identifiers=2,
        discovered_at="2026-04-30T12:00:00Z",
    )

    assert report["baseline"]["candidate_count"] == 1
    assert report["priority_follow"]["candidate_count"] == 2
    assert report["delta"]["candidate_count"] == 1
    assert report["delta"]["added_source_count"] == 1
    assert report["baseline"]["warning_summary"] == {"timeout": 1}
    assert report["priority_follow"]["method_summary"] == {
        "homepage_scan": 1,
        "priority_link_scan": 1,
    }
    assert report["added_sources"][0]["source_identifier"] == "acme-university"


def test_compare_discovery_recall_main_writes_report(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    seed_path = tmp_path / "data" / "source_registry" / "company_seeds.json"
    output_path = tmp_path / "outputs" / "discovery_recall_compare.json"
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    seed_path.write_text(
        json.dumps(
            [
                {"company": "Acme", "homepage_url": "https://acme.com"},
                {"company": "Other", "homepage_url": "https://other.example.com"},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(compare_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        compare_script,
        "_parse_args",
        lambda: SimpleNamespace(
            seed_file="data/source_registry/company_seeds.json",
            seed_offset=0,
            seed_limit=1,
            timeout=15.0,
            baseline_priority_follow_limit=0,
            priority_follow_limit=5,
            probe_direct_ats=False,
            record_blocked_sources=False,
            direct_probe_limit=1,
            max_direct_probe_identifiers=2,
            output_file="outputs/discovery_recall_compare.json",
        ),
    )
    monkeypatch.setattr(
        compare_script,
        "build_recall_comparison",
        lambda **kwargs: {
            "generated_at": "2026-04-30T12:00:00Z",
            "config": {"seed_count": len(kwargs["seeds"])},
            "baseline": {
                "candidate_count": 1,
                "method_summary": {"homepage_scan": 1},
                "warning_count": 0,
                "warning_summary": {},
            },
            "priority_follow": {
                "candidate_count": 2,
                "method_summary": {"homepage_scan": 1, "priority_link_scan": 1},
                "warning_count": 0,
                "warning_summary": {},
            },
            "delta": {
                "candidate_count": 1,
                "warning_count": 0,
                "added_source_count": 1,
                "removed_source_count": 0,
            },
            "added_sources": [
                {
                    "company": "Acme",
                    "source_type": "lever",
                    "source_identifier": "acme-university",
                    "discovery_method": "priority_link_scan",
                }
            ],
            "removed_sources": [],
        },
    )

    compare_script.main()
    output = capsys.readouterr().out
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert "Discovery recall comparison complete" in output
    assert "Candidate count: 1 -> 2 (delta +1)" in output
    assert "Acme | lever | acme-university | method=priority_link_scan" in output
    assert payload["delta"]["added_source_count"] == 1
    assert payload["config"]["seed_count"] == 1
