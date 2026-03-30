from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.fetch_lever_registry as registry_script


def _write_registry(path: Path, payload: list[dict]) -> None:
    # Write one registry JSON file for registry loader tests.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def test_filter_internship_jobs_keeps_only_internship_like_postings() -> None:
    # Keep postings that look like internships and drop non-intern roles.
    jobs = [
        {
            "text": "Machine Learning Intern",
            "descriptionPlain": "Remote internship role.",
            "categories": {"commitment": "Internship"},
        },
        {
            "text": "Software Engineer",
            "descriptionPlain": "Full-time backend role.",
            "categories": {"commitment": "Full-time"},
        },
        {
            "text": "Data Analyst",
            "descriptionPlain": "Summer internship working on analytics.",
            "categories": {"commitment": "Temporary"},
        },
    ]

    filtered = registry_script._filter_internship_jobs(jobs)

    assert len(filtered) == 2
    assert filtered[0]["text"] == "Machine Learning Intern"
    assert filtered[1]["text"] == "Data Analyst"


def test_load_registry_reads_valid_entries_and_skips_invalid_rows(tmp_path: Path) -> None:
    # Load valid registry rows and skip rows without a site_name.
    registry_path = tmp_path / "lever_targets.json"
    _write_registry(
        registry_path,
        [
            {
                "site_name": "acds",
                "active": True,
                "internship_only": True,
                "notes": "demo/eval source",
            },
            {
                "site_name": "rws",
                "active": False,
                "internship_only": False,
                "notes": "smoke-test source",
            },
            {
                "site_name": "",
                "active": True,
                "internship_only": True,
                "notes": "invalid",
            },
        ],
    )

    entries = registry_script._load_registry(registry_path)

    assert len(entries) == 2
    assert entries[0]["site_name"] == "acds"
    assert entries[0]["active"] is True
    assert entries[0]["internship_only"] is True
    assert entries[1]["site_name"] == "rws"
    assert entries[1]["active"] is False
    assert entries[1]["internship_only"] is False


def test_load_registry_rejects_non_list_json(tmp_path: Path) -> None:
    # The registry file must be a list of board entries.
    registry_path = tmp_path / "lever_targets.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump({"site_name": "acds"}, f, indent=2)

    try:
        registry_script._load_registry(registry_path)
        assert False, "Expected ValueError for non-list registry payload"
    except ValueError as e:
        assert "Registry JSON must be a list" in str(e)


def test_main_fetches_registry_entries_and_applies_filters(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    # Verify that main() loads the registry, applies internship filtering,
    # and reports the final processed counts.
    registry_path = tmp_path / "lever_targets.json"
    _write_registry(
        registry_path,
        [
            {
                "site_name": "acds",
                "active": True,
                "internship_only": True,
                "notes": "demo/eval source",
            },
            {
                "site_name": "rws",
                "active": True,
                "internship_only": False,
                "notes": "smoke-test source",
            },
            {
                "site_name": "inactive_board",
                "active": False,
                "internship_only": False,
                "notes": "inactive source",
            },
        ],
    )

    monkeypatch.setattr(
        registry_script,
        "_parse_args",
        lambda: SimpleNamespace(
            registry_path=str(registry_path),
            timeout=60.0,
            limit=None,
            only_active=True,
        ),
    )
    monkeypatch.setattr(registry_script, "PROJECT_ROOT", tmp_path)

    fetch_calls: list[str] = []
    processed_counts: dict[str, int] = {}

    def fake_fetch(site_name: str, *, limit, timeout):
        fetch_calls.append(site_name)

        if site_name == "acds":
            return [
                {
                    "text": "Machine Learning Intern",
                    "descriptionPlain": "Internship role",
                    "categories": {"commitment": "Internship"},
                },
                {
                    "text": "Software Engineer",
                    "descriptionPlain": "Full-time role",
                    "categories": {"commitment": "Full-time"},
                },
            ]

        if site_name == "rws":
            return [
                {
                    "text": "AI Data Specialist",
                    "descriptionPlain": "Contract work",
                    "categories": {"commitment": "Temporary/Contract"},
                }
            ]

        return []

    def fake_save_raw(site_name: str, jobs: list[dict], *, project_root: Path) -> Path:
        return project_root / "data" / "raw" / "lever" / site_name / "jobs_test.json"

    def fake_save_processed(site_name: str, jobs: list[dict], *, project_root: Path) -> list[Path]:
        processed_counts[site_name] = len(jobs)
        return [
            project_root / "data" / "processed" / "jobs" / "lever" / site_name / f"{site_name}_{i}.json"
            for i in range(len(jobs))
        ]

    monkeypatch.setattr(registry_script, "fetch_lever_postings", fake_fetch)
    monkeypatch.setattr(registry_script, "save_raw_lever_snapshot", fake_save_raw)
    monkeypatch.setattr(registry_script, "save_processed_lever_postings", fake_save_processed)

    registry_script.main()
    output = capsys.readouterr().out

    assert fetch_calls == ["acds", "rws"]
    assert processed_counts["acds"] == 1
    assert processed_counts["rws"] == 1
    assert "=== Fetching Lever board: acds ===" in output
    assert "=== Fetching Lever board: rws ===" in output
    assert "Total filtered jobs fetched: 2" in output
    assert "Total processed jobs saved: 2" in output