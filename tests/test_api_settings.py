from __future__ import annotations

from pathlib import Path

import src.api.app as api_app
from src.api.settings import DEFAULT_CORS_ORIGINS, env_list, env_value, resolve_project_path


def test_env_list_uses_default_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("INTERNLENS_CORS_ORIGINS", raising=False)

    assert env_list("INTERNLENS_CORS_ORIGINS", DEFAULT_CORS_ORIGINS) == DEFAULT_CORS_ORIGINS


def test_env_list_parses_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setenv("INTERNLENS_CORS_ORIGINS", "https://demo.example.com, http://localhost:5173 ,,")

    assert env_list("INTERNLENS_CORS_ORIGINS", DEFAULT_CORS_ORIGINS) == [
        "https://demo.example.com",
        "http://localhost:5173",
    ]


def test_env_value_trims_and_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("INTERNLENS_JOBS_DIR", "  data/sample_jobs  ")
    assert env_value("INTERNLENS_JOBS_DIR", "data/processed/jobs") == "data/sample_jobs"

    monkeypatch.setenv("INTERNLENS_JOBS_DIR", "   ")
    assert env_value("INTERNLENS_JOBS_DIR", "data/processed/jobs") == "data/processed/jobs"


def test_resolve_project_path_supports_relative_and_absolute_paths(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    absolute_path = tmp_path / "data" / "internlens.db"

    assert resolve_project_path(project_root, "data/processed/jobs") == project_root / "data" / "processed" / "jobs"
    assert resolve_project_path(project_root, absolute_path) == absolute_path


def test_database_path_can_be_configured_with_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("INTERNLENS_DB_PATH", str(tmp_path / "state" / "internlens.db"))

    assert api_app._database_path() == tmp_path / "state" / "internlens.db"
