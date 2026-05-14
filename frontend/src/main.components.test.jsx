import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { JobCard, JobDetailModal, ProfileQuality, RecommendationPanel, scoreExplanation } from "./main.jsx";

const baseJob = {
  job_id: "job_1",
  company: "Acme",
  title: "Software Engineering Intern",
  location: "Atlanta",
  fit_level: "strong",
  recommendation: "apply_now",
  reranked_score: 88,
  posting_date: "2026-05-10",
  fetched_at: "2026-05-12T00:00:00Z",
  expires_at: "2026-05-20T00:00:00Z",
  matched_skills: ["Python", "React"],
  skill_gaps: ["AWS"],
  component_scores: {
    skill_score: 0.7,
    qualification_coverage_score: 0.55,
    role_score: 1,
    major_score: 0.8,
    location_score: 1,
    freshness_score: 1,
    internship_bonus: 1
  },
  why_apply: ["preferred role matches software engineering"],
  watchouts: ["AWS is not visible in the profile"],
  application_link: "https://example.com/apply"
};

const noop = () => {};

describe("main UI components", () => {
  it("shows recommendation signals by default in the review panel", () => {
    const html = renderToStaticMarkup(
      <RecommendationPanel
        recommendations={{ results: [baseJob] }}
        dashboard={null}
        dashboardJobView="recommendations"
        dashboardJobLists={{}}
        selectedRun="run_1"
        filter="all"
        onFilterChange={noop}
        busy={false}
        onAddSkill={noop}
        onOpenDetails={noop}
        onAction={noop}
      />
    );

    expect(html).toContain("Hide signals");
    expect(html).toContain("Matched skills");
    expect(html).toContain("Skill gaps");
    expect(html).toContain("Qualification coverage");
    expect(html).toContain("Freshness");
    expect(html).toContain("Internship signal");
    expect(html).toContain("Highest priority");
    expect(html).toContain("Score explanation:");
    expect(html).not.toContain("Show signals");
  });

  it("can render a compact job card when signals are hidden", () => {
    const html = renderToStaticMarkup(
      <JobCard
        job={baseJob}
        busy={false}
        expanded={false}
        onToggleExpanded={noop}
        onAddSkill={noop}
        onOpenDetails={noop}
        onAction={noop}
      />
    );

    expect(html).toContain("Show signals");
    expect(html).toContain("1 skill gap");
    expect(html).not.toContain("Matched skills");
  });

  it("shows profile readiness as a concise summary", () => {
    const quality = {
      isReady: false,
      requiredComplete: 1,
      requiredTotal: 2,
      items: [
        { label: "Target role selected", detail: "Choose at least one role.", complete: true, required: true },
        { label: "Core skills selected", detail: "Add skills.", complete: false, required: true },
        { label: "Industry preference added", detail: "Optional tie-breaker.", complete: false, required: false }
      ]
    };

    const html = renderToStaticMarkup(<ProfileQuality quality={quality} />);

    expect(html).toContain("Matching readiness");
    expect(html).toContain("Core skills selected");
    expect(html).toContain("Optional signals");
  });

  it("renders match context in the job detail modal", () => {
    const detail = {
      ...baseJob,
      description: "Full posting text with more detail.",
      short_description: "Short summary.",
      min_qualifications: "",
      preferred_qualifications: "React experience preferred.",
      possible_requirements: ["Currently enrolled"],
      possible_blockers: ["Sponsorship unclear"],
      internship_signals: ["Intern title"],
      source: "lever",
      source_url: "https://example.com/source",
      application_link: "https://example.com/apply",
      freshness_days: 7
    };

    const html = renderToStaticMarkup(
      <JobDetailModal detail={detail} summaryJob={baseJob} status={{ loading: false, error: "" }} onClose={noop} />
    );

    expect(html).toContain("Job details");
    expect(html).toContain("Score explanation:");
    expect(html).toContain("Matched skills");
    expect(html).toContain("Skill gaps");
    expect(html).toContain("Full posting text");
  });

  it("builds a plain-language score explanation from match signals", () => {
    expect(scoreExplanation(baseJob)).toContain("matched Python, React");
    expect(scoreExplanation(baseJob)).toContain("missing or unclear AWS");
  });

  it("keeps skill-gap add actions wired on cards", () => {
    const onAddSkill = vi.fn();
    const html = renderToStaticMarkup(
      <JobCard
        job={baseJob}
        busy={false}
        expanded
        onToggleExpanded={noop}
        onAddSkill={onAddSkill}
        onOpenDetails={noop}
        onAction={noop}
      />
    );

    expect(html).toContain("title=\"Add AWS to profile skills\"");
    expect(html).toContain("Highest priority");
    expect(html).toContain(">Add</span>");
  });
});
