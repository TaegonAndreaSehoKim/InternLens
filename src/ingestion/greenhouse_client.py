from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


GREENHOUSE_JOBS_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


def _utc_now() -> datetime:
    # Return the current UTC datetime.
    return datetime.now(timezone.utc)


def _utc_filename_timestamp() -> str:
    # Format a UTC datetime for stable file names.
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _normalize_whitespace(text: str) -> str:
    # Collapse repeated whitespace while preserving readable text.
    return " ".join(text.strip().split())


def _coerce_text(value: Any) -> str:
    # Safely convert a value into a plain string.
    if value is None:
        return ""
    return _normalize_whitespace(str(value))


def _strip_html(value: Any) -> str:
    # Convert Greenhouse HTML content into plain text.
    if value is None:
        return ""

    text = unescape(str(value))
    text = re.sub(r"<br\\s*/?>", "\\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\\s*>", "\\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\\s*>", "\\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li\\s*>", "- ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\n{3,}", "\\n\\n", text)
    return _normalize_whitespace(text.replace("\\r", "\\n"))


def _slugify(value: str) -> str:
    # Create a filesystem-safe identifier fragment.
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return slug.strip("_")


def _build_jobs_url(board_token: str, *, content: bool = True) -> str:
    # Build the Greenhouse jobs list URL for one board token.
    token = board_token.strip()
    url = f"{GREENHOUSE_JOBS_BASE_URL}/{token}/jobs"
    if content:
        url += "?content=true"
    return url


def _extract_posting_date(updated_at: Any) -> str:
    # Convert Greenhouse updated_at into YYYY-MM-DD when possible.
    if updated_at in (None, ""):
        return ""

    text = str(updated_at).strip()

    try:
        # Support timestamps ending with Z as well as timezone offsets.
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except ValueError:
        return ""


def _extract_location(job: Dict[str, Any]) -> str:
    # Prefer the top-level location name, then fall back to offices.
    location = job.get("location", {})
    if isinstance(location, dict):
        location_name = _coerce_text(location.get("name", ""))
        if location_name:
            return location_name

    offices = job.get("offices", [])
    if isinstance(offices, list) and offices:
        office = offices[-1]
        if isinstance(office, dict):
            office_location = _coerce_text(office.get("location", ""))
            if office_location:
                return office_location
            office_name = _coerce_text(office.get("name", ""))
            if office_name:
                return office_name

    return ""

def _extract_team(job: Dict[str, Any]) -> str:
    # Join department names into one readable team string.
    departments = job.get("departments", [])
    if not isinstance(departments, list):
        return ""

    names: List[str] = []
    for department in departments:
        if not isinstance(department, dict):
            continue
        name = _coerce_text(department.get("name", ""))
        if name:
            names.append(name)

    return " | ".join(names)


def _infer_remote_status(location: str, description: str, title: str) -> str:
    # Infer remote status conservatively.
    # Do not scan the full description because many postings include boilerplate
    # that mentions remote work policies unrelated to the actual role location.
    location_text = location.lower()
    title_text = title.lower()
    combined = f"{location_text} {title_text}"

    if "in-office" in location_text or "in office" in location_text:
        return "onsite"
    if "on-site" in location_text or "onsite" in location_text:
        return "onsite"
    if "hybrid" in combined:
        return "hybrid"
    if "remote" in combined:
        return "remote"
    if location:
        return "onsite"
    return ""


def fetch_greenhouse_jobs(
    board_token: str,
    *,
    timeout: float = 60.0,
    limit: Optional[int] = None,
    content: bool = True,
) -> List[Dict[str, Any]]:
    # Fetch published Greenhouse jobs for one board token.
    request_url = _build_jobs_url(board_token, content=content)

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
            f"Greenhouse request timed out for board '{board_token}'. Try a larger timeout or verify the board token."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Greenhouse request failed for board '{board_token}' with status {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Greenhouse request failed for board '{board_token}': {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Greenhouse jobs API returned a non-object payload.")

    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("Greenhouse jobs API returned a non-list jobs field.")

    normalized_jobs: List[Dict[str, Any]] = [item for item in jobs if isinstance(item, dict)]

    if limit is not None:
        normalized_jobs = normalized_jobs[:limit]

    return normalized_jobs


def save_raw_greenhouse_snapshot(
    board_token: str,
    jobs: List[Dict[str, Any]],
    *,
    project_root: Path,
) -> Path:
    # Save fetched Greenhouse jobs as one raw JSON snapshot.
    output_dir = project_root / "data" / "raw" / "greenhouse" / board_token
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"jobs_{_utc_filename_timestamp()}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

    return output_path


def normalize_greenhouse_job(
    job: Dict[str, Any],
    board_token: str,
) -> Dict[str, Any]:
    # Normalize one Greenhouse job into the current InternLens processed schema.
    source_job_id = _coerce_text(job.get("id", ""))
    title = _coerce_text(job.get("title", ""))
    location = _extract_location(job)
    description = _strip_html(job.get("content", ""))
    posting_date = _extract_posting_date(job.get("updated_at"))
    source_url = _coerce_text(job.get("absolute_url", ""))
    team = _extract_team(job)
    remote_status = _infer_remote_status(location, description, title)

    return {
        "job_id": f"greenhouse_{_slugify(board_token)}_{source_job_id}",
        "source": "greenhouse",
        "source_site": board_token.strip(),
        "source_job_id": source_job_id,
        "company": board_token.strip(),
        "title": title,
        "location": location,
        "description": description,
        "min_qualifications": "",
        "preferred_qualifications": "",
        "posting_date": posting_date,
        "sponsorship_info": "",
        "employment_type": "",
        "source_url": source_url,
        "application_url": source_url,
        "remote_status": remote_status,
        "team": team,
    }


def save_processed_greenhouse_jobs(
    board_token: str,
    jobs: List[Dict[str, Any]],
    *,
    project_root: Path,
) -> List[Path]:
    # Normalize each Greenhouse job and save it under a source/site-specific folder.
    output_dir = project_root / "data" / "processed" / "jobs" / "greenhouse" / board_token
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[Path] = []

    for job in jobs:
        normalized = normalize_greenhouse_job(job, board_token)
        output_path = output_dir / f"{normalized['job_id']}.json"

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, ensure_ascii=False)

        saved_paths.append(output_path)

    return saved_paths