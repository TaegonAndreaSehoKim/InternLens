from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx


LEVER_POSTINGS_BASE_URL = "https://api.lever.co/v0/postings"


def _utc_now() -> datetime:
    # Return the current UTC datetime.
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    # Return the current UTC timestamp in ISO format.
    return _utc_now().isoformat()


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
    # Convert basic HTML content into plain text.
    if value is None:
        return ""

    text = str(value)
    text = unescape(text)
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


def _build_request_url(site_name: str) -> str:
    # Build the Lever postings API URL for one site.
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


def _normalize_heading(text: str) -> str:
    # Normalize headings so marker detection is more robust.
    return _coerce_text(text).lower().replace("’", "'").rstrip(":")


def _split_plain_lines(text: str) -> List[str]:
    # Split a plain-text block into cleaned logical lines.
    # Also normalize escaped newline sequences such as "\\n" into real newlines.
    normalized_text = str(text).replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")

    lines: List[str] = []

    for raw_line in normalized_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line = re.sub(r"^[\\-•*]+\\s*", "", line)
        line = _normalize_whitespace(line)
        if line:
            lines.append(line)

    return lines


def _extract_section_text(list_item: Dict[str, Any]) -> str:
    # Extract plain text from one Lever list section.
    plain_candidates = [
        list_item.get("contentPlain"),
        list_item.get("plainText"),
        list_item.get("content"),
    ]

    for candidate in plain_candidates:
        text = _strip_html(candidate)
        if text:
            return text

    return ""


def _extract_qualification_sections_from_lists(posting: Dict[str, Any]) -> Tuple[str, str]:
    # Extract qualification sections from Lever structured list blocks when present.
    required_keywords = [
        "requirements",
        "qualifications",
        "minimum qualifications",
        "basic qualifications",
        "what we're looking for",
        "what we are looking for",
        "must have",
    ]
    preferred_keywords = [
        "preferred qualifications",
        "preferred",
        "nice to have",
        "bonus",
        "bonus points",
        "pluses",
    ]

    required_sections: List[str] = []
    preferred_sections: List[str] = []

    raw_lists = posting.get("lists", [])
    if not isinstance(raw_lists, list):
        raw_lists = []

    for item in raw_lists:
        if not isinstance(item, dict):
            continue

        heading = _normalize_heading(item.get("text", ""))
        content = _extract_section_text(item)
        if not content:
            continue

        if any(keyword in heading for keyword in preferred_keywords):
            preferred_sections.append(content)
        elif any(keyword in heading for keyword in required_keywords):
            required_sections.append(content)

    return "\\n\\n".join(required_sections), "\\n\\n".join(preferred_sections)


def _extract_qualification_sections_from_description(posting: Dict[str, Any]) -> Tuple[str, str]:
    # Fallback extraction for postings that embed qualification bullets inside description text.
    # Important: do not collapse newlines before parsing, or section boundaries disappear.
    raw_text = posting.get("descriptionPlain")
    if raw_text in (None, ""):
        raw_text = posting.get("descriptionBodyPlain", "")

    plain_text = str(raw_text or "")
    if not plain_text.strip():
        return "", ""

    lines = _split_plain_lines(plain_text)
    if not lines:
        return "", ""

    start_markers = [
        "what we're looking for",
        "what we are looking for",
        "qualifications",
        "requirements",
        "minimum qualifications",
        "basic qualifications",
    ]
    stop_markers = [
        "what we offer",
        "how to apply",
        "benefits",
        "about us",
    ]
    preferred_markers = [
        "preferred",
        "nice to have",
        "bonus",
    ]

    start_index: Optional[int] = None
    for index, line in enumerate(lines):
        heading = _normalize_heading(line)
        if heading in start_markers:
            start_index = index + 1
            break

    if start_index is None:
        return "", ""

    required_lines: List[str] = []
    preferred_lines: List[str] = []

    for line in lines[start_index:]:
        heading = _normalize_heading(line)

        if heading in stop_markers:
            break

        if line.startswith("#"):
            break

        if any(marker in heading for marker in preferred_markers):
            preferred_lines.append(line)
        else:
            required_lines.append(line)

    return "\n".join(required_lines), "\n".join(preferred_lines)


def _extract_qualification_sections(posting: Dict[str, Any]) -> Tuple[str, str]:
    # Prefer structured Lever list sections, then fall back to description parsing.
    min_qualifications, preferred_qualifications = _extract_qualification_sections_from_lists(posting)

    if min_qualifications or preferred_qualifications:
        return min_qualifications, preferred_qualifications

    return _extract_qualification_sections_from_description(posting)


def fetch_lever_postings(
    site_name: str,
    *,
    timeout: float = 60.0,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    # Fetch published Lever postings for a single site.
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
            f"Lever request timed out for site '{site_name}'. Try a larger timeout or verify the site name."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Lever request failed for site '{site_name}' with status {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Lever request failed for site '{site_name}': {exc}") from exc

    if not isinstance(payload, list):
        raise ValueError("Lever postings API returned a non-list payload.")

    postings: List[Dict[str, Any]] = [item for item in payload if isinstance(item, dict)]

    if limit is not None:
        postings = postings[:limit]

    return postings


def _hash_payload(payload: Dict[str, Any]) -> str:
    # Create a stable hash for one raw source payload.
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def save_raw_lever_snapshot(
    site_name: str,
    postings: List[Dict[str, Any]],
    *,
    project_root: Path,
) -> Path:
    # Save the fetched Lever postings as one raw JSON snapshot.
    output_dir = project_root / "data" / "raw" / "lever" / site_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"jobs_{_utc_filename_timestamp()}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(postings, f, indent=2, ensure_ascii=False)

    return output_path


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
    min_qualifications, preferred_qualifications = _extract_qualification_sections(posting)
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
        "min_qualifications": min_qualifications,
        "preferred_qualifications": preferred_qualifications,
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
    # Normalize each Lever posting and save it under a source/site-specific folder.
    output_dir = project_root / "data" / "processed" / "jobs" / "lever" / site_name
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[Path] = []

    for posting in postings:
        normalized = normalize_lever_posting(posting, site_name)
        output_path = output_dir / f"{normalized['job_id']}.json"

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, ensure_ascii=False)

        saved_paths.append(output_path)

    return saved_paths