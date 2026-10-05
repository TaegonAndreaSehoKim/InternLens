from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from src.preprocessing.job_parser import load_job_posting


def save_job_snapshot(output_dir: Path, jobs: list[dict[str, Any]], *, project_root: Path) -> list[Path]:
    """Stage and validate a source snapshot, then publish it with rollback."""
    data_root = (project_root / "data").resolve()
    jobs_root = (data_root / "processed" / "jobs").resolve()
    destination = output_dir.resolve()
    relative = destination.relative_to(jobs_root)
    if len(relative.parts) != 2:
        raise ValueError("A snapshot must target a provider/source directory within data/processed/jobs.")

    data_root.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=".job-snapshot-", dir=data_root)).resolve()
    workspace.relative_to(data_root)  # Verify the cleanup target before any recursive removal.
    staged = workspace / "new"
    backup = workspace / "previous"
    staged.mkdir()
    filenames: list[str] = []
    published = False
    try:
        for job in jobs:
            job_id = str(job.get("job_id", ""))
            if not re.fullmatch(r"[A-Za-z0-9_-]+", job_id):
                raise ValueError(f"Invalid job_id for a snapshot file: {job_id!r}")
            filename = f"{job_id}.json"
            if filename in filenames:
                raise ValueError(f"Duplicate job_id in snapshot: {job_id}")
            with (staged / filename).open("w", encoding="utf-8") as handle:
                json.dump(job, handle, indent=2, ensure_ascii=False, allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            load_job_posting(staged / filename)
            filenames.append(filename)

        # Older refreshes removed only direct JSON files. Preserve other content.
        if destination.exists():
            for entry in destination.iterdir():
                if entry.is_file() and entry.suffix == ".json":
                    continue
                target = staged / entry.name
                if entry.is_dir():
                    shutil.copytree(entry, target)
                else:
                    shutil.copy2(entry, target)

        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            os.replace(destination, backup)
        try:
            os.replace(staged, destination)
        except OSError as publish_error:
            if backup.exists():
                try:
                    os.replace(backup, destination)
                except OSError as rollback_error:
                    raise RuntimeError(
                        f"Snapshot publication and rollback failed; previous data is preserved at {backup}"
                    ) from rollback_error
            raise publish_error
        published = True
        return [output_dir / filename for filename in filenames]
    finally:
        # A failed rollback keeps its backup for recovery. Staging/backup JSON is
        # outside the loader's corpus tree and cannot appear as duplicate jobs.
        if published or not backup.exists():
            shutil.rmtree(workspace)
