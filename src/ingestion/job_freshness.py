from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict


DEFAULT_JOB_FRESHNESS_DAYS = 7


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def build_freshness_fields(
    *,
    fetched_at: datetime | None = None,
    freshness_days: int = DEFAULT_JOB_FRESHNESS_DAYS,
) -> Dict[str, Any]:
    fetched_dt = fetched_at or utc_now()
    expires_dt = fetched_dt + timedelta(days=freshness_days)
    return {
        "fetched_at": utc_iso(fetched_dt),
        "expires_at": utc_iso(expires_dt),
        "freshness_days": freshness_days,
    }
