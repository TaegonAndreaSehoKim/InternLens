from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.ingestion.snapshot_store as snapshots
import src.ingestion.greenhouse_client as greenhouse
import src.ingestion.lever_client as lever
from src.preprocessing.job_parser import REQUIRED_JOB_FIELDS


def job(job_id: str) -> dict:
    return {field: "" for field in REQUIRED_JOB_FIELDS} | {"job_id": job_id, "title": "Engineering Intern"}


def previous_snapshot(root: Path) -> Path:
    destination = root / "data/processed/jobs/manual/example"
    destination.mkdir(parents=True)
    (destination / "old.json").write_text(json.dumps(job("old")), encoding="utf-8")
    return destination


def test_successful_snapshot_replaces_closed_jobs_and_preserves_other_files(tmp_path):
    destination = previous_snapshot(tmp_path)
    (destination / "notes.txt").write_text("keep", encoding="utf-8")
    paths = snapshots.save_job_snapshot(destination, [job("new")], project_root=tmp_path)
    assert paths == [destination / "new.json"]
    assert json.loads(paths[0].read_text()) == job("new")
    assert not (destination / "old.json").exists()
    assert (destination / "notes.txt").read_text() == "keep"
    assert not list((tmp_path / "data").glob(".job-snapshot-*"))


def test_successful_empty_snapshot_removes_closed_jobs(tmp_path):
    destination = previous_snapshot(tmp_path)
    assert snapshots.save_job_snapshot(destination, [], project_root=tmp_path) == []
    assert list(destination.glob("*.json")) == []


@pytest.mark.parametrize("jobs", [
    [job("new"), job("broken") | {"unexpected": object()}],
    [job("new"), {"job_id": "missing_fields"}],
    [job("same"), job("same")],
    [job("../outside")],
])
def test_invalid_or_unserializable_snapshot_keeps_previous_data(tmp_path, jobs):
    destination = previous_snapshot(tmp_path)
    original = (destination / "old.json").read_bytes()
    with pytest.raises((TypeError, ValueError)):
        snapshots.save_job_snapshot(destination, jobs, project_root=tmp_path)
    assert (destination / "old.json").read_bytes() == original
    assert list(destination.glob("*.json")) == [destination / "old.json"]


def test_publish_failure_restores_previous_directory(tmp_path, monkeypatch):
    destination = previous_snapshot(tmp_path)
    original_replace = snapshots.os.replace

    def fail_publish(source, target):
        if Path(source).name == "new":
            # Staging must never appear inside the recursively loaded corpus.
            assert not Path(source).is_relative_to(tmp_path / "data/processed/jobs")
            raise OSError("disk write failed")
        original_replace(source, target)

    monkeypatch.setattr(snapshots.os, "replace", fail_publish)
    with pytest.raises(OSError, match="disk write failed"):
        snapshots.save_job_snapshot(destination, [job("new")], project_root=tmp_path)
    assert (destination / "old.json").exists()
    assert not (destination / "new.json").exists()
    assert not list((tmp_path / "data").glob(".job-snapshot-*"))


def test_failed_rollback_preserves_backup_for_recovery(tmp_path, monkeypatch):
    destination = previous_snapshot(tmp_path)
    original_replace = snapshots.os.replace

    def fail_after_backup(source, target):
        if Path(source).name in {"new", "previous"}:
            raise OSError("unavailable destination")
        original_replace(source, target)

    monkeypatch.setattr(snapshots.os, "replace", fail_after_backup)
    with pytest.raises(RuntimeError, match="previous data is preserved"):
        snapshots.save_job_snapshot(destination, [job("new")], project_root=tmp_path)
    backups = list((tmp_path / "data").glob(".job-snapshot-*/previous/old.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text())["job_id"] == "old"


@pytest.mark.parametrize("module,normalizer,saver,provider", [
    (greenhouse, "normalize_greenhouse_job", "save_processed_greenhouse_jobs", "greenhouse"),
    (lever, "normalize_lever_posting", "save_processed_lever_postings", "lever"),
])
def test_normalization_failure_does_not_touch_previous_snapshot(tmp_path, monkeypatch, module, normalizer, saver, provider):
    destination = tmp_path / "data/processed/jobs" / provider / "example"
    destination.mkdir(parents=True)
    (destination / "old.json").write_text("previous data", encoding="utf-8")

    def fail_normalization(*args, **kwargs):
        raise ValueError("invalid source")

    monkeypatch.setattr(module, normalizer, fail_normalization)
    with pytest.raises(ValueError, match="invalid source"):
        getattr(module, saver)("example", [{}], project_root=tmp_path)
    assert (destination / "old.json").read_text() == "previous data"


def test_snapshot_target_must_stay_in_source_directory(tmp_path):
    with pytest.raises(ValueError):
        snapshots.save_job_snapshot(tmp_path / "outside", [], project_root=tmp_path)
    assert not (tmp_path / "outside").exists()
