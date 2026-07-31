from __future__ import annotations

import sys
import time
from typing import Any

import httpx


DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0
MAX_RETRY_DELAY_SECONDS = 30.0
RETRYABLE_STATUS_CODES = {408, 425, 429}


def _is_retryable_failure(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code in RETRYABLE_STATUS_CODES or status_code >= 500

    return isinstance(exc, (httpx.RequestError, ValueError))


def _retry_delay_seconds(
    exc: Exception,
    *,
    attempt: int,
    backoff_seconds: float,
) -> float:
    if isinstance(exc, httpx.HTTPStatusError):
        retry_after = exc.response.headers.get("Retry-After", "").strip()
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), MAX_RETRY_DELAY_SECONDS)
            except ValueError:
                pass

    return min(backoff_seconds * (2 ** (attempt - 1)), MAX_RETRY_DELAY_SECONDS)


def _failure_description(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "request timeout"
    if isinstance(exc, httpx.RequestError):
        return type(exc).__name__
    return "invalid JSON response"


def get_json_with_retry(
    client: httpx.Client,
    url: str,
    *,
    request_label: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
) -> Any:
    if max_attempts < 1:
        raise ValueError("max_attempts must be greater than or equal to 1.")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds must be greater than or equal to 0.")

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            if not _is_retryable_failure(exc) or attempt >= max_attempts:
                raise

            delay_seconds = _retry_delay_seconds(
                exc,
                attempt=attempt,
                backoff_seconds=backoff_seconds,
            )
            print(
                f"Retrying {request_label} after {_failure_description(exc)} "
                f"(attempt {attempt}/{max_attempts}, delay {delay_seconds:g}s).",
                file=sys.stderr,
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Retry loop completed without returning or raising.")
