import { describe, expect, it } from "vitest";
import { activityBadgeLabel, activityLabel, activityTitle, compactTimestamp, formatJobReference } from "./dashboardHelpers";

describe("dashboardHelpers", () => {
  it("formats ISO timestamps into compact display text", () => {
    expect(compactTimestamp("2026-05-06T12:49:14Z")).toMatch(/May 6/);
    expect(compactTimestamp("not-a-date")).toBe("");
    expect(compactTimestamp(null)).toBe("");
  });

  it("labels known activity types", () => {
    expect(activityLabel("recommendation_run")).toBe("Shortlist");
    expect(activityLabel("saved")).toBe("Saved");
    expect(activityLabel("dismissed")).toBe("Hidden");
    expect(activityLabel("custom_event")).toBe("custom event");
  });

  it("uses feedback labels for activity badges", () => {
    expect(activityBadgeLabel({ activity_type: "feedback", label: "applied" })).toBe("Applied");
    expect(activityBadgeLabel({ activity_type: "feedback", label: "skipped" })).toBe("Hidden");
    expect(activityBadgeLabel({ activity_type: "recommendation_run" })).toBe("Shortlist");
  });

  it("formats job references from snapshots", () => {
    expect(formatJobReference({ company: "Hone Health", title: "Data Science Intern (Summer 2026)" })).toBe(
      "Hone Health_Data Science Intern_Summer 2026"
    );
    expect(formatJobReference({ company: "data/raw/company.json", title: "Data Science Intern" })).toBe(
      "Data Science Intern"
    );
  });

  it("chooses the most useful activity title", () => {
    expect(activityTitle({ activity_type: "saved", title: "Data Science Intern" })).toBe("Data Science Intern");
    expect(activityTitle({ activity_type: "feedback", summary: "Strong match" })).toBe("Strong match");
    expect(activityTitle({ activity_type: "saved", job_id: "job_123" })).toBe("Job saved");
    expect(activityTitle({ activity_type: "recommendation_run", run_id: "abcdef1234567890" })).toBe(
      "New recommendation set"
    );
    expect(activityTitle({ activity_type: "saved", summary: "data/processed/jobs/example.json" })).toBe("Job saved");
    expect(
      activityTitle(
        { activity_type: "feedback", job_id: "job_123", label: "applied" },
        {
          job_123: {
            job_snapshot: {
              company: "Hone Health",
              title: "Data Science Intern (Summer 2026)"
            }
          }
        }
      )
    ).toBe("Marked Hone Health_Data Science Intern_Summer 2026 as applied");
    expect(
      activityTitle({
        activity_type: "feedback",
        summary: "Marked greenhouse_honehealth_5169202004 as applied",
        label: "applied"
      })
    ).toBe("Marked role as applied");
  });
});
