from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.api.settings import DEFAULT_JOBS_DIR, resolve_project_path
from src.preprocessing.corpus_health import build_corpus_health_report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that the processed job corpus has active, recommendable jobs."
    )
    parser.add_argument(
        "--jobs-dir",
        default=DEFAULT_JOBS_DIR,
        help="Path to processed job JSON files, relative to the project root.",
    )
    parser.add_argument(
        "--min-active-jobs",
        type=int,
        default=1,
        help="Minimum non-expired jobs required for a healthy corpus.",
    )
    parser.add_argument(
        "--output-file",
        default=None,
        help="Optional JSON report path, relative to the project root.",
    )
    return parser.parse_args()


def _write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _print_report(report: Dict[str, Any]) -> None:
    print("##### Corpus health #####")
    print(f"Jobs dir: {report['jobs_dir']}")
    print(f"Active jobs: {report['active_job_count']}")
    print(f"All jobs: {report['all_job_count']}")
    print(f"Expired or filtered jobs: {report['expired_or_filtered_job_count']}")
    print(f"Latest fetched_at: {report['latest_fetched_at']}")
    print(f"Latest expires_at: {report['latest_expires_at']}")
    print(f"Minimum active jobs: {report['min_active_jobs']}")
    print(f"Overall: {'passed' if report['ok'] else 'failed'}")


def main() -> None:
    args = _parse_args()
    report = build_corpus_health_report(
        args.jobs_dir,
        min_active_jobs=args.min_active_jobs,
    )

    if args.output_file:
        _write_report(resolve_project_path(PROJECT_ROOT, args.output_file), report)

    _print_report(report)

    if not report["ok"]:
        raise SystemExit(
            "Corpus health check failed: "
            f"{report['active_job_count']} active job(s), "
            f"minimum required is {report['min_active_jobs']}."
        )


if __name__ == "__main__":
    main()
