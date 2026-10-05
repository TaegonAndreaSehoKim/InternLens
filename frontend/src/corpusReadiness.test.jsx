import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { createApiClient } from "./apiClient";
import { fetchCorpusReadiness } from "./corpusReadiness";
import { CorpusReadinessNotice, DashboardPanel, RecommendationPanel } from "./main.jsx";

const unavailable = { status: "unavailable", active_job_count: 0, latest_fetched_at: "2026-07-08T00:00:00Z", message: "Refresh needed" };

describe("job corpus readiness", () => {
  it("preserves a 503 readiness response without treating it as a failed workspace session", async () => {
    const fetchRequest = vi.fn().mockResolvedValue({ status: 503, ok: false, json: async () => unavailable });
    const api = createApiClient({ baseUrl: "", fetchRequest });
    await expect(fetchCorpusReadiness(api)).resolves.toEqual(unavailable);
  });

  it("propagates connection failures so they remain distinct from expired data", async () => {
    const api = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(fetchCorpusReadiness(api)).rejects.toThrow("Failed to fetch");
  });

  it("explains unavailable data, shows the last check, and keeps a retry control", () => {
    const html = renderToStaticMarkup(<CorpusReadinessNotice readiness={unavailable} busy={false} onCheck={() => {}} />);
    expect(html).toContain("Current job data is unavailable");
    expect(html).toContain("Last source check");
    expect(html).toContain("earlier shortlists are still available");
    expect(html).toContain("Check again");
  });

  it("hides the notice once the corpus is ready", () => {
    expect(renderToStaticMarkup(<CorpusReadinessNotice readiness={{ status: "ready" }} />)).toBe("");
  });

  it("disables retries while checking", () => {
    const html = renderToStaticMarkup(<CorpusReadinessNotice readiness={{ status: "checking" }} />);
    expect(html).toMatch(/button[^>]*disabled=""/);
    expect(html).toContain("Checking job availability");
  });

  it("explains why a new shortlist is unavailable", () => {
    const html = renderToStaticMarkup(<RecommendationPanel corpusReadiness={unavailable} dashboardJobView="recommendations" />);
    expect(html).toContain("Waiting for current job data");
    expect(html).toContain("after the job sources are refreshed");
  });

  it.each([true, false])("gates finding matches on corpus readiness (%s)", (corpusReady) => {
    const dashboard = {
      summary: { recommendation_run_count: 0, saved_jobs_count: 0, applied_jobs_count: 0, dismissed_jobs_count: 0 },
      recommended_next_actions: [], saved_jobs: [], applied_jobs: [], dismissed_jobs: [],
      activity: { activities: [] }, recent_runs: [],
    };
    const html = renderToStaticMarkup(<DashboardPanel dashboard={dashboard} profileState="saved" profileReady corpusReady={corpusReady} />);
    const button = html.match(/<button class="primary-action"[^>]*>/)?.[0];
    expect(Boolean(button?.includes("disabled"))).toBe(!corpusReady);
  });
});
