from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import scripts.discover_sources as discover_script
from src.discovery.source_discovery import (
    build_direct_probe_warning,
    build_fetch_warning,
    classify_source_url,
    discover_sources,
    extract_candidate_urls,
    extract_priority_follow_urls,
    format_discovery_warning,
    iter_seed_batches,
    merge_discovered_sources,
    resolve_seed_path,
    summarize_discovery_methods,
    summarize_discovery_warnings,
    visible_discovery_warnings,
)


def test_classify_source_url_recognizes_lever_and_greenhouse() -> None:
    assert classify_source_url("https://jobs.lever.co/rws/12345") == {
        "source_type": "lever",
        "source_identifier": "rws",
    }
    assert classify_source_url("https://boards.greenhouse.io/waymo/jobs") == {
        "source_type": "greenhouse",
        "source_identifier": "waymo",
    }
    assert classify_source_url("https://example.com/careers") is None


def test_classify_source_url_normalizes_nested_ats_urls_to_source_identifiers() -> None:
    assert classify_source_url("https://jobs.lever.co/acme/abc123/apply?lever-source=site") == {
        "source_type": "lever",
        "source_identifier": "acme",
    }
    assert classify_source_url("https://boards.greenhouse.io/acme/jobs/123#app") == {
        "source_type": "greenhouse",
        "source_identifier": "acme",
    }
    assert classify_source_url("https://job-boards.greenhouse.io/acme/departments/engineering") == {
        "source_type": "greenhouse",
        "source_identifier": "acme",
    }


def test_classify_source_url_strips_common_trailing_url_punctuation() -> None:
    assert classify_source_url("https://jobs.lever.co/acme);") == {
        "source_type": "lever",
        "source_identifier": "acme",
    }
    assert classify_source_url("https://boards.greenhouse.io/acme/jobs/123);") == {
        "source_type": "greenhouse",
        "source_identifier": "acme",
    }


def test_classify_source_url_rejects_greenhouse_embed_helpers() -> None:
    assert classify_source_url("https://boards.greenhouse.io/embed/job_board?for=acme") is None
    assert classify_source_url("https://job-boards.greenhouse.io/embed/job_app?for=acme") is None


def test_classify_source_url_rejects_non_board_or_malformed_identifiers() -> None:
    assert classify_source_url("https://jobs.lever.co/api/postings/acme") is None
    assert classify_source_url("https://boards.greenhouse.io/api/jobs?for=acme") is None
    assert classify_source_url("https://boards.greenhouse.io/job_app?for=acme") is None
    assert classify_source_url("https://boards.greenhouse.io/acme.com/jobs") is None


def test_extract_candidate_urls_collects_href_and_inline_ats_urls() -> None:
    html = """
    <html>
      <body>
        <a href="/careers">Careers</a>
        <a href="https://jobs.lever.co/acme">Lever</a>
        <script>
          const board = "https://boards.greenhouse.io/acme";
        </script>
      </body>
    </html>
    """

    urls = extract_candidate_urls(html, "https://acme.com")

    assert "https://acme.com/careers" in urls
    assert "https://jobs.lever.co/acme" in urls
    assert "https://boards.greenhouse.io/acme" in urls


def test_extract_priority_follow_urls_keeps_same_site_high_intent_links() -> None:
    html = """
    <a href="/university-recruiting">Students</a>
    <a href="https://careers.acme.com/early-careers">Early Careers</a>
    <script>
      window.__ROUTES__ = {"students": "/students-and-grads"};
      window.__CAREERS__ = {"url": "https://jobs.acme.com/campus"};
    </script>
    <a href="/blog/company-news">Blog</a>
    <a href="https://example.com/internships">External internships</a>
    <a href="/assets/logo.svg">Logo</a>
    <a href="https://jobs.lever.co/acme">ATS</a>
    """

    urls = extract_priority_follow_urls(
        html,
        "https://www.acme.com/careers",
        limit=5,
    )

    assert urls == [
        "https://careers.acme.com/early-careers",
        "https://www.acme.com/university-recruiting",
        "https://jobs.acme.com/campus",
        "https://www.acme.com/students-and-grads",
    ]


