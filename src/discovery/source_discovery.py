from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence
from urllib.parse import unquote, urljoin, urlparse

import httpx

from src.ingestion.greenhouse_client import fetch_greenhouse_jobs
from src.ingestion.lever_client import fetch_lever_postings


LEVER_HOST = "jobs.lever.co"
GREENHOUSE_HOSTS = {"boards.greenhouse.io", "job-boards.greenhouse.io"}
LEVER_NON_BOARD_PATHS = {"api", "embed"}
GREENHOUSE_NON_BOARD_PATHS = {"api", "embed", "job_app", "job_board"}
BLOCKED_REVIEW_REASONS = {"http_403", "http_406", "http_429"}
HIGH_VALUE_FOLLOW_KEYWORDS = (
    "intern",
    "internship",
    "student",
    "students",
    "university",
    "early-career",
    "early-careers",
    "earlycareer",
    "earlycareers",
    "campus",
    "graduate",
    "graduates",
    "new-grad",
    "newgrad",
)
GENERAL_FOLLOW_KEYWORDS = (
    "career",
    "careers",
    "job",
    "jobs",
)
PRIORITY_FOLLOW_KEYWORDS = HIGH_VALUE_FOLLOW_KEYWORDS + GENERAL_FOLLOW_KEYWORDS
IGNORED_FOLLOW_EXTENSIONS = (
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".pdf",
    ".png",
    ".svg",
    ".webp",
)

HREF_PATTERN = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
INLINE_HTTP_URL_PATTERN = re.compile(r"""https?://[^\s"'<>\\)]+""", re.IGNORECASE)
QUOTED_PATH_PATTERN = re.compile(r"""["'](/[A-Za-z0-9][^"']*)["']""")
SOURCE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
TRAILING_URL_PUNCTUATION = ".,;:)]}"
COMPANY_SUFFIX_WORDS = {
    "ai",
    "inc",
    "labs",
    "technologies",
    "technology",
    "group",
    "systems",
}
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
    "last_validated_at",
    "last_promoted_at",
    "status",
    "validation_notes",
    "source_score",
    "internship_likelihood",
    "internship_signal_examples",
)
DiscoveryWarning = Dict[str, str]


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


