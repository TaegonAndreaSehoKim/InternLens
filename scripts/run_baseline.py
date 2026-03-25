from __future__ import annotations

import sys
from pathlib import Path

# Resolve the project root based on the current file location.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Add the project root to sys.path so that src imports work when running this script directly.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import load_candidate_profile
from src.ranking.baseline_scorer import rank_jobs


def main() -> None:
    """
    Load the sample candidate profile and sample jobs,
    run the baseline ranking pipeline, and print the results.
    """
    profile_path = PROJECT_ROOT / "data" / "processed" / "candidate_profile_example.json"
    jobs_dir = PROJECT_ROOT / "data" / "sample_jobs"

    # Load input data.
    profile = load_candidate_profile(profile_path)
    jobs = load_all_job_postings(jobs_dir)

    # Run the ranking pipeline.
    ranked_jobs = rank_jobs(profile, jobs)

    # Print the ranked results in a readable format.
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


if __name__ == "__main__":
    main()