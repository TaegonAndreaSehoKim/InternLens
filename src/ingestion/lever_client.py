from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional
from pathlib import Path

import httpx

LEVER_POSTINGS_BASE_URL = "https://api.lever.co/v0/postings"

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()

def _utc_filename_timestamp() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def save_raw_lever_snapshot(
    site_name: str,
    postings: List[Dict[str, Any]],
    *,
    project_root: Path,
) -> Path:
    output_dir = project_root / "data" / "raw" / "lever" / site_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"jobs_{_utc_filename_timestamp()}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(postings, f, indent=2, ensure_ascii=False)

    return output_path

def _normalize_whitespace(text: str) -> str:
    return " ".join(text.strip().split())


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return _normalize_whitespace(str(value))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return slug.strip("_")


def _build_request_url(site_name: str) -> str:
    normalized_site = site_name.strip()
    return f"{LEVER_POSTINGS_BASE_URL}/{normalized_site}?mode=json"

def _extract_posting_date(created_at_ms: Any) -> str:
    # Convert Lever millisecond timestamp into YYYY-MM-DD.
    if created_at_ms in (None, ""):
        return ""

    try:
        timestamp_ms = int(created_at_ms)
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


def _extract_categories(posting: Dict[str, Any]) -> Dict[str, Any]:
    # Safely return the categories object when present.
    categories = posting.get("categories", {})
    if isinstance(categories, dict):
        return categories
    return {}

def normalize_lever_posting(
    posting: Dict[str, Any],
    site_name: str,
) -> Dict[str, Any]:
    # Normalize one Lever posting into the current InternLens processed schema.
    categories = _extract_categories(posting)

    source_job_id = _coerce_text(posting.get("id", ""))
    title = _coerce_text(posting.get("text", ""))
    company = _coerce_text(categories.get("department", "")) or site_name.strip()
    location = _coerce_text(categories.get("location", "")) or _coerce_text(posting.get("country", ""))
    description = _coerce_text(posting.get("descriptionPlain", "")) or _coerce_text(
        posting.get("descriptionBodyPlain", "")
    )
    employment_type = _coerce_text(categories.get("commitment", ""))
    remote_status = _coerce_text(posting.get("workplaceType", "")).lower()
    posting_date = _extract_posting_date(posting.get("createdAt"))
    source_url = _coerce_text(posting.get("hostedUrl", ""))
    application_url = _coerce_text(posting.get("applyUrl", ""))

    return {
        "job_id": f"lever_{_slugify(site_name)}_{source_job_id}",
        "source": "lever",
        "source_site": site_name.strip(),
        "source_job_id": source_job_id,
        "company": company,
        "title": title,
        "location": location,
        "description": description,
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": posting_date,
        "sponsorship_info": "",
        "employment_type": employment_type,
        "source_url": source_url,
        "application_url": application_url,
        "remote_status": remote_status,
        "team": _coerce_text(categories.get("team", "")),
    }

def save_processed_lever_postings(
    site_name: str,
    postings: List[Dict[str, Any]],
    *,
    project_root: Path,
) -> List[Path]:
    # Normalize each Lever posting and save it as one processed JSON file.
    output_dir = project_root / "data" / "processed" / "jobs"
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[Path] = []

    for posting in postings:
        normalized = normalize_lever_posting(posting, site_name)
        output_path = output_dir / f"{normalized['job_id']}.json"

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, ensure_ascii=False)

        saved_paths.append(output_path)

    return saved_paths

def fetch_lever_postings(
    site_name: str,
    *,
    timeout: float = 60.0,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    request_url = _build_request_url(site_name)

    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={
                "Accept": "application/json",
                "User-Agent": "InternLens/0.1",
            },
            follow_redirects=True,
        ) as client:
            response = client.get(request_url)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"Lever request timed out for site '{site_name}'. "
            f"Try a larger timeout or verify the site name."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Lever request failed for site '{site_name}' "
            f"with status {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Lever request failed for site '{site_name}': {exc}"
        ) from exc

    if not isinstance(payload, list):
        raise ValueError("Lever postings API returned a non-list payload.")

    postings: List[Dict[str, Any]] = [item for item in payload if isinstance(item, dict)]

    if limit is not None:
        postings = postings[:limit]

    return postings

