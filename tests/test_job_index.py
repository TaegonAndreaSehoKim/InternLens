from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import src.storage.job_index as indexed
from src.ingestion.snapshot_store import save_job_snapshot
from src.preprocessing.job_parser import REQUIRED_JOB_FIELDS


def write_job(path: Path, job_id="one", title="Engineering Intern", **fields):
    payload = {field: "" for field in REQUIRED_JOB_FIELDS} | {"job_id": job_id, "title": title} | fields
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_repeated_detail_lookups_parse_once_and_return_independent_copies(tmp_path, monkeypatch):
    write_job(tmp_path / "one.json")
    loader = Mock(wraps=indexed.load_all_job_postings)
    monkeypatch.setattr(indexed, "load_all_job_postings", loader)
    index = indexed.JobIndex()
    first = index.get(tmp_path, "one")
    first["title"] = "caller changed this"
    assert index.get(tmp_path, "one")["title"] == "Engineering Intern"
    assert index.get(tmp_path, "missing") is None
    assert loader.call_count == 1


def test_index_rebuilds_for_edits_additions_and_deletions(tmp_path, monkeypatch):
    write_job(tmp_path / "one.json")
    loader = Mock(wraps=indexed.load_all_job_postings)
    monkeypatch.setattr(indexed, "load_all_job_postings", loader)
    index = indexed.JobIndex()
    index.get(tmp_path, "one")
    write_job(tmp_path / "one.json", title="Updated Engineering Intern")
    assert index.get(tmp_path, "one")["title"] == "Updated Engineering Intern"
    write_job(tmp_path / "two.json", job_id="two")
    assert index.get(tmp_path, "two")["job_id"] == "two"
    (tmp_path / "one.json").unlink()
    assert index.get(tmp_path, "one") is None
    assert loader.call_count == 4


def test_index_preserves_expired_detail_and_canonical_duplicate_rules(tmp_path):
    write_job(tmp_path / "legacy.json", title="Legacy Intern")
    write_job(tmp_path / "lever/site/one.json", title="Canonical Intern", expires_at="2020-01-01T00:00:00Z")
    # Different IDs with the same title must remain directly addressable.
    write_job(tmp_path / "lever/site/two.json", job_id="two", title="Canonical Intern")
    index = indexed.JobIndex()
    assert index.get(tmp_path, "one")["title"] == "Canonical Intern"
    assert index.get(tmp_path, "two")["job_id"] == "two"


def test_recoverable_snapshot_publication_invalidates_detail_cache(tmp_path):
    destination = tmp_path / "data/processed/jobs/manual/example"
    write_job(destination / "one.json")
    index = indexed.JobIndex()
    assert index.get(destination.parent.parent, "one")["title"] == "Engineering Intern"
    payload = {field: "" for field in REQUIRED_JOB_FIELDS} | {"job_id": "new", "title": "New Intern"}
    save_job_snapshot(destination, [payload], project_root=tmp_path)
    assert index.get(destination.parent.parent, "one") is None
    assert index.get(destination.parent.parent, "new")["title"] == "New Intern"


def test_changing_corpus_during_load_retries_before_publishing_cache(tmp_path, monkeypatch):
    write_job(tmp_path / "one.json")
    original = indexed.load_all_job_postings
    calls = 0

    def changing_loader(*args, **kwargs):
        nonlocal calls
        jobs = original(*args, **kwargs)
        calls += 1
        if calls == 1:
            write_job(tmp_path / "one.json", title="Newly Refreshed Intern")
        return jobs

    monkeypatch.setattr(indexed, "load_all_job_postings", changing_loader)
    assert indexed.JobIndex().get(tmp_path, "one")["title"] == "Newly Refreshed Intern"
    assert calls == 2


def test_invalid_changed_corpus_is_not_hidden_by_a_warm_cache(tmp_path):
    write_job(tmp_path / "one.json")
    index = indexed.JobIndex()
    index.get(tmp_path, "one")
    (tmp_path / "one.json").write_text("{}")
    with pytest.raises(ValueError, match="Missing required"):
        index.get(tmp_path, "one")


def test_index_is_bounded_and_scoped_by_corpus_path(tmp_path, monkeypatch):
    write_job(tmp_path / "a/one.json", title="A Intern")
    write_job(tmp_path / "b/one.json", title="B Intern")
    loader = Mock(wraps=indexed.load_all_job_postings)
    monkeypatch.setattr(indexed, "load_all_job_postings", loader)
    index = indexed.JobIndex(max_corpora=1)
    assert index.get(tmp_path / "a", "one")["title"] == "A Intern"
    assert index.get(tmp_path / "b", "one")["title"] == "B Intern"
    assert index.get(tmp_path / "a", "one")["title"] == "A Intern"
    assert loader.call_count == 3
