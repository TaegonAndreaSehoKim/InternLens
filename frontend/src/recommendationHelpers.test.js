import { describe, expect, it } from "vitest";
import {
  actionLabel,
  actionValue,
  displayScore,
  postedAgeLabel,
  recommendationCounts,
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
});
