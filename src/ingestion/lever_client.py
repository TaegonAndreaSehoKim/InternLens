from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional

import httpx

LEVER_POSTINGS_BASE_URL = "https://api.lever.co/v0/postings"

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


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

