from __future__ import annotations

import json
from types import SimpleNamespace

import httpx

import scripts.smoke_deployment as smoke_script


class FakeSmokeClient:
    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout
        self.requests: list[tuple[str, str, dict | None]] = []

    def __enter__(self) -> "FakeSmokeClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def request(
        self,
        method: str,
        url: str,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        self.requests.append((method, url, json))
        request = httpx.Request(method, url)

        if url.endswith("/health"):
            return httpx.Response(200, json={"status": "ok"}, request=request)
        if method == "POST" and url.endswith("/profiles"):
            return httpx.Response(201, json={**json, "created_at": "now", "updated_at": "now"}, request=request)
        if method == "POST" and url.endswith("/profiles/smoke_user/recommend"):
            return httpx.Response(
                200,
                json={
                    "run_id": "run_123",
                    "returned_jobs": 2,
                    "results": [],
                },
                request=request,
            )
        if method == "GET" and url.endswith("/profiles/smoke_user/dashboard"):
            return httpx.Response(
                200,
                json={
                    "summary": {
                        "recommendation_run_count": 1,
                        "saved_jobs_count": 0,
                        "applied_jobs_count": 0,
                    }
                },
                request=request,
            )

        return httpx.Response(404, json={"detail": "not found"}, request=request)


def test_run_deployment_smoke_checks_stored_profile_flow() -> None:
    clients: list[FakeSmokeClient] = []

    def fake_client_factory(*, timeout: float) -> FakeSmokeClient:
        client = FakeSmokeClient(timeout=timeout)
        clients.append(client)
        return client

    report = smoke_script.run_deployment_smoke(
        base_url="https://api.example.com/",
        profile_id="smoke_user",
        top_k=2,
        timeout=15.0,
        client_factory=fake_client_factory,
    )

    assert report["ok"] is True
    assert report["base_url"] == "https://api.example.com"
    assert report["summary"] == {
        "run_id": "run_123",
        "returned_jobs": 2,
        "dashboard_runs": 1,
        "saved_jobs": 0,
        "applied_jobs": 0,
    }
    assert [request[0] for request in clients[0].requests] == ["GET", "POST", "POST", "GET"]
    assert clients[0].requests[2][2]["top_k"] == 2


def test_run_deployment_smoke_loads_existing_profile_on_duplicate() -> None:
    class ExistingProfileClient(FakeSmokeClient):
        def request(
            self,
            method: str,
            url: str,
            json: dict | None = None,
            headers: dict | None = None,
        ) -> httpx.Response:
            if method == "POST" and url.endswith("/profiles"):
                request = httpx.Request(method, url)
                return httpx.Response(409, json={"detail": "Profile already exists: smoke_user"}, request=request)
            if method == "GET" and url.endswith("/profiles/smoke_user"):
                request = httpx.Request(method, url)
                return httpx.Response(200, json={"profile_id": "smoke_user"}, request=request)
            return super().request(method, url, json=json, headers=headers)

    report = smoke_script.run_deployment_smoke(
        base_url="http://localhost:8000",
        profile_id="smoke_user",
        top_k=1,
        timeout=10.0,
        client_factory=lambda **kwargs: ExistingProfileClient(**kwargs),
    )

    assert report["ok"] is True
    assert report["steps"][1]["status_code"] == 200


def test_run_deployment_smoke_can_expect_auth_required() -> None:
    class AuthRequiredClient(FakeSmokeClient):
        def request(
            self,
            method: str,
            url: str,
            json: dict | None = None,
            headers: dict | None = None,
        ) -> httpx.Response:
            if method == "POST" and url.endswith("/profiles"):
                self.requests.append((method, url, json))
                request = httpx.Request(method, url)
                return httpx.Response(401, json={"detail": "Missing bearer authentication token."}, request=request)
            if method == "GET" and url.endswith("/openapi.json"):
                self.requests.append((method, url, json))
                request = httpx.Request(method, url)
                return httpx.Response(
                    200,
                    json={
                        "components": {
                            "schemas": {
                                "ProfileRecommendRequest": {
                                    "properties": {"top_k": {"maximum": 1000}}
                                }
                            }
                        }
                    },
                    request=request,
                )
            return super().request(method, url, json=json, headers=headers)

    report = smoke_script.run_deployment_smoke(
        base_url="https://api.example.com",
        profile_id="smoke_user",
        top_k=1000,
        timeout=10.0,
        expect_auth_required=True,
        client_factory=lambda **kwargs: AuthRequiredClient(**kwargs),
    )

    assert report["ok"] is True
    assert [step["name"] for step in report["steps"]] == ["health", "auth_required", "openapi_schema"]
    assert report["summary"]["auth_required"] is True
    assert report["summary"]["top_k_maximum"] == 1000


def test_smoke_deployment_main_writes_report(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(smoke_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        smoke_script,
        "_parse_args",
        lambda: SimpleNamespace(
            base_url="https://api.example.com",
            profile_id="smoke_user",
            top_k=2,
            timeout=15.0,
            bearer_token=None,
            expect_auth_required=False,
            output_file="outputs/deployment_smoke.json",
        ),
    )
    monkeypatch.setattr(
        smoke_script,
        "run_deployment_smoke",
        lambda **kwargs: {
            "generated_at": "2026-05-07T12:00:00Z",
            "base_url": kwargs["base_url"],
            "profile_id": kwargs["profile_id"],
            "ok": True,
            "steps": [
                {"name": "health", "status_code": 200, "elapsed_ms": 1.2, "ok": True},
            ],
            "summary": {
                "run_id": "run_123",
                "returned_jobs": 2,
                "dashboard_runs": 1,
                "saved_jobs": 0,
                "applied_jobs": 0,
            },
        },
    )

    smoke_script.main()
    output = capsys.readouterr().out
    payload = json.loads((tmp_path / "outputs" / "deployment_smoke.json").read_text(encoding="utf-8"))

    assert "Deployment smoke complete" in output
    assert "Overall: passed" in output
    assert payload["summary"]["run_id"] == "run_123"
