from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.fetch_greenhouse_registry as registry_script


def _write_registry(path: Path, payload: list[dict]) -> None:
    # Write one registry JSON file for registry loader tests.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def test_filter_internship_jobs_keeps_only_internship_like_postings() -> None:
    # Keep jobs that look like internships and drop non-intern roles.
    jobs = [
        {
            "title": "Machine Learning Intern",
            "content": "Remote internship role.",
        },
        {
            "title": "Software Engineer",
            "content": "Full-time backend role.",
        },
        {
            "title": "Data Analyst",
            "content": "Summer internship working on analytics.",
        },
    ]

    filtered = registry_script._filter_internship_jobs(jobs)

    assert len(filtered) == 2
    assert filtered[0]["title"] == "Machine Learning Intern"
    assert filtered[1]["title"] == "Data Analyst"


def test_load_registry_reads_valid_entries_and_skips_invalid_rows(tmp_path: Path) -> None:
    # Load valid registry rows and skip rows without a board_token.
    registry_path = tmp_path / "greenhouse_targets.json"
    _write_registry(
        registry_path,
        [
            {
                "board_token": "waymo",
                "active": True,
                "notes": "demo/eval source",
            },
            {
                "board_token": "honehealth",
                "active": False,
                "notes": "intern source",
            },
            {
                "board_token": "",
                "active": True,
                "notes": "invalid",
            },
        ],
    )

    entries = registry_script._load_registry(registry_path)

    assert len(entries) == 2
    assert entries[0]["board_token"] == "waymo"
    assert entries[0]["active"] is True
    assert entries[1]["board_token"] == "honehealth"
    assert entries[1]["active"] is False


def test_load_registry_rejects_non_list_json(tmp_path: Path) -> None:
    # The registry file must be a list of board entries.
    registry_path = tmp_path / "greenhouse_targets.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", encoding="utf-8") as f:
        json.dump({"board_token": "waymo"}, f, indent=2)

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
    registry_path = tmp_path / "greenhouse_targets.json"
    _write_registry(
        registry_path,
        [
            {
                "board_token": "waymo",
                "active": True,
                "notes": "demo/eval source",
            },
            {
                "board_token": "honehealth",
                "active": True,
                "notes": "intern source",
            },
            {
                "board_token": "inactive_board",
                "active": False,
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
            internship_only=True,
        ),
    )
    monkeypatch.setattr(registry_script, "PROJECT_ROOT", tmp_path)

    fetch_calls: list[str] = []
    processed_counts: dict[str, int] = {}

    def fake_fetch(board_token: str, *, limit, timeout, content):
        fetch_calls.append(board_token)

        if board_token == "waymo":
            return [
                {
                    "title": "Machine Learning Intern",
                    "content": "Internship role",
                },
                {
                    "title": "Software Engineer",
                    "content": "Full-time role",
                },
            ]

        if board_token == "honehealth":
            return [
                {
                    "title": "Data Science Intern",
                    "content": "Internship role",
                }
            ]

        return []

    def fake_save_raw(board_token: str, jobs: list[dict], *, project_root: Path) -> Path:
        return project_root / "data" / "raw" / "greenhouse" / board_token / "jobs_test.json"

    def fake_save_processed(board_token: str, jobs: list[dict], *, project_root: Path) -> list[Path]:
        processed_counts[board_token] = len(jobs)
        return [
            project_root / "data" / "processed" / "jobs" / "greenhouse" / board_token / f"{board_token}_{i}.json"
            for i in range(len(jobs))
        ]

    monkeypatch.setattr(registry_script, "fetch_greenhouse_jobs", fake_fetch)
    monkeypatch.setattr(registry_script, "save_raw_greenhouse_snapshot", fake_save_raw)
    monkeypatch.setattr(registry_script, "save_processed_greenhouse_jobs", fake_save_processed)

    registry_script.main()
    output = capsys.readouterr().out

    assert fetch_calls == ["waymo", "honehealth"]
    assert processed_counts["waymo"] == 1
    assert processed_counts["honehealth"] == 1
    assert "=== Fetching Greenhouse board: waymo ===" in output
    assert "=== Fetching Greenhouse board: honehealth ===" in output
    assert "Total filtered jobs fetched: 2" in output
    assert "Total processed jobs saved: 2" in output