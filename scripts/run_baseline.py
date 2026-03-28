from __future__ import annotations

import argparse
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
from src.ranking.feedback_reranker import (
    apply_feedback_reranking,
    load_feedback_profile,
)


def _ensure_output_dir(output_dir: Path) -> None:
    """Create the output directory if it does not already exist."""
    output_dir.mkdir(parents=True, exist_ok=True)


def _save_ranked_results_json(ranked_jobs: List[Dict[str, Any]], output_path: Path) -> None:
    """Save ranked or reranked results to a JSON file."""
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(ranked_jobs, f, indent=2)


def _save_ranked_results_csv(ranked_jobs: List[Dict[str, Any]], output_path: Path) -> None:
    """Save ranked or reranked results to a CSV file."""
    # Start with the baseline output fields.
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

    # Add reranking-specific columns only when they exist in the result rows.
    if ranked_jobs and "feedback_adjustment" in ranked_jobs[0]:
        fieldnames.extend(
            [
                "feedback_adjustment",
                "reranked_score",
                "feedback_explanations",
            ]
        )

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for job in ranked_jobs:
            row = {
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

            # Include reranking columns only when available.
            if "feedback_adjustment" in job:
                row["feedback_adjustment"] = job["feedback_adjustment"]
                row["reranked_score"] = job["reranked_score"]
                row["feedback_explanations"] = json.dumps(
                    job.get("feedback_explanations", []),
                    ensure_ascii=False,
                )

            writer.writerow(row)


def _print_ranked_results(ranked_jobs: List[Dict[str, Any]], title: str) -> None:
    """Print ranked job results in a readable format."""
    print(f"\n=== {title} ===\n")

    for idx, job in enumerate(ranked_jobs, start=1):
        print(f"[{idx}] {job['title']} @ {job['company']}")
        print(f"    Location: {job['location']}")
        print(f"    Score: {job['score']}")

        # Show reranking details only when feedback-based fields exist.
        if "feedback_adjustment" in job:
            print(f"    Feedback Adjustment: {job['feedback_adjustment']}")
            print(f"    Reranked Score: {job['reranked_score']}")

            explanations = job.get("feedback_explanations", [])
            if explanations:
                print("    Feedback Explanations:")
                for explanation in explanations:
                    print(
                        "      - "
                        f"{explanation['feedback_label']} -> "
                        f"{explanation['source_job_title']} | "
                        f"similarity={explanation['similarity']} | "
                        f"adjustment={explanation['adjustment']}"
                    )
                    print(
                        "        shared_title_tokens="
                        f"{', '.join(explanation['shared_title_tokens']) if explanation['shared_title_tokens'] else 'None'}; "
                        "shared_skill_tokens="
                        f"{', '.join(explanation['shared_skill_tokens']) if explanation['shared_skill_tokens'] else 'None'}"
                    )

        print(f"    Action: {job['action_label']}")
        print(
            f"    Blocking Issues: "
            f"{', '.join(job['blocking_issues']) if job['blocking_issues'] else 'None'}"
        )
        print(
            f"    Matched Skills: "
            f"{', '.join(job['matched_skills']) if job['matched_skills'] else 'None'}"
        )
        print(
            f"    Skill Gaps: "
            f"{', '.join(job['skill_gaps']) if job['skill_gaps'] else 'None'}"
        )
        print("    Reasons:")
        for reason in job["reasons"]:
            print(f"      - {reason}")
        print()


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for local script execution."""
    parser = argparse.ArgumentParser(description="Run InternLens ranking locally.")
    parser.add_argument(
        "--profile-path",
        default="data/processed/candidate_profile_example.json",
        help="Path to the candidate profile JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--jobs-dir",
        default="data/sample_jobs",
        help="Path to the job posting directory, relative to the project root.",
    )
    parser.add_argument(
        "--feedback-path",
        default=None,
        help="Optional path to a feedback JSON file for feedback-based reranking.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    profile_path = PROJECT_ROOT / args.profile_path
    jobs_dir = PROJECT_ROOT / args.jobs_dir
    output_dir = PROJECT_ROOT / "outputs"

    profile = load_candidate_profile(profile_path)
    jobs = load_all_job_postings(jobs_dir)
    ranked_jobs = rank_jobs(profile, jobs)

    _ensure_output_dir(output_dir)

    # Always save the baseline ranking outputs.
    baseline_json_output_path = output_dir / "ranked_results.json"
    baseline_csv_output_path = output_dir / "ranked_results.csv"

    _save_ranked_results_json(ranked_jobs, baseline_json_output_path)
    _save_ranked_results_csv(ranked_jobs, baseline_csv_output_path)
    _print_ranked_results(ranked_jobs, "InternLens Baseline Ranking Results")

    print(f"Saved baseline JSON results to: {baseline_json_output_path}")
    print(f"Saved baseline CSV results to: {baseline_csv_output_path}")

    # Apply optional feedback-based reranking only when a feedback file is provided.
    if args.feedback_path:
        feedback_path = PROJECT_ROOT / args.feedback_path
        feedback_profile = load_feedback_profile(feedback_path)
        reranked_jobs = apply_feedback_reranking(ranked_jobs, jobs, feedback_profile)

        reranked_json_output_path = output_dir / "reranked_results.json"
        reranked_csv_output_path = output_dir / "reranked_results.csv"

        _save_ranked_results_json(reranked_jobs, reranked_json_output_path)
        _save_ranked_results_csv(reranked_jobs, reranked_csv_output_path)
        _print_ranked_results(reranked_jobs, "InternLens Feedback-Reranked Results")

        print(f"Saved reranked JSON results to: {reranked_json_output_path}")
        print(f"Saved reranked CSV results to: {reranked_csv_output_path}")


if __name__ == "__main__":
    main()