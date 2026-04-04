from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence
from urllib.parse import urljoin, urlparse

import httpx


LEVER_HOST = "jobs.lever.co"
GREENHOUSE_HOSTS = {"boards.greenhouse.io", "job-boards.greenhouse.io"}

HREF_PATTERN = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
LEVER_URL_PATTERN = re.compile(
    r"https?://jobs\.lever\.co/[A-Za-z0-9_-]+(?:/[^\s\"'<>]*)?",
    re.IGNORECASE,
)
GREENHOUSE_URL_PATTERN = re.compile(
    r"https?://(?:boards|job-boards)\.greenhouse\.io/[A-Za-z0-9_-]+(?:/[^\s\"'<>]*)?",
    re.IGNORECASE,
)

DISCOVERED_SOURCE_SORT_FIELDS = ("company", "source_type", "source_identifier")
PRESERVED_EXISTING_FIELDS = (
    "discovered_at",
    "status",
    "validation_notes",
    "source_score",
    "internship_likelihood",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_html(url: str, timeout: float) -> str:
    response = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "InternLens-Discovery/0.1"},
    )
    response.raise_for_status()
    return response.text


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON list in {path}")

    return [item for item in payload if isinstance(item, dict)]


def save_json_list(path: Path, payload: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(list(payload), handle, indent=2)
        handle.write("\n")


def resolve_seed_path(requested_path: Path) -> Path:
    if requested_path.exists():
        return requested_path

    example_path = requested_path.with_name(f"{requested_path.stem}.example{requested_path.suffix}")
    if example_path.exists():
        return example_path

    raise FileNotFoundError(f"Seed file not found: {requested_path}")


def classify_source_url(url: str) -> Dict[str, str] | None:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if not path_parts:
        return None

    if host == LEVER_HOST:
        return {
            "source_type": "lever",
            "source_identifier": path_parts[0],
        }

    if host in GREENHOUSE_HOSTS:
        return {
            "source_type": "greenhouse",
            "source_identifier": path_parts[0],
        }

    return None


def extract_candidate_urls(html: str, base_url: str) -> List[str]:
    candidates: List[str] = []
    seen: set[str] = set()

    for match in HREF_PATTERN.findall(html):
        resolved = urljoin(base_url, match.strip())
        if resolved not in seen:
            seen.add(resolved)
            candidates.append(resolved)

    for pattern in (LEVER_URL_PATTERN, GREENHOUSE_URL_PATTERN):
        for match in pattern.findall(html):
            normalized = match.strip()
            if normalized not in seen:
                seen.add(normalized)
                candidates.append(normalized)

    return candidates


def _seed_scan_urls(seed: Dict[str, Any]) -> Iterable[tuple[str, str]]:
    seen: set[str] = set()

    careers_url = str(seed.get("careers_url", "")).strip()
    homepage_url = str(seed.get("homepage_url", "")).strip()

    if careers_url and careers_url not in seen:
        seen.add(careers_url)
        yield careers_url, "careers_page_scan"

    if homepage_url and homepage_url not in seen:
        seen.add(homepage_url)
        yield homepage_url, "homepage_scan"


def _build_candidate_record(
    *,
    seed: Dict[str, Any],
    source_type: str,
    source_identifier: str,
    discovery_url: str,
    discovery_method: str,
    discovered_at: str,
) -> Dict[str, Any]:
    careers_url = str(seed.get("careers_url", "")).strip() or discovery_url
    return {
        "company": str(seed.get("company", "")).strip(),
        "source_type": source_type,
        "source_identifier": source_identifier,
        "careers_url": careers_url,
        "discovery_url": discovery_url,
        "discovered_at": discovered_at,
        "discovery_method": discovery_method,
        "status": "candidate",
        "validation_notes": "",
        "source_score": 0.0,
        "internship_likelihood": 0.0,
    }


def discover_sources_from_seed(
    seed: Dict[str, Any],
    *,
    timeout: float,
    fetch_html_fn: Callable[[str, float], str],
    discovered_at: str,
) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    seen_source_keys: set[tuple[str, str]] = set()

    for page_url, scan_method in _seed_scan_urls(seed):
        direct_source = classify_source_url(page_url)
        if direct_source is not None:
            source_key = (
                direct_source["source_type"],
                direct_source["source_identifier"],
            )
            if source_key not in seen_source_keys:
                seen_source_keys.add(source_key)
                candidates.append(
                    _build_candidate_record(
                        seed=seed,
                        source_type=direct_source["source_type"],
                        source_identifier=direct_source["source_identifier"],
                        discovery_url=page_url,
                        discovery_method="direct_seed_url",
                        discovered_at=discovered_at,
                    )
                )

        html = fetch_html_fn(page_url, timeout)
        for candidate_url in extract_candidate_urls(html, page_url):
            source = classify_source_url(candidate_url)
            if source is None:
                continue

            source_key = (source["source_type"], source["source_identifier"])
            if source_key in seen_source_keys:
                continue

            seen_source_keys.add(source_key)
            candidates.append(
                _build_candidate_record(
                    seed=seed,
                    source_type=source["source_type"],
                    source_identifier=source["source_identifier"],
                    discovery_url=candidate_url,
                    discovery_method=scan_method,
                    discovered_at=discovered_at,
                )
            )

    return candidates


def merge_discovered_sources(
    existing: Sequence[Dict[str, Any]],
    discovered: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged: Dict[tuple[str, str], Dict[str, Any]] = {}

    for record in existing:
        key = (
            str(record.get("source_type", "")).strip(),
            str(record.get("source_identifier", "")).strip(),
        )
        if not all(key):
            continue
        merged[key] = dict(record)

    for record in discovered:
        key = (
            str(record.get("source_type", "")).strip(),
            str(record.get("source_identifier", "")).strip(),
        )
        if not all(key):
            continue

        if key not in merged:
            merged[key] = dict(record)
            continue

        updated = dict(record)
        existing_record = merged[key]
        for field in PRESERVED_EXISTING_FIELDS:
            if field in existing_record and existing_record[field] is not None and existing_record[field] != "":
                updated[field] = existing_record[field]
        merged[key] = updated

    return sorted(
        merged.values(),
        key=lambda item: tuple(str(item.get(field, "")).lower() for field in DISCOVERED_SOURCE_SORT_FIELDS),
    )


def discover_sources(
    seeds: Sequence[Dict[str, Any]],
    *,
    timeout: float,
    fetch_html_fn: Callable[[str, float], str] = fetch_html,
    discovered_at: str | None = None,
) -> tuple[List[Dict[str, Any]], List[str]]:
    records: List[Dict[str, Any]] = []
    errors: List[str] = []
    discovered_at_value = discovered_at or utc_now_iso()

    for seed in seeds:
        company = str(seed.get("company", "")).strip() or "<unknown>"
        try:
            records.extend(
                discover_sources_from_seed(
                    seed,
                    timeout=timeout,
                    fetch_html_fn=fetch_html_fn,
                    discovered_at=discovered_at_value,
                )
            )
        except Exception as exc:
            errors.append(f"{company}: {exc}")

    return merge_discovered_sources([], records), errors
