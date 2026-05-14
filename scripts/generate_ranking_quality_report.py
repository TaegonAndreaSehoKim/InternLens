from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.preprocessing.job_parser import load_all_job_postings
from src.preprocessing.profile_parser import normalize_candidate_profile
from src.ranking.baseline_scorer import rank_jobs


REPRESENTATIVE_PROFILES: Dict[str, Dict[str, Any]] = {
    "cs_engineering": {
        "profile_id": "quality_cs_engineering",
        "resume_text": "Computer science student with backend, Python, SQL, cloud, and software engineering projects.",
        "degree_level": "Bachelor's",
        "major": "computer science",
        "grad_date": "2027-05",
        "preferred_roles": ["Software Engineering Intern", "Backend Engineer Intern", "Data Engineer Intern"],
        "preferred_locations": [],
        "target_industries": ["Technology", "AI"],
        "sponsorship_need": False,
        "extracted_skills": ["Python", "SQL", "AWS", "Docker", "Software Engineering", "Data Analysis"],
    },
    "data_ml": {
        "profile_id": "quality_data_ml",
        "resume_text": "Data science student focused on machine learning, statistics, PyTorch, and analytics.",
        "degree_level": "Master's",
        "major": "data science",
        "grad_date": "2027-12",
        "preferred_roles": ["Data Scientist Intern", "Machine Learning Engineer Intern", "Applied Scientist Intern"],
        "preferred_locations": [],
        "target_industries": ["AI", "Analytics"],
        "sponsorship_need": True,
        "extracted_skills": ["Python", "SQL", "PyTorch", "Machine Learning", "Statistics", "Data Analysis"],
    },
    "marketing_growth": {
        "profile_id": "quality_marketing_growth",
        "resume_text": "Marketing student with campaign analytics, content strategy, brand, and social media experience.",
        "degree_level": "Bachelor's",
        "major": "marketing",
        "grad_date": "2027-05",
        "preferred_roles": ["Marketing Intern", "Growth Marketing Intern", "Brand Intern"],
        "preferred_locations": [],
        "target_industries": ["Marketing", "Consumer"],
        "sponsorship_need": False,
        "extracted_skills": ["Data Analysis", "Statistics"],
    },
    "finance_analyst": {
        "profile_id": "quality_finance_analyst",
        "resume_text": "Finance student interested in analyst internships, financial modeling, risk, and operations.",
        "degree_level": "Bachelor's",
        "major": "finance",
        "grad_date": "2027-05",
        "preferred_roles": ["Finance Intern", "Business Analyst Intern", "Operations Analyst Intern"],
        "preferred_locations": [],
        "target_industries": ["Finance", "Business"],
        "sponsorship_need": False,
        "extracted_skills": ["SQL", "Data Analysis", "Statistics"],
    },
}


def _safe_component_scores(job: Dict[str, Any]) -> Dict[str, float]:
    scores = job.get("component_scores") or {}
    return {
        "skill": float(scores.get("skill_score", 0.0)),
        "qualification": float(scores.get("qualification_coverage_score", 0.0)),
        "role": float(scores.get("role_score", 0.0)),
        "major": float(scores.get("major_score", 0.0)),
        "location": float(scores.get("location_score", 0.0)),
        "freshness": float(scores.get("freshness_score", 0.0)),
        "internship": float(scores.get("internship_bonus", 0.0)),
    }


def _compact_job(job: Dict[str, Any], rank: int) -> Dict[str, Any]:
    return {
        "rank": rank,
        "job_id": job.get("job_id", ""),
        "company": job.get("company", ""),
        "title": job.get("title", ""),
        "location": job.get("location", ""),
        "score": job.get("score", 0.0),
        "action_label": job.get("action_label", ""),
        "matched_skills": job.get("matched_skills", [])[:5],
        "skill_gaps": job.get("skill_gaps", [])[:5],
        "reasons": job.get("reasons", [])[:3],
        "blocking_issues": job.get("blocking_issues", [])[:3],
        "component_scores": _safe_component_scores(job),
    }


def build_quality_report(jobs: List[Dict[str, Any]], *, top_k: int = 20) -> Dict[str, Any]:
    profiles: List[Dict[str, Any]] = []

    for profile_name, raw_profile in REPRESENTATIVE_PROFILES.items():
        profile = normalize_candidate_profile(raw_profile)
        ranked_jobs = rank_jobs(profile, jobs)
        top_jobs = [_compact_job(job, index + 1) for index, job in enumerate(ranked_jobs[:top_k])]
        action_counts = Counter(job.get("action_label", "") for job in ranked_jobs)

        profiles.append(
            {
                "profile_name": profile_name,
                "profile_id": profile["profile_id"],
                "major": profile["major"],
                "preferred_roles": profile["preferred_roles"],
                "skills": sorted(profile["skill_set"]),
                "total_jobs_scored": len(ranked_jobs),
                "action_counts": dict(sorted(action_counts.items())),
                "top_jobs": top_jobs,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_k": top_k,
        "profiles": profiles,
    }


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Ranking Quality Report",
        "",
        f"Generated at: `{report['generated_at']}`",
        f"Top jobs per profile: `{report['top_k']}`",
        "",
        "This report is a lightweight ranking sanity check across representative candidate profiles.",
        "",
    ]

    for profile in report["profiles"]:
        lines.extend(
            [
                f"## {profile['profile_name']}",
                "",
                f"- Major: `{profile['major']}`",
                f"- Preferred roles: {', '.join(profile['preferred_roles']) or 'Any'}",
                f"- Skills: {', '.join(profile['skills']) or 'None'}",
                f"- Total jobs scored: `{profile['total_jobs_scored']}`",
                f"- Action counts: `{json.dumps(profile['action_counts'], sort_keys=True)}`",
                "",
                "| Rank | Action | Score | Company | Role | Location | Matched | Gaps |",
                "| ---: | --- | ---: | --- | --- | --- | --- | --- |",
            ]
        )

        for job in profile["top_jobs"]:
            matched = ", ".join(job["matched_skills"]) or "-"
            gaps = ", ".join(job["skill_gaps"]) or "-"
            lines.append(
                "| {rank} | {action} | {score:.1f} | {company} | {title} | {location} | {matched} | {gaps} |".format(
                    rank=job["rank"],
                    action=job["action_label"],
                    score=float(job["score"]),
                    company=str(job["company"]).replace("|", "/"),
                    title=str(job["title"]).replace("|", "/"),
                    location=str(job["location"]).replace("|", "/"),
                    matched=matched.replace("|", "/"),
                    gaps=gaps.replace("|", "/"),
                )
            )

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate representative ranking quality reports.")
    parser.add_argument(
        "--jobs-dir",
        default="data/processed/jobs",
        help="Directory containing processed job JSON files.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Number of ranked jobs to include per representative profile.",
    )
    parser.add_argument(
        "--output-file",
        default="outputs/ranking_quality_report.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--json-output-file",
        default="outputs/ranking_quality_report.json",
        help="Machine-readable JSON report output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    jobs_dir = PROJECT_ROOT / args.jobs_dir
    output_path = PROJECT_ROOT / args.output_file
    json_output_path = PROJECT_ROOT / args.json_output_file

    jobs = load_all_job_postings(jobs_dir)
    report = build_quality_report(jobs, top_k=args.top_k)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown_report(report), encoding="utf-8")

    json_output_path.parent.mkdir(parents=True, exist_ok=True)
    json_output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote markdown report: {output_path}")
    print(f"Wrote JSON report: {json_output_path}")


if __name__ == "__main__":
    main()
