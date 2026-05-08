import { describe, expect, it } from "vitest";
import { activityLabel, activityTitle, compactTimestamp } from "./dashboardHelpers";

describe("dashboardHelpers", () => {
  it("formats ISO timestamps into compact display text", () => {
    expect(compactTimestamp("2026-05-06T12:49:14Z")).toMatch(/May 6/);
    expect(compactTimestamp("not-a-date")).toBe("");
    expect(compactTimestamp(null)).toBe("");
  });

  it("labels known activity types", () => {
    expect(activityLabel("recommendation_run")).toBe("Recommendations");
    expect(activityLabel("saved")).toBe("Saved");
    expect(activityLabel("custom_event")).toBe("custom event");
  });

  it("chooses the most useful activity title", () => {
    expect(activityTitle({ activity_type: "saved", title: "Data Science Intern" })).toBe("Data Science Intern");
    expect(activityTitle({ activity_type: "feedback", summary: "Strong match" })).toBe("Strong match");
    expect(activityTitle({ activity_type: "saved", job_id: "job_123" })).toBe("Job saved");
    expect(activityTitle({ activity_type: "recommendation_run", run_id: "abcdef1234567890" })).toBe(
      "New recommendation set"
    );
    expect(activityTitle({ activity_type: "saved", summary: "data/processed/jobs/example.json" })).toBe("Job saved");
  });
});
