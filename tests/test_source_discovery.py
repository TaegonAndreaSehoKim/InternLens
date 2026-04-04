from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import scripts.discover_sources as discover_script
from src.discovery.source_discovery import (
    classify_source_url,
    discover_sources,
    extract_candidate_urls,
    merge_discovered_sources,
    resolve_seed_path,
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
    assert any("Broken Co" in error for error in errors)


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
        ),
    )
    monkeypatch.setattr(
        discover_script,
        "discover_sources",
        lambda seeds, timeout: (
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
            [],
        ),
    )

    discover_script.main()
    output = capsys.readouterr().out
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert "Source discovery complete" in output
    assert len(payload) == 2
    assert {item["source_identifier"] for item in payload} == {"existing", "acme"}