def test_extract_priority_follow_urls_prefers_student_links_over_general_jobs() -> None:
    html = """
    <a href="/jobs">Jobs</a>
    <a href="/careers">Careers</a>
    <a href="/blog/intern-experience">Intern blog</a>
    <a href="/university-recruiting">University Recruiting</a>
    <a href="/campus">Campus</a>
    """

    urls = extract_priority_follow_urls(
        html,
        "https://www.acme.com/",
        limit=2,
    )

    assert urls == [
        "https://www.acme.com/blog/intern-experience",
        "https://www.acme.com/university-recruiting",
    ]


def test_discover_sources_follows_priority_links_to_find_nested_ats_boards() -> None:
    seeds = [
        {
            "company": "Acme",
            "homepage_url": "https://www.acme.com",
        }
    ]
    html_by_url = {
        "https://www.acme.com": '<a href="/students-and-grads">Students and grads</a>',
        "https://www.acme.com/students-and-grads": '<a href="https://boards.greenhouse.io/acme">Jobs</a>',
    }
    fetched_urls: list[str] = []

    def fake_fetch_html(url: str, timeout: float) -> str:
        fetched_urls.append(url)
        return html_by_url[url]

    records, errors = discover_sources(
        seeds,
        timeout=10.0,
        fetch_html_fn=fake_fetch_html,
        discovered_at="2026-04-04T00:00:00Z",
    )

    assert errors == []
    assert fetched_urls == [
        "https://www.acme.com",
        "https://www.acme.com/students-and-grads",
    ]
    assert records[0]["source_type"] == "greenhouse"
    assert records[0]["source_identifier"] == "acme"
    assert records[0]["discovery_method"] == "priority_link_scan"


def test_summarize_discovery_methods_counts_record_methods() -> None:
    records = [
        {"discovery_method": "careers_page_scan"},
        {"discovery_method": "priority_link_scan"},
        {"discovery_method": "priority_link_scan"},
    ]

    assert summarize_discovery_methods(records) == {
        "careers_page_scan": 1,
        "priority_link_scan": 2,
    }


def test_discover_sources_dedupes_results_and_reports_page_errors() -> None:
    seeds = [
        {
            "company": "Acme",
            "homepage_url": "https://acme.com",
            "careers_url": "https://careers.acme.com",
        },
        {
            "company": "Broken Co",
            "homepage_url": "https://broken.example.com",
        },
    ]

    html_by_url = {
        "https://careers.acme.com": '<a href="https://jobs.lever.co/acme">Jobs</a>',
        "https://acme.com": '<a href="https://boards.greenhouse.io/acme">Board</a>',
    }

    def fake_fetch_html(url: str, timeout: float) -> str:
        if url not in html_by_url:
            raise RuntimeError(f"cannot fetch {url}")
        return html_by_url[url]

    records, errors = discover_sources(
        seeds,
        timeout=10.0,
        fetch_html_fn=fake_fetch_html,
        discovered_at="2026-04-04T00:00:00Z",
    )

    assert len(records) == 2
    assert {record["source_type"] for record in records} == {"lever", "greenhouse"}
    assert any(error["company"] == "Broken Co" for error in errors)


def test_discover_sources_preserves_partial_seed_results_after_page_error() -> None:
    seeds = [
        {
            "company": "Acme",
            "careers_url": "https://jobs.lever.co/acme",
            "homepage_url": "https://acme.com",
        }
    ]

    def fake_fetch_html(url: str, timeout: float) -> str:
        raise RuntimeError(f"cannot fetch {url}")

    records, errors = discover_sources(
        seeds,
        timeout=10.0,
        fetch_html_fn=fake_fetch_html,
        discovered_at="2026-04-04T00:00:00Z",
    )

    assert records == [
        {
            "company": "Acme",
            "source_type": "lever",
            "source_identifier": "acme",
            "careers_url": "https://jobs.lever.co/acme",
            "discovery_url": "https://jobs.lever.co/acme",
            "discovered_at": "2026-04-04T00:00:00Z",
            "discovery_method": "direct_seed_url",
            "status": "candidate",
            "validation_notes": "",
            "source_score": 0.0,
            "internship_likelihood": 0.0,
        }
    ]
    assert len(errors) == 2
    assert all(error["company"] == "Acme" for error in errors)
    assert all(error["reason"] == "fetch_error" for error in errors)


