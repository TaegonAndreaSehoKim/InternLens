from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.discovery.source_discovery import utc_now_iso


DEFAULT_PROFILE = {
    "profile_id": "smoke_deploy_user",
    "resume_text": "Graduate student with Python, machine learning, ranking systems, and data analysis experience.",
    "degree_level": "Master's",
    "major": "Computer Science",
    "grad_date": "2027-12",
    "preferred_roles": [
        "Machine Learning Engineer Intern",
        "Applied Scientist Intern",
        "Data Science Intern",
    ],
    "preferred_locations": ["Remote", "California"],
    "target_industries": ["AI", "Tech"],
    "sponsorship_need": True,
    "extracted_skills": ["Python", "Machine Learning", "PyTorch", "Data Analysis"],
    "years_of_experience": 1,
    "notes": "Deployment smoke profile",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke test a running InternLens API deployment through the stored-profile workflow."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--profile-id", default=DEFAULT_PROFILE["profile_id"])
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--bearer-token", default=None, help="Optional Cognito JWT for protected staging APIs.")
    parser.add_argument(
        "--expect-auth-required",
        action="store_true",
        help="Pass when validating a Cognito-protected deployment without a bearer token.",
    )
    parser.add_argument("--output-file", default=None)
    return parser.parse_args()


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _request(
    client: httpx.Client,
    method: str,
    base_url: str,
    path: str,
    *,
    json_payload: Dict[str, Any] | None = None,
    headers: Dict[str, str] | None = None,
) -> httpx.Response:
    response = client.request(method, _url(base_url, path), json=json_payload, headers=headers)
    response.raise_for_status()
    return response


def _auth_headers(bearer_token: str | None) -> Dict[str, str] | None:
    if not bearer_token:
        return None
    return {"Authorization": f"Bearer {bearer_token}"}


def _step(
    *,
    name: str,
    request_fn: Callable[[], httpx.Response],
) -> Dict[str, Any]:
    started = time.perf_counter()
    response = request_fn()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    return {
        "name": name,
        "status_code": response.status_code,
        "elapsed_ms": elapsed_ms,
        "ok": 200 <= response.status_code < 300,
        "body": response.json(),
    }


def _response_body(response: httpx.Response) -> Dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {"text": response.text}
    if isinstance(payload, dict):
        return payload
    return {"value": payload}


def _schema_top_k_maximum(openapi_body: Dict[str, Any]) -> Any:
    schemas = openapi_body.get("components", {}).get("schemas", {})
    for schema_name in ("ProfileRecommendRequest", "RecommendRequest"):
        top_k_schema = schemas.get(schema_name, {}).get("properties", {}).get("top_k", {})
        if "maximum" in top_k_schema:
            return top_k_schema["maximum"]
    return None


def _profile_payload(profile_id: str) -> Dict[str, Any]:
    return {**DEFAULT_PROFILE, "profile_id": profile_id}


