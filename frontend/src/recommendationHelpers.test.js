import { describe, expect, it } from "vitest";
import {
  actionLabel,
  actionValue,
  checkedAgeLabel,
  displayScore,
  freshnessStatus,
  postedAgeLabel,
  recommendationCounts,
  sortJobs,
  sourceFreshnessSummary,
  stateAgeLabel,
  visibleRecommendations
} from "./recommendationHelpers";

describe("recommendationHelpers", () => {
  const jobs = [
    { job_id: "a", recommendation: "apply_now", reranked_score: 91.6 },
    { job_id: "b", action_label: "Apply Later", score: 72.2 },
    { job_id: "c", action_label: "Skip", score: 41 }
  ];

  it("normalizes recommendation values from API codes and action labels", () => {
    expect(actionValue(jobs[0])).toBe("apply_now");
    expect(actionValue(jobs[1])).toBe("apply_later");
    expect(actionLabel(jobs[0])).toBe("Apply Now");
  });

  it("counts and filters jobs by recommendation bucket", () => {
    expect(recommendationCounts(jobs)).toEqual({
      all: 3,
      apply_now: 1,
      apply_later: 1,
      skip: 1
    });
    expect(visibleRecommendations(jobs, "apply_later")).toEqual([jobs[1]]);
  });

  it("sorts jobs without mutating the original order", () => {
    const sortableJobs = [
      { job_id: "a", score: 70, posting_date: "2026-05-10", fetched_at: "2026-05-09T00:00:00Z" },
      { job_id: "b", score: 92, posting_date: "2026-05-08", fetched_at: "2026-05-12T00:00:00Z" },
      { job_id: "c", score: 81, posting_date: "2026-05-12", fetched_at: "2026-05-10T00:00:00Z" }
    ];

    expect(sortJobs(sortableJobs, "recommended").map((job) => job.job_id)).toEqual(["a", "b", "c"]);
    expect(sortJobs(sortableJobs, "newest").map((job) => job.job_id)).toEqual(["c", "a", "b"]);
    expect(sortJobs(sortableJobs, "checked").map((job) => job.job_id)).toEqual(["b", "c", "a"]);
    expect(sortJobs(sortableJobs, "score").map((job) => job.job_id)).toEqual(["b", "c", "a"]);
    expect(sortableJobs.map((job) => job.job_id)).toEqual(["a", "b", "c"]);
  });

  it("prefers rounded reranked score when present", () => {
    expect(displayScore(jobs[0])).toBe(92);
    expect(displayScore(jobs[1])).toBe(72);
    expect(displayScore({ job_id: "d" })).toBeNull();
  });

  it("formats posting age from a posting date", () => {
    const now = new Date("2026-05-12T18:00:00Z");

    expect(postedAgeLabel("2026-05-12", now)).toBe("posted today");
    expect(postedAgeLabel("2026-05-11", now)).toBe("posted 1 day ago");
    expect(postedAgeLabel("2026-05-07", now)).toBe("posted 5 days ago");
    expect(postedAgeLabel("", now)).toBe("");
  });

  it("formats source freshness from a fetched timestamp", () => {
    const now = new Date("2026-05-12T18:00:00Z");

    expect(checkedAgeLabel("2026-05-12T01:10:00+00:00", now)).toBe("checked today");
    expect(checkedAgeLabel("2026-05-11T23:10:00+00:00", now)).toBe("checked 1 day ago");
    expect(checkedAgeLabel("2026-05-09T23:10:00+00:00", now)).toBe("checked 3 days ago");
    expect(checkedAgeLabel("not-a-date", now)).toBe("");
  });

  it("formats saved job state age", () => {
    const now = new Date("2026-05-12T18:00:00Z");

    expect(stateAgeLabel("saved", "2026-05-12T01:10:00+00:00", now)).toBe("saved today");
    expect(stateAgeLabel("applied", "2026-05-11T23:10:00+00:00", now)).toBe("applied 1 day ago");
    expect(stateAgeLabel("dismissed", "2026-05-09T23:10:00+00:00", now)).toBe("hidden 3 days ago");
    expect(stateAgeLabel("saved", "bad-date", now)).toBe("");
  });

  it("summarizes source expiry status", () => {
    const now = new Date("2026-05-12T18:00:00Z");

    expect(freshnessStatus("2026-05-20T00:00:00+00:00", now)).toEqual({
      label: "fresh source",
      tone: "fresh"
    });
    expect(freshnessStatus("2026-05-14T00:00:00+00:00", now)).toEqual({
      label: "refresh in 2d",
      tone: "soon"
    });
    expect(freshnessStatus("2026-05-12T00:00:00+00:00", now)).toEqual({
      label: "refresh due today",
      tone: "stale"
    });
    expect(freshnessStatus("2026-05-10T00:00:00+00:00", now)).toEqual({
      label: "refresh due",
      tone: "stale"
    });
    expect(freshnessStatus("bad-date", now)).toBeNull();
  });

  it("summarizes freshness across a visible job list", () => {
    const now = new Date("2026-05-12T18:00:00Z");
    const summary = sourceFreshnessSummary([
      {
        job_id: "fresh",
        expires_at: "2026-05-20T00:00:00+00:00",
        fetched_at: "2026-05-12T01:00:00+00:00"
      },
      {
        job_id: "soon",
        expires_at: "2026-05-14T00:00:00+00:00",
        fetched_at: "2026-05-10T01:00:00+00:00"
      },
      {
        job_id: "stale",
        expires_at: "2026-05-10T00:00:00+00:00",
        fetched_at: "2026-05-09T01:00:00+00:00"
      },
      { job_id: "unknown" }
    ], now);

    expect(summary).toEqual({
      total: 4,
      fresh: 1,
      soon: 1,
      stale: 1,
      unknown: 1,
      latestFetchedAt: "2026-05-12T01:00:00+00:00",
      latestCheckedLabel: "checked today"
    });
  });
});