def test_build_fetch_warning_classifies_common_failure_reasons() -> None:
    request = httpx.Request("GET", "https://blocked.example.com")
    response = httpx.Response(429, request=request)
    http_error = httpx.HTTPStatusError("rate limited", request=request, response=response)

    warnings = [
        build_fetch_warning("Blocked", "https://blocked.example.com", http_error),
        build_fetch_warning("Slow", "https://slow.example.com", httpx.TimeoutException("timed out")),
        build_fetch_warning("Broken", "https://broken.example.com", RuntimeError("boom")),
    ]

    assert [warning["reason"] for warning in warnings] == [
        "http_429",
        "timeout",
        "fetch_error",
    ]
    assert summarize_discovery_warnings(warnings) == {
        "fetch_error": 1,
        "http_429": 1,
        "timeout": 1,
    }
    assert "http_429" in format_discovery_warning(warnings[0])


def test_direct_probe_warnings_are_summarized_but_not_visible_by_default() -> None:
    warnings = [
        build_direct_probe_warning("Acme", "lever", "acme", RuntimeError("not found")),
        build_fetch_warning("Blocked", "https://blocked.example.com", RuntimeError("blocked")),
    ]

    assert warnings[0]["reason"] == "direct_probe_miss"
    assert summarize_discovery_warnings(warnings) == {
        "direct_probe_miss": 1,
        "fetch_error": 1,
    }
    assert visible_discovery_warnings(warnings) == [warnings[1]]


def test_discover_sources_ignores_greenhouse_embed_candidates() -> None:
    seeds = [
        {
            "company": "Acme",
            "homepage_url": "https://acme.com",
        }
    ]

    def fake_fetch_html(url: str, timeout: float) -> str:
        return """
        <a href="https://boards.greenhouse.io/embed/job_board?for=acme">Embedded board</a>
        <a href="https://boards.greenhouse.io/acme">Real board</a>
        """

    records, errors = discover_sources(
        seeds,
        timeout=10.0,
        fetch_html_fn=fake_fetch_html,
        discovered_at="2026-04-04T00:00:00Z",
    )

    assert errors == []
    assert [record["source_identifier"] for record in records] == ["acme"]


def test_discover_sources_can_probe_seed_derived_direct_ats_sources() -> None:
    seeds = [
        {
            "company": "Mistral AI",
            "homepage_url": "https://mistral.ai",
        }
    ]

    def fake_fetch_html(url: str, timeout: float) -> str:
        return "<html>No ATS links here.</html>"

    def fake_lever_probe(site_name: str, *, timeout: float, limit: int | None):
        if site_name == "mistral":
            return [{"text": "Research Intern"}]
        raise RuntimeError("not found")

    def fake_greenhouse_probe(board_token: str, *, timeout: float, limit: int | None, content: bool):
        raise RuntimeError("not found")

    records, errors = discover_sources(
        seeds,
        timeout=10.0,
        fetch_html_fn=fake_fetch_html,
        discovered_at="2026-04-04T00:00:00Z",
        probe_direct_ats=True,
        max_direct_probe_identifiers=2,
        lever_probe_fn=fake_lever_probe,
        greenhouse_probe_fn=fake_greenhouse_probe,
    )

    assert records == [
        {
            "company": "Mistral AI",
            "source_type": "lever",
            "source_identifier": "mistral",
            "careers_url": "https://jobs.lever.co/mistral",
            "discovery_url": "https://jobs.lever.co/mistral",
            "discovered_at": "2026-04-04T00:00:00Z",
            "discovery_method": "direct_ats_probe",
            "status": "candidate",
            "validation_notes": "",
            "source_score": 0.0,
            "internship_likelihood": 0.0,
        }
    ]
    assert any(error["url"] == "https://jobs.lever.co/mistralai" for error in errors)
    assert any(error["url"] == "https://boards.greenhouse.io/mistral" for error in errors)
    assert all(error["reason"] == "direct_probe_miss" for error in errors)


def test_discover_sources_skips_direct_probe_when_page_scan_finds_source() -> None:
    seeds = [{"company": "Acme", "homepage_url": "https://acme.com"}]

    def fake_fetch_html(url: str, timeout: float) -> str:
        return '<a href="https://boards.greenhouse.io/acme">Jobs</a>'

    def fail_probe(*args, **kwargs):
        raise AssertionError("direct probe should not run after page discovery succeeds")

    records, errors = discover_sources(
        seeds,
        timeout=10.0,
        fetch_html_fn=fake_fetch_html,
        discovered_at="2026-04-04T00:00:00Z",
        probe_direct_ats=True,
        lever_probe_fn=fail_probe,
        greenhouse_probe_fn=fail_probe,
    )

    assert errors == []
    assert [record["discovery_method"] for record in records] == ["homepage_scan"]