def run_deployment_smoke(
    *,
    base_url: str,
    profile_id: str,
    top_k: int,
    timeout: float,
    bearer_token: str | None = None,
    expect_auth_required: bool = False,
    client_factory: Callable[..., httpx.Client] = httpx.Client,
) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    headers = _auth_headers(bearer_token)

    with client_factory(timeout=timeout) as client:
        steps.append(
            _step(
                name="health",
                request_fn=lambda: _request(client, "GET", base_url, "/health"),
            )
        )

        if expect_auth_required and bearer_token is None:
            started = time.perf_counter()
            auth_response = client.request(
                "POST",
                _url(base_url, "/profiles"),
                json=_profile_payload(profile_id),
            )
            steps.append(
                {
                    "name": "auth_required",
                    "status_code": auth_response.status_code,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                    "ok": auth_response.status_code in {401, 403},
                    "body": _response_body(auth_response),
                }
            )

            schema_step = _step(
                name="openapi_schema",
                request_fn=lambda: _request(client, "GET", base_url, "/openapi.json"),
            )
            top_k_maximum = _schema_top_k_maximum(schema_step["body"])
            schema_step["ok"] = schema_step["ok"] and top_k_maximum == 1000
            schema_step["top_k_maximum"] = top_k_maximum
            steps.append(schema_step)

            return {
                "generated_at": utc_now_iso(),
                "base_url": base_url.rstrip("/"),
                "profile_id": profile_id,
                "ok": all(step["ok"] for step in steps),
                "steps": steps,
                "summary": {
                    "run_id": None,
                    "returned_jobs": None,
                    "dashboard_runs": None,
                    "saved_jobs": None,
                    "applied_jobs": None,
                    "auth_required": steps[1]["ok"],
                    "top_k_maximum": top_k_maximum,
                },
            }

        try:
            profile_response = _request(
                client,
                "POST",
                base_url,
                "/profiles",
                json_payload=_profile_payload(profile_id),
                headers=headers,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 400 or "already exists" not in exc.response.text:
                raise
            profile_response = _request(
                client,
                "GET",
                base_url,
                f"/profiles/{profile_id}",
                headers=headers,
            )

        steps.append(
            {
                "name": "profile",
                "status_code": profile_response.status_code,
                "elapsed_ms": None,
                "ok": 200 <= profile_response.status_code < 300,
                "body": profile_response.json(),
            }
        )

        steps.append(
            _step(
                name="recommend",
                request_fn=lambda: _request(
                    client,
                    "POST",
                    base_url,
                    f"/profiles/{profile_id}/recommend",
                    json_payload={
                        "top_k": top_k,
                        "include_feedback": True,
                        "exclude_dismissed": True,
                        "exclude_applied": True,
                        "include_debug": False,
                        "save_run": True,
                    },
                    headers=headers,
                ),
            )
        )

        steps.append(
            _step(
                name="dashboard",
                request_fn=lambda: _request(
                    client,
                    "GET",
                    base_url,
                    f"/profiles/{profile_id}/dashboard",
                    headers=headers,
                ),
            )
        )

    recommend_body = steps[-2]["body"]
    dashboard_body = steps[-1]["body"]
    return {
        "generated_at": utc_now_iso(),
        "base_url": base_url.rstrip("/"),
        "profile_id": profile_id,
        "ok": all(step["ok"] for step in steps),
        "steps": steps,
        "summary": {
            "run_id": recommend_body.get("run_id"),
            "returned_jobs": recommend_body.get("returned_jobs"),
            "dashboard_runs": dashboard_body.get("summary", {}).get("recommendation_run_count"),
            "saved_jobs": dashboard_body.get("summary", {}).get("saved_jobs_count"),
            "applied_jobs": dashboard_body.get("summary", {}).get("applied_jobs_count"),
        },
    }


def _write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")


def _print_summary(report: Dict[str, Any]) -> None:
    print("##### Deployment smoke complete #####")
    print(f"Base URL: {report['base_url']}")
    print(f"Profile ID: {report['profile_id']}")
    print(f"Overall: {'passed' if report['ok'] else 'failed'}")
    for step in report["steps"]:
        elapsed = "" if step["elapsed_ms"] is None else f" ({step['elapsed_ms']} ms)"
        print(f"- {step['name']}: {step['status_code']}{elapsed}")
    print(f"Run ID: {report['summary']['run_id']}")
    print(f"Returned jobs: {report['summary']['returned_jobs']}")


def main() -> None:
    args = _parse_args()
    report = run_deployment_smoke(
        base_url=args.base_url,
        profile_id=args.profile_id,
        top_k=args.top_k,
        timeout=args.timeout,
        bearer_token=args.bearer_token,
        expect_auth_required=args.expect_auth_required,
    )

    if args.output_file:
        _write_report(PROJECT_ROOT / args.output_file, report)

    _print_summary(report)

    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