def _warning_reason_for_exception(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"http_{exc.response.status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.NetworkError):
        return "network_error"
    return "fetch_error"


def build_discovery_warning(
    *,
    company: str,
    url: str,
    reason: str,
    message: str,
) -> DiscoveryWarning:
    return {
        "company": company,
        "url": url,
        "reason": reason,
        "message": message,
    }


def build_fetch_warning(company: str, url: str, exc: Exception) -> DiscoveryWarning:
    return build_discovery_warning(
        company=company,
        url=url,
        reason=_warning_reason_for_exception(exc),
        message=str(exc),
    )


def build_direct_probe_warning(
    company: str,
    source_type: str,
    source_identifier: str,
    exc: Exception,
) -> DiscoveryWarning:
    if source_type == "lever":
        url = f"https://jobs.lever.co/{source_identifier}"
    else:
        url = f"https://boards.greenhouse.io/{source_identifier}"

    reason = "direct_probe_miss"
    if isinstance(exc, httpx.TimeoutException):
        reason = "direct_probe_timeout"
    elif isinstance(exc, httpx.NetworkError):
        reason = "direct_probe_network_error"

    return build_discovery_warning(
        company=company,
        url=url,
        reason=reason,
        message=str(exc),
    )


def format_discovery_warning(warning: DiscoveryWarning) -> str:
    company = warning.get("company", "<unknown>")
    url = warning.get("url", "")
    reason = warning.get("reason", "fetch_error")
    message = warning.get("message", "")

    if url:
        return f"{company}: failed to fetch {url} ({reason}): {message}"
    return f"{company}: {reason}: {message}"


def summarize_discovery_warnings(warnings: Sequence[DiscoveryWarning]) -> Dict[str, int]:
    counts = Counter(warning.get("reason", "unknown") for warning in warnings)
    return dict(sorted(counts.items()))


def summarize_discovery_methods(records: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(str(record.get("discovery_method", "unknown") or "unknown") for record in records)
    return dict(sorted(counts.items()))


def visible_discovery_warnings(warnings: Sequence[DiscoveryWarning]) -> List[DiscoveryWarning]:
    return [
        warning
        for warning in warnings
        if not warning.get("reason", "").startswith("direct_probe_")
    ]


def iter_seed_batches(
    seeds: Sequence[Dict[str, Any]],
    batch_size: int | None,
) -> Iterable[Sequence[Dict[str, Any]]]:
    if not seeds:
        return

    if batch_size is None or batch_size <= 0:
        yield seeds
        return

    for start_index in range(0, len(seeds), batch_size):
        yield seeds[start_index : start_index + batch_size]


def resolve_seed_path(requested_path: Path) -> Path:
    if requested_path.exists():
        return requested_path

    example_path = requested_path.with_name(f"{requested_path.stem}.example{requested_path.suffix}")
    if example_path.exists():
        return example_path

    raise FileNotFoundError(f"Seed file not found: {requested_path}")


def _normalize_source_identifier(path_part: str) -> str | None:
    identifier = unquote(path_part).strip().rstrip(TRAILING_URL_PUNCTUATION)
    if not SOURCE_IDENTIFIER_PATTERN.fullmatch(identifier):
        return None
    return identifier


def classify_source_url(url: str) -> Dict[str, str] | None:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if not path_parts:
        return None

    source_identifier = _normalize_source_identifier(path_parts[0])
    if source_identifier is None:
        return None

    if host == LEVER_HOST:
        if source_identifier.lower() in LEVER_NON_BOARD_PATHS:
            return None

        return {
            "source_type": "lever",
            "source_identifier": source_identifier,
        }

    if host in GREENHOUSE_HOSTS:
        if source_identifier.lower() in GREENHOUSE_NON_BOARD_PATHS:
            return None

        return {
            "source_type": "greenhouse",
            "source_identifier": source_identifier,
        }

    return None


def _slugify_source_identifier(value: str) -> str:
    return "".join(re.findall(r"[A-Za-z0-9]+", value)).lower()


def _company_slug_candidates(seed: Dict[str, Any]) -> List[str]:
    company = str(seed.get("company", "")).strip()
    if not company:
        return []

    words = re.findall(r"[A-Za-z0-9]+", company)
    if not words:
        return []

    candidates = [_slugify_source_identifier(company)]

    trimmed_words = [
        word
        for word in words
        if word.lower() not in COMPANY_SUFFIX_WORDS
    ]
    if trimmed_words:
        candidates.append(_slugify_source_identifier(" ".join(trimmed_words)))

    if len(words) > 1:
        candidates.append(_slugify_source_identifier(words[0]))

    seen: set[str] = set()
    return [
        candidate
        for candidate in candidates
        if candidate and candidate not in seen and not seen.add(candidate)
    ]


def _build_direct_probe_record(
    *,
    seed: Dict[str, Any],
    source_type: str,
    source_identifier: str,
    discovered_at: str,
) -> Dict[str, Any]:
    if source_type == "lever":
        discovery_url = f"https://jobs.lever.co/{source_identifier}"
    else:
        discovery_url = f"https://boards.greenhouse.io/{source_identifier}"

    return _build_candidate_record(
        seed=seed,
        source_type=source_type,
        source_identifier=source_identifier,
        discovery_url=discovery_url,
        discovery_method="direct_ats_probe",
        discovered_at=discovered_at,
    )


def _build_blocked_review_record(
    *,
    seed: Dict[str, Any],
    warning: DiscoveryWarning,
    discovered_at: str,
) -> Dict[str, Any]:
    source_identifier = (_company_slug_candidates(seed) or ["unknown"])[0]
    discovery_url = warning.get("url", "")
    reason = warning.get("reason", "fetch_error")
    careers_url = str(seed.get("careers_url", "")).strip() or discovery_url

    return {
        "company": str(seed.get("company", "")).strip(),
        "source_type": "manual_review",
        "source_identifier": source_identifier,
        "careers_url": careers_url,
        "discovery_url": discovery_url,
        "discovered_at": discovered_at,
        "discovery_method": "blocked_page_review",
        "status": "blocked",
        "validation_notes": f"page fetch blocked or rate-limited: {reason}",
        "source_score": 0.0,
        "internship_likelihood": 0.0,
    }


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


def _host_key(host: str) -> str:
    parts = [part for part in host.lower().split(".") if part and part != "www"]
    if len(parts) <= 2:
        return ".".join(parts)
    return ".".join(parts[-2:])


def _same_site_url(candidate_url: str, base_url: str) -> bool:
    candidate_host = urlparse(candidate_url).netloc.lower()
    base_host = urlparse(base_url).netloc.lower()
    if not candidate_host or not base_host:
        return False
    return _host_key(candidate_host) == _host_key(base_host)


def _looks_like_priority_follow_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.endswith(IGNORED_FOLLOW_EXTENSIONS):
        return False

    target_text = f"{path} {parsed.query}".lower()
    return any(keyword in target_text for keyword in PRIORITY_FOLLOW_KEYWORDS)


def _priority_follow_score(url: str) -> int:
    parsed = urlparse(url)
    target_text = f"{parsed.path} {parsed.query}".lower()
    score = 0

    if any(keyword in target_text for keyword in HIGH_VALUE_FOLLOW_KEYWORDS):
        score += 100
    if any(keyword in target_text for keyword in GENERAL_FOLLOW_KEYWORDS):
        score += 10

    return score


def _iter_priority_follow_targets(html: str) -> Iterable[str]:
    for match in HREF_PATTERN.findall(html):
        yield match.strip()

    for match in INLINE_HTTP_URL_PATTERN.findall(html):
        yield match.strip()

    for match in QUOTED_PATH_PATTERN.findall(html):
        yield match.strip()


def extract_priority_follow_urls(
    html: str,
    base_url: str,
    *,
    limit: int,
) -> List[str]:
    if limit <= 0:
        return []

    follow_candidates: List[tuple[int, int, str]] = []
    seen: set[str] = {urlparse(base_url)._replace(fragment="").geturl()}

    for index, target in enumerate(_iter_priority_follow_targets(html)):
        resolved = urljoin(base_url, target)
        parsed = urlparse(resolved)
        if parsed.scheme not in {"http", "https"}:
            continue

        normalized = parsed._replace(fragment="").geturl()
        if normalized in seen:
            continue
        if classify_source_url(normalized) is not None:
            continue
        if not _same_site_url(normalized, base_url):
            continue
        if not _looks_like_priority_follow_url(normalized):
            continue

        seen.add(normalized)
        follow_candidates.append((_priority_follow_score(normalized), index, normalized))

    sorted_candidates = sorted(follow_candidates, key=lambda item: (-item[0], item[1], item[2]))
    return [url for _, _, url in sorted_candidates[:limit]]


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
    errors: List[DiscoveryWarning] | None = None,
    probe_direct_ats: bool = False,
    record_blocked_sources: bool = False,
    direct_probe_limit: int = 1,
    max_direct_probe_identifiers: int = 2,
    priority_follow_limit: int = 5,
    lever_probe_fn: Callable[..., List[Dict[str, Any]]] = fetch_lever_postings,
    greenhouse_probe_fn: Callable[..., List[Dict[str, Any]]] = fetch_greenhouse_jobs,
) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    page_warnings: List[DiscoveryWarning] = []
    seen_source_keys: set[tuple[str, str]] = set()
    seen_page_urls: set[str] = set()
    company = str(seed.get("company", "")).strip() or "<unknown>"
    scan_queue = list(_seed_scan_urls(seed))

    while scan_queue:
        page_url, scan_method = scan_queue.pop(0)
        normalized_page_url = urlparse(page_url)._replace(fragment="").geturl()
        if normalized_page_url in seen_page_urls:
            continue
        seen_page_urls.add(normalized_page_url)

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

        try:
            html = fetch_html_fn(page_url, timeout)
        except Exception as exc:
            warning = build_fetch_warning(company, page_url, exc)
            page_warnings.append(warning)
            if errors is not None:
                errors.append(warning)
            continue

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

        if scan_method != "priority_link_scan":
            remaining_follow_slots = max(0, priority_follow_limit - sum(
                1 for _, queued_method in scan_queue if queued_method == "priority_link_scan"
            ))
            for follow_url in extract_priority_follow_urls(
                html,
                page_url,
                limit=remaining_follow_slots,
            ):
                if follow_url not in seen_page_urls:
                    scan_queue.append((follow_url, "priority_link_scan"))

    if probe_direct_ats and not candidates:
        for source_identifier in _company_slug_candidates(seed)[:max_direct_probe_identifiers]:
            source_key = ("lever", source_identifier)
            if source_key not in seen_source_keys:
                try:
                    postings = lever_probe_fn(
                        source_identifier,
                        timeout=timeout,
                        limit=direct_probe_limit,
                    )
                except Exception as exc:
                    if errors is not None:
                        errors.append(
                            build_direct_probe_warning(
                                company,
                                "lever",
                                source_identifier,
                                exc,
                            )
                        )
                else:
                    if postings:
                        seen_source_keys.add(source_key)
                        candidates.append(
                            _build_direct_probe_record(
                                seed=seed,
                                source_type="lever",
                                source_identifier=source_identifier,
                                discovered_at=discovered_at,
                            )
                        )

            source_key = ("greenhouse", source_identifier)
            if source_key not in seen_source_keys:
                try:
                    jobs = greenhouse_probe_fn(
                        source_identifier,
                        timeout=timeout,
                        limit=direct_probe_limit,
                        content=False,
                    )
                except Exception as exc:
                    if errors is not None:
                        errors.append(
                            build_direct_probe_warning(
                                company,
                                "greenhouse",
                                source_identifier,
                                exc,
                            )
                        )
                else:
                    if jobs:
                        seen_source_keys.add(source_key)
                        candidates.append(
                            _build_direct_probe_record(
                                seed=seed,
                                source_type="greenhouse",
                                source_identifier=source_identifier,
                                discovered_at=discovered_at,
                            )
                        )

    if record_blocked_sources and not candidates:
        blocked_warning = next(
            (
                warning
                for warning in page_warnings
                if warning.get("reason") in BLOCKED_REVIEW_REASONS
            ),
            None,
        )
        if blocked_warning is not None:
            candidates.append(
                _build_blocked_review_record(
                    seed=seed,
                    warning=blocked_warning,
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
    probe_direct_ats: bool = False,
    record_blocked_sources: bool = False,
    direct_probe_limit: int = 1,
    max_direct_probe_identifiers: int = 2,
    priority_follow_limit: int = 5,
    lever_probe_fn: Callable[..., List[Dict[str, Any]]] = fetch_lever_postings,
    greenhouse_probe_fn: Callable[..., List[Dict[str, Any]]] = fetch_greenhouse_jobs,
) -> tuple[List[Dict[str, Any]], List[DiscoveryWarning]]:
    records: List[Dict[str, Any]] = []
    errors: List[DiscoveryWarning] = []
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
                    errors=errors,
                    probe_direct_ats=probe_direct_ats,
                    record_blocked_sources=record_blocked_sources,
                    direct_probe_limit=direct_probe_limit,
                    max_direct_probe_identifiers=max_direct_probe_identifiers,
                    priority_follow_limit=priority_follow_limit,
                    lever_probe_fn=lever_probe_fn,
                    greenhouse_probe_fn=greenhouse_probe_fn,
                )
            )
        except Exception as exc:
            errors.append(
                build_discovery_warning(
                    company=company,
                    url="",
                    reason="seed_error",
                    message=str(exc),
                )
            )

    return merge_discovered_sources([], records), errors