def test_discover_sources_can_record_blocked_pages_for_manual_review() -> None:
    seeds = [
        {
            "company": "Blocked Co",
            "careers_url": "https://blocked.example.com/careers",
        }
    ]
    request = httpx.Request("GET", "https://blocked.example.com/careers")
    response = httpx.Response(403, request=request)

    def fake_fetch_html(url: str, timeout: float) -> str:
        raise httpx.HTTPStatusError("Forbidden", request=request, response=response)

    records, errors = discover_sources(
        seeds,
        timeout=10.0,
        fetch_html_fn=fake_fetch_html,
        discovered_at="2026-04-04T00:00:00Z",
        record_blocked_sources=True,
    )

    assert records == [
        {
            "company": "Blocked Co",
            "source_type": "manual_review",
            "source_identifier": "blockedco",
            "careers_url": "https://blocked.example.com/careers",
            "discovery_url": "https://blocked.example.com/careers",
            "discovered_at": "2026-04-04T00:00:00Z",
            "discovery_method": "blocked_page_review",
            "status": "blocked",
            "validation_notes": "page fetch blocked or rate-limited: http_403",
            "source_score": 0.0,
            "internship_likelihood": 0.0,
        }
    ]
    assert errors[0]["reason"] == "http_403"


def test_discover_sources_does_not_record_blocked_pages_by_default() -> None:
    seeds = [{"company": "Blocked Co", "careers_url": "https://blocked.example.com/careers"}]
    request = httpx.Request("GET", "https://blocked.example.com/careers")
    response = httpx.Response(403, request=request)

    def fake_fetch_html(url: str, timeout: float) -> str:
        raise httpx.HTTPStatusError("Forbidden", request=request, response=response)

    records, errors = discover_sources(
        seeds,
        timeout=10.0,
        fetch_html_fn=fake_fetch_html,
        discovered_at="2026-04-04T00:00:00Z",
    )

    assert records == []
    assert errors[0]["reason"] == "http_403"


def test_merge_discovered_sources_preserves_existing_status_and_scores() -> None:
    existing = [
        {
            "company": "Waymo",
            "source_type": "greenhouse",
            "source_identifier": "waymo",
            "careers_url": "https://careers.withwaymo.com/",
            "discovery_url": "https://boards.greenhouse.io/waymo",
            "discovered_at": "2026-04-02T10:00:00Z",
            "discovery_method": "manual_seed_scan",
            "status": "validated",
            "validation_notes": "fetch succeeded",
            "source_score": 0.9,
            "internship_likelihood": 0.8,
        }
    ]
    new = [
        {
            "company": "Waymo",
            "source_type": "greenhouse",
            "source_identifier": "waymo",
            "careers_url": "https://careers.withwaymo.com/",
            "discovery_url": "https://job-boards.greenhouse.io/waymo",
            "discovered_at": "2026-04-04T10:00:00Z",
            "discovery_method": "homepage_scan",
            "status": "candidate",
            "validation_notes": "",
            "source_score": 0.0,
            "internship_likelihood": 0.0,
        }
    ]

    merged = merge_discovered_sources(existing, new)

    assert len(merged) == 1
    assert merged[0]["status"] == "validated"
    assert merged[0]["source_score"] == 0.9
    assert merged[0]["internship_likelihood"] == 0.8
    assert merged[0]["discovered_at"] == "2026-04-02T10:00:00Z"


def test_resolve_seed_path_falls_back_to_example(tmp_path: Path) -> None:
    example_path = tmp_path / "company_seeds.example.json"
    example_path.write_text("[]", encoding="utf-8")

    resolved = resolve_seed_path(tmp_path / "company_seeds.json")

    assert resolved == example_path


def test_iter_seed_batches_splits_seed_lists() -> None:
    seeds = [{"company": "A"}, {"company": "B"}, {"company": "C"}]

    assert list(iter_seed_batches(seeds, 2)) == [
        [{"company": "A"}, {"company": "B"}],
        [{"company": "C"}],
    ]
    assert list(iter_seed_batches(seeds, 0)) == [seeds]
    assert list(iter_seed_batches([], 2)) == []


