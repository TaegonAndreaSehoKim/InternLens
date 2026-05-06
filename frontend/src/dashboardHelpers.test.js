import { describe, expect, it } from "vitest";
import { activityLabel, activityTitle, compactTimestamp } from "./dashboardHelpers";

describe("dashboardHelpers", () => {
  it("formats ISO timestamps into compact display text", () => {
    expect(compactTimestamp("2026-05-06T19:49:14Z")).toBe("2026-05-06 19:49");
    expect(compactTimestamp(null)).toBe("");
  });

  it("labels known activity types", () => {
    expect(activityLabel("recommendation_run")).toBe("Run");
    expect(activityLabel("saved")).toBe("Saved");
    expect(activityLabel("custom_event")).toBe("custom event");
  });

  it("chooses the most useful activity title", () => {
    expect(activityTitle({ activity_type: "saved", title: "Data Science Intern" })).toBe("Data Science Intern");
    expect(activityTitle({ activity_type: "feedback", job_id: "job_123" })).toBe("job_123");
    expect(activityTitle({ activity_type: "recommendation_run", run_id: "abcdef1234567890" })).toBe("Run abcdef123456");
  });
});
