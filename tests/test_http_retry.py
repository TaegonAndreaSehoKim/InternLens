from __future__ import annotations

from typing import Any

import httpx
import pytest

import src.ingestion.http_retry as retry_module


class SequenceClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def get(self, url: str) -> httpx.Response:
        response = self.responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return response


def _response(status_code: int, *, payload: Any = None, headers: dict | None = None) -> httpx.Response:
    request = httpx.Request("GET", "https://example.test/jobs")
    return httpx.Response(status_code, request=request, json=payload, headers=headers)


def test_get_json_with_retry_retries_transient_statuses_with_exponential_backoff(
    monkeypatch,
) -> None:
    client = SequenceClient(
        [
            _response(503, payload={"error": "unavailable"}),
            _response(503, payload={"error": "unavailable"}),
            _response(200, payload={"jobs": [1]}),
        ]
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(retry_module.time, "sleep", sleep_calls.append)

    payload = retry_module.get_json_with_retry(
        client,
        "https://example.test/jobs",
        request_label="test source",
        max_attempts=3,
        backoff_seconds=1.0,
    )

    assert payload == {"jobs": [1]}
    assert client.calls == 3
    assert sleep_calls == [1.0, 2.0]


def test_get_json_with_retry_honors_retry_after(monkeypatch) -> None:
    client = SequenceClient(
        [
            _response(429, payload={}, headers={"Retry-After": "4"}),
            _response(200, payload=[]),
        ]
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(retry_module.time, "sleep", sleep_calls.append)

    payload = retry_module.get_json_with_retry(
        client,
        "https://example.test/jobs",
        request_label="rate-limited source",
    )

    assert payload == []
    assert sleep_calls == [4.0]


def test_get_json_with_retry_does_not_retry_permanent_client_error(monkeypatch) -> None:
    client = SequenceClient([_response(404, payload={"error": "missing"})])
    sleep_calls: list[float] = []
    monkeypatch.setattr(retry_module.time, "sleep", sleep_calls.append)

    with pytest.raises(httpx.HTTPStatusError):
        retry_module.get_json_with_retry(
            client,
            "https://example.test/jobs",
            request_label="missing source",
        )

    assert client.calls == 1
    assert sleep_calls == []


def test_get_json_with_retry_retries_connection_error(monkeypatch) -> None:
    request = httpx.Request("GET", "https://example.test/jobs")
    client = SequenceClient(
        [
            httpx.ConnectError("connection reset", request=request),
            _response(200, payload={"jobs": []}),
        ]
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(retry_module.time, "sleep", sleep_calls.append)

    payload = retry_module.get_json_with_retry(
        client,
        "https://example.test/jobs",
        request_label="unstable source",
    )

    assert payload == {"jobs": []}
    assert client.calls == 2
    assert sleep_calls == [1.0]
