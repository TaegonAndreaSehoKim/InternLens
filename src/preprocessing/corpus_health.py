from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.api.settings import resolve_project_path
from src.preprocessing.job_parser import load_all_job_postings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_corpus_health_report(
    jobs_dir: str | Path,
    *,
    project_root: Path = PROJECT_ROOT,
    min_active_jobs: int = 1,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Use the same expiry and duplicate rules as recommendations."""
    if min_active_jobs < 0:
        raise ValueError("--min-active-jobs must be greater than or equal to 0.")
    resolved_jobs_dir = resolve_project_path(project_root, jobs_dir)
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    current_time = current_time.astimezone(timezone.utc)

    def load(include_expired: bool) -> list[dict[str, Any]]:
        try:
            return load_all_job_postings(resolved_jobs_dir, include_expired=include_expired, now=current_time)
        except ValueError as error:
            # Empty or expired data is a normal unavailable state; malformed data
            # must fail the check rather than accidentally passing a low threshold.
            if str(error).startswith(("No active job posting JSON files", "No job posting JSON files")):
                return []
            raise

    error = None
    try:
        all_jobs = load(True)
        active_jobs = load(False)
    except (OSError, ValueError) as exc:
        all_jobs, active_jobs = [], []
        error = str(exc)

    def latest(field: str) -> str | None:
        values = [str(job.get(field) or "").strip() for job in all_jobs]
        return max((value for value in values if value), default=None)

    return {
        "jobs_dir": str(resolved_jobs_dir),
        "checked_at": current_time.isoformat(),
        "min_active_jobs": min_active_jobs,
        "active_job_count": len(active_jobs),
        "all_job_count": len(all_jobs),
        "expired_or_filtered_job_count": max(len(all_jobs) - len(active_jobs), 0),
        "latest_fetched_at": latest("fetched_at"),
        "latest_expires_at": latest("expires_at"),
        "ok": error is None and len(active_jobs) >= min_active_jobs,
        "error": error,
    }
