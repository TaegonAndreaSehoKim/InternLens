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
from src.ranking.feedback_reranker import apply_feedback_reranking, load_feedback_profile
from src.ranking.output_filters import filter_results_for_output, truncate_results


def parse_args() -> argparse.Namespace:
    # Parse command-line arguments for baseline ranking runs.
    parser = argparse.ArgumentParser(description="Run the InternLens baseline ranking pipeline.")
    parser.add_argument(
        "--profile-path",
        default="data/processed/candidate_profile_example.json",
        help="Path to the candidate profile JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--jobs-dir",
        default="data/sample_jobs",
        help="Path to the directory containing job posting JSON files, relative to the project root.",
    )
    parser.add_argument(
        "--feedback-path",
        default=None,
        help="Optional path to a feedback JSON file, relative to the project root.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where JSON and CSV outputs should be written, relative to the project root.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Optional number of results to print and export after filtering.",
    )
    parser.add_argument(
        "--eligible-only",
        action="store_true",
        help="Show and export only jobs with no blocking issues.",
    )
    parser.add_argument(
        "--applyable-only",
        action="store_true",
        help="Show and export only jobs with action_label other than Skip.",
    )
    return parser.parse_args()


def _stringify_list(values: List[Any]) -> str:
    # Convert list-like values into a readable string for CSV export.
    if not values:
        return ""
    return " | ".join(str(value) for value in values)


def _feedback_explanations_to_text(job: Dict[str, Any]) -> str:
    # Flatten feedback explanation items into one readable string for CSV export.
    explanations = job.get("feedback_explanations") or []
    if not explanations:
        return ""

    parts: List[str] = []
    for item in explanations:
        parts.append(
            (
                f"{item.get('feedback_label', '')}:{item.get('source_job_title', '')}"
                f":sim={item.get('similarity', 0)}"
                f":adj={item.get('adjustment', 0)}"
            )
        )

    return " | ".join(parts)


def _export_results_json(results: List[Dict[str, Any]], output_path: Path) -> None:
    # Save ranked results as JSON.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def _export_results_csv(results: List[Dict[str, Any]], output_path: Path) -> None:
    # Save ranked results as CSV.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "job_id",
        "company",
        "title",
        "location",
        "score",
        "action_label",
        "blocking_issues",
        "matched_skills",
        "skill_gaps",
        "reasons",
        "skill_score",
        "role_score",
        "location_score",
        "internship_bonus",
        "feedback_adjustment",
        "reranked_score",
        "feedback_explanations",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for job in results:
            component_scores = job.get("component_scores", {})
            writer.writerow(
                {
                    "job_id": job.get("job_id", ""),
                    "company": job.get("company", ""),
                    "title": job.get("title", ""),
                    "location": job.get("location", ""),
                    "score": job.get("score", ""),
                    "action_label": job.get("action_label", ""),
                    "blocking_issues": _stringify_list(job.get("blocking_issues", [])),
                    "matched_skills": _stringify_list(job.get("matched_skills", [])),
                    "skill_gaps": _stringify_list(job.get("skill_gaps", [])),
                    "reasons": _stringify_list(job.get("reasons", [])),
                    "skill_score": component_scores.get("skill_score", ""),
                    "role_score": component_scores.get("role_score", ""),
                    "location_score": component_scores.get("location_score", ""),
                    "internship_bonus": component_scores.get("internship_bonus", ""),
                    "feedback_adjustment": job.get("feedback_adjustment", ""),
                    "reranked_score": job.get("reranked_score", ""),
                    "feedback_explanations": _feedback_explanations_to_text(job),
                }
            )


def _print_job(job: Dict[str, Any], index: int) -> None:
    # Print one ranked job in a readable console format.
    print(f"[{index}] {job['title']} @ {job['company']}")
    print(f"    Location: {job['location']}")
    print(f"    Score: {job['score']}")

    if job.get("feedback_adjustment") is not None:
        print(f"    Feedback Adjustment: {job['feedback_adjustment']}")
    if job.get("reranked_score") is not None:
        print(f"    Reranked Score: {job['reranked_score']}")

    feedback_explanations = job.get("feedback_explanations") or []
    if feedback_explanations:
        print("    Feedback Explanations:")
        for item in feedback_explanations:
            shared_title_tokens = item.get("shared_title_tokens") or []
            shared_skill_tokens = item.get("shared_skill_tokens") or []
            shared_title_text = ", ".join(shared_title_tokens) if shared_title_tokens else "None"
            shared_skill_text = ", ".join(shared_skill_tokens) if shared_skill_tokens else "None"

            print(
                "      - "
                f"{item.get('feedback_label', '')} -> {item.get('source_job_title', '')} "
                f"| similarity={item.get('similarity', 0)} "
                f"| adjustment={item.get('adjustment', 0)}"
            )
            print(
                f"        shared_title_tokens={shared_title_text}; "
                f"shared_skill_tokens={shared_skill_text}"
            )

    print(f"    Action: {job['action_label']}")

    blocking_issues = job.get("blocking_issues") or []
    print(f"    Blocking Issues: {', '.join(blocking_issues) if blocking_issues else 'None'}")

    matched_skills = job.get("matched_skills") or []
    print(f"    Matched Skills: {', '.join(matched_skills) if matched_skills else 'None'}")

    skill_gaps = job.get("skill_gaps") or []
    print(f"    Skill Gaps: {', '.join(skill_gaps) if skill_gaps else 'None'}")

    print("    Reasons:")
    for reason in job.get("reasons", []):
        print(f"      - {reason}")

    print()


def main() -> None:
    args = parse_args()

    profile_path = PROJECT_ROOT / args.profile_path
    jobs_dir = PROJECT_ROOT / args.jobs_dir
    output_dir = PROJECT_ROOT / args.output_dir

    profile = load_candidate_profile(profile_path)
    jobs = load_all_job_postings(jobs_dir)
    ranked_jobs = rank_jobs(profile, jobs)

    output_prefix = "ranked_results"

    if args.feedback_path:
        feedback_path = PROJECT_ROOT / args.feedback_path
        feedback_profile = load_feedback_profile(feedback_path)
        ranked_jobs = apply_feedback_reranking(ranked_jobs, jobs, feedback_profile)
        output_prefix = "reranked_results"

    visible_jobs = filter_results_for_output(
        ranked_jobs,
        eligible_only=args.eligible_only,
        applyable_only=args.applyable_only,
    )
    visible_jobs = truncate_results(visible_jobs, args.top_k)

    print("\n=== InternLens Baseline Ranking Results ===\n")

    if args.eligible_only:
        print("(eligible_only=True: showing only jobs with no blocking issues)\n")

    if args.applyable_only:
        print("(applyable_only=True: showing only jobs with action_label != Skip)\n")

    if not visible_jobs:
        print("No jobs matched the current output filter.")
    else:
        for index, job in enumerate(visible_jobs, start=1):
            _print_job(job, index)

    if args.eligible_only:
        output_prefix += "_eligible_only"

    if args.applyable_only:
        output_prefix += "_applyable_only"

    json_output_path = output_dir / f"{output_prefix}.json"
    csv_output_path = output_dir / f"{output_prefix}.csv"

    _export_results_json(visible_jobs, json_output_path)
    _export_results_csv(visible_jobs, csv_output_path)

    if "reranked" in output_prefix:
        print(f"Saved reranked JSON results to: {json_output_path}")
        print(f"Saved reranked CSV results to: {csv_output_path}")
    else:
        print(f"Saved baseline JSON results to: {json_output_path}")
        print(f"Saved baseline CSV results to: {csv_output_path}")


if __name__ == "__main__":
    main()
