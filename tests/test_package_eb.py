from __future__ import annotations

import zipfile

import pytest

import scripts.package_eb as package_eb


def _write_fixture_project(project_root):
    (project_root / "src" / "api").mkdir(parents=True)
    (project_root / "data" / "processed" / "jobs").mkdir(parents=True)
    (project_root / "frontend").mkdir()
    (project_root / "Procfile").write_text("web: uvicorn src.api.app:app\n", encoding="utf-8")
    (project_root / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
    (project_root / "src" / "api" / "app.py").write_text("app = object()\n", encoding="utf-8")
    (project_root / "src" / "api" / "__pycache__").mkdir()
    (project_root / "src" / "api" / "__pycache__" / "app.pyc").write_bytes(b"cache")
    (project_root / "data" / "processed" / "jobs" / "job.json").write_text('{"job_id": "1"}\n', encoding="utf-8")
    (project_root / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")


def test_build_source_bundle_contains_backend_files_without_parent_directory(tmp_path) -> None:
    _write_fixture_project(tmp_path)

    summary = package_eb.build_source_bundle(
        output_file=tmp_path / "outputs" / "backend.zip",
        project_root=tmp_path,
    )

    with zipfile.ZipFile(summary["output_file"]) as archive:
        names = set(archive.namelist())

    assert "Procfile" in names
    assert "requirements.txt" in names
    assert "src/api/app.py" in names
    assert "data/processed/jobs/job.json" in names
    assert "frontend/package.json" not in names
    assert "src/api/__pycache__/app.pyc" not in names
    assert all(not name.startswith("InternLens/") for name in names)


def test_build_source_bundle_can_skip_bundled_jobs(tmp_path) -> None:
    _write_fixture_project(tmp_path)

    summary = package_eb.build_source_bundle(
        output_file=tmp_path / "outputs" / "backend.zip",
        project_root=tmp_path,
        include_jobs=False,
    )

    with zipfile.ZipFile(summary["output_file"]) as archive:
        names = set(archive.namelist())

    assert "src/api/app.py" in names
    assert "data/processed/jobs/job.json" not in names
    assert summary["include_jobs"] is False


def test_build_source_bundle_requires_runtime_files(tmp_path) -> None:
    (tmp_path / "src" / "api").mkdir(parents=True)
    (tmp_path / "data" / "processed" / "jobs").mkdir(parents=True)
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (tmp_path / "src" / "api" / "app.py").write_text("app = object()\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Procfile"):
        package_eb.build_source_bundle(
            output_file=tmp_path / "outputs" / "backend.zip",
            project_root=tmp_path,
        )
