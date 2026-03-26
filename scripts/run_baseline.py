from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import load_candidate_profile
from src.ranking.baseline_scorer import rank_jobs


def _ensure_output_dir(output_dir: Path) -> None:
    """Create the output directory if it does not already exist."""
    output_dir.mkdir(parents=True, exist_ok=True)


def _save_ranked_results_json(ranked_jobs: List[Dict[str, Any]], output_path: Path) -> None:
    """Save ranked job results to a JSON file."""
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(ranked_jobs, f, indent=2)


def _save_ranked_results_csv(ranked_jobs: List[Dict[str, Any]], output_path: Path) -> None:
    """Save ranked job results to a CSV file."""
    fieldnames = [
        "job_id",
        "company",
        "title",
        "location",
        "score",
        "action_label",
        "matched_skills",
        "skill_gaps",
        "reasons",
        "blocking_issues",
        "skill_score",
        "role_score",
        "location_score",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for job in ranked_jobs:
            writer.writerow(
                {
                    "job_id": job["job_id"],
                    "company": job["company"],
                    "title": job["title"],
                    "location": job["location"],
                    "score": job["score"],
                    "action_label": job["action_label"],
                    "matched_skills": ", ".join(job["matched_skills"]),
                    "skill_gaps": ", ".join(job["skill_gaps"]),
                    "reasons": " | ".join(job["reasons"]),
                    "blocking_issues": " | ".join(job["blocking_issues"]),
                    "skill_score": job["component_scores"]["skill_score"],
                    "role_score": job["component_scores"]["role_score"],
                    "location_score": job["component_scores"]["location_score"],
                }
            )


def _print_ranked_results(ranked_jobs: List[Dict[str, Any]]) -> None:
    """Print ranked job results in a readable format."""
    print("\n=== InternLens Baseline Ranking Results ===\n")

    for idx, job in enumerate(ranked_jobs, start=1):
        print(f"[{idx}] {job['title']} @ {job['company']}")
        print(f"    Location: {job['location']}")
        print(f"    Score: {job['score']}")
        print(f"    Action: {job['action_label']}")
        print(
            f"    Blocking Issues: "
            f"{', '.join(job['blocking_issues']) if job['blocking_issues'] else 'None'}"
        )
        print(f"    Matched Skills: {', '.join(job['matched_skills']) if job['matched_skills'] else 'None'}")
        print(f"    Skill Gaps: {', '.join(job['skill_gaps']) if job['skill_gaps'] else 'None'}")
        print("    Reasons:")
        for reason in job["reasons"]:
            print(f"      - {reason}")
        print()


def main() -> None:
    profile_path = PROJECT_ROOT / "data" / "processed" / "candidate_profile_example.json"
    jobs_dir = PROJECT_ROOT / "data" / "sample_jobs"
    output_dir = PROJECT_ROOT / "outputs"

    profile = load_candidate_profile(profile_path)
    jobs = load_all_job_postings(jobs_dir)
    ranked_jobs = rank_jobs(profile, jobs)

    _ensure_output_dir(output_dir)

    json_output_path = output_dir / "ranked_results.json"
    csv_output_path = output_dir / "ranked_results.csv"

    _save_ranked_results_json(ranked_jobs, json_output_path)
    _save_ranked_results_csv(ranked_jobs, csv_output_path)
    _print_ranked_results(ranked_jobs)

    print(f"Saved JSON results to: {json_output_path}")
    print(f"Saved CSV results to: {csv_output_path}")


if __name__ == "__main__":
    main()
