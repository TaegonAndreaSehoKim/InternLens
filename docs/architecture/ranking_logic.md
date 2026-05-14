# Ranking Logic

This document explains the current baseline evaluator at a product level.
The implementation source of truth is `src/ranking/baseline_scorer.py`.

## Purpose

InternLens ranks internships with an interpretable heuristic evaluator.
The goal is not to hide decisions inside a model. The goal is to show why a role is recommended, what matched, what is missing, and what eligibility issues make the role unrealistic.

## Inputs

The scorer compares two records:

- Candidate profile: skills, preferred roles, majors, preferred locations, degree level, graduation date, and sponsorship need.
- Job posting: title, company, team, location, remote status, employment type, description, qualifications, posting date, and sponsorship text.

## Fit Score

The base fit score is a weighted sum:

```text
fit =
  skill_score * 0.35
  + qualification_coverage_score * 0.17
  + role_score * 0.18
  + major_score * 0.12
  + location_score * 0.08
  + freshness_score * 0.04
  + internship_signal_score * 0.06
```

The result is bounded to `0.0` through `1.0`, then shown to users as a `0-100` score.

Current components:

- `skill_score`: compares candidate skills against required qualifications, preferred qualifications, title, and description.
- `qualification_coverage_score`: measures how much of the structured required/preferred qualification signal is covered. Sparse postings without structured qualifications are treated as neutral instead of being punished.
- `role_score`: compares job title tokens against preferred role tokens. If no preferred roles are provided, role fit is treated as neutral so the user can search broadly.
- `major_score`: checks whether the user's selected major fields align with title, team, description, qualifications, or employment type signals. Missing or `other` major input is treated as neutral in the score but does not count as a relevance signal.
- `location_score`: returns a match when the job location or remote status fits the user's location preferences. If no preferred locations are provided, location fit is treated as neutral.
- `freshness_score`: gives a small tie-breaker to recently posted jobs and gently lowers stale postings.
- `internship_signal_score`: rewards postings that explicitly identify themselves as internships.

## Skill Priority

Skill matching uses priority weights so all skill mentions are not treated equally:

```text
required qualification: 1.00
title signal:           0.70
preferred qualification:0.55
description signal:     0.35
```

When a skill appears in multiple places, the scorer keeps the strongest signal instead of double-counting the same word.
For postings with structured qualifications, required and preferred qualification fields are trusted first.
For sparse public postings without structured qualifications, title and description fallback matching is allowed only when the title looks technical, data-oriented, research-oriented, or engineering-oriented.

Matched skills and skill gaps are also ordered by this priority so the frontend can show the most important skill signals first.

## Blockers

Blockers are intentionally separate from the fit score.
A role can look relevant but still be a poor recommendation if the posting has hard constraints.

Current blockers include:

- sponsorship unavailable when the user needs sponsorship
- posting does not appear to be an internship
- posting appears to be senior-level
- posting appears to require a PhD when the candidate profile is not PhD-level
- graduation timing appears incompatible with the posting

If blockers are present, the action label becomes `Skip` even if the raw fit score is high.

## Noise Guardrails

Public ATS data is noisy, so the scorer includes conservative guardrails:

- Qualification fields are trusted more than broad description text.
- Title and description fallback skill matching is restricted to roles that look technical, data-oriented, research-oriented, or engineering-oriented.
- Business, marketing, communications, people, and operations internships are prevented from outranking core technical roles unless the profile itself targets those fields.
- Seniority words do not block a role when the title explicitly identifies the role as an internship.
- Neutral defaults from open-ended profile fields are not enough by themselves to produce `Apply Now` or `Apply Later`; the scorer still requires at least one real skill, preferred-role, or major match.

## Action Labels

The score and blockers are converted into a user-facing action label:

- `Apply Now`: blocker-free role with score `>= 70`.
- `Apply Later`: blocker-free role with score `>= 45`, or a clear internship with some role, skill, or major relevance.
- `Skip`: blocked roles, non-core noisy matches, or low-signal roles.

The final list is sorted by action priority first, then blocker severity, internship signal strength, score, and title.

## User-Facing Explanations

Each scored job returns:

- `score`
- `action_label`
- `matched_skills`
- `skill_gaps`
- `reasons`
- `blocking_issues`
- `component_scores`

The frontend uses these fields to show why a role ranked where it did and which skills may be worth adding to the user's profile.