def test_discover_sources_script_merges_and_writes_output(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    seeds_path = tmp_path / "data" / "source_registry" / "company_seeds.json"
    output_path = tmp_path / "data" / "source_registry" / "discovered_sources.json"
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    seeds_path.write_text(
        json.dumps(
            [
                {
                    "company": "Acme",
                    "homepage_url": "https://acme.com",
                    "careers_url": "https://careers.acme.com",
                }
            ]
        ),
        encoding="utf-8",
    )
    output_path.write_text(
        json.dumps(
            [
                {
                    "company": "Existing Co",
                    "source_type": "lever",
                    "source_identifier": "existing",
                    "careers_url": "https://jobs.lever.co/existing",
                    "discovery_url": "https://jobs.lever.co/existing",
                    "discovered_at": "2026-04-01T00:00:00Z",
                    "discovery_method": "manual",
                    "status": "active",
                    "validation_notes": "already active",
                    "source_score": 0.5,
                    "internship_likelihood": 0.4,
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(discover_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        discover_script,
        "_parse_args",
        lambda: SimpleNamespace(
            seed_file="data/source_registry/company_seeds.json",
            output_file="data/source_registry/discovered_sources.json",
            timeout=15.0,
            checkpoint_size=25,
            record_blocked_sources=False,
        ),
    )
    monkeypatch.setattr(
        discover_script,
        "discover_sources",
        lambda seeds, timeout, **kwargs: (
            [
                {
                    "company": "Acme",
                    "source_type": "greenhouse",
                    "source_identifier": "acme",
                    "careers_url": "https://careers.acme.com",
                    "discovery_url": "https://boards.greenhouse.io/acme",
                    "discovered_at": "2026-04-04T00:00:00Z",
                    "discovery_method": "careers_page_scan",
                    "status": "candidate",
                    "validation_notes": "",
                    "source_score": 0.0,
                    "internship_likelihood": 0.0,
                }
            ],
            [
                {
                    "company": "Acme",
                    "url": "https://careers.acme.com",
                    "reason": "http_403",
                    "message": "Forbidden",
                },
                {
                    "company": "Acme",
                    "url": "https://acme.com",
                    "reason": "http_403",
                    "message": "Forbidden",
                },
                {
                    "company": "Acme",
                    "url": "https://jobs.lever.co/acme",
                    "reason": "direct_probe_miss",
                    "message": "Lever request failed for site 'acme' with status 404.",
                },
            ],
        ),
    )

    discover_script.main()
    output = capsys.readouterr().out
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert "Source discovery complete" in output
    assert "Discovery method summary:" in output
    assert "- careers_page_scan: 1" in output
    assert "Warning summary:" in output
    assert "- http_403: 2" in output
    assert "- direct_probe_miss: 1" in output
    assert "Acme: failed to fetch https://careers.acme.com (http_403): Forbidden" in output
    assert "https://jobs.lever.co/acme" not in output
    assert len(payload) == 2
    assert {item["source_identifier"] for item in payload} == {"existing", "acme"}


def test_discover_sources_script_checkpoints_after_each_seed_batch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    seeds_path = tmp_path / "data" / "source_registry" / "company_seeds.json"
    output_path = tmp_path / "data" / "source_registry" / "discovered_sources.json"
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    seeds_path.write_text(
        json.dumps(
            [
                {"company": "Acme", "homepage_url": "https://acme.com"},
                {"company": "Broken", "homepage_url": "https://broken.example.com"},
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(discover_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        discover_script,
        "_parse_args",
        lambda: SimpleNamespace(
            seed_file="data/source_registry/company_seeds.json",
            output_file="data/source_registry/discovered_sources.json",
            timeout=15.0,
            checkpoint_size=1,
            record_blocked_sources=False,
        ),
    )

    calls = 0

    def fake_discover_sources(seeds, timeout, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("interrupted")
        return (
            [
                {
                    "company": "Acme",
                    "source_type": "greenhouse",
                    "source_identifier": "acme",
                    "careers_url": "https://acme.com",
                    "discovery_url": "https://boards.greenhouse.io/acme",
                    "discovered_at": "2026-04-04T00:00:00Z",
                    "discovery_method": "homepage_scan",
                    "status": "candidate",
                    "validation_notes": "",
                    "source_score": 0.0,
                    "internship_likelihood": 0.0,
                }
            ],
            [],
        )

    monkeypatch.setattr(discover_script, "discover_sources", fake_discover_sources)

    with pytest.raises(RuntimeError, match="interrupted"):
        discover_script.main()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert calls == 2
    assert [item["source_identifier"] for item in payload] == ["acme"]
